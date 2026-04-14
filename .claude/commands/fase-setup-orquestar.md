Activa tu rol de Orquestador de Fase 00 (Setup) en MODO ORQUESTAR.

Lee estos archivos para cargar contexto completo:
- `framework-agentico/agents/00-setup/ORCHESTRATOR.md` (tu system prompt)
- `framework-agentico/agents/00-setup/environment-setup.md` (agente que coordinas)
- `framework-agentico/agents/00-setup/rules/RULES.md` (reglas de la fase)
- `framework-agentico/agents/00-setup/CHECKPOINT.md` (estado de la fase)
- `framework-agentico/agents/CHECKPOINT_GLOBAL.md` (estado global)
- `framework-agentico/agents/rules/GENERAL_RULES.md` (reglas generales)

MODO ORQUESTAR: Ejecuta la fase de setup real.
1. Detecta el SO del usuario (Windows 11 segun entorno).
2. Evalua que herramientas ya tiene instaladas.
3. Guia la instalacion de las que faltan (IDE, Docker, cliente BD).
4. Verifica acceso al repositorio.
5. Actualiza el checkpoint de la fase al completar.

Habla en espanol.
