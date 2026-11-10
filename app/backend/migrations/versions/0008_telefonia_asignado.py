"""Telefonia: campo "asignado" (a quien corresponde el interno segun la guia de internos de LLyA).

Lo carga un usuario (o la guia) y manda sobre el nombre de 3CX; la reimportacion de 3CX no lo toca.
Idempotente como 0002-0007.

Revision ID: 0008
Revises: 0007
"""
from alembic import op
import sqlalchemy as sa

revision = '0008'
down_revision = '0007'
branch_labels = None
depends_on = None


def upgrade():
    columnas = {c['name'] for c in sa.inspect(op.get_bind()).get_columns('linea_telefonica')}
    if 'asignado' not in columnas:
        op.add_column('linea_telefonica', sa.Column('asignado', sa.String(), nullable=True, server_default=''))


def downgrade():
    op.drop_column('linea_telefonica', 'asignado')
