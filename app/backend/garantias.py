# -*- coding: utf-8 -*-
"""Garantias (fase C).

Lenovo: la pagina publica de soporte (pcsupport.lenovo.com/ar/es/products/<SERIE>/warranty, sin clave) trae en el
HTML el JSON "UpmaWarranties" (cada cobertura: Start, End, Name, DeliveryType, Origin, Duration...) y el resumen
"BaseUpmaWarranties" (solo End/StatusV2). Se guarda la garantia completa en asset_garantia: fin = la cobertura que
vence mas tarde, inicio = la que empezo antes, estado calculado por fecha (no se confia solo en StatusV2).

HP y otros: no hay consulta automatica (la API de garantias de HP pide alta de desarrollador y aprobacion de HP, ver
docs/garantias-hp.md). Se cargan a mano o con un CSV (serie, inicio, fin, cobertura, proveedor, contrato). Una
garantia con fuente "manual" no la pisa nunca la consulta automatica; para volver a Lenovo se quita la carga manual.

Asset.garantia (texto AAAA-MM-DD) se mantiene igual a `fin`: lo usan el Dashboard, los filtros y el export.

Actualizacion automatica: un hilo dentro de la app (como los snapshots de Tendencias) revisa cada minuto si toca
correr (cada 6 h o cuando alguien apreta "Actualizar desde Lenovo"). Atlas-HTTP y Atlas-HTTPS son dos procesos con
la misma app: solo corre el que toma el lease de la fila garantia_corrida (UPDATE condicional), el otro espera.
Se apaga con GARANTIA_REFRESCO_DIAS=0 (el boton manual sigue andando).
"""
import csv
import io
import json
import logging
import re
import socket
import ssl
import threading
import time
import urllib.request
import uuid
from datetime import date, datetime, timedelta
from typing import Optional

from fastapi import APIRouter, Depends, File, HTTPException, Request, UploadFile
from fastapi.responses import Response
from pydantic import BaseModel, ConfigDict, Field, field_validator
from sqlalchemy import text as _sql

import config
from audit import log_action
from auth import MODULOS_FICHA, UserOut, require_modulo
from database import Asset, AssetGarantia, GarantiaCorrida, Historial, SessionLocal
from impresoras import tiene_credencial

log = logging.getLogger("atlas")
router = APIRouter(prefix="/api/garantias", tags=["garantias"])

URL_LENOVO = "https://pcsupport.lenovo.com/ar/es/products/%s/warranty"
_HDR = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) "
                      "Chrome/120.0 Safari/537.36",
        "Accept": "text/html,application/xhtml+xml", "Accept-Language": "es-AR,es;q=0.9"}
_CTX = ssl.create_default_context()
TIMEOUT_S = 25
SERIE_OK = re.compile(r"[A-Z0-9-]{3,40}")
CADA_HORAS = 6
POR_VENCER_DIAS = 60          # lo que vence pronto se vuelve a consultar aunque sea reciente (extensiones)
LEASE_MIN = 30                # se renueva en cada consulta; si el proceso muere, a los 30 min otro la toma
FORMATO_SEGUIDOS = 5          # respuestas sin JSON seguidas: Lenovo cambio la pagina, se corta la corrida
TIPOS_EXCLUIDOS = ("Monitor", "Impresora")   # salvo marca Lenovo con serie (no suele haber)
MAX_CSV = 1024 * 1024
USUARIO_AUTO = "garantias-lenovo"
ENTREGAS = {"on_site": "En sitio", "onsite": "En sitio", "depot": "Depósito", "carry_in": "Llevar al service",
            "carryin": "Llevar al service", "mail_in": "Envío por correo", "customer_carry_in": "Llevar al service"}


# ---------------------------------------------------------------- Lenovo: descarga y parseo
class ErrorFormato(Exception):
    """La pagina respondio pero sin el JSON de garantias (serie desconocida o Lenovo cambio la pagina)."""


def _descargar(serie):
    req = urllib.request.Request(URL_LENOVO % serie, headers=_HDR)
    with urllib.request.urlopen(req, timeout=TIMEOUT_S, context=_CTX) as r:
        return r.read(3 * 1024 * 1024).decode("utf-8", "ignore")


def _extraer_array(html, clave):
    """Devuelve la lista JSON que sigue a "clave": [...] (cuenta corchetes respetando strings; tolera espacios)."""
    m = re.search(r'"%s"\s*:\s*\[' % re.escape(clave), html)
    if not m:
        return None
    i, prof, en_str, esc = m.end() - 1, 0, False, False
    for j in range(i, min(len(html), i + 500000)):
        ch = html[j]
        if en_str:
            if esc:
                esc = False
            elif ch == "\\":
                esc = True
            elif ch == '"':
                en_str = False
        elif ch == '"':
            en_str = True
        elif ch == "[":
            prof += 1
        elif ch == "]":
            prof -= 1
            if prof == 0:
                try:
                    v = json.loads(html[i:j + 1])
                except ValueError:
                    return None
                return v if isinstance(v, list) else None
    return None


def _fecha(v):
    m = re.match(r"^(\d{4})-(\d{2})-(\d{2})", str(v or "").strip())
    if not m:
        return None
    try:
        return date(int(m.group(1)), int(m.group(2)), int(m.group(3)))
    except ValueError:
        return None


def _txt(v, largo=160):
    return "".join(ch for ch in ("" if v is None else str(v)) if ch.isprintable()).strip()[:largo]


def estado_por_fecha(fin, hoy=None):
    if not fin:
        return ""
    return "vigente" if fin >= (hoy or date.today()) else "vencida"


ENTREGAS = {"on_site": "En sitio", "depot": "Depósito", "carry_in": "Llevar al service"}


def es_codigo(nombre):
    """Lenovo a veces nombra la cobertura con un codigo interno ("UKN", "VEO", "TP1") en vez de un texto."""
    n = (nombre or "").strip()
    return not n or (len(n) <= 4 and " " not in n)


def nombre_cobertura(c):
    if not es_codigo(c["nombre"]):
        return c["nombre"]
    partes = []
    if c.get("duracion_meses"):
        m = c["duracion_meses"]
        partes.append("%d año%s" % (m // 12, "" if m // 12 == 1 else "s") if m % 12 == 0 else "%d meses" % m)
    if ENTREGAS.get(c.get("entrega")):
        partes.append(ENTREGAS[c["entrega"]])
    return " · ".join(partes) or c["nombre"] or "Garantía"


def parsear_lenovo(html, hoy=None):
    """HTML de la pagina de garantia -> dict con inicio/fin/estado/cobertura/entrega/origen/coberturas, o None."""
    hoy = hoy or date.today()
    crudas = _extraer_array(html, "UpmaWarranties")
    if not crudas:
        crudas = _extraer_array(html, "BaseUpmaWarranties")
    if not crudas:
        return None
    lista = []
    for w in crudas:
        if not isinstance(w, dict):
            continue
        fin = _fecha(w.get("End"))
        if not fin:
            continue
        try:
            meses = int(w.get("Duration")) if w.get("Duration") not in (None, "") else None
        except (TypeError, ValueError):
            meses = None
        lista.append({"nombre": _txt(w.get("Name") or w.get("WarrentyType") or w.get("WarrantyType")),
                      "inicio": (_fecha(w.get("Start")) or None), "fin": fin, "estado": estado_por_fecha(fin, hoy),
                      "entrega": _txt(w.get("DeliveryType"), 40), "origen": _txt(w.get("Origin"), 80),
                      "duracion_meses": meses})
    if not lista:
        return None
    # entre las que vencen ultimo, la de nombre legible ("3 YR On-site, 9X5 Upgrade" antes que el codigo "UKN")
    lista.sort(key=lambda c: (c["fin"], not es_codigo(c["nombre"])), reverse=True)
    mayor = lista[0]
    inicios = [c["inicio"] for c in lista if c["inicio"]]
    return {"inicio": min(inicios) if inicios else None, "fin": mayor["fin"], "estado": estado_por_fecha(mayor["fin"], hoy),
            "cobertura": nombre_cobertura(mayor), "entrega": mayor["entrega"], "origen": mayor["origen"],
            "coberturas": [dict(c, inicio=c["inicio"].isoformat() if c["inicio"] else "", fin=c["fin"].isoformat())
                           for c in lista]}


def serie_valida(serie):
    s = str(serie or "").strip().upper()
    return s if SERIE_OK.fullmatch(s) and s not in ("N/A", "NA", "---") else ""


def consultar_lenovo(serie):
    """(datos, error). error es un texto corto; ErrorFormato se informa como 'formato'."""
    s = serie_valida(serie)
    if not s:
        return None, "Serie vacía o inválida"
    try:
        html = _descargar(s)
    except (OSError, socket.timeout, ValueError) as e:
        return None, "No se pudo consultar a Lenovo (%s)" % type(e).__name__
    datos = parsear_lenovo(html)
    if not datos:
        return None, "formato"
    return datos, ""


# ---------------------------------------------------------------- guardar
def es_lenovo(a):
    return "LENOVO" in (a.marca or "").upper()


def _sincronizar_activo(db, a, fin, usuario):
    nuevo = fin.isoformat() if fin else ""
    anterior = a.garantia or ""
    if anterior != nuevo:
        db.add(Historial(asset_id=a.id, usuario=usuario, campo="garantia", valor_ant=anterior, valor_new=nuevo,
                         accion="edicion"))
        a.garantia = nuevo
        a.updated = datetime.utcnow()


def guardar_lenovo(db, a, datos, error, ahora=None):
    """Aplica el resultado de una consulta a Lenovo. No toca una garantia cargada a mano. Devuelve la fila."""
    ahora = ahora or datetime.utcnow()
    g = db.get(AssetGarantia, a.id)
    if g is None:
        g = AssetGarantia(asset_id=a.id, fuente="lenovo", estado="", cobertura="", entrega="", origen="",
                          coberturas="", proveedor="", contrato="", notas="", error="")
        db.add(g)
    if g.fuente == "manual":
        return g
    g.fuente = "lenovo"
    g.consultado = ahora
    if error:
        g.error = "No figura en Lenovo o la página cambió" if error == "formato" else _txt(error, 120)
        return g
    g.error = ""
    g.inicio, g.fin, g.estado = datos["inicio"], datos["fin"], datos["estado"]
    g.cobertura, g.entrega, g.origen = datos["cobertura"], datos["entrega"], datos["origen"]
    g.coberturas = json.dumps(datos["coberturas"], ensure_ascii=False)
    g.proveedor = g.proveedor or "Lenovo"
    g.actualizado = ahora
    _sincronizar_activo(db, a, g.fin, USUARIO_AUTO)
    return g


def guardar_manual(db, a, datos, usuario, ahora=None):
    ahora = ahora or datetime.utcnow()
    g = db.get(AssetGarantia, a.id)
    if g is None:
        g = AssetGarantia(asset_id=a.id, entrega="", origen="", coberturas="", error="")
        db.add(g)
    g.fuente = "manual"
    g.inicio, g.fin = datos.get("inicio"), datos.get("fin")
    g.estado = estado_por_fecha(g.fin)
    for c in ("cobertura", "proveedor", "contrato", "notas"):
        setattr(g, c, datos.get(c) or "")
    g.error, g.actualizado = "", ahora
    _sincronizar_activo(db, a, g.fin, usuario)
    return g


def borrar_datos_garantia(db, asset_id):
    """Para el borrado de un activo (en SQLite las FK no se aplican solas)."""
    db.query(AssetGarantia).filter(AssetGarantia.asset_id == asset_id).delete(synchronize_session=False)


# ---------------------------------------------------------------- seleccion y corrida automatica
def pendientes(db, ahora=None, refresco_dias=None):
    """Activos Lenovo con serie valida que hay que consultar: sin dato, consulta vieja o por vencer.
    Excluye dados de baja, monitores/impresoras (salvo Lenovo) y las garantias cargadas a mano."""
    ahora = ahora or datetime.utcnow()
    hoy = ahora.date()
    refresco = config.GARANTIA_REFRESCO_DIAS if refresco_dias is None else refresco_dias
    filas = (db.query(Asset, AssetGarantia).outerjoin(AssetGarantia, AssetGarantia.asset_id == Asset.id)
             .filter(Asset.estado != "Dado de baja").all())
    out = []
    for a, g in filas:
        if not es_lenovo(a) or not serie_valida(a.serial):
            continue
        if g is not None and g.fuente == "manual":
            continue
        if g is None or g.fin is None:
            prioridad = 0                                   # sin dato (incluye las que dieron error)
        elif g.fin >= hoy and (g.fin - hoy).days <= POR_VENCER_DIAS and \
                (g.consultado is None or ahora - g.consultado > timedelta(days=1)):
            prioridad = 1                                   # vence pronto: puede haber una extension nueva
        elif refresco > 0 and (g.consultado is None or ahora - g.consultado > timedelta(days=refresco)):
            prioridad = 2
        else:
            continue
        out.append((prioridad, g.consultado if g and g.consultado else datetime.min, a.id))
    out.sort()
    return [aid for _, _, aid in out]


def _fila_corrida(db):
    f = db.get(GarantiaCorrida, 1)
    if f is None:
        try:
            db.add(GarantiaCorrida(id=1, pedida=False, pendientes=0, ok=0, errores=0, mensaje="", duenio=""))
            db.commit()
        except Exception:
            db.rollback()
        f = db.get(GarantiaCorrida, 1)
    return f


def _tomar_lease(db, duenio, ahora):
    _fila_corrida(db)
    r = db.execute(_sql("UPDATE garantia_corrida SET corriendo_hasta = :h, duenio = :d "
                        "WHERE id = 1 AND (corriendo_hasta IS NULL OR corriendo_hasta < :a)"),
                   {"h": ahora + timedelta(minutes=LEASE_MIN), "d": duenio, "a": ahora})
    db.commit()
    return r.rowcount == 1


def _renovar_lease(db, duenio):
    db.execute(_sql("UPDATE garantia_corrida SET corriendo_hasta = :h WHERE id = 1 AND duenio = :d"),
               {"h": datetime.utcnow() + timedelta(minutes=LEASE_MIN), "d": duenio})
    db.commit()


_DUENIO = "%s-%s" % (socket.gethostname(), uuid.uuid4().hex[:8])


def correr(refresco_dias=None, pausa_s=None, maximo=None, consultar=None):
    """Una corrida completa si este proceso toma el lease. Devuelve el resumen o None si otro esta corriendo."""
    consultar = consultar or consultar_lenovo
    pausa = config.GARANTIA_PAUSA_S if pausa_s is None else pausa_s
    maximo = config.GARANTIA_MAX_POR_CORRIDA if maximo is None else maximo
    duenio = "%s-%s" % (_DUENIO, threading.get_ident())
    db = SessionLocal()
    try:
        ahora = datetime.utcnow()
        if not _tomar_lease(db, duenio, ahora):
            return None
        ids = pendientes(db, ahora, refresco_dias)[:maximo]
        f = _fila_corrida(db)
        f.pedida, f.inicio, f.fin, f.pendientes, f.ok, f.errores, f.mensaje = False, ahora, None, len(ids), 0, 0, ""
        db.commit()
        ok = err = formato_seguidos = 0
        mensaje = ""
        for n, aid in enumerate(ids):
            if n:
                time.sleep(pausa)
            a = db.get(Asset, aid)
            if a is None:
                continue
            datos, error = consultar(a.serial)
            guardar_lenovo(db, a, datos, error)
            if error:
                err += 1
                formato_seguidos = formato_seguidos + 1 if error == "formato" else 0
            else:
                ok += 1
                formato_seguidos = 0
            f = _fila_corrida(db)
            f.ok, f.errores = ok, err
            db.commit()
            _renovar_lease(db, duenio)
            if formato_seguidos >= FORMATO_SEGUIDOS:
                mensaje = "Lenovo respondió %d veces seguidas sin datos de garantía: se cortó la corrida" % formato_seguidos
                log.warning("garantias.formato %s", mensaje, extra={"event": "garantias"})
                break
        f = _fila_corrida(db)
        f.fin, f.mensaje, f.corriendo_hasta, f.duenio = datetime.utcnow(), mensaje, None, ""
        db.commit()
        log.info("garantias.corrida ok=%d errores=%d", ok, err, extra={"event": "garantias"})
        return {"pendientes": len(ids), "ok": ok, "errores": err, "mensaje": mensaje}
    except Exception as e:
        db.rollback()
        log.error("garantias.error %s", type(e).__name__, extra={"event": "garantias"})
        try:
            db.execute(_sql("UPDATE garantia_corrida SET corriendo_hasta = NULL, duenio = '', mensaje = :m "
                            "WHERE id = 1 AND duenio = :d"), {"m": "Error: %s" % type(e).__name__, "d": duenio})
            db.commit()
        except Exception:
            db.rollback()
        return None
    finally:
        db.close()


def toca_correr(db, ahora=None):
    ahora = ahora or datetime.utcnow()
    f = _fila_corrida(db)
    if f.pedida:
        return True
    if config.GARANTIA_REFRESCO_DIAS <= 0:
        return False
    return f.inicio is None or ahora - f.inicio >= timedelta(hours=CADA_HORAS)


def loop():
    """Hilo de fondo (lo arranca main.lifespan). Revisa cada minuto si toca correr."""
    time.sleep(120)   # no consultar a Lenovo apenas arranca el servicio
    while True:
        try:
            db = SessionLocal()
            try:
                toca = toca_correr(db)
            finally:
                db.close()
            if toca:
                correr()
        except Exception as e:
            log.error("garantias.loop %s", type(e).__name__, extra={"event": "garantias"})
        time.sleep(60)


# ---------------------------------------------------------------- vista
def _iso(d):
    return d.isoformat() if d else None


def _json_lista(t):
    try:
        v = json.loads(t or "[]")
        return v if isinstance(v, list) else []
    except ValueError:
        return []


def armar(a, g, hoy=None):
    hoy = hoy or date.today()
    fin = g.fin if g and g.fin else _fecha(a.garantia)
    dias = (fin - hoy).days if fin else None
    return {
        "id": a.id, "nombre": a.nombre, "tipo": a.tipo, "marca": a.marca, "modelo": a.modelo, "serial": a.serial,
        "usuario": a.usuario, "sede": a.ubicacion, "estado_activo": a.estado,
        "fuente": (g.fuente if g else "") or ("ficha" if fin else ""),
        "inicio": _iso(g.inicio) if g else None, "fin": _iso(fin), "dias": dias,
        "estado": estado_por_fecha(fin, hoy),
        "cobertura": g.cobertura if g else "", "entrega": g.entrega if g else "",
        "entrega_texto": ENTREGAS.get((g.entrega or "").lower(), g.entrega or "") if g else "",
        "origen": g.origen if g else "", "proveedor": g.proveedor if g else "", "contrato": g.contrato if g else "",
        "notas": g.notas if g else "", "consultado": g.consultado if g else None, "error": g.error if g else "",
        "coberturas": _json_lista(g.coberturas) if g else [],
        "consultable": es_lenovo(a) and bool(serie_valida(a.serial)),
    }


def _filas(db):
    pares = (db.query(Asset, AssetGarantia).outerjoin(AssetGarantia, AssetGarantia.asset_id == Asset.id)
             .filter(Asset.estado != "Dado de baja").order_by(Asset.nombre).all())
    hoy = date.today()
    return [armar(a, g, hoy) for a, g in pares]


def resumir(filas):
    c = {"total": len(filas), "vigentes": 0, "vencen_90": 0, "vencidas": 0, "sin_dato": 0, "por_marca": {},
         "por_tipo": {}}
    for f in filas:
        clave = ("sin_dato" if f["dias"] is None else "vencidas" if f["dias"] < 0 else "vigentes")
        c[clave] += 1
        if f["dias"] is not None and 0 <= f["dias"] <= 90:
            c["vencen_90"] += 1
        for grupo, valor in (("por_marca", (f["marca"] or "Sin marca").strip().upper()),
                             ("por_tipo", f["tipo"] or "Sin tipo")):
            d = c[grupo].setdefault(valor, {"total": 0, "vigentes": 0, "vencidas": 0, "sin_dato": 0})
            d["total"] += 1
            d[clave] += 1
    return c


def _estado_corrida(db):
    f = _fila_corrida(db)
    ahora = datetime.utcnow()
    return {"corriendo": bool(f.corriendo_hasta and f.corriendo_hasta > ahora), "pedida": bool(f.pedida),
            "inicio": f.inicio, "fin": f.fin, "pendientes": f.pendientes or 0, "ok": f.ok or 0,
            "errores": f.errores or 0, "mensaje": f.mensaje or "",
            "automatica": config.GARANTIA_REFRESCO_DIAS > 0, "refresco_dias": config.GARANTIA_REFRESCO_DIAS}


@router.get("")
def listar(user: UserOut = Depends(require_modulo("activos", "dashboard"))):
    db = SessionLocal()
    try:
        return _filas(db)
    finally:
        db.close()


@router.get("/resumen")
def resumen(user: UserOut = Depends(require_modulo("activos", "dashboard"))):
    db = SessionLocal()
    try:
        return resumir(_filas(db))
    finally:
        db.close()


@router.get("/vencimientos")
def vencimientos(dias: int = 90, user: UserOut = Depends(require_modulo("activos", "dashboard"))):
    """Activos cuya garantia vence en los proximos `dias` (lee Asset.garantia, que se mantiene igual al fin)."""
    hoy = date.today()
    lim = hoy + timedelta(days=dias)
    db = SessionLocal()
    out = []
    try:
        for a in db.query(Asset).filter(Asset.garantia != "").all():
            f = _fecha(a.garantia)
            if f and hoy <= f <= lim:
                out.append({"id": a.id, "nombre": a.nombre or "", "serial": a.serial or "",
                            "usuario": a.usuario or "", "sede": a.ubicacion or "",
                            "modelo": a.modelo or "", "garantia": a.garantia, "dias": (f - hoy).days})
    finally:
        db.close()
    out.sort(key=lambda x: x["dias"])
    return out


@router.get("/estado-actualizacion")
def estado_actualizacion(user: UserOut = Depends(require_modulo("activos", "dashboard"))):
    db = SessionLocal()
    try:
        return _estado_corrida(db)
    finally:
        db.close()


def _correr_manual():
    # El boton fuerza una corrida aunque la automatica este apagada (refresco 0 -> se usa 30 dias)
    correr(refresco_dias=config.GARANTIA_REFRESCO_DIAS or 30)


@router.post("/actualizar")
def actualizar(request: Request, user: UserOut = Depends(require_modulo("activos", nivel="editar"))):
    """Encola una corrida y vuelve enseguida: la corre un hilo aparte (o el otro proceso, si ya esta corriendo)."""
    db = SessionLocal()
    try:
        f = _fila_corrida(db)
        f.pedida = True
        db.commit()
        estado = _estado_corrida(db)
    finally:
        db.close()
    if not estado["corriendo"]:
        threading.Thread(target=_correr_manual, daemon=True).start()
    log_action(user.username, "actualizar_garantias", "garantias", "lenovo", {}, ip=request.client.host if request.client else "")
    return {"status": "encolada", "ya_corriendo": estado["corriendo"]}


PLANTILLA = "serie,inicio,fin,cobertura,proveedor,contrato\r\n5CD1234ABC,2024-03-01,2027-02-28,3 años en sitio,HP,CTR-0001\r\n"


@router.get("/plantilla.csv")
def plantilla(user: UserOut = Depends(require_modulo("activos", nivel="editar"))):
    return Response(content="﻿" + PLANTILLA, media_type="text/csv; charset=utf-8",
                    headers={"Content-Disposition": 'attachment; filename="garantias-plantilla.csv"'})


def _fecha_flexible(v):
    s = str(v or "").strip()
    if not s:
        return None
    d = _fecha(s)
    if d:
        return d
    m = re.match(r"^(\d{1,2})[/.-](\d{1,2})[/.-](\d{4})$", s)
    if m:
        try:
            return date(int(m.group(3)), int(m.group(2)), int(m.group(1)))
        except ValueError:
            return None
    raise ValueError("fecha inválida: %s" % s[:20])


def leer_csv(contenido: bytes):
    texto = contenido.decode("utf-8-sig", "replace")
    muestra = texto[:2000]
    sep = ";" if muestra.count(";") > muestra.count(",") else ","
    lector = csv.DictReader(io.StringIO(texto), delimiter=sep)
    cols = {(c or "").strip().lower(): c for c in (lector.fieldnames or [])}
    if "serie" not in cols or "fin" not in cols:
        raise HTTPException(400, detail="El CSV tiene que tener al menos las columnas serie y fin")
    filas, errores = [], []
    for n, r in enumerate(lector, start=2):
        v = {k: _txt(r.get(cols[k]) if k in cols else "", 160) for k in
             ("serie", "inicio", "fin", "cobertura", "proveedor", "contrato", "notas")}
        if not v["serie"]:
            continue
        if any(tiene_credencial(x) for x in v.values()):
            errores.append({"fila": n, "motivo": "Trae texto con forma de credencial: no se importa"})
            continue
        try:
            v["inicio"], v["fin"] = _fecha_flexible(v["inicio"]), _fecha_flexible(v["fin"])
        except ValueError as e:
            errores.append({"fila": n, "motivo": str(e)})
            continue
        if not v["fin"]:
            errores.append({"fila": n, "motivo": "Falta la fecha de fin"})
            continue
        filas.append(v)
    return filas, errores


@router.post("/importar")
async def importar(request: Request, archivo: UploadFile = File(...),
                   user: UserOut = Depends(require_modulo("activos", nivel="editar"))):
    contenido = await archivo.read(MAX_CSV + 1)
    if len(contenido) > MAX_CSV:
        raise HTTPException(413, detail="El archivo supera 1 MB")
    filas, errores = leer_csv(contenido)
    db = SessionLocal()
    res = {"actualizados": 0, "no_encontrados": [], "ambiguos": [], "errores": errores}
    try:
        for v in filas:
            activos = db.query(Asset).filter(_sql("upper(trim(serial)) = :s")).params(s=v["serie"].upper()).all()
            if not activos:
                res["no_encontrados"].append(v["serie"])
                continue
            if len(activos) > 1:
                res["ambiguos"].append(v["serie"])
                continue
            guardar_manual(db, activos[0], v, user.username)
            res["actualizados"] += 1
        db.commit()
    finally:
        db.close()
    log_action(user.username, "importacion", "garantias", "csv",
               {"actualizados": res["actualizados"], "no_encontrados": len(res["no_encontrados"]),
                "errores": len(errores)}, ip=request.client.host if request.client else "")
    return res


@router.get("/{asset_id}")
def ver(asset_id: str, user: UserOut = Depends(require_modulo(*MODULOS_FICHA))):
    db = SessionLocal()
    try:
        a = db.get(Asset, asset_id)
        if not a:
            raise HTTPException(404)
        return armar(a, db.get(AssetGarantia, asset_id))
    finally:
        db.close()


class GarantiaManual(BaseModel):
    model_config = ConfigDict(extra="forbid")
    inicio:    Optional[date] = None
    fin:       date
    cobertura: Optional[str] = Field(default="", max_length=160)
    proveedor: Optional[str] = Field(default="", max_length=120)
    contrato:  Optional[str] = Field(default="", max_length=80)
    notas:     Optional[str] = Field(default="", max_length=2000)

    @field_validator("cobertura", "proveedor", "contrato", "notas", mode="after")
    @classmethod
    def _sin_credenciales(cls, v):
        if v and tiene_credencial(v):
            raise ValueError("Atlas no guarda credenciales")
        return v

    @field_validator("fin", mode="after")
    @classmethod
    def _fin_despues_de_inicio(cls, v, info):
        ini = info.data.get("inicio")
        if ini and v < ini:
            raise ValueError("La fecha de fin es anterior a la de inicio")
        return v


@router.put("/{asset_id}")
def cargar_manual(asset_id: str, data: GarantiaManual, request: Request,
                  user: UserOut = Depends(require_modulo("activos", nivel="editar"))):
    db = SessionLocal()
    try:
        a = db.get(Asset, asset_id)
        if not a:
            raise HTTPException(404)
        g = guardar_manual(db, a, data.model_dump(), user.username)
        db.commit()
        out = armar(a, g)
    finally:
        db.close()
    log_action(user.username, "garantia_manual", "asset", asset_id, {"fin": out["fin"]},
               ip=request.client.host if request.client else "")
    return out


@router.delete("/{asset_id}/manual")
def quitar_manual(asset_id: str, request: Request, user: UserOut = Depends(require_modulo("activos", nivel="editar"))):
    """Saca la carga manual: si es Lenovo, la proxima consulta (o el boton) la vuelve a traer de Lenovo."""
    db = SessionLocal()
    try:
        a = db.get(Asset, asset_id)
        if not a:
            raise HTTPException(404)
        g = db.get(AssetGarantia, asset_id)
        if g is None or g.fuente != "manual":
            raise HTTPException(409, detail="Este activo no tiene una garantía cargada a mano")
        db.delete(g)
        _sincronizar_activo(db, a, None, user.username)
        db.commit()
        out = armar(a, None)
    finally:
        db.close()
    log_action(user.username, "garantia_quitar_manual", "asset", asset_id, {},
               ip=request.client.host if request.client else "")
    return out
