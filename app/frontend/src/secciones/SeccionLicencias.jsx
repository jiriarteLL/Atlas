// SeccionLicencias.jsx — Pestaña Licencias: Claude, Adobe y otras.
import { useState, useEffect } from "react";
import { API_UM, umFetch, http } from "../api";
import { Tag } from "../ui";

export function SeccionLicencias({ empleados }) {
  const [sub, setSub] = useState("claude");
  const [subClaude, setSubClaude] = useState("personal");
  const [asignacionesClaude, setAsignacionesClaude] = useState([]);
  const [loadingClaude, setLoadingClaude] = useState(true);
  const [equiposLicencias, setEquiposLicencias] = useState([]);
  const [loadingEquipos, setLoadingEquipos] = useState(true);
  const [paresAdobe, setParesAdobe] = useState([]);
  const [otrasLic, setOtrasLic] = useState([]);
  const emptyOtra = {empleado_id:"", licencia_id:"", cuenta:"", imputacion:""};
  const [formOtra, setFormOtra] = useState(emptyOtra);
  const [editandoOtra, setEditandoOtra] = useState(null);
  const [buscarEmpOtra, setBuscarEmpOtra] = useState("");
  const [loadingOtras, setLoadingOtras] = useState(true);
  const [loadingAdobe, setLoadingAdobe] = useState(true);
  const [licenciasCatalogo, setLicenciasCatalogo] = useState([]);
  const [buscar, setBuscar] = useState("");
  const [ordLic, setOrdLic] = useState({col:null,asc:true});
  function sortLic(col){ setOrdLic(o=>({col, asc: o.col===col ? !o.asc : true})); }
  function ordenar(arr){
    if(!ordLic.col) return arr;
    return [...arr].sort((a,b)=>{
      const va=(a[ordLic.col]??"").toString(), vb=(b[ordLic.col]??"").toString();
      const r=va.localeCompare(vb,"es",{numeric:true,sensitivity:"base"});
      return ordLic.asc?r:-r;
    });
  }
  const thOrd = (cols) => cols.map(([k,h])=>(
    <th key={h||k} onClick={()=>k&&sortLic(k)} style={{cursor:k?"pointer":"default",userSelect:"none"}}>
      {h}{(k&&ordLic.col===k)?(ordLic.asc?" \u2191":" \u2193"):""}
    </th>
  ));
  const [fTipoLic, setFTipoLic] = useState("");
  const [fEstadoLic, setFEstadoLic] = useState("");

  const emptyPar = { sector:"", usuario_principal:"", email_principal:"", usuario_secundario:"", email_secundario:"", imputacion:"" };
  const [editandoPar, setEditandoPar] = useState(null);
  const [formPar, setFormPar] = useState(emptyPar);

  const emptyClaude = { empleado_id:"", licencia_id:"", unidad:"" };
  const [editandoClaude, setEditandoClaude] = useState(null);
  const [formClaude, setFormClaude] = useState(emptyClaude);
  const [buscarEmp, setBuscarEmp] = useState("");

  const emptyEquipo = { numero:"", unidad:"", lider:"", responsable:"", email:"", tipo:"", estado:"Activo" };
  const [editandoEquipo, setEditandoEquipo] = useState(null);
  const [formEquipo, setFormEquipo] = useState(emptyEquipo);

  function cargarOtras(){
    umFetch(API_UM + "/asignaciones/otras").then(r=>r.json()).then(setOtrasLic).catch(()=>{}).finally(()=>setLoadingOtras(false));
  }
  function cargarAdobe(){
    umFetch(API_UM + "/adobe/pares").then(r=>r.json()).then(setParesAdobe).catch(()=>{}).finally(()=>setLoadingAdobe(false));
  }
  function cargarClaude(){
    umFetch(API_UM + "/asignaciones/claude").then(r=>r.json()).then(setAsignacionesClaude).catch(()=>{}).finally(()=>setLoadingClaude(false));
  }
  function cargarEquipos(){
    umFetch(API_UM + "/equipos/licencias").then(r=>r.json()).then(setEquiposLicencias).catch(()=>{}).finally(()=>setLoadingEquipos(false));
  }

  useEffect(()=>{
    cargarClaude();
    cargarEquipos();
    cargarAdobe();
    cargarOtras();
    umFetch(API_UM + "/licencias").then(r=>r.json()).then(setLicenciasCatalogo).catch(()=>{});
  }, []);

  async function exportarLicencias(){
    try{
      const ExcelJS = (await import("exceljs")).default; // se carga recien al exportar
      const wb = new ExcelJS.Workbook();
      if(sub==="claude"){
        const wsP = wb.addWorksheet("Personal");
        wsP.columns = [
          {header:"#",key:"numero",width:8},
          {header:"Unidad de Negocio",key:"unidad",width:32},
          {header:"Lider",key:"lider",width:20},
          {header:"Responsable",key:"responsable",width:28},
          {header:"Email",key:"email",width:32},
          {header:"Tipo",key:"tipo",width:14},
          {header:"Estado",key:"estado",width:16}
        ];
        asignacionesClaude.forEach(a=>wsP.addRow(a));
        const wsE = wb.addWorksheet("Equipos");
        wsE.columns = wsP.columns;
        equiposLicencias.forEach(e=>wsE.addRow(e));
        [wsP,wsE].forEach(ws=>{ ws.getRow(1).font={bold:true,color:{argb:"FFFFFFFF"}}; ws.getRow(1).eachCell(c=>{c.fill={type:"pattern",pattern:"solid",fgColor:{argb:"FF0B7285"}};}); });
      } else if(licsOtras.includes(sub)){
        const ws = wb.addWorksheet(sub.substring(0,30));
        ws.columns = [
          {header:"Licencia",key:"licencia",width:20},
          {header:"Plan",key:"plan",width:14},
          {header:"Empleado",key:"empleado",width:32},
          {header:"Legajo",key:"legajo",width:10},
          {header:"Email",key:"email",width:32},
          {header:"Sede",key:"sede",width:14},
          {header:"Centro de costo",key:"centro_costo",width:28},
          {header:"Detalle",key:"detalle",width:40},
          {header:"Desde",key:"fecha_desde",width:14}
        ];
        otrasLic.filter(o=>o.licencia===sub).forEach(o=>ws.addRow(o));
        ws.getRow(1).font={bold:true,color:{argb:"FFFFFFFF"}};
        ws.getRow(1).eachCell(c=>{c.fill={type:"pattern",pattern:"solid",fgColor:{argb:"FF0B7285"}};});
      } else {
        const ws = wb.addWorksheet("Adobe");
        ws.columns = [
          {header:"Sector",key:"sector",width:24},
          {header:"Usuario Principal",key:"usuario_principal",width:28},
          {header:"Email Principal",key:"email_principal",width:32},
          {header:"Usuario Secundario",key:"usuario_secundario",width:28},
          {header:"Email Secundario",key:"email_secundario",width:32},
          {header:"Imputacion",key:"imputacion",width:24}
        ];
        paresAdobe.forEach(p=>ws.addRow(p));
        ws.getRow(1).font={bold:true,color:{argb:"FFFFFFFF"}};
        ws.getRow(1).eachCell(c=>{c.fill={type:"pattern",pattern:"solid",fgColor:{argb:"FFD03B3B"}};});
      }
      const buf = await wb.xlsx.writeBuffer();
      const blob = new Blob([buf], { type: "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet" });
      const url = URL.createObjectURL(blob);
      const a = document.createElement("a");
      a.href = url;
      a.download = "licencias_" + sub.toLowerCase().replace(/[^a-z0-9]+/g,"_") + ".xlsx";
      a.click();
      URL.revokeObjectURL(url);
    } catch(e){ alert("Error al exportar: "+e.message); }
  }

  const licenciasClaude = licenciasCatalogo.filter(l=>l.tipo==="IA");
  const q = buscar.trim().toLowerCase();
  const coincide = (...campos) => !q || campos.some(x=>(x||"").toLowerCase().includes(q));
  const claudeFiltrado = asignacionesClaude.filter(a=>coincide(a.unidad,a.responsable,a.email,a.lider) && (!fTipoLic || (a.tipo||"").includes(fTipoLic)) && (!fEstadoLic || (a.estado||"").includes(fEstadoLic)));
  const equiposFiltrado = equiposLicencias.filter(e=>coincide(e.unidad,e.responsable,e.email,e.lider) && (!fTipoLic || (e.tipo||"").includes(fTipoLic)) && (!fEstadoLic || (e.estado||"").includes(fEstadoLic)));
  const licsOtras = Array.from(new Set(otrasLic.map(o=>o.licencia))).sort();
  const otrasFiltrado = otrasLic.filter(o=>o.licencia===sub && coincide(o.licencia,o.plan,o.empleado,o.email,o.sede,o.centro_costo,o.detalle));
  const adobeFiltrado = paresAdobe.filter(p=>coincide(p.sector,p.usuario_principal,p.email_principal,p.usuario_secundario,p.email_secundario,p.imputacion));
  const empleadosMap = {};
  empleados.forEach(e=>{ empleadosMap[e.nombre+" (Legajo "+e.legajo+")"] = e; });

  const licenciasOtras = licenciasCatalogo.filter(l=>l.tipo!=="IA" && l.nombre!=="Adobe Acrobat");
  function abrirNuevaOtra(){
    const lic = licenciasCatalogo.find(l=>l.nombre===sub);
    setFormOtra({...emptyOtra, licencia_id: lic?lic.id:""});
    setBuscarEmpOtra(""); setEditandoOtra({});
  }
  function abrirEditarOtra(o){
    const p = (o.detalle||"").split("|");
    setFormOtra({empleado_id:o.empleado_id, licencia_id:o.licencia_id,
                 cuenta:(p[0]||"").trim(), imputacion:(p[1]||"").trim()});
    setBuscarEmpOtra(o.empleado); setEditandoOtra(o);
  }
  function cerrarFormOtra(){ setEditandoOtra(null); setFormOtra(emptyOtra); setBuscarEmpOtra(""); }
  async function guardarOtra(){
    if(!formOtra.licencia_id){ alert("Elegi una licencia."); return; }
    const det = [formOtra.cuenta, formOtra.imputacion].filter(x=>x&&x.trim()).join(" | ");
    try{
      if(editandoOtra && editandoOtra.id){
        await http.put(API_UM+"/asignaciones/licencias/"+editandoOtra.id+"?licencia_id="+formOtra.licencia_id+"&detalle="+encodeURIComponent(det), {});
      } else {
        if(!formOtra.empleado_id){ alert("Elegi un empleado de la lista."); return; }
        await http.post(API_UM+"/asignaciones/licencias", {empleado_id:formOtra.empleado_id, licencia_id:formOtra.licencia_id, detalle:det, activo:"1"});
      }
      cerrarFormOtra(); cargarOtras();
    } catch(e){ alert("Error al guardar: "+e.message); }
  }
  async function quitarOtra(o){
    if(!confirm("Quitar la licencia "+o.licencia+" de "+o.empleado+"?")) return;
    try{ await http.del(API_UM+"/asignaciones/licencias/"+o.id); cargarOtras(); }
    catch(e){ alert("Error al quitar: "+e.message); }
  }
  function abrirNuevoPar(){ setFormPar(emptyPar); setEditandoPar({}); }
  function abrirEditarPar(p){ setFormPar({sector:p.sector,usuario_principal:p.usuario_principal,email_principal:p.email_principal,usuario_secundario:p.usuario_secundario,email_secundario:p.email_secundario,imputacion:p.imputacion}); setEditandoPar(p); }
  function cerrarFormPar(){ setEditandoPar(null); }

  async function guardarPar(){
    if(!formPar.usuario_principal || !formPar.email_principal){ alert("Usuario principal y su email son obligatorios."); return; }
    try{
      if(editandoPar && editandoPar.id){
        await http.put(API_UM+"/adobe/pares/"+editandoPar.id, formPar);
      } else {
        await http.post(API_UM+"/adobe/pares", formPar);
      }
      cerrarFormPar();
      cargarAdobe();
    } catch(e){ alert("Error al guardar: "+e.message); }
  }

  async function quitarPar(p){
    if(!confirm(`Quitar el par de "${p.usuario_principal}"? Esto tambien cierra su licencia Adobe asignada.`)) return;
    try{
      await http.del(API_UM+"/adobe/pares/"+p.id);
      cargarAdobe();
    } catch(e){ alert("Error al quitar: "+e.message); }
  }

  function abrirNuevoClaude(){ setFormClaude(emptyClaude); setBuscarEmp(""); setEditandoClaude({}); }
  function abrirEditarClaude(a){ setFormClaude({empleado_id:a.empleado_id, licencia_id:a.licencia_id, unidad:a.unidad}); setBuscarEmp(a.responsable); setEditandoClaude(a); }
  function cerrarFormClaude(){ setEditandoClaude(null); }

  function elegirEmpleado(nombreConLegajo){
    setBuscarEmp(nombreConLegajo);
    const emp = empleadosMap[nombreConLegajo];
    if(emp) setFormClaude({...formClaude, empleado_id: emp.id});
  }

  async function guardarClaude(){
    if(!formClaude.licencia_id){ alert("Elegi un plan (Standard/Premium/Max)."); return; }
    try{
      if(editandoClaude && editandoClaude.id){
        await http.put(API_UM+"/asignaciones/licencias/"+editandoClaude.id+"?licencia_id="+formClaude.licencia_id+"&detalle="+encodeURIComponent(formClaude.unidad), {});
      } else {
        if(!formClaude.empleado_id){ alert("Elegi un empleado de la lista (con autocompletado)."); return; }
        await http.post(API_UM+"/asignaciones/licencias", {empleado_id:formClaude.empleado_id, licencia_id:formClaude.licencia_id, detalle:formClaude.unidad});
      }
      cerrarFormClaude();
      cargarClaude();
    } catch(e){ alert("Error al guardar: "+e.message); }
  }

  async function quitarClaude(a){
    if(!confirm(`Quitar la licencia Claude de "${a.responsable}"?`)) return;
    try{
      await http.del(API_UM+"/asignaciones/licencias/"+a.id);
      cargarClaude();
    } catch(e){ alert("Error al quitar: "+e.message); }
  }

  function abrirNuevoEquipo(){ setFormEquipo(emptyEquipo); setEditandoEquipo({}); }
  function abrirEditarEquipo(eq){ setFormEquipo({numero:eq.numero,unidad:eq.unidad,lider:eq.lider,responsable:eq.responsable,email:eq.email,tipo:eq.tipo,estado:eq.estado}); setEditandoEquipo(eq); }
  function cerrarFormEquipo(){ setEditandoEquipo(null); }

  async function guardarEquipo(){
    if(!formEquipo.unidad || !formEquipo.responsable){ alert("Unidad de negocio y responsable son obligatorios."); return; }
    try{
      if(editandoEquipo && editandoEquipo.id){
        await http.put(API_UM+"/equipos/licencias/"+editandoEquipo.id, formEquipo);
      } else {
        await http.post(API_UM+"/equipos/licencias", formEquipo);
      }
      cerrarFormEquipo();
      cargarEquipos();
    } catch(e){ alert("Error al guardar: "+e.message); }
  }

  async function quitarEquipo(eq){
    if(!confirm(`Quitar el equipo "${eq.unidad}"?`)) return;
    try{
      await http.del(API_UM+"/equipos/licencias/"+eq.id);
      cargarEquipos();
    } catch(e){ alert("Error al quitar: "+e.message); }
  }

  return (
    <div>
      <datalist id="empleadosLicenciasDatalist">
        {empleados.map(e=><option key={e.id} value={e.nombre+" (Legajo "+e.legajo+")"}/>)}
      </datalist>
      <div style={{display:"flex",gap:16,rowGap:10,marginBottom:16,alignItems:"center",flexWrap:"wrap"}}>
        {[["claude","Claude"],["adobe","Adobe"],...licsOtras.map(x=>[x,x])].map(([k,l])=>(
          <span key={k} onClick={()=>setSub(k)}
            style={{fontSize:13,cursor:"pointer",fontWeight:600,paddingBottom:6,
            color:sub===k?"var(--accent-hover)":"var(--text-muted)",
            borderBottom:sub===k?"2px solid var(--accent-hover)":"2px solid transparent"}}>{l}</span>
        ))}
        <span style={{color:"var(--text-muted)",fontSize:12,marginLeft:"auto"}}>
          {sub==="claude"?(subClaude==="personal"?`${claudeFiltrado.length} unidades`:`${equiposFiltrado.length} equipos`):sub==="adobe"?`${adobeFiltrado.length} pares`:`${otrasFiltrado.length} asignaciones`}
        </span>
        <button className="btn" onClick={exportarLicencias} style={{marginLeft:8}}>Exportar Excel</button>
        {sub==="adobe" && <button className="btn btn-primary" onClick={abrirNuevoPar}>+ Agregar par</button>}
        {licsOtras.includes(sub) && <button className="btn btn-primary" onClick={abrirNuevaOtra}>+ Agregar</button>}
        {sub==="claude" && subClaude==="personal" && <button className="btn btn-primary" onClick={abrirNuevoClaude}>+ Agregar</button>}
        {sub==="claude" && subClaude==="equipos" && <button className="btn btn-primary" onClick={abrirNuevoEquipo}>+ Agregar equipo</button>}
      </div>

      <div className="search-bar">
        <div style={{position:"relative",flex:1,minWidth:180}}>
          <input style={{width:"100%",paddingRight:30}} placeholder={sub==="claude"?"Buscar unidad, responsable, email, lider...":"Buscar sector, usuario, email, imputacion..."} value={buscar} onChange={e=>setBuscar(e.target.value)}/>
          {buscar && <span onClick={()=>setBuscar("")} title="Limpiar" style={{position:"absolute",right:10,top:"50%",transform:"translateY(-50%)",cursor:"pointer",color:"var(--text-muted)",fontSize:15,fontWeight:700,lineHeight:1}}>&times;</span>}
        </div>
        {sub==="claude" && <select value={fTipoLic} onChange={e=>setFTipoLic(e.target.value)}>
          <option value="">Todos los planes</option>
          <option value="Standard">Standard</option>
          <option value="Premium">Premium</option>
          <option value="Max">Max</option>
        </select>}
        {sub==="claude" && <select value={fEstadoLic} onChange={e=>setFEstadoLic(e.target.value)}>
          <option value="">Todos los estados</option>
          <option value="Activo">Activo</option>
          <option value="Libre">Libre</option>
          <option value="Inactivo">Inactivo</option>
        </select>}
        {(buscar||fTipoLic||fEstadoLic) && <button className="btn" onClick={()=>{setBuscar("");setFTipoLic("");setFEstadoLic("");}}>Limpiar</button>}
      </div>

      {sub==="claude" && (
        <div style={{display:"flex",gap:10,marginBottom:14}}>
          {[["personal","Personal"],["equipos","Equipos"]].map(([k,l])=>(
            <span key={k} onClick={()=>setSubClaude(k)}
              style={{fontSize:12,cursor:"pointer",fontWeight:600,padding:"4px 10px",borderRadius:20,
              background:subClaude===k?"var(--accent-soft)":"transparent",
              color:subClaude===k?"var(--accent-hover)":"var(--text-muted)"}}>{l}</span>
          ))}
        </div>
      )}

      {sub==="claude" && subClaude==="personal" && editandoClaude && (
        <div className="card" style={{padding:16,marginBottom:16,border:"1px solid var(--accent-hover)"}}>
          <div className="form-cols" style={{display:"grid",gridTemplateColumns:"1fr 1fr 1fr",gap:12,marginBottom:12}}>
            <div>
              <label style={{fontSize:12,color:"var(--text-muted)"}}>Empleado {editandoClaude.id?"(no editable)":""}</label>
              <input list="empleadosLicenciasDatalist" value={buscarEmp} disabled={!!editandoClaude.id} onChange={e=>elegirEmpleado(e.target.value)} placeholder="Buscar por nombre o legajo..." style={{width:"100%"}}/>
            </div>
            <div>
              <label style={{fontSize:12,color:"var(--text-muted)"}}>Plan *</label>
              <select value={formClaude.licencia_id} onChange={e=>setFormClaude({...formClaude,licencia_id:e.target.value})} style={{width:"100%"}}>
                <option value="">-----</option>
                {licenciasClaude.map(l=><option key={l.id} value={l.id}>{l.nombre}</option>)}
              </select>
            </div>
            <div>
              <label style={{fontSize:12,color:"var(--text-muted)"}}>Unidad de Negocio</label>
              <input value={formClaude.unidad} onChange={e=>setFormClaude({...formClaude,unidad:e.target.value})} style={{width:"100%"}}/>
            </div>
          </div>
          <div style={{display:"flex",gap:8}}>
            <button className="btn btn-primary" onClick={guardarClaude}>Guardar</button>
            <button className="btn" onClick={cerrarFormClaude}>Cancelar</button>
          </div>
        </div>
      )}

      {sub==="claude" && subClaude==="equipos" && editandoEquipo && (
        <div className="card" style={{padding:16,marginBottom:16,border:"1px solid var(--accent-hover)"}}>
          <div className="form-cols" style={{display:"grid",gridTemplateColumns:"1fr 1fr 1fr",gap:12,marginBottom:12}}>
            <div><label style={{fontSize:12,color:"var(--text-muted)"}}>Numero</label><input value={formEquipo.numero} onChange={e=>setFormEquipo({...formEquipo,numero:e.target.value})} style={{width:"100%"}}/></div>
            <div><label style={{fontSize:12,color:"var(--text-muted)"}}>Unidad de Negocio *</label><input value={formEquipo.unidad} onChange={e=>setFormEquipo({...formEquipo,unidad:e.target.value})} style={{width:"100%"}}/></div>
            <div><label style={{fontSize:12,color:"var(--text-muted)"}}>Lider</label><input value={formEquipo.lider} onChange={e=>setFormEquipo({...formEquipo,lider:e.target.value})} style={{width:"100%"}}/></div>
            <div><label style={{fontSize:12,color:"var(--text-muted)"}}>Responsable *</label><input value={formEquipo.responsable} onChange={e=>setFormEquipo({...formEquipo,responsable:e.target.value})} style={{width:"100%"}}/></div>
            <div><label style={{fontSize:12,color:"var(--text-muted)"}}>Email</label><input value={formEquipo.email} onChange={e=>setFormEquipo({...formEquipo,email:e.target.value})} style={{width:"100%"}}/></div>
            <div>
              <label style={{fontSize:12,color:"var(--text-muted)"}}>Tipo</label>
              <select value={formEquipo.tipo} onChange={e=>setFormEquipo({...formEquipo,tipo:e.target.value})} style={{width:"100%"}}>
                <option value="">-----</option>
                {licenciasClaude.map(l=><option key={l.id} value={l.plan||l.nombre}>{l.nombre}</option>)}
              </select>
            </div>
            <div>
              <label style={{fontSize:12,color:"var(--text-muted)"}}>Estado</label>
              <select value={formEquipo.estado} onChange={e=>setFormEquipo({...formEquipo,estado:e.target.value})} style={{width:"100%"}}>
                <option value="Activo">Activo</option>
                <option value="Libre">Libre</option>
                <option value="Inactivo">Inactivo</option>
              </select>
            </div>
          </div>
          <div style={{display:"flex",gap:8}}>
            <button className="btn btn-primary" onClick={guardarEquipo}>Guardar</button>
            <button className="btn" onClick={cerrarFormEquipo}>Cancelar</button>
          </div>
        </div>
      )}

      {licsOtras.includes(sub) && editandoOtra && (
        <div className="card" style={{padding:16,marginBottom:16,border:"1px solid var(--accent-hover)"}}>
          <div className="form-cols" style={{display:"grid",gridTemplateColumns:"1fr 1fr 1fr 1fr",gap:12,marginBottom:12}}>
            <div>
              <label style={{fontSize:12,color:"var(--text-muted)"}}>Empleado {editandoOtra.id?"(no editable)":"*"}</label>
              <input list="empleadosLicenciasDatalist" value={buscarEmpOtra} disabled={!!editandoOtra.id}
                onChange={e=>{ const v=e.target.value; setBuscarEmpOtra(v); const emp=empleadosMap[v]; if(emp) setFormOtra(f=>({...f,empleado_id:emp.id})); }}
                placeholder="Buscar por nombre o legajo..." style={{width:"100%"}}/>
            </div>
            <div>
              <label style={{fontSize:12,color:"var(--text-muted)"}}>Licencia *</label>
              <select value={formOtra.licencia_id} onChange={e=>setFormOtra({...formOtra,licencia_id:e.target.value})} style={{width:"100%"}}>
                <option value="">-----</option>
                {licenciasOtras.map(l=><option key={l.id} value={l.id}>{l.nombre}{l.plan?" ("+l.plan+")":""}</option>)}
              </select>
            </div>
            <div>
              <label style={{fontSize:12,color:"var(--text-muted)"}}>Cuenta</label>
              <input value={formOtra.cuenta} onChange={e=>setFormOtra({...formOtra,cuenta:e.target.value})} placeholder="usuario@llyasoc.com" style={{width:"100%"}}/>
            </div>
            <div>
              <label style={{fontSize:12,color:"var(--text-muted)"}}>Imputacion</label>
              <input value={formOtra.imputacion} onChange={e=>setFormOtra({...formOtra,imputacion:e.target.value})} style={{width:"100%"}}/>
            </div>
          </div>
          <div style={{display:"flex",gap:8}}>
            <button className="btn btn-primary" onClick={guardarOtra}>Guardar</button>
            <button className="btn" onClick={cerrarFormOtra}>Cancelar</button>
          </div>
        </div>
      )}

      {sub==="adobe" && editandoPar && (
        <div className="card" style={{padding:16,marginBottom:16,border:"1px solid var(--accent-hover)"}}>
          <div className="form-cols" style={{display:"grid",gridTemplateColumns:"1fr 1fr 1fr",gap:12,marginBottom:12}}>
            <div><label style={{fontSize:12,color:"var(--text-muted)"}}>Sector</label><input value={formPar.sector} onChange={e=>setFormPar({...formPar,sector:e.target.value})} style={{width:"100%"}}/></div>
            <div><label style={{fontSize:12,color:"var(--text-muted)"}}>Usuario principal *</label><input value={formPar.usuario_principal} onChange={e=>setFormPar({...formPar,usuario_principal:e.target.value})} style={{width:"100%"}}/></div>
            <div><label style={{fontSize:12,color:"var(--text-muted)"}}>Email principal *</label><input value={formPar.email_principal} onChange={e=>setFormPar({...formPar,email_principal:e.target.value})} style={{width:"100%"}}/></div>
            <div><label style={{fontSize:12,color:"var(--text-muted)"}}>Usuario secundario</label><input value={formPar.usuario_secundario} onChange={e=>setFormPar({...formPar,usuario_secundario:e.target.value})} style={{width:"100%"}}/></div>
            <div><label style={{fontSize:12,color:"var(--text-muted)"}}>Email secundario</label><input value={formPar.email_secundario} onChange={e=>setFormPar({...formPar,email_secundario:e.target.value})} style={{width:"100%"}}/></div>
            <div><label style={{fontSize:12,color:"var(--text-muted)"}}>Imputacion</label><input value={formPar.imputacion} onChange={e=>setFormPar({...formPar,imputacion:e.target.value})} style={{width:"100%"}}/></div>
          </div>
          <div style={{display:"flex",gap:8}}>
            <button className="btn btn-primary" onClick={guardarPar}>Guardar</button>
            <button className="btn" onClick={cerrarFormPar}>Cancelar</button>
          </div>
        </div>
      )}

      {sub==="claude" && subClaude==="personal" && (
        <div className="table-wrap">
          <table><thead><tr>
            {thOrd([["numero","#"],["unidad","Unidad de Negocio"],["lider","Lider"],["responsable","Responsable"],["email","Email"],["tipo","Tipo"],["estado","Estado"],[null,""]])}
          </tr></thead>
          <tbody>
            {!loadingClaude && claudeFiltrado.length===0&&<tr><td colSpan="8"><div className="empty">Sin unidades de negocio con Claude</div></td></tr>}
            {ordenar(claudeFiltrado).map((a,i)=>(
              <tr key={i}>
                <td style={{fontWeight:700,color:"var(--accent-hover)"}}>{a.numero}</td>
                <td style={{fontWeight:600,color:"var(--text)"}}>{a.unidad}</td>
                <td className="td-muted">{a.lider}</td>
                <td style={{fontWeight:600}}>{a.responsable}</td>
                <td className="td-muted">{a.email}</td>
                <td><Tag color={a.tipo==="Premium"||a.tipo.includes("Premium")?"#9085e9":a.tipo.includes("MAX")?"#d03b3b":"#3987e5"} label={a.tipo}/></td>
                <td><span className={`badge ${a.estado==="Activo"||a.estado.includes("Activo")?"badge-green":a.estado==="Libre"?"badge-yellow":"badge-gray"}`}>{a.estado}</span></td>
                <td style={{whiteSpace:"nowrap"}}>
                  <button className="btn" style={{padding:"4px 8px",fontSize:12}} onClick={()=>abrirEditarClaude(a)}>Editar</button>
                  <button className="btn" style={{padding:"4px 8px",fontSize:12,marginLeft:6,color:"#d03b3b",borderColor:"#d03b3b"}} onClick={()=>quitarClaude(a)}>Quitar</button>
                </td>
              </tr>
            ))}
          </tbody></table>
        </div>
      )}

      {sub==="claude" && subClaude==="equipos" && (
        <div className="table-wrap">
          <table><thead><tr>
            {thOrd([["numero","#"],["unidad","Unidad de Negocio"],["lider","Lider"],["responsable","Responsable"],["email","Email"],["tipo","Tipo"],["estado","Estado"],[null,""]])}
          </tr></thead>
          <tbody>
            {!loadingEquipos && equiposFiltrado.length===0&&<tr><td colSpan="8"><div className="empty">Sin cuentas de equipo cargadas</div></td></tr>}
            {ordenar(equiposFiltrado).map((eq,i)=>(
              <tr key={i}>
                <td style={{fontWeight:700,color:"var(--accent-hover)"}}>{eq.numero}</td>
                <td style={{fontWeight:600,color:"var(--text)"}}>{eq.unidad}</td>
                <td className="td-muted">{eq.lider}</td>
                <td style={{fontWeight:600}}>{eq.responsable}</td>
                <td className="td-muted">{eq.email}</td>
                <td><Tag color={eq.tipo==="Premium"||eq.tipo.includes("Premium")?"#9085e9":"#3987e5"} label={eq.tipo}/></td>
                <td><span className={`badge ${eq.estado==="Activo"?"badge-green":"badge-gray"}`}>{eq.estado}</span></td>
                <td style={{whiteSpace:"nowrap"}}>
                  <button className="btn" style={{padding:"4px 8px",fontSize:12}} onClick={()=>abrirEditarEquipo(eq)}>Editar</button>
                  <button className="btn" style={{padding:"4px 8px",fontSize:12,marginLeft:6,color:"#d03b3b",borderColor:"#d03b3b"}} onClick={()=>quitarEquipo(eq)}>Quitar</button>
                </td>
              </tr>
            ))}
          </tbody></table>
        </div>
      )}

      {licsOtras.includes(sub) && (
        <div className="table-wrap">
          <table><thead><tr>
            {thOrd([["plan","Plan"],["empleado","Empleado"],["email","Email"],["sede","Sede"],["centro_costo","Centro de costo"],["detalle","Detalle"],["fecha_desde","Desde"],[null,""]])}
          </tr></thead>
          <tbody>
            {!loadingOtras && otrasFiltrado.length===0&&<tr><td colSpan="8"><div className="empty">Sin asignaciones</div></td></tr>}
            {ordenar(otrasFiltrado).map((o,i)=>(
              <tr key={o.id||i}>
                <td style={{fontWeight:600}}>{o.plan}</td>
                <td style={{fontWeight:700,color:"var(--accent-hover)"}}>{o.empleado}</td>
                <td className="td-muted">{o.email}</td>
                <td className="td-muted">{o.sede}</td>
                <td className="td-muted">{o.centro_costo}</td>
                <td className="td-muted">{o.detalle}</td>
                <td className="td-muted" style={{whiteSpace:"nowrap"}}>{o.fecha_desde}</td>
                <td style={{whiteSpace:"nowrap"}}>
                  <button className="btn" style={{padding:"4px 8px",fontSize:12}} onClick={()=>abrirEditarOtra(o)}>Editar</button>
                  <button className="btn" style={{padding:"4px 8px",fontSize:12,marginLeft:6,color:"#d03b3b",borderColor:"#d03b3b"}} onClick={()=>quitarOtra(o)}>Quitar</button>
                </td>
              </tr>
            ))}
          </tbody></table>
        </div>
      )}
      {sub==="adobe" && (
        <div className="table-wrap">
          <table><thead><tr>
            {thOrd([["sector","Sector"],["usuario_principal","Usuario Principal"],["email_principal","Email"],["usuario_secundario","Usuario Secundario"],["email_secundario","Email"],["imputacion","Imputacion"],[null,""]])}
          </tr></thead>
          <tbody>
            {!loadingAdobe && adobeFiltrado.length===0&&<tr><td colSpan="7"><div className="empty">Sin pares Adobe cargados</div></td></tr>}
            {ordenar(adobeFiltrado).map((p,i)=>(
              <tr key={i}>
                <td style={{fontWeight:600}}>{p.sector}</td>
                <td style={{fontWeight:700,color:"var(--accent-hover)"}}>{p.usuario_principal}</td>
                <td className="td-muted">{p.email_principal}</td>
                <td className="td-muted">{p.usuario_secundario}</td>
                <td className="td-muted">{p.email_secundario}</td>
                <td className="td-muted">{p.imputacion}</td>
                <td style={{whiteSpace:"nowrap"}}>
                  <button className="btn" style={{padding:"4px 8px",fontSize:12}} onClick={()=>abrirEditarPar(p)}>Editar</button>
                  <button className="btn" style={{padding:"4px 8px",fontSize:12,marginLeft:6,color:"#d03b3b",borderColor:"#d03b3b"}} onClick={()=>quitarPar(p)}>Quitar</button>
                </td>
              </tr>
            ))}
          </tbody></table>
        </div>
      )}
    </div>
  );
}
