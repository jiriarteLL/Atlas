# FRAMEWORK_MEMORY.md — Lecciones para proyectos futuros

> **Fuente:** retrospectiva de PRJ-MAESTRO-V1 (cerrado 2026-04-18).
> **Audiencia:** PM + orquestadores + agentes del framework en próximos proyectos.
> **Reglas:** las entradas son concisas, accionables, con origen rastreable. No narrativas.

---

## 1. Patrones exitosos (repetir)

| ID | Patrón | Cuándo aplicar | Origen | Ganancia medida |
|---|---|---|---|---|
| MEM-P01 | **Zero-local-installs:** TODO corre dockerizado; host solo necesita Docker + git + IDE | Default para proyectos con stack multilenguaje (PHP + Node + Python + DB clients) | DEC-012 en PRJ-MAESTRO-V1 | Eliminó 100% de "works on my machine"; onboarding dev = `just up` |
| MEM-P02 | **WON'T HAVE V1 explícitos en Discovery validados por el PO** | Siempre que la premisa tenga ambigüedades sobre scope (accesibilidad, i18n, MFA, billing, SLAs) | DEC-014..021 cerradas en 1 sesión | Reduce reaperturas de scope en Planning y Development |
| MEM-P03 | **Preset por inversión (negación simétrica)** | Cuando existe un preset "cliente" (app huésped) y hace falta un preset "servidor" (plataforma) | `maestro-platform` ← `web-maestro` | Mantiene contrato coherente sin duplicar reglas |
| MEM-P04 | **Transversal APROBADO CON OBSERVACIONES aplicadas inline** | Fase 04 Delivery y Fase 05 Operations cuando las observaciones son HIGH pero localizadas | Fase 04 PRJ-MAESTRO-V1 | Evitó crear "deuda inmediata" en el mismo tag |
| MEM-P05 | **Runbook específico 1-a-1 con alerta** | Al cerrar Fase 05: cada regla Prometheus apunta a `RUNBOOK §N` existente | 10/10 alertas cubiertas | Sin alertas huérfanas ni runbooks sin alerta |
| MEM-P06 | **Postmortem blameless → TECH_DEBT pipeline** | Cada action item del template `§8` genera/actualiza un `TD-###` | Diseñado en PRJ-MAESTRO-V1 | Cierra loop incidente→aprendizaje sin sistema externo |
| MEM-P07 | **ADRs atómicos por decisión (no megaADR)** | Cuando una decisión puede cambiar independientemente (framework vs. DB vs. queue) | 14 ADRs en Planning | Cuando `DEC-023` forzó Laravel 11→13, solo 1 ADR cambió |
| MEM-P08 | **Validación humana temprana del MoSCoW** | Antes de cerrar Discovery | PRJ-MAESTRO-V1 | Evita reabrir priorización en Development |
| MEM-P09 | **audit_log en DB INSERT-only con triggers, no en logs de app** | Siempre que haya compliance (GDPR/SOC2) y necesidad de forense | ADR-014 PRJ-MAESTRO-V1 | Logs de app pueden tener secretos; audit_log no y es inmutable por DB |
| MEM-P10 | **Provisioning E2E real verificado en desarrollo, no solo por tests** | Épicas que tocan infra (Docker, DB, red) | iter 8 PRJ-MAESTRO-V1 (nginx-test) | Atrapa bugs que los mocks no ven |

---

## 2. Anti-patrones (evitar)

| ID | Anti-patrón | Por qué duele | Origen | Cómo prevenir |
|---|---|---|---|---|
| MEM-A01 | **Bumpear major de framework sin auditar ecosistema** | 5 fixes encadenados + 7 paquetes removidos en iter 4 | DEC-023 / ISSUE-001 PRJ-MAESTRO-V1 | Antes del ADR, correr `composer why-not laravel/framework:^X` sobre dependencias esperadas |
| MEM-A02 | **Hardening genérico (tmpfs, read_only) aplicado en bloque sin leer la imagen base** | tmpfs en `/usr/local/etc/haproxy` rompió el template de docker-socket-proxy | iter 8 PRJ-MAESTRO-V1 | Validar por imagen; tmpfs solo en `/tmp`, `/run` y paths de app conocidos |
| MEM-A03 | **Iniciar proyecto sin verificar acceso a infra externa (GitHub org, cloud, BD externa)** | 1 día perdido hasta que el humano habilitó classic PAT | ESC-003 PRJ-MAESTRO-V1 | Agregar `gh auth status` + `gh api /repos/...` al exit criteria de Fase 00 |
| MEM-A04 | **Diferir endpoint `/metrics` de aplicación después de la fase de observabilidad** | Deja el SLO principal sin alerta activa (ForwardAuth p95) | TD-015 PRJ-MAESTRO-V1 | Regla dura: Fase 05 no cierra sin `/metrics` exportando al menos 3 métricas de negocio |
| MEM-A05 | **Healthcheck con `localhost` literal en alpine / busybox** | Resuelve a `::1` IPv6 y marca `unhealthy` falso cuando el servicio es IPv4-only | iter 10 PRJ-MAESTRO-V1 | Usar `127.0.0.1` o `wget --inet4-only` en HEALTHCHECK |
| MEM-A06 | **Runbooks escritos post-hoc en Fase 05** | No validan operabilidad durante desarrollo; aparecen casos sin documentar | PRJ-MAESTRO-V1 | Runbook específico nace junto con la alerta, no después |
| MEM-A07 | **Secreto hardcoded aunque sea "placeholder"** | El bug de HMAC `'placeholder'` pasó Review básico; lo atrapó grep del security-auditor | iter 9 `DeliverHookJob` PRJ-MAESTRO-V1 | Linter / grep en CI para constantes sospechosas (`placeholder`, `todo_secret`, `changeme`) |
| MEM-A08 | **`exec -T` para backups sin permisos restrictivos en destino** | Dumps potencialmente legibles por otros procesos del host | Transversal Fase 05 PRJ-MAESTRO-V1 | `chmod 0600` + `chown operador:operador` en el script de backup |

---

## 3. Preferencias del humano detectadas

| ID | Preferencia | Evidencia |
|---|---|---|
| MEM-H01 | **Idioma único español** en docs y commits | DEC-014 + estilo de respuestas |
| MEM-H02 | **No zero-downtime requerido V1** — prefiere ventanas cortas nocturnas sobre complejidad blue-green | DEC-020 |
| MEM-H03 | **Prefiere operar todo local (docker-only)** y dejar la infra VPS fuera del framework | DEC-011 + DEC-012 |
| MEM-H04 | **Escala realista** (1 tenant × 7 apps) sobre teorizar B2B SaaS genérico | DEC-017 |
| MEM-H05 | **Autónomo cuando la decisión está clara**, escala solo cuando la ambigüedad es real | "Sigue, no me consultes ni me resumas excepto si tienes algún problema o falta de definición, sin rodeos." |
| MEM-H06 | **Prefiere markdown canónico + GitHub mirror**, no GitHub como fuente de verdad | DEC-024 |
| MEM-H07 | **Tolera deuda trazable** pero exige que esté inventariada con ID y SLO | `TECH_DEBT.md` con 35 items aceptado sin fricción |
| MEM-H08 | **No pide código de rutina de `console.log` / debug** — espera que el ruido no llegue a producción | LOG_LEVEL=warning en prod |
| MEM-H09 | **Rechaza resúmenes innecesarios y preámbulos.** Pide acción directa. | Feedback explícito en sesión |

---

## 4. Defaults optimizados para el próximo proyecto

| ID | Default | Aplica cuando |
|---|---|---|
| MEM-D01 | Stack Laravel **13.x** + Passport **13.x** + PostgreSQL **16** + Redis **7** + React **18** + Vite + Tailwind + Traefik **v3.5** | Proyecto backend PHP + frontend React con auth OAuth2 + multi-tenant |
| MEM-D02 | Docker Compose con `no-new-privileges:true` + `CapDrop: ALL` + `CapAdd` mínimo + `PidsLimit` + `resources.limits` + `read_only:true` + tmpfs explícito | Cualquier servicio productivo |
| MEM-D03 | docker-socket-proxy con `POST=1`, `IMAGES=1`, `EXEC=0`, `BUILD=0`, `VOLUMES=0` | Si la app necesita orquestar Docker desde el container |
| MEM-D04 | `scrape_interval: 30s` + retención Prometheus **30d** + Loki **30d** | Proyectos con 1 host + ≤ 20 containers |
| MEM-D05 | Schedule de backups diarios 02:15 UTC + rotación 30d + `chmod 0600` + cifrado AES-256-CBC | Siempre que haya DB persistente |
| MEM-D06 | `.env.production.example` con `APP_DEBUG=false` + `LOG_LEVEL=warning` + rate limits explícitos | Nunca shipear sin este template |
| MEM-D07 | Pipeline release: tag `v*` → build + Trivy CRITICAL/HIGH bloqueante → push GHCR → GitHub Release con changelog | Proyectos que van a VPS/cloud |
| MEM-D08 | Estructura docs: `docs/0N-<fase>/` con deliverables fijos por fase + `CHANGELOG.md` + `CLAUDE.md` en raíz | Default para proyectos con el framework |

---

## 5. Preguntas a anticipar en la primera sesión con el humano

Basado en lo que se escaló o se preguntó tarde en este proyecto, arrancar las siguientes conversaciones **antes** de cerrar Fase 00:

| ID | Pregunta | Razón |
|---|---|---|
| MEM-Q01 | ¿Qué compliance es MUST V1? Opciones: GDPR, SOC 2, CIS, OWASP ASVS, HIPAA, PCI-DSS. | ESC-002 tomó un round extra. |
| MEM-Q02 | ¿Qué idiomas debe soportar el UI V1? | DEC-014 — hubiera sido pregunta de arranque. |
| MEM-Q03 | ¿WCAG 2.1 AA obligatorio V1 o diferido? | DEC-015. |
| MEM-Q04 | ¿MFA propio o delegado a IdP externo (Entra ID, Google, etc.)? | DEC-016. |
| MEM-Q05 | ¿Volumen esperado V1 (tenants × apps × users concurrentes)? | DEC-017 — reformuló completamente el capacity planning. |
| MEM-Q06 | ¿Pricing / billing / tiers son alcance V1 o diferidos? | DEC-018. |
| MEM-Q07 | ¿Retención exacta de datos (mínimos legales o más)? | DEC-019. |
| MEM-Q08 | ¿Zero-downtime requerido o ventanas aceptables? | DEC-020. |
| MEM-Q09 | ¿Soporte a clientes finales dentro del producto o fuera? | DEC-021. |
| MEM-Q10 | ¿Hay preset relevante ya creado? ¿Derivar por inversión es válido? | Ahorra definir reglas desde cero. |
| MEM-Q11 | **Acceso a GitHub org y scopes del PAT verificados.** | ESC-003 costó medio día. |
| MEM-Q12 | ¿Stack local-only o deploy incluido en alcance del framework? | DEC-011. |

---

## 6. Tiempos de referencia por fase (PRJ-MAESTRO-V1)

Solo como calibración inicial; cada proyecto difiere.

| Fase | Duración | Iteraciones | Notas |
|---|---|---|---|
| 00-setup | 1 día | 1 | Express si se aplica MEM-Q01 a MEM-Q12 temprano |
| 01-discovery | 1 día | 1 | Con el PO disponible |
| 02-planning | 1 día | 1 | 14 ADRs + DATA + API + UX + THREAT |
| 03-development | 1 día calendario, 9 iteraciones | 9 | 14 épicas + loop transversal por épica |
| 04-delivery | 1 día | 1 | Compose prod + CHANGELOG + CI/CD |
| 05-operations | 1 día | 1 | Observability + incident + runbook + tech debt |
| 06-retrospective | < 1 día | 1 | Este documento |

Total: ~5 días calendario para un proyecto "fat" como Maestro con el framework warm.

---

## 7. Acciones estructurales al framework (AI-1 a AI-8 de RETROSPECTIVE §9)

| # | Acción | Destino |
|---|---|---|
| AI-1 | Plantilla de ADR de framework con sección "Breaking changes + paquetes afectados" | `framework-agentico/.../ADR_TEMPLATE.md` |
| AI-2 | Exit criteria Fase 00 incluye verificación GitHub org access | `00-setup/CHECKPOINT.md` |
| AI-3 | Regla transversal: healthchecks `--inet4-only` o IP literal | `rules/GENERAL_RULES.md` |
| AI-4 | Política: `/metrics` app no se difiere post-fase K | `05-operations/rules/RULES.md` |
| AI-5 | Runbook específico se escribe junto con alerta, no post-hoc | `05-operations/rules/RULES.md` |
| AI-6 | Dry-run mensual de restore en calendario | Humano |
| AI-7 | Cerrar ESC-001 (PAT git leak) | Humano |
| AI-8 | Primer dry-run restore post-tag v1.0.0-rc.1 | Humano |

Las AI-1 a AI-5 son cambios estructurales al framework y deberían aplicarse antes del próximo proyecto.

---

## 8. Nota final al PM

Si arrancás un nuevo proyecto:

1. Leé primero este archivo + `CHECKPOINT_GLOBAL.md` del proyecto anterior.
2. Hacé las 12 preguntas de §5 al humano **antes** de cerrar Fase 00.
3. Aplicá los defaults de §4 salvo que el humano indique lo contrario.
4. Evitá los 8 anti-patrones de §2 — todos costaron tiempo real en este proyecto.
5. Al cerrar, actualizá este archivo con lo nuevo que aprendiste; no sobreescribas lo de acá, acumulá.
