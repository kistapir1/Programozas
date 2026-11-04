import Dropdown from "./Dropdown";
import CheckboxGroup, { type CheckboxOption } from "./CheckboxGroup";
import WaypointInputs from "./WaypointInputs";

// ── Placeholder names – you can rename these later ──────────────────────────
const DROPDOWN_TITLES = [
  "Közlekedési eszköz",
  "2. Menetrend típusa",
  "3. Időszak",
  "4. Járat kategória",
  "5. Egyéb szűrők",
];

const CHECKBOX_OPTIONS: CheckboxOption[] = [
  { id: "cb1", label: "Helyközi Járat" },
  { id: "cb2", label: "Helyi járat" },
  { id: "cb3", label: "Vonat" },
  { id: "cb4", label: "Gyalog" },
  { id: "cb5", label: "Elektromos Roller" },
];
// ────────────────────────────────────────────────────────────────────────────

interface SidebarProps {
  onSearch?: (params: unknown) => void;
}

function Sidebar({ onSearch }: SidebarProps) {
  const handleSearch = () => {
    onSearch?.({});
  };

  return (
    <aside className="sidebar">
      <h1 className="sidebar-title">Menetrend kereső</h1>

      {/* ── 5 Dropdown menus ───────────────────────────────────────────── */}
      <div className="dropdown-group">
        {/* First dropdown has checkboxes */}
        <Dropdown title={DROPDOWN_TITLES[0]} defaultOpen>
          <CheckboxGroup options={CHECKBOX_OPTIONS} />
        </Dropdown>

        {/* Remaining 4 dropdowns – empty for now, fill with content later */}
        {DROPDOWN_TITLES.slice(1).map((title) => (
          <Dropdown key={title} title={title}>
            <p style={{ color: "#94a3b8", fontSize: "0.88rem" }}>
              Tartalom hamarosan…
            </p>
          </Dropdown>
        ))}
      </div>

      <div className="sidebar-divider" />

      {/* ── Origin / waypoints / destination inputs ──────────────────── */}
      <WaypointInputs
        originLabel="Indulási pont"
        waypointLabel="Közbenső megálló"
        destinationLabel="Cél"
      />

      {/* ── Search button ─────────────────────────────────────────────── */}
      <button className="search-btn" onClick={handleSearch}>
        🔍 Keresés
      </button>
    </aside>
  );
}

export default Sidebar;
