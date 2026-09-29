// AuthContext.jsx
// Contexto de autenticación para el frontend de Inventario LLYA.
// Maneja login/logout, guarda el token y expone el usuario actual + su rol.

import { createContext, useContext, useState, useCallback } from "react";

const AuthContext = createContext(null);

// Ajustar si el backend corre en otro host/puerto durante desarrollo.
const API_BASE = import.meta.env.VITE_API_BASE || (window.location.protocol === "https:" ? "https://192.168.100.116:8443" : "http://192.168.100.116:8000");

// NOTA DE SEGURIDAD: se guarda en localStorage (se borra al cerrar la pestaña/navegador),
// no en localStorage (persistiría indefinidamente). Sigue siendo accesible por JS,
// por lo que un XSS podría robarlo — mitigarlo evitando dangerouslySetInnerHTML
// y sanitizando cualquier contenido que venga de campos de texto libre del ABM.
// Si en el futuro se quiere eliminar ese riesgo del todo, la alternativa es que
// el backend setee una cookie HttpOnly en /auth/login en vez de devolver el
// token en el body — requiere que front y back compartan el mismo origen.
const TOKEN_KEY = "abm_token";
const USER_KEY = "abm_user";

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

      const res = await fetch(`${API_BASE}/auth/login`, {
        method: "POST",
        headers: { "Content-Type": "application/x-www-form-urlencoded" },
        body,
      });

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

  const logout = useCallback(() => {
    localStorage.removeItem(TOKEN_KEY);
    localStorage.removeItem(USER_KEY);
    setToken(null);
    setUser(null);
  }, []);

  // authFetch: wrapper de fetch que adjunta el Bearer token automáticamente
  // y desloguea sola si el backend responde 401 (token vencido/inválido).
  const authFetch = useCallback(
    async (path, options = {}) => {
      const res = await fetch(`${API_BASE}${path}`, {
        ...options,
        headers: {
          ...(options.headers || {}),
          Authorization: token ? `Bearer ${token}` : "",
        },
      });
      if (res.status === 401) {
        logout();
      }
      return res;
    },
    [token, logout]
  );

  return (
    <AuthContext.Provider
      value={{ user, token, login, logout, authFetch, loading, error, isAuthenticated: !!token }}
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

// Helper para proteger rutas por rol.
// Uso: <RequireRole roles={['soporte','admin']}><ABMList/></RequireRole>
export function RequireRole({ roles, children, fallback = <p>No tenés permisos para ver esta sección.</p> }) {
  const { user, isAuthenticated } = useAuth();
  if (!isAuthenticated) return <p>Necesitás iniciar sesión.</p>;
  if (!roles.includes(user.role)) return fallback;
  return children;
}
