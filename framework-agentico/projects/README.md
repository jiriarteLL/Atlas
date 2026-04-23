# Projects — Directorio de Proyectos

> Cada subdirectorio es un proyecto gestionado por el framework.

## Estructura por Proyecto

```
projects/
  {project-id}/                        # nombre del repositorio de GitHub
    PROJECT.md                         # estado del proyecto (ex GLOBAL.md)
    cost/
      SUMMARY.md                       # costos agregados (rollup de ramas)
    branches/
      epic_{name}/
        BRANCH.md                      # estado de la rama
        cost/
          COST_LOG.md                  # costos de esta rama
        phases/
          {NN}-{name}.md               # artefactos de fase
        transactions/
          {timestamp}_{phase}_{agent}_{operation}.md
      issue_{module}/
        BRANCH.md
        cost/
          COST_LOG.md
        transactions/
          ...
```

## Convenciones

- **project-id**: nombre del repositorio de GitHub (ej: `mi-app-web`)
- **branch names**: se sanitizan reemplazando `/` por `_` (ej: `epic/mi-app` -> `epic_mi-app`)
- **transaction files**: inmutables una vez escritos, se compactan al cerrar el proyecto
- **PRICING.md** permanece en `cost/PRICING.md` (referencia global, no se duplica por proyecto)

## Templates

Los templates para crear la estructura estan en `framework-agentico/core/templates/`:
- `PROJECT_TEMPLATE.md` — checkpoint por proyecto
- `BRANCH_TEMPLATE.md` — estado por rama
- `TRANSACTION_TEMPLATE.md` — registro transaccional
- `COST_LOG_TEMPLATE.md` — log de costos por rama
- `COST_SUMMARY_TEMPLATE.md` — resumen de costos por proyecto
