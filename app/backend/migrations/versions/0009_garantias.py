"""Garantias (fase C): asset_garantia (detalle por activo) y garantia_corrida (estado/lock de la actualizacion).

Idempotente como 0002-0008: si una tabla ya existe no se vuelve a crear.

Revision ID: 0009
Revises: 0008
"""
from alembic import op
import sqlalchemy as sa

revision = '0009'
down_revision = '0008'
branch_labels = None
depends_on = None


def upgrade():
    existentes = set(sa.inspect(op.get_bind()).get_table_names())
    if 'asset_garantia' not in existentes:
        op.create_table(
            'asset_garantia',
            sa.Column('asset_id', sa.String(), nullable=False),
            sa.Column('fuente', sa.String(), nullable=True),
            sa.Column('inicio', sa.Date(), nullable=True),
            sa.Column('fin', sa.Date(), nullable=True),
            sa.Column('estado', sa.String(), nullable=True),
            sa.Column('cobertura', sa.String(), nullable=True),
            sa.Column('entrega', sa.String(), nullable=True),
            sa.Column('origen', sa.String(), nullable=True),
            sa.Column('coberturas', sa.Text(), nullable=True),
            sa.Column('proveedor', sa.String(), nullable=True),
            sa.Column('contrato', sa.String(), nullable=True),
            sa.Column('notas', sa.Text(), nullable=True),
            sa.Column('consultado', sa.DateTime(), nullable=True),
            sa.Column('error', sa.String(), nullable=True),
            sa.Column('actualizado', sa.DateTime(), nullable=True),
            sa.ForeignKeyConstraint(['asset_id'], ['assets.id'], ondelete='CASCADE'),
            sa.PrimaryKeyConstraint('asset_id'),
        )
    if 'garantia_corrida' not in existentes:
        op.create_table(
            'garantia_corrida',
            sa.Column('id', sa.Integer(), nullable=False),
            sa.Column('corriendo_hasta', sa.DateTime(), nullable=True),
            sa.Column('duenio', sa.String(), nullable=True),
            sa.Column('pedida', sa.Boolean(), nullable=True),
            sa.Column('inicio', sa.DateTime(), nullable=True),
            sa.Column('fin', sa.DateTime(), nullable=True),
            sa.Column('pendientes', sa.Integer(), nullable=True),
            sa.Column('ok', sa.Integer(), nullable=True),
            sa.Column('errores', sa.Integer(), nullable=True),
            sa.Column('mensaje', sa.String(), nullable=True),
            sa.PrimaryKeyConstraint('id'),
        )


def downgrade():
    op.drop_table('garantia_corrida')
    op.drop_table('asset_garantia')
