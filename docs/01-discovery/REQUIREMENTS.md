# Requisitos del Proyecto — Maestro Platform V1

> **Fase:** 01-Discovery
> **Agente:** requirements-analyst
> **Fecha:** 2026-04-16
> **Proyecto:** PRJ-MAESTRO-V1
> **Status:** ✅ Priorización MoSCoW **VALIDADA por humano (Product Owner) el 2026-04-16** vía DEC-013 a DEC-021

---

## 1. Contexto

Maestro Platform V1 es la construcción completa del orquestador multi-tenant descrito en `PremisaWebMaestro/`. Este documento formaliza los requisitos funcionales y no funcionales derivados de la constitución del proyecto, los 10 no-negociables, las 12 decisiones registradas en CHECKPOINT_GLOBAL y los hallazgos del `RESEARCH_FINDINGS.md`.

**Alcance V1**: las 9 fases del plan de implementación de la premisa.

**Equipo**: humano (Product Owner) + Claude Code agentico.

**Objetivos cuantitativos heredados**:
- 50 usuarios concurrentes
- Latencia ForwardAuth < 50ms p95
- Cold start < 15s
- Cache hit rate validación tokens > 90%
- Cobertura tests: 80% statements / 70% branches
- Retención backups >= 30 días; retención instancia destruida 90 días

---

## 2. Usuarios

Ver detalle en `RESEARCH_FINDINGS.md` §2. Resumen:

| Grupo | Usa | Principal métrica de éxito |
|---|---|---|
| Empresa tenant | Portal + reportes admin | Onboarding de empleados < 5 min/usuario |
| Usuario final (empleado) | Portal + apps huésped | Tiempo de login a app < 3 s |
| Desarrollador de apps | maestro-cli + SDK + CLAUDE.md | Tiempo hasta primer despliegue < 1 día |
| Admin Maestro | Dashboards Grafana + CLI | Diagnóstico de incidente < 15 min |
| C-Level | Reportes ejecutivos | Actualización mensual de KPIs |

---

## 3. Requisitos Funcionales

### 3.1 MUST HAVE (V1 obligatorio)

#### Épica A — Identidad y autenticación

| ID | Descripción | Criterio de aceptación |
|---|---|---|
| RF-001 | Como usuario, quiero iniciar sesión con email + contraseña y recibir un token JWT. | Dado un email y password válidos en `POST /api/auth/login`, cuando el usuario envía el form, entonces recibe un JWT con estructura estándar (iss, sub, exp, company_id, roles) con expiración de 1 hora. |
| RF-002 | Como usuario, quiero iniciar sesión con Microsoft (Entra ID) y recibir un JWT del Maestro. | Dado un flujo OAuth2 con Microsoft Entra ID, cuando el usuario completa el consentimiento, entonces el Maestro crea o vincula el usuario y emite un JWT propio. |
| RF-003 | Como sistema, quiero validar tokens emitidos via endpoint consumido por Traefik ForwardAuth. | Dado `GET /api/auth/validate` con header Authorization Bearer, cuando el token es válido, entonces responde 200 con headers X-Auth-User-Id, X-Auth-User-Email, X-Auth-Company-Id, X-Auth-Roles, X-Auth-Permissions. Si el token es inválido/expirado, responde 401. |
| RF-004 | Como usuario, quiero renovar mi token con un refresh_token sin re-autenticarme. | Dado `POST /api/auth/refresh` con refresh_token válido, cuando el usuario lo envía, entonces recibe nuevo JWT y nuevo refresh_token (rotación). |
| RF-005 | Como usuario, quiero cerrar sesión y que mi token sea revocado. | Dado `POST /api/auth/logout` con token válido, cuando se llama, entonces el token queda registrado como revocado y futuras llamadas a `/api/auth/validate` con ese token responden 401. |
| RF-006 | Como usuario, quiero cambiar mi empresa activa y recibir un JWT con el nuevo contexto. | Dado un usuario que pertenece a múltiples empresas, cuando solicita cambio de empresa activa, entonces recibe un JWT nuevo con X-Auth-Company-Id actualizado. |

#### Épica B — Modelo de identidades (M-M)

| ID | Descripción | Criterio de aceptación |
|---|---|---|
| RF-010 | Como admin, quiero gestionar empresas (CRUD) con soft delete. | `POST/GET/PUT/DELETE /api/companies` con soft delete. Registros borrados permanecen 90 días antes de purga. |
| RF-011 | Como admin, quiero gestionar usuarios (CRUD) con soft delete. | `POST/GET/PUT/DELETE /api/users` con soft delete. Email único global. |
| RF-012 | Como admin, quiero gestionar aplicaciones del catálogo (CRUD). | `POST/GET/PUT/DELETE /api/applications` con metadata de app (nombre, version, image, maestro.yaml validado). |
| RF-013 | Como admin, quiero asignar usuarios a empresas con roles. | Tabla pivote `company_user` con roles. Un usuario puede pertenecer a N empresas con roles distintos. |
| RF-014 | Como admin, quiero licenciar aplicaciones a empresas con tier. | Tabla pivote `application_company` con tier, fecha de expiración, estado activo/inactivo. |
| RF-015 | Como admin, quiero asignar usuarios a apps con permisos específicos. | Tabla pivote `application_user` con roles dentro de la app específica. |

#### Épica C — Audit log

| ID | Descripción | Criterio de aceptación |
|---|---|---|
| RF-020 | Como admin, quiero que toda acción administrativa quede registrada e inmutable. | Toda operación de escritura en `/api/companies`, `/api/users`, `/api/applications`, `/api/licenses`, `/api/instances/*` genera un registro en `audit_log` con: timestamp (ms), user_id, IP, action, data_before, data_after. La tabla acepta solo INSERT; triggers de BD rechazan UPDATE y DELETE. |
| RF-021 | Como admin, quiero consultar el audit log con filtros. | `GET /api/audit-log?user_id=...&action=...&from=...&to=...` responde con paginación. |

#### Épica D — Motor de provisioning

| ID | Descripción | Criterio de aceptación |
|---|---|---|
| RF-030 | Como admin, quiero provisionar una instancia de una app para una empresa. | `POST /api/instances/create` con app_id + company_id crea: red Docker aislada, BD dedicada con credenciales random 32+ chars, contenedor de app con env vars inyectadas, labels Traefik para ruteo. Estado transiciona a provisioning → starting → healthy. |
| RF-031 | Como admin, quiero detener/reiniciar una instancia. | `POST /api/instances/{id}/stop` y `/start` cambian estado del contenedor y registran en audit. |
| RF-032 | Como admin, quiero destruir una instancia con retención. | `DELETE /api/instances/{id}` detiene contenedor, marca como destroyed y programa purgado de datos 90 días después. Permite restaurar durante ese periodo. |
| RF-033 | Como sistema, quiero ejecutar health checks periódicos contra cada instancia. | Cada N segundos (configurable, default 30s), job de Laravel queue consulta el endpoint health de la app. Registro de estado por instancia. |
| RF-034 | Como sistema, quiero auto-reiniciar instancias con health checks fallidos. | Tras 3 fallos consecutivos: restart automático. Tras 5: notificación al admin. Tras 10: suspender instancia. |

#### Épica E — Reverse proxy y seguridad perimetral

| ID | Descripción | Criterio de aceptación |
|---|---|---|
| RF-040 | Como sistema, quiero terminar TLS automáticamente con Let's Encrypt. | Traefik configurado con ACME HTTP-01 o DNS-01 challenge. Certificados se renuevan automáticamente. |
| RF-041 | Como sistema, quiero redirigir HTTP→HTTPS en el borde. | Toda request HTTP (puerto 80) redirige 301 a HTTPS (puerto 443). |
| RF-042 | Como sistema, quiero aplicar ForwardAuth a todas las rutas protegidas. | Middleware de Traefik consulta `/api/auth/validate` antes de reenviar cada request. Solo si valida 200, reenvía con headers X-Auth-*. |
| RF-043 | Como sistema, quiero rate limiting por IP en el portal. | 100 req/min/IP por defecto en rutas públicas. Rutas de login: 10 req/min/IP. |
| RF-044 | Como sistema, quiero inyectar headers de seguridad en todas las respuestas. | HSTS (1 año + includeSubDomains), X-Frame-Options DENY, X-Content-Type-Options nosniff, Referrer-Policy strict-origin-when-cross-origin, Content-Security-Policy restrictiva. |

#### Épica F — Portal web

| ID | Descripción | Criterio de aceptación |
|---|---|---|
| RF-050 | Como usuario, quiero ver un portal con sidebar de mis apps licenciadas. | Tras login, el portal carga un shell React con sidebar listando las apps activas de la empresa activa del usuario. |
| RF-051 | Como usuario, quiero cargar una app dentro de un iframe sin re-autenticarme. | Click en app del sidebar carga iframe en el área principal. El portal transfiere el token via postMessage. La app lee X-Auth-* del request HTTP (inyectados por Traefik). |
| RF-052 | Como usuario con varias empresas, quiero cambiar entre ellas desde el portal. | Selector de empresa activa en la barra superior. Al cambiar, se emite JWT nuevo y se recarga el sidebar. |
| RF-053 | Como usuario, quiero ver una pantalla de carga durante cold start de apps dormidas. | Si la instancia está dormida, al seleccionarla se muestra pantalla de carga con tiempo estimado. Auto-refresh cuando esté healthy. |
| RF-054 | Como usuario, quiero manejo visual de errores comunes. | Si una app está caída, licencia expirada, token expirado o sin conexión, el portal muestra mensaje claro sin pantallas en blanco. |
| RF-055 | Como usuario sin apps, quiero una pantalla de bienvenida. | Si el usuario no tiene apps activas en la empresa seleccionada, se muestra mensaje de bienvenida y contacto con admin. |
| RF-056 | Como usuario, quiero que el portal funcione en desktop, tablet y mobile. | Responsive, testeable en Chrome/Firefox/Safari última versión y viewport móvil 375px. |

#### Épica G — Contrato y SDK

| ID | Descripción | Criterio de aceptación |
|---|---|---|
| RF-060 | Como dev de app, quiero un JSON Schema oficial de maestro.yaml. | Schema versionado (SemVer) publicado en el repo del Maestro y referenciable desde apps huésped. Valida nombre, version, requires, health, auth, resources, hooks. |
| RF-061 | Como dev de app, quiero un CLI `maestro-cli` con `validate` y `new`. | `maestro-cli validate` valida el maestro.yaml contra schema y reglas. `maestro-cli new` genera proyecto scaffold Node.js + Express funcional. |
| RF-062 | Como dev de app, quiero un SDK Node.js con middleware de auth. | `@maestro/sdk-node` publicado en npm. Middleware lee headers X-Auth-* y popula `req.user`. Filtro de tenant agrega automáticamente company_id a queries. Helpers de verificación de roles/permisos. |
| RF-063 | Como dev de app, quiero generar CLAUDE.md automáticamente para mi app. | `maestro-cli new` genera CLAUDE.md con reglas heredadas de plataforma (no-negociables, prohibiciones). |
| RF-064 | Como sistema, quiero que apps se registren automáticamente al hacer push. | `POST /api/apps/register` consumido por el workflow CI/CD de apps huésped. Recibe metadata (nombre, version, image) y registra o actualiza la app en el catálogo. |

#### Épica H — CI/CD de apps huésped

| ID | Descripción | Criterio de aceptación |
|---|---|---|
| RF-070 | Como dev de app, quiero un workflow de GitHub Actions template. | Template reutilizable que ejecuta: validate maestro.yaml → tests → build Docker → scan vulnerabilidades → push a registry → registrar en Maestro. |
| RF-071 | Como sistema, quiero bloquear imágenes con vulnerabilidades CRITICAL/HIGH. | Escaneo (ej: Trivy) en CI/CD. Si hay CVEs CRITICAL o HIGH sin remediar, el pipeline falla y no publica. |
| RF-072 | Como dev de app, quiero que main esté protegida con PR + review. | Template de repositorio configura branch protection rules automáticamente. |

#### Épica I — Gateway inter-apps

| ID | Descripción | Criterio de aceptación |
|---|---|---|
| RF-080 | Como app huésped, quiero comunicarme con otra app del mismo tenant vía gateway. | `/api/gateway/{app_destino}/{ruta}` recibe request, verifica permisos del tenant y del usuario, reenvía a la app destino, registra en audit log. |
| RF-081 | Como sistema, quiero prohibir comunicación directa entre apps huésped. | Redes Docker no conectan contenedores de apps distintas. La única vía es el gateway. |

#### Épica J — Hooks salientes

| ID | Descripción | Criterio de aceptación |
|---|---|---|
| RF-090 | Como sistema, quiero notificar a apps huésped cuando se agrega/remueve un usuario. | Si la app declara hooks en maestro.yaml, el Maestro envía `on_user_added` / `on_user_removed` firmado con HMAC-SHA256 y header X-Maestro-Webhook-Secret. |

#### Épica K — Observabilidad y operaciones

| ID | Descripción | Criterio de aceptación |
|---|---|---|
| RF-100 | Como admin, quiero dashboards de Grafana para métricas clave. | Tres dashboards: Ejecutivo (empresas activas, apps, usuarios), Por Instancia (CPU, mem, requests, errors), Del Maestro (latencia auth, queue length, BD). |
| RF-101 | Como admin, quiero alertas por Slack/email en condiciones críticas. | Alertas configuradas: instancia no responde >3 fallos, CPU/mem > 90% sostenido, certificado TLS expira <30 días, BD del Maestro down. |
| RF-102 | Como admin, quiero logs centralizados filtrables por company_id. | Loki + Promtail recolectan logs. Grafana permite búsqueda por company_id, app, nivel, rango de tiempo. |

#### Épica L — Backups

| ID | Descripción | Criterio de aceptación |
|---|---|---|
| RF-110 | Como sistema, quiero backups diarios automáticos cifrados. | Job entre 2-4am, cifra dump (AES-256), sube a Azure Blob Storage. |
| RF-111 | Como sistema, quiero retención mínima de 30 días. | Política de lifecycle en Blob Storage mantiene últimos 30 snapshots. |
| RF-112 | Como sistema, quiero respaldo pre-migración de BD del Maestro. | Antes de cada migración de schema, snapshot adicional con tag "pre-migration". |

#### Épica M — Portabilidad y DX (DEC-012)

| ID | Descripción | Criterio de aceptación |
|---|---|---|
| RF-120 | Como dev del Maestro, quiero levantar todo el stack con `docker compose up -d`. | `docker-compose.dev.yml` en raíz levanta Traefik + Maestro + BD + Redis sin prerequisitos de runtime en host. |
| RF-121 | Como dev del Maestro, quiero ejecutar composer/artisan/npm via contenedores. | `docker compose run --rm php composer install`, `docker compose run --rm php php artisan migrate`, `docker compose run --rm node npm install` funcionan out-of-the-box. |
| RF-122 | Como admin del proyecto, quiero un documento de convenciones para coexistencia. | `docs/CONVENCIONES_PLATAFORMA.md` versionado define naming, puertos, redes, volúmenes, subdominios y env vars que TODA app huésped debe respetar para coexistir sin conflicto. |

---

### 3.2 SHOULD HAVE (V1 si el tiempo lo permite)

| ID | Descripción | Justificación de no-MUST |
|---|---|---|
| RF-201 | Como dev de app, quiero SDKs adicionales (Python, Go). | V1 entrega Node.js. Otros lenguajes post-V1 salvo que el humano los marque obligatorios. |
| RF-202 | Como admin, quiero exportar audit log a CSV/JSON. | Valor operativo claro, pero no bloqueante para V1. |
| RF-203 | Como usuario, quiero preferencias de UI (tema oscuro, densidad). | UX plus. |
| RF-204 | Como admin, quiero whitelabel básico del portal por empresa (logo, colores). | Diferenciador comercial, diferible. |

> **Nota:** RF-200 (MFA propio TOTP) fue movido a WON'T (RF-908) por DEC-016.

### 3.3 COULD HAVE (nice-to-have)

| ID | Descripción |
|---|---|
| RF-300 | SSO federado con otros IdPs (Google Workspace, Okta). |
| RF-301 | Marketplace de apps con reviews y ratings. |
| RF-302 | CLI interactivo del maestro-cli con wizards. |
| RF-303 | Instrumentación de costos por tenant/app. |

### 3.4 WON'T HAVE (explícitamente fuera de V1)

| ID | Descripción | Razón de exclusión |
|---|---|---|
| RF-900 | Multi-region / multi-VPS activa-activa. | Complejidad enorme; V1 es single-node. Documentar como deuda técnica. |
| RF-901 | Auto-scaling horizontal del Maestro. | Single-node suficiente para 50 usuarios concurrentes V1; escala DEC-017 (1 empresa × 7 apps) hace innecesario V1. |
| RF-902 | Clústers de Kubernetes. | Docker single-host es la estrategia V1. |
| RF-903 | Canary / blue-green deployments de apps huésped. | V1: reemplazo simple con restart controlado (DEC-020 acepta ventanas breves). |
| RF-904 | Marketplace público de apps de terceros. | V1: catálogo privado controlado por Maestro. |
| RF-905 | Facturación integrada (Stripe, billing). | V1 no incluye billing; se gestiona por fuera (DEC-018). |
| RF-906 | Plugins / extensiones del Maestro. | V1 no tiene sistema de plugins. |
| RF-907 | Despliegue al VPS Azure desde el framework. | DEC-011: el humano opera el VPS por fuera. |
| RF-908 | MFA propio TOTP para usuarios user/password. | **DEC-016**: el MFA se apoya exclusivamente en Microsoft Entra ID para ese flujo. Usuarios user/pass no tienen MFA disponible V1 (riesgo aceptado y documentado). |
| RF-909 | Accesibilidad WCAG 2.1 AA formal. | **DEC-015**: sin certificación ni auditoría de accesibilidad V1; baseline = HTML semántico básico y contraste razonable. Deuda técnica documentada para V2+ si mercado lo exige. |
| RF-910 | Idiomas adicionales al español (inglés, portugués, etc.). | **DEC-014**: V1 solo español. i18n queda fuera del scope V1. |
| RF-911 | Pricing/billing/tiers complejos de licencias con lógica de negocio. | **DEC-018**: V1 solo ABM de entidades. Los campos tier/activa/expira_en en `application_company` son metadata sin lógica de facturación. Billing completo es post-V1. |
| RF-912 | SLA de soporte a clientes finales integrado en el producto. | **DEC-021**: el canal de soporte se gestiona fuera del producto; no hay ticket system ni SLA de respuesta en V1. |

---

## 4. Requisitos No Funcionales

### 4.1 Rendimiento

| ID | Requisito | Métrica |
|---|---|---|
| RNF-001 | Latencia de validación de token en ForwardAuth | p95 < 50ms bajo carga normal |
| RNF-002 | Latencia de validación con cache Redis | p95 < 10ms (cache hit) |
| RNF-003 | Cache hit rate de validación | > 90% en estado estable |
| RNF-004 | Cold start de instancia dormida | < 15s desde request hasta healthy |
| RNF-005 | Tiempo de login user/pass | p95 < 500ms |
| RNF-006 | Tiempo de respuesta endpoints admin (CRUD) | p95 < 300ms |
| RNF-007 | Capacidad concurrente V1 | 50 usuarios concurrentes sin degradación |
| RNF-008 | Dashboards Grafana refresh | < 30s |

### 4.2 Seguridad

| ID | Requisito | Métrica |
|---|---|---|
| RNF-010 | Zero Trust: ningún request a app huésped sin validación | 100% de las rutas protegidas tras ForwardAuth |
| RNF-011 | TLS obligatorio | TLS 1.2+ preferente 1.3. HTTP rechazado o redirigido |
| RNF-012 | Cifrado at-rest de secretos | AES-256 para credenciales BD, tokens externos, webhook secrets |
| RNF-013 | No secretos en código/imágenes | Pre-commit scan + CI scan del historial git |
| RNF-014 | Contenedores no-root | USER no-root en todos los Dockerfiles + `--security-opt no-new-privileges` |
| RNF-015 | Aislamiento de red por instancia | Cada instancia en su red Docker dedicada privada |
| RNF-016 | BD dedicada por instancia con credenciales únicas | password >= 32 chars entropía |
| RNF-017 | Audit log inmutable | Triggers DB rechazan UPDATE/DELETE |
| RNF-018 | Expiración de JWT | 1 hora por defecto, máximo 24h |
| RNF-019 | Vulnerabilidades CRITICAL/HIGH | Bloquean pipeline sin excepción |
| RNF-020 | OWASP ASVS Nivel 2 para capa de auth | Checklist verificable por security-auditor |

### 4.3 Escalabilidad y disponibilidad

| ID | Requisito | Métrica |
|---|---|---|
| RNF-030 | Backups diarios | 100% de éxito semanal; retención 30 días mínimo |
| RNF-031 | Retención de instancia destruida | 90 días antes de purga definitiva |
| RNF-032 | Disponibilidad del Maestro V1 | SLA objetivo 99.5% (permite ~3.6h downtime/mes) |
| RNF-033 | Recovery Time Objective (RTO) | < 4h para el Maestro; < 1h por instancia desde backup |
| RNF-034 | Recovery Point Objective (RPO) | < 24h (un backup diario) |

### 4.4 Compatibilidad y portabilidad (DEC-012)

| ID | Requisito | Métrica |
|---|---|---|
| RNF-040 | Zero local installs | Dev productivo solo con Docker + git + IDE |
| RNF-041 | docker-compose.dev.yml portátil | Levanta stack completo en < 2 min desde clone |
| RNF-042 | Coexistencia de apps huésped | Añadir N apps nuevas siguiendo CONVENCIONES_PLATAFORMA.md no rompe el Maestro ni a otras apps |
| RNF-043 | Agnosticismo de stack para apps huésped | Apps en Node/Python/Go/Java/PHP/.NET funcionan vía contrato maestro.yaml |

### 4.5 Usabilidad

| ID | Requisito | Métrica |
|---|---|---|
| RNF-050 | Portal responsive | Funcional en viewports de 375px a 4K |
| RNF-051 | Idioma V1 | **Español únicamente (DEC-014)** |
| RNF-052 | Accesibilidad | **WON'T HAVE V1 (DEC-015)** — baseline: HTML semántico y contraste razonable, sin WCAG AA formal |
| RNF-053 | Tiempo hasta primer despliegue de nueva app | < 1 día para dev medio siguiendo el CLAUDE.md |

### 4.6 Observabilidad

| ID | Requisito | Métrica |
|---|---|---|
| RNF-060 | Métricas por instancia | CPU, memoria, requests/s, latencia p50/p95/p99, errores |
| RNF-061 | Logs centralizados con retención | 30 días searchable; archivo en Blob > 30 días |
| RNF-062 | Alertas accionables | Todas las alertas tienen runbook asociado |
| RNF-063 | Trazabilidad end-to-end | Request ID propagado entre Traefik → Maestro → App |

### 4.7 Compliance (VALIDADA por humano — DEC-013)

| ID | Requisito | Estado |
|---|---|---|
| RNF-070 | Cumplir GDPR | **MUST CONFIRMADO (DEC-013)** — derecho al olvido, portabilidad, DPA, retención mínima legal (DEC-019) |
| RNF-071 | Controles SOC 2 Type II (sin certificación V1) | **MUST CONFIRMADO (DEC-013)** — controles documentados y aplicados; certificación formal post-V1 |
| RNF-072 | CIS Docker Benchmark aplicado | **MUST CONFIRMADO (DEC-013)** — hardening Docker como verificación obligatoria de security-auditor |
| RNF-073 | OWASP Top 10 + OWASP ASVS Nivel 2 en capa de auth | **MUST CONFIRMADO (DEC-013)** — ASVS L2 verifica la robustez del stack OAuth2/JWT |
| RNF-074 | LGPD (Brasil) | **WON'T V1** (no hay clientes BR; DEC-017 define escala 1 empresa interna) |
| RNF-075 | HIPAA / PCI-DSS / FedRAMP | **WON'T V1** (aplica en apps huésped específicas, no al Maestro) |

---

## 5. Restricciones

### 5.1 Tecnológicas (inmutables por la premisa)
- Backend: **Laravel 13.x** (PHP 8.3+) — DEC-023. No se migra a otro framework.
- Frontend: **React + Tailwind CSS**. No se migra.
- Auth server: **Laravel Passport** (OAuth2).
- Reverse proxy: **Traefik** con ForwardAuth.
- Container: **Docker** + docker-compose.
- Cloud: **Azure** (VPS + Blob Storage).

### 5.2 Operativas
- **DEC-012**: zero local installs; todo vía Docker.
- **DEC-011**: framework no despliega al VPS; produce artefactos.
- **Equipo**: humano (PO) + Claude Code agentico.
- **Sin deadline** explícito (calidad sobre velocidad).
- **Sin budget USD** formal (cost-analyst registra igual).

### 5.3 De negocio
- Multi-tenant B2B: cada empresa tenant tiene múltiples usuarios y múltiples apps licenciadas.
- **Escala inicial V1 (DEC-017)**: 1 empresa × 7 apps huésped en primeros 12 meses. La arquitectura multi-tenant se mantiene inmutable para habilitar crecimiento sin refactor mayor.
- **Modelo de licenciamiento V1 (DEC-018)**: solo ABM de empresas, usuarios, aplicaciones, clientes×app y usuarios×app. Sin tiers complejos, sin billing, sin pricing.
- **Retención (DEC-019)**: mínimos legales estrictos (30 días backups, 90 días post-destrucción). Purga agresiva pasados esos plazos.
- **Disponibilidad (DEC-020)**: V1 no exige zero-downtime. Ventanas de mantenimiento permitidas, preferentemente fuera de horario laboral del tenant. SLA 99.5% se mantiene.
- **Soporte (DEC-021)**: el canal de soporte a clientes finales se gestiona fuera del Maestro. Sin ticket system ni SLA de respuesta integrado V1.
- Idioma V1: español únicamente (DEC-014).
- Stakeholders: 5 grupos identificados en RESEARCH_FINDINGS.md.

---

## 6. Fuera de Alcance V1

Resumen consolidado (detalle en §3.4):
- **Escala y arquitectura** — RF-900: multi-region/HA activa-activa; RF-901: auto-scaling horizontal; RF-902: Kubernetes.
- **Deploy y release** — RF-903: canary/blue-green; RF-907: despliegue automático al VPS (DEC-011).
- **Negocio** — RF-904: marketplace público; RF-905: facturación integrada; RF-911: pricing/tiers complejos (DEC-018); RF-912: SLA de soporte integrado (DEC-021).
- **Extensibilidad** — RF-906: plugins.
- **Seguridad adicional** — RF-908: MFA propio TOTP (DEC-016).
- **Usabilidad** — RF-909: WCAG AA (DEC-015); RF-910: i18n (DEC-014).
- **Compliance extra** — LGPD, HIPAA, PCI-DSS, FedRAMP (§4.7).

---

## 7. Asunciones documentadas

1. El repositorio destino está limpio; partimos desde el template Tailwise Laravel.
2. El humano tiene acceso administrativo a Microsoft Entra ID para registrar una App Registration del Maestro.
3. El dominio del Maestro está (o estará) disponible con capacidad de agregar subdominios tipo `{app}-{company}.maestro.dominio` para Traefik.
4. Azure Blob Storage y un Service Principal para backups son aprovisionables por el humano antes de Fase 04 (Delivery).
5. PostgreSQL es la BD preferida para el Maestro y para apps huésped por defecto (confirmar en Planning con data-architect).
6. El tenant inicial (DEC-017) es probablemente LLyAsoc o similar; las 7 apps huésped iniciales son herramientas internas de ese tenant.

---

## 8. Priorización MoSCoW — Resumen (VALIDADA 2026-04-16)

### Funcionales
| Categoría | Cantidad | IDs |
|---|---|---|
| MUST HAVE | 62 | RF-001 a RF-122 (dispersos por épicas A–M) |
| SHOULD HAVE | 4 | RF-201 a RF-204 |
| COULD HAVE | 4 | RF-300 a RF-303 |
| WON'T HAVE V1 | 13 | RF-900 a RF-912 |
| **Total RF** | **83** | |

### No funcionales
| Categoría | Cantidad |
|---|---|
| Rendimiento (RNF-001 a RNF-008) | 8 |
| Seguridad (RNF-010 a RNF-020) | 11 |
| Escalabilidad/disponibilidad (RNF-030 a RNF-034) | 5 |
| Compatibilidad/portabilidad (RNF-040 a RNF-043) | 4 |
| Usabilidad (RNF-050 a RNF-053) | 4 |
| Observabilidad (RNF-060 a RNF-063) | 4 |
| Compliance (RNF-070 a RNF-075) | 6 |
| **Total RNF** | **42** |

### Gran total: 125 requisitos formalizados

> ✅ **VALIDADA por humano (Product Owner) el 2026-04-16** vía DEC-013 a DEC-021. Registrada en `framework-agentico/agents/CHECKPOINT_GLOBAL.md` y en `framework-agentico/agents/01-discovery/CHECKPOINT.md`.

---

## 9. Cierre de Discovery

Todos los gaps de información del RESEARCH_FINDINGS.md §8 fueron resueltos:

| Pregunta | Resolución |
|---|---|
| Jurisdicciones / compliance | DEC-013: GDPR + SOC 2 Type II controles + CIS Docker + OWASP ASVS L2 |
| Volumen 12 meses | DEC-017: 1 empresa × 7 apps |
| Modelo de pricing | DEC-018: solo ABM, sin billing V1 |
| Retención | DEC-019: mínimos legales estrictos |
| Ventanas de mantenimiento | DEC-020: las menores posibles, no zero-downtime |
| Idiomas | DEC-014: solo español |
| Accesibilidad | DEC-015: WON'T V1 |
| Soporte a clientes | DEC-021: fuera del alcance del Maestro |
| MFA propio | DEC-016: WON'T V1 (Entra ID cubre MFA) |

Fase 01 Discovery queda **completada**. Los artefactos se entregan como input a Fase 02 (Planning) para que software-architect, data-architect, api-designer y ux-designer tomen decisiones técnicas.
