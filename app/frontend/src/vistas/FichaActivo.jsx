// FichaActivo.jsx — Panel lateral con la ficha completa del activo: datos tecnicos, seguridad,
// relevamiento GLPI, garantia (Lenovo automatica o carga manual), QR, software, licencias (diseño), adjuntos e historial.
import { useEffect, useState } from "react";
import { apiFetch } from "../api";
import { QR, fmtFechaHora } from "../ui";
import { Drawer, Ficha, Rotulo, estadoColor } from "../diseno/comunes";
import { AdjuntosActivo } from "../secciones/AdjuntosActivo";
import { GarantiaActivo } from "../secciones/GarantiaActivo";
import { HistorialActivo } from "../secciones/HistorialActivo";
import { HistorialPcs, MonitoresConectados } from "../secciones/MonitoresActivo";
import { COLOR_CIFRADO, glpiDe } from "./filtros";
import { BarraBateria, EstadoAntivirus, InsigniaSoporte, fmtFecha, textoWindows } from "./Salud";

export default function FichaActivo({ activo, glpiMap, user, onCerrar, onEditar, onEliminar, onGarantia, puedeEditar, puedeEliminar, abrirActivo }) {
  const [verQR, setVerQR] = useState(false);
  const [verSoft, setVerSoft] = useState(false);
  const [salud, setSalud] = useState(null);
  const id = activo?.id;
  useEffect(() => {
    if (!id) return undefined;
    let vivo = true;
    apiFetch("/api/salud/" + id).then((r) => (r.ok ? r.json() : null)).then((d) => { if (vivo) setSalud(d); }).catch(() => {});
    return () => { vivo = false; };
  }, [id]);
  if (!activo) return null;
  const a = activo;
  const gl = glpiDe(glpiMap, a);
  const ec = estadoColor(a.estado);
  const impresoras = (a.impresoras || "").split("|").filter((s) => s.trim());
  const software = (a.software || "").split("~~~").filter((s) => s.trim()).map((s) => s.split("|||"));

  return (
    <Drawer abierto onCerrar={onCerrar} ancho>
      <div className="ll-drawer-cab">
        <div style={{ minWidth: 0 }}>
          <div className="mono" style={{ fontSize: 21, fontWeight: 600, color: "var(--accent)", letterSpacing: -0.3, wordBreak: "break-all" }}>{a.nombre || a.serial}</div>
          <div style={{ fontSize: 12.5, color: "var(--ll-dim)", marginTop: 4 }}>{a.tipo} · {((a.marca || "") + " " + (a.modelo || "")).trim()}</div>
        </div>
        <button className="ll-cerrar" onClick={onCerrar} aria-label="Cerrar">✕</button>
      </div>

      <div style={{ display: "flex", alignItems: "center", gap: 9, padding: "12px 16px", borderRadius: 12, background: "color-mix(in srgb, var(--accent) 8%, transparent)", border: "1px solid color-mix(in srgb, var(--accent) 26%, transparent)" }}>
        <span style={{ width: 8, height: 8, borderRadius: "50%", background: ec, boxShadow: "0 0 10px " + ec }} />
        <span style={{ fontSize: 13.5, fontWeight: 600, color: ec }}>{a.estado}</span>
        <span style={{ flex: 1 }} />
        <span className="mono" style={{ fontSize: 11.5, color: "var(--ll-dim)" }}>SYNC {fmtFechaHora(a.updated)}</span>
      </div>

      <div style={{ display: "flex", gap: 10, flexWrap: "wrap" }}>
        <button className="ll-btn-borde" onClick={() => setVerQR((v) => !v)}>{verQR ? "Ocultar QR" : "Ver QR"}</button>
      </div>
      {verQR && <div style={{ display: "flex", justifyContent: "center" }}><div style={{ padding: 10, background: "#fff", borderRadius: 12 }}><QR value={a.serial || String(a.id)} size={130} /></div></div>}

      <div>
        <Rotulo>FICHA TÉCNICA</Rotulo>
        <Ficha filas={[
          ["Tipo", a.tipo], ["Fabricante", a.marca], ["Modelo", a.modelo], ["N° serie", a.serial], ["Garantía", a.garantia],
          ["CPU", a.cpu], ["RAM", a.ram], ["Disco", a.disco], ["S.O.", a.so], ["Versión S.O.", a.so_version],
          ["Arquitectura", a.so_arquitectura], ["IP", a.ip], ["Dominio", a.red],
        ]} />
      </div>

      <div>
        <Rotulo>RED E IDENTIDAD</Rotulo>
        <Ficha filas={[
          ["IP local", a.ip], ["IP pública", a.ip_publica], ["Gateway", a.gateway], ["MAC", a.mac],
          ["OU (Active Directory)", a.ou_ad], ["Último reinicio", a.ultimo_reinicio], ["Último login", a.ultimo_login],
        ]} />
      </div>

      <div>
        <Rotulo>ASIGNACIÓN</Rotulo>
        <Ficha filas={[
          ["Usuario", a.usuario || "Sin asignar"], ["Usuario alt.", a.usuario_alt], ["Sede", a.ubicacion], ["Grupo", a.grupo],
          ["Comentarios", a.comentarios], ["Últ. sync", fmtFechaHora(a.updated)],
        ]} />
      </div>

      <GarantiaActivo assetId={a.id} puedeEditar={puedeEditar} onCambio={(fin) => onGarantia && onGarantia(a.id, fin)} />

      <div>
        <Rotulo>SEGURIDAD</Rotulo>
        <div className="ll-ficha">
          <div><span className="k">Cifrado de disco</span><span className="v" style={{ color: COLOR_CIFRADO(a.cifrado), fontWeight: 600 }}>{a.cifrado || "—"}</span></div>
          {a.tpm && <div><span className="k">TPM</span><span className="v">{a.tpm}</span></div>}
          {gl && <>
            <div><span className="k">CrowdStrike</span><span className={"v" + (gl.edr !== "Activo" ? " alerta" : "")}>{gl.edr || "—"}</span></div>
            <div><span className="k">Antivirus</span><span className="v">{gl.antivirus || "—"}</span></div>
            <div><span className="k">Volúmenes sin cifrar</span><span className={"v" + (gl.volumenes_sin_cifrar ? " alerta" : "")}>{gl.volumenes_sin_cifrar || "Ninguno"}</span></div>
            <div><span className="k">Acceso remoto</span><span className={"v" + ((gl.acceso_remoto || "").includes("anydesk") ? " alerta" : "")}>{gl.acceso_remoto || "Ninguno"}</span></div>
          </>}
        </div>
        {(a.cifrado || "").startsWith("Cifrado (") && <div style={{ fontSize: 11.5, color: "var(--ll-warn)", marginTop: 8, lineHeight: 1.5 }}>El disco está cifrado pero la protección está suspendida: la clave queda disponible sin autenticación.</div>}
        {a.cifrado === "Sin acceso" && <div style={{ fontSize: 11.5, color: "var(--ll-dim)", marginTop: 8, lineHeight: 1.5 }}>No se pudo leer el estado (requiere privilegios elevados o BitLocker no está instalado).</div>}
      </div>

      {salud && <div>
        <Rotulo>SALUD Y SEGURIDAD</Rotulo>
        <div className="ll-ficha">
          <div><span className="k">Windows</span><span className="v">{textoWindows(salud)}{salud.so_build ? " · " + salud.so_build + (salud.so_ubr != null ? "." + salud.so_ubr : "") : ""}</span></div>
          <div><span className="k">Soporte de Microsoft</span><span className="v"><InsigniaSoporte f={salud} />{!salud.so_build && "—"}</span></div>
          {salud.con_datos ? <>
            <div><span className="k">Antivirus</span><span className="v"><EstadoAntivirus f={salud} /></span></div>
            <div><span className="k">Último parche</span><span className={"v" + (salud.dias_sin_parches > 30 ? " alerta" : "")}>
              {salud.ultimo_parche ? fmtFecha(salud.ultimo_parche) + (salud.dias_sin_parches != null ? ` (hace ${salud.dias_sin_parches} días)` : "") : "—"}</span></div>
            {salud.parches_90d != null && <div><span className="k">Parches en 90 días</span><span className="v">{salud.parches_90d}</span></div>}
            {(salud.discos || []).map((d, i) => (
              <div key={i}><span className="k">Disco {d.nombre || i + 1}</span>
                <span className={"v" + (salud.disco_estado === "riesgo" && (!/^(healthy|ok)$/i.test(d.salud || "") || d.desgaste >= 80 || d.errores_lectura > 0) ? " alerta" : "")}>
                  {[d.tipo, d.tamano_gb ? d.tamano_gb + " GB" : "", d.salud, d.desgaste != null ? d.desgaste + "% desgaste" : "",
                    d.temperatura != null ? d.temperatura + " °C" : "", d.errores_lectura ? d.errores_lectura + " errores de lectura" : ""].filter(Boolean).join(" · ")}
                </span></div>
            ))}
            {salud.bateria_salud != null && <div><span className="k">Batería</span><span className="v"><BarraBateria porcentaje={salud.bateria_salud} ciclos={salud.bateria_ciclos} />
              {salud.bateria_ciclos != null ? <span className="tenue" style={{ marginLeft: 8 }}>{salud.bateria_ciclos} ciclos</span> : null}</span></div>}
            <div><span className="k">Relevado</span><span className="v">{fmtFechaHora(salud.salud_actualizada)}</span></div>
          </> : <div><span className="k">Antivirus, parches, discos</span><span className="v tenue">Sin datos: el equipo todavía no tiene el agente nuevo</span></div>}
        </div>
      </div>}

      {gl && <div>
        <Rotulo>RELEVAMIENTO GLPI</Rotulo>
        <Ficha filas={[
          ["Batería", gl.bateria_salud != null ? gl.bateria_salud + "%" : null, gl.bateria_salud != null && gl.bateria_salud < 70],
          ["Discos", gl.discos], ["Office", gl.office, (gl.office || "").includes("Grace")], ["Windows", gl.os_build],
          ["BIOS", gl.bios], ["Último arranque", gl.ultimo_arranque], ["Relevado", (gl.fecha || "").replace("T", " ")],
        ]} />
      </div>}

      {a.tipo === "Monitor" ? <HistorialPcs assetId={a.id} abrir={abrirActivo} /> : <MonitoresConectados assetId={a.id} abrir={abrirActivo} />}

      {impresoras.length > 0 && <div>
        <Rotulo>IMPRESORAS ({impresoras.length})</Rotulo>
        <div className="ll-ficha">{impresoras.map((p, i) => <div key={i}><span className="v" style={{ textAlign: "left" }}>{p}</span></div>)}</div>
      </div>}

      {software.length > 0 && <div>
        <div style={{ display: "flex", alignItems: "center", marginBottom: 12 }}>
          <div className="ll-rotulo" style={{ flex: 1 }}>SOFTWARE INSTALADO ({software.length})</div>
          <button className="ll-btn-borde ll-btn-chico" onClick={() => setVerSoft((v) => !v)}>{verSoft ? "Ocultar" : "Ver"}</button>
        </div>
        {verSoft && <div className="ll-card" style={{ maxHeight: 300, overflowY: "auto" }}>
          <table className="ll-tabla"><thead><tr><th>NOMBRE</th><th>VERSIÓN</th><th>INSTALADO</th></tr></thead>
            <tbody>{software.map(([n, v, f], i) => <tr key={i}><td>{n}</td><td className="tenue">{v}</td><td className="tenue mono">{f}</td></tr>)}</tbody>
          </table>
        </div>}
      </div>}

      <div>
        <Rotulo>LICENCIAS VINCULADAS</Rotulo>
        <div style={{ padding: 18, textAlign: "center", fontSize: 12.5, color: "var(--ll-faint)", borderRadius: 12, border: "1px dashed var(--ll-line-3)" }}>
          El módulo de licencias no está incluido en esta versión.
        </div>
      </div>

      <div className="ll-seccion-clasica" style={{ display: "flex", flexDirection: "column", gap: 16 }}>
        <AdjuntosActivo assetId={a.id} usuario={user?.username} />
        <HistorialActivo assetId={a.id} />
      </div>

      <div style={{ marginTop: "auto", display: "flex", gap: 11 }}>
        {puedeEditar && <button className="ll-btn-primario" style={{ flex: 1, padding: 12 }} onClick={() => onEditar(a)}>Editar activo</button>}
        {puedeEliminar && <button className="ll-btn-peligro" style={{ padding: "12px 16px", borderRadius: 11 }} onClick={() => onEliminar(a)}>Eliminar</button>}
        <button className="ll-btn-borde" style={{ padding: "12px 20px", borderRadius: 11 }} onClick={onCerrar}>Cerrar</button>
      </div>
    </Drawer>
  );
}
