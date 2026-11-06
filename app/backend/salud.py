# -*- coding: utf-8 -*-
"""Notebooks y PC: salud y seguridad.

El agente de Atlas manda dentro de /api/sync un campo opcional "salud":
    {"so": {"edicion", "display_version", "build", "ubr"},
     "antivirus": [{"nombre", "activo", "actualizado"}],
     "parches": {"ultimo": "YYYY-MM-DD" | "", "cantidad_90d"},
     "discos": [{"nombre", "tipo", "salud", "desgaste", "temperatura", "errores_lectura", "tamano_gb"}],
     "bateria": {"salud", "ciclos", "diseno_mwh", "actual_mwh"} | null}
guardar_salud lo normaliza (sin confiar en tipos ni tamanos) y lo guarda en asset_salud; los endpoints de aca lo
cruzan con el activo (cifrado, ultimo reporte) y con el fin de soporte de Windows (ciclo_vida).
Un equipo que todavia no tiene el agente nuevo igual muestra Windows y BitLocker (salen del sync clasico).
"""
import json
import re
from datetime import date, datetime, timedelta

from fastapi import APIRouter, Depends

from auth import UserOut, require_lectura
from ciclo_vida import build_de, soporte
from database import Asset, AssetSalud, SessionLocal

router = APIRouter(prefix="/api/salud", tags=["salud"])

TIPOS_EQUIPO = ("Notebook", "CPU")
MAX_JSON = 20000          # bytes del campo "salud" completo; si se pasa, se ignora (el sync clasico sigue)
MAX_ITEMS = 16            # antivirus o discos por equipo
DISCO_OK = ("healthy", "ok", "")
DESGASTE_RIESGO = 80      # % de vida consumida del SSD
BATERIA_BAJA = 60         # % de la capacidad de diseno
DIAS_SIN_PARCHES = 30
DIAS_SIN_REPORTAR = 15


# ---------------------------------------------------------------- normalizacion de lo que manda el agente
def _txt(v, largo=120):
    s = "" if v is None else str(v)
    return "".join(ch for ch in s if ch.isprintable()).strip()[:largo]


def _ent(v, minimo=None, maximo=None):
    try:
        n = int(float(v))
    except (TypeError, ValueError):
        return None
    if (minimo is not None and n < minimo) or (maximo is not None and n > maximo):
        return None
    return n


def _bool(v):
    if isinstance(v, bool):
        return v
    return str(v).strip().lower() in ("1", "true", "si", "sí", "yes")


def _fecha(v):
    m = re.match(r"^(\d{4})-(\d{2})-(\d{2})", _txt(v, 30))
    if not m:
        return None
    try:
        return date(int(m.group(1)), int(m.group(2)), int(m.group(3)))
    except ValueError:
        return None


def _lista(v):
    return [x for x in v if isinstance(x, dict)][:MAX_ITEMS] if isinstance(v, list) else []


def limitar_salud(v):
    """Validador de AssetSync.salud: dict de tamano razonable o None (nunca rompe el sync clasico)."""
    if not isinstance(v, dict):
        return None
    try:
        if len(json.dumps(v, default=str)) > MAX_JSON:
            return None
    except (TypeError, ValueError):
        return None
    return v


def estado_antivirus(avs):
    """'' sin datos | 'desactivado' ninguno activo | 'desactualizado' activo pero ninguno al dia | 'ok'."""
    if not avs:
        return ""
    activos = [a for a in avs if a["activo"]]
    if not activos:
        return "desactivado"
    if not any(a["actualizado"] for a in activos):
        return "desactualizado"
    return "ok"


def disco_en_riesgo(d):
    return (d.get("salud", "").lower() not in DISCO_OK
            or (d.get("desgaste") is not None and d["desgaste"] >= DESGASTE_RIESGO)
            or (d.get("errores_lectura") or 0) > 0)


def normalizar(s):
    so = s.get("so") if isinstance(s.get("so"), dict) else {}
    parches = s.get("parches") if isinstance(s.get("parches"), dict) else {}
    bat = s.get("bateria") if isinstance(s.get("bateria"), dict) else None
    avs = [{"nombre": _txt(a.get("nombre")), "activo": _bool(a.get("activo")), "actualizado": _bool(a.get("actualizado"))}
           for a in _lista(s.get("antivirus"))]
    discos = [{"nombre": _txt(d.get("nombre")), "tipo": _txt(d.get("tipo"), 20), "salud": _txt(d.get("salud"), 30),
               "desgaste": _ent(d.get("desgaste"), 0, 100), "temperatura": _ent(d.get("temperatura"), 0, 150),
               "errores_lectura": _ent(d.get("errores_lectura"), 0), "tamano_gb": _ent(d.get("tamano_gb"), 0)}
              for d in _lista(s.get("discos"))]
    bat_salud = bat_ciclos = None
    if bat:
        bat_salud = _ent(bat.get("salud"), 0, 150)
        if bat_salud is None:
            diseno, actual = _ent(bat.get("diseno_mwh"), 1), _ent(bat.get("actual_mwh"), 0)
            if diseno and actual is not None:
                bat_salud = round(actual * 100 / diseno)
        if bat_salud is not None:
            bat_salud = min(bat_salud, 100)
        bat_ciclos = _ent(bat.get("ciclos"), 0)
    return {
        "so_edicion": _txt(so.get("edicion"), 60), "so_display": _txt(so.get("display_version"), 20),
        "so_build": _ent(so.get("build"), 1000, 99999), "so_ubr": _ent(so.get("ubr"), 0),
        "antivirus": json.dumps(avs, ensure_ascii=False), "av_estado": estado_antivirus(avs),
        "ultimo_parche": _fecha(parches.get("ultimo")), "parches_90d": _ent(parches.get("cantidad_90d"), 0),
        "discos": json.dumps(discos, ensure_ascii=False),
        "disco_estado": ("riesgo" if any(disco_en_riesgo(d) for d in discos) else "ok") if discos else "",
        "bateria_salud": bat_salud, "bateria_ciclos": bat_ciclos,
    }


def guardar_salud(db, asset_id, s):
    """Upsert de la ultima foto de salud del equipo (lo llama _aplicar_sync)."""
    datos = normalizar(s)
    fila = db.query(AssetSalud).filter(AssetSalud.asset_id == asset_id).first()
    if not fila:
        fila = AssetSalud(asset_id=asset_id)
        db.add(fila)
    for k, v in datos.items():
        setattr(fila, k, v)
    fila.actualizado = datetime.utcnow()


def borrar_datos_salud(db, asset_id):
    """Para el borrado de un activo: en SQLite las FK no se aplican solas (en PostgreSQL ya lo hace el CASCADE)."""
    db.query(AssetSalud).filter(AssetSalud.asset_id == asset_id).delete(synchronize_session=False)


# ---------------------------------------------------------------- vista
def _json(t):
    try:
        v = json.loads(t or "[]")
        return v if isinstance(v, list) else []
    except ValueError:
        return []


def sin_cifrar(cifrado):
    c = (cifrado or "").strip().lower()
    return c.startswith("sin cifrar") or c.startswith("cifrado (proteccion off)")


def armar(a, s, hoy=None):
    """Fila de la vista: datos del activo + salud + fin de soporte calculado."""
    hoy = hoy or date.today()
    build = (s.so_build if s and s.so_build else None) or build_de(a.so_version)
    edicion = (s.so_edicion if s and s.so_edicion else "") or a.so
    sop = soporte(build, edicion, hoy)
    discos = _json(s.discos) if s else []
    ultimo = a.updated
    return {
        "id": a.id, "nombre": a.nombre, "tipo": a.tipo, "marca": a.marca, "modelo": a.modelo, "serial": a.serial,
        "usuario": a.usuario, "sede": a.ubicacion, "estado": a.estado, "so": a.so, "so_version": a.so_version,
        "so_edicion": s.so_edicion if s else "", "so_display": (s.so_display if s else "") or sop["version"],
        "so_build": build, "so_ubr": s.so_ubr if s else None,
        "soporte_producto": sop["producto"], "fin_soporte": sop["fin_soporte"], "soporte_estado": sop["estado"],
        "soporte_dias": sop["dias"],
        "cifrado": a.cifrado, "sin_cifrar": sin_cifrar(a.cifrado), "tpm": a.tpm,
        "antivirus": _json(s.antivirus) if s else [], "av_estado": s.av_estado if s else "",
        "ultimo_parche": s.ultimo_parche if s else None, "parches_90d": s.parches_90d if s else None,
        "dias_sin_parches": (hoy - s.ultimo_parche).days if s and s.ultimo_parche else None,
        "discos": discos, "disco_estado": s.disco_estado if s else "",
        "desgaste_max": max((d["desgaste"] for d in discos if d.get("desgaste") is not None), default=None),
        "bateria_salud": s.bateria_salud if s else None, "bateria_ciclos": s.bateria_ciclos if s else None,
        "bateria_baja": bool(s and s.bateria_salud is not None and s.bateria_salud < BATERIA_BAJA),
        "ultimo_reporte": ultimo,
        "sin_reportar": bool(ultimo and datetime.utcnow() - ultimo > timedelta(days=DIAS_SIN_REPORTAR)),
        "con_datos": s is not None, "salud_actualizada": s.actualizado if s else None,
    }


def _filas(db):
    pares = (db.query(Asset, AssetSalud).outerjoin(AssetSalud, AssetSalud.asset_id == Asset.id)
             .filter(Asset.estado != "Dado de baja")
             .filter((Asset.tipo.in_(TIPOS_EQUIPO)) | ((Asset.tipo == "Servidor") & AssetSalud.asset_id.isnot(None)))
             .order_by(Asset.nombre).all())
    hoy = date.today()
    return [armar(a, s, hoy) for a, s in pares]


def resumir(filas):
    c = {"total": len(filas), "sin_soporte": 0, "vence_pronto": 0, "sin_cifrar": 0, "av_problema": 0,
         "sin_parches_30d": 0, "disco_riesgo": 0, "bateria_baja": 0, "sin_reportar_15d": 0, "sin_datos": 0}
    for f in filas:
        c["sin_soporte"] += f["soporte_estado"] == "sin_soporte"
        c["vence_pronto"] += f["soporte_estado"] == "vence_pronto"
        c["sin_cifrar"] += f["sin_cifrar"]
        c["av_problema"] += f["av_estado"] in ("desactivado", "desactualizado")
        c["sin_parches_30d"] += f["dias_sin_parches"] is not None and f["dias_sin_parches"] > DIAS_SIN_PARCHES
        c["disco_riesgo"] += f["disco_estado"] == "riesgo"
        c["bateria_baja"] += f["bateria_baja"]
        c["sin_reportar_15d"] += f["sin_reportar"]
        c["sin_datos"] += not f["con_datos"]
    return c


@router.get("")
def listar_salud(user: UserOut = Depends(require_lectura)):
    db = SessionLocal()
    try:
        return _filas(db)
    finally:
        db.close()


@router.get("/resumen")
def resumen_salud(user: UserOut = Depends(require_lectura)):
    db = SessionLocal()
    try:
        return resumir(_filas(db))
    finally:
        db.close()


@router.get("/{asset_id}")
def salud_de_activo(asset_id: str, user: UserOut = Depends(require_lectura)):
    """Para la ficha del activo (cualquier tipo): null si no es un equipo con datos."""
    db = SessionLocal()
    try:
        par = (db.query(Asset, AssetSalud).outerjoin(AssetSalud, AssetSalud.asset_id == Asset.id)
               .filter(Asset.id == asset_id).first())
        if not par:
            return None
        a, s = par
        if s is None and a.tipo not in TIPOS_EQUIPO:
            return None
        return armar(a, s)
    finally:
        db.close()
