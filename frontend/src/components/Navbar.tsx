import { useState } from "react";

interface UserSearchHit {
  user_id: number;
  username: string;
}

interface NavbarProps {
  onAuthClick?: () => void;
  isLoggedIn?: boolean;
  onLogout?: () => void;
  onProfileClick?: () => void;
  onSavedRoutesClick?: () => void;
  onUserSearch?: (query: string) => void;
  userSearchQuery?: string;
  userSearchResults?: UserSearchHit[];
  userSearchLoading?: boolean;
  userSearchComplete?: boolean;
  userSearchError?: string | null;
}

function Navbar({ 
  onAuthClick,
  isLoggedIn,
  onLogout,
  onProfileClick,
  onSavedRoutesClick,
  onUserSearch,
  userSearchQuery = "",
  userSearchResults = [],
  userSearchLoading = false,
  userSearchComplete = false,
  userSearchError = null,
}: NavbarProps) {
  const [searchFocused, setSearchFocused] = useState(false);
  const showSearchDropdown =
    searchFocused &&
    userSearchQuery.trim().length > 0 &&
    (userSearchLoading || userSearchError !== null || userSearchComplete);

  return (
    <nav className="top-navbar">
      <span className="nav-brand">Menetrend kereső</span>

      {isLoggedIn ? (
        <div className="nav-user-area">
          <div className="nav-search-wrapper">
            <input
              type="text"
              className="nav-search"
              placeholder="Felhasználó keresése…"
              value={userSearchQuery}
              maxLength={50}
              autoComplete="off"
              aria-label="Felhasználó keresése"
              aria-expanded={showSearchDropdown}
              aria-controls="user-search-results"
              onFocus={() => setSearchFocused(true)}
              onBlur={() => setSearchFocused(false)}
              onChange={(e) => onUserSearch?.(e.target.value)}
            />
            {showSearchDropdown && (
              <div id="user-search-results" className="nav-search-dropdown">
                {userSearchLoading ? (
                  <p className="nav-search-message" role="status">Keresés…</p>
                ) : userSearchError ? (
                  <p className="nav-search-message nav-search-error" role="alert">
                    {userSearchError}
                  </p>
                ) : userSearchResults.length > 0 ? (
                  <ul aria-label="Felhasználó keresési találatok">
                    {userSearchResults.map((user) => (
                      <li key={user.user_id}>{user.username}</li>
                    ))}
                  </ul>
                ) : (
                  <p className="nav-search-message" role="status">Nincs találat.</p>
                )}
              </div>
            )}
          </div>

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