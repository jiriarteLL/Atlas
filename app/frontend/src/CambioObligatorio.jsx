// CambioObligatorio.jsx — pantalla que bloquea la app hasta cambiar la password inicial
// (superadmin sembrado o password reseteada por un admin; 09-SEGURIDAD capa 4).
import { useState } from "react";
import { AUTH, authHeaders } from "./api";
import { useAuth } from "./AuthContext";

export default function CambioObligatorio() {
  const { user, logout } = useAuth();
  const [f, setF] = useState({ actual: "", nuevo: "", confirmar: "" });
  const [msg, setMsg] = useState("");
  const [enviando, setEnviando] = useState(false);

  async function enviar(e) {
    e.preventDefault();
    if (f.nuevo !== f.confirmar) { setMsg("Las contraseñas nuevas no coinciden."); return; }
    if (f.nuevo.length < 12) { setMsg("Mínimo 12 caracteres, combinando mayúsculas, minúsculas, números o símbolos."); return; }
    setEnviando(true);
    try {
      const r = await fetch(AUTH + "/cambiar-password", {
        method: "POST", credentials: "same-origin",
        headers: authHeaders({ "Content-Type": "application/json" }),
        body: JSON.stringify({ password_actual: f.actual, password_nuevo: f.nuevo }),
      });
      const d = await r.json().catch(() => ({}));
      if (r.ok) {
        alert("Contraseña cambiada. Volvé a iniciar sesión con la nueva.");
        window.location.reload();   // el backend cerro todas las sesiones anteriores
        return;
      }
      setMsg(d.detail || "No se pudo cambiar la contraseña (" + r.status + ").");
    } catch (err) { setMsg("Error de conexión: " + err.message); }
    setEnviando(false);
  }

  const campo = (k, label, auto) => (
    <label className="ll-campo">
      <span>{label}</span>
      <input className="ll-input" type="password" autoComplete={auto} value={f[k]} onChange={(e) => setF({ ...f, [k]: e.target.value })} required />
    </label>
  );

  return (
    <div className="ll-login-velo">
      <form className="ll-login" onSubmit={enviar}>
        <div style={{ display: "flex", flexDirection: "column", alignItems: "center", gap: 14 }}>
          <div className="ll-logo" style={{ width: 58, height: 58, borderRadius: 16, fontSize: 22 }}>🔒</div>
          <div style={{ textAlign: "center" }}>
            <div style={{ fontSize: 21, fontWeight: 600 }}>Cambiá tu contraseña</div>
            <div className="mono" style={{ fontSize: 10.5, letterSpacing: 3, color: "var(--accent)", marginTop: 5 }}>PRIMER INGRESO</div>
          </div>
        </div>
        <p style={{ fontSize: 13, color: "var(--ll-text-2)", margin: 0, textAlign: "center" }}>
          {user?.username} tiene una contraseña inicial o reseteada. Antes de seguir tenés que elegir una propia.
        </p>
        {campo("actual", "CONTRASEÑA ACTUAL", "current-password")}
        {campo("nuevo", "CONTRASEÑA NUEVA", "new-password")}
        {campo("confirmar", "REPETIR LA NUEVA", "new-password")}
        {msg && <div className="ll-error" role="alert"><span>⚠</span>{msg}</div>}
        <button type="submit" className="ll-login-btn" disabled={enviando}>{enviando ? "GUARDANDO…" : "CAMBIAR CONTRASEÑA"}</button>
        <button type="button" className="ll-btn-borde" onClick={logout} style={{ alignSelf: "center" }}>Cerrar sesión</button>
      </form>
    </div>
  );
}
