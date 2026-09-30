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
    <div className="form-group" style={{ marginBottom: 12 }}>
      <label className="form-label">{label}</label>
      <input type="password" autoComplete={auto} value={f[k]} onChange={(e) => setF({ ...f, [k]: e.target.value })} required style={{ width: "100%" }} />
    </div>
  );

  return (
    <div className="modal-overlay">
      <form className="modal" onSubmit={enviar} style={{ maxWidth: 420 }}>
        <div className="modal-head">
          <div className="modal-icon">🔒</div>
          <div className="modal-title">Cambiá tu contraseña</div>
        </div>
        <p style={{ fontSize: 13, color: "var(--text-secondary)", margin: "0 0 16px" }}>
          {user?.username} tiene una contraseña inicial o reseteada. Antes de seguir tenés que elegir una propia.
        </p>
        {campo("actual", "Contraseña actual", "current-password")}
        {campo("nuevo", "Contraseña nueva", "new-password")}
        {campo("confirmar", "Repetir la nueva", "new-password")}
        {msg && <div style={{ fontSize: 13, color: "var(--critical-text)", marginBottom: 10 }}>{msg}</div>}
        <div className="modal-actions">
          <button type="button" className="btn" onClick={logout}>Cerrar sesión</button>
          <button type="submit" className="btn btn-primary" disabled={enviando}>{enviando ? "Guardando..." : "Cambiar contraseña"}</button>
        </div>
      </form>
    </div>
  );
}
