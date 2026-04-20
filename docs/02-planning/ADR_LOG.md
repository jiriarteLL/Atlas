# Architecture Decision Records — Maestro Platform V1

> **Fase:** 02-Planning
> **Proyecto:** PRJ-MAESTRO-V1
> **Fecha base:** 2026-04-16

Este archivo registra las 14 decisiones arquitectónicas clave con contexto, alternativas y consecuencias. Son inmutables salvo una nueva ADR que las supere (ADR-XXX-supersedes-YYY).

---

## ADR-001: Laravel Passport como OAuth2 Server emisor de JWT

- **Estado:** Aceptado
- **Fecha:** 2026-04-16
- **Contexto:** El Maestro debe ser Identity Provider único del ecosistema (no-negociable 1). Necesita emitir JWT, validarlos vía un endpoint de ForwardAuth, soportar refresh tokens, revocación y federación con Microsoft Entra ID.
- **Decisión:** Usar **Laravel Passport 13.x** como OAuth2 server (compatible con Laravel 11/12/13 según Packagist; se usa Laravel 13 — DEC-023).
- **Alternativas consideradas:**
  - `tymon/jwt-auth`: solo JWT, sin OAuth2 server completo; descartada porque no cubre refresh, revocación y OAuth2 flows estándar.
  - **Keycloak** externo: IdP maduro pero añade un servicio más, complica el stack Docker y contradice "monolito modular". Descartada para V1.
  - **Auth0** (SaaS): fuera de control del humano, costo por MAU, dependencia externa con datos sensibles. Descartada.
- **Consecuencias:**
  - ✅ Integración nativa con Laravel 13.
  - ✅ Auditoría del código, sin black-box.
  - ✅ Tablas `oauth_*` en la misma BD del Maestro — simplifica backup.
  - ⚠️ Requiere rotación manual de claves OAuth (no hay rotación automática out-of-the-box).
  - ⚠️ Scope Passport es amplio; se limita a usar solo Password Grant + Authorization Code (Microsoft) + Refresh Grant. Prohibido Client Credentials para usuarios finales.

---

## ADR-002: PostgreSQL 16 como BD del Maestro

- **Estado:** Aceptado
- **Fecha:** 2026-04-16
- **Contexto:** Necesitamos BD del Maestro con: tipos JSON/JSONB (para audit_log `data_before/after`), triggers maduros (audit_log inmutable), UUIDs nativos, réplicas en V2.
- **Decisión:** **PostgreSQL 16 Alpine**.
- **Alternativas:**
  - MySQL 8: JSON sí, triggers sí, pero UUIDs menos ergonómicos; menor adopción en comunidad Laravel/modern stack.
  - MariaDB: variante de MySQL, mismos trade-offs.
  - SQLite: descartada; multi-tenant no escala.
- **Consecuencias:**
  - ✅ JSONB indexable para audit_log.
  - ✅ UUIDs como PK nativos (gen_random_uuid()).
  - ✅ Triggers robustos y procedures para inmutabilidad.
  - ✅ CIS PostgreSQL Benchmark disponible.
  - ⚠️ Laravel migrations requieren nulls explícitos en FK y atención con cascade; se adopta convención de migration reversibles.

---

## ADR-003: Monolito Modular sobre Microservicios

- **Estado:** Aceptado
- **Fecha:** 2026-04-16
- **Contexto:** Escala V1 (DEC-017): 1 empresa × 7 apps × 50 concurrentes. Equipo: humano + Claude Code. Overhead operacional de microservicios (service mesh, tracing distribuido, coordinación) no se justifica.
- **Decisión:** **Monolito modular Laravel** con módulos aislados por frontera de dominio (`app/Modules/Auth|Identity|Catalog|Provisioning|Gateway|Hooks|AuditLog|Platform`).
- **Alternativas:**
  - Microservicios: sobre-ingeniería a V1.
  - Monolito tradicional (sin módulos): harder to extract services en V2.
- **Consecuencias:**
  - ✅ Simple de operar, deploy único, transacciones DB cruzadas cuando hace falta.
  - ✅ Límites de módulo permiten extraer servicios en V2 sin refactor grande (ej: Provisioning como worker independiente).
  - ⚠️ Riesgo de "monolito big ball of mud" si se violan las fronteras. Mitigación: `code-reviewer` transversal verifica imports cross-module en PRs.

---

## ADR-004: Traefik v3 como Reverse Proxy

- **Estado:** Aceptado
- **Fecha:** 2026-04-16
- **Contexto:** Necesitamos reverse proxy con: ForwardAuth middleware nativo, TLS automático (Let's Encrypt), ruteo dinámico basado en Docker labels, rate limiting, headers de seguridad inyectables.
- **Decisión:** **Traefik v3** como edge router.
- **Alternativas:**
  - `nginx` + `oauth2-proxy`: funciona pero dos componentes que mantener y configurar. Más complejo.
  - **Caddy**: ACME nativo y bonito, pero ForwardAuth vía plugin menos maduro.
  - **HAProxy**: rendimiento excepcional pero menor DX para Docker labels.
- **Consecuencias:**
  - ✅ Labels Docker → ruteo automático al levantar nuevas instancias (clave para provisioning dinámico).
  - ✅ ACME HTTP-01 / DNS-01 automático.
  - ✅ `traefik.http.middlewares.forward-auth` nativo.
  - ⚠️ Configuración declarativa en labels puede ser verbosa; se adopta convención de "template de labels" por tipo de instancia documentada en `docs/CONVENCIONES_PLATAFORMA.md`.

---

## ADR-005: Cache Redis para Validación de Tokens — desde V1

- **Estado:** Aceptado
- **Fecha:** 2026-04-16
- **Contexto:** ForwardAuth se invoca en cada request a cualquier app huésped. Objetivo RNF-001 < 50ms p95. Aunque DEC-017 (escala baja) relaja la presión, se mantiene Redis por defensa en profundidad, consistencia futura y porque Laravel Queue también lo necesita.
- **Decisión:** **Redis 7** como cache de validación de tokens (TTL 300s, invalidado al logout/revoke) + queue driver + rate limiting store.
- **Alternativas:**
  - Solo BD: cumple V1 pero agrega latencia y carga.
  - In-memory por proceso: no sirve con múltiples workers.
  - Memcached: perfectamente válido pero Redis es más versátil (pub/sub, lists para queue).
- **Consecuencias:**
  - ✅ Reduce queries a BD ~10x en picos.
  - ✅ Habilita queue driver eficiente para Jobs (health checks, provisioning, hooks).
  - ⚠️ Una dependencia más en el stack. Mitigación: graceful degradation a BD si Redis cae.

---

## ADR-006: Acceso a Docker API vía `docker-socket-proxy` con Allowlist

- **Estado:** Aceptado
- **Fecha:** 2026-04-16
- **Contexto:** El motor de provisioning necesita crear contenedores, redes y BDs via Docker API. Montar `/var/run/docker.sock` directamente en el contenedor del Maestro expone el kernel del host si el Maestro se compromete (R-002, catastrófico).
- **Decisión:** Usar **docker-socket-proxy** (`tecnativa/docker-socket-proxy`) como intermediario, con allowlist explícita de endpoints.
- **Allowlist V1**:
  - `CONTAINERS=1`, `NETWORKS=1`, `EXEC=1`, `INFO=1`, `VERSION=1`, `PING=1`
  - Bloqueado: `BUILD=0`, `COMMIT=0`, `IMAGES=0` (solo pull por nombre), `PLUGINS=0`, `SWARM=0`, `SYSTEM=0`, `VOLUMES_DELETE=0`, `NODES=0`, `SECRETS=0`
- **Alternativas:**
  - Montar socket directo: inaceptable por R-002.
  - Docker rootless: aporta defensa pero aún así se requiere proxy para restringir endpoints.
  - Podman en su lugar: cambio de stack grande; no justificado.
- **Consecuencias:**
  - ✅ Reduce superficie de ataque enormemente.
  - ✅ Compatible con CIS Docker Benchmark.
  - ⚠️ Si un endpoint necesario queda fuera de la allowlist, provisioning falla; se ajusta con ADR-XXX adicional si surge.

---

## ADR-007: Portal React con Iframes y postMessage (no Module Federation)

- **Estado:** Aceptado
- **Fecha:** 2026-04-16
- **Contexto:** El portal debe embeber apps huésped desarrolladas independientemente, posiblemente con stacks distintos (Node, Python, etc.). El premisa lo exige (cada app es containerizable en cualquier lenguaje).
- **Decisión:** **Iframes** con transferencia de auth via `postMessage` al origen.
- **Alternativas:**
  - **Module Federation (Webpack 5)**: elegante pero obliga a las apps huésped a ser SPAs React compilables con Webpack → viola premisa 3 (agnosticismo tecnológico).
  - **Micro-frontends con single-spa**: similar restricción.
- **Consecuencias:**
  - ✅ Apps huésped 100% agnósticas del stack del portal.
  - ✅ Aislamiento de JS sandbox por navegador.
  - ⚠️ UX puede sentirse "pesada" con iframes anidados. Mitigación: transiciones visuales suaves, cold start bien manejado, `sandbox` attribute configurado (permite forms, scripts, same-origin con Maestro domain).
  - ⚠️ `X-Frame-Options` NO debe ser `DENY` para el dominio del Maestro; se usa `CSP frame-ancestors 'self'` para permitir solo self.

---

## ADR-008: Audit Log Inmutable mediante Triggers DB

- **Estado:** Aceptado
- **Fecha:** 2026-04-16
- **Contexto:** No-negociable 9: audit_log inmutable a nivel BD. Cumplir GDPR (DEC-013) y SOC 2 exige evidencia de controles.
- **Decisión:** Tabla `audit_log` con:
  - Columnas: `id BIGSERIAL PK, at TIMESTAMPTZ(6), actor_user_id UUID, actor_ip INET, company_id UUID NULL, action VARCHAR, resource_type VARCHAR, resource_id UUID NULL, data_before JSONB NULL, data_after JSONB NULL`.
  - Triggers BEFORE UPDATE y BEFORE DELETE que ejecutan `RAISE EXCEPTION 'audit_log is INSERT-only'`.
  - Permisos granulares: el user de aplicación `maestro_app` solo tiene INSERT y SELECT sobre `audit_log`.
- **Alternativas:**
  - Event sourcing completo: overengineering para V1.
  - Solo aplicación-layer: insuficiente según no-negociable 9 (debe ser nivel BD).
- **Consecuencias:**
  - ✅ Cumplimiento verificable (tests de integración intentan UPDATE/DELETE y esperan excepción).
  - ✅ Retención GDPR: purga por fecha antigua permitida vía usuario `maestro_purger` con rol especial, operación registrada ella misma.
  - ⚠️ Migraciones Laravel necesitan SQL raw para crear triggers; se aceptan como migraciones "manuales" con documentación.

---

## ADR-009: GitHub Actions como CI/CD

- **Estado:** Aceptado
- **Fecha:** 2026-04-16
- **Contexto:** Repo está en GitHub (org LLyAsoc-Digital). CI/CD debe: correr tests, lint, scan secretos (gitleaks), scan vulnerabilidades (trivy), build imagen Docker, publicar imagen al registry, validar contratos maestro.yaml de apps huésped.
- **Decisión:** **GitHub Actions**. Workflows en `.github/workflows/`:
  - `ci.yml`: push a cualquier rama → lint + tests + scan.
  - `release.yml`: tag `v*` → build + push imagen a ghcr.io + generar changelog.
  - `app-register.yml`: template para repos de apps huésped (fase 5).
- **Alternativas:**
  - GitLab CI: cambiar de plataforma no justificado.
  - Jenkins auto-hosted: infra extra no deseada.
- **Consecuencias:**
  - ✅ Integración natural con el repo.
  - ✅ `ghcr.io` (GitHub Container Registry) como registry V1 (privado).
  - ⚠️ ESC-003: desde el framework no podemos operar Actions/Issues por restricción del PAT. Los workflows se commitean y el humano/ci los ejecuta. No bloqueante V1.

---

## ADR-010: @maestro/sdk-node como Primer SDK

- **Estado:** Aceptado
- **Fecha:** 2026-04-16
- **Contexto:** DEC-010 y plan de la premisa (fase 5) fijan Node.js como primer SDK.
- **Decisión:** Paquete npm **`@maestro/sdk-node`** con:
  - Middleware Express/Fastify que lee headers X-Auth-* y popula `req.user`.
  - Filtro automático de tenant: wrapper de Prisma/Knex/Sequelize que agrega `WHERE company_id = $1` a todas las queries.
  - Helpers de RBAC: `req.user.hasRole('admin')`, `req.user.hasPermission('reports:view')`.
  - Verificación HMAC de hooks entrantes.
  - Cliente del API Gateway: `maestro.gateway('app-destino').post('/ruta', body)`.
- **Alternativas:**
  - No publicar SDK V1: las apps huésped tendrían que implementar todo a mano; alto riesgo de bugs de multi-tenant.
  - Publicar solo docs/ejemplos: mismo problema.
- **Consecuencias:**
  - ✅ Cumplimiento del contrato garantizado por construcción.
  - ⚠️ SDK debe versionarse con SemVer estricto; cualquier breaking change implica bump mayor y comunicación a devs de apps huésped.

---

## ADR-011: Convenciones Docker Documentadas en `docs/CONVENCIONES_PLATAFORMA.md`

- **Estado:** Aceptado
- **Fecha:** 2026-04-16
- **Contexto:** DEC-012: zero local installs. DEL-001: documento obligatorio con convenciones para evitar colisiones entre Maestro y apps huésped.
- **Decisión:** Producir `docs/CONVENCIONES_PLATAFORMA.md` en esta fase con:
  - **Naming de contenedores**: `maestro-<servicio>` para core; `app-<app_slug>-<company_slug>-<servicio>` para instancias.
  - **Naming de redes Docker**: `maestro-network` (core), `app-<app_slug>-<company_slug>-net` (instancias).
  - **Naming de volúmenes**: `maestro-<recurso>-data` (core), `app-<app_slug>-<company_slug>-db-data` (instancia).
  - **Puertos externos**: solo 80 y 443 (Traefik). Nada más expuesto al host.
  - **Puertos internos**: >= 1024 por contrato (RNF). Maestro = 8080; apps = declarado en maestro.yaml.
  - **Subdominios**: `maestro.<MAESTRO_BASE_DOMAIN>` para el portal, `<app_slug>-<company_slug>.<MAESTRO_BASE_DOMAIN>` para instancias.
  - **Env vars reservadas del Maestro** (apps no las deben usar): `MAESTRO_*`, `X_AUTH_*`, `DATABASE_URL` (inyectada).
- **Alternativas:** documentar ad-hoc por PR: invita a inconsistencias.
- **Consecuencias:**
  - ✅ Apps huésped se integran sin coordinar con el equipo Maestro.
  - ✅ Base para generación automática de labels Traefik en provisioning.

---

## ADR-012: Zero Local Installs vía `docker compose run --rm`

- **Estado:** Aceptado (refuerzo de DEC-012)
- **Fecha:** 2026-04-16
- **Contexto:** DEC-012 exige portabilidad total; no se instala PHP/Node/psql/composer en host.
- **Decisión:** `docker-compose.dev.yml` en la raíz define servicios:
  - `maestro-php`: imagen `maestro-php:dev`, workdir `/app`, mount del repo, comando default `php-fpm`.
  - `maestro-node`: imagen `maestro-node:dev`, workdir `/app/portal`, mount del repo, comando default `npm run dev`.
  - Todos los comandos de toolchain se invocan: `docker compose run --rm maestro-php composer install`, `docker compose run --rm maestro-php php artisan migrate`, `docker compose run --rm maestro-node npm install`, etc.
  - Un `justfile` o `Makefile` provee atajos: `just install`, `just migrate`, `just test`, `just portal-dev`.
- **Alternativas:** ya evaluadas en DEC-012.
- **Consecuencias:**
  - ✅ Dev clona → `docker compose up -d` → funciona.
  - ⚠️ Primera ejecución lenta (pull de imágenes). Mitigación: CI precachea imágenes en GHCR.

---

## ADR-013: Trunk-Based Git + Conventional Commits

- **Estado:** Aceptado
- **Fecha:** 2026-04-16
- **Contexto:** Equipo chico (humano + Claude). Feature branches largas son innecesarias. Necesitamos auditabilidad de cambios y auto-generación de changelogs para releases (fase 4).
- **Decisión:**
  - Rama principal `master` protegida (PR obligatorio + 1 review + CI green).
  - Feature branches cortas (<3 días).
  - Conventional Commits obligatorio en `master`.
  - Tags de release `v<SEMVER>` para disparar `release.yml`.
- **Alternativas:**
  - Git Flow completo: pesado para el tamaño del equipo.
  - Commits libres: no auditables.
- **Consecuencias:**
  - ✅ Changelog automático a partir de conventional commits (`conventional-changelog`).
  - ✅ Reducción de conflict merges por branches largas.
  - ⚠️ Requiere disciplina; se configura commitlint como pre-commit hook (local) + lint en CI.

---

## ADR-014: Framework No Despliega al VPS; Solo Produce Artefactos (refuerzo DEC-011)

- **Estado:** Aceptado
- **Fecha:** 2026-04-16
- **Contexto:** DEC-011 decreta que el VPS Azure lo opera el humano fuera del framework. El framework genera: Dockerfile, docker-compose.staging.yml, docker-compose.prod.yml, scripts `scripts/deploy.sh`, documentación `docs/04-delivery/DEPLOY_GUIDE.md`.
- **Decisión:** No IaC (Terraform/Pulumi) V1. El humano mantiene el VPS con `docker compose pull && docker compose up -d` ejecutado manualmente.
- **Alternativas:**
  - IaC completo (Terraform + Azure): valor real, pero out of scope V1.
  - GitHub Actions con self-hosted runner en VPS: ampliaría la superficie de seguridad (runner con credenciales de deploy). Diferible.
- **Consecuencias:**
  - ✅ Separación de responsabilidades clara: framework construye, humano opera.
  - ⚠️ Deploys son manuales, error humano posible. Mitigación: scripts idempotentes, checklist de release (fase 4, release-manager).
  - ⚠️ ESC-003 reforzada: mientras no haya acceso a GitHub desde el framework, cualquier auto-deploy queda vetado igualmente.

---

## Resumen y trazabilidad

| ADR | Módulo/capa impactada | Requisito asociado |
|---|---|---|
| ADR-001 | Auth | RF-001–RF-006, RNF-020 |
| ADR-002 | Data layer | RNF-002, RNF-017 |
| ADR-003 | Toda la aplicación | escala V1, mantenibilidad |
| ADR-004 | Perimeter/infra | RF-040–RF-044, RNF-010, RNF-011 |
| ADR-005 | Auth + Infra | RNF-001, RNF-002, RNF-003 |
| ADR-006 | Provisioning + Security | R-002, RNF-010 |
| ADR-007 | Portal/Frontend | RF-050–RF-056 |
| ADR-008 | AuditLog | RF-020, RF-021, RNF-017, GDPR (DEC-013) |
| ADR-009 | CI/CD | RF-070–RF-072 |
| ADR-010 | SDK | RF-062, RF-063 |
| ADR-011 | Convenciones | DEL-001, coexistencia apps |
| ADR-012 | DX/infra local | DEC-012, RNF-040–RNF-043 |
| ADR-013 | Governance | RF-072 |
| ADR-014 | Delivery | DEC-011 |
