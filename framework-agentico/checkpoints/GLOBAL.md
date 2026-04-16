# Checkpoint Global

> **Administrado por:** Project Manager (PM)
> **Ultima actualizacion:** 2026-04-16

---

```yaml
project_id: null
repo_url: null
premise: null
status: "not_started"       # not_started | in_progress | interrupted | completed
preset: "web-maestro"       # siempre activo

created_at: null
updated_at: "2026-04-16"
iteration: 0

# --- Stack (se define en discovery/planning) ---
stack:
  backend: null
  frontend: null
  database: null
  infra: null

# --- Fases ---
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

phases_status:
  00-setup:
    status: "not_started"
    exit_criteria_met: false
  01-discovery:
    status: "not_started"
    exit_criteria_met: false
  02-planning:
    status: "not_started"
    exit_criteria_met: false
  03-development:
    status: "not_started"
    exit_criteria_met: false
  04-delivery:
    status: "not_started"
    exit_criteria_met: false
  05-operations:
    status: "not_started"
    exit_criteria_met: false
  06-retrospective:
    status: "not_started"
    exit_criteria_met: false

# --- Git ---
git:
  epic_branch: null
  milestones: []
  issues_open: 0
  issues_closed: 0
  prs_open: 0
  prs_merged: 0

# --- Decisiones ---
decisions_log: []

# --- Escalaciones ---
escalations_log: []

# --- Agentes dinamicos determinados ---
agents_determined: []
# Se completa cuando el PM entiende el problema. Ejemplo:
# - { role: "backend-developer", focus: "Laravel API", model: "sonnet" }
# - { role: "frontend-developer", focus: "React UI", model: "sonnet" }

# --- Costos ---
cost_summary:
  license:
    type: "subscription"
    plan: "max-5x"
    monthly_cost_usd: 200.00
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
    cache_hit_rate: 0.0%
    tokens_per_loc: 0
  cost_log: "framework-agentico/cost/COST_LOG.md"
```

---

## Notas

- Framework v2 inicializado el 2026-04-16
- Arquitectura: PM persistente + Agent() calls reales
- Preset Web Maestro siempre activo
- Para iniciar proyecto: invocar `/pm`
