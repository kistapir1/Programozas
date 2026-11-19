import { useState, useEffect, useRef, useId } from "react";

interface StationAutocompleteProps {
  value: string;
  onChange: (value: string) => void;
  placeholder?: string;
  className?: string;
}

const API_BASE = "http://localhost:8000";

interface StationSearchHit {
  name: string;
}

export default function StationAutocomplete({
  value,
  onChange,
  placeholder,
  className = "text-input",
}: StationAutocompleteProps) {
  const [suggestions, setSuggestions] = useState<string[]>([]);
  const [isLoading, setIsLoading] = useState(false);
  const [searchComplete, setSearchComplete] = useState(false);
  const [searchError, setSearchError] = useState<string | null>(null);
  const [isFocused, setIsFocused] = useState(false);
  const [selectedIndex, setSelectedIndex] = useState<number>(-1);

  const containerRef = useRef<HTMLDivElement>(null);
  const inputRef = useRef<HTMLInputElement>(null);
  const selectedStationRef = useRef<string | null>(null);
  const resultsId = useId();

  useEffect(() => {
    if (selectedStationRef.current === value) {
      selectedStationRef.current = null;
      return;
    }
    selectedStationRef.current = null;

    const query = value.trim();
    if (!query) {
      setSuggestions([]);
      setIsLoading(false);
      setSearchComplete(false);
      setSearchError(null);
      return;
    }

    const controller = new AbortController();
    setSuggestions([]);
    setIsLoading(true);
    setSearchComplete(false);
    setSearchError(null);
    setSelectedIndex(-1);

    const timeoutId = window.setTimeout(async () => {
      try {
        const res = await fetch(
          `${API_BASE}/api/stations?q=${encodeURIComponent(query)}`,
          { signal: controller.signal }
        );
        if (!res.ok) {
          throw new Error(`A megállókeresés nem sikerült (HTTP ${res.status}).`);
        }

        const data: StationSearchHit[] = await res.json();
        const names = Array.from(new Set(data.map((item) => item.name)));
        setSuggestions(names);
        setSearchComplete(true);
      } catch (err: unknown) {
        if (controller.signal.aborted) return;
        setSearchError(err instanceof Error ? err.message : "Ismeretlen hiba történt.");
      } finally {
        if (!controller.signal.aborted) {
          setIsLoading(false);
        }
      }
    }, 180);

    return () => {
      window.clearTimeout(timeoutId);
      controller.abort();
    };
  }, [value]);

  useEffect(() => {
    function handleClickOutside(e: MouseEvent) {
      if (
        containerRef.current &&
        !containerRef.current.contains(e.target as Node)
      ) {
        setIsFocused(false);
      }
    }
    document.addEventListener("mousedown", handleClickOutside);
    return () => document.removeEventListener("mousedown", handleClickOutside);
  }, []);

  const handleSelect = (stationName: string) => {
    selectedStationRef.current = stationName;
    onChange(stationName);
    setIsFocused(false);
    setSuggestions([]);
    inputRef.current?.blur();
  };

  const handleKeyDown = (e: React.KeyboardEvent<HTMLInputElement>) => {
    if (!isFocused || suggestions.length === 0) return;

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
      setIsFocused(false);
    }
  };

  return (
    <div className="autocomplete-container" ref={containerRef}>
      <input
        ref={inputRef}
        type="text"
        className={className}
        placeholder={placeholder}
        value={value}
        onChange={(e) => {
          onChange(e.target.value);
          setIsFocused(true);
        }}
        onFocus={() => {
          setIsFocused(true);
        }}
        onKeyDown={handleKeyDown}
        autoComplete="off"
        aria-label={placeholder}
        aria-expanded={isFocused && Boolean(value.trim())}
        aria-controls={resultsId}
        aria-autocomplete="list"
      />

      {isFocused && value.trim() && (isLoading || searchError || searchComplete) && (
        <ul
          id={resultsId}
          className="autocomplete-dropdown"
          role={suggestions.length > 0 && !isLoading && !searchError ? "listbox" : undefined}
          aria-label={suggestions.length > 0 ? "Megálló keresési találatok" : undefined}
        >
          {isLoading ? (
            <li className="autocomplete-message" role="status">Keresés…</li>
          ) : searchError ? (
            <li className="autocomplete-message error" role="alert">
              {searchError}
            </li>
          ) : suggestions.length > 0 ? (
            suggestions.map((name, index) => (
              <li
                key={name}
                role="option"
                aria-selected={index === selectedIndex}
                className={`autocomplete-item ${
                  index === selectedIndex ? "active" : ""
                }`}
                onMouseDown={() => handleSelect(name)}
              >
                <span className="station-text">{name}</span>
              </li>
            ))
          ) : (
            <li className="autocomplete-message" role="status">Nincs találat.</li>
          )}
        </ul>
      )}
    </div>
  );
}
