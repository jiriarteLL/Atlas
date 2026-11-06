// Agente.jsx — Instrucciones de instalacion del agente de sincronizacion (Windows y Linux).
// La URL sale del propio navegador (mismo origen); la clave de sync nunca se muestra aca.
import { Ficha, Rotulo } from "../diseno/comunes";

function Bloque({ titulo, comando, codigo }) {
  return (
    <div className="ll-card" style={{ padding: 24 }}>
      <div className="ll-card-titulo" style={{ marginBottom: 14 }}>{titulo}</div>
      <code className="mono" style={{ fontSize: 11.5, display: "block", marginBottom: 10, color: "var(--accent)", wordBreak: "break-all" }}>{comando}</code>
      <pre className="mono" style={{ margin: 0, background: "var(--ll-codigo-bg)", border: "1px solid var(--ll-line)", color: "var(--ll-text-2)", padding: 14, borderRadius: 12, fontSize: 11.5, overflow: "auto" }}>{codigo}</pre>
    </div>
  );
}

export default function Agente() {
  const origen = window.location.origin;
  return (
    <div>
      <div className="ll-grid-2">
        <Bloque titulo="◈ Agente Windows v4.3"
          comando="powershell -ExecutionPolicy Bypass -File agent.ps1 -Server <url> -SyncKey <clave>"
          codigo={`# Servidor de este ambiente\n-Server "${origen}"\n# La clave (SYNC_API_KEY) la entrega el administrador;\n# no se escribe dentro del script.`} />
        <Bloque titulo="◈ Agente Linux"
          comando={`curl -s ${origen}/agent_linux.sh -o agent.sh`}
          codigo={`INVENTARIO_URL="${origen}" \\\nINVENTARIO_SYNC_KEY="<clave>" bash agent.sh`} />
      </div>
      <div style={{ marginTop: 22 }}>
        <Rotulo>DISTRIBUCIÓN</Rotulo>
        <Ficha filas={[
          ["Distribución", "GPO: script de arranque (SYSVOL), con -Server y -SyncKey"],
          ["Endpoint", "POST " + origen + "/api/sync (header X-Sync-Key)"],
          ["Frecuencia", "Cada 2 horas (8 a 22) y al iniciar sesión, de fondo"],
          ["Identificador", "Serial del equipo (sin serial: comparten registro)"],
        ]} />
      </div>
    </div>
  );
}
