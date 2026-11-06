// AlertaToner.jsx — Aviso emergente al entrar: impresoras con algun cartucho por debajo del umbral (10% por defecto,
// TONER_ALERTA_PCT en el servidor). Se muestra una vez por sesion; si aparece un cartucho nuevo por debajo, vuelve.
import { useCallback, useEffect, useState } from "react";
import { apiFetch } from "../api";
import { Modal } from "../diseno/comunes";
import { fmtFechaHora } from "../ui";

const CLAVE = "atlas_alerta_toner";
const firma = (alertas) => alertas.map((a) => a.id + ":" + a.consumible + ":" + a.porcentaje).join("|");

export default function AlertaToner({ onVer }) {
  const [datos, setDatos] = useState(null);

  useEffect(() => {
    let vivo = true;
    apiFetch("/api/impresoras/alertas")
      .then((r) => (r.ok ? r.json() : null))
      .then((d) => {
        if (!vivo || !d || !d.alertas?.length) return;
        let vista = "";
        try { vista = sessionStorage.getItem(CLAVE) || ""; } catch { /* sin storage */ }
        if (vista !== firma(d.alertas)) setDatos(d);
      })
      .catch(() => { /* sin red: no se avisa */ });
    return () => { vivo = false; };
  }, []);

  const cerrar = useCallback(() => {
    try { sessionStorage.setItem(CLAVE, firma(datos?.alertas || [])); } catch { /* sin storage */ }
    setDatos(null);
  }, [datos]);

  if (!datos) return null;
  const n = new Set(datos.alertas.map((a) => a.id)).size;
  return (
    <Modal titulo={`Tóner por debajo del ${datos.umbral}%`} onCerrar={cerrar}
      pie={<>
        <button type="button" className="ll-btn-borde" onClick={cerrar}>Cerrar</button>
        <button type="button" className="ll-btn-primario" onClick={() => { cerrar(); onVer(); }}>Ver impresoras</button>
      </>}>
      <div style={{ padding: "18px 26px", display: "flex", flexDirection: "column", gap: 12 }}>
        <p style={{ margin: 0, color: "var(--ll-text-2)", fontSize: 14 }}>
          {n === 1 ? "Una impresora tiene" : `${n} impresoras tienen`} cartuchos por cambiar pronto:
        </p>
        {datos.alertas.map((a) => (
          <div key={a.id + a.consumible} style={{ display: "flex", alignItems: "center", gap: 14, padding: "12px 14px",
            borderRadius: 12, background: "rgba(244,114,182,0.08)", border: "1px solid rgba(244,114,182,0.3)" }}>
            <span className="mono" style={{ fontSize: 22, fontWeight: 600, color: "#f472b6", minWidth: 48, textAlign: "right" }}>
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
