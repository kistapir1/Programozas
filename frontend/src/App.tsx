import Sidebar from "./components/Sidebar";
import "./index.css";

function App() {
  const handleSearch = (params: unknown) => {
    // TODO: connect to Python backend API
    console.log("Search triggered with params:", params);
  };

  return (
    <div className="app-shell">
      {/* ── Left side: Main menu panel ────────────────────────────────── */}
      <Sidebar onSearch={handleSearch} />

      {/* ── Right side: Results / content area ───────────────────────── */}
      <main className="main-content">
        <div className="placeholder-card">
          <h2>Menetrend eredmények</h2>
          <p>
            Adja meg az indulási pontot és a célt a bal oldali panelen, majd
            kattintson a <strong>Keresés</strong> gombra.
          </p>
        </div>
      </main>
    </div>
  );
}

export default App;
