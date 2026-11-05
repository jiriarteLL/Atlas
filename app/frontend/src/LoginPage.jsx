// LoginPage.jsx — Acceso con el diseño v2 (tarjeta sobre el fondo animado).
import { useState } from "react";
import { useAuth } from "./AuthContext";

export default function LoginPage({ saliendo }) {
  const { login, loading, error } = useAuth();
  const [usuario, setUsuario] = useState("");
  const [clave, setClave] = useState("");
  const [verClave, setVerClave] = useState(false);
  const [aviso, setAviso] = useState("");

  async function enviar(e) {
    e.preventDefault();
    if (!usuario.trim() || !clave) { setAviso("Ingresá usuario y contraseña."); return; }
    setAviso("");
    await login(usuario.trim(), clave);
  }

  const mensaje = aviso || error;
  return (
    <div className="ll-login-velo" style={saliendo ? { opacity: 0, pointerEvents: "none" } : undefined}>
      <form className="ll-login" onSubmit={enviar}>
        <div style={{ display: "flex", flexDirection: "column", alignItems: "center", gap: 14 }}>
          <div className="ll-logo" style={{ width: 58, height: 58, borderRadius: 16, fontSize: 17 }}>LLyA</div>
          <div style={{ textAlign: "center" }}>
            <div style={{ fontSize: 21, fontWeight: 600, letterSpacing: -0.3 }}>Atlas</div>
            <div className="mono" style={{ fontSize: 10.5, letterSpacing: 3, color: "var(--accent)", marginTop: 5 }}>ACCESO · SISTEMA DE ACTIVOS</div>
          </div>
        </div>
        <div className="ll-sep" />
        <label className="ll-campo">
          <span>USUARIO</span>
          <input className="ll-input" value={usuario} onChange={(e) => setUsuario(e.target.value)}
            placeholder="usuario de Windows o email" autoComplete="username" autoFocus />
        </label>
        <label className="ll-campo">
          <span>CONTRASEÑA</span>
          <span style={{ position: "relative", display: "flex" }}>
            <input className="ll-input" type={verClave ? "text" : "password"} value={clave}
              onChange={(e) => setClave(e.target.value)} placeholder="••••••••"
              autoComplete="current-password" style={{ flex: 1, paddingRight: 46 }} />
            <button type="button" onClick={() => setVerClave((v) => !v)} title={verClave ? "Ocultar contraseña" : "Ver contraseña"}
              aria-label={verClave ? "Ocultar contraseña" : "Ver contraseña"}
              style={{ position: "absolute", right: 6, top: "50%", transform: "translateY(-50%)", width: 34, height: 34, border: "none", background: "transparent", color: "var(--ll-muted)", fontSize: 14, cursor: "pointer", borderRadius: 9 }}>
              {verClave ? "◉" : "◎"}
            </button>
          </span>
        </label>
        {mensaje && <div className="ll-error" role="alert"><span>⚠</span>{mensaje}</div>}
        <button type="submit" className="ll-login-btn" disabled={loading}>{loading ? "VERIFICANDO…" : "INGRESAR →"}</button>
        <div style={{ textAlign: "center", fontSize: 11.5, color: "var(--ll-faint)" }}>Soporte Técnico · Lisicki, Litvin &amp; Abelovich</div>
      </form>
    </div>
  );
}
