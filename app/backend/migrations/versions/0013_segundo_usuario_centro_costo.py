"""Segundo usuario y centro de costo: en las asignaciones de licencias y en los activos (asset_admin).

- licencia_asignacion: secundario, secundario_nombre, porcentaje_principal, centro_costo. Una licencia compartida por
  dos personas es UNA asignacion con segundo usuario; el costo se reparte por porcentaje_principal (vacio = 50 con
  segundo usuario, 100 sin el).
- asset_admin: usuario_secundario, usuario_secundario_nombre, porcentaje_principal, centro_costo (los carga una
  persona; el agente, GLPI, CrowdStrike y las actas no los tocan).
- licencia_compartida (pares de Adobe del UserManager) deja de usarse: sus filas pasan a la asignacion del principal
  (o a una asignacion nueva "par-<id>" si el principal no tenia una), con la imputacion como centro de costo de la
  asignacion. El % de imputacion viejo no se traslada (el reparto queda 50/50; se ajusta a mano). La tabla queda.

No toca datos existentes salvo esa conversion. Idempotente como 0002-0012.

Revision ID: 0013
Revises: 0012
"""
import uuid
from datetime import datetime

from alembic import op
import sqlalchemy as sa

revision = '0013'
down_revision = '0012'
branch_labels = None
depends_on = None

CAMPOS_ASIG = (('secundario', sa.String()), ('secundario_nombre', sa.String()),
               ('porcentaje_principal', sa.Float()), ('centro_costo', sa.String()))
CAMPOS_ADMIN = (('usuario_secundario', sa.String()), ('usuario_secundario_nombre', sa.String()),
                ('porcentaje_principal', sa.Float()), ('centro_costo', sa.String()))


def _agregar(con, tabla, campos):
    if tabla not in sa.inspect(con).get_table_names():
        return
    hay = {c['name'] for c in sa.inspect(con).get_columns(tabla)}
    for nombre, tipo in campos:
        if nombre not in hay:
            op.add_column(tabla, sa.Column(nombre, tipo, nullable=True,
                                           server_default='' if isinstance(tipo, sa.String) else None))


def _pasar_pares(con):
    tablas = set(sa.inspect(con).get_table_names())
    if 'licencia_compartida' not in tablas or 'licencia_asignacion' not in tablas:
        return
    pares = con.execute(sa.text(
        "SELECT id, producto_id, id_externo, sector, principal, principal_nombre, secundario, secundario_nombre, "
        "imputacion, activo FROM licencia_compartida WHERE producto_id IS NOT NULL")).fetchall()
    ahora = datetime.utcnow()
    for p in pares:
        if not p.principal:
            continue
        ya = con.execute(sa.text(
            "SELECT id, secundario FROM licencia_asignacion WHERE producto_id = :pr AND persona = :pe AND estado = 'activa'"),
            {'pr': p.producto_id, 'pe': p.principal}).fetchone()
        centro = (p.imputacion or '').strip().upper()
        if ya is not None:
            if not (ya.secundario or ''):
                con.execute(sa.text(
                    "UPDATE licencia_asignacion SET secundario = :s, secundario_nombre = :sn, "
                    "centro_costo = CASE WHEN COALESCE(centro_costo, '') = '' THEN :c ELSE centro_costo END WHERE id = :i"),
                    {'s': p.secundario or '', 'sn': p.secundario_nombre or '', 'c': centro, 'i': ya.id})
            continue
        ext = 'par-' + (p.id_externo or p.id)
        if con.execute(sa.text("SELECT 1 FROM licencia_asignacion WHERE id_externo = :e"), {'e': ext}).fetchone():
            continue
        activo = bool(p.activo)
        con.execute(sa.text(
            "INSERT INTO licencia_asignacion (id, producto_id, persona, nombre, origen, id_externo, detalle, desde, hasta, "
            "estado, secundario, secundario_nombre, porcentaje_principal, centro_costo) VALUES (:id, :pr, :pe, :n, :o, :e, "
            ":d, :desde, :hasta, :est, :s, :sn, NULL, :c)"),
            {'id': str(uuid.uuid4()), 'pr': p.producto_id, 'pe': p.principal, 'n': p.principal_nombre or '',
             'o': 'usermanager' if p.id_externo else 'manual', 'e': ext, 'd': p.sector or '', 'desde': ahora,
             'hasta': None if activo else ahora, 'est': 'activa' if activo else 'liberada', 's': p.secundario or '',
             'sn': p.secundario_nombre or '', 'c': centro})


def upgrade():
    con = op.get_bind()
    _agregar(con, 'licencia_asignacion', CAMPOS_ASIG)
    _agregar(con, 'asset_admin', CAMPOS_ADMIN)
    _pasar_pares(con)


def downgrade():
    con = op.get_bind()
    for tabla, campos in (('licencia_asignacion', CAMPOS_ASIG), ('asset_admin', CAMPOS_ADMIN)):
        hay = {c['name'] for c in sa.inspect(con).get_columns(tabla)}
        with op.batch_alter_table(tabla) as b:     # batch: SQLite no hace DROP COLUMN directo
            for nombre, _ in campos:
                if nombre in hay:
                    b.drop_column(nombre)
