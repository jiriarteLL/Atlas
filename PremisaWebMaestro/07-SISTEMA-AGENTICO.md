# Sistema Agéntico aplicado a la Web Maestro

> **Versión:** v4 (framework agéntico v4 / contrato `maestro.platform/v2`)
> **Última revisión:** 2026-05-07
> **Estado:** vigente
> **Reemplaza a:** `legacy/v3/PremisaWebMaestro/07-SISTEMA-AGENTICO.md` (modelo v1 con jerarquía agéntica acoplada al IdP).

---

## Propósito de este documento

Este documento describe cómo el **framework agéntico v4** (definido en `framework-agentico/`) se aplica a la construcción y mantenimiento de la **Web Maestro** v4. Cubre:

- La activación del preset `maestro-platform` cuando el proyecto es la Web Maestro misma.
- El flujo del PM persistente al iniciar un proyecto de Web Maestro.
- Los Agent() calls específicos que orquestan cada fase.
- Los validadores transversales adaptados al contexto del Maestro.
- La relación con el preset `web-maestro` que aplica al login propio del Maestro (la Web Maestro es app huésped de sí misma para fines de auth).

---

## Cambio respecto a v1

En v1 había una jerarquía agéntica diseñada específicamente para construir el Maestro v1 (con sus orquestadores acoplados al IdP, headers `X-Auth-*`, multi-tenancy lógica). En v4 el framework agéntico es **estable y agnóstico**: aplica igual al construir una app huésped o al construir la Web Maestro misma. Lo único que cambia es el **preset activo**:

- Preset `web-maestro` → para construir una app huésped.
- Preset `maestro-platform` → para construir la Web Maestro.

El framework agéntico v4 ya está definido en `framework-agentico/` (PM, RULES, fases 00-07, validadores, templates). Este documento describe **cómo se usa** en el contexto específico de la Web Maestro.

---

## Activación del preset al iniciar un proyecto de Web Maestro

Cuando el PO ejecuta `/pm` en un repo nuevo (o un fork del template), el flujo es (ver `framework-agentico/core/PM.md` y `framework-agentico/core/RULES.md` sección `activacion_de_preset`):

```
1. PM detecta el repo y obtiene project_id (gh repo view --json name).
2. PM verifica si existe PROJECT.md.
3. Si no existe, PM presume "app huésped" (default) y le pregunta al PO:
   "Voy a presumir que estás construyendo una app huésped. Si en cambio vas a construir
    la Web Maestro / Web Anfitriona, decímelo."
4. Si el PO indica "Web Maestro" (o cualquier sinónimo: web anfitriona, plataforma):
   - project_type = "web_maestro"
   - preset_active = "maestro-platform"
5. PM crea estructura del proyecto:
   - framework-agentico/projects/<project_id>/PROJECT.md (con preset_active grabado)
   - cost/SUMMARY.md
   - branches/
6. PM lee la premisa del proyecto (este conjunto de documentos PremisaWebMaestro/) y
   pregunta al PO hasta certeza 100% sobre alcance y requisitos.
7. PM determina los agentes que se necesitan según las fases.
8. PM crea epic branch (epic/maestro-v4 o similar).
9. PM ejecuta /pm:orquestar para arrancar la fase 00-setup.
```

Este flujo es **idéntico al de una app huésped**; solo cambia el preset y, por tanto, las constraints inyectadas en cada Context Packet.

---

## Constraints del preset `maestro-platform` por fase

El preset `maestro-platform` (`framework-agentico/agents/presets/maestro-platform/PRESET.md`) define las obligaciones específicas del proyecto Web Maestro en cada fase. Resumen:

### Fase 00 — Setup
- Verificar Docker, Docker Compose, git, IDE.
- NO instalar runtimes en el host (Laravel/Node/Python solo via contenedores).
- Toolchain ejecutable exclusivamente vía `docker compose run --rm <servicio> <comando>`.
- VPS/cloud lo gestiona el humano por fuera del framework.

### Fase 01 — Discovery
- Tratar las 14 no-negociables y las 10 premisas de `01-PREMISAS-Y-NO-NEGOCIABLES.md` como requisitos no funcionales obligatorios.
- Identificar regulaciones aplicables (GDPR, LGPD, ISO 27001, SOC 2 según mercado).
- Mapear stakeholders: empresas tenant, usuarios finales de las apps huésped, devs de apps huésped, admins del Maestro, C-Level.
- Documentar métricas objetivo: latencia de redirección < 200ms, provisioning de deployment < 60s, branding fetch (con cache) < 50ms, hooks success rate ≥ 99%.

### Fase 02 — Planning
- ADRs obligatorios:
  - Elección del RDBMS para la BD del Maestro (PostgreSQL recomendado).
  - Reverse proxy: Traefik con TLS Let's Encrypt (sin ForwardAuth).
  - Estrategia de cifrado AES-256 para secretos (api_keys, webhook_secrets).
  - Estrategia de provisioning (Docker API).
  - Estrategia de redes Docker por deployment.
- Modelo de datos según `02-MODELO-DE-DATOS.md`.
- Contratos de API según `03-AUTENTICACION-Y-AUTORIZACION.md` y `06-CONTRATO-MAESTRO-YAML.md`.
- Threat model obligatorio (ver `09-SEGURIDAD.md`).
- UX del portal según `05-PORTAL-Y-RENDERIZADO.md`.
- Decisión de seeding: superadmin obligatorio (`admin@llyasoc.com`) + opcionalmente admins adicionales.
- Producir `docs/CONVENCIONES_PLATAFORMA.md` actualizado para v4.

### Fase 03 — Development
- Implementar:
  - Backend del Maestro (registry + admin API + provisioner).
  - Login propio del Maestro para sus admins (cumple `web-maestro` v4 a sí mismo).
  - Tablas y migraciones según `02-MODELO-DE-DATOS.md`.
  - Triggers SQL para inmutabilidad del `audit_log`.
  - Cifrado AES-256 de api_keys y webhook_secrets.
  - Motor de provisioning (servicio + Docker API).
  - Job periódico de health checks (con escalado de respuestas).
  - Job periódico de fetch de branding.
  - Hooks salientes con HMAC-SHA256.
  - Endpoint `POST /api/v2/apps/register` para auto-registro de apps.
  - Endpoint `GET /api/v2/portal/my-apps` para que apps consulten apps de la empresa.
  - Frontend del portal (preferentemente Tailwise React).
  - JSON Schema oficial de `maestro.yaml` v2.
  - `maestro-cli` con comandos `validate` (v2) y `new` (template).

### Fase 04 — Delivery
- Dockerfile del Maestro multi-stage, non-root, con HEALTHCHECK.
- docker-compose con Traefik + Maestro API + DB del Maestro + Redis (opcional).
- Pipeline CI/CD en `.github/workflows/`.
- Configuración Traefik: TLS Let's Encrypt, redirect HTTP→HTTPS, HSTS, rate limiting (sin ForwardAuth).
- Branch protection en `main`.
- Scripts/documentación de deployment (el deploy al VPS lo ejecuta el humano; el framework solo produce los artefactos).
- ENV vars obligatorias: `DATABASE_URL`, `MAESTRO_ENCRYPTION_KEY`, `JWT_SECRET` (o `APP_KEY`), `SUPERADMIN_INITIAL_PASSWORD`.

### Fase 05 — Seeding
- Seeder idempotente del superadmin del Maestro (`admin@llyasoc.com`).
- Validación obligatoria: la fase 05-seeding del Maestro **DEBE** cumplir el preset `web-maestro` (= cumple `framework-agentico/phases/05-seeding.md` y `framework-agentico/core/PRESET_WEB_MAESTRO.md` sección Fase 05).
- Tests del seeder (idempotencia, password débil, login exitoso, etc.).

### Fase 06 — Operations
- Stack de observabilidad: Prometheus, Loki, Grafana (ver `10-OBSERVABILIDAD.md`).
- Dashboards: ejecutivo, por deployment, por empresa, salud del registry.
- Alertas (deployment unhealthy, branding fetch fail, hooks fail rate alto, BD del Maestro caída).
- Runbooks operativos (ver `10-OBSERVABILIDAD.md`).
- Política de backups: diario, cifrado, externo al VPS, retención ≥ 30 días.
- Audit log centralizado y consultable.
- Logs con `user_id` (admin) y `request_id` — sin `company_id` en logs del Maestro mismo.

### Fase 07 — Retrospective
- Documentar patterns de la Web Maestro v4.
- Consolidar ADRs, threat model, runbooks.
- Lecciones de migración del modelo v1 (si aplica).
- Reporte ejecutivo final.

---

## Agentes específicos del proyecto Web Maestro

El PM determina qué agentes necesita para construir la Web Maestro. Recomendados:

### Fase 02 (Planning)
- `software-architect` (opus): patrones, ADRs, estructura de servicios, integración Maestro ↔ apps.
- `data-architect` (sonnet): modelo de datos según `02-MODELO-DE-DATOS.md`.
- `api-designer` (sonnet): endpoints REST según `03-AUTENTICACION-Y-AUTORIZACION.md` y `06-CONTRATO-MAESTRO-YAML.md`.
- `ux-designer` (sonnet): flujos del portal según `05-PORTAL-Y-RENDERIZADO.md`. Presenta Tailwise como recomendación.
- `security-architect` (opus): threat model detallado.

### Fase 03 (Development)
- `backend-developer` (sonnet): implementa registry, admin API, provisioner.
- `frontend-developer` (sonnet): implementa portal. Hereda premisa Tailwise (preferido pero no obligatorio).
- `database-migrator` (haiku): migraciones de schema con triggers de inmutabilidad.
- `devops-engineer` (sonnet): integración con Docker API para provisioning.
- `cli-developer` (sonnet): `maestro-cli` con comandos `validate` y `new`.
- `seeder-developer` (sonnet): seeder del superadmin idempotente.

### Fase 04 (Delivery)
- `devops-engineer` (sonnet): Dockerfile, docker-compose, configuración Traefik.
- `ci-cd-specialist` (sonnet): pipeline GitHub Actions.
- `integrator` (sonnet): smoke tests post-build.

### Fase 05 (Seeding)
- `seeder-developer` (sonnet): aplica seeder al stack del Maestro.
- `seeder-tester` (sonnet): tests de idempotencia.

### Fase 06 (Operations)
- `observability-engineer` (sonnet): stack Prometheus/Loki/Grafana, dashboards, alertas.
- `incident-manager` (haiku): runbooks operativos.
- `tech-debt-manager` (haiku): documentar deuda técnica del MVP.

### Fase 07 (Retrospective)
- `documentation-writer` (sonnet): consolidación final.
- `executive-reporter` (sonnet): reporte ejecutivo.

### Validadores (transversales en cada fase)
- `code-reviewer` (sonnet/opus según módulo).
- `security-auditor` (sonnet/opus para módulos de auth, provisioning, secretos).
- `qa-tester` (sonnet).
- `performance-analyst` (haiku/sonnet).
- `compliance-analyst` (haiku/sonnet).
- `documentation-writer` (haiku, post-aprobación).

---

## Validadores transversales adaptados al Maestro

Los validadores leen `framework-agentico/validation/validators/<rol>.md` como template, pero el orquestador **adapta el prompt al contexto del proyecto Web Maestro**. Adaptaciones clave:

### `security-auditor`
Adicional a su checklist general:
- Validar triggers SQL de inmutabilidad en `audit_log`.
- Validar cifrado AES-256 de `api_keys.key_hash` y `webhook_secrets.secret_hash`.
- Validar que `MAESTRO_ENCRYPTION_KEY` viene de ENV var y no está hardcodeada.
- Validar que rotación de api keys/webhook secrets queda audit logged.
- Validar que el motor de provisioning no expone `docker.sock` a apps huésped.
- Validar que Traefik no tiene ForwardAuth configurado (artefacto v1 prohibido).
- Validar que NO existe tabla `users` global con usuarios de apps huésped.
- Validar firma HMAC-SHA256 en hooks salientes (timing-safe comparison).

### `qa-tester`
Adicional:
- Tests del flujo completo: registrar app via `/api/v2/apps/register` → licenciar a empresa → provisionar deployment → consumir `/maestro/branding` → click en portal abre `target="_blank"`.
- Tests de hooks: `on_user_added` llega correctamente firmado, deduplica por `event_id`.
- Tests de rotación de api_key sin downtime.
- Tests del seeder del Maestro (idempotencia).
- Tests del provisioning: aislamiento de redes (deployment A no ve deployment B).
- Tests del audit log: UPDATE/DELETE rechazado por trigger.

### `compliance-analyst`
Adicional:
- Validar política de retención de backups (30 días mín).
- Validar política de retención de deployments destruidos (90 días mín).
- Validar audit log cumple requisitos regulatorios (timestamp ms, actor, payload before/after).
- Validar GDPR aplicado a la BD del Maestro (usuarios admin pueden solicitar eliminación).

### `performance-analyst`
Adicional:
- Latencia de redirección < 200ms p95.
- Tiempo de provisioning de deployment < 60s p95.
- Tiempo de fetch de branding (con cache) < 50ms p95.
- Cache hit rate de branding > 90%.
- Sin filtros multi-tenant en queries (premisa de single-tenant físico).

### `code-reviewer`
Adicional:
- Validar separación de capas (controllers, services, repositories) en backend.
- Validar que el provisioner no expone Docker API a usuarios finales (solo a admins).
- Validar manejo de errores en operaciones largas (provisioning) con timeouts.
- Validar idempotencia del provisioner.

---

## Memorias transaccionales en el proyecto Web Maestro

El framework agéntico v4 registra transacciones por cada Agent() call (ver `framework-agentico/core/RULES.md` sección `memorias_transaccionales`). En el proyecto Web Maestro:

- Cada operación queda en `framework-agentico/projects/<project_id>/branches/<sanitized-branch>/transactions/`.
- El cost-analyst post-fase agrega costos a `branches/<rama>/cost/COST_LOG.md`.
- Rollup a `framework-agentico/projects/<project_id>/cost/SUMMARY.md`.
- Indexado en `framework-agentico/checkpoints/GLOBAL.md`.

Al cerrar el proyecto, se compactan las transacciones en `COMPACTED_TRANSACTIONS.md` por rama.

---

## Migración del Maestro v1 a Maestro v4

Si existe un repositorio del Maestro v1 (con código basado en el modelo IdP centralizado), su migración a v4 implica:

1. PO ejecuta `/pm` en el repo v1.
2. PM detecta `framework_version` desactualizado en `framework-agentico/checkpoints/GLOBAL.md`.
3. PM ofrece sincronizar con upstream del template v4.
4. Tras sync, `Agent(framework-migrator, opus)` genera reporte de gaps en el código del Maestro v1:
   - Endpoints `/api/auth/login`, `/api/auth/validate` (lado IdP) → marcar como deprecados.
   - Tabla `users` global → migrar a `admin_users` (solo admins del Maestro).
   - Eliminación de pivots `company_user`, `application_company`, `application_user`.
   - Headers `X-Auth-*` emitidos por `/api/auth/validate` → eliminar.
   - Configuración Traefik con ForwardAuth → eliminar.
   - Reverse proxy con iframes → reemplazar por portal con `target="_blank"`.
   - Inversión del modelo de auth (apps huésped pasan a tener login propio; el Maestro se simplifica).
5. PM presenta el reporte al PO. **NO modifica código** automáticamente.
6. El PO decide:
   - Resolver los gaps con un nuevo trabajo (issues, PRs).
   - Marcar el proyecto como `non_compliant_v4` y operar solo lectura.

Detalle del proceso de migración en `framework-agentico/migration/v3-to-v4.md`.

---

## Diferencia con la construcción de una app huésped

| Aspecto | App huésped | Web Maestro |
|---|---|---|
| Preset activo | `web-maestro` | `maestro-platform` |
| Constraints inyectadas en Context Packet | `framework-agentico/core/PRESET_WEB_MAESTRO.md` | `framework-agentico/agents/presets/maestro-platform/PRESET.md` |
| Modelo de datos | `users`, `roles`, `permissions` propios (sin `company_id`) | `companies`, `applications`, `deployments`, `api_keys`, `webhook_secrets`, `audit_log`, `admin_users` |
| Auth implementada | Login propio para usuarios finales | Login propio para admins del Maestro **+** auth server-to-server hacia apps |
| Provisioning | NO aplica (la app es provisionada por el Maestro) | SÍ implementa el provisioner (Docker API + redes + BDs dedicadas) |
| Portal | NO existe (la app puede tener su UI propia) | SÍ implementa el portal admin |
| Tailwise | Recomendado, no obligatorio | Recomendado, no obligatorio |

**Punto en común clave**: el Maestro v4 implementa para sus admins **el mismo modelo de auth propia** que cualquier app huésped, cumpliendo el preset `web-maestro` para esa parte. Por eso la fase 05-seeding del Maestro es idéntica a la de una app huésped.

---

## Preset compuesto: `maestro-platform` extiende implícitamente `web-maestro`

Como aclarado en `framework-agentico/core/RULES.md` sección `activacion_de_preset`:

- El preset `maestro-platform` **incluye internamente** el cumplimiento de `web-maestro` para el login propio de los admins del Maestro.
- **NO es activar dos presets**: el preset_active sigue siendo único (`maestro-platform`).
- Es un solo preset que **referencia** las obligaciones del otro para una parte específica del proyecto.

En la práctica: cuando el preset `maestro-platform` está activo, el Context Packet inyecta sus constraints, y dentro de esas constraints está la obligación "el login propio de los admins cumple `web-maestro` v4". Los validadores transversales validan ambos conjuntos para los módulos relevantes.

---

## Referencias normativas

- `01-PREMISAS-Y-NO-NEGOCIABLES.md` — premisas y no-negociables que el sistema agéntico hace cumplir.
- `framework-agentico/CLAUDE.md` — root del framework.
- `framework-agentico/core/PM.md` — system prompt del PM.
- `framework-agentico/core/RULES.md` — reglas generales (glosario, activación de preset, persistencia, etc.).
- `framework-agentico/core/CONTEXT_PACKET.md` — formato de comunicación PM ↔ orquestadores.
- `framework-agentico/core/PRESET_WEB_MAESTRO.md` — preset que aplica a apps huésped.
- `framework-agentico/agents/presets/maestro-platform/PRESET.md` — preset que aplica a la Web Maestro.
- `framework-agentico/phases/00-setup.md` … `07-retrospective.md` — templates por fase.
- `framework-agentico/validation/validators/*.md` — templates de validadores.
- `framework-agentico/migration/v3-to-v4.md` — proceso de migración para forks v1.

---

## Historial de revisiones

| Versión | Fecha | Cambio |
|---|---|---|
| 4.0.0 | 2026-05-07 | Versión inicial v4. Documenta cómo el framework agéntico v4 (preset `maestro-platform` activo) construye la Web Maestro v4. Reemplaza al v1 (legacy en `legacy/v3/PremisaWebMaestro/07-SISTEMA-AGENTICO.md`). |
