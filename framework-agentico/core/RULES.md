# Reglas Generales del Framework v2

> **FUENTE UNICA DE VERDAD** — Todas las reglas del framework estan en este archivo.
> **Aplican a:** PM, todos los orquestadores, todos los agentes, todos los niveles.
> **Enforcement:** CLAUDE.md fuerza la lectura de este archivo a todos los niveles.
> **Ningun otro archivo puede contradecir lo que dice este archivo.**

---

```yaml
# ============================================================
# 1. GOVERNANCE
# ============================================================
governance:
  - El humano es el Product Owner. Las prioridades de negocio siempre se escalan a el.
  - El PM es la conversacion persistente. No es un Agent() call.
  - Todo lo demas (orquestadores, developers, validadores) son Agent() calls reales con contexto aislado.
  - El PM no avanza de fase sin exit_criteria cumplidos en el checkpoint de la fase.
  - Si se invoca una fase directamente, el PM verifica que las anteriores esten completas.
  - El modo planificar nunca edita archivos ni ejecuta comandos.

  premisa:
    - Antes de activar cualquier fase, el PM DEBE entender el 100% de la premisa del proyecto.
    - El PM pregunta hasta eliminar toda ambiguedad: problema de negocio, usuarios, alcance, restricciones, calidad esperada.
    - NO se avanza hasta tener certeza total.

  escalamiento:
    - Cadena de escalamiento: agente -> orquestador de fase -> PM -> humano.
    - Si el PM puede resolverla con contexto del proyecto, responde directamente.
    - Si no puede, traslada al humano con: quien pregunta, por que, que impacto tiene, opciones.
    - Los orquestadores NUNCA contactan al humano directamente. Siempre pasan por el PM.

# ============================================================
# 2. GIT WORKFLOW
# ============================================================
git_workflow:
  prerequisitos:
    - Antes de iniciar CUALQUIER operacion Git, el PM DEBE verificar que el repositorio tenga Issues habilitados (gh repo view --json hasIssuesEnabled).
    - Si Issues NO esta habilitado: DETENER la ejecucion INMEDIATAMENTE. Informar al humano que debe activar Issues en Settings > General > Features. NO continuar hasta confirmacion.
    - Si el repo es un fork: el PM DEBE identificar las ramas que existen en el repositorio base (upstream) y registrarlas en checkpoints/GLOBAL.md.

  permisos_de_merge:
    - SOLO EL PM puede crear PRs y mergear hacia main. NADIE MAS.
    - SOLO EL PM puede crear PRs hacia ramas que existen en el repositorio base del fork (upstream branches). Esto protege la integridad del upstream.
    - Los orquestadores de fase pueden crear PRs y mergear UNICAMENTE hacia ramas intermedias (issue-branch -> epic-branch, o cualquier rama que NO sea main ni upstream).
    - Los developers NUNCA crean PRs ni mergean. Solo trabajan en worktrees.
    - Cualquier violacion de estos permisos es un error critico.

  flujo:
    - El PM crea la epic branch al iniciar proyecto.
    - Los orquestadores crean milestones, issues y sub-branches.
    - Los developers trabajan en worktrees aislados (isolation "worktree" en Agent()).
    - El orquestador mergea worktrees a issue branches.
    - Post-validacion transversal, el orquestador crea PR issue-branch -> epic-branch y lo mergea.
    - Los PRs se crean SOLO despues de validacion transversal aprobada.
    - Conflictos irresolubles se escalan al PM.
    - Al cerrar proyecto, SOLO EL PM crea y mergea el PR epic -> main.

  abm_responsabilidades:
    - Orquestadores: crean y administran Milestones e Issues. Actualizan estado al cerrar.
    - Developers: solo ABM de issues (actualizar estado, comentar). No crean milestones.
    - PM: revisa que todo este cerrado al final. Reporta lo pendiente al humano.

# ============================================================
# 3. PLANTILLA BASE
# ============================================================
plantilla_base:
  - La plantilla Tailwise Bundle (en "/Tailwise Bundle") es la PREFERIDA para iniciar cualquier proyecto.
  - Los agentes de desarrollo DEBEN usar esta plantilla como base salvo incompatibilidad tecnica comprobada.
  - Si existe incompatibilidad, DEBE documentarse como ADR con: que parte es incompatible, por que, y que alternativa se usa.
  - Variantes disponibles: Laravel, React, Vue, HTML. La seleccion depende del stack definido en planning.
  - El PM registra la variante seleccionada y su compatibilidad en checkpoints/GLOBAL.md.

# ============================================================
# 4. VALIDACION TRANSVERSAL
# ============================================================
validacion_transversal:
  validadores_minimos:
    - code-reviewer
    - security-auditor
    - qa-tester
    - performance-analyst
    - compliance-analyst
    - "El PM puede agregar mas segun el proyecto. NUNCA puede haber menos de estos 5."

  ejecucion:
    - Los validadores se lanzan EN PARALELO despues de cada entregable.
    - Cada validador es un Agent() call independiente.
    - Los templates de validadores en validation/validators/ son guias; el orquestador los adapta al contexto.

  veredicto:
    - TODOS los validadores deben devolver PASS para generar un PR.
    - Un solo FAIL bloquea el PR. Sin excepciones.
    - Si un validador devuelve N/A, el orquestador DEBE consultar al PM para validar la justificacion.
    - Vulnerabilidades CRITICAL/HIGH en security bloquean el avance sin excepcion.
    - Findings MEDIUM/LOW no bloquean pero se documentan como observaciones.

  reintentos:
    - Maximo 3 intentos de correccion por modulo.
    - En cada reintento, el feedback del validador se pasa al developer.
    - El orquestador puede escalar el modelo del developer (sonnet -> opus) en reintentos.
    - Despues de 3 fallos: escalar al PM con modulo, motivo, intentos y opciones. NO seguir intentando.

  post_aprobacion:
    - Despues de aprobar un entregable, el orquestador lanza documentation-writer para documentar.
    - La documentacion no es un gate de validacion; se genera post-aprobacion.

  modelo_por_complejidad:
    - haiku: validaciones de modulos triviales (config, README, scaffolding)
    - sonnet: validaciones estandar (default para code-review y security)
    - opus: modulos criticos (auth, pagos, datos sensibles, arquitectura core)

# ============================================================
# 5. CALIDAD CONTINUA
# ============================================================
calidad_continua:
  - Ningun artefacto de codigo avanza sin pasar por validacion transversal completa.
  - Toda decision arquitectonica se documenta como ADR con: contexto, decision, consecuencias.
  - El code review es obligatorio para todo artefacto textual (codigo, configuracion, IaC).

# ============================================================
# 6. AGENTES DINAMICOS
# ============================================================
agentes_dinamicos:
  - Los agentes se determinan cuando el PM entiende el problema, NO antes.
  - El PM decide que agentes necesita cada fase segun el stack y el problema.
  - El modelo de cada agente es dinamico segun complejidad:
    - haiku: tareas simples, validaciones rapidas, tareas mecanicas
    - sonnet: desarrollo estandar, reviews, testing
    - opus: PM, orquestadores, decisiones arquitectonicas, debugging profundo
  - El orquestador puede escalar el modelo de un agente si la tarea falla o es mas compleja de lo esperado.
  - Los agentes determinados se registran en checkpoints/GLOBAL.md.

# ============================================================
# 7. COMUNICACION
# ============================================================
comunicacion:
  - La comunicacion entre PM y orquestadores usa el Context Packet (ver core/CONTEXT_PACKET.md).
  - El PM envia un Context Packet completo a cada orquestador. El packet incluye SIEMPRE las constraints del preset Web Maestro.
  - Cada orquestador devuelve un Phase Result estructurado.
  - Los artefactos pesados se referencian como paths a archivos, no como contenido inline.
  - Los agentes dentro de una fase se comunican a traves de su orquestador.
  - Los agentes NUNCA se invocan directamente entre fases; siempre pasan por el PM.

# ============================================================
# 8. PRESET WEB MAESTRO
# ============================================================
preset_web_maestro:
  - SIEMPRE ACTIVO. Todas las aplicaciones corren en la plataforma Web Maestro.
  - Las constraints del preset se incluyen en CADA Context Packet.
  - Las constraints son NO NEGOCIABLES y aplican en TODAS las fases.
  - Ver core/PRESET_WEB_MAESTRO.md para la lista completa de constraints por fase.
  - Los validadores transversales DEBEN verificar cumplimiento del preset.

# ============================================================
# 9. SINCRONIZACION DE PROYECTO EXISTENTE
# ============================================================
sincronizacion_proyecto_existente:
  descripcion: >
    Cuando el PM detecta que existe codigo en el repositorio pero no hay archivos
    de seguimiento (checkpoints de fase), debe iniciar un analisis automatico para
    determinar que fases del framework ya estan cubiertas por el estado actual del codigo.

  deteccion_automatica:
    - Al iniciar cualquier modo (/pm, /pm:orquestar, /pm:planificar), el PM verifica:
      1. checkpoints/GLOBAL.md tiene status "not_started" o no tiene proyecto activo
      2. NO existen archivos en checkpoints/phases/
      3. EXISTE codigo funcional en el repositorio mas alla de los archivos del framework
    - Si las 3 condiciones se cumplen, el PM DEBE entrar en modo sincronizacion ANTES de cualquier otra accion.
    - El PM informa al Project Owner que detecto un proyecto con avance previo y que va a analizar el estado.

  flujo_de_sincronizacion:
    - El PM analiza el repositorio fase por fase, en orden (00 a 06).
    - Para CADA fase, el PM:
      1. Lee los exit_criteria del template de fase (phases/{NN}-{nombre}.md).
      2. Analiza el estado actual del repositorio contra cada criterio.
      3. Clasifica cada criterio como: CUMPLIDO, PARCIAL, o NO_CUMPLIDO.
      4. Presenta el resultado al Project Owner de forma interactiva.
      5. Espera confirmacion del Project Owner antes de avanzar a la siguiente fase.
    - El analisis puede usar Agent(sync-analyzer, sonnet) para inspeccionar el codigo si es necesario.

  clasificacion_de_fases:
    fase_cumplida:
      - TODOS los exit_criteria estan CUMPLIDOS.
      - El PM marca la fase con status "verified_by_analysis" en GLOBAL.md.
      - Se registra en completed_phases.
      - NO se generan los artefactos de checkpoint retroactivamente.
      - Se registra una nota indicando: "Fase verificada por analisis de proyecto existente. No posee artefactos de checkpoint."
    fase_incompleta:
      - Al menos un exit_criteria esta PARCIAL o NO_CUMPLIDO.
      - El PM lista los criterios faltantes al Project Owner.
      - El PM consulta al Project Owner como desea proceder:
        a) Resolver lo faltante antes de continuar (el PO lo resuelve manualmente o el PM lo incluye en la planificacion).
        b) Marcar la fase como incompleta y documentar las excepciones.
      - La fase queda en pending_phases hasta que el PO decida.
    fase_no_aplica:
      - Si una fase no tiene relevancia para el estado actual (ej: 06-retrospective en un proyecto en desarrollo), se omite del analisis.
      - El PM lo informa y sigue con la siguiente.

  restricciones:
    - La sincronizacion es SOLO LECTURA. No modifica codigo ni ejecuta comandos destructivos.
    - El PM NO asume cumplimiento. Si no puede verificar un criterio, lo marca como NO_CUMPLIDO.
    - El Project Owner tiene la ultima palabra sobre si un criterio se considera cumplido.
    - Despues de la sincronizacion, el PM actualiza GLOBAL.md con el estado real y continua el flujo normal desde la primera fase pendiente.

  registro_en_global:
    - Cada fase sincronizada se registra en phases_status con:
        status: "verified_by_analysis" | "incomplete_pre_existing"
        exit_criteria_met: true | false
        sync_date: "{fecha}"
        sync_notes: "{resumen de hallazgos}"
        missing_criteria: [] # lista de criterios faltantes si los hay

# ============================================================
# 10. CHECKPOINT
# ============================================================
checkpoint:
  estados_validos_de_fase:
    - "not_started"              # Fase no iniciada
    - "in_progress"              # Fase en ejecucion
    - "completed"                # Fase completada por el framework
    - "verified_by_analysis"     # Fase verificada por analisis de proyecto existente
    - "incomplete_pre_existing"  # Fase con avance parcial pre-existente, pendiente de resolucion
    - "skipped"                  # Fase omitida (con justificacion)

  - El PM mantiene checkpoints/GLOBAL.md actualizado despues de cada cambio de estado.
  - Cada fase puede generar artefactos en checkpoints/phases/.
  - Al reanudar una sesion, el PM verifica GLOBAL.md para determinar estado.
  - Si hay proyecto in_progress o interrupted: preguntar al humano si retomar o iniciar nuevo.

# ============================================================
# 11. MONITOREO DE COSTOS
# ============================================================
monitoreo_de_costos:
  - Despues de cada fase, el PM lanza Agent(cost-analyst, haiku) para registrar metricas.
  - El cost-analyst lee el JSONL de sesion y actualiza cost/COST_LOG.md y checkpoints/GLOBAL.md.
  - Los costos se registran en tokens (valor absoluto) y USD (valor estimado).
  - Tabla de precios en cost/PRICING.md. Historicos NO se recalculan si el pricing cambia.
  - No hay limite de presupuesto pero se monitorea para determinar estrategias futuras.
  - Metricas de eficiencia: tokens/respuesta, cache hit rate, tokens/LOC.

# ============================================================
# 12. CIERRE DE PROYECTO
# ============================================================
cierre_de_proyecto:
  - El PM verifica que TODOS los issues esten cerrados en GitHub.
  - El PM reporta al humano lo que no se pudo resolver.
  - SOLO EL PM crea y mergea el PR final epic -> main.
  - El PM lanza documentation-writer para consolidar documentacion.
  - El PM lanza cost-analyst para metricas finales.
  - El PM genera reporte ejecutivo (o lo delega a un Agent).
  - El PM cierra el proyecto en GLOBAL.md con status "completed".
```
