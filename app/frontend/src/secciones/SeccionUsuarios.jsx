// SeccionUsuarios.jsx — Pestaña Usuarios: nomina, ficha del empleado y ABM.
import { useState, useEffect } from "react";
import ABMForm, { OFICINA_TO_SEDE, clasificarSectorCentro } from "../ABMForm";
import HistorialEmpleado from "../HistorialEmpleado";
import { API_UM, umFetch, http } from "../api";
import { Badge, Tag } from "../ui";
import { generarResumenABM } from "../resumenABM";

// La sincronizacion con el Excel de nomina esta desactivada a proposito (el boton no se muestra).
const MOSTRAR_SYNC_EXCEL = false;

export function SeccionUsuarios({ empleados, setEmpleados, assets, user, searchEmp, setSearchEmp, fSedeEmp, setFSedeEmp, loadEmpleadoDetalle, empleadoSelected, setEmpleadoSelected, empLicencias, empHardware, setEmpLicencias, setEmpHardware, setEmpActivo }) {
  const SEDES_EMP = ["Todas","CABA1","CABA2","Rosario","Cordoba","Corrientes","Mendoza","Neuquen","Tigre"];
  const LICS_FILTRO = ["Todas", ...Array.from(new Set(empleados.flatMap(e=>e.licencias||[]))).sort()];
  const [fLic, setFLic] = useState("Todas");
  const [fCategoria, setFCategoria] = useState("Todas");
  const [sortLegajo, setSortLegajo] = useState("asc");
  const [ordEmp, setOrdEmp] = useState({col:null,asc:true});
  const [pagEmp, setPagEmp] = useState(1);
  const [syncing, setSyncing] = useState(false);
  const [syncMsg, setSyncMsg] = useState("");
  const [licenciasDisponibles, setLicenciasDisponibles] = useState([]);
  const [nuevaLicId, setNuevaLicId] = useState("");
  const [nuevaLicDetalle, setNuevaLicDetalle] = useState("");
  useEffect(()=>{ umFetch(API_UM+"/licencias").then(r=>r.json()).then(setLicenciasDisponibles).catch(()=>{}); },[]);
  async function asignarLicencia() {
    if(!nuevaLicId){ alert("Elegi una licencia."); return; }
    try {
      await umFetch(API_UM+"/asignaciones/licencias?usuario="+encodeURIComponent(user?.username||""),{method:"POST",headers:{"Content-Type":"application/json"},body:JSON.stringify({empleado_id:empleadoSelected.id,licencia_id:nuevaLicId,detalle:nuevaLicDetalle,activo:"1"})});
      setNuevaLicId(""); setNuevaLicDetalle("");
      loadEmpleadoDetalle(empleadoSelected);
    } catch(e){ alert("Error al asignar: "+e.message); }
  }
  async function quitarLicencia(aid) {
    if(!confirm("Quitar esta licencia?")) return;
    try {
      await umFetch(API_UM+"/asignaciones/licencias/"+aid+"?usuario="+encodeURIComponent(user?.username||""),{method:"DELETE"});
      loadEmpleadoDetalle(empleadoSelected);
    } catch(e){ alert("Error al quitar: "+e.message); }
  }
  const [hwAsignado, setHwAsignado] = useState([]);
  const [hwHistorial, setHwHistorial] = useState([]);
  const [nuevoAssetId, setNuevoAssetId] = useState("");
  const [verHistorial, setVerHistorial] = useState(false);
  async function cargarHardware() {
    if(!empleadoSelected) return;
    try {
      const [act,hist] = await Promise.all([
        umFetch(API_UM+"/empleados/"+empleadoSelected.id+"/hardware").then(r=>r.json()),
        umFetch(API_UM+"/empleados/"+empleadoSelected.id+"/hardware/historial").then(r=>r.json())
      ]);
      setHwAsignado(Array.isArray(act)?act:[]);
      setHwHistorial(Array.isArray(hist)?hist:[]);
    } catch { /* sin conexion: la ficha queda sin equipos */ }
  }
  // eslint-disable-next-line react-hooks/exhaustive-deps -- recarga solo al cambiar de empleado
  useEffect(()=>{ if(empleadoSelected) cargarHardware(); },[empleadoSelected]);
  async function asignarHardware() {
    if(!nuevoAssetId){ alert("Elegi un equipo."); return; }
    const asset = assets.find(a=>a.id===nuevoAssetId);
    if(!asset) return;
    try {
      await umFetch(API_UM+"/asignaciones/hardware?usuario="+encodeURIComponent(user?.username||""),{method:"POST",headers:{"Content-Type":"application/json"},body:JSON.stringify({empleado_id:empleadoSelected.id,tipo:asset.tipo||"Equipo",descripcion:(asset.nombre||asset.modelo||"")+" - "+(asset.serial||""),asset_id:asset.id,activo:"1"})});
      setNuevoAssetId("");
      cargarHardware();
    } catch(e){ alert("Error al asignar: "+e.message); }
  }
  async function quitarHardware(aid) {
    if(!confirm("Quitar este equipo del empleado?")) return;
    try {
      await umFetch(API_UM+"/asignaciones/hardware/"+aid+"?usuario="+encodeURIComponent(user?.username||""),{method:"DELETE"});
      cargarHardware();
    } catch(e){ alert("Error al quitar: "+e.message); }
  }

  const [editandoEmp, setEditandoEmp] = useState(false);
  const [empEdit, setEmpEdit] = useState({});
  const [guardandoEmp, setGuardandoEmp] = useState(false);
  async function guardarEmpleado() {
    setGuardandoEmp(true);
    try {
      const r = await umFetch(API_UM+"/empleados/"+empleadoSelected.id+"?usuario="+encodeURIComponent(user?.username||""),{method:"PUT",headers:{"Content-Type":"application/json"},body:JSON.stringify(empEdit)});
      if(!r.ok) throw new Error("HTTP "+r.status);
      const data = await umFetch(API_UM+"/empleados/con-licencias").then(x=>x.json());
      setEmpleados(data);
      const act = data.find(e=>e.id===empleadoSelected.id);
      if(act) setEmpleadoSelected(act);
      setEditandoEmp(false);
    } catch(e){ alert("Error al guardar: "+e.message); }
    setGuardandoEmp(false);
  }
  const [showBaja, setShowBaja] = useState(false);
  const [abmTipo, setAbmTipo] = useState("Baja");

  async function manejarSubmitABM(tipoAbm, formData) {
    const emp = empleadoSelected;
    const hoy = new Date().toLocaleDateString('es-AR',{day:'2-digit',month:'2-digit',year:'numeric'});
    let idAfectado = emp ? emp.id : null;

    if(tipoAbm==="Baja") {
      if(!confirm("CONFIRMAR BAJA de "+emp.nombre+"?\n\nEsto va a marcar al empleado como INACTIVO y cerrar todos sus equipos y licencias. Se conserva el historial.")) return;
      const r = await umFetch(API_UM+"/empleados/"+emp.id+"/baja?usuario="+encodeURIComponent(formData.solicitante||""),{method:"POST"});
      if(!r.ok) throw new Error("HTTP "+r.status);
    } else if(tipoAbm==="Modificación") {
      const nombreCompleto = (formData.apellidos+", "+formData.nombres).trim();
      const body = {
        legajo: formData.legajo ? parseInt(formData.legajo,10) : null,
        nombre: nombreCompleto,
        centro_costo: formData.centroCostos,
        subauxiliar: formData.sector,
        categoria: formData.puesto,
        fecha_ingreso: formData.fechaEjecucion,
        email: emp.email || "",
        sede: OFICINA_TO_SEDE[formData.oficina] || emp.sede || "",
        estado: emp.estado || "Activo"
      };
      const r = await umFetch(API_UM+"/empleados/"+emp.id+"?usuario="+encodeURIComponent(formData.solicitante||""),{method:"PUT",headers:{"Content-Type":"application/json"},body:JSON.stringify(body)});
      if(!r.ok) throw new Error("HTTP "+r.status);
    } else if(tipoAbm==="Alta") {
      const nombreCompleto = (formData.apellidos+", "+formData.nombres).trim();
      const body = {
        legajo: formData.legajo ? parseInt(formData.legajo,10) : null,
        nombre: nombreCompleto,
        centro_costo: formData.centroCostos,
        subauxiliar: formData.sector,
        categoria: formData.puesto,
        fecha_ingreso: formData.fechaEjecucion,
        email: "",
        sede: OFICINA_TO_SEDE[formData.oficina] || "",
        estado: "Activo"
      };
      const r = await umFetch(API_UM+"/empleados?usuario="+encodeURIComponent(formData.solicitante||""),{method:"POST",headers:{"Content-Type":"application/json"},body:JSON.stringify(body)});
      if(!r.ok) throw new Error("HTTP "+r.status);
      const nuevo = await r.json();
      idAfectado = nuevo.id;
    }

    const filas = [
      ["N° de Legajo", formData.legajo],
      ["Tipo de ABM", tipoAbm],
      ["Fecha de generación", hoy],
      ["Solicitante de ABM", formData.solicitante],
      [tipoAbm==="Alta"?"Fecha de ingreso":"Fecha de ejecución", formData.fechaEjecucion],
      ["__sep__"],
      ["Nombres", formData.nombres],
      ["Apellidos", formData.apellidos],
      [tipoAbm==="Alta"?"Responsable / Tutor":"Manager (de quién depende)", formData.manager],
      ["Oficina", formData.oficina],
      ["Puesto / Categoría", formData.puesto],
      ["__sep__"],
      ["Sector / Departamento", formData.sector],
      ["Centro de Costos", formData.centroCostos],
    ];
    if(tipoAbm!=="Baja" && (formData.rutaFileServer||formData.rutaSharepoint||formData.sistemasApps)){
      filas.push(["__sep__"]);
      if(formData.rutaFileServer) filas.push(["Ruta File Server", formData.rutaFileServer]);
      if(formData.rutaSharepoint) filas.push(["Ruta SharePoint", formData.rutaSharepoint]);
      if(formData.sistemasApps) filas.push(["Sistemas o aplicaciones", formData.sistemasApps]);
    }
    if(tipoAbm!=="Alta" && ((empHardware&&empHardware.length>0) || (empLicencias&&empLicencias.length>0))){
      filas.push(["__sep__"]);
      const hwTxt = (empHardware||[]).map(h=>h.descripcion||h.tipo).join(", ") || "Sin equipos";
      const licTxt = (empLicencias||[]).map(l=>l.licencia_nombre||l.nombre||l.detalle||"Licencia").join(", ") || "Sin licencias";
      filas.push(["Equipos asignados", hwTxt]);
      filas.push(["Licencias asignadas", licTxt]);
    }
    if(tipoAbm==="Baja"){
      filas.push(["__sep__"]);
      filas.push(["¿Requiere backup?", formData.backup]);
      if(formData.backup==="Sí") filas.push(["Detalle del backup", formData.detalleBackup]);
      filas.push(["¿Correo se mantiene?", formData.correoMantiene]);
      filas.push(["¿Buzón por 90 días?", formData.buzon90]);
      filas.push(["Activos a entregar", (formData.activosEntrega||[]).join(", ")||"-"]);
    }
    if(tipoAbm==="Modificación"){
      filas.push(["__sep__"]);
      filas.push(["Aprobación", formData.aprobacionModif||"-"]);
      if(formData.mantieneAcceso) filas.push(["¿Mantiene acceso?", formData.mantieneAcceso]);
      if(formData.accesosNuevos) filas.push(["Accesos nuevos", formData.accesosNuevos]);
    }
    filas.push(["__sep__"]);
    filas.push(["Características Especiales", formData.caracEspeciales||"-"]);

    generarResumenABM(tipoAbm, filas);
    setShowBaja(false);

    const data = await umFetch(API_UM+"/empleados/con-licencias").then(x=>x.json());
    setEmpleados(data);
    if(idAfectado){
      const actualizado = data.find(e=>e.id===idAfectado);
      if(actualizado) setEmpleadoSelected(actualizado);
    }
    cargarHardware();
  }

  async function sincronizar() {
    setSyncing(true); setSyncMsg("");
    try {
      const r1 = await umFetch(API_UM + "/sync/excel", { method:"POST" }).then(r=>r.json());
      const r2 = await umFetch(API_UM + "/sync/licencias", { method:"POST" }).then(r=>r.json());
      setSyncMsg(`✓ ${r1.nuevos} nuevos, ${r1.actualizados} actualizados, ${r2.asignados} lic. nuevas`);
      // Forzar reload pasando datos al padre no es posible, recargar pagina
      setTimeout(()=>window.location.reload(), 1500);
    } catch { setSyncMsg("Error al sincronizar"); }
    setSyncing(false);
  }
  const sedeBg = s => ({CABA1:"#0B4F6C",CABA2:"#0B4F6C",Rosario:"#8E44AD",Cordoba:"#E67E22",Corrientes:"#16A085",Mendoza:"#C0392B",Tigre:"#27AE60",Neuquen:"#2980B9"}[s]||"#666");

  if (empleadoSelected) {
    return (
      <>
      <div>
        <div style={{display:"flex",gap:8,alignItems:"center"}}>
          <button className="btn" onClick={()=>{setEmpleadoSelected(null);setEmpLicencias([]);setEmpHardware([]);setEmpActivo(null);}}>← Volver</button>
          {!editandoEmp && <button className="btn btn-primary" onClick={()=>{setEmpEdit({nombre:empleadoSelected.nombre||"",legajo:empleadoSelected.legajo||"",email:empleadoSelected.email||"",sede:empleadoSelected.sede||"",categoria:empleadoSelected.categoria||"",centro_costo:empleadoSelected.centro_costo||"",subauxiliar:empleadoSelected.subauxiliar||"",fecha_ingreso:empleadoSelected.fecha_ingreso||"",estado:empleadoSelected.estado||"Activo"});setEditandoEmp(true);}}>✎ Editar</button>}
          {editandoEmp && <button className="btn btn-primary" onClick={guardarEmpleado} disabled={guardandoEmp}>{guardandoEmp?"Guardando...":"Guardar"}</button>}
          {editandoEmp && <button className="btn" onClick={()=>setEditandoEmp(false)}>Cancelar</button>}
          {!editandoEmp && <button className="btn btn-primary" onClick={()=>{setAbmTipo("Modificación");setShowBaja(true);}}>Modificar (ABM)</button>}
          {!editandoEmp && empleadoSelected.estado==="Activo" && <button className="btn btn-danger" onClick={()=>{setAbmTipo("Baja");setShowBaja(true);}}>Dar de baja</button>}
        </div>
        <div style={{display:"flex",alignItems:"center",gap:16,background:"var(--surface)",border:"1px solid var(--border)",borderRadius:"var(--radius)",padding:"20px 24px",margin:"16px 0",boxShadow:"var(--shadow-card)"}}>
          <div style={{width:52,height:52,borderRadius:"50%",background:"linear-gradient(135deg,var(--accent),var(--accent-teal))",color:"#fff",display:"flex",alignItems:"center",justifyContent:"center",fontSize:22,fontWeight:700,flexShrink:0}}>
            {empleadoSelected.nombre?.split(",")[0]?.trim()[0]||"?"}
          </div>
          <div>
            <div style={{fontSize:17,fontWeight:700,color:"var(--text)"}}>{empleadoSelected.nombre}</div>
            <div style={{fontSize:12,color:"var(--text-muted)"}}>{empleadoSelected.categoria} · {clasificarSectorCentro(empleadoSelected.subauxiliar, empleadoSelected.centro_costo).centroCostos}</div>
            <div style={{fontSize:12,color:"var(--text-muted)"}}>{empleadoSelected.email}</div>
          </div>
          <div style={{marginLeft:"auto",display:"flex",gap:8}}>
            <Tag color={sedeBg(empleadoSelected.sede)} label={empleadoSelected.sede}/>
            <Badge label={empleadoSelected.estado} map={{Activo:"badge-green",Inactivo:"badge-gray"}}/>
          </div>
        </div>
        <div className="grid-2">
          <div className="card">
            <div className="card-head"><div className="card-title">👤 Datos</div></div>
            <div className="card-body">
              {!editandoEmp ? (
                [["Legajo",empleadoSelected.legajo],["Ingreso",empleadoSelected.fecha_ingreso],["Subauxiliar",empleadoSelected.subauxiliar],["Email",empleadoSelected.email],["Centro de costo",empleadoSelected.centro_costo],["Estado",empleadoSelected.estado]].map(([k,v])=>(
                  <div key={k} className="field"><span className="field-label">{k}</span><span className="field-value">{v}</span></div>
                ))
              ) : (
                <div style={{display:"flex",flexDirection:"column",gap:8}}>
                  {[["nombre","Nombre"],["legajo","Legajo"],["email","Email"],["centro_costo","Centro de costo"],["subauxiliar","Subauxiliar"],["fecha_ingreso","Ingreso"]].map(([k,l])=>(
                    <div key={k}><label style={{fontSize:11,color:"var(--text-muted)",display:"block",marginBottom:2}}>{l}</label>
                      <input value={empEdit[k]||""} onChange={e=>setEmpEdit({...empEdit,[k]:e.target.value})} style={{width:"100%",padding:"6px 8px",border:"1px solid var(--border-strong)",borderRadius:6,fontSize:13}}/></div>
                  ))}
                  <div><label style={{fontSize:11,color:"var(--text-muted)",display:"block",marginBottom:2}}>Sede</label>
                    <select value={empEdit.sede||""} onChange={e=>setEmpEdit({...empEdit,sede:e.target.value})} style={{width:"100%",padding:"6px 8px",border:"1px solid var(--border-strong)",borderRadius:6,fontSize:13}}>
                      {["CABA1","CABA2","Rosario","Cordoba","Corrientes","Mendoza","Neuquen","Tigre","Resguarda"].map(s=><option key={s}>{s}</option>)}</select></div>
                  <div><label style={{fontSize:11,color:"var(--text-muted)",display:"block",marginBottom:2}}>Categoria</label>
                    <input value={empEdit.categoria||""} onChange={e=>setEmpEdit({...empEdit,categoria:e.target.value})} style={{width:"100%",padding:"6px 8px",border:"1px solid var(--border-strong)",borderRadius:6,fontSize:13}}/></div>
                  <div><label style={{fontSize:11,color:"var(--text-muted)",display:"block",marginBottom:2}}>Estado</label>
                    <select value={empEdit.estado||"Activo"} onChange={e=>setEmpEdit({...empEdit,estado:e.target.value})} style={{width:"100%",padding:"6px 8px",border:"1px solid var(--border-strong)",borderRadius:6,fontSize:13}}>
                      {["Activo","Inactivo"].map(s=><option key={s}>{s}</option>)}</select></div>
                </div>
              )}
            </div>
          </div>
          <div className="card">
            <div className="card-head"><div className="card-title">💻 Equipos asignados</div></div>
            <div className="card-body">
              {hwAsignado.length===0 && <div className="empty">Sin equipos asignados</div>}
              {hwAsignado.map(h=>(
                <div key={h.id} className="field" style={{display:"flex",alignItems:"center",gap:8}}>
                  <span className="field-value" style={{flex:1,fontWeight:600}}>{h.descripcion||h.tipo}</span>
                  <Tag color="#3987e5" label={h.tipo}/>
                  <button className="btn btn-danger" style={{padding:"2px 8px",fontSize:11}} onClick={()=>quitarHardware(h.id)}>Quitar</button>
                </div>
              ))}
              <div style={{marginTop:12,paddingTop:12,borderTop:"1px solid var(--border)",display:"flex",gap:8,alignItems:"center",flexWrap:"wrap"}}>
                <select value={nuevoAssetId} onChange={e=>setNuevoAssetId(e.target.value)} style={{flex:1,minWidth:180,padding:"6px 8px",border:"1px solid var(--border-strong)",borderRadius:6,fontSize:13}}>
                  <option value="">+ Asignar equipo del inventario...</option>
                  {[...assets].sort((a,b)=>(a.nombre||a.modelo||"").localeCompare(b.nombre||b.modelo||"")).map(a=>(
                    <option key={a.id} value={a.id}>{(a.nombre||a.modelo||"?")} - {a.tipo} {a.serial?("("+a.serial+")"):""}</option>
                  ))}
                </select>
                <button className="btn btn-primary" style={{padding:"6px 12px",fontSize:12}} onClick={asignarHardware}>Asignar</button>
              </div>
              {hwHistorial.filter(h=>h.activo==="0").length>0 && (
                <div style={{marginTop:12}}>
                  <button className="btn" style={{padding:"4px 10px",fontSize:11}} onClick={()=>setVerHistorial(v=>!v)}>{verHistorial?"Ocultar historial":"Ver historial ("+hwHistorial.filter(h=>h.activo==="0").length+")"}</button>
                  {verHistorial && <div style={{marginTop:8}}>
                    {hwHistorial.filter(h=>h.activo==="0").map(h=>(
                      <div key={h.id} className="field" style={{opacity:0.7}}>
                        <span className="field-label">{h.descripcion||h.tipo}</span>
                        <span className="field-value" style={{fontSize:11}}>{h.fecha_desde} a {h.fecha_hasta||"?"}</span>
                      </div>
                    ))}
                  </div>}
                </div>
              )}
            </div>
          </div>
          <div className="card">
            <div className="card-head"><div className="card-title">📦 Hardware estandar</div></div>
            <div className="card-body">
              {["Auriculares","Mouse","Teclado Numerico"].map(h=>(
                <div key={h} className="field"><span className="field-label">{h}</span><span className="field-value" style={{color:"var(--good)",fontWeight:600}}>✓ Asignado</span></div>
              ))}
            </div>
          </div>
          <div className="card">
            <div className="card-head"><div className="card-title">🔑 Licencias</div></div>
            <div className="card-body">
              {empLicencias.length===0 ? <div className="empty">Sin licencias especiales</div> :
              empLicencias.map(l=>(
                <div key={l.asignacion.id} className="field" style={{display:"flex",alignItems:"center",gap:8}}>
                  <span className="field-label">{l.licencia?.nombre}</span>
                  <span className="field-value" style={{flex:1}}>{l.asignacion.detalle}</span>
                  <button className="btn btn-danger" style={{padding:"2px 8px",fontSize:11}} onClick={()=>quitarLicencia(l.asignacion.id)}>Quitar</button>
                </div>
              ))}
              <div style={{marginTop:12,paddingTop:12,borderTop:"1px solid var(--border)",display:"flex",gap:8,alignItems:"center",flexWrap:"wrap"}}>
                <select value={nuevaLicId} onChange={e=>setNuevaLicId(e.target.value)} style={{flex:1,minWidth:140,padding:"6px 8px",border:"1px solid var(--border-strong)",borderRadius:6,fontSize:13}}>
                  <option value="">+ Asignar licencia...</option>
                  {licenciasDisponibles.map(l=><option key={l.id} value={l.id}>{l.nombre}</option>)}
                </select>
                <input placeholder="Detalle (opcional)" value={nuevaLicDetalle} onChange={e=>setNuevaLicDetalle(e.target.value)} style={{flex:1,minWidth:120,padding:"6px 8px",border:"1px solid var(--border-strong)",borderRadius:6,fontSize:13}}/>
                <button className="btn btn-primary" style={{padding:"6px 12px",fontSize:12}} onClick={asignarLicencia}>Asignar</button>
              </div>
            </div>
          </div>
        </div>
        <HistorialEmpleado empleadoId={empleadoSelected.id} cargar={id=>http.get(API_UM+"/empleados/"+id+"/historial")}
          recarga={[empLicencias.length, hwAsignado.length, empleadoSelected.nombre, empleadoSelected.estado, empleadoSelected.categoria].join("|")}/>
      </div>
      {showBaja && empleadoSelected && (
        <ABMForm
          tipoInicial={abmTipo}
          empleado={empleadoSelected}
          empleados={empleados}
          hardware={empHardware}
          licencias={empLicencias}
          onClose={()=>setShowBaja(false)}
          onSubmit={manejarSubmitABM}
        />
      )}
      </>
    );
  }

  const usuariosConEquipo = new Set(assets.map(a=>a.usuario?.toLowerCase().trim()).filter(Boolean));

  async function exportarEmpleados(){
    try{
      const ExcelJS = (await import("exceljs")).default; // se carga recien al exportar
      const wb = new ExcelJS.Workbook();
      const ws = wb.addWorksheet("Empleados");
      ws.columns = [{header:"Legajo",key:"legajo",width:10},{header:"Nombre",key:"nombre",width:32},{header:"Centro de Costo",key:"centro",width:26},{header:"Categoria",key:"categoria",width:20},{header:"Sede",key:"sede",width:14},{header:"Email",key:"email",width:32},{header:"Estado",key:"estado",width:12}];
      aplicarOrdenEmp(filtrados).forEach(e=>ws.addRow({legajo:e.legajo,nombre:e.nombre,centro:clasificarSectorCentro(e.subauxiliar,e.centro_costo).centroCostos,categoria:e.categoria,sede:e.sede,email:e.email,estado:e.estado}));
      ws.getRow(1).font={bold:true,color:{argb:"FFFFFFFF"}};
      ws.getRow(1).eachCell(c=>{c.fill={type:"pattern",pattern:"solid",fgColor:{argb:"FF0B7285"}};});
      const buf=await wb.xlsx.writeBuffer();
      const url=URL.createObjectURL(new Blob([buf],{type:"application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"}));
      const a=document.createElement("a"); a.href=url; a.download="empleados_llya.xlsx"; a.click(); URL.revokeObjectURL(url);
    }catch(e){ alert("Error al exportar: "+e.message); }
  }
  function sortEmp(col){ setOrdEmp(o=>({col, asc: o.col===col ? !o.asc : true})); }
  function aplicarOrdenEmp(arr){
    if(!ordEmp.col) return arr;
    const get = { legajo:e=>e.legajo, nombre:e=>e.nombre, centro:e=>clasificarSectorCentro(e.subauxiliar,e.centro_costo).centroCostos, categoria:e=>e.categoria, sede:e=>e.sede, email:e=>e.email, estado:e=>e.estado }[ordEmp.col];
    if(!get) return arr;
    return [...arr].sort((a,b)=>{ const va=(get(a)??"").toString(), vb=(get(b)??"").toString(); const r=va.localeCompare(vb,"es",{numeric:true,sensitivity:"base"}); return ordEmp.asc?r:-r; });
  }
  const filtrados = empleados
    .filter(e=>{
      const q = searchEmp.toLowerCase();
      const ms = !q||e.nombre?.toLowerCase().includes(q)||e.email?.toLowerCase().includes(q)||String(e.legajo).includes(q);
      const mse = fSedeEmp==="Todas"||e.sede===fSedeEmp;
      const prefijo = e.email?.split("@")[0]?.toLowerCase().trim();
      const msl = fLic==="__sin_equipo__"
        ? (prefijo && !usuariosConEquipo.has(prefijo))
        : fLic==="Todas"||(e.licencias||[]).includes(fLic);
      const msc = fCategoria==="Todas"||e.categoria===fCategoria;
      // Si hay texto de busqueda, ignora los filtros de dropdown y busca sobre todos
      if(q) return ms;
      return mse&&msl&&msc;
    })
    .sort((a,b)=> sortLegajo==="asc" ? a.legajo-b.legajo : b.legajo-a.legajo);

  return (
    <div>
      <div className="search-bar">
        <div style={{position:"relative",flex:1,minWidth:180}}><input style={{width:"100%",paddingRight:30}} placeholder="Buscar nombre, email, legajo..." value={searchEmp} onChange={e=>setSearchEmp(e.target.value)}/>{searchEmp && <span onClick={()=>setSearchEmp("")} title="Limpiar" style={{position:"absolute",right:10,top:"50%",transform:"translateY(-50%)",cursor:"pointer",color:"var(--text-muted)",fontSize:15,fontWeight:700,lineHeight:1}}>&times;</span>}</div>
        <select value={fSedeEmp} onChange={e=>setFSedeEmp(e.target.value)}>
          {SEDES_EMP.map(s=><option key={s}>{s}</option>)}
        </select>
        <select value={fLic} onChange={e=>setFLic(e.target.value)}>
          {LICS_FILTRO.map(l=><option key={l}>{l}</option>)}
          {user?.rol==="admin"&&<option value="__sin_equipo__">Sin equipo asignado</option>}
        </select>
        <select value={fCategoria} onChange={e=>setFCategoria(e.target.value)}>
          <option value="Todas">Todas las categorias</option>
          {[...new Set(empleados.map(e=>e.categoria).filter(Boolean))].sort().map(c=><option key={c} value={c}>{c}</option>)}
        </select>
        <span style={{color:"var(--text-muted)",fontSize:12,alignSelf:"center"}}>{filtrados.length} empleados</span>
        {MOSTRAR_SYNC_EXCEL && <button className="btn btn-primary" onClick={sincronizar} disabled={syncing} style={{marginLeft:"auto"}}>
          {syncing?"Sincronizando...":"↻ Sincronizar Excel"}
        </button>}
        {syncMsg&&<span style={{fontSize:12,color:"var(--good)",alignSelf:"center"}}>{syncMsg}</span>}
        <button className="btn" onClick={exportarEmpleados} style={{marginLeft:"auto"}}>Exportar Excel</button>
      </div>

      <div className="table-wrap">
        <table><thead><tr>
          <th style={{cursor:"pointer",userSelect:"none"}} onClick={()=>setSortLegajo(s=>s==="asc"?"desc":"asc")}>
            Legajo {sortLegajo==="asc"?"↑":"↓"}
          </th>
          {[["nombre","Nombre"],["centro","Centro de Costo"],["categoria","Categoria"],["sede","Sede"],["email","Email"],["estado","Estado"],[null,"Licencias"]].map(([k,h])=>(
            <th key={h} onClick={()=>k&&sortEmp(k)} style={{cursor:k?"pointer":"default",userSelect:"none"}}>{h}{(k&&ordEmp.col===k)?(ordEmp.asc?" \u2191":" \u2193"):""}</th>
          ))}
        </tr></thead>
        <tbody>
          {filtrados.length===0&&<tr><td colSpan="8"><div className="empty">Sin empleados que coincidan</div></td></tr>}
          {aplicarOrdenEmp(filtrados).slice((pagEmp-1)*50, pagEmp*50).map((e)=>(
            <tr key={e.id} className="clickable" onClick={()=>loadEmpleadoDetalle(e)}>
              <td>{e.legajo}</td>
              <td style={{fontWeight:600,color:"var(--accent-hover)"}}>{e.nombre}</td>
              <td>{clasificarSectorCentro(e.subauxiliar, e.centro_costo).centroCostos}</td>
              <td>{e.categoria}</td>
              <td><Tag color={sedeBg(e.sede)} label={e.sede}/></td>
              <td className="td-muted">{e.email}</td>
              <td><Badge label={e.estado} map={{Activo:"badge-green",Inactivo:"badge-gray"}}/></td>
              <td>{(e.licencias||[]).map(l=>(
                <span key={l} style={{marginRight:4,display:"inline-block"}}><Tag color={l.includes("Claude")?"#9085e9":l==="Adobe Acrobat"?"#e66767":l==="IDEA"?"#3987e5":"#d95926"} label={l.replace("Adobe Acrobat","Adobe").replace("Claude Standard","Claude Std").replace("Claude Premium","Claude Pro")}/></span>
              ))}</td>
            </tr>
          ))}
        </tbody></table>
        {(()=>{ const tot=aplicarOrdenEmp(filtrados).length, tp=Math.max(1,Math.ceil(tot/50)); if(tot<=50) return null; return (
          <div style={{display:"flex",gap:8,alignItems:"center",justifyContent:"center",padding:"12px 0"}}>
            <button className="btn" disabled={pagEmp<=1} onClick={()=>{setPagEmp(p=>Math.max(1,p-1));document.querySelector(".content")?.scrollTo({top:0,behavior:"smooth"});}}>Anterior</button>
            <span style={{fontSize:12,color:"var(--text-muted)"}}>Pagina {pagEmp} de {tp} — {tot} empleados</span>
            <button className="btn" disabled={pagEmp>=tp} onClick={()=>{setPagEmp(p=>Math.min(tp,p+1));document.querySelector(".content")?.scrollTo({top:0,behavior:"smooth"});}}>Siguiente</button>
          </div>
        ); })()}
      </div>
    </div>
  );
}
