# Reglas Transversales

> **Aplican a:** Todos los agentes transversales en todas las fases

---

## Reglas Generales

```yaml
reglas:
  - todo artefacto de código debe pasar por code-review antes de avanzar
  - todo artefacto aprobado por code-review pasa a security-auditor
  - ningún artefacto avanza con vulnerabilidades de severidad CRITICAL o HIGH sin remediación
  - la documentación se genera para cada fase, no solo al final
  - los reportes ejecutivos usan lenguaje de negocio, no técnico
  - los agentes transversales adaptan sus checklists al stack del proyecto
  - si un preset está activo, las reglas del preset extienden estas reglas
  - las dudas se escalan: agente → orquestador transversal → PM → humano
  - cada intervención transversal se registra en el checkpoint
  - el veredicto transversal es consolidado: un solo resultado, no múltiples reportes sueltos

secuenciacion:
  - code-review rechaza → no se ejecuta security ni QA (desperdicio)
  - security rechaza → no se ejecuta performance (priorizar seguridad)
  - compliance rechaza → bloqueo total hasta remediación
  - documentation-writer actúa post-aprobación técnica
  - executive-reporter solo bajo solicitud explícita

adaptacion_por_fase:
  00-setup: "skills-researcher activo, resto inactivo"
  01-discovery: "compliance-analyst activo para requisitos regulatorios"
  02-planning: "security-auditor para threat modeling, code-reviewer para ADRs"
  03-development: "ciclo completo de validación en cada módulo"
  04-delivery: "integrator solicita validación final completa"
  05-operations: "observability validada por performance-analyst"
  06-retrospective: "documentation-writer consolida, executive-reporter genera reporte final"
```
