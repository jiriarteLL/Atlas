# Web Maestro — Índice Maestro de Arquitectura

> **Versión:** v4 (framework agéntico v4 / contrato `maestro.platform/v2`)
> **Última revisión:** 2026-05-07
> **Estado:** vigente
> **Reemplaza a:** `legacy/v3/PremisaWebMaestro/00-INDICE-MAESTRO.md` (modelo v1).

---

## Qué es este conjunto de documentos

Este conjunto de archivos markdown constituye la **especificación arquitectónica completa** de la Web Maestro (= Web Anfitriona = plataforma Maestro = Maestro). Están redactados íntegramente en lenguaje natural para que un agente de IA pueda interpretarlos sin ambigüedad y tomar decisiones de implementación alineadas con la visión, las premisas y los límites aquí definidos.

Cada archivo es autónomo en su dominio pero interdependiente con los demás. Un agente que reciba estos documentos debe leerlos todos antes de generar código, tomar decisiones de diseño o proponer alternativas. Ningún archivo individual contiene la verdad completa; la arquitectura emerge de la lectura conjunta.

## Sinónimos que el PO puede usar

El PO (= Project Owner = Product Owner = dueño del producto) usa sinónimos intercambiables para varios conceptos. Todos los agentes deben reconocerlos correctamente:

- **Web Maestro** = Web Anfitriona = plataforma Maestro = Maestro = anfitriona (la plataforma orquestadora descrita en estos documentos).
- **Aplicación huésped** = app huésped = aplicación genérica = app genérica = aplicación tool = app tool (las apps que corren en deployments dentro de la Web Maestro).
- **PO** = Project Owner = Product Owner.

NO forzar un único término canónico; responder usando el término que el PO usó. Detalle en `framework-agentico/core/RULES.md` sección `glosario_de_sinonimos`.

## Orden de lectura obligatorio

El agente debe leer los archivos en este orden porque cada uno construye sobre los conceptos del anterior:

**Primero**: este mismo índice (`00-INDICE-MAESTRO.md`), porque establece contexto general, sinónimos y reglas de interpretación.

**Segundo**: `01-PREMISAS-Y-NO-NEGOCIABLES.md`. Es el documento más importante de todo el conjunto: los axiomas y los límites duros del sistema. Cualquier decisión técnica que contradiga lo establecido allí es inválida. El agente debe internalizar ese archivo como su constitución antes de proceder.

**Tercero**: `02-MODELO-DE-DATOS.md`. Define las entidades del Maestro (`companies`, `applications`, `deployments`, `api_keys`, `webhook_secrets`, `audit_log`, `admin_users`, `admin_roles`, `admin_permissions`) y sus relaciones. Necesario para entender qué se persiste, dónde y cómo.

**Cuarto**: `03-AUTENTICACION-Y-AUTORIZACION.md`. Define cómo se autentican los admins del Maestro (login propio), cómo se autentican los requests server-to-server entre Maestro y apps huésped (`X-Maestro-Api-Key`, `X-Maestro-Webhook-Secret`) y por qué el Maestro NO autentica usuarios finales.

**Quinto**: `04-INFRAESTRUCTURA-DOCKER.md`. Topología de redes Docker, provisioning de deployments (un contenedor + una BD por par app+empresa), ciclo de vida (provisioning → healthy → degraded → suspended → destroyed → purged), límites de recursos.

**Sexto**: `05-PORTAL-Y-RENDERIZADO.md`. Cómo el portal del Maestro renderiza el catálogo de apps disponibles para sus admins, cómo cambia el contexto de empresa, y por qué el click en una app abre la URL en `target="_blank"` (sin iframes, sin transferencia de identidad).

**Séptimo**: `06-CONTRATO-MAESTRO-YAML.md`. Estructura del archivo `maestro.yaml` v2 que cada app huésped declara en la raíz de su repo. Campos obligatorios y opcionales, JSON Schema, validación CLI, endpoint `POST /api/v2/apps/register`.

**Octavo**: `07-SISTEMA-AGENTICO.md`. Cómo el framework agéntico v4 (con preset `maestro-platform` activo) construye la Web Maestro a través de las 8 fases (00-setup → 07-retrospective).

**Noveno**: `08-CICD-Y-GOBERNANZA.md`. Pipelines CI/CD del Maestro y de las apps huésped, branch protection, self-registration de apps desde su CI, scans de imagen Docker.

**Décimo**: `09-SEGURIDAD.md`. Estrategia de defensa en profundidad. Threat model. Pre-commit hooks, CI deep scans, audit log inmutable.

**Undécimo**: `10-OBSERVABILIDAD.md`. Stack (Prometheus + Loki + Grafana), métricas clave del Maestro y por deployment, dashboards, alertas, runbooks.

**Duodécimo**: `11-PLAN-DE-IMPLEMENTACION.md`. Fases cronológicas para construir la Web Maestro v4, dependencias, entregables y criterios de aceptación.

## Reglas de interpretación

1. **Las premisas son axiomas**; los no-negociables son límites duros verificables. Una decisión que cumple una premisa pero viola un no-negociable es inválida.
2. **Si dos documentos contradicen**, prevalece `01-PREMISAS-Y-NO-NEGOCIABLES.md` sobre todos los demás.
3. **Si un concepto no está en estos documentos**, el agente NO lo inventa: escala al PO o consulta `framework-agentico/core/RULES.md`.
4. **El framework agéntico v4** (`framework-agentico/`) es el meta-sistema que orquesta la construcción de la Web Maestro. Estos documentos describen QUÉ se construye; el framework describe CÓMO.
5. **El preset activo cuando se construye la Web Maestro** es `maestro-platform` (ver `framework-agentico/agents/presets/maestro-platform/PRESET.md`). Cuando se construye una app huésped, el preset activo es `web-maestro` (ver `framework-agentico/core/PRESET_WEB_MAESTRO.md`). Ver `framework-agentico/core/RULES.md` sección `activacion_de_preset`.

## Mapa rápido del conjunto

| # | Archivo | Tema | Audiencia |
|---|---|---|---|
| 00 | `00-INDICE-MAESTRO.md` | Este índice | Toda |
| 01 | `01-PREMISAS-Y-NO-NEGOCIABLES.md` | Constitución | Toda (lectura obligatoria) |
| 02 | `02-MODELO-DE-DATOS.md` | Schema de la BD del Maestro | Backend, DBA, agentes data-architect |
| 03 | `03-AUTENTICACION-Y-AUTORIZACION.md` | Auth de admins + server-to-server | Backend, security-auditor |
| 04 | `04-INFRAESTRUCTURA-DOCKER.md` | Provisioning, redes, ciclo de vida | DevOps, agentes devops-engineer |
| 05 | `05-PORTAL-Y-RENDERIZADO.md` | Frontend del portal del Maestro | Frontend, agentes ux-designer/frontend-developer |
| 06 | `06-CONTRATO-MAESTRO-YAML.md` | Contrato de integración con apps | Toda app huésped, CI/CD, agentes |
| 07 | `07-SISTEMA-AGENTICO.md` | Framework agéntico v4 aplicado al Maestro | PM, orquestadores, agentes |
| 08 | `08-CICD-Y-GOBERNANZA.md` | Pipelines, repos, deploy | DevOps, agentes ci-cd-specialist |
| 09 | `09-SEGURIDAD.md` | Defensa en profundidad, threat model | Security-auditor, todos los agentes |
| 10 | `10-OBSERVABILIDAD.md` | Stack de monitoreo, métricas, alertas | Observability-engineer, operaciones |
| 11 | `11-PLAN-DE-IMPLEMENTACION.md` | Fases cronológicas y entregables | PO, PM |

## Referencias normativas

- `framework-agentico/CHANGELOG.md` — historial de cambios entre versiones del framework.
- `framework-agentico/core/RULES.md` — reglas generales del framework v4 (glosario, versionado, persistencia, activación de preset).
- `framework-agentico/core/PRESET_WEB_MAESTRO.md` — preset que aplica al construir apps huésped.
- `framework-agentico/agents/presets/maestro-platform/PRESET.md` — preset que aplica al construir la Web Maestro.
- `docs/APP_HUESPED_SPEC.md` — contrato `maestro.platform/v2` lado app.
- `legacy/v3/PremisaWebMaestro/` — versiones v1 (legacy, deprecadas).

---

## Historial de revisiones

| Versión | Fecha | Cambio |
|---|---|---|
| 4.0.0 | 2026-05-07 | Versión inicial v4. Reemplaza al índice v1 (legacy en `legacy/v3/PremisaWebMaestro/00-INDICE-MAESTRO.md`). |
