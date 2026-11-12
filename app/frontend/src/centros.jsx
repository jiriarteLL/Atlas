// centros.jsx — Sugerencias de centro de costo (texto libre: los valores ya usados en Atlas, /api/costos/centros)
// y reparto entre dos personas. El backend normaliza el centro (espacios simples y MAYÚSCULAS).
import { useEffect, useState } from "react";
import { apiFetch } from "./api";

let cache = null;   // una sola consulta por sesión de la página (se refresca al guardar uno nuevo)

export function refrescarCentros() { cache = null; }

export function DatalistCentros({ id = "ll-centros-costo" }) {
  const [lista, setLista] = useState(cache || []);
  useEffect(() => {
    if (cache) return undefined;
    let vivo = true;
    apiFetch("/api/costos/centros").then((r) => (r.ok ? r.json() : [])).then((d) => {
      cache = Array.isArray(d) ? d : [];
      if (vivo) setLista(cache);
    }).catch(() => {});
    return () => { vivo = false; };
  }, []);
  return <datalist id={id}>{lista.map((c) => <option key={c} value={c} />)}</datalist>;
}

// % que paga el principal: vacío = 50 si hay segundo usuario, 100 si no
export const pctEfectivo = (pct, haySecundario) => (!haySecundario ? 100 : pct == null || pct === "" ? 50 : Number(pct));
