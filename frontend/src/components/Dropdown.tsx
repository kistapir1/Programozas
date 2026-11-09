import { useState, type ReactNode } from "react";

interface DropdownProps {
  title: string;
  children: ReactNode;
  defaultOpen?: boolean;
}

function Dropdown({ title, children, defaultOpen = false }: DropdownProps) {
  const [open, setOpen] = useState(defaultOpen);

  return (
    <div className="dropdown">
      <button
        className={`dropdown-header${open ? " open" : ""}`}
        onClick={() => setOpen((prev) => !prev)}
        aria-expanded={open}
      >
        {title}
        <span className="dropdown-arrow">▼</span>
      </button>
      {open && <div className="dropdown-body">{children}</div>}
    </div>
  );
}

export default Dropdown;
