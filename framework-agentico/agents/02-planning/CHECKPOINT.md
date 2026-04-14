# Checkpoint Fase 02 — Planning

```yaml
status: "not_started | in_progress | completed"
updated_at: ""

exit_criteria:
  stack_defined: false
  stack_propagated: false
  architecture_documented: false
  adrs_created: false
  data_model_designed: false
  api_contracts_defined: false
  ux_flows_documented: false
  threat_model_reviewed: false
  coherence_validated: false
  maestro_yaml_validated: false  # solo si preset web-maestro

stack:
  language: ""
  framework: ""
  database: ""
  frontend_framework: ""
  orm: ""
  test_framework: ""
  containerization: ""

architecture:
  pattern: ""
  components: []
  adrs: []

data_model:
  entities: []
  relationships: []
  migration_strategy: ""

api_contracts:
  endpoints_count: 0
  versioning_strategy: ""
  auth_strategy: ""

ux:
  user_flows: []
  design_system: ""

security:
  threat_model_status: ""
  risks_identified: []

escalations:
  - question: ""
    asked_by: ""
    answer: ""
    timestamp: ""
```
