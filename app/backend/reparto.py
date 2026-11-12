# -*- coding: utf-8 -*-
"""Reparto de costos entre dos personas y centro de costo (licencias compartidas y equipos con segundo usuario).

Una licencia o un equipo puede tener un usuario principal y uno secundario. El costo se reparte por
porcentaje_principal: vacio = 50 % si hay segundo usuario (100 % si no lo hay); el secundario paga el resto.
El centro de costo es texto libre normalizado (espacios simples y MAYUSCULAS) para que "caba 1-aud" y "CABA 1-AUD"
sean el mismo centro.
"""


def norm_centro(v):
    return " ".join(str(v or "").split()).upper()[:80]


def clave_persona(v):
    """Email o usuario de Windows en minusculas ('TANGO\\Ana' -> 'ana')."""
    s = str(v or "").strip().lower()
    if "\\" in s:
        s = s.split("\\")[-1]
    return s[:200]


def parte_local(clave):
    """'ana@llyasoc.com' -> 'ana' (para cruzar el mail con el usuario de Windows)."""
    return clave.split("@")[0] if "@" in (clave or "") else (clave or "")


def misma_persona(a, b):
    a, b = clave_persona(a), clave_persona(b)
    return bool(a and b) and (a == b or parte_local(a) == parte_local(b))


def porcentaje_efectivo(pct, hay_secundario):
    if not hay_secundario:
        return 100.0
    if pct is None:
        return 50.0
    return max(0.0, min(100.0, float(pct)))


def fracciones(pct, hay_secundario):
    """(fraccion del principal, fraccion del secundario)."""
    p = porcentaje_efectivo(pct, hay_secundario) / 100.0
    return p, (1.0 - p if hay_secundario else 0.0)
