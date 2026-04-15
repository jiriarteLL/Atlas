# Reglas Generales del Framework

> **Aplican a:** Todos los agentes, orquestadores y fases

---

```yaml
governance:
  - el humano es el Product Owner; las prioridades de negocio siempre se escalan a él
  - el PM no avanza de fase sin exit_criteria cumplidos en el checkpoint de la fase
  - si se invoca una fase directamente, el PM verifica que las anteriores estén completas
  - toda duda sigue la cadena: agente → orquestador de fase → PM → humano
  - el modo planificar nunca edita archivos ni ejecuta comandos

calidad_continua:
  - QA, Security, Performance, Compliance y Code Review son transversales y actúan en todas las fases
  - ningún artefacto de código avanza sin pasar por code-review
  - vulnerabilidades CRITICAL/HIGH bloquean el avance sin excepción
  - la cobertura de tests mínima es 80% statements, 70% branches
  - toda decisión arquitectónica se documenta como ADR

documentacion:
  - cada fase tiene un directorio /docs con templates predefinidos
  - el documentation-writer genera templates al inicio y los completa al final de cada fase
  - la documentación se versiona junto con el código
  - al final del proyecto se consolida toda la documentación

checkpoint:
  - cada fase tiene su propio checkpoint con exit_criteria
  - existe un checkpoint global administrado por el PM
  - los checkpoints se actualizan después de cada cambio de estado significativo
  - al reanudar una sesión, el PM verifica si hay trabajo en curso

adaptacion_al_stack:
  - el stack se define en fase 01 (Discovery) o 02 (Planning)
  - una vez definido, todos los agentes ajustan sus reglas y artefactos al stack
  - el PM verifica continuamente compatibilidad con la arquitectura final
  - si hay preset activo, las reglas del preset extienden (no reemplazan) las generales

presets:
  - un preset es un conjunto de reglas adicionales que se activan para un contexto específico
  - el preset se activa al inicio del proyecto y aplica a todas las fases
  - los agentes verifican si hay preset activo y aplican sus reglas adicionales
  - las reglas del preset nunca contradicen las reglas generales

monitoreo_de_costos:
  - el cost-analyst registra consumo de tokens de cada consulta en COST_LOG.md
  - al cierre de cada fase, el cost-analyst consolida metricas en el checkpoint de fase y en CHECKPOINT_GLOBAL
  - los costos se registran siempre en tokens (valor absoluto) y en USD (valor estimado con pricing vigente)
  - si la licencia o el pricing cambia, se actualiza en COST_LOG.md; los registros historicos NO se recalculan
  - si el humano define un budget_usd, el cost-analyst alerta al 60%, 80%, 95% y 100% del presupuesto
  - el cost-analyst no es un gate de validacion; opera en paralelo y reporta sin bloquear
  - las metricas de eficiencia (tokens/respuesta, cache hit rate, tokens/LOC) se incluyen en reportes ejecutivos

comunicacion_entre_agentes:
  - los agentes se comunican mediante artefactos con estructura predefinida
  - los orquestadores de fase solicitan intervención transversal al orquestador transversal
  - los agentes nunca se invocan directamente entre fases; pasan por sus orquestadores
  - el veredicto transversal es consolidado: un resultado, no múltiples reportes

mejora_continua:
  - al final de cada proyecto se ejecuta la fase 06 (Retrospective)
  - el memory-updater registra patrones exitosos, errores evitados y preferencias del usuario
  - cada nuevo proyecto se beneficia de las memorias anteriores
```
