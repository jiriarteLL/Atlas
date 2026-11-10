// Telefonia.jsx — Internos de la central 3CX y los telefonos (Grandstream IP / WiFi) que los usan.
// Los internos entran por la exportacion de usuarios de la consola de 3CX (boton "Importar exportacion de 3CX");
// la IP de cada telefono la completa el relevamiento DHCP por MAC. Tipo, sede, piso, estado y notas se editan
// en la ficha lateral y no los pisan ni la importacion ni el relevamiento.
import { useCallback, useEffect, useMemo, useRef, useState } from "react";
import { apiFetch } from "../api";
import { SEDES, fmtFechaHora } from "../ui";
import { Drawer, Ficha, Rotulo } from "../diseno/comunes";

const URL = "/api/telefonia";
const TIPOS = [["", "Todos los tipos"], ["IP", "IP (escritorio)"], ["WiFi", "WiFi"], ["-", "Sin equipo"]];
const ESTADOS = ["Activa", "Deshabilitada", "Baja"];
const COLOR_ESTADO = { Activa: "var(--ll-verde)", Deshabilitada: "var(--ll-ambar)", Baja: "var(--ll-dim)" };

async function pedir(url, opciones) {
  const r = await apiFetch(url, opciones);
  const d = await r.json().catch(() => ({}));
  if (!r.ok) {
    const det = Array.isArray(d.detail) ? d.detail.map((x) => x.msg).join(" · ") : d.detail;
    throw new Error(typeof det === "string" ? det : "Error " + r.status);
  }
  return d;
}

// "C074ADA88EEA" -> "C0:74:AD:A8:8E:EA"
// "ABELOVICH, José Daniel" y "Daniel Abelovich" son la misma persona: comparte alguna palabra (sin tildes ni mayúsculas)
const palabras = (s) => (s || "").normalize("NFD").replace(/[̀-ͯ]/g, "").toLowerCase().split(/[^a-z]+/).filter((p) => p.length > 2);
const mismoNombre = (a, b) => { const pb = new Set(palabras(b)); return palabras(a).some((p) => pb.has(p)); };
const fmtMac = (m) => (m && m.length === 12 ? m.match(/.{2}/g).join(":") : m || "");

function EstadoLinea({ valor, en3cx }) {
  return (
    <span style={{ display: "inline-flex", flexDirection: "column", gap: 2 }}>
      <span style={{ color: COLOR_ESTADO[valor] || "var(--ll-dim)", fontWeight: 600, fontSize: 12.5 }}>● {valor || "—"}</span>
      {en3cx === false && <span className="tenue" style={{ fontSize: 11 }}>No figura en la última exportación</span>}
    </span>
  );
}

export default function Telefonia({ puedeEditar, avisar }) {
  const [datos, setDatos] = useState({ lineas: [], sin_interno: [], resumen: {} });
  const [cargando, setCargando] = useState(true);
  const [error, setError] = useState("");
  const [filtros, setFiltros] = useState({ q: "", sede: "", tipo: "", estado: "", tarjeta: "" });
  const [abierta, setAbierta] = useState(null);
  const [importando, setImportando] = useState(false);
  const archivo = useRef(null);

  const cargar = useCallback(async () => {
    setCargando(true);
    try { setDatos(await pedir(URL)); setError(""); } catch (e) { setError(e.message); } finally { setCargando(false); }
  }, []);
  useEffect(() => { cargar(); }, [cargar]);

  const { lineas, sin_interno: sinInterno, resumen } = datos;
  const filtradas = useMemo(() => {
    const q = filtros.q.trim().toLowerCase().replace(/[:-]/g, "");
    return lineas.filter((x) => (!q || [x.interno, x.asignado, x.nombre, x.mac, x.ip, x.email, x.modelo].some((v) => String(v || "").toLowerCase().replace(/[:-]/g, "").includes(q)))
      && (!filtros.sede || x.sede === filtros.sede)
      && (!filtros.tipo || (filtros.tipo === "-" ? !x.tipo : x.tipo === filtros.tipo))
      && (!filtros.estado || x.estado === filtros.estado)
      && (filtros.tarjeta !== "telefono" || x.mac)
      && (filtros.tarjeta !== "sin_ip" || (x.mac && !x.ip)));
  }, [lineas, filtros]);
  const f = (k) => (e) => setFiltros({ ...filtros, [k]: e.target.value });

  async function importar(e) {
    const a = e.target.files[0];
    e.target.value = "";
    if (!a) return;
    setImportando(true);
    try {
      const fd = new FormData();
      fd.append("archivo", a);
      const r = await pedir(URL + "/importar-3cx", { method: "POST", body: fd });
      avisar && avisar(`3CX: ${r.altas} altas, ${r.cambios} cambios, ${r.fuera_de_3cx} ya no figuran. Borrá el CSV: trae PIN y claves.`);
      await cargar();
    } catch (err) { alert("No se pudo importar: " + err.message); } finally { setImportando(false); }
  }

  const tarjetas = [
    ["", "Internos", resumen.internos, "var(--accent)"],
    ["telefono", "Con teléfono", resumen.con_telefono, "var(--ll-verde)"],
    ["sin_ip", "Teléfonos sin IP", resumen.sin_ip, "var(--ll-ambar)"],
    ["sin_interno", "Teléfonos sin interno", resumen.sin_interno, "var(--ll-rosa)"],
  ];

  return (
    <div>
      <div style={{ display: "grid", gridTemplateColumns: "repeat(auto-fill, minmax(150px, 1fr))", gap: 12, marginBottom: 20 }}>
        {tarjetas.map(([k, rotulo, n, color]) => {
          const activa = k && filtros.tarjeta === k;
          return (
            <button key={rotulo} type="button" className="ll-card hover" aria-pressed={!!activa}
              onClick={() => k === "sin_interno" ? document.getElementById("tel-sin-interno")?.scrollIntoView({ behavior: "smooth" })
                : setFiltros({ ...filtros, tarjeta: activa ? "" : k })}
              style={{ textAlign: "left", padding: "14px 16px", cursor: "pointer", color: "inherit", font: "inherit",
                borderColor: activa ? color : undefined, boxShadow: activa ? `0 0 0 1px ${color}` : undefined }}>
              <div className="mono" style={{ fontSize: 24, fontWeight: 600, color: n ? color : "var(--ll-dim)" }}>{n ?? 0}</div>
              <div style={{ fontSize: 12.5, color: "var(--ll-text-2)", marginTop: 4 }}>{rotulo}</div>
            </button>
          );
        })}
      </div>

      <div className="ll-barra">
        <div className="ll-buscador">
          <span>⌕</span>
          <input className="ll-input" value={filtros.q} onChange={f("q")} placeholder="Buscar por interno, nombre, MAC o IP…" aria-label="Buscar internos" />
        </div>
        <select className="ll-select" style={{ width: "auto" }} value={filtros.sede} onChange={f("sede")} aria-label="Sede">
          <option value="">Todas las sedes</option>
          {SEDES.map((s) => <option key={s}>{s}</option>)}
        </select>
        <select className="ll-select" style={{ width: "auto" }} value={filtros.tipo} onChange={f("tipo")} aria-label="Tipo">
          {TIPOS.map(([v, l]) => <option key={v} value={v}>{l}</option>)}
        </select>
        <select className="ll-select" style={{ width: "auto" }} value={filtros.estado} onChange={f("estado")} aria-label="Estado">
          <option value="">Todos los estados</option>
          {ESTADOS.map((s) => <option key={s}>{s}</option>)}
        </select>
        <span className="ll-contador">{filtradas.length} internos</span>
        <span style={{ flex: 1 }} />
        {puedeEditar && <>
          <button className="ll-btn-borde" disabled={importando} onClick={() => archivo.current.click()}
            title="En la consola de 3CX: Usuarios → seleccionar todos → Exportar">{importando ? "Importando…" : "Importar exportación de 3CX"}</button>
          <input ref={archivo} type="file" accept=".csv,text/csv" onChange={importar} style={{ display: "none" }} />
        </>}
      </div>
      {puedeEditar && !lineas.length && !cargando && <div className="tenue" style={{ fontSize: 12.5, margin: "-6px 0 14px" }}>
        Para cargar los internos: en la consola de 3CX, <b>Usuarios → seleccionar todos → Exportar</b>, y subí ese CSV con el botón de arriba.
        Atlas solo lee interno, nombre, mail, DID, departamento, MAC y modelo: nunca guarda PIN ni claves.
      </div>}

      {error && <div className="ll-vacio" style={{ color: "var(--ll-warn)" }}>No se pudo cargar la telefonía: {error}</div>}
      <div className="ll-card" style={{ overflow: "hidden" }}>
        <div className="ll-tabla-wrap">
          <table className="ll-tabla" style={{ minWidth: 1100 }}>
            <thead><tr>
              <th>INTERNO</th><th>NOMBRE</th><th>SEDE / PISO</th><th>TIPO</th><th>MODELO</th><th>MAC</th><th>IP</th>
              <th>ESTADO</th><th>ÚLTIMA VEZ VISTO</th>
            </tr></thead>
            <tbody>
              {filtradas.map((x) => (
                <tr key={x.id} className="click" onClick={() => setAbierta(x.id)}>
                  <td className="nombre mono">{x.interno}</td>
                  <td>{x.asignado || x.nombre || <span className="tenue">—</span>}
                    <div className="tenue" style={{ fontSize: 11.5 }}>
                      {/* la guia de internos manda; si 3CX dice otra cosa se muestra para corregirlo en la consola */}
                      {x.asignado && x.nombre && !mismoNombre(x.asignado, x.nombre) ? "En 3CX: " + x.nombre : x.departamento}
                    </div></td>
                  <td>{x.sede || <span className="tenue">—</span>}{x.piso ? " · piso " + x.piso : ""}</td>
                  <td>{x.tipo ? <span className={"ll-chip" + (x.tipo === "WiFi" ? "" : " acento")}>{x.tipo}</span> : <span className="tenue">Sin equipo</span>}</td>
                  <td>{x.modelo || <span className="tenue">—</span>}</td>
                  <td className="mono" style={{ fontSize: 12.5 }}>{fmtMac(x.mac) || <span className="tenue">—</span>}</td>
                  <td className="mono">{x.ip
                    ? <a href={"http://" + x.ip} target="_blank" rel="noopener noreferrer" onClick={(e) => e.stopPropagation()}>{x.ip}</a>
                    : x.mac ? <span style={{ color: "var(--ll-ambar)", fontSize: 12 }}>sin IP</span> : <span className="tenue">—</span>}</td>
                  <td><EstadoLinea valor={x.estado} en3cx={x.en_3cx} /></td>
                  <td className="mono tenue" style={{ fontSize: 12.5 }}>{x.ip_visto ? fmtFechaHora(x.ip_visto) : "—"}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
        {!cargando && !filtradas.length && <div className="ll-vacio">{lineas.length ? "Sin internos que coincidan con los filtros." : "Todavía no hay internos cargados."}</div>}
        {cargando && !lineas.length && <div className="ll-vacio">Cargando internos…</div>}
      </div>

      <div id="tel-sin-interno" style={{ marginTop: 22 }}>
        <Rotulo>TELÉFONOS SIN INTERNO ({sinInterno.length})</Rotulo>
        {sinInterno.length ? <div className="ll-card" style={{ overflow: "hidden" }}>
          <div className="ll-tabla-wrap">
            <table className="ll-tabla">
              <thead><tr><th>MAC</th><th>IP</th><th>HOSTNAME</th><th>VISTO</th></tr></thead>
              <tbody>{sinInterno.map((t) => (
                <tr key={t.mac}>
                  <td className="mono">{fmtMac(t.mac)}</td>
                  <td className="mono">{t.ip ? <a href={"http://" + t.ip} target="_blank" rel="noopener noreferrer">{t.ip}</a> : "—"}</td>
                  <td>{t.hostname || <span className="tenue">—</span>}</td>
                  <td className="mono tenue" style={{ fontSize: 12.5 }}>{fmtFechaHora(t.visto)}</td>
                </tr>))}
              </tbody>
            </table>
          </div>
        </div> : <div className="tenue" style={{ fontSize: 13 }}>Todos los teléfonos que ve el DHCP tienen un interno en 3CX.</div>}
      </div>

      {abierta && <FichaLinea id={abierta} puedeEditar={puedeEditar} avisar={avisar} onCerrar={() => setAbierta(null)} onGuardada={cargar} />}
    </div>
  );
}

// ---------------------------------------------------------------- ficha
function FichaLinea({ id, puedeEditar, avisar, onCerrar, onGuardada }) {
  const [x, setX] = useState(null);
  const [error, setError] = useState("");
  const [edicion, setEdicion] = useState(null);
  const [guardando, setGuardando] = useState(false);

  const cargar = useCallback(async () => {
    try { setX(await pedir(URL + "/" + id)); setError(""); } catch (e) { setError(e.message); }
  }, [id]);
  useEffect(() => { cargar(); }, [cargar]);

  const editar = () => setEdicion({ asignado: x.asignado || "", tipo: x.tipo || "", sede: x.sede_manual ? x.sede : "", piso: x.piso || "",
    estado: x.estado || "Activa", notas: x.notas || "", ip: x.ip_origen === "manual" ? x.ip : "" });

  async function guardar() {
    setGuardando(true);
    try {
      setX(await pedir(URL + "/" + id, { method: "PUT", headers: { "Content-Type": "application/json" }, body: JSON.stringify(edicion) }));
      setEdicion(null);
      setError("");
      avisar && avisar("Interno actualizado");
      onGuardada && onGuardada();
    } catch (e) { setError(e.message); } finally { setGuardando(false); }
  }
  const set = (k) => (e) => setEdicion({ ...edicion, [k]: e.target.value });

  return (
    <Drawer abierto onCerrar={onCerrar} ancho>
      <div className="ll-drawer-cab">
        <div style={{ minWidth: 0 }}>
          <div className="mono" style={{ fontSize: 21, fontWeight: 600, color: "var(--accent)", letterSpacing: -0.3 }}>{x ? "Interno " + x.interno : "Interno"}</div>
          {x && <div style={{ fontSize: 12.5, color: "var(--ll-dim)", marginTop: 4 }}>{[x.asignado || x.nombre, x.modelo].filter(Boolean).join(" · ")}</div>}
        </div>
        <button className="ll-cerrar" onClick={onCerrar} aria-label="Cerrar">✕</button>
      </div>
      {error && <div className="ll-vacio" style={{ color: "var(--ll-warn)", padding: 12 }}>{error}</div>}
      {!x ? <div className="ll-vacio">Cargando…</div> : edicion ? (
        <div style={{ display: "flex", flexDirection: "column", gap: 14 }}>
          <Rotulo>EDITAR DATOS DEL INTERNO</Rotulo>
          <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: 12 }}>
            <label className="ll-campo" style={{ gridColumn: "1 / -1" }}><span>ASIGNADO A (GUÍA DE INTERNOS)</span>
              <input className="ll-input" value={edicion.asignado} onChange={set("asignado")} placeholder={x.nombre ? "En 3CX: " + x.nombre : ""} autoComplete="off" /></label>
            <label className="ll-campo"><span>TIPO DE TELÉFONO</span>
              <select className="ll-select" value={edicion.tipo} onChange={set("tipo")}>
                <option value="IP">IP (escritorio)</option><option value="WiFi">WiFi</option><option value="">Sin equipo</option>
              </select></label>
            <label className="ll-campo"><span>ESTADO</span>
              <select className="ll-select" value={edicion.estado} onChange={set("estado")}>{ESTADOS.map((s) => <option key={s}>{s}</option>)}</select></label>
            <label className="ll-campo"><span>SEDE</span>
              <select className="ll-select" value={edicion.sede} onChange={set("sede")}>
                <option value="">Automática ({x.sede || "sin dato"})</option>{SEDES.map((s) => <option key={s}>{s}</option>)}
              </select></label>
            <label className="ll-campo"><span>PISO</span><input className="ll-input" value={edicion.piso} onChange={set("piso")} autoComplete="off" /></label>
            <label className="ll-campo" style={{ gridColumn: "1 / -1" }}><span>IP MANUAL (VACÍO = LA DEL DHCP)</span>
              <input className="ll-input mono" value={edicion.ip} onChange={set("ip")} placeholder={x.ip_origen === "dhcp" ? "Hoy por DHCP: " + x.ip : "Sin IP"} autoComplete="off" /></label>
          </div>
          <label className="ll-campo"><span>NOTAS</span><textarea className="ll-input" rows={3} value={edicion.notas} onChange={set("notas")} /></label>
          <div style={{ fontSize: 12, color: "var(--ll-dim)" }}>Interno, nombre, MAC y modelo vienen de 3CX: se corrigen en la consola y se reimporta la exportación.</div>
          <div style={{ display: "flex", gap: 10, justifyContent: "flex-end" }}>
            <button className="ll-btn-borde" onClick={() => setEdicion(null)}>Cancelar</button>
            <button className="ll-btn-primario" disabled={guardando} onClick={guardar}>{guardando ? "Guardando…" : "Guardar"}</button>
          </div>
        </div>
      ) : (<>
        <div style={{ display: "flex", alignItems: "center", gap: 10, flexWrap: "wrap" }}>
          <EstadoLinea valor={x.estado} en3cx={x.en_3cx} />
          {x.tipo && <span className={"ll-chip" + (x.tipo === "WiFi" ? "" : " acento")}>{x.tipo}</span>}
          <span style={{ flex: 1 }} />
          {puedeEditar && <button className="ll-btn-borde" onClick={editar}>Editar</button>}
        </div>
        <div>
          <Rotulo>INTERNO (3CX)</Rotulo>
          <Ficha filas={[["Interno", x.interno], ["Asignado a (guía)", x.asignado], ["Nombre en 3CX", x.nombre], ["Mail", x.email], ["Departamento", x.departamento],
            ["DID", x.did], ["Deshabilitado en 3CX", x.deshabilitado ? "Sí" : "No"]]} />
        </div>
        <div>
          <Rotulo>TELÉFONO</Rotulo>
          <Ficha filas={[["Modelo", x.modelo], ["MAC", fmtMac(x.mac)], ["IP", x.ip ? `${x.ip} (${x.ip_origen === "manual" ? "cargada a mano" : "DHCP"})` : ""],
            ["Hostname", x.hostname], ["Última vez visto", x.ip_visto ? fmtFechaHora(x.ip_visto) : ""],
            ["Sede", x.sede ? `${x.sede}${x.sede_manual ? " (elegida a mano)" : ""}` : ""], ["Piso", x.piso], ["Notas", x.notas]]} />
        </div>
      </>)}
    </Drawer>
  );
}
