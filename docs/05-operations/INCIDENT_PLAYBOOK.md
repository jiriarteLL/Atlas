# INCIDENT_PLAYBOOK.md — Maestro Platform V1

> **Fase:** 05-operations
> **Versión:** v1.0.0-rc.1
> **Fecha:** 2026-04-18
> **Alcance V1 (DEC-017):** 1 empresa × 7 apps huésped. Operación VPS manual por el humano (DEC-011). Sin SLA de soporte integrado (DEC-021).

---

## 1. Niveles de severidad

| Nivel | Definición | Ejemplos |
|---|---|---|
| **SEV1** | Sistema caído o indisponible para todos los usuarios. Pérdida de datos activa o riesgo inminente. Brecha de seguridad confirmada. | Maestro API down, DB corrupta, credenciales expuestas, disco VPS 100% |
| **SEV2** | Funcionalidad crítica degradada pero con workaround. Alta latencia sostenida. Pérdida parcial de funcionalidad multi-tenant. | ForwardAuth lento, provisioning falla, webhook delivery cae, una app huésped inaccesible |
| **SEV3** | Funcionalidad secundaria afectada. Sin impacto significativo en usuarios finales. | Grafana down, observabilidad parcial, audit-log no se actualiza en UI pero sí en DB |
| **SEV4** | Informativo. Sin impacto operativo actual pero requiere atención. | Warning de deuda, dependencia EOL en <6m, métrica fuera de rango sin alertar |

## 2. Tiempos de respuesta objetivo

V1 es operado por **1 persona (el humano + Claude asistente)**. Los tiempos son guía, no SLA contractual (DEC-021).

| Severidad | Tiempo respuesta objetivo | Tiempo resolución objetivo | Canal |
|---|---|---|---|
| SEV1 | ≤ 15 min | ≤ 2 h | Alerta directa + escalamiento humano inmediato |
| SEV2 | ≤ 1 h | ≤ 8 h | Alerta + atención en ventana laboral |
| SEV3 | ≤ 4 h laborales | ≤ 3 días | Ticket — próximo sprint operativo |
| SEV4 | ≤ 24 h laborales | Backlog | Issue + tech debt |

## 3. Flujo de respuesta a incidentes

```
┌──────────────┐   ┌──────────┐   ┌──────────────┐   ┌────────────┐   ┌──────────┐   ┌────────────┐
│ 1. Detección │ → │ 2. Triaje│ → │ 3. Contención│ → │ 4. Resolver│ → │ 5. Cierre│ → │ 6. Postmort│
└──────────────┘   └──────────┘   └──────────────┘   └────────────┘   └──────────┘   └────────────┘
```

### 3.1 Detección

Fuentes de detección ordenadas por tiempo típico al descubrimiento:

1. **Alerta automática** (Grafana → canal configurado) — minutos
2. **Health check Maestro** (`/api/platform/health` falla) — minutos
3. **Reporte del usuario interno** (1 empresa tenant V1) — minutos a horas
4. **Revisión manual del humano** — horas a días

### 3.2 Triaje (quién, cuándo, qué severidad)

Preguntas en orden:
1. ¿Está el sistema respondiendo? → si no responde, SEV1
2. ¿Hay pérdida de datos activa o riesgo? → SEV1
3. ¿Hay brecha de seguridad (acceso no autorizado, datos expuestos)? → SEV1
4. ¿Funcionalidad crítica degradada con workaround? → SEV2
5. ¿Impacto parcial no crítico? → SEV3
6. ¿Sin impacto pero requiere atención? → SEV4

**Asignación de roles durante el incidente (aun siendo 1 persona):**
- **Incident Commander (IC):** quien toma decisiones — el humano por default
- **Scribe:** quien documenta timeline — Claude Code asistente
- **Comms:** quien notifica — el humano

### 3.3 Contención

Acciones para **limitar el blast radius** sin necesariamente resolver la causa raíz:

- **SEV1 DB corrupta:** poner Maestro en modo solo-lectura (feature flag) o down total si es peor el síntoma que la caída
- **SEV1 secreto expuesto:** rotar `MAESTRO_ENCRYPTION_KEY` + todas las `webhook_secret_encrypted` (re-generar por app) + forzar re-login a todos los usuarios (invalidar refresh tokens: `php artisan passport:purge`)
- **SEV1 provisioning runaway:** deshabilitar temporalmente endpoint `POST /api/admin/instances` (middleware 503) — evita multiplicar containers
- **SEV2 queue explota:** pausar workers (`docker compose stop maestro-worker`), diagnosticar, reanudar
- **SEV2 app huésped rebelde:** `POST /api/admin/instances/{id}/stop` → aísla sin destruir

### 3.4 Resolución

Seguir el **runbook específico** según la alerta disparada (referencia en `MONITORING.md §3.1` → `RUNBOOK.md §6`).

Si la causa raíz no está documentada, escalar: Claude asistente ayuda a diagnosticar desde logs (Loki) + métricas (Prometheus) + estado (`docker ps` / DB queries).

### 3.5 Cierre

Verificaciones antes de declarar el incidente cerrado:
- [ ] Métricas vuelven a valores normales sostenidos >15 min
- [ ] Alertas disparadas se resuelven (no solo silencian)
- [ ] Health check OK en los 3 últimos polls
- [ ] Usuario final (si hubo reporte) confirma que funciona
- [ ] Postmortem agendado (solo SEV1/SEV2)

### 3.6 Postmortem (SEV1 y SEV2 siempre; SEV3 si hay lecciones)

Usar template `docs/05-operations/templates/POSTMORTEM_TEMPLATE.md`.
**Principio innegociable:** blameless. El postmortem busca **mejorar el sistema**, no asignar culpa. Los action items se convierten en **deuda técnica** vía `tech-debt-manager`.

Debe publicarse dentro de las **72h** del cierre del incidente.

## 4. Canales de comunicación

| Canal | Uso | Audiencia V1 |
|---|---|---|
| Alerta automatizada (Grafana Contact Point) | Disparo inicial SEV1/SEV2 | Humano (email) |
| Log `docs/05-operations/INCIDENTS/` | Registro persistente de cada incidente | Humano + Claude |
| Commit messages | Cambios que responden a incidentes | Git history |
| Postmortem | Aprendizajes | Humano (luego V2+: equipo) |

V1 **no incluye** Slack/Teams integration ni on-call rotation (DEC-021).

## 5. Escalamiento

V1 con 1 persona responsable:

- **Técnico:** si no puede resolver el incidente → consultar con Claude Code (cargar `CLAUDE.md` + `RUNBOOK.md` + logs relevantes + descripción). Prompt sugerido: *"Incidente SEV{N}: [descripción]. Ver logs adjuntos. Sugerir diagnóstico y pasos de contención/resolución."*
- **Seguridad:** si hay brecha confirmada → contactar legal + compliance ANTES de tocar nada (preservar evidencia).
- **Plataforma Azure:** si el VPS se cae por problemas de infra Azure → soporte del proveedor (DEC-011).

## 6. Template de postmortem blameless

Guardado en `docs/05-operations/templates/POSTMORTEM_TEMPLATE.md`. Cada postmortem se copia en `docs/05-operations/INCIDENTS/INC-YYYYMMDD-<slug>.md`.

## 7. Lista de incidentes registrados V1

Ninguno aún. Se irán agregando en `docs/05-operations/INCIDENTS/` con formato `INC-YYYYMMDD-<slug>.md`.

## 8. Revisión periódica del playbook

- **Post-SEV1:** revisar dentro de 1 semana si el playbook guió bien la respuesta. Ajustar.
- **Mensual:** repasar alertas que dispararon y action items pendientes.
- **Trimestral:** simulacro de incidente (game day) para validar el playbook sin presión real. Opcional V1.
