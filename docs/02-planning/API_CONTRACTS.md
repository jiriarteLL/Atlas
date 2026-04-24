# Contratos de API — Maestro Platform V1

> **Fase:** 02-Planning
> **Agente:** api-designer
> **Fecha:** 2026-04-16
> **Proyecto:** PRJ-MAESTRO-V1

---

## 1. Convenciones Generales

### 1.1 Base URL y versionado

- **Base**: `https://maestro.<MAESTRO_BASE_DOMAIN>/api`
- **Versionado**: prefijo `/v1/` para endpoints públicos del Maestro consumidos por apps huésped y CI/CD. Ejemplos:
  - `/api/v1/auth/*` — público
  - `/api/v1/apps/register` — público (consumido por CI/CD de apps)
  - `/api/v1/inventory/context` — público
  - `/api/v1/gateway/{target}/*` — público
- Endpoints internos del portal (`/api/admin/*`, `/api/portal/*`) **no** llevan versión porque evolucionan en lockstep con el portal (monolito frontend+backend acoplado).
- **ForwardAuth** (`/api/auth/validate`) sin `/v1/` por compatibilidad con config Traefik declarativa.

### 1.2 Formato de URLs

- RESTful: `/api/admin/<recurso-en-plural>` para colecciones, `/api/admin/<recurso>/<id>` para ítems.
- kebab-case en rutas (`/instance-events`, no `/instanceEvents`).
- Verbos HTTP estándar: GET (read), POST (create/action), PUT (full update, raro), PATCH (partial update), DELETE.

### 1.3 Autenticación

Tres zonas:

| Zona | Auth | Ejemplo |
|---|---|---|
| **Público sin auth** | ninguna | GET `/api/platform/health`, GET `/api/auth/microsoft/redirect`, GET `/.well-known/jwks.json` |
| **Auth por token (Bearer JWT)** | `Authorization: Bearer <jwt>` validado por middleware del Maestro | GET `/api/auth/me`, GET `/api/portal/my-apps`, POST `/api/admin/*` |
| **Auth por ForwardAuth** | Traefik ya validó; headers `X-Auth-*` presentes | apps huésped (fuera del Maestro); `/api/inventory/context` (para SDK) |
| **Auth por HMAC** | header `X-Maestro-Webhook-Secret` firmado HMAC-SHA256 | hooks entrantes no implementados V1; reservado |
| **Auth por CI/CD token** | header `X-Maestro-App-Secret` único por app | POST `/api/v1/apps/register` |

### 1.4 Formato de Response estándar

**Success**:
```json
{
  "data": { ... } | [ ... ],
  "meta": {
    "request_id": "req_01HY...",
    "timestamp": "2026-04-16T14:23:01.234Z"
  },
  "pagination": {          // solo si collection
    "cursor_next": "...",  // null si no hay más
    "cursor_prev": "...",
    "per_page": 50,
    "total_estimate": 1234
  }
}
```

**Error**:
```json
{
  "error": {
    "code": "AUTH_TOKEN_EXPIRED",
    "message": "El token JWT ha expirado",
    "details": {
      "expired_at": "2026-04-16T13:23:01Z"
    }
  },
  "meta": {
    "request_id": "req_01HY...",
    "timestamp": "2026-04-16T14:23:01.234Z"
  }
}
```

### 1.5 Códigos de error canónicos (no exhaustivo)

| Code | HTTP | Significado |
|---|---|---|
| `VALIDATION_FAILED` | 422 | Datos de request no pasan validación |
| `AUTH_TOKEN_MISSING` | 401 | No hay Authorization header |
| `AUTH_TOKEN_INVALID` | 401 | Token malformado o firma inválida |
| `AUTH_TOKEN_EXPIRED` | 401 | Token vencido |
| `AUTH_TOKEN_REVOKED` | 401 | Token revocado (logout o revocación admin) |
| `AUTH_COMPANY_MISMATCH` | 403 | El user no pertenece a la empresa solicitada |
| `PERMISSION_DENIED` | 403 | No tiene permisos para la acción |
| `RESOURCE_NOT_FOUND` | 404 | El recurso no existe o fue soft-deleted |
| `RESOURCE_CONFLICT` | 409 | Conflicto de estado (ej: provisionar instancia duplicada) |
| `RATE_LIMIT_EXCEEDED` | 429 | Demasiadas requests |
| `INTERNAL_ERROR` | 500 | Fallo no controlado; se loguea con request_id |
| `SERVICE_UNAVAILABLE` | 503 | BD o Redis caídos |
| `CONTRACT_INVALID` | 422 | maestro.yaml inválido al registrar app |
| `PROVISIONING_FAILED` | 500 | Docker API reporta error |

### 1.6 Paginación

Todas las colecciones usan **cursor-based pagination**:

- Query params: `?cursor=<opaque>&per_page=50` (default 20, máx 100).
- Response incluye `pagination.cursor_next` y `cursor_prev`.
- Orden default: `created_at DESC` salvo indicación contraria en el endpoint.

### 1.7 Rate limiting

- Default: 100 req/min/IP (RF-043), 1000 req/min/user autenticado.
- Endpoints de login: 10 req/min/IP.
- Configurable en `.env`.
- Response 429 incluye `Retry-After` header.

### 1.8 Request ID y trazabilidad

- Middleware global inyecta `X-Request-Id` si no viene y propaga en toda la cadena (logs, hooks, audit_log).
- Formato: ULID (`req_01HY...`).

### 1.9 CORS

- V1: Maestro backend **no** acepta cross-origin requests salvo del portal (`VITE_API_BASE_URL`). Default `Access-Control-Allow-Origin: <MAESTRO_BASE_DOMAIN>`.
- Apps huésped NO hacen requests al Maestro desde el browser; todo va vía Traefik que les inyecta headers.

---

## 2. Endpoints

Organizados por módulo. Cada endpoint se describe: Method, Path, Auth, Request, Response, Errores típicos.

### 2.1 Módulo Auth

#### `POST /api/auth/login`
- **Auth**: ninguna
- **Request**: `{ "email": "string", "password": "string" }`
- **Response 200**: `{ "data": { "access_token": "jwt", "refresh_token": "opaque", "expires_in": 3600, "user": { ...User } } }`
- **Errores**: `VALIDATION_FAILED`, `AUTH_CREDENTIALS_INVALID` (401), `AUTH_USER_DISABLED` (403), `RATE_LIMIT_EXCEEDED`.

#### `GET /api/auth/microsoft/redirect`
- **Auth**: ninguna
- **Response 302** con redirect a Microsoft Entra ID (URL con state param).

#### `GET /api/auth/microsoft/callback`
- **Auth**: ninguna (state verifica)
- **Query**: `?code=<oauth_code>&state=<state>`
- **Response 302**: redirect a portal con `access_token` y `refresh_token` en cookies httpOnly, o a `/auth/error` con query `?error=...` si falló.
- **Side effect**: si `entra_id_sub` no existe → crea user (si `MICROSOFT_AUTO_PROVISION=true`) o rechaza.

#### `POST /api/auth/refresh`
- **Auth**: `Authorization: Bearer <refresh_token>`
- **Response 200**: `{ "data": { "access_token": "...", "refresh_token": "...", "expires_in": 3600 } }` (rotación: el refresh_token anterior queda revocado)
- **Errores**: `AUTH_TOKEN_INVALID`, `AUTH_TOKEN_EXPIRED`, `AUTH_TOKEN_REVOKED`.

#### `POST /api/auth/logout`
- **Auth**: Bearer JWT
- **Response 204**
- **Side effect**: access_token y refresh_token revocados (ambos a `revoked_tokens`), cache Redis invalidada.

#### `POST /api/auth/switch-company`
- **Auth**: Bearer JWT
- **Request**: `{ "company_id": "uuid" }`
- **Response 200**: `{ "data": { "access_token": "...nuevo JWT con company_id actualizado...", "expires_in": 3600 } }`
- **Errores**: `AUTH_COMPANY_MISMATCH` si el user no pertenece a esa empresa.

#### `GET /api/auth/me`
- **Auth**: Bearer JWT
- **Response 200**: `{ "data": { ...User, "active_company": {...}, "companies": [...], "roles": [...], "permissions": [...] } }`

#### `GET /api/auth/validate` (consumido por Traefik ForwardAuth)
- **Auth**: header `Authorization: Bearer <jwt>` (Traefik lo pasa tal cual)
- **Response 200 con headers**:
  - `X-Auth-User-Id: <uuid>`
  - `X-Auth-User-Email: <email>`
  - `X-Auth-Company-Id: <uuid>`
  - `X-Auth-Roles: role1,role2,role3` (comma-separated)
  - `X-Auth-Permissions: perm1,perm2,perm3`
- **Response 401** sin body si token inválido/expirado/revocado.
- **SLA**: p95 < 50ms (RNF-001). Implementación: lookup Redis cache (key `token:<jti>`, TTL 300s) → fallback a `oauth_access_tokens` + `revoked_tokens`.

### 2.2 Módulo Portal (para el usuario logueado desde el portal React)

#### `GET /api/portal/my-apps`
- **Auth**: Bearer JWT
- **Response 200**: `{ "data": [{ "app_id": "uuid", "slug": "string", "name": "string", "url": "https://slug-company.maestro.local", "status": "healthy|starting|...", "license_active": true, "license_expires_at": null }] }`
- **Fuente**: join `application_user` × `application_company` × `instances`.

#### `GET /api/portal/context`
- **Auth**: Bearer JWT
- **Response 200**: `{ "data": { "user": {...}, "active_company": {...}, "available_companies": [...] } }`

### 2.3 Módulo Admin — Companies

#### `GET /api/admin/companies`
- **Auth**: Bearer JWT + permiso `platform.companies:list` (solo `is_platform_admin`)
- **Query**: `?cursor&per_page&search&status`
- **Response 200**: `{ "data": [Company], "pagination": {...} }`

#### `POST /api/admin/companies`
- **Request**: `{ "name": "string", "slug": "[a-z0-9-]{3,50}", "subdomain": "...", "metadata": {...} }`
- **Response 201**: `{ "data": Company }`
- **Audit**: `companies.create`.

#### `GET /api/admin/companies/{id}`
#### `PATCH /api/admin/companies/{id}`
#### `DELETE /api/admin/companies/{id}` (soft delete)

### 2.4 Módulo Admin — Users

#### `GET /api/admin/users`
- Filtros: `?company_id&is_platform_admin&search`
- Paginación estándar.

#### `POST /api/admin/users`
- **Request**: `{ "email": "string", "display_name": "string", "password": "string|null", "is_platform_admin": false, "memberships": [{ "company_id": "uuid", "roles": ["admin"] }] }`
- **Response 201**: `{ "data": User }`
- **Audit**: `users.create`. Dispara `on_user_added` a las apps del las empresas membresadas.

#### `GET/PATCH/DELETE /api/admin/users/{id}`

#### `POST /api/admin/users/{id}/memberships`
#### `DELETE /api/admin/users/{id}/memberships/{company_id}`

### 2.5 Módulo Admin — Applications

#### `GET /api/admin/applications`
#### `POST /api/admin/applications` — alta manual (sin CI/CD)
#### `GET/PATCH/DELETE /api/admin/applications/{id}`

#### `GET /api/admin/applications/{id}/licenses`
#### `POST /api/admin/applications/{id}/licenses`
- **Request**: `{ "company_id": "uuid", "tier": "default", "expires_at": null }`
- **Response 201**: registro en `application_company`.

#### `POST /api/admin/applications/{app_id}/user-access`
- Asignar permisos del usuario en una app específica dentro de una empresa (pivote `application_user`).

### 2.6 Módulo Admin — Instances

#### `GET /api/admin/instances`
- Filtros: `?company_id&application_id&status`
- Respuesta incluye `current_health`, `lifecycle_summary`.

#### `POST /api/admin/instances`
- **Request**: `{ "application_id": "uuid", "company_id": "uuid", "resources": { "memory": "512m", "cpu": 0.5 }? }`
- **Response 202 Accepted**: `{ "data": { "instance_id": "uuid", "status": "provisioning" } }` (async; job dispatched)
- **Errores**: `CONTRACT_INVALID` (maestro.yaml de la app ya no es válido), `RESOURCE_CONFLICT` (instancia ya existe para ese (app, company)).

#### `POST /api/admin/instances/{id}/stop`
#### `POST /api/admin/instances/{id}/start`
#### `POST /api/admin/instances/{id}/restart`
#### `DELETE /api/admin/instances/{id}` (marca `destroyed`; purga en 90 días)
#### `POST /api/admin/instances/{id}/restore` (si aún no se purgó)

#### `GET /api/admin/instances/{id}/health-history?from=&to=`
#### `GET /api/admin/instances/{id}/lifecycle-events?from=&to=`
#### `POST /api/admin/instances/{id}/exec` — para operaciones de debug V1 muy limitadas (audit + rate limit alto).

### 2.7 Módulo Admin — Audit Log

#### `GET /api/admin/audit-log`
- **Query**: `?actor_user_id&company_id&action&resource_type&from&to&cursor`
- **Response 200**: paginado.
- **Restricciones**: solo `is_platform_admin` o rol `audit-viewer` asignado.

### 2.8 Módulo Platform (público, consumido por apps huésped y CI/CD)

#### `GET /api/platform/health`
- **Auth**: ninguna
- **Response 200**: `{ "status": "ok", "checks": { "db": "ok", "redis": "ok", "docker": "ok" }, "version": "1.0.0" }` (o `503` con `checks` detallado si algo falla).

#### `GET /.well-known/jwks.json`
- **Auth**: ninguna
- Set público de claves públicas Passport para apps que quieran validar JWT por su cuenta.

#### `POST /api/v1/apps/register`
- **Auth**: `X-Maestro-App-Secret: <secret>` (emitido al alta de la app en el admin)
- **Request**:
  ```json
  {
    "name": "my-app",
    "slug": "my-app",
    "version": "1.2.3",
    "image": "ghcr.io/org/my-app:1.2.3",
    "maestro_yaml": "<YAML como string>"
  }
  ```
- **Response 200**: actualizado.
- **Response 201**: creado (primera registración).
- **Errores**: `CONTRACT_INVALID` con detalles del validador.

#### `GET /api/v1/inventory/context`
- **Auth**: ForwardAuth headers (Traefik ya validó; app huésped proxy-ea a este endpoint con los headers).
- **Response 200**: `{ "data": { "user": {...}, "company": {...}, "application": { "slug": "...", "version": "...", "tier": "..." }, "maestro": { "base_domain": "...", "version": "..." } } }`
- Uso: el SDK de la app llama a este endpoint para conocer su contexto sin hardcodear.

#### `POST /api/v1/gateway/{target_app_slug}/{path}`
- **Auth**: ForwardAuth headers.
- **Request body**: forwarded as-is al target.
- **Side effects**:
  - Verifica que la app origen y target están en la misma empresa.
  - Verifica permiso `gateway:{target_app_slug}` en el usuario.
  - Firma HMAC en header `X-Maestro-Gateway-Signature` que la app target verifica con su SDK.
  - Registra en `audit_log` (`gateway.forward`).
- **Response**: proxy transparente al target + headers `X-Maestro-Gateway: true, X-Maestro-Source-App: <slug>`.

### 2.9 Módulo Apps-Huésped facing — Hooks salientes (NO endpoints en el Maestro)

El Maestro **envía** hooks a las apps huésped; estos son endpoints **en la app huésped** (definidos en su `maestro.yaml`). El Maestro solo orquesta:

- `POST <app.hooks.on_user_added>` — payload `{ "user_id", "email", "display_name", "company_id", "roles", "permissions" }` + headers `X-Maestro-Webhook-Secret: <hmac>`, `X-Maestro-Event: on_user_added`, `X-Maestro-Delivery-Id: <uuid>`.
- `POST <app.hooks.on_user_removed>` — idem con evento correspondiente.
- `POST <app.hooks.on_company_license_granted>` — reservado; opcional V1.
- `POST <app.hooks.on_company_license_revoked>` — reservado.

Retries: exponential backoff (1s, 5s, 30s, 2m, 10m). Tras 5 intentos fallidos → queda en `hooks_deliveries.status='failed'` y aparece en dashboard admin.

---

## 3. JSON Schema del contrato `maestro.yaml`

Ubicación: `docs/02-planning/schema/maestro.yaml.schema.json` (a generar en Fase 03 junto con el SDK/CLI).

Estructura declarativa esperada:

```yaml
apiVersion: maestro.platform/v1
kind: Application
metadata:
  name: my-app                 # regex [a-z0-9][a-z0-9-]{2,49}
  version: 1.2.3               # SemVer
requires:
  database: postgres           # postgres|mysql|mongo|sqlite|none
  ports:
    app: 3000                  # 1024..65535
health:
  endpoint: /health
  timeout_seconds: 5           # max 5
auth:
  mode: header                 # constante
  headers:
    - X-Auth-User-Id
    - X-Auth-User-Email
    - X-Auth-Company-Id
    - X-Auth-Roles
    - X-Auth-Permissions
resources:
  memory: 512m                 # max 4g
  cpu: 0.5                     # 0.25..4.0
hooks:                         # opcional
  on_user_added: /hooks/user-added
  on_user_removed: /hooks/user-removed
```

El validador del CLI y del endpoint `/api/v1/apps/register` valida:
- nombre único en catálogo,
- rangos numéricos,
- presencia de campos obligatorios (`metadata.name`, `metadata.version`, `requires.database`, `requires.ports.app`, `health.endpoint`, `auth.mode`, `resources.memory`, `resources.cpu`).

---

## 4. Estrategia de Versionado

- **Maestro API pública (`/api/v1/*`)**: SemVer. Breaking change = `/api/v2/*` nuevo; se mantiene `/v1` por **mínimo 6 meses** o hasta que todas las apps huésped migren.
- **Maestro API interna (admin, portal)**: no versionada; evoluciona en lockstep con el portal (ambos en el mismo repo).
- **SDK @maestro/sdk-node**: SemVer estricto. Mayor = breaking; deprecation warnings al menos en una minor antes.
- **JSON Schema de maestro.yaml**: versionado en el campo `apiVersion: maestro.platform/v1`. Un schema v2 convive con v1 en el validador.
- **Deprecation policy**: endpoints deprecated responden con header `Deprecation: true, Sunset: <fecha>`. Al llegar `Sunset` se retiran.

---

## 5. Comunicación Inter-Servicios

Dentro del Maestro (monolito modular): todo vía llamadas directas a servicios PHP (inyección de dependencias); no hay I/O entre módulos.

Entre Maestro ↔ apps huésped:
- **Salida**: hooks firmados HMAC-SHA256 (§2.9).
- **Entrada**: solo vía Traefik con ForwardAuth; las apps no pueden llamar al Maestro excepto endpoints `/api/v1/inventory/context` y `/api/v1/gateway/*`.

Entre apps huésped:
- Solo vía `/api/v1/gateway/*` del Maestro (ADR-007 refuerza).
- Prohibida comunicación directa de red (enforcado por redes Docker aisladas).

---

## 6. Checklist de coherencia con otros artefactos

| Endpoint | RF cubierto | Tabla principal | Flujo UX |
|---|---|---|---|
| POST /api/auth/login | RF-001 | users + oauth_* | Flow: Login |
| GET /api/auth/microsoft/callback | RF-002 | users + oauth_* | Flow: Login Microsoft |
| GET /api/auth/validate | RF-003 | Redis + oauth_access_tokens | (Traefik) |
| POST /api/auth/refresh | RF-004 | oauth_refresh_tokens | transparente |
| POST /api/auth/logout | RF-005 | revoked_tokens | Logout btn |
| POST /api/auth/switch-company | RF-006 | company_user | Selector empresa |
| /api/admin/companies/* | RF-010 | companies | Admin panel |
| /api/admin/users/* | RF-011 | users + company_user | Admin panel |
| /api/admin/applications/* | RF-012 | applications | Admin panel |
| /api/admin/*/memberships | RF-013, RF-014, RF-015 | pivotes | Admin panel |
| /api/admin/audit-log | RF-021 | audit_log | Audit viewer |
| /api/admin/instances/* | RF-030–RF-034 | instances + health + lifecycle | Admin panel instances |
| /api/platform/health | RNF-060 | - | - |
| /api/v1/apps/register | RF-064, RF-070 | applications | (CI/CD) |
| /api/v1/inventory/context | RF-062 (SDK) | - | - |
| /api/v1/gateway/*/* | RF-080, RF-081 | audit_log | - |
| Hooks salientes (§2.9) | RF-090 | hooks_deliveries | - |

---

## 7. OpenAPI / generación de specs

Se genera `docs/02-planning/openapi.yaml` en Fase 03 (usando `Scribe` Laravel plugin o similar) como artefacto vivo sincronizado con el código. El spec es consumido por el SDK y el portal para tipado.
