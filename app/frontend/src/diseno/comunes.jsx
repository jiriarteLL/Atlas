// comunes.jsx — Piezas chicas del diseño v2 reutilizadas por las vistas.
import { useCallback, useEffect, useRef, useState } from "react";

// Estados de ciclo de vida (fase F) primero; despues los de antes, que siguen siendo validos.
export const ESTADOS = ["En stock", "Asignado", "Prestado", "En reparación", "Para baja", "Dado de baja", "Activo", "Mantenimiento", "Libre", "Stock", "Robado"];
// Igual que backend/ciclo_activos.estado_ciclo: "Activo" = Asignado si tiene usuario, si no En stock.
export function estadoCiclo(a) {
  const e = (a.estado || "").trim();
  if (["En stock", "Asignado", "Prestado", "En reparación", "Para baja", "Dado de baja"].includes(e)) return e;
  if (e === "Stock" || e === "Libre") return "En stock";
  if (e === "Mantenimiento") return "En reparación";
  if (e === "Activo" || !e) return (a.usuario || "").trim() ? "Asignado" : "En stock";
  return e;
}
export const TIPO_COLOR = { Notebook: "#3b82f6", Impresora: "#22c55e", Servidor: "#ec4899", Monitor: "#a78bfa", Switch: "#fbbf24", UPS: "#f97316", CPU: "#22d3ee" };

export function estadoColor(e) {
  if (e === "Activo" || e === "Activa" || e === "Asignado") return "var(--ll-verde)";
  if (e === "Mantenimiento" || e === "Por vencer" || e === "Inactivo" || e === "En reparación" || e === "Prestado") return "var(--ll-ambar)";
  if (e === "Libre" || e === "Stock" || e === "En stock") return "var(--ll-azul)";
  if (e === "Dado de baja") return "var(--ll-gris)";
  return "var(--ll-rosa)";
}

export const Estado = ({ valor }) => (
  <span className="ll-estado" style={{ color: estadoColor(valor) }}><i />{valor || "—"}</span>
);

// Panel lateral derecho con velo; Esc lo cierra.
export function Drawer({ abierto, onCerrar, ancho, children }) {
  useEffect(() => {
    if (!abierto) return undefined;
    const k = (e) => { if (e.key === "Escape") onCerrar(); };
    window.addEventListener("keydown", k);
    return () => window.removeEventListener("keydown", k);
  }, [abierto, onCerrar]);
  if (!abierto) return null;
  return <>
    <div className="ll-velo" onClick={onCerrar} />
    <aside className={"ll-drawer" + (ancho ? " ancho" : "")} role="dialog" aria-modal="true">{children}</aside>
  </>;
}

export function Modal({ titulo, onCerrar, children, pie, ancho }) {
  useEffect(() => {
    const k = (e) => { if (e.key === "Escape") onCerrar(); };
    window.addEventListener("keydown", k);
    return () => window.removeEventListener("keydown", k);
  }, [onCerrar]);
  return (
    <div className="ll-modal-velo" onClick={onCerrar}>
      <div className="ll-modal" style={ancho ? { maxWidth: ancho } : undefined} onClick={(e) => e.stopPropagation()} role="dialog" aria-modal="true">
        <div className="ll-modal-cab"><div>{titulo}</div><button className="ll-cerrar" onClick={onCerrar} aria-label="Cerrar">✕</button></div>
        {children}
        {pie && <div className="ll-modal-pie">{pie}</div>}
      </div>
    </div>
  );
}

export function useToast() {
  const [msg, setMsg] = useState("");
  const t = useRef(0);
  const mostrar = useCallback((m) => {
    setMsg(m);
    clearTimeout(t.current);
    t.current = setTimeout(() => setMsg(""), 2600);
  }, []);
  useEffect(() => () => clearTimeout(t.current), []);
  const Toast = msg ? <div className="ll-toast" role="status"><i /><span>{msg}</span></div> : null;
  return [Toast, mostrar];
}

export const Rotulo = ({ children, style }) => <div className="ll-rotulo" style={{ marginBottom: 12, ...style }}>{children}</div>;

export const Ficha = ({ filas }) => (
  <div className="ll-ficha">
    {filas.filter(([, v]) => v !== undefined && v !== null && v !== "" && v !== "-").map(([k, v, alerta]) => (
      <div key={k}><span className="k">{k}</span><span className={"v" + (alerta ? " alerta" : "")}>{v}</span></div>
    ))}
  </div>
);

// Pantalla de un modulo que esta en el diseño pero no en esta version (Licencias, Nomina).
export function Proximamente({ titulo, texto, columnas }) {
  return (
    <div>
      <div className="ll-barra">
        <span className="ll-contador">0 {titulo.toLowerCase()}</span>
        <div style={{ flex: 1 }} />
        <button className="ll-btn-primario" disabled title="Módulo no incluido en esta versión">＋ Nuevo</button>
      </div>
      <div className="ll-card" style={{ overflow: "hidden" }}>
        {columnas && <div className="ll-tabla-wrap"><table className="ll-tabla" style={{ minWidth: 760 }}>
          <thead><tr>{columnas.map((c) => <th key={c}>{c}</th>)}</tr></thead>
        </table></div>}
        <div className="ll-vacio">
          <div style={{ fontSize: 30, marginBottom: 10, color: "var(--accent)" }}>⬡</div>
          <div style={{ color: "var(--ll-text)", fontWeight: 600, marginBottom: 6 }}>Módulo no incluido en esta versión</div>
          <div style={{ maxWidth: 460, margin: "0 auto", lineHeight: 1.6 }}>{texto}</div>
        </div>
      </div>
    </div>
  );
}
