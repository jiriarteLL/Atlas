# -*- coding: utf-8 -*-
"""Monitores (fase B): los manda el agente de Atlas en /api/sync, campo "monitores_detalle".

Cada monitor EXTERNO con numero de serie valido es un activo tipo "Monitor" (ficha, historial, adjuntos y QR se
reusan), identificado por fabricante PnP + codigo de producto + serie (lo que guarda el EDID del monitor), con su
detalle en monitor_detalle. Queda vinculado a la PC donde se lo vio conectado: monitor_conexion guarda desde/hasta
para tener el historial; si aparece en otra PC se cierra la conexion anterior y se registra "movido de PC-X a PC-Y".
Que una notebook se desenchufe del monitor no cierra la conexion (sigue siendo "su" monitor): para eso esta
monitor_detalle.visto (ultima vez que se lo vio conectado).

Las pantallas internas de las notebooks y los monitores sin serie NO son activos: quedan como dato de la PC
(pc_monitores, la ultima lista que mando el agente). Usuario y sede del monitor son los de la PC. Nunca se pisan
los campos administrativos cargados a mano (estado, comentarios, garantia).
"""
import json
import re
import uuid
from datetime import datetime, timedelta

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import func

from auth import MODULOS_FICHA, UserOut, require_modulo
from database import Asset, Historial, MonitorConexion, MonitorDetalle, PcMonitores, SessionLocal

router = APIRouter(prefix="/api/monitores", tags=["monitores"])

USUARIO = "agente-automatico"
MAX_MONITORES = 16
MAX_JSON = 8000
CONEXIONES = ("HDMI", "DisplayPort", "VGA", "DVI", "Interna", "Dock USB", "Miracast", "UDI", "Otra")
DIAS_SIN_VER = 30
ANIOS_ANTIGUO = 7

# Codigo PnP del fabricante (3 letras del EDID) -> marca. Los de paneles de notebook casi siempre son internos.
MARCAS_PNP = {
    "SAM": "Samsung", "SEC": "Samsung", "SDC": "Samsung Display", "LEN": "Lenovo", "DEL": "Dell", "HWP": "HP",
    "HPN": "HP", "HPQ": "HP", "GSM": "LG", "LGD": "LG Display", "AOC": "AOC", "PHL": "Philips", "ACI": "Asus",
    "AUS": "Asus", "BNQ": "BenQ", "VSC": "ViewSonic", "ACR": "Acer", "BOE": "BOE", "AUO": "AU Optronics",
    "CMN": "Innolux", "CMO": "Chi Mei", "IVO": "InfoVision", "SHP": "Sharp", "SNY": "Sony", "NEC": "NEC",
    "MSI": "MSI", "GBT": "Gigabyte", "HSD": "HannStar", "HKC": "HKC", "APP": "Apple", "MEI": "Panasonic",
    "ENC": "Eizo", "XMI": "Xiaomi", "HIQ": "Hyundai", "FUS": "Fujitsu", "IFS": "InFocus", "TOS": "Toshiba",
}


# ---------------------------------------------------------------- normalizacion de lo que manda el agente
def _txt(v, largo=80):
    s = "" if v is None else str(v)
    return re.sub(r"\s+", " ", "".join(ch for ch in s if ch.isprintable())).strip()[:largo]


def _ent(v, minimo, maximo):
    try:
        n = int(float(v))
    except (TypeError, ValueError):
        return None
    return n if minimo <= n <= maximo else None


def serie_valida(s):
    """El EDID trae "0", "00000000", "1234567890" o vacio cuando el fabricante no grabo la serie."""
    s = (s or "").strip()
    return len(s) >= 4 and len(set(s)) > 1 and s not in ("1234567890", "123456789", "0123456789")


def limitar_monitores(v):
    """Validador de AssetSync.monitores_detalle: lista de tamano razonable o None (nunca rompe el sync)."""
    if not isinstance(v, list):
        return None
    try:
        if len(json.dumps(v, default=str)) > MAX_JSON:
            return None
    except (TypeError, ValueError):
        return None
    return [x for x in v if isinstance(x, dict)][:MAX_MONITORES]


def normalizar(m):
    fab = _txt(m.get("fabricante"), 3).upper()
    fab = fab if re.fullmatch(r"[A-Z]{3}", fab) else ""
    try:
        pulgadas = round(float(m.get("pulgadas")), 1)
        pulgadas = pulgadas if 5 <= pulgadas <= 120 else None
    except (TypeError, ValueError):
        pulgadas = None
    conexion = _txt(m.get("conexion"), 20)
    conexion = next((c for c in CONEXIONES if c.lower() == conexion.lower()), "Otra" if conexion else "")
    interno = m.get("interno") is True or str(m.get("interno")).lower() == "true" or conexion == "Interna"
    return {"fabricante": fab, "marca": MARCAS_PNP.get(fab, fab), "modelo": _txt(m.get("modelo"), 64),
            "codigo_producto": re.sub(r"[^0-9A-Fa-f]", "", _txt(m.get("codigo_producto"), 8)).upper(),
            "serie": _txt(m.get("serie"), 40), "anio": _ent(m.get("anio"), 1990, 2100),
            "semana": _ent(m.get("semana"), 1, 53), "pulgadas": pulgadas, "conexion": conexion, "interno": interno}


def clave_de(m):
    return "|".join((m["fabricante"], m["codigo_producto"], m["serie"])).upper()


# ---------------------------------------------------------------- sync
def con_marca(marca, modelo):
    """ "HP" + "HP E24 G4" -> "HP E24 G4" (muchos EDID ya traen la marca en el nombre del modelo)."""
    marca, modelo = (marca or "").strip(), (modelo or "").strip()
    return modelo if marca and modelo.upper().startswith(marca.upper()) else (marca + " " + modelo).strip()


def _nombre(m):
    return con_marca(m["marca"], m["modelo"] or m["codigo_producto"]) or m["serie"]


def procesar_monitores(db, pc, lista, ahora=None):
    """La llama _aplicar_sync con la lista ya validada. Guarda la foto en la PC y da de alta/mueve los externos."""
    ahora = ahora or datetime.utcnow()
    mons = [normalizar(m) for m in lista]
    fila = db.get(PcMonitores, pc.id)
    if fila is None:
        fila = PcMonitores(asset_id=pc.id)
        db.add(fila)
    fila.detalle = json.dumps(mons, ensure_ascii=False)
    fila.actualizado = ahora
    vistos = set()
    for m in mons:
        if m["interno"] or not serie_valida(m["serie"]) or not m["fabricante"]:
            continue
        clave = clave_de(m)
        if clave in vistos:
            continue
        vistos.add(clave)
        det = db.query(MonitorDetalle).filter(MonitorDetalle.clave == clave).first()
        mon = db.get(Asset, det.asset_id) if det else None
        if mon is None:
            # un monitor cargado a mano con esa serie se adopta en vez de duplicarlo
            mon = (db.query(Asset).filter(Asset.tipo == "Monitor", func.upper(Asset.serial) == m["serie"].upper())
                   .first())
        if mon is None:
            mon = Asset(id=("A" + str(uuid.uuid4())[:6]).upper(), tipo="Monitor", estado="Activo", nombre=_nombre(m),
                        marca=m["marca"], modelo=m["modelo"] or m["codigo_producto"], serial=m["serie"],
                        usuario=pc.usuario or "", ubicacion=pc.ubicacion or "", updated=ahora)
            db.add(mon)
            db.flush()
            db.add(Historial(asset_id=mon.id, usuario=USUARIO, campo="alta", valor_ant="",
                             valor_new=f"{mon.nombre} (serie {mon.serial}) conectado a {pc.nombre}",
                             accion="sincronizacion"))
        else:
            cambios = {}
            for campo, valor in (("usuario", pc.usuario or ""), ("ubicacion", pc.ubicacion or "")):
                if valor and (getattr(mon, campo) or "") != valor:
                    cambios[campo] = (getattr(mon, campo) or "", valor)
                    setattr(mon, campo, valor)
            for campo, valor in (("marca", m["marca"]), ("modelo", m["modelo"] or m["codigo_producto"])):
                if valor and not getattr(mon, campo):   # solo completa: lo cargado a mano no se pisa
                    cambios[campo] = ("", valor)
                    setattr(mon, campo, valor)
            for campo, (antes, despues) in cambios.items():
                db.add(Historial(asset_id=mon.id, usuario=USUARIO, campo=campo, valor_ant=str(antes),
                                 valor_new=str(despues), accion="sincronizacion"))
            mon.updated = ahora
        if det is None:
            det = db.query(MonitorDetalle).filter(MonitorDetalle.asset_id == mon.id).first()
        if det is None:
            det = MonitorDetalle(asset_id=mon.id)
            db.add(det)
        anterior = det.pc_id
        det.clave, det.fabricante, det.codigo_producto = clave, m["fabricante"], m["codigo_producto"]
        det.pulgadas, det.anio, det.semana = m["pulgadas"], m["anio"], m["semana"]
        det.conexion, det.pc_id, det.visto, det.actualizado = m["conexion"], pc.id, ahora, ahora
        if anterior != pc.id:
            abierta = (db.query(MonitorConexion).filter(MonitorConexion.monitor_id == mon.id,
                                                        MonitorConexion.hasta.is_(None)).all())
            for c in abierta:
                c.hasta = ahora
            db.add(MonitorConexion(monitor_id=mon.id, pc_id=pc.id, pc_nombre=pc.nombre or "", desde=ahora,
                                   conexion=m["conexion"]))
            if anterior:
                previa = db.get(Asset, anterior)
                db.add(Historial(asset_id=mon.id, usuario=USUARIO, campo="conectado_a",
                                 valor_ant=previa.nombre if previa else anterior, valor_new=pc.nombre or pc.id,
                                 accion="sincronizacion"))


def borrar_datos_monitor(db, asset_id):
    """Para el borrado de un activo (en SQLite las FK no se aplican solas): como monitor y como PC."""
    db.query(MonitorConexion).filter(MonitorConexion.monitor_id == asset_id).delete(synchronize_session=False)
    db.query(MonitorDetalle).filter(MonitorDetalle.asset_id == asset_id).delete(synchronize_session=False)
    db.query(PcMonitores).filter(PcMonitores.asset_id == asset_id).delete(synchronize_session=False)
    db.query(MonitorDetalle).filter(MonitorDetalle.pc_id == asset_id).update({"pc_id": None}, synchronize_session=False)


# ---------------------------------------------------------------- lectura
def _pcs(db, ids):
    ids = [i for i in ids if i]
    return {a.id: a for a in db.query(Asset).filter(Asset.id.in_(ids))} if ids else {}


def _fila(a, d, pc, hoy):
    sin_ver = bool(d and d.visto and datetime.utcnow() - d.visto > timedelta(days=DIAS_SIN_VER))
    return {"id": a.id, "nombre": a.nombre, "marca": a.marca, "modelo": a.modelo, "serial": a.serial,
            "estado": a.estado, "usuario": a.usuario, "sede": a.ubicacion, "comentarios": a.comentarios,
            "pulgadas": d.pulgadas if d else None, "conexion": d.conexion if d else "",
            "anio": d.anio if d else None, "semana": d.semana if d else None,
            "fabricante": d.fabricante if d else "", "codigo_producto": d.codigo_producto if d else "",
            "visto": d.visto if d else None, "sin_ver": sin_ver,
            "antiguo": bool(d and d.anio and hoy.year - d.anio > ANIOS_ANTIGUO),
            "pc": {"id": pc.id, "nombre": pc.nombre, "usuario": pc.usuario, "sede": pc.ubicacion} if pc else None}


def tamano(p):
    if not p:
        return "Sin dato"
    return "Hasta 21\"" if p < 21.5 else "22\" a 24\"" if p < 25 else "25\" a 27\"" if p < 28 else "28\" o más"


@router.get("")
def listar(user: UserOut = Depends(require_modulo("activos"))):
    db = SessionLocal()
    try:
        pares = (db.query(Asset, MonitorDetalle).outerjoin(MonitorDetalle, MonitorDetalle.asset_id == Asset.id)
                 .filter(Asset.tipo == "Monitor", Asset.estado != "Dado de baja").order_by(Asset.nombre).all())
        pcs = _pcs(db, [d.pc_id for _, d in pares if d])
        hoy = datetime.utcnow()
        filas = [_fila(a, d, pcs.get(d.pc_id) if d else None, hoy) for a, d in pares]
        por_tamano = {}
        for f in filas:
            por_tamano[tamano(f["pulgadas"])] = por_tamano.get(tamano(f["pulgadas"]), 0) + 1
        return {"monitores": filas,
                "resumen": {"total": len(filas), "sin_ver": sum(f["sin_ver"] for f in filas),
                            "antiguos": sum(f["antiguo"] for f in filas), "sin_pc": sum(not f["pc"] for f in filas),
                            "por_tamano": por_tamano}}
    finally:
        db.close()


@router.get("/pc/{asset_id}")
def monitores_de_pc(asset_id: str, user: UserOut = Depends(require_modulo(*MODULOS_FICHA))):
    """Para la ficha de una PC: lo ultimo que informo el agente, con link al activo de cada monitor externo."""
    db = SessionLocal()
    try:
        fila = db.get(PcMonitores, asset_id)
        if not fila:
            return {"monitores": [], "actualizado": None}
        try:
            mons = json.loads(fila.detalle or "[]")
        except ValueError:
            mons = []
        claves = [clave_de(m) for m in mons if isinstance(m, dict) and m.get("serie") is not None]
        ids = {d.clave: d.asset_id for d in db.query(MonitorDetalle).filter(MonitorDetalle.clave.in_(claves))} if claves else {}
        for m in mons:
            m["asset_id"] = ids.get(clave_de(m))
        return {"monitores": mons, "actualizado": fila.actualizado}
    finally:
        db.close()


@router.get("/{asset_id}/conexiones")
def conexiones(asset_id: str, user: UserOut = Depends(require_modulo(*MODULOS_FICHA))):
    db = SessionLocal()
    try:
        a = db.get(Asset, asset_id)
        if not a or a.tipo != "Monitor":
            raise HTTPException(404)
        d = db.query(MonitorDetalle).filter(MonitorDetalle.asset_id == asset_id).first()
        cons = (db.query(MonitorConexion).filter(MonitorConexion.monitor_id == asset_id)
                .order_by(MonitorConexion.desde.desc()).all())
        return {"detalle": {"fabricante": d.fabricante, "codigo_producto": d.codigo_producto, "pulgadas": d.pulgadas,
                            "anio": d.anio, "semana": d.semana, "conexion": d.conexion, "visto": d.visto,
                            "pc_id": d.pc_id} if d else None,
                "conexiones": [{"pc_id": c.pc_id, "pc_nombre": c.pc_nombre, "desde": c.desde, "hasta": c.hasta,
                                "conexion": c.conexion} for c in cons]}
    finally:
        db.close()
