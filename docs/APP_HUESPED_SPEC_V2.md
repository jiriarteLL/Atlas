# Especificación Técnica de Aplicación Huésped — Maestro Platform v2

> **Documento normativo.** Vincula a todo equipo, interno o externo, que pretenda registrar una aplicación huésped en Maestro Platform v2.
>
> **Versión del contrato:** `maestro.platform/v2`
> **Framework agéntico:** v4
> **Última revisión:** 2026-05-06
> **Audiencia:** desarrolladores, tech leads, responsables de plataforma de equipos integradores.
> **Reemplaza a:** `docs/APP_HUESPED_SPEC.md` (v1 / framework v3) — deprecado.
> **Documento complementario:** `docs/APP_HUESPED_BEST_PRACTICES_V2.md` (no normativo).
> **Stack agnóstico:** los requisitos se expresan en términos de HTTP, headers, schemas y ENV vars; ningún stack específico es obligatorio.

---

## 0. Marco de cumplimiento

Las palabras clave **DEBE / NO DEBE / DEBERÍA / NO DEBERÍA / PUEDE** se interpretan según RFC 2119 / RFC 8174.

| Término | Significado | Consecuencia |
|---|---|---|
| **DEBE** / **OBLIGATORIO** | Requisito absoluto. | Bloqueo en `maestro-cli validate` o en registro contra el Maestro. |
| **NO DEBE** / **PROHIBIDO** | Prohibición absoluta. | Igual al anterior. |
| **DEBERÍA** / **RECOMENDADO** | Práctica esperada salvo justificación documentada. | Warning no bloqueante. |
| **PUEDE** / **OPCIONAL** | A discreción del equipo. | Sin consecuencia. |

> **Precedencia:** ante conflicto, prevalece este documento > `docs/CONVENCIONES_PLATAFORMA_V2.md` > `docs/APP_HUESPED_BEST_PRACTICES_V2.md` > convención local del equipo.

---

## 1. Cambios principales respecto a v1

| Area | v1 | v2 |
|---|---|---|
| Tenancy | Multi-tenant con `company_id` por fila | Single-tenant fisico (un contenedor = una empresa) |
| Auth de usuarios | Headers `X-Auth-*` inyectados por Traefik ForwardAuth | Login propio de la app (users + roles + permissions + tokens propios) |
| Tabla `users` | Prohibida | Obligatoria |
| Maestro -> App (usuario) | Inyecta headers + maneja sesion | Solo abre la URL de la app en `target="_blank"` |
| Maestro -> App (server) | `X-Maestro-Webhook-Secret` para hooks | + `X-Maestro-Api-Key` para `/maestro/branding` |
| `apiVersion` en `maestro.yaml` | `maestro.platform/v1` | `maestro.platform/v2` |
| Superadmin | N/A | `admin@llyasoc.com` creado por seed idempotente en fase 05-seeding |

Detalle completo en `framework-agentico/CHANGELOG.md`.

---

## 2. Requisitos OBLIGATORIOS

### 2.1 Contrato `maestro.yaml` en la raíz [OBLIGATORIO]

- El repositorio **DEBE** contener un `maestro.yaml` en la raíz.
- El campo `apiVersion` **DEBE** ser exactamente `"maestro.platform/v2"`.
- El campo `kind` **DEBE** ser `"Application"`.
- Estructura completa en §5.

### 2.2 Dockerfile en la raíz [OBLIGATORIO]

- `Dockerfile` en la raíz.
- Multi-stage build.
- `USER` no-root (UID ≠ 0) en la etapa final.
- `EXPOSE` con puerto coincidente con `requires.ports.app`.
- Imagen final ≤ 500 MB comprimida (warning a 350 MB).
- Sin secretos, claves privadas, `.env` ni historial de git.
- `HEALTHCHECK` presente apuntando a `health.endpoint`.

### 2.3 Endpoint de health check [OBLIGATORIO]

- Ruta HTTP **sin auth** declarada en `health.endpoint` (default `/health`).
- Responde `HTTP 200` con `Content-Type: application/json` y cuerpo que contenga al menos `{"status":"ok"}`.
- Tiempo de respuesta ≤ 5 s (`health.timeout_seconds`, default 3).
- **NO DEBE** ejecutar logica de negocio pesada.
- **DEBERÍA** verificar conectividad a la BD propia (`SELECT 1` ≤ 200 ms).

### 2.4 Auth propia de la app [OBLIGATORIO]

- La app **DEBE** declarar `auth.mode = "own"`. El modo `header` (v1) NO es valido en v2.
- La app **DEBE** implementar:
  - `POST {auth.login_path}` (default `/login`): valida credenciales, emite token (cookie HttpOnly o JWT).
  - `POST {auth.logout_path}` (default `/logout`): invalida el token.
  - Middleware que valida tokens propios en endpoints protegidos.
  - Tablas `users`, `roles`, `permissions` con pivots (estructura sugerida en §3, no obligatoria).
- La app **NO DEBE** leer headers `X-Auth-*` (deprecados; el Maestro v2 no los inyecta).
- La app **DEBE** rechazar con `HTTP 401` cualquier request sin auth válida en endpoints protegidos.

#### 2.4.1 Password storage

- Hash con **bcrypt (cost ≥ 12)** o **argon2id**.
- **NO DEBE** almacenarse en texto plano.
- **NO DEBE** usarse `md5` / `sha1` / `sha256` directo.

#### 2.4.2 Sesiones / tokens

- Cookies con `HttpOnly`, `Secure`, `SameSite=Lax` (o `Strict` si aplica).
- **O** JWT con expiración corta + refresh token.
- Almacenar tokens propios de la app es **PERMITIDO** (es el modelo v2).

### 2.5 Single-tenancy física [OBLIGATORIO]

- Cada contenedor sirve a UNA sola empresa.
- El modelo de datos **NO DEBE** tener `company_id` en queries.
- La empresa esta implícita por contenedor.
- Logs incluyen `user_id` y `request_id` (sin `company_id`).

### 2.6 Endpoint `/maestro/branding` [OBLIGATORIO]

- La app **DEBE** exponer el path declarado en `branding.url` (default `/maestro/branding`).
- **DEBE** requerir header `X-Maestro-Api-Key` (secret compartido, ENV var `MAESTRO_API_KEY`).
- Sin / con api key inválida → `HTTP 401`.
- Con api key válida → `HTTP 200` con JSON:

  ```json
  {
    "company_name": "Acme S.A.",
    "logo_url": "https://app.example.com/storage/logo.png",
    "primary_color": "#1F2937",
    "favicon_url": "https://app.example.com/storage/favicon.ico"
  }
  ```

- `company_name` y `logo_url` son **obligatorios**; `primary_color` y `favicon_url` son **opcionales**.

### 2.7 Base de datos dedicada [OBLIGATORIO si `requires.database != "none"`]

- La app lee la cadena de conexión de `DATABASE_URL` (ENV var inyectada por el Maestro o por orquestador).
- **NO DEBE** hardcodear hostnames, usuarios ni contraseñas.
- Motores soportados: `postgres`, `mysql`, `mongo`, `sqlite`, `none`.
- Migraciones idempotentes ejecutadas en arranque o post_provision.

### 2.8 Hooks de plataforma [OBLIGATORIO si la app declara `hooks.*`]

- Si la app declara `hooks.on_user_added`, `hooks.on_user_removed`, etc.:
  - El path **DEBE** existir, aceptar `POST` y responder `HTTP 200` en ≤ 5 s.
  - **DEBE** verificar `X-Maestro-Webhook-Signature` (HMAC-SHA256 del cuerpo, usando `MAESTRO_WEBHOOK_SECRET`).
  - **DEBE** ser idempotente (Maestro reintenta hasta 3 veces).

### 2.9 Variables de entorno obligatorias [OBLIGATORIO]

La app **DEBE** leer (no hardcodear) las siguientes ENV vars:

| Variable | Origen | Proposito |
|---|---|---|
| `DATABASE_URL` | Maestro (al provisionar) | Connection string de la BD dedicada |
| `MAESTRO_API_KEY` | Maestro / portal | Secret compartido para autenticar requests del Maestro al endpoint `/maestro/branding` |
| `SUPERADMIN_INITIAL_PASSWORD` | Operador / portal | Password inicial del superadmin (`admin@llyasoc.com`) consumida por la fase 05-seeding |
| `APP_KEY` o `JWT_SECRET` (segun stack) | Operador | Secret para firmar tokens propios |

### 2.10 Seeding del superadmin [OBLIGATORIO]

- La app **DEBE** implementar un seeder idempotente (ver fase 05-seeding del framework agéntico v4).
- El seeder lee `SUPERADMIN_INITIAL_PASSWORD` y crea (si no existe) el usuario `admin@llyasoc.com` con rol `superadmin` y todos los permisos definidos por la app.
- Idempotente: si el usuario ya existe, NO toca password; si le falta el rol, lo asigna.
- Logs sin password ni hash.
- Si `SUPERADMIN_INITIAL_PASSWORD` no existe o es debil (< 12 chars / blacklisted), el seeder **DEBE** fallar con exit code != 0 sin crear nada.

### 2.11 Variables de entorno reservadas [OBLIGATORIO]

La app **NO DEBE** usar nombres con prefijos reservados:

| Prefijo / nombre | Reservado para |
|---|---|
| `MAESTRO_*` | Inyección de plataforma |
| `DATABASE_URL` | Cadena de conexión a la BD provisionada |
| `SUPERADMIN_*` | Seeding del superadmin |

Custom env vars **DEBEN** seguir regex `^[A-Z][A-Z0-9_]*$` y no caer en prefijos reservados.

### 2.12 TLS y zero trust [OBLIGATORIO]

- App escucha HTTP en su red privada; Traefik termina TLS en el borde.
- **NO DEBE** desactivar verificación TLS al consumir servicios externos.
- Llamadas al API del Maestro **DEBEN** usar HTTPS.
- Webhooks salientes/entrantes **DEBEN** firmarse con HMAC-SHA256.

### 2.13 Secretos fuera de código y de imagen [OBLIGATORIO]

- Repositorio, historial git e imagen Docker **NO DEBEN** contener secretos.
- Pre-commit + CI con `gitleaks` (o equivalente) sobre todo el historial.

---

## 3. Estructura sugerida de tablas (NO obligatoria)

El framework v4 sugiere (no impone) la siguiente estructura para users/roles/permissions:

```
users(id, email UNIQUE, password_hash, name, is_active, last_login_at, created_at, updated_at)
roles(id, name UNIQUE, description, is_system)
permissions(id, key UNIQUE, description, group)
user_roles(user_id, role_id)
role_permissions(role_id, permission_id)
```

Cada app **PUEDE** modelarla diferente si lo justifica como ADR. Lo único obligatorio:

- Existe alguna forma de identificar usuarios por email único.
- Existe un rol `superadmin` (o equivalente) con TODOS los permisos.
- El superadmin `admin@llyasoc.com` existe tras el seeding.

---

## 4. Variables de entorno estándar

```yaml
required:
  DATABASE_URL: "URL de conexion a la BD del contenedor"
  MAESTRO_API_KEY: "Secret compartido con el Maestro para /maestro/branding"
  SUPERADMIN_INITIAL_PASSWORD: "Password inicial del superadmin (>= 12 chars)"

required_per_stack:
  Laravel:
    APP_KEY: "Key generada por php artisan key:generate"
  Node/Express o frameworks JS:
    JWT_SECRET: "Secret para firmar tokens JWT"
  Python/Django:
    SECRET_KEY: "Django secret key"

optional:
  MAESTRO_WEBHOOK_SECRET: "Secret para validar hooks (si la app declara hooks)"
  LOG_LEVEL: "info | warn | error"
```

---

## 5. Estructura de datos del contrato `maestro.yaml`

### 5.1 Esqueleto canónico v2

```yaml
apiVersion: maestro.platform/v2
kind: Application
metadata:
  name: <slug>                    # regex ^[a-z0-9][a-z0-9-]{2,49}$
  version: <semver>
  description: <texto, ≤ 500 chars>
requires:
  database: postgres | mysql | mongo | sqlite | none
  ports:
    app: <int 1024–65535>
health:
  endpoint: /health
  timeout_seconds: 3              # 1–5, default 3
auth:
  mode: own                       # v2: solo "own" es valido
  login_path: /login              # ruta del formulario de login
  logout_path: /logout            # opcional
branding:
  url: /maestro/branding          # endpoint autenticado con X-Maestro-Api-Key
resources:
  memory: 256m | 512m | 1g | 2g | 4g
  cpu: <float 0.25–4.0>
seeding:
  superadmin_email: admin@llyasoc.com   # default; PO puede sobreescribir en planning
  additional_users: []                   # opcional, decisión del PO
hooks:                            # opcional
  on_user_added: /hooks/user-added
  # ... otros hooks
env:                              # opcional, lista de nombres custom
  - SMTP_HOST
  - REDIS_URL
```

### 5.2 Diccionario de campos (cambios respecto a v1)

| Campo | Tipo | Obligatorio | Cambio v1 -> v2 |
|---|---|---|---|
| `apiVersion` | string | Sí | `"maestro.platform/v2"` (era `v1`) |
| `auth.mode` | string | Sí | enum `["own"]` (antes `["header"]`) |
| `auth.login_path` | string | Sí | NEW: ruta del formulario de login (regex `^/.*`) |
| `auth.logout_path` | string | No | NEW: opcional |
| `auth.headers` | array | — | ELIMINADO (no aplica en v2) |
| `branding.url` | string | Sí | NEW: endpoint de branding (regex `^/.*`) |
| `seeding.superadmin_email` | string | Sí | NEW: default `admin@llyasoc.com` |
| `seeding.additional_users` | array | No | NEW: usuarios adicionales decididos por el PO |

Resto de campos (metadata, requires, health, resources, hooks, env) sin cambios respecto a v1.

### 5.3 Restricciones cruzadas

- Si `requires.database = "none"`, `DATABASE_URL` no se inyecta y la app NO debe leerla.
- `requires.ports.app` DEBE coincidir con un `EXPOSE` del Dockerfile.
- `resources.memory` y `resources.cpu` DEBEN estar dentro de tier coherente.
- Si `auth.mode = own`, `auth.login_path` es obligatorio.

---

## 6. Estructura del repositorio

### 6.1 Layout obligatorio

```
.
├── maestro.yaml             [OBLIGATORIO]
├── Dockerfile               [OBLIGATORIO]
├── docker-compose.dev.yml   [DESEABLE]
├── README.md                [DESEABLE]
├── CHANGELOG.md             [DESEABLE]
├── SECURITY.md              [DESEABLE]
├── LICENSE                  [DESEABLE]
├── CLAUDE.md                [DESEABLE]
├── .github/workflows/deploy.yml  [OBLIGATORIO]
├── .dockerignore            [DESEABLE]
├── .gitignore               [OBLIGATORIO]
└── (estructura interna libre del stack)
```

### 6.2 Archivos prohibidos

| Patron | Motivo |
|---|---|
| `.env`, `.env.*` (excepto `.env.example`) | Secretos en codigo |
| `*.pem`, `*.key`, `*.p12` | Claves privadas |
| `secrets.json`, `credentials.json` | Secretos |
| `.aws/`, `.gcp/`, `.azure/` | Credenciales cloud |

---

## 7. Validacion CLI

`maestro-cli validate` (v2) verifica en orden:

1. `maestro.yaml` valida contra JSON Schema v2.
2. Dockerfile USER no-root.
3. Health endpoint declarado.
4. Recursos declarados con tier coherente.
5. Secret-scan completo del historial.
6. `auth.mode = own` y `auth.login_path` presente.
7. `branding.url` presente.
8. `seeding.superadmin_email` presente.
9. Puerto coincide con EXPOSE.
10. Env vars no colisionan con prefijos reservados.

---

## 8. Anti-patrones que bloquean despliegue

| Anti-patron | Bloquea |
|---|---|
| Lectura de headers `X-Auth-*` (modelo v1) | Sí |
| Filtros por `company_id` en queries | Sí |
| Falta de tabla `users` o equivalente | Sí |
| Password storage en texto plano | Sí |
| `MAESTRO_API_KEY` hardcodeada | Sí |
| `SUPERADMIN_INITIAL_PASSWORD` hardcodeada o debil | Sí |
| Endpoint `/maestro/branding` sin api key | Sí |
| Endpoint `/maestro/branding` ausente | Sí |
| Tag `:latest` en `FROM` o como imagen final | Sí |
| Ejecutar como root | Sí |
| Secreto en `git log` | Sí |
| `rejectUnauthorized: false` en cliente HTTPS | Sí en producción |
| Login + auth headers (mezclar v1 y v2) | Sí |

---

## 9. Comportamiento standalone (estado transitorio)

Mientras el Maestro v2 no esta desplegado, las apps v4 **PUEDEN** funcionar standalone:

- El usuario navega directamente a la URL de la app.
- Hace login en `auth.login_path`.
- Opera normalmente.

El endpoint `/maestro/branding` puede consultarse manualmente con la api key compartida, pero ningun consumidor automatizado lo hara hasta que el Maestro v2 lo registre.

Esto NO es un permiso para implementar dual-mode (v1 + v2). La app es v4 y solo cumple el contrato v2.

---

## 10. Migración v1 -> v2

Apps existentes que cumplen el contrato v1 deben migrar para operar bajo Maestro v2. Proceso:

1. PO ejecuta `/pm` en el repo de la app.
2. Framework v4 detecta version desactualizada y propone migracion.
3. Tras sync con upstream, se lanza `Agent(framework-migrator, opus)` que genera reporte de gaps.
4. PO decide si abrir trabajo correctivo (issue/branch) para corregir el codigo.

Detalle en `framework-agentico/migration/v3-to-v4.md`.

---

## 11. Glosario

| Término | Definicion |
|---|---|
| **App huésped** | Aplicación de tercero o equipo interno alojada en Maestro Platform. |
| **Maestro v2** | Plataforma orquestadora con contrato `maestro.platform/v2` (single-tenant fisico, registry + redirector). |
| **Single-tenant fisico** | Un contenedor de aplicación = una empresa. La empresa esta implícita por contenedor; no hay `company_id`. |
| **Auth propia** | La app emite, valida y revoca sus propios tokens. |
| **Branding endpoint** | Endpoint autenticado que expone nombre y logos de la empresa para mostrar en el portal del Maestro. |
| **Seeding** | Fase 05 del ciclo agéntico v4: crea el superadmin `admin@llyasoc.com` de forma idempotente. |
| **Superadmin** | Usuario con todos los permisos definidos por la app. Email canonico: `admin@llyasoc.com`. |
| **Contrato v2** | `maestro.platform/v2`. Reemplaza al v1. |

---

## 12. Referencias normativas

| Documento | Rol |
|---|---|
| `framework-agentico/CHANGELOG.md` | Historial de cambios entre versiones del framework |
| `framework-agentico/core/PRESET_WEB_MAESTRO.md` | Preset Web Maestro v4 (constraints por fase) |
| `framework-agentico/phases/05-seeding.md` | Fase de seeding (incluye superadmin) |
| `framework-agentico/migration/v3-to-v4.md` | Proceso de migración |
| `framework-agentico/agents/presets/maestro-platform-v2/PRESET.md` | Preset para construir el Maestro v2 (lado servidor) |
| `docs/CONVENCIONES_PLATAFORMA_V2.md` | Naming, redes, puertos, vars de entorno (v2) |
| `docs/APP_HUESPED_BEST_PRACTICES_V2.md` | Recomendaciones no normativas |

---

## 13. Historial de revisiones

| Versión | Fecha | Cambio |
|---|---|---|
| 2.0.0 | 2026-05-06 | Versión inicial. Cubre contrato `maestro.platform/v2` (single-tenant, auth propia, branding endpoint, seeding). Reemplaza a `APP_HUESPED_SPEC.md` v1. |
