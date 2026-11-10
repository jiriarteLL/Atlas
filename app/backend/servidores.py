# -*- coding: utf-8 -*-
"""Servidores y VM (fase D).

Fuentes de cada servidor:
- el agente de Atlas (bloque "servidor" de /api/sync, solo en Windows Server): roles, uptime, reinicio pendiente,
  servicios automaticos detenidos, SQL, IIS, controlador de dominio y VMs de Hyper-V; los volumenes llegan en el
  bloque "salud" (todos los equipos) y se guardan en asset_salud.volumenes;
- los conectores (conectores.py): vCenter, Azure y Redfish (iDRAC / iLO), guardados en asset_externo.

Alertas: volumen con menos de SERVIDOR_DISCO_ALERTA_PCT % libre, reinicio pendiente hace mas de
SERVIDOR_REINICIO_DIAS, sin reiniciar hace mas de SERVIDOR_UPTIME_DIAS (no se aplicaron parches), servicios
automaticos detenidos, Windows Server sin soporte (ciclo_vida.py) y sin reportar hace mas de 15 dias.
"""
import json
from datetime import date, datetime, timedelta

from fastapi import APIRouter, Depends, HTTPException

import config
from auth import MODULOS_FICHA, UserOut, require_modulo
from ciclo_vida import build_de, soporte
from database import Asset, AssetExterno, AssetSalud, AssetServidor, SessionLocal

router = APIRouter(prefix="/api/servidores", tags=["servidores"])

MAX_JSON = 60000          # bytes del bloque "servidor"; si se pasa se ignora (el sync clasico sigue)
MAX_ITEMS = 100
DIAS_SIN_REPORTAR = 15
TIPOS_SERVIDOR = ("Servidor", "VM")
FUENTES = ("vcenter", "azure", "redfish")


# ---------------------------------------------------------------- normalizacion de lo que manda el agente
def _txt(v, largo=120):
    s = "" if v is None else str(v)
    return "".join(ch for ch in s if ch.isprintable()).strip()[:largo]


def _num(v, minimo=None, maximo=None):
    try:
        n = round(float(v), 1)
    except (TypeError, ValueError):
        return None
    if n != n or (minimo is not None and n < minimo) or (maximo is not None and n > maximo):
        return None
    return n


def _bool(v):
    if isinstance(v, bool):
        return v
    return str(v).strip().lower() in ("1", "true", "si", "sí", "yes")


def _dicts(v, maximo=MAX_ITEMS):
    return [x for x in v if isinstance(x, dict)][:maximo] if isinstance(v, list) else []


def _textos(v, largo=120, maximo=30):
    return [_txt(x, largo) for x in v if isinstance(x, (str, int, float)) and _txt(x, largo)][:maximo] if isinstance(v, list) else []


def limitar_servidor(v):
    """Validador de AssetSync.servidor: dict de tamano razonable o None (nunca rompe el sync clasico)."""
    if not isinstance(v, dict):
        return None
    try:
        if len(json.dumps(v, default=str)) > MAX_JSON:
            return None
    except (TypeError, ValueError):
        return None
    return v


def normalizar(s):
    roles = [{"nombre": _txt(r.get("nombre"), 80), "servicios": _textos(r.get("servicios"), 80, 15)}
             for r in _dicts(s.get("roles"), 40) if _txt(r.get("nombre"))]
    servicios = [{"nombre": _txt(x.get("nombre"), 80), "display": _txt(x.get("display"), 120)}
                 for x in _dicts(s.get("servicios_detenidos"), 25) if _txt(x.get("nombre"))]
    sql = [{"instancia": _txt(x.get("instancia"), 60), "estado": _txt(x.get("estado"), 20)}
           for x in _dicts(s.get("sql"), 20) if _txt(x.get("instancia"))]
    iis = [{"nombre": _txt(x.get("nombre"), 80), "estado": _txt(x.get("estado"), 20), "bindings": _textos(x.get("bindings"), 120, 10)}
           for x in _dicts(s.get("iis"), 30) if _txt(x.get("nombre"))]
    hv = s.get("hyperv_vms")
    vms = None if hv is None else [{"nombre": _txt(x.get("nombre"), 80), "estado": _txt(x.get("estado"), 20),
                                    "cpu": _num(x.get("cpu"), 0, 1024), "ram_gb": _num(x.get("ram_gb"), 0)}
                                   for x in _dicts(hv) if _txt(x.get("nombre"))]
    motivos = _textos(s.get("reinicio_motivos"), 60, 5)
    return {
        "roles": json.dumps(roles, ensure_ascii=False), "uptime_dias": _num(s.get("uptime_dias"), 0, 100000),
        "reinicio_pendiente": _bool(s.get("reinicio_pendiente")) or bool(motivos),
        "reinicio_motivos": json.dumps(motivos, ensure_ascii=False),
        "servicios_detenidos": json.dumps(servicios, ensure_ascii=False), "sql": json.dumps(sql, ensure_ascii=False),
        "iis": json.dumps(iis, ensure_ascii=False), "controlador_dominio": _bool(s.get("controlador_dominio")),
        "hyperv_vms": "" if vms is None else json.dumps(vms, ensure_ascii=False),
    }


def guardar_servidor(db, asset_id, s, ahora=None):
    """Upsert del bloque servidor (lo llama _aplicar_sync). reinicio_desde = primera vez que se lo vio pendiente."""
    ahora = ahora or datetime.utcnow()
    datos = normalizar(s)
    fila = db.get(AssetServidor, asset_id)
    if fila is None:
        fila = AssetServidor(asset_id=asset_id, reinicio_desde=None)
        db.add(fila)
    if datos["reinicio_pendiente"]:
        if not fila.reinicio_pendiente or fila.reinicio_desde is None:
            fila.reinicio_desde = ahora
    else:
        fila.reinicio_desde = None
    for k, v in datos.items():
        setattr(fila, k, v)
    fila.actualizado = ahora


def borrar_datos_servidor(db, asset_id):
    """Para el borrado de un activo: en SQLite las FK no se aplican solas (en PostgreSQL ya lo hace el CASCADE)."""
    db.query(AssetServidor).filter(AssetServidor.asset_id == asset_id).delete(synchronize_session=False)
    db.query(AssetExterno).filter(AssetExterno.asset_id == asset_id).delete(synchronize_session=False)


# ---------------------------------------------------------------- vista
def _json(t, defecto=None):
    try:
        v = json.loads(t) if t else defecto
    except (TypeError, ValueError):
        return defecto
    return v if v is not None else defecto


def _lista(t):
    v = _json(t, [])
    return v if isinstance(v, list) else []


def armar(a, srv, salud, externos, hoy=None, ahora=None):
    hoy = hoy or date.today()
    ahora = ahora or datetime.utcnow()
    ext = {e.fuente: _json(e.datos, {}) for e in externos}
    creado_por = [e.fuente for e in externos if e.creado]
    con_agente = srv is not None or salud is not None or not creado_por
    origenes = (["agente"] if con_agente else []) + [f for f in FUENTES if f in ext]
    build = (salud.so_build if salud and salud.so_build else None) or build_de(a.so_version)
    # El agente manda la edicion como "Standard"/"Datacenter": para saber que es Windows Server sirve el nombre del SO
    edicion = a.so if "server" in (a.so or "").lower() else ((salud.so_edicion if salud and salud.so_edicion else "") or a.so)
    sop = soporte(build, edicion, hoy) if "windows" in (a.so or "").lower() or (salud and salud.so_edicion) else \
        {"producto": "", "version": "", "fin_soporte": None, "estado": "desconocido", "dias": None}
    vols = _lista(salud.volumenes) if salud else []
    libres = [v.get("libre_pct") for v in vols if isinstance(v, dict) and v.get("libre_pct") is not None]
    min_libre = min(libres) if libres else None
    reinicio_dias = (ahora - srv.reinicio_desde).days if srv and srv.reinicio_pendiente and srv.reinicio_desde else None
    servicios = _lista(srv.servicios_detenidos) if srv else []
    host = (ext.get("vcenter") or {}).get("host") or (ext.get("azure") or {}).get("grupo_recursos") or ""
    sin_reportar = bool(con_agente and a.updated and ahora - a.updated > timedelta(days=DIAS_SIN_REPORTAR))
    alertas = {
        "disco_lleno": min_libre is not None and min_libre < config.SERVIDOR_DISCO_ALERTA_PCT,
        "reinicio_pendiente": reinicio_dias is not None and reinicio_dias > config.SERVIDOR_REINICIO_DIAS,
        "uptime_alto": bool(srv and srv.uptime_dias is not None and srv.uptime_dias > config.SERVIDOR_UPTIME_DIAS),
        "servicios_detenidos": bool(servicios),
        "sin_soporte": sop["estado"] == "sin_soporte",
        "sin_reportar": sin_reportar,
    }
    return {
        "id": a.id, "nombre": a.nombre, "tipo": a.tipo, "marca": a.marca, "modelo": a.modelo, "serial": a.serial,
        "sede": a.ubicacion, "usuario": a.usuario, "ip": a.ip, "so": a.so, "so_version": a.so_version,
        "estado": a.estado, "cpu": a.cpu, "ram": a.ram, "disco": a.disco,
        "soporte_producto": sop["producto"], "soporte_version": sop["version"], "fin_soporte": sop["fin_soporte"],
        "soporte_estado": sop["estado"], "soporte_dias": sop["dias"],
        "origenes": origenes, "creado_por": creado_por, "con_agente": con_agente,
        "roles": _lista(srv.roles) if srv else [], "volumenes": vols, "disco_min_libre_pct": min_libre,
        "uptime_dias": srv.uptime_dias if srv else None,
        "reinicio_pendiente": bool(srv and srv.reinicio_pendiente), "reinicio_dias": reinicio_dias,
        "reinicio_motivos": _lista(srv.reinicio_motivos) if srv else [],
        "servicios_detenidos": servicios, "sql": _lista(srv.sql) if srv else [], "iis": _lista(srv.iis) if srv else [],
        "controlador_dominio": bool(srv and srv.controlador_dominio),
        "hyperv_vms": (_lista(srv.hyperv_vms) if srv and srv.hyperv_vms else None),
        "externos": ext, "host": host,
        "ultimo_reporte": a.updated, "servidor_actualizado": srv.actualizado if srv else None,
        "alertas": [k for k, v in alertas.items() if v],
    }


def _filas(db):
    externos = {}
    for e in db.query(AssetExterno).all():
        externos.setdefault(e.asset_id, []).append(e)
    srvs = {s.asset_id: s for s in db.query(AssetServidor).all()}
    ids = set(srvs) | set(externos)
    q = db.query(Asset).filter(Asset.estado != "Dado de baja")
    activos = [a for a in q.all() if a.tipo in TIPOS_SERVIDOR or a.id in ids]
    salud = {s.asset_id: s for s in db.query(AssetSalud).filter(AssetSalud.asset_id.in_([a.id for a in activos])).all()} if activos else {}
    hoy, ahora = date.today(), datetime.utcnow()
    filas = [armar(a, srvs.get(a.id), salud.get(a.id), externos.get(a.id, []), hoy, ahora) for a in activos]
    filas.sort(key=lambda f: (f["nombre"] or "").lower())
    return filas


ALERTAS = ("disco_lleno", "reinicio_pendiente", "uptime_alto", "servicios_detenidos", "sin_soporte", "sin_reportar")


def resumir(filas):
    c = {"total": len(filas), "con_agente": 0, "por_origen": {}}
    for k in ALERTAS:
        c[k] = 0
    for f in filas:
        c["con_agente"] += f["con_agente"]
        for o in f["origenes"]:
            c["por_origen"][o] = c["por_origen"].get(o, 0) + 1
        for k in f["alertas"]:
            c[k] += 1
    return c


@router.get("")
def listar(user: UserOut = Depends(require_modulo("servidores"))):
    db = SessionLocal()
    try:
        return _filas(db)
    finally:
        db.close()


@router.get("/resumen")
def resumen(user: UserOut = Depends(require_modulo("servidores", "dashboard"))):
    db = SessionLocal()
    try:
        return resumir(_filas(db))
    finally:
        db.close()


@router.get("/{asset_id}")
def ver(asset_id: str, user: UserOut = Depends(require_modulo("servidores", *MODULOS_FICHA))):
    """Detalle de un servidor (lo usa tambien la ficha del activo). 404 si el activo no es servidor ni VM."""
    db = SessionLocal()
    try:
        a = db.get(Asset, asset_id)
        if a is None:
            raise HTTPException(404)
        srv = db.get(AssetServidor, asset_id)
        ext = db.query(AssetExterno).filter(AssetExterno.asset_id == asset_id).all()
        if a.tipo not in TIPOS_SERVIDOR and srv is None and not ext:
            raise HTTPException(404, "No es un servidor")
        salud = db.get(AssetSalud, asset_id)
        return armar(a, srv, salud, ext)
    finally:
        db.close()
