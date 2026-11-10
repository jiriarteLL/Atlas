# -*- coding: utf-8 -*-
"""Conectores de la fase D: vCenter, Azure y Redfish (iDRAC de Dell / iLO de HPE).

Cada conector queda INERTE mientras falte su configuracion (ver config.py y docs/conectores-servidores.md). Las
claves no van nunca en el .env ni en la base: se leen de un archivo aparte (una linea) con ACL restringida, y no
aparecen en logs ni en mensajes de error.

Que hace cada uno:
- vCenter (REST de vSphere 7): VMs y hosts ESXi. La VM se cruza con el activo del agente por la serie: el agente
  manda "VMware-42 1d ..." que es el bios_uuid de la VM. Una VM sin agente (Linux, appliances) se da de alta como
  activo tipo "VM" (asset_externo.creado); si despues aparece el agente con esa serie, el sync la unifica solo.
- Azure (Resource Manager): VMs de las suscripciones configuradas, por service principal o identidad administrada.
  Se cruzan por nombre de equipo con los servidores del dominio (que ya tienen agente).
- Redfish: controladoras de servidores fisicos (iDRAC, iLO). Se cruzan por numero de serie / service tag.

Corrida: un hilo dentro de la app (como las garantias) revisa cada minuto; cada conector configurado corre cada
CONECTORES_CADA_HORAS o cuando alguien aprieta "Actualizar ahora". Lease por conector en conector_corrida (los dos
procesos de Atlas corren la misma app y solo uno consulta).
"""
import base64
import json
import logging
import re
import socket
import ssl
import threading
import time
import urllib.error
import urllib.parse
import urllib.request
import uuid
from datetime import datetime, timedelta

from fastapi import APIRouter, Depends, Request
from sqlalchemy import text as _sql

import config
from audit import log_action
from auth import UserOut, require_modulo
from database import Asset, AssetExterno, AssetSalud, ConectorCorrida, Historial, SessionLocal
from impresoras_relevamiento import sede_de_ip

log = logging.getLogger("atlas")
router = APIRouter(prefix="/api/conectores", tags=["conectores"])

CONECTORES = ("vcenter", "azure", "redfish")
NOMBRES = {"vcenter": "VMware vCenter", "azure": "Microsoft Azure", "redfish": "iDRAC / iLO (Redfish)"}
TIMEOUT_S = 30
LEASE_MIN = 30
USUARIO_AUTO = "conector-%s"
AZURE_API_VM = "2024-07-01"
AZURE_API_NIC = "2024-05-01"
AZURE_MGMT = "https://management.azure.com"
AZURE_IMDS = "http://169.254.169.254/metadata/identity/oauth2/token?api-version=2018-02-01&resource=" + \
             urllib.parse.quote(AZURE_MGMT + "/", safe="")


class ErrorConector(Exception):
    """Error para mostrar en la vista: nunca lleva claves ni respuestas crudas."""


# ---------------------------------------------------------------- utilidades
def leer_secreto(ruta):
    """Primera linea del archivo de la clave, o None. Nunca se loguea el contenido."""
    if not ruta:
        return None
    try:
        with open(ruta, encoding="utf-8-sig") as f:
            v = f.readline().strip()
        return v or None
    except OSError:
        return None


def _ctx(verificar):
    if verificar:
        return ssl.create_default_context()
    c = ssl.create_default_context()
    c.check_hostname = False
    c.verify_mode = ssl.CERT_NONE   # controladoras y vCenter con certificado autofirmado (se avisa en el log)
    return c


def http(metodo, url, headers=None, cuerpo=None, verificar=True):
    """(status, dict|lista|str) — los tests reemplazan esta funcion. Errores HTTP -> ErrorConector sin detalles."""
    datos = None
    if cuerpo is not None:
        datos = cuerpo if isinstance(cuerpo, bytes) else json.dumps(cuerpo).encode("utf-8")
    req = urllib.request.Request(url, data=datos, method=metodo, headers=dict(headers or {}))
    try:
        with urllib.request.urlopen(req, timeout=TIMEOUT_S, context=_ctx(verificar) if url.startswith("https") else None) as r:
            crudo = r.read()
            status = r.status
    except urllib.error.HTTPError as e:
        raise ErrorConector("HTTP %d en %s" % (e.code, urllib.parse.urlsplit(url).path[:80])) from None
    except (urllib.error.URLError, socket.timeout, ssl.SSLError, ConnectionError, OSError) as e:
        raise ErrorConector("Sin conexión con %s (%s)" % (urllib.parse.urlsplit(url).hostname, type(e).__name__)) from None
    try:
        return status, json.loads(crudo.decode("utf-8")) if crudo else None
    except ValueError:
        return status, crudo.decode("utf-8", "replace")


def _basic(usuario, clave):
    return "Basic " + base64.b64encode(("%s:%s" % (usuario, clave)).encode("utf-8")).decode("ascii")


def _txt(v, largo=160):
    s = "" if v is None else str(v)
    return "".join(ch for ch in s if ch.isprintable()).strip()[:largo]


def _num(v):
    try:
        return round(float(v), 1)
    except (TypeError, ValueError):
        return None


# ---------------------------------------------------------------- configuracion
def falta_config(conector):
    """Lista de lo que falta para activar el conector (sin mostrar valores)."""
    falta = []
    if conector == "vcenter":
        if not config.VCENTER_URL:
            falta.append("VCENTER_URL")
        if not config.VCENTER_USUARIO:
            falta.append("VCENTER_USUARIO")
        if not config.VCENTER_CLAVE_ARCHIVO:
            falta.append("VCENTER_CLAVE_ARCHIVO")
        elif not leer_secreto(config.VCENTER_CLAVE_ARCHIVO):
            falta.append("archivo de clave de vCenter (no existe o está vacío)")
    elif conector == "azure":
        if not config.AZURE_SUSCRIPCIONES:
            falta.append("AZURE_SUSCRIPCIONES")
        if not config.AZURE_USAR_IDENTIDAD:
            for k in ("AZURE_TENANT_ID", "AZURE_CLIENT_ID", "AZURE_CLIENT_SECRET_ARCHIVO"):
                if not getattr(config, k):
                    falta.append(k)
            if config.AZURE_CLIENT_SECRET_ARCHIVO and not leer_secreto(config.AZURE_CLIENT_SECRET_ARCHIVO):
                falta.append("archivo del secreto de Azure (no existe o está vacío)")
    elif conector == "redfish":
        if not config.REDFISH_HOSTS:
            falta.append("REDFISH_HOSTS")
        if not config.REDFISH_USUARIO:
            falta.append("REDFISH_USUARIO")
        if not config.REDFISH_CLAVE_ARCHIVO:
            falta.append("REDFISH_CLAVE_ARCHIVO")
        elif not leer_secreto(config.REDFISH_CLAVE_ARCHIVO):
            falta.append("archivo de clave de Redfish (no existe o está vacío)")
    return falta


def configurado(conector):
    return not falta_config(conector)


# ---------------------------------------------------------------- vCenter
def serie_vmware(bios_uuid):
    """'421d2a3b-4c5d-6e7f-8091-a2b3c4d5e6f7' -> 'VMware-42 1d 2a 3b 4c 5d 6e 7f-80 91 a2 b3 c4 d5 e6 f7'."""
    h = re.sub(r"[^0-9a-fA-F]", "", bios_uuid or "").lower()
    if len(h) != 32:
        return ""
    b = [h[i:i + 2] for i in range(0, 32, 2)]
    return "VMware-" + " ".join(b[:8]) + "-" + " ".join(b[8:])


def clave_vmware(serial):
    """Serie de VMware (del agente o armada) -> 32 hex para comparar sin importar espacios ni mayusculas."""
    s = (serial or "").strip()
    if not s.lower().startswith("vmware-"):
        return ""
    h = re.sub(r"[^0-9a-fA-F]", "", s[7:]).lower()
    return h if len(h) == 32 else ""


def leer_vcenter(http=http):
    url, verificar = config.VCENTER_URL, config.VCENTER_VERIFICAR_CERT
    clave = leer_secreto(config.VCENTER_CLAVE_ARCHIVO)
    if not clave:
        raise ErrorConector("Falta la clave de vCenter")
    if not verificar:
        log.warning("conectores.vcenter sin verificar el certificado (VCENTER_VERIFICAR_CERT=0)", extra={"event": "conectores"})
    _, token = http("POST", url + "/api/session", {"Authorization": _basic(config.VCENTER_USUARIO, clave)}, None, verificar)
    if not isinstance(token, str) or not token:
        raise ErrorConector("vCenter no devolvió una sesión")
    h = {"vmware-api-session-id": token}
    try:
        _, hosts = http("GET", url + "/api/vcenter/host", h, None, verificar)
        hosts = hosts if isinstance(hosts, list) else []
        cluster_de_host = {}
        try:
            _, clusters = http("GET", url + "/api/vcenter/cluster", h, None, verificar)
            for c in clusters if isinstance(clusters, list) else []:
                _, hs = http("GET", url + "/api/vcenter/host?clusters=" + urllib.parse.quote(c.get("cluster", "")), h, None, verificar)
                for x in hs if isinstance(hs, list) else []:
                    cluster_de_host[x.get("host")] = _txt(c.get("name"), 80)
        except ErrorConector:
            pass
        host_de_vm = {}
        for x in hosts:
            _, vms_h = http("GET", url + "/api/vcenter/vm?hosts=" + urllib.parse.quote(x.get("host", "")), h, None, verificar)
            for v in vms_h if isinstance(vms_h, list) else []:
                host_de_vm[v.get("vm")] = x
        _, vms = http("GET", url + "/api/vcenter/vm", h, None, verificar)
        out_vms = []
        for v in (vms if isinstance(vms, list) else [])[:2000]:
            moid = v.get("vm")
            _, d = http("GET", url + "/api/vcenter/vm/" + urllib.parse.quote(moid or ""), h, None, verificar)
            d = d if isinstance(d, dict) else {}
            ip = nombre_guest = so_guest = ""
            try:
                _, g = http("GET", url + "/api/vcenter/vm/%s/guest/identity" % urllib.parse.quote(moid or ""), h, None, verificar)
                if isinstance(g, dict):
                    fn = g.get("full_name")
                    ip, nombre_guest = _txt(g.get("ip_address"), 45), _txt(g.get("host_name"), 120)
                    so_guest = _txt(fn.get("default_message") if isinstance(fn, dict) else fn)
            except ErrorConector:
                pass   # sin VMware Tools
            discos = []
            for k, dk in (d.get("disks") or {}).items() if isinstance(d.get("disks"), dict) else []:
                cap = dk.get("capacity") if isinstance(dk, dict) else None
                discos.append({"nombre": _txt((dk.get("label") if isinstance(dk, dict) else "") or k, 60),
                               "tamano_gb": round(cap / 1024 ** 3, 1) if isinstance(cap, (int, float)) else None})
            host = host_de_vm.get(moid) or {}
            ident = d.get("identity") if isinstance(d.get("identity"), dict) else {}
            mib = (d.get("memory") or {}).get("size_MiB") if isinstance(d.get("memory"), dict) else None
            mib = mib if isinstance(mib, (int, float)) else v.get("memory_size_MiB")
            cpu = (d.get("cpu") or {}).get("count") if isinstance(d.get("cpu"), dict) else None
            out_vms.append({
                "moid": _txt(moid, 40), "nombre": _txt(d.get("name") or v.get("name"), 120),
                "estado": _txt(d.get("power_state") or v.get("power_state"), 20),
                "cpu": cpu if isinstance(cpu, int) else v.get("cpu_count"),
                "ram_gb": round(mib / 1024, 1) if isinstance(mib, (int, float)) else None,
                "so": so_guest or _txt(d.get("guest_OS"), 60), "ip": ip, "nombre_guest": nombre_guest,
                "discos": discos[:20], "bios_uuid": _txt(ident.get("bios_uuid"), 40),
                "host": _txt(host.get("name"), 120), "cluster": cluster_de_host.get(host.get("host"), ""),
            })
        out_hosts = [{"moid": _txt(x.get("host"), 40), "nombre": _txt(x.get("name"), 120),
                      "estado": _txt(x.get("connection_state"), 20), "encendido": _txt(x.get("power_state"), 20),
                      "cluster": cluster_de_host.get(x.get("host"), "")} for x in hosts]
        return {"vms": out_vms, "hosts": out_hosts}
    finally:
        try:
            http("DELETE", url + "/api/session", h, None, verificar)
        except ErrorConector:
            pass


# ---------------------------------------------------------------- Azure
def _token_azure(http=http):
    if config.AZURE_USAR_IDENTIDAD:
        _, r = http("GET", AZURE_IMDS, {"Metadata": "true"}, None, True)
    else:
        secreto = leer_secreto(config.AZURE_CLIENT_SECRET_ARCHIVO)
        if not secreto:
            raise ErrorConector("Falta el secreto del service principal de Azure")
        cuerpo = urllib.parse.urlencode({"grant_type": "client_credentials", "client_id": config.AZURE_CLIENT_ID,
                                         "client_secret": secreto, "scope": AZURE_MGMT + "/.default"}).encode("ascii")
        _, r = http("POST", "https://login.microsoftonline.com/%s/oauth2/v2.0/token" % urllib.parse.quote(config.AZURE_TENANT_ID),
                    {"Content-Type": "application/x-www-form-urlencoded"}, cuerpo, True)
    tok = r.get("access_token") if isinstance(r, dict) else None
    if not tok:
        raise ErrorConector("Azure no devolvió un token")
    return tok


def _paginas(http, url, h):
    while url:
        _, r = http("GET", url, h, None, True)
        r = r if isinstance(r, dict) else {}
        yield from (r.get("value") or [])
        url = r.get("nextLink")


def leer_azure(http=http):
    h = {"Authorization": "Bearer " + _token_azure(http)}
    out = []
    for sub in config.AZURE_SUSCRIPCIONES:
        base = AZURE_MGMT + "/subscriptions/%s/providers/Microsoft.Compute/virtualMachines" % urllib.parse.quote(sub)
        estados = {}
        for v in _paginas(http, base + "?api-version=%s&statusOnly=true" % AZURE_API_VM, h):
            codigos = [s.get("code", "") for s in ((v.get("properties") or {}).get("instanceView") or {}).get("statuses", [])]
            estados[(v.get("id") or "").lower()] = next((c.split("/", 1)[1] for c in codigos if c.startswith("PowerState/")), "")
        for v in _paginas(http, base + "?api-version=%s" % AZURE_API_VM, h):
            p = v.get("properties") or {}
            st = p.get("storageProfile") or {}
            os_d = st.get("osDisk") or {}
            discos = [{"nombre": _txt(os_d.get("name"), 80), "tamano_gb": os_d.get("diskSizeGB"), "so": True}] + \
                     [{"nombre": _txt(d.get("name"), 80), "tamano_gb": d.get("diskSizeGB"), "so": False} for d in st.get("dataDisks") or []]
            ip = ""
            nics = (p.get("networkProfile") or {}).get("networkInterfaces") or []
            if nics and nics[0].get("id"):
                try:
                    _, nic = http("GET", AZURE_MGMT + nics[0]["id"] + "?api-version=" + AZURE_API_NIC, h, None, True)
                    cfgs = ((nic or {}).get("properties") or {}).get("ipConfigurations") or []
                    ip = _txt(((cfgs[0] if cfgs else {}).get("properties") or {}).get("privateIPAddress"), 45)
                except ErrorConector:
                    pass
            rid = v.get("id") or ""
            partes = rid.split("/")
            rg = partes[partes.index("resourceGroups") + 1] if "resourceGroups" in partes else ""
            img = st.get("imageReference") or {}
            out.append({
                "id": _txt(rid.lower(), 300), "nombre": _txt(v.get("name"), 80),
                "nombre_equipo": _txt((p.get("osProfile") or {}).get("computerName"), 80),
                "suscripcion": _txt(sub, 40), "grupo_recursos": _txt(rg, 90), "region": _txt(v.get("location"), 40),
                "tamano": _txt((p.get("hardwareProfile") or {}).get("vmSize"), 60),
                "so_tipo": _txt(os_d.get("osType"), 20),
                "imagen": _txt(" ".join(x for x in (img.get("publisher"), img.get("offer"), img.get("sku")) if x), 120),
                "estado": estados.get(rid.lower(), ""), "ip": ip, "discos": discos[:20],
            })
    return {"vms": out}


# ---------------------------------------------------------------- Redfish (iDRAC / iLO)
def _rf_get(http, base, ruta, h, verificar):
    _, r = http("GET", base + ruta, h, None, verificar)
    return r if isinstance(r, dict) else {}


def _salud(x):
    st = x.get("Status") if isinstance(x.get("Status"), dict) else {}
    return _txt(st.get("HealthRollup") or st.get("Health"), 20)


def leer_redfish_host(host, http=http, usuario=None, clave=None):
    verificar = config.REDFISH_VERIFICAR_CERT
    base = "https://" + host
    h = {"Authorization": _basic(usuario or config.REDFISH_USUARIO, clave or leer_secreto(config.REDFISH_CLAVE_ARCHIVO) or "")}
    sistemas = _rf_get(http, base, "/redfish/v1/Systems", h, verificar).get("Members") or []
    if not sistemas:
        raise ErrorConector("Redfish sin sistemas en %s" % host)
    sys_ruta = (sistemas[0].get("@odata.id") or "").rstrip("/")   # iLO devuelve las rutas con "/" al final
    s = _rf_get(http, base, sys_ruta, h, verificar)
    fabricante = _txt(s.get("Manufacturer"), 60)
    fab = fabricante.lower()
    controlador = "iDRAC" if "dell" in fab else "iLO" if ("hpe" in fab or fab in ("hp", "hewlett-packard")) else "BMC"
    out = {
        "host": _txt(host, 120), "controlador": controlador, "fabricante": fabricante, "modelo": _txt(s.get("Model"), 80),
        "serie": _txt(s.get("SerialNumber"), 60), "sku": _txt(s.get("SKU"), 60), "nombre_host": _txt(s.get("HostName"), 120),
        "salud": _salud(s), "encendido": _txt(s.get("PowerState"), 20), "bios": _txt(s.get("BiosVersion"), 60),
        "memoria_gb": _num((s.get("MemorySummary") or {}).get("TotalSystemMemoryGiB")),
        "cpu": _txt(((s.get("ProcessorSummary") or {}).get("Model")), 120),
        "cpu_cantidad": (s.get("ProcessorSummary") or {}).get("Count"),
        "firmware": "", "fuentes": [], "discos": [], "temperatura_max": None, "garantia": None,
    }
    # Firmware de la controladora (Managers)
    try:
        mgrs = _rf_get(http, base, "/redfish/v1/Managers", h, verificar).get("Members") or []
        if mgrs:
            mgr = _rf_get(http, base, (mgrs[0].get("@odata.id") or "").rstrip("/"), h, verificar)
            out["firmware"] = _txt(mgr.get("FirmwareVersion"), 60)
    except ErrorConector:
        pass
    # Fuentes y temperatura (Chassis/<id>/Power y /Thermal, rutas estandar)
    try:
        chasis = _rf_get(http, base, "/redfish/v1/Chassis", h, verificar).get("Members") or []
        if chasis:
            ch = (chasis[0].get("@odata.id") or "").rstrip("/")
            pw = _rf_get(http, base, ch + "/Power", h, verificar)
            out["fuentes"] = [{"nombre": _txt(f.get("Name"), 60), "salud": _salud(f),
                               "estado": _txt((f.get("Status") or {}).get("State"), 20)} for f in (pw.get("PowerSupplies") or [])[:8]]
            th = _rf_get(http, base, ch + "/Thermal", h, verificar)
            temps = [t.get("ReadingCelsius") for t in th.get("Temperatures") or [] if isinstance(t.get("ReadingCelsius"), (int, float))]
            out["temperatura_max"] = max(temps) if temps else None
    except ErrorConector:
        pass
    # Discos (Systems/<id>/Storage -> controladoras -> Drives)
    try:
        ctrls = _rf_get(http, base, sys_ruta + "/Storage", h, verificar).get("Members") or []
        for c in ctrls[:6]:
            ct = _rf_get(http, base, (c.get("@odata.id") or "").rstrip("/"), h, verificar)
            for d in (ct.get("Drives") or [])[:24]:
                dd = _rf_get(http, base, (d.get("@odata.id") or "").rstrip("/"), h, verificar)
                cap = dd.get("CapacityBytes")
                out["discos"].append({"nombre": _txt(dd.get("Name") or dd.get("Id"), 60), "salud": _salud(dd),
                                      "tipo": _txt(dd.get("MediaType"), 10), "modelo": _txt(dd.get("Model"), 60),
                                      "tamano_gb": round(cap / 1000 ** 3) if isinstance(cap, (int, float)) else None})
    except ErrorConector:
        pass
    # Garantia: solo si la controladora Dell la expone en su OEM (no es estandar)
    oem = ((s.get("Oem") or {}).get("Dell") or {}) if isinstance(s.get("Oem"), dict) else {}
    gar = oem.get("DellSystem") if isinstance(oem.get("DellSystem"), dict) else {}
    if gar.get("WarrantyEndDate") if isinstance(gar, dict) else None:
        out["garantia"] = _txt(gar.get("WarrantyEndDate"), 30)
    return out


def leer_redfish(http=http):
    clave = leer_secreto(config.REDFISH_CLAVE_ARCHIVO)
    if not clave:
        raise ErrorConector("Falta la clave de Redfish")
    if not config.REDFISH_VERIFICAR_CERT:
        log.warning("conectores.redfish sin verificar el certificado (REDFISH_VERIFICAR_CERT=0)", extra={"event": "conectores"})
    equipos, errores = [], []
    for host in config.REDFISH_HOSTS:
        try:
            equipos.append(leer_redfish_host(host, http, config.REDFISH_USUARIO, clave))
        except ErrorConector as e:
            errores.append(str(e))
    if not equipos and errores:
        raise ErrorConector("; ".join(errores)[:300])
    return {"equipos": equipos, "errores": errores}


# ---------------------------------------------------------------- aplicar a los activos
def _externo(db, asset_id, fuente):
    return db.query(AssetExterno).filter(AssetExterno.asset_id == asset_id, AssetExterno.fuente == fuente).first()


def _guardar_externo(db, a, fuente, clave, datos, creado, ahora):
    e = _externo(db, a.id, fuente)
    if e is None:
        e = AssetExterno(asset_id=a.id, fuente=fuente, creado=creado)
        db.add(e)
    e.clave, e.datos, e.actualizado = clave, json.dumps(datos, ensure_ascii=False, default=str), ahora
    return e


def _sin_agente(db, a):
    """El activo lo dio de alta un conector y el agente todavia no reporto: el conector puede completar sus datos."""
    return db.get(AssetSalud, a.id) is None


def _por_clave(db, fuente, clave):
    e = db.query(AssetExterno).filter(AssetExterno.fuente == fuente, AssetExterno.clave == clave).first()
    return db.get(Asset, e.asset_id) if e else None


def _alta(db, fuente, ahora, **campos):
    a = Asset(id=("A" + str(uuid.uuid4())[:6]).upper(), estado="Activo", updated=ahora, **campos)
    db.add(a)
    db.flush()
    db.add(Historial(asset_id=a.id, usuario=USUARIO_AUTO % fuente, campo="alta", valor_ant="",
                     valor_new=a.nombre or a.serial, accion="sincronizacion"))
    return a


def aplicar_vcenter(db, datos, ahora=None):
    ahora = ahora or datetime.utcnow()
    por_uuid = {}
    for a in db.query(Asset).filter(Asset.serial.ilike("vmware-%")).all():
        k = clave_vmware(a.serial)
        if k:
            por_uuid[k] = a
    res = {"vms": 0, "altas": 0, "hosts": 0}
    for v in datos.get("vms", []):
        serie = serie_vmware(v.get("bios_uuid"))
        a = _por_clave(db, "vcenter", v["moid"]) or (por_uuid.get(clave_vmware(serie)) if serie else None)
        nuevo = a is None
        if nuevo:
            a = _alta(db, "vcenter", ahora, nombre=v["nombre_guest"].split(".")[0] or v["nombre"], tipo="VM",
                      marca="VMware, Inc.", modelo="VMware Virtual Platform", serial=serie,
                      ubicacion=sede_de_ip(v["ip"]) if v.get("ip") else "")
            res["altas"] += 1
        e = _guardar_externo(db, a, "vcenter", v["moid"], v, nuevo, ahora)
        if e.creado and _sin_agente(db, a):
            a.so, a.ip = v.get("so") or a.so, v.get("ip") or a.ip
            a.cpu = "%s vCPU" % v["cpu"] if v.get("cpu") else a.cpu
            a.ram = "%sGB" % int(v["ram_gb"]) if v.get("ram_gb") else a.ram
            total = sum(d["tamano_gb"] or 0 for d in v.get("discos", []))
            a.disco = "%dGB" % total if total else a.disco
            if v.get("ip") and not a.ubicacion:
                a.ubicacion = sede_de_ip(v["ip"])
            a.updated = ahora
        res["vms"] += 1
    for x in datos.get("hosts", []):
        a = _por_clave(db, "vcenter", "host:" + x["moid"])
        if a is None:
            a = db.query(Asset).filter(Asset.tipo == "Servidor", Asset.nombre.ilike(x["nombre"])).first()
        nuevo = a is None
        if nuevo:
            a = _alta(db, "vcenter", ahora, nombre=x["nombre"], tipo="Servidor", marca="VMware ESXi", modelo="Host ESXi", serial="")
            res["altas"] += 1
        _guardar_externo(db, a, "vcenter", "host:" + x["moid"], dict(x, es_host=True), nuevo, ahora)
        res["hosts"] += 1
    return res


def aplicar_azure(db, datos, ahora=None):
    ahora = ahora or datetime.utcnow()
    res = {"vms": 0, "altas": 0}
    for v in datos.get("vms", []):
        a = _por_clave(db, "azure", v["id"])
        if a is None:
            for nombre in (v.get("nombre_equipo"), v.get("nombre")):
                if nombre:
                    a = db.query(Asset).filter(Asset.nombre.ilike(nombre), Asset.estado != "Dado de baja").first()
                    if a:
                        break
        nuevo = a is None
        if nuevo:
            a = _alta(db, "azure", ahora, nombre=v.get("nombre_equipo") or v["nombre"], tipo="VM", marca="Microsoft Corporation",
                      modelo=("Azure " + v.get("tamano", "")).strip(), serial="", ip=v.get("ip", ""),
                      so=v.get("imagen") or v.get("so_tipo", ""),
                      ubicacion=sede_de_ip(v["ip"]) if v.get("ip") else "")
            res["altas"] += 1
        _guardar_externo(db, a, "azure", v["id"], v, nuevo, ahora)
        res["vms"] += 1
    return res


_ES_IP = re.compile(r"^[0-9.:]+$")


def nombre_equipo(x):
    """Nombre del servidor fisico: el host name del sistema; si no hay, "iLO <ip>" / "iDRAC <nombre corto>"."""
    if x.get("nombre_host"):
        return x["nombre_host"].split(".")[0]
    host = x.get("host") or ""
    return "%s %s" % (x.get("controlador") or "BMC", host if _ES_IP.match(host) else host.split(".")[0])


def aplicar_redfish(db, datos, ahora=None):
    ahora = ahora or datetime.utcnow()
    res = {"equipos": 0, "altas": 0}
    for x in datos.get("equipos", []):
        a = _por_clave(db, "redfish", x["host"])
        if a is None:
            for serie in (x.get("sku"), x.get("serie")):
                if serie:
                    a = db.query(Asset).filter(Asset.serial.ilike(serie)).first()
                    if a:
                        break
        nuevo = a is None
        if nuevo:
            # Dell: la serie del equipo es el service tag (SKU en Redfish); HPE: SKU es el numero de parte
            serie = x.get("sku") if x.get("controlador") == "iDRAC" and x.get("sku") else (x.get("serie") or x.get("sku") or "")
            a = _alta(db, "redfish", ahora, nombre=nombre_equipo(x), tipo="Servidor",
                      marca=x.get("fabricante") or "", modelo=x.get("modelo") or "", serial=serie)
            res["altas"] += 1
        _guardar_externo(db, a, "redfish", x["host"], x, nuevo, ahora)
        res["equipos"] += 1
    return res


LEER = {"vcenter": lambda: leer_vcenter(http), "azure": lambda: leer_azure(http), "redfish": lambda: leer_redfish(http)}
APLICAR = {"vcenter": aplicar_vcenter, "azure": aplicar_azure, "redfish": aplicar_redfish}


# ---------------------------------------------------------------- corrida (lease por conector)
_DUENIO = "%s-%s" % (socket.gethostname(), uuid.uuid4().hex[:8])


def _fila(db, conector):
    f = db.get(ConectorCorrida, conector)
    if f is None:
        try:
            db.add(ConectorCorrida(conector=conector, pedida=False, elementos=0, mensaje="", duenio=""))
            db.commit()
        except Exception:
            db.rollback()
        f = db.get(ConectorCorrida, conector)
    return f


def _tomar_lease(db, conector, duenio, ahora):
    _fila(db, conector)
    r = db.execute(_sql("UPDATE conector_corrida SET corriendo_hasta = :h, duenio = :d "
                        "WHERE conector = :c AND (corriendo_hasta IS NULL OR corriendo_hasta < :a)"),
                   {"h": ahora + timedelta(minutes=LEASE_MIN), "d": duenio, "c": conector, "a": ahora})
    db.commit()
    return r.rowcount == 1


def correr(conector, leer=None):
    """Una corrida del conector si este proceso toma el lease. Devuelve el resumen o None."""
    if conector not in CONECTORES or not configurado(conector):
        return None
    leer = leer or LEER[conector]
    duenio = "%s-%s" % (_DUENIO, threading.get_ident())
    db = SessionLocal()
    try:
        ahora = datetime.utcnow()
        if not _tomar_lease(db, conector, duenio, ahora):
            return None
        f = _fila(db, conector)
        f.pedida, f.inicio, f.fin = False, ahora, None
        db.commit()
        try:
            datos = leer()
            res = APLICAR[conector](db, datos)
            elementos = sum(v for k, v in res.items() if k != "altas")
            ok, mensaje = True, "%d elementos, %d altas" % (elementos, res.get("altas", 0))
            if isinstance(datos, dict) and datos.get("errores"):
                mensaje += " · sin respuesta: %s" % "; ".join(datos["errores"])[:200]
            db.commit()
        except ErrorConector as e:
            db.rollback()
            ok, elementos, mensaje = False, 0, str(e)[:300]
        except Exception as e:
            db.rollback()
            ok, elementos, mensaje = False, 0, "Error interno (%s)" % type(e).__name__
        f = _fila(db, conector)
        f.fin, f.ok, f.elementos, f.mensaje, f.corriendo_hasta, f.duenio = datetime.utcnow(), ok, elementos, mensaje, None, ""
        db.commit()
        log.info("conectores.%s ok=%s %s", conector, ok, mensaje, extra={"event": "conectores"})
        return {"ok": ok, "elementos": elementos, "mensaje": mensaje}
    finally:
        db.close()


def toca_correr(db, conector, ahora=None):
    if not configurado(conector):
        return False
    ahora = ahora or datetime.utcnow()
    f = _fila(db, conector)
    if f.pedida:
        return True
    if config.CONECTORES_CADA_HORAS <= 0:
        return False
    return f.inicio is None or ahora - f.inicio >= timedelta(hours=config.CONECTORES_CADA_HORAS)


def hay_alguno_configurado():
    return any(configurado(c) for c in CONECTORES)


def loop():
    """Hilo de fondo (lo arranca main.lifespan). Revisa cada minuto si a algun conector configurado le toca."""
    time.sleep(90)
    while True:
        for c in CONECTORES:
            try:
                db = SessionLocal()
                try:
                    toca = toca_correr(db, c)
                finally:
                    db.close()
                if toca:
                    correr(c)
            except Exception as e:
                log.error("conectores.loop %s %s", c, type(e).__name__, extra={"event": "conectores"})
        time.sleep(60)


# ---------------------------------------------------------------- endpoints
def estado(db):
    ahora = datetime.utcnow()
    out = []
    for c in CONECTORES:
        f = _fila(db, c)
        falta = falta_config(c)
        out.append({"conector": c, "nombre": NOMBRES[c], "configurado": not falta, "falta": falta,
                    "corriendo": bool(f.corriendo_hasta and f.corriendo_hasta > ahora), "pedida": bool(f.pedida),
                    "inicio": f.inicio, "fin": f.fin, "ok": f.ok, "elementos": f.elementos or 0, "mensaje": f.mensaje or "",
                    "cada_horas": config.CONECTORES_CADA_HORAS})
    return out


@router.get("")
def listar(user: UserOut = Depends(require_modulo("servidores"))):
    db = SessionLocal()
    try:
        return estado(db)
    finally:
        db.close()


@router.post("/actualizar")
def actualizar(request: Request, user: UserOut = Depends(require_modulo("activos", nivel="editar"))):
    """Pide una corrida ya de cada conector configurado (no bloquea: la corre un hilo aparte)."""
    db = SessionLocal()
    lanzados = []
    try:
        for c in CONECTORES:
            if configurado(c):
                _fila(db, c).pedida = True
                lanzados.append(c)
        db.commit()
    finally:
        db.close()
    for c in lanzados:
        threading.Thread(target=correr, args=(c,), daemon=True).start()
    log_action(user.username, "actualizar_conectores", "conectores", ",".join(lanzados) or "-", {},
               ip=request.client.host if request.client else "")
    return {"status": "encolada" if lanzados else "sin_conectores", "conectores": lanzados}
