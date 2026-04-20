# Arquitectura del Sistema — Maestro Platform V1

> **Fase:** 02-Planning
> **Agente:** software-architect
> **Fecha:** 2026-04-16
> **Proyecto:** PRJ-MAESTRO-V1
> **Preset:** maestro-platform

---

## 1. Visión General

Maestro Platform V1 es un **monolito modular Laravel** que expone un **portal React** sobre un **reverse proxy Traefik** con **ForwardAuth**, y actúa como **Identity Provider** (OAuth2 + JWT + Microsoft Entra ID) y **motor de orquestación Docker** para aplicaciones huésped dockerizadas, con aislamiento de red por instancia y BD dedicada por instancia.

La plataforma corre **100% dockerizada** (DEC-012): ningún runtime se instala en el host del dev. Todo el desarrollo se hace vía `docker compose run --rm <servicio>`.

El despliegue productivo al VPS Azure se gestiona fuera del framework (DEC-011); los artefactos de deploy sí se producen dentro del proyecto.

---

## 2. Stack Tecnológico

| Capa | Tecnología | Versión | Rationale |
|---|---|---|---|
| Lenguaje backend | PHP | 8.3+ | Laravel 13 requiere PHP ^8.3 (DEC-023); imagen Docker `php:8.3-fpm-alpine` |
| Framework backend | Laravel | 13.x (latest stable) | DEC-023; premisa dice "Laravel" sin fijar major, se elige la última estable (13.5.0 al 2026-04-14) |
| OAuth2 server | Laravel Passport | 13.x (compat con Laravel 11/12/13) | ADR-001; emite JWT, maneja refresh tokens |
| SSO externo | Microsoft Entra ID via Laravel Socialite | 5.x + socialite-providers/microsoft-graph | Premisa lo exige |
| BD del Maestro | PostgreSQL | 16 | ADR-002; robusto para multi-tenant, tipos JSON nativos, triggers maduros |
| Cache / broker | Redis | 7.x | ADR-005; validación de tokens, rate limiting, queues |
| ORM | Eloquent | (incluido Laravel) | Default de Laravel |
| Queue | Laravel Queue + Redis driver | (incluido) | Jobs de health check, provisioning async, hooks |
| Framework frontend | React | 18 | Inmutable por premisa; base Tailwise React v1.0.9 |
| Estilos frontend | Tailwind CSS | 3 | Base Tailwise; no custom CSS nuevo |
| Bundler frontend | Vite | 5 | Viene con Tailwise |
| Tipado frontend | TypeScript | 5 | Recomendado para SDK y portal |
| Reverse proxy | Traefik | v3 | ADR-004; ForwardAuth nativo, ACME Let's Encrypt |
| Containers | Docker | 29+ | ya instalado |
| Orchestración | Docker Compose | v2.5+ | multi-contenedor local; prod usa mismo compose |
| Docker API access | docker-socket-proxy | Linuxserver/socket-proxy | ADR-006; superficie de ataque mínima |
| CI/CD | GitHub Actions | - | ADR-009 |
| Test backend | PHPUnit | 11 | default Laravel |
| Test frontend | Vitest + React Testing Library | - | rápido, moderno |
| Test E2E | Playwright | latest | flujos login + portal + iframe |
| Scan de secretos | gitleaks + trivy | latest | RNF-013, RNF-019 |
| Observabilidad | Prometheus + cAdvisor + Loki + Promtail + Grafana | latest estable | Fase 5 según premisa |
| Backups | pg_dump + age (cifrado) + Azure Blob | - | RF-110, RNF-012 |
| SDK primer lenguaje | Node.js + Express middleware | 20 LTS | DEC-010 |
| CLI | maestro-cli en Node.js | 20 LTS | RF-061 |
| i18n | **ninguna librería** (DEC-014: solo español) | - | Strings hardcoded en es-AR |

### 2.1 Estructura de imágenes Docker de desarrollo

| Imagen | Uso |
|---|---|
| `php:8.3-fpm-alpine` → build custom `maestro-php` | Maestro backend |
| `node:20-alpine` → build custom `maestro-node` | Portal frontend + SDK + CLI |
| `postgres:16-alpine` | BD del Maestro y de cada instancia |
| `redis:7-alpine` | cache y queue |
| `traefik:v3` | reverse proxy |
| `tecnativa/docker-socket-proxy` | proxy restrictivo del docker socket |
| `grafana/grafana`, `prom/prometheus`, etc. | observabilidad |

---

## 3. Patrón Arquitectónico

**Elección: Monolito Modular (Clean Architecture + DDD light)** — ADR-003.

Organización del backend en módulos con frontera clara:

```
app/
├── Modules/
│   ├── Auth/             # Passport, Microsoft Entra, JWT, ForwardAuth endpoint
│   ├── Identity/         # users, companies, pivotes M-N, roles, permisos
│   ├── Catalog/          # applications + licenses (application_company, application_user)
│   ├── Provisioning/     # motor Docker API: instancias, redes, BDs, lifecycle
│   ├── Gateway/          # API gateway inter-apps del mismo tenant
│   ├── Hooks/            # webhooks salientes firmados HMAC
│   ├── AuditLog/         # registro inmutable (INSERT only + triggers)
│   └── Platform/         # endpoints meta (/api/inventory/context, /api/apps/register)
├── Http/
│   ├── Controllers/      # thin controllers → delegan a módulos
│   ├── Middleware/       # global (CORS, throttle, audit)
│   └── Resources/        # API Resources para serializar
├── Console/              # comandos artisan (provisioning manual, migraciones custom)
└── Providers/            # Laravel service providers

database/
├── migrations/           # numeradas, reversibles, con up()/down()
├── seeders/              # semilla mínima (admin inicial)
└── factories/            # para tests

routes/
├── api.php               # /api/*
├── auth.php              # /api/auth/* (separado para claridad)
└── hooks.php             # no hay hooks entrantes; el Maestro dispara salientes desde Jobs

tests/
├── Feature/              # tests por módulo, con HTTP simulado
├── Integration/          # tests que pegan a BD real y Redis real
└── Unit/                 # tests aislados
```

Justificación:
- Escala V1 (DEC-017) no justifica microservicios.
- Módulos con fronteras claras permiten extraer servicios en V2 sin refactor traumático.
- Thin controllers + lógica en módulos facilita testing (RNF tests cobertura 80%/70%).

### 3.1 Frontend

- **SPA React** con shell pattern.
- **Iframe-based app loader**: cada app huésped se muestra dentro de un `<iframe>` del portal.
- **postMessage protocol** para transferir el token al iframe y recibir eventos (ej: cambio de ruta dentro de la app).
- **Router**: React Router 6.
- **State management**: Context API + Zustand (nada más pesado se justifica a V1).
- **Fetching**: Tanstack Query (react-query) sobre fetch nativo.

---

## 4. Diagrama de Componentes (C4 Nivel 2)

```mermaid
flowchart TB
    User[👤 Usuario final / Admin]
    DevApp[👤 Dev app huésped<br/>via maestro-cli]
    Entra[Microsoft Entra ID]
    AzureBlob[Azure Blob Storage<br/>backups cifrados]

    subgraph VPS[VPS / Entorno local Docker]
        subgraph maestroNet[Red Docker: maestro-network]
            Traefik[Traefik v3<br/>- TLS Let's Encrypt<br/>- ForwardAuth<br/>- Rate limit<br/>- HSTS]
            Portal[Portal React<br/>Nginx static]
            Maestro[Maestro Laravel<br/>Modules: Auth/Identity/<br/>Catalog/Provisioning/<br/>Gateway/Hooks/AuditLog]
            MaestroDB[(PostgreSQL 16<br/>maestro_db)]
            Redis[(Redis 7<br/>cache + queue)]
            DockerProxy[docker-socket-proxy<br/>acceso restringido a API Docker]
            Observ[Observabilidad<br/>Prometheus + Loki + Grafana]
        end

        subgraph Inst1[Red: app-{slug}-{company}-net]
            App1[Contenedor app 1]
            App1DB[(postgres<br/>dedicada)]
        end

        subgraph InstN[Red: app-{slug}-{company}-net]
            AppN[Contenedor app N]
            AppNDB[(postgres<br/>dedicada)]
        end

        DockerSocket[/var/run/docker.sock]
    end

    User -->|HTTPS 443| Traefik
    Traefik -->|valida token| Maestro
    Traefik -->|reenvia con X-Auth-*| Portal
    Traefik -->|reenvia con X-Auth-*| App1
    Traefik -->|reenvia con X-Auth-*| AppN
    Portal -->|fetch API| Maestro
    Maestro --> MaestroDB
    Maestro --> Redis
    Maestro -->|Docker API<br/>via proxy| DockerProxy
    DockerProxy -->|readonly endpoints| DockerSocket
    Maestro -->|hooks HMAC| App1
    Maestro -->|hooks HMAC| AppN
    App1 --> App1DB
    AppN --> AppNDB
    DevApp -->|POST /api/apps/register| Maestro
    Entra -.OAuth2.-> Maestro
    Maestro -.nightly backup.-> AzureBlob
    Observ -.scrape metrics.-> Maestro
    Observ -.scrape cAdvisor.-> App1
    Observ -.scrape cAdvisor.-> AppN
```

### 4.1 Flujo request típico (usuario final accede a app huésped)

```
1. Browser → https://app1-tenant.maestro.local/ruta
2. Traefik recibe, verifica TLS, mira labels y encuentra la instancia.
3. Traefik → ForwardAuth middleware → GET https://maestro.local/api/auth/validate con cookie/token.
4. Maestro-Auth valida JWT (primero consulta Redis, fallback a BD).
5. Si OK: Maestro retorna 200 + headers X-Auth-User-Id, X-Auth-User-Email, X-Auth-Company-Id, X-Auth-Roles, X-Auth-Permissions.
6. Traefik adjunta esos headers al request original y lo reenvía al contenedor de la app huésped.
7. La app huésped lee los headers, procesa y responde.
8. Traefik retorna al browser.
```

### 4.2 Flujo provisioning de una nueva instancia

```
1. Admin → POST /api/admin/instances con {application_id, company_id}.
2. Maestro-Provisioning despacha Job async.
3. Job crea red Docker dedicada: `app-{appSlug}-{companySlug}-net`.
4. Job crea contenedor Postgres dedicado en la red privada, con user/pass random 32+ chars (AES-256 at-rest).
5. Job crea contenedor de la app en la red privada + conectado a maestro-network para recibir Traefik.
6. Job inyecta env vars (DATABASE_URL, MAESTRO_APP_SECRET, etc.) — nunca persistidas en disco.
7. Job aplica labels Traefik para ruteo por subdominio.
8. Job entra en loop de health check hasta que responde 200 en /health (o timeout → rollback).
9. Job actualiza instance.status = 'healthy' y emite audit_log entry.
10. Si hooks configurados: dispatch de on_user_added para los users que tienen acceso (Hooks module).
```

---

## 5. Estrategia de Error Handling

- **Errores HTTP estándar**: formato consistente `{ "error": { "code": "string", "message": "string", "details": {} } }` — ADR-008.
- **Códigos de error HTTP**:
  - 400 bad request (validación)
  - 401 unauthenticated (token inválido/expirado)
  - 403 forbidden (permisos insuficientes)
  - 404 not found
  - 409 conflict (estado inconsistente, ej: crear instancia duplicada)
  - 422 unprocessable (validación semántica)
  - 429 rate limit
  - 500 internal (log en Sentry o equivalente + alerta)
  - 503 service unavailable (BD/Redis caídos)
- **Retry en Jobs async**: exponential backoff 1s, 5s, 30s, 2m, 10m (máx 5 intentos); tras agotar → DLQ lógico (tabla `failed_jobs` de Laravel + alerta).
- **Circuit breaker**: hacia Docker API (si falla >3 veces en 30s, pausa provisioning por 2 min y alerta).
- **Graceful degradation**: si Redis cae, validación de tokens sigue funcionando contra BD (más lento pero OK).
- **Healthchecks externos al Maestro mismo**: `/api/platform/health` sin auth, retorna 200 si BD + Redis + docker proxy responden.

---

## 6. Estrategia de Branching (ADR-013)

- **Trunk-based con feature branches cortas** (<3 días de vida).
- Rama principal: `master` (protegida; PR + 1 review obligatorio + CI green).
- Branches: `feat/<slug>`, `fix/<slug>`, `chore/<slug>`, `docs/<slug>`.
- **Conventional Commits** obligatorio para commits en `master`. Hook local con commitlint.
- Tags de release: `v<SEMVER>` (ej: `v1.0.0`) en commits de `master` tras PR de release.
- **No se permite** force-push a `master`.

---

## 7. Estrategia de Ambientes

| Ambiente | Dónde corre | Datos | Quién opera |
|---|---|---|---|
| `local` | docker-compose.dev.yml en la máquina del dev | BD con seeders, TLS self-signed o sin TLS (dominio `.maestro.local`) | Dev/Claude (zero local installs) |
| `staging` | VPS Azure, docker-compose.staging.yml | Datos sintéticos, TLS Let's Encrypt | Humano (DEC-011) |
| `production` | VPS Azure, docker-compose.prod.yml | Datos reales del tenant inicial | Humano (DEC-011) |

Paridad **100%** entre compose files (las 3 corren la misma imagen del Maestro); difieren solo en env vars, réplicas de workers y TLS.

El framework **no despliega** a staging ni production (DEC-011). Entrega el artefacto Docker + compose + scripts shell que el humano ejecuta en el VPS.

---

## 8. Internacionalización

**WON'T HAVE V1** (DEC-014). Solo español argentino (`es-AR`). Strings hardcoded en componentes y mensajes de error. No se usa `lang` files de Laravel ni `i18next` en React.

Post-V1, si se suma inglés u otro idioma, la migración a `@php app()->getLocale()` y `i18next` en frontend es mecánica.

---

## 9. Variables de Entorno

### 9.1 Maestro backend (`.env` gitignored, `.env.example` versionado)

**Obligatorias**:
```
APP_NAME=Maestro
APP_ENV=local|staging|production
APP_KEY=base64:...          # laravel artisan key:generate
APP_DEBUG=false             # en staging/prod
APP_URL=https://maestro.local
DB_CONNECTION=pgsql
DB_HOST=maestro-db
DB_PORT=5432
DB_DATABASE=maestro
DB_USERNAME=maestro
DB_PASSWORD=<random 32+>
REDIS_HOST=maestro-redis
REDIS_PASSWORD=<random>
REDIS_PORT=6379
PASSPORT_PRIVATE_KEY_PATH=/secrets/oauth-private.key
PASSPORT_PUBLIC_KEY_PATH=/secrets/oauth-public.key
MAESTRO_ENCRYPTION_KEY=<AES-256 key base64>   # cifrado de secretos de instancias
MICROSOFT_ENTRA_CLIENT_ID=<uuid>
MICROSOFT_ENTRA_CLIENT_SECRET=<secret>
MICROSOFT_ENTRA_TENANT_ID=<uuid>
MICROSOFT_ENTRA_REDIRECT_URI=https://maestro.local/api/auth/microsoft/callback
DOCKER_PROXY_URL=tcp://docker-proxy:2375
MAESTRO_BASE_DOMAIN=maestro.local        # para construir subdominios de apps
```

**Opcionales**:
```
SENTRY_DSN=
LOG_CHANNEL=stack|stderr
AZURE_STORAGE_ACCOUNT=
AZURE_STORAGE_KEY=
AZURE_STORAGE_CONTAINER=maestro-backups
BACKUP_SCHEDULE="0 2 * * *"              # cron
JWT_TTL_MINUTES=60                       # default 1h
REFRESH_TOKEN_TTL_DAYS=30
TOKEN_CACHE_TTL_SECONDS=300              # cache de validación en Redis
```

### 9.2 Portal React

Variables prefijadas `VITE_`:
```
VITE_API_BASE_URL=https://maestro.local/api
VITE_APP_TITLE=Maestro
VITE_MICROSOFT_LOGIN_URL=https://maestro.local/api/auth/microsoft/redirect
```

### 9.3 Gestión de Secretos

- **Local**: `.env` en raíz (gitignored) + `.env.example` versionado como plantilla.
- **Staging/Prod**: Docker secrets inyectados por el humano al desplegar (no archivos `.env` en VPS).
- **Secretos de instancias** (DB passwords por instancia): cifrados AES-256 en `instances.db_password_encrypted`. Se descifran solo al momento de inyectar env vars al contenedor de la app.
- **Claves OAuth2 (Passport)**: generadas con `php artisan passport:keys`, montadas como Docker secret en `/secrets/oauth-*.key`, nunca committeadas.

---

## 10. Integración con Plataforma (preset maestro-platform)

Este proyecto **ES** el Maestro. No consume el preset, lo **produce**:

- **Emite** los headers `X-Auth-User-Id`, `X-Auth-User-Email`, `X-Auth-Company-Id`, `X-Auth-Roles`, `X-Auth-Permissions` desde `/api/auth/validate`.
- **Define y publica** el JSON Schema de `maestro.yaml` (fuente de verdad en `docs/02-planning/schema/maestro.yaml.schema.json`).
- **Emite** el SDK `@maestro/sdk-node` (repo separado o subpath; decisión en Fase 03).
- **Valida** los maestro.yaml de apps huésped cuando éstas se registran (POST /api/apps/register) y en CI/CD de las apps.
- **Provisiona** las instancias respetando los límites declarados en `maestro.yaml` (memory, cpu).
- **Impone** el contrato: apps que no lo cumplen no se registran ni se provisionan.

Las convenciones de coexistencia (naming, puertos, redes, volúmenes, subdominios, env vars) viven en `docs/CONVENCIONES_PLATAFORMA.md` — deliverable obligatorio DEL-001, también producido en esta fase.

---

## 11. Dimensionamiento V1

Dada la escala DEC-017 (1 empresa × 7 apps × 50 usuarios concurrentes):

| Componente | Recursos V1 |
|---|---|
| Maestro backend (php-fpm) | 1 contenedor, 1 CPU, 512 MB RAM |
| Maestro workers (queue) | 2 contenedores, 0.5 CPU cada, 256 MB RAM |
| Portal (nginx static) | 1 contenedor, 0.25 CPU, 128 MB RAM |
| PostgreSQL Maestro | 1 contenedor, 1 CPU, 1 GB RAM |
| Redis | 1 contenedor, 0.25 CPU, 256 MB RAM |
| Traefik | 1 contenedor, 0.5 CPU, 256 MB RAM |
| Docker socket proxy | 1 contenedor, 0.1 CPU, 64 MB RAM |
| Por instancia huésped (default tier) | según `maestro.yaml` — rango 0.25-1 CPU, 128MB-1GB RAM |
| Observabilidad stack | ~1.5 CPU total, ~1.5 GB RAM total |

**Total mínimo Maestro + stack (sin apps huésped)**: ~5 CPU, ~4 GB RAM.
**Con 7 apps promedio**: ~10 CPU, ~8 GB RAM.
**VPS recomendado V1**: 8 vCPU / 16 GB RAM / 200 GB SSD. Cualquier tier B-Series o D-Series de Azure encaja.

---

## 12. Riesgos arquitectónicos y mitigaciones

| Riesgo (del RESEARCH_FINDINGS) | Mitigación en arquitectura |
|---|---|
| R-001 Leak entre tenants | Doble barrera: (a) red Docker aislada por instancia, (b) middleware de filtrado por company_id en Maestro + SDK. Tests de integración específicos que intenten crossing. |
| R-002 Compromiso del Maestro → Docker | docker-socket-proxy con allowlist de endpoints (solo containers, networks, exec, logs; bloquea build, system, volumes.delete, swarm). ADR-006. |
| R-003 Latencia ForwardAuth | Redis cache desde V1 (ADR-005). Fallback a BD si Redis cae (graceful degradation). |
| R-004 Cold start >15s | V1 **no duerme instancias por defecto**. Se evalúa post-V1 con métricas reales. |
| R-005 Passport config compleja | ADR-001 con prototipo temprano en Fase 03; OWASP ASVS L2 como checklist. |
| R-006 TLS no renueva | Alerta a los 30 días antes de expiración (observability), runbook de renovación manual. |
| R-008 Capacidad VPS | Dimensionamiento §11 con holgura; pruebas de carga en Fase 04 antes de release. |
| R-009 Single-node no escala | Deuda técnica documentada. BD y estados diseñados multi-node-ready (UUIDs, sin assumptions de memoria compartida). Extracción a K8s post-V1 factible. |

---

## 13. Convenciones de desarrollo

- **PSR-12** para PHP.
- **ESLint + Prettier** para TypeScript/React (config en repo).
- **Nombres**: archivos kebab-case; clases PascalCase; variables/funciones camelCase; constantes SCREAMING_SNAKE_CASE.
- **Tests**: `Feature/ModuleNameTest.php` / `Integration/ModuleNameTest.php`; frontend `Component.test.tsx`.
- **Commits**: Conventional Commits (`feat:`, `fix:`, `refactor:`, `test:`, `docs:`, `chore:`, `perf:`, `ci:`). Scope opcional (`feat(auth): ...`).
- **Documentación de código**: solo cuando el _why_ no es obvio del _what_; no narrar lo que el código ya dice.
- **Pull requests**: plantilla con secciones: Summary, Motivation, Changes, Tests, Screenshots (si UI), Linked Requirements (RF-XXX / RNF-XXX).

---

## 14. Referencias cruzadas

- Decisiones registradas: `framework-agentico/agents/CHECKPOINT_GLOBAL.md` → decisions_log (DEC-001 a DEC-022).
- Requisitos: `docs/01-discovery/REQUIREMENTS.md` (125 ítems).
- Premisa vinculante: `PremisaWebMaestro/01-PREMISAS-Y-NO-NEGOCIABLES.md` (10 no-negociables).
- ADRs detallados: `docs/02-planning/ADR_LOG.md`.
- Modelo de datos: `docs/02-planning/DATA_MODEL.md`.
- API: `docs/02-planning/API_CONTRACTS.md`.
- UX: `docs/02-planning/UX_SPECS.md`.
- Threat model: `docs/02-planning/THREAT_MODEL.md`.
- Convenciones de coexistencia: `docs/CONVENCIONES_PLATAFORMA.md` (DEL-001).
