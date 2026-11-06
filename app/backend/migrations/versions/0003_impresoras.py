"""impresoras: detalle propio de las impresoras (assets tipo Impresora), lecturas de contador y consumibles

Revision ID: 0003
Revises: 0002
Create Date: 2026-11-06 12:00:00
"""
from alembic import op
import sqlalchemy as sa

revision = '0003'
down_revision = '0002'
branch_labels = None
depends_on = None


def upgrade():
    # Idempotente como la 0002: una base creada con create_all (marcada en 0001) ya puede tener estas tablas.
    existentes = set(sa.inspect(op.get_bind()).get_table_names())
    if 'impresora_detalle' not in existentes:
        _crear_detalle()
    if 'impresora_lectura' not in existentes:
        _crear_lectura()
    if 'impresora_consumible' not in existentes:
        _crear_consumible()


def _crear_detalle():
    op.create_table('impresora_detalle',
    sa.Column('asset_id', sa.String(), nullable=False),
    sa.Column('conexion', sa.String(), nullable=True),
    sa.Column('uso', sa.String(), nullable=True),
    sa.Column('piso', sa.String(), nullable=True),
    sa.Column('mac', sa.String(), nullable=True),
    sa.Column('hostname', sa.String(), nullable=True),
    sa.Column('nombre_cola', sa.String(), nullable=True),
    sa.Column('color', sa.Boolean(), nullable=True),
    sa.Column('duplex', sa.Boolean(), nullable=True),
    sa.Column('escaner', sa.Boolean(), nullable=True),
    sa.Column('toner_modelo', sa.String(), nullable=True),
    sa.Column('tenencia', sa.String(), nullable=True),
    sa.Column('proveedor', sa.String(), nullable=True),
    sa.Column('nro_inventario', sa.String(), nullable=True),
    sa.Column('credencial_ref', sa.String(), nullable=True),
    sa.Column('notas', sa.Text(), nullable=True),
    sa.Column('actualizado', sa.DateTime(), nullable=True),
    sa.ForeignKeyConstraint(['asset_id'], ['assets.id'], ondelete='CASCADE'),
    sa.PrimaryKeyConstraint('asset_id')
    )
    op.create_index(op.f('ix_impresora_detalle_nombre_cola'), 'impresora_detalle', ['nombre_cola'], unique=False)


def _crear_lectura():
    op.create_table('impresora_lectura',
    sa.Column('id', sa.String(), nullable=False),
    sa.Column('asset_id', sa.String(), nullable=False),
    sa.Column('fecha', sa.DateTime(), nullable=True),
    sa.Column('contador_total', sa.Integer(), nullable=True),
    sa.Column('estado', sa.String(), nullable=True),
    sa.Column('error', sa.String(), nullable=True),
    sa.ForeignKeyConstraint(['asset_id'], ['assets.id'], ondelete='CASCADE'),
    sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_impresora_lectura_asset_id'), 'impresora_lectura', ['asset_id'], unique=False)
    op.create_index(op.f('ix_impresora_lectura_fecha'), 'impresora_lectura', ['fecha'], unique=False)


def _crear_consumible():
    op.create_table('impresora_consumible',
    sa.Column('asset_id', sa.String(), nullable=False),
    sa.Column('indice', sa.Integer(), nullable=False),
    sa.Column('descripcion', sa.String(), nullable=True),
    sa.Column('tipo', sa.String(), nullable=True),
    sa.Column('nivel', sa.Integer(), nullable=True),
    sa.Column('maximo', sa.Integer(), nullable=True),
    sa.Column('porcentaje', sa.Integer(), nullable=True),
    sa.Column('actualizado', sa.DateTime(), nullable=True),
    sa.ForeignKeyConstraint(['asset_id'], ['assets.id'], ondelete='CASCADE'),
    sa.PrimaryKeyConstraint('asset_id', 'indice')
    )


def downgrade():
    op.drop_table('impresora_consumible')
    op.drop_index(op.f('ix_impresora_lectura_fecha'), table_name='impresora_lectura')
    op.drop_index(op.f('ix_impresora_lectura_asset_id'), table_name='impresora_lectura')
    op.drop_table('impresora_lectura')
    op.drop_index(op.f('ix_impresora_detalle_nombre_cola'), table_name='impresora_detalle')
    op.drop_table('impresora_detalle')
