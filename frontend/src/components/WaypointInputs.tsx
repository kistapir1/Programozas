import { useState } from "react";

interface WaypointInputsProps {
  originLabel?: string;
  waypointLabel?: string;
  destinationLabel?: string;
  onValuesChange?: (values: { origin: string; waypoints: string[]; destination: string }) => void;
}

function WaypointInputs({
  originLabel = "Indulási pont",
  waypointLabel = "Közbenső megálló",
  destinationLabel = "Cél",
  onValuesChange,
}: WaypointInputsProps) {
  const [origin, setOrigin] = useState("");
  const [waypoints, setWaypoints] = useState<string[]>([]);
  const [destination, setDestination] = useState("");

  const notify = (
    newOrigin: string,
    newWaypoints: string[],
    newDest: string
  ) => {
    onValuesChange?.({
      origin: newOrigin,
      waypoints: newWaypoints,
      destination: newDest,
    });
  };

  const addWaypoint = () => {
    const updated = [...waypoints, ""];
    setWaypoints(updated);
    notify(origin, updated, destination);
  };

  const removeWaypoint = (index: number) => {
    const updated = waypoints.filter((_, i) => i !== index);
    setWaypoints(updated);
    notify(origin, updated, destination);
  };

  const updateWaypoint = (index: number, value: string) => {
    const updated = waypoints.map((w, i) => (i === index ? value : w));
    setWaypoints(updated);
    notify(origin, updated, destination);
  };

  return (
    <div className="input-section">
      {/* Origin */}
      <div className="input-row">
        <span className="input-label">{originLabel}</span>
        <input
          className="text-input"
          type="text"
          placeholder={originLabel}
          value={origin}
          onChange={(e) => {
            setOrigin(e.target.value);
            notify(e.target.value, waypoints, destination);
          }}
        />
      </div>

      {/* Dynamic waypoints */}
      {waypoints.map((wp, i) => (
        <div key={i} className="input-row">
          <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center" }}>
            <span className="input-label">{waypointLabel} {i + 1}</span>
            <button
              className="remove-row-btn"
              onClick={() => removeWaypoint(i)}
              title="Megálló törlése"
              aria-label={`Megálló ${i + 1} törlése`}
            >
              ✕
            </button>
          </div>
          <input
            className="text-input"
            type="text"
            placeholder={`${waypointLabel} ${i + 1}`}
            value={wp}
            onChange={(e) => updateWaypoint(i, e.target.value)}
          />
        </div>
      ))}

      {/* Plus button — always above the destination field */}
      <div className="add-row-wrapper">
        <button
          className="add-row-btn"
          onClick={addWaypoint}
          title="Közbenső megálló hozzáadása"
          aria-label="Közbenső megálló hozzáadása"
        >
          +
        </button>
      </div>

      {/* Destination — always last */}
      <div className="destination-section">
        <span className="input-label">{destinationLabel}</span>
        <input
          className="text-input"
          type="text"
          placeholder={destinationLabel}
          value={destination}
          onChange={(e) => {
            setDestination(e.target.value);
            notify(origin, waypoints, e.target.value);
          }}
        />
      </div>
    </div>
  );
}

export default WaypointInputs;
