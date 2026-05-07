# Contrato `maestro.yaml` — Especificación Normativa

> **Versión:** v4 (framework agéntico v4 / contrato `maestro.platform/v2`)
> **Última revisión:** 2026-05-07
> **Estado:** vigente
> **Reemplaza a:** `legacy/v3/PremisaWebMaestro/06-SDK-Y-CONTRATO.md` (modelo v1 con `auth.mode: header`).

---

## Propósito de este documento

Este documento especifica el contrato `maestro.platform/v2` que **toda aplicación huésped** (= app genérica = app tool) debe cumplir para integrarse con la **Web Maestro** v4. Define la estructura completa del archivo `maestro.yaml`, los campos obligatorios y opcionales, las restricciones cruzadas, el JSON Schema canónico, el flujo de validación CLI y el endpoint de auto-registro.

Audiencia: equipos que desarrollan apps huésped, agentes de IA que generan scaffolding, herramientas de validación.

> **Nota**: este documento describe el contrato desde la perspectiva de la **constitución del Maestro**. La especificación detallada para los desarrolladores de apps está en `docs/APP_HUESPED_SPEC.md` y es el documento normativo final ante conflicto.

---

## Cambio fundamental respecto a v1

| Campo | v1 | v4 |
|---|---|---|
| `apiVersion` | `maestro.platform/v1` | `maestro.platform/v2` |
| `auth.mode` | enum `["header"]` | enum `["own"]` |
| `auth.headers` | array obligatorio | **eliminado** |
| `auth.login_path` | — | obligatorio |
| `auth.logout_path` | — | opcional |
| `branding.url` | — | obligatorio |
| `seeding.superadmin_email` | — | obligatorio (default `admin@llyasoc.com`) |
| `seeding.additional_users` | — | opcional |
| `ui.tailwise` | — | recomendado true (preferencia, no obligatorio) |
| `ui.theme` | — | opcional |

Apps con `apiVersion: maestro.platform/v1` son **rechazadas** en `POST /api/v2/apps/register`.

---

## Estructura canónica

```yaml
apiVersion: maestro.platform/v2
kind: Application
metadata:
  name: <slug>                          # OBLIGATORIO
  version: <semver>                     # OBLIGATORIO
  description: <texto, ≤ 500 chars>     # OPCIONAL
requires:
  database: postgres|mysql|mongo|sqlite|none   # OBLIGATORIO
  ports:
    app: <int 1024–65535>               # OBLIGATORIO
health:
  endpoint: /health                     # OBLIGATORIO
  timeout_seconds: 3                    # OPCIONAL, default 3, max 5
auth:
  mode: own                             # OBLIGATORIO, único valor aceptado
  login_path: /login                    # OBLIGATORIO
  logout_path: /logout                  # OPCIONAL
branding:
  url: /maestro/branding                # OBLIGATORIO
seeding:
  superadmin_email: admin@llyasoc.com   # OBLIGATORIO, default admin@llyasoc.com
  additional_users: []                  # OPCIONAL, lista de {email, role}
resources:
  memory: 256m|512m|1g|2g|4g            # OBLIGATORIO
  cpu: <float 0.25–4.0>                 # OBLIGATORIO
hooks:                                  # OPCIONAL
  on_user_added: /hooks/user-added
  on_user_removed: /hooks/user-removed
  on_company_license_granted: /hooks/license-granted
  on_company_license_revoked: /hooks/license-revoked
ui:                                     # OPCIONAL
  tailwise: true                        # OPCIONAL, default true (recomendado)
  theme: echo                           # OPCIONAL si tailwise=true
  reason: ""                            # OBLIGATORIO si tailwise=false
env:                                    # OPCIONAL
  - SMTP_HOST
  - REDIS_URL
  - FEATURE_FLAGS_API_KEY
```

---

## Diccionario de campos

### `apiVersion` (string, obligatorio)

- **Valor permitido**: exactamente `"maestro.platform/v2"`.
- Otros valores son rechazados en validación CLI y en `/api/v2/apps/register`.

### `kind` (string, obligatorio)

- **Valor permitido**: exactamente `"Application"`.

### `metadata.name` (string, obligatorio)

- Slug de la app.
- **Regex**: `^[a-z0-9][a-z0-9-]{2,49}[a-z0-9]$`. Longitud 4-50.
- **Único en el catálogo del Maestro**. Una vez registrado, **inmutable**.

### `metadata.version` (string, obligatorio)

- SemVer estricto: `^\d+\.\d+\.\d+(-[\w\.-]+)?(\+[\w\.-]+)?$`.
- Sin prefijo `v`.

### `metadata.description` (string, opcional)

- ≤ 500 chars.
- Mostrado en el catálogo del portal del Maestro.

### `requires.database` (enum, obligatorio)

- Valores: `postgres | mysql | mongo | sqlite | none`.
- Si `none`, la ENV var `DATABASE_URL` **NO** se inyecta y la app **NO DEBE** intentar leerla.
- En todos los demás casos, el Maestro provisiona BD dedicada.

### `requires.ports.app` (integer, obligatorio)

- Rango: `1024 ≤ x ≤ 65535`.
- **DEBE coincidir** con un `EXPOSE` del Dockerfile (validado estáticamente por CLI).

### `health.endpoint` (string, obligatorio)

- Ruta HTTP **sin auth**.
- Regex: `^/.*`.
- Sin parámetros de query.

### `health.timeout_seconds` (integer, opcional)

- Default `3`. Max `5`.
- Si la app no responde en este tiempo, el health check se considera fallido.

### `auth.mode` (string, obligatorio)

- **Valor único permitido**: `"own"`.
- `"header"` (modo v1) **rechaza** el registro.

### `auth.login_path` (string, obligatorio)

- Ruta del formulario de login.
- Regex: `^/.*`.
- Default sugerido: `/login`.

### `auth.logout_path` (string, opcional)

- Ruta de logout.
- Regex: `^/.*`.

### `branding.url` (string, obligatorio)

- Ruta del endpoint que retorna `{company_name, logo_url, primary_color?, favicon_url?}`.
- Regex: `^/.*`.
- Default sugerido: `/maestro/branding`.
- **Autenticación obligatoria** vía `X-Maestro-Api-Key`.

### `seeding.superadmin_email` (string, obligatorio)

- Email canónico del superadmin de la app.
- Default: `admin@llyasoc.com`.
- Validación de formato email RFC 5322.
- El PO puede sobreescribir en la fase 02-planning si lo justifica como ADR.

### `seeding.additional_users` (array, opcional)

- Lista de `{email, role}` para sembrar usuarios adicionales además del superadmin.
- Cada usuario adicional requiere su propia ENV var dedicada (ej: `EDITOR_INITIAL_PASSWORD`).
- Decisión documentada en la fase 02-planning del proyecto.

### `resources.memory` (enum, obligatorio)

- Valores: `256m | 512m | 1g | 2g | 4g`.
- Aplicado vía `--memory` al `docker run`.

### `resources.cpu` (number, obligatorio)

- Rango: `0.25 ≤ x ≤ 4.0`.
- Aplicado vía `--cpus` al `docker run`.

### `hooks.*` (string, opcional)

- Cada uno declara la ruta del endpoint para recibir el hook correspondiente.
- Regex: `^/.*`.
- Si la app declara hooks, **DEBE** verificar `X-Maestro-Webhook-Signature` (HMAC-SHA256) — ver `03-AUTENTICACION-Y-AUTORIZACION.md` §2.2.
- Hooks soportados: `on_user_added`, `on_user_removed`, `on_company_license_granted`, `on_company_license_revoked`.

### `ui.tailwise` (boolean, opcional)

- Default `true`.
- Indica si la app usa el sistema de diseño Tailwise (recomendado, no obligatorio).
- Si `false`, **DEBE** declarar `ui.reason` con el motivo (ej: "App sin frontend propio, solo API REST" o "App usa Flutter Web").
- Los agentes UX/UI deben presentar Tailwise como recomendación pero respetar la decisión final del PO.

### `ui.theme` (string, opcional)

- Theme de Tailwise: `dagger | echo | exort | havoc | hook | hurricane | ravage | raze | razor | shuriken | viper`.
- Aplicable solo si `ui.tailwise = true`.

### `ui.reason` (string, condicional)

- Obligatorio si `ui.tailwise = false`.
- Texto libre justificando la excepción.

### `env` (array, opcional)

- Lista de ENV vars custom que la app declara consumir.
- Regex: `^[A-Z][A-Z0-9_]*$`.
- **Prohibido** usar prefijos reservados:
  - `MAESTRO_*` (reservado para inyección de plataforma).
  - `SUPERADMIN_*` (reservado para seeding).
  - `DATABASE_URL` (reservado para conexión a BD).
- Estas vars **NO** las inyecta el Maestro automáticamente; el operador (o el portal del Maestro) las configura por deployment.

---

## Restricciones cruzadas

1. Si `requires.database = "none"`:
   - `DATABASE_URL` NO se inyecta.
   - El seeder de superadmin **DEBE** ser stack-compatible (ej: si la app no tiene BD, debe tener algún mecanismo de auth alternativo o declarar `seeding` como N/A — caso raro, validado caso a caso).

2. `requires.ports.app` **DEBE** coincidir con al menos un `EXPOSE` del Dockerfile.

3. `resources.memory` y `resources.cpu` **DEBEN** estar dentro de un tier coherente. El CLI rechaza combinaciones inválidas (ej: `cpu: 4.0` con `memory: 256m`).

4. Si `auth.mode = "own"`:
   - `auth.login_path` es obligatorio.
   - `branding.url` es obligatorio.
   - `seeding.superadmin_email` es obligatorio.

5. Si la app declara hooks:
   - **DEBE** consumir `MAESTRO_WEBHOOK_SECRET` y verificar firma HMAC-SHA256.
   - **DEBE** ser idempotente (`event_id` para deduplicar).

6. Si `ui.tailwise = false`:
   - `ui.reason` es obligatorio.

---

## JSON Schema oficial

El JSON Schema canónico vive en `docs/schemas/maestro.yaml.schema.v2.json` y es la **fuente de verdad técnica** para validación. Versionado junto con el repo template.

Estructura del schema:

```json
{
  "$schema": "https://json-schema.org/draft/2020-12/schema",
  "$id": "https://maestro.llyasoc.com/schemas/maestro.yaml.schema.v2.json",
  "title": "Maestro Platform Application Contract v2",
  "type": "object",
  "additionalProperties": false,
  "required": ["apiVersion", "kind", "metadata", "requires", "health", "auth", "branding", "seeding", "resources"],
  "properties": {
    "apiVersion": { "const": "maestro.platform/v2" },
    "kind": { "const": "Application" },
    "metadata": { ... },
    "requires": { ... },
    "health": { ... },
    "auth": { ... },
    "branding": { ... },
    "seeding": { ... },
    "resources": { ... },
    "hooks": { ... },
    "ui": { ... },
    "env": { ... }
  }
}
```

(Estructura completa generada en la implementación de la Web Maestro.)

---

## Validación CLI (`maestro-cli validate`)

El comando `maestro-cli validate` ejecuta, en orden:

1. **Existencia**: `maestro.yaml` existe en la raíz del repo.
2. **Schema**: valida contra el JSON Schema v2.
3. **Dockerfile USER**: instrucción `USER` presente, no-root, no UID 0 (en stage final si es multi-stage).
4. **Health endpoint**: declarado, comienza con `/`, sin parámetros de query.
5. **Recursos**: `resources.memory` y `resources.cpu` dentro de tier coherente.
6. **Secret-scan**: `gitleaks` (o equivalente) sobre todo el historial de git.
7. **Auth**: `auth.mode = own` y `auth.login_path` presente.
8. **Branding**: `branding.url` presente.
9. **Seeding**: `seeding.superadmin_email` presente con formato email válido.
10. **Puerto**: `requires.ports.app` coincide con `EXPOSE` del Dockerfile.
11. **Reservados**: ninguna entrada de `env` colisiona con prefijos reservados.

Si **cualquier** verificación falla, exit code ≠ 0 y el pipeline se detiene. La salida del CLI es JSON estructurado para ser leído por GitHub Actions y mostrado en el PR.

---

## Auto-registro: `POST /api/v2/apps/register`

Endpoint del Maestro que las apps invocan desde su CI tras pasar `maestro-cli validate` y construir su imagen Docker.

### Request

```http
POST /api/v2/apps/register
Authorization: Bearer <REGISTRATION_TOKEN>
Content-Type: application/yaml

<contenido del maestro.yaml>
```

Headers adicionales:
- `X-Image-Ref`: digest de la imagen recién construida (ej: `ghcr.io/org/app@sha256:...`).
- `X-Commit-Sha`: SHA del commit que originó el registro.
- `X-Yaml-Hash`: SHA-256 del cuerpo del request.

### Validaciones del Maestro

1. `apiVersion = "maestro.platform/v2"` (rechaza v1 con `HTTP 422`).
2. `metadata.name` cumple regex.
3. JSON Schema completo.
4. `metadata.name` único en el catálogo (rechaza con `HTTP 409` si ya existe con otro contenido).
5. Hash del YAML coincide con `X-Yaml-Hash` (integridad).
6. `REGISTRATION_TOKEN` válido (cada owner del repo obtiene un token único, audit logged).

### Respuestas

- `HTTP 201 Created`: app registrada (o nueva versión registrada si `metadata.name` ya existía con misma version).
- `HTTP 409 Conflict`: el `metadata.name` ya existe con contenido diferente y el `version` no fue incrementado.
- `HTTP 422 Unprocessable Entity`: validación falló (detalle en body).
- `HTTP 401 Unauthorized`: token inválido.

### Audit log del registro

Toda llamada exitosa registra:
- `action: "application.register"` o `application.update`.
- `actor`: el `REGISTRATION_TOKEN` (no un admin).
- `resource_id`: `applications.id`.
- `payload_after`: maestro.yaml + image_ref + commit_sha.

---

## Reglas de evolución del contrato

### Compatibilidad

- **Backward compatibility**: cuando se libere `maestro.platform/v3` (futuro), las apps en v2 seguirán funcionando durante un período mínimo de **12 meses**. Después la Web Maestro puede dejar de aceptarlas en `/api/v2/apps/register`.
- **Forward compatibility**: las apps NO deben asumir que `apiVersion: maestro.platform/v3` será aceptado por el Maestro v2.

### Versionado del contrato

- Cambios mayores (incompatibles) bumpean la versión del contrato (`v2` → `v3`).
- Cambios menores (agregar campos opcionales) NO bumpean la versión. Apps existentes siguen siendo válidas.
- El JSON Schema v2 puede agregar `properties` opcionales sin bumpear, pero NO puede agregar `required` ni cambiar enums sin bumpear.

### Migración entre versiones del contrato

Cuando llegue la migración v2 → v3 (futuro), aplicará el mismo modelo lazy del framework agéntico:

- El PM detecta la versión del `maestro.yaml` y propone migración.
- Genera reporte de gaps en el código de la app.
- El PO decide si aplicar.

Detalle del modelo de migración en `framework-agentico/migration/v3-to-v4.md` (proceso del bump v3→v4 del framework, modelo aplicable también a futuros bumps del contrato).

---

## Anti-patrones que bloquean el registro

| Anti-patrón | Bloquea |
|---|---|
| `apiVersion: maestro.platform/v1` | Sí |
| `auth.mode: header` | Sí |
| Lectura de headers `X-Auth-*` en código (detección estática) | Sí |
| Filtros por `company_id` en queries | Sí |
| Falta de tabla `users` o equivalente | Sí |
| `MAESTRO_API_KEY` hardcodeada en código | Sí |
| `SUPERADMIN_INITIAL_PASSWORD` hardcodeada o débil | Sí |
| Endpoint `/maestro/branding` sin api key | Sí |
| Endpoint `/maestro/branding` ausente | Sí |
| Tag `:latest` en `FROM` o como imagen final | Sí |
| Ejecutar como root | Sí |
| Secreto en `git log` (gitleaks detecta) | Sí |
| `rejectUnauthorized: false` en cliente HTTPS | Sí en producción |
| Mezcla de v1 y v2 (login propio + lee X-Auth-*) | Sí |
| `metadata.name` con caracteres no permitidos | Sí |
| `requires.ports.app` no coincide con EXPOSE | Sí |

---

## Ejemplo completo (Node + Express + Postgres)

```yaml
apiVersion: maestro.platform/v2
kind: Application
metadata:
  name: inventario
  version: 1.4.2
  description: Sistema de inventario y movimientos de stock con alertas configurables.
requires:
  database: postgres
  ports:
    app: 3000
health:
  endpoint: /health
  timeout_seconds: 3
auth:
  mode: own
  login_path: /login
  logout_path: /logout
branding:
  url: /maestro/branding
seeding:
  superadmin_email: admin@llyasoc.com
  additional_users:
    - { email: editor@llyasoc.com, role: editor }
resources:
  memory: 512m
  cpu: 0.5
hooks:
  on_user_added: /hooks/user-added
  on_company_license_revoked: /hooks/license-revoked
ui:
  tailwise: true
  theme: echo
env:
  - SMTP_HOST
  - SMTP_PORT
  - SMTP_USER
  - SMTP_PASSWORD_REF
```

Ejemplos para otros stacks (Laravel, Vue, Python, Go) en `docs/APP_HUESPED_SPEC.md` §12-13 y siguientes (a expandir según necesidad).

---

## Referencias normativas

- `01-PREMISAS-Y-NO-NEGOCIABLES.md` — premisa 5 (contrato obligatorio); no-negociables 1, 5, 9.
- `02-MODELO-DE-DATOS.md` — tabla `applications` que persiste el `maestro.yaml` registrado.
- `03-AUTENTICACION-Y-AUTORIZACION.md` — uso de `MAESTRO_API_KEY` y `MAESTRO_WEBHOOK_SECRET` declarados implícitamente por este contrato.
- `04-INFRAESTRUCTURA-DOCKER.md` — el motor de provisioning consume `requires`, `resources`, `health`.
- `08-CICD-Y-GOBERNANZA.md` — pipeline CI/CD que ejecuta `maestro-cli validate` y `POST /api/v2/apps/register`.
- `docs/APP_HUESPED_SPEC.md` — especificación normativa lado app (precedencia).
- `docs/schemas/maestro.yaml.schema.v2.json` — JSON Schema canónico.
- `framework-agentico/core/PRESET_WEB_MAESTRO.md` — preset que aplica a apps huésped (alineado con este contrato).

---

## Historial de revisiones

| Versión | Fecha | Cambio |
|---|---|---|
| 4.0.0 | 2026-05-07 | Versión inicial v4. Reescribe el contrato con `auth.mode: own`, `branding.url`, `seeding.superadmin_email`, `ui.tailwise`. Reemplaza al v1 (legacy en `legacy/v3/PremisaWebMaestro/06-SDK-Y-CONTRATO.md`). Se renombra de `06-SDK-Y-CONTRATO.md` a `06-CONTRATO-MAESTRO-YAML.md` para reflejar que en v4 los SDKs son opcionales (no obligatorios como en v1). |
