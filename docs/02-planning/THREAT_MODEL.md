# Threat Model — Maestro Platform V1

> **Fase:** 02-Planning (validación transversal)
> **Agente:** security-auditor
> **Fecha:** 2026-04-16
> **Metodología:** STRIDE + OWASP ASVS Nivel 2 + CIS Docker Benchmark
> **Compliance objetivo:** GDPR + SOC 2 Type II controles (DEC-013)

---

## 1. Alcance del threat model

Sistemas evaluados:
1. Capa perimetral: Traefik + TLS + ForwardAuth.
2. Backend Maestro (Laravel + Passport + Docker socket proxy).
3. BD del Maestro (PostgreSQL con audit_log inmutable).
4. Portal React (shell + iframes).
5. Instancias de apps huésped (contenedor app + contenedor BD dedicado + red aislada).
6. Hooks salientes HMAC.
7. Gateway inter-apps.
8. CI/CD y registry de imágenes.
9. Secretos (AES-256 at rest, Docker secrets en runtime).

Fuera del alcance (documentado):
- Seguridad del VPS Azure (SO, networking, firewalls) — DEC-011, responsabilidad del humano.
- Seguridad física del datacenter (Azure).
- Seguridad interna de cada app huésped (responsabilidad del dev de la app).

---

## 2. STRIDE por componente (resumen)

| Componente | Spoofing | Tampering | Repudiation | Info disclosure | DoS | Elevation |
|---|---|---|---|---|---|---|
| Traefik / ForwardAuth | M3 | M5 | M7 | M9, M11 | M13 | — |
| Maestro API | M1, M3 | M5, M6 | M7 | M9, M10 | M13 | M2, M4 |
| PostgreSQL Maestro | — | M5 | M7 | M9, M10, M12 | M13 | — |
| Portal React (iframes) | M3 | M14 | — | M11 | — | — |
| Instancia app+BD | M4 | — | — | M10, M12 | M13 | M4 |
| Docker socket proxy | — | — | — | — | M13 | **M2 (crítico)** |
| Hooks salientes | M8 | M8 | — | — | M13 | — |
| Gateway inter-apps | M8 | M6 | M7 | M11 | M13 | M2 |
| CI/CD | — | **M6** | — | — | — | **M2** |
| Secretos | — | — | — | **M9, M10** | — | — |

Leyenda: M1–M14 son mitigaciones listadas en §4.

---

## 3. Vectores de ataque identificados

### 3.1 Críticos

#### T-01: Cross-tenant data leak vía bug de filtrado (R-001 de RESEARCH_FINDINGS)
- **Vector**: un dev de app huésped olvida filtrar `company_id` en una query, o un admin con permisos de una empresa consulta datos de otra.
- **Impacto**: catastrófico — confidentialidad entre tenants es la diferencia entre "plataforma empresarial" y "error de compliance".
- **Probabilidad**: media (errores humanos inevitables en código de apps huésped).
- **Mitigaciones**: M5 (middleware SDK force-add WHERE), M10 (tests de cross-tenant en Fase 03), M11 (CIS DB benchmark + least privilege DB user), M14 (review obligatorio de toda query inter-tenant en PR).

#### T-02: Escape del contenedor Maestro → compromiso del VPS (R-002)
- **Vector**: RCE en el Maestro (vulnerabilidad Laravel/Passport/extension) + Docker socket expuesto → atacante crea contenedores privilegiados y escapa al host.
- **Impacto**: catastrófico — acceso a TODAS las BDs de todas las instancias, al VPS, a los secretos del Maestro.
- **Probabilidad**: baja pero no nula.
- **Mitigaciones**: M2 (ADR-006 docker-socket-proxy con allowlist de endpoints; sin BUILD, sin VOLUMES.DELETE, sin SWARM, sin SECRETS API), M4 (contenedores non-root + no-new-privileges), M15 (Sentry + alerta en 5xx de endpoints Docker API), M16 (imágenes Docker scan en CI).

#### T-03: Robo de token JWT vía XSS en portal o en app huésped
- **Vector**: XSS en app huésped → atacante lee el JWT del localStorage/cookie y lo usa contra el Maestro.
- **Impacto**: alto — suplantación completa del usuario hasta que el token expire.
- **Probabilidad**: media.
- **Mitigaciones**: M1 (cookies `httpOnly; Secure; SameSite=Strict` en portal — nunca localStorage), M2 (token del iframe es de **corta duración**, scoped a la app, no reutilizable en el Maestro), M7 (CSP estricta `default-src 'self'`, `frame-ancestors 'self'`), M12 (refresh tokens rotativos en cada uso).

#### T-04: Impersonación Microsoft OAuth via CSRF state hijack
- **Vector**: atacante intercepta el `state` param del flujo Microsoft y lo usa para vincular su cuenta Entra con el user Maestro de la víctima.
- **Impacto**: alto.
- **Probabilidad**: baja (requiere atacante activo en la red o browser comprometido).
- **Mitigaciones**: M1 (state random 32+ bytes ligado a session en Redis, expiración 5 min), M7 (verificación estricta del state en callback), M17 (`nonce` OIDC validado).

### 3.2 Altos

#### T-05: SQL injection
- **Vector**: input del admin (query filters) o del body (hooks, register) alcanzan DB sin sanitizar.
- **Probabilidad**: baja (Eloquent por default).
- **Mitigación**: M5 (uso exclusivo de Eloquent ORM / parametrized queries; prohibido `DB::raw` con interpolación de input), M18 (static analysis: larastan + phpstan con rule contra `DB::raw()` con concat).

#### T-06: JWT tampering (algoritmo none, RSA weak keys)
- **Vector**: atacante modifica JWT cambiando `alg` a `none` o explotando clave débil.
- **Mitigación**: M2 (Passport configurado con RS256, claves ≥ 4096 bits; `alg: none` rechazado explícitamente), M15 (assertion test en CI).

#### T-07: Hook replay attack
- **Vector**: atacante intercepta un hook con HMAC válido y lo re-envía para duplicar efectos.
- **Mitigación**: M8 (header `X-Maestro-Delivery-Id` único + `X-Maestro-Delivery-Timestamp`; las apps huésped rechazan deliveries con timestamp > 5 min de delay o delivery_id ya procesado).

#### T-08: Supply chain — dependencia npm/composer maliciosa
- **Vector**: typosquatting, dependencia comprometida.
- **Mitigaciones**: M16 (trivy scan en CI), M19 (composer.lock / package-lock.json committeados; Renovate/Dependabot con review manual), M20 (allowlist de registries — npm + packagist; prohibir git://).

#### T-09: Secrets leak en logs, git o imágenes
- **Vector**: developer accidentalmente committea un `.env`, o el Maestro loguea una env var sensible.
- **Mitigaciones**: M9 (gitleaks pre-commit + en CI sobre historial completo), M10 (filtro de Laravel Log que redacta keys sensibles `password, secret, token, *_key`), M11 (imágenes no incluyen `.env`; Dockerfile con `.dockerignore` estricto).

#### T-10: DoS por provisioning masivo
- **Vector**: admin compromedido dispara cientos de provisioning.
- **Mitigación**: M13 (rate limit interno por admin: máx 5 provisioning/min; queue cap).

### 3.3 Medios

#### T-11: Log/audit tampering
- **Vector**: admin de BD intenta UPDATE/DELETE audit_log.
- **Mitigación**: ADR-008 + M11 (triggers DB con `maestro_app` user sin privilegio suficiente; purga controlada por otro user y registrada).

#### T-12: ReDoS en validación de slugs / maestro.yaml
- **Vector**: regex ineficiente explota con input muy largo.
- **Mitigación**: M20 (regex simples lineales; límites de tamaño en input 64KB max).

#### T-13: Insecure deserialization
- **Vector**: PHP unserialize() en queues.
- **Mitigación**: M18 (Laravel queues usan serialización JSON, no PHP native; configurado `queue.connections.*.serializer = 'json'`).

#### T-14: Clickjacking vía portal en iframe embebido por atacante
- **Vector**: atacante carga `https://maestro.local/admin` en un iframe de su sitio.
- **Mitigación**: M7 (CSP `frame-ancestors 'self'`; XFO `DENY` en rutas `/admin/*`; sólo `/` y `/portal/app/*` permiten iframe de self).

### 3.4 Bajos / informativos

- Subdomain takeover: mitigado al no exponer wildcards públicos de DNS sin instancia asociada (humano gestiona DNS; no bloqueante desde framework).
- Cache poisoning de Redis: mitigado por auth a Redis + red privada.
- Open Redirects en flujos de login: mitigado con allowlist de URLs post-login.

---

## 4. Mitigaciones catalogadas

| ID | Mitigación | Dónde se implementa | Validación |
|---|---|---|---|
| M1 | Cookies httpOnly + Secure + SameSite=Strict + state random OAuth | Maestro-Auth | Tests feature de login |
| M2 | docker-socket-proxy con allowlist; Passport RS256 ≥4096; JWT corta duración para iframe | Provisioning + Auth | Test unitario rechaza alg:none |
| M3 | ForwardAuth sin bypass posible por config Traefik | Traefik labels | Test de integración: request sin token → 401 |
| M4 | Contenedores non-root + `--security-opt no-new-privileges` + `--cap-drop ALL` | Dockerfiles + compose | CIS Docker Benchmark |
| M5 | Middleware `EnforceCompanyIdFilter` en SDK + Eloquent scopes; ORM sin `DB::raw(concat)` | SDK + Maestro | Tests cross-tenant |
| M6 | Branch protection + PR review obligatorio + conventional commits + signed commits recomendados | GitHub config | Audit trimestral |
| M7 | CSP estricta, HSTS 1 año + includeSubDomains, X-Frame-Options + frame-ancestors, Referrer-Policy | Traefik middlewares | Security headers scan (securityheaders.com) |
| M8 | HMAC-SHA256 + delivery_id + timestamp en hooks; verificación en app huésped vía SDK | Hooks module + SDK | Test E2E con replay intentional |
| M9 | gitleaks en pre-commit + CI profundo (historial) + filtro Log redactor | Repo + Laravel Log | Test: string parecido a password se redacta |
| M10 | Tests de integración que intentan cross-tenant reads; fuzzing básico | Test suite | Cobertura ≥ requisitos |
| M11 | CIS PostgreSQL Benchmark; usuarios DB con privilegios mínimos; audit_log triggers | DB migration | Audit manual |
| M12 | Refresh tokens rotativos; expiración access 1h / refresh 30d | Passport config | Test feature |
| M13 | Rate limiting (IP, user, admin, CI/CD); circuit breaker Docker API; queue caps | Maestro middleware + queue | Test de carga |
| M14 | Code review de cross-tenant queries; module boundary enforcement (deptrac) | CI + review | PR template |
| M15 | Sentry (o equivalente) con alertas en 5xx y en errores de Passport; tests CI que assertean alg correcto | Observability | Alert config |
| M16 | Trivy image scan bloqueante en CI (CRITICAL/HIGH = fail) | GitHub Actions | release.yml gate |
| M17 | OIDC nonce validado además del state | Maestro-Auth | Unit test |
| M18 | Static analysis phpstan/larastan level 7+; queue serializer=json | CI + config | phpstan run in CI |
| M19 | composer.lock/package-lock commiteado; Dependabot con auto-PR pero merge manual | GitHub | Renovate config |
| M20 | Regex auditadas; límites de body size | Maestro + validator | Unit test ReDoS |

---

## 5. OWASP ASVS Nivel 2 — Mapeo (RNF-073)

Capa de autenticación mapeada contra ASVS v4.0.3:

| Control ASVS | Status |
|---|---|
| V2.1 Password Security | ✅ Bcrypt cost ≥12, longitud mínima 12, zxcvbn en frontend |
| V2.2 General Authenticator | ✅ Passport OAuth2 flujos estándar |
| V2.3 Authenticator Lifecycle | ⚠️ Rotación de claves RS256 anual manual (runbook V2) |
| V2.4 Credential Storage | ✅ Bcrypt para passwords; AES-256 para secrets |
| V2.5 Credential Recovery | ⚠️ V1: reset por admin únicamente (sin self-service reset). Documentado. |
| V2.6 Lookup Secret Verifier | ✅ JWT verificado por firma + expiración + revocation list |
| V2.7 Out-of-Band Verifier | ❌ MFA propio = WON'T V1 (DEC-016). Entra ID cubre el flujo Microsoft. |
| V2.8 Single or Multi-factor OTP | ❌ Idem |
| V2.9 Cryptographic Software | ✅ RS256 ≥4096 bits |
| V2.10 Service Authentication | ✅ Maestro ↔ apps huésped: HMAC hooks; Apps ↔ Maestro: ForwardAuth |
| V3.1 Session Binding | ✅ JWT incluye `sub`, `exp`, `iat`, `jti`, `company_id` |
| V3.2 Session Termination | ✅ Logout → revoked_tokens |
| V3.3 Cookie-based Session | ✅ httpOnly + Secure + SameSite |
| V3.4 Token-based Session | ✅ JWT estándar |
| V3.5 Re-authentication | ⚠️ V1: cambio de empresa no requiere re-auth (documentado; aceptable porque ya se autenticó) |
| V3.7 Defenses Against Session Management Exploits | ✅ nonce, state, rotación de refresh |

Items ❌ corresponden a decisiones conscientes (DEC-016: sin MFA propio); no bloquean ASVS L2 globalmente porque Entra ID provee L2+ para ese flujo.

---

## 6. CIS Docker Benchmark — Cumplimiento V1

Controles críticos (v1.6, items 4 y 5):

| Control | V1 |
|---|---|
| 4.1 Usuario no-root | ✅ USER directive en Dockerfile |
| 4.2 `HEALTHCHECK` | ✅ Dockerfile del Maestro + docker-compose healthcheck |
| 4.5 Image scan | ✅ Trivy en CI |
| 5.1 AppArmor / SELinux profile | ⚠️ Default docker; configurable en VPS (humano) |
| 5.3 Capabilities dropped | ✅ `--cap-drop ALL --cap-add NET_BIND_SERVICE` donde aplique |
| 5.4 `--privileged` | ✅ nunca usado (prohibido por preset RULES) |
| 5.9 Memory limits | ✅ `resources.memory` requerido en cada service |
| 5.10 CPU limits | ✅ idem `resources.cpu` |
| 5.12 Mount filesystem read-only donde posible | ⚠️ Maestro con escritura a `/tmp` y logs; documentado |
| 5.25 Restrict networks | ✅ redes custom por instancia |
| 5.28 Use PIDs cgroup limit | ⚠️ configurable en prod (humano) |

Items ⚠️ se documentan como recomendaciones al humano en `docs/04-delivery/DEPLOY_GUIDE.md`.

---

## 7. GDPR — Controles aplicados

| Principio GDPR | Control en Maestro |
|---|---|
| Lawfulness | Contrato DPA entre LLyAsoc y usuarios; consentimiento explícito en login |
| Purpose limitation | Audit log documenta qué datos se usan y para qué |
| Data minimization | Tablas `users` solo guardan email, nombre, Entra sub; no teléfono, no dirección |
| Accuracy | PATCH /api/admin/users permite corregir datos |
| Storage limitation | Retención backups 30d (DEC-019); purga instancia 90d; purga soft-deleted TBD V2 |
| Integrity/confidentiality | AES-256, HTTPS, audit_log inmutable |
| Accountability | Audit log + documentos DPIA (post-V1 si se amplía alcance) |
| Rights of data subject |  |
| └ Acceso | `/api/auth/me` (propio) |
| └ Rectificación | PATCH sobre user |
| └ Supresión (right to be forgotten) | DELETE /api/admin/users + dispatch hooks `on_user_removed` + purga de tokens |
| └ Portabilidad | `/api/portal/my-data/export` SHOULD HAVE; diferible V2 |
| └ Objeción | N/A V1 (tratamiento basado en contrato de empleo, no consentimiento) |

---

## 8. Riesgos residuales aceptados

| Riesgo | Nivel | Por qué se acepta |
|---|---|---|
| MFA propio ausente | medio | DEC-016; Entra ID cubre el flujo SSO; usuarios user/pass son minoría (admin inicial) |
| Accesibilidad WCAG AA ausente | bajo | DEC-015; mercado V1 (LLyAsoc interna) no lo exige |
| Rotación automática de claves OAuth | bajo | Manual anual es aceptable V1 |
| Single-node (sin HA) | medio | Escala DEC-017 no lo requiere; RTO 4h aceptable |
| Sin self-service password reset | bajo | Reset por admin es factible con escala 1 empresa |
| Retención audit_log igual que backups (30d) | medio | Revisable si compliance cliente lo exige; no hay cliente externo V1 |
| Portabilidad de datos (GDPR) diferida V2 | bajo | Aplica en caso extremo; V1 admin puede exportar manualmente |

---

## 9. Acciones para Fase 03 (Development)

Derivadas de este threat model:

1. Implementar triggers DB de `audit_log` en la migración correspondiente (ADR-008).
2. Configurar Passport con RS256 ≥4096 y test que assertee rechazo de `alg: none`.
3. Configurar docker-socket-proxy con la allowlist exacta del ADR-006.
4. Implementar `EnforceCompanyIdFilter` middleware tanto en Maestro como en SDK.
5. Agregar Trivy y gitleaks al workflow `ci.yml`.
6. Implementar tests de integración cross-tenant explícitos (mínimo 5 casos).
7. Configurar CSP estricta y security headers en Traefik.
8. Configurar Laravel Log redactor para keys sensibles.
9. Configurar rate limiting con buckets separados para login, admin, apps/register.
10. Escribir runbook de rotación de `MAESTRO_ENCRYPTION_KEY`.

Estas acciones se registran como DEL (deliverables) heredadas a Fase 03.

---

## 10. Validación y revisión

Este threat model debe revisarse:
- Tras cada nueva épica implementada (fase 03).
- Antes de release V1 (fase 04) con un re-scan completo.
- Anualmente en producción (fase 05 + compliance-analyst).

Firmas de aceptación:
- security-auditor: ✅ (2026-04-16)
- compliance-analyst: ✅ GDPR + SOC 2 controles mapeados (2026-04-16)
- software-architect: ✅ mitigaciones reflejadas en ADR-001/002/004/005/006/008 (2026-04-16)
