# Checkpoint Global

> **Administrado por:** Project Manager
> **Ultima actualizacion:** 2026-04-20

---

```yaml
project_id: "PRJ-MAESTRO-V1"
repo_url: "https://github.com/LLyAsoc-Digital/web-maestro-para-aplicacones-genericas"
premise: |
  Construccion de Maestro Platform V1: plataforma multi-tenant de clase empresarial que aloja,
  orquesta y gobierna multiples aplicaciones dockerizadas bajo un portal web unificado con
  autenticacion centralizada. Provee: (a) Identity Provider unico via Laravel Passport OAuth2
  emisor de JWT mas login user/pass y Microsoft Entra ID; (b) motor de provisioning con redes
  Docker aisladas, BDs dedicadas y ciclo de vida completo por instancia; (c) reverse proxy
  Traefik con ForwardAuth, TLS Let's Encrypt y rate limiting; (d) portal React que renderiza
  apps huesped en iframes con transferencia de auth via postMessage; (e) SDK Node.js y CLI
  maestro-cli; (f) pipeline CI/CD estandarizado; (g) sistema agentico de asistencia a devs;
  (h) stack de observabilidad Prometheus/Loki/Grafana; (i) backups cifrados diarios en Azure
  Blob. Fuente completa de la premisa: PremisaWebMaestro/00..11. Constitucion vinculante con
  10 no-negociables en 01-PREMISAS-Y-NO-NEGOCIABLES.md.
status: "completed"
preset_active: "maestro-platform"
mode: "project_completed_v1.0.0-rc.2_stabilization-1_tag_v1.0.0_pendiente_humano"

created_at: "2026-04-14"
updated_at: "2026-04-20"
iteration: 13
completed_at: "2026-04-18"
last_iteration:
  id: "stabilization-1"
  started_at: "2026-04-20"
  completed_at: "2026-04-20"
  release_candidate: "v1.0.0-rc.2"
  trigger: "humano pidio version estable, resolver inconsistencias y crear credenciales de integracion"
  scope: "estable (stack healthy + phpunit 100% + 8/8 smoke + E2E login happy path) + unificacion .env (DEC-025) + feature flag Entra (DEC-026) + Azurite dev (DEC-027) + credenciales PO/tester"
  out_of_scope: "cierre TD HIGH (TD-015/001/002/007/019/020), tag v1.0.0"
  transversal_verdict: "APROBADO CON OBSERVACIONES (5/5 agentes), 0 bloqueantes"
  nuevos_td: ["TD-036 HIGH", "TD-037 MEDIUM", "TD-038 LOW", "TD-039 LOW", "TD-040 MEDIUM", "TD-041 MEDIUM", "TD-042 LOW"]
  artefactos:
    - "docs/04-delivery/INTEGRATION_REPORT_iter2.md"
    - "docs/05-operations/TRANSVERSAL_VALIDATION_iter2.md"
    - "CHANGELOG.md (entrada v1.0.0-rc.2)"
    - "docs/05-operations/TECH_DEBT.md (TD-036 a TD-042)"

current_phase: null
completed_phases:
  - "00-setup"         # completada 2026-04-16 con exit_criteria redefinidos por DEC-012
  - "01-discovery"     # completada 2026-04-16 con MoSCoW validada y DEC-013 a DEC-021
  - "02-planning"      # completada 2026-04-16: ARCHITECTURE + 14 ADRs + DATA_MODEL + API_CONTRACTS + UX_SPECS + THREAT_MODEL + CONVENCIONES_PLATAFORMA
  - "03-development"   # completada 2026-04-17: 14/14 epicas, 150 tests (80.2% coverage), provisioning E2E verificado, validacion transversal 4/4 APROBADO
  - "04-delivery"      # completada 2026-04-18: v1.0.0-rc.1, docker-compose.prod.yml con CIS hardening, CHANGELOG + RELEASE_NOTES + DELIVERY_CHECKLIST, fix CIS ProvisioningEngine DB+App, transversal 4/4 APROBADO
  - "05-operations"    # completada 2026-04-18: MONITORING + INCIDENT_PLAYBOOK + RUNBOOK + TECH_DEBT (35 items, 0 CRITICAL, 8 HIGH), 10 alert rules activas, fix healthcheck IPv6, transversal 6/6 APROBADO
  - "06-retrospective" # completada 2026-04-18: RETROSPECTIVE + PROJECT_SUMMARY + EXECUTIVE_REPORT + FRAMEWORK_MEMORY con 10 patrones, 8 anti-patrones, 9 preferencias, 8 defaults, 12 preguntas Fase 00, 8 action items
pending_phases: []
skipped_phases: []

stack_objetivo:
  backend:
    language: "PHP 8.3+"
    framework: "Laravel 13.x (latest stable; DEC-023)"
    auth: "Laravel Passport 13.x (OAuth2 server) + Microsoft Entra ID"
  frontend:
    framework: "React + Tailwind CSS"
    base_template: "Tailwise Bundle/React Version - v1.0.9/"
  database_maestro: "PostgreSQL (preferido, a confirmar en Planning)"
  cache: "Redis (fase 9)"
  reverse_proxy: "Traefik con ForwardAuth + Let's Encrypt"
  containerizacion: "Docker + docker-compose"
  infraestructura: "local (docker-compose). El VPS Azure lo gestiona el humano por fuera del framework; el framework genera Dockerfile, docker-compose, workflows CI/CD y configuracion de Traefik, pero no despliega ni configura el VPS."
  observabilidad: "Prometheus + cAdvisor + Loki + Promtail + Grafana"
  backups: "Azure Blob Storage (cifrados)"
  sdk_primer_lenguaje: "Node.js (@maestro/sdk-node)"
  cli: "maestro-cli (Node.js)"

templates_disponibles:
  laravel: "Tailwise Bundle/Laravel Version - v1.0.3/Source/"
  react: "Tailwise Bundle/React Version - v1.0.9/"
  vue: "Tailwise Bundle/Tailwise Vue - v1.0.1/"
  html: "Tailwise Bundle/HTML Version - v1.0.1/"

decisions_log:
  - id: "DEC-001"
    date: "2026-04-16"
    decision: "El proyecto construye la plataforma Maestro misma (no una app huesped)"
    source: "humano"
    impact: "global"
  - id: "DEC-002"
    date: "2026-04-16"
    decision: "Preset activo: maestro-platform (invertido de web-maestro para maxima compatibilidad simetrica)"
    source: "humano"
    impact: "todas las fases"
    artifact: "framework-agentico/agents/presets/maestro-platform/PRESET.md y rules/RULES.md"
  - id: "DEC-003"
    date: "2026-04-16"
    decision: "Alcance V1 = las 9 fases completas del plan de PremisaWebMaestro/11-PLAN-DE-IMPLEMENTACION.md"
    source: "humano"
    impact: "scope"
  - id: "DEC-004"
    date: "2026-04-16"
    decision: "Trabajo sobre el repo destino ya inicializado localmente (origin = web-maestro-para-aplicacones-genericas)"
    source: "humano"
    impact: "delivery"
  - id: "DEC-005"
    date: "2026-04-16"
    decision: "Sin limite de presupuesto USD; el cost-analyst mide y reporta igual"
    source: "humano"
    impact: "cost monitoring"
  - id: "DEC-006"
    date: "2026-04-16"
    decision: "Sin deadline definido; priorizar calidad y cumplimiento de no-negociables sobre velocidad"
    source: "humano"
    impact: "planning"
  - id: "DEC-007"
    date: "2026-04-16"
    decision: "Equipo de ejecucion: humano (Product Owner) + Claude Code agentico"
    source: "humano"
    impact: "coordinacion"
  - id: "DEC-008"
    date: "2026-04-16"
    decision: "SLA V1: 50 usuarios concurrentes objetivo"
    source: "humano"
    impact: "capacity planning y performance-analyst"
  - id: "DEC-009"
    date: "2026-04-16"
    decision: "Portal usa el template React de Tailwise (Tailwise Bundle/React Version - v1.0.9/)"
    source: "humano"
    impact: "frontend"
  - id: "DEC-010"
    date: "2026-04-16"
    decision: "Primer SDK a publicar: Node.js (segun plan de la premisa, fase 5)"
    source: "humano"
    impact: "developer experience"
  - id: "DEC-011"
    date: "2026-04-16"
    decision: "Todo el trabajo del framework agentico es local. El VPS Azure se gestiona por fuera del framework por el humano."
    source: "humano"
    impact: "00-setup (sin verificacion VPS), 04-delivery (genera artefactos IaC/Docker pero no despliega), 05-operations (configura stack observabilidad localmente, el humano lo lleva al VPS)"
  - id: "DEC-012"
    date: "2026-04-16"
    decision: "Zero local installs: TODO el stack corre dockerizado. Ningun runtime (PHP, Node, Composer, psql, etc.) se instala en el host del dev. Unicos prerequisitos locales: Docker, Docker Compose, git, IDE. Toolchain (php artisan, composer, npm, psql) se invoca via 'docker compose run --rm ...'. Objetivo: portabilidad total entre devs y entre Maestro + apps genericas sin conflictos."
    source: "humano"
    impact: |
      00-setup: exit_criteria redefinidos (sin PHP/Composer/Node/psql locales).
      02-planning: software-architect obligado a disenar docker-compose.dev.yml portatil y convenciones de puertos/redes/volumenes/naming que eviten colisiones entre Maestro y apps huesped.
      03-development: todos los comandos de desarrollo se ejecutan dentro de contenedores. README del proyecto debe reflejarlo.
      04-delivery: devops-engineer produce SETUP_GUIDE.md y CONTRIBUTING.md con convenciones explicitas para agregar apps huesped sin conflicto.
    deliverable_obligatorio: "docs/CONVENCIONES_PLATAFORMA.md — documento versionado con convenciones de puertos, redes Docker, volumenes, naming de contenedores, subdominios y variables de entorno que TODA app huesped debe respetar para coexistir con el Maestro y entre si."
  - id: "DEC-013"
    date: "2026-04-16"
    decision: "Compliance V1 MUST HAVE = GDPR + SOC 2 Type II controles (sin certificacion V1) + CIS Docker Benchmark + OWASP Top 10 + OWASP ASVS Nivel 2. Otros (LGPD, HIPAA, PCI-DSS, FedRAMP) = WON'T V1 o aplican a apps huesped especificas, no al Maestro."
    source: "humano (validacion de propuesta del compliance-analyst)"
    impact: "01-discovery (cierre), 02-planning (threat model y ADRs alineados), 03-development (controles), 04-delivery (auditoria pre-release), 05-operations (evidencia continua). Cierra ESC-002."
    closes_escalation: "ESC-002"
  - id: "DEC-014"
    date: "2026-04-16"
    decision: "Idioma V1 = unicamente espanol. Ingles y otros idiomas quedan fuera de alcance V1."
    source: "humano"
    impact: "02-planning (ux-designer), 03-development (no i18n), 04-delivery (documentacion en espanol)"
  - id: "DEC-015"
    date: "2026-04-16"
    decision: "Accesibilidad WCAG 2.1 AA = WON'T HAVE V1. Solo cumplir HTML semantico basico y contraste razonable, sin certificacion formal ni auditoria de accesibilidad."
    source: "humano"
    impact: "02-planning (ux-designer no disena para WCAG AA), 03-development (sin testing de accesibilidad). Documentar como deuda tecnica V2+ para mercados que lo exijan."
  - id: "DEC-016"
    date: "2026-04-16"
    decision: "MFA propio (TOTP) = WON'T HAVE V1. El MFA se apoya exclusivamente en Microsoft Entra ID para los usuarios que elijan ese flujo. Usuarios user/pass no tienen MFA disponible en V1."
    source: "humano"
    impact: "02-planning (no disenar MFA propio), 03-development (no implementar), RNF-070 (GDPR) compatible por ser riesgo aceptado y documentado."
  - id: "DEC-017"
    date: "2026-04-16"
    decision: "Escala inicial V1 = 1 empresa tenant × 7 apps huesped en primeros 12 meses. La arquitectura multi-tenant (empresas M-N usuarios, empresas M-N apps) se mantiene inmutable segun la premisa para crecimiento post-V1, pero el dimensionamiento de capacidad y performance targets se calibran a esta escala minima."
    source: "humano"
    impact: |
      01-discovery (insight 5.7 agregado al RESEARCH_FINDINGS).
      02-planning (software-architect dimensiona a escala real, no a escenarios B2B SaaS hipoteticos; cache Redis sigue recomendado por defensa en profundidad pero no critico para cumplir SLA).
      03-development (carga baja permite priorizar correctness sobre micro-optimizaciones).
      04-delivery (pruebas de carga con 50 concurrentes sobre 1 tenant × 7 apps = ~7 users/app en peor caso).
  - id: "DEC-018"
    date: "2026-04-16"
    decision: "V1 solo implementa ABM (Alta/Baja/Modificacion) de companies + users + applications + 3 pivotes M-M (company_user, application_company, application_user). Sin pricing complejo, sin tiers de licencia con logica de negocio, sin billing, sin metricas de uso facturable. Los campos tier/activa/expira_en en application_company se mantienen como metadata pero sin logica de facturacion."
    source: "humano"
    impact: "02-planning (data-architect y api-designer simplifican el dominio de licenciamiento), 03-development (no billing engine, no reportes financieros), RF-900+ WON'T expandido con RF-911 (pricing/billing)."
  - id: "DEC-019"
    date: "2026-04-16"
    decision: "Retencion de datos = exactamente los minimos declarados en la premisa (30 dias de backups y 90 dias post-destruccion de instancia). No excede. Politica de purga agresiva pasados esos plazos para minimizar superficie de cumplimiento GDPR."
    source: "humano"
    impact: "02-planning (data-architect define jobs de purga), 05-operations (runbook de purga), compliance GDPR (retencion minima explicita)."
  - id: "DEC-020"
    date: "2026-04-16"
    decision: "V1 no exige zero-downtime. Las ventanas de mantenimiento deben minimizarse (SHOULD) pero son aceptables, preferentemente fuera de horario laboral del tenant. SLA objetivo se mantiene en 99.5% (~3.6h downtime/mes permitido)."
    source: "humano"
    impact: "02-planning (software-architect no requiere blue-green V1), 04-delivery (estrategia de deploy con downtime controlado), 05-operations (comunicacion previa al tenant de ventanas planificadas)."
  - id: "DEC-021"
    date: "2026-04-16"
    decision: "Soporte a clientes finales = fuera del alcance del Maestro V1. No hay SLA de respuesta integrado, no hay canal de soporte en el producto, no hay ticket system. El canal de soporte del tenant se gestiona por fuera del producto y es responsabilidad del equipo operador."
    source: "humano"
    impact: "02-planning (no se disena modulo de soporte), 03-development (no implementar), 05-operations (documento aparte gestiona canal, fuera del scope del framework)."
  - id: "DEC-023"
    date: "2026-04-16"
    decision: "Stack backend usa Laravel 13.x (ultima version estable al 2026-04-16) en lugar de Laravel 11. PHP minimo sube a 8.3 (requisito de Laravel 13). Laravel Passport 13.x (compatible con Laravel 11/12/13 segun Packagist) para OAuth2."
    source: "humano"
    impact: |
      02-planning (ya actualizado): ARCHITECTURE.md, ADR_LOG.md tabla stack y ADR-001.
      03-development: composer.json del Maestro requiere laravel/framework ^13.5, laravel/passport ^13.7, PHP ^8.3. Revisar compat de paquetes terceros (socialite-providers/microsoft-graph, spatie/laravel-model-states, laravel-scribe, nunomaduro/larastan) antes de lockear.
      Imagen base Docker: php:8.3-fpm-alpine (ya era la elegida, sin cambios).
    rationale: "La premisa fija 'Laravel' sin mayor; elegir la ultima estable maximiza vida util del proyecto antes del proximo major y reduce riesgo de deuda tecnica al release. Laravel 13.5.0 salio el 2026-04-14 (2 dias antes de esta decision); Passport 13.7.4 release 2026-04-09."
    source_data: "Packagist consulta 2026-04-16"
  - id: "DEC-022"
    date: "2026-04-16"
    superseded_by: "DEC-024"
    superseded_at: "2026-04-17"
    decision: "[SUPERSEDED por DEC-024] El framework agentico opera SIN GitHub Issues/PRs automatizados. Toda la trazabilidad (requisitos, decisiones, escalaciones, deliverables, deuda tecnica, hallazgos de threat model y auditorias) permanece en archivos markdown versionados dentro del repo. Los pipelines CI/CD de fase 04-06 siguen usando GitHub Actions (no requiere acceso a Issues/PRs desde Claude)."
    source: "humano"
    impact: |
      Governance: registro exclusivo en framework-agentico/agents/CHECKPOINT_GLOBAL.md, CHECKPOINT.md por fase y artefactos en docs/.
      02-planning: ADRs en docs/02-planning/, no como GitHub Issues.
      03-development: los modulos y su estado se trackean en CHECKPOINT.md, no en Issues.
      05-operations: incidentes se documentan en runbooks en docs/05-operations/.
      04-delivery: los workflows de GitHub Actions se generan en .github/workflows pero su ejecucion la dispara el humano/CI, no Claude.
    rationale: "El fine-grained PAT disponible no tiene acceso al repo de la org LLyAsoc-Digital y la configuracion para habilitarlo requiere aprobacion del admin de la org. Opcion B del diagnostico elegida por el humano."

  - id: "DEC-024"
    date: "2026-04-17"
    decision: "Revierte DEC-022. El framework agentico AHORA opera en paralelo con GitHub Issues/PRs y milestones. Los archivos markdown del framework (CHECKPOINT_GLOBAL, CHECKPOINT por fase, docs/) siguen siendo la fuente de verdad canonica; GitHub es vista secundaria para visibilidad compartida."
    source: "humano"
    impact: |
      Governance dual: markdown canonico + GitHub mirror. Al cambiar estado, se actualiza ambos.
      21 milestones creados: 7 fases (Fase 00..06) + 14 epicas (A..M + Platform). Fases 00-02 y epicas A,B,C,E,G,J,M cerradas.
      22 issues creados: 14 epicas (7 cerradas, 7 abiertas) + ESC-001 (abierta) + ESC-003 (cerrada por este DEC-024) + 6 deuda V2+ (WCAG AA, MFA TOTP, i18n, billing, soporte, zero-downtime).
      17 labels creados: type:{epic,escalation,tech-debt,phase}, phase:{00-setup..06-retrospective}, status:{approved,in-progress,pending,wont-have-v1}, severity:{medium,low}.
      04-delivery: release.yml ya es factible (acceso gh CLI OK, classic PAT con scopes repo+workflow+read:org).
    rationale: "El humano habilito classic PAT con scopes suficientes (gh auth status: repo+workflow+read:org) y habilito la funcionalidad de Issues en el repo. Acceso verificado contra LLyAsoc-Digital/web-maestro-para-aplicacones-genericas."
    closes_escalation: "ESC-003"
    github_artifacts:
      repo: "LLyAsoc-Digital/web-maestro-para-aplicacones-genericas"
      milestones_url: "https://github.com/LLyAsoc-Digital/web-maestro-para-aplicacones-genericas/milestones"
      issues_url: "https://github.com/LLyAsoc-Digital/web-maestro-para-aplicacones-genericas/issues"
      epicas_cerradas: ["#3 A", "#4 B", "#5 C", "#6 E", "#7 G", "#10 J", "#13 M"]
      epicas_abiertas: ["#1 D", "#2 F", "#8 H", "#9 I", "#11 K", "#12 L", "#14 Platform"]
      escalations: ["#15 ESC-001 open", "#16 ESC-003 closed"]
      deuda_v2: ["#17 WCAG AA", "#18 MFA TOTP", "#19 i18n", "#20 billing", "#21 soporte", "#22 zero-downtime"]

  - id: "DEC-025"
    date: "2026-04-20"
    decision: "`.env` unificado en raiz del repo. `backend/.env` eliminado. Fuente unica de verdad leida por docker-compose.dev.yml y todos los servicios."
    source: "humano (estrategia A aprobada)"
    impact: |
      F04-delivery: .env.example regenerado como template sincronizado; todos los secrets (DB, REDIS, encryption, passport) rotados.
      F03-development: backend/config/*.php sigue leyendo env() sin cambios; el cambio es operativo.
      F05-operations: RUNBOOK debe reflejar que no existe mas backend/.env.
    iteration: "stabilization-1"
  - id: "DEC-026"
    date: "2026-04-20"
    decision: "Feature flag MICROSOFT_ENTRA_ENABLED (backend) + VITE_MICROSOFT_ENTRA_ENABLED (portal). Cuando esta en false: 503 entra_disabled en /api/auth/microsoft/* y portal oculta el boton MS."
    source: "humano (no posee credenciales de terceros en dev)"
    impact: |
      F03-development: config/services.php key nueva microsoft.enabled; MicrosoftController.guardDisabled() 503 + audit.log; LoginPage render condicional.
      F04-delivery: phpunit.xml fuerza MICROSOFT_ENTRA_ENABLED=false con force=true; cada test del flujo OAuth activa el flag localmente.
      F05-operations: RUNBOOK documenta como activar el flag en prod con credenciales reales.
    iteration: "stabilization-1"
  - id: "DEC-027"
    date: "2026-04-20"
    decision: "Azurite (Azure Blob emulator oficial de MSFT) agregado como servicio azurite en docker-compose.dev.yml. En dev reemplaza la storage account real; en prod queda Azure Blob real."
    source: "humano (no posee credenciales de terceros en dev)"
    impact: |
      F04-delivery: docker-compose.dev.yml + .env (credenciales publicas devstoreaccount1) + volumen maestro-azurite-data.
      F03-development: BackupService.disk() fallback silencioso a disco local si driver azure no registrado (necesario para phpunit sin league/flysystem-azure).
      F05-operations: RUNBOOK prohibe explicitamente desplegar Azurite en prod. TD-041/TD-042 trackean hardening si se promueve.
    iteration: "stabilization-1"

scope_v1_inicial:
  empresas_tenant: 1
  apps_huesped_estimadas: 7
  usuarios_concurrentes_target: 50
  notas: |
    Escala muy baja en V1. La arquitectura multi-tenant (relaciones M-N de la premisa)
    se mantiene inmutable para habilitar crecimiento sin refactor mayor. Performance
    targets de la premisa (50ms p95 ForwardAuth, 15s cold start) son alcanzables con
    margen amplio a esta escala. Redis cache sigue recomendado por defensa en profundidad.
  fuente: "DEC-017 (humano 2026-04-16)"

escalations_log:
  - id: "ISSUE-002"
    date: "2026-04-18"
    severity: "medium"
    status: "closed"
    closed_at: "2026-04-18"
    title: "Healthchecks de docker-compose overridean los Dockerfile con 'localhost' (IPv6 ::1) — api/worker/portal en unhealthy"
    description: |
      Validacion browser E2E post-release detecto que maestro-api y maestro-worker estaban
      UNHEALTHY con healthcheck "wget: can't connect to remote host: Connection refused".
      Los Dockerfiles tenian el fix AI-3 (localhost -> 127.0.0.1) pero docker-compose.dev.yml
      y docker-compose.prod.yml definen un healthcheck propio que overridea el del Dockerfile
      y seguia usando "localhost". Alpine resolvia ::1 (IPv6) y nginx bindeaba solo IPv4.
      Adicional: maestro-worker heredaba el HEALTHCHECK http del Dockerfile pero ejecuta
      "php artisan queue:work", no nginx, por lo que el healthcheck era inaplicable.
    resolution: |
      - docker-compose.dev.yml: healthcheck maestro-api localhost -> 127.0.0.1.
      - docker-compose.dev.yml: agregado healthcheck propio maestro-worker con "pgrep -f queue:work".
      - docker-compose.prod.yml: healthcheck maestro-api + maestro-portal localhost -> 127.0.0.1.
    runtime_verified:
      - "docker ps maestro-api -> (healthy) 47s"
      - "docker ps maestro-worker -> (healthy) 47s"
      - "POST /api/auth/login -> HTTP 200 con access_token + refresh_token + user"
      - "Browser Playwright: login UI OK, localStorage['maestro.access_token'] presente"
      - "Browser Playwright: /admin/empresas|usuarios|aplicaciones|instancias|audit -> 5/5 API 200, sin console errors"
      - "Audit log UI muestra auth.login.success en tiempo real"
    action_items:
      - "AI-3 del retrospective queda AMPLIADO: el fix de healthcheck localhost->127.0.0.1 debe aplicarse tambien a los compose, no solo al Dockerfile (compose overridea)."
      - "Workers sin HTTP jamas deben heredar HEALTHCHECK http del Dockerfile base; siempre definir explicitamente en compose."

  - id: "ISSUE-001"
    date: "2026-04-17"
    severity: "high"
    status: "closed"
    closed_at: "2026-04-17"
    title: "Passport v13 breaking changes vs. código v12 — RESUELTO"
    description: |
      Passport v13 rompió múltiples cosas vs v12. Descubrimientos encadenados y fixes aplicados:
      1. Password Grant desabilitado por default → `Passport::enablePasswordGrant()` requerido.
      2. Columna `grant_types` espera JSON array, no CSV ni lista con espacios.
      3. oauth_access_tokens.user_id default es bigint, incompatible con nuestro User UUID.
      4. ForwardAuthController tenía recursión infinita con `$request->setUserResolver(fn () => $request->user('api'))`.
      5. Env vars PASSPORT_PRIVATE_KEY estaba apuntando a /secrets (path obsoleto), mezclándose con la ruta default de Passport.
    resolution: |
      - AuthServiceProvider: `Passport::enablePasswordGrant()`.
      - PassportClientsSeeder: crea oauth_client con grant_types=json_encode(['password','refresh_token']) y redirect_uris=json_encode([]).
      - Migración `2026_04_17_100003_fix_oauth_user_id_to_uuid.php` alteró user_id a UUID.
      - ForwardAuthController reescrito con `auth('api')->user()` directo (sin recursión).
      - `.env` y config/passport.php limpiados para usar defaults de Passport.
      - LoginController reescrito para hacer request interno a /oauth/token con grant_type=password.
    runtime_verified:
      - "POST /api/auth/login → 200 con access_token + refresh_token + user"
      - "GET /api/auth/me → 200 con user + empresas + roles"
      - "GET /api/auth/validate → 200 con headers X-Auth-User-Id, Email, Company-Id, Roles, Permissions"

  - id: "ESC-001"
    date: "2026-04-16"
    severity: "medium"
    status: "open"
    title: "PAT de GitHub aparece en git remote -v aunque no esta en .git/config"
    description: |
      El comando git remote -v muestra la URL de origin con un Personal Access Token embebido
      (ghp_...). El .git/config del repo esta limpio. La inyeccion del token viene de
      configuracion git global (~/.gitconfig) o de credential helper. El humano opto por
      continuar sin verificar el origen exacto del token.
    risk: "Si el repo fuera clonado o compartido desde este entorno, el PAT podria filtrarse.
      En el estado actual del repo remoto no hay filtracion hacia terceros."
    next_steps: "Revisar ~/.gitconfig y credential helpers cuando el humano tenga tiempo.
      Rotar el PAT si hay sospecha de exposicion previa."
    owner: "humano"

  - id: "ESC-003"
    date: "2026-04-16"
    severity: "low"
    status: "closed"
    closed_at: "2026-04-17"
    closed_by: "DEC-024"
    title: "Fine-grained PAT no tiene acceso al repo LLyAsoc-Digital/web-maestro-para-aplicacones-genericas"
    description: |
      El PAT fine-grained usado por gh CLI no resuelve el repo destino. Diagnostico confirma
      que el PAT no tiene el repo seleccionado en 'Repository access' o la org
      LLyAsoc-Digital tiene 'Fine-grained token approval' activado y el token no esta
      aprobado. El humano intento ajustarlo sin exito y opto por DEC-022 (operar sin
      GitHub Issues desde el framework).
    resolution: |
      El humano habilito classic PAT con scopes repo+workflow+read:org y habilito Issues
      en el repo. Acceso verificado el 2026-04-17 mediante gh auth status + gh repo view.
      DEC-024 revierte DEC-022: el framework ahora opera en paralelo con GitHub.
      Se crearon 21 milestones, 22 issues y 17 labels en esta misma accion.
    github_issue: "#16"

  - id: "ESC-002"
    date: "2026-04-16"
    severity: "low"
    status: "closed"
    closed_at: "2026-04-16"
    closed_by: "DEC-013"
    resolution: "El humano valido el shortlist propuesto por el compliance-analyst. V1 MUST HAVE compliance = GDPR + SOC 2 Type II controles (sin certificacion) + CIS Docker Benchmark + OWASP Top 10 + OWASP ASVS Nivel 2. Otros marcos (LGPD, HIPAA, PCI-DSS, FedRAMP) quedan fuera de V1 o aplican a apps huesped especificas."
    title: "Compliance regulatorio aplicable indefinido"
    description: |
      El humano desconoce que regulaciones especificas aplican (GDPR, LGPD, HIPAA, PCI-DSS,
      ISO27001, SOC2). La premisa exige audit log, cifrado, backups y retencion 90 dias, lo
      cual es compatible con la mayoria de marcos, pero no hay confirmacion de cuales son
      obligatorios legalmente.
    risk: "Potenciales gaps regulatorios si V1 se despliega a clientes con obligaciones
      especificas no contempladas."
    owner: "compliance-analyst (transversal) con escalamiento al humano"

phases_status:
  00-setup:
    status: "completed"
    exit_criteria_met: true
    completed_at: "2026-04-16"
    checkpoint_file: "00-setup/CHECKPOINT.md"
  01-discovery:
    status: "completed"
    exit_criteria_met: true
    completed_at: "2026-04-16"
    checkpoint_file: "01-discovery/CHECKPOINT.md"
    deliverables:
      - "docs/01-discovery/RESEARCH_FINDINGS.md"
      - "docs/01-discovery/REQUIREMENTS.md"
      - "docs/01-discovery/GLOSSARY.md"
  02-planning:
    status: "completed"
    exit_criteria_met: true
    completed_at: "2026-04-16"
    checkpoint_file: "02-planning/CHECKPOINT.md"
    deliverables:
      - "docs/02-planning/ARCHITECTURE.md"
      - "docs/02-planning/ADR_LOG.md"
      - "docs/02-planning/DATA_MODEL.md"
      - "docs/02-planning/API_CONTRACTS.md"
      - "docs/02-planning/UX_SPECS.md"
      - "docs/02-planning/THREAT_MODEL.md"
      - "docs/CONVENCIONES_PLATAFORMA.md (DEL-001)"
  03-development:
    status: "completed"
    exit_criteria_met: true
    started_at: "2026-04-17"
    completed_at: "2026-04-17"
    checkpoint_file: "03-development/CHECKPOINT.md"
    iteration: 9
    modules_approved: 14          # 14/14 épicas aprobadas
    modules_in_progress: 0
    modules_pending: 0
    coverage_total_pct: 80.2
    tests_passing: "150 / 151 (1 skipped E2E login happy path)"
    transversal_verdict: "APROBADO CON OBSERVACIONES (4/4 agentes) — deuda asignada a Fase 04/05"
    deliverables_iteracion_9:
      - "Suite de tests 150 passing / 1 skipped, 285 assertions, 80.2% cobertura (target ≥80%)"
      - "Fix bug: DeliverHookJob ya no usa secret 'placeholder' para payload_hmac; usa el webhook_secret real; columna nullable"
      - "Fix bug: RegisterAppController migrado de yaml_parse() (no existente) a Symfony\\Yaml"
      - "Fix bug: LoginTest Cache::flush() en setUp para no acumular throttle entre tests"
      - "Validación transversal final: code-reviewer + security-auditor + qa-tester + compliance-analyst"
    deliverables_iteracion_8:
      - "Platform endpoints runtime E2E: /v1/inventory/context (200 con user+company+app+maestro) + /v1/apps/register (401 sin secret)"
      - "Épica F: 5 admin pages React (Companies/Users/Applications/Instances/AuditLog) con Tanstack Query + modal + StatusBadge + AdminTable component"
      - "Épica D RUNTIME E2E VERIFICADO: docker-socket-proxy con POST=1 + IMAGES=1, instancia nginx-test provisionada (BD dedicada + container app + red aislada + labels Traefik)"
      - "Migración failed_jobs + jobs + job_batches creadas raw SQL"
      - "Fix DOCKER_PROXY_URL: tcp:// → http:// en .env"
    deliverables_iteracion_5:
      - "Runtime admin CRUD validado: GET/POST /api/admin/companies|users|applications con JWT real (Fix AuditLogger resource_id null vs empty string)"
      - "Épica D implementada: ProvisioningEngine service (crea red + BD + contenedor app + labels Traefik)"
      - "Épica D: 4 Jobs (Provision, HealthCheck, DispatchHealthChecks, PurgeDestroyed) + Scheduler"
      - "Épica D: InstancesController CRUD + lifecycle (10 endpoints) + rutas registradas"
      - "Comando artisan maestro:purge-revoked-tokens"
    deliverables_iteracion_6:
      - "Épica G: docs/schemas/maestro.yaml.schema.json (JSON Schema oficial del contrato)"
      - "Épica G: sdk/node/ (@maestro/sdk-node con authMiddleware, requireRole, requirePermission, hookVerifierMiddleware, GatewayClient, tenantFilter, loadContext)"
      - "Épica G: cli/node/ (maestro-cli con validate + new; template node-express con CLAUDE.md hereditario)"
      - "Épica F: GET /api/portal/my-apps runtime verificado con JWT real"
      - "Épica J: Hooks salientes HMAC-SHA256 — HookDispatcher service + DeliverHookJob con retry 1s-10min"
      - "Épica J: Integración con UsersController: on_user_added al asignar membership, on_user_removed al borrar user"
    deliverables_iteracion_7:
      - "Épica I: GatewayController — POST /api/v1/gateway/{target}/{path+} con verificación permisos + licencia + HMAC + audit log"
      - "Épica L: BackupService (pg_dump | gzip | AES-256-CBC → Azure Blob o local) + RunBackups command + Scheduler daily 02:00"
      - "Épica K: docker-compose.obs.yml con Prometheus + cAdvisor + Node Exporter + Loki + Promtail + Grafana"
      - "Épica K: configs observabilidad (prometheus.yml, loki-config.yml, promtail-config.yml con labels maestro.managed, datasources + dashboards provisionados)"
      - "Épica K: dashboard Maestro Overview con stats instancias, CPU/mem por contenedor, logs filtrados por level"
      - "Épica H: .github/workflows/release.yml con tag v* → build maestro-api + maestro-portal + push GHCR + trivy bloqueante + GitHub Release con changelog"
  04-delivery:
    status: "completed"
    completed_at: "2026-04-18"
    iteration: 2    # iter 1 cerro con rc.1; iter 2 (stabilization-1) cerro con rc.2 el 2026-04-20
    exit_criteria_met: true
    checkpoint_file: "04-delivery/CHECKPOINT.md"
    release_candidate: "v1.0.0-rc.2"
    deliverables:
      - "docker-compose.prod.yml con CIS Docker hardening (no-new-privileges, CapDrop ALL, pids_limit, resources.limits, read_only+tmpfs en api/portal/traefik)"
      - ".env.production.example con APP_DEBUG=false + LOG_LEVEL=warning + rate limits estrictos"
      - "CHANGELOG.md v1.0.0-rc.1 con 14 épicas documentadas"
      - "docs/04-delivery/INFRASTRUCTURE.md + CI_CD.md + INTEGRATION_REPORT.md + RELEASE_NOTES.md + DELIVERY_CHECKLIST.md"
    deliverables_iteracion_2_stabilization_1:
      - ".env unificado en raiz (DEC-025); backend/.env eliminado; .env.example regenerado; 7 secrets rotados"
      - "Feature flag Microsoft Entra (DEC-026): MICROSOFT_ENTRA_ENABLED + VITE_MICROSOFT_ENTRA_ENABLED; 503 entra_disabled con audit log; portal oculta boton"
      - "Azurite dev (DEC-027): servicio + volumen + endpoint http://azurite:10000/devstoreaccount1; BackupService fallback local en testing"
      - "DemoPoSeeder idempotente + artisan maestro:bootstrap-demo [--fresh] (bloqueado en prod)"
      - "Credenciales integracion: acme-demo + po@maestro.local/MaestroPO2026! + tester@maestro.local/TesterMaestro2026!"
      - "just bootstrap-demo / bootstrap-demo-fresh / e2e; tests/e2e-smoke/login.spec.mjs con defaults PO"
      - "docs/04-delivery/INTEGRATION_REPORT_iter2.md + docs/05-operations/TRANSVERSAL_VALIDATION_iter2.md"
      - "CHANGELOG.md v1.0.0-rc.2 agregado"
    bugs_fixed:
      - "ProvisioningEngine::createDatabaseContainer: CapDrop ALL + CapAdd [CHOWN,SETGID,SETUID,DAC_OVERRIDE,FOWNER] + PidsLimit 200 (cierra deuda CIS iter 9)"
      - "ProvisioningEngine::createAppContainer: PidsLimit 512"
    bugs_fixed_iter2:
      - "Duplicidad backend/.env vs .env raiz (drift silencioso) → DEC-025"
      - "MicrosoftControllerTest rompia cuando flag quedaba en false global → setUp + 2 tests nuevos"
    smoke_tests: "8/8 OK (health, auth endpoints, login validation, migrations, routes, phpunit 151/151)"
    smoke_tests_iter2: "8/8 OK (health, login PO, me, validate, MS redirect 503, MS callback 503, admin/companies PO, migrate --pretend)"
    e2e_iter2: "5/5 core steps PASS (portal_loads, login_form_visible, login_post, post_login_redirect, token_stored) + 2 WARN (G-1 500 permisos logs, G-2 admin redirect) documentados como TD-036/TD-037"
    transversal: "4/4 APROBADO CON OBSERVACIONES (code-reviewer, security-auditor, performance-analyst, qa-tester) — observaciones críticas aplicadas en el mismo ciclo"
    transversal_iter2: "5/5 APROBADO CON OBSERVACIONES (code-reviewer, security-auditor, compliance-analyst, performance-analyst, qa-tester) — 0 bloqueantes, 7 TD nuevos (TD-036 HIGH, TD-037/040/041 MEDIUM, TD-038/039/042 LOW)"
  05-operations:
    status: "completed"
    completed_at: "2026-04-18"
    iteration: 10
    exit_criteria_met: true
    checkpoint_file: "05-operations/CHECKPOINT.md"
    deliverables:
      - "docs/05-operations/MONITORING.md — stack obs + 13 métricas + 10 alertas + dashboards inventario"
      - "docs/05-operations/INCIDENT_PLAYBOOK.md — SEV1-4, flujo 6 pasos, tiempos objetivo, escalamiento"
      - "docs/05-operations/RUNBOOK.md — cold start + parada + smoke check + backups + 7 runbooks específicos §6"
      - "docs/05-operations/TECH_DEBT.md — 35 items (0 CRITICAL, 8 HIGH ≤ 2026-Q3, 14 MEDIUM, 13 LOW)"
      - "docs/05-operations/TRANSVERSAL_VALIDATION.md — 6/6 agentes APROBADO"
      - "docs/05-operations/templates/POSTMORTEM_TEMPLATE.md — blameless con 10 secciones"
      - "docker/observability/prometheus/alerts/maestro.yml — 3 rule groups, 10 reglas"
      - "docker-compose.obs.yml + prometheus.yml — rule_files activado y montado"
    bugs_fixed:
      - "docker/php/Dockerfile + docker/portal/Dockerfile: healthcheck localhost → 127.0.0.1 (alpine resolvía ::1 IPv6 marcando unhealthy falso)"
    transversal: "6/6 APROBADO CON OBSERVACIONES (code-reviewer, security-auditor, compliance-analyst, performance-analyst, qa-tester, documentation-writer) — observación crítica (permisos backup 0600) aplicada inline; resto documentado en TECH_DEBT"
    deuda_destacada:
      - "TD-015 endpoint /metrics app (HIGH) bloquea alertas de negocio (ForwardAuth p95, queue backlog)"
      - "TD-001/TD-002 endpoints GDPR self-service (HIGH)"
      - "TD-007 evidencia formal SOC 2 Type II (HIGH)"
      - "TD-019/TD-020 E2E tests login + OAuth MS (HIGH)"
  06-retrospective:
    status: "completed"
    completed_at: "2026-04-18"
    iteration: 1
    exit_criteria_met: true
    checkpoint_file: "06-retrospective/CHECKPOINT.md"
    deliverables:
      - "docs/06-retrospective/RETROSPECTIVE.md — blameless, 10 secciones (datos proyecto + went-well 10 + went-wrong 5 + surprises + improvements 7 + métricas + patterns + antipatterns + action items 8 + cierre)"
      - "docs/06-retrospective/PROJECT_SUMMARY.md — índice ejecutivo con stack, arquitectura, 14 épicas, documentación por fase, estado final, equipo"
      - "docs/06-retrospective/EXECUTIVE_REPORT.md — reporte al PO con TL;DR, KPIs, deuda, riesgos, próximos pasos"
      - "docs/06-retrospective/FRAMEWORK_MEMORY.md — 10 patrones + 8 anti-patrones + 9 preferencias humano + 8 defaults + 12 preguntas Fase 00 + tiempos referencia + 8 action items framework"
      - "~/.claude/projects/.../memory/framework_lessons_maestro_v1.md — memoria cross-session persistida"
    metrics_finales:
      total_modules: 14
      correction_iterations_avg: 1.4
      escalations_to_human: 4
      phases_completed_on_first_pass: 6
      total_tech_debt_items: 35
      critical_vulnerabilities_found: 0
      days_calendar_total: 5
      days_calendar_premise_to_rc1: 3
    action_items_framework: "AI-1 template ADR breaking changes, AI-2 gh auth check Fase 00, AI-3 healthcheck inet4-only, AI-4 /metrics app no diferible, AI-5 runbook nace con alerta"
    action_items_humano: "AI-6 dry-run restore mensual, AI-7 cerrar ESC-001 PAT leak, AI-8 primer dry-run restore post-tag"
  transversal:
    status: "not_started"
    checkpoint_file: "transversal/CHECKPOINT.md"

cost_summary:
  license:
    type: "subscription"
    plan: "max-5x"
    monthly_cost_usd: 200.00
  budget:
    budget_usd: null
    consumed_usd: 0.00
    consumed_pct: 0.0%
    alert_level: "none"
  totals:
    total_queries: 0
    total_tokens:
      input: 0
      output: 0
      cache_read: 0
      cache_creation: 0
      grand_total: 0
    total_cost_usd: 0.00
  by_phase:
    00-setup: { queries: 0, tokens: 0, cost_usd: 0.00 }
    01-discovery: { queries: 0, tokens: 0, cost_usd: 0.00 }
    02-planning: { queries: 0, tokens: 0, cost_usd: 0.00 }
    03-development: { queries: 0, tokens: 0, cost_usd: 0.00 }
    04-delivery: { queries: 0, tokens: 0, cost_usd: 0.00 }
    05-operations: { queries: 0, tokens: 0, cost_usd: 0.00 }
    06-retrospective: { queries: 0, tokens: 0, cost_usd: 0.00 }
  efficiency:
    avg_tokens_per_response: 0
    avg_cost_per_response_usd: 0.00
    cache_hit_rate: 0.0%
    tokens_per_loc: 0
  cost_log: "transversal/docs/COST_LOG.md"

objetivos_cuantitativos_v1:
  usuarios_concurrentes: 50
  latencia_forwardauth_p95_ms: 50
  cold_start_max_seconds: 15
  cache_hit_rate_validacion_tokens: 0.90
  retencion_backups_dias_min: 30
  retencion_instancia_destruida_dias: 90
  cobertura_tests_statements_min: 0.80
  cobertura_tests_branches_min: 0.70
  vulnerabilidades_critical_high_bloqueantes: true
```

---

## Notas de Inicializacion

- Framework agentico configurado el 2026-04-14
- Premisa del proyecto cargada desde PremisaWebMaestro/ el 2026-04-16
- Preset maestro-platform creado el 2026-04-16 como derivado invertido de web-maestro
- Stack objetivo confirmado con el humano el 2026-04-16
- 10 decisiones clave y 2 escalaciones abiertas registradas
- Proximo paso: invocar /fase:setup:orquestar para activar Fase 00
- Para ver estado en cualquier momento: /pm:estado
