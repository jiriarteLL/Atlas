import re
# -*- coding: utf-8 -*-
from fastapi import FastAPI, HTTPException, Header, Depends, Request, BackgroundTasks
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from pydantic import BaseModel, Field, field_validator
from typing import Optional, Literal, Union
import unicodedata
from database import SessionLocal, Asset, Ticket, Proyecto, ProyectoResponsable, ProyectoActivo, ProyectoTarea
from datetime import datetime, date
import uuid, os
from dotenv import load_dotenv
load_dotenv(override=True)
from auth import auth_router, get_current_user, require_admin, require_escritura, User, UserOut, hash_password
from excel_sync import update_excel
from historial import Historial
from excel_stock import actualizar_serial
import gzip as _gzip, json as _json
from sqlalchemy import text as _sqltext
from mailer import notificar_tarea_completada, notificar_proyecto_finalizado

app = FastAPI(title="AssetManager API", docs_url=None, redoc_url=None, openapi_url=None)  # sin documentacion publica de la API
app.include_router(auth_router)
app.add_middleware(CORSMiddleware, allow_origins=["http://192.168.100.116:8000","https://192.168.100.116:8443","http://192.168.100.116:8001","https://192.168.100.116:8444","http://192.168.0.88:8000"],
    allow_methods=["*"], allow_headers=["*"])


TIPOS_OK = ("Notebook", "Monitor", "Impresora", "Servidor", "Switch", "UPS", "CPU")
ESTADOS_OK = ("Activo", "Mantenimiento", "Dado de baja",
              "Libre", "Stock", "Robado")

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

class TicketIn(BaseModel):
    activo:     str
    titulo:     str
    estado:     Optional[str] = "Abierto"
    prioridad:  Optional[str] = "Media"
    comentario: Optional[str] = ""


def registrar_historial(db, asset_id, usuario, accion, cambios):
    for campo, (valor_ant, valor_new) in cambios.items():
        if str(valor_ant) != str(valor_new):
            h = Historial(
                asset_id=asset_id,
                usuario=usuario,
                campo=campo,
                valor_ant=str(valor_ant) if valor_ant else "",
                valor_new=str(valor_new) if valor_new else "",
                accion=accion
            )
            db.add(h)

from audit import log_action

@app.get("/api/assets/{asset_id}/historial")
def get_historial(asset_id: str):
    db = SessionLocal()
    items = db.query(Historial).filter(Historial.asset_id == asset_id).order_by(Historial.fecha.desc()).all()
    db.close()
    return [{"id": h.id, "fecha": h.fecha, "usuario": h.usuario, "campo": h.campo, "valor_ant": h.valor_ant, "valor_new": h.valor_new, "accion": h.accion} for h in items]
@app.get("/api/assets")
def list_assets():
    db = SessionLocal()
    r = db.query(Asset).all()
    db.close()
    return r

@app.get("/api/assets/{aid}/ficha")
def ver_ficha_asset(aid: str, request: Request, user: UserOut = Depends(get_current_user)):
    db = SessionLocal()
    obj = db.query(Asset).filter(Asset.id==aid).first()
    db.close()
    if not obj: raise HTTPException(404)
    log_action(user.username, "ver_ficha", "asset", aid, {"nombre": obj.nombre}, ip=(request.client.host if request.client else ""))
    return obj

@app.post("/api/assets")
def create_asset(a: AssetCreate, request: Request, bg: BackgroundTasks, user: UserOut = Depends(require_escritura)):
    db = SessionLocal()
    obj = Asset(id=("A"+str(uuid.uuid4())[:6]).upper(), **a.model_dump(), updated=datetime.utcnow())
    db.add(obj); db.commit()
    id_creado = obj.id
    db.close()
    bg.add_task(actualizar_serial, a.serial, a.usuario or "", a.nombre or "", a.ubicacion or "")
    log_action(user.username, "alta", "asset", id_creado, {"nombre": a.nombre, "tipo": a.tipo}, ip=(request.client.host if request.client else ""))
    return obj

@app.put("/api/assets/{aid}")
def update_asset(aid: str, a: AssetUpdate, request: Request, bg: BackgroundTasks, user: UserOut = Depends(require_escritura)):
    db = SessionLocal()
    obj = db.query(Asset).filter(Asset.id==aid).first()
    if not obj: raise HTTPException(404)
    datos = a.model_dump(exclude_unset=True)
    cambios = {k: (getattr(obj, k), v) for k,v in datos.items() if str(getattr(obj, k, "")) != str(v)}
    for k,v in datos.items(): setattr(obj, k, v)
    obj.updated = datetime.utcnow()
    registrar_historial(db, aid, "web", "edicion", cambios)
    _ser, _usr, _nom, _sed = obj.serial, obj.usuario, obj.nombre, obj.ubicacion
    db.commit(); db.close()
    bg.add_task(actualizar_serial, _ser, _usr or "", _nom or "", _sed or "")
    log_action(user.username, "modificacion", "asset", aid, cambios, ip=(request.client.host if request.client else ""))
    return obj


@app.delete("/api/assets/{aid}")
def delete_asset(aid: str, request: Request, user: UserOut = Depends(require_admin)):
    db = SessionLocal()
    obj = db.query(Asset).filter(Asset.id==aid).first()
    if not obj: raise HTTPException(404)
    nombre = obj.nombre
    db.delete(obj); db.commit(); db.close()
    log_action(user.username, "eliminacion", "asset", aid, {"nombre": nombre}, ip=(request.client.host if request.client else ""))
    return {"status": "deleted"}

@app.post("/api/sync")
def sync_agent(a: AssetSync, x_sync_key: str = Header(default="")):
    _k = os.getenv("SYNC_API_KEY", "")
    if not _k or x_sync_key != _k:
        raise HTTPException(status_code=401, detail="Clave de sincronizacion invalida")
    if isinstance(a.software, list):
        def _lim(s):
            s = str(s or "").replace("|||", " ").replace("~~~", " ")
            return "".join(ch for ch in s if unicodedata.category(ch)[0] != "C").strip()
        regs = []
        for it in a.software:
            if isinstance(it, dict):
                nom = _lim(it.get("nombre") or it.get("name"))
                ver = _lim(it.get("version"))
                fec = _lim(it.get("fecha") or it.get("date"))
            else:
                nom, ver, fec = _lim(it), "", ""
            if nom:
                regs.append("%s|||%s|||%s" % (nom, ver, fec))
        a.software = "~~~".join(regs)
    db = SessionLocal()
    obj = db.query(Asset).filter(Asset.serial==a.serial).first()
    if obj:
        for _campo in ("garantia", "comentarios", "estado"):
            setattr(a, _campo, getattr(obj, _campo) or "")

    CAMPOS_LOG = ["nombre","tipo","marca","modelo","serial","estado","usuario","usuario_alt",
                  "ubicacion","grupo","red","cpu","ram","disco","ip","so","so_version",
                  "so_arquitectura","garantia","comentarios","monitores","impresoras","cifrado","tpm"]

    def _parse_sw(txt):
        d = {}
        for item in (txt or "").split("~~~"):
            if not item.strip():
                continue
            partes = item.split("|||")
            nom = partes[0].strip()
            ver = partes[1].strip() if len(partes) > 1 else ""
            if nom:
                d[nom] = ver
        return d

    def _log_sw(dbs, asset_id, ant, nuevo):
        viejos, nuevos = _parse_sw(ant), _parse_sw(nuevo)
        if not viejos and len(nuevos) > 20:
            dbs.add(Historial(asset_id=asset_id, usuario="agente-automatico",
                              campo="software_inventario", valor_ant="",
                              valor_new=str(len(nuevos)) + " programas relevados",
                              accion="sincronizacion"))
            return
        for n, v in nuevos.items():
            if n not in viejos:
                dbs.add(Historial(asset_id=asset_id, usuario="agente-automatico",
                                  campo="software_instalado", valor_ant="",
                                  valor_new=(n + " " + v).strip(), accion="sincronizacion"))
            elif viejos[n] != v:
                dbs.add(Historial(asset_id=asset_id, usuario="agente-automatico",
                                  campo="software_actualizado",
                                  valor_ant=(n + " " + viejos[n]).strip(),
                                  valor_new=(n + " " + v).strip(), accion="sincronizacion"))
        for n, v in viejos.items():
            if n not in nuevos:
                dbs.add(Historial(asset_id=asset_id, usuario="agente-automatico",
                                  campo="software_desinstalado",
                                  valor_ant=(n + " " + v).strip(), valor_new="",
                                  accion="sincronizacion"))

    if obj:
        datos = a.model_dump()
        cambios = {}
        sw_ant = obj.software
        for k, v in datos.items():
            if k in CAMPOS_LOG:
                ant = getattr(obj, k, None)
                if v is not None and str(v).strip() != "":
                    cambios[k] = (ant or "", v)
            # No pisar cifrado/tpm con vacio o "Sin acceso": la tarea local
            # corre sin elevacion y no puede leerlos, pero el arranque si.
            if k in ("cifrado","tpm") and (v is None or str(v).strip() == "" or str(v).strip().lower().startswith("sin acceso")):
                continue
            setattr(obj, k, v)
        obj.updated = datetime.utcnow()
        registrar_historial(db, obj.id, "agente-automatico", "sincronizacion", cambios)
        if "software" in datos:
            _log_sw(db, obj.id, sw_ant, datos.get("software"))
    else:
        obj = Asset(id=("A"+str(uuid.uuid4())[:6]).upper(), **a.model_dump(), updated=datetime.utcnow())
        db.add(obj)
        db.flush()
        registrar_historial(db, obj.id, "agente-automatico", "sincronizacion", {"alta": ("", a.nombre or a.serial)})
    db.commit(); db.close()
    return {"status": "ok"}


TIPOS_PROY = ("Infraestructura", "Desarrollo", "Seguridad", "Migracion", "Documentacion", "Soporte")
ESTADOS_PROY = ("Planificado", "En curso", "Pausado", "Finalizado", "Cancelado")
PRIORIDADES = ("Alta", "Media", "Baja")

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

def _proy_dict(db, p):
    resp = [r.responsable for r in db.query(ProyectoResponsable).filter(ProyectoResponsable.proyecto_id == p.id)]
    acts = []
    for pa in db.query(ProyectoActivo).filter(ProyectoActivo.proyecto_id == p.id):
        a = db.query(Asset).filter(Asset.id == pa.asset_id).first()
        acts.append({"id": pa.asset_id,
                     "nombre": a.nombre if a else "",
                     "tipo": a.tipo if a else "",
                     "serial": a.serial if a else ""})
    tareas = [{"id": t.id, "titulo": t.titulo, "completada": t.completada == "1",
               "estado": t.estado or ("Realizado" if t.completada == "1" else "Pendiente"),
               "responsable": t.responsable or "", "fecha_limite": t.fecha_limite or "",
               "notas": t.notas or "", "completada_el": t.completada_el or "", "orden": t.orden or 0}
              for t in db.query(ProyectoTarea).filter(ProyectoTarea.proyecto_id == p.id)
                         .order_by(ProyectoTarea.orden)]
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

def _destinatarios(db, pid, tarea=None):
    """Responsables del proyecto + creador del proyecto + creador y responsable de la tarea."""
    us = [r.responsable for r in db.query(ProyectoResponsable).filter(ProyectoResponsable.proyecto_id == pid)]
    p = db.query(Proyecto).filter(Proyecto.id == pid).first()
    if p and p.creado_por:
        us.append(p.creado_por)
    if tarea is not None:
        if tarea.responsable:
            us.append(tarea.responsable)
        if tarea.creado_por:
            us.append(tarea.creado_por)
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
def get_equipo():
    db = SessionLocal()
    us = db.query(User).filter(User.activo == "1").all()
    db.close()
    return sorted([{"username": u.username, "nombre": u.nombre}
                   for u in us if u.username != "admin"], key=lambda x: x["nombre"])

@app.get("/api/proyectos")
def list_proyectos():
    db = SessionLocal()
    out = [_proy_dict(db, p) for p in db.query(Proyecto).all()]
    db.close()
    out.sort(key=lambda x: (x["estado"] != "En curso", x["nombre"]))
    return out

@app.post("/api/proyectos")
def create_proyecto(p: ProyectoIn, request: Request, user: UserOut = Depends(require_escritura)):
    db = SessionLocal()
    pid = ("P" + str(uuid.uuid4())[:6]).upper()
    ahora = datetime.utcnow().isoformat(timespec="seconds")
    anio = datetime.utcnow().year
    pref = "PRY-%d-" % anio
    ultimos = [x.numero for x in db.query(Proyecto).filter(Proyecto.numero.like(pref + "%")).all() if x.numero]
    seq = 1
    if ultimos:
        try:
            seq = max(int(u.split("-")[-1]) for u in ultimos) + 1
        except Exception:
            seq = len(ultimos) + 1
    numero = "%s%03d" % (pref, seq)
    d = p.model_dump(exclude={"responsables", "activos"})
    obj = Proyecto(id=pid, numero=numero, creado=ahora, updated=ahora, creado_por=user.username, **d)
    db.add(obj)
    _guardar_rel(db, pid, p.responsables, p.activos)
    db.commit()
    res = _proy_dict(db, obj)
    db.close()
    log_action(user.username, "alta", "proyecto", pid, {"nombre": p.nombre},
               ip=(request.client.host if request.client else ""))
    return res

@app.put("/api/proyectos/{pid}")
def update_proyecto(pid: str, p: ProyectoIn, request: Request, bg: BackgroundTasks, user: UserOut = Depends(require_escritura)):
    db = SessionLocal()
    obj = db.query(Proyecto).filter(Proyecto.id == pid).first()
    if not obj:
        db.close(); raise HTTPException(404)
    estado_antes = obj.estado
    for k, v2 in p.model_dump(exclude={"responsables", "activos"}).items():
        setattr(obj, k, v2)
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
    log_action(user.username, "modificacion", "proyecto", pid, {"nombre": p.nombre},
               ip=(request.client.host if request.client else ""))
    return res

@app.delete("/api/proyectos/{pid}")
def delete_proyecto(pid: str, request: Request, user: UserOut = Depends(require_escritura)):
    db = SessionLocal()
    obj = db.query(Proyecto).filter(Proyecto.id == pid).first()
    if not obj:
        db.close(); raise HTTPException(404)
    nombre = obj.nombre
    db.query(ProyectoResponsable).filter(ProyectoResponsable.proyecto_id == pid).delete()
    db.query(ProyectoActivo).filter(ProyectoActivo.proyecto_id == pid).delete()
    db.query(ProyectoTarea).filter(ProyectoTarea.proyecto_id == pid).delete()
    db.delete(obj)
    db.commit(); db.close()
    log_action(user.username, "eliminacion", "proyecto", pid, {"nombre": nombre},
               ip=(request.client.host if request.client else ""))
    return {"status": "deleted"}


ESTADOS_TAREA = ("Pendiente", "En proceso", "Realizado")

class TareaIn(BaseModel):
    titulo:       str = Field(..., min_length=1, max_length=250)
    estado:       Optional[Literal[ESTADOS_TAREA]] = "Pendiente"
    responsable:  Optional[str] = ""
    fecha_limite: Optional[str] = ""
    notas:        Optional[str] = ""
    completada:   Optional[bool] = False

@app.post("/api/proyectos/{pid}/tareas")
def crear_tarea(pid: str, t: TareaIn, request: Request, user: UserOut = Depends(require_escritura)):
    db = SessionLocal()
    if not db.query(Proyecto).filter(Proyecto.id == pid).first():
        db.close(); raise HTTPException(404)
    mx = db.query(ProyectoTarea).filter(ProyectoTarea.proyecto_id == pid).count()
    tid = ("T" + str(uuid.uuid4())[:8]).upper()
    est = t.estado or "Pendiente"
    db.add(ProyectoTarea(id=tid, proyecto_id=pid, titulo=t.titulo.strip(),
                         estado=est, completada="1" if est == "Realizado" else "0",
                         responsable=t.responsable or "", fecha_limite=t.fecha_limite or "",
                         notas=t.notas or "", orden=mx + 1, creado_por=user.username,
                         creado=datetime.utcnow().isoformat(timespec="seconds")))
    db.commit()
    p = db.query(Proyecto).filter(Proyecto.id == pid).first()
    res = _proy_dict(db, p)
    db.close()
    log_action(user.username, "alta_tarea", "proyecto", pid, {"tarea": t.titulo},
               ip=(request.client.host if request.client else ""))
    return res

@app.put("/api/tareas/{tid}")
def editar_tarea(tid: str, t: TareaIn, request: Request, bg: BackgroundTasks, user: UserOut = Depends(require_escritura)):
    db = SessionLocal()
    obj = db.query(ProyectoTarea).filter(ProyectoTarea.id == tid).first()
    if not obj:
        db.close(); raise HTTPException(404)
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
    p = db.query(Proyecto).filter(Proyecto.id == pid).first()
    res = _proy_dict(db, p)
    recien = (obj.completada == "1" and antes != "1")
    dest = _destinatarios(db, pid, obj) if recien else []
    titulo_t = obj.titulo
    db.close()
    return res

@app.delete("/api/tareas/{tid}")
def borrar_tarea(tid: str, request: Request, user: UserOut = Depends(require_escritura)):
    db = SessionLocal()
    obj = db.query(ProyectoTarea).filter(ProyectoTarea.id == tid).first()
    if not obj:
        db.close(); raise HTTPException(404)
    pid, titulo = obj.proyecto_id, obj.titulo
    db.delete(obj); db.commit()
    p = db.query(Proyecto).filter(Proyecto.id == pid).first()
    res = _proy_dict(db, p) if p else {"status": "deleted"}
    db.close()
    log_action(user.username, "baja_tarea", "proyecto", pid, {"tarea": titulo},
               ip=(request.client.host if request.client else ""))
    return res

import urllib.request as _ureq, ssl as _ssl, json as _json

_CTX = _ssl.create_default_context()
_HDR_LNV = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 Chrome/120 Safari/537.36",
            "Accept": "text/html,application/xhtml+xml"}

def _lenovo_garantia(serial):
    """Devuelve (fecha_fin, estado, error). Scraping del portal publico de Lenovo."""
    s = str(serial or "").strip().upper()
    if s in ("", "-", "N/A"):
        return None, None, "Serial vacio"
    url = "https://pcsupport.lenovo.com/ar/es/products/%s/warranty" % s
    try:
        rq = _ureq.Request(url, headers=_HDR_LNV)
        with _ureq.urlopen(rq, timeout=25, context=_CTX) as r:
            html = r.read().decode("utf-8", "ignore")
    except Exception as e:
        return None, None, "No se pudo consultar (%s)" % type(e).__name__
    fin, activa = None, False
    m = re.search(r'"BaseUpmaWarranties"\s*:\s*(\[.*?\])', html)
    if m:
        try:
            for w in _json.loads(m.group(1)):
                e = w.get("End")
                if e and (fin is None or e > fin):
                    fin = e
                    activa = (w.get("StatusV2") == "Active")
        except Exception:
            pass
    if not fin:
        return None, None, "Lenovo no devolvio datos para ese serial"
    return fin, ("Vigente" if activa else "Vencida"), None

@app.post("/api/assets/{aid}/garantia")
def consultar_garantia(aid: str, request: Request, user: UserOut = Depends(get_current_user)):
    db = SessionLocal()
    obj = db.query(Asset).filter(Asset.id == aid).first()
    if not obj:
        db.close(); raise HTTPException(404)
    marca = (obj.marca or "").upper()
    if "LENOVO" not in marca:
        db.close()
        raise HTTPException(400, detail="Solo disponible para equipos Lenovo (marca: %s)" % (obj.marca or "sin marca"))
    fin, estado, err = _lenovo_garantia(obj.serial)
    if err:
        db.close(); raise HTTPException(422, detail=err)
    anterior = obj.garantia or ""
    obj.garantia = fin
    obj.updated = datetime.utcnow()
    db.commit(); db.close()
    log_action(user.username, "consulta_garantia", "asset", aid,
               {"anterior": anterior, "nueva": fin, "estado": estado},
               ip=(request.client.host if request.client else ""))
    return {"garantia": fin, "estado": estado, "anterior": anterior}

@app.get("/api/garantias/vencimientos")
def vencimientos(dias: int = 90):
    from datetime import date, timedelta
    hoy = date.today()
    lim = hoy + timedelta(days=dias)
    db = SessionLocal()
    out = []
    for a in db.query(Asset).filter(Asset.garantia != "").all():
        try:
            y, m, d = map(int, str(a.garantia).split("-")[:3])
            f = date(y, m, d)
        except Exception:
            continue
        if hoy <= f <= lim:
            out.append({"id": a.id, "nombre": a.nombre or "", "serial": a.serial or "",
                        "usuario": a.usuario or "", "sede": a.ubicacion or "",
                        "modelo": a.modelo or "", "garantia": a.garantia,
                        "dias": (f - hoy).days})
    db.close()
    out.sort(key=lambda x: x["dias"])
    return out


# ===================== GLPI Agent =====================
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
        "modelo": _gc(bios.get("mmodel") or bios.get("smodel")),
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
        "monitores": "|".join(x for x in (_gc("%s %s" % (m.get("manufacturer") or "", m.get("caption") or "")) for m in (c.get("monitors") or [])) if x),
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
        "office": "; ".join(_gc(l.get("name")) for l in (c.get("licenseinfos") or []) if "office" in (l.get("name") or "").lower()),
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

@app.get("/api/glpi/resumen")
def glpi_resumen(user: UserOut = Depends(get_current_user)):
    db = SessionLocal()
    rows = db.execute(_sqltext("""SELECT serial, nombre, fecha, antivirus, edr, bateria_salud, acceso_remoto,
        discos, volumenes_sin_cifrar, office, ultimo_arranque, chasis, virtual, bios, os_build, actualizaciones
        FROM asset_glpi""")).mappings().all()
    db.close()
    return [dict(r) for r in rows]

@app.post("/api/sync-glpi")
async def sync_glpi(request: Request, x_sync_key: str = Header(default="")):
    _k = os.getenv("SYNC_API_KEY", "")
    if not _k or x_sync_key != _k:
        raise HTTPException(status_code=401, detail="Clave de sincronizacion invalida")
    raw = await request.body()
    if len(raw) > 8 * 1024 * 1024:
        raise HTTPException(status_code=413, detail="Inventario demasiado grande")
    if "gzip" in (request.headers.get("content-encoding") or "").lower():
        raw = _gzip.decompress(raw)
    try:
        txt = raw.decode("utf-8-sig")
        data = _json.loads(txt[txt.find("{"):])
    except Exception:
        raise HTTPException(status_code=422, detail="JSON invalido")
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
    sync_agent(AssetSync(**m), x_sync_key=x_sync_key)
    r = _glpi_resumen(c)
    db = SessionLocal()
    db.execute(_sqltext("""INSERT OR REPLACE INTO asset_glpi
        (serial, nombre, fecha, antivirus, edr, bateria_salud, acceso_remoto, discos, volumenes_sin_cifrar,
         office, ultimo_arranque, chasis, virtual, bios, os_build, actualizaciones, detalle)
        VALUES (:serial, :nombre, :fecha, :antivirus, :edr, :bateria_salud, :acceso_remoto, :discos,
         :volumenes_sin_cifrar, :office, :ultimo_arranque, :chasis, :virtual, :bios, :os_build,
         :actualizaciones, :detalle)"""),
        dict(r, serial=serial, nombre=m["nombre"], fecha=datetime.utcnow().isoformat(timespec="seconds"),
             detalle=_json.dumps(_glpi_sanear(c), ensure_ascii=False)))
    db.commit()
    db.close()
    return {"status": "ok", "serial": serial, "tipo": m["tipo"], "ubicacion": m["ubicacion"]}

@app.get("/api/tickets")
def list_tickets():
    db = SessionLocal()
    r = db.query(Ticket).all()
    db.close()
    return r

@app.post("/api/tickets")
def create_ticket(t: TicketIn, usuario: str = "", user: UserOut = Depends(require_escritura)):
    usuario = user.username
    db = SessionLocal()
    obj = Ticket(id="T-"+str(uuid.uuid4())[:6].upper(), fecha=str(date.today()), **t.dict())
    db.add(obj); db.commit()
    tid = obj.id
    db.close()
    log_action(usuario or "web", "alta", "ticket", tid, t.dict())
    return obj

@app.put("/api/tickets/{tid}")
def update_ticket(tid: str, t: TicketIn, usuario: str = "", user: UserOut = Depends(require_escritura)):
    usuario = user.username
    db = SessionLocal()
    obj = db.query(Ticket).filter(Ticket.id==tid).first()
    if not obj: raise HTTPException(404)
    antes = {k: getattr(obj, k, None) for k in t.dict().keys()}
    for k,v in t.dict().items(): setattr(obj, k, v)
    db.commit(); db.close()
    cambios = {k: {"antes": antes.get(k), "despues": v} for k, v in t.dict().items() if str(antes.get(k)) != str(v)}
    log_action(usuario or "web", "modificacion", "ticket", tid, cambios)
    return obj

# ---------- ADJUNTOS ----------
from fastapi import UploadFile, File, Form, Header
from fastapi.responses import FileResponse
from adjuntos import Adjunto
import shutil

ADJ_DIR = "C:/AssetManager/adjuntos"
MAX_MB = 10
EXT_OK = {".pdf",".jpg",".jpeg",".png",".gif",".webp",".xlsx",".xls",".docx",".doc",".txt",".csv"}

@app.get("/api/assets/{asset_id}/adjuntos")
def listar_adjuntos(asset_id: str, user: UserOut = Depends(get_current_user)):
    db = SessionLocal()
    items = db.query(Adjunto).filter(Adjunto.asset_id==asset_id, Adjunto.activo=="1").order_by(Adjunto.fecha.desc()).all()
    db.close()
    return [{"id":a.id,"nombre":a.nombre,"tipo":a.tipo,"tamano":a.tamano,"descripcion":a.descripcion,"subido_por":a.subido_por,"fecha":str(a.fecha)} for a in items]

@app.post("/api/assets/{asset_id}/adjuntos")
async def subir_adjunto(asset_id: str, file: UploadFile = File(...), descripcion: str = Form(""), usuario: str = Form(""), user: UserOut = Depends(require_escritura)):
    usuario = user.username
    ext = os.path.splitext(file.filename)[1].lower()
    if ext not in EXT_OK:
        raise HTTPException(400, f"Extension no permitida: {ext}")
    contenido = await file.read()
    if len(contenido) > MAX_MB * 1024 * 1024:
        raise HTTPException(400, f"El archivo supera el maximo de {MAX_MB} MB")
    if not re.fullmatch(r"[A-Za-z0-9_-]{1,40}", asset_id or ""):
        raise HTTPException(400, "Identificador de activo invalido")
    carpeta = os.path.join(ADJ_DIR, asset_id)
    os.makedirs(carpeta, exist_ok=True)
    aid = str(uuid.uuid4())
    destino = os.path.join(carpeta, aid + ext)
    with open(destino, "wb") as f:
        f.write(contenido)
    db = SessionLocal()
    obj = Adjunto(id=aid, asset_id=asset_id, nombre=file.filename, archivo=destino,
                  tipo=ext.replace(".",""), tamano=len(contenido), descripcion=descripcion,
                  subido_por=usuario or "web")
    db.add(obj)
    registrar_historial(db, asset_id, usuario or "web", "adjunto", {"archivo_adjunto": ("", file.filename)})
    db.commit(); db.close()
    log_action(usuario or "web", "alta", "adjunto", aid, {"asset": asset_id, "archivo": file.filename})
    return {"status":"ok","id":aid}

@app.get("/api/adjuntos/{adj_id}/descargar")
def descargar_adjunto(adj_id: str, user: UserOut = Depends(get_current_user)):
    db = SessionLocal()
    a = db.query(Adjunto).filter(Adjunto.id==adj_id, Adjunto.activo=="1").first()
    db.close()
    if not a or not os.path.exists(a.archivo):
        raise HTTPException(404, "Archivo no encontrado")
    return FileResponse(a.archivo, filename=a.nombre)

@app.delete("/api/adjuntos/{adj_id}")
def borrar_adjunto(adj_id: str, usuario: str = "", user: UserOut = Depends(require_escritura)):
    usuario = user.username
    db = SessionLocal()
    a = db.query(Adjunto).filter(Adjunto.id==adj_id).first()
    if not a:
        db.close()
        raise HTTPException(404)
    a.activo = "0"
    nombre = a.nombre
    registrar_historial(db, a.asset_id, usuario or "web", "adjunto", {"archivo_eliminado": (nombre, "")})
    db.commit(); db.close()
    log_action(usuario or "web", "baja", "adjunto", adj_id, {"archivo": nombre})
    return {"status":"ok"}

# ---------- TENDENCIAS ----------
from snapshots import Snapshot

@app.get("/api/tendencias")
def get_tendencias(metrica: str = ""):
    db = SessionLocal()
    q = db.query(Snapshot)
    if metrica:
        q = q.filter(Snapshot.metrica == metrica)
    items = q.order_by(Snapshot.fecha.asc()).all()
    db.close()
    return [{"fecha": str(s.fecha)[:10], "metrica": s.metrica, "clave": s.clave, "valor": s.valor} for s in items]

@app.get("/api/tendencias/metricas")
def get_metricas_disponibles():
    db = SessionLocal()
    items = db.query(Snapshot.metrica).distinct().all()
    db.close()
    return sorted([i[0] for i in items])

FRONTEND = "C:/AssetManager/frontend/dist"


@app.get("/agent_linux.sh")
def get_agent_linux():
    return FileResponse("C:/AssetManager/agente/agent_linux.sh", media_type="text/plain")
@app.get("/")
def root():
    return FileResponse(f"{FRONTEND}/index.html")

@app.get("/{full_path:path}")
def catch_all(full_path: str):
    if full_path.startswith(("api/", "auth/")):
        raise HTTPException(status_code=404, detail="Not Found")
    fp = f"{FRONTEND}/{full_path}"
    if os.path.exists(fp) and os.path.isfile(fp):
        return FileResponse(fp)
    return FileResponse(f"{FRONTEND}/index.html")

from ratelimit import limiter
from slowapi.errors import RateLimitExceeded
from slowapi import _rate_limit_exceeded_handler

app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)
if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
