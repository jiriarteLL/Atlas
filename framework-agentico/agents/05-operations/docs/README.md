# Documentación Fase 05 — Operations

## Templates de esta fase

### RUNBOOK.md
```markdown
# Runbook Operativo

## Información General
<!-- Nombre del sistema, versión, stack, contactos -->

## Arquitectura Resumida
<!-- Diagrama simplificado de componentes desplegados -->

## Procedimientos de Arranque y Parada
<!-- Cómo levantar y detener el sistema de forma segura -->

## Health Checks
<!-- Endpoints, frecuencia, qué significa cada estado -->

## Troubleshooting Común
<!-- Problema → Diagnóstico → Solución para los errores más frecuentes -->

## Escalamiento
<!-- Cómo escalar horizontal/verticalmente, límites conocidos -->

## Backup y Restauración
<!-- Procedimiento de backup de BD, volúmenes, frecuencia -->

## Contactos de Emergencia
<!-- Quién contactar según severidad del incidente -->
```

### MONITORING.md
```markdown
# Monitoreo y Observabilidad

## Métricas Configuradas
<!-- Lista de métricas con descripción y umbral -->

## Alertas Configuradas
<!-- Lista de alertas con condición, severidad y runbook asociado -->

## Dashboards
<!-- Descripción de dashboards disponibles, qué muestran -->

## Logs
<!-- Formato de logs, dónde se almacenan, cómo buscar -->

## Tracing
<!-- Si aplica, configuración de tracing distribuido -->
```

### INCIDENT_PLAYBOOK.md
```markdown
# Playbook de Incidentes

## Niveles de Severidad
<!-- SEV1 (crítico) a SEV4 (informativo), definición de cada uno -->

## Tiempos de Respuesta
<!-- Tiempo objetivo de respuesta y resolución por severidad -->

## Flujo de Respuesta
<!-- Pasos desde detección hasta resolución -->

## Comunicación
<!-- Canales, stakeholders a notificar por severidad -->

## Escalamiento
<!-- Cuándo y a quién escalar -->

## Postmortem
<!-- Template y proceso para postmortems blameless -->
```
