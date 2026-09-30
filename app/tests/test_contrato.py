# -*- coding: utf-8 -*-
"""Contrato con el Maestro: /health y /maestro/branding (README §9, Gate 2)."""
from conftest import MAESTRO_KEY


def test_health_sin_auth(client):
    r = client.get("/health")
    assert r.status_code == 200
    assert r.json() == {"status": "ok"}


def test_branding_sin_api_key_401(client):
    assert client.get("/maestro/branding").status_code == 401


def test_branding_api_key_invalida_401(client):
    r = client.get("/maestro/branding", headers={"X-Maestro-Api-Key": "cualquier-cosa"})
    assert r.status_code == 401


def test_branding_api_key_valida_200(client):
    r = client.get("/maestro/branding", headers={"X-Maestro-Api-Key": MAESTRO_KEY})
    assert r.status_code == 200
    d = r.json()
    assert d["company_name"]
    assert d["logo_url"].startswith("http")


def test_rutas_reservadas_no_caen_en_el_frontend(client):
    assert client.get("/api/no-existe").status_code in (401, 404)
    assert client.get("/maestro/otra").status_code == 404


def test_metrics_protegido_con_api_key(client):
    assert client.get("/metrics").status_code == 401
    assert client.get("/metrics", headers={"X-Maestro-Api-Key": "otra"}).status_code == 401
    r = client.get("/metrics", headers={"X-Maestro-Api-Key": MAESTRO_KEY})
    assert r.status_code == 200
    assert "http_requests_total" in r.text and "auth_login_attempts_total" in r.text and 'app_info{' in r.text


def test_cabeceras_de_seguridad(client):
    h = client.get("/health").headers
    assert h["x-content-type-options"] == "nosniff"
    assert h["x-frame-options"] == "DENY"
    assert "frame-ancestors 'none'" in h["content-security-policy"]
    assert client.get("/api/assets").headers.get("cache-control") == "no-store"


def test_request_id_se_propaga_o_se_genera(client):
    assert client.get("/health", headers={"X-Request-Id": "abc123-def456"}).headers["x-request-id"] == "abc123-def456"
    generado = client.get("/health", headers={"X-Request-Id": "<script>"}).headers["x-request-id"]
    assert generado.startswith("req_")


def test_branding_usa_app_url_detras_del_proxy(client, monkeypatch):
    import config
    monkeypatch.setattr(config, "APP_URL", "https://inventario-llyasoc.maestro.example")
    d = client.get("/maestro/branding", headers={"X-Maestro-Api-Key": MAESTRO_KEY}).json()
    assert d["logo_url"] == "https://inventario-llyasoc.maestro.example/logo.png"


def test_database_url_canonica_del_maestro():
    import config
    assert config._normalizar_db_url("postgres://u:p@db-x:5432/d") == "postgresql+psycopg://u:p@db-x:5432/d"
    assert config._normalizar_db_url("postgresql://u:p@h/d") == "postgresql+psycopg://u:p@h/d"
    assert config._normalizar_db_url("sqlite:///x.db") == "sqlite:///x.db"
