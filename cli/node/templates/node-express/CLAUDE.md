# CLAUDE.md — App huésped Maestro

> Este archivo **hereda** las reglas de la plataforma Maestro. Claude Code lo lee en cada sesión y aplica estas restricciones automáticamente al generar o modificar código en este proyecto.

## Regla 1: Auth por headers, NUNCA login propio

- La app **NO** implementa login, registro ni reset de password.
- La identidad viene en los headers: `X-Auth-User-Id`, `X-Auth-User-Email`, `X-Auth-Company-Id`, `X-Auth-Roles`, `X-Auth-Permissions`.
- Usá `authMiddleware()` del SDK: `import { authMiddleware } from '@maestro/sdk-node'`.
- Nunca crees tablas `users`, `sessions`, `password_resets` ni similares.

## Regla 2: Multi-tenancy — filtrar por company_id en TODO query

- `tenantFilter(req)` del SDK te da el `company_id` del request actual.
- Cualquier `SELECT`, `INSERT`, `UPDATE`, `DELETE` debe incluir `WHERE company_id = <tenant>`.
- Bug de no-filtrado = leak entre tenants = catastrófico.

## Regla 3: Health check sin auth obligatorio

- `GET /health` debe responder 200 JSON `{"status":"ok"}` sin pasar por auth middleware.
- Timeout máximo: 5 segundos.
- El Maestro lo consulta cada 30s; 3 fallos → restart automático.

## Regla 4: Hooks verificados HMAC

- Los endpoints declarados en `maestro.yaml` bajo `hooks:` reciben eventos del Maestro.
- SIEMPRE usar `hookVerifierMiddleware()` para verificar firma HMAC-SHA256.
- Nunca confiar en hooks sin verificar la firma.

## Regla 5: Variables de entorno

- **OBLIGATORIO leer del env**: `DATABASE_URL`, `MAESTRO_*`. Nunca hardcodear.
- **RESERVADOS (prohibidos en tu app)**: prefijos `MAESTRO_`, `X_AUTH_`, `DATABASE_URL`.
- Tus env vars custom se declaran en `maestro.yaml` → `env:` y deben matchear regex `^[A-Z][A-Z0-9_]*$`.

## Regla 6: Dockerfile obligatorios

- Multi-stage (`FROM ... AS build` + `FROM ... AS runtime`).
- `USER` directive con UID no-root.
- `HEALTHCHECK` instruction.
- `EXPOSE` con el puerto de `maestro.yaml`.
- **Prohibido**: `--privileged`, montar `/var/run/docker.sock`, exponer puertos <1024.

## Regla 7: Nada de secretos en código

- Pre-commit scan con gitleaks + CI deep scan del historial git.
- Secretos como passwords, tokens, API keys SOLO por env vars inyectadas en runtime por el Maestro.

## Regla 8: `maestro.yaml` es el contrato

- Cualquier cambio al contrato requiere `maestro-cli validate` antes de commit.
- CI/CD valida en cada push; build falla si el contrato es inválido.

## Regla 9: Comunicación inter-apps solo via Gateway

- Si necesitás llamar a otra app del mismo tenant, usar `GatewayClient` del SDK.
- Nunca llamar a otra app por URL directa (las redes Docker lo bloquean igualmente).

## Regla 10: Logs estructurados JSON sin datos sensibles

- Formato JSON a stdout/stderr (Loki los recolecta).
- **Nunca** loguear: headers `X-Auth-*`, passwords, tokens, `DATABASE_URL`, bodies de requests completos.
- Incluir `company_id` en logs para trazabilidad multi-tenant.

---

Más info en la documentación de la plataforma (`docs/CONVENCIONES_PLATAFORMA.md` del Maestro).
