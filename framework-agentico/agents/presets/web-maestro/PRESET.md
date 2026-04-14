# Preset: Web Maestro

> **Tipo:** Preset activable  
> **Activación:** El humano lo activa al inicio del proyecto  
> **Efecto:** Extiende las reglas generales con las restricciones del contrato de integración Web Maestro

---

## Descripción

Este preset se activa cuando la aplicación a desarrollar va a correr dentro de la plataforma Web Maestro. El Maestro es un orquestador de aplicaciones dockerizadas multi-tenant que provee autenticación centralizada, provisioning de infraestructura y gateway inter-apps.

Al activar este preset, todos los agentes del framework reciben restricciones adicionales que garantizan compatibilidad con el contrato de integración del Maestro.

---

## Documentos de Referencia

- `ARQUITECTURA_APLICACIONES_GENERICAS.md` — Contrato universal de integración
- `POLITICA_REUSO_CONTENEDORES.md` — Política de reuso de recursos del Maestro

---

## Impacto por Fase

```yaml
00-setup:
  - verificar cuenta GitHub vinculada al portal Maestro
  - verificar acceso al repo generado por el portal
  - verificar template del stack intacto

01-discovery:
  - consultar /api/inventory/context para conocer estado de la plataforma
  - incluir requisitos obligatorios del contrato Maestro como no negociables
  - considerar aislamiento multi-tenant como requisito de compliance

02-planning:
  - auth por headers (X-Auth-*), NO login propio
  - NO tabla users ni sessions
  - BD del pool o dedicada según carga
  - maestro.yaml obligatorio
  - hooks del Maestro contemplados
  - gateway inter-apps contemplado si hay comunicación entre apps
  - considerar limits de recursos (máx 4GB RAM, 4 CPU cores)

03-development:
  - middleware de auth que lea X-Auth-User-Id, X-Auth-User-Email, X-Auth-Company-Id, X-Auth-Roles, X-Auth-Permissions
  - rechazar 401 sin headers
  - GET /health retorna 200 {"status":"ok"} sin auth
  - filtrar TODOS los queries por company_id
  - leer DATABASE_URL del environment
  - implementar hooks si están definidos en maestro.yaml
  - verificar X-Maestro-Webhook-Secret en hooks
  - NO hardcodear credenciales
  - NO crear tablas users/sessions
  - NO almacenar tokens OAuth/JWT de usuarios

04-delivery:
  - Dockerfile multi-stage, non-root, con HEALTHCHECK
  - NO --privileged, NO docker.sock
  - NO puertos < 1024
  - .dockerignore excluye .git, node_modules, .env*, logs
  - pipeline en .github/workflows/deploy.yml
  - rama main protegida (PR + review)
  - maestro.yaml validado contra schema
  - checklist de entrega sección 19 del contrato

05-operations:
  - logs incluyen company_id para filtrar por tenant
  - NO loguear contenido de headers X-Auth-*
  - considerar health checks externos del Maestro
  - distinguir errores de app vs errores de gateway

06-retrospective:
  - documentar lecciones de integración con Maestro
  - registrar patterns específicos del preset para futuros proyectos

transversal:
  security-auditor:
    - verificar TODAS las prohibiciones de sección 18 del contrato
  qa-tester:
    - testear middleware de auth (401 sin headers, 200 con headers)
    - testear health check
    - testear aislamiento de datos por company_id
  compliance-analyst:
    - validar multi-tenancy seguro
    - validar políticas de retención del Maestro
```

---

## Artefactos que el Preset Valida (no genera)

```yaml
generados_por_portal_maestro:
  - maestro.yaml (el framework solo valida)
  - CLAUDE.md (el framework solo valida)
  - template del stack (repo generado por el portal)
  - pipeline CI/CD base

generados_por_el_framework:
  - middleware de auth
  - health check endpoint
  - hooks endpoints (si aplica)
  - Dockerfile compatible
  - tests de integración con el contrato
```
