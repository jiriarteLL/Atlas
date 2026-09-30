# -*- coding: utf-8 -*-
"""Negocio: activos, sincronizacion de agentes, GLPI, proyectos, adjuntos y tendencias."""
import json

from conftest import SYNC_KEY, bearer

ACTIVO = {"tipo": "Notebook", "serial": "PF3ABCD", "marca": "Lenovo", "modelo": "T14", "usuario": "jperez"}


def test_alta_edicion_e_historial(client, token):
    r = client.post("/api/assets", headers=bearer(token), json=ACTIVO)
    assert r.status_code == 200
    aid = r.json()["id"]
    r = client.put("/api/assets/" + aid, headers=bearer(token), json={"usuario": "mgomez"})
    assert r.status_code == 200 and r.json()["usuario"] == "mgomez"
    h = client.get("/api/assets/%s/historial" % aid, headers=bearer(token)).json()
    assert any(x["campo"] == "usuario" and x["valor_new"] == "mgomez" and x["usuario"] == "qa-admin" for x in h)


def test_sync_rechaza_clave_invalida_o_faltante(client):
    assert client.post("/api/sync", json=ACTIVO).status_code == 401
    assert client.post("/api/sync", json=ACTIVO, headers={"X-Sync-Key": "otra"}).status_code == 401


def test_sync_crea_y_actualiza_por_serial(client, token):
    h = {"X-Sync-Key": SYNC_KEY}
    assert client.post("/api/sync", json=dict(ACTIVO, software=[{"nombre": "7-Zip", "version": "23"}]), headers=h).status_code == 200
    assert client.post("/api/sync", json=dict(ACTIVO, ram="16GB", software=[{"nombre": "7-Zip", "version": "24"}]), headers=h).status_code == 200
    activos = client.get("/api/assets", headers=bearer(token)).json()
    assert len(activos) == 1 and activos[0]["ram"] == "16GB"
    hist = client.get("/api/assets/%s/historial" % activos[0]["id"], headers=bearer(token)).json()
    assert any(x["campo"] == "software_actualizado" for x in hist)


def test_sync_glpi_upsert(client, token):
    inv = {"content": {"bios": {"ssn": "GLPI0001", "smanufacturer": "LENOVO", "mmodel": "T14"},
                       "hardware": {"name": "MAUDIT0099", "chassis_type": "Notebook", "memory": 16384},
                       "operatingsystem": {"full_name": "Windows 11 Pro", "arch": "64-bit"},
                       "antivirus": [{"name": "CrowdStrike Falcon", "enabled": True}]}}
    h = {"X-Sync-Key": SYNC_KEY, "Content-Type": "application/json"}
    for _ in range(2):
        r = client.post("/api/sync-glpi", content=json.dumps(inv), headers=h)
        assert r.status_code == 200, r.text
    res = client.get("/api/glpi/resumen", headers=bearer(token)).json()
    assert len(res) == 1 and res[0]["edr"] == "Activo"
    a = client.get("/api/assets", headers=bearer(token)).json()
    assert a[0]["ubicacion"] == "Mendoza" and a[0]["tipo"] == "Notebook"


def test_proyecto_con_tareas(client, token):
    r = client.post("/api/proyectos", headers=bearer(token), json={"nombre": "Migracion de servidores"})
    assert r.status_code == 200
    pid = r.json()["id"]
    assert r.json()["numero"].startswith("PRY-")
    r = client.post("/api/proyectos/%s/tareas" % pid, headers=bearer(token), json={"titulo": "Relevar", "estado": "Realizado"})
    assert r.json()["avance_efectivo"] == 100


def test_adjuntos_quedan_en_storage_y_no_escapan(client, token):
    aid = client.post("/api/assets", headers=bearer(token), json=ACTIVO).json()["id"]
    r = client.post("/api/assets/%s/adjuntos" % aid, headers=bearer(token),
                    files={"file": ("factura.pdf", b"%PDF-1.4 prueba", "application/pdf")})
    assert r.status_code == 200
    adj = r.json()["id"]
    r = client.get("/api/adjuntos/%s/descargar" % adj, headers=bearer(token))
    assert r.status_code == 200 and r.content.startswith(b"%PDF")
    # Un id con caracteres fuera de [A-Za-z0-9_-] no llega a tocar el disco.
    r = client.post("/api/assets/a..b/adjuntos", headers=bearer(token),
                    files={"file": ("x.pdf", b"x", "application/pdf")})
    assert r.status_code == 400
    r = client.post("/api/assets/%s/adjuntos" % aid, headers=bearer(token),
                    files={"file": ("x.exe", b"MZ", "application/octet-stream")})
    assert r.status_code == 400


def test_snapshot_de_tendencias(client, token):
    client.post("/api/assets", headers=bearer(token), json=ACTIVO)
    r = client.post("/api/tendencias/snapshot", headers=bearer(token))
    assert r.status_code == 200 and r.json()["metricas"] > 0
    assert "total_activos" in client.get("/api/tendencias/metricas", headers=bearer(token)).json()
