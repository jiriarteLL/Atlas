// Impresoras.jsx — Subseccion de Activos: lista de impresoras (red y USB personales) con filtros, toner y contador,
// y la ficha lateral con consumibles, PCs que la tienen instalada y edicion de los datos manuales.
// Las credenciales de administracion no estan en Atlas: la ficha solo muestra la referencia (credencial_ref).
import { useCallback, useEffect, useMemo, useState } from "react";
import { apiFetch } from "../api";
import { SEDES, fmtFechaHora } from "../ui";
import { Drawer, Estado, Ficha, Rotulo } from "../diseno/comunes";

const URL = "/api/impresoras";
const TENENCIAS = [["", "Sin dato"], ["propia", "Propia"], ["alquilada", "Alquilada"], ["tercerizada", "Tercerizada"]];

async function pedir(url, metodo, cuerpo) {
  const r = await apiFetch(url, { method: metodo || "GET", headers: cuerpo ? { "Content-Type": "application/json" } : undefined,
    body: cuerpo ? JSON.stringify(cuerpo) : undefined });
  const d = await r.json().catch(() => ({}));
  if (!r.ok) {
    const det = Array.isArray(d.detail) ? d.detail.map((x) => x.msg).join(" · ") : d.detail;
    throw new Error(typeof det === "string" ? det : "Error " + r.status);
  }
  return d;
}

const pctMinimo = (i) => {
  const ps = (i.consumibles || []).map((c) => c.porcentaje).filter((p) => p !== null && p !== undefined && p >= 0);
  return ps.length ? Math.min(...ps) : null;
};
const colorToner = (p) => (p === null ? "var(--ll-dim)" : p <= 15 ? "var(--ll-rosa)" : p <= 30 ? "var(--ll-ambar)" : "var(--ll-verde)");

function BarraToner({ porcentaje, etiqueta }) {
  if (porcentaje === null || porcentaje === undefined) return <span className="tenue">—</span>;
  const c = colorToner(porcentaje);
  return (
    <span style={{ display: "inline-flex", alignItems: "center", gap: 8 }} title={etiqueta || ""}>
      <span style={{ width: 70, height: 7, borderRadius: 4, background: "var(--ll-track)", overflow: "hidden" }}>
        <span style={{ display: "block", width: Math.max(2, Math.min(100, porcentaje)) + "%", height: "100%", background: c }} />
      </span>
      <span className="mono" style={{ color: c, fontSize: 12 }}>{porcentaje}%</span>
    </span>
  );
}

// "HP" + "HP LaserJet M605" -> "HP LaserJet M605" (muchos modelos ya traen la marca)
const modeloDe = (i) => {
  const m = (i.modelo || "").trim(), b = (i.marca || "").trim();
  return !b || m.toLowerCase().startsWith(b.toLowerCase()) ? m : (b + " " + m).trim();
};
const textoConexion = (d) => (d.conexion === "usb" ? "USB" : "Red");
const textoTenencia = (d) => [TENENCIAS.find(([v]) => v === d.tenencia)?.[1] || "", d.proveedor].filter(Boolean).join(" · ");

export default function Impresoras({ puedeEditar, avisar }) {
  const [lista, setLista] = useState([]);
  const [cargando, setCargando] = useState(true);
  const [error, setError] = useState("");
  const [filtros, setFiltros] = useState({ q: "", sede: "", conexion: "", tenencia: "" });
  const [abierta, setAbierta] = useState(null);   // id de la impresora en la ficha

  const cargar = useCallback(async () => {
    setCargando(true);
    try { setLista(await pedir(URL)); setError(""); } catch (e) { setError(e.message); } finally { setCargando(false); }
  }, []);
  useEffect(() => { cargar(); }, [cargar]);

  const filtradas = useMemo(() => {
    const q = filtros.q.trim().toLowerCase();
    return lista.filter((i) => {
      const d = i.detalle || {};
      return (!q || [i.nombre, i.marca, i.modelo, i.serial, i.usuario, i.ip, d.nombre_cola, d.piso].some((v) => String(v || "").toLowerCase().includes(q)))
        && (!filtros.sede || i.ubicacion === filtros.sede)
        && (!filtros.conexion || d.conexion === filtros.conexion)
        && (!filtros.tenencia || (filtros.tenencia === "-" ? !d.tenencia : d.tenencia === filtros.tenencia));
    });
  }, [lista, filtros]);
  const f = (k) => (e) => setFiltros({ ...filtros, [k]: e.target.value });

  return (
    <div>
      <div className="ll-barra">
        <div className="ll-buscador">
          <span>⌕</span>
          <input className="ll-input" value={filtros.q} onChange={f("q")} placeholder="Buscar por nombre, cola, modelo, serial, IP o persona…" aria-label="Buscar impresoras" />
        </div>
        <select className="ll-select" style={{ width: "auto" }} value={filtros.sede} onChange={f("sede")} aria-label="Sede">
          <option value="">Todas las sedes</option>
          {SEDES.map((s) => <option key={s}>{s}</option>)}
        </select>
        <select className="ll-select" style={{ width: "auto" }} value={filtros.conexion} onChange={f("conexion")} aria-label="Conexión">
          <option value="">Red y USB</option>
          <option value="red">De red (compartidas)</option>
          <option value="usb">USB (personales)</option>
        </select>
        <select className="ll-select" style={{ width: "auto" }} value={filtros.tenencia} onChange={f("tenencia")} aria-label="Tenencia">
          <option value="">Toda tenencia</option>
          {TENENCIAS.filter(([v]) => v).map(([v, l]) => <option key={v} value={v}>{l}</option>)}
          <option value="-">Sin dato</option>
        </select>
        <span className="ll-contador">{filtradas.length} impresoras</span>
      </div>

      {error && <div className="ll-vacio" style={{ color: "var(--ll-warn)" }}>No se pudieron cargar las impresoras: {error}</div>}
      <div className="ll-card" style={{ overflow: "hidden" }}>
        <div className="ll-tabla-wrap">
          <table className="ll-tabla" style={{ minWidth: 1100 }}>
            <thead><tr>
              <th>NOMBRE</th><th>MODELO</th><th>SEDE / PISO</th><th>IP</th><th>CONEXIÓN</th><th>ASIGNADA A</th>
              <th>TENENCIA</th><th>TÓNER</th><th>CONTADOR</th><th>ESTADO</th>
            </tr></thead>
            <tbody>
              {filtradas.map((i) => {
                const d = i.detalle || {};
                const p = pctMinimo(i);
                return (
                  <tr key={i.id} className="click" onClick={() => setAbierta(i.id)}>
                    <td className="nombre">{i.nombre}</td>
                    <td className="mono">{modeloDe(i)}</td>
                    <td>{i.ubicacion}{d.piso ? " · piso " + d.piso : ""}</td>
                    <td className="mono">{i.ip ? <a href={"http://" + i.ip} target="_blank" rel="noopener noreferrer" onClick={(e) => e.stopPropagation()}>{i.ip}</a> : <span className="tenue">—</span>}</td>
                    <td><span className={"ll-chip" + (d.conexion === "usb" ? "" : " acento")}>{textoConexion(d)}</span></td>
                    <td>{i.usuario || <span className="tenue">{d.uso === "personal" ? "—" : "Compartida"}</span>}</td>
                    <td className="tenue">{textoTenencia(d) || "—"}</td>
                    <td><BarraToner porcentaje={p} /></td>
                    <td className="mono tenue">{i.lectura ? (i.lectura.contador_total ?? "—").toLocaleString("es-AR") + " · " + fmtFechaHora(i.lectura.fecha) : "—"}</td>
                    <td><Estado valor={i.estado} /></td>
                  </tr>
                );
              })}
            </tbody>
          </table>
        </div>
        {!cargando && !filtradas.length && <div className="ll-vacio">{lista.length ? "Sin impresoras que coincidan con los filtros." : "Todavía no hay impresoras cargadas."}</div>}
        {cargando && !lista.length && <div className="ll-vacio">Cargando impresoras…</div>}
      </div>

      {abierta && <FichaImpresora id={abierta} puedeEditar={puedeEditar} avisar={avisar}
        onCerrar={() => setAbierta(null)} onGuardada={cargar} />}
    </div>
  );
}

// ---------------------------------------------------------------- ficha
const CAMPOS_EDITABLES = [
  ["nombre", "Nombre"], ["usuario", "Asignada a (persona)"], ["ubicacion", "Sede"], ["piso", "Piso"], ["ip", "IP"],
  ["nombre_cola", "Nombre de cola"], ["hostname", "Hostname"], ["mac", "MAC"], ["toner_modelo", "Modelo de tóner"],
  ["proveedor", "Proveedor"], ["nro_inventario", "N° de inventario"], ["credencial_ref", "Referencia de la credencial"],
];

function FichaImpresora({ id, puedeEditar, avisar, onCerrar, onGuardada }) {
  const [imp, setImp] = useState(null);
  const [error, setError] = useState("");
  const [edicion, setEdicion] = useState(null);
  const [guardando, setGuardando] = useState(false);

  const cargar = useCallback(async () => {
    try { setImp(await pedir(URL + "/" + id)); setError(""); } catch (e) { setError(e.message); }
  }, [id]);
  useEffect(() => { cargar(); }, [cargar]);

  const editar = () => {
    const d = imp.detalle || {};
    setEdicion({ nombre: imp.nombre || "", usuario: imp.usuario || "", ubicacion: imp.ubicacion || "", ip: imp.ip || "",
      piso: d.piso || "", nombre_cola: d.nombre_cola || "", hostname: d.hostname || "", mac: d.mac || "",
      toner_modelo: d.toner_modelo || "", proveedor: d.proveedor || "", nro_inventario: d.nro_inventario || "",
      credencial_ref: d.credencial_ref || "", conexion: d.conexion || "red", uso: d.uso || "compartida",
      tenencia: d.tenencia || "", color: !!d.color, duplex: !!d.duplex, escaner: !!d.escaner, notas: d.notas || "" });
  };

  async function guardar() {
    setGuardando(true);
    try {
      setImp(await pedir(URL + "/" + id, "PUT", edicion));
      setEdicion(null);
      setError("");
      avisar && avisar("Impresora actualizada");
      onGuardada && onGuardada();
    } catch (e) { setError(e.message); } finally { setGuardando(false); }
  }

  const d = imp?.detalle || {};
  const set = (k) => (e) => setEdicion({ ...edicion, [k]: e.target.type === "checkbox" ? e.target.checked : e.target.value });
  const si = (b) => (b ? "Sí" : "No");

  return (
    <Drawer abierto onCerrar={onCerrar} ancho>
      <div className="ll-drawer-cab">
        <div style={{ minWidth: 0 }}>
          <div className="mono" style={{ fontSize: 21, fontWeight: 600, color: "var(--accent)", letterSpacing: -0.3, wordBreak: "break-all" }}>{imp ? imp.nombre : "Impresora"}</div>
          {imp && <div style={{ fontSize: 12.5, color: "var(--ll-dim)", marginTop: 4 }}>Impresora · {modeloDe(imp)}</div>}
        </div>
        <button className="ll-cerrar" onClick={onCerrar} aria-label="Cerrar">✕</button>
      </div>
      {error && <div className="ll-vacio" style={{ color: "var(--ll-warn)", padding: 12 }}>{error}</div>}
      {!imp ? <div className="ll-vacio">Cargando…</div> : edicion ? (
        <div style={{ display: "flex", flexDirection: "column", gap: 14 }}>
          <Rotulo>EDITAR DATOS DE LA IMPRESORA</Rotulo>
          <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: 12 }}>
            {CAMPOS_EDITABLES.map(([k, l]) => (
              <label key={k} className="ll-campo"><span>{l.toUpperCase()}</span>
                {k === "ubicacion"
                  ? <select className="ll-select" value={edicion[k]} onChange={set(k)}><option value="">—</option>{SEDES.map((s) => <option key={s}>{s}</option>)}</select>
                  : <input className="ll-input" value={edicion[k]} onChange={set(k)} autoComplete="off" />}
              </label>
            ))}
            <label className="ll-campo"><span>CONEXIÓN</span>
              <select className="ll-select" value={edicion.conexion} onChange={set("conexion")}><option value="red">Red</option><option value="usb">USB</option></select></label>
            <label className="ll-campo"><span>USO</span>
              <select className="ll-select" value={edicion.uso} onChange={set("uso")}><option value="compartida">Compartida</option><option value="personal">Personal</option></select></label>
            <label className="ll-campo"><span>TENENCIA</span>
              <select className="ll-select" value={edicion.tenencia} onChange={set("tenencia")}>{TENENCIAS.map(([v, l]) => <option key={v} value={v}>{l}</option>)}</select></label>
            <div className="ll-campo"><span>CAPACIDADES</span>
              <div style={{ display: "flex", gap: 16, paddingTop: 8 }}>
                {[["color", "Color"], ["duplex", "Doble faz"], ["escaner", "Escáner"]].map(([k, l]) => (
                  <label key={k} style={{ display: "flex", gap: 6, alignItems: "center", fontSize: 13 }}><input type="checkbox" checked={edicion[k]} onChange={set(k)} />{l}</label>
                ))}
              </div>
            </div>
          </div>
          <label className="ll-campo"><span>NOTAS</span><textarea className="ll-input" rows={3} value={edicion.notas} onChange={set("notas")} /></label>
          <div style={{ fontSize: 12, color: "var(--ll-dim)" }}>
            Las contraseñas de administración no se guardan en Atlas: quedan en KeePassXC. En “Referencia de la credencial” poné solo dónde está (por ejemplo, “KeePassXC - clave común de impresoras”).
          </div>
          <div style={{ display: "flex", gap: 10, justifyContent: "flex-end" }}>
            <button className="ll-btn-borde" onClick={() => setEdicion(null)}>Cancelar</button>
            <button className="ll-btn-primario" disabled={guardando} onClick={guardar}>{guardando ? "Guardando…" : "Guardar"}</button>
          </div>
        </div>
      ) : (<>
        <div style={{ display: "flex", alignItems: "center", gap: 10, flexWrap: "wrap" }}>
          <Estado valor={imp.estado} />
          <span className={"ll-chip" + (d.conexion === "usb" ? "" : " acento")}>{textoConexion(d)}</span>
          <span className="ll-chip">{d.uso === "personal" ? "Personal" : "Compartida"}</span>
          <span style={{ flex: 1 }} />
          {puedeEditar && <button className="ll-btn-borde" onClick={editar}>Editar</button>}
        </div>

        <div>
          <Rotulo>FICHA</Rotulo>
          <Ficha filas={[
            ["Fabricante", imp.marca], ["Modelo", imp.modelo], ["N° serie", imp.serial], ["Sede", imp.ubicacion], ["Piso", d.piso],
            ["Asignada a", imp.usuario], ["IP", imp.ip], ["Nombre de cola", d.nombre_cola], ["Hostname", d.hostname], ["MAC", d.mac],
            ["Tenencia", textoTenencia(d)], ["N° de inventario", d.nro_inventario], ["Modelo de tóner", d.toner_modelo],
            ["Color", si(d.color)], ["Doble faz", si(d.duplex)], ["Escáner", si(d.escaner)],
            ["Credencial de administración", d.credencial_ref], ["Notas", d.notas],
          ]} />
        </div>

        <div>
          <Rotulo>CONSUMIBLES</Rotulo>
          {(imp.consumibles || []).length ? <div className="ll-ficha">
            {imp.consumibles.map((c) => (
              <div key={c.indice}><span className="k" style={{ flex: "1 1 auto" }}>{c.descripcion || "Consumible " + c.indice}</span>
                <span className="v" style={{ flex: "0 0 auto" }}><BarraToner porcentaje={c.porcentaje} /></span></div>
            ))}
          </div> : <div className="tenue" style={{ fontSize: 13, color: "var(--ll-dim)" }}>Sin lecturas todavía: el relevamiento automático (SNMP) va a completar el tóner y el contador.</div>}
        </div>

        <div>
          <Rotulo>CONTADOR</Rotulo>
          <Ficha filas={[["Páginas totales", imp.lectura ? (imp.lectura.contador_total ?? "—").toLocaleString("es-AR") : "Sin lecturas"],
            ["Última lectura", imp.lectura ? fmtFechaHora(imp.lectura.fecha) : ""]]} />
        </div>

        <div>
          <Rotulo>PCS CON ESTA IMPRESORA INSTALADA ({(imp.pcs || []).length})</Rotulo>
          {(imp.pcs || []).length ? <div className="ll-ficha" style={{ maxHeight: 320, overflowY: "auto" }}>
            {imp.pcs.map((p) => <div key={p.id}><span className="k">{p.nombre}</span><span className="v" style={{ textAlign: "left" }}>{[p.usuario, p.ubicacion].filter(Boolean).join(" · ")}</span></div>)}
          </div> : <div style={{ fontSize: 13, color: "var(--ll-dim)" }}>{d.conexion === "usb" ? "Impresora USB: no se instala como cola compartida." : "Ningún equipo informa esta cola todavía."}</div>}
        </div>
      </>)}
    </Drawer>
  );
}
