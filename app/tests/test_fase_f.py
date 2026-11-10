# -*- coding: utf-8 -*-
"""Fase F: ciclo de vida (estado, movimientos, vida util), actas y auditoria fisica."""
import os
from datetime import date, timedelta

from alembic import command
from alembic.config import Config

import database
from auth import User, UserModulo, plantilla
from conftest import SYNC_KEY, bearer, clave_valida, crear_usuario_db, login

INI = os.path.join(os.path.dirname(__file__), "..", "backend", "alembic.ini")
CLAVE = clave_valida()
NB = {"nombre": "NB-F-01", "tipo": "Notebook", "marca": "LENOVO", "modelo": "ThinkPad E14", "serial": "TEST-F-01",
      "usuario": "", "ubicacion": "CABA", "estado": "Activo"}
FIRMA = "data:image/png;base64,iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAYAAAAfFcSJAAAADUlEQVR42mNkYPhfDwAChwGA60e6kgAAAABJRU5ErkJggg=="


def _sync(client, **extra):
    r = client.post("/api/sync", json=dict(NB, **extra), headers={"X-Sync-Key": SYNC_KEY})
    assert r.status_code == 200, r.text


def _activo(client, token, serial="TEST-F-01"):
    return next(a for a in client.get("/api/assets", headers=bearer(token)).json() if a["serial"] == serial)


def _ciclo(client, token, aid):
    r = client.get("/api/ciclo/" + aid, headers=bearer(token))
    assert r.status_code == 200, r.text
    return r.json()


def _mov(client, token, aid, **datos):
    return client.post("/api/ciclo/%s/movimientos" % aid, headers=bearer(token), json=datos)


# ---------------------------------------------------------------- ciclo de vida
def test_estado_derivado_de_los_valores_viejos(client, token):
    _sync(client)
    aid = _activo(client, token)["id"]
    assert _ciclo(client, token, aid)["estado_ciclo"] == "En stock"     # "Activo" sin usuario
    _sync(client, usuario="jperez")
    assert _ciclo(client, token, aid)["estado_ciclo"] == "Asignado"     # "Activo" con usuario


def test_movimientos_cambian_estado_y_quedan_registrados(client, token):
    _sync(client)
    aid = _activo(client, token)["id"]
    assert _mov(client, token, aid, tipo="asignacion").status_code == 422          # falta la persona
    r = _mov(client, token, aid, tipo="asignacion", a_usuario="María López", sede="Rosario")
    assert r.status_code == 200, r.text
    assert r.json()["estado"] == "Asignado" and r.json()["usuario"] == "María López" and r.json()["ubicacion"] == "Rosario"
    assert _mov(client, token, aid, tipo="envio_reparacion", motivo="pantalla").json()["estado"] == "En reparación"
    assert _mov(client, token, aid, tipo="vuelta_reparacion").json()["estado"] == "Asignado"
    assert _mov(client, token, aid, tipo="devolucion").json()["usuario"] == ""
    c = _ciclo(client, token, aid)
    assert c["estado_ciclo"] == "En stock"
    assert [m["tipo"] for m in c["movimientos"]] == ["devolucion", "vuelta_reparacion", "envio_reparacion", "asignacion"]
    hist = client.get("/api/assets/%s/historial" % aid, headers=bearer(token)).json()
    assert any(h["campo"] == "estado" and h["valor_new"] == "En reparación" for h in hist)


def test_el_agente_no_pisa_un_estado_puesto_a_mano(client, token):
    _sync(client)
    aid = _activo(client, token)["id"]
    _mov(client, token, aid, tipo="envio_reparacion")
    _sync(client, estado="Activo", usuario="otro")
    a = _activo(client, token)
    assert a["estado"] == "En reparación"


def test_vida_util_y_para_renovar(client, token):
    _sync(client)
    aid = _activo(client, token)["id"]
    assert _ciclo(client, token, aid)["vida_util"]["renovacion"] is None          # sin fecha de compra
    vieja = (date.today() - timedelta(days=5 * 365)).isoformat()
    r = client.put("/api/ciclo/%s/admin" % aid, headers=bearer(token),
                   json={"fecha_compra": vieja, "proveedor": "Proveedor SA", "costo": 1200, "moneda": "USD",
                         "nro_inventario": "CABA 1-99"})
    assert r.status_code == 200, r.text
    v = _ciclo(client, token, aid)["vida_util"]
    assert v["vida_util_meses"] == 48 and v["para_renovar"] and v["base_origen"] == "compra"
    res = client.get("/api/ciclo/resumen", headers=bearer(token)).json()
    assert res["para_renovar"] == 1
    assert client.put("/api/ciclo/%s/admin" % aid, headers=bearer(token), json={"vida_util_meses": 120}).status_code == 200
    assert not _ciclo(client, token, aid)["vida_util"]["para_renovar"]
    # credenciales y campos desconocidos: rechazados
    assert client.put("/api/ciclo/%s/admin" % aid, headers=bearer(token), json={"notas": "clave: 1234"}).status_code == 422
    assert client.put("/api/ciclo/%s/admin" % aid, headers=bearer(token), json={"otro": 1}).status_code == 422


# ---------------------------------------------------------------- actas
def _acta(client, token, aid, **extra):
    datos = {"tipo": "entrega", "persona": "María López", "sede": "CABA", "area": "Auditoría",
             "items": [{"asset_id": aid, "accesorios": ["Cargador", "Mouse"]}]}
    datos.update(extra)
    return client.post("/api/actas", headers=bearer(token), json=datos)


def test_acta_de_entrega_numera_y_al_firmar_asigna(client, token):
    _sync(client)
    _sync(client, serial="TEST-F-02", nombre="NB-F-02")
    aid, aid2 = _activo(client, token)["id"], _activo(client, token, "TEST-F-02")["id"]
    r1, r2 = _acta(client, token, aid), _acta(client, token, aid2)
    assert r1.status_code == 200, r1.text
    anio = date.today().year
    assert r1.json()["numero"] == "ACT-%d-0001" % anio and r2.json()["numero"] == "ACT-%d-0002" % anio
    assert r1.json()["estado"] == "borrador" and r1.json()["items"][0]["accesorios"] == ["Cargador", "Mouse"]
    assert _activo(client, token)["usuario"] == ""                                   # el borrador no cambia nada
    assert client.post("/api/actas/%s/firmar" % r1.json()["id"], headers=bearer(token),
                       json={"firma_receptor": "no-es-png", "firma_soporte": FIRMA}).status_code == 422
    r = client.post("/api/actas/%s/firmar" % r1.json()["id"], headers=bearer(token),
                    json={"firma_receptor": FIRMA, "firma_soporte": FIRMA})
    assert r.status_code == 200, r.text
    assert r.json()["estado"] == "firmada"
    a = _activo(client, token)
    assert a["usuario"] == "María López" and a["estado"] == "Asignado"
    movs = _ciclo(client, token, aid)["movimientos"]
    assert movs[0]["tipo"] == "asignacion" and movs[0]["acta_id"] == r1.json()["id"]
    # una firmada no se vuelve a firmar ni se edita
    assert client.post("/api/actas/%s/firmar" % r1.json()["id"], headers=bearer(token),
                       json={"firma_receptor": FIRMA, "firma_soporte": FIRMA}).status_code == 409
    datos = {"tipo": "entrega", "persona": "X Y", "items": [{"asset_id": aid}]}
    assert client.put("/api/actas/" + r1.json()["id"], headers=bearer(token), json=datos).status_code == 409


def test_acta_de_devolucion_por_escaneo_y_anulacion(client, token):
    _sync(client, usuario="María López")
    aid = _activo(client, token)["id"]
    r = _acta(client, token, aid, tipo="devolucion")
    acta_id = r.json()["id"]
    r = client.post("/api/actas/%s/escaneo" % acta_id, headers=bearer(token),
                    files={"archivo": ("acta.pdf", b"%PDF-1.4 prueba", "application/pdf")})
    assert r.status_code == 200, r.text
    assert r.json()["estado"] == "firmada" and r.json()["escaneo_adjunto_id"]
    assert _activo(client, token)["usuario"] == "" and _ciclo(client, token, aid)["estado_ciclo"] == "En stock"
    adj = client.get("/api/assets/%s/adjuntos" % aid, headers=bearer(token)).json()
    assert any("firmada" in x["nombre"] for x in adj)
    assert client.post("/api/actas/%s/anular" % acta_id, headers=bearer(token), json={"motivo": "x"}).status_code == 422
    r = client.post("/api/actas/%s/anular" % acta_id, headers=bearer(token), json={"motivo": "Error de carga"})
    assert r.status_code == 200 and r.json()["estado"] == "anulada"
    assert client.post("/api/actas/%s/anular" % acta_id, headers=bearer(token), json={"motivo": "otra vez"}).status_code == 409


def test_acta_rechaza_equipos_dados_de_baja_o_inexistentes(client, token):
    _sync(client)
    aid = _activo(client, token)["id"]
    assert _acta(client, token, "NOEXISTE").status_code == 404
    _mov(client, token, aid, tipo="baja")
    assert _acta(client, token, aid).status_code == 409


# ---------------------------------------------------------------- auditoria
def test_auditoria_esperados_encontrados_sobrantes_y_faltantes(client, token):
    _sync(client)                                                      # CABA, esperado y se encuentra
    _sync(client, serial="TEST-F-02", nombre="NB-F-02")                # CABA, esperado y falta
    _sync(client, serial="TEST-F-03", nombre="NB-F-03", ubicacion="Rosario")   # aparece en CABA: sobrante
    aid1, aid3 = _activo(client, token)["id"], _activo(client, token, "TEST-F-03")["id"]
    r = client.post("/api/auditoria", headers=bearer(token), json={"sede": "CABA", "piso": "12", "tipos": ["Notebook"]})
    assert r.status_code == 200, r.text
    cid = r.json()["id"]
    assert r.json()["resumen"]["esperados"] == 2
    leer = lambda codigo, lugar="Piso 12": client.post("/api/auditoria/%s/lecturas" % cid, headers=bearer(token),
                                                        json={"codigo": codigo, "lugar": lugar}).json()
    assert leer("https://atlas.example/#activos?activo=" + aid1)["resultado"] == "encontrado"   # QR de la etiqueta
    assert leer("TEST-F-01")["repetido"] is True
    assert leer("test-f-03")["resultado"] == "sobrante"                                       # por serie
    assert leer("ZZZ-NO-EXISTE")["resultado"] == "desconocido"
    r = client.post("/api/auditoria/%s/cerrar" % cid, headers=bearer(token))
    assert r.status_code == 200, r.text
    res = r.json()["resumen"]
    assert (res["encontrados"], res["faltantes"], res["sobrantes"], res["desconocidos"]) == (1, 1, 1, 1)
    assert client.post("/api/auditoria/%s/lecturas" % cid, headers=bearer(token), json={"codigo": "x"}).status_code == 409
    r = client.post("/api/auditoria/%s/mover-sobrantes" % cid, headers=bearer(token), json={})
    assert r.json()["movidos"] == 1
    assert _activo(client, token, "TEST-F-03")["ubicacion"] == "CABA"
    assert _ciclo(client, token, aid3)["movimientos"][0]["tipo"] == "traslado"


def test_auditoria_encuentra_por_numero_de_inventario(client, token):
    _sync(client)
    aid = _activo(client, token)["id"]
    client.put("/api/ciclo/%s/admin" % aid, headers=bearer(token), json={"nro_inventario": "CABA 1-32"})
    cid = client.post("/api/auditoria", headers=bearer(token), json={"sede": "CABA"}).json()["id"]
    r = client.post("/api/auditoria/%s/lecturas" % cid, headers=bearer(token), json={"codigo": "caba 1-32"})
    assert r.json()["resultado"] == "encontrado"


# ---------------------------------------------------------------- permisos y migracion
def test_permisos(client, token):
    _sync(client)
    aid = _activo(client, token)["id"]
    crear_usuario_db("f-viewer", "f-viewer@example.test", CLAVE, "viewer")
    tok = login(client, "f-viewer", CLAVE).json()["access_token"]
    assert client.get("/api/ciclo/" + aid, headers=bearer(tok)).status_code == 200
    assert _mov(client, tok, aid, tipo="devolucion").status_code == 403
    assert client.get("/api/actas", headers=bearer(tok)).status_code == 200
    assert _acta(client, tok, aid).status_code == 403
    assert client.get("/api/auditoria", headers=bearer(tok)).status_code == 200
    assert client.post("/api/auditoria", headers=bearer(tok), json={"sede": "CABA"}).status_code == 403
    r = client.put("/auth/usuarios/f-viewer/permisos", headers=bearer(token), json={"modulos": {"dashboard": "ver"}})
    assert r.status_code == 200, r.text
    assert client.get("/api/auditoria", headers=bearer(tok)).status_code == 403
    assert client.get("/api/actas", headers=bearer(tok)).status_code == 403


def test_la_migracion_suma_auditoria_a_los_usuarios_con_modulos(client):
    for nombre, rol in (("a-viewer", "viewer"), ("a-editor", "editor"), ("a-admin", "admin")):
        crear_usuario_db(nombre, nombre + "@example.test", CLAVE, rol)
    cfg = Config(INI)
    with database.engine.begin() as con:   # base como antes de la fase F
        cfg.attributes["connection"] = con
        command.downgrade(cfg, "0008")
    database.init_db()
    db = database.SessionLocal()
    try:
        for nombre, rol in (("a-viewer", "viewer"), ("a-editor", "editor"), ("a-admin", "admin")):
            u = db.query(User).filter(User.username == nombre).first()
            m = {f.modulo: f.nivel for f in db.query(UserModulo).filter(UserModulo.user_id == u.id)}
            assert m == plantilla(rol), nombre
        assert plantilla("viewer")["auditoria"] == "ver" and plantilla("editor")["auditoria"] == "editar"
    finally:
        db.close()
