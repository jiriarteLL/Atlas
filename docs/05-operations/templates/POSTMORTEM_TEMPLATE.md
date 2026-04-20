# Postmortem — INC-YYYYMMDD-<slug>

> **Principio:** este postmortem es **blameless**. Busca mejorar el sistema, no asignar culpa.

## Información básica

| Campo | Valor |
|---|---|
| Incident ID | INC-YYYYMMDD-<slug> |
| Severidad | SEV1 / SEV2 / SEV3 |
| Inicio (UTC) | YYYY-MM-DD HH:MM |
| Detección (UTC) | YYYY-MM-DD HH:MM |
| Cierre (UTC) | YYYY-MM-DD HH:MM |
| Duración total | X h Y min |
| Tiempo de detección | X min (desde inicio hasta detección) |
| Tiempo de resolución | X min (desde detección hasta cierre) |
| Incident Commander | |
| Scribe | |
| Postmortem lead | |

## 1. Resumen ejecutivo

Breve descripción del incidente en 2-3 frases. ¿Qué falló, cuánto duró, qué impacto tuvo?

## 2. Impacto

- **Usuarios afectados:** X% de usuarios / empresas concretas
- **Apps huésped afectadas:** lista
- **Funcionalidades degradadas o caídas:** lista
- **Datos perdidos o corruptos:** si aplica, cantidad y alcance
- **Violación de SLO o compliance:** GDPR, SOC2, ForwardAuth p95, cold start

## 3. Timeline

Cronología detallada de eventos en UTC. Ejemplo:

| Hora (UTC) | Evento | Origen |
|---|---|---|
| 10:23 | Deploy v1.0.1 a VPS | CI/CD |
| 10:25 | Primera alerta `MaestroContainerRestarting` | Grafana |
| 10:28 | IC detecta alerta | Email |
| 10:30 | Triaje: SEV2 confirmado | IC |
| 10:35 | Contención: rollback a v1.0.0 disparado | IC |
| 10:42 | Sistema estable | Health check OK x3 |
| 10:42 | Incidente cerrado | IC |

## 4. Causa raíz

Aplicar **5 whys** o **fishbone**. Ejemplo:

1. ¿Por qué cayó la app? Migración DB corrupted índice X.
2. ¿Por qué la migración quedó a medias? Timeout en connection pool bajo carga.
3. ¿Por qué hubo timeout? Pool size no ajustado post-scale a 3 réplicas API.
4. ¿Por qué no se detectó antes? Falta alerta de `pg_stat_activity` waiting events.
5. ¿Por qué falta esa alerta? No estaba en MONITORING.md V1 (deuda V1.1).

**Causa raíz:** capacity planning del pool de conexiones de PG no acompañó el scaling horizontal del API.

## 5. Qué funcionó bien

- Rollback automatizado tomó <10 min
- Alerta de restart loop disparó rápido
- Backup previo estaba disponible y verificado

## 6. Qué no funcionó bien

- No había alerta de estado de conexiones PG en progreso
- Runbook no cubría este escenario específico
- Rollback requirió intervención manual (no es 1-click)

## 7. Por qué no fue peor

(Opcional pero útil: qué controles evitaron escalarlo a SEV1)

- El health check detectó el loop antes que los usuarios reportaran
- La DB del Maestro no sufrió datos corruptos porque la migración abortó antes del commit

## 8. Action items

Formato: owner, deadline, severidad (pasa a `tech-debt-manager`).

| # | Acción | Owner | Deadline | Severidad deuda |
|---|---|---|---|---|
| AI-1 | Agregar alerta `PgConnectionsWaiting` a MONITORING.md | observability-engineer | 2026-04-25 | HIGH |
| AI-2 | Actualizar RUNBOOK §6 con este escenario | incident-manager | 2026-04-22 | MEDIUM |
| AI-3 | Parametrizar `max_connections` de PG por # de réplicas API | devops-engineer | 2026-05-01 | HIGH |
| AI-4 | 1-click rollback script en `just rollback vX.Y.Z` | devops-engineer | 2026-05-15 | MEDIUM |

## 9. Lecciones aprendidas

Síntesis en 2-3 puntos clave:

- El scaling horizontal debe auditarse contra límites de recursos **compartidos** (DB connections, Redis clients, locks), no solo CPU/Memory del servicio escalado.
- Los runbooks deben actualizarse después de cada SEV ≥2, sin excepción.
- El rollback debería ser el primer reflejo, incluso antes de entender la causa raíz, cuando hay una versión estable anterior cercana.

## 10. Anexos

- Logs Loki: link a query o dump
- Métricas Grafana: screenshot o link
- Commits/PRs relacionados: lista
