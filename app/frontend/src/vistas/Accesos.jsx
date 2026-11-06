// Accesos.jsx — Usuarios que pueden entrar a la app (solo admin). Tarjetas con el diseño v2;
// alta, edicion (nombre, email, rol, activo), reseteo de contraseña y baja.
import { useCallback, useEffect, useState } from "react";
import { AUTH, apiFetch } from "../api";
import { Modal } from "../diseno/comunes";

const ROLES = [["viewer", "Solo ver"], ["editor", "Editor"], ["admin", "Admin"]];
const VACIO = { username: "", password: "", nombre: "", email: "", rol: "viewer" };
const iniciales = (n) => (n || "?").split(/\s+/).filter(Boolean).map((w) => w[0]).slice(0, 2).join("").toUpperCase();

async function pedir(url, metodo, cuerpo) {
  const r = await apiFetch(url, { method: metodo, headers: cuerpo ? { "Content-Type": "application/json" } : undefined, body: cuerpo ? JSON.stringify(cuerpo) : undefined });
  const d = await r.json().catch(() => ({}));
  if (!r.ok) throw new Error(typeof d.detail === "string" ? d.detail : "Error " + r.status);
  return d;
}

export default function Accesos({ user, avisar }) {
  const [usuarios, setUsuarios] = useState([]);
  const [error, setError] = useState("");
  const [modal, setModal] = useState(null);   // {tipo: "alta"|"editar"|"clave", datos}

  const cargar = useCallback(async () => {
    try { setUsuarios(await pedir(AUTH + "/usuarios", "GET")); setError(""); }
    catch (e) { setError(e.message); }
  }, []);
  useEffect(() => { cargar(); }, [cargar]);

  async function guardar() {
    const { tipo, datos } = modal;
    try {
      if (tipo === "alta") {
        await pedir(AUTH + "/usuarios", "POST", datos);
        avisar("Usuario " + datos.username + " creado");
      } else if (tipo === "clave") {
        if (datos.password.length < 12) throw new Error("Mínimo 12 caracteres, combinando mayúsculas, minúsculas, números o símbolos.");
        if (datos.password !== datos.confirmar) throw new Error("Las contraseñas no coinciden.");
        await pedir(AUTH + "/usuarios/" + encodeURIComponent(datos.username), "PUT", { password: datos.password });
        avisar("Contraseña reseteada");
      } else {
        const { username, nombre, email, rol, activo } = datos;
        await pedir(AUTH + "/usuarios/" + encodeURIComponent(username), "PUT", { nombre, email, rol: rol === "superadmin" ? undefined : rol, activo });
        avisar("Usuario actualizado");
      }
      setModal(null);
      cargar();
    } catch (e) { setModal({ ...modal, error: e.message }); }
  }

  async function eliminar(u) {
    if (!confirm("¿Eliminar el acceso de " + u.username + "?")) return;
    try { await pedir(AUTH + "/usuarios/" + encodeURIComponent(u.username), "DELETE"); avisar("Usuario eliminado"); cargar(); }
    catch (e) { alert(e.message); }
  }

  const campo = (k, l, tipo = "text", extra = {}) => (
    <label className="ll-campo" key={k}>
      <span>{l}</span>
      <input className="ll-input" type={tipo} value={modal.datos[k] ?? ""} {...extra}
        onChange={(e) => setModal({ ...modal, error: "", datos: { ...modal.datos, [k]: e.target.value } })} />
    </label>
  );

  return (
    <div>
      <div className="ll-barra">
        <span className="ll-contador">{usuarios.length} usuarios con acceso</span>
        <div style={{ flex: 1 }} />
        <button className="ll-btn-primario" onClick={() => setModal({ tipo: "alta", datos: { ...VACIO } })}>＋ Nuevo usuario</button>
      </div>
      {error && <div className="ll-error" style={{ marginBottom: 16 }}><span>⚠</span>{error}</div>}
      <div className="ll-grid-3">
        {usuarios.map((u) => {
          const activo = u.activo !== "0";
          const esSuper = u.rol === "superadmin";
          return (
            <div key={u.username} className="ll-card hover" style={{ padding: 20, borderRadius: 16 }}>
              <div style={{ display: "flex", alignItems: "center", gap: 13 }}>
                <div className="ll-logo" style={{ width: 44, height: 44, flex: "0 0 44px", borderRadius: 12, fontSize: 14, letterSpacing: 0, boxShadow: "none" }}>{iniciales(u.nombre)}</div>
                <div style={{ minWidth: 0 }}>
                  <div style={{ fontWeight: 600, fontSize: 14.5 }}>{u.nombre}</div>
                  <div style={{ fontSize: 12, color: "var(--ll-dim)", overflow: "hidden", textOverflow: "ellipsis", whiteSpace: "nowrap" }}>{u.email || u.username}</div>
                </div>
              </div>
              <div style={{ display: "flex", gap: 8, marginTop: 16, flexWrap: "wrap" }}>
                <span className="ll-chip acento">{u.rol}</span>
                <span className="ll-chip mono">{u.username}</span>
                <span className="ll-chip" style={{ color: activo ? "var(--ll-verde)" : "var(--ll-ambar)", background: `color-mix(in srgb, ${activo ? "var(--ll-verde)" : "var(--ll-ambar)"} 12%, transparent)` }}>{activo ? "Activo" : "Inactivo"}</span>
              </div>
              <div style={{ display: "flex", gap: 8, marginTop: 16, borderTop: "1px solid var(--ll-line-2)", paddingTop: 14 }}>
                <button className="ll-btn-borde" style={{ flex: 1 }} onClick={() => setModal({ tipo: "editar", datos: { ...u, activo: activo ? "1" : "0" } })}>Editar</button>
                <button className="ll-btn-borde" onClick={() => setModal({ tipo: "clave", datos: { username: u.username, password: "", confirmar: "" } })}>Clave</button>
                {!esSuper && u.username !== user?.username && <button className="ll-btn-peligro" style={{ padding: "8px 14px", borderRadius: 9 }} onClick={() => eliminar(u)} aria-label={"Eliminar " + u.username}>✕</button>}
              </div>
            </div>
          );
        })}
      </div>

      {modal && (
        <Modal onCerrar={() => setModal(null)}
          titulo={modal.tipo === "alta" ? "Nuevo usuario" : modal.tipo === "clave" ? "Nueva contraseña para " + modal.datos.username : "Editar " + modal.datos.username}
          pie={<>
            <button className="ll-btn-borde" style={{ padding: "11px 20px", borderRadius: 11 }} onClick={() => setModal(null)}>Cancelar</button>
            <button className="ll-btn-primario" style={{ padding: "11px 24px" }} onClick={guardar}>Guardar</button>
          </>}>
          <div className="ll-modal-cuerpo">
            {modal.tipo === "alta" && <>
              {campo("username", "USUARIO", "text", { placeholder: "nombre.apellido", autoComplete: "off" })}
              {campo("password", "CONTRASEÑA INICIAL", "password", { placeholder: "Mínimo 12 caracteres", autoComplete: "new-password" })}
              {campo("nombre", "NOMBRE COMPLETO")}
              {campo("email", "EMAIL", "email")}
            </>}
            {modal.tipo === "editar" && <>
              {campo("nombre", "NOMBRE COMPLETO")}
              {campo("email", "EMAIL", "email", { disabled: modal.datos.rol === "superadmin" })}
            </>}
            {modal.tipo !== "clave" && <label className="ll-campo">
              <span>ROL</span>
              <select className="ll-select" value={modal.datos.rol} disabled={modal.datos.rol === "superadmin"}
                onChange={(e) => setModal({ ...modal, error: "", datos: { ...modal.datos, rol: e.target.value } })}>
                {(modal.datos.rol === "superadmin" ? [["superadmin", "Superadmin"]] : ROLES).map(([v, l]) => <option key={v} value={v}>{l}</option>)}
              </select>
            </label>}
            {modal.tipo === "editar" && <label className="ll-campo">
              <span>ESTADO</span>
              <select className="ll-select" value={modal.datos.activo} disabled={modal.datos.rol === "superadmin" || modal.datos.username === user?.username}
                onChange={(e) => setModal({ ...modal, error: "", datos: { ...modal.datos, activo: e.target.value } })}>
                <option value="1">Activo</option><option value="0">Inactivo (no puede entrar)</option>
              </select>
            </label>}
            {modal.tipo === "clave" && <>
              {campo("password", "CONTRASEÑA NUEVA", "password", { autoComplete: "new-password" })}
              {campo("confirmar", "REPETIR", "password", { autoComplete: "new-password" })}
              <div className="doble" style={{ fontSize: 12.5, color: "var(--ll-dim)" }}>El usuario va a tener que cambiarla en su próximo ingreso. Sus sesiones abiertas se cierran.</div>
            </>}
            {modal.tipo === "alta" && <div className="doble" style={{ fontSize: 12.5, color: "var(--ll-dim)" }}>El usuario va a tener que cambiar la contraseña inicial en su primer ingreso.</div>}
            {modal.error && <div className="ll-error doble" role="alert"><span>⚠</span>{modal.error}</div>}
          </div>
        </Modal>
      )}
    </div>
  );
}
