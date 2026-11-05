# Atlas — Contratos de API (fase 02-planning)

Todo lo que no está marcado como público exige `Authorization: Bearer <access token>` y el permiso indicado.
Sin token o con un token inválido o revocado → **401**. Sin el permiso → **403**. La documentación interactiva
(`/docs`, `/openapi.json`) está deshabilitada a propósito.

## Contrato con el Maestro (`maestro.yaml`)

| Endpoint | Auth | Respuesta |
|---|---|---|
| `GET /health` | pública | `200 {"status":"ok"}` (JSON). Hace `SELECT 1`; sin base → `503`. |
| `GET /maestro/branding` | `X-Maestro-Api-Key` | `200 {company_name, logo_url, primary_color, favicon_url}`; sin clave o con clave inválida → `401 {"error":"invalid_api_key"}` |
| `GET /metrics` | `X-Maestro-Api-Key` | Formato texto de Prometheus: `http_requests_total`, `http_request_duration_seconds`, `auth_login_attempts_total`, `auth_login_failures_total`, `app_info`, métricas del proceso |
| `POST /login` (= `POST /auth/login`) | pública, con rate limit | Ver abajo |
| `POST /logout` (= `POST /auth/logout`) | Bearer | `200 {"status":"ok"}`. Revoca el access y el refresh. |

## Autenticación

| Endpoint | Auth | Detalle |
|---|---|---|
| `POST /login` / `POST /auth/login` | pública | Body **form** (`username`, `password`) o **JSON** (`email`\|`username`\|`usuario`, `password`). `200 {access_token, token_type, expires_in, user}` y `Set-Cookie: inventario_session=…; HttpOnly; SameSite=Strict; Path=/auth[; Secure]`. Credenciales inválidas → `401` con mensaje único. Más de 5/min por IP o 10/h por email → `429`. Con 5 fallos seguidos, la cuenta queda bloqueada 15 min (se responde `401`). |
| `POST /auth/refresh` | cookie + `X-Requested-With` | Canjea y rota el refresh: `200` con un access nuevo y cookie nueva. Si se reusa un refresh ya rotado, se revocan todas las sesiones del usuario y responde `401`. |
| `GET /auth/me` | login | Usuario actual con rol, permisos y `debe_cambiar_password`. |
| `GET/PUT /auth/perfil` | login | Datos propios y últimos 8 eventos de auditoría. En el PUT se pueden cambiar nombre y email. |
| `POST /auth/cambiar-password` | login | `{password_actual, password_nuevo}`. Revoca todas las sesiones y borra la cookie. |
| `GET/POST /auth/usuarios` | `usuarios.administrar` | Alta: `{username, email, nombre, password, rol ∈ admin\|editor\|viewer}`. El email es obligatorio y único. |
| `PUT/DELETE /auth/usuarios/{username}` | `usuarios.administrar` | El superadmin no se puede degradar ni borrar. Un reset de password obliga a cambiarla y revoca las sesiones. El DELETE es lógico. |

## Negocio

| Endpoint | Permiso |
|---|---|
| `GET /api/assets` · `GET /api/assets/{aid}/ficha` · `GET /api/assets/{id}/historial` | `inventario.ver` |
| `POST /api/assets` · `PUT /api/assets/{aid}` | `inventario.editar` |
| `DELETE /api/assets/{aid}` | `activos.eliminar` |
| `POST /api/assets/{aid}/garantia` | `garantias.consultar` |
| `GET /api/garantias/vencimientos?dias=90` | `inventario.ver` |
| `GET /api/assets/{id}/adjuntos` · `GET /api/adjuntos/{id}/descargar` | `inventario.ver` |
| `POST /api/assets/{id}/adjuntos` (multipart) · `DELETE /api/adjuntos/{id}` | `inventario.editar` |
| `GET /api/glpi/resumen` | `inventario.ver` |
| `GET /api/proyectos` · `GET /api/equipo` | `inventario.ver` |
| `POST/PUT/DELETE /api/proyectos[/{pid}]` · `POST /api/proyectos/{pid}/tareas` · `PUT/DELETE /api/tareas/{tid}` | `inventario.editar` |
| `GET /api/tickets` | `inventario.ver` |
| `POST /api/tickets` · `PUT /api/tickets/{tid}` | `inventario.editar` |
| `GET /api/tendencias[?metrica=]` · `GET /api/tendencias/metricas` | `inventario.ver` |
| `POST /api/tendencias/snapshot` | `usuarios.administrar` |

## Agentes

| Endpoint | Auth | Detalle |
|---|---|---|
| `POST /api/sync` | `X-Sync-Key` (comparación en tiempo constante) | JSON de `AssetSync`. El serial es la clave: si ya existe se actualiza, si no se crea. `software` acepta texto o una lista `[{nombre, version, fecha}]`. |
| `POST /api/sync-glpi` | `X-Sync-Key` | JSON GLPI (acepta gzip, hasta 8 MB). Actualiza el activo y el resumen `asset_glpi`. |
| `GET /agent_linux.sh` | pública | Script del agente Linux. No contiene secretos: la clave se pasa al instalarlo. |

## Cabeceras de todas las respuestas

`X-Request-Id` (se propaga si viene válido; si no, se genera), `X-Content-Type-Options: nosniff`,
`X-Frame-Options: DENY`, `Referrer-Policy`, `Permissions-Policy` y `Content-Security-Policy`. Bajo HTTPS se agrega
`Strict-Transport-Security`. `/api`, `/auth`, `/login` y `/logout` llevan además `Cache-Control: no-store`.
