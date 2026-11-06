# -*- coding: utf-8 -*-
"""Monitores (fase B): el agente manda monitores_detalle en /api/sync y Atlas da de alta / mueve los externos."""
import database
from conftest import SYNC_KEY, bearer

SAMSUNG = {"fabricante": "SAM", "modelo": "S22F350", "codigo_producto": "0D1A", "serie": "H4ZK300465", "anio": 2018,
           "semana": 9, "pulgadas": 21.7, "conexion": "HDMI", "interno": False}
PANTALLA = {"fabricante": "LEN", "modelo": "", "codigo_producto": "403D", "serie": "0", "anio": 2021, "semana": 20,
            "pulgadas": 14, "conexion": "Interna", "interno": True}
DELL_SIN_SERIE = {"fabricante": "DEL", "modelo": "P2419H", "codigo_producto": "A0C4", "serie": "0", "anio": 2015,
                  "pulgadas": 23.8, "conexion": "DisplayPort", "interno": False}


def _sync(client, serial="NB-MON-01", nombre="NB-MON-01", usuario="ana.prueba", ubicacion="CABA", **extra):
    cuerpo = {"nombre": nombre, "tipo": "Notebook", "serial": serial, "marca": "Lenovo", "modelo": "E14",
              "usuario": usuario, "ubicacion": ubicacion, **extra}
    r = client.post("/api/sync", headers={"X-Sync-Key": SYNC_KEY}, json=cuerpo)
    assert r.status_code == 200, r.text


def _monitores(client, token):
    r = client.get("/api/monitores", headers=bearer(token))
    assert r.status_code == 200, r.text
    return r.json()


def _asset(serial):
    db = database.SessionLocal()
    try:
        return db.query(database.Asset).filter(database.Asset.serial == serial).first()
    finally:
        db.close()


def test_alta_limpia_solo_del_externo_con_serie(client, token):
    _sync(client, monitores_detalle=[PANTALLA, SAMSUNG, DELL_SIN_SERIE])
    d = _monitores(client, token)
    assert d["resumen"]["total"] == 1
    m = d["monitores"][0]
    assert m["marca"] == "Samsung" and m["modelo"] == "S22F350" and m["serial"] == "H4ZK300465"
    assert m["pulgadas"] == 21.7 and m["conexion"] == "HDMI" and m["anio"] == 2018 and m["semana"] == 9
    assert m["usuario"] == "ana.prueba" and m["sede"] == "CABA" and m["pc"]["nombre"] == "NB-MON-01"
    assert m["antiguo"] is True   # 2018: mas de 7 anios
    # la PC guarda los tres (pantalla interna y el Dell sin serie como dato de la PC, sin activo)
    pc = _asset("NB-MON-01")
    r = client.get("/api/monitores/pc/" + pc.id, headers=bearer(token)).json()
    assert len(r["monitores"]) == 3
    assert [x["asset_id"] is not None for x in r["monitores"]] == [False, True, False]
    assert _asset("0") is None


def test_segundo_sync_no_duplica(client, token):
    _sync(client, monitores_detalle=[SAMSUNG])
    _sync(client, monitores_detalle=[SAMSUNG])
    assert _monitores(client, token)["resumen"]["total"] == 1
    db = database.SessionLocal()
    try:
        assert db.query(database.MonitorConexion).count() == 1
    finally:
        db.close()


def test_monitor_movido_de_pc_queda_en_el_historial(client, token):
    _sync(client, monitores_detalle=[SAMSUNG])
    _sync(client, serial="PC-MON-02", nombre="PC-MON-02", usuario="beto.prueba", ubicacion="Rosario",
          monitores_detalle=[SAMSUNG])
    m = _monitores(client, token)["monitores"][0]
    assert m["pc"]["nombre"] == "PC-MON-02" and m["usuario"] == "beto.prueba" and m["sede"] == "Rosario"
    c = client.get("/api/monitores/%s/conexiones" % m["id"], headers=bearer(token)).json()["conexiones"]
    assert [x["pc_nombre"] for x in c] == ["PC-MON-02", "NB-MON-01"]
    assert c[0]["hasta"] is None and c[1]["hasta"] is not None
    hist = client.get("/api/assets/%s/historial" % m["id"], headers=bearer(token)).json()
    assert any(h["campo"] == "conectado_a" and h["valor_ant"] == "NB-MON-01" and h["valor_new"] == "PC-MON-02" for h in hist)
    # desenchufarlo (sync sin monitores) no lo saca de la PC: sigue siendo "su" monitor
    _sync(client, serial="PC-MON-02", nombre="PC-MON-02", monitores_detalle=[])
    assert _monitores(client, token)["monitores"][0]["pc"]["nombre"] == "PC-MON-02"


def test_no_pisa_los_campos_administrativos(client, token):
    _sync(client, monitores_detalle=[SAMSUNG])
    mid = _monitores(client, token)["monitores"][0]["id"]
    r = client.put("/api/assets/" + mid, headers=bearer(token),
                   json={"estado": "Mantenimiento", "comentarios": "pixel muerto", "garantia": "2027-01-01",
                         "modelo": "S22F350FHL"})
    assert r.status_code == 200, r.text
    _sync(client, monitores_detalle=[SAMSUNG])
    a = _asset("H4ZK300465")
    assert a.estado == "Mantenimiento" and a.comentarios == "pixel muerto" and a.garantia == "2027-01-01"
    assert a.modelo == "S22F350FHL"


def test_adopta_un_monitor_cargado_a_mano(client, token):
    r = client.post("/api/assets", headers=bearer(token),
                    json={"tipo": "Monitor", "serial": "H4ZK300465", "marca": "Samsung", "modelo": "S22F350", "nombre": "MON-CABA-01"})
    assert r.status_code == 200, r.text
    _sync(client, monitores_detalle=[SAMSUNG])
    d = _monitores(client, token)
    assert d["resumen"]["total"] == 1 and d["monitores"][0]["nombre"] == "MON-CABA-01" and d["monitores"][0]["pc"]


def test_payload_basura_no_rompe_el_sync(client, token):
    for basura in ("texto", [1, "a", None], [{"fabricante": 123, "serie": ["x"], "pulgadas": "mucho"}],
                   [dict(SAMSUNG, modelo="x" * 9000)], {"a": 1}):
        _sync(client, monitores_detalle=basura)
    assert _asset("NB-MON-01") is not None
    assert _monitores(client, token)["resumen"]["total"] == 0
    # el sync clasico sin el campo sigue igual y no borra la foto anterior
    _sync(client, monitores_detalle=[SAMSUNG])
    _sync(client)
    assert _monitores(client, token)["resumen"]["total"] == 1


def test_borrar_la_pc_o_el_monitor_limpia_sus_datos(client, token):
    _sync(client, monitores_detalle=[SAMSUNG])
    pc, mon = _asset("NB-MON-01"), _asset("H4ZK300465")
    assert client.delete("/api/assets/" + pc.id, headers=bearer(token)).status_code == 200
    m = _monitores(client, token)["monitores"][0]
    assert m["pc"] is None
    assert client.delete("/api/assets/" + mon.id, headers=bearer(token)).status_code == 200
    db = database.SessionLocal()
    try:
        assert db.query(database.MonitorDetalle).count() == 0 and db.query(database.MonitorConexion).count() == 0
        assert db.query(database.PcMonitores).count() == 0
    finally:
        db.close()


def test_requiere_permiso_de_activos(client):
    assert client.get("/api/monitores").status_code == 401
