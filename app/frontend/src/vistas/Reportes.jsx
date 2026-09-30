// Reportes.jsx — Indicadores y graficos exportables a Excel.
import { useGraficos } from "../graficos";
import { SEDES, TIPOS } from "../ui";
import { ESTADOS, TIPO_COLOR, estadoColor } from "../diseno/comunes";
import { diasSinReportar } from "./filtros";

const TOOLTIP = {
  contentStyle: { borderRadius: 10, border: "1px solid rgba(255,255,255,0.1)", background: "#0b1020", color: "#e6edf6", fontSize: 12 },
  itemStyle: { color: "#e6edf6" }, labelStyle: { color: "#8a97ab" },
};
const EJE = { tick: { fontSize: 11, fill: "#7c8798" }, axisLine: { stroke: "rgba(255,255,255,0.08)" }, tickLine: false };

function Panel({ rotulo, valor, sub, color }) {
  return (
    <div className="ll-card" style={{ padding: 24 }}>
      <div className="ll-rotulo">{rotulo}</div>
      <div className="mono" style={{ fontSize: 34, fontWeight: 600, marginTop: 10, color }}>{valor}</div>
      <div style={{ fontSize: 12.5, color: "var(--ll-dim)", marginTop: 6 }}>{sub}</div>
    </div>
  );
}

function Grafico({ id, titulo, datos, exportar, children }) {
  return (
    <div className="ll-card" style={{ padding: "22px 24px" }}>
      <div style={{ display: "flex", alignItems: "center", marginBottom: 12 }}>
        <div className="ll-card-titulo" style={{ flex: 1 }}>{titulo}</div>
        <button className="ll-btn-borde ll-btn-chico" onClick={() => exportar(titulo, datos, id)}>Excel</button>
      </div>
      <div id={id}>{children}</div>
    </div>
  );
}

export default function Reportes({ assets, ir, exportar }) {
  const G = useGraficos();
  const total = assets.length;
  const operativos = assets.filter((a) => a.estado === "Activo").length;
  const enMant = assets.filter((a) => a.estado === "Mantenimiento").length;
  const dSede = SEDES.map((s) => ({ name: s, value: assets.filter((a) => (a.ubicacion || "").toLowerCase() === s.toLowerCase()).length }));
  const dTipo = TIPOS.map((t) => ({ name: t, value: assets.filter((a) => a.tipo === t).length })).filter((d) => d.value > 0);
  const dSinReportar = [["16-30 días", 16, 30], ["31-60 días", 31, 60], ["+60 días", 61, Infinity]]
    .map(([name, min, max]) => ({ name, value: assets.filter((a) => { const d = diasSinReportar(a); return d >= min && d <= max; }).length }));
  const dEstado = ESTADOS.map((s) => ({ name: s, value: assets.filter((a) => a.estado === s).length })).filter((d) => d.value > 0);

  return (
    <div>
      <div className="ll-grid-2">
        <Panel rotulo="TASA DE ACTIVOS OPERATIVOS" valor={total ? Math.round(operativos / total * 100) + "%" : "—"} sub={`${operativos} de ${total} equipos operativos`} color="#34d399" />
        <Panel rotulo="EQUIPOS EN MANTENIMIENTO" valor={enMant} sub="Requieren seguimiento del área TI" color="#fbbf24" />
        <Panel rotulo="SEDES CON INVENTARIO" valor={dSede.filter((d) => d.value > 0).length} sub={`de ${SEDES.length} sedes`} color="var(--accent)" />
        <Panel rotulo="LICENCIAS POR VENCER" valor="—" sub="Módulo no incluido en esta versión" color="#f472b6" />
      </div>

      <div className="ll-grid-2" style={{ marginTop: 18 }}>
        <Grafico id="rep-sede" titulo="Activos por sede" datos={dSede} exportar={exportar}>
          <G.ResponsiveContainer width="100%" height={260}>
            <G.BarChart data={dSede} margin={{ top: 8, right: 8, left: -18, bottom: 0 }}
              onClick={(st) => { if (st && st.activeLabel) ir("activos", { sede: st.activeLabel }); }}>
              <G.CartesianGrid vertical={false} stroke="rgba(255,255,255,0.05)" />
              <G.XAxis dataKey="name" {...EJE} interval={0} tick={{ fontSize: 10, fill: "#7c8798" }} />
              <G.YAxis {...EJE} axisLine={false} allowDecimals={false} />
              <G.Tooltip cursor={{ fill: "rgba(255,255,255,0.03)" }} {...TOOLTIP} />
              <G.Bar dataKey="value" name="Activos" radius={[5, 5, 0, 0]} fill="var(--accent)" cursor="pointer" />
            </G.BarChart>
          </G.ResponsiveContainer>
        </Grafico>
        <Grafico id="rep-tipo" titulo="Distribución por tipo" datos={dTipo} exportar={exportar}>
          <G.ResponsiveContainer width="100%" height={260}>
            <G.PieChart>
              <G.Pie data={dTipo} dataKey="value" nameKey="name" innerRadius={58} outerRadius={96} paddingAngle={2} cursor="pointer"
                onClick={(d) => { if (d && d.name) ir("activos", { tipo: d.name }); }}>
                {dTipo.map((d) => <G.Cell key={d.name} fill={TIPO_COLOR[d.name] || "#7c8798"} stroke="#05070d" strokeWidth={2} />)}
              </G.Pie>
              <G.Tooltip {...TOOLTIP} />
              <G.Legend wrapperStyle={{ fontSize: 11, color: "#c4cdda" }} />
            </G.PieChart>
          </G.ResponsiveContainer>
        </Grafico>
        <Grafico id="rep-estado" titulo="Activos por estado" datos={dEstado} exportar={exportar}>
          <G.ResponsiveContainer width="100%" height={260}>
            <G.PieChart>
              <G.Pie data={dEstado} dataKey="value" nameKey="name" outerRadius={96} paddingAngle={2} cursor="pointer"
                onClick={(d) => { if (d && d.name) ir("activos", { estado: d.name }); }}>
                {dEstado.map((d) => <G.Cell key={d.name} fill={estadoColor(d.name)} stroke="#05070d" strokeWidth={2} />)}
              </G.Pie>
              <G.Tooltip {...TOOLTIP} />
              <G.Legend wrapperStyle={{ fontSize: 11, color: "#c4cdda" }} />
            </G.PieChart>
          </G.ResponsiveContainer>
        </Grafico>
        <Grafico id="rep-sin-reportar" titulo="Equipos sin reportar" datos={dSinReportar} exportar={exportar}>
          <G.ResponsiveContainer width="100%" height={260}>
            <G.BarChart data={dSinReportar} margin={{ top: 8, right: 8, left: -18, bottom: 0 }}
              onClick={() => ir("activos", { estado: "__sin_reportar__" })}>
              <G.CartesianGrid vertical={false} stroke="rgba(255,255,255,0.05)" />
              <G.XAxis dataKey="name" {...EJE} />
              <G.YAxis {...EJE} axisLine={false} allowDecimals={false} />
              <G.Tooltip cursor={{ fill: "rgba(255,255,255,0.03)" }} {...TOOLTIP} />
              <G.Bar dataKey="value" name="Equipos" radius={[5, 5, 0, 0]} fill="#f472b6" cursor="pointer" />
            </G.BarChart>
          </G.ResponsiveContainer>
        </Grafico>
      </div>
    </div>
  );
}
