# Reglas de Validacion Transversal

> **Aplican a:** Todos los orquestadores de fase al ejecutar validacion

---

## Reglas Absolutas

```yaml
validadores_minimos_obligatorios:
  - code-reviewer
  - security-auditor
  - qa-tester
  - performance-analyst
  - compliance-analyst
  nota: "El PM puede agregar mas. Nunca puede haber menos de estos 5."

veredicto:
  - TODOS los validadores deben devolver PASS para generar un PR.
  - Un solo FAIL bloquea el PR.
  - N/A requiere justificacion y aprobacion del PM.
  - CRITICAL/HIGH en security bloquean sin excepcion.
  - Findings MEDIUM/LOW no bloquean pero se documentan.

reintentos:
  - Maximo 3 intentos de correccion por modulo.
  - En cada reintento, el feedback del validador se pasa al developer.
  - Si el modelo del developer es menor a opus, considerar escalarlo en el reintento.
  - Despues de 3 fallos, escalar al PM (NO seguir intentando).

escalamiento:
  - Si un validador devuelve N/A, el orquestador consulta al PM.
  - Si el PM valida que N/A es correcto, se acepta.
  - Si el PM no valida, el orquestador debe conseguir el PASS.
  - Dudas irresolubles se escalan al PM para que decida o pregunte al humano.

documentacion:
  - Post-aprobacion, lanzar documentation-writer para documentar el entregable.
  - La documentacion no es un gate — se genera despues de la aprobacion.

modelo_dinamico:
  - haiku: validaciones de modulos triviales (config, README, scaffolding)
  - sonnet: validaciones estandar (la mayoria de modulos)
  - opus: modulos criticos (auth, pagos, datos sensibles, arquitectura core)
  - El orquestador decide el modelo segun la complejidad del modulo.
```

---

## Formato de Resultado por Validador

Cada validador debe devolver su resultado en este formato:

```yaml
validator_result:
  validator: "nombre-del-validador"
  verdict: "PASS | FAIL | N/A"
  findings:
    - severity: "CRITICAL | HIGH | MEDIUM | LOW"
      description: "Descripcion del hallazgo"
      location: "archivo:linea o area general"
      recommendation: "Como corregirlo"
  summary: "Resumen en una linea del resultado"
```
