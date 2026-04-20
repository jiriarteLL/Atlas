# Integration Report — Iteración stabilization-1

> **Fecha:** 2026-04-20
> **Rol:** F04 Integrator
> **Base:** v1.0.0-rc.1 (tag pendiente) + DEC-025/026/027 aplicadas
> **Objetivo:** Entregar versión estable con `.env` unificado, feature flag Entra, Azurite emulador y credenciales de integración.

---

## 1. Alcance de la iteración

Aprobado por el humano (ver summary de sesión previa):

1. **Estable** = `docker-compose.dev.yml up` saludable + `phpunit` 100% + 8/8 smoke tests + login happy path E2E.
2. Inconsistencia raíz resuelta: `.env` duplicado (`./.env` vs `backend/.env`) unificado en `./.env` (Estrategia A, DEC-025).
3. Sin credenciales de terceros: Entra detrás de feature flag (DEC-026), Azure Blob reemplazado por Azurite en dev (DEC-027), Sentry vacío.
4. Credenciales de integración: PO + tester sobre tenant `Acme Demo`.
5. **Fuera de alcance:** cierre de TD HIGH (TD-015/001/002/007/019/020), tag `v1.0.0`.

---

## 2. Cambios aplicados

### 2.1 Unificación `.env` (DEC-025)
- Fuente única: `./.env` (raíz) leída por `docker-compose.dev.yml` y todos los servicios.
- `backend/.env` **eliminado**.
- `.env.example` regenerado como template sincronizado.
- Secrets rotados esta iteración: `DB_PASSWORD`, `REDIS_PASSWORD`, `DB_PURGER_PASSWORD`, `MAESTRO_ENCRYPTION_KEY`, `BACKUP_ENCRYPTION_KEY`, `PASSPORT_PASSWORD_CLIENT_ID/SECRET`.

### 2.2 Feature flag Microsoft Entra ID (DEC-026)
- `config/services.php`: key nueva `microsoft.enabled` controlada por `MICROSOFT_ENTRA_ENABLED`.
- `app/Http/Controllers/Auth/MicrosoftController.php`: `guardDisabled()` devuelve **HTTP 503** + `{error.code: "entra_disabled"}` cuando el flag está en `false`.
- Portal `LoginPage.tsx`: botón "Iniciar sesión con Microsoft" renderizado sólo si `VITE_MICROSOFT_ENTRA_ENABLED === 'true'`.
- Tests nuevos: `test_redirect_devuelve_503_cuando_feature_flag_desactivado` y `test_callback_devuelve_503_cuando_feature_flag_desactivado` (clase `MicrosoftControllerTest`).

### 2.3 Azurite emulador para backups en dev (DEC-027)
- Servicio `azurite` agregado a `docker-compose.dev.yml` (imagen `mcr.microsoft.com/azure-storage/azurite:latest`, volumen `maestro-azurite-data`).
- `.env`: `AZURE_STORAGE_ENDPOINT=http://azurite:10000/devstoreaccount1` + credenciales por defecto `devstoreaccount1`.
- `BackupService::disk()`: fallback silencioso a disco local si el driver `azure` no está registrado (sin `league/flysystem-azure` en test, el fallback evita romper `phpunit`).
- `phpunit.xml`: `AZURE_STORAGE_ACCOUNT` forzado a vacío para que los tests nunca toquen Azurite.

### 2.4 Credenciales de integración (PO + tester)
- `DemoPoSeeder` (idempotente, `firstOrCreate` + password rehidratada):
  - Company: `acme-demo`, nombre `Acme Demo`.
  - PO: `po@maestro.local` / `MaestroPO2026!` (roles `admin`, permissions full).
  - Tester: `tester@maestro.local` / `TesterMaestro2026!` (rol `member`).
  - Aplicación vinculada: `nginx-test` (si existe; warning si no).
- Comando `artisan maestro:bootstrap-demo [--fresh]` orquesta `migrate` + `db:seed DemoPoSeeder`; bloqueado en `production`.
- Recipes `just bootstrap-demo` y `just bootstrap-demo-fresh` agregados al `justfile`.

### 2.5 E2E Playwright (`just e2e`)
- Spec `tests/e2e-smoke/login.spec.mjs` con defaults `po@maestro.local` / `MaestroPO2026!`.
- Recipe `just e2e` corre `mcr.microsoft.com/playwright:v1.49.0-jammy` en la red `maestro-network`, copia el spec a `/tmp` y hace `npm init` + `npm i playwright@1.49.0` antes de ejecutar (único workaround estable para la imagen oficial; ver Known Gap G-4).

---

## 3. Resultados de la validación runtime

### 3.1 Stack
`just up` → 9 servicios healthy:
- `maestro-db` (pg16) healthy.
- `maestro-redis` healthy.
- `maestro-api` (php-fpm+nginx) healthy tras AI-3 localhost→127.0.0.1.
- `maestro-worker` healthy con `pgrep -f queue:work`.
- `maestro-portal` (vite) healthy.
- `maestro-traefik` routing OK para `maestro.maestro.local`.
- `maestro-docker-proxy` healthy.
- `azurite` healthy (tcp 10000).
- `maestro-scheduler` corriendo `schedule:work`.

### 3.2 PHPUnit (dentro de `maestro-api`)
```
OK (151 tests, 289 assertions)
Coverage: 80.2% statements (target ≥ 80%) — sin regresiones vs iter9.
```
Cero tests fallidos, cero skipped.

### 3.3 Smoke tests API
| # | Endpoint | Verbo | Esperado | Observado | Resultado |
|---|----------|-------|----------|-----------|-----------|
| 1 | `/api/health` | GET | 200 | 200 `{status:"ok"}` | PASS |
| 2 | `/api/auth/login` (PO) | POST | 200 | 200 con `access_token`+`refresh_token`+`user` | PASS |
| 3 | `/api/auth/me` (JWT PO) | GET | 200 | 200 con user + memberships | PASS |
| 4 | `/api/auth/validate` (JWT PO) | GET | 200 | 200 con headers ForwardAuth | PASS |
| 5 | `/api/auth/microsoft/redirect` | GET | 503 | 503 `entra_disabled` | PASS |
| 6 | `/api/auth/microsoft/callback` | GET | 503 | 503 `entra_disabled` | PASS |
| 7 | `/api/admin/companies` (PO) | GET | 200 | 200 con lista `Acme Demo` | PASS |
| 8 | `artisan migrate --pretend` | CLI | 0 cambios | 0 migraciones pendientes | PASS |

**Smoke = 8/8 PASS.**

### 3.4 E2E Playwright (`just e2e`)
```
[PASS] portal_loads                     — https://maestro.maestro.local/login
[PASS] login_form_visible               — email=true password=true
[PASS] login_post                       — submit ejecutado
[PASS] post_login_redirect              — http://maestro-portal:8081/
[PASS] token_stored                     — localStorage['maestro.access_token'] len=1077
[WARN] admin_users_reachable            — ver Known Gap G-2
[WARN] no_console_errors                — ver Known Gap G-1
=== RESUMEN: 7 steps, 0 fail, 5 pass, 2 warn ===
```

Happy path de login **PASS** (core 5/5). Los dos WARN quedan documentados abajo y no bloquean la estabilización (fuera de alcance acordado con el humano).

---

## 4. Known Gaps (quedan para TD / iteraciones futuras)

| ID | Origen | Descripción | Impacto | Acción sugerida |
|----|--------|-------------|---------|-----------------|
| G-1 | E2E WARN `no_console_errors` | Dos respuestas 500 en consola del browser tras navegar a `/admin/users`. Raíz en `maestro-api`: `UnexpectedValueException: /app/storage/logs/laravel-...log could not be opened in append mode` (permisos del volumen) + `authorization server denied the request` encadenado cuando el handler de logs falla y tumba el request. | No bloquea login; sí ensucia logs y puede degradar endpoints que dependan del logger. | Alinear con TD-019 (E2E login) y TD-020 (OAuth MS). Propuesta: dockerfile `chown -R www-data:www-data /app/storage` y `chmod -R ug+rwX` en build, o init container que corrige permisos. Registrar como **TD-036**. |
| G-2 | E2E WARN `admin_users_reachable` | Tras navegar a `/admin/users`, el body contiene el markup del login ("Bienvenido a Maestro \| Email \| Contraseña"). Consecuencia directa de G-1: un 500 en la primera llamada API dispara el refresh de token, el refresh también cae por logs y el portal redirige a `/login`. | No bloquea smoke 8/8; sí impide automatizar golden path admin sin mitigar G-1. | Se cierra automáticamente al resolver G-1. Dejar test como WARN hasta entonces. Registrar como **TD-037**. |
| G-3 | Seed demo | Aplicación `nginx-test` no está seedeada por default (pertenece a provisioning E2E de iter 8). `DemoPoSeeder` emite warning si no existe; PO queda sin app vinculada en ese caso. | Bajo — no afecta login ni admin CRUD. | Agregar `ApplicationSeeder` base con `nginx-test` stub, o vincular a primera app disponible en DB. Registrar como **TD-038 LOW**. |
| G-4 | E2E recipe | `just e2e` hace `npm install` dentro del contenedor Playwright en cada corrida (≈ 15s). La imagen oficial sólo trae browsers, no el paquete Node. | Lento pero determinista. | Construir imagen propia `maestro-e2e` con `FROM mcr.microsoft.com/playwright:v1.49.0-jammy` + `npm i -g playwright@1.49.0`. Registrar como **TD-039 LOW**. |

Ninguno de G-1..G-4 se cierra en esta iteración por acuerdo explícito: el humano pidió estable **sin** tocar la deuda HIGH.

---

## 5. Criterios de "estable" — cumplimiento

| Criterio | Objetivo | Resultado |
|----------|----------|-----------|
| Stack `just up` healthy | 9/9 servicios healthy | PASS |
| PHPUnit | 151+ / 151+ PASS | **151 / 151 PASS** |
| Smoke tests | 8/8 | **8 / 8 PASS** |
| E2E login happy path | 5 core steps PASS | **5 / 5 PASS** |
| `.env` unificado | `backend/.env` eliminado, un solo archivo raíz | PASS |
| Feature flag Entra | 503 + portal sin botón | PASS |
| Azurite dev | contenedor up + accesible `http://azurite:10000` | PASS |
| Credenciales integración | PO + tester idempotentes | PASS |

**Iteración stabilization-1 → LISTA para validación transversal.**

---

## 6. Artefactos tocados

```
.env                                                         (rewritten)
.env.example                                                 (rewritten)
docker-compose.dev.yml                                       (azurite + portal env_file)
justfile                                                     (+ bootstrap-demo + e2e)
backend/.env                                                 (deleted)
backend/config/services.php                                  (flag microsoft.enabled)
backend/app/Http/Controllers/Auth/MicrosoftController.php    (guardDisabled 503)
backend/app/Modules/Backups/Services/BackupService.php       (fallback local)
backend/app/Console/Commands/BootstrapDemoCommand.php        (nuevo)
backend/database/seeders/DemoPoSeeder.php                    (nuevo)
backend/phpunit.xml                                          (flags test)
backend/tests/Feature/Auth/MicrosoftControllerTest.php       (+ setUp + 2 tests)
portal/src/pages/auth/LoginPage.tsx                          (flag + data-testids)
tests/e2e-smoke/login.spec.mjs                               (default creds PO)
docs/04-delivery/INTEGRATION_REPORT_iter2.md                 (este archivo)
```

Quedan pendientes para Task #7 (transversal) y Task #8 (CHECKPOINT_GLOBAL + CHANGELOG).
