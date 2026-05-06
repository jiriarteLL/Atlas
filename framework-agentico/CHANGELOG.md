# Framework Agentico — CHANGELOG

> Registro de cambios entre versiones del framework.
> Sigue SemVer: MAJOR.MINOR.PATCH. Bumps MAJOR son cambios incompatibles.

---

## v4.0 — 2026-05-06

**BREAKING.** Cambio de modelo de auth y tenancy. Inversion del contrato Maestro <-> App huesped.

### Resumen

v4.0 invierte el modelo de auth y tenancy de las aplicaciones huesped:

- **De multi-tenant a single-tenant**: cada contenedor de aplicacion sirve a UNA empresa. Se elimina el filtrado por `company_id`.
- **De auth centralizada por headers a login propio**: cada app gestiona sus propios users, roles, permisos y tokens. La Web Maestro deja de inyectar headers de identidad y solo redirige (target=`_blank`) a la URL de la app.
- **Nueva fase `05-seeding`** entre `04-delivery` y `06-operations`: garantiza que el MVP tenga un usuario superadmin (`admin@llyasoc.com`) creado de forma idempotente.
- **Renumeracion de fases**: `05-operations` -> `06-operations`, `06-retrospective` -> `07-retrospective`.

### Detalle de cambios

| Area | v3.0 | v4.0 |
|---|---|---|
| Tenancy | Multi-tenant con filtrado por `company_id` | Single-tenant: un contenedor por empresa |
| Auth | Headers `X-Auth-*` inyectados por el Maestro | Cada app implementa login propio (users + roles + permissions + tokens propios) |
| Tabla `users` | Prohibida | Obligatoria. Estructura sugerida (no obligatoria) en el preset |
| Maestro -> App (usuario) | Inyecta headers de identidad y maneja sesion | Solo redirige con `target="_blank"` a la URL de la app |
| Maestro -> App (server) | `X-Maestro-Webhook-Secret` para hooks | + `X-Maestro-Api-Key` para endpoint `/maestro/branding` |
| `maestro.yaml` | hooks + recursos | + `auth_model: own`, `login_path`, `branding_url` |
| Fases | 00-setup ... 06-retrospective (7 fases) | 00-setup ... 07-retrospective (8 fases) |
| Fase de seeding | No existe | Nueva: `05-seeding` (post-delivery, pre-operations) |
| Superadmin | N/A | `admin@llyasoc.com`. Password desde ENV `SUPERADMIN_INITIAL_PASSWORD`. Idempotente. |
| `security-auditor` | "Validar que NO haya tabla users/sessions" | "Validar que `users` existe + bcrypt/argon2 + no leakeo de api keys" |
| `qa-tester` | "Testear middleware de headers (401/200)" | "Testear login propio + idempotencia del seed + branding endpoint con api key" |
| `compliance-analyst` | "Validar multi-tenancy seguro entre tenants" | "Validar password policy + audit log de auth + retencion de sesiones" |
| `performance-analyst` | "Validar filtros por `company_id` (no full table scan cross-tenant)" | "Validar limites de recursos. Sin filtros multi-tenant (single-tenant fisico)" |

### Migracion v3 -> v4

La migracion es **lazy** (no automatica masiva). Cuando un Project Owner ejecuta `/pm` en un fork con framework < v4:

1. El PM detecta `framework_version` desactualizada en `checkpoints/GLOBAL.md`.
2. El PM ofrece sincronizar el fork con upstream (**modo hibrido**: el PO confirma y el PM ejecuta `git fetch upstream && git merge upstream/master`, o el PO lo hace manual).
3. Tras el sync, el PM detecta `framework_version: "4.0"` y propone migracion del proyecto local.
4. Si el PO acepta, el PM lanza `Agent(framework-migrator, opus)` que:
   - Reemplaza archivos del framework con la copia v4 (ya sincronizada).
   - Preserva `projects/` (estado del proyecto local).
   - Genera reporte de gaps en el codigo de la app (middleware viejo, prohibiciones de tabla users, fases renumeradas, etc.) **SIN tocar el codigo**.
5. El PM presenta el reporte. Si el PO quiere actualizar el codigo de la app, abre un nuevo trabajo (issue/branch). El framework no fuerza cambios al codigo.

Detalle del proceso: `framework-agentico/migration/v3-to-v4.md`.

### Razones del bump MAJOR

- Cambio incompatible con apps v3 (cambia el contrato externo de auth).
- Aplicaciones v3 NO funcionan bajo el modelo v4 sin migracion del codigo.
- SemVer estricto pide MAJOR.

### Archivos creados

- `framework-agentico/CHANGELOG.md`
- `framework-agentico/phases/05-seeding.md`
- `framework-agentico/migration/v3-to-v4.md`
- `framework-agentico/migration/migrator-template.md`

### Archivos renombrados

- `phases/05-operations.md` -> `phases/06-operations.md`
- `phases/06-retrospective.md` -> `phases/07-retrospective.md`

### Archivos modificados

- `framework-agentico/CLAUDE.md` (root del repo)
- `core/PM.md`
- `core/RULES.md` (NEW seccion 15: migracion entre versiones)
- `core/PRESET_WEB_MAESTRO.md` (rewrite completo)
- `core/CONTEXT_PACKET.md` (version 4.0 + preset constraints)
- `checkpoints/GLOBAL.md` (`framework_version: "4.0"`)
- `phases/00-setup.md`, `01-discovery.md`, `02-planning.md`, `03-development.md`, `04-delivery.md`
- `phases/06-operations.md`, `07-retrospective.md` (post-rename)
- `validation/validators/security-auditor.md` (rewrite)
- `validation/validators/qa-tester.md` (rewrite)
- `validation/validators/compliance-analyst.md`
- `validation/validators/performance-analyst.md`

---

## v3.0 — 2026-04-23

Memorias transaccionales granulares + aislamiento por proyecto.

- Memorias transaccionales: cada `Agent()` call genera una transaccion inmutable.
- Aislamiento por proyecto: `projects/{id}/` con `PROJECT.md`, cost summary y branches.
- Costos a nivel de rama, agregados a proyecto, indexados en `GLOBAL.md`.
- Compactacion de transacciones al cierre del proyecto.

---

## v2.0

PM persistente + `Agent()` calls reales + context packets + agentes dinamicos + worktrees aislados.

Para detalles, ver `git log` previo a v3.0.
