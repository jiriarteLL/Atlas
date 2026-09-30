// Ambientacion.jsx — Panel de preferencias visuales (acento, fondo animado, brillo, sonido).
import { Drawer, Rotulo } from "./comunes";
import { ACENTOS, useAmbiente } from "./ambiente";

function Interruptor({ on, onClick, etiqueta }) {
  return <button className={"ll-switch" + (on ? " on" : "")} onClick={onClick} role="switch" aria-checked={on} aria-label={etiqueta}><span /></button>;
}

export default function Ambientacion({ abierto, onCerrar }) {
  const amb = useAmbiente();
  return (
    <Drawer abierto={abierto} onCerrar={onCerrar}>
      <div className="ll-drawer-cab">
        <div>
          <div style={{ fontSize: 19, fontWeight: 600 }}>Ambientación</div>
          <div style={{ fontSize: 12, color: "var(--ll-dim)", marginTop: 3 }}>Personalizá la interfaz a tu gusto</div>
        </div>
        <button className="ll-cerrar" onClick={onCerrar} aria-label="Cerrar">✕</button>
      </div>

      <div>
        <Rotulo>COLOR DE ACENTO</Rotulo>
        <div className="ll-acentos">
          {Object.entries(ACENTOS).map(([nombre, [c1, c2]]) => (
            <button key={nombre} title={nombre} aria-label={nombre} aria-pressed={amb.acento === nombre}
              className={amb.acento === nombre ? "activo" : ""} onClick={() => amb.cambiar("acento", nombre)}
              style={{ background: `linear-gradient(135deg, ${c1}, ${c2})`, boxShadow: amb.acento === nombre ? "0 0 22px -4px " + c1 : "none" }} />
          ))}
        </div>
        <div style={{ fontSize: 12.5, color: "var(--ll-text-2)", marginTop: 11 }}>Seleccionado: <span style={{ color: "var(--accent)", fontWeight: 600 }}>{amb.acento}</span></div>
      </div>

      <div style={{ display: "flex", alignItems: "center", justifyContent: "space-between", gap: 12 }}>
        <div>
          <div style={{ fontSize: 14.5, fontWeight: 500 }}>Fondo animado</div>
          <div style={{ fontSize: 12, color: "var(--ll-dim)" }}>Esfera, grilla y destellos en movimiento</div>
        </div>
        <Interruptor on={amb.fx} onClick={() => amb.cambiar("fx", !amb.fx)} etiqueta="Fondo animado" />
      </div>

      <div>
        <div style={{ display: "flex", alignItems: "center", justifyContent: "space-between", marginBottom: 12 }}>
          <div style={{ fontSize: 14.5, fontWeight: 500 }}>Intensidad de brillo</div>
          <div className="mono" style={{ fontSize: 12.5, color: "var(--accent)" }}>{amb.brillo}%</div>
        </div>
        <input type="range" min="0" max="100" step="5" value={amb.brillo} aria-label="Intensidad de brillo"
          onChange={(e) => amb.cambiar("brillo", +e.target.value)} style={{ width: "100%", accentColor: "var(--accent)", cursor: "pointer" }} />
      </div>

      <div style={{ display: "flex", alignItems: "center", justifyContent: "space-between", gap: 12 }}>
        <div>
          <div style={{ fontSize: 14.5, fontWeight: 500 }}>Ambiente sonoro</div>
          <div style={{ fontSize: 12, color: "var(--ll-dim)" }}>Música ambiental suave de fondo</div>
        </div>
        <Interruptor on={amb.sonando} onClick={() => amb.sonar(!amb.sonando)} etiqueta="Ambiente sonoro" />
      </div>

      <div className="mono" style={{ marginTop: "auto", fontSize: 11, color: "var(--ll-ghost)" }}>Los cambios se aplican al instante.</div>
    </Drawer>
  );
}
