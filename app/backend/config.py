# -*- coding: utf-8 -*-
"""Configuracion de la app. TODO sale de variables de entorno (README §7: nada hardcodeado)."""
import os


def _req(nombre):
    v = os.getenv(nombre, "").strip()
    if not v:
        raise RuntimeError("Falta la variable de entorno obligatoria %s" % nombre)
    return v


def _lista(nombre):
    return [x.strip() for x in os.getenv(nombre, "").split(",") if x.strip()]


def _bool(nombre, default=False):
    v = os.getenv(nombre)
    if v is None or v.strip() == "":
        return default
    return v.strip().lower() in ("1", "true", "yes", "si", "on")


APP_NAME = os.getenv("APP_NAME", "inventario")
APP_VERSION = "2.0.0"

DATABASE_URL = _req("DATABASE_URL")
JWT_SECRET = _req("JWT_SECRET")
JWT_ALGORITHM = "HS256"
JWT_EXPIRE_MINUTES = int(os.getenv("JWT_EXPIRE_MINUTES", "480"))
BCRYPT_COST = max(12, int(os.getenv("BCRYPT_COST", "12")))
LOGIN_RATE_LIMIT = os.getenv("LOGIN_RATE_LIMIT", "5/minute")

# Maestro v2
MAESTRO_API_KEY = os.getenv("MAESTRO_API_KEY", "")
COMPANY_NAME = os.getenv("COMPANY_NAME", "Lisicki, Litvin & Abelovich")
COMPANY_LOGO_URL = os.getenv("COMPANY_LOGO_URL", "")
COMPANY_PRIMARY_COLOR = os.getenv("COMPANY_PRIMARY_COLOR", "#0B7285")

# Seeding
SUPERADMIN_EMAIL = "admin@llyasoc.com"

# Rutas dentro del contenedor
STORAGE_DIR = os.getenv("STORAGE_DIR", "/app/storage")
FRONTEND_DIST = os.getenv("FRONTEND_DIST", "/app/frontend_dist")
AGENTE_DIR = os.getenv("AGENTE_DIR", "/app/agente")

# CORS: vacio = mismo origen (el backend sirve el frontend), no se agrega el middleware.
CORS_ORIGINS = _lista("CORS_ORIGINS")

# Agentes de inventario (POST /api/sync y /api/sync-glpi)
SYNC_API_KEY = os.getenv("SYNC_API_KEY", "")

# Mail
SMTP_HOST = os.getenv("SMTP_HOST", "")
SMTP_PORT = int(os.getenv("SMTP_PORT", "587"))
SMTP_USER = os.getenv("SMTP_USER", "")
SMTP_PASS = os.getenv("SMTP_PASS", "")
SMTP_FROM_NAME = os.getenv("SMTP_FROM_NAME", "Inventario LLYA")
SMTP_DOMINIO = os.getenv("SMTP_DOMINIO", "")
APP_URL = os.getenv("APP_URL", "")

# Tendencias: snapshot automatico cada N dias (0 = desactivado)
SNAPSHOT_DIAS = int(os.getenv("SNAPSHOT_DIAS", "7"))
