# -*- coding: utf-8 -*-
"""Permisos por modulo y por usuario (Accesos, como Argos pero con nivel): control real en el servidor."""
import os

import pytest
from alembic import command
from alembic.config import Config

import ad_auth
import config
import database
from auth import ELIMINAR_ACTIVOS, User, UserModulo, plantilla
from conftest import SUPERADMIN, QA_ADMIN, bearer, clave_valida, crear_usuario_db, login

CLAVE = clave_valida()
ACTIVO = {"tipo": "Notebook", "serial": "PERM-001", "marca": "Lenovo", "modelo": "T14"}
INI = os.path.join(os.path.dirname(__file__), "..", "backend", "alembic.ini")


def _usuario(client, username, rol="viewer"):
    crear_usuario_db(username, username + "@example.test", CLAVE, rol)
    r = login(client, username, CLAVE)
    assert r.status_code == 200, r.text
    return r.json()["access_token"]


def _permisos(client, token, username, modulos, **extra):
    return client.put("/auth/usuarios/%s/permisos" % username, headers=bearer(token),
                      json={"modulos": modulos, **extra})


def _modulos_db(username):
    db = database.SessionLocal()
    try:
        u = db.query(User).filter(User.username == username).first()
        return {f.modulo: f.nivel for f in db.query(UserModulo).filter(UserModulo.user_id == u.id)}
    finally:
        db.close()


# ---------------------------------------------------------------- migracion
def test_la_migracion_siembra_los_modulos_segun_el_rol(client):
    for nombre, rol in (("m-viewer", "viewer"), ("m-editor", "editor"), ("m-admin", "admin")):
        crear_usuario_db(nombre, nombre + "@example.test", CLAVE, rol)
    cfg = Config(INI)
    with database.engine.begin() as con:   # base como antes del despliegue: sin user_modulos
        cfg.attributes["connection"] = con
        command.downgrade(cfg, "0004")
    database.init_db()
    assert _modulos_db("m-viewer") == plantilla("viewer")
    assert _modulos_db("m-editor") == plantilla("editor")
    assert _modulos_db("m-admin") == plantilla("admin")
    # nadie gana ni pierde: viewer sin importar ni accesos; editor sin eliminar ni accesos
    assert "importar" not in plantilla("viewer") and "accesos" not in plantilla("viewer")
    assert ELIMINAR_ACTIVOS not in plantilla("editor") and "accesos" not in plantilla("editor")


# ---------------------------------------------------------------- control por modulo
RUTAS = [  # (ruta de lectura, modulo que alcanza para verla)
    ("/api/assets", "reportes"),
    ("/api/impresoras", "impresoras"),
    ("/api/salud", "salud"),
    ("/api/salud/resumen", "dashboard"),
    ("/api/proyectos", "proyectos"),
    ("/api/tendencias/metricas", "tendencias"),
    ("/api/tickets", "activos"),
]


@pytest.mark.parametrize("ruta,modulo", RUTAS)
def test_cada_modulo_bloquea_sin_permiso_y_deja_con_ver(client, token, ruta, modulo):
    tu = _usuario(client, "parcial")
    assert _permisos(client, token, "parcial", {}).status_code == 200
    assert client.get(ruta, headers=bearer(tu)).status_code == 403
    assert _permisos(client, token, "parcial", {modulo: "ver"}).status_code == 200
    assert client.get(ruta, headers=bearer(tu)).status_code == 200


def test_sin_accesos_no_administra_usuarios(client, token):
    tu = _usuario(client, "lector")
    assert client.get("/auth/usuarios", headers=bearer(tu)).status_code == 403
    assert _permisos(client, token, "lector", {"accesos": "administrar"}).status_code == 200
    assert client.get("/auth/usuarios", headers=bearer(tu)).status_code == 200


def test_ver_no_alcanza_para_editar(client, token):
    tu = _usuario(client, "lector")
    assert client.post("/api/assets", headers=bearer(tu), json=ACTIVO).status_code == 403
    assert client.post("/api/proyectos", headers=bearer(tu), json={"nombre": "P"}).status_code == 403
    # importar permite dar de alta (el CSV), pero no editar activos existentes
    _permisos(client, token, "lector", {"importar": "editar"})
    r = client.post("/api/assets", headers=bearer(tu), json=ACTIVO)
    assert r.status_code == 200
    assert client.put("/api/assets/" + r.json()["id"], headers=bearer(tu), json=ACTIVO).status_code == 403


def test_eliminar_activos_es_un_permiso_aparte(client, token):
    te = _usuario(client, "editor1", "editor")
    aid = client.post("/api/assets", headers=bearer(te), json=ACTIVO).json()["id"]
    assert client.delete("/api/assets/" + aid, headers=bearer(te)).status_code == 403
    # sin poder editar no se puede dar eliminar
    assert _permisos(client, token, "editor1", {"activos": "ver", ELIMINAR_ACTIVOS: "si"}).status_code == 400
    assert _permisos(client, token, "editor1", {"activos": "editar", ELIMINAR_ACTIVOS: "si"}).status_code == 200
    assert client.delete("/api/assets/" + aid, headers=bearer(te)).status_code == 200


def test_el_cambio_vale_en_la_request_siguiente(client, token):
    tu = _usuario(client, "lector")
    assert client.get("/api/impresoras", headers=bearer(tu)).status_code == 200
    _permisos(client, token, "lector", {"activos": "ver"})
    assert client.get("/api/impresoras", headers=bearer(tu)).status_code == 403   # mismo token
    me = client.get("/auth/me", headers=bearer(tu)).json()
    assert me["modulos"] == {"activos": "ver"} and me["permisos"] == ["inventario.ver"] and me["rol"] == "viewer"


def test_modulos_y_niveles_invalidos(client, token):
    _usuario(client, "lector")
    assert _permisos(client, token, "lector", {"inexistente": "ver"}).status_code == 400
    assert _permisos(client, token, "lector", {"salud": "editar"}).status_code == 400   # salud es solo lectura
    assert _permisos(client, token, "lector", {"licencias": "ver"}).status_code == 400  # proximamente
    assert _permisos(client, token, "lector", {"activos": "ninguno", "salud": "ver"}).status_code == 200
    assert _modulos_db("lector") == {"salud": "ver"}


# ---------------------------------------------------------------- protecciones y auditoria
def test_superadmin_y_uno_mismo_no_se_editan(client, token):
    assert _permisos(client, token, SUPERADMIN, {"dashboard": "ver"}).status_code == 400
    assert _permisos(client, token, QA_ADMIN, {"dashboard": "ver"}).status_code == 400
    assert client.get("/auth/usuarios", headers=bearer(token)).status_code == 200


def test_los_admins_de_ad_tienen_todo_y_no_se_editan(client, token, monkeypatch):
    db = database.SessionLocal()
    db.add(User(username="jadmin", nombre="Admin AD", password_hash=ad_auth.MARCA, activo="1"))
    db.commit()
    db.close()
    monkeypatch.setattr(config, "AD_ADMINS", ["jadmin"])
    assert _permisos(client, token, "jadmin", {"dashboard": "ver"}).status_code == 400
    fila = next(u for u in client.get("/auth/usuarios", headers=bearer(token)).json() if u["username"] == "jadmin")
    assert fila["protegido"] and fila["modulos"] == plantilla("admin")


def test_habilitar_pendiente_con_permisos_y_auditoria(client, token):
    crear_usuario_db("pendiente", "pendiente@example.test", CLAVE, "viewer")
    db = database.SessionLocal()
    u = db.query(User).filter(User.username == "pendiente").first()
    u.activo = "0"
    db.query(UserModulo).filter(UserModulo.user_id == u.id).delete()   # como entra un usuario nuevo de Windows
    db.commit()
    db.close()
    assert login(client, "pendiente", CLAVE).status_code == 401
    r = _permisos(client, token, "pendiente", {"impresoras": "editar"}, activar=True)
    assert r.status_code == 200 and r.json()["activo"] == "1" and r.json()["rol"] == "editor"
    tp = login(client, "pendiente", CLAVE).json()["access_token"]
    assert client.get("/api/impresoras", headers=bearer(tp)).status_code == 200
    assert client.get("/api/assets", headers=bearer(tp)).status_code == 403
    db = database.SessionLocal()
    reg = db.query(database.AuditLog).filter(database.AuditLog.accion == "PERMISSIONS_CHANGE").all()
    db.close()
    assert len(reg) == 1 and reg[0].usuario == QA_ADMIN and reg[0].entidad_id == "pendiente"
    assert "impresoras" in reg[0].detalle


def test_cambiar_el_rol_aplica_la_plantilla(client, token):
    _usuario(client, "lector")
    _permisos(client, token, "lector", {"salud": "ver"})
    r = client.put("/auth/usuarios/lector", headers=bearer(token), json={"rol": "editor"})
    assert r.status_code == 200
    assert _modulos_db("lector") == plantilla("editor")


def test_alta_con_modulos_elegidos(client, token):
    r = client.post("/auth/usuarios", headers=bearer(token),
                    json={"username": "nuevo", "password": CLAVE, "nombre": "Nuevo", "email": "nuevo@example.test",
                          "modulos": {"impresoras": "ver"}})
    assert r.status_code == 200
    assert _modulos_db("nuevo") == {"impresoras": "ver"}
    cat = client.get("/auth/modulos", headers=bearer(token)).json()
    assert any(m["clave"] == "licencias" and not m["disponible"] for m in cat["modulos"])
    assert cat["plantillas"]["viewer"] == plantilla("viewer")
