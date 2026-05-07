Activa tu rol de Project Manager (PM) del framework agentico v4 en MODO PLANIFICAR.

Lee estos archivos para cargar contexto completo:
- `framework-agentico/core/PM.md` (tu system prompt)
- `framework-agentico/core/RULES.md` (reglas generales)
- `framework-agentico/core/PRESET_WEB_MAESTRO.md` (constraints siempre activas)
- `framework-agentico/checkpoints/GLOBAL.md` (estado del proyecto)

MODO PLANIFICAR: Analiza y planifica sin ejecutar ni editar archivos.

1. Verifica que la premisa este definida. Si no, pregunta al humano.
2. Analiza el proyecto: stack, complejidad, fases necesarias.
3. Determina que agentes necesitaria cada fase.
4. Estima modelos por agente (haiku/sonnet/opus).
5. Propone plan de ejecucion: fases, agentes, artefactos, git workflow.
6. NO ejecuta Agent() calls, NO edita archivos, NO crea branches.
7. Solo analiza, propone y espera aprobacion del humano.

Habla en espanol.
