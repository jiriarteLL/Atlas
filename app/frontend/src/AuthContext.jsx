// AuthContext.jsx
// Contexto de autenticacion: login/logout contra el backend (mismo origen), token y usuario actual con sus permisos.

import { createContext, useContext, useState, useCallback } from "react";
import { AUTH } from "./api";

const AuthContext = createContext(null);

// NOTA DE SEGURIDAD: el token vive en localStorage y es accesible por JS, por lo que un XSS
// podria robarlo. Se mitiga evitando dangerouslySetInnerHTML. El logout lo revoca en el servidor.
const TOKEN_KEY = "abm_token";
const USER_KEY = "abm_user";

export function tienePermiso(user, codigo) {
  return !!user && Array.isArray(user.permisos) && user.permisos.includes(codigo);
}

export function AuthProvider({ children }) {
  const [token, setToken] = useState(() => localStorage.getItem(TOKEN_KEY));
  const [user, setUser] = useState(() => {
    const raw = localStorage.getItem(USER_KEY);
    return raw ? JSON.parse(raw) : null;
  });
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState(null);

  const login = useCallback(async (username, password) => {
    setLoading(true);
    setError(null);
    try {
      const body = new URLSearchParams();
      body.set("username", username);
      body.set("password", password);

      const res = await fetch(`${AUTH}/login`, {
        method: "POST",
        headers: { "Content-Type": "application/x-www-form-urlencoded" },
        body,
      });

      if (res.status === 429) throw new Error("Demasiados intentos. Espera un minuto y volve a probar.");
      if (!res.ok) {
        const data = await res.json().catch(() => ({}));
        throw new Error(data.detail || "Usuario o contraseña incorrectos.");
      }

      const data = await res.json();
      localStorage.setItem(TOKEN_KEY, data.access_token);
      localStorage.setItem(USER_KEY, JSON.stringify(data.user));
      setToken(data.access_token);
      setUser(data.user);
      return true;
    } catch (err) {
      setError(err.message);
      return false;
    } finally {
      setLoading(false);
    }
  }, []);

  const logout = useCallback(async () => {
    const t = localStorage.getItem(TOKEN_KEY);
    if (t) {
      // Revoca el token en el servidor; si falla (red caida) igual se cierra la sesion local.
      try { await fetch(`${AUTH}/logout`, { method: "POST", headers: { Authorization: `Bearer ${t}` } }); } catch { /* sin red */ }
    }
    localStorage.removeItem(TOKEN_KEY);
    localStorage.removeItem(USER_KEY);
    setToken(null);
    setUser(null);
  }, []);

  return (
    <AuthContext.Provider
      value={{ user, token, login, logout, loading, error, isAuthenticated: !!token }}
    >
      {children}
    </AuthContext.Provider>
  );
}

export function useAuth() {
  const ctx = useContext(AuthContext);
  if (!ctx) throw new Error("useAuth debe usarse dentro de <AuthProvider>");
  return ctx;
}
