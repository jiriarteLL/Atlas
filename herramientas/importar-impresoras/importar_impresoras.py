# -*- coding: utf-8 -*-
"""Importa a Atlas las impresoras PERSONALES/USB desde el inventario productivo (SQLite) y la planilla (Excel).

Las impresoras DE RED no se importan: entran "limpias desde la red" con el relevamiento SNMP (paso 2), que las crea
o actualiza por numero de serie. Este script las lista aparte, solo como informacion.

Fuentes:
  --productivo  assetmanager.db del inventario v1 (se abre en solo lectura)
  --excel       Inventario.xlsx: una hoja por sede con las columnas N° Inv., Tipo de Equipo, Marca, Modelo, N° Serie,
                Piso / Ubicacion, Estado, Asignado a, Tipo de Tenencia, Nombre
Destino: la base de Atlas que indique DATABASE_URL (PostgreSQL en la VM, o SQLite para ensayar).

Reglas:
- Se unen por numero de serie normalizado (mayusculas, sin espacios). Sin serie, se unen solo si coinciden sede y
  modelo/marca con un unico candidato; si no, entran por separado y se avisa.
- Del Excel: asignacion, tenencia, proveedor, piso y nro. de inventario. Del productivo: IP, nombre de cola, modelo
  (si el Excel no lo tiene) y lo util de los comentarios (piso, toner, notas).
- Las credenciales de administracion NUNCA se importan: cualquier "User:", "Pass:", "clave:" se descarta de todos los
  textos, y el script se niega a escribir si algo con forma de credencial llegara a un campo. En las impresoras de
  red se deja solo la referencia --credencial-ref (por defecto "KeePassXC - clave comun de impresoras").
- Solo se escriben las personales/USB (ip "USB (HOME)"/"USB (ESTUDIO)", comentario "Personal" o, en el Excel,
  asignadas a una persona), con su asignacion, piso, modelo, serie y nro. de inventario.
- Upsert por serial: si ya existe una impresora con ese serial (p. ej. cargada antes) se actualiza, no se duplica.
  Si el serial pertenece a otro tipo de activo, se saltea y se avisa.

Uso (sin --confirmar es SIMULACRO: hace todo en una transaccion, muestra el reporte y deshace):
  set DATABASE_URL=postgres://...      (o sqlite:///C:/temp/prueba.db)
  python importar_impresoras.py --productivo assetmanager.db --excel Inventario.xlsx
  python importar_impresoras.py --productivo assetmanager.db --excel Inventario.xlsx --confirmar
"""
import argparse
import os
import re
import secrets
import sqlite3
import sys
import unicodedata
import uuid
from datetime import datetime

os.environ.setdefault("JWT_SECRET", secrets.token_hex(32))   # config lo exige; el script no emite tokens
BACKEND = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", "app", "backend"))
sys.path.insert(0, BACKEND)

from impresoras import quitar_credenciales, tiene_credencial  # noqa: E402

CREDENCIAL_REF = "KeePassXC - clave común de impresoras"
HOJAS = {"caba 1": "CABA", "caba1": "CABA", "caba 2": "CABA", "caba2": "CABA", "tigre": "Tigre",
         "corrientes": "Corrientes", "rosario": "Rosario", "cordoba": "Cordoba", "mendoza": "Mendoza",
         "neuquen": "Neuquen", "resguarda": "Resguarda"}
SIN_PERSONA = {"", "sistemas", "propio", "canal directo"}


# ---------------------------------------------------------------- utilidades
def sin_acentos(s):
    return "".join(c for c in unicodedata.normalize("NFKD", str(s or "")) if not unicodedata.combining(c))


def clave_col(s):
    return re.sub(r"\s+", " ", re.sub(r"[^a-z0-9 /]", "", sin_acentos(s).lower())).strip()


def norm_serial(s):
    s = re.sub(r"\s+", "", str(s or "")).upper()
    return "" if s in ("", "NONE", "N/A", "-") else s


def texto(v):
    return "" if v is None else str(v).strip()


def es_ip(s):
    return bool(re.fullmatch(r"\d{1,3}(\.\d{1,3}){3}", texto(s)))


def parsear_comentario(c):
    """Comentario del productivo -> piso, toner, notas, personal. Las credenciales se descartan primero."""
    limpio = quitar_credenciales(c)
    piso = toner = ""
    personal = False
    notas = []
    for parte in [p.strip() for p in limpio.split(" - ") if p.strip()]:
        m = re.fullmatch(r"(?i)piso\s*(\w+)", parte)
        t = re.fullmatch(r"(?i)toner\s+(.+)", parte)
        if m:
            piso = m.group(1)
        elif t:
            toner = t.group(1).strip()
        elif parte.lower() == "personal":
            personal = True
        else:
            notas.append(parte)
    return {"piso": piso, "toner": toner, "personal": personal, "notas": notas}


# ---------------------------------------------------------------- lectura de fuentes
def leer_productivo(ruta):
    con = sqlite3.connect("file:%s?mode=ro" % ruta.replace("\\", "/"), uri=True)
    con.row_factory = sqlite3.Row
    filas = [dict(r) for r in con.execute(
        "select nombre, marca, modelo, serial, ip, ubicacion, usuario, comentarios from assets where tipo = 'Impresora'")]
    con.close()
    return filas


def leer_excel(ruta):
    import openpyxl
    wb = openpyxl.load_workbook(ruta, read_only=True, data_only=True)
    salida = []
    for ws in wb.worksheets:
        sede = HOJAS.get(clave_col(ws.title))
        if not sede:
            continue
        filas = list(ws.iter_rows(values_only=True))
        enc = next((i for i, f in enumerate(filas[:10]) if any(clave_col(c) == "tipo de equipo" for c in f)), None)
        if enc is None:
            continue
        cols = {clave_col(c): j for j, c in enumerate(filas[enc]) if c}

        def col(f, nombre, cols=cols):
            j = cols.get(nombre)
            return texto(f[j]) if j is not None and j < len(f) else ""
        for f in filas[enc + 1:]:
            if clave_col(col(f, "tipo de equipo")) != "impresora":
                continue
            salida.append({"hoja": ws.title, "sede": sede, "inv": col(f, "n inv"), "marca": col(f, "marca"),
                           "modelo": col(f, "modelo"), "serial": col(f, "n serie"),
                           "piso": col(f, "piso / ubicacion"), "estado": col(f, "estado"),
                           "asignado": col(f, "asignado a"), "tenencia": col(f, "tipo de tenencia"),
                           "nombre": col(f, "nombre")})
    return salida


# ---------------------------------------------------------------- union de fuentes
def unir(prod, excel, avisos):
    """Devuelve una lista de pares (fila_productivo|None, fila_excel|None)."""
    por_serie = {}
    for e in excel:
        s = norm_serial(e["serial"])
        if s:
            por_serie.setdefault(s, []).append(e)
    for s, filas in por_serie.items():
        if len(filas) > 1:
            avisos.append("Serie %s aparece en %d filas del Excel (%s): se usa la de la sede que corresponda" % (
                s, len(filas), ", ".join("%s-%s" % (f["hoja"], f["inv"]) for f in filas)))
    usadas = set()
    sin_serie_excel = [e for e in excel if not norm_serial(e["serial"])]
    pares = []
    for p in prod:
        s = norm_serial(p["serial"])
        e = None
        if s and s in por_serie:
            filas = por_serie[s]
            e = next((f for f in filas if f["sede"] == (p["ubicacion"] or "")), filas[0])
            if e["sede"] != (p["ubicacion"] or ""):
                avisos.append("Serie %s: el productivo dice %s y el Excel %s (se toma la sede del productivo)" % (
                    s, p["ubicacion"], e["sede"]))
            usadas.update(id(f) for f in filas)
        elif not s:
            cands = [x for x in sin_serie_excel if id(x) not in usadas and x["sede"] == (p["ubicacion"] or "")
                     and _modelo_parecido(p, x)]
            if len(cands) == 1:
                e = cands[0]
                usadas.add(id(e))
                avisos.append("Sin serie: '%s' del productivo se unio con la fila %s-%s del Excel por sede y modelo" % (
                    p["nombre"], e["hoja"], e["inv"]))
        pares.append((p, e))
    for s, filas in por_serie.items():
        if id(filas[0]) not in usadas:
            pares.append((None, filas[0]))
            usadas.update(id(f) for f in filas)
            avisos.append("Solo en el Excel: %s-%s %s %s serie %s" % (filas[0]["hoja"], filas[0]["inv"],
                                                                     filas[0]["marca"], filas[0]["modelo"], s))
    for e in sin_serie_excel:
        if id(e) not in usadas:
            pares.append((None, e))
            avisos.append("Solo en el Excel y sin serie: %s-%s %s %s (entra por separado, revisar)" % (
                e["hoja"], e["inv"], e["marca"], e["modelo"]))
    return pares


def _modelo_parecido(p, e):
    pm = clave_col(" ".join([p["marca"] or "", p["modelo"] or ""]))
    em = clave_col(e["modelo"])
    if em:
        return em in pm or pm in em
    return bool(e["marca"]) and clave_col(e["marca"]) in pm


# ---------------------------------------------------------------- armado del registro final
def armar(p, e, credencial_ref):
    """(fila productivo, fila excel) -> dict con campos de Asset + detalle, y origen de cada dato."""
    r, o = {}, {}
    def poner(campo, valor, origen):
        if valor not in ("", None):
            r[campo] = valor
            o[campo] = origen
    com = parsear_comentario(p["comentarios"] if p else "")
    asignado = texto(e["asignado"]) if e else ""
    persona = asignado if clave_col(asignado) not in SIN_PERSONA else ""
    ip_prod = texto(p["ip"]) if p else ""
    usb = ip_prod.upper().startswith("USB")
    personal = bool(persona) or com["personal"] or usb
    if personal and not persona and p and not re.match(r"(?i)impresora|solo|cola", p["nombre"] or ""):
        persona = p["nombre"]
        o["usuario"] = "productivo (nombre)"
    poner("serial", norm_serial((p or {}).get("serial") or (e or {}).get("serial")), "productivo" if p and p["serial"] else "excel")
    poner("marca", (e and e["marca"]) or (p and p["marca"]) or "", "excel" if e and e["marca"] else "productivo")
    modelo = (p and p["modelo"]) or (e and e["modelo"]) or ""
    poner("modelo", modelo, "productivo" if p and p["modelo"] else "excel")
    sede = (p and p["ubicacion"]) or (e and e["sede"]) or ""
    poner("ubicacion", sede, "productivo" if p and p["ubicacion"] else "excel")
    if es_ip(ip_prod):
        poner("ip", ip_prod, "productivo")
    if persona:
        r["usuario"] = persona
        o.setdefault("usuario", "excel (asignado a)" if e and persona == asignado else "productivo")
    cola = ""
    for cand in ((p or {}).get("nombre"), (e or {}).get("nombre")):
        if cand and re.fullmatch(r"[A-Z0-9][A-Z0-9_\-]{3,}", texto(cand)):
            cola = texto(cand)
            break
    poner("nombre_cola", cola, "productivo" if p and cola == p["nombre"] else "excel")
    if personal:
        nombre = "%s (%s)" % (modelo or "Impresora", persona) if persona else (modelo or "Impresora personal")
        o["nombre"] = "armado: modelo + persona"
    else:
        nombre = cola or (p and p["nombre"]) or "%s (%s-%s)" % (
            " ".join(x for x in [(e or {}).get("marca", ""), (e or {}).get("modelo", "")] if x) or "Impresora",
            (e or {}).get("hoja", ""), (e or {}).get("inv", ""))
        o["nombre"] = "productivo" if p else "excel/armado"
    r["nombre"] = nombre.strip()
    piso_x = re.sub(r"(?i)^piso\s*", "", texto(e["piso"])) if e else ""
    poner("piso", piso_x or com["piso"], "excel" if piso_x else "productivo (comentario)")
    poner("toner_modelo", com["toner"], "productivo (comentario)")
    ten = clave_col(e["tenencia"]) if e else ""
    tenencia = {"tercerizado": "tercerizada", "alquilado": "alquilada", "propio": "propia"}.get(ten, "")
    if not tenencia and clave_col(asignado) == "canal directo":
        tenencia = "tercerizada"
    if not tenencia and clave_col(asignado) in ("propio", "sistemas"):
        tenencia = "propia"
    poner("tenencia", tenencia, "excel")
    if clave_col(asignado) == "canal directo":
        poner("proveedor", "Canal Directo", "excel (asignado a)")
    if e and e["inv"]:
        poner("nro_inventario", "%s-%s" % (e["hoja"], e["inv"]), "excel")
    notas = list(com["notas"])
    if usb:
        lugar = re.search(r"\((\w+)\)", ip_prod)
        notas.append("Conectada por USB" + (" (%s)" % lugar.group(1).lower() if lugar else ""))
    poner("notas", " - ".join(n for n in notas if n), "productivo (comentario)")
    r["conexion"] = "usb" if personal else "red"
    r["uso"] = "personal" if personal else "compartida"
    m = " ".join([r.get("marca", ""), modelo]).lower()
    r["color"] = "color" in m
    r["escaner"] = "mfp" in m or "scann" in " ".join(notas).lower() or "tank mfp" in m
    r["duplex"] = False
    if not personal:
        r["credencial_ref"] = credencial_ref
        o["credencial_ref"] = "referencia fija (la clave queda en KeePassXC)"
    r["estado"] = "Activo"
    return r, o


def separar(registros):
    """(personales/USB a importar, de red que NO se importan: las crea el relevamiento SNMP)."""
    personales = [x for x in registros if x[0]["uso"] == "personal"]
    de_red = [x for x in registros if x[0]["uso"] != "personal"]
    return personales, de_red


# ---------------------------------------------------------------- escritura
CAMPOS_ASSET = ("nombre", "marca", "modelo", "serial", "estado", "usuario", "ubicacion", "ip")


def main():
    ap = argparse.ArgumentParser(description="Importa impresoras a Atlas (productivo + Excel).")
    ap.add_argument("--productivo", required=True)
    ap.add_argument("--excel", required=True)
    ap.add_argument("--credencial-ref", default=CREDENCIAL_REF)
    ap.add_argument("--confirmar", action="store_true", help="guardar (sin esto es un simulacro)")
    args = ap.parse_args()
    if not os.getenv("DATABASE_URL"):
        sys.exit("Falta DATABASE_URL (base de Atlas de destino).")

    from database import Asset, Historial, ImpresoraDetalle, SessionLocal, engine, init_db

    avisos = []
    prod = leer_productivo(args.productivo)
    excel = leer_excel(args.excel)
    pares = unir(prod, excel, avisos)
    registros, de_red = separar([armar(p, e, args.credencial_ref) for p, e in pares])

    # Defensa final: nada con forma de credencial puede llegar a la base ni al reporte.
    for r, _ in registros + de_red:
        for k, v in r.items():
            if isinstance(v, str) and tiene_credencial(v):
                sys.exit("ABORTADO: el campo %s de '%s' tiene forma de credencial." % (k, r.get("nombre")))

    print("Destino: %s" % engine.url.render_as_string(hide_password=True))
    print("Modo: %s" % ("CONFIRMADO (guarda)" if args.confirmar else "SIMULACRO (deshace al final)"))
    print("Fuentes: productivo %d impresoras | Excel %d filas de impresora | %d personales/USB a importar | "
          "%d de red que NO se importan\n" % (len(prod), len(excel), len(registros), len(de_red)))
    init_db()
    db = SessionLocal()
    altas = actualizadas = salteadas = 0
    try:
        for r, o in registros:
            det = {k: r[k] for k in ("conexion", "uso", "piso", "nombre_cola", "color", "duplex", "escaner",
                                     "toner_modelo", "tenencia", "proveedor", "nro_inventario", "credencial_ref",
                                     "notas") if k in r}
            a = None
            if r.get("serial"):
                a = db.query(Asset).filter(Asset.serial.isnot(None), Asset.serial != "").filter(
                    Asset.serial.ilike(r["serial"])).first()
            elif r.get("nombre"):
                a = db.query(Asset).filter(Asset.tipo == "Impresora", Asset.nombre == r["nombre"]).first()
            if a is not None and a.tipo != "Impresora":
                avisos.append("Serie %s ya es un %s en Atlas (%s): se saltea" % (r["serial"], a.tipo, a.nombre))
                salteadas += 1
                accion = "SALTEADA"
            elif a is None:
                a = Asset(id=("A" + str(uuid.uuid4())[:6]).upper(), tipo="Impresora", updated=datetime.utcnow(),
                          **{c: r.get(c, "") for c in CAMPOS_ASSET})
                db.add(a)
                db.flush()
                db.add(ImpresoraDetalle(asset_id=a.id, actualizado=datetime.utcnow(), **det))
                db.add(Historial(asset_id=a.id, usuario="importacion-impresoras", campo="alta", valor_ant="",
                                 valor_new=a.nombre, accion="sincronizacion"))
                altas += 1
                accion = "ALTA"
            else:
                for c in CAMPOS_ASSET:
                    if r.get(c):
                        setattr(a, c, r[c])
                a.updated = datetime.utcnow()
                d = db.query(ImpresoraDetalle).filter(ImpresoraDetalle.asset_id == a.id).first()
                if d is None:
                    db.add(ImpresoraDetalle(asset_id=a.id, actualizado=datetime.utcnow(), **det))
                else:
                    for k, v in det.items():
                        setattr(d, k, v)
                    d.actualizado = datetime.utcnow()
                actualizadas += 1
                accion = "ACTUALIZA"
            print("%-9s %-46s serie %-16s %-10s piso %-4s %-4s %-10s asignado: %-22s tenencia: %-11s %s" % (
                accion, r["nombre"][:46], r.get("serial", "-") or "-", r.get("ubicacion", ""), r.get("piso", "-"),
                r["conexion"].upper(), r.get("ip", ""), r.get("usuario", "-"), r.get("tenencia", "-") or "-",
                ("cola " + r["nombre_cola"]) if r.get("nombre_cola") else ""))
            print("          origen: " + ", ".join("%s=%s" % (k, v) for k, v in sorted(o.items())))
        print("\nAltas: %d | actualizadas: %d | salteadas: %d" % (altas, actualizadas, salteadas))
        print("\nDe red, NO se importan (las crea el relevamiento SNMP por numero de serie) - solo informacion:")
        for r, _ in de_red:
            print("  %-34s serie %-16s %-10s %-15s %s" % (
                r["nombre"][:34], r.get("serial", "-") or "-", r.get("ubicacion", ""), r.get("ip", "") or "(sin IP)",
                ((r.get("marca", "") + " " + r.get("modelo", "")).strip())[:40]))
        if avisos:
            print("\nAvisos:")
            for a_ in avisos:
                print("  - " + a_)
        print("\nCredenciales: ninguna (los usuarios y contrasenas de los comentarios se descartaron; las de red "
              "llevan solo la referencia '%s')." % args.credencial_ref)
        if args.confirmar:
            db.commit()
            print("LISTO: guardado.")
        else:
            db.rollback()
            print("SIMULACRO: no se guardo nada (correr con --confirmar para guardar).")
    except Exception:
        db.rollback()
        raise
    finally:
        db.close()


if __name__ == "__main__":
    main()
