// api.js — cliente HTTP con token. El backend sirve este frontend: todas las rutas son del mismo origen.

export const API = "/api";
export const AUTH = "/auth";
let currentUsername = "";
export function setUsuarioActual(u) { currentUsername = u || ""; }
export function usuarioActual() { return currentUsername; }
export function authHeaders(extra) {
  const token = localStorage.getItem("abm_token");
  return { ...(extra || {}), ...(token ? { Authorization: "Bearer " + token } : {}) };
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
      localStorage.removeItem("abm_token");
      localStorage.removeItem("abm_user");
      alert("Tu sesion expiro. Volve a iniciar sesion.");
      window.location.reload();
    }
    throw new Error("Sesion expirada");
  }
  return r;
}
export const http = {
  get: (url) => fetch(url, { headers: authHeaders() }).then(chequear401).then(r => r.json()),
  post: (url, data) => fetch(url, { method:"POST", headers: authHeaders({"Content-Type":"application/json"}), body:JSON.stringify(data) }).then(chequear401).then(r => r.json()),
  put: (url, data) => fetch(url, { method:"PUT", headers: authHeaders({"Content-Type":"application/json"}), body:JSON.stringify(data) }).then(chequear401).then(r => r.json()),
  del: (url) => fetch(url, { method:"DELETE", headers: authHeaders() }).then(chequear401).then(r => r.json()),
};
