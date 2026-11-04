import { useState } from "react";

export interface CheckboxOption {
  id: string;
  label: string;
}

interface CheckboxGroupProps {
  options: CheckboxOption[];
  onChange?: (selected: string[]) => void;
}

function CheckboxGroup({ options, onChange }: CheckboxGroupProps) {
  const [selected, setSelected] = useState<string[]>([]);

  const toggle = (id: string) => {
    setSelected((prev) => {
      const next = prev.includes(id)
        ? prev.filter((x) => x !== id)
        : [...prev, id];
      onChange?.(next);
      return next;
    });
  };

  return (
    <>
      {options.map((opt) => (
        <label key={opt.id} className="checkbox-item">
          <input
            type="checkbox"
            checked={selected.includes(opt.id)}
            onChange={() => toggle(opt.id)}
          />
          <span>{opt.label}</span>
        </label>
      ))}
    </>
  );
}

export default CheckboxGroup;
