"""Licencias: productos, asignaciones (historial: nunca se borran), personas (nomina), licencias compartidas (pares de
Adobe), cuentas de equipo (Claude por unidad) y costos por periodo (API o manual).

Habilita el modulo de permisos "licencias" (antes "Proximamente") y lo suma a los usuarios que ya tienen modulos,
segun su rol (viewer -> ver, editor/admin/superadmin -> editar), como 0006/0010. Los pendientes siguen sin acceso.
Idempotente como 0002-0011.

Revision ID: 0012
Revises: 0011
"""
from alembic import op
import sqlalchemy as sa

revision = '0012'
down_revision = '0011'
branch_labels = None
depends_on = None

NIVEL_POR_ROL = {'viewer': 'ver', 'editor': 'editar', 'admin': 'editar', 'superadmin': 'editar'}
TABLAS = ('licencia_costo_periodo', 'licencia_cuenta_equipo', 'licencia_compartida', 'licencia_asignacion',
          'licencia_persona', 'licencia_producto')


def upgrade():
    con = op.get_bind()
    existentes = set(sa.inspect(con).get_table_names())
    if 'licencia_producto' not in existentes:
        op.create_table(
            'licencia_producto',
            sa.Column('id', sa.String(), nullable=False),
            sa.Column('proveedor', sa.String(), nullable=True),
            sa.Column('producto', sa.String(), nullable=True),
            sa.Column('tipo', sa.String(), nullable=True),
            sa.Column('plan', sa.String(), nullable=True),
            sa.Column('sku', sa.String(), nullable=True),
            sa.Column('origen', sa.String(), nullable=True),
            sa.Column('id_externo', sa.String(), nullable=True),
            sa.Column('producto_externo', sa.String(), nullable=True),
            sa.Column('cupo', sa.Integer(), nullable=True),
            sa.Column('ilimitado', sa.Boolean(), nullable=True),
            sa.Column('cupo_manual', sa.Boolean(), nullable=True),
            sa.Column('precio_usd', sa.Numeric(14, 2), nullable=True),
            sa.Column('precio_ars', sa.Numeric(16, 2), nullable=True),
            sa.Column('periodo', sa.String(), nullable=True),
            sa.Column('costo_origen', sa.String(), nullable=True),
            sa.Column('workspace', sa.String(), nullable=True),
            sa.Column('fecha_renovacion', sa.Date(), nullable=True),
            sa.Column('contrato', sa.String(), nullable=True),
            sa.Column('notas', sa.Text(), nullable=True),
            sa.Column('activo', sa.Boolean(), nullable=True),
            sa.Column('creado', sa.DateTime(), nullable=True),
            sa.Column('actualizado', sa.DateTime(), nullable=True),
            sa.PrimaryKeyConstraint('id'),
        )
        op.create_index('ix_licencia_producto_id_externo', 'licencia_producto', ['id_externo'])
    if 'licencia_asignacion' not in existentes:
        op.create_table(
            'licencia_asignacion',
            sa.Column('id', sa.String(), nullable=False),
            sa.Column('producto_id', sa.String(), sa.ForeignKey('licencia_producto.id', ondelete='CASCADE'), nullable=False),
            sa.Column('persona', sa.String(), nullable=False),
            sa.Column('nombre', sa.String(), nullable=True),
            sa.Column('origen', sa.String(), nullable=True),
            sa.Column('id_externo', sa.String(), nullable=True),
            sa.Column('detalle', sa.String(), nullable=True),
            sa.Column('desde', sa.DateTime(), nullable=True),
            sa.Column('hasta', sa.DateTime(), nullable=True),
            sa.Column('estado', sa.String(), nullable=True),
            sa.PrimaryKeyConstraint('id'),
        )
        op.create_index('ix_licencia_asignacion_producto_id', 'licencia_asignacion', ['producto_id'])
        op.create_index('ix_licencia_asignacion_persona', 'licencia_asignacion', ['persona'])
        op.create_index('ix_licencia_asignacion_id_externo', 'licencia_asignacion', ['id_externo'])
    if 'licencia_persona' not in existentes:
        op.create_table(
            'licencia_persona',
            sa.Column('persona', sa.String(), nullable=False),
            sa.Column('nombre', sa.String(), nullable=True),
            sa.Column('legajo', sa.String(), nullable=True),
            sa.Column('centro_costo', sa.String(), nullable=True),
            sa.Column('area', sa.String(), nullable=True),
            sa.Column('categoria', sa.String(), nullable=True),
            sa.Column('sede', sa.String(), nullable=True),
            sa.Column('estado_nomina', sa.String(), nullable=True),
            sa.Column('id_externo', sa.String(), nullable=True),
            sa.Column('estado_externo', sa.String(), nullable=True),
            sa.Column('cuenta_ad', sa.String(), nullable=True),
            sa.Column('actualizado', sa.DateTime(), nullable=True),
            sa.PrimaryKeyConstraint('persona'),
        )
        op.create_index('ix_licencia_persona_id_externo', 'licencia_persona', ['id_externo'])
    if 'licencia_compartida' not in existentes:
        op.create_table(
            'licencia_compartida',
            sa.Column('id', sa.String(), nullable=False),
            sa.Column('producto_id', sa.String(), sa.ForeignKey('licencia_producto.id', ondelete='CASCADE'), nullable=True),
            sa.Column('id_externo', sa.String(), nullable=True),
            sa.Column('sector', sa.String(), nullable=True),
            sa.Column('principal', sa.String(), nullable=True),
            sa.Column('principal_nombre', sa.String(), nullable=True),
            sa.Column('secundario', sa.String(), nullable=True),
            sa.Column('secundario_nombre', sa.String(), nullable=True),
            sa.Column('imputacion', sa.String(), nullable=True),
            sa.Column('porcentaje', sa.Float(), nullable=True),
            sa.Column('activo', sa.Boolean(), nullable=True),
            sa.Column('actualizado', sa.DateTime(), nullable=True),
            sa.PrimaryKeyConstraint('id'),
        )
        op.create_index('ix_licencia_compartida_producto_id', 'licencia_compartida', ['producto_id'])
        op.create_index('ix_licencia_compartida_id_externo', 'licencia_compartida', ['id_externo'])
    if 'licencia_cuenta_equipo' not in existentes:
        op.create_table(
            'licencia_cuenta_equipo',
            sa.Column('id', sa.String(), nullable=False),
            sa.Column('producto_id', sa.String(), sa.ForeignKey('licencia_producto.id', ondelete='SET NULL'), nullable=True),
            sa.Column('id_externo', sa.String(), nullable=True),
            sa.Column('numero', sa.String(), nullable=True),
            sa.Column('unidad', sa.String(), nullable=True),
            sa.Column('lider', sa.String(), nullable=True),
            sa.Column('responsable', sa.String(), nullable=True),
            sa.Column('email', sa.String(), nullable=True),
            sa.Column('tipo', sa.String(), nullable=True),
            sa.Column('estado', sa.String(), nullable=True),
            sa.Column('activo', sa.Boolean(), nullable=True),
            sa.Column('actualizado', sa.DateTime(), nullable=True),
            sa.PrimaryKeyConstraint('id'),
        )
        op.create_index('ix_licencia_cuenta_equipo_producto_id', 'licencia_cuenta_equipo', ['producto_id'])
        op.create_index('ix_licencia_cuenta_equipo_id_externo', 'licencia_cuenta_equipo', ['id_externo'])
    if 'licencia_costo_periodo' not in existentes:
        op.create_table(
            'licencia_costo_periodo',
            sa.Column('id', sa.String(), nullable=False),
            sa.Column('producto_id', sa.String(), sa.ForeignKey('licencia_producto.id', ondelete='CASCADE'), nullable=False),
            sa.Column('periodo', sa.String(), nullable=False),
            sa.Column('workspace', sa.String(), nullable=True),
            sa.Column('moneda', sa.String(), nullable=True),
            sa.Column('monto', sa.Numeric(16, 2), nullable=False),
            sa.Column('cantidad', sa.Integer(), nullable=True),
            sa.Column('origen', sa.String(), nullable=True),
            sa.Column('detalle', sa.Text(), nullable=True),
            sa.Column('actualizado', sa.DateTime(), nullable=True),
            sa.PrimaryKeyConstraint('id'),
        )
        op.create_index('ix_licencia_costo_periodo_producto_id', 'licencia_costo_periodo', ['producto_id'])
        op.create_index('ix_licencia_costo_periodo_periodo', 'licencia_costo_periodo', ['periodo'])

    if 'user_modulos' not in existentes:
        return
    ya = {uid for (uid,) in con.execute(sa.text("SELECT user_id FROM user_modulos WHERE modulo = 'licencias'"))}
    con_modulos = {uid for (uid,) in con.execute(sa.text('SELECT DISTINCT user_id FROM user_modulos'))}
    roles = dict(con.execute(sa.text(
        'SELECT ur.user_id, r.nombre FROM user_roles ur JOIN roles r ON r.id = ur.role_id')).fetchall())
    tabla = sa.table('user_modulos', sa.column('user_id', sa.String()), sa.column('modulo', sa.String()),
                     sa.column('nivel', sa.String()))
    filas = [{'user_id': uid, 'modulo': 'licencias', 'nivel': NIVEL_POR_ROL.get(rol, 'ver')}
             for uid, rol in roles.items() if uid in con_modulos and uid not in ya]
    if filas:
        op.bulk_insert(tabla, filas)


def downgrade():
    op.execute("DELETE FROM user_modulos WHERE modulo = 'licencias'")
    for t in TABLAS:
        op.drop_table(t)
