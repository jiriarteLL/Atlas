# Atlas — Modelo de datos (fase 02-planning)

Single-tenant físico: **ninguna tabla tiene `company_id`** (SPEC §2.5). La empresa está implícita en el deployment.
El esquema se versiona con Alembic (`app/backend/migrations/`). `init_db()` lo lleva a la última migración en cada arranque.

## Autenticación y autorización

| Tabla | Campos clave | Notas |
|---|---|---|
| `users` | `id` (uuid), `username` único, `email` único, `password_hash` (bcrypt ≥ 12), `nombre`, `activo`, `last_login_at`, `sesiones_desde`, `intentos_fallidos`, `bloqueado_hasta`, `debe_cambiar_password` | `sesiones_desde` invalida tokens anteriores. El superadmin es `admin@llyasoc.com`. |
| `roles` | `id`, `nombre` único, `descripcion` | `superadmin`, `admin`, `editor`, `viewer` |
| `permissions` | `id`, `codigo` único, `descripcion` | 5 permisos (ver `auth.PERMISOS`) |
| `role_permissions` | `role_id`, `permission_id` | Pivot |
| `user_roles` | `user_id`, `role_id` | Pivot. La UI asigna un rol por usuario. |
| `refresh_tokens` | `id`, `user_id`, `token_hash` (sha256), `creado`, `expira`, `revocado` | El token en claro nunca se guarda. |
| `revoked_tokens` | `jti`, `expira` | Access tokens revocados por logout. Se purgan al vencer. |
| `audit_log` | `id`, `timestamp`, `usuario`, `user_id`, `accion`, `entidad`, `entidad_id`, `detalle` (JSON), `ip_origen`, `user_agent`, `request_id`, `resultado` | **Solo INSERT:** un trigger rechaza UPDATE/DELETE. |

## Negocio

| Tabla | Campos clave | Notas |
|---|---|---|
| `assets` | `id` (`A` + 6 hex), `serial` (índice), `nombre`, `tipo`, `marca`, `modelo`, `estado`, `usuario`, `ubicacion` (sede), hardware, SO, `ip`, `garantia`, `software` (texto `nombre\|\|\|version\|\|\|fecha~~~…`), `cifrado`, `tpm`, `updated` | El serial es la clave de conciliación con los agentes. |
| `asset_glpi` | `serial` (PK), `edr`, `antivirus`, `volumenes_sin_cifrar`, `bateria_salud`, `acceso_remoto`, `office`, `bios`, `os_build`, `detalle` (JSON saneado) | Upsert por serial. El `detalle` excluye la clave de Windows, variables de entorno y procesos. |
| `historial` | `asset_id`, `fecha`, `usuario`, `campo`, `valor_ant`, `valor_new`, `accion` | Una fila por campo cambiado. |
| `adjuntos` | `id`, `asset_id`, `nombre`, `contenido` (bytea, deferred), `tipo`, `tamano`, `activo` | Borrado lógico (`activo = "0"`). ADR-001. |
| `proyectos` | `id`, `numero` (`PRY-AAAA-NNN`), `nombre`, `tipo`, `estado`, `prioridad`, fechas, `avance`, links | |
| `proyecto_responsables` | `proyecto_id`, `responsable` | Usernames de la app |
| `proyecto_activos` | `proyecto_id`, `asset_id` | |
| `proyecto_tareas` | `proyecto_id`, `titulo`, `estado`, `responsable`, `fecha_limite`, `orden` | |
| `tickets` | `id`, `activo`, `titulo`, `estado`, `prioridad` | |
| `snapshots` | `fecha`, `metrica`, `clave`, `valor` | Base de Tendencias |

## Datos personales (data_policy)

`pii: true`. Se guardan el nombre, el usuario de dominio y el email corporativo de las personas asignadas a cada
equipo y de los usuarios de la app. No hay categorías sensibles. El tier `standard` lo confirmó el PO (2026-09-30). `regulated: false` es una **propuesta**: si el
estudio considera que aplica la Ley 25.326, corresponde `regulated: true`, `criticality: critical` y un ADR de
cumplimiento (DP-006). Lo decide el evaluador o el PO.

## Migración desde producción (pendiente)

La v2 arranca con la base vacía. Pasar los datos de producción (SQLite) a PostgreSQL es un trabajo aparte, que se
hace **después** de tener HTTPS, porque Test y Preprod corren en HTTP (MANUAL §0.1).
