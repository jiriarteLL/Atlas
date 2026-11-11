# -*- coding: utf-8 -*-
"""Conector de CrowdStrike Falcon (solo servidores). Ninguna prueba toca la red: `http` falso."""
import json
from datetime import datetime, timedelta

import pytest

import config
import conectores
import database
from conftest import SYNC_KEY, bearer

SERIE_VM = "VMware-56 4d 2a 3b 4c 5d 6e 7f-80 91 a2 b3 c4 d5 e6 f7"
SERIE_AZ = "0000-0003-1234-5678-9012-3456-78"


def _iso(dt):
    return dt.strftime("%Y-%m-%dT%H:%M:%SZ")


def _dev(device_id, hostname, serie, tipo="Server", so="Windows Server 2019", plataforma="Windows", ip="192.168.100.50",
         visto=None, **extra):
    d = {"device_id": device_id, "hostname": hostname, "serial_number": serie, "product_type_desc": tipo,
         "os_product_name": so, "os_version": so, "platform_name": plataforma, "major_version": "10", "minor_version": "0",
         "build_number": "17763", "kernel_version": "6.8.0-45-generic" if plataforma == "Linux" else "", "local_ip": ip,
         "external_ip": "190.210.78.1", "mac_address": "00-0c-29-96-c9-2b", "default_gateway_ip": "192.168.100.4",
         "machine_domain": "llasesores.corp" if plataforma == "Windows" else "", "ou": ["Servers", "CABA"],
         "site_name": "CABA", "system_manufacturer": "VMware, Inc.", "system_product_name": "VMware7,1",
         "agent_version": "7.18.18905.0", "status": "normal", "reduced_functionality_mode": "no",
         "filesystem_containment_status": "normal", "groups": ["g1"], "tags": ["SensorGroupingTags/Servers"],
         "first_seen": "2025-01-10T10:00:00Z", "last_seen": _iso(visto or datetime.utcnow()),
         "last_reboot": "2026-11-01T06:00:00Z", "last_login_timestamp": "2026-11-05T17:56:00Z",
         "last_login_user": "TANGO\\jiriarte"}
    d.update(extra)
    return d


class FalsoCS:
    """API de hosts falsa: token, query paginada y detalle por lotes; puede devolver 401/429 una vez."""

    def __init__(self, dispositivos, falla_401=False, falla_429=False):
        self.dev = {d["device_id"]: d for d in dispositivos}
        self.orden = [d["device_id"] for d in dispositivos]
        self.tokens = 0
        self.llamadas = []
        self.falla_401, self.falla_429 = falla_401, falla_429

    def __call__(self, metodo, url, headers=None, cuerpo=None, verificar=True):
        ruta = url.replace("https://api.cs.test", "")
        self.llamadas.append((metodo, ruta.split("?")[0]))
        if ruta == "/oauth2/token":
            assert b"client_secret=secreto-cs" in cuerpo and headers["Content-Type"].startswith("application/x-www-form")
            self.tokens += 1
            return 201, {"access_token": "tok-%d" % self.tokens, "expires_in": 1799}
        assert headers["Authorization"].startswith("Bearer tok-")
        if self.falla_401 and self.tokens == 1:
            raise conectores.ErrorConector("HTTP 401", 401)
        if self.falla_429:
            self.falla_429 = False
            raise conectores.ErrorConector("HTTP 429", 429, 3)
        if ruta.startswith("/devices/queries/devices/v1"):
            assert "filter=product_type_desc" in ruta
            offset = int(ruta.split("offset=")[1].split("&")[0])
            limite = int(ruta.split("limit=")[1].split("&")[0])
            return 200, {"meta": {"pagination": {"offset": offset, "limit": limite, "total": len(self.orden)}},
                         "resources": self.orden[offset:offset + limite]}
        if ruta == "/devices/entities/devices/v2":
            assert len(cuerpo["ids"]) <= conectores.CS_LOTE
            return 200, {"resources": [self.dev[i] for i in cuerpo["ids"]]}
        raise AssertionError(ruta)


@pytest.fixture
def cfg_cs(monkeypatch, tmp_path):
    p = tmp_path / "cs.txt"
    p.write_text("secreto-cs\n", encoding="utf-8")
    monkeypatch.setattr(config, "CROWDSTRIKE_URL", "https://api.cs.test")
    monkeypatch.setattr(config, "CROWDSTRIKE_CLIENT_ID", "cliente-1")
    monkeypatch.setattr(config, "CROWDSTRIKE_SECRET_ARCHIVO", str(p))
    monkeypatch.setattr(config, "SEDES_POR_RED", [("192.168.100.0/24", "CABA"), ("172.20.0.0/16", "CABA")])
    monkeypatch.setattr(conectores, "CS_PAGINA", 2)     # para probar la paginacion con pocos equipos
    monkeypatch.setattr(conectores, "CS_LOTE", 2)


def _correr(falso, dormidas=None):
    d = dormidas if dormidas is not None else []
    return conectores.correr("crowdstrike", leer=lambda: conectores.leer_crowdstrike(falso, dormir=d.append))


def _sync(client, **campos):
    base = {"nombre": "SRV-AGENTE", "tipo": "Servidor", "marca": "VMware, Inc.", "modelo": "VMware Virtual Platform",
            "serial": SERIE_VM, "so": "Microsoft Windows Server 2019 Standard", "so_version": "10.0.17763",
            "ip": "192.168.100.21", "ubicacion": "CABA"}
    r = client.post("/api/sync", json=dict(base, **campos), headers={"X-Sync-Key": SYNC_KEY})
    assert r.status_code == 200, r.text


def _servidores(client, token):
    r = client.get("/api/servidores", headers=bearer(token))
    assert r.status_code == 200, r.text
    return r.json()


def _activo(nombre):
    db = database.SessionLocal()
    try:
        return db.query(database.Asset).filter(database.Asset.nombre == nombre).first()
    finally:
        db.close()


# ---------------------------------------------------------------- pruebas
def test_inerte_sin_config(client, token):
    assert conectores.correr("crowdstrike") is None
    est = {c["conector"]: c for c in client.get("/api/conectores", headers=bearer(token)).json()}["crowdstrike"]
    assert not est["configurado"] and "CROWDSTRIKE_URL" in est["falta"] and "CROWDSTRIKE_SECRET_ARCHIVO" in est["falta"]


def test_trae_servidores_cruza_y_da_de_alta(client, token, cfg_cs):
    hace_1h = datetime.utcnow() - timedelta(hours=1)
    _sync(client)                                                         # servidor con agente (VMware)
    _sync(client, nombre="LLAZSVRAPP01", serial=SERIE_AZ, marca="Microsoft Corporation", ip="172.20.0.10")
    db = database.SessionLocal()                                          # cargado a mano, sin serie
    db.add(database.Asset(id="AMANO01", nombre="PLATAFORMA", tipo="Servidor", serial="", estado="Activo",
                          updated=datetime.utcnow() - timedelta(days=3)))
    db.commit()
    db.close()
    falso = FalsoCS([
        # el agente reporto hace instantes: CrowdStrike (visto hace 1 h) no pisa sus campos, solo suma su bloque
        _dev("d1", "SRV-AGENTE.llasesores.corp", SERIE_VM.replace("VMware-56 4d", "VMware-56 4D"), visto=hace_1h),
        _dev("d2", "LLAZSVRAPP01", SERIE_AZ, ip="172.20.0.10", system_manufacturer="Microsoft Corporation",
             system_product_name="Virtual Machine", so="Windows Server 2022"),
        _dev("d3", "PLATAFORMA", "VMware-56 11 11 11 11 11 11 11 11-11 11 11 11 11 11 11 11", ip="192.168.0.64"),
        _dev("d4", "LLAZCRM", "0000-0003-aaaa", tipo="Server", so="Ubuntu 24.04", plataforma="Linux", ip="172.20.0.5",
             system_manufacturer="Microsoft Corporation"),
        _dev("d5", "LLAZCRM", "0000-0006-bbbb", tipo="Server", so="Ubuntu 16.04", plataforma="Linux", ip="172.20.0.6",
             system_manufacturer="Microsoft Corporation"),
        _dev("d6", "NB-USUARIO", "PF0000", tipo="Workstation", so="Windows 11"),   # el filtro de la API no lo deberia traer
    ])
    res = _correr(falso)
    assert res["ok"], res
    assert falso.tokens == 1
    consultas = [r for m, r in falso.llamadas if r == "/devices/queries/devices/v1"]
    assert len(consultas) == 3                                            # 6 ids de a 2
    f = {x["nombre"]: x for x in _servidores(client, token)}
    assert "NB-USUARIO" not in f and _activo("NB-USUARIO") is None        # estaciones: nunca
    srv = f["SRV-AGENTE"]
    assert srv["origenes"] == ["agente", "crowdstrike"] and srv["externos"]["crowdstrike"]["version_sensor"] == "7.18.18905.0"
    assert srv["ip"] == "192.168.100.21"                                  # gano el agente (reporto despues)
    az = f["LLAZSVRAPP01"]
    assert "crowdstrike" in az["origenes"] and az["externos"]["crowdstrike"]["device_id"] == "d2"
    plat = f["PLATAFORMA"]                                                # cruzado por nombre (no tenia serie)
    assert plat["id"] == "AMANO01" and plat["serial"].startswith("VMware-56 11") and plat["ip"] == "192.168.0.64"
    assert plat["origenes"] == ["crowdstrike"] or "crowdstrike" in plat["origenes"]
    # hostnames repetidos con series distintas: dos activos, el segundo con la IP en el nombre
    crm = [x for x in f.values() if x["nombre"].startswith("LLAZCRM")]
    assert sorted(x["nombre"] for x in crm) == ["LLAZCRM", "LLAZCRM (172.20.0.6)"]
    viejo = next(x for x in crm if x["nombre"] == "LLAZCRM (172.20.0.6)")
    assert viejo["tipo"] == "VM" and viejo["origenes"] == ["crowdstrike"] and viejo["sede"] == "Azure"   # LLAZ... = Azure por nombre
    assert viejo["soporte_producto"] == "Ubuntu" and viejo["soporte_estado"] == "sin_soporte"          # 16.04
    nuevo = next(x for x in crm if x["nombre"] == "LLAZCRM")
    assert nuevo["soporte_version"] == "24.04 LTS" and nuevo["soporte_estado"] == "vigente"
    assert nuevo["externos"]["crowdstrike"]["kernel"] == "6.8.0-45-generic"
    # segunda corrida: no duplica ni renombra
    assert _correr(FalsoCS(list(falso.dev.values())))["ok"]
    assert len(_servidores(client, token)) == len(f)


def test_no_pisa_lo_administrativo_y_gana_el_mas_reciente(client, token, cfg_cs):
    _sync(client)
    db = database.SessionLocal()
    a = db.query(database.Asset).filter(database.Asset.nombre == "SRV-AGENTE").first()
    a.garantia, a.comentarios, a.estado, a.usuario = "2028-01-31", "rack 2", "En reparación", "Soporte"
    aid = a.id
    db.commit()
    db.close()
    # CrowdStrike lo vio DESPUES que el ultimo reporte del agente: manda en los campos de red / SO
    futuro = datetime.utcnow() + timedelta(minutes=5)
    assert _correr(FalsoCS([_dev("d1", "SRV-AGENTE", SERIE_VM, ip="192.168.100.99", visto=futuro)]))["ok"]
    a = _activo("SRV-AGENTE")
    assert a.ip == "192.168.100.99" and a.mac == "00:0C:29:96:C9:2B" and a.gateway == "192.168.100.4"
    assert a.so == "Microsoft Windows Server 2019 Standard"          # equivalente ("Microsoft ..."): no se toca
    assert a.modelo == "VMware Virtual Platform"                      # el modelo solo se completa si esta vacio
    assert (a.garantia, a.comentarios, a.estado, a.usuario) == ("2028-01-31", "rack 2", "En reparación", "Soporte")
    assert a.ultimo_login.endswith("(TANGO\\jiriarte)")
    db = database.SessionLocal()
    h = db.query(database.Historial).filter(database.Historial.asset_id == aid, database.Historial.usuario == "crowdstrike").all()
    db.close()
    assert any(x.campo == "ip" and x.valor_new == "192.168.100.99" for x in h)


def test_antivirus_y_contencion(client, token, cfg_cs):
    _sync(client, salud={"so": {"edicion": "Standard", "build": 17763},
                         "antivirus": [{"nombre": "Windows Defender", "activo": False, "actualizado": True}]})
    assert _correr(FalsoCS([_dev("d1", "SRV-AGENTE", SERIE_VM)]))["ok"]
    s = client.get("/api/salud/" + _activo("SRV-AGENTE").id, headers=bearer(token)).json()
    nombres = [x["nombre"] for x in s["antivirus"]]
    assert "Windows Defender" in nombres and "CrowdStrike Falcon Sensor" in nombres and s["av_estado"] == "ok"
    assert s["so_build"] == 17763                                     # no pisa lo que cargo el agente
    assert _correr(FalsoCS([_dev("d1", "SRV-AGENTE", SERIE_VM, status="contained", filesystem_containment_status="contained")]))["ok"]
    s = client.get("/api/salud/" + _activo("SRV-AGENTE").id, headers=bearer(token)).json()
    cs = next(x for x in s["antivirus"] if "CrowdStrike" in x["nombre"])
    assert s["av_estado"] == "desactivado" and "aislado" in cs["nota"]


def test_401_renueva_el_token_y_429_espera(client, cfg_cs):
    falso = FalsoCS([_dev("d1", "SRV-1", "S-1")], falla_401=True)
    assert _correr(falso)["ok"] and falso.tokens == 2
    dormidas = []
    falso = FalsoCS([_dev("d1", "SRV-1", "S-1")], falla_429=True)
    assert _correr(falso, dormidas)["ok"] and dormidas == [3]


def test_error_no_expone_el_secreto(client, token, cfg_cs):
    def caido(metodo, url, headers=None, cuerpo=None, verificar=True):
        raise conectores.ErrorConector("HTTP 403", 403)
    res = _correr(caido)
    assert not res["ok"] and "secreto-cs" not in res["mensaje"] and "403" in res["mensaje"]


def test_sin_reportar_cuando_crowdstrike_no_lo_ve_hace_30_dias(client, token, cfg_cs):
    viejo = datetime.utcnow() - timedelta(days=40)
    assert _correr(FalsoCS([_dev("d9", "SRV-VIEJO", "S-9", plataforma="Linux", so="Debian GNU 9", visto=viejo)]))["ok"]
    x = next(f for f in _servidores(client, token) if f["nombre"] == "SRV-VIEJO")
    assert "sin_reportar" in x["alertas"] and "sin_soporte" in x["alertas"]
    assert _activo("SRV-VIEJO").estado == "Activo"                    # no se da de baja solo
    assert json.loads(json.dumps(x["externos"]["crowdstrike"]))["ultima_vez"].startswith(viejo.strftime("%Y-%m-%d"))
