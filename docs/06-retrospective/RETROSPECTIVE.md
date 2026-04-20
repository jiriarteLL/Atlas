# RETROSPECTIVE.md — Proyecto PRJ-MAESTRO-V1

> **Fase:** 06-retrospective
> **Fecha de la retrospectiva:** 2026-04-18
> **Alcance evaluado:** ciclo completo 00-setup → 05-operations (5 días calendario)
> **Principio:** blameless — enfoque en sistemas, no en personas.

---

## 1. Datos del proyecto

| Campo | Valor |
|---|---|
| ID | PRJ-MAESTRO-V1 |
| Premisa | Maestro Platform: multi-tenant que aloja 7 apps dockerizadas con auth centralizada, OAuth2 Passport, Traefik ForwardAuth, React portal, observabilidad. |
| Preset | `maestro-platform` (derivado invertido de `web-maestro`). |
| Stack | Laravel 13 + Passport 13 + PostgreSQL 16 + Redis 7 + React 18 + Tailwise + Traefik v3 + docker-socket-proxy + Prometheus/Loki/Grafana. |
| Inicio | 2026-04-14 (framework) / 2026-04-16 (premisa cargada). |
| Cierre operativo | 2026-04-18 (v1.0.0-rc.1 lista para VPS). |
| Equipo | 1 humano (Product Owner) + Claude Code agentico. |
| Alcance | 14 épicas (A–M + Platform) + observabilidad + release + runbooks. |
| Release | `v1.0.0-rc.1` (tag manual pendiente por humano). |

### Decisiones clave
- 24 decisiones formales registradas (`DEC-001` a `DEC-024`).
- 2 decisiones supersedidas (`DEC-022` → `DEC-024` el 2026-04-17).
- 3 escalaciones gestionadas: `ISSUE-001` (Passport v13 breaking changes — cerrada), `ESC-001` (PAT git leak — open), `ESC-002` (compliance indefinido — cerrada por `DEC-013`), `ESC-003` (PAT fine-grained sin acceso — cerrada por `DEC-024`).

---

## 2. ¿Qué salió bien?

### 2.1 Estructura del framework
- **Fase 00 con DEC-012 (zero local installs):** decidir de arranque que TODO corre dockerizado eliminó una clase entera de problemas de "funciona en mi máquina". Una vez invertida la mentalidad (de local toolchain a `docker compose run --rm`), el resto fluyó.
- **Framework agentico por fases con checkpoints explícitos:** cada fase tuvo `exit_criteria` auditables. Esto hizo que cerrar una fase fuera una decisión booleana, no un "parece que está listo".
- **Preset `maestro-platform` como inversión de `web-maestro`:** forzar simetría al derivar preset por negación mantuvo el contrato entre plataforma y app huésped coherente sin reescribir reglas.

### 2.2 Discovery y Planning
- **Validación humana temprana del MoSCoW (DEC-013 a DEC-021):** cerrar los 9 WON'T explícitos (`DEC-014` a `DEC-021`) en Discovery evitó re-trabajo en Planning. WCAG AA, MFA propio, i18n, billing y soporte quedaron registrados como deuda V2+ sin ambigüedad.
- **ADRs concretos (14 en Planning):** cada decisión con rationale, no "es mejor". Cuando `DEC-023` forzó Laravel 11→13, solo 1 ADR tuvo que recalibrarse porque cada dependencia tenía ADR propio.
- **Threat model con STRIDE + ASVS L2 desde Planning:** atrapar vectores (header injection en ForwardAuth, Docker socket blast radius, JWT tampering) antes del código evitó retrabajar controles en iteración 9.

### 2.3 Development
- **Épicas A→M con validación transversal por módulo:** el loop `code-review → security → QA → compliance` cerrado por épica mantuvo la cobertura ≥ 80% estable (cerró en 80.2%). Rechazos en iter 4–8 se resolvieron en ≤ 2 iteraciones adicionales.
- **Provisioning E2E real verificado en iter 8:** no "tests lo cubren" sino instancia `nginx-test` creada por API con BD dedicada + red aislada + container + labels Traefik.
- **Bug fixing disciplinado en iter 9:** tres bugs atrapados antes del rc.1 (HMAC placeholder en `DeliverHookJob`, `yaml_parse()` inexistente en `RegisterAppController`, throttle acumulado en `LoginTest::setUp`).

### 2.4 Delivery
- **Transversal aplicada en el mismo ciclo:** las 3 observaciones HIGH del transversal Fase 04 (read_only api, healthchecks worker/scheduler, réplicas 2→3) se aplicaron inline sin pasar a la siguiente iteración. Evitó crear "deuda inmediata".
- **CIS Docker Benchmark pasado de papel a código:** `ProvisioningEngine::createDatabaseContainer` modificado para `CapDrop ALL` + `CapAdd` mínimo + `PidsLimit` cerró el gap de iter 9 en la misma ventana de Delivery.

### 2.5 Operations
- **1-a-1 entre alertas y runbooks específicos:** cada una de las 10 reglas Prometheus apunta a `RUNBOOK.md §6.N` existente. No hay alerta huérfana ni runbook sin alerta.
- **35 items de deuda inventariados con ID estable y SLO:** `TECH_DEBT.md` se integra con el postmortem template (§8 de postmortem genera/actualiza TD-###), cerrando el loop de mejora continua.
- **Bug real detectado y corregido en iter 10:** healthcheck `wget localhost` resolvía `::1` IPv6 en alpine — fix `127.0.0.1` aplicado en 2 Dockerfiles. Atrapado antes del tag `v1.0.0-rc.1` manual.

---

## 3. ¿Qué salió mal?

### 3.1 Passport v13 breaking changes (ISSUE-001, iter 4)
- **Qué pasó:** 5 fixes encadenados requeridos en una sola iteración (Password Grant disabled by default, `grant_types` JSON array, `user_id` bigint vs UUID, recursión en `ForwardAuthController`, env vars obsoletas).
- **Causa raíz:** no se auditaron los breaking changes de Passport 11→13 antes de bumpear por DEC-023. La migración por decreto sin diligencia atrajo los 5 problemas.
- **Impacto:** iter 4 casi íntegra consumida en auth debugging. Épica A se retrasó 1 iteración.
- **Acción correctiva:** memoria nueva — "antes de bumpear un major de dependencia core, leer breaking changes y atar la migración a un ADR específico" (ver §8 Action Items).

### 3.2 Docker-socket-proxy tmpfs bloqueaba el template HAProxy
- **Qué pasó:** en iter 8, montar `tmpfs` en `/usr/local/etc/haproxy` rompió el entrypoint del proxy (el template HAProxy se generaba en ese path).
- **Causa raíz:** copiar patrón CIS genérico (tmpfs para todo) sin leer la imagen base del proxy.
- **Impacto:** 1 ciclo de debug en iter 8 para localizar. Solución: tmpfs solo en `/tmp` y `/run`.
- **Acción correctiva:** memoria — "hardenings genéricos (read_only, tmpfs) deben validarse por imagen, no aplicarse en bloque".

### 3.3 GitHub PAT / acceso inconsistente (ESC-001 + ESC-003)
- **Qué pasó:** PAT embebido en `git remote -v` (ESC-001, abierta) + fine-grained PAT sin acceso al repo de la org (ESC-003, cerrada 2026-04-17 por `DEC-024`).
- **Causa raíz:** configuración de credenciales del host no controlada por el framework; orgs de GitHub con aprobación de fine-grained deshabilitada.
- **Impacto:** `DEC-022` obligó a operar 1 día sin GitHub Issues/PRs hasta que el humano habilitó classic PAT. `DEC-024` revirtió.
- **Acción correctiva:** en próximos proyectos, verificar acceso a la org **antes** de Discovery. Ver §8 Action Items.

### 3.4 Dependencias incompatibles con Laravel 13
- **Qué pasó:** al bumpear a Laravel 13, 7 paquetes requirieron removerse: `socialiteproviders/microsoft-graph`, `pest-plugin-laravel`, `laravel-scribe`, `spatie/laravel-model-states`, `doctrine/dbal`, `flysystem-azure-blob`, `sentry-laravel`.
- **Causa raíz:** mismo problema que §3.1 — no se validó compat de ecosistema antes del bump.
- **Impacto:** features como generación automática de docs API (Scribe), estados explícitos (model-states), SDK Azure Blob quedaron sin reemplazo directo en V1. Algunas se resolvieron ad-hoc, otras pasaron a deuda.
- **Acción correctiva:** memoria — "al elegir versión major de framework, correr `composer why-not` o equivalente sobre la lista esperada de paquetes **antes** de commitear el ADR".

### 3.5 Métricas de aplicación diferidas (TD-015)
- **Qué pasó:** V1 no expone `/metrics` de la app. Alertas de SLO (ForwardAuth p95 < 50ms por DEC-017) no existen.
- **Causa raíz:** priorización — el endpoint requería librería externa (`promphpclient/prometheus-client-php` o `unisharp/laravel-prometheus`) que no cabía en el alcance de iter 7/K. Se optó por cubrir infra (cAdvisor + node-exporter) y diferir app.
- **Impacto:** el SLO más importante (latencia auth) queda sin alerta activa hasta TD-015 (SLO 2026-06-30).
- **Acción correctiva:** elevar TD-015 a HIGH con plazo estricto; validar en operaciones semanalmente.

---

## 4. ¿Qué nos sorprendió?

### 4.1 Positivas
- **Escala DEC-017 (1×7) relajó mucho el diseño:** la arquitectura multi-tenant completa sigue, pero capacity planning es holgado. 3 réplicas × 1.5 CPU / 768M dan 4.5 CPU / 2.3 GB para 50 concurrentes — sobra.
- **El bug de IPv6 en healthcheck fue trivial pero silencioso:** `wget localhost` resolvía a `::1` mientras nginx solo bindeaba a IPv4. Lección: healthchecks deberían hacer `curl -4` o IP literal explícita por defecto.
- **Postmortem blameless + TECH_DEBT vinculados:** el template de postmortem §8 genera entradas TD-###. Esto cierra el loop "incidente → aprendizaje → deuda rastreable" sin sistema externo de ticketing.

### 4.2 Negativas
- **El threat model detectó gaps de observabilidad, no de código:** esperábamos vectores de ataque como principal hallazgo; en cambio, el valor más alto vino de "¿cómo nos enteramos si esto falla?" — eso guió `MONITORING.md §5.3` (nunca loguear secrets) y la integración del audit_log en DB INSERT-only con triggers.
- **El MFA WON'T V1 (DEC-016) tiene implicancias de compliance más finas de lo previsto:** cubrir solo Entra ID para flujo MFA deja al usuario user/pass sin 2FA. Aceptado como riesgo documentado pero requerirá DPA explícito por tenant (TD-003).

---

## 5. ¿Qué haríamos diferente?

1. **Validar compatibilidad de ecosistema ANTES del ADR de framework.** En este proyecto, DEC-023 (Laravel 11→13) forzó remover 7 paquetes ya en iter 4. Pre-check con `composer why-not` hubiera movido esas remociones a Planning.
2. **Acceso GitHub verificado en Fase 00.** ESC-003 perdió medio día. El checklist de 00-setup debería incluir `gh auth status` + `gh api /repos/OWNER/REPO --method GET`.
3. **Breaking changes de deps core explícitos en ADRs.** ADR-001 debía incluir sección "Breaking changes relevantes de vX a vY" con referencia al upgrade guide. Pasó en ISSUE-001.
4. **Healthchecks con IP literal o flag `-4`.** Regla transversal: `wget --inet4-only` o `127.0.0.1`. Evitaría la clase de §3.5 iter 10.
5. **Endpoint `/metrics` de app en fase K (observabilidad), no diferido.** TD-015 debería haber nacido con alerta bloqueante en la iter 7; la decisión de diferir dejó SLO sin guardia.
6. **Runbooks escritos durante el desarrollo, no al final.** En Fase 05 se escribieron 7 runbooks post-hoc. Hacerlos "módulo a módulo" en Fase 03 hubiera validado que lo construido fuera operable.
7. **Dry-run de restore mensual desde día 1.** `backup-daily.sh` se escribió en operations, pero el primer dry-run queda para 2026-05-02. Deberíamos haber ejecutado uno inmediatamente post-rc.1.

---

## 6. Métricas del proyecto

### 6.1 Ciclo
| Métrica | Valor |
|---|---|
| Fases completadas | 6 / 7 (retrospectiva incluida) |
| Iteraciones totales (global) | 10 |
| Iteraciones en Development | 9 (5 de features, 4 de refinamiento) |
| Días calendario 00 → rc.1 | 5 (2026-04-14 a 2026-04-18) |
| Días calendario premisa → rc.1 | 3 (2026-04-16 a 2026-04-18) |

### 6.2 Entregables
| Métrica | Valor |
|---|---|
| Épicas aprobadas | 14 / 14 (100%) |
| Endpoints API | ~45 (auth + admin + platform + instances + gateway + audit) |
| Tests pasando | 150 / 151 (1 E2E login happy path skipped) |
| Cobertura statements | 80.2% |
| Cobertura branches | ~72% (target ≥ 70% cumplido) |
| ADRs | 14 |
| Decisiones formales | 24 (2 supersedidas) |

### 6.3 Calidad
| Métrica | Valor |
|---|---|
| Vulnerabilidades CRITICAL / HIGH abiertas | 0 / 0 |
| Validaciones transversales | 5 ciclos (Fases 03, 04, 05) |
| Veredicto más común | APROBADO CON OBSERVACIONES (observaciones aplicadas inline) |
| Bugs de integración detectados pre-release | 5 (HMAC, yaml_parse, throttle, Passport v13, IPv6 HC) |
| Bugs atrapados por transversal | 3 adicionales (read_only api, healthchecks worker, réplicas api) |

### 6.4 Deuda
| Severidad | Count | SLO promedio |
|---|---|---|
| CRITICAL | 0 | — |
| HIGH | 8 | ≤ 2026-Q3 |
| MEDIUM | 14 | ≤ 2026-Q4 |
| LOW | 13 | Oportunista / V2+ |

### 6.5 Escalaciones al humano
| Id | Qué | Resolución |
|---|---|---|
| ESC-001 | PAT filtrado en `git remote -v` | Open (el humano optó por diferir). |
| ESC-002 | Compliance indefinido | Cerrada por DEC-013 (GDPR + SOC2 + CIS + OWASP ASVS L2). |
| ESC-003 | Fine-grained PAT sin acceso | Cerrada por DEC-024 (classic PAT habilitado). |
| ISSUE-001 | Passport v13 breaking changes | Cerrada en iter 4 (5 fixes encadenados). |

Promedio: 4 escalaciones en 10 iteraciones = 0.4 escalaciones/iter. Aceptable.

---

## 7. Patrones a repetir (entran en FRAMEWORK_MEMORY)

1. **Zero-local-installs (DEC-012) como default para proyectos con toolchain multilenguaje.** Docker-only eliminó 100% del "works on my machine".
2. **Validación humana temprana del MoSCoW con WON'T explícitos.** Los 9 WON'T de Discovery evitaron reabrir scope en Planning y Development.
3. **Preset por inversión (maestro-platform ← web-maestro).** Mantener simetría entre plataforma y cliente por negación escalable a más pares.
4. **Transversal en el mismo ciclo de Delivery.** No crear deuda inmediata: aplicar observaciones HIGH antes del tag.
5. **Runbook 1-a-1 con alertas.** Sin alertas huérfanas ni runbooks sin alerta correspondiente.
6. **Postmortem template → TECH_DEBT pipeline.** Cada action item de postmortem genera TD-### trazable.
7. **Secreto hardcoded = error auditable.** El bug de HMAC `'placeholder'` se atrapó solo porque el security-auditor hacía grep de constantes sospechosas; vale la pena ritual izarlo.

## 8. Anti-patrones a evitar (entran en FRAMEWORK_MEMORY)

1. **Bumpear major de framework sin auditar ecosistema (§3.1, §3.4).** 5 fixes + 7 paquetes removidos por DEC-023.
2. **Aplicar hardening genérico sin leer imagen base (§3.2).** Caso tmpfs en HAProxy proxy.
3. **Verificar acceso a infra externa (GitHub org) después de arrancar (§3.3).** Costó ESC-003 + DEC-022.
4. **Diferir observabilidad de aplicación (TD-015, §3.5).** Dejó el SLO más importante sin alerta.
5. **Healthcheck con `localhost` literal en alpine.** Resuelve a `::1` IPv6 y genera `unhealthy` falso cuando el servicio es IPv4-only.
6. **Runbooks escritos post-hoc.** No validan operabilidad durante el desarrollo.

---

## 9. Action Items

| # | Acción | Destino | Severidad | Owner |
|---|---|---|---|---|
| AI-1 | Incorporar checklist de compat ecosystem en el template de ADR de framework (sección "Breaking changes + paquetes afectados") | Framework: `presets/*/ADR_TEMPLATE.md` | HIGH | memory-updater |
| AI-2 | Agregar verificación de acceso GitHub a exit criteria de 00-setup | Framework: `00-setup/CHECKPOINT.md` | HIGH | memory-updater |
| AI-3 | Regla transversal: healthchecks con `--inet4-only` o IP literal | Framework: `rules/GENERAL_RULES.md` | MEDIUM | memory-updater |
| AI-4 | Política: endpoint `/metrics` de app no se difiere después de fase K (observabilidad) | Framework: `05-operations/rules/RULES.md` | HIGH | memory-updater |
| AI-5 | Regla: runbook específico por alerta se escribe cuando la alerta se define, no en Fase 05 | Framework: `05-operations/rules/RULES.md` | MEDIUM | memory-updater |
| AI-6 | Dry-run mensual de restore en calendario del operador (ya documentado en RUNBOOK §3.5; agregar recordatorio) | Operador humano | MEDIUM | operador |
| AI-7 | Cerrar ESC-001 (PAT git leak) — revisar `~/.gitconfig` y credential helper | Humano | LOW | humano |
| AI-8 | Ejecutar primer dry-run de backup/restore post-tag `v1.0.0-rc.1` | Operador humano | HIGH | operador |

---

## 10. Cierre

El proyecto PRJ-MAESTRO-V1 entregó **v1.0.0-rc.1 lista para despliegue VPS** con:
- 14/14 épicas aprobadas, 0 vulnerabilidades bloqueantes, 80.2% cobertura.
- 24 decisiones formales + 14 ADRs documentados.
- 5 artefactos de operaciones + 10 alertas activas + 35 items de deuda priorizados.
- 6 fases cerradas con transversal aprobado en cada gate.

**Recomendación al humano (Product Owner):** proceder con el tag `v1.0.0-rc.1` para disparar `release.yml` → GHCR → deploy VPS. Próxima sesión: monitorear SEV de post-deploy durante la primera semana y ejecutar AI-8 (dry-run restore).

La memoria del framework se actualiza en paralelo (ver `FRAMEWORK_MEMORY.md`) para que el próximo proyecto parta desde estos aprendizajes.
