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
```
