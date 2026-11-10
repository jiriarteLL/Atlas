# -*- coding: utf-8 -*-
"""Negocio: activos, sincronizacion de agentes, GLPI, proyectos, adjuntos y tendencias."""
import json

from datetime import date, timedelta

import pytest

import garantias
import main
from conftest import SYNC_KEY, bearer, crear_usuario_db, login

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
    datos = dict(ACTIVO, ram="16GB", software=[{"nombre": "7-Zip", "version": "24"}])
    assert client.post("/api/sync", json=datos, headers=h).status_code == 200
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


def test_glpi_no_borra_los_campos_del_agente_y_usa_el_modelo_comercial(client, token):
    """En una corrida del agente llega primero /api/sync (con MAC, OU...) y despues GLPI, que no los trae."""
    red = {"mac": "AA:BB:CC:DD:EE:FF", "gateway": "192.168.100.4", "ip_publica": "190.210.78.1",
           "ou_ad": "OU=CABA,DC=LLASESORES,DC=CORP", "ultimo_reinicio": "2026-11-05 08:00", "ultimo_login": "2026-11-05 08:05"}
    h = {"X-Sync-Key": SYNC_KEY}
    assert client.post("/api/sync", json=dict(ACTIVO, serial="GLPI0002", **red), headers=h).status_code == 200
    inv = {"content": {"bios": {"ssn": "GLPI0002", "smanufacturer": "LENOVO", "mmodel": "21M80017AR",
                                "smodel": "ThinkPad E14 Gen 6"},
                       "hardware": {"name": "TEST", "chassis_type": "Notebook", "memory": 32768},
                       "operatingsystem": {"full_name": "Windows 11 Pro", "arch": "64-bit"}}}
    r = client.post("/api/sync-glpi", content=json.dumps(inv), headers=dict(h, **{"Content-Type": "application/json"}))
    assert r.status_code == 200, r.text
    a = client.get("/api/assets", headers=bearer(token)).json()[0]
    assert a["modelo"] == "ThinkPad E14 Gen 6"
    assert {k: a[k] for k in red} == red


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


# ---------------------------------------------------------------- validacion de activos (RF-03)
@pytest.mark.parametrize("falta", ["serial", "marca", "modelo"])
def test_alta_de_activo_incompleta_422(client, token, falta):
    datos = {k: v for k, v in ACTIVO.items() if k != falta}
    assert client.post("/api/assets", headers=bearer(token), json=datos).status_code == 422


# ---------------------------------------------------------------- garantias (RF-08)
HTML_LENOVO = ('<script>var d = {"UpmaWarranties":[{"Start":"2096-07-01","End":"2099-06-30",'
               '"Name":"3 YR Onsite","DeliveryType":"on_site"}],"x":1}</script>')


def _activo(client, token, **extra):
    return client.post("/api/assets", headers=bearer(token), json=dict(ACTIVO, **extra)).json()["id"]


def test_garantia_lenovo_ok(client, token, monkeypatch):
    monkeypatch.setattr(garantias, "_descargar", lambda serie: HTML_LENOVO)
    aid = _activo(client, token)
    r = client.post("/api/assets/%s/garantia" % aid, headers=bearer(token))
    assert r.status_code == 200, r.text
    j = r.json()
    assert (j["garantia"], j["estado"], j["anterior"]) == ("2099-06-30", "Vigente", "") and j["cobertura"] == "3 YR Onsite"
    ficha = client.get("/api/assets/%s/ficha" % aid, headers=bearer(token)).json()
    assert ficha["garantia"] == "2099-06-30"


def test_garantia_marca_no_lenovo_400(client, token, monkeypatch):
    monkeypatch.setattr(garantias, "_descargar", lambda serie: pytest.fail("no deberia consultar el portal"))
    aid = _activo(client, token, marca="HP", serial="HPX12345")
    r = client.post("/api/assets/%s/garantia" % aid, headers=bearer(token))
    assert r.status_code == 400 and "Lenovo" in r.json()["detail"]


def test_garantia_error_del_portal_422(client, token, monkeypatch):
    monkeypatch.setattr(garantias, "_descargar", lambda serie: "<html>sin datos</html>")
    aid = _activo(client, token)
    r = client.post("/api/assets/%s/garantia" % aid, headers=bearer(token))
    assert r.status_code == 422 and "Lenovo" in r.json()["detail"]


def test_garantia_serial_invalido_no_consulta_el_portal():
    assert garantias.consultar_lenovo("../../etc")[1] == "Serie vacía o inválida"


def test_garantia_requiere_permiso(client, token):
    crear_usuario_db("lector-g", "lector-g@example.test", "Aa1-lectorG-9x", "viewer")
    tv = login(client, "lector-g", "Aa1-lectorG-9x").json()["access_token"]
    aid = _activo(client, token)
    assert client.post("/api/assets/%s/garantia" % aid, headers=bearer(tv)).status_code == 403


def test_vencimientos_filtra_y_ordena(client, token):
    hoy = date.today()
    _activo(client, token, serial="SER-V1", garantia=str(hoy + timedelta(days=60)))
    _activo(client, token, serial="SER-V2", garantia=str(hoy + timedelta(days=10)))
    _activo(client, token, serial="SER-V3", garantia=str(hoy + timedelta(days=200)))   # fuera de los 90 dias
    _activo(client, token, serial="SER-V4", garantia=str(hoy - timedelta(days=5)))     # ya vencida
    _activo(client, token, serial="SER-V5", garantia="sin fecha")                      # formato invalido
    r = client.get("/api/garantias/vencimientos", headers=bearer(token)).json()
    assert [x["serial"] for x in r] == ["SER-V2", "SER-V1"]
    assert [x["dias"] for x in r] == [10, 60]


# ---------------------------------------------------------------- adjuntos (RF-07)
def test_adjunto_de_mas_de_10_mb_400(client, token):
    aid = _activo(client, token)
    grande = b"0" * (main.MAX_MB * 1024 * 1024 + 1)
    r = client.post("/api/assets/%s/adjuntos" % aid, headers=bearer(token),
                    files={"file": ("grande.pdf", grande, "application/pdf")})
    assert r.status_code == 400 and "10 MB" in r.json()["detail"]


# ---------------------------------------------------------------- proyectos (RF-09 / RF-10)
def test_proyecto_con_responsables_y_activos(client, token):
    a1, a2 = _activo(client, token, serial="SER-P1"), _activo(client, token, serial="SER-P2")
    r = client.post("/api/proyectos", headers=bearer(token),
                    json={"nombre": "Recambio de notebooks", "responsables": ["qa-admin", "otro"], "activos": [a1, a2]})
    assert r.status_code == 200
    d = r.json()
    assert sorted(d["responsables"]) == ["otro", "qa-admin"]
    assert sorted(x["serial"] for x in d["activos"]) == ["SER-P1", "SER-P2"]
    listado = client.get("/api/proyectos", headers=bearer(token)).json()
    assert len(listado[0]["activos"]) == 2


def test_proyecto_finalizado_notifica_sin_romper(client, token, monkeypatch):
    enviados = []
    monkeypatch.setattr(main, "notificar_proyecto_finalizado",
                        lambda proy, quien, dest: enviados.append((proy["nombre"], sorted(set(dest)))))
    pid = client.post("/api/proyectos", headers=bearer(token),
                      json={"nombre": "Migracion", "responsables": ["jperez"]}).json()["id"]
    r = client.put("/api/proyectos/" + pid, headers=bearer(token),
                   json={"nombre": "Migracion", "estado": "Finalizado", "responsables": ["jperez"]})
    assert r.status_code == 200
    assert enviados == [("Migracion", ["jperez", "qa-admin"])]
    # volver a guardarlo finalizado no reenvia
    client.put("/api/proyectos/" + pid, headers=bearer(token),
               json={"nombre": "Migracion", "estado": "Finalizado", "responsables": ["jperez"]})
    assert len(enviados) == 1


def test_mail_sin_smtp_no_falla():
    import mailer
    assert mailer.enviar(["alguien"], "asunto", "<p>x</p>") is False   # SMTP_HOST vacio en los tests


def test_mail_escapa_html_de_usuario(monkeypatch):
    import mailer
    capturado = {}
    monkeypatch.setattr(mailer, "enviar", lambda dest, asunto, cuerpo, txt="": capturado.update(cuerpo=cuerpo))
    mailer.notificar_proyecto_finalizado({"nombre": "<a href=x>Click</a>", "numero": "PRY-1", "descripcion": "<script>x</script>",
                                          "tareas_hechas": 0, "tareas_total": 0}, "<b>quien</b>", ["a"])
    assert "<script>" not in capturado["cuerpo"] and "&lt;script&gt;" in capturado["cuerpo"]
    assert "<a href=x>" not in capturado["cuerpo"]


@pytest.mark.parametrize("link,esperado", [("https://llyasoc.sharepoint.com/x", 200), ("http://mesa/ticket/1", 200), ("", 200),
                                           ("javascript:alert(1)", 422), ("data:text/html,<b>x</b>", 422), ("ftp://x", 422)])
def test_links_de_proyecto_solo_http(client, token, link, esperado):
    r = client.post("/api/proyectos", headers=bearer(token), json={"nombre": "Con link", "link_ticket": link})
    assert r.status_code == esperado


# ---------------------------------------------------------------- tendencias (RF-12)
@pytest.mark.parametrize("rol", ["viewer", "editor"])
def test_snapshot_solo_admin(client, token, rol):
    crear_usuario_db("u-" + rol, rol + "@example.test", "Aa1-" + rol + "-9x", rol)
    tk = login(client, "u-" + rol, "Aa1-" + rol + "-9x").json()["access_token"]
    assert client.post("/api/tendencias/snapshot", headers=bearer(tk)).status_code == 403
