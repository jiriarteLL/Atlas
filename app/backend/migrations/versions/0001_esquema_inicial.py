"""esquema inicial (v2.0.0): todas las tablas + trigger que hace inmutable el audit_log

Revision ID: 0001
Revises: (ninguna)
Create Date: 2026-09-30 15:05:38.750258
"""
from alembic import op
import sqlalchemy as sa

# audit_log solo INSERT (BEST_PRACTICES §2.8): cualquier UPDATE o DELETE falla en la base.
_TRIGGERS = {
    "postgresql": [
        """CREATE OR REPLACE FUNCTION audit_log_inmutable() RETURNS trigger AS $$
           BEGIN RAISE EXCEPTION 'audit_log es solo INSERT'; END; $$ LANGUAGE plpgsql""",
        """CREATE OR REPLACE TRIGGER audit_log_sin_update BEFORE UPDATE OR DELETE ON audit_log
           FOR EACH ROW EXECUTE FUNCTION audit_log_inmutable()""",
    ],
    "sqlite": [
        """CREATE TRIGGER IF NOT EXISTS audit_log_sin_update BEFORE UPDATE ON audit_log
           BEGIN SELECT RAISE(ABORT, 'audit_log es solo INSERT'); END""",
        """CREATE TRIGGER IF NOT EXISTS audit_log_sin_delete BEFORE DELETE ON audit_log
           BEGIN SELECT RAISE(ABORT, 'audit_log es solo INSERT'); END""",
    ],
}


revision = '0001'
down_revision = None
branch_labels = None
depends_on = None


def upgrade():
    op.create_table('adjuntos',
    sa.Column('id', sa.String(), nullable=False),
    sa.Column('asset_id', sa.String(), nullable=False),
    sa.Column('nombre', sa.String(), nullable=True),
    sa.Column('contenido', sa.LargeBinary(), nullable=False),
    sa.Column('tipo', sa.String(), nullable=True),
    sa.Column('tamano', sa.Integer(), nullable=True),
    sa.Column('descripcion', sa.String(), nullable=True),
    sa.Column('subido_por', sa.String(), nullable=True),
    sa.Column('fecha', sa.DateTime(), nullable=True),
    sa.Column('activo', sa.String(), nullable=True),
    sa.PrimaryKeyConstraint('id')
    )
    with op.batch_alter_table('adjuntos', schema=None) as batch_op:
        batch_op.create_index(batch_op.f('ix_adjuntos_asset_id'), ['asset_id'], unique=False)

    op.create_table('asset_glpi',
    sa.Column('serial', sa.String(), nullable=False),
    sa.Column('nombre', sa.String(), nullable=True),
    sa.Column('fecha', sa.String(), nullable=True),
    sa.Column('antivirus', sa.Text(), nullable=True),
    sa.Column('edr', sa.String(), nullable=True),
    sa.Column('bateria_salud', sa.Integer(), nullable=True),
    sa.Column('acceso_remoto', sa.String(), nullable=True),
    sa.Column('discos', sa.Text(), nullable=True),
    sa.Column('volumenes_sin_cifrar', sa.String(), nullable=True),
    sa.Column('office', sa.Text(), nullable=True),
    sa.Column('ultimo_arranque', sa.String(), nullable=True),
    sa.Column('chasis', sa.String(), nullable=True),
    sa.Column('virtual', sa.String(), nullable=True),
    sa.Column('bios', sa.String(), nullable=True),
    sa.Column('os_build', sa.String(), nullable=True),
    sa.Column('actualizaciones', sa.Integer(), nullable=True),
    sa.Column('detalle', sa.Text(), nullable=True),
    sa.PrimaryKeyConstraint('serial')
    )
    op.create_table('assets',
    sa.Column('id', sa.String(), nullable=False),
    sa.Column('nombre', sa.String(), nullable=True),
    sa.Column('tipo', sa.String(), nullable=True),
    sa.Column('marca', sa.String(), nullable=True),
    sa.Column('modelo', sa.String(), nullable=True),
    sa.Column('serial', sa.String(), nullable=True),
    sa.Column('estado', sa.String(), nullable=True),
    sa.Column('usuario', sa.String(), nullable=True),
    sa.Column('usuario_alt', sa.String(), nullable=True),
    sa.Column('ubicacion', sa.String(), nullable=True),
    sa.Column('grupo', sa.String(), nullable=True),
    sa.Column('red', sa.String(), nullable=True),
    sa.Column('cpu', sa.String(), nullable=True),
    sa.Column('ram', sa.String(), nullable=True),
    sa.Column('disco', sa.String(), nullable=True),
    sa.Column('ip', sa.String(), nullable=True),
    sa.Column('so', sa.String(), nullable=True),
    sa.Column('so_version', sa.String(), nullable=True),
    sa.Column('so_arquitectura', sa.String(), nullable=True),
    sa.Column('garantia', sa.String(), nullable=True),
    sa.Column('updated', sa.DateTime(), nullable=True),
    sa.Column('comentarios', sa.Text(), nullable=True),
    sa.Column('monitores', sa.Text(), nullable=True),
    sa.Column('impresoras', sa.Text(), nullable=True),
    sa.Column('software', sa.Text(), nullable=True),
    sa.Column('cifrado', sa.String(), nullable=True),
    sa.Column('tpm', sa.String(), nullable=True),
    sa.PrimaryKeyConstraint('id')
    )
    with op.batch_alter_table('assets', schema=None) as batch_op:
        batch_op.create_index(batch_op.f('ix_assets_serial'), ['serial'], unique=False)

    op.create_table('audit_log',
    sa.Column('id', sa.Integer(), autoincrement=True, nullable=False),
    sa.Column('timestamp', sa.DateTime(), nullable=True),
    sa.Column('usuario', sa.String(), nullable=True),
    sa.Column('user_id', sa.String(), nullable=True),
    sa.Column('accion', sa.String(), nullable=True),
    sa.Column('entidad', sa.String(), nullable=True),
    sa.Column('entidad_id', sa.String(), nullable=True),
    sa.Column('detalle', sa.Text(), nullable=True),
    sa.Column('ip_origen', sa.String(), nullable=True),
    sa.Column('user_agent', sa.String(), nullable=True),
    sa.Column('request_id', sa.String(), nullable=True),
    sa.Column('resultado', sa.String(), nullable=True),
    sa.PrimaryKeyConstraint('id')
    )
    with op.batch_alter_table('audit_log', schema=None) as batch_op:
        batch_op.create_index(batch_op.f('ix_audit_log_timestamp'), ['timestamp'], unique=False)
        batch_op.create_index(batch_op.f('ix_audit_log_user_id'), ['user_id'], unique=False)

    op.create_table('historial',
    sa.Column('id', sa.String(), nullable=False),
    sa.Column('asset_id', sa.String(), nullable=False),
    sa.Column('fecha', sa.DateTime(), nullable=True),
    sa.Column('usuario', sa.String(), nullable=True),
    sa.Column('campo', sa.String(), nullable=True),
    sa.Column('valor_ant', sa.Text(), nullable=True),
    sa.Column('valor_new', sa.Text(), nullable=True),
    sa.Column('accion', sa.String(), nullable=True),
    sa.PrimaryKeyConstraint('id')
    )
    with op.batch_alter_table('historial', schema=None) as batch_op:
        batch_op.create_index(batch_op.f('ix_historial_asset_id'), ['asset_id'], unique=False)

    op.create_table('permissions',
    sa.Column('id', sa.String(), nullable=False),
    sa.Column('codigo', sa.String(), nullable=False),
    sa.Column('descripcion', sa.String(), nullable=True),
    sa.PrimaryKeyConstraint('id'),
    sa.UniqueConstraint('codigo')
    )
    op.create_table('proyecto_activos',
    sa.Column('id', sa.String(), nullable=False),
    sa.Column('proyecto_id', sa.String(), nullable=True),
    sa.Column('asset_id', sa.String(), nullable=True),
    sa.PrimaryKeyConstraint('id')
    )
    with op.batch_alter_table('proyecto_activos', schema=None) as batch_op:
        batch_op.create_index(batch_op.f('ix_proyecto_activos_proyecto_id'), ['proyecto_id'], unique=False)

    op.create_table('proyecto_responsables',
    sa.Column('id', sa.String(), nullable=False),
    sa.Column('proyecto_id', sa.String(), nullable=True),
    sa.Column('responsable', sa.String(), nullable=True),
    sa.PrimaryKeyConstraint('id')
    )
    with op.batch_alter_table('proyecto_responsables', schema=None) as batch_op:
        batch_op.create_index(batch_op.f('ix_proyecto_responsables_proyecto_id'), ['proyecto_id'], unique=False)

    op.create_table('proyecto_tareas',
    sa.Column('id', sa.String(), nullable=False),
    sa.Column('proyecto_id', sa.String(), nullable=True),
    sa.Column('titulo', sa.Text(), nullable=True),
    sa.Column('completada', sa.String(), nullable=True),
    sa.Column('estado', sa.String(), nullable=True),
    sa.Column('responsable', sa.String(), nullable=True),
    sa.Column('orden', sa.Integer(), nullable=True),
    sa.Column('creado', sa.String(), nullable=True),
    sa.Column('fecha_limite', sa.String(), nullable=True),
    sa.Column('notas', sa.Text(), nullable=True),
    sa.Column('completada_el', sa.String(), nullable=True),
    sa.Column('creado_por', sa.String(), nullable=True),
    sa.PrimaryKeyConstraint('id')
    )
    with op.batch_alter_table('proyecto_tareas', schema=None) as batch_op:
        batch_op.create_index(batch_op.f('ix_proyecto_tareas_proyecto_id'), ['proyecto_id'], unique=False)

    op.create_table('proyectos',
    sa.Column('id', sa.String(), nullable=False),
    sa.Column('nombre', sa.String(), nullable=True),
    sa.Column('descripcion', sa.Text(), nullable=True),
    sa.Column('tipo', sa.String(), nullable=True),
    sa.Column('estado', sa.String(), nullable=True),
    sa.Column('prioridad', sa.String(), nullable=True),
    sa.Column('sede', sa.String(), nullable=True),
    sa.Column('fecha_inicio', sa.String(), nullable=True),
    sa.Column('fecha_fin_est', sa.String(), nullable=True),
    sa.Column('avance', sa.Integer(), nullable=True),
    sa.Column('link_sharepoint', sa.Text(), nullable=True),
    sa.Column('comentarios', sa.Text(), nullable=True),
    sa.Column('creado', sa.String(), nullable=True),
    sa.Column('updated', sa.String(), nullable=True),
    sa.Column('numero', sa.String(), nullable=True),
    sa.Column('creado_por', sa.String(), nullable=True),
    sa.Column('link_ticket', sa.Text(), nullable=True),
    sa.Column('recursos', sa.Text(), nullable=True),
    sa.PrimaryKeyConstraint('id')
    )
    op.create_table('revoked_tokens',
    sa.Column('jti', sa.String(), nullable=False),
    sa.Column('expira', sa.DateTime(), nullable=False),
    sa.PrimaryKeyConstraint('jti')
    )
    op.create_table('roles',
    sa.Column('id', sa.String(), nullable=False),
    sa.Column('nombre', sa.String(), nullable=False),
    sa.Column('descripcion', sa.String(), nullable=True),
    sa.PrimaryKeyConstraint('id'),
    sa.UniqueConstraint('nombre')
    )
    op.create_table('snapshots',
    sa.Column('id', sa.String(), nullable=False),
    sa.Column('fecha', sa.DateTime(), nullable=True),
    sa.Column('metrica', sa.String(), nullable=True),
    sa.Column('clave', sa.String(), nullable=True),
    sa.Column('valor', sa.Integer(), nullable=True),
    sa.PrimaryKeyConstraint('id')
    )
    with op.batch_alter_table('snapshots', schema=None) as batch_op:
        batch_op.create_index(batch_op.f('ix_snapshots_fecha'), ['fecha'], unique=False)
        batch_op.create_index(batch_op.f('ix_snapshots_metrica'), ['metrica'], unique=False)

    op.create_table('tickets',
    sa.Column('id', sa.String(), nullable=False),
    sa.Column('activo', sa.String(), nullable=True),
    sa.Column('titulo', sa.String(), nullable=True),
    sa.Column('estado', sa.String(), nullable=True),
    sa.Column('prioridad', sa.String(), nullable=True),
    sa.Column('fecha', sa.String(), nullable=True),
    sa.Column('comentario', sa.Text(), nullable=True),
    sa.PrimaryKeyConstraint('id')
    )
    op.create_table('users',
    sa.Column('id', sa.String(), nullable=False),
    sa.Column('username', sa.String(), nullable=False),
    sa.Column('email', sa.String(), nullable=True),
    sa.Column('password_hash', sa.String(), nullable=False),
    sa.Column('nombre', sa.String(), nullable=True),
    sa.Column('activo', sa.String(), nullable=True),
    sa.Column('created', sa.DateTime(), nullable=True),
    sa.Column('last_login_at', sa.DateTime(), nullable=True),
    sa.Column('sesiones_desde', sa.DateTime(), nullable=True),
    sa.Column('intentos_fallidos', sa.Integer(), nullable=True),
    sa.Column('bloqueado_hasta', sa.DateTime(), nullable=True),
    sa.Column('debe_cambiar_password', sa.Boolean(), nullable=True),
    sa.PrimaryKeyConstraint('id'),
    sa.UniqueConstraint('email'),
    sa.UniqueConstraint('username')
    )
    op.create_table('refresh_tokens',
    sa.Column('id', sa.String(), nullable=False),
    sa.Column('user_id', sa.String(), nullable=False),
    sa.Column('token_hash', sa.String(), nullable=False),
    sa.Column('creado', sa.DateTime(), nullable=True),
    sa.Column('expira', sa.DateTime(), nullable=False),
    sa.Column('revocado', sa.Boolean(), nullable=True),
    sa.ForeignKeyConstraint(['user_id'], ['users.id'], ),
    sa.PrimaryKeyConstraint('id'),
    sa.UniqueConstraint('token_hash')
    )
    with op.batch_alter_table('refresh_tokens', schema=None) as batch_op:
        batch_op.create_index(batch_op.f('ix_refresh_tokens_user_id'), ['user_id'], unique=False)

    op.create_table('role_permissions',
    sa.Column('role_id', sa.String(), nullable=False),
    sa.Column('permission_id', sa.String(), nullable=False),
    sa.ForeignKeyConstraint(['permission_id'], ['permissions.id'], ),
    sa.ForeignKeyConstraint(['role_id'], ['roles.id'], ),
    sa.PrimaryKeyConstraint('role_id', 'permission_id')
    )
    op.create_table('user_roles',
    sa.Column('user_id', sa.String(), nullable=False),
    sa.Column('role_id', sa.String(), nullable=False),
    sa.ForeignKeyConstraint(['role_id'], ['roles.id'], ),
    sa.ForeignKeyConstraint(['user_id'], ['users.id'], ),
    sa.PrimaryKeyConstraint('user_id', 'role_id')
    )
    for sql in _TRIGGERS.get(op.get_bind().dialect.name, []):
        op.execute(sql)


def downgrade():
    if op.get_bind().dialect.name == "postgresql":
        op.execute("DROP TRIGGER IF EXISTS audit_log_sin_update ON audit_log")
        op.execute("DROP FUNCTION IF EXISTS audit_log_inmutable()")
    op.drop_table('user_roles')
    op.drop_table('role_permissions')
    with op.batch_alter_table('refresh_tokens', schema=None) as batch_op:
        batch_op.drop_index(batch_op.f('ix_refresh_tokens_user_id'))

    op.drop_table('refresh_tokens')
    op.drop_table('users')
    op.drop_table('tickets')
    with op.batch_alter_table('snapshots', schema=None) as batch_op:
        batch_op.drop_index(batch_op.f('ix_snapshots_metrica'))
        batch_op.drop_index(batch_op.f('ix_snapshots_fecha'))

    op.drop_table('snapshots')
    op.drop_table('roles')
    op.drop_table('revoked_tokens')
    op.drop_table('proyectos')
    with op.batch_alter_table('proyecto_tareas', schema=None) as batch_op:
        batch_op.drop_index(batch_op.f('ix_proyecto_tareas_proyecto_id'))

    op.drop_table('proyecto_tareas')
    with op.batch_alter_table('proyecto_responsables', schema=None) as batch_op:
        batch_op.drop_index(batch_op.f('ix_proyecto_responsables_proyecto_id'))

    op.drop_table('proyecto_responsables')
    with op.batch_alter_table('proyecto_activos', schema=None) as batch_op:
        batch_op.drop_index(batch_op.f('ix_proyecto_activos_proyecto_id'))

    op.drop_table('proyecto_activos')
    op.drop_table('permissions')
    with op.batch_alter_table('historial', schema=None) as batch_op:
        batch_op.drop_index(batch_op.f('ix_historial_asset_id'))

    op.drop_table('historial')
    with op.batch_alter_table('audit_log', schema=None) as batch_op:
        batch_op.drop_index(batch_op.f('ix_audit_log_user_id'))
        batch_op.drop_index(batch_op.f('ix_audit_log_timestamp'))

    op.drop_table('audit_log')
    with op.batch_alter_table('assets', schema=None) as batch_op:
        batch_op.drop_index(batch_op.f('ix_assets_serial'))

    op.drop_table('assets')
    op.drop_table('asset_glpi')
    with op.batch_alter_table('adjuntos', schema=None) as batch_op:
        batch_op.drop_index(batch_op.f('ix_adjuntos_asset_id'))

    op.drop_table('adjuntos')
