// graficos.jsx — Carga recharts bajo demanda (es lo mas pesado del bundle).
// useGraficos() devuelve el modulo recharts; mientras se descarga devuelve un reemplazo
// donde ResponsiveContainer es un espacio reservado del mismo alto y el resto no dibuja
// nada. Asi los graficos se escriben igual (<G.BarChart>, <G.Bar>...) y aparecen solos
// cuando llega la libreria, sin saltos de layout.
import { useState, useEffect } from "react";

let modulo = null;
let pedido = null;
const cargar = () => (pedido ||= import("recharts").then(m => (modulo = m)));

const Nada = () => null;
const Reservado = ({ height }) => (
  <div style={{height: height || 260, display:"flex", alignItems:"center", justifyContent:"center",
    color:"var(--text-muted)", fontSize:12}}>Cargando gráfico…</div>
);
const PROVISORIO = new Proxy({ ResponsiveContainer: Reservado }, { get: (o, k) => o[k] || Nada });

export function useGraficos() {
  const [m, setM] = useState(modulo);
  useEffect(() => {
    if (modulo) return;
    let vivo = true;
    cargar().then(x => { if (vivo) setM(x); }).catch((e) => { pedido = null; console.error("No se pudo cargar la libreria de graficos:", e); });
    return () => { vivo = false; };
  }, []);
  return m || PROVISORIO;
}
