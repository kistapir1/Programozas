import { useState } from "react";
import Sidebar from "./components/Sidebar";
import "./index.css";

// Az API végpont base URL-je
const API_BASE = "http://localhost:8000";

// Egy menetrend-találat típusa (a backend által visszaadott mezők)
interface ScheduleResult {
  trip_id: number;
  route_short_name: string;
  route_long_name: string;
  transport_mode: string;
  operator: string;
  origin_station: string;
  departure_time: string;
  destination_station: string;
  arrival_time: string;
}

// Transport mode → Magyar szöveg + ikon
const MODE_LABELS: Record<string, { label: string; icon: string }> = {
  train:         { label: "Vonat",          icon: "🚆" },
  intercity_bus: { label: "Helyközi busz",  icon: "🚌" },
  local_bus:     { label: "Helyi busz",     icon: "🚍" },
};

function App() {
  const [results, setResults] = useState<ScheduleResult[]>([]);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [searched, setSearched] = useState(false);

  const handleSearch = async (params: {
    origin: string;
    destination: string;
    waypoints: string[];
    transport_modes: string[];
  }) => {
    if (!params.origin.trim() || !params.destination.trim()) {
      setError("Kérem adja meg az indulási pontot és a célt!");
      return;
    }

    setLoading(true);
    setError(null);
    setSearched(true);

    try {
      const response = await fetch(`${API_BASE}/api/search`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(params),
      });

      if (!response.ok) {
        const err = await response.json();
        throw new Error(err.detail ?? "Szerverhiba történt.");
      }

      const data = await response.json();
      setResults(data.results ?? []);
    } catch (e: unknown) {
      setError(e instanceof Error ? e.message : "Ismeretlen hiba.");
      setResults([]);
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="app-shell">
      {/* ── Bal oldal: keresőpanel ──────────────────────────────────────── */}
      <Sidebar onSearch={handleSearch} />

      {/* ── Jobb oldal: találatok ──────────────────────────────────────── */}
      <main className="main-content">
        {!searched && (
          <div className="placeholder-card">
            <h2>Menetrend eredmények</h2>
            <p>
              Adja meg az indulási pontot és a célt a bal oldali panelen, majd
              kattintson a <strong>Keresés</strong> gombra.
            </p>
          </div>
        )}

        {loading && (
          <div className="placeholder-card">
            <p>⏳ Keresés folyamatban…</p>
          </div>
        )}

        {error && (
          <div className="placeholder-card error-card">
            <p>⚠️ {error}</p>
          </div>
        )}

        {!loading && searched && !error && results.length === 0 && (
          <div className="placeholder-card">
            <h2>Nincs találat</h2>
            <p>Nem található menetrend a megadott feltételekkel. Próbáljon más útvonalat!</p>
          </div>
        )}

        {!loading && results.length > 0 && (
          <div className="results-list">
            <h2 className="results-title">
              {results.length} találat (max. 5)
            </h2>
            {results.map((r, idx) => {
              const mode = MODE_LABELS[r.transport_mode] ?? { label: r.transport_mode, icon: "🚏" };
              return (
                <div key={idx} className="result-card">
                  <div className="result-header">
                    <span className="result-icon">{mode.icon}</span>
                    <span className="result-route-name">{r.route_short_name}</span>
                    <span className="result-mode-badge">{mode.label}</span>
                  </div>
                  <p className="result-long-name">{r.route_long_name}</p>
                  <div className="result-times">
                    <div className="result-stop">
                      <span className="time">{r.departure_time}</span>
                      <span className="station">{r.origin_station}</span>
                    </div>
                    <span className="result-arrow">→</span>
                    <div className="result-stop">
                      <span className="time">{r.arrival_time}</span>
                      <span className="station">{r.destination_station}</span>
                    </div>
                  </div>
                  <p className="result-operator">🏢 {r.operator}</p>
                </div>
              );
            })}
          </div>
        )}
      </main>
    </div>
  );
}

export default App;
