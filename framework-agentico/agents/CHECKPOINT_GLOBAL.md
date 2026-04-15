# Checkpoint Global

> **Administrado por:** Project Manager
> **Ultima actualizacion:** 2026-04-14

---

```yaml
project_id: "PRJ-0001"
repo_url: "local"
premise: "Pendiente de definir con el humano (Product Owner)"
status: "not_started"
preset_active: "none"
mode: "pendiente"

created_at: "2026-04-14"
updated_at: "2026-04-14"
iteration: 0

current_phase: "none"
completed_phases: []
pending_phases:
  - "00-setup"
  - "01-discovery"
  - "02-planning"
  - "03-development"
  - "04-delivery"
  - "05-operations"
  - "06-retrospective"
skipped_phases: []

stack_detected:
  language: "PHP 8.2"
  framework: "Laravel 11"
  database: "SQLite (default, pendiente definir)"
  frontend: "Vite 4 + TailwindCSS 3 + Vanilla JS (templates disponibles: Vue, React)"
  infra: "pendiente definir"

templates_disponibles:
  laravel: "Tailwise Bundle/Laravel Version - v1.0.3/Source/"
  react: "Tailwise Bundle/React Version - v1.0.9/"
  vue: "Tailwise Bundle/Tailwise Vue - v1.0.1/"
  html: "Tailwise Bundle/HTML Version - v1.0.1/"

decisions_log: []

escalations_log: []

phases_status:
  00-setup:
    status: "not_started"
    exit_criteria_met: false
    checkpoint_file: "00-setup/CHECKPOINT.md"
  01-discovery:
    status: "not_started"
    exit_criteria_met: false
    checkpoint_file: "01-discovery/CHECKPOINT.md"
  02-planning:
    status: "not_started"
    exit_criteria_met: false
    checkpoint_file: "02-planning/CHECKPOINT.md"
  03-development:
    status: "not_started"
    exit_criteria_met: false
    checkpoint_file: "03-development/CHECKPOINT.md"
  04-delivery:
    status: "not_started"
    exit_criteria_met: false
    checkpoint_file: "04-delivery/CHECKPOINT.md"
  05-operations:
    status: "not_started"
    exit_criteria_met: false
    checkpoint_file: "05-operations/CHECKPOINT.md"
  06-retrospective:
    status: "not_started"
    exit_criteria_met: false
    checkpoint_file: "06-retrospective/CHECKPOINT.md"
  transversal:
    status: "not_started"
    checkpoint_file: "transversal/CHECKPOINT.md"

cost_summary:
  license:
    type: "subscription"
    plan: "max-5x"
    monthly_cost_usd: 200.00
  budget:
    budget_usd: null
    consumed_usd: 0.00
    consumed_pct: 0.0%
    alert_level: "none"
  totals:
    total_queries: 0
    total_tokens:
      input: 0
      output: 0
      cache_read: 0
      cache_creation: 0
      grand_total: 0
    total_cost_usd: 0.00
  by_phase:
    00-setup: { queries: 0, tokens: 0, cost_usd: 0.00 }
    01-discovery: { queries: 0, tokens: 0, cost_usd: 0.00 }
    02-planning: { queries: 0, tokens: 0, cost_usd: 0.00 }
    03-development: { queries: 0, tokens: 0, cost_usd: 0.00 }
    04-delivery: { queries: 0, tokens: 0, cost_usd: 0.00 }
    05-operations: { queries: 0, tokens: 0, cost_usd: 0.00 }
    06-retrospective: { queries: 0, tokens: 0, cost_usd: 0.00 }
  efficiency:
    avg_tokens_per_response: 0
    avg_cost_per_response_usd: 0.00
    cache_hit_rate: 0.0%
    tokens_per_loc: 0
  cost_log: "transversal/docs/COST_LOG.md"
```

---

## Notas de Inicializacion

- Framework agentico configurado el 2026-04-14
- Stack base detectado del template Tailwise: Laravel 11, PHP 8.2, Vite 4, TailwindCSS 3
- Templates disponibles: Laravel, React, Vue, HTML
- Pendiente: definir premisa del proyecto, stack definitivo, y si se activa algun preset
- Para iniciar: invocar `/pm` y definir la premisa del proyecto
