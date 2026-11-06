// SeccionProyectos.jsx — Pestaña Proyectos: tabla, board y tareas.
import { useState, useEffect } from "react";
import { Plus } from "lucide-react";
import { API, http } from "../api";
import { SEDES, Badge, urlSegura } from "../ui";

export const TIPOS_PROY = ["Infraestructura","Desarrollo","Seguridad","Migracion","Documentacion","Soporte"];
export const ESTADOS_PROY = ["Planificado","En curso","Pausado","Finalizado","Cancelado"];
export const PRIORIDADES = ["Alta","Media","Baja"];
export const ESTADOS_TAREA = ["Pendiente","En proceso","Realizado"];
export const colorEstadoProy = {"Planificado":"#4D7E9E","En curso":"#00AEAE","Pausado":"#c98500","Finalizado":"#6E7A90","Cancelado":"#d03b3b"};
export const estadoProyClass = {"Planificado":"badge-blue","En curso":"badge-green","Pausado":"badge-yellow","Finalizado":"badge-gray","Cancelado":"badge-red"};

export function SeccionProyectos({ assets, puedeEditar = true }) {
  const emptyProy = {nombre:"",descripcion:"",tipo:"",estado:"Planificado",prioridad:"Media",sede:"",
                     fecha_inicio:"",fecha_fin_est:"",avance:0,link_sharepoint:"",comentarios:"",link_ticket:"",recursos:"",
                     responsables:[],activos:[]};
  const [proyectos, setProyectos] = useState([]);
  const [equipo, setEquipo] = useState([]);
  const [cargando, setCargando] = useState(true);
  const [form, setForm] = useState(emptyProy);
  const [editando, setEditando] = useState(null);
  const [buscar, setBuscar] = useState("");
  const [fEstado, setFEstado] = useState("");
  const [buscarAsset, setBuscarAsset] = useState("");
  const [expandido, setExpandido] = useState(null);
  const [nuevaTarea, setNuevaTarea] = useState({titulo:"",responsable:"",fecha_limite:"",notas:""});
  const [vista, setVista] = useState("tabla");
  const [arrastrando, setArrastrando] = useState(null);
  const [sobreCol, setSobreCol] = useState(null);

  function cargar(){
    setCargando(true);
    http.get(API+"/proyectos").then(d=>setProyectos(Array.isArray(d)?d:[])).catch(()=>{}).finally(()=>setCargando(false));
  }
  useEffect(()=>{
    cargar();
    http.get(API+"/equipo").then(d=>setEquipo(Array.isArray(d)?d:[])).catch(()=>{});
  },[]);

  function abrirNuevo(){ setForm(emptyProy); setBuscarAsset(""); setEditando({}); }
  function abrirEditar(p){
    setForm({...p, responsables:p.responsables||[], activos:(p.activos||[]).map(a=>a.id)});
    setBuscarAsset(""); setEditando(p);
  }
  function cerrar(){ setEditando(null); setForm(emptyProy); setBuscarAsset(""); }

  function toggleResp(u){
    setForm(f=>({...f, responsables: f.responsables.includes(u) ? f.responsables.filter(x=>x!==u) : [...f.responsables,u]}));
  }
  function agregarAsset(id){
    if(id && !form.activos.includes(id)) setForm(f=>({...f, activos:[...f.activos,id]}));
    setBuscarAsset("");
  }
  function quitarAsset(id){ setForm(f=>({...f, activos:f.activos.filter(x=>x!==id)})); }

  async function guardar(){
    if(!form.nombre || form.nombre.trim().length<3){ alert("El nombre del proyecto es obligatorio (min 3 caracteres)."); return; }
    const body = {...form, avance: parseInt(form.avance)||0, tipo: form.tipo||null};
    try{
      if(editando && editando.id) await http.put(API+"/proyectos/"+editando.id, body);
      else await http.post(API+"/proyectos", body);
      cerrar(); cargar();
    } catch(e){ alert("Error al guardar: "+e.message); }
  }
  async function eliminar(p){
    if(!confirm("Eliminar el proyecto \""+p.nombre+"\"?")) return;
    try{ await http.del(API+"/proyectos/"+p.id); cargar(); }
    catch(e){ alert("Error al eliminar: "+e.message); }
  }

  function reemplazar(p){ setProyectos(ps=>ps.map(x=>x.id===p.id?p:x)); }
  async function agregarTarea(pid){
    if(!nuevaTarea.titulo.trim()){ alert("Escribi el titulo de la tarea."); return; }
    try{
      const p = await http.post(API+"/proyectos/"+pid+"/tareas", nuevaTarea);
      reemplazar(p); setNuevaTarea({titulo:"",responsable:"",fecha_limite:"",notas:""});
    } catch(e){ alert("Error: "+e.message); }
  }
  async function toggleTarea(t){
    try{
      const p = await http.put(API+"/tareas/"+t.id, {...t, completada: !t.completada});
      reemplazar(p);
    } catch(e){ alert("Error: "+e.message); }
  }
  async function borrarTarea(t){
    if(!confirm("Eliminar la tarea \""+t.titulo+"\"?")) return;
    try{ const p = await http.del(API+"/tareas/"+t.id); reemplazar(p); }
    catch(e){ alert("Error: "+e.message); }
  }

  async function moverProyecto(p, estado){
    if(p.estado===estado) return;
    try{
      const r = await http.put(API+"/proyectos/"+p.id, {...p, estado, activos:(p.activos||[]).map(a=>a.id)});
      reemplazar(r);
    } catch(e){ alert("Error: "+e.message); }
  }
  async function moverTarea(t, estado){
    if(t.estado===estado) return;
    try{ const p = await http.put(API+"/tareas/"+t.id, {...t, estado}); reemplazar(p); }
    catch(e){ alert("Error: "+e.message); }
  }

  async function exportar(){
    try{
      const ExcelJS = (await import("exceljs")).default; // se carga recien al exportar
      const wb = new ExcelJS.Workbook();
      const ws = wb.addWorksheet("Proyectos");
      ws.columns = [
        {header:"N Proyecto",key:"numero",width:15},
        {header:"Proyecto",key:"nombre",width:34},
        {header:"Tipo",key:"tipo",width:16},
        {header:"Estado",key:"estado",width:14},
        {header:"Prioridad",key:"prioridad",width:11},
        {header:"Avance %",key:"avance_efectivo",width:10},
        {header:"Tareas",key:"tareasTxt",width:12},
        {header:"Responsables",key:"resp",width:34},
        {header:"Sede",key:"sede",width:13},
        {header:"Inicio",key:"fecha_inicio",width:12},
        {header:"Fin estimado",key:"fecha_fin_est",width:13},
        {header:"Activos",key:"acts",width:36},
        {header:"Otros recursos",key:"recursos",width:30},
        {header:"Ticket",key:"link_ticket",width:30},
        {header:"Descripcion",key:"descripcion",width:44},
        {header:"SharePoint",key:"link_sharepoint",width:34},
        {header:"Comentarios",key:"comentarios",width:44}
      ];
      const nomb = {}; equipo.forEach(e=>{ nomb[e.username]=e.nombre; });
      filtrados.forEach(p=>ws.addRow({...p,
        tareasTxt: p.tiene_tareas ? (p.tareas_hechas+"/"+p.tareas_total) : "",
        resp:(p.responsables||[]).map(r=>nomb[r]||r).join(", "),
        acts:(p.activos||[]).map(a=>a.nombre||a.id).join(", ")}));
      ws.getRow(1).font={bold:true,color:{argb:"FFFFFFFF"}};
      ws.getRow(1).eachCell(c=>{c.fill={type:"pattern",pattern:"solid",fgColor:{argb:"FF0B7285"}};});
      const buf = await wb.xlsx.writeBuffer();
      const url = URL.createObjectURL(new Blob([buf],{type:"application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"}));
      const a = document.createElement("a"); a.href=url; a.download="proyectos.xlsx"; a.click();
      URL.revokeObjectURL(url);
    } catch(e){ alert("Error al exportar: "+e.message); }
  }

  const q = buscar.trim().toLowerCase();
  const filtrados = proyectos.filter(p=>
    (!q || [p.numero,p.nombre,p.descripcion,p.tipo,p.sede,p.recursos,(p.responsables||[]).join(" ")].some(x=>(x||"").toLowerCase().includes(q)))
    && (!fEstado || p.estado===fEstado));
  const nombresEquipo = {}; equipo.forEach(e=>{ nombresEquipo[e.username]=e.nombre; });
  const assetsFiltrados = buscarAsset.trim().length<2 ? [] :
    assets.filter(a=>[a.nombre,a.serial,a.usuario].some(x=>(x||"").toLowerCase().includes(buscarAsset.trim().toLowerCase()))).slice(0,8);

  return (
    <div>
      <div style={{display:"flex",gap:10,marginBottom:14,alignItems:"center",flexWrap:"wrap"}}>
        <input placeholder="Buscar proyecto, responsable, sede..." value={buscar} onChange={e=>setBuscar(e.target.value)} style={{flex:1,minWidth:240}}/>
        <select value={fEstado} onChange={e=>setFEstado(e.target.value)}>
          <option value="">Todos los estados</option>
          {ESTADOS_PROY.map(e=><option key={e}>{e}</option>)}
        </select>
        <span style={{color:"var(--text-muted)",fontSize:12}}>{filtrados.length} proyectos</span>
        <div style={{display:"flex",border:"1px solid var(--border-strong)",borderRadius:6,overflow:"hidden"}}>
          {[["tabla","Tabla"],["board","Board"]].map(([k,l])=>(
            <span key={k} onClick={()=>setVista(k)} style={{padding:"6px 14px",fontSize:12.5,cursor:"pointer",fontWeight:600,
              background:vista===k?"var(--accent-soft)":"transparent",
              color:vista===k?"var(--accent-hover)":"var(--text-muted)"}}>{l}</span>
          ))}
        </div>
        <button className="btn" onClick={exportar}>Exportar Excel</button>
        {puedeEditar && <button className="btn btn-primary" onClick={abrirNuevo}><Plus size={13} strokeWidth={2}/>Nuevo proyecto</button>}
      </div>

      {editando && (
        <div className="card" style={{padding:16,marginBottom:16,border:"1px solid var(--accent-hover)"}}>
          <div className="form-cols" style={{display:"grid",gridTemplateColumns:"2fr 1fr 1fr 1fr",gap:12,marginBottom:12}}>
            <div><label style={{fontSize:12,color:"var(--text-muted)"}}>Proyecto *</label>
              <input value={form.nombre} onChange={e=>setForm({...form,nombre:e.target.value})} style={{width:"100%"}}/></div>
            <div><label style={{fontSize:12,color:"var(--text-muted)"}}>Tipo</label>
              <select value={form.tipo||""} onChange={e=>setForm({...form,tipo:e.target.value})} style={{width:"100%"}}>
                <option value="">-----</option>{TIPOS_PROY.map(t=><option key={t}>{t}</option>)}</select></div>
            <div><label style={{fontSize:12,color:"var(--text-muted)"}}>Estado</label>
              <select value={form.estado} onChange={e=>setForm({...form,estado:e.target.value})} style={{width:"100%"}}>
                {ESTADOS_PROY.map(t=><option key={t}>{t}</option>)}</select></div>
            <div><label style={{fontSize:12,color:"var(--text-muted)"}}>Prioridad</label>
              <select value={form.prioridad} onChange={e=>setForm({...form,prioridad:e.target.value})} style={{width:"100%"}}>
                {PRIORIDADES.map(t=><option key={t}>{t}</option>)}</select></div>
          </div>
          <div className="form-cols" style={{display:"grid",gridTemplateColumns:"1fr 1fr 1fr 1fr",gap:12,marginBottom:12}}>
            <div><label style={{fontSize:12,color:"var(--text-muted)"}}>Sede</label>
              <select value={form.sede} onChange={e=>setForm({...form,sede:e.target.value})} style={{width:"100%"}}>
                <option value="">-----</option>{SEDES.map(s=><option key={s}>{s}</option>)}</select></div>
            <div><label style={{fontSize:12,color:"var(--text-muted)"}}>Fecha inicio</label>
              <input type="date" value={form.fecha_inicio||""} onChange={e=>setForm({...form,fecha_inicio:e.target.value})} style={{width:"100%"}}/></div>
            <div><label style={{fontSize:12,color:"var(--text-muted)"}}>Fin estimado</label>
              <input type="date" value={form.fecha_fin_est||""} onChange={e=>setForm({...form,fecha_fin_est:e.target.value})} style={{width:"100%"}}/></div>
            <div><label style={{fontSize:12,color:"var(--text-muted)"}}>Avance %{editando&&editando.tiene_tareas?" (segun tareas)":""}</label>
              <input type="number" min="0" max="100" value={editando&&editando.tiene_tareas?(editando.avance_efectivo||0):form.avance}
                disabled={!!(editando&&editando.tiene_tareas)}
                onChange={e=>setForm({...form,avance:e.target.value})} style={{width:"100%"}}/></div>
          </div>
          <div style={{marginBottom:12}}>
            <label style={{fontSize:12,color:"var(--text-muted)"}}>Equipo responsable</label>
            <div style={{display:"flex",gap:8,flexWrap:"wrap",marginTop:6}}>
              {equipo.map(u=>(
                <span key={u.username} onClick={()=>toggleResp(u.username)}
                  style={{fontSize:12,cursor:"pointer",padding:"5px 11px",borderRadius:20,userSelect:"none",
                  border:"1px solid "+(form.responsables.includes(u.username)?"var(--accent-hover)":"var(--border-strong)"),
                  background:form.responsables.includes(u.username)?"var(--accent-soft)":"transparent",
                  color:form.responsables.includes(u.username)?"var(--accent-hover)":"var(--text-muted)"}}>{u.nombre}</span>
              ))}
            </div>
          </div>
          <div style={{marginBottom:12}}>
            <label style={{fontSize:12,color:"var(--text-muted)"}}>Activos vinculados</label>
            <input value={buscarAsset} onChange={e=>setBuscarAsset(e.target.value)} placeholder="Buscar por nombre, serial o usuario..." style={{width:"100%",marginTop:4}}/>
            {assetsFiltrados.length>0 && (
              <div style={{border:"1px solid var(--border-strong)",borderRadius:6,marginTop:4,maxHeight:150,overflowY:"auto"}}>
                {assetsFiltrados.map(a=>(
                  <div key={a.id} onClick={()=>agregarAsset(a.id)} style={{padding:"6px 10px",cursor:"pointer",fontSize:12.5,borderBottom:"1px solid var(--border)"}}>
                    <b>{a.nombre||"(sin nombre)"}</b> <span style={{color:"var(--text-muted)"}}>{a.tipo} · {a.serial} · {a.usuario}</span>
                  </div>
                ))}
              </div>
            )}
            <div style={{display:"flex",gap:6,flexWrap:"wrap",marginTop:8}}>
              {form.activos.map(id=>{
                const a = assets.find(x=>x.id===id);
                return <span key={id} style={{fontSize:11.5,padding:"4px 9px",borderRadius:14,background:"var(--accent-soft)",color:"var(--accent-hover)"}}>
                  {a?(a.nombre||a.serial||id):id} <b onClick={()=>quitarAsset(id)} style={{cursor:"pointer",marginLeft:4}}>x</b></span>;
              })}
            </div>
          </div>
          <div className="form-cols" style={{display:"grid",gridTemplateColumns:"1fr 1fr",gap:12,marginBottom:12}}>
            <div><label style={{fontSize:12,color:"var(--text-muted)"}}>Descripcion</label>
              <textarea style={{height:60,width:"100%"}} value={form.descripcion} onChange={e=>setForm({...form,descripcion:e.target.value})}/></div>
            <div><label style={{fontSize:12,color:"var(--text-muted)"}}>Comentarios</label>
              <textarea style={{height:60,width:"100%"}} value={form.comentarios} onChange={e=>setForm({...form,comentarios:e.target.value})}/></div>
          </div>
          <div style={{marginBottom:12}}>
            <label style={{fontSize:12,color:"var(--text-muted)"}}>Otros recursos (apps, webs, servicios que no estan en inventario)</label>
            <input value={form.recursos||""} onChange={e=>setForm({...form,recursos:e.target.value})} placeholder="Ej: Portal de Facturacion, SharePoint RRHH, API Tango" style={{width:"100%"}}/>
          </div>
          <div style={{marginBottom:12}}>
            <label style={{fontSize:12,color:"var(--text-muted)"}}>Ticket Portalgo (URL)</label>
            <input value={form.link_ticket||""} onChange={e=>setForm({...form,link_ticket:e.target.value})} placeholder="https://..." style={{width:"100%"}}/>
          </div>
          <div style={{marginBottom:12}}>
            <label style={{fontSize:12,color:"var(--text-muted)"}}>Repositorio SharePoint</label>
            <input value={form.link_sharepoint} onChange={e=>setForm({...form,link_sharepoint:e.target.value})} placeholder="https://llyasoc.sharepoint.com/..." style={{width:"100%"}}/>
          </div>
          <div style={{display:"flex",gap:8}}>
            <button className="btn btn-primary" onClick={guardar}>Guardar</button>
            <button className="btn" onClick={cerrar}>Cancelar</button>
          </div>
        </div>
      )}

      {vista==="board" && (
        <div style={{display:"flex",gap:14,overflowX:"auto",paddingBottom:10}}>
          {ESTADOS_PROY.map(col=>{
            const enCol = filtrados.filter(p=>p.estado===col);
            return (
            <div key={col} onDragOver={e=>{e.preventDefault(); setSobreCol(col);}} onDragLeave={()=>setSobreCol(null)}
              onDrop={e=>{e.preventDefault(); setSobreCol(null); if(arrastrando&&arrastrando.tipo==="proy") moverProyecto(arrastrando.item, col);}}
              style={{flex:"0 0 280px",minHeight:180,borderRadius:8,padding:"10px 12px",
                background:sobreCol===col?"var(--accent-soft)":"rgba(255,255,255,0.02)",
                border:"1px solid "+(sobreCol===col?"var(--accent-hover)":"var(--border)"),transition:"all .15s"}}>
              <div style={{display:"flex",alignItems:"center",gap:8,marginBottom:12}}>
                <span style={{width:9,height:9,borderRadius:"50%",background:colorEstadoProy[col]||"#888"}}/>
                <span style={{fontSize:13.5,fontWeight:700}}>{col}</span>
                <span style={{marginLeft:"auto",fontSize:11.5,color:"var(--text-muted)"}}>{enCol.length}</span>
              </div>
              {enCol.map(p=>(
                <div key={p.id} draggable onDragStart={()=>setArrastrando({tipo:"proy",item:p})} onDragEnd={()=>{setArrastrando(null);setSobreCol(null);}}
                  onClick={()=>setExpandido(expandido===p.id?null:p.id)}
                  style={{background:"var(--card, rgba(255,255,255,0.04))",border:"1px solid var(--border)",borderRadius:7,
                    padding:"11px 13px",marginBottom:9,cursor:"grab",borderLeft:"3px solid "+(colorEstadoProy[col]||"#888")}}>
                  <div style={{fontSize:10.5,color:"var(--text-muted)",marginBottom:3}}>{p.numero}</div>
                  <div style={{fontSize:13,fontWeight:600,lineHeight:1.35,marginBottom:6}}>{p.nombre}</div>
                  {p.descripcion&&<div style={{fontSize:11.5,color:"var(--text-muted)",marginBottom:8,lineHeight:1.35}}>{p.descripcion.substring(0,80)}{p.descripcion.length>80?"...":""}</div>}
                  <div style={{background:"var(--border)",borderRadius:10,height:5,overflow:"hidden",marginBottom:6}}>
                    <div style={{width:(p.avance_efectivo||0)+"%",height:"100%",background:colorEstadoProy[col]||"var(--accent-hover)"}}/>
                  </div>
                  <div style={{display:"flex",alignItems:"center",gap:6,flexWrap:"wrap"}}>
                    <span style={{fontSize:10.5,color:"var(--text-muted)"}}>{p.avance_efectivo||0}%{p.tiene_tareas?" · "+p.tareas_hechas+"/"+p.tareas_total:""}</span>
                    {p.fecha_fin_est&&<span style={{fontSize:10,padding:"2px 6px",borderRadius:4,
                      background:new Date(p.fecha_fin_est)<new Date()&&p.estado!=="Finalizado"?"#d03b3b":"var(--border)",
                      color:new Date(p.fecha_fin_est)<new Date()&&p.estado!=="Finalizado"?"#fff":"var(--text-muted)"}}>{p.fecha_fin_est}</span>}
                    <span style={{marginLeft:"auto",display:"flex",gap:3}}>
                      {(p.responsables||[]).slice(0,3).map(r=>(
                        <span key={r} title={nombresEquipo[r]||r} style={{width:22,height:22,borderRadius:"50%",background:"var(--accent-hover)",
                          color:"#fff",fontSize:9.5,fontWeight:700,display:"flex",alignItems:"center",justifyContent:"center"}}>
                          {(nombresEquipo[r]||r).split(" ").map(x=>x[0]).slice(0,2).join("").toUpperCase()}</span>
                      ))}
                    </span>
                  </div>
                </div>
              ))}
            </div>);
          })}
        </div>
      )}

      {vista==="board" && expandido && (()=>{
        const p = filtrados.find(x=>x.id===expandido);
        if(!p) return null;
        return (
        <div style={{marginTop:20,paddingTop:16,borderTop:"1px solid var(--border)"}}>
          <div style={{fontSize:13.5,fontWeight:700,marginBottom:12,color:"var(--accent-hover)"}}>Tareas · {p.numero} {p.nombre}</div>
          <div style={{display:"flex",gap:14,overflowX:"auto"}}>
            {ESTADOS_TAREA.map(col=>{
              const tk = (p.tareas||[]).filter(t=>(t.estado||"Pendiente")===col);
              return (
              <div key={col} onDragOver={e=>{e.preventDefault(); setSobreCol("t"+col);}} onDragLeave={()=>setSobreCol(null)}
                onDrop={e=>{e.preventDefault(); setSobreCol(null); if(arrastrando&&arrastrando.tipo==="tarea") moverTarea(arrastrando.item, col);}}
                style={{flex:"0 0 260px",minHeight:120,borderRadius:8,padding:"10px 12px",
                  background:sobreCol==="t"+col?"var(--accent-soft)":"rgba(255,255,255,0.02)",
                  border:"1px solid "+(sobreCol==="t"+col?"var(--accent-hover)":"var(--border)")}}>
                <div style={{display:"flex",marginBottom:10}}>
                  <span style={{fontSize:12.5,fontWeight:700}}>{col}</span>
                  <span style={{marginLeft:"auto",fontSize:11,color:"var(--text-muted)"}}>{tk.length}</span>
                </div>
                {tk.map(t=>(
                  <div key={t.id} draggable onDragStart={()=>setArrastrando({tipo:"tarea",item:t})} onDragEnd={()=>{setArrastrando(null);setSobreCol(null);}}
                    style={{background:"var(--card, rgba(255,255,255,0.04))",border:"1px solid var(--border)",borderRadius:6,
                      padding:"9px 11px",marginBottom:8,cursor:"grab"}}>
                    <div style={{marginBottom:7,fontSize:12.5,lineHeight:1.4}}>
                      <input type="checkbox" checked={col==="Realizado"} title="Marcar como realizada"
                        onChange={()=>moverTarea(t, col==="Realizado"?"Pendiente":"Realizado")}
                        style={{cursor:"pointer",width:13,height:13,verticalAlign:"middle",margin:"0 7px 0 0"}}/>
                      <span style={{verticalAlign:"middle",textDecoration:col==="Realizado"?"line-through":"none",opacity:col==="Realizado"?0.55:1}}>{t.titulo}</span>
                    </div>
                    <div style={{display:"flex",alignItems:"center",gap:6}}>
                      {t.fecha_limite&&<span style={{fontSize:10,padding:"2px 6px",borderRadius:4,
                        background:new Date(t.fecha_limite)<new Date()&&col!=="Realizado"?"#d03b3b":"var(--border)",
                        color:new Date(t.fecha_limite)<new Date()&&col!=="Realizado"?"#fff":"var(--text-muted)"}}>{t.fecha_limite}</span>}
                      {t.responsable&&<span title={nombresEquipo[t.responsable]||t.responsable}
                        style={{marginLeft:"auto",width:21,height:21,borderRadius:"50%",background:"var(--accent-hover)",color:"#fff",
                        fontSize:9,fontWeight:700,display:"flex",alignItems:"center",justifyContent:"center"}}>
                        {(nombresEquipo[t.responsable]||t.responsable).split(" ").map(x=>x[0]).slice(0,2).join("").toUpperCase()}</span>}
                      {puedeEditar&&col!=="En proceso"&&<button className="btn" title="Mover a En proceso" style={{padding:"1px 6px",fontSize:10}} onClick={()=>moverTarea(t,"En proceso")}>→</button>}
                      {puedeEditar && <button className="btn" style={{padding:"1px 6px",fontSize:10,color:"#d03b3b",borderColor:"#d03b3b"}} onClick={()=>borrarTarea(t)}>x</button>}
                    </div>
                  </div>
                ))}
                {puedeEditar && col==="Pendiente" && (
                  <div style={{marginTop:8}}>
                    <input placeholder="+ Nueva tarea" value={nuevaTarea.titulo} onChange={e=>setNuevaTarea({...nuevaTarea,titulo:e.target.value})}
                      onKeyDown={e=>{ if(e.key==="Enter") agregarTarea(p.id); }} style={{width:"100%",fontSize:12}}/>
                  </div>
                )}
              </div>);
            })}
          </div>
        </div>);
      })()}

      {vista==="tabla" && (
      <div className="table-wrap">
        <table><thead><tr>
          <th>N°</th><th>Proyecto</th><th>Tipo</th><th>Estado</th><th>Prior.</th><th>Avance</th>
          <th>Responsables</th><th>Activos</th><th>Fin est.</th><th></th>
        </tr></thead>
        <tbody>
          {!cargando && filtrados.length===0 && <tr><td colSpan="10"><div className="empty">Sin proyectos cargados</div></td></tr>}
          {filtrados.map(p=>(
            <tr key={p.id}>
              <td className="td-muted" style={{whiteSpace:"nowrap",fontSize:11.5}}>{p.numero}</td>
              <td><b>{p.nombre}</b>{p.descripcion&&<div style={{fontSize:11.5,color:"var(--text-muted)",marginTop:2}}>{p.descripcion.substring(0,70)}{p.descripcion.length>70?"...":""}</div>}</td>
              <td className="td-muted">{p.tipo}</td>
              <td><Badge label={p.estado} map={estadoProyClass}/></td>
              <td className="td-muted">{p.prioridad}</td>
              <td style={{minWidth:90}}>
                <div style={{background:"var(--border)",borderRadius:10,height:6,overflow:"hidden"}}>
                  <div style={{width:(p.avance_efectivo||0)+"%",height:"100%",background:"var(--accent-hover)"}}/>
                </div>
                <span style={{fontSize:11,color:"var(--text-muted)"}}>{p.avance_efectivo||0}%{p.tiene_tareas?" ("+p.tareas_hechas+"/"+p.tareas_total+")":""}</span>
              </td>
              <td className="td-muted" style={{fontSize:12}}>{(p.responsables||[]).map(r=>nombresEquipo[r]||r).join(", ")}</td>
              <td className="td-muted" style={{fontSize:12}}>{[...(p.activos||[]).map(a=>a.nombre||a.id), ...(p.recursos?[p.recursos]:[])].join(", ")}</td>
              <td className="td-muted" style={{whiteSpace:"nowrap"}}>{p.fecha_fin_est}</td>
              <td style={{whiteSpace:"nowrap"}}>
                {urlSegura(p.link_ticket) && <a href={urlSegura(p.link_ticket)} target="_blank" rel="noreferrer" className="btn" style={{padding:"4px 8px",fontSize:12,textDecoration:"none",marginRight:6}}>Ticket</a>}
                {urlSegura(p.link_sharepoint) && <a href={urlSegura(p.link_sharepoint)} target="_blank" rel="noreferrer" className="btn" style={{padding:"4px 8px",fontSize:12,textDecoration:"none"}}>SP</a>}
                <button className="btn" style={{padding:"4px 8px",fontSize:12,marginLeft:6}} onClick={()=>setExpandido(expandido===p.id?null:p.id)}>Tareas{p.tiene_tareas?" ("+p.tareas_hechas+"/"+p.tareas_total+")":""}</button>
                {puedeEditar && <button className="btn" style={{padding:"4px 8px",fontSize:12,marginLeft:6}} onClick={()=>abrirEditar(p)}>Editar</button>}
                {puedeEditar && <button className="btn" style={{padding:"4px 8px",fontSize:12,marginLeft:6,color:"#d03b3b",borderColor:"#d03b3b"}} onClick={()=>eliminar(p)}>Quitar</button>}
              </td>
            </tr>
          ))}
          {filtrados.map(p=>expandido===p.id&&(
            <tr key={p.id+"-t"}>
              <td colSpan="10" style={{background:"var(--bg-soft, rgba(0,0,0,0.15))",padding:"14px 18px"}}>
                <div style={{fontSize:12.5,fontWeight:600,marginBottom:10,color:"var(--accent-hover)"}}>Tareas de {p.nombre}</div>
                {(p.tareas||[]).length===0 && <div style={{fontSize:12,color:"var(--text-muted)",marginBottom:10}}>Sin tareas cargadas. El avance se carga a mano.</div>}
                {(p.tareas||[]).map(t=>(
                  <div key={t.id} style={{display:"flex",alignItems:"center",gap:10,padding:"6px 0",borderBottom:"1px solid var(--border)"}}>
                    <input type="checkbox" checked={t.completada} disabled={!puedeEditar} onChange={()=>toggleTarea(t)} style={{cursor:puedeEditar?"pointer":"default"}}/>
                    <span style={{flex:1,fontSize:13,textDecoration:t.completada?"line-through":"none",opacity:t.completada?0.55:1}}>{t.titulo}</span>
                    {t.responsable&&<span style={{fontSize:11,color:"var(--text-muted)"}}>{nombresEquipo[t.responsable]||t.responsable}</span>}
                    {t.fecha_limite&&<span style={{fontSize:11,color:"var(--text-muted)"}}>{t.fecha_limite}</span>}
                    {t.notas&&<span style={{fontSize:11,color:"var(--text-muted)",fontStyle:"italic"}}>{t.notas.substring(0,40)}</span>}
                    {puedeEditar && <button className="btn" style={{padding:"2px 7px",fontSize:11,color:"#d03b3b",borderColor:"#d03b3b"}} onClick={()=>borrarTarea(t)}>x</button>}
                  </div>
                ))}
                {puedeEditar && <div style={{display:"flex",gap:8,marginTop:12,flexWrap:"wrap"}}>
                  <input placeholder="Nueva tarea..." value={nuevaTarea.titulo} onChange={e=>setNuevaTarea({...nuevaTarea,titulo:e.target.value})}
                    onKeyDown={e=>{ if(e.key==="Enter") agregarTarea(p.id); }} style={{flex:2,minWidth:200,fontSize:13}}/>
                  <select value={nuevaTarea.responsable} onChange={e=>setNuevaTarea({...nuevaTarea,responsable:e.target.value})} style={{fontSize:13}}>
                    <option value="">Responsable...</option>
                    {equipo.map(u=><option key={u.username} value={u.username}>{u.nombre}</option>)}
                  </select>
                  <input type="date" value={nuevaTarea.fecha_limite} onChange={e=>setNuevaTarea({...nuevaTarea,fecha_limite:e.target.value})} style={{fontSize:13}}/>
                  <input placeholder="Notas" value={nuevaTarea.notas} onChange={e=>setNuevaTarea({...nuevaTarea,notas:e.target.value})} style={{flex:1,minWidth:120,fontSize:13}}/>
                  <button className="btn btn-primary" style={{fontSize:12.5}} onClick={()=>agregarTarea(p.id)}>Agregar</button>
                </div>}
              </td>
            </tr>
          ))}
        </tbody></table>
      </div>
      )}
    </div>
  );
}
