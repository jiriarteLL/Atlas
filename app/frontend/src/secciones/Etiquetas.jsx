// Etiquetas.jsx — Etiquetas QR de los activos (fase F) y utilidades de impresion compartidas con las actas.
// El QR apunta a la ficha en Atlas: <url publica>/#activos?activo=<id>. Se genera en el navegador con la libreria
// local "qrcode" (sin servicios externos). Imprimir: la hoja va a un portal .ll-impresion (ver diseno/fasef.css).
import { useEffect, useMemo, useState } from "react";
import { createPortal } from "react-dom";
import QRCode from "qrcode";
import { apiFetch } from "../api";
import { Modal } from "../diseno/comunes";
import "../diseno/fasef.css";

let urlPublica = null;   // cache de /api/ciclo/config
export function useUrlPublica() {
  const [u, setU] = useState(urlPublica || window.location.origin);
  useEffect(() => {
    if (urlPublica !== null) return undefined;
    let vivo = true;
    apiFetch("/api/ciclo/config").then((r) => (r.ok ? r.json() : null)).then((d) => {
      urlPublica = (d && d.url_publica) || window.location.origin;
      if (vivo) setU(urlPublica);
    }).catch(() => {});
    return () => { vivo = false; };
  }, []);
  return u;
}

export const urlActivo = (base, id) => base.replace(/\/$/, "") + "/#activos?activo=" + encodeURIComponent(id);

// <img> con el QR (data URL PNG). nivel M: aguanta una etiqueta algo gastada.
export function QrImg({ texto, px = 220, alt = "Código QR", className }) {
  const [src, setSrc] = useState("");
  useEffect(() => {
    let vivo = true;
    QRCode.toDataURL(texto, { errorCorrectionLevel: "M", margin: 1, width: px }).then((d) => { if (vivo) setSrc(d); }).catch(() => {});
    return () => { vivo = false; };
  }, [texto, px]);
  return src ? <img src={src} alt={alt} className={className} /> : <span className="tenue">…</span>;
}

// Portal que solo se ve al imprimir. imprimir() marca el body para ocultar el resto de la app.
export function Impresion({ children }) {
  return createPortal(<div className="ll-impresion">{children}</div>, document.body);
}
export function imprimir() {
  document.body.classList.add("ll-imprimiendo");
  const fin = () => { document.body.classList.remove("ll-imprimiendo"); window.removeEventListener("afterprint", fin); };
  window.addEventListener("afterprint", fin);
  setTimeout(() => window.print(), 60);   // deja que el portal termine de dibujar los QR
}

export function Etiqueta({ a, base }) {
  return (
    <div className="etq">
      <QrImg texto={urlActivo(base, a.id)} px={240} alt={"QR de " + (a.nombre || a.serial)} />
      <div className="t">
        <b>{a.nombre || a.serial}</b>
        <div>{[a.tipo, a.marca, a.modelo].filter(Boolean).join(" · ")}</div>
        {a.serial && <div className="m">S/N {a.serial}</div>}
        {a.nro_inventario && <div className="m">Inv. {a.nro_inventario}</div>}
        <div className="e">LL&A · Soporte Técnico</div>
      </div>
    </div>
  );
}

const FORMATOS = [["c2", "A4 · 2 columnas"], ["c3", "A4 · 3 columnas"], ["c4", "A4 · 4 columnas"], ["f62", "Etiqueta 62 mm (Brother)"]];
const MAX = 400;

// Modal: elegir activos (vienen filtrados de la lista) y formato, vista previa e imprimir.
export function HojaEtiquetas({ activos, onCerrar }) {
  const base = useUrlPublica();
  const [formato, setFormato] = useState("c3");
  const [sel, setSel] = useState(() => new Set(activos.slice(0, MAX).map((a) => a.id)));
  const [q, setQ] = useState("");
  const [inventario, setInventario] = useState({});
  useEffect(() => {   // n de inventario (datos de compra), si esta cargado
    let vivo = true;
    apiFetch("/api/ciclo/inventario").then((r) => (r.ok ? r.json() : {})).then((d) => { if (vivo) setInventario(d || {}); }).catch(() => {});
    return () => { vivo = false; };
  }, []);
  const visibles = useMemo(() => {
    const t = q.trim().toLowerCase();
    return activos.filter((a) => !t || [a.nombre, a.serial, a.usuario, a.modelo].some((v) => (v || "").toLowerCase().includes(t)));
  }, [activos, q]);
  const elegidos = activos.filter((a) => sel.has(a.id)).map((a) => ({ ...a, nro_inventario: inventario[a.id] || "" }));
  const marcar = (id) => setSel((s) => { const n = new Set(s); if (n.has(id)) n.delete(id); else n.add(id); return n; });
  const hoja = <div className={"etq-hoja " + formato}>{elegidos.map((a) => <Etiqueta key={a.id} a={a} base={base} />)}</div>;

  return (
    <Modal titulo={"Etiquetas QR · " + elegidos.length + " de " + activos.length} onCerrar={onCerrar} ancho={980}
      pie={<>
        <span className="tenue" style={{ fontSize: 12, marginRight: "auto" }}>El QR abre la ficha en {base}</span>
        <button className="ll-btn-borde" onClick={onCerrar}>Cerrar</button>
        <button className="ll-btn-primario" disabled={!elegidos.length} onClick={imprimir}>Imprimir {elegidos.length}</button>
      </>}>
      <div style={{ padding: "18px 26px", display: "flex", flexDirection: "column", gap: 14 }}>
        <div style={{ display: "flex", gap: 10, flexWrap: "wrap", alignItems: "center" }}>
          <select className="ll-select" style={{ width: "auto" }} value={formato} onChange={(e) => setFormato(e.target.value)} aria-label="Formato">
            {FORMATOS.map(([k, l]) => <option key={k} value={k}>{l}</option>)}
          </select>
          <input className="ll-input" style={{ flex: 1, minWidth: 180 }} value={q} onChange={(e) => setQ(e.target.value)} placeholder="Buscar en la selección…" aria-label="Buscar" />
          <button className="ll-btn-borde ll-btn-chico" onClick={() => setSel(new Set(visibles.slice(0, MAX).map((a) => a.id)))}>Todos</button>
          <button className="ll-btn-borde ll-btn-chico" onClick={() => setSel(new Set())}>Ninguno</button>
        </div>
        {activos.length > MAX && <div className="tenue" style={{ fontSize: 12 }}>Se marcaron los primeros {MAX}: filtrá la lista para imprimir el resto.</div>}
        <div style={{ display: "grid", gridTemplateColumns: "minmax(220px, 1fr) 2fr", gap: 14 }} className="etq-elegir">
          <div className="ll-card" style={{ maxHeight: "46vh", overflowY: "auto", padding: "6px 12px" }}>
            {visibles.map((a) => (
              <label key={a.id} style={{ display: "flex", gap: 9, alignItems: "center", justifyContent: "flex-start", textAlign: "left", padding: "7px 2px", fontSize: 13, cursor: "pointer", borderTop: "1px solid var(--ll-row-line)" }}>
                <input type="checkbox" style={{ flex: "none", width: "auto", margin: 0 }} checked={sel.has(a.id)} onChange={() => marcar(a.id)} />
                <span style={{ minWidth: 0, flex: 1, textAlign: "left" }}><b style={{ color: "var(--ll-text)" }}>{a.nombre || a.serial}</b>
                  <span className="tenue" style={{ display: "block", fontSize: 11.5 }}>{a.tipo} · {a.serial}</span></span>
              </label>
            ))}
            {!visibles.length && <div className="ll-vacio" style={{ padding: 20 }}>Sin activos.</div>}
          </div>
          <div className="etq-previa" aria-label="Vista previa">{elegidos.length ? hoja : <div style={{ color: "#666", fontSize: 13 }}>Elegí al menos un activo.</div>}</div>
        </div>
      </div>
      <Impresion>{hoja}</Impresion>
    </Modal>
  );
}
