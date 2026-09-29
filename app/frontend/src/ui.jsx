// ui.jsx — Constantes y componentes chicos compartidos por las secciones.

export const SEDES = ["CABA","Rosario","Cordoba","Corrientes","Mendoza","Neuquen","Tigre","Resguarda"];
export const COLORES = ["#3987e5","#008300","#d55181","#c98500","#199e70","#d95926","#9085e9","#e66767"];
export const TIPOS = ["Notebook","Monitor","Impresora","Servidor","Switch","UPS","CPU"];
export const estadoClass = { "Activo":"badge-green","Mantenimiento":"badge-yellow","Dado de baja":"badge-gray","Libre":"badge-blue","Stock":"badge-blue","Robado":"badge-red" };
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
export const Field = ({ label, value, mono }) => !value||value==="-"||value===""?null:(
  <div className="field">
    <span className="field-label">{label}</span>
    <span className={`field-value${mono?" field-mono":""}`}>{value}</span>
  </div>
);
export const BarRow = ({ label, value, total, color }) => {
  const pct = total ? Math.round(value/total*100) : 0;
  return <div className="bar-row">
    <div className="bar-label"><span>{label}</span><strong>{value}</strong></div>
    <div className="bar-track"><div className="bar-fill" style={{width:`${pct}%`,background:color}}/></div>
  </div>;
};
export const emptyAsset = { nombre:"",tipo:"Notebook",marca:"",modelo:"",serial:"",usuario:"",usuario_alt:"",ubicacion:"",grupo:"",red:"",estado:"Activo",cpu:"",ram:"",disco:"",so:"",so_version:"",so_arquitectura:"",ip:"",garantia:"",comentarios:"" };
export const fmtDate = d => { if(!d) return "—"; try { return new Date(d).toLocaleDateString("es-AR"); } catch { return d; } };

export const COL_TEND = ["#00B0B9","#0B7285","#E67E22","#9085e9","#0ca30c","#d03b3b","#3987e5","#fab219","#6E7A90"];
