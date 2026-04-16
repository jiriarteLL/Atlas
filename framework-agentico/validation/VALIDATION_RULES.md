# Formato de Resultado de Validacion

> **Reglas de validacion:** Ver `framework-agentico/core/RULES.md` seccion `validacion_transversal`.
> Este archivo solo define el formato de resultado que cada validador debe devolver.

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
