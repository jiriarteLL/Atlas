// HistorialActivo.jsx — Historial de cambios de la ficha del activo.
import { useState, useEffect } from "react";
import { API } from "../api";
import { Tag } from "../ui";

export function HistorialActivo({ assetId }) {
  const [historial, setHistorial] = useState([]);
  const [filtro, setFiltro] = useState("todo");
  useEffect(() => {
    if (!assetId) return;
    fetch(`${API.replace("/api","")}/api/assets/${assetId}/historial`)
      .then(r => r.json()).then(setHistorial).catch(() => {});
  }, [assetId]);

  const GRUPOS = {
    asignaciones: ["usuario","usuario_alt","ubicacion","estado","alta"],
    hardware: ["nombre","tipo","marca","modelo","serial","cpu","ram","disco","ip","so","so_version","so_arquitectura","grupo","red","monitores","impresoras","garantia","comentarios"],
  };
  function pasa(h){
    const c = (h.campo||"").toLowerCase();
    if (filtro === "todo") return true;
    if (filtro === "software") return c.startsWith("software");
    if (filtro === "asignaciones") return GRUPOS.asignaciones.includes(c);
    if (filtro === "hardware") return GRUPOS.hardware.includes(c);
    return true;
  }
  const filtrados = historial.filter(pasa);

  return (
    <div className="card">
      <div className="card-head" style={{display:"flex",alignItems:"center",gap:10,flexWrap:"wrap"}}>
        <div className="card-title">📋 Historial de cambios ({filtrados.length}{filtro!=="todo"?` de ${historial.length}`:""})</div>
        <div style={{display:"flex",gap:6,marginLeft:"auto"}}>
          {[["todo","Todo"],["asignaciones","Asignaciones"],["hardware","Hardware"],["software","Software"]].map(([k,lbl])=>(
            <span key={k} onClick={()=>setFiltro(k)}
              style={{fontSize:11,cursor:"pointer",fontWeight:600,padding:"3px 10px",borderRadius:20,userSelect:"none",
              background: filtro===k?"var(--accent-soft)":"transparent",
              color: filtro===k?"var(--accent-hover)":"var(--text-muted)"}}>{lbl}</span>
          ))}
        </div>
      </div>
      <div style={{maxHeight:280,overflowY:"auto"}}>
        <table><thead><tr><th>Fecha</th><th>Accion</th><th>Campo</th><th>Valor anterior</th><th>Valor nuevo</th></tr></thead>
        <tbody>
          {filtrados.length===0&&<tr><td colSpan="5" style={{textAlign:"center",padding:16,color:"var(--text-muted)"}}>{historial.length===0?"Sin cambios registrados aun.":"Sin cambios de este tipo."}</td></tr>}
          {filtrados.map((h,i)=>(
            <tr key={h.id||i}>
              <td className="td-small">{new Date(h.fecha).toLocaleString("es-AR")}</td>
              <td><Tag color={h.accion==="edicion"?"#3987e5":h.accion==="alta"?"#0ca30c":"#6E7A90"} label={h.accion}/></td>
              <td>{(h.campo||"").startsWith("software") ? <Tag color={h.campo==="software_instalado"?"#0ca30c":h.campo==="software_desinstalado"?"#d03b3b":"#E67E22"} label={h.campo.replace("software_","")}/> : h.campo}</td>
              <td className="td-muted">{h.valor_ant||"—"}</td>
              <td style={{fontWeight:600}}>{h.valor_new||"—"}</td>
            </tr>
          ))}
        </tbody></table>
      </div>
    </div>
  );
}
