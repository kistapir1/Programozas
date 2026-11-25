import { useEffect, useState } from "react";
import Sidebar from "./components/Sidebar";
import Navbar from "./components/Navbar";
import AuthPanel, {type AuthResponse} from "./components/AuthPanel";
import Profile from "./components/Profile";
import RouteMapModal from "./components/RouteMapModal";
import "./index.css";

// Az API végpont base URL-je
const API_BASE = "http://localhost:8000";

interface Leg {
  route_short_name: string;
  route_long_name: string;
  transport_mode: string;
  operator: string;
  origin_station: string;
  origin_lat?: number | null;
  origin_lon?: number | null;
  departure_time: string;
  destination_station: string;
  destination_lat?: number | null;
  destination_lon?: number | null;
  arrival_time: string;
  walk_seconds_before?: number;
  transfer_station?: string;
  bikes_allowed?: number;
  wheelchair_accessible?: number;
  shape_points?: [number, number][];
}

// Egy menetrend-találat típusa (a backend által visszaadott mezők)
interface ScheduleResult {
  trip_id: number | string;
  route_short_name: string;
  route_long_name: string;
  transport_mode: string;
  operator: string;
  origin_station: string;
  origin_lat?: number | null;
  origin_lon?: number | null;
  departure_time: string;
  destination_station: string;
  destination_lat?: number | null;
  destination_lon?: number | null;
  arrival_time: string;
  transfers?: number;
  walk_seconds_before?: number;
  transfer_station?: string;
  bikes_allowed?: number;
  wheelchair_accessible?: number;
  shape_points?: [number, number][];
  legs?: Leg[];
}

interface SearchParams {
  origin: string;
  destination: string;
  waypoints: string[];
  transport_modes: string[];
  max_transfers: number;
  min_transfer_time?: number;
  bikes_allowed?: boolean;
  wheelchair_accessible?: boolean;
  wheelchair_boarding?: boolean;
  time_mode: "departure" | "arrival";
  date: string;
  time: string;
}

interface UserSearchHit {
  user_id: number;
  username: string;
}

interface UserSearchResponse {
  results: UserSearchHit[];
}

// Transport mode → Magyar szöveg + ikon (közvetlenül az adatbázisbeli route_types.type_name szerint)
const MODE_LABELS: Record<string, { label: string; icon: string }> = {
  "Metró":                 { label: "Metró",     icon: "🚇" },
  "Villamos":              { label: "Villamos",  icon: "🚋" },
  "Busz":                  { label: "Busz",      icon: "🚌" },
  "Trolibusz":             { label: "Trolibusz", icon: "🚎" },
  "Elővárosi vasút / HÉV": { label: "HÉV",       icon: "🚆" },
  "Komp":                  { label: "Komp",      icon: "⛴️" },
  "Vasút":                 { label: "Vasút",     icon: "🚆" },
};

function formatDisplayTime(time: string): string {
  const match = /^(\d{1,2}):(\d{2})(?::\d{2}(?:\.\d+)?)?$/.exec(time);
  return match ? `${match[1].padStart(2, "0")}:${match[2]}` : time;
}

function App() {
  const [results, setResults] = useState<ScheduleResult[]>([]);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [searched, setSearched] = useState(false);
  const [showAuth, setShowAuth] = useState(false);
  const [showProfile, setShowProfile] = useState(false);
  const [mapRoute, setMapRoute] = useState<ScheduleResult | null>(null);
  const [accessToken, setAccessToken] = useState<string | null>(
    () => localStorage.getItem("access_token")
  );
  const [currentUser, setCurrentUser] = useState<AuthResponse["user"] | null>(null);
  const [userSearchQuery, setUserSearchQuery] = useState("");
  const [userSearchResults, setUserSearchResults] = useState<UserSearchHit[]>([]);
  const [userSearchLoading, setUserSearchLoading] = useState(false);
  const [userSearchComplete, setUserSearchComplete] = useState(false);
  const [userSearchError, setUserSearchError] = useState<string | null>(null);
  const [friendRequestStates, setFriendRequestStates] = useState<Record<number, "sending" | "sent">>({});
  const [friendRequestError, setFriendRequestError] = useState<string | null>(null);

  useEffect(() => {
    const query = userSearchQuery.trim();
    if (!accessToken || !query) {
      setUserSearchResults([]);
      setUserSearchLoading(false);
      setUserSearchComplete(false);
      setUserSearchError(null);
      return;
    }

    const controller = new AbortController();
    setUserSearchResults([]);
    setUserSearchLoading(true);
    setUserSearchComplete(false);
    setUserSearchError(null);

    const timeoutId = window.setTimeout(async () => {
      try {
        const searchParams = new URLSearchParams({ q: query });
        const response = await fetch(`${API_BASE}/api/users/search?${searchParams}`, {
          headers: { Authorization: `Bearer ${accessToken}` },
          signal: controller.signal,
        });

        if (!response.ok) {
          throw new Error(
            response.status === 401
              ? "A munkamenet lejárt. Kérjük, jelentkezzen be újra."
              : `A felhasználókeresés nem sikerült (HTTP ${response.status}).`
          );
        }

        const data: UserSearchResponse = await response.json();
        setUserSearchResults(data.results);
        setUserSearchComplete(true);
      } catch (e: unknown) {
        if (controller.signal.aborted) return;
        setUserSearchError(e instanceof Error ? e.message : "Ismeretlen hiba történt.");
      } finally {
        if (!controller.signal.aborted) {
          setUserSearchLoading(false);
        }
      }
    }, 300);

    return () => {
      window.clearTimeout(timeoutId);
      controller.abort();
    };
  }, [accessToken, userSearchQuery]);

  const handleLoginSuccess = (auth: AuthResponse) => {
    localStorage.setItem("access_token", auth.access_token);
    setAccessToken(auth.access_token);
    setCurrentUser(auth.user);
    setFriendRequestStates({});
    setFriendRequestError(null);
    setShowAuth(false);
  };

  const handleRegisterSuccess = (auth: AuthResponse) => {};

  // Kijelentkezés
  const handleLogout = () => {
    localStorage.removeItem("access_token");
    setAccessToken(null);
    setCurrentUser(null);
    setUserSearchQuery("");
    setFriendRequestStates({});
    setFriendRequestError(null);
    setShowProfile(false);
  };

  const handleSendFriendRequest = async (target: UserSearchHit) => {
    if (!accessToken) return;
    setFriendRequestStates((states) => ({ ...states, [target.user_id]: "sending" }));
    setFriendRequestError(null);

    try {
      const response = await fetch(`${API_BASE}/api/friends/requests/${target.user_id}`, {
        method: "POST",
        headers: { Authorization: `Bearer ${accessToken}` },
      });
      if (!response.ok) {
        const data = await response.json().catch(() => null);
        throw new Error(
          typeof data?.detail === "string"
            ? data.detail
            : `A barátkérelem küldése nem sikerült (HTTP ${response.status}).`
        );
      }
      setFriendRequestStates((states) => ({ ...states, [target.user_id]: "sent" }));
    } catch (e: unknown) {
      setFriendRequestStates((states) => {
        const nextStates = { ...states };
        delete nextStates[target.user_id];
        return nextStates;
      });
      setFriendRequestError(e instanceof Error ? e.message : "Ismeretlen hiba történt.");
    }
  };

  const handleSearch = async (params: SearchParams) => {
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
    <>
      <Navbar 
        onAuthClick={() => setShowAuth(true)}
        isLoggedIn={Boolean(accessToken)}
        onLogout={handleLogout}
        onProfileClick={() => setShowProfile(true)}
        onSavedRoutesClick={() => console.log("Mentett útvonalak – TODO")}
        userSearchQuery={userSearchQuery}
        userSearchResults={userSearchResults}
        userSearchLoading={userSearchLoading}
        userSearchComplete={userSearchComplete}
        userSearchError={userSearchError}
        friendRequestStates={friendRequestStates}
        friendRequestError={friendRequestError}
        onSendFriendRequest={handleSendFriendRequest}
        onUserSearch={setUserSearchQuery}
      />
        {showAuth ? (
          <div className="app-shell">
            <AuthPanel 
              onBack={() => setShowAuth(false)} 
              onLogin={handleLoginSuccess}
              onRegister={handleRegisterSuccess}
            />
          </div>
        ): showProfile ? (
          <div className="app-shell">
            <Profile user={currentUser} accessToken={accessToken} onBack={() => setShowProfile(false)} />
          </div>
        ):(
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
              <p>Nincs a kritériumoknak megfelelő találat.</p>
            </div>
          )}

          {!loading && results.length > 0 && (
            <div className="results-list">
              <h2 className="results-title">
                {results.length} találat
              </h2>
              {results.map((r, idx) => {
                const transfersCount = r.transfers ?? (r.legs ? r.legs.length - 1 : 0);
                const legsToRender = r.legs && r.legs.length > 0 ? r.legs : [r];
                const departureTime = formatDisplayTime(r.departure_time);
                const arrivalTime = formatDisplayTime(r.arrival_time);

                return (
                  <div key={idx} className="result-card">
                    {/* Összesített fejléc (különösen hasznos átszállás esetén) */}
                    <div className="result-journey-summary">
                      <div className="journey-total-time">
                        <span className="journey-time-main">{departureTime} → {arrivalTime}</span>
                        <span className="journey-station-sub">{r.origin_station} → {r.destination_station}</span>
                      </div>
                      <div className="journey-badges">
                        {r.bikes_allowed === 1 && <span className="accessibility-badge" title="Kerékpárszállítás megengedett">🚲</span>}
                        {r.wheelchair_accessible === 1 && <span className="accessibility-badge" title="Akadálymentes jármű">♿</span>}
                        <span className={`result-transfer-badge ${transfersCount === 0 ? "direct" : "transfer"}`}>
                          {transfersCount === 0 ? "Közvetlen" : `${transfersCount} átszállás`}
                        </span>
                      </div>
                      <button
                        type="button"
                        className="open-map-btn"
                        onClick={() => setMapRoute(r)}
                      >
                        🗺️ Térkép megnyitása
                      </button>
                    </div>

                    {/* Szakaszok (legs) listázása */}
                    <div className="result-legs-list">
                      {legsToRender.map((leg, legIdx) => {
                        const mode = MODE_LABELS[leg.transport_mode] ?? { label: leg.transport_mode, icon: "🚏" };
                        const legDepartureTime = formatDisplayTime(leg.departure_time);
                        const legArrivalTime = formatDisplayTime(leg.arrival_time);
                        return (
                          <div key={legIdx} className="result-leg-wrapper">
                            {legIdx > 0 && (
                              <div className="result-transfer-divider">
                                <span className="transfer-icon">🔄</span>
                                <span className="transfer-text">
                                  Átszállás: <strong>{leg.transfer_station || leg.origin_station}</strong>
                                  {leg.walk_seconds_before ? ` (~${Math.round(leg.walk_seconds_before / 60)} perc séta / csatlakozás)` : ""}
                                </span>
                              </div>
                            )}

                            <div className="result-leg-item">
                              <div className="result-header">
                                <span className="result-icon">{mode.icon}</span>
                                <span className="result-route-name">{leg.route_short_name}</span>
                                {leg.bikes_allowed === 1 && (
                                  <span className="accessibility-icon" title="Kerékpárszállítás megengedett">🚲</span>
                                )}
                                {leg.wheelchair_accessible === 1 && (
                                  <span className="accessibility-icon" title="Akadálymentes jármű">♿</span>
                                )}
                                <span className="result-mode-badge">{mode.label}</span>
                              </div>
                              <p className="result-long-name">{leg.route_long_name}</p>
                              <div className="result-times">
                                <div className="result-stop">
                                  <span className="time">{legDepartureTime}</span>
                                  <span className="station">{leg.origin_station}</span>
                                </div>
                                <span className="result-arrow">→</span>
                                <div className="result-stop">
                                  <span className="time">{legArrivalTime}</span>
                                  <span className="station">{leg.destination_station}</span>
                                </div>
                              </div>
                              <p className="result-operator">🏢 {leg.operator}</p>
                            </div>
                          </div>
                        );
                      })}
                    </div>
                  </div>
                );
              })}
            </div>
          )}
        </main>
      </div>
      )}
      <RouteMapModal route={mapRoute} onClose={() => setMapRoute(null)} />
    </>
  );
}

export default App;
