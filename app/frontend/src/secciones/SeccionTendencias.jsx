// SeccionTendencias.jsx — Pestaña Tendencias (snapshots historicos).
import { useGraficos } from "../graficos";
import { useState, useEffect } from "react";
import { API, apiFetch } from "../api";
import { COL_TEND } from "../ui";

export function SeccionTendencias() {
  const G = useGraficos();
  const [metrica, setMetrica] = useState("total_activos");
  const [metricas, setMetricas] = useState([]);
  const [datos, setDatos] = useState([]);
  const [, setCargando] = useState(true);

  useEffect(()=>{
    apiFetch(`${API}/tendencias/metricas`, {}).then(r=>r.json()).then(m=>setMetricas(Array.isArray(m)?m:[])).catch(()=>{});
  },[]);

  useEffect(()=>{
    setCargando(true);
    apiFetch(`${API}/tendencias?metrica=${encodeURIComponent(metrica)}`, {}).then(r=>r.json()).then(d=>{
      const arr = Array.isArray(d)?d:[];
      const porFecha = {};
      const claves = new Set();
      arr.forEach(x=>{
        if(!porFecha[x.fecha]) porFecha[x.fecha] = { fecha: x.fecha };
        porFecha[x.fecha][x.clave] = x.valor;
        claves.add(x.clave);
      });
      const serie = Object.values(porFecha).sort((a,b)=>a.fecha.localeCompare(b.fecha));
      serie.__claves = [...claves];
      setDatos(serie);
      setCargando(false);
    }).catch(()=>setCargando(false));
  },[metrica]);

  const claves = datos.length ? Object.keys(datos[0]).filter(k=>k!=="fecha") : [];
  const nombreLindo = m => m.replace(/_/g," ").replace(/^\w/, c=>c.toUpperCase());

  return (
    <div>
      <div className="search-bar">
        <select value={metrica} onChange={e=>setMetrica(e.target.value)} style={{minWidth:220}}>
          {metricas.map(m=><option key={m} value={m}>{nombreLindo(m)}</option>)}
        </select>
        <span style={{fontSize:12,color:"var(--text-muted)",alignSelf:"center"}}>
          {datos.length} {datos.length===1?"medicion":"mediciones"} registradas
        </span>
      </div>

      {datos.length < 2 ? (
        <div className="card"><div className="card-body">
          <div className="empty" style={{padding:30}}>
            Todavia no hay suficientes mediciones para graficar una tendencia.<br/>
            <span style={{fontSize:12}}>Se toma una medicion automatica cada lunes a las 2am. Volve la semana que viene para ver la evolucion.</span>
          </div>
        </div></div>
      ) : (
        <div className="card">
          <div className="card-head"><div className="card-title">{nombreLindo(metrica)} — evolucion</div></div>
          <div className="card-body">
            <G.ResponsiveContainer width="100%" height={380}>
              <G.LineChart data={datos}>
                <G.CartesianGrid strokeDasharray="3 3" stroke="var(--border)" vertical={false}/>
                <G.XAxis dataKey="fecha" tick={{fill:"var(--text-muted)",fontSize:11}} axisLine={{stroke:"var(--border)"}}/>
                <G.YAxis tick={{fill:"var(--text-muted)",fontSize:11}} axisLine={{stroke:"var(--border)"}}/>
                <G.Tooltip contentStyle={{borderRadius:8,border:"1px solid var(--border)",background:"var(--surface-2)",color:"var(--text)",fontSize:12}} itemStyle={{color:"var(--text)"}} labelStyle={{color:"var(--text-secondary)"}}/>
                <G.Legend wrapperStyle={{fontSize:11,color:"var(--text-secondary)"}}/>
                {claves.map((k,i)=><G.Line key={k} type="monotone" dataKey={k} stroke={COL_TEND[i%COL_TEND.length]} strokeWidth={2} dot={{r:3}}/>)}
              </G.LineChart>
            </G.ResponsiveContainer>
          </div>
        </div>
      )}

      <div className="card">
        <div className="card-head"><div className="card-title">Detalle por medicion</div></div>
        <div className="table-wrap">
          <table><thead><tr><th>Fecha</th>{claves.map(k=><th key={k}>{k}</th>)}</tr></thead>
          <tbody>
            {datos.length===0 && <tr><td colSpan={claves.length+1}><div className="empty">Sin datos</div></td></tr>}
            {[...datos].reverse().map((d,i)=>(
              <tr key={i}>
                <td style={{fontWeight:600,color:"var(--accent-hover)"}}>{d.fecha}</td>
                {claves.map(k=><td key={k}>{d[k] ?? "-"}</td>)}
              </tr>
            ))}
          </tbody></table>
        </div>
      </div>
    </div>
  );
}
