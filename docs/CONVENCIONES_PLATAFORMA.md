# Convenciones de la Plataforma Maestro — Coexistencia Maestro ↔ Apps Huésped

> **Fuente de verdad** para naming, puertos, redes, volúmenes, subdominios y variables de entorno que **TODA aplicación huésped (contrato `maestro.platform/v2`)** debe respetar.
>
> **Versión del contrato:** `maestro.platform/v2`
> **Framework agéntico:** v4
> **Última revisión:** 2026-05-07.
> **Reemplaza a:** `legacy/v3/docs/CONVENCIONES_PLATAFORMA.md` (convenciones v1).
>
> **Cambio principal v1 → v2:** single-tenant fisico (un contenedor = una empresa). El `company_slug` ya no aparece en naming de contenedores ni redes; cada deployment de app es independiente.
>
> Este documento es **normativo**. Cualquier app huésped que no lo cumpla **no se provisiona**.

---

## 1. Naming

### 1.1 Contenedores Docker

| Tipo | Patrón | Ejemplo |
|---|---|---|
| Servicio core del Maestro v2 | `maestro-<servicio>` | `maestro-api`, `maestro-portal`, `maestro-db`, `maestro-traefik` |
| Worker del Maestro v2 | `maestro-worker-<rol>` | `maestro-worker-health`, `maestro-worker-registry` |
| Contenedor app huésped (uno por empresa) | `app-<app_slug>-<empresa_slug>` | `app-contabilidad-llyasoc` |
| BD dedicada de app | `db-<app_slug>-<empresa_slug>` | `db-contabilidad-llyasoc` |
| Observabilidad | `obs-<componente>` | `obs-prometheus`, `obs-grafana`, `obs-loki` |

> **Nota v2:** aunque el contenedor de app huésped sirve a UNA empresa (single-tenant fisico), el `empresa_slug` sigue presente en el naming **del contenedor** para que el operador (Maestro v2) distinga entre deployments de la misma app para distintas empresas. Pero **dentro del contenedor**, no hay logica de tenancy: un solo deployment, una sola empresa, sin `company_id` en queries.

**Reglas de nombres:**
- **Namespace `maestro-*`**: reservado exclusivamente para el core del Maestro.
- **Namespace `app-*`**: reservado para deployments de apps huésped.
- **Namespace `db-*`**: reservado para BDs dedicadas.
- **Namespace `obs-*`**: reservado para observabilidad.
- `app_slug` y `empresa_slug` deben cumplir regex `^[a-z0-9][a-z0-9-]{2,49}[a-z0-9]$`.
- Longitud total ≤ 63 chars.

### 1.2 Imágenes Docker

| Registry | Uso |
|---|---|
| `ghcr.io/llyasoc-digital/maestro-api:<version>` | Backend del Maestro v2 |
| `ghcr.io/llyasoc-digital/maestro-portal:<version>` | Portal del Maestro v2 |
| `ghcr.io/<owner>/<app_slug>:<semver>` | Imágenes de apps huésped (independiente de empresa) |

Tags inmutables. `latest` prohibido en producción.

> **Nota v2:** la imagen de la app es la misma para todas las empresas que la usan. La diferenciación se hace en el deployment (un contenedor por empresa, distintos `DATABASE_URL`, distintos secrets).

---

## 2. Redes Docker

### 2.1 Definición

| Red | Propósito | Miembros |
|---|---|---|
| `maestro-network` | Edge + backplane del Maestro v2 | Traefik, maestro-api, maestro-portal, maestro-db, obs-* |
| `app-<app_slug>-<empresa_slug>-net` | Red privada del deployment | contenedor de la app + su BD dedicada |

### 2.2 Conectividad

- El contenedor de **app huésped** está conectado a `app-<slug>-<empresa>-net` (con su BD) y a `maestro-network` (para que Traefik enrute trafico).
- El contenedor de **BD** está conectado **exclusivamente** a su red privada.
- **Prohibido** conectar contenedores de distintos deployments entre sí directamente.
- Comunicación inter-apps: vía API Gateway del Maestro v2 (futuro), nunca conexión directa.

### 2.3 DNS interno Docker

- Dentro de `maestro-network`: contenedores se resuelven por nombre.
- Dentro de `app-<slug>-<empresa>-net`: la app resuelve su BD por `db-<slug>-<empresa>`.
- **Variable canónica** que la app recibe: `DATABASE_URL=postgres://<user>:<pass>@db-<slug>-<empresa>:5432/<dbname>`.

---

## 3. Puertos

### 3.1 Puertos expuestos al host

**Solo Traefik** expone puertos al exterior:
- `80/tcp` → redirect 301 a 443.
- `443/tcp` → tráfico HTTPS.

Ningun otro servicio se expone al host.

### 3.2 Puertos internos (dentro de redes Docker)

| Servicio | Puerto |
|---|---|
| maestro-api | 8080 |
| maestro-portal | 8081 |
| maestro-db | 5432 |
| Traefik admin (interno) | 8082 |
| Observability stack | 9090 (prom), 3000 (grafana), 3100 (loki) |
| Contenedor app huésped | declarado en `maestro.yaml` `requires.ports.app` (1024–65535) |
| BD de app huésped | 5432 (postgres), 3306 (mysql), 27017 (mongo) |

Apps huésped no pueden declarar puertos < 1024.

---

## 4. Volúmenes

### 4.1 Nombres y contenido

| Volumen | Contenido |
|---|---|
| `maestro-db-data` | PostgreSQL data dir del Maestro v2 |
| `maestro-traefik-acme` | Certificados Let's Encrypt |
| `maestro-secrets` | Secrets del Maestro (API keys, passwords) |
| `obs-*-data` | Data de observabilidad |
| `db-<app_slug>-<empresa_slug>-data` | PostgreSQL data dir de un deployment de app |

### 4.2 Reglas

- Apps huésped no pueden solicitar volúmenes custom al Maestro v2.
- Filesystem del contenedor de app es **efímero** — todo estado persistente va a la BD o a blob storage externo.

---

## 5. Subdominios y ruteo Traefik

### 5.1 Patrón de subdominios

Base: `<MAESTRO_BASE_DOMAIN>` (ej: `maestro.llyasoc.com`).

| Subdominio | Ruta a |
|---|---|
| `<MAESTRO_BASE_DOMAIN>` | Portal del Maestro v2 |
| `<app_slug>-<empresa_slug>.<MAESTRO_BASE_DOMAIN>` | Deployment de app huésped (URL que el portal abre en `target="_blank"`) |
| `grafana.<MAESTRO_BASE_DOMAIN>` | Grafana (admin only) |

### 5.2 Labels Traefik para deployments huésped (cambio v1 → v2)

```yaml
labels:
  - "traefik.enable=true"
  - "traefik.docker.network=maestro-network"
  - "traefik.http.routers.app-<slug>-<empresa>.rule=Host(`<slug>-<empresa>.<MAESTRO_BASE_DOMAIN>`)"
  - "traefik.http.routers.app-<slug>-<empresa>.entrypoints=websecure"
  - "traefik.http.routers.app-<slug>-<empresa>.tls=true"
  - "traefik.http.routers.app-<slug>-<empresa>.tls.certresolver=letsencrypt"
  # NOTA v2: NO HAY middleware ForwardAuth.
  # La app v2 maneja su propia auth. Traefik solo enruta tráfico.
  - "traefik.http.routers.app-<slug>-<empresa>.middlewares=security-headers@file,rate-limit@file"
  - "traefik.http.services.app-<slug>-<empresa>.loadbalancer.server.port=<app_port_from_maestro_yaml>"
```

> **Cambio crítico v1 → v2:** ya no hay `forward-auth-maestro` middleware. Traefik no inyecta headers `X-Auth-*`. La app autentica al usuario por su cuenta.

---

## 6. Variables de entorno

### 6.1 Inyectadas por el Maestro v2 a cada deployment de app huésped

El motor de provisioning del Maestro v2 inyecta:

| Variable | Contenido |
|---|---|
| `DATABASE_URL` | Connection string de la BD dedicada |
| `MAESTRO_BASE_URL` | URL pública del Maestro v2 |
| `MAESTRO_APP_ID` | UUID de la app en el catálogo |
| `MAESTRO_APP_SLUG` | Slug de la app |
| `MAESTRO_EMPRESA_ID` | UUID de la empresa que opera este contenedor |
| `MAESTRO_EMPRESA_SLUG` | Slug de la empresa |
| `MAESTRO_DEPLOYMENT_ID` | UUID único de este deployment |
| `MAESTRO_API_KEY` | Secret compartido para que el Maestro v2 consuma `/maestro/branding` de la app |
| `MAESTRO_WEBHOOK_SECRET` | Secret HMAC para verificar hooks entrantes (si la app declara hooks) |
| `SUPERADMIN_INITIAL_PASSWORD` | Password inicial del superadmin (consumida por la fase 05-seeding) |
| `APP_KEY` o `JWT_SECRET` (segun stack) | Secret para firmar tokens propios de la app |
| `APP_ENV` | `local | staging | production` |
| `LOG_LEVEL` | default `info` |
| Custom env vars declaradas en `maestro.yaml.env` | propagadas tal cual |

> **Cambio v2:** se agregan `MAESTRO_API_KEY`, `SUPERADMIN_INITIAL_PASSWORD`. Ya NO se inyectan headers `X-Auth-*` (eso era trabajo de Traefik en v1).

### 6.2 Prefijos reservados

Las apps huésped **NO DEBEN** usar variables con estos prefijos:

- `MAESTRO_*` (reservado para metadata y coordinación)
- `SUPERADMIN_*` (reservado para seeding del superadmin)
- `DATABASE_URL` (sera sobrescrita por el Maestro v2)

### 6.3 Headers HTTP reservados (cambio v1 → v2)

- `X-Maestro-Api-Key`: la app **DEBE** consumirlo (lo envía el Maestro v2 al consumir `/maestro/branding`).
- `X-Maestro-Webhook-Signature`: la app **DEBE** verificarlo en endpoints de hooks.
- `X-Auth-*`: **DEPRECADOS en v2.** El Maestro v2 NO los inyecta. La app NO debe leerlos.

---

## 7. Recursos (CPU / memoria)

### 7.1 Tiers disponibles v2

| Tier | Memoria | CPU |
|---|---|---|
| `small` | 256m | 0.25 |
| `default` | 512m | 0.5 |
| `medium` | 1g | 1.0 |
| `large` | 2g | 2.0 |
| `xlarge` | 4g | 4.0 |

(Igual que v1.) Cada app declara `resources.memory` y `resources.cpu` en `maestro.yaml`.

### 7.2 Reglas

- Es obligatorio declarar ambos campos.
- Si el consumo real excede sostenidamente el 90 % por > 30 min: alerta.
- Si excede el 100 % de memory: OOM Killer → restart automático.

---

## 8. Dockerfile — Reglas normativas v2

(Mayoritariamente igual a v1.)

```dockerfile
# Multi-stage obligatorio
FROM node:20-alpine AS build
WORKDIR /app
# ...

FROM node:20-alpine AS runtime
WORKDIR /app

# Usuario no-root
RUN addgroup -g 1001 -S app && adduser -u 1001 -S app -G app
USER app

COPY --from=build --chown=app:app /app/dist ./dist
COPY --from=build --chown=app:app /app/node_modules ./node_modules

EXPOSE 3000
HEALTHCHECK --interval=30s --timeout=5s --retries=3 \
  CMD wget -q -O- http://localhost:3000/health || exit 1

CMD ["node", "dist/index.js"]
```

Reglas verificadas:
- ✅ `USER` directive presente y no-root.
- ✅ `HEALTHCHECK` instruction.
- ✅ `EXPOSE` con puerto coincidente con `maestro.yaml.requires.ports.app`.
- ❌ `COPY .env*` (usar `.dockerignore`).
- ❌ `--privileged`.
- ❌ Hardcodeo de secretos.

---

## 9. `maestro.yaml` v2 — Contrato resumido

Ver `docs/APP_HUESPED_SPEC.md §5` para la especificación completa.

Ejemplo canónico v2:

```yaml
apiVersion: maestro.platform/v2
kind: Application
metadata:
  name: contabilidad
  version: 2.0.0
requires:
  database: postgres
  ports:
    app: 3000
health:
  endpoint: /health
  timeout_seconds: 5
auth:
  mode: own                          # v2: solo "own"
  login_path: /login
  logout_path: /logout               # opcional
branding:
  url: /maestro/branding             # endpoint autenticado con X-Maestro-Api-Key
resources:
  memory: 512m
  cpu: 0.5
seeding:
  superadmin_email: admin@llyasoc.com
  additional_users: []
hooks:
  on_user_added: /hooks/user-added   # opcional
env:
  - SMTP_HOST
  - REDIS_URL
```

Diferencias claves vs v1:
- `apiVersion: maestro.platform/v2` (era `v1`)
- `auth.mode: own` (era `header`)
- `auth.login_path` (NEW; obligatorio en v2)
- `auth.logout_path` (NEW; opcional)
- `auth.headers` ELIMINADO (no aplica)
- `branding.url` (NEW; obligatorio en v2)
- `seeding.*` (NEW; obligatorio en v2)

---

## 10. Logging

### 10.1 Formato obligatorio

Toda app huésped debe loguear a stdout/stderr en JSON:

```json
{
  "timestamp": "2026-05-06T14:23:01.234Z",
  "level": "info",
  "message": "user.login.success",
  "request_id": "req_01HY...",
  "user_id": "uuid",
  "app_slug": "<slug>"
}
```

> **Cambio v2:** se agrega `user_id`, **se elimina `company_id`** (single-tenant fisico).

### 10.2 Prohibiciones

- **Nunca loguear:** passwords, hashes, JWTs propios, `MAESTRO_API_KEY`, `MAESTRO_WEBHOOK_SECRET`, `SUPERADMIN_INITIAL_PASSWORD`, cookies de sesion, bodies de requests con datos sensibles.

---

## 11. Ciclo de vida de un deployment v2

```
1. Equipo construye app v2 siguiendo `docs/APP_HUESPED_SPEC.md`.
2. CI ejecuta: maestro-cli validate (v2) + tests + trivy + build.
3. Tag semver → push imagen a ghcr.io/<owner>/<app_slug>:<version>.
4. CI llama POST /api/v2/apps/register al Maestro v2 con metadata.
5. Admin del Maestro v2 licencia la app a una empresa.
6. Maestro v2 provisiona deployment: contenedor + BD + ENV vars + SUPERADMIN_INITIAL_PASSWORD.
7. Pipeline de deploy ejecuta el seeder (fase 05-seeding del framework v4): crea admin@llyasoc.com.
8. App queda online en https://<app_slug>-<empresa_slug>.<MAESTRO_BASE_DOMAIN>.
9. Maestro v2 consume /maestro/branding para mostrar nombre y logos en el portal.
10. Usuario hace click en el portal → Maestro v2 abre la URL en target="_blank".
11. Usuario hace login en la app con sus credenciales propias.
```

---

## 12. Referencias cruzadas

- `framework-agentico/CHANGELOG.md` — cambios v3 → v4
- `framework-agentico/core/PRESET_WEB_MAESTRO.md` — preset v4 (constraints por fase)
- `framework-agentico/phases/05-seeding.md` — fase de seeding
- `framework-agentico/agents/presets/maestro-platform/PRESET.md` — preset para construir la Web Maestro
- `framework-agentico/migration/v3-to-v4.md` — proceso de migración
- `docs/APP_HUESPED_SPEC.md` — especificación normativa v2
- `docs/APP_HUESPED_BEST_PRACTICES.md` — best practices v2

---

## 13. Historial de revisiones

| Versión | Fecha | Cambio |
|---|---|---|
| 2.0.0 | 2026-05-06 | Versión inicial. Convenciones para Maestro v2 / contrato `maestro.platform/v2` / framework agéntico v4. Single-tenant fisico, sin ForwardAuth, sin headers X-Auth-*. |
