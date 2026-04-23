# CLAUDE.md — Framework de Desarrollo Agentico v3

> **Version:** 3.0.0
> **Proyecto:** Aplicaciones genericas para plataforma Web Maestro
> **Framework:** PM persistente + Agent() calls reales + memorias transaccionales + aislamiento por proyecto

---

## REGLAS OBLIGATORIAS

**TODOS los agentes (PM, orquestadores, developers, validadores) DEBEN leer y cumplir
`framework-agentico/core/RULES.md` ANTES de ejecutar cualquier accion.**

RULES.md es la FUENTE UNICA DE VERDAD para todas las reglas del framework.
Ningun otro archivo puede contradecirlo. Si hay conflicto, RULES.md prevalece.

---

## Arquitectura

```
Humano (Product Owner)
  |
  └── PM (conversacion persistente, opus) — /pm
        |
        ├── Agent(Orquestador Fase, opus)
        │     ├── Agent(developer, sonnet/opus, worktree)
        │     ├── Validacion paralela: Agent(validators...)
        │     └── Escribe transacciones por cada Agent() call
        │
        ├── Agent(cost-analyst, haiku) — post-fase
        │     └── Actualiza: rama/COST_LOG -> proyecto/SUMMARY -> GLOBAL
        │
        └── Fases: 00-Setup → 01-Discovery → 02-Planning →
            03-Development → 04-Delivery → 05-Operations → 06-Retrospective

Datos:
  projects/{project-id}/
    ├── PROJECT.md (estado del proyecto)
    ├── cost/SUMMARY.md (rollup de costos)
    └── branches/{rama}/
          ├── BRANCH.md, cost/COST_LOG.md
          ├── phases/ (artefactos de fase)
          └── transactions/ (memorias transaccionales)
```

---

## Comandos

Solo el PM tiene slash commands. Todo lo demas es interno via Agent().

| Comando | Accion | Modo |
|---------|--------|------|
| `/pm` | Conversacion con el PM | Interactivo |
| `/pm:orquestar` | Ejecuta proyecto completo fase por fase | Ejecucion |
| `/pm:planificar` | Analiza y planifica sin ejecutar | Solo lectura |
| `/pm:estado` | Muestra estado actual del proyecto | Consulta |
| `/pm:reporte` | Genera reporte ejecutivo | Consulta |

---

## Flujo de Ejecucion

```
/pm:orquestar
  |
  ├── PM obtiene project-id del repo (gh repo view --json name)
  ├── PM crea estructura: projects/{id}/PROJECT.md, cost/, branches/
  ├── PM entiende premisa (pregunta hasta certeza 100%)
  ├── PM determina agentes segun problema/stack
  ├── PM verifica prerequisitos del repo (ver RULES.md)
  ├── PM crea epic branch + estructura de rama
  |
  ├── Para cada fase (00 a 06):
  │   ├── PM registra interaccion propia como transaccion
  │   ├── PM construye Context Packet con project_paths (core/CONTEXT_PACKET.md)
  │   ├── PM lanza Agent(orquestador, opus) con el packet
  │   ├── Orquestador ejecuta fase, escribe transacciones por cada agente
  │   ├── PM recibe Phase Result (incluye cost_breakdown + transactions_written)
  │   ├── PM valida exit criteria
  │   ├── PM lanza Agent(cost-analyst, haiku) -> actualiza rama/COST_LOG, proyecto/SUMMARY
  │   └── PM actualiza PROJECT.md y GLOBAL.md
  |
  ├── PM cierra proyecto (segun RULES.md seccion cierre_de_proyecto)
  └── PM lanza compactacion de transacciones
```

---

## Estructura de Archivos

```
framework-agentico/
├── core/
│   ├── PM.md                    # System prompt del PM
│   ├── CONTEXT_PACKET.md        # Formato de comunicacion PM↔orquestadores (v3)
│   ├── RULES.md                 # FUENTE UNICA DE VERDAD — todas las reglas
│   ├── PRESET_WEB_MAESTRO.md   # Constraints Web Maestro (siempre activo)
│   └── templates/               # Templates para instanciar por proyecto
│       ├── PROJECT_TEMPLATE.md
│       ├── BRANCH_TEMPLATE.md
│       ├── TRANSACTION_TEMPLATE.md
│       ├── COST_LOG_TEMPLATE.md
│       └── COST_SUMMARY_TEMPLATE.md
│
├── phases/                      # Templates operativos por fase (inmutables)
│   ├── 00-setup.md ... 06-retrospective.md
│
├── validation/                  # Templates de validacion (inmutables)
│   ├── TRANSVERSAL_TEMPLATE.md
│   ├── VALIDATION_RULES.md
│   └── validators/
│
├── checkpoints/
│   ├── GLOBAL.md                # INDICE de proyectos (no checkpoint individual)
│   └── phases/                  # Legacy — los artefactos ahora van por proyecto/rama
│
├── cost/
│   ├── PRICING.md               # Tabla de precios (referencia global)
│   └── COST_LOG.md              # Referencia — datos reales por rama en projects/
│
├── projects/                    # DIRECTORIO DE PROYECTOS
│   └── {project-id}/
│       ├── PROJECT.md           # Estado del proyecto
│       ├── cost/
│       │   └── SUMMARY.md       # Costos agregados (rollup de ramas)
│       └── branches/
│           └── {sanitized-branch}/
│               ├── BRANCH.md
│               ├── cost/COST_LOG.md
│               ├── phases/
│               └── transactions/
│
└── docs/                        # Documentacion generada (dinamica)
```

---

## Como Iniciar

1. Invocar `/pm` para hablar con el Project Manager
2. El PM detecta el repo, crea estructura de proyecto en projects/
3. El PM lee RULES.md, pregunta la premisa hasta certeza 100%
4. El PM determina agentes, stack y plan de fases
5. `/pm:orquestar` para ejecutar, `/pm:planificar` para solo planificar
6. `/pm:estado` para ver progreso en cualquier momento

## Reanudacion de Sesion

Al inicio, verificar `framework-agentico/checkpoints/GLOBAL.md`:
- Si hay proyecto activo (active_project != null): cargar su PROJECT.md
- Si el proyecto esta in_progress o interrupted: preguntar si retomar
- Si no hay proyecto activo: iniciar desde /pm

## Sincronizacion de Proyecto Existente

Si el repositorio tiene codigo pero no hay archivos de seguimiento,
el PM crea la estructura de proyecto y entra en modo sincronizacion.
Analiza el estado actual fase por fase contra los exit criteria, presenta
los hallazgos al Project Owner interactivamente, y marca las fases como
`verified_by_analysis` o `incomplete_pre_existing` segun corresponda.
Ver `framework-agentico/core/RULES.md` seccion 9 para las reglas completas.

---

## Documentacion Detallada

- **REGLAS (fuente unica):** `framework-agentico/core/RULES.md`
- System prompt del PM: `framework-agentico/core/PM.md`
- Formato de comunicacion: `framework-agentico/core/CONTEXT_PACKET.md`
- Preset Web Maestro: `framework-agentico/core/PRESET_WEB_MAESTRO.md`
- Templates de instanciacion: `framework-agentico/core/templates/`
- Templates de fase: `framework-agentico/phases/{NN}-{nombre}.md`
- Validacion transversal: `framework-agentico/validation/`
- Indice de proyectos: `framework-agentico/checkpoints/GLOBAL.md`
- Precios de referencia: `framework-agentico/cost/PRICING.md`
- Proyectos: `framework-agentico/projects/`
