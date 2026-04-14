# Reglas Fase 05 — Operations

```yaml
reglas:
  - toda métrica debe tener un umbral de alerta definido
  - los logs deben ser estructurados (JSON recomendado)
  - los logs nunca deben contener datos sensibles (passwords, tokens, PII)
  - toda alerta crítica debe tener un runbook asociado
  - el protocolo de incidentes debe definir niveles de severidad y tiempos de respuesta
  - toda deuda técnica se documenta con severidad y plan de remediación
  - los postmortems son blameless y orientados a mejora sistémica

metricas_minimas:
  - latencia de endpoints (p50, p95, p99)
  - tasa de errores (4xx, 5xx)
  - uso de recursos (CPU, memoria, disco)
  - health check status
  - queries lentas (> umbral definido)

alertas_minimas:
  - health check falla
  - tasa de errores 5xx > umbral
  - latencia p95 > umbral
  - uso de memoria > 80%
  - disco > 85%

si_preset_web_maestro:
  - considerar que el Maestro tiene sus propios health checks
  - las alertas deben distinguir entre errores de la app y errores del Maestro
  - logs deben incluir company_id para filtrar por tenant
  - no loguear contenido de headers de auth
```
