# Checkpoint Fase 02 — Planning

```yaml
status: "completed"
updated_at: "2026-04-16"
completed_at: "2026-04-16"

exit_criteria:
  stack_defined: true
  stack_propagated: true                # via ARCHITECTURE.md + memory
  architecture_documented: true         # ARCHITECTURE.md
  adrs_created: true                    # 14 ADRs en ADR_LOG.md
  data_model_designed: true             # DATA_MODEL.md con ER, indices, retencion
  api_contracts_defined: true           # API_CONTRACTS.md con endpoints, schemas, errores
  ux_flows_documented: true             # UX_SPECS.md con 9 flujos y wireframes
  threat_model_reviewed: true           # THREAT_MODEL.md con STRIDE + ASVS L2 + CIS
  coherence_validated: true             # cross-check en §9 de cada artefacto
  maestro_yaml_validated: true          # schema definido en API_CONTRACTS §3 (no aplica validacion V1 porque aun no hay apps; aplicable en fase 5)
  convenciones_plataforma_generadas: true  # docs/CONVENCIONES_PLATAFORMA.md (DEL-001)

stack:
  language: "PHP 8.3+"
  framework: "Laravel 13.x (latest stable; DEC-023)"
  auth: "Laravel Passport 13.x + Microsoft Entra ID via Laravel Socialite"
  database: "PostgreSQL 16 Alpine"
  cache: "Redis 7 Alpine"
  orm: "Eloquent"
  queue: "Laravel Queue with Redis driver"
  frontend_framework: "React 18 + TypeScript 5"
  frontend_styles: "Tailwind CSS 3 (base Tailwise v1.0.9)"
  frontend_bundler: "Vite 5"
  reverse_proxy: "Traefik v3"
  containerization: "Docker 29+ + Compose v2"
  docker_api_access: "tecnativa/docker-socket-proxy con allowlist"
  ci_cd: "GitHub Actions"
  test_frameworks:
    backend: "PHPUnit 11"
    frontend: "Vitest + React Testing Library"
    e2e: "Playwright"
  observability: "Prometheus + cAdvisor + Loki + Promtail + Grafana"
  backups: "pg_dump + age/gpg + Azure Blob Storage"
  sdk_primer: "@maestro/sdk-node (Node 20)"
  cli: "maestro-cli (Node 20)"
  secrets_scan: "gitleaks + trivy"
  i18n: "ninguna (solo es-AR segun DEC-014)"

architecture:
  pattern: "Monolito modular Laravel (Clean Architecture + DDD light)"
  modules:
    - "Auth (Passport, Entra, ForwardAuth)"
    - "Identity (users, companies, pivotes M-N)"
    - "Catalog (applications, licenses)"
    - "Provisioning (Docker API, redes, BDs, lifecycle)"
    - "Gateway (inter-apps con HMAC)"
    - "Hooks (webhooks salientes firmados)"
    - "AuditLog (inmutable DB-level)"
    - "Platform (inventory, health, apps/register)"
  frontend: "SPA React con iframe-based app loader + postMessage"
  adrs_count: 14

data_model:
  entities:
    - "users"
    - "companies"
    - "applications"
    - "company_user (M-N)"
    - "application_company (M-N)"
    - "application_user (ternaria M-N-N)"
    - "oauth_clients / oauth_access_tokens / oauth_refresh_tokens (Passport)"
    - "revoked_tokens"
    - "instances"
    - "instance_health_history"
    - "instance_lifecycle_events"
    - "hooks_deliveries"
    - "audit_log (INSERT-only via triggers DB)"
  relationships:
    - "users N:M companies via company_user"
    - "applications N:M companies via application_company"
    - "applications N:M users via application_user (ternaria con company_id)"
    - "instances (application_id, company_id) unique active"
  migration_strategy: "Laravel Migrations con up/down reversibles; triggers DB via DB::unprepared"
  retention_policy:
    backups: "30 dias (DEC-019)"
    destroyed_instances: "90 dias (DEC-019)"
    audit_log: "30 dias V1 (minimos legales)"
    revoked_tokens: "hasta expires_at"
  multi_tenancy:
    isolation_layer_1: "Red Docker dedicada por instancia"
    isolation_layer_2: "Middleware EnforceCompanyIdFilter en Maestro y SDK"

api_contracts:
  endpoints_count: 45+  # incluye auth, portal, admin (companies/users/apps/licenses/instances/audit), platform, gateway, hooks outgoing (no endpoints)
  versioning_strategy: "SemVer publico /api/v1/; interno admin/portal en lockstep con portal"
  auth_strategy: "Bearer JWT para portal; ForwardAuth headers para apps huesped; X-Maestro-App-Secret para CI/CD register"
  error_format: "JSON estandar {error: {code, message, details}, meta: {request_id, timestamp}}"
  pagination: "cursor-based"
  maestro_yaml_schema: "docs/02-planning/API_CONTRACTS.md §3; JSON Schema a generar en fase 03"

ux:
  user_flows_count: 9
  design_system: "Hereda Tailwise React v1.0.9 (tokens de color, tipografia, spacing, componentes)"
  custom_components:
    - "AppIframe"
    - "CompanySwitcher"
    - "ColdStartScreen"
    - "StatusBadge"
    - "HealthSparkline"
    - "AuditDiffViewer"
  responsive: "breakpoints Tailwind default; functional desde 375px"
  accessibility: "WON'T V1 (DEC-015); baseline HTML semantico y contraste razonable"
  i18n: "solo es-AR hardcoded (DEC-014)"

security:
  threat_model_status: "completed 2026-04-16"
  methodology: "STRIDE + OWASP ASVS Nivel 2 + CIS Docker Benchmark"
  critical_threats:
    - "T-01 Cross-tenant data leak (R-001)"
    - "T-02 Escape del Maestro via Docker socket (R-002)"
    - "T-03 XSS + robo de JWT"
    - "T-04 CSRF en flujo Microsoft OAuth"
  mitigations_count: 20   # M1-M20
  asvs_level_2_mapping: "OK para todos los items salvo V2.7/V2.8 MFA (DEC-016 acepta riesgo)"
  cis_docker_mapping: "10 controles criticos OK; 3 configurables en prod (documentado al humano)"
  gdpr_controls_mapping: "cubierto salvo portabilidad (diferida V2)"
  residual_risks_accepted:
    - "MFA propio ausente (DEC-016)"
    - "WCAG AA ausente (DEC-015)"
    - "Single-node (sin HA) V1"
    - "Self-service password reset ausente V1"
    - "Portabilidad GDPR diferida V2"

deliverables_producidos:
  - "docs/02-planning/ARCHITECTURE.md"
  - "docs/02-planning/ADR_LOG.md (14 ADRs)"
  - "docs/02-planning/DATA_MODEL.md"
  - "docs/02-planning/API_CONTRACTS.md"
  - "docs/02-planning/UX_SPECS.md"
  - "docs/02-planning/THREAT_MODEL.md"
  - "docs/CONVENCIONES_PLATAFORMA.md (DEL-001 cumplido)"

deliverables_pendientes_fase_03:
  - "docker-compose.dev.yml portatil (DEL-002)"
  - "docs/02-planning/schema/maestro.yaml.schema.json"
  - "docs/02-planning/openapi.yaml (generado via Scribe)"
  - "Estructura de carpetas del proyecto Laravel inicializada"
  - "Passport install + primeras migraciones"
  - "Dockerfile del Maestro multi-stage non-root"

acciones_derivadas_para_fase_03:
  del_del_threat_model:
    - "Implementar triggers DB audit_log"
    - "Configurar Passport RS256 >=4096 + test alg:none rejection"
    - "Configurar docker-socket-proxy con allowlist ADR-006"
    - "Implementar EnforceCompanyIdFilter en Maestro y SDK"
    - "Agregar Trivy + gitleaks a .github/workflows/ci.yml"
    - "Tests de integracion cross-tenant (>=5 casos)"
    - "Configurar CSP + security headers en Traefik"
    - "Redactor de Laravel Log para keys sensibles"
    - "Rate limiting por endpoint (login 10/min, admin 1000/min, /apps/register 100/min)"
    - "Runbook rotacion MAESTRO_ENCRYPTION_KEY"

escalations:
  - question: "none al cierre de fase 02; todas resueltas o documentadas"
    asked_by: "-"

handoff_al_PM: |
  Fase 02 COMPLETADA 2026-04-16. 7 artefactos producidos en docs/ con coherencia
  cruzada verificada. Stack definitivo: Laravel 13 + Passport 13 + React/Tailwise +
  PostgreSQL 16 + Redis 7 + Traefik v3 + Docker + GHCR + Observability stack + SDK
  Node 20. 14 ADRs registrados. Modelo de datos cubre los 125 requisitos.
  Threat model con 20 mitigaciones mapea ASVS L2 + CIS Docker + GDPR. DEL-001
  (CONVENCIONES_PLATAFORMA.md) cumplido.
  Fase 03 (Development) lista para activar: comienza por montar la estructura de
  carpetas, docker-compose.dev.yml y las primeras migraciones de la epica A (Auth)
  y B (Identity).
```
