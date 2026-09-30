// Escenario.jsx — Fondo comun a intro, login y app: esfera 3D, grilla, brillos y
// el halo que sigue al cursor. Todo decorativo (aria-hidden, sin eventos).
import { useEffect, useRef } from "react";
import Esfera from "./Esfera";
import { useAmbiente } from "./ambiente";

export default function Escenario({ children }) {
  const cursor = useRef(null);
  const { fx } = useAmbiente();

  useEffect(() => {
    if (!fx || window.matchMedia("(prefers-reduced-motion: reduce)").matches) return undefined;
    let pendiente = false, x = 0, y = 0;
    const mover = (e) => {
      x = e.clientX; y = e.clientY;
      if (pendiente) return;
      pendiente = true;
      requestAnimationFrame(() => {
        pendiente = false;
        if (cursor.current) cursor.current.style.transform = `translate(${x}px,${y}px)`;
      });
    };
    window.addEventListener("mousemove", mover, { passive: true });
    return () => window.removeEventListener("mousemove", mover);
  }, [fx]);

  return (
    <div className="ll-app">
      <Esfera />
      {fx && <>
        <div className="ll-fx-grid" aria-hidden="true" />
        <div className="ll-glow-a" aria-hidden="true" />
        <div className="ll-glow-b" aria-hidden="true" />
        <div className="ll-cursor" ref={cursor} aria-hidden="true" />
      </>}
      {children}
    </div>
  );
}
