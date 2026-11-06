# -*- coding: utf-8 -*-
"""Pide a Atlas la lista de impresoras de red, las releva por SNMP y le manda los resultados.

Corre en un servidor que llegue a todas las sedes (hoy LLBASVRAPPS01: Tigre y 192.168.0.x no llegan a Azure),
como tarea programada cada 2 horas. Configuracion en relevamiento.ini al lado del script (solo SYSTEM y
Administradores), igual que el agente:
    [atlas]
    Server=https://172.20.0.10:8743
    SyncKey=<SYNC_API_KEY de Atlas>
    CertInterno=1
    Community=public

Contrato con Atlas (mismo header X-Sync-Key que los agentes):
    GET  /api/impresoras/relevamiento/ips  -> {"ips": ["192.168.100.141", ...]}
    POST /api/impresoras/relevamiento      <- {"lecturas": [<resultado de relevar_impresoras.relevar()>, ...]}
"""
import asyncio
import configparser
import json
import os
import ssl
import sys
import urllib.request
from datetime import datetime

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from relevar_impresoras import relevar_todas  # noqa: E402

AQUI = os.path.dirname(os.path.abspath(__file__))
LOG = os.path.join(os.environ.get("ProgramData", AQUI), "LLyA", "atlas-relevamiento-impresoras.log")


def log(m):
    linea = "%s  %s" % (datetime.now().strftime("%Y-%m-%d %H:%M:%S"), m)
    print(linea)
    try:
        os.makedirs(os.path.dirname(LOG), exist_ok=True)
        if os.path.exists(LOG) and os.path.getsize(LOG) > 1024 * 1024:
            os.replace(LOG, LOG + ".1")
        with open(LOG, "a", encoding="utf-8") as f:
            f.write(linea + "\n")
    except OSError:
        pass


def _pedir(cfg, metodo, ruta, cuerpo=None):
    ctx = ssl.create_default_context()
    if cfg.get("CertInterno", "0") == "1":
        ctx.check_hostname = False
        ctx.verify_mode = ssl.CERT_NONE
    datos = json.dumps(cuerpo).encode("utf-8") if cuerpo is not None else None
    req = urllib.request.Request(cfg["Server"].rstrip("/") + ruta, data=datos, method=metodo,
                                 headers={"X-Sync-Key": cfg["SyncKey"], "Content-Type": "application/json",
                                          "User-Agent": "LLyA-Atlas-Relevamiento-Impresoras"})
    with urllib.request.urlopen(req, context=ctx, timeout=60) as r:
        return json.loads(r.read().decode("utf-8") or "{}")


def main():
    ini = configparser.ConfigParser()
    ini.read(os.path.join(AQUI, "relevamiento.ini"), encoding="utf-8")
    if not ini.has_section("atlas") or not ini["atlas"].get("Server") or not ini["atlas"].get("SyncKey"):
        log("ERROR: falta relevamiento.ini con Server y SyncKey")
        return 2
    cfg = ini["atlas"]
    try:
        ips = _pedir(cfg, "GET", "/api/impresoras/relevamiento/ips").get("ips", [])
    except Exception as e:  # noqa: BLE001
        log("ERROR al pedir la lista de IP a Atlas: %s" % e)
        return 1
    # IP iniciales (ips-iniciales.txt, una por linea): solo direcciones a consultar, nunca datos. De cada una
    # Atlas guarda unicamente lo que la impresora responde por SNMP (alta "limpia" desde la red).
    semillas = os.path.join(AQUI, "ips-iniciales.txt")
    if os.path.exists(semillas):
        with open(semillas, encoding="utf-8") as f:
            ips += [x.strip() for x in f if x.strip() and not x.startswith("#")]
    ips = sorted(set(ips), key=lambda s: tuple(int(p) for p in s.split(".")))
    if not ips:
        log("Atlas no devolvio impresoras de red para relevar")
        return 0
    lecturas = asyncio.run(relevar_todas(ips, cfg.get("Community", "public"), 2.0))
    ok = sum(1 for r in lecturas if r["responde"])
    try:
        resp = _pedir(cfg, "POST", "/api/impresoras/relevamiento", {"lecturas": lecturas})
    except Exception as e:  # noqa: BLE001
        log("ERROR al enviar a Atlas: %s" % e)
        return 1
    log("OK: %d impresoras consultadas, %d respondieron. Atlas: %s" % (len(ips), ok, json.dumps(resp, ensure_ascii=False)))
    return 0


if __name__ == "__main__":
    sys.exit(main())
