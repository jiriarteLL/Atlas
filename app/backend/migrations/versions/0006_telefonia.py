"""Telefonia: internos de 3CX (linea_telefonica) y telefonos vistos por DHCP sin interno.

Suma el modulo de permisos "telefonia" a los usuarios que ya tienen modulos, segun su rol (viewer -> ver,
editor/admin/superadmin -> editar), para que con el despliegue nadie pierda acceso. Los pendientes (sin
ninguna fila en user_modulos) siguen sin acceso. Idempotente como 0002-0005.

Revision ID: 0006
Revises: 0005
"""
from alembic import op
import sqlalchemy as sa

revision = '0006'
down_revision = '0005'
branch_labels = None
depends_on = None

NIVEL_POR_ROL = {'viewer': 'ver', 'editor': 'editar', 'admin': 'editar', 'superadmin': 'editar'}


def upgrade():
    con = op.get_bind()
    existentes = set(sa.inspect(con).get_table_names())
    if 'linea_telefonica' not in existentes:
        op.create_table(
            'linea_telefonica',
            sa.Column('id', sa.String(), nullable=False),
            sa.Column('interno', sa.String(), nullable=False),
            sa.Column('nombre', sa.String(), nullable=True),
            sa.Column('email', sa.String(), nullable=True),
            sa.Column('departamento', sa.String(), nullable=True),
            sa.Column('did', sa.String(), nullable=True),
            sa.Column('deshabilitado', sa.Boolean(), nullable=True),
            sa.Column('mac', sa.String(), nullable=True),
            sa.Column('modelo', sa.String(), nullable=True),
            sa.Column('tipo', sa.String(), nullable=True),
            sa.Column('tipo_manual', sa.Boolean(), nullable=True),
            sa.Column('ip', sa.String(), nullable=True),
            sa.Column('ip_origen', sa.String(), nullable=True),
            sa.Column('ip_visto', sa.DateTime(), nullable=True),
            sa.Column('hostname', sa.String(), nullable=True),
            sa.Column('sede', sa.String(), nullable=True),
            sa.Column('sede_manual', sa.Boolean(), nullable=True),
            sa.Column('piso', sa.String(), nullable=True),
            sa.Column('notas', sa.Text(), nullable=True),
            sa.Column('estado', sa.String(), nullable=True),
            sa.Column('en_3cx', sa.Boolean(), nullable=True),
            sa.Column('creado', sa.DateTime(), nullable=True),
            sa.Column('actualizado', sa.DateTime(), nullable=True),
            sa.PrimaryKeyConstraint('id'),
            sa.UniqueConstraint('interno'),
        )
        op.create_index(op.f('ix_linea_telefonica_mac'), 'linea_telefonica', ['mac'], unique=False)
    if 'telefono_sin_interno' not in existentes:
        op.create_table(
            'telefono_sin_interno',
            sa.Column('mac', sa.String(), nullable=False),
            sa.Column('ip', sa.String(), nullable=True),
            sa.Column('hostname', sa.String(), nullable=True),
            sa.Column('visto', sa.DateTime(), nullable=True),
            sa.PrimaryKeyConstraint('mac'),
        )
    if 'user_modulos' not in existentes:
        return
    ya = {uid for (uid,) in con.execute(sa.text("SELECT user_id FROM user_modulos WHERE modulo = 'telefonia'"))}
    con_modulos = {uid for (uid,) in con.execute(sa.text('SELECT DISTINCT user_id FROM user_modulos'))}
    roles = dict(con.execute(sa.text(
        'SELECT ur.user_id, r.nombre FROM user_roles ur JOIN roles r ON r.id = ur.role_id')).fetchall())
    tabla = sa.table('user_modulos', sa.column('user_id', sa.String()), sa.column('modulo', sa.String()),
                     sa.column('nivel', sa.String()))
    filas = [{'user_id': uid, 'modulo': 'telefonia', 'nivel': NIVEL_POR_ROL.get(rol, 'ver')}
             for uid, rol in roles.items() if uid in con_modulos and uid not in ya]
    if filas:
        op.bulk_insert(tabla, filas)


def downgrade():
    op.execute("DELETE FROM user_modulos WHERE modulo = 'telefonia'")
    op.drop_table('telefono_sin_interno')
    op.drop_index(op.f('ix_linea_telefonica_mac'), table_name='linea_telefonica')
    op.drop_table('linea_telefonica')
