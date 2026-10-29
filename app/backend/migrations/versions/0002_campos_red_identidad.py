"""assets: campos de red e identidad del agente enriquecido (ip publica, mac, gateway, OU AD, reinicio, login)

Revision ID: 0002
Revises: 0001
Create Date: 2026-10-29 19:40:00
"""
from alembic import op
import sqlalchemy as sa

revision = '0002'
down_revision = '0001'
branch_labels = None
depends_on = None

_COLS = ("ip_publica", "mac", "gateway", "ou_ad", "ultimo_reinicio", "ultimo_login")


def upgrade():
    existentes = {c["name"] for c in sa.inspect(op.get_bind()).get_columns("assets")}
    with op.batch_alter_table("assets", schema=None) as batch_op:
        for col in _COLS:
            if col not in existentes:
                batch_op.add_column(sa.Column(col, sa.String(), nullable=True))


def downgrade():
    with op.batch_alter_table("assets", schema=None) as batch_op:
        for col in _COLS:
            batch_op.drop_column(col)
