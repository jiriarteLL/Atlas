# Modelo de Datos de la Web Maestro

> **Versión:** v4 (framework agéntico v4 / contrato `maestro.platform/v2`)
> **Última revisión:** 2026-05-07
> **Estado:** vigente
> **Reemplaza a:** `legacy/v3/PremisaWebMaestro/02-MODELO-DE-DATOS.md` (modelo v1 con `users` global y multi-tenancy lógica).

---

## Propósito de este documento

Este documento define todas las entidades persistentes en la base de datos de la **Web Maestro** (= Web Anfitriona = plataforma Maestro), sus atributos, las relaciones entre ellas, las reglas de integridad referencial y las restricciones de negocio. Un agente de IA que genere código de migraciones, modelos ORM, endpoints de API o lógica de negocio del Maestro debe usar este documento como fuente de verdad.

La base de datos del Maestro usa **PostgreSQL** (recomendación; cualquier RDBMS con soporte de triggers SQL, UUID nativo y JSONB es aceptable). Las bases de datos de los **deployments de apps huésped** son ajenas a este documento: cada app tiene su propio modelo, registrado en `docs/APP_HUESPED_SPEC.md` §3.

---

## Cambios respecto a v1 (legacy)

En v1 el Maestro tenía una tabla `users` global con todos los usuarios de todas las apps, además de tablas de `companies`, `applications` y pivots M-M (`company_user`, `application_company`, `application_user`). Las apps consumían estos datos via headers `X-Auth-*` inyectados.

En v4 ese modelo desaparece:

- **NO** existe tabla `users` global. Cada app huésped mantiene su propia tabla `users` en su BD dedicada.
- **NO** existen pivots M-M de usuarios contra apps o empresas.
- **SÍ** existen `admin_users`, `admin_roles`, `admin_permissions` con sus pivots — pero son **solo para los administradores de la Web Maestro misma**, no para los usuarios finales de las apps.
- **SÍ** se introducen las tablas `deployments`, `api_keys`, `webhook_secrets` para gestionar el ciclo de vida del par app+empresa.

---

## Inventario de entidades

### Entidades del catálogo (registry)

| Tabla | Propósito | Cardinalidad |
|---|---|---|
| `companies` | Empresas tenant que tienen acceso a la plataforma | N |
| `applications` | Apps huésped registradas en el catálogo | N |
| `deployments` | Instancias activas (un par app + empresa = un deployment) | N (default 1 por par) |

### Entidades de secretos (cifrados con AES-256)

| Tabla | Propósito | Cardinalidad |
|---|---|---|
| `api_keys` | `MAESTRO_API_KEY` por deployment, rotables | 1 activa por deployment |
| `webhook_secrets` | `MAESTRO_WEBHOOK_SECRET` por deployment, rotables | 1 activa por deployment |

### Entidades de identidad de admins del Maestro

> Estas tablas son **para administradores de la Web Maestro** (no para usuarios finales de las apps huésped). Cumplen las mismas reglas que cualquier app huésped según el preset `web-maestro`: bcrypt cost ≥ 12 o argon2id, audit log de auth, sin `company_id` (los admins son globales del Maestro).

| Tabla | Propósito |
|---|---|
| `admin_users` | Administradores del Maestro |
| `admin_roles` | Roles de admin (ej: `superadmin`, `operator`, `viewer`) |
| `admin_permissions` | Permisos granulares |
| `admin_user_roles` | Pivot M-M users ↔ roles |
| `admin_role_permissions` | Pivot M-M roles ↔ permissions |

### Entidades de auditoría e historia

| Tabla | Propósito | Mutabilidad |
|---|---|---|
| `audit_log` | Toda acción administrativa | **INMUTABLE** (INSERT-only, triggers DB rechazan UPDATE/DELETE) |
| `branding_cache` | Cache del consumo de `/maestro/branding` por deployment | Mutable (TTL configurable) |
| `hooks_log` | Registro de hooks salientes y su outcome | INSERT-only |

---

## Esquema detallado

> Notación: `PK` = Primary Key, `FK` = Foreign Key, `UNIQUE` = unique constraint, `NOT NULL` = obligatorio.

### Tabla `companies`

```sql
companies (
  id              UUID PK,
  slug            VARCHAR(50) UNIQUE NOT NULL,    -- regex ^[a-z0-9][a-z0-9-]{2,49}[a-z0-9]$
  name            VARCHAR(255) NOT NULL,
  status          VARCHAR(20) NOT NULL,            -- enum: active | suspended
  contact_email   VARCHAR(255),
  notes           TEXT,
  created_at      TIMESTAMPTZ NOT NULL DEFAULT NOW(),
  updated_at      TIMESTAMPTZ NOT NULL DEFAULT NOW(),
  deleted_at      TIMESTAMPTZ                      -- soft delete
)
INDEX companies_slug_idx ON companies(slug)
INDEX companies_status_idx ON companies(status) WHERE deleted_at IS NULL
```

**Reglas**:
- `slug` es inmutable una vez creada la empresa (parte del naming de contenedores y redes Docker).
- `status = "suspended"` impide provisionar nuevos deployments para esta empresa pero NO destruye los existentes.
- `deleted_at` (soft delete) preserva la historia; los deployments de la empresa pasan a `destroyed`.

### Tabla `applications`

```sql
applications (
  id                  UUID PK,
  slug                VARCHAR(50) UNIQUE NOT NULL,    -- regex ^[a-z0-9][a-z0-9-]{2,49}[a-z0-9]$
  name                VARCHAR(255) NOT NULL,
  description         TEXT,
  current_version     VARCHAR(20) NOT NULL,            -- SemVer
  maestro_yaml_hash   VARCHAR(64) NOT NULL,            -- SHA-256 del maestro.yaml registrado
  default_image       VARCHAR(255),                    -- ej: ghcr.io/org/app:1.0.0
  status              VARCHAR(20) NOT NULL,            -- enum: active | deprecated
  registered_at       TIMESTAMPTZ NOT NULL DEFAULT NOW(),
  updated_at          TIMESTAMPTZ NOT NULL DEFAULT NOW(),
  deleted_at          TIMESTAMPTZ
)
INDEX applications_slug_idx ON applications(slug)
INDEX applications_status_idx ON applications(status) WHERE deleted_at IS NULL
```

**Reglas**:
- Cada app se auto-registra desde su CI vía `POST /api/v2/apps/register` enviando su `maestro.yaml`.
- El registro valida el `maestro.yaml` contra el JSON Schema v2 (ver `06-CONTRATO-MAESTRO-YAML.md`).
- `current_version` se actualiza con cada nuevo registro; las versiones anteriores quedan en `applications_versions` (tabla histórica opcional, recomendada).

### Tabla `deployments`

```sql
deployments (
  id                  UUID PK,
  application_id      UUID NOT NULL FK -> applications(id),
  company_id          UUID NOT NULL FK -> companies(id),
  container_name      VARCHAR(63) UNIQUE NOT NULL,     -- ej: app-inventario-acme
  db_container_name   VARCHAR(63) UNIQUE,              -- ej: db-inventario-acme; NULL si requires.database = none
  network_name        VARCHAR(63) UNIQUE NOT NULL,     -- ej: app-inventario-acme-net
  app_url             VARCHAR(500) NOT NULL,           -- URL pública (target="_blank")
  app_internal_port   INTEGER NOT NULL,                -- coincide con requires.ports.app
  status              VARCHAR(20) NOT NULL,            -- enum: provisioning | starting | healthy | degraded | suspended | destroyed | purged
  resources_memory    VARCHAR(10) NOT NULL,            -- enum: 256m | 512m | 1g | 2g | 4g
  resources_cpu       NUMERIC(3,2) NOT NULL,           -- 0.25 - 4.00
  image_ref           VARCHAR(500) NOT NULL,           -- ej: ghcr.io/org/app@sha256:...
  provisioned_at      TIMESTAMPTZ,
  destroyed_at        TIMESTAMPTZ,
  purge_eligible_at   TIMESTAMPTZ,                     -- destroyed_at + 90 days
  last_health_check_at TIMESTAMPTZ,
  consecutive_health_failures INTEGER NOT NULL DEFAULT 0,
  created_at          TIMESTAMPTZ NOT NULL DEFAULT NOW(),
  updated_at          TIMESTAMPTZ NOT NULL DEFAULT NOW(),
  UNIQUE (application_id, company_id) WHERE status NOT IN ('destroyed', 'purged')
)
INDEX deployments_status_idx ON deployments(status)
INDEX deployments_company_idx ON deployments(company_id)
INDEX deployments_application_idx ON deployments(application_id)
```

**Reglas**:
- **Constraint UNIQUE parcial**: solo puede existir UN deployment activo (`status NOT IN ('destroyed', 'purged')`) por par `(application_id, company_id)`. Esta es la traducción a SQL del no-negociable de single-tenant físico.
- `purge_eligible_at = destroyed_at + 90 days`. Antes de esa fecha la BD del deployment NO se borra (ver no-negociable de retención de 90 días).
- `consecutive_health_failures` se resetea a 0 cuando el health check responde 200; las acciones correctivas (restart, alerta, suspensión) son escalonadas por este contador.

### Tabla `api_keys`

```sql
api_keys (
  id              UUID PK,
  deployment_id   UUID NOT NULL FK -> deployments(id),
  key_hash        BYTEA NOT NULL,                    -- AES-256(MAESTRO_API_KEY) usando MAESTRO_ENCRYPTION_KEY
  key_preview     VARCHAR(8) NOT NULL,                -- primeros 4 chars + "..." para identificación visual
  status          VARCHAR(20) NOT NULL,                -- enum: active | rotated | revoked
  created_at      TIMESTAMPTZ NOT NULL DEFAULT NOW(),
  rotated_at      TIMESTAMPTZ,
  expires_at      TIMESTAMPTZ,                         -- recomendado: created_at + 90 days
  UNIQUE (deployment_id, status) WHERE status = 'active'
)
INDEX api_keys_deployment_idx ON api_keys(deployment_id)
```

**Reglas**:
- **Constraint UNIQUE parcial**: solo UNA api_key activa por deployment a la vez (durante rotación, la nueva entra como `active` y la vieja pasa a `rotated`).
- `key_hash` cifrado con AES-256 usando la clave maestra `MAESTRO_ENCRYPTION_KEY` (ENV var del Maestro mismo). El descifrado solo ocurre al inyectar la key en el contenedor de la app.
- Al rotar: se genera nueva key, se actualiza la ENV var `MAESTRO_API_KEY` en el contenedor del deployment (sin downtime), la vieja queda como `rotated` por 24h para grace period y luego pasa a `revoked`.
- `key_preview` (ej: `f8a3...`) permite a los admins identificar la key sin exponerla.

### Tabla `webhook_secrets`

```sql
webhook_secrets (
  id              UUID PK,
  deployment_id   UUID NOT NULL FK -> deployments(id),
  secret_hash     BYTEA NOT NULL,                    -- AES-256(MAESTRO_WEBHOOK_SECRET)
  secret_preview  VARCHAR(8) NOT NULL,
  status          VARCHAR(20) NOT NULL,                -- enum: active | rotated | revoked
  created_at      TIMESTAMPTZ NOT NULL DEFAULT NOW(),
  rotated_at      TIMESTAMPTZ,
  UNIQUE (deployment_id, status) WHERE status = 'active'
)
INDEX webhook_secrets_deployment_idx ON webhook_secrets(deployment_id)
```

Mismas reglas que `api_keys` aplicadas a webhook secrets.

### Tablas de auth de admins

```sql
admin_users (
  id                  UUID PK,
  email               VARCHAR(255) UNIQUE NOT NULL,
  password_hash       VARCHAR(255) NOT NULL,           -- bcrypt cost >= 12 o argon2id
  name                VARCHAR(255),
  is_active           BOOLEAN NOT NULL DEFAULT TRUE,
  last_login_at       TIMESTAMPTZ,
  failed_login_count  INTEGER NOT NULL DEFAULT 0,
  locked_until        TIMESTAMPTZ,
  created_at          TIMESTAMPTZ NOT NULL DEFAULT NOW(),
  updated_at          TIMESTAMPTZ NOT NULL DEFAULT NOW(),
  deleted_at          TIMESTAMPTZ
)
INDEX admin_users_email_idx ON admin_users(email)

admin_roles (
  id           UUID PK,
  slug         VARCHAR(50) UNIQUE NOT NULL,             -- ej: superadmin, operator, viewer
  name         VARCHAR(100) NOT NULL,
  description  TEXT,
  is_system    BOOLEAN NOT NULL DEFAULT FALSE,          -- true para roles definidos por el sistema (no editables)
  created_at   TIMESTAMPTZ NOT NULL DEFAULT NOW()
)

admin_permissions (
  id           UUID PK,
  key          VARCHAR(100) UNIQUE NOT NULL,            -- ej: companies.create, deployments.destroy
  description  TEXT,
  group_name   VARCHAR(50)                              -- ej: companies, deployments, audit
)

admin_user_roles (
  admin_user_id UUID NOT NULL FK -> admin_users(id),
  admin_role_id UUID NOT NULL FK -> admin_roles(id),
  granted_at    TIMESTAMPTZ NOT NULL DEFAULT NOW(),
  granted_by    UUID FK -> admin_users(id),
  PRIMARY KEY (admin_user_id, admin_role_id)
)

admin_role_permissions (
  admin_role_id        UUID NOT NULL FK -> admin_roles(id),
  admin_permission_id  UUID NOT NULL FK -> admin_permissions(id),
  PRIMARY KEY (admin_role_id, admin_permission_id)
)
```

**Reglas**:
- El rol `superadmin` es de sistema (`is_system = TRUE`), tiene TODOS los permisos definidos, no puede borrarse ni editarse.
- El admin canónico `admin@llyasoc.com` se siembra en la fase 05-seeding del Maestro (idempotente), con rol `superadmin` y la password leída de la ENV var `SUPERADMIN_INITIAL_PASSWORD`.
- Login con bcrypt/argon2; bloqueo por `failed_login_count >= 5` durante 15 minutos (`locked_until`).
- Audit log obligatorio para login (success/failure), logout, cambios de password, cambios de roles.

### Tabla `audit_log` (INMUTABLE)

```sql
audit_log (
  id              UUID PK,
  timestamp       TIMESTAMPTZ NOT NULL DEFAULT NOW(),    -- precision ms
  actor_user_id   UUID FK -> admin_users(id),            -- NULL si la acción es del sistema (ej: cron)
  actor_ip        INET,
  user_agent      TEXT,
  action          VARCHAR(100) NOT NULL,                  -- ej: company.create, deployment.destroy, api_key.rotate, login.success
  resource_type   VARCHAR(50),
  resource_id     UUID,
  payload_before  JSONB,
  payload_after   JSONB,
  request_id      UUID                                    -- correlación con logs
)
INDEX audit_log_timestamp_idx ON audit_log(timestamp DESC)
INDEX audit_log_actor_idx ON audit_log(actor_user_id, timestamp DESC)
INDEX audit_log_resource_idx ON audit_log(resource_type, resource_id)
INDEX audit_log_action_idx ON audit_log(action)
```

**Triggers de inmutabilidad** (PostgreSQL):

```sql
CREATE OR REPLACE FUNCTION audit_log_no_update_delete()
RETURNS TRIGGER AS $$
BEGIN
  RAISE EXCEPTION 'audit_log is immutable; UPDATE and DELETE are not allowed';
END;
$$ LANGUAGE plpgsql;

CREATE TRIGGER audit_log_block_update BEFORE UPDATE ON audit_log
  FOR EACH ROW EXECUTE FUNCTION audit_log_no_update_delete();

CREATE TRIGGER audit_log_block_delete BEFORE DELETE ON audit_log
  FOR EACH ROW EXECUTE FUNCTION audit_log_no_update_delete();
```

Cualquier `UPDATE` o `DELETE` sobre `audit_log` falla con error explícito. Esta es la implementación del No-negociable doce.

### Tabla `branding_cache`

```sql
branding_cache (
  deployment_id     UUID PK FK -> deployments(id),
  company_name      VARCHAR(255) NOT NULL,
  logo_url          VARCHAR(500) NOT NULL,
  primary_color     VARCHAR(7),                          -- hex (opcional)
  favicon_url       VARCHAR(500),                        -- opcional
  fetched_at        TIMESTAMPTZ NOT NULL DEFAULT NOW(),
  ttl_expires_at    TIMESTAMPTZ NOT NULL,
  fetch_status      VARCHAR(20) NOT NULL,                -- enum: ok | unauthorized | timeout | server_error
  consecutive_failures INTEGER NOT NULL DEFAULT 0
)
INDEX branding_cache_ttl_idx ON branding_cache(ttl_expires_at)
```

**Reglas**:
- TTL default: 6 horas (configurable). Antes del TTL, el portal lee del cache; tras el TTL, un job re-consume `/maestro/branding` de la app.
- Tras 3 fallos consecutivos (`fetch_status != 'ok'`), el deployment se marca como `degraded` y se alerta al admin.
- Endpoint `POST /api/v2/branding/{deployment_id}/refresh` permite forzar refresh manual (audit logged).

### Tabla `hooks_log`

```sql
hooks_log (
  id              UUID PK,
  deployment_id   UUID NOT NULL FK -> deployments(id),
  event_id        UUID NOT NULL,                          -- UUID v4 incluido en el body del hook
  event_type      VARCHAR(50) NOT NULL,                   -- enum: on_user_added | on_user_removed | on_company_license_granted | on_company_license_revoked
  attempt         INTEGER NOT NULL DEFAULT 1,             -- 1, 2, 3 con backoff exponencial
  status          VARCHAR(20) NOT NULL,                   -- enum: success | failed | retry | abandoned
  http_status     INTEGER,
  response_body   TEXT,                                    -- truncado a 1KB; sin headers sensibles
  triggered_at    TIMESTAMPTZ NOT NULL DEFAULT NOW(),
  responded_at    TIMESTAMPTZ
)
INDEX hooks_log_deployment_idx ON hooks_log(deployment_id, triggered_at DESC)
INDEX hooks_log_event_idx ON hooks_log(event_id)
INDEX hooks_log_status_idx ON hooks_log(status)
```

**Reglas**:
- INSERT-only en la práctica (no se ejecutan UPDATE/DELETE en código), aunque sin trigger restrictivo (a diferencia de `audit_log`).
- Cada `event_id` se respeta para idempotencia: la app debe deduplicar por `event_id`.

---

## Relaciones clave (resumen)

```
companies (1) ─── (N) deployments
applications (1) ─── (N) deployments
deployments (1) ─── (1) api_keys [active]
deployments (1) ─── (1) webhook_secrets [active]
deployments (1) ─── (1) branding_cache
deployments (1) ─── (N) hooks_log
admin_users (N) ──── (M) admin_roles ──── (M) admin_permissions
admin_users (1) ─── (N) audit_log [actor]
```

NO hay relación entre `companies/applications/deployments` y `admin_users`: los admins son globales, no pertenecen a ninguna empresa específica. Tampoco hay relación con usuarios finales de las apps (esos viven en las BDs propias de cada deployment).

---

## Reglas de integridad y negocio

1. **Single deployment por par app+empresa activo**: la constraint `UNIQUE (application_id, company_id) WHERE status NOT IN ('destroyed', 'purged')` lo enforza a nivel BD.
2. **Inmutabilidad del audit log**: triggers SQL bloquean UPDATE/DELETE.
3. **Cifrado de secretos**: `api_keys.key_hash` y `webhook_secrets.secret_hash` se almacenan AES-256. La clave maestra `MAESTRO_ENCRYPTION_KEY` está en una ENV var del Maestro y NO en BD.
4. **Soft delete con preservación**: `companies` y `applications` usan soft delete (`deleted_at`) para preservar referencias en audit log. `deployments` no usa soft delete; pasa por estados explícitos hasta `purged`.
5. **Retención post-destrucción**: deployments destruidos preservan su BD durante 90 días (`purge_eligible_at`). El purgado requiere confirmación explícita del PO (registrada en audit log).
6. **Consistencia de naming**: `deployments.container_name`, `deployments.db_container_name`, `deployments.network_name` siguen el patrón `<role>-<app_slug>-<company_slug>` con longitud total ≤ 63 chars (límite Linux hostname).
7. **Persistencia entre versiones**: ninguna migración de schema borra datos sin confirmación del PO. Migraciones expand-then-contract para cambios destructivos. Ver `framework-agentico/core/RULES.md` sección `politica_de_persistencia_de_datos`.

---

## Migraciones recomendadas

- Idempotentes: re-ejecutar una migración no rompe el estado.
- Una migración por cambio lógico (no agrupar cambios no relacionados).
- Migraciones reversibles donde sea posible (mediante migración inversa explícita), excepto cuando reverse-engineering perdería datos.
- Antes de cada migración del schema del Maestro, backup completo de la BD del Maestro (ver no-negociable trece).

---

## Referencias normativas

- `01-PREMISAS-Y-NO-NEGOCIABLES.md` — premisas y no-negociables que este modelo cumple.
- `03-AUTENTICACION-Y-AUTORIZACION.md` — uso de las tablas `admin_*` para login propio del Maestro.
- `04-INFRAESTRUCTURA-DOCKER.md` — uso de `deployments` por el motor de provisioning.
- `06-CONTRATO-MAESTRO-YAML.md` — formato del `maestro.yaml` cuyo hash queda registrado en `applications`.
- `09-SEGURIDAD.md` — cifrado AES-256 y manejo de secretos.
- `framework-agentico/core/RULES.md` — sección `politica_de_persistencia_de_datos` (cambios destructivos requieren confirmación PO).

---

## Historial de revisiones

| Versión | Fecha | Cambio |
|---|---|---|
| 4.0.0 | 2026-05-07 | Versión inicial v4. Reescribe el modelo eliminando `users` global, multi-tenancy lógica, pivots de usuarios contra apps. Introduce `deployments`, `api_keys`, `webhook_secrets`, `branding_cache`, `hooks_log`, `admin_users` (auth propia del Maestro). Reemplaza al v1 (legacy en `legacy/v3/PremisaWebMaestro/02-MODELO-DE-DATOS.md`). |
