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
