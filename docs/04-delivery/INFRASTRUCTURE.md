# INFRASTRUCTURE.md — Maestro Platform V1

> **Fase:** 04-delivery
> **Versión:** 1.0.0-rc.1
> **Fecha:** 2026-04-18
> **Ámbito:** V1 (1 empresa × 7 apps huésped — DEC-017)

---

## 1. Topología

```
Internet → Traefik (80/443) → ForwardAuth (maestro-api) ↘
                                                         ├→ maestro-api (x2 replicas)
                                                         ├→ maestro-portal (x2)
                                                         ├→ obs-grafana
                                                         └→ apps huésped (N instancias)

                           maestro-network (bridge)
                             │
     maestro-db ── maestro-redis ── maestro-docker-proxy ── maestro-worker ── maestro-scheduler
                                             │
                                             └─ dockerd (socket via proxy, allowlist estricta)
```

Redes aisladas por instancia huésped: cada `apps/register` crea `maestro-instance-<slug>` con solo su app + su DB — doble aislamiento: red Docker + middleware `EnforceCompanyIdFilter` en SDK.

## 2. Imágenes

| Componente | Imagen | Build |
|---|---|---|
| Backend API + Worker + Scheduler | `ghcr.io/llyasoc-digital/web-maestro-.../-api:<tag>` | `docker/php/Dockerfile` (multi-stage `base`→`dev`→`prod`) |
| Portal React | `ghcr.io/llyasoc-digital/web-maestro-.../-portal:<tag>` | `docker/portal/Dockerfile` (multi-stage node build → nginx:alpine) |
| DB | `postgres:16-alpine` | oficial |
| Redis | `redis:7-alpine` | oficial |
| Traefik | `traefik:v3.5` | oficial |
| Docker proxy | `ghcr.io/tecnativa/docker-socket-proxy:latest` | oficial |
| Observabilidad | `prom/prometheus:v3.1.0`, `grafana/loki:3.3.2`, `grafana/grafana:11.4.0`, `gcr.io/cadvisor/cadvisor:v0.51.0` | oficial |

### Convenciones de build

- Multi-stage obligatorio (RULES fase 04)
- Non-root (UID/GID 1000) en todos los stages `prod`
- `HEALTHCHECK` definido (`/api/platform/health` para api, `/` para portal)
- `.dockerignore` excluye `.env*`, secretos, `node_modules`, `vendor`, `docs/`, `framework-agentico/`, `Tailwise Bundle/`
- Etiquetado: SemVer (`v1.0.0`, `v1.0`, `sha-<git>`) via `docker/metadata-action@v5`

## 3. Ambientes

### Local / dev
- Archivo: `docker-compose.dev.yml` + `docker-compose.obs.yml`
- Build local con `target: dev` (xdebug activo, bind mounts `backend/`, `portal/`)
- TLS self-signed
- Levantar: `just up && just composer-install && just npm-install && just migrate && just seed`

### Producción (VPS Azure — operado por humano fuera del framework — DEC-011)
- Archivo: `docker-compose.prod.yml` + `docker-compose.obs.yml`
- `.env.production` (copiar de `.env.production.example`)
- Imágenes pre-buildadas desde GHCR (tag SemVer explícito, nunca `latest`)
- TLS Let's Encrypt (Traefik ACME) → mail `TRAEFIK_ACME_EMAIL`
- 2 réplicas para api y portal; 2 worker; 1 scheduler
- Secretos rotables por `docker secret rotate` / rebuild y `docker compose up -d --force-recreate <svc>`

## 4. CIS Docker Benchmark — estado V1

| Control | DB maestro | DB huésped | API | Portal | Traefik | Docker proxy | Estado |
|---|---|---|---|---|---|---|---|
| 1 `no-new-privileges` | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ | OK |
| 2 `CapDrop: ALL` | ✅ prod | ✅ (fix iter 9/F04) | ✅ | ✅ | ✅ | ✅ | OK |
| 3 `CapAdd` mínimo | CHOWN/SETGID/SETUID/DAC/FOWNER | idem | NET_BIND_SERVICE | NET_BIND_SERVICE | NET_BIND_SERVICE | — | OK |
| 4 `ReadonlyRootfs` | N/A (datos en volumen) | N/A | N/A (storage vol) | ✅ + tmpfs | ✅ + tmpfs | ✅ + tmpfs | OK (justificado) |
| 5 `pids_limit` | 200 | 200 | 512 | 200 | 200 | 100 | OK |
| 6 `resources` limits | 2 CPU / 2 GB | 0.5 CPU / 512 MB | 2 CPU / 1 GB | 0.5 CPU / 256 MB | 1 CPU / 512 MB | 0.5 CPU / 128 MB | OK |
| 7 Non-root user | postgres | postgres | app (1000) | nginx (101) | root traefik-bin | n/a | OK |
| 8 HEALTHCHECK | ✅ pg_isready | (via scheduler health check) | ✅ wget /health | ✅ wget / | ✅ traefik ping | — | OK |
| 9 No Docker socket directo | ✅ vía proxy | ✅ vía proxy | ✅ vía proxy | ✅ | ✅ prod | ✅ socket:ro | OK |
| 10 Secrets fuera de env | .env.production / Docker Secrets | Env solo (BD huésped) | .env.production | n/a | n/a | n/a | Parcial — plan rotación fase 05 |

## 5. Secretos

Secretos críticos V1:

- `APP_KEY` (Laravel encryption)
- `MAESTRO_ENCRYPTION_KEY` (AES-256-GCM — webhook_secret, db_password, env_vars de instancias)
- `BACKUP_ENCRYPTION_KEY` (AES-256 pg_dump backups)
- `DB_PASSWORD`, `DB_PURGER_PASSWORD`, `REDIS_PASSWORD`
- `PASSPORT_PASSWORD_CLIENT_SECRET`
- `MICROSOFT_ENTRA_CLIENT_SECRET`
- `AZURE_STORAGE_KEY`
- `GRAFANA_ADMIN_PASSWORD`

Rotación: manual vía `docker compose up -d --force-recreate maestro-api maestro-worker` tras cambiar `.env.production`. El humano documenta cada rotación en changelog interno del VPS.

## 6. Gateway inter-apps (Épica I)

- Endpoint: `POST /api/v1/gateway/{appSlug}/<path>` en maestro-api
- Requiere JWT válido (ForwardAuth)
- Rate limit: `RATE_LIMIT_DEFAULT_PER_MIN` (60 req/min/usuario en prod)
- Forward con headers `X-Maestro-*` inyectados

### Fixes aplicados tras validación transversal Fase 04

- **maestro-api:** `read_only: true` + tmpfs (`/tmp`, `/var/cache/nginx`, `/var/run`, `/var/log/nginx`, `/var/log/supervisor`) — CIS 5.10
- **maestro-api:** 3 réplicas x (1.5 CPU / 768 MB) = 4.5 CPU / 2.3 GB total — cabe holgadamente en SLA 50 concurrentes con buffer (performance-analyst)
- **maestro-worker:** HEALTHCHECK vía `queue:monitor`
- **maestro-scheduler:** HEALTHCHECK vía `pgrep artisan schedule:work`

## 7. Gap cerrado en Fase 04

- **CIS Docker DB huésped:** `ProvisioningEngine::createDatabaseContainer` ahora aplica `CapDrop: ALL` + `CapAdd` mínimo (CHOWN/SETGID/SETUID/DAC_OVERRIDE/FOWNER) + `PidsLimit: 200`. **Evidencia:** `backend/app/Modules/Provisioning/Services/ProvisioningEngine.php:168-181`.
- **PidsLimit en app huésped:** agregado 512 (defensa fork-bomb). Evidencia: misma clase, método `createAppContainer`, HostConfig.
- **docker-compose.prod.yml:** generado con los controles CIS completos y recursos acotados.
- **.env.production.example:** plantilla con APP_DEBUG=false, LOG_LEVEL=warning, rate limiting estricto, `RATE_LIMIT_DOCKER_API_PER_MIN=30` (deuda Docker API circuit-breaker parcialmente cubierta vía rate-limit; lógica de circuit-breaker propiamente dicha se traslada a Fase 05).

## 8. Gaps que quedan para Fase 05 Operations

- Circuit breaker en `DockerApiClient` (fuera de alcance V1 según OBS fase 03)
- `GDPR /api/v1/gdpr/export` endpoint (Fase 05)
- DPA template legal (humano)
- E2E suite (login happy path, OAuth MS callback, gateway forward real, webhook delivery real) — Fase 05
- JSON Schema validation en `RegisterAppController` — Fase 05
- Logging de `DecryptionException` — Fase 05
- Rotación automática de `MAESTRO_ENCRYPTION_KEY` — post-V1
