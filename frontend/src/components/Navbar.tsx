import { useState } from "react";

interface NavbarProps {
  onAuthClick?: () => void;
  isLoggedIn?: boolean;
  onLogout?: () => void;
  onProfileClick?: () => void;
  onSavedRoutesClick?: () => void;
  onUserSearch?: (query: string) => void;
}

function Navbar({ 
  onAuthClick,
  isLoggedIn,
  onLogout,
  onProfileClick,
  onSavedRoutesClick,
  onUserSearch,
}: NavbarProps) {
  const [searchQuery, setSearchQuery] = useState("");

  const handleSearchChange = (value: string) => {
    setSearchQuery(value);
    onUserSearch?.(value);
  };

  return (
    <nav className="top-navbar">
      <span className="nav-brand">Menetrend kereső</span>

      {isLoggedIn ? (
        <div className="nav-user-area">
          <input
            type="text"
            className="nav-search"
            placeholder="Felhasználó keresése…"
            value={searchQuery}
            onChange={(e) => handleSearchChange(e.target.value)}
          />

          <button type="button" className="nav-icon-btn" onClick={onSavedRoutesClick}>
            ⭐ Mentett útvonalak
          </button>

          <button type="button" className="nav-icon-btn" onClick={onProfileClick}>
            👤 Profil
          </button>

          <button type="button" className="nav-logout-btn" onClick={onLogout} aria-label="Kijelentkezés">
            ⏻
          </button>
        </div>
      ) : (
        <span className="nav-link auth-link" onClick={onAuthClick}>
          Belépés/Regisztráció
        </span>
      )}
    </nav>
  );
}

export default Navbar;