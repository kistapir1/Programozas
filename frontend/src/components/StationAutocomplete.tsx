import { useState, useEffect, useRef } from "react";

interface StationAutocompleteProps {
  value: string;
  onChange: (value: string) => void;
  placeholder?: string;
  className?: string;
}

const API_BASE = "http://localhost:8000";

export default function StationAutocomplete({
  value,
  onChange,
  placeholder,
  className = "text-input",
}: StationAutocompleteProps) {
  const [suggestions, setSuggestions] = useState<string[]>([]);
  const [isOpen, setIsOpen] = useState(false);
  const [isLoading, setIsLoading] = useState(false);
  const [selectedIndex, setSelectedIndex] = useState<number>(-1);

  const containerRef = useRef<HTMLDivElement>(null);
  const debounceTimerRef = useRef<ReturnType<typeof setTimeout> | null>(null);

  // Lekérés a backend /api/stations végpontról
  useEffect(() => {
    if (!value || value.trim().length < 2) {
      setSuggestions([]);
      setIsOpen(false);
      return;
    }

    if (debounceTimerRef.current) {
      clearTimeout(debounceTimerRef.current);
    }

    debounceTimerRef.current = setTimeout(async () => {
      try {
        setIsLoading(true);
        const res = await fetch(
          `${API_BASE}/api/stations?q=${encodeURIComponent(value.trim())}`
        );
        if (!res.ok) return;

        const data = await res.json();
        // data: [{ name: "..." }, ...]
        const names: string[] = Array.from(
          new Set(data.map((item: { name: string }) => item.name))
        );

        setSuggestions(names);
        setIsOpen(names.length > 0);
        setSelectedIndex(-1);
      } catch (err) {
        console.error("Autocomplete fetch hiba:", err);
      } finally {
        setIsLoading(false);
      }
    }, 180);

    return () => {
      if (debounceTimerRef.current) {
        clearTimeout(debounceTimerRef.current);
      }
    };
  }, [value]);

  // Kívülre kattintás figyelése a lista bezárásához
  useEffect(() => {
    function handleClickOutside(e: MouseEvent) {
      if (
        containerRef.current &&
        !containerRef.current.contains(e.target as Node)
      ) {
        setIsOpen(false);
      }
    }
    document.addEventListener("mousedown", handleClickOutside);
    return () => document.removeEventListener("mousedown", handleClickOutside);
  }, []);

  const handleSelect = (stationName: string) => {
    onChange(stationName);
    setIsOpen(false);
    setSuggestions([]);
  };

  const handleKeyDown = (e: React.KeyboardEvent<HTMLInputElement>) => {
    if (!isOpen || suggestions.length === 0) return;

    if (e.key === "ArrowDown") {
      e.preventDefault();
      setSelectedIndex((prev) =>
        prev < suggestions.length - 1 ? prev + 1 : 0
      );
    } else if (e.key === "ArrowUp") {
      e.preventDefault();
      setSelectedIndex((prev) =>
        prev > 0 ? prev - 1 : suggestions.length - 1
      );
    } else if (e.key === "Enter" && selectedIndex >= 0) {
      e.preventDefault();
      handleSelect(suggestions[selectedIndex]);
    } else if (e.key === "Escape") {
      setIsOpen(false);
    }
  };

  return (
    <div className="autocomplete-container" ref={containerRef}>
      <input
        type="text"
        className={className}
        placeholder={placeholder}
        value={value}
        onChange={(e) => onChange(e.target.value)}
        onFocus={() => {
          if (suggestions.length > 0) setIsOpen(true);
        }}
        onKeyDown={handleKeyDown}
        autoComplete="off"
      />

      {isLoading && <span className="autocomplete-spinner">…</span>}

      {isOpen && suggestions.length > 0 && (
        <ul className="autocomplete-dropdown">
          {suggestions.map((name, index) => (
            <li
              key={index}
              className={`autocomplete-item ${
                index === selectedIndex ? "active" : ""
              }`}
              onMouseDown={() => handleSelect(name)}
            >
              <span className="station-text">{name}</span>
            </li>
          ))}
        </ul>
      )}
    </div>
  );
}
