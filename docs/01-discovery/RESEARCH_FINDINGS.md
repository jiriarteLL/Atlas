# Hallazgos de Investigación — Maestro Platform V1

> **Fase:** 01-Discovery
> **Agente:** researcher
> **Fecha:** 2026-04-16
> **Proyecto:** PRJ-MAESTRO-V1

---

## 1. Dominio

Maestro Platform es una **plataforma multi-tenant de clase empresarial tipo PaaS interno** (Platform-as-a-Service) que aloja, orquesta y gobierna múltiples aplicaciones dockerizadas bajo un portal web unificado con autenticación centralizada.

El dominio combina tres áreas técnicas maduras pero rara vez integradas en una sola plataforma coherente:

1. **Identity Provider / SSO**: emisión de tokens OAuth2/JWT, federación con Microsoft Entra ID, gestión de sesiones, roles y permisos multi-empresa.
2. **Container orchestration**: ciclo de vida de contenedores Docker, redes aisladas, provisioning de bases de datos, health checks, auto-healing.
3. **Reverse proxy y API gateway**: terminación TLS, ForwardAuth, rate limiting, ruteo dinámico por subdominio, gateway inter-aplicaciones.

El problema de negocio que resuelve es la **fragmentación operativa** que sufren las organizaciones con múltiples herramientas internas (cada una con su login, gestión de usuarios, deuda técnica de seguridad), unificándolas bajo un único portal y un único modelo de identidad.

Metáfora arquitectónica: el Maestro es un **sistema operativo para aplicaciones internas**. Gestiona procesos (contenedores), memoria (recursos), seguridad (autenticación) e interfaz (portal) para que cada app huésped se enfoque exclusivamente en su lógica de negocio.

---

## 2. Usuarios Objetivo (5 grupos de stakeholders)

### 2.1 Empresas / Tenants
- **Perfil**: organizaciones clientes que contratan licencias de aplicaciones.
- **Necesidades**: acceso unificado a herramientas, control de costos, visibilidad de uso, seguridad.
- **Pain points hoy**: cada herramienta interna tiene su propio login y gestión de usuarios; no hay reporte unificado de licencias; onboarding/offboarding de empleados es manual por app.
- **Métricas que les importan**: usuarios activos, aplicaciones licenciadas, consumo, cumplimiento regulatorio.

### 2.2 Usuarios finales (empleados)
- **Perfil**: empleados de las empresas tenant que usan las apps día a día.
- **Nivel técnico**: heterogéneo (desde contadores hasta operarios de planta).
- **Necesidades**: un único login, transiciones rápidas entre apps, interfaz consistente.
- **Pain points hoy**: múltiples passwords, tener que re-autenticarse cada vez que cambian de herramienta, navegación diferente por cada app.
- **Métricas que les importan**: velocidad de carga, fluidez, disponibilidad.

### 2.3 Desarrolladores de aplicaciones
- **Perfil**: equipos internos o externos que crean apps para alojarse en Maestro.
- **Nivel técnico**: alto (backend/frontend dev).
- **Necesidades**: SDK claro, contrato estándar bien documentado, CI/CD automatizado, asistente IA (CLAUDE.md).
- **Pain points anticipados**: curva de aprendizaje del contrato `maestro.yaml`, debugging en producción sin acceso directo a contenedores, onboarding de nuevos stacks.
- **Métricas que les importan**: tiempo hasta primer despliegue, claridad de errores del `maestro-cli`, cobertura de SDKs por lenguaje.

### 2.4 Administradores del Maestro
- **Perfil**: equipo operador de la plataforma (~1-3 personas al inicio).
- **Nivel técnico**: muy alto (DevOps, SRE).
- **Necesidades**: observabilidad completa, gobernanza de licencias, herramientas de escalado sin downtime, runbooks.
- **Pain points anticipados**: diagnóstico de instancias con cold start lento, escalamiento horizontal del VPS, gestión de certificados TLS cuando Let's Encrypt falle.
- **Métricas que les importan**: uptime por instancia, latencia ForwardAuth, tasa de éxito de backups, incidentes por semana.

### 2.5 Dirección / C-Level
- **Perfil**: tomadores de decisiones estratégicas y financieras.
- **Necesidades**: ROI, cumplimiento regulatorio, reportes ejecutivos de uso y salud.
- **Pain points anticipados**: visibilidad del valor entregado por la plataforma, control del costo total de propiedad.
- **Métricas que les importan**: empresas activas, apps licenciadas, MRR/ARR, cumplimiento de SLA, auditorías pasadas.

---

## 3. Contexto

- **Versión existente**: la premisa menciona "Maestro ya existe en una versión inicial" con Laravel + React + Docker en Azure, con auth user/pass y Microsoft. Sin embargo, el repo destino está esencialmente limpio (primer commit 2b88f4d, sin código del Maestro original). **Interpretación**: la v0 es aspiracional/de referencia, y partimos construyendo sobre el template Tailwise Laravel.
- **Escala inicial V1 (DEC-017)**: **1 empresa tenant × 7 apps huésped** en primeros 12 meses. El tenant inicial es probablemente LLyAsoc u organización similar alojando sus herramientas internas. La arquitectura multi-tenant se mantiene inmutable según la premisa para permitir crecimiento post-V1 sin refactor mayor.
- **Template base disponible**: `Tailwise Bundle/Laravel Version - v1.0.3/Source/` (backend) y `Tailwise Bundle/React Version - v1.0.9/` (portal). No reutilizamos el Vue ni el HTML puro.
- **VPS Azure**: existe pero queda fuera del framework (DEC-011). El framework produce artefactos de deploy; el humano ejecuta el deploy.
- **Datos a migrar**: ninguno. Arrancamos greenfield.
- **Integraciones externas obligatorias**:
  - Microsoft Entra ID (OAuth2 flow)
  - Let's Encrypt (ACME, certificados automáticos)
  - Azure Blob Storage (backups cifrados)
  - GitHub / GitHub Actions (pipelines CI/CD y registry de imágenes)

---

## 4. Competidores / Referencias

| Solución | Qué hace bien | Qué no cubre / diferencia con Maestro |
|---|---|---|
| **Heroku** | PaaS simple, marketplace de add-ons, SSO básico | Proprietario, no on-prem, modelo de precios no predecible, sin multi-tenancy real de apps del mismo cliente |
| **Railway / Render / Fly.io** | DX moderna, deploy por push | No son multi-tenant gobernados (cada proyecto es aislado pero no hay capa de "empresa" sobre ellos), sin SSO centralizado por defecto |
| **Vercel** | Frontend-focus, preview deploys | No genérico para backends complejos dockerizados, no multi-tenant empresarial |
| **AWS App Runner / Azure Container Apps** | Serverless containers, integración cloud nativa | Sin capa de identidad unificada a nivel plataforma, cada app implementa su propio auth |
| **Kubernetes + Keycloak + Istio** | Flexibilidad total, ecosistema maduro | Complejidad operativa altísima, no integrado out-of-the-box, requiere equipo SRE grande |
| **Okta + App Catalog** | SSO enterprise robusto | No orquesta infraestructura, solo es IdP, no provisiona apps |
| **Microsoft Intune + Entra ID** | Gestión de apps SaaS con SSO | Orientado a apps de terceros, no aloja apps propias dockerizadas |
| **Portainer / Rancher** | UI para gestión de Docker/K8s | Orientado a operadores, no tiene capa de portal para usuarios finales ni modelo multi-tenant de negocio |

### 4.1 Conclusión de la comparativa

Maestro ocupa un **nicho específico**: la intersección de PaaS interno + IdP + portal para usuarios finales, con enfoque en multi-tenant B2B donde cada empresa tenant tiene múltiples apps licenciadas. Ningún competidor cubre los 3 ejes simultáneamente sin integración manual pesada.

### 4.2 Diferenciadores clave del Maestro

1. **Contrato estandarizado obligatorio** (`maestro.yaml`) que fuerza compatibilidad por construcción.
2. **Agnosticismo tecnológico** para las apps huésped (Node/Python/Go/Java/PHP/.NET vía Docker).
3. **Sistema agéntico de IA** integrado (CLAUDE.md por app huésped con reglas heredadas de plataforma).
4. **Aislamiento de red por instancia** a nivel Docker, no solo a nivel aplicación.

---

## 5. Insights Clave

### 5.1 El contrato `maestro.yaml` es el foso defensivo
La idea central del Maestro no es técnica sino **contractual**: fuerza a las apps huésped a cumplir un contrato validado automáticamente en CI/CD, eliminando clases enteras de bugs de integración. Sin este contrato, Maestro sería solo otro PaaS; con él, es una plataforma de gobernanza.

### 5.2 ForwardAuth es el cuello de botella crítico
Cada request a cualquier app huésped pasa por validación del token contra el Maestro. A 50 usuarios concurrentes × ~10 req/seg = 500 req/seg hacia `/api/auth/validate`. El objetivo <50ms p95 **requiere cache Redis desde V1 si queremos margen**, no esperar a la fase 9 de hardening. Recomendamos revisar esta decisión con el software-architect en Planning.

### 5.3 El aislamiento multi-tenant es doble
- **Red**: Docker networks dedicadas por instancia.
- **Aplicación**: middleware del SDK filtra por `company_id` automáticamente.

Ambos son necesarios. Solo red deja el riesgo de lógica bugs; solo aplicación deja el riesgo de lateral movement si un contenedor cae. La defensa en profundidad es el diferenciador vs competidores.

### 5.4 El Docker socket es una superficie de ataque
El motor de provisioning requiere acceso a la Docker API para crear contenedores, redes y BDs. Esto significa que el Maestro **tiene acceso a la máquina host** y un compromiso del Maestro = compromiso total. Mitigar con: servicio de provisioning dedicado con mínimo privilegio, rootless Docker si es posible, o Docker-in-Docker con socket proxy.

### 5.5 El cold start y las instancias dormidas son UX críticos
A 15s de cold start, los usuarios perciben lentitud. El manejo visual (pantalla de carga con tiempo estimado) es tan importante como la latencia real. En V1, no dormir instancias por defecto hasta que tengamos métricas reales de uso.

### 5.6 Microsoft Entra ID es el canal de adquisición
Muchas empresas cliente ya están en Microsoft 365. OAuth2 con Entra ID elimina fricción de onboarding y es un argumento comercial fuerte. Debe funcionar impecablemente desde V1.

### 5.7 Escala V1 muy baja permite priorizar correctness (DEC-017)
La escala inicial V1 (1 empresa × 7 apps ≈ 7 usuarios/app concurrentes en peor caso de 50 concurrentes totales) libera presión sobre los objetivos de performance de la premisa (<50ms p95 ForwardAuth, <15s cold start). Alcanzables con margen amplio. **Implicación estratégica**: Fase 03 puede priorizar correctness, testabilidad y claridad arquitectónica sobre micro-optimizaciones. La cache Redis sigue recomendada por defensa en profundidad (tolerancia a picos, reducción de carga en BD Maestro) pero deja de ser crítica para cumplir SLA. El software-architect debería documentar esta trade-off en un ADR específico de caching.

---

## 6. Riesgos de Negocio y Técnicos

| ID | Riesgo | Probabilidad | Impacto | Mitigación propuesta |
|---|---|---|---|---|
| R-001 | **Leak de datos entre tenants** por bug en middleware company_id | Media | Catastrófico | Doble capa (red + app); tests de integración que intenten crossing; auditoría de código del middleware |
| R-002 | **Compromiso del Maestro** → acceso a Docker socket → compromiso de todo el VPS | Baja | Catastrófico | Servicio provisioning aislado con permisos mínimos; socket proxy; hardening del contenedor Maestro |
| R-003 | **Latencia ForwardAuth** supera el objetivo de 50ms p95 | Alta sin cache | Alto | Cache Redis desde V1 para validación de tokens (adelantar fase 9) |
| R-004 | **Cold start >15s** genera mala UX en primer uso del día | Media | Medio | No dormir instancias por defecto en V1; medir tráfico real; dormir solo tras >1h sin actividad |
| R-005 | **Passport/OAuth2 config compleja** retrasa fase 1 | Media | Alto | Asignar al software-architect un ADR temprano con prototipo de flujo OAuth2 + JWT + refresh |
| R-006 | **Certificados TLS (Let's Encrypt) no renuevan** en producción | Baja | Alto | Monitoreo con alerta a 30 días antes de expiración; runbook de renovación manual |
| R-007 | **Compliance no identificado** bloquea despliegue a clientes con requerimientos específicos | Alta | Medio | ESC-002 abierta; compliance-analyst propone shortlist; humano valida con legal |
| R-008 | **Velocidad del VPS Azure** insuficiente para 50 usuarios concurrentes | Media | Medio | Performance-analyst dimensiona en Planning; prueba de carga en Delivery |
| R-009 | **Escalabilidad horizontal** del Maestro no contemplada en V1 (single-node) | Alta | Medio | Documentar como deuda técnica; diseñar BD y estados para soportar multi-node en V2 |
| R-010 | **Complejidad del sistema agéntico** retrasa fase 7 | Media | Bajo | Fase 7 es opcional si las fases críticas (1-4) requieren más tiempo |

---

## 7. Regulaciones Aplicables — Propuesta del compliance-analyst

> ⚠️ **Pendiente de validación por humano y equipo legal (ESC-002).** El humano reportó desconocer las regulaciones aplicables. El compliance-analyst transversal propone este shortlist basado en el tipo de producto (SaaS B2B multi-tenant con datos de empleados).

### 7.1 Probablemente aplicables

| Marco | Aplica si... | Impacto arquitectónico |
|---|---|---|
| **GDPR** (Reglamento UE 2016/679) | Hay usuarios o empresas cliente en UE | Derecho al olvido (soft delete con purga), portabilidad de datos, DPA con clientes, logs con retención definida |
| **LGPD** (Brasil, Ley 13.709/2018) | Hay clientes en Brasil | Similar a GDPR; requiere DPO y registro de actividades de tratamiento |
| **SOC 2 Type II** (AICPA) | Clientes empresariales B2B | Controles de seguridad, disponibilidad, confidencialidad documentados y auditados anualmente |
| **ISO/IEC 27001** | Necesidad de certificación internacional | SGSI documentado; análisis de riesgos; auditoría externa |

### 7.2 Posiblemente aplicables según cliente final

| Marco | Aplica si... |
|---|---|
| **HIPAA** (US) | Hay apps huésped que procesan PHI (datos de salud) |
| **PCI-DSS** | Hay apps huésped que procesan tarjetas de crédito |
| **FedRAMP** | Hay clientes del gobierno federal de EE.UU. |

### 7.3 Estándares complementarios recomendados

- **NIST Cybersecurity Framework** — guía para threat modeling y controles.
- **CIS Benchmarks** — hardening de Docker, Linux y PostgreSQL.
- **OWASP Top 10** — ya es estándar en security-auditor transversal.
- **OWASP ASVS** — para la capa de autenticación (nivel 2 recomendado).

### 7.4 Recomendación del compliance-analyst

Para V1, **adoptar como MUST HAVE**: GDPR + SOC 2 Type II (controles, no certificación todavía) + CIS Docker Benchmark + OWASP Top 10 + OWASP ASVS Nivel 2. Es la combinación mínima creíble para vender B2B a empresas medianas y grandes.

### 7.5 Validación por humano (2026-04-16) — DEC-013

El Product Owner **validó** el shortlist propuesto. Queda cerrada la ESC-002. Compliance MUST HAVE V1 definitivo:
- **GDPR** (Reglamento UE 2016/679) — retención mínima legal (DEC-019), derecho al olvido, DPA, DPIA donde aplique.
- **SOC 2 Type II controles** (sin certificación formal V1) — controles documentados y aplicados; certificación auditada post-V1.
- **CIS Docker Benchmark** — hardening obligatorio de contenedores, verificado por security-auditor.
- **OWASP Top 10 + ASVS Nivel 2** — mitigaciones estándar y verificación formal de la capa de autenticación.

**Fuera de V1**: LGPD (no hay clientes BR), HIPAA (aplica a apps huésped específicas), PCI-DSS (idem), FedRAMP (no aplica).

---

## 8. Gaps de información — TODOS RESUELTOS (2026-04-16)

| # | Pregunta original | Resolución |
|---|---|---|
| 1 | Jurisdicciones / compliance aplicable | ✅ **DEC-013**: GDPR + SOC 2 Type II controles + CIS Docker + OWASP ASVS L2 como MUST V1. Otros fuera de V1. |
| 2 | Volumen esperado 12 meses | ✅ **DEC-017**: 1 empresa × 7 apps en primeros 12 meses. Arquitectura multi-tenant se mantiene. |
| 3 | Modelo de pricing | ✅ **DEC-018**: solo ABM V1 de empresas, usuarios, apps y pivotes. Sin billing/pricing/tiers con lógica. |
| 4 | Retención más allá del mínimo legal | ✅ **DEC-019**: solo mínimos legales (30 días backups / 90 días post-destrucción). Purga agresiva pasados esos plazos. |
| 5 | Ventanas de mantenimiento | ✅ **DEC-020**: ventanas mínimas permitidas, no zero-downtime obligatorio. SLA 99.5% se mantiene. |
| 6 | Idiomas del portal | ✅ **DEC-014**: solo español V1. |
| 7 | Accesibilidad | ✅ **DEC-015**: WCAG 2.1 AA = WON'T V1. Baseline HTML semántico y contraste razonable. |
| 8 | Plan de soporte a clientes | ✅ **DEC-021**: canal de soporte se gestiona fuera del Maestro. Sin SLA de respuesta ni ticket system integrado V1. |

Adicional resuelto en la misma sesión:
- **MFA propio (TOTP)**: ✅ **DEC-016** — WON'T V1 (Entra ID cubre MFA para ese flujo).

**Discovery cerrada.** Todos los inputs necesarios para Planning están disponibles.

---

## 9. Preset activo y restricciones heredadas

- **Preset**: `maestro-platform` (dual invertido de `web-maestro`). Todas las obligaciones del preset son requisitos no funcionales MUST HAVE.
- **Constitución del proyecto**: los 10 no-negociables de `PremisaWebMaestro/01-PREMISAS-Y-NO-NEGOCIABLES.md` son ley. Violarlos invalida el diseño.
- **DEC-012 (zero local installs)**: el proyecto debe ser 100% portátil vía Docker, sin runtimes en el host.
- **DEC-011 (VPS out-of-scope)**: el framework genera artefactos de deploy pero no despliega; el humano opera el VPS.

---

## 10. Entregables al `requirements-analyst`

Este researcher entrega al requirements-analyst:
1. Perfil completo de 5 grupos de usuarios con pain points y métricas de éxito.
2. 10 riesgos identificados que deben mapearse a mitigaciones en RNF.
3. Shortlist de compliance para marcar como RNF MUST HAVE (pendiente validación humana).
4. 6 insights clave que impactan decisiones de arquitectura.
5. 8 gaps de información que requieren respuesta del humano para priorización MoSCoW final.
