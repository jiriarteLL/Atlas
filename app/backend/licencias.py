# -*- coding: utf-8 -*-
"""Licencias: productos contratados, quién los tiene, cupos, costos (por centro de costo y por mes) y renovaciones.

Fuentes (ninguna borra: lo que deja de venir pasa a "liberada"/inactivo con su fecha):
  - UserManager productivo (principal): productos, asignaciones, nomina (legajo, centro de costo, area, sede, estado),
    pares de Adobe (una licencia compartida por dos personas, con centro de imputacion) y cuentas de equipo de Claude
    (una cuenta por unidad de negocio). Se exporta a JSON con herramientas/licencias/exportar_usermanager.py (lee la
    base en solo lectura) y se importa con POST /api/licencias/importar-usermanager (idempotente, upsert por los ids
    del UserManager guardados en id_externo).
  - Adobe: exportacion CSV de la Admin Console o User Management API (conector, conectores.py). Solo leen.
  - Carga manual / CSV generico (email, nombre, producto, proveedor).
COSTOS: precio por licencia en USD y/o ARS (las dos columnas) y periodicidad, cargados en Atlas: ninguna importacion
los pisa. Los costos reales por mes (licencia_costo_periodo) vienen de la API del proveedor (origen "api", p. ej.
Anthropic) o se cargan a mano (origen "manual").
"""
import csv
import io
import json
import re
import time
import unicodedata
import urllib.parse
from collections import defaultdict
from datetime import date, datetime, timedelta
from decimal import Decimal
from typing import List, Literal, Optional

from fastapi import APIRouter, Depends, File, Form, HTTPException, Request, UploadFile
from fastapi.responses import Response
from pydantic import BaseModel, ConfigDict, Field, field_validator

import config
import conectores
from audit import log_action
from auth import UserOut, require_modulo
from conectores import ErrorConector, leer_secreto
from database import (Asset, LicenciaAsignacion, LicenciaCompartida, LicenciaCostoPeriodo, LicenciaCuentaEquipo,
                      LicenciaPersona, LicenciaProducto, SessionLocal)
from impresoras import tiene_credencial

router = APIRouter(prefix="/api/licencias", tags=["licencias"])

MONEDAS = ("USD", "ARS")
PERIODOS = ("mensual", "anual")
ADOBE_SCOPE = "openid,AdobeID,user_management_sdk"
ADOBE_PAGINAS_MAX = 200
ADOBE_REINTENTOS_429 = 3
ADOBE_ESPERA_MAX_S = 60
MAX_ARCHIVO = 5 * 1024 * 1024
ORIGENES_EXTERNOS = ("usermanager", "adobe", "adobe-csv")   # los define la fuente: no se asignan ni liberan a mano
SIN_DATO = "sin dato"
SIN_ASIGNAR = "sin asignar"
_EMAIL = re.compile(r"^[^@\s,;]+@[^@\s,;]+\.[^@\s,;]+$")
_PERIODO = re.compile(r"^\d{4}-(0[1-9]|1[0-2])$")


def _txt(v, largo=160):
    s = "" if v is None else str(v)
    return "".join(ch for ch in s if ch.isprintable()).strip()[:largo]


def norm_email(v):
    e = _txt(v, 200).lower()
    return e if _EMAIL.match(e) else ""


def _f(v):
    return float(v) if isinstance(v, Decimal) else (None if v is None else float(v))


def _num(v):
    """'1.234,50' / '1234.5' / '' -> float o None."""
    s = _txt(v, 40).replace("$", "").replace("USD", "").replace("ARS", "").strip()
    if not s:
        return None
    if "," in s and "." in s:
        s = s.replace(".", "").replace(",", ".")
    elif "," in s:
        s = s.replace(",", ".")
    try:
        return round(float(s), 2)
    except ValueError:
        return None


def _fecha(v):
    """'2026-07-14', '14/07/2026' o '2026-07-14T10:00:00' -> datetime (o None)."""
    s = _txt(v, 30)
    for fmt, largo in (("%Y-%m-%dT%H:%M:%S", 19), ("%Y-%m-%d %H:%M:%S", 19), ("%Y-%m-%d", 10), ("%d/%m/%Y", 10)):
        try:
            return datetime.strptime(s[:largo], fmt)
        except ValueError:
            continue
    return None


# ---------------------------------------------------------------- catalogo inicial (seed)
# Lo unico que se carga solo: los productos contratados hoy, SIN costos (los carga el usuario) y sin personas.
# Planes Team: Adobe Teams no tiene User Management API y Claude Team no tiene Admin/Analytics API (solo Enterprise):
# las asignaciones van por carga manual o CSV de miembros.
CATALOGO = (
    # proveedor, producto, plan, cupo
    ("Anthropic", "Claude Team Standard", "Team", None),
    ("Anthropic", "Claude Team Premium", "Team", None),
    ("Anthropic", "Claude Max 20x", "Max 20x", None),
    ("Adobe", "Creative Cloud Pro", "Teams", 4),
    ("Adobe", "Illustrator", "Teams", 4),
    ("Adobe", "Photoshop", "Teams", 1),
    ("Adobe", "Premiere Pro", "Teams", 4),
    ("Adobe", "Acrobat Premium para equipos", "Teams", 66),
)


def sembrar_catalogo(db, ahora=None):
    """Idempotente por (proveedor, producto): crea los que falten; nunca toca los que ya existen (ni sus costos)."""
    ahora = ahora or datetime.utcnow()
    existentes = {((p.proveedor or "").lower(), (p.producto or "").lower()) for p in db.query(LicenciaProducto).all()}
    creados = []
    for proveedor, producto, plan, cupo in CATALOGO:
        if (proveedor.lower(), producto.lower()) in existentes:
            continue
        p = _nuevo_producto(db, "manual", "", ahora, proveedor=proveedor, producto=producto, periodo="mensual")
        p.plan, p.cupo, p.cupo_manual = plan, cupo, cupo is not None
        p.tipo = "IA" if proveedor == "Anthropic" else "Software"
        creados.append(producto)
    return creados


# ---------------------------------------------------------------- personas
def _persona(db, clave, nombre="", estado=None, ahora=None):
    p = db.get(LicenciaPersona, clave)
    if p is None:
        p = LicenciaPersona(persona=clave, nombre=nombre or "", estado_externo="", cuenta_ad="desconocida", legajo="",
                            centro_costo="", area="", categoria="", sede="", estado_nomina="", id_externo="")
        db.add(p)
        db.flush()
    if nombre and not p.nombre:
        p.nombre = nombre
    if estado is not None:
        p.estado_externo = estado
    p.actualizado = ahora or datetime.utcnow()
    return p


def de_baja(p):
    return bool(p) and (p.estado_nomina or "") == "baja"


def deshabilitada(p):
    """Cuenta que no deberia tener licencias: baja en la nomina, deshabilitada en AD o en Adobe."""
    return bool(p) and (de_baja(p) or (p.cuenta_ad or "") == "deshabilitada" or (p.estado_externo or "") not in ("", "active"))


# ---------------------------------------------------------------- Adobe (User Management API)
class _ClienteAdobe:
    """Token de IMS (client_credentials) que se renueva ante un 401; espera ante un 429 (Retry-After)."""

    def __init__(self, http, dormir):
        self.http, self.dormir = http, dormir
        self.token = None

    def _token(self):
        secreto = leer_secreto(config.ADOBE_SECRET_ARCHIVO)
        if not secreto:
            raise ErrorConector("No se pudo leer el archivo del secreto de Adobe")
        cuerpo = urllib.parse.urlencode({"client_id": config.ADOBE_CLIENT_ID, "client_secret": secreto,
                                         "grant_type": "client_credentials", "scope": ADOBE_SCOPE}).encode("ascii")
        try:
            _, r = self.http("POST", config.ADOBE_IMS_URL, {"Content-Type": "application/x-www-form-urlencoded",
                                                            "Accept": "application/json"}, cuerpo)
        except ErrorConector as e:
            raise ErrorConector("Adobe no aceptó la credencial (%s)" % (e.status or "sin conexión"), e.status) from None
        tok = r.get("access_token") if isinstance(r, dict) else None
        if not tok:
            raise ErrorConector("Adobe no devolvió un token")
        self.token = tok

    def get(self, ruta):
        if not self.token:
            self._token()
        renovado, intentos = False, 0
        while True:
            h = {"Authorization": "Bearer " + self.token, "X-Api-Key": config.ADOBE_CLIENT_ID, "Accept": "application/json"}
            try:
                return self.http("GET", config.ADOBE_UMAPI_URL + ruta, h)[1]
            except ErrorConector as e:
                if e.status == 401 and not renovado:
                    renovado = True
                    self._token()
                    continue
                if e.status == 429 and intentos < ADOBE_REINTENTOS_429:
                    intentos += 1
                    self.dormir(min(ADOBE_ESPERA_MAX_S, e.reintentar_en or 5))
                    continue
                raise


def _paginas(cli, recurso, clave):
    org = urllib.parse.quote(config.ADOBE_ORG_ID, safe="@")
    out = []
    for pagina in range(ADOBE_PAGINAS_MAX):
        r = cli.get("/%s/%s/%d" % (recurso, org, pagina)) or {}
        if not isinstance(r, dict):
            raise ErrorConector("Adobe respondió algo inesperado en /%s" % recurso)
        out.extend(x for x in (r.get(clave) or []) if isinstance(x, dict))
        if r.get("lastPage", True):
            break
    return out


def _cupo(v):
    """licenseQuota: número (a veces como texto), "UNLIMITED" o ausente -> (cupo, ilimitado)."""
    if isinstance(v, str) and v.strip().upper() == "UNLIMITED":
        return None, True
    try:
        return int(float(v)), False
    except (TypeError, ValueError):
        return None, False


def leer_adobe(http, dormir=time.sleep):
    cli = _ClienteAdobe(http, dormir)
    perfiles = []
    for g in _paginas(cli, "groups", "groups"):
        if (g.get("type") or "").upper() != "PRODUCT_PROFILE":
            continue
        cupo, ilimitado = _cupo(g.get("licenseQuota"))
        perfiles.append({"perfil": _txt(g.get("groupName"), 200), "producto": _txt(g.get("productName"), 200),
                         "cupo": cupo, "ilimitado": ilimitado, "miembros": g.get("memberCount")})
    usuarios = []
    for u in _paginas(cli, "users", "users"):
        email = norm_email(u.get("email") or u.get("username"))
        if not email:
            continue
        nombre = " ".join(x for x in (_txt(u.get("firstname"), 80), _txt(u.get("lastname"), 80)) if x)
        usuarios.append({"email": email, "nombre": nombre, "estado": _txt(u.get("status"), 30).lower() or "active",
                         "grupos": [_txt(x, 200) for x in (u.get("groups") or []) if isinstance(x, str)]})
    return {"perfiles": [p for p in perfiles if p["perfil"]], "usuarios": usuarios}


def _nuevo_producto(db, origen, id_externo, ahora, **campos):
    p = LicenciaProducto(origen=origen, id_externo=id_externo, periodo=campos.pop("periodo", "anual"), activo=True,
                         cupo_manual=False, ilimitado=False, costo_origen="manual", workspace="", creado=ahora, actualizado=ahora,
                         tipo="", plan="", sku="", contrato="", notas="", producto_externo="", **campos)
    db.add(p)
    db.flush()
    return p


def _sincronizar_asignaciones(db, origen, deben, ahora, res):
    """deben: {(producto_id, persona): nombre}. Crea las que faltan y libera las de ese origen que ya no vienen."""
    activas = {(a.producto_id, a.persona): a for a in db.query(LicenciaAsignacion).filter(
        LicenciaAsignacion.origen == origen, LicenciaAsignacion.estado == "activa").all()}
    for clave, nombre in deben.items():
        if clave in activas:
            if nombre:
                activas[clave].nombre = nombre
        else:
            db.add(LicenciaAsignacion(producto_id=clave[0], persona=clave[1], nombre=nombre, origen=origen, desde=ahora,
                                      estado="activa", id_externo="", detalle=""))
            res["altas"] = res.get("altas", 0) + 1
    for clave, a in activas.items():
        if clave not in deben:
            a.estado, a.hasta = "liberada", ahora
            res["liberadas"] = res.get("liberadas", 0) + 1


def aplicar_adobe(db, datos, ahora=None):
    """Upsert de perfiles (sin pisar costos ni cupo manual) y de asignaciones (las que no vinieron -> liberadas)."""
    ahora = ahora or datetime.utcnow()
    res = {"productos": 0, "asignadas": 0, "altas": 0, "liberadas": 0}
    existentes = {p.id_externo: p for p in db.query(LicenciaProducto).filter(LicenciaProducto.origen == "adobe").all()}
    vistos = set()
    for x in datos.get("perfiles", []):
        p = existentes.get(x["perfil"]) or _nuevo_producto(db, "adobe", x["perfil"], ahora, proveedor="Adobe", producto=x["perfil"])
        existentes[x["perfil"]] = p
        p.producto_externo = x["producto"]
        if not p.cupo_manual:
            p.cupo, p.ilimitado = x["cupo"], x["ilimitado"]
        p.activo, p.actualizado = True, ahora
        vistos.add(x["perfil"])
        res["productos"] += 1
    for k, p in existentes.items():
        if k not in vistos and p.activo:          # el perfil ya no existe en Adobe: queda inactivo, no se borra
            p.activo, p.actualizado = False, ahora
    deben = {}
    for u in datos.get("usuarios", []):
        _persona(db, u["email"], u["nombre"], u["estado"], ahora)
        for g in u["grupos"]:
            p = existentes.get(g)
            if p is not None and g in vistos:
                deben[(p.id, u["email"])] = u["nombre"]
    _sincronizar_asignaciones(db, "adobe", deben, ahora, res)
    res["asignadas"] = len(deben)
    return res


# ---------------------------------------------------------------- exportacion de la Admin Console de Adobe (CSV)
# Usuarios -> "..." -> Exportar lista de usuarios a CSV. Formatos (columnas por nombre, sin importar mayusculas,
# espacios, tildes ni idioma): Enterprise (Email, First Name, Last Name, Product Configurations, ...) y
# Teams/VIP (Email, First Name, Last Name, ..., Products / Assigned Products).
COLS_EMAIL = ("email", "correoelectronico", "correo", "emailaddress", "mail")
COLS_USUARIO = ("username", "nombredeusuario", "usuario")
COLS_NOMBRE = ("firstname", "nombre", "givenname")
COLS_APELLIDO = ("lastname", "apellido", "apellidos", "surname", "familyname")
COLS_PRODUCTOS = ("productconfigurations", "configuracionesdeproducto", "configuracionesdeproductos", "productprofiles",
                  "productosdeequipo", "teamproducts",
                  "perfilesdeproducto", "assignedproducts", "productosasignados", "products", "productos", "product", "producto")


def _col(nombre):
    s = unicodedata.normalize("NFKD", nombre or "").encode("ascii", "ignore").decode("ascii").lower()
    return re.sub(r"[^a-z0-9]", "", s)


def _buscar(cabecera, candidatos):
    for c in candidatos:
        if c in cabecera:
            return cabecera[c]
    return None


def _texto(contenido):
    try:
        return contenido.decode("utf-8-sig")
    except UnicodeDecodeError:
        return contenido.decode("latin-1")


def leer_csv_adobe(contenido):
    """-> [{email, nombre, productos: [..]}]. ValueError si no tiene las columnas minimas (mail y productos)."""
    texto = _texto(contenido)
    lineas = texto.splitlines()
    if not lineas:
        raise ValueError("El archivo está vacío")
    sep = max((",", ";", "\t"), key=lineas[0].count)
    lector = csv.reader(io.StringIO(texto), delimiter=sep)
    idx = {}
    for i, n in enumerate(next(lector, [])):
        idx.setdefault(_col(n), i)
    c_mail, c_user, c_prod = _buscar(idx, COLS_EMAIL), _buscar(idx, COLS_USUARIO), _buscar(idx, COLS_PRODUCTOS)
    if c_prod is None or (c_mail is None and c_user is None):
        raise ValueError("No parece una exportación de usuarios de Adobe: faltan las columnas de mail o de productos")
    c_nom, c_ape = _buscar(idx, COLS_NOMBRE), _buscar(idx, COLS_APELLIDO)

    def val(fila, i):
        return fila[i].strip() if i is not None and i < len(fila) else ""
    out = []
    for fila in lector:
        email = norm_email(val(fila, c_mail)) or norm_email(val(fila, c_user))
        if not email:
            continue
        productos = [_txt(x, 200) for x in re.split(r"\s*[,;|\n]\s*", val(fila, c_prod)) if _txt(x, 200)]
        nombre = " ".join(x for x in (_txt(val(fila, c_nom), 80), _txt(val(fila, c_ape), 80)) if x)
        out.append({"email": email, "nombre": nombre, "productos": list(dict.fromkeys(productos))})
    return out


# Nombres de la exportacion de Adobe -> producto del catalogo (sin el sufijo "(DIRECT - <contrato>)")
ALIAS_ADOBE = {"acrobatpremiumforteams": "Acrobat Premium para equipos", "acrobatpremiumparaequipos": "Acrobat Premium para equipos",
               "premiereproedition": "Premiere Pro", "premierepro": "Premiere Pro", "creativecloudpro": "Creative Cloud Pro",
               "illustrator": "Illustrator", "photoshop": "Photoshop"}
SUFIJO_CONTRATO = re.compile(r"\s*\((DIRECT|INDIRECT|VIP)\b[^)]*\)\s*$", re.I)


def nombre_adobe(nombre):
    """"Acrobat Premium for teams (DIRECT - CD0B...)" -> "Acrobat Premium para equipos" (o el nombre limpio)."""
    limpio = SUFIJO_CONTRATO.sub("", nombre or "").strip()
    return ALIAS_ADOBE.get(_col(limpio), limpio)


def aplicar_csv_adobe(db, filas, ahora=None):
    """Solo personas con licencia: las filas sin productos se ignoran (no se dan de alta)."""
    ahora = ahora or datetime.utcnow()
    res = {"personas": 0, "productos_nuevos": 0, "altas": 0, "liberadas": 0, "sin_productos": 0}
    prods = {p.id_externo: p for p in db.query(LicenciaProducto).filter(LicenciaProducto.origen == "adobe-csv").all()}
    # el catalogo de Adobe (seed o carga a mano) se reusa por nombre: no se duplican productos
    catalogo = {_col(p.producto): p for p in db.query(LicenciaProducto).filter(LicenciaProducto.proveedor == "Adobe").all()}
    deben = {}
    for f in filas:
        if not f["productos"]:
            res["sin_productos"] += 1
            continue
        res["personas"] += 1
        _persona(db, f["email"], f["nombre"], None, ahora)
        for crudo in f["productos"]:
            nombre = nombre_adobe(crudo)
            p = prods.get(nombre) or catalogo.get(_col(nombre))
            if p is None:
                p = _nuevo_producto(db, "adobe-csv", nombre, ahora, proveedor="Adobe", producto=nombre)
                res["productos_nuevos"] += 1
            prods[nombre] = catalogo[_col(nombre)] = p
            p.activo, p.actualizado = True, ahora
            deben[(p.id, f["email"])] = f["nombre"]
    _sincronizar_asignaciones(db, "adobe-csv", deben, ahora, res)
    res["asignadas"] = len(deben)
    return res


# ---------------------------------------------------------------- UserManager (JSON del exportador)
def _clave_empleado(e):
    """Clave de la persona: el mail; sin mail, "legajo-N"; sin legajo, el id del UserManager."""
    legajo = _txt(e.get("legajo"), 20)
    return norm_email(e.get("email")) or ("legajo-%s" % legajo if legajo else "um-" + _txt(e.get("id"), 60))


def _activo(v):
    return _txt(v, 10).lower() in ("1", "true", "si", "sí", "activo")


def aplicar_usermanager(db, datos, ahora=None):
    """Upsert idempotente desde el JSON de herramientas/licencias/exportar_usermanager.py. Nunca pisa precios cargados
    en Atlas ni el cupo cargado a mano; lo que ya no viene queda liberado / inactivo (no se borra)."""
    if not isinstance(datos, dict) or datos.get("origen") != "usermanager":
        raise ValueError("No es una exportación del UserManager (falta \"origen\": \"usermanager\")")
    ahora = ahora or datetime.utcnow()
    hoy = ahora.date()
    res = {"productos": 0, "productos_nuevos": 0, "personas": 0, "asignaciones": 0, "altas": 0, "liberadas": 0,
           "compartidas": 0, "cuentas_equipo": 0}
    # productos
    prods = {p.id_externo: p for p in db.query(LicenciaProducto).filter(LicenciaProducto.origen == "usermanager").all()}
    vistos = set()
    for x in datos.get("licencias") or []:
        ext = _txt(x.get("id"), 60)
        if not ext:
            continue
        p = prods.get(ext)
        if p is None:
            p = prods[ext] = _nuevo_producto(db, "usermanager", ext, ahora, proveedor=_txt(x.get("proveedor"), 60) or "Otro",
                                             producto=_txt(x.get("nombre")) or ext,
                                             periodo="anual" if _txt(x.get("periodicidad")).lower().startswith("anual") else "mensual")
            p.notas = _txt(x.get("notas"), 2000)
            res["productos_nuevos"] += 1
        p.producto, p.proveedor = _txt(x.get("nombre")) or p.producto, _txt(x.get("proveedor"), 60) or p.proveedor
        p.tipo, p.plan = _txt(x.get("tipo"), 60), _txt(x.get("plan"), 80)
        if not p.cupo_manual:
            cant = x.get("cantidad")
            p.cupo = int(cant) if isinstance(cant, (int, float)) and cant > 0 else None
        # precios: solo si Atlas todavia no tiene (los cargados en Atlas mandan)
        usd, ars = _num(x.get("costo_usd")), _num(x.get("costo_ars"))
        if p.precio_usd is None and usd is not None:
            p.precio_usd = usd
        if p.precio_ars is None and ars is not None:
            p.precio_ars = ars
        p.activo, p.actualizado = True, ahora
        vistos.add(ext)
        res["productos"] += 1
    for ext, p in prods.items():
        if ext not in vistos and p.activo:
            p.activo, p.actualizado = False, ahora
    # personas (nomina)
    claves = {}
    for e in datos.get("empleados") or []:
        clave = _clave_empleado(e)
        claves[_txt(e.get("id"), 60)] = (clave, _txt(e.get("nombre")))
        per = _persona(db, clave, _txt(e.get("nombre")), None, ahora)
        per.nombre = _txt(e.get("nombre")) or per.nombre
        per.legajo, per.centro_costo = _txt(e.get("legajo"), 20), _txt(e.get("centro_costo"), 80)
        per.area, per.categoria, per.sede = _txt(e.get("subauxiliar"), 80), _txt(e.get("categoria"), 60), _txt(e.get("sede"), 40)
        per.estado_nomina = "activo" if _txt(e.get("estado"), 20).lower() == "activo" else "baja"
        per.id_externo = _txt(e.get("id"), 60)
        res["personas"] += 1
    por_mail = {norm_email(e.get("email")): claves[_txt(e.get("id"), 60)]
                for e in datos.get("empleados") or [] if norm_email(e.get("email"))}
    # asignaciones (upsert por id del UserManager)
    asig = {a.id_externo: a for a in db.query(LicenciaAsignacion).filter(LicenciaAsignacion.origen == "usermanager").all()}
    vistas = set()
    for x in datos.get("asignaciones") or []:
        ext, p = _txt(x.get("id"), 60), prods.get(_txt(x.get("licencia_id"), 60))
        emp = claves.get(_txt(x.get("empleado_id"), 60))
        if not ext or p is None or emp is None:
            continue
        hasta = _fecha(x.get("fecha_hasta"))
        activa = _activo(x.get("activo")) and (hasta is None or hasta.date() >= hoy)
        a = asig.get(ext)
        if a is None:
            a = asig[ext] = LicenciaAsignacion(producto_id=p.id, persona=emp[0], origen="usermanager", id_externo=ext,
                                               desde=_fecha(x.get("fecha_desde")) or ahora, estado="activa")
            db.add(a)
            res["altas"] += 1
        a.producto_id, a.persona, a.nombre, a.detalle = p.id, emp[0], emp[1], _txt(x.get("detalle"), 160)
        if activa:
            a.estado, a.hasta = "activa", None
        elif a.estado == "activa":
            a.estado, a.hasta = "liberada", hasta or ahora
            res["liberadas"] += 1
        vistas.add(ext)
        res["asignaciones"] += 1
    for ext, a in asig.items():
        if ext not in vistas and a.estado == "activa":
            a.estado, a.hasta = "liberada", ahora
            res["liberadas"] += 1
    # licencias compartidas (pares de Adobe)
    adobe = next((p for p in prods.values() if (p.proveedor or "").lower() == "adobe" and p.activo), None)
    pares = {c.id_externo: c for c in db.query(LicenciaCompartida).all()}
    vistos_p = set()
    for x in datos.get("adobe_pares") or []:
        ext = _txt(x.get("id"), 60)
        if not ext:
            continue
        c = pares.get(ext)
        if c is None:
            c = pares[ext] = LicenciaCompartida(id_externo=ext)
            db.add(c)
        def quien(mail, nombre):
            m = norm_email(mail)
            if m in por_mail:
                return por_mail[m]
            return (m or ("nombre:" + _txt(nombre, 80).lower() if _txt(nombre, 80) else ""), _txt(nombre, 120))
        c.principal, c.principal_nombre = quien(x.get("email_principal"), x.get("usuario_principal"))
        c.secundario, c.secundario_nombre = quien(x.get("email_secundario"), x.get("usuario_secundario"))
        c.producto_id, c.sector, c.imputacion = adobe.id if adobe else None, _txt(x.get("sector"), 80), _txt(x.get("imputacion"), 80)
        pct = _num(x.get("porcentaje_imputacion"))
        c.porcentaje = pct if pct and 0 < pct < 100 else None
        c.activo, c.actualizado = _activo(x.get("activo")), ahora
        vistos_p.add(ext)
        res["compartidas"] += 1
    for ext, c in pares.items():
        if ext not in vistos_p and c.activo:
            c.activo, c.actualizado = False, ahora
    # cuentas de equipo (Claude por unidad): el producto sale del plan ("Standard" -> el de Anthropic con plan Standard)
    por_plan = {(p.plan or "").strip().lower(): p for p in prods.values() if (p.proveedor or "").lower() == "anthropic" and p.activo}
    cuentas = {c.id_externo: c for c in db.query(LicenciaCuentaEquipo).all()}
    vistas_c = set()
    for x in datos.get("equipos_licencias") or []:
        ext = _txt(x.get("id"), 60)
        if not ext:
            continue
        c = cuentas.get(ext)
        if c is None:
            c = cuentas[ext] = LicenciaCuentaEquipo(id_externo=ext)
            db.add(c)
        c.numero, c.unidad, c.lider = _txt(x.get("numero"), 20), _txt(x.get("unidad"), 120), _txt(x.get("lider"), 120)
        c.responsable, c.email, c.tipo = _txt(x.get("responsable"), 120), norm_email(x.get("email")), _txt(x.get("tipo"), 40)
        c.estado, c.activo, c.actualizado = _txt(x.get("estado"), 60), _activo(x.get("activo")), ahora
        p = por_plan.get(c.tipo.strip().lower())
        c.producto_id = p.id if p else None
        vistas_c.add(ext)
        res["cuentas_equipo"] += 1
    for ext, c in cuentas.items():
        if ext not in vistas_c and c.activo:
            c.activo, c.actualizado = False, ahora
    return res


# ---------------------------------------------------------------- costos reales por periodo (API / manual)
def aplicar_costos_periodo(db, filas, origen="api", ahora=None):
    """Upsert de costos reales por (producto, periodo AAAA-MM, workspace, moneda, origen). Lo usaran los conectores
    con costos (Anthropic, Adobe) con origen "api"; tambien la carga manual. Marca costo_origen del producto."""
    ahora = ahora or datetime.utcnow()
    res = {"filas": 0, "nuevas": 0}
    for f in filas:
        if not _PERIODO.match(f.get("periodo") or "") or f.get("monto") is None:
            continue
        p = db.get(LicenciaProducto, f["producto_id"])
        if p is None:
            continue
        moneda = f.get("moneda") or "USD"
        q = db.query(LicenciaCostoPeriodo).filter(
            LicenciaCostoPeriodo.producto_id == p.id, LicenciaCostoPeriodo.periodo == f["periodo"],
            LicenciaCostoPeriodo.workspace == (f.get("workspace") or ""), LicenciaCostoPeriodo.moneda == moneda,
            LicenciaCostoPeriodo.origen == origen).first()
        if q is None:
            q = LicenciaCostoPeriodo(producto_id=p.id, periodo=f["periodo"], workspace=f.get("workspace") or "", moneda=moneda,
                                     origen=origen, monto=0)
            db.add(q)
            res["nuevas"] += 1
        q.monto, q.cantidad, q.detalle, q.actualizado = f["monto"], f.get("cantidad"), _txt(f.get("detalle"), 500), ahora
        if origen == "api":
            p.costo_origen = "api"
        res["filas"] += 1
    return res


def costos_por_periodo(db, desde=None):
    """{periodo: {"total": {moneda: monto}, "productos": [{producto_id, producto, proveedor, workspace, moneda, monto,
    cantidad, origen}]}} ordenado del mas reciente al mas viejo."""
    q = db.query(LicenciaCostoPeriodo, LicenciaProducto).join(LicenciaProducto, LicenciaProducto.id == LicenciaCostoPeriodo.producto_id)
    if desde:
        q = q.filter(LicenciaCostoPeriodo.periodo >= desde)
    out = {}
    for c, p in q.order_by(LicenciaCostoPeriodo.periodo.desc(), LicenciaProducto.proveedor, LicenciaProducto.producto).all():
        per = out.setdefault(c.periodo, {"periodo": c.periodo, "total": {}, "productos": []})
        _suma(per["total"], c.moneda, _f(c.monto))
        per["productos"].append({"producto_id": p.id, "producto": p.producto, "proveedor": p.proveedor, "workspace": c.workspace or "",
                                 "moneda": c.moneda, "monto": _f(c.monto), "cantidad": c.cantidad, "origen": c.origen,
                                 "detalle": c.detalle or ""})
    return list(out.values())


# ---------------------------------------------------------------- costos teoricos (precio x licencias)
def _suma(destino, moneda, valor):
    if valor:
        destino[moneda] = round(destino.get(moneda, 0) + valor, 2)


def mensual_unitario(p):
    """{moneda: costo mensual de UNA licencia} (anual / 12). Vacio si no se cargo precio."""
    div = 12.0 if (p.periodo or "mensual") == "anual" else 1.0
    out = {}
    for moneda, v in (("USD", p.precio_usd), ("ARS", p.precio_ars)):
        if v is not None:
            out[moneda] = round(_f(v) / div, 4)
    return out


def _por(d, k):
    return d.setdefault(k, {})


def _uso(db):
    """Por producto: personas con asignacion individual, pares activos (1 licencia c/u) y cuentas de equipo activas."""
    ind = defaultdict(dict)       # producto -> {persona: asignacion}
    for a in db.query(LicenciaAsignacion).filter(LicenciaAsignacion.estado == "activa").all():
        ind[a.producto_id][a.persona] = a
    pares = defaultdict(list)
    for c in db.query(LicenciaCompartida).filter(LicenciaCompartida.activo.is_(True)).all():
        if c.producto_id:
            pares[c.producto_id].append(c)
    cuentas = defaultdict(list)
    for c in db.query(LicenciaCuentaEquipo).filter(LicenciaCuentaEquipo.activo.is_(True)).all():
        if c.producto_id:
            cuentas[c.producto_id].append(c)
    return ind, pares, cuentas


def _en_pares(pares):
    return {x for c in pares for x in (c.principal, c.secundario) if x}


def armar_producto(p, ind, pares, cuentas, hoy=None):
    hoy = hoy or date.today()
    unit = mensual_unitario(p)
    individuales = [k for k in ind if k not in _en_pares(pares)]
    en_uso = len(individuales) + len(pares) + len(cuentas)
    personas = len(set(ind) | _en_pares(pares))
    cupo = None if p.ilimitado else p.cupo
    libres = (cupo - en_uso) if cupo is not None else None
    pagadas = cupo if cupo is not None else en_uso     # se paga lo contratado; sin cupo cargado, lo que se usa
    mensual = {m: round(v * pagadas, 2) for m, v in unit.items()}
    dias = (p.fecha_renovacion - hoy).days if p.fecha_renovacion else None
    return {
        "id": p.id, "proveedor": p.proveedor, "producto": p.producto, "producto_externo": p.producto_externo or "",
        "tipo": p.tipo or "", "plan": p.plan or "", "sku": p.sku or "", "origen": p.origen, "id_externo": p.id_externo or "",
        "activo": bool(p.activo), "cupo": cupo, "ilimitado": bool(p.ilimitado), "cupo_manual": bool(p.cupo_manual),
        "asignadas": en_uso, "personas": personas, "individuales": len(individuales), "compartidas": len(pares),
        "cuentas_equipo": len(cuentas), "libres": libres, "excedido": cupo is not None and en_uso > cupo,
        "precio_usd": _f(p.precio_usd), "precio_ars": _f(p.precio_ars), "periodo": p.periodo or "mensual",
        "costo_origen": p.costo_origen or "manual", "workspace": p.workspace or "", "sin_precio": not unit,
        "mensual_unitario": unit, "costo_mensual": mensual, "costo_anual": {m: round(v * 12, 2) for m, v in mensual.items()},
        "costo_sin_asignar_mensual": {m: round(v * libres, 2) for m, v in unit.items()} if libres and libres > 0 else {},
        "fecha_renovacion": p.fecha_renovacion, "renovacion_dias": dias,
        "renueva_pronto": dias is not None and 0 <= dias <= config.LICENCIAS_RENOVACION_DIAS,
        "contrato": p.contrato or "", "notas": p.notas or "", "actualizado": p.actualizado,
    }


def reparto_centros(productos_db, uso, personas):
    """Costo mensual por centro de costo (o unidad): asignacion individual -> centro de la persona; licencia compartida
    -> el centro de imputacion (o su %), si no mitad a cada centro de las dos personas; cuenta de equipo -> su unidad;
    lo contratado sin usar -> "sin asignar"."""
    ind, pares, cuentas = uso
    centros = {}

    def poner(centro, unit, factor):
        c = centros.setdefault(centro or SIN_DATO, {})
        for m, v in unit.items():
            _suma(c, m, v * factor)
    for p in productos_db:
        if not p.activo:
            continue
        unit = mensual_unitario(p)
        if not unit:
            continue
        cubiertas = _en_pares(pares.get(p.id, []))
        for persona in ind.get(p.id, {}):
            if persona not in cubiertas:
                poner(_centro(personas.get(persona)), unit, 1)
        for c in pares.get(p.id, []):
            miembros = [x for x in (c.principal, c.secundario) if x]
            if c.imputacion:
                pct = (c.porcentaje or 100) / 100.0
                poner(c.imputacion, unit, pct)
                resto = 1 - pct
            else:
                resto = 1.0
            if resto > 0:
                for x in miembros or [None]:
                    poner(_centro(personas.get(x)), unit, resto / max(1, len(miembros)))
        for c in cuentas.get(p.id, []):
            poner(c.unidad or SIN_DATO, unit, 1)
        cupo = None if p.ilimitado else p.cupo
        en_uso = len([k for k in ind.get(p.id, {}) if k not in cubiertas]) + len(pares.get(p.id, [])) + len(cuentas.get(p.id, []))
        if cupo is not None and cupo > en_uso:
            poner(SIN_ASIGNAR, unit, cupo - en_uso)
    return [{"centro": k, "mensual": v, "anual": {m: round(x * 12, 2) for m, x in v.items()}}
            for k, v in sorted(centros.items(), key=lambda kv: -sum(kv[1].values()))]


def _centro(per):
    return (per.centro_costo or per.area) if per and (per.centro_costo or per.area) else SIN_DATO


def _equipos_por_persona(db):
    """usuario de Windows (lo que va antes de la @) -> activos de Atlas donde figura como usuario."""
    out = defaultdict(list)
    for a in db.query(Asset).filter(Asset.estado != "Dado de baja").all():
        for u in {(a.usuario or "").strip().lower(), ((a.usuario_alt or "").split("\\")[-1]).strip().lower()}:
            if u:
                out[u].append({"id": a.id, "nombre": a.nombre, "tipo": a.tipo, "sede": a.ubicacion or ""})
    return out


def _personas_vista(db, prods, uso, personas):
    ind, pares, _ = uso
    equipos = _equipos_por_persona(db)
    tiene = defaultdict(list)                     # persona -> [(producto, origen, desde, fraccion)]
    for pid, d in ind.items():
        if pid not in prods:
            continue
        cubiertas = _en_pares(pares.get(pid, []))
        for persona, a in d.items():
            if persona not in cubiertas:
                tiene[persona].append((prods[pid], a.origen, a.desde, 1.0, a.detalle or ""))
    for pid, lista in pares.items():
        if pid not in prods:
            continue
        for c in lista:
            miembros = [x for x in (c.principal, c.secundario) if x]
            for x in miembros:
                otro = next((y for y in miembros if y != x), "")
                desde = ind.get(pid, {}).get(x).desde if x in ind.get(pid, {}) else None
                tiene[x].append((prods[pid], "compartida", desde, 1.0 / len(miembros), "compartida con " + (otro or "-")))
    out = []
    for clave, items in tiene.items():
        d = personas.get(clave)
        usuario = clave.split("@")[0] if "@" in clave else ""
        eq = equipos.get(usuario, []) if usuario else []
        mensual = {}
        for prod, _, _, fr, _ in items:
            for m, v in prod["mensual_unitario"].items():
                _suma(mensual, m, v * fr)
        nombre = (d.nombre if d and d.nombre else "") or next(
            (c.principal_nombre if c.principal == clave else c.secundario_nombre
             for lst in pares.values() for c in lst if clave in (c.principal, c.secundario)), "")
        out.append({
            "persona": clave, "nombre": nombre, "legajo": d.legajo if d else "", "centro_costo": _centro(d),
            "area": d.area if d else "", "categoria": d.categoria if d else "",
            "estado_nomina": d.estado_nomina if d else "", "estado_externo": d.estado_externo if d else "",
            "cuenta_ad": d.cuenta_ad if d else "desconocida", "de_baja": de_baja(d), "deshabilitada": deshabilitada(d),
            "en_atlas": bool(eq), "equipos": eq[:10],
            "sede": (d.sede if d and d.sede else "") or next((e["sede"] for e in eq if e["sede"]), "") or SIN_DATO,
            "productos": [{"id": prod["id"], "proveedor": prod["proveedor"], "producto": prod["producto"], "origen": orig,
                           "desde": desde, "fraccion": fr, "detalle": det,
                           "mensual_unitario": {m: round(v * fr, 2) for m, v in prod["mensual_unitario"].items()}}
                          for prod, orig, desde, fr, det in items],
            "costo_mensual": mensual, "costo_anual": {m: round(v * 12, 2) for m, v in mensual.items()},
        })
    out.sort(key=lambda x: (x["nombre"] or x["persona"]).lower())
    return out


def resumir(productos, personas, centros):
    r = {"productos": len([p for p in productos if p["activo"]]), "asignadas": 0, "cupo": 0, "sin_cupo": 0, "libres": 0,
         "mensual": {}, "anual": {}, "sin_asignar_mensual": {}, "por_proveedor": {}, "renovaciones_proximas": 0,
         "excedidos": 0, "sin_precio": 0, "compartidas": 0, "cuentas_equipo": 0, "personas": len(personas),
         "personas_deshabilitadas": 0, "asignadas_deshabilitadas": 0, "personas_baja": 0, "asignadas_baja": 0,
         "centros": len([c for c in centros if c["centro"] not in (SIN_DATO, SIN_ASIGNAR)])}
    for p in productos:
        if not p["activo"]:
            continue
        r["asignadas"] += p["asignadas"]
        r["compartidas"] += p["compartidas"]
        r["cuentas_equipo"] += p["cuentas_equipo"]
        if p["cupo"] is not None:
            r["cupo"] += p["cupo"]
        else:
            r["sin_cupo"] += 1
        if p["libres"] and p["libres"] > 0:
            r["libres"] += p["libres"]
        for m, v in p["costo_mensual"].items():
            _suma(r["mensual"], m, v)
        for m, v in p["costo_anual"].items():
            _suma(r["anual"], m, v)
        for m, v in p["costo_sin_asignar_mensual"].items():
            _suma(r["sin_asignar_mensual"], m, v)
        prov = r["por_proveedor"].setdefault(p["proveedor"], {"productos": 0, "asignadas": 0, "mensual": {}, "anual": {}})
        prov["productos"] += 1
        prov["asignadas"] += p["asignadas"]
        for m, v in p["costo_mensual"].items():
            _suma(prov["mensual"], m, v)
        for m, v in p["costo_anual"].items():
            _suma(prov["anual"], m, v)
        r["renovaciones_proximas"] += p["renueva_pronto"]
        r["excedidos"] += p["excedido"]
        r["sin_precio"] += p["sin_precio"]
    for x in personas:
        if x["deshabilitada"]:
            r["personas_deshabilitadas"] += 1
            r["asignadas_deshabilitadas"] += len(x["productos"])
        if x["de_baja"]:
            r["personas_baja"] += 1
            r["asignadas_baja"] += len(x["productos"])
    return r


def _todo(db):
    uso = _uso(db)
    ind, pares, cuentas = uso
    hoy = date.today()
    prods_db = db.query(LicenciaProducto).order_by(LicenciaProducto.proveedor, LicenciaProducto.producto).all()
    productos = [armar_producto(p, ind.get(p.id, {}), pares.get(p.id, []), cuentas.get(p.id, []), hoy) for p in prods_db]
    activos = {p["id"]: p for p in productos if p["activo"]}
    claves = set()
    for d in ind.values():
        claves |= set(d)
    for lst in pares.values():
        claves |= _en_pares(lst)
    personas = {x.persona: x for x in db.query(LicenciaPersona).filter(LicenciaPersona.persona.in_(claves or {""})).all()}
    vista = _personas_vista(db, activos, uso, personas)
    centros = reparto_centros(prods_db, uso, personas)
    por_sede = {}
    for x in vista:
        s = por_sede.setdefault(x["sede"], {"personas": 0, "mensual": {}})
        s["personas"] += 1
        for m, v in x["costo_mensual"].items():
            _suma(s["mensual"], m, v)
    resumen = resumir(productos, vista, centros)
    resumen["por_sede"] = por_sede
    return productos, vista, resumen, centros


# ---------------------------------------------------------------- esquemas
class _Base(BaseModel):
    model_config = ConfigDict(extra="forbid")

    @field_validator("*", mode="after")
    @classmethod
    def _sin_credenciales(cls, v):
        if isinstance(v, str):
            v = v.strip()
            if tiene_credencial(v):
                raise ValueError("Atlas no guarda credenciales: dejalas en KeePassXC")
        return v


class ProductoIn(_Base):
    proveedor: str = Field("Otro", max_length=60)
    producto: str = Field(..., min_length=1, max_length=160)
    tipo: Optional[str] = Field("", max_length=60)
    plan: Optional[str] = Field("", max_length=80)
    sku: Optional[str] = Field("", max_length=80)
    cupo: Optional[int] = Field(None, ge=0, le=100000)
    precio_usd: Optional[float] = Field(None, ge=0, le=10_000_000)
    precio_ars: Optional[float] = Field(None, ge=0, le=10_000_000_000)
    periodo: Literal[PERIODOS] = "mensual"
    fecha_renovacion: Optional[date] = None
    contrato: Optional[str] = Field("", max_length=120)
    notas: Optional[str] = Field("", max_length=2000)


class ProductoUpdate(_Base):
    proveedor: Optional[str] = Field(None, max_length=60)
    producto: Optional[str] = Field(None, min_length=1, max_length=160)
    tipo: Optional[str] = Field(None, max_length=60)
    plan: Optional[str] = Field(None, max_length=80)
    sku: Optional[str] = Field(None, max_length=80)
    cupo: Optional[int] = Field(None, ge=0, le=100000)
    cupo_automatico: Optional[bool] = None     # True = volver al cupo que informa la fuente
    precio_usd: Optional[float] = Field(None, ge=0, le=10_000_000)
    precio_ars: Optional[float] = Field(None, ge=0, le=10_000_000_000)
    periodo: Optional[Literal[PERIODOS]] = None
    fecha_renovacion: Optional[date] = None
    contrato: Optional[str] = Field(None, max_length=120)
    notas: Optional[str] = Field(None, max_length=2000)
    activo: Optional[bool] = None


class AsignacionIn(_Base):
    producto_id: str = Field(..., max_length=60)
    persona: str = Field(..., max_length=200)
    nombre: Optional[str] = Field("", max_length=160)


class PersonaUpdate(_Base):
    cuenta_ad: Literal["activa", "deshabilitada", "desconocida"]


class CostoIn(_Base):
    producto_id: str = Field(..., max_length=60)
    periodo: str = Field(..., pattern=r"^\d{4}-(0[1-9]|1[0-2])$")
    moneda: Literal[MONEDAS] = "USD"
    monto: float = Field(..., ge=0, le=10_000_000_000)
    cantidad: Optional[int] = Field(None, ge=0, le=100000)
    workspace: Optional[str] = Field("", max_length=120)
    detalle: Optional[str] = Field("", max_length=500)


class CostosIn(_Base):
    costos: List[CostoIn] = Field(..., max_length=500)


def _ip(request):
    return request.client.host if request.client else ""


# ---------------------------------------------------------------- endpoints
@router.get("")
def listar(user: UserOut = Depends(require_modulo("licencias"))):
    db = SessionLocal()
    try:
        productos, _, resumen, centros = _todo(db)
        return {"productos": productos, "resumen": resumen, "centros": centros}
    finally:
        db.close()


@router.get("/personas")
def personas(user: UserOut = Depends(require_modulo("licencias"))):
    db = SessionLocal()
    try:
        return _todo(db)[1]
    finally:
        db.close()


@router.get("/compartidas")
def compartidas(user: UserOut = Depends(require_modulo("licencias"))):
    db = SessionLocal()
    try:
        prods = {p.id: p for p in db.query(LicenciaProducto).all()}
        personas = {x.persona: x for x in db.query(LicenciaPersona).all()}
        out = []
        for c in db.query(LicenciaCompartida).order_by(LicenciaCompartida.activo.desc(), LicenciaCompartida.sector).all():
            p = prods.get(c.producto_id)
            pp, ps = personas.get(c.principal), personas.get(c.secundario)
            out.append({"id": c.id, "producto": p.producto if p else "", "producto_id": c.producto_id, "sector": c.sector,
                        "principal": c.principal, "principal_nombre": (pp.nombre if pp and pp.nombre else c.principal_nombre),
                        "principal_centro": _centro(pp), "principal_baja": de_baja(pp),
                        "secundario": c.secundario, "secundario_nombre": (ps.nombre if ps and ps.nombre else c.secundario_nombre),
                        "secundario_centro": _centro(ps) if c.secundario else "", "secundario_baja": de_baja(ps),
                        "imputacion": c.imputacion, "porcentaje": c.porcentaje, "activo": bool(c.activo),
                        "mensual": mensual_unitario(p) if p else {}})
        return out
    finally:
        db.close()


@router.get("/cuentas-equipo")
def cuentas_equipo(user: UserOut = Depends(require_modulo("licencias"))):
    db = SessionLocal()
    try:
        prods = {p.id: p for p in db.query(LicenciaProducto).all()}
        return [{"id": c.id, "numero": c.numero, "unidad": c.unidad, "lider": c.lider, "responsable": c.responsable,
                 "email": c.email, "tipo": c.tipo, "estado": c.estado, "activo": bool(c.activo), "producto_id": c.producto_id,
                 "producto": prods[c.producto_id].producto if c.producto_id in prods else "",
                 "mensual": mensual_unitario(prods[c.producto_id]) if c.producto_id in prods else {}}
                for c in db.query(LicenciaCuentaEquipo).order_by(LicenciaCuentaEquipo.numero).all()]
    finally:
        db.close()


@router.get("/costos")
def costos(desde: Optional[str] = None, user: UserOut = Depends(require_modulo("licencias"))):
    if desde and not _PERIODO.match(desde):
        raise HTTPException(400, "desde: AAAA-MM")
    db = SessionLocal()
    try:
        return costos_por_periodo(db, desde)
    finally:
        db.close()


@router.post("/costos")
def cargar_costos(data: CostosIn, request: Request, user: UserOut = Depends(require_modulo("licencias", nivel="editar"))):
    """Carga manual del costo real de uno o varios meses (lo que dice la factura)."""
    db = SessionLocal()
    try:
        res = aplicar_costos_periodo(db, [c.model_dump() for c in data.costos], origen="manual")
        db.commit()
    finally:
        db.close()
    log_action(user.username, "costos", "licencias", "manual", res, ip=_ip(request))
    return res


@router.get("/productos/{pid}")
def ver_producto(pid: str, user: UserOut = Depends(require_modulo("licencias"))):
    db = SessionLocal()
    try:
        p = db.get(LicenciaProducto, pid)
        if p is None:
            raise HTTPException(404, "Producto no encontrado")
        ind, pares, cuentas = _uso(db)
        asig = (db.query(LicenciaAsignacion).filter(LicenciaAsignacion.producto_id == pid)
                .order_by(LicenciaAsignacion.estado, LicenciaAsignacion.persona).all())
        datos = {x.persona: x for x in db.query(LicenciaPersona).filter(
            LicenciaPersona.persona.in_({a.persona for a in asig} or {""})).all()}
        out = armar_producto(p, ind.get(pid, {}), pares.get(pid, []), cuentas.get(pid, []))
        out["asignaciones"] = [{"id": a.id, "persona": a.persona,
                                "nombre": a.nombre or (datos[a.persona].nombre if a.persona in datos else ""),
                                "centro_costo": _centro(datos.get(a.persona)), "origen": a.origen, "detalle": a.detalle or "",
                                "estado": a.estado, "desde": a.desde, "hasta": a.hasta,
                                "deshabilitada": deshabilitada(datos.get(a.persona)), "de_baja": de_baja(datos.get(a.persona))}
                               for a in asig]
        out["costos_periodo"] = [dict(x, periodo=per["periodo"]) for per in costos_por_periodo(db)
                                 for x in per["productos"] if x["producto_id"] == pid]
        return out
    finally:
        db.close()


@router.post("/productos")
def alta_producto(data: ProductoIn, request: Request, user: UserOut = Depends(require_modulo("licencias", nivel="editar"))):
    db = SessionLocal()
    try:
        ahora = datetime.utcnow()
        p = _nuevo_producto(db, "manual", "", ahora, proveedor=data.proveedor or "Otro", producto=data.producto, periodo=data.periodo)
        p.tipo, p.plan, p.sku = data.tipo or "", data.plan or "", data.sku or ""
        p.cupo, p.cupo_manual = data.cupo, data.cupo is not None
        p.precio_usd, p.precio_ars, p.fecha_renovacion = data.precio_usd, data.precio_ars, data.fecha_renovacion
        p.contrato, p.notas = data.contrato or "", data.notas or ""
        db.commit()
        log_action(user.username, "alta", "licencia_producto", p.id, {"producto": p.producto, "proveedor": p.proveedor}, ip=_ip(request))
        return armar_producto(p, {}, [], [])
    finally:
        db.close()


@router.put("/productos/{pid}")
def editar_producto(pid: str, data: ProductoUpdate, request: Request,
                    user: UserOut = Depends(require_modulo("licencias", nivel="editar"))):
    db = SessionLocal()
    try:
        p = db.get(LicenciaProducto, pid)
        if p is None:
            raise HTTPException(404, "Producto no encontrado")
        datos = data.model_dump(exclude_unset=True)
        cambios = {}
        if datos.pop("cupo_automatico", None):
            p.cupo_manual = False
            cambios["cupo"] = "automatico (fuente)"
        elif "cupo" in datos:
            cambios["cupo"] = [p.cupo, datos["cupo"]]
            p.cupo, p.cupo_manual = datos.pop("cupo"), True
        if p.origen in ORIGENES_EXTERNOS:      # nombre, proveedor, tipo y plan los define la fuente
            for k in ("producto", "proveedor", "tipo", "plan"):
                datos.pop(k, None)
        for k, v in datos.items():
            ant = getattr(p, k)
            if k in ("precio_usd", "precio_ars"):
                ant = _f(ant)
            if ant != v:
                cambios[k] = [str(ant) if ant is not None else None, str(v) if v is not None else None]
                setattr(p, k, v)
        p.actualizado = datetime.utcnow()
        db.commit()
        if cambios:
            log_action(user.username, "modificacion", "licencia_producto", p.id, cambios, ip=_ip(request))
        ind, pares, cuentas = _uso(db)
        return armar_producto(p, ind.get(p.id, {}), pares.get(p.id, []), cuentas.get(p.id, []))
    finally:
        db.close()


@router.post("/asignaciones")
def alta_asignacion(data: AsignacionIn, request: Request, user: UserOut = Depends(require_modulo("licencias", nivel="editar"))):
    email = norm_email(data.persona)
    if not email:
        raise HTTPException(400, "Ingresá el mail de la persona")
    db = SessionLocal()
    try:
        p = db.get(LicenciaProducto, data.producto_id)
        if p is None:
            raise HTTPException(404, "Producto no encontrado")
        if p.origen in ORIGENES_EXTERNOS:
            raise HTTPException(409, "Este producto lo define su fuente (UserManager / Adobe): se asigna allá y Atlas lo toma "
                                     "en la próxima importación")
        ya = db.query(LicenciaAsignacion).filter(LicenciaAsignacion.producto_id == p.id, LicenciaAsignacion.persona == email,
                                                 LicenciaAsignacion.estado == "activa").first()
        if ya:
            raise HTTPException(409, "Esa persona ya tiene este producto")
        a = LicenciaAsignacion(producto_id=p.id, persona=email, nombre=data.nombre or "", origen="manual", id_externo="",
                               detalle="", desde=datetime.utcnow(), estado="activa")
        db.add(a)
        _persona(db, email, data.nombre or "")
        db.commit()
        log_action(user.username, "asignacion", "licencia", a.id, {"producto": p.producto, "persona": email}, ip=_ip(request))
        return {"id": a.id, "estado": a.estado}
    finally:
        db.close()


@router.post("/asignaciones/{aid}/liberar")
def liberar(aid: str, request: Request, user: UserOut = Depends(require_modulo("licencias", nivel="editar"))):
    db = SessionLocal()
    try:
        a = db.get(LicenciaAsignacion, aid)
        if a is None:
            raise HTTPException(404, "Asignación no encontrada")
        if a.origen in ORIGENES_EXTERNOS:
            raise HTTPException(409, "Esta asignación la define su fuente (UserManager / Adobe): se libera allá y Atlas lo "
                                     "toma en la próxima importación")
        if a.estado == "activa":
            a.estado, a.hasta = "liberada", datetime.utcnow()
            db.commit()
            log_action(user.username, "liberacion", "licencia", a.id, {"persona": a.persona}, ip=_ip(request))
        return {"id": a.id, "estado": a.estado}
    finally:
        db.close()


@router.put("/personas/{clave}")
def editar_persona(clave: str, data: PersonaUpdate, request: Request,
                   user: UserOut = Depends(require_modulo("licencias", nivel="editar"))):
    c = norm_email(clave) or _txt(clave, 200).lower()
    if not c:
        raise HTTPException(400, "Persona inválida")
    db = SessionLocal()
    try:
        p = _persona(db, c)
        p.cuenta_ad = data.cuenta_ad
        db.commit()
        log_action(user.username, "modificacion", "licencia_persona", c, {"cuenta_ad": data.cuenta_ad}, ip=_ip(request))
        return {"persona": c, "cuenta_ad": p.cuenta_ad}
    finally:
        db.close()


async def _leer_archivo(archivo):
    contenido = await archivo.read(MAX_ARCHIVO + 1)
    if len(contenido) > MAX_ARCHIVO:
        raise HTTPException(413, "El archivo supera los 5 MB")
    return contenido


COLS_PRODUCTO_GEN = ("producto", "product", "licencia", "seattier", "seattype", "tipodeasiento", "tier", "plan", "seat")
COLS_PROVEEDOR = ("proveedor", "vendor", "provider")
COLS_NOMBRE_GEN = ("nombre", "name", "fullname", "nombreyapellido", "nombrecompleto")


def leer_csv(contenido):
    """CSV de miembros (Claude, Adobe u otro) o generico: columnas por nombre, sin importar mayusculas ni idioma.
    Mail obligatorio (email / correo / mail); producto opcional (producto / seat tier / plan...), proveedor y nombre
    opcionales. Acepta , o ; y BOM."""
    texto = _texto(contenido)
    lineas = texto.splitlines()
    if not lineas:
        return []
    sep = max((",", ";", "\t"), key=lineas[0].count)
    lector = csv.reader(io.StringIO(texto), delimiter=sep)
    idx = {}
    for i, n in enumerate(next(lector, [])):
        idx.setdefault(_col(n), i)
    c_mail = _buscar(idx, COLS_EMAIL)
    if c_mail is None:
        return []
    c_prod, c_prov = _buscar(idx, COLS_PRODUCTO_GEN), _buscar(idx, COLS_PROVEEDOR)
    c_nom, c_ape = _buscar(idx, COLS_NOMBRE_GEN + COLS_NOMBRE), _buscar(idx, COLS_APELLIDO)

    def val(fila, i):
        return fila[i].strip() if i is not None and i < len(fila) else ""
    filas = []
    for fila in lector:
        email = norm_email(val(fila, c_mail))
        if not email:
            continue
        nombre = " ".join(x for x in (_txt(val(fila, c_nom), 80), _txt(val(fila, c_ape), 80)) if x)
        filas.append({"email": email, "nombre": nombre, "producto": _txt(val(fila, c_prod), 160),
                      "proveedor": _txt(val(fila, c_prov), 60)})
    return filas


def _producto_para(prods, f):
    """Producto de una fila: (proveedor, producto) exacto, o el unico que termina con ese texto ("Premium" ->
    "Claude Team Premium"), o None."""
    nombre = f["producto"].lower()
    if f["proveedor"]:
        p = prods.get((f["proveedor"].lower(), nombre))
        if p is not None:
            return p
    candidatos = [p for (prov, prod), p in prods.items() if prod == nombre or prod.endswith(" " + nombre)]
    if f["proveedor"]:
        candidatos = [p for p in candidatos if (p.proveedor or "").lower() == f["proveedor"].lower()] or candidatos
    return candidatos[0] if len(candidatos) == 1 else None


@router.post("/importar")
async def importar(request: Request, archivo: UploadFile = File(...), producto_id: Optional[str] = Form(None),
                   user: UserOut = Depends(require_modulo("licencias", nivel="editar"))):
    """CSV de miembros o generico. Con producto_id, todas las filas van a ese producto (p. ej. el CSV de miembros de
    Claude Team Standard); si no, cada fila dice su producto (si no existe, se crea como producto manual)."""
    filas = leer_csv(await _leer_archivo(archivo))
    if not filas:
        raise HTTPException(400, "El archivo no trae una columna de mail (email / correo) con datos")
    db = SessionLocal()
    res = {"filas": len(filas), "productos_nuevos": 0, "asignaciones_nuevas": 0, "ya_estaban": 0, "externas_ignoradas": 0,
           "sin_producto": 0}
    try:
        ahora = datetime.utcnow()
        fijo = db.get(LicenciaProducto, producto_id) if producto_id else None
        if producto_id and fijo is None:
            raise HTTPException(404, "Producto no encontrado")
        prods = {}
        for p in db.query(LicenciaProducto).all():
            prods.setdefault(((p.proveedor or "").lower(), (p.producto or "").lower()), p)
        for f in filas:
            p = fijo or (_producto_para(prods, f) if f["producto"] else None)
            if p is None:
                if not f["producto"]:
                    res["sin_producto"] += 1
                    continue
                prov = f["proveedor"] or "Otro"
                p = prods[(prov.lower(), f["producto"].lower())] = _nuevo_producto(db, "manual", "", ahora, proveedor=prov,
                                                                                   producto=f["producto"], periodo="mensual")
                res["productos_nuevos"] += 1
            if p.origen in ORIGENES_EXTERNOS:
                res["externas_ignoradas"] += 1
                continue
            ya = db.query(LicenciaAsignacion).filter(LicenciaAsignacion.producto_id == p.id, LicenciaAsignacion.persona == f["email"],
                                                     LicenciaAsignacion.estado == "activa").first()
            if ya:
                res["ya_estaban"] += 1
                continue
            db.add(LicenciaAsignacion(producto_id=p.id, persona=f["email"], nombre=f["nombre"], origen="csv", id_externo="",
                                      detalle="", desde=ahora, estado="activa"))
            db.flush()
            _persona(db, f["email"], f["nombre"], None, ahora)
            res["asignaciones_nuevas"] += 1
        db.commit()
    finally:
        db.close()
    log_action(user.username, "importacion", "licencias", "csv", res, ip=_ip(request))
    return res


@router.post("/importar-adobe")
async def importar_adobe(request: Request, archivo: UploadFile = File(...),
                         user: UserOut = Depends(require_modulo("licencias", nivel="editar"))):
    try:
        filas = leer_csv_adobe(await _leer_archivo(archivo))
    except ValueError as e:
        raise HTTPException(400, str(e)) from None
    if not filas:
        raise HTTPException(400, "El archivo no trae usuarios con mail")
    db = SessionLocal()
    try:
        res = aplicar_csv_adobe(db, filas)
        db.commit()
    finally:
        db.close()
    log_action(user.username, "importacion", "licencias", "adobe-csv", res, ip=_ip(request))
    return res


@router.post("/importar-usermanager")
async def importar_usermanager(request: Request, archivo: UploadFile = File(...),
                               user: UserOut = Depends(require_modulo("licencias", nivel="editar"))):
    """JSON generado por herramientas/licencias/exportar_usermanager.py (idempotente: se puede subir las veces que sea)."""
    try:
        datos = json.loads(_texto(await _leer_archivo(archivo)))
    except ValueError:
        raise HTTPException(400, "El archivo no es un JSON válido") from None
    db = SessionLocal()
    try:
        try:
            res = aplicar_usermanager(db, datos)
        except ValueError as e:
            db.rollback()
            raise HTTPException(400, str(e)) from None
        db.commit()
    finally:
        db.close()
    log_action(user.username, "importacion", "licencias", "usermanager", res, ip=_ip(request))
    return res


def _monto(d):
    return " / ".join("%s %s" % (m, ("%.2f" % v).replace(".", ",")) for m, v in d.items()) if d else ""


@router.get("/exportar.csv")
def exportar(user: UserOut = Depends(require_modulo("licencias"))):
    db = SessionLocal()
    try:
        productos, personas, _, centros = _todo(db)
    finally:
        db.close()
    out = io.StringIO()
    w = csv.writer(out, delimiter=";")
    w.writerow(["persona", "nombre", "legajo", "centro de costo", "sede", "proveedor", "producto", "origen", "detalle",
                "costo mensual", "costo anual", "baja / deshabilitada"])
    for x in personas:
        for p in x["productos"]:
            w.writerow([x["persona"], x["nombre"], x["legajo"], x["centro_costo"], x["sede"], p["proveedor"], p["producto"],
                        p["origen"], p["detalle"], _monto(p["mensual_unitario"]),
                        _monto({m: v * 12 for m, v in p["mensual_unitario"].items()}),
                        "baja" if x["de_baja"] else ("si" if x["deshabilitada"] else "")])
    for p in productos:
        if p["activo"] and p["libres"] and p["libres"] > 0:
            w.writerow(["(sin asignar x%d)" % p["libres"], "", "", SIN_ASIGNAR, "", p["proveedor"], p["producto"], p["origen"], "",
                        _monto(p["costo_sin_asignar_mensual"]), _monto({m: v * 12 for m, v in p["costo_sin_asignar_mensual"].items()}), ""])
    w.writerow([])
    w.writerow(["centro de costo", "", "", "", "", "", "", "", "", "costo mensual", "costo anual", ""])
    for c in centros:
        w.writerow([c["centro"], "", "", "", "", "", "", "", "", _monto(c["mensual"]), _monto(c["anual"]), ""])
    return Response("﻿" + out.getvalue(), media_type="text/csv; charset=utf-8",
                    headers={"Content-Disposition": 'attachment; filename="licencias-atlas.csv"'})


@router.get("/conector")
def estado_conector(user: UserOut = Depends(require_modulo("licencias"))):
    db = SessionLocal()
    try:
        return conectores.estado(db, ("adobe",))[0]
    finally:
        db.close()


@router.post("/conector/actualizar")
def actualizar_conector(request: Request, user: UserOut = Depends(require_modulo("licencias", nivel="editar"))):
    if not conectores.configurado("adobe"):
        return {"status": "sin_configurar", "falta": conectores.falta_config("adobe")}
    db = SessionLocal()
    try:
        conectores._fila(db, "adobe").pedida = True
        db.commit()
    finally:
        db.close()
    import threading
    threading.Thread(target=conectores.correr, args=("adobe",), daemon=True).start()
    log_action(user.username, "actualizar_conectores", "conectores", "adobe", {}, ip=_ip(request))
    return {"status": "encolada"}


def proximas_renovaciones(productos, hoy=None):
    hoy = hoy or date.today()
    lim = hoy + timedelta(days=config.LICENCIAS_RENOVACION_DIAS)
    return [p for p in productos if p["activo"] and p["fecha_renovacion"] and hoy <= p["fecha_renovacion"] <= lim]
