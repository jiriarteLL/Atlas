"""Permisos por modulo y por usuario (user_modulos), como en Argos pero con nivel (ver / editar).

Siembra a cada usuario existente con los modulos equivalentes a su rol, para que con el despliegue nadie gane
ni pierda acceso. Las plantillas estan copiadas aca (no se importa auth: la migracion no debe cambiar si cambia
el codigo). Idempotente como 0002-0004: si la tabla ya existe solo siembra a los usuarios que no tengan filas
y la tabla este vacia (base creada con create_all).

Revision ID: 0005
Revises: 0004
"""
from alembic import op
import sqlalchemy as sa

revision = '0005'
down_revision = '0004'
branch_labels = None
depends_on = None

_VER = ['dashboard', 'activos', 'salud', 'impresoras', 'proyectos', 'reportes', 'tendencias', 'agente']
_EDITOR = {'dashboard': 'ver', 'activos': 'editar', 'salud': 'ver', 'impresoras': 'editar', 'proyectos': 'editar',
           'reportes': 'ver', 'tendencias': 'ver', 'agente': 'ver', 'importar': 'editar'}
PLANTILLAS = {
    'viewer': {k: 'ver' for k in _VER},
    'editor': _EDITOR,
    'admin': dict(_EDITOR, accesos='administrar', activos_eliminar='si'),
}
PLANTILLAS['superadmin'] = PLANTILLAS['admin']


def upgrade():
    con = op.get_bind()
    existentes = set(sa.inspect(con).get_table_names())
    if 'user_modulos' not in existentes:
        op.create_table(
            'user_modulos',
            sa.Column('user_id', sa.String(), nullable=False),
            sa.Column('modulo', sa.String(), nullable=False),
            sa.Column('nivel', sa.String(), nullable=False),
            sa.ForeignKeyConstraint(['user_id'], ['users.id'], ondelete='CASCADE'),
            sa.PrimaryKeyConstraint('user_id', 'modulo'),
        )
    elif con.execute(sa.text('SELECT COUNT(*) FROM user_modulos')).scalar():
        return
    tabla = sa.table('user_modulos', sa.column('user_id', sa.String()), sa.column('modulo', sa.String()),
                     sa.column('nivel', sa.String()))
    roles = con.execute(sa.text(
        'SELECT ur.user_id, r.nombre FROM user_roles ur JOIN roles r ON r.id = ur.role_id')).fetchall()
    filas = [{'user_id': uid, 'modulo': k, 'nivel': v}
             for uid, rol in roles for k, v in PLANTILLAS.get(rol, PLANTILLAS['viewer']).items()]
    if filas:
        op.bulk_insert(tabla, filas)


def downgrade():
    op.drop_table('user_modulos')
