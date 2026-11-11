# -*- coding: utf-8 -*-
"""Notebooks y PC: salud y seguridad (campo "salud" del sync, fin de soporte de Windows, resumen)."""
from datetime import date, datetime, timedelta

import database
from ciclo_vida import build_de, soporte, tipo_edicion
from conftest import SYNC_KEY, bearer, clave_valida, crear_usuario_db, login
from salud import normalizar

HOY = date(2026, 11, 6)

PC = {"nombre": "NB-TEST-01", "tipo": "Notebook", "marca": "Lenovo", "modelo": "ThinkPad E14 Gen 6",
      "serial": "TEST-SALUD-01", "usuario": "usuario.prueba", "ubicacion": "CABA",
      "so": "Microsoft Windows 11 Pro", "so_version": "10.0.26200", "cifrado": "Cifrado"}

SALUD = {"so": {"edicion": "Professional", "display_version": "25H2", "build": 26200, "ubr": 7019},
         "antivirus": [{"nombre": "Windows Defender", "activo": False, "actualizado": True},
                      {"nombre": "CrowdStrike Falcon Sensor", "activo": True, "actualizado": True}],
         "parches": {"ultimo": date.today().isoformat(), "cantidad_90d": 4},
         "discos": [{"nombre": "SSD TEST", "tipo": "SSD", "salud": "Healthy", "desgaste": 5, "temperatura": 38,
                     "errores_lectura": 0, "tamano_gb": 512}],
         "bateria": {"salud": 92, "ciclos": 120, "diseno_mwh": 57000, "actual_mwh": 52440}}


def _sync(client, **extra):
    r = client.post("/api/sync", json=dict(PC, **extra), headers={"X-Sync-Key": SYNC_KEY})
    assert r.status_code == 200, r.text


def _fila(client, token, serial="TEST-SALUD-01"):
    return next(f for f in client.get("/api/salud", headers=bearer(token)).json() if f["serial"] == serial)


# ---------------------------------------------------------------- ciclo de vida
def test_fin_de_soporte_por_build_y_edicion():
    assert soporte(26100, "Professional", HOY)["estado"] == "sin_soporte"            # 24H2 Pro: 13/10/2026
    assert soporte(26100, "Enterprise", HOY)["estado"] == "vigente"                  # 24H2 Ent: 12/10/2027
    s = soporte(22631, "Enterprise", HOY)                                            # 23H2 Ent: 10/11/2026
    assert s["estado"] == "vence_pronto" and s["fin_soporte"] == date(2026, 11, 10) and s["dias"] == 4
    assert soporte(22631, "Microsoft Windows 11 Pro", HOY)["estado"] == "sin_soporte"
    assert soporte(19045, "Professional", HOY)["fin_soporte"] == date(2025, 10, 14)
    assert soporte(26200, "Professional", HOY)["estado"] == "vigente"
    assert soporte(26300, "Professional", HOY)["version"] == "26H2"
    assert soporte(99999, "Professional", HOY)["estado"] == "desconocido"
    assert soporte(None, "", HOY)["estado"] == "desconocido"
    assert soporte(17763, "Microsoft Windows Server 2019 Standard", HOY)["version"] == "2019"
    assert soporte(19044, "EnterpriseS", HOY)["estado"] == "desconocido"             # LTSC no verificado


def test_edicion_y_build():
    assert tipo_edicion("Microsoft Windows 11 Enterprise") == "empresa"
    assert tipo_edicion("Education") == "empresa"
    assert tipo_edicion("Core") == "pro"
    assert tipo_edicion("ServerStandard") == "servidor"
    assert tipo_edicion("IoTEnterpriseS") == "ltsc"
    assert build_de("10.0.22631") == 22631 and build_de("22631") == 22631 and build_de("") is None


# ---------------------------------------------------------------- normalizacion
def test_estados_de_antivirus_disco_y_bateria():
    n = normalizar(SALUD)
    assert n["av_estado"] == "ok" and n["disco_estado"] == "ok" and n["bateria_salud"] == 92 and n["so_build"] == 26200
    n = normalizar({"antivirus": [{"nombre": "CrowdStrike Falcon", "activo": False, "actualizado": True}]})
    assert n["av_estado"] == "desactivado"
    n = normalizar({"antivirus": [{"nombre": "CrowdStrike Falcon", "activo": "true", "actualizado": "false"}]})
    assert n["av_estado"] == "desactualizado"
    # solo Defender (aunque este activo y al dia): falta el antivirus de la empresa
    n = normalizar({"antivirus": [{"nombre": "Windows Defender", "activo": True, "actualizado": True}]})
    assert n["av_estado"] == "falta_corporativo"
    assert normalizar({})["av_estado"] == "" and normalizar({})["disco_estado"] == ""
    assert normalizar({"discos": [{"salud": "Warning"}]})["disco_estado"] == "riesgo"
    assert normalizar({"discos": [{"salud": "Healthy", "desgaste": 85}]})["disco_estado"] == "riesgo"
    assert normalizar({"discos": [{"salud": "OK", "errores_lectura": 3}]})["disco_estado"] == "riesgo"
    # sin % de salud: se calcula con la capacidad actual / de diseno
    assert normalizar({"bateria": {"diseno_mwh": 50000, "actual_mwh": 25000}})["bateria_salud"] == 50
    assert normalizar({"bateria": None})["bateria_salud"] is None
    # basura: no rompe
    n = normalizar({"so": "x", "antivirus": "x", "discos": [1, "a", {"desgaste": "mucho"}], "parches": {"ultimo": "ayer"}})
    assert n["ultimo_parche"] is None and n["disco_estado"] == "ok"


# ---------------------------------------------------------------- sync + endpoints
def test_sync_con_salud_y_vista(client, token):
    _sync(client, salud=SALUD)
    f = _fila(client, token)
    assert f["so_display"] == "25H2" and f["soporte_estado"] == "vigente" and f["av_estado"] == "ok"
    assert f["bateria_salud"] == 92 and f["discos"][0]["tipo"] == "SSD" and f["con_datos"] and not f["sin_cifrar"]
    # el sync siguiente actualiza la misma fila (upsert) y no toca el resto del activo
    _sync(client, salud=dict(SALUD, bateria={"salud": 41, "ciclos": 900}, discos=[{"salud": "Warning"}]))
    f = _fila(client, token)
    assert f["bateria_salud"] == 41 and f["bateria_baja"] and f["disco_estado"] == "riesgo"
    db = database.SessionLocal()
    assert db.query(database.AssetSalud).count() == 1
    db.close()


def test_sync_sin_salud_igual_muestra_windows_y_bitlocker(client, token):
    _sync(client, so="Microsoft Windows 10 Pro", so_version="10.0.19045", cifrado="Sin cifrar")
    f = _fila(client, token)
    assert not f["con_datos"] and f["soporte_estado"] == "sin_soporte" and f["so_display"] == "22H2" and f["sin_cifrar"]
    r = client.get("/api/salud/resumen", headers=bearer(token)).json()
    assert r["total"] == 1 and r["sin_soporte"] == 1 and r["sin_cifrar"] == 1 and r["sin_datos"] == 1


def test_salud_gigante_se_ignora_pero_el_sync_sigue(client, token):
    _sync(client, salud={"discos": [{"nombre": "x" * 30000}]})
    f = _fila(client, token)
    assert not f["con_datos"] and f["nombre"] == "NB-TEST-01"


def test_resumen_cuenta_cada_alerta(client, token):
    viejo = (date.today() - timedelta(days=45)).isoformat()
    _sync(client, salud=dict(SALUD, parches={"ultimo": viejo}, antivirus=[{"nombre": "X", "activo": False}]),
          cifrado="Cifrado (proteccion off)")
    _sync(client, serial="TEST-SALUD-02", nombre="PC-TEST-02", tipo="CPU", salud=dict(SALUD, bateria=None))
    db = database.SessionLocal()   # un equipo que no reporta hace 20 dias
    a = db.query(database.Asset).filter(database.Asset.serial == "TEST-SALUD-02").first()
    a.updated = datetime.utcnow() - timedelta(days=20)
    db.commit()
    db.close()
    r = client.get("/api/salud/resumen", headers=bearer(token)).json()
    assert r["total"] == 2 and r["sin_cifrar"] == 1 and r["av_problema"] == 1 and r["sin_parches_30d"] == 1
    assert r["sin_reportar_15d"] == 1 and r["bateria_baja"] == 0 and r["sin_datos"] == 0
    assert _fila(client, token, "TEST-SALUD-02")["bateria_salud"] is None


def test_solo_notebooks_pc_y_servidores_con_datos(client, token):
    _sync(client, salud=SALUD)
    _sync(client, serial="TEST-SRV-01", nombre="SRV-TEST", tipo="Servidor")
    _sync(client, serial="TEST-SRV-02", nombre="SRV-TEST-2", tipo="Servidor", so="Microsoft Windows Server 2019 Standard",
          so_version="10.0.17763", salud={"so": {"edicion": "ServerStandard", "build": 17763}})
    nombres = {f["nombre"] for f in client.get("/api/salud", headers=bearer(token)).json()}
    assert nombres == {"NB-TEST-01"}   # los servidores van en Servidores y VM


def test_ficha_y_borrado(client, token):
    _sync(client, salud=SALUD)
    aid = _fila(client, token)["id"]
    assert client.get("/api/salud/" + aid, headers=bearer(token)).json()["av_estado"] == "ok"
    assert client.delete("/api/assets/" + aid, headers=bearer(token)).status_code == 200
    db = database.SessionLocal()
    assert db.query(database.AssetSalud).count() == 0
    db.close()


def test_requiere_sesion_y_lo_ve_un_viewer(client, token):
    assert client.get("/api/salud").status_code == 401
    pw = clave_valida()
    crear_usuario_db("qa-viewer", "qa-viewer@example.test", pw, "viewer")
    tok = login(client, "qa-viewer", pw).json()["access_token"]
    assert client.get("/api/salud/resumen", headers=bearer(tok)).status_code == 200
