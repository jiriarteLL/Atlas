# Reglas Preset Maestro Platform

> ⚠️ **DEPRECADO** — Reglas del preset v3 / contrato `maestro.platform/v1`.
> Conservadas como referencia historica. NO aplicar en proyectos nuevos.
>
> **Version vigente:** `framework-agentico/agents/presets/maestro-platform/rules/RULES.md` (reglas v4, ya canonicas tras el cleanup v4).
> **Razon de la deprecacion:** ver `framework-agentico/CHANGELOG.md` v4.0.
>
> **Cambio principal v3 -> v4:** se elimina toda referencia a `X-Auth-*`, ForwardAuth, tabla `users` global, `company_id` multi-tenant. Se introducen `deployments`, `api_keys` (cifrados), `webhook_secrets`, `admin_users` (auth propia del Maestro).

---

> **Aplican cuando:** El preset `maestro-platform` v1 estaba activo (legacy)
> **Extienden:** Las reglas generales del framework v3 (nunca las contradicen)
> **Relación con `web-maestro/rules/RULES.md`:** Son duales. Lo que allí era "prohibido" aquí era "obligatorio"; lo que allí era "obligatorio en la app" aquí era "obligatorio que el Maestro lo provea/valide/imponga".

---

```yaml
obligatorio:
  portabilidad_y_dev_experience:
    - TODO runtime se ejecuta dentro de contenedores Docker; ningun PHP/Node/psql/composer se instala en el host del dev
    - prerequisitos locales unicos y absolutos: Docker, Docker Compose, git, IDE
    - docker-compose.dev.yml en la raiz del repo arranca el stack completo del Maestro con `docker compose up -d` sin pasos previos
    - comandos de toolchain se invocan siempre via `docker compose run --rm <servicio> <comando>` (ej: `docker compose run --rm php composer install`)
    - documento docs/CONVENCIONES_PLATAFORMA.md versionado en el repo con naming, puertos, redes, volumenes y env vars que evitan colisiones entre Maestro y apps huesped
    - cada app huesped que se agregue al entorno dev respeta las convenciones de ese documento sin modificar el Maestro
    - variables de entorno sensibles en .env (gitignored) con .env.example versionado como plantilla
    - scripts make/just o composer-scripts documentados como atajos de los comandos docker compose run mas comunes

  autenticacion_y_autorizacion:
    - Laravel Passport configurado como servidor OAuth2 emisor de JWT
    - endpoint POST /api/auth/login acepta email + password y retorna JWT
    - flujo OAuth2 con Microsoft Entra ID que emite JWT del Maestro tras éxito
    - endpoint GET /api/auth/validate consumido por Traefik ForwardAuth retorna 200 con headers X-Auth-* o 401
    - endpoint POST /api/auth/refresh para renovar tokens con refresh_token
    - endpoint POST /api/auth/logout revoca el token en la BD
    - headers emitidos exactamente: X-Auth-User-Id, X-Auth-User-Email, X-Auth-Company-Id, X-Auth-Roles, X-Auth-Permissions
    - JWT expira en 1 hora por defecto (configurable); refresh tokens con expiración mayor
    - cambio de empresa activa emite un JWT nuevo con X-Auth-Company-Id actualizado

  modelo_de_datos:
    - tabla canónica users con soft delete
    - tabla canónica companies con soft delete
    - tabla canónica applications con soft delete
    - tabla pivote company_user con roles y permisos
    - tabla pivote application_company con licencia (tier, activa, expira_en)
    - tabla pivote application_user con roles dentro de la app
    - tablas OAuth de Passport (oauth_access_tokens, oauth_refresh_tokens, oauth_clients)
    - tabla instances con estado, empresa, aplicación, red docker, credenciales BD cifradas
    - tabla audit_log INMUTABLE (solo INSERT; triggers DB rechazan UPDATE y DELETE)
    - campos sensibles cifrados con AES-256 (credenciales BD, tokens externos, webhook secrets)

  infraestructura_y_provisioning:
    - Traefik corriendo en contenedor dentro de maestro-network
    - Traefik termina TLS con Let's Encrypt (ACME) para el dominio del Maestro
    - Traefik redirige automáticamente HTTP (80) a HTTPS (443)
    - middleware ForwardAuth aplicado a todas las rutas protegidas sin excepción
    - headers de seguridad inyectados: HSTS (1 año + includeSubDomains), CSP, X-Frame-Options, X-Content-Type-Options
    - rate limiting 100 req/min/IP por defecto (configurable)
    - motor de provisioning como servicio Laravel que consume Docker API
    - cada instancia recibe su propia red Docker dedicada privada
    - cada instancia recibe su propia BD con usuario dedicado y password >=32 chars aleatorios
    - límites Docker aplicados por instancia (--memory, --cpus) según maestro.yaml de la app
    - contenedores creados con --security-opt no-new-privileges
    - Dockerfile del Maestro mismo multi-stage, non-root, con HEALTHCHECK

  health_checks_y_ciclo_de_vida:
    - health checks ejecutados periódicamente contra el endpoint declarado en maestro.yaml de la app
    - tras 3 health checks fallidos consecutivos: restart automático del contenedor
    - tras 5: notificación al administrador
    - tras 10: suspensión de la instancia y marca de intervención manual requerida
    - máquina de estados del ciclo de vida completa: provisioning → starting → healthy → degraded → suspended → destroyed → purged (tras 90 días)

  contrato_y_sdk:
    - JSON Schema oficial de maestro.yaml publicado y versionado
    - CLI maestro-cli con comandos validate y new funcionales
    - SDK @maestro/sdk-node publicado en npm con middleware auth, filtro tenant, helpers permisos
    - endpoint POST /api/apps/register que recibe metadata desde CI/CD de apps y las registra
    - template repository en GitHub listo para maestro-cli new
    - generación automática de CLAUDE.md para apps huésped (hereda reglas de la plataforma)

  portal_y_frontend:
    - shell React con barra superior, sidebar, área de contenido principal
    - selector de empresa activa que emite JWT nuevo al cambiar
    - renderizado de apps huésped en iframes sandbox
    - protocolo postMessage para transferencia de token al iframe
    - pantalla de carga durante cold start con tiempo estimado
    - pantalla de bienvenida para usuarios sin apps licenciadas
    - manejo visual de errores: app caída, licencia expirada, token expirado, sin conexión
    - portal funcional en desktop, tablet y mobile

  gateway_inter_apps:
    - API Gateway que actúa como intermediario en toda comunicación entre apps del mismo tenant
    - verificación de permisos en cada request inter-app
    - registro de toda comunicación inter-apps en audit log

  hooks_salientes:
    - hooks on_user_added y on_user_removed disparados hacia apps huésped cuando sea relevante
    - hooks firmados con HMAC-SHA256 usando secret único por aplicación
    - header X-Maestro-Webhook-Secret en cada hook

  seguridad:
    - HTTPS obligatorio sin excepciones (TLS 1.2 mínimo, preferir 1.3)
    - secretos cifrados con AES-256 en BD del Maestro
    - credenciales inyectadas como env vars en runtime, nunca persistidas en disco del contenedor
    - pre-commit hook con escáner de secretos
    - escaneo profundo de secretos en CI/CD (historial completo de git)
    - scan de vulnerabilidades de imágenes Docker en CI/CD
    - audit log inmutable con: timestamp (ms), user_id, IP, action, data_before, data_after

  observabilidad:
    - Prometheus, cAdvisor, Loki, Promtail, Grafana desplegados
    - métricas de CPU, memoria, latencia, health status por instancia
    - logs centralizados filtrables por company_id y nivel de severidad
    - dashboards: ejecutivo, por instancia, del Maestro
    - alertas con canales Slack y email configurados
    - runbooks documentados para: instancia no responde, VPS sin espacio, cert TLS no renueva, BD Maestro caída, rollback de app

  backups:
    - backups diarios automáticos entre 2-4am (configurable)
    - cifrados antes de subir
    - almacenados en Azure Blob Storage separado del VPS
    - retención mínima 30 días (no reducible)
    - BD del Maestro respaldada antes de cada migración de schema

prohibido:
  - instalar PHP, Node.js, Composer, clientes de BD u otros runtimes en el host del dev
  - hardcodear versiones de runtime en scripts que dependan de binarios del host
  - modificar el Maestro para que una app huesped encaje (la app se adapta a las convenciones, no al reves)
  - bypass de ForwardAuth en cualquier ruta protegida
  - endpoints de app huésped accesibles sin pasar por validación del Maestro
  - tráfico HTTP plano expuesto al exterior
  - UPDATE o DELETE sobre audit_log (a nivel de aplicación Y de BD)
  - compartir BD entre instancias de distintos tenants
  - conectividad de red directa entre contenedores de distintos tenants
  - secretos en código fuente, en historial git o en imágenes Docker
  - contenedores corriendo como root o con --privileged
  - montaje de /var/run/docker.sock en contenedores de apps huésped
  - puertos expuestos al exterior distintos de 80 y 443
  - rutas que permitan acceso al metadata endpoint de Azure (169.254.169.254) desde apps huésped
  - reducción de la retención mínima de backups por debajo de 30 días
  - reducción de la expiración máxima de JWT por encima de 24 horas
  - comunicación directa entre apps huésped sin pasar por el gateway del Maestro
  - hard-delete de instancias antes de los 90 días de retención

recomendado:
  - cache Redis para validación de tokens (objetivo cache hit rate >90%)
  - imágenes Docker del Maestro optimizadas <200MB
  - preferir TLS 1.3 cuando el cliente lo soporte
  - documentar todo ADR con formato estándar (contexto, decisión, alternativas, consecuencias)
  - tests de integración end-to-end del flujo login → ForwardAuth → app huésped
  - pruebas de carga con 50 usuarios concurrentes como SLA objetivo de V1

validacion_json_schema_maestro_yaml:
  name: "regex ^[a-z0-9][a-z0-9-]{2,49}$, único en catálogo del Maestro"
  version: "SemVer válido (X.Y.Z)"
  requires.database: "enum: postgres, mysql, mongo, sqlite, none"
  requires.ports.app: "entero entre 1024 y 65535"
  health.endpoint: "debe comenzar con /"
  health.timeout_seconds: "máximo 5"
  auth.mode: "exactamente header"
  auth.headers: "nombres estándar exactos X-Auth-*"
  resources.memory: "formato válido, máximo 4g"
  resources.cpu: "float entre 0.25 y 4.0"
  hooks.endpoints: "rutas que comienzan con /"

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
