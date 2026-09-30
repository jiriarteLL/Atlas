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

const CLAVE = "inventario_ambiente";
const DEFECTO = { acento: "Cian", fx: true, brillo: 55, sonido: true };

function leer() {
  try {
    const v = JSON.parse(localStorage.getItem(CLAVE) || "{}");
    return { ...DEFECTO, ...v, acento: ACENTOS[v.acento] ? v.acento : DEFECTO.acento };
  } catch { return DEFECTO; }
}

const Ctx = createContext(null);

export function AmbienteProvider({ children }) {
  const [pref, setPref] = useState(leer);
  const [entrado, setEntrado] = useState(false);   // la esfera se acerca y se atenua
  const [sonando, setSonando] = useState(false);

  useEffect(() => {
    try { localStorage.setItem(CLAVE, JSON.stringify(pref)); } catch { /* sin storage */ }
    const [a, b] = ACENTOS[pref.acento];
    const h = document.documentElement.style;
    h.setProperty("--accent", a);
    h.setProperty("--accent2", b);
    h.setProperty("--ll-brillo", String(pref.brillo / 100));
  }, [pref]);

  useEffect(() => () => detenerSonido(), []);

  const valor = useMemo(() => ({
    ...pref,
    color: ACENTOS[pref.acento][0],
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
