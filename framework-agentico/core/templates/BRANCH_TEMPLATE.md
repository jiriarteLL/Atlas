# Estado de Rama

> **Administrado por:** Orquestador de fase / PM
> **Ultima actualizacion:** {fecha}

---

```yaml
branch:
  name: "{branch-name}"               # ej: "epic/mi-app" o "epic/mi-app/modulo-auth"
  sanitized_name: "{sanitized}"        # ej: "epic_mi-app" o "issue_modulo-auth"
  type: "epic | issue | worktree"
  project_id: "{project-id}"
  parent_branch: null                  # rama padre (ej: epic para un issue branch)

  status: "active"                     # active | merged | abandoned
  created_at: "{fecha}"
  updated_at: "{fecha}"
  created_by: "pm | orchestrator"

  # --- Fase actual en esta rama ---
  current_phase: null
  phases_worked: []                    # fases que tuvieron actividad en esta rama

  # --- Agentes que trabajaron en esta rama ---
  agents_active: []
  # Ejemplo:
  # - { role: "backend-developer", model: "sonnet", module: "modulo-auth" }

  # --- Transacciones ---
  transaction_count: 0
  last_transaction_id: null

  # --- Costos de esta rama ---
  cost:
    total_agent_calls: 0
    total_retries: 0
    total_transactions: 0
    total_tokens: 0
    total_cost_usd: 0.00
    cost_log_path: "cost/COST_LOG.md"

  # --- Git state ---
  git:
    issues_associated: []              # numeros de issues de GitHub
    prs_created: []
    merged_to: null                    # rama destino del merge
    merge_date: null
```
