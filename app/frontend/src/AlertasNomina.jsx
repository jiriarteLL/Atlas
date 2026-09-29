// AlertasNomina.jsx — Tarjeta del Dashboard con inconsistencias entre la nomina y lo asignado.
// Solo lee datos: no modifica nada. Si no hay alertas, la tarjeta no se muestra.
// Tocar un item abre la ficha del empleado o del activo.
import { useState, useEffect } from "react";

const prefijoEmail = e => e?.split("@")[0]?.toLowerCase().trim() || "";

export default function AlertasNomina({ empleados, assets, cargarEquiposClaude, abrirEmpleado, abrirActivo }) {
  const [equiposClaude, setEquiposClaude] = useState([]);
  const [abierta, setAbierta] = useState(null);
  // eslint-disable-next-line react-hooks/exhaustive-deps -- se carga una sola vez al mostrar el Dashboard
  useEffect(() => { cargarEquiposClaude().then(d => setEquiposClaude(Array.isArray(d) ? d : [])).catch(() => {}); }, []);

  const inactivos = empleados.filter(e => e.estado && e.estado !== "Activo");

  // Empleados dados de baja (o marcados Inactivo a mano) que conservan licencias activas
  const conLicencias = inactivos.filter(e => (e.licencias || []).length > 0)
    .map(e => ({ emp: e, detalle: e.licencias.join(", ") }));

  // Empleados inactivos que siguen figurando como usuario de un equipo del Inventario
  const equiposPorUsuario = {};
  assets.filter(a => a.estado !== "Dado de baja").forEach(a => {
    const u = (a.usuario || "").toLowerCase().trim();
    if (u) (equiposPorUsuario[u] = equiposPorUsuario[u] || []).push(a);
  });
  const conEquipo = inactivos
    .map(e => ({ emp: e, equipos: equiposPorUsuario[prefijoEmail(e.email)] || [] }))
    .filter(x => prefijoEmail(x.emp.email) && x.equipos.length > 0)
    .map(x => ({ emp: x.emp, detalle: x.equipos.map(a => (a.nombre || a.modelo || a.tipo) + (a.serial ? " (" + a.serial + ")" : "")).join(", ") }));

  // Notebooks/CPU a nombre de un usuario que no esta en la nomina (en general, gente que ya no esta)
  const enNomina = new Set(empleados.map(e => prefijoEmail(e.email)).filter(Boolean));
  const fueraDeNomina = assets
    .filter(a => ["Notebook","CPU"].includes(a.tipo) && a.estado !== "Dado de baja")
    .filter(a => { const u = (a.usuario || "").toLowerCase().trim(); return u && !enNomina.has(u); })
    .map(a => ({ activo: a, nombre: a.usuario, detalle: (a.nombre || a.modelo || a.tipo) + (a.serial ? " (" + a.serial + ")" : "") }));

  // Empleados activos que no figuran como usuario de ningun equipo
  const usuariosConEquipo = new Set(assets.map(a => (a.usuario || "").toLowerCase().trim()).filter(Boolean));
  const sinEquipo = empleados
    .filter(e => e.estado === "Activo" && prefijoEmail(e.email) && !usuariosConEquipo.has(prefijoEmail(e.email)))
    .map(e => ({ emp: e, detalle: [e.categoria, e.sede].filter(Boolean).join(" · ") }));

  // Cuentas Claude de equipo libres o sin correo cargado
  const claudePendientes = equiposClaude
    .filter(q => { const s = (q.estado || "").toLowerCase(); return s.includes("libre") || s.includes("falta") || !s; })
    .map(q => ({ nombre: q.unidad || "Cuenta #" + q.numero, detalle: [q.estado || "Sin estado", q.tipo, q.email].filter(Boolean).join(" · ") }));

  const alertas = [
    { k: "lic", titulo: "Inactivos con licencias activas", items: conLicencias, clase: "trend-danger" },
    { k: "eq", titulo: "Inactivos con equipo asignado", items: conEquipo, clase: "trend-warn" },
    { k: "fn", titulo: "Equipos a nombre de usuarios fuera de la nómina", items: fueraDeNomina, clase: "trend-warn" },
    { k: "cl", titulo: "Cuentas Claude de equipo libres o sin correo", items: claudePendientes, clase: "trend-warn" },
    { k: "se", titulo: "Empleados activos sin equipo asignado", items: sinEquipo, clase: "badge-gray" },
  ].filter(a => a.items.length > 0);

  if (alertas.length === 0) return null;

  return (
    <div className="card">
      <div className="card-head"><div className="card-title">Alertas de nómina</div></div>
      <div className="card-body" style={{paddingTop:6}}>
        {alertas.map(a => (
          <div key={a.k} style={{borderBottom:"1px solid var(--border)",padding:"8px 0"}}>
            <div onClick={() => setAbierta(abierta === a.k ? null : a.k)} style={{display:"flex",alignItems:"center",gap:10,cursor:"pointer",userSelect:"none"}}>
              <span className={a.clase} style={{fontSize:20,fontWeight:800,minWidth:34,fontVariantNumeric:"tabular-nums"}}>{a.items.length}</span>
              <span style={{fontSize:13,color:"var(--text)",fontWeight:600}}>{a.titulo}</span>
              <span style={{marginLeft:"auto",fontSize:12,color:"var(--text-muted)"}}>{abierta === a.k ? "Ocultar" : "Ver"}</span>
            </div>
            {abierta === a.k && (
              <div style={{marginTop:8,display:"flex",flexDirection:"column",gap:4}}>
                {a.items.map((it, i) => (
                  <div key={i} className="field" style={{cursor:(it.emp||it.activo)?"pointer":"default"}}
                    onClick={() => { if(it.emp) abrirEmpleado(it.emp); else if(it.activo) abrirActivo(it.activo); }}>
                    <span className="field-label" style={{color:(it.emp||it.activo)?"var(--accent-hover)":"var(--text)",fontWeight:600}}>{it.emp ? it.emp.nombre : it.nombre}</span>
                    <span className="field-value" style={{fontSize:12,color:"var(--text-muted)"}}>{it.detalle}</span>
                  </div>
                ))}
              </div>
            )}
          </div>
        ))}
      </div>
    </div>
  );
}
