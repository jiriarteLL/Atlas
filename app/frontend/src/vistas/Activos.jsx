// Activos.jsx — Inventario completo: busqueda, filtros, orden, paginado y acciones por fila.
import { useMemo, useState } from "react";
import { SEDES, TIPOS, fmtFechaHora } from "../ui";
import { ESTADOS, Estado } from "../diseno/comunes";
import { ESPECIALES } from "./filtros";

const POR_PAGINA = 50;
const COLUMNAS = [
  ["nombre", "NOMBRE", (a) => a.nombre], ["modelo", "MODELO", (a) => ((a.marca || "") + " " + (a.modelo || "")).trim()],
  ["serial", "N° SERIE", (a) => a.serial], ["ip", "IP", (a) => a.ip], ["usuario", "USUARIO", (a) => a.usuario],
  ["centro_costo", "CENTRO DE COSTO", (a) => a.centro_costo],
  ["ubicacion", "SEDE", (a) => a.ubicacion], ["tipo", "TIPO", (a) => a.tipo], ["so", "S.O.", (a) => a.so],
  ["updated", "ÚLT. SYNC", (a) => a.updated], ["estado", "ESTADO", (a) => a.estado],
];

export function ordenar(lista, orden) {
  const col = COLUMNAS.find((c) => c[0] === orden.col);
  if (!col) return lista;
  return [...lista].sort((a, b) => {
    const r = String(col[2](a) ?? "").localeCompare(String(col[2](b) ?? ""), "es", { numeric: true, sensitivity: "base" });
    return orden.asc ? r : -r;
  });
}

export default function Activos({ filtrados, filtros, setFiltros, orden, setOrden, verFicha, editar, eliminar, nuevo,
  exportar, puedeEditar, puedeEliminar, esAdmin, etiquetas, todos = filtrados }) {
  // La pagina vuelve a 1 cuando cambian los filtros (queda asociada a la combinacion de filtros).
  const clave = JSON.stringify(filtros);
  const [pag, setPag] = useState({ clave, n: 1 });
  const pagina = pag.clave === clave ? pag.n : 1;
  const setPagina = (n) => setPag({ clave, n });
  const lista = ordenar(filtrados, orden);
  // centros de costo cargados en los activos (para el filtro)
  const centros = useMemo(() => [...new Set(todos.map((a) => a.centro_costo).filter(Boolean))].sort(), [todos]);
  const paginas = Math.max(1, Math.ceil(lista.length / POR_PAGINA));
  const f = (k) => (e) => setFiltros({ ...filtros, [k]: e.target.value });
  const irPagina = (p) => { setPagina(p); document.querySelector(".ll-contenido")?.scrollTo({ top: 0, behavior: "smooth" }); };

  return (
    <div>
      <div className="ll-barra">
        <div className="ll-buscador">
          <span>⌕</span>
          <input className="ll-input" value={filtros.q} onChange={f("q")} placeholder="Buscar por nombre, usuario, modelo, serial o sede…" aria-label="Buscar activos" />
        </div>
        <select className="ll-select" style={{ width: "auto" }} value={filtros.tipo} onChange={f("tipo")} aria-label="Tipo">
          <option value="">Todos los tipos</option>
          {TIPOS.map((t) => <option key={t}>{t}</option>)}
        </select>
        <select className="ll-select" style={{ width: "auto" }} value={filtros.estado} onChange={f("estado")} aria-label="Estado">
          <option value="">Todos los estados</option>
          {ESTADOS.map((s) => <option key={s}>{s}</option>)}
          {ESPECIALES.filter(([, , soloAdmin]) => !soloAdmin || esAdmin).map(([v, l]) => <option key={v} value={v}>{l}</option>)}
        </select>
        <select className="ll-select" style={{ width: "auto" }} value={filtros.sede} onChange={f("sede")} aria-label="Sede">
          <option value="">Todas las sedes</option>
          {SEDES.map((s) => <option key={s}>{s}</option>)}
        </select>
        <select className="ll-select" style={{ width: "auto" }} value={filtros.centro || ""} onChange={f("centro")} aria-label="Centro de costo">
          <option value="">Todo centro de costo</option>
          {centros.map((c) => <option key={c}>{c}</option>)}
          <option value="-">Sin centro de costo</option>
        </select>
        <span className="ll-contador">{lista.length} activos</span>
        <div style={{ flex: 1 }} />
        {etiquetas && <button className="ll-btn-borde" onClick={() => etiquetas(lista)} title="Etiquetas con QR de los activos filtrados">Etiquetas QR</button>}
        <button className="ll-btn-borde" onClick={() => exportar(lista)}>Exportar Excel</button>
        {puedeEditar && <button className="ll-btn-primario" onClick={nuevo}>＋ Nuevo activo</button>}
      </div>

      <div className="ll-card" style={{ overflow: "hidden" }}>
        <div className="ll-tabla-wrap">
          <table className="ll-tabla" style={{ minWidth: 980 }}>
            <thead><tr>
              {COLUMNAS.map(([k, h]) => (
                <th key={k} className="orden" onClick={() => setOrden((o) => ({ col: k, asc: o.col === k ? !o.asc : true }))}
                  aria-sort={orden.col === k ? (orden.asc ? "ascending" : "descending") : undefined}>
                  {h}{orden.col === k ? (orden.asc ? " ↑" : " ↓") : ""}
                </th>
              ))}
              {(puedeEditar || puedeEliminar) && <th style={{ textAlign: "right" }}>ACCIONES</th>}
            </tr></thead>
            <tbody>
              {lista.slice((pagina - 1) * POR_PAGINA, pagina * POR_PAGINA).map((a) => (
                <tr key={a.id} className="click" onClick={() => verFicha(a)}>
                  <td className="nombre">{a.nombre}</td>
                  <td className="mono">{((a.marca || "") + " " + (a.modelo || "")).trim()}</td>
                  <td className="mono">{a.serial}</td>
                  <td className="mono">{a.ip ? <a href={"http://" + a.ip} target="_blank" rel="noopener noreferrer" onClick={(e) => e.stopPropagation()}>{a.ip}</a> : ""}</td>
                  <td>{a.usuario}{a.usuario_secundario && <span className="ll-chip" style={{ marginLeft: 6, padding: "1px 7px", fontSize: 11 }}
                    title={"Segundo usuario: " + [a.usuario_secundario_nombre, a.usuario_secundario].filter(Boolean).join(" · ")}>+1</span>}</td>
                  <td className="tenue">{a.centro_costo || ""}</td>
                  <td>{a.ubicacion}</td>
                  <td className="tenue">{a.tipo}</td>
                  <td className="tenue">{a.so}</td>
                  <td className="tenue mono">{fmtFechaHora(a.updated)}</td>
                  <td><Estado valor={a.estado} /></td>
                  {(puedeEditar || puedeEliminar) && <td style={{ textAlign: "right", whiteSpace: "nowrap" }} onClick={(e) => e.stopPropagation()}>
                    {puedeEditar && <button className="ll-btn-borde ll-btn-chico" onClick={() => editar(a)}>Editar</button>}
                    {puedeEliminar && <button className="ll-btn-peligro" style={{ marginLeft: 6 }} onClick={() => eliminar(a)} title="Eliminar" aria-label={"Eliminar " + (a.nombre || a.serial)}>✕</button>}
                  </td>}
                </tr>
              ))}
            </tbody>
          </table>
        </div>
        {!lista.length && <div className="ll-vacio">{filtros.q ? `Sin resultados para “${filtros.q}”.` : "Sin activos que coincidan con los filtros."}</div>}
        {lista.length > POR_PAGINA && (
          <div className="ll-paginado">
            <button className="ll-btn-borde" disabled={pagina <= 1} onClick={() => irPagina(pagina - 1)}>Anterior</button>
            <span>Página {pagina} de {paginas}</span>
            <button className="ll-btn-borde" disabled={pagina >= paginas} onClick={() => irPagina(pagina + 1)}>Siguiente</button>
          </div>
        )}
      </div>
    </div>
  );
}
