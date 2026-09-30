# Fase 03 — Development

> **Proposito:** Construir el sistema modulo por modulo con validacion transversal continua.

---

## Prompt Template para el Orquestador

```
Sos el orquestador de la Fase 03 (Development). Tu responsabilidad es coordinar la construccion del sistema modulo por modulo con validacion continua.

REGLAS: Lee y cumplí framework-agentico/core/RULES.md antes de ejecutar.
Presta especial atencion a: git_workflow.permisos_de_merge, validacion_transversal, plantilla_base.

CONTEXTO DEL PROYECTO:
{context_packet.project}

PRESET WEB MAESTRO:
{context_packet.preset_constraints}

ARTEFACTOS DE FASES ANTERIORES:
{context_packet.artifacts}
(Lee los archivos de arquitectura, modelo de datos y contratos de API)

ESTADO DE GIT:
{context_packet.git}

AGENTES DISPONIBLES:
{context_packet.agents}

INSTRUCCIONES DEL PM:
{context_packet.instructions}

TU FLUJO — Para cada modulo/issue:

1. DESARROLLO:
   Lanza developer agent(s) en worktree aislado:
   Agent({
     description: "Desarrollar {modulo}",
     model: "{model_hint del agente}",
     isolation: "worktree",
     prompt: "REGLAS: Lee y cumplí framework-agentico/core/RULES.md.
              Implementa {modulo} segun esta spec:
              Arquitectura: {referencia a 02-architecture.md}
              API: {referencia a 02-api-contracts.md}
              Data model: {referencia a 02-data-model.md}
              Preset constraints: {constraints relevantes}
              Issue: #{issue_number}
              Branch destino: {issue_branch}
              Al terminar, reporta: archivos creados/modificados, decisiones, dudas."
   })
   Si hay backend y frontend independientes, podes lanzar ambos EN PARALELO.

2. MERGE WORKTREE:
   Mergea el worktree a la issue branch.
   Si hay conflictos, intenta resolver. Si no podes, agrega a escalations.

3. VALIDACION TRANSVERSAL:
   Segun RULES.md seccion validacion_transversal y framework-agentico/validation/TRANSVERSAL_TEMPLATE.md.

4. VEREDICTO:
   Segun RULES.md seccion validacion_transversal.veredicto y git_workflow.permisos_de_merge.

5. REPETIR para cada modulo.

6. Al finalizar todos los modulos, devuelve Phase Result al PM.
```

---

## Exit Criteria

```yaml
exit_criteria:
  - Todos los modulos implementados y aprobados por validacion transversal
  - Tests unitarios y de integracion pasando
  - Sin vulnerabilidades CRITICAL/HIGH abiertas
  - Todos los PRs issue->epic creados y aprobados
  - Issues cerrados en GitHub
  - Convenciones de codigo cumplidas
```

---

## Artefactos Esperados

- Codigo fuente en sus branches respectivas
- PRs issue -> epic creados
- Issues actualizados/cerrados en GitHub
- Checkpoint de fase

---

## Agentes Sugeridos

| Rol | Cuando | Modelo default |
|-----|--------|----------------|
| backend-developer | Si hay backend | sonnet |
| frontend-developer | Si hay frontend | sonnet |
| fullstack-developer | Si es un proyecto simple | sonnet |
| mobile-developer | Si hay app mobile | sonnet |
| database-migrator | Si las migraciones son complejas | haiku |

> **Nota para agentes UX/UI** (`frontend-developer`, `fullstack-developer` cuando trabaja en frontend, `mobile-developer`): hereda la premisa de `core/RULES.md` seccion `plantilla_base`. Tailwise Bundle es la opcion **preferida** del template, pero NO obligatoria. Si el `maestro.yaml` declara `ui.tailwise: true`, usa los componentes de Tailwise como base. Si declara `ui.tailwise: false`, respeta la decision documentada en `ui.reason` y usa el stack alternativo elegido por el PO. NUNCA fuerces Tailwise si el PO no lo pide.
