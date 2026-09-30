// SeccionPerfil.jsx — Pestaña Mi perfil.
import { useState, useEffect } from "react";
import { AUTH, apiFetch } from "../api";

export function SeccionPerfil() {
  const [p, setP] = useState(null);
  const [tab, setTab] = useState("datos");
  const [form, setForm] = useState({nombre:"", email:""});
  const [editando, setEditando] = useState(false);
  const [msg, setMsg] = useState("");
  const [pass, setPass] = useState({actual:"", nuevo:"", confirmar:""});
  const [passMsg2, setPassMsg2] = useState("");

  function cargar(){
    apiFetch(AUTH+"/perfil")
      .then(r=>r.json()).then(d=>{ setP(d); setForm({nombre:d.nombre||"", email:d.email||""}); })
      .catch(()=>{});
  }
  useEffect(()=>{ cargar(); },[]);

  async function guardar(){
    try{
      const r = await apiFetch(AUTH+"/perfil", { method:"PUT",
        headers:{ "Content-Type":"application/json" },
        body: JSON.stringify(form) });
      if(r.ok){ setMsg("Perfil actualizado."); setEditando(false); cargar(); }
      else { const d = await r.json().catch(()=>({})); setMsg("Error: "+(d.detail||r.status)); }
    } catch(e){ setMsg("Error: "+e.message); }
  }

  async function cambiarPass(){
    if(!pass.actual||!pass.nuevo){ setPassMsg2("Completa los campos."); return; }
    if(pass.nuevo!==pass.confirmar){ setPassMsg2("Las contrasenas no coinciden."); return; }
    if(pass.nuevo.length<12){ setPassMsg2("Minimo 12 caracteres, combinando mayusculas, minusculas, numeros o simbolos."); return; }
    try{
      const r = await apiFetch(AUTH+"/cambiar-password", { method:"POST", credentials:"same-origin",
        headers:{ "Content-Type":"application/json" },
        body: JSON.stringify({ password_actual:pass.actual, password_nuevo:pass.nuevo }) });
      const d = await r.json().catch(()=>({}));
      if(r.ok){
        // El backend invalida las sesiones anteriores al cambio: hay que volver a entrar.
        alert("Contrasena cambiada. Volve a iniciar sesion con la nueva.");
        window.location.reload();
      }
      else setPassMsg2("Error: "+(d.detail||r.status));
    } catch(e){ setPassMsg2("Error: "+e.message); }
  }

  if(!p) return <div className="loading-wrap"><div className="spinner"/><span className="loading-text">Cargando perfil...</span></div>;

  const ini = (p.nombre||p.username||"?").split(" ").map(x=>x[0]).slice(0,2).join("").toUpperCase();
  const rolLabel = {superadmin:"Superadministrador", admin:"Administrador", editor:"Editor", viewer:"Solo lectura"}[p.rol] || p.rol;

  return (
    <div style={{maxWidth:820}}>
      <div style={{display:"flex",alignItems:"center",gap:16,marginBottom:26}}>
        <div style={{width:64,height:64,borderRadius:"50%",background:"var(--accent-soft)",
          color:"var(--accent-hover)",display:"flex",alignItems:"center",justifyContent:"center",
          fontSize:22,fontWeight:700,flexShrink:0}}>{ini}</div>
        <div>
          <div style={{fontSize:21,fontWeight:600,color:"var(--text)"}}>{p.nombre||p.username}</div>
          <div style={{fontSize:13,color:"var(--accent-hover)"}}>{p.email||"(sin email)"}</div>
          <div style={{fontSize:12,color:"var(--text-muted)",marginTop:2}}>{rolLabel}</div>
        </div>
      </div>

      <div style={{display:"flex",gap:20,borderBottom:"1px solid var(--border)",marginBottom:22}}>
        {[["datos","Datos personales"],["permisos","Permisos"],["seguridad","Seguridad"]].map(([k,l])=>(
          <span key={k} onClick={()=>setTab(k)} style={{fontSize:13.5,cursor:"pointer",fontWeight:600,
            paddingBottom:9,color:tab===k?"var(--accent-hover)":"var(--text-muted)",
            borderBottom:tab===k?"2px solid var(--accent-hover)":"2px solid transparent"}}>{l}</span>
        ))}
      </div>

      {tab==="datos" && (
        <div style={{maxWidth:430}}>
          {msg && <div style={{fontSize:13,marginBottom:12,color:msg.includes("Error")?"#d03b3b":"var(--good, #7CF2C0)"}}>{msg}</div>}
          <div className="form-group" style={{marginBottom:14}}>
            <label className="form-label">Nombre</label>
            <input value={form.nombre} disabled={!editando}
              onChange={e=>setForm({...form,nombre:e.target.value})} style={{width:"100%"}}/>
          </div>
          <div className="form-group" style={{marginBottom:14}}>
            <label className="form-label">Correo electronico</label>
            <input value={form.email} disabled={!editando}
              onChange={e=>setForm({...form,email:e.target.value})} style={{width:"100%"}}/>
          </div>
          <div className="form-group" style={{marginBottom:14}}>
            <label className="form-label">Usuario</label>
            <input value={p.username} disabled style={{width:"100%"}}/>
          </div>
          <div className="form-group" style={{marginBottom:18}}>
            <label className="form-label">Rol</label>
            <div><span className="badge badge-blue"><i className="badge-dot"/>{rolLabel}</span>
              <span style={{fontSize:11.5,color:"var(--text-muted)",marginLeft:10}}>Solo un administrador puede cambiarlo</span></div>
          </div>
          {editando ? (
            <div style={{display:"flex",gap:8}}>
              <button className="btn btn-primary" onClick={guardar}>Guardar</button>
              <button className="btn" onClick={()=>{setEditando(false);setForm({nombre:p.nombre||"",email:p.email||""});setMsg("");}}>Cancelar</button>
            </div>
          ) : (
            <button className="btn" onClick={()=>{setEditando(true);setMsg("");}}>Editar</button>
          )}
        </div>
      )}

      {tab==="permisos" && (
        <div>
          <div style={{fontSize:13,color:"var(--text-muted)",marginBottom:14}}>
            Tu rol <b style={{color:"var(--accent-hover)"}}>{rolLabel}</b> habilita las siguientes acciones:
          </div>
          <div style={{display:"grid",gap:8,maxWidth:480}}>
            {(p.permisos||[]).map(x=>(
              <div key={x} style={{display:"flex",alignItems:"center",gap:10,padding:"9px 13px",
                background:"var(--surface-2)",border:"1px solid var(--border)",borderRadius:7,fontSize:13}}>
                <span style={{color:"var(--accent-hover)",fontWeight:700}}>&#10003;</span>
                <span style={{color:"var(--text-secondary)"}}>{x}</span>
              </div>
            ))}
          </div>
        </div>
      )}

      {tab==="seguridad" && (
        <div>
          <div style={{maxWidth:430,marginBottom:28}}>
            <div style={{fontSize:14,fontWeight:600,color:"var(--text)",marginBottom:12}}>Cambiar contrasena</div>
            {passMsg2 && <div style={{fontSize:13,marginBottom:10,color:passMsg2.includes("Error")||passMsg2.includes("no coinciden")||passMsg2.includes("Minimo")||passMsg2.includes("Completa")?"#d03b3b":"var(--good, #7CF2C0)"}}>{passMsg2}</div>}
            {[["actual","Contrasena actual"],["nuevo","Nueva contrasena"],["confirmar","Confirmar nueva"]].map(([k,l])=>(
              <div key={k} className="form-group" style={{marginBottom:11}}>
                <label className="form-label">{l}</label>
                <input type="password" value={pass[k]} onChange={e=>setPass({...pass,[k]:e.target.value})} style={{width:"100%"}}/>
              </div>
            ))}
            <button className="btn btn-primary" onClick={cambiarPass}>Cambiar contrasena</button>
          </div>

          <div>
            <div style={{fontSize:14,fontWeight:600,color:"var(--text)",marginBottom:12}}>Actividad reciente</div>
            {(p.actividad||[]).length===0 && <div style={{fontSize:13,color:"var(--text-muted)"}}>Sin actividad registrada.</div>}
            <div className="table-wrap" style={{maxWidth:620}}>
              <table><thead><tr><th>Fecha</th><th>Accion</th><th>Entidad</th><th>IP</th></tr></thead>
              <tbody>
                {(p.actividad||[]).map((a,i)=>(
                  <tr key={i}>
                    <td className="td-muted" style={{whiteSpace:"nowrap"}}>{a.fecha}</td>
                    <td>{a.accion}</td>
                    <td className="td-muted">{a.entidad}</td>
                    <td className="td-muted">{a.ip}</td>
                  </tr>
                ))}
              </tbody></table>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
