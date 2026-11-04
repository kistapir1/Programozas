import { useState } from "react";
import Dropdown from "./Dropdown";
import CheckboxGroup, { type CheckboxOption } from "./CheckboxGroup";
import WaypointInputs from "./WaypointInputs";

// Közlekedési eszközök – a checkbox id-k megegyeznek a backend transport_mode értékeivel
const TRANSPORT_OPTIONS: CheckboxOption[] = [
  { id: "train",        label: "Vonat" },
  { id: "intercity_bus", label: "Helyközi járat" },
  { id: "local_bus",    label: "Helyi járat" },
];

const OTHER_DROPDOWNS = ["Átszálások száma", "Átszállásra szánt idő", "Indulási időpont", "Egyéb"];

interface WaypointValues {
  origin: string;
  waypoints: string[];
  destination: string;
}

interface SidebarProps {
  onSearch?: (params: {
    origin: string;
    destination: string;
    waypoints: string[];
    transport_modes: string[];
  }) => void;
}

function Sidebar({ onSearch }: SidebarProps) {
  const [waypointValues, setWaypointValues] = useState<WaypointValues>({
    origin: "",
    waypoints: [],
    destination: "",
  });
  const [selectedModes, setSelectedModes] = useState<string[]>([]);

  const handleSearch = () => {
    onSearch?.({
      origin: waypointValues.origin,
      destination: waypointValues.destination,
      waypoints: waypointValues.waypoints,
      transport_modes: selectedModes,
    });
  };

  return (
    <aside className="sidebar">
      <h1 className="sidebar-title">Menetrend kereső</h1>

      {/* ── Dropdown menük ─────────────────────────────────────────────── */}
      <div className="dropdown-group">
        {/* Közlekedési eszköz választó checkboxokkal */}
        <Dropdown title="Közlekedési eszköz" defaultOpen>
          <CheckboxGroup options={TRANSPORT_OPTIONS} onChange={setSelectedModes} />
        </Dropdown>

        {/* Többi dropdown – egyelőre üres */}
        {OTHER_DROPDOWNS.map((title) => (
          <Dropdown key={title} title={title}>
            <p style={{ color: "#94a3b8", fontSize: "0.88rem" }}>
              Tartalom hamarosan…
            </p>
          </Dropdown>
        ))}
      </div>

      <div className="sidebar-divider" />

      {/* ── Indulási / közbenső / cél mezők ───────────────────────────── */}
      <WaypointInputs
        originLabel="Indulási pont"
        waypointLabel="Közbenső megálló"
        destinationLabel="Cél"
        onValuesChange={setWaypointValues}
      />

      {/* ── Keresés gomb ──────────────────────────────────────────────── */}
      <button className="search-btn" onClick={handleSearch}>
        Keresés
      </button>
    </aside>
  );
}

export default Sidebar;
