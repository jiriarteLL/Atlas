"""Salud y seguridad de notebooks y PC: asset_salud (Windows, antivirus, parches, discos, bateria).

Idempotente como 0002/0003: si la tabla ya existe no se vuelve a crear.

Revision ID: 0004
Revises: 0003
"""
from alembic import op
import sqlalchemy as sa

revision = '0004'
down_revision = '0003'
branch_labels = None
depends_on = None


def upgrade():
    existentes = set(sa.inspect(op.get_bind()).get_table_names())
    if 'asset_salud' in existentes:
        return
    op.create_table(
        'asset_salud',
        sa.Column('asset_id', sa.String(), nullable=False),
        sa.Column('so_edicion', sa.String(), nullable=True),
        sa.Column('so_display', sa.String(), nullable=True),
        sa.Column('so_build', sa.Integer(), nullable=True),
        sa.Column('so_ubr', sa.Integer(), nullable=True),
        sa.Column('antivirus', sa.Text(), nullable=True),
        sa.Column('av_estado', sa.String(), nullable=True),
        sa.Column('ultimo_parche', sa.Date(), nullable=True),
        sa.Column('parches_90d', sa.Integer(), nullable=True),
        sa.Column('discos', sa.Text(), nullable=True),
        sa.Column('disco_estado', sa.String(), nullable=True),
        sa.Column('bateria_salud', sa.Integer(), nullable=True),
        sa.Column('bateria_ciclos', sa.Integer(), nullable=True),
        sa.Column('actualizado', sa.DateTime(), nullable=True),
        sa.ForeignKeyConstraint(['asset_id'], ['assets.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('asset_id'),
    )


def downgrade():
    op.drop_table('asset_salud')
