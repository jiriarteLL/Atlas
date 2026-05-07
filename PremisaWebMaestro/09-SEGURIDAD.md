# Seguridad: Defensa en Profundidad

> **Versión:** v4 (framework agéntico v4 / contrato `maestro.platform/v2`)
> **Última revisión:** 2026-05-07
> **Estado:** vigente
> **Reemplaza a:** `legacy/v3/PremisaWebMaestro/09-SEGURIDAD.md` (modelo v1).

---

## Propósito de este documento

Este documento presenta la estrategia de seguridad completa de la **Web Maestro** v4 organizada en capas de defensa redundantes. El principio rector es que **si una capa de seguridad falla o es comprometida, las capas restantes contienen la amenaza**. Un agente de IA que implemente componentes de seguridad, configure infraestructura o revise código debe usar este documento como checklist y como threat model de referencia.

---

## Cambio respecto a v1

En v1 la seguridad estaba centrada en el modelo IdP del Maestro: ForwardAuth, headers `X-Auth-*`, multi-tenancy lógica con filtrado de queries por `company_id`. En v4 la responsabilidad se distribuyó:

- La Web Maestro asegura **su propia perimetría** (TLS, login propio de admins, rotación de api keys, audit log inmutable).
- Cada app huésped asegura **su propia auth** (login propio, password storage, tokens propios).
- El **aislamiento físico** (single-tenant) reemplaza al aislamiento lógico (multi-tenant con `company_id`), simplificando significativamente la superficie de ataque.

---

## Capas de defensa

### Capa 1: Perimetro de red

**TLS obligatorio** (No-negociable 11):
- Traefik termina TLS 1.2+ (preferiblemente 1.3) en el puerto 443.
- Certificados gestionados automáticamente por Let's Encrypt vía ACME.
- Redirect automático HTTP (80) → HTTPS (443).
- Header HSTS con `max-age=31536000` (1 año) e `includeSubDomains`.
- Sin tráfico HTTP plano expuesto al exterior.

**Headers de seguridad** (Traefik los inyecta en cada respuesta):
- `Strict-Transport-Security: max-age=31536000; includeSubDomains; preload`
- `X-Content-Type-Options: nosniff`
- `X-Frame-Options: DENY` (para el portal del Maestro; las apps huésped pueden definir su propia política)
- `Content-Security-Policy`: estricta para el portal (script-src 'self'; style-src 'self' 'unsafe-inline' por Tailwise; etc.)
- `Referrer-Policy: strict-origin-when-cross-origin`
- `Permissions-Policy`: bloqueo de features peligrosas (camera, microphone, etc.) salvo declaración explícita.

**Rate limiting** (Traefik o middleware):
- Default global: 100 req/min/IP.
- `/api/v2/auth/login`: 5 req/min/IP (anti-bruteforce).
- `/api/v2/apps/register`: 10 req/hora/token.
- `/maestro/branding` consumido por Maestro: sin rate limit por IP del Maestro (es un IP fijo o range conocido).

**Egress policy**:
- Los contenedores de apps huésped pueden hacer requests salientes a internet (necesario para integraciones).
- El contenedor de la BD del Maestro **NO** tiene acceso a internet (sólo accesible desde `maestro-net`).
- Recomendado: bloqueo del metadata endpoint de cloud (Azure: `169.254.169.254`) desde apps huésped, para prevenir SSRF a metadata del VPS.

### Capa 2: Aislamiento de contenedores

**No-root obligatorio** (No-negociable 7):
- Validación estática del Dockerfile en CI: presencia de instrucción `USER` con UID ≠ 0.
- Validación dinámica en runtime: si el contenedor se levanta y `whoami` devuelve `root`, alerta crítica.

**`--security-opt=no-new-privileges`** en todos los contenedores: previene escalada vía setuid binaries.

**Aislamiento de redes Docker**:
- Cada deployment en su propia red dedicada `app-<slug>-<empresa>-net`.
- Sin tráfico inter-deployment a nivel red.
- Comunicación inter-apps solo via API Gateway del Maestro (audit logged).

**Volúmenes restringidos**:
- Apps huésped: solo `/app/storage` (configurable por la app).
- **Prohibido**: montar `/var/run/docker.sock` (excepto el provisioner del Maestro mismo, que lo necesita).
- **Prohibido**: montar paths del filesystem del host arbitrarios.

**`--privileged` prohibido** absolutamente.

**Recursos limitados** (No-negociable 9):
- `--memory` y `--cpus` aplicados según declaración del `maestro.yaml`.
- Excesos matados por el OOM Killer / throttled por scheduler.

### Capa 3: Autenticación y autorización

#### Auth de admins del Maestro
- bcrypt cost ≥ 12 o argon2id para `password_hash`.
- Comparación timing-constant de hash.
- Bloqueo de cuenta tras 5 intentos fallidos durante 15 min.
- Cookies de sesión `HttpOnly + Secure + SameSite=Lax` o JWT con expiración corta + refresh token.
- Rotación de session/refresh tokens recomendada.
- MFA recomendado para `superadmin` (a definir como ADR en fase 02-planning del proyecto Maestro).

#### Auth server-to-server entre Maestro y apps
- `X-Maestro-Api-Key`: secret aleatorio ≥ 32 chars, cifrado AES-256 en BD, rotable cada 90 días, audit logged.
- `X-Maestro-Webhook-Signature`: HMAC-SHA256 con timestamp, anti-replay window de 300s, idempotencia por `event_id`.
- Comparación timing-safe en ambos casos.

#### Auth de usuarios finales
- **Responsabilidad de cada app huésped**, no del Maestro.
- Ver `03-AUTENTICACION-Y-AUTORIZACION.md` plano 3.

#### RBAC
- Permisos granulares (`companies.create`, `deployments.destroy`, `audit_log.read`, etc.).
- Rol `superadmin` (de sistema, no editable) con TODOS los permisos.
- Roles operativos definibles: `operator`, `viewer`, etc.

### Capa 4: Cifrado y manejo de secretos

**Secretos cifrados en BD del Maestro**:
- `api_keys.key_hash`: cifrado AES-256.
- `webhook_secrets.secret_hash`: cifrado AES-256.
- Clave maestra `MAESTRO_ENCRYPTION_KEY` en ENV var del Maestro (NO en BD, NO en código).
- Descifrado solo al inyectar la key en el contenedor de la app.

**Secretos NO en código** (No-negociable 8):
- Pre-commit hook con `gitleaks` antes de cada commit local.
- CI deep scan de **todo el historial de git** en cada PR.
- Image scan de la imagen Docker construida (busca secretos en layers).
- Detección bloquea push/merge sin excepción.

**Secretos NO en logs**:
- `security-auditor` valida en cada PR que el código no loguee:
  - Passwords, hashes, JWTs propios.
  - `MAESTRO_API_KEY`, `MAESTRO_WEBHOOK_SECRET`, `SUPERADMIN_INITIAL_PASSWORD`.
  - Cookies de sesión, headers `Authorization`.
  - Bodies de request con datos sensibles.

**Rotación**:
- API keys del Maestro hacia apps: cada 90 días automático (cronjob).
- Webhook secrets: cada 90 días automático.
- JWT secret del Maestro: rotación manual con audit log; tras rotación, sesiones existentes se invalidan.
- Password de admins: política mínima 12 chars + complejidad + no en blacklist; recomendado cambio cada 90 días (no obligatorio).
- Password del superadmin (`SUPERADMIN_INITIAL_PASSWORD`): después del primer login, el superadmin debe cambiarla via UI; el seeder no la toca de nuevo.

### Capa 5: Validación de input y output

**Input validation**:
- Toda entrada en la API del Maestro valida contra schemas (JSON Schema, OpenAPI, Zod, Joi, según stack).
- Parametrized queries / ORM con prepared statements para prevenir SQL injection.
- Sanitización de slugs y nombres con regex estrictos.
- Tamaño máximo de body (default 1MB; `maestro.yaml` registrado max 50KB).

**Output sanitization**:
- Frontend del portal usa framework con escaping automático (React, Vue).
- API responses en JSON con `Content-Type: application/json; charset=utf-8`.
- Errores no exponen stack traces ni paths internos.
- Errores de auth NO distinguen "user not found" vs "wrong password" (mensaje genérico para no enumerar usuarios).

### Capa 6: Auditoría e integridad

**Audit log inmutable** (No-negociable 12):
- Tabla `audit_log` con triggers SQL que rechazan UPDATE/DELETE.
- Captura: timestamp ms, actor, IP, action, resource, payload before/after.
- Retención: indefinida (parte del backup diario).

**Backup automatizado** (No-negociable 13):
- Diario, cifrado AES-256, almacenamiento externo al VPS.
- Retención mínima 30 días, no reducible.
- BD del Maestro: backup adicional antes de migraciones.

**Persistencia entre versiones** (No-negociable 14):
- Migraciones del framework v3 → v4 → v5 NO truncan datos.
- Cambios destructivos requieren confirmación PO + audit log.

### Capa 7: CI/CD y supply chain

- Imágenes Docker firmadas con `cosign`.
- Provenance + SBOM generados en cada build.
- Trivy o equivalente para scan de vulnerabilidades (CRITICAL/HIGH bloquean el push).
- Tags inmutables (no se reescriben).
- Tag `:latest` prohibido en producción.
- `FROM` con digest `@sha256:...` recomendado, mínimo `<imagen>:<tag-fijo>`.
- Imágenes base oficiales firmadas (Docker Official Images, MCR, distroless de Google).

### Capa 8: Observabilidad de seguridad

Métricas relevantes (más detalle en `10-OBSERVABILIDAD.md`):
- Login failures por IP/admin (ratio de bruteforce).
- Bloqueos de cuenta.
- API key invalida en `/maestro/branding` (intentos no autorizados).
- Webhook signature inválida (apps no rechazan correctamente).
- Container restarts inesperados.
- Health check failures consecutivos.

Alertas críticas:
- Bruteforce detectado.
- Login exitoso desde IP nueva (recomendado).
- Rotación de api_key/webhook_secret fallida.
- Backup fallido.
- Cert TLS no renueva (30 días antes de expiración).

---

## Threat model detallado

### Amenazas externas

#### T1: Bruteforce contra `/api/v2/auth/login` del portal del Maestro
- **Mitigaciones**: rate limiting estricto (5 req/min/IP), bloqueo de cuenta tras 5 fallos, MFA recomendado para `superadmin`, alerta a admin tras 3 bloqueos en 24h.

#### T2: Filtración de `MAESTRO_REGISTRATION_TOKEN` de un repo de app
- **Mitigaciones**: token por owner único, audit log de cada uso, rate limiting (N registros/hora), revocación rápida desde portal, scope acotado (solo registra apps con `metadata.name` permitido).

#### T3: Filtración de `MAESTRO_API_KEY` de un deployment
- **Mitigaciones**: cifrado AES-256 en BD, rotación cada 90 días automática, audit log de uso, alerta si key revocada se sigue usando, opción de invalidar inmediatamente.

#### T4: Replay attack contra hooks salientes (Maestro → app)
- **Mitigaciones**: timestamp en firma + anti-replay window 300s, idempotencia por `event_id`.

#### T5: SSRF desde una app huésped a metadata del cloud (`169.254.169.254`)
- **Mitigaciones**: egress policy bloquea esa IP desde redes de deployment.

#### T6: Compromise de una app huésped y pivote a otras apps
- **Mitigaciones**: aislamiento físico (red Docker dedicada por deployment, BD propia), sin conectividad inter-deployment, App A no puede ver App B aunque corran en el mismo VPS.

#### T7: Inyección SQL en endpoints del Maestro
- **Mitigaciones**: ORM con prepared statements, input validation contra schemas, code review obligatorio.

#### T8: XSS en portal del Maestro
- **Mitigaciones**: framework con escaping automático, CSP estricta, cookies HttpOnly (token no accesible vía JS), `X-Content-Type-Options: nosniff`.

#### T9: CSRF en operaciones admin (ej: destruir deployment)
- **Mitigaciones**: tokens CSRF en formularios, `SameSite=Lax` en cookies, double-submit cookie pattern para APIs.

#### T10: Exfiltración de audit log
- **Mitigaciones**: permisos granulares (`audit_log.read` solo para roles autorizados), exportación logueada en sí misma, alertas si se exporta más del N% del audit log en una sesión.

### Amenazas internas

#### T11: Admin malicioso modifica datos arbitrarios
- **Mitigaciones**: audit log inmutable (admin malicioso NO puede borrar evidencia), separación de deberes (`superadmin` único es escaso, las acciones críticas requieren `superadmin`), revisión periódica del audit log por seguridad.

#### T12: Admin malicioso destruye datos masivamente
- **Mitigaciones**: confirmación explícita para operaciones destructivas (DROP TABLE, TRUNCATE, mass DELETE), retención de 90 días post-destroy de deployments, backups diarios cifrados externos al VPS.

#### T13: Compromiso del VPS (hipotético)
- **Mitigaciones**: backups externos (Azure Blob, S3), claves de cifrado backed-up también externamente, audit log replicado, recovery documentado en runbook.

### Amenazas a la cadena de suministro

#### T14: Imagen Docker base comprometida
- **Mitigaciones**: imágenes oficiales firmadas, trivy scan en CI, anclaje a digest `@sha256:...`.

#### T15: Dependencia npm/composer/pip comprometida
- **Mitigaciones**: lock files commiteados, `npm audit` / `composer audit` en CI, scan de SBOM, actualización regular pero controlada.

#### T16: Pipeline CI comprometido (ej: token de GitHub robado)
- **Mitigaciones**: secrets de GitHub Actions usan `id-token` (OIDC) cuando sea posible, rotación de tokens, scoping a repos específicos, revisión de logs de Actions.

---

## Pre-commit hooks recomendados

```yaml
# .pre-commit-config.yaml
repos:
  - repo: https://github.com/gitleaks/gitleaks
    rev: v8.18.0
    hooks:
      - id: gitleaks
  - repo: https://github.com/pre-commit/pre-commit-hooks
    rev: v4.5.0
    hooks:
      - id: detect-private-key
      - id: detect-aws-credentials
      - id: end-of-file-fixer
      - id: trailing-whitespace
      - id: check-yaml
      - id: check-added-large-files
        args: ['--maxkb=500']
```

Cada repo (Maestro y apps huésped) **DEBERÍA** tener pre-commit configurado.

---

## CI security checks obligatorios

```yaml
# Resumen del checklist
- gitleaks deep scan (todo el historial de git)
- trivy scan de imagen Docker (CRITICAL, HIGH bloquean)
- npm audit / composer audit / pip-audit
- maestro-cli validate (para apps huésped)
- Schema validation del maestro.yaml
- Lint de código (eslint, phpcs, etc.)
- Type checking (TypeScript, mypy, etc.)
- Unit tests
- Integration tests (cuando aplique)
```

---

## Referencias normativas

- `01-PREMISAS-Y-NO-NEGOCIABLES.md` — premisas 7 (mínimo privilegio), 8 (cifrado); no-negociables 7, 8, 9, 10, 11, 12, 13, 14.
- `03-AUTENTICACION-Y-AUTORIZACION.md` — detalle de auth en sus tres planos.
- `04-INFRAESTRUCTURA-DOCKER.md` — aislamiento de redes y contenedores.
- `08-CICD-Y-GOBERNANZA.md` — pipelines con seguridad integrada.
- `framework-agentico/validation/validators/security-auditor.md` — checklist del validador transversal.
- `framework-agentico/core/RULES.md` sección `politica_de_persistencia_de_datos` — confirmación PO para destructivo.

---

## Historial de revisiones

| Versión | Fecha | Cambio |
|---|---|---|
| 4.0.0 | 2026-05-07 | Versión inicial v4. Defensa en profundidad alineada al modelo registry+redirector+provisioner. Threat model explícito con 16 amenazas. Reemplaza al v1 (legacy en `legacy/v3/PremisaWebMaestro/09-SEGURIDAD.md`). |
