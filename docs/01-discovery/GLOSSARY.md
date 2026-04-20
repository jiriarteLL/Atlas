# Glosario de Dominio — Maestro Platform V1

> **Fase:** 01-Discovery
> **Agente:** requirements-analyst
> **Fecha:** 2026-04-16
> **Proyecto:** PRJ-MAESTRO-V1

Este glosario define los términos que usarán todos los agentes en fases posteriores (Planning, Development, etc.). Cualquier término ambiguo debe agregarse aquí antes de usarlo en un artefacto.

---

| Término | Definición | Contexto de uso |
|---|---|---|
| **Maestro** | Plataforma multi-tenant que aloja apps dockerizadas, actúa como Identity Provider, motor de provisioning y reverse proxy. | Sustantivo principal del proyecto. |
| **Tenant** | Organización cliente que contrata licencias de apps. Sinónimo de "empresa" en este proyecto. | Modelo de datos (tabla `companies`), seguridad (aislamiento por tenant). |
| **Instancia** | Combinación única de (empresa × aplicación). Cada instancia tiene contenedor de app, BD dedicada, red Docker aislada y ciclo de vida propio. | Motor de provisioning, cost-analyst. |
| **App huésped** | Aplicación dockerizada que corre dentro del Maestro cumpliendo el contrato `maestro.yaml`. | SDK, CI/CD, preset web-maestro. |
| **App catalog** | Registro de aplicaciones disponibles para licenciamiento. Tabla `applications`. | Admin del Maestro. |
| **Licencia** | Registro de `application_company` que habilita a una empresa a usar una app con un tier y expiración. | Modelo de datos, reportes C-Level. |
| **Empresa activa** | Empresa bajo la cual el usuario está operando en su sesión actual. Impacta el JWT y el `company_id` propagado. | Portal, selector de empresa, middleware. |
| **company_id** | Identificador de la empresa tenant en el contexto de un request. Se propaga vía header `X-Auth-Company-Id`. | Middleware SDK, filtros de queries, auditoría. |
| **Usuario final** | Empleado de una empresa tenant que usa apps huésped desde el portal. | Modelo de datos (`users`), UX. |
| **Admin del Maestro** | Operador de la plataforma con acceso a dashboards, CRUD de empresas/usuarios/apps, provisioning. | Audit log, permisos. |
| **Dev de app huésped** | Persona o equipo que construye una app para alojarse en Maestro. | Documentación, SDK, CLAUDE.md. |
| **maestro.yaml** | Contrato obligatorio en la raíz del repo de cada app huésped. Declara recursos, health, auth, hooks, limits. Validado por `maestro-cli validate` y en CI/CD. | Preset web-maestro, pipeline. |
| **JSON Schema de maestro.yaml** | Especificación formal del contrato, publicada y versionada por el Maestro. | maestro-cli, IDE support. |
| **maestro-cli** | CLI oficial que valida el contrato y scaffold proyectos nuevos (`new`, `validate`). | DX de apps huésped. |
| **SDK** | Librería por lenguaje (`@maestro/sdk-node` primero) que provee middleware de auth, filtro tenant y helpers de permisos. | Apps huésped. |
| **Hooks** | Webhooks salientes desde el Maestro hacia apps huésped en eventos (`on_user_added`, `on_user_removed`). Firmados HMAC-SHA256. | SDK, preset web-maestro. |
| **X-Maestro-Webhook-Secret** | Header que la app huésped usa para verificar autenticidad de hooks del Maestro. | Seguridad hooks. |
| **ForwardAuth** | Middleware de Traefik que intercepta cada request, lo valida contra `/api/auth/validate` del Maestro y reenvía con headers `X-Auth-*`. | Seguridad perimetral. |
| **X-Auth-\*** | Conjunto de headers HTTP que inyecta el Maestro vía ForwardAuth tras validar el token: `X-Auth-User-Id`, `X-Auth-User-Email`, `X-Auth-Company-Id`, `X-Auth-Roles`, `X-Auth-Permissions`. | Apps huésped, SDK, middleware. |
| **JWT** | JSON Web Token emitido por Laravel Passport. Contiene identidad, empresa activa, roles. Expira 1h por defecto. | Auth. |
| **Refresh token** | Token de larga duración que permite renovar el JWT sin re-autenticación. Se rota en cada uso. | RF-004. |
| **Laravel Passport** | Servidor OAuth2 del Maestro. Emite y valida JWT. | Backend. |
| **Microsoft Entra ID** | IdP externo (antes Azure AD) con el que el Maestro federa autenticación. Flujo OAuth2 estándar. | RF-002. |
| **OAuth2** | Protocolo estándar de autorización. El Maestro actúa como Authorization Server y Resource Server. | Auth. |
| **Zero Trust** | Principio según el cual ningún request llega a una app huésped sin haber sido validado. No hay endpoints "internos confiables". | No-negociable 1. |
| **Traefik** | Reverse proxy y edge router. Termina TLS, aplica ForwardAuth, inyecta headers, hace ruteo dinámico por labels Docker. | Infra. |
| **Let's Encrypt** | Autoridad certificadora gratuita con protocolo ACME. Usada por Traefik para TLS automático. | Infra. |
| **HSTS** | HTTP Strict Transport Security. Header que indica al browser usar solo HTTPS. Configurado con max-age 1 año + includeSubDomains. | Seguridad. |
| **HMAC-SHA256** | Algoritmo de firma de mensajes. Usado en webhooks salientes y en comunicación interna Maestro↔apps. | Seguridad. |
| **AES-256** | Cifrado simétrico usado para secretos at-rest (credenciales BD, tokens externos). | Seguridad. |
| **Cold start** | Tiempo desde que un request llega hasta que la instancia dormida está lista para responder. Objetivo V1: <15s. | UX, performance. |
| **Instancia dormida** | Instancia sin tráfico reciente que se detiene para liberar recursos. Se despierta ante el siguiente request. V1 no la activa por defecto. | Operations. |
| **Health check** | Endpoint HTTP (default `/health`) que responde 200 con `{"status":"ok"}` si la app está saludable. Consultado por el Maestro cada N segundos. | No-negociable 3. |
| **Máquina de estados (instancia)** | Secuencia de estados por los que pasa una instancia: provisioning → starting → healthy → degraded → suspended → destroyed → purged. | Motor de provisioning. |
| **Audit log** | Tabla inmutable que registra toda acción administrativa. Solo INSERT. Contiene timestamp, user, IP, action, data_before, data_after. | No-negociable 9, compliance. |
| **Soft delete** | Borrado lógico: registro queda marcado como eliminado pero físicamente presente. Permite restaurar y cumplir retención. | Modelo de datos. |
| **Retención** | Tiempo que se conservan datos tras "borrarlos". Instancias destruidas: 90 días. Backups: 30 días mínimo. | Compliance, ops. |
| **Gateway inter-apps** | API del Maestro que actúa como intermediario entre apps huésped del mismo tenant. Única vía autorizada de comunicación entre apps. | RF-080. |
| **Rate limiting** | Restricción de requests/tiempo por IP o usuario. Default: 100 req/min/IP; login: 10 req/min/IP. | Seguridad. |
| **Threat model** | Documento formal que identifica vectores de ataque y mitigaciones. Obligatorio en Planning. | Security-auditor. |
| **ADR** | Architecture Decision Record. Documenta decisiones arquitectónicas con contexto, alternativas y consecuencias. | Planning. |
| **DEC-XXX** | Identificador de decisión registrada en `CHECKPOINT_GLOBAL.md`. | Trazabilidad. |
| **ESC-XXX** | Identificador de escalación abierta en `CHECKPOINT_GLOBAL.md`. | Trazabilidad. |
| **DEL-XXX** | Identificador de deliverable obligatorio heredado entre fases. | Trazabilidad. |
| **RF / RNF** | Requisito Funcional / Requisito No Funcional. Formato en `REQUIREMENTS.md`. | Requirements. |
| **MoSCoW** | Priorización: **M**ust have / **S**hould have / **C**ould have / **W**on't have. Validada por humano. | Planning. |
| **Preset** | Conjunto de reglas adicionales que se activan para un contexto específico (ej: `web-maestro`, `maestro-platform`). Extienden las reglas generales. | Framework agéntico. |
| **DEC-012 (zero local installs)** | Decisión: ningún runtime se instala en el host del dev; todo corre en contenedores. | DX, portabilidad. |
| **docs/CONVENCIONES_PLATAFORMA.md** | Documento obligatorio que fija naming, puertos, redes, volúmenes, subdominios y env vars para evitar colisiones entre Maestro y apps huésped. | Deliverable DEL-001. |
| **CHECKPOINT (fase)** | Archivo `CHECKPOINT.md` por fase que registra status, exit_criteria y outputs. | Governance. |
| **CHECKPOINT_GLOBAL** | Archivo maestro del proyecto con premise, status, decisions, escalations, cost_summary. | Governance. |
| **Exit criteria** | Lista de condiciones que una fase debe cumplir para considerarse completada y pasar a la siguiente. | Governance. |
| **Transversales** | Agentes que operan en todas las fases: code-reviewer, security-auditor, qa-tester, performance-analyst, compliance-analyst, documentation-writer, executive-reporter, skills-researcher, cost-analyst. | Framework. |
| **VPS** | Virtual Private Server. En este proyecto, máquina en Azure donde corre el stack. Operado por el humano (DEC-011). | Infra. |
| **Azure Blob Storage** | Servicio de almacenamiento de objetos de Azure. Destino de backups cifrados. | RF-110. |
| **CIS Benchmarks** | Configuration hardening guides del Center for Internet Security. Aplicables a Docker, Linux, PostgreSQL. | Seguridad. |
| **OWASP ASVS** | Application Security Verification Standard. Nivel 2 recomendado para la capa de auth. | RNF-020. |
| **Trivy** | Escáner de vulnerabilidades de imágenes Docker. Usado en pipeline CI/CD de apps huésped. | RF-071. |
| **Cache hit rate** | Porcentaje de lookups que encuentran el dato en cache (Redis). Objetivo >90% para validación de tokens. | RNF-003. |
| **SLA** | Service Level Agreement. Objetivo V1 del Maestro: 99.5% uptime. | RNF-032. |
| **RTO / RPO** | Recovery Time Objective / Recovery Point Objective. V1: RTO <4h Maestro / <1h instancia; RPO <24h. | RNF-033, RNF-034. |
| **Grafana / Prometheus / Loki / Promtail / cAdvisor** | Stack de observabilidad. Prometheus = métricas, cAdvisor = métricas de contenedores, Loki = logs, Promtail = shipper de logs, Grafana = dashboards. | Observability. |
| **Portabilidad** | Capacidad de que el stack completo funcione en cualquier máquina con Docker + git + IDE, sin pasos adicionales. | DEC-012, RNF-040-043. |
| **ABM** | Alta/Baja/Modificación. CRUD básico en español. En V1 del Maestro se refiere a la gestión de empresas, usuarios, aplicaciones y sus pivotes M-N **sin pricing, sin billing, sin tiers con lógica de negocio**. | DEC-018, épica B del REQUIREMENTS.md. |
| **Escala V1 inicial** | 1 empresa tenant × 7 apps huésped × 50 usuarios concurrentes objetivo. La arquitectura multi-tenant se mantiene inmutable según premisa para crecimiento post-V1. | DEC-017. |
| **Tenant inicial** | La única empresa tenant del Maestro durante V1 (probablemente LLyAsoc u organización operadora). Aloja las 7 apps internas objetivo V1. | DEC-017. |
| **OWASP ASVS** | Application Security Verification Standard. Nivel 2 es el objetivo para la capa de autenticación del Maestro (controles de credenciales, sesiones, tokens). | DEC-013, RNF-073. |
| **Riesgo aceptado (documentado)** | Situación donde un control mitigador no se implementa V1 pero el riesgo queda registrado como decisión consciente con trazabilidad. Ej: ausencia de MFA propio para usuarios user/pass (DEC-016). | Governance. |
