// ParaRenovar.jsx — Tarjeta del Dashboard (fase F): equipos con la vida util cumplida o por cumplirse y su estado de
// ciclo de vida. Datos: /api/ciclo/resumen y /api/ciclo/renovar.
import { useEffect, useState } from "react";
import { apiFetch } from "../api";
import { estadoColor } from "../diseno/comunes";

const fmtF = (s) => { const m = /^(\d{4})-(\d{2})-(\d{2})/.exec(s || ""); return m ? `${m[3]}/${m[2]}/${m[1]}` : ""; };

export default function ParaRenovar({ verFicha, assets }) {
  const [r, setR] = useState(null);
  const [lista, setLista] = useState([]);
  const [ver, setVer] = useState(false);
  useEffect(() => {
    let vivo = true;
    apiFetch("/api/ciclo/resumen").then((x) => (x.ok ? x.json() : null)).then((d) => { if (vivo) setR(d); }).catch(() => {});
    apiFetch("/api/ciclo/renovar").then((x) => (x.ok ? x.json() : [])).then((d) => { if (vivo) setLista(d || []); }).catch(() => {});
    return () => { vivo = false; };
  }, []);
  if (!r) return null;
  const estados = ["Asignado", "En stock", "Prestado", "En reparación", "Para baja"];
  const abrir = (id) => { const a = assets.find((x) => x.id === id); if (a) verFicha(a); };
  const vencidos = lista.filter((x) => x.para_renovar).sort((a, b) => a.dias_renovacion - b.dias_renovacion);
  const pronto = lista.filter((x) => x.renovar_pronto).sort((a, b) => a.dias_renovacion - b.dias_renovacion);

  return (
    <div className="ll-card" style={{ marginTop: 22, padding: "20px 24px" }}>
      <div style={{ display: "flex", alignItems: "center", justifyContent: "space-between", marginBottom: 16, gap: 12, flexWrap: "wrap" }}>
        <div className="ll-card-titulo">Ciclo de vida <span className="tenue" style={{ fontSize: 12.5, fontWeight: 400 }}>· {r.total} activos</span></div>
        {lista.length > 0 && <button className="ll-btn-borde" onClick={() => setVer((v) => !v)}>{ver ? "Ocultar equipos" : "Ver equipos para renovar"}</button>}
      </div>
      <div style={{ display: "grid", gridTemplateColumns: "repeat(auto-fill, minmax(140px, 1fr))", gap: 12 }}>
        <div style={{ border: "1px solid var(--ll-line)", borderRadius: 12, padding: "12px 14px" }}>
          <div className="mono" style={{ fontSize: 22, fontWeight: 600, color: r.para_renovar ? "var(--ll-rosa)" : "var(--ll-dim)" }}>{r.para_renovar}</div>
          <div style={{ fontSize: 12.5, color: "var(--ll-text-2)", marginTop: 3 }}>Para renovar</div>
        </div>
        <div style={{ border: "1px solid var(--ll-line)", borderRadius: 12, padding: "12px 14px" }}>
          <div className="mono" style={{ fontSize: 22, fontWeight: 600, color: r.renovar_pronto ? "var(--ll-ambar)" : "var(--ll-dim)" }}>{r.renovar_pronto}</div>
          <div style={{ fontSize: 12.5, color: "var(--ll-text-2)", marginTop: 3 }}>Renovar en 90 días</div>
        </div>
        {estados.map((e) => (
          <div key={e} style={{ border: "1px solid var(--ll-line)", borderRadius: 12, padding: "12px 14px" }}>
            <div className="mono" style={{ fontSize: 22, fontWeight: 600, color: r.por_estado[e] ? estadoColor(e) : "var(--ll-dim)" }}>{r.por_estado[e] || 0}</div>
            <div style={{ fontSize: 12.5, color: "var(--ll-text-2)", marginTop: 3 }}>{e}</div>
          </div>
        ))}
      </div>
      {r.sin_dato > 0 && <div className="tenue" style={{ fontSize: 12, marginTop: 10 }}>{r.sin_dato} activos sin fecha de compra ni de fabricación: no se puede calcular cuándo renovarlos.</div>}
      {ver && <div className="ll-tabla-wrap" style={{ marginTop: 14 }}>
        <table className="ll-tabla"><thead><tr><th>EQUIPO</th><th>TIPO</th><th>USUARIO</th><th>SEDE</th><th>DESDE</th><th>RENOVAR</th></tr></thead>
          <tbody>{[...vencidos, ...pronto].slice(0, 100).map((x) => (
            <tr key={x.id} className="click" onClick={() => abrir(x.id)}>
              <td className="nombre">{x.nombre || x.serial}</td><td className="tenue">{x.tipo}</td><td>{x.usuario || <span className="tenue">—</span>}</td>
              <td>{x.sede}</td><td className="tenue">{fmtF(x.base)} <span style={{ fontSize: 11 }}>({x.base_origen})</span></td>
              <td className="mono" style={{ color: x.para_renovar ? "var(--ll-rosa)" : "var(--ll-ambar)" }}>{fmtF(x.renovacion)}</td>
            </tr>))}</tbody></table>
      </div>}
    </div>
  );
}
