# Reglas Fase 02 — Planning

```yaml
reglas:
  - toda decisión arquitectónica debe documentarse como ADR con rationale y trade-offs
  - el stack se define una vez y se propaga; cambios posteriores requieren aprobación del PM
  - el modelo de datos debe soportar todos los requisitos funcionales de fase 01
  - los contratos de API se definen antes del desarrollo; cambios requieren versionado
  - las decisiones de auth, cifrado y gestión de secretos se definen aquí, no en desarrollo
  - la estrategia de error handling se define aquí (retry, circuit breaker, fallbacks, error codes)
  - la estrategia de branching y convención de commits se define aquí
  - la estrategia de i18n se define aquí si aplica
  - la estrategia de ambientes (local, dev, staging, prod) se define aquí
  - toda decisión debe ser coherente con las demás; contradicciones se resuelven antes de avanzar
  - las variables de entorno necesarias se identifican aquí

si_preset_web_maestro:
  - auth es por headers HTTP del Maestro, no negociable
  - NO crear tabla users ni sessions
  - el modelo de datos DEBE filtrar por company_id en toda consulta
  - los hooks del Maestro (on_user_added, on_user_removed, etc.) se diseñan como endpoints
  - la comunicación inter-apps va via gateway del Maestro
  - maestro.yaml se valida contra el schema, no se genera
  - resources.memory y resources.cpu deben ser coherentes con la carga esperada
```
