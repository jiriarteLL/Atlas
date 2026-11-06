// App.jsx — Esqueleto de la app con el diseño v2: menu lateral, encabezado y vistas.
// Ruteo por hash (#seccion?tipo=..&sede=..&estado=..) para que atras/adelante y los links funcionen.
import { Fragment, useCallback, useEffect, useMemo, useRef, useState } from "react";
import { useAuth, tienePermiso } from "./AuthContext";
import { API, apiFetch, http, setUsuarioActual } from "./api";
import { useToast, Proximamente } from "./diseno/comunes";
import Ambientacion from "./diseno/Ambientacion";
import { recordarTotal } from "./diseno/Intro";
import { exportarActivosExcel, exportarCSV, exportarReporte, leerCSV } from "./exportar";
import { cumpleEstado } from "./vistas/filtros";
import Dashboard from "./vistas/Dashboard";
import Activos from "./vistas/Activos";
import Impresoras from "./vistas/Impresoras";
import AlertaToner from "./vistas/AlertaToner";
import FichaActivo from "./vistas/FichaActivo";
import ModalActivo from "./vistas/ModalActivo";
import Reportes from "./vistas/Reportes";
import Accesos from "./vistas/Accesos";
import Agente from "./vistas/Agente";
import { SeccionTendencias } from "./secciones/SeccionTendencias";
import { SeccionProyectos } from "./secciones/SeccionProyectos";
import { SeccionPerfil } from "./secciones/SeccionPerfil";

const SECCIONES = {
  dashboard: ["Dashboard", "Vista general"], activos: ["Activos", "Inventario completo"],
  licencias: ["Licencias", "Software y suscripciones"], proyectos: ["Proyectos", "Seguimiento de IT"],
  reportes: ["Reportes", "Análisis"], tendencias: ["Tendencias", "Evolución en el tiempo"],
  usuarios: ["Usuarios", "Nómina"], perfil: ["Mi perfil", "Cuenta, permisos y seguridad"],
  agente: ["Agente", "Scripts de sincronización"], accesos: ["Accesos", "Usuarios de la aplicación"],
};
const FILTROS_VACIOS = { q: "", tipo: "", estado: "", sede: "" };
// Subsecciones de Activos (pestañas). Para sumar otro tipo con vista propia, agregarlo aca y en el render.
const VISTAS_ACTIVOS = [["todos", "Todos los activos"], ["impresoras", "Impresoras"]];
const vistaValida = (v) => (VISTAS_ACTIVOS.some(([k]) => k === v) ? v : "todos");

function leerHash() {
  const [sec, query] = (window.location.hash || "").replace("#", "").split("?");
  const p = new URLSearchParams(query || "");
  return { tab: SECCIONES[sec] ? sec : "dashboard", vista: vistaValida(p.get("vista")),
    filtros: { ...FILTROS_VACIOS, tipo: p.get("tipo") || "", sede: p.get("sede") || "", estado: p.get("estado") || "" } };
}

export default function App() {
  const { user, logout } = useAuth();
  const esAdmin = tienePermiso(user, "usuarios.administrar");
  const puedeEditar = tienePermiso(user, "inventario.editar");
  const puedeEliminar = tienePermiso(user, "activos.eliminar");
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
  const [ambientacion, setAmbientacion] = useState(false);
  const [menu, setMenu] = useState(() => window.innerWidth > 760);
  const archivo = useRef(null);

  useEffect(() => { setUsuarioActual(user?.username); }, [user]);

  const cargar = useCallback(async () => {
    setCargando(true);
    try {
      const a = await http.get(`${API}/assets`);
      setAssets(a);
      recordarTotal(a.length);
    } catch (e) { console.error(e); }
    setCargando(false);
  }, []);

  const cargarGlpi = useCallback(async () => {
    try {
      const r = await apiFetch(API + "/glpi/resumen");
      if (!r.ok) return;
      const lista = await r.json();
      const m = {};
      (Array.isArray(lista) ? lista : []).forEach((x) => { m[(x.serial || "").trim().toUpperCase()] = x; });
      setGlpiMap(m);
    } catch { /* GLPI no disponible: la ficha se muestra sin esos datos */ }
  }, []);

  useEffect(() => { cargar(); cargarGlpi(); }, [cargar, cargarGlpi]);

  // Hash -> estado (atras/adelante del navegador)
  useEffect(() => {
    const aplicar = () => { const h = leerHash(); setTab(h.tab); setVista(h.vista); setFiltros((f) => ({ ...h.filtros, q: h.tab === "activos" ? f.q : "" })); setFicha(null); };
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

  const ir = useCallback((sec, f, v) => {
    setTab(sec);
    setFicha(null);
    if (sec === "activos") { setFiltros({ ...FILTROS_VACIOS, ...(f || {}) }); setVista(vistaValida(v)); }
    if (window.innerWidth <= 760) setMenu(false);
  }, []);

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
    ["dashboard", "▦", "Dashboard"], ["activos", "▭", "Activos", assets.length], ["licencias", "⬡", "Licencias"],
    ["proyectos", "◧", "Proyectos"], ["reportes", "◫", "Reportes"], ["tendencias", "◭", "Tendencias"],
    ["usuarios", "⚇", "Usuarios"], ["perfil", "◉", "Mi perfil"],
  ];
  const [titulo, sub] = SECCIONES[tab];

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
                  {VISTAS_ACTIVOS.map(([v, lv]) => {
                    const act = tab === "activos" && vista === v;
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
          <div className="ll-nav-sec" style={{ marginTop: 22 }}>HERRAMIENTAS</div>
          <div className="ll-nav-lista">
            <button className={"ll-nav-item" + (tab === "agente" ? " activo" : "")} onClick={() => ir("agente")}><span className="ll-nav-ico">◈</span>Agente</button>
            {puedeEditar && <button className="ll-nav-item" onClick={() => archivo.current.click()}><span className="ll-nav-ico">⭱</span>Importar CSV</button>}
            <button className="ll-nav-item" onClick={() => { exportarCSV(assets); avisar("Exportando " + assets.length + " activos a CSV…"); }}><span className="ll-nav-ico">⭳</span>Exportar CSV</button>
            {esAdmin && <button className={"ll-nav-item" + (tab === "accesos" ? " activo" : "")} onClick={() => ir("accesos")}><span className="ll-nav-ico">◇</span>Accesos</button>}
          </div>
          <input ref={archivo} type="file" accept=".csv" onChange={importar} style={{ display: "none" }} />
        </nav>
        <div className="ll-pie">
          <button className="ll-nav-item" onClick={() => setAmbientacion(true)}><span className="ll-nav-ico">⚙</span>Configuración</button>
          <button className="ll-nav-item peligro" onClick={logout}><span className="ll-nav-ico">←</span>Cerrar sesión</button>
          <div className="ll-version"><span className="ll-punto-vivo" />v{__APP_VERSION__} · {user?.username}</div>
        </div>
      </aside>

      <main className="ll-main">
        <header className="ll-header">
          <div style={{ display: "flex", alignItems: "center", gap: 16, minWidth: 0 }}>
            <button className="ll-icono-btn" title="Menú" aria-label={menu ? "Ocultar menú" : "Mostrar menú"} onClick={() => setMenu((m) => !m)}>{menu ? "⟨" : "⟩"}</button>
            {tab === "activos" && vista !== "todos"
              ? <h1 className="ll-titulo"><a href="#activos" className="ll-miga" onClick={(e) => { e.preventDefault(); setVista("todos"); }}>Activos</a> <span>/ {VISTAS_ACTIVOS.find(([k]) => k === vista)[1]}</span></h1>
              : <h1 className="ll-titulo">{titulo} <span>— {sub}</span></h1>}
          </div>
          <button className="ll-btn-acento" onClick={() => { cargar(); cargarGlpi(); }}>
            <span style={{ display: "inline-flex", animation: cargando ? "ll-spin 1s linear infinite" : "none" }}>↻</span> Actualizar
          </button>
        </header>

        <div className="ll-contenido">
          {cargando && !assets.length ? <div className="ll-vacio">Cargando datos…</div> : <>
            {tab === "dashboard" && <Dashboard assets={assets} ir={ir} verFicha={verFicha} />}
            {tab === "activos" && <nav className="ll-pestanas" aria-label="Subsecciones de Activos">
              {VISTAS_ACTIVOS.map(([k, l]) => <button key={k} className={"ll-pestana" + (vista === k ? " activa" : "")}
                aria-current={vista === k ? "page" : undefined} onClick={() => setVista(k)}>{l}</button>)}
            </nav>}
            {tab === "activos" && vista === "impresoras" && <Impresoras puedeEditar={puedeEditar} avisar={avisar} />}
            {tab === "activos" && vista === "todos" && <Activos filtrados={filtrados} filtros={filtros} setFiltros={setFiltros} orden={orden} setOrden={setOrden}
              verFicha={verFicha} editar={(a) => setEdicion(a)} eliminar={eliminarActivo} nuevo={() => setEdicion({})}
              exportar={exportarExcel} puedeEditar={puedeEditar} puedeEliminar={puedeEliminar} esAdmin={esAdmin} />}
            {tab === "licencias" && <Proximamente titulo="Licencias" columnas={["PRODUCTO", "CLAVE", "ASIGNADO A", "SEDE", "VENCE", "ESTADO", "ACCIONES"]}
              texto="El control de licencias (Claude, Office, antivirus) está diseñado pero quedó fuera del alcance de la v2.0.0. Se habilita en una versión posterior." />}
            {tab === "usuarios" && <Proximamente titulo="Usuarios"
              texto="La nómina de empleados (con sede, rol y licencias asignadas) está diseñada pero quedó fuera del alcance de la v2.0.0. Los accesos a la aplicación se administran en Herramientas → Accesos." />}
            {tab === "proyectos" && <div className="ll-seccion-clasica"><SeccionProyectos assets={assets} user={user} /></div>}
            {tab === "reportes" && <Reportes assets={assets} ir={ir} exportar={exportarGrafico} />}
            {tab === "tendencias" && <div className="ll-seccion-clasica"><SeccionTendencias /></div>}
            {tab === "perfil" && <div className="ll-seccion-clasica"><SeccionPerfil user={user} /></div>}
            {tab === "agente" && <Agente />}
            {tab === "accesos" && esAdmin && <Accesos user={user} avisar={avisar} />}
          </>}
        </div>
      </main>

      <AlertaToner onVer={() => ir("activos", {}, "impresoras")} />
      {ficha && <FichaActivo key={ficha.id} activo={ficha} glpiMap={glpiMap} user={user} onCerrar={() => setFicha(null)}
        onEditar={(a) => setEdicion(a)} onEliminar={eliminarActivo} consultarGarantia={consultarGarantia}
        puedeEditar={puedeEditar} puedeEliminar={puedeEliminar} />}
      {edicion && <ModalActivo inicial={edicion} onGuardar={guardarActivo} onCerrar={() => setEdicion(null)} />}
      <Ambientacion abierto={ambientacion} onCerrar={() => setAmbientacion(false)} />
      {Toast}
    </>
  );
}
