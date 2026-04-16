# Context Packet — Formato de Comunicacion entre PM y Orquestadores

> **Version:** 2.0
> **Proposito:** Eliminar perdida de informacion entre Agent() calls

---

## Principios

1. **El PM nunca pierde contexto.** Cada Agent() recibe todo lo que necesita y devuelve todo lo que el PM necesita saber.
2. **Artefactos pesados son paths, no contenido.** El context packet referencia archivos, no los incluye inline.
3. **El formato es una guia, no un schema rigido.** Adaptar al contexto del proyecto.

---

## Input: Context Packet (PM -> Orquestador)

El PM construye este packet y lo pasa como prompt al Agent() del orquestador de fase.

```yaml
context_packet:

  # --- Identificacion ---
  meta:
    project_id: "PRJ-XXXX"
    phase: "NN-nombre"              # ej: "03-development"
    timestamp: "YYYY-MM-DDTHH:MM:SSZ"
    retry: 0                        # numero de reintento (0 = primera vez)

  # --- Contexto del proyecto ---
  project:
    premise: "Descripcion completa de lo que se construye y para quien"
    stack:
      backend: "Framework / Lenguaje"
      frontend: "Framework / Lenguaje"
      database: "Motor / Version"
      infra: "Docker / Cloud / etc"
    preset_constraints:              # Web Maestro (siempre presentes)
      - "Auth por headers X-Auth-*, NO tabla users"
      - "Filtrar queries por company_id"
      - "GET /health -> 200 sin auth"
      - "Dockerfile non-root, HEALTHCHECK, no privileged"
      - "maestro.yaml obligatorio"
      # ... lista completa segun core/PRESET_WEB_MAESTRO.md

  # --- Artefactos de fases anteriores (paths a archivos) ---
  artifacts:
    requirements: "framework-agentico/checkpoints/phases/01-requirements.md"
    architecture: "framework-agentico/checkpoints/phases/02-architecture.md"
    api_contracts: "framework-agentico/checkpoints/phases/02-api-contracts.md"
    data_model: "framework-agentico/checkpoints/phases/02-data-model.md"
    # ... solo incluir los que existen

  # --- Estado de Git ---
  git:
    repo: "github.com/org/repo"
    main_branch: "main"
    epic_branch: "epic/nombre-proyecto"
    milestone: { id: N, title: "Nombre" }
    open_issues:
      - { number: 10, title: "Modulo X", branch: "epic/.../modulo-x", status: "open" }
      - { number: 11, title: "Modulo Y", branch: "epic/.../modulo-y", status: "open" }

  # --- Agentes que el orquestador debe crear ---
  agents:
    - role: "nombre-del-rol"
      focus: "Descripcion de en que se enfoca"
      model_hint: "sonnet"           # sugerencia, el orquestador puede ajustar
    - role: "otro-rol"
      focus: "..."
      model_hint: "haiku"

  # --- Instrucciones especificas para esta fase ---
  instructions: |
    Instrucciones en lenguaje natural que el PM le da al orquestador.
    Incluye: que hacer, en que orden, criterios de exito, restricciones.

  # --- Feedback de rondas anteriores (si es retry) ---
  previous_feedback:
    - module: "Modulo X"
      issue: "Descripcion del problema"
      suggestion: "Como corregirlo"
```

---

## Output: Phase Result (Orquestador -> PM)

El orquestador devuelve este resultado al PM al finalizar. El PM lo usa para actualizar checkpoints y decidir el siguiente paso.

```yaml
phase_result:

  # --- Estado general ---
  meta:
    phase: "NN-nombre"
    status: "completed | completed_with_observations | blocked"
    modules_total: N
    modules_completed: N
    modules_blocked: N

  # --- Modulos completados ---
  completed:
    - module: "Nombre del modulo"
      issue_number: N
      pr_url: "https://github.com/org/repo/pull/N"
      verdict: "APPROVED"
      validators:
        code_review: "PASS"
        security: "PASS"
        qa: "PASS"
        performance: "PASS"
        compliance: "PASS"

  # --- Modulos bloqueados (si hay) ---
  blocked:
    - module: "Nombre del modulo"
      issue_number: N
      attempts: 3
      last_verdict: "REJECTED by {validador}"
      reason: "Descripcion del problema"
      suggested_options:
        - "Opcion A"
        - "Opcion B"

  # --- Decisiones tomadas durante la fase ---
  decisions_made:
    - "Descripcion de la decision y por que"

  # --- Estado de Git al finalizar ---
  git_state:
    branches_created: []
    branches_merged: []
    branches_pending: []
    prs_created: []
    prs_pending: []
    issues_closed: []
    issues_open: []
    milestones_created: []

  # --- Artefactos producidos (paths a archivos) ---
  artifacts_produced:
    - path: "ruta/al/archivo"
      description: "Que contiene"

  # --- Estimacion de costo (para el cost-analyst) ---
  cost_estimate:
    agent_calls: N
    files_read: N
    files_written: N
    estimated_complexity: "low | medium | high"

  # --- Escalaciones pendientes ---
  escalations:
    - type: "technical_blocker | decision_needed | conflict"
      description: "Descripcion del problema"
      options:
        - "Opcion A"
        - "Opcion B"
```

---

## Notas de Implementacion

### Como construir el Context Packet
El PM lee los archivos relevantes y construye el packet como texto en el prompt del Agent(). No es un archivo YAML literal — es una estructura que el PM redacta en lenguaje natural + estructura, adaptada al contexto.

### Como devolver el Phase Result
El orquestador incluye el phase result como la parte final de su respuesta al Agent() call. El PM lo parsea del resultado.

### Evolucion
El formato puede evolucionar por proyecto. Si un proyecto necesita campos adicionales (ej: regulatory_requirements, external_apis), el PM los agrega.
