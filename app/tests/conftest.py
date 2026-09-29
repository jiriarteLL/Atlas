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
    "STORAGE_DIR": os.path.join(_TMP, "storage"),
    "FRONTEND_DIST": os.path.join(_TMP, "dist"),
    "AGENTE_DIR": os.path.join(_TMP, "agente"),
    "SNAPSHOT_DIAS": "0",
})
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "backend"))

from fastapi.testclient import TestClient  # noqa: E402

import database  # noqa: E402
import main  # noqa: E402
import seed  # noqa: E402
from ratelimit import limiter  # noqa: E402


@pytest.fixture(autouse=True)
def base_limpia():
    """Cada test arranca con la base vacia + superadmin sembrado y el rate limit en cero."""
    database.Base.metadata.drop_all(database.engine)
    seed.seed_superadmin()
    limiter.reset()
    yield


@pytest.fixture
def client():
    with TestClient(main.app) as c:
        yield c


def login(client, usuario="admin@llyasoc.com", password=SUPERADMIN_PASS):
    return client.post("/auth/login", data={"username": usuario, "password": password})


@pytest.fixture
def token(client):
    r = login(client)
    assert r.status_code == 200, r.text
    return r.json()["access_token"]


def bearer(tok):
    return {"Authorization": "Bearer " + tok}
