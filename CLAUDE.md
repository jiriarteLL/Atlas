# CLAUDE.md — Framework de Desarrollo Agentico v2

> **Version:** 2.0.0
> **Proyecto:** Aplicaciones genericas para plataforma Web Maestro
> **Framework:** PM persistente + Agent() calls reales con contexto aislado

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
  │
  └── PM (conversacion persistente, opus) — /pm
        │
        ├── Agent(Orquestador Fase, opus)
        │     ├── Agent(developer, sonnet/opus, worktree)
        │     └── Validacion paralela: Agent(validators...)
        │
        ├── Agent(cost-analyst, haiku) — post-fase
        │
        └── Fases: 00-Setup → 01-Discovery → 02-Planning →
            03-Development → 04-Delivery → 05-Operations → 06-Retrospective
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
  │
  ├── PM entiende premisa (pregunta hasta certeza 100%)
  ├── PM determina agentes segun problema/stack
  ├── PM verifica prerequisitos del repo (ver RULES.md)
  ├── PM crea epic branch
  │
  ├── Para cada fase (00 a 06):
  │   ├── PM construye Context Packet (core/CONTEXT_PACKET.md)
  │   ├── PM lanza Agent(orquestador, opus) con el packet
  │   ├── Orquestador ejecuta fase (segun RULES.md)
  │   ├── PM recibe Phase Result
  │   ├── PM valida exit criteria
  │   ├── PM lanza Agent(cost-analyst, haiku)
  │   └── PM actualiza checkpoints/GLOBAL.md
  │
  └── PM cierra proyecto (segun RULES.md seccion cierre_de_proyecto)
```

---

## Estructura de Archivos

```
framework-agentico/
├── core/
│   ├── PM.md                    # System prompt del PM
│   ├── CONTEXT_PACKET.md        # Formato de comunicacion PM↔orquestadores
│   ├── RULES.md                 # FUENTE UNICA DE VERDAD — todas las reglas
│   └── PRESET_WEB_MAESTRO.md   # Constraints Web Maestro (siempre activo)
│
├── phases/                      # Templates operativos por fase
│   ├── 00-setup.md
│   ├── 01-discovery.md
│   ├── 02-planning.md
│   ├── 03-development.md
│   ├── 04-delivery.md
│   ├── 05-operations.md
│   └── 06-retrospective.md
│
├── validation/
│   ├── TRANSVERSAL_TEMPLATE.md  # Instrucciones de validacion para orquestadores
│   ├── VALIDATION_RULES.md      # Formato de resultado por validador
│   └── validators/              # Prompt templates de cada validador
│
├── checkpoints/
│   ├── GLOBAL.md                # Estado global del proyecto
│   └── phases/                  # Artefactos por fase (dinamicos)
│
├── cost/
│   ├── PRICING.md               # Tabla de precios por modelo
│   └── COST_LOG.md              # Registro detallado de consumo
│
└── docs/                        # Documentacion generada (dinamica)
```

---

## Como Iniciar

1. Invocar `/pm` para hablar con el Project Manager
2. El PM lee RULES.md, pregunta la premisa hasta certeza 100%
3. El PM determina agentes, stack y plan de fases
4. `/pm:orquestar` para ejecutar, `/pm:planificar` para solo planificar
5. `/pm:estado` para ver progreso en cualquier momento

## Reanudacion de Sesion

Al inicio, verificar `framework-agentico/checkpoints/GLOBAL.md`:
- Si hay proyecto in_progress o interrupted: preguntar si retomar
- Si no hay proyecto activo: iniciar desde /pm

## Sincronizacion de Proyecto Existente

Si el repositorio tiene codigo pero no hay archivos de seguimiento (checkpoints de fase),
el PM entra automaticamente en modo sincronizacion al iniciar cualquier modo.
Analiza el estado actual del codigo fase por fase contra los exit criteria, presenta
los hallazgos al Project Owner de forma interactiva, y marca las fases como
`verified_by_analysis` o `incomplete_pre_existing` segun corresponda.
Ver `framework-agentico/core/RULES.md` seccion 9 para las reglas completas.

---

## Documentacion Detallada

- **REGLAS (fuente unica):** `framework-agentico/core/RULES.md`
- System prompt del PM: `framework-agentico/core/PM.md`
- Formato de comunicacion: `framework-agentico/core/CONTEXT_PACKET.md`
- Preset Web Maestro: `framework-agentico/core/PRESET_WEB_MAESTRO.md`
- Templates de fase: `framework-agentico/phases/{NN}-{nombre}.md`
- Validacion transversal: `framework-agentico/validation/`
- Estado del proyecto: `framework-agentico/checkpoints/GLOBAL.md`
- Costos: `framework-agentico/cost/`
