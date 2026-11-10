# -*- coding: utf-8 -*-
"""Actas de entrega / devolucion / prestamo de equipos (fase F).

Flujo: se crea en borrador (numero correlativo por anio ACT-AAAA-NNNN, asignado al crearla) con la persona, los
equipos y sus accesorios -> se firma en pantalla (receptor y soporte, PNG del canvas) o se imprime, se firma en
papel y se sube el escaneo -> al confirmarla queda "firmada" y se aplican los movimientos a cada equipo
(entrega = asignacion, devolucion, prestamo) con Historial. Una firmada se puede anular (con motivo); la anulacion
no revierte los movimientos: si hace falta, se registra el movimiento contrario.
"""
import json
import os
import re
import uuid
from datetime import date, datetime
from typing import List, Literal, Optional

from fastapi import APIRouter, Depends, File, Form, HTTPException, Request, UploadFile
from pydantic import BaseModel, ConfigDict, Field, field_validator
from sqlalchemy import Column, Date, DateTime, Integer, String, Text
from sqlalchemy.exc import IntegrityError

import config
from audit import log_action
from auth import UserOut, require_modulo
from ciclo_activos import AssetAdmin, _texto_limpio, aplicar_movimiento
from database import Adjunto, Asset, Base, Historial, SessionLocal, _uuid

router = APIRouter(prefix="/api/actas", tags=["actas"])

TIPOS_ACTA = ("entrega", "devolucion", "prestamo")
MOVIMIENTO_DE_ACTA = {"entrega": "asignacion", "devolucion": "devolucion", "prestamo": "prestamo"}
MAX_FIRMA = 400_000          # bytes del data URL de cada firma
MAX_ESCANEO_MB = 10
TIPOS_ESCANEO = (".pdf", ".jpg", ".jpeg", ".png")


class Acta(Base):
    __tablename__ = "acta"
    id                 = Column(String, primary_key=True, default=_uuid)
    numero             = Column(String, nullable=False, unique=True)      # ACT-2026-0001
    anio               = Column(Integer, nullable=False)
    secuencia          = Column(Integer, nullable=False)
    tipo               = Column(String, default="entrega")
    estado             = Column(String, default="borrador")               # borrador | firmada | anulada
    persona            = Column(String, default="")
    legajo             = Column(String, default="")
    area               = Column(String, default="")
    sede               = Column(String, default="")
    fecha              = Column(Date, nullable=True)
    devolucion_prevista = Column(Date, nullable=True)                     # prestamos
    observaciones      = Column(Text, default="")
    clausula           = Column(Text, default="")
    firma_receptor     = Column(Text, default="")                         # data:image/png;base64,...
    firma_soporte      = Column(Text, default="")
    firmo_soporte      = Column(String, default="")
    escaneo_adjunto_id = Column(String, default="")
    creado_por         = Column(String, default="")
    creado             = Column(DateTime, default=datetime.utcnow)
    firmada_el         = Column(DateTime, nullable=True)
    anulada_el         = Column(DateTime, nullable=True)
    motivo_anulacion   = Column(Text, default="")


class ActaItem(Base):
    __tablename__ = "acta_item"
    id          = Column(String, primary_key=True, default=_uuid)
    acta_id     = Column(String, nullable=False, index=True)
    asset_id    = Column(String, nullable=False, index=True)
    orden       = Column(Integer, default=0)
    descripcion = Column(String, default="")     # tipo + marca + modelo al momento del acta
    serial      = Column(String, default="")
    nro_inventario = Column(String, default="")
    accesorios  = Column(Text, default="[]")     # JSON: ["Cargador", "Mouse", ...]


# ---------------------------------------------------------------- esquemas
class ItemIn(BaseModel):
    model_config = ConfigDict(extra="forbid")
    asset_id:   str = Field(..., min_length=1, max_length=40)
    accesorios: List[str] = Field(default_factory=list, max_length=20)

    @field_validator("accesorios", mode="after")
    @classmethod
    def _acc(cls, v):
        return [_texto_limpio(x)[:60] for x in v if isinstance(x, str) and x.strip()]


class ActaIn(BaseModel):
    model_config = ConfigDict(extra="forbid")
    tipo:          Literal[TIPOS_ACTA] = "entrega"
    persona:       str = Field(..., min_length=2, max_length=120)
    legajo:        Optional[str] = Field(default="", max_length=40)
    area:          Optional[str] = Field(default="", max_length=120)
    sede:          Optional[str] = Field(default="", max_length=60)
    fecha:         Optional[date] = None
    devolucion_prevista: Optional[date] = None
    observaciones: Optional[str] = Field(default="", max_length=3000)
    clausula:      Optional[str] = Field(default=None, max_length=5000)
    items:         List[ItemIn] = Field(..., min_length=1, max_length=30)

    @field_validator("persona", "legajo", "area", "sede", "observaciones", "clausula", mode="after")
    @classmethod
    def _limpio(cls, v):
        return _texto_limpio(v)


class FirmaIn(BaseModel):
    model_config = ConfigDict(extra="forbid")
    firma_receptor: str = Field(..., max_length=MAX_FIRMA)
    firma_soporte:  str = Field(..., max_length=MAX_FIRMA)

    @field_validator("firma_receptor", "firma_soporte", mode="after")
    @classmethod
    def _png(cls, v):
        if not re.fullmatch(r"data:image/png;base64,[A-Za-z0-9+/=]+", v or ""):
            raise ValueError("la firma tiene que ser una imagen PNG")
        return v


class AnularIn(BaseModel):
    model_config = ConfigDict(extra="forbid")
    motivo: str = Field(..., min_length=3, max_length=1000)


# ---------------------------------------------------------------- helpers
def siguiente_numero(db, anio):
    ult = (db.query(Acta.secuencia).filter(Acta.anio == anio).order_by(Acta.secuencia.desc()).first())
    sec = (ult[0] if ult else 0) + 1
    return sec, "ACT-%d-%04d" % (anio, sec)


def _items(db, acta_id):
    return db.query(ActaItem).filter(ActaItem.acta_id == acta_id).order_by(ActaItem.orden).all()


def _dict(acta, items, con_firmas=False):
    d = {k: getattr(acta, k) for k in ("id", "numero", "tipo", "estado", "persona", "legajo", "area", "sede", "fecha",
                                       "devolucion_prevista", "observaciones", "clausula", "firmo_soporte",
                                       "escaneo_adjunto_id", "creado_por", "creado", "firmada_el", "anulada_el",
                                       "motivo_anulacion")}
    d["firmada_en_pantalla"] = bool(acta.firma_receptor)
    if con_firmas:
        d["firma_receptor"], d["firma_soporte"] = acta.firma_receptor or "", acta.firma_soporte or ""
    d["items"] = [{"id": i.id, "asset_id": i.asset_id, "descripcion": i.descripcion, "serial": i.serial,
                   "nro_inventario": i.nro_inventario, "accesorios": json.loads(i.accesorios or "[]")} for i in items]
    return d


def _guardar_items(db, acta, items):
    vistos = set()
    for n, it in enumerate(items):
        if it.asset_id in vistos:
            continue
        vistos.add(it.asset_id)
        a = db.get(Asset, it.asset_id)
        if not a:
            raise HTTPException(404, "No existe el activo %s" % it.asset_id)
        if a.estado == "Dado de baja":
            raise HTTPException(409, "%s está dado de baja" % (a.nombre or a.serial))
        adm = db.get(AssetAdmin, a.id)
        db.add(ActaItem(acta_id=acta.id, asset_id=a.id, orden=n,
                        descripcion=" ".join(x for x in (a.tipo, a.marca, a.modelo) if x).strip(),
                        serial=a.serial or "", nro_inventario=(adm.nro_inventario if adm else "") or "",
                        accesorios=json.dumps(it.accesorios, ensure_ascii=False)))


def _confirmar(db, acta, hecho_por):
    """Pasa a firmada y aplica los movimientos de cada equipo."""
    tipo_mov = MOVIMIENTO_DE_ACTA[acta.tipo]
    for it in _items(db, acta.id):
        a = db.get(Asset, it.asset_id)
        if not a:
            continue
        aplicar_movimiento(db, a, tipo_mov, hecho_por, a_usuario=acta.persona, sede=acta.sede or None,
                           motivo="Acta " + acta.numero, acta_id=acta.id)
    acta.estado = "firmada"
    acta.firmada_el = datetime.utcnow()


def _ip(request):
    return request.client.host if request.client else ""


# ---------------------------------------------------------------- endpoints
@router.get("/config")
def ver_config(user: UserOut = Depends(require_modulo("activos"))):
    return {"empresa": config.ACTA_EMPRESA, "clausula": config.ACTA_CLAUSULA, "accesorios": config.ACTA_ACCESORIOS}


@router.get("")
def listar(user: UserOut = Depends(require_modulo("activos"))):
    db = SessionLocal()
    try:
        actas = db.query(Acta).order_by(Acta.anio.desc(), Acta.secuencia.desc()).limit(1000).all()
        items = {}
        for i in db.query(ActaItem).filter(ActaItem.acta_id.in_([a.id for a in actas])).order_by(ActaItem.orden).all():
            items.setdefault(i.acta_id, []).append(i)
        return [_dict(a, items.get(a.id, [])) for a in actas]
    finally:
        db.close()


@router.get("/de-activo/{asset_id}")
def actas_de_activo(asset_id: str, user: UserOut = Depends(require_modulo("activos"))):
    db = SessionLocal()
    try:
        ids = [i.acta_id for i in db.query(ActaItem).filter(ActaItem.asset_id == asset_id).all()]
        actas = db.query(Acta).filter(Acta.id.in_(ids)).order_by(Acta.creado.desc()).all() if ids else []
        return [{"id": a.id, "numero": a.numero, "tipo": a.tipo, "estado": a.estado, "persona": a.persona,
                 "fecha": a.fecha} for a in actas]
    finally:
        db.close()


@router.get("/{acta_id}")
def ver(acta_id: str, user: UserOut = Depends(require_modulo("activos"))):
    db = SessionLocal()
    try:
        a = db.get(Acta, acta_id)
        if not a:
            raise HTTPException(404)
        return _dict(a, _items(db, a.id), con_firmas=True)
    finally:
        db.close()


@router.post("")
def crear(data: ActaIn, request: Request, user: UserOut = Depends(require_modulo("activos", nivel="editar"))):
    anio = (data.fecha or date.today()).year
    for _ in range(5):          # dos altas a la vez: la segunda choca con el UNIQUE del numero y reintenta
        db = SessionLocal()
        try:
            sec, numero = siguiente_numero(db, anio)
            acta = Acta(id=str(uuid.uuid4()), numero=numero, anio=anio, secuencia=sec, tipo=data.tipo,
                        estado="borrador", persona=data.persona, legajo=data.legajo or "", area=data.area or "",
                        sede=data.sede or "", fecha=data.fecha or date.today(),
                        devolucion_prevista=data.devolucion_prevista if data.tipo == "prestamo" else None,
                        observaciones=data.observaciones or "",
                        clausula=data.clausula if data.clausula is not None else config.ACTA_CLAUSULA,
                        creado_por=user.username, creado=datetime.utcnow())
            db.add(acta)
            db.flush()
            _guardar_items(db, acta, data.items)
            db.commit()
            log_action(user.username, "alta", "acta", acta.id, {"numero": numero, "tipo": data.tipo,
                                                               "persona": data.persona}, ip=_ip(request))
            return _dict(acta, _items(db, acta.id))
        except IntegrityError:
            db.rollback()
        finally:
            db.close()
    raise HTTPException(409, "No se pudo numerar el acta, probá de nuevo")


@router.put("/{acta_id}")
def editar(acta_id: str, data: ActaIn, request: Request, user: UserOut = Depends(require_modulo("activos", nivel="editar"))):
    db = SessionLocal()
    try:
        a = db.get(Acta, acta_id)
        if not a:
            raise HTTPException(404)
        if a.estado != "borrador":
            raise HTTPException(409, "Solo se edita un acta en borrador")
        for k in ("tipo", "persona", "legajo", "area", "sede", "observaciones"):
            setattr(a, k, getattr(data, k) or "")
        a.fecha = data.fecha or a.fecha
        a.devolucion_prevista = data.devolucion_prevista if data.tipo == "prestamo" else None
        if data.clausula is not None:
            a.clausula = data.clausula
        db.query(ActaItem).filter(ActaItem.acta_id == a.id).delete(synchronize_session=False)
        _guardar_items(db, a, data.items)
        db.commit()
        log_action(user.username, "modificacion", "acta", a.id, {"numero": a.numero}, ip=_ip(request))
        return _dict(a, _items(db, a.id))
    finally:
        db.close()


@router.post("/{acta_id}/firmar")
def firmar(acta_id: str, data: FirmaIn, request: Request, user: UserOut = Depends(require_modulo("activos", nivel="editar"))):
    db = SessionLocal()
    try:
        a = db.get(Acta, acta_id)
        if not a:
            raise HTTPException(404)
        if a.estado != "borrador":
            raise HTTPException(409, "El acta ya está " + a.estado)
        a.firma_receptor, a.firma_soporte, a.firmo_soporte = data.firma_receptor, data.firma_soporte, user.username
        _confirmar(db, a, user.username)
        db.commit()
        log_action(user.username, "firma", "acta", a.id, {"numero": a.numero, "modo": "pantalla"}, ip=_ip(request))
        return _dict(a, _items(db, a.id))
    finally:
        db.close()


@router.post("/{acta_id}/escaneo")
async def subir_escaneo(acta_id: str, request: Request, archivo: UploadFile = File(...), confirmar: str = Form("1"),
                        user: UserOut = Depends(require_modulo("activos", nivel="editar"))):
    """Escaneo del acta firmada en papel: queda como adjunto de cada equipo y (por defecto) confirma el acta."""
    ext = os.path.splitext(archivo.filename or "")[1].lower()
    if ext not in TIPOS_ESCANEO:
        raise HTTPException(400, "Subí el acta como PDF, JPG o PNG")
    contenido = await archivo.read(MAX_ESCANEO_MB * 1024 * 1024 + 1)
    if len(contenido) > MAX_ESCANEO_MB * 1024 * 1024:
        raise HTTPException(400, "El archivo supera los %d MB" % MAX_ESCANEO_MB)
    db = SessionLocal()
    try:
        a = db.get(Acta, acta_id)
        if not a:
            raise HTTPException(404)
        if a.estado == "anulada":
            raise HTTPException(409, "El acta está anulada")
        nombre = "%s firmada%s" % (a.numero, ext)
        primero = ""
        for it in _items(db, a.id):
            adj_id = str(uuid.uuid4())
            primero = primero or adj_id
            db.add(Adjunto(id=adj_id, asset_id=it.asset_id, nombre=nombre, contenido=contenido, tipo=ext.lstrip("."),
                           tamano=len(contenido), descripcion="Acta " + a.numero + " firmada", subido_por=user.username))
            db.add(Historial(asset_id=it.asset_id, usuario=user.username, campo="archivo_adjunto", valor_ant="",
                             valor_new=nombre, accion="adjunto"))
        a.escaneo_adjunto_id = primero
        if a.estado == "borrador" and confirmar != "0":
            a.firmo_soporte = user.username
            _confirmar(db, a, user.username)
        db.commit()
        log_action(user.username, "firma", "acta", a.id, {"numero": a.numero, "modo": "escaneo"}, ip=_ip(request))
        return _dict(a, _items(db, a.id))
    finally:
        db.close()


@router.post("/{acta_id}/anular")
def anular(acta_id: str, data: AnularIn, request: Request, user: UserOut = Depends(require_modulo("activos", nivel="editar"))):
    db = SessionLocal()
    try:
        a = db.get(Acta, acta_id)
        if not a:
            raise HTTPException(404)
        if a.estado == "anulada":
            raise HTTPException(409, "El acta ya está anulada")
        a.estado, a.anulada_el, a.motivo_anulacion = "anulada", datetime.utcnow(), _texto_limpio(data.motivo)
        db.commit()
        log_action(user.username, "anulacion", "acta", a.id, {"numero": a.numero, "motivo": data.motivo}, ip=_ip(request))
        return _dict(a, _items(db, a.id))
    finally:
        db.close()

