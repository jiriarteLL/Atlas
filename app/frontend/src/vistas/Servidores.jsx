// Servidores.jsx — Subseccion de Activos "Servidores y VM": lo que informa el agente en Windows Server (roles,
// volumenes, uptime, reinicio pendiente, servicios detenidos, SQL, IIS, Hyper-V) mas lo que traen los conectores
// (vCenter, Azure y Redfish: iDRAC / iLO). Las tarjetas son alertas que filtran la tabla; un clic abre la ficha.
// Abajo, el panel de conectores con su estado y lo que falta configurar. Datos de /api/servidores y /api/conectores.
import { useCallback, useEffect, useMemo, useState } from "react";
import { apiFetch } from "../api";
import { SEDES, fmtFechaHora } from "../ui";
import { fmtFecha } from "./Salud";

const ALERTAS = [
  ["disco_lleno", "Disco con menos de 10% libre", "var(--ll-rojo)"],
  ["reinicio_pendiente", "Reinicio pendiente +7 días", "var(--ll-ambar)"],
  ["uptime_alto", "Sin reiniciar +60 días", "var(--ll-ambar)"],
  ["servicios_detenidos", "Servicios automáticos detenidos", "var(--ll-rojo)"],
  ["sin_soporte", "Windows Server sin soporte", "var(--ll-rosa)"],
  ["sin_reportar", "Sin reportar +15 días", "var(--ll-muted)"],
];
const ORIGENES = { agente: "Agente", vcenter: "vCenter", azure: "Azure", redfish: "iDRAC / iLO" };

const colorLibre = (p) => (p === null || p === undefined ? "var(--ll-dim)" : p < 10 ? "var(--ll-rojo)" : p < 20 ? "var(--ll-ambar)" : "var(--ll-verde)");

export function BarraVolumen({ pct, texto }) {
  if (pct === null || pct === undefined) return <span className="tenue">—</span>;
  const usado = Math.max(0, Math.min(100, 100 - pct)), c = colorLibre(pct);
  return (
    <span style={{ display: "inline-flex", alignItems: "center", gap: 8 }} title={texto || ""}>
      <span style={{ width: 70, height: 7, borderRadius: 4, background: "var(--ll-track)", overflow: "hidden" }}>
        <span style={{ display: "block", width: Math.max(2, usado) + "%", height: "100%", background: c }} />
      </span>
      <span className="mono" style={{ color: c, fontSize: 12 }}>{pct}% libre</span>
    </span>
  );
}

const textoSO = (f) => [f.soporte_producto ? `${f.soporte_producto} ${f.soporte_version}` : (f.so || "").replace(/^Microsoft\s+/i, "")].filter(Boolean).join(" ") || "—";
const textoUptime = (d) => (d === null || d === undefined ? "—" : d < 1 ? "< 1 día" : Math.round(d) + " días");

function Origenes({ f }) {
  return (
    <span style={{ display: "inline-flex", gap: 4, flexWrap: "wrap" }}>
      {(f.origenes || []).map((o) => <span key={o} className={"ll-chip" + (o === "agente" ? " acento" : "")} style={{ fontSize: 11 }}>{ORIGENES[o] || o}</span>)}
    </span>
  );
}

function Soporte({ f }) {
  if (f.soporte_estado === "sin_soporte") return <span style={{ fontSize: 11.5, color: "var(--ll-rosa)", fontWeight: 600 }}>Sin soporte desde {fmtFecha(f.fin_soporte)}</span>;
  if (f.soporte_estado === "vence_pronto") return <span style={{ fontSize: 11.5, color: "var(--ll-ambar)", fontWeight: 600 }}>Vence {fmtFecha(f.fin_soporte)}</span>;
  if (f.soporte_estado === "vigente") return <span className="tenue" style={{ fontSize: 11.5 }}>Hasta {fmtFecha(f.fin_soporte)}</span>;
  return null;
}

// ---------------------------------------------------------------- panel de conectores
function Conectores({ puedeEditar, avisar }) {
  const [lista, setLista] = useState([]);
  const cargar = useCallback(async () => {
    try { const r = await apiFetch("/api/conectores"); if (r.ok) setLista(await r.json()); } catch { /* sin permiso o sin red */ }
  }, []);
  useEffect(() => { cargar(); }, [cargar]);
  const corriendo = lista.some((c) => c.corriendo || c.pedida);
  useEffect(() => {
    if (!corriendo) return undefined;
    const t = setInterval(cargar, 5000);
    return () => clearInterval(t);
  }, [corriendo, cargar]);
  async function actualizar() {
    const r = await apiFetch("/api/conectores/actualizar", { method: "POST" });
    const d = r.ok ? await r.json() : null;
    avisar && avisar(d && d.conectores.length ? "Actualizando: " + d.conectores.join(", ") : "No hay conectores configurados");
    setTimeout(cargar, 1500);
  }
  const algunoConfigurado = lista.some((c) => c.configurado);
  return (
    <div className="ll-card" style={{ padding: "16px 18px", marginTop: 20 }}>
      <div style={{ display: "flex", alignItems: "center", gap: 10, marginBottom: 12, flexWrap: "wrap" }}>
        <div className="mono" style={{ fontSize: 11.5, letterSpacing: 1.5, color: "var(--ll-dim)" }}>CONECTORES</div>
        <span style={{ flex: 1 }} />
        {puedeEditar && <button className="ll-btn-borde" disabled={!algunoConfigurado || corriendo} onClick={actualizar}>{corriendo ? "Actualizando…" : "Actualizar ahora"}</button>}
      </div>
      <div style={{ display: "grid", gridTemplateColumns: "repeat(auto-fill, minmax(260px, 1fr))", gap: 12 }}>
        {lista.map((c) => (
          <div key={c.conector} style={{ border: "1px solid var(--ll-line)", borderRadius: 12, padding: "12px 14px" }}>
            <div style={{ display: "flex", alignItems: "center", gap: 8 }}>
              <span style={{ width: 8, height: 8, borderRadius: "50%", background: !c.configurado ? "var(--ll-ghost)" : c.ok === false ? "var(--ll-rojo)" : c.ok ? "var(--ll-verde)" : "var(--ll-ambar)" }} />
              <span style={{ fontWeight: 600, fontSize: 13.5 }}>{c.nombre}</span>
            </div>
            {!c.configurado ? (
              <div style={{ fontSize: 12, color: "var(--ll-dim)", marginTop: 6 }}>
                Sin configurar. Falta: <span className="mono" style={{ fontSize: 11.5 }}>{c.falta.join(", ")}</span>
              </div>
            ) : (
              <div style={{ fontSize: 12, color: "var(--ll-text-2)", marginTop: 6 }}>
                {c.corriendo || c.pedida ? "Consultando…" : c.fin ? `Última: ${fmtFechaHora(c.fin)} · ${c.mensaje || (c.ok ? "OK" : "")}` : "Todavía no corrió"}
                <div className="tenue" style={{ fontSize: 11.5, marginTop: 2 }}>{c.cada_horas ? `Automático cada ${c.cada_horas} h` : "Solo con el botón"}</div>
              </div>
            )}
          </div>
        ))}
      </div>
      <div className="tenue" style={{ fontSize: 11.5, marginTop: 10 }}>Cómo activarlos: docs/conectores-servidores.md (usuarios de solo lectura; las claves van en archivos protegidos, nunca en Atlas).</div>
    </div>
  );
}

// ---------------------------------------------------------------- vista
export default function Servidores({ assets, verFicha, puedeEditar, avisar }) {
  const [lista, setLista] = useState([]);
  const [cargando, setCargando] = useState(true);
  const [error, setError] = useState("");
  const [filtros, setFiltros] = useState({ q: "", sede: "", origen: "", alerta: "" });

  const cargar = useCallback(async () => {
    setCargando(true);
    try {
      const r = await apiFetch("/api/servidores");
      if (!r.ok) throw new Error("Error " + r.status);
      setLista(await r.json());
      setError("");
    } catch (e) { setError(e.message); } finally { setCargando(false); }
  }, []);
  useEffect(() => { cargar(); }, [cargar]);

  const porSede = useMemo(() => lista.filter((x) => !filtros.sede || (x.sede || "").toLowerCase() === filtros.sede.toLowerCase()), [lista, filtros.sede]);
  const cuentas = useMemo(() => Object.fromEntries(ALERTAS.map(([k]) => [k, porSede.filter((x) => x.alertas.includes(k)).length])), [porSede]);
  const filtradas = useMemo(() => {
    const q = filtros.q.trim().toLowerCase();
    return porSede.filter((x) => (!filtros.alerta || x.alertas.includes(filtros.alerta))
      && (!filtros.origen || x.origenes.includes(filtros.origen))
      && (!q || [x.nombre, x.ip, x.so, x.serial, x.host, ...(x.roles || []).map((r) => r.nombre)].some((v) => String(v || "").toLowerCase().includes(q))));
  }, [porSede, filtros]);
  const f = (k) => (e) => setFiltros({ ...filtros, [k]: e.target.value });
  const abrir = (id) => { const a = assets.find((y) => y.id === id); if (a) verFicha(a); };

  return (
    <div>
      <div style={{ display: "grid", gridTemplateColumns: "repeat(auto-fill, minmax(165px, 1fr))", gap: 12, marginBottom: 20 }}>
        <div className="ll-card" style={{ padding: "14px 16px" }}>
          <div className="mono" style={{ fontSize: 24, fontWeight: 600, color: "var(--accent)" }}>{porSede.length}</div>
          <div style={{ fontSize: 12.5, color: "var(--ll-text-2)", marginTop: 4 }}>Servidores y VM</div>
        </div>
        {ALERTAS.map(([k, rotulo, color]) => {
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
          <input className="ll-input" value={filtros.q} onChange={f("q")} placeholder="Buscar por nombre, IP, rol, host o serie…" aria-label="Buscar servidores" />
        </div>
        <select className="ll-select" style={{ width: "auto" }} value={filtros.sede} onChange={f("sede")} aria-label="Sede">
          <option value="">Todas las sedes</option>
          {SEDES.map((s) => <option key={s}>{s}</option>)}
        </select>
        <select className="ll-select" style={{ width: "auto" }} value={filtros.origen} onChange={f("origen")} aria-label="Origen">
          <option value="">Todo origen</option>
          {Object.entries(ORIGENES).map(([k, v]) => <option key={k} value={k}>{v}</option>)}
        </select>
        <select className="ll-select" style={{ width: "auto" }} value={filtros.alerta} onChange={f("alerta")} aria-label="Alerta">
          <option value="">Todas las alertas</option>
          {ALERTAS.map(([k, l]) => <option key={k} value={k}>{l}</option>)}
        </select>
        <span className="ll-contador">{filtradas.length} servidores</span>
      </div>

      {error && <div className="ll-vacio" style={{ color: "var(--ll-warn)" }}>No se pudieron cargar los servidores: {error}</div>}
      <div className="ll-card" style={{ overflow: "hidden" }}>
        <div className="ll-tabla-wrap">
          <table className="ll-tabla" style={{ minWidth: 1250 }}>
            <thead><tr>
              <th>SERVIDOR</th><th>ORIGEN</th><th>SISTEMA OPERATIVO</th><th>ROLES</th><th>DISCOS</th><th>UPTIME</th>
              <th>REINICIO PENDIENTE</th><th>SEDE / HOST</th><th>ÚLTIMO REPORTE</th>
            </tr></thead>
            <tbody>
              {filtradas.map((x) => {
                const roles = (x.controlador_dominio ? ["Controlador de dominio"] : []).concat((x.roles || []).map((r) => r.nombre)
                  .filter((r) => !(x.controlador_dominio && /dominio de active directory/i.test(r))));
                return (
                  <tr key={x.id} className="click" onClick={() => abrir(x.id)}>
                    <td className="nombre">{x.nombre}<div className="tenue" style={{ fontSize: 11.5, fontWeight: 400 }}>{[x.tipo, x.ip].filter(Boolean).join(" · ")}</div></td>
                    <td><Origenes f={x} /></td>
                    <td><div>{textoSO(x)}</div><Soporte f={x} /></td>
                    <td style={{ maxWidth: 230 }}>
                      {roles.length ? <span style={{ display: "inline-flex", gap: 4, flexWrap: "wrap" }}>
                        {roles.slice(0, 3).map((r) => <span key={r} className="ll-chip" title={r} style={{ fontSize: 11, maxWidth: 200, overflow: "hidden", textOverflow: "ellipsis", whiteSpace: "nowrap" }}>{r}</span>)}
                        {roles.length > 3 && <span className="tenue" style={{ fontSize: 11.5 }}>+{roles.length - 3}</span>}
                      </span> : <span className="tenue">—</span>}
                    </td>
                    <td><BarraVolumen pct={x.disco_min_libre_pct} texto={(x.volumenes || []).map((v) => `${v.letra} ${v.libre_gb} de ${v.tamano_gb} GB libres`).join("\n")} /></td>
                    <td className="mono" style={{ fontSize: 12.5, color: x.alertas.includes("uptime_alto") ? "var(--ll-ambar)" : undefined }}>{textoUptime(x.uptime_dias)}</td>
                    <td style={{ fontSize: 12.5 }}>
                      {x.reinicio_pendiente
                        ? <span style={{ color: x.alertas.includes("reinicio_pendiente") ? "var(--ll-ambar)" : "var(--ll-text-2)", fontWeight: 600 }}>Sí{x.reinicio_dias !== null ? ` · ${x.reinicio_dias} d` : ""}</span>
                        : <span className="tenue">{x.con_agente && x.servidor_actualizado ? "No" : "—"}</span>}
                    </td>
                    <td>{x.sede || <span className="tenue">—</span>}{x.host && <div className="tenue" style={{ fontSize: 11.5 }}>{x.host}</div>}</td>
                    <td className="mono" style={{ fontSize: 12.5, color: x.alertas.includes("sin_reportar") ? "var(--ll-ambar)" : "var(--ll-dim)" }}>{fmtFechaHora(x.ultimo_reporte)}</td>
                  </tr>
                );
              })}
            </tbody>
          </table>
        </div>
        {!cargando && !filtradas.length && <div className="ll-vacio">{lista.length ? "Sin servidores que coincidan con los filtros." : "Todavía no hay servidores cargados."}</div>}
        {cargando && !lista.length && <div className="ll-vacio">Cargando servidores…</div>}
      </div>

      <Conectores puedeEditar={puedeEditar} avisar={avisar} />
    </div>
  );
}

// ---------------------------------------------------------------- seccion de la ficha del activo
function Bloque({ titulo, children }) {
  return (
    <div>
      <div className="mono" style={{ fontSize: 11, letterSpacing: 1.5, color: "var(--ll-dim)", margin: "4px 0 8px" }}>{titulo}</div>
      {children}
    </div>
  );
}

const Fila = ({ k, v }) => (v === null || v === undefined || v === "" ? null : (
  <div style={{ display: "flex", gap: 12, fontSize: 13, padding: "3px 0" }}><span style={{ color: "var(--ll-dim)", minWidth: 150 }}>{k}</span><span style={{ color: "var(--ll-text)" }}>{v}</span></div>
));

export function ServidorActivo({ assetId }) {
  const [x, setX] = useState(null);
  useEffect(() => {
    let vivo = true;
    apiFetch("/api/servidores/" + assetId).then((r) => (r.ok ? r.json() : null)).then((d) => { if (vivo) setX(d); }).catch(() => {});
    return () => { vivo = false; };
  }, [assetId]);
  if (!x) return null;
  const ext = x.externos || {};
  const vc = ext.vcenter, az = ext.azure, rf = ext.redfish;
  return (
    <div style={{ display: "flex", flexDirection: "column", gap: 14 }}>
      <Bloque titulo="SERVIDOR">
        <Fila k="Origen" v={<Origenes f={x} />} />
        <Fila k="Uptime" v={x.uptime_dias !== null ? textoUptime(x.uptime_dias) : null} />
        <Fila k="Reinicio pendiente" v={x.reinicio_pendiente ? `Sí (${(x.reinicio_motivos || []).join(", ")}${x.reinicio_dias !== null ? ` · hace ${x.reinicio_dias} días` : ""})` : (x.servidor_actualizado ? "No" : null)} />
        <Fila k="Controlador de dominio" v={x.controlador_dominio ? "Sí" : null} />
        <Fila k="Soporte de Windows" v={x.fin_soporte ? <Soporte f={x} /> : null} />
      </Bloque>
      {x.roles?.length > 0 && <Bloque titulo="ROLES">
        {x.roles.map((r) => <div key={r.nombre} style={{ fontSize: 13, padding: "3px 0" }}><b style={{ fontWeight: 600 }}>{r.nombre}</b>{r.servicios?.length ? <span className="tenue"> · {r.servicios.join(", ")}</span> : null}</div>)}
      </Bloque>}
      {x.volumenes?.length > 0 && <Bloque titulo="VOLÚMENES">
        {x.volumenes.map((v) => <div key={v.letra} style={{ display: "flex", gap: 12, alignItems: "center", fontSize: 13, padding: "3px 0" }}>
          <span className="mono" style={{ minWidth: 36 }}>{v.letra}</span><BarraVolumen pct={v.libre_pct} />
          <span className="tenue" style={{ fontSize: 12 }}>{v.libre_gb} de {v.tamano_gb} GB libres{v.etiqueta ? ` · ${v.etiqueta}` : ""}{v.fs ? ` · ${v.fs}` : ""}</span></div>)}
      </Bloque>}
      {x.servicios_detenidos?.length > 0 && <Bloque titulo="SERVICIOS AUTOMÁTICOS DETENIDOS">
        {x.servicios_detenidos.map((s) => <div key={s.nombre} style={{ fontSize: 13, padding: "2px 0", color: "var(--ll-rojo)" }}>{s.display || s.nombre} <span className="mono tenue" style={{ fontSize: 11.5 }}>{s.nombre}</span></div>)}
      </Bloque>}
      {(x.sql?.length > 0 || x.iis?.length > 0) && <Bloque titulo="SQL SERVER / IIS">
        {x.sql.map((s) => <Fila key={"s" + s.instancia} k={"SQL " + s.instancia} v={s.estado} />)}
        {x.iis.map((s) => <Fila key={"i" + s.nombre} k={"IIS " + s.nombre} v={`${s.estado}${s.bindings?.length ? " · " + s.bindings.join(", ") : ""}`} />)}
      </Bloque>}
      {x.hyperv_vms && <Bloque titulo={`HYPER-V · ${x.hyperv_vms.length} VM`}>
        {x.hyperv_vms.map((v) => <Fila key={v.nombre} k={v.nombre} v={[v.estado, v.cpu ? v.cpu + " vCPU" : "", v.ram_gb ? v.ram_gb + " GB" : ""].filter(Boolean).join(" · ")} />)}
      </Bloque>}
      {(vc || az || rf) && <Bloque titulo="VIRTUALIZACIÓN / HARDWARE">
        {vc && (vc.es_host
          ? <><Fila k="vCenter" v="Host ESXi" /><Fila k="Estado" v={[vc.estado, vc.encendido].filter(Boolean).join(" · ")} /><Fila k="Cluster" v={vc.cluster} /></>
          : <><Fila k="vCenter: host" v={vc.host} /><Fila k="Cluster" v={vc.cluster} /><Fila k="Estado" v={vc.estado} />
            <Fila k="CPU / RAM" v={[vc.cpu ? vc.cpu + " vCPU" : "", vc.ram_gb ? vc.ram_gb + " GB" : ""].filter(Boolean).join(" · ")} />
            <Fila k="SO invitado" v={vc.so} /><Fila k="Discos" v={(vc.discos || []).map((d) => `${d.nombre} ${d.tamano_gb ?? "?"} GB`).join(", ")} /></>)}
        {az && <><Fila k="Azure: tamaño" v={az.tamano} /><Fila k="Región / grupo" v={[az.region, az.grupo_recursos].filter(Boolean).join(" · ")} />
          <Fila k="Estado" v={az.estado} /><Fila k="Imagen" v={az.imagen} /><Fila k="IP privada" v={az.ip} />
          <Fila k="Discos" v={(az.discos || []).map((d) => `${d.nombre || (d.so ? "SO" : "datos")} ${d.tamano_gb ?? "?"} GB`).join(", ")} /></>}
        {rf && <><Fila k={rf.controlador + ": salud"} v={<span style={{ color: rf.salud && rf.salud !== "OK" ? "var(--ll-rojo)" : "var(--ll-verde)", fontWeight: 600 }}>{rf.salud || "—"}</span>} />
          <Fila k="Modelo / serie" v={[rf.fabricante, rf.modelo, rf.sku || rf.serie].filter(Boolean).join(" · ")} />
          <Fila k="BIOS / firmware" v={[rf.bios, rf.firmware].filter(Boolean).join(" · ")} />
          <Fila k="Fuentes" v={(rf.fuentes || []).map((p) => `${p.nombre}: ${p.salud || "—"}`).join(" · ")} />
          <Fila k="Discos" v={(rf.discos || []).length ? `${rf.discos.length} (${rf.discos.filter((d) => d.salud && d.salud !== "OK").length} con problemas)` : null} />
          <Fila k="Temperatura máx." v={rf.temperatura_max !== null && rf.temperatura_max !== undefined ? rf.temperatura_max + " °C" : null} />
          <Fila k="Garantía (Dell)" v={rf.garantia} /></>}
      </Bloque>}
    </div>
  );
}
