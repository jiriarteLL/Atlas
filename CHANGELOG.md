# Changelog — Inventario LLYA

## [2.0.0] — sin publicar (2026-09-30)

Primera version como app huesped del contrato `maestro.platform/v2`, en paralelo al Inventario de
produccion (v3.4, servicio NSSM en Windows con SQLite).

### Agregado
- Contenedor Docker (imagen unica: FastAPI sirve el frontend compilado) y tres compose:
  `docker-compose.yml` (dev local), `docker-compose.test.yml` y `docker-compose.preprod.yml`.
- PostgreSQL como base (contenedor propio por ambiente).
- `GET /health` y `GET /maestro/branding` (autenticado con `X-Maestro-Api-Key`).
- Tablas `roles`, `permissions`, `role_permissions` y `user_roles`; permisos por codigo.
- Seeder idempotente del superadmin `admin@llyasoc.com` (falla si la password falta o es debil).
- Sesion: access token JWT de 15 min (solo en memoria del frontend) + refresh token rotativo en cookie
  `inventario_session` HttpOnly/SameSite=Strict; `POST /auth/refresh`; deteccion de reuso de refresh.
- `POST /logout` y `POST /auth/logout` revocan access y refresh; cambio de password y desactivacion invalidan
  todas las sesiones.
- Bloqueo de cuenta de 15 min tras 5 fallos; limite de 10 intentos por hora por email.
- Politica de passwords (>= 12 caracteres, complejidad, blacklist de passwords comunes). Login por usuario o email;
  email unico y obligatorio. Cambio de password obligatorio para el superadmin sembrado y tras un reset.
- Audit log inmutable (trigger que rechaza UPDATE/DELETE) con user_id, user-agent y request_id.
- Logs JSON a stdout con request_id, user_id y app_slug (CONVENCIONES §10); cabecera `X-Request-Id`.
- `GET /metrics` (Prometheus) protegido con `X-Maestro-Api-Key`; cabeceras de seguridad (CSP, nosniff, HSTS).
- Snapshot de tendencias automatico dentro de la app y `POST /api/tendencias/snapshot`.
- CI: `ci.yml` (tests, lint, build, schema v2, compose, gitleaks) y `deploy.yml` (build, Trivy, ghcr, cosign).
- Documentacion de fases en `docs/inventario/` y ADR-001..004; `SECURITY.md`; proyecto registrado en el framework.
- 83 tests de backend (contrato, auth, sesion, seeder, negocio, logs y chequeos estaticos).

### Cambiado
- Toda la configuracion por variables de entorno; sin IPs, puertos, rutas de Windows ni secretos en el codigo.
- Todos los endpoints de `/api` exigen login (antes varios GET eran publicos).
- Rate limit del login: 5 intentos por minuto por IP (antes 10).
- `DATABASE_URL` acepta el formato canonico del Maestro (`postgres://`).
- Imagenes base fijadas por digest; usuario no-root con UID 1001.
- JWT con PyJWT en lugar de python-jose (que arrastraba `ecdsa`, CVE-2024-23342 sin fix); `npm audit fix`.
- Claves de sincronizacion comparadas en tiempo constante (`hmac.compare_digest`).
- Adjuntos guardados en la base (sin volumen de storage; ADR-001).
- Frontend con rutas relativas (mismo origen) y controles segun permisos.
- Agentes: servidor y clave por parametro; ahora mandan `X-Sync-Key`.

### Quitado (dependian del UserManager o de Windows)
- Secciones Licencias y Usuarios/Nomina, alta ABM, alertas de nomina y reportes de empleados.
- Sincronizacion con el Excel de stock local y scripts sobre SQLite.

---

## Historial del repo template (heredado)

> Cambios del **repo template** (este repositorio). Para cambios del **framework agentico** ver `framework-agentico/CHANGELOG.md`.

---

## [Unreleased] / 2026-05-07

### Added
- Framework agentico **v4.0** (ver `framework-agentico/CHANGELOG.md` para detalle).
- Contrato **`maestro.platform/v2`** documentado en:
  - `docs/APP_HUESPED_SPEC.md` (canonico tras cleanup)
  - `docs/APP_HUESPED_BEST_PRACTICES.md` (canonico tras cleanup)
  - `docs/CONVENCIONES_PLATAFORMA.md` (canonico tras cleanup)
  - `docs/schemas/maestro.yaml.schema.v2.json` (nuevo schema v2)
- Preset `framework-agentico/agents/presets/maestro-platform/` (canonico tras cleanup; aplica al construir la Web Maestro / Web Anfitriona).
- Sistema de **migracion lazy** v3 -> v4 (`framework-agentico/migration/`).
- Nueva **fase 05-seeding** del ciclo agentico (superadmin `admin@llyasoc.com` idempotente).
- `.env.example` reescrito para v4 (sin `MOCK_*`; agrega `JWT_SECRET`, `MAESTRO_API_KEY`, `MAESTRO_WEBHOOK_SECRET`, `SUPERADMIN_INITIAL_PASSWORD`).
- `README.md` reescrito para reflejar el modelo v4.
- `.gitignore` (root) bumpeado con exclusiones robustas v4.

### Changed
- `framework-agentico/checkpoints/GLOBAL.md`: `framework_version: "4.0"` + `default_preset` (en lugar de `preset` hardcodeado).
- `framework-agentico/core/RULES.md`: titulo "v4" + secciones nuevas: `glosario_de_sinonimos` (§0), `activacion_de_preset` (§8 reescrita), `politica_de_versionado` (§16), `politica_de_persistencia_de_datos` (§17). Seccion 15 `migracion_entre_versiones` ya estaba.
- `framework-agentico/core/PRESET_WEB_MAESTRO.md`: rewrite completo a modelo v4 (single-tenant + auth propia + branding endpoint + seeding).
- `framework-agentico/core/PM.md`: system prompt actualizado con flujo de migracion lazy, flujo del seed interactivo y confirmacion de preset al iniciar proyecto.
- `framework-agentico/core/CONTEXT_PACKET.md`: version 4.0 + preset_constraints actualizados.
- `framework-agentico/core/templates/PROJECT_TEMPLATE.md`: lista de fases 00-07 + campos nuevos `project_type` y `preset_active`.
- `framework-agentico/core/templates/COST_SUMMARY_TEMPLATE.md`: lista de fases 00-07 (incluyendo `05-seeding`).
- `framework-agentico/phases/`: renumeracion (`05-operations` -> `06-operations`, `06-retrospective` -> `07-retrospective`) + nueva fase `05-seeding.md`.
- `framework-agentico/validation/validators/*`: validadores actualizados para modelo v4 (security exige tabla users + bcrypt; qa testea login propio + branding + seed; compliance valida password policy + audit log; performance sin filtros multi-tenant; code-reviewer y documentation-writer alineados a v4).
- `CLAUDE.md` (root): version 4.0.0 + arquitectura ASCII con fases 00-07 + seccion sobre migracion lazy + paso de confirmacion de preset.

### Deprecated
- Contrato `maestro.platform/v1` y modelo de auth por headers `X-Auth-*`. Apps existentes deben migrar a v2 (ver `framework-agentico/migration/v3-to-v4.md`).
- `legacy/v3/docs/APP_HUESPED_SPEC.md` (v1) — superado por `docs/APP_HUESPED_SPEC.md` (canonico).
- `legacy/v3/docs/APP_HUESPED_BEST_PRACTICES.md` (v1) — superado por `docs/APP_HUESPED_BEST_PRACTICES.md` (canonico).
- `legacy/v3/docs/CONVENCIONES_PLATAFORMA.md` (v1) — superado por `docs/CONVENCIONES_PLATAFORMA.md` (canonico).
- `legacy/v3/framework-agentico/agents/presets/maestro-platform/` (v1) — superado por `framework-agentico/agents/presets/maestro-platform/` (canonico).
- `legacy/v3/PremisaWebMaestro/` (constitucion v1 del Maestro) — sera reemplazada por `PremisaWebMaestro/` v4 en Fase 3 del cleanup.
- `legacy/v3/arquitectura_actual.md` (snapshot historico 2026-04-14) — sin reemplazo.
- `docs/schemas/maestro.yaml.schema.json` (v1) — sigue presente como referencia legacy. Apps nuevas usan `schema.v2.json`.

### Removed
- Directorio `mock/` (modelo v3 con inyeccion de headers `X-Auth-*`). Eliminado del template canonico — apps v4 con auth propia no requieren mock. Recuperable via git history si fuera necesario.
- Directorio `cli/node/templates/node-express/` (template Node ilustrativo). Eliminado del template canonico — el repo es stack-agnostico, cualquier stack containerizable con Docker es valido. Recuperable via git history.

### Path canonicalization (cleanup v4, 2026-05-07)
- **Politica nueva** documentada en `framework-agentico/core/RULES.md` seccion `politica_de_versionado`: el path canonico (sin sufijo de version) siempre apunta a la version vigente; las versiones anteriores se mueven a `legacy/v{n}/` con banner DEPRECADO en su encabezado.
- Renombrados (sufijo `_V2`/`-v2` removido del path canonico):
  - `docs/APP_HUESPED_SPEC_V2.md` -> `docs/APP_HUESPED_SPEC.md`
  - `docs/APP_HUESPED_BEST_PRACTICES_V2.md` -> `docs/APP_HUESPED_BEST_PRACTICES.md`
  - `docs/CONVENCIONES_PLATAFORMA_V2.md` -> `docs/CONVENCIONES_PLATAFORMA.md`
  - `framework-agentico/agents/presets/maestro-platform-v2/` -> `framework-agentico/agents/presets/maestro-platform/`
- Movimientos a legacy:
  - `docs/APP_HUESPED_SPEC.md` (v1) -> `legacy/v3/docs/APP_HUESPED_SPEC.md`
  - `docs/APP_HUESPED_BEST_PRACTICES.md` (v1) -> `legacy/v3/docs/APP_HUESPED_BEST_PRACTICES.md`
  - `docs/CONVENCIONES_PLATAFORMA.md` (v1) -> `legacy/v3/docs/CONVENCIONES_PLATAFORMA.md`
  - `framework-agentico/agents/presets/maestro-platform/` (v1) -> `legacy/v3/framework-agentico/agents/presets/maestro-platform/`
  - `PremisaWebMaestro/` (v1) -> `legacy/v3/PremisaWebMaestro/`
  - `arquitectura_actual.md` -> `legacy/v3/arquitectura_actual.md`
- Cada archivo movido a `legacy/v3/` recibio banner DEPRECADO con apuntador a su equivalente vigente y referencia al CHANGELOG.

### Notas operativas
- El cleanup del **PR #8** ("cleanup/template-restore", commit `ddc41fb`) borro el codigo de aplicacion del proyecto Maestro v1 historico que estaba en este repo (backend/, portal/, sdk/, docker/, tests/, docs/01-..06-*, framework-agentico/agents/{00..06}/CHECKPOINT.md). El framework, los templates, las premisas y los presets quedaron intactos.
- El **proyecto historico Maestro Platform v1** (preset `legacy/v3/.../maestro-platform`, premisa en `legacy/v3/PremisaWebMaestro/`, snapshot `legacy/v3/arquitectura_actual.md`) se conserva como referencia, marcado como legacy con banner DEPRECADO.
- **Apps v4 funcionan standalone** mientras la Web Maestro v2 no este desplegada. Cada deployment local se loguea con el superadmin sembrado por la fase 05 y opera sin necesidad del portal de la Web Maestro.

---

## Convencion de versionado

- Este repo no tiene un numero de version global propio: las versiones relevantes son las del **framework agentico** (`framework-agentico/CHANGELOG.md`) y las de cada **app huesped** (en su propio fork).
- Cambios mayores que afectan el contrato Maestro <-> App se documentan aqui y en `framework-agentico/CHANGELOG.md` simultaneamente.
- Formato basado en [Keep a Changelog](https://keepachangelog.com/en/1.1.0/).

---

## Documentos de referencia

- `framework-agentico/CHANGELOG.md` — cambios del framework agentico.
- `README.md` — guia general de desarrollo de apps huesped v4.
- `docs/APP_HUESPED_SPEC.md` — contrato normativo v2.
- `framework-agentico/migration/v3-to-v4.md` — proceso de migracion para apps v3 existentes.
