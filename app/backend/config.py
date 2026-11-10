# -*- coding: utf-8 -*-
"""Configuracion de la app. TODO sale de variables de entorno (README §7: nada hardcodeado).
Los nombres siguen el .env.example del template y CONVENCIONES §6."""
import os
import re


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


def _duracion_min(nombre, default):
    """'15m', '12h', '30d' o un numero de minutos -> minutos."""
    v = (os.getenv(nombre) or default).strip().lower()
    m = re.fullmatch(r"(\d+)\s*([mhd]?)", v)
    if not m:
        raise RuntimeError("%s invalido: %r (usar 15m, 12h, 30d)" % (nombre, v))
    return int(m.group(1)) * {"": 1, "m": 1, "h": 60, "d": 1440}[m.group(2)]


def _normalizar_db_url(url):
    """El Maestro inyecta postgres://... (CONVENCIONES §2.3); SQLAlchemy necesita el driver explicito."""
    for prefijo in ("postgres://", "postgresql://"):
        if url.startswith(prefijo):
            return "postgresql+psycopg://" + url[len(prefijo):]
    return url


# Identidad (el slug es metadata.name de maestro.yaml; el Maestro lo inyecta como MAESTRO_APP_SLUG)
APP_SLUG = os.getenv("MAESTRO_APP_SLUG", "") or "atlas"
APP_VERSION = "2.0.0"  # = maestro.yaml metadata.version
APP_ENV = os.getenv("APP_ENV", "production")

DATABASE_URL = _normalizar_db_url(_req("DATABASE_URL"))

# Auth (SPEC §2.4.2 / Premisa 7: JWT corto + refresh token)
JWT_SECRET = _req("JWT_SECRET")
JWT_ALGORITHM = "HS256"  # ADR-002: JWT_SECRET es la variable que inyecta el Maestro (SPEC §2.9)
TOKEN_TTL_MIN = _duracion_min("TOKEN_TTL", "15m")
REFRESH_TOKEN_TTL_MIN = _duracion_min("REFRESH_TOKEN_TTL", "12h")
BCRYPT_COST = max(12, int(os.getenv("BCRYPT_COST", "12")))
LOGIN_RATE_LIMIT_PER_IP = int(os.getenv("LOGIN_RATE_LIMIT_PER_IP", "5"))        # por minuto
LOGIN_RATE_LIMIT_PER_EMAIL = int(os.getenv("LOGIN_RATE_LIMIT_PER_EMAIL", "10"))  # por hora
LOGIN_MAX_FALLOS = 5            # fallos seguidos antes de bloquear la cuenta
LOGIN_BLOQUEO_MIN = 15          # minutos de bloqueo
# Cookie del refresh token: nombre unico en la plataforma (MANUAL §6.4) y Secure apagable sin TLS.
COOKIE_SESION = "%s_session" % APP_SLUG
COOKIES_SEGURAS = _bool("COOKIES_SEGURAS", True)

# Maestro v2
MAESTRO_API_KEY = os.getenv("MAESTRO_API_KEY", "")
COMPANY_NAME = os.getenv("COMPANY_NAME", "Lisicki, Litvin & Abelovich")
COMPANY_LOGO_URL = os.getenv("COMPANY_LOGO_URL", "")
COMPANY_PRIMARY_COLOR = os.getenv("COMPANY_PRIMARY_COLOR", "#0B7285")

# Seeding
SUPERADMIN_EMAIL = "admin@llyasoc.com"

# Login con el usuario de Windows del dominio, como Argos (ad_auth.py). Vacio = desactivado.
# Solo funciona si la app corre en un Windows unido al dominio (en Linux/Docker queda apagado).
AD_DOMINIO = os.getenv("AD_DOMINIO", "").strip()                    # NetBIOS, p. ej. TANGO
AD_SUFIJO_UPN = os.getenv("AD_SUFIJO_UPN", "").strip().lower()      # p. ej. llasesores.corp
AD_ADMINS = {u.lower() for u in _lista("AD_ADMINS")}                # usuarios de Windows que entran como admin

# Rutas dentro del contenedor (solo lectura: el estado persistente vive en la base, CONVENCIONES §4.2)
FRONTEND_DIST = os.getenv("FRONTEND_DIST", "/app/frontend_dist")
AGENTE_DIR = os.getenv("AGENTE_DIR", "/app/agente")

# URL publica del ambiente (links de mails y de branding). Vacia = se arma con la URL del request.
APP_URL = os.getenv("APP_URL", "").rstrip("/")
# CORS: vacio = mismo origen (el backend sirve el frontend), no se agrega el middleware.
CORS_ORIGINS = _lista("CORS_ORIGINS")

# Agentes de inventario (POST /api/sync y /api/sync-glpi)
SYNC_API_KEY = os.getenv("SYNC_API_KEY", "")

# Sede de una impresora relevada por SNMP segun su red: "red/prefijo=Sede", separadas por coma; gana la
# primera que contenga la IP (poner las mas especificas primero). Vacio = la sede queda para cargar a mano.
SEDES_POR_RED = [tuple(x.split("=", 1)) for x in _lista("SEDES_POR_RED") if "=" in x]
# Aviso emergente de toner: cartuchos por debajo de este porcentaje
TONER_ALERTA_PCT = int(os.getenv("TONER_ALERTA_PCT", "10"))

# Antivirus de la empresa (Notebooks y PC): un equipo sin este producto activo cuenta como alerta.
# Se busca dentro del nombre que reporta el agente; vacio = vale cualquier antivirus activo.
AV_CORPORATIVO = os.getenv("AV_CORPORATIVO", "CrowdStrike").strip()

# Logs (CONVENCIONES §10: JSON a stdout)
LOG_LEVEL = os.getenv("LOG_LEVEL", "info")
LOG_FORMAT = os.getenv("LOG_FORMAT", "json").lower()

# Mail
SMTP_HOST = os.getenv("SMTP_HOST", "")
SMTP_PORT = int(os.getenv("SMTP_PORT", "587"))
SMTP_USER = os.getenv("SMTP_USER", "")
SMTP_PASS = os.getenv("SMTP_PASS", "")
SMTP_FROM_NAME = os.getenv("SMTP_FROM_NAME", "Atlas - LLyA")
SMTP_DOMINIO = os.getenv("SMTP_DOMINIO", "")

# Tendencias: snapshot automatico cada N dias (0 = desactivado)
SNAPSHOT_DIAS = int(os.getenv("SNAPSHOT_DIAS", "7"))

# Garantias (garantias.py): actualizacion automatica desde la pagina publica de soporte de Lenovo, dentro de la app.
# Se vuelve a consultar lo que tenga mas de GARANTIA_REFRESCO_DIAS (0 = sin actualizacion automatica; el boton
# "Actualizar desde Lenovo" sigue andando), con una pausa entre consultas y un tope por corrida (cada 6 horas).
GARANTIA_REFRESCO_DIAS = int(os.getenv("GARANTIA_REFRESCO_DIAS", "30"))
GARANTIA_PAUSA_S = float(os.getenv("GARANTIA_PAUSA_S", "2"))
GARANTIA_MAX_POR_CORRIDA = int(os.getenv("GARANTIA_MAX_POR_CORRIDA", "300"))

# ---- Fase F: ciclo de vida, actas, etiquetas QR y auditoria fisica
# URL con la que se abre Atlas desde el celular al escanear una etiqueta (el QR apunta a #activos?activo=<id>).
# Vacio = la direccion con la que se entro a Atlas (en la VM: ATLAS_URL_PUBLICA=https://<ip o nombre>:8743 en el .env)
ATLAS_URL_PUBLICA = os.getenv("ATLAS_URL_PUBLICA", "").rstrip("/")
# Vida util por tipo de equipo en meses ("Tipo=meses" separados por coma): define la renovacion sugerida
VIDA_UTIL_MESES = {k.strip(): int(v) for k, v in (x.split("=", 1) for x in _lista("VIDA_UTIL_MESES") if "=" in x)} or {
    "Notebook": 48, "CPU": 60, "Monitor": 72, "Impresora": 60, "Servidor": 60}
# Actas de entrega / devolucion / prestamo
ACTA_EMPRESA = os.getenv("ACTA_EMPRESA", "Lisicki, Litvin y Abelovich")
ACTA_CLAUSULA = os.getenv("ACTA_CLAUSULA", (
    "El/la receptor/a declara recibir los equipos detallados en buen estado de funcionamiento y se compromete a "
    "usarlos exclusivamente para tareas laborales, cuidarlos, no instalar software no autorizado ni prestarlos a "
    "terceros, y devolverlos con sus accesorios al finalizar la relacion laboral o cuando la empresa lo solicite. "
    "Cualquier rotura, perdida o robo debe informarse de inmediato a Soporte Tecnico."))
ACTA_ACCESORIOS = _lista("ACTA_ACCESORIOS") or ["Cargador", "Mouse", "Teclado", "Mochila / funda", "Auriculares",
                                                "Dock / adaptador", "Cable de red"]

# ---- Fase D: servidores y VM (servidores.py, conectores.py)
# Alerta de disco: volumenes con menos de este % libre
SERVIDOR_DISCO_ALERTA_PCT = float(os.getenv("SERVIDOR_DISCO_ALERTA_PCT", "10"))
SERVIDOR_REINICIO_DIAS = int(os.getenv("SERVIDOR_REINICIO_DIAS", "7"))      # reinicio pendiente hace mas de N dias
SERVIDOR_UPTIME_DIAS = int(os.getenv("SERVIDOR_UPTIME_DIAS", "60"))         # sin reiniciar (sin parches) hace mas de N dias
# Conectores: cada uno queda inerte mientras falte su configuracion. Las claves NUNCA van en el .env ni en la base:
# van en un archivo aparte (una sola linea) con ACL solo para SYSTEM y Administradores, en la carpeta
# "secretos" de Atlas (ver docs/conectores-servidores.md)
CONECTORES_CADA_HORAS = int(os.getenv("CONECTORES_CADA_HORAS", "6"))       # 0 = solo con el boton "Actualizar ahora"
VCENTER_URL = os.getenv("VCENTER_URL", "").strip().rstrip("/")
VCENTER_USUARIO = os.getenv("VCENTER_USUARIO", "").strip()
VCENTER_CLAVE_ARCHIVO = os.getenv("VCENTER_CLAVE_ARCHIVO", "").strip()
VCENTER_VERIFICAR_CERT = _bool("VCENTER_VERIFICAR_CERT", False)
AZURE_TENANT_ID = os.getenv("AZURE_TENANT_ID", "").strip()
AZURE_CLIENT_ID = os.getenv("AZURE_CLIENT_ID", "").strip()
AZURE_CLIENT_SECRET_ARCHIVO = os.getenv("AZURE_CLIENT_SECRET_ARCHIVO", "").strip()
AZURE_USAR_IDENTIDAD = _bool("AZURE_USAR_IDENTIDAD", False)
AZURE_SUSCRIPCIONES = _lista("AZURE_SUSCRIPCIONES")
# Redfish (controladoras de servidores fisicos: iDRAC de Dell, iLO de HPE). IDRAC_* se aceptan como alias viejos.
REDFISH_HOSTS = _lista("REDFISH_HOSTS") or _lista("IDRAC_HOSTS")
REDFISH_USUARIO = (os.getenv("REDFISH_USUARIO") or os.getenv("IDRAC_USUARIO") or "").strip()
REDFISH_CLAVE_ARCHIVO = (os.getenv("REDFISH_CLAVE_ARCHIVO") or os.getenv("IDRAC_CLAVE_ARCHIVO") or "").strip()
REDFISH_VERIFICAR_CERT = _bool("REDFISH_VERIFICAR_CERT", _bool("IDRAC_VERIFICAR_CERT", False))
