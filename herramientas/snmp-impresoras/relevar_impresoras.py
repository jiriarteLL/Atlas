# -*- coding: utf-8 -*-
"""Relevamiento SNMP de impresoras de red para Atlas (paso 2 del modulo de impresoras).

Consulta SOLO las IP que se le pasan (las impresoras que Atlas ya conoce): no escanea la red.
Lee con MIBs estandar (RFC 3805 Printer-MIB y HOST-RESOURCES-MIB), solo lectura:
  modelo (hrDeviceDescr), nombre (sysName), descripcion (sysDescr), serie (prtGeneralSerialNumber),
  contador total (prtMarkerLifeCount), estado (hrPrinterStatus), errores (hrPrinterDetectedErrorState),
  MAC (ifPhysAddress) y consumibles (prtMarkerSupplies: descripcion, maximo, nivel).

Uso:
  python relevar_impresoras.py --ips 192.168.100.141 192.168.100.26 [--community public] [--json salida.json]
  python relevar_impresoras.py --archivo ips.txt
Requiere pysnmp>=7.1.
"""
import argparse
import asyncio
import json
import sys
from datetime import datetime, timezone

from pysnmp.hlapi.v3arch.asyncio import (CommunityData, ContextData, ObjectIdentity, ObjectType, SnmpEngine,
                                         UdpTransportTarget, get_cmd, walk_cmd)

OID = {
    "sys_descr": "1.3.6.1.2.1.1.1.0",
    "sys_name": "1.3.6.1.2.1.1.5.0",
    "modelo": "1.3.6.1.2.1.25.3.2.1.3.1",
    "serie": "1.3.6.1.2.1.43.5.1.1.17.1",
    "contador": "1.3.6.1.2.1.43.10.2.1.4.1.1",
    "estado": "1.3.6.1.2.1.25.3.5.1.1.1",
}
SUM_DESCR = "1.3.6.1.2.1.43.11.1.1.6.1"
SUM_MAX = "1.3.6.1.2.1.43.11.1.1.8.1"
SUM_NIVEL = "1.3.6.1.2.1.43.11.1.1.9.1"
IF_MAC = "1.3.6.1.2.1.2.2.1.6"
ESTADOS = {1: "otro", 2: "desconocido", 3: "en espera", 4: "imprimiendo", 5: "calentando"}
CONCURRENCIA = 16


def _txt(v):
    if v is None:
        return ""
    try:
        if hasattr(v, "asOctets"):
            b = v.asOctets()
            # Muchas HP mandan los textos en Latin-1 ("tóner" = 0xF3): si no es UTF-8 valido, se lee como Latin-1.
            try:
                s = b.decode("utf-8")
            except UnicodeDecodeError:
                s = b.decode("latin-1")
            return "".join(ch for ch in s if ch.isprintable()).strip()
        return str(v).strip()
    except Exception:  # noqa: BLE001
        return str(v)


def _mac(v):
    try:
        b = v.asOctets()
        return ":".join("%02X" % x for x in b) if len(b) == 6 and any(b) else ""
    except Exception:  # noqa: BLE001
        return ""


async def _get(motor, destino, comunidad, oid):
    err, est, _, binds = await get_cmd(motor, comunidad, destino, ContextData(), ObjectType(ObjectIdentity(oid)))
    if err or est or not binds:
        return None
    v = binds[0][1]
    return None if v.__class__.__name__ in ("NoSuchObject", "NoSuchInstance", "EndOfMibView") else v


async def _walk(motor, destino, comunidad, oid):
    res = {}
    async for err, est, _, binds in walk_cmd(motor, comunidad, destino, ContextData(),
                                             ObjectType(ObjectIdentity(oid)), lexicographicMode=False):
        if err or est:
            break
        for nombre, valor in binds:
            res[str(nombre).rsplit(".", 1)[-1]] = valor
    return res


async def relevar(ip, comunidad_txt, timeout=2.0, reintentos=1):
    """Devuelve un dict con los datos de la impresora; 'responde' False si no contesta SNMP."""
    motor = SnmpEngine()
    comunidad = CommunityData(comunidad_txt, mpModel=1)   # SNMP v2c
    r = {"ip": ip, "responde": False, "relevado": datetime.now(timezone.utc).isoformat(timespec="seconds")}
    try:
        destino = await UdpTransportTarget.create((ip, 161), timeout=timeout, retries=reintentos)
        nombre = await _get(motor, destino, comunidad, OID["sys_name"])
        if nombre is None:
            return r
        r["responde"] = True
        r["nombre_red"] = _txt(nombre)
        for k in ("sys_descr", "modelo", "serie"):
            r[k] = _txt(await _get(motor, destino, comunidad, OID[k]))
        cont = await _get(motor, destino, comunidad, OID["contador"])
        r["contador"] = int(cont) if cont is not None else None
        est = await _get(motor, destino, comunidad, OID["estado"])
        r["estado"] = ESTADOS.get(int(est), str(est)) if est is not None else ""
        r["mac"] = next((m for m in (_mac(v) for v in (await _walk(motor, destino, comunidad, IF_MAC)).values()) if m), "")
        descr = await _walk(motor, destino, comunidad, SUM_DESCR)
        maxi = await _walk(motor, destino, comunidad, SUM_MAX)
        nivel = await _walk(motor, destino, comunidad, SUM_NIVEL)
        r["consumibles"] = []
        for i in sorted(descr, key=lambda x: int(x) if x.isdigit() else 0):
            mx = int(maxi[i]) if i in maxi else None
            nv = int(nivel[i]) if i in nivel else None
            # RFC 3805: -1 otro, -2 desconocido, -3 "queda algo" (sin porcentaje)
            pct = round(nv * 100 / mx) if (mx and mx > 0 and nv is not None and nv >= 0) else None
            r["consumibles"].append({"indice": int(i), "descripcion": _txt(descr[i]), "maximo": mx, "nivel": nv,
                                     "porcentaje": pct, "nota": {-3: "queda algo", -2: "desconocido"}.get(nv, "")})
    except Exception as e:  # noqa: BLE001
        r["error"] = str(e)[:200]
    finally:
        motor.close_dispatcher()
    return r


async def relevar_todas(ips, comunidad, timeout):
    sem = asyncio.Semaphore(CONCURRENCIA)

    async def una(ip):
        async with sem:
            return await relevar(ip, comunidad, timeout)
    return await asyncio.gather(*(una(ip) for ip in ips))


def main():
    ap = argparse.ArgumentParser(description="Relevamiento SNMP de impresoras conocidas (solo lectura).")
    ap.add_argument("--ips", nargs="*", default=[])
    ap.add_argument("--archivo", help="archivo con una IP por linea")
    ap.add_argument("--community", default="public")
    ap.add_argument("--timeout", type=float, default=2.0)
    ap.add_argument("--json", help="guardar el resultado completo en este archivo")
    a = ap.parse_args()
    ips = list(a.ips)
    if a.archivo:
        ips += [linea.strip() for linea in open(a.archivo, encoding="utf-8")
                if linea.strip() and not linea.startswith("#")]
    ips = sorted(set(ips), key=lambda s: tuple(int(x) for x in s.split(".")))
    if not ips:
        sys.exit("Indicar --ips o --archivo")
    res = asyncio.run(relevar_todas(ips, a.community, a.timeout))
    for r in res:
        if not r["responde"]:
            print("%-16s sin respuesta%s" % (r["ip"], (" (" + r["error"] + ")") if r.get("error") else ""))
            continue
        ton = ", ".join("%s %s" % (c["descripcion"][:28], ("%d%%" % c["porcentaje"]) if c["porcentaje"] is not None
                                   else (c["nota"] or "?")) for c in r["consumibles"])
        print("%-16s %-28s serie %-16s contador %-9s %-11s MAC %-17s | %s" % (
            r["ip"], r["modelo"][:28], r["serie"] or "-", r["contador"] if r["contador"] is not None else "-",
            r["estado"], r["mac"] or "-", ton or "sin consumibles"))
    if a.json:
        with open(a.json, "w", encoding="utf-8") as f:
            json.dump(res, f, ensure_ascii=False, indent=1)


if __name__ == "__main__":
    main()
