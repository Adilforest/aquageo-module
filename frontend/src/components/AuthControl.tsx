import { useState } from "react";
import { useTranslation } from "react-i18next";

import { ApiError } from "../api/client";
import { useAuth } from "../auth/AuthContext";

export default function AuthControl() {
  const { t } = useTranslation();
  const { user, login, logout } = useAuth();
  const [open, setOpen] = useState(false);
  const [username, setUsername] = useState("");
  const [password, setPassword] = useState("");
  const [error, setError] = useState("");
  const [busy, setBusy] = useState(false);

  if (user) {
    return (
      <div className="auth-control">
        <span className="auth-user">
          {user.username} · <b>{t(`roles.${user.role}`, { defaultValue: user.role })}</b>
        </span>
        <button className="auth-btn" onClick={logout}>
          {t("auth.logout")}
        </button>
      </div>
    );
  }

  const submit = async (e: React.FormEvent) => {
    e.preventDefault();
    setBusy(true);
    setError("");
    try {
      await login(username.trim(), password);
      setOpen(false);
      setUsername("");
      setPassword("");
    } catch (err) {
      setError(err instanceof ApiError && err.status === 401 ? t("auth.invalid") : t("auth.error"));
    } finally {
      setBusy(false);
    }
  };

  return (
    <div className="auth-control">
      <button className="auth-btn" onClick={() => setOpen((v) => !v)}>
        {t("auth.login")}
      </button>
      {open && (
        <form className="auth-popover" onSubmit={submit}>
          <input
            placeholder={t("auth.username")}
            value={username}
            onChange={(e) => setUsername(e.target.value)}
            autoFocus
          />
          <input
            type="password"
            placeholder={t("auth.password")}
            value={password}
            onChange={(e) => setPassword(e.target.value)}
          />
          {error && <div className="auth-error">{error}</div>}
          <button type="submit" className="auth-btn primary" disabled={busy}>
            {t("auth.login")}
          </button>
        </form>
      )}
    </div>
  );
}
