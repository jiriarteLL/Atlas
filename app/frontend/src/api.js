// api.js — URLs de los backends y cliente HTTP con token (Inventario y UserManager).

export const API = window.location.protocol === "https:" ? "https://192.168.100.116:8443/api" : "http://192.168.100.116:8000/api";
export const API_UM = window.location.protocol === "https:" ? "https://192.168.100.116:8444/api" : "http://192.168.100.116:8001/api";
let currentUsername = "";
export function setUsuarioActual(u) { currentUsername = u || ""; }
export function conUsuario(url) {
  const sep = url.includes("?") ? "&" : "?";
  return url + sep + "usuario=" + encodeURIComponent(currentUsername || "");
}
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
// Llamadas al UserManager que necesitan la Response cruda: mismo token y manejo de 401/403/422 que http.
export const umFetch = (url, opts = {}) => fetch(url, { ...opts, headers: authHeaders(opts.headers) }).then(chequear401);
export const http = {
  get: (url) => fetch(url, { headers: authHeaders() }).then(chequear401).then(r => r.json()),
  post: (url, data) => fetch(conUsuario(url), { method:"POST", headers: authHeaders({"Content-Type":"application/json"}), body:JSON.stringify(data) }).then(chequear401).then(r => r.json()),
  put: (url, data) => fetch(conUsuario(url), { method:"PUT", headers: authHeaders({"Content-Type":"application/json"}), body:JSON.stringify(data) }).then(chequear401).then(r => r.json()),
  del: (url) => fetch(conUsuario(url), { method:"DELETE", headers: authHeaders() }).then(chequear401).then(r => r.json()),
};
