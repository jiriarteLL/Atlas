# -*- coding: utf-8 -*-
"""Auditoria fisica (fase F): campanias de relevamiento por sede con el celular.

Al crear una campania se toma la foto de los activos esperados (los de la sede, de los tipos elegidos, no dados de
baja; el piso es solo un rotulo de la campania). Cada lectura (QR de la etiqueta, serie o n de
inventario) marca el activo como "encontrado"; si el activo existe pero no estaba en la lista es un "sobrante"
(esta en otro lugar segun Atlas) y si el codigo no corresponde a ningun activo queda como "desconocido". Al
cerrar, lo esperado que no se leyo queda "faltante". Los sobrantes se pueden mover a la sede de la campania.
Permiso: modulo "auditoria" (ver / editar).
"""
import re
from datetime import datetime
from typing import List, Optional

from fastapi import APIRouter, Depends, HTTPException, Request
from pydantic import BaseModel, ConfigDict, Field, field_validator
from sqlalchemy import Boolean, Column, DateTime, String

from audit import log_action
from auth import UserOut, require_modulo
from ciclo_activos import AssetAdmin, _texto_limpio, aplicar_movimiento, estado_ciclo
from database import Asset, Base, SessionLocal, _uuid

router = APIRouter(prefix="/api/auditoria", tags=["auditoria fisica"])

MAX_ESPERADOS = 3000


class AuditoriaCampana(Base):
    __tablename__ = "auditoria_campana"
    id          = Column(String, primary_key=True, default=_uuid)
    nombre      = Column(String, default="")
    sede        = Column(String, default="")
    piso        = Column(String, default="")
    tipos       = Column(String, default="")       # "Notebook,Monitor" ; vacio = todos
    estado      = Column(String, default="abierta")  # abierta | cerrada
    creada_por  = Column(String, default="")
    creada      = Column(DateTime, default=datetime.utcnow)
    cerrada     = Column(DateTime, nullable=True)
    cerrada_por = Column(String, default="")


class AuditoriaItem(Base):
    __tablename__ = "auditoria_item"
    id            = Column(String, primary_key=True, default=_uuid)
    campana_id    = Column(String, nullable=False, index=True)
    asset_id      = Column(String, nullable=True, index=True)
    esperado      = Column(Boolean, default=False)
    resultado     = Column(String, default="pendiente")  # pendiente | encontrado | faltante | sobrante | desconocido
    lectura       = Column(String, default="")           # lo que se escaneo o tipeo
    nombre        = Column(String, default="")
    serial        = Column(String, default="")
    tipo          = Column(String, default="")
    usuario       = Column(String, default="")
    sede_sistema  = Column(String, default="")           # sede que tenia en Atlas al leerlo / al crear la campania
    lugar         = Column(String, default="")           # piso / oficina donde se encontro
    leido_por     = Column(String, default="")
    leido_el      = Column(DateTime, nullable=True)
    movido        = Column(Boolean, default=False)


class CampanaIn(BaseModel):
    model_config = ConfigDict(extra="forbid")
    nombre: Optional[str] = Field(default="", max_length=120)
    sede:   str = Field(..., min_length=2, max_length=60)
    piso:   Optional[str] = Field(default="", max_length=40)
    tipos:  List[str] = Field(default_factory=list, max_length=10)

    @field_validator("nombre", "sede", "piso", mode="after")
    @classmethod
    def _limpio(cls, v):
        return _texto_limpio(v)


class LecturaIn(BaseModel):
    model_config = ConfigDict(extra="forbid")
    codigo: str = Field(..., min_length=1, max_length=400)
    lugar:  Optional[str] = Field(default="", max_length=80)

    @field_validator("codigo", "lugar", mode="after")
    @classmethod
    def _limpio(cls, v):
        return _texto_limpio(v)


class MoverIn(BaseModel):
    model_config = ConfigDict(extra="forbid")
    item_ids: Optional[List[str]] = Field(default=None, max_length=MAX_ESPERADOS)


# ---------------------------------------------------------------- helpers
def buscar_activo(db, codigo):
    """QR de Atlas (URL con ?activo=<id> / #activos?activo=<id>), id, serie, n de inventario o nombre."""
    c = (codigo or "").strip()
    m = re.search(r"[?&]activo=([A-Za-z0-9_-]{1,40})", c)
    if m:
        return db.get(Asset, m.group(1))
    if re.fullmatch(r"[A-Za-z0-9_-]{1,40}", c):
        a = db.get(Asset, c)
        if a:
            return a
    if not c:
        return None
    a = db.query(Asset).filter(Asset.serial.ilike(c)).first()
    if a:
        return a
    adm = db.query(AssetAdmin).filter(AssetAdmin.nro_inventario.ilike(c)).first()
    if adm:
        return db.get(Asset, adm.asset_id)
    return db.query(Asset).filter(Asset.nombre.ilike(c)).first()


def _item_dict(i):
    return {k: getattr(i, k) for k in ("id", "asset_id", "esperado", "resultado", "lectura", "nombre", "serial", "tipo",
                                       "usuario", "sede_sistema", "lugar", "leido_por", "leido_el", "movido")}


def _resumen(items, cerrada):
    r = {"esperados": 0, "encontrados": 0, "pendientes": 0, "faltantes": 0, "sobrantes": 0, "desconocidos": 0}
    for i in items:
        r["esperados"] += bool(i.esperado)
        if i.resultado == "encontrado":
            r["encontrados"] += 1
        elif i.resultado == "pendiente":
            r["faltantes" if cerrada else "pendientes"] += 1
        elif i.resultado == "faltante":
            r["faltantes"] += 1
        elif i.resultado == "sobrante":
            r["sobrantes"] += 1
        elif i.resultado == "desconocido":
            r["desconocidos"] += 1
    return r


def _campana_dict(c, items=None):
    d = {k: getattr(c, k) for k in ("id", "nombre", "sede", "piso", "estado", "creada_por", "creada", "cerrada",
                                    "cerrada_por")}
    d["tipos"] = [t for t in (c.tipos or "").split(",") if t]
    if items is not None:
        d["resumen"] = _resumen(items, c.estado == "cerrada")
    return d


def _abierta(db, campana_id):
    c = db.get(AuditoriaCampana, campana_id)
    if not c:
        raise HTTPException(404)
    if c.estado != "abierta":
        raise HTTPException(409, "La campaña está cerrada")
    return c


def _ip(request):
    return request.client.host if request.client else ""


# ---------------------------------------------------------------- endpoints
@router.get("")
def listar(user: UserOut = Depends(require_modulo("auditoria"))):
    db = SessionLocal()
    try:
        camps = db.query(AuditoriaCampana).order_by(AuditoriaCampana.creada.desc()).limit(300).all()
        items = {}
        for i in db.query(AuditoriaItem).filter(AuditoriaItem.campana_id.in_([c.id for c in camps])).all():
            items.setdefault(i.campana_id, []).append(i)
        return [_campana_dict(c, items.get(c.id, [])) for c in camps]
    finally:
        db.close()


@router.post("")
def crear(data: CampanaIn, request: Request, user: UserOut = Depends(require_modulo("auditoria", nivel="editar"))):
    db = SessionLocal()
    try:
        q = db.query(Asset).filter(Asset.estado != "Dado de baja").filter(Asset.ubicacion.ilike(data.sede))
        tipos = [t for t in data.tipos if t]
        if tipos:
            q = q.filter(Asset.tipo.in_(tipos))
        esperados = q.limit(MAX_ESPERADOS).all()
        c = AuditoriaCampana(nombre=data.nombre or ("Relevamiento %s %s" % (data.sede, datetime.now().strftime("%d/%m/%Y"))),
                             sede=data.sede, piso=data.piso or "", tipos=",".join(tipos), estado="abierta",
                             creada_por=user.username, creada=datetime.utcnow())
        db.add(c)
        db.flush()
        for a in esperados:
            db.add(AuditoriaItem(campana_id=c.id, asset_id=a.id, esperado=True, resultado="pendiente", nombre=a.nombre or "",
                                 serial=a.serial or "", tipo=a.tipo or "", usuario=a.usuario or "",
                                 sede_sistema=a.ubicacion or ""))
        db.commit()
        log_action(user.username, "alta", "auditoria", c.id, {"sede": c.sede, "esperados": len(esperados)}, ip=_ip(request))
        return _campana_dict(c, db.query(AuditoriaItem).filter(AuditoriaItem.campana_id == c.id).all())
    finally:
        db.close()


@router.get("/{campana_id}")
def ver(campana_id: str, user: UserOut = Depends(require_modulo("auditoria"))):
    db = SessionLocal()
    try:
        c = db.get(AuditoriaCampana, campana_id)
        if not c:
            raise HTTPException(404)
        items = db.query(AuditoriaItem).filter(AuditoriaItem.campana_id == c.id).all()
        d = _campana_dict(c, items)
        d["items"] = [_item_dict(i) for i in sorted(items, key=lambda i: (i.resultado != "pendiente", i.nombre or ""))]
        return d
    finally:
        db.close()


@router.post("/{campana_id}/lecturas")
def leer(campana_id: str, data: LecturaIn, request: Request,
         user: UserOut = Depends(require_modulo("auditoria", nivel="editar"))):
    db = SessionLocal()
    try:
        c = _abierta(db, campana_id)
        a = buscar_activo(db, data.codigo)
        ahora = datetime.utcnow()
        if a is None:
            ya = (db.query(AuditoriaItem).filter(AuditoriaItem.campana_id == c.id, AuditoriaItem.asset_id.is_(None),
                                                 AuditoriaItem.lectura == data.codigo).first())
            i = ya or AuditoriaItem(campana_id=c.id, asset_id=None, esperado=False, resultado="desconocido",
                                    lectura=data.codigo[:400])
            if not ya:
                db.add(i)
            i.lugar, i.leido_por, i.leido_el = data.lugar or "", user.username, ahora
            db.commit()
            return {"resultado": "desconocido", "repetido": bool(ya), "item": _item_dict(i)}
        i = (db.query(AuditoriaItem).filter(AuditoriaItem.campana_id == c.id, AuditoriaItem.asset_id == a.id).first())
        repetido = bool(i and i.resultado in ("encontrado", "sobrante"))
        if i is None:
            i = AuditoriaItem(campana_id=c.id, asset_id=a.id, esperado=False, resultado="sobrante", nombre=a.nombre or "",
                              serial=a.serial or "", tipo=a.tipo or "", usuario=a.usuario or "",
                              sede_sistema=a.ubicacion or "")
            db.add(i)
        elif i.esperado:
            i.resultado = "encontrado"
        i.lectura = data.codigo[:400]
        i.lugar, i.leido_por, i.leido_el = data.lugar or "", user.username, ahora
        db.commit()
        return {"resultado": i.resultado, "repetido": repetido, "item": _item_dict(i),
                "activo": {"id": a.id, "nombre": a.nombre, "tipo": a.tipo, "modelo": " ".join(x for x in (a.marca, a.modelo) if x),
                           "serial": a.serial, "usuario": a.usuario, "sede": a.ubicacion, "estado_ciclo": estado_ciclo(a)}}
    finally:
        db.close()


@router.post("/{campana_id}/cerrar")
def cerrar(campana_id: str, request: Request, user: UserOut = Depends(require_modulo("auditoria", nivel="editar"))):
    db = SessionLocal()
    try:
        c = _abierta(db, campana_id)
        items = db.query(AuditoriaItem).filter(AuditoriaItem.campana_id == c.id).all()
        for i in items:
            if i.resultado == "pendiente":
                i.resultado = "faltante"
        c.estado, c.cerrada, c.cerrada_por = "cerrada", datetime.utcnow(), user.username
        db.commit()
        r = _resumen(items, True)
        log_action(user.username, "cierre", "auditoria", c.id, r, ip=_ip(request))
        return {**_campana_dict(c, items), "items": [_item_dict(i) for i in items]}
    finally:
        db.close()


@router.post("/{campana_id}/mover-sobrantes")
def mover_sobrantes(campana_id: str, data: MoverIn, request: Request,
                    user: UserOut = Depends(require_modulo("auditoria", nivel="editar"))):
    """Pasa a la sede de la campania los sobrantes (todos o los elegidos), con Historial y movimiento "traslado"."""
    db = SessionLocal()
    try:
        c = db.get(AuditoriaCampana, campana_id)
        if not c:
            raise HTTPException(404)
        q = db.query(AuditoriaItem).filter(AuditoriaItem.campana_id == c.id, AuditoriaItem.resultado == "sobrante",
                                           AuditoriaItem.movido.is_(False))
        if data.item_ids is not None:
            q = q.filter(AuditoriaItem.id.in_(data.item_ids))
        movidos = 0
        for i in q.all():
            a = db.get(Asset, i.asset_id) if i.asset_id else None
            if not a:
                continue
            if (a.ubicacion or "").lower() != c.sede.lower():
                aplicar_movimiento(db, a, "traslado", user.username, sede=c.sede,
                                   motivo="Auditoría física: " + c.nombre + (" · " + i.lugar if i.lugar else ""))
            i.movido = True
            movidos += 1
        db.commit()
        log_action(user.username, "traslado", "auditoria", c.id, {"movidos": movidos, "sede": c.sede}, ip=_ip(request))
        return {"movidos": movidos}
    finally:
        db.close()
