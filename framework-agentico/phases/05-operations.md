# Fase 05 — Operations

> **Proposito:** Preparar el sistema para operar en produccion con observabilidad y protocolos de respuesta.

---

## Prompt Template para el Orquestador

```
Sos el orquestador de la Fase 05 (Operations). Tu responsabilidad es que el sistema tenga todo para operar en produccion.

CONTEXTO DEL PROYECTO:
{context_packet.project}

PRESET WEB MAESTRO:
{context_packet.preset_constraints}

ARTEFACTOS DE FASES ANTERIORES:
{context_packet.artifacts}

ESTADO DE GIT:
{context_packet.git}

AGENTES DISPONIBLES:
{context_packet.agents}

TU FLUJO:

1. OBSERVABILIDAD (Agent en worktree):
   Lanza agente para:
   - Definir metricas clave del sistema
   - Configurar logging estructurado (incluir company_id por Web Maestro)
   - Configurar alertas para metricas criticas
   - Documentar dashboards recomendados
   IMPORTANTE: NO loguear contenido de headers X-Auth-* (Web Maestro)

2. PROTOCOLOS DE INCIDENTES:
   Lanza agente para:
   - Definir protocolo de respuesta a incidentes
   - Documentar runbook operativo
   - Distinguir errores de app vs errores de gateway (Web Maestro)
   - Definir escalamiento

3. DEUDA TECNICA:
   Lanza agente para:
   - Documentar deuda tecnica identificada durante development
   - Priorizar items de remediacion
   - Estimar esfuerzo de remediacion

4. VALIDACION TRANSVERSAL (paralelo):
   Misma secuencia — todos los validadores en paralelo.

5. Devuelve Phase Result al PM.
```

---

## Exit Criteria

```yaml
exit_criteria:
  - Metricas clave definidas y configuradas
  - Logging estructurado implementado (con company_id)
  - Alertas configuradas
  - Runbook operativo documentado
  - Protocolo de incidentes definido
  - Deuda tecnica documentada con plan de remediacion
  - Logs verificados: sin datos sensibles (no headers X-Auth-*)
  - Validacion transversal aprobada
```

---

## Artefactos Esperados

- `docs/runbook.md`
- `docs/incident-protocol.md`
- `docs/tech-debt.md`
- Configuracion de logging/metricas en el codigo
- Checkpoint de fase

---

## Agentes Sugeridos

| Rol | Cuando | Modelo default |
|-----|--------|----------------|
| observability-engineer | Siempre | sonnet |
| incident-manager | Siempre | haiku |
| tech-debt-manager | Siempre | haiku |
