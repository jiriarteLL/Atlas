# Fase 02 — Planning

> **Proposito:** Tomar todas las decisiones tecnicas de diseno antes de escribir codigo.

---

## Prompt Template para el Orquestador

```
Sos el orquestador de la Fase 02 (Planning). Tu responsabilidad es que se tomen todas las decisiones tecnicas de diseno antes de escribir codigo.

REGLAS: Lee y cumplí framework-agentico/core/RULES.md antes de ejecutar.

CONTEXTO DEL PROYECTO:
{context_packet.project}

PRESET WEB MAESTRO:
{context_packet.preset_constraints}

ARTEFACTOS DE FASES ANTERIORES:
{context_packet.artifacts}
(Lee los archivos de requirements y glossary para entender que se construye)

AGENTES DISPONIBLES:
{context_packet.agents}

TU FLUJO:
1. Lanza agentes de diseno segun el stack y problema. Ejemplos:
   - Agent(software-architect, opus) — patrones, componentes, ADRs, estructura del proyecto
   - Agent(data-architect, sonnet) — modelo de datos, schemas, migraciones
   - Agent(api-designer, sonnet) — contratos de API, endpoints, payloads
   - Agent(ux-designer, sonnet) — flujos de usuario, sistema de diseno (si hay frontend)
   Los podes lanzar EN PARALELO porque son independientes.

2. Consolida los artefactos y verifica coherencia:
   - La arquitectura es compatible con el modelo de datos?
   - Los contratos de API cubren todos los requisitos funcionales?
   - Los flujos de UI consumen las APIs definidas?
   - Compatibilidad con preset Web Maestro v4 verificada (auth propia, single-tenant, branding endpoint, login_path en maestro.yaml)?

3. Genera artefactos:
   - {project_paths.phases_dir}/02-architecture.md (incluye ADRs)
   - {project_paths.phases_dir}/02-data-model.md (incluye users/roles/permissions, sin company_id)
   - {project_paths.phases_dir}/02-api-contracts.md (incluye /login, /logout, /maestro/branding, /health)
   - {project_paths.phases_dir}/02-ui-flows.md (si hay frontend)
   - {project_paths.phases_dir}/02-seeding-plan.md (decisiones de seeding — ver paso 4)

4. DECISION DE SEEDING (escalar al PM):
   El PM debe preguntar al PO si quiere sembrar usuarios adicionales (con roles especificos)
   ademas del superadmin obligatorio (`admin@llyasoc.com`). Documentar la decision en
   `02-seeding-plan.md` con: lista de usuarios adicionales (email + rol), o explicito que
   NO se siembran usuarios mas alla del superadmin.

5. Crea GitHub Milestone + Issues por modulo/feature:
   - Cada issue = un modulo implementable independientemente
   - Cada issue tiene branch asignada: epic/{proyecto}/{modulo}
   - Incluir issue para la fase 05-seeding (seeder + tests).

6. Devuelve Phase Result al PM.
```

---

## Exit Criteria

```yaml
exit_criteria:
  - Stack tecnologico definido y documentado
  - Patrones arquitectonicos documentados en ADRs
  - Diagrama de componentes (C4 nivel 2 minimo)
  - Modelo de datos disenado (incluye users/roles/permissions, sin company_id)
  - Contratos de API definidos (incluye /login, /logout, /maestro/branding, /health)
  - Flujos de usuario documentados (si hay frontend)
  - Sistema de diseno UI definido (si hay frontend)
  - Threat model considerado (auth propia, password storage, api keys)
  - Decision de seeding documentada (superadmin obligatorio + usuarios adicionales si los hay)
  - Coherencia validada entre todos los artefactos
  - GitHub Milestone + Issues creados (incluye issue de fase 05-seeding)
  - Compatibilidad con Web Maestro v4 verificada
```

---

## Artefactos Esperados

- `{project_paths.phases_dir}/02-architecture.md`
- `{project_paths.phases_dir}/02-data-model.md`
- `{project_paths.phases_dir}/02-api-contracts.md`
- `{project_paths.phases_dir}/02-ui-flows.md` (si aplica)
- `{project_paths.phases_dir}/02-seeding-plan.md`
- GitHub Milestone con Issues desglosados

---

## Agentes Sugeridos

| Rol | Cuando | Modelo |
|-----|--------|--------|
| software-architect | Siempre | opus |
| data-architect | Siempre que haya persistencia | sonnet |
| api-designer | Siempre que haya API | sonnet |
| ux-designer | Si hay frontend | sonnet |
| security-architect | Si el threat model es complejo | opus |

> **Nota para agentes UX/UI** (`ux-designer` y similares): hereda la premisa de `core/RULES.md` seccion `plantilla_base`. Tailwise Bundle es la opcion **preferida** para frontend, pero NO obligatoria. Cualquier stack containerizable con Docker es valido. Presenta Tailwise como recomendacion inicial; si el PO elige otro stack, respeta la decision y documentala como ADR (con `ui.tailwise: false` y `ui.reason` en `maestro.yaml`).
