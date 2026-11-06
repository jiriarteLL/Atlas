// Salud.jsx — Subseccion de Activos "Notebooks y PC": salud y seguridad de cada equipo (version de Windows y su fin
// de soporte, BitLocker, antivirus, ultimo parche, discos, bateria y ultimo reporte). Las tarjetas de arriba son
// alertas que filtran la tabla; un clic en la fila abre la ficha del activo. Los datos salen de /api/salud.
import { useCallback, useEffect, useMemo, useState } from "react";
import { apiFetch } from "../api";
import { SEDES, fmtFechaHora } from "../ui";
import { COLOR_CIFRADO } from "./filtros";

const ROJO = "#f87171", AMBAR = "#fbbf24", VERDE = "#34d399";

// Alertas: clave del resumen, rotulo de la tarjeta, color y condicion sobre una fila de /api/salud
export const ALERTAS_SALUD = [
  ["sin_soporte", "Windows sin soporte", ROJO, (f) => f.soporte_estado === "sin_soporte"],
  ["vence_pronto", "Soporte vence pronto", AMBAR, (f) => f.soporte_estado === "vence_pronto"],
  ["sin_cifrar", "Sin BitLocker", "#f472b6", (f) => f.sin_cifrar],
  ["av_problema", "Antivirus con problemas", ROJO, (f) => f.av_estado === "desactivado" || f.av_estado === "desactualizado"],
  ["sin_parches_30d", "Sin parches +30 días", AMBAR, (f) => f.dias_sin_parches !== null && f.dias_sin_parches > 30],
  ["disco_riesgo", "Disco en riesgo", ROJO, (f) => f.disco_estado === "riesgo"],
  ["bateria_baja", "Batería por debajo del 60%", AMBAR, (f) => f.bateria_baja],
  ["sin_reportar_15d", "Sin reportar +15 días", "var(--ll-muted)", (f) => f.sin_reportar],
  ["sin_datos", "Sin datos del agente nuevo", "var(--ll-muted)", (f) => !f.con_datos],
];

// "2026-10-13" -> "13/10/2026" (sin pasar por Date: es una fecha, no un instante)
export const fmtFecha = (s) => {
  const m = /^(\d{4})-(\d{2})-(\d{2})/.exec(s || "");
  return m ? `${m[3]}/${m[2]}/${m[1]}` : "—";
};

export const textoWindows = (f) => {
  const prod = f.soporte_producto || (f.so || "").replace(/^Microsoft\s+/i, "").replace(/\s+(Pro|Home|Enterprise|Education).*$/i, "");
  return [prod, f.so_display].filter(Boolean).join(" ") || "—";
};

function Insignia({ color, children, titulo }) {
  return (
    <span title={titulo} style={{ display: "inline-block", fontSize: 11.5, fontWeight: 600, padding: "3px 9px", borderRadius: 20,
      color, background: `color-mix(in srgb, ${color} 13%, transparent)`, border: `1px solid color-mix(in srgb, ${color} 35%, transparent)`, whiteSpace: "nowrap" }}>
      {children}
    </span>
  );
}

export function InsigniaSoporte({ f }) {
  if (f.soporte_estado === "sin_soporte") return <Insignia color={ROJO}>Sin soporte desde {fmtFecha(f.fin_soporte)}</Insignia>;
  if (f.soporte_estado === "vence_pronto") return <Insignia color={AMBAR} titulo={`Quedan ${f.soporte_dias} días`}>Vence {fmtFecha(f.fin_soporte)}</Insignia>;
  if (f.soporte_estado === "vigente") return <span className="tenue" style={{ fontSize: 12 }}>Hasta {fmtFecha(f.fin_soporte)}</span>;
  if (f.so_build >= 26300) return <Insignia color="var(--ll-muted)" titulo="Build que todavía no está en la tabla de ciclo de vida">versión nueva</Insignia>;
  return f.so_build ? <Insignia color="var(--ll-muted)" titulo="Build o edición sin fecha conocida (LTSC, Insider…)">sin dato de soporte</Insignia> : null;
}

const AV_TEXTO = { ok: ["Al día", VERDE], desactualizado: ["Desactualizado", AMBAR], desactivado: ["Desactivado", ROJO] };

export function EstadoAntivirus({ f }) {
  const [txt, color] = AV_TEXTO[f.av_estado] || ["—", "var(--ll-dim)"];
  const activos = (f.antivirus || []).filter((a) => a.activo).map((a) => a.nombre);
  const nombres = (activos.length ? activos : (f.antivirus || []).map((a) => a.nombre)).join(", ");
  return (
    <span style={{ display: "inline-flex", flexDirection: "column", gap: 2 }}>
      <span style={{ color, fontWeight: 600, fontSize: 12.5 }}>{txt}</span>
      {nombres && <span className="tenue" style={{ fontSize: 11.5 }}>{nombres}</span>}
    </span>
  );
}

const colorBateria = (p) => (p < 60 ? ROJO : p < 80 ? AMBAR : VERDE);

export function BarraBateria({ porcentaje, ciclos }) {
  if (porcentaje === null || porcentaje === undefined) return <span className="tenue">—</span>;
  const c = colorBateria(porcentaje);
  return (
    <span style={{ display: "inline-flex", alignItems: "center", gap: 8 }} title={ciclos != null ? ciclos + " ciclos" : ""}>
      <span style={{ width: 60, height: 7, borderRadius: 4, background: "rgba(255,255,255,0.08)", overflow: "hidden" }}>
        <span style={{ display: "block", width: Math.max(2, Math.min(100, porcentaje)) + "%", height: "100%", background: c }} />
      </span>
      <span className="mono" style={{ color: c, fontSize: 12 }}>{porcentaje}%</span>
    </span>
  );
}

export function textoDisco(f) {
  const d = f.discos || [];
  if (!d.length) return null;
  const peor = d.find((x) => x.salud && !/^(healthy|ok)$/i.test(x.salud)) || d[0];
  return [peor.salud || "—", f.desgaste_max != null ? f.desgaste_max + "% desgaste" : ""].filter(Boolean).join(" · ");
}

export default function Salud({ assets, verFicha }) {
  const [lista, setLista] = useState([]);
  const [cargando, setCargando] = useState(true);
  const [error, setError] = useState("");
  const [filtros, setFiltros] = useState({ q: "", sede: "", alerta: "" });

  const cargar = useCallback(async () => {
    setCargando(true);
    try {
      const r = await apiFetch("/api/salud");
      if (!r.ok) throw new Error("Error " + r.status);
      setLista(await r.json());
      setError("");
    } catch (e) { setError(e.message); } finally { setCargando(false); }
  }, []);
  useEffect(() => { cargar(); }, [cargar]);

  const porSede = useMemo(() => lista.filter((f) => !filtros.sede || (f.sede || "").toLowerCase() === filtros.sede.toLowerCase()), [lista, filtros.sede]);
  const cuentas = useMemo(() => Object.fromEntries(ALERTAS_SALUD.map(([k, , , cond]) => [k, porSede.filter(cond).length])), [porSede]);
  const filtradas = useMemo(() => {
    const q = filtros.q.trim().toLowerCase();
    const cond = ALERTAS_SALUD.find(([k]) => k === filtros.alerta)?.[3];
    return porSede.filter((f) => (!cond || cond(f))
      && (!q || [f.nombre, f.usuario, f.serial, f.modelo, f.so, f.so_display].some((v) => String(v || "").toLowerCase().includes(q))));
  }, [porSede, filtros]);
  const f = (k) => (e) => setFiltros({ ...filtros, [k]: e.target.value });
  const abrir = (fila) => { const a = assets.find((x) => x.id === fila.id); if (a) verFicha(a); };

  return (
    <div>
      <div style={{ display: "grid", gridTemplateColumns: "repeat(auto-fill, minmax(165px, 1fr))", gap: 12, marginBottom: 20 }}>
        {ALERTAS_SALUD.map(([k, rotulo, color]) => {
          const activa = filtros.alerta === k;
          return (
            <button key={k} type="button" className="ll-card hover" aria-pressed={activa}
              onClick={() => setFiltros({ ...filtros, alerta: activa ? "" : k })}
              style={{ textAlign: "left", padding: "14px 16px", cursor: "pointer", color: "inherit", font: "inherit",
                borderColor: activa ? color : undefined, boxShadow: activa ? `0 0 0 1px ${color}` : undefined }}>
              <div className="mono" style={{ fontSize: 24, fontWeight: 600, color: cuentas[k] ? color : "var(--ll-dim)" }}>{cuentas[k] ?? 0}</div>
              <div style={{ fontSize: 12.5, color: "var(--ll-text-2)", marginTop: 4 }}>{rotulo}</div>
            </button>
          );
        })}
      </div>

      <div className="ll-barra">
        <div className="ll-buscador">
          <span>⌕</span>
          <input className="ll-input" value={filtros.q} onChange={f("q")} placeholder="Buscar por equipo, usuario, serie o Windows…" aria-label="Buscar equipos" />
        </div>
        <select className="ll-select" style={{ width: "auto" }} value={filtros.sede} onChange={f("sede")} aria-label="Sede">
          <option value="">Todas las sedes</option>
          {SEDES.map((s) => <option key={s}>{s}</option>)}
        </select>
        <select className="ll-select" style={{ width: "auto" }} value={filtros.alerta} onChange={f("alerta")} aria-label="Alerta">
          <option value="">Todas las alertas</option>
          {ALERTAS_SALUD.map(([k, l]) => <option key={k} value={k}>{l}</option>)}
        </select>
        <span className="ll-contador">{filtradas.length} equipos</span>
      </div>

      {error && <div className="ll-vacio" style={{ color: "var(--ll-warn)" }}>No se pudo cargar la salud de los equipos: {error}</div>}
      <div className="ll-card" style={{ overflow: "hidden" }}>
        <div className="ll-tabla-wrap">
          <table className="ll-tabla" style={{ minWidth: 1250 }}>
            <thead><tr>
              <th>EQUIPO</th><th>USUARIO</th><th>SEDE</th><th>WINDOWS</th><th>BITLOCKER</th><th>ANTIVIRUS</th>
              <th>ÚLTIMO PARCHE</th><th>DISCO</th><th>BATERÍA</th><th>ÚLTIMO REPORTE</th>
            </tr></thead>
            <tbody>
              {filtradas.map((x) => {
                const disco = textoDisco(x);
                return (
                  <tr key={x.id} className="click" onClick={() => abrir(x)}>
                    <td className="nombre">{x.nombre}<div className="tenue" style={{ fontSize: 11.5, fontWeight: 400 }}>{x.tipo}</div></td>
                    <td>{x.usuario || <span className="tenue">—</span>}</td>
                    <td>{x.sede || <span className="tenue">—</span>}</td>
                    <td>
                      <div>{textoWindows(x)}{x.so_build ? <span className="mono tenue" style={{ fontSize: 11.5 }}> · {x.so_build}{x.so_ubr != null ? "." + x.so_ubr : ""}</span> : null}</div>
                      <div style={{ marginTop: 4 }}><InsigniaSoporte f={x} /></div>
                    </td>
                    <td style={{ color: COLOR_CIFRADO(x.cifrado), fontWeight: 600, fontSize: 12.5 }}>{x.cifrado || "—"}</td>
                    <td><EstadoAntivirus f={x} /></td>
                    <td className="mono" style={{ fontSize: 12.5, color: x.dias_sin_parches > 30 ? AMBAR : undefined }}>
                      {x.ultimo_parche ? fmtFecha(x.ultimo_parche) : <span className="tenue">—</span>}
                    </td>
                    <td style={{ fontSize: 12.5, color: x.disco_estado === "riesgo" ? ROJO : undefined, fontWeight: x.disco_estado === "riesgo" ? 600 : 400 }}>
                      {disco || <span className="tenue">—</span>}
                    </td>
                    <td><BarraBateria porcentaje={x.bateria_salud} ciclos={x.bateria_ciclos} /></td>
                    <td className="mono" style={{ fontSize: 12.5, color: x.sin_reportar ? AMBAR : "var(--ll-dim)" }}>{fmtFechaHora(x.ultimo_reporte)}</td>
                  </tr>
                );
              })}
            </tbody>
          </table>
        </div>
        {!cargando && !filtradas.length && <div className="ll-vacio">{lista.length ? "Sin equipos que coincidan con los filtros." : "Todavía no hay notebooks ni PC cargadas."}</div>}
        {cargando && !lista.length && <div className="ll-vacio">Cargando equipos…</div>}
      </div>
    </div>
  );
}
