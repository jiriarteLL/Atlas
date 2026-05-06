# CLAUDE.md — App huésped Maestro v2

> Este archivo **hereda** las reglas de la plataforma Maestro v2 / framework agéntico v4. Claude Code lo lee en cada sesión y aplica estas restricciones automáticamente al generar o modificar código en este proyecto.
>
> **Versión del contrato:** `maestro.platform/v2`
> **Framework agéntico:** v4
> **Reemplaza al CLAUDE.md v1** (que asumía headers `X-Auth-*` y multi-tenancy con `company_id`).

## Regla 1: Auth propia de la app — NO leer headers X-Auth-*

- La app implementa **su propio login** (formulario + endpoint POST + middleware).
- Tablas obligatorias: `users`, `roles`, `permissions` con pivots (estructura sugerida en docs/APP_HUESPED_SPEC_V2.md §3).
- Password storage: bcrypt (cost ≥ 12) o argon2id. **NUNCA** texto plano, MD5, SHA1, SHA256 directo.
- Cookies con `HttpOnly`, `Secure`, `SameSite=Lax`, **O** JWT con expiracion corta + refresh token.
- **NO** leas headers `X-Auth-*` (deprecados en v2; el Maestro v2 no los inyecta).
- En este template (Node + Express): usa middleware como Passport.js, express-session, o helmet + jsonwebtoken segun necesidad.

## Regla 2: Single-tenant físico — NO filtres por company_id

- Cada contenedor sirve a UNA empresa. La empresa esta implícita.
- **NO** agregues `company_id` a las tablas. **NO** filtres queries por `company_id`.
- Si necesitas datos de la empresa (nombre, logo), exponelos via el endpoint `/maestro/branding` (Regla 6).

## Regla 3: Health check sin auth obligatorio

- `GET /health` responde 200 JSON `{"status":"ok"}` **sin pasar por auth middleware**.
- Timeout maximo: 5 segundos.
- Verifica conectividad a la BD con `SELECT 1` en happy path.

## Regla 4: Endpoint /maestro/branding con X-Maestro-Api-Key

- Expone el path declarado en `maestro.yaml` bajo `branding.url` (default `/maestro/branding`).
- **DEBE** validar header `X-Maestro-Api-Key` contra ENV var `MAESTRO_API_KEY`.
- Sin / con api key inválida → `HTTP 401`.
- Con api key válida → 200 + JSON: `{ "company_name", "logo_url", "primary_color"?, "favicon_url"? }`.
- `company_name` y `logo_url` son obligatorios; los otros opcionales.

## Regla 5: Hooks verificados con HMAC

- Endpoints declarados en `maestro.yaml` bajo `hooks:` reciben eventos del Maestro v2.
- **SIEMPRE** verificar header `X-Maestro-Webhook-Signature` (HMAC-SHA256 del body con `MAESTRO_WEBHOOK_SECRET`).
- Comparar en tiempo constante (`crypto.timingSafeEqual` en Node).
- Idempotente: deduplica por `event_id`.

## Regla 6: Variables de entorno

**OBLIGATORIO leer del env (NO hardcodear):**
- `DATABASE_URL`
- `MAESTRO_API_KEY`
- `SUPERADMIN_INITIAL_PASSWORD`
- `JWT_SECRET` (o `APP_KEY` segun stack)

**RESERVADOS (prohibidos como custom env vars):** prefijos `MAESTRO_*`, `SUPERADMIN_*`, y `DATABASE_URL`.

Custom env vars en `maestro.yaml` → `env:`. Regex `^[A-Z][A-Z0-9_]*$`.

## Regla 7: Dockerfile obligatorio

- Multi-stage (`FROM ... AS build` + `FROM ... AS runtime`).
- `USER` con UID no-root.
- `HEALTHCHECK` instruction.
- `EXPOSE` con el puerto de `maestro.yaml`.
- **Prohibido**: `--privileged`, montar `/var/run/docker.sock`, exponer puertos < 1024, hardcodear secretos.

## Regla 8: Nada de secretos en código

- Pre-commit con gitleaks + CI deep scan del historial.
- Secretos solo via ENV vars inyectadas en runtime.

## Regla 9: maestro.yaml v2 es el contrato

- `apiVersion: maestro.platform/v2` (no v1).
- Campos obligatorios: `auth.mode: own`, `auth.login_path`, `branding.url`, `seeding.superadmin_email` (default `admin@llyasoc.com`).
- Cualquier cambio requiere `maestro-cli validate` (v2) antes de commit.

## Regla 10: Seeder del superadmin (fase 05-seeding del framework agéntico)

- Implementa un seeder idempotente que:
  - Lee `SUPERADMIN_INITIAL_PASSWORD` del env.
  - Si no existe o es debil (< 12 chars / blacklisted): falla con exit code != 0.
  - Crea (si no existe) rol `superadmin` con TODOS los permisos.
  - Crea (si no existe) usuario `admin@llyasoc.com` con rol `superadmin`.
  - Si ya existe: NO toca password; verifica que tenga el rol.
  - Logs sin password ni hash.
- Hook en pipeline post-migrations: ejecutar el seeder.

## Regla 11: Logs estructurados JSON sin datos sensibles

- Formato JSON a stdout/stderr.
- Incluir `user_id` y `request_id` (NO `company_id` — single-tenant fisico).
- **NUNCA** loguear: passwords, hashes, JWTs propios, `MAESTRO_API_KEY`, `MAESTRO_WEBHOOK_SECRET`, `SUPERADMIN_INITIAL_PASSWORD`, cookies de sesion, bodies con datos sensibles.

## Regla 12: Audit log de auth (recomendado)

- Tabla `audit_log` con eventos: login (exitoso / fallido), logout, password change, role change.
- Campos: timestamp, user_id, action, ip_address, user_agent, success.
- Inmutable (solo INSERT).

---

## Stack de este template

- **Runtime:** Node 22+
- **Framework:** Express 4.x
- **BD:** PostgreSQL via `pg` o `prisma`
- **Auth:** sugerido `passport.js` (con strategy local) + `express-session` con cookie store, **O** `jsonwebtoken` con cookies HttpOnly.
- **Hash:** `bcrypt` o `argon2`.
- **Validación:** `zod` o `joi`.
- **Testing:** `vitest` o `jest` + `supertest`.

> El stack es ilustrativo. Cualquier librería madura es válida; lo obligatorio es cumplir las 12 reglas anteriores.

---

## Referencias

- `docs/APP_HUESPED_SPEC_V2.md` — contrato normativo v2
- `docs/APP_HUESPED_BEST_PRACTICES_V2.md` — recomendaciones
- `docs/CONVENCIONES_PLATAFORMA_V2.md` — naming, redes, env vars
- `framework-agentico/core/PRESET_WEB_MAESTRO.md` — preset v4
- `framework-agentico/phases/05-seeding.md` — detalle de la fase de seeding
