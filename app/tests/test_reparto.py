# -*- coding: utf-8 -*-
"""Segundo usuario, % de reparto y centro de costo: en las asignaciones de licencias y en los equipos (asset_admin),
y el costo mensual por persona (licencias + equipos) de /api/costos/personas."""
import os

from alembic import command
from alembic.config import Config
from sqlalchemy import text

import database
import licencias
import seed
from conftest import SYNC_KEY, bearer

INI = os.path.join(os.path.dirname(__file__), "..", "backend", "alembic.ini")
NB = {"nombre": "NB-R-01", "tipo": "Notebook", "marca": "LENOVO", "modelo": "ThinkPad E14", "serial": "TEST-R-01",
      "usuario": "ana", "ubicacion": "CABA", "estado": "Activo"}


def _sync(client, **extra):
    r = client.post("/api/sync", json=dict(NB, **extra), headers={"X-Sync-Key": SYNC_KEY})
    assert r.status_code == 200, r.text


def _activo(client, token, serial="TEST-R-01"):
    return next(a for a in client.get("/api/assets", headers=bearer(token)).json() if a["serial"] == serial)


def _producto(client, token, **datos):
    r = client.post("/api/licencias/productos", headers=bearer(token), json=dict({"proveedor": "Otro", "periodo": "mensual"}, **datos))
    assert r.status_code == 200, r.text
    return r.json()["id"]


def _centros(client, token):
    return {c["centro"]: c["mensual"] for c in client.get("/api/licencias", headers=bearer(token)).json()["centros"]}


def _personas(client, token):
    return {x["persona"]: x for x in client.get("/api/licencias/personas", headers=bearer(token)).json()}


def _nomina(**centros):
    db = database.SessionLocal()
    try:
        for clave, centro in centros.items():
            licencias._persona(db, clave.replace("_", ".") + "@ejemplo.com").centro_costo = centro
        db.commit()
    finally:
        db.close()


# ---------------------------------------------------------------- licencias
def test_licencia_compartida_reparte_costo_por_persona_y_centro(client, token):
    pid = _producto(client, token, producto="Acrobat X", cupo=2, precio_usd=100)
    _nomina(ana="AUDITORIA", bruno="IMPUESTOS")
    r = client.post("/api/licencias/asignaciones", headers=bearer(token),
                    json={"producto_id": pid, "persona": "ana@ejemplo.com", "nombre": "Ana",
                          "secundario": "Bruno@Ejemplo.com", "secundario_nombre": "Bruno", "porcentaje_principal": 70})
    assert r.status_code == 200, r.text
    per = _personas(client, token)
    assert per["ana@ejemplo.com"]["costo_mensual"] == {"USD": 70} and per["bruno@ejemplo.com"]["costo_mensual"] == {"USD": 30}
    c = _centros(client, token)
    assert c["AUDITORIA"] == {"USD": 70} and c["IMPUESTOS"] == {"USD": 30} and c["sin asignar"] == {"USD": 100}
    prod = client.get("/api/licencias/productos/" + pid, headers=bearer(token)).json()
    assert prod["asignadas"] == 1 and prod["compartidas"] == 1 and prod["personas"] == 2
    a = prod["asignaciones"][0]
    assert a["secundario"] == "bruno@ejemplo.com" and a["porcentaje_efectivo"] == 70
    # centro de la asignacion: manda sobre el de cada persona (normalizado)
    r = client.put("/api/licencias/asignaciones/" + a["id"], headers=bearer(token), json={"centro_costo": "  caba 1-aud  ea "})
    assert r.status_code == 200 and r.json()["centro_costo"] == "CABA 1-AUD EA"
    assert _centros(client, token)["CABA 1-AUD EA"] == {"USD": 100}
    # sin % cargado y con segundo usuario: 50/50; sin segundo usuario: 100 % al principal
    client.put("/api/licencias/asignaciones/" + a["id"], headers=bearer(token), json={"porcentaje_principal": None})
    assert _personas(client, token)["ana@ejemplo.com"]["costo_mensual"] == {"USD": 50}
    client.put("/api/licencias/asignaciones/" + a["id"], headers=bearer(token), json={"secundario": ""})
    per = _personas(client, token)
    assert per["ana@ejemplo.com"]["costo_mensual"] == {"USD": 100} and "bruno@ejemplo.com" not in per


def test_el_segundo_usuario_no_puede_ser_el_principal(client, token):
    pid = _producto(client, token, producto="Claude X", precio_usd=30)
    r = client.post("/api/licencias/asignaciones", headers=bearer(token),
                    json={"producto_id": pid, "persona": "ana@ejemplo.com", "secundario": "ANA@ejemplo.com"})
    assert r.status_code == 422
    aid = client.post("/api/licencias/asignaciones", headers=bearer(token),
                      json={"producto_id": pid, "persona": "ana@ejemplo.com"}).json()["id"]
    for mismo in ("ana", "TANGO\\ana", "Ana@Ejemplo.com"):
        r = client.put("/api/licencias/asignaciones/" + aid, headers=bearer(token), json={"secundario": mismo})
        assert r.status_code == 422, mismo


def test_reimportar_el_csv_de_adobe_no_pisa_el_reparto(client, token):
    seed.seed_licencias()
    csv_ = ("Correo electrónico,Nombre,Apellidos,Funciones de administrador,Grupos de usuarios,Productos de equipo\n"
            'ana@llyasoc.com,Ana,Prueba,,,"Acrobat Premium for teams (DIRECT - X1)"\n'
            'bruno@llyasoc.com,Bruno,Prueba,,,"Acrobat Premium for teams (DIRECT - X1)"\n').encode("utf-8-sig")

    def importar():
        db = database.SessionLocal()
        try:
            licencias.aplicar_csv_adobe(db, licencias.leer_csv_adobe(csv_))
            db.commit()
        finally:
            db.close()
    importar()
    prods = {p["producto"]: p for p in client.get("/api/licencias", headers=bearer(token)).json()["productos"]}
    acro = prods["Acrobat Premium para equipos"]
    assert acro["asignadas"] == 2
    ficha = client.get("/api/licencias/productos/" + acro["id"], headers=bearer(token)).json()
    ana = next(a for a in ficha["asignaciones"] if a["persona"] == "ana@llyasoc.com")
    r = client.put("/api/licencias/asignaciones/" + ana["id"], headers=bearer(token),
                   json={"secundario": "bruno@llyasoc.com", "secundario_nombre": "Bruno", "porcentaje_principal": 60,
                         "centro_costo": "CABA 1"})
    assert r.status_code == 200, r.text
    importar()      # la fuente solo trae al principal: no toca segundo usuario, % ni centro
    ficha = client.get("/api/licencias/productos/" + acro["id"], headers=bearer(token)).json()
    ana = next(a for a in ficha["asignaciones"] if a["persona"] == "ana@llyasoc.com")
    assert (ana["secundario"], ana["porcentaje_principal"], ana["centro_asignacion"]) == ("bruno@llyasoc.com", 60, "CABA 1")
    # Bruno usa la licencia de Ana: su propia asignacion del CSV no suma otra licencia
    bruno = next(a for a in ficha["asignaciones"] if a["persona"] == "bruno@llyasoc.com")
    assert bruno["duplicada"] and ficha["asignadas"] == 1


# ---------------------------------------------------------------- equipos
def test_equipo_con_segundo_usuario_y_centro_el_agente_no_lo_pisa(client, token):
    _sync(client)
    aid = _activo(client, token)["id"]
    r = client.put("/api/ciclo/%s/admin" % aid, headers=bearer(token),
                   json={"usuario_secundario": "TANGO\\Carlos", "usuario_secundario_nombre": "Carlos",
                         "porcentaje_principal": 60, "centro_costo": "caba 1-aud"})
    assert r.status_code == 200, r.text
    a = _activo(client, token)
    assert (a["usuario_secundario"], a["porcentaje_principal"], a["centro_costo"]) == ("carlos", 60, "CABA 1-AUD")
    _sync(client, usuario="otro.usuario", comentarios="")     # el agente reporta de nuevo
    a = _activo(client, token)
    assert (a["usuario_secundario"], a["centro_costo"]) == ("carlos", "CABA 1-AUD")
    hist = client.get("/api/assets/%s/historial" % aid, headers=bearer(token)).json()
    assert {"usuario_secundario", "centro_costo"} <= {h["campo"] for h in hist}
    # el segundo usuario no puede ser el mismo que el principal
    r = client.put("/api/ciclo/%s/admin" % aid, headers=bearer(token), json={"usuario_secundario": "otro.usuario@llyasoc.com"})
    assert r.status_code == 422
    # sugerencias de centros: los ya usados en Atlas
    assert "CABA 1-AUD" in client.get("/api/costos/centros", headers=bearer(token)).json()


def test_filtro_por_centro_en_la_lista_de_activos(client, token):
    _sync(client)
    _sync(client, serial="TEST-R-02", nombre="NB-R-02")
    aid = _activo(client, token)["id"]
    client.put("/api/ciclo/%s/admin" % aid, headers=bearer(token), json={"centro_costo": "PYMES"})
    lista = client.get("/api/assets", headers=bearer(token)).json()
    assert [a["serial"] for a in lista if a["centro_costo"] == "PYMES"] == ["TEST-R-01"]
    assert next(a for a in lista if a["serial"] == "TEST-R-02")["centro_costo"] == ""


# ---------------------------------------------------------------- costo por persona
def test_costo_por_persona_licencias_y_equipos(client, token):
    pid = _producto(client, token, producto="Claude Y", precio_usd=30)
    pid2 = _producto(client, token, producto="Lex Y", precio_ars=120000, periodo="anual")
    for p in (pid, pid2):
        client.post("/api/licencias/asignaciones", headers=bearer(token), json={"producto_id": p, "persona": "ana@ejemplo.com"})
    _sync(client)                                            # notebook de "ana" (usuario de Windows)
    _sync(client, serial="TEST-R-02", nombre="PC-R-02", tipo="CPU", usuario="ana")
    aid = _activo(client, token)["id"]
    client.put("/api/ciclo/%s/admin" % aid, headers=bearer(token),
               json={"costo": 1200, "moneda": "USD", "vida_util_meses": 12, "usuario_secundario": "carlos",
                     "centro_costo": "AUDITORIA"})
    r = client.get("/api/costos/personas", headers=bearer(token))
    assert r.status_code == 200, r.text
    per = {x["persona"]: x for x in r.json()}
    ana = per["ana@ejemplo.com"]                              # el usuario de Windows "ana" se cruza con el mail
    assert ana["licencias"] == {"USD": 30, "ARS": 10000}      # monedas separadas (Lex anual / 12)
    assert ana["equipos"] == {"USD": 50} and ana["equipos_sin_costo"] == 1    # 1200/12 a medias; la PC sin costo
    assert ana["total"] == {"USD": 80, "ARS": 10000} and ana["centro_costo"] == "AUDITORIA"
    assert per["carlos"]["equipos"] == {"USD": 50} and per["carlos"]["licencias"] == {}
    assert any(e["sin_dato"] for e in ana["equipos_detalle"])


# ---------------------------------------------------------------- migracion
def test_la_migracion_pasa_las_compartidas_a_la_asignacion(client):
    cfg = Config(INI)
    with database.engine.begin() as con:   # base como antes de 0013
        cfg.attributes["connection"] = con
        command.downgrade(cfg, "0012")
    with database.engine.begin() as con:
        con.execute(text("INSERT INTO licencia_producto (id, proveedor, producto, origen, activo) VALUES "
                         "('PA', 'Adobe', 'Acrobat', 'usermanager', 1)"))
        con.execute(text("INSERT INTO licencia_asignacion (id, producto_id, persona, nombre, origen, id_externo, detalle, estado) "
                         "VALUES ('A1', 'PA', 'ana@ejemplo.com', 'Ana', 'usermanager', 'X1', '', 'activa')"))
        con.execute(text("INSERT INTO licencia_compartida (id, producto_id, id_externo, sector, principal, principal_nombre, "
                         "secundario, secundario_nombre, imputacion, porcentaje, activo) VALUES "
                         "('C1', 'PA', 'P1', 'Aud', 'ana@ejemplo.com', 'Ana', 'bruno@ejemplo.com', 'Bruno', '', NULL, 1), "
                         "('C2', 'PA', 'P2', 'Pymes', 'nombre:dario', 'Dario', 'ext@otra.com', 'Ext', 'cor-pymes', 40, 1)"))
    database.init_db()
    db = database.SessionLocal()
    try:
        a1 = db.get(database.LicenciaAsignacion, "A1")
        assert (a1.secundario, a1.secundario_nombre, a1.centro_costo) == ("bruno@ejemplo.com", "Bruno", "")
        par = db.query(database.LicenciaAsignacion).filter(database.LicenciaAsignacion.id_externo == "par-P2").one()
        assert (par.persona, par.secundario, par.centro_costo, par.estado) == ("nombre:dario", "ext@otra.com", "COR-PYMES", "activa")
        assert db.get(licencias.AssetAdmin, "no-existe") is None   # asset_admin con las columnas nuevas
    finally:
        db.close()
    database.init_db()       # idempotente: no duplica
    db = database.SessionLocal()
    try:
        assert db.query(database.LicenciaAsignacion).filter(database.LicenciaAsignacion.id_externo == "par-P2").count() == 1
    finally:
        db.close()
