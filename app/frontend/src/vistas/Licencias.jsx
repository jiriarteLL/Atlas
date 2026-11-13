// Licencias.jsx — Productos contratados, quién los tiene, cupos, costos y renovaciones.
// Los costos se cargan en Atlas (precio por licencia en USD y/o ARS, periodicidad, renovación) y se editan directo en
// la tabla de productos; ninguna importación los pisa. Costo = licencias (asientos) × precio. Los planes Team de Adobe y
// de Claude no tienen API: las personas se cargan a mano o con el CSV de miembros. Datos de /api/licencias.
import { Fragment, useCallback, useEffect, useMemo, useRef, useState } from "react";
import { apiFetch } from "../api";
import { fmtFechaHora } from "../ui";
import { Drawer, Ficha, Modal, Rotulo } from "../diseno/comunes";
import { DatalistCentros, refrescarCentros } from "../centros";

const URL = "/api/licencias";
const PROVEEDORES = ["Anthropic", "Adobe", "Microsoft", "Google", "Antivirus", "Otro"];
// productos que define una fuente externa (UserManager, API o exportación de Adobe): no se asignan a mano en Atlas
const EXTERNO = (origen) => ["usermanager", "adobe", "adobe-csv"].includes(origen);
const ORIGEN = { usermanager: "UserManager", adobe: "API de Adobe", "adobe-csv": "exportación de Adobe", manual: "carga manual",
  csv: "CSV", compartida: "compartida" };

async function pedir(url, opciones) {
  const r = await apiFetch(url, opciones);
  const d = await r.json().catch(() => ({}));
  if (!r.ok) {
    const det = Array.isArray(d.detail) ? d.detail.map((x) => x.msg).join(" · ") : d.detail;
    throw new Error(typeof det === "string" ? det : "Error " + r.status);
  }
  return d;
}
const json = (metodo, cuerpo) => ({ method: metodo, headers: { "Content-Type": "application/json" }, body: JSON.stringify(cuerpo) });

const num = (v, dec = 0) => (v == null ? "—" : Number(v).toLocaleString("es-AR", { minimumFractionDigits: dec, maximumFractionDigits: 2 }));
// {"USD": 150, "ARS": 20000} -> "USD 150 · ARS 20.000" (no se convierte entre monedas)
const montos = (o) => {
  const e = Object.entries(o || {}).filter(([, v]) => v);
  return e.length ? e.map(([m, v]) => `${m} ${num(v)}`).join(" · ") : "—";
};
const fmtFecha = (s) => { const m = /^(\d{4})-(\d{2})-(\d{2})/.exec(s || ""); return m ? `${m[3]}/${m[2]}/${m[1]}` : "—"; };
const mesActual = () => new Date().toISOString().slice(0, 7);

function BarraUso({ p }) {
  if (p.ilimitado) return <span className="tenue">{p.asignadas} · ilimitado</span>;
  if (p.cupo == null) return <span className="tenue">{p.asignadas} en uso · sin cupo</span>;
  const pct = p.cupo ? Math.min(100, (100 * p.asignadas) / p.cupo) : 100;
  const c = p.excedido ? "var(--ll-rojo)" : pct >= 90 ? "var(--ll-ambar)" : "var(--ll-verde)";
  return (
    <span style={{ display: "inline-flex", alignItems: "center", gap: 8 }}>
      <span style={{ width: 64, height: 7, borderRadius: 4, background: "var(--ll-track)", overflow: "hidden" }}>
        <span style={{ display: "block", width: Math.max(2, pct) + "%", height: "100%", background: c }} />
      </span>
      <span className="mono" style={{ fontSize: 12, color: c }}>{p.asignadas}/{p.cupo}</span>
    </span>
  );
}

function Tarjeta({ valor, rotulo, sub, color, activa, onClick }) {
  return (
    <button type="button" className="ll-card hover" aria-pressed={!!activa} onClick={onClick}
      style={{ textAlign: "left", padding: "14px 16px", cursor: onClick ? "pointer" : "default", color: "inherit", font: "inherit",
        borderColor: activa ? color : undefined, boxShadow: activa ? `0 0 0 1px ${color}` : undefined }}>
      <div className="mono" style={{ fontSize: 18, fontWeight: 600, color: color || "var(--ll-text)", lineHeight: 1.25 }}>{valor}</div>
      <div style={{ fontSize: 12.5, color: "var(--ll-text-2)", marginTop: 4 }}>{rotulo}</div>
      {sub && <div className="tenue" style={{ fontSize: 11.5, marginTop: 2 }}>{sub}</div>}
    </button>
  );
}

// Celda editable: guarda al salir (o con Enter). Vacío = sin dato.
function CeldaEditable({ valor, tipo = "number", ancho = 92, prefijo, onGuardar, opciones, deshabilitada, lista, placeholder, max }) {
  const [v, setV] = useState(valor ?? "");
  useEffect(() => { setV(valor ?? ""); }, [valor]);
  const guardar = () => {
    const nuevo = v === "" ? null : (tipo === "number" ? Number(v) : v);
    if ((nuevo ?? "") !== (valor ?? "")) onGuardar(nuevo);
  };
  if (deshabilitada) return <span className="mono" style={{ fontSize: 12.5 }}>{valor == null || valor === "" ? "—" : (prefijo ? `${prefijo} ${num(valor, 2)}` : valor)}</span>;
  const comun = { onClick: (e) => e.stopPropagation(), onBlur: guardar, onKeyDown: (e) => { if (e.key === "Enter") e.target.blur(); },
    className: (opciones ? "ll-select" : "ll-input") + " mono", style: { width: ancho, padding: "5px 8px", fontSize: 12.5 } };
  if (opciones) {
    return <select {...comun} value={v} onChange={(e) => { setV(e.target.value); onGuardar(e.target.value); }} onBlur={undefined}>
      {opciones.map(([k, l]) => <option key={k} value={k}>{l}</option>)}</select>;
  }
  return <input {...comun} type={tipo} min={tipo === "number" ? 0 : undefined} max={max} step={tipo === "number" ? "0.01" : undefined}
    list={lista} value={v} placeholder={placeholder ?? prefijo ?? ""} onChange={(e) => setV(e.target.value)}
    aria-label={prefijo ? "Precio " + prefijo : (placeholder || "Valor")} />;
}

export default function Licencias({ puedeEditar, avisar, verFicha, assets }) {
  const [datos, setDatos] = useState({ productos: [], resumen: {}, centros: [] });
  const [personas, setPersonas] = useState([]);
  const [compartidas, setCompartidas] = useState([]);
  const [cuentas, setCuentas] = useState([]);
  const [costos, setCostos] = useState([]);
  const [cargando, setCargando] = useState(true);
  const [error, setError] = useState("");
  const [pestana, setPestana] = useState("productos");
  const [filtros, setFiltros] = useState({ q: "", proveedor: "", alerta: "", producto: "" });
  const [producto, setProducto] = useState(null);
  const [persona, setPersona] = useState(null);
  const [modal, setModal] = useState("");   // nuevo | importar | costo
  const [cuenta, setCuenta] = useState(null);   // {} = nueva, {...} = editar

  const cargar = useCallback(async () => {
    setCargando(true);
    try {
      const [d, p, c, e, k] = await Promise.all([pedir(URL), pedir(URL + "/personas"), pedir(URL + "/compartidas"),
        pedir(URL + "/cuentas-equipo"), pedir(URL + "/costos")]);
      setDatos(d); setPersonas(p); setCompartidas(c); setCuentas(e); setCostos(k); setError("");
    } catch (err) { setError(err.message); } finally { setCargando(false); }
  }, []);
  useEffect(() => { cargar(); }, [cargar]);

  async function guardarProducto(id, cambios) {
    try { await pedir(URL + "/productos/" + id, json("PUT", cambios)); cargar(); }
    catch (e) { avisar && avisar("No se pudo guardar: " + e.message); }
  }

  const r = datos.resumen || {};
  const activos = useMemo(() => datos.productos.filter((p) => p.activo), [datos]);
  const q = filtros.q.trim().toLowerCase();
  const prodFiltrados = useMemo(() => activos.filter((p) =>
    (!filtros.proveedor || p.proveedor === filtros.proveedor)
    && (filtros.alerta !== "libres" || (p.libres || 0) > 0)
    && (filtros.alerta !== "sin_precio" || p.sin_precio)
    && (!q || [p.producto, p.plan, p.proveedor, p.contrato].some((v) => String(v || "").toLowerCase().includes(q)))), [activos, filtros, q]);
  const persFiltradas = useMemo(() => personas.filter((x) =>
    (filtros.alerta !== "deshabilitadas" || x.deshabilitada)
    && (!filtros.proveedor || x.productos.some((p) => p.proveedor === filtros.proveedor))
    && (!q || [x.persona, x.nombre, x.sede, x.centro_costo, x.legajo, ...x.productos.map((p) => p.producto)].some((v) => String(v || "").toLowerCase().includes(q)))),
  [personas, filtros, q]);
  const renovaciones = useMemo(() => activos.filter((p) => p.fecha_renovacion)
    .sort((a, b) => String(a.fecha_renovacion).localeCompare(String(b.fecha_renovacion))), [activos]);
  const proveedores = useMemo(() => [...new Set(datos.productos.map((p) => p.proveedor))].sort(), [datos]);
  const f = (k) => (e) => setFiltros({ ...filtros, [k]: e.target.value });
  const ir = (pest, alerta = "") => { setPestana(pest); setFiltros({ ...filtros, alerta }); };

  async function exportar() {
    const res = await apiFetch(URL + "/exportar.csv");
    if (!res.ok) { avisar && avisar("No se pudo exportar"); return; }
    const url = window.URL.createObjectURL(await res.blob());
    const link = document.createElement("a"); link.href = url; link.download = "licencias-atlas.csv"; link.click();
    setTimeout(() => window.URL.revokeObjectURL(url), 1000);
  }

  const PESTANAS = [["productos", "Productos"], ["personas", "Personas"], ["centros", "Centros de costo"],
    ...(compartidas.length ? [["compartidas", "Compartidas"]] : []), ["cuentas", "Cuentas de equipo"],
    ["costos", "Costos por mes"], ["renovaciones", "Renovaciones"]];
  const contador = { productos: prodFiltrados.length + " productos", personas: persFiltradas.length + " personas",
    centros: (datos.centros || []).length + " centros", compartidas: compartidas.length + " compartidas",
    cuentas: cuentas.length + " cuentas", costos: costos.length + " meses", renovaciones: renovaciones.length + " productos" }[pestana];

  return (
    <div>
      <div style={{ display: "grid", gridTemplateColumns: "repeat(auto-fill, minmax(190px, 1fr))", gap: 12, marginBottom: 20 }}>
        <Tarjeta valor={montos(r.mensual)} rotulo="Costo mensual" sub="licencias × precio (anual / 12)" color="var(--accent)" />
        <Tarjeta valor={montos(r.anual)} rotulo="Costo anual" />
        <Tarjeta valor={`${num(r.asignadas)} / ${num(r.cupo)}`} rotulo="En uso / contratadas"
          sub={r.sin_cupo ? `${r.sin_cupo} producto(s) sin cupo cargado` : null} onClick={() => ir("productos")} />
        <Tarjeta valor={montos(r.sin_asignar_mensual)} rotulo={`Sin asignar (${num(r.libres)} lic.) por mes`} color="var(--ll-ambar)"
          activa={filtros.alerta === "libres"} onClick={() => ir("productos", filtros.alerta === "libres" ? "" : "libres")} />
        <Tarjeta valor={num(r.sin_precio)} rotulo="Productos sin precio cargado" color={r.sin_precio ? "var(--ll-ambar)" : undefined}
          activa={filtros.alerta === "sin_precio"} onClick={() => ir("productos", filtros.alerta === "sin_precio" ? "" : "sin_precio")} />
        <Tarjeta valor={num(r.renovaciones_proximas)} rotulo="Renuevan en 60 días" color={r.renovaciones_proximas ? "var(--ll-ambar)" : undefined}
          activa={pestana === "renovaciones"} onClick={() => ir("renovaciones")} />
        <Tarjeta valor={num(r.asignadas_deshabilitadas)} rotulo="Asignadas a bajas o cuentas deshabilitadas"
          color={r.asignadas_deshabilitadas ? "var(--ll-rosa)" : undefined}
          sub={r.personas_baja ? `${r.personas_baja} de baja en la nómina` : null}
          activa={filtros.alerta === "deshabilitadas"} onClick={() => ir("personas", filtros.alerta === "deshabilitadas" ? "" : "deshabilitadas")} />
      </div>

      <nav className="ll-pestanas" aria-label="Vistas de licencias">
        {PESTANAS.map(([k, l]) => <button key={k} className={"ll-pestana" + (pestana === k ? " activa" : "")} onClick={() => setPestana(k)}>{l}</button>)}
      </nav>

      <div className="ll-barra">
        <div className="ll-buscador">
          <span>⌕</span>
          <input className="ll-input" value={filtros.q} onChange={f("q")} placeholder="Buscar producto, persona, mail o centro de costo…" aria-label="Buscar licencias" />
        </div>
        <select className="ll-select" style={{ width: "auto" }} value={filtros.proveedor} onChange={f("proveedor")} aria-label="Proveedor">
          <option value="">Todos los proveedores</option>
          {proveedores.map((p) => <option key={p}>{p}</option>)}
        </select>
        {pestana === "cuentas" && <select className="ll-select" style={{ width: "auto" }} value={filtros.producto} onChange={f("producto")} aria-label="Producto">
          <option value="">Todos los productos ({cuentas.filter((c) => c.activo).length})</option>
          {[...new Set(cuentas.map((c) => c.producto).filter(Boolean))].sort().map((x) =>
            <option key={x} value={x}>{x} ({cuentas.filter((c) => c.activo && c.producto === x).length})</option>)}
        </select>}
        {filtros.alerta && <button className="ll-btn-borde" onClick={() => setFiltros({ ...filtros, alerta: "" })}>Quitar filtro ✕</button>}
        <span className="ll-contador">{contador}</span>
        <span style={{ flex: 1 }} />
        {puedeEditar && <button className="ll-btn-primario" onClick={() => setModal("nuevo")}>+ Producto</button>}
        {puedeEditar && <button className="ll-btn-borde" onClick={() => setModal("importar")}>Importar miembros</button>}
        {puedeEditar && pestana === "cuentas" && <button className="ll-btn-borde" onClick={() => setCuenta({})}>+ Cuenta</button>}
        {puedeEditar && pestana === "costos" && <button className="ll-btn-borde" onClick={() => setModal("costo")}>+ Costo del mes</button>}
        <button className="ll-btn-borde" onClick={exportar}>Exportar</button>
      </div>

      {error && <div className="ll-vacio" style={{ color: "var(--ll-warn)" }}>No se pudieron cargar las licencias: {error}</div>}
      <div className="ll-card" style={{ overflow: "hidden" }}>
        <div className="ll-tabla-wrap">
          {pestana === "productos" && <table className="ll-tabla" style={{ minWidth: 1280 }}>
            <thead><tr><th>PRODUCTO</th><th>PROVEEDOR</th><th>USO</th><th>CUPO</th><th>PRECIO USD</th><th>PRECIO ARS</th><th>PERÍODO</th>
              <th>COSTO MENSUAL</th><th>COSTO ANUAL</th><th>SIN ASIGNAR / MES</th><th>RENOVACIÓN</th></tr></thead>
            <tbody>{prodFiltrados.map((p) => (
              <tr key={p.id} className="click" onClick={() => setProducto(p.id)}>
                <td className="nombre">{p.producto}<div className="tenue" style={{ fontSize: 11.5, fontWeight: 400 }}>{[p.plan && "Plan " + p.plan, ORIGEN[p.origen]].filter(Boolean).join(" · ")}</div></td>
                <td><span className={"ll-chip" + (p.proveedor === "Anthropic" || p.proveedor === "Adobe" ? " acento" : "")}>{p.proveedor}</span></td>
                <td><BarraUso p={p} /></td>
                <td><CeldaEditable valor={p.cupo} ancho={70} deshabilitada={!puedeEditar} onGuardar={(v) => guardarProducto(p.id, v == null ? { cupo_automatico: true } : { cupo: v })} /></td>
                <td><CeldaEditable valor={p.precio_usd} prefijo="USD" deshabilitada={!puedeEditar} onGuardar={(v) => guardarProducto(p.id, { precio_usd: v })} /></td>
                <td><CeldaEditable valor={p.precio_ars} prefijo="ARS" ancho={110} deshabilitada={!puedeEditar} onGuardar={(v) => guardarProducto(p.id, { precio_ars: v })} /></td>
                <td><CeldaEditable valor={p.periodo} ancho={98} deshabilitada={!puedeEditar} opciones={[["mensual", "Mensual"], ["anual", "Anual"]]}
                  onGuardar={(v) => guardarProducto(p.id, { periodo: v })} /></td>
                <td className="mono" style={{ fontSize: 12.5 }}>{p.sin_precio ? <span style={{ color: "var(--ll-ambar)" }}>sin precio</span> : montos(p.costo_mensual)}</td>
                <td className="mono" style={{ fontSize: 12.5 }}>{montos(p.costo_anual)}</td>
                <td className="mono" style={{ fontSize: 12.5, color: Object.keys(p.costo_sin_asignar_mensual).length ? "var(--ll-ambar)" : "var(--ll-dim)" }}>
                  {Object.keys(p.costo_sin_asignar_mensual).length ? `${montos(p.costo_sin_asignar_mensual)} (${p.libres})` : (p.libres > 0 ? `${p.libres} libres` : "—")}</td>
                <td><CeldaEditable valor={p.fecha_renovacion} tipo="date" ancho={140} deshabilitada={!puedeEditar}
                  onGuardar={(v) => guardarProducto(p.id, { fecha_renovacion: v })} /></td>
              </tr>))}
            </tbody>
          </table>}

          {pestana === "personas" && <table className="ll-tabla" style={{ minWidth: 980 }}>
            <thead><tr><th>PERSONA</th><th>CENTRO DE COSTO</th><th>SEDE</th><th>LICENCIAS</th><th>EQUIPOS EN ATLAS</th><th>COSTO MENSUAL</th><th>COSTO ANUAL</th></tr></thead>
            <tbody>{persFiltradas.map((x) => (
              <tr key={x.persona} className="click" onClick={() => setPersona(x.persona)}>
                <td className="nombre">{x.nombre || x.persona}
                  <div className="tenue" style={{ fontSize: 11.5, fontWeight: 400 }}>{[x.persona, x.legajo && "legajo " + x.legajo].filter(Boolean).join(" · ")}</div>
                  {x.deshabilitada && <div style={{ fontSize: 11.5, color: "var(--ll-rosa)", fontWeight: 600 }}>{x.de_baja ? "De baja en la nómina" : "Cuenta deshabilitada"}</div>}</td>
                <td>{x.centro_costo}{x.area && <div className="tenue" style={{ fontSize: 11.5 }}>{x.area}</div>}</td>
                <td>{x.sede}</td>
                <td><div style={{ display: "flex", gap: 6, flexWrap: "wrap" }}>{x.productos.map((p) => <span key={p.id + p.origen} className="ll-chip">{p.producto}{p.fraccion < 1 ? " ½" : ""}</span>)}</div></td>
                <td style={{ fontSize: 12.5 }}>{x.equipos.length ? x.equipos.map((e) => e.nombre).join(", ") : <span className="tenue">—</span>}</td>
                <td className="mono" style={{ fontSize: 12.5 }}>{montos(x.costo_mensual)}</td>
                <td className="mono" style={{ fontSize: 12.5 }}>{montos(x.costo_anual)}</td>
              </tr>))}
            </tbody>
          </table>}

          {pestana === "centros" && <table className="ll-tabla" style={{ minWidth: 640 }}>
            <thead><tr><th>CENTRO DE COSTO / UNIDAD</th><th>COSTO MENSUAL</th><th>COSTO ANUAL</th></tr></thead>
            <tbody>{(datos.centros || []).map((c) => (
              <tr key={c.centro}><td className="nombre" style={{ color: c.centro === "sin asignar" ? "var(--ll-ambar)" : undefined }}>{c.centro}</td>
                <td className="mono" style={{ fontSize: 12.5 }}>{montos(c.mensual)}</td><td className="mono" style={{ fontSize: 12.5 }}>{montos(c.anual)}</td></tr>))}
            </tbody>
          </table>}

          {pestana === "compartidas" && <table className="ll-tabla" style={{ minWidth: 900 }}>
            <thead><tr><th>PRODUCTO</th><th>SECTOR</th><th>PRINCIPAL</th><th>SEGUNDO USUARIO</th><th>CENTRO DE COSTO · REPARTO</th><th>COSTO MENSUAL</th><th>ESTADO</th></tr></thead>
            <tbody>{compartidas.map((c) => (
              <tr key={c.id}><td className="nombre">{c.producto || "—"}</td><td>{c.sector}</td>
                <td>{c.principal_nombre || c.principal}<div className="tenue" style={{ fontSize: 11.5 }}>{c.principal_centro}</div></td>
                <td>{c.secundario_nombre || c.secundario || "—"}<div className="tenue" style={{ fontSize: 11.5 }}>{c.secundario_centro}</div></td>
                <td>{c.imputacion || <span className="tenue">el de cada persona</span>}<div className="tenue" style={{ fontSize: 11.5 }}>{c.porcentaje} / {100 - c.porcentaje}</div></td>
                <td className="mono" style={{ fontSize: 12.5 }}>{montos(c.mensual)}</td>
                <td>{c.activo ? "Activa" : <span className="tenue">Inactiva</span>}</td></tr>))}
            </tbody>
          </table>}

          {pestana === "cuentas" && <table className="ll-tabla" style={{ minWidth: 900 }}>
            <thead><tr><th>CUENTA</th><th>UNIDAD</th><th>LÍDER</th><th>RESPONSABLE</th><th>PRODUCTO</th><th>COSTO MENSUAL</th><th>ESTADO</th></tr></thead>
            <tbody>{cuentas.filter((c) => (!filtros.producto || c.producto === filtros.producto) && (!q || [c.numero, c.unidad, c.lider, c.responsable, c.email, c.tipo, c.producto]
              .some((v) => String(v || "").toLowerCase().includes(q)))).map((c) => (
              <tr key={c.id} className={puedeEditar ? "click" : undefined} onClick={puedeEditar ? () => setCuenta(c) : undefined}
                title={puedeEditar ? "Editar la cuenta" : undefined}><td className="nombre mono">{c.numero}<div className="tenue" style={{ fontSize: 11.5 }}>{c.email}</div></td>
                <td>{c.unidad}</td><td>{c.lider}</td><td>{c.responsable}</td><td>{c.producto || c.tipo || "—"}</td>
                <td className="mono" style={{ fontSize: 12.5 }}>{montos(c.mensual)}</td><td>{c.activo ? (c.estado || "Activa") : <span className="tenue">Inactiva</span>}</td></tr>))}
            </tbody>
          </table>}

          {pestana === "costos" && <table className="ll-tabla" style={{ minWidth: 860 }}>
            <thead><tr><th>MES</th><th>PRODUCTO</th><th>WORKSPACE</th><th>LICENCIAS</th><th>MONTO</th><th>ORIGEN</th></tr></thead>
            <tbody>{costos.map((m) => (
              <Fragment key={m.periodo}>
                <tr><td className="nombre mono">{m.periodo}</td><td colSpan={3} className="tenue">Total del mes</td>
                  <td className="mono" style={{ fontSize: 12.5, fontWeight: 600 }}>{montos(m.total)}</td><td /></tr>
                {m.productos.map((x, i) => (
                  <tr key={m.periodo + i}><td /><td>{x.producto}<div className="tenue" style={{ fontSize: 11.5 }}>{x.proveedor}</div></td>
                    <td>{x.workspace || <span className="tenue">—</span>}</td><td className="mono">{x.cantidad ?? "—"}</td>
                    <td className="mono" style={{ fontSize: 12.5 }}>{x.moneda} {num(x.monto, 2)}</td>
                    <td><span className={"ll-chip" + (x.origen === "api" ? " acento" : "")}>{x.origen === "api" ? "API" : "manual"}</span></td></tr>))}
              </Fragment>))}
            </tbody>
          </table>}

          {pestana === "renovaciones" && <table className="ll-tabla" style={{ minWidth: 760 }}>
            <thead><tr><th>RENUEVA</th><th>PRODUCTO</th><th>PROVEEDOR</th><th>CONTRATO</th><th>COSTO ANUAL</th></tr></thead>
            <tbody>{renovaciones.map((p) => (
              <tr key={p.id} className="click" onClick={() => setProducto(p.id)}>
                <td className="mono" style={{ color: p.renueva_pronto ? "var(--ll-ambar)" : p.renovacion_dias < 0 ? "var(--ll-rosa)" : undefined }}>
                  {fmtFecha(p.fecha_renovacion)}<div className="tenue" style={{ fontSize: 11 }}>{p.renovacion_dias < 0 ? `hace ${-p.renovacion_dias} días` : `en ${p.renovacion_dias} días`}</div></td>
                <td className="nombre">{p.producto}</td><td>{p.proveedor}</td><td>{p.contrato || <span className="tenue">—</span>}</td>
                <td className="mono" style={{ fontSize: 12.5 }}>{montos(p.costo_anual)}</td>
              </tr>))}
            </tbody>
          </table>}
        </div>
        {!cargando && pestana === "productos" && !prodFiltrados.length && <div className="ll-vacio">{activos.length ? "Sin productos que coincidan." : "Todavía no hay productos: cargá uno con + Producto."}</div>}
        {!cargando && pestana === "personas" && !persFiltradas.length && <div className="ll-vacio">Todavía no hay personas con licencias: asignalas desde la ficha del producto o con Importar miembros.</div>}
        {!cargando && pestana === "centros" && !(datos.centros || []).length && <div className="ll-vacio">Sin costos para repartir: cargá precios y personas.</div>}
        {!cargando && pestana === "costos" && !costos.length && <div className="ll-vacio">Sin costos reales por mes todavía (se cargan a mano con lo que dice la factura, o los traerá la API cuando haya).</div>}
        {!cargando && pestana === "renovaciones" && !renovaciones.length && <div className="ll-vacio">Ningún producto tiene fecha de renovación cargada.</div>}
        {cargando && !datos.productos.length && <div className="ll-vacio">Cargando licencias…</div>}
      </div>

      <PanelFuentes puedeEditar={puedeEditar} avisar={avisar} onTermino={cargar} />

      {producto && <FichaProducto id={producto} puedeEditar={puedeEditar} avisar={avisar} onCerrar={() => setProducto(null)} onCambio={cargar} />}
      {persona && <FichaPersona p={personas.find((x) => x.persona === persona)} puedeEditar={puedeEditar} avisar={avisar}
        onCerrar={() => setPersona(null)} onCambio={cargar} verEquipo={(id) => { const a = (assets || []).find((y) => y.id === id); if (a) verFicha(a); }} />}
      {modal === "nuevo" && <NuevoProducto onCerrar={() => setModal("")} avisar={avisar} onCreado={(id) => { setModal(""); cargar(); setProducto(id); }} />}
      {cuenta && <EditarCuenta cuenta={cuenta} onCerrar={() => setCuenta(null)} avisar={avisar} onListo={() => { setCuenta(null); cargar(); }} />}
      {modal === "importar" && <ImportarMiembros productos={activos} onCerrar={() => setModal("")} avisar={avisar} onListo={() => { setModal(""); cargar(); }} />}
      {modal === "costo" && <NuevoCosto productos={activos} onCerrar={() => setModal("")} avisar={avisar} onListo={() => { setModal(""); cargar(); }} />}
    </div>
  );
}

// ---------------------------------------------------------------- fuentes y conectores
function Fila({ color, titulo, children }) {
  return (
    <div style={{ border: "1px solid var(--ll-line)", borderRadius: 12, padding: "12px 14px" }}>
      <div style={{ display: "flex", alignItems: "center", gap: 8 }}>
        <span style={{ width: 8, height: 8, borderRadius: "50%", background: color }} />
        <span style={{ fontWeight: 600, fontSize: 13.5 }}>{titulo}</span>
      </div>
      <div style={{ fontSize: 12, color: "var(--ll-dim)", marginTop: 6, lineHeight: 1.5 }}>{children}</div>
    </div>
  );
}

function PanelFuentes({ puedeEditar, avisar, onTermino }) {
  const [c, setC] = useState(null);
  const cargar = useCallback(async () => {
    try { const r = await apiFetch(URL + "/conector"); if (r.ok) setC(await r.json()); } catch { /* sin red */ }
  }, []);
  useEffect(() => { cargar(); }, [cargar]);
  const corriendo = !!(c && (c.corriendo || c.pedida));
  useEffect(() => {
    if (!corriendo) return undefined;
    const t = setInterval(cargar, 5000);
    return () => clearInterval(t);
  }, [corriendo, cargar]);
  const antes = useRef(corriendo);
  useEffect(() => { if (antes.current && !corriendo) onTermino && onTermino(); antes.current = corriendo; }, [corriendo, onTermino]);
  async function actualizar() {
    try { await pedir(URL + "/conector/actualizar", { method: "POST" }); avisar && avisar("Consultando Adobe…"); setTimeout(cargar, 1500); }
    catch (e) { avisar && avisar(e.message); }
  }
  return (
    <div className="ll-card" style={{ padding: "16px 18px", marginTop: 20 }}>
      <div style={{ display: "flex", alignItems: "center", gap: 10, marginBottom: 12, flexWrap: "wrap" }}>
        <div className="mono" style={{ fontSize: 11.5, letterSpacing: 1.5, color: "var(--ll-dim)" }}>FUENTES Y CONECTORES</div>
        <span style={{ flex: 1 }} />
        {puedeEditar && c && c.configurado && <button className="ll-btn-borde" disabled={corriendo} onClick={actualizar}>{corriendo ? "Actualizando…" : "Actualizar Adobe"}</button>}
      </div>
      <div style={{ display: "grid", gridTemplateColumns: "repeat(auto-fill, minmax(280px, 1fr))", gap: 12 }}>
        <Fila color={c && c.configurado ? (c.ok === false ? "var(--ll-rojo)" : "var(--ll-verde)") : "var(--ll-ghost)"} titulo="Adobe (plan Teams)">
          {c && c.configurado
            ? <>{corriendo ? "Consultando…" : c.fin ? `Última: ${fmtFechaHora(c.fin)} · ${c.mensaje || ""}` : "Todavía no corrió"}</>
            : <>Plan Teams: sin API (la User Management API es solo de Enterprise). Asignaciones por carga manual o con <b>Importar miembros</b> (exportación de usuarios de la Admin Console).</>}
        </Fila>
        <Fila color="var(--ll-ghost)" titulo="Anthropic · Claude (plan Team)">
          Plan Team: sin API (la Admin / Analytics API es solo de Enterprise). Asignaciones por carga manual o CSV de miembros; el costo es licencias × precio por asiento.
        </Fila>
        <Fila color="var(--ll-ghost)" titulo="Costos">
          Precio por licencia en USD y/o ARS, periodicidad y renovación se cargan en la tabla de productos. Los costos reales por mes se cargan en <b>Costos por mes</b> (o los traerá la API cuando haya).
        </Fila>
      </div>
    </div>
  );
}

// ---------------------------------------------------------------- ficha de producto
function FichaProducto({ id, puedeEditar, avisar, onCerrar, onCambio }) {
  const [p, setP] = useState(null);
  const [error, setError] = useState("");
  const [edicion, setEdicion] = useState(null);
  const [nueva, setNueva] = useState({ persona: "", nombre: "" });
  const [guardando, setGuardando] = useState(false);
  const cargar = useCallback(async () => {
    try { setP(await pedir(URL + "/productos/" + id)); setError(""); } catch (e) { setError(e.message); }
  }, [id]);
  useEffect(() => { cargar(); }, [cargar]);

  const editar = () => setEdicion({ proveedor: p.proveedor, producto: p.producto, plan: p.plan, precio_usd: p.precio_usd ?? "", precio_ars: p.precio_ars ?? "",
    periodo: p.periodo, fecha_renovacion: p.fecha_renovacion || "", cupo: p.cupo ?? "", contrato: p.contrato, notas: p.notas });
  const set = (k) => (e) => setEdicion({ ...edicion, [k]: e.target.value });
  async function guardar() {
    setGuardando(true);
    const n = (v) => (v === "" ? null : Number(v));
    const cuerpo = { precio_usd: n(edicion.precio_usd), precio_ars: n(edicion.precio_ars), periodo: edicion.periodo,
      fecha_renovacion: edicion.fecha_renovacion || null, contrato: edicion.contrato || "", notas: edicion.notas || "" };
    Object.assign(cuerpo, { proveedor: edicion.proveedor, producto: edicion.producto, plan: edicion.plan || "" });
    if (edicion.cupo !== "") cuerpo.cupo = Number(edicion.cupo); else if (p.cupo_manual) cuerpo.cupo_automatico = true;
    try {
      await pedir(URL + "/productos/" + id, json("PUT", cuerpo));
      setEdicion(null); avisar && avisar("Producto actualizado"); cargar(); onCambio && onCambio();
    } catch (e) { setError(e.message); } finally { setGuardando(false); }
  }
  async function asignar() {
    try {
      await pedir(URL + "/asignaciones", json("POST", { producto_id: id, persona: nueva.persona, nombre: nueva.nombre }));
      setNueva({ persona: "", nombre: "" }); cargar(); onCambio && onCambio();
    } catch (e) { avisar && avisar(e.message); }
  }
  async function liberar(aid) {
    try { await pedir(URL + "/asignaciones/" + aid + "/liberar", { method: "POST" }); cargar(); onCambio && onCambio(); }
    catch (e) { avisar && avisar(e.message); }
  }
  // segundo usuario, % del principal y centro de costo de una asignación (vale también para las importadas)
  async function guardarReparto(aid, cambios) {
    try {
      await pedir(URL + "/asignaciones/" + aid, json("PUT", cambios));
      if ("centro_costo" in cambios) refrescarCentros();
      cargar(); onCambio && onCambio();
    } catch (e) { avisar && avisar("No se pudo guardar: " + e.message); cargar(); }
  }
  const activas = p ? p.asignaciones.filter((a) => a.estado === "activa") : [];
  const liberadas = p ? p.asignaciones.filter((a) => a.estado !== "activa") : [];

  return (
    <Drawer abierto onCerrar={onCerrar} ancho>
      <div className="ll-drawer-cab">
        <div style={{ minWidth: 0 }}>
          <div style={{ fontSize: 20, fontWeight: 600, color: "var(--accent)" }}>{p ? p.producto : "Producto"}</div>
          {p && <div style={{ fontSize: 12.5, color: "var(--ll-dim)", marginTop: 4 }}>{[p.proveedor, p.plan && "Plan " + p.plan, ORIGEN[p.origen]].filter(Boolean).join(" · ")}</div>}
        </div>
        <button className="ll-cerrar" onClick={onCerrar} aria-label="Cerrar">✕</button>
      </div>
      {error && <div className="ll-vacio" style={{ color: "var(--ll-warn)", padding: 12 }}>{error}</div>}
      {!p ? <div className="ll-vacio">Cargando…</div> : edicion ? (
        <div style={{ display: "flex", flexDirection: "column", gap: 14 }}>
          <Rotulo>PRODUCTO Y COSTOS</Rotulo>
          <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: 12 }}>
            <label className="ll-campo"><span>PROVEEDOR</span>
                <select className="ll-select" value={edicion.proveedor} onChange={set("proveedor")}>{[...new Set([edicion.proveedor, ...PROVEEDORES])].map((x) => <option key={x}>{x}</option>)}</select></label>
            <label className="ll-campo"><span>PRODUCTO</span><input className="ll-input" value={edicion.producto} onChange={set("producto")} /></label>
            <label className="ll-campo"><span>PLAN</span><input className="ll-input" value={edicion.plan} onChange={set("plan")} /></label>
            <label className="ll-campo"><span>CUPO CONTRATADO (LICENCIAS)</span><input className="ll-input mono" type="number" min="0" value={edicion.cupo} onChange={set("cupo")} /></label>
            <label className="ll-campo"><span>PRECIO POR LICENCIA · USD</span><input className="ll-input mono" type="number" min="0" step="0.01" value={edicion.precio_usd} onChange={set("precio_usd")} /></label>
            <label className="ll-campo"><span>PRECIO POR LICENCIA · ARS</span><input className="ll-input mono" type="number" min="0" step="0.01" value={edicion.precio_ars} onChange={set("precio_ars")} /></label>
            <label className="ll-campo"><span>PERÍODO DEL PRECIO</span><select className="ll-select" value={edicion.periodo} onChange={set("periodo")}><option value="mensual">Mensual</option><option value="anual">Anual</option></select></label>
            <label className="ll-campo"><span>RENOVACIÓN</span><input className="ll-input" type="date" value={edicion.fecha_renovacion || ""} onChange={set("fecha_renovacion")} /></label>
            <label className="ll-campo"><span>CONTRATO / FACTURA</span><input className="ll-input" value={edicion.contrato} onChange={set("contrato")} /></label>
          </div>
          <label className="ll-campo"><span>NOTAS</span><textarea className="ll-input" rows={3} value={edicion.notas} onChange={set("notas")} /></label>
          <div style={{ display: "flex", gap: 10, justifyContent: "flex-end" }}>
            <button className="ll-btn-borde" onClick={() => setEdicion(null)}>Cancelar</button>
            <button className="ll-btn-primario" disabled={guardando} onClick={guardar}>{guardando ? "Guardando…" : "Guardar"}</button>
          </div>
        </div>
      ) : (<>
        <div style={{ display: "flex", alignItems: "center", gap: 10, flexWrap: "wrap" }}>
          <BarraUso p={p} />
          {p.excedido && <span style={{ color: "var(--ll-rojo)", fontSize: 12.5, fontWeight: 600 }}>Más en uso que contratadas</span>}
          <span style={{ flex: 1 }} />
          {puedeEditar && <button className="ll-btn-borde" onClick={editar}>Editar</button>}
        </div>
        <div>
          <Rotulo>COSTOS</Rotulo>
          <Ficha filas={[["Precio por licencia", [p.precio_usd != null && `USD ${num(p.precio_usd, 2)}`, p.precio_ars != null && `ARS ${num(p.precio_ars, 2)}`].filter(Boolean).join(" · ") + (p.sin_precio ? "Sin cargar" : ` (${p.periodo})`)],
            ["Costo mensual", montos(p.costo_mensual)], ["Costo anual", montos(p.costo_anual)],
            ["Sin asignar por mes", Object.keys(p.costo_sin_asignar_mensual).length ? `${montos(p.costo_sin_asignar_mensual)} (${p.libres} libres)` : ""],
            ["Licencias", p.ilimitado ? "Ilimitado" : `${p.asignadas} en uso de ${p.cupo ?? "—"} contratadas` + (p.compartidas ? ` · ${p.compartidas} compartidas` : "") + (p.cuentas_equipo ? ` · ${p.cuentas_equipo} cuentas de equipo` : "")],
            ["Renovación", p.fecha_renovacion ? `${fmtFecha(p.fecha_renovacion)} (${p.renovacion_dias} días)` : ""],
            ["Contrato / factura", p.contrato], ["Notas", p.notas]]} />
        </div>
        <div>
          <Rotulo>ASIGNADAS ({activas.length})</Rotulo>
          {activas.length ? <div className="ll-tabla-wrap"><table className="ll-tabla ll-tabla-compacta" style={{ minWidth: 0, width: "100%" }}>
            <thead><tr><th>PRINCIPAL</th><th>SEGUNDO USUARIO</th><th>% · CENTRO DE COSTO</th>{puedeEditar && <th />}</tr></thead>
            <tbody>{activas.map((a) => (
              <tr key={a.id} style={a.duplicada ? { opacity: 0.6 } : undefined}>
                <td><div style={{ fontSize: 13 }}>{puedeEditar
                  ? <CeldaEditable valor={a.nombre || ""} tipo="text" ancho={170} placeholder="nombre" onGuardar={(v) => guardarReparto(a.id, { nombre: v || "" })} />
                  : (a.nombre || a.persona)}{a.deshabilitada && <span style={{ color: "var(--ll-rosa)", fontSize: 11.5, marginLeft: 8 }}>{a.de_baja ? "de baja" : "deshabilitada"}</span>}</div>
                  <div className="tenue" style={{ fontSize: 11.5, wordBreak: "break-all" }}>{a.persona}</div>
                  {a.duplicada && <div style={{ fontSize: 11.5, color: "var(--ll-ambar)" }}>Usa la licencia de otra persona como segundo usuario: no suma</div>}</td>
                <td><div style={{ display: "flex", flexDirection: "column", gap: 4 }}>
                  <CeldaEditable valor={a.secundario || ""} tipo="text" ancho={150} placeholder="mail o usuario" deshabilitada={!puedeEditar}
                    onGuardar={(v) => guardarReparto(a.id, { secundario: v || "" })} />
                  {a.secundario && <CeldaEditable valor={a.secundario_nombre || ""} tipo="text" ancho={150} placeholder="nombre"
                    deshabilitada={!puedeEditar} onGuardar={(v) => guardarReparto(a.id, { secundario_nombre: v || "" })} />}</div></td>
                <td><div style={{ display: "flex", flexDirection: "column", gap: 4 }}>
                  <div style={{ display: "flex", alignItems: "center", gap: 6 }}>
                    {a.secundario ? <CeldaEditable valor={a.porcentaje_principal} ancho={58} max={100} placeholder="50" deshabilitada={!puedeEditar}
                      onGuardar={(v) => guardarReparto(a.id, { porcentaje_principal: v })} /> : <span className="tenue mono">100 %</span>}
                    {a.secundario && <span className="tenue" style={{ fontSize: 11 }}>{a.porcentaje_efectivo} / {100 - a.porcentaje_efectivo}</span>}
                  </div>
                  <CeldaEditable valor={a.centro_asignacion || ""} tipo="text" ancho={150} lista="ll-centros-costo"
                    placeholder={a.centro_costo !== "sin dato" ? a.centro_costo : "el de la persona"} deshabilitada={!puedeEditar}
                    onGuardar={(v) => guardarReparto(a.id, { centro_costo: v || "" })} /></div></td>
                {puedeEditar && <td style={{ textAlign: "right" }}><button className="ll-btn-borde ll-btn-chico" onClick={() => liberar(a.id)}>Liberar</button></td>}
              </tr>))}</tbody>
          </table><DatalistCentros /></div> : <div className="tenue" style={{ fontSize: 13 }}>{p.cuentas && p.cuentas.length ? "Sin personas asignadas: se usa por cuentas de equipo (abajo)." : "Nadie tiene este producto todavía."}</div>}
          {activas.length > 0 && <div className="tenue" style={{ fontSize: 11.5, marginTop: 6 }}>Una licencia puede usarla una segunda persona: el costo se reparte según el %
            (vacío = 50/50). El centro de costo de la asignación manda sobre el de cada persona. Ninguna importación pisa estos datos.</div>}
          {puedeEditar && <div style={{ display: "flex", gap: 8, marginTop: 10, flexWrap: "wrap" }}>
            <input className="ll-input" style={{ flex: "2 1 180px" }} placeholder="mail de la persona" value={nueva.persona} onChange={(e) => setNueva({ ...nueva, persona: e.target.value })} />
            <input className="ll-input" style={{ flex: "1 1 140px" }} placeholder="nombre (opcional)" value={nueva.nombre} onChange={(e) => setNueva({ ...nueva, nombre: e.target.value })} />
            <button className="ll-btn-primario" disabled={!nueva.persona.trim()} onClick={asignar}>Asignar</button>
          </div>}
          {EXTERNO(p.origen) && <div className="tenue" style={{ fontSize: 11.5, marginTop: 8 }}>Viene de {ORIGEN[p.origen]}: lo que cambies acá se mantiene,
            pero si volvés a importar, la importación vuelve a cargar a quien siga figurando allá.</div>}
        </div>
        {p.cuentas && p.cuentas.length > 0 && <div>
          <Rotulo>CUENTAS DE EQUIPO ({p.cuentas.filter((c) => c.activo).length})</Rotulo>
          <div className="ll-tabla-wrap"><table className="ll-tabla ll-tabla-compacta" style={{ minWidth: 0, width: "100%" }}>
            <thead><tr><th>CUENTA</th><th>UNIDAD</th><th>RESPONSABLE</th></tr></thead>
            <tbody>{p.cuentas.map((c) => (
              <tr key={c.id} style={c.activo ? undefined : { opacity: 0.5 }}>
                <td><div className="mono" style={{ fontSize: 12.5 }}>{c.numero}</div><div className="tenue" style={{ fontSize: 11.5, wordBreak: "break-all" }}>{c.email}</div></td>
                <td>{c.unidad}{!c.activo && <span className="tenue" style={{ fontSize: 11.5, marginLeft: 6 }}>(baja)</span>}</td>
                <td>{c.responsable}{c.lider && <div className="tenue" style={{ fontSize: 11.5 }}>Líder: {c.lider}</div>}</td></tr>))}
            </tbody></table></div>
          <div className="tenue" style={{ fontSize: 11.5, marginTop: 6 }}>Se editan en la pestaña Cuentas de equipo.</div>
        </div>}
        {p.costos_periodo && p.costos_periodo.length > 0 && <div>
          <Rotulo>COSTO REAL POR MES</Rotulo>
          <Ficha filas={p.costos_periodo.map((x) => [x.periodo + (x.workspace ? " · " + x.workspace : ""), `${x.moneda} ${num(x.monto, 2)} · ${x.origen === "api" ? "API" : "manual"}`])} />
        </div>}
        {liberadas.length > 0 && <div>
          <Rotulo>HISTORIAL (LIBERADAS)</Rotulo>
          {liberadas.map((a) => <div key={a.id} className="tenue" style={{ fontSize: 12.5, padding: "4px 0" }}>{a.nombre || a.persona} · {fmtFecha(a.desde)} → {fmtFecha(a.hasta)}</div>)}
        </div>}
      </>)}
    </Drawer>
  );
}

// ---------------------------------------------------------------- ficha de persona
function FichaPersona({ p, puedeEditar, avisar, onCerrar, onCambio, verEquipo }) {
  if (!p) return null;
  async function cuentaAd(e) {
    try { await pedir(URL + "/personas/" + encodeURIComponent(p.persona), json("PUT", { cuenta_ad: e.target.value })); onCambio && onCambio(); }
    catch (err) { avisar && avisar(err.message); }
  }
  return (
    <Drawer abierto onCerrar={onCerrar} ancho>
      <div className="ll-drawer-cab">
        <div style={{ minWidth: 0 }}>
          <div style={{ fontSize: 20, fontWeight: 600, color: "var(--accent)" }}>{p.nombre || p.persona}</div>
          <div style={{ fontSize: 12.5, color: "var(--ll-dim)", marginTop: 4 }}>{[p.persona, p.sede].filter(Boolean).join(" · ")}</div>
        </div>
        <button className="ll-cerrar" onClick={onCerrar} aria-label="Cerrar">✕</button>
      </div>
      <div>
        <Rotulo>LICENCIAS</Rotulo>
        <Ficha filas={p.productos.map((x) => [x.producto + (x.fraccion < 1 ? " (compartida)" : ""), `${x.proveedor} · ${montos(x.mensual_unitario)} por mes${x.detalle ? " · " + x.detalle : ""}`])} />
        <div style={{ fontSize: 13, marginTop: 8 }}>Costo: <b className="mono">{montos(p.costo_mensual)}</b> por mes · <span className="mono">{montos(p.costo_anual)}</span> por año</div>
      </div>
      <div>
        <Rotulo>NÓMINA Y CUENTA</Rotulo>
        <Ficha filas={[["Legajo", p.legajo], ["Centro de costo", p.centro_costo], ["Área", p.area], ["Categoría", p.categoria],
          ["Estado en la nómina", p.estado_nomina === "baja" ? "De baja" : p.estado_nomina === "activo" ? "Activo" : ""], ["En Adobe", p.estado_externo]]} />
        <label className="ll-campo" style={{ marginTop: 10 }}><span>CUENTA DE ACTIVE DIRECTORY</span>
          <select className="ll-select" value={p.cuenta_ad} onChange={cuentaAd} disabled={!puedeEditar}>
            <option value="desconocida">Sin dato</option><option value="activa">Activa</option><option value="deshabilitada">Deshabilitada</option>
          </select></label>
      </div>
      <div>
        <Rotulo>EQUIPOS EN ATLAS</Rotulo>
        {p.equipos.length ? <div style={{ display: "flex", gap: 8, flexWrap: "wrap" }}>{p.equipos.map((e) =>
          <button key={e.id} className="ll-btn-borde" onClick={() => verEquipo(e.id)}>{e.nombre} · {e.tipo}</button>)}</div>
          : <div className="tenue" style={{ fontSize: 13 }}>Ningún equipo de Atlas tiene a esta persona como usuario.</div>}
      </div>
    </Drawer>
  );
}

// ---------------------------------------------------------------- altas
function NuevoProducto({ onCerrar, onCreado, avisar }) {
  const [d, setD] = useState({ proveedor: "Anthropic", producto: "", plan: "", cupo: "", precio_usd: "", precio_ars: "", periodo: "mensual", fecha_renovacion: "" });
  const set = (k) => (e) => setD({ ...d, [k]: e.target.value });
  const n = (v) => (v === "" ? null : Number(v));
  async function crear() {
    try {
      const p = await pedir(URL + "/productos", json("POST", { proveedor: d.proveedor, producto: d.producto, plan: d.plan, cupo: n(d.cupo),
        precio_usd: n(d.precio_usd), precio_ars: n(d.precio_ars), periodo: d.periodo, fecha_renovacion: d.fecha_renovacion || null }));
      avisar && avisar("Producto creado"); onCreado(p.id);
    } catch (e) { avisar && avisar(e.message); }
  }
  return (
    <Modal titulo="Nuevo producto" onCerrar={onCerrar}
      pie={<><button className="ll-btn-borde" onClick={onCerrar}>Cancelar</button><button className="ll-btn-primario" disabled={!d.producto.trim()} onClick={crear}>Crear</button></>}>
      <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: 12 }}>
        <label className="ll-campo"><span>PROVEEDOR</span><select className="ll-select" value={d.proveedor} onChange={set("proveedor")}>{PROVEEDORES.map((x) => <option key={x}>{x}</option>)}</select></label>
        <label className="ll-campo"><span>PRODUCTO</span><input className="ll-input" value={d.producto} onChange={set("producto")} placeholder="Microsoft 365 Business, Dropbox Plus…" autoFocus /></label>
        <label className="ll-campo"><span>PLAN</span><input className="ll-input" value={d.plan} onChange={set("plan")} /></label>
        <label className="ll-campo"><span>CUPO CONTRATADO</span><input className="ll-input mono" type="number" min="0" value={d.cupo} onChange={set("cupo")} /></label>
        <label className="ll-campo"><span>PRECIO POR LICENCIA · USD</span><input className="ll-input mono" type="number" min="0" step="0.01" value={d.precio_usd} onChange={set("precio_usd")} /></label>
        <label className="ll-campo"><span>PRECIO POR LICENCIA · ARS</span><input className="ll-input mono" type="number" min="0" step="0.01" value={d.precio_ars} onChange={set("precio_ars")} /></label>
        <label className="ll-campo"><span>PERÍODO DEL PRECIO</span><select className="ll-select" value={d.periodo} onChange={set("periodo")}><option value="mensual">Mensual</option><option value="anual">Anual</option></select></label>
        <label className="ll-campo"><span>RENOVACIÓN</span><input className="ll-input" type="date" value={d.fecha_renovacion} onChange={set("fecha_renovacion")} /></label>
      </div>
    </Modal>
  );
}

function ImportarMiembros({ productos, onCerrar, onListo, avisar }) {
  const [fuente, setFuente] = useState("miembros");
  const [productoId, setProductoId] = useState("");
  const archivo = useRef(null);
  async function subir(e) {
    const a = e.target.files && e.target.files[0];
    e.target.value = "";
    if (!a) return;
    const fd = new FormData(); fd.append("archivo", a);
    if (fuente === "miembros" && productoId) fd.append("producto_id", productoId);
    const ruta = { miembros: "/importar", adobe: "/importar-adobe", usermanager: "/importar-usermanager", cuentas: "/importar-cuentas-equipo" }[fuente];
    try {
      const d = await pedir(URL + ruta, { method: "POST", body: fd });
      if (fuente === "cuentas") {
        avisar && avisar(`Cuentas de equipo: ${d.cuentas} cargadas (${d.altas} nuevas${d.inactivas ? `, ${d.inactivas} inactivas` : ""})` +
          (d.sin_producto && d.sin_producto.length ? ` · sin producto: ${d.sin_producto.join(", ")}` : ""));
        onListo(); return;
      }
      const n = d.asignaciones_nuevas ?? d.altas ?? 0;
      avisar && avisar(`Importado: ${n} asignaciones nuevas${d.liberadas ? `, ${d.liberadas} liberadas` : ""}${d.ya_estaban ? `, ${d.ya_estaban} ya estaban` : ""}`);
      onListo();
    } catch (err) { avisar && avisar("No se pudo importar: " + err.message); }
  }
  return (
    <Modal titulo="Importar miembros" onCerrar={onCerrar}
      pie={<><button className="ll-btn-borde" onClick={onCerrar}>Cancelar</button><button className="ll-btn-primario" onClick={() => archivo.current && archivo.current.click()}>Elegir archivo…</button></>}>
      <label className="ll-campo"><span>QUÉ ARCHIVO ES</span>
        <select className="ll-select" value={fuente} onChange={(e) => setFuente(e.target.value)}>
          <option value="miembros">CSV de miembros (Claude, Adobe u otro) o genérico</option>
          <option value="adobe">Exportación de usuarios de la Admin Console de Adobe</option>
          <option value="cuentas">Cuentas de equipo de Claude (planilla por unidad)</option>
          <option value="usermanager">Exportación del UserManager (JSON)</option>
        </select></label>
      {fuente === "miembros" && <>
        <label className="ll-campo" style={{ marginTop: 12 }}><span>PRODUCTO (SI EL ARCHIVO NO LO TRAE)</span>
          <select className="ll-select" value={productoId} onChange={(e) => setProductoId(e.target.value)}>
            <option value="">Que lo diga cada fila (columna producto / seat tier)</option>
            {productos.filter((p) => !EXTERNO(p.origen)).map((p) => <option key={p.id} value={p.id}>{p.proveedor} · {p.producto}</option>)}
          </select></label>
        <div className="tenue" style={{ fontSize: 12, marginTop: 10, lineHeight: 1.6 }}>Columnas por nombre (en inglés o castellano): <b>email</b> (obligatoria), nombre, producto / seat tier, proveedor.
          Claude Team: exportá los miembros desde la consola de administración y elegí el producto. Quien ya tenga el producto no se duplica.</div>
      </>}
      {fuente === "adobe" && <ol style={{ margin: "12px 0 0", paddingLeft: 20, fontSize: 13, lineHeight: 1.7 }}>
        <li><b>adminconsole.adobe.com</b> → <b>Usuarios</b> → <b>Usuarios</b>.</li>
        <li>Menú <b>“…”</b> → <b>Exportar lista de usuarios a CSV</b> y elegí ese archivo.</li>
        <li>Quien ya no figure con un producto queda como liberado; los costos no se tocan.</li></ol>}
      {fuente === "cuentas" && <div className="tenue" style={{ fontSize: 12, marginTop: 12, lineHeight: 1.6 }}>
        Planilla copiada de Excel a un .txt (tabulado) o CSV: #, unidad, líder, responsable, <b>mail de la cuenta</b> y tipo
        (Standard / Premium / MAX x20). Es la lista completa: las cuentas que no vengan quedan inactivas. No hace falta cargar además
        el CSV de miembros de esas cuentas (si ya estaba, no se cuenta dos veces).</div>}
      {fuente === "usermanager" && <div className="tenue" style={{ fontSize: 12, marginTop: 12, lineHeight: 1.6 }}>
        JSON generado con <span className="mono">herramientas/licencias/exportar_usermanager.py</span> (lee la base del UserManager en solo lectura).
        Es idempotente y no pisa los costos cargados en Atlas.</div>}
      <input ref={archivo} type="file" accept={fuente === "usermanager" ? ".json,application/json" : fuente === "cuentas" ? ".txt,.tsv,.csv,text/plain,text/csv" : ".csv,text/csv"} style={{ display: "none" }} onChange={subir} />
    </Modal>
  );
}

const TIPOS_CUENTA = ["Standard", "Premium", "Max 20x"];
// "MAX x20" / "premium" (como vienen en la planilla) -> el tipo del desplegable
function tipoCuenta(t) {
  const s = String(t || "").toLowerCase().replace(/\W/g, "");
  if (!s) return "Standard";
  if (s.startsWith("max") || s.includes("x20")) return "Max 20x";
  return TIPOS_CUENTA.find((x) => x.toLowerCase() === s) || t;
}

// Alta / edición / baja de una cuenta de equipo de Claude (una cuenta por unidad = una licencia).
function EditarCuenta({ cuenta, onCerrar, onListo, avisar }) {
  const nueva = !cuenta.id;
  const [d, setD] = useState({ numero: cuenta.numero || "", unidad: cuenta.unidad || "", lider: cuenta.lider || "",
    responsable: cuenta.responsable || "", email: cuenta.email || "",
    tipo: tipoCuenta(cuenta.tipo) });
  const set = (k) => (e) => setD({ ...d, [k]: e.target.value });
  async function enviar(cuerpo, aviso) {
    try {
      await pedir(URL + "/cuentas-equipo" + (nueva ? "" : "/" + cuenta.id), json(nueva ? "POST" : "PUT", cuerpo));
      avisar && avisar(aviso); onListo();
    } catch (e) { avisar && avisar(e.message); }
  }
  const tipos = TIPOS_CUENTA.includes(d.tipo) ? TIPOS_CUENTA : [...TIPOS_CUENTA, d.tipo];
  return (
    <Modal titulo={nueva ? "Nueva cuenta de equipo" : "Cuenta " + (cuenta.numero || cuenta.email)} onCerrar={onCerrar}
      pie={<>
        {!nueva && <button className="ll-btn-borde" style={{ marginRight: "auto" }}
          onClick={() => enviar({ activo: !cuenta.activo }, cuenta.activo ? "Cuenta dada de baja" : "Cuenta reactivada")}>
          {cuenta.activo ? "Dar de baja" : "Reactivar"}</button>}
        <button className="ll-btn-borde" onClick={onCerrar}>Cancelar</button>
        <button className="ll-btn-primario" disabled={!d.unidad.trim() || !d.email.trim()}
          onClick={() => enviar(d, nueva ? "Cuenta creada" : "Cuenta guardada")}>Guardar</button></>}>
      <div style={{ display: "grid", gridTemplateColumns: "110px 1fr", gap: 12 }}>
        <label className="ll-campo"><span>#</span><input className="ll-input" value={d.numero} onChange={set("numero")} placeholder="#38" /></label>
        <label className="ll-campo"><span>UNIDAD DE NEGOCIO / ÁREA</span><input className="ll-input" value={d.unidad} onChange={set("unidad")} /></label>
        <label className="ll-campo" style={{ gridColumn: "1 / -1" }}><span>MAIL DE LA CUENTA</span>
          <input className="ll-input" type="email" value={d.email} onChange={set("email")} placeholder="ia-area@llyasoc.com" /></label>
        <label className="ll-campo" style={{ gridColumn: "1 / -1" }}><span>RESPONSABLE</span><input className="ll-input" value={d.responsable} onChange={set("responsable")} /></label>
        <label className="ll-campo" style={{ gridColumn: "1 / -1" }}><span>LÍDER</span><input className="ll-input" value={d.lider} onChange={set("lider")} /></label>
        <label className="ll-campo" style={{ gridColumn: "1 / -1" }}><span>TIPO DE LICENCIA</span>
          <select className="ll-select" value={d.tipo} onChange={set("tipo")}>{tipos.map((t) => <option key={t}>{t}</option>)}</select></label>
      </div>
      {!nueva && !cuenta.activo && <div className="tenue" style={{ fontSize: 12, marginTop: 12 }}>Esta cuenta está dada de baja: no suma licencias ni costo.</div>}
    </Modal>
  );
}

function NuevoCosto({ productos, onCerrar, onListo, avisar }) {
  const [d, setD] = useState({ producto_id: productos[0] ? productos[0].id : "", periodo: mesActual(), moneda: "USD", monto: "", cantidad: "", workspace: "" });
  const set = (k) => (e) => setD({ ...d, [k]: e.target.value });
  async function guardar() {
    try {
      await pedir(URL + "/costos", json("POST", { costos: [{ producto_id: d.producto_id, periodo: d.periodo, moneda: d.moneda, monto: Number(d.monto),
        cantidad: d.cantidad === "" ? null : Number(d.cantidad), workspace: d.workspace }] }));
      avisar && avisar("Costo cargado"); onListo();
    } catch (e) { avisar && avisar(e.message); }
  }
  return (
    <Modal titulo="Costo real del mes (factura)" onCerrar={onCerrar}
      pie={<><button className="ll-btn-borde" onClick={onCerrar}>Cancelar</button><button className="ll-btn-primario" disabled={!d.producto_id || d.monto === ""} onClick={guardar}>Guardar</button></>}>
      <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: 12 }}>
        <label className="ll-campo" style={{ gridColumn: "1 / -1" }}><span>PRODUCTO</span>
          <select className="ll-select" value={d.producto_id} onChange={set("producto_id")}>{productos.map((p) => <option key={p.id} value={p.id}>{p.proveedor} · {p.producto}</option>)}</select></label>
        <label className="ll-campo"><span>MES</span><input className="ll-input mono" type="month" value={d.periodo} onChange={set("periodo")} /></label>
        <label className="ll-campo"><span>MONEDA</span><select className="ll-select" value={d.moneda} onChange={set("moneda")}><option>USD</option><option>ARS</option></select></label>
        <label className="ll-campo"><span>MONTO</span><input className="ll-input mono" type="number" min="0" step="0.01" value={d.monto} onChange={set("monto")} /></label>
        <label className="ll-campo"><span>LICENCIAS FACTURADAS</span><input className="ll-input mono" type="number" min="0" value={d.cantidad} onChange={set("cantidad")} /></label>
        <label className="ll-campo" style={{ gridColumn: "1 / -1" }}><span>WORKSPACE / CUENTA (OPCIONAL)</span><input className="ll-input" value={d.workspace} onChange={set("workspace")} /></label>
      </div>
    </Modal>
  );
}
