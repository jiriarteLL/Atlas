// MonitoresActivo.jsx — Secciones de la ficha de un activo: "Monitores conectados" (en una PC, lo ultimo que
// informo el agente) e "Historial de PCs" (en un monitor, las PCs donde estuvo conectado). Datos de /api/monitores.
import { useEffect, useState } from "react";
import { apiFetch } from "../api";
import { fmtFechaHora } from "../ui";
import { Rotulo } from "../diseno/comunes";
import { conMarca } from "../vistas/Monitores";

const fabricado = (m) => (m.anio ? (m.semana ? `${m.anio} (sem. ${m.semana})` : String(m.anio)) : "");

export function MonitoresConectados({ assetId, abrir }) {
  const [d, setD] = useState(null);
  useEffect(() => {
    let vivo = true;
    apiFetch("/api/monitores/pc/" + assetId).then((r) => (r.ok ? r.json() : null)).then((x) => { if (vivo) setD(x); }).catch(() => {});
    return () => { vivo = false; };
  }, [assetId]);
  if (!d || !d.monitores.length) return null;
  return (
    <div>
      <Rotulo>MONITORES CONECTADOS ({d.monitores.length})</Rotulo>
      <div className="ll-ficha">
        {d.monitores.map((m, i) => (
          <div key={i}>
            <span className="k">{m.interno ? "Pantalla de la notebook" : conMarca(m.marca, m.modelo || m.codigo_producto) || "Monitor"}</span>
            <span className="v">
              {[m.pulgadas ? m.pulgadas + "\"" : "", m.conexion, fabricado(m), !m.interno && m.serie && m.serie !== "0" ? "serie " + m.serie : ""].filter(Boolean).join(" · ")}
              {m.asset_id && abrir && <a href="#" style={{ marginLeft: 8 }} onClick={(e) => { e.preventDefault(); abrir(m.asset_id); }}>ver ficha</a>}
            </span>
          </div>
        ))}
        <div><span className="k">Relevado</span><span className="v">{fmtFechaHora(d.actualizado)}</span></div>
      </div>
    </div>
  );
}

export function HistorialPcs({ assetId, abrir }) {
  const [d, setD] = useState(null);
  useEffect(() => {
    let vivo = true;
    apiFetch("/api/monitores/" + assetId + "/conexiones").then((r) => (r.ok ? r.json() : null)).then((x) => { if (vivo) setD(x); }).catch(() => {});
    return () => { vivo = false; };
  }, [assetId]);
  if (!d) return null;
  const det = d.detalle || {};
  return (<>
    {d.detalle && <div>
      <Rotulo>MONITOR</Rotulo>
      <div className="ll-ficha">
        {det.pulgadas && <div><span className="k">Tamaño</span><span className="v">{det.pulgadas}"</span></div>}
        {det.conexion && <div><span className="k">Conexión</span><span className="v">{det.conexion}</span></div>}
        {det.anio && <div><span className="k">Fabricado</span><span className="v">{fabricado(det)}</span></div>}
        {det.codigo_producto && <div><span className="k">Código (EDID)</span><span className="v mono">{det.fabricante} {det.codigo_producto}</span></div>}
        <div><span className="k">Visto conectado</span><span className="v">{fmtFechaHora(det.visto)}</span></div>
      </div>
    </div>}
    <div>
      <Rotulo>HISTORIAL DE PCS ({d.conexiones.length})</Rotulo>
      {d.conexiones.length ? <div className="ll-ficha">
        {d.conexiones.map((c, i) => (
          <div key={i}>
            <span className="k">{abrir ? <a href="#" onClick={(e) => { e.preventDefault(); abrir(c.pc_id); }}>{c.pc_nombre || c.pc_id}</a> : c.pc_nombre}</span>
            <span className="v">{fmtFechaHora(c.desde)} → {c.hasta ? fmtFechaHora(c.hasta) : "hoy"}{c.conexion ? " · " + c.conexion : ""}</span>
          </div>
        ))}
      </div> : <div className="tenue" style={{ fontSize: 13 }}>Cargado a mano: el agente todavía no lo vio conectado a ninguna PC.</div>}
    </div>
  </>);
}
