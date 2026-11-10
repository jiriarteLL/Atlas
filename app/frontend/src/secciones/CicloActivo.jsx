// CicloActivo.jsx — Secciones "Ciclo de vida" y "Movimientos" de la ficha del activo (fase F): estado, datos de
// compra, vida util / renovacion sugerida, acciones rapidas (asignar, devolver, prestar, reparacion, baja) y la
// linea de tiempo de movimientos con las actas. Datos: /api/ciclo/<id>.
import { useCallback, useEffect, useState } from "react";
import { apiFetch } from "../api";
import { SEDES, fmtFechaHora } from "../ui";
import { Ficha, Rotulo, estadoColor } from "../diseno/comunes";
import "../diseno/fasef.css";

const fmtF = (s) => { const m = /^(\d{4})-(\d{2})-(\d{2})/.exec(s || ""); return m ? `${m[3]}/${m[2]}/${m[1]}` : ""; };
const ACCIONES = [
  ["asignacion", "Asignar", true], ["prestamo", "Prestar", true], ["devolucion", "Devolver", false],
  ["envio_reparacion", "A reparación", false], ["vuelta_reparacion", "Vuelve de reparación", false],
  ["traslado", "Cambiar de sede", false], ["para_baja", "Para baja", false], ["baja", "Dar de baja", false],
];

async function pedir(url, opts) {
  const r = await apiFetch(url, opts);
  const d = await r.json().catch(() => ({}));
  if (!r.ok) throw new Error(typeof d.detail === "string" ? d.detail : "Error " + r.status);
  return d;
}

export function textoRenovacion(v) {
  if (!v) return "";
  if (!v.renovacion) return v.vida_util_meses ? "Sin fecha de compra" : "";
  const d = v.dias_renovacion;
  return fmtF(v.renovacion) + (d <= 0 ? " · vencida hace " + -d + " días" : " · en " + d + " días");
}

export function CicloActivo({ assetId, puedeEditar, avisar, onCambio, abrirActa }) {
  const [c, setC] = useState(null);
  const [error, setError] = useState("");
  const [accion, setAccion] = useState(null);      // {tipo, a_usuario, sede, motivo}
  const [compra, setCompra] = useState(null);       // edicion de datos de compra
  const [guardando, setGuardando] = useState(false);

  const cargar = useCallback(async () => {
    try { setC(await pedir("/api/ciclo/" + assetId)); setError(""); } catch (e) { setError(e.message); }
  }, [assetId]);
  useEffect(() => { cargar(); }, [cargar]);

  async function registrar() {
    setGuardando(true);
    try {
      const body = { tipo: accion.tipo, motivo: accion.motivo || "" };
      if (accion.a_usuario) body.a_usuario = accion.a_usuario;
      if (accion.sede) body.sede = accion.sede;
      await pedir("/api/ciclo/" + assetId + "/movimientos", { method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify(body) });
      setAccion(null);
      await cargar();
      avisar && avisar("Movimiento registrado");
      onCambio && onCambio();
    } catch (e) { setError(e.message); } finally { setGuardando(false); }
  }

  async function guardarCompra() {
    setGuardando(true);
    try {
      const body = { ...compra, costo: compra.costo === "" ? null : Number(compra.costo),
        vida_util_meses: compra.vida_util_meses === "" ? null : Number(compra.vida_util_meses), fecha_compra: compra.fecha_compra || null };
      await pedir("/api/ciclo/" + assetId + "/admin", { method: "PUT", headers: { "Content-Type": "application/json" }, body: JSON.stringify(body) });
      setCompra(null);
      await cargar();
      avisar && avisar("Datos de compra guardados");
    } catch (e) { setError(e.message); } finally { setGuardando(false); }
  }

  if (!c) return error ? <div className="tenue" style={{ fontSize: 12.5 }}>{error}</div> : null;
  const v = c.vida_util, adm = c.admin, ec = estadoColor(c.estado_ciclo);
  const set = (o, setO, k) => (e) => setO({ ...o, [k]: e.target.value });
  const def = ACCIONES.find(([k]) => k === accion?.tipo);

  return (<>
    <div>
      <Rotulo>CICLO DE VIDA</Rotulo>
      <div style={{ display: "flex", alignItems: "center", gap: 10, flexWrap: "wrap", marginBottom: 12 }}>
        <span className="ll-chip" style={{ color: ec, background: `color-mix(in srgb, ${ec} 14%, transparent)`, fontWeight: 600 }}>{c.estado_ciclo}</span>
        {v.para_renovar && <span className="ll-chip" style={{ color: "var(--ll-rosa)", background: "color-mix(in srgb, var(--ll-rosa) 14%, transparent)" }}>Para renovar</span>}
        {v.renovar_pronto && <span className="ll-chip" style={{ color: "var(--ll-ambar)", background: "color-mix(in srgb, var(--ll-ambar) 14%, transparent)" }}>Renovar pronto</span>}
      </div>
      {puedeEditar && !accion && <div style={{ display: "flex", gap: 6, flexWrap: "wrap", marginBottom: 12 }}>
        {ACCIONES.map(([k, l]) => <button key={k} className="ll-btn-borde ll-btn-chico" onClick={() => setAccion({ tipo: k, a_usuario: "", sede: "", motivo: "" })}>{l}</button>)}
      </div>}
      {accion && <div className="ll-card" style={{ padding: 14, marginBottom: 12, display: "flex", flexDirection: "column", gap: 10 }}>
        <div style={{ fontWeight: 600 }}>{def ? def[1] : accion.tipo}</div>
        <div className="ll-grid-form">
          {def && def[2] && <label className="ll-campo doble"><span>PERSONA</span><input className="ll-input" value={accion.a_usuario} onChange={set(accion, setAccion, "a_usuario")} autoComplete="off" /></label>}
          <label className="ll-campo"><span>SEDE {accion.tipo === "traslado" ? "" : "(OPCIONAL)"}</span>
            <select className="ll-select" value={accion.sede} onChange={set(accion, setAccion, "sede")}><option value="">Sin cambio</option>{SEDES.map((s) => <option key={s}>{s}</option>)}</select></label>
          <label className="ll-campo"><span>MOTIVO / NOTA</span><input className="ll-input" value={accion.motivo} onChange={set(accion, setAccion, "motivo")} autoComplete="off" /></label>
        </div>
        <div className="tenue" style={{ fontSize: 11.5 }}>Para entregas con firma, usá Herramientas → Actas: el acta registra el movimiento sola.</div>
        <div style={{ display: "flex", gap: 8, justifyContent: "flex-end" }}>
          <button className="ll-btn-borde" onClick={() => setAccion(null)}>Cancelar</button>
          <button className="ll-btn-primario" disabled={guardando || (def && def[2] && !accion.a_usuario.trim()) || (accion.tipo === "traslado" && !accion.sede)} onClick={registrar}>{guardando ? "Guardando…" : "Registrar"}</button>
        </div>
      </div>}
      {compra ? <div className="ll-card" style={{ padding: 14, display: "flex", flexDirection: "column", gap: 10 }}>
        <div className="ll-grid-form">
          <label className="ll-campo"><span>N° DE INVENTARIO</span><input className="ll-input" value={compra.nro_inventario} onChange={set(compra, setCompra, "nro_inventario")} /></label>
          <label className="ll-campo"><span>FECHA DE COMPRA</span><input className="ll-input" type="date" value={compra.fecha_compra} onChange={set(compra, setCompra, "fecha_compra")} /></label>
          <label className="ll-campo"><span>PROVEEDOR</span><input className="ll-input" value={compra.proveedor} onChange={set(compra, setCompra, "proveedor")} /></label>
          <label className="ll-campo"><span>FACTURA / OC</span><input className="ll-input" value={compra.factura} onChange={set(compra, setCompra, "factura")} /></label>
          <label className="ll-campo"><span>COSTO</span><input className="ll-input" type="number" min="0" step="0.01" value={compra.costo} onChange={set(compra, setCompra, "costo")} /></label>
          <label className="ll-campo"><span>MONEDA</span><select className="ll-select" value={compra.moneda} onChange={set(compra, setCompra, "moneda")}><option value="">—</option><option>ARS</option><option>USD</option></select></label>
          <label className="ll-campo doble"><span>VIDA ÚTIL EN MESES (VACÍO = {v.vida_util_meses && !adm.vida_util_meses ? v.vida_util_meses + ", LA DEL TIPO" : "LA DEL TIPO"})</span>
            <input className="ll-input" type="number" min="1" max="240" value={compra.vida_util_meses} onChange={set(compra, setCompra, "vida_util_meses")} /></label>
          <label className="ll-campo doble"><span>NOTAS</span><textarea className="ll-input" rows={2} value={compra.notas} onChange={set(compra, setCompra, "notas")} /></label>
        </div>
        <div style={{ display: "flex", gap: 8, justifyContent: "flex-end" }}>
          <button className="ll-btn-borde" onClick={() => setCompra(null)}>Cancelar</button>
          <button className="ll-btn-primario" disabled={guardando} onClick={guardarCompra}>{guardando ? "Guardando…" : "Guardar"}</button>
        </div>
      </div> : <>
        <Ficha filas={[
          ["N° de inventario", adm.nro_inventario], ["Fecha de compra", fmtF(adm.fecha_compra)], ["Proveedor", adm.proveedor],
          ["Factura / OC", adm.factura], ["Costo", adm.costo != null ? (adm.moneda ? adm.moneda + " " : "") + Number(adm.costo).toLocaleString("es-AR") : ""],
          ["Vida útil", v.vida_util_meses ? v.vida_util_meses + " meses" + (adm.vida_util_meses ? "" : " (la del tipo)") : "Sin definir para este tipo"],
          ["Cuenta desde", v.base ? fmtF(v.base) + " · " + v.base_origen : ""],
          ["Renovación sugerida", textoRenovacion(v), v.para_renovar], ["Notas", adm.notas],
        ]} />
        {puedeEditar && <button className="ll-btn-borde ll-btn-chico" style={{ marginTop: 10 }} onClick={() => setCompra({
          nro_inventario: adm.nro_inventario || "", fecha_compra: adm.fecha_compra || "", proveedor: adm.proveedor || "", factura: adm.factura || "",
          costo: adm.costo ?? "", moneda: adm.moneda || "", vida_util_meses: adm.vida_util_meses ?? "", notas: adm.notas || "" })}>Editar datos de compra</button>}
      </>}
      {error && <div style={{ fontSize: 12, color: "var(--ll-warn)", marginTop: 8 }}>{error}</div>}
    </div>

    <div>
      <Rotulo>MOVIMIENTOS ({c.movimientos.length})</Rotulo>
      {c.movimientos.length ? <div className="ciclo-linea">
        {c.movimientos.map((m) => (
          <div key={m.id} className="ciclo-mov">
            <div><b>{m.rotulo}</b>{m.a_usuario ? " a " + m.a_usuario : ""}{m.tipo === "devolucion" && m.de_usuario ? " de " + m.de_usuario : ""}{m.sede ? " · " + m.sede : ""}
              {m.estado_ant !== m.estado_new && <span className="tenue"> · {m.estado_ant} → {m.estado_new}</span>}</div>
            <div className="f">{fmtFechaHora(m.fecha)} · {m.hecho_por}</div>
            {m.motivo && <div className="tenue">{m.acta_id && abrirActa ? <a href="#actas" onClick={(e) => { e.preventDefault(); abrirActa(m.acta_id); }}>{m.motivo}</a> : m.motivo}</div>}
          </div>
        ))}
      </div> : <div className="tenue" style={{ fontSize: 12.5 }}>Sin movimientos registrados todavía.</div>}
    </div>
  </>);
}
