# Preset: Maestro Platform

> **Tipo:** Preset activable
> **Activación:** El humano lo activa al construir la plataforma Maestro misma (no una app huésped)
> **Efecto:** Invierte el preset `web-maestro` — cada restricción que ese impone a las apps huésped, aquí se convierte en una obligación que el Maestro debe **producir, emitir, validar o imponer**.
> **Relación con `web-maestro`:** Son duales. Toda app construida con `web-maestro` depende de que el Maestro construido con `maestro-platform` cumpla su lado del contrato.

---

## Descripción

Este preset se activa cuando el proyecto es la **plataforma Maestro** (el orquestador multi-tenant que aloja apps dockerizadas), no una aplicación huésped. El Maestro es:

- **Identity Provider único** del ecosistema (Laravel Passport OAuth2 + JWT + Microsoft Entra ID + usuario/contraseña).
- **Motor de provisioning** de contenedores, redes Docker aisladas y bases de datos dedicadas por instancia.
- **Reverse proxy manager** (Traefik + ForwardAuth + TLS Let's Encrypt).
- **Gateway inter-apps** con registro y verificación de permisos.
- **Definidor y validador** del contrato `maestro.yaml` que las apps huésped deben cumplir.
- **Emisor** de los headers `X-Auth-User-Id`, `X-Auth-User-Email`, `X-Auth-Company-Id`, `X-Auth-Roles`, `X-Auth-Permissions`.
- **Receptor** de los health checks que las apps exponen.
- **Dueño** de la tabla canónica `users`, `companies`, `applications` y las tres tablas pivote M-M.

Al activar este preset, todos los agentes del framework reciben obligaciones adicionales que garantizan que el Maestro cumpla simétricamente el contrato que `web-maestro` exige a las apps.

---

## Documentos de Referencia

- `PremisaWebMaestro/00-INDICE-MAESTRO.md` — índice maestro
- `PremisaWebMaestro/01-PREMISAS-Y-NO-NEGOCIABLES.md` — constitución del proyecto
- `PremisaWebMaestro/02-MODELO-DE-DATOS.md` — entidades y relaciones canónicas
- `PremisaWebMaestro/03-AUTENTICACION-Y-AUTORIZACION.md` — sistema de identidad
- `PremisaWebMaestro/04-INFRAESTRUCTURA-DOCKER.md` — topología de redes, ciclo de vida
- `PremisaWebMaestro/05-PORTAL-Y-RENDERIZADO.md` — shell React + iframes + postMessage
- `PremisaWebMaestro/06-SDK-Y-CONTRATO.md` — schema `maestro.yaml`, SDKs, CLI
- `PremisaWebMaestro/07-SISTEMA-AGENTICO.md` — jerarquía de agentes IA para apps huésped
- `PremisaWebMaestro/08-CICD-Y-GOBERNANZA.md` — pipelines y protecciones
- `PremisaWebMaestro/09-SEGURIDAD.md` — defensa en profundidad
- `PremisaWebMaestro/10-OBSERVABILIDAD.md` — stack de monitoreo
- `PremisaWebMaestro/11-PLAN-DE-IMPLEMENTACION.md` — fases cronológicas
- `framework-agentico/agents/presets/web-maestro/PRESET.md` — preset dual (lado app huésped)

---

## Impacto por Fase

```yaml
00-setup:
  - verificar SOLO: Docker, Docker Compose, git, IDE (VSCode o equivalente), acceso al repo
  - NO instalar PHP, Composer, Node.js, ni clientes de BD en el host (DEC-012)
  - toolchain ejecutable exclusivamente via contenedores (`docker compose run --rm <servicio> <comando>`)
  - cliente gráfico de BD (DBeaver, DataGrip, TablePlus) en el host es opcional y aceptado
  - NO verificar VPS Azure: gestionado por el humano por fuera del framework (DEC-011)
  - todo el trabajo es local-dockerizado; el framework genera artefactos de deploy, no despliega

01-discovery:
  - tratar los 10 no-negociables de la premisa como requisitos no funcionales obligatorios
  - identificar regulaciones aplicables (cliente no ha definido; compliance-analyst investiga GDPR/LGPD/ISO27001)
  - mapear stakeholders: empresas tenant, usuarios finales, devs de apps, admins Maestro, C-Level
  - documentar métricas objetivo: 50 usuarios concurrentes V1, latencia ForwardAuth <50ms p95, cold start <15s

02-planning:
  - ADRs obligatorios: Laravel Passport vs alternativa, elección de BD del Maestro, estrategia de cifrado AES-256, Traefik como reverse proxy, estrategia de redes Docker por instancia
  - modelo de datos: entidades canónicas users, companies, applications + pivots M-M + oauth_* (Passport) + instances + audit_log inmutable + backups_registry
  - contratos de API: /api/auth/*, /api/companies, /api/users, /api/applications, /api/instances/*, /api/apps/register, /api/inventory/context, /api/gateway/*
  - threat model OBLIGATORIO: superficie de ataque multi-tenant, escalada de privilegios entre tenants, inyección vía headers X-Auth-*, tampering del token JWT
  - UX: shell React portal, selector de empresa activa, iframe + postMessage, pantalla cold start, manejo de errores por estado
  - OBLIGATORIO: diseñar `docker-compose.dev.yml` 100% portátil (sin dependencia de PHP/Node en host) (DEC-012)
  - OBLIGATORIO: producir `docs/CONVENCIONES_PLATAFORMA.md` con convenciones de puertos, redes Docker, volúmenes, naming de contenedores, subdominios y variables de entorno que eviten colisiones entre Maestro y apps huésped

03-development:
  - IMPLEMENTAR Laravel Passport como OAuth2 server emisor de JWT
  - IMPLEMENTAR /api/auth/login (user/pass) y OAuth2 flow con Microsoft Entra ID
  - IMPLEMENTAR /api/auth/validate (consumido por Traefik ForwardAuth) que retorna headers X-Auth-*
  - CREAR tablas canónicas users, companies, applications + 3 tablas pivote M-M + oauth_* + instances + audit_log
  - IMPLEMENTAR audit log INMUTABLE (solo INSERT; triggers que rechazan UPDATE/DELETE a nivel BD)
  - IMPLEMENTAR cifrado AES-256 de secretos en BD del Maestro
  - IMPLEMENTAR motor de provisioning de instancias (Docker API, redes aisladas, BDs dedicadas, credenciales random 32+ chars)
  - IMPLEMENTAR máquina de estados del ciclo de vida de instancia
  - IMPLEMENTAR health checks periódicos + auto-restart tras 3 fallos consecutivos
  - IMPLEMENTAR portal React con shell, sidebar, iframe, postMessage, cold start screen
  - IMPLEMENTAR gateway inter-apps con registro en audit log
  - PUBLICAR JSON Schema de maestro.yaml como validador canónico
  - IMPLEMENTAR SDK Node.js @maestro/sdk-node (middleware auth, filtro tenant, helpers permisos)
  - IMPLEMENTAR CLI maestro-cli con comandos validate y new
  - IMPLEMENTAR endpoint /api/apps/register para registro automático de apps desde CI/CD
  - IMPLEMENTAR hooks salientes on_user_added / on_user_removed firmados con HMAC-SHA256

04-delivery:
  - Dockerfile del Maestro multi-stage, non-root, HEALTHCHECK (el Maestro se impone a sí mismo lo que exige a las apps)
  - docker-compose.yml con Traefik, Maestro, BD del Maestro, Redis (levantable localmente)
  - pipeline CI/CD en .github/workflows con validación, tests, build y escaneo
  - configuración de Traefik con ForwardAuth, TLS Let's Encrypt, redirect HTTP→HTTPS, HSTS, rate limiting 100 req/min/IP
  - scripts/documentación de deployment para Azure VPS (el despliegue al VPS lo ejecuta el humano; el framework solo produce los artefactos)
  - rama main protegida (PR + review)

05-operations:
  - stack de observabilidad: Prometheus, cAdvisor, Loki, Promtail, Grafana
  - dashboards: ejecutivo, por instancia, del Maestro
  - alertas con canales Slack y email
  - runbooks operativos: instancia no responde, VPS sin espacio, cert TLS no renueva, BD Maestro caída, rollback de app
  - política de backups: diario 2-4am, cifrado, Azure Blob Storage, retención >=30 días
  - logs centralizados con company_id filtrable + audit log consultable

06-retrospective:
  - documentar patterns del Maestro para referencia del equipo
  - consolidar ADRs, threat model, runbooks
  - registrar lecciones aprendidas sobre multi-tenancy seguro

transversal:
  security-auditor:
    - auditar los 10 no-negociables de la premisa como checklist obligatorio
    - validar defensa en profundidad (red + middleware + cifrado)
    - validar que Traefik no tenga rutas que bypass ForwardAuth
    - validar que credenciales de BD por instancia sean únicas y >=32 chars
    - validar que audit_log tenga triggers DB contra UPDATE/DELETE
    - validar ausencia de secretos en código y en imagen Docker
  qa-tester:
    - testear flujo completo: login → JWT → ForwardAuth → headers inyectados en app huésped
    - testear aislamiento entre tenants (Tenant A no puede leer datos de Tenant B)
    - testear ciclo de vida completo de instancia: crear → ejecutar → dormir → despertar → destruir → restaurar
    - testear OAuth2 con Microsoft Entra ID
    - testear health checks y auto-restart
    - testear rate limiting y headers de seguridad
  compliance-analyst:
    - investigar GDPR/LGPD/ISO27001/SOC2 aplicables (abierto desde Discovery)
    - validar política de retención 90 días post-destrucción de instancia
    - validar audit log cumple requisitos regulatorios
  performance-analyst:
    - verificar latencia ForwardAuth <50ms p95 (objetivo de la premisa)
    - verificar cold start <15s para instancias dormidas
    - verificar cache hit rate >90% en validación de tokens (Redis)
    - dimensionar para SLA V1 de 50 usuarios concurrentes
```

---

## Diferencias Clave con el Preset `web-maestro`

| Dimensión | `web-maestro` (app huésped) | `maestro-platform` (Maestro mismo) |
|---|---|---|
| Login | **Prohibido** implementar login propio | **Obligatorio** implementar Passport OAuth2 + Microsoft Entra ID |
| Tabla users/sessions | **Prohibido** crearlas | **Obligatorio** mantenerlas como canónicas |
| Tokens OAuth/JWT | **Prohibido** almacenarlos | **Obligatorio** emitirlos, almacenarlos cifrados y validarlos |
| Headers X-Auth-* | **Obligatorio** consumirlos | **Obligatorio** emitirlos vía endpoint /api/auth/validate |
| Endpoint /health | **Obligatorio** exponerlo | **Obligatorio** consumirlo y actuar sobre él (auto-restart) |
| Contrato maestro.yaml | **Obligatorio** cumplirlo | **Obligatorio** definirlo, publicar schema y validarlo |
| DATABASE_URL | **Obligatorio** leerla del env | **Obligatorio** generarla, inyectarla y cifrar credenciales |
| Docker socket | **Prohibido** montarlo | **Obligatorio** usarlo (vía servicio dedicado mínimo-privilegio) desde el motor de provisioning |
| Comunicación inter-apps | **Prohibido** URL directa | **Obligatorio** proveer gateway inter-apps |
| Límites de recursos | **Obligatorio** respetarlos | **Obligatorio** imponerlos vía flags Docker |
| Ejecución como root | **Prohibido** | **Prohibido** también (el Maestro se autoimpone la regla) |
| Audit log | Opcional | **Obligatorio e inmutable** (INSERT-only, triggers DB) |
| Backups | No aplica (stateless desde la app) | **Obligatorio** diarios cifrados >=30 días retención |

---

## Artefactos que el Preset Genera y Valida

```yaml
generados_por_el_framework_agentico:
  backend_laravel:
    - migraciones de BD con entidades canónicas + tablas Passport + audit_log + instances
    - modelos Eloquent con relaciones M-M, scopes, soft delete, cifrado de campos sensibles
    - endpoints de autenticación (/api/auth/login, /api/auth/microsoft, /api/auth/validate, /api/auth/refresh, /api/auth/logout)
    - endpoints CRUD (/api/companies, /api/users, /api/applications, /api/licenses)
    - endpoints de instancias (/api/instances/create, /stop, /start, /destroy)
    - endpoints de registro de apps (/api/apps/register)
    - endpoints de gateway inter-apps (/api/gateway/*)
    - endpoint de inventario (/api/inventory/context)
    - motor de provisioning (servicio Laravel + Docker API)
    - jobs periódicos de health check con auto-restart escalonado
    - middleware de emisión de headers X-Auth-*
    - hooks salientes on_user_added, on_user_removed firmados HMAC
    - audit log con triggers DB INSERT-only
    - cifrado AES-256 de secretos

  frontend_react:
    - shell del portal con barra superior + sidebar + área de contenido
    - selector de empresa activa con cambio de contexto JWT
    - renderizador de iframes con transferencia de token vía postMessage
    - pantalla cold start con tiempo estimado
    - pantalla de bienvenida para usuarios sin apps
    - manejo visual de errores por estado (app caída, licencia expirada, token expirado, sin conexión)
    - flujo de login user/pass + botón Microsoft

  infraestructura:
    - docker-compose con Traefik, Maestro, BD Maestro, Redis
    - configuración Traefik: ForwardAuth, TLS, HSTS, rate limiting, redirect HTTP→HTTPS
    - Dockerfile multi-stage non-root con HEALTHCHECK
    - scripts de deployment para Azure VPS
    - stack de observabilidad (Prometheus, cAdvisor, Loki, Promtail, Grafana)
    - dashboards y reglas de alertas

  sdk_y_cli:
    - @maestro/sdk-node con middleware de auth + filtro tenant + helpers permisos
    - maestro-cli con comandos validate, new
    - JSON Schema oficial de maestro.yaml publicado
    - repositorio template de GitHub para apps huésped
    - CLAUDE.md generador para apps huésped (hereda reglas de la plataforma)

generados_por_humanos_o_portal_externo:
  - credenciales iniciales de Microsoft Entra ID (humano entrega al equipo dev)
  - certificados TLS wildcard para el dominio (si no se usa Let's Encrypt por instancia)
  - secretos Azure (subscription ID, tenant ID, service principal) para despliegue IaC

validados_por_el_framework:
  - maestro.yaml de apps huésped contra JSON Schema (en fase 5-6, via maestro-cli)
  - Dockerfiles de apps huésped (USER no-root, HEALTHCHECK presente)
  - imágenes Docker de apps huésped (scan de vulnerabilidades en CI/CD)
```

---

## No-Negociables Heredados de la Premisa

Los 10 no-negociables del documento `01-PREMISAS-Y-NO-NEGOCIABLES.md` aplican al Maestro como obligaciones de construcción y validación:

1. **Zero Trust en autenticación** → ForwardAuth en Traefik sin rutas que lo bypass
2. **Aislamiento de red por instancia** → redes Docker dedicadas creadas en el provisioning
3. **Health check obligatorio** → validador en maestro-cli + verificación runtime
4. **Prohibición root en contenedores** → validación estática del Dockerfile en CI/CD + flag no-new-privileges
5. **Secretos nunca en código** → pre-commit hooks + scan profundo CI/CD + AES-256 en BD
6. **Límites de recursos declarados** → maestro.yaml obligatorio + flags Docker
7. **Base de datos dedicada por instancia** → provisioning genera BD + usuario + pass 32 chars
8. **TLS obligatorio** → Traefik + Let's Encrypt + HSTS
9. **Audit log inmutable** → tabla INSERT-only + triggers DB
10. **Backup automatizado >=30 días** → job diario + Azure Blob Storage cifrado
