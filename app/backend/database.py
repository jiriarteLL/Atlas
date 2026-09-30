# -*- coding: utf-8 -*-
"""Motor de base y modelos de negocio. El motor sale de DATABASE_URL (PostgreSQL en los compose)."""
import uuid
from datetime import datetime
from sqlalchemy import create_engine, Column, String, DateTime, Text, Integer, LargeBinary
from sqlalchemy.orm import declarative_base, deferred, sessionmaker
import config

_args = {"check_same_thread": False} if config.DATABASE_URL.startswith("sqlite") else {}
engine = create_engine(config.DATABASE_URL, connect_args=_args, pool_pre_ping=True)
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
