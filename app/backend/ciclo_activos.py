# -*- coding: utf-8 -*-
"""Ciclo de vida de los activos (fase F): estado, datos de compra, vida util / renovacion y movimientos.

El estado vive en Asset.estado (el mismo campo de siempre) con los valores nuevos En stock / Asignado / Prestado /
En reparacion / Para baja / Dado de baja. Los valores viejos se leen asi: "Activo" = Asignado si tiene usuario o
En stock si no; "Stock"/"Libre" = En stock; "Mantenimiento" = En reparacion. El agente nunca cambia el estado de
un activo que ya existe (main._aplicar_sync lo conserva), asi que un estado puesto a mano no se pisa.

Cada cambio de estado o de persona queda en asset_movimiento (y en el Historial del activo). Los movimientos de
las actas firmadas llevan el acta_id. Los datos de compra (n de inventario, fecha, proveedor, factura, costo,
vida util propia) van en asset_admin.
"""
import re
from datetime import date, datetime, timedelta
from typing import Literal, Optional

from fastapi import APIRouter, Depends, HTTPException, Request
from pydantic import BaseModel, ConfigDict, Field, field_validator
from sqlalchemy import Column, Date, DateTime, Float, ForeignKey, Integer, String, Text

import config
from audit import log_action
from auth import MODULOS_FICHA, UserOut, require_modulo
from database import Asset, AssetGlpi, Base, Historial, MonitorDetalle, SessionLocal, _uuid

router = APIRouter(prefix="/api/ciclo", tags=["ciclo de vida"])

ESTADOS_CICLO = ("En stock", "Asignado", "Prestado", "En reparación", "Para baja", "Dado de baja")
# tipo de movimiento -> estado en que queda el activo (None = no cambia; "auto" = Asignado si tiene usuario)
MOVIMIENTOS = {
    "alta": None, "asignacion": "Asignado", "devolucion": "En stock", "prestamo": "Prestado",
    "envio_reparacion": "En reparación", "vuelta_reparacion": "auto", "para_baja": "Para baja",
    "baja": "Dado de baja", "traslado": None,
}
ROTULO_MOVIMIENTO = {
    "alta": "Alta", "asignacion": "Asignación", "devolucion": "Devolución", "prestamo": "Préstamo",
    "envio_reparacion": "Envío a reparación", "vuelta_reparacion": "Vuelta de reparación", "para_baja": "Para baja",
    "baja": "Baja", "traslado": "Traslado de sede",
}
DIAS_AVISO_RENOVACION = 90


# ---------------------------------------------------------------- modelos
class AssetAdmin(Base):
    """Datos administrativos y de compra (los carga una persona; el agente no los toca)."""
    __tablename__ = "asset_admin"
    asset_id        = Column(String, ForeignKey("assets.id", ondelete="CASCADE"), primary_key=True)
    nro_inventario  = Column(String, default="", index=True)
    fecha_compra    = Column(Date, nullable=True)
    proveedor       = Column(String, default="")
    factura         = Column(String, default="")
    costo           = Column(Float, nullable=True)
    moneda          = Column(String, default="")
    vida_util_meses = Column(Integer, nullable=True)       # vacio = la del tipo (config.VIDA_UTIL_MESES)
    notas           = Column(Text, default="")
    actualizado     = Column(DateTime, default=datetime.utcnow)


class AssetMovimiento(Base):
    __tablename__ = "asset_movimiento"
    id         = Column(String, primary_key=True, default=_uuid)
    asset_id   = Column(String, nullable=False, index=True)
    fecha      = Column(DateTime, default=datetime.utcnow, index=True)
    tipo       = Column(String, default="")
    estado_ant = Column(String, default="")
    estado_new = Column(String, default="")
    de_usuario = Column(String, default="")
    a_usuario  = Column(String, default="")
    sede       = Column(String, default="")
    motivo     = Column(Text, default="")
    acta_id    = Column(String, default="", index=True)
    hecho_por  = Column(String, default="")


# ---------------------------------------------------------------- estado
def estado_ciclo(a):
    """Estado de ciclo de vida para mostrar, a partir de Asset.estado (incluye los valores viejos)."""
    e = (a.estado or "").strip()
    if e in ESTADOS_CICLO:
        return e
    if e in ("Stock", "Libre"):
        return "En stock"
    if e == "Mantenimiento":
        return "En reparación"
    if e in ("Activo", ""):
        return "Asignado" if (a.usuario or "").strip() else "En stock"
    return e   # "Robado" u otro que se cargo a mano


def usuario_fijado(db, asset_id):
    """True si el usuario del equipo lo decidio una persona: el ultimo movimiento de asignacion/prestamo/devolucion
    es una asignacion o un prestamo (por acta o cargado a mano). Mientras tanto el agente no cambia el usuario;
    quien inicio sesion en la PC sigue viendose en usuario_alt y en el ultimo login. Una devolucion lo libera."""
    m = (db.query(AssetMovimiento).filter(AssetMovimiento.asset_id == asset_id,
                                          AssetMovimiento.tipo.in_(("asignacion", "prestamo", "devolucion")))
         .order_by(AssetMovimiento.fecha.desc()).first())
    return bool(m and m.tipo in ("asignacion", "prestamo"))


def aplicar_movimiento(db, a, tipo, hecho_por, a_usuario=None, sede=None, motivo="", acta_id="", fecha=None):
    """Registra el movimiento y deja el activo en el estado / persona / sede que corresponde (con Historial)."""
    if tipo not in MOVIMIENTOS:
        raise ValueError("tipo de movimiento invalido")
    antes = {"estado": a.estado or "", "usuario": a.usuario or "", "ubicacion": a.ubicacion or ""}
    estado_ant = estado_ciclo(a)
    de_usuario = a.usuario or ""
    if tipo in ("asignacion", "prestamo"):
        a.usuario = (a_usuario or "").strip()
    elif tipo == "devolucion":
        a.usuario = ""
    if sede:
        a.ubicacion = sede
    nuevo = MOVIMIENTOS[tipo]
    if nuevo == "auto":
        nuevo = "Asignado" if (a.usuario or "").strip() else "En stock"
    if nuevo:
        a.estado = nuevo
    a.updated = datetime.utcnow()
    despues = {"estado": a.estado or "", "usuario": a.usuario or "", "ubicacion": a.ubicacion or ""}
    for campo in antes:
        if antes[campo] != despues[campo]:
            db.add(Historial(asset_id=a.id, usuario=hecho_por, campo=campo, valor_ant=antes[campo],
                             valor_new=despues[campo], accion="ciclo de vida"))
    # El reloj de Windows tiene resolucion de ~1-15 ms: dos movimientos seguidos podrian empatar y salir en otro
    # orden. Cada movimiento de un activo queda siempre despues del anterior.
    fecha = fecha or datetime.utcnow()
    ult = (db.query(AssetMovimiento.fecha).filter(AssetMovimiento.asset_id == a.id)
           .order_by(AssetMovimiento.fecha.desc()).first())
    if ult and ult[0] and fecha <= ult[0]:
        fecha = ult[0] + timedelta(microseconds=1000)
    m = AssetMovimiento(asset_id=a.id, fecha=fecha, tipo=tipo, estado_ant=estado_ant,
                        estado_new=estado_ciclo(a), de_usuario=de_usuario,
                        a_usuario=a.usuario if tipo in ("asignacion", "prestamo") else "",
                        sede=sede or "", motivo=(motivo or "")[:2000], acta_id=acta_id or "", hecho_por=hecho_por)
    db.add(m)
    return m


# ---------------------------------------------------------------- vida util
def _sumar_meses(d, meses):
    y, m = divmod(d.month - 1 + meses, 12)
    dia = min(d.day, [31, 29 if (d.year + y) % 4 == 0 else 28, 31, 30, 31, 30, 31, 31, 30, 31, 30, 31][m])
    return date(d.year + y, m + 1, dia)


def fecha_bios(texto):
    """'R2XET34W (05/10/2023)' o '... (2023-05-10)' -> date. Es la fecha de la version de BIOS (aproximada)."""
    s = texto or ""
    m = re.search(r"(\d{4})-(\d{2})-(\d{2})", s)
    try:
        if m:
            return date(int(m.group(1)), int(m.group(2)), int(m.group(3)))
        m = re.search(r"(\d{1,2})/(\d{1,2})/(\d{4})", s)   # GLPI la manda como MM/DD/AAAA
        if m:
            return date(int(m.group(3)), int(m.group(1)), int(m.group(2)))
    except ValueError:
        return None
    return None


def vida_util(a, adm, monitor=None, glpi=None, hoy=None):
    """Base (compra > fabricacion del monitor > BIOS), meses, renovacion sugerida y alerta."""
    hoy = hoy or date.today()
    meses = (adm.vida_util_meses if adm and adm.vida_util_meses else None) or config.VIDA_UTIL_MESES.get(a.tipo or "")
    base, origen = None, ""
    if adm and adm.fecha_compra:
        base, origen = adm.fecha_compra, "compra"
    elif monitor is not None and monitor.anio:
        try:
            base = date.fromisocalendar(monitor.anio, monitor.semana or 1, 1)
        except ValueError:
            base = date(monitor.anio, 1, 1)
        origen = "fabricación del monitor"
    elif glpi is not None and fecha_bios(glpi.bios):
        base, origen = fecha_bios(glpi.bios), "fecha de BIOS (aprox.)"
    out = {"vida_util_meses": meses, "base": base, "base_origen": origen, "renovacion": None,
           "dias_renovacion": None, "para_renovar": False, "renovar_pronto": False}
    if base and meses:
        ren = _sumar_meses(base, meses)
        dias = (ren - hoy).days
        out.update(renovacion=ren, dias_renovacion=dias, para_renovar=dias <= 0,
                   renovar_pronto=0 < dias <= DIAS_AVISO_RENOVACION)
    return out


def _admin_dict(adm):
    if not adm:
        return {"nro_inventario": "", "fecha_compra": None, "proveedor": "", "factura": "", "costo": None,
                "moneda": "", "vida_util_meses": None, "notas": ""}
    return {k: getattr(adm, k) for k in ("nro_inventario", "fecha_compra", "proveedor", "factura", "costo",
                                         "moneda", "vida_util_meses", "notas")}


def _mov_dict(m):
    return {"id": m.id, "fecha": m.fecha, "tipo": m.tipo, "rotulo": ROTULO_MOVIMIENTO.get(m.tipo, m.tipo),
            "estado_ant": m.estado_ant, "estado_new": m.estado_new, "de_usuario": m.de_usuario,
            "a_usuario": m.a_usuario, "sede": m.sede, "motivo": m.motivo, "acta_id": m.acta_id,
            "hecho_por": m.hecho_por}


def _datos_vida(db):
    """Para el resumen: {asset_id: (admin, monitor, glpi)} sin una consulta por activo."""
    adm = {x.asset_id: x for x in db.query(AssetAdmin).all()}
    mon = {x.asset_id: x for x in db.query(MonitorDetalle).all()}
    glpi = {(x.serial or "").strip().upper(): x for x in db.query(AssetGlpi).all()}
    return adm, mon, glpi


def filas_vida_util(db, hoy=None):
    adm, mon, glpi = _datos_vida(db)
    out = []
    for a in db.query(Asset).filter(Asset.estado != "Dado de baja").all():
        v = vida_util(a, adm.get(a.id), mon.get(a.id), glpi.get((a.serial or "").strip().upper()), hoy)
        out.append((a, v))
    return out


def borrar_datos_ciclo(db, asset_id):
    """Para el borrado de un activo (en SQLite las FK no se aplican solas). Los movimientos quedan como registro."""
    db.query(AssetAdmin).filter(AssetAdmin.asset_id == asset_id).delete(synchronize_session=False)


# ---------------------------------------------------------------- API
def _texto_limpio(v):
    if isinstance(v, str):
        v = v.strip()
        if any(ord(ch) < 32 and ch not in "\n\t" for ch in v):
            raise ValueError("contiene caracteres de control")
        if re.search(r"(?i)(contrase(n|ñ)a|password|clave)\s*[:=]", v):
            raise ValueError("no se guardan credenciales en Atlas")
    return v


class AdminIn(BaseModel):
    model_config = ConfigDict(extra="forbid")
    nro_inventario:  Optional[str] = Field(default=None, max_length=60)
    fecha_compra:    Optional[date] = None
    proveedor:       Optional[str] = Field(default=None, max_length=120)
    factura:         Optional[str] = Field(default=None, max_length=60)
    costo:           Optional[float] = Field(default=None, ge=0)
    moneda:          Optional[Literal["ARS", "USD", ""]] = None
    vida_util_meses: Optional[int] = Field(default=None, ge=1, le=240)
    notas:           Optional[str] = Field(default=None, max_length=2000)

    @field_validator("*", mode="after")
    @classmethod
    def _limpio(cls, v):
        return _texto_limpio(v)


class MovimientoIn(BaseModel):
    model_config = ConfigDict(extra="forbid")
    tipo:      Literal[tuple(k for k in MOVIMIENTOS if k != "alta")]
    a_usuario: Optional[str] = Field(default=None, max_length=120)
    sede:      Optional[str] = Field(default=None, max_length=60)
    motivo:    Optional[str] = Field(default="", max_length=2000)

    @field_validator("*", mode="after")
    @classmethod
    def _limpio(cls, v):
        return _texto_limpio(v)


@router.get("/config")
def ver_config(user: UserOut = Depends(require_modulo(*MODULOS_FICHA))):
    return {"url_publica": config.ATLAS_URL_PUBLICA, "vida_util_meses": config.VIDA_UTIL_MESES,
            "estados": list(ESTADOS_CICLO), "movimientos": ROTULO_MOVIMIENTO}


@router.get("/resumen")
def resumen(user: UserOut = Depends(require_modulo("activos", "dashboard"))):
    db = SessionLocal()
    try:
        filas = filas_vida_util(db)
        por_estado = {}
        for a, _ in filas:
            e = estado_ciclo(a)
            por_estado[e] = por_estado.get(e, 0) + 1
        return {"por_estado": por_estado,
                "para_renovar": sum(v["para_renovar"] for _, v in filas),
                "renovar_pronto": sum(v["renovar_pronto"] for _, v in filas),
                "sin_dato": sum(1 for a, v in filas if v["renovacion"] is None and v["vida_util_meses"]),
                "total": len(filas)}
    finally:
        db.close()


@router.get("/renovar")
def para_renovar(user: UserOut = Depends(require_modulo("activos", "dashboard"))):
    db = SessionLocal()
    try:
        return [{"id": a.id, "nombre": a.nombre, "tipo": a.tipo, "marca": a.marca, "modelo": a.modelo,
                 "serial": a.serial, "usuario": a.usuario, "sede": a.ubicacion, "estado_ciclo": estado_ciclo(a), **v}
                for a, v in filas_vida_util(db) if v["para_renovar"] or v["renovar_pronto"]]
    finally:
        db.close()


@router.get("/inventario")
def numeros_de_inventario(user: UserOut = Depends(require_modulo(*MODULOS_FICHA))):
    """{asset_id: n de inventario} de los que lo tienen cargado (para las etiquetas y la lista)."""
    db = SessionLocal()
    try:
        return {x.asset_id: x.nro_inventario for x in db.query(AssetAdmin).filter(AssetAdmin.nro_inventario != "").all()}
    finally:
        db.close()


@router.get("/{asset_id}")
def ver_ciclo(asset_id: str, user: UserOut = Depends(require_modulo(*MODULOS_FICHA))):
    db = SessionLocal()
    try:
        a = db.get(Asset, asset_id)
        if not a:
            raise HTTPException(404)
        adm = db.get(AssetAdmin, asset_id)
        mon = db.get(MonitorDetalle, asset_id)
        glpi = db.query(AssetGlpi).filter(AssetGlpi.serial == (a.serial or "")).first() if a.serial else None
        movs = (db.query(AssetMovimiento).filter(AssetMovimiento.asset_id == asset_id)
                .order_by(AssetMovimiento.fecha.desc()).limit(200).all())
        return {"estado_ciclo": estado_ciclo(a), "estado": a.estado, "admin": _admin_dict(adm),
                "vida_util": vida_util(a, adm, mon, glpi), "movimientos": [_mov_dict(m) for m in movs]}
    finally:
        db.close()


@router.put("/{asset_id}/admin")
def editar_admin(asset_id: str, data: AdminIn, request: Request,
                 user: UserOut = Depends(require_modulo("activos", nivel="editar"))):
    db = SessionLocal()
    try:
        a = db.get(Asset, asset_id)
        if not a:
            raise HTTPException(404)
        adm = db.get(AssetAdmin, asset_id)
        if not adm:
            adm = AssetAdmin(asset_id=asset_id, nro_inventario="", proveedor="", factura="", moneda="", notas="")
            db.add(adm)
        cambios = {}
        for k, v in data.model_dump(exclude_unset=True).items():
            if v != getattr(adm, k):
                cambios[k] = (getattr(adm, k), v)
                setattr(adm, k, v)
        adm.actualizado = datetime.utcnow()
        for k, (ant, nue) in cambios.items():
            db.add(Historial(asset_id=asset_id, usuario=user.username, campo=k,
                             valor_ant="" if ant is None else str(ant), valor_new="" if nue is None else str(nue),
                             accion="edicion"))
        db.commit()
        log_action(user.username, "modificacion", "asset_admin", asset_id,
                   {k: [str(x), str(y)] for k, (x, y) in cambios.items()}, ip=request.client.host if request.client else "")
        return _admin_dict(adm)
    finally:
        db.close()


@router.post("/{asset_id}/movimientos")
def registrar_movimiento(asset_id: str, data: MovimientoIn, request: Request,
                         user: UserOut = Depends(require_modulo("activos", nivel="editar"))):
    if data.tipo in ("asignacion", "prestamo") and not (data.a_usuario or "").strip():
        raise HTTPException(422, "Falta la persona a la que se asigna o presta")
    db = SessionLocal()
    try:
        a = db.get(Asset, asset_id)
        if not a:
            raise HTTPException(404)
        m = aplicar_movimiento(db, a, data.tipo, user.username, a_usuario=data.a_usuario, sede=data.sede,
                               motivo=data.motivo)
        db.commit()
        out = _mov_dict(m)
        log_action(user.username, "movimiento", "asset", asset_id, {"tipo": data.tipo, "estado": out["estado_new"]},
                   ip=request.client.host if request.client else "")
        return {"movimiento": out, "estado": a.estado, "estado_ciclo": estado_ciclo(a), "usuario": a.usuario,
                "ubicacion": a.ubicacion}
    finally:
        db.close()
