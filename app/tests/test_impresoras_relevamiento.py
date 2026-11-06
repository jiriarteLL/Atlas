# -*- coding: utf-8 -*-
"""Relevamiento SNMP de impresoras: alta limpia desde la red, actualizacion por serie, sin respuesta, USB intactas."""
import pytest

import config
from conftest import SYNC_KEY, bearer

H = {"X-Sync-Key": SYNC_KEY}
URL = "/api/impresoras/relevamiento"


@pytest.fixture(autouse=True)
def sedes(monkeypatch):
    monkeypatch.setattr(config, "SEDES_POR_RED", [("192.168.9.0/24", "Tigre"), ("192.168.0.0/16", "CABA")])


def _lectura(**kw):
    base = {"ip": "192.168.100.141", "responde": True, "nombre_red": "NPI1FAA0D",
            "sys_descr": "HP ETHERNET MULTI-ENVIRONMENT", "modelo": "HP LaserJet MFP E42540",
            "serie": "CNBRR4M5VH", "contador": 129257, "estado": "otro", "mac": "E0:73:E7:1F:AA:0D",
            "consumibles": [{"indice": 1, "descripcion": "Cartucho negro HP W9024MC", "maximo": 100,
                             "nivel": 89, "porcentaje": 89, "nota": ""}]}
    return base | kw


def _impresoras(client, token):
    return {i["serial"]: i for i in client.get("/api/impresoras", headers=bearer(token)).json()}


def test_requiere_clave(client):
    assert client.post(URL, json={"lecturas": []}).status_code == 401
    assert client.get(URL + "/ips", headers={"X-Sync-Key": "otra"}).status_code == 401


def test_alta_limpia_desde_la_red_y_lista_de_ips(client, token):
    r = client.post(URL, json={"lecturas": [_lectura()]}, headers=H)
    assert r.status_code == 200 and r.json()["creadas"] == 1
    i = _impresoras(client, token)["CNBRR4M5VH"]
    assert i["marca"] == "HP" and i["modelo"] == "HP LaserJet MFP E42540" and i["ubicacion"] == "CABA"
    assert i["detalle"]["conexion"] == "red" and i["detalle"]["mac"] == "E0:73:E7:1F:AA:0D"
    assert i["detalle"]["escaner"] is True and i["detalle"]["color"] is False
    assert i["lectura"]["contador_total"] == 129257
    assert i["consumibles"][0]["porcentaje"] == 89 and i["consumibles"][0]["tipo"] == "toner"
    assert client.get(URL + "/ips", headers=H).json() == {"ips": ["192.168.100.141"]}


def test_segunda_lectura_actualiza_sin_duplicar_y_no_pisa_datos_administrativos(client, token):
    client.post(URL, json={"lecturas": [_lectura()]}, headers=H)
    aid = _impresoras(client, token)["CNBRR4M5VH"]["id"]
    r = client.put("/api/impresoras/" + aid, headers=bearer(token),
                   json={"nombre": "IMPRESORA-CABA-08", "piso": "17", "tenencia": "tercerizada", "proveedor": "Canal Directo"})
    assert r.status_code == 200, r.text
    otra = _lectura(ip="192.168.100.142", contador=129300,
                    consumibles=[{"indice": 1, "descripcion": "Cartucho negro HP W9024MC", "maximo": 100,
                                  "nivel": 85, "porcentaje": 85, "nota": ""}])
    r = client.post(URL, json={"lecturas": [otra]}, headers=H)
    assert r.json()["actualizadas"] == 1 and r.json()["creadas"] == 0
    imps = _impresoras(client, token)
    assert len(imps) == 1
    i = imps["CNBRR4M5VH"]
    assert i["nombre"] == "IMPRESORA-CABA-08" and i["ip"] == "192.168.100.142"
    assert i["detalle"]["piso"] == "17" and i["detalle"]["proveedor"] == "Canal Directo"
    assert i["lectura"]["contador_total"] == 129300 and len(i["consumibles"]) == 1
    hist = client.get("/api/assets/%s/historial" % aid, headers=bearer(token)).json()
    assert any(h["campo"] == "ip" and h["usuario"] == "relevamiento-snmp" for h in hist)


def test_sin_respuesta_queda_registrado_solo_si_ya_existe(client, token):
    client.post(URL, json={"lecturas": [_lectura()]}, headers=H)
    r = client.post(URL, json={"lecturas": [
        {"ip": "192.168.100.141", "responde": False, "error": "timeout"},
        {"ip": "192.168.24.171", "responde": False}]}, headers=H)
    assert r.json()["sin_respuesta"] == 1 and r.json()["ignoradas"] == 1
    i = _impresoras(client, token)["CNBRR4M5VH"]
    assert i["lectura"]["estado"] == "sin respuesta"
    assert len(_impresoras(client, token)) == 1   # la que nunca respondio no se crea


def test_impresora_usb_y_otros_activos_no_se_tocan(client, token):
    r = client.post("/api/impresoras", headers=bearer(token),
                    json={"nombre": "Persona X", "marca": "HP", "modelo": "HP Laser 107a", "serial": "BRBSPBK084",
                          "conexion": "usb", "uso": "personal"})
    assert r.status_code == 200, r.text
    client.post("/api/sync", headers=H, json={"tipo": "Notebook", "serial": "PF5JZXCD", "marca": "Lenovo",
                                              "modelo": "E14", "nombre": "TEST"})
    r = client.post(URL, json={"lecturas": [_lectura(serie="BRBSPBK084"), _lectura(serie="PF5JZXCD", mac="")]},
                    headers=H)
    assert r.json()["ignoradas"] == 2 and r.json()["creadas"] == 0
    usb = _impresoras(client, token)["BRBSPBK084"]
    assert usb["detalle"]["conexion"] == "usb" and usb["ip"] in ("", None) and usb["lectura"] is None


def test_sede_por_red_y_color(client, token):
    color = _lectura(ip="192.168.9.71", serie="MXCCV14082", mac="4C:CF:7C:79:FF:E3", modelo="HP Color LaserJet MFP E78625",
                     consumibles=[{"indice": 2, "descripcion": "Cartucho cian HP W9141", "maximo": 100, "nivel": 9,
                                   "porcentaje": 9, "nota": ""}])
    client.post(URL, json={"lecturas": [color]}, headers=H)
    i = _impresoras(client, token)["MXCCV14082"]
    assert i["ubicacion"] == "Tigre" and i["detalle"]["color"] is True and i["consumibles"][0]["tipo"] == "color"
