# Observabilidad y Monitoreo

> **Versión:** v4 (framework agéntico v4 / contrato `maestro.platform/v2`)
> **Última revisión:** 2026-05-07
> **Estado:** vigente
> **Reemplaza a:** `legacy/v3/PremisaWebMaestro/10-OBSERVABILIDAD.md` (modelo v1).

---

## Propósito de este documento

Este documento describe el stack de observabilidad de la **Web Maestro** v4: las métricas clave con sus umbrales, el sistema de alertas, los dashboards, la estrategia de logging centralizado y los runbooks operativos. Sin observabilidad, la plataforma es ingobernable: no se puede operar lo que no se puede ver.

Audiencia: equipos de plataforma, observability-engineers, agentes `observability-engineer` y `incident-manager`.

---

## Cambio respecto a v1

En v1 los logs y métricas incluían `company_id` (consecuencia de la multi-tenancy lógica). En v4, con single-tenant físico:

- Logs **NO** incluyen `company_id` en el contexto base. Cuando se loguea contexto de un deployment específico, se loguea `deployment_id` (que ya implica empresa+app).
- Métricas se agrupan por `deployment_id`, no por `company_id`.

El stack tecnológico (Prometheus + Loki + Grafana) se mantiene igual, ajustado a las nuevas métricas y filtros.

---

## Stack de observabilidad

### Componentes

| Componente | Rol | Despliegue |
|---|---|---|
| **Prometheus** | Métricas time-series | Contenedor `obs-prometheus` |
| **Promtail** | Agente de log shipping | Contenedor `obs-promtail` (lee logs de Docker) |
| **Loki** | Almacenamiento y búsqueda de logs | Contenedor `obs-loki` |
| **Grafana** | Dashboards y alertas | Contenedor `obs-grafana` |
| **cAdvisor** (opcional) | Métricas de contenedores | Contenedor `obs-cadvisor` |
| **node-exporter** | Métricas del host | Daemon en el VPS |
| **alertmanager** | Routing de alertas | Contenedor `obs-alertmanager` |

### Topología

```
┌───────────────────────────────────────────────────┐
│              maestro-net + obs-net                  │
│                                                     │
│  ┌──────────┐   ┌──────────┐   ┌──────────┐        │
│  │ maestro- │   │ deployment│   │ deployment│        │
│  │  api      │   │     A     │   │     B     │        │
│  └─────┬────┘   └─────┬────┘   └─────┬────┘        │
│        │              │              │              │
│        │ /metrics    │ stdout       │ stdout        │
│        │              │              │              │
│  ┌─────▼─────┐  ┌────▼────┐    ┌────▼────┐         │
│  │ prometheus│  │ promtail │    │ promtail │         │
│  │  scrape    │  └────┬────┘    └────┬────┘         │
│  └─────┬─────┘       │              │              │
│        │              └──────┬──────┘              │
│        │                     │                     │
│        │              ┌──────▼─────┐                │
│        │              │    loki     │                │
│        │              └──────┬─────┘                │
│        │                     │                     │
│  ┌─────▼─────────────────────▼─────┐               │
│  │             grafana             │               │
│  │   (dashboards + alertmanager)    │               │
│  └─────────────────────────────────┘               │
└───────────────────────────────────────────────────┘
```

### Acceso a Grafana

- Dominio: `grafana.<base_domain>` o subpath del Maestro.
- TLS terminado por Traefik.
- Auth: integración con login del Maestro (admins del Maestro pueden acceder a Grafana con su sesión).
- Permisos: `observability.read` para ver, `observability.admin` para configurar.

---

## Métricas clave

### Del Maestro mismo

| Métrica | Tipo | Etiquetas | Umbral verde | Umbral amarillo | Umbral rojo |
|---|---|---|---|---|---|
| `maestro_login_total` | counter | `result=success/failure/locked` | — | — | failure rate >5% |
| `maestro_login_failure_per_admin` | counter | `admin_id` | <3/h | 3-5/h | >5/h (bloqueo automático) |
| `maestro_api_request_duration_seconds` | histogram | `endpoint, method, status` | p95 <100ms | p95 100-300ms | p95 >300ms |
| `maestro_api_request_total` | counter | `endpoint, method, status` | — | — | 5xx rate >1% |
| `maestro_db_query_duration_seconds` | histogram | `query_type` | p95 <50ms | p95 50-200ms | p95 >200ms |
| `maestro_audit_log_writes_total` | counter | `action_category` | — | — | >100/min (sospechoso) |

### Del provisioning

| Métrica | Tipo | Etiquetas | Umbral verde | Umbral rojo |
|---|---|---|---|---|
| `maestro_deployment_provisioning_duration_seconds` | histogram | `application_id` | p95 <60s | p95 >120s |
| `maestro_deployment_provisioning_total` | counter | `result=success/failure` | — | failure rate >5% |
| `maestro_deployment_count` | gauge | `status` | — | `provisioning_failed` >0 |
| `maestro_deployment_destroy_total` | counter | — | — | spike inusual |

### Del consumo de branding

| Métrica | Tipo | Etiquetas | Umbral verde | Umbral rojo |
|---|---|---|---|---|
| `maestro_branding_fetch_total` | counter | `deployment_id, status=ok/unauthorized/timeout/server_error` | ok rate >95% | ok rate <90% |
| `maestro_branding_fetch_duration_seconds` | histogram | `deployment_id` (con cache) | p95 <50ms | p95 >200ms |
| `maestro_branding_consecutive_failures` | gauge | `deployment_id` | 0 | ≥3 (deployment marcado degraded) |

### De hooks salientes

| Métrica | Tipo | Etiquetas | Umbral verde | Umbral rojo |
|---|---|---|---|---|
| `maestro_hook_dispatch_total` | counter | `event_type, deployment_id, status=success/failed/retry/abandoned` | success rate >99% | success rate <95% |
| `maestro_hook_dispatch_duration_seconds` | histogram | `event_type` | p95 <2s | p95 >5s |
| `maestro_hook_signature_invalid_total` | counter | `deployment_id` | 0 | >0 (alerta crítica) |

### De los deployments (apps huésped)

| Métrica | Tipo | Etiquetas | Umbral verde | Umbral rojo |
|---|---|---|---|---|
| `app_health_check_status` | gauge | `deployment_id` | 1 (healthy) | 0 (unhealthy) |
| `app_health_check_consecutive_failures` | gauge | `deployment_id` | 0 | ≥10 (suspended) |
| `app_container_memory_usage_bytes` | gauge | `deployment_id` | <80% del límite | >95% del límite |
| `app_container_cpu_usage_percent` | gauge | `deployment_id` | <70% del límite | >90% del límite |
| `app_container_restart_total` | counter | `deployment_id, reason` | <1/día | >5/hora |

### De seguridad

| Métrica | Tipo | Umbral alerta |
|---|---|---|
| `maestro_admin_account_locked_total` | counter | >3 en 24h |
| `maestro_login_failure_total` (sin admin específico) | counter | >50/h global |
| `maestro_api_key_invalid_total` | counter (`/maestro/branding`) | >10/h por deployment |
| `maestro_webhook_signature_invalid_total` | counter | >0 (apps no validando firma) |
| `maestro_csrf_violation_total` | counter | >0 |

### De backup

| Métrica | Tipo | Umbral |
|---|---|---|
| `maestro_backup_success_total` | counter | (verificar daily ≥1) |
| `maestro_backup_failure_total` | counter | >0 (alerta crítica) |
| `maestro_backup_duration_seconds` | histogram | p95 <30min |
| `maestro_backup_size_bytes` | gauge | (monitorear crecimiento) |

---

## Logs estructurados

### Formato base

Todos los logs en JSON a stdout/stderr (los recoge Promtail → Loki):

```json
{
  "timestamp": "2026-05-07T14:30:22.123Z",
  "level": "info",
  "message": "deployment provisioning completed",
  "service": "maestro-api",
  "request_id": "uuid",
  "deployment_id": "uuid",
  "actor_user_id": "uuid",
  "duration_ms": 42500
}
```

**Campos comunes**:
- `timestamp` (ISO-8601 UTC con ms).
- `level` (`debug | info | warn | error | fatal`).
- `message` (string corto).
- `service` (`maestro-api`, `maestro-portal`, `maestro-provisioner`, `obs-*`).
- `request_id` (UUID por request HTTP, propagado entre servicios via header `X-Request-Id`).
- `deployment_id` (cuando aplique; identifica unívocamente app+empresa).
- `actor_user_id` (cuando aplique; admin del Maestro).
- `duration_ms` (en logs de operaciones).

### NO incluir en logs

- Passwords, hashes, JWTs propios.
- `MAESTRO_API_KEY`, `MAESTRO_WEBHOOK_SECRET`, `SUPERADMIN_INITIAL_PASSWORD`, `MAESTRO_ENCRYPTION_KEY`.
- Cookies de sesión completas, headers `Authorization`.
- Bodies de request con datos sensibles (PII, secretos).
- `company_id` del usuario final de las apps (artefacto v3 deprecado).

### Sampling

- Logs `debug` solo en development (filtrados en producción).
- Logs `info` muestreados al 10% para endpoints de alta frecuencia (ej: health checks).
- Logs `warn`, `error`, `fatal` siempre completos.

---

## Dashboards

### Dashboard 1: Ejecutivo del Maestro

Panel único, refresh 30s. Para C-Level y operaciones generales.

- Total de empresas activas.
- Total de applications registradas.
- Total de deployments por estado (gauge: healthy / degraded / suspended).
- Hooks success rate últimas 24h (gauge con umbrales).
- Branding fetch success rate últimas 24h.
- Backup status (semáforo verde/rojo).
- API uptime últimos 30 días (de Prometheus blackbox).
- Cost trend (si se integra con cost-analyst del framework agéntico).

### Dashboard 2: Salud de deployments

Lista de todos los deployments con detalle por fila:

- `deployment_id` + nombre del par app+empresa.
- Estado (color por status).
- CPU/memoria actual (% del límite).
- Health check status + último check.
- Branding fetch status + último fetch.
- Hooks last 24h (success/failed counts).

Filtros: por status, por empresa, por application. Click abre Dashboard 3.

### Dashboard 3: Detalle de un deployment

Para troubleshooting de un deployment específico.

- Métricas de container (CPU, memoria, network I/O, restart count) últimas 24h.
- Health check status timeline.
- Branding fetch timeline.
- Hooks dispatch timeline.
- Logs filtrados por `deployment_id` (vista Loki integrada).
- Audit log filtrado por `resource_id = deployment_id`.

### Dashboard 4: Performance del Maestro API

- Request rate por endpoint.
- Latencia p50/p95/p99 por endpoint.
- Error rate (4xx/5xx) por endpoint.
- DB query duration por query type.
- Cache hit rate (si Redis está activo).

### Dashboard 5: Seguridad

- Login attempts (success/failure/locked) últimas 24h.
- Bloqueos de cuenta.
- API key invalidations / rotations.
- Webhook signature failures.
- CSRF violations.
- Logs de seguridad recientes (filter `level >= warn`).
- Acciones críticas del audit log (action prefix `*.destroy`, `*.purge`, `password.change`, `role.granted`, `role.revoked`).

### Dashboard 6: Capacidad

- Uso CPU/memoria/disco del VPS.
- Tendencia de crecimiento (últimos 30 días).
- Proyección de capacidad (gráfica con línea de proyección lineal).
- Alertas: VPS con <20% disco libre, etc.

---

## Alertas

### Severidades

| Severidad | Acción | Canal |
|---|---|---|
| **CRITICAL** | Atención inmediata, llamada/SMS/Slack | PagerDuty + Slack #alerts-critical + email |
| **HIGH** | Atención en horario laboral | Slack #alerts-high + email |
| **MEDIUM** | Revisar próxima jornada | Slack #alerts-medium |
| **LOW** | Loguear, revisar en retrospectiva semanal | Solo log, sin notificación |

### Reglas de alerta clave

```yaml
# Ejemplo simplificado de reglas Prometheus

groups:
  - name: maestro_critical
    rules:
      - alert: MaestroAPIDown
        expr: up{job="maestro-api"} == 0
        for: 1m
        labels: { severity: critical }
        annotations:
          summary: "Maestro API is down"

      - alert: MaestroDBDown
        expr: up{job="maestro-db"} == 0
        for: 30s
        labels: { severity: critical }
        annotations:
          summary: "Maestro DB unreachable"

      - alert: MaestroBackupFailed
        expr: increase(maestro_backup_failure_total[1d]) > 0
        labels: { severity: critical }
        annotations:
          summary: "Backup failed in last 24h"

      - alert: TLSCertExpiringSoon
        expr: probe_ssl_earliest_cert_expiry - time() < 30 * 86400
        labels: { severity: high }
        annotations:
          summary: "TLS cert expires in less than 30 days"

      - alert: DeploymentSuspended
        expr: maestro_deployment_count{status="suspended"} > 0
        labels: { severity: high }
        annotations:
          summary: "{{ $labels.deployment_id }} is suspended"

      - alert: HighLoginFailureRate
        expr: rate(maestro_login_total{result="failure"}[5m]) > 0.5
        for: 5m
        labels: { severity: high }
        annotations:
          summary: "Possible bruteforce: login failures rate {{ $value }}/s"

      - alert: BrandingFetchFailing
        expr: maestro_branding_consecutive_failures >= 3
        labels: { severity: medium }
        annotations:
          summary: "Branding fetch failing for {{ $labels.deployment_id }}"

      - alert: HookDispatchFailureRate
        expr: rate(maestro_hook_dispatch_total{status="abandoned"}[1h]) > 0.01
        labels: { severity: medium }
        annotations:
          summary: "Hooks abandoned rate above 1%"

      - alert: VPSDiskLow
        expr: node_filesystem_avail_bytes / node_filesystem_size_bytes < 0.20
        labels: { severity: high }
        annotations:
          summary: "VPS disk usage above 80%"
```

---

## Runbooks operativos

Documentos paso-a-paso para incidentes comunes. Cada runbook tiene:

- **Síntoma**: lo que ve el operador (alerta, comportamiento del usuario).
- **Diagnóstico inicial**: comandos para verificar el estado.
- **Acciones correctivas**: pasos en orden, con condiciones.
- **Verificación post-acción**: cómo confirmar que se resolvió.
- **Escalation**: a quién contactar si no se resuelve.

### Runbooks mínimos a producir en fase 06-operations

1. **MaestroAPIDown**: Maestro API no responde.
2. **MaestroDBDown**: BD del Maestro caída.
3. **DeploymentNotResponding**: deployment health check falla repetidamente.
4. **DeploymentRestoreFromBackup**: restaurar deployment destruido.
5. **TLSCertNotRenewing**: cert TLS no renueva automáticamente.
6. **HighLoginFailureRate**: posible bruteforce contra login.
7. **BackupFailed**: backup diario falló.
8. **VPSDiskLow**: VPS sin espacio.
9. **APIKeyCompromised**: api_key filtrada o comprometida.
10. **WebhookSecretCompromised**: webhook_secret filtrado.
11. **AuditLogTamperingAttempt**: detección de intento de UPDATE/DELETE en audit_log.
12. **MigrationRollback**: rollback de una migración del Maestro fallida.

Estos runbooks se generan en la fase 06-operations del proyecto Maestro y se mantienen en `docs/runbook.md` (o split por tema en `docs/runbooks/`).

---

## Retención de datos de observabilidad

| Tipo | Retención |
|---|---|
| Métricas Prometheus | 30 días local + 1 año en cold storage (Thanos o equivalente) |
| Logs Loki | 14 días local + 90 días en cold storage |
| Audit log | Indefinido (parte del backup) |
| Hooks log | 90 días local |
| Dashboards | Versionados en git (Grafana provisioning) |

Cumplimiento con regulaciones (GDPR): logs con PII se anonimizan tras 90 días.

---

## Integración con cost-analyst del framework agéntico

El framework agéntico v4 (ver `framework-agentico/core/RULES.md` sección `monitoreo_de_costos`) registra costos por agente/Agent() call. Estos datos se pueden visualizar en un Dashboard 7: Costos del proyecto Maestro.

- Total cost USD acumulado por proyecto.
- Cost trend semanal/mensual.
- Distribución por fase (00-setup → 07-retrospective).
- Distribución por modelo (opus/sonnet/haiku).
- Retry cost ratio.
- PM overhead ratio.

---

## Referencias normativas

- `01-PREMISAS-Y-NO-NEGOCIABLES.md` — premisa 9 (observabilidad y recuperabilidad).
- `02-MODELO-DE-DATOS.md` — tabla `audit_log` y triggers de inmutabilidad.
- `04-INFRAESTRUCTURA-DOCKER.md` — health checks y máquina de estados de deployments.
- `09-SEGURIDAD.md` — métricas y alertas de seguridad.
- `framework-agentico/phases/06-operations.md` — fase de la cual surgen runbooks y dashboards.
- `framework-agentico/core/RULES.md` sección `monitoreo_de_costos` — auto-reporte de agentes.

---

## Historial de revisiones

| Versión | Fecha | Cambio |
|---|---|---|
| 4.0.0 | 2026-05-07 | Versión inicial v4. Stack Prometheus/Loki/Grafana adaptado a single-tenant físico (sin `company_id` en logs). Métricas centradas en deployments y registry. Reemplaza al v1 (legacy en `legacy/v3/PremisaWebMaestro/10-OBSERVABILIDAD.md`). |
