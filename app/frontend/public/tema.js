// tema.js — Aplica el tema guardado (Oscuro / Claro / Blanco) antes del primer render, sin parpadeo.
// Va como archivo aparte y no en linea porque la CSP de Atlas solo permite scripts propios (script-src 'self').
// Lee la misma preferencia que diseno/ambiente.jsx; si no hay storage queda el Oscuro.
(function () {
  var tema = "oscuro";
  try {
    var v = JSON.parse(localStorage.getItem("inventario_ambiente") || "{}");
    if (v.tema === "claro" || v.tema === "blanco") tema = v.tema;
  } catch { /* sin storage */ }
  document.documentElement.setAttribute("data-theme", tema);
  var meta = document.querySelector('meta[name="theme-color"]');
  if (meta) meta.setAttribute("content", tema === "blanco" ? "#ffffff" : tema === "claro" ? "#eef1f5" : "#080b14");
})();
