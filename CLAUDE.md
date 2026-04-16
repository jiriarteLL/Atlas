# CLAUDE.md — Framework de Desarrollo Agentico v2

> **Version:** 2.0.0
> **Proyecto:** Aplicaciones genericas para plataforma Web Maestro
> **Framework:** PM persistente + Agent() calls reales con contexto aislado

---

## Arquitectura

```
Humano (Product Owner)
  │
  └── PM (conversacion persistente, opus) — /pm
        │
        ├── Agent(Orquestador Fase, opus)
        │     ├── Agent(developer, sonnet/opus, worktree)
        │     ├── Agent(developer, sonnet, worktree)
        │     └── Validacion paralela:
        │           Agent(code-reviewer, sonnet)
        │           Agent(security-auditor, sonnet)
        │           Agent(qa-tester, sonnet)
        │           Agent(performance-analyst, haiku)
        │           Agent(compliance-analyst, haiku)
        │
        ├── Agent(cost-analyst, haiku) — post-fase
        │
        └── Fases: 00-Setup → 01-Discovery → 02-Planning →
            03-Development → 04-Delivery → 05-Operations → 06-Retrospective
```

**Principios clave:**
- El PM es la conversacion principal. Nunca pierde contexto.
- Todo lo demas son Agent() calls reales con contexto aislado.
- Comunicacion via Context Packets (entrada) y Phase Results (salida).
- Los agentes se determinan dinamicamente segun el problema y stack.
- Modelo por agente segun complejidad: haiku < sonnet < opus.
- Los developers trabajan en worktrees aislados.
- Validacion transversal paralela obligatoria antes de cada PR.
- Preset Web Maestro siempre activo.

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
  ├── PM determina agentes necesarios segun problema/stack
  ├── PM verifica repo GitHub, crea epic branch
  │
  ├── Para cada fase (00 a 06):
  │   ├── PM construye Context Packet (core/CONTEXT_PACKET.md)
  │   ├── PM lanza Agent(orquestador, opus) con el packet
  │   ├── Orquestador ejecuta fase:
  │   │   ├── Lanza developers en worktrees
  │   │   ├── Mergea worktrees a issue branches
  │   │   ├── Lanza validadores en paralelo
  │   │   ├── Si aprobado: crea PR issue→epic
  │   │   └── Si rechazado: reintenta (max 3) o escala
  │   ├── PM recibe Phase Result
  │   ├── PM valida exit criteria
  │   ├── PM lanza Agent(cost-analyst, haiku)
  │   └── PM actualiza checkpoints/GLOBAL.md
  │
  └── PM cierra: PR epic→main, reporte, GLOBAL completed
```

---

## Git Workflow

```
main (protegida)
  └── epic/{proyecto}
        ├── epic/{proyecto}/{modulo-1} → PR → epic
        ├── epic/{proyecto}/{modulo-2} → PR → epic
        └── PR final → main
```

- PM crea epic branch y PR final epic→main
- Orquestadores crean milestones, issues, sub-branches y PRs issue→epic
- Developers trabajan en worktrees (no tocan working directory)
- Validacion transversal aprobada = requisito para PR

---

## Validacion Transversal

Gate de calidad obligatorio. Se ejecuta en paralelo despues de cada entregable.

**Validadores minimos (siempre presentes):**
- code-reviewer, security-auditor, qa-tester, performance-analyst, compliance-analyst

**Reglas:**
- TODOS deben aprobar (PASS) para generar PR
- CRITICAL/HIGH en security bloquean sin excepcion
- N/A requiere justificacion y aprobacion del PM
- Max 3 reintentos por modulo, luego escalar al PM
- Post-aprobacion: documentation-writer documenta

---

## Estructura de Archivos

```
framework-agentico/
├── core/
│   ├── PM.md                    # System prompt del PM
│   ├── CONTEXT_PACKET.md        # Formato de comunicacion PM↔orquestadores
│   ├── RULES.md                 # Reglas generales
│   └── PRESET_WEB_MAESTRO.md   # Constraints Web Maestro (siempre activo)
│
├── phases/
│   ├── 00-setup.md              # Template + exit criteria por fase
│   ├── 01-discovery.md
│   ├── 02-planning.md
│   ├── 03-development.md
│   ├── 04-delivery.md
│   ├── 05-operations.md
│   └── 06-retrospective.md
│
├── validation/
│   ├── TRANSVERSAL_TEMPLATE.md  # Instrucciones de validacion para orquestadores
│   ├── VALIDATION_RULES.md      # Reglas del gate de calidad
│   └── validators/              # Prompt templates de cada validador
│       ├── code-reviewer.md
│       ├── security-auditor.md
│       ├── qa-tester.md
│       ├── performance-analyst.md
│       ├── compliance-analyst.md
│       └── documentation-writer.md
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

## Agentes Dinamicos

Los agentes NO estan predefinidos. Se determinan cuando el PM entiende el problema:

1. PM analiza premisa, stack y complejidad
2. PM determina roles necesarios por fase (ej: si no hay frontend, no hay frontend-developer)
3. PM asigna modelo por complejidad: haiku (simple), sonnet (estandar), opus (complejo)
4. Los templates de fase sugieren roles tipicos pero el PM adapta

**Modelo dinamico:** el orquestador puede escalar el modelo de un agente si la tarea falla o es mas compleja de lo esperado.

---

## Monitoreo de Costos

- Post-fase: PM lanza Agent(cost-analyst, haiku) para leer JSONL de sesion
- Registra tokens (input, output, cache_read, cache_creation) y costo USD estimado
- Sin limite de presupuesto, pero monitoreo activo para estrategias futuras
- Precios en cost/PRICING.md, registro en cost/COST_LOG.md

---

## Como Iniciar

1. Invocar `/pm` para hablar con el Project Manager
2. El PM pregunta la premisa hasta certeza 100%
3. El PM determina agentes, stack y plan de fases
4. `/pm:orquestar` para ejecutar, `/pm:planificar` para solo planificar
5. `/pm:estado` para ver progreso en cualquier momento

## Reanudacion de Sesion

Al inicio, verificar `framework-agentico/checkpoints/GLOBAL.md`:
- Si hay proyecto in_progress o interrupted: preguntar si retomar
- Si no hay proyecto activo: iniciar desde /pm

---

## Documentacion Detallada

- System prompt del PM: `framework-agentico/core/PM.md`
- Formato de comunicacion: `framework-agentico/core/CONTEXT_PACKET.md`
- Reglas generales: `framework-agentico/core/RULES.md`
- Preset Web Maestro: `framework-agentico/core/PRESET_WEB_MAESTRO.md`
- Templates de fase: `framework-agentico/phases/{NN}-{nombre}.md`
- Validacion transversal: `framework-agentico/validation/`
- Estado del proyecto: `framework-agentico/checkpoints/GLOBAL.md`
- Costos: `framework-agentico/cost/`
