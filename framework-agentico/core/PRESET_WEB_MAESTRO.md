# Preset: Web Maestro (Siempre Activo)

> **Estado:** Permanentemente activo para todos los proyectos
> **Plataforma:** Orquestador de aplicaciones dockerizadas multi-tenant

---

## Descripcion

Todas las aplicaciones gestionadas por este framework corren dentro de la plataforma Web Maestro. El Maestro es un orquestador de aplicaciones dockerizadas multi-tenant que provee autenticacion centralizada, provisioning de infraestructura y gateway inter-apps.

Las constraints de este preset son NO NEGOCIABLES y deben incluirse en cada Context Packet que el PM envia a los orquestadores.

---

## Constraints por Fase

### Fase 00 — Setup
- Verificar cuenta GitHub vinculada al portal Maestro
- Verificar acceso al repo generado por el portal
- Verificar template del stack intacto

### Fase 01 — Discovery
- Incluir requisitos obligatorios del contrato Maestro como no negociables
- Considerar aislamiento multi-tenant como requisito de compliance
- Consultar /api/inventory/context si esta disponible

### Fase 02 — Planning
- Auth por headers (X-Auth-*), NO login propio
- NO tabla users ni sessions
- BD del pool o dedicada segun carga
- maestro.yaml obligatorio
- Hooks del Maestro contemplados
- Gateway inter-apps contemplado si hay comunicacion entre apps
- Limites de recursos: max 4GB RAM, 4 CPU cores

### Fase 03 — Development
Obligatorio implementar:
- Middleware de auth que lea: X-Auth-User-Id, X-Auth-User-Email, X-Auth-Company-Id, X-Auth-Roles, X-Auth-Permissions
- Rechazar 401 sin headers de auth
- GET /health retorna 200 {"status":"ok"} sin auth
- Filtrar TODOS los queries por company_id (multi-tenancy)
- Leer DATABASE_URL del environment
- Implementar hooks si estan definidos en maestro.yaml
- Verificar X-Maestro-Webhook-Secret en hooks

Prohibido:
- NO hardcodear credenciales
- NO crear tablas users/sessions
- NO almacenar tokens OAuth/JWT de usuarios

### Fase 04 — Delivery
- Dockerfile multi-stage, non-root, con HEALTHCHECK
- NO --privileged, NO docker.sock
- NO puertos < 1024
- .dockerignore excluye .git, node_modules, .env*, logs
- Pipeline en .github/workflows/deploy.yml
- Rama main protegida (PR + review)
- maestro.yaml validado contra schema

### Fase 05 — Operations
- Logs incluyen company_id para filtrar por tenant
- NO loguear contenido de headers X-Auth-*
- Considerar health checks externos del Maestro
- Distinguir errores de app vs errores de gateway

### Fase 06 — Retrospective
- Documentar lecciones de integracion con Maestro
- Registrar patterns especificos del preset para futuros proyectos

---

## Constraints para Validadores Transversales

```yaml
security-auditor:
  - Verificar TODAS las prohibiciones listadas arriba
  - Validar que no haya tabla users/sessions
  - Validar que no se hardcodeen credenciales
  - Validar manejo correcto de headers X-Auth-*

qa-tester:
  - Testear middleware de auth (401 sin headers, 200 con headers validos)
  - Testear health check endpoint
  - Testear aislamiento de datos por company_id

compliance-analyst:
  - Validar multi-tenancy seguro (aislamiento de datos entre tenants)
  - Validar politicas de retencion del Maestro

performance-analyst:
  - Validar que queries filtran por company_id (no full table scans cross-tenant)
  - Validar limites de recursos (4GB RAM, 4 CPU cores)
```

---

## Artefactos

```yaml
generados_por_portal_maestro:
  - maestro.yaml (el framework solo valida, no genera)
  - Template del stack (repo generado por el portal)
  - Pipeline CI/CD base

generados_por_el_framework:
  - Middleware de auth
  - Health check endpoint
  - Hooks endpoints (si aplica)
  - Dockerfile compatible
  - Tests de integracion con el contrato
```

---

## Documentos de Referencia

Si estan disponibles en el repo:
- ARQUITECTURA_APLICACIONES_GENERICAS.md — Contrato universal de integracion
- POLITICA_REUSO_CONTENEDORES.md — Politica de reuso de recursos del Maestro
