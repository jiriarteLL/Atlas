// Garantias.jsx — Subseccion de Activos: garantia de cada equipo. Lenovo se consulta sola desde su pagina de soporte
// (fin, inicio, cobertura y extensiones); HP y otros se cargan a mano o con un CSV. Las tarjetas filtran la tabla y
// un clic en la fila abre la ficha del activo. Datos de /api/garantias.
import { useCallback, useEffect, useMemo, useRef, useState } from "react";
import { apiFetch } from "../api";
import { SEDES, fmtFechaHora } from "../ui";
import { fmtFecha } from "./Salud";

const URL = "/api/garantias";

export async function pedir(url, opciones) {
  const r = await apiFetch(url, opciones);
  const d = await r.json().catch(() => ({}));
  if (!r.ok) {
    const det = Array.isArray(d.detail) ? d.detail.map((x) => x.msg).join(" · ") : d.detail;
    throw new Error(typeof det === "string" ? det : "Error " + r.status);
  }
  return d;
}

// vencida: rosa · vence en 90 dias: ambar · vigente: verde
export const colorDias = (d) => (d === null || d === undefined ? "var(--ll-dim)" : d < 0 ? "var(--ll-rosa)" : d <= 90 ? "var(--ll-ambar)" : "var(--ll-verde)");
export const textoDias = (d) => (d === null || d === undefined ? "—" : d < 0 ? `vencida hace ${-d} d` : d === 0 ? "vence hoy" : `${d} d`);
const FUENTES = { lenovo: "Lenovo", manual: "Manual", ficha: "Ficha" };

export function ChipEntrega({ g }) {
  if (!g.entrega_texto) return null;
  return <span className={"ll-chip" + (g.entrega === "on_site" ? " acento" : "")} style={{ fontSize: 11 }}>{g.entrega_texto}</span>;
}

const TARJETAS = [
  ["vigentes", "Vigentes", "var(--ll-verde)", (g) => g.dias !== null && g.dias >= 0],
  ["vencen_90", "Vencen en 90 días", "var(--ll-ambar)", (g) => g.dias !== null && g.dias >= 0 && g.dias <= 90],
  ["vencidas", "Vencidas", "var(--ll-rosa)", (g) => g.dias !== null && g.dias < 0],
  ["sin_dato", "Sin dato", "var(--ll-muted)", (g) => g.dias === null],
];

export default function Garantias({ assets, verFicha, puedeEditar, avisar }) {
  const [lista, setLista] = useState([]);
  const [cargando, setCargando] = useState(true);
  const [error, setError] = useState("");
  const [corrida, setCorrida] = useState(null);
  const [importando, setImportando] = useState(false);
  const [resultadoCsv, setResultadoCsv] = useState(null);
  const [filtros, setFiltros] = useState({ q: "", sede: "", marca: "", tipo: "", fuente: "", tarjeta: "" });
  const archivo = useRef(null);

  const cargar = useCallback(async () => {
    setCargando(true);
    try { setLista(await pedir(URL)); setError(""); } catch (e) { setError(e.message); } finally { setCargando(false); }
  }, []);
  const verCorrida = useCallback(async () => {
    try { const c = await pedir(URL + "/estado-actualizacion"); setCorrida(c); return c; } catch { return null; }
  }, []);
  useEffect(() => { cargar(); verCorrida(); }, [cargar, verCorrida]);

  // Mientras corre la actualizacion se consulta el estado cada 5 s y al terminar se recarga la lista
  const corriendo = corrida && (corrida.corriendo || corrida.pedida);
  useEffect(() => {
    if (!corriendo) return undefined;
    const t = setInterval(async () => {
      const c = await verCorrida();
      if (c && !c.corriendo && !c.pedida) cargar();
    }, 5000);
    return () => clearInterval(t);
  }, [corriendo, verCorrida, cargar]);

  async function actualizar() {
    try {
      const r = await pedir(URL + "/actualizar", { method: "POST" });
      avisar && avisar(r.ya_corriendo ? "Ya hay una actualización en curso" : "Actualización desde Lenovo en curso");
      verCorrida();
    } catch (e) { alert(e.message); }
  }

  async function importar(e) {
    const a = e.target.files[0];
    e.target.value = "";
    if (!a) return;
    setImportando(true);
    try {
      const fd = new FormData();
      fd.append("archivo", a);
      const r = await pedir(URL + "/importar", { method: "POST", body: fd });
      setResultadoCsv(r);
      avisar && avisar(`Garantías importadas: ${r.actualizados}`);
      await cargar();
    } catch (err) { alert(err.message); } finally { setImportando(false); }
  }

  async function bajarPlantilla() {
    const r = await apiFetch(URL + "/plantilla.csv");
    if (!r.ok) return;
    const u = window.URL.createObjectURL(await r.blob());
    const l = document.createElement("a");
    l.href = u; l.download = "garantias-plantilla.csv"; l.click();
    window.URL.revokeObjectURL(u);
  }

  const marcas = useMemo(() => [...new Set(lista.map((g) => (g.marca || "").trim().toUpperCase()).filter(Boolean))].sort(), [lista]);
  const tipos = useMemo(() => [...new Set(lista.map((g) => g.tipo).filter(Boolean))].sort(), [lista]);
  const base = useMemo(() => lista.filter((g) =>
    (!filtros.sede || (g.sede || "").toLowerCase() === filtros.sede.toLowerCase())
    && (!filtros.marca || (g.marca || "").trim().toUpperCase() === filtros.marca)
    && (!filtros.tipo || g.tipo === filtros.tipo)
    && (!filtros.fuente || (filtros.fuente === "-" ? !g.fuente : g.fuente === filtros.fuente))), [lista, filtros]);
  const cuentas = useMemo(() => Object.fromEntries(TARJETAS.map(([k, , , c]) => [k, base.filter(c).length])), [base]);
  const porMarca = useMemo(() => {
    const m = {};
    base.forEach((g) => {
      const k = (g.marca || "Sin marca").trim().toUpperCase();
      m[k] = m[k] || { total: 0, vigentes: 0 };
      m[k].total += 1;
      if (g.dias !== null && g.dias >= 0) m[k].vigentes += 1;
    });
    return Object.entries(m).sort((a, b) => b[1].total - a[1].total).slice(0, 6);
  }, [base]);
  const filtradas = useMemo(() => {
    const q = filtros.q.trim().toLowerCase();
    const cond = TARJETAS.find(([k]) => k === filtros.tarjeta)?.[3];
    return base.filter((g) => (!cond || cond(g))
      && (!q || [g.nombre, g.serial, g.modelo, g.usuario, g.cobertura, g.contrato, g.proveedor].some((v) => String(v || "").toLowerCase().includes(q))));
  }, [base, filtros]);
  const f = (k) => (e) => setFiltros({ ...filtros, [k]: e.target.value });
  const abrir = (id) => { const a = assets.find((x) => x.id === id); if (a) verFicha(a); };

  return (
    <div>
      <div style={{ display: "grid", gridTemplateColumns: "repeat(auto-fill, minmax(150px, 1fr))", gap: 12, marginBottom: 20 }}>
        {TARJETAS.map(([k, rotulo, color]) => {
          const activa = filtros.tarjeta === k;
          return (
            <button key={k} type="button" className="ll-card hover" aria-pressed={activa}
              onClick={() => setFiltros({ ...filtros, tarjeta: activa ? "" : k })}
              style={{ textAlign: "left", padding: "14px 16px", cursor: "pointer", color: "inherit", font: "inherit",
                borderColor: activa ? color : undefined, boxShadow: activa ? `0 0 0 1px ${color}` : undefined }}>
              <div className="mono" style={{ fontSize: 24, fontWeight: 600, color: cuentas[k] ? color : "var(--ll-dim)" }}>{cuentas[k] ?? 0}</div>
              <div style={{ fontSize: 12.5, color: "var(--ll-text-2)", marginTop: 4 }}>{rotulo}</div>
            </button>
          );
        })}
        <div className="ll-card" style={{ padding: "12px 16px", gridColumn: "span 2", minWidth: 0 }}>
          <div style={{ fontSize: 12, color: "var(--ll-dim)", marginBottom: 6 }}>Vigentes por marca</div>
          <div style={{ display: "flex", gap: 6, flexWrap: "wrap" }}>
            {porMarca.map(([m, c]) => (
              <button key={m} type="button" className={"ll-chip" + (filtros.marca === m ? " acento" : "")} style={{ border: 0, cursor: "pointer", font: "inherit", fontSize: 11.5 }}
                onClick={() => setFiltros({ ...filtros, marca: filtros.marca === m ? "" : m })}>{m} · {c.vigentes}/{c.total}</button>
            ))}
            {!porMarca.length && <span className="tenue" style={{ fontSize: 12 }}>—</span>}
          </div>
        </div>
      </div>

      <div className="ll-barra">
        <div className="ll-buscador">
          <span>⌕</span>
          <input className="ll-input" value={filtros.q} onChange={f("q")} placeholder="Buscar por equipo, serie, usuario o cobertura…" aria-label="Buscar garantías" />
        </div>
        <select className="ll-select" style={{ width: "auto" }} value={filtros.sede} onChange={f("sede")} aria-label="Sede">
          <option value="">Todas las sedes</option>
          {SEDES.map((s) => <option key={s}>{s}</option>)}
        </select>
        <select className="ll-select" style={{ width: "auto" }} value={filtros.marca} onChange={f("marca")} aria-label="Marca">
          <option value="">Todas las marcas</option>
          {marcas.map((m) => <option key={m}>{m}</option>)}
        </select>
        <select className="ll-select" style={{ width: "auto" }} value={filtros.tipo} onChange={f("tipo")} aria-label="Tipo de equipo">
          <option value="">Todos los tipos</option>
          {tipos.map((t) => <option key={t}>{t}</option>)}
        </select>
        <select className="ll-select" style={{ width: "auto" }} value={filtros.fuente} onChange={f("fuente")} aria-label="Fuente">
          <option value="">Toda fuente</option>
          <option value="lenovo">Lenovo (automática)</option>
          <option value="manual">Manual / CSV</option>
          <option value="-">Sin dato</option>
        </select>
        <span className="ll-contador">{filtradas.length} equipos</span>
      </div>

      <div style={{ display: "flex", alignItems: "center", gap: 10, flexWrap: "wrap", margin: "-4px 0 14px" }}>
        {puedeEditar && <button className="ll-btn-borde" disabled={!!corriendo} onClick={actualizar}>{corriendo ? "Actualizando desde Lenovo…" : "Actualizar desde Lenovo"}</button>}
        {puedeEditar && <>
          <button className="ll-btn-borde" disabled={importando} onClick={() => archivo.current?.click()}>{importando ? "Importando…" : "Importar CSV (HP y otros)"}</button>
          <input ref={archivo} type="file" accept=".csv,text/csv" style={{ display: "none" }} onChange={importar} />
          <button className="ll-btn-borde" onClick={bajarPlantilla}>Plantilla CSV</button>
        </>}
        <span className="tenue" style={{ fontSize: 12 }}>
          {corrida && (corriendo
            ? `Consultando a Lenovo: ${corrida.ok + corrida.errores} de ${corrida.pendientes}…`
            : corrida.fin ? `Última actualización: ${fmtFechaHora(corrida.fin)} · ${corrida.ok} ok, ${corrida.errores} sin dato${corrida.automatica ? " · automática cada 6 h" : " · automática apagada"}`
              : corrida.automatica ? "La actualización automática corre cada 6 h" : "Actualización automática apagada")}
          {corrida?.mensaje ? " · " + corrida.mensaje : ""}
        </span>
      </div>

      {resultadoCsv && <div className="ll-card" style={{ padding: "12px 16px", marginBottom: 14, fontSize: 12.5 }}>
        <div style={{ display: "flex", gap: 10 }}>
          <b style={{ color: "var(--ll-verde)" }}>{resultadoCsv.actualizados} actualizadas</b>
          {resultadoCsv.no_encontrados.length > 0 && <span style={{ color: "var(--ll-ambar)" }}>· {resultadoCsv.no_encontrados.length} series no encontradas</span>}
          {resultadoCsv.ambiguos.length > 0 && <span style={{ color: "var(--ll-ambar)" }}>· {resultadoCsv.ambiguos.length} series repetidas en Atlas</span>}
          {resultadoCsv.errores.length > 0 && <span style={{ color: "var(--ll-rosa)" }}>· {resultadoCsv.errores.length} filas con error</span>}
          <span style={{ flex: 1 }} />
          <button className="ll-cerrar" onClick={() => setResultadoCsv(null)} aria-label="Cerrar">✕</button>
        </div>
        {resultadoCsv.no_encontrados.length > 0 && <div className="tenue mono" style={{ marginTop: 6 }}>No encontradas: {resultadoCsv.no_encontrados.join(", ")}</div>}
        {resultadoCsv.errores.map((e) => <div key={e.fila} className="tenue" style={{ marginTop: 4 }}>Fila {e.fila}: {e.motivo}</div>)}
      </div>}

      {error && <div className="ll-vacio" style={{ color: "var(--ll-warn)" }}>No se pudieron cargar las garantías: {error}</div>}
      <div className="ll-card" style={{ overflow: "hidden" }}>
        <div className="ll-tabla-wrap">
          <table className="ll-tabla" style={{ minWidth: 1350 }}>
            <thead><tr>
              <th>EQUIPO</th><th>TIPO</th><th>MARCA / MODELO</th><th>SERIE</th><th>USUARIO</th><th>SEDE</th>
              <th>COBERTURA</th><th>INICIO</th><th>FIN</th><th>DÍAS</th><th>FUENTE</th><th>CONSULTADO</th>
            </tr></thead>
            <tbody>
              {filtradas.map((g) => (
                <tr key={g.id} className="click" onClick={() => abrir(g.id)}>
                  <td className="nombre">{g.nombre || g.serial}</td>
                  <td>{g.tipo || <span className="tenue">—</span>}</td>
                  <td>{[g.marca, g.modelo].filter(Boolean).join(" ") || <span className="tenue">—</span>}</td>
                  <td className="mono" style={{ fontSize: 12.5 }}>{g.serial || <span className="tenue">—</span>}</td>
                  <td>{g.usuario || <span className="tenue">—</span>}</td>
                  <td>{g.sede || <span className="tenue">—</span>}</td>
                  <td style={{ maxWidth: 240 }}>
                    {g.cobertura || (g.error ? <span className="tenue" title={g.error}>{g.error}</span> : <span className="tenue">—</span>)}
                    {g.entrega_texto && <div style={{ marginTop: 3 }}><ChipEntrega g={g} /></div>}
                  </td>
                  <td className="mono" style={{ fontSize: 12.5 }}>{g.inicio ? fmtFecha(g.inicio) : <span className="tenue">—</span>}</td>
                  <td className="mono" style={{ fontSize: 12.5 }}>{g.fin ? fmtFecha(g.fin) : <span className="tenue">—</span>}</td>
                  <td className="mono" style={{ fontSize: 12.5, fontWeight: 600, color: colorDias(g.dias) }}>{textoDias(g.dias)}</td>
                  <td>{g.fuente ? <span className={"ll-chip" + (g.fuente === "lenovo" ? " acento" : "")}>{FUENTES[g.fuente] || g.fuente}</span> : <span className="tenue">—</span>}</td>
                  <td className="mono" style={{ fontSize: 12, color: "var(--ll-dim)" }}>{g.consultado ? fmtFechaHora(g.consultado) : "—"}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
        {!cargando && !filtradas.length && <div className="ll-vacio">{lista.length ? "Sin equipos que coincidan con los filtros." : "Todavía no hay activos."}</div>}
        {cargando && !lista.length && <div className="ll-vacio">Cargando garantías…</div>}
      </div>
    </div>
  );
}
