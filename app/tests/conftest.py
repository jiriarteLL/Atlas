# -*- coding: utf-8 -*-
"""Tests sin Docker: SQLite en un archivo temporal. El entorno se fija ANTES de importar la app."""
import os
import secrets
import sys
import tempfile

import pytest


def clave_valida():
    """Password que cumple la politica, generada en cada corrida (sin secretos literales en el repo)."""
    return "Aa1-" + secrets.token_hex(8)


def clave_mala():
    """Password bien formada pero que no es la de nadie."""
    return "Zz9-" + secrets.token_hex(8)


_TMP = tempfile.mkdtemp(prefix="inventario-tests-")
SUPERADMIN_PASS = clave_valida()
MAESTRO_KEY = secrets.token_hex(16)
SYNC_KEY = secrets.token_hex(16)

os.environ.update({
    "DATABASE_URL": "sqlite:///" + os.path.join(_TMP, "test.db").replace("\\", "/"),
    "JWT_SECRET": secrets.token_hex(32),
    "MAESTRO_API_KEY": MAESTRO_KEY,
    "SYNC_API_KEY": SYNC_KEY,
    "SUPERADMIN_INITIAL_PASSWORD": SUPERADMIN_PASS,
    "FRONTEND_DIST": os.path.join(_TMP, "dist"),
    "AGENTE_DIR": os.path.join(_TMP, "agente"),
    "SNAPSHOT_DIAS": "0",
    "GARANTIA_REFRESCO_DIAS": "0",   # sin hilo de fondo que consulte a Lenovo
    "COOKIES_SEGURAS": "0",   # el TestClient va por http: con Secure no mandaria la cookie
    "LOG_FORMAT": "json",
})
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "backend"))

from fastapi.testclient import TestClient  # noqa: E402

import database  # noqa: E402
import main  # noqa: E402
import seed  # noqa: E402
from auth import reiniciar_limites  # noqa: E402


@pytest.fixture(autouse=True)
def base_limpia():
    """Cada test arranca con la base vacia + superadmin sembrado y el rate limit en cero."""
    database.Base.metadata.drop_all(database.engine)
    with database.engine.begin() as con:   # sin esto Alembic creeria que la base ya esta migrada
        con.exec_driver_sql("DROP TABLE IF EXISTS alembic_version")
    seed.seed_superadmin()
    reiniciar_limites()
    yield


@pytest.fixture
def client():
    with TestClient(main.app) as c:
        yield c


SUPERADMIN = "admin@llyasoc.com"
# Usuario de QA propio (BEST_PRACTICES §7.3: los tests no operan con el superadmin real salvo el seeder).
QA_ADMIN, QA_ADMIN_EMAIL, QA_ADMIN_PASS = "qa-admin", "qa-admin@example.test", clave_valida()


def login(client, usuario=QA_ADMIN, password=QA_ADMIN_PASS):
    return client.post("/auth/login", data={"username": usuario, "password": password})


def crear_usuario_db(username, email, password, rol):
    """Alta directa en la base (sin pasar por la API)."""
    from auth import User, asignar_rol, hash_password
    db = database.SessionLocal()
    u = User(username=username, email=email, nombre=username, password_hash=hash_password(password))
    db.add(u)
    db.flush()
    asignar_rol(db, u, rol)
    db.commit()
    db.close()


@pytest.fixture
def token(client):
    crear_usuario_db(QA_ADMIN, QA_ADMIN_EMAIL, QA_ADMIN_PASS, "admin")
    r = login(client)
    assert r.status_code == 200, r.text
    return r.json()["access_token"]


def bearer(tok):
    return {"Authorization": "Bearer " + tok}
