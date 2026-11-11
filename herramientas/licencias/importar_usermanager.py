# -*- coding: utf-8 -*-
"""Importa en Atlas el JSON de exportar_usermanager.py, desde la linea de comandos (alternativa al boton de la vista).

Se corre en la VM de Atlas con las variables de C:\\Atlas\\.env cargadas (como run_atlas.py):
    C:\\Atlas\\.venv\\Scripts\\python.exe importar_usermanager.py licencias-usermanager.json [--env C:\\Atlas\\.env]
                                       [--backend C:\\Atlas\\app\\backend] [--probar]

--probar: hace todo dentro de una transaccion y la deshace al final (muestra lo que cambiaria, sin guardar).
Idempotente: upsert por los ids del UserManager; nunca pisa precios ni cupos cargados en Atlas.
"""
import argparse
import json
import os
import pathlib
import sys


def cargar_env(ruta):
    for linea in pathlib.Path(ruta).read_text(encoding="utf-8-sig").splitlines():
        linea = linea.strip()
        if linea and not linea.startswith("#") and "=" in linea:
            k, v = linea.split("=", 1)
            os.environ.setdefault(k.strip(), v.strip())


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("archivo")
    ap.add_argument("--env", default=r"C:\Atlas\.env")
    ap.add_argument("--backend", default=r"C:\Atlas\app\backend")
    ap.add_argument("--probar", action="store_true")
    a = ap.parse_args(argv)
    if a.env and pathlib.Path(a.env).exists():
        cargar_env(a.env)
    sys.path.insert(0, a.backend)
    import licencias  # noqa: E402  (despues de cargar el entorno)
    from audit import log_action  # noqa: E402
    from database import SessionLocal  # noqa: E402

    datos = json.loads(pathlib.Path(a.archivo).read_text(encoding="utf-8-sig"))
    db = SessionLocal()
    try:
        res = licencias.aplicar_usermanager(db, datos)
        if a.probar:
            db.rollback()
            print("PRUEBA (no se guardo nada):", res)
            return 0
        db.commit()
    finally:
        db.close()
    log_action("importar_usermanager.py", "importacion", "licencias", "usermanager", res)
    print("OK:", res)
    return 0


if __name__ == "__main__":
    sys.exit(main())
