# -*- coding: utf-8 -*-
"""Migraciones con Alembic (DT-05): el esquema migrado es el de los modelos y las migraciones son reversibles."""
import os

from alembic import command
from alembic.autogenerate import compare_metadata
from alembic.config import Config
from alembic.runtime.migration import MigrationContext
from alembic.script import ScriptDirectory
from sqlalchemy import inspect

import database

INI = os.path.join(os.path.dirname(__file__), "..", "backend", "alembic.ini")


def _cfg(con):
    cfg = Config(INI)
    cfg.attributes["connection"] = con
    return cfg


def _head():
    return ScriptDirectory.from_config(Config(INI)).get_current_head()


def _version(con):
    return MigrationContext.configure(con).get_current_revision()


def test_la_base_queda_en_la_ultima_migracion():
    with database.engine.connect() as con:
        assert _version(con) == _head()


def test_el_esquema_migrado_coincide_con_los_modelos():
    """Si alguien cambia un modelo sin escribir la migracion, este test falla."""
    import auth  # noqa: F401
    with database.engine.connect() as con:
        diferencias = compare_metadata(MigrationContext.configure(con), database.Base.metadata)
    assert diferencias == []


def test_base_anterior_a_alembic_se_marca_sin_recrearse():
    """Una base creada con create_all (sin alembic_version) queda marcada en 0001 y conserva sus datos."""
    import auth  # noqa: F401
    database.Base.metadata.drop_all(database.engine)
    with database.engine.begin() as con:
        con.exec_driver_sql("DROP TABLE IF EXISTS alembic_version")
    database.Base.metadata.create_all(database.engine)
    with database.engine.begin() as con:
        con.exec_driver_sql("INSERT INTO tickets (id, titulo) VALUES ('T-PREVIO', 'dato previo')")
    database.init_db()
    with database.engine.connect() as con:
        assert _version(con) == _head()
        assert con.exec_driver_sql("SELECT titulo FROM tickets WHERE id = 'T-PREVIO'").scalar() == "dato previo"


def test_downgrade_y_upgrade_de_nuevo():
    with database.engine.begin() as con:
        command.downgrade(_cfg(con), "base")
    with database.engine.connect() as con:
        assert set(inspect(con).get_table_names()) <= {"alembic_version"}
    database.init_db()
    with database.engine.connect() as con:
        assert "users" in inspect(con).get_table_names() and _version(con) == _head()
