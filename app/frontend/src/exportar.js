// exportar.js — Exportaciones e importacion de activos (CSV y Excel).
// exceljs y html2canvas pesan mucho: se descargan recien cuando el usuario exporta.

const COLS_CSV = ["nombre","tipo","marca","modelo","serial","usuario","ubicacion","estado","cpu","ram","disco","so","ip","garantia","comentarios"];

function descargar(blob, nombre) {
  const url = URL.createObjectURL(blob);
  const a = document.createElement("a");
  a.href = url; a.download = nombre; a.click();
  URL.revokeObjectURL(url);
}

// Un valor de celda que empieza con = + - @ se neutraliza para que Excel no lo ejecute como formula.
const celda = (v) => {
  let s = String(v ?? "");
  if (/^[=+\-@\t\r]/.test(s)) s = "'" + s;
  return /[",\n]/.test(s) ? '"' + s.replace(/"/g, '""') + '"' : s;
};

export function exportarCSV(activos) {
  const filas = activos.map((a) => COLS_CSV.map((c) => celda(a[c])).join(","));
  descargar(new Blob([COLS_CSV.join(",") + "\n" + filas.join("\n")], { type: "text/csv" }), "atlas_inventario.csv");
}

// Separa una linea CSV respetando comillas ("a, b" es un solo campo; "" es una comilla).
function partirLinea(linea) {
  const campos = [];
  let actual = "", comillas = false;
  for (let i = 0; i < linea.length; i++) {
    const c = linea[i];
    if (comillas) {
      if (c === '"' && linea[i + 1] === '"') { actual += '"'; i++; }
      else if (c === '"') comillas = false;
      else actual += c;
    } else if (c === '"') comillas = true;
    else if (c === ",") { campos.push(actual); actual = ""; }
    else actual += c;
  }
  campos.push(actual);
  return campos;
}

// Devuelve los activos del archivo (solo filas con fabricante y modelo).
export async function leerCSV(archivo) {
  const texto = await archivo.text();
  return texto.trim().split(/\r?\n/).slice(1).map((linea) => {
    const v = partirLinea(linea);
    const o = {};
    COLS_CSV.forEach((c, i) => { o[c] = (v[i] || "").trim(); });
    return o;
  }).filter((a) => a.marca && a.modelo);
}

const XLSX = "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet";
const ENCABEZADO = (ws) => {
  ws.getRow(1).font = { bold: true, color: { argb: "FFFFFFFF" } };
  ws.getRow(1).eachCell((c) => { c.fill = { type: "pattern", pattern: "solid", fgColor: { argb: "FF0B7285" } }; });
};

export async function exportarActivosExcel(activos) {
  const ExcelJS = (await import("exceljs")).default;
  const wb = new ExcelJS.Workbook();
  const ws = wb.addWorksheet("Activos");
  ws.columns = [
    { header: "Nombre", key: "nombre", width: 22 }, { header: "Tipo", key: "tipo", width: 14 },
    { header: "Fabricante/Modelo", key: "modelo", width: 30 }, { header: "N Serie", key: "serial", width: 22 },
    { header: "IP", key: "ip", width: 16 }, { header: "Usuario", key: "usuario", width: 22 },
    { header: "Sede", key: "ubicacion", width: 14 }, { header: "S.O.", key: "so", width: 22 },
    { header: "Ult Sync", key: "updated", width: 18 }, { header: "Estado", key: "estado", width: 14 },
  ];
  activos.forEach((a) => ws.addRow({ nombre: a.nombre, tipo: a.tipo, modelo: ((a.marca || "") + " " + (a.modelo || "")).trim(), serial: a.serial, ip: a.ip, usuario: a.usuario, ubicacion: a.ubicacion, so: a.so, updated: a.updated, estado: a.estado }));
  ENCABEZADO(ws);
  descargar(new Blob([await wb.xlsx.writeBuffer()], { type: XLSX }), "activos_llya.xlsx");
}

// Reporte: tabla categoria/cantidad y, si se pasa el id de un elemento, una imagen del panel.
export async function exportarReporte(titulo, datos, elementId) {
  const ExcelJS = (await import("exceljs")).default;
  const wb = new ExcelJS.Workbook();
  const ws = wb.addWorksheet("Reporte");
  ws.mergeCells("A1:C1");
  ws.getCell("A1").value = titulo;
  ws.getCell("A1").font = { bold: true, size: 14, color: { argb: "FF0A2540" } };
  ws.getRow(1).height = 24;
  ws.getCell("A3").value = "Categoria";
  ws.getCell("B3").value = "Cantidad";
  ["A3", "B3"].forEach((c) => {
    ws.getCell(c).font = { bold: true, color: { argb: "FFFFFFFF" } };
    ws.getCell(c).fill = { type: "pattern", pattern: "solid", fgColor: { argb: "FF0B7285" } };
  });
  datos.forEach((d, i) => { ws.getCell("A" + (4 + i)).value = d.name; ws.getCell("B" + (4 + i)).value = d.value; });
  ws.getColumn("A").width = 28;
  ws.getColumn("B").width = 14;
  const el = elementId && document.getElementById(elementId);
  if (el) {
    const html2canvas = (await import("html2canvas")).default;
    const canvas = await html2canvas(el, { scale: 2, backgroundColor: "#0b1020" });
    const img = wb.addImage({ base64: canvas.toDataURL("image/png"), extension: "png" });
    ws.addImage(img, { tl: { col: 3, row: 2 }, ext: { width: canvas.width / 2, height: canvas.height / 2 } });
  }
  descargar(new Blob([await wb.xlsx.writeBuffer()], { type: XLSX }), "reporte_" + titulo.toLowerCase().replace(/[^a-z0-9]+/g, "_") + ".xlsx");
}
