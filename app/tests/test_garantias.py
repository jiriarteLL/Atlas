# -*- coding: utf-8 -*-
"""Garantias (fase C): parseo de la pagina de Lenovo (sin red), sincronizacion con Asset.garantia + Historial,
carga manual que no se pisa, seleccion de la corrida automatica, importacion CSV (HP) y permisos."""
import os
import time
from datetime import date, datetime, timedelta

from alembic import command
from alembic.config import Config

import database
import garantias
from conftest import bearer, clave_valida, crear_usuario_db, login

INI = os.path.join(os.path.dirname(__file__), "..", "backend", "alembic.ini")
HOY = date.today()
FIN = HOY + timedelta(days=700)
EXT = HOY + timedelta(days=30)
# Como la pagina real: el JSON va embebido en un <script>, con BaseUpmaWarranties antes y texto con corchetes
HTML = ('<html><script>window.ds = {"BaseUpmaWarranties":[{"End":"%(ext)s","Status":1,"StatusV2":"Active"}],'
        '"UpmaWarranties":[{"Start":"%(ini)s","End":"%(fin)s","Status":1,"WarrentyType":"TP1",'
        '"Description":"Incluye [piezas] y mano de obra","Origin":"Factory Warranty","StatusV2":"Expired",'
        '"DeliveryType":"on_site","Duration":36,"Name":"3 YR Onsite"},'
        '{"Start":"%(ini2)s","End":"%(ext)s","Status":-1,"Origin":"Extension","DeliveryType":"depot",'
        '"Duration":12,"Name":"1 YR Depot"}],"Otro":"x"};</script></html>') % {
    "ini": (HOY - timedelta(days=400)).isoformat(), "fin": FIN.isoformat(),
    "ini2": (HOY - timedelta(days=335)).isoformat(), "ext": EXT.isoformat()}
SIN_JSON = "<html><body>Producto no encontrado</body></html>"


def _activo(client, token, **extra):
    datos = {"nombre": "NB-G", "tipo": "Notebook", "marca": "LENOVO", "modelo": "E14", "serial": "PF5JZXCD",
             "estado": "Activo", "ubicacion": "CABA"}
    datos.update(extra)
    r = client.post("/api/assets", headers=bearer(token), json=datos)
    assert r.status_code in (200, 201), r.text
    return r.json()["id"]


# ---------------------------------------------------------------- parseo
def test_parsea_upma_fin_inicio_estado_por_fecha():
    d = garantias.parsear_lenovo(HTML)
    assert d["fin"] == FIN and d["inicio"] == HOY - timedelta(days=400)
    assert d["estado"] == "vigente"            # por fecha, aunque StatusV2 diga Expired
    assert d["cobertura"] == "3 YR Onsite" and d["entrega"] == "on_site" and d["origen"] == "Factory Warranty"
    assert [c["nombre"] for c in d["coberturas"]] == ["3 YR Onsite", "1 YR Depot"]
    assert "Description" not in str(d) and "piezas" not in str(d)


def test_sin_upma_usa_base_y_sin_json_es_none():
    base = '<script>{"BaseUpmaWarranties":[{"End":"2020-01-31","StatusV2":"Active"}]}</script>'
    d = garantias.parsear_lenovo(base)
    assert d["fin"] == date(2020, 1, 31) and d["estado"] == "vencida" and d["inicio"] is None
    assert garantias.parsear_lenovo(SIN_JSON) is None
    assert garantias.parsear_lenovo('{"UpmaWarranties":[{"End":"basura"}]}') is None


def test_serie_invalida_no_consulta(monkeypatch):
    monkeypatch.setattr(garantias, "_descargar", lambda s: (_ for _ in ()).throw(AssertionError("consulto")))
    assert garantias.consultar_lenovo("../../etc") == (None, "Serie vacía o inválida")
    assert garantias.consultar_lenovo("") == (None, "Serie vacía o inválida")


# ---------------------------------------------------------------- consulta y sincronizacion
def test_consulta_sincroniza_asset_garantia_y_historial(client, token, monkeypatch):
    monkeypatch.setattr(garantias, "_descargar", lambda s: HTML)
    aid = _activo(client, token)
    r = client.post("/api/assets/%s/garantia" % aid, headers=bearer(token))
    assert r.status_code == 200, r.text
    assert r.json()["garantia"] == FIN.isoformat() and r.json()["cobertura"] == "3 YR Onsite"
    g = client.get("/api/garantias/" + aid, headers=bearer(token)).json()
    assert g["fuente"] == "lenovo" and g["inicio"] == (HOY - timedelta(days=400)).isoformat()
    assert g["entrega_texto"] == "En sitio" and len(g["coberturas"]) == 2 and g["dias"] == 700
    ficha = client.get("/api/assets/%s/ficha" % aid, headers=bearer(token)).json()
    assert ficha["garantia"] == FIN.isoformat()
    hist = client.get("/api/assets/%s/historial" % aid, headers=bearer(token)).json()
    assert any(h["campo"] == "garantia" and h["valor_new"] == FIN.isoformat() for h in hist)


def test_error_queda_guardado_y_no_borra_lo_anterior(client, token, monkeypatch):
    monkeypatch.setattr(garantias, "_descargar", lambda s: HTML)
    aid = _activo(client, token)
    client.post("/api/assets/%s/garantia" % aid, headers=bearer(token))
    monkeypatch.setattr(garantias, "_descargar", lambda s: SIN_JSON)
    r = client.post("/api/assets/%s/garantia" % aid, headers=bearer(token))
    assert r.status_code == 422
    g = client.get("/api/garantias/" + aid, headers=bearer(token)).json()
    assert g["fin"] == FIN.isoformat() and "Lenovo" in g["error"]


def test_manual_no_la_pisa_lenovo_y_se_puede_quitar(client, token, monkeypatch):
    aid = _activo(client, token)
    fin = (HOY + timedelta(days=100)).isoformat()
    r = client.put("/api/garantias/" + aid, headers=bearer(token),
                   json={"fin": fin, "inicio": HOY.isoformat(), "proveedor": "Lenovo", "contrato": "EXT-1"})
    assert r.status_code == 200, r.text
    assert r.json()["fuente"] == "manual"
    # ni el boton ni la corrida automatica la pisan
    monkeypatch.setattr(garantias, "_descargar", lambda s: HTML)
    assert client.post("/api/assets/%s/garantia" % aid, headers=bearer(token)).status_code == 409
    assert aid not in garantias.pendientes(database.SessionLocal(), refresco_dias=30)
    assert client.get("/api/garantias/" + aid, headers=bearer(token)).json()["fin"] == fin
    # quitar la carga manual vuelve a la fuente automatica
    r = client.delete("/api/garantias/%s/manual" % aid, headers=bearer(token))
    assert r.status_code == 200 and r.json()["fin"] is None
    assert client.post("/api/assets/%s/garantia" % aid, headers=bearer(token)).json()["garantia"] == FIN.isoformat()


def test_editar_la_fecha_en_la_ficha_la_vuelve_manual(client, token):
    aid = _activo(client, token)
    fin = (HOY + timedelta(days=50)).isoformat()
    assert client.put("/api/assets/" + aid, headers=bearer(token), json={"garantia": fin}).status_code == 200
    g = client.get("/api/garantias/" + aid, headers=bearer(token)).json()
    assert g["fuente"] == "manual" and g["fin"] == fin


def test_manual_rechaza_credenciales_y_fechas_al_reves(client, token):
    aid = _activo(client, token)
    r = client.put("/api/garantias/" + aid, headers=bearer(token), json={"fin": HOY.isoformat(), "notas": "pass: 1234"})
    assert r.status_code == 422
    r = client.put("/api/garantias/" + aid, headers=bearer(token),
                   json={"fin": HOY.isoformat(), "inicio": (HOY + timedelta(days=1)).isoformat()})
    assert r.status_code == 422


# ---------------------------------------------------------------- corrida automatica
def _garantia(aid, **campos):
    db = database.SessionLocal()
    db.add(database.AssetGarantia(asset_id=aid, **campos))
    db.commit()
    db.close()


def test_pendientes_selecciona_sin_dato_viejo_y_por_vencer(client, token):
    ahora = datetime.utcnow()
    sin_dato = _activo(client, token, serial="SER00001")
    viejo = _activo(client, token, serial="SER00002")
    _garantia(viejo, fuente="lenovo", fin=HOY + timedelta(days=500), consultado=ahora - timedelta(days=40))
    reciente = _activo(client, token, serial="SER00003")
    _garantia(reciente, fuente="lenovo", fin=HOY + timedelta(days=500), consultado=ahora - timedelta(days=2))
    por_vencer = _activo(client, token, serial="SER00004")
    _garantia(por_vencer, fuente="lenovo", fin=HOY + timedelta(days=20), consultado=ahora - timedelta(days=2))
    baja = _activo(client, token, serial="SER00005", estado="Dado de baja")
    hp = _activo(client, token, serial="SER00006", marca="HP")
    sin_serie = _activo(client, token, serial="N/A")
    db = database.SessionLocal()
    try:
        ids = garantias.pendientes(db, ahora, refresco_dias=30)
        assert ids[0] == sin_dato and set(ids) == {sin_dato, viejo, por_vencer}
        assert not ({reciente, baja, hp, sin_serie} & set(ids))
        # sin refresco periodico (0) igual entran las sin dato y las por vencer
        assert set(garantias.pendientes(db, ahora, refresco_dias=0)) == {sin_dato, por_vencer}
    finally:
        db.close()


def test_corrida_guarda_y_corta_si_lenovo_cambia_la_pagina(client, token):
    ids = [_activo(client, token, serial="SER1000%d" % i, nombre="NB-%d" % i) for i in range(7)]
    r = garantias.correr(refresco_dias=30, pausa_s=0, consultar=lambda s: (None, "formato"))
    assert r["errores"] == garantias.FORMATO_SEGUIDOS and "cort" in r["mensaje"]
    estado = client.get("/api/garantias/estado-actualizacion", headers=bearer(token)).json()
    assert not estado["corriendo"] and estado["errores"] == garantias.FORMATO_SEGUIDOS
    datos = garantias.parsear_lenovo(HTML)
    r = garantias.correr(refresco_dias=30, pausa_s=0, consultar=lambda s: (datos, ""))
    assert r["ok"] == len(ids) and r["errores"] == 0


def test_un_solo_proceso_corre_a_la_vez(client, token):
    _activo(client, token)
    db = database.SessionLocal()
    try:
        assert garantias._tomar_lease(db, "otro-proceso", datetime.utcnow())
        assert garantias.correr(pausa_s=0, consultar=lambda s: (None, "x")) is None   # el lease es del otro
    finally:
        db.close()


def test_actualizar_no_bloquea_la_request(client, token, monkeypatch):
    aid = _activo(client, token)

    def lento(serie):
        time.sleep(1.5)
        return HTML
    monkeypatch.setattr(garantias, "_descargar", lento)
    monkeypatch.setattr(garantias.config, "GARANTIA_PAUSA_S", 0)
    t0 = time.monotonic()
    r = client.post("/api/garantias/actualizar", headers=bearer(token))
    assert r.status_code == 200 and r.json()["status"] == "encolada"
    assert time.monotonic() - t0 < 1.2
    for _ in range(60):   # espera a que termine el hilo (que no quede corriendo contra la base del test siguiente)
        e = client.get("/api/garantias/estado-actualizacion", headers=bearer(token)).json()
        if e["fin"] and not e["corriendo"]:
            break
        time.sleep(0.1)
    assert client.get("/api/garantias/" + aid, headers=bearer(token)).json()["fin"] == FIN.isoformat()


# ---------------------------------------------------------------- vista, resumen, CSV
def test_lista_y_resumen(client, token):
    a = _activo(client, token, serial="SER20001")
    b = _activo(client, token, serial="SER20002", marca="HP", tipo="Impresora")
    _activo(client, token, serial="SER20003", marca="HP")
    _garantia(a, fuente="lenovo", fin=HOY + timedelta(days=30), consultado=datetime.utcnow())
    _garantia(b, fuente="manual", fin=HOY - timedelta(days=3))
    r = client.get("/api/garantias/resumen", headers=bearer(token)).json()
    assert (r["vigentes"], r["vencen_90"], r["vencidas"], r["sin_dato"]) == (1, 1, 1, 1)
    assert r["por_marca"]["HP"] == {"total": 2, "vigentes": 0, "vencidas": 1, "sin_dato": 1}
    filas = {f["serial"]: f for f in client.get("/api/garantias", headers=bearer(token)).json()}
    assert filas["SER20001"]["dias"] == 30 and filas["SER20001"]["consultable"]
    assert filas["SER20002"]["estado"] == "vencida" and not filas["SER20002"]["consultable"]


def test_importar_csv_hp(client, token):
    _activo(client, token, serial="5CD111", marca="HP", nombre="NB-HP1")
    _activo(client, token, serial="5CD222", marca="HP", nombre="NB-HP2")
    csv = ("serie;inicio;fin;cobertura;proveedor;contrato\n"
           "5cd111;01/03/2024;28/02/2027;3 años en sitio;HP;C-1\n"
           "5CD222;;2026-01-10;;HP;\n"
           "NOEXISTE;;2027-01-01;;;\n"
           "5CD111;;mañana;;;\n"
           "5CD222;;2027-01-01;user: admin;;\n").encode("utf-8-sig")
    r = client.post("/api/garantias/importar", headers=bearer(token), files={"archivo": ("g.csv", csv, "text/csv")})
    assert r.status_code == 200, r.text
    j = r.json()
    assert j["actualizados"] == 2 and j["no_encontrados"] == ["NOEXISTE"] and len(j["errores"]) == 2
    filas = {f["serial"]: f for f in client.get("/api/garantias", headers=bearer(token)).json()}
    assert filas["5CD111"]["fin"] == "2027-02-28" and filas["5CD111"]["inicio"] == "2024-03-01"
    assert filas["5CD111"]["fuente"] == "manual" and filas["5CD111"]["contrato"] == "C-1"
    sin_cols = client.post("/api/garantias/importar", headers=bearer(token),
                           files={"archivo": ("g.csv", b"a,b\n1,2\n", "text/csv")})
    assert sin_cols.status_code == 400
    assert client.get("/api/garantias/plantilla.csv", headers=bearer(token)).text.startswith("﻿serie,")


def test_permisos(client, token):
    aid = _activo(client, token)
    clave = clave_valida()
    crear_usuario_db("g-viewer", "g-viewer@example.test", clave, "viewer")
    tv = login(client, "g-viewer", clave).json()["access_token"]
    assert client.get("/api/garantias", headers=bearer(tv)).status_code == 200
    assert client.put("/api/garantias/" + aid, headers=bearer(tv), json={"fin": HOY.isoformat()}).status_code == 403
    assert client.post("/api/garantias/actualizar", headers=bearer(tv)).status_code == 403
    assert client.post("/api/garantias/importar", headers=bearer(tv),
                       files={"archivo": ("g.csv", b"serie,fin\n", "text/csv")}).status_code == 403
    db = database.SessionLocal()   # sin ningun modulo: nada
    from auth import User, UserModulo
    u = db.query(User).filter(User.username == "g-viewer").first()
    db.query(UserModulo).filter(UserModulo.user_id == u.id).delete()
    db.commit()
    db.close()
    assert client.get("/api/garantias", headers=bearer(tv)).status_code == 403
    assert client.get("/api/garantias").status_code == 401


def test_borrar_el_activo_borra_su_garantia(client, token):
    aid = _activo(client, token)
    _garantia(aid, fuente="manual", fin=HOY)
    assert client.delete("/api/assets/" + aid, headers=bearer(token)).status_code == 200
    db = database.SessionLocal()
    assert db.query(database.AssetGarantia).count() == 0
    db.close()


def test_migracion_0009_crea_y_baja(client):
    cfg = Config(INI)
    with database.engine.begin() as con:
        cfg.attributes["connection"] = con
        command.downgrade(cfg, "0008")
    from sqlalchemy import inspect
    assert "asset_garantia" not in inspect(database.engine).get_table_names()
    database.init_db()
    tablas = inspect(database.engine).get_table_names()
    assert "asset_garantia" in tablas and "garantia_corrida" in tablas
