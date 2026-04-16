# Cost Log — Registro de Consumo

> **Administrado por:** cost-analyst (Agent, haiku)
> **Actualizado:** despues de cada fase

---

## Formato de Registro

Cada entrada sigue esta estructura:

| timestamp | sesion | fase | modelo | input | output | cache_read | cache_create | total_tokens | costo_usd |
|-----------|--------|------|--------|-------|--------|------------|--------------|-------------|-----------|

---

## Registro

(Vacio — se completa al ejecutar el primer proyecto)

---

## Metricas Acumuladas

```yaml
totals:
  queries: 0
  input_tokens: 0
  output_tokens: 0
  cache_read_tokens: 0
  cache_creation_tokens: 0
  grand_total_tokens: 0
  estimated_cost_usd: 0.00

efficiency:
  avg_tokens_per_response: 0
  cache_hit_rate: 0.0%
  tokens_per_loc: 0
  output_input_ratio: 0
```
