# -*- coding: utf-8 -*-
"""Motor de base y modelos de negocio. El motor sale de DATABASE_URL (PostgreSQL en los compose)."""
import uuid
from datetime import datetime
from sqlalchemy import create_engine, event, Boolean, Column, Date, String, DateTime, Float, ForeignKey, Text, Integer, LargeBinary
from sqlalchemy.orm import declarative_base, deferred, sessionmaker
import config

_es_sqlite = config.DATABASE_URL.startswith("sqlite")
_args = {"check_same_thread": False} if _es_sqlite else {}
engine = create_engine(config.DATABASE_URL, connect_args=_args, pool_pre_ping=True)

if _es_sqlite:
    # WAL + espera ante bloqueo: con varios agentes haciendo /api/sync a la vez, las lecturas no se
    # bloquean contra las escrituras (evita el "database is locked" que sufria la version con SQLite).
    @event.listens_for(engine, "connect")
    def _sqlite_pragmas(dbapi_con, _rec):
        cur = dbapi_con.cursor()
        cur.execute("PRAGMA journal_mode=WAL")
        cur.execute("PRAGMA busy_timeout=10000")
        cur.execute("PRAGMA synchronous=NORMAL")
        cur.close()

SessionLocal = sessionmaker(bind=engine)
Base = declarative_base()


def _uuid():
    return str(uuid.uuid4())


class Asset(Base):
    __tablename__ = "assets"
    id              = Column(String, primary_key=True)
    nombre          = Column(String, default="")
    tipo            = Column(String, default="")
    marca           = Column(String, default="")
    modelo          = Column(String, default="")
    serial          = Column(String, default="", index=True)
    estado          = Column(String, default="Activo")
    usuario         = Column(String, default="")
    usuario_alt     = Column(String, default="")
    ubicacion       = Column(String, default="")
    grupo           = Column(String, default="")
    red             = Column(String, default="")
    cpu             = Column(String, default="")
    ram             = Column(String, default="")
    disco           = Column(String, default="")
    ip              = Column(String, default="")
    so              = Column(String, default="")
    so_version      = Column(String, default="")
    so_arquitectura = Column(String, default="")
    garantia        = Column(String, default="")
    updated         = Column(DateTime, default=datetime.utcnow)
    comentarios     = Column(Text, default="")
    monitores       = Column(Text, default="")
    impresoras      = Column(Text, default="")
    software        = Column(Text, default="")
    cifrado         = Column(String, default="")
    tpm             = Column(String, default="")
    # Campos de red/identidad que aporta el agente enriquecido (equivalentes a lo que daba Falcon)
    ip_publica      = Column(String, default="")
    mac             = Column(String, default="")
    gateway         = Column(String, default="")
    ou_ad           = Column(String, default="")
    ultimo_reinicio = Column(String, default="")
    ultimo_login    = Column(String, default="")


class AssetGlpi(Base):
    """Resumen del inventario GLPI por serial (antes era una tabla creada a mano en SQLite)."""
    __tablename__ = "asset_glpi"
    serial               = Column(String, primary_key=True)
    nombre               = Column(String, default="")
    fecha                = Column(String, default="")
    antivirus            = Column(Text, default="")
    edr                  = Column(String, default="")
    bateria_salud        = Column(Integer, nullable=True)
    acceso_remoto        = Column(String, default="")
    discos               = Column(Text, default="")
    volumenes_sin_cifrar = Column(String, default="")
    office               = Column(Text, default="")
    ultimo_arranque      = Column(String, default="")
    chasis               = Column(String, default="")
    virtual              = Column(String, default="")
    bios                 = Column(String, default="")
    os_build             = Column(String, default="")
    actualizaciones      = Column(Integer, default=0)
    detalle              = Column(Text, default="")


class Historial(Base):
    __tablename__ = "historial"
    id        = Column(String, primary_key=True, default=_uuid)
    asset_id  = Column(String, nullable=False, index=True)
    fecha     = Column(DateTime, default=datetime.utcnow)
    usuario   = Column(String, default="sistema")
    campo     = Column(String, default="")
    valor_ant = Column(Text, default="")
    valor_new = Column(Text, default="")
    accion    = Column(String, default="")  # "edicion" | "sincronizacion"


class Adjunto(Base):
    """El contenido va en la base: el filesystem del contenedor es efimero (CONVENCIONES §4.2, ADR-001)."""
    __tablename__ = "adjuntos"
    id          = Column(String, primary_key=True, default=_uuid)
    asset_id    = Column(String, nullable=False, index=True)
    nombre      = Column(String, default="")
    contenido   = deferred(Column(LargeBinary, nullable=False))  # no se carga al listar
    tipo        = Column(String, default="")
    tamano      = Column(Integer, default=0)
    descripcion = Column(String, default="")
    subido_por  = Column(String, default="")
    fecha       = Column(DateTime, default=datetime.utcnow)
    activo      = Column(String, default="1")


class Snapshot(Base):
    __tablename__ = "snapshots"
    id       = Column(String, primary_key=True, default=_uuid)
    fecha    = Column(DateTime, default=datetime.utcnow, index=True)
    metrica  = Column(String, default="", index=True)
    clave    = Column(String, default="")
    valor    = Column(Integer, default=0)


class Ticket(Base):
    __tablename__ = "tickets"
    id         = Column(String, primary_key=True)
    activo     = Column(String, default="")
    titulo     = Column(String, default="")
    estado     = Column(String, default="Abierto")
    prioridad  = Column(String, default="Media")
    fecha      = Column(String, default="")
    comentario = Column(Text, default="")


class AuditLog(Base):
    """Solo INSERT: la app nunca actualiza ni borra filas de esta tabla."""
    __tablename__ = "audit_log"
    id          = Column(Integer, primary_key=True, autoincrement=True)
    timestamp   = Column(DateTime, default=datetime.utcnow, index=True)
    usuario     = Column(String, default="")
    user_id     = Column(String, default="", index=True)
    accion      = Column(String, default="")
    entidad     = Column(String, default="")
    entidad_id  = Column(String, default="")
    detalle     = Column(Text, default="")
    ip_origen   = Column(String, default="")
    user_agent  = Column(String, default="")
    request_id  = Column(String, default="")
    resultado   = Column(String, default="success")


class Proyecto(Base):
    __tablename__ = "proyectos"
    id              = Column(String, primary_key=True)
    nombre          = Column(String, default="")
    descripcion     = Column(Text, default="")
    tipo            = Column(String, default="")
    estado          = Column(String, default="Planificado")
    prioridad       = Column(String, default="Media")
    sede            = Column(String, default="")
    fecha_inicio    = Column(String, default="")
    fecha_fin_est   = Column(String, default="")
    avance          = Column(Integer, default=0)
    link_sharepoint = Column(Text, default="")
    comentarios     = Column(Text, default="")
    creado          = Column(String, default="")
    updated         = Column(String, default="")
    numero          = Column(String, default="")
    creado_por      = Column(String, default="")
    link_ticket     = Column(Text, default="")
    recursos        = Column(Text, default="")


class ProyectoResponsable(Base):
    __tablename__ = "proyecto_responsables"
    id          = Column(String, primary_key=True)
    proyecto_id = Column(String, default="", index=True)
    responsable = Column(String, default="")


class ProyectoTarea(Base):
    __tablename__ = "proyecto_tareas"
    id            = Column(String, primary_key=True)
    proyecto_id   = Column(String, default="", index=True)
    titulo        = Column(Text, default="")
    completada    = Column(String, default="0")
    estado        = Column(String, default="Pendiente")
    responsable   = Column(String, default="")
    orden         = Column(Integer, default=0)
    creado        = Column(String, default="")
    fecha_limite  = Column(String, default="")
    notas         = Column(Text, default="")
    completada_el = Column(String, default="")
    creado_por    = Column(String, default="")


class ProyectoActivo(Base):
    __tablename__ = "proyecto_activos"
    id          = Column(String, primary_key=True)
    proyecto_id = Column(String, default="", index=True)
    asset_id    = Column(String, default="")


# ---------------------------------------------------------------- impresoras
# La impresora sigue siendo un Asset tipo "Impresora" (historial, adjuntos, QR y dashboard se reusan);
# estas tablas guardan lo propio de una impresora. Las credenciales de administracion NO se guardan en Atlas:
# credencial_ref es solo una referencia de texto (p. ej. "KeePassXC - clave comun de impresoras").
class ImpresoraDetalle(Base):
    __tablename__ = "impresora_detalle"
    asset_id       = Column(String, ForeignKey("assets.id", ondelete="CASCADE"), primary_key=True)
    conexion       = Column(String, default="red")          # red | usb
    uso            = Column(String, default="compartida")   # compartida | personal
    piso           = Column(String, default="")
    mac            = Column(String, default="")
    hostname       = Column(String, default="")
    nombre_cola    = Column(String, default="", index=True)  # nombre con que la instalan las PCs
    color          = Column(Boolean, default=False)
    duplex         = Column(Boolean, default=False)
    escaner        = Column(Boolean, default=False)
    toner_modelo   = Column(String, default="")
    tenencia       = Column(String, default="")             # propia | alquilada | tercerizada | ""
    proveedor      = Column(String, default="")
    nro_inventario = Column(String, default="")
    credencial_ref = Column(String, default="")
    notas          = Column(Text, default="")
    actualizado    = Column(DateTime, default=datetime.utcnow)


class ImpresoraLectura(Base):
    """Serie temporal del contador (la llena el relevamiento SNMP, paso 2)."""
    __tablename__ = "impresora_lectura"
    id             = Column(String, primary_key=True, default=_uuid)
    asset_id       = Column(String, ForeignKey("assets.id", ondelete="CASCADE"), nullable=False, index=True)
    fecha          = Column(DateTime, default=datetime.utcnow, index=True)
    contador_total = Column(Integer, nullable=True)
    estado         = Column(String, default="")
    error          = Column(String, default="")


class ImpresoraConsumible(Base):
    """Ultimo nivel conocido de cada consumible (la llena el relevamiento SNMP, paso 2)."""
    __tablename__ = "impresora_consumible"
    asset_id    = Column(String, ForeignKey("assets.id", ondelete="CASCADE"), primary_key=True)
    indice      = Column(Integer, primary_key=True)
    descripcion = Column(String, default="")
    tipo        = Column(String, default="")
    nivel       = Column(Integer, nullable=True)
    maximo      = Column(Integer, nullable=True)
    porcentaje  = Column(Integer, nullable=True)
    actualizado = Column(DateTime, default=datetime.utcnow)


# ---------------------------------------------------------------- salud y seguridad (notebooks y PC)
# Lo manda el agente de Atlas dentro de /api/sync (campo "salud"). Una fila por equipo con la ultima foto:
# version de Windows, antivirus, parches, discos y bateria. antivirus y discos van como JSON en texto;
# av_estado y disco_estado se calculan al recibirlos para poder filtrar sin abrir el JSON.
class AssetSalud(Base):
    __tablename__ = "asset_salud"
    asset_id       = Column(String, ForeignKey("assets.id", ondelete="CASCADE"), primary_key=True)
    so_edicion     = Column(String, default="")
    so_display     = Column(String, default="")    # 23H2, 24H2...
    so_build       = Column(Integer, nullable=True)
    so_ubr         = Column(Integer, nullable=True)
    antivirus      = Column(Text, default="")      # JSON: [{nombre, activo, actualizado}]
    av_estado      = Column(String, default="")    # ok | desactualizado | desactivado | "" (sin datos)
    ultimo_parche  = Column(Date, nullable=True)
    parches_90d    = Column(Integer, nullable=True)
    discos         = Column(Text, default="")      # JSON: [{nombre, tipo, salud, desgaste, temperatura, ...}]
    disco_estado   = Column(String, default="")    # ok | riesgo | "" (sin datos)
    bateria_salud  = Column(Integer, nullable=True)  # % de la capacidad de diseno; NULL = sin bateria
    bateria_ciclos = Column(Integer, nullable=True)
    volumenes      = Column(Text, default="")      # JSON: [{letra, etiqueta, fs, tamano_gb, libre_gb, libre_pct}]
    actualizado    = Column(DateTime, default=datetime.utcnow)


# ---------------------------------------------------------------- telefonia (internos de 3CX + telefonos)
# Un registro por interno de la central 3CX (importado de la exportacion de usuarios de la consola). El telefono
# fisico (Grandstream IP o WiFi) se identifica por la MAC que trae la exportacion; la IP sale de las concesiones
# DHCP (relevamiento-dhcp). Lo administrativo (tipo, sede, piso, notas, estado) se edita a mano y no se pisa.
# Nunca se guardan PIN, claves ni otros secretos de 3CX: el importador lee solo una lista blanca de columnas.
class LineaTelefonica(Base):
    __tablename__ = "linea_telefonica"
    id            = Column(String, primary_key=True, default=_uuid)
    interno       = Column(String, nullable=False, unique=True)
    nombre        = Column(String, default="")           # el de 3CX
    asignado      = Column(String, default="")           # segun la guia de internos: manda sobre "nombre"
    email         = Column(String, default="")
    departamento  = Column(String, default="")
    did           = Column(String, default="")
    deshabilitado = Column(Boolean, default=False)       # "Disabled" en 3CX
    mac           = Column(String, default="", index=True)
    modelo        = Column(String, default="")
    tipo          = Column(String, default="")           # IP | WiFi | "" (sin equipo)
    tipo_manual   = Column(Boolean, default=False)       # lo eligio un usuario: la importacion no lo cambia
    ip            = Column(String, default="")
    ip_origen     = Column(String, default="")           # dhcp | manual
    ip_visto      = Column(DateTime, nullable=True)      # ultima concesion DHCP vista
    hostname      = Column(String, default="")
    sede          = Column(String, default="")
    sede_manual   = Column(Boolean, default=False)
    piso          = Column(String, default="")
    notas         = Column(Text, default="")
    estado        = Column(String, default="Activa")     # Activa | Deshabilitada | Baja
    en_3cx        = Column(Boolean, default=True)        # aparecio en la ultima importacion de 3CX
    creado        = Column(DateTime, default=datetime.utcnow)
    actualizado   = Column(DateTime, default=datetime.utcnow)


class TelefonoSinInterno(Base):
    """Telefono visto por DHCP (OUI de Grandstream) cuya MAC no figura en ningun interno de 3CX."""
    __tablename__ = "telefono_sin_interno"
    mac      = Column(String, primary_key=True)
    ip       = Column(String, default="")
    hostname = Column(String, default="")
    visto    = Column(DateTime, default=datetime.utcnow)


# ---------------------------------------------------------------- monitores (fase B, ver monitores.py)
# Un monitor externo con serie es un Asset tipo "Monitor"; su detalle del EDID va en monitor_detalle y las PCs
# donde estuvo conectado en monitor_conexion (desde/hasta). pc_monitores guarda la ultima lista que mando el
# agente de cada PC (incluye la pantalla de la notebook y los monitores sin serie, que no son activos).
class MonitorDetalle(Base):
    __tablename__ = "monitor_detalle"
    asset_id        = Column(String, ForeignKey("assets.id", ondelete="CASCADE"), primary_key=True)
    clave           = Column(String, default="", index=True)   # FABRICANTE|CODIGO|SERIE
    fabricante      = Column(String, default="")               # codigo PnP de 3 letras (SAM, DEL, ...)
    codigo_producto = Column(String, default="")
    pulgadas        = Column(Float, nullable=True)
    anio            = Column(Integer, nullable=True)
    semana          = Column(Integer, nullable=True)
    conexion        = Column(String, default="")               # HDMI | DisplayPort | VGA | DVI | Dock USB | ...
    pc_id           = Column(String, nullable=True, index=True)  # PC donde se lo vio por ultima vez
    visto           = Column(DateTime, nullable=True)
    actualizado     = Column(DateTime, default=datetime.utcnow)


class MonitorConexion(Base):
    __tablename__ = "monitor_conexion"
    id         = Column(String, primary_key=True, default=_uuid)
    monitor_id = Column(String, ForeignKey("assets.id", ondelete="CASCADE"), nullable=False, index=True)
    pc_id      = Column(String, default="")     # sin FK: el historial queda aunque se borre la PC
    pc_nombre  = Column(String, default="")
    desde      = Column(DateTime, default=datetime.utcnow)
    hasta      = Column(DateTime, nullable=True)
    conexion   = Column(String, default="")


class PcMonitores(Base):
    __tablename__ = "pc_monitores"
    asset_id    = Column(String, ForeignKey("assets.id", ondelete="CASCADE"), primary_key=True)
    detalle     = Column(Text, default="")      # JSON: lista normalizada que mando el agente
    actualizado = Column(DateTime, default=datetime.utcnow)


# ---------------------------------------------------------------- garantias (fase C, ver garantias.py)
class AssetGarantia(Base):
    """Garantia de un activo. fuente "lenovo" = la consulta automatica; "manual" = cargada a mano o por CSV (HP y
    otros): la consulta automatica NO la pisa. Asset.garantia (texto AAAA-MM-DD) se mantiene igual a `fin`."""
    __tablename__ = "asset_garantia"
    asset_id   = Column(String, ForeignKey("assets.id", ondelete="CASCADE"), primary_key=True)
    fuente     = Column(String, default="")       # lenovo | manual
    inicio     = Column(Date, nullable=True)
    fin        = Column(Date, nullable=True)
    estado     = Column(String, default="")       # vigente | vencida | "" (sin dato)
    cobertura  = Column(String, default="")       # la de fin mas lejano ("3 YR Onsite...")
    entrega    = Column(String, default="")       # on_site | depot | carry_in ...
    origen     = Column(String, default="")       # Factory Warranty / extension
    coberturas = Column(Text, default="")         # JSON: lista normalizada (fabrica + extensiones)
    proveedor  = Column(String, default="")
    contrato   = Column(String, default="")
    notas      = Column(Text, default="")
    consultado = Column(DateTime, nullable=True)  # ultima consulta a Lenovo (exitosa o no)
    error      = Column(String, default="")       # ultimo error de consulta; "" si salio bien
    actualizado = Column(DateTime, default=datetime.utcnow)


class GarantiaCorrida(Base):
    """Fila unica (id=1) con el estado de la actualizacion automatica. Hace de lock entre procesos: Atlas-HTTP y
    Atlas-HTTPS corren la misma app, y solo corre quien toma `corriendo_hasta` (un UPDATE condicional)."""
    __tablename__ = "garantia_corrida"
    id              = Column(Integer, primary_key=True)
    corriendo_hasta = Column(DateTime, nullable=True)   # lease: vencido = libre
    duenio          = Column(String, default="")
    pedida          = Column(Boolean, default=False)    # alguien apreto "Actualizar desde Lenovo"
    inicio          = Column(DateTime, nullable=True)   # ultima corrida
    fin             = Column(DateTime, nullable=True)
    pendientes      = Column(Integer, default=0)
    ok              = Column(Integer, default=0)
    errores         = Column(Integer, default=0)
    mensaje         = Column(String, default="")


# ---------------------------------------------------------------- servidores y VM (fase D, ver servidores.py)
class AssetServidor(Base):
    """Ultima foto del bloque "servidor" que manda el agente (solo servidores Windows)."""
    __tablename__ = "asset_servidor"
    asset_id            = Column(String, ForeignKey("assets.id", ondelete="CASCADE"), primary_key=True)
    roles               = Column(Text, default="")        # JSON: [{nombre, servicios: [..]}]
    uptime_dias         = Column(Float, nullable=True)
    reinicio_pendiente  = Column(Boolean, default=False)
    reinicio_motivos    = Column(Text, default="")        # JSON: ["Windows Update", ...]
    reinicio_desde      = Column(DateTime, nullable=True)  # primera vez que se lo vio pendiente (para la alerta > 7 dias)
    servicios_detenidos = Column(Text, default="")        # JSON: [{nombre, display}]
    sql                 = Column(Text, default="")        # JSON: [{instancia, estado}]
    iis                 = Column(Text, default="")        # JSON: [{nombre, estado, bindings: [..]}]
    controlador_dominio = Column(Boolean, default=False)
    hyperv_vms          = Column(Text, default="")        # JSON: [{nombre, estado, cpu, ram_gb}] ("" = no es host)
    actualizado         = Column(DateTime, default=datetime.utcnow)


class AssetExterno(Base):
    """Lo que dice de un activo una fuente externa (vcenter | azure | idrac). `creado` = el activo lo dio de alta el
    conector (VM sin agente, host ESXi): si despues aparece el agente con la misma serie, se unifica solo."""
    __tablename__ = "asset_externo"
    asset_id    = Column(String, ForeignKey("assets.id", ondelete="CASCADE"), primary_key=True)
    fuente      = Column(String, primary_key=True)
    clave       = Column(String, default="", index=True)   # id en la fuente (moid de vCenter, id de Azure, host iDRAC)
    datos       = Column(Text, default="")                  # JSON normalizado (sin secretos)
    creado      = Column(Boolean, default=False)
    actualizado = Column(DateTime, default=datetime.utcnow)


class ConectorCorrida(Base):
    """Estado y lease de cada conector (una fila por conector). Mismo mecanismo que garantia_corrida."""
    __tablename__ = "conector_corrida"
    conector        = Column(String, primary_key=True)     # vcenter | azure | idrac
    corriendo_hasta = Column(DateTime, nullable=True)
    duenio          = Column(String, default="")
    pedida          = Column(Boolean, default=False)
    inicio          = Column(DateTime, nullable=True)
    fin             = Column(DateTime, nullable=True)
    ok              = Column(Boolean, nullable=True)
    elementos       = Column(Integer, default=0)
    mensaje         = Column(String, default="")


def init_db():
    """Lleva la base a la ultima migracion de Alembic (idempotente; corre en cada arranque).

    Una base creada con create_all antes de adoptar Alembic (tiene tablas pero no alembic_version) se marca
    como 0001 sin recrear nada, y desde ahi se aplican las migraciones siguientes.
    """
    import os
    import auth  # noqa: F401  (registra los modelos de auth en Base)
    from alembic import command
    from alembic.config import Config
    from sqlalchemy import inspect

    cfg = Config(os.path.join(os.path.dirname(os.path.abspath(__file__)), "alembic.ini"))
    with engine.begin() as con:
        cfg.attributes["connection"] = con
        tablas = inspect(con).get_table_names()
        if "users" in tablas and "alembic_version" not in tablas:
            command.stamp(cfg, "0001")
        command.upgrade(cfg, "head")
