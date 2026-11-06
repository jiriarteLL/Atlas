# -*- coding: utf-8 -*-
"""Modulo de telefonia: internos de la central 3CX y los telefonos (Grandstream IP / WiFi) que los usan.

La 3CX es edicion Pro (sin API), asi que los internos entran por la exportacion de usuarios de la consola
(Usuarios -> seleccionar todos -> Exportar), que sube un usuario con permiso "telefonia: editar":
    POST /api/telefonia/importar-3cx           (multipart, archivo CSV)
La IP de cada telefono sale de las concesiones DHCP, por MAC, con la clave de los agentes (X-Sync-Key):
    POST /api/telefonia/relevamiento-dhcp      <- {"concesiones": [{mac, ip, hostname, vence}]}
(lo manda herramientas/telefonia-dhcp/relevar_telefonos_dhcp.ps1).

SEGURIDAD: la exportacion de 3CX trae PIN de casilla de voz (VMPIN), claves de click-to-call y configuracion de
agentes IA. El importador toma SOLO las columnas de COLUMNAS_3CX; el resto del archivo no se lee ni se guarda.
Tampoco se aceptan textos con forma de credencial en los campos que se editan a mano.
"""
import csv
import hmac
import io
import ipaddress
import re
from datetime import datetime
from typing import List, Literal, Optional

from fastapi import APIRouter, Depends, File, Header, HTTPException, Request, UploadFile
from pydantic import BaseModel, ConfigDict, Field, field_validator

import config
from audit import log_action
from auth import UserOut, require_modulo
from database import LineaTelefonica, SessionLocal, TelefonoSinInterno
from impresoras import tiene_credencial
from impresoras_relevamiento import sede_de_ip

router = APIRouter(prefix="/api/telefonia", tags=["telefonia"])

USUARIO_DHCP = "relevamiento-dhcp"
MAX_CSV = 2 * 1024 * 1024
MAX_CONCESIONES = 5000
TIPOS = ("IP", "WiFi", "")
ESTADOS = ("Activa", "Deshabilitada", "Baja")
# Lista blanca: columna de la exportacion de 3CX -> campo de Atlas. Nada fuera de esta lista se lee.
COLUMNAS_3CX = {"Number": "interno", "FirstName": "nombre", "LastName": "apellido", "EmailAddress": "email",
                "DID": "did", "Department": "departamento", "MAC": "mac", "Model": "modelo", "Disabled": "deshabilitado"}
# Departamentos de 3CX que son de la casa central (el resto viene como "Sucursal X")
SEDE_CENTRAL = "CABA"


# ---------------------------------------------------------------- utilidades
def _txt(v, largo=160):
    s = "" if v is None else str(v)
    return re.sub(r"\s+", " ", "".join(ch for ch in s if ch.isprintable())).strip()[:largo]


def normalizar_mac(v):
    m = re.sub(r"[^0-9A-Fa-f]", "", str(v or "")).upper()
    return m if len(m) == 12 else ""


def _ip_valida(ip):
    try:
        return str(ipaddress.IPv4Address(str(ip or "").strip()))
    except ValueError:
        return ""


def sede_de_departamento(dep):
    d = _txt(dep)
    m = re.match(r"^sucursal\s+(.+)$", d, re.I)
    if m:
        return m.group(1).strip().title()   # mismo rotulo que SEDES del frontend ("Cordoba", "Neuquen")
    return SEDE_CENTRAL if d else ""


def calcular_sede(linea):
    return (sede_de_ip(linea.ip) if linea.ip else "") or sede_de_departamento(linea.departamento)


def _clave(x_sync_key):
    esperada = config.SYNC_API_KEY
    if not (esperada and hmac.compare_digest((x_sync_key or "").encode(), esperada.encode())):
        raise HTTPException(status_code=401, detail="Clave de sincronizacion invalida")


def leer_csv_3cx(contenido: bytes):
    """Filas de la exportacion de 3CX con SOLO las columnas de la lista blanca (el resto se descarta al leer)."""
    for cod in ("utf-8-sig", "cp1252"):
        try:
            texto = contenido.decode(cod)
            break
        except UnicodeDecodeError:
            continue
    else:
        raise HTTPException(status_code=400, detail="No se pudo leer el archivo (codificacion desconocida)")
    lector = csv.DictReader(io.StringIO(texto, newline=""))
    if not lector.fieldnames or "Number" not in [c.strip() for c in lector.fieldnames]:
        raise HTTPException(status_code=400, detail="No parece una exportacion de usuarios de 3CX (falta la columna Number)")
    filas = []
    for fila in lector:
        f = {destino: _txt(fila.get(origen)) for origen, destino in COLUMNAS_3CX.items()}
        f["interno"] = re.sub(r"\D", "", f["interno"])[:10]
        if not f["interno"]:
            continue
        f["nombre"] = _txt(f"{f.pop('nombre')} {f.pop('apellido')}")
        f["mac"] = normalizar_mac(f["mac"])
        f["deshabilitado"] = f["deshabilitado"].lower() in ("1", "true", "si", "yes")
        filas.append(f)
    return filas


def _dict(linea):
    return {c: getattr(linea, c) for c in (
        "id", "interno", "nombre", "email", "departamento", "did", "deshabilitado", "mac", "modelo", "tipo",
        "tipo_manual", "ip", "ip_origen", "ip_visto", "hostname", "sede", "sede_manual", "piso", "notas", "estado",
        "en_3cx", "creado", "actualizado")}


def resumir(lineas, sin_interno):
    por_sede = {}
    for x in lineas:
        por_sede[x.sede or "Sin sede"] = por_sede.get(x.sede or "Sin sede", 0) + 1
    return {"internos": len(lineas), "con_telefono": sum(1 for x in lineas if x.mac),
            "sin_ip": sum(1 for x in lineas if x.mac and not x.ip), "sin_interno": len(sin_interno),
            "wifi": sum(1 for x in lineas if x.tipo == "WiFi"), "por_sede": por_sede}


# ---------------------------------------------------------------- lectura
@router.get("")
def listar(user: UserOut = Depends(require_modulo("telefonia"))):
    db = SessionLocal()
    try:
        lineas = db.query(LineaTelefonica).order_by(LineaTelefonica.interno).all()
        sin = db.query(TelefonoSinInterno).order_by(TelefonoSinInterno.ip).all()
        return {"lineas": [_dict(x) for x in lineas],
                "sin_interno": [{"mac": t.mac, "ip": t.ip, "hostname": t.hostname, "visto": t.visto} for t in sin],
                "resumen": resumir(lineas, sin)}
    finally:
        db.close()


@router.get("/{linea_id}")
def ver(linea_id: str, user: UserOut = Depends(require_modulo("telefonia"))):
    db = SessionLocal()
    try:
        x = db.get(LineaTelefonica, linea_id)
        if not x:
            raise HTTPException(404)
        return _dict(x)
    finally:
        db.close()


# ---------------------------------------------------------------- edicion manual
class LineaUpdate(BaseModel):
    model_config = ConfigDict(extra="forbid")
    tipo:   Optional[Literal[TIPOS]] = None
    sede:   Optional[str] = Field(default=None, max_length=60)
    piso:   Optional[str] = Field(default=None, max_length=30)
    notas:  Optional[str] = Field(default=None, max_length=2000)
    estado: Optional[Literal[ESTADOS]] = None
    ip:     Optional[str] = Field(default=None, max_length=45)   # "" = volver a la IP del DHCP

    @field_validator("*", mode="after")
    @classmethod
    def _sin_credenciales(cls, v):
        if isinstance(v, str):
            v = v.strip()
            if tiene_credencial(v):
                raise ValueError("Atlas no guarda credenciales: dejalas en KeePassXC")
        return v


@router.put("/{linea_id}")
def editar(linea_id: str, data: LineaUpdate, request: Request,
           user: UserOut = Depends(require_modulo("telefonia", nivel="editar"))):
    datos = data.model_dump(exclude_unset=True)
    db = SessionLocal()
    try:
        x = db.get(LineaTelefonica, linea_id)
        if not x:
            raise HTTPException(404)
        cambios = {}
        if "ip" in datos:
            if datos["ip"]:
                ip = _ip_valida(datos["ip"])
                if not ip:
                    raise HTTPException(status_code=422, detail="IP invalida")
                if ip != x.ip or x.ip_origen != "manual":
                    cambios["ip"] = (x.ip, ip)
                    x.ip, x.ip_origen = ip, "manual"
            elif x.ip_origen == "manual":
                cambios["ip"] = (x.ip, "")
                x.ip, x.ip_origen = "", ""
        if "tipo" in datos and datos["tipo"] != x.tipo:
            cambios["tipo"] = (x.tipo, datos["tipo"])
            x.tipo, x.tipo_manual = datos["tipo"], True
        if "sede" in datos:
            if datos["sede"]:
                if datos["sede"] != x.sede:
                    cambios["sede"] = (x.sede, datos["sede"])
                x.sede, x.sede_manual = datos["sede"], True
            else:   # vacio = volver a la sede calculada
                x.sede_manual = False
        for campo in ("piso", "notas", "estado"):
            if campo in datos and datos[campo] != getattr(x, campo):
                cambios[campo] = (getattr(x, campo), datos[campo])
                setattr(x, campo, datos[campo])
        if not x.sede_manual:
            x.sede = calcular_sede(x)
        x.actualizado = datetime.utcnow()
        db.commit()
        log_action(user.username, "modificacion", "linea_telefonica", x.interno,
                   {k: [a, b] for k, (a, b) in cambios.items()}, ip=request.client.host if request.client else "")
        return _dict(x)
    finally:
        db.close()


# ---------------------------------------------------------------- importacion de 3CX
def aplicar_importacion(db, filas, ahora=None):
    """Upsert por interno. Los que no vinieron quedan con en_3cx=False (nunca se borra). Devuelve contadores."""
    ahora = ahora or datetime.utcnow()
    res = {"altas": 0, "cambios": 0, "sin_cambios": 0, "fuera_de_3cx": 0}
    existentes = {x.interno: x for x in db.query(LineaTelefonica).all()}
    vistos = set()
    for f in filas:
        if f["interno"] in vistos:
            continue
        vistos.add(f["interno"])
        x = existentes.get(f["interno"])
        nuevo = x is None
        if nuevo:
            x = LineaTelefonica(interno=f["interno"], estado="Activa", creado=ahora, ip="", ip_origen="",
                                sede_manual=False, tipo_manual=False, piso="", notas="", hostname="")
            db.add(x)
        cambio = False
        for campo in ("nombre", "email", "departamento", "did", "mac", "modelo", "deshabilitado"):
            if getattr(x, campo) != f[campo]:
                setattr(x, campo, f[campo])
                cambio = True
        if not x.tipo_manual:
            tipo = "IP" if x.mac else ""
            if x.tipo != tipo:
                x.tipo, cambio = tipo, True
        if x.estado in ("Activa", "Deshabilitada", None):
            estado = "Deshabilitada" if x.deshabilitado else "Activa"
            if x.estado != estado:
                x.estado, cambio = estado, True
        if not x.en_3cx:
            x.en_3cx, cambio = True, True
        if not x.sede_manual and x.sede != calcular_sede(x):
            x.sede, cambio = calcular_sede(x), True
        if cambio:
            x.actualizado = ahora
        res["altas" if nuevo else ("cambios" if cambio else "sin_cambios")] += 1
    for interno, x in existentes.items():
        if interno not in vistos and x.en_3cx:
            x.en_3cx, x.actualizado = False, ahora
            res["fuera_de_3cx"] += 1
    # una MAC que ahora tiene interno deja de figurar como "sin interno"
    macs = {f["mac"] for f in filas if f["mac"]}
    if macs:
        db.query(TelefonoSinInterno).filter(TelefonoSinInterno.mac.in_(macs)).delete(synchronize_session=False)
    return res


@router.post("/importar-3cx")
async def importar_3cx(request: Request, archivo: UploadFile = File(...),
                       user: UserOut = Depends(require_modulo("telefonia", nivel="editar"))):
    contenido = await archivo.read(MAX_CSV + 1)
    if len(contenido) > MAX_CSV:
        raise HTTPException(status_code=413, detail="El archivo supera los 2 MB")
    filas = leer_csv_3cx(contenido)
    if not filas:
        raise HTTPException(status_code=400, detail="El archivo no trae internos")
    db = SessionLocal()
    try:
        res = aplicar_importacion(db, filas)
        db.commit()
    finally:
        db.close()
    log_action(user.username, "importacion", "telefonia", "3cx", {"filas": len(filas), **res},
               ip=request.client.host if request.client else "")
    return {"status": "ok", "filas": len(filas), **res}


# ---------------------------------------------------------------- relevamiento DHCP
class Concesion(BaseModel):
    mac: str = Field(..., max_length=20)
    ip: str = Field(..., max_length=45)
    hostname: str = Field("", max_length=120)
    vence: Optional[str] = Field(default=None, max_length=40)


class RelevamientoDhcp(BaseModel):
    concesiones: List[Concesion] = Field(..., max_length=MAX_CONCESIONES)


def aplicar_dhcp(db, concesiones, ahora=None):
    ahora = ahora or datetime.utcnow()
    res = {"actualizados": 0, "sin_cambios": 0, "sin_interno": 0, "ignoradas": 0}
    por_mac = {}
    for c in concesiones:
        mac, ip = normalizar_mac(c.mac), _ip_valida(c.ip)
        if mac and ip:
            por_mac[mac] = (ip, _txt(c.hostname, 120))
        else:
            res["ignoradas"] += 1
    lineas = {}
    for x in db.query(LineaTelefonica).filter(LineaTelefonica.mac.in_(list(por_mac))).all() if por_mac else []:
        lineas.setdefault(x.mac, []).append(x)
    for mac, (ip, host) in por_mac.items():
        if mac not in lineas:
            t = db.get(TelefonoSinInterno, mac)
            if t is None:
                db.add(TelefonoSinInterno(mac=mac, ip=ip, hostname=host, visto=ahora))
            else:
                t.ip, t.hostname, t.visto = ip, host or t.hostname, ahora
            res["sin_interno"] += 1
            continue
        for x in lineas[mac]:
            x.ip_visto = ahora
            if host:
                x.hostname = host
            if x.ip_origen == "manual":   # la IP cargada a mano no se pisa
                res["sin_cambios"] += 1
                continue
            if x.ip != ip:
                x.ip, x.ip_origen = ip, "dhcp"
                if not x.sede_manual:
                    x.sede = calcular_sede(x)
                x.actualizado = ahora
                res["actualizados"] += 1
            else:
                x.ip_origen = "dhcp"
                res["sin_cambios"] += 1
    return res


@router.post("/relevamiento-dhcp")
def relevamiento_dhcp(data: RelevamientoDhcp, x_sync_key: str = Header(default="")):
    _clave(x_sync_key)
    db = SessionLocal()
    try:
        res = aplicar_dhcp(db, data.concesiones)
        db.commit()
    finally:
        db.close()
    log_action(USUARIO_DHCP, "relevamiento", "telefonia", "dhcp", res)
    return {"status": "ok", **res}
