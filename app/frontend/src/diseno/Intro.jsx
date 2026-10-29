// Intro.jsx — Secuencia de arranque: contador de activos, barra y registro, y el boton ENTRAR.
// Antes del login no se puede consultar la API, asi que el contador usa el ultimo total visto
// en este navegador ("—" la primera vez, para no sugerir un inventario vacio). Los mensajes son genericos: no muestran IPs ni hosts.
import { useEffect, useRef, useState } from "react";
import { useAmbiente } from "./ambiente";

const REGISTRO = [
  "> iniciando inventario de activos",
  "> verificando servicios",
  "> cargando sedes y equipos",
  "> indexando notebooks · impresoras · servidores",
  "> listo",
];
const CLAVE_TOTAL = "inventario_ultimo_total";

export function recordarTotal(n) {
  try { localStorage.setItem(CLAVE_TOTAL, String(n)); } catch { /* sin storage */ }
}
function ultimoTotal() {
  try {
    const n = parseInt(localStorage.getItem(CLAVE_TOTAL) ?? "", 10);
    return Number.isFinite(n) && n >= 0 ? n : null;
  } catch { return null; }
}

export default function Intro({ alEntrar }) {
  const { sonar, sonido } = useAmbiente();
  const [lineas, setLineas] = useState([]);
  const [listo, setListo] = useState(false);
  const [saliendo, setSaliendo] = useState(false);
  const contador = useRef(null);
  const barra = useRef(null);

  useEffect(() => {
    const timers = REGISTRO.map((txt, i) => setTimeout(() => setLineas((l) => [...l, txt]), 300 + i * 470));
    const meta = ultimoTotal(), dur = 2700, t0 = performance.now();
    let raf = 0;
    const paso = (ahora) => {
      const p = Math.min((ahora - t0) / dur, 1);
      const e = 1 - Math.pow(1 - p, 3);
      if (contador.current) contador.current.textContent = meta === null ? "—" : String(Math.round(e * meta));
      if (barra.current) barra.current.style.width = (e * 100) + "%";
      if (p < 1) raf = requestAnimationFrame(paso); else setListo(true);
    };
    raf = requestAnimationFrame(paso);
    return () => { timers.forEach(clearTimeout); cancelAnimationFrame(raf); };
  }, []);

  function entrar() {
    if (saliendo) return;
    setSaliendo(true);
    if (sonido) sonar(true);
    setTimeout(alEntrar, 780);
  }

  useEffect(() => {
    if (!listo) return undefined;
    const tecla = (e) => { if (e.key === "Enter") entrar(); };
    window.addEventListener("keydown", tecla);
    return () => window.removeEventListener("keydown", tecla);
  });

  return (
    <div className="ll-intro" style={{ opacity: saliendo ? 0 : 1, pointerEvents: saliendo ? "none" : "auto" }}>
      <div className="ll-intro-logo">LLyA</div>
      <h1>INVENTARIO LLYA</h1>
      <div className="mono" style={{ fontSize: 12, letterSpacing: 5, color: "var(--accent)" }}>SISTEMA DE ACTIVOS · TI</div>
      <div style={{ display: "flex", alignItems: "baseline", gap: 15, marginTop: 42 }}>
        <span ref={contador} className="mono" style={{ fontSize: 64, fontWeight: 600, letterSpacing: -2, color: "#fff" }}>{ultimoTotal() === null ? "—" : "0"}</span>
        <span className="mono" style={{ fontSize: 13, letterSpacing: 3, color: "var(--ll-dim)" }}>ACTIVOS REGISTRADOS</span>
      </div>
      <div className="ll-intro-barra"><div ref={barra} style={{ width: "0%" }} /></div>
      <div className="ll-intro-log" aria-live="polite">{lineas.map((l) => <div key={l}>{l}</div>)}</div>
      <button className="ll-entrar" onClick={entrar}
        style={{ opacity: listo ? 1 : 0, pointerEvents: listo ? "auto" : "none", transform: listo ? "translateY(0)" : "translateY(10px)" }}>
        ENTRAR ⏎
      </button>
    </div>
  );
}
