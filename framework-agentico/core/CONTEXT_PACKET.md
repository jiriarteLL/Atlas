# Context Packet — Formato de Comunicacion entre PM y Orquestadores

> **Version:** 4.0
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
    project_id: "{repo-name}"          # nombre del repositorio de GitHub
    phase: "NN-nombre"              # ej: "03-development"
    branch: "epic/nombre-proyecto"  # rama Git activa para esta fase
    timestamp: "YYYY-MM-DDTHH:MM:SSZ"
    retry: 0                        # numero de reintento (0 = primera vez)

  # --- Paths del proyecto (para que el orquestador sepa donde escribir) ---
  project_paths:
    project_root: "framework-agentico/projects/{project-id}"
    branch_root: "framework-agentico/projects/{project-id}/branches/{sanitized-branch}"
    transactions_dir: "framework-agentico/projects/{project-id}/branches/{sanitized-branch}/transactions"
    cost_log: "framework-agentico/projects/{project-id}/branches/{sanitized-branch}/cost/COST_LOG.md"
    phases_dir: "framework-agentico/projects/{project-id}/branches/{sanitized-branch}/phases"
    templates_dir: "framework-agentico/core/templates"

  # --- Contexto del proyecto ---
  project:
    premise: "Descripcion completa de lo que se construye y para quien"
    stack:
      backend: "Framework / Lenguaje"
      frontend: "Framework / Lenguaje"
      database: "Motor / Version"
      infra: "Docker / Cloud / etc"
    preset_constraints:              # Web Maestro v4 (siempre presentes)
      - "Auth propia de la app: tablas users + roles + permissions; tokens propios (NO X-Auth-*)"
      - "Single-tenant fisico: NO filtrar queries por company_id"
      - "GET /health -> 200 sin auth"
      - "GET /maestro/branding -> 401 sin X-Maestro-Api-Key, 200 con api key valida"
      - "El Maestro NO inyecta headers X-Auth-*; abre URL en target=_blank"
      - "Dockerfile non-root, HEALTHCHECK, sin --privileged ni docker.sock"
      - "maestro.yaml obligatorio: auth_model: own, login_path, branding_url"
      - "Fase 05-seeding crea admin@llyasoc.com idempotente (password desde SUPERADMIN_INITIAL_PASSWORD)"
      - "ENV vars obligatorias: DATABASE_URL, MAESTRO_API_KEY, SUPERADMIN_INITIAL_PASSWORD, APP_KEY/JWT_SECRET"
      # ... lista completa segun core/PRESET_WEB_MAESTRO.md

  # --- Artefactos de fases anteriores (paths dentro del proyecto) ---
  # Nota: usar {sanitized-branch} (/ reemplazado por _) consistente con project_paths
  artifacts:
    requirements: "projects/{project-id}/branches/{sanitized-branch}/phases/01-requirements.md"
    architecture: "projects/{project-id}/branches/{sanitized-branch}/phases/02-architecture.md"
    api_contracts: "projects/{project-id}/branches/{sanitized-branch}/phases/02-api-contracts.md"
    data_model: "projects/{project-id}/branches/{sanitized-branch}/phases/02-data-model.md"
    # ... solo incluir los que existen, paths relativos a framework-agentico/

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
    project_id: "{project-id}"
    branch: "{branch-name}"
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
    branch_structures_created: []    # ramas para las que se creo estructura en projects/
    prs_created: []
    prs_pending: []
    issues_closed: []
    issues_open: []
    milestones_created: []

  # --- Artefactos producidos (paths a archivos) ---
  artifacts_produced:
    - path: "ruta/al/archivo"
      description: "Que contiene"

  # --- Transacciones escritas durante la fase ---
  transactions_written:
    count: N
    path: "projects/{project-id}/branches/{branch}/transactions/"
    files: []                        # lista de nombres de archivos de transaccion generados
    # Ejemplo: ["20260423T143022_03_backend-developer_dev-attempt-1.md", ...]

  # --- Desglose de costos por agente (auto-reporte obligatorio) ---
  cost_breakdown:

    # Reporte del orquestador mismo
    orchestrator_report:
      role: "orchestrator"
      model: "opus"
      phase: "NN-nombre"
      files_read: N
      files_written: N
      estimated_output_chars: N        # largo aproximado de la respuesta del orquestador
      sub_agents_launched: N           # cantidad de Agent() calls que hizo

    # Un agent_cost_report por cada Agent() call que el orquestador lanzo
    agent_reports:
      - role: "backend-developer"        # rol del agente
        model: "sonnet"                  # modelo usado
        phase: "NN-nombre"
        module: "modulo-auth"            # issue/modulo asociado
        attempt: 1                       # intento (1 = primera vez, 2+ = retry)
        is_retry: false
        retry_reason: null               # si es retry, motivo del fallo anterior
        model_escalated: false           # true si el modelo fue escalado por retry
        files_read: N
        files_written: N
        lines_of_code_produced: N
        estimated_output_chars: N

      - role: "code-reviewer"            # validador
        model: "sonnet"
        phase: "NN-nombre"
        module: "modulo-auth"
        attempt: 1                       # a que intento del modulo corresponde
        verdict: "PASS | FAIL"
        files_read: N
        files_written: 0
        estimated_output_chars: N

    # Registro de reintentos (solo si hubo al menos un retry)
    retry_log:
      - module: "modulo-auth"
        total_attempts: 3
        attempts:
          - attempt: 1
            developer: { model: "sonnet", estimated_output_chars: N }
            validators_launched: 5
            blocking_validator: "security-auditor"
            blocking_reason: "SQL injection en endpoint X"
          - attempt: 2
            developer: { model: "sonnet", estimated_output_chars: N }
            validators_launched: 5
            blocking_validator: null       # null = todos PASS
            blocking_reason: null
        model_escalations: 0              # cuantas veces se escalo el modelo
        total_agent_calls: 12             # developer + validators en todos los intentos

    # Totales de la fase
    phase_totals:
      total_agent_calls: N               # todos los Agent() calls de la fase
      total_retries: N                    # cantidad total de reintentos
      total_files_read: N
      total_files_written: N
      total_lines_of_code: N
      total_estimated_output_chars: N     # suma de todos los agentes + orquestador
      agents_by_role:                     # desglose por tipo de agente
        orchestration: { calls: 1, estimated_chars: N }
        development: { calls: N, estimated_chars: N }
        validation: { calls: N, estimated_chars: N }
        documentation: { calls: N, estimated_chars: N }

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
