"""Fase F: ciclo de vida (asset_admin, asset_movimiento), actas (acta, acta_item) y auditoria fisica
(auditoria_campana, auditoria_item).

Suma el modulo de permisos "auditoria" a los usuarios que ya tienen modulos, segun su rol (viewer -> ver,
editor/admin/superadmin -> editar), como 0006. Los pendientes siguen sin acceso. Idempotente como 0002-0009.

Revision ID: 0010
Revises: 0009
"""
from alembic import op
import sqlalchemy as sa

revision = '0010'
# AL MERGEAR: cambiar a '0009' (garantias, fase C). En la rama feature/atlas-fase-f la 0009 todavia no existe.
down_revision = '0009'
branch_labels = None
depends_on = None

NIVEL_POR_ROL = {'viewer': 'ver', 'editor': 'editar', 'admin': 'editar', 'superadmin': 'editar'}


def upgrade():
    con = op.get_bind()
    existentes = set(sa.inspect(con).get_table_names())
    if 'asset_admin' not in existentes:
        op.create_table(
            'asset_admin',
            sa.Column('asset_id', sa.String(), sa.ForeignKey('assets.id', ondelete='CASCADE'), nullable=False),
            sa.Column('nro_inventario', sa.String(), nullable=True),
            sa.Column('fecha_compra', sa.Date(), nullable=True),
            sa.Column('proveedor', sa.String(), nullable=True),
            sa.Column('factura', sa.String(), nullable=True),
            sa.Column('costo', sa.Float(), nullable=True),
            sa.Column('moneda', sa.String(), nullable=True),
            sa.Column('vida_util_meses', sa.Integer(), nullable=True),
            sa.Column('notas', sa.Text(), nullable=True),
            sa.Column('actualizado', sa.DateTime(), nullable=True),
            sa.PrimaryKeyConstraint('asset_id'),
        )
        op.create_index('ix_asset_admin_nro_inventario', 'asset_admin', ['nro_inventario'])
    if 'asset_movimiento' not in existentes:
        op.create_table(
            'asset_movimiento',
            sa.Column('id', sa.String(), nullable=False),
            sa.Column('asset_id', sa.String(), nullable=False),
            sa.Column('fecha', sa.DateTime(), nullable=True),
            sa.Column('tipo', sa.String(), nullable=True),
            sa.Column('estado_ant', sa.String(), nullable=True),
            sa.Column('estado_new', sa.String(), nullable=True),
            sa.Column('de_usuario', sa.String(), nullable=True),
            sa.Column('a_usuario', sa.String(), nullable=True),
            sa.Column('sede', sa.String(), nullable=True),
            sa.Column('motivo', sa.Text(), nullable=True),
            sa.Column('acta_id', sa.String(), nullable=True),
            sa.Column('hecho_por', sa.String(), nullable=True),
            sa.PrimaryKeyConstraint('id'),
        )
        op.create_index('ix_asset_movimiento_asset_id', 'asset_movimiento', ['asset_id'])
        op.create_index('ix_asset_movimiento_fecha', 'asset_movimiento', ['fecha'])
        op.create_index('ix_asset_movimiento_acta_id', 'asset_movimiento', ['acta_id'])
    if 'acta' not in existentes:
        op.create_table(
            'acta',
            sa.Column('id', sa.String(), nullable=False),
            sa.Column('numero', sa.String(), nullable=False),
            sa.Column('anio', sa.Integer(), nullable=False),
            sa.Column('secuencia', sa.Integer(), nullable=False),
            sa.Column('tipo', sa.String(), nullable=True),
            sa.Column('estado', sa.String(), nullable=True),
            sa.Column('persona', sa.String(), nullable=True),
            sa.Column('legajo', sa.String(), nullable=True),
            sa.Column('area', sa.String(), nullable=True),
            sa.Column('sede', sa.String(), nullable=True),
            sa.Column('fecha', sa.Date(), nullable=True),
            sa.Column('devolucion_prevista', sa.Date(), nullable=True),
            sa.Column('observaciones', sa.Text(), nullable=True),
            sa.Column('clausula', sa.Text(), nullable=True),
            sa.Column('firma_receptor', sa.Text(), nullable=True),
            sa.Column('firma_soporte', sa.Text(), nullable=True),
            sa.Column('firmo_soporte', sa.String(), nullable=True),
            sa.Column('escaneo_adjunto_id', sa.String(), nullable=True),
            sa.Column('creado_por', sa.String(), nullable=True),
            sa.Column('creado', sa.DateTime(), nullable=True),
            sa.Column('firmada_el', sa.DateTime(), nullable=True),
            sa.Column('anulada_el', sa.DateTime(), nullable=True),
            sa.Column('motivo_anulacion', sa.Text(), nullable=True),
            sa.PrimaryKeyConstraint('id'),
            sa.UniqueConstraint('numero'),
        )
    if 'acta_item' not in existentes:
        op.create_table(
            'acta_item',
            sa.Column('id', sa.String(), nullable=False),
            sa.Column('acta_id', sa.String(), nullable=False),
            sa.Column('asset_id', sa.String(), nullable=False),
            sa.Column('orden', sa.Integer(), nullable=True),
            sa.Column('descripcion', sa.String(), nullable=True),
            sa.Column('serial', sa.String(), nullable=True),
            sa.Column('nro_inventario', sa.String(), nullable=True),
            sa.Column('accesorios', sa.Text(), nullable=True),
            sa.PrimaryKeyConstraint('id'),
        )
        op.create_index('ix_acta_item_acta_id', 'acta_item', ['acta_id'])
        op.create_index('ix_acta_item_asset_id', 'acta_item', ['asset_id'])
    if 'auditoria_campana' not in existentes:
        op.create_table(
            'auditoria_campana',
            sa.Column('id', sa.String(), nullable=False),
            sa.Column('nombre', sa.String(), nullable=True),
            sa.Column('sede', sa.String(), nullable=True),
            sa.Column('piso', sa.String(), nullable=True),
            sa.Column('tipos', sa.String(), nullable=True),
            sa.Column('estado', sa.String(), nullable=True),
            sa.Column('creada_por', sa.String(), nullable=True),
            sa.Column('creada', sa.DateTime(), nullable=True),
            sa.Column('cerrada', sa.DateTime(), nullable=True),
            sa.Column('cerrada_por', sa.String(), nullable=True),
            sa.PrimaryKeyConstraint('id'),
        )
    if 'auditoria_item' not in existentes:
        op.create_table(
            'auditoria_item',
            sa.Column('id', sa.String(), nullable=False),
            sa.Column('campana_id', sa.String(), nullable=False),
            sa.Column('asset_id', sa.String(), nullable=True),
            sa.Column('esperado', sa.Boolean(), nullable=True),
            sa.Column('resultado', sa.String(), nullable=True),
            sa.Column('lectura', sa.String(), nullable=True),
            sa.Column('nombre', sa.String(), nullable=True),
            sa.Column('serial', sa.String(), nullable=True),
            sa.Column('tipo', sa.String(), nullable=True),
            sa.Column('usuario', sa.String(), nullable=True),
            sa.Column('sede_sistema', sa.String(), nullable=True),
            sa.Column('lugar', sa.String(), nullable=True),
            sa.Column('leido_por', sa.String(), nullable=True),
            sa.Column('leido_el', sa.DateTime(), nullable=True),
            sa.Column('movido', sa.Boolean(), nullable=True),
            sa.PrimaryKeyConstraint('id'),
        )
        op.create_index('ix_auditoria_item_campana_id', 'auditoria_item', ['campana_id'])
        op.create_index('ix_auditoria_item_asset_id', 'auditoria_item', ['asset_id'])

    if 'user_modulos' not in existentes:
        return
    ya = {uid for (uid,) in con.execute(sa.text("SELECT user_id FROM user_modulos WHERE modulo = 'auditoria'"))}
    con_modulos = {uid for (uid,) in con.execute(sa.text('SELECT DISTINCT user_id FROM user_modulos'))}
    roles = dict(con.execute(sa.text(
        'SELECT ur.user_id, r.nombre FROM user_roles ur JOIN roles r ON r.id = ur.role_id')).fetchall())
    tabla = sa.table('user_modulos', sa.column('user_id', sa.String()), sa.column('modulo', sa.String()),
                     sa.column('nivel', sa.String()))
    filas = [{'user_id': uid, 'modulo': 'auditoria', 'nivel': NIVEL_POR_ROL.get(rol, 'ver')}
             for uid, rol in roles.items() if uid in con_modulos and uid not in ya]
    if filas:
        op.bulk_insert(tabla, filas)


def downgrade():
    op.execute("DELETE FROM user_modulos WHERE modulo = 'auditoria'")
    for t in ('auditoria_item', 'auditoria_campana', 'acta_item', 'acta', 'asset_movimiento', 'asset_admin'):
        op.drop_table(t)
