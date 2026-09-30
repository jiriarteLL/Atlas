// api.js — cliente HTTP. El backend sirve este frontend: todas las rutas son del mismo origen.
//
// Sesion (SPEC §2.4.2 / BEST_PRACTICES §2.4):
// - El access token (JWT de 15 min) vive SOLO en memoria: nunca en localStorage/sessionStorage.
// - El refresh token viaja en una cookie HttpOnly que JS no puede leer; /auth/refresh lo canjea
//   por un access nuevo. Asi, un XSS no puede llevarse una sesion persistente.

export const API = "/api";
export const AUTH = "/auth";

let accessToken = "";
let alPerderSesion = null;
let currentUsername = "";

export function setAccessToken(t) { accessToken = t || ""; }
export function onSesionPerdida(fn) { alPerderSesion = fn; }
export function setUsuarioActual(u) { currentUsername = u || ""; }
export function usuarioActual() { return currentUsername; }

export function authHeaders(extra) {
  return { ...(extra || {}), ...(accessToken ? { Authorization: "Bearer " + accessToken } : {}) };
}

// Un solo refresh a la vez aunque varias llamadas reciban 401 juntas.
let refrescando = null;
export function refrescar() {
  if (!refrescando) {
    refrescando = fetch(AUTH + "/refresh", { method: "POST", credentials: "same-origin", headers: { "X-Requested-With": "fetch" } })
      .then(async (r) => {
        if (!r.ok) return null;
        const d = await r.json();
        accessToken = d.access_token;
        return d;
      })
      .catch(() => null)
      .finally(() => { refrescando = null; });
  }
  return refrescando;
}

// fetch con token; ante un 401 intenta renovar la sesion una vez y reintenta.
export async function apiFetch(url, opts = {}) {
  let r = await fetch(url, { ...opts, headers: authHeaders(opts.headers) });
  if (r.status === 401 && accessToken) {
    const d = await refrescar();
    if (d) r = await fetch(url, { ...opts, headers: authHeaders(opts.headers) });
  }
  return r;
}

let _avisado401 = false;
export function chequear401(r) {
  if (r.status === 403) {
    alert("No tenes permisos para realizar esta accion.");
    throw new Error("Sin permisos");
  }
  if (r.status === 422) {
    alert("Datos invalidos. Revisa los campos obligatorios.");
    throw new Error("Datos invalidos");
  }
  if (r.status === 401) {
    if (!_avisado401) {
      _avisado401 = true;
      accessToken = "";
      alert("Tu sesion expiro. Volve a iniciar sesion.");
      if (alPerderSesion) alPerderSesion(); else window.location.reload();
      setTimeout(() => { _avisado401 = false; }, 2000);
    }
    throw new Error("Sesion expirada");
  }
  return r;
}

const json = (h) => ({ ...h, "Content-Type": "application/json" });
export const http = {
  get: (url) => apiFetch(url).then(chequear401).then(r => r.json()),
  post: (url, data) => apiFetch(url, { method: "POST", headers: json(), body: JSON.stringify(data) }).then(chequear401).then(r => r.json()),
  put: (url, data) => apiFetch(url, { method: "PUT", headers: json(), body: JSON.stringify(data) }).then(chequear401).then(r => r.json()),
  del: (url) => apiFetch(url, { method: "DELETE" }).then(chequear401).then(r => r.json()),
};
