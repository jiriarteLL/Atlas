# -*- coding: utf-8 -*-
"""Telefonia: importacion de la exportacion de 3CX (lista blanca), relevamiento DHCP y permisos del modulo."""
import os

import pytest
from alembic import command
from alembic.config import Config

import config
import database
from auth import User, UserModulo, plantilla
from conftest import SYNC_KEY, bearer, clave_valida, crear_usuario_db, login

INI = os.path.join(os.path.dirname(__file__), "..", "backend", "alembic.ini")
CLAVE = clave_valida()
PIN = "731946"   # PIN de casilla de voz de prueba: no tiene que quedar guardado en ningun lado
CABECERA = ("Number,FirstName,LastName,EmailAddress,MobileNumber,OutboundCallerID,DID,Role,Department,"
            "ClickToCallAuth,MAC,Model,VMPIN,Disabled,AiAgentSettings\n")


def _csv(*filas):
    return (CABECERA + "".join(f + "\n" for f in filas)).encode("utf-8-sig")


FILA_1102 = ('1102,Maria Laura,Moratto,mlm@example.test,,,71751,"<role name=""users"" />",Llya,'
             'SECRETO-C2C,C074ADA88EEA,GrandStream GRP-2604,%s,0,{"token":"x"}' % PIN)
FILA_1201 = '1201,Ana,Rosario,ana@example.test,,,,,Sucursal Rosario,,C0:74:AD:00:00:01,GrandStream GRP-2602,1111,0,'
FILA_1300 = '1300,Sin,Telefono,st@example.test,,,,,GTH,,,,2222,1,'


@pytest.fixture(autouse=True)
def _sedes():
    antes = config.SEDES_POR_RED
    config.SEDES_POR_RED = [("192.168.10.0/24", "Corrientes"), ("192.168.0.0/16", "CABA")]
    yield
    config.SEDES_POR_RED = antes


def _importar(client, token, contenido):
    return client.post("/api/telefonia/importar-3cx", headers=bearer(token),
                       files={"archivo": ("extensions.csv", contenido, "text/csv")})


def _lista(client, token):
    r = client.get("/api/telefonia", headers=bearer(token))
    assert r.status_code == 200, r.text
    return r.json()


def _por_interno(client, token):
    return {x["interno"]: x for x in _lista(client, token)["lineas"]}


def _dhcp(client, concesiones, clave=SYNC_KEY):
    return client.post("/api/telefonia/relevamiento-dhcp", headers={"X-Sync-Key": clave},
                       json={"concesiones": concesiones})


# ---------------------------------------------------------------- importacion
def test_importa_solo_la_lista_blanca_y_nunca_el_pin(client, token):
    r = _importar(client, token, _csv(FILA_1102, FILA_1201, FILA_1300))
    assert r.status_code == 200, r.text
    assert r.json()["altas"] == 3
    x = _por_interno(client, token)
    assert x["1102"]["nombre"] == "Maria Laura Moratto" and x["1102"]["mac"] == "C074ADA88EEA"
    assert x["1102"]["tipo"] == "IP" and x["1102"]["sede"] == "CABA" and x["1102"]["did"] == "71751"
    assert x["1201"]["mac"] == "C074AD000001" and x["1201"]["sede"] == "Rosario"
    assert x["1300"]["tipo"] == "" and x["1300"]["estado"] == "Deshabilitada" and x["1300"]["deshabilitado"]
    # ni el PIN, ni la clave de click-to-call, ni la config de IA quedan en la base
    with database.engine.connect() as con:
        volcado = " ".join(str(v) for fila in con.exec_driver_sql("SELECT * FROM linea_telefonica") for v in fila)
    for secreto in (PIN, "1111", "2222", "SECRETO-C2C", "token"):
        assert secreto not in volcado


def test_reimportar_es_idempotente_y_marca_los_que_faltan(client, token):
    _importar(client, token, _csv(FILA_1102, FILA_1201))
    r = _importar(client, token, _csv(FILA_1102, FILA_1201)).json()
    assert r["altas"] == 0 and r["cambios"] == 0 and r["sin_cambios"] == 2
    r = _importar(client, token, _csv(FILA_1102)).json()
    assert r["fuera_de_3cx"] == 1
    x = _por_interno(client, token)
    assert len(x) == 2 and not x["1201"]["en_3cx"] and x["1102"]["en_3cx"]   # nunca se borra


def test_asignado_de_la_guia_no_lo_pisa_la_reimportacion(client, token):
    assert _importar(client, token, _csv(FILA_1102)).status_code == 200
    x = _por_interno(client, token)["1102"]
    r = client.put("/api/telefonia/" + x["id"], headers=bearer(token), json={"asignado": "MORATTO, Maria Laura / OTERMIN, Gabriela"})
    assert r.status_code == 200, r.text
    assert _importar(client, token, _csv(FILA_1102)).status_code == 200
    x = _por_interno(client, token)["1102"]
    assert x["asignado"] == "MORATTO, Maria Laura / OTERMIN, Gabriela" and x["nombre"] == "Maria Laura Moratto"


def test_rechaza_archivos_que_no_son_de_3cx_o_muy_grandes(client, token):
    assert _importar(client, token, b"Nombre,Interno\nA,1\n").status_code == 400
    assert _importar(client, token, b"x" * (2 * 1024 * 1024 + 10)).status_code == 413


# ---------------------------------------------------------------- relevamiento DHCP
def test_dhcp_pone_ip_y_sede_y_registra_los_sin_interno(client, token):
    _importar(client, token, _csv(FILA_1102, FILA_1201))
    r = _dhcp(client, [{"mac": "c0-74-ad-a8-8e-ea", "ip": "192.168.10.55", "hostname": "GRP2604"},
                       {"mac": "c0-74-ad-f7-45-58", "ip": "192.168.101.83", "hostname": ""},
                       {"mac": "basura", "ip": "999.1.1.1"}])
    assert r.status_code == 200, r.text
    assert r.json()["actualizados"] == 1 and r.json()["sin_interno"] == 1 and r.json()["ignoradas"] == 1
    d = _lista(client, token)
    x = {f["interno"]: f for f in d["lineas"]}
    assert x["1102"]["ip"] == "192.168.10.55" and x["1102"]["ip_origen"] == "dhcp" and x["1102"]["sede"] == "Corrientes"
    assert x["1102"]["ip_visto"] and x["1201"]["ip"] == ""
    assert [t["mac"] for t in d["sin_interno"]] == ["C074ADF74558"]
    assert d["resumen"]["sin_ip"] == 1 and d["resumen"]["sin_interno"] == 1 and d["resumen"]["con_telefono"] == 2


def test_dhcp_requiere_clave(client):
    assert _dhcp(client, [], clave="otra").status_code == 401
    assert _dhcp(client, [], clave="").status_code == 401


def test_dhcp_no_pisa_la_ip_manual_ni_la_sede_manual(client, token):
    _importar(client, token, _csv(FILA_1102))
    lid = _por_interno(client, token)["1102"]["id"]
    r = client.put("/api/telefonia/" + lid, headers=bearer(token),
                   json={"ip": "192.168.50.10", "sede": "Tigre", "tipo": "WiFi", "piso": "12"})
    assert r.status_code == 200, r.text
    _dhcp(client, [{"mac": "C074ADA88EEA", "ip": "192.168.10.55"}])
    _importar(client, token, _csv(FILA_1102))   # la reimportacion tampoco cambia lo manual
    x = _por_interno(client, token)["1102"]
    assert x["ip"] == "192.168.50.10" and x["ip_origen"] == "manual" and x["sede"] == "Tigre"
    assert x["tipo"] == "WiFi" and x["piso"] == "12" and x["ip_visto"]


def test_edicion_rechaza_credenciales_y_campos_desconocidos(client, token):
    _importar(client, token, _csv(FILA_1102))
    lid = _por_interno(client, token)["1102"]["id"]
    assert client.put("/api/telefonia/" + lid, headers=bearer(token), json={"notas": "clave: 1234"}).status_code == 422
    assert client.put("/api/telefonia/" + lid, headers=bearer(token), json={"pin": "1"}).status_code == 422
    assert client.put("/api/telefonia/" + lid, headers=bearer(token), json={"ip": "no-es-ip"}).status_code == 422


def test_importar_la_mac_saca_al_telefono_de_sin_interno(client, token):
    _dhcp(client, [{"mac": "C074ADA88EEA", "ip": "192.168.1.20"}])
    assert len(_lista(client, token)["sin_interno"]) == 1
    _importar(client, token, _csv(FILA_1102))
    assert _lista(client, token)["sin_interno"] == []


# ---------------------------------------------------------------- permisos
def test_permisos_del_modulo(client, token):
    crear_usuario_db("tel-viewer", "tel-viewer@example.test", CLAVE, "viewer")
    tok = login(client, "tel-viewer", CLAVE).json()["access_token"]
    assert client.get("/api/telefonia", headers=bearer(tok)).status_code == 200
    assert _importar(client, tok, _csv(FILA_1102)).status_code == 403
    # sin el modulo: 403 tambien para leer
    r = client.put("/auth/usuarios/tel-viewer/permisos", headers=bearer(token), json={"modulos": {"dashboard": "ver"}})
    assert r.status_code == 200, r.text
    assert client.get("/api/telefonia", headers=bearer(tok)).status_code == 403


def test_la_migracion_suma_telefonia_a_los_usuarios_con_modulos(client):
    for nombre, rol in (("t-viewer", "viewer"), ("t-editor", "editor"), ("t-admin", "admin")):
        crear_usuario_db(nombre, nombre + "@example.test", CLAVE, rol)
    cfg = Config(INI)
    with database.engine.begin() as con:   # base como antes del despliegue de telefonia
        cfg.attributes["connection"] = con
        command.downgrade(cfg, "0005")
    database.init_db()
    db = database.SessionLocal()
    try:
        for nombre, rol in (("t-viewer", "viewer"), ("t-editor", "editor"), ("t-admin", "admin")):
            u = db.query(User).filter(User.username == nombre).first()
            m = {f.modulo: f.nivel for f in db.query(UserModulo).filter(UserModulo.user_id == u.id)}
            assert m == plantilla(rol), nombre
        assert plantilla("viewer")["telefonia"] == "ver" and plantilla("editor")["telefonia"] == "editar"
    finally:
        db.close()
