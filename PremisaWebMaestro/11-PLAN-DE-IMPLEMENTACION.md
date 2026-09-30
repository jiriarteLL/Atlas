# Plan de Implementación por Fases

> **Versión:** v4 (framework agéntico v4 / contrato `maestro.platform/v2`)
> **Última revisión:** 2026-05-07
> **Estado:** vigente
> **Reemplaza a:** `legacy/v3/PremisaWebMaestro/11-PLAN-DE-IMPLEMENTACION.md` (modelo v1).

---

## Propósito de este documento

Este documento establece las **fases de construcción** de la **Web Maestro** v4 ordenadas cronológicamente. Cada fase tiene sus dependencias, entregables concretos, criterios de aceptación y estimación de duración. Un agente que asista en la planificación o ejecución del proyecto debe seguir este orden porque cada fase construye sobre los cimientos de la anterior.

Este plan se ejecuta a través del **framework agéntico v4** con el preset `maestro-platform` activo (ver `07-SISTEMA-AGENTICO.md`). Las 8 fases del framework (00-setup → 07-retrospective) corresponden directamente con las del plan, adaptadas al contexto del proyecto Web Maestro.

---

## Principios del plan

### 1. Construir sobre lo construido

Cada fase **DEBE** completar sus exit criteria antes de iniciar la siguiente. Saltarse una fase introduce deuda técnica que se paga cara.

### 2. Validación transversal continua

Después de cada entregable significativo, el orquestador lanza los 5 validadores transversales mínimos en paralelo (`code-reviewer`, `security-auditor`, `qa-tester`, `performance-analyst`, `compliance-analyst`). Sin todos PASS, no se mergea.

### 3. Decisiones documentadas como ADR

Cada decisión arquitectónica importante queda como **Architecture Decision Record** con: contexto, decisión, alternativas consideradas, consecuencias.

### 4. Iteración explícita

Si los validadores rechazan, hay máximo 3 reintentos por módulo. Tras 3, se escala al PM y eventualmente al PO.

### 5. Persistencia y reversibilidad

Los datos de la BD del Maestro persisten entre versiones (ver No-negociable 14). Las migraciones de schema son expand-then-contract. Las acciones destructivas requieren confirmación explícita del PO.

---

## Fase 00 — Setup (≈ 1-2 días)

### Objetivo
Verificar que el equipo tiene un entorno de desarrollo funcional para el proyecto Web Maestro.

### Pre-requisitos
- Repo del Maestro creado (privado, propiedad del equipo de plataforma).
- GitHub Issues habilitados.
- Acceso del equipo al repo confirmado.

### Entregables
- Verificación de Docker, Docker Compose, git, IDE en cada dev.
- Confirmación de que NO hay PHP/Node/psql instalados en el host (todo via contenedores).
- `docker-compose.dev.yml` inicial que arranca un stack mínimo para validar el setup.
- Checkpoint en `framework-agentico/projects/<id>/branches/<rama>/phases/00-setup.md`.

### Exit criteria
- Cada dev del equipo ejecuta `docker compose run --rm maestro-api npm install` (o equivalente) sin errores.
- Verificación de acceso al repo y a las herramientas externas (registries de imágenes, observabilidad).

---

## Fase 01 — Discovery (≈ 1-2 semanas)

### Objetivo
Entender completamente qué se va a construir y bajo qué restricciones.

### Pre-requisitos
- Fase 00 completa.
- Premisa del proyecto leída por todo el equipo (este conjunto de documentos `PremisaWebMaestro/`).

### Entregables
- `phases/01-requirements.md` con requisitos funcionales (priorización MoSCoW) y no-funcionales (perf, seguridad, disponibilidad).
- `phases/01-glossary.md` con términos del dominio (companies, applications, deployments, api_keys, webhook_secrets, audit_log, admin_users, etc.) y sinónimos del PO.
- `phases/01-research.md` (si aplica): investigación de regulaciones (GDPR, LGPD, ISO 27001, SOC 2 según mercado).
- GitHub Milestone creado.

### Exit criteria
- Requisitos funcionales documentados con MoSCoW.
- Requisitos no funcionales: latencia de redirección < 200ms, provisioning < 60s, branding fetch (con cache) < 50ms, hooks success rate ≥ 99%.
- Criterios de aceptación para cada requisito.
- Glosario completo (incluyendo los sinónimos del PO según `framework-agentico/core/RULES.md` sección `glosario_de_sinonimos`).
- Regulaciones aplicables identificadas.
- Las 14 no-negociables y 10 premisas (`01-PREMISAS-Y-NO-NEGOCIABLES.md`) marcadas como **MUST** en el backlog.

---

## Fase 02 — Planning (≈ 2-3 semanas)

### Objetivo
Tomar todas las decisiones técnicas de diseño antes de escribir código.

### Pre-requisitos
- Fase 01 completa.

### Entregables

**ADRs obligatorios** (cada uno como archivo en `phases/02-adr-*.md`):
- ADR-001: Stack tecnológico (recomendación: Laravel + React + PostgreSQL + Redis).
- ADR-002: Estrategia de cifrado AES-256 para api_keys, webhook_secrets, password_hash.
- ADR-003: Estrategia de provisioning (Docker API directa vs ansible vs cloud-specific).
- ADR-004: Reverse proxy (Traefik con TLS Let's Encrypt; sin ForwardAuth).
- ADR-005: Estrategia de redes Docker por deployment.
- ADR-006: BD del Maestro (PostgreSQL recomendado por triggers SQL nativos).
- ADR-007: Comunicación inter-apps via API Gateway del Maestro (no directa).
- ADR-008: Política de retención (backups 30d, deployments destruidos 90d).
- ADR-009: Implementación de MFA para `superadmin` (sí/no, qué método).

**Modelo de datos**:
- `phases/02-data-model.md` con todas las tablas según `02-MODELO-DE-DATOS.md`.
- Diagrama ER (puede ser ASCII o Mermaid).
- Migraciones planeadas (no implementadas todavía).

**Contratos de API**:
- `phases/02-api-contracts.md` con OpenAPI/Swagger spec de:
  - `/api/v2/auth/*` (login, logout, refresh, me, password-change).
  - `/api/v2/companies` (CRUD).
  - `/api/v2/applications` (read-only para admins; mutación via `/api/v2/apps/register`).
  - `/api/v2/deployments` (CRUD + lifecycle: provision, suspend, destroy, purge, restore, rotate-api-key, rotate-webhook-secret).
  - `/api/v2/branding/*` (read, force-refresh).
  - `/api/v2/audit_log` (read).
  - `/api/v2/admins` (CRUD).
  - `/api/v2/apps/register` (POST de auto-registro).
  - `/api/v2/portal/my-apps` (consumido por apps huésped).
  - `/api/v2/gateway/<app>/<path>` (gateway inter-apps).
  - `/health`.

**UX del portal**:
- `phases/02-ui-flows.md` con flujos: login, dashboard, gestión de empresas, gestión de deployments, audit log viewer.
- Wireframes (Figma, Excalidraw, o equivalente).
- Decisión sobre Tailwise (preferido pero no obligatorio; ver premisa 4 y `framework-agentico/core/RULES.md` sección `plantilla_base`).

**Threat model**:
- `phases/02-threat-model.md` con las 16 amenazas listadas en `09-SEGURIDAD.md` y sus mitigaciones.

**Plan de seeding**:
- `phases/02-seeding-plan.md` con superadmin del Maestro (`admin@llyasoc.com`) + admins adicionales si aplica.

**Convenciones**:
- Actualización de `docs/CONVENCIONES_PLATAFORMA.md` para v4 (naming canónico, env vars, puertos, redes Docker).

**Issues por módulo**:
- GitHub Milestone con issues, una por módulo o feature implementable independientemente. Cada issue con su issue branch.

### Exit criteria
- Todos los ADRs aprobados.
- Modelo de datos coherente con `02-MODELO-DE-DATOS.md`.
- Contratos de API revisados por el equipo.
- Threat model validado por security architect.
- Plan de seeding aprobado por el PO.
- Milestone con issues desglosados.

---

## Fase 03 — Development (≈ 2-3 meses, depende de la complejidad)

### Objetivo
Construir el sistema módulo por módulo con validación transversal continua.

### Pre-requisitos
- Fase 02 completa.

### Estrategia de módulos

Implementar en orden recomendado:

**Sprint 1: Fundación**
- Setup del proyecto Laravel/Node/Python según ADR-001.
- Migraciones iniciales (companies, applications, admin_users, admin_roles, admin_permissions, audit_log con triggers).
- Cifrado AES-256 helper.
- Login propio del Maestro para admins.
- Rol `superadmin` y middleware de auth.

**Sprint 2: Catálogo (registry)**
- CRUD de `companies`.
- CRUD de `applications` (read-only para admins, write via `/api/v2/apps/register`).
- Endpoint `/api/v2/apps/register` con validación contra JSON Schema v2.
- Token de registro por owner.

**Sprint 3: Deployments — capa de datos**
- Tabla `deployments` con constraint UNIQUE parcial.
- Tabla `api_keys`, `webhook_secrets` con cifrado.
- Endpoints CRUD para gestión.

**Sprint 4: Provisioner**
- Servicio de provisioning que consume Docker API.
- Generación de redes Docker dedicadas.
- Generación de credenciales aleatorias.
- Inyección de ENV vars al levantar contenedor.
- Ejecución de migrations + seeders.
- Esperar health check.
- Idempotencia y rollback en fallo.

**Sprint 5: Salud y branding**
- Job periódico de health checks.
- Máquina de estados con acciones correctivas escalonadas.
- Job periódico de fetch de `/maestro/branding`.
- Cache en `branding_cache`.

**Sprint 6: Hooks salientes**
- Worker de envío de hooks con HMAC-SHA256.
- Reintentos con backoff exponencial.
- Idempotencia por `event_id`.
- Tabla `hooks_log`.

**Sprint 7: Portal admin (frontend)**
- Login del portal.
- Dashboards (ejecutivo, deployments, audit log).
- CRUD de empresas, deployments.
- Vista de detalle del deployment con click `target="_blank"`.
- Tailwise React (recomendado).

**Sprint 8: CLI y schema**
- `maestro-cli validate` (v2).
- `maestro-cli new` (template para apps).
- Publicación de `maestro.yaml.schema.v2.json`.

**Sprint 9: API Gateway inter-apps (opcional MVP)**
- Si el alcance del MVP lo requiere; sino, posterior.

### Validación transversal por sprint

Después de cada sprint:
- Lanzar 5 validadores en paralelo: `code-reviewer`, `security-auditor`, `qa-tester`, `performance-analyst`, `compliance-analyst`.
- Adicional para módulos críticos (auth, provisioner, secretos): validadores en `opus`.
- Sin todos PASS, no se mergea el sprint a la epic branch.

### Exit criteria de la fase 03
- Todos los sprints completos y mergeados.
- Tests unitarios y de integración pasando.
- Sin vulnerabilidades CRITICAL/HIGH abiertas.
- Cobertura mínima recomendada: 80% statements, 70% branches.
- Convenciones de código cumplidas.
- Issues cerrados en GitHub.

---

## Fase 04 — Delivery (≈ 1-2 semanas)

### Objetivo
Empaquetar, configurar CI/CD y preparar el sistema para deployment al VPS.

### Entregables
- Dockerfile multi-stage del Maestro, non-root, con HEALTHCHECK.
- `docker-compose.yml` con Traefik + Maestro API + Maestro DB + Redis (opcional) + observabilidad.
- `docker-compose.dev.yml` para entorno local.
- Pipeline CI/CD en `.github/workflows/` (validate, security, build, integration_tests, register).
- Configuración Traefik: TLS Let's Encrypt, redirect HTTP→HTTPS, HSTS, rate limiting (sin ForwardAuth).
- Branch protection en `main`.
- Scripts de deployment a VPS (`scripts/deploy.sh` o equivalente). El VPS lo gestiona el humano.
- ENV vars obligatorias documentadas en `.env.example`: `DATABASE_URL`, `MAESTRO_ENCRYPTION_KEY`, `JWT_SECRET`, `SUPERADMIN_INITIAL_PASSWORD`.

### Exit criteria
- `docker compose up -d` levanta el stack completo localmente.
- CI corre verde en main.
- Smoke tests pasan post-deploy.
- Documentación de deployment lista en `docs/deployment.md`.

---

## Fase 05 — Seeding (≈ 2-3 días)

### Objetivo
Garantizar que el Maestro arranca con un superadmin operativo en cada deployment.

### Entregables
- Seeder idempotente del superadmin (`admin@llyasoc.com`).
- Lectura de `SUPERADMIN_INITIAL_PASSWORD` con validación de fortaleza.
- Creación/verificación de rol `superadmin` con todos los permisos.
- Hook en pipeline de deploy: `docker compose exec maestro-api <cmd_seed>` post-migrations.
- Tests del seeder (no seteo, password débil, primer run, segundo run, asignación de rol faltante, login exitoso).

### Exit criteria
- El seeder cumple las reglas de `framework-agentico/phases/05-seeding.md`.
- Re-ejecutar el seeder NO duplica datos ni cambia password existente.
- Login del superadmin funciona post-deploy.
- Logs sin password ni hash.

---

## Fase 06 — Operations (≈ 1-2 semanas)

### Objetivo
Preparar el sistema para operar en producción con observabilidad y protocolos de respuesta.

### Entregables
- Stack de observabilidad desplegado: Prometheus, Loki, Grafana, alertmanager.
- Dashboards (6 dashboards mínimos según `10-OBSERVABILIDAD.md`).
- Reglas de alerta provisioned en Prometheus.
- Runbooks operativos (12 mínimos según `10-OBSERVABILIDAD.md`).
- Audit log centralizado y consultable desde el portal.
- Política de backups operativa: cron diario, cifrado, externo al VPS, retención ≥ 30 días.
- Logs estructurados JSON con `request_id`, `deployment_id`, `actor_user_id` (sin `company_id`).
- Documentación de tech debt en `docs/tech-debt.md`.

### Exit criteria
- Métricas clave alimentando Grafana.
- Alertas críticas configuradas y probadas.
- Al menos un backup diario ejecutado y verificado.
- Runbooks revisados con el equipo.

---

## Fase 07 — Retrospective (≈ 3-5 días)

### Objetivo
Cerrar el proyecto con retrospectiva, documentación consolidada y mejora continua.

### Entregables
- `docs/retrospective.md` con: qué funcionó, qué no, qué mejorar.
- `docs/final-report.md` con reporte ejecutivo (premisa, alcance, métricas, costos del proyecto).
- README del proyecto actualizado.
- Índice maestro de documentación.
- Lecciones aprendidas registradas en memoria del framework agéntico (si aplican a futuros proyectos).

### Exit criteria
- Retrospectiva completada.
- Reporte ejecutivo entregado al PO.
- Documentación final consolidada.
- PR final epic → main aprobado y mergeado **por el PM** (ver `framework-agentico/core/RULES.md` sección `git_workflow.permisos_de_merge`).
- Proyecto marcado `completed` en `framework-agentico/projects/<id>/PROJECT.md` y en `framework-agentico/checkpoints/GLOBAL.md`.
- Transacciones compactadas (`COMPACTED_TRANSACTIONS.md` por rama).

---

## Estimación total

| Fase | Duración estimada |
|---|---|
| 00 — Setup | 1-2 días |
| 01 — Discovery | 1-2 semanas |
| 02 — Planning | 2-3 semanas |
| 03 — Development | 2-3 meses |
| 04 — Delivery | 1-2 semanas |
| 05 — Seeding | 2-3 días |
| 06 — Operations | 1-2 semanas |
| 07 — Retrospective | 3-5 días |
| **Total** | **~4-5 meses** |

Estimación para un equipo de 2-3 devs full-time + 1 PM/PO + soporte de agentes IA. Ajustar según realidad del equipo.

---

## Dependencias entre fases

```
00-setup ──→ 01-discovery ──→ 02-planning ──→ 03-development ──→ 04-delivery ──→ 05-seeding ──→ 06-operations ──→ 07-retrospective
```

- Cada fase depende estrictamente de la anterior.
- 05-seeding puede solaparse parcialmente con 04-delivery (el seeder se desarrolla durante delivery, se prueba en una fase dedicada).
- 06-operations puede iniciar la observabilidad en paralelo durante 04-delivery (instrumentación de métricas en código).

---

## Hitos de revisión con el PO

Recomendados:

- **Post-01**: revisión de requisitos.
- **Post-02**: revisión de ADRs y modelo de datos.
- **Post-Sprint 1, 4, 7 (durante 03)**: demos parciales.
- **Post-04**: review de la imagen Docker y CI/CD.
- **Post-06**: walkthrough de dashboards y runbooks.
- **Post-07**: presentación del reporte ejecutivo.

---

## Riesgos y mitigaciones

| Riesgo | Probabilidad | Impacto | Mitigación |
|---|---|---|---|
| Underestimación de complejidad del provisioner | Media | Alto | Spike técnico en 02 con prototipo de Docker API directa |
| Cambios de regulación (GDPR/SOC) durante el proyecto | Baja | Medio | Reunión trimestral con compliance-analyst |
| Compromiso de credenciales en CI | Baja | Alto | gitleaks + cosign desde 04-delivery |
| Rotación de equipo durante 03-development | Media | Medio | Documentación obligatoria por sprint, ADRs actualizados |
| Dependencias upstream (Tailwise, Traefik) con vulnerabilidades | Media | Medio | Updates regulares, trivy scan en CI |
| Performance del provisioning peor que objetivo (60s) | Baja | Bajo | Profiling early; cache de imágenes Docker en el VPS |

---

## Criterios de éxito del proyecto

Al cierre del proyecto:

1. ✅ La Web Maestro está desplegada en el VPS y accesible vía HTTPS.
2. ✅ El superadmin (`admin@llyasoc.com`) puede loguearse en el portal.
3. ✅ Una app huésped puede registrarse exitosamente vía `POST /api/v2/apps/register`.
4. ✅ Un admin puede provisionar un deployment de la app para una empresa, y la app queda accesible en su URL pública.
5. ✅ El click en la app desde el portal abre la URL en `target="_blank"` y la app pide login propio.
6. ✅ El deployment responde a `/maestro/branding` correctamente y el branding se cachea.
7. ✅ Los hooks salientes funcionan: el Maestro envía `on_user_added` y la app valida la firma HMAC.
8. ✅ Los dashboards muestran métricas reales del Maestro y los deployments.
9. ✅ Las alertas críticas se disparan correctamente en simulación.
10. ✅ El backup diario corre y se almacena externo al VPS.
11. ✅ El audit log captura todas las operaciones administrativas y es inmutable.
12. ✅ Los runbooks resuelven los 12 escenarios documentados.

---

## Referencias normativas

- `01-PREMISAS-Y-NO-NEGOCIABLES.md` — base constitucional.
- `02-MODELO-DE-DATOS.md` — schema a implementar.
- `03-AUTENTICACION-Y-AUTORIZACION.md` — endpoints de auth a construir.
- `04-INFRAESTRUCTURA-DOCKER.md` — provisioning a implementar.
- `05-PORTAL-Y-RENDERIZADO.md` — frontend a construir.
- `06-CONTRATO-MAESTRO-YAML.md` — JSON Schema a publicar y endpoint de registro.
- `07-SISTEMA-AGENTICO.md` — cómo el framework agéntico v4 ejecuta este plan.
- `08-CICD-Y-GOBERNANZA.md` — pipelines a configurar.
- `09-SEGURIDAD.md` — threat model a mitigar.
- `10-OBSERVABILIDAD.md` — stack y métricas a implementar.
- `framework-agentico/phases/00-setup.md` … `07-retrospective.md` — templates operativos del framework.
- `framework-agentico/agents/presets/maestro-platform/PRESET.md` — preset activo durante este proyecto.

---

## Historial de revisiones

| Versión | Fecha | Cambio |
|---|---|---|
| 4.0.0 | 2026-05-07 | Versión inicial v4. Plan alineado al modelo registry+redirector+provisioner del Maestro v4. 8 fases con dependencias, entregables, exit criteria y estimaciones. Reemplaza al v1 (legacy en `legacy/v3/PremisaWebMaestro/11-PLAN-DE-IMPLEMENTACION.md`). |
