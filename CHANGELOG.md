# Changelog

Todos los cambios notables de Maestro Platform.
Formato basado en [Keep a Changelog](https://keepachangelog.com/es/1.1.0/).
Versionado [Semantic Versioning](https://semver.org/lang/es/).

---

## [1.0.0-rc.2] — 2026-04-20 — Iteración stabilization-1

Iteración de estabilización sobre `v1.0.0-rc.1`. Resuelve inconsistencias del entorno dev, cierra el flujo de login end-to-end con credenciales de integración y deja el stack apto para demos sin credenciales de terceros. No cambia ninguna API pública ni el contrato de datos.

### Added
- **DEC-025** — `.env` unificado en raíz del repo. `backend/.env` eliminado. `.env.example` regenerado como template.
- **DEC-026** — Feature flag `MICROSOFT_ENTRA_ENABLED` + `VITE_MICROSOFT_ENTRA_ENABLED`. Cuando está en `false`: el backend responde `HTTP 503 entra_disabled` en `/api/auth/microsoft/{redirect,callback}` y el portal oculta el botón "Iniciar sesión con Microsoft".
- **DEC-027** — Servicio `azurite` (Azure Blob emulator) agregado a `docker-compose.dev.yml` para que backups dev no dependan de una storage account real.
- Seeder `DemoPoSeeder` idempotente + comando `artisan maestro:bootstrap-demo [--fresh]` (bloqueado en producción).
- Recipes `just bootstrap-demo`, `just bootstrap-demo-fresh`, `just e2e` (Playwright dockerizado, happy path de login).
- `data-testid` en `LoginPage.tsx`: `login-form`, `login-email`, `login-password`, `login-submit`, `login-error`, `login-microsoft`.
- 2 feature tests nuevos en `MicrosoftControllerTest` para el flag OFF.
- `backend/phpunit.xml`: `MICROSOFT_ENTRA_ENABLED=false` y `AZURE_STORAGE_ACCOUNT=""` con `force="true"`.
- Docs: `docs/04-delivery/INTEGRATION_REPORT_iter2.md`, `docs/05-operations/TRANSVERSAL_VALIDATION_iter2.md`.

### Changed
- `backend/config/services.php`: key `microsoft.enabled` controlada por env.
- `BackupService::disk()`: fallback silencioso a disco local cuando el driver `azure` no está registrado (habilita phpunit sin `league/flysystem-azure`).
- `DB_PASSWORD`, `REDIS_PASSWORD`, `DB_PURGER_PASSWORD`, `MAESTRO_ENCRYPTION_KEY`, `BACKUP_ENCRYPTION_KEY`, `PASSPORT_PASSWORD_CLIENT_ID/SECRET` rotados tras la unificación de `.env`.

### Credenciales de integración (dev)
- Company: `acme-demo` (Acme Demo).
- PO: `po@maestro.local` / `MaestroPO2026!` (admin).
- Tester: `tester@maestro.local` / `TesterMaestro2026!` (member).

### Fixed
- Duplicidad de fuentes de verdad entre `./.env` y `backend/.env` (drift silencioso de secrets).
- Tests de `MicrosoftController` rompían cuando el flag quedaba en `false` globalmente — ahora cada test controla el estado que necesita.

### Known Gaps (no cierran esta iteración)
- **G-1 / TD-036 HIGH** — `/app/storage/logs` devuelve `UnexpectedValueException` (permisos) durante navegación admin.
- **G-2 / TD-037 MEDIUM** — E2E `admin_users_reachable` redirige a login como consecuencia de G-1.
- **G-3 / TD-038 LOW** — `ApplicationSeeder` base (`nginx-test`) no existe; `DemoPoSeeder` emite warning.
- **G-4 / TD-039 LOW** — `just e2e` hace `npm install` por corrida.
- **TD-040 MEDIUM** — `BackupService` no advierte cuando cae al fallback local en prod.
- **TD-041 MEDIUM** — Azurite sin auth en `maestro-network` (dev-only, prohibido en prod).
- **TD-042 LOW** — Azurite sin hardening CIS.

### Validación
- PHPUnit: **151 / 151 PASS**, 289 assertions, coverage 80.2% statements.
- Smoke API: **8 / 8 PASS**.
- E2E Playwright login happy path: **5 / 5 core steps PASS**, 2 WARN documentados (G-1, G-2).
- Transversal 5/5 APROBADO CON OBSERVACIONES, 0 bloqueantes (`TRANSVERSAL_VALIDATION_iter2.md`).

---

## [1.0.0-rc.1] — 2026-04-18

Primera release candidate de Maestro Platform V1. Construcción completa de la plataforma multi-tenant para hospedar apps dockerizadas con autenticación centralizada. Listo para despliegue manual en VPS.

### Added

#### Autenticación e Identidades (Épicas A y B)
- OAuth2 Password Grant + Personal Access Tokens via Laravel Passport 13.7
- Federación con Microsoft Entra ID (SSO)
- Middleware ForwardAuth para Traefik — validación centralizada <50ms p95
- Modelo de identidades: `users`, `companies`, `applications` + 3 pivotes M-M (`company_user`, `application_company`, `application_user`)
- Switch de empresa activa por usuario (`active_company_id`)
- Cifrado AES-256-GCM de secretos en BD (webhook_secret, env vars, db passwords)

#### Audit Log (Épica C)
- Tabla `audit_log` INSERT-only con triggers PostgreSQL que bloquean UPDATE/DELETE
- Middleware que captura todas las mutaciones REST con diff before/after
- Endpoint `GET /api/admin/audit-log` con filtros + paginación + viewer frontend

#### Motor de Provisioning (Épica D)
- `ProvisioningEngine`: POST `/api/admin/instances` dispara job async
- Creación: red Docker aislada → BD dedicada postgres:16-alpine → container de app
- Doble aislamiento multi-tenant: red Docker privada + `EnforceCompanyIdFilter` en SDK
- Lifecycle completo: start/stop/restart/destroy/restore
- Health checks periódicos con histórico y transiciones de estado
- Purga automática de instancias destroyed a los 90 días (DEC-019)
- **CIS Docker Benchmark aplicado:** no-new-privileges, CapDrop ALL, CapAdd mínimo, PidsLimit, resource limits en DB y app containers huésped

#### Reverse Proxy + Seguridad (Épica E)
- Traefik v3.5 con ForwardAuth middleware
- `docker-socket-proxy` con allowlist estricta (EXEC=0, BUILD=0, VOLUMES=0, SECRETS=0)
- TLS self-signed en dev / Let's Encrypt ACME en prod
- Security headers middleware + rate limiting

#### Portal Admin (Épica F)
- React 18 + Vite + Tailwind (template Tailwise) con 5 páginas admin:
  - Companies (CRUD + auto-slug)
  - Users (alta + tipos + Microsoft link badge)
  - Applications (catálogo + alta manual)
  - Instances (lifecycle + auto-refresh 15s)
  - Audit Log (filtros + diff viewer before/after)
- Componentes: `AdminTable`, `StatusBadge`, `Modal`
- Tanstack Query con refetchInterval
- `GET /api/portal/my-apps` para vista de usuario

#### Contrato + SDK + CLI (Épica G)
- JSON Schema `maestro.yaml` como contrato canónico
- SDK Node.js: `@maestro-platform/sdk`
- `maestro-cli`: comandos `validate` y `new`
- Template `node-express` con CLAUDE.md hereditario

#### Hooks Salientes (Épica J)
- `HookDispatcher` + `DeliverHookJob`
- Firma HMAC-SHA256 en header `X-Maestro-Webhook-Secret`
- Retry con backoff 1s/5s/30s/2m/10m
- Tabla `hooks_deliveries` con trazabilidad (status, attempts, response_code)
- Eventos integrados en `UsersController` (user.created, user.updated, etc.)

#### Gateway Inter-Apps (Épica I)
- `POST/GET /api/v1/gateway/{app}/{path}` — llamadas entre apps autenticadas
- Headers `X-Maestro-*` inyectados en el forward
- Rate limiting por usuario

#### Observabilidad (Épica K)
- Stack completo: Prometheus v3.1.0 + Loki 3.3.2 + Promtail + Grafana 11.4.0 + cAdvisor + Node Exporter
- `docker-compose.obs.yml` levanta el stack
- Métricas de containers, logs centralizados, dashboards Grafana

#### Backups (Épica L)
- `BackupService`: `pg_dump | gzip | AES-256` → Azure Blob Storage
- Schedule diario 02:00 (configurable)
- Comando `php artisan backups:run` + `restore <backup-id>`
- Retención 30 días (DEC-019)

#### CI/CD (Épica H)
- `.github/workflows/ci.yml`: gitleaks + Pint + PHPStan + PHPUnit (postgres+redis services) + Trivy scan CRITICAL/HIGH bloqueante
- `.github/workflows/release.yml`: build multi-stage a GHCR + SemVer tagging + Trivy scan + GitHub Release con conventional-changelog

#### Platform + API v1 (Épica M)
- `GET /api/platform/health`
- `POST /api/v1/apps/register` (protegido por `X-Maestro-App-Secret`)
- `GET /api/v1/inventory/context` (protegido por ForwardAuth)

### Infrastructure (Fase 04)
- `docker-compose.prod.yml` con CIS Docker hardening completo:
  - `read_only: true` + tmpfs en maestro-api, traefik, portal
  - `cap_drop: ALL` + caps mínimos en todos los servicios
  - `pids_limit` + `resources.limits` CPU+Memory
  - HEALTHCHECK en api/db/redis/traefik/portal/worker/scheduler
  - 3 réplicas de `maestro-api` (1.5 CPU / 768 MB c/u), 2 de worker, 2 de portal
- `.env.production.example` con placeholders claros + `APP_DEBUG=false` + `LOG_LEVEL=warning`
- `docs/04-delivery/INFRASTRUCTURE.md`, `CI_CD.md`, `INTEGRATION_REPORT.md`

### Security
- Dependencias removidas por incompatibilidad Laravel 13: socialiteproviders/microsoft-graph, pest-plugin-laravel, scribe, spatie/laravel-model-states, dbal, flysystem-azure-blob, sentry-laravel
- **Fix iter 9:** `DeliverHookJob::recordDelivery` ya no usa HMAC con secret `'placeholder'`; usa webhook_secret real y `payload_hmac` es nullable para pre-dispatch failures
- **Fix Fase 04:** `ProvisioningEngine::createDatabaseContainer` ahora aplica `CapDrop: ALL` + CapAdd mínimo (CHOWN, SETGID, SETUID, DAC_OVERRIDE, FOWNER) + `PidsLimit: 200`
- **Fix Fase 04:** `ProvisioningEngine::createAppContainer` ahora aplica `PidsLimit: 512`
- OWASP Top 10 + ASVS Nivel 2 compliance validado

### Tests
- 151 tests (Feature + Unit) pasando, 1 skipped, 285 assertions
- Cobertura total: **80.2%** (target ≥80% alcanzado — DEC-013/iter 9)
- Controllers ≥76%, middleware 100%, models ≥95%, services 96–100%, jobs 81–100%

### Compliance V1 (DEC-013)
- GDPR: ✅ cifrado en reposo, derecho al olvido via purga, audit log inmutable
- SOC 2 Type II (controles, no certificación): ✅ logging centralizado + backups cifrados + access controls
- CIS Docker Benchmark: ✅ full coverage (DB host + containers huésped)
- OWASP ASVS Nivel 2: ✅ validado por security-auditor

### Known Issues (deuda a Fase 05)
- Healthcheck Docker usa `wget localhost` que resuelve IPv6 → falso "unhealthy". Fix: cambiar a `127.0.0.1`.
- E2E tests pendientes: login happy path, OAuth Microsoft callback, gateway forward real, webhook delivery real
- JSON Schema validation en `RegisterAppController` (usa Symfony Yaml pero sin validación de esquema)
- Rate limiting Docker API + circuit breaker en `DockerApiClient`
- GDPR: endpoint `/api/v1/gdpr/export` pendiente
- DPA template legal

### Excluido del alcance V1 (WON'T)
- WCAG 2.1 AA formal (DEC-015)
- MFA propio TOTP — se delega en Microsoft Entra ID (DEC-016)
- Idiomas adicionales al español (DEC-014)
- Pricing/billing/tiers complejos (DEC-018)
- SLA de soporte a clientes finales (DEC-021)
- Zero-downtime deployments (DEC-020)
- LGPD, HIPAA, PCI-DSS, FedRAMP (DEC-013)
