# Cost Log

> **Administrado por:** cost-analyst  
> **Actualizado:** Despues de cada fase o bajo demanda

---

## Pricing Vigente

```yaml
pricing_version: "2026-04-15"
model: "claude-opus-4-6"
license_type: "subscription"  # API | subscription
subscription_plan: "max-5x"   # solo si license_type = subscription
subscription_cost_monthly_usd: 200.00

# Precios por millon de tokens (usados para calculo de costo equivalente API)
rates_per_million_tokens:
  input: 15.00
  output: 75.00
  cache_read: 1.50
  cache_creation: 18.75

# Historial de cambios de pricing
pricing_history:
  - version: "2026-04-15"
    model: "claude-opus-4-6"
    rates: { input: 15.00, output: 75.00, cache_read: 1.50, cache_creation: 18.75 }
    nota: "Pricing inicial del proyecto"
```

---

## Registro por Consulta

> Cada fila representa una respuesta del asistente. Los tokens se registran en valores absolutos.  
> El costo USD se calcula con el pricing vigente al momento del registro.

### Sesion: (pendiente)

| # | Timestamp | Fase | Input | Output | Cache Read | Cache Create | Total Tokens | Costo USD |
|---|-----------|------|-------|--------|------------|--------------|--------------|-----------|
| — | — | — | — | — | — | — | — | — |

---

## Acumulado por Fase

| Fase | Consultas | Input | Output | Cache Read | Cache Create | Total Tokens | Costo USD | Tokens/Respuesta | Cache Hit Rate |
|------|-----------|-------|--------|------------|--------------|--------------|-----------|------------------|----------------|
| 00-setup | 0 | 0 | 0 | 0 | 0 | 0 | $0.00 | 0 | 0% |
| 01-discovery | 0 | 0 | 0 | 0 | 0 | 0 | $0.00 | 0 | 0% |
| 02-planning | 0 | 0 | 0 | 0 | 0 | 0 | $0.00 | 0 | 0% |
| 03-development | 0 | 0 | 0 | 0 | 0 | 0 | $0.00 | 0 | 0% |
| 04-delivery | 0 | 0 | 0 | 0 | 0 | 0 | $0.00 | 0 | 0% |
| 05-operations | 0 | 0 | 0 | 0 | 0 | 0 | $0.00 | 0 | 0% |
| 06-retrospective | 0 | 0 | 0 | 0 | 0 | 0 | $0.00 | 0 | 0% |
| **TOTAL** | **0** | **0** | **0** | **0** | **0** | **0** | **$0.00** | **0** | **0%** |

---

## Acumulado por Proyecto

```yaml
project_id: "PRJ-0001"
total_queries: 0
total_tokens:
  input: 0
  output: 0
  cache_read: 0
  cache_creation: 0
  grand_total: 0
total_cost_usd: 0.00
efficiency:
  avg_tokens_per_response: 0
  avg_cost_per_response_usd: 0.00
  cache_hit_rate: 0.0%
  output_input_ratio: 0.0
  tokens_per_loc: 0      # se calcula cuando haya datos de git
budget:
  budget_usd: null        # definido por el humano
  consumed_usd: 0.00
  consumed_pct: 0.0%
  alert_level: "none"     # none | info_60 | warning_80 | critical_95 | exceeded_100
```

---

## Notas

- Los costos USD son equivalentes API, calculados con el pricing vigente al momento del registro.
- Si la licencia cambia de precio, se agrega una entrada en pricing_history y los registros futuros usan el nuevo pricing.
- Los registros historicos NO se recalculan.
- Para licencias de suscripcion, el costo USD permite comparar si el plan fijo es mas rentable que pagar por token.
