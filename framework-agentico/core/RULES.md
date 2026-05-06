# Reglas Generales del Framework v4

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
    - Si el repo es un fork: el PM DEBE identificar las ramas que existen en el repositorio base (upstream) y registrarlas en el PROJECT.md del proyecto.

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
  - El PM registra la variante seleccionada y su compatibilidad en el PROJECT.md del proyecto.

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
  - Los agentes determinados se registran en el PROJECT.md del proyecto.

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
      1. checkpoints/GLOBAL.md tiene active_project: null (no hay proyecto activo)
      2. NO existe directorio projects/{repo-name}/ para este repositorio
      3. EXISTE codigo funcional en el repositorio mas alla de los archivos del framework
    - Si las 3 condiciones se cumplen, el PM DEBE entrar en modo sincronizacion ANTES de cualquier otra accion.
    - El PM crea la estructura de proyecto (ver seccion aislamiento_por_proyecto) y luego informa al Project Owner que detecto un proyecto con avance previo.

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
      - El PM marca la fase con status "verified_by_analysis" en PROJECT.md.
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
    - Despues de la sincronizacion, el PM actualiza PROJECT.md con el estado real, registra el proyecto en checkpoints/GLOBAL.md, y continua el flujo normal desde la primera fase pendiente.

  registro_en_project:
    - Cada fase sincronizada se registra en PROJECT.md seccion phases_status con:
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

  - El PM mantiene PROJECT.md del proyecto activo actualizado despues de cada cambio de estado.
  - El PM mantiene checkpoints/GLOBAL.md (indice de proyectos) sincronizado.
  - Cada fase puede generar artefactos en branches/{rama}/phases/.
  - Al reanudar una sesion, el PM verifica GLOBAL.md para identificar el proyecto activo, luego carga su PROJECT.md.
  - Si hay proyecto in_progress o interrupted: preguntar al humano si retomar o iniciar nuevo.

# ============================================================
# 11. MONITOREO DE COSTOS Y AUTO-REPORTE
# ============================================================
monitoreo_de_costos:
  scope: >
    Los costos se registran a nivel de RAMA, se agregan a nivel de PROYECTO, y se indexan en GLOBAL.
    Nunca se escribe un costo en un lugar global — siempre fluye de rama -> proyecto -> indice.
  flujo:
    - Cada agente auto-reporta en su respuesta (agent_cost_report).
    - El orquestador recolecta y genera transacciones en branches/{rama}/transactions/.
    - El cost-analyst post-fase escribe en branches/{rama}/cost/COST_LOG.md.
    - El cost-analyst hace rollup a projects/{id}/cost/SUMMARY.md.
    - El PM actualiza checkpoints/GLOBAL.md con el total del proyecto.
  - Tabla de precios en cost/PRICING.md (referencia global, no se duplica por proyecto).
  - Historicos NO se recalculan si el pricing cambia.
  - No hay limite de presupuesto pero se monitorea para determinar estrategias futuras.
  - Metricas de eficiencia: tokens/respuesta, cache hit rate, tokens/LOC, costo por retry.

  auto_reporte_obligatorio:
    descripcion: >
      Cada actor del framework DEBE incluir un bloque de auto-reporte en su respuesta.
      Esto aplica a TODOS los niveles: PM, orquestadores, developers, validadores y agentes de soporte.
      El auto-reporte es la UNICA fuente de datos de consumo, ya que Claude Code no expone
      metricas de tokens por Agent() call al caller.

    regla_general: >
      Todo Agent() call DEBE incluir al final de su respuesta un bloque agent_cost_report
      con el formato definido en core/CONTEXT_PACKET.md seccion cost_breakdown.
      Omitir el auto-reporte es una violacion de reglas equivalente a omitir validacion.

    estimacion_de_tokens: >
      Como los agentes no tienen acceso a sus contadores de tokens reales, se usa la
      convencion de proxy: estimated_output_chars (largo de la respuesta en caracteres).
      El cost-analyst convierte a tokens estimados con la formula: chars / 4 = tokens aprox.
      Input tokens se estiman por: cantidad de archivos leidos * promedio de chars por archivo.

    por_nivel:
      pm:
        - El PM registra CADA interaccion como transaccion de tipo pm_interaction en la rama correspondiente.
        - Si la interaccion no esta asociada a una rama especifica, se escribe en la rama epic principal.
        - El PM tambien escribe en branches/{rama}/cost/COST_LOG.md seccion pm_interactions.
        - Campos: timestamp, tipo (query/estado/reporte/orquestar/planificar/ad_hoc), estimated_output_chars.
        - Las interacciones del PM se registran con modelo "opus".

      orquestador:
        - El orquestador incluye orchestrator_report en el Phase Result.
        - El orquestador RECOLECTA todos los agent_cost_report de sus sub-agentes.
        - El orquestador ESCRIBE una transaccion por cada agent_cost_report en branches/{rama}/transactions/.
        - El orquestador construye el retry_log si hubo reintentos.
        - El orquestador calcula los phase_totals antes de devolver el Phase Result.

      developer:
        - Cada developer incluye agent_cost_report al final de su respuesta.
        - Campos obligatorios: role, model, module, attempt, files_read, files_written, lines_of_code_produced, estimated_output_chars.
        - Si es retry: is_retry=true, retry_reason con el motivo del fallo anterior, model_escalated si aplica.
        - El developer NO escribe transacciones directamente — el orquestador las persiste.

      validador:
        - Cada validador incluye agent_cost_report al final de su respuesta.
        - Campos obligatorios: role, model, module, attempt (del modulo), verdict, files_read, estimated_output_chars.
        - El validador NO escribe transacciones directamente — el orquestador las persiste.

      agentes_de_soporte:
        - cost-analyst, documentation-writer, sync-analyzer: incluyen agent_cost_report.
        - El cost-analyst escribe en branches/{rama}/cost/COST_LOG.md y hace rollup a projects/{id}/cost/SUMMARY.md.
        - El cost-analyst se auto-registra como transaccion de tipo cost_analysis.

    reintentos:
      - El costo de reintentos se trackea por rama en branches/{rama}/cost/COST_LOG.md.
      - Cada reintento genera transacciones individuales por agente (developer + validators del intento).
      - El retry_log en el Phase Result agrupa todos los intentos por modulo.
      - Se registra: cuantos intentos, que validador bloqueo, si hubo escalamiento de modelo.
      - Metrica clave: retry_cost_ratio = costo de reintentos / costo total de la fase.

    interaccion_usuario:
      - Toda interaccion PM <-> usuario consume tokens de opus (el modelo mas caro).
      - El PM categoriza cada interaccion: query, estado, reporte, orquestar, planificar, ad_hoc.
      - Se registran como transacciones en la rama correspondiente + en su COST_LOG.
      - Metrica clave: pm_overhead_ratio = costo PM interactions / costo total del proyecto.

# ============================================================
# 12. CIERRE DE PROYECTO
# ============================================================
cierre_de_proyecto:
  - El PM verifica que TODOS los issues esten cerrados en GitHub.
  - El PM reporta al humano lo que no se pudo resolver.
  - SOLO EL PM crea y mergea el PR final epic -> main.
  - El PM lanza documentation-writer para consolidar documentacion.
  - El PM lanza cost-analyst para metricas finales del proyecto.
  - El PM lanza transaction-compactor (haiku) para compactar transacciones (ver seccion memorias_transaccionales.compactacion).
  - El PM genera reporte ejecutivo (o lo delega a un Agent).
  - El PM cierra el proyecto en PROJECT.md con status "completed".
  - El PM actualiza checkpoints/GLOBAL.md (indice de proyectos).

# ============================================================
# 13. MEMORIAS TRANSACCIONALES
# ============================================================
memorias_transaccionales:
  descripcion: >
    Cada operacion del framework genera un registro transaccional inmutable.
    Las transacciones se organizan jerarquicamente: Proyecto > Rama > Fase > Agente > Operacion.
    Esto permite trazabilidad completa, evita colisiones entre proyectos/ramas concurrentes,
    y habilita analisis post-mortem por cualquier dimension.

  jerarquia:
    proyecto:
      - Cada proyecto tiene su directorio en framework-agentico/projects/{project-id}/.
      - El project-id es el nombre del repositorio de GitHub.
      - El PROJECT.md contiene el estado global del proyecto (ex GLOBAL.md).
      - El cost/SUMMARY.md agrega costos de todas las ramas (rollup).
    rama:
      - Cada rama Git (epic, issue, worktree) tiene su subdirectorio en branches/{sanitized-name}/.
      - Nombres sanitizados: reemplazar "/" por "_" (ej: "epic/mi-app" -> "epic_mi-app").
      - Cada rama tiene: BRANCH.md, cost/COST_LOG.md, phases/, transactions/.
      - Las ramas worktree tambien se trackean (son efimeras pero generan transacciones).
    fase:
      - Los artefactos de fase se guardan en branches/{rama}/phases/{NN}-{nombre}.md.
      - Las transacciones de una fase comparten el campo phase en su registro.
    agente:
      - Cada agente genera transacciones con su role y model registrados.
      - Un agente puede generar multiples transacciones en una misma fase (ej: developer con reintentos).
    operacion:
      - Es la unidad atomica. Cada Agent() call = 1 operacion = 1 transaccion.
      - Tipos: development, validation, retry, escalation, pm_interaction, cost_analysis, documentation, orchestration.

  formato:
    - Cada transaccion es un archivo .md en branches/{rama}/transactions/.
    - Nombre: {timestamp}_{phase}_{agent-role}_{operation-name}.md
    - Ejemplo: 20260423T143022_03-development_backend-developer_dev-attempt-1.md
    - El formato interno sigue core/templates/TRANSACTION_TEMPLATE.md.

  inmutabilidad:
    - Una transaccion NUNCA se edita una vez escrita.
    - Si hay correccion, se crea una nueva transaccion con correction_of apuntando a la original.
    - Esto garantiza un audit trail completo e integro.

  quien_escribe:
    pm:
      - El PM escribe transacciones de tipo pm_interaction directamente en la rama correspondiente.
      - Si la interaccion es general (no asociada a rama), se escribe en la rama epic principal.
    orquestador:
      - El orquestador escribe su propia transaccion de tipo orchestration.
      - El orquestador recolecta los agent_cost_report de sub-agentes y escribe transacciones por cada uno.
      - Los developers y validadores NO escriben transacciones directamente — reportan via agent_cost_report al orquestador, y el orquestador persiste.
    cost_analyst:
      - El cost-analyst escribe su propia transaccion de tipo cost_analysis.
      - Ademas actualiza cost/COST_LOG.md de la rama y cost/SUMMARY.md del proyecto.

  trazabilidad:
    - Cada transaccion tiene un bloque trace con:
      - triggered_by: quien lanzo este agente
      - parent_transaction: TXN-id de la transaccion que origino esta
      - next_action: que deberia pasar despues (informativo)
      - correction_of: si corrige otra transaccion
    - Esto forma una cadena de causalidad que permite reconstruir el flujo completo.

  compactacion:
    - Las transacciones se mantienen como archivos individuales durante la vida del proyecto.
    - Al CERRAR el proyecto (seccion cierre_de_proyecto), el PM lanza:
      Agent({
        description: "Transaction compactor",
        model: "haiku",
        prompt: "Compacta las transacciones del proyecto."
      })
    - El compactador:
      1. Lee TODAS las transacciones de TODAS las ramas.
      2. Genera un archivo COMPACTED_TRANSACTIONS.md por rama con todas las transacciones en formato tabla.
      3. Elimina los archivos .md individuales de transactions/.
      4. El COMPACTED_TRANSACTIONS.md queda como registro historico permanente.
    - NUNCA se compacta un proyecto con status != "completed".

# ============================================================
# 14. AISLAMIENTO POR PROYECTO
# ============================================================
aislamiento_por_proyecto:
  descripcion: >
    Cada proyecto opera en su propio espacio dentro de framework-agentico/projects/.
    Esto evita colisiones entre proyectos concurrentes y permite tracking independiente.

  estructura:
    - Templates en core/templates/ (PROJECT, BRANCH, TRANSACTION, COST_LOG, COST_SUMMARY).
    - El PM instancia los templates al crear un nuevo proyecto.
    - checkpoints/GLOBAL.md es un INDICE de proyectos, no un checkpoint individual.

  creacion_de_proyecto:
    - El PM obtiene el project-id del nombre del repositorio de GitHub (gh repo view --json name).
    - El PM crea: projects/{project-id}/ con PROJECT.md, cost/SUMMARY.md.
    - Al crear la epic branch, el PM crea: projects/{project-id}/branches/epic_{name}/ con BRANCH.md, cost/COST_LOG.md, phases/, transactions/.
    - Al crear issue branches, el orquestador crea la estructura equivalente.

  rollup_de_costos:
    - Los costos se registran a nivel de RAMA (branches/{rama}/cost/COST_LOG.md).
    - El cost-analyst hace rollup de rama -> proyecto en projects/{id}/cost/SUMMARY.md.
    - El PM hace rollup de proyecto -> indice global en checkpoints/GLOBAL.md.
    - Cada nivel solo tiene AGREGADOS del nivel inferior, nunca entradas duplicadas.

  multi_proyecto:
    - checkpoints/GLOBAL.md lista todos los proyectos con: id, status, path, costo total.
    - Solo un proyecto puede estar in_progress a la vez (restriccion del framework single-PM).
    - Proyectos completed quedan como referencia historica.

# ============================================================
# 15. MIGRACION ENTRE VERSIONES DEL FRAMEWORK
# ============================================================
migracion_entre_versiones:
  descripcion: >
    El framework versiona cambios mayores. Las apps huesped (forks) pueden quedar
    atrasadas respecto a la version actual del framework. La migracion es LAZY:
    el PM detecta la version desactualizada al ejecutar /pm en un fork y ofrece migrar.

  alcance:
    - Aplica a CUALQUIER version anterior a la version actual del framework.
      Una app con framework v1, v2, v3 o cualquier version pre-v4 debe llevarse al estado v4.
    - La migracion NO modifica el codigo de la app. Solo actualiza los archivos del framework
      y produce un reporte de gaps en el codigo de la app que el PO puede resolver despues.

  deteccion_de_version:
    - El PM lee framework_version en framework-agentico/checkpoints/GLOBAL.md.
    - Compara contra la version target del framework (la que figura en este repo upstream).
    - Si la version local < version target: el PM entra en modo migracion ANTES de cualquier otra accion.

  flujo_lazy:
    - Cuando el PO ejecuta /pm en un fork con framework desactualizado:
      1. El PM informa la version detectada y la version target.
      2. El PM ofrece sincronizar el fork con upstream (modo HIBRIDO):
         a. Si el PO acepta y autoriza, el PM ejecuta `git fetch upstream && git merge upstream/{main_branch}`.
         b. Si el PO prefiere manual, el PM lista los pasos y espera a que el PO sincronice.
      3. Tras el sync, el PM relee framework_version en GLOBAL.md.
      4. Si la version local ahora es la target, el PM lanza:
         Agent({
           description: "Framework migrator v{old} -> v{target}",
           model: "opus",
           prompt: "Sos el framework-migrator. Lee framework-agentico/migration/migrator-template.md
           y ejecuta la migracion del proyecto local al estado v{target}.
           NO modifiques codigo de la app. Genera reporte de gaps."
         })
      5. El migrator devuelve un reporte de gaps. El PM se lo presenta al PO.
      6. El PO decide si abrir un nuevo trabajo (issue/branch) para corregir los gaps en el codigo.

  restricciones:
    - La migracion NO toca codigo de la app sin autorizacion explicita del PO.
    - La migracion preserva projects/ (estado del proyecto local).
    - Si el PO rechaza migrar, el PM advierte que NO puede operar bajo el preset v4 con framework anterior, y queda en modo solo-lectura hasta migrar.
    - El PM NUNCA hace force push ni reescribe historia de git.

  documentos_de_referencia:
    - framework-agentico/migration/v3-to-v4.md (proceso detallado v3 -> v4)
    - framework-agentico/migration/migrator-template.md (template del Agent migrator)
    - framework-agentico/CHANGELOG.md (cambios entre versiones)
```
