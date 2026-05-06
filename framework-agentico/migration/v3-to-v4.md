# Migracion v3 -> v4

> **Estado:** Activa para v4.0
> **Aplica a:** apps huesped que usen el framework v3 (o cualquier version anterior).

---

## Resumen del cambio

v4.0 introduce un cambio incompatible en el contrato de auth y tenancy entre el Maestro y las apps huesped:

| Aspecto | v3 | v4 |
|---|---|---|
| Tenancy | Multi-tenant con `company_id` | Single-tenant fisico (un contenedor por empresa) |
| Auth | Headers `X-Auth-*` inyectados por el Maestro | Login propio de la app (users + roles + permissions + tokens propios) |
| Tabla `users` | Prohibida | Obligatoria |
| Maestro -> App (usuario) | Inyecta headers de identidad y maneja sesion | Solo redirige (`target="_blank"`) y consume `/maestro/branding` |
| Maestro -> App (server) | `X-Maestro-Webhook-Secret` para hooks | + `X-Maestro-Api-Key` para `/maestro/branding` |
| `maestro.yaml` | hooks + recursos | + `auth_model: own`, `login_path`, `branding_url` |
| Fases | 7 fases (00-06) | 8 fases (00-07): nueva `05-seeding`, `05-operations` -> `06-operations`, `06-retrospective` -> `07-retrospective` |
| Superadmin | N/A | `admin@llyasoc.com` creado por seed idempotente, password desde `SUPERADMIN_INITIAL_PASSWORD` |

Detalle completo en `framework-agentico/CHANGELOG.md`.

---

## Quien activa la migracion

La migracion es **lazy**:

- Cuando el Project Owner ejecuta `/pm` en un fork del repo template, el PM detecta `framework_version` desactualizada en `framework-agentico/checkpoints/GLOBAL.md`.
- El PM informa la version detectada y la version target.
- El PM ofrece sincronizar el fork con upstream (modo **hibrido**: el PO autoriza y el PM ejecuta `git fetch + merge`, o el PO lo hace manual).
- Si el PO acepta, el PM ejecuta el flujo de migracion.

Aplicable a CUALQUIER version anterior a v4 (v1, v2, v3, etc.).

---

## Pasos de la migracion

### Paso 1 — Sincronizar el fork con upstream

El PO ejecuta (o autoriza al PM a ejecutar):

```bash
git fetch upstream
git merge upstream/master      # o el nombre de la main branch del upstream
```

Esto trae los archivos actualizados del framework v4 al fork. **No toca codigo de la app.**

> Si el repo NO tiene remote `upstream` configurado, agregalo:
> ```bash
> git remote add upstream https://github.com/{org}/tailwise_laravel_vue_react_template.git
> ```

### Paso 2 — Detectar version post-sync

El PM relee `framework-agentico/checkpoints/GLOBAL.md`. Si `framework_version` ahora es `"4.0"`, se procede al paso 3.

### Paso 3 — Lanzar Agent(framework-migrator, opus)

El PM lanza:

```
Agent({
  description: "Framework migrator v{old} -> v4",
  model: "opus",
  prompt: "Sos el framework-migrator. Lee framework-agentico/migration/migrator-template.md
  y ejecuta la migracion. NO modifiques codigo de la app. Genera reporte de gaps."
})
```

### Paso 4 — Reporte de gaps

El migrator genera un reporte con los gaps detectados en el codigo de la app:

- Middleware de auth que lee headers `X-Auth-*` (deprecado en v4).
- Filtros por `company_id` en queries (no aplican en single-tenant).
- Falta de tabla `users` / `roles` / `permissions`.
- Falta de endpoint `/maestro/branding` con middleware de api key.
- Falta del seeder del superadmin (`admin@llyasoc.com`).
- ENV vars faltantes en `.env.example` (`MAESTRO_API_KEY`, `SUPERADMIN_INITIAL_PASSWORD`).
- Numeracion de fases desactualizada en `projects/{id}/PROJECT.md` (si aplica).
- `maestro.yaml` sin campos `auth_model`, `login_path`, `branding_url`.

Reporte guardado en `framework-agentico/migration/reports/v3-to-v4-{project-id}-{date}.md`.

### Paso 5 — Decision del PO

El PO revisa el reporte y decide:

- **Resolver gaps ahora**: abrir un nuevo trabajo (issue/branch). El PM coordina las fases necesarias para corregir.
- **Resolver gaps mas adelante**: queda registrado en el reporte; el PM advierte que la app NO esta en compliance v4 hasta resolverse y solo permite operar en modo solo-lectura.

---

## Que NO hace la migracion

- **NO toca codigo de la app**. Solo actualiza archivos del framework.
- **NO borra `projects/`**. El estado del proyecto local se preserva.
- **NO hace force push** ni reescribe historia git.
- **NO despliega** la app actualizada. El deploy es responsabilidad del flujo normal de `04-delivery`.

## Que SI hace la migracion

- Actualiza `framework-agentico/` con los archivos v4 (via sync con upstream).
- Actualiza la numeracion de fases en `projects/{id}/PROJECT.md` (si la app tiene proyecto activo: `05-operations` -> `06-operations`, `06-retrospective` -> `07-retrospective`, agrega `05-seeding` como `pending`).
- Confirma `framework_version: "4.0"` en `checkpoints/GLOBAL.md`.
- Registra `migration_history` en `PROJECT.md` con: `from_version`, `to_version`, `date`, `sync_method`.
- Genera el reporte de gaps en `framework-agentico/migration/reports/`.

---

## Revertir la migracion

Si el PO decide revertir, ejecuta:

```bash
git reset --hard HEAD~1     # si la migracion fue el ultimo commit
```

O restaura desde el branch anterior al sync. Dado que la migracion no toca codigo de la app, revertir solo afecta a los archivos del framework.

---

## Ver tambien

- `framework-agentico/CHANGELOG.md` — cambios v3 -> v4
- `framework-agentico/migration/migrator-template.md` — template del Agent migrator
- `framework-agentico/core/RULES.md` seccion 15 — reglas de migracion
- `framework-agentico/core/PRESET_WEB_MAESTRO.md` — preset v4 vigente
