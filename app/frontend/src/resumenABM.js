// resumenABM.js — Abre una pestaña con el resumen del ABM para pegar en el Portal GO.

export function generarResumenABM(tipo, filas) {
  const rowsHtml = filas.map(f=>{
    if(f[0]==='__sep__') return '<div style="height:16px"></div>';
    const val = (f[1]===undefined||f[1]===null||f[1]==='') ? '-' : f[1];
    return '<div class="row"><div class="lbl">'+f[0]+'</div><div class="val">'+val+'</div></div>';
  }).join('');
  const plainText = filas.filter(f=>f[0]!=='__sep__').map(f=>{
    const val = (f[1]===undefined||f[1]===null||f[1]==='') ? '-' : f[1];
    return f[0]+': '+val;
  }).join('\n');
  const plainTextEsc = plainText.replace(/</g,'&lt;').replace(/>/g,'&gt;');
  const w = window.open("","_blank");
  if(!w){ alert("El navegador bloqueo la pestana nueva. Habilita los pop-ups e intenta de nuevo."); return; }
  w.document.write(`<!DOCTYPE html><html><head><title>ABM ${tipo}</title>
  <style>
    body{margin:0;font-family:Arial,Helvetica,sans-serif;background:#F5F6F7;color:#3A3A3A;}
    .wrap{max-width:760px;margin:0 auto;background:#fff;}
    .head{background:#0B4F6C;color:#fff;padding:22px 28px;border-bottom:4px solid #00B0B9;}
    .head h1{margin:0 0 4px;font-size:20px;}
    .head p{margin:0;color:#cfe4e8;font-size:13px;}
    .actions{padding:18px 28px;background:#EAF3F6;display:flex;gap:10px;align-items:center;flex-wrap:wrap;}
    button,.linkbtn{background:#0B7285;color:#fff;border:none;padding:11px 20px;border-radius:6px;font-weight:700;font-size:14px;cursor:pointer;text-decoration:none;display:inline-block;}
    button:hover,.linkbtn:hover{background:#00B0B9;}
    .linkbtn.dark{background:#0B4F6C;}
    .copied{color:#0B7285;font-weight:700;font-size:13.5px;display:none;}
    .row{display:flex;padding:10px 28px;border-bottom:1px solid #eee;}
    .lbl{font-weight:700;width:240px;color:#0B4F6C;flex-shrink:0;}
    .val{color:#111;}
    @media print{ .actions{display:none;} body{background:#fff;} }
  </style></head><body>
  <div class="wrap">
    <div class="head">
      <h1>ABM ${tipo}</h1>
      <p>Resumen generado para pegar en el Sistema de Tickets - Portal GO</p>
    </div>
    <div class="actions">
      <button onclick="copiarTodo()">Copiar todo</button>
      <button onclick="window.print()">Imprimir / Guardar PDF</button>
      <a class="linkbtn dark" href="https://portal.llyasoc.com/tickets/soporte" target="_blank">Ir al Portal GO</a>
      <span class="copied" id="copiedMsg">Copiado al portapapeles</span>
    </div>
    ${rowsHtml}
  </div>
  <textarea id="plainText" style="position:absolute;left:-9999px;">${plainTextEsc}</textarea>
  <script>
    function copiarTodo(){
      const ta = document.getElementById('plainText');
      ta.style.left = '0px'; ta.select();
      try{
        navigator.clipboard.writeText(ta.value).then(showCopied, function(){
          document.execCommand('copy'); showCopied();
        });
      }catch(e){
        document.execCommand('copy'); showCopied();
      }
      ta.style.left = '-9999px';
    }
    function showCopied(){
      const m = document.getElementById('copiedMsg');
      m.style.display='inline'; setTimeout(()=>m.style.display='none', 2500);
    }
  </script>
  </body></html>`);
  w.document.close();
}
