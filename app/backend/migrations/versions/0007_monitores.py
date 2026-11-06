"""Monitores (fase B): monitor_detalle, monitor_conexion (historial de PCs) y pc_monitores.

Idempotente como 0002-0006: si una tabla ya existe no se vuelve a crear.

Revision ID: 0007
Revises: 0006
"""
from alembic import op
import sqlalchemy as sa

revision = '0007'
down_revision = '0006'
branch_labels = None
depends_on = None


def upgrade():
    existentes = set(sa.inspect(op.get_bind()).get_table_names())
    if 'monitor_detalle' not in existentes:
        op.create_table(
            'monitor_detalle',
            sa.Column('asset_id', sa.String(), nullable=False),
            sa.Column('clave', sa.String(), nullable=True),
            sa.Column('fabricante', sa.String(), nullable=True),
            sa.Column('codigo_producto', sa.String(), nullable=True),
            sa.Column('pulgadas', sa.Float(), nullable=True),
            sa.Column('anio', sa.Integer(), nullable=True),
            sa.Column('semana', sa.Integer(), nullable=True),
            sa.Column('conexion', sa.String(), nullable=True),
            sa.Column('pc_id', sa.String(), nullable=True),
            sa.Column('visto', sa.DateTime(), nullable=True),
            sa.Column('actualizado', sa.DateTime(), nullable=True),
            sa.ForeignKeyConstraint(['asset_id'], ['assets.id'], ondelete='CASCADE'),
            sa.PrimaryKeyConstraint('asset_id'),
        )
        op.create_index(op.f('ix_monitor_detalle_clave'), 'monitor_detalle', ['clave'], unique=False)
        op.create_index(op.f('ix_monitor_detalle_pc_id'), 'monitor_detalle', ['pc_id'], unique=False)
    if 'monitor_conexion' not in existentes:
        op.create_table(
            'monitor_conexion',
            sa.Column('id', sa.String(), nullable=False),
            sa.Column('monitor_id', sa.String(), nullable=False),
            sa.Column('pc_id', sa.String(), nullable=True),
            sa.Column('pc_nombre', sa.String(), nullable=True),
            sa.Column('desde', sa.DateTime(), nullable=True),
            sa.Column('hasta', sa.DateTime(), nullable=True),
            sa.Column('conexion', sa.String(), nullable=True),
            sa.ForeignKeyConstraint(['monitor_id'], ['assets.id'], ondelete='CASCADE'),
            sa.PrimaryKeyConstraint('id'),
        )
        op.create_index(op.f('ix_monitor_conexion_monitor_id'), 'monitor_conexion', ['monitor_id'], unique=False)
    if 'pc_monitores' not in existentes:
        op.create_table(
            'pc_monitores',
            sa.Column('asset_id', sa.String(), nullable=False),
            sa.Column('detalle', sa.Text(), nullable=True),
            sa.Column('actualizado', sa.DateTime(), nullable=True),
            sa.ForeignKeyConstraint(['asset_id'], ['assets.id'], ondelete='CASCADE'),
            sa.PrimaryKeyConstraint('asset_id'),
        )


def downgrade():
    op.drop_table('pc_monitores')
    op.drop_index(op.f('ix_monitor_conexion_monitor_id'), table_name='monitor_conexion')
    op.drop_table('monitor_conexion')
    op.drop_index(op.f('ix_monitor_detalle_pc_id'), table_name='monitor_detalle')
    op.drop_index(op.f('ix_monitor_detalle_clave'), table_name='monitor_detalle')
    op.drop_table('monitor_detalle')
