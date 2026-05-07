# CHANGELOG — Repo Plataforma Maestro Template

> Cambios del **repo template** (este repositorio). Para cambios del **framework agentico** ver `framework-agentico/CHANGELOG.md`.

---

## [Unreleased] / 2026-05-07

### Added
- Framework agentico **v4.0** (ver `framework-agentico/CHANGELOG.md` para detalle).
- Contrato **`maestro.platform/v2`** documentado en:
  - `docs/APP_HUESPED_SPEC_V2.md`
  - `docs/APP_HUESPED_BEST_PRACTICES_V2.md`
  - `docs/CONVENCIONES_PLATAFORMA_V2.md`
  - `docs/schemas/maestro.yaml.schema.v2.json` (nuevo schema v2)
- Preset `framework-agentico/agents/presets/maestro-platform-v2/` (lado servidor del contrato v2 — para construir un Maestro v2 en proyecto separado).
- Sistema de **migracion lazy** v3 -> v4 (`framework-agentico/migration/`).
- Nueva **fase 05-seeding** del ciclo agentico (superadmin `admin@llyasoc.com` idempotente).
- `cli/node/templates/node-express/CLAUDE.md` reescrito para v4.
- `cli/node/templates/node-express/maestro.yaml` reescrito a `apiVersion: maestro.platform/v2`.
- `cli/node/templates/node-express/package.json` reescrito sin `@maestro/sdk-node` (apps v4 son autocontenidas).
- `mock/README.md` documentando el directorio `mock/` como legacy v3.
- `.env.example` reescrito para v4 (sin `MOCK_*`; agrega `JWT_SECRET`, `MAESTRO_API_KEY`, `MAESTRO_WEBHOOK_SECRET`, `SUPERADMIN_INITIAL_PASSWORD`).
- `README.md` (este archivo) reescrito para reflejar el modelo v4.
- `.gitignore` (root) bumpeado con exclusiones robustas v4.

### Changed
- `framework-agentico/checkpoints/GLOBAL.md`: `framework_version: "4.0"`.
- `framework-agentico/core/RULES.md`: titulo "v4" + nueva seccion 15 (`migracion_entre_versiones`).
- `framework-agentico/core/PRESET_WEB_MAESTRO.md`: rewrite completo a modelo v4 (single-tenant + auth propia + branding endpoint + seeding).
- `framework-agentico/core/PM.md`: system prompt actualizado con flujo de migracion lazy y flow del seed interactivo.
- `framework-agentico/core/CONTEXT_PACKET.md`: version 4.0 + preset_constraints actualizados.
- `framework-agentico/core/templates/PROJECT_TEMPLATE.md` y `COST_SUMMARY_TEMPLATE.md`: lista de fases 00-07 (incluyendo `05-seeding`).
- `framework-agentico/phases/`: renumeracion (`05-operations` -> `06-operations`, `06-retrospective` -> `07-retrospective`) + nueva fase `05-seeding.md`.
- `framework-agentico/validation/validators/*`: validadores actualizados para modelo v4 (security exige tabla users + bcrypt; qa testea login propio + branding + seed; compliance valida password policy + audit log; performance sin filtros multi-tenant; code-reviewer y documentation-writer alineados a v4).
- `CLAUDE.md` (root): version 4.0.0 + arquitectura ASCII con fases 00-07 + seccion sobre migracion lazy.

### Deprecated
- Contrato `maestro.platform/v1` y modelo de auth por headers `X-Auth-*`. Apps existentes deben migrar a v2 (ver `framework-agentico/migration/v3-to-v4.md`).
- `docs/APP_HUESPED_SPEC.md` (v1) — superado por `docs/APP_HUESPED_SPEC_V2.md`.
- `docs/APP_HUESPED_BEST_PRACTICES.md` (v1) — superado por `docs/APP_HUESPED_BEST_PRACTICES_V2.md`.
- `docs/CONVENCIONES_PLATAFORMA.md` (v1) — superado por `docs/CONVENCIONES_PLATAFORMA_V2.md`.
- Directorio `mock/` (modelo v3) — ver `mock/README.md` para opciones (borrar / mantener legacy / re-propositar).
- `docs/schemas/maestro.yaml.schema.json` (v1) — sigue presente como referencia legacy. Apps nuevas usan `schema.v2.json`.

### Notas operativas
- El cleanup del **PR #8** ("cleanup/template-restore", commit `ddc41fb`) borro el codigo de aplicacion del proyecto Maestro v1 historico que estaba en este repo (backend/, portal/, sdk/, docker/, tests/, docs/01-..06-*, framework-agentico/agents/{00..06}/CHECKPOINT.md). El framework, los templates, las premisas y los presets quedaron intactos.
- El **proyecto historico Maestro Platform v1** (preset `maestro-platform`, premisa en `PremisaWebMaestro/`, snapshot `arquitectura_actual.md`) se conserva como referencia, marcado como legacy.
- **Apps v4 funcionan standalone** mientras el Maestro v2 no este desplegado. Cada deployment local se loguea con el superadmin sembrado por la fase 05 y opera sin necesidad del portal del Maestro.

---

## Convencion de versionado

- Este repo no tiene un numero de version global propio: las versiones relevantes son las del **framework agentico** (`framework-agentico/CHANGELOG.md`) y las de cada **app huesped** (en su propio fork).
- Cambios mayores que afectan el contrato Maestro <-> App se documentan aqui y en `framework-agentico/CHANGELOG.md` simultaneamente.
- Formato basado en [Keep a Changelog](https://keepachangelog.com/en/1.1.0/).

---

## Documentos de referencia

- `framework-agentico/CHANGELOG.md` — cambios del framework agentico.
- `README.md` — guia general de desarrollo de apps huesped v4.
- `docs/APP_HUESPED_SPEC_V2.md` — contrato normativo v2.
- `framework-agentico/migration/v3-to-v4.md` — proceso de migracion para apps v3 existentes.
