# Mejores Prácticas para Aplicaciones Huésped — Maestro Platform

> ⚠️ **DOCUMENTO DEPRECADO (acompaña al contrato v1) — superado por `docs/APP_HUESPED_BEST_PRACTICES_V2.md`.**
>
> Este documento contiene practicas alineadas con el contrato `maestro.platform/v1` (Maestro v1, framework v3). Para apps nuevas (framework v4) usar `APP_HUESPED_BEST_PRACTICES_V2.md`.
>
> Algunas practicas siguen siendo aplicables (12-factor, supply chain, observabilidad, testing, despliegue, comunicacion). Las que cambian estan marcadas en el documento V2 con notas explicitas.
>
> ---
>
> **Documento orientativo (legacy).** Acompaña a `docs/APP_HUESPED_SPEC.md` v1 (legacy).
>
> **Audiencia:** equipos que diseñan, implementan, operan y mantienen apps en Maestro Platform.
> **Carácter:** recomendaciones derivadas de estándares industriales (12-factor, OWASP, OpenSSF, SLSA, NIST SSDF, CNCF) adaptadas al contexto de la plataforma.
> **Última revisión:** 2026-04-28.

Las recomendaciones aquí vertidas están priorizadas con un código de color implícito por sección. Cada subsección abre con un *takeaway* en una línea para lectura rápida y baja a profundidad para implementadores.

---

## 1. Filosofía base

> *Takeaway:* combiná **12-factor**, **tenant-aware-by-default** y **zero-trust**. Cuando dudes, prefiere cumplir los tres a la vez.

### 1.1 The Twelve Factors aplicados a Maestro

| Factor | Implicación en Maestro |
|---|---|
| 1. Codebase | Un repositorio por app, varios deploys (uno por empresa). |
| 2. Dependencies | Todas declaradas (`package.json`, `composer.json`, `go.mod`, `requirements.txt`). Lock files commiteados. |
| 3. Config | Solo vía env vars inyectadas por Maestro. Nada en código ni en imagen. |
| 4. Backing services | La BD es un recurso adjunto via `DATABASE_URL`. Cambiable sin redeploy de imagen. |
| 5. Build, release, run | Build = imagen Docker; release = imagen + config inyectada; run = contenedor en VPS. Etapas separadas. |
| 6. Processes | Apps stateless. Estado en BD, archivos solo en blob storage del Maestro. |
| 7. Port binding | App escucha en `requires.ports.app`. Nadie más lo bindea. |
| 8. Concurrency | Escalar verticalmente bumpeando tier; horizontalmente cuando Maestro pase a Swarm/K8s. |
| 9. Disposability | Arranque ≤ 60 s, shutdown limpio en SIGTERM ≤ 30 s. |
| 10. Dev/prod parity | `docker-compose.dev.yml` reproduce headers `X-Auth-*` y motor de BD idéntico. |
| 11. Logs | JSON a stdout. Promtail/Loki los recoge. |
| 12. Admin processes | Comandos artisan / management / scripts vía `docker exec` o jobs efímeros, nunca embebidos en el server web. |

### 1.2 Tenant-aware-by-default

- Todo modelo, repositorio, servicio o caché **DEBE** filtrar por `company_id` del header.
- Usá el SDK oficial: implementa el patrón *Row-Level-Security application-side*. Si rolá tu propio adaptador, **escribí tests que verifiquen que un usuario de empresa A nunca puede leer datos de empresa B**.
- Caché por tenant: prefijar todas las claves con `c:<company_id>:`. Nunca compartir caché entre empresas.

### 1.3 Zero trust en el borde y en el interior

- El borde lo cubre Traefik + ForwardAuth. Vos no necesitás auth.
- En el interior: cada llamada saliente a otra app **DEBE** pasar por el API Gateway del Maestro y firmarse con `MAESTRO_APP_SECRET`.
- Nunca confíes en hostnames del DNS interno: validá la firma del payload.

---

## 2. Estructura de repositorios

> *Takeaway:* un repo por app, trunk-based, conventional commits, semver, CHANGELOG generado.

### 2.1 Mono-repo vs poly-repo

- **Recomendado:** poly-repo (un repo por app). Aísla blast radius, simplifica permisos, alinea con la separación de equipos del Maestro.
- **Mono-repo justificado:** equipos de plataforma que mantienen 3+ apps muy acopladas y tienen tooling para enrutar despliegues por path. Si vas a mono-repo, usá `nx`, `turborepo`, `bazel` o `pnpm workspaces`.

### 2.2 Branching: trunk-based development

- Una sola rama larga: `main`.
- Feature branches cortas (≤ 3 días, idealmente ≤ 1 día).
- Toda integración a `main` vía Pull Request con CI verde + ≥ 1 reviewer.
- Releases por tag semver (`v1.4.2`), nunca por rama larga.

### 2.3 Conventional Commits + SemVer + Keep a Changelog

- Mensajes de commit: `<tipo>(<scope>)!: <mensaje>` con tipos `feat`, `fix`, `chore`, `docs`, `refactor`, `test`, `perf`, `build`, `ci`, `revert`.
- `!` después del scope marca breaking change.
- SemVer: `MAJOR.MINOR.PATCH`. Breaking → MAJOR. Funcionalidad backward-compat → MINOR. Bug fix → PATCH.
- `CHANGELOG.md` generado por `release-please` o `changesets` desde commits.

### 2.4 Code ownership

- `CODEOWNERS` en `.github/` mapea paths a equipos para auto-asignar reviewers.
- Reglas de protección de `main`:
  - Require PR review (≥ 1, idealmente 2 para cambios en seguridad/migraciones).
  - Require status checks (todos los jobs de CI verdes).
  - Require branches up-to-date.
  - Require signed commits (gpg o sigstore).
  - Disallow force-push y deletion.

### 2.5 Convenciones de archivos

| Archivo | Recomendación |
|---|---|
| `README.md` | Quickstart en ≤ 5 minutos. Diagrama de arquitectura ASCII. Variables de entorno. Cómo correr `docker-compose.dev.yml`. |
| `CHANGELOG.md` | Generado automáticamente. No editar a mano. |
| `CONTRIBUTING.md` | Cómo abrir PRs, estilo de commits, cómo ejecutar tests. |
| `SECURITY.md` | Canal privado de reporte (`security@…`), SLA de respuesta, política de disclosure (90 días o coordinada). |
| `LICENSE` | Identificada con SPDX (`MIT`, `Apache-2.0`, `BSD-3-Clause`, `proprietary`). |
| `.editorconfig` | Tamaño de tab, charset, EOL — uniforme cross-IDE. |
| `.gitattributes` | `* text=auto eol=lf`. Evita problemas con CRLF en Windows. |
| `docs/ADR/` | Architecture Decision Records (Michael Nygard format). Nuevo ADR por decisión técnica importante. |
| `docs/RFC/` | Para propuestas grandes (cambios cross-cutting), antes de codificar. |

---

## 3. CI/CD con GitHub Actions

> *Takeaway:* pipeline en 5 fases (validate → build → scan → publish → register). Cada fase falla rápido y reporta en el PR.

### 3.1 Pipeline canónico

```
validate (en cada push)
  ├── lint
  ├── typecheck
  ├── unit tests
  ├── maestro-cli validate
  ├── gitleaks (historial completo)
  └── dependency review (PRs)
build-and-push (solo en main)
  ├── docker buildx build --provenance --sbom
  ├── push GHCR (tags: <semver>, <sha>, NUNCA :latest)
scan
  ├── trivy / grype sobre la imagen (CRITICAL/HIGH bloquean)
  ├── cosign sign (sigstore keyless)
  └── attestations (SLSA L3 build provenance)
publish-artifacts
  ├── upload SBOM (SPDX o CycloneDX)
  └── upload provenance attestation
register
  └── POST /api/v1/apps/register al Maestro
```

### 3.2 Acciones recomendadas (con anclaje a SHA)

| Acción | Propósito |
|---|---|
| `actions/checkout@v4` | Checkout del código. Usá `fetch-depth: 0` para gitleaks. |
| `actions/setup-node@v4` / `setup-python@v5` / `setup-go@v5` / `shivammathur/setup-php@v2` | Setup del runtime con cache integrado. |
| `docker/setup-buildx-action@v3` | Builder con cache + multi-arch. |
| `docker/login-action@v3` | Login a GHCR vía `GITHUB_TOKEN`. |
| `docker/build-push-action@v6` | Build con `provenance: true` + `sbom: true`. |
| `aquasecurity/trivy-action` o `anchore/scan-action` | Scan de vulnerabilidades. |
| `sigstore/cosign-installer@v3` + `cosign sign --yes` | Firma keyless de imágenes. |
| `gitleaks/gitleaks-action@v2` | Detección de secretos en historial. |
| `github/codeql-action` | SAST contra PRs. |
| `actions/dependency-review-action` | Bloquea introducción de deps con CVEs altas en PRs. |
| `release-please-action` | Generación de releases + tags + CHANGELOG. |

> **Anclá las acciones a SHA**, no a tag mutable, para reducir riesgo de supply chain (`uses: actions/checkout@a5ac7e51b41094c92402da3b24376905380afc29 # v4.1.1`).

### 3.3 Permisos mínimos del workflow

```yaml
permissions:
  contents: read       # leer el repo
  packages: write      # publicar a GHCR
  id-token: write      # OIDC para cosign keyless / cloud login
  pull-requests: write # para release-please / dependency-review
```

Nunca `permissions: write-all`. Configuración recomendada a nivel organización: `read` por defecto, los workflows escalan.

### 3.4 OIDC en lugar de secrets de cloud

- Para autenticarte a AWS / Azure / GCP, usá **OIDC federation** vía `id-token: write` y los actions oficiales de cada cloud (`aws-actions/configure-aws-credentials@v4`, `azure/login@v2`, `google-github-actions/auth@v2`).
- Resultado: no hay long-lived secrets en el repo; las credenciales son ephemeral y con scope mínimo.

### 3.5 Reusable workflows y composite actions

- Si tu organización mantiene varias apps, extraé los pasos comunes (validate, scan, sign, register) a un repo `org/.github` con `workflow_call`.
- Las apps consumen: `uses: org/.github/.github/workflows/maestro-app.yml@v1`.
- Aislamiento de cambios: bumps controlados por tag.

### 3.6 Concurrency, environments y approval gates

- `concurrency: { group: deploy-${{ github.ref }}, cancel-in-progress: false }` evita despliegues paralelos del mismo branch.
- Definí `environments: production` con required reviewers para gate manual antes de `register`.
- Para apps críticas, gate adicional con check de "horario laboral / no-freeze" (ver §4 de `APP_HUESPED_SPEC.md` y memoria de freeze de release).

---

## 4. Seguridad (Supply Chain + AppSec)

> *Takeaway:* asumir compromiso. Firmar todo, escanear todo, rotar todo, almacenar nada.

### 4.1 Supply chain

| Práctica | Herramienta | Rol |
|---|---|---|
| Lock files | npm/yarn/pnpm/composer/pip/go.sum | Reproducibilidad. |
| Pin de imágenes base por digest | `FROM node:22.13-alpine@sha256:...` | Inmutabilidad de la base. |
| Pin de actions por SHA | `uses: foo/bar@<sha40>` | Inmutabilidad de las actions. |
| SBOM | Syft (integrado en buildx con `sbom: true`) | Inventario auditable. |
| Provenance | SLSA L3 attestation (buildx `provenance: true`) | Quién y cómo construyó la imagen. |
| Firma | Cosign keyless (sigstore) | Verificable sin gestionar claves. |
| Verificación en deploy | Maestro verifica firma cosign antes de provisionar | Cierra el loop. |
| Dependabot | `.github/dependabot.yml` | Bumps automáticos semanales. |
| Renovate | Alternativa más flexible que Dependabot | Reglas finas por paquete. |

### 4.2 AppSec en CI

- **SAST:** GitHub Advanced Security CodeQL para JS/TS/Python/Go/Java/Ruby/C#. Ejecutar en push y en cron semanal.
- **DAST:** OWASP ZAP baseline en staging contra el endpoint expuesto vía Traefik.
- **Secret scanning:** habilitar en GitHub repos (push protection). Reforzar con `gitleaks` que cubre el historial.
- **Dependency review:** action oficial bloquea PRs que introducen vulns críticas.
- **License scanning:** `licensee` o `fossa` para detectar licencias incompatibles con tu producto.

### 4.3 Hardening de imágenes Docker

- Multi-stage build con runtime mínima (alpine, slim, distroless).
- `USER` no-root (UID > 1000).
- `--read-only` filesystem cuando sea posible (ajustar `tmpfs` para temporales).
- `--cap-drop=ALL --cap-add=<solo lo necesario>` (mayoría de apps no necesita ninguna capability).
- `--security-opt=no-new-privileges` (lo aplica el Maestro automáticamente).
- Imagen final sin shell ni paquete manager (distroless impide `docker exec` interactivo, asumilo y usá sidecars de debug).

### 4.4 Hardening de runtime

- `seccomp` default profile habilitado (Maestro lo aplica).
- Variables de entorno sensibles **NUNCA** se loguean. Filtros en logger.
- Cabeceras de respuesta:
  - `Strict-Transport-Security: max-age=31536000; includeSubDomains; preload` (Traefik lo añade, vos no lo sobrescribas).
  - `Content-Security-Policy` adecuado para tu UI.
  - `X-Content-Type-Options: nosniff`.
  - `Referrer-Policy: strict-origin-when-cross-origin`.

### 4.5 Política de rotación

- `MAESTRO_APP_SECRET` rota automáticamente cada 90 días. La app **DEBE** soportar dos secretos válidos en transición (verificar firma con cualquiera).
- Credenciales de BD: rotación coordinada por Maestro. La app las relee al recibir SIGHUP o al reiniciar.
- API keys de servicios externos: rotación trimestral mínima.

---

## 5. Observabilidad

> *Takeaway:* logs JSON + métricas Prometheus + trazas OTel. Atributo `tenant_id` en todo.

### 5.1 Logs estructurados

```json
{
  "ts": "2026-04-28T13:24:11.832Z",
  "level": "info",
  "msg": "ticket.created",
  "tenant_id": "7e2b1f12-...",
  "user_id": "b3a8c0e8-...",
  "request_id": "01HV7N5Z...",
  "app": "hr-dashboard",
  "version": "0.9.0",
  "duration_ms": 47,
  "ticket_id": "tk_8123"
}
```

- Un solo logger por app, configurado por env (`LOG_LEVEL`, `LOG_FORMAT`).
- En desarrollo: pretty-print. En producción: JSON.
- Recomendados: `pino` (Node), `structlog` (Python), `monolog` con `JsonFormatter` (Laravel), `slog` (Go ≥ 1.21).
- Nunca loguear: `Authorization`, `Cookie`, `X-Auth-*` completo, body de requests con PII, payloads de webhooks con datos sensibles.

### 5.2 Métricas Prometheus

- Endpoint `/metrics` autenticado solo para el scrapper de Prometheus del Maestro (Maestro lo accede vía red privada).
- Métricas RED por endpoint: Rate, Errors, Duration.
- Métricas USE por instancia: Utilization, Saturation, Errors (CPU, memoria, BD pool).
- Etiquetas obligatorias: `app`, `version`, `tenant_id` (cuidado con cardinalidad: si hay > 1k tenants, omitir tenant en métricas y mantenerlo solo en logs/trazas).

### 5.3 Trazas distribuidas (OpenTelemetry)

- Auto-instrumentación de los SDKs oficiales (HTTP server, BD, HTTP client).
- Propagar `traceparent` y `tracestate` (W3C Trace Context) en llamadas inter-app.
- Endpoint OTLP: `MAESTRO_OTLP_ENDPOINT` cuando esté disponible (env var futura).
- Sampling: 100 % en error, 5–10 % en happy path; tail-sampling en el colector central.

### 5.4 SLOs y error budgets

- Definir SLO por endpoint crítico:
  - Latencia: `p99 < 500 ms` (ej.).
  - Disponibilidad: `success_rate > 99.5 %` mensual.
- Error budget = `1 - SLO`. Si se consume > 50 % del budget en 7 días, frenar features y trabajar en estabilidad.
- Alertas multi-window multi-burn-rate (Google SRE Workbook).

---

## 6. Testing

> *Takeaway:* pirámide invertida está mal; pirámide normal: muchos unit, suficientes integración, pocos e2e. Sumá *contract tests* contra el contrato del Maestro.

### 6.1 Niveles

| Nivel | Cobertura objetivo | Velocidad esperada |
|---|---|---|
| Unit | ≥ 70 % de lógica de dominio | < 100 ms por test |
| Integración | Rutas críticas + acceso a BD real (testcontainers) | 1–10 s por test |
| Contract test del SDK | Todas las rutas de la app | Determinístico |
| E2E (docker-compose.dev) | Flujos de usuario top 5 | Aceptable < 5 min |
| Smoke en producción | Health + login + 1 lectura + 1 escritura por tenant canario | < 30 s |

### 6.2 Test data y tenants de prueba

- Cada test crea su propio `company_id` aleatorio (UUID) y limpia al final.
- Nunca uses tenants reales en tests automatizados.
- Para tests integrados con Maestro real, usá el set bootstrap-demo (tenant `acme-demo`), nunca empresas con datos productivos.

### 6.3 Contract tests

- Generá un test que arranca tu app, simula los headers `X-Auth-*` con un mock-Traefik, y verifica:
  - `/health` responde 200 en ≤ 3 s.
  - Cualquier ruta sin headers responde 401.
  - Datos de empresa A nunca se filtran a empresa B (test paramétrico cruzado).
- El SDK oficial provee este harness; usalo.

### 6.4 Mutation testing (avanzado)

- Para apps con lógica de negocio sensible (financiera, regulada), correr mutation testing periódico (`stryker-mutator` para Node/.NET, `mutmut` para Python, `infection` para PHP, `gomutesting` para Go).
- Ratio aceptable: ≥ 80 % mutantes detectados.

---

## 7. Despliegue y operación

> *Takeaway:* migraciones expand-then-contract, blue/green vía Maestro, feature flags por tenant.

### 7.1 Migraciones de BD seguras

| Operación | Estrategia |
|---|---|
| Agregar columna nullable | Una sola migración, deploy normal. |
| Agregar columna `NOT NULL` | Tres pasos: (1) migración agrega columna nullable, deploy app que escribe en ambas. (2) backfill async. (3) migración que pone `NOT NULL` y elimina código de doble-escritura. |
| Renombrar columna | Expand-then-contract: agregar nueva, dual-write, migrar lectura, deprecar vieja en N+1. |
| Borrar columna | Marcar como deprecada en una versión, removerla en la siguiente major. |
| Cambiar tipo | Expand-then-contract con columna shadow. |
| Agregar índice grande | `CREATE INDEX CONCURRENTLY` (Postgres). En MySQL, online DDL o pt-online-schema-change. |

> Regla de oro: **una migración nunca debe ser incompatible con la versión anterior de la app**. Si lo es, partila.

### 7.2 Feature flags

- Recomendados: GrowthBook self-hosted, Unleash, OpenFeature SDK.
- Flags por tenant (`X-Auth-Company-Id` como contexto).
- Toda nueva feature de riesgo va detrás de un flag inicialmente en 0 %, se rampea por canary tenant (`acme-demo`), luego por cohorte, luego al 100 %.
- Borrar flags muertos cada quarter; código tras flag eliminado debe limpiarse.

### 7.3 Release management

- Cadencia recomendada: releases pequeños y frecuentes (≥ 1 por sprint, idealmente diario en main).
- Tag semver al merge a main; el workflow de `release-please` propone PR de release con CHANGELOG.
- Anuncio de release: webhook a Slack/Discord con link al CHANGELOG.

### 7.4 Rollback

- Maestro mantiene versiones en GHCR. Rollback = re-provisionar instancia con tag anterior.
- La app **DEBE** ser tolerante a rollback: una migración aplicada no debe bloquear correr la versión anterior. De ahí la regla de §7.1.
- Definir runbook de rollback en `RUNBOOK.md` con comandos exactos.

### 7.5 Cold start budget

- App debería responder al primer request en ≤ 15 s desde STOPPED → RUNNING.
- Para lograrlo:
  - Imagen liviana (≤ 200 MB descomprimida).
  - Lazy initialization de conexiones costosas.
  - Health check rápido (≤ 200 ms en happy path).
  - JIT warmup mínimo (Node/Go cumplen; JVM/.NET requieren AOT o ReadyToRun).

### 7.6 Capacity planning

- Ejecutar load tests representativos (k6, Gatling, JMeter) trimestralmente o ante cambios mayores.
- Alertas en Grafana cuando una instancia consume > 80 % de tier por 3 ventanas de 5 min consecutivas → solicitar bump de tier o investigar leak.

---

## 8. Comunicación y colaboración

> *Takeaway:* documentar decisiones, automatizar lo repetitivo, definir canales claros.

### 8.1 Canales

| Canal | Uso |
|---|---|
| Slack/Discord `#maestro-platform` | Anuncios de plataforma, freezes, breaking changes. |
| Slack/Discord `#app-<slug>` | Por app: alertas, deploys, on-call handoff. |
| GitHub Issues | Bugs y features de la app. |
| GitHub Discussions | RFCs, dudas, decisiones abiertas. |
| Linear / Jira / Monday | Tracking de roadmap (no obligatorio). Linkear a PRs. |
| PagerDuty / Opsgenie | Incidentes de severidad ≥ 2. |
| Email `security@…` | Reporte privado de vulnerabilidades. |

### 8.2 Plantilla de Pull Request

`.github/PULL_REQUEST_TEMPLATE.md`:

```md
## Resumen
<qué cambia y por qué>

## Tipo
- [ ] feat / fix / chore / docs / refactor / test / perf / build / ci / revert

## Riesgo y blast radius
- [ ] Toca migraciones (expand-then-contract OK / N/A)
- [ ] Toca contrato `maestro.yaml` (subir versión)
- [ ] Toca seguridad / autenticación
- [ ] Cambia performance esperada

## Pruebas
- [ ] Unit
- [ ] Integración
- [ ] Manual en `docker-compose.dev`
- [ ] Tenant canario (`acme-demo`) en staging

## Checklist Maestro
- [ ] `maestro-cli validate` verde
- [ ] CHANGELOG actualizado (o release-please lo hace)
- [ ] Documentación actualizada si la API cambió
- [ ] Logs no exponen PII / secretos
```

### 8.3 ADRs

- Formato Michael Nygard: Title, Status, Context, Decision, Consequences.
- Numerados secuencialmente: `docs/ADR/0001-uso-de-postgres.md`.
- Status: Proposed → Accepted | Deprecated | Superseded by ADR-XXXX.
- Inmutables salvo cambio de status. Decisiones nuevas → ADR nuevo que supersede.

### 8.4 RFC para cambios grandes

- Cambios cross-cutting (rediseño de módulo, integración nueva, deprecación) abren un RFC en `docs/RFC/000N-titulo.md` antes de codificar.
- Plantilla: Motivación, propuesta detallada, alternativas, drawbacks, impacto, plan de rollout.
- Se discute en GitHub Discussions con un period de comentarios mínimo (3 días hábiles).

### 8.5 On-call y escalación

- Cada app define rotación on-call con un mínimo de 2 personas (sin SPOFs).
- Runbook en `RUNBOOK.md` cubre los escenarios de incidente más frecuentes.
- Severidades:
  - SEV-1: app caída para todos los tenants. Page inmediato.
  - SEV-2: degradación parcial, > 10 % requests con error. Notificación inmediata.
  - SEV-3: bug funcional sin downtime. Ticket en horario laboral.
  - SEV-4: cosmético / mejora.
- Postmortem obligatorio para SEV-1/SEV-2 en ≤ 5 días hábiles. Blameless. Output: ADRs y/o tickets de mejora.

### 8.6 Code review

- Reviewers focalizan en: corrección, claridad, seguridad, tenant-isolation, observabilidad.
- Reviewers **NO** focalizan en: estilo (lo hace el linter), performance prematura.
- Tono: descriptivo, con propuesta concreta. "Esta query no filtra por `company_id`, sugiero usar el scope `ForTenant`" > "Está mal".
- SLA: primer review ≤ 1 día hábil; resolver PRs en ≤ 5 días o cerrar.

---

## 9. Documentación que la app debe mantener

> *Takeaway:* doc viva, generada cuando se pueda, revisada con cada major.

### 9.1 README mínimo

```md
# <App slug>

> <una línea: qué hace y para quién>

## Quickstart local
```bash
docker-compose -f docker-compose.dev.yml up
open http://localhost:8080
```

## Variables de entorno
| Var | Obligatoria | Origen | Descripción |
| ... |

## Arquitectura
<diagrama ASCII o link a docs/architecture.md>

## Tests
```bash
make test
```

## Despliegue
Maestro lo hace tras `register`. Ver `RUNBOOK.md`.

## Licencia
SPDX: <identifier>
```

### 9.2 RUNBOOK.md

- Cómo conectar al log live (Grafana / Loki dashboard).
- Cómo dumpear el schema de la BD vía exec.
- Comandos de "hold the line" durante un incidente.
- Procedimiento de rollback paso a paso.
- Contactos de escalación.

### 9.3 OpenAPI / GraphQL schema

- Si la app expone API consumida por terceros, mantener OpenAPI 3.1 o el schema GraphQL versionado en `docs/api/`.
- Validar que el código y el schema no divergan vía test (`schemathesis`, `dredd`, `graphql-inspector`).

### 9.4 Documentación de seguridad (`SECURITY.md`)

- Versiones soportadas (matriz).
- Canal privado: `security@<dominio>` o GitHub private vulnerability reporting.
- SLA de triage: ≤ 72 h.
- Política de disclosure: 90 días o coordinada.

---

## 10. Performance

> *Takeaway:* presupuestos cuantificados por endpoint. Mídelo, no lo adivines.

### 10.1 Latencia

- Endpoint principal de UI: `p50 < 100 ms`, `p99 < 500 ms`.
- Endpoint pesado de reporte: `p99 < 5 s`. Si supera, mover a job async + polling.
- Health endpoint: `p99 < 200 ms`.

### 10.2 Throughput

- Cada instancia tier `standard` debería soportar ≥ 50 RPS sostenidos en lecturas simples.
- Para más, escalar tier o partir la app.

### 10.3 Caché

- Redis disponible vía `REDIS_URL` si la app lo declara.
- TTLs cortos (1–5 min) salvo justificación.
- Invalidación al escribir; nunca depender solo de TTL para corrección.
- Claves prefijadas por `tenant_id` para evitar leaks.

### 10.4 BD

- Pool de conexiones: dimensionar por `tier`. `micro: 5`, `standard: 10`, `professional: 20`, `enterprise: 50`.
- Toda query nueva pasa por `EXPLAIN` antes de mergear.
- Índices sobre `company_id` siempre, y sobre las columnas usadas en WHERE de filtros frecuentes.
- Sin N+1: usar eager-loading (`include`/`with`/`Preload`).

---

## 11. Accesibilidad y UX (apps con UI)

> *Takeaway:* WCAG 2.2 AA mínimo. i18n desde el día 1 si vendés a Latam + España.

- Tests automáticos: `axe-core` integrado en e2e.
- Targets: contraste 4.5:1 mínimo para texto normal, 3:1 para texto grande.
- Foco visible siempre, navegación completa por teclado.
- ARIA: usar landmarks, nombres accesibles, evitar duplicar (no `aria-label` cuando hay `<label>` correcto).
- i18n: cadenas extraídas a archivos `locale/<lang>.json`. Nunca concatenar strings.
- Soportar locale del browser y del header `X-Auth-User-Locale` (si la plataforma lo añade).

---

## 12. Definition of Done — checklist antes de pedir registro

Una versión está lista para registrarse en Maestro cuando:

### Contrato
- [ ] `maestro.yaml` valida contra el schema (`maestro-cli validate` verde).
- [ ] Versión bumpeada según semver.
- [ ] CHANGELOG actualizado.

### Código
- [ ] Linter verde, formatter aplicado.
- [ ] Type-check verde (si aplica).
- [ ] Tests unitarios verdes con cobertura ≥ 70 % en lógica de dominio.
- [ ] Tests de integración con BD real verdes.
- [ ] Contract tests del SDK verdes (incluye cross-tenant).

### Seguridad
- [ ] gitleaks limpio (historial completo).
- [ ] Trivy CRITICAL/HIGH limpio en la imagen final.
- [ ] CodeQL sin findings críticos.
- [ ] Dependabot al día (no PRs abiertos > 30 días).
- [ ] Cosign sign aplicado.
- [ ] SBOM publicado.

### Operación
- [ ] Health endpoint responde < 3 s con la BD real.
- [ ] Logs JSON con `tenant_id` y `request_id`.
- [ ] Métricas `/metrics` expuestas.
- [ ] Migraciones backward-compatible (si las hay).

### Documentación
- [ ] README quickstart verificado en un entorno limpio.
- [ ] RUNBOOK actualizado con cualquier nuevo procedimiento.
- [ ] CHANGELOG completa el "Unreleased" con la versión actual.
- [ ] ADRs nuevos commiteados si hubo decisiones técnicas relevantes.

### Despliegue
- [ ] Imagen publicada con tag `<semver>` y `<sha>` (no `:latest`).
- [ ] Workflow de `register` ejecutado y exitoso.
- [ ] Smoke tests en staging contra tenant canario aprobados.

---

## 13. Anti-patrones organizacionales (qué evitar)

| Anti-patrón | Por qué evitar | Alternativa |
|---|---|---|
| Long-lived feature branches | Drift con main, merge hells, riesgo en PR enormes. | Trunk-based + feature flags. |
| PRs gigantes | Imposibles de revisar a fondo, ocultan bugs. | PRs ≤ 400 LOC; partir el cambio. |
| "Lo arreglo en el siguiente PR" | Deuda técnica que nunca se paga. | Si es chico, en este PR. Si es grande, ticket inmediato y referenciado. |
| Tests solo del happy path | Falsos positivos de calidad. | Tests de borde, errores, concurrencia, idempotencia. |
| Logs de texto plano sin nivel | Imposible buscar / filtrar. | JSON estructurado con `level`. |
| Usar `:latest` en producción | Despliegues no reproducibles, riesgo de pull mutado. | Tag semver inmutable + digest. |
| Compartir secretos por chat | Leak de credenciales. | Vault / 1Password / GitHub Secrets / OIDC. |
| Hotfix directo en producción sin PR | Sin trazabilidad ni review. | Hotfix branch + PR fast-track con 1 reviewer. |
| Postmortem con culpables | Mata el aprendizaje, oculta problemas a futuro. | Blameless. Foco en proceso/sistema. |
| Documentación que vive en chat | Se pierde, se contradice. | ADR / RFC / README / RUNBOOK en repo. |

---

## 14. Estándares de industria referenciados

| Estándar | Aplicación |
|---|---|
| RFC 2119 / RFC 8174 | Vocabulario MUST/SHOULD/MAY usado en SPEC. |
| RFC 7230, 7231 (HTTP/1.1) y 9110 (HTTP semántico) | Convenciones de headers y métodos. |
| RFC 5322 | Validación de emails. |
| RFC 4122 | UUIDs (preferentemente v4). |
| W3C Trace Context | Propagación de trazas. |
| Conventional Commits 1.0 | Mensajes de commit. |
| SemVer 2.0 | Versionado del contrato y de las apps. |
| Keep a Changelog 1.1 | Formato de CHANGELOG. |
| The Twelve-Factor App | Filosofía base. |
| OWASP Top 10 (2021) | Foco de AppSec en CI. |
| OWASP ASVS 4.0 | Checklist exhaustivo de verificación. |
| NIST SP 800-218 (SSDF) | Marco de desarrollo seguro. |
| SLSA 1.0 (L3 objetivo) | Provenance + firma. |
| Sigstore (Cosign, Fulcio, Rekor) | Firma keyless de imágenes y artefactos. |
| OpenTelemetry | Trazas, métricas, logs unificados. |
| WCAG 2.2 AA | Accesibilidad de UI. |
| OpenAPI 3.1 / GraphQL Spec | Documentación de APIs. |

---

## 15. Cómo este documento se mantiene

- Cambios proponen vía PR contra este archivo.
- Cambios estructurales requieren ADR en `docs/ADR/`.
- Revisión semestral mínima por el equipo de plataforma.
- Cuando una recomendación se vuelva norma (caída de costo / madurez del ecosistema), migrar la cláusula a `APP_HUESPED_SPEC.md` y hacer cross-reference desde acá.

---

## 16. Historial de revisiones

| Versión | Fecha | Cambio |
|---|---|---|
| 1.0.0 | 2026-04-28 | Versión inicial. Cubre 12-factor, repos, GH Actions, supply chain, observabilidad, testing, despliegue, comunicación, performance y a11y. |
