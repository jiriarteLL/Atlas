# MONITORING.md — Maestro Platform V1

> **Fase:** 05-operations
> **Versión:** v1.0.0-rc.1
> **Fecha:** 2026-04-18

---

## 1. Stack de observabilidad

| Componente | Rol | Puerto interno | Expuesto en prod |
|---|---|---|---|
| **Prometheus** v3.1.0 | Time-series metrics | 9090 | No — solo red interna |
| **Grafana** 11.4.0 | UI dashboards + alertas | 3000 | Sí — `grafana.<dominio>` vía Traefik ForwardAuth |
| **Loki** 3.3.2 | Agregación de logs | 3100 | No — solo red interna |
| **Promtail** 3.3.2 | Tail de logs de containers → Loki | — | No |
| **cAdvisor** v0.51.0 | Métricas por container (CPU/mem/net) | 8080 | No |
| **Node Exporter** v1.8.2 | Métricas del host (VPS) | 9100 | No |

Se levanta con: `docker compose -f docker-compose.obs.yml --env-file .env.production up -d`.
Retención Prometheus: 30 días. Loki: 30 días (config default).

## 2. Métricas configuradas

### 2.1 Infraestructura (cAdvisor)

| Métrica | Qué mide | Fuente |
|---|---|---|
| `container_cpu_usage_seconds_total` | CPU por container | cAdvisor |
| `container_memory_working_set_bytes` | Memoria usada | cAdvisor |
| `container_spec_memory_limit_bytes` | Memoria límite | cAdvisor |
| `container_network_receive_bytes_total` | Bytes red in | cAdvisor |
| `container_network_transmit_bytes_total` | Bytes red out | cAdvisor |
| `container_start_time_seconds` | Inicio último reinicio | cAdvisor |
| `container_last_seen` | Último heartbeat | cAdvisor |

### 2.2 Host (node-exporter)

| Métrica | Qué mide |
|---|---|
| `node_filesystem_avail_bytes` | Espacio disponible en disco |
| `node_memory_MemAvailable_bytes` | Memoria disponible |
| `node_load5` | Load average 5 min |
| `node_cpu_seconds_total` | Uso de CPU total |

### 2.3 Aplicación (pendiente — deuda V1.1)

El endpoint `/metrics` del Maestro API no está expuesto en V1. Cuando se agregue (deuda TD-015 en `TECH_DEBT.md`, usando `promphpclient/prometheus-client-php` o `unisharp/laravel-prometheus`):

| Métrica propuesta | Tipo |
|---|---|
| `maestro_http_requests_total{route, method, status}` | Counter |
| `maestro_http_request_duration_seconds{route, method}` | Histogram (p50, p95, p99) |
| `maestro_forward_auth_duration_seconds` | Histogram (SLO <50ms p95) |
| `maestro_queue_jobs_pending{queue}` | Gauge |
| `maestro_queue_jobs_failed_total{queue}` | Counter |
| `maestro_instances_status_total{status}` | Gauge (healthy/degraded/destroyed) |
| `maestro_hooks_delivery_total{status}` | Counter |
| `maestro_provisioning_duration_seconds` | Histogram |
| `maestro_active_companies_total` | Gauge |
| `maestro_active_users_total` | Gauge |

### 2.4 Traefik

Traefik expone `/metrics` (Prometheus) en `:8082` si se activa `metrics.prometheus` en `traefik.yml`. **Pendiente verificar en prod** (deuda TD-010).

## 3. Alertas configuradas

Archivo: `docker/observability/prometheus/alerts/maestro.yml`.
V1 usa Grafana Alerting (no Alertmanager) — canales en `Contact Points` de Grafana.

### 3.1 Alertas activas

| Alerta | Severidad | Trigger | Runbook |
|---|---|---|---|
| `MaestroContainerDown` | SEV1 | container no visto en >2 min | RUNBOOK.md §6.1 |
| `MaestroContainerMemoryHigh` | SEV2 | memoria >80% x10 min | RUNBOOK.md §6.2 |
| `MaestroContainerCPUHigh` | SEV3 | CPU >90% x15 min | RUNBOOK.md §6.3 |
| `MaestroContainerRestarting` | SEV2 | restart en últimos 15 min | RUNBOOK.md §6.4 |
| `HostDiskAlmostFull` | SEV1 | disco root >85% x5 min | RUNBOOK.md §6.5 |
| `HostDiskGrowthFast` | SEV3 | predicción linear <24h a 0 | RUNBOOK.md §6.5 |
| `HostMemoryHigh` | SEV2 | memoria host >90% x10 min | RUNBOOK.md §6.6 |
| `HostLoadHigh` | SEV3 | load5 >1.5x cores x15 min | RUNBOOK.md §6.3 |
| `PrometheusTargetDown` | SEV2 | scrape up=0 x5 min | RUNBOOK.md §6.7 |
| `MaestroAPIMetricsMissing` | SEV3 | informativa hasta deuda V1.1 | — |

### 3.2 Alertas de negocio pendientes (deuda V1.1)

Requieren endpoint `/metrics` en la app:
- `ForwardAuthP95Breach`: ForwardAuth p95 > 50ms x10 min (SLO DEC-017)
- `HighErrorRate`: tasa 5xx > 5% x5 min
- `QueueBacklog`: pending jobs > 1000 x15 min
- `FailedJobsSpike`: failed jobs rate > 5/min
- `InstanceUnhealthy`: instancia huésped en status=unhealthy >10 min
- `HookDeliveryFailureRate`: hooks fallidos > 10% x10 min

## 4. Dashboards

Ubicación: `docker/observability/grafana/dashboards/`. Provisionados automáticamente por Grafana (`/etc/grafana/provisioning/dashboards/`).

| Dashboard | Archivo | Qué muestra |
|---|---|---|
| **Maestro Overview** | `maestro-overview.json` (existe) | Estado global: containers up, CPU/mem/net por servicio, disk host |

### Dashboards recomendados (deuda V1.1)

- `maestro-api.json`: métricas del API (latencia p50/p95/p99 por endpoint, tasa errores, requests/s)
- `maestro-queues.json`: jobs pendientes, tasa de procesamiento, failed jobs, backoff
- `maestro-tenants.json`: uso por company (queries, instancias, hooks)
- `maestro-security.json`: login failures, rate limiting, auth denegadas

## 5. Logs

### 5.1 Formato

- **Laravel** loguea a `stderr` (channel `stderr` en `.env.production`) — capturado por Docker y Promtail.
- **Formato recomendado:** JSON estructurado. V1 usa el default de Laravel (line-based). **Deuda TD-011:** migrar a `Monolog\Formatter\JsonFormatter` para parsing robusto.
- **Niveles:** V1 prod = `LOG_LEVEL=warning` (warning+error+critical). Nunca `debug` en prod.

### 5.2 Labels de Loki

Promtail taggea cada log con:
- `container_name`
- `image`
- `stream` (stdout/stderr)
- `compose_project`: `maestro`

### 5.3 Reglas estrictas

- **NUNCA loguear:** passwords, tokens (JWT, Passport secrets, `X-Maestro-App-Secret`), webhook secrets, contenido de `X-Auth-*` headers, DB passwords de instancias huésped, tarjetas, documentos personales.
- **SIEMPRE incluir:** `company_id`, `user_id`, `request_id` (ULID `req_01K...`), ruta, método, status HTTP, duración.
- **Audit log va a BD, no a logs de app** — los `audit_log` son INSERT-only en PostgreSQL, no en stdout.

### 5.4 Retención

Loki: 30 días por defecto (configurable en `loki-config.yml`). Para cumplimiento GDPR (DEC-019), si algún log contiene datos personales involuntariamente, debe purgarse en el ciclo mensual.

## 6. Tracing

**Fuera de alcance V1** (DEC-020, escala baja). Si V2+ requiere trazas distribuidas entre apps huésped y Maestro, evaluar OpenTelemetry + Tempo (Grafana stack).

## 7. Cómo acceder

| Interfaz | URL dev | URL prod |
|---|---|---|
| Grafana | `https://grafana.maestro.local` | `https://grafana.<dominio>` (ForwardAuth Maestro) |
| Prometheus | `docker exec obs-prometheus wget -q -O- localhost:9090/-/ready` | idem |
| Loki | query vía Grafana Explore → datasource Loki | idem |

Grafana admin inicial: usuario `admin`, password en `.env.production` → `GRAFANA_ADMIN_PASSWORD`.

## 8. Escalabilidad V2+

Cuando la escala supere DEC-017 (1 empresa × 7 apps):
- Migrar a Alertmanager dedicado para ruteo y deduplicación
- Agregar Tempo para tracing distribuido
- Considerar Thanos o Mimir si retention >30d
- SIEM centralizado (deuda SOC2 TD-008)
