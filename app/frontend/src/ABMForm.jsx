import { useState, useMemo } from "react";

export const OFICINAS = ["CABA 1","CABA 2","Tigre","Corrientes","Rosario","Córdoba","Mendoza","Neuquén"];

export const OFICINA_TO_SEDE = {
  "CABA 1":"CABA1", "CABA 2":"CABA2", "Tigre":"Tigre", "Corrientes":"Corrientes",
  "Rosario":"Rosario", "Córdoba":"Cordoba", "Mendoza":"Mendoza", "Neuquén":"Neuquen"
};
export const SEDE_TO_OFICINA = {
  "CABA1":"CABA 1", "CABA2":"CABA 2", "Resguarda":"CABA 2", "Tigre":"Tigre",
  "Corrientes":"Corrientes", "Rosario":"Rosario", "Cordoba":"Córdoba",
  "Mendoza":"Mendoza", "Neuquen":"Neuquén"
};

const COST_CENTERS = {
  "CABA 1": ["CABA 1-ACTUARIO","CABA 1-AEF","CABA 1-AEF AE","CABA 1-AEF AI","CABA 1-AEF SYS","CABA 1-AUD EA","CABA 1-AUD PL","CABA 1-AUD XM","CABA 1-C.TRANSF DIG","CABA 1-COMPLIANCE","CABA 1-DPT","CABA 1-EF AUD-AE","CABA 1-EF AUD-AI","CABA 1-EF CONS-PLA","CABA 1-EF CONS-PROV","CABA 1-ENERGIA","CABA 1-IMP FLC","CABA 1-IMP GH","CABA 1-IMP GR","CABA 1-IMP INT","CABA 1-IMP LM","CABA 1-IMP MM","CABA 1-IMP RS","CABA 1-IMP SF","CABA 1-IMP VRS","CABA 1-LEGALES","CABA 1-LEGALES.A","CABA 1-LEGALES.B","CABA 1-LEGALES.C","CABA 1-LEGALES.D","CABA 1-NA AUD","CABA 1-NA IMP","CABA 1-PY ET","CABA 1-PY GO","CABA 1-PY IMP","CABA 1-PY NL","CABA 1-PY NN","CABA 1-SOCIEDADES","CABA 1-SOLINF","CABA 1-TD CORPO"],
  "CABA 2": ["CABA 2-CONSUL","CABA 2-RESGUARDA"],
  "Córdoba": ["CORDOBA-AUD CBA","CORDOBA-IMP AU","CORDOBA-IMP DR","CORDOBA-NA CORDOBA"],
  "Corrientes": ["CORRIENTES-AUD CM","CORRIENTES-IMP DE.L","CORRIENTES-LEGALES","CORRIENTES-NA CTES","CORRIENTES-PYMES"],
  "Mendoza": ["MENDOZA-AUD MDZA","MENDOZA-EF AUD-AE","MENDOZA-NICASTRO","MENDOZA-NICASTROPY"],
  "Rosario": ["ROSARIO-AGRO","ROSARIO-AUD ED","ROSARIO-AUD LZ","ROSARIO-AUD MP","ROSARIO-IMP FR","ROSARIO-IMP HA","ROSARIO-LEGALES","ROSARIO-NA ROSARIO"],
  "Tigre": ["TIGRE-AUD TIGRE","TIGRE-DAC","TIGRE-IMP EJ","TIGRE-IMP JMA","TIGRE-IMP PL","TIGRE-NA TIGRE","TIGRE-PT"],
  "Neuquén": [],
  "General": ["GENERAL-ADM","GENERAL-FIN-D.ORG","GENERAL-GTH ADM","GENERAL-I+D","GENERAL-MKT","GENERAL-SISTEMAS","SOCIOS-SOCIOS"]
};

const PUESTO_GROUPS = [
  ["Junior / Senior", ["Pasante","Junior B","Junior A","Semi Senior","Senior D","Senior C","Senior B","Senior A"]],
  ["Liderazgo", ["Supervisor","Gerente","Gerente Senior","Director","Socio A","Socio B"]],
  ["Consultoría / Especialistas", ["Consultor","Especialista I","Especialista II"]],
  ["Analistas", ["Analista Supervisor","Analista Sr","Analista Semi Sr"]],
  ["Asistentes / Ingreso", ["Asistente Exp","Asistente Inicial","Senior Inicial","Senior Avanzado"]],
  ["Abogacía", ["Abogado Semi Sr","Abogado Sr"]]
];

const SECTORES = ["Administración","Auditoría Externa","Auditoría Financiera","Auditoría Financiera > Servicios Actuariales","Centro de Transformación Digital","Comercial","Compliance","Consultoría","Derecho Aduanero y Cambiario","Energía","Gestión del Talento Humano","Impuestos","Innovación y Desarrollo","Legales","Marketing","Precios y Transferencias","PYMES","Resguarda","Sistemas","Sociedades","Socios","Soluciones Informáticas"];

const ACTIVOS_CHECKLIST = ["Notebook","Cargador","Auriculares","Mouse","Teclado","Monitor","Mochila"];

function splitNombre(nombreCompleto){
  const partes = (nombreCompleto||"").split(",");
  const apellidos = (partes[0]||"").trim();
  const nombres = (partes.slice(1).join(",")||"").trim();
  return { nombres, apellidos };
}

function withFallback(options, valorActual){
  if(!valorActual) return options;
  const yaEsta = options.some(o => o.toLowerCase() === valorActual.toLowerCase());
  if(yaEsta) return options;
  return [valorActual, ...options];
}

// Los datos de la nomina estan cargados de forma inconsistente: para algunos empleados el
// codigo de Centro de Costos (ej "CABA 1-LEGALES") esta en la columna subauxiliar, para otros
// en centro_costo. Detectamos por el FORMATO del valor (arranca con nombre de oficina + guion)
// en vez de confiar en la columna, para mostrar cada dato en el campo correcto sin importar
// donde este cargado.
export function pareceCentroCosto(v){
  if(!v) return false;
  return /^[A-Za-zÁÉÍÓÚÑáéíóúñ.]+(\s?\d)?\s*-/.test(v.trim());
}
export function clasificarSectorCentro(subauxiliar, centro_costo){
  const a = (subauxiliar||"").trim();
  const b = (centro_costo||"").trim();
  const aEsCentro = pareceCentroCosto(a);
  const bEsCentro = pareceCentroCosto(b);
  if(aEsCentro && !bEsCentro) return { sector: b, centroCostos: a };
  if(bEsCentro && !aEsCentro) return { sector: a, centroCostos: b };
  return { sector: a, centroCostos: b };
}

function RadioGroup({ value, onChange, options }){
  return (
    <div className="abm-radio-group">
      {options.map(op=>(
        <div key={op} className={"abm-radio-opt"+(value===op?" sel":"")} onClick={()=>onChange(op)}>{op}</div>
      ))}
    </div>
  );
}

export default function ABMForm({ tipoInicial, empleado, empleados, hardware, licencias, onClose, onSubmit }){
  const inicial = splitNombre(empleado?.nombre);
  const [tipoAbm, setTipoAbm] = useState(tipoInicial || "Alta");
  const [legajo, setLegajo] = useState(empleado?.legajo ? String(empleado.legajo) : "");
  const [fechaEjecucion, setFechaEjecucion] = useState("");
  const [solicitante, setSolicitante] = useState("");
  const [backup, setBackup] = useState("");
  const [detalleBackup, setDetalleBackup] = useState("");
  const [correoMantiene, setCorreoMantiene] = useState("");
  const [buzon90, setBuzon90] = useState("");
  const [activosEntrega, setActivosEntrega] = useState([]);
  const [aprobacionModif, setAprobacionModif] = useState("");
  const [mantieneAcceso, setMantieneAcceso] = useState("");
  const [accesosNuevos, setAccesosNuevos] = useState("");
  const [nombres, setNombres] = useState(inicial.nombres);
  const [apellidos, setApellidos] = useState(inicial.apellidos);
  const [manager, setManager] = useState("");
  const [oficina, setOficina] = useState(SEDE_TO_OFICINA[empleado?.sede] || "");
  const [puesto, setPuesto] = useState(empleado?.categoria || "");
  const clasifSectorCentro = clasificarSectorCentro(empleado?.subauxiliar, empleado?.centro_costo);
  const [sector, setSector] = useState(clasifSectorCentro.sector || "");
  const [centroCostos, setCentroCostos] = useState(clasifSectorCentro.centroCostos || "");
  const [rutaFileServer, setRutaFileServer] = useState("");
  const [rutaSharepoint, setRutaSharepoint] = useState("");
  const [sistemasApps, setSistemasApps] = useState("");
  const [caracEspeciales, setCaracEspeciales] = useState("");
  const [leido, setLeido] = useState(false);
  const [enviando, setEnviando] = useState(false);

  const centrosDisponibles = useMemo(()=>{
    if(!oficina) return [];
    return withFallback(COST_CENTERS[oficina] || [], oficina===SEDE_TO_OFICINA[empleado?.sede] ? clasifSectorCentro.centroCostos : "");
  // eslint-disable-next-line react-hooks/exhaustive-deps -- valores iniciales del formulario: se calculan una vez al abrirlo
  }, [oficina]);

  const puestoOptions = useMemo(()=>{
    const flat = PUESTO_GROUPS.flatMap(([,opts])=>opts);
    if(empleado?.categoria && !flat.some(o=>o.toLowerCase()===empleado.categoria.toLowerCase())){
      return [["Actual", [empleado.categoria]], ...PUESTO_GROUPS];
    }
    return PUESTO_GROUPS;
  // eslint-disable-next-line react-hooks/exhaustive-deps -- valores iniciales del formulario: se calculan una vez al abrirlo
  }, []);

  // eslint-disable-next-line react-hooks/exhaustive-deps -- valores iniciales del formulario: se calculan una vez al abrirlo
  const sectorOptions = useMemo(()=> withFallback(SECTORES, clasifSectorCentro.sector), []);

  function toggleActivo(a){
    setActivosEntrega(list => list.includes(a) ? list.filter(x=>x!==a) : [...list, a]);
  }

  async function handleSubmit(){
    if(!leido){ alert('Tenés que tildar "Leído" en el aviso importante antes de generar el resumen.'); return; }
    if(!legajo || !fechaEjecucion || !solicitante || !nombres || !apellidos || !manager || !oficina || !puesto || !sector || !centroCostos){
      alert("Completá todos los campos obligatorios (*).");
      return;
    }
    const formData = {
      tipoAbm, legajo, fechaEjecucion, solicitante,
      backup, detalleBackup, correoMantiene, buzon90, activosEntrega,
      aprobacionModif, mantieneAcceso, accesosNuevos,
      nombres, apellidos, manager, oficina, puesto, sector, centroCostos,
      rutaFileServer, rutaSharepoint, sistemasApps, caracEspeciales
    };
    setEnviando(true);
    try{
      await onSubmit(tipoAbm, formData);
    } catch(e){
      alert("Error al procesar el ABM: " + e.message);
    }
    setEnviando(false);
  }

  const labelFecha = tipoAbm === "Alta" ? "Fecha de ingreso" : "Fecha de ejecución";
  const labelManager = tipoAbm === "Alta" ? "Responsable / Tutor del ingresante" : "Manager (de quién depende)";
  const tieneEquipos = (hardware && hardware.length > 0) || (licencias && licencias.length > 0);

  return (
    <div className="abm-overlay" onClick={onClose}>
      <div className="abm-modal" onClick={e=>e.stopPropagation()}>
        <div className="abm-hero">
          <button className="abm-close" onClick={onClose}>✕</button>
          <h1>Formulario ABM</h1>
          <p>Alta, Baja o Modificación de usuarios. Completá todos los campos obligatorios (*). El tiempo de preparación de 1 a 10 equipos es de 4 días hábiles, sin excepción.</p>
        </div>

        <div className="abm-body">

          {tipoAbm !== "Alta" && tieneEquipos && (
            <div className="abm-card">
              <div className="abm-section-title">Equipos y licencias asignados actualmente</div>
              <div className="abm-card-body" style={{display:"flex",gap:24,flexWrap:"wrap"}}>
                <div style={{flex:1,minWidth:200}}>
                  <div style={{fontSize:12,fontWeight:700,color:"#0B4F6C",marginBottom:6}}>Equipos</div>
                  {(!hardware || hardware.length===0) ? <div style={{fontSize:12,color:"#888"}}>Sin equipos</div> :
                    hardware.map(h=><div key={h.id} style={{fontSize:13,color:"#333",marginBottom:2}}>• {h.descripcion||h.tipo}</div>)}
                </div>
                <div style={{flex:1,minWidth:200}}>
                  <div style={{fontSize:12,fontWeight:700,color:"#0B4F6C",marginBottom:6}}>Licencias</div>
                  {(!licencias || licencias.length===0) ? <div style={{fontSize:12,color:"#888"}}>Sin licencias</div> :
                    licencias.map((l,i)=><div key={i} style={{fontSize:13,color:"#333",marginBottom:2}}>• {l.licencia_nombre||l.nombre||l.detalle||"Licencia"}</div>)}
                </div>
              </div>
            </div>
          )}

          <div className="abm-card">
            <div className="abm-section-title">Datos de ABM</div>
            <div className="abm-card-body">
              <div className="abm-field">
                <label>Tipo de ABM <span className="req">*</span></label>
                <RadioGroup value={tipoAbm} onChange={setTipoAbm} options={["Alta","Baja","Modificación"]} />
              </div>
              <div className="abm-row2">
                <div className="abm-field">
                  <label title="Indicar legajo de Portal GO">N° de Legajo <span className="req">*</span></label>
                  <input value={legajo} onChange={e=>setLegajo(e.target.value)} />
                </div>
                <div className="abm-field">
                  <label>{labelFecha} <span className="req">*</span></label>
                  <input type="date" value={fechaEjecucion} onChange={e=>setFechaEjecucion(e.target.value)} />
                </div>
              </div>
              <div className="abm-field">
                <label title="Indicar el creador del ABM">Solicitante de ABM <span className="req">*</span></label>
                <input value={solicitante} onChange={e=>setSolicitante(e.target.value)} />
              </div>

              {tipoAbm === "Baja" && (
                <div className="abm-conditional">
                  <div className="abm-field">
                    <label>¿Requiere backup de la información? <span className="req">*</span></label>
                    <RadioGroup value={backup} onChange={setBackup} options={["Sí","No"]} />
                  </div>
                  {backup === "Sí" && (
                    <div className="abm-field">
                      <label>Detalle del backup requerido</label>
                      <div className="abm-hint">Indicar carpetas, correo, OneDrive u otro contenido a resguardar antes de dar de baja el acceso.</div>
                      <textarea value={detalleBackup} onChange={e=>setDetalleBackup(e.target.value)} />
                    </div>
                  )}
                  <div className="abm-field">
                    <label>¿El correo electrónico se mantiene? <span className="req">*</span></label>
                    <RadioGroup value={correoMantiene} onChange={setCorreoMantiene} options={["Sí","No"]} />
                  </div>
                  <div className="abm-field">
                    <label>¿Requiere buzón por 90 días? <span className="req">*</span></label>
                    <RadioGroup value={buzon90} onChange={setBuzon90} options={["Sí","No"]} />
                  </div>
                  <div className="abm-field">
                    <label>Activos a entregar</label>
                    <div className="abm-hint">Equipos que el usuario debe devolver al darse de baja.</div>
                    <div className="abm-checklist">
                      {ACTIVOS_CHECKLIST.map(a=>(
                        <label key={a}>
                          <input type="checkbox" checked={activosEntrega.includes(a)} onChange={()=>toggleActivo(a)} />{a}
                        </label>
                      ))}
                    </div>
                  </div>
                </div>
              )}

              {tipoAbm === "Modificación" && (
                <div className="abm-conditional">
                  <div className="abm-field">
                    <label>Aprobación</label>
                    <div className="abm-hint">Quién aprueba la modificación (nombre / cargo).</div>
                    <input value={aprobacionModif} onChange={e=>setAprobacionModif(e.target.value)} />
                  </div>
                  <div className="abm-field">
                    <label>¿Mantiene acceso? ¿Por cuánto tiempo?</label>
                    <input value={mantieneAcceso} onChange={e=>setMantieneAcceso(e.target.value)} placeholder="Ej: Sí, por 30 días / No" />
                  </div>
                  <div className="abm-field">
                    <label>¿Accesos nuevos? ¿Qué carpetas?</label>
                    <textarea value={accesosNuevos} onChange={e=>setAccesosNuevos(e.target.value)} placeholder="Detallar rutas de file server y/o carpetas de SharePoint" />
                  </div>
                </div>
              )}
            </div>
          </div>

          <div className="abm-card">
            <div className="abm-section-title">Usuario</div>
            <div className="abm-card-body">
              <div className="abm-row2">
                <div className="abm-field">
                  <label>Nombres <span className="req">*</span></label>
                  <div className="abm-hint">Primer y Segundo Nombre</div>
                  <input value={nombres} onChange={e=>setNombres(e.target.value)} />
                </div>
                <div className="abm-field">
                  <label>Apellidos <span className="req">*</span></label>
                  <div className="abm-hint">Primer y Segundo Apellido</div>
                  <input value={apellidos} onChange={e=>setApellidos(e.target.value)} />
                </div>
              </div>
            </div>
          </div>

          <div className="abm-card">
            <div className="abm-section-title">Características del Usuario</div>
            <div className="abm-card-body">
              <div className="abm-field">
                <label>{labelManager} <span className="req">*</span></label>
                <input list="abmEmpleadosNomina" value={manager} onChange={e=>setManager(e.target.value)} placeholder="Empezá a escribir para buscar..." autoComplete="off" />
              </div>
              <div className="abm-row2">
                <div className="abm-field">
                  <label>Oficina <span className="req">*</span></label>
                  <select value={oficina} onChange={e=>{ setOficina(e.target.value); setCentroCostos(""); }}>
                    <option value="">-----</option>
                    {OFICINAS.map(o=><option key={o}>{o}</option>)}
                  </select>
                </div>
                <div className="abm-field">
                  <label>Puesto / Categoría <span className="req">*</span></label>
                  <select value={puesto} onChange={e=>setPuesto(e.target.value)}>
                    <option value="">-----</option>
                    {puestoOptions.map(([grp, opts])=>(
                      <optgroup label={grp} key={grp}>{opts.map(o=><option key={o}>{o}</option>)}</optgroup>
                    ))}
                  </select>
                </div>
              </div>
              {tipoAbm !== "Baja" && (
                <div className="abm-field">
                  <label>Especificar accesos</label>
                  <div className="abm-hint">Detallar rutas de red, carpetas compartidas, sistemas o permisos específicos que necesita el usuario.</div>
                  <input placeholder="Ruta de file server" value={rutaFileServer} onChange={e=>setRutaFileServer(e.target.value)} style={{marginBottom:10}} />
                  <input placeholder="Ruta / carpeta raíz de SharePoint" value={rutaSharepoint} onChange={e=>setRutaSharepoint(e.target.value)} style={{marginBottom:10}} />
                  <input placeholder="Sistemas o aplicaciones — ej: Tango, Lex-Doctor, IDEA" value={sistemasApps} onChange={e=>setSistemasApps(e.target.value)} />
                </div>
              )}
            </div>
          </div>

          <div className="abm-card">
            <div className="abm-section-title">Sector y Centro de Costos</div>
            <div className="abm-card-body">
              <div className="abm-row2">
                <div className="abm-field">
                  <label>Sector / Departamento <span className="req">*</span></label>
                  <select value={sector} onChange={e=>setSector(e.target.value)}>
                    <option value="">-----</option>
                    {sectorOptions.map(s=><option key={s}>{s}</option>)}
                  </select>
                </div>
                <div className="abm-field">
                  <label>Centro de Costos <span className="req">*</span></label>
                  <div className="abm-hint">Se filtra automáticamente según la Oficina seleccionada.</div>
                  <select value={centroCostos} onChange={e=>setCentroCostos(e.target.value)} disabled={!oficina}>
                    {!oficina && <option value="">Elegí primero la Oficina...</option>}
                    {oficina && <option value="">-----</option>}
                    {oficina && centrosDisponibles.length > 0 && (
                      <optgroup label={oficina}>{centrosDisponibles.map(cc=><option key={cc}>{cc}</option>)}</optgroup>
                    )}
                    {oficina && (
                      <optgroup label="General / Socios">{COST_CENTERS["General"].map(cc=><option key={cc}>{cc}</option>)}</optgroup>
                    )}
                  </select>
                </div>
              </div>
            </div>
          </div>

          <div className="abm-card">
            <div className="abm-section-title">Observaciones</div>
            <div className="abm-card-body">
              <div className="abm-field">
                <label>Características Especiales</label>
                <textarea value={caracEspeciales} onChange={e=>setCaracEspeciales(e.target.value)} />
              </div>
            </div>
          </div>

          <div className="abm-card">
            <div className="abm-card-body">
              <div className="abm-alert">
                <span>⚠️</span>
                <span><strong>IMPORTANTE, leer:</strong> El tiempo de preparación de 1 a 10 equipos por parte de Soporte Técnico es de 4 días hábiles, sin excepción. Si el ABM es generado luego de las 14hs, no se cuenta como día hábil. Al aceptar la solicitud del ABM confirma estar de acuerdo con el tiempo establecido por Soporte Técnico y que todos los datos ingresados son correctos.</span>
              </div>
              <div className="abm-agree">
                <input type="checkbox" id="abmLeido" checked={leido} onChange={e=>setLeido(e.target.checked)} />
                <label htmlFor="abmLeido">Leído</label>
              </div>
            </div>
          </div>

        </div>

        <div className="abm-footer">
          <button className="abm-submit" disabled={enviando} onClick={handleSubmit}>
            {enviando ? "Procesando..." : "Generar resumen para el ticket"}
          </button>
        </div>

        <datalist id="abmEmpleadosNomina">
          {(empleados||[]).map(e=><option value={e.nombre} key={e.id} />)}
        </datalist>
      </div>
    </div>
  );
}