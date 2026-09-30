// Dashboard.jsx — Vista general: tarjetas, activos por sede, distribucion por tipo y ultimos sincronizados.
import { useState } from "react";
import { SEDES, TIPOS, fmtDate } from "../ui";
import { Estado, TIPO_COLOR } from "../diseno/comunes";
import { diasGarantia } from "./filtros";

function Tarjeta({ valor, rotulo, sub, subColor, barra, demora, onClick, children }) {
  return (
    <div className={"ll-card hover ll-stat" + (onClick ? " click" : "")} style={{ animationDelay: demora }} onClick={onClick}
      role={onClick ? "button" : undefined} tabIndex={onClick ? 0 : undefined}
      onKeyDown={onClick ? (e) => { if (e.key === "Enter") onClick(); } : undefined}>
      <div className="ll-stat-barra" style={{ background: `linear-gradient(90deg, ${barra}, transparent)` }} />
      <div className="ll-stat-num">{valor}</div>
      <div className="ll-rotulo" style={{ marginTop: 12 }}>{rotulo}</div>
      {sub && <div style={{ marginTop: 7, fontSize: 12.5, color: subColor || "var(--ll-dim)" }}>{sub}</div>}
      {children}
    </div>
  );
}

export default function Dashboard({ assets, ir, verFicha }) {
  const [nbFiltro, setNbFiltro] = useState("total");
  const total = assets.length;
  const enUso = assets.filter((a) => a.estado === "Activo").length;
  const enMant = assets.filter((a) => a.estado === "Mantenimiento").length;
  const garVencen = assets.filter((a) => { const d = diasGarantia(a); return d !== null && d >= 0 && d <= 90; }).length;
  const nb = assets.filter((a) => a.tipo === "Notebook" || a.tipo === "CPU");
  const nbValor = nbFiltro === "asignadas" ? nb.filter((a) => (a.usuario || "").trim()).length
    : nbFiltro === "sinasignar" ? nb.filter((a) => !(a.usuario || "").trim()).length : nb.length;
  const cuenta = (t) => assets.filter((a) => a.tipo === t).length;
  const acento = "var(--accent)";

  const sedes = SEDES.map((s) => {
    const en = assets.filter((a) => (a.ubicacion || "").toLowerCase() === s.toLowerCase());
    return { name: s, nb: en.filter((a) => a.tipo === "Notebook").length, im: en.filter((a) => a.tipo === "Impresora").length };
  });
  const maxSede = Math.max(1, ...sedes.map((x) => Math.max(x.nb, x.im)));

  const tipos = TIPOS.map((t) => ({ name: t, value: cuenta(t), color: TIPO_COLOR[t] || "#7c8798" })).filter((t) => t.value > 0);
  let acc = 0;
  const dona = tipos.length ? `conic-gradient(${tipos.map((t) => {
    const desde = acc / total * 100; acc += t.value;
    return `${t.color} ${desde}% ${acc / total * 100}%`;
  }).join(", ")})` : "rgba(255,255,255,0.06)";

  const recientes = [...assets].sort((a, b) => new Date(b.updated || 0) - new Date(a.updated || 0)).slice(0, 8);

  return (
    <div>
      <div className="ll-grid-4">
        <Tarjeta valor={total} rotulo="TOTAL ACTIVOS" sub={enUso + " activos en uso"} subColor="var(--ll-ok)" barra={acento} demora="0s" onClick={() => ir("activos")} />
        <Tarjeta valor={enMant} rotulo="EN MANTENIMIENTO" sub={enMant ? "Requieren atención" : "Sin urgencias"} subColor={enMant ? "var(--ll-warn)" : undefined} barra="#fbbf24" demora=".05s"
          onClick={() => ir("activos", { estado: "Mantenimiento" })} />
        <Tarjeta valor="—" rotulo="LICENCIAS CLAUDE" sub="Módulo no incluido" barra="var(--accent2)" demora=".1s" onClick={() => ir("licencias")} />
        <Tarjeta valor={garVencen} rotulo="GARANTÍAS POR VENCER" sub="Próximos 3 meses" barra="#f472b6" demora=".15s"
          onClick={() => ir("activos", { estado: "__gar_vencen__" })} />
        <Tarjeta valor={nbValor} rotulo="NOTEBOOKS / CPU" barra="#3b82f6" demora=".2s">
          <div style={{ display: "flex", gap: 12, marginTop: 8 }}>
            {[["total", "Total"], ["asignadas", "Asignadas"], ["sinasignar", "Sin asignar"]].map(([k, l]) => (
              <button key={k} onClick={() => setNbFiltro(k)}
                style={{ border: "none", background: "none", padding: "0 0 2px", fontSize: 11.5, cursor: "pointer", fontWeight: 600,
                  color: nbFiltro === k ? "var(--accent)" : "var(--ll-dim)", borderBottom: "1.5px solid " + (nbFiltro === k ? "var(--accent)" : "transparent") }}>{l}</button>
            ))}
          </div>
          <button onClick={() => ir("activos", { tipo: "Notebook" })} style={{ marginTop: 8, border: "none", background: "none", padding: 0, fontSize: 12.5, color: "var(--accent)", cursor: "pointer" }}>Ver inventario →</button>
        </Tarjeta>
        <Tarjeta valor={cuenta("Impresora")} rotulo="IMPRESORAS" sub="Ver inventario →" subColor={acento} barra="#22c55e" demora=".25s" onClick={() => ir("activos", { tipo: "Impresora" })} />
        <Tarjeta valor={cuenta("Servidor")} rotulo="SERVIDORES" sub="Ver inventario →" subColor={acento} barra="#ec4899" demora=".3s" onClick={() => ir("activos", { tipo: "Servidor" })} />
        <Tarjeta valor="—" rotulo="LICENCIAS ASIGNADAS" sub="Ver nómina →" subColor={acento} barra="var(--accent2)" demora=".35s" onClick={() => ir("usuarios")} />
      </div>

      <div className="ll-grid-dash">
        <div className="ll-card" style={{ padding: "24px 26px 20px" }}>
          <div className="ll-card-titulo" style={{ marginBottom: 22 }}>Activos por sede</div>
          <div style={{ display: "flex", alignItems: "flex-end", gap: 10, height: 220, paddingBottom: 26, borderBottom: "1px solid rgba(255,255,255,0.06)" }}>
            {sedes.map((s) => (
              <button key={s.name} onClick={() => ir("activos", { sede: s.name })} title={`${s.name}: ${s.nb} notebooks, ${s.im} impresoras`}
                style={{ flex: 1, display: "flex", flexDirection: "column", alignItems: "center", height: "100%", justifyContent: "flex-end", position: "relative", border: "none", background: "none", padding: 0, cursor: "pointer" }}>
                <div style={{ display: "flex", alignItems: "flex-end", gap: 4, height: "100%", width: "100%", justifyContent: "center" }}>
                  <div style={{ width: "34%", height: (s.nb / maxSede * 100) + "%", minHeight: 2, borderRadius: "5px 5px 0 0", background: "linear-gradient(180deg,#60a5fa,#2563eb)", boxShadow: "0 0 14px -3px #3b82f6", transition: "height .6s cubic-bezier(.2,.8,.2,1)" }} />
                  <div style={{ width: "34%", height: (s.im / maxSede * 100) + "%", minHeight: 2, borderRadius: "5px 5px 0 0", background: "linear-gradient(180deg,#4ade80,#16a34a)", transition: "height .6s cubic-bezier(.2,.8,.2,1)" }} />
                </div>
                <div style={{ position: "absolute", bottom: -24, fontSize: 10.5, color: "var(--ll-dim)", whiteSpace: "nowrap" }}>{s.name}</div>
              </button>
            ))}
          </div>
          <div style={{ display: "flex", gap: 22, marginTop: 16, fontSize: 12, color: "var(--ll-muted)" }}>
            <span style={{ display: "flex", alignItems: "center", gap: 7 }}><span style={{ width: 11, height: 11, borderRadius: 3, background: "#3b82f6" }} /> Notebook</span>
            <span style={{ display: "flex", alignItems: "center", gap: 7 }}><span style={{ width: 11, height: 11, borderRadius: 3, background: "#22c55e" }} /> Impresora</span>
          </div>
        </div>

        <div className="ll-card" style={{ padding: "24px 26px" }}>
          <div className="ll-card-titulo" style={{ marginBottom: 18 }}>Distribución por tipo</div>
          <div style={{ display: "flex", alignItems: "center", justifyContent: "center", height: 200 }}>
            <div style={{ position: "relative", width: 186, height: 186, borderRadius: "50%", background: dona }}>
              <div style={{ position: "absolute", inset: 30, borderRadius: "50%", background: "#080b14", display: "flex", flexDirection: "column", alignItems: "center", justifyContent: "center" }}>
                <div className="mono" style={{ fontSize: 30, fontWeight: 600 }}>{total}</div>
                <div style={{ fontSize: 10.5, letterSpacing: 1.5, color: "var(--ll-dim)" }}>ACTIVOS</div>
              </div>
            </div>
          </div>
          <div style={{ display: "flex", flexDirection: "column", gap: 9, marginTop: 14 }}>
            {tipos.map((t) => (
              <button key={t.name} onClick={() => ir("activos", { tipo: t.name })}
                style={{ display: "flex", alignItems: "center", gap: 10, fontSize: 12.5, border: "none", background: "none", padding: 0, cursor: "pointer", color: "inherit" }}>
                <span style={{ width: 11, height: 11, borderRadius: 3, background: t.color }} />
                <span style={{ flex: 1, color: "var(--ll-text-2)", textAlign: "left" }}>{t.name}</span>
                <span className="mono" style={{ color: "var(--ll-muted)" }}>{t.value}</span>
              </button>
            ))}
          </div>
        </div>
      </div>

      <div className="ll-card" style={{ marginTop: 22, overflow: "hidden" }}>
        <div style={{ display: "flex", alignItems: "center", justifyContent: "space-between", padding: "20px 24px 14px" }}>
          <div className="ll-card-titulo">Últimos sincronizados</div>
          <button className="ll-btn-borde" onClick={() => ir("activos")}>Ver todos</button>
        </div>
        <div className="ll-tabla-wrap">
          <table className="ll-tabla" style={{ minWidth: 720 }}>
            <thead><tr><th>NOMBRE</th><th>MODELO</th><th>USUARIO</th><th>SEDE</th><th>S.O.</th><th>ÚLT. SYNC</th><th>ESTADO</th></tr></thead>
            <tbody>
              {recientes.map((a) => (
                <tr key={a.id} className="click" onClick={() => verFicha(a)}>
                  <td className="nombre">{a.nombre}</td>
                  <td className="mono">{a.modelo}</td>
                  <td>{a.usuario}</td>
                  <td>{a.ubicacion}</td>
                  <td className="tenue">{a.so}</td>
                  <td className="tenue mono">{fmtDate(a.updated)}</td>
                  <td><Estado valor={a.estado} /></td>
                </tr>
              ))}
              {!recientes.length && <tr><td colSpan={7}><div className="ll-vacio">Todavía no hay activos cargados.</div></td></tr>}
            </tbody>
          </table>
        </div>
      </div>
    </div>
  );
}
