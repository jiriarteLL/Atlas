// ambiente.jsx — Preferencias visuales del diseño (color de acento, fondo animado, brillo, sonido)
// y el estado "entrado" que usa la esfera del fondo para acercarse al pasar la intro.
// Las preferencias se guardan en localStorage solo como comodidad del navegador: si no hay
// storage (modo privado, bloqueado) la app funciona igual con los valores por defecto.
import { createContext, useContext, useEffect, useMemo, useState } from "react";
import { iniciarSonido, detenerSonido } from "./sonido";

export const ACENTOS = {
  Cian: ["#22d3ee", "#818cf8"],
  Violeta: ["#a855f7", "#22d3ee"],
  Esmeralda: ["#34d399", "#22d3ee"],
  Ambar: ["#fbbf24", "#f472b6"],
};
// Los mismos acentos, mas oscuros, para los temas Claro y Blanco: el acento se usa como color de texto
// (nombres en tablas, enlaces, insignias) y tiene que leerse sobre blanco (>= 4.5:1).
export const ACENTOS_CLAROS = {
  Cian: ["#0e7490", "#4f46e5"],
  Violeta: ["#7e22ce", "#0e7490"],
  Esmeralda: ["#047857", "#0e7490"],
  Ambar: ["#b45309", "#be185d"],
};

// [clave, rotulo, color de fondo de la muestra, color de la barra del navegador]
export const TEMAS = [["oscuro", "Oscuro", "#080b14"], ["claro", "Claro", "#eef1f5"], ["blanco", "Blanco", "#ffffff"]];
export const esTemaClaro = (t) => t === "claro" || t === "blanco";

// La misma clave y la misma lectura las usa public/tema.js (cargado desde index.html) para pintar el tema antes del primer render.
const CLAVE = "inventario_ambiente";
const DEFECTO = { acento: "Cian", fx: true, brillo: 55, sonido: true, tema: "oscuro" };

function leer() {
  try {
    const v = JSON.parse(localStorage.getItem(CLAVE) || "{}");
    return { ...DEFECTO, ...v, acento: ACENTOS[v.acento] ? v.acento : DEFECTO.acento,
      tema: TEMAS.some(([k]) => k === v.tema) ? v.tema : DEFECTO.tema };
  } catch { return DEFECTO; }
}

const Ctx = createContext(null);

export function AmbienteProvider({ children }) {
  const [pref, setPref] = useState(leer);
  const [entrado, setEntrado] = useState(false);   // la esfera se acerca y se atenua
  const [sonando, setSonando] = useState(false);

  useEffect(() => {
    try { localStorage.setItem(CLAVE, JSON.stringify(pref)); } catch { /* sin storage */ }
    const [a, b] = (esTemaClaro(pref.tema) ? ACENTOS_CLAROS : ACENTOS)[pref.acento];
    const raiz = document.documentElement;
    raiz.dataset.theme = pref.tema;
    const h = raiz.style;
    h.setProperty("--accent", a);
    h.setProperty("--accent2", b);
    h.setProperty("--ll-brillo", String(pref.brillo / 100));
    const meta = document.querySelector('meta[name="theme-color"]');
    if (meta) meta.setAttribute("content", TEMAS.find(([k]) => k === pref.tema)[2]);
  }, [pref]);

  useEffect(() => () => detenerSonido(), []);

  const valor = useMemo(() => ({
    ...pref,
    color: (esTemaClaro(pref.tema) ? ACENTOS_CLAROS : ACENTOS)[pref.acento][0],
    claro: esTemaClaro(pref.tema),
    entrado, setEntrado, sonando,
    cambiar: (k, v) => setPref((p) => ({ ...p, [k]: v })),
    // El navegador solo deja arrancar audio despues de un clic: se llama desde botones.
    sonar: (on) => {
      if (on) { iniciarSonido(); setSonando(true); } else { detenerSonido(); setSonando(false); }
      setPref((p) => ({ ...p, sonido: on }));
    },
  }), [pref, entrado, sonando]);

  return <Ctx.Provider value={valor}>{children}</Ctx.Provider>;
}

export function useAmbiente() {
  const c = useContext(Ctx);
  if (!c) throw new Error("useAmbiente debe usarse dentro de <AmbienteProvider>");
  return c;
}
