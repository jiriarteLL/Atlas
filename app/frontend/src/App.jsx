// App.jsx — Esqueleto de la app con el diseño v2: menu lateral, encabezado y vistas.
// Ruteo por hash (#seccion?tipo=..&sede=..&estado=..) para que atras/adelante y los links funcionen.
import { Fragment, useCallback, useEffect, useMemo, useRef, useState } from "react";
import { useAuth, puede } from "./AuthContext";
import { API, apiFetch, http, setUsuarioActual } from "./api";
import { useToast, Proximamente } from "./diseno/comunes";
import Ambientacion, { SelectorTema } from "./diseno/Ambientacion";
import { recordarTotal } from "./diseno/Intro";
import { exportarActivosExcel, exportarCSV, exportarReporte, leerCSV } from "./exportar";
import { cumpleEstado } from "./vistas/filtros";
import Dashboard from "./vistas/Dashboard";
import Activos from "./vistas/Activos";
import Impresoras from "./vistas/Impresoras";
import Salud from "./vistas/Salud";
import Telefonia from "./vistas/Telefonia";
import Monitores from "./vistas/Monitores";
import AlertaToner from "./vistas/AlertaToner";
import FichaActivo from "./vistas/FichaActivo";
import ModalActivo from "./vistas/ModalActivo";
import Reportes from "./vistas/Reportes";
import Accesos from "./vistas/Accesos";
import Agente from "./vistas/Agente";
import Actas from "./vistas/Actas";
import Auditoria from "./vistas/Auditoria";
import { HojaEtiquetas } from "./secciones/Etiquetas";
import { SeccionTendencias } from "./secciones/SeccionTendencias";
import { SeccionProyectos } from "./secciones/SeccionProyectos";
import { SeccionPerfil } from "./secciones/SeccionPerfil";

const SECCIONES = {
  dashboard: ["Dashboard", "Vista general"], activos: ["Activos", "Inventario completo"],
  telefonia: ["Telefonía", "Internos de 3CX y teléfonos"], licencias: ["Licencias", "Software y suscripciones"], proyectos: ["Proyectos", "Seguimiento de IT"],
  reportes: ["Reportes", "Análisis"], tendencias: ["Tendencias", "Evolución en el tiempo"],
  usuarios: ["Usuarios", "Nómina"], perfil: ["Mi perfil", "Cuenta, permisos y seguridad"],
  agente: ["Agente", "Scripts de sincronización"], accesos: ["Accesos", "Usuarios de la aplicación"],
  actas: ["Actas", "Entrega, devolución y préstamo de equipos"], auditoria: ["Auditoría física", "Relevamiento por sede con el celular"],
};
const FILTROS_VACIOS = { q: "", tipo: "", estado: "", sede: "" };
// Subsecciones de Activos (pestañas). Para sumar otro tipo con vista propia, agregarlo aca y en el render.
const VISTAS_ACTIVOS = [["todos", "Todos los activos"], ["salud", "Notebooks y PC"], ["monitores", "Monitores"], ["impresoras", "Impresoras"]];
// Modulo de permisos que habilita cada seccion y subseccion (ver backend/auth.py MODULOS). Sin entrada = siempre.
const MODULO_DE_VISTA = { todos: "activos", salud: "salud", monitores: "activos", impresoras: "impresoras" };
const MODULO_DE_SECCION = { dashboard: "dashboard", telefonia: "telefonia", proyectos: "proyectos", reportes: "reportes", tendencias: "tendencias",
  agente: "agente", accesos: "accesos", actas: "activos", auditoria: "auditoria" };
// Para cargar /api/assets alcanza con ver alguno de estos (igual que MODULOS_LISTA_ACTIVOS del servidor)
const MODULOS_LISTA_ACTIVOS = ["activos", "dashboard", "salud", "reportes", "proyectos"];
const vistaValida = (v) => (VISTAS_ACTIVOS.some(([k]) => k === v) ? v : "todos");

function leerHash() {
  const [sec, query] = (window.location.hash || "").replace("#", "").split("?");
  const p = new URLSearchParams(query || "");
  return { tab: SECCIONES[sec] ? sec : "dashboard", vista: vistaValida(p.get("vista")), activo: p.get("activo") || "",
    filtros: { ...FILTROS_VACIOS, tipo: p.get("tipo") || "", sede: p.get("sede") || "", estado: p.get("estado") || "" } };
}

export default function App() {
  const { user, logout } = useAuth();
  const esAdmin = puede(user, "accesos", "administrar");
  const puedeEditar = puede(user, "activos", "editar");
  const puedeEliminar = puede(user, "activos_eliminar", "si");
  const puedeVer = useCallback((m) => puede(user, m), [user]);
  const vistasActivos = VISTAS_ACTIVOS.filter(([k]) => puedeVer(MODULO_DE_VISTA[k]));
  const veAssets = MODULOS_LISTA_ACTIVOS.some(puedeVer);
  // sec + vista (solo Activos; sin vista = cualquiera de sus subsecciones)
  const permitida = useCallback((sec, v) => {
    if (sec === "activos") return v ? puedeVer(MODULO_DE_VISTA[v]) : VISTAS_ACTIVOS.some(([k]) => puedeVer(MODULO_DE_VISTA[k]));
    return !MODULO_DE_SECCION[sec] || puede(user, MODULO_DE_SECCION[sec], sec === "accesos" ? "administrar" : "ver");
  }, [user, puedeVer]);
  const [Toast, avisar] = useToast();

  const [tab, setTab] = useState(() => leerHash().tab);
  const [vista, setVista] = useState(() => leerHash().vista);
  const [filtros, setFiltros] = useState(() => leerHash().filtros);
  const [orden, setOrden] = useState({ col: null, asc: true });
  const [assets, setAssets] = useState([]);
  const [cargando, setCargando] = useState(true);
  const [glpiMap, setGlpiMap] = useState({});
  const [ficha, setFicha] = useState(null);
  const [edicion, setEdicion] = useState(null);      // activo a editar, o {} para alta
  const [etiquetas, setEtiquetas] = useState(null);  // lista de activos para la hoja de etiquetas QR
  const [actaAbrir, setActaAbrir] = useState("");     // acta a abrir desde un movimiento de la ficha
  const [activoHash, setActivoHash] = useState(() => leerHash().activo);   // #activos?activo=<id> (QR de la etiqueta)
  const [ambientacion, setAmbientacion] = useState(false);
  const [menu, setMenu] = useState(() => window.innerWidth > 760);
  const archivo = useRef(null);

  useEffect(() => { setUsuarioActual(user?.username); }, [user]);

  const cargar = useCallback(async () => {
    if (!veAssets) { setCargando(false); return; }   // ningun modulo usa la lista: no se pide (seria un 403)
    setCargando(true);
    try {
      const a = await http.get(`${API}/assets`);
      setAssets(a);
      recordarTotal(a.length);
    } catch (e) { console.error(e); }
    setCargando(false);
  }, [veAssets]);

  const cargarGlpi = useCallback(async () => {
    if (!veAssets) return;
    try {
      const r = await apiFetch(API + "/glpi/resumen");
      if (!r.ok) return;
      const lista = await r.json();
      const m = {};
      (Array.isArray(lista) ? lista : []).forEach((x) => { m[(x.serial || "").trim().toUpperCase()] = x; });
      setGlpiMap(m);
    } catch { /* GLPI no disponible: la ficha se muestra sin esos datos */ }
  }, [veAssets]);

  useEffect(() => { cargar(); cargarGlpi(); }, [cargar, cargarGlpi]);

  // El QR de una etiqueta abre la ficha: cuando llega la lista de activos se abre la del hash (una sola vez)
  useEffect(() => {
    if (!activoHash || !assets.length) return;
    const a = assets.find((x) => x.id === activoHash);
    setActivoHash("");
    if (a) { setFicha(a); apiFetch(API + "/assets/" + a.id + "/ficha").catch(() => {}); }
  }, [activoHash, assets]);

  // Hash -> estado (atras/adelante del navegador)
  useEffect(() => {
    const aplicar = () => { const h = leerHash(); setTab(h.tab); setVista(h.vista); setFiltros((f) => ({ ...h.filtros, q: h.tab === "activos" ? f.q : "" })); setFicha(null); if (h.activo) setActivoHash(h.activo); };
    window.addEventListener("popstate", aplicar);
    return () => window.removeEventListener("popstate", aplicar);
  }, []);
  // Estado -> hash
  useEffect(() => {
    let destino = tab;
    if (tab === "activos") {
      const p = new URLSearchParams();
      if (vista !== "todos") p.set("vista", vista);
      else ["tipo", "sede", "estado"].forEach((k) => { if (filtros[k]) p.set(k, filtros[k]); });
      if (p.toString()) destino += "?" + p.toString();
    }
    const actual = (window.location.hash || "").replace("#", "");
    if (actual === destino) return;
    if (!actual) window.history.replaceState(null, "", "#" + destino);
    else window.history.pushState(null, "", "#" + destino);
  }, [tab, vista, filtros]);

  // Sin useCallback: depende de los permisos del usuario (lo memoiza el compilador de React)
  const ir = (sec, f, v) => {
    // "Activos" sin vista abre la primera permitida; con vista, tiene que estar permitida esa
    if (!permitida(sec, sec === "activos" && v ? vistaValida(v) : undefined)) { avisar("No tenés acceso a ese módulo"); return; }
    setTab(sec);
    setFicha(null);
    if (sec === "activos") { setFiltros({ ...FILTROS_VACIOS, ...(f || {}) }); setVista(vistaValida(v)); }
    if (window.innerWidth <= 760) setMenu(false);
  };

  // Si el inicio (Dashboard) no esta permitido, se arranca en la primera seccion que si
  useEffect(() => {
    if (tab !== "dashboard" || permitida("dashboard")) return;
    const primera = ["activos", "telefonia", "proyectos", "reportes", "tendencias", "actas", "auditoria", "agente", "perfil"].find((x) => permitida(x));
    if (primera) setTab(primera);
  }, [tab, permitida]);

  const filtrados = useMemo(() => {
    const q = filtros.q.trim().toLowerCase();
    return assets.filter((a) =>
      (!q || [a.nombre, a.marca, a.modelo, a.serial, a.usuario, a.ubicacion].some((v) => (v || "").toLowerCase().includes(q))) &&
      (!filtros.tipo || a.tipo === filtros.tipo) &&
      (!filtros.sede || (a.ubicacion || "").toLowerCase() === filtros.sede.toLowerCase()) &&
      cumpleEstado(a, filtros.estado, glpiMap));
  }, [assets, filtros, glpiMap]);

  function verFicha(a) {
    setFicha(a);
    apiFetch(API + "/assets/" + a.id + "/ficha").catch(() => {});   // registra la consulta en auditoria
  }

  // Despues de un movimiento de ciclo de vida: lista y ficha con el estado / usuario / sede nuevos
  async function refrescarFicha() {
    try {
      const lista = await http.get(`${API}/assets`);
      setAssets(lista);
      setFicha((f) => (f ? lista.find((x) => x.id === f.id) || f : f));
    } catch { /* se ve al recargar */ }
  }

  async function guardarActivo(a) {
    if (a.id) await http.put(API + "/assets/" + a.id, a);
    else await http.post(API + "/assets", a);
    await cargar();
    setEdicion(null);
    if (a.id && ficha?.id === a.id) setFicha({ ...ficha, ...a });
    avisar(a.id ? "Activo actualizado" : "Activo creado");
  }

  async function eliminarActivo(a) {
    if (!confirm("¿Eliminar el activo " + (a.nombre || a.serial) + "?")) return;
    try { await http.del(API + "/assets/" + a.id); await cargar(); setFicha(null); avisar("Activo eliminado"); }
    catch (e) { alert("Error: " + e.message); }
  }

  async function consultarGarantia(a) {
    try {
      const r = await http.post(API + "/assets/" + a.id + "/garantia", {});
      if (r && r.garantia) {
        avisar("Garantía: " + r.garantia + " (" + r.estado + ")");
        await cargar();
        setFicha((f) => (f && f.id === a.id ? { ...f, garantia: r.garantia } : f));
      } else alert(r && r.detail ? r.detail : "No se pudo obtener la garantía.");
    } catch (e) { alert("Error: " + e.message); }
  }

  async function importar(e) {
    const f = e.target.files[0];
    e.target.value = "";
    if (!f) return;
    const filas = await leerCSV(f);
    let ok = 0;
    avisar("Importando " + filas.length + " activos…");
    for (const a of filas) { try { await http.post(`${API}/assets`, a); ok++; } catch { /* fila invalida: se saltea */ } }
    await cargar();
    avisar(ok + " de " + filas.length + " activos importados");
  }

  const exportarExcel = async (lista) => { try { await exportarActivosExcel(lista); } catch (e) { alert("Error al exportar: " + e.message); } };
  const exportarGrafico = async (t, d, id) => { try { await exportarReporte(t, d, id); } catch (e) { alert("Error al exportar: " + e.message); } };

  const principal = [
    ["dashboard", "▦", "Dashboard"], ["activos", "▭", "Activos", puedeVer("activos") ? assets.length : undefined], ["telefonia", "☏", "Telefonía"], ["licencias", "⬡", "Licencias"],
    ["proyectos", "◧", "Proyectos"], ["reportes", "◫", "Reportes"], ["tendencias", "◭", "Tendencias"],
    ["usuarios", "⚇", "Usuarios"], ["perfil", "◉", "Mi perfil"],
  ].filter(([k]) => permitida(k));
  const [titulo, sub] = SECCIONES[tab];
  // Vista de Activos efectiva: si la del hash no esta permitida, la primera que si
  const vistaEf = vistasActivos.some(([k]) => k === vista) ? vista : (vistasActivos[0] || [""])[0];
  const sinAcceso = tab === "activos" ? !vistaEf : !permitida(tab);

  return (
    <>
      {menu && window.innerWidth <= 760 && <div className="ll-velo" style={{ zIndex: 40 }} onClick={() => setMenu(false)} />}
      <aside className={"ll-sidebar" + (menu ? "" : " cerrada")} aria-label="Menú principal">
        <div className="ll-marca">
          <img className="ll-isotipo" src="/brand/isotipo.png" alt="LL&A" />
          <div style={{ lineHeight: 1.15 }}>
            <div style={{ fontSize: 16, fontWeight: 600, letterSpacing: -0.2 }}>Atlas</div>
            <div className="ll-marca-sub">ACTIVOS · TI</div>
          </div>
        </div>
        <nav className="ll-nav">
          <div className="ll-nav-sec">PRINCIPAL</div>
          <div className="ll-nav-lista">
            {principal.map(([k, ico, l, badge]) => (
              <Fragment key={k}>
                <a href={"#" + k} className={"ll-nav-item" + (tab === k ? " activo" : "")}
                  aria-current={tab === k && !(k === "activos") ? "page" : undefined}
                  onClick={(e) => { if (e.ctrlKey || e.metaKey || e.shiftKey || e.button === 1) return; e.preventDefault(); ir(k); }}>
                  <span className="ll-nav-ico">{ico}</span><span style={{ flex: 1 }}>{l}</span>
                  {badge !== undefined && <span className="ll-nav-badge">{badge}</span>}
                </a>
                {k === "activos" && <div className="ll-nav-sub" aria-label="Subsecciones de Activos">
                  {vistasActivos.map(([v, lv]) => {
                    const act = tab === "activos" && vistaEf === v;
                    return <a key={v} href={"#activos" + (v === "todos" ? "" : "?vista=" + v)}
                      className={"ll-nav-subitem" + (act ? " activo" : "")} aria-current={act ? "page" : undefined}
                      onClick={(e) => { if (e.ctrlKey || e.metaKey || e.shiftKey || e.button === 1) return; e.preventDefault(); ir("activos", {}, v); }}>
                      {lv}
                    </a>;
                  })}
                </div>}
              </Fragment>
            ))}
          </div>
          {(puedeVer("agente") || puede(user, "importar", "editar") || puedeVer("reportes") || puedeVer("activos") || puedeVer("auditoria") || esAdmin) &&
            <div className="ll-nav-sec" style={{ marginTop: 22 }}>HERRAMIENTAS</div>}
          <div className="ll-nav-lista">
            {puedeVer("activos") && <button className={"ll-nav-item" + (tab === "actas" ? " activo" : "")} onClick={() => { setActaAbrir(""); ir("actas"); }}><span className="ll-nav-ico">✎</span>Actas</button>}
            {puedeVer("auditoria") && <button className={"ll-nav-item" + (tab === "auditoria" ? " activo" : "")} onClick={() => ir("auditoria")}><span className="ll-nav-ico">⌖</span>Auditoría física</button>}
            {puedeVer("agente") && <button className={"ll-nav-item" + (tab === "agente" ? " activo" : "")} onClick={() => ir("agente")}><span className="ll-nav-ico">◈</span>Agente</button>}
            {puede(user, "importar", "editar") && <button className="ll-nav-item" onClick={() => archivo.current.click()}><span className="ll-nav-ico">⭱</span>Importar CSV</button>}
            {puedeVer("reportes") && <button className="ll-nav-item" onClick={() => { exportarCSV(assets); avisar("Exportando " + assets.length + " activos a CSV…"); }}><span className="ll-nav-ico">⭳</span>Exportar CSV</button>}
            {esAdmin && <button className={"ll-nav-item" + (tab === "accesos" ? " activo" : "")} onClick={() => ir("accesos")}><span className="ll-nav-ico">◇</span>Accesos</button>}
          </div>
          <input ref={archivo} type="file" accept=".csv" onChange={importar} style={{ display: "none" }} />
        </nav>
        <div className="ll-pie">
          <SelectorTema />
          <button className="ll-nav-item" onClick={() => setAmbientacion(true)}><span className="ll-nav-ico">⚙</span>Configuración</button>
          <button className="ll-nav-item peligro" onClick={logout}><span className="ll-nav-ico">←</span>Cerrar sesión</button>
          <div className="ll-version"><span className="ll-punto-vivo" />v{__APP_VERSION__} · {user?.username}</div>
        </div>
      </aside>

      <main className="ll-main">
        <header className="ll-header">
          <div style={{ display: "flex", alignItems: "center", gap: 16, minWidth: 0 }}>
            <button className="ll-icono-btn" title="Menú" aria-label={menu ? "Ocultar menú" : "Mostrar menú"} onClick={() => setMenu((m) => !m)}>{menu ? "⟨" : "⟩"}</button>
            {tab === "activos" && vistaEf && vistaEf !== "todos"
              ? <h1 className="ll-titulo">{puedeVer("activos") ? <a href="#activos" className="ll-miga" onClick={(e) => { e.preventDefault(); setVista("todos"); }}>Activos</a> : "Activos"} <span>/ {VISTAS_ACTIVOS.find(([k]) => k === vistaEf)[1]}</span></h1>
              : <h1 className="ll-titulo">{titulo} <span>— {sub}</span></h1>}
          </div>
          <button className="ll-btn-acento" onClick={() => { cargar(); cargarGlpi(); }}>
            <span style={{ display: "inline-flex", animation: cargando ? "ll-spin 1s linear infinite" : "none" }}>↻</span> Actualizar
          </button>
        </header>

        <div className="ll-contenido">
          {sinAcceso ? <div className="ll-card ll-sin-acceso" role="alert">
            <div style={{ fontSize: 30, marginBottom: 10 }}>⊘</div>
            <div style={{ fontSize: 17, fontWeight: 600 }}>No tenés acceso a este módulo</div>
            <div className="tenue" style={{ fontSize: 13, marginTop: 8 }}>Si lo necesitás, pedíselo a un administrador de Atlas (Herramientas → Accesos).</div>
          </div> : cargando && !assets.length ? <div className="ll-vacio">Cargando datos…</div> : <>
            {tab === "dashboard" && <Dashboard assets={assets} ir={ir} verFicha={verFicha} puedeVer={puedeVer} />}
            {tab === "activos" && vistasActivos.length > 1 && <nav className="ll-pestanas" aria-label="Subsecciones de Activos">
              {vistasActivos.map(([k, l]) => <button key={k} className={"ll-pestana" + (vistaEf === k ? " activa" : "")}
                aria-current={vistaEf === k ? "page" : undefined} onClick={() => setVista(k)}>{l}</button>)}
            </nav>}
            {tab === "activos" && vistaEf === "salud" && <Salud assets={assets} verFicha={verFicha} />}
            {tab === "activos" && vistaEf === "monitores" && <Monitores assets={assets} verFicha={verFicha} />}
            {tab === "activos" && vistaEf === "impresoras" && <Impresoras puedeEditar={puede(user, "impresoras", "editar")} avisar={avisar} />}
            {tab === "activos" && vistaEf === "todos" && <Activos filtrados={filtrados} filtros={filtros} setFiltros={setFiltros} orden={orden} setOrden={setOrden}
              verFicha={verFicha} editar={(a) => setEdicion(a)} eliminar={eliminarActivo} nuevo={() => setEdicion({})}
              exportar={exportarExcel} puedeEditar={puedeEditar} puedeEliminar={puedeEliminar} esAdmin={esAdmin} etiquetas={setEtiquetas} />}
            {tab === "telefonia" && <Telefonia puedeEditar={puede(user, "telefonia", "editar")} avisar={avisar} />}
            {tab === "licencias" && <Proximamente titulo="Licencias" columnas={["PRODUCTO", "CLAVE", "ASIGNADO A", "SEDE", "VENCE", "ESTADO", "ACCIONES"]}
              texto="El control de licencias (Claude, Office, antivirus) está diseñado pero quedó fuera del alcance de la v2.0.0. Se habilita en una versión posterior." />}
            {tab === "usuarios" && <Proximamente titulo="Usuarios"
              texto="La nómina de empleados (con sede, rol y licencias asignadas) está diseñada pero quedó fuera del alcance de la v2.0.0. Los accesos a la aplicación se administran en Herramientas → Accesos." />}
            {tab === "proyectos" && <div className="ll-seccion-clasica"><SeccionProyectos assets={assets} user={user} puedeEditar={puede(user, "proyectos", "editar")} /></div>}
            {tab === "reportes" && <Reportes assets={assets} ir={ir} exportar={exportarGrafico} />}
            {tab === "tendencias" && <div className="ll-seccion-clasica"><SeccionTendencias /></div>}
            {tab === "perfil" && <div className="ll-seccion-clasica"><SeccionPerfil user={user} /></div>}
            {tab === "agente" && <Agente />}
            {tab === "accesos" && <Accesos user={user} avisar={avisar} />}
            {tab === "actas" && <Actas key={actaAbrir || "lista"} assets={assets} puedeEditar={puedeEditar} avisar={avisar} onCambio={cargar} abrirId={actaAbrir} />}
            {tab === "auditoria" && <Auditoria puedeEditar={puede(user, "auditoria", "editar")} avisar={avisar} onCambio={cargar} />}
          </>}
        </div>
      </main>

      {puedeVer("impresoras") && <AlertaToner onVer={() => ir("activos", {}, "impresoras")} />}
      {ficha && <FichaActivo key={ficha.id} activo={ficha} glpiMap={glpiMap} user={user} onCerrar={() => setFicha(null)}
        onEditar={(a) => setEdicion(a)} onEliminar={eliminarActivo} consultarGarantia={consultarGarantia}
        puedeEditar={puedeEditar} puedeEliminar={puedeEliminar} abrirActivo={(id) => { const x = assets.find((y) => y.id === id); if (x) verFicha(x); }}
        avisar={avisar} onCambio={refrescarFicha} abrirActa={(id) => { setActaAbrir(id); ir("actas"); }} />}
      {etiquetas && <HojaEtiquetas activos={etiquetas} onCerrar={() => setEtiquetas(null)} />}
      {edicion && <ModalActivo inicial={edicion} onGuardar={guardarActivo} onCerrar={() => setEdicion(null)} />}
      <Ambientacion abierto={ambientacion} onCerrar={() => setAmbientacion(false)} />
      {Toast}
    </>
  );
}
