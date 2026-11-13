# -*- coding: utf-8 -*-
"""Licencias: catalogo inicial (sin costos), costos (USD/ARS, compartidas, cuentas de equipo, centros de costo, por mes),
carga manual y CSV de miembros, UserManager (exportador + importacion con datos FICTICIOS), Adobe (CSV y API con `http`
falso) y permisos. Ninguna prueba toca la red ni la base real del UserManager."""
import importlib.util
import json
import os
import sqlite3
from datetime import date, timedelta

import pytest
from alembic import command
from alembic.config import Config

import config
import conectores
import database
import licencias
import seed
from auth import User, UserModulo, plantilla
from conftest import bearer, clave_valida, crear_usuario_db, login

INI = os.path.join(os.path.dirname(__file__), "..", "backend", "alembic.ini")
HERRAMIENTAS = os.path.join(os.path.dirname(__file__), "..", "..", "herramientas", "licencias")
CLAVE = clave_valida()
ORG = "ABC123@AdobeOrg"
UMAPI = "https://um.adobe.test/v2/usermanagement"
IMS = "https://ims.adobe.test/ims/token/v3"


def _modulo(nombre):
    spec = importlib.util.spec_from_file_location(nombre, os.path.join(HERRAMIENTAS, nombre + ".py"))
    m = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(m)
    return m


def _productos(client, token):
    r = client.get("/api/licencias", headers=bearer(token))
    assert r.status_code == 200, r.text
    d = r.json()
    return {p["id_externo"] or p["producto"]: p for p in d["productos"]}, d["resumen"], d["centros"]


# ---------------------------------------------------------------- catalogo inicial
def test_catalogo_inicial_sin_costos_ni_personas_e_idempotente(client, token):
    assert seed.seed_licencias() == [x[1] for x in licencias.CATALOGO]
    p, r, _ = _productos(client, token)
    assert len(p) == 8 and r["personas"] == 0 and r["asignadas"] == 0 and r["mensual"] == {}
    assert p["Acrobat Premium para equipos"]["cupo"] == 66 and p["Photoshop"]["cupo"] == 1
    assert p["Claude Team Standard"]["cupo"] is None and p["Claude Team Standard"]["plan"] == "Team"
    assert all(x["precio_usd"] is None and x["precio_ars"] is None and x["sin_precio"] for x in p.values())
    # el usuario carga un costo: correr el seed otra vez no duplica ni lo pisa
    pid = p["Photoshop"]["id"]
    client.put("/api/licencias/productos/" + pid, headers=bearer(token), json={"precio_usd": 30, "cupo": 2})
    assert seed.seed_licencias() == []
    p, r, _ = _productos(client, token)
    assert len(p) == 8 and p["Photoshop"]["precio_usd"] == 30 and p["Photoshop"]["costo_mensual"] == {"USD": 60}


# ---------------------------------------------------------------- costos teoricos y carga manual
def test_costos_usd_y_ars_sin_asignar_y_por_persona(client, token):
    h = bearer(token)
    a = client.post("/api/licencias/productos", headers=h, json={"proveedor": "Anthropic", "producto": "Claude Team", "cupo": 5,
                                                                 "precio_usd": 30, "periodo": "mensual"}).json()
    b = client.post("/api/licencias/productos", headers=h, json={"proveedor": "Microsoft", "producto": "M365", "cupo": 2,
                                                                 "precio_usd": 120, "precio_ars": 120000, "periodo": "anual"}).json()
    for prod, mail in ((a, "ana@ejemplo.com"), (a, "beto@ejemplo.com"), (b, "ana@ejemplo.com")):
        assert client.post("/api/licencias/asignaciones", headers=h, json={"producto_id": prod["id"], "persona": mail}).status_code == 200
    assert client.post("/api/licencias/asignaciones", headers=h,
                       json={"producto_id": a["id"], "persona": "ana@ejemplo.com"}).status_code == 409
    p, r, _ = _productos(client, token)
    assert p["Claude Team"]["costo_mensual"] == {"USD": 150} and p["Claude Team"]["costo_anual"] == {"USD": 1800}
    assert p["Claude Team"]["costo_sin_asignar_mensual"] == {"USD": 90}
    assert p["M365"]["mensual_unitario"] == {"USD": 10, "ARS": 10000} and p["M365"]["costo_mensual"] == {"USD": 20, "ARS": 20000}
    assert r["mensual"] == {"USD": 170, "ARS": 20000} and r["sin_asignar_mensual"] == {"USD": 100, "ARS": 10000}   # 3 Claude + 1 M365
    ana = next(x for x in client.get("/api/licencias/personas", headers=h).json() if x["persona"] == "ana@ejemplo.com")
    assert ana["costo_mensual"] == {"USD": 40, "ARS": 10000}


def test_sin_cupo_paga_lo_asignado_y_excedido(client, token):
    h = bearer(token)
    a = client.post("/api/licencias/productos", headers=h,
                    json={"producto": "Antivirus X", "precio_usd": 12, "periodo": "anual"}).json()
    client.post("/api/licencias/asignaciones", headers=h, json={"producto_id": a["id"], "persona": "x@ejemplo.com"})
    p, r, _ = _productos(client, token)
    assert p["Antivirus X"]["costo_mensual"] == {"USD": 1} and r["sin_cupo"] == 1
    client.put("/api/licencias/productos/" + a["id"], headers=h, json={"cupo": 0})
    p, r, _ = _productos(client, token)
    assert p["Antivirus X"]["excedido"] and r["excedidos"] == 1


def test_cuenta_deshabilitada_y_cruce_con_equipos(client, token):
    h = bearer(token)
    db = database.SessionLocal()
    db.add(database.Asset(id="ANB0001", nombre="NB-ANA", tipo="Notebook", serial="S1", usuario="ana", ubicacion="Rosario", estado="Activo"))
    db.commit()
    db.close()
    a = client.post("/api/licencias/productos", headers=h, json={"producto": "Claude Team", "precio_usd": 30}).json()
    client.post("/api/licencias/asignaciones", headers=h, json={"producto_id": a["id"], "persona": "ana@ejemplo.com"})
    assert client.put("/api/licencias/personas/ana@ejemplo.com", headers=h, json={"cuenta_ad": "deshabilitada"}).status_code == 200
    ana = client.get("/api/licencias/personas", headers=h).json()[0]
    assert ana["en_atlas"] and ana["sede"] == "Rosario" and ana["equipos"][0]["nombre"] == "NB-ANA" and ana["deshabilitada"]
    assert client.get("/api/licencias", headers=h).json()["resumen"]["asignadas_deshabilitadas"] == 1


def test_liberar_manual_y_rechaza_credenciales(client, token):
    h = bearer(token)
    m = client.post("/api/licencias/productos", headers=h, json={"producto": "Claude Team"}).json()
    aid = client.post("/api/licencias/asignaciones", headers=h, json={"producto_id": m["id"], "persona": "z@ejemplo.com"}).json()["id"]
    assert client.post("/api/licencias/asignaciones/%s/liberar" % aid, headers=h).json()["estado"] == "liberada"
    assert client.post("/api/licencias/productos", headers=h, json={"producto": "X", "notas": "usuario: admin pass: 1234"}).status_code == 422


# ---------------------------------------------------------------- CSV de miembros / generico
def _subir_csv(client, token, texto, producto_id=None):
    datos = {"producto_id": producto_id} if producto_id else None
    return client.post("/api/licencias/importar", headers=bearer(token), data=datos,
                       files={"archivo": ("miembros.csv", texto.encode("utf-8-sig"), "text/csv")})


def test_csv_generico_y_exportar(client, token):
    h = bearer(token)
    texto = ("email;nombre;producto;proveedor\nana@ejemplo.com;Ana;Claude Team;Anthropic\n"
             "beto@ejemplo.com;Beto;Claude Team;Anthropic\nana@ejemplo.com;Ana;Claude Team;Anthropic\nsin-mail;X;Y;Z\n")
    r = _subir_csv(client, token, texto)
    assert r.status_code == 200, r.text
    assert r.json() == {"filas": 3, "productos_nuevos": 1, "asignaciones_nuevas": 2, "ya_estaban": 1, "externas_ignoradas": 0,
                        "sin_producto": 0, "sin_asiento": 0}
    ex = client.get("/api/licencias/exportar.csv", headers=h)
    assert ex.status_code == 200 and "beto@ejemplo.com" in ex.text and ex.text.startswith("﻿") and "centro de costo" in ex.text
    assert _subir_csv(client, token, "nombre,telefono\nAna,1\n").status_code == 400


def test_csv_de_miembros_de_claude_con_producto_elegido_o_por_tier(client, token):
    seed.seed_licencias()
    p, _, _ = _productos(client, token)
    std, prem = p["Claude Team Standard"], p["Claude Team Premium"]
    # export de miembros sin columna de producto: se eligen en la vista (producto_id)
    r = _subir_csv(client, token, "Name,Email,Role\nAna Prueba,ana@ejemplo.com,User\nBeto,beto@ejemplo.com,Admin\n", std["id"])
    assert r.json()["asignaciones_nuevas"] == 2
    # con columna "Seat tier": "Premium" -> "Claude Team Premium"
    r = _subir_csv(client, token, "Name,Email,Seat tier\nCarla,carla@ejemplo.com,Premium\nDario,dario@ejemplo.com,Standard\n")
    assert r.json() == {"filas": 2, "productos_nuevos": 0, "asignaciones_nuevas": 2, "ya_estaban": 0, "externas_ignoradas": 0,
                        "sin_producto": 0, "sin_asiento": 0}
    p, _, _ = _productos(client, token)
    assert p["Claude Team Standard"]["asignadas"] == 3 and p["Claude Team Premium"]["asignadas"] == 1
    assert _subir_csv(client, token, "Email\na@ejemplo.com\n").json()["sin_producto"] == 1
    # "Unassigned" (owner sin asiento pago) no es una licencia ni crea un producto
    r = _subir_csv(client, token, "Name,Email,Seat Tier\nJose,jose@ejemplo.com,Unassigned\n").json()
    assert r["sin_asiento"] == 1 and r["productos_nuevos"] == 0 and r["asignaciones_nuevas"] == 0
    assert prem["proveedor"] == "Anthropic"


# ---------------------------------------------------------------- costos por periodo (API / manual)
def test_costos_por_mes_manual_y_api(client, token):
    h = bearer(token)
    a = client.post("/api/licencias/productos", headers=h, json={"proveedor": "Anthropic", "producto": "Claude Team"}).json()
    r = client.post("/api/licencias/costos", headers=h, json={"costos": [
        {"producto_id": a["id"], "periodo": "2026-10", "monto": 750, "cantidad": 30, "workspace": "Default"},
        {"producto_id": a["id"], "periodo": "2026-11", "monto": 800, "cantidad": 32, "workspace": "Default"}]})
    assert r.status_code == 200 and r.json() == {"filas": 2, "nuevas": 2}
    db = database.SessionLocal()
    try:      # lo que cargaria un conector con costos reales (origen "api") no pisa lo manual
        licencias.aplicar_costos_periodo(db, [{"producto_id": a["id"], "periodo": "2026-11", "monto": 812.5, "moneda": "USD",
                                               "workspace": "Default", "cantidad": 32}], origen="api")
        db.commit()
    finally:
        db.close()
    meses = client.get("/api/licencias/costos?desde=2026-11", headers=h).json()
    assert [m["periodo"] for m in meses] == ["2026-11"]
    assert {(x["origen"], x["monto"]) for x in meses[0]["productos"]} == {("manual", 800), ("api", 812.5)}
    det = client.get("/api/licencias/productos/" + a["id"], headers=h).json()
    assert det["costo_origen"] == "api" and len(det["costos_periodo"]) == 3
    assert client.post("/api/licencias/costos", headers=h, json={"costos": [
        {"producto_id": a["id"], "periodo": "2026-13", "monto": 1}]}).status_code == 422
    assert client.get("/api/licencias/costos?desde=ayer", headers=h).status_code == 400


def test_anthropic_preparado_pero_inerte():
    falta = conectores.falta_config("anthropic")
    assert "ANTHROPIC_ADMIN_KEY_ARCHIVO" in falta and any("pendiente" in x for x in falta)
    assert "anthropic" not in conectores.CONECTORES


# ---------------------------------------------------------------- UserManager (datos ficticios)
def _base_usermanager(ruta):
    """Base SQLite con el esquema del UserManager y datos INVENTADOS."""
    c = sqlite3.connect(ruta)
    c.executescript("""
        CREATE TABLE licencias (id VARCHAR, nombre VARCHAR, tipo VARCHAR, proveedor VARCHAR, plan VARCHAR, costo_usd VARCHAR,
                                costo_ars VARCHAR, periodicidad VARCHAR, cantidad INTEGER, notas VARCHAR);
        CREATE TABLE asignaciones_licencias (id VARCHAR, empleado_id VARCHAR, licencia_id VARCHAR, detalle VARCHAR,
                                             fecha_desde VARCHAR, fecha_hasta VARCHAR, activo VARCHAR);
        CREATE TABLE empleados (id VARCHAR, legajo INTEGER, nombre VARCHAR, centro_costo VARCHAR, subauxiliar VARCHAR,
                                categoria VARCHAR, fecha_ingreso VARCHAR, email VARCHAR, sede VARCHAR, estado VARCHAR,
                                updated DATETIME, editado_manual TEXT);
        CREATE TABLE adobe_pares (id VARCHAR, sector VARCHAR, usuario_principal VARCHAR, email_principal VARCHAR,
                                  usuario_secundario VARCHAR, email_secundario VARCHAR, imputacion VARCHAR,
                                  porcentaje_imputacion VARCHAR, activo VARCHAR);
        CREATE TABLE equipos_licencias (id VARCHAR, numero VARCHAR, unidad VARCHAR, lider VARCHAR, responsable VARCHAR,
                                        email VARCHAR, tipo VARCHAR, estado VARCHAR, activo VARCHAR);
    """)
    c.executemany("INSERT INTO licencias VALUES (?,?,?,?,?,?,?,?,?,?)", [
        ("L-ADOBE", "Adobe Acrobat", "Software", "Adobe", "Teams", "", "", "Mensual", 3, ""),
        ("L-CLAUDE", "Claude Standard", "IA", "Anthropic", "Standard", "25", "", "Mensual", 4, ""),
        ("L-LEX", "Lex-Doctor", "Software", "Lex-Doctor", "", "", "120000", "Anual", 0, "Legales"),
    ])
    c.executemany("INSERT INTO empleados VALUES (?,?,?,?,?,?,?,?,?,?,?,?)", [
        ("E1", 101, "PRUEBA, Ana", "Auditoria", "CABA 1-AUD", "Senior", "01/02/2020", "Ana.Prueba@ejemplo.com", "CABA1", "Activo", "", "0"),
        ("E2", 102, "EJEMPLO, Bruno", "Impuestos", "CABA 1-IMP", "Gerente", "01/02/2019", "bruno@ejemplo.com", "Rosario", "Activo", "", "0"),
        ("E3", 103, "DEMO, Carla", "Legales", "CABA 1-LEG", "Junior", "01/02/2021", "carla@ejemplo.com", "CABA1", "Inactivo", "", "0"),
        ("E4", 104, "SINMAIL, Dario", "Pymes", "COR-PYMES", "Senior", "01/02/2022", "", "Corrientes", "Activo", "", "0"),
    ])
    c.executemany("INSERT INTO asignaciones_licencias VALUES (?,?,?,?,?,?,?)", [
        ("A1", "E1", "L-ADOBE", "Auditoria", "2026-01-10", "", "1"),
        ("A2", "E2", "L-ADOBE", "Impuestos", "", "", "1"),
        ("A3", "E1", "L-CLAUDE", "", "", "", "1"),
        ("A4", "E3", "L-LEX", "Legales", "", "", "1"),          # baja en la nomina con licencia -> alerta
        ("A5", "E4", "L-CLAUDE", "", "", "2020-01-01", "1"),    # vencida por fecha -> liberada
    ])
    c.executemany("INSERT INTO adobe_pares VALUES (?,?,?,?,?,?,?,?,?)", [
        ("P1", "Auditoria", "Ana", "ana.prueba@ejemplo.com", "Bruno", "bruno@ejemplo.com", "", "0", "1"),
        ("P2", "Pymes", "Dario", "", "Externo", "externo@otra.com", "COR-PYMES", "0", "1"),
    ])
    c.executemany("INSERT INTO equipos_licencias VALUES (?,?,?,?,?,?,?,?,?)", [
        ("Q1", "#01", "Bancos", "L. Lider", "Resp Uno", "equipo1@ejemplo.com", "Standard", "Activo", "1"),
        ("Q2", "#02", "Pymes", "V. Lider", "Resp Dos", "", "Standard", "Activo", "0"),
    ])
    c.commit()
    c.close()


@pytest.fixture
def um_json(tmp_path):
    base = tmp_path / "usermanager.db"
    _base_usermanager(base)
    exp = _modulo("exportar_usermanager")
    salida = tmp_path / "um.json"
    assert exp.main(["--base", str(base), "--salida", str(salida)]) == 0
    datos = json.loads(salida.read_text(encoding="utf-8"))
    assert sqlite3.connect(base).execute("select count(*) from licencias").fetchone()[0] == 3   # solo lectura
    return datos


def _importar_um(client, token, datos):
    return client.post("/api/licencias/importar-usermanager", headers=bearer(token),
                       files={"archivo": ("um.json", json.dumps(datos).encode("utf-8"), "application/json")})


def test_exportador_e_importacion_del_usermanager(client, token, um_json):
    assert um_json["origen"] == "usermanager" and len(um_json["empleados"]) == 4 and len(um_json["asignaciones"]) == 5
    r = _importar_um(client, token, um_json)
    assert r.status_code == 200, r.text
    res = r.json()
    assert res["productos_nuevos"] == 3 and res["personas"] == 4 and res["asignaciones"] == 5
    assert res["compartidas"] == 2 and res["cuentas_equipo"] == 2
    p, r, centros = _productos(client, token)
    adobe, claude, lex = p["L-ADOBE"], p["L-CLAUDE"], p["L-LEX"]
    # Adobe: Ana y Bruno comparten UNA licencia (par P1) + el par P2 = 2 licencias en uso (no 3)
    assert adobe["asignadas"] == 2 and adobe["compartidas"] == 2 and adobe["cupo"] == 3 and adobe["libres"] == 1
    assert adobe["personas"] == 4 and adobe["sin_precio"]      # Ana, Bruno, Dario (sin mail) y el externo
    # Claude: Ana (individual) + la cuenta de equipo activa Q1 (Q2 inactiva); A5 vencida por fecha
    assert claude["asignadas"] == 2 and claude["cuentas_equipo"] == 1 and claude["precio_usd"] == 25
    assert claude["costo_mensual"] == {"USD": 100}           # cupo 4 x 25
    assert lex["periodo"] == "anual" and lex["precio_ars"] == 120000 and lex["costo_mensual"] == {"ARS": 10000}
    assert r["asignadas_baja"] == 1 and r["personas_baja"] == 1    # Carla, baja con Lex-Doctor
    c = {x["centro"]: x["mensual"] for x in centros}
    assert c["Auditoria"]["USD"] == 25 and c["Bancos"]["USD"] == 25 and c["sin asignar"]["USD"] == 50
    assert c["Legales"]["ARS"] == 10000
    personas = {x["persona"]: x for x in client.get("/api/licencias/personas", headers=bearer(token)).json()}
    ana = personas["ana.prueba@ejemplo.com"]
    assert ana["legajo"] == "101" and ana["centro_costo"] == "Auditoria" and ana["sede"] == "CABA1"
    assert {x["producto"] for x in ana["productos"]} == {"Adobe Acrobat", "Claude Standard"}
    assert next(x for x in ana["productos"] if x["producto"] == "Adobe Acrobat")["fraccion"] == 0.5
    assert personas["carla@ejemplo.com"]["de_baja"]
    comp = client.get("/api/licencias/compartidas", headers=bearer(token)).json()
    assert {c["imputacion"] for c in comp} == {"", "COR-PYMES"}
    eq = client.get("/api/licencias/cuentas-equipo", headers=bearer(token)).json()
    assert {(c["numero"], c["activo"], c["producto"]) for c in eq} == {("#01", True, "Claude Standard"), ("#02", False, "Claude Standard")}


def test_importacion_idempotente_y_no_pisa_costos(client, token, um_json):
    _importar_um(client, token, um_json)
    p, _, _ = _productos(client, token)
    pid = p["L-ADOBE"]["id"]
    client.put("/api/licencias/productos/" + pid, headers=bearer(token),
               json={"precio_usd": 19.99, "periodo": "mensual", "cupo": 10, "notas": "Factura VIP"})
    um_json["asignaciones"] = [a for a in um_json["asignaciones"] if a["id"] != "A2"]    # Bruno ya no la tiene
    um_json["licencias"][0]["cantidad"] = 50
    um_json["licencias"][0]["costo_usd"] = "99"
    res = _importar_um(client, token, um_json).json()
    assert res["productos_nuevos"] == 0 and res["altas"] == 0 and res["liberadas"] == 1
    det = client.get("/api/licencias/productos/" + pid, headers=bearer(token)).json()
    assert det["precio_usd"] == 19.99 and det["cupo"] == 10 and det["notas"] == "Factura VIP"
    assert next(a for a in det["asignaciones"] if a["persona"] == "bruno@ejemplo.com")["estado"] == "liberada"
    res = _importar_um(client, token, um_json).json()
    assert res["altas"] == 0 and res["liberadas"] == 0 and res["productos_nuevos"] == 0


def test_importacion_rechaza_otro_json(client, token):
    for cuerpo in (b'{"hola": 1}', b"no es json"):
        r = client.post("/api/licencias/importar-usermanager", headers=bearer(token),
                        files={"archivo": ("x.json", cuerpo, "application/json")})
        assert r.status_code == 400


def test_importador_por_linea_de_comandos_modo_prueba(um_json, tmp_path, capsys):
    archivo = tmp_path / "um.json"
    archivo.write_text(json.dumps(um_json), encoding="utf-8")
    imp = _modulo("importar_usermanager")
    backend = os.path.join(os.path.dirname(__file__), "..", "backend")
    assert imp.main([str(archivo), "--env", "", "--backend", backend, "--probar"]) == 0
    assert "PRUEBA" in capsys.readouterr().out
    db = database.SessionLocal()
    try:
        assert db.query(database.LicenciaProducto).count() == 0        # --probar no guarda
    finally:
        db.close()


# ---------------------------------------------------------------- Adobe: exportacion CSV de la Admin Console
CSV_ENTERPRISE = (
    "Identity Type,Username,Domain,Email,First Name,Last Name,Country Code,Product Configurations,Admin Roles,"
    "Product Configurations Administered,User Groups,User Groups Administered,Products Administered,Developer Access,"
    "Auto Assigned Products\n"
    'Federated ID,ana.prueba@ejemplo.com,ejemplo.com,ana.prueba@ejemplo.com,Ana,Prueba,AR,'
    '"Acrobat Pro - Default,Creative Cloud - Diseño",,,Diseño,,,,\n'
    'Federated ID,bruno@ejemplo.com,ejemplo.com,Bruno@ejemplo.com,Bruno,Ejemplo,AR,Acrobat Pro - Default,,,,,,,\n'
    'Federated ID,sin.licencia@ejemplo.com,ejemplo.com,sin.licencia@ejemplo.com,Sin,Licencia,AR,,,,,,,,\n')
CSV_TEAMS_ES = ("Correo electrónico;Nombre;Apellido;Productos\n"
                "carla@ejemplo.com;Carla;Demo;Acrobat Pro\n"
                "dario@ejemplo.com;Darío;Test;Acrobat Pro, Adobe Express\n")


def _importar_adobe(client, token, texto):
    return client.post("/api/licencias/importar-adobe", headers=bearer(token),
                       files={"archivo": ("usuarios.csv", texto.encode("utf-8-sig"), "text/csv")})


def test_exportacion_adobe_enterprise(client, token):
    r = _importar_adobe(client, token, CSV_ENTERPRISE)
    assert r.status_code == 200, r.text
    assert r.json() == {"personas": 2, "productos_nuevos": 2, "altas": 3, "liberadas": 0, "sin_productos": 1, "asignadas": 3}
    p, _, _ = _productos(client, token)
    acro = p["Acrobat Pro - Default"]
    assert acro["proveedor"] == "Adobe" and acro["origen"] == "adobe-csv" and acro["asignadas"] == 2
    client.put("/api/licencias/productos/" + acro["id"], headers=bearer(token), json={"precio_usd": 200, "periodo": "anual", "cupo": 5})
    sin_bruno = "\n".join(x for x in CSV_ENTERPRISE.splitlines() if "bruno" not in x.lower()) + "\n"
    r = _importar_adobe(client, token, sin_bruno)
    assert r.json()["liberadas"] == 1 and r.json()["altas"] == 0
    det = client.get("/api/licencias/productos/" + acro["id"], headers=bearer(token)).json()
    assert det["precio_usd"] == 200 and det["cupo"] == 5 and det["asignadas"] == 1
    assert client.post("/api/licencias/asignaciones", headers=bearer(token),
                       json={"producto_id": acro["id"], "persona": "x@ejemplo.com"}).status_code == 409


def test_exportacion_adobe_teams_en_castellano(client, token):
    r = _importar_adobe(client, token, CSV_TEAMS_ES)
    assert r.status_code == 200, r.text
    assert r.json()["productos_nuevos"] == 2 and r.json()["altas"] == 3
    personas = {x["persona"]: x for x in client.get("/api/licencias/personas", headers=bearer(token)).json()}
    assert personas["dario@ejemplo.com"]["nombre"] == "Darío Test"
    assert _importar_adobe(client, token, "Nombre,Telefono\nAna,123\n").status_code == 400


# ---------------------------------------------------------------- Adobe: User Management API (http falso)
def _grupo(nombre, producto, cupo, tipo="PRODUCT_PROFILE"):
    return {"groupName": nombre, "type": tipo, "productName": producto, "licenseQuota": cupo, "memberCount": 0}


def _usuario(email, grupos, estado="active", nombre="Ana", apellido="Prueba"):
    return {"email": email, "firstname": nombre, "lastname": apellido, "status": estado, "groups": grupos}


class FalsoAdobe:
    """IMS + UMAPI falsos: grupos y usuarios en paginas de a 2; puede devolver 401 o 429 una vez."""

    def __init__(self, grupos, usuarios, falla_401=False, falla_429=False, por_pagina=2):
        self.grupos, self.usuarios, self.por_pagina = grupos, usuarios, por_pagina
        self.tokens, self.esperas, self.paginas = 0, [], []
        self.falla_401, self.falla_429 = falla_401, falla_429

    def __call__(self, metodo, url, headers=None, cuerpo=None, verificar=True):
        if url == IMS:
            assert metodo == "POST" and b"client_secret=secreto-adobe" in cuerpo and b"user_management_sdk" in cuerpo
            self.tokens += 1
            return 200, {"access_token": "tok-%d" % self.tokens, "expires_in": 86399}
        assert url.startswith(UMAPI) and headers["X-Api-Key"] == "cliente-adobe" and headers["Authorization"].startswith("Bearer tok-")
        if self.falla_401 and self.tokens == 1:
            raise conectores.ErrorConector("HTTP 401", 401)
        if self.falla_429:
            self.falla_429 = False
            raise conectores.ErrorConector("HTTP 429", 429, 7)
        recurso, org, pagina = url[len(UMAPI) + 1:].split("/")
        assert org == ORG
        pagina = int(pagina)
        self.paginas.append((recurso, pagina))
        datos = self.grupos if recurso == "groups" else self.usuarios
        trozo = datos[pagina * self.por_pagina:(pagina + 1) * self.por_pagina]
        return 200, {"lastPage": (pagina + 1) * self.por_pagina >= len(datos), recurso: trozo}


@pytest.fixture
def cfg_adobe(monkeypatch, tmp_path):
    p = tmp_path / "adobe.txt"
    p.write_text("secreto-adobe\n", encoding="utf-8")
    for k, v in (("ADOBE_CLIENT_ID", "cliente-adobe"), ("ADOBE_ORG_ID", ORG), ("ADOBE_SECRET_ARCHIVO", str(p)),
                 ("ADOBE_IMS_URL", IMS), ("ADOBE_UMAPI_URL", UMAPI)):
        monkeypatch.setattr(config, k, v)
    return p


GRUPOS = [_grupo("Acrobat Pro - Default", "Acrobat Pro DC", "10"), _grupo("Creative Cloud - Diseño", "Creative Cloud All Apps", 3),
          _grupo("Administradores", "", None, tipo="USER_GROUP"), _grupo("Express", "Adobe Express", "UNLIMITED")]
USUARIOS = [_usuario("ana.prueba@ejemplo.com", ["Acrobat Pro - Default", "Administradores"]),
            _usuario("Bruno@ejemplo.com", ["Acrobat Pro - Default", "Creative Cloud - Diseño"], nombre="Bruno", apellido="Ejemplo"),
            _usuario("carla@ejemplo.com", ["Acrobat Pro - Default"], estado="disabled", nombre="Carla", apellido="Baja")]


def _sincronizar(falso):
    datos = licencias.leer_adobe(falso, dormir=lambda s: falso.esperas.append(s))
    db = database.SessionLocal()
    try:
        res = licencias.aplicar_adobe(db, datos)
        db.commit()
        return res
    finally:
        db.close()


def test_api_adobe_perfiles_usuarios_y_liberadas(cfg_adobe, client, token):
    falso = FalsoAdobe(GRUPOS, USUARIOS)
    assert _sincronizar(falso) == {"productos": 3, "asignadas": 4, "altas": 4, "liberadas": 0}
    assert ("groups", 1) in falso.paginas and ("users", 1) in falso.paginas
    p, _, _ = _productos(client, token)
    assert p["Acrobat Pro - Default"]["cupo"] == 10 and p["Acrobat Pro - Default"]["asignadas"] == 3
    assert p["Express"]["ilimitado"] and p["Express"]["cupo"] is None
    personas = {x["persona"]: x for x in client.get("/api/licencias/personas", headers=bearer(token)).json()}
    assert personas["carla@ejemplo.com"]["deshabilitada"]
    usuarios = [USUARIOS[0], _usuario("bruno@ejemplo.com", ["Creative Cloud - Diseño"]), USUARIOS[2]]
    assert _sincronizar(FalsoAdobe(GRUPOS, usuarios))["liberadas"] == 1


def test_api_adobe_401_y_429(cfg_adobe):
    falso = FalsoAdobe(GRUPOS, USUARIOS, falla_401=True, falla_429=True)
    _sincronizar(falso)
    assert falso.tokens == 2 and falso.esperas == [7]


def test_api_adobe_corrida_con_lease_e_inerte(cfg_adobe, monkeypatch):
    falso = FalsoAdobe(GRUPOS, USUARIOS)
    monkeypatch.setitem(conectores.LEER, "adobe", lambda: licencias.leer_adobe(falso, dormir=lambda s: None))
    r = conectores.correr("adobe")
    assert r["ok"] and "4 altas" in r["mensaje"]
    db = database.SessionLocal()
    try:
        assert conectores.toca_correr(db, "adobe") is False
    finally:
        db.close()
    monkeypatch.setattr(config, "ADOBE_CLIENT_ID", "")
    assert not conectores.configurado("adobe") and conectores.correr("adobe") is None
    assert "adobe" not in conectores.CONECTORES_SERVIDORES


# ---------------------------------------------------------------- permisos y migracion
def test_permisos_del_modulo(client, token):
    crear_usuario_db("sin-lic", "sin-lic@example.test", CLAVE, "viewer")
    db = database.SessionLocal()
    u = db.query(User).filter(User.username == "sin-lic").first()
    db.query(UserModulo).filter(UserModulo.user_id == u.id, UserModulo.modulo == "licencias").delete()
    db.commit()
    db.close()
    t = login(client, "sin-lic", CLAVE).json()["access_token"]
    assert client.get("/api/licencias", headers=bearer(t)).status_code == 403
    crear_usuario_db("lector-lic", "lector-lic@example.test", CLAVE, "viewer")
    t2 = login(client, "lector-lic", CLAVE).json()["access_token"]
    assert client.get("/api/licencias", headers=bearer(t2)).status_code == 200
    assert client.post("/api/licencias/productos", headers=bearer(t2), json={"producto": "X"}).status_code == 403
    assert client.post("/api/licencias/importar-usermanager", headers=bearer(t2),
                       files={"archivo": ("x.json", b"{}", "application/json")}).status_code == 403
    assert client.get("/api/licencias/conector", headers=bearer(t2)).json()["conector"] == "adobe"


def test_la_migracion_suma_licencias(client):
    for nombre, rol in (("l-viewer", "viewer"), ("l-editor", "editor"), ("l-admin", "admin")):
        crear_usuario_db(nombre, nombre + "@example.test", CLAVE, rol)
    cfg = Config(INI)
    with database.engine.begin() as con:
        cfg.attributes["connection"] = con
        command.downgrade(cfg, "0011")
    database.init_db()
    db = database.SessionLocal()
    try:
        for nombre, rol in (("l-viewer", "viewer"), ("l-editor", "editor"), ("l-admin", "admin")):
            u = db.query(User).filter(User.username == nombre).first()
            m = {f.modulo: f.nivel for f in db.query(UserModulo).filter(UserModulo.user_id == u.id)}
            assert m == plantilla(rol), nombre
            assert m["licencias"] == ("ver" if rol == "viewer" else "editar")
    finally:
        db.close()


def test_renovaciones_proximas():
    hoy = date.today()
    prods = [{"activo": True, "fecha_renovacion": hoy + timedelta(days=10)}, {"activo": True, "fecha_renovacion": hoy + timedelta(days=200)},
             {"activo": False, "fecha_renovacion": hoy + timedelta(days=5)}]
    assert len(licencias.proximas_renovaciones(prods, hoy)) == 1


def test_csv_adobe_teams_real_usa_el_catalogo_y_omite_sin_licencia(client, token):
    # Formato real de la Admin Console (plan Teams, castellano): "Productos de equipo" con sufijo "(DIRECT - <contrato>)"
    seed.seed_licencias()
    csv_ = ("Correo electrónico,Nombre,Apellidos,Funciones de administrador,Grupos de usuarios,Productos de equipo\n"
            'ana@llyasoc.com,Ana,Prueba,,,"Acrobat Premium for teams (DIRECT - CD0B0217959655120B2A)"\n'
            'beto@llyasoc.com,Beto,Prueba,,,"Creative Cloud Pro (DIRECT - CD0B0217959655120B2A),Premiere - Pro Edition (DIRECT - CD0B0217959655120B2A)"\n'
            "sinlic@llyasoc.com,Sin,Licencia,,,\n").encode("utf-8-sig")
    db = database.SessionLocal()
    try:
        antes = db.query(licencias.LicenciaProducto).count()
        res = licencias.aplicar_csv_adobe(db, licencias.leer_csv_adobe(csv_))
        db.commit()
        assert res["personas"] == 2 and res["sin_productos"] == 1 and res["productos_nuevos"] == 0 and res["altas"] == 3
        assert db.query(licencias.LicenciaProducto).count() == antes          # reusa el catalogo, sin duplicados
        personas = {a.persona for a in db.query(licencias.LicenciaAsignacion).all()}
        assert personas == {"ana@llyasoc.com", "beto@llyasoc.com"}             # el que no tiene licencia no entra
        nombres = {db.get(licencias.LicenciaProducto, a.producto_id).producto for a in db.query(licencias.LicenciaAsignacion).all()}
        assert nombres == {"Acrobat Premium para equipos", "Creative Cloud Pro", "Premiere Pro"}
    finally:
        db.close()
