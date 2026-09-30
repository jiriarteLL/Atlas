# Autenticación y Autorización en la Web Maestro

> **Versión:** v4 (framework agéntico v4 / contrato `maestro.platform/v2`)
> **Última revisión:** 2026-05-07
> **Estado:** vigente
> **Reemplaza a:** `legacy/v3/PremisaWebMaestro/03-AUTENTICACION-Y-AUTORIZACION.md` (modelo v1 / IdP centralizado con `X-Auth-*`).

---

## Propósito de este documento

Este documento describe el sistema completo de identidad y autorización de la **Web Maestro** v4. Cubre los tres planos de autenticación que existen en el ecosistema:

1. **Auth de admins de la Web Maestro** (login propio del Maestro para sus operadores).
2. **Auth server-to-server entre Maestro y apps huésped** (`X-Maestro-Api-Key` para `/maestro/branding`, `X-Maestro-Webhook-Secret` para hooks).
3. **Auth de usuarios finales de las apps**: NO la maneja el Maestro. Cada app huésped la implementa por sí misma. Este documento aclara los límites para que no haya confusión.

---

## Cambio fundamental respecto a v1

En v1 el Maestro era el **Identity Provider único** del ecosistema:

- Laravel Passport como servidor OAuth2.
- Microsoft Entra ID integrado.
- Tabla `users` global del Maestro.
- Validación de tokens vía Traefik **ForwardAuth** contra `/api/auth/validate` del Maestro.
- Inyección de headers `X-Auth-User-Id`, `X-Auth-User-Email`, `X-Auth-Company-Id`, `X-Auth-Roles`, `X-Auth-Permissions` en cada request a las apps.

En v4 ese modelo se invirtió:

- **El Maestro NO es Identity Provider** de los usuarios finales.
- Cada app huésped tiene su **propio login** (tabla `users`, password hash, tokens propios, middleware propio).
- Traefik en v4 **NO** usa ForwardAuth para apps huésped. Solo termina TLS y enruta tráfico.
- **NO** se inyectan headers `X-Auth-*`. Apps que los lean se rechazan en validación.

El Maestro sigue siendo IdP solo de **sí mismo** (sus admins): el rol `admin@llyasoc.com` se autentica con login propio del Maestro, mismo modelo que cualquier app huésped según el preset `web-maestro`.

---

## Plano 1: Auth de admins de la Web Maestro

### Modelo

El Maestro implementa para sus admins el **mismo modelo de auth propia** que cualquier app huésped. Esto significa que el Maestro v4 **es una app huésped de sí misma** para fines de auth.

Tablas usadas (definidas en `02-MODELO-DE-DATOS.md`):
- `admin_users` con `email`, `password_hash`, `is_active`, `last_login_at`, `failed_login_count`, `locked_until`.
- `admin_roles` (con `is_system` para roles del sistema como `superadmin`).
- `admin_permissions` (granulares: `companies.create`, `deployments.destroy`, `audit_log.read`, etc.).
- Pivots `admin_user_roles`, `admin_role_permissions`.

### Endpoints del plano admin

```
POST   /api/v2/auth/login          (email + password -> token)
POST   /api/v2/auth/logout         (invalida el token)
POST   /api/v2/auth/refresh        (refresh token -> nuevo access token)
GET    /api/v2/auth/me             (datos del admin autenticado)
POST   /api/v2/auth/password-change (requiere password actual + nueva)
```

`POST /api/v2/auth/login` y `POST /api/v2/auth/logout` son públicos (sin auth). Los demás requieren middleware de auth propio.

`GET /health` también es público (sin auth) para health checks externos.

### Token de acceso

Dos opciones soportadas (la implementación elige una):

**Opción A: Cookies de sesión**
- Cookie `maestro_session` con `HttpOnly`, `Secure`, `SameSite=Lax`.
- Backend mantiene sesión en BD o Redis con expiración corta (1h sliding window).
- Logout invalida la sesión.

**Opción B: JWT con refresh**
- Access token: JWT firmado con `JWT_SECRET`, expiración 1h, payload con `user_id`, `roles`, `permissions`, `iat`, `exp`.
- Refresh token: opaco, almacenado en BD, expiración 30 días.
- Logout invalida el refresh token.

**Reglas comunes**:
- `bcrypt` cost ≥ 12 o `argon2id` para `password_hash`. NUNCA texto plano, MD5, SHA1 ni SHA256 directo.
- Comparación de hash con timing-constant (provista por la librería).
- Bloqueo de cuenta tras 5 intentos fallidos consecutivos durante 15 minutos (`locked_until`).
- Rate limiting en `/login` (recomendado: 5 intentos/minuto/IP).

### Authorization (RBAC)

El middleware de auth carga `roles` y `permissions` del admin en el contexto del request. Cada endpoint protegido declara qué `permission` requiere:

```
DELETE /api/v2/deployments/{id}  ->  requiere permission "deployments.destroy"
POST   /api/v2/companies         ->  requiere permission "companies.create"
GET    /api/v2/audit_log         ->  requiere permission "audit_log.read"
```

El rol `superadmin` (de sistema, `is_system = TRUE`) tiene TODOS los permisos definidos. Otros roles se definen según necesidad operativa (ej: `operator` con permisos sobre deployments pero no sobre `audit_log` ni rotación de keys; `viewer` con solo lecturas).

### Audit log obligatorio

Cada evento de auth genera un registro en `audit_log`:

| Acción | Campos relevantes |
|---|---|
| `login.success` | `actor_user_id`, `actor_ip`, `user_agent` |
| `login.failure` | `actor_ip`, `user_agent`, `payload_before` (intento sin password) |
| `login.locked` | `actor_user_id`, `actor_ip` |
| `logout` | `actor_user_id`, `actor_ip` |
| `password.change` | `actor_user_id`, `actor_ip` |
| `role.granted` | `actor_user_id`, `resource_id` (target user), `payload_after` |
| `role.revoked` | igual con `payload_before` |

`audit_log` es **inmutable** (triggers DB rechazan UPDATE/DELETE). Ver `02-MODELO-DE-DATOS.md`.

### Seeding del superadmin

La fase 05-seeding del framework agéntico v4 (con preset `maestro-platform` activo, ver `framework-agentico/agents/presets/maestro-platform/PRESET.md` y `framework-agentico/phases/05-seeding.md`) ejecuta un seeder idempotente que:

1. Crea o verifica el rol `superadmin` con `is_system = TRUE` y todos los permisos definidos.
2. Crea (si no existe) al usuario `admin@llyasoc.com` con `password_hash` derivado de `SUPERADMIN_INITIAL_PASSWORD` (ENV var). Si la ENV var no existe o la password es débil (< 12 chars o blacklist), el seeder falla con exit ≠ 0.
3. Asigna el rol `superadmin` al usuario `admin@llyasoc.com` si no lo tiene.
4. Si el usuario ya existe, **NO toca su password** (idempotencia).
5. Logs sin password ni hash.

---

## Plano 2: Auth server-to-server entre Maestro y apps huésped

### 2.1 `X-Maestro-Api-Key` para `/maestro/branding`

**Flujo**:
1. Cuando el Maestro provisiona un deployment, genera una `MAESTRO_API_KEY` aleatoria (≥ 32 chars), la cifra con AES-256 y la almacena en `api_keys.key_hash`.
2. La key (en claro, solo en memoria) se inyecta como ENV var `MAESTRO_API_KEY` en el contenedor de la app durante el provisioning.
3. Un job periódico del Maestro (default cada 6h) ejecuta `GET <app_url>/maestro/branding` con header `X-Maestro-Api-Key: <key_en_claro>`.
4. La app valida el header en tiempo constante contra su ENV var `MAESTRO_API_KEY`.
5. Sin/con header inválido → `HTTP 401`.
6. Con válido → `HTTP 200` + JSON `{company_name, logo_url, primary_color?, favicon_url?}`.
7. El Maestro cachea la respuesta en `branding_cache` con TTL de 6h.

**Rotación**:
- `POST /api/v2/deployments/{id}/rotate-api-key` (requiere permiso del admin).
- Genera nueva key, actualiza la ENV var en el contenedor (sin downtime mediante restart escalonado), marca la vieja como `rotated` por 24h (grace period), luego `revoked`.
- Audit log: `api_key.rotate` con `actor_user_id`, `resource_id` (deployment), `payload_before` (preview de la vieja), `payload_after` (preview de la nueva).
- Recomendado: rotación automática cada 90 días (cronjob con audit log).

### 2.2 `X-Maestro-Webhook-Secret` y firma HMAC-SHA256 para hooks salientes

**Flujo**:
1. Al provisionar un deployment, el Maestro genera un `MAESTRO_WEBHOOK_SECRET` aleatorio (≥ 32 chars), lo cifra y almacena en `webhook_secrets.secret_hash`.
2. La secret se inyecta como ENV var `MAESTRO_WEBHOOK_SECRET` en el contenedor.
3. Cuando ocurre un evento (ej: `on_user_added`), el Maestro envía `POST <hook_url>` con:
   - Body JSON: `{event_id: "<uuid>", event_type: "on_user_added", timestamp: "<iso8601>", payload: {...}}`.
   - Header `X-Maestro-Webhook-Signature: t=<unix_ts>,v1=<hex_hmac>` donde `v1 = HMAC-SHA256(MAESTRO_WEBHOOK_SECRET, "<unix_ts>.<raw_body>")`.
4. La app **DEBE** verificar:
   - `|now - t| ≤ 300` segundos (anti-replay).
   - Recalcular el HMAC y comparar en tiempo constante.
   - Si no coincide → `HTTP 401`. El Maestro registra `hooks_log.status = failed` con `http_status = 401`.
5. La app **DEBE** procesar el evento de manera **idempotente** usando `event_id` para deduplicar (el Maestro reintenta hasta 3 veces con backoff exponencial: 30s, 2min, 10min).
6. La app **DEBE** responder `HTTP 200` (o `202 Accepted` si encola) en ≤ 5s.

**Eventos soportados**:
- `on_user_added` — usuario agregado a una empresa con licencia activa de la app.
- `on_user_removed` — usuario removido o licencia individual revocada.
- `on_company_license_granted` — empresa adquiere licencia de la app.
- `on_company_license_revoked` — empresa pierde licencia.

**Rotación**:
- Análogo a `api_keys`: `POST /api/v2/deployments/{id}/rotate-webhook-secret`. Audit log: `webhook_secret.rotate`.

### 2.3 Por qué dos credenciales separadas

`X-Maestro-Api-Key` y `X-Maestro-Webhook-Secret` son **credenciales separadas** por deployment. Razones:

- **Direccionalidad**: la api_key autentica requests del Maestro **hacia** la app (consumo de branding). El webhook_secret autentica requests del Maestro **hacia** la app (hooks). Aunque la dirección es la misma, los riesgos son distintos: el branding endpoint expone metadata de la empresa; los hooks ejecutan lógica de negocio.
- **Rotación independiente**: rotar una no invalida la otra.
- **Observabilidad**: separar permite trazar fallos (¿es el branding que falla o los hooks?) sin ambigüedad.

---

## Plano 3: Auth de usuarios finales de las apps huésped

### El Maestro NO la implementa

El Maestro v4 **NO autentica** a los usuarios finales de las apps huésped. **NO** mantiene tabla `users` global. **NO** emite tokens de identidad. **NO** consume credenciales de usuarios finales.

Cuando un usuario final de Empresa A quiere usar la App de Inventario, el flujo es:

1. El usuario navega al portal del Maestro.
2. El usuario admin del Maestro NO es el mismo que el usuario final; pero el portal del Maestro puede mostrar links a las apps que la empresa tiene licenciadas.
3. (Más comúnmente) la empresa comparte la URL del deployment de su app con sus empleados, sin pasar por el portal del Maestro.
4. El usuario final navega a `https://<app_slug>-<empresa>.<dominio>/login` o equivalente.
5. La app huésped muestra **su propio formulario de login**.
6. El usuario ingresa email + password.
7. La app valida contra **su propia tabla `users`** (con `password_hash` bcrypt/argon2id).
8. La app emite **su propio token** (cookie HttpOnly o JWT propio).
9. Cada request posterior: el middleware de la app valida el token. NO hay involucramiento del Maestro.

### Por qué este modelo

- **Aislamiento de datos**: cada app tiene sus usuarios, su lógica de roles/permisos específica del dominio, su política de password. El compromiso de una app no expone usuarios de otra.
- **Independencia operativa**: una app puede operar standalone si el Maestro está caído (relevante en transición Maestro v1 → Maestro v2).
- **Flexibilidad de stack**: cada app elige su librería de auth (Passport.js, Devise, Laravel Sanctum, FastAPI users, Django auth, etc.). El Maestro no impone.
- **Compliance**: regulaciones como GDPR son más simples cuando los datos personales no cruzan fronteras de aplicaciones innecesariamente.

### Lo único que el Maestro le dice a la app sobre sus usuarios

A través de hooks server-to-server (Plano 2.2):
- `on_user_added`: "agregamos a tu app un usuario con email X de la empresa que opera tu deployment".
- `on_user_removed`: "removimos al usuario con email X".

La app huésped recibe estos hooks y **decide** qué hacer (crear/desactivar el usuario en su tabla `users` propia, enviar email de bienvenida, etc.). El Maestro **NO** crea registros directamente en la BD de la app.

---

## Resumen de credenciales por capa

| Capa | Credencial | Origen | Destino | Verificación |
|---|---|---|---|---|
| Admin del Maestro | password (bcrypt/argon2id) | tabla `admin_users` | login del Maestro | timing-constant |
| Admin sesión | cookie/JWT del Maestro | login del Maestro | middleware del Maestro | firma + expiración |
| Maestro → app (branding) | `X-Maestro-Api-Key` | ENV var inyectada | endpoint `/maestro/branding` de la app | timing-safe-compare |
| Maestro → app (hooks) | `X-Maestro-Webhook-Signature` | HMAC-SHA256 del body | endpoint del hook en la app | recalcular HMAC + anti-replay |
| Usuario final → app | password (bcrypt/argon2id) | tabla `users` de la app | login de la app | timing-constant |
| Usuario sesión → app | cookie/JWT propio de la app | login de la app | middleware de la app | firma + expiración |

---

## Threat model resumido

**Amenaza 1**: bypass del registry vía credenciales filtradas.
- Mitigación: api_keys cifradas en BD, rotación automática cada 90 días, audit log de toda rotación, alerta en uso de keys revocadas.

**Amenaza 2**: escalada de privilegios en el portal admin.
- Mitigación: RBAC granular, rol `superadmin` único con auditoría especial, MFA recomendado para `superadmin` (a definir en `09-SEGURIDAD.md`).

**Amenaza 3**: replay attack en hooks.
- Mitigación: firma HMAC-SHA256 con timestamp + window de 300s; idempotencia por `event_id`.

**Amenaza 4**: leak de webhook secret en logs de la app.
- Mitigación: la app **NO DEBE** loguear el header `X-Maestro-Webhook-Signature` ni `MAESTRO_WEBHOOK_SECRET`. Validación por `security-auditor` en cada PR de la app.

**Amenaza 5**: timing attack contra api_key inválida.
- Mitigación: comparación timing-safe (`crypto.timingSafeEqual` o equivalente).

**Amenaza 6**: SQL injection en login.
- Mitigación: parametrized queries / ORM. Validación por `security-auditor`.

**Amenaza 7**: XSS en portal del Maestro.
- Mitigación: framework frontend con escaping automático, CSP estricta, cookies HttpOnly.

Detalle completo del threat model en `09-SEGURIDAD.md`.

---

## Referencias normativas

- `01-PREMISAS-Y-NO-NEGOCIABLES.md` — premisa uno (auth distribuida) y no-negociables 1, 5, 6.
- `02-MODELO-DE-DATOS.md` — tablas `admin_users`, `admin_roles`, `admin_permissions`, `api_keys`, `webhook_secrets`, `audit_log`.
- `06-CONTRATO-MAESTRO-YAML.md` — el contrato exige `auth.mode = "own"` y declara `branding.url`, `hooks.*`.
- `09-SEGURIDAD.md` — threat model completo y capas de defensa.
- `framework-agentico/core/PRESET_WEB_MAESTRO.md` — preset que aplica a apps huésped (incluye reglas de auth propia).
- `framework-agentico/agents/presets/maestro-platform/PRESET.md` — preset que aplica al Maestro mismo (impone que el login propio para sus admins cumpla `web-maestro`).
- `framework-agentico/phases/05-seeding.md` — fase de seeding del superadmin.
- `docs/APP_HUESPED_SPEC.md` — sección de auth lado app huésped.

---

## Historial de revisiones

| Versión | Fecha | Cambio |
|---|---|---|
| 4.0.0 | 2026-05-07 | Versión inicial v4. Reescribe el sistema de identidad con auth distribuida: el Maestro deja de ser IdP de usuarios finales; mantiene auth propia para sus admins; autentica server-to-server con `X-Maestro-Api-Key` y firma HMAC. Reemplaza al v1 (legacy en `legacy/v3/PremisaWebMaestro/03-AUTENTICACION-Y-AUTORIZACION.md`). |
