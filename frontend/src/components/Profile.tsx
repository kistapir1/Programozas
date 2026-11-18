import { useEffect, useState } from "react";

const API_BASE = "http://localhost:8000";
const PASSWORD_MIN_LENGTH = 8;

// Ezeket az útvonalakat a backend tényleges végpontjaihoz kell igazítani.
const FRIENDS_API = {
  incoming: "/api/friends/requests/incoming",
  outgoing: "/api/friends/requests/outgoing",
  friends: "/api/friends",
  accept: (id: number | string) => `/api/friends/requests/${id}/accept`,
  reject: (id: number | string) => `/api/friends/requests/${id}`,
  cancel: (id: number | string) => `/api/friends/requests/${id}`,
  remove: (id: number | string) => `/api/friends/${id}`,
};

interface ProfileUser {
  username: string;
  email: string;
  created_at?: string;
}

interface ProfileProps {
  user: ProfileUser | null;
  accessToken: string | null;
  onBack?: () => void;
  onUsernameChanged?: (newUsername: string) => void;
}

interface PasswordValues {
  currentPassword: string;
  newPassword: string;
  newPasswordAgain: string;
}

interface FriendRequest {
  id: number;
  username: string;
}

interface Friend {
  id: number;
  username: string;
}

type ProfileTab = "profile" | "requests" | "friends";

async function parseErrorDetail(response: Response): Promise<string> {
  try {
    const data = await response.json();
    const detail = data.detail;
    if (typeof detail === "string") return detail;
    if (Array.isArray(detail)) {
      return detail.map((d: { msg?: string }) => d.msg ?? "Érvénytelen adat.").join(" ");
    }
    return "Ismeretlen hiba történt.";
  } catch {
    return "Ismeretlen hiba történt.";
  }
}

function Profile({ user, accessToken, onBack, onUsernameChanged }: ProfileProps) {
  const [activeTab, setActiveTab] = useState<ProfileTab>("profile");

  // Profiladatok
  const [displayedUsername, setDisplayedUsername] = useState(user?.username ?? "");
  const [usernameInput, setUsernameInput] = useState(user?.username ?? "");
  const [isEditingUsername, setIsEditingUsername] = useState(false);
  const [usernameError, setUsernameError] = useState<string | null>(null);
  const [usernameSuccess, setUsernameSuccess] = useState(false);
  const [usernameLoading, setUsernameLoading] = useState(false);

  const [showPasswordForm, setShowPasswordForm] = useState(false);
  const [passwordValues, setPasswordValues] = useState<PasswordValues>({
    currentPassword: "",
    newPassword: "",
    newPasswordAgain: "",
  });
  const [passwordError, setPasswordError] = useState<string | null>(null);
  const [passwordSuccess, setPasswordSuccess] = useState(false);
  const [passwordLoading, setPasswordLoading] = useState(false);

  // Barátok és kérelmek
  const [incomingRequests, setIncomingRequests] = useState<FriendRequest[]>([]);
  const [outgoingRequests, setOutgoingRequests] = useState<FriendRequest[]>([]);
  const [friends, setFriends] = useState<Friend[]>([]);
  const [friendsLoading, setFriendsLoading] = useState(false);
  const [friendsError, setFriendsError] = useState<string | null>(null);
  const [requestActionId, setRequestActionId] = useState<number | null>(null);
  const [friendActionId, setFriendActionId] = useState<number | null>(null);

  useEffect(() => {
    setDisplayedUsername(user?.username ?? "");
    setUsernameInput(user?.username ?? "");
  }, [user?.username]);

  const authHeaders = (): HeadersInit => ({
    Authorization: `Bearer ${accessToken}`,
    "Content-Type": "application/json",
  });

  const loadFriendData = async () => {
    if (!accessToken) return;
    setFriendsLoading(true);
    setFriendsError(null);

    try {
      const [incomingResponse, outgoingResponse, friendsResponse] = await Promise.all([
        fetch(`${API_BASE}${FRIENDS_API.incoming}`, { headers: authHeaders() }),
        fetch(`${API_BASE}${FRIENDS_API.outgoing}`, { headers: authHeaders() }),
        fetch(`${API_BASE}${FRIENDS_API.friends}`, { headers: authHeaders() }),
      ]);

      for (const response of [incomingResponse, outgoingResponse, friendsResponse]) {
        if (!response.ok) throw new Error(await parseErrorDetail(response));
      }

      const [incomingData, outgoingData, friendsData] = await Promise.all([
        incomingResponse.json(),
        outgoingResponse.json(),
        friendsResponse.json(),
      ]);

      // A backend közvetlen tömböt vagy { requests: [...] } / { friends: [...] } objektumot is visszaadhat.
      setIncomingRequests(Array.isArray(incomingData) ? incomingData : incomingData.requests ?? []);
      setOutgoingRequests(Array.isArray(outgoingData) ? outgoingData : outgoingData.requests ?? []);
      setFriends(Array.isArray(friendsData) ? friendsData : friendsData.friends ?? []);
    } catch (error) {
      setFriendsError(error instanceof Error ? error.message : "Nem sikerült betölteni az adatokat.");
    } finally {
      setFriendsLoading(false);
    }
  };

  useEffect(() => {
    if (activeTab === "requests" || activeTab === "friends") {
      void loadFriendData();
    }
    // A fülek váltásakor frissítjük a listákat.
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [activeTab, accessToken]);

  const handleUsernameCancel = () => {
    setUsernameInput(displayedUsername);
    setUsernameError(null);
    setIsEditingUsername(false);
  };

  const handleUsernameSave = async () => {
    setUsernameError(null);
    setUsernameSuccess(false);
    if (usernameInput.trim().length < 3) {
      setUsernameError("A felhasználónév legalább 3 karakter kell legyen.");
      return;
    }

    setUsernameLoading(true);
    try {
      const response = await fetch(`${API_BASE}/api/profile/username`, {
        method: "PATCH",
        headers: authHeaders(),
        body: JSON.stringify({ username: usernameInput.trim() }),
      });
      if (!response.ok) {
        setUsernameError(await parseErrorDetail(response));
        return;
      }

      const data = await response.json();
      const newUsername = data.username ?? usernameInput.trim();
      setDisplayedUsername(newUsername);
      setUsernameInput(newUsername);
      setUsernameSuccess(true);
      setIsEditingUsername(false);
      onUsernameChanged?.(newUsername);
    } catch {
      setUsernameError("Nem sikerült kapcsolódni a szerverhez.");
    } finally {
      setUsernameLoading(false);
    }
  };

  const newPasswordTooShort =
    passwordValues.newPassword.length > 0 &&
    passwordValues.newPassword.length < PASSWORD_MIN_LENGTH;
  const newPasswordsMismatch =
    passwordValues.newPasswordAgain.length > 0 &&
    passwordValues.newPassword !== passwordValues.newPasswordAgain;
  const isPasswordFormValid =
    passwordValues.currentPassword.length > 0 &&
    passwordValues.newPassword.length >= PASSWORD_MIN_LENGTH &&
    passwordValues.newPassword === passwordValues.newPasswordAgain;

  const handlePasswordCancel = () => {
    setPasswordValues({ currentPassword: "", newPassword: "", newPasswordAgain: "" });
    setPasswordError(null);
    setShowPasswordForm(false);
  };

  const handlePasswordSave = async () => {
    setPasswordError(null);
    setPasswordSuccess(false);
    setPasswordLoading(true);
    try {
      const response = await fetch(`${API_BASE}/api/profile/password`, {
        method: "PATCH",
        headers: authHeaders(),
        body: JSON.stringify({
          current_password: passwordValues.currentPassword,
          new_password: passwordValues.newPassword,
          newPasswordAgain: passwordValues.newPasswordAgain,
        }),
      });
      if (!response.ok) {
        setPasswordError(await parseErrorDetail(response));
        return;
      }
      setPasswordSuccess(true);
      setPasswordValues({ currentPassword: "", newPassword: "", newPasswordAgain: "" });
      setShowPasswordForm(false);
    } catch {
      setPasswordError("Nem sikerült kapcsolódni a szerverhez.");
    } finally {
      setPasswordLoading(false);
    }
  };

  const handleRequestAction = async (requestId: number, action: "accept" | "reject" | "cancel") => {
    setRequestActionId(requestId);
    setFriendsError(null);
    try {
      const url = action === "accept"
        ? `${API_BASE}${FRIENDS_API.accept(requestId)}`
        : `${API_BASE}${action === "reject" ? FRIENDS_API.reject(requestId) : FRIENDS_API.cancel(requestId)}`;
      const response = await fetch(url, {
        method: action === "accept" ? "POST" : "DELETE",
        headers: authHeaders(),
      });
      if (!response.ok) throw new Error(await parseErrorDetail(response));
      await loadFriendData();
    } catch (error) {
      setFriendsError(error instanceof Error ? error.message : "A művelet nem sikerült.");
    } finally {
      setRequestActionId(null);
    }
  };

  const handleRemoveFriend = async (friendId: number) => {
    setFriendActionId(friendId);
    setFriendsError(null);
    try {
      const response = await fetch(`${API_BASE}${FRIENDS_API.remove(friendId)}`, {
        method: "DELETE",
        headers: authHeaders(),
      });
      if (!response.ok) throw new Error(await parseErrorDetail(response));
      await loadFriendData();
    } catch (error) {
      setFriendsError(error instanceof Error ? error.message : "A barát eltávolítása nem sikerült.");
    } finally {
      setFriendActionId(null);
    }
  };

  const tabs: { id: ProfileTab; label: string }[] = [
    { id: "profile", label: "Profil" },
    { id: "requests", label: "Barát kérelmek" },
    { id: "friends", label: "Barátok" },
  ];

  return (
    <div className="profile-panel">
      {onBack && (
        <button type="button" className="auth-back-btn" onClick={onBack}>
          ← Vissza
        </button>
      )}

      {!user ? (
        <p>Nincs bejelentkezve felhasználó.</p>
      ) : (
        <>
          <nav className="profile-tabs" aria-label="Profil menü">
            {tabs.map((tab) => (
              <button
                key={tab.id}
                type="button"
                className={`profile-tab ${activeTab === tab.id ? "active" : ""}`}
                onClick={() => setActiveTab(tab.id)}
                aria-current={activeTab === tab.id ? "page" : undefined}
              >
                {tab.label}
              </button>
            ))}
          </nav>

          {activeTab === "profile" && (
            <section className="profile-tab-content">
              <div className="profile-row">
                <span className="input-label">Email</span>
                <span className="profile-value">{user.email}</span>
              </div>

              <div className="profile-divider" />

              <h3 className="profile-section-title">Felhasználónév</h3>
              <div className="profile-username-display">
                <span className="profile-value">{displayedUsername}</span>
                <button
                  type="button"
                  className="profile-edit-icon"
                  onClick={() => {
                    setUsernameInput(displayedUsername);
                    setUsernameError(null);
                    setUsernameSuccess(false);
                    setIsEditingUsername((editing) => !editing);
                  }}
                  aria-label="Felhasználónév szerkesztése"
                  title="Felhasználónév szerkesztése"
                >
                  ✏️
                </button>
              </div>

              {isEditingUsername && (
                <div className="profile-edit-form">
                  <div className="input-row">
                    <label className="input-label" htmlFor="profile-username-input">
                      Új felhasználónév
                    </label>
                    <input
                      id="profile-username-input"
                      type="text"
                      className="text-input"
                      value={usernameInput}
                      onChange={(e) => setUsernameInput(e.target.value)}
                    />
                  </div>
                  {usernameError && <p className="auth-error">{usernameError}</p>}
                  <div className="profile-form-actions">
                    <button type="button" className="search-btn" onClick={handleUsernameSave} disabled={usernameLoading}>
                      {usernameLoading ? "Mentés…" : "Mentés"}
                    </button>
                    <button type="button" className="profile-cancel-btn" onClick={handleUsernameCancel} disabled={usernameLoading}>
                      Mégse
                    </button>
                  </div>
                </div>
              )}
              {usernameSuccess && <p className="field-success">✅ A felhasználónév módosítva.</p>}

              <div className="profile-divider" />

              <h3 className="profile-section-title">Jelszó</h3>
              {!showPasswordForm ? (
                <>
                  <button
                    type="button"
                    className="search-btn"
                    onClick={() => {
                      setPasswordError(null);
                      setPasswordSuccess(false);
                      setShowPasswordForm(true);
                    }}
                  >
                    Jelszó módosítása
                  </button>
                  {passwordSuccess && <p className="field-success">✅ A jelszó sikeresen módosítva.</p>}
                </>
              ) : (
                <div className="profile-edit-form">
                  <div className="input-row">
                    <label className="input-label" htmlFor="current-password">Jelenlegi jelszó</label>
                    <input id="current-password" type="password" className="text-input" value={passwordValues.currentPassword}
                      onChange={(e) => setPasswordValues((v) => ({ ...v, currentPassword: e.target.value }))} />
                  </div>
                  <div className="input-row">
                    <label className="input-label" htmlFor="new-password">Új jelszó</label>
                    <input id="new-password" type="password" className="text-input" value={passwordValues.newPassword}
                      onChange={(e) => setPasswordValues((v) => ({ ...v, newPassword: e.target.value }))} />
                    {newPasswordTooShort && <p className="field-warning">Az új jelszónak legalább {PASSWORD_MIN_LENGTH} karakterből kell állnia.</p>}
                  </div>
                  <div className="input-row">
                    <label className="input-label" htmlFor="new-password-again">Új jelszó újra</label>
                    <input id="new-password-again" type="password" className="text-input" value={passwordValues.newPasswordAgain}
                      onChange={(e) => setPasswordValues((v) => ({ ...v, newPasswordAgain: e.target.value }))} />
                    {newPasswordsMismatch && <p className="field-warning">A két új jelszó nem egyezik.</p>}
                  </div>
                  {passwordError && <p className="auth-error">{passwordError}</p>}
                  <div className="profile-form-actions">
                    <button type="button" className="search-btn" onClick={handlePasswordSave} disabled={passwordLoading || !isPasswordFormValid}>
                      {passwordLoading ? "Mentés…" : "Jelszó módosítása"}
                    </button>
                    <button type="button" className="profile-cancel-btn" onClick={handlePasswordCancel} disabled={passwordLoading}>Mégse</button>
                  </div>
                </div>
              )}
            </section>
          )}

          {activeTab === "requests" && (
            <section className="profile-tab-content">
              <h3 className="profile-section-title">Beérkező kérelmek</h3>
              {friendsLoading ? <p>Beérkező kérelmek betöltése…</p> :
                incomingRequests.length === 0 ? <p className="profile-empty">Nincs beérkező barátkérelmed.</p> :
                <div className="profile-list">
                  {incomingRequests.map((request) => (
                    <div className="profile-list-item" key={request.id}>
                      <span className="profile-value">{request.username}</span>
                      <div className="profile-list-actions">
                        <button type="button" className="friend-accept-btn" title="Elfogadás" aria-label="Kérelem elfogadása"
                          disabled={requestActionId === request.id} onClick={() => void handleRequestAction(request.id, "accept")}>✓</button>
                        <button type="button" className="friend-reject-btn" title="Elutasítás" aria-label="Kérelem elutasítása"
                          disabled={requestActionId === request.id} onClick={() => void handleRequestAction(request.id, "reject")}>✕</button>
                      </div>
                    </div>
                  ))}
                </div>
              }

              <div className="profile-divider" />
              <h3 className="profile-section-title">Kimenő kérelmek</h3>
              {friendsLoading ? <p>Kimenő kérelmek betöltése…</p> :
                outgoingRequests.length === 0 ? <p className="profile-empty">Nincs függőben lévő kimenő kérelmed.</p> :
                <div className="profile-list">
                  {outgoingRequests.map((request) => (
                    <div className="profile-list-item" key={request.id}>
                      <span className="profile-value">{request.username}</span>
                      <button type="button" className="friend-cancel-btn" disabled={requestActionId === request.id}
                        onClick={() => void handleRequestAction(request.id, "cancel")}>Visszavonás</button>
                    </div>
                  ))}
                </div>
              }
              {friendsError && <p className="auth-error">{friendsError}</p>}
            </section>
          )}

          {activeTab === "friends" && (
            <section className="profile-tab-content">
              <h3 className="profile-section-title">Barátaim</h3>
              {friendsLoading ? <p>Barátlista betöltése…</p> :
                friends.length === 0 ? <p className="profile-empty">Még nincsenek felvett barátaid.</p> :
                <div className="profile-list">
                  {friends.map((friend) => (
                    <div className="profile-list-item" key={friend.id}>
                      <span className="profile-value">{friend.username}</span>
                      <button type="button" className="friend-remove-btn" disabled={friendActionId === friend.id}
                        onClick={() => void handleRemoveFriend(friend.id)}>Eltávolítás</button>
                    </div>
                  ))}
                </div>
              }
              {friendsError && <p className="auth-error">{friendsError}</p>}
            </section>
          )}
        </>
      )}
    </div>
  );
}

export default Profile;
