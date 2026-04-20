# TECH_DEBT.md — Maestro Platform V1

> **Fase:** 05-operations
> **Versión:** v1.0.0-rc.1
> **Fecha:** 2026-04-18
> **Responsable:** `tech-debt-manager` (Fase 05) + `executive-reporter` para priorización trimestral.

Inventario consolidado de deuda técnica del proyecto al cierre de V1. Fuentes:

1. Observaciones transversales Fase 03 iter 9 (code-reviewer, security-auditor, qa-tester, compliance-analyst).
2. Observaciones transversales Fase 04 Delivery.
3. Gaps identificados durante Fase 05 Operations (observability).
4. TODOs en el código.

Cada item tiene **ID estable** `TD-###`. No se reusan IDs de deuda resuelta.

---

## 1. Clasificación

| Severidad | Definición operativa | SLO de remediación |
|---|---|---|
| **CRITICAL** | Bloquea un release / hay riesgo legal o de seguridad inminente | Inmediata (no debería entrar aquí sin excepción) |
| **HIGH** | Aumenta materialmente riesgo de SEV1/SEV2 o viola compliance contratado | ≤ 1 mes |
| **MEDIUM** | Degrada operabilidad, testabilidad o costo; sin riesgo inmediato | ≤ 3 meses |
| **LOW** | Cosmético, estilístico, optimización | Oportunista |

V1 arranca **sin deuda CRITICAL**. Toda la deuda abajo es HIGH/MEDIUM/LOW.

---

## 2. Inventario de deuda

### 2.1 Seguridad & Compliance

| ID | Título | Severidad | Origen | SLO | Owner propuesto | Notas |
|---|---|---|---|---|---|---|
| TD-001 | Endpoint `POST /api/v1/gdpr/export` (derecho de acceso usuario) | HIGH | Fase 03 / compliance-analyst | 2026-07-31 | backend-developer | GDPR Art. 15. V1 cumple con borrado pero no con export self-service. Workaround: export manual por ticket. |
| TD-002 | Endpoint `DELETE /api/v1/gdpr/erase` (derecho al olvido) | HIGH | Fase 03 / compliance-analyst | 2026-07-31 | backend-developer | GDPR Art. 17. Hoy solo soft-delete operado por admin. |
| TD-003 | Template de DPA (Data Processing Agreement) firmable con tenant | HIGH | Fase 03 / compliance-analyst | 2026-06-30 | legal + compliance-analyst | Requerido antes de onboarding del 2º tenant (post DEC-017). |
| TD-004 | JSON Schema validation en `RegisterAppController` (registro de apps huésped) | MEDIUM | Fase 03 / code-reviewer (TODO L77) | 2026-07-31 | backend-developer | Hoy validación solo estructural. Archivo: `backend/app/Http/Controllers/Platform/RegisterAppController.php:77`. |
| TD-005 | Logging explícito de `DecryptionException` con `request_id` (no payload) | MEDIUM | Fase 03 / security-auditor | 2026-06-30 | backend-developer | Detectar intentos de tampering de secrets cifrados. |
| TD-006 | Circuit breaker sobre Docker API (rate limit ya aplicado) | MEDIUM | Fase 04 / security-auditor | 2026-08-31 | backend-developer | Hoy solo rate limit `RATE_LIMIT_DOCKER_API_PER_MIN=30`. Patrón Polly / Laravel-circuit-breaker. |
| TD-007 | Evidencia formal de controles SOC 2 Type II (CC1-CC9) | HIGH | Fase 03 / compliance-analyst | 2026-09-30 | compliance-analyst | Hoy implementados pero sin runbook de evidencia ni auditor externo. DEC-013. |
| TD-008 | SIEM centralizado (Loki local → siem managed) | MEDIUM | Fase 05 / monitoring | 2026-Q4 | devops-engineer | Requisito SOC 2 a escala. V1 cubre con Loki local 30d. |
| TD-009 | Escaneo de imágenes base en pipeline contra CVE database diario (no solo on-build) | MEDIUM | Fase 04 / security-auditor | 2026-07-31 | devops-engineer | Trivy cron diario + issue automático. |

### 2.2 Observabilidad

| ID | Título | Severidad | Origen | SLO | Owner propuesto | Notas |
|---|---|---|---|---|---|---|
| TD-010 | Activar `metrics.prometheus` en `traefik.yml` + scrape en prod | MEDIUM | Fase 05 / observability-engineer | 2026-06-30 | devops-engineer | Referenciado en `MONITORING.md §2.4`. |
| TD-011 | Migrar logs Laravel a `Monolog\Formatter\JsonFormatter` | MEDIUM | Fase 05 / observability-engineer | 2026-07-31 | backend-developer | Hoy logs line-based. Parseo robusto en Loki requiere JSON. |
| TD-015 | Endpoint `/metrics` en Maestro API (Prometheus exporter) | HIGH | Fase 05 / observability-engineer | 2026-06-30 | backend-developer | Sin esto, alertas de negocio (ForwardAuth p95, queue backlog, error rate) no existen. Alerta `MaestroAPIMetricsMissing` vigila. Librería candidata: `promphpclient/prometheus-client-php`. |
| TD-016 | Dashboards Grafana: `maestro-api.json`, `maestro-queues.json`, `maestro-tenants.json`, `maestro-security.json` | MEDIUM | Fase 05 / observability-engineer | 2026-07-31 | observability-engineer | Bloqueado por TD-015 (necesita métricas app). |
| TD-017 | Alertas de negocio (ForwardAuthP95Breach, HighErrorRate, QueueBacklog, FailedJobsSpike, InstanceUnhealthy, HookDeliveryFailureRate) | HIGH | Fase 05 / observability-engineer | 2026-07-31 | observability-engineer | Bloqueado por TD-015. SLO ForwardAuth p95 < 50ms (DEC-017) sin alerta activa hoy. |
| TD-018 | Alerta `PgConnectionsWaiting` + dashboard PG | MEDIUM | Fase 05 / observability-engineer | 2026-08-31 | observability-engineer | `pg_exporter` + rule Prometheus. Previene clase de incidentes por capacity planning. |

### 2.3 Testing & Calidad

| ID | Título | Severidad | Origen | SLO | Owner propuesto | Notas |
|---|---|---|---|---|---|---|
| TD-019 | E2E test: login happy path (username/password → access token válido) | HIGH | Fase 03 / qa-tester | 2026-06-30 | qa-tester | Hoy solo unit + integration. |
| TD-020 | E2E test: OAuth Microsoft callback completo | HIGH | Fase 03 / qa-tester | 2026-06-30 | qa-tester | DEC-016 (MFA por Entra ID único); sin E2E el camino crítico queda sin red. |
| TD-021 | E2E test: Gateway forward real a app huésped | MEDIUM | Fase 03 / qa-tester | 2026-07-31 | qa-tester | Requiere fixture de app huésped dummy. |
| TD-022 | E2E test: Webhook delivery real (dispatch → retry → dead-letter) | MEDIUM | Fase 03 / qa-tester | 2026-07-31 | qa-tester | |
| TD-023 | E2E test: Provisioning lifecycle con health transitions | MEDIUM | Fase 03 / qa-tester | 2026-07-31 | qa-tester | provisioning → healthy → degraded → destroyed. |
| TD-024 | Subir cobertura a 85% statements / 75% branches | LOW | Fase 03 / qa-tester | Oportunista | qa-tester | V1 está en 80.2% (exit criteria cumplidos). |
| TD-037 | E2E `admin_users_reachable` redirige a login por 500 encadenado | MEDIUM | stabilization-1 / qa-tester | 2026-Q3 | frontend-developer | Se cierra junto con TD-036. |

### 2.4 Operación / DevOps

| ID | Título | Severidad | Origen | SLO | Owner propuesto | Notas |
|---|---|---|---|---|---|---|
| TD-012 | `just rollback vX.Y.Z` (1-click rollback) | MEDIUM | Fase 05 / incident-manager | 2026-07-31 | devops-engineer | Hoy manual (`RUNBOOK §4.2`). Reduce MTTR en incidentes post-deploy. |
| TD-036 | Permisos de `/app/storage/logs` devuelven 500 encadenados en runtime | HIGH | stabilization-1 / E2E WARN G-1 | 2026-Q3 | backend-developer | `chown/chmod` en Dockerfile o init container. Cierra TD-019/TD-020 indirectamente. |
| TD-038 | `ApplicationSeeder` base con `nginx-test` para que `DemoPoSeeder` no warnee | LOW | stabilization-1 / Known Gap G-3 | Backlog | backend-developer | Alternativa: vincular PO a primera app disponible. |
| TD-039 | Imagen `maestro-e2e` con Playwright npm precargado | LOW | stabilization-1 / Known Gap G-4 | Backlog | devops-engineer | Elimina el `npm install` por corrida de `just e2e`. |
| TD-040 | `BackupService` no loggea cuando cae al fallback local fuera de testing | MEDIUM | stabilization-1 / code-reviewer | Backlog | backend-developer | En prod enmascararía un driver Azure mal instalado. |
| TD-041 | Azurite sin auth expuesto en `maestro-network` | MEDIUM | stabilization-1 / security-auditor | Backlog | devops-engineer | Sólo mitigar si Azurite se promueve a staging/perf. Prohibir en prod documentado en RUNBOOK. |
| TD-042 | Hardening CIS Docker para contenedor `azurite` | LOW | stabilization-1 / compliance-analyst | Backlog | devops-engineer | `no-new-privileges` + `cap_drop ALL` si se promueve fuera de dev. |
| TD-013 | CI/CD: blue-green o canary deploy (evita ventanas de mantenimiento) | LOW | Fase 05 / devops-engineer | 2026-Q4 | devops-engineer | DEC-020 permite downtime; upgrade a V2+. |
| TD-014 | Dry-run mensual automatizado de restore de backup a `stage.<dominio>` | MEDIUM | Fase 05 / incident-manager | 2026-07-31 | devops-engineer | Hoy manual (`RUNBOOK §3.5`). |
| TD-025 | Parametrizar `max_connections` de PG por # de réplicas API | MEDIUM | Fase 05 / observability-engineer | 2026-08-31 | devops-engineer | Escalar API sin ajustar pool = clase de incidente. |
| TD-026 | Secret rotation automatizada en calendario | LOW | Fase 05 / security-auditor | 2026-Q4 | devops-engineer | Hoy `RUNBOOK §4.3` manual. |
| TD-027 | Alertmanager dedicado (hoy Grafana Alerting inline) | LOW | Fase 05 / observability-engineer | V2+ | observability-engineer | Innecesario con 1 canal + 1 operador. |

### 2.5 Producto / Arquitectura

| ID | Título | Severidad | Origen | SLO | Owner propuesto | Notas |
|---|---|---|---|---|---|---|
| TD-028 | Naming inconsistente: `belongsTo_Company` vs. convención `belongsToCompany` | LOW | Fase 03 / code-reviewer | Oportunista | backend-developer | Refactor ligero, sin impacto funcional. |
| TD-029 | Tracing distribuido (OpenTelemetry + Tempo) | LOW | Fase 05 / observability-engineer | V2+ | observability-engineer | DEC-020 lo deja fuera de V1. Necesario cuando el grafo huésped→maestro→huésped crezca. |
| TD-030 | Feature flag service (hoy hardcodeado a `.env`) | LOW | Fase 05 / arquitectura | V2+ | backend-developer | Util para contener blast radius en rollouts. |
| TD-031 | MFA propio TOTP (hoy solo vía Entra ID) | LOW | DEC-016 (WON'T V1) | V2+ | backend-developer | Explícitamente fuera de alcance V1. Registrado para trazabilidad. |
| TD-032 | Accesibilidad WCAG 2.1 AA | LOW | DEC-015 (WON'T V1) | V2+ | ux-designer | Explícitamente fuera de alcance V1. Registrado para trazabilidad. |
| TD-033 | Internacionalización: idiomas adicionales al español | LOW | DEC-014 (WON'T V1) | V2+ | frontend-developer | Explícitamente fuera de alcance V1. |
| TD-034 | Pricing / billing / tiers de licencias | LOW | DEC-018 (WON'T V1) | V2+ | backend-developer | Solo ABM en V1; campos `tier/activa/expira_en` ya existen sin lógica asociada. |
| TD-035 | Canal de soporte integrado a clientes finales | LOW | DEC-021 (WON'T V1) | V2+ | product | Fuera del Maestro en V1. |

---

## 3. Totales

| Severidad | Conteo |
|---|---|
| CRITICAL | 0 |
| HIGH | 9 (TD-001, TD-002, TD-003, TD-007, TD-015, TD-017, TD-019, TD-020, TD-036) |
| MEDIUM | 17 (añadidos TD-037, TD-040, TD-041) |
| LOW | 16 (añadidos TD-038, TD-039, TD-042) |
| **Total** | **42** |

De los 42, **9 están atados a plazos explícitos ≤ 2026-Q3** (todos los HIGH). Los demás son V1.1/V2+ o oportunistas / backlog.

---

## 4. Reglas de gestión

1. **No se suma deuda sin ID.** Si aparece un hallazgo nuevo, se asigna `TD-###` (próximo libre = TD-043) antes de cerrar la iteración que lo detectó.
2. **No se cierra deuda sin PR/commit referenciable.** Al cerrar se mueve a §5 con fecha + commit SHA.
3. **HIGH se revisa semanalmente** en el cierre operativo del humano.
4. **MEDIUM/LOW se repasan mensualmente** y se reportan al humano via `/pm:reporte`.
5. **Los items WON'T V1 explícitos (TD-031 a TD-035)** no se borran — son trazabilidad de decisiones DEC-014 a DEC-021.
6. **Promoción automática:** si un item MEDIUM provoca un SEV ≥ 2 en producción, se promueve a HIGH inmediatamente y su SLO se recalcula desde el postmortem.
7. **Integración con postmortems:** cada action item de un postmortem blameless (`POSTMORTEM_TEMPLATE §8`) genera o actualiza una entrada TD-### en este archivo.

---

## 5. Deuda resuelta (historial)

Vacío al 2026-04-18. Al cerrar items, mover aquí con:

```
| TD-### | Título | Cerrada | Commit | Notas |
|---|---|---|---|---|
```

---

## 6. Referencias

- `docs/05-operations/MONITORING.md` — deuda de observabilidad listada en §2.3 (métricas app) y §5.1 (logs JSON).
- `docs/05-operations/INCIDENT_PLAYBOOK.md` §3.6 — cada postmortem genera items aquí.
- `docs/05-operations/RUNBOOK.md` §4.2, §4.3 — procedimientos manuales que TD-012 / TD-026 eventualmente automatizan.
- `docs/04-delivery/DELIVERY_CHECKLIST.md` — exit criteria Fase 04 referenciaban gaps hoy encapsulados aquí.
- `framework-agentico/agents/CHECKPOINT_GLOBAL.md` — DEC-013 a DEC-021 son el origen de los WON'T (TD-031 a TD-035).
