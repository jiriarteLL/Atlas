# Checkpoint Fase 05 — Operations

```yaml
status: "completed"
updated_at: "2026-04-18"
iteration: 10

exit_criteria:
  metrics_defined: true                   # MONITORING.md §2
  alerts_configured: true                 # prometheus/alerts/maestro.yml — 10 rules activas + 6 deuda TD-017
  runbook_documented: true                # RUNBOOK.md con 8 secciones + 7 runbooks específicos §6
  incident_protocol_defined: true         # INCIDENT_PLAYBOOK.md + POSTMORTEM_TEMPLATE.md
  tech_debt_documented: true              # TECH_DEBT.md — 35 items (0 CRITICAL, 8 HIGH, 14 MEDIUM, 13 LOW)
  logs_verified_no_sensitive_data: true   # MONITORING.md §5.3 reglas explícitas; audit_log va a DB no a logs

observability:
  metrics:
    - "container_cpu_usage_seconds_total"
    - "container_memory_working_set_bytes"
    - "container_network_receive_bytes_total"
    - "container_network_transmit_bytes_total"
    - "container_start_time_seconds"
    - "node_filesystem_avail_bytes"
    - "node_memory_MemAvailable_bytes"
    - "node_load5"
    - "node_cpu_seconds_total"
  metrics_app_pending_td015: true          # /metrics endpoint en Maestro API → deuda HIGH SLO 2026-06-30
  alerts:
    - { name: "MaestroContainerDown",      severity: "SEV1", for: "2m",  runbook: "RUNBOOK §6.1" }
    - { name: "MaestroContainerMemoryHigh", severity: "SEV2", for: "10m", runbook: "RUNBOOK §6.2" }
    - { name: "MaestroContainerCPUHigh",    severity: "SEV3", for: "15m", runbook: "RUNBOOK §6.3" }
    - { name: "MaestroContainerRestarting", severity: "SEV2", for: "15m", runbook: "RUNBOOK §6.4" }
    - { name: "HostDiskAlmostFull",         severity: "SEV1", for: "5m",  runbook: "RUNBOOK §6.5" }
    - { name: "HostDiskGrowthFast",         severity: "SEV3", for: "30m", runbook: "RUNBOOK §6.5" }
    - { name: "HostMemoryHigh",             severity: "SEV2", for: "10m", runbook: "RUNBOOK §6.6" }
    - { name: "HostLoadHigh",               severity: "SEV3", for: "15m", runbook: "RUNBOOK §6.3" }
    - { name: "PrometheusTargetDown",       severity: "SEV2", for: "5m",  runbook: "RUNBOOK §6.7" }
    - { name: "MaestroAPIMetricsMissing",   severity: "SEV3", for: "1h",  runbook: "—" }
  dashboards:
    - "Maestro Overview (maestro-overview.json) — provisionado"
  log_format: "line-based Laravel default (TD-011: migrar a JSON)"
  tracing_configured: false               # Fuera de alcance V1 (DEC-020)

incidents:
  severity_levels_defined: true           # SEV1-4 en INCIDENT_PLAYBOOK §1
  response_times_targets:
    SEV1: "≤ 15 min respuesta / ≤ 2 h resolución"
    SEV2: "≤ 1 h respuesta / ≤ 8 h resolución"
    SEV3: "≤ 4 h laborales respuesta / ≤ 3 días resolución"
    SEV4: "≤ 24 h laborales respuesta / backlog"
  escalation_paths:
    - "Técnico: operador humano → Claude Code con CLAUDE.md + RUNBOOK.md"
    - "Seguridad: brecha confirmada → legal + compliance ANTES de tocar"
    - "Infra Azure: soporte del proveedor VPS (DEC-011)"
  communication_channels:
    - "Alerta automatizada Grafana Contact Point (email al humano)"
    - "docs/05-operations/INCIDENTS/ como log persistente"
    - "Commit messages para cambios derivados"
    - "Postmortem documentado en /INCIDENTS/"
  postmortem_template: true               # templates/POSTMORTEM_TEMPLATE.md
  postmortem_mandatory_for: ["SEV1", "SEV2"]
  postmortem_publication_deadline: "72h desde cierre"

tech_debt:
  source: "docs/05-operations/TECH_DEBT.md"
  total_items: 35
  critical_items: 0
  high_items: 8                           # TD-001, TD-002, TD-003, TD-007, TD-015, TD-017, TD-019, TD-020
  medium_items: 14
  low_items: 13
  highlights:
    - "TD-015 endpoint /metrics app — bloquea alertas de negocio (SLO ForwardAuth p95)"
    - "TD-017 alertas de negocio (6 reglas) — bloqueadas por TD-015"
    - "TD-001/TD-002 endpoints GDPR self-service — compliance"
    - "TD-007 evidencia formal SOC 2 Type II"
    - "TD-019/TD-020 E2E tests login + OAuth Microsoft"

transversal_validation:
  code_reviewer:        "APROBADO"
  security_auditor:     "APROBADO CON OBSERVACIONES — permisos backup 0600 aplicado inline; resto → TECH_DEBT"
  compliance_analyst:   "APROBADO — GDPR/SOC2/CIS/ASVS L2 alineados; gaps ya trackeados como TD-###"
  performance_analyst:  "APROBADO — cardinalidad y retención saludables; TD-015 priorizado HIGH"
  qa_tester:            "APROBADO — runbooks 1-a-1 con alertas; E2E trackeados TD-019 a TD-023"
  documentation_writer: "APROBADO — referencias cruzadas consistentes"
  veredicto_final:      "APROBADO CON OBSERVACIONES"
  report: "docs/05-operations/TRANSVERSAL_VALIDATION.md"

deliverables:
  - "docs/05-operations/MONITORING.md"
  - "docs/05-operations/INCIDENT_PLAYBOOK.md"
  - "docs/05-operations/RUNBOOK.md"
  - "docs/05-operations/TECH_DEBT.md"
  - "docs/05-operations/TRANSVERSAL_VALIDATION.md"
  - "docs/05-operations/templates/POSTMORTEM_TEMPLATE.md"
  - "docker/observability/prometheus/alerts/maestro.yml"
  - "docker/observability/prometheus/prometheus.yml (rule_files activado)"
  - "docker-compose.obs.yml (montaje alerts)"
  - "docker/php/Dockerfile (fix healthcheck IPv6)"
  - "docker/portal/Dockerfile (fix healthcheck IPv6)"

handoff_al_PM: |
  Iteración 10 CIERRA Fase 05 Operations. Exit criteria 6/6 cumplidos:
   ✓ Métricas definidas (9 infra + 4 host, 10 app pendientes por TD-015)
   ✓ Alertas configuradas (10 reglas activas cargadas por Prometheus)
   ✓ Runbook operativo (RUNBOOK.md con 7 runbooks específicos §6.1-§6.7)
   ✓ Protocolo de incidentes (INCIDENT_PLAYBOOK.md + POSTMORTEM_TEMPLATE.md)
   ✓ Deuda técnica documentada (TECH_DEBT.md con 35 items, 0 CRITICAL, 8 HIGH priorizadas ≤ 2026-Q3)
   ✓ Logs sin datos sensibles (MONITORING §5.3 reglas explícitas)

  Fix aplicado en iter 10: Dockerfiles healthcheck cambiado de localhost a 127.0.0.1
  (localhost resolvía a ::1 IPv6 en alpine y marcaba "unhealthy" falsamente).

  Validación transversal 6/6 APROBADO CON OBSERVACIONES (0 bloqueantes).

  Siguiente: Fase 06 Retrospective — memory-updater + executive-reporter + cost-analyst
  para cierre total del proyecto V1.
```
