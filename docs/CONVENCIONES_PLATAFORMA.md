# Convenciones de la Plataforma Maestro — Coexistencia Maestro ↔ Apps Huésped

> **Fuente de verdad** para naming, puertos, redes, volúmenes, subdominios y variables de entorno que **TODA aplicación huésped** debe respetar para coexistir con el Maestro y con otras apps huésped sin conflicto.
>
> **Deliverable DEL-001** generado en Fase 02 (Planning) el 2026-04-16.
> **Origen**: DEC-012 (zero local installs) + DEC-017 (multi-tenant con escala V1 de 1 empresa × 7 apps).
> **Vinculación**: RF-122, preset `maestro-platform` `rules/RULES.md`, ADR-011.
>
> Este documento es **normativo**. Cualquier app huésped que no lo cumpla **no se provisiona**.

---

## 1. Naming

### 1.1 Contenedores Docker

| Tipo | Patrón | Ejemplo |
|---|---|---|
| Servicio core del Maestro | `maestro-<servicio>` | `maestro-api`, `maestro-portal`, `maestro-db`, `maestro-redis`, `maestro-traefik`, `maestro-docker-proxy` |
| Worker del Maestro | `maestro-worker-<rol>` | `maestro-worker-health`, `maestro-worker-provisioning`, `maestro-worker-hooks` |
| Instancia app huésped (app) | `app-<app_slug>-<company_slug>` | `app-contabilidad-llyasoc` |
| BD dedicada de instancia | `db-<app_slug>-<company_slug>` | `db-contabilidad-llyasoc` |
| Observabilidad | `obs-<componente>` | `obs-prometheus`, `obs-grafana`, `obs-loki`, `obs-promtail`, `obs-cadvisor` |

**Reglas de nombres**:
- **Namespace `maestro-*`**: reservado exclusivamente para el core del Maestro. Ninguna app huésped puede usar este prefijo en sus contenedores, redes o volúmenes.
- **Namespace `app-*`**: reservado para instancias huésped provisionadas por el Maestro.
- **Namespace `db-*`**: reservado para BDs dedicadas de instancias huésped.
- **Namespace `obs-*`**: reservado para el stack de observabilidad.
- `app_slug` y `company_slug` deben cumplir regex `^[a-z0-9][a-z0-9-]{2,49}[a-z0-9]$` (validado por el JSON Schema de `maestro.yaml` y por la regla de validación de `companies.slug`).
- Longitud total del nombre de contenedor: **≤ 63 caracteres** (límite Linux hostname). Los slugs max 50 chars dejan margen para prefijos.

### 1.2 Imágenes Docker

| Registry | Uso |
|---|---|
| `ghcr.io/llyasoc-digital/maestro-api:<version>` | backend del Maestro |
| `ghcr.io/llyasoc-digital/maestro-portal:<version>` | portal React estático |
| `ghcr.io/llyasoc-digital/maestro-php:<version>` | base image PHP para desarrollo |
| `ghcr.io/llyasoc-digital/maestro-node:<version>` | base image Node para SDK/CLI |
| `ghcr.io/<owner>/<app_slug>:<semver>` | imágenes de apps huésped |

Tags inmutables (no re-push). `latest` **prohibido** en producción; se usa en dev.

---

## 2. Redes Docker

### 2.1 Definición

| Red | Propósito | Miembros |
|---|---|---|
| `maestro-network` | Edge + backplane del Maestro | Traefik, maestro-api, maestro-portal, maestro-db, maestro-redis, maestro-docker-proxy, obs-* |
| `app-<app_slug>-<company_slug>-net` | Red privada por instancia | contenedor de la app + su BD dedicada |

### 2.2 Conectividad

- El **contenedor de app huésped** está conectado a **dos redes**: su red privada `app-<slug>-<company>-net` (donde vive su BD) Y a `maestro-network` (solo para recibir tráfico reenviado por Traefik).
- El **contenedor de BD de una instancia** está conectado **exclusivamente** a su red privada. No es accesible desde `maestro-network` ni desde otras apps.
- **Prohibido** conectar el contenedor de BD de una instancia a `maestro-network` o a otra red.
- **Prohibido** crear rutas, aliases o DNS que permitan a una app huésped resolver contenedores de otra instancia.
- Comunicación inter-apps: **exclusivamente** vía `/api/v1/gateway/<app-destino>/<ruta>` del Maestro (ADR-007).

### 2.3 DNS interno Docker

- Dentro de `maestro-network`: los contenedores se resuelven por nombre (ej: `maestro-api` resuelve al IP del Maestro).
- Dentro de `app-<slug>-<company>-net`: el contenedor de la app resuelve su BD por el nombre `db-<slug>-<company>` (via Docker DNS).
- **Variable de entorno canónica** que la app huésped recibe: `DATABASE_URL=postgres://<user>:<pass>@db-<slug>-<company>:5432/<dbname>`. La app **debe** leer esta variable y no hardcodear hostnames.

---

## 3. Puertos

### 3.1 Puertos expuestos al host / exterior

**Solo Traefik expone puertos al exterior**:
- `80/tcp` → redirect 301 a 443.
- `443/tcp` → tráfico HTTPS.

**Nada más** se expone al host. Ni el Maestro, ni las BDs, ni las apps, ni Redis, ni Grafana. Todo queda en redes Docker internas.

### 3.2 Puertos internos (dentro de redes Docker)

| Servicio | Puerto |
|---|---|
| maestro-api (php-fpm via nginx sidecar) | 8080 |
| maestro-portal (nginx static) | 8081 |
| maestro-db (PostgreSQL) | 5432 |
| maestro-redis | 6379 |
| maestro-docker-proxy | 2375 |
| Traefik admin dashboard (interno, no expuesto) | 8082 |
| Observability stack | 9090 (prom), 3000 (grafana), 3100 (loki), ... (documentado separado) |
| Instancia app huésped | declarado en `maestro.yaml` `requires.ports.app` (1024–65535) |
| Instancia BD de app huésped | 5432 (PostgreSQL default), 3306 (MySQL), 27017 (Mongo), etc. |

**Reglas**:
- Apps huésped **no pueden** declarar puertos < 1024 (no-negociable del preset web-maestro).
- Apps huésped **no deben** intentar bindear al host (no hay `ports:` en docker-compose de instancias; todo está expuesto vía Traefik).

---

## 4. Volúmenes

### 4.1 Nombres y contenido

| Volumen | Contenido | Persistencia |
|---|---|---|
| `maestro-db-data` | PostgreSQL data dir del Maestro | backed up diario |
| `maestro-redis-data` | Redis AOF | backed up diario (opcional) |
| `maestro-traefik-acme` | Certificados Let's Encrypt | backed up diario |
| `maestro-secrets` | bind mount `/secrets/` (OAuth keys, master keys) | gestionado por humano; no por framework |
| `obs-prometheus-data`, `obs-grafana-data`, `obs-loki-data` | Data de observabilidad | retention según política |
| `db-<app_slug>-<company_slug>-data` | PostgreSQL data dir de una instancia | backed up diario |

### 4.2 Reglas

- Las apps huésped **no pueden** solicitar volúmenes custom al Maestro V1. Solo reciben la BD dedicada.
- Filesystem del contenedor de app **efímero** — todo estado persistente va a la BD, no a disco local.
- Si una app necesita storage de archivos (ej: uploads), V1 requiere usar almacenamiento externo (Azure Blob vía SDK custom; no soportado directamente V1; diferible).

---

## 5. Subdominios y ruteo Traefik

### 5.1 Patrón de subdominios

Base: `<MAESTRO_BASE_DOMAIN>` (ej: `maestro.local` en dev, `maestro.llyasoc.com` en prod).

| Subdominio | Ruta a |
|---|---|
| `<MAESTRO_BASE_DOMAIN>` | Portal (redirect a `/` o `/login`) |
| `maestro.<MAESTRO_BASE_DOMAIN>` | API + portal (mismo backend, Traefik enruta por path) |
| `<app_slug>-<company_slug>.<MAESTRO_BASE_DOMAIN>` | Instancia de app huésped |
| `grafana.<MAESTRO_BASE_DOMAIN>` | Grafana (solo admins, auth via ForwardAuth) |

### 5.2 Labels Traefik para instancias huésped

Template de labels que el motor de provisioning aplica al contenedor de una instancia:

```yaml
labels:
  - "traefik.enable=true"
  - "traefik.docker.network=maestro-network"
  - "traefik.http.routers.app-<slug>-<company>.rule=Host(`<slug>-<company>.<MAESTRO_BASE_DOMAIN>`)"
  - "traefik.http.routers.app-<slug>-<company>.entrypoints=websecure"
  - "traefik.http.routers.app-<slug>-<company>.tls=true"
  - "traefik.http.routers.app-<slug>-<company>.tls.certresolver=letsencrypt"
  - "traefik.http.routers.app-<slug>-<company>.middlewares=forward-auth-maestro@file,security-headers@file,rate-limit@file"
  - "traefik.http.services.app-<slug>-<company>.loadbalancer.server.port=<app_port_from_maestro_yaml>"
```

El middleware `forward-auth-maestro` está declarado globalmente en la config de Traefik:

```yaml
http:
  middlewares:
    forward-auth-maestro:
      forwardAuth:
        address: "http://maestro-api:8080/api/auth/validate"
        authResponseHeaders:
          - "X-Auth-User-Id"
          - "X-Auth-User-Email"
          - "X-Auth-Company-Id"
          - "X-Auth-Roles"
          - "X-Auth-Permissions"
        trustForwardHeader: false
```

---

## 6. Variables de entorno

### 6.1 Inyectadas por el Maestro a cada instancia huésped

El motor de provisioning inyecta **sólo** estas variables (no más, no menos):

| Variable | Contenido |
|---|---|
| `DATABASE_URL` | Connection string completa de la BD dedicada |
| `MAESTRO_BASE_URL` | URL pública del Maestro (ej: `https://maestro.<MAESTRO_BASE_DOMAIN>`) |
| `MAESTRO_APP_ID` | UUID de la app en el catálogo |
| `MAESTRO_APP_SLUG` | Slug de la app |
| `MAESTRO_COMPANY_ID` | UUID de la empresa (tenant) en ejecución |
| `MAESTRO_COMPANY_SLUG` | Slug de la empresa |
| `MAESTRO_INSTANCE_ID` | UUID único de la instancia |
| `MAESTRO_WEBHOOK_SECRET` | Secret HMAC para verificar hooks entrantes (proporcionado por Maestro) |
| `MAESTRO_GATEWAY_URL` | URL del endpoint gateway (ej: `https://maestro.<MAESTRO_BASE_DOMAIN>/api/v1/gateway`) |
| `MAESTRO_JWKS_URL` | URL del JWKS público (para validar JWT offline si la app quiere) |
| `APP_ENV` | `local|staging|production` |
| `LOG_LEVEL` | por default `info` |
| Custom env declaradas en `maestro.yaml.env` | propagadas tal cual |

### 6.2 Prefijos reservados (prohibidos en apps huésped)

Las apps huésped **no deben** declarar ni usar variables con estos prefijos:

- `MAESTRO_*` (reservado para metadata y coordinación con plataforma)
- `X_AUTH_*` (header values; son headers HTTP, no env vars, pero mencionamos por si confunde)
- `DATABASE_URL` (será sobrescrita por el Maestro)

Si una app declara una env var con prefijo reservado en su `maestro.yaml`, la validación del contrato falla.

### 6.3 Headers HTTP reservados

Las apps huésped no deben **emitir** estos headers en sus responses (ya que Traefik o el Maestro los inyectan en el request):

- `X-Auth-User-Id`, `X-Auth-User-Email`, `X-Auth-Company-Id`, `X-Auth-Roles`, `X-Auth-Permissions`.
- `X-Maestro-*` (reservado).
- `X-Request-Id` (propagado por Traefik; la app puede **leerlo** pero no reemplazarlo).

Las apps **deben leer** los `X-Auth-*` del request (no de cookies, no de body, no de query params).

---

## 7. Recursos (CPU / memoria)

### 7.1 Tiers disponibles V1

| Tier | Memoria | CPU |
|---|---|---|
| `small` | 256m | 0.25 |
| `default` | 512m | 0.5 |
| `medium` | 1g | 1.0 |
| `large` | 2g | 2.0 |
| `xlarge` | 4g | 4.0 |

Cada app declara en `maestro.yaml` valores dentro de rangos:
- `resources.memory`: entre `256m` y `4g`.
- `resources.cpu`: entre `0.25` y `4.0`.

El motor de provisioning aplica `--memory` y `--cpus` de Docker al levantar el contenedor.

### 7.2 Reglas

- Es **obligatorio** declarar ambos campos. Omitirlos es un error de validación.
- Si el consumo real excede sostenidamente el 90% durante >30 min, se dispara alerta.
- Si excede el 100% (`memory`): OOM Killer → contenedor reiniciado automáticamente; después de 3 OOMs en 5 min, se suspende la instancia.

---

## 8. Dockerfile — Reglas normativas para apps huésped

Toda app huésped debe cumplir:

```dockerfile
# Multi-stage obligatorio
FROM node:20-alpine AS build
WORKDIR /app
# ...

FROM node:20-alpine AS runtime
WORKDIR /app

# No-negociable 4: usuario no-root
RUN addgroup -g 1001 -S app && adduser -u 1001 -S app -G app
USER app

# Copy solo lo necesario
COPY --from=build --chown=app:app /app/dist ./dist
COPY --from=build --chown=app:app /app/node_modules ./node_modules
COPY --from=build --chown=app:app /app/package.json ./

EXPOSE 3000
# No-negociable 3: HEALTHCHECK
HEALTHCHECK --interval=30s --timeout=5s --retries=3 \
  CMD wget -q -O- http://localhost:3000/health || exit 1

CMD ["node", "dist/index.js"]
```

Reglas verificadas automáticamente por `maestro-cli validate`:
- ✅ `USER` directive presente y no-root (UID != 0).
- ✅ `HEALTHCHECK` instruction presente.
- ✅ `EXPOSE` con puerto que coincide con `maestro.yaml.requires.ports.app`.
- ❌ No `COPY .env*` (usa `.dockerignore`).
- ❌ No `--privileged` (se valida en el runner, no en el Dockerfile; pero el Maestro no lo permitiría).
- ❌ No `ENV <VAR>=<SECRETO>` hardcoded (gitleaks + trivy).

---

## 9. `maestro.yaml` — Contrato resumido

La especificación completa del contrato gateway se documenta en la fase 02-planning de cada proyecto generado por el framework agéntico (entregable `API_CONTRACTS.md`).

Ejemplo canónico:
```yaml
apiVersion: maestro.platform/v1
kind: Application
metadata:
  name: contabilidad
  version: 1.0.0
requires:
  database: postgres
  ports:
    app: 3000
health:
  endpoint: /health
  timeout_seconds: 5
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
hooks:
  on_user_added: /hooks/user-added
  on_user_removed: /hooks/user-removed
env:                   # variables custom de la app (opcionales)
  - FEATURE_FLAG_X
```

---

## 10. Logging

### 10.1 Formato obligatorio

Toda app huésped debe loguear a **stdout/stderr** (no a archivos). Formato:

```json
{
  "timestamp": "2026-04-16T14:23:01.234Z",
  "level": "info|warn|error|debug",
  "message": "string",
  "request_id": "req_01HY...",
  "company_id": "uuid (si aplica)",
  "user_id": "uuid (si aplica)",
  "app_slug": "<slug>",
  "additional_fields": {}
}
```

### 10.2 Prohibiciones

- **Nunca loguear** el contenido de headers `X-Auth-*`, tokens, passwords, `DATABASE_URL`, secrets.
- **Nunca loguear** bodies de requests completos sin redacción.
- Promtail + Loki recolectan y retienen 30 días.

---

## 11. Ciclo de vida de una app nueva (resumen de flujo para devs)

```
1. Dev clona repo template (`maestro-cli new <name>`).
2. Template incluye: Dockerfile compatible, maestro.yaml baseline, CLAUDE.md con reglas heredadas,
   workflow .github/workflows/deploy.yml, SDK @maestro/sdk-node preinstalado.
3. Dev desarrolla la app respetando las convenciones de este documento.
4. Dev hace push a su rama → CI ejecuta:
   - maestro-cli validate
   - tests + lint
   - trivy scan
   - build imagen Docker
5. Dev abre PR → review → merge a master.
6. Tag v<semver> → CI push de imagen a ghcr.io/<owner>/<app_slug>:<version>.
7. CI llama POST /api/v1/apps/register al Maestro.
8. Admin del Maestro licencia la app a una o más empresas via portal admin.
9. Admin provisiona instancia para (app, empresa).
10. Usuarios finales acceden al portal y la app aparece en su sidebar.
```

---

## 12. Dónde cambiar este documento

- Cualquier cambio en este doc requiere PR con label `convenciones` + aprobación del software-architect + code-reviewer transversal.
- Breaking changes (ej: cambio de nombre de header, cambio de prefijo reservado) requieren bump mayor del `apiVersion: maestro.platform/v1` → `v2` y un periodo de transición >=6 meses.
- Historial de cambios se mantiene en `CHANGELOG.md` del repo.

---

## 13. Referencias cruzadas

Estos artefactos son **generados por el framework agéntico** durante el ciclo de desarrollo. Ver:

- Fase 02 — Planning: `framework-agentico/phases/02-planning.md` define cómo se generan ARCHITECTURE, ADR_LOG, DATA_MODEL, API_CONTRACTS, UX_SPECS y THREAT_MODEL.
- Decisiones: cada proyecto registra sus ADRs en `framework-agentico/projects/{project-id}/branches/{rama}/phases/02-planning-adr.md`.
- Preset y reglas: `framework-agentico/agents/presets/maestro-platform/rules/RULES.md`
- Premisa vinculante: `PremisaWebMaestro/01-PREMISAS-Y-NO-NEGOCIABLES.md`
