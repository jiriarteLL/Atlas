"""Fase D: servidores y VM (asset_servidor, asset_externo, conector_corrida) y volumenes en asset_salud.

Suma el modulo de permisos "servidores" (solo "ver") a los usuarios que ya tienen modulos, como 0006/0010.
Los pendientes siguen sin acceso. Idempotente como 0002-0010.

Revision ID: 0011
Revises: 0010
"""
from alembic import op
import sqlalchemy as sa

revision = '0011'
down_revision = '0010'
branch_labels = None
depends_on = None


def upgrade():
    con = op.get_bind()
    insp = sa.inspect(con)
    existentes = set(insp.get_table_names())
    if 'asset_salud' in existentes and 'volumenes' not in {c['name'] for c in insp.get_columns('asset_salud')}:
        op.add_column('asset_salud', sa.Column('volumenes', sa.Text(), nullable=True, server_default=''))
    if 'asset_servidor' not in existentes:
        op.create_table(
            'asset_servidor',
            sa.Column('asset_id', sa.String(), sa.ForeignKey('assets.id', ondelete='CASCADE'), nullable=False),
            sa.Column('roles', sa.Text(), nullable=True),
            sa.Column('uptime_dias', sa.Float(), nullable=True),
            sa.Column('reinicio_pendiente', sa.Boolean(), nullable=True),
            sa.Column('reinicio_motivos', sa.Text(), nullable=True),
            sa.Column('reinicio_desde', sa.DateTime(), nullable=True),
            sa.Column('servicios_detenidos', sa.Text(), nullable=True),
            sa.Column('sql', sa.Text(), nullable=True),
            sa.Column('iis', sa.Text(), nullable=True),
            sa.Column('controlador_dominio', sa.Boolean(), nullable=True),
            sa.Column('hyperv_vms', sa.Text(), nullable=True),
            sa.Column('actualizado', sa.DateTime(), nullable=True),
            sa.PrimaryKeyConstraint('asset_id'),
        )
    if 'asset_externo' not in existentes:
        op.create_table(
            'asset_externo',
            sa.Column('asset_id', sa.String(), sa.ForeignKey('assets.id', ondelete='CASCADE'), nullable=False),
            sa.Column('fuente', sa.String(), nullable=False),
            sa.Column('clave', sa.String(), nullable=True),
            sa.Column('datos', sa.Text(), nullable=True),
            sa.Column('creado', sa.Boolean(), nullable=True),
            sa.Column('actualizado', sa.DateTime(), nullable=True),
            sa.PrimaryKeyConstraint('asset_id', 'fuente'),
        )
        op.create_index('ix_asset_externo_clave', 'asset_externo', ['clave'])
    if 'conector_corrida' not in existentes:
        op.create_table(
            'conector_corrida',
            sa.Column('conector', sa.String(), nullable=False),
            sa.Column('corriendo_hasta', sa.DateTime(), nullable=True),
            sa.Column('duenio', sa.String(), nullable=True),
            sa.Column('pedida', sa.Boolean(), nullable=True),
            sa.Column('inicio', sa.DateTime(), nullable=True),
            sa.Column('fin', sa.DateTime(), nullable=True),
            sa.Column('ok', sa.Boolean(), nullable=True),
            sa.Column('elementos', sa.Integer(), nullable=True),
            sa.Column('mensaje', sa.String(), nullable=True),
            sa.PrimaryKeyConstraint('conector'),
        )

    if 'user_modulos' not in existentes:
        return
    ya = {uid for (uid,) in con.execute(sa.text("SELECT user_id FROM user_modulos WHERE modulo = 'servidores'"))}
    con_modulos = {uid for (uid,) in con.execute(sa.text('SELECT DISTINCT user_id FROM user_modulos'))}
    tabla = sa.table('user_modulos', sa.column('user_id', sa.String()), sa.column('modulo', sa.String()),
                     sa.column('nivel', sa.String()))
    filas = [{'user_id': uid, 'modulo': 'servidores', 'nivel': 'ver'} for uid in con_modulos if uid not in ya]
    if filas:
        op.bulk_insert(tabla, filas)


def downgrade():
    op.execute("DELETE FROM user_modulos WHERE modulo = 'servidores'")
    for t in ('conector_corrida', 'asset_externo', 'asset_servidor'):
        op.drop_table(t)
    op.drop_column('asset_salud', 'volumenes')
