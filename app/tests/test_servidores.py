# -*- coding: utf-8 -*-
"""Fase D: bloque "servidor" del agente, volumenes, alertas, permisos y conectores (vCenter, Azure, Redfish) con mocks.
Ninguna prueba toca la red: los conectores reciben un `http` falso."""
import os
from datetime import datetime, timedelta

import pytest
from alembic import command
from alembic.config import Config

import config
import conectores
import database
from auth import User, UserModulo, plantilla
from conftest import SYNC_KEY, bearer, clave_valida, crear_usuario_db, login

INI = os.path.join(os.path.dirname(__file__), "..", "backend", "alembic.ini")
CLAVE = clave_valida()
SERIE_VM = "VMware-42 1d 2a 3b 4c 5d 6e 7f-80 91 a2 b3 c4 d5 e6 f7"
UUID_VM = "421d2a3b-4c5d-6e7f-8091-a2b3c4d5e6f7"
SRV = {"nombre": "SRV-TEST-01", "tipo": "Servidor", "marca": "VMware, Inc.", "modelo": "VMware Virtual Platform",
       "serial": SERIE_VM, "so": "Microsoft Windows Server 2019 Standard", "so_version": "10.0.17763", "ubicacion": "CABA"}
SERVIDOR = {"roles": [{"nombre": "Servidor web (IIS)", "servicios": ["Servidor web"]}], "uptime_dias": 12.5,
            "reinicio_pendiente": True, "reinicio_motivos": ["Windows Update"],
            "servicios_detenidos": [{"nombre": "MSSQL$TANGO", "display": "SQL Server (TANGO)"}],
            "sql": [{"instancia": "TANGO", "estado": "Stopped"}],
            "iis": [{"nombre": "Default Web Site", "estado": "Started", "bindings": ["http *:80:"]}],
            "controlador_dominio": False, "hyperv_vms": None}
SALUD = {"so": {"edicion": "Standard", "build": 17763},
         "volumenes": [{"letra": "C:", "etiqueta": "", "fs": "NTFS", "tamano_gb": 100, "libre_gb": 5, "libre_pct": 5}]}


def _sync(client, **extra):
    r = client.post("/api/sync", json=dict(SRV, **extra), headers={"X-Sync-Key": SYNC_KEY})
    assert r.status_code == 200, r.text


def _lista(client, token):
    r = client.get("/api/servidores", headers=bearer(token))
    assert r.status_code == 200, r.text
    return {f["nombre"]: f for f in r.json()}


# ---------------------------------------------------------------- agente
def test_bloque_servidor_y_alertas(client, token):
    _sync(client, servidor=SERVIDOR, salud=SALUD)
    f = _lista(client, token)["SRV-TEST-01"]
    assert f["roles"][0]["nombre"] == "Servidor web (IIS)" and f["iis"][0]["bindings"] == ["http *:80:"]
    assert f["disco_min_libre_pct"] == 5 and f["reinicio_pendiente"] and f["origenes"] == ["agente"]
    assert set(f["alertas"]) == {"disco_lleno", "servicios_detenidos"}   # reinicio recien visto: todavia no alerta
    assert f["soporte_producto"] == "Windows Server" and f["soporte_estado"] == "vigente"
    # reinicio pendiente hace mas de 7 dias y uptime alto
    db = database.SessionLocal()
    s = db.query(database.AssetServidor).first()
    s.reinicio_desde = datetime.utcnow() - timedelta(days=9)
    db.commit()
    db.close()
    _sync(client, servidor=dict(SERVIDOR, uptime_dias=90), salud=SALUD)
    f = _lista(client, token)["SRV-TEST-01"]
    assert {"reinicio_pendiente", "uptime_alto"} <= set(f["alertas"]) and f["reinicio_dias"] >= 9
    # se reinicio: la marca se limpia
    _sync(client, servidor=dict(SERVIDOR, reinicio_pendiente=False, reinicio_motivos=[], uptime_dias=0.1), salud=SALUD)
    f = _lista(client, token)["SRV-TEST-01"]
    assert not f["reinicio_pendiente"] and f["reinicio_dias"] is None
    r = client.get("/api/servidores/resumen", headers=bearer(token)).json()
    assert r["total"] == 1 and r["disco_lleno"] == 1 and r["servicios_detenidos"] == 1


def test_server_2012_r2_sin_soporte(client, token):
    _sync(client, so="Microsoft Windows Server 2012 R2 Standard", so_version="6.3.9600", salud={"so": {"edicion": "Standard", "build": 9600}})
    assert "sin_soporte" in _lista(client, token)["SRV-TEST-01"]["alertas"]


def test_basura_no_rompe_el_sync(client, token):
    _sync(client, servidor={"roles": "x", "uptime_dias": "mucho", "iis": [1, {"nombre": None}], "hyperv_vms": [{"nombre": "VM1", "ram_gb": "a"}]},
          salud={"volumenes": [{"letra": "C:", "tamano_gb": 0}, "x", {"tamano_gb": "a"}]})
    f = _lista(client, token)["SRV-TEST-01"]
    assert f["roles"] == [] and f["volumenes"] == [] and f["hyperv_vms"] == [{"nombre": "VM1", "estado": "", "cpu": None, "ram_gb": None}]
    _sync(client, servidor={"roles": [{"nombre": "x" * 100}] * 2000})   # gigante: se ignora, el sync sigue
    assert client.get("/api/assets", headers=bearer(token)).status_code == 200


def test_permisos_y_ficha(client, token):
    _sync(client, servidor=SERVIDOR, salud=SALUD)
    aid = _lista(client, token)["SRV-TEST-01"]["id"]
    assert client.get("/api/servidores/" + aid, headers=bearer(token)).json()["sql"][0]["instancia"] == "TANGO"
    crear_usuario_db("srv-viewer", "srv-viewer@example.test", CLAVE, "viewer")
    tok = login(client, "srv-viewer", CLAVE).json()["access_token"]
    assert client.get("/api/servidores", headers=bearer(tok)).status_code == 200
    assert client.post("/api/conectores/actualizar", headers=bearer(tok)).status_code == 403
    r = client.put("/auth/usuarios/srv-viewer/permisos", headers=bearer(token), json={"modulos": {"impresoras": "ver"}})
    assert r.status_code == 200, r.text
    assert client.get("/api/servidores", headers=bearer(tok)).status_code == 403
    assert client.get("/api/conectores", headers=bearer(tok)).status_code == 403


def test_la_migracion_suma_servidores(client):
    for nombre, rol in (("s-viewer", "viewer"), ("s-editor", "editor"), ("s-admin", "admin")):
        crear_usuario_db(nombre, nombre + "@example.test", CLAVE, rol)
    cfg = Config(INI)
    with database.engine.begin() as con:   # base como antes de la fase D
        cfg.attributes["connection"] = con
        command.downgrade(cfg, "0010")
    database.init_db()
    db = database.SessionLocal()
    try:
        for nombre, rol in (("s-viewer", "viewer"), ("s-editor", "editor"), ("s-admin", "admin")):
            u = db.query(User).filter(User.username == nombre).first()
            m = {f.modulo: f.nivel for f in db.query(UserModulo).filter(UserModulo.user_id == u.id)}
            assert m == plantilla(rol), nombre
            assert m["servidores"] == "ver"
    finally:
        db.close()


# ---------------------------------------------------------------- conectores
@pytest.fixture
def secreto(tmp_path):
    p = tmp_path / "clave.txt"
    p.write_text("clave-de-prueba\n", encoding="utf-8")
    return str(p)


@pytest.fixture
def cfg_vcenter(monkeypatch, secreto):
    monkeypatch.setattr(config, "VCENTER_URL", "https://vcenter.test")
    monkeypatch.setattr(config, "VCENTER_USUARIO", "atlas-lectura@vsphere.local")
    monkeypatch.setattr(config, "VCENTER_CLAVE_ARCHIVO", secreto)


def _http_vcenter(metodo, url, headers=None, cuerpo=None, verificar=True):
    ruta = url.replace("https://vcenter.test", "")
    if ruta == "/api/session":
        return (201, "token-1") if metodo == "POST" else (204, None)
    assert headers.get("vmware-api-session-id") == "token-1"
    tabla = {
        "/api/vcenter/host": [{"host": "host-10", "name": "esxi01.test", "connection_state": "CONNECTED", "power_state": "POWERED_ON"}],
        "/api/vcenter/cluster": [{"cluster": "domain-c1", "name": "Cluster CABA"}],
        "/api/vcenter/host?clusters=domain-c1": [{"host": "host-10"}],
        "/api/vcenter/vm?hosts=host-10": [{"vm": "vm-1"}, {"vm": "vm-2"}],
        "/api/vcenter/vm": [{"vm": "vm-1", "name": "SRV-TEST-01"}, {"vm": "vm-2", "name": "linux01"}],
        "/api/vcenter/vm/vm-1": {"name": "SRV-TEST-01", "power_state": "POWERED_ON", "guest_OS": "WINDOWS_9_SERVER_64",
                                 "cpu": {"count": 4}, "memory": {"size_MiB": 16384},
                                 "disks": {"2000": {"label": "Hard disk 1", "capacity": 107374182400}},
                                 "identity": {"bios_uuid": UUID_VM}},
        "/api/vcenter/vm/vm-2": {"name": "linux01", "power_state": "POWERED_ON", "guest_OS": "UBUNTU_64",
                                 "cpu": {"count": 2}, "memory": {"size_MiB": 4096}, "disks": {},
                                 "identity": {"bios_uuid": "564d0000-1111-2222-3333-444455556666"}},
        "/api/vcenter/vm/vm-2/guest/identity": {"ip_address": "10.9.8.7", "host_name": "linux01.test",
                                                "full_name": {"default_message": "Ubuntu Linux (64-bit)"}},
    }
    if ruta == "/api/vcenter/vm/vm-1/guest/identity":
        raise conectores.ErrorConector("HTTP 503")
    return 200, tabla[ruta]


def test_conectores_inertes_sin_config(client, token):
    assert not conectores.hay_alguno_configurado()
    assert conectores.correr("vcenter") is None
    estado = {c["conector"]: c for c in client.get("/api/conectores", headers=bearer(token)).json()}
    assert not estado["vcenter"]["configurado"] and "VCENTER_URL" in estado["vcenter"]["falta"]
    assert "REDFISH_HOSTS" in estado["redfish"]["falta"] and "AZURE_SUSCRIPCIONES" in estado["azure"]["falta"]
    assert client.post("/api/conectores/actualizar", headers=bearer(token)).json()["status"] == "sin_conectores"


def test_vcenter_cruza_por_uuid_no_pisa_y_unifica(client, token, cfg_vcenter):
    _sync(client, servidor=SERVIDOR, salud=SALUD, ram="32GB")
    res = conectores.correr("vcenter", leer=lambda: conectores.leer_vcenter(_http_vcenter))
    assert res["ok"], res
    f = _lista(client, token)
    srv, linux, host = f["SRV-TEST-01"], f["linux01"], f["esxi01.test"]
    assert srv["origenes"] == ["agente", "vcenter"] and srv["externos"]["vcenter"]["host"] == "esxi01.test"
    assert srv["externos"]["vcenter"]["cluster"] == "Cluster CABA"
    a = next(x for x in client.get("/api/assets", headers=bearer(token)).json() if x["nombre"] == "SRV-TEST-01")
    assert a["ram"] == "32GB"                                   # no pisa lo que manda el agente
    assert linux["tipo"] == "VM" and linux["origenes"] == ["vcenter"] and linux["so"] == "Ubuntu Linux (64-bit)"
    assert linux["serial"] == "VMware-56 4d 00 00 11 11 22 22-33 33 44 44 55 55 66 66" and linux["ip"] == "10.9.8.7"
    assert host["tipo"] == "Servidor" and host["externos"]["vcenter"]["es_host"]
    # segunda corrida: no duplica
    conectores.correr("vcenter", leer=lambda: conectores.leer_vcenter(_http_vcenter))
    assert len(_lista(client, token)) == 3
    # aparece el agente en la VM linux (misma serie): se unifica en el mismo activo
    r = client.post("/api/sync", json={"nombre": "linux01", "tipo": "Servidor", "serial": linux["serial"], "so": "Ubuntu 24.04"},
                    headers={"X-Sync-Key": SYNC_KEY})
    assert r.status_code == 200
    assert len(_lista(client, token)) == 3


def test_vcenter_error_queda_en_el_estado_sin_clave(client, token, cfg_vcenter):
    def falla(*a, **k):
        raise conectores.ErrorConector("HTTP 401 en /api/session")
    res = conectores.correr("vcenter", leer=lambda: conectores.leer_vcenter(falla))
    assert not res["ok"] and "401" in res["mensaje"] and "clave-de-prueba" not in res["mensaje"]
    est = {c["conector"]: c for c in client.get("/api/conectores", headers=bearer(token)).json()}["vcenter"]
    assert est["configurado"] and est["ok"] is False and not est["corriendo"]


def test_lease_un_solo_proceso(client, cfg_vcenter):
    db = database.SessionLocal()
    try:
        assert conectores._tomar_lease(db, "vcenter", "proceso-a", datetime.utcnow())
        assert not conectores._tomar_lease(db, "vcenter", "proceso-b", datetime.utcnow())
        assert conectores.correr("vcenter", leer=lambda: {"vms": [], "hosts": []}) is None   # el otro lo tiene
        assert conectores._tomar_lease(db, "vcenter", "proceso-b", datetime.utcnow() + timedelta(minutes=31))
    finally:
        db.close()


def test_azure_cruza_por_nombre(client, token, monkeypatch, secreto):
    monkeypatch.setattr(config, "AZURE_SUSCRIPCIONES", ["sub-1"])
    monkeypatch.setattr(config, "AZURE_TENANT_ID", "tenant-1")
    monkeypatch.setattr(config, "AZURE_CLIENT_ID", "app-1")
    monkeypatch.setattr(config, "AZURE_CLIENT_SECRET_ARCHIVO", secreto)
    _sync(client, nombre="LLAZSVRAPP01", serial="AZ-SERIE-1", marca="Microsoft Corporation", modelo="Virtual Machine")
    vm_id = "/subscriptions/sub-1/resourceGroups/RG-LLYA/providers/Microsoft.Compute/virtualMachines/llazsvrapp01"
    nic_id = "/subscriptions/sub-1/resourceGroups/RG-LLYA/providers/Microsoft.Network/networkInterfaces/nic1"

    def http(metodo, url, headers=None, cuerpo=None, verificar=True):
        if "login.microsoftonline.com/tenant-1" in url:
            assert b"client_secret=clave-de-prueba" in cuerpo
            return 200, {"access_token": "tok"}
        assert headers["Authorization"] == "Bearer tok"
        if "statusOnly=true" in url:
            return 200, {"value": [{"id": vm_id, "properties": {"instanceView": {"statuses": [
                {"code": "ProvisioningState/succeeded"}, {"code": "PowerState/running"}]}}}]}
        if "virtualMachines?" in url:
            return 200, {"value": [
                {"id": vm_id, "name": "llazsvrapp01", "location": "brazilsouth",
                 "properties": {"hardwareProfile": {"vmSize": "Standard_D4s_v5"}, "osProfile": {"computerName": "LLAZSVRAPP01"},
                                "storageProfile": {"osDisk": {"name": "os", "osType": "Windows", "diskSizeGB": 128}, "dataDisks": [],
                                                   "imageReference": {"publisher": "MicrosoftWindowsServer", "offer": "WindowsServer", "sku": "2022-datacenter"}},
                                "networkProfile": {"networkInterfaces": [{"id": nic_id}]}}},
                {"id": vm_id.replace("llazsvrapp01", "llaznueva"), "name": "llaznueva", "location": "brazilsouth",
                 "properties": {"hardwareProfile": {"vmSize": "Standard_B2s"}, "osProfile": {"computerName": "LLAZNUEVA"},
                                "storageProfile": {"osDisk": {"osType": "Linux", "diskSizeGB": 30}}, "networkProfile": {}}}]}
        if nic_id in url:
            return 200, {"properties": {"ipConfigurations": [{"properties": {"privateIPAddress": "10.20.0.10"}}]}}
        raise AssertionError(url)

    res = conectores.correr("azure", leer=lambda: conectores.leer_azure(http))
    assert res["ok"], res
    f = _lista(client, token)
    app = f["LLAZSVRAPP01"]["externos"]["azure"]
    assert app["tamano"] == "Standard_D4s_v5" and app["grupo_recursos"] == "RG-LLYA" and app["estado"] == "running"
    assert app["ip"] == "10.20.0.10" and app["region"] == "brazilsouth"
    assert f["LLAZNUEVA"]["tipo"] == "VM" and f["LLAZNUEVA"]["origenes"] == ["azure"]


# Redfish: el mismo conector lee iDRAC (Dell) e iLO (HPE); el System se descubre en /redfish/v1/Systems
RF_DELL = {
    "/redfish/v1/Systems": {"Members": [{"@odata.id": "/redfish/v1/Systems/System.Embedded.1"}]},
    "/redfish/v1/Systems/System.Embedded.1": {
        "Manufacturer": "Dell Inc.", "Model": "PowerEdge R740", "SerialNumber": "CN123", "SKU": "ABC1234",
        "HostName": "llrossvr03", "PowerState": "On", "BiosVersion": "2.19.1", "Status": {"Health": "OK", "HealthRollup": "Warning"},
        "MemorySummary": {"TotalSystemMemoryGiB": 192}, "ProcessorSummary": {"Count": 2, "Model": "Xeon Silver 4214"},
        "Oem": {"Dell": {"DellSystem": {"WarrantyEndDate": "2027-01-31"}}}},
    "/redfish/v1/Managers": {"Members": [{"@odata.id": "/redfish/v1/Managers/iDRAC.Embedded.1"}]},
    "/redfish/v1/Managers/iDRAC.Embedded.1": {"FirmwareVersion": "6.10.30.00"},
    "/redfish/v1/Chassis": {"Members": [{"@odata.id": "/redfish/v1/Chassis/System.Embedded.1"}]},
    "/redfish/v1/Chassis/System.Embedded.1/Power": {"PowerSupplies": [
        {"Name": "PS1", "Status": {"Health": "OK", "State": "Enabled"}}, {"Name": "PS2", "Status": {"Health": "Critical", "State": "Enabled"}}]},
    "/redfish/v1/Chassis/System.Embedded.1/Thermal": {"Temperatures": [{"ReadingCelsius": 24}, {"ReadingCelsius": 41}]},
    "/redfish/v1/Systems/System.Embedded.1/Storage": {"Members": [{"@odata.id": "/redfish/v1/Systems/System.Embedded.1/Storage/RAID.Integrated.1-1"}]},
    "/redfish/v1/Systems/System.Embedded.1/Storage/RAID.Integrated.1-1": {"Drives": [{"@odata.id": "/d/1"}]},
    "/d/1": {"Name": "Disk 0", "MediaType": "HDD", "CapacityBytes": 600000000000, "Status": {"Health": "OK"}},
}
RF_HPE = {
    "/redfish/v1/Systems": {"Members": [{"@odata.id": "/redfish/v1/Systems/1/"}]},
    "/redfish/v1/Systems/1": {"Manufacturer": "HPE", "Model": "ProLiant DL380 Gen10", "SerialNumber": "MXQ30301PW",
                               "SKU": "868703-B21", "HostName": "", "PowerState": "On", "BiosVersion": "U30 v2.80",
                               "Status": {"Health": "OK"}},
    "/redfish/v1/Managers": {"Members": [{"@odata.id": "/redfish/v1/Managers/1/"}]},
    "/redfish/v1/Managers/1": {"FirmwareVersion": "iLO 5 v2.78"},
    "/redfish/v1/Chassis": {"Members": [{"@odata.id": "/redfish/v1/Chassis/1/"}]},
    "/redfish/v1/Chassis/1/Power": {"PowerSupplies": [{"Name": "HpeServerPowerSupply", "Status": {"Health": "OK", "State": "Enabled"}}]},
    "/redfish/v1/Chassis/1/Thermal": {"Temperatures": [{"ReadingCelsius": 30}]},
    "/redfish/v1/Systems/1/Storage": {"Members": []},
}


def _http_redfish(metodo, url, headers=None, cuerpo=None, verificar=True):
    assert headers["Authorization"].startswith("Basic ")
    host, ruta = url[len("https://"):].split("/", 1)
    return 200, {"dell.test": RF_DELL, "hpe.test": RF_HPE}[host]["/" + ruta]


def test_redfish_idrac_e_ilo(client, token, monkeypatch, secreto):
    monkeypatch.setattr(config, "REDFISH_HOSTS", ["dell.test", "hpe.test"])
    monkeypatch.setattr(config, "REDFISH_USUARIO", "atlas-lectura")
    monkeypatch.setattr(config, "REDFISH_CLAVE_ARCHIVO", secreto)
    _sync(client, nombre="LLROSSVR03", serial="ABC1234", marca="Dell Inc.", modelo="PowerEdge R740", tipo="Servidor")
    res = conectores.correr("redfish", leer=lambda: conectores.leer_redfish(_http_redfish))
    assert res["ok"], res
    f = _lista(client, token)
    dell = f["LLROSSVR03"]["externos"]["redfish"]
    assert dell["controlador"] == "iDRAC" and dell["salud"] == "Warning" and dell["firmware"] == "6.10.30.00"
    assert dell["fuentes"][1]["salud"] == "Critical" and dell["temperatura_max"] == 41 and dell["discos"][0]["tamano_gb"] == 600
    assert dell["garantia"] == "2027-01-31" and dell["memoria_gb"] == 192
    hpe = next(x for x in f.values() if x["serial"] == "MXQ30301PW")
    rf = hpe["externos"]["redfish"]
    assert rf["controlador"] == "iLO" and rf["firmware"] == "iLO 5 v2.78" and rf["serie"] == "MXQ30301PW"
    assert hpe["tipo"] == "Servidor" and hpe["origenes"] == ["redfish"] and rf["garantia"] is None


def test_redfish_un_host_caido_no_corta_los_demas(client, monkeypatch, secreto):
    monkeypatch.setattr(config, "REDFISH_HOSTS", ["caido.test", "hpe.test"])
    monkeypatch.setattr(config, "REDFISH_USUARIO", "atlas-lectura")
    monkeypatch.setattr(config, "REDFISH_CLAVE_ARCHIVO", secreto)

    def http(metodo, url, headers=None, cuerpo=None, verificar=True):
        if "caido.test" in url:
            raise conectores.ErrorConector("Sin conexión con caido.test (timeout)")
        return _http_redfish(metodo, url, headers, cuerpo, verificar)
    res = conectores.correr("redfish", leer=lambda: conectores.leer_redfish(http))
    assert res["ok"] and "caido.test" in res["mensaje"]


def test_serie_vmware():
    assert conectores.serie_vmware(UUID_VM) == SERIE_VM
    assert conectores.clave_vmware(SERIE_VM) == UUID_VM.replace("-", "")
    assert conectores.clave_vmware("vmware-421D2A3B4C5D6E7F8091A2B3C4D5E6F7") == UUID_VM.replace("-", "")
    assert conectores.serie_vmware("x") == "" and conectores.clave_vmware("ABC") == ""
    # controladora configurada por IP y sin host name: el activo no se llama "10"
    assert conectores.nombre_equipo({"host": "10.1.2.3", "controlador": "iLO"}) == "iLO 10.1.2.3"
    assert conectores.nombre_equipo({"host": "idrac-ros.dominio", "controlador": "iDRAC"}) == "iDRAC idrac-ros"
    assert conectores.nombre_equipo({"host": "10.1.2.3", "nombre_host": "llrossvr03.dominio"}) == "llrossvr03"
