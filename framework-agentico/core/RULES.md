# Reglas Generales del Framework v2

> **Aplican a:** PM, todos los orquestadores y todos los agentes

---

```yaml
governance:
  - El humano es el Product Owner. Las prioridades de negocio siempre se escalan a el.
  - El PM no avanza de fase sin exit_criteria cumplidos en el checkpoint de la fase.
  - Si se invoca una fase directamente, el PM verifica que las anteriores esten completas.
  - Toda duda sigue la cadena: agente -> orquestador de fase -> PM -> humano.
  - El modo planificar nunca edita archivos ni ejecuta comandos.
  - Cada agente es un Agent() call real con contexto aislado, no role-play.

calidad_continua:
  - Ningun artefacto de codigo avanza sin pasar por validacion transversal completa.
  - Los validadores minimos obligatorios son: code-reviewer, security-auditor, qa-tester, performance-analyst, compliance-analyst.
  - TODOS los validadores deben aprobar (PASS) para generar un PR.
  - Si un validador no aplica (N/A), el orquestador consulta al PM para validar la justificacion.
  - Vulnerabilidades CRITICAL/HIGH bloquean el avance sin excepcion.
  - Toda decision arquitectonica se documenta como ADR.
  - Maximo 3 reintentos de correccion por modulo antes de escalar al PM.

agentes_dinamicos:
  - Los agentes se determinan cuando el PM entiende el problema, no antes.
  - El PM decide que agentes necesita cada fase segun el stack y el problema.
  - El modelo de cada agente es dinamico segun complejidad:
    - haiku: tareas simples, validaciones rapidas, tareas mecanicas
    - sonnet: desarrollo estandar, reviews, testing
    - opus: PM, orquestadores, decisiones arquitectonicas, debugging profundo
  - Los templates de validadores en validation/validators/ son guias; el orquestador los adapta.

comunicacion:
  - La comunicacion entre PM y orquestadores usa el Context Packet (ver core/CONTEXT_PACKET.md).
  - El PM envia un Context Packet completo a cada orquestador.
  - Cada orquestador devuelve un Phase Result estructurado.
  - Los artefactos pesados se referencian como paths a archivos, no como contenido inline.
  - Los agentes dentro de una fase se comunican a traves de su orquestador.
  - Los agentes NUNCA se invocan directamente entre fases; siempre pasan por el PM.

git_workflow:
  - El PM crea la epic branch al iniciar proyecto.
  - Los orquestadores crean milestones, issues y sub-branches.
  - Los developers trabajan en worktrees aislados (isolation "worktree" en Agent()).
  - El orquestador mergea worktrees a issue branches.
  - Los PRs se crean solo despues de validacion transversal aprobada.
  - Conflictos irresolubles se escalan al PM.
  - El PM crea el PR final epic -> main al cerrar.

checkpoint:
  - El PM mantiene checkpoints/GLOBAL.md actualizado despues de cada cambio de estado.
  - Cada fase puede generar artefactos en checkpoints/phases/.
  - Al reanudar una sesion, el PM verifica GLOBAL.md para determinar estado.

preset_web_maestro:
  - Siempre activo. Todas las aplicaciones corren en la plataforma Web Maestro.
  - Las constraints del preset se incluyen en cada Context Packet.
  - Las constraints son no negociables y aplican en todas las fases.
  - Ver core/PRESET_WEB_MAESTRO.md para la lista completa.

monitoreo_de_costos:
  - Despues de cada fase, el PM lanza Agent(cost-analyst, haiku) para registrar metricas.
  - Los costos se registran en tokens (absoluto) y USD (estimado).
  - Tabla de precios en cost/PRICING.md. Historicos NO se recalculan si cambia.
  - No hay limite de presupuesto pero se monitorea para estrategias futuras.
  - Metricas de eficiencia: tokens/respuesta, cache hit rate, tokens/LOC.
```
