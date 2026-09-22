# Manual Metodológico — Despliegue a Test y Preproducción vía Dokploy

> **Versión:** 1.0.0
> **Última revisión:** 2026-09-22
> **Ámbito:** aplicaciones huésped (contrato `maestro.platform/v2`) sobre el VPS interno `llubuntu2` (`10.100.1.124`).
> **Audiencia:** **desarrolladores** (§1–§7) y **evaluador humano** (§8–§9), más los agentes que trabajan para cualquiera de los dos. Ver el reparto de responsabilidades en §0.1.
> **Panel Dokploy:** <http://10.100.1.124:3000/>
>
> **Precedencia normativa.** Este documento es **operativo**, no normativo. Ante conflicto mandan, en este orden:
> `PremisaWebMaestro/01-PREMISAS-Y-NO-NEGOCIABLES.md` → `EvaluacionAppHuesped/SPEC.md` →
> `docs/APP_HUESPED_SPEC.md` → `docs/CONVENCIONES_PLATAFORMA.md`.
> Este manual **no baja la vara de ningún requisito** de esos documentos: sólo describe cómo se opera el despliegue.

---

## 0. Los dos ambientes y la regla que los separa

Dokploy es un PaaS self-hosted (tipo Heroku) que corre en la red interna. Desde el **mismo panel** se despliegan los dos ambientes previos a producción, y lo que los distingue **no es la infraestructura sino el estado de evaluación de la app**:

| Ambiente | Tag | Qué es | Quién lo despliega |
|---|---|---|---|
| **Test** | `Test` | Aplicación **sin evaluar**. Sirve para que el desarrollador pruebe el desarrollo end-to-end en un entorno real. | **El desarrollador**, por su cuenta. |
| **Preproducción** | `Preprod` | Aplicación **ya evaluada contra el Maestro** y **aprobada por el evaluador humano**. Se registra en el catálogo del Maestro. | **El evaluador humano**, nunca el desarrollador. |

> **Regla dura.** Una app **no** puede pasar a `Preprod` sin haber atravesado la evaluación contra el Maestro (§7 y §8). Y el despliegue a `Preprod` lo ejecuta **el evaluador humano**: el desarrollador no lo hace, ni siquiera con un Gate 1 en PASS. Un despliegue `Preprod` hecho por fuera de esto es una violación del proceso y se revierte.

### 0.1 Quién hace qué

El proceso tiene **dos dueños** y el traspaso ocurre en un punto exacto. Esta tabla manda sobre cualquier lectura suelta del resto del manual:

| # | Etapa | Dueño | Sección |
|---|---|---|---|
| 1 | Desarrollo y despliegue a **Test** en Dokploy | **Desarrollador** | §1–§6 |
| 2 | Verificación del Test (`done` ≠ funciona) | **Desarrollador** | §6 |
| 3 | PR del fork contra la rama `tools/{app-name}` | **Desarrollador** | §7 Paso 2 |
| 4 | **Auto-evaluación Gate 1**, iterando hasta **PASS** | **Desarrollador** | §7 Paso 3 |
| 5 | **Re-evaluación independiente** (aunque el Gate 1 ya esté en PASS) | **Evaluador humano** | §8 |
| 6 | Gate 2 RUNTIME smoke | **Evaluador humano** | §8.2 |
| 7 | Merge a `tools/{app-name}` | **Evaluador humano** | §8.3 |
| 8 | **Despliegue a `Preprod`** y registro en el Maestro | **Evaluador humano** | §9 |
| 9 | Verificación del `Preprod` | **Evaluador humano** | §9.1 |
| 10 | **Entrega del proyecto al desarrollador** | **Evaluador humano** | §9.4 |
| 11 | Operación del `Preprod` de ahí en adelante | **Desarrollador** | §9.4 |

**El punto de traspaso es el 10.** Hasta ahí el `Preprod` es del evaluador humano; después de ahí, del desarrollador. Un desarrollador que toca el `Preprod` antes del traspaso está operando algo que todavía no es suyo.

**Qué NO es este ambiente.** No es un ambiente para datos reales. Corre sobre **HTTP sin certificado**: todo lo que se suba y la sesión entera viajan en claro por la red interna. Decíselo al usuario **antes** de que empiece a probar con archivos de clientes; no esperes a que pregunte.

Producción sigue su propio runbook (`docs/05-operations/`) y **no** se opera desde este manual.

---

## 1. Convención de nombres — OBLIGATORIA

Esto no es cosmético: el panel es compartido por varios proyectos y sin esta convención nadie sabe qué está mirando.

### 1.1 Proyecto

Al crear el proyecto en Dokploy hay que llenar **los tres campos**:

| Campo | Regla | Ejemplo |
|---|---|---|
| **Título (name)** | Nombre funcional de la aplicación, legible por un humano. Sin el ambiente adentro. | `Procesamiento Inteligente de Documentos` |
| **Descripción (description)** | Una o dos frases: para qué sirve la app, a qué tool/número corresponde y a quién pertenece. | `App 20 — extracción y clasificación de comprobantes. Owner: equipo Compras. Tool: tools/20_procesamiento_inteligente_de_documentos.` |
| **Tag** | `Test` **o** `Preprod`. Nada más. | `Test` |

**El tag es semántico, no decorativo:**

- `Test` → aplicación **sin evaluación**.
- `Preprod` → aplicación **ya evaluada** contra el Maestro y que **se registrará dentro del Maestro**.

> ⚠️ El campo *tag* se completa desde el panel web. La ruta de API `project.create` acepta `name` y `description`; si tu versión de la API no expone el tag como campo propio, **igual queda reflejado de forma obligatoria** en el nombre del servicio (§1.2) y **además** se escribe como primera línea de la descripción: `[Tag: Test]`. Verificá el spec real (§4.4) antes de asumir que el campo no existe.

### 1.2 Servicio (compose)

El servicio se llama **`App` + el tag**, con esa mayúscula y ese espacio:

| Ambiente | Nombre del servicio |
|---|---|
| Test | `App Test` |
| Preproducción | `App Preprod` |

No `app-test`, no `app_test`, no `App-Test`. Literalmente **`App Test`** y **`App Preprod`**.

Dokploy le asigna además un `appName` generado internamente (tipo `compose-algo-random-xxxx`): **guardalo**, es lo que necesitás para buscar los contenedores en §6.

### 1.3 Provider

El **Provider DEBE ser `Git`**.

En la API eso se traduce en `sourceType: "git"` + `customGitUrl` (clona por HTTPS, no necesita clave SSH). Ver §3.2 para el detalle y §3.1 para por qué los otros caminos no sirven.

### 1.4 Contenedores, redes y volúmenes

El naming interno sigue `docs/CONVENCIONES_PLATAFORMA.md` §1 y §2, sin excepción:

- Contenedores: `app-<slug>`, `db-<slug>`, `redis-<slug>`.
- Red privada del deployment: `app-<slug>-net`.
- Volúmenes: declarados con `name:` explícito, `<slug>_{pgdata,storage,...}`.

Para el ambiente de Test agregá el sufijo del ambiente al slug (`app-<slug>-test`) para que **nunca** colisione con el stack de preproducción del mismo aplicativo corriendo en el mismo host.

### 1.5 Un `docker-compose` por ambiente

**Cada ambiente tiene su propio archivo de compose, versionado en el repo.** No se reutiliza el de desarrollo para subir a Dokploy, ni se edita a mano el de Test para convertirlo en el de Preprod.

| Archivo | Ambiente | Quién lo usa |
|---|---|---|
| `docker-compose.yml` | **Desarrollo local** | El desarrollador en su máquina. **Obligatorio en la raíz** (`IN-011`): es el que evalúa el Gate 1 y el que valida `docker compose config`. |
| `docker-compose.test.yml` | **Test en Dokploy** | El desarrollador. Es el que apunta `composePath` del servicio `App Test` (§5.3). |
| `docker-compose.preprod.yml` | **Preproducción en Dokploy** | El evaluador humano. Es el que apunta `composePath` del servicio `App Preprod` (§9.1). |

> 🔴 **El `docker-compose.yml` de la raíz no se elimina ni se reemplaza.** Es un MUST del contrato (`IN-011`) y su ausencia es FAIL de Gate 1. Los archivos por ambiente **se suman**, no lo sustituyen.

**Hacelos autocontenidos, no overlays.** Dokploy recibe **un solo** `composePath`: no hay forma de pasarle `-f base -f overlay` como se hace a mano. Un archivo por ambiente, completo, evita el problema entero. Si tu versión del panel soportara varios archivos, **verificalo contra el spec real (§4.4) antes de confiar en eso** — no lo asumas.

Esa decisión además esquiva dos trampas que ya costaron un incidente de producción en este VPS:

- **Omitir un `-f` es destructivo en silencio:** recrea los contenedores perdiendo los overrides del ambiente, sin ningún error.
- **Un `-p` (nombre de proyecto) distinto crea volúmenes nuevos y vacíos.** Los volúmenes son *project-scoped*: si el nombre de proyecto no coincide, Postgres inicializa una base limpia y el esquema aparece completo por la migración de arranque — con cero datos. **Un esquema migrado no prueba que sean los datos correctos.**

Por eso cada archivo declara **explícitamente** su `name:` de nivel superior y el `name:` de cada volumen, en vez de depender del directorio o de un `-p` de invocación.

**Qué DEBE cambiar entre los tres archivos:**

- `name:` del proyecto compose y sufijo del slug (`<slug>-test` vs `<slug>`).
- Puerto publicado (§2: dev local libre, Test `3110-3199`, Preprod `3200-3299`).
- Nombres de contenedores, red y volúmenes (§1.4) — **nunca compartidos entre ambientes**.
- Límites de recursos y `restart:` policy.
- Flags de ambiente: la bandera `Secure` de la cookie apagada mientras no haya HTTPS (§6.4).

**Qué NO puede cambiar, en ninguno de los tres:**

- **Cero secretos hardcodeados.** Todos los valores sensibles vienen de `.env` / `env_file` o `${VAR}`. Un literal de `MAESTRO_API_KEY`, `*_SECRET`, `*_PASSWORD` o `SUPERADMIN` en cualquiera de estos archivos es **FAIL automático de Gate 1** (`IN-011`), y el chequeo corre sobre **todos** los compose del repo, no sólo el de la raíz.
- El puerto interno del contenedor, que **DEBE** coincidir con `requires.ports.app` del `maestro.yaml` y con el `EXPOSE` del Dockerfile. Lo que cambia por ambiente es el puerto **publicado** en el host, no el interno.
- La presencia de BD y healthcheck.

Verificá los tres antes de abrir el PR:

```bash
for f in docker-compose.yml docker-compose.test.yml docker-compose.preprod.yml; do echo "== $f"; docker compose -f "$f" config >/dev/null && echo "  parsea OK"; rg -n 'MAESTRO_API_KEY|_SECRET|_PASSWORD|SUPERADMIN' "$f" | rg -v '\$\{' && echo "  ⚠ HARDCODE" || echo "  sin hardcode"; done
```

---

## 2. Puertos — el apartado que más incidentes evita

Todas las apps comparten el host `10.100.1.124`. Un puerto mal elegido no da un error claro: pisa otra app o la deja sin arrancar.

### 2.1 Rangos por ambiente

| Ambiente | Rango | Asignación |
|---|---|---|
| **Test** | `3110` – `3199` | Secuencial, **de 10 en 10** (`3110`, `3120`, `3130`, …). |
| **Preproducción** | `3200` – `3299` | Secuencial, **de 10 en 10** (`3200`, `3210`, … `3240`, `3250`, `3260`, …). |

El puerto **no se reutiliza entre ambientes**: una app tiene un puerto de Test y otro de Preprod, y los dos stacks pueden convivir. Ese es justamente el motivo de separar los rangos — permite probar una versión nueva en Test mientras la preprod sigue sirviendo.

### 2.2 Puertos reservados — PROHIBIDO usarlos

| Puerto | Ocupado por |
|---|---|
| `80` / `443` | Traefik (redirect y TLS del portal del Maestro) |
| `3000` | **Panel de Dokploy** (y Grafana en el stack de observabilidad) |
| `3100` | Loki — **por eso el rango de Test arranca en `3110`, no en `3100`** |
| `8080` / `8081` | `maestro-api` / `maestro-portal` |
| `9090` | Prometheus |
| `5432` / `3306` / `27017` | Motores de BD — internos a la red del deployment, **no** se exponen al host |

Regla adicional de `docs/CONVENCIONES_PLATAFORMA.md` §3.2: **las apps huésped no pueden declarar puertos < 1024**, y el puerto declarado en `maestro.yaml` → `requires.ports.app` **DEBE** coincidir con el `EXPOSE` del Dockerfile.

### 2.3 Chequeo obligatorio antes de reservar un puerto

No hay tabla de asignaciones que mantener: **se verifica contra la realidad**, que es la única fuente que no se desactualiza. Antes de escribir el puerto en el compose:

```bash
curl -s -o /dev/null -m 5 -w "%{http_code}\n" http://10.100.1.124:3160/
```

Si contesta **cualquier cosa distinta de `000`**, el puerto ya está ocupado: probá el siguiente.

Para recorrer el rango entero y quedarte con el primero libre:

```bash
for p in $(seq 3110 10 3199); do c=$(curl -s -o /dev/null -m 3 -w "%{http_code}" "http://10.100.1.124:$p/"); echo "$p -> $([ "$c" = "000" ] && echo LIBRE || echo "OCUPADO ($c)")"; done
```

La BD y el resto de servicios internos quedan **sin** exponer al host: se alcanzan por DNS interno de Docker dentro de `app-<slug>-net`.

---

## 3. Cómo llega el código al servidor

Esta es **la** decisión del despliegue, y la que más tiempo hace perder. Está probada contra esta instancia.

### 3.1 Lo que NO funciona

| Camino | Por qué no |
|---|---|
| `compose.import` | Importa **plantillas de Dokploy en JSON**, no código fuente. Mandarle un zip da `Unexpected token 'P', "PK..." is not valid JSON`. |
| Subir la imagen a un registry | `registry.*` suele dar SIN PERMISO con las cuentas del equipo. |
| Deploy key SSH | `sshKey.*` suele dar SIN PERMISO — incluido `sshKey.generate`. |
| `sourceType: raw` con `build:` | Dokploy escribe el compose pero **no tiene el código**, así que el build falla. `raw` sólo sirve si todas las imágenes se bajan de un registry público. |

### 3.2 Lo que SÍ funciona — Provider `Git`

**`sourceType: git` con `customGitUrl`**, que clona por HTTPS y **no necesita clave SSH**. Probado con una cuenta sin permisos de registry ni de SSH.

Si el repo es público alcanza la URL. Si es privado hace falta un token dentro de la URL:

```
https://x-access-token:<TOKEN>@github.com/<org>/<repo>.git
```

### 3.3 Pedir el token al usuario

Probá en este orden y quedate con el primero que se pueda:

1. **Token fine-grained de GitHub** (lo mejor: un repo, sólo lectura).
   `https://github.com/settings/personal-access-tokens/new` → Resource owner = **la organización**, Repository access = *Only select repositories*, Permissions → Contents = **Read-only**, Expiration = 7 días.

   **Si la organización no aparece en "Resource owner", esta opción no existe** para esa cuenta: la organización no habilitó los tokens fine-grained. No insistas, pasá al 2 y mencionale que un owner lo habilita con un solo setting y la próxima vez sale limpio.

2. **Token clásico** — `https://github.com/settings/tokens` → pestaña **"Tokens (classic)"** → *Generate new token (classic)*. Scope: **sólo `repo`**. Expiration: 7 días.

   La pantalla correcta tiene **Note**, **Expiration** y casilleros bajo *"Select scopes"*. Si ve "Resource owner" y "Repository access", está en la de fine-grained.

   **Decí el costo con todas las letras:** un token clásico con `repo` alcanza **todos** los repos que esa persona puede ver, no sólo el del despliegue. No existe scope de sólo lectura para repos privados en tokens clásicos. Lo que lo acota es el vencimiento corto y revocarlo al terminar.

3. **Conectar GitHub desde Dokploy** (`Settings → Git Providers`). Es lo más prolijo —no queda ningún token en la config— pero **no se puede hacer por API**: es un flujo de GitHub App en el navegador y hace falta ser owner de la organización.

Que lo guarde en un archivo (por ejemplo `D:\secrets\github.token`), nunca en el chat.

**Probá el token antes de usarlo**, así separás "el token está mal" de "el despliegue está mal":

```bash
git ls-remote --heads "https://x-access-token:$TOK@github.com/<org>/<repo>.git" master
```

> 🔴 **El token viaja adentro de `customGitUrl`.** Cualquier volcado del compose lo muestra entero. Pasá por un enmascarado todo lo que imprimas de ese objeto.

---

## 4. Acceso a la API de Dokploy

**Los despliegues se hacen por API, no a mano por el panel.** El panel se usa para mirar y para completar el tag; lo que se hace por API queda reproducible, auditable y repetible, y lo que se hace a mano no.

### 4.1 Verificá que llegás a la instancia

```bash
curl -s -m 15 -o /dev/null -w "%{http_code}\n" http://10.100.1.124:3000/api/health
```

- `200` → seguí.
- `000` → **no es la API, es la red.** Es una IP privada: casi siempre significa que se cayó la VPN. Comprobalo con `ping 10.100.1.124` y contra una URL pública (si internet anda y la 10.x no, es la VPN). Decíselo al usuario y esperá; no intentes diagnosticar la API.

### 4.2 API key

Sin key, **toda** la API devuelve 401. Pedísela al usuario con este texto:

> Necesito una API key de Dokploy. Entrá a `http://10.100.1.124:3000/dashboard/settings/profile` y bajá hasta **"API/CLI Keys"** → *Generate API Key*.
>
> | Campo | Valor |
> |---|---|
> | Name | algo que identifique para qué es (máx. 32 caracteres) |
> | Prefix | vacío |
> | Expiration | **30 days** (no uses "Never") |
> | Enable Rate Limiting | **apagado** — prendido te puede frenar a mitad del despliegue |
>
> Dokploy la muestra **una sola vez**. Guardala en un archivo y pasame la ruta. **No la pegues en el chat:** quedaría en el historial para siempre y es una credencial.

Detalles que ahorran vueltas:

- El menú lateral **no tiene** entrada "API". Está adentro de *Profile*.
- Si el usuario ve pocas opciones en el menú lateral (3 de 22), su cuenta es **miembro** y no dueño de la organización. Eso importa: ver §4.3.
- `http://10.100.1.124:3000/swagger` **redirige a la raíz** si no hay sesión de navegador. No es que esté mal la URL.

**Cómo usar la key:** header `x-api-key`. **No** `Authorization: Bearer` (da 401).

```bash
K=$(cat /d/secrets/dokploy.key | tr -d '\r\n')
curl -s -H "x-api-key: $K" http://10.100.1.124:3000/api/project.all
```

El `tr -d '\r\n'` es necesario en Windows: sin él, el CRLF del archivo entra en el header y la API rechaza la key.

> 🔴 **Nunca imprimas la key.** Ni en un eco, ni en un error, ni en un log.

### 4.3 Mapeá tus permisos ANTES de planificar

Las cuentas suelen ser **miembro**, no admin, y eso descarta caminos enteros. Averigualo en 20 segundos en vez de descubrirlo a mitad del despliegue:

```bash
for p in registry.all sshKey.all server.all destination.all gitProvider.getAll project.all; do r=$(curl -s -m 15 -H "x-api-key: $K" "http://10.100.1.124:3000/api/$p"); echo "$p -> $(echo "$r" | grep -q UNAUTHORIZED && echo 'SIN PERMISO' || echo OK)"; done
```

Lo habitual: **`registry`, `sshKey`, `server` y `destination` dan SIN PERMISO**; proyectos, composes y git providers funcionan.

Un recurso que no aparece en el listado igual puede estar bloqueado en su creación: **comprobá el que vas a usar, no uno parecido.** Que `sshKey.all` falle no demuestra que `sshKey.create` falle — probalo antes de prometerle un camino al usuario.

### 4.4 El spec completo de la API

604 rutas. Bajalo y consultalo en vez de adivinar nombres de campos:

```bash
curl -s -H "x-api-key: $K" "http://10.100.1.124:3000/api/trpc/settings.getOpenApiDocument" -o api.json
```

Viene envuelto: el spec real está en `.result.data.json`. Las rutas son `/api/<router>.<procedimiento>`, GET o POST según la operación.

---

## 5. Despliegue paso a paso (API)

```
ensayo local → project.create → compose.create → compose.update (env + git) → compose.deploy → verificación
```

### 5.0 Ensayá en local ANTES de tocar Dokploy

**No te saltees esto.** Un error de configuración adentro de Dokploy cuesta muchísimo más de diagnosticar que el mismo error en tu máquina.

Ensayá **con el mismo archivo que va a correr en Dokploy** (§1.5), no con el de desarrollo: si probás `docker-compose.yml` y desplegás `docker-compose.test.yml`, el ensayo no prueba nada de lo que vas a subir.

```bash
docker build -t <app>:test .
docker compose -f docker-compose.test.yml --env-file <tu.env> up -d
curl -s http://localhost:<puerto>/health
docker compose -f docker-compose.test.yml down -v
```

No hace falta `-p`: el archivo por ambiente ya declara su `name:` de nivel superior (§1.5). Si tuvieras que pasar un `-p`, es señal de que al compose le falta ese `name:`.

Cuatro trampas que aparecieron haciendo exactamente esto:

1. **Los secretos tienen formato.** Una app puede exigir base64 **estándar** y rechazar el *url-safe* de `secrets.token_urlsafe()` (usa `-` y `_`, que `b64decode(validate=True)` rechaza). El contenedor muere en la migración. Generá con `base64.b64encode(os.urandom(32))` cuando el ejemplo diga `openssl rand -base64 32`, y leé qué valida la app.

2. **`--env-file` no alimenta el bloque `env_file:` del compose.** Si el `docker-compose.yml` tiene `env_file: - .env`, esa lista se lee del `.env` que está **al lado del compose**, no del que pasás por línea de comandos. `--env-file` sólo alimenta la interpolación de `${VARS}`. Es silencioso: la app arranca con otros valores y vos creés que usó los tuyos. Comprobalo comparando un valor adentro del contenedor contra tu archivo.

3. **Postgres fija la contraseña al inicializar el volumen.** Si regenerás los secretos y volvés a levantar, el contenedor viejo sigue con la contraseña vieja y da `password authentication failed`. Hay que hacer `down -v`.

4. **Puerto ocupado.** Ver §2.3. Verificalo **antes**, no después del deploy.

### 5.1 Proyecto

```json
POST /api/project.create
{
  "name": "<Título funcional de la app>",
  "description": "[Tag: Test] <qué hace, tool/número, owner>"
}
```

Devuelve `{project, environment}`. **Guardate `environment.environmentId`**: lo necesita el paso siguiente y no es obvio de dónde sale después.

Es idempotente a mano: si ya existe, listá con `project.all` y sacá el `environmentId` de `project.one?projectId=...` → `environments[0]`.

Completá el **tag** (`Test` / `Preprod`) desde el panel.

### 5.2 Compose (servicio)

```json
POST /api/compose.create
{
  "name": "App Test",
  "environmentId": "<del paso anterior>",
  "composeType": "docker-compose",
  "sourceType": "raw",
  "composeFile": "<contenido de docker-compose.test.yml>"
}
```

Recordá: el `name` es **`App Test`** o **`App Preprod`** (§1.2), y el contenido es el del compose **del ambiente que estás desplegando** (§1.5) — no el de la raíz, que es el de desarrollo local. Devuelve `composeId` y un `appName` generado — anotá los dos.

### 5.3 Variables y origen del código — Provider `Git`

```json
POST /api/compose.update
{
  "composeId": "<...>",
  "sourceType": "git",
  "customGitUrl": "https://x-access-token:<TOKEN>@github.com/<org>/<repo>.git",
  "customGitBranch": "master",
  "composePath": "./docker-compose.test.yml",
  "composeType": "docker-compose",
  "env": "CLAVE=valor\nOTRA=valor\n...",
  "createEnvFile": true
}
```

> 🔴 **`composePath` apunta al compose del ambiente** (§1.5): `./docker-compose.test.yml` para `App Test`, `./docker-compose.preprod.yml` para `App Preprod`. Dejarlo en `./docker-compose.yml` despliega el compose de **desarrollo local** — con su puerto, sus nombres de contenedor y sus flags — y el síntoma aparece como una colisión de puerto o de nombre, no como un error de configuración.

> 🔴 **`createEnvFile: true` es obligatorio si el compose tiene `env_file: - .env`.** Es lo que hace que Dokploy escriba ese archivo al lado del compose. Sin esto las variables no llegan al contenedor, la app arranca con los defaults y el síntoma aparece mucho después y en otro lado.

Variables que **no** podés olvidar en un ambiente HTTP sin TLS (ver §6.4): la que apaga la bandera `Secure` de la cookie de sesión, y un nombre de cookie único por app.

### 5.4 Desplegar

```json
POST /api/compose.deploy
{"composeId": "<...>", "title": "<descripción del despliegue>"}
```

Responde enseguida; el trabajo sigue en el servidor. Consultá el estado con `compose.one?composeId=...` → `composeStatus`: `idle` → `running` → `done`/`error`.

---

## 6. `done` no significa que funcione

**Este es el punto más importante del manual.** Un despliegue que dice que salió bien y no levantó nada es peor que uno que falla: nadie lo vuelve a mirar. Verificá las cuatro cosas, con evidencia.

### 6.1 Los contenedores están corriendo

```bash
curl -s -H "x-api-key: $K" "http://10.100.1.124:3000/api/docker.getContainersByAppNameMatch?appName=<appName>"
```

Tiene que decir `running` y, si el compose declara healthcheck, `(healthy)`.

### 6.2 Clonó el commit que esperabas

`deployment.allByCompose?composeId=...` pone como título el último commit del repo clonado. Si no es el tuyo, clonó otra cosa.

### 6.3 Los logs de la app

Acá se ven la versión real, los seeders y los errores:

```bash
curl -s -H "x-api-key: $K" "http://10.100.1.124:3000/api/compose.readLogs?composeId=<id>&containerId=<nombre>&tail=60"
```

(`deployment.readLogs` pide `deploymentId`, no el `logPath` que trae el listado.)

### 6.4 La app responde y se puede entrar de verdad

`/health` en 200 **no alcanza**: probá el login completo **en un navegador real**, no con `curl`. Dos bugs conocidos de plataforma que `curl` no detecta:

1. **Cookie con bandera `Secure` sobre HTTP.** Si la app pone la cookie de sesión con `Secure` y el ambiente es HTTP, **el navegador la descarta y el login entra en un bucle silencioso** — no da error, simplemente vuelve al login. Buscá la variable que apaga esa bandera (`COOKIES_SEGURAS` / `SECURE_COOKIES` / `SESSION_COOKIE_FORCE_INSECURE`) y ponela en **off** mientras no haya HTTPS. Verificá que llegó: pedí la cookie y mirá si trae `Secure`. Que esté escrita en tus variables **no prueba** que llegó al contenedor (ver trampa 2 de §5.0).

2. **Colisión del nombre de la cookie de sesión.** Las cookies del navegador se indexan por **(host, path)**, **no** por puerto ni esquema. Una app servida en el mismo host que el portal del Maestro (`10.100.1.124:31xx` vs `10.100.1.124`) que use el mismo nombre de cookie (`maestro_session` es el default de Laravel y es muy fácil de copiar) **pisa la sesión del Maestro y viceversa**. Cada app DEBE usar un nombre único en toda la plataforma: `<slug>_session`. Chequealo **antes** de desplegar.

Un `403` después de un login exitoso no siempre es un error: puede ser la app obligando a cambiar la contraseña inicial. Leé el cuerpo de la respuesta antes de salir a diagnosticar.

---

## 7. Lo que hace el DESARROLLADOR: PR y auto-evaluación hasta Gate 1 PASS

> **Dueño de esta sección: el desarrollador.** Termina cuando el Gate 1 da **PASS** sobre su propio PR. Ahí entrega y se detiene: **no** corre el Gate 2, **no** mergea y **no** despliega a `Preprod`. Eso es §8 y §9, del evaluador humano.

La fuente de verdad es `EvaluacionAppHuesped/SPEC.md`; estos son los pasos operativos.

### Paso 1 — Pre-flight en el fork (SPEC §6.1)

Antes de abrir nada, el PM agéntico del fork verifica **los cinco** puntos. Si uno falla, no hay autorización para abrir el PR:

1. `maestro-cli validate` local → **PASS**.
2. Validadores transversales del framework v4 (`framework-agentico/validation/`) → **PASS**.
3. `projects/{id}/PROJECT.md` declara `criticality` y **coincide** con `maestro.yaml.metadata.criticality`.
4. Artefactos obligatorios presentes en el **último commit**:
   - `maestro.yaml`
   - `Dockerfile` (con `EXPOSE` coincidente con `requires.ports.app`)
   - **`.env.example` en la raíz** (`SE-009`) — enumera TODAS las vars con placeholders seguros; el `.env` real **nunca** commiteado
   - **`docker-compose.yml` en la raíz** (`IN-011`) — parsea, toma variables desde `.env`/`env_file`, **sin secretos hardcodeados**, con BD + healthcheck + `ports` coherentes
   - **`docker-compose.test.yml` y `docker-compose.preprod.yml`** (§1.5) — los tres parsean y los tres pasan el grep anti-hardcode
   - `CHANGELOG.md` mencionando la nueva versión
   - `slo.yaml`, `observability.yaml` y bloque `data_policy` **según el tier**
5. Emulación local completa del Gate 1 (Paso 3) sobre la propia máquina.

### Paso 2 — Abrir el PR

- **Origen:** `master` del fork. **Destino:** rama `tools/{app-name}` del repo principal.
  Si la rama no existe, se le solicita al PM del repo principal — **nunca** se crea desde el fork.
- **Título:** `[{tier}] {app-name} {version}: {resumen}`
  Ej.: `[standard] inventario 1.5.0: agrega módulo de transferencias`
- **Template:** `.github/PULL_REQUEST_TEMPLATE/tools-app-name.md`, declarando tier (+ADR si cambió), cambios funcionales, tipo de bump y justificación, confirmación del pre-flight, riesgos y mitigaciones, y coordinación de rolling upgrade.

### Paso 3 — Gate 1, REPO-TIME: auto-evaluación hasta PASS (emulación local, **sin** GitHub Actions)

**El desarrollador evalúa su propio PR** con `/evaluar-app-huesped <PR>` y **itera hasta obtener PASS**: corrige lo que sale en FAIL, empuja, vuelve a evaluar. No se entrega un PR con Gate 1 en FAIL esperando que lo arregle el evaluador humano — el reporte ya trae la remediación de mínima modificación, así que el camino está escrito.

El comando checkoutea el head del PR **en un worktree aislado** (nunca la copia de trabajo principal) y corre todo con docker:

| # | Check | Criterio | Req |
|---|---|---|---|
| 1 | Validación de schemas | `maestro.yaml`, `slo.yaml`, `observability.yaml`, `data_policy`, manifest contra los schemas v2 | — |
| 2 | Build de imagen | `docker build`; **FAIL si > 500 MB**, WARN > 350 MB | `IN-004` |
| 3 | Trivy | CRITICAL/HIGH → **FAIL** | `IN-006`/`CI-003` |
| 4 | Gitleaks | Historial **completo** + diff del PR → FAIL si matchea | `SE-001`/`CI-004` |
| 5 | Análisis estático | Lecturas de `X-Auth-*`; `company_id` en migraciones/queries; comparaciones inseguras de strings sensibles; `rejectUnauthorized: false`; secretos hardcodeados en **cualquiera** de los compose de §1.5 → **FAIL** | varios / `IN-011` |
| 6 | Auditoría de tier | Cross-check del tier declarado contra el código (SPEC §3.4) → FAIL si inconsistente sin ADR | — |
| 7 | Validadores transversales | `security-auditor`, `qa-tester`, `performance-analyst`, `compliance-analyst`, `code-reviewer` | — |

Recetas de referencia:

```bash
# Compose válido y sin hardcode (IN-011) — los TRES archivos de §1.5
for f in docker-compose.yml docker-compose.test.yml docker-compose.preprod.yml; do docker compose -f "$f" config >/dev/null; rg -n 'MAESTRO_API_KEY|_SECRET|_PASSWORD|SUPERADMIN' "$f" | rg -v '\$\{'; done
```

```bash
# Tamaño de imagen (IN-004)
docker build -t eval/app:sha .
docker image inspect eval/app:sha --format '{{.Size}}'
```

```bash
# Trivy (IN-006 / CI-003)
docker run --rm -v /var/run/docker.sock:/var/run/docker.sock aquasec/trivy:latest image --severity CRITICAL,HIGH --exit-code 1 eval/app:sha
```

```bash
# Gitleaks (SE-001 / CI-004)
docker run --rm -v "$PWD:/repo" zricethezav/gitleaks:latest detect --source=/repo --redact --log-opts=--all --exit-code 1
```

```bash
# Tests del fork, sin instalar toolchain
docker compose run --rm app <comando-de-tests-del-fork>
```

**Agregación:** cualquier MUST en FAIL → Gate 1 **FAIL** → PR bloqueado. SHOULD en FAIL sin ADR → escala a FAIL, **excepto** los marcados como no bloqueantes por decisión operativa (hoy `CI-001`, branch protection, que queda en WARN). Todo MUST PASS y SHOULD resuelto → **PASS**.

> **GitHub Actions no es fuente de verdad.** Un run rojo, incompleto o ausente (p. ej. por agotamiento de minutos) **no genera FAIL**. Si un check no se puede correr localmente por falta de tooling irreductible, se marca **sólo ese ítem** como `NEEDS_REVIEW` documentando qué falta.

**Salida:** reporte JSON (SPEC §7.1) + Markdown (§7.2) publicado como **comentario sticky** en el PR, con la sección obligatoria de **Sugerencias de mejora** (§7.3) cuando el veredicto no es PASS limpio: remediación de **mínima modificación**, priorizada P0/P1/P2, con esfuerzo estimado y la línea final *"Camino más corto a PASS"*.

### Paso 4 — Entregar y detenerse

Con el Gate 1 en **PASS**, el desarrollador:

1. Deja el comentario sticky con el PASS visible en el PR.
2. Avisa al evaluador humano que el PR está listo para revisión, indicando el head SHA evaluado, el tier declarado y la URL del `Test` donde la app está corriendo.
3. **Se detiene ahí.**

Lo que el desarrollador **NO** hace, ni aunque el Gate 1 esté en PASS:

- ❌ Correr el Gate 2 (consume recursos del VPS y se autoriza en §8).
- ❌ Mergear el PR a `tools/{app-name}`.
- ❌ Crear el proyecto `Preprod` en Dokploy ni desplegar nada ahí.
- ❌ Registrar la app en el catálogo del Maestro.

Un Gate 1 en PASS **habilita la revisión, no la promoción.**

---

## 8. Lo que hace el EVALUADOR HUMANO: re-evaluación y merge

> **Dueño de esta sección: el evaluador humano.** El PASS del desarrollador es condición **necesaria, no suficiente**.

### 8.1 Re-evaluación independiente

**El PASS del desarrollador no se da por bueno.** El evaluador humano vuelve a evaluar el PR **desde cero**, aunque el comentario sticky diga PASS. El motivo es simple: quien evalúa su propio trabajo optimiza, sin querer, para que el check pase — no para que la app esté bien.

1. Re-corre el Gate 1 (§7 Paso 3) sobre el head del PR, en su propio entorno.
2. Compara su resultado contra el sticky del desarrollador. **Cualquier divergencia se investiga antes de seguir**: o el desarrollador evaluó otro SHA, o su entorno se salteó un check, o un check es no determinístico. Las tres cosas importan.
3. Revisa a mano lo que ningún check cubre: coherencia del tier declarado contra lo que hace la app de verdad, decisiones de arquitectura, calidad del `CHANGELOG`, riesgos declarados en el PR.
4. Resuelve los ítems `NEEDS_REVIEW` — los que el agente **no puede** decidir solo.
5. Decide los waivers: **sólo el admin humano del Maestro puede autorizar el waiver de un MUST**, y queda registrado como `application.merge.forced`. Un agente **nunca** lo autoriza, y un desarrollador tampoco se lo auto-otorga.

### 8.2 Gate 2, RUNTIME smoke

Lo lanza el evaluador humano, sólo si el Gate 1 quedó en PASS (o el `NEEDS_REVIEW` está resuelto). **Consume recursos del VPS.**

1. **Provisioning efímero** contra la empresa demo `evaluation`, con credenciales generadas para el test (`MAESTRO_API_KEY`, `MAESTRO_WEBHOOK_SECRET`, `SUPERADMIN_INITIAL_PASSWORD`).
2. **Contract test suite:**
   - **Health:** 100 polls; ≥ 99 % responden 200 en ≤ 5 s.
   - **Branding:** sin api key → 401; api key inválida → 401; válida → 200 + schema correcto; latencia p95 dentro del umbral del tier.
   - **Login:** credenciales válidas → 200; inválidas → 401; 5 intentos seguidos → 429 (si el SHOULD aplica).
   - **Endpoints protegidos:** sin token → 401; con token → 200; tras logout → 401.
   - **Hooks** (si declarados): firma válida → 2xx; inválida → 401; replay > 300 s → 401; `event_id` duplicado → idempotente.
   - **Manifest** (si declarado): schema válido, autoconsistente y coincidente con la realidad.
   - **Metrics** (si declarado): parsea, métricas estándar presentes.
   - **Seeding:** primer arranque crea el superadmin; re-ejecución idempotente; password débil → el seed falla.
3. **Análisis de logs** durante los tests: **cero** passwords, api keys o secretos en stdout/stderr.
4. **Análisis de recursos:** el contenedor no excede `resources.memory` / `resources.cpu` declarados.
5. **Teardown:** smoke deployment destruido y BD efímera purgada.

Cualquier MUST en FAIL → Gate 2 FAIL → PR bloqueado y devuelto al desarrollador. Si **no hay runner disponible**, se marca `NEEDS_RUNTIME_RUNNER` y el evaluador decide si suple esos contract tests a mano contra el `Test` del desarrollador o si bloquea.

### 8.3 Merge

Con la re-evaluación y el Gate 2 en PASS, el evaluador humano mergea a `tools/{app-name}`:

```
feat(tools/{app-name}): release {version} [{tier}]
```

Si algo quedó en FAIL, el PR vuelve al desarrollador con los bloqueos y sus sugerencias de mínima modificación, y se reinicia en §7 Paso 3. La app se queda en `Test` hasta entonces.

---

## 9. Desplegar a `Preprod`, registrar en el Maestro y entregar

> **Dueño de esta sección: el evaluador humano.** El desarrollador **no** ejecuta ningún paso de §9. Su participación vuelve en §9.4, cuando recibe el proyecto ya desplegado y verificado.

### 9.1 Despliegue y verificación

Mecánicamente idéntico a §5, con estas diferencias:

- Tag del proyecto: **`Preprod`**.
- Nombre del servicio: **`App Preprod`**.
- `composePath`: **`./docker-compose.preprod.yml`** (§1.5). No el de Test, no el de la raíz.
- Puerto del rango **`3200`–`3299`** (§2), verificado libre con §2.3.
- `customGitBranch` apunta al **commit/tag evaluado y mergeado**, no a una rama móvil.
- Secretos **generados nuevos** para `Preprod`: no se reutilizan los del `Test` del desarrollador (§10).
- Verificación de §6 completa, **incluido el login en navegador real**. Este es el punto que decide si hay entrega o no: mientras el `Preprod` no esté verificado y funcional, no se entrega nada.

### 9.2 Registro en el catálogo del Maestro

Una app en `Preprod` **se registra dentro del Maestro**. Eso son dos filas y un permiso:

1. **`applications`** — con el `slug` real de la app. Verificá el slug contra el repo; **no lo adivines** (hay slugs parecidos que son apps distintas).
2. **`deployments`** — un deployment por empresa. Sólo aparece en "Mis Apps" y se puede lanzar cuando `status` es `healthy` o `degraded`. `provisioning` **no** se auto-promueve: el job de health-check sólo levanta filas que ya están en `starting`/`healthy`/`degraded`.
3. **`user_application_access`** — sin esta fila (o sin el permiso RBAC `my_apps.view_all`) el usuario no ve la app aunque el deployment esté sano. La tabla tiene columna `role` (`member` | `leader`).

### 9.3 Si la app integra SSO del Maestro

Contrato real del emisor (`SsoTokenService` + `SsoHandoffController`):

- `iss` es literalmente `"maestro"`.
- `aud` es el `applications.slug` de la app.
- TTL del token: **60 segundos**.
- `deployments.sso_secret` se genera con `SsoTokenService::generateSecret()` y se guarda **cifrado** AES-256-GCM (`iv:ciphertext:tag`, partes en base64) con `MAESTRO_ENCRYPTION_KEY`. **No fabriques un valor en un formato inventado.**
- `returnUrl` / `siteName` **no son un auto-redirect**: son para un botón "Volver a {siteName}" **dentro** de la app. Tratarlos como destino post-login expulsa al usuario y nunca puede entrar.

> `php artisan tinker` **no está instalado** en la imagen de producción del Maestro. Para correr código Eloquent puntual, escribí un script standalone que bootea Laravel a mano y usá rutas absolutas `/app/...` (`__DIR__` resuelve a donde está el archivo, no a la raíz de la app).

### 9.4 Entrega del proyecto al desarrollador

**Este es el punto de traspaso.** Una vez que el `Preprod` está desplegado, registrado en el Maestro y **verificado como funcional** (§9.1), el evaluador humano le entrega el proyecto al desarrollador, que opera desde ahí en adelante.

**Qué se entrega:**

| Qué | Detalle |
|---|---|
| **URL y ambiente** | `http://10.100.1.124:<puerto>` + tag `Preprod`. |
| **Identificadores de Dokploy** | `projectId`, `environmentId`, `composeId` y el `appName` generado. Sin esto el desarrollador no puede redesplegar ni leer logs por API. |
| **Acceso al proyecto en Dokploy** | Permiso sobre el proyecto `Preprod` en el panel. |
| **Credenciales iniciales** | Usuario y contraseña del superadmin **en un archivo**, nunca en el chat (§10). Que las cambie y después borre el archivo. |
| **Registro en el Maestro** | `applications.slug`, `deployments.id` y el estado (`healthy`/`degraded`) con el que quedó. |
| **Evidencia de la verificación** | Qué se verificó y cómo: contenedores corriendo, commit clonado, versión de los logs, login probado en navegador. |
| **Commit/tag desplegado** | El SHA exacto que está corriendo, para que el desarrollador sepa desde dónde sigue. |

**Qué cambia después de la entrega:**

- El desarrollador pasa a ser el dueño operativo del `Preprod`: redespliegues, logs, diagnóstico.
- **Cada versión nueva vuelve a empezar el ciclo completo**: §7 (PR + Gate 1 PASS) → §8 (re-evaluación del evaluador humano) → §9. La entrega **no** es un permiso permanente para subir lo que quiera: es la entrega de *esta* versión ya evaluada.
- El evaluador humano sigue siendo quien decide qué llega a `Preprod`.

---

## 10. Higiene de credenciales

- Las credenciales se leen de **un archivo**, nunca del chat.
- **No las imprimas**: ni en un eco, ni en un mensaje de error, ni en un log, ni en un volcado de un objeto de la API. El token de git vive **dentro** de `customGitUrl`, así que es facilísimo filtrarlo sin querer.
- Los secretos de la app **generalos nuevos** para cada ambiente. No reutilices los de producción: un ambiente de test se tira y se rehace, y una clave maestra de producción no puede vivir ahí.
- Pedí siempre **vencimiento corto** y avisá cuándo se puede revocar.
- Nunca filtres la salida de `env` por **nombre** de variable (`grep -v "secret|password"` no ve un secreto embebido en un `DATABASE_URL`). Imprimí sólo nombres: `cut -d'=' -f1`.

---

## 11. Cierre de un despliegue de `Test`

Qué entregar al cerrar un `Test` (la entrega del `Preprod` es distinta y está en §9.4):

- **La URL** (`http://10.100.1.124:<puerto>`) y el ambiente (`Test`).
- **Usuario y contraseña inicial en un archivo**, no en el chat. Avisale que la cambie y después borre el archivo.
- **Qué verificaste, con evidencia:** contenedores corriendo, commit clonado, versión que reportan los logs, login probado **en navegador**.
- **Que revoque el token de GitHub.** La app sigue corriendo; sólo se pierde la capacidad de redesplegar hasta generar otro. Si fue un token clásico, insistí: alcanza **todos** sus repos.
- **Que no suba datos reales** mientras el ambiente sea HTTP.
- **Qué hay que cambiar el día que haya HTTPS** (volver a prender la cookie `Secure`).

---

## 12. Checklist de una pantalla

### DESARROLLADOR

**Antes de tocar Dokploy**

1. `curl /api/health` → si da `000`, es la VPN, no la API.
2. API key de Dokploy (Settings → **Profile** → API/CLI Keys). Header `x-api-key`.
3. Mapeá permisos: `registry`, `sshKey`, `server` suelen estar bloqueados.
4. **Puerto libre** del rango de **Test: `3110-3199`**, de 10 en 10. Nunca `3000`, `3100`, `8080`, `8081`, `9090`, `80`, `443`.
5. **`docker-compose.test.yml`** propio del ambiente (§1.5), autocontenido, con `name:` explícito de proyecto y de volúmenes, sin tocar el `docker-compose.yml` de la raíz.
6. **Ensayo local con ese mismo archivo:** formato de los secretos, `env_file`, volumen de Postgres, puerto.

**Alta del `Test` en Dokploy**

7. Proyecto: **título + descripción + tag `Test`**.
8. Servicio: **`App Test`**. Provider **`Git`**.
9. `project.create` → `compose.create` → `compose.update` (**`composePath: ./docker-compose.test.yml`**, **`createEnvFile: true`**, `sourceType: git`, `customGitUrl`) → `compose.deploy`.
10. **`done` no prueba nada.** Contenedores `running`/`healthy`, commit clonado correcto, logs, y **login en navegador real** (cookie `Secure` off + nombre de cookie único).

**Camino a Preprod — hasta acá llega el desarrollador**

11. Pre-flight del fork (5 puntos), con **los tres compose** parseando y sin hardcode → PR `master del fork → tools/{app-name}`.
12. `/evaluar-app-huesped <PR>` sobre su **propio** PR, **iterando hasta PASS**.
13. Avisar al evaluador humano: head SHA evaluado, tier, URL del `Test`. **Y detenerse.** Sin Gate 2, sin merge, sin `Preprod`.

### EVALUADOR HUMANO

14. **Re-evaluar el Gate 1 desde cero**, aunque el sticky diga PASS. Investigar cualquier divergencia.
15. Revisar a mano lo que ningún check cubre: tier real vs. declarado, arquitectura, riesgos. Resolver `NEEDS_REVIEW`. Decidir waivers (sólo él puede).
16. **Gate 2** smoke contra el tenant `evaluation` + teardown.
17. **Merge** a `tools/{app-name}`.
18. **Desplegar el `Preprod`**: tag `Preprod`, servicio **`App Preprod`**, **`composePath: ./docker-compose.preprod.yml`**, puerto **`3200-3299`**, `customGitBranch` al commit mergeado, **secretos nuevos**. Verificación de §6 completa.
19. **Registrar en el Maestro:** `applications`, `deployments` en `healthy`, `user_application_access`.
20. **Entregar el proyecto al desarrollador** (§9.4): URL, IDs de Dokploy, acceso al panel, credenciales en archivo, registro en el Maestro, evidencia y SHA desplegado.

### SIEMPRE

21. Credenciales en archivo, nunca en el chat. Vencimiento corto. Revocar al terminar.
22. Cada versión nueva **reinicia el ciclo** en el punto 11. La entrega no es un permiso permanente.

---

## Referencias

| Documento | Qué aporta |
|---|---|
| `EvaluacionAppHuesped/SPEC.md` | Proceso de evaluación, tiers, dimensiones, requisitos MUST/SHOULD, gates, waivers, formato del reporte. **Fuente de verdad de §7.** |
| `PremisaWebMaestro/01-PREMISAS-Y-NO-NEGOCIABLES.md` | Axiomas y no-negociables. Toda violación es FAIL bloqueante sin waiver posible. |
| `docs/APP_HUESPED_SPEC.md` | Contrato de la app huésped: `maestro.yaml`, endpoints, Dockerfile, puertos. |
| `docs/CONVENCIONES_PLATAFORMA.md` | Naming de contenedores/redes/volúmenes, puertos, variables de entorno reservadas. |
| `docs/APP_HUESPED_BEST_PRACTICES.md` | Prácticas recomendadas de implementación. |
| `framework-agentico/core/RULES.md` | Reglas del framework, incluido `git_workflow` y permisos de merge. |
| `.claude/commands/evaluar-app-huesped.md` | Comando `/evaluar-app-huesped` que ejecuta los gates. |

> **Nota de disponibilidad.** `EvaluacionAppHuesped/` y el comando `/evaluar-app-huesped` viven hoy en la rama `maestros/web-maestro-para-aplicacones-genericas` y aterrizan en `master` cuando esa rama se mergee. Hasta entonces, los pasos de §7 son igualmente vinculantes y se ejecutan desde esa rama.

---

## Historial de revisiones

| Versión | Fecha | Cambios |
|---|---|---|
| 1.0.0 | 2026-09-22 | Versión inicial. Consolida los descubrimientos del despliegue de test sobre la instancia Dokploy `10.100.1.124:3000`, define la convención de nombres/tags, fija los rangos de puertos por ambiente (`Test` 3110–3199 / `Preprod` 3200–3299), exige un `docker-compose` autocontenido por ambiente (`docker-compose.yml` desarrollo / `.test.yml` / `.preprod.yml`, §1.5) y establece el reparto de responsabilidades entre desarrollador y evaluador humano (§0.1): el desarrollador despliega su `Test`, abre el PR y auto-evalúa hasta Gate 1 PASS; el evaluador humano re-evalúa de forma independiente, corre el Gate 2, mergea, **despliega el `Preprod`** y recién entonces entrega el proyecto al desarrollador. |
