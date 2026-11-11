# -*- coding: utf-8 -*-
"""Fin de soporte de Windows segun build y edicion.

Fuentes (consultadas el 06/11/2026):
- Windows 11 Home and Pro / Enterprise and Education y Windows 10 Home and Pro / Enterprise and Education:
  learn.microsoft.com/lifecycle/products/<producto> (tabla "Releases").
- Builds por version y fechas de Windows 11 y Windows Server: learn.microsoft.com/windows/release-health
  (windows11-release-information y windows-server-release-info).
Microsoft publica el fin a las 06:59:59 UTC del dia siguiente (medianoche de Redmond): aca va el ultimo dia con
soporte, que es el martes de parches. Las fechas que pasaron siguen en la tabla para mostrar "sin soporte desde".

Cuando Microsoft publique una version nueva hay que agregar su build aca; mientras tanto el equipo queda como
"desconocido" (no se lo marca como vencido).
"""
import re
from datetime import date

AVISO_DIAS = 60   # "vence pronto" si al soporte le quedan esta cantidad de dias o menos

# build: (producto, version, fin Home/Pro, fin Enterprise/Education)
CLIENTE = {
    19041: ("Windows 10", "2004", date(2021, 12, 14), date(2021, 12, 14)),
    19042: ("Windows 10", "20H2", date(2022, 5, 10), date(2023, 5, 9)),
    19043: ("Windows 10", "21H1", date(2022, 12, 13), date(2022, 12, 13)),
    19044: ("Windows 10", "21H2", date(2023, 6, 13), date(2024, 6, 11)),
    19045: ("Windows 10", "22H2", date(2025, 10, 14), date(2025, 10, 14)),
    22000: ("Windows 11", "21H2", date(2023, 10, 10), date(2024, 10, 8)),
    22621: ("Windows 11", "22H2", date(2024, 10, 8), date(2025, 10, 14)),
    22631: ("Windows 11", "23H2", date(2025, 11, 11), date(2026, 11, 10)),
    26100: ("Windows 11", "24H2", date(2026, 10, 13), date(2027, 10, 12)),
    26200: ("Windows 11", "25H2", date(2027, 10, 12), date(2028, 10, 10)),
    26300: ("Windows 11", "26H2", date(2028, 10, 10), date(2029, 10, 9)),
    28000: ("Windows 11", "26H1", date(2028, 3, 14), date(2029, 3, 13)),
}

# LTSC: solo las verificadas; el resto queda "desconocido" para revisarlo a mano.
LTSC = {
    26100: ("Windows 11", "LTSC 2024", date(2029, 10, 9)),
}

# Windows Server (soporte extendido)
SERVIDOR = {
    7601: ("Windows Server", "2008 R2", date(2020, 1, 14)),
    9200: ("Windows Server", "2012", date(2023, 10, 10)),
    9600: ("Windows Server", "2012 R2", date(2023, 10, 10)),
    14393: ("Windows Server", "2016", date(2027, 1, 12)),
    17763: ("Windows Server", "2019", date(2029, 1, 9)),
    20348: ("Windows Server", "2022", date(2031, 10, 14)),
    26100: ("Windows Server", "2025", date(2034, 11, 14)),
}


# Linux de los servidores (los trae CrowdStrike / vCenter). Ubuntu LTS: fin del soporte estandar (sin Ubuntu Pro/ESM);
# Debian: fin del LTS. Fechas de los calendarios publicados por Canonical y Debian LTS; las que se anuncian solo por
# mes (Ubuntu 22.04 y 24.04, Debian 13) van al ultimo dia de ese mes y son APROXIMADAS: revisarlas cuando se acerquen.
LINUX = {
    ("ubuntu", "14.04"): ("Ubuntu", "14.04 LTS", date(2019, 4, 30)),
    ("ubuntu", "16.04"): ("Ubuntu", "16.04 LTS", date(2021, 4, 30)),
    ("ubuntu", "18.04"): ("Ubuntu", "18.04 LTS", date(2023, 5, 31)),
    ("ubuntu", "20.04"): ("Ubuntu", "20.04 LTS", date(2025, 5, 31)),
    ("ubuntu", "22.04"): ("Ubuntu", "22.04 LTS", date(2027, 4, 30)),    # aproximada (abril 2027)
    ("ubuntu", "24.04"): ("Ubuntu", "24.04 LTS", date(2029, 4, 30)),    # aproximada (abril 2029)
    ("debian", "9"): ("Debian", "9 (stretch)", date(2022, 6, 30)),
    ("debian", "10"): ("Debian", "10 (buster)", date(2024, 6, 30)),
    ("debian", "11"): ("Debian", "11 (bullseye)", date(2026, 8, 31)),
    ("debian", "12"): ("Debian", "12 (bookworm)", date(2028, 6, 30)),
    ("debian", "13"): ("Debian", "13 (trixie)", date(2030, 6, 30)),     # aproximada
}


def _estado(fin, hoy):
    dias = (fin - hoy).days
    return ("sin_soporte" if dias < 0 else "vence_pronto" if dias <= AVISO_DIAS else "vigente"), dias


def soporte_linux(so, hoy=None):
    """"Ubuntu 24.04" / "Ubuntu 24.04.1 LTS" / "Debian GNU 9" -> mismo formato que soporte(); desconocido si no esta."""
    hoy = hoy or date.today()
    s = (so or "").lower()
    fila = None
    m = re.search(r"ubuntu\D*(\d{2}\.\d{2})", s)
    if m:
        fila = LINUX.get(("ubuntu", m.group(1)))
    m = re.search(r"debian\D*(\d{1,2})\b", s)
    if not fila and m:
        fila = LINUX.get(("debian", m.group(1)))
    if not fila:
        return {"producto": "", "version": "", "fin_soporte": None, "estado": "desconocido", "dias": None}
    prod, ver, fin = fila
    estado, dias = _estado(fin, hoy)
    return {"producto": prod, "version": ver, "fin_soporte": fin, "estado": estado, "dias": dias}


def tipo_edicion(edicion):
    """'servidor' | 'ltsc' | 'empresa' (Enterprise/Education) | 'pro' (Home/Pro y cualquier otra)."""
    e = (edicion or "").lower().replace(" ", "")
    if "server" in e:
        return "servidor"
    if "ltsc" in e or "ltsb" in e or e.endswith("enterprises") or e.endswith("enterprisesn"):
        return "ltsc"
    if "enterprise" in e or "education" in e:
        return "empresa"
    return "pro"


def build_de(texto):
    """10.0.22631 -> 22631; "22631" -> 22631; sin numero -> None."""
    m = re.search(r"(?:^|\.)(\d{4,5})(?:\.\d+)?$", (texto or "").strip())
    return int(m.group(1)) if m else None


def soporte(build, edicion, hoy=None):
    """{producto, version, fin_soporte (date|None), estado: vigente|vence_pronto|sin_soporte|desconocido, dias}."""
    hoy = hoy or date.today()
    tipo = tipo_edicion(edicion)
    fila = None
    if build:
        if tipo == "servidor":
            fila = SERVIDOR.get(build)
        elif tipo == "ltsc":
            fila = LTSC.get(build)
        elif build in CLIENTE:
            prod, ver, pro, emp = CLIENTE[build]
            fila = (prod, ver, emp if tipo == "empresa" else pro)
    if not fila:
        return {"producto": "", "version": "", "fin_soporte": None, "estado": "desconocido", "dias": None}
    prod, ver, fin = fila
    dias = (fin - hoy).days
    if dias < 0:
        estado = "sin_soporte"
    elif dias <= AVISO_DIAS:
        estado = "vence_pronto"
    else:
        estado = "vigente"
    return {"producto": prod, "version": ver, "fin_soporte": fin, "estado": estado, "dias": dias}
