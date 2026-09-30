# Fase 06 — Operations

> **Proposito:** Preparar el sistema para operar en produccion con observabilidad y protocolos de respuesta.

---

## Prompt Template para el Orquestador

```
Sos el orquestador de la Fase 06 (Operations). Tu responsabilidad es que el sistema tenga todo para operar en produccion.

REGLAS: Lee y cumplí framework-agentico/core/RULES.md antes de ejecutar.

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
   - Configurar logging estructurado (incluir user_id y request_id; NO incluir company_id porque el contenedor es single-tenant fisico en v4)
   - Configurar alertas para metricas criticas
   - Documentar dashboards recomendados
   - Implementar audit log de eventos de auth (login, logout, cambios de password, cambios de roles)
   IMPORTANTE: NO loguear cookies de sesion, JWTs propios, MAESTRO_API_KEY ni MAESTRO_WEBHOOK_SECRET (Web Maestro v4)

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
  - Logging estructurado implementado (con user_id y request_id; sin company_id en v4 single-tenant)
  - Audit log de eventos de auth implementado
  - Alertas configuradas
  - Runbook operativo documentado
  - Protocolo de incidentes definido
  - Deuda tecnica documentada con plan de remediacion
  - Logs verificados: sin datos sensibles (no cookies de sesion, no JWTs, no MAESTRO_API_KEY, no MAESTRO_WEBHOOK_SECRET)
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
