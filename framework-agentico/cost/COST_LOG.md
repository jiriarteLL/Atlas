# Cost Log — Referencia

> **Este archivo ya no contiene datos de costos directamente.**

A partir del framework v3, los registros de costos se almacenan por rama dentro de cada proyecto:

```
projects/{project-id}/branches/{branch}/cost/COST_LOG.md   — costos por rama
projects/{project-id}/cost/SUMMARY.md                       — rollup por proyecto
checkpoints/GLOBAL.md                                       — indice global
```

## Templates

Los templates para instanciar logs de costos estan en:
- `core/templates/COST_LOG_TEMPLATE.md` — template para COST_LOG por rama
- `core/templates/COST_SUMMARY_TEMPLATE.md` — template para SUMMARY por proyecto

## Referencia de precios

La tabla de precios sigue en este directorio:
- `cost/PRICING.md` — referencia global, no se duplica por proyecto
