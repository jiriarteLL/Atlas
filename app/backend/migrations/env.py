# -*- coding: utf-8 -*-
"""Entorno de Alembic. Usa el mismo motor y los mismos modelos que la app."""
from alembic import context

import auth  # noqa: F401  (registra users/roles/permissions en Base.metadata)
from database import Base, engine

target_metadata = Base.metadata


def run_migrations_offline():
    context.configure(url=str(engine.url), target_metadata=target_metadata, literal_binds=True,
                      render_as_batch=engine.dialect.name == "sqlite")
    with context.begin_transaction():
        context.run_migrations()


def run_migrations_online():
    conexion = context.config.attributes.get("connection")
    if conexion is not None:          # llamada desde la app (database.init_db) con una conexion abierta
        _migrar(conexion)
        return
    with engine.connect() as con:     # llamada desde la linea de comandos (alembic upgrade head)
        _migrar(con)
        con.commit()


def _migrar(con):
    # render_as_batch: SQLite no soporta ALTER de columnas; Alembic lo resuelve recreando la tabla.
    context.configure(connection=con, target_metadata=target_metadata,
                      render_as_batch=con.dialect.name == "sqlite", compare_type=True)
    with context.begin_transaction():
        context.run_migrations()


if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()
