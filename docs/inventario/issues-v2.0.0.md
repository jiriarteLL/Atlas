# Milestone v2.0.0 — Issues a crear en GitHub

Milestone: **v2.0.0 — primera versión como app huésped** (fase 02-planning: "GitHub Milestone + Issues creados").
Cada issue sale de un pendiente real de `PROJECT.md` o de la deuda técnica (`06-incidentes-y-deuda.md`).

| # | Título | Etiquetas | Descripción / criterio de cierre |
|---|---|---|---|
| 1 | VM de ensayo con Docker | `infra`, `bloqueante` | VM Ubuntu 24.04 (2 vCPU, 4 GB, 40 GB) con Docker instalado (`herramientas/vm-ensayo/instalar-docker.sh`). Se cierra cuando `docker compose version` responde en la VM. |
| 2 | Ensayo local completo con Docker (`ensayo.sh`) | `delivery`, `bloqueante` | `bash herramientas/vm-ensayo/ensayo.sh` termina en TODO PASS: build ≤ 500 MB, Trivy sin CRITICAL/HIGH, Gitleaks, contrato, cookie, seeder idempotente, read-only, no-root. Adjuntar `ensayo-resultado.txt`. |
| 3 | Puerto asignado en el rango de Test | `infra`, `bloqueante` | Los 9 puertos 3110–3190 están ocupados. Pedir el puerto a quien administra el VPS y verificarlo libre (MANUAL §2.3). |
| 4 | Despliegue a Test en Dokploy | `delivery` | Proyecto con título, descripción y tag `Test`; servicio `App Test`; `composePath: ./docker-compose.test.yml`; `createEnvFile: true`; verificación de MANUAL §6 completa, con login en un navegador real. Depende de #2 y #3. |
| 5 | Tests contra PostgreSQL | `testing`, `deuda` | Correr `app/tests` contra PostgreSQL 16 (en la VM y como servicio en `ci.yml`). DT-06. |
| 6 | ~~Migraciones versionadas con Alembic~~ | `backend`, `deuda` | **Hecho (2026-09-30):** migración `0001` y tests. Crear el issue ya cerrado o no crearlo. DT-05. |
| 7 | Validación transversal (fases 03 a 06) | `proceso` | security-auditor, qa-tester, performance-analyst, compliance-analyst y code-reviewer (`framework-agentico/validation/`) en PASS. |
| 8 | Gate 1 — auto-evaluación hasta PASS | `proceso` | Abrir el PR `master` del fork → `tools/inventario` y correr `/evaluar-app-huesped` hasta PASS (MANUAL §7). Depende de conseguir `EvaluacionAppHuesped/SPEC.md` y el comando. |
| 9 | Hallazgos de Gitleaks heredados del template | `seguridad`, `decisión-evaluador` | 31 hallazgos en commits del template (Tailwise, `legacy/`, `.env.example` viejo). La app no puede reescribir ese historial. Lo decide el evaluador humano. |
| 10 | Separar `main.py` en routers por dominio | `backend`, `deuda` | activos, sync/GLPI, proyectos, adjuntos, tendencias. DT-01. |
| 11 | Rate limit compartido (Redis) | `backend`, `deuda` | Necesario si se escala a más de un worker o réplica. DT-02. |
| 12 | Clave de sincronización por equipo o sede | `seguridad`, `deuda` | Reemplazar la `SYNC_API_KEY` única por claves revocables. DT-03. |
| 13 | Antivirus para adjuntos | `seguridad`, `deuda` | Escaneo al subir (ClamAV o similar). DT-04. |
| 14 | Tests de humo del frontend (Playwright) | `testing`, `deuda` | Login, refresh, cambio obligatorio de contraseña, exportar a Excel (verificar la CSP). DT-07. |
| 15 | ~~Fuentes servidas por la app~~ | `frontend`, `deuda` | **Hecho (2026-09-30):** fuentes en `/fonts/`, CSP sin dominios externos y test. Crear el issue ya cerrado o no crearlo. DT-08. |
| 16 | Migración de datos de producción a PostgreSQL | `datos`, `deuda` | Script SQLite → PostgreSQL. Recién cuando haya HTTPS (MANUAL §0.1). DT-10. |
| 17 | Protocolo de incidentes: responsables y escalamiento | `operaciones`, `decisión-PO` | Completar los responsables y canales en `06-incidentes-y-deuda.md`. |
| 18 | Decisión `regulated` (Ley 25.326) | `datos`, `decisión-PO` | Confirmar `data_policy.classification.regulated`. Si es `true`: tier `critical` + ADR de cumplimiento. |
