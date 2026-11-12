# -*- coding: utf-8 -*-
import gzip as _gzip
import hmac
import json as _json
import logging
import mimetypes
import os
import re
import threading
import time
import unicodedata
from urllib.parse import quote
import uuid
from contextlib import asynccontextmanager
from datetime import date, datetime
from typing import Literal, Optional, Union

from fastapi import BackgroundTasks, Depends, FastAPI, File, Form, Header, HTTPException, Request, UploadFile
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, JSONResponse, Response
from pydantic import BaseModel, Field, field_validator
from slowapi import _rate_limit_exceeded_handler
from slowapi.errors import RateLimitExceeded
from sqlalchemy import func, text as _sqltext

import config
import contexto
from audit import log_action
from auth import (ELIMINAR_ACTIVOS, MODULOS_FICHA, MODULOS_LISTA_ACTIVOS, User, UserOut, auth_router,
                  login_router, require_modulo)
from database import (Adjunto, Asset, AssetGlpi, Historial, Proyecto, ProyectoActivo, ProyectoResponsable,
                      ProyectoTarea, SessionLocal, Snapshot, Ticket, init_db)
from impresoras import borrar_datos_impresora, router as impresoras_router
from impresoras_relevamiento import router as relevamiento_router, sede_de_nombre
from salud import borrar_datos_salud, guardar_salud, limitar_salud, router as salud_router
from telefonia import router as telefonia_router
from monitores import borrar_datos_monitor, limitar_monitores, procesar_monitores, router as monitores_router
import garantias
from garantias import borrar_datos_garantia, router as garantias_router
from ciclo_activos import borrar_datos_ciclo, reparto_activos, router as ciclo_router, usuario_fijado
from actas import router as actas_router
from auditoria import router as auditoria_router
import conectores
from conectores import router as conectores_router
from licencias import router as licencias_router
from costos import router as costos_router
from servidores import borrar_datos_servidor, guardar_servidor, limitar_servidor, router as servidores_router
from mailer import notificar_proyecto_finalizado
from metricas import metricas_texto, registrar_request
from ratelimit import limiter

contexto.configurar_logs()
log = logging.getLogger("atlas")


@asynccontextmanager
async def lifespan(app):
    init_db()
    if config.SNAPSHOT_DIAS > 0:
        threading.Thread(target=_loop_snapshots, daemon=True).start()
    if config.GARANTIA_REFRESCO_DIAS > 0:
        # Corre en los dos procesos (HTTP y HTTPS); el lease de garantia_corrida hace que consulte uno solo
        threading.Thread(target=garantias.loop, daemon=True).start()
    if conectores.hay_alguno_configurado():
        # vCenter / Azure / Redfish: solo si hay alguno configurado (lease por conector, consulta un solo proceso)
        threading.Thread(target=conectores.loop, daemon=True).start()
    log.info("app.start", extra={"event": "app.start"})
    yield


app = FastAPI(title="Atlas", version=config.APP_VERSION, lifespan=lifespan,
              docs_url=None, redoc_url=None, openapi_url=None)  # sin documentacion publica de la API
app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)
app.include_router(auth_router)
app.include_router(login_router)
app.include_router(relevamiento_router)   # antes que /api/impresoras/{id}
app.include_router(impresoras_router)
app.include_router(salud_router)
app.include_router(telefonia_router)
app.include_router(monitores_router)
app.include_router(garantias_router)
app.include_router(ciclo_router)
app.include_router(costos_router)
app.include_router(actas_router)
app.include_router(auditoria_router)
app.include_router(servidores_router)
app.include_router(conectores_router)
app.include_router(licencias_router)
if config.CORS_ORIGINS:
    app.add_middleware(CORSMiddleware, allow_origins=config.CORS_ORIGINS, allow_methods=["*"], allow_headers=["*"],
                       allow_credentials=True)

# Cabeceras de seguridad (BEST_PRACTICES §5.4). Traefik puede agregar las suyas; estas valen igual sin proxy.
_CSP = ("default-src 'self'; script-src 'self'; style-src 'self' 'unsafe-inline'; "
        "font-src 'self' data:; img-src 'self' data: blob:; connect-src 'self'; "
        "object-src 'none'; base-uri 'self'; form-action 'self'; frame-ancestors 'none'")


@app.middleware("http")
async def cabeceras_seguridad(request: Request, call_next):
    inicio = time.perf_counter()
    resp = await call_next(request)
    resp.headers.setdefault("X-Content-Type-Options", "nosniff")
    resp.headers.setdefault("X-Frame-Options", "DENY")
    resp.headers.setdefault("Referrer-Policy", "strict-origin-when-cross-origin")
    resp.headers.setdefault("Permissions-Policy", "camera=(self), microphone=(), geolocation=()")
    resp.headers.setdefault("Content-Security-Policy", _CSP)
    if request.url.scheme == "https":
        resp.headers.setdefault("Strict-Transport-Security", "max-age=31536000; includeSubDomains")
    if request.url.path.startswith(("/api/", "/auth/", "/login", "/logout")):
        resp.headers.setdefault("Cache-Control", "no-store")
    ruta = request.scope.get("route")
    registrar_request(request.method, getattr(ruta, "path", "otra"), resp.status_code, time.perf_counter() - inicio)
    return resp


# El contexto (request_id, ip, user-agent) envuelve todo, incluidos los otros middlewares.
app.add_middleware(contexto.ContextoMiddleware)


def _ip(request):
    return request.client.host if (request is not None and request.client) else ""


def _clave_ok(recibida, esperada):
    """Comparacion en tiempo constante. Sin clave configurada, nada pasa."""
    return bool(esperada) and hmac.compare_digest((recibida or "").encode(), esperada.encode())


def _url_publica(request):
    """URL publica del ambiente: APP_URL si esta definida (detras de Traefik), si no la del request."""
    return config.APP_URL or str(request.base_url).rstrip("/")


# ================================================================ endpoints publicos
@app.get("/health")
def health():
    try:
        db = SessionLocal()
        db.execute(_sqltext("SELECT 1"))
        db.close()
    except Exception:
        log.error("health.db_error", extra={"event": "health"})
        return JSONResponse(status_code=503, content={"status": "error", "db": "sin conexion"})
    return {"status": "ok"}


@app.get("/maestro/branding")
def maestro_branding(request: Request, x_maestro_api_key: str = Header(default="")):
    if not _clave_ok(x_maestro_api_key, config.MAESTRO_API_KEY):
        return JSONResponse(status_code=401, content={"error": "invalid_api_key"})
    base = _url_publica(request)
    return {"company_name": config.COMPANY_NAME,
            "logo_url": config.COMPANY_LOGO_URL or base + "/logo.png",
            "primary_color": config.COMPANY_PRIMARY_COLOR,
            "favicon_url": base + "/favicon.ico"}


@app.get("/metrics")
def metrics(x_maestro_api_key: str = Header(default="")):
    """Metricas Prometheus (BEST_PRACTICES §6.2): solo para el scrapper del Maestro, con X-Maestro-Api-Key."""
    if not _clave_ok(x_maestro_api_key, config.MAESTRO_API_KEY):
        return JSONResponse(status_code=401, content={"error": "invalid_api_key"})
    cuerpo, tipo = metricas_texto()
    return Response(content=cuerpo, media_type=tipo)
# ================================================================ activos
TIPOS_OK = ("Notebook", "Monitor", "Impresora", "Servidor", "Switch", "UPS", "CPU", "VM")
# Los primeros son los de antes; los de ciclo de vida (fase F, ver ciclo_activos.py) van al final.
ESTADOS_OK = ("Activo", "Mantenimiento", "Dado de baja", "Libre", "Stock", "Robado",
              "En stock", "Asignado", "Prestado", "En reparación", "Para baja")


def _limpiar(v):
    if not isinstance(v, str):
        return v
    v = v.strip()
    if any(unicodedata.category(ch)[0] == "C" for ch in v):
        raise ValueError("contiene caracteres de control")
    return v


class AssetIn(BaseModel):
    nombre:          Optional[str] = ""
    tipo:            Optional[str] = ""
    marca:           Optional[str] = ""
    modelo:          Optional[str] = ""
    serial:          Optional[str] = ""
    estado:          Optional[str] = "Activo"
    usuario:         Optional[str] = ""
    usuario_alt:     Optional[str] = ""
    ubicacion:       Optional[str] = ""
    grupo:           Optional[str] = ""
    red:             Optional[str] = ""
    cpu:             Optional[str] = ""
    ram:             Optional[str] = ""
    disco:           Optional[str] = ""
    ip:              Optional[str] = ""
    so:              Optional[str] = ""
    so_version:      Optional[str] = ""
    so_arquitectura: Optional[str] = ""
    garantia:        Optional[str] = ""
    comentarios:     Optional[str] = ""
    monitores:       Optional[str] = ""
    impresoras:      Optional[str] = ""
    software:        Optional[str] = ""
    cifrado:         Optional[str] = ""
    tpm:             Optional[str] = ""
    ip_publica:      Optional[str] = ""
    mac:             Optional[str] = ""
    gateway:         Optional[str] = ""
    ou_ad:           Optional[str] = ""
    ultimo_reinicio: Optional[str] = ""
    ultimo_login:    Optional[str] = ""

    @field_validator("*", mode="after")
    @classmethod
    def _v(cls, v):
        return _limpiar(v)


class AssetCreate(AssetIn):
    tipo:   Literal[TIPOS_OK]
    estado: Literal[ESTADOS_OK] = "Activo"
    serial: str = Field(..., min_length=3, max_length=100)
    marca:  str = Field(..., min_length=1)
    modelo: str = Field(..., min_length=1)


class AssetUpdate(AssetIn):
    tipo:   Optional[Literal[TIPOS_OK]] = None
    estado: Optional[Literal[ESTADOS_OK]] = None


class AssetSync(AssetIn):
    """Solo para /api/sync: acepta software como texto (formato viejo) o lista JSON (formato nuevo)."""
    software: Optional[Union[str, list]] = ""
    # Salud y seguridad (agente de Atlas): se guarda aparte en asset_salud, ver salud.py
    salud: Optional[dict] = None
    # Monitores con el detalle del EDID (agente de Atlas): ver monitores.py
    monitores_detalle: Optional[list] = None
    # Servidores (agente de Atlas 5.4+, solo Windows Server): ver servidores.py
    servidor: Optional[dict] = None

    @field_validator("servidor", mode="before")
    @classmethod
    def _servidor(cls, v):
        return limitar_servidor(v)

    @field_validator("salud", mode="after")
    @classmethod
    def _salud(cls, v):
        return limitar_salud(v)

    @field_validator("monitores_detalle", mode="before")
    @classmethod
    def _monitores(cls, v):
        return limitar_monitores(v)


class TicketIn(BaseModel):
    activo:     str
    titulo:     str
    estado:     Optional[str] = "Abierto"
    prioridad:  Optional[str] = "Media"
    comentario: Optional[str] = ""


def registrar_historial(db, asset_id, usuario, accion, cambios):
    for campo, (valor_ant, valor_new) in cambios.items():
        if str(valor_ant) != str(valor_new):
            db.add(Historial(asset_id=asset_id, usuario=usuario, campo=campo,
                             valor_ant=str(valor_ant) if valor_ant else "",
                             valor_new=str(valor_new) if valor_new else "", accion=accion))


@app.get("/api/assets/{asset_id}/historial")
def get_historial(asset_id: str, user: UserOut = Depends(require_modulo(*MODULOS_FICHA))):
    db = SessionLocal()
    items = db.query(Historial).filter(Historial.asset_id == asset_id).order_by(Historial.fecha.desc()).all()
    db.close()
    return [{"id": h.id, "fecha": h.fecha, "usuario": h.usuario, "campo": h.campo,
             "valor_ant": h.valor_ant, "valor_new": h.valor_new, "accion": h.accion} for h in items]


@app.get("/api/assets")
def list_assets(user: UserOut = Depends(require_modulo(*MODULOS_LISTA_ACTIVOS))):
    db = SessionLocal()
    try:
        r = db.query(Asset).all()
        reparto = reparto_activos(db)     # segundo usuario y centro de costo (asset_admin, carga manual)
    finally:
        db.close()
    vacio = {"usuario_secundario": "", "usuario_secundario_nombre": "", "porcentaje_principal": None, "centro_costo": ""}
    columnas = [c.name for c in Asset.__table__.columns]
    return [dict({k: getattr(a, k) for k in columnas}, **reparto.get(a.id, vacio)) for a in r]


@app.get("/api/assets/{aid}/ficha")
def ver_ficha_asset(aid: str, request: Request, user: UserOut = Depends(require_modulo(*MODULOS_FICHA))):
    db = SessionLocal()
    obj = db.query(Asset).filter(Asset.id == aid).first()
    db.close()
    if not obj:
        raise HTTPException(404)
    log_action(user.username, "ver_ficha", "asset", aid, {"nombre": obj.nombre}, ip=_ip(request))
    return obj


@app.post("/api/assets")
def create_asset(a: AssetCreate, request: Request, user: UserOut = Depends(require_modulo("activos", "importar", nivel="editar"))):
    db = SessionLocal()
    obj = Asset(id=("A" + str(uuid.uuid4())[:6]).upper(), **a.model_dump(), updated=datetime.utcnow())
    db.add(obj)
    db.commit()
    db.refresh(obj)
    db.close()
    log_action(user.username, "alta", "asset", obj.id, {"nombre": a.nombre, "tipo": a.tipo}, ip=_ip(request))
    return obj


@app.put("/api/assets/{aid}")
def update_asset(aid: str, a: AssetUpdate, request: Request, user: UserOut = Depends(require_modulo("activos", nivel="editar"))):
    db = SessionLocal()
    obj = db.query(Asset).filter(Asset.id == aid).first()
    if not obj:
        db.close()
        raise HTTPException(404)
    datos = a.model_dump(exclude_unset=True)
    cambios = {k: (getattr(obj, k), v) for k, v in datos.items() if str(getattr(obj, k, "")) != str(v)}
    for k, v in datos.items():
        setattr(obj, k, v)
    obj.updated = datetime.utcnow()
    registrar_historial(db, aid, user.username, "edicion", cambios)
    if "garantia" in cambios:
        _garantia_editada_en_ficha(db, obj, user.username)
    db.commit()
    db.refresh(obj)
    db.close()
    log_action(user.username, "modificacion", "asset", aid, cambios, ip=_ip(request))
    return obj


@app.delete("/api/assets/{aid}")
def delete_asset(aid: str, request: Request, user: UserOut = Depends(require_modulo(ELIMINAR_ACTIVOS, nivel="si"))):
    db = SessionLocal()
    obj = db.query(Asset).filter(Asset.id == aid).first()
    if not obj:
        db.close()
        raise HTTPException(404)
    nombre = obj.nombre
    borrar_datos_impresora(db, aid)
    borrar_datos_salud(db, aid)
    borrar_datos_monitor(db, aid)
    borrar_datos_garantia(db, aid)
    borrar_datos_ciclo(db, aid)
    borrar_datos_servidor(db, aid)
    db.delete(obj)
    db.commit()
    db.close()
    log_action(user.username, "eliminacion", "asset", aid, {"nombre": nombre}, ip=_ip(request))
    return {"status": "deleted"}


# ================================================================ sincronizacion de agentes
CAMPOS_LOG = ["nombre", "tipo", "marca", "modelo", "serial", "estado", "usuario", "usuario_alt",
              "ubicacion", "grupo", "red", "cpu", "ram", "disco", "ip", "so", "so_version",
              "so_arquitectura", "garantia", "comentarios", "monitores", "impresoras", "cifrado", "tpm"]
CAMPOS_SOLO_AGENTE = ("ip_publica", "mac", "gateway", "ou_ad", "ultimo_reinicio", "ultimo_login")


def _parse_sw(txt):
    d = {}
    for item in (txt or "").split("~~~"):
        if not item.strip():
            continue
        partes = item.split("|||")
        nom = partes[0].strip()
        if nom:
            d[nom] = partes[1].strip() if len(partes) > 1 else ""
    return d


def _log_sw(db, asset_id, ant, nuevo):
    viejos, nuevos = _parse_sw(ant), _parse_sw(nuevo)
    agente = "agente-automatico"
    if not viejos and len(nuevos) > 20:
        db.add(Historial(asset_id=asset_id, usuario=agente, campo="software_inventario", valor_ant="",
                         valor_new=str(len(nuevos)) + " programas relevados", accion="sincronizacion"))
        return
    for n, v in nuevos.items():
        if n not in viejos:
            db.add(Historial(asset_id=asset_id, usuario=agente, campo="software_instalado", valor_ant="",
                             valor_new=(n + " " + v).strip(), accion="sincronizacion"))
        elif viejos[n] != v:
            db.add(Historial(asset_id=asset_id, usuario=agente, campo="software_actualizado",
                             valor_ant=(n + " " + viejos[n]).strip(), valor_new=(n + " " + v).strip(),
                             accion="sincronizacion"))
    for n, v in viejos.items():
        if n not in nuevos:
            db.add(Historial(asset_id=asset_id, usuario=agente, campo="software_desinstalado",
                             valor_ant=(n + " " + v).strip(), valor_new="", accion="sincronizacion"))


def _aplicar_sync(a: AssetSync):
    if isinstance(a.software, list):
        def _lim(s):
            s = str(s or "").replace("|||", " ").replace("~~~", " ")
            return "".join(ch for ch in s if unicodedata.category(ch)[0] != "C").strip()
        regs = []
        for it in a.software:
            if isinstance(it, dict):
                nom, ver, fec = _lim(it.get("nombre") or it.get("name")), _lim(it.get("version")), _lim(it.get("fecha") or it.get("date"))
            else:
                nom, ver, fec = _lim(it), "", ""
            if nom:
                regs.append("%s|||%s|||%s" % (nom, ver, fec))
        a.software = "~~~".join(regs)
    if sede_de_nombre(a.nombre):   # LLAZ... = Azure (SEDES_POR_NOMBRE), aunque el agente diga otra cosa
        a.ubicacion = sede_de_nombre(a.nombre)
    salud, monitores, servidor = a.salud, a.monitores_detalle, a.servidor
    db = SessionLocal()
    obj = db.query(Asset).filter(Asset.serial == a.serial).first()
    if obj:
        for campo in ("garantia", "comentarios", "estado"):
            setattr(a, campo, getattr(obj, campo) or "")
        if usuario_fijado(db, obj.id):   # entregado por acta / asignado a mano: manda sobre el agente
            a.usuario = obj.usuario or ""
        datos = a.model_dump(exclude={"salud", "monitores_detalle", "servidor"})
        cambios = {}
        sw_ant = obj.software
        for k, v in datos.items():
            if k in CAMPOS_LOG and v is not None and str(v).strip() != "":
                cambios[k] = (getattr(obj, k, None) or "", v)
            # No pisar cifrado/tpm con vacio o "Sin acceso": la tarea local
            # corre sin elevacion y no puede leerlos, pero el arranque si.
            if k in ("cifrado", "tpm") and (v is None or str(v).strip() == "" or str(v).strip().lower().startswith("sin acceso")):
                continue
            # Los campos de red e identidad solo los manda el agente de Atlas: el inventario GLPI (que llega
            # despues en la misma corrida) no los trae y no tiene que borrarlos.
            if k in CAMPOS_SOLO_AGENTE and (v is None or str(v).strip() == ""):
                continue
            setattr(obj, k, v)
        obj.updated = datetime.utcnow()
        registrar_historial(db, obj.id, "agente-automatico", "sincronizacion", cambios)
        if "software" in datos:
            _log_sw(db, obj.id, sw_ant, datos.get("software"))
    else:
        obj = Asset(id=("A" + str(uuid.uuid4())[:6]).upper(), **a.model_dump(exclude={"salud", "monitores_detalle", "servidor"}),
                    updated=datetime.utcnow())
        db.add(obj)
        db.flush()
        registrar_historial(db, obj.id, "agente-automatico", "sincronizacion", {"alta": ("", a.nombre or a.serial)})
    if salud:
        guardar_salud(db, obj.id, salud)
    if monitores is not None and obj.tipo != "Monitor":
        procesar_monitores(db, obj, monitores)
    if servidor:
        guardar_servidor(db, obj.id, servidor)
    db.commit()
    db.close()


@app.post("/api/sync")
def sync_agent(a: AssetSync, x_sync_key: str = Header(default="")):
    if not _clave_ok(x_sync_key, config.SYNC_API_KEY):
        raise HTTPException(status_code=401, detail="Clave de sincronizacion invalida")
    _aplicar_sync(a)
    return {"status": "ok"}


# ================================================================ proyectos y tareas
TIPOS_PROY = ("Infraestructura", "Desarrollo", "Seguridad", "Migracion", "Documentacion", "Soporte")
ESTADOS_PROY = ("Planificado", "En curso", "Pausado", "Finalizado", "Cancelado")
PRIORIDADES = ("Alta", "Media", "Baja")
ESTADOS_TAREA = ("Pendiente", "En proceso", "Realizado")


class ProyectoIn(BaseModel):
    nombre:          str = Field(..., min_length=3, max_length=120)
    descripcion:     Optional[str] = ""
    tipo:            Optional[Literal[TIPOS_PROY]] = None
    estado:          Literal[ESTADOS_PROY] = "Planificado"
    prioridad:       Literal[PRIORIDADES] = "Media"
    sede:            Optional[str] = ""
    fecha_inicio:    Optional[str] = ""
    fecha_fin_est:   Optional[str] = ""
    avance:          Optional[int] = 0
    link_sharepoint: Optional[str] = ""
    comentarios:     Optional[str] = ""
    link_ticket:     Optional[str] = ""
    recursos:        Optional[str] = ""
    responsables:    Optional[list] = []
    activos:         Optional[list] = []

    @field_validator("link_sharepoint", "link_ticket", mode="after")
    @classmethod
    def _solo_http(cls, v):
        """Los links se muestran como href: solo http(s), nada de javascript: o data:."""
        v = (v or "").strip()
        if v and not re.match(r"^https?://[^\s<>\"']+$", v, re.I):
            raise ValueError("el link tiene que empezar con http:// o https://")
        return v


class TareaIn(BaseModel):
    titulo:       str = Field(..., min_length=1, max_length=250)
    estado:       Optional[Literal[ESTADOS_TAREA]] = "Pendiente"
    responsable:  Optional[str] = ""
    fecha_limite: Optional[str] = ""
    notas:        Optional[str] = ""
    completada:   Optional[bool] = False


def _proy_dict(db, p):
    resp = [r.responsable for r in db.query(ProyectoResponsable).filter(ProyectoResponsable.proyecto_id == p.id)]
    vinculos = [pa.asset_id for pa in db.query(ProyectoActivo).filter(ProyectoActivo.proyecto_id == p.id)]
    # Una sola consulta para todos los activos del proyecto (antes era una por activo: N+1).
    por_id = {a.id: a for a in db.query(Asset).filter(Asset.id.in_(vinculos))} if vinculos else {}
    acts = []
    for aid in vinculos:
        a = por_id.get(aid)
        acts.append({"id": aid, "nombre": a.nombre if a else "",
                     "tipo": a.tipo if a else "", "serial": a.serial if a else ""})
    tareas = [{"id": t.id, "titulo": t.titulo, "completada": t.completada == "1",
               "estado": t.estado or ("Realizado" if t.completada == "1" else "Pendiente"),
               "responsable": t.responsable or "", "fecha_limite": t.fecha_limite or "",
               "notas": t.notas or "", "completada_el": t.completada_el or "", "orden": t.orden or 0}
              for t in db.query(ProyectoTarea).filter(ProyectoTarea.proyecto_id == p.id).order_by(ProyectoTarea.orden)]
    hechas = len([t for t in tareas if t["completada"]])
    avance_calc = int(round(hechas * 100.0 / len(tareas))) if tareas else None
    return {"id": p.id, "nombre": p.nombre, "descripcion": p.descripcion, "tipo": p.tipo,
            "estado": p.estado, "prioridad": p.prioridad, "sede": p.sede,
            "fecha_inicio": p.fecha_inicio, "fecha_fin_est": p.fecha_fin_est,
            "avance": p.avance or 0, "link_sharepoint": p.link_sharepoint,
            "comentarios": p.comentarios, "creado": p.creado, "updated": p.updated,
            "numero": p.numero or "", "link_ticket": p.link_ticket or "", "recursos": p.recursos or "",
            "responsables": resp, "activos": acts,
            "tareas": tareas, "tiene_tareas": len(tareas) > 0,
            "tareas_hechas": hechas, "tareas_total": len(tareas),
            "avance_efectivo": avance_calc if avance_calc is not None else (p.avance or 0)}


def _destinatarios(db, pid):
    """Responsables del proyecto + creador del proyecto."""
    us = [r.responsable for r in db.query(ProyectoResponsable).filter(ProyectoResponsable.proyecto_id == pid)]
    p = db.query(Proyecto).filter(Proyecto.id == pid).first()
    if p and p.creado_por:
        us.append(p.creado_por)
    return us


def _guardar_rel(db, pid, responsables, activos):
    db.query(ProyectoResponsable).filter(ProyectoResponsable.proyecto_id == pid).delete()
    db.query(ProyectoActivo).filter(ProyectoActivo.proyecto_id == pid).delete()
    for r in (responsables or []):
        if str(r).strip():
            db.add(ProyectoResponsable(id=str(uuid.uuid4()), proyecto_id=pid, responsable=str(r).strip()))
    for a in (activos or []):
        if str(a).strip():
            db.add(ProyectoActivo(id=str(uuid.uuid4()), proyecto_id=pid, asset_id=str(a).strip()))


@app.get("/api/equipo")
def get_equipo(user: UserOut = Depends(require_modulo("proyectos"))):
    db = SessionLocal()
    us = db.query(User).filter(User.activo == "1").all()
    db.close()
    return sorted([{"username": u.username, "nombre": u.nombre} for u in us
                   if u.username not in ("admin", config.SUPERADMIN_EMAIL)], key=lambda x: x["nombre"] or "")


@app.get("/api/proyectos")
def list_proyectos(user: UserOut = Depends(require_modulo("proyectos"))):
    db = SessionLocal()
    out = [_proy_dict(db, p) for p in db.query(Proyecto).all()]
    db.close()
    out.sort(key=lambda x: (x["estado"] != "En curso", x["nombre"]))
    return out


@app.post("/api/proyectos")
def create_proyecto(p: ProyectoIn, request: Request, user: UserOut = Depends(require_modulo("proyectos", nivel="editar"))):
    db = SessionLocal()
    pid = ("P" + str(uuid.uuid4())[:6]).upper()
    ahora = datetime.utcnow().isoformat(timespec="seconds")
    pref = "PRY-%d-" % datetime.utcnow().year
    ultimos = [x.numero for x in db.query(Proyecto).filter(Proyecto.numero.like(pref + "%")).all() if x.numero]
    seq = 1
    if ultimos:
        try:
            seq = max(int(u.split("-")[-1]) for u in ultimos) + 1
        except ValueError:
            seq = len(ultimos) + 1
    d = p.model_dump(exclude={"responsables", "activos"})
    obj = Proyecto(id=pid, numero="%s%03d" % (pref, seq), creado=ahora, updated=ahora, creado_por=user.username, **d)
    db.add(obj)
    _guardar_rel(db, pid, p.responsables, p.activos)
    db.commit()
    res = _proy_dict(db, obj)
    db.close()
    log_action(user.username, "alta", "proyecto", pid, {"nombre": p.nombre}, ip=_ip(request))
    return res


@app.put("/api/proyectos/{pid}")
def update_proyecto(pid: str, p: ProyectoIn, request: Request, bg: BackgroundTasks,
                    user: UserOut = Depends(require_modulo("proyectos", nivel="editar"))):
    db = SessionLocal()
    obj = db.query(Proyecto).filter(Proyecto.id == pid).first()
    if not obj:
        db.close()
        raise HTTPException(404)
    estado_antes = obj.estado
    for k, v in p.model_dump(exclude={"responsables", "activos"}).items():
        setattr(obj, k, v)
    if not obj.numero:
        obj.numero = "PRY-%d-000" % datetime.utcnow().year
    obj.updated = datetime.utcnow().isoformat(timespec="seconds")
    _guardar_rel(db, pid, p.responsables, p.activos)
    db.commit()
    res = _proy_dict(db, obj)
    fin = (p.estado == "Finalizado" and estado_antes != "Finalizado")
    dest = _destinatarios(db, pid) if fin else []
    db.close()
    if fin and dest:
        bg.add_task(notificar_proyecto_finalizado, res, user.nombre or user.username, dest)
    log_action(user.username, "modificacion", "proyecto", pid, {"nombre": p.nombre}, ip=_ip(request))
    return res


@app.delete("/api/proyectos/{pid}")
def delete_proyecto(pid: str, request: Request, user: UserOut = Depends(require_modulo("proyectos", nivel="editar"))):
    db = SessionLocal()
    obj = db.query(Proyecto).filter(Proyecto.id == pid).first()
    if not obj:
        db.close()
        raise HTTPException(404)
    nombre = obj.nombre
    db.query(ProyectoResponsable).filter(ProyectoResponsable.proyecto_id == pid).delete()
    db.query(ProyectoActivo).filter(ProyectoActivo.proyecto_id == pid).delete()
    db.query(ProyectoTarea).filter(ProyectoTarea.proyecto_id == pid).delete()
    db.delete(obj)
    db.commit()
    db.close()
    log_action(user.username, "eliminacion", "proyecto", pid, {"nombre": nombre}, ip=_ip(request))
    return {"status": "deleted"}


@app.post("/api/proyectos/{pid}/tareas")
def crear_tarea(pid: str, t: TareaIn, request: Request, user: UserOut = Depends(require_modulo("proyectos", nivel="editar"))):
    db = SessionLocal()
    if not db.query(Proyecto).filter(Proyecto.id == pid).first():
        db.close()
        raise HTTPException(404)
    mx = db.query(ProyectoTarea).filter(ProyectoTarea.proyecto_id == pid).count()
    est = t.estado or "Pendiente"
    db.add(ProyectoTarea(id=("T" + str(uuid.uuid4())[:8]).upper(), proyecto_id=pid, titulo=t.titulo.strip(),
                         estado=est, completada="1" if est == "Realizado" else "0",
                         responsable=t.responsable or "", fecha_limite=t.fecha_limite or "",
                         notas=t.notas or "", orden=mx + 1, creado_por=user.username,
                         creado=datetime.utcnow().isoformat(timespec="seconds")))
    db.commit()
    res = _proy_dict(db, db.query(Proyecto).filter(Proyecto.id == pid).first())
    db.close()
    log_action(user.username, "alta_tarea", "proyecto", pid, {"tarea": t.titulo}, ip=_ip(request))
    return res


@app.put("/api/tareas/{tid}")
def editar_tarea(tid: str, t: TareaIn, user: UserOut = Depends(require_modulo("proyectos", nivel="editar"))):
    db = SessionLocal()
    obj = db.query(ProyectoTarea).filter(ProyectoTarea.id == tid).first()
    if not obj:
        db.close()
        raise HTTPException(404)
    antes = obj.completada
    obj.titulo = t.titulo.strip()
    obj.responsable = t.responsable or ""
    obj.fecha_limite = t.fecha_limite or ""
    obj.notas = t.notas or ""
    obj.estado = t.estado or ("Realizado" if t.completada else "Pendiente")
    obj.completada = "1" if obj.estado == "Realizado" else "0"
    if obj.completada == "1" and antes != "1":
        obj.completada_el = datetime.utcnow().isoformat(timespec="seconds")
    elif obj.completada == "0":
        obj.completada_el = ""
    pid = obj.proyecto_id
    db.commit()
    res = _proy_dict(db, db.query(Proyecto).filter(Proyecto.id == pid).first())
    db.close()
    return res


@app.delete("/api/tareas/{tid}")
def borrar_tarea(tid: str, request: Request, user: UserOut = Depends(require_modulo("proyectos", nivel="editar"))):
    db = SessionLocal()
    obj = db.query(ProyectoTarea).filter(ProyectoTarea.id == tid).first()
    if not obj:
        db.close()
        raise HTTPException(404)
    pid, titulo = obj.proyecto_id, obj.titulo
    db.delete(obj)
    db.commit()
    p = db.query(Proyecto).filter(Proyecto.id == pid).first()
    res = _proy_dict(db, p) if p else {"status": "deleted"}
    db.close()
    log_action(user.username, "baja_tarea", "proyecto", pid, {"tarea": titulo}, ip=_ip(request))
    return res


# ================================================================ garantias (detalle en garantias.py)
def _garantia_editada_en_ficha(db, obj, usuario):
    """La fecha de garantia cambiada a mano en la ficha pasa a ser una garantia manual (la consulta automatica no
    la pisa); vaciarla quita la carga manual."""
    from database import AssetGarantia
    nueva = garantias._fecha(obj.garantia)
    g = db.get(AssetGarantia, obj.id)
    if nueva:
        datos = {"inicio": g.inicio if g else None, "fin": nueva, "cobertura": g.cobertura if g else "",
                 "proveedor": g.proveedor if g else "", "contrato": g.contrato if g else "", "notas": g.notas if g else ""}
        garantias.guardar_manual(db, obj, datos, usuario)
    elif g is not None:
        db.delete(g)


@app.post("/api/assets/{aid}/garantia")
def consultar_garantia(aid: str, request: Request, user: UserOut = Depends(require_modulo("activos", nivel="editar"))):
    """Boton "Consultar ahora" de la ficha (Lenovo). Endpoint sincronico: corre en el threadpool."""
    db = SessionLocal()
    try:
        obj = db.query(Asset).filter(Asset.id == aid).first()
        if not obj:
            raise HTTPException(404)
        if not garantias.es_lenovo(obj):
            raise HTTPException(400, detail="Solo disponible para equipos Lenovo (marca: %s)" % (obj.marca or "sin marca"))
        from database import AssetGarantia
        g = db.get(AssetGarantia, aid)
        if g is not None and g.fuente == "manual":
            raise HTTPException(409, detail="Tiene una garantía cargada a mano: quitala para volver a consultar a Lenovo")
        anterior = obj.garantia or ""
        datos, err = garantias.consultar_lenovo(obj.serial)
        garantias.guardar_lenovo(db, obj, datos, err)
        db.commit()
        if err:
            raise HTTPException(422, detail="Lenovo no devolvió datos para esa serie" if err == "formato" else err)
        out = garantias.armar(obj, db.get(AssetGarantia, aid))
    finally:
        db.close()
    log_action(user.username, "consulta_garantia", "asset", aid,
               {"anterior": anterior, "nueva": out["fin"], "estado": out["estado"]}, ip=_ip(request))
    return {"garantia": out["fin"], "estado": "Vigente" if out["estado"] == "vigente" else "Vencida",
            "anterior": anterior, "cobertura": out["cobertura"], "detalle": out}


# ================================================================ GLPI Agent
_GLPI_PORTATIL = ("notebook", "laptop", "portable", "sub notebook", "convertible", "detachable", "tablet", "hand held")


def _gc(s):
    s = "" if s is None else str(s)
    s = re.sub(r'["\\/]', " ", s)
    s = "".join(ch for ch in s if unicodedata.category(ch)[0] != "C")
    return re.sub(r"\s+", " ", s).strip()


def _glpi_sede(nombre):
    n = (nombre or "").upper()
    for pat, sede in ((r"^(RESG|RSG)", "Resguarda"), (r"^CBA", "Cordoba"), (r"^NQN", "Neuquen"),
                      (r"^(RIMPTO|RADMIN|RAUDIT|RAUDI|RLEGALES)", "Rosario"),
                      (r"^(CIMPTO|CAUDIT|CADMIN|CLEGALES|CPYMES|CMULETO)", "Corrientes"),
                      (r"^(TIMPTO|TAUDIT|TADMIN|TSISTEMAS|PRECYTRANS)", "Tigre"),
                      (r"^(MIMPTO|MADMIN|MAUDIT|MLEGALES|MPYMES|MNMULETO)", "Mendoza")):
        if re.match(pat, n):
            return sede
    return "CABA"


def _glpi_fecha(f):
    f = str(f or "")
    m = re.match(r"(\d{4})-(\d{2})-(\d{2})", f)
    return "%s%s%s" % m.groups() if m else re.sub(r"\D", "", f)[:8]


def _glpi_cifrado(d):
    e = (d.get("encrypt_status") or "").lower()
    algo = (d.get("encrypt_algo") or "").strip().lower()
    if e == "yes":
        return "Cifrado"
    if e == "partially":
        return "Cifrando"
    if e == "no":
        return "Cifrado (proteccion off)" if algo and algo != "none" else "Sin cifrar"
    return ""


def _glpi_map(c, previo):
    bios = c.get("bios") or {}
    hw = c.get("hardware") or {}
    so = c.get("operatingsystem") or {}
    nombre = _gc(hw.get("name"))
    chasis = (hw.get("chassis_type") or "").strip().lower()
    virtual = (hw.get("vmsystem") or "Physical") != "Physical"
    if virtual or "server" in (so.get("full_name") or "").lower():
        tipo = "Servidor"
    elif chasis in _GLPI_PORTATIL:
        tipo = "Notebook"
    elif chasis:
        tipo = "CPU"
    else:
        tipo = previo.get("tipo") or "Notebook"
    mem = hw.get("memory") or 0
    discos = [s for s in (c.get("storages") or []) if (s.get("disksize") or 0) > 0]
    ip = ""
    for nw in (c.get("networks") or []):
        a = nw.get("ipaddress") or ""
        if a and not nw.get("virtualdev") and (nw.get("status") or "") == "up" and not a.startswith(("127.", "169.254.")):
            ip = a
            break
    us = (c.get("users") or [{}])[0]
    crudo = str(us.get("login") or hw.get("lastloggeduser") or "")
    login = _gc(crudo.split("\\")[-1])
    dominio = _gc(us.get("domain") or (crudo.split("\\")[0] if "\\" in crudo else ""))
    sw, vistos = [], set()
    for s in (c.get("softwares") or []):
        if s.get("system_category") not in ("application", None):
            continue
        nom = _gc(s.get("name"))
        nom = re.sub(r"\s*#\d+\s*$", "", nom)
        nom = re.sub(r"\s*\([A-Za-z]:.*$", "", nom).strip()
        if not nom or nom in vistos:
            continue
        vistos.add(nom)
        sw.append({"nombre": nom, "version": _gc(s.get("version")), "fecha": _glpi_fecha(s.get("install_date"))})
    cif = ""
    for d in (c.get("drives") or []):
        if (d.get("letter") or "").upper() == "C:":
            cif = _glpi_cifrado(d)
    arq = so.get("arch") or ""
    return {
        "nombre": nombre, "tipo": tipo, "serial": _gc(bios.get("ssn") or bios.get("msn")),
        "marca": _gc(bios.get("smanufacturer") or bios.get("mmanufacturer")),
        # smodel es el nombre comercial ("ThinkPad E14 Gen 6"); mmodel suele ser el codigo de placa o el
        # machine type de Lenovo ("21M80017AR"). Se prefiere el comercial, como hace el agente.
        "modelo": _gc(bios.get("smodel") or bios.get("mmodel")),
        "cpu": _gc(((c.get("cpus") or [{}])[0]).get("name")),
        "ram": ("%dGB" % round(mem / 1024.0)) if mem else "",
        "disco": " + ".join("%dGB" % round(s["disksize"] / 1000.0) for s in discos),
        "so": _gc(so.get("full_name")), "so_version": _gc(so.get("kernel_version")),
        "so_arquitectura": "64 bits" if "64" in arq else ("32 bits" if arq else ""),
        "grupo": "x64-based PC" if "64" in arq else (previo.get("grupo") or ""),
        "ip": ip, "red": _gc(so.get("dns_domain") or hw.get("workgroup")),
        "usuario": login or (previo.get("usuario") or ""),
        "usuario_alt": ("%s %s" % (dominio, login)).strip(),
        "ubicacion": _glpi_sede(nombre),
        "estado": "Activo", "garantia": "", "comentarios": "",
        "monitores": "|".join(x for x in (_gc("%s %s" % (m.get("manufacturer") or "", m.get("caption") or ""))
                                          for m in (c.get("monitors") or [])) if x),
        "impresoras": "|".join(x for x in (_gc(p.get("name")) for p in (c.get("printers") or [])) if x),
        "software": sw, "cifrado": cif, "tpm": "",
    }


def _glpi_resumen(c):
    av = c.get("antivirus") or []
    edr = "No instalado"
    for a in av:
        if "crowdstrike" in (a.get("name") or "").lower():
            edr = "Activo" if a.get("enabled") else "Inactivo"
    bat = (c.get("batteries") or [{}])[0]
    salud = None
    if bat.get("capacity") and bat.get("real_capacity"):
        salud = int(round(bat["real_capacity"] * 100.0 / bat["capacity"]))
    sin_cif = []
    for d in (c.get("drives") or []):
        if d.get("type") == "Local Disk" and re.match(r"^[A-Za-z]:$", d.get("letter") or ""):
            est = _glpi_cifrado(d)
            if est == "Sin cifrar":
                sin_cif.append(d.get("letter"))
            elif est == "Cifrado (proteccion off)":
                sin_cif.append(d.get("letter") + " (proteccion off)")
    so = c.get("operatingsystem") or {}
    hw = c.get("hardware") or {}
    bios = c.get("bios") or {}
    return {
        "antivirus": "; ".join("%s (%s%s)" % (_gc(a.get("name")), "activo" if a.get("enabled") else "inactivo",
                                              "" if a.get("uptodate", True) else ", desactualizado") for a in av),
        "edr": edr, "bateria_salud": salud,
        "acceso_remoto": ", ".join(sorted({_gc(r.get("type")) for r in (c.get("remote_mgmt") or []) if r.get("type")})),
        "discos": "; ".join("%s %dGB %s" % (_gc(s.get("model")), round((s.get("disksize") or 0) / 1000.0), _gc(s.get("type")))
                            for s in (c.get("storages") or [])),
        "volumenes_sin_cifrar": ", ".join(sin_cif),
        "office": "; ".join(_gc(li.get("name")) for li in (c.get("licenseinfos") or []) if "office" in (li.get("name") or "").lower()),
        "ultimo_arranque": _gc(so.get("boot_time")),
        "chasis": _gc(hw.get("chassis_type")), "virtual": _gc(hw.get("vmsystem")),
        "bios": "%s (%s)" % (_gc(bios.get("bversion")), _gc(bios.get("bdate"))),
        "os_build": ("%s %s" % (_gc(so.get("version")), _gc(so.get("service_pack")))).strip(),
        "actualizaciones": sum(1 for s in (c.get("softwares") or []) if s.get("system_category") in ("update", "security_update")),
    }


def _glpi_sanear(c):
    d = _json.loads(_json.dumps(c))
    (d.get("hardware") or {}).pop("winprodkey", None)
    for k in ("envs", "processes"):
        d.pop(k, None)
    for m in (d.get("monitors") or []):
        m.pop("base64", None)
    d["softwares"] = [s for s in (d.get("softwares") or [])
                      if s.get("system_category") in ("application", None, "update", "security_update")]
    return d


_GLPI_COLS = ("serial", "nombre", "fecha", "antivirus", "edr", "bateria_salud", "acceso_remoto", "discos",
              "volumenes_sin_cifrar", "office", "ultimo_arranque", "chasis", "virtual", "bios", "os_build", "actualizaciones")


@app.get("/api/glpi/resumen")
def glpi_resumen(user: UserOut = Depends(require_modulo(*MODULOS_LISTA_ACTIVOS))):
    db = SessionLocal()
    rows = db.query(AssetGlpi).all()
    db.close()
    return [{c: getattr(r, c) for c in _GLPI_COLS} for r in rows]


@app.post("/api/sync-glpi")
async def sync_glpi(request: Request, x_sync_key: str = Header(default="")):
    if not _clave_ok(x_sync_key, config.SYNC_API_KEY):
        raise HTTPException(status_code=401, detail="Clave de sincronizacion invalida")
    raw = await request.body()
    if len(raw) > 8 * 1024 * 1024:
        raise HTTPException(status_code=413, detail="Inventario demasiado grande")
    try:
        if "gzip" in (request.headers.get("content-encoding") or "").lower():
            raw = _gzip.decompress(raw)
        txt = raw.decode("utf-8-sig")
        data = _json.loads(txt[txt.find("{"):])
    except (OSError, ValueError):
        raise HTTPException(status_code=422, detail="JSON invalido") from None
    c = data.get("content", data) if isinstance(data, dict) else {}
    bios = c.get("bios") or {}
    serial = _gc(bios.get("ssn") or bios.get("msn"))
    if not serial or serial.upper() in ("DEFAULT STRING", "TO BE FILLED BY O.E.M.", "0", "00000000"):
        raise HTTPException(status_code=422, detail="Equipo sin serial valido")
    db = SessionLocal()
    prev = db.query(Asset).filter(Asset.serial == serial).first()
    previo = {"tipo": prev.tipo, "grupo": prev.grupo, "usuario": prev.usuario} if prev else {}
    db.close()
    m = _glpi_map(c, previo)
    _aplicar_sync(AssetSync(**m))
    db = SessionLocal()
    db.merge(AssetGlpi(serial=serial, nombre=m["nombre"], fecha=datetime.utcnow().isoformat(timespec="seconds"),
                       detalle=_json.dumps(_glpi_sanear(c), ensure_ascii=False), **_glpi_resumen(c)))
    db.commit()
    db.close()
    return {"status": "ok", "serial": serial, "tipo": m["tipo"], "ubicacion": m["ubicacion"]}


# ================================================================ tickets
@app.get("/api/tickets")
def list_tickets(user: UserOut = Depends(require_modulo("activos"))):
    db = SessionLocal()
    r = db.query(Ticket).all()
    db.close()
    return r


@app.post("/api/tickets")
def create_ticket(t: TicketIn, user: UserOut = Depends(require_modulo("activos", nivel="editar"))):
    db = SessionLocal()
    obj = Ticket(id="T-" + str(uuid.uuid4())[:6].upper(), fecha=str(date.today()), **t.model_dump())
    db.add(obj)
    db.commit()
    db.refresh(obj)
    db.close()
    log_action(user.username, "alta", "ticket", obj.id, t.model_dump())
    return obj


@app.put("/api/tickets/{tid}")
def update_ticket(tid: str, t: TicketIn, user: UserOut = Depends(require_modulo("activos", nivel="editar"))):
    db = SessionLocal()
    obj = db.query(Ticket).filter(Ticket.id == tid).first()
    if not obj:
        db.close()
        raise HTTPException(404)
    datos = t.model_dump()
    antes = {k: getattr(obj, k, None) for k in datos}
    for k, v in datos.items():
        setattr(obj, k, v)
    db.commit()
    db.refresh(obj)
    db.close()
    cambios = {k: {"antes": antes.get(k), "despues": v} for k, v in datos.items() if str(antes.get(k)) != str(v)}
    log_action(user.username, "modificacion", "ticket", tid, cambios)
    return obj


# ================================================================ adjuntos (contenido en la base, ADR-001)
MAX_MB = 10
TIPOS_ADJ = {".pdf": "application/pdf", ".jpg": "image/jpeg", ".jpeg": "image/jpeg", ".png": "image/png",
             ".gif": "image/gif", ".webp": "image/webp",
             ".xlsx": "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
             ".xls": "application/vnd.ms-excel",
             ".docx": "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
             ".doc": "application/msword", ".txt": "text/plain", ".csv": "text/csv"}


@app.get("/api/assets/{asset_id}/adjuntos")
def listar_adjuntos(asset_id: str, user: UserOut = Depends(require_modulo(*MODULOS_FICHA))):
    db = SessionLocal()
    items = (db.query(Adjunto).filter(Adjunto.asset_id == asset_id, Adjunto.activo == "1")
             .order_by(Adjunto.fecha.desc()).all())
    db.close()
    return [{"id": a.id, "nombre": a.nombre, "tipo": a.tipo, "tamano": a.tamano, "descripcion": a.descripcion,
             "subido_por": a.subido_por, "fecha": str(a.fecha)} for a in items]


@app.post("/api/assets/{asset_id}/adjuntos")
async def subir_adjunto(asset_id: str, file: UploadFile = File(...), descripcion: str = Form(""),
                        user: UserOut = Depends(require_modulo("activos", nivel="editar"))):
    ext = os.path.splitext(file.filename or "")[1].lower()
    if ext not in TIPOS_ADJ:
        raise HTTPException(400, "Extension no permitida: %s" % ext)
    if not re.fullmatch(r"[A-Za-z0-9_-]{1,40}", asset_id or ""):
        raise HTTPException(400, "Identificador de activo invalido")
    contenido = await file.read(MAX_MB * 1024 * 1024 + 1)
    if len(contenido) > MAX_MB * 1024 * 1024:
        raise HTTPException(400, "El archivo supera el maximo de %d MB" % MAX_MB)
    aid = str(uuid.uuid4())
    db = SessionLocal()
    db.add(Adjunto(id=aid, asset_id=asset_id, nombre=file.filename, contenido=contenido, tipo=ext.replace(".", ""),
                   tamano=len(contenido), descripcion=descripcion, subido_por=user.username))
    registrar_historial(db, asset_id, user.username, "adjunto", {"archivo_adjunto": ("", file.filename)})
    db.commit()
    db.close()
    log_action(user.username, "alta", "adjunto", aid, {"asset": asset_id, "archivo": file.filename})
    return {"status": "ok", "id": aid}


@app.get("/api/adjuntos/{adj_id}/descargar")
def descargar_adjunto(adj_id: str, user: UserOut = Depends(require_modulo(*MODULOS_FICHA))):
    db = SessionLocal()
    a = db.query(Adjunto).filter(Adjunto.id == adj_id, Adjunto.activo == "1").first()
    contenido = a.contenido if a else None
    db.close()
    if contenido is None:
        raise HTTPException(404, "Archivo no encontrado")
    tipo = TIPOS_ADJ.get("." + (a.tipo or ""), "application/octet-stream")
    return Response(content=contenido, media_type=tipo, headers={
        "Content-Disposition": "attachment; filename*=UTF-8''" + quote(a.nombre or "adjunto"),
        "X-Content-Type-Options": "nosniff"})


@app.delete("/api/adjuntos/{adj_id}")
def borrar_adjunto(adj_id: str, user: UserOut = Depends(require_modulo("activos", nivel="editar"))):
    db = SessionLocal()
    a = db.query(Adjunto).filter(Adjunto.id == adj_id).first()
    if not a:
        db.close()
        raise HTTPException(404)
    a.activo = "0"
    nombre = a.nombre
    registrar_historial(db, a.asset_id, user.username, "adjunto", {"archivo_eliminado": (nombre, "")})
    db.commit()
    db.close()
    log_action(user.username, "baja", "adjunto", adj_id, {"archivo": nombre})
    return {"status": "ok"}


# ================================================================ tendencias
def tomar_snapshot(db):
    """Guarda las metricas del inventario de hoy. Devuelve la cantidad de filas."""
    ahora = datetime.utcnow()
    assets = db.query(Asset).all()
    filas = [("total_activos", "total", len(assets))]
    for metrica, campo, vacio in (("activos_por_sede", "ubicacion", "Sin sede"),
                                  ("activos_por_tipo", "tipo", "Sin tipo"),
                                  ("activos_por_estado", "estado", "Sin estado")):
        conteo = {}
        for a in assets:
            k = (getattr(a, campo) or "").strip() or vacio
            conteo[k] = conteo.get(k, 0) + 1
        filas += [(metrica, k, n) for k, n in conteo.items()]
    asignados = sum(1 for a in assets if (a.usuario or "").strip())
    filas += [("activos_asignados", "asignados", asignados), ("activos_asignados", "sin_asignar", len(assets) - asignados)]
    filas.append(("equipos_sin_reportar", "mas_30_dias",
                  sum(1 for a in assets if a.updated and (ahora - a.updated).days > 30)))
    for metrica, clave, valor in filas:
        db.add(Snapshot(fecha=ahora, metrica=metrica, clave=str(clave), valor=int(valor)))
    db.commit()
    return len(filas)


def _loop_snapshots():
    """Toma un snapshot si el ultimo tiene mas de SNAPSHOT_DIAS dias. Revisa cada 6 horas."""
    while True:
        try:
            db = SessionLocal()
            ultimo = db.query(func.max(Snapshot.fecha)).scalar()
            if ultimo is None or (datetime.utcnow() - ultimo).days >= config.SNAPSHOT_DIAS:
                tomar_snapshot(db)
                log.info("snapshot.ok", extra={"event": "snapshot"})
            db.close()
        except Exception as e:
            log.error("snapshot.error %s", type(e).__name__, extra={"event": "snapshot"})
        time.sleep(6 * 3600)


@app.get("/api/tendencias")
def get_tendencias(metrica: str = "", user: UserOut = Depends(require_modulo("tendencias"))):
    db = SessionLocal()
    q = db.query(Snapshot)
    if metrica:
        q = q.filter(Snapshot.metrica == metrica)
    items = q.order_by(Snapshot.fecha.asc()).all()
    db.close()
    return [{"fecha": str(s.fecha)[:10], "metrica": s.metrica, "clave": s.clave, "valor": s.valor} for s in items]


@app.get("/api/tendencias/metricas")
def get_metricas_disponibles(user: UserOut = Depends(require_modulo("tendencias"))):
    db = SessionLocal()
    items = db.query(Snapshot.metrica).distinct().all()
    db.close()
    return sorted([i[0] for i in items])


@app.post("/api/tendencias/snapshot")
def forzar_snapshot(request: Request, user: UserOut = Depends(require_modulo("accesos", nivel="administrar"))):
    db = SessionLocal()
    n = tomar_snapshot(db)
    db.close()
    log_action(user.username, "snapshot", "tendencias", "", {"metricas": n}, ip=_ip(request))
    return {"status": "ok", "metricas": n}


# ================================================================ frontend y archivos estaticos
# Fuentes servidas por la app (DT-08): tipo correcto aunque el sistema no lo tenga registrado.
mimetypes.add_type("font/woff2", ".woff2")

_RESERVADAS = ("api/", "auth/", "maestro/", "metrics")


def _estatico(base, relativa):
    """Archivo dentro de base, o None (evita salirse de la carpeta con ..)."""
    raiz = os.path.realpath(base)
    ruta = os.path.realpath(os.path.join(raiz, relativa))
    return ruta if ruta.startswith(raiz + os.sep) and os.path.isfile(ruta) else None


@app.get("/agent_linux.sh")
def get_agent_linux():
    ruta = _estatico(config.AGENTE_DIR, "agent_linux.sh")
    if not ruta:
        raise HTTPException(404)
    return FileResponse(ruta, media_type="text/plain")


@app.get("/{full_path:path}")
def frontend(full_path: str):
    if full_path.startswith(_RESERVADAS):
        raise HTTPException(status_code=404, detail="Not Found")
    ruta = _estatico(config.FRONTEND_DIST, full_path) if full_path else None
    if ruta:
        return FileResponse(ruta)
    index = _estatico(config.FRONTEND_DIST, "index.html")
    if not index:
        raise HTTPException(status_code=404, detail="Frontend no compilado")
    return FileResponse(index)
