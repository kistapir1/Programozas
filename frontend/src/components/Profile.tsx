interface ProfileUser {
  username: string;
  email: string;
  created_at?: string;
}

interface ProfileProps {
  user: ProfileUser | null;
  onBack?: () => void;
}

function Profile({ user, onBack }: ProfileProps) {
  return (
    <div className="profile-panel">
      {onBack && (
        <button type="button" className="auth-back-btn" onClick={onBack}>
          ← Vissza
        </button>
      )}

      <h2 className="auth-col-title">Profil</h2>

      {user ? (
        <div className="profile-details">
          <div className="profile-row">
            <span className="input-label">Felhasználónév</span>
            <span className="profile-value">{user.username}</span>
          </div>

          <div className="profile-row">
            <span className="input-label">Email</span>
            <span className="profile-value">{user.email}</span>
          </div>
        </div>
      ) : (
        <p>Nincs bejelentkezve felhasználó.</p>
      )}
    </div>
  );
}

export default Profile;
