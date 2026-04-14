# Reglas Fase 01 — Discovery

```yaml
reglas:
  - no tomar decisiones técnicas en esta fase (eso es fase 02)
  - todo requisito debe tener al menos un criterio de aceptación testeable
  - la priorización MoSCoW la valida el humano, nunca los agentes
  - el glosario de dominio debe contener todos los términos que usarán los agentes posteriores
  - los requisitos no funcionales deben ser cuantificables (no "rápido" sino "respuesta < 200ms")
  - si hay ambigüedad en un requisito, preguntar antes de asumir
  - documentar explícitamente qué NO está en el alcance de esta versión

si_preset_web_maestro:
  - incorporar como requisitos no funcionales obligatorios:
    - auth por headers HTTP (no login propio)
    - aislamiento de datos por company_id
    - health check en /health
    - compatibilidad con maestro.yaml
    - restricciones de recursos (memory, cpu)
  - investigar estado de la plataforma via /api/inventory/context
  - identificar apps del mismo stack como referencia
```
