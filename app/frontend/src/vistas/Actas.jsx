// Actas.jsx — Actas de entrega / devolucion / prestamo (fase F). Listado con filtros, alta en borrador con la persona,
// los equipos y sus accesorios, vista A4 del acta, firma en pantalla (receptor y soporte) o "imprimir para firmar" y
// subir el escaneo. Al firmar, Atlas registra el movimiento de cada equipo (asignacion / devolucion / prestamo).
import { useCallback, useEffect, useMemo, useRef, useState } from "react";
import { apiFetch } from "../api";
import { SEDES, fmtFechaHora } from "../ui";
import { Rotulo, estadoCiclo } from "../diseno/comunes";
import { Impresion, imprimir } from "../secciones/Etiquetas";
import "../diseno/fasef.css";

const URL = "/api/actas";
const TIPOS = [["entrega", "Entrega"], ["devolucion", "Devolución"], ["prestamo", "Préstamo"]];
const TITULO = { entrega: "ACTA DE ENTREGA DE EQUIPAMIENTO", devolucion: "ACTA DE DEVOLUCIÓN DE EQUIPAMIENTO", prestamo: "ACTA DE PRÉSTAMO DE EQUIPAMIENTO" };
const COLOR_ESTADO = { borrador: "var(--ll-ambar)", firmada: "var(--ll-verde)", anulada: "var(--ll-dim)" };
const fmtF = (s) => { const m = /^(\d{4})-(\d{2})-(\d{2})/.exec(s || ""); return m ? `${m[3]}/${m[2]}/${m[1]}` : ""; };
const hoy = () => new Date().toLocaleDateString("sv-SE");

async function pedir(url, opts) {
  const r = await apiFetch(url, opts);
  const d = await r.json().catch(() => ({}));
  if (!r.ok) throw new Error(typeof d.detail === "string" ? d.detail : Array.isArray(d.detail) ? "Revisá los datos: " + (d.detail[0]?.msg || "") : "Error " + r.status);
  return d;
}
const json = (method, body) => ({ method, headers: { "Content-Type": "application/json" }, body: JSON.stringify(body) });

let configCache = null;
function useConfigActas() {
  const [c, setC] = useState(configCache);
  useEffect(() => {
    if (configCache) return;
    pedir(URL + "/config").then((d) => { configCache = d; setC(d); }).catch(() => {});
  }, []);
  return c;
}

// ---------------------------------------------------------------- documento A4
export function ActaDoc({ acta, config }) {
  return (
    <div className="acta-doc">
      <div className="cab">
        <img src="/brand/logo-dark.png" alt="LL&A" />
        <div className="num"><b>{acta.numero}</b>{fmtF(acta.fecha)}</div>
      </div>
      <h2>{TITULO[acta.tipo] || "ACTA"} {acta.estado === "anulada" && <span className="anulada">ANULADA</span>}</h2>
      <div className="datos">
        <div><span>Empresa:</span> {config?.empresa}</div>
        <div><span>Sede:</span> {acta.sede || "—"}</div>
        <div><span>{acta.tipo === "devolucion" ? "Devuelve" : "Recibe"}:</span> <b>{acta.persona}</b></div>
        <div><span>Legajo / Área:</span> {[acta.legajo, acta.area].filter(Boolean).join(" · ") || "—"}</div>
        {acta.tipo === "prestamo" && <div><span>Devolución prevista:</span> {fmtF(acta.devolucion_prevista) || "—"}</div>}
      </div>
      <table>
        <thead><tr><th>#</th><th>EQUIPO</th><th>N° DE SERIE</th><th>N° INVENTARIO</th><th>ACCESORIOS</th></tr></thead>
        <tbody>{acta.items.map((it, i) => (
          <tr key={it.id || it.asset_id}><td>{i + 1}</td><td>{it.descripcion}</td><td>{it.serial}</td><td>{it.nro_inventario || "—"}</td>
            <td>{(it.accesorios || []).join(", ") || "—"}</td></tr>))}</tbody>
      </table>
      {acta.observaciones && <p><b>Observaciones:</b> {acta.observaciones}</p>}
      {acta.tipo !== "devolucion" && acta.clausula && <div className="clausula">{acta.clausula}</div>}
      {acta.tipo === "devolucion" && <div className="clausula">Soporte Técnico deja constancia de la recepción de los equipos y accesorios detallados, sujeta a la revisión de su estado.</div>}
      <div className="firmas">
        <div className="firma"><div className="linea">{acta.firma_receptor && <img src={acta.firma_receptor} alt="Firma" />}</div>
          {acta.persona}<br /><span style={{ color: "#666" }}>{acta.tipo === "devolucion" ? "Entrega" : "Recibe"} · firma y aclaración</span></div>
        <div className="firma"><div className="linea">{acta.firma_soporte && <img src={acta.firma_soporte} alt="Firma de soporte" />}</div>
          {acta.firmo_soporte || "Soporte Técnico"}<br /><span style={{ color: "#666" }}>Soporte Técnico · {config?.empresa}</span></div>
      </div>
      <div className="sello">{acta.numero} · generada en Atlas{acta.firmada_el ? " · firmada " + fmtFechaHora(acta.firmada_el) : ""}{acta.estado === "anulada" ? " · ANULADA: " + (acta.motivo_anulacion || "") : ""}</div>
    </div>
  );
}

// ---------------------------------------------------------------- firma en pantalla
function FirmaLienzo({ rotulo, onCambio }) {
  const ref = useRef(null);
  const dibujando = useRef(false);
  const [vacia, setVacia] = useState(true);
  useEffect(() => {
    const c = ref.current;
    const r = c.getBoundingClientRect();
    const k = window.devicePixelRatio || 1;
    c.width = r.width * k; c.height = r.height * k;
    const ctx = c.getContext("2d");
    ctx.scale(k, k); ctx.lineWidth = 2.2; ctx.lineCap = "round"; ctx.lineJoin = "round"; ctx.strokeStyle = "#111";
  }, []);
  const punto = (e) => { const r = ref.current.getBoundingClientRect(); return [e.clientX - r.left, e.clientY - r.top]; };
  const bajar = (e) => { e.preventDefault(); ref.current.setPointerCapture(e.pointerId); dibujando.current = true; const [x, y] = punto(e); const ctx = ref.current.getContext("2d"); ctx.beginPath(); ctx.moveTo(x, y); };
  const mover = (e) => { if (!dibujando.current) return; const [x, y] = punto(e); const ctx = ref.current.getContext("2d"); ctx.lineTo(x, y); ctx.stroke(); };
  const subir = () => { if (!dibujando.current) return; dibujando.current = false; setVacia(false); onCambio(ref.current.toDataURL("image/png")); };
  const borrar = () => { const c = ref.current; c.getContext("2d").clearRect(0, 0, c.width, c.height); setVacia(true); onCambio(""); };
  return (
    <div className="firma-caja">
      <canvas ref={ref} className="firma-lienzo" onPointerDown={bajar} onPointerMove={mover} onPointerUp={subir} onPointerLeave={subir} aria-label={rotulo} />
      <div className="pie"><span>{rotulo}{vacia ? " · firmá con el dedo o el mouse" : ""}</span><button className="ll-btn-borde ll-btn-chico" onClick={borrar}>Borrar</button></div>
    </div>
  );
}

// ---------------------------------------------------------------- editor
function EditorActa({ inicial, assets, config, onGuardada, onCancelar }) {
  const [d, setD] = useState(() => inicial ? {
    tipo: inicial.tipo, persona: inicial.persona, legajo: inicial.legajo || "", area: inicial.area || "", sede: inicial.sede || "",
    fecha: inicial.fecha || hoy(), devolucion_prevista: inicial.devolucion_prevista || "", observaciones: inicial.observaciones || "",
    clausula: inicial.clausula || "", items: inicial.items.map((i) => ({ asset_id: i.asset_id, accesorios: i.accesorios || [] })),
  } : { tipo: "entrega", persona: "", legajo: "", area: "", sede: "", fecha: hoy(), devolucion_prevista: "", observaciones: "",
    clausula: config?.clausula || "", items: [] });
  const [q, setQ] = useState("");
  const [error, setError] = useState("");
  const [guardando, setGuardando] = useState(false);
  const porId = useMemo(() => Object.fromEntries(assets.map((a) => [a.id, a])), [assets]);
  const candidatos = useMemo(() => {
    const t = q.trim().toLowerCase();
    if (t.length < 2) return [];
    return assets.filter((a) => a.estado !== "Dado de baja" && !d.items.some((i) => i.asset_id === a.id)
      && [a.nombre, a.serial, a.usuario, a.modelo].some((v) => (v || "").toLowerCase().includes(t))).slice(0, 8);
  }, [assets, q, d.items]);
  const set = (k) => (e) => setD({ ...d, [k]: e.target.value });
  const agregar = (a) => { setD({ ...d, items: [...d.items, { asset_id: a.id, accesorios: a.tipo === "Notebook" ? ["Cargador"] : [] }], persona: d.persona || (d.tipo === "devolucion" ? a.usuario || "" : ""), sede: d.sede || a.ubicacion || "" }); setQ(""); };
  const quitar = (id) => setD({ ...d, items: d.items.filter((i) => i.asset_id !== id) });
  const acc = (id, nombre) => setD({ ...d, items: d.items.map((i) => i.asset_id !== id ? i : { ...i, accesorios: i.accesorios.includes(nombre) ? i.accesorios.filter((x) => x !== nombre) : [...i.accesorios, nombre] }) });

  async function guardar() {
    setGuardando(true);
    try {
      const body = { ...d, devolucion_prevista: d.tipo === "prestamo" && d.devolucion_prevista ? d.devolucion_prevista : null };
      const r = inicial ? await pedir(URL + "/" + inicial.id, json("PUT", body)) : await pedir(URL, json("POST", body));
      onGuardada(r);
    } catch (e) { setError(e.message); } finally { setGuardando(false); }
  }

  return (
    <div className="ll-card" style={{ padding: 22, display: "flex", flexDirection: "column", gap: 16 }}>
      <div className="ll-card-titulo">{inicial ? "Editar " + inicial.numero : "Nueva acta"}</div>
      <div className="ll-grid-form">
        <label className="ll-campo"><span>TIPO</span><select className="ll-select" value={d.tipo} onChange={set("tipo")}>{TIPOS.map(([k, l]) => <option key={k} value={k}>{l}</option>)}</select></label>
        <label className="ll-campo"><span>FECHA</span><input className="ll-input" type="date" value={d.fecha} onChange={set("fecha")} /></label>
        <label className="ll-campo"><span>{d.tipo === "devolucion" ? "PERSONA QUE DEVUELVE" : "PERSONA QUE RECIBE"}</span><input className="ll-input" value={d.persona} onChange={set("persona")} autoComplete="off" /></label>
        <label className="ll-campo"><span>SEDE</span><select className="ll-select" value={d.sede} onChange={set("sede")}><option value="">—</option>{SEDES.map((s) => <option key={s}>{s}</option>)}</select></label>
        <label className="ll-campo"><span>LEGAJO (OPCIONAL)</span><input className="ll-input" value={d.legajo} onChange={set("legajo")} autoComplete="off" /></label>
        <label className="ll-campo"><span>ÁREA (OPCIONAL)</span><input className="ll-input" value={d.area} onChange={set("area")} autoComplete="off" /></label>
        {d.tipo === "prestamo" && <label className="ll-campo"><span>DEVOLUCIÓN PREVISTA</span><input className="ll-input" type="date" value={d.devolucion_prevista} onChange={set("devolucion_prevista")} /></label>}
      </div>

      <div>
        <Rotulo>EQUIPOS ({d.items.length})</Rotulo>
        <div style={{ position: "relative" }}>
          <input className="ll-input" value={q} onChange={(e) => setQ(e.target.value)} placeholder="Buscar equipo por nombre, serie, usuario o modelo…" aria-label="Buscar equipo" />
          {candidatos.length > 0 && <div className="ll-card" style={{ position: "absolute", zIndex: 5, left: 0, right: 0, top: "calc(100% + 4px)", padding: 6, background: "var(--ll-panel)" }}>
            {candidatos.map((a) => <button key={a.id} className="ll-nav-item" style={{ width: "100%", textAlign: "left" }} onClick={() => agregar(a)}>
              <span style={{ flex: 1 }}><b>{a.nombre || a.serial}</b> <span className="tenue">· {a.tipo} · {a.serial} · {estadoCiclo(a)}{a.usuario ? " · " + a.usuario : ""}</span></span></button>)}
          </div>}
        </div>
        <div style={{ display: "flex", flexDirection: "column", gap: 10, marginTop: 12 }}>
          {d.items.map((i) => { const a = porId[i.asset_id] || {}; return (
            <div key={i.asset_id} className="ll-card" style={{ padding: "12px 14px" }}>
              <div style={{ display: "flex", alignItems: "center", gap: 10 }}>
                <div style={{ flex: 1, minWidth: 0 }}><b>{a.nombre || a.serial || i.asset_id}</b> <span className="tenue" style={{ fontSize: 12 }}>· {[a.tipo, a.marca, a.modelo].filter(Boolean).join(" ")} · S/N {a.serial}</span></div>
                <button className="ll-btn-borde ll-btn-chico" onClick={() => quitar(i.asset_id)} aria-label="Quitar">Quitar</button>
              </div>
              <div style={{ display: "flex", gap: 12, flexWrap: "wrap", marginTop: 8 }}>
                {(config?.accesorios || []).map((n) => <label key={n} style={{ fontSize: 12.5, display: "flex", gap: 5, alignItems: "center", cursor: "pointer" }}>
                  <input type="checkbox" checked={i.accesorios.includes(n)} onChange={() => acc(i.asset_id, n)} />{n}</label>)}
              </div>
            </div>); })}
          {!d.items.length && <div className="tenue" style={{ fontSize: 12.5 }}>Buscá y agregá al menos un equipo.</div>}
        </div>
      </div>

      <label className="ll-campo"><span>OBSERVACIONES</span><textarea className="ll-input" rows={2} value={d.observaciones} onChange={set("observaciones")} /></label>
      {d.tipo !== "devolucion" && <label className="ll-campo"><span>CLÁUSULA DE RESPONSABILIDAD</span><textarea className="ll-input" rows={4} value={d.clausula} onChange={set("clausula")} /></label>}
      {error && <div style={{ color: "var(--ll-warn)", fontSize: 13 }}>{error}</div>}
      <div style={{ display: "flex", gap: 10, justifyContent: "flex-end" }}>
        <button className="ll-btn-borde" onClick={onCancelar}>Cancelar</button>
        <button className="ll-btn-primario" disabled={guardando || !d.persona.trim() || !d.items.length} onClick={guardar}>{guardando ? "Guardando…" : "Guardar borrador"}</button>
      </div>
    </div>
  );
}

// ---------------------------------------------------------------- vista de un acta
function VerActa({ id, config, assets, puedeEditar, avisar, onVolver, onCambio }) {
  const [acta, setActa] = useState(null);
  const [error, setError] = useState("");
  const [editando, setEditando] = useState(false);
  const [firmando, setFirmando] = useState(false);
  const [firmas, setFirmas] = useState({ r: "", s: "" });
  const [ocupado, setOcupado] = useState(false);
  const archivo = useRef(null);
  const cargar = useCallback(async () => { try { setActa(await pedir(URL + "/" + id)); setError(""); } catch (e) { setError(e.message); } }, [id]);
  useEffect(() => { cargar(); }, [cargar]);

  async function accion(fn, msg) {
    setOcupado(true);
    try { setActa(await fn()); setError(""); avisar && avisar(msg); onCambio && onCambio(); } catch (e) { setError(e.message); } finally { setOcupado(false); }
  }
  const firmar = () => accion(() => pedir(URL + "/" + id + "/firmar", json("POST", { firma_receptor: firmas.r, firma_soporte: firmas.s })), "Acta firmada: los equipos quedaron actualizados")
    .then(() => setFirmando(false));
  const subir = (e) => {
    const f = e.target.files[0]; e.target.value = "";
    if (!f) return;
    const fd = new FormData(); fd.append("archivo", f);
    accion(() => pedir(URL + "/" + id + "/escaneo", { method: "POST", body: fd }), "Escaneo guardado" + (acta.estado === "borrador" ? " y acta confirmada" : ""));
  };
  const anular = () => {
    const motivo = prompt("Motivo de la anulación (la anulación no revierte los movimientos de los equipos):");
    if (motivo && motivo.trim().length >= 3) accion(() => pedir(URL + "/" + id + "/anular", json("POST", { motivo })), "Acta anulada");
  };

  if (!acta) return <div className="ll-vacio">{error || "Cargando acta…"}</div>;
  if (editando) return <EditorActa inicial={acta} assets={assets} config={config} onCancelar={() => setEditando(false)} onGuardada={(r) => { setEditando(false); setActa({ ...acta, ...r }); cargar(); }} />;
  return (
    <div style={{ display: "flex", flexDirection: "column", gap: 16 }}>
      <div style={{ display: "flex", gap: 8, flexWrap: "wrap", alignItems: "center" }}>
        <button className="ll-btn-borde" onClick={onVolver}>← Actas</button>
        <span className="ll-chip" style={{ color: COLOR_ESTADO[acta.estado], fontWeight: 600 }}>{acta.estado}</span>
        <span style={{ flex: 1 }} />
        {puedeEditar && acta.estado === "borrador" && <>
          <button className="ll-btn-borde" onClick={() => setEditando(true)}>Editar</button>
          <button className="ll-btn-primario" onClick={() => setFirmando(true)}>Firmar en pantalla</button>
        </>}
        <button className="ll-btn-borde" onClick={imprimir}>{acta.estado === "borrador" ? "Imprimir para firmar" : "Imprimir"}</button>
        {puedeEditar && acta.estado !== "anulada" && <button className="ll-btn-borde" disabled={ocupado} onClick={() => archivo.current.click()}>Subir escaneo firmado</button>}
        {puedeEditar && acta.estado !== "anulada" && <button className="ll-btn-peligro" style={{ padding: "8px 14px", borderRadius: 10 }} onClick={anular}>Anular</button>}
        <input ref={archivo} type="file" accept=".pdf,.jpg,.jpeg,.png" style={{ display: "none" }} onChange={subir} />
      </div>
      {error && <div style={{ color: "var(--ll-warn)", fontSize: 13 }}>{error}</div>}
      {firmando && <div className="ll-card" style={{ padding: 18, display: "flex", flexDirection: "column", gap: 14 }}>
        <div className="ll-card-titulo">Firmas</div>
        <div className="ll-grid-form">
          <FirmaLienzo rotulo={(acta.tipo === "devolucion" ? "Entrega: " : "Recibe: ") + acta.persona} onCambio={(v) => setFirmas((f) => ({ ...f, r: v }))} />
          <FirmaLienzo rotulo="Soporte Técnico" onCambio={(v) => setFirmas((f) => ({ ...f, s: v }))} />
        </div>
        <div className="tenue" style={{ fontSize: 12 }}>Al confirmar, el acta queda firmada y {acta.tipo === "entrega" ? "los equipos se asignan a " + acta.persona : acta.tipo === "prestamo" ? "los equipos quedan prestados a " + acta.persona : "los equipos vuelven a stock"}.</div>
        <div style={{ display: "flex", gap: 10, justifyContent: "flex-end" }}>
          <button className="ll-btn-borde" onClick={() => setFirmando(false)}>Cancelar</button>
          <button className="ll-btn-primario" disabled={ocupado || !firmas.r || !firmas.s} onClick={firmar}>{ocupado ? "Guardando…" : "Confirmar firmas"}</button>
        </div>
      </div>}
      <div className="acta-previa" style={{ maxWidth: 860 }}><ActaDoc acta={acta} config={config} /></div>
      <Impresion><ActaDoc acta={acta} config={config} /></Impresion>
    </div>
  );
}

// ---------------------------------------------------------------- listado
export default function Actas({ assets, puedeEditar, avisar, onCambio, abrirId }) {
  const config = useConfigActas();
  const [lista, setLista] = useState([]);
  const [cargando, setCargando] = useState(true);
  const [error, setError] = useState("");
  const [f, setF] = useState({ q: "", tipo: "", estado: "" });
  const [vista, setVista] = useState(() => (abrirId ? { modo: "ver", id: abrirId } : null));
  const cargar = useCallback(async () => {
    setCargando(true);
    try { setLista(await pedir(URL)); setError(""); } catch (e) { setError(e.message); } finally { setCargando(false); }
  }, []);
  useEffect(() => { cargar(); }, [cargar]);
  const filtradas = useMemo(() => {
    const q = f.q.trim().toLowerCase();
    return lista.filter((a) => (!f.tipo || a.tipo === f.tipo) && (!f.estado || a.estado === f.estado)
      && (!q || [a.numero, a.persona, a.area, a.legajo, ...a.items.map((i) => i.serial + " " + i.descripcion)].some((v) => (v || "").toLowerCase().includes(q))));
  }, [lista, f]);
  const cambio = () => { cargar(); onCambio && onCambio(); };

  if (vista?.modo === "nueva") return <EditorActa assets={assets} config={config} onCancelar={() => setVista(null)}
    onGuardada={(r) => { cargar(); setVista({ modo: "ver", id: r.id }); avisar && avisar("Acta " + r.numero + " guardada en borrador"); }} />;
  if (vista?.modo === "ver") return <VerActa id={vista.id} config={config} assets={assets} puedeEditar={puedeEditar} avisar={avisar}
    onVolver={() => { setVista(null); cargar(); }} onCambio={cambio} />;

  const set = (k) => (e) => setF({ ...f, [k]: e.target.value });
  return (
    <div>
      <div className="ll-barra">
        <div className="ll-buscador"><span>⌕</span>
          <input className="ll-input" value={f.q} onChange={set("q")} placeholder="Buscar por número, persona, área o serie…" aria-label="Buscar actas" /></div>
        <select className="ll-select" style={{ width: "auto" }} value={f.tipo} onChange={set("tipo")} aria-label="Tipo"><option value="">Todos los tipos</option>{TIPOS.map(([k, l]) => <option key={k} value={k}>{l}</option>)}</select>
        <select className="ll-select" style={{ width: "auto" }} value={f.estado} onChange={set("estado")} aria-label="Estado">
          <option value="">Todos los estados</option><option value="borrador">Borrador</option><option value="firmada">Firmada</option><option value="anulada">Anulada</option></select>
        <span className="ll-contador">{filtradas.length} actas</span>
        <div style={{ flex: 1 }} />
        {puedeEditar && <button className="ll-btn-primario" onClick={() => setVista({ modo: "nueva" })}>＋ Nueva acta</button>}
      </div>
      {error && <div className="ll-vacio" style={{ color: "var(--ll-warn)" }}>{error}</div>}
      <div className="ll-card" style={{ overflow: "hidden" }}>
        <div className="ll-tabla-wrap">
          <table className="ll-tabla" style={{ minWidth: 820 }}>
            <thead><tr><th>NÚMERO</th><th>TIPO</th><th>PERSONA</th><th>EQUIPOS</th><th>SEDE</th><th>FECHA</th><th>ESTADO</th></tr></thead>
            <tbody>{filtradas.map((a) => (
              <tr key={a.id} className="click" onClick={() => setVista({ modo: "ver", id: a.id })}>
                <td className="nombre">{a.numero}</td><td>{(TIPOS.find(([k]) => k === a.tipo) || ["", a.tipo])[1]}</td>
                <td>{a.persona}{a.area ? <div className="tenue" style={{ fontSize: 11.5 }}>{a.area}</div> : null}</td>
                <td className="tenue">{a.items.map((i) => i.descripcion).join(", ")}</td><td>{a.sede}</td>
                <td className="mono">{fmtF(a.fecha)}</td>
                <td><span style={{ color: COLOR_ESTADO[a.estado], fontWeight: 600, fontSize: 12.5 }}>{a.estado}{a.estado === "firmada" && !a.firmada_en_pantalla && a.escaneo_adjunto_id ? " (escaneo)" : ""}</span></td>
              </tr>))}</tbody>
          </table>
        </div>
        {!cargando && !filtradas.length && <div className="ll-vacio">{lista.length ? "Sin actas que coincidan con los filtros." : "Todavía no hay actas. Creá la primera con “Nueva acta”."}</div>}
        {cargando && !lista.length && <div className="ll-vacio">Cargando actas…</div>}
      </div>
    </div>
  );
}
