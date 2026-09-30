# Tabla de Precios — Modelos Claude

> **Ultima actualizacion:** 2026-04-16
> **Nota:** Si el pricing cambia, actualizar esta tabla. Costos historicos NO se recalculan.

---

## Precios Vigentes (API pricing, para estimacion)

```yaml
claude-opus-4:
  input: 15.00          # USD por 1M tokens
  output: 75.00          # USD por 1M tokens
  cache_read: 1.50       # USD por 1M tokens
  cache_creation: 18.75  # USD por 1M tokens

claude-sonnet-4:
  input: 3.00
  output: 15.00
  cache_read: 0.30
  cache_creation: 3.75

claude-haiku-4:
  input: 0.80
  output: 4.00
  cache_read: 0.08
  cache_creation: 1.00
```

---

## Licencia Actual

```yaml
license:
  type: "subscription"
  plan: "max-5x"
  monthly_cost_usd: 200.00
  nota: "Los costos USD calculados son equivalentes a API pricing. Utiles para comparar rentabilidad y decidir si el plan conviene."
```

---

## Mapping de Nombres

El framework usa nombres cortos para los modelos. Equivalencias:

```yaml
mapping:
  opus: "claude-opus-4"
  sonnet: "claude-sonnet-4"
  haiku: "claude-haiku-4"
```

El cost-analyst debe usar este mapping para calcular costos desde los agent_cost_report.

---

## Notas

- Los precios son de referencia para estimar consumo equivalente.
- Con suscripcion, no hay costo por token real, pero la estimacion permite:
  - Comparar rentabilidad del plan vs API directa
  - Estimar cuanto costaria escalar a API si se necesita
  - Identificar fases o agentes mas costosos para optimizar
