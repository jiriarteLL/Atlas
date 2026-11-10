// Auditoria.jsx — Auditoria fisica (fase F): campanias de relevamiento por sede. Pensada para el celular: se escanea
// el QR de la etiqueta con la camara (BarcodeDetector del navegador o, si no esta, jsQR local) o se tipea la serie /
// n de inventario. Encontrados, pendientes/faltantes, sobrantes y desconocidos; al cerrar, informe exportable.
import { useCallback, useEffect, useMemo, useRef, useState } from "react";
import jsQR from "jsqr";
import { apiFetch } from "../api";
import { SEDES, TIPOS, fmtFechaHora } from "../ui";
import "../diseno/fasef.css";

const BASE = "/api/auditoria";
const GRUPOS = [["pendiente", "Pendientes"], ["encontrado", "Encontrados"], ["sobrante", "Sobrantes"], ["desconocido", "Desconocidos"], ["faltante", "Faltantes"]];
const COLOR = { encontrado: "var(--ll-verde)", pendiente: "var(--ll-dim)", faltante: "var(--ll-rosa)", sobrante: "var(--ll-ambar)", desconocido: "var(--ll-rosa)" };
const TEXTO = { encontrado: "Encontrado", sobrante: "Sobrante: según Atlas está en otro lugar", desconocido: "No corresponde a ningún activo de Atlas" };

async function pedir(url, opts) {
  const r = await apiFetch(url, opts);
  const d = await r.json().catch(() => ({}));
  if (!r.ok) throw new Error(typeof d.detail === "string" ? d.detail : "Error " + r.status);
  return d;
}
const json = (method, body) => ({ method, headers: { "Content-Type": "application/json" }, body: JSON.stringify(body) });

// ---------------------------------------------------------------- camara
function Camara({ onCodigo, activa }) {
  const video = useRef(null);
  const [error, setError] = useState("");
  const ultimo = useRef({ c: "", t: 0 });
  useEffect(() => {
    if (!activa) return undefined;
    let stream = null, vivo = true, timer = 0;
    const canvas = document.createElement("canvas");
    const detector = "BarcodeDetector" in window ? new window.BarcodeDetector({ formats: ["qr_code", "code_128", "code_39", "ean_13"] }) : null;
    const emitir = (c) => {
      const ahora = Date.now();
      if (c && (c !== ultimo.current.c || ahora - ultimo.current.t > 4000)) { ultimo.current = { c, t: ahora }; onCodigo(c); }
    };
    async function ciclo() {
      if (!vivo) return;
      const v = video.current;
      if (v && v.readyState >= 2) {
        try {
          if (detector) {
            const r = await detector.detect(v);
            if (r[0]) emitir(r[0].rawValue);
          } else {
            const w = Math.min(640, v.videoWidth), h = Math.round(w * v.videoHeight / v.videoWidth);
            canvas.width = w; canvas.height = h;
            const ctx = canvas.getContext("2d", { willReadFrequently: true });
            ctx.drawImage(v, 0, 0, w, h);
            const q = jsQR(ctx.getImageData(0, 0, w, h).data, w, h, { inversionAttempts: "dontInvert" });
            if (q) emitir(q.data);
          }
        } catch { /* cuadro sin codigo */ }
      }
      timer = setTimeout(ciclo, 250);
    }
    navigator.mediaDevices?.getUserMedia({ video: { facingMode: "environment" }, audio: false })
      .then((s) => { if (!vivo) { s.getTracks().forEach((t) => t.stop()); return; } stream = s; video.current.srcObject = s; video.current.play().catch(() => {}); ciclo(); })
      .catch((e) => setError(e && e.name === "NotAllowedError" ? "No hay permiso para usar la cámara: habilitalo en el navegador." : "No se pudo abrir la cámara (requiere HTTPS)."));
    if (!navigator.mediaDevices) setError("Este navegador no permite usar la cámara: cargá el código a mano.");
    return () => { vivo = false; clearTimeout(timer); if (stream) stream.getTracks().forEach((t) => t.stop()); };
  }, [activa, onCodigo]);
  if (!activa) return null;
  return error ? <div className="aud-resultado desconocido">{error}</div>
    : <div className="aud-video"><video ref={video} playsInline muted /><div className="mira" /></div>;
}

// ---------------------------------------------------------------- campania
function Campana({ id, puedeEditar, avisar, onVolver, onCambio }) {
  const [c, setC] = useState(null);
  const [error, setError] = useState("");
  const [camara, setCamara] = useState(false);
  const [manual, setManual] = useState("");
  const [lugar, setLugar] = useState("");
  const [ultima, setUltima] = useState(null);
  const [grupo, setGrupo] = useState("pendiente");
  const [ocupado, setOcupado] = useState(false);
  const cargar = useCallback(async () => { try { setC(await pedir(BASE + "/" + id)); setError(""); } catch (e) { setError(e.message); } }, [id]);
  useEffect(() => { cargar(); }, [cargar]);

  const leer = useCallback(async (codigo) => {
    try {
      const r = await pedir(BASE + "/" + id + "/lecturas", json("POST", { codigo, lugar }));
      setUltima(r);
      if (navigator.vibrate) navigator.vibrate(r.resultado === "encontrado" ? 60 : [60, 60, 60]);
      cargar();
    } catch (e) { setError(e.message); }
  }, [id, lugar, cargar]);

  async function cerrar() {
    if (!confirm("¿Cerrar la campaña? Lo que no se leyó queda como faltante.")) return;
    setOcupado(true);
    try { await pedir(BASE + "/" + id + "/cerrar", { method: "POST" }); setCamara(false); await cargar(); setGrupo("faltante"); avisar && avisar("Campaña cerrada"); onCambio && onCambio(); }
    catch (e) { setError(e.message); } finally { setOcupado(false); }
  }
  async function mover() {
    if (!confirm("¿Pasar los sobrantes a la sede " + c.sede + "? Queda registrado en el historial de cada equipo.")) return;
    setOcupado(true);
    try { const r = await pedir(BASE + "/" + id + "/mover-sobrantes", json("POST", {})); avisar && avisar(r.movidos + " equipos pasados a " + c.sede); await cargar(); onCambio && onCambio(); }
    catch (e) { setError(e.message); } finally { setOcupado(false); }
  }
  function exportar() {
    const cols = ["resultado", "nombre", "tipo", "serial", "usuario", "sede_sistema", "lugar", "lectura", "leido_por", "leido_el"];
    const esc = (v) => '"' + String(v ?? "").replace(/"/g, '""') + '"';
    const filas = [cols.join(";"), ...c.items.map((i) => cols.map((k) => esc(k === "leido_el" && i[k] ? fmtFechaHora(i[k]) : i[k])).join(";"))];
    const blob = new Blob(["﻿" + filas.join("\r\n")], { type: "text/csv;charset=utf-8" });
    const a = document.createElement("a");
    a.href = URL.createObjectURL(blob); a.download = "auditoria-" + c.sede + "-" + new Date().toISOString().slice(0, 10) + ".csv"; a.click();
    setTimeout(() => URL.revokeObjectURL(a.href), 2000);
  }

  const items = useMemo(() => (c ? c.items.filter((i) => i.resultado === grupo || (grupo === "pendiente" && i.resultado === "pendiente")) : []), [c, grupo]);
  if (!c) return <div className="ll-vacio">{error || "Cargando campaña…"}</div>;
  const abierta = c.estado === "abierta";
  const r = c.resumen;
  const cuenta = { pendiente: r.pendientes, encontrado: r.encontrados, sobrante: r.sobrantes, desconocido: r.desconocidos, faltante: r.faltantes };
  const grupos = GRUPOS.filter(([k]) => (abierta ? k !== "faltante" : k !== "pendiente"));

  return (
    <div className="aud-escaner" style={{ maxWidth: 760 }}>
      <div style={{ display: "flex", gap: 8, alignItems: "center", flexWrap: "wrap" }}>
        <button className="ll-btn-borde" onClick={onVolver}>← Campañas</button>
        <div style={{ flex: 1, minWidth: 0 }}><b>{c.nombre}</b><div className="tenue" style={{ fontSize: 12 }}>{c.sede}{c.piso ? " · piso " + c.piso : ""} · {r.encontrados} de {r.esperados} encontrados</div></div>
        <span className="ll-chip" style={{ color: abierta ? "var(--ll-verde)" : "var(--ll-dim)" }}>{c.estado}</span>
      </div>
      <div style={{ height: 8, borderRadius: 5, background: "var(--ll-track)", overflow: "hidden" }}>
        <div style={{ height: "100%", width: (r.esperados ? Math.round(r.encontrados * 100 / r.esperados) : 0) + "%", background: "var(--ll-verde)" }} />
      </div>

      {abierta && puedeEditar && <>
        <div style={{ display: "flex", gap: 8 }}>
          <button className={camara ? "ll-btn-borde" : "ll-btn-primario"} style={{ flex: 1, padding: 14 }} onClick={() => setCamara((v) => !v)}>{camara ? "Apagar cámara" : "📷 Escanear con la cámara"}</button>
        </div>
        <Camara activa={camara} onCodigo={leer} />
        <form style={{ display: "flex", gap: 8 }} onSubmit={(e) => { e.preventDefault(); if (manual.trim()) { leer(manual.trim()); setManual(""); } }}>
          <input className="ll-input" value={manual} onChange={(e) => setManual(e.target.value)} placeholder="Serie, n° de inventario o nombre" aria-label="Código manual" autoCapitalize="characters" />
          <button className="ll-btn-borde" type="submit">Cargar</button>
        </form>
        <input className="ll-input" value={lugar} onChange={(e) => setLugar(e.target.value)} placeholder="Dónde estás (piso / oficina): se guarda con cada lectura" aria-label="Lugar" />
      </>}
      {ultima && <div className={"aud-resultado " + ultima.resultado}>
        <b>{ultima.repetido ? "Ya leído · " : ""}{TEXTO[ultima.resultado] || ultima.resultado}</b>
        <div style={{ marginTop: 4 }}>{ultima.activo ? <>{ultima.activo.nombre} · {ultima.activo.tipo} {ultima.activo.modelo} · S/N {ultima.activo.serial}
          {ultima.resultado === "sobrante" && <> · en Atlas: <b>{ultima.activo.sede || "sin sede"}</b></>}{ultima.activo.usuario ? " · " + ultima.activo.usuario : ""}</> : <span className="mono">{ultima.item.lectura}</span>}</div>
      </div>}
      {error && <div style={{ color: "var(--ll-warn)", fontSize: 13 }}>{error}</div>}

      <div className="aud-contadores">
        {grupos.map(([k, l]) => <button key={k} type="button" aria-pressed={grupo === k} onClick={() => setGrupo(k)}>
          <div className="n" style={{ color: cuenta[k] ? COLOR[k] : "var(--ll-dim)" }}>{cuenta[k]}</div><div className="l">{l}</div></button>)}
      </div>
      <div className="ll-card" style={{ padding: "6px 14px" }}>
        {items.map((i) => (
          <div key={i.id} className="aud-fila">
            <span style={{ width: 9, height: 9, borderRadius: "50%", background: COLOR[i.resultado], flex: "none" }} />
            <div className="q"><b>{i.nombre || i.lectura || "—"}</b>
              <span>{[i.tipo, i.serial && "S/N " + i.serial, i.usuario, i.resultado === "sobrante" && "en Atlas: " + (i.sede_sistema || "sin sede"), i.lugar && "visto en " + i.lugar].filter(Boolean).join(" · ")}</span></div>
            {i.leido_el && <span className="tenue mono" style={{ fontSize: 11 }}>{fmtFechaHora(i.leido_el).slice(11)}</span>}
            {i.movido && <span className="ll-chip">movido</span>}
          </div>))}
        {!items.length && <div className="ll-vacio" style={{ padding: 24 }}>Nada en este grupo.</div>}
      </div>

      <div style={{ display: "flex", gap: 8, flexWrap: "wrap", justifyContent: "flex-end" }}>
        <button className="ll-btn-borde" onClick={exportar}>Exportar CSV</button>
        {puedeEditar && !abierta && r.sobrantes > 0 && <button className="ll-btn-borde" disabled={ocupado} onClick={mover}>Pasar sobrantes a {c.sede}</button>}
        {puedeEditar && abierta && <button className="ll-btn-primario" disabled={ocupado} onClick={cerrar}>Cerrar campaña</button>}
      </div>
    </div>
  );
}

// ---------------------------------------------------------------- listado / alta
export default function Auditoria({ puedeEditar, avisar, onCambio }) {
  const [lista, setLista] = useState([]);
  const [cargando, setCargando] = useState(true);
  const [error, setError] = useState("");
  const [abierta, setAbierta] = useState(null);
  const [nueva, setNueva] = useState(null);
  const cargar = useCallback(async () => {
    setCargando(true);
    try { setLista(await pedir(BASE)); setError(""); } catch (e) { setError(e.message); } finally { setCargando(false); }
  }, []);
  useEffect(() => { cargar(); }, [cargar]);

  async function crear() {
    try { const r = await pedir(BASE, json("POST", nueva)); setNueva(null); avisar && avisar("Campaña creada con " + r.resumen.esperados + " equipos esperados"); setAbierta(r.id); cargar(); }
    catch (e) { setError(e.message); }
  }
  if (abierta) return <Campana id={abierta} puedeEditar={puedeEditar} avisar={avisar} onCambio={onCambio} onVolver={() => { setAbierta(null); cargar(); }} />;
  const tipo = (t) => setNueva({ ...nueva, tipos: nueva.tipos.includes(t) ? nueva.tipos.filter((x) => x !== t) : [...nueva.tipos, t] });

  return (
    <div style={{ maxWidth: 980 }}>
      <div className="ll-barra">
        <div className="tenue" style={{ fontSize: 13, flex: 1, minWidth: 220 }}>Recorré una sede con el celular y escaneá las etiquetas QR: Atlas compara lo que encontrás con lo que dice el inventario.</div>
        {puedeEditar && !nueva && <button className="ll-btn-primario" onClick={() => setNueva({ nombre: "", sede: "", piso: "", tipos: [] })}>＋ Nueva campaña</button>}
      </div>
      {nueva && <div className="ll-card" style={{ padding: 18, marginBottom: 18, display: "flex", flexDirection: "column", gap: 12 }}>
        <div className="ll-grid-form">
          <label className="ll-campo"><span>SEDE</span><select className="ll-select" value={nueva.sede} onChange={(e) => setNueva({ ...nueva, sede: e.target.value })}><option value="">Elegí la sede</option>{SEDES.map((s) => <option key={s}>{s}</option>)}</select></label>
          <label className="ll-campo"><span>PISO / SECTOR (OPCIONAL)</span><input className="ll-input" value={nueva.piso} onChange={(e) => setNueva({ ...nueva, piso: e.target.value })} /></label>
          <label className="ll-campo doble"><span>NOMBRE (OPCIONAL)</span><input className="ll-input" value={nueva.nombre} onChange={(e) => setNueva({ ...nueva, nombre: e.target.value })} placeholder="Relevamiento CABA noviembre" /></label>
        </div>
        <div style={{ display: "flex", gap: 12, flexWrap: "wrap", fontSize: 13 }}>
          <span className="tenue">Tipos (vacío = todos):</span>
          {TIPOS.map((t) => <label key={t} style={{ display: "flex", gap: 5, alignItems: "center", cursor: "pointer" }}><input type="checkbox" checked={nueva.tipos.includes(t)} onChange={() => tipo(t)} />{t}</label>)}
        </div>
        <div style={{ display: "flex", gap: 8, justifyContent: "flex-end" }}>
          <button className="ll-btn-borde" onClick={() => setNueva(null)}>Cancelar</button>
          <button className="ll-btn-primario" disabled={!nueva.sede} onClick={crear}>Crear campaña</button>
        </div>
      </div>}
      {error && <div className="ll-vacio" style={{ color: "var(--ll-warn)" }}>{error}</div>}
      <div style={{ display: "flex", flexDirection: "column", gap: 10 }}>
        {lista.map((c) => { const r = c.resumen; return (
          <button key={c.id} className="ll-card hover" style={{ textAlign: "left", padding: "14px 16px", cursor: "pointer", color: "inherit", font: "inherit" }} onClick={() => setAbierta(c.id)}>
            <div style={{ display: "flex", gap: 10, alignItems: "center", flexWrap: "wrap" }}>
              <b style={{ flex: 1, minWidth: 0 }}>{c.nombre}</b>
              <span className="ll-chip" style={{ color: c.estado === "abierta" ? "var(--ll-verde)" : "var(--ll-dim)" }}>{c.estado}</span>
            </div>
            <div className="tenue" style={{ fontSize: 12.5, marginTop: 4 }}>{c.sede}{c.piso ? " · piso " + c.piso : ""} · {fmtFechaHora(c.creada)} · {c.creada_por}</div>
            <div style={{ fontSize: 12.5, marginTop: 6 }}><span style={{ color: "var(--ll-verde)" }}>{r.encontrados} encontrados</span> de {r.esperados}
              {c.estado === "cerrada" ? <> · <span style={{ color: "var(--ll-rosa)" }}>{r.faltantes} faltantes</span></> : <> · {r.pendientes} pendientes</>}
              {r.sobrantes ? <> · <span style={{ color: "var(--ll-ambar)" }}>{r.sobrantes} sobrantes</span></> : null}</div>
          </button>); })}
        {!cargando && !lista.length && <div className="ll-vacio">Todavía no hay campañas de relevamiento.</div>}
      </div>
    </div>
  );
}
