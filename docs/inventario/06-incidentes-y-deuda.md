# Inventario LLYA v2 — Incidentes, alertas y deuda técnica (fase 06-operations)

## Protocolo de incidentes

> **Pendiente del PO:** asignar los dueños y los canales de escalamiento. Lo que sigue es la propuesta.

| Severidad | Ejemplo | Respuesta |
|---|---|---|
| **S1** | App caída, o sospecha de acceso indebido o de fuga de datos | Avisar al responsable de TI y al evaluador. Si hay sospecha de acceso: rotar `JWT_SECRET`, `MAESTRO_API_KEY` y `SYNC_API_KEY`; revisar `audit_log` (`LOGIN_*`, `REFRESH_REUSE`, `ROLE_CHANGE`) |
| **S2** | Los agentes no sincronizan, o fallan login y refresh a muchos usuarios | Revisar el runbook; escalar si dura más de 1 h |
| **S3** | Falla una función puntual (garantía Lenovo, mails, exportes) | Ticket normal |

Pasos: detectar → contener (cortar sesiones o rotar secretos) → diagnosticar con el `request_id` y el audit →
corregir con un PR (el ciclo completo de MANUAL §7) → postmortem en `docs/inventario/postmortems/`.

## Alertas propuestas (sobre `/metrics`)

| Alerta | Condición | Umbral sugerido |
|---|---|---|
| App sin salud | `/health` distinto de 200 | 3 chequeos seguidos |
| Errores 5xx | `rate(http_requests_total{status=~"5.."}[5m]) / rate(http_requests_total[5m])` | > 2 % durante 10 min |
| Latencia | p95 de `http_request_duration_seconds` | > 1 s durante 10 min |
| Posible fuerza bruta | `rate(auth_login_failures_total[5m])` | > 1/s |
| Memoria | memoria del proceso respecto del límite de 512 MB | > 90 % durante 30 min (CONVENCIONES §7.2) |

## Deuda técnica

> Aceptada por el PO el 2026-09-30, con el plan de cada ítem (issues #10 a #16).

| ID | Deuda | Impacto | Plan |
|---|---|---|---|
| DT-01 | `main.py` concentra todos los endpoints (~1.000 líneas) | Mantenibilidad | Separar en routers por dominio (activos, sync/GLPI, proyectos, adjuntos, tendencias) |
| DT-02 | El rate limit y el límite por email son en memoria, por proceso | Con más de un worker o réplica, los límites se multiplican | Pasar a Redis si se escala horizontalmente |
| DT-03 | Una sola `SYNC_API_KEY` para todos los agentes | Si se filtra, cualquiera puede escribir activos | Clave por equipo o por sede, revocable |
| DT-04 | Los adjuntos no pasan por antivirus | Riesgo de malware en los descargables | Escaneo con ClamAV o similar al subir |
| DT-05 | Migraciones con `create_all` (no versionadas) | Los cambios de columnas en tablas existentes no se aplican solos | Adoptar Alembic antes del primer cambio de esquema en Preprod |
| DT-06 | Tests sobre SQLite, no sobre PostgreSQL | Diferencias de dialecto sin detectar | Correr la suite contra Postgres en la VM de ensayo y en CI (servicio `postgres`) |
| DT-07 | Sin tests del frontend | Regresiones de UI | Tests de humo con Playwright del login, el refresh y el cambio obligatorio |
| DT-08 | Google Fonts externo | Dependencia de terceros y privacidad | Servir las fuentes desde la app |
| DT-09 | Licencias y Nómina fuera de alcance (ADR-003) | Funcionalidad que hoy da el UserManager | A definir por el PO |
| DT-10 | Migración de datos desde producción | La v2 arranca vacía | Script SQLite → PostgreSQL cuando haya HTTPS |
| DT-11 | `App.jsx` concentra el shell y varias pantallas (~940 líneas) (code review, 2026-09-30) | Mantenibilidad del frontend | Extraer dashboard, listado de activos y ficha a `secciones/`, como ya se hizo con proyectos y perfil |
