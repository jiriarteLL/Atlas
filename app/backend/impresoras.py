# -*- coding: utf-8 -*-
"""Modulo de impresoras.

Una impresora es un Asset tipo "Impresora" (historial, adjuntos, QR y dashboard se reusan) con su detalle propio en
impresora_detalle. El contador (impresora_lectura) y los consumibles (impresora_consumible) los llena el relevamiento
SNMP (paso 2); aca solo se leen.

Las credenciales de administracion de las impresoras NO se guardan en Atlas (estan en KeePassXC): credencial_ref es
una referencia de texto. Cualquier texto con forma de credencial ("User: x", "Pass: y", "clave= z") se rechaza al
editar y se descarta al importar (quitar_credenciales).
"""
import re
import uuid
from datetime import datetime
from typing import Literal, Optional

from fastapi import APIRouter, Depends, HTTPException, Request
from pydantic import BaseModel, ConfigDict, Field, field_validator
from sqlalchemy import func

import config
from audit import log_action
from auth import UserOut, require_escritura, require_lectura
from database import Asset, Historial, ImpresoraConsumible, ImpresoraDetalle, ImpresoraLectura, SessionLocal

router = APIRouter(prefix="/api/impresoras", tags=["impresoras"])

CONEXIONES = ("red", "usb")
USOS = ("compartida", "personal")
TENENCIAS = ("propia", "alquilada", "tercerizada", "")
ESTADOS = ("Activo", "Mantenimiento", "Dado de baja", "Libre", "Stock", "Robado")

# "User: admin", "Pass:1234", "password = x", "clave: y", "contraseña: z" (el valor es lo que sigue hasta un espacio)
_CREDENCIAL = re.compile(r"\b(user(name)?|usuario|pass(word)?|pwd|clave|contrase(n|ñ)a)\s*[:=]\s*\S+", re.IGNORECASE)

CAMPOS_ASSET = ("nombre", "marca", "modelo", "serial", "estado", "usuario", "ubicacion", "ip", "comentarios")
CAMPOS_DETALLE = ("conexion", "uso", "piso", "mac", "hostname", "nombre_cola", "color", "duplex", "escaner",
                  "toner_modelo", "tenencia", "proveedor", "nro_inventario", "credencial_ref", "notas")


def tiene_credencial(texto):
    return bool(texto) and bool(_CREDENCIAL.search(str(texto)))


def quitar_credenciales(texto):
    """Saca de un texto libre cualquier "User:...", "Pass:...", etc. y ordena los separadores que quedan."""
    if not texto:
        return ""
    t = _CREDENCIAL.sub("", str(texto))
    t = re.sub(r"(\s+-)+\s+", " - ", t)          # "Toner X - - Doble" (donde estaba la credencial) -> un separador
    partes = [p.strip(" .,;-") for p in re.split(r"\s+-\s+|\s*;\s*", t)]
    return " - ".join(p for p in partes if p)


# ---------------------------------------------------------------- esquemas
class _Base(BaseModel):
    # extra="forbid": un campo desconocido (p. ej. "password") es un 422, nunca se guarda en silencio
    model_config = ConfigDict(extra="forbid")

    @field_validator("*", mode="after")
    @classmethod
    def _sin_credenciales(cls, v):
        if isinstance(v, str):
            v = v.strip()
            if tiene_credencial(v):
                raise ValueError("Atlas no guarda credenciales: dejalas en KeePassXC y usa credencial_ref "
                                 "solo como referencia")
        return v


class ImpresoraUpdate(_Base):
    nombre:         Optional[str] = None
    marca:          Optional[str] = None
    modelo:         Optional[str] = None
    serial:         Optional[str] = None
    estado:         Optional[Literal[ESTADOS]] = None
    usuario:        Optional[str] = None
    ubicacion:      Optional[str] = None
    ip:             Optional[str] = None
    comentarios:    Optional[str] = None
    conexion:       Optional[Literal[CONEXIONES]] = None
    uso:            Optional[Literal[USOS]] = None
    piso:           Optional[str] = None
    mac:            Optional[str] = None
    hostname:       Optional[str] = None
    nombre_cola:    Optional[str] = None
    color:          Optional[bool] = None
    duplex:         Optional[bool] = None
    escaner:        Optional[bool] = None
    toner_modelo:   Optional[str] = None
    tenencia:       Optional[Literal[TENENCIAS]] = None
    proveedor:      Optional[str] = None
    nro_inventario: Optional[str] = None
    credencial_ref: Optional[str] = Field(default=None, max_length=120)
    notas:          Optional[str] = None


class ImpresoraCreate(ImpresoraUpdate):
    nombre:   str = Field(..., min_length=2, max_length=120)
    marca:    str = Field(..., min_length=1)
    modelo:   str = Field(..., min_length=1)
    conexion: Literal[CONEXIONES] = "red"
    uso:      Literal[USOS] = "compartida"
    estado:   Literal[ESTADOS] = "Activo"


# ---------------------------------------------------------------- armado de respuestas
def _detalle_dict(d):
    if not d:
        return {c: (False if c in ("color", "duplex", "escaner") else "") for c in CAMPOS_DETALLE}
    return {c: getattr(d, c) for c in CAMPOS_DETALLE} | {"actualizado": d.actualizado}


def _asset_dict(a):
    return {"id": a.id, "nombre": a.nombre, "tipo": a.tipo, "marca": a.marca, "modelo": a.modelo,
            "serial": a.serial, "estado": a.estado, "usuario": a.usuario, "ubicacion": a.ubicacion,
            "ip": a.ip, "comentarios": a.comentarios, "garantia": a.garantia, "updated": a.updated}


def _armar(db, assets):
    ids = [a.id for a in assets]
    detalles = {d.asset_id: d for d in db.query(ImpresoraDetalle).filter(ImpresoraDetalle.asset_id.in_(ids))} if ids else {}
    ultimas = {}
    if ids:
        sub = (db.query(ImpresoraLectura.asset_id, func.max(ImpresoraLectura.fecha).label("f"))
               .filter(ImpresoraLectura.asset_id.in_(ids)).group_by(ImpresoraLectura.asset_id).subquery())
        for le in db.query(ImpresoraLectura).join(sub, (ImpresoraLectura.asset_id == sub.c.asset_id)
                                                     & (ImpresoraLectura.fecha == sub.c.f)):
            ultimas[le.asset_id] = {"fecha": le.fecha, "contador_total": le.contador_total,
                                    "estado": le.estado, "error": le.error}
    consumibles = {}
    if ids:
        for c in db.query(ImpresoraConsumible).filter(ImpresoraConsumible.asset_id.in_(ids)).order_by(
                ImpresoraConsumible.asset_id, ImpresoraConsumible.indice):
            consumibles.setdefault(c.asset_id, []).append(
                {"indice": c.indice, "descripcion": c.descripcion, "tipo": c.tipo, "nivel": c.nivel,
                 "maximo": c.maximo, "porcentaje": c.porcentaje, "actualizado": c.actualizado})
    return [_asset_dict(a) | {"detalle": _detalle_dict(detalles.get(a.id)), "lectura": ultimas.get(a.id),
                              "consumibles": consumibles.get(a.id, [])} for a in assets]


def _norm(s):
    return re.sub(r"\s+", " ", str(s or "")).strip().lower()


def pcs_con_impresora(db, nombres):
    """Activos (no impresoras) que tienen instalada alguna de estas colas. Lo informan los agentes en el campo
    impresoras ("A|B|C"); se compara por nombre exacto, por "\\\\servidor\\cola" y por "Cola (Copia 1)"."""
    buscados = {_norm(n) for n in nombres if n and len(str(n).strip()) >= 4}
    if not buscados:
        return []
    salida = []
    for a in (db.query(Asset.id, Asset.nombre, Asset.usuario, Asset.ubicacion, Asset.impresoras)
              .filter(Asset.tipo != "Impresora", Asset.impresoras.isnot(None), Asset.impresoras != "")):
        for cola in (a.impresoras or "").split("|"):
            c = _norm(cola)
            base = c.rsplit("\\", 1)[-1]
            base = re.sub(r"\s*\((copia|copy|copiar)[^)]*\)$", "", base)
            if c in buscados or base in buscados:
                salida.append({"id": a.id, "nombre": a.nombre, "usuario": a.usuario, "ubicacion": a.ubicacion,
                               "cola": cola.strip()})
                break
    return sorted(salida, key=lambda x: (x["ubicacion"] or "", x["nombre"] or ""))


def _ip(request):
    return request.client.host if (request is not None and request.client) else ""


def _historial(db, asset_id, usuario, cambios):
    for campo, (antes, despues) in cambios.items():
        db.add(Historial(asset_id=asset_id, usuario=usuario, campo=campo,
                         valor_ant="" if antes is None else str(antes),
                         valor_new="" if despues is None else str(despues), accion="edicion"))


# ---------------------------------------------------------------- endpoints
@router.get("")
def listar_impresoras(user: UserOut = Depends(require_lectura)):
    db = SessionLocal()
    try:
        assets = db.query(Asset).filter(Asset.tipo == "Impresora").order_by(Asset.ubicacion, Asset.nombre).all()
        return _armar(db, assets)
    finally:
        db.close()


@router.get("/alertas")
def alertas_toner(user: UserOut = Depends(require_lectura)):
    """Cartuchos (toner/color) por debajo del umbral (TONER_ALERTA_PCT, 10% por defecto): el aviso emergente."""
    umbral = config.TONER_ALERTA_PCT
    db = SessionLocal()
    try:
        filas = (db.query(Asset, ImpresoraConsumible, ImpresoraDetalle)
                 .join(ImpresoraConsumible, ImpresoraConsumible.asset_id == Asset.id)
                 .outerjoin(ImpresoraDetalle, ImpresoraDetalle.asset_id == Asset.id)
                 .filter(Asset.tipo == "Impresora", Asset.estado != "Dado de baja",
                         ImpresoraConsumible.tipo.in_(("toner", "color")),
                         ImpresoraConsumible.porcentaje.isnot(None), ImpresoraConsumible.porcentaje >= 0,
                         ImpresoraConsumible.porcentaje < umbral)
                 .order_by(ImpresoraConsumible.porcentaje, Asset.nombre).all())
        return {"umbral": umbral, "alertas": [
            {"id": a.id, "nombre": a.nombre, "ubicacion": a.ubicacion, "piso": d.piso if d else "",
             "consumible": c.descripcion, "porcentaje": c.porcentaje, "actualizado": c.actualizado}
            for a, c, d in filas]}
    finally:
        db.close()


@router.get("/{asset_id}")
def ver_impresora(asset_id: str, user: UserOut = Depends(require_lectura)):
    db = SessionLocal()
    try:
        a = db.query(Asset).filter(Asset.id == asset_id, Asset.tipo == "Impresora").first()
        if not a:
            raise HTTPException(404, detail="Impresora no encontrada.")
        r = _armar(db, [a])[0]
        r["pcs"] = pcs_con_impresora(db, [r["detalle"]["nombre_cola"], a.nombre])
        return r
    finally:
        db.close()


def _serial_libre(db, serial, excepto=None):
    if not serial:
        return
    q = db.query(Asset).filter(func.upper(Asset.serial) == serial.upper())
    if excepto:
        q = q.filter(Asset.id != excepto)
    if q.first():
        raise HTTPException(409, detail="Ya existe un activo con ese numero de serie.")


@router.post("")
def crear_impresora(data: ImpresoraCreate, request: Request, user: UserOut = Depends(require_escritura)):
    datos = data.model_dump()
    db = SessionLocal()
    try:
        _serial_libre(db, datos.get("serial"))
        a = Asset(id=("A" + str(uuid.uuid4())[:6]).upper(), tipo="Impresora", updated=datetime.utcnow(),
                  **{c: (datos.get(c) or ("Activo" if c == "estado" else "")) for c in CAMPOS_ASSET})
        db.add(a)
        db.flush()
        db.add(ImpresoraDetalle(asset_id=a.id, actualizado=datetime.utcnow(),
                                **{c: datos.get(c) if datos.get(c) is not None else
                                   (False if c in ("color", "duplex", "escaner") else "") for c in CAMPOS_DETALLE}))
        db.add(Historial(asset_id=a.id, usuario=user.username, campo="alta", valor_ant="",
                         valor_new=a.nombre, accion="edicion"))
        db.commit()
        aid = a.id
    finally:
        db.close()
    log_action(user.username, "alta", "impresora", aid, {"nombre": data.nombre, "modelo": data.modelo}, ip=_ip(request))
    return ver_impresora(aid, user)


@router.put("/{asset_id}")
def editar_impresora(asset_id: str, data: ImpresoraUpdate, request: Request,
                     user: UserOut = Depends(require_escritura)):
    datos = data.model_dump(exclude_unset=True)
    db = SessionLocal()
    try:
        a = db.query(Asset).filter(Asset.id == asset_id, Asset.tipo == "Impresora").first()
        if not a:
            raise HTTPException(404, detail="Impresora no encontrada.")
        if "serial" in datos:
            _serial_libre(db, datos["serial"], excepto=asset_id)
        d = db.query(ImpresoraDetalle).filter(ImpresoraDetalle.asset_id == asset_id).first()
        if not d:
            d = ImpresoraDetalle(asset_id=asset_id, conexion="red", uso="compartida")
            db.add(d)
        cambios = {}
        for campo, valor in datos.items():
            obj = a if campo in CAMPOS_ASSET else d
            if valor is None and campo in CAMPOS_ASSET:
                continue
            antes = getattr(obj, campo, None)
            if str(antes if antes is not None else "") != str(valor if valor is not None else ""):
                cambios[campo] = (antes, valor)
                setattr(obj, campo, valor)
        if cambios:
            a.updated = datetime.utcnow()
            d.actualizado = datetime.utcnow()
            _historial(db, asset_id, user.username, cambios)
        db.commit()
    finally:
        db.close()
    log_action(user.username, "modificacion", "impresora", asset_id,
               {k: {"antes": v[0], "despues": v[1]} for k, v in cambios.items()} or None, ip=_ip(request))
    return ver_impresora(asset_id, user)


def borrar_datos_impresora(db, asset_id):
    """Para el borrado de un activo: en SQLite las FK no se aplican solas (en PostgreSQL ya lo hace el CASCADE)."""
    for modelo in (ImpresoraConsumible, ImpresoraLectura, ImpresoraDetalle):
        db.query(modelo).filter(modelo.asset_id == asset_id).delete(synchronize_session=False)
