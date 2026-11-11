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
        {/* Como Argos: el emblema (globo de Atlas con los colores de LLyA) y el nombre en grande; el logo de LLyA va al pie */}
        <div className="ll-login-cab">
          <div className="ll-login-emblema"><span className="anillo" aria-hidden /><img src="/favicon.svg" alt="" /></div>
          <div className="mono ll-login-kicker">ACCESO · DOMINIO TANGO</div>
          <h1 className="ll-login-nombre">ATLAS</h1>
          <div className="ll-login-lema">Sistema de activos de Lisicki, Litvin &amp; Abelovich</div>
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
        <div className="ll-login-pie">
          {/* logo-light: letras blancas para el tema oscuro; logo-dark: letras oscuras para Claro y Blanco */}
          <img className="ll-login-logo ll-solo-oscuro" src="/brand/logo-light.png" alt="Lisicki, Litvin & Abelovich — Member of Nexia" />
          <img className="ll-login-logo ll-solo-claro" src="/brand/logo-dark.png" alt="" />
          <span>Soporte Técnico</span>
        </div>
      </form>
    </div>
  );
}
