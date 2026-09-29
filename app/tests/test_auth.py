# -*- coding: utf-8 -*-
"""Login propio, logout con revocacion, rate limit y permisos (README §7-§8, Gate 2)."""
import pytest

from conftest import SUPERADMIN_PASS, bearer, clave_mala, clave_valida, login

CLAVE_USUARIO = clave_valida()
CLAVE_NUEVA = clave_valida()

PROTEGIDOS = ["/api/assets", "/api/proyectos", "/api/tickets", "/api/equipo", "/api/tendencias",
              "/api/tendencias/metricas", "/api/garantias/vencimientos", "/api/glpi/resumen",
              "/api/assets/X/historial", "/api/assets/X/adjuntos", "/auth/me", "/auth/perfil"]


def test_login_valido_200_con_email(client):
    r = login(client)
    assert r.status_code == 200
    d = r.json()
    assert d["access_token"]
    assert d["user"]["rol"] == "superadmin"
    assert "usuarios.administrar" in d["user"]["permisos"]


def test_login_invalido_401(client):
    assert login(client, password=clave_mala()).status_code == 401
    assert login(client, usuario="nadie@llyasoc.com").status_code == 401


def test_rate_limit_login_429(client):
    codigos = [login(client, password=clave_mala()).status_code for _ in range(6)]
    assert codigos[:5] == [401] * 5
    assert codigos[5] == 429


def test_login_path_de_maestro_acepta_json(client):
    r = client.post("/login", json={"email": "admin@llyasoc.com", "password": SUPERADMIN_PASS})
    assert r.status_code == 200 and r.json()["access_token"]
    assert client.post("/login", json={"email": "admin@llyasoc.com", "password": clave_mala()}).status_code == 401
    assert client.post("/login", json={}).status_code == 401


def test_rate_limit_compartido_entre_login_y_auth_login(client):
    codigos = [client.post("/login", json={"email": "x@y.com", "password": clave_mala()}).status_code for _ in range(3)]
    codigos += [login(client, password=clave_mala()).status_code for _ in range(3)]
    assert codigos[:5] == [401] * 5 and codigos[5] == 429


def test_placeholder_de_env_example_no_sirve_como_password():
    from auth import validar_password
    assert validar_password("cambiar" + clave_valida()) is not None


@pytest.mark.parametrize("ruta", PROTEGIDOS)
def test_endpoint_protegido_sin_token_401(client, ruta):
    assert client.get(ruta).status_code == 401


@pytest.mark.parametrize("ruta", PROTEGIDOS)
def test_endpoint_protegido_con_token_200(client, token, ruta):
    assert client.get(ruta, headers=bearer(token)).status_code == 200


def test_logout_invalida_el_token(client, token):
    assert client.get("/api/assets", headers=bearer(token)).status_code == 200
    assert client.post("/auth/logout", headers=bearer(token)).status_code == 200
    assert client.get("/api/assets", headers=bearer(token)).status_code == 401


def test_token_invalido_401(client):
    assert client.get("/api/assets", headers=bearer("no.es.un.jwt")).status_code == 401


def _crear(client, token, username, rol, password=CLAVE_USUARIO):
    r = client.post("/auth/usuarios", headers=bearer(token),
                    json={"username": username, "password": password, "nombre": username, "rol": rol})
    assert r.status_code == 200, r.text
    return login(client, username, password).json()["access_token"]


def test_viewer_es_solo_lectura(client, token):
    tv = _crear(client, token, "lector", "viewer")
    assert client.get("/api/assets", headers=bearer(tv)).status_code == 200
    r = client.post("/api/assets", headers=bearer(tv),
                    json={"tipo": "Notebook", "serial": "SER123", "marca": "Lenovo", "modelo": "T14"})
    assert r.status_code == 403
    assert client.get("/auth/usuarios", headers=bearer(tv)).status_code == 403


def test_editor_no_elimina_activos(client, token):
    te = _crear(client, token, "editor1", "editor")
    r = client.post("/api/assets", headers=bearer(te),
                    json={"tipo": "Notebook", "serial": "SER124", "marca": "Lenovo", "modelo": "T14"})
    assert r.status_code == 200
    assert client.delete("/api/assets/" + r.json()["id"], headers=bearer(te)).status_code == 403
    assert client.delete("/api/assets/" + r.json()["id"], headers=bearer(token)).status_code == 200


def test_password_debil_rechazada(client, token):
    for debil in ("corta1A!", "password", "todominusculas123", "Aaaaaaaaaaaa1"):
        r = client.post("/auth/usuarios", headers=bearer(token),
                        json={"username": "x" + str(len(debil)), "password": debil, "nombre": "x", "rol": "viewer"})
        assert r.status_code == 400, debil


def test_cambio_de_password_invalida_sesiones_viejas(client, token):
    r = client.post("/auth/cambiar-password", headers=bearer(token),
                    json={"password_actual": SUPERADMIN_PASS, "password_nuevo": CLAVE_NUEVA})
    assert r.status_code == 200
    assert client.get("/api/assets", headers=bearer(token)).status_code == 401
    assert login(client).status_code == 401
    nuevo = login(client, password=CLAVE_NUEVA).json()["access_token"]
    assert client.get("/api/assets", headers=bearer(nuevo)).status_code == 200


def test_usuario_desactivado_pierde_la_sesion(client, token):
    tv = _crear(client, token, "temporal", "viewer")
    assert client.get("/api/assets", headers=bearer(tv)).status_code == 200
    assert client.delete("/auth/usuarios/temporal", headers=bearer(token)).status_code == 200
    assert client.get("/api/assets", headers=bearer(tv)).status_code == 401


def test_superadmin_no_se_puede_degradar_ni_borrar(client, token):
    _crear(client, token, "admin2", "admin")
    t2 = login(client, "admin2", CLAVE_USUARIO).json()["access_token"]
    assert client.put("/auth/usuarios/admin@llyasoc.com", headers=bearer(t2), json={"rol": "viewer"}).status_code == 400
    assert client.delete("/auth/usuarios/admin@llyasoc.com", headers=bearer(t2)).status_code == 400


def test_audit_log_registra_eventos_de_auth(client, token):
    import database
    client.post("/auth/logout", headers=bearer(token))
    login(client, password=clave_mala())
    db = database.SessionLocal()
    acciones = {a.accion for a in db.query(database.AuditLog).all()}
    db.close()
    assert {"LOGIN_SUCCESS", "LOGOUT", "LOGIN_FAILED"} <= acciones
