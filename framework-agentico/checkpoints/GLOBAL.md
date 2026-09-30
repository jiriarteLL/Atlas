# Indice Global de Proyectos

> **Administrado por:** Project Manager (PM)
> **Ultima actualizacion:** 2026-05-06
> **Nota:** Este archivo es un INDICE. El estado detallado de cada proyecto esta en su PROJECT.md.

---

```yaml
framework_version: "4.0"
default_preset: "web-maestro"           # default sugerido para proyectos nuevos. Cada proyecto declara su preset_active en su PROJECT.md (ver core/RULES.md seccion activacion_de_preset).

# --- Proyecto activo ---
# Solo un proyecto puede estar in_progress a la vez (restriccion single-PM)
active_project: null                    # project-id del proyecto activo, o null

# --- Lista de proyectos ---
projects: []
  # Ejemplo:
  # - project_id: "mi-app-web"
  #   repo_url: "https://github.com/org/mi-app-web"
  #   status: "in_progress"             # not_started | in_progress | interrupted | completed
  #   current_phase: "03-development"
  #   path: "framework-agentico/projects/mi-app-web/PROJECT.md"
  #   total_cost_usd: 12.50
  #   created_at: "2026-04-23"
  #   updated_at: "2026-04-23"
  #
  # - project_id: "otro-proyecto"
  #   repo_url: "https://github.com/org/otro-proyecto"
  #   status: "completed"
  #   current_phase: "completed"
  #   path: "framework-agentico/projects/otro-proyecto/PROJECT.md"
  #   total_cost_usd: 8.30
  #   created_at: "2026-04-20"
  #   updated_at: "2026-04-22"

# --- Costos globales (suma de todos los proyectos) ---
global_cost:
  total_projects: 0
  total_cost_usd: 0.00
  by_project: {}
    # Ejemplo:
    # mi-app-web: { cost_usd: 12.50, status: "in_progress" }
    # otro-proyecto: { cost_usd: 8.30, status: "completed" }
```

---

## Notas

- Framework v4 — single-tenant + auth propio por app + fase de seeding (ver CHANGELOG.md)
- Cada proyecto tiene su estado en projects/{project-id}/PROJECT.md
- Costos se registran por rama, se agregan por proyecto, se indexan aqui
- Templates en core/templates/
- Preset Web Maestro siempre activo
- Para iniciar proyecto: invocar `/pm`
- Migracion lazy v3 -> v4: ver framework-agentico/migration/v3-to-v4.md
