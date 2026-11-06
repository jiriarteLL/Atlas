# -*- coding: utf-8 -*-
"""Relevamiento SNMP de impresoras de red (paso 2 del modulo de impresoras).

Lo alimenta herramientas/snmp-impresoras/enviar_a_atlas.py, que corre en un servidor que llega a todas las sedes,
con la misma clave que los agentes (header X-Sync-Key):
    GET  /api/impresoras/relevamiento/ips   -> IP de las impresoras de red que Atlas ya conoce
    POST /api/impresoras/relevamiento       <- {"lecturas": [...]} (resultado de relevar_impresoras.relevar)

Las impresoras de red entran "limpias desde la red": se identifican por numero de serie (o MAC si no hay serie)
y todo dato que se guarda lo informo el equipo por SNMP. Los datos administrativos (piso, tenencia, proveedor,
nro. de inventario, nombre visible) se cargan a mano en Atlas y el relevamiento no los pisa. Las personales por
USB nunca se tocan.
"""
import hmac
import ipaddress
import re
import uuid
from datetime import datetime
from typing import List, Optional

from fastapi import APIRouter, Header, HTTPException
from pydantic import BaseModel, Field
from sqlalchemy import func

import config
from database import Asset, Historial, ImpresoraConsumible, ImpresoraDetalle, ImpresoraLectura, SessionLocal

router = APIRouter(prefix="/api/impresoras/relevamiento", tags=["impresoras"])
USUARIO = "relevamiento-snmp"
MAX_LECTURAS = 500

_MARCAS = ("HP", "Xerox", "Ricoh", "Lexmark", "Kyocera", "Brother", "Canon", "Epson", "Samsung", "OKI",
           "Konica", "Sharp", "Toshiba")


class Consumible(BaseModel):
    indice: int
    descripcion: str = Field("", max_length=200)
    maximo: Optional[int] = None
    nivel: Optional[int] = None
    porcentaje: Optional[int] = None
    nota: str = Field("", max_length=40)


class Lectura(BaseModel):
    ip: str = Field(..., max_length=45)
    responde: bool = False
    nombre_red: str = Field("", max_length=120)
    sys_descr: str = Field("", max_length=400)
    modelo: str = Field("", max_length=160)
    serie: str = Field("", max_length=80)
    contador: Optional[int] = None
    estado: str = Field("", max_length=40)
    mac: str = Field("", max_length=17)
    consumibles: List[Consumible] = []
    error: str = Field("", max_length=200)


class Relevamiento(BaseModel):
    lecturas: List[Lectura] = Field(..., max_length=MAX_LECTURAS)


def _clave(x_sync_key):
    esperada = config.SYNC_API_KEY
    if not (esperada and hmac.compare_digest((x_sync_key or "").encode(), esperada.encode())):
        raise HTTPException(status_code=401, detail="Clave de sincronizacion invalida")


def _ip_valida(ip):
    try:
        return str(ipaddress.IPv4Address(ip.strip()))
    except (ValueError, AttributeError):
        return ""


def sede_de_ip(ip):
    try:
        dir_ = ipaddress.IPv4Address(ip)
    except ValueError:
        return ""
    for red, sede in config.SEDES_POR_RED:   # configurable por entorno (SEDES_POR_RED)
        try:
            if dir_ in ipaddress.IPv4Network(red.strip(), strict=False):
                return sede.strip()
        except ValueError:
            continue
    return ""


def marca_de_modelo(modelo):
    m = (modelo or "").strip()
    return next((x for x in _MARCAS if m.upper().startswith(x.upper())), m.split(" ")[0] if m else "")


def _limpio(s):
    return re.sub(r"\s+", " ", s or "").strip()


@router.get("/ips")
def ips_a_relevar(x_sync_key: str = Header(default="")):
    _clave(x_sync_key)
    db = SessionLocal()
    try:
        filas = (db.query(Asset.ip).join(ImpresoraDetalle, ImpresoraDetalle.asset_id == Asset.id)
                 .filter(Asset.tipo == "Impresora", ImpresoraDetalle.conexion == "red").all())
        return {"ips": sorted({ip for ip in (_ip_valida(f.ip or "") for f in filas) if ip})}
    finally:
        db.close()


def _buscar(db, lec):
    if lec.serie:
        a = db.query(Asset).filter(func.upper(Asset.serial) == lec.serie.upper()).first()
        if a:
            return a
    if lec.mac:
        d = db.query(ImpresoraDetalle).filter(func.upper(ImpresoraDetalle.mac) == lec.mac.upper()).first()
        if d:
            return db.get(Asset, d.asset_id)
    return None


def _guardar_consumibles(db, asset_id, consumibles, ahora):
    db.query(ImpresoraConsumible).filter(ImpresoraConsumible.asset_id == asset_id).delete(synchronize_session=False)
    for c in consumibles:
        desc = _limpio(c.descripcion)
        # Solo los cartuchos son "toner"/"color"; tambores, reveladores, fusor, kits y la unidad de recogida
        # de toner usado son "otro" (no son lo que se cambia seguido ni lo que dispara el aviso de toner bajo).
        if re.search(r"(recogida|residual|waste|collect)", desc, re.I) or \
                not re.search(r"(cartucho|cartridge|t[oó]ner)", desc, re.I):
            tipo = "otro"
        else:
            tipo = "color" if re.search(r"\b(cian|cyan|magenta|amarill|yellow)", desc, re.I) else "toner"
        db.add(ImpresoraConsumible(asset_id=asset_id, indice=c.indice, descripcion=desc, tipo=tipo,
                                   nivel=c.nivel, maximo=c.maximo, porcentaje=c.porcentaje, actualizado=ahora))


@router.post("")
def recibir_relevamiento(data: Relevamiento, x_sync_key: str = Header(default="")):
    _clave(x_sync_key)
    ahora = datetime.utcnow()
    res = {"creadas": 0, "actualizadas": 0, "sin_respuesta": 0, "ignoradas": 0}
    db = SessionLocal()
    try:
        for lec in data.lecturas:
            ip = _ip_valida(lec.ip)
            if not ip:
                res["ignoradas"] += 1
                continue
            if not lec.responde:
                # Solo se registra si ya es una impresora de red conocida con esa IP.
                a = (db.query(Asset).join(ImpresoraDetalle, ImpresoraDetalle.asset_id == Asset.id)
                     .filter(Asset.tipo == "Impresora", Asset.ip == ip, ImpresoraDetalle.conexion == "red").first())
                if a:
                    db.add(ImpresoraLectura(asset_id=a.id, fecha=ahora, contador_total=None,
                                            estado="sin respuesta", error=_limpio(lec.error)[:200]))
                    res["sin_respuesta"] += 1
                else:
                    res["ignoradas"] += 1
                continue
            if not (lec.serie or lec.mac):
                res["ignoradas"] += 1   # sin serie ni MAC no hay forma segura de identificarla
                continue
            modelo = _limpio(lec.modelo)
            a = _buscar(db, lec)
            if a is not None and a.tipo != "Impresora":
                res["ignoradas"] += 1   # la serie es de otro tipo de activo: no se mezcla
                continue
            d = db.query(ImpresoraDetalle).filter(ImpresoraDetalle.asset_id == a.id).first() if a else None
            if d is not None and d.conexion == "usb":
                res["ignoradas"] += 1   # personal por USB: el relevamiento no la toca
                continue
            if a is None:
                a = Asset(id=("A" + str(uuid.uuid4())[:6]).upper(), tipo="Impresora", estado="Activo",
                          nombre=_limpio(lec.nombre_red) or ip, marca=marca_de_modelo(modelo), modelo=modelo,
                          serial=_limpio(lec.serie), ip=ip, ubicacion=sede_de_ip(ip), updated=ahora)
                db.add(a)
                db.flush()
                color = any(re.search(r"\b(cian|cyan|magenta)", c.descripcion, re.I) for c in lec.consumibles)
                escaner = bool(re.search(r"\b(MFP|WorkCentre|multifun)", f"{modelo} {lec.sys_descr}", re.I))
                d = ImpresoraDetalle(asset_id=a.id, conexion="red", uso="compartida", mac=lec.mac.upper(),
                                     hostname=_limpio(lec.nombre_red), color=color, escaner=escaner, actualizado=ahora)
                db.add(d)
                db.add(Historial(asset_id=a.id, usuario=USUARIO, campo="alta", valor_ant="",
                                 valor_new=f"{a.nombre} ({modelo}, serie {a.serial or '-'})", accion="sincronizacion"))
                res["creadas"] += 1
            else:
                if d is None:
                    d = ImpresoraDetalle(asset_id=a.id, conexion="red", uso="compartida")
                    db.add(d)
                cambios = {}
                for obj, campo, valor in ((a, "ip", ip), (a, "modelo", modelo), (a, "serial", _limpio(lec.serie)),
                                          (d, "mac", lec.mac.upper()), (d, "hostname", _limpio(lec.nombre_red))):
                    if valor and str(getattr(obj, campo) or "") != valor:
                        cambios[campo] = (getattr(obj, campo) or "", valor)
                        setattr(obj, campo, valor)
                if cambios.get("modelo") and not a.marca:
                    a.marca = marca_de_modelo(modelo)
                for campo, (antes, despues) in cambios.items():
                    db.add(Historial(asset_id=a.id, usuario=USUARIO, campo=campo, valor_ant=str(antes),
                                     valor_new=str(despues), accion="sincronizacion"))
                d.actualizado = ahora
                res["actualizadas"] += 1
            a.updated = ahora
            db.add(ImpresoraLectura(asset_id=a.id, fecha=ahora, contador_total=lec.contador,
                                    estado=_limpio(lec.estado) or "en linea", error=""))
            _guardar_consumibles(db, a.id, lec.consumibles, ahora)
        db.commit()
    finally:
        db.close()
    return {"status": "ok", **res}
