# -*- coding: utf-8 -*-
"""Exporta las licencias del UserManager productivo a un JSON para importarlo en Atlas.

Abre la base SQLite SOLO EN LECTURA (?mode=ro): no la modifica ni la bloquea para escribir.
Tablas: licencias, asignaciones_licencias, empleados, adobe_pares, equipos_licencias.

Uso:
    python exportar_usermanager.py [--base C:\\UserManager\\usermanager.db] [--salida licencias-usermanager.json]

Despues, en Atlas: Licencias -> "Importar del UserManager (JSON)" (o importar_usermanager.py en la VM). La importacion
es idempotente (upsert por los ids del UserManager) y no pisa los costos cargados en Atlas.
El JSON lleva datos personales de la nomina (nombre, legajo, mail, centro de costo): tratarlo como confidencial y
borrarlo despues de importar.
"""
import argparse
import json
import pathlib
import sqlite3
import sys
from datetime import datetime

COLUMNAS = {
    "licencias": ("id", "nombre", "tipo", "proveedor", "plan", "costo_usd", "costo_ars", "periodicidad", "cantidad", "notas"),
    "asignaciones_licencias": ("id", "empleado_id", "licencia_id", "detalle", "fecha_desde", "fecha_hasta", "activo"),
    "empleados": ("id", "legajo", "nombre", "centro_costo", "subauxiliar", "categoria", "fecha_ingreso", "email", "sede", "estado"),
    "adobe_pares": ("id", "sector", "usuario_principal", "email_principal", "usuario_secundario", "email_secundario",
                    "imputacion", "porcentaje_imputacion", "activo"),
    "equipos_licencias": ("id", "numero", "unidad", "lider", "responsable", "email", "tipo", "estado", "activo"),
}
CLAVE_JSON = {"asignaciones_licencias": "asignaciones"}


def exportar(base):
    uri = "file:%s?mode=ro" % pathlib.Path(base).resolve().as_posix()
    con = sqlite3.connect(uri, uri=True)
    try:
        con.row_factory = sqlite3.Row
        out = {"origen": "usermanager", "version": 1, "exportado": datetime.now().isoformat(timespec="seconds")}
        for tabla, cols in COLUMNAS.items():
            existentes = {r[1] for r in con.execute("PRAGMA table_info(%s)" % tabla)}
            usar = [c for c in cols if c in existentes]
            filas = con.execute("SELECT %s FROM %s" % (", ".join(usar), tabla)).fetchall() if usar else []
            out[CLAVE_JSON.get(tabla, tabla)] = [{c: (r[c] if r[c] is not None else "") for c in usar} for r in filas]
        return out
    finally:
        con.close()


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--base", default=r"C:\UserManager\usermanager.db")
    ap.add_argument("--salida", default="licencias-usermanager.json")
    a = ap.parse_args(argv)
    if not pathlib.Path(a.base).exists():
        print("No existe la base: %s" % a.base, file=sys.stderr)
        return 2
    datos = exportar(a.base)
    pathlib.Path(a.salida).write_text(json.dumps(datos, ensure_ascii=False, indent=1), encoding="utf-8")
    print("OK %s: %s" % (a.salida, ", ".join("%s=%d" % (k, len(v)) for k, v in datos.items() if isinstance(v, list))))
    return 0


if __name__ == "__main__":
    sys.exit(main())
