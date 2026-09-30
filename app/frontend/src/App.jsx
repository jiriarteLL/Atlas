import React, { useState, useEffect, useRef } from "react";
import { useGraficos } from "./graficos";
import { useAuth, tienePermiso } from "./AuthContext";
import { LayoutGrid, Laptop, BarChart3, Bot, Settings, Power, Menu, Upload, Download, RefreshCw, Plus, FolderKanban, UserCircle } from "lucide-react";
import { useTablaTarjetas } from "./tablaTarjetas";
import { API, AUTH, apiFetch, http, setUsuarioActual } from "./api";
import { SEDES, COLORES, TIPOS, estadoClass, Badge, QR, Field, emptyAsset, fmtDate } from "./ui";
import { SeccionTendencias } from "./secciones/SeccionTendencias";
import { AdjuntosActivo } from "./secciones/AdjuntosActivo";
import { HistorialActivo } from "./secciones/HistorialActivo";
import { SeccionProyectos } from "./secciones/SeccionProyectos";
import { SeccionPerfil } from "./secciones/SeccionPerfil";
import "./styles.css";

const MODOS = [["","Oscuro"],["medianoche","Medianoche"],["neutro","Neutro"],["claro","Claro"]];
const SWATCHES = [["","Teal","#00B0B9","#35d0d8"],["violeta","Violeta","#6366F1","#a855f7"],
                  ["azul","Azul","#3B82F6","#60A5FA"],["verde","Verde","#10B981","#34D399"],
                  ["ambar","Ambar","#F59E0B","#FBBF24"]];

export default function App() {
  useTablaTarjetas();
  const G = useGraficos();
  const [panelTema, setPanelTema] = useState(false);
  const [modo, setModo] = useState(() => localStorage.getItem("abm_modo") || "");
  const [colorTema, setColorTema] = useState(() => localStorage.getItem("abm_color") || "");
  useEffect(()=>{
    const h = document.documentElement;
    if(modo) h.setAttribute("data-modo", modo); else h.removeAttribute("data-modo");
    localStorage.setItem("abm_modo", modo);
  },[modo]);
  useEffect(()=>{
    const h = document.documentElement;
    if(colorTema) h.setAttribute("data-color", colorTema); else h.removeAttribute("data-color");
    localStorage.setItem("abm_color", colorTema);
  },[colorTema]);
  const [tab, setTab] = useState(() => ((window.location.hash || "").replace("#","").split("/")[0]) || "dashboard");
  const [assets, setAssets] = useState([]);
  const [loading, setLoading] = useState(true);
  const [search, setSearch] = useState("");
  const [fTipo, setFTipo] = useState("");


  const [fEstado, setFEstado] = useState("");
  const [fSede, setFSede] = useState("");

  // ---- Ruteo por hash: #seccion?param=valor&param2=valor ----
  useEffect(()=>{
    const aplicarHash = () => {
      const h = (window.location.hash || "").replace("#","");
      const [sec, query] = h.split("?");
      const p = new URLSearchParams(query || "");
      setTab(sec || "dashboard");
      if (sec === "activos") {
        setFTipo(p.get("tipo") || "");
        setFSede(p.get("sede") || "");
        setFEstado(p.get("estado") || "");
      }
      setSelected(null);
      setEditando(false);
    };
    aplicarHash();
    window.addEventListener("popstate", aplicarHash);
    return () => window.removeEventListener("popstate", aplicarHash);
  }, []);

  useEffect(()=>{
    let destino = tab;
    if (tab === "activos") {
      const p = new URLSearchParams();
      if (fTipo)   p.set("tipo", fTipo);
      if (fSede)   p.set("sede", fSede);
      if (fEstado) p.set("estado", fEstado);
      const q = p.toString();
      if (q) destino = tab + "?" + q;
    }
    const actual = (window.location.hash || "").replace("#","");
    if (actual === destino) return;
    if (!actual) window.history.replaceState(null, "", "#" + destino);
    else window.history.pushState(null, "", "#" + destino);
  }, [tab, fTipo, fSede, fEstado]);
  const [selected, setSelected] = useState(null);
  const [editando, setEditando] = useState(false);
  const [editAsset, setEditAsset] = useState(null);
  const [showQR, setShowQR] = useState(false);
  const [showModal, setShowModal] = useState(false);
  const [nbFiltro, setNbFiltro] = useState("total");
  const [saving, setSaving] = useState(false);
  const [newAsset, setNewAsset] = useState(emptyAsset);
  const fileRef = useRef(null);
  const spotRef = useRef(null);
  const { user, logout } = useAuth();
  const esAdmin = tienePermiso(user, "usuarios.administrar");
  const puedeEditar = tienePermiso(user, "inventario.editar");
  useEffect(()=>{ setUsuarioActual(user?.username); }, [user]);
  const [glpiMap, setGlpiMap] = useState({});
  async function cargarGlpi(){
    try {
      const res = await apiFetch(API+"/glpi/resumen", {});
      if (!res.ok) return;
      const r = await res.json();
      const m = {};
      (Array.isArray(r) ? r : []).forEach(x=>{ m[(x.serial||"").trim().toUpperCase()] = x; });
      setGlpiMap(m);
    } catch { /* GLPI no disponible: la ficha se muestra sin esos datos */ }
  }
  useEffect(()=>{ if(user) cargarGlpi(); }, [user]);
  function verFicha(a){ setSelected(a); apiFetch(API+"/assets/"+a.id+"/ficha", {}).catch(()=>{}); }
  const [showConfig, setShowConfig] = useState(false);
  const [usuarios, setUsuarios] = useState([]);
  const [nuevoUser, setNuevoUser] = useState({username:"",password:"",nombre:"",email:"",rol:"viewer"});
  const [userMsg, setUserMsg] = useState("");
  const [sidebarOpen, setSidebarOpen] = useState(false);
  const [sidebarHidden, setSidebarHidden] = useState(false);

  async function loadUsuarios() {
    try {
      const r = await apiFetch(AUTH + "/usuarios", {});
      if (r.ok) setUsuarios(await r.json());
      else if (r.status === 401) setUserMsg("Error: sesion expirada, volve a iniciar sesion."); else setUserMsg("Error al listar usuarios (" + r.status + ")");
    } catch { setUserMsg("Error de conexion al listar usuarios"); }
  }

  async function crearUsuario() {
    try {
      const r = await apiFetch(AUTH + "/usuarios", {
        method: "POST", headers: { "Content-Type": "application/json" },
        body: JSON.stringify(nuevoUser)
      });
      if (r.ok) { setUserMsg("Usuario creado!"); setNuevoUser({username:"",password:"",nombre:"",email:"",rol:"viewer"}); loadUsuarios(); }
      else { const d = await r.json(); setUserMsg("Error: " + d.detail); }
    } catch { setUserMsg("Error al crear usuario"); }
  }

  async function guardarUsuario(u, cambios) {
    try {
      const r = await apiFetch(AUTH + "/usuarios/" + encodeURIComponent(u.username), {
        method: "PUT", headers: { "Content-Type": "application/json" },
        body: JSON.stringify(cambios)
      });
      const d = await r.json().catch(()=>({}));
      if (r.ok) { setUserMsg("Usuario actualizado."); loadUsuarios(); }
      else setUserMsg("Error: " + (d.detail || r.status));
    } catch (e) { setUserMsg("Error: " + e.message); }
  }

  async function eliminarUsuario(username) {
    if (!confirm("Eliminar usuario " + username + "?")) return;
    await apiFetch(AUTH + "/usuarios/" + encodeURIComponent(username), { method: "DELETE" });
    loadUsuarios();
  }
  async function loadData() {
    setLoading(true);
    try { const a = await http.get(`${API}/assets`); setAssets(a); }
    catch(e) { console.error(e); }
    setLoading(false);
  }

  useEffect(()=>{ loadData(); },[]);

  useEffect(()=>{
    if (window.matchMedia("(prefers-reduced-motion: reduce)").matches) return;
    let queued = false, lastX = window.innerWidth/2, lastY = window.innerHeight/2;
    const onMove = (e) => {
      lastX = e.clientX; lastY = e.clientY;
      if (!queued) {
        queued = true;
        requestAnimationFrame(() => {
          if (spotRef.current) spotRef.current.style.transform = `translate3d(${lastX}px,${lastY}px,0)`;
          queued = false;
        });
      }
    };
    document.addEventListener("mousemove", onMove, { passive: true });
    return () => document.removeEventListener("mousemove", onMove);
  },[]);

  async function crearActivo() {
    if(!newAsset.marca||!newAsset.modelo||!newAsset.serial) return alert("Fabricante, modelo y serial son obligatorios.");
    setSaving(true);
    try { await http.post(`${API}/assets`,newAsset); await loadData(); setShowModal(false); setNewAsset(emptyAsset); }
    catch(e) { alert("Error: "+e.message); }
    setSaving(false);
  }

  const [consultandoGar, setConsultandoGar] = useState(false);
  async function consultarGarantia(a) {
    setConsultandoGar(true);
    try {
      const r = await http.post(API+"/assets/"+a.id+"/garantia", {});
      if (r && r.garantia) {
        alert("Garantia: " + r.garantia + " (" + r.estado + ")");
        await loadData();
        setSelected({...a, garantia: r.garantia});
      } else {
        alert(r && r.detail ? r.detail : "No se pudo obtener la garantia.");
      }
    } catch(e) { alert("Error: " + e.message); }
    setConsultandoGar(false);
  }

  async function guardarEdicion() {
    setSaving(true);
    try { await http.put(API+"/assets/"+editAsset.id,editAsset); await loadData(); setSelected(editAsset); setEditando(false); }
    catch(e) { alert("Error: "+e.message); }
    setSaving(false);
  }

  async function eliminar(id, e) {
    if(e) e.stopPropagation();
    if(!confirm("¿Eliminar este activo?")) return;
    try { await http.del(API+"/assets/"+id); await loadData(); setSelected(null); }
    catch(e) { alert("Error: "+e.message); }
  }

  async function exportarGrafico(elementId, titulo, datos) {
    try {
      const el = document.getElementById(elementId);
      if (!el) { alert("No se encontro el grafico."); return; }
      const html2canvas = (await import("html2canvas")).default;
      const canvas = await html2canvas(el, { scale: 2, backgroundColor: "#ffffff" });
      const imgBase64 = canvas.toDataURL("image/png");

      const ExcelJS = (await import("exceljs")).default; // se carga recien al exportar

      const wb = new ExcelJS.Workbook();
      const ws = wb.addWorksheet("Reporte");

      ws.mergeCells("A1:C1");
      ws.getCell("A1").value = titulo;
      ws.getCell("A1").font = { bold: true, size: 14, color: { argb: "FF0A2540" } };
      ws.getCell("A1").alignment = { vertical: "middle" };
      ws.getRow(1).height = 24;

      ws.getCell("A3").value = "Categoria";
      ws.getCell("B3").value = "Cantidad";
      ["A3","B3"].forEach(c=>{
        ws.getCell(c).font = { bold: true, color: { argb: "FFFFFFFF" } };
        ws.getCell(c).fill = { type: "pattern", pattern: "solid", fgColor: { argb: "FF0B7285" } };
      });
      let r = 4;
      datos.forEach(d=>{
        ws.getCell("A"+r).value = d.name;
        ws.getCell("B"+r).value = d.value;
        r++;
      });
      ws.getColumn("A").width = 28;
      ws.getColumn("B").width = 14;

      const imgId = wb.addImage({ base64: imgBase64, extension: "png" });
      ws.addImage(imgId, { tl: { col: 3, row: 2 }, ext: { width: canvas.width/2, height: canvas.height/2 } });

      const buf = await wb.xlsx.writeBuffer();
      const blob = new Blob([buf], { type: "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet" });
      const url = URL.createObjectURL(blob);
      const a = document.createElement("a");
      a.href = url;
      a.download = "reporte_" + titulo.toLowerCase().replace(/[^a-z0-9]+/g,"_") + ".xlsx";
      a.click();
      URL.revokeObjectURL(url);
    } catch(e) {
      alert("Error al exportar: " + e.message);
    }
  }

  function exportCSV() {
    const cols = ["nombre","tipo","marca","modelo","serial","usuario","ubicacion","estado","cpu","ram","disco","so","ip","garantia","comentarios"];
    const rows = assets.map(a=>cols.map(c=>(a[c]||"")).join(","));
    const blob = new Blob([cols.join(",")+"\n"+rows.join("\n")],{type:"text/csv"});
    const url = URL.createObjectURL(blob);
    const a = document.createElement("a"); a.href=url; a.download="inventario_llya.csv"; a.click();
    URL.revokeObjectURL(url);
  }

  async function importCSV(e) {
    const file=e.target.files[0]; if(!file) return;
    const text=await file.text();
    const cols=["nombre","tipo","marca","modelo","serial","usuario","ubicacion","estado","cpu","ram","disco","so","ip","garantia","comentarios"];
    const imported=text.trim().split("\n").slice(1).map(line=>{ const v=line.split(","); const o={}; cols.forEach((c,i)=>o[c]=(v[i]||"").trim()); return o; }).filter(a=>a.marca&&a.modelo);
    setSaving(true);
    for(const a of imported) { try { await http.post(`${API}/assets`,a); } catch { /* fila invalida: se saltea */ } }
    await loadData(); setSaving(false);
    alert(`${imported.length} activos importados.`);
    e.target.value="";
  }

  const hoy = new Date();
  const enMant = assets.filter(a=>a.estado==="Mantenimiento").length;
  const garVencen = assets.filter(a=>{
    if(!a.garantia || a.garantia==="-") return false;
    const p = String(a.garantia).split("-");
    if(p.length<3) return false;
    const f = new Date(+p[0], +p[1]-1, +p[2]);
    const d = (f - hoy)/(1000*60*60*24);
    return d >= 0 && d <= 90;
  }).length;

  const [ordAct, setOrdAct] = useState({col:null,asc:true});
  const [pagAct, setPagAct] = useState(1);
  async function exportarActivos(){
    try{
      const ExcelJS = (await import("exceljs")).default; // se carga recien al exportar
      const wb = new ExcelJS.Workbook();
      const ws = wb.addWorksheet("Activos");
      ws.columns = [{header:"Nombre",key:"nombre",width:22},{header:"Tipo",key:"tipo",width:14},{header:"Fabricante/Modelo",key:"modelo",width:30},{header:"N Serie",key:"serial",width:22},{header:"IP",key:"ip",width:16},{header:"Usuario",key:"usuario",width:22},{header:"Sede",key:"ubicacion",width:14},{header:"S.O.",key:"so",width:22},{header:"Ult Sync",key:"updated",width:18},{header:"Estado",key:"estado",width:14}];
      aplicarOrdenAct(filtrados).forEach(a=>ws.addRow({nombre:a.nombre,tipo:a.tipo,modelo:((a.marca||"")+" "+(a.modelo||"")).trim(),serial:a.serial,ip:a.ip,usuario:a.usuario,ubicacion:a.ubicacion,so:a.so,updated:a.updated,estado:a.estado}));
      ws.getRow(1).font={bold:true,color:{argb:"FFFFFFFF"}};
      ws.getRow(1).eachCell(c=>{c.fill={type:"pattern",pattern:"solid",fgColor:{argb:"FF0B7285"}};});
      const buf=await wb.xlsx.writeBuffer();
      const url=URL.createObjectURL(new Blob([buf],{type:"application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"}));
      const a=document.createElement("a"); a.href=url; a.download="activos_llya.xlsx"; a.click(); URL.revokeObjectURL(url);
    }catch(e){ alert("Error al exportar: "+e.message); }
  }
  function sortAct(col){ setOrdAct(o=>({col, asc: o.col===col ? !o.asc : true})); }
  function aplicarOrdenAct(arr){
    if(!ordAct.col) return arr;
    const get = { nombre:a=>a.nombre, tipo:a=>a.tipo, modelo:a=>(a.marca||"")+" "+(a.modelo||""), serial:a=>a.serial, ip:a=>a.ip, usuario:a=>a.usuario, ubicacion:a=>a.ubicacion, so:a=>a.so, updated:a=>a.updated, estado:a=>a.estado }[ordAct.col];
    if(!get) return arr;
    return [...arr].sort((a,b)=>{ const va=(get(a)??"").toString(), vb=(get(b)??"").toString(); const r=va.localeCompare(vb,"es",{numeric:true,sensitivity:"base"}); return ordAct.asc?r:-r; });
  }
  const filtrados = assets.filter(a=>{
    const mq=!search||[a.nombre,a.marca,a.modelo,a.serial,a.usuario,a.ubicacion].some(v=>(v||"").toLowerCase().includes(search.toLowerCase()));
    const diasSinReportar = a.updated ? Math.floor((Date.now() - new Date(a.updated).getTime())/86400000) : 9999;
    const garDias = (()=>{ if(!a.garantia||a.garantia==="-") return null; const p=String(a.garantia).split("-"); if(p.length<3) return null; return Math.floor((new Date(+p[0],+p[1]-1,+p[2]) - new Date())/86400000); })();
    const gl = glpiMap[(a.serial||"").trim().toUpperCase()];
    const mEstado = fEstado==="__sin_usuario__" ? (!a.usuario||a.usuario.trim()==="") : fEstado==="__sin_reportar__" ? (diasSinReportar > 30) : fEstado==="__gar_vencen__" ? (garDias!==null && garDias>=0 && garDias<=90) : fEstado==="__sin_edr__" ? (!!gl && gl.edr!=="Activo") : fEstado==="__sin_cifrar__" ? (!!gl && !!gl.volumenes_sin_cifrar) : fEstado==="__anydesk__" ? (!!gl && (gl.acceso_remoto||"").includes("anydesk")) : fEstado==="__bateria__" ? (!!gl && gl.bateria_salud!=null && gl.bateria_salud<70) : (!fEstado||a.estado===fEstado);
    return mq&&(!fTipo||a.tipo===fTipo)&&mEstado&&(!fSede||(a.ubicacion||"").toLowerCase()===fSede.toLowerCase());
  });

  const titles = { dashboard:"Dashboard", activos:"Activos", proyectos:"Proyectos", reportes:"Reportes", tendencias:"Tendencias", agente:"Agente", perfil:"Mi perfil" };
  const subs = { dashboard:"— Vista general", activos:"— Inventario completo", proyectos:"— Seguimiento de IT", reportes:"— Análisis", agente:"— Scripts de sincronización", perfil:"— Cuenta, permisos y seguridad" };

  if(loading) return <div className="loading-wrap"><div className="spinner"/><span className="loading-text">Cargando datos...</span></div>;

  return (
    <div className="app">
      <div id="spot" ref={spotRef}/>

      {/* MODAL CONFIGURACION */}
      {showConfig && esAdmin && (
        <div style={{position:"fixed",inset:0,background:"rgba(0,0,0,0.5)",zIndex:1000,display:"flex",alignItems:"center",justifyContent:"center"}}>
          <div style={{background:"#fff",borderRadius:12,padding:28,width:600,maxWidth:"95vw",maxHeight:"85vh",overflowY:"auto",boxShadow:"0 20px 60px rgba(0,0,0,0.3)"}}>
            <div style={{display:"flex",justifyContent:"space-between",alignItems:"center",marginBottom:20}}>
              <h2 style={{margin:0,color:"#0D2B45",fontSize:18}}>⚙️ Gestión de Usuarios</h2>
              <button onClick={()=>{setShowConfig(false);setUserMsg("");}} style={{background:"none",border:"none",fontSize:20,cursor:"pointer",color:"#666"}}>✕</button>
            </div>
            <div style={{background:"#f8fbfd",borderRadius:8,padding:16,marginBottom:20,border:"1px solid #dde3e6"}}>
              <h4 style={{margin:"0 0 12px",color:"#0D2B45",fontSize:14}}>Nuevo usuario</h4>
              <div className="form-cols" style={{display:"grid",gridTemplateColumns:"1fr 1fr",gap:10,marginBottom:10}}>
                <div><label style={{fontSize:12,fontWeight:600,display:"block",marginBottom:4,color:"#0D2B45"}}>Usuario</label><input value={nuevoUser.username} onChange={e=>setNuevoUser({...nuevoUser,username:e.target.value})} placeholder="nombre.apellido" style={{width:"100%",padding:"8px 10px",border:"1px solid #dde3e6",borderRadius:6,fontSize:13,boxSizing:"border-box",color:"#333",background:"#fff"}}/></div>
                <div><label style={{fontSize:12,fontWeight:600,display:"block",marginBottom:4,color:"#0D2B45"}}>Contraseña</label><input type="password" value={nuevoUser.password} onChange={e=>setNuevoUser({...nuevoUser,password:e.target.value})} placeholder="Mínimo 12 caracteres" style={{width:"100%",padding:"8px 10px",border:"1px solid #dde3e6",borderRadius:6,fontSize:13,boxSizing:"border-box",color:"#333",background:"#fff"}}/></div>
                <div><label style={{fontSize:12,fontWeight:600,display:"block",marginBottom:4,color:"#0D2B45"}}>Nombre completo</label><input value={nuevoUser.nombre} onChange={e=>setNuevoUser({...nuevoUser,nombre:e.target.value})} placeholder="Juan Pérez" style={{width:"100%",padding:"8px 10px",border:"1px solid #dde3e6",borderRadius:6,fontSize:13,boxSizing:"border-box",color:"#333",background:"#fff"}}/></div>
                <div><label style={{fontSize:12,fontWeight:600,display:"block",marginBottom:4,color:"#0D2B45"}}>Email</label><input value={nuevoUser.email} onChange={e=>setNuevoUser({...nuevoUser,email:e.target.value})} placeholder="nombre@llyasoc.com" style={{width:"100%",padding:"8px 10px",border:"1px solid #dde3e6",borderRadius:6,fontSize:13,boxSizing:"border-box",color:"#333",background:"#fff"}}/></div>
                <div><label style={{fontSize:12,fontWeight:600,display:"block",marginBottom:4,color:"#0D2B45"}}>Rol</label><select value={nuevoUser.rol} onChange={e=>setNuevoUser({...nuevoUser,rol:e.target.value})} style={{width:"100%",padding:"8px 10px",border:"1px solid #dde3e6",borderRadius:6,fontSize:13,boxSizing:"border-box",color:"#333",background:"#fff"}}><option value="viewer">Solo ver</option><option value="editor">Editor</option><option value="admin">Admin</option></select></div>
              </div>
              {userMsg && <div style={{fontSize:13,color:userMsg.includes("Error")?"#c0392b":"#27ae60",marginBottom:8}}>{userMsg}</div>}
              <button onClick={crearUsuario} style={{background:"linear-gradient(135deg,#00B0B9,#0B4F6C)",color:"#fff",border:"none",borderRadius:6,padding:"8px 16px",cursor:"pointer",fontWeight:700,fontSize:13}}>+ Crear usuario</button>
            </div>
            <h4 style={{margin:"0 0 10px",color:"#0D2B45",fontSize:14}}>Usuarios existentes</h4>
            <table style={{width:"100%",borderCollapse:"collapse",fontSize:13}}>
              <thead><tr style={{background:"#0D2B45",color:"#fff"}}>
                <th style={{padding:"8px 12px",textAlign:"left"}}>Usuario</th>
                <th style={{padding:"8px 12px",textAlign:"left"}}>Nombre</th>
                <th style={{padding:"8px 12px",textAlign:"left"}}>Rol</th>
                <th style={{padding:"8px 12px",textAlign:"left"}}>Acción</th>
              </tr></thead>
              <tbody>
                {usuarios.map((u,i)=>(
                  <tr key={u.username} style={{borderBottom:"1px solid #dde3e6",background:i%2===0?"#fff":"#f8fbfd"}}>
                    <td style={{padding:"8px 12px",color:"#333"}}>{u.username}</td>
                    <td style={{padding:"8px 12px",color:"#333"}}>
                      <input defaultValue={u.nombre}
                        onBlur={e=>{ if(e.target.value.trim() && e.target.value!==u.nombre) guardarUsuario(u,{nombre:e.target.value.trim()}); }}
                        onKeyDown={e=>{ if(e.key==="Enter") e.target.blur(); }}
                        onFocus={e=>{e.target.style.border="1px solid #dde3e6";e.target.style.background="#fff";}}
                        style={{border:"1px solid transparent",borderRadius:4,padding:"3px 6px",fontSize:13,background:"transparent",color:"#333",width:"92%"}}/>
                    </td>
                    <td style={{padding:"8px 12px",color:"#333"}}>
                      <select value={u.rol} onChange={e=>guardarUsuario(u,{rol:e.target.value})} disabled={u.rol==="superadmin"}
                        style={{background:u.rol==="admin"||u.rol==="superadmin"?"#0D2B45":u.rol==="editor"?"#00B0B9":"#6b8090",color:"#fff",border:"none",borderRadius:4,padding:"3px 8px",fontSize:11,fontWeight:700,minWidth:82,cursor:u.rol==="superadmin"?"default":"pointer"}}>
                        {(u.rol==="superadmin"?["superadmin"]:["admin","editor","viewer"]).map(r=><option key={r} value={r} style={{background:"#fff",color:"#333"}}>{r}</option>)}
                      </select></td>
                    <td style={{padding:"8px 12px",color:"#333"}}>
                      <button onClick={()=>{ const p=prompt("Nueva contrasena para "+u.username+" (minimo 12 caracteres, con mayusculas, minusculas, numeros o simbolos):"); if(p&&p.length>=12) guardarUsuario(u,{password:p}); else if(p) alert("Minimo 12 caracteres."); }}
                        style={{background:"#6b8090",color:"#fff",border:"none",borderRadius:4,padding:"4px 10px",cursor:"pointer",fontSize:12,marginRight:6}}>Reset pass</button>
                      {u.rol !== "superadmin" && u.username !== user?.username && (<button onClick={()=>eliminarUsuario(u.username)} style={{background:"#e74c3c",color:"#fff",border:"none",borderRadius:4,padding:"4px 10px",cursor:"pointer",fontSize:12}}>Eliminar</button>)}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </div>
      )}

      <div className={"sidebar-overlay" + (sidebarOpen?" open":"")} onClick={()=>setSidebarOpen(false)}/>
      <div className={"sidebar" + (sidebarOpen?" open":"") + (sidebarHidden?" hidden":"")}>
        <div className="sidebar-logo">
          <img src="/logo.png" alt="LL&A"/>
          <div><div className="logo-text">Inventario LLYA</div><div className="logo-sub">Activos TI</div></div>
        </div>
        <div className="sidebar-nav">
          <div className="nav-section">Principal</div>
          {[["dashboard",LayoutGrid,"Dashboard"],["activos",Laptop,"Activos"],["proyectos",FolderKanban,"Proyectos"],["reportes",BarChart3,"Reportes"],["tendencias",BarChart3,"Tendencias"],["perfil",UserCircle,"Mi perfil"]].map(([k,Icon,l])=>(
            <React.Fragment key={k}>
            <a href={"#"+k} className={`nav-item${tab===k&&!selected?" active":""}`} style={{textDecoration:"none",color:"inherit"}} onClick={(e)=>{ if(e.ctrlKey||e.metaKey||e.shiftKey||e.button===1) return; e.preventDefault(); setTab(k);setSelected(null);setEditando(false);if(k==="activos")setFTipo(""); }}>
              <Icon size={16} strokeWidth={1.75}/><span>{l}</span>
              {k==="activos"&&<span className="nav-badge">{assets.length}</span>}
            </a>
            {k==="activos"&&tab==="activos"&&!selected&&<div className="nav-subitems">
              {[["","Todos"],["Notebook","Notebooks"],["Impresora","Impresoras"]].map(([tp,lb])=>(
                <a key={lb} href={"#activos" + (tp ? "/" + encodeURIComponent(tp) : "")} className={`nav-subitem${fTipo===tp?" active":""}`}
                  style={{textDecoration:"none",color:"inherit"}} onClick={(e)=>{ if(e.ctrlKey||e.metaKey||e.shiftKey) return; e.preventDefault(); setFTipo(tp); }}>
                  {lb}
                  <span className="nav-badge">{tp===""?assets.length:assets.filter(a=>a.tipo===tp).length}</span>
                </a>
              ))}
            </div>}
          </React.Fragment>
          ))}
          <div className="nav-section">Herramientas</div>
          <div className={`nav-item${tab==="agente"&&!selected?" active":""}`} onClick={()=>{setTab("agente");setSelected(null);}}><Bot size={16} strokeWidth={1.75}/><span>Agente</span></div>
          {puedeEditar&&<div className="nav-item" onClick={()=>fileRef.current.click()}><Upload size={16} strokeWidth={1.75}/><span>Importar CSV</span></div>}
          <input ref={fileRef} type="file" accept=".csv" onChange={importCSV} style={{display:"none"}}/>
          <div className="nav-item" onClick={exportCSV}><Download size={16} strokeWidth={1.75}/><span>Exportar CSV</span></div>
        </div>
        <div className="sidebar-footer">
          {esAdmin && (
            <div className="nav-item" onClick={()=>{setShowConfig(true);loadUsuarios();}} style={{cursor:"pointer"}}>
              <Settings size={16} strokeWidth={1.75}/><span>Configuracion</span>
            </div>
          )}
          <div className="nav-item" onClick={logout} style={{cursor:"pointer",color:"var(--critical-text)",fontWeight:700}}><Power size={16} strokeWidth={1.75}/><span>Cerrar sesion</span></div>
          <div className="nav-item"><span className="sync-dot"/>v{__APP_VERSION__}</div>
        </div>
      </div>

      {/* MAIN */}
      <div className="main">
        <div className="topbar">
          <button className="btn btn-collapse" title="Ocultar/mostrar menu" onClick={()=>setSidebarHidden(s=>!s)}><Menu size={16} strokeWidth={1.75}/></button>
          <button className="hamburger" onClick={()=>setSidebarOpen(s=>!s)}><Menu size={20} strokeWidth={1.75}/></button>
          <div>
            <span className="page-title">{selected?selected.nombre||selected.modelo:titles[tab]}</span>
            <span className="page-sub">{selected?"— Ficha del activo":subs[tab]}</span>
          </div>
          <div className="topbar-right">
            {selected && <>
              {!editando&&puedeEditar&&<button className="btn btn-primary" onClick={()=>{setEditando(true);setEditAsset({...selected});}}>✏<span className="btn-label"> Editar</span></button>}
              {editando&&<button className="btn btn-primary" onClick={guardarEdicion}>💾<span className="btn-label">{saving?" Guardando...":" Guardar"}</span></button>}
              {editando&&<button className="btn" onClick={()=>setEditando(false)}>Cancelar</button>}
              {!editando&&tienePermiso(user,"activos.eliminar")&&<button className="btn btn-danger" onClick={()=>eliminar(selected.id,null)}>🗑<span className="btn-label"> Eliminar</span></button>}
              <button className="btn" onClick={()=>{setSelected(null);setEditando(false);setShowQR(false);}}>←<span className="btn-label"> Volver</span></button>
            </>}
            {!selected&&<>
              <button className="btn" title="Ambientacion" onClick={()=>setPanelTema(true)}
                style={{whiteSpace:"nowrap",padding:"6px 10px"}}>
                <span style={{display:"inline-block",width:13,height:13,borderRadius:"50%",verticalAlign:"middle",
                  background:"linear-gradient(135deg,var(--accent-2),var(--accent-hover))"}}/>
              </button>
              <button className="btn" style={{whiteSpace:"nowrap"}} onClick={loadData}><RefreshCw size={13} strokeWidth={2}/><span className="btn-label">Actualizar</span></button>
              {tab==="activos"&&puedeEditar&&<button className="btn btn-primary" style={{whiteSpace:"nowrap"}} onClick={()=>setShowModal(true)}><Plus size={13} strokeWidth={2}/><span className="btn-label">Nuevo activo</span></button>}
            </>}
          </div>
        </div>

        <div className="content">

          {/* DASHBOARD */}
          {tab==="dashboard"&&!selected&&<div>
            <div className="metrics">
              <div className="metric">
                <div className="metric-val">{assets.length}</div>
                <div className="metric-label">Total activos</div>
                <div className="metric-trend trend-up">{assets.filter(a=>a.estado==="Activo").length} activos en uso</div>
              </div>
              <div className="metric">
                <div className="metric-val">{enMant}</div>
                <div className="metric-label">En mantenimiento</div>
                <div className={`metric-trend ${enMant>0?"trend-warn":"trend-up"}`}>{enMant>0?"Requieren atención":"Sin urgencias"}</div>
              </div>
              <div className="metric metric-clickable" onClick={()=>{setTab("activos");setFEstado("__gar_vencen__");setSearch("");setFTipo("");setFSede("");setSelected(null);}}>
                <div className="metric-val">{garVencen}</div>
                <div className="metric-label">Garantias por vencer</div>
                <div className={`metric-trend ${garVencen>0?"trend-warn":"trend-up"}`}>{garVencen>0?"Proximos 90 dias":"Sin vencimientos"}</div>
              </div>

              <div className="metric">
                <div className="metric-val">{(()=>{
                  const nb=assets.filter(a=>a.tipo==="Notebook"||a.tipo==="CPU");
                  if(nbFiltro==="asignadas") return nb.filter(a=>(a.usuario||"").trim()).length;
                  if(nbFiltro==="sinasignar") return nb.filter(a=>!(a.usuario||"").trim()).length;
                  return nb.length;
                })()}</div>
                <div className="metric-label">Notebooks / CPU</div>
                <div style={{display:"flex",gap:10,marginTop:6}}>
                  {[["total","Total"],["asignadas","Asignadas"],["sinasignar","Sin asignar"]].map(([k,l])=>(
                    <span key={k} onClick={(e)=>{e.stopPropagation();setNbFiltro(k);}}
                      style={{fontSize:10.5,cursor:"pointer",fontWeight:600,
                      color:nbFiltro===k?"var(--accent-hover)":"var(--text-muted)",
                      borderBottom:nbFiltro===k?"1.5px solid var(--accent-hover)":"1.5px solid transparent"}}>{l}</span>
                  ))}
                </div>
                <div className="metric-trend trend-up" style={{cursor:"pointer",marginTop:6}} onClick={()=>{setTab("activos");setFTipo("Notebook");}}>Ver inventario -&gt;</div>
              </div>
              <div className="metric metric-clickable" onClick={()=>{setTab("activos");setFTipo("Impresora");}}>
                <div className="metric-val">{assets.filter(a=>a.tipo==="Impresora").length}</div>
                <div className="metric-label">Impresoras</div>
                <div className="metric-trend trend-up">Ver inventario -&gt;</div>
              </div>
              <div className="metric metric-clickable" onClick={()=>{setTab("activos");setFTipo("Servidor");}}>
                <div className="metric-val">{assets.filter(a=>a.tipo==="Servidor").length}</div>
                <div className="metric-label">Servidores</div>
                <div className="metric-trend trend-up">Ver inventario -&gt;</div>
              </div>
            </div>
            <div className="grid-3">
              <div className="card">
                <div className="card-head"><div className="card-title">Activos por sede</div></div>
                <div className="card-body" style={{paddingTop:8}}>
                  <G.ResponsiveContainer width="100%" height={280}>
                    <G.BarChart data={SEDES.map((s)=>{
                      const enSede=assets.filter(a=>(a.ubicacion||"").toLowerCase()===s.toLowerCase());
                      return {sede:s,
                        Notebook:enSede.filter(a=>(a.tipo||"")==="Notebook").length,
                        Impresora:enSede.filter(a=>(a.tipo||"")==="Impresora").length};
                    })} margin={{top:8,right:16,left:-8,bottom:8}} onClick={(st)=>{ if(st&&st.activeLabel){ setTab("activos"); setSelected(null); setFSede(st.activeLabel); setFTipo(""); setFEstado(""); } }}>
                      <G.CartesianGrid vertical={false} stroke="var(--border)"/>
                      <G.XAxis dataKey="sede" tick={{fontSize:11,fill:"var(--text-muted)"}} axisLine={{stroke:"var(--border)"}} tickLine={false}/>
                      <G.YAxis tick={{fontSize:11,fill:"var(--text-muted)"}} axisLine={false} tickLine={false} allowDecimals={false}/>
                      <G.Tooltip cursor={{fill:"var(--surface-2)"}} contentStyle={{borderRadius:8,border:"1px solid var(--border)",background:"var(--surface-2)",color:"var(--text)",fontSize:12}} itemStyle={{color:"var(--text)"}} labelStyle={{color:"var(--text-secondary)"}}/>
                      <G.Legend wrapperStyle={{fontSize:11,color:"var(--text-secondary)"}}/>
                      <G.Bar dataKey="Notebook" fill={COLORES[0]} radius={[3,3,0,0]} cursor="pointer"/>
                      <G.Bar dataKey="Impresora" fill={COLORES[1]} radius={[3,3,0,0]} cursor="pointer"/>
                    </G.BarChart>
                  </G.ResponsiveContainer>
                </div>
              </div>
              <div className="card">
                <div className="card-head"><div className="card-title">Distribucion por tipo</div></div>
                <div className="card-body" style={{paddingTop:8}}>
                  <G.ResponsiveContainer width="100%" height={280}>
                    <G.PieChart>
                      <G.Pie data={TIPOS.map(t=>({name:t,value:assets.filter(a=>a.tipo===t).length})).filter(d=>d.value>0)} dataKey="value" nameKey="name" cx="50%" cy="50%" innerRadius={60} outerRadius={100} paddingAngle={2} cursor="pointer" onClick={(d)=>{ if(d&&d.name){ setTab("activos"); setSelected(null); setFTipo(d.name); setFSede(""); setFEstado(""); } }}>
                        {TIPOS.map((t,i)=><G.Cell key={t} fill={COLORES[i%COLORES.length]} stroke="var(--surface)" strokeWidth={2}/>)}
                      </G.Pie>
                      <G.Tooltip contentStyle={{borderRadius:8,border:"1px solid var(--border)",background:"var(--surface-2)",color:"var(--text)",fontSize:12}} itemStyle={{color:"var(--text)"}} labelStyle={{color:"var(--text-secondary)"}}/>
                      <G.Legend wrapperStyle={{fontSize:11,color:"var(--text-secondary)"}}/>
                    </G.PieChart>
                  </G.ResponsiveContainer>
                </div>
              </div>
              <div className="card">
                <div className="card-head"><div className="card-title">Equipos sin reportar</div></div>
                <div className="card-body" style={{paddingTop:8}}>
                  <G.ResponsiveContainer width="100%" height={280}>
                    <G.BarChart data={(()=>{ const t=[{name:"16-30d",min:16,max:30},{name:"31-60d",min:31,max:60},{name:"+60d",min:61,max:99999}]; return t.map(x=>({name:x.name, equipos: assets.filter(a=>{ const d=a.updated?Math.floor((Date.now()-new Date(a.updated).getTime())/86400000):9999; return d>=x.min && d<=x.max; }).length})); })()}>
                      <G.CartesianGrid strokeDasharray="3 3" stroke="var(--border)" vertical={false}/>
                      <G.XAxis dataKey="name" tick={{fill:"var(--text-muted)",fontSize:11}} axisLine={{stroke:"var(--border)"}}/>
                      <G.YAxis tick={{fill:"var(--text-muted)",fontSize:11}} axisLine={{stroke:"var(--border)"}}/>
                      <G.Tooltip contentStyle={{borderRadius:8,border:"1px solid var(--border)",background:"var(--surface-2)",color:"var(--text)",fontSize:12}} itemStyle={{color:"var(--text)"}} labelStyle={{color:"var(--text-secondary)"}}/>
                      <G.Bar dataKey="equipos" fill="#E67E22" radius={[6,6,0,0]} cursor="pointer" onClick={()=>{setTab("activos");setFEstado("__sin_reportar__");}}/>
                    </G.BarChart>
                  </G.ResponsiveContainer>
                  <div style={{fontSize:11,color:"var(--text-muted)",textAlign:"center",marginTop:4}}>Clic en una barra para ver el listado</div>
                </div>
              </div>
            </div>
            <div className="card" style={{marginTop:14}}>
              <div className="card-head"><div className="card-title">Ultimos sincronizados</div><button className="btn" onClick={()=>{setTab("activos");setSelected(null);}}>Ver todos</button></div>
              <table><thead><tr><th>Nombre</th><th>Modelo</th><th>Usuario</th><th>Sede</th><th>S.O.</th><th>Ult. Sync</th><th>Estado</th></tr></thead>
              <tbody>
                {[...assets].sort((a,b)=>new Date(b.updated||0)-new Date(a.updated||0)).slice(0,8).map((a)=>(
                  <tr key={a.id} className="clickable" onClick={()=>verFicha(a)}>
                    <td style={{fontWeight:600,color:"var(--accent-hover)"}}>{a.nombre}</td>
                    <td>{a.modelo}</td>
                    <td>{a.usuario}</td>
                    <td>{a.ubicacion}</td>
                    <td className="td-muted">{a.so}</td>
                    <td className="td-small">{fmtDate(a.updated)}</td>
                    <td><Badge label={a.estado} map={estadoClass}/></td>
                  </tr>
                ))}
              </tbody></table>
            </div>

          </div>}

          {/* ACTIVOS */}
          {tab==="activos"&&!selected&&<div>
            <div className="search-bar">
              <div style={{position:"relative",flex:1,minWidth:180}}><input style={{width:"100%",paddingRight:30}} placeholder="Buscar nombre, modelo, serial, usuario..." value={search} onChange={e=>setSearch(e.target.value)}/>{search && <span onClick={()=>setSearch("")} title="Limpiar" style={{position:"absolute",right:10,top:"50%",transform:"translateY(-50%)",cursor:"pointer",color:"var(--text-muted)",fontSize:15,fontWeight:700,lineHeight:1}}>&times;</span>}</div>
              <select value={fTipo} onChange={e=>setFTipo(e.target.value)}>
                <option value="">Todos los tipos</option>
                {TIPOS.map(t=><option key={t}>{t}</option>)}
              </select>
              <select value={fEstado} onChange={e=>setFEstado(e.target.value)}>
                <option value="">Todos los estados</option>
                {["Activo","Mantenimiento","Libre","Stock","Robado","Dado de baja"].map(s=><option key={s}>{s}</option>)}
                {esAdmin&&<option value="__sin_usuario__">Sin usuario asignado</option>}
                <option value="__sin_reportar__">Sin reportar +30 dias</option>
                <option value="__gar_vencen__">Garantia vence en 90 dias</option>
                <option value="__sin_edr__">Sin CrowdStrike activo</option>
                <option value="__sin_cifrar__">Discos sin cifrar</option>
                <option value="__anydesk__">Con AnyDesk instalado</option>
                <option value="__bateria__">Bateria bajo 70%</option>
              </select>
              <select value={fSede} onChange={e=>setFSede(e.target.value)}>
                <option value="">Todas las sedes</option>
                {SEDES.map(s=><option key={s}>{s}</option>)}
              </select>
              <span style={{color:"var(--text-muted)",fontSize:12,alignSelf:"center"}}>{filtrados.length} activos</span><button className="btn" onClick={exportarActivos}>Exportar Excel</button>
            </div>
            <div className="table-wrap">
              <table><thead><tr>
                {[["nombre","Nombre"],["tipo","Tipo"],["modelo","Fabricante/Modelo"],["serial","N\u00b0 Serie"],["ip","IP"],["usuario","Usuario"],["ubicacion","Sede"],["so","S.O."],["updated","\u00dalt. Sync"],["estado","Estado"]].map(([k,h])=>(<th key={h} onClick={()=>sortAct(k)} style={{cursor:"pointer",userSelect:"none"}}>{h}{ordAct.col===k?(ordAct.asc?" \u2191":" \u2193"):""}</th>))}
              </tr></thead>
              <tbody>
                {filtrados.length===0&&<tr><td colSpan="9"><div className="empty">Sin activos que coincidan</div></td></tr>}
                {aplicarOrdenAct(filtrados).slice((pagAct-1)*50, pagAct*50).map((a)=>(
                  <tr key={a.id} className="clickable" onClick={()=>verFicha(a)}>
                    <td style={{fontWeight:600,color:"var(--accent-hover)"}}>{a.nombre}</td>
                    <td>{a.tipo}</td>
                    <td>{a.marca} {a.modelo}</td>
                    <td className="td-mono">{a.serial}</td>
                    <td className="td-mono">{a.ip ? <a href={"http://"+a.ip} target="_blank" rel="noopener noreferrer" onClick={e=>e.stopPropagation()} style={{color:"var(--accent-hover)"}}>{a.ip}</a> : ""}</td>
                    <td>{a.usuario}</td>
                    <td>{a.ubicacion}</td>
                    <td className="td-muted">{a.so}</td>
                    <td className="td-small">{fmtDate(a.updated)}</td>
                    <td><Badge label={a.estado} map={estadoClass}/></td>
                  </tr>
                ))}
              </tbody></table>
              {(()=>{ const tot=aplicarOrdenAct(filtrados).length, tp=Math.max(1,Math.ceil(tot/50)); if(tot<=50) return null; return (
                <div style={{display:"flex",gap:8,alignItems:"center",justifyContent:"center",padding:"12px 0"}}>
                  <button className="btn" disabled={pagAct<=1} onClick={()=>{setPagAct(p=>Math.max(1,p-1));document.querySelector(".content")?.scrollTo({top:0,behavior:"smooth"});}}>Anterior</button>
                  <span style={{fontSize:12,color:"var(--text-muted)"}}>Pagina {pagAct} de {tp} — {tot} activos</span>
                  <button className="btn" disabled={pagAct>=tp} onClick={()=>{setPagAct(p=>Math.min(tp,p+1));document.querySelector(".content")?.scrollTo({top:0,behavior:"smooth"});}}>Siguiente</button>
                </div>
              ); })()}
            </div>
          </div>}

          {/* FICHA ACTIVO */}
          {selected&&<div>
            {editando?(
              <div className="form-grid">
                {[["nombre","Nombre"],["tipo","Tipo"],["marca","Fabricante"],["modelo","Modelo"],["serial","N° Serie"],["usuario","Usuario"],["usuario_alt","Usuario alt."],["ubicacion","Sede"],["estado","Estado"],["cpu","CPU"],["ram","RAM"],["disco","Disco"],["so","S.O."],["ip","IP"],["garantia","Garantía (AAAA-MM-DD)"],["comentarios","Comentarios"]].map(([k,l])=>(
                  <div key={k} className="form-group">
                    <label className="form-label">{l}</label>
                    {k==="tipo"?<select value={editAsset[k]||""} onChange={e=>setEditAsset({...editAsset,[k]:e.target.value})}>{TIPOS.map(v=><option key={v}>{v}</option>)}</select>
                    :k==="estado"?<select value={editAsset[k]||""} onChange={e=>setEditAsset({...editAsset,[k]:e.target.value})}>{["Activo","Mantenimiento","Libre","Stock","Robado","Dado de baja"].map(v=><option key={v}>{v}</option>)}</select>
                    :k==="ubicacion"?<select value={editAsset[k]||""} onChange={e=>setEditAsset({...editAsset,[k]:e.target.value})}><option value="">--</option>{SEDES.map(v=><option key={v}>{v}</option>)}</select>
                    :<input value={editAsset[k]||""} onChange={e=>setEditAsset({...editAsset,[k]:e.target.value})}/>}
                  </div>
                ))}
              </div>
            ):(
              <div className="grid-2">
                <div className="card">
                  <div className="card-head"><div className="card-title">💻 Identificación</div><button className="btn" onClick={()=>setShowQR(!showQR)}>{showQR?"Ocultar QR":"Ver QR"}</button></div>
                  <div className="card-body">
                    {showQR&&<div style={{display:"flex",justifyContent:"center",padding:"8px 0 16px"}}><QR value={selected.serial||selected.id} size={120}/></div>}
                    <Field label="Nombre" value={selected.nombre}/>
                    <Field label="Tipo" value={selected.tipo}/>
                    <Field label="Fabricante" value={selected.marca}/>
                    <Field label="Modelo" value={selected.modelo}/>
                    <Field label="N° Serie" value={selected.serial} mono/>
                    <Field label="Estado" value={selected.estado}/>
                    <Field label="Garantía" value={selected.garantia}/>
                    {(selected.marca||"").toUpperCase().includes("LENOVO") && (
                      <div className="field">
                        <span className="field-label">&nbsp;</span>
                        <span className="field-value">
                          <button className="btn" disabled={consultandoGar}
                            style={{padding:"4px 10px",fontSize:12}}
                            onClick={()=>consultarGarantia(selected)}>
                            {consultandoGar ? "Consultando..." : "Consultar a Lenovo"}
                          </button>
                        </span>
                      </div>
                    )}
                    {(()=>{ const gl = glpiMap[(selected.serial||"").trim().toUpperCase()]; if(!gl) return null;
                      const alerta = (cond, txt) => cond ? "⚠ " + txt : txt;
                      return (<>
                        <Field label="CrowdStrike" value={alerta(gl.edr!=="Activo", gl.edr)}/>
                        <Field label="Antivirus" value={gl.antivirus||"—"}/>
                        <Field label="Volumenes sin cifrar" value={alerta(!!gl.volumenes_sin_cifrar, gl.volumenes_sin_cifrar||"Ninguno")}/>
                        <Field label="Acceso remoto" value={alerta((gl.acceso_remoto||"").includes("anydesk"), gl.acceso_remoto||"Ninguno")}/>
                        <Field label="Bateria" value={gl.bateria_salud!=null ? alerta(gl.bateria_salud<70, gl.bateria_salud+"%") : "—"}/>
                        <Field label="Discos" value={gl.discos||"—"}/>
                        <Field label="Office" value={alerta((gl.office||"").includes("Grace"), gl.office||"—")}/>
                        <Field label="Windows" value={gl.os_build||"—"}/>
                        <Field label="BIOS" value={gl.bios||"—"}/>
                        <Field label="Ultimo arranque" value={gl.ultimo_arranque||"—"}/>
                        <Field label="Relevado por GLPI" value={(gl.fecha||"").replace("T"," ")}/>
                      </>);
                    })()}
                  </div>
                </div>
                <div className="card">
                  <div className="card-head"><div className="card-title">⚙️ Hardware</div></div>
                  <div className="card-body">
                    <Field label="CPU" value={selected.cpu}/>
                    <Field label="RAM" value={selected.ram}/>
                    <Field label="Disco" value={selected.disco}/>
                    <Field label="S.O." value={selected.so}/>
                    <Field label="Versión SO" value={selected.so_version}/>
                    <Field label="Arquitectura" value={selected.so_arquitectura}/>
                    <Field label="IP" value={selected.ip} mono/>
                    <Field label="Dominio" value={selected.red}/>
                  </div>
                </div>
                <div className="card">
                  <div className="card-head"><div className="card-title">🔒 Seguridad</div></div>
                  <div className="card-body">
                    <div className="field">
                      <span className="field-label">Cifrado de disco</span>
                      <span className="field-value" style={{fontWeight:700, color:
                        selected.cifrado==="Cifrado" ? "#0ca30c"
                        : (selected.cifrado||"").startsWith("Cifrado (") ? "#E67E22"
                        : selected.cifrado==="Sin cifrar" ? "#d03b3b"
                        : selected.cifrado==="Cifrando" ? "#3987e5"
                        : "var(--text-muted)"}}>
                        {selected.cifrado || "—"}
                      </span>
                    </div>
                    <Field label="TPM" value={selected.tpm}/>
                    {(selected.cifrado||"").startsWith("Cifrado (") && (
                      <div style={{fontSize:11.5,color:"#E67E22",marginTop:8,lineHeight:1.5}}>
                        El disco está cifrado pero la protección está suspendida: la clave queda disponible sin autenticación.
                      </div>
                    )}
                    {selected.cifrado==="Sin acceso" && (
                      <div style={{fontSize:11.5,color:"var(--text-muted)",marginTop:8,lineHeight:1.5}}>
                        No se pudo leer el estado (requiere privilegios elevados o BitLocker no está instalado).
                      </div>
                    )}
                  </div>
                </div>
                <div className="card">
                  <div className="card-head"><div className="card-title">👤 Asignación</div></div>
                  <div className="card-body">
                    <Field label="Usuario" value={selected.usuario}/>
                    <Field label="Usuario alt." value={selected.usuario_alt}/>
                    <Field label="Sede" value={selected.ubicacion}/>
                    <Field label="Grupo" value={selected.grupo}/>
                    <Field label="Comentarios" value={selected.comentarios}/>
                    <Field label="Últ. sync" value={fmtDate(selected.updated)}/>
                  </div>
                </div>
                {selected.impresoras&&selected.impresoras!==""&&<div className="card">
                  <div className="card-head"><div className="card-title">🖨️ Impresoras ({selected.impresoras.split("|").filter(s=>s.trim()).length})</div></div>
                  <div className="card-body">
                    {selected.impresoras.split("|").filter(s=>s.trim()).map((p,i)=><div key={i} className="field"><span className="field-value">{p}</span></div>)}
                  </div>
                </div>}
                {selected.software&&selected.software!==""&&<div className="card">
                  <div className="card-head"><div className="card-title">📦 Software instalado ({selected.software.split("~~~").filter(s=>s.trim()).length} programas)</div></div>
                  <div style={{maxHeight:280,overflowY:"auto"}}>
                    <table><thead><tr><th>Nombre</th><th>Versión</th><th>Instalado</th></tr></thead>
                    <tbody>{selected.software.split("~~~").filter(s=>s.trim()).map((s,i)=>{
                      const[nombre,version,fecha]=s.split("|||");
                      return <tr key={i}>
                        <td>{nombre}</td><td className="td-muted">{version}</td><td className="td-small">{fecha}</td>
                      </tr>;
                    })}</tbody></table>
                  </div>
                </div>}
                <AdjuntosActivo assetId={selected?.id} usuario={user?.username}/>
                <HistorialActivo assetId={selected?.id}/>
              </div>
            )}
          </div>}

          {/* PROYECTOS */}
          {tab==="proyectos"&&!selected&&<SeccionProyectos assets={assets} user={user}/>}

          {/* MI PERFIL */}
          {tab==="perfil"&&!selected&&<SeccionPerfil user={user}/>}

          {/* REPORTES */}
          {tab==="reportes"&&!selected&&(()=>{
            const dSede=SEDES.map(s=>({name:s,value:assets.filter(a=>(a.ubicacion||"").toLowerCase()===s.toLowerCase()).length}));
            const dEstado=["Activo","Mantenimiento","Libre","Stock","Robado","Dado de baja"].map(s=>({name:s,value:assets.filter(a=>a.estado===s).length})).filter(d=>d.value>0);
            const dTipo=TIPOS.map(t=>({name:t,value:assets.filter(a=>a.tipo===t).length})).filter(d=>d.value>0);
            const ESTADO_COL={"Activo":"#0ca30c","Mantenimiento":"#fab219","Libre":"#00B0B9","Stock":"#3987e5","Robado":"#c0392b","Dado de baja":"#6E7A90"};
            return (
              <>
              <div className="grid-2">
                <div className="card">
                  <div className="card-head"><div className="card-title">Activos por sede</div><button className="btn" onClick={()=>exportarGrafico("rep-sede","Activos por sede",dSede)}>Excel</button></div>
                  <div className="card-body" style={{paddingTop:8}} id="rep-sede">
                    <G.ResponsiveContainer width="100%" height={260}>
                      <G.BarChart data={dSede} margin={{top:8,right:16,left:-8,bottom:8}} onClick={(st)=>{ if(st&&st.activeLabel){ setTab("activos"); setSelected(null); setFSede(st.activeLabel); setFTipo(""); setFEstado(""); } }}>
                        <G.XAxis dataKey="name" tick={{fontSize:11,fill:"var(--text-muted)"}} axisLine={{stroke:"var(--border)"}} tickLine={false}/>
                        <G.YAxis tick={{fontSize:11,fill:"var(--text-muted)"}} axisLine={false} tickLine={false} allowDecimals={false}/>
                        <G.Tooltip cursor={{fill:"rgba(11,114,133,0.06)"}} contentStyle={{borderRadius:8,border:"1px solid var(--border)",background:"var(--surface-2)",color:"var(--text)",fontSize:12}} itemStyle={{color:"var(--text)"}} labelStyle={{color:"var(--text-secondary)"}}/>
                        <G.Bar dataKey="value" radius={[3,3,0,0]}>{dSede.map((d,i)=><G.Cell key={i} fill={COLORES[i%COLORES.length]}/>)}</G.Bar>
                      </G.BarChart>
                    </G.ResponsiveContainer>
                  </div>
                </div>
                <div className="card">
                  <div className="card-head"><div className="card-title">Distribucion por tipo</div><button className="btn" onClick={()=>exportarGrafico("rep-tipo","Distribucion por tipo",dTipo)}>Excel</button></div>
                  <div className="card-body" style={{paddingTop:8}} id="rep-tipo">
                    <G.ResponsiveContainer width="100%" height={260}>
                      <G.PieChart>
                        <G.Pie data={dTipo} dataKey="value" nameKey="name" cx="50%" cy="50%" innerRadius={55} outerRadius={95} paddingAngle={2} cursor="pointer" onClick={(d)=>{ if(d&&d.name){ setTab("activos"); setSelected(null); setFTipo(d.name); setFSede(""); setFEstado(""); } }}>{dTipo.map((d,i)=><G.Cell key={i} fill={COLORES[i%COLORES.length]} stroke="var(--surface)" strokeWidth={2}/>)}</G.Pie>
                        <G.Tooltip contentStyle={{borderRadius:8,border:"1px solid var(--border)",background:"var(--surface-2)",color:"var(--text)",fontSize:12}} itemStyle={{color:"var(--text)"}} labelStyle={{color:"var(--text-secondary)"}}/>
                        <G.Legend wrapperStyle={{fontSize:11,color:"var(--text-secondary)"}}/>
                      </G.PieChart>
                    </G.ResponsiveContainer>
                  </div>
                </div>
                <div className="card">
                  <div className="card-head"><div className="card-title">Activos por estado</div><button className="btn" onClick={()=>exportarGrafico("rep-estado","Activos por estado",dEstado)}>Excel</button></div>
                  <div className="card-body" style={{paddingTop:8}} id="rep-estado">
                    <G.ResponsiveContainer width="100%" height={260}>
                      <G.PieChart>
                        <G.Pie data={dEstado} dataKey="value" nameKey="name" cx="50%" cy="50%" outerRadius={95} paddingAngle={2} cursor="pointer" onClick={(d)=>{ if(d&&d.name){ setTab("activos"); setSelected(null); setFEstado(d.name); setFSede(""); setFTipo(""); } }}>{dEstado.map((d,i)=><G.Cell key={i} fill={ESTADO_COL[d.name]||COLORES[i%COLORES.length]} stroke="var(--surface)" strokeWidth={2}/>)}</G.Pie>
                        <G.Tooltip contentStyle={{borderRadius:8,border:"1px solid var(--border)",background:"var(--surface-2)",color:"var(--text)",fontSize:12}} itemStyle={{color:"var(--text)"}} labelStyle={{color:"var(--text-secondary)"}}/>
                        <G.Legend wrapperStyle={{fontSize:11,color:"var(--text-secondary)"}}/>
                      </G.PieChart>
                    </G.ResponsiveContainer>
                  </div>
                </div>
              </div>
              </>
            );
          })()}

          {/* AGENTE */}
          {tab==="agente"&&!selected&&<div>
            <div className="grid-2">
              {[
                ["🪟 Agente Windows v4.3","powershell -ExecutionPolicy Bypass -File agent.ps1 -Server <url> -SyncKey <clave>",`# Servidor de este ambiente\n-Server "${window.location.origin}"\n# La clave (SYNC_API_KEY) la entrega el administrador;\n# no se escribe dentro del script.`],
                ["🐧 Agente Linux",`curl -s ${window.location.origin}/agent_linux.sh -o agent.sh`,`INVENTARIO_URL="${window.location.origin}" \\\nINVENTARIO_SYNC_KEY="<clave>" bash agent.sh`],
              ].map(([title,cmd,code])=>(
                <div key={title} className="card">
                  <div className="card-head"><div className="card-title">{title}</div></div>
                  <div className="card-body">
                    <code style={{fontSize:11,display:"block",marginBottom:8,color:"#aef"}}>{cmd}</code>
                    <pre style={{background:"#0D2B45",color:"#e0f0ff",padding:12,borderRadius:6,fontSize:11,overflow:"auto"}}>{code}</pre>
                  </div>
                </div>
              ))}
            </div>
            <div className="card" style={{marginTop:14}}>
              <div className="card-head"><div className="card-title">📁 Distribución</div></div>
              <div className="card-body">
                {[["Distribuci\u00f3n","GPO: script de arranque (SYSVOL), con -Server y -SyncKey"],["Endpoint","POST "+window.location.origin+"/api/sync (header X-Sync-Key)"],["Frecuencia","Cada 2 horas (8 a 22) y al iniciar sesi\u00f3n, de fondo"],["Identificador","Serial del equipo (sin serial: comparten registro)"]].map(([k,v])=>(
                  <div key={k} className="field"><span className="field-label">{k}</span><code>{v}</code></div>
                ))}
              </div>
            </div>
          </div>}

          {tab==="tendencias"&&!selected&&<SeccionTendencias/>}

        </div>
      </div>

      {panelTema && (<>
        <div onClick={()=>setPanelTema(false)} style={{position:"fixed",inset:0,zIndex:60,background:"rgba(3,5,10,0.5)",backdropFilter:"blur(3px)"}}/>
        <div style={{position:"fixed",top:0,right:0,zIndex:61,width:330,maxWidth:"90vw",height:"100%",background:"var(--bg)",borderLeft:"1px solid var(--border)",boxShadow:"-30px 0 90px -30px #000",display:"flex",flexDirection:"column",padding:26,gap:24,overflowY:"auto"}}>
          <div style={{display:"flex",alignItems:"flex-start"}}>
            <div>
              <div style={{fontSize:18,fontWeight:600,color:"var(--text)"}}>Ambientacion</div>
              <div style={{fontSize:12,color:"var(--text-muted)",marginTop:3}}>Personaliza la interfaz</div>
            </div>
            <button onClick={()=>setPanelTema(false)} style={{marginLeft:"auto",width:30,height:30,border:"none",background:"var(--surface-2)",color:"var(--text-muted)",fontSize:15,cursor:"pointer",borderRadius:8}}>x</button>
          </div>
          <div>
            <div style={{fontSize:11,letterSpacing:1.4,color:"var(--text-muted)",fontWeight:600,marginBottom:11}}>MODO</div>
            <div style={{display:"grid",gridTemplateColumns:"1fr 1fr",gap:8}}>
              {MODOS.map(([v2,l])=>(
                <div key={l} onClick={()=>setModo(v2)} style={{border:"1px solid "+(modo===v2?"var(--accent-hover)":"var(--border)"),background:modo===v2?"var(--accent-soft)":"transparent",borderRadius:8,padding:"9px 11px",fontSize:12.5,cursor:"pointer",color:modo===v2?"var(--accent-hover)":"var(--text-secondary)",textAlign:"center",userSelect:"none"}}>{l}</div>
              ))}
            </div>
          </div>
          <div>
            <div style={{fontSize:11,letterSpacing:1.4,color:"var(--text-muted)",fontWeight:600,marginBottom:11}}>COLOR DE ACENTO</div>
            <div style={{display:"flex",gap:9,flexWrap:"wrap"}}>
              {SWATCHES.map(([v2,l,c1,c2])=>(
                <div key={l} onClick={()=>setColorTema(v2)} title={l} style={{width:48,height:44,borderRadius:9,cursor:"pointer",background:"linear-gradient(135deg,"+c1+","+c2+")",border:"2px solid "+(colorTema===v2?"var(--text)":"transparent"),boxShadow:colorTema===v2?("0 0 14px -2px "+c1):"none",display:"flex",alignItems:"center",justifyContent:"center",color:"#fff",fontSize:15,fontWeight:700}}>{colorTema===v2?"\u2713":""}</div>
              ))}
            </div>
            <div style={{fontSize:12.5,color:"var(--text-muted)",marginTop:11}}>Seleccionado: <span style={{color:"var(--accent-hover)",fontWeight:600}}>{(SWATCHES.find(s=>s[0]===colorTema)||SWATCHES[0])[1]}</span></div>
          </div>
          <div style={{borderTop:"1px solid var(--border)",paddingTop:16}}>
            <div style={{fontSize:11,letterSpacing:1.4,color:"var(--text-muted)",fontWeight:600,marginBottom:11}}>VISTA PREVIA</div>
            <div style={{background:"var(--surface-2)",border:"1px solid var(--border)",borderRadius:8,padding:"11px 13px"}}>
              <div style={{fontSize:10,color:"var(--text-muted)"}}>PRY-2026-001</div>
              <div style={{fontSize:13,color:"var(--text)",margin:"3px 0 8px"}}>Proyecto de ejemplo</div>
              <div style={{background:"var(--border)",borderRadius:10,height:5,overflow:"hidden"}}>
                <div style={{width:"60%",height:"100%",background:"var(--accent-2)"}}/>
              </div>
              <div style={{display:"flex",alignItems:"center",marginTop:8}}>
                <span style={{fontSize:10.5,color:"var(--text-muted)"}}>60% · 3/5 tareas</span>
                <span style={{marginLeft:"auto",width:22,height:22,borderRadius:"50%",background:"var(--accent-2)",color:"#fff",fontSize:9.5,fontWeight:700,display:"flex",alignItems:"center",justifyContent:"center"}}>JI</span>
              </div>
            </div>
          </div>
          <div style={{marginTop:"auto",fontSize:11,color:"var(--text-muted)"}}>Los cambios se aplican al instante.</div>
        </div>
      </>)}

      {/* MODAL NUEVO ACTIVO */}
      {showModal&&<div className="modal-overlay" onClick={()=>setShowModal(false)}>
        <div className="modal" onClick={e=>e.stopPropagation()}>
          <div className="modal-head">
            <div className="modal-icon">💻</div>
            <div className="modal-title">Nuevo activo</div>
            <button className="btn" style={{marginLeft:"auto"}} onClick={()=>setShowModal(false)}>✕</button>
          </div>
          <div className="form-grid">
            {[["nombre","Nombre del equipo","text"],["tipo","Tipo","select-tipo"],["marca","Fabricante *","text"],["modelo","Modelo *","text"],["serial","N° Serie *","text"],["estado","Estado","select-estado"],["usuario","Usuario","text"],["ubicacion","Sede","select-sede"],["garantia","Garantía (AAAA-MM-DD)","text"],["ip","IP","text"],["cpu","CPU","text"],["ram","RAM","text"],["disco","Disco","text"],["so","Sistema operativo","text"]].map(([k,l,t])=>(
              <div key={k} className="form-group">
                <label className="form-label">{l}</label>
                {t==="select-tipo"?<select value={newAsset[k]} onChange={e=>setNewAsset({...newAsset,[k]:e.target.value})}>{TIPOS.map(v=><option key={v}>{v}</option>)}</select>
                :t==="select-estado"?<select value={newAsset[k]} onChange={e=>setNewAsset({...newAsset,[k]:e.target.value})}>{["Activo","Mantenimiento","Libre","Stock","Robado","Dado de baja"].map(v=><option key={v}>{v}</option>)}</select>
                :t==="select-sede"?<select value={newAsset[k]} onChange={e=>setNewAsset({...newAsset,[k]:e.target.value})}><option value="">-- Seleccionar --</option>{SEDES.map(v=><option key={v}>{v}</option>)}</select>
                :<input value={newAsset[k]} onChange={e=>setNewAsset({...newAsset,[k]:e.target.value})}/>}
              </div>
            ))}
          </div>
          <div className="form-group" style={{marginTop:10}}>
            <label className="form-label">Comentarios</label>
            <textarea style={{height:60}} value={newAsset.comentarios} onChange={e=>setNewAsset({...newAsset,comentarios:e.target.value})}/>
          </div>
          <div className="modal-actions">
            <button className="btn" onClick={()=>setShowModal(false)}>Cancelar</button>
            <button className="btn btn-primary" onClick={crearActivo}>{saving?"Guardando...":"Guardar activo"}</button>
          </div>
        </div>
      </div>}


    </div>
  );
}

