// Monitores.jsx — Subseccion de Activos: monitores externos que informa el agente de Atlas (marca, serie, pulgadas,
// conexion y año de fabricacion, del EDID) y la PC donde estan conectados. Las tarjetas filtran la tabla; un clic
// en la fila abre la ficha del monitor y el nombre de la PC abre la ficha de la PC. Datos de /api/monitores.
import { useCallback, useEffect, useMemo, useState } from "react";
import { apiFetch } from "../api";
import { SEDES, fmtFechaHora } from "../ui";

const TAMANOS = ["Hasta 21\"", "22\" a 24\"", "25\" a 27\"", "28\" o más", "Sin dato"];
const tamano = (p) => (!p ? "Sin dato" : p < 21.5 ? TAMANOS[0] : p < 25 ? TAMANOS[1] : p < 28 ? TAMANOS[2] : TAMANOS[3]);

// "HP" + "HP E24 G4" -> "HP E24 G4" (muchos EDID ya traen la marca en el modelo)
export const conMarca = (marca, modelo) => {
  const b = (marca || "").trim(), m = (modelo || "").trim();
  return b && m.toUpperCase().startsWith(b.toUpperCase()) ? m : (b + " " + m).trim();
};
export const textoFabricado = (m) => (m.anio ? (m.semana ? `sem. ${m.semana} / ${m.anio}` : String(m.anio)) : "—");

export default function Monitores({ assets, verFicha }) {
  const [datos, setDatos] = useState({ monitores: [], resumen: {} });
  const [cargando, setCargando] = useState(true);
  const [error, setError] = useState("");
  const [filtros, setFiltros] = useState({ q: "", sede: "", marca: "", tamano: "", conexion: "", tarjeta: "" });

  const cargar = useCallback(async () => {
    setCargando(true);
    try {
      const r = await apiFetch("/api/monitores");
      if (!r.ok) throw new Error("Error " + r.status);
      setDatos(await r.json());
      setError("");
    } catch (e) { setError(e.message); } finally { setCargando(false); }
  }, []);
  useEffect(() => { cargar(); }, [cargar]);

  const lista = datos.monitores;
  const marcas = useMemo(() => [...new Set(lista.map((m) => m.marca).filter(Boolean))].sort(), [lista]);
  const conexiones = useMemo(() => [...new Set(lista.map((m) => m.conexion).filter(Boolean))].sort(), [lista]);
  const filtradas = useMemo(() => {
    const q = filtros.q.trim().toLowerCase();
    return lista.filter((m) => (!q || [m.nombre, m.marca, m.modelo, m.serial, m.usuario, m.pc?.nombre].some((v) => String(v || "").toLowerCase().includes(q)))
      && (!filtros.sede || (m.sede || "").toLowerCase() === filtros.sede.toLowerCase())
      && (!filtros.marca || m.marca === filtros.marca)
      && (!filtros.tamano || tamano(m.pulgadas) === filtros.tamano)
      && (!filtros.conexion || m.conexion === filtros.conexion)
      && (filtros.tarjeta !== "sin_ver" || m.sin_ver)
      && (filtros.tarjeta !== "antiguos" || m.antiguo));
  }, [lista, filtros]);
  const f = (k) => (e) => setFiltros({ ...filtros, [k]: e.target.value });
  const abrir = (id) => { const a = assets.find((x) => x.id === id); if (a) verFicha(a); };
  const r = datos.resumen || {};
  const porTamano = r.por_tamano || {};

  const tarjetas = [
    ["", "Monitores", r.total, "var(--accent)"],
    ["sin_ver", "Sin ver conectados +30 días", r.sin_ver, "var(--ll-ambar)"],
    ["antiguos", "Fabricados hace más de 7 años", r.antiguos, "var(--ll-rosa)"],
  ];

  return (
    <div>
      <div style={{ display: "grid", gridTemplateColumns: "repeat(auto-fill, minmax(150px, 1fr))", gap: 12, marginBottom: 20 }}>
        {tarjetas.map(([k, rotulo, n, color]) => {
          const activa = k && filtros.tarjeta === k;
          return (
            <button key={rotulo} type="button" className="ll-card hover" aria-pressed={!!activa}
              onClick={() => setFiltros({ ...filtros, tarjeta: activa ? "" : k })}
              style={{ textAlign: "left", padding: "14px 16px", cursor: "pointer", color: "inherit", font: "inherit",
                borderColor: activa ? color : undefined, boxShadow: activa ? `0 0 0 1px ${color}` : undefined }}>
              <div className="mono" style={{ fontSize: 24, fontWeight: 600, color: n ? color : "var(--ll-dim)" }}>{n ?? 0}</div>
              <div style={{ fontSize: 12.5, color: "var(--ll-text-2)", marginTop: 4 }}>{rotulo}</div>
            </button>
          );
        })}
        <div className="ll-card" style={{ padding: "12px 16px", gridColumn: "span 2", minWidth: 0 }}>
          <div style={{ fontSize: 12, color: "var(--ll-dim)", marginBottom: 6 }}>Por tamaño</div>
          <div style={{ display: "flex", gap: 6, flexWrap: "wrap" }}>
            {TAMANOS.filter((t) => porTamano[t]).map((t) => (
              <button key={t} type="button" className={"ll-chip" + (filtros.tamano === t ? " acento" : "")} style={{ border: 0, cursor: "pointer", font: "inherit", fontSize: 11.5 }}
                onClick={() => setFiltros({ ...filtros, tamano: filtros.tamano === t ? "" : t })}>{t} · {porTamano[t]}</button>
            ))}
            {!Object.keys(porTamano).length && <span className="tenue" style={{ fontSize: 12 }}>—</span>}
          </div>
        </div>
      </div>

      <div className="ll-barra">
        <div className="ll-buscador">
          <span>⌕</span>
          <input className="ll-input" value={filtros.q} onChange={f("q")} placeholder="Buscar por modelo, serie, usuario o PC…" aria-label="Buscar monitores" />
        </div>
        <select className="ll-select" style={{ width: "auto" }} value={filtros.sede} onChange={f("sede")} aria-label="Sede">
          <option value="">Todas las sedes</option>
          {SEDES.map((s) => <option key={s}>{s}</option>)}
        </select>
        <select className="ll-select" style={{ width: "auto" }} value={filtros.marca} onChange={f("marca")} aria-label="Marca">
          <option value="">Todas las marcas</option>
          {marcas.map((m) => <option key={m}>{m}</option>)}
        </select>
        <select className="ll-select" style={{ width: "auto" }} value={filtros.tamano} onChange={f("tamano")} aria-label="Pulgadas">
          <option value="">Todos los tamaños</option>
          {TAMANOS.map((t) => <option key={t}>{t}</option>)}
        </select>
        <select className="ll-select" style={{ width: "auto" }} value={filtros.conexion} onChange={f("conexion")} aria-label="Conexión">
          <option value="">Toda conexión</option>
          {conexiones.map((c) => <option key={c}>{c}</option>)}
        </select>
        <span className="ll-contador">{filtradas.length} monitores</span>
      </div>

      {error && <div className="ll-vacio" style={{ color: "var(--ll-warn)" }}>No se pudieron cargar los monitores: {error}</div>}
      <div className="ll-card" style={{ overflow: "hidden" }}>
        <div className="ll-tabla-wrap">
          <table className="ll-tabla" style={{ minWidth: 1150 }}>
            <thead><tr>
              <th>MONITOR</th><th>SERIE</th><th>PULGADAS</th><th>CONEXIÓN</th><th>FABRICADO</th><th>CONECTADO A</th>
              <th>USUARIO</th><th>SEDE</th><th>VISTO</th>
            </tr></thead>
            <tbody>
              {filtradas.map((m) => (
                <tr key={m.id} className="click" onClick={() => abrir(m.id)}>
                  <td className="nombre">{conMarca(m.marca, m.modelo) || m.nombre}</td>
                  <td className="mono" style={{ fontSize: 12.5 }}>{m.serial || <span className="tenue">—</span>}</td>
                  <td className="mono">{m.pulgadas ? m.pulgadas + "\"" : <span className="tenue">—</span>}</td>
                  <td>{m.conexion ? <span className="ll-chip">{m.conexion}</span> : <span className="tenue">—</span>}</td>
                  <td className="mono" style={{ fontSize: 12.5, color: m.antiguo ? "var(--ll-rosa)" : undefined }}>{textoFabricado(m)}</td>
                  <td>{m.pc ? <a href="#" onClick={(e) => { e.preventDefault(); e.stopPropagation(); abrir(m.pc.id); }}>{m.pc.nombre}</a> : <span className="tenue">—</span>}</td>
                  <td>{m.usuario || <span className="tenue">—</span>}</td>
                  <td>{m.sede || <span className="tenue">—</span>}</td>
                  <td className="mono" style={{ fontSize: 12.5, color: m.sin_ver ? "var(--ll-ambar)" : "var(--ll-dim)" }}>{m.visto ? fmtFechaHora(m.visto) : "—"}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
        {!cargando && !filtradas.length && <div className="ll-vacio">{lista.length ? "Sin monitores que coincidan con los filtros." : "Todavía no hay monitores: los informa el agente de Atlas desde la versión que releva los monitores."}</div>}
        {cargando && !lista.length && <div className="ll-vacio">Cargando monitores…</div>}
      </div>
    </div>
  );
}
