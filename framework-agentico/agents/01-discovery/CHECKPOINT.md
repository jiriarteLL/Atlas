# Checkpoint Fase 01 — Discovery

```yaml
status: "completed"
updated_at: "2026-04-16"
completed_at: "2026-04-16"

exit_criteria:
  functional_requirements_documented: true         # 62 MUST + 4 SHOULD + 4 COULD + 13 WONT, ver REQUIREMENTS.md §3
  non_functional_requirements_documented: true    # 42 RNF cuantificados en REQUIREMENTS.md §4
  acceptance_criteria_defined: true                # todos los RF MUST tienen criterio de aceptacion testeable
  domain_glossary_complete: true                   # GLOSSARY.md con 70+ terminos
  regulations_identified: true                     # shortlist validada por humano; DEC-013 cierra ESC-002
  prioritization_validated_by_human: true          # VALIDADA 2026-04-16 via DEC-013 a DEC-021
  maestro_constraints_incorporated: true           # no-negociables de la premisa mapeados como MUST RF y RNF

research_findings:
  domain: "PaaS interno + IdP + Portal para usuarios finales. SaaS B2B multi-tenant."
  target_users:
    - "Empresas tenant (organizaciones cliente)"
    - "Usuarios finales (empleados de las empresas)"
    - "Desarrolladores de apps huesped"
    - "Administradores del Maestro"
    - "Direccion / C-Level"
  competitors:
    - "Heroku, Railway, Render, Fly.io, Vercel"
    - "AWS AppRunner, Azure Container Apps"
    - "Kubernetes + Keycloak + Istio"
    - "Okta + App Catalog"
    - "Portainer / Rancher"
  key_insights:
    - "El contrato maestro.yaml es el foso defensivo clave"
    - "ForwardAuth es cuello de botella critico; cache Redis necesario desde V1"
    - "Aislamiento multi-tenant doble (red + aplicacion)"
    - "Docker socket es la superficie de ataque mas sensible"
    - "Cold start y manejo visual son UX criticos"
    - "Microsoft Entra ID es canal de adquisicion clave"

risks_identified:
  - "R-001: Leak entre tenants (catastrofico)"
  - "R-002: Compromiso del Maestro da acceso al host (catastrofico)"
  - "R-003: Latencia ForwardAuth sin cache (alto)"
  - "R-004: Cold start >15s (medio)"
  - "R-005: Passport/OAuth2 config compleja (alto)"
  - "R-006: TLS no renueva (alto)"
  - "R-007: Compliance no identificado (medio) - ESC-002"
  - "R-008: VPS insuficiente para 50 concurrentes (medio)"
  - "R-009: Single-node no escala horizontal (medio)"
  - "R-010: Sistema agentico complejo (bajo)"

requirements_summary:
  total_requirements: 112
  functional:
    must_have: 62        # Epicas A-M
    should_have: 5       # RF-200 a RF-204
    could_have: 4        # RF-300 a RF-303
    wont_have: 8         # RF-900 a RF-907
  non_functional:
    performance: 8       # RNF-001 a RNF-008
    security: 11         # RNF-010 a RNF-020
    scalability: 5       # RNF-030 a RNF-034
    compatibility: 4     # RNF-040 a RNF-043
    usability: 4         # RNF-050 a RNF-053
    observability: 4     # RNF-060 a RNF-063
    compliance: 6        # RNF-070 a RNF-075

regulations_applicable:
  - regulation: "GDPR (Reglamento UE 2016/679)"
    impact: "Derecho al olvido, portabilidad, DPA, retencion definida"
    identified_by: "compliance-analyst"
    status: "PROPUESTO MUST — pendiente validacion humano"
  - regulation: "SOC 2 Type II (AICPA)"
    impact: "Controles de seguridad, disponibilidad, confidencialidad documentados"
    identified_by: "compliance-analyst"
    status: "PROPUESTO MUST — pendiente validacion humano"
  - regulation: "CIS Docker Benchmark"
    impact: "Hardening obligatorio de contenedores"
    identified_by: "compliance-analyst"
    status: "PROPUESTO MUST"
  - regulation: "OWASP Top 10 + ASVS Nivel 2"
    impact: "Ya es regla del framework; nivel 2 es objetivo para la capa de auth"
    identified_by: "compliance-analyst"
    status: "MUST"
  - regulation: "LGPD (Brasil)"
    impact: "Similar a GDPR si hay clientes brasilenos"
    identified_by: "compliance-analyst"
    status: "SHOULD HAVE segun mercado objetivo"
  - regulation: "HIPAA / PCI-DSS / FedRAMP"
    impact: "Aplican en apps huesped especificas, no al Maestro directamente"
    identified_by: "compliance-analyst"
    status: "WON'T HAVE V1"

stack_hints:
  language: "PHP 8.3+ (Laravel 13)"
  framework: "Laravel 13 + Passport 13 + React + Tailwind"
  database: "PostgreSQL (preferido, a confirmar en Planning con data-architect)"
  infra: "Docker + Traefik + Redis + Azure Blob. Todo dockerizado (DEC-012)."
  notes: "Stack es inmutable segun la premisa; el trabajo de Planning es ADRs sobre componentes y patrones, no cambio de stack."

deliverables_producidos:
  - "docs/01-discovery/RESEARCH_FINDINGS.md"
  - "docs/01-discovery/REQUIREMENTS.md"
  - "docs/01-discovery/GLOSSARY.md"

deliverables_obligatorios_heredados_de_setup:
  - "DEL-001: docs/CONVENCIONES_PLATAFORMA.md (fase 02)"
  - "DEL-002: docker-compose.dev.yml (fase 03/04)"
  - "DEL-003: SETUP_GUIDE.md (fase 04)"

human_answers_received_2026-04-16:
  Q-001:
    question: "Confirmar GDPR + SOC 2 Type II (controles) + CIS Docker + OWASP ASVS L2 como MUST HAVE V1"
    answer: "OK"
    decision: "DEC-013"
  Q-002:
    question: "Idioma V1"
    answer: "solo espanol"
    decision: "DEC-014"
  Q-003:
    question: "Accesibilidad WCAG 2.1 AA"
    answer: "WON'T HAVE V1"
    decision: "DEC-015"
  Q-004:
    question: "MFA propio TOTP"
    answer: "no"
    decision: "DEC-016"
  Q-005:
    question: "Volumen esperado 12 meses"
    answer: "1 empresa × 7 apps"
    decision: "DEC-017"
  Q-006:
    question: "Modelo de pricing"
    answer: "por empresa, sin pricing complejo V1; solo ABM de clientes, apps, usuarios"
    decision: "DEC-018"
  Q-007:
    question: "Retencion de datos mas alla del minimo legal"
    answer: "solo minimo legal"
    decision: "DEC-019"
  Q-008:
    question: "Ventanas de mantenimiento"
    answer: "las menores posibles; no zero-downtime obligatorio"
    decision: "DEC-020"
  Q-009:
    question: "Plan de soporte a clientes"
    answer: "no aplica, canal aparte"
    decision: "DEC-021"

escalations_al_PM_para_humano:
  - id: "ESC-002"
    status: "closed"
    closed_at: "2026-04-16"
    closed_by: "DEC-013"
    resolution: "Shortlist validado por humano"
  - id: "Q-001"
    status: "resolved"
    resolution: "DEC-013"
  - id: "Q-002"
    status: "resolved"
    resolution: "DEC-014"
  - id: "Q-003"
    status: "resolved"
    resolution: "DEC-015"
  - id: "Q-004"
    status: "resolved"
    resolution: "DEC-016"
  - id: "Q-005"
    status: "resolved"
    resolution: "DEC-017"
  - id: "Q-006"
    status: "resolved"
    resolution: "DEC-018"
  - id: "Q-007"
    status: "resolved"
    resolution: "DEC-019"
  - id: "Q-008"
    status: "resolved"
    resolution: "DEC-020"
  - id: "Q-009"
    status: "resolved"
    resolution: "DEC-021"

handoff_al_PM: |
  Fase 01 COMPLETADA 2026-04-16. Artefactos producidos:
  - docs/01-discovery/RESEARCH_FINDINGS.md (dominio, usuarios, competidores, insights, riesgos, compliance).
  - docs/01-discovery/REQUIREMENTS.md (112 requisitos, MoSCoW validada por humano).
  - docs/01-discovery/GLOSSARY.md (70+ terminos).
  9 decisiones registradas (DEC-013 a DEC-021). ESC-002 cerrada por DEC-013.
  Listo para activar Fase 02 (Planning) con software-architect, data-architect, api-designer, ux-designer.
```
