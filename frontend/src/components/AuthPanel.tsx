import { useState } from "react";

interface LoginValues {
  identifier: string; // Email vagy felhasználónév
  password: string;
}

interface RegisterValues {
  username: string;
  email: string;
  password: string;
  passwordAgain: string;
}

interface AuthPanelProps {
  onLogin?: (values: LoginValues) => void;
  onRegister?: (values: RegisterValues) => void;
  onBack?: () => void;
}

function AuthPanel({ onLogin, onRegister, onBack }: AuthPanelProps) {
  const [loginValues, setLoginValues] = useState<LoginValues>({
    identifier: "",
    password: "",
  });

  const [registerValues, setRegisterValues] = useState<RegisterValues>({
    username: "",
    email: "",
    password: "",
    passwordAgain: "",
  });

  const handleLogin = () => {
    onLogin?.(loginValues);
  };

  const handleRegister = () => {
    onRegister?.(registerValues);
  };

  return (
    <div className="auth-panel">
      {onBack && (
        <button type="button" className="auth-back-btn" onClick={onBack}>
          ← Vissza
        </button>
      )}

      <div className="auth-split">
        {/* ── Bal oldal: Belépés ──────────────────────────────────────── */}
        <div className="auth-col">
          <h2 className="auth-col-title">Belépés</h2>

          <div className="input-row">
            <span className="input-label">Email/Felhasználónév</span>
            <input
              type="text"
              className="text-input"
              value={loginValues.identifier}
              onChange={(e) =>
                setLoginValues((v) => ({ ...v, identifier: e.target.value }))
              }
            />
          </div>

          <div className="input-row">
            <span className="input-label">Jelszó</span>
            <input
              type="password"
              className="text-input"
              value={loginValues.password}
              onChange={(e) =>
                setLoginValues((v) => ({ ...v, password: e.target.value }))
              }
            />
          </div>

          <button type="button" className="search-btn" onClick={handleLogin}>
            Belépés
          </button>
        </div>

        <div className="auth-divider" />

        {/* ── Jobb oldal: Regisztráció ───────────────────────────────── */}
        <div className="auth-col">
          <h2 className="auth-col-title">Regisztráció</h2>

          <div className="input-row">
            <span className="input-label">Felhasználónév</span>
            <input
              type="text"
              className="text-input"
              value={registerValues.username}
              onChange={(e) =>
                setRegisterValues((v) => ({ ...v, username: e.target.value }))
              }
            />
          </div>

          <div className="input-row">
            <span className="input-label">Email</span>
            <input
              type="email"
              className="text-input"
              value={registerValues.email}
              onChange={(e) =>
                setRegisterValues((v) => ({ ...v, email: e.target.value }))
              }
            />
          </div>

          <div className="input-row">
            <span className="input-label">Jelszó</span>
            <input
              type="password"
              className="text-input"
              value={registerValues.password}
              onChange={(e) =>
                setRegisterValues((v) => ({ ...v, password: e.target.value }))
              }
            />
          </div>

          <div className="input-row">
            <span className="input-label">Jelszó újra</span>
            <input
              type="password"
              className="text-input"
              value={registerValues.passwordAgain}
              onChange={(e) =>
                setRegisterValues((v) => ({ ...v, passwordAgain: e.target.value }))
              }
            />
          </div>

          <button type="button" className="search-btn" onClick={handleRegister}>
            Regisztráció
          </button>
        </div>
      </div>
    </div>
  );
}

export default AuthPanel;
