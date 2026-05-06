# Preset: Maestro Platform v2

> **Tipo:** Preset activable
> **Activación:** El humano lo activa al construir un Maestro v2 (no una app huésped v4).
> **Framework agéntico:** v4
> **Reemplaza a:** Preset `maestro-platform` v1 (que asumía Maestro como Identity Provider con headers `X-Auth-*`).
> **Relación con `web-maestro` v4:** Son duales. Toda app construida con `web-maestro` v4 depende de que el Maestro construido con `maestro-platform-v2` cumpla su lado del contrato `maestro.platform/v2`.

---

## Descripción

Este preset se activa cuando el proyecto es la **plataforma Maestro v2** (orquestador de aplicaciones huésped single-tenant), no una aplicación huésped. El Maestro v2 es un **registry + redirector**, NO un Identity Provider:

- **Registry**: mantiene un catálogo de aplicaciones registradas, empresas, deployments (un deployment = una app + una empresa = un contenedor), URLs, puertos, estado.
- **Redirector**: cuando un usuario hace click en una app desde el portal del Maestro, el Maestro abre la URL del deployment en `target="_blank"`. NO maneja la sesión del usuario.
- **Provisioner**: provisiona contenedores Docker, redes aisladas y BDs dedicadas por deployment.
- **Brand consumer**: consume el endpoint `/maestro/branding` de cada app (autenticando con `X-Maestro-Api-Key`) para obtener nombre y logos de cada empresa.
- **Hook emitter**: emite hooks server-to-server hacia las apps (firmados con `X-Maestro-Webhook-Secret`).
- **NO** es Identity Provider de las apps huesped. Cada app tiene su propio login.
- **NO** inyecta headers `X-Auth-*`. Esa responsabilidad fue deprecada al pasar de v1 a v2.
- **NO** mantiene una tabla `users` global a la que las apps consultan. Cada app tiene su propia tabla `users`.

Al activar este preset, todos los agentes del framework agéntico v4 reciben obligaciones específicas de construir el Maestro v2.

---

## Diferencias clave con el Preset `maestro-platform` (v1)

| Dimensión | `maestro-platform` v1 | `maestro-platform-v2` |
|---|---|---|
| Rol del Maestro | Identity Provider único + Reverse proxy con ForwardAuth | Registry + redirector + provisioner |
| Headers `X-Auth-*` | **Emitidos** vía `/api/auth/validate` consumido por Traefik | **NO emitidos.** Cada app autentica por su cuenta. |
| Tabla `users` global | **Obligatoria** en el Maestro (canónica) | **NO existe** en el Maestro. Cada app tiene la suya. |
| OAuth2 / Passport | Implementación obligatoria con Laravel Passport | NO aplica |
| Microsoft Entra ID | Integración obligatoria | NO aplica (cada app puede integrarlo si lo requiere) |
| Multi-tenancy | Multi-tenant lógico con `company_id` en tablas | Multi-tenant físico: un contenedor por empresa, sin `company_id` |
| Branding | Inyectado por el Maestro al portal | Consumido por el Maestro vía `/maestro/branding` autenticado con `X-Maestro-Api-Key` |
| Autenticación Maestro → App (server) | `X-Maestro-Webhook-Secret` para hooks | + `X-Maestro-Api-Key` para `/maestro/branding` |
| Click en app desde portal | Reverse proxy + iframe + headers inyectados | Abre URL en `target="_blank"`, app gestiona login |
| Hooks salientes (Maestro → App) | Igual: HMAC-SHA256 con secret por app | Igual |
| Audit log inmutable | Obligatorio | Obligatorio (igual) |
| Backups cifrados ≥ 30 días | Obligatorio | Obligatorio (igual) |

---

## Documentos de referencia

- `framework-agentico/CHANGELOG.md` — cambios v3 → v4
- `framework-agentico/core/PRESET_WEB_MAESTRO.md` — preset dual (lado app huésped v4)
- `docs/APP_HUESPED_SPEC_V2.md` — contrato `maestro.platform/v2` (lado app)
- `docs/APP_HUESPED_BEST_PRACTICES_V2.md` — recomendaciones
- `docs/CONVENCIONES_PLATAFORMA_V2.md` — convenciones (naming, redes, env vars)
- `framework-agentico/phases/05-seeding.md` — fase de seeding (las apps tienen seeder; el Maestro tambien)
- `framework-agentico/migration/v3-to-v4.md` — proceso de migración

---

## Impacto por fase

```yaml
00-setup:
  - verificar SOLO: Docker, Docker Compose, git, IDE
  - NO instalar runtimes en el host (mismo principio v1)
  - toolchain ejecutable exclusivamente via contenedores
  - el VPS / cloud lo gestiona el humano por fuera del framework

01-discovery:
  - tratar las premisas v2 como requisitos no funcionales obligatorios
  - identificar regulaciones aplicables (compliance-analyst investiga)
  - mapear stakeholders: empresas tenant, usuarios finales, devs de apps huesped, admins Maestro
  - documentar metricas objetivo: latencia de redireccion < 200ms, tiempo de provisioning de deployment < 60s

02-planning:
  - ADRs obligatorios:
    - eleccion de BD del Maestro (PostgreSQL recomendado)
    - reverse proxy (Traefik con TLS Let's Encrypt; ya NO requiere middleware ForwardAuth)
    - estrategia de provisioning (Docker API)
    - estrategia de cifrado AES-256 para secretos del Maestro
    - estrategia de redes Docker por deployment
  - modelo de datos del Maestro v2:
    - companies (empresas registradas)
    - applications (apps en el catálogo, con metadata de SPEC v2)
    - deployments (instancias activas: app + empresa + contenedor + BD + estado)
    - api_keys (X-Maestro-Api-Key por deployment, rotables)
    - webhook_secrets (X-Maestro-Webhook-Secret por deployment, rotables)
    - audit_log inmutable
    - admin_users (usuarios del Maestro mismo, con su propio login segun preset web-maestro v4 — el Maestro v2 ES una app huesped de si mismo)
  - contratos de API:
    - /api/v2/apps/register (apps se auto-registran desde CI)
    - /api/v2/companies (CRUD)
    - /api/v2/deployments/* (lifecycle)
    - /api/v2/portal/my-apps (portal queries)
    - /api/v2/branding/refresh (forzar refresh del cache de branding)
  - threat model: bypass del registry, escalada de privilegios admin, leak de api keys, leak de webhook secrets
  - UX: shell del portal con grid de apps disponibles. Click abre URL en target="_blank".

03-development:
  - IMPLEMENTAR el catálogo: companies, applications, deployments
  - IMPLEMENTAR motor de provisioning (Docker API: redes aisladas, BDs dedicadas, ENV vars inyectadas)
  - IMPLEMENTAR generacion + inyeccion de MAESTRO_API_KEY y MAESTRO_WEBHOOK_SECRET por deployment
  - IMPLEMENTAR consumo del endpoint /maestro/branding de cada app (con X-Maestro-Api-Key)
  - IMPLEMENTAR cache de branding por deployment (TTL razonable, invalidacion via /api/v2/branding/refresh)
  - IMPLEMENTAR portal con grid de apps disponibles para el usuario admin del Maestro
  - IMPLEMENTAR redireccion: cuando el usuario hace click, abrir URL en target="_blank" (no iframe)
  - IMPLEMENTAR hooks salientes (on_user_added, on_user_removed) firmados con HMAC-SHA256
  - IMPLEMENTAR endpoint /api/v2/apps/register para self-registration desde CI/CD
  - IMPLEMENTAR JSON Schema oficial de maestro.yaml v2 publicado
  - IMPLEMENTAR maestro-cli con comandos validate (v2) y new (template v4)
  - IMPLEMENTAR audit log INMUTABLE (triggers DB rechazan UPDATE/DELETE)
  - IMPLEMENTAR cifrado AES-256 de secretos en BD
  - El Maestro v2 mismo cumple el preset web-maestro v4 para SU PROPIO LOGIN (auth propia para admins del Maestro)

04-delivery:
  - Dockerfile multi-stage non-root con HEALTHCHECK
  - docker-compose con Traefik, Maestro v2, BD del Maestro, Redis (opcional)
  - pipeline CI/CD en .github/workflows
  - Traefik: TLS Let's Encrypt, redirect HTTP→HTTPS, HSTS, rate limiting
  - SIN ForwardAuth (no aplica en v2): Traefik solo enruta tráfico
  - rama main protegida (PR + review)
  - ENV vars obligatorias: DATABASE_URL, MAESTRO_ENCRYPTION_KEY, APP_KEY/JWT_SECRET para auth de admins, SUPERADMIN_INITIAL_PASSWORD para el seed del admin del Maestro

05-seeding:
  - El Maestro v2 mismo arranca con un usuario superadmin admin@llyasoc.com (seeder idempotente)
  - Si el PO lo requiere, sembrar empresas iniciales y/o admins adicionales
  - Validacion transversal: security-auditor + qa-tester + compliance-analyst aprueban el seed

06-operations:
  - stack de observabilidad: Prometheus, Loki, Grafana
  - dashboards: ejecutivo del Maestro, deployments individuales, salud del registry
  - alertas: deployment unhealthy, /maestro/branding 5xx, hooks failures
  - runbooks: deployment caido, BD del Maestro caída, Traefik no renueva cert
  - backups diarios cifrados, retencion >= 30 dias
  - logs: incluir user_id (admin) y request_id en logs del Maestro mismo

07-retrospective:
  - documentar patterns del Maestro v2
  - consolidar ADRs y runbooks
  - lecciones de migracion del modelo v1 (si aplica)

transversal:
  security-auditor:
    - validar que no haya tabla users global con auth de usuarios de apps (eso es responsabilidad de cada app)
    - validar manejo de secretos de los deployments (api_keys, webhook_secrets cifrados)
    - validar audit log inmutable
    - validar TLS y headers de seguridad en Traefik
    - validar que el endpoint /api/v2/apps/register tiene su propio mecanismo de auth (token de registro)
  qa-tester:
    - testear ciclo completo: registrar app → licenciar a empresa → provisionar deployment → consumir /maestro/branding → click en portal
    - testear hooks: on_user_added llega correctamente firmado
    - testear rotacion de api_key sin downtime
    - testear que el seed del Maestro mismo es idempotente
  compliance-analyst:
    - GDPR/LGPD/ISO27001/SOC2 segun aplicabilidad
    - validar politica de retencion de backups y de deployments destruidos
    - validar audit log
  performance-analyst:
    - latencia de redireccion < 200ms
    - tiempo de provisioning de deployment < 60s
    - tiempo de consumo de /maestro/branding (con cache) < 50ms
```

---

## Artefactos que el preset genera y valida

```yaml
generados_por_el_framework_agentico:
  backend:
    - migraciones de BD del Maestro (companies, applications, deployments, api_keys, webhook_secrets, audit_log, admin_users)
    - modelos de dominio del registry
    - endpoints de admin del Maestro: /api/v2/companies, /api/v2/applications, /api/v2/deployments
    - endpoint /api/v2/apps/register para self-registration desde CI/CD de apps huesped
    - endpoint /api/v2/portal/my-apps para el portal
    - endpoint /api/v2/branding/refresh para forzar cache
    - motor de provisioning (servicio + Docker API)
    - jobs periodicos de health check de deployments
    - jobs periodicos de refresh de branding (consumo de /maestro/branding de cada app)
    - hooks salientes on_user_added, on_user_removed firmados HMAC
    - audit log con triggers DB INSERT-only
    - cifrado AES-256 de api_keys y webhook_secrets
    - middleware de admin auth (login propio del Maestro v2 para sus admins)
    - seeder del superadmin del Maestro (admin@llyasoc.com)

  frontend:
    - portal React con grid de apps registradas
    - selector de empresa (los admins del Maestro pueden ver vista de cada empresa)
    - preview del branding por deployment
    - acciones: registrar empresa, licenciar app, provisionar deployment, suspender, destruir
    - vista de audit log
    - login propio del Maestro v2 para sus admins

  infraestructura:
    - docker-compose con Traefik, Maestro v2, BD Maestro, Redis (opcional)
    - configuracion Traefik: TLS, HSTS, rate limiting (SIN ForwardAuth)
    - Dockerfile multi-stage non-root
    - scripts de deployment a cloud
    - stack de observabilidad

  cli_y_sdk:
    - maestro-cli con comandos: validate (v2 schema), new (template v4)
    - JSON Schema oficial de maestro.yaml v2 publicado
    - SDK opcional: librerias de auth/branding helpers (no obligatorias, son convenientes)

generados_por_humanos_o_portal_externo:
  - certificados TLS wildcard (si no se usa Let's Encrypt por subdominio)
  - secretos de cloud para despliegue IaC

validados_por_el_framework:
  - maestro.yaml v2 de apps huesped contra JSON Schema (en CI de las apps)
  - Dockerfiles de apps huesped (USER no-root, HEALTHCHECK)
  - imagenes Docker (scan de vulnerabilidades en CI)
  - endpoint /maestro/branding de cada app (test de integracion en CI)
```

---

## No-negociables del Maestro v2

1. **Single-tenant fisico de las apps huesped**: cada deployment = un contenedor = una empresa. El Maestro NO permite que un deployment sirva a multiples empresas.
2. **Auth propia de las apps**: el Maestro NO inyecta headers de identidad de usuario a las apps. Las apps tienen su propio login.
3. **Auth server-to-server**: toda llamada del Maestro a una app DEBE autenticarse con `X-Maestro-Api-Key` (o `X-Maestro-Webhook-Secret` para hooks).
4. **Audit log inmutable**: triggers DB rechazan UPDATE/DELETE. Toda accion administrativa queda registrada.
5. **Aislamiento de red por deployment**: cada deployment tiene su propia red Docker privada. Su BD esta en esa red privada, no expuesta al Maestro.
6. **Cifrado AES-256** de secretos en BD del Maestro (api_keys, webhook_secrets).
7. **TLS obligatorio** sin excepciones; Let's Encrypt o cert wildcard.
8. **Backups cifrados ≥ 30 dias** retencion.
9. **Login propio del Maestro v2** para sus admins (cumple preset web-maestro v4 a si mismo).
10. **Click en app abre URL en target="_blank"** — NO iframe, NO reverse proxy con inyeccion de headers.

---

## Notas operativas

- El Maestro v2 NO necesita ser construido en este meta-trabajo del framework v4. Este preset esta listo para que un proyecto separado lo use cuando el PO ejecute `/pm:orquestar` y declare el preset activo `maestro-platform-v2`.
- Cuando se construya, el proyecto sigue las 8 fases del framework v4 (00-setup ... 07-retrospective) con este preset activo.
- El Maestro v2 mismo cumple el preset `web-maestro` v4 para SU PROPIO login de admins (es una app huesped de si mismo, en cierto sentido). Pero adicionalmente cumple las obligaciones de este preset por su rol de orquestador.
