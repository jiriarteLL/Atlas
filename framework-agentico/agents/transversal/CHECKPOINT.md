# Checkpoint Transversal

> **Administrado por:** Orquestador Transversal  
> **Actualización:** Después de cada intervención transversal

---

## Schema

```yaml
status: "active | idle"
last_intervention:
  requested_by: ""
  phase: ""
  artifact: ""
  timestamp: ""

interventions_log:
  - id: ""
    phase: ""
    requested_by: ""
    agents_activated: []
    verdict: "approved | rejected | approved_with_observations"
    observations: []
    blockers: []
    timestamp: ""

stack_propagated:
  language: ""
  framework: ""
  database: ""
  frontend: ""
  propagated_to: []

skills_suggested:
  - skill: ""
    reason: ""
    accepted: false
    timestamp: ""

documentation_generated:
  - phase: ""
    document: ""
    version: ""
    timestamp: ""

reports_generated:
  - type: "executive | consolidated | phase"
    requested_by: ""
    timestamp: ""

cost_metrics:
  last_updated: ""
  current_phase_consumption:
    phase: ""
    queries: 0
    tokens: { input: 0, output: 0, cache_read: 0, cache_creation: 0 }
    cost_usd: 0.00
    efficiency:
      tokens_per_response: 0
      cache_hit_rate: 0.0%
  project_accumulated:
    total_queries: 0
    total_tokens: 0
    total_cost_usd: 0.00
    avg_cost_per_query_usd: 0.00
  budget_status:
    budget_usd: null
    consumed_pct: 0.0%
    alert_level: "none"
  cost_log_file: "transversal/docs/COST_LOG.md"
```
