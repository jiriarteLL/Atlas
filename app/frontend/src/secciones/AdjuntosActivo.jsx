// AdjuntosActivo.jsx — Archivos adjuntos de la ficha del activo.
import { useState, useEffect, useRef } from "react";
import { API, authHeaders, chequear401 } from "../api";

export function AdjuntosActivo({ assetId, usuario }) {
  const [items, setItems] = useState([]);
  const [subiendo, setSubiendo] = useState(false);
  const [desc, setDesc] = useState("");
  const inputRef = useRef(null);
  const BASE = API.replace("/api","");

  function cargar(){
    fetch(`${BASE}/api/assets/${assetId}/adjuntos`, { headers: authHeaders() }).then(r=>r.json()).then(d=>setItems(Array.isArray(d)?d:[])).catch(()=>{});
  }
  // eslint-disable-next-line react-hooks/exhaustive-deps -- recarga solo al cambiar de activo
  useEffect(()=>{ if(assetId) cargar(); }, [assetId]);

  // La descarga exige el token, asi que no puede ser un link directo: se baja con fetch.
  // PDF e imagenes se abren en una pestana nueva (abierta en el mismo click para que el
  // navegador no la bloquee); el resto se descarga con su nombre original.
  const SE_ABRE = ["pdf","jpg","jpeg","png","gif","webp","txt"];
  async function abrir(a){
    const enPestana = SE_ABRE.includes((a.tipo||"").toLowerCase());
    const w = enPestana ? window.open("", "_blank") : null;
    try{
      const r = await fetch(`${BASE}/api/adjuntos/${a.id}/descargar`, { headers: authHeaders() }).then(chequear401);
      if(!r.ok) throw new Error(r.status===404 ? "El archivo ya no existe" : "Error al descargar");
      const url = URL.createObjectURL(await r.blob());
      if(w){ w.location.href = url; }
      else { const l = document.createElement("a"); l.href = url; l.download = a.nombre; l.click(); }
      setTimeout(()=>URL.revokeObjectURL(url), 60000);
    } catch(e){ if(w) w.close(); alert(e.message); }
  }

  async function subir(e){
    const f = e.target.files && e.target.files[0];
    if(!f) return;
    if(f.size > 10*1024*1024){ alert("El archivo pesa "+(f.size/1048576).toFixed(1)+" MB y el maximo permitido es 10 MB."); e.target.value=""; return; }
    setSubiendo(true);
    try{
      const fd = new FormData();
      fd.append("file", f);
      fd.append("descripcion", desc);
      fd.append("usuario", usuario || "web");
      const r = await fetch(`${BASE}/api/assets/${assetId}/adjuntos`, { method:"POST", body: fd, headers: authHeaders() }).then(chequear401);
      if(!r.ok){ const d = await r.json().catch(()=>({})); throw new Error(d.detail || "Error al subir"); }
      setDesc(""); if(inputRef.current) inputRef.current.value="";
      cargar();
    } catch(err){ alert(err.message); }
    setSubiendo(false);
  }

  async function borrar(a){
    if(!confirm(`Eliminar "${a.nombre}"?`)) return;
    try{ await fetch(`${BASE}/api/adjuntos/${a.id}?usuario=${encodeURIComponent(usuario||"web")}`, {method:"DELETE", headers: authHeaders()}).then(chequear401); cargar(); }
    catch { alert("Error al eliminar"); }
  }

  const kb = n => n < 1024*1024 ? (n/1024).toFixed(0)+" KB" : (n/1048576).toFixed(1)+" MB";

  return (
    <div className="card">
      <div className="card-head"><div className="card-title">Archivos adjuntos ({items.length})</div></div>
      <div className="card-body">
        <div style={{display:"flex",gap:8,flexWrap:"wrap",alignItems:"center",marginBottom:10}}>
          <input ref={inputRef} type="file" onChange={subir} disabled={subiendo} style={{flex:1,minWidth:200}}/>
          <input placeholder="Descripcion (opcional)" value={desc} onChange={e=>setDesc(e.target.value)} style={{flex:1,minWidth:160}}/>
        </div>
        <div style={{fontSize:11,color:"var(--text-muted)",marginBottom:12}}>
          Maximo 10 MB por archivo. Formatos: PDF, imagenes (jpg, png, gif, webp), Excel, Word, txt, csv.
          {subiendo && <span style={{color:"var(--accent-hover)",marginLeft:8}}>Subiendo...</span>}
        </div>
        {items.length===0 ? <div className="empty" style={{padding:14}}>Sin archivos adjuntos</div> : (
          <table><thead><tr><th>Archivo</th><th>Descripcion</th><th>Tamano</th><th>Subido por</th><th></th></tr></thead>
          <tbody>
            {items.map(a=>(
              <tr key={a.id}>
                <td><a href="#" onClick={e=>{e.preventDefault();abrir(a);}} style={{color:"var(--accent-hover)",fontWeight:600}}>{a.nombre}</a></td>
                <td className="td-muted">{a.descripcion}</td>
                <td className="td-small">{kb(a.tamano)}</td>
                <td className="td-small">{a.subido_por}</td>
                <td><button className="btn" style={{padding:"3px 8px",fontSize:11,color:"#d03b3b",borderColor:"#d03b3b"}} onClick={()=>borrar(a)}>Quitar</button></td>
              </tr>
            ))}
          </tbody></table>
        )}
      </div>
    </div>
  );
}
