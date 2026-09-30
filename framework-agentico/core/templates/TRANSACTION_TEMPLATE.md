# Transaccion — {id}

> **Inmutable:** Una vez escrito, este archivo NO se modifica.
> Si hay correccion, se crea una nueva transaccion con referencia a esta.

---

```yaml
transaction:
  id: "{TXN-timestamp-seq}"             # ej: TXN-20260423T143022-001
  project_id: "{project-id}"
  branch: "{branch-name}"
  phase: "{NN-nombre}"
  
  # --- Actor ---
  agent:
    role: "{rol}"                        # backend-developer, security-auditor, orchestrator, pm, cost-analyst, etc.
    model: "{modelo}"                    # opus, sonnet, haiku
  
  # --- Operacion ---
  operation:
    type: "{tipo}"                       # development | validation | retry | escalation | pm_interaction | cost_analysis | documentation | orchestration
    name: "{nombre-operacion}"           # ej: dev-attempt-1, validation-run-2, pm-query
    module: "{modulo}"                   # issue/modulo asociado (null si no aplica)
    attempt: 1                           # numero de intento (1 = primera vez)
    is_retry: false
    retry_reason: null                   # motivo del fallo anterior si es retry
    model_escalated: false               # true si el modelo fue escalado por retry
  
  # --- Entrada ---
  input:
    files_read: []                       # lista de archivos leidos
    context_source: "{descripcion}"      # de donde vino el contexto (Context Packet, PM, etc.)
  
  # --- Salida ---
  output:
    files_written: []                    # lista de archivos escritos/modificados
    lines_of_code: 0                     # LOC producidos (0 si no aplica)
    result: "{resultado}"                # completed | failed | blocked | escalated | pass | fail
    verdict: null                        # para validadores: PASS | FAIL | N/A
    observations: null                   # notas del agente sobre la operacion
  
  # --- Costo ---
  cost:
    estimated_output_chars: 0
    estimated_input_tokens: 0            # files_read * 500
    estimated_output_tokens: 0           # estimated_output_chars / 4
    estimated_cost_usd: 0.00
  
  # --- Trazabilidad ---
  trace:
    timestamp_start: "{ISO-8601}"
    timestamp_end: "{ISO-8601}"
    triggered_by: "{quien-lanzo-este-agente}"   # orchestrator-fase-03, pm, etc.
    parent_transaction: null             # TXN-id de la transaccion que origino esta
    next_action: null                    # que deberia pasar despues (informativo)
    correction_of: null                  # si corrige otra TXN, referencia aqui
```
