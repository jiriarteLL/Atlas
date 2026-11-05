# -*- coding: utf-8 -*-
"""Lanzador de Atlas en la VM de Azure (LLAZSVRAPP01) bajo NSSM.

Uso:  python run_atlas.py http    -> puerto 8700; antes migra la base (Alembic) y siembra el superadmin
      python run_atlas.py https   -> puerto 8743 con el certificado de C:\\Atlas\\certs (solo sirve)
"""
import os
import subprocess
import sys

RAIZ = r"C:\Atlas"
BACK = os.path.join(RAIZ, "app", "backend")

for linea in open(os.path.join(RAIZ, ".env"), encoding="utf-8"):
    linea = linea.strip()
    if linea and not linea.startswith("#") and "=" in linea:
        k, v = linea.split("=", 1)
        os.environ[k] = v
os.chdir(BACK)

modo = (sys.argv[1] if len(sys.argv) > 1 else "http").lower()
cmd = [sys.executable, "-m", "uvicorn", "main:app", "--app-dir", BACK, "--host", "0.0.0.0",
       "--proxy-headers", "--forwarded-allow-ips", os.getenv("FORWARDED_ALLOW_IPS", "127.0.0.1")]
if modo == "https":
    cmd += ["--port", "8743",
            "--ssl-certfile", os.path.join(RAIZ, "certs", "atlas.pem"),
            "--ssl-keyfile", os.path.join(RAIZ, "certs", "atlas-key.pem")]
else:
    subprocess.run([sys.executable, "-c", "import database; database.init_db()"], check=True)
    subprocess.run([sys.executable, "seed.py"], check=True)
    cmd += ["--port", "8700"]
sys.exit(subprocess.call(cmd))
