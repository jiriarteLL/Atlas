# -*- coding: utf-8 -*-
"""Seeder del superadmin: los 6 tests obligatorios del README §10."""
import pytest

import database
import seed
from auth import User, UserRole, permisos_de, rol_de, verify_password, PERMISOS
from conftest import SUPERADMIN, SUPERADMIN_PASS, clave_valida, login


def _superadmins():
    db = database.SessionLocal()
    us = db.query(User).filter(User.username == "admin@llyasoc.com").all()
    datos = [(u.id, u.password_hash, rol_de(db, u.id), permisos_de(db, u.id)) for u in us]
    db.close()
    return datos


def test_sin_password_falla(monkeypatch):
    monkeypatch.delenv("SUPERADMIN_INITIAL_PASSWORD")
    assert seed.main() != 0


@pytest.mark.parametrize("debil", ["corta", "password", "123456789012", "admin", "sololetrasminusculas"])
def test_password_debil_falla(monkeypatch, debil):
    monkeypatch.setenv("SUPERADMIN_INITIAL_PASSWORD", debil)
    assert seed.main() != 0


def test_primera_ejecucion_crea_superadmin_con_todos_los_permisos():
    us = _superadmins()
    assert len(us) == 1
    _, _, rol, permisos = us[0]
    assert rol == "superadmin"
    assert set(permisos) == set(PERMISOS)


def test_segunda_ejecucion_no_duplica_ni_cambia_password(monkeypatch):
    antes = _superadmins()
    monkeypatch.setenv("SUPERADMIN_INITIAL_PASSWORD", clave_valida())
    assert seed.main() == 0
    despues = _superadmins()
    assert len(despues) == 1
    assert despues[0][1] == antes[0][1]
    assert verify_password(SUPERADMIN_PASS, despues[0][1])


def test_existente_sin_rol_recibe_superadmin_sin_tocar_password():
    db = database.SessionLocal()
    u = db.query(User).filter(User.username == "admin@llyasoc.com").first()
    hash_antes = u.password_hash
    db.query(UserRole).filter(UserRole.user_id == u.id).delete()
    db.commit()
    db.close()
    assert seed.main() == 0
    (_, hash_despues, rol, _), = _superadmins()
    assert rol == "superadmin"
    assert hash_despues == hash_antes


def test_login_con_la_password_de_la_env(client):
    assert login(client, SUPERADMIN, SUPERADMIN_PASS).status_code == 200


def test_superadmin_sembrado_debe_cambiar_password():
    db = database.SessionLocal()
    u = db.query(User).filter(User.username == "admin@llyasoc.com").first()
    db.close()
    assert u.debe_cambiar_password is True
