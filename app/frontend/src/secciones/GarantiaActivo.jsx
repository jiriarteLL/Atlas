// GarantiaActivo.jsx — Seccion "Garantía" de la ficha de un activo: cobertura, inicio/fin, dias, coberturas de
// fabrica y extensiones, fuente y fecha de consulta. Lenovo: "Consultar ahora"; cualquier marca: "Cargar a mano".
// Una carga manual no la pisa la consulta automatica; "Volver a Lenovo" la quita.
import { useCallback, useEffect, useState } from "react";
import { fmtFechaHora } from "../ui";
import { Rotulo } from "../diseno/comunes";
import { fmtFecha } from "../vistas/Salud";
import { ChipEntrega, colorDias, pedir, textoDias } from "../vistas/Garantias";

const VACIA = { inicio: "", fin: "", cobertura: "", proveedor: "", contrato: "", notas: "" };

export function GarantiaActivo({ assetId, puedeEditar, onCambio }) {
  const [g, setG] = useState(null);
  const [edicion, setEdicion] = useState(null);
  const [ocupado, setOcupado] = useState(false);
  const [error, setError] = useState("");

  const cargar = useCallback(async () => {
    try { setG(await pedir("/api/garantias/" + assetId)); } catch { setG(null); }
  }, [assetId]);
  useEffect(() => { cargar(); }, [cargar]);

  async function accion(fn) {
    setOcupado(true);
    setError("");
    try {
      const fin = await fn();
      await cargar();
      onCambio && onCambio(fin);
    } catch (e) { setError(e.message); } finally { setOcupado(false); }
  }
  const consultar = () => accion(async () => (await pedir("/api/assets/" + assetId + "/garantia", { method: "POST" })).garantia);
  const volverALenovo = () => accion(async () => {
    await pedir("/api/garantias/" + assetId + "/manual", { method: "DELETE" });
    if (g?.consultable) return (await pedir("/api/assets/" + assetId + "/garantia", { method: "POST" }).catch(() => ({}))).garantia || "";
    return "";
  });
  const guardar = () => accion(async () => {
    const cuerpo = { ...edicion, inicio: edicion.inicio || null };
    const r = await pedir("/api/garantias/" + assetId, { method: "PUT", headers: { "Content-Type": "application/json" }, body: JSON.stringify(cuerpo) });
    setEdicion(null);
    return r.fin;
  });
  const set = (k) => (e) => setEdicion({ ...edicion, [k]: e.target.value });

  if (!g) return null;
  const manual = g.fuente === "manual";
  return (
    <div>
      <Rotulo>GARANTÍA</Rotulo>
      {edicion ? (
        <div style={{ display: "flex", flexDirection: "column", gap: 12 }}>
          <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: 12 }}>
            <label className="ll-campo"><span>INICIO</span><input type="date" className="ll-input" value={edicion.inicio} onChange={set("inicio")} /></label>
            <label className="ll-campo"><span>FIN *</span><input type="date" className="ll-input" value={edicion.fin} onChange={set("fin")} /></label>
            <label className="ll-campo"><span>COBERTURA</span><input className="ll-input" value={edicion.cobertura} onChange={set("cobertura")} placeholder="3 años en sitio" autoComplete="off" /></label>
            <label className="ll-campo"><span>PROVEEDOR</span><input className="ll-input" value={edicion.proveedor} onChange={set("proveedor")} autoComplete="off" /></label>
            <label className="ll-campo" style={{ gridColumn: "1 / -1" }}><span>N° DE CONTRATO</span><input className="ll-input" value={edicion.contrato} onChange={set("contrato")} autoComplete="off" /></label>
          </div>
          <label className="ll-campo"><span>NOTAS</span><textarea className="ll-input" rows={2} value={edicion.notas} onChange={set("notas")} /></label>
          {error && <div style={{ color: "var(--ll-warn)", fontSize: 12.5 }}>{error}</div>}
          <div style={{ display: "flex", gap: 10, justifyContent: "flex-end" }}>
            <button className="ll-btn-borde" onClick={() => setEdicion(null)}>Cancelar</button>
            <button className="ll-btn-primario" disabled={ocupado || !edicion.fin} onClick={guardar}>{ocupado ? "Guardando…" : "Guardar"}</button>
          </div>
        </div>
      ) : (<>
        <div className="ll-ficha">
          <div><span className="k">Vence</span><span className="v" style={{ color: colorDias(g.dias), fontWeight: 600 }}>
            {g.fin ? `${fmtFecha(g.fin)} · ${textoDias(g.dias)}` : "Sin dato"}</span></div>
          {g.inicio && <div><span className="k">Inicio</span><span className="v">{fmtFecha(g.inicio)}</span></div>}
          {g.cobertura && <div><span className="k">Cobertura</span><span className="v">{g.cobertura} <ChipEntrega g={g} /></span></div>}
          {g.proveedor && <div><span className="k">Proveedor</span><span className="v">{g.proveedor}</span></div>}
          {g.contrato && <div><span className="k">Contrato</span><span className="v mono">{g.contrato}</span></div>}
          {g.notas && <div><span className="k">Notas</span><span className="v">{g.notas}</span></div>}
          <div><span className="k">Fuente</span><span className="v">
            {g.fuente === "lenovo" ? "Lenovo (automática)" : manual ? "Cargada a mano" : g.fuente === "ficha" ? "Fecha de la ficha" : "—"}
            {g.consultado ? <span className="tenue"> · consultada {fmtFechaHora(g.consultado)}</span> : null}</span></div>
          {g.error && <div><span className="k">Última consulta</span><span className="v alerta">{g.error}</span></div>}
        </div>
        {g.coberturas.length > 1 && <div style={{ marginTop: 10 }}>
          {g.coberturas.map((c, i) => (
            <div key={i} style={{ display: "flex", gap: 8, alignItems: "baseline", fontSize: 12.5, padding: "5px 0", borderTop: i ? "1px solid var(--ll-line)" : "none" }}>
              <span style={{ flex: 1, minWidth: 0 }}>{c.nombre || "Cobertura"} <span className="tenue">· {c.origen || "—"}</span></span>
              <span className="mono tenue" style={{ fontSize: 12 }}>{c.inicio ? fmtFecha(c.inicio) : "—"} → {fmtFecha(c.fin)}</span>
            </div>
          ))}
        </div>}
        {error && <div style={{ color: "var(--ll-warn)", fontSize: 12.5, marginTop: 8 }}>{error}</div>}
        {puedeEditar && <div style={{ display: "flex", gap: 10, flexWrap: "wrap", marginTop: 12 }}>
          {g.consultable && !manual && <button className="ll-btn-borde" disabled={ocupado} onClick={consultar}>{ocupado ? "Consultando…" : "Consultar ahora a Lenovo"}</button>}
          <button className="ll-btn-borde" onClick={() => setEdicion(manual ? { ...VACIA, ...Object.fromEntries(Object.keys(VACIA).map((k) => [k, g[k] || ""])) } : { ...VACIA, fin: g.fin || "", inicio: g.inicio || "" })}>
            {manual ? "Editar carga manual" : "Cargar a mano"}</button>
          {manual && <button className="ll-btn-borde" disabled={ocupado} onClick={volverALenovo}>{g.consultable ? "Volver a Lenovo" : "Quitar carga manual"}</button>}
        </div>}
      </>)}
    </div>
  );
}
