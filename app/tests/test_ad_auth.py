# -*- coding: utf-8 -*-
"""Login con el usuario de Windows (ad_auth), como Argos. El dominio se simula: en CI no hay controlador."""
import pytest

import ad_auth
import config
import database
from auth import User, rol_de
from conftest import QA_ADMIN, bearer, clave_mala, clave_valida, login

CLAVE_WINDOWS = clave_valida()


@pytest.fixture
def dominio(monkeypatch):
    """Dominio TANGO simulado: acepta CLAVE_WINDOWS para cualquier usuario y cuenta las consultas."""
    llamadas = []

    def validar(usuario, clave):
        llamadas.append(usuario)
        return (True, None) if clave == CLAVE_WINDOWS else (False, 1326)

    monkeypatch.setattr(ad_auth, "habilitado", lambda: True)
    monkeypatch.setattr(ad_auth, "validar", validar)
    monkeypatch.setattr(ad_auth, "nombre_completo", lambda u: "Nombre de " + u)
    monkeypatch.setattr(config, "AD_DOMINIO", "TANGO")
    monkeypatch.setattr(config, "AD_SUFIJO_UPN", "llasesores.corp")
    monkeypatch.setattr(config, "AD_ADMINS", {"jiriarte"})
    ad_auth.limpiar()
    yield llamadas
    ad_auth.limpiar()


def _usuario(username):
    db = database.SessionLocal()
    try:
        u = db.query(User).filter(User.username == username).first()
        return u and {"activo": u.activo, "hash": u.password_hash, "nombre": u.nombre, "rol": rol_de(db, u.id)}
    finally:
        db.close()


def test_admin_de_windows_entra_la_primera_vez(client, dominio):
    r = login(client, "jiriarte", CLAVE_WINDOWS)
    assert r.status_code == 200, r.text
    assert r.json()["user"]["rol"] == "admin"
    u = _usuario("jiriarte")
    assert u["activo"] == "1" and u["hash"] == ad_auth.MARCA and u["nombre"] == "Nombre de jiriarte"


@pytest.mark.parametrize("ident", ["TANGO\\jiriarte", "jiriarte@llasesores.corp", "JIRIARTE"])
def test_formatos_de_usuario_de_windows(client, dominio, ident):
    assert login(client, ident, CLAVE_WINDOWS).status_code == 200
    assert dominio[-1] == "jiriarte"


def test_usuario_nuevo_queda_pendiente_hasta_que_lo_habiliten(client, dominio, token):
    r = login(client, "jperez", CLAVE_WINDOWS)
    assert r.status_code == 403 and "todavía no tiene acceso" in r.json()["detail"]
    assert _usuario("jperez") == {"activo": "0", "hash": ad_auth.MARCA, "nombre": "Nombre de jperez", "rol": "viewer"}
    assert login(client, "jperez", CLAVE_WINDOWS).status_code == 403
    r = client.put("/auth/usuarios/jperez", json={"activo": "1", "rol": "editor"}, headers=bearer(token))
    assert r.status_code == 200, r.text
    r = login(client, "jperez", CLAVE_WINDOWS)
    assert r.status_code == 200 and r.json()["user"]["rol"] == "editor"


def test_no_prueba_por_tercera_vez_para_no_bloquear_la_cuenta(client, dominio):
    r1 = login(client, "jiriarte", clave_mala())
    r2 = login(client, "jiriarte", clave_mala())
    assert r1.status_code == r2.status_code == 401
    assert "tercer intento" in r1.json()["detail"]
    r3 = login(client, "jiriarte", CLAVE_WINDOWS)
    assert r3.status_code == 401 and "no se prueba de nuevo" in r3.json()["detail"]
    assert dominio == ["jiriarte", "jiriarte"]   # la tercera ni llega al dominio


def test_fallo_de_windows_no_crea_usuario(client, dominio):
    assert login(client, "nadie", clave_mala()).status_code == 401
    assert _usuario("nadie") is None


def test_usuarios_locales_siguen_entrando(client, dominio, token):
    assert token   # el fixture ya entro con el admin local de QA
    assert login(client, QA_ADMIN, clave_mala()).status_code == 401
    assert dominio == []   # un usuario local nunca se valida contra Windows


def test_usuario_de_windows_no_cambia_ni_resetea_password_en_atlas(client, dominio, token):
    tok = login(client, "jiriarte", CLAVE_WINDOWS).json()["access_token"]
    r = client.post("/auth/cambiar-password", json={"password_actual": CLAVE_WINDOWS, "password_nuevo": clave_valida()},
                    headers=bearer(tok))
    assert r.status_code == 400 and "Windows" in r.json()["detail"]
    r = client.put("/auth/usuarios/jiriarte", json={"password": clave_valida()}, headers=bearer(token))
    assert r.status_code == 400


def test_sin_dominio_configurado_no_hay_login_de_windows(client, dominio, monkeypatch):
    login(client, "jiriarte", CLAVE_WINDOWS)
    monkeypatch.setattr(ad_auth, "habilitado", lambda: False)
    dominio.clear()
    assert login(client, "jiriarte", CLAVE_WINDOWS).status_code == 401
    assert dominio == []


def test_normalizar_usuario_rechaza_otros_dominios(dominio):
    assert ad_auth.normalizar_usuario("OTRO\\jperez") is None
    assert ad_auth.normalizar_usuario("jperez@gmail.com") is None
    assert ad_auth.normalizar_usuario("j;perez") is None
    assert ad_auth.normalizar_usuario(" Tango\\JPerez ") == "jperez"
