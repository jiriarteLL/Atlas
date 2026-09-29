# -*- coding: utf-8 -*-
"""Chequeos estaticos del contrato v4 sobre el codigo del backend (README §7)."""
import pathlib
import re

BACKEND = pathlib.Path(__file__).resolve().parent.parent / "backend"
FUENTES = {p.name: p.read_text(encoding="utf-8") for p in BACKEND.glob("*.py")}


def test_no_lee_headers_x_auth():
    assert not [n for n, t in FUENTES.items() if re.search(r"x[-_]auth[-_]", t, re.I)]


def test_no_filtra_por_company_id():
    assert not [n for n, t in FUENTES.items() if "company_id" in t]


def test_sin_ips_ni_rutas_de_windows():
    patron = re.compile(r"\b(?:\d{1,3}\.){3}\d{1,3}\b|[A-Z]:[\\/]")
    hallazgos = {n: patron.findall(t) for n, t in FUENTES.items()}
    # 127./169.254. aparecen en _glpi_map como filtros de IPs de loopback/link-local.
    hallazgos = {n: [x for x in v if not x.startswith(("127.", "169.254."))] for n, v in hallazgos.items()}
    assert not {n: v for n, v in hallazgos.items() if v}


def test_sin_verify_false_ni_comparaciones_inseguras_de_claves():
    for n, t in FUENTES.items():
        assert "verify=False" not in t, n
        assert not re.search(r"(api_key|sync_key|_k)\s*[!=]=", t, re.I), n
