# -*- coding: utf-8 -*-
"""Costo mensual por persona: licencias + equipos (base del futuro modulo de Usuarios; sin pantalla todavia).

Criterio (docs/costos-por-persona.md):
  - Persona: email o usuario de Windows en minusculas. El usuario de Windows de un equipo se cruza con el mail de las
    licencias por la parte antes de la @ ("jiriarte" = "jiriarte@llyasoc.com").
  - Licencias: costo mensual de cada licencia (precio / 12 si es anual) repartido entre principal y segundo usuario
    segun porcentaje_principal (vacio = 50/50 con segundo usuario). Mismo calculo que la vista de Licencias.
  - Equipos: costo de compra / vida util en meses (la del equipo o la de su tipo, config.VIDA_UTIL_MESES), repartido
    igual entre el usuario del equipo y su segundo usuario. Sin costo, sin moneda o sin vida util = "sin dato".
  - Monedas separadas (USD y ARS no se convierten).
  - Centro de costo: el de la nomina / licencias; si no hay, el cargado en su equipo.
"""
from fastapi import APIRouter, Depends

import config
import licencias
from auth import UserOut, require_modulo
from ciclo_activos import AssetAdmin
from database import Asset, LicenciaAsignacion, LicenciaPersona, SessionLocal
from reparto import clave_persona, fracciones, norm_centro, parte_local

router = APIRouter(prefix="/api/costos", tags=["costos"])
SIN_DATO = "sin dato"


def _suma(d, moneda, v):
    if v:
        d[moneda] = round(d.get(moneda, 0) + v, 2)


def mensual_equipo(a, adm):
    """{moneda: costo mensual} del equipo completo, o None si falta el costo, la moneda o la vida util."""
    if not adm or adm.costo is None or not (adm.moneda or ""):
        return None
    meses = adm.vida_util_meses or config.VIDA_UTIL_MESES.get(a.tipo or "")
    if not meses:
        return None
    return {adm.moneda: round(float(adm.costo) / meses, 4)}


def costos_por_persona(db):
    _, vista, _, _ = licencias._todo(db)
    personas = {}
    por_local = {}                       # parte local del mail -> clave (para cruzar con el usuario de Windows)

    def persona(clave, nombre=""):
        if clave not in personas:
            personas[clave] = {"persona": clave, "nombre": nombre, "centro_costo": SIN_DATO, "licencias": {}, "equipos": {},
                               "total": {}, "licencias_detalle": [], "equipos_detalle": [], "equipos_sin_costo": 0}
            if "@" in clave:
                por_local.setdefault(parte_local(clave), clave)
        elif nombre and not personas[clave]["nombre"]:
            personas[clave]["nombre"] = nombre
        return personas[clave]

    for x in vista:
        p = persona(x["persona"], x["nombre"])
        p["centro_costo"] = x["centro_costo"]
        for prod in x["productos"]:
            p["licencias_detalle"].append({"producto": prod["producto"], "proveedor": prod["proveedor"],
                                           "fraccion": round(prod["fraccion"], 4), "mensual": prod["mensual_unitario"]})
            for m, v in prod["mensual_unitario"].items():
                _suma(p["licencias"], m, v)

    def clave_equipo(usuario):
        u = clave_persona(usuario)
        if not u:
            return ""
        if "@" in u:
            return u
        return por_local.get(u, u)

    for a, adm in db.query(Asset, AssetAdmin).outerjoin(AssetAdmin, AssetAdmin.asset_id == Asset.id).filter(
            Asset.estado != "Dado de baja").all():
        sec = (adm.usuario_secundario or "") if adm else ""
        principal = clave_equipo(a.usuario)
        if not principal and not sec:
            continue
        mensual = mensual_equipo(a, adm)
        fp, fs = fracciones(adm.porcentaje_principal if adm else None, bool(sec))
        centro = norm_centro(adm.centro_costo) if adm and adm.centro_costo else ""
        for clave, fr, nombre in ((principal, fp, ""), (clave_equipo(sec), fs, adm.usuario_secundario_nombre if adm else "")):
            if not clave or fr <= 0:
                continue
            p = persona(clave, nombre)
            if centro and p["centro_costo"] == SIN_DATO:
                p["centro_costo"] = centro
            parte = {m: round(v * fr, 2) for m, v in mensual.items()} if mensual else None
            p["equipos_detalle"].append({"id": a.id, "nombre": a.nombre, "tipo": a.tipo, "fraccion": round(fr, 4),
                                         "mensual": parte, "sin_dato": parte is None})
            if parte is None:
                p["equipos_sin_costo"] += 1
            else:
                for m, v in parte.items():
                    _suma(p["equipos"], m, v)
    for p in personas.values():
        for parte in (p["licencias"], p["equipos"]):
            for m, v in parte.items():
                _suma(p["total"], m, v)
    return sorted(personas.values(), key=lambda x: (x["nombre"] or x["persona"]).lower())


@router.get("/personas")
def personas(user: UserOut = Depends(require_modulo("licencias", "activos"))):
    db = SessionLocal()
    try:
        return costos_por_persona(db)
    finally:
        db.close()


@router.get("/centros")
def centros(user: UserOut = Depends(require_modulo("licencias", "activos"))):
    """Centros de costo ya usados en Atlas (sugerencias del campo; no hay tabla maestra)."""
    db = SessionLocal()
    try:
        vals = set()
        for (c,) in db.query(LicenciaPersona.centro_costo).distinct():
            vals.add(norm_centro(c))
        for (c,) in db.query(LicenciaAsignacion.centro_costo).distinct():
            vals.add(norm_centro(c))
        for (c,) in db.query(AssetAdmin.centro_costo).distinct():
            vals.add(norm_centro(c))
        return sorted(v for v in vals if v)
    finally:
        db.close()

