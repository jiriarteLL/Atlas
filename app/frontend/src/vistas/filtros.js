// filtros.js — Calculos compartidos sobre los activos (garantia, dias sin reportar, filtros especiales).
import { fechaUtc } from "../ui";
import { estadoCiclo } from "../diseno/comunes";

// Color del estado de BitLocker (ficha del activo y Notebooks y PC)
export const COLOR_CIFRADO = (c) => c === "Cifrado" ? "var(--ll-verde)" : (c || "").startsWith("Cifrado (") ? "var(--ll-ambar)"
  : c === "Sin cifrar" ? "var(--ll-rosa)" : c === "Cifrando" ? "var(--ll-azul)" : "var(--ll-dim)";

export function diasGarantia(a) {
  if (!a.garantia || a.garantia === "-") return null;
  const p = String(a.garantia).split("-");
  if (p.length < 3) return null;
  return Math.floor((new Date(+p[0], +p[1] - 1, +p[2]) - new Date()) / 86400000);
}

export const diasSinReportar = (a) => a.updated ? Math.floor((Date.now() - fechaUtc(a.updated).getTime()) / 86400000) : 9999;

export const glpiDe = (glpiMap, a) => glpiMap[(a.serial || "").trim().toUpperCase()];

// Filtros especiales del selector de estado (los que empiezan con __).
export const ESPECIALES = [
  ["__sin_usuario__", "Sin usuario asignado", true],
  ["__sin_reportar__", "Sin reportar +30 días"],
  ["__gar_vencen__", "Garantía vence en 90 días"],
  ["__sin_edr__", "Sin CrowdStrike activo"],
  ["__sin_cifrar__", "Discos sin cifrar"],
  ["__anydesk__", "Con AnyDesk instalado"],
  ["__bateria__", "Batería bajo 70%"],
];

export function cumpleEstado(a, fEstado, glpiMap) {
  const gl = glpiDe(glpiMap, a);
  switch (fEstado) {
    case "": return true;
    case "__sin_usuario__": return !a.usuario || a.usuario.trim() === "";
    case "__sin_reportar__": return diasSinReportar(a) > 30;
    case "__gar_vencen__": { const d = diasGarantia(a); return d !== null && d >= 0 && d <= 90; }
    case "__sin_edr__": return !!gl && gl.edr !== "Activo";
    case "__sin_cifrar__": return !!gl && !!gl.volumenes_sin_cifrar;
    case "__anydesk__": return !!gl && (gl.acceso_remoto || "").includes("anydesk");
    case "__bateria__": return !!gl && gl.bateria_salud != null && gl.bateria_salud < 70;
    default: return a.estado === fEstado || estadoCiclo(a) === fEstado;
  }
}
