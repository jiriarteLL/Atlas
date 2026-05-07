# Checkpoint de Proyecto

> **Administrado por:** Project Manager (PM)
> **Ultima actualizacion:** {fecha}

---

```yaml
project_id: "{project-id}"           # nombre del repositorio de GitHub
repo_url: "{repo-url}"
premise: null
status: "not_started"                 # not_started | in_progress | interrupted | completed

# --- Tipo de proyecto y preset activo ---
# Confirmado por el PM al iniciar el proyecto (ver core/RULES.md seccion activacion_de_preset).
# Default: app huesped + preset web-maestro. Cambiar a web_maestro/maestro-platform si el PO indica que construye la Web Maestro misma.
project_type: "app_huesped"          # app_huesped | web_maestro
preset_active: "web-maestro"         # web-maestro | maestro-platform

created_at: "{fecha}"
updated_at: "{fecha}"
iteration: 0

# --- Stack ---
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
  - "05-seeding"
  - "06-operations"
  - "07-retrospective"
skipped_phases: []

phases_status:
  00-setup: { status: "not_started", exit_criteria_met: false }
  01-discovery: { status: "not_started", exit_criteria_met: false }
  02-planning: { status: "not_started", exit_criteria_met: false }
  03-development: { status: "not_started", exit_criteria_met: false }
  04-delivery: { status: "not_started", exit_criteria_met: false }
  05-seeding: { status: "not_started", exit_criteria_met: false }
  06-operations: { status: "not_started", exit_criteria_met: false }
  07-retrospective: { status: "not_started", exit_criteria_met: false }

# --- Repositorio ---
repo:
  url: null
  is_fork: null
  issues_enabled: null
  upstream_branches: []
  tailwise_template: null
  tailwise_template_compatible: null

# --- Git ---
git:
  epic_branch: null
  milestones: []
  issues_open: 0
  issues_closed: 0
  prs_open: 0
  prs_merged: 0

# --- Ramas activas ---
active_branches:
  # Se completa dinamicamente. Ejemplo:
  # - { name: "epic/mi-app", type: "epic", path: "branches/epic_mi-app", status: "active" }
  # - { name: "epic/mi-app/modulo-auth", type: "issue", path: "branches/issue_modulo-auth", status: "active" }

# --- Decisiones ---
decisions_log: []

# --- Escalaciones ---
escalations_log: []

# --- Agentes dinamicos ---
agents_determined: []

# --- Costos (rollup de ramas) ---
cost_summary:
  license:
    type: "subscription"
    plan: "max-5x"
    monthly_cost_usd: 200.00
  totals:
    total_queries: 0
    total_agent_calls: 0
    total_pm_interactions: 0
    total_retries: 0
    total_transactions: 0
    total_tokens:
      input: 0
      output: 0
      cache_read: 0
      cache_creation: 0
      grand_total: 0
    total_cost_usd: 0.00
  by_branch: {}
    # Ejemplo:
    # epic_mi-app: { agent_calls: 10, tokens: 50000, cost_usd: 1.20 }
    # issue_modulo-auth: { agent_calls: 8, tokens: 30000, cost_usd: 0.80 }
  by_phase:
    00-setup: { agent_calls: 0, retries: 0, tokens: 0, cost_usd: 0.00 }
    01-discovery: { agent_calls: 0, retries: 0, tokens: 0, cost_usd: 0.00 }
    02-planning: { agent_calls: 0, retries: 0, tokens: 0, cost_usd: 0.00 }
    03-development: { agent_calls: 0, retries: 0, tokens: 0, cost_usd: 0.00 }
    04-delivery: { agent_calls: 0, retries: 0, tokens: 0, cost_usd: 0.00 }
    05-seeding: { agent_calls: 0, retries: 0, tokens: 0, cost_usd: 0.00 }
    06-operations: { agent_calls: 0, retries: 0, tokens: 0, cost_usd: 0.00 }
    07-retrospective: { agent_calls: 0, retries: 0, tokens: 0, cost_usd: 0.00 }
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
    cache_hit_rate: 0.0%
    tokens_per_loc: 0
    retry_cost_ratio: 0.0%
    pm_overhead_ratio: 0.0%
    avg_cost_per_module: 0.00
    avg_retries_per_module: 0.0
  cost_summary_path: "cost/SUMMARY.md"
```
