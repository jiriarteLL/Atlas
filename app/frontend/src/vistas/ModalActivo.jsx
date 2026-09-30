// ModalActivo.jsx — Alta y edicion de un activo.
import { useState } from "react";
import { SEDES, TIPOS, emptyAsset } from "../ui";
import { ESTADOS, Modal } from "../diseno/comunes";

const CAMPOS = [
  ["nombre", "NOMBRE DEL EQUIPO"], ["tipo", "TIPO *", TIPOS], ["marca", "FABRICANTE *"], ["modelo", "MODELO *"],
  ["serial", "N° SERIE *"], ["estado", "ESTADO", ESTADOS], ["usuario", "USUARIO"], ["usuario_alt", "USUARIO ALT."],
  ["ubicacion", "SEDE", ["", ...SEDES]], ["garantia", "GARANTÍA (AAAA-MM-DD)"], ["ip", "IP"], ["red", "DOMINIO"],
  ["cpu", "CPU"], ["ram", "RAM"], ["disco", "DISCO"], ["so", "SISTEMA OPERATIVO"],
];

export default function ModalActivo({ inicial, onGuardar, onCerrar }) {
  const [a, setA] = useState(() => ({ ...emptyAsset, ...(inicial || {}) }));
  const [error, setError] = useState("");
  const [guardando, setGuardando] = useState(false);
  const editando = !!inicial?.id;

  async function guardar() {
    if (!a.tipo || !a.marca.trim() || !a.modelo.trim() || !a.serial.trim()) { setError("Tipo, fabricante, modelo y serial son obligatorios."); return; }
    if (a.serial.trim().length < 3) { setError("El serial debe tener al menos 3 caracteres."); return; }
    if (a.garantia && !/^\d{4}-\d{2}-\d{2}$/.test(a.garantia)) { setError("La garantía va con formato AAAA-MM-DD."); return; }
    setGuardando(true);
    setError("");
    try { await onGuardar(a); } catch (e) { setError(e.message || "No se pudo guardar."); }
    setGuardando(false);
  }

  return (
    <Modal titulo={editando ? "Editar activo" : "Nuevo activo"} onCerrar={onCerrar} ancho={640}
      pie={<>
        <button className="ll-btn-borde" style={{ padding: "11px 20px", borderRadius: 11 }} onClick={onCerrar}>Cancelar</button>
        <button className="ll-btn-primario" style={{ padding: "11px 24px" }} disabled={guardando} onClick={guardar}>{guardando ? "Guardando…" : "Guardar"}</button>
      </>}>
      <div className="ll-modal-cuerpo">
        {CAMPOS.map(([k, l, opciones]) => (
          <label key={k} className="ll-campo">
            <span>{l}</span>
            {opciones
              ? <select className="ll-select" value={a[k] || ""} onChange={(e) => setA({ ...a, [k]: e.target.value })}>
                  {opciones.map((o) => <option key={o} value={o}>{o || "— Seleccionar —"}</option>)}
                </select>
              : <input className="ll-input" value={a[k] || ""} onChange={(e) => setA({ ...a, [k]: e.target.value })} />}
          </label>
        ))}
        <label className="ll-campo doble">
          <span>COMENTARIOS</span>
          <textarea className="ll-input" rows={3} value={a.comentarios || ""} onChange={(e) => setA({ ...a, comentarios: e.target.value })} />
        </label>
        {error && <div className="ll-error doble" role="alert"><span>⚠</span>{error}</div>}
      </div>
    </Modal>
  );
}
