# -*- coding: utf-8 -*-
from sqlalchemy import create_engine, Column, String, DateTime, Text, Integer
from sqlalchemy.orm import declarative_base, sessionmaker
from datetime import datetime

DATABASE_URL = "sqlite:///C:/AssetManager/assetmanager.db"
engine = create_engine(DATABASE_URL, connect_args={"check_same_thread": False})
SessionLocal = sessionmaker(bind=engine)
Base = declarative_base()

class Asset(Base):
    __tablename__ = "assets"
    id              = Column(String, primary_key=True)
    nombre          = Column(String, default="")
    tipo            = Column(String, default="")
    marca           = Column(String, default="")
    modelo          = Column(String, default="")
    serial          = Column(String, default="")
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
    __tablename__ = "audit_log"
    id          = Column(Integer, primary_key=True, autoincrement=True)
    timestamp   = Column(DateTime, default=datetime.utcnow)
    usuario     = Column(String, default="")
    accion      = Column(String, default="")
    entidad     = Column(String, default="")
    entidad_id  = Column(String, default="")
    detalle     = Column(Text, default="")
    ip_origen   = Column(String, default="")
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
    proyecto_id = Column(String, default="")
    responsable = Column(String, default="")

class ProyectoTarea(Base):
    __tablename__ = "proyecto_tareas"
    id            = Column(String, primary_key=True)
    proyecto_id   = Column(String, default="")
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
    proyecto_id = Column(String, default="")
    asset_id    = Column(String, default="")

Base.metadata.create_all(engine)