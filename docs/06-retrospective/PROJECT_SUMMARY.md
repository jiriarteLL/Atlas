# PROJECT_SUMMARY.md — Maestro Platform V1

> **Fase:** 06-retrospective
> **Versión:** v1.0.0-rc.1 (lista para despliegue VPS)
> **Fecha:** 2026-04-18

---

## 1. Visión general

**Maestro Platform** es una plataforma multi-tenant de clase empresarial que aloja, orquesta y gobierna múltiples aplicaciones dockerizadas ("apps huésped") bajo un portal web unificado con autenticación centralizada.

| Para quién | Empresas (tenants) que operan una suite interna de aplicaciones web heterogéneas. |
|---|---|
| Qué resuelve | Autenticación única, aislamiento multi-tenant por red Docker + DB dedicada, enrutamiento via Traefik ForwardAuth, licenciamiento por empresa/app/usuario, audit log inmutable, observabilidad centralizada, despliegue/CI-CD estandarizado y SDK/CLI para apps huésped. |
| Escala inicial V1 | 1 empresa tenant × 7 apps huésped × 50 usuarios concurrentes (DEC-017). Arquitectura preparada para crecimiento. |
| Fuera de alcance V1 (documentado) | WCAG 2.1 AA (DEC-015), MFA propio TOTP (DEC-016), idiomas no-español (DEC-014), pricing/billing complejo (DEC-018), SLA de soporte integrado (DEC-021), zero-downtime (DEC-020). |

---

## 2. Stack tecnológico

| Capa | Elección | ADR |
|---|---|---|
| Lenguaje backend | PHP 8.3+ | ADR-001 |
| Framework backend | Laravel 13.x | ADR-001, DEC-023 |
| Auth (IdP propio) | Laravel Passport 13.x (OAuth2 Password Grant + PAT) | ADR-002 |
| Auth externo | Microsoft Entra ID via socialite (removido en Laravel 13, reimplementado ad-hoc) | ADR-002 |
| DB Maestro | PostgreSQL 16 (UUID PKs, JSONB, triggers INSERT-only) | ADR-003 |
| Cache / Queue | Redis 7 | ADR-004 |
| Frontend | React 18 + Vite + Tailwind CSS (template Tailwise React v1.0.9) | ADR-005, DEC-009 |
| Reverse proxy | Traefik v3.5 + ForwardAuth + Let's Encrypt | ADR-006 |
| Carga de apps huésped | iframe + postMessage (no micro-frontends) | ADR-007 |
| Orquestación | docker-compose (dev + prod) + docker-socket-proxy (EXEC=0, BUILD=0) | ADR-008 |
| CI/CD | GitHub Actions + GHCR + Trivy CRITICAL/HIGH bloqueante | ADR-009 |
| Observabilidad | Prometheus + cAdvisor + node-exporter + Loki + Promtail + Grafana | ADR-010 |
| Backups | `pg_dump | gzip | AES-256-CBC` → Azure Blob o local, cifrado en reposo | ADR-011 |
| SDK | Node.js (`@maestro/sdk-node`) | ADR-012, DEC-010 |
| CLI | `maestro-cli` (Node.js) con comandos `validate`, `new` | ADR-013 |
| Hooks salientes | HMAC-SHA256 con retry 1s → 10min, dead-letter | ADR-014 |

---

## 3. Arquitectura (resumen)

```
                  ┌─────────────────────────────────────────────┐
                  │                   Internet                   │
                  └──────────────────────┬──────────────────────┘
                                         │ 443
                  ┌──────────────────────▼──────────────────────┐
                  │  Traefik v3.5 — ForwardAuth + ACME Let's    │
                  │  Encrypt + security-headers + rate-limit    │
                  └─┬─────────────────────────────────────────┬─┘
                    │ ForwardAuth middleware                   │
                    ▼                                          │
       ┌────────────────────────┐                              │
       │  Maestro API (3×)      │                              │
       │  Laravel 13 + Passport │◀── JWT emit/validate         │
       │  /oauth/*              │                              │
       │  /api/auth/*           │                              │
       │  /api/admin/*          │                              │
       │  /api/platform/*       │                              │
       │  /api/instances/*      │                              │
       │  /api/gateway/*        │                              │
       │  /api/portal/*         │                              │
       └───┬────────────────────┘                              │
           │                                                   │
           ▼                                                   ▼
  ┌────────────────┐    ┌─────────────┐    ┌──────────────────────────────┐
  │ PostgreSQL 16  │    │ Redis 7     │    │ App huésped N (iframe)       │
  │ (Maestro DB)   │    │ (queue+kv)  │    │ red Docker privada dedicada  │
  │ audit_log      │    └─────────────┘    │ DB dedicada (contenedor)     │
  │ INSERT-only    │                        │ Labels Traefik ForwardAuth   │
  └────────────────┘                        └──────────────────────────────┘

  Docker socket → docker-socket-proxy (POST=1, IMAGES=1, EXEC=0, BUILD=0)
  Workers: maestro-worker (HookDispatcher, Provisioner, HealthCheck) + maestro-scheduler
  Observabilidad: Prometheus ← cAdvisor + node-exporter + /metrics pendiente (TD-015)
                  Loki ← Promtail ← /var/lib/docker/containers (line-based, TD-011 → JSON)
                  Grafana ← dashboards provisionados, ForwardAuth Maestro
```

### Módulos del Laravel (monolito modular)
- `app/Modules/Auth` — login user/pass, refresh, logout, `/auth/me`, `/auth/validate`.
- `app/Modules/Identity` — users, companies, roles, permissions, pivots M-M.
- `app/Modules/Catalog` — applications, licencias por company/user (`application_company`, `application_user`).
- `app/Modules/Provisioning` — `AppInstance`, `ProvisioningEngine`, jobs lifecycle (Provision, HealthCheck, PurgeDestroyed).
- `app/Modules/Gateway` — `GatewayController` proxy entre apps con verificación de permisos + licencia + HMAC + audit.
- `app/Modules/Hooks` — `HookDispatcher`, `DeliverHookJob`, HMAC-SHA256 retry 1s-10min.
- `app/Modules/AuditLog` — `AuditLogger`, `audit_log` INSERT-only con triggers DB.
- `app/Modules/Platform` — `/v1/inventory/context`, `/v1/apps/register` para SDK de apps huésped.

---

## 4. Épicas implementadas (14/14)

| ID | Épica | Estado | Deliverables clave |
|---|---|---|---|
| A | Auth IdP único (Passport OAuth2 + Entra ID) | ✅ | `/oauth/token`, `/api/auth/*`, ForwardAuth ready |
| B | ABM Companies + M-M users | ✅ | `/api/admin/companies`, `company_user` pivot |
| C | ABM Users + roles + permissions | ✅ | `/api/admin/users`, roles/permissions |
| D | Provisioning engine (Docker API) | ✅ | `ProvisioningEngine`, 4 jobs + scheduler, E2E nginx-test |
| E | ABM Applications | ✅ | `/api/admin/applications`, `application_company/user` |
| F | Portal React + admin pages + my-apps | ✅ | 5 admin pages + iframe app loader + postMessage |
| G | Contrato `maestro.yaml` + SDK Node + CLI | ✅ | JSON Schema, `@maestro/sdk-node`, `maestro-cli validate` / `new` |
| H | CI/CD release pipeline | ✅ | `.github/workflows/release.yml` (tag v* → GHCR → Trivy) |
| I | Gateway inter-app | ✅ | `GatewayController` con auth + licencia + HMAC + audit |
| J | Hooks salientes HMAC | ✅ | `HookDispatcher`, retry 1s-10min, integración con ABM |
| K | Observabilidad | ✅ | Prometheus + cAdvisor + Loki + Promtail + Grafana + dashboard Maestro Overview |
| L | Backups cifrados | ✅ | `BackupService` (`pg_dump|gzip|AES-256-CBC → Azure Blob o local`) + daily schedule |
| M | Audit log inmutable | ✅ | `audit_log` INSERT-only + triggers DB + `/api/admin/audit-log` |
| Platform | Endpoints de plataforma para apps huésped | ✅ | `/v1/inventory/context`, `/v1/apps/register` |

---

## 5. Documentación generada

### Raíz del repo
- `CLAUDE.md` — contexto del framework agentico (versión 1.0.0).
- `README.md` — quickstart + convenciones.
- `CHANGELOG.md` — v1.0.0-rc.1 con 14 épicas + Platform.
- `docker-compose.dev.yml` + `docker-compose.prod.yml` + `docker-compose.obs.yml`.
- `.env.example` + `.env.production.example`.

### Por fase (`docs/`)
- **00-setup:** implícito en `CLAUDE.md` y `README.md`.
- **01-discovery:**
  - `RESEARCH_FINDINGS.md` — dominio, mercado, insights (5.7 escala V1).
  - `REQUIREMENTS.md` — 62 RF MUST + 4 SHOULD + 4 COULD + 13 WON'T + 42 RNF.
  - `GLOSSARY.md` — 70+ términos.
- **02-planning:**
  - `ARCHITECTURE.md` — componentes C4 nivel 2, decisiones de estructura.
  - `ADR_LOG.md` — 14 ADRs con rationale + breaking changes + alternativas descartadas.
  - `DATA_MODEL.md` — ERD + schemas + índices + soft delete + retention jobs.
  - `API_CONTRACTS.md` — endpoints + payloads + errores estandarizados.
  - `UX_SPECS.md` — flujos + sistema de diseño Tailwise + iframe loader + cold start.
  - `THREAT_MODEL.md` — STRIDE + ASVS L2 + CIS Docker + GDPR por superficie.
  - `CONVENCIONES_PLATAFORMA.md` (DEL-001) — puertos, redes, volúmenes, naming, subdominios, env vars para apps huésped.
- **04-delivery:**
  - `INFRASTRUCTURE.md` — topology, CIS table, secretos, gap closure.
  - `CI_CD.md` — workflows, SemVer strategy, rollback policy.
  - `INTEGRATION_REPORT.md` — smoke tests 8/8 + PHPUnit 151/151.
  - `RELEASE_NOTES.md` — procedimiento VPS.
  - `DELIVERY_CHECKLIST.md` — exit criteria + gates.
- **05-operations:**
  - `MONITORING.md` — stack, métricas, 10 alertas activas, dashboards.
  - `INCIDENT_PLAYBOOK.md` — SEV1-4, tiempos, flujo 6 pasos, escalamiento.
  - `RUNBOOK.md` — arranque/parada, smoke check, backups, 7 runbooks específicos §6.
  - `TECH_DEBT.md` — 35 items inventariados con ID estable y SLO.
  - `TRANSVERSAL_VALIDATION.md` — 6/6 agentes APROBADO.
  - `templates/POSTMORTEM_TEMPLATE.md` — blameless, 10 secciones.
- **06-retrospective:**
  - `RETROSPECTIVE.md` — went well / wrong / surprises / improvements / metrics / action items.
  - `PROJECT_SUMMARY.md` — este documento.
  - `EXECUTIVE_REPORT.md` — resumen ejecutivo al PO.
  - `FRAMEWORK_MEMORY.md` — lecciones aprendidas para proyectos futuros.

### Agentes del framework (`framework-agentico/agents/`)
- `CHECKPOINT_GLOBAL.md` + checkpoint por fase (`00`-`06`) + transversal.
- `PROJECT_MANAGER.md` + `COMMANDS.md` + `rules/GENERAL_RULES.md`.
- `presets/maestro-platform/PRESET.md` + rules (derivado de `web-maestro` por inversión).

---

## 6. Estado final

| Dimensión | Valor | Target V1 | Estado |
|---|---|---|---|
| Épicas aprobadas | 14/14 | 14/14 | ✅ |
| Cobertura statements | 80.2% | ≥ 80% | ✅ |
| Cobertura branches | ~72% | ≥ 70% | ✅ |
| Tests pasando | 150/151 | 100% menos skipped justificados | ✅ (1 skipped: E2E login happy path, TD-019) |
| Vulnerabilidades CRITICAL / HIGH | 0 / 0 | 0 / 0 bloqueantes | ✅ |
| ForwardAuth p95 latencia | No medido (TD-015) | < 50 ms | ⚠ (sin métricas app hasta TD-015) |
| Cold start apps | No medido (TD-015) | < 15 s | ⚠ |
| Cache hit rate validación tokens | No medido (TD-015) | ≥ 0.90 | ⚠ |
| Retención backups | 30 días | ≥ 30 días | ✅ |
| Retención post-destrucción | 90 días | ≥ 90 días | ✅ |
| CIS Docker Benchmark | Aplicado en compose + ProvisioningEngine | Compliant | ✅ |
| OWASP ASVS L2 | Controles aplicados | Compliant | ✅ |
| SOC 2 controles | Controles aplicados (evidencia formal → TD-007) | Controles, no certificación | ✅ (per DEC-013) |
| GDPR | Audit log + cifrado + retención + export manual (TD-001) | Compliant base | ✅ (self-service pendiente) |

**Gaps conocidos al rc.1:**
- TD-015 (endpoint `/metrics` app) bloquea verificación continua de SLOs de latencia / cache. SLO 2026-06-30.
- TD-019/TD-020 E2E tests login + OAuth Microsoft. SLO 2026-06-30.
- TD-001/TD-002/TD-003 GDPR self-service + DPA. SLO 2026-06/07.
- TD-007 evidencia formal SOC 2 Type II (si se persigue certificación). SLO 2026-09-30.

---

## 7. Equipo y roles

| Rol | Persona / agente | Responsabilidad |
|---|---|---|
| Product Owner | Humano (aviera@llyasoc.com) | Decisiones de negocio, priorización, validación de entregables, despliegue al VPS. |
| Project Manager | Claude Code (rol `/pm`) | Orquestación global, checkpoints, escalamientos, cost tracking. |
| Orquestador de fase | Claude Code (rol `/fase:N:orquestar`) | Coordinación de agentes de la fase, validación de exit criteria. |
| Agentes transversales | Claude Code (rol transversal) | code-review, security-auditor, QA, performance, compliance, documentation, executive-reporter, cost-analyst. |
| Agentes de fase | Claude Code (por fase) | researcher, requirements-analyst, software-architect, data-architect, api-designer, ux-designer, backend-developer, frontend-developer, devops-engineer, integrator, release-manager, observability-engineer, incident-manager, tech-debt-manager, memory-updater. |
| Infra VPS Azure | Humano (fuera del framework) | Provisión del VPS y despliegue del tag `v1.0.0-rc.1`. |

---

## 8. Referencias

- `framework-agentico/agents/CHECKPOINT_GLOBAL.md` — estado canónico del proyecto.
- `CHANGELOG.md` — narrativa de versiones.
- `docs/06-retrospective/RETROSPECTIVE.md` — lecciones + métricas + action items.
- `docs/06-retrospective/EXECUTIVE_REPORT.md` — resumen ejecutivo para el PO.
- `docs/06-retrospective/FRAMEWORK_MEMORY.md` — memoria transferible a próximos proyectos.
