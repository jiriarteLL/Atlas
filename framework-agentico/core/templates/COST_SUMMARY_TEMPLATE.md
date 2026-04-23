# Cost Summary — Proyecto: {project-id}

> **Administrado por:** cost-analyst (Agent, haiku)
> **Actualizado:** despues de cada fase (rollup de ramas)

---

```yaml
project_cost:
  project_id: "{project-id}"
  total_cost_usd: 0.00
  total_agent_calls: 0
  total_pm_interactions: 0
  total_retries: 0
  total_transactions: 0

  # --- Desglose por rama ---
  by_branch: {}
    # Ejemplo:
    # epic_mi-app:
    #   total_cost_usd: 10.20
    #   agent_calls: 15
    #   retries: 2
    #   transactions: 22
    #   cost_log: "branches/epic_mi-app/cost/COST_LOG.md"
    # issue_modulo-auth:
    #   total_cost_usd: 2.30
    #   agent_calls: 8
    #   retries: 1
    #   transactions: 12
    #   cost_log: "branches/issue_modulo-auth/cost/COST_LOG.md"

  # --- Desglose por fase (sumado de todas las ramas) ---
  by_phase:
    00-setup: { cost_usd: 0.00, retries: 0 }
    01-discovery: { cost_usd: 0.00, retries: 0 }
    02-planning: { cost_usd: 0.00, retries: 0 }
    03-development: { cost_usd: 0.00, retries: 0 }
    04-delivery: { cost_usd: 0.00, retries: 0 }
    05-operations: { cost_usd: 0.00, retries: 0 }
    06-retrospective: { cost_usd: 0.00, retries: 0 }

  # --- Desglose por modelo (sumado de todas las ramas) ---
  by_model:
    opus: { calls: 0, tokens: 0, cost_usd: 0.00 }
    sonnet: { calls: 0, tokens: 0, cost_usd: 0.00 }
    haiku: { calls: 0, tokens: 0, cost_usd: 0.00 }

  # --- Desglose por rol (sumado de todas las ramas) ---
  by_role:
    orchestration: { calls: 0, tokens: 0, cost_usd: 0.00 }
    development: { calls: 0, tokens: 0, cost_usd: 0.00 }
    validation: { calls: 0, tokens: 0, cost_usd: 0.00 }
    documentation: { calls: 0, tokens: 0, cost_usd: 0.00 }
    cost_analysis: { calls: 0, tokens: 0, cost_usd: 0.00 }
    pm_interactions: { calls: 0, tokens: 0, cost_usd: 0.00 }

  # --- Eficiencia global ---
  efficiency:
    avg_tokens_per_response: 0
    tokens_per_loc: 0
    retry_cost_ratio: 0.0%
    pm_overhead_ratio: 0.0%
    avg_cost_per_module: 0.00
    most_expensive_branch: null
    most_expensive_phase: null
```

---

## Compactacion

Al cerrar el proyecto:
1. El cost-analyst (haiku) lee TODOS los COST_LOG.md de cada rama y genera este SUMMARY.md con los totales finales.
2. El transaction-compactor (haiku, agente separado) compacta las transacciones (ver RULES.md seccion memorias_transaccionales.compactacion).
3. Ambos son lanzados por el PM como parte del cierre de proyecto.
