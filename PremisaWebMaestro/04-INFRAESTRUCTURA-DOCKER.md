# Infraestructura Docker y Ciclo de Vida de Deployments

> **Versión:** v4 (framework agéntico v4 / contrato `maestro.platform/v2`)
> **Última revisión:** 2026-05-07
> **Estado:** vigente
> **Reemplaza a:** `legacy/v3/PremisaWebMaestro/04-INFRAESTRUCTURA-DOCKER.md` (modelo v1 con instancias multi-tenant lógicas + ForwardAuth).

---

## Propósito de este documento

Este documento describe la infraestructura Docker de la **Web Maestro** v4: la topología de redes, cómo se crean y destruyen los **deployments** (un deployment = una app huésped + una empresa = un contenedor + una BD), los estados del ciclo de vida, los mecanismos de aislamiento, los límites de recursos y la estrategia de provisioning. Un agente que implemente el motor de provisioning, configure Traefik o gestione contenedores debe usar este documento como referencia.

---

## Cambio fundamental respecto a v1

En v1 el modelo era:

- **Instancias** multi-tenant lógicas con `company_id` por fila.
- **Traefik con middleware ForwardAuth** validando contra el Maestro y inyectando headers `X-Auth-*`.
- Reverse-proxy con identidad inyectada hacia las apps.
- Iframes en el portal para mostrar las apps.

En v4 el modelo es:

- **Deployments** físicos: un contenedor de app + una BD dedicada por par app+empresa. Sin `company_id` en queries de las apps.
- **Traefik solo termina TLS y enruta** (sin ForwardAuth, sin inyección de identidad).
- Las apps se autentican por sí mismas; el Maestro solo abre URLs en `target="_blank"`.
- Sin iframes.

---

## Topología general

### Nivel host (VPS o cloud)

```
                     ┌──────────────────────────────────┐
                     │       INTERNET (HTTPS 443)         │
                     └─────────────┬────────────────────┘
                                   │
                          ┌────────▼────────┐
                          │     Traefik      │
                          │  (TLS, HSTS,     │
                          │   rate limiting) │
                          └────────┬────────┘
                                   │
            ┌──────────────────────┼──────────────────────┐
            │                      │                      │
   ┌────────▼────────┐    ┌────────▼────────┐    ┌────────▼────────┐
   │   maestro-net   │    │ deployment-A-net │    │ deployment-B-net │
   │                  │    │  (privada)       │    │  (privada)       │
   │ ┌──────────────┐ │    │ ┌──────────────┐ │    │ ┌──────────────┐ │
   │ │ maestro-api  │ │    │ │ app-X-acme   │ │    │ │ app-Y-zenith │ │
   │ │ maestro-db   │ │    │ │ db-X-acme    │ │    │ │ db-Y-zenith  │ │
   │ │ maestro-redis│ │    │ └──────────────┘ │    │ └──────────────┘ │
   │ │   (opcional) │ │    │                  │    │                  │
   │ └──────────────┘ │    │ Sin company_id   │    │ Sin company_id   │
   └──────────────────┘    └──────────────────┘    └──────────────────┘
```

**Reglas**:
- Solo Traefik bindea puertos del host (80, 443). Ningún otro contenedor expone puertos al exterior.
- `maestro-net` es la red Docker compartida del **Maestro mismo** (api + db + redis opcional + observabilidad opcional).
- Cada deployment tiene su **red Docker dedicada** (`app-<slug>-<empresa>-net`) donde solo conviven el contenedor de app y su BD.
- Traefik está conectado a **todas** las redes (a `maestro-net` y a cada `deployment-*-net`) para poder enrutar tráfico hacia cada deployment. Pero esa conexión es solo de salida (Traefik → contenedor), nunca permite tráfico inverso entre redes.

### Nivel Maestro (red `maestro-net`)

Servicios:
- `maestro-traefik` — reverse proxy + TLS termination + redirect HTTP→HTTPS + rate limiting + HSTS.
- `maestro-api` — backend del Maestro (registry + admin + provisioner).
- `maestro-db` — BD del Maestro (PostgreSQL recomendado).
- `maestro-redis` (opcional) — cache de branding, rate limiting, sesiones de admins.
- Observabilidad opcional: `obs-prometheus`, `obs-loki`, `obs-grafana`, `obs-promtail`. Pueden vivir en una red `obs-net` separada con bridge a `maestro-net`.

### Nivel deployment (red `app-<slug>-<empresa>-net`)

Servicios mínimos:
- `app-<slug>-<empresa>` — contenedor de la app huésped.
- `db-<slug>-<empresa>` — BD dedicada (si la app declara `requires.database != "none"`).

Si la app declara servicios adicionales (ej: workers, scheduler, redis propio), pueden agregarse a la misma red, siempre que estén declarados en su `docker-compose.yml` y respeten los límites de recursos del `maestro.yaml`.

---

## Provisioning de un deployment

### Flujo paso a paso

Cuando un admin del Maestro ejecuta `POST /api/v2/deployments` con `{application_id, company_id}`:

1. **Validación**:
   - Verificar que `applications.status = active` y `companies.status = active`.
   - Verificar que NO existe ya un deployment activo para el par (constraint UNIQUE de la BD del Maestro).
   - Validar que el `maestro.yaml` registrado en `applications` cumple el JSON Schema v2.

2. **Reserva de recursos**:
   - Generar nombres canónicos: `container_name = app-<app_slug>-<company_slug>`, `db_container_name = db-<app_slug>-<company_slug>`, `network_name = app-<app_slug>-<company_slug>-net` (≤ 63 chars cada uno).
   - Generar credenciales aleatorias:
     - DB password: ≥ 32 chars aleatorios.
     - `MAESTRO_API_KEY`: ≥ 32 chars aleatorios.
     - `MAESTRO_WEBHOOK_SECRET`: ≥ 32 chars aleatorios.
   - Cifrar las tres últimas con AES-256 y persistir en `api_keys`, `webhook_secrets`.

3. **Creación de red Docker**:
   - `docker network create --driver bridge --internal=false <network_name>`.
   - `--internal=false` permite que la red tenga acceso saliente a internet (para que la app pueda llamar a APIs externas).
   - Conectar Traefik a la red para enrutar tráfico inbound.

4. **Provisioning de la BD** (si aplica):
   - `docker run -d --name <db_container_name> --network <network_name> --env-file ... <db_image>`.
   - Esperar a que la BD esté lista (`pg_isready` o equivalente, max 60s).
   - Crear database, usuario y password generados.

5. **Provisioning del contenedor de la app**:
   - Construir `DATABASE_URL` con las credenciales generadas.
   - Inyectar ENV vars: `DATABASE_URL`, `MAESTRO_API_KEY`, `MAESTRO_WEBHOOK_SECRET`, `SUPERADMIN_INITIAL_PASSWORD` (generado o leído de un secret store), `JWT_SECRET` o `APP_KEY` (según stack), más las custom env vars declaradas en `maestro.yaml` `env:`.
   - `docker run -d --name <container_name> --network <network_name> --memory <m> --cpus <c> --user <non-root> --security-opt no-new-privileges --restart unless-stopped --health-cmd "..." <image_ref>`.
   - Exponer al exterior vía Traefik label: `traefik.http.routers.<name>.rule=Host("<app_slug>-<company_slug>.<base_domain>")`.

6. **Migrations + Seeding**:
   - Ejecutar migraciones: `docker exec <container_name> <comando_migrations>` (según stack: `php artisan migrate`, `npm run migrate`, `python manage.py migrate`, etc.).
   - Ejecutar seeder del superadmin (fase 05-seeding): `docker exec <container_name> <comando_seed>`.
   - Validar exit codes; si fallan, deployment pasa a `provisioning_failed` y se alerta.

7. **Validación final**:
   - Esperar a que el health check responda 200 (max 60s, configurable).
   - Marcar deployment como `healthy`.
   - Iniciar job periódico de health checks y job de consumo de `/maestro/branding`.

8. **Audit log**:
   - Registrar `deployment.provision` con `actor_user_id`, `resource_id` (deployment.id), `payload_after` (estado del deployment).

### Idempotencia

El motor de provisioning es **idempotente**: si una llamada a `POST /api/v2/deployments` se reintenta (ej: por timeout en cliente), el motor verifica si el deployment ya está en estado `provisioning` o posterior y reanuda desde donde quedó, en lugar de crear uno nuevo.

### Rollback en fallo

Si cualquier paso falla:
- Limpieza de recursos: detener y borrar contenedores creados, eliminar la red Docker.
- Marcar deployment como `provisioning_failed`.
- Audit log: `deployment.provision.failed` con detalle del error.
- La BD del deployment, si llegó a crearse, se preserva 90 días (no-negociable de retención) salvo que el PO confirme purgado inmediato.

---

## Ciclo de vida del deployment

### Máquina de estados

```
              ┌──────────────────────────────────────┐
              │                                       │
              │   ┌──────────┐                        │
              │   │provisioning│ (recursos creandose)  │
              │   └─────┬─────┘                        │
              │         │                              │
              │   ┌─────▼─────┐                        │
              │   │  starting  │ (esperando health 200)│
              │   └─────┬─────┘                        │
              │         │                              │
              │   ┌─────▼─────┐                        │
              │   │   healthy  │◄──┐                   │
              │   └─────┬─────┘   │                   │
              │         │          │                   │
              │   ┌─────▼─────┐   │                   │
              │   │  degraded  │───┘ (recovery)        │
              │   └─────┬─────┘                        │
              │         │                              │
              │   ┌─────▼─────┐                        │
              │   │ suspended  │ (intervencion manual) │
              │   └─────┬─────┘                        │
              │         │                              │
              │   ┌─────▼─────┐                        │
              │   │ destroyed  │ (BD preservada 90 dias)│
              │   └─────┬─────┘                        │
              │         │ (>= 90 dias + confirmacion PO)│
              │   ┌─────▼─────┐                        │
              │   │   purged   │                        │
              │   └───────────┘                        │
              └──────────────────────────────────────┘
```

### Definición de cada estado

| Estado | Definición | Quién lo cambia |
|---|---|---|
| `provisioning` | Recursos en creación (red, BD, contenedor) | Motor de provisioning |
| `starting` | Contenedor levantado, esperando primer health check 200 | Worker de health |
| `healthy` | Health check OK; tráfico activo | Worker de health |
| `degraded` | Health check fallando (1-9 fallos consecutivos), o consumo de branding fallido tras 3 intentos | Worker de health |
| `suspended` | Health check fallando ≥ 10 veces consecutivas, o suspensión manual por admin | Worker de health o admin |
| `destroyed` | Contenedor y red eliminados; BD preservada por 90 días | Admin via `DELETE /api/v2/deployments/{id}` |
| `purged` | BD eliminada (irrecuperable) | Admin con confirmación PO + audit log |

### Acciones correctivas escalonadas

Cuando el health check falla (HTTP ≠ 200 o timeout):

| Fallos consecutivos | Acción |
|---|---|
| 1-2 | Loguear; no actuar |
| 3 | Restart automático del contenedor (`docker restart`); reset del contador si el restart logra `healthy` |
| 4-5 | Estado `degraded`; notificación al admin (email/Slack) |
| 6-9 | Mantener `degraded`; intentar restart cada 5 min |
| 10+ | Estado `suspended`; alerta crítica; intervención manual requerida |

El contador `consecutive_health_failures` se resetea a 0 cuando el health check responde 200.

### Transiciones permitidas

- `provisioning` → `starting`: automática al terminar el provisioning.
- `starting` → `healthy`: automática al primer health check 200.
- `starting` → `provisioning_failed`: si el health check no responde 200 en 60s.
- `healthy` ↔ `degraded`: por contador de health checks.
- `degraded` → `suspended`: por umbral de fallos.
- `suspended` → `healthy`: solo manual (admin retira la suspensión y el primer health check responde 200).
- `healthy/degraded/suspended` → `destroyed`: solo manual (admin via API + audit log).
- `destroyed` → `purged`: solo después de 90 días + confirmación PO + audit log.
- `destroyed` → `healthy`: posible **restauración** desde backup dentro de los 90 días, con audit log.

Las transiciones no permitidas se rechazan con `HTTP 422`.

---

## Aislamiento entre deployments

### Aislamiento de red

- Cada deployment tiene su propia red Docker `bridge`.
- Los contenedores de un deployment **NO** pueden hacer ping ni resolver DNS de los contenedores de otro deployment.
- Solo Traefik puede enrutar tráfico desde el exterior hacia un deployment, y solo en la dirección inbound.
- **NO** existe red compartida entre deployments. Si dos apps de la misma empresa necesitan intercambiar datos, lo hacen vía **API Gateway del Maestro** (mediado por el Maestro, con audit log).

### Aislamiento de datos

- Cada deployment tiene su propia BD con credenciales únicas.
- Las credenciales **NO** se comparten ni con el Maestro ni con otros deployments.
- Compartir BD entre deployments es arquitectónicamente imposible.

### Aislamiento de privilegios

- Contenedores no-root (`USER` no-root en Dockerfile).
- `--security-opt=no-new-privileges` (impide escalada a root vía setuid).
- Volúmenes montados solo en paths específicos (`/app/storage` típicamente), nunca el filesystem del host.
- **Prohibido** montar `/var/run/docker.sock` en contenedores de apps huésped (eso permitiría a la app controlar el daemon Docker).
- **Prohibido** `--privileged`.
- **Prohibido** `--network=host`.

---

## Límites de recursos

### Memoria

Tiers permitidos: `256m`, `512m`, `1g`, `2g`, `4g`. El motor de provisioning aplica `--memory <valor>` al `docker run`. Un contenedor que excede el límite es matado por el OOM Killer del kernel; el restart automático lo reintenta.

### CPU

Permitido: `0.25` a `4.0` cores en incrementos de `0.01`. Aplicado vía `--cpus <valor>`. Excesos son throttled por el scheduler.

### Disco

Volumen para datos persistentes:
- `<deployment_name>-storage` para archivos de la app (uploads, cache, etc.).
- `<deployment_name>-db-data` para datos de la BD.

Los volúmenes son persistentes a través de restarts del contenedor. Se preservan junto con la BD durante los 90 días post-destroy.

### Red

Sin límite de bandwidth por defecto, pero rate limiting global aplicado por Traefik (default 100 req/min/IP, configurable por endpoint).

---

## Naming canónico

| Recurso | Patrón | Ejemplo | Restricciones |
|---|---|---|---|
| Contenedor de app | `app-<slug>-<empresa>` | `app-inventario-acme` | ≤ 63 chars |
| Contenedor de BD | `db-<slug>-<empresa>` | `db-inventario-acme` | ≤ 63 chars |
| Red Docker | `app-<slug>-<empresa>-net` | `app-inventario-acme-net` | ≤ 63 chars |
| Volumen storage | `<container>-storage` | `app-inventario-acme-storage` | — |
| Volumen DB data | `<container>-db-data` | `app-inventario-acme-db-data` | — |

`slug` y `empresa` cumplen regex `^[a-z0-9][a-z0-9-]{2,49}[a-z0-9]$` (mismo regex que el `slug` en `maestro.yaml`).

Detalle adicional en `docs/CONVENCIONES_PLATAFORMA.md`.

---

## Imágenes Docker

### De la Web Maestro

- Construidas en CI del repo del Maestro.
- Multi-stage build, non-root, `HEALTHCHECK`.
- Publicadas en registry privado (ej: `ghcr.io/<org>/maestro-api:<semver>`).
- Tag inmutable (no se reescriben). Para rollback se usa el digest `@sha256:...`.

### De las apps huésped

- Construidas en CI del fork de cada app.
- Validación obligatoria (vía CI):
  - `Dockerfile` con `USER` no-root (estática).
  - `EXPOSE` coincide con `requires.ports.app` del `maestro.yaml`.
  - Imagen ≤ 500 MB comprimida (warning a 350 MB).
  - Sin secretos, claves privadas ni `.env` en la imagen.
  - Scan de vulnerabilidades (trivy o equivalente) sin CRITICAL/HIGH.
  - Firma con cosign (recomendado).
- Publicadas en registry de la app (ej: `ghcr.io/<owner>/<app_slug>:<sha>` o `:<semver>`).
- Tag `:latest` **PROHIBIDO** en producción.

---

## Backup automatizado

Como cumplimiento del No-negociable trece:

- Job `cron` corre diariamente entre 02:00-04:00 hora del servidor.
- Para cada deployment activo: `pg_dump` (o equivalente según motor) de la BD del deployment.
- Para la BD del Maestro: `pg_dump` siempre.
- Cifrado con AES-256 antes de subir.
- Almacenamiento externo al VPS: Azure Blob, S3, GCS u otro. Configurable.
- Retención mínima: 30 días. NO reducible.
- BD del Maestro: backup adicional **antes de cada migración de schema**.
- Restauración: documentada en `docs/runbook.md` (lo genera la fase 06-operations).

Audit log: cada backup se registra (`backup.success` o `backup.failed`) con tamaño, duración y destination.

---

## Referencias normativas

- `01-PREMISAS-Y-NO-NEGOCIABLES.md` — premisas 2 (single-tenant), 6 (límites de recursos), 7 (mínimo privilegio); no-negociables 2, 7, 9, 10, 13.
- `02-MODELO-DE-DATOS.md` — tabla `deployments` y sus estados.
- `03-AUTENTICACION-Y-AUTORIZACION.md` — generación e inyección de `MAESTRO_API_KEY` y `MAESTRO_WEBHOOK_SECRET` en provisioning.
- `06-CONTRATO-MAESTRO-YAML.md` — campos `requires`, `resources`, `health` que el motor de provisioning consume.
- `08-CICD-Y-GOBERNANZA.md` — pipelines que producen las imágenes Docker.
- `09-SEGURIDAD.md` — TLS, no-new-privileges, scan de imágenes.
- `10-OBSERVABILIDAD.md` — métricas de provisioning, health, recursos.
- `docs/CONVENCIONES_PLATAFORMA.md` — naming canónico (lado app huésped).

---

## Historial de revisiones

| Versión | Fecha | Cambio |
|---|---|---|
| 4.0.0 | 2026-05-07 | Versión inicial v4. Rediseña la infraestructura para single-tenant físico (un deployment = un par app+empresa con red y BD propias). Elimina ForwardAuth de Traefik. Reemplaza al v1 (legacy en `legacy/v3/PremisaWebMaestro/04-INFRAESTRUCTURA-DOCKER.md`). |
