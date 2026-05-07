# Reglas Preset Maestro Platform

> **Aplican cuando:** El preset `maestro-platform` está activo (ver `framework-agentico/core/RULES.md` seccion `activacion_de_preset`).
> **Framework agéntico:** v4
> **Reemplaza a:** `legacy/v3/framework-agentico/agents/presets/maestro-platform/rules/RULES.md` (reglas v1 con Maestro como IdP).
> **Extienden:** Las reglas generales del framework v4 (`framework-agentico/core/RULES.md`).
> **Relación con `web-maestro` v4:** Son duales. Lo que en `web-maestro` v4 es "obligatorio en la app", aqui es "obligatorio que la Web Maestro lo provea, valide o consuma".

---

```yaml
obligatorio:
  portabilidad_y_dev_experience:
    - TODO runtime se ejecuta dentro de contenedores Docker; ningun PHP/Node/psql/composer en el host del dev
    - prerequisitos locales: Docker, Docker Compose, git, IDE
    - docker-compose.dev.yml en la raiz arranca el stack completo del Maestro v2 con `docker compose up -d`
    - comandos de toolchain via `docker compose run --rm <servicio> <comando>`
    - documento docs/CONVENCIONES_PLATAFORMA.md versionado en el repo (deliverable de fase 02)
    - variables de entorno sensibles en .env (gitignored) con .env.example versionado

  registry_y_catalogo:
    - tabla `companies` con: id (UUID), nombre, slug (regex `^[a-z0-9][a-z0-9-]{2,49}[a-z0-9]$`), estado (active|suspended), created_at, updated_at
    - tabla `applications` con: id (UUID), nombre, slug, version (semver), maestro_yaml_hash, descripcion, estado (active|deprecated), created_at
    - tabla `deployments` (uno por app + empresa) con: id (UUID), application_id, company_id, container_name (`app-<slug>-<empresa>`), db_container_name (`db-<slug>-<empresa>`), network_name, app_url, app_port, estado (provisioning|healthy|degraded|suspended|destroyed), created_at, last_health_check_at
    - tabla `api_keys` con: deployment_id, key_hash (cifrado AES-256), created_at, rotated_at, expires_at
    - tabla `webhook_secrets` con: deployment_id, secret_hash (cifrado AES-256), created_at, rotated_at
    - tabla `audit_log` INMUTABLE: id, timestamp, actor_user_id, actor_ip, action, resource_type, resource_id, payload_before, payload_after — triggers DB rechazan UPDATE/DELETE
    - cada deployment recibe MAESTRO_API_KEY y MAESTRO_WEBHOOK_SECRET unicos al provisionarse
    - rotacion de api_key disponible via UI o API (sin downtime)

  auth_de_admins_del_maestro:
    - El Maestro v2 mismo tiene login propio para sus administradores (cumple preset web-maestro v4 a si mismo)
    - tabla `admin_users` con: id, email UNIQUE, password_hash (bcrypt cost >= 12 o argon2id), name, is_active, last_login_at, created_at
    - tablas `admin_roles`, `admin_permissions`, pivots
    - rol `superadmin` con TODOS los permisos
    - usuario `admin@llyasoc.com` creado por seeder idempotente (fase 05-seeding) con SUPERADMIN_INITIAL_PASSWORD
    - middleware de auth propio: cookies HttpOnly+Secure+SameSite o JWT
    - audit log de eventos: login (exitoso/fallido), logout, password_change, role_change

  endpoints_publicos:
    - GET /health -> 200 sin auth
    - POST /api/v2/auth/login (login de admins del Maestro)
    - POST /api/v2/auth/logout
    - POST /api/v2/apps/register (auth con token de registro de la app)

  endpoints_admin:
    - GET/POST/PUT/DELETE /api/v2/companies
    - GET/POST/PUT/DELETE /api/v2/applications
    - GET/POST/PUT/DELETE /api/v2/deployments
    - POST /api/v2/deployments/{id}/provision
    - POST /api/v2/deployments/{id}/suspend
    - POST /api/v2/deployments/{id}/destroy
    - POST /api/v2/deployments/{id}/rotate-api-key
    - GET /api/v2/branding/{deployment_id}
    - POST /api/v2/branding/{deployment_id}/refresh

  endpoints_para_apps_huesped:
    - POST /api/v2/apps/register: la app envia metadata + maestro.yaml hash + commit sha; recibe deployment_id (si la empresa ya licencio la app) o queda pending
    - GET /api/v2/inventory/context (opcional): la app puede consultar contexto de la empresa que la opera

  consumo_de_branding:
    - Job periodico (configurable, default cada 6 horas) consume GET <app_url>/maestro/branding de cada deployment activo
    - Header obligatorio en el request: X-Maestro-Api-Key: <api_key del deployment>
    - Si responde 200 con JSON valido (company_name + logo_url): cachear en BD
    - Si responde 401: alertar admin (api_key invalida o desincronizada)
    - Si responde 5xx: contar fallos; tras 3 fallos consecutivos, marcar deployment como degraded y alertar
    - El portal del Maestro consume el cache (no llama directo a la app)
    - Endpoint POST /api/v2/branding/{deployment_id}/refresh permite forzar refresh manual

  redireccion_a_apps:
    - El portal del Maestro NO usa iframes ni reverse proxy
    - Cuando el usuario hace click en una app, el portal genera un link <a target="_blank" href="<app_url>"> que abre en pestana nueva
    - El Maestro NO transfiere identidad ni token al click — la app solicita login propio
    - El portal puede mostrar un mensaje "Vas a abrir <nombre_app>. Te pedira login propio de la app."

  hooks_salientes:
    - hooks on_user_added, on_user_removed, on_company_license_granted, on_company_license_revoked se disparan cuando aplican
    - cada hook firmado con HMAC-SHA256: header X-Maestro-Webhook-Signature: t=<unix_ts>,v1=<hex_hmac>
    - secret usado: MAESTRO_WEBHOOK_SECRET del deployment destino
    - reintento con backoff exponencial: 3 intentos, max 10 min entre reintentos
    - cada hook lleva un event_id UUIDv4 unico para idempotencia
    - audit log de cada disparo (success/failure)

  infraestructura_y_provisioning:
    - Traefik en contenedor dentro de maestro-network, termina TLS con Let's Encrypt
    - Traefik redirige HTTP (80) a HTTPS (443) automaticamente
    - SIN middleware ForwardAuth (no aplica en v2)
    - headers de seguridad: HSTS, CSP, X-Frame-Options, X-Content-Type-Options, Referrer-Policy
    - rate limiting global y por endpoint
    - motor de provisioning como servicio que consume Docker API
    - cada deployment tiene su red Docker dedicada `app-<slug>-<empresa>-net`
    - BD dedicada con usuario y password >= 32 chars aleatorios
    - limites Docker: --memory y --cpus segun maestro.yaml
    - --security-opt=no-new-privileges en todos los contenedores
    - Dockerfile del Maestro v2: multi-stage, non-root, con HEALTHCHECK

  health_checks_y_ciclo_de_vida:
    - health checks contra el endpoint health.endpoint del maestro.yaml de cada app
    - estados de deployment: provisioning -> starting -> healthy -> degraded -> suspended -> destroyed -> purged (>90 dias)
    - tras 3 fallos consecutivos: restart automatico
    - tras 5: notificacion al admin
    - tras 10: marcar suspended y requerir intervencion manual

  contrato_y_validacion:
    - JSON Schema oficial de maestro.yaml v2 publicado y versionado
    - maestro-cli con comandos `validate` (verifica apiVersion v2 + auth.mode=own + branding.url + seeding) y `new` (genera template v4)
    - endpoint POST /api/v2/apps/register valida el maestro.yaml contra el schema antes de aceptar el registro
    - rechazar apps con apiVersion v1 (solo se acepta v2)

  seguridad:
    - HTTPS obligatorio sin excepciones
    - secretos cifrados con AES-256 en BD del Maestro
    - api_keys y webhook_secrets nunca en logs ni en respuestas API
    - pre-commit hook con escaner de secretos
    - escaneo profundo del historial git en CI
    - scan de vulnerabilidades de imagenes Docker en CI
    - audit log inmutable

  observabilidad:
    - Prometheus, Loki, Grafana desplegados
    - metricas: salud del registry, latencia de provisioning, latencia de consumo de /maestro/branding, hooks success/failure rate, deployments por estado
    - logs centralizados con user_id (admin) y request_id (NO company_id en logs del Maestro mismo, salvo cuando se loguea contexto de un deployment)
    - dashboards: ejecutivo, por deployment, por empresa
    - alertas configuradas

  backups:
    - backups diarios automaticos cifrados
    - almacenados externos al VPS (Azure Blob, S3, GCS, etc.)
    - retencion minima 30 dias
    - BD del Maestro respaldada antes de cada migracion

prohibido:
  - implementar tabla `users` global con usuarios de apps huesped (eso lo hace cada app)
  - inyectar headers X-Auth-* a las apps huesped (deprecado en v2)
  - usar middleware ForwardAuth de Traefik para validar identidad en apps huesped (no aplica en v2)
  - reverse proxy con inyeccion de identidad hacia apps huesped (apps tienen auth propia)
  - iframes para mostrar apps huesped en el portal (abrir URL en target="_blank")
  - consumir /maestro/branding sin X-Maestro-Api-Key
  - consumir hooks sin verificar X-Maestro-Webhook-Signature en la app destino
  - guardar api_keys o webhook_secrets en texto plano en BD
  - UPDATE o DELETE sobre audit_log (a nivel app y a nivel BD)
  - compartir BD entre deployments
  - conectividad de red directa entre contenedores de distintos deployments
  - secretos en codigo, en historial git, o en imagenes Docker
  - contenedores corriendo como root o con --privileged
  - puertos expuestos al exterior distintos de 80 y 443
  - reduccion de retencion de backups por debajo de 30 dias
  - aceptar maestro.yaml con apiVersion v1 en /api/v2/apps/register

recomendado:
  - cache de branding por deployment con TTL razonable (ej: 6 horas) + invalidacion via refresh
  - imagenes Docker del Maestro optimizadas <200MB
  - preferir TLS 1.3
  - documentar todo ADR con formato estandar
  - tests de integracion del flujo: register app -> license to company -> provision -> consume branding -> click portal
  - rotacion automatica de api_keys cada 90 dias

validacion_json_schema_maestro_yaml_v2:
  apiVersion: 'exactamente "maestro.platform/v2"'
  kind: 'exactamente "Application"'
  metadata.name: 'regex ^[a-z0-9][a-z0-9-]{2,49}$, unico en catalogo'
  metadata.version: 'SemVer valido'
  requires.database: 'enum: postgres, mysql, mongo, sqlite, none'
  requires.ports.app: 'entero entre 1024 y 65535'
  health.endpoint: 'comienza con /'
  health.timeout_seconds: 'maximo 5'
  auth.mode: 'exactamente "own"'
  auth.login_path: 'comienza con /, obligatorio'
  auth.logout_path: 'comienza con /, opcional'
  branding.url: 'comienza con /, obligatorio'
  resources.memory: 'enum: 256m, 512m, 1g, 2g, 4g'
  resources.cpu: 'float entre 0.25 y 4.0'
  seeding.superadmin_email: 'email valido, default admin@llyasoc.com'
  seeding.additional_users: 'array opcional con {email, role}'
  hooks.endpoints: 'rutas que comienzan con /'
  env: 'array opcional, nombres regex ^[A-Z][A-Z0-9_]*$, no en prefijos reservados'

objetivos_cuantitativos_v1_del_maestro_v2:
  latencia_redireccion_ms: 200
  tiempo_provisioning_deployment_seconds_max: 60
  tiempo_consumo_branding_con_cache_ms: 50
  retencion_backups_dias_min: 30
  retencion_deployment_destruido_dias: 90
  cobertura_tests_statements_min: 0.80
  cobertura_tests_branches_min: 0.70
  vulnerabilidades_critical_high_bloqueantes: true
  hooks_success_rate_min: 0.99
```
