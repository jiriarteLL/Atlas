# Cost Log — Rama: {branch-name}

> **Administrado por:** cost-analyst (Agent, haiku) + PM (interacciones propias)
> **Proyecto:** {project-id}
> **Rama:** {branch-name}

---

## 1. Interacciones PM en esta rama

| timestamp | tipo | estimated_output_chars | estimated_tokens | costo_usd |
|-----------|------|----------------------|-----------------|-----------|

<!-- Tipos: query, estado, reporte, orquestar, planificar, ad_hoc -->

---

## 2. Entradas por Agente

| timestamp | fase | rol | modelo | modulo | intento | is_retry | files_read | files_written | loc | est_output_chars | est_input_tokens | est_output_tokens | costo_usd | txn_id |
|-----------|------|-----|--------|--------|---------|----------|------------|---------------|-----|-----------------|-----------------|------------------|-----------|--------|

<!-- txn_id vincula cada entrada con su archivo de transaccion -->

---

## 3. Tracking de Reintentos

| fase | modulo | total_intentos | intento | developer_model | developer_chars | validator_bloqueante | razon_bloqueo | model_escalated | agent_calls_intento | costo_intento_usd |
|------|--------|---------------|---------|----------------|----------------|---------------------|--------------|----------------|--------------------|--------------------|

---

## 4. Totales de Rama

```yaml
branch_totals:
  branch: "{branch-name}"
  total_agent_calls: 0
  total_pm_interactions: 0
  total_retries: 0
  total_transactions: 0
  tokens:
    input: 0
    output: 0
    grand_total: 0
  total_cost_usd: 0.00
  by_phase: {}
  by_role:
    orchestration: { calls: 0, tokens: 0, cost_usd: 0.00 }
    development: { calls: 0, tokens: 0, cost_usd: 0.00 }
    validation: { calls: 0, tokens: 0, cost_usd: 0.00 }
    documentation: { calls: 0, tokens: 0, cost_usd: 0.00 }
    cost_analysis: { calls: 0, tokens: 0, cost_usd: 0.00 }
    pm_interactions: { calls: 0, tokens: 0, cost_usd: 0.00 }
  by_model:
    opus: { calls: 0, tokens: 0, cost_usd: 0.00 }
    sonnet: { calls: 0, tokens: 0, cost_usd: 0.00 }
    haiku: { calls: 0, tokens: 0, cost_usd: 0.00 }
  efficiency:
    avg_tokens_per_response: 0
    retry_cost_ratio: 0.0%
```
