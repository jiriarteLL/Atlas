# Template de Validacion Transversal

> **Proposito:** Instrucciones que cada orquestador de fase incluye para ejecutar validacion transversal.
> **Uso:** El orquestador de fase lee este archivo y ejecuta las instrucciones despues de cada entregable.

---

## Instrucciones para el Orquestador

```
VALIDACION TRANSVERSAL — Instrucciones

REGLAS: Lee y cumplí framework-agentico/core/RULES.md seccion validacion_transversal.

Despues de cada entregable (modulo, componente, configuracion), ejecuta esta validacion:

1. LANZA TODOS LOS VALIDADORES EN PARALELO:

   Agent({
     description: "Code review - {modulo}",
     model: "sonnet",  // o superior si la complejidad lo amerita
     prompt: "[Incluir template de validation/validators/code-reviewer.md]
              Codigo a revisar: [branch o path]
              Stack: {stack}
              Constraints: {preset_constraints}"
   })

   Agent({
     description: "Security audit - {modulo}",
     model: "sonnet",
     prompt: "[Incluir template de validation/validators/security-auditor.md]
              Codigo a auditar: [branch o path]
              Stack: {stack}
              Constraints: {preset_constraints}"
   })

   Agent({
     description: "QA testing - {modulo}",
     model: "sonnet",
     prompt: "[Incluir template de validation/validators/qa-tester.md]
              Codigo a testear: [branch o path]
              Stack: {stack}
              Constraints: {preset_constraints}"
   })

   Agent({
     description: "Performance analysis - {modulo}",
     model: "haiku",  // subir a sonnet si hay queries complejos
     prompt: "[Incluir template de validation/validators/performance-analyst.md]
              Codigo a analizar: [branch o path]
              Stack: {stack}
              Constraints: {preset_constraints}"
   })

   Agent({
     description: "Compliance check - {modulo}",
     model: "haiku",  // subir a sonnet si hay regulaciones complejas
     prompt: "[Incluir template de validation/validators/compliance-analyst.md]
              Codigo a verificar: [branch o path]
              Stack: {stack}
              Constraints: {preset_constraints}"
   })

   // + validadores adicionales si el PM los definio en el context packet

2. RECOLECTA RESULTADOS:
   Cada validador devuelve:
   - verdict: PASS | FAIL | N/A
   - findings: lista de hallazgos (si hay)
   - severity: CRITICAL | HIGH | MEDIUM | LOW (si hay findings)
   - recommendation: que corregir (si FAIL)

3. CONSOLIDA VEREDICTO:
   - Si TODOS son PASS: veredicto = APPROVED
   - Si alguno es FAIL: veredicto = REJECTED
   - Si alguno es N/A: justifica y consulta al PM si es necesario
   - Si hay findings MEDIUM/LOW pero ningun FAIL: veredicto = APPROVED_WITH_OBSERVATIONS

4. SI REJECTED:
   - Identifica que validador rechazo y por que.
   - Construye feedback especifico para el developer.
   - Relanza developer con el feedback (max 3 intentos).
   - Si despues de 3 intentos sigue rechazado, agrega a escalations.

5. SI APPROVED:
   - Crea PR issue-branch -> epic-branch.
   - Lanza Agent(documentation-writer, haiku) para documentar post-aprobacion.
   - Cierra el issue en GitHub.

MODELO DINAMICO PARA VALIDADORES:
- Default: sonnet para code-review y security, haiku para performance y compliance.
- Si el modulo es critico (auth, pagos, datos sensibles): subir TODOS a sonnet o opus.
- Si el modulo es trivial (config, README): bajar TODOS a haiku.
```
