// AlertaToner.jsx — Aviso emergente: impresoras con algun cartucho por debajo del umbral (10% por defecto,
// TONER_ALERTA_PCT en el servidor). Consulta al entrar y cada 10 minutos; mientras haya cartuchos por debajo,
// el aviso vuelve a aparecer 10 minutos despues de cerrado (o enseguida si aparece un cartucho nuevo).
import { useCallback, useEffect, useRef, useState } from "react";
import { apiFetch } from "../api";
import { Modal } from "../diseno/comunes";
import { fmtFechaHora } from "../ui";

const CADA_MS = 10 * 60 * 1000;
const CLAVE = "atlas_alerta_toner";   // { firma, cerrada } del ultimo aviso cerrado en esta pestaña
const firma = (alertas) => alertas.map((a) => a.id + ":" + a.consumible + ":" + a.porcentaje).join("|");

function leerCierre() {
  try { return JSON.parse(sessionStorage.getItem(CLAVE) || "{}"); } catch { return {}; }
}

export default function AlertaToner({ onVer }) {
  const [datos, setDatos] = useState(null);
  const abierto = useRef(false);

  const revisar = useCallback(async () => {
    if (abierto.current) return;
    try {
      const r = await apiFetch("/api/impresoras/alertas");
      if (!r.ok) return;
      const d = await r.json();
      if (!d.alertas?.length) return;
      const ultimo = leerCierre();
      const nuevo = ultimo.firma !== firma(d.alertas);
      if (nuevo || !ultimo.cerrada || Date.now() - ultimo.cerrada >= CADA_MS) {
        abierto.current = true;
        setDatos(d);
      }
    } catch { /* sin red: se reintenta en la proxima vuelta */ }
  }, []);

  useEffect(() => {
    revisar();
    const t = setInterval(revisar, CADA_MS);
    return () => clearInterval(t);
  }, [revisar]);

  const cerrar = useCallback(() => {
    try { sessionStorage.setItem(CLAVE, JSON.stringify({ firma: firma(datos?.alertas || []), cerrada: Date.now() })); }
    catch { /* sin storage */ }
    abierto.current = false;
    setDatos(null);
  }, [datos]);

  if (!datos) return null;
  const n = new Set(datos.alertas.map((a) => a.id)).size;
  return (
    <Modal titulo={`Tóner por debajo del ${datos.umbral}%`} onCerrar={cerrar}
      pie={<>
        <button type="button" className="ll-btn-borde" onClick={cerrar}>Recordarme en 10 min</button>
        <button type="button" className="ll-btn-primario" onClick={() => { cerrar(); onVer(); }}>Ver impresoras</button>
      </>}>
      <div style={{ padding: "18px 26px", display: "flex", flexDirection: "column", gap: 12 }}>
        <p style={{ margin: 0, color: "var(--ll-text-2)", fontSize: 14 }}>
          {n === 1 ? "Una impresora tiene" : `${n} impresoras tienen`} cartuchos por cambiar pronto:
        </p>
        {datos.alertas.map((a) => (
          <div key={a.id + a.consumible} style={{ display: "flex", alignItems: "center", gap: 14, padding: "12px 14px",
            borderRadius: 12, background: "color-mix(in srgb, var(--ll-rosa) 8%, transparent)", border: "1px solid color-mix(in srgb, var(--ll-rosa) 30%, transparent)" }}>
            <span className="mono" style={{ fontSize: 22, fontWeight: 600, color: "var(--ll-rosa)", minWidth: 48, textAlign: "right" }}>
              {a.porcentaje}%
            </span>
            <div style={{ minWidth: 0 }}>
              <div className="mono" style={{ fontSize: 13.5 }}>{a.nombre}</div>
              <div style={{ fontSize: 13, color: "var(--ll-text-2)" }}>{a.consumible}</div>
              <div style={{ fontSize: 12, color: "var(--ll-dim)" }}>
                {[a.ubicacion, a.piso ? "Piso " + a.piso : ""].filter(Boolean).join(" · ")}
                {a.actualizado ? " · leído " + fmtFechaHora(a.actualizado) : ""}
              </div>
            </div>
          </div>
        ))}
      </div>
    </Modal>
  );
}
