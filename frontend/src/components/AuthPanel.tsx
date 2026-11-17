import { useState } from "react";

const API_BASE = "http://localhost:8000";
const PASSWORD_MIN_LENGTH = 8;

export interface AuthUser {
  user_id: number;
  username: string;
  email: string;
  created_at?: string;
}

export interface AuthResponse {
  access_token: string;
  token_type: string;
  expires_in: number;
  user: AuthUser;
}

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
  onLogin?: (values: AuthResponse) => void;
  onRegister?: (values: AuthResponse) => void;
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

  const [loginError, setLoginError] = useState<string | null>(null);
  const [registerError, setRegisterError] = useState<string | null>(null);
  const [loginLoading, setLoginLoading] = useState(false);
  const [registerLoading, setRegisterLoading] = useState(false);
  const [registerSuccess, setRegisterSuccess] = useState(false);

  const passwordTooShort =
  registerValues.password.length > 0 &&
  registerValues.password.length < PASSWORD_MIN_LENGTH;

  const passwordsMismatch =
    registerValues.passwordAgain.length > 0 &&
    registerValues.password !== registerValues.passwordAgain;

  const isRegisterFormValid =
    registerValues.username.trim().length >= 3 &&
    registerValues.email.trim().length > 0 &&
    registerValues.password.length >= PASSWORD_MIN_LENGTH &&
    registerValues.password === registerValues.passwordAgain;

  async function parseErrorDetail(response: Response): Promise<string> {
    try {
      const data = await response.json();
      const detail = data.detail;

      if (typeof detail === "string") {
        return detail;
      }

      if (Array.isArray(detail)) {
        return detail
          .map((d: { msg?: string }) => d.msg ?? "Érvénytelen adat.")
          .join(" ");
      }

      return data.detail ?? "Ismeretlen hiba történt.";
    } catch {
      return "Ismeretlen hiba történt.";
    }
  }

  const handleLogin = async () => {
    setLoginError(null);
    setLoginLoading(true);
    try {
      const response = await fetch(`${API_BASE}/api/auth/login`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(loginValues),
      });
      if (!response.ok) {
        setLoginError(await parseErrorDetail(response));
        return;
      }
      const data: AuthResponse = await response.json();
      onLogin?.(data);
    } catch {
      setLoginError("Nem sikerült kapcsolódni a szerverhez.");
    } finally {
      setLoginLoading(false);
    }
  };

  const handleRegister = async () => {
    setRegisterError(null);
    setRegisterSuccess(false);
    setRegisterLoading(true);
    try {
      const response = await fetch(`${API_BASE}/api/auth/register`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(registerValues),
      });
      if (!response.ok) {
        setRegisterError(await parseErrorDetail(response));
        return;
      }
      const data: AuthResponse = await response.json();
      setRegisterSuccess(true);
      setRegisterValues({ username: "", email: "", password: "", passwordAgain: "" });
      onRegister?.(data);
    } catch {
      setRegisterError("Nem sikerült kapcsolódni a szerverhez.");
    } finally {
      setRegisterLoading(false);
    }
  };

  return (
    <div className="auth-panel">
      {onBack && (
        <button type="button" className="auth-back-btn" onClick={onBack}>
          ← Vissza
        </button>
      )}

      {registerSuccess && (
        <div className="auth-success-banner">
          <span>✅ Sikeres regisztráció! Most már bejelentkezhet a bal oldali űrlapon.</span>
          <button
            type="button"
            className="auth-success-close"
            onClick={() => setRegisterSuccess(false)}
            aria-label="Bezárás"
          >
            ×
          </button>
        </div>
      )}

<div className="auth-split">
        {/* ── Bal oldal: Belépés ──────────────────────────────────────── */}
        <div className="auth-col">
          <h2 className="auth-col-title">Belépés</h2>

          <div className="input-row">
            <span className="input-label">Email</span>
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

          {loginError && <p className="auth-error">{loginError}</p>}
          <button type="button" className="search-btn" onClick={handleLogin} disabled={loginLoading}>
            {loginLoading ? "Belépés…" : "Belépés"}
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
            {passwordTooShort && (
              <p className="field-warning">
                A jelszónak legalább {PASSWORD_MIN_LENGTH} karakterből kell állnia.
              </p>
            )}
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
            {passwordsMismatch && (
              <p className="field-warning">
                A jelszavak nem egyeznek meg.
              </p>
            )}
          </div>

          {registerError && <p className="auth-error">{registerError}</p>}
          <button type="button" className="search-btn" onClick={handleRegister} disabled={registerLoading || !isRegisterFormValid}>
            {registerLoading ? "Regisztráció…" : "Regisztráció"}
          </button>
        </div>
      </div>
    </div>
  );
}

export default AuthPanel;
