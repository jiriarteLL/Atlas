// ui.jsx — Constantes y componentes chicos compartidos por las secciones.

// Solo http(s): un link guardado nunca se usa como href si es javascript:, data:, etc.
export const urlSegura = (u) => (typeof u === "string" && /^https?:\/\//i.test(u.trim())) ? u.trim() : null;
export const SEDES = ["CABA","Rosario","Cordoba","Corrientes","Mendoza","Neuquen","Tigre","Resguarda"];
export const TIPOS = ["Notebook","Monitor","Impresora","Servidor","Switch","UPS","CPU"];
export const Badge = ({ label, map }) => <span className={`badge ${(map||{})[label]||"badge-gray"}`}><i className="badge-dot"/>{label}</span>;
export const hexToRgba = (hex, a) => { const n=parseInt(hex.replace("#",""),16); return `rgba(${(n>>16)&255},${(n>>8)&255},${n&255},${a})`; };
export const Tag = ({ label, color }) => <span className="tag" style={{color, background:hexToRgba(color,0.14)}}>{label}</span>;
export const QR = ({ value, size=100 }) => {
  const seed = value.split("").reduce((a,c)=>a+c.charCodeAt(0),0);
  const rng = n => { let x=Math.sin(seed+n)*10000; return x-Math.floor(x); };
  const g=10, cell=size/g, cells=[];
  for(let r=0;r<g;r++) for(let c=0;c<g;c++) if(rng(r*g+c)>0.45) cells.push({r,c});
  const corners=[[0,0],[0,1],[0,2],[1,0],[1,2],[2,0],[2,1],[2,2],[0,7],[0,8],[0,9],[1,7],[1,9],[2,7],[2,8],[2,9],[7,0],[7,1],[7,2],[8,0],[8,2],[9,0],[9,1],[9,2]];
  return <svg width={size} height={size}><rect width={size} height={size} fill="#fff"/>
    {cells.map(({r,c},i)=><rect key={i} x={c*cell} y={r*cell} width={cell} height={cell} fill="#0077B6"/>)}
    {corners.map(([r,c],i)=><rect key={"k"+i} x={c*cell} y={r*cell} width={cell} height={cell} fill="#0077B6"/>)}
    {[[1,1],[1,8],[8,1]].map(([r,c],i)=><rect key={"w"+i} x={c*cell} y={r*cell} width={cell} height={cell} fill="#fff"/>)}
  </svg>;
};
export const emptyAsset = { nombre:"",tipo:"Notebook",marca:"",modelo:"",serial:"",usuario:"",usuario_alt:"",ubicacion:"",grupo:"",red:"",estado:"Activo",cpu:"",ram:"",disco:"",so:"",so_version:"",so_arquitectura:"",ip:"",garantia:"",comentarios:"" };
export const fmtDate = d => { if(!d) return "—"; try { return new Date(d).toLocaleDateString("es-AR"); } catch { return d; } };

// El backend guarda los momentos en UTC (datetime.utcnow) y los manda sin zona ("2026-11-05T18:14:48"):
// sin la Z, el navegador los tomaria como hora local y la hora saldria corrida 3 h.
export const fechaUtc = d => {
  if (!d) return null;
  const s = String(d);
  return new Date(/[zZ]|[+-]\d\d:?\d\d$/.test(s) ? s : s.replace(" ", "T") + "Z");
};
// "05/11/2026 15:14" en hora de Argentina (para la ultima sincronizacion).
export const fmtFechaHora = d => {
  const f = fechaUtc(d);
  if (!f || isNaN(f)) return d ? String(d) : "—";
  return f.toLocaleDateString("es-AR", { day: "2-digit", month: "2-digit", year: "numeric" }) + " " +
         f.toLocaleTimeString("es-AR", { hour: "2-digit", minute: "2-digit", hour12: false });
};

export const COL_TEND = ["#00B0B9","#0B7285","#E67E22","#9085e9","#0ca30c","#d03b3b","#3987e5","#fab219","#6E7A90"];
