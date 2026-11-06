// Accesos.jsx — Usuarios que pueden entrar a Atlas y sus permisos por modulo (como en Argos, pero con nivel:
// sin acceso / ver / editar). Pendientes de Windows arriba con "Habilitar y elegir permisos"; tarjetas con el
// resumen de modulos; editor de permisos con plantillas (Solo ver / Editor / Admin) y "copiar de otro usuario".
// El control real lo hace el servidor (require_modulo); esto solo arma y muestra los permisos.
import { useCallback, useEffect, useMemo, useState } from "react";
import { AUTH, apiFetch } from "../api";
import { Modal } from "../diseno/comunes";

const ROLES = [["viewer", "Solo ver"], ["editor", "Editor"], ["admin", "Admin"]];
const VACIO = { username: "", password: "", nombre: "", email: "", rol: "viewer" };
const TEXTO_NIVEL = { ver: "Ver", editar: "Editar", administrar: "Administrar" };
const iniciales = (n) => (n || "?").split(/\s+/).filter(Boolean).map((w) => w[0]).slice(0, 2).join("").toUpperCase();

async function pedir(url, metodo, cuerpo) {
  const r = await apiFetch(url, { method: metodo, headers: cuerpo ? { "Content-Type": "application/json" } : undefined, body: cuerpo ? JSON.stringify(cuerpo) : undefined });
  const d = await r.json().catch(() => ({}));
  if (!r.ok) throw new Error(typeof d.detail === "string" ? d.detail : "Error " + r.status);
  return d;
}

// Pendiente = entro con su usuario de Windows y todavia nadie le dio acceso
const esPendiente = (u) => u.activo === "0" && !Object.keys(u.modulos || {}).length;

// Chips con los modulos del usuario: "Impresoras · editar"
function ResumenModulos({ u, catalogo }) {
  if (u.protegido) return <span className="ll-chip acento">Acceso total</span>;
  const m = u.modulos || {};
  const lista = (catalogo?.modulos || []).filter((x) => m[x.clave]);
  if (!lista.length) return <span className="ll-chip" style={{ color: "var(--ll-ambar)" }}>Sin módulos</span>;
  return <>
    {lista.map((x) => <span key={x.clave} className={"ll-chip" + (m[x.clave] !== "ver" ? " acento" : "")}
      title={x.descripcion}>{x.rotulo}{m[x.clave] !== "ver" ? " · " + (x.clave === "importar" ? "usar" : (TEXTO_NIVEL[m[x.clave]] || m[x.clave]).toLowerCase()) : ""}</span>)}
    {m[catalogo.eliminar] && <span className="ll-chip" style={{ color: "var(--ll-rojo)" }}>Elimina activos</span>}
  </>;
}

function EditorPermisos({ catalogo, valor, onCambio, otros }) {
  const set = (k, v) => {
    const n = { ...valor };
    if (v) n[k] = v; else delete n[k];
    if (k === "activos" && v !== "editar") delete n[catalogo.eliminar];   // eliminar exige poder editar
    onCambio(n);
  };
  return (
    <div className="ll-permisos">
      <div className="ll-permisos-atajos">
        <span className="tenue">Plantillas:</span>
        {ROLES.map(([r, l]) => <button key={r} type="button" className="ll-btn-borde ll-btn-chico" onClick={() => onCambio({ ...catalogo.plantillas[r] })}>{l}</button>)}
        <button type="button" className="ll-btn-borde ll-btn-chico" onClick={() => onCambio({})}>Ninguno</button>
        {otros.length > 0 && <select className="ll-select" style={{ width: "auto", padding: "6px 10px", fontSize: 12.5 }} value="" aria-label="Copiar permisos de otro usuario"
          onChange={(e) => { const o = otros.find((x) => x.username === e.target.value); if (o) onCambio({ ...o.modulos }); }}>
          <option value="">Copiar de otro usuario…</option>
          {otros.map((o) => <option key={o.username} value={o.username}>{o.nombre || o.username}</option>)}
        </select>}
      </div>
      <div className="ll-permisos-tabla" role="table" aria-label="Permisos por módulo">
        {catalogo.modulos.map((x) => (
          <div key={x.clave} className={"ll-permisos-fila" + (x.disponible ? "" : " apagada")} role="row">
            <div role="cell" style={{ minWidth: 0 }}>
              <div style={{ fontWeight: 600, fontSize: 13.5 }}>{x.rotulo}</div>
              <div className="tenue" style={{ fontSize: 12 }}>{x.descripcion}</div>
              {x.clave === "activos" && <label className="ll-permisos-extra">
                <input type="checkbox" checked={!!valor[catalogo.eliminar]} disabled={valor.activos !== "editar"}
                  onChange={(e) => set(catalogo.eliminar, e.target.checked ? "si" : "")} />
                Eliminar activos {valor.activos !== "editar" && <span className="tenue">(requiere Editar)</span>}
              </label>}
            </div>
            <div role="cell" className="ll-niveles" aria-label={"Nivel en " + x.rotulo}>
              {x.disponible ? <>
                <button type="button" aria-pressed={!valor[x.clave]} onClick={() => set(x.clave, "")}>Sin acceso</button>
                {x.niveles.map((n) => <button key={n} type="button" aria-pressed={valor[x.clave] === n} onClick={() => set(x.clave, n)}>
                  {x.clave === "importar" ? "Usar" : TEXTO_NIVEL[n] || n}</button>)}
              </> : <span className="tenue" style={{ fontSize: 12, padding: "6px 10px" }}>Próximamente</span>}
            </div>
          </div>
        ))}
      </div>
    </div>
  );
}

export default function Accesos({ user, avisar }) {
  const [usuarios, setUsuarios] = useState([]);
  const [catalogo, setCatalogo] = useState(null);
  const [error, setError] = useState("");
  const [q, setQ] = useState("");
  const [modal, setModal] = useState(null);   // {tipo: "alta"|"editar"|"clave"|"permisos", datos}

  const cargar = useCallback(async () => {
    try {
      const [u, c] = await Promise.all([pedir(AUTH + "/usuarios", "GET"), pedir(AUTH + "/modulos", "GET")]);
      setUsuarios(u); setCatalogo(c); setError("");
    } catch (e) { setError(e.message); }
  }, []);
  useEffect(() => { cargar(); }, [cargar]);

  const pendientes = useMemo(() => usuarios.filter(esPendiente), [usuarios]);
  const resto = useMemo(() => {
    const t = q.trim().toLowerCase();
    return usuarios.filter((u) => !esPendiente(u) && (!t || [u.username, u.nombre, u.email].some((v) => (v || "").toLowerCase().includes(t))));
  }, [usuarios, q]);

  const abrirPermisos = (u, activar = false) =>
    setModal({ tipo: "permisos", datos: { username: u.username, nombre: u.nombre, activar,
      modulos: activar && !Object.keys(u.modulos || {}).length ? { ...catalogo.plantillas.viewer } : { ...(u.modulos || {}) } } });

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
      } else if (tipo === "permisos") {
        await pedir(AUTH + "/usuarios/" + encodeURIComponent(datos.username) + "/permisos", "PUT", { modulos: datos.modulos, activar: datos.activar });
        avisar(datos.activar ? "Usuario " + datos.username + " habilitado" : "Permisos de " + datos.username + " actualizados");
      } else {
        const { username, nombre, email, activo } = datos;
        await pedir(AUTH + "/usuarios/" + encodeURIComponent(username), "PUT", { nombre, email, activo });
        avisar("Usuario actualizado");
      }
      setModal(null);
      cargar();
    } catch (e) { setModal({ ...modal, error: e.message }); }
  }

  async function eliminar(u) {
    if (!confirm("¿Quitar el acceso de " + u.username + "?")) return;
    try { await pedir(AUTH + "/usuarios/" + encodeURIComponent(u.username), "DELETE"); avisar("Acceso quitado"); cargar(); }
    catch (e) { alert(e.message); }
  }

  const campo = (k, l, tipo = "text", extra = {}) => (
    <label className="ll-campo" key={k}>
      <span>{l}</span>
      <input className="ll-input" type={tipo} value={modal.datos[k] ?? ""} {...extra}
        onChange={(e) => setModal({ ...modal, error: "", datos: { ...modal.datos, [k]: e.target.value } })} />
    </label>
  );

  const motivoBloqueo = (u) => (u.protegido ? "Acceso total (superadmin o administrador de dominio): no se edita"
    : u.username === user?.username ? "Tus propios permisos los cambia otro administrador" : "");

  return (
    <div>
      <div className="ll-barra">
        <div className="ll-buscador">
          <span>⌕</span>
          <input className="ll-input" value={q} onChange={(e) => setQ(e.target.value)} placeholder="Buscar por usuario, nombre o email…" aria-label="Buscar usuarios" />
        </div>
        <span className="ll-contador">{resto.length} usuarios</span>
        <div style={{ flex: 1 }} />
        <button className="ll-btn-primario" onClick={() => setModal({ tipo: "alta", datos: { ...VACIO } })}>＋ Nuevo usuario</button>
      </div>
      {error && <div className="ll-error" style={{ marginBottom: 16 }}><span>⚠</span>{error}</div>}

      {pendientes.length > 0 && catalogo && <div className="ll-card" style={{ padding: "16px 20px", marginBottom: 20, borderColor: "color-mix(in srgb, var(--ll-ambar) 45%, transparent)" }}>
        <div style={{ fontWeight: 600, marginBottom: 10 }}>Pendientes de habilitar <span className="tenue" style={{ fontWeight: 400 }}>· entraron con su usuario de Windows (o se desactivaron) y no tienen módulos asignados</span></div>
        {pendientes.map((u) => (
          <div key={u.username} className="ll-permisos-pendiente">
            <div style={{ minWidth: 0 }}>
              <div style={{ fontWeight: 600 }}>{u.nombre || u.username}</div>
              <div className="tenue mono" style={{ fontSize: 12 }}>{u.username}</div>
            </div>
            <button className="ll-btn-primario" onClick={() => abrirPermisos(u, true)}>Habilitar y elegir permisos</button>
          </div>
        ))}
      </div>}

      <div className="ll-grid-3">
        {resto.map((u) => {
          const activo = u.activo !== "0";
          const bloqueo = motivoBloqueo(u);
          return (
            <div key={u.username} className="ll-card hover" style={{ padding: 20, borderRadius: 16, display: "flex", flexDirection: "column" }}>
              <div style={{ display: "flex", alignItems: "center", gap: 13 }}>
                <div className="ll-logo" style={{ width: 44, height: 44, flex: "0 0 44px", borderRadius: 12, fontSize: 14, letterSpacing: 0, boxShadow: "none" }}>{iniciales(u.nombre)}</div>
                <div style={{ minWidth: 0 }}>
                  <div style={{ fontWeight: 600, fontSize: 14.5 }}>{u.nombre}</div>
                  <div style={{ fontSize: 12, color: "var(--ll-dim)", overflow: "hidden", textOverflow: "ellipsis", whiteSpace: "nowrap" }}>{u.email || u.username}</div>
                </div>
              </div>
              <div style={{ display: "flex", gap: 8, marginTop: 14, flexWrap: "wrap" }}>
                <span className="ll-chip mono">{u.username}</span>
                {u.windows && <span className="ll-chip">Windows</span>}
                <span className="ll-chip" style={{ color: activo ? "var(--ll-verde)" : "var(--ll-ambar)", background: `color-mix(in srgb, ${activo ? "var(--ll-verde)" : "var(--ll-ambar)"} 12%, transparent)` }}>{activo ? "Activo" : "Inactivo"}</span>
              </div>
              <div style={{ display: "flex", gap: 6, marginTop: 12, flexWrap: "wrap", flex: 1, alignContent: "flex-start" }}>
                <ResumenModulos u={u} catalogo={catalogo} />
              </div>
              <div style={{ display: "flex", gap: 8, marginTop: 16, borderTop: "1px solid var(--ll-line-2)", paddingTop: 14 }}>
                <button className="ll-btn-borde" style={{ flex: 1 }} disabled={!!bloqueo || !catalogo} title={bloqueo || "Elegir a qué módulos entra y con qué nivel"}
                  onClick={() => abrirPermisos(u)}>Permisos</button>
                <button className="ll-btn-borde" onClick={() => setModal({ tipo: "editar", datos: { ...u, activo: activo ? "1" : "0" } })}>Editar</button>
                {!u.windows && <button className="ll-btn-borde" onClick={() => setModal({ tipo: "clave", datos: { username: u.username, password: "", confirmar: "" } })}>Clave</button>}
                {!u.protegido && u.username !== user?.username && <button className="ll-btn-peligro" style={{ padding: "8px 14px", borderRadius: 9 }} onClick={() => eliminar(u)} aria-label={"Quitar acceso a " + u.username}>✕</button>}
              </div>
            </div>
          );
        })}
      </div>

      {modal && (
        <Modal onCerrar={() => setModal(null)} ancho={modal.tipo === "permisos" ? 760 : undefined}
          titulo={modal.tipo === "alta" ? "Nuevo usuario" : modal.tipo === "clave" ? "Nueva contraseña para " + modal.datos.username
            : modal.tipo === "permisos" ? (modal.datos.activar ? "Habilitar a " : "Permisos de ") + (modal.datos.nombre || modal.datos.username)
              : "Editar " + modal.datos.username}
          pie={<>
            <button className="ll-btn-borde" style={{ padding: "11px 20px", borderRadius: 11 }} onClick={() => setModal(null)}>Cancelar</button>
            <button className="ll-btn-primario" style={{ padding: "11px 24px" }} onClick={guardar}>{modal.tipo === "permisos" && modal.datos.activar ? "Habilitar" : "Guardar"}</button>
          </>}>
          {modal.tipo === "permisos" ? <div style={{ padding: "18px 26px 6px" }}>
            <EditorPermisos catalogo={catalogo} valor={modal.datos.modulos}
              otros={usuarios.filter((o) => o.username !== modal.datos.username && !esPendiente(o))}
              onCambio={(m) => setModal({ ...modal, error: "", datos: { ...modal.datos, modulos: m } })} />
            <div className="tenue" style={{ fontSize: 12.5, marginTop: 12 }}>Los cambios valen desde la próxima acción del usuario; no hace falta que cierre sesión.</div>
            {modal.error && <div className="ll-error" role="alert" style={{ marginTop: 12 }}><span>⚠</span>{modal.error}</div>}
          </div> : <div className="ll-modal-cuerpo">
            {modal.tipo === "alta" && <>
              {campo("username", "USUARIO", "text", { placeholder: "nombre.apellido", autoComplete: "off" })}
              {campo("password", "CONTRASEÑA INICIAL", "password", { placeholder: "Mínimo 12 caracteres", autoComplete: "new-password" })}
              {campo("nombre", "NOMBRE COMPLETO")}
              {campo("email", "EMAIL", "email")}
              <label className="ll-campo doble">
                <span>PERMISOS INICIALES</span>
                <select className="ll-select" value={modal.datos.rol}
                  onChange={(e) => setModal({ ...modal, error: "", datos: { ...modal.datos, rol: e.target.value } })}>
                  {ROLES.map(([v, l]) => <option key={v} value={v}>{l}</option>)}
                </select>
              </label>
            </>}
            {modal.tipo === "editar" && <>
              {campo("nombre", "NOMBRE COMPLETO")}
              {campo("email", "EMAIL", "email", { disabled: modal.datos.rol === "superadmin" })}
              <label className="ll-campo doble">
                <span>ESTADO</span>
                <select className="ll-select" value={modal.datos.activo} disabled={modal.datos.protegido || modal.datos.username === user?.username}
                  onChange={(e) => setModal({ ...modal, error: "", datos: { ...modal.datos, activo: e.target.value } })}>
                  <option value="1">Activo</option><option value="0">Inactivo (no puede entrar)</option>
                </select>
              </label>
            </>}
            {modal.tipo === "clave" && <>
              {campo("password", "CONTRASEÑA NUEVA", "password", { autoComplete: "new-password" })}
              {campo("confirmar", "REPETIR", "password", { autoComplete: "new-password" })}
              <div className="doble" style={{ fontSize: 12.5, color: "var(--ll-dim)" }}>El usuario va a tener que cambiarla en su próximo ingreso. Sus sesiones abiertas se cierran.</div>
            </>}
            {modal.tipo === "alta" && <div className="doble" style={{ fontSize: 12.5, color: "var(--ll-dim)" }}>Después podés ajustar módulo por módulo con el botón Permisos. El usuario cambia la contraseña inicial en su primer ingreso.</div>}
            {modal.error && <div className="ll-error doble" role="alert"><span>⚠</span>{modal.error}</div>}
          </div>}
        </Modal>
      )}
    </div>
  );
}
