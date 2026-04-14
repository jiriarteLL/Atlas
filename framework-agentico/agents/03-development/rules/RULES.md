# Reglas Fase 03 — Development

```yaml
reglas:
  - seguir estrictamente la arquitectura y patrones definidos en fase 02
  - seguir las convenciones de código definidas por el architect
  - cada módulo pasa por validación transversal antes de marcarse como completado
  - no modificar API contracts sin aprobación del orquestador de fase
  - no modificar el modelo de datos sin aprobación del data-architect (via orquestador)
  - tests unitarios obligatorios para toda lógica de negocio
  - manejo de errores siguiendo la estrategia definida en fase 02
  - no hardcodear secrets, URLs, ni configuración específica de ambiente
  - usar variables de entorno para toda configuración externa
  - commits siguiendo la convención definida (conventional commits recomendado)
  - máximo 3 iteraciones de corrección por módulo antes de escalar

si_preset_web_maestro:
  - implementar middleware de auth que lea headers X-Auth-*
  - rechazar 401 si faltan headers de auth
  - filtrar TODA query de BD por company_id
  - implementar GET /health sin auth que retorne {"status":"ok"}
  - implementar endpoints de hooks SIN middleware de auth
  - verificar X-Maestro-Webhook-Secret en hooks
  - NO crear tabla users ni sessions
  - NO implementar login/registro
  - NO almacenar tokens de usuario
  - usar DATABASE_URL del environment para conexión a BD
```
