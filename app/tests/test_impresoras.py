# -*- coding: utf-8 -*-
"""Modulo de impresoras: alta, edicion, permisos, validaciones, relacion con PCs e importacion sin credenciales."""
import importlib.util
import os

import database
from conftest import SYNC_KEY, bearer, clave_valida, crear_usuario_db, login

IMPRESORA = {"nombre": "IMPRESORA-CABA-08", "marca": "HP", "modelo": "HP LaserJet MFP E42540", "serial": "CNBRR4M5VH",
             "ubicacion": "CABA", "ip": "192.168.100.141", "piso": "17", "nombre_cola": "IMPRESORA-CABA-08",
             "tenencia": "tercerizada", "proveedor": "Canal Directo", "escaner": True,
             "credencial_ref": "KeePassXC - clave comun de impresoras"}


def _alta(client, token, **extra):
    r = client.post("/api/impresoras", json=dict(IMPRESORA, **extra), headers=bearer(token))
    assert r.status_code == 200, r.text
    return r.json()


def test_alta_lista_ficha_y_edicion_con_historial(client, token):
    imp = _alta(client, token)
    assert imp["tipo"] == "Impresora" and imp["detalle"]["piso"] == "17" and imp["detalle"]["escaner"] is True
    assert imp["lectura"] is None and imp["consumibles"] == []
    lista = client.get("/api/impresoras", headers=bearer(token)).json()
    assert [i["nombre"] for i in lista] == ["IMPRESORA-CABA-08"]
    r = client.put("/api/impresoras/" + imp["id"], json={"piso": "18", "usuario": "Mesa de ayuda", "duplex": True},
                   headers=bearer(token))
    assert r.status_code == 200, r.text
    assert r.json()["detalle"]["piso"] == "18" and r.json()["usuario"] == "Mesa de ayuda" and r.json()["detalle"]["duplex"]
    hist = client.get("/api/assets/%s/historial" % imp["id"], headers=bearer(token)).json()
    assert {"piso", "usuario", "duplex"} <= {h["campo"] for h in hist}
    # sigue siendo un activo mas: aparece en /api/assets
    assert any(a["id"] == imp["id"] for a in client.get("/api/assets", headers=bearer(token)).json())


def test_serie_repetida_409(client, token):
    _alta(client, token)
    r = client.post("/api/impresoras", json=dict(IMPRESORA, nombre="OTRA"), headers=bearer(token))
    assert r.status_code == 409


def test_viewer_ve_pero_no_edita(client, token):
    imp = _alta(client, token)
    clave = clave_valida()
    crear_usuario_db("qa-lector", "qa-lector@example.test", clave, "viewer")
    tok = login(client, "qa-lector", clave).json()["access_token"]
    assert client.get("/api/impresoras", headers=bearer(tok)).status_code == 200
    assert client.get("/api/impresoras/" + imp["id"], headers=bearer(tok)).status_code == 200
    assert client.put("/api/impresoras/" + imp["id"], json={"piso": "1"}, headers=bearer(tok)).status_code == 403
    assert client.post("/api/impresoras", json=dict(IMPRESORA, serial="X1234"), headers=bearer(tok)).status_code == 403


def test_validaciones_y_nada_de_credenciales(client, token):
    imp = _alta(client, token)
    url, h = "/api/impresoras/" + imp["id"], bearer(token)
    assert client.put(url, json={"conexion": "wifi"}, headers=h).status_code == 422
    assert client.put(url, json={"tenencia": "prestada"}, headers=h).status_code == 422
    assert client.put(url, json={"password": "x"}, headers=h).status_code == 422          # campo desconocido
    assert client.put(url, json={"notas": "User: prueba Pass: Ficticia-1"}, headers=h).status_code == 422
    assert client.put(url, json={"credencial_ref": "clave: Ficticia-2"}, headers=h).status_code == 422
    assert client.put(url, json={"credencial_ref": "KeePassXC - impresoras"}, headers=h).status_code == 200
    assert client.get("/api/impresoras/x-no-existe", headers=h).status_code == 404


def test_pcs_que_la_tienen_instalada(client, token):
    imp = _alta(client, token)
    h = {"X-Sync-Key": SYNC_KEY}
    for serial, cola in (("PC0001", "IMPRESORA-CABA-08|Microsoft Print to PDF"),
                         ("PC0002", "\\\\llsvr17\\IMPRESORA-CABA-08 (Copia 1)"),
                         ("PC0003", "IMPRESORA-CABA-02")):
        body = {"tipo": "Notebook", "serial": serial, "nombre": "NB-" + serial, "marca": "Lenovo", "modelo": "E14",
                "usuario": "u" + serial, "ubicacion": "CABA", "impresoras": cola}
        assert client.post("/api/sync", json=body, headers=h).status_code == 200
    pcs = client.get("/api/impresoras/" + imp["id"], headers=bearer(token)).json()["pcs"]
    assert sorted(p["nombre"] for p in pcs) == ["NB-PC0001", "NB-PC0002"]


def test_borrar_el_activo_borra_el_detalle(client, token):
    imp = _alta(client, token)
    assert client.delete("/api/assets/" + imp["id"], headers=bearer(token)).status_code == 200
    db = database.SessionLocal()
    try:
        assert db.query(database.ImpresoraDetalle).filter_by(asset_id=imp["id"]).count() == 0
    finally:
        db.close()


def _importador():
    ruta = os.path.join(os.path.dirname(__file__), "..", "..", "herramientas", "importar-impresoras",
                        "importar_impresoras.py")
    spec = importlib.util.spec_from_file_location("importar_impresoras", ruta)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def test_importacion_descarta_credenciales():
    imp = _importador()
    c = imp.parsear_comentario("Piso 12 - Toner 90X - User:Admin Pass:Ficticia-9z - Doble bandeja")
    assert c == {"piso": "12", "toner": "90X", "personal": False, "notas": ["Doble bandeja"]}
    c = imp.parsear_comentario("Piso 14 - Toner 81A - User:administrador - Doble bandeja")
    assert "administrador" not in str(c)
    prod = {"nombre": "IMPRESORA-CABA-01", "marca": "HP", "modelo": "HP LaserJet 600 M602", "serial": "brbsfbjxrp ",
            "ip": "192.168.100.73", "ubicacion": "CABA", "usuario": "",
            "comentarios": "Piso 12 - Toner 90X - User:Admin Pass:Ficticia-9z - Doble bandeja"}
    r, origen = imp.armar(prod, None, "KeePassXC")
    assert r["serial"] == "BRBSFBJXRP" and r["nombre_cola"] == "IMPRESORA-CABA-01" and r["conexion"] == "red"
    assert r["credencial_ref"] == "KeePassXC"
    assert not any("Ficticia-9z" in str(v) or "Admin" == str(v) for v in r.values())


def test_importacion_solo_trae_personales():
    """Las de red no se importan (las crea el relevamiento SNMP); solo se informan."""
    imp = _importador()
    red = imp.armar({"nombre": "IMPRESORA-CABA-08", "marca": "HP", "modelo": "E42540", "serial": "CNBRR4M5VH",
                     "ip": "192.168.100.141", "ubicacion": "CABA", "usuario": "", "comentarios": "Piso 17"}, None, "K")
    usb = imp.armar({"nombre": "Monica Moreira", "marca": "HP", "modelo": "HP1102W", "serial": "", "ip": "USB (HOME)",
                     "ubicacion": "CABA", "usuario": "", "comentarios": "Piso 14 - Personal"}, None, "K")
    excel_persona = imp.armar(None, {"hoja": "CABA 1", "sede": "CABA", "inv": "33", "marca": "HP", "modelo": "HP Laser 107a",
                                     "serial": "BRBSPBK067", "piso": "Piso 17", "estado": "Disponible",
                                     "asignado": "Martin Ghirardotti", "tenencia": "", "nombre": ""}, "K")
    personales, de_red = imp.separar([red, usb, excel_persona])
    assert [r["nombre"] for r, _ in personales] == ["HP1102W (Monica Moreira)", "HP Laser 107a (Martin Ghirardotti)"]
    assert [r["nombre"] for r, _ in de_red] == ["IMPRESORA-CABA-08"]
    assert personales[1][0]["piso"] == "17" and personales[1][0]["nro_inventario"] == "CABA 1-33"


def test_importacion_personal_usb_queda_asignada():
    imp = _importador()
    prod = {"nombre": "Ricardo Sosa", "marca": "HP", "modelo": "HP LaserJet Pro M15W", "serial": "", "ip": "USB (HOME)",
            "ubicacion": "CABA", "usuario": "", "comentarios": "Piso 12 - Toner 48A - Personal"}
    r, _ = imp.armar(prod, None, "KeePassXC")
    assert r["conexion"] == "usb" and r["uso"] == "personal" and r["usuario"] == "Ricardo Sosa"
    assert "credencial_ref" not in r and "USB (home)" in r["notas"]
