# Framework Agentico — CHANGELOG

> Registro de cambios entre versiones del framework.
> Sigue SemVer: MAJOR.MINOR.PATCH. Bumps MAJOR son cambios incompatibles.

---

## v4.1 — 2026-05-07

**Cleanup de paths canonicos.** Sin cambios funcionales en el framework. Saneamiento de nomenclatura y reorganizacion de archivos legacy bajo `legacy/v3/`.

### Cambios en `framework-agentico/`

- `core/RULES.md`: nuevas secciones:
  - `glosario_de_sinonimos` (§0): PO/Project Owner/Product Owner, app huesped/aplicacion generica/tool, Web Maestro/Web Anfitriona como sinonimos.
  - `politica_de_versionado` (§16): paths canonicos sin sufijo de version; versiones anteriores a `legacy/v{n}/` con banner DEPRECADO.
  - `politica_de_persistencia_de_datos` (§17): BD persiste entre versiones; cambios destructivos requieren confirmacion explicita del PO.
  - `activacion_de_preset` (§8 reescrita, antes `preset_web_maestro`): default `web-maestro` (app huesped); el PM confirma con el PO al iniciar; si PO declara construir Web Maestro, preset_active = `maestro-platform`.
- `core/PM.md`: paso 2 nuevo de confirmacion de tipo de proyecto (app huesped vs Web Maestro). Seccion "PRESET WEB MAESTRO" reescrita como "PRESET ACTIVO" con logica condicional.
- `core/templates/PROJECT_TEMPLATE.md`: agregados `project_type` y `preset_active`.
- `core/templates/PROJECT_TEMPLATE.md`: campo legacy `preset` reemplazado por `preset_active`.
- `checkpoints/GLOBAL.md`: campo `preset` reemplazado por `default_preset` (cada proyecto declara su preset_active en su PROJECT.md).
- `agents/presets/maestro-platform-v2/` -> `agents/presets/maestro-platform/` (sufijo `-v2` removido para alineacion con politica de versionado).
- `agents/presets/maestro-platform/PRESET.md` y `rules/RULES.md` (canonicos): titulos "v2" removidos; referencias a `_V2.md` y `-v2/` actualizadas a paths canonicos.
- `agents/presets/maestro-platform/` legacy v1 movido a `legacy/v3/framework-agentico/agents/presets/maestro-platform/` con banner DEPRECADO.
- `phases/04-delivery.md` y `phases/05-seeding.md`: referencia a seccion `preset_web_maestro` actualizada a `activacion_de_preset`.
- `phases/05-seeding.md`: documentado orden obligatorio de seeders (permissions -> roles -> assign permissions to role -> users -> assign role to user).
- `phases/02-planning.md` y `phases/03-development.md`: agregada nota explicita para agentes UX/UI sobre Tailwise como preferido pero NO obligatorio.
- `migration/migrator-template.md`: paso 2 actualizado para usar `git mv` (preserva historia git).

### Cambios fuera de `framework-agentico/`

- Documentos canonicos de apps huesped (sufijo `_V2` removido):
  - `docs/APP_HUESPED_SPEC_V2.md` -> `docs/APP_HUESPED_SPEC.md`
  - `docs/APP_HUESPED_BEST_PRACTICES_V2.md` -> `docs/APP_HUESPED_BEST_PRACTICES.md`
  - `docs/CONVENCIONES_PLATAFORMA_V2.md` -> `docs/CONVENCIONES_PLATAFORMA.md`
- v1 de los anteriores movidos a `legacy/v3/docs/` con banner DEPRECADO.
- `PremisaWebMaestro/` (constitucion v1 del Maestro) movida a `legacy/v3/PremisaWebMaestro/` con banner DEPRECADO en cada uno de sus 12 archivos.
- `PremisaWebMaestro/` v4 redactada de cero (12 documentos): constitucion del Maestro v4 alineada al modelo registry+redirector+provisioner del contrato `maestro.platform/v2`.
- `arquitectura_actual.md` movido a `legacy/v3/` (snapshot historico, sin reemplazo).
- `mock/` ELIMINADO del template canonico (era legacy v3, recuperable via git history).
- `cli/node/templates/node-express/` ELIMINADO del template canonico (era ilustrativo Node-only; el template es stack-agnostico, recuperable via git history).
- `legacy/README.md` y `legacy/v3/README.md` creados como indices con politica de versionado y mapping de equivalentes vigentes.
- `.env.example` (raiz) creado para apps huesped v4 con todas las ENV vars del modelo (DATABASE_URL, MAESTRO_API_KEY, MAESTRO_WEBHOOK_SECRET, SUPERADMIN_INITIAL_PASSWORD, JWT_SECRET, etc.).

### Cambios en slash commands

- `.claude/commands/pm.md`: "framework agentico v2" -> "framework agentico v4".
- `.claude/commands/pm-orquestar.md`, `pm-planificar.md`, `pm-estado.md`, `pm-reporte.md`: header marcado con "framework agentico v4".

### Referencias cruzadas

- `README.md` (raiz), `CHANGELOG.md` (raiz), `docs/*`, `framework-agentico/core/*`, `framework-agentico/phases/*`, `framework-agentico/agents/presets/maestro-platform/*` actualizados para apuntar a paths canonicos.
- Banner DEPRECADO estandar (definido en `core/RULES.md` §`politica_de_versionado`) aplicado a 18 archivos en `legacy/v3/`.

### Compatibilidad

- **Sin breaking changes** en el framework. Forks que sincronicen con upstream tras este cleanup deben actualizar referencias en sus archivos propios si las tienen (paths obsoletos `_V2.md`, `maestro-platform-v2/`).
- El `framework-migrator` (`migration/migrator-template.md`) sigue siendo aplicable para forks v3 que migren a v4. Tras este cleanup, las referencias generadas por el migrator apuntan a paths canonicos.

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
