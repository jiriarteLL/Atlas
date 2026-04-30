# Especificación Técnica de Aplicación Huésped — Maestro Platform

> **Documento normativo.** Vincula a todo equipo, interno o externo, que pretenda registrar una aplicación genérica en Maestro Platform.
>
> **Versión del contrato:** `maestro.platform/v1`
> **Última revisión:** 2026-04-28
> **Audiencia:** desarrolladores, tech leads, responsables de plataforma de equipos integradores.
> **Predecesores normativos:** `PremisaWebMaestro/01-PREMISAS-Y-NO-NEGOCIABLES.md`, `PremisaWebMaestro/06-SDK-Y-CONTRATO.md`, `docs/CONVENCIONES_PLATAFORMA.md`, `docs/schemas/maestro.yaml.schema.json`.
> **Documento complementario:** `docs/APP_HUESPED_BEST_PRACTICES.md` (no normativo; recomendaciones de industria).

---

## 0. Marco de cumplimiento

Las palabras clave **DEBE / NO DEBE / DEBERÍA / NO DEBERÍA / PUEDE** en este documento se interpretan según RFC 2119 / RFC 8174:

| Término | Significado | Consecuencia de incumplimiento |
|---|---|---|
| **DEBE** / **OBLIGATORIO** / **REQUERIDO** | Requisito absoluto. | Bloqueo automático en `maestro-cli validate` o en `POST /api/v1/apps/register`. La app **no se provisiona**. |
| **NO DEBE** / **PROHIBIDO** | Prohibición absoluta. | Igual al anterior. Detectable estática o dinámicamente. |
| **DEBERÍA** / **RECOMENDADO** | Implementación esperada salvo justificación documentada. | Genera *warning* no bloqueante en CI. Puede bloquear en revisión de código. |
| **NO DEBERÍA** / **NO RECOMENDADO** | Práctica desaconsejada. | Igual al anterior. |
| **PUEDE** / **OPCIONAL** | Implementación a discreción del equipo de la app. | Sin consecuencia. |

Las secciones se etiquetan en su encabezado con **[OBLIGATORIO]**, **[DESEABLE]** o **[NEGOCIABLE]** para clasificar de un vistazo.

> **Regla de precedencia:** ante conflicto, prevalece `PremisaWebMaestro/01-PREMISAS-Y-NO-NEGOCIABLES.md` > este documento > `docs/CONVENCIONES_PLATAFORMA.md` > `docs/APP_HUESPED_BEST_PRACTICES.md` > convención local del equipo.

---

## 1. Requisitos OBLIGATORIOS

Esta sección lista **todo** lo que el `maestro-cli validate` y el endpoint de registro verifican antes de permitir el despliegue. Su incumplimiento bloquea la app sin posibilidad de *waiver*.

### 1.1 Contrato `maestro.yaml` en la raíz del repositorio [OBLIGATORIO]

- El repositorio **DEBE** contener un archivo `maestro.yaml` en la raíz (no en subdirectorios).
- El archivo **DEBE** validar contra `https://maestro.llyasoc.com/schemas/maestro.yaml.schema.json` (versión `maestro.platform/v1`).
- El archivo **NO DEBE** contener claves desconocidas (`additionalProperties: false`).
- El campo `apiVersion` **DEBE** ser exactamente `"maestro.platform/v1"`.
- El campo `kind` **DEBE** ser exactamente `"Application"`.
- La estructura completa se documenta en la **Sección 4**.

### 1.2 Dockerfile en la raíz del repositorio [OBLIGATORIO]

- El repositorio **DEBE** contener un `Dockerfile` en la raíz.
- El Dockerfile **DEBE** declarar una instrucción `USER` con un usuario **no-root** (UID ≠ 0). En multi-stage builds, esta instrucción se verifica en la **etapa final**.
- El Dockerfile **DEBE** declarar al menos un `EXPOSE` cuyo puerto coincida exactamente con `requires.ports.app` del contrato.
- La imagen final **NO DEBE** ejecutar como root (`whoami` durante runtime no debe devolver `root`).
- La imagen final **NO DEBE** superar **500 MB** comprimida (warning a 350 MB).
- La imagen **NO DEBE** incluir secretos, claves privadas, archivos `.env` ni historiales de git.

### 1.3 Endpoint de health check [OBLIGATORIO]

- La app **DEBE** exponer una ruta HTTP **sin autenticación** declarada en `health.endpoint`.
- La ruta **DEBE** comenzar con `/`.
- La ruta **DEBE** responder `HTTP 200` con `Content-Type: application/json` y un cuerpo que contenga al menos `{"status":"ok"}`.
- La respuesta **DEBE** llegar en **≤ 5 segundos** (límite duro `health.timeout_seconds`, default 3).
- La ruta **NO DEBE** ejecutar lógica de negocio pesada, consultas a servicios externos críticos ni operaciones de escritura.
- La ruta **DEBERÍA** verificar la conectividad a la BD propia con un `SELECT 1` (≤ 200 ms) antes de retornar `ok`.
- La ruta **NO DEBE** estar protegida por el middleware ForwardAuth de Traefik (Maestro la consulta directamente desde la red Docker privada del worker de health).

### 1.4 Autenticación por headers ForwardAuth [OBLIGATORIO]

- La app **DEBE** declarar `auth.mode = "header"`. Ningún otro modo es aceptado.
- La app **DEBE** leer la identidad del usuario **exclusivamente** de los siguientes headers, inyectados por Traefik tras validar el token con el Maestro:

| Header | Tipo | Cardinalidad | Ejemplo |
|---|---|---|---|
| `X-Auth-User-Id` | UUID v4 string | 1 | `b3a8c0e8-2a3a-4d27-9c1c-5a8a3f8b7e21` |
| `X-Auth-User-Email` | RFC 5322 email | 1 | `aviera@llyasoc.com` |
| `X-Auth-Company-Id` | UUID v4 string | 1 | `7e2b1f12-8b3a-4d77-bc1c-90c3bfb0a112` |
| `X-Auth-Roles` | CSV de slugs | 0..N | `admin,editor` |
| `X-Auth-Permissions` | CSV de slugs | 0..N | `users.read,users.write` |

- La app **DEBE** declarar en `auth.headers` el subconjunto de headers que realmente consume (mínimo 3 distintos, máximo 5).
- La app **NO DEBE** implementar formularios de login, registro de usuarios, recuperación de contraseña, emisión propia de JWT/sessions, ni almacenar contraseñas o factor segundo.
- La app **NO DEBE** confiar en ningún otro mecanismo (cookies de sesión propias, JWTs propios, query strings, basic auth) para identificar al usuario.
- Si los headers no llegan, la app **DEBE** responder `HTTP 401` (significaría que el request no pasó por Traefik y por lo tanto es interno o falsificado).
- La app **DEBE** validar siempre el `X-Auth-Company-Id` contra los datos consultados antes de devolver información (filtrado obligatorio, ver §1.5).

### 1.5 Aislamiento de datos por tenant [OBLIGATORIO]

- Toda fila de toda tabla que contenga datos de tenant **DEBE** incluir una columna `company_id` (o equivalente FK al tenant).
- Toda consulta de lectura/escritura **DEBE** filtrar por `company_id = X-Auth-Company-Id`.
- La app **DEBE** rechazar (con `HTTP 403`) cualquier request que intente acceder a datos cuyo `company_id` no coincida con el header.
- Cuando se use el SDK oficial (Node, Python, PHP-Laravel, Go), el filtrado **DEBE** delegarse al middleware/scope del SDK; el desarrollador **NO DEBE** desactivar este filtrado.
- Las migraciones de BD **DEBEN** crear índice sobre `company_id` en tablas con > 1.000 filas esperadas.

### 1.6 Base de datos dedicada [OBLIGATORIO]

- Si la app declara `requires.database != "none"`, recibe una BD dedicada provisionada por el Maestro.
- La app **DEBE** leer la cadena de conexión exclusivamente de la variable de entorno `DATABASE_URL`. No puede hardcodear hostnames, usuarios ni contraseñas.
- La app **NO DEBE** intentar conectarse a la BD de otra instancia, a la BD del Maestro, ni a ninguna BD que no le haya sido inyectada.
- Motores soportados (`requires.database`): `postgres`, `mysql`, `mongo`, `sqlite`, `none`.
- Las migraciones idempotentes **DEBEN** ejecutarse en el hook `post_provision` o en el arranque (idempotente, ver §2.3).

### 1.7 Aislamiento de red [OBLIGATORIO]

- La app **NO DEBE** crear conexiones de red salientes a otras apps huésped por su nombre de contenedor o IP de red privada.
- Toda comunicación inter-apps **DEBE** pasar por `https://<maestro>/api/v1/gateway/<app-destino>/<ruta>` (ADR-007).
- La app **NO DEBE** intentar escanear la red Docker, descubrir contenedores vecinos ni resolver nombres `app-*-*` ajenos.
- La app **NO DEBE** abrir puertos al host (no hay `ports:` en el compose de instancias; Traefik enruta todo).
- La app **DEBE** escuchar en el puerto declarado en `requires.ports.app` (1024 ≤ puerto ≤ 65535).

### 1.8 Límites de recursos declarados [OBLIGATORIO]

- El bloque `resources` **DEBE** estar presente con los campos `memory` y `cpu`.
- `resources.memory` **DEBE** ser uno de: `256m`, `512m`, `1g`, `2g`, `4g`. No se aceptan otros valores.
- `resources.cpu` **DEBE** ser un número decimal entre `0.25` y `4.0` inclusive.
- La app **NO DEBE** asumir más recursos que los declarados; el kernel matará el contenedor por OOM o lo throttling-eará si excede.
- Tier inferido (informativo): ver §8.

### 1.9 Secretos fuera de código y de imagen [OBLIGATORIO]

- El repositorio, su historial de git completo y la imagen Docker resultante **NO DEBEN** contener:
  - Contraseñas, tokens API, claves privadas (RSA/EC/SSH), cadenas de conexión, claves de cifrado, claves de servicio (GCP/AWS/Azure), webhooks firmados.
  - Archivos `.env`, `secrets.json`, `credentials.json`, `*.pem`, `*.p12`, `*.kdbx`.
- Los secretos **DEBEN** entregarse exclusivamente vía variables de entorno inyectadas por el Maestro en runtime.
- El pipeline CI **DEBE** ejecutar `gitleaks` (o equivalente) sobre **todo el historial** de git en cada PR.
- Si el scan detecta una coincidencia, el pipeline falla y la imagen no se publica.

### 1.10 TLS y zero trust [OBLIGATORIO]

- La app **NO DEBE** servir HTTP plano. Internamente escucha en HTTP, pero **solo** en su red Docker privada; Traefik termina TLS en el borde.
- La app **NO DEBE** desactivar verificación TLS al consumir servicios externos (`rejectUnauthorized: false` y similares están prohibidos en producción).
- Toda llamada al API del Maestro **DEBE** usar HTTPS (`MAESTRO_API_URL` siempre comienza con `https://`).
- Webhooks salientes/entrantes **DEBEN** firmarse con HMAC-SHA256 (ver §9).

### 1.11 Variables de entorno reservadas [OBLIGATORIO]

La app **NO DEBE** usar nombres de variables que coincidan con prefijos reservados:

| Prefijo / nombre | Reservado para |
|---|---|
| `MAESTRO_*` | Inyección de plataforma (URL del Maestro, secret de la app, feature flags). |
| `X_AUTH_*` | Datos de autenticación (no son env vars; son headers HTTP, pero el prefijo está reservado para evitar colisión). |
| `DATABASE_URL` | Cadena de conexión a la BD provisionada. |

- El campo `env` del contrato **DEBE** listar solo variables que no caigan bajo estos prefijos.
- Los nombres **DEBEN** seguir la regex `^[A-Z][A-Z0-9_]*$`.

### 1.12 Webhooks de plataforma [OBLIGATORIO si la app declara `hooks.*`]

- Si la app declara `hooks.on_user_added`, `hooks.on_user_removed`, `hooks.on_company_license_granted` u `hooks.on_company_license_revoked`:
  - La ruta declarada **DEBE** existir, aceptar `POST` y responder `HTTP 200` en ≤ 5 s.
  - La app **DEBE** verificar el header `X-Maestro-Webhook-Signature` (HMAC-SHA256 del cuerpo, usando `MAESTRO_APP_SECRET`).
  - La app **DEBE** ser **idempotente**: el Maestro reintenta hasta 3 veces con backoff exponencial.
  - La app **DEBE** procesar el webhook en `≤ 5 s`. Para trabajo pesado, encolar y responder 200 inmediato (`202 Accepted` también es válido si la app declara una cola).

### 1.13 Restricción del `Dockerfile`: capas y cache [OBLIGATORIO]

- El Dockerfile **DEBE** usar imágenes base oficiales firmadas (Docker Official Images, Microsoft Container Registry, distroless de Google).
- El Dockerfile **NO DEBE** usar `FROM` con tag `latest` ni con tag mutable. Las bases **DEBEN** anclarse a un digest (`@sha256:...`) o, como mínimo, a una versión menor (`node:22.13-alpine`).
- El Dockerfile **NO DEBE** ejecutar `apt-get upgrade` ni mecanismos equivalentes (rompe reproducibilidad).
- El Dockerfile **NO DEBE** llamar a `curl | sh` ni instalar binarios desde URLs sin verificación de hash.

### 1.14 Health check del Dockerfile [DESEABLE → OBLIGATORIO desde v1.1 del contrato]

- El Dockerfile **DEBERÍA** incluir una instrucción `HEALTHCHECK` que invoque la misma ruta declarada en `health.endpoint`. Esto facilita debugging local; el Maestro usa su propio mecanismo de health check vía Traefik.

---

## 2. Requisitos DESEABLES

Las siguientes prácticas **DEBERÍAN** seguirse. CI emite *warnings* si no se cumplen pero permite el despliegue. La revisión de código del integrador es la última línea de defensa para estas reglas.

### 2.1 Uso del SDK oficial [DESEABLE]

- Si la app está escrita en Node, Python, PHP-Laravel o Go, **DEBERÍA** usar el SDK oficial:
  - `@maestro/sdk-node` (npm)
  - `maestro-sdk` (pip)
  - `maestro/sdk-laravel` (composer)
  - `github.com/maestro/sdk-go` (go mod)
- El SDK abstrae el parseo de `X-Auth-*`, el filtrado por `company_id`, y la firma HMAC de webhooks. Reescribir esta lógica a mano es propenso a errores de seguridad.

### 2.2 Definición de `config_schema` [DESEABLE]

- Si la app expone parámetros configurables por empresa (ej.: política de retención, color de marca, integraciones externas), **DEBERÍA** declararlos en `config_schema` para que el portal Maestro genere automáticamente el formulario de configuración.
- Cada parámetro **DEBERÍA** tener: `name`, `type` (`string|number|boolean|select`), `default`, `description`, y `required` (boolean).

### 2.3 Migraciones idempotentes y backward-compatible [DESEABLE]

- Las migraciones **DEBERÍAN** ser idempotentes (ejecutarlas dos veces no rompe).
- Migraciones que rompen compatibilidad (drop column, rename) **DEBERÍAN** dividirse en **dos releases** (expand-then-contract): primero agregar el campo nuevo y dual-write; luego, en una versión posterior, dropear el viejo.

### 2.4 Logs estructurados [DESEABLE]

- La app **DEBERÍA** emitir logs en JSON a `stdout`/`stderr` (los recoge Promtail → Loki).
- Cada log **DEBERÍA** incluir: `timestamp` (ISO-8601 UTC), `level` (`debug|info|warn|error|fatal`), `message`, `tenant_id` (== `X-Auth-Company-Id`), `user_id` (== `X-Auth-User-Id`), `request_id`, `app_version`.
- La app **NO DEBERÍA** loguear PII bruta (emails completos, nombres, identificadores fiscales). Use hash o truncado.
- La app **NO DEBE** loguear secretos, headers `X-Auth-*` completos, ni cuerpos de request con datos sensibles.

### 2.5 Trazas distribuidas con OpenTelemetry [DESEABLE]

- La app **DEBERÍA** emitir spans OpenTelemetry vía OTLP al colector del Maestro (env var `MAESTRO_OTLP_ENDPOINT` cuando esté disponible).
- Cada span **DEBERÍA** incluir attributes: `tenant.id`, `app.slug`, `app.version`.

### 2.6 Multi-stage build y mínima superficie [DESEABLE]

- El Dockerfile **DEBERÍA** usar multi-stage build separando build-deps (compiladores, devDependencies) de runtime.
- La imagen final **DEBERÍA** basarse en una imagen mínima (`alpine`, `slim`, `distroless`) salvo que el stack lo impida.

### 2.7 Reintentos idempotentes en clientes HTTP [DESEABLE]

- Toda llamada saliente **DEBERÍA** implementar timeout, reintentos con backoff exponencial y jitter, y circuit breaker.
- Solo se reintentan métodos idempotentes (`GET`, `PUT`, `DELETE`) o requests con `Idempotency-Key`.

### 2.8 Documentación mínima [DESEABLE]

- El repositorio **DEBERÍA** incluir:
  - `README.md` con quickstart, arquitectura y cómo correr `docker-compose.dev.yml`.
  - `RUNBOOK.md` con incidentes comunes y comandos de debug.
  - `CHANGELOG.md` siguiendo Keep a Changelog.
  - `SECURITY.md` con canal de reporte de vulnerabilidades.

### 2.9 `docker-compose.dev.yml` con mock del Maestro [DESEABLE]

- El repositorio **DEBERÍA** incluir un `docker-compose.dev.yml` que arranque la app + su BD + un mock que simule los headers `X-Auth-*` para desarrollo local sin Maestro real.
- El mock recomendado: imagen `ghcr.io/llyasoc-digital/maestro-dev-mock:latest` (provista por el equipo de plataforma).

---

## 3. Requisitos NEGOCIABLES

Esta sección lista las decisiones que **PUEDEN** tomarse libremente; la plataforma no impone preferencia.

### 3.1 Stack tecnológico [NEGOCIABLE]

Cualquier lenguaje y framework que pueda containerizarse. Stacks reconocidos por el sistema agéntico (que les asigna especialista preconfigurado): `node-express`, `node-fastify`, `node-nestjs`, `python-django`, `python-flask`, `python-fastapi`, `php-laravel`, `go-gin`, `go-fiber`, `java-spring`, `dotnet-aspnet`, `rust-actix`. Otros stacks funcionan pero sin agente especializado.

### 3.2 Motor de base de datos [NEGOCIABLE dentro del enum]

`postgres | mysql | mongo | sqlite | none`. **PUEDE** elegirse el que mejor se adapte. Recomendación: PostgreSQL salvo justificación técnica explícita.

### 3.3 Variables de entorno custom [NEGOCIABLE]

Cualquier variable que no caiga bajo prefijos reservados (`MAESTRO_*`, `X_AUTH_*`, `DATABASE_URL`). Declararlas en `env`.

### 3.4 Layout interno del repositorio [NEGOCIABLE bajo restricciones]

La estructura de directorios internos (`src/`, `app/`, `pkg/`, `internal/`, etc.) es libre siempre que se respeten los archivos en raíz exigidos por §1 y §6.

### 3.5 Idioma de UI [NEGOCIABLE]

La app **PUEDE** servir UI en cualquier idioma. Para multi-idioma, leer el header `Accept-Language` o exponer un selector. Maestro **NO** impone un idioma.

### 3.6 Estrategia de testing [NEGOCIABLE]

Maestro no exige cobertura mínima. Recomendación industria: ≥ 70 % en lógica de negocio. Ver `APP_HUESPED_BEST_PRACTICES.md` §6.

### 3.7 Modelo de licenciamiento de la app [NEGOCIABLE]

La app puede ser propietaria o open-source. La plataforma no impone licencia; sí exige que el repositorio incluya un archivo `LICENSE` legible.

---

## 4. Estructura de datos del contrato `maestro.yaml`

### 4.1 Esqueleto canónico

```yaml
apiVersion: maestro.platform/v1
kind: Application
metadata:
  name: <slug>
  version: <semver>
  description: <texto libre, ≤ 500 chars>
requires:
  database: postgres | mysql | mongo | sqlite | none
  ports:
    app: <int 1024–65535>
health:
  endpoint: /health
  timeout_seconds: 3        # opcional, 1–5, default 3
auth:
  mode: header
  headers:                  # subconjunto de los 5 estándar, mínimo 3
    - X-Auth-User-Id
    - X-Auth-User-Email
    - X-Auth-Company-Id
    - X-Auth-Roles
    - X-Auth-Permissions
resources:
  memory: 256m | 512m | 1g | 2g | 4g
  cpu: <float 0.25–4.0>
hooks:                      # opcional
  on_user_added: /hooks/user-added
  on_user_removed: /hooks/user-removed
  on_company_license_granted: /hooks/license-granted
  on_company_license_revoked: /hooks/license-revoked
env:                        # opcional, lista de nombres custom
  - SMTP_HOST
  - REDIS_URL
  - FEATURE_FLAGS_API_KEY
```

### 4.2 Diccionario de campos

| Campo | Tipo | Obligatorio | Validación | Descripción |
|---|---|---|---|---|
| `apiVersion` | string | Sí | enum `["maestro.platform/v1"]` | Versión del contrato. |
| `kind` | string | Sí | enum `["Application"]` | Tipo de recurso. |
| `metadata.name` | string | Sí | regex `^[a-z0-9][a-z0-9-]{2,49}$` | Slug único, 3–50 chars. **Inmutable** una vez registrado. |
| `metadata.version` | string | Sí | regex `^\d+\.\d+\.\d+$` | SemVer estricto, sin prefijo `v` ni sufijo. |
| `metadata.description` | string | No | ≤ 500 chars | Mostrado en catálogo del portal. |
| `requires.database` | string | Sí | enum `[postgres, mysql, mongo, sqlite, none]` | Motor a provisionar. |
| `requires.ports.app` | integer | Sí | 1024 ≤ x ≤ 65535 | Puerto interno donde escucha la app. **DEBE** coincidir con `EXPOSE` del Dockerfile. |
| `health.endpoint` | string | Sí | regex `^/.*` | Ruta HTTP sin auth. |
| `health.timeout_seconds` | integer | No | 1–5, default 3 | Timeout del health check. |
| `auth.mode` | string | Sí | enum `["header"]` | Único modo soportado. |
| `auth.headers` | array | Sí | minItems 3, uniqueItems, valores del enum X-Auth-* | Subconjunto de headers consumidos. |
| `resources.memory` | string | Sí | enum `[256m, 512m, 1g, 2g, 4g]` | Tier de memoria. |
| `resources.cpu` | number | Sí | 0.25 ≤ x ≤ 4.0 | Fracción de core. |
| `hooks.on_user_added` | string | No | regex `^/.*` | POST que recibe evento. |
| `hooks.on_user_removed` | string | No | regex `^/.*` | POST que recibe evento. |
| `hooks.on_company_license_granted` | string | No | regex `^/.*` | POST que recibe evento. |
| `hooks.on_company_license_revoked` | string | No | regex `^/.*` | POST que recibe evento. |
| `env` | array | No | strings regex `^[A-Z][A-Z0-9_]*$`, no reservados, uniqueItems | Vars de entorno custom. |

### 4.3 Restricciones cruzadas

- Si `requires.database = "none"`, la variable `DATABASE_URL` **NO** se inyecta y la app **NO DEBE** intentar leerla.
- El puerto `requires.ports.app` **DEBE** coincidir con al menos un `EXPOSE` del Dockerfile (verificación estática del CLI).
- `auth.headers` **DEBE** declarar al menos `X-Auth-User-Id`, `X-Auth-Company-Id` y uno más. Apps que solo lean roles sin user-id son arquitectónicamente inválidas.
- `resources.memory` y `resources.cpu` **DEBEN** estar dentro del mismo tier (ver §8). El CLI no permite combinaciones cruzadas (ej.: `memory: 4g` + `cpu: 0.25`).

### 4.4 Compatibilidad de versiones del contrato

- `maestro.platform/v1` es la única versión soportada.
- Cuando el equipo de plataforma libere `v2`, las apps en `v1` seguirán funcionando durante un período de gracia mínimo de **12 meses**.
- La migración a `v2` se documentará en una guía dedicada y herramienta `maestro-cli migrate-contract`.

---

## 5. Estructura de headers de autenticación

### 5.1 Flujo de inyección

```
Browser → Traefik:443
Traefik → ForwardAuth → Maestro (POST /api/v1/auth/verify)
Maestro → Traefik (200 + headers JSON)
Traefik → App-container (request original + headers X-Auth-* añadidos)
```

Los headers **siempre** se inyectan por Traefik, **nunca** por el cliente. Si la app recibe un request sin headers `X-Auth-*`, **DEBE** asumir que es un bypass del proxy y rechazar (`401`).

### 5.2 Definición canónica de headers

```http
X-Auth-User-Id:        b3a8c0e8-2a3a-4d27-9c1c-5a8a3f8b7e21
X-Auth-User-Email:     aviera@llyasoc.com
X-Auth-Company-Id:     7e2b1f12-8b3a-4d77-bc1c-90c3bfb0a112
X-Auth-Roles:          admin,editor
X-Auth-Permissions:    users.read,users.write,reports.export
```

- Todos los headers son **case-insensitive** según RFC 7230 §3.2 (Maestro emite siempre en *Pascal-Case-Kebab*).
- Los CSV (`Roles`, `Permissions`) **NO** contienen espacios alrededor de las comas.
- `X-Auth-Roles` puede estar vacío (string vacío) si el usuario no tiene roles asignados en esta app.
- `X-Auth-Permissions` puede estar vacío. Una app **NO DEBERÍA** depender solo de roles; las decisiones finas se hacen sobre permisos.

### 5.3 Reglas de derivación

A partir de los headers, la app construye internamente un `User`:

```ts
type User = {
  id: string;            // X-Auth-User-Id
  email: string;         // X-Auth-User-Email
  companyId: string;     // X-Auth-Company-Id
  roles: string[];       // X-Auth-Roles split(",").filter(Boolean)
  permissions: string[]; // X-Auth-Permissions split(",").filter(Boolean)
};
```

- La app **DEBE** considerar los headers como **autoritativos**. No puede consultar al Maestro para "verificar" la identidad en cada request (ya lo hizo Traefik).
- La app **PUEDE** consultar al Maestro vía API REST (`GET /api/v1/users/{id}`) si necesita campos adicionales (foto, locale, último login). Estas llamadas **DEBEN** firmar con `MAESTRO_APP_SECRET` (HMAC).

### 5.4 Headers prohibidos

La app **NO DEBE** confiar en los siguientes headers para identidad o autorización:

- `Authorization` (lo consume y descarta Traefik tras ForwardAuth).
- `Cookie` (Traefik no lo retransmite a la app huésped salvo configuración explícita).
- `X-Forwarded-User` o variantes legacy (no se inyectan).
- Cualquier header custom que no comience por `X-Auth-`.

---

## 6. Estructura del repositorio

### 6.1 Layout obligatorio

```
.
├── maestro.yaml             [OBLIGATORIO]   Contrato (§1.1, §4)
├── Dockerfile               [OBLIGATORIO]   USER no-root + EXPOSE (§1.2)
├── docker-compose.dev.yml   [DESEABLE]      Mock del Maestro (§2.9)
├── README.md                [DESEABLE]      Quickstart (§2.8)
├── CHANGELOG.md             [DESEABLE]      Keep a Changelog
├── SECURITY.md              [DESEABLE]      Canal de reporte
├── LICENSE                  [DESEABLE]      Licencia de la app
├── CLAUDE.md                [DESEABLE]      Especialista IA (ver 07-SISTEMA-AGENTICO.md)
├── .github/
│   └── workflows/
│       └── deploy.yml       [OBLIGATORIO]   CI/CD (§10, §best-practices)
├── .dockerignore            [DESEABLE]      Excluir node_modules, .env, .git
├── .gitignore               [OBLIGATORIO]   Excluir secretos y artefactos
├── .gitleaks.toml           [DESEABLE]      Configuración del secret scanner
├── src/                     [NEGOCIABLE]    Código fuente
├── tests/                   [DESEABLE]      Suite de tests
└── migrations/              [DESEABLE]      Migraciones de BD
```

### 6.2 Archivos prohibidos en el repo

| Patrón | Motivo |
|---|---|
| `.env`, `.env.*` (excepto `.env.example`) | Secretos en código (§1.9). |
| `*.pem`, `*.key`, `*.p12`, `*.pfx`, `*.kdbx` | Claves privadas. |
| `id_rsa`, `id_ed25519`, `*.ppk` | Llaves SSH. |
| `secrets.json`, `credentials.json` | Secretos. |
| `.aws/`, `.gcp/`, `.azure/` | Credenciales cloud. |
| `node_modules/`, `vendor/` (excepto en mono-repos justificados) | Bloat. |

`.gitleaks.toml` puede usarse para alowlistear falsos positivos puntualmente (con justificación en PR).

---

## 7. Restricciones de red, puertos, naming

### 7.1 Naming de contenedores y volúmenes (impuesto por Maestro)

Estos nombres **NO** los elige la app; el Maestro los genera al provisionar. La app **DEBE** asumir que `db-<app_slug>-<company_slug>` es el hostname interno de su BD.

| Recurso | Patrón | Ejemplo |
|---|---|---|
| Contenedor app | `app-<app_slug>-<company_slug>` | `app-contabilidad-llyasoc` |
| Contenedor BD | `db-<app_slug>-<company_slug>` | `db-contabilidad-llyasoc` |
| Red privada | `app-<app_slug>-<company_slug>-net` | `app-contabilidad-llyasoc-net` |

- `app_slug` y `company_slug` cumplen `^[a-z0-9][a-z0-9-]{2,49}[a-z0-9]$`.
- Longitud total ≤ 63 chars (límite Linux hostname).

### 7.2 Namespaces reservados [PROHIBIDO usarlos]

La app **NO DEBE** crear contenedores, redes ni volúmenes con prefijos:

- `maestro-*` (core de la plataforma).
- `app-*` (apps huésped, gestionadas solo por el Maestro).
- `db-*` (BDs huésped).
- `obs-*` (stack de observabilidad).

### 7.3 Puertos

| Tipo | Permitido |
|---|---|
| Bind al host del VPS | **NO PERMITIDO** (solo Traefik bindea 80/443). |
| Listen interno declarado | Sí, único, en `requires.ports.app`, 1024 ≤ x ≤ 65535. |
| Conexión saliente | Permitida solo a `MAESTRO_API_URL`, al hostname `db-<slug>-<company>` (su BD), y a internet si la app lo necesita (sujeto a egress policy futura). |

### 7.4 DNS interno

- Dentro de la red privada: la BD se resuelve por nombre `db-<app_slug>-<company_slug>`.
- Dentro de `maestro-network`: se puede resolver `maestro-api` (URL completa siempre proviene de `MAESTRO_API_URL`).
- La app **NO DEBE** intentar resolver nombres que no le pertenezcan.

### 7.5 Imágenes Docker

| Patrón | Uso |
|---|---|
| `ghcr.io/<owner>/<app_slug>:<semver>` | Imagen de la app (canónico). |
| `ghcr.io/<owner>/<app_slug>:<commit_sha>` | Imagen anclada a commit (también válida; usada por Maestro para rollbacks). |
| `*:latest` | **PROHIBIDO** en producción. Permitido solo en `docker-compose.dev.yml`. |

Tags inmutables: una imagen publicada **NO** se re-pushea con el mismo tag.

---

## 8. Tiers de recursos

| Tier | CPU | Memoria | Storage BD | Casos típicos |
|---|---|---|---|---|
| `micro` | 0.25 core | `256m` | 1 GB | API simples, dashboards, lectores. |
| `standard` | 0.5 core | `512m` | 5 GB | Mayoría de apps típicas. |
| `professional` | 1.0 core | `1g` | 20 GB | Cargas medias, ETL liviano. |
| `enterprise` | 2.0 core | `2g`–`4g` | 50 GB | Alta carga, procesamiento intensivo. |

- El tier se **infiere** a partir de `resources.memory` y `resources.cpu` declarados.
- Combinaciones inválidas (ej.: `cpu: 4.0` con `memory: 256m`) se rechazan en validación.
- Cambiar de tier requiere bump de versión del contrato y redespliegue.

---

## 9. Webhooks y firma HMAC

### 9.1 Eventos emitidos por el Maestro

| Evento | Cuándo se emite | Payload |
|---|---|---|
| `on_user_added` | Usuario agregado a una empresa con licencia activa de esta app. | `{user_id, email, company_id, roles, timestamp, event_id}` |
| `on_user_removed` | Usuario removido o licencia individual revocada. | `{user_id, company_id, timestamp, event_id}` |
| `on_company_license_granted` | Empresa adquiere licencia de esta app. | `{company_id, plan, max_users, timestamp, event_id}` |
| `on_company_license_revoked` | Empresa pierde licencia. | `{company_id, reason, timestamp, event_id}` |

### 9.2 Firma del cuerpo

```
X-Maestro-Webhook-Signature: t=<unix_ts>,v1=<hex_hmac_sha256>
```

Donde `v1 = HMAC-SHA256(secret = MAESTRO_APP_SECRET, message = "<unix_ts>.<raw_body>")`.

La app **DEBE**:

1. Leer el header.
2. Verificar que `|now - t| ≤ 300` segundos (anti-replay).
3. Recalcular el HMAC y comparar en **tiempo constante** (`crypto.timingSafeEqual` en Node, `hmac.compare_digest` en Python).
4. Rechazar con `HTTP 401` si la firma no coincide.

### 9.3 Idempotencia

- Cada evento incluye `event_id` (UUID v4).
- La app **DEBE** persistir `event_id` y rechazar duplicados con `HTTP 200` (acepta pero no reprocesa). El Maestro reintenta hasta 3 veces; sin idempotencia, el equipo de la app verá doble efecto.

---

## 10. Proceso de validación CLI

El comando `maestro-cli validate` ejecuta, en orden:

1. **Schema:** `maestro.yaml` existe en raíz y valida contra el JSON Schema.
2. **Dockerfile USER:** instrucción `USER` presente, no-root, no UID 0 (en stage final si es multi-stage).
3. **Health endpoint declarado:** `health.endpoint` presente, no vacío, comienza con `/`.
4. **Recursos declarados:** `resources.memory` y `resources.cpu` presentes y dentro de tier coherente.
5. **Secret-scan:** `gitleaks` sobre todo el historial de git.
6. **Auth headers:** `auth.mode = header` y al menos los 3 headers mínimos declarados.
7. **Puerto:** `requires.ports.app` coincide con un `EXPOSE` del Dockerfile.
8. **Reservados:** ningún `env` colisiona con `MAESTRO_*`, `X_AUTH_*`, `DATABASE_URL`.

Si **cualquier** verificación falla, exit code ≠ 0 y el pipeline se detiene. La salida del CLI es JSON estructurado para ser leído por GitHub Actions y mostrado en el PR.

---

## 11. Anti-patrones que bloquean despliegue

| Anti-patrón | Detección | Bloquea |
|---|---|---|
| Login propio (formulario, JWT, sesión cookie) | Code review + heurística CLI (busca rutas `/login`, `/register` no tras ForwardAuth). | Sí |
| Tag `:latest` en `FROM` o como imagen final | Estática | Sí |
| Ejecutar como root (`USER root` o sin USER) | Estática | Sí |
| Secreto en `git log` | gitleaks | Sí |
| Conectar a BD ajena (hostname `db-otro-tenant`) | Code review + tests | Sí |
| Llamada directa a otra app (`http://app-otra-empresa:8080`) | Code review | Sí |
| Bypass de filtrado por tenant (`raw query sin company_id`) | Code review + tests del SDK | Sí |
| `rejectUnauthorized: false` en cliente HTTPS | grep estático | Sí en producción |
| Loguear `X-Auth-*` completos | grep estático en logs estructurados | Warning + revisión |
| `health.endpoint` que ejecuta `SELECT *` sobre tabla grande | Code review | Warning |
| Migraciones que dropean columnas en mismo release que las introducen | Code review | Warning |

---

## 12. Anexo A — Ejemplo end-to-end Node.js (Express + Postgres)

### 12.1 `maestro.yaml`

```yaml
apiVersion: maestro.platform/v1
kind: Application
metadata:
  name: inventory-manager
  version: 1.4.2
  description: Gestión de inventario y movimientos de stock con alertas configurables.
requires:
  database: postgres
  ports:
    app: 8080
health:
  endpoint: /healthz
  timeout_seconds: 3
auth:
  mode: header
  headers:
    - X-Auth-User-Id
    - X-Auth-User-Email
    - X-Auth-Company-Id
    - X-Auth-Roles
resources:
  memory: 512m
  cpu: 0.5
hooks:
  on_user_added: /webhooks/maestro/user-added
  on_company_license_revoked: /webhooks/maestro/license-revoked
env:
  - SMTP_HOST
  - SMTP_PORT
  - SMTP_USER
  - SMTP_PASSWORD_REF
```

### 12.2 `Dockerfile`

```dockerfile
# syntax=docker/dockerfile:1.7

FROM node:22.13-alpine@sha256:abc123... AS deps
WORKDIR /app
COPY package*.json ./
RUN --mount=type=cache,target=/root/.npm \
    npm ci --omit=dev

FROM node:22.13-alpine@sha256:abc123... AS build
WORKDIR /app
COPY package*.json ./
RUN npm ci
COPY . .
RUN npm run build

FROM node:22.13-alpine@sha256:abc123... AS runtime
RUN addgroup -S app && adduser -S app -G app
WORKDIR /app
COPY --from=deps /app/node_modules ./node_modules
COPY --from=build /app/dist ./dist
COPY --from=build /app/package.json ./
USER app
EXPOSE 8080
HEALTHCHECK --interval=30s --timeout=3s --start-period=10s --retries=3 \
  CMD wget -qO- http://127.0.0.1:8080/healthz || exit 1
CMD ["node", "dist/server.js"]
```

### 12.3 Servidor mínimo con SDK

```ts
// src/server.ts
import express from 'express';
import { maestroAuth, maestroDb } from '@maestro/sdk-node';

const app = express();
app.use(express.json());

app.get('/healthz', async (_req, res) => {
  const ok = await maestroDb.ping();
  res.status(ok ? 200 : 503).json({ status: ok ? 'ok' : 'degraded' });
});

app.use(maestroAuth());

app.get('/items', async (req, res) => {
  const items = await maestroDb.query(
    'SELECT id, sku, name, qty FROM items',
    { user: req.user }
  );
  res.json(items);
});

app.post('/webhooks/maestro/user-added', maestroAuth.webhook(), async (req, res) => {
  await onUserAdded(req.body);
  res.json({ ok: true });
});

app.listen(8080, () => console.log('listening :8080'));
```

### 12.4 Workflow CI/CD (`.github/workflows/deploy.yml`)

```yaml
name: deploy

on:
  push:
    branches: [main]
  pull_request:

permissions:
  contents: read
  id-token: write
  packages: write

jobs:
  validate:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
        with: { fetch-depth: 0 }
      - uses: actions/setup-node@v4
        with: { node-version: '22', cache: 'npm' }
      - run: npm ci
      - run: npm run lint
      - run: npm test -- --ci
      - run: npx -y @maestro/cli@latest validate
      - uses: gitleaks/gitleaks-action@v2
        env: { GITLEAKS_LICENSE: ${{ secrets.GITLEAKS_LICENSE }} }

  build-and-push:
    needs: validate
    if: github.ref == 'refs/heads/main'
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - uses: docker/setup-buildx-action@v3
      - uses: docker/login-action@v3
        with:
          registry: ghcr.io
          username: ${{ github.actor }}
          password: ${{ secrets.GITHUB_TOKEN }}
      - uses: docker/build-push-action@v6
        with:
          context: .
          push: true
          tags: |
            ghcr.io/${{ github.repository }}:${{ github.sha }}
            ghcr.io/${{ github.repository }}:1.4.2
          cache-from: type=gha
          cache-to: type=gha,mode=max
          provenance: true
          sbom: true
      - uses: aquasecurity/trivy-action@0.24.0
        with:
          image-ref: ghcr.io/${{ github.repository }}:${{ github.sha }}
          severity: CRITICAL,HIGH
          exit-code: '1'
      - uses: sigstore/cosign-installer@v3
      - run: cosign sign --yes ghcr.io/${{ github.repository }}@${{ steps.build.outputs.digest }}
      - name: Register on Maestro
        run: |
          curl -fsSL -X POST "$MAESTRO_API_URL/api/v1/apps/register" \
            -H "Authorization: Bearer $MAESTRO_REGISTRATION_TOKEN" \
            -H "Content-Type: application/json" \
            -d @- <<EOF
          {
            "name": "inventory-manager",
            "version": "1.4.2",
            "image": "ghcr.io/${{ github.repository }}@${{ steps.build.outputs.digest }}",
            "commit": "${{ github.sha }}",
            "contract_hash": "$(sha256sum maestro.yaml | cut -d' ' -f1)"
          }
          EOF
        env:
          MAESTRO_API_URL: ${{ secrets.MAESTRO_API_URL }}
          MAESTRO_REGISTRATION_TOKEN: ${{ secrets.MAESTRO_REGISTRATION_TOKEN }}
```

---

## 13. Anexo B — Ejemplo end-to-end PHP/Laravel

### 13.1 `maestro.yaml`

```yaml
apiVersion: maestro.platform/v1
kind: Application
metadata:
  name: hr-dashboard
  version: 0.9.0
  description: Tablero de RRHH con KPIs y aprobaciones de tickets.
requires:
  database: mysql
  ports:
    app: 8080
health:
  endpoint: /up
  timeout_seconds: 3
auth:
  mode: header
  headers:
    - X-Auth-User-Id
    - X-Auth-User-Email
    - X-Auth-Company-Id
    - X-Auth-Roles
    - X-Auth-Permissions
resources:
  memory: 512m
  cpu: 0.5
env:
  - APP_ENV
  - APP_KEY_REF
  - LOG_CHANNEL
```

### 13.2 `Dockerfile` (PHP-FPM + Caddy)

```dockerfile
FROM composer:2 AS vendor
WORKDIR /app
COPY composer.json composer.lock ./
RUN composer install --no-dev --no-interaction --no-progress --prefer-dist --optimize-autoloader

FROM php:8.3-fpm-alpine AS runtime
RUN apk add --no-cache caddy mysql-client \
 && docker-php-ext-install pdo_mysql opcache \
 && addgroup -S app && adduser -S app -G app
WORKDIR /app
COPY --from=vendor /app/vendor ./vendor
COPY . .
RUN chown -R app:app /app/storage /app/bootstrap/cache
USER app
EXPOSE 8080
CMD ["sh", "-c", "php-fpm -D && caddy run --config /etc/caddy/Caddyfile --adapter caddyfile"]
```

### 13.3 Middleware con SDK Laravel

```php
// app/Http/Kernel.php
protected $middlewareGroups = [
    'web' => [
        \Maestro\Sdk\Middleware\InjectAuthFromHeaders::class,
        \Maestro\Sdk\Middleware\RequireTenantContext::class,
        // ...
    ],
];

// app/Models/Concerns/TenantAware.php (trait provisto por SDK)
class Ticket extends Model
{
    use \Maestro\Sdk\Eloquent\TenantAware;
    // El scope global agrega WHERE company_id = Auth::user()->companyId
}
```

---

## 14. Glosario

| Término | Definición |
|---|---|
| **App huésped** | Aplicación de tercero o equipo interno alojada en Maestro Platform. |
| **Instancia** | Combinación única de una app + una empresa + sus datos. Cada instancia tiene contenedor y BD propios. |
| **Tenant / Empresa** | Cliente final identificado por `company_id`. Todo dato pertenece a un tenant. |
| **Maestro** | Aplicación Laravel central que gestiona auth, provisionamiento, billing y orquestación. |
| **Contrato (`maestro.yaml`)** | Archivo que la app declara para integrarse con la plataforma. |
| **ForwardAuth** | Middleware de Traefik que valida el token con el Maestro antes de reenviar el request. |
| **SDK oficial** | Librería provista por la plataforma para Node, Python, PHP-Laravel, Go. |
| **Tier** | Nivel de recursos asignados (`micro`, `standard`, `professional`, `enterprise`). |
| **Cold start** | Tiempo desde despertar una instancia dormida hasta que responde tráfico. |

---

## 15. Referencias normativas

| Documento | Rol |
|---|---|
| `PremisaWebMaestro/01-PREMISAS-Y-NO-NEGOCIABLES.md` | Constitución de la plataforma. Prevalece sobre este documento en caso de conflicto. |
| `PremisaWebMaestro/04-INFRAESTRUCTURA-DOCKER.md` | Topología Docker, ciclo de vida de instancias, tiers. |
| `PremisaWebMaestro/06-SDK-Y-CONTRATO.md` | Origen narrativo del contrato. Este documento es su versión normativa. |
| `PremisaWebMaestro/08-CICD-Y-GOBERNANZA.md` | Pipelines, repos, despliegue blue-green. |
| `PremisaWebMaestro/09-SEGURIDAD.md` | Modelo de amenazas, audit logs. |
| `docs/CONVENCIONES_PLATAFORMA.md` | Naming, redes, puertos, vars de entorno. |
| `docs/schemas/maestro.yaml.schema.json` | JSON Schema canónico (fuente de verdad de la validación). |
| `docs/APP_HUESPED_BEST_PRACTICES.md` | Recomendaciones no normativas que complementan este documento. |

---

## 16. Historial de revisiones

| Versión | Fecha | Cambio |
|---|---|---|
| 1.0.0 | 2026-04-28 | Versión inicial consolidada. Cubre contrato `maestro.platform/v1`. |
