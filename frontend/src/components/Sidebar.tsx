import { useState } from "react";
import Dropdown from "./Dropdown";
import CheckboxGroup, { type CheckboxOption } from "./CheckboxGroup";
import WaypointInputs from "./WaypointInputs";

// Közlekedési eszközök – a checkbox id-k megegyeznek a backend transport_mode értékeivel
const TRANSPORT_OPTIONS: CheckboxOption[] = [
  { id: "train",         label: "Vonat" },
  { id: "intercity_bus", label: "Helyközi járat" },
  { id: "local_bus",     label: "Helyi járat" },
  { id: "metro",         label: "Metró" },
  { id: "tram",          label: "Villamos" },
  { id: "trolleybus",    label: "Trolibusz" },
];

const OTHER_DROPDOWNS = ["Egyéb"];

const MAX_TRANSFERS_LIMIT = 5;

type TimeMode = "departure" | "arrival";

function getCurrentDateString(): string {
  const now = new Date();
  const yyyy = now.getFullYear();
  const mm = String(now.getMonth() + 1).padStart(2, "0");
  const dd = String(now.getDate()).padStart(2, "0");
  return `${yyyy}-${mm}-${dd}`;
}

function getCurrentTimeString(): string {
  const now = new Date();
  const hh = String(now.getHours()).padStart(2, "0");
  const min = String(now.getMinutes()).padStart(2, "0");
  return `${hh}:${min}`;
}

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
    max_transfers: number;
    time_mode: TimeMode;
    date: string;
    time: string;
  }) => void;
}

function Sidebar({ onSearch }: SidebarProps) {
  const [waypointValues, setWaypointValues] = useState<WaypointValues>({
    origin: "",
    waypoints: [],
    destination: "",
  });

  const [selectedModes, setSelectedModes] = useState<string[]>([]);

  const [maxTransfers, setMaxTransfers] = useState<number>(2);
  const [timeMode, setTimeMode] = useState<TimeMode>("departure");
  const [dateValue, setDateValue] = useState<string>(getCurrentDateString());
  const [timeValue, setTimeValue] = useState<string>(getCurrentTimeString()); 

  const handleSearch = () => {
    onSearch?.({
      origin: waypointValues.origin,
      destination: waypointValues.destination,
      waypoints: waypointValues.waypoints,
      transport_modes: selectedModes,
      max_transfers: maxTransfers,
      time_mode: timeMode,
      date: dateValue,
      time: timeValue,
    });
  };

  return (
    <aside className="sidebar">
      {/* ── Dropdown menük ─────────────────────────────────────────────── */}
      <div className="dropdown-group">
        {/* Közlekedési eszköz választó checkboxokkal */}
        <Dropdown title="Közlekedési eszköz" defaultOpen>
          <CheckboxGroup options={TRANSPORT_OPTIONS} onChange={setSelectedModes} />
        </Dropdown>

        <Dropdown title="Átszálások száma">
          <div className="slider-wrapper">
            <div className="slider-value-row">
              <span className="slider-label">Max. átszállás</span>
              <span className="slider-value">
                {maxTransfers === 0 ? "Közvetlen" : maxTransfers}
              </span>
            </div>
            <input
              type="range"
              min={0}
              max={MAX_TRANSFERS_LIMIT}
              step={1}
              value={maxTransfers}
              onChange={(e) => setMaxTransfers(Number(e.target.value))}
              className="transfer-slider"
            />
            <div className="slider-ticks">
              {Array.from({ length: MAX_TRANSFERS_LIMIT + 1 }, (_, i) => (
                <span key={i}>{i}</span>
              ))}
            </div>
          </div>
        </Dropdown>

        <Dropdown title="Átszállásra szánt idő">
          <p style={{ color: "#94a3b8", fontSize: "0.88rem" }}>
            Tartalom hamarosan…
          </p>
        </Dropdown>

        {/* Indulási időpont – dátum/idő választó */}
        <Dropdown title="Indulási időpont">
          <div className="datetime-wrapper">
            <div className="time-mode-toggle">
              <button
                type="button"
                className={`time-mode-btn ${timeMode === "departure" ? "active" : ""}`}
                onClick={() => setTimeMode("departure")}
              >
                Indulás
              </button>
              <button
                type="button"
                className={`time-mode-btn ${timeMode === "arrival" ? "active" : ""}`}
                onClick={() => setTimeMode("arrival")}
              >
                Érkezés
              </button>
            </div>

            <div className="datetime-row">
              <div className="input-row">
                <span className="input-label">Dátum</span>
                <input
                  type="date"
                  className="text-input"
                  value={dateValue}
                  onChange={(e) => setDateValue(e.target.value)}
                />
              </div>
              <div className="input-row">
                <span className="input-label">Idő</span>
                <input
                  type="time"
                  className="text-input"
                  value={timeValue}
                  onChange={(e) => setTimeValue(e.target.value)}
                />
              </div>
            </div>

            <button
              type="button"
              className="now-btn"
              onClick={() => {
                setDateValue(getCurrentDateString());
                setTimeValue(getCurrentTimeString());
              }}
            >
              Most
            </button>
          </div>
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
