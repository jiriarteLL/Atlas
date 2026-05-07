# Preset: Web Maestro v4 (Siempre Activo)

> **Estado:** Permanentemente activo para todos los proyectos
> **Version del preset:** 4.0 (BREAKING respecto a v3)
> **Plataforma:** Orquestador de aplicaciones dockerizadas single-tenant

---

## Descripcion

Todas las aplicaciones gestionadas por este framework corren dentro de la plataforma Web Maestro. En v4 el Maestro es un **registry + redirector** de aplicaciones huesped:

- Mantiene un **registro central** de aplicaciones activas: `app_id`, `empresa_id`, `puerto`, `URL`, `estado`.
- Cuando un usuario hace click en una app desde el portal del Maestro, **abre la URL de la app en `target="_blank"`** (no redirige internamente, no maneja la sesion del usuario).
- Cada aplicacion gestiona **su propio login**, users, roles, permisos y tokens.
- Cada contenedor de aplicacion sirve a **una sola empresa** (single-tenant fisico). Esto evita cualquier mezcla de datos entre empresas.

Las constraints de este preset son **NO NEGOCIABLES** y deben incluirse en cada Context Packet que el PM envia a los orquestadores.

---

## Principios v4

1. **Single-tenant por contenedor**: una empresa = un contenedor. NO se filtra por `company_id` en queries.
2. **Auth propia de la app**: la app emite, valida y revoca sus propios tokens.
3. **Maestro = registry + redirector**: no inyecta headers de identidad; solo registra apps y abre URLs en pestana nueva.
4. **Branding via API autenticada**: la app expone un endpoint autenticado (con `X-Maestro-Api-Key`) para que el Maestro lea el nombre de la empresa y los logos.
5. **Hooks server-to-server**: los hooks Maestro -> App siguen autenticados con `X-Maestro-Webhook-Secret`.
6. **Seeding obligatorio**: cada MVP arranca con un usuario superadmin (`admin@llyasoc.com`) creado de forma idempotente.

---

## Constraints por Fase

### Fase 00 — Setup

- Verificar cuenta GitHub vinculada al portal Maestro.
- Verificar acceso al repo generado por el portal.
- Verificar template del stack intacto (preferentemente Tailwise Bundle).

### Fase 01 — Discovery

- Incluir requisitos del **registry del Maestro** como no negociables: la app debe ser registrable (declarar URL, puerto, branding endpoint, login path).
- **Single-tenancy fisica** como requisito de aislamiento: la app NO debe asumir multi-tenancy.
- **Auth propia de la app** como requisito: NO depender de headers inyectados por terceros.
- Consultar `/api/inventory/context` del Maestro si esta disponible (informa contexto de empresa al provisionar).

### Fase 02 — Planning

- **Auth propia obligatoria**: definir login, registro (si aplica), recuperacion de password, modelo de roles/permisos.
- **Estructura de tablas sugerida** (no obligatoria):

  ```
  users(id, email UNIQUE, password_hash, name, is_active, last_login_at, created_at, updated_at)
  roles(id, name UNIQUE, description, is_system)
  permissions(id, key UNIQUE, description, group)
  user_roles(user_id, role_id)
  role_permissions(role_id, permission_id)
  ```

  La app puede modelar diferente si lo justifica como ADR.

- **Single-tenancy fisica**: el modelo de datos NO debe tener `company_id` en cada tabla. La empresa esta implicita por contenedor.
- **`maestro.yaml` obligatorio** con campos minimos:

  ```yaml
  maestro:
    auth_model: own                  # v4: auth gestionada por la app
    login_path: /login               # ruta del formulario de login
    branding_url: /maestro/branding  # endpoint autenticado para nombre + logos
    health_url: /health              # health check sin auth
    # ... + campos de hooks, recursos, etc.
  ```

- **Hooks del Maestro** contemplados (con `X-Maestro-Webhook-Secret`).
- **Limites de recursos**: max 4GB RAM, 4 CPU cores.
- **Decision de seeding**: el PM **pregunta al PO** si quiere sembrar usuarios adicionales (con roles especificos) ademas del superadmin obligatorio.

### Fase 03 — Development

**Obligatorio implementar:**

1. **Login propio**
   - Formulario servido en `login_path` (default `/login`).
   - Endpoint POST que valida credenciales, emite token (cookie HttpOnly o JWT segun stack).
   - Logout que invalida el token.
   - Recuperacion de password (si la app lo requiere).
2. **Tabla `users`** con al menos: `id`, `email` (unico, indexado), `password_hash`, `name`, `is_active`, `created_at`, `updated_at`.
3. **Tablas `roles` y `permissions`** con pivots `user_roles` y `role_permissions` (estructura libre).
4. **Middleware de auth propio** que valide el token de la app. NO lee headers `X-Auth-*`.
5. **GET `/health`** retorna 200 `{"status":"ok"}` **sin auth**.
6. **Endpoint `/maestro/branding`** (o el path declarado en `maestro.yaml`):
   - Requiere header `X-Maestro-Api-Key` (secret compartido, ENV var `MAESTRO_API_KEY`).
   - Retorna 401 sin / con api key invalida.
   - Retorna 200 con JSON:
     ```json
     {
       "company_name": "Acme S.A.",
       "logo_url": "https://app.example.com/storage/logo.png",
       "primary_color": "#1F2937",
       "favicon_url": "https://app.example.com/storage/favicon.ico"
     }
     ```
   - `company_name` y `logo_url` son obligatorios; `primary_color` y `favicon_url` son opcionales.
7. **Hooks** si estan declarados en `maestro.yaml`:
   - Verificar header `X-Maestro-Webhook-Secret` antes de procesar (rechazar 401 si falta o invalido).
8. **Password storage**:
   - Hash con `bcrypt` (cost >= 12) o `argon2id`.
   - Nunca en texto plano. Nunca con `md5` / `sha1` / `sha256` directo.
9. **Sesiones / Tokens**:
   - Cookies con `HttpOnly`, `Secure`, `SameSite=Lax`; o JWT con expiracion corta + refresh token.
   - Almacenar tokens propios de la app es **PERMITIDO** (es el modelo v4).

**Prohibido:**

- NO hardcodear credenciales (`MAESTRO_API_KEY`, `SUPERADMIN_INITIAL_PASSWORD`, `APP_KEY`, `JWT_SECRET`, etc.).
- NO loggear passwords, hashes, ni api keys.
- NO almacenar passwords en texto plano.
- NO leer headers `X-Auth-*` (modelo v3 deprecado; el Maestro v4 no los inyecta).
- NO filtrar queries por `company_id` (el contenedor es single-tenant; agregar `company_id` es un error de modelo).

### Fase 04 — Delivery

- Dockerfile multi-stage, non-root, con `HEALTHCHECK`.
- NO `--privileged`, NO montar `docker.sock`.
- NO puertos < 1024.
- `.dockerignore` excluye `.git`, `node_modules`, `.env*`, `logs`.
- Pipeline en `.github/workflows/deploy.yml`.
- Rama `main` protegida (PR + review).
- `maestro.yaml` validado contra schema v4.
- **ENV vars obligatorias** (no provistas en codigo):
  - `DATABASE_URL`
  - `MAESTRO_API_KEY` (compartido con el Maestro)
  - `SUPERADMIN_INITIAL_PASSWORD` (consumida por la fase 05-seeding)
  - `APP_KEY` / `JWT_SECRET` (segun stack)
- Validar que el Maestro **registre** la app antes de declarar Delivery completa: la app debe aparecer en el registry con `URL`, `puerto`, `empresa_id`, `estado: active`.

### Fase 05 — Seeding

> **NUEVA en v4.** Garantiza que el MVP tenga un superadmin operativo.

**Obligatorio:**

- Implementar un seed (ej. `php artisan db:seed --class=SuperAdminSeeder`, `npm run seed:superadmin`) que:
  - Lea `SUPERADMIN_INITIAL_PASSWORD` de ENV.
  - Si la ENV var no existe o la password NO cumple la politica de fortaleza (ver `compliance-analyst`), **falla con exit code distinto de 0** sin crear nada.
  - Crea (o verifica que existe) un rol `superadmin` con **TODOS** los permisos definidos por la app.
  - Crea (si no existe) el usuario `admin@llyasoc.com` con `password_hash = hash(SUPERADMIN_INITIAL_PASSWORD)`, `is_active = true` y rol `superadmin` asignado.
  - **Idempotente**: si el usuario ya existe, NO toca su password. Si le falta el rol `superadmin`, lo asigna. Si todo esta correcto, no hace nada.
  - Logs SIN password, SIN hash, SIN api keys.
- El seed se ejecuta como parte del pipeline de deploy.

**Opcional (segun decision del PO en Fase 02):**

- Sembrar usuarios adicionales con roles especificos definidos por el PO.
- Estos usuarios siguen las mismas reglas: idempotencia, password desde ENV var dedicada, no leakeo en logs.

**Exit criteria:**

- `admin@llyasoc.com` existe en BD con rol `superadmin`.
- El usuario puede loguearse con `SUPERADMIN_INITIAL_PASSWORD`.
- Re-ejecutar el seed (en deploys subsiguientes) NO duplica usuarios ni rompe el sistema.
- No hay leakeo de password ni api keys en logs.

### Fase 06 — Operations

- Logs incluyen `user_id` y `request_id`. **NO incluyen `company_id`** (single-tenant fisico).
- NO loguear contenido de `Authorization` headers, cookies de sesion, ni `X-Maestro-Api-Key`.
- Considerar health checks externos del Maestro.
- Distinguir errores de app vs errores de gateway.
- Audit log de auth recomendado (login, logout, cambios de roles, cambios de password).

### Fase 07 — Retrospective

- Documentar lecciones de integracion con Maestro v4.
- Registrar patterns especificos del preset para futuros proyectos.
- Si la migracion del codigo a v4 fue desde v3, documentar gaps encontrados y como se resolvieron.

---

## Constraints para Validadores Transversales

```yaml
security-auditor:
  - Verificar TODAS las prohibiciones listadas arriba.
  - Validar que existe tabla `users` con `password_hash` (no plain).
  - Validar uso de `bcrypt` (cost >= 12) o `argon2id` para hash.
  - Validar que no se hardcodeen credenciales (MAESTRO_API_KEY, SUPERADMIN_INITIAL_PASSWORD, APP_KEY, JWT_SECRET, etc.).
  - Validar que NO se leen headers X-Auth-* (modelo v3 deprecado).
  - Validar manejo correcto de X-Maestro-Api-Key en /maestro/branding.
  - Validar manejo correcto de X-Maestro-Webhook-Secret en hooks.
  - Validar cookies con HttpOnly, Secure, SameSite.
  - Validar que no haya leakeo de api keys / passwords en logs ni en respuestas de error.

qa-tester:
  - Testear login propio:
    - POST /login con creds validas -> 200 + token/cookie de sesion.
    - POST /login con creds invalidas -> 401.
    - GET /api/protegido sin auth -> 401.
    - GET /api/protegido con auth valida -> 200.
  - Testear GET /health retorna 200 sin auth.
  - Testear GET /maestro/branding:
    - Sin X-Maestro-Api-Key -> 401.
    - Con X-Maestro-Api-Key invalida -> 401.
    - Con X-Maestro-Api-Key valida -> 200 + JSON con company_name y logo_url.
  - Testear seed idempotente: re-ejecutar seed NO duplica admin@llyasoc.com ni rompe el sistema.
  - Testear que el superadmin tiene TODOS los permisos definidos por la app.

compliance-analyst:
  - Validar password policy (min 12 chars, complejidad razonable, no comunes). Aplica a SUPERADMIN_INITIAL_PASSWORD y a passwords de usuarios.
  - Validar audit log de eventos de auth (login, logout, cambios de password, cambios de roles).
  - Validar politicas de retencion de sesiones del Maestro.
  - Validar que cada contenedor sirve a UNA sola empresa (single-tenant fisico, sin company_id en queries).

performance-analyst:
  - Validar limites de recursos (4GB RAM, 4 CPU cores).
  - Validar indices sobre users.email (lookup frecuente en login).
  - NO validar filtrado por company_id (no aplica en v4).
  - Validar throughput aceptable en login y endpoints autenticados.

code-reviewer:
  - Validar separacion de capas (controllers, services, repositories) en codigo de auth.
  - Validar que el middleware de auth no expone informacion sensible en errores.
  - Validar que los endpoints de branding y hooks usan el middleware correcto (api key vs webhook secret).

documentation-writer:
  - Documentar el flujo de auth de la app (login, logout, refresh, recuperacion).
  - Documentar el modelo de roles y permisos.
  - Documentar el seed de superadmin y como cambiar la password despues del primer login.
  - Documentar los endpoints publicos: /login, /health, /maestro/branding (con su autenticacion).
```

---

## Artefactos

```yaml
generados_por_portal_maestro:
  - maestro.yaml (el framework solo valida, no genera)
  - Template del stack (repo generado por el portal)
  - Pipeline CI/CD base
  - MAESTRO_API_KEY (compartida con la app via ENV var)

generados_por_el_framework:
  - Login propio (formulario + endpoints + middleware)
  - Modelo de users / roles / permissions
  - Health check endpoint
  - Endpoint /maestro/branding autenticado
  - Hooks endpoints (si aplica)
  - Dockerfile compatible
  - Tests de integracion con el contrato v4
  - Seeder de superadmin (Fase 05)
```

---

## Variables de Entorno Estandar

```yaml
required:
  DATABASE_URL: "URL de conexion a la BD del contenedor"
  MAESTRO_API_KEY: "Secret compartido con el Maestro para /maestro/branding"
  SUPERADMIN_INITIAL_PASSWORD: "Password inicial del usuario admin@llyasoc.com (>= 12 chars, complejidad)"

required_per_stack:
  Laravel:
    APP_KEY: "Key generada por php artisan key:generate"
  Node/Express o frameworks JS:
    JWT_SECRET: "Secret para firmar tokens JWT"
  # ... ajustar segun stack

optional:
  MAESTRO_WEBHOOK_SECRET: "Secret para validar hooks del Maestro (si la app declara hooks en maestro.yaml)"
  LOG_LEVEL: "info | warn | error"
```

---

## Documentos de Referencia

Si estan disponibles en el repo:

- `ARQUITECTURA_APLICACIONES_GENERICAS.md` — Contrato universal de integracion (puede estar desactualizado vs v4).
- `POLITICA_REUSO_CONTENEDORES.md` — Politica de reuso de recursos del Maestro.

> **Nota:** estos documentos pueden estar desactualizados respecto a v4. Si los conceptos contradicen lo descrito en este preset, **prevalece este archivo**.
