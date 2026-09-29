// HistorialEmpleado.jsx — Tarjeta "Historial" de la ficha: quien cambio que y cuando (audit_log del UserManager).
import { useState, useEffect } from "react";

const fmt = f => { if(!f) return ""; const d = new Date(f.endsWith("Z") ? f : f + "Z"); return isNaN(d) ? f : d.toLocaleString("es-AR", { dateStyle:"short", timeStyle:"short" }); };

export default function HistorialEmpleado({ empleadoId, cargar, recarga }) {
  const [items, setItems] = useState(null);
  const [todos, setTodos] = useState(false);
  useEffect(() => {
    setItems(null);
    cargar(empleadoId).then(d => setItems(Array.isArray(d) ? d : [])).catch(() => setItems([]));
  // eslint-disable-next-line react-hooks/exhaustive-deps -- cargar llega como funcion nueva en cada render; se recarga por empleadoId y recarga
  }, [empleadoId, recarga]);

  const visibles = (items || []).slice(0, todos ? undefined : 8);
  return (
    <div className="card">
      <div className="card-head"><div className="card-title">🕘 Historial</div></div>
      <div className="card-body">
        {items === null && <div className="empty">Cargando...</div>}
        {items && items.length === 0 && <div className="empty">Sin cambios registrados</div>}
        {visibles.map((h, i) => (
          <div key={i} className="field" style={{alignItems:"flex-start"}}>
            <span className="field-label" style={{minWidth:0}}>
              <span style={{color:"var(--text)",fontWeight:600}}>{h.accion}</span>
              {h.detalle && <span style={{display:"block",fontSize:12,color:"var(--text-muted)",fontWeight:400}}>{h.detalle}</span>}
            </span>
            <span className="field-value" style={{fontSize:11.5,color:"var(--text-muted)"}}>{fmt(h.fecha)}<br/>{h.usuario}</span>
          </div>
        ))}
        {items && items.length > 8 && (
          <button className="btn" style={{marginTop:10,padding:"4px 10px",fontSize:11}} onClick={() => setTodos(v => !v)}>
            {todos ? "Ver menos" : "Ver todo (" + items.length + ")"}
          </button>
        )}
      </div>
    </div>
  );
}
