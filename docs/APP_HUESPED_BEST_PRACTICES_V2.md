# Mejores Prácticas para Aplicaciones Huésped v2 — Maestro Platform v2

> **Documento orientativo.** Acompaña a `docs/APP_HUESPED_SPEC_V2.md` (normativo).
>
> **Versión:** 2.0.0
> **Framework agéntico:** v4
> **Última revisión:** 2026-05-06.
> **Reemplaza a:** `docs/APP_HUESPED_BEST_PRACTICES.md` v1.
> **Stack agnóstico:** ejemplos en Node/Laravel/Python son ilustrativos; cualquier stack es válido.

---

## 1. Filosofía base

> *Takeaway:* combiná **12-factor**, **single-tenant-by-default**, **auth-propia-segura** y **zero-trust**.

### 1.1 The Twelve Factors aplicados a Maestro v2

| Factor | Implicación en Maestro v2 |
|---|---|
| 1. Codebase | Un repositorio por app, **un deploy por empresa** (single-tenant fisico). |
| 2. Dependencies | Lock files commiteados (`package-lock.json`, `composer.lock`, `go.sum`, etc.). |
| 3. Config | Solo via ENV vars. Nada en código ni en imagen. |
| 4. Backing services | BD adjunta via `DATABASE_URL`. |
| 5. Build, release, run | Build = imagen; release = imagen + config; run = contenedor. |
| 6. Processes | Apps stateless. Estado en BD; archivos a blob storage. |
| 7. Port binding | App escucha en `requires.ports.app`. |
| 8. Concurrency | Escalar verticalmente bumpeando tier. |
| 9. Disposability | Arranque ≤ 60 s, shutdown limpio en SIGTERM ≤ 30 s. |
| 10. Dev/prod parity | `docker-compose.dev.yml` reproduce el entorno. |
| 11. Logs | JSON a stdout con `user_id` y `request_id`. |
| 12. Admin processes | Comandos via `docker exec` o jobs efímeros. |

### 1.2 Single-tenant-by-default (cambio respecto a v1)

- **Cada contenedor sirve a UNA empresa.** No hay `company_id` en el modelo de datos.
- La empresa esta implicita por contenedor; sus datos de branding (nombre, logos) se exponen via `/maestro/branding`.
- Esto **simplifica el modelo de datos**: no hay scopes globales por tenant, no hay risk de leak cross-tenant a nivel de aplicación (el aislamiento es fisico, a nivel de contenedor).
- Si en el futuro se necesita multi-tenancy, se hace por **un contenedor por empresa**, no por filtrado en queries.

### 1.3 Auth-propia segura

- La app es **un Identity Provider para sus usuarios** (no un consumidor pasivo de identidad como en v1).
- Aplican OWASP ASVS 4.0 y NIST SP 800-63B (Digital Identity Guidelines).
- Implementación recomendada: librerías maduras del stack (Laravel Sanctum, NextAuth, Passport.js, Django auth, Spring Security). NO escribir auth desde cero.

### 1.4 Zero trust en el borde y en el interior

- El Maestro v2 NO valida identidad de usuario por la app (cada app lo hace).
- Pero sí autentica las **llamadas server-to-server** (consumo de `/maestro/branding`, hooks): siempre con HMAC o api keys.
- Internamente: cada app es independiente. No hay comunicación inter-apps directa salvo via gateway autenticado del Maestro v2.

---

## 2. Auth propia: prácticas recomendadas

### 2.1 Password storage

- **bcrypt cost ≥ 12** o **argon2id** (memory ≥ 32 MB, iterations ≥ 3, parallelism ≥ 1).
- Nunca SHA1/SHA256 directo.
- **Pepper** (secret adicional al hash) en ENV var separada — opcional pero recomendado.
- Rotación de hash: si se cambia el cost, re-hashear silenciosamente al próximo login exitoso.

### 2.2 Password policy

- Minimo 12 caracteres.
- Complejidad razonable (mezcla de mayúsculas, minúsculas, números, símbolos) — alternativamente, simplemente 14+ chars sin restricción de complejidad (NIST 800-63B 5.1.1.2).
- Blacklist de passwords comunes (top 100K de HaveIBeenPwned o similar).
- NO forzar cambios periódicos de password (NIST 800-63B 5.1.1.2).

### 2.3 Sesiones (cookie HttpOnly + Secure)

- Cookies con `HttpOnly`, `Secure`, `SameSite=Lax`.
- Token de sesión opaco (no JWT) almacenado en BD.
- Expiración relativa (sliding) ≥ 24 h con limite absoluto ≤ 30 dias.
- Logout invalida el token en BD.
- Rotacion de session ID en login exitoso (anti session fixation).

### 2.4 JWT (alternativa a cookies)

- Si usas JWT en lieu de cookies:
  - Algoritmo `RS256` o `EdDSA`. NO `HS256` con secret compartido.
  - Expiración corta (≤ 15 min).
  - Refresh token separado, almacenado en cookie HttpOnly o en BD.
- NO almacenes JWT en `localStorage`; vulnerable a XSS.

### 2.5 Multi-Factor Authentication (MFA)

- Para apps con datos sensibles, soportar MFA opcional (TOTP via apps como Google Authenticator).
- Backup codes generados en setup.
- Recovery flow seguro (no por email simple; idealmente confirmation por admin u otro factor).

### 2.6 Recuperación de password

- Token unico de un solo uso, con expiración ≤ 1 h.
- Email enviado por servicio externo (SES, SendGrid, etc.) — no SMTP propio en el contenedor.
- Ratelimit estricto (3 intentos por hora por email).
- NO revelar si el email existe en respuestas (opacidad anti-enumeration).

### 2.7 Roles y permisos

- Modelo RBAC sugerido: `users <-> roles <-> permissions`.
- Permisos como strings opacos (`users.create`, `reports.view`).
- Rol `superadmin` con TODOS los permisos (asignado al usuario `admin@llyasoc.com` por el seeder de fase 05).
- Permisos verificados en backend (NO solo en frontend).

### 2.8 Audit log de auth

- Tabla `audit_log` con eventos: login (exitoso y fallido), logout, password change, role change.
- Campos: timestamp, user_id, action, ip_address, user_agent, success.
- Retencion mínima 90 dias.
- Inmutable (solo INSERT; idealmente con triggers DB que rechazan UPDATE/DELETE).

---

## 3. Estructura de repositorios

> *Takeaway:* un repo por app, trunk-based, conventional commits, semver, CHANGELOG generado.

(Igual que en v1, sin cambios significativos.)

- Poly-repo (un repo por app).
- Trunk-based development con `main` protegida.
- Conventional commits + SemVer + Keep a Changelog.
- `CODEOWNERS`, `SECURITY.md`, `LICENSE`, `.editorconfig`, `.gitattributes`.
- ADRs en `docs/ADR/` para decisiones técnicas mayores.

---

## 4. CI/CD con GitHub Actions

(Mayormente igual que v1; los cambios son específicos del modelo v2.)

### 4.1 Pipeline canónico v2

```
validate → build → scan → publish → register → seed
```

Diferencias respecto a v1:
- **`maestro-cli validate`** verifica `apiVersion: maestro.platform/v2` y campos nuevos (auth.mode=own, branding.url, seeding).
- **`register`** envia metadata al Maestro v2 (cuando exista).
- **`seed`** ejecuta el seeder del superadmin (parte de fase 05-seeding del framework v4).

### 4.2 Acciones recomendadas

(Idem v1.) `actions/checkout@v4`, `docker/build-push-action@v6`, `aquasecurity/trivy-action`, `sigstore/cosign-installer@v3`, `gitleaks/gitleaks-action@v2`, `github/codeql-action`.

### 4.3 Secret management

- `MAESTRO_API_KEY` y `SUPERADMIN_INITIAL_PASSWORD` se inyectan via GitHub Secrets o vault externo.
- Nunca en código, nunca en logs.
- Rotación recomendada cada 90 dias.

---

## 5. Seguridad (Supply Chain + AppSec)

> *Takeaway:* asumir compromiso. Firmar todo, escanear todo, rotar todo, almacenar nada salvo passwords hasheadas.

### 5.1 Supply chain

(Igual a v1.) Lock files, pin de imágenes por digest, pin de actions por SHA, SBOM, provenance, cosign sign.

### 5.2 AppSec específico de v2

- **SAST con foco en auth:** code scanners deben verificar uso correcto del middleware de auth, no leakeo de passwords en logs, no SQL injection en queries de auth.
- **DAST:** OWASP ZAP baseline contra `/login`, `/logout`, endpoints protegidos, `/maestro/branding`, hooks.
- **Dependency review:** bloquear PRs que introducen libs de auth con CVEs altas.
- **License scanning:** mantener dependencies con licencias compatibles.

### 5.3 Hardening de imágenes Docker

(Idem v1.) Multi-stage, USER no-root, read-only filesystem cuando posible, cap-drop ALL.

### 5.4 Hardening de runtime

- Variables de entorno sensibles **NUNCA** se loguean (filtros en logger).
- Headers de respuesta: HSTS, CSP, X-Content-Type-Options, Referrer-Policy.
- Rate limiting en `/login` (ej. 5 intentos por minuto por IP, 10 por hora por email).

### 5.5 Política de rotación

- `MAESTRO_API_KEY` rota cada 90 dias.
- `JWT_SECRET` / `APP_KEY`: rotación trimestral con soporte de múltiples claves activas durante transición.
- Credenciales de BD: rotación coordinada por Maestro v2.
- Tokens de sesión: invalidados en logout y al cambio de password.

---

## 6. Observabilidad

> *Takeaway:* logs JSON + métricas Prometheus + trazas OTel. Atributos `user_id`, `request_id` (sin `tenant_id`/`company_id` en v2 single-tenant).

### 6.1 Logs estructurados

```json
{
  "ts": "2026-05-06T13:24:11.832Z",
  "level": "info",
  "msg": "user.login.success",
  "user_id": "b3a8c0e8-...",
  "request_id": "01HV7N5Z...",
  "app": "hr-dashboard",
  "version": "2.0.0",
  "duration_ms": 47
}
```

- **Sin `company_id`** (single-tenant fisico).
- Eventos de auth siempre logueados (login.success, login.failed, logout, password_change).
- Nunca loguear: `Authorization`, `Cookie`, `MAESTRO_API_KEY`, `MAESTRO_WEBHOOK_SECRET`, password, hash, JWT.

### 6.2 Métricas Prometheus

- Endpoint `/metrics` autenticado solo para el scrapper del Maestro.
- Métricas RED por endpoint: Rate, Errors, Duration.
- Métricas USE por instancia: CPU, memoria, BD pool.
- Métricas de auth: `auth_login_attempts_total`, `auth_login_failures_total`, `auth_active_sessions`.

### 6.3 Trazas distribuidas (OpenTelemetry)

(Idem v1.) Auto-instrumentación, propagación W3C Trace Context, sampling.

### 6.4 SLOs y error budgets

- SLO de disponibilidad: `success_rate > 99.5 %` mensual.
- SLO de latencia: `p99 < 500 ms` para endpoints UI; `p99 < 1 s` para login.
- Alertas multi-window multi-burn-rate.

---

## 7. Testing

> *Takeaway:* pirámide normal: muchos unit, suficientes integración, pocos e2e. Sumá *contract tests* del contrato v2.

### 7.1 Niveles

| Nivel | Cobertura objetivo |
|---|---|
| Unit | ≥ 70 % de lógica de dominio |
| Integración | Rutas críticas + acceso a BD real (testcontainers) |
| Contract test del SDK (cuando exista para v2) | Todas las rutas auth + branding |
| E2E | Flujos top 5 (login, logout, recuperación, CRUD principal) |
| Smoke en producción | Health + login del superadmin + 1 lectura |

### 7.2 Tests específicos de v2 obligatorios

- Login con creds validas → 200 + token/cookie.
- Login con creds invalidas → 401.
- Endpoint protegido sin auth → 401.
- Endpoint protegido con auth válida → 200.
- `/maestro/branding` sin api key → 401.
- `/maestro/branding` con api key inválida → 401.
- `/maestro/branding` con api key válida → 200 + JSON con `company_name` y `logo_url`.
- Seed idempotente: re-ejecutar NO duplica `admin@llyasoc.com`.
- Superadmin tiene TODOS los permisos definidos por la app.
- Hooks: `X-Maestro-Webhook-Signature` ausente o invalido → 401; valido → 200.

### 7.3 Test data

- Usuarios de prueba creados por test setup, eliminados en teardown.
- Nunca usar `admin@llyasoc.com` en tests automatizados (es el superadmin real).
- Para tests integrados con Maestro v2 mock, usar fixtures de `acme-demo` o equivalente.

### 7.4 Mutation testing (avanzado)

- Para apps con lógica financiera/regulada, ratio de mutantes detectados ≥ 80 %.

---

## 8. Despliegue y operación

> *Takeaway:* migraciones expand-then-contract, blue/green via Maestro v2, feature flags por usuario.

### 8.1 Migraciones de BD seguras

(Igual a v1.) Expand-then-contract, dual-write, indices CONCURRENTLY.

### 8.2 Feature flags

- Flags por **usuario** o por **rol** (en v2 single-tenant, ya no por tenant).
- Recomendados: GrowthBook, Unleash, OpenFeature SDK.
- Flags muertos eliminados cada quarter.

### 8.3 Release management

- Releases pequeños y frecuentes.
- Tag semver al merge a main; release-please para CHANGELOG.
- Anuncio via webhook a Slack/Discord.

### 8.4 Rollback

- Maestro v2 mantiene versiones en GHCR.
- App tolerante a rollback: una migración aplicada no debe bloquear correr la versión anterior (ver §8.1).

### 8.5 Cold start budget

- Primer request en ≤ 15 s desde STOPPED → RUNNING.
- Imagen liviana, lazy initialization, health check rápido.

### 8.6 Capacity planning

- Load tests trimestrales (k6, Gatling, JMeter).
- Alertas en Grafana cuando una instancia consume > 80 % de tier.

---

## 9. Comunicación y colaboración

(Idem v1.) Slack/Discord, Issues, RFCs, ADRs, code review, on-call, postmortems blameless.

---

## 10. Documentación que la app debe mantener

- `README.md` con quickstart.
- `RUNBOOK.md` con incidentes comunes.
- `OpenAPI 3.1` (si la app expone API).
- `SECURITY.md`.
- ADRs en `docs/ADR/`.
- **NEW v2:** documentación del modelo de auth (login flow, password policy, MFA si aplica, recuperación), del modelo de roles/permisos, y del seeder del superadmin.

---

## 11. Performance

(Idem v1.)

- Latencia: `p99 < 500 ms` para UI; `p99 < 5 s` para reportes pesados.
- Throughput: tier `standard` ≥ 50 RPS sostenidos en lecturas simples.
- Caché: TTLs cortos, prefijos por usuario (single-tenant ya garantiza aislamiento).
- BD: pool dimensionado por tier, índices sobre `users.email` (lookup frecuente en login).

---

## 12. Definition of Done v2

Una versión está lista para registrarse en Maestro v2 cuando:

### Contrato
- [ ] `maestro.yaml` valida contra schema v2 (`apiVersion: maestro.platform/v2`).
- [ ] Versión bumpeada según semver.
- [ ] CHANGELOG actualizado.

### Auth (NEW v2)
- [ ] Login propio implementado (login_path + middleware).
- [ ] Tabla users con password_hash (bcrypt o argon2id).
- [ ] Modelo de roles y permisos implementado.
- [ ] Endpoint `/maestro/branding` autenticado con `X-Maestro-Api-Key`.
- [ ] Seeder del superadmin idempotente.
- [ ] `admin@llyasoc.com` se crea correctamente con `SUPERADMIN_INITIAL_PASSWORD`.

### Código
- [ ] Linter, formatter, type-check verdes.
- [ ] Tests unitarios verdes con cobertura ≥ 70 %.
- [ ] Tests de integración con BD real verdes.
- [ ] Tests específicos de v2 (login, logout, branding, seed) verdes.

### Seguridad
- [ ] gitleaks limpio (historial completo).
- [ ] Trivy CRITICAL/HIGH limpio.
- [ ] CodeQL sin findings críticos.
- [ ] Cosign sign aplicado.
- [ ] SBOM publicado.
- [ ] No leakeo de api keys / passwords / tokens en logs.

### Operación
- [ ] Health endpoint < 3 s.
- [ ] Logs JSON con `user_id` y `request_id` (sin `company_id`).
- [ ] Métricas `/metrics` expuestas.
- [ ] Audit log de eventos de auth implementado.
- [ ] Migraciones backward-compatible.

### Documentación
- [ ] README quickstart verificado.
- [ ] RUNBOOK actualizado.
- [ ] CHANGELOG completa la versión actual.
- [ ] Documentación del modelo de auth y roles.

---

## 13. Anti-patrones organizacionales (qué evitar)

(Idem v1, mas:)

| Anti-patrón v2 | Por qué evitar | Alternativa |
|---|---|---|
| Mezclar auth headers `X-Auth-*` con auth propia | Crea ambiguedad, vulnerabilidades | Auth propia exclusivamente |
| Multi-tenancy logica con `company_id` en v2 | Contradice single-tenant fisico | Un contenedor por empresa |
| Hardcodear `SUPERADMIN_INITIAL_PASSWORD` | Leak en imagen / repo | ENV var inyectada |
| Seeder no idempotente | Crea duplicados o pisa cambios | Idempotente; chequea existencia |
| Loggear password / api key | Compromiso de seguridad | Filtros en logger |

---

## 14. Estándares de industria referenciados

(Igual que v1, mas: NIST SP 800-63B Digital Identity Guidelines, OWASP ASVS 4.0 V2 Authentication, OWASP ASVS 4.0 V3 Session Management.)

---

## 15. Cómo este documento se mantiene

- PR contra este archivo.
- Cambios estructurales requieren ADR.
- Revisión semestral por el equipo de plataforma.
- Cuando una recomendación se vuelva norma, migrar la cláusula a `APP_HUESPED_SPEC_V2.md`.

---

## 16. Historial de revisiones

| Versión | Fecha | Cambio |
|---|---|---|
| 2.0.0 | 2026-05-06 | Versión inicial. Best practices alineadas con `maestro.platform/v2` y framework agéntico v4. Énfasis en auth propia, single-tenant fisico, seeding del superadmin. |
