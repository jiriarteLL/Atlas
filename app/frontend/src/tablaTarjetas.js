// tablaTarjetas.js — En celular las tablas (.table-wrap) se ven como tarjetas: cada fila es una
// tarjeta y cada celda muestra el titulo de su columna. Este hook copia el texto de cada <th>
// al atributo data-label de las celdas; el CSS (styles.css, max-width 768px) hace el resto.
// Solo trabaja mientras la pantalla es chica, asi que en desktop no hace nada.
import { useEffect } from "react";

const CONSULTA = "(max-width: 768px)";

function etiquetar() {
  document.querySelectorAll(".table-wrap table").forEach(tabla => {
    const titulos = Array.from(tabla.querySelectorAll("thead th")).map(th =>
      th.textContent.replace(/[↑↓]/g, "").trim());
    if (!titulos.length) return;
    tabla.querySelectorAll("tbody tr").forEach(tr => {
      if (tr.querySelector("td[colspan]")) return; // filas de "sin datos"
      Array.from(tr.children).forEach((td, i) => {
        const t = titulos[i] || "";
        if (td.getAttribute("data-label") !== t) td.setAttribute("data-label", t);
      });
    });
  });
}

export function useTablaTarjetas() {
  useEffect(() => {
    const mq = window.matchMedia(CONSULTA);
    let observador = null, pendiente = false;
    const programar = () => {
      if (pendiente) return;
      pendiente = true;
      requestAnimationFrame(() => { pendiente = false; etiquetar(); });
    };
    const activar = () => {
      if (mq.matches && !observador) {
        observador = new MutationObserver(programar);
        observador.observe(document.body, { childList: true, subtree: true });
        programar();
      } else if (!mq.matches && observador) {
        observador.disconnect(); observador = null;
      }
    };
    activar();
    mq.addEventListener("change", activar);
    return () => { mq.removeEventListener("change", activar); if (observador) observador.disconnect(); };
  }, []);
}
