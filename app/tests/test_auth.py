# -*- coding: utf-8 -*-
"""Login propio, refresh rotativo, logout con revocacion, limites y permisos (SPEC §2.4, 03-AUTENTICACION)."""
import json
import logging

import pytest

import config
from conftest import (QA_ADMIN, QA_ADMIN_PASS, SUPERADMIN, SUPERADMIN_PASS, bearer, clave_mala, clave_valida,
                      crear_usuario_db, login)

CLAVE_USUARIO = clave_valida()
CLAVE_NUEVA = clave_valida()
XRW = {"X-Requested-With": "fetch"}

PROTEGIDOS = ["/api/assets", "/api/proyectos", "/api/tickets", "/api/equipo", "/api/tendencias",
              "/api/tendencias/metricas", "/api/garantias/vencimientos", "/api/glpi/resumen",
              "/api/assets/X/historial", "/api/assets/X/adjuntos", "/auth/me", "/auth/perfil"]


# ---------------------------------------------------------------- contrato del Gate 2 (superadmin sembrado)
def test_login_superadmin_valido_200_con_email(client):
    r = login(client, SUPERADMIN, SUPERADMIN_PASS)
    assert r.status_code == 200
    d = r.json()
    assert d["access_token"] and d["user"]["rol"] == "superadmin"
    assert "usuarios.administrar" in d["user"]["permisos"]
    assert d["user"]["debe_cambiar_password"] is True   # la UI lo obliga a cambiarla
    assert d["expires_in"] == config.TOKEN_TTL_MIN * 60 <= 3600


def test_superadmin_recien_sembrado_accede_a_endpoints_protegidos(client):
    """El cambio de password inicial lo exige la UI, no la API: el smoke del Gate 2 usa este usuario."""
    tok = login(client, SUPERADMIN, SUPERADMIN_PASS).json()["access_token"]
    assert client.get("/api/assets", headers=bearer(tok)).status_code == 200


def test_login_path_de_maestro_acepta_json(client, token):
    r = client.post("/login", json={"email": "qa-admin@example.test", "password": QA_ADMIN_PASS})
    assert r.status_code == 200 and r.json()["access_token"]
    assert client.post("/login", json={"email": "qa-admin@example.test", "password": clave_mala()}).status_code == 401
    assert client.post("/login", json={}).status_code == 401


def test_login_invalido_401_mismo_mensaje(client, token):
    a = login(client, password=clave_mala())
    b = login(client, usuario="nadie@example.test")
    assert a.status_code == b.status_code == 401
    assert a.json() == b.json()   # no revela si el usuario existe


# ---------------------------------------------------------------- limites y bloqueo
def test_rate_limit_por_ip_429(client):
    codigos = [login(client, usuario="x%d@example.test" % i, password=clave_mala()).status_code for i in range(6)]
    assert codigos[:5] == [401] * 5
    assert codigos[5] == 429


def test_rate_limit_compartido_entre_login_y_auth_login(client):
    codigos = [client.post("/login", json={"email": "a%d@example.test" % i, "password": clave_mala()}).status_code
               for i in range(3)]
    codigos += [login(client, usuario="b%d@example.test" % i, password=clave_mala()).status_code for i in range(3)]
    assert codigos[:5] == [401] * 5 and codigos[5] == 429


def test_bloqueo_de_cuenta_tras_5_fallos(client, token, monkeypatch):
    import auth
    for _ in range(5):
        auth.limiter.reset()   # descarta el limite por IP: aca se prueba el bloqueo de la cuenta
        assert login(client, password=clave_mala()).status_code == 401
    auth.limiter.reset()
    assert login(client).status_code == 401   # password correcta, pero la cuenta esta bloqueada
    import database
    db = database.SessionLocal()
    acciones = [a.accion for a in db.query(database.AuditLog).all()]
    db.close()
    assert "ACCOUNT_LOCKED" in acciones and "LOGIN_LOCKED" in acciones


def test_rate_limit_por_email_por_hora(client, token, monkeypatch):
    import auth
    monkeypatch.setattr(auth, "_limite_email", auth.parse_limite("3/hour"))
    for _ in range(3):
        auth.limiter.reset()
        assert login(client, usuario="otro@example.test", password=clave_mala()).status_code == 401
    auth.limiter.reset()
    assert login(client, usuario="otro@example.test", password=clave_mala()).status_code == 429


# ---------------------------------------------------------------- endpoints protegidos
@pytest.mark.parametrize("ruta", PROTEGIDOS)
def test_endpoint_protegido_sin_token_401(client, ruta):
    assert client.get(ruta).status_code == 401


@pytest.mark.parametrize("ruta", PROTEGIDOS)
def test_endpoint_protegido_con_token_200(client, token, ruta):
    assert client.get(ruta, headers=bearer(token)).status_code == 200


def test_token_invalido_401(client):
    assert client.get("/api/assets", headers=bearer("no.es.un.jwt")).status_code == 401


# ---------------------------------------------------------------- refresh y logout
def test_cookie_de_sesion_httponly_samesite_path(client, token, monkeypatch):
    r = login(client)
    sc = r.headers["set-cookie"].lower()
    assert sc.startswith("inventario_session=")
    assert "httponly" in sc and "samesite=strict" in sc and "path=/auth" in sc
    assert "secure" not in sc   # COOKIES_SEGURAS=0 en los tests (ambiente HTTP, MANUAL §6.4)
    monkeypatch.setattr(config, "COOKIES_SEGURAS", True)
    assert "secure" in login(client).headers["set-cookie"].lower()


def test_refresh_rota_y_detecta_reuso(client, token):
    r1 = client.post("/auth/refresh", headers=XRW)
    assert r1.status_code == 200 and r1.json()["access_token"]
    viejo = r1.request.headers.get("cookie", "")
    assert client.post("/auth/refresh", headers=XRW).status_code == 200   # la cookie nueva (rotada) sirve
    # reusar el refresh ya rotado corta todas las sesiones del usuario
    client.cookies.clear()
    r = client.post("/auth/refresh", headers={**XRW, "Cookie": viejo})
    assert r.status_code == 401
    assert client.get("/api/assets", headers=bearer(r1.json()["access_token"])).status_code == 401


def test_refresh_sin_header_o_sin_cookie_401(client, token):
    assert client.post("/auth/refresh").status_code == 401            # falta X-Requested-With
    client.cookies.clear()
    assert client.post("/auth/refresh", headers=XRW).status_code == 401


@pytest.mark.parametrize("ruta", ["/auth/logout", "/logout"])
def test_logout_invalida_access_y_refresh(client, token, ruta):
    assert client.get("/api/assets", headers=bearer(token)).status_code == 200
    assert client.post(ruta, headers=bearer(token)).status_code == 200
    assert client.get("/api/assets", headers=bearer(token)).status_code == 401
    assert client.post("/auth/refresh", headers=XRW).status_code == 401


# ---------------------------------------------------------------- permisos y usuarios
def _crear(client, token, username, rol, password=CLAVE_USUARIO):
    r = client.post("/auth/usuarios", headers=bearer(token),
                    json={"username": username, "password": password, "nombre": username, "rol": rol,
                          "email": username + "@example.test"})
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


def test_email_obligatorio_y_unico(client, token):
    base = {"password": CLAVE_USUARIO, "nombre": "x", "rol": "viewer"}
    assert client.post("/auth/usuarios", headers=bearer(token), json={**base, "username": "u1", "email": "no-es-mail"}).status_code == 400
    assert client.post("/auth/usuarios", headers=bearer(token), json={**base, "username": "u1", "email": "Rep@Example.test"}).status_code == 200
    assert client.post("/auth/usuarios", headers=bearer(token), json={**base, "username": "u2", "email": "rep@example.test"}).status_code == 400
    # login por email, sin distinguir mayusculas
    assert login(client, "REP@example.test", CLAVE_USUARIO).status_code == 200


def test_password_debil_rechazada(client, token):
    for i, debil in enumerate(("corta1A!", "password", "todominusculas123", "Aaaaaaaaaaaa1")):
        r = client.post("/auth/usuarios", headers=bearer(token),
                        json={"username": "d%d" % i, "password": debil, "nombre": "x", "rol": "viewer",
                              "email": "d%d@example.test" % i})
        assert r.status_code == 400, debil


def test_cambio_de_password_invalida_sesiones_viejas(client, token):
    r = client.post("/auth/cambiar-password", headers=bearer(token),
                    json={"password_actual": QA_ADMIN_PASS, "password_nuevo": CLAVE_NUEVA})
    assert r.status_code == 200
    assert client.get("/api/assets", headers=bearer(token)).status_code == 401
    assert login(client).status_code == 401
    nuevo = login(client, password=CLAVE_NUEVA).json()["access_token"]
    assert client.get("/api/assets", headers=bearer(nuevo)).status_code == 200


def test_cambiar_password_limpia_debe_cambiar(client):
    tok = login(client, SUPERADMIN, SUPERADMIN_PASS).json()["access_token"]
    client.post("/auth/cambiar-password", headers=bearer(tok),
                json={"password_actual": SUPERADMIN_PASS, "password_nuevo": CLAVE_NUEVA})
    assert login(client, SUPERADMIN, CLAVE_NUEVA).json()["user"]["debe_cambiar_password"] is False


def test_reset_de_admin_obliga_a_cambiar(client, token):
    _crear(client, token, "reseteado", "viewer")
    assert client.put("/auth/usuarios/reseteado", headers=bearer(token), json={"password": CLAVE_NUEVA}).status_code == 200
    assert login(client, "reseteado", CLAVE_NUEVA).json()["user"]["debe_cambiar_password"] is True


def test_usuario_desactivado_pierde_la_sesion(client, token):
    tv = _crear(client, token, "temporal", "viewer")
    assert client.get("/api/assets", headers=bearer(tv)).status_code == 200
    assert client.delete("/auth/usuarios/temporal", headers=bearer(token)).status_code == 200
    assert client.get("/api/assets", headers=bearer(tv)).status_code == 401


def test_superadmin_no_se_puede_degradar_ni_borrar(client, token):
    assert client.put("/auth/usuarios/" + SUPERADMIN, headers=bearer(token), json={"rol": "viewer"}).status_code == 400
    assert client.delete("/auth/usuarios/" + SUPERADMIN, headers=bearer(token)).status_code == 400


def test_placeholder_de_env_example_no_sirve_como_password():
    from auth import validar_password
    assert validar_password("cambiar" + clave_valida()) is not None


# ---------------------------------------------------------------- audit log
def test_audit_log_registra_eventos_con_contexto(client, token):
    import database
    client.post("/auth/logout", headers=bearer(token))
    login(client, password=clave_mala())
    db = database.SessionLocal()
    filas = db.query(database.AuditLog).all()
    db.close()
    acciones = {a.accion for a in filas}
    assert {"LOGIN_SUCCESS", "LOGOUT", "LOGIN_FAILED"} <= acciones
    ok = [a for a in filas if a.accion == "LOGIN_SUCCESS"][0]
    assert ok.user_id and ok.request_id.startswith("req_") and ok.user_agent


def test_audit_log_es_inmutable(client, token):
    import sqlalchemy
    import database
    with pytest.raises(sqlalchemy.exc.DatabaseError):
        with database.engine.begin() as con:
            con.execute(sqlalchemy.text("UPDATE audit_log SET accion = 'x'"))
    with pytest.raises(sqlalchemy.exc.DatabaseError):
        with database.engine.begin() as con:
            con.execute(sqlalchemy.text("DELETE FROM audit_log"))


# ---------------------------------------------------------------- logs
class _Captura(logging.Handler):
    """Formatea al emitir (con el contexto del request vivo), igual que el handler de stdout."""
    def __init__(self):
        import contexto
        super().__init__(logging.INFO)
        self.setFormatter(contexto.FormatoJSON())
        self.lineas = []

    def emit(self, record):
        self.lineas.append(self.format(record))


def test_logs_json_sin_secretos(client):
    h = _Captura()
    raiz = logging.getLogger()
    raiz.addHandler(h)
    try:
        tok = login(client, SUPERADMIN, SUPERADMIN_PASS).json()["access_token"]
        client.get("/api/assets", headers=bearer(tok))
    finally:
        raiz.removeHandler(h)
    lineas = h.lineas
    todo = "\n".join(lineas)
    assert SUPERADMIN_PASS not in todo and tok not in todo
    req = [json.loads(l) for l in lineas if '"http.request"' in l]
    assert req and all(r["request_id"].startswith("req_") and r["app_slug"] == "inventario" for r in req)
    assert any(r["user_id"] for r in req if r["path"] == "/api/assets")
