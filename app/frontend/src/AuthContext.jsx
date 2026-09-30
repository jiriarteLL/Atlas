// AuthContext.jsx
// Sesion del usuario: login/logout contra el backend (mismo origen), access token en memoria y
// renovacion automatica con el refresh token (cookie HttpOnly). Al recargar la pagina la sesion se
// recupera con /auth/refresh: no hay nada guardado en localStorage.

import { createContext, useContext, useState, useCallback, useEffect } from "react";
import { AUTH, authHeaders, onSesionPerdida, refrescar, setAccessToken } from "./api";

const AuthContext = createContext(null);

export function tienePermiso(user, codigo) {
  return !!user && Array.isArray(user.permisos) && user.permisos.includes(codigo);
}

export function AuthProvider({ children }) {
  const [user, setUser] = useState(null);
  const [listo, setListo] = useState(false);   // false mientras se intenta recuperar la sesion
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState(null);
  // Proxima renovacion: {seg: vida del token, n: contador para que cada ciclo dispare el efecto}.
  const [renovacion, setRenovacion] = useState(null);

  const cerrarLocal = useCallback(() => {
    setAccessToken("");
    setUser(null);
    setRenovacion(null);
  }, []);

  const programar = useCallback((seg) => setRenovacion((r) => ({ seg, n: (r?.n || 0) + 1 })), []);

  // Renueva el access token antes de que venza (al 80 % de su vida).
  useEffect(() => {
    if (!renovacion) return undefined;
    const id = setTimeout(async () => {
      const d = await refrescar();
      if (d) { setUser(d.user); programar(d.expires_in); } else cerrarLocal();
    }, Math.max(30, renovacion.seg * 0.8) * 1000);
    return () => clearTimeout(id);
  }, [renovacion, programar, cerrarLocal]);

  // Al abrir la app: recuperar la sesion con la cookie de refresh (si la hay).
  useEffect(() => {
    onSesionPerdida(cerrarLocal);
    refrescar().then((d) => { if (d) { setUser(d.user); programar(d.expires_in); } }).finally(() => setListo(true));
  }, [cerrarLocal, programar]);

  const login = useCallback(async (username, password) => {
    setLoading(true);
    setError(null);
    try {
      const body = new URLSearchParams();
      body.set("username", username);
      body.set("password", password);
      const res = await fetch(`${AUTH}/login`, {
        method: "POST", credentials: "same-origin",
        headers: { "Content-Type": "application/x-www-form-urlencoded" },
        body,
      });
      if (res.status === 429) throw new Error("Demasiados intentos. Espera un rato y volve a probar.");
      if (!res.ok) {
        const data = await res.json().catch(() => ({}));
        throw new Error(data.detail || "Usuario o contraseña incorrectos.");
      }
      const data = await res.json();
      setAccessToken(data.access_token);
      setUser(data.user);
      programar(data.expires_in);
      return true;
    } catch (err) {
      setError(err.message);
      return false;
    } finally {
      setLoading(false);
    }
  }, [programar]);

  const logout = useCallback(async () => {
    // Revoca access y refresh en el servidor; si falla (red caida) igual se cierra la sesion local.
    try { await fetch(`${AUTH}/logout`, { method: "POST", credentials: "same-origin", headers: authHeaders() }); } catch { /* sin red */ }
    cerrarLocal();
  }, [cerrarLocal]);

  return (
    <AuthContext.Provider value={{ user, login, logout, loading, error, listo, isAuthenticated: !!user }}>
      {children}
    </AuthContext.Provider>
  );
}

export function useAuth() {
  const ctx = useContext(AuthContext);
  if (!ctx) throw new Error("useAuth debe usarse dentro de <AuthProvider>");
  return ctx;
}
