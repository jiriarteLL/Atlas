# Validación Transversal — Iteración stabilization-1

> **Fecha:** 2026-04-20
> **Orquestador:** Transversal
> **Input:** `docs/04-delivery/INTEGRATION_REPORT_iter2.md` + diff vs v1.0.0-rc.1
> **Veredicto consolidado:** **APROBADO CON OBSERVACIONES**

---

## 1. Secuencia de validación

1. code-reviewer
2. security-auditor
3. compliance-analyst (delta-only vs DEC-013)
4. performance-analyst (delta-only)
5. qa-tester

`documentation-writer` actúa post-aprobación; `executive-reporter` sólo bajo demanda del PM.

---

## 2. code-reviewer

### 2.1 Áreas revisadas
- `.env` / `.env.example` / `docker-compose.dev.yml`
- `config/services.php`
- `app/Http/Controllers/Auth/MicrosoftController.php`
- `app/Modules/Backups/Services/BackupService.php`
- `database/seeders/DemoPoSeeder.php`
- `app/Console/Commands/BootstrapDemoCommand.php`
- `portal/src/pages/auth/LoginPage.tsx`
- `tests/Feature/Auth/MicrosoftControllerTest.php`
- `tests/e2e-smoke/login.spec.mjs`
- `justfile`

### 2.2 Hallazgos

| Severidad | Hallazgo | Archivo | Acción |
|-----------|----------|---------|--------|
| Bloqueante | — | — | — |
| Alto | Ninguno | — | — |
| Medio | `BackupService::disk()` captura `InvalidArgumentException` pero no registra nada cuando cae al fallback local en producción. En prod eso enmascararía un driver Azure mal instalado. | `backend/app/Modules/Backups/Services/BackupService.php:130` | **Observación** → agregar log `warning` cuando el fallback se activa en `env != 'testing'`. No bloquea estabilización. TD-040 MEDIUM. |
| Medio | `DemoPoSeeder::upsertUser()` rehidrata password en cada corrida. Es intencional (idempotente), pero si alguien seedea en un entorno ya en uso, resetea credenciales silenciosamente. | `backend/database/seeders/DemoPoSeeder.php` | **Observación** → `BootstrapDemoCommand` ya está bloqueado en `production`. Suficiente. Documentar en `RUNBOOK`. |
| Bajo | `LoginPage.tsx` lee `import.meta.env.VITE_MICROSOFT_ENTRA_ENABLED === 'true'`. La comparación string es correcta pero frágil si alguien setea `True`/`1`. | `portal/src/pages/auth/LoginPage.tsx` | **Observación** → en este repo la convención es minúsculas. Suficiente. |
| Bajo | `just e2e` hace `npm install` por corrida. | `justfile` | Ya documentado como G-4/TD-039 en `INTEGRATION_REPORT_iter2.md`. |

**Veredicto code-reviewer: APROBADO CON OBSERVACIONES.** Ninguna observación bloquea la iteración.

---

## 3. security-auditor

### 3.1 Checklist aplicable a esta iteración

| Item | Estado |
|------|--------|
| Secrets rotados tras unificación `.env` | **PASS** — 7 secrets rotados (DB, REDIS, DB_PURGER, MAESTRO_ENCRYPTION, BACKUP_ENCRYPTION, PASSPORT CLIENT ID+SECRET). |
| `.env` ignorado en `.gitignore` | **PASS** — verificado, `.env` en `.gitignore` raíz desde iter1. |
| `backend/.env` eliminado (riesgo de drift de secrets) | **PASS**. |
| Credenciales dev distinguibles de prod | **PASS** — prefijo `dev_` + endpoints `maestro-*` (hostnames internos). |
| Feature flag Entra: cerrado por default | **PASS** — `MICROSOFT_ENTRA_ENABLED=false` en `.env`, `.env.example` y `phpunit.xml` (`force="true"`). |
| Respuesta 503 con audit log | **PASS** — `guardDisabled()` llama `audit->log()` antes de responder. |
| Azurite: credenciales bien conocidas | **ACEPTADO** — `devstoreaccount1` es la credencial pública documentada del emulador. Sólo expuesta en `maestro-network`, no en `traefik-public`. Registrar en RUNBOOK para evitar que alguien use esos mismos valores en prod. |
| Credenciales PO/tester | **ACEPTADO** — passwords cumplen política (≥12, mayúsc+minúsc+num+símbolo). Bootstrap bloqueado en prod. |
| OWASP A02 (Cryptographic Failures) — claves de cifrado | **PASS** — `MAESTRO_ENCRYPTION_KEY` y `BACKUP_ENCRYPTION_KEY` son base64-encoded de 32 bytes random nuevos. |
| OWASP A07 (ID&Auth) — flag Entra | **PASS** — cero superficie de ataque expuesta en dev sin credenciales reales. |
| Supply chain delta | **PASS** — imagen `mcr.microsoft.com/azure-storage/azurite:latest` es first-party Microsoft; `mcr.microsoft.com/playwright:v1.49.0-jammy` pinned. |

### 3.2 Hallazgos

| Severidad | Hallazgo | Acción |
|-----------|----------|--------|
| CRITICAL | 0 | — |
| HIGH | 0 | — |
| MEDIUM | Azurite está sin auth en `maestro-network`. Cualquier contenedor que entre a esa red puede leer/escribir blobs. Riesgo acotado a dev; en prod el stack usa Azure Blob real con SAS. | **Observación** — documentar en RUNBOOK que Azurite no debe promoverse a prod. TD-041 MEDIUM (sólo si algún día se abre red de dev a hosts externos). |
| MEDIUM | Permisos de `/app/storage/logs` (Known Gap G-1) generan 500 encadenados → el handler de error global podría filtrar stack trace con `APP_DEBUG=true`. Dev only, pero si alguien clona y abre `https://maestro.maestro.local` desde LAN, ver el body. | **Observación** — cerrar junto con G-1 (TD-036). El stack ya se expone sólo en la red local Docker vía Traefik; no hay 0.0.0.0 expuesto al host. |
| LOW | `BACKUP_ENCRYPTION_KEY` viaja en el `command` de `pg_dump | openssl enc -pass pass:$KEY`. En `ps aux` dentro del contenedor API queda visible. | Heredado de iter anteriores; ya tracked como parte del modelo de threat. No se re-abre aquí. |

**Veredicto security-auditor: APROBADO CON OBSERVACIONES.** 0 CRITICAL / 0 HIGH → no bloquea.

---

## 4. compliance-analyst

### 4.1 Delta contra DEC-013 (GDPR + SOC 2 controles + CIS Docker + OWASP Top 10/ASVS N2)

- **GDPR retención (DEC-019):** sin cambios de retención. PASS.
- **GDPR derecho de acceso/borrado (TD-001/TD-002):** sigue abierto. Fuera de alcance de iter. PASS por omisión.
- **SOC 2 Type II evidencias (TD-007):** sin cambios. PASS por omisión.
- **CIS Docker Benchmark:** el nuevo servicio `azurite` corre con defaults del publisher (no define `security_opt no-new-privileges` ni `cap_drop ALL`). En `docker-compose.dev.yml` es tolerable (dev only, no `docker-compose.prod.yml`), pero el patrón de hardening de iter 04 no se aplicó. **Observación.** En prod no debe desplegarse Azurite.
- **OWASP ASVS N2 — V2 Authentication:** feature flag cumple V2.1.1 (no passwords por defecto) y V2.3.3 (políticas de recuperación). PASS.
- **OWASP ASVS N2 — V3 Session Management:** sin cambios. PASS.

### 4.2 Hallazgos

| Severidad | Hallazgo | Acción |
|-----------|----------|--------|
| MEDIUM | Azurite en `docker-compose.dev.yml` sin hardening CIS | **Observación** — aceptable dev-only, prohibir explícitamente en prod. Registrar en RUNBOOK §Entornos + TECH_DEBT TD-042 LOW (alinear hardening si se promueve Azurite a perf/staging). |

**Veredicto compliance-analyst: APROBADO CON OBSERVACIONES.**

---

## 5. performance-analyst

### 5.1 Delta performance

- **Nuevos servicios:** `azurite` (baseline footprint < 150 MB RAM en idle, observado). No impacta los targets DEC-008 (50 users concurrentes) ni DEC-017 (1 tenant × 7 apps).
- **Nuevos tests:** +2 en `MicrosoftControllerTest` → `phpunit` total 151 vs 149 previo. Tiempo total subió de 38s a 40s (< 5% delta).
- **Seeder idempotente:** `DemoPoSeeder` corre en ≈ 400ms (observado vía `artisan db:seed --class=DemoPoSeeder` en shell). Sin queries N+1.
- **LoginPage flag:** 0 cost runtime; es un `if` al render.

### 5.2 Hallazgos

| Severidad | Hallazgo | Acción |
|-----------|----------|--------|
| — | Ninguno | — |

**Veredicto performance-analyst: APROBADO.**

---

## 6. qa-tester

### 6.1 Cobertura de la iteración

| Caso | Cobertura |
|------|-----------|
| Login PO happy path | **unit/feature** `LoginTest` + **E2E** `login.spec.mjs` |
| Feature flag Entra OFF → redirect 503 | **feature** `test_redirect_devuelve_503_cuando_feature_flag_desactivado` |
| Feature flag Entra OFF → callback 503 | **feature** `test_callback_devuelve_503_cuando_feature_flag_desactivado` |
| Feature flag Entra ON → redirect a MS | **feature** `test_redirect_envia_a_microsoft_con_state` |
| Feature flag Entra ON → callback state inválido | **feature** `test_callback_state_invalido_redirige_a_error` |
| Seed DemoPoSeeder idempotente | **manual runtime** (2 ejecuciones consecutivas, cero duplicados) |
| Backup fallback local sin driver azure | **feature** `BackupServiceTest` pasa con `AZURE_STORAGE_ACCOUNT=""` |
| Portal muestra/oculta botón MS | **E2E implícito** (login.spec verifica que `login-microsoft` no está cuando flag OFF) |

### 6.2 Métricas
```
PHPUnit: 151 / 151 PASS, 289 assertions, 40s
Coverage: 80.2% statements (≥ 80% target), 70.6% branches (≥ 70% target)
Smoke: 8 / 8 PASS
E2E: 5 / 5 core steps PASS, 2 WARN (G-1, G-2 documentados)
```

### 6.3 Hallazgos

| Severidad | Hallazgo | Acción |
|-----------|----------|--------|
| MEDIUM | G-2 admin_users_reachable WARN | Documentado en INTEGRATION_REPORT. Abrir **TD-037**. |
| MEDIUM | G-1 no_console_errors WARN | Documentado en INTEGRATION_REPORT. Abrir **TD-036** (raíz: permisos `/app/storage/logs`). |

**Veredicto qa-tester: APROBADO CON OBSERVACIONES.** Los WARN están fuera del happy path acordado.

---

## 7. Veredicto consolidado

| Agente | Veredicto | Bloqueantes | Observaciones a persistir |
|--------|-----------|-------------|---------------------------|
| code-reviewer | APROBADO CON OBSERVACIONES | 0 | TD-040 (log fallback Azure) |
| security-auditor | APROBADO CON OBSERVACIONES | 0 | TD-041 (Azurite hardening sólo si promueve) |
| compliance-analyst | APROBADO CON OBSERVACIONES | 0 | TD-042 (CIS Azurite si promueve) |
| performance-analyst | APROBADO | 0 | — |
| qa-tester | APROBADO CON OBSERVACIONES | 0 | TD-036, TD-037 |

**Resultado 5/5: APROBADO CON OBSERVACIONES.**

Se autoriza la iteración stabilization-1. Todas las observaciones son **no bloqueantes** y se registran como deuda nueva (TD-036..TD-042) en `docs/05-operations/TECH_DEBT.md` en Task #8.

---

## 8. Entradas a TECH_DEBT (a aplicar en Task #8)

```yaml
- id: TD-036
  severity: HIGH
  title: "Permisos /app/storage/logs generan 500 en runtime"
  found_in: stabilization-1 (E2E WARN G-1)
  remediation: "Chown/chmod en Dockerfile o init container. Cierra TD-019/TD-020 indirectamente."
  owner: backend-developer
  target: 2026-Q3
- id: TD-037
  severity: MEDIUM
  title: "E2E admin_users_reachable falla por redirección a login tras 500 encadenado"
  found_in: stabilization-1 (E2E WARN G-2)
  remediation: "Se cierra al resolver TD-036."
  owner: frontend-developer
  target: 2026-Q3
  blocked_by: TD-036
- id: TD-038
  severity: LOW
  title: "ApplicationSeeder base con nginx-test para DemoPoSeeder"
  found_in: stabilization-1 (Known Gap G-3)
  owner: backend-developer
  target: backlog
- id: TD-039
  severity: LOW
  title: "Imagen maestro-e2e con Playwright npm precargado"
  found_in: stabilization-1 (Known Gap G-4)
  owner: devops-engineer
  target: backlog
- id: TD-040
  severity: MEDIUM
  title: "BackupService fallback local sin warning en producción"
  found_in: stabilization-1 (code-reviewer)
  owner: backend-developer
  target: backlog
- id: TD-041
  severity: MEDIUM
  title: "Azurite sin auth expuesto en maestro-network"
  found_in: stabilization-1 (security-auditor)
  remediation: "Sólo mitigar si Azurite se promueve a staging/perf. Prohibir en prod ya documentado en RUNBOOK."
  owner: devops-engineer
  target: backlog
- id: TD-042
  severity: LOW
  title: "Hardening CIS Docker para contenedor azurite"
  found_in: stabilization-1 (compliance-analyst)
  remediation: "Añadir no-new-privileges + cap_drop ALL si se promueve."
  owner: devops-engineer
  target: backlog
```
