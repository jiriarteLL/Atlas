# Premisas Fundamentales y Requisitos No Negociables

> **Versión:** v4 (framework agéntico v4 / contrato `maestro.platform/v2`)
> **Última revisión:** 2026-05-07
> **Estado:** vigente
> **Reemplaza a:** `legacy/v3/PremisaWebMaestro/01-PREMISAS-Y-NO-NEGOCIABLES.md` (modelo v1 / IdP centralizado).

---

## Propósito de este documento

Este documento es la constitución de la Web Maestro (= Web Anfitriona = plataforma Maestro). Todo lo que aquí se establece tiene fuerza vinculante sobre cualquier decisión técnica, de diseño o de implementación. Un agente de IA que reciba este documento debe internalizarlo como su marco de referencia primario antes de generar cualquier código, arquitectura o recomendación.

Las **premisas** son los axiomas: principios verdaderos sobre los cuales se construyen todas las decisiones. Los **no negociables** son los límites duros: restricciones absolutas que jamás pueden violarse bajo ninguna circunstancia, presión de negocio, limitación de tiempo o excepción técnica.

---

## Contexto: cambio de modelo respecto a v3

En v3 la Web Maestro era el **Identity Provider** del ecosistema y todas las aplicaciones huésped consumían identidad vía headers `X-Auth-*` inyectados por Traefik ForwardAuth. En v4 ese modelo fue **invertido**:

- La Web Maestro es ahora **registry + redirector + provisioner**, no Identity Provider.
- Cada **aplicación huésped** (= app genérica = app tool) implementa su **propio login** (tabla `users` propia, tokens propios, middleware propio).
- El modelo de tenancy pasó de **multi-tenant lógico** (con `company_id` por fila) a **single-tenant físico** (un contenedor de app = una empresa).
- El Maestro abre las apps en `target="_blank"` desde su portal; ya no hace reverse-proxy con inyección de identidad ni iframes.

Detalle del cambio en `framework-agentico/CHANGELOG.md` v4.0.

---

## Premisas Fundamentales

### Premisa uno: La autenticación de usuarios es responsabilidad de cada aplicación huésped

Cada aplicación huésped implementa, gestiona y revoca su propio sistema de login. Mantiene su propia tabla `users` (con `password_hash` usando bcrypt cost ≥ 12 o argon2id), sus tablas `roles` y `permissions`, y emite sus propios tokens (cookies HttpOnly + Secure + SameSite, o JWT con expiración corta + refresh token). Cada app es responsable de validar sus tokens en cada request mediante un middleware propio.

La Web Maestro **NO** es Identity Provider. **NO** emite tokens de identidad de usuarios finales. **NO** inyecta headers `X-Auth-*`. **NO** consume credenciales de usuarios finales. La única autenticación que la Web Maestro realiza es:

1. La de sus propios **administradores** (con su propio login interno, que cumple las mismas reglas que cualquier app huésped: tabla `admin_users`, password hash, tokens propios). El admin canónico es `admin@llyasoc.com`, sembrado por la fase 05-seeding de la propia Web Maestro.
2. La server-to-server **hacia las apps huésped**: el Maestro firma los requests outbound con `X-Maestro-Api-Key` (para `/maestro/branding`) o `X-Maestro-Webhook-Secret` (para hooks salientes con HMAC-SHA256).

La implicación práctica: una aplicación huésped que intente leer headers `X-Auth-*` o que asuma identidad inyectada por el Maestro será **rechazada** en validación. El contrato `maestro.platform/v2` exige `auth.mode = "own"`.

### Premisa dos: Aislamiento físico por empresa (single-tenant)

Cada deployment es la combinación única **una aplicación huésped + una empresa = un contenedor + una base de datos dedicada**. La empresa está **implícita por contenedor**; no se filtra por `company_id` en queries dentro de la app. No existe ninguna tabla de app huésped que tenga `company_id`. No existe multi-tenancy lógica.

El motor de provisioning del Maestro genera, para cada deployment:

- Un contenedor de aplicación nombrado `app-<slug>-<empresa>`.
- Un contenedor de base de datos nombrado `db-<slug>-<empresa>` con credenciales únicas (≥ 32 caracteres aleatorios).
- Una red Docker dedicada `app-<slug>-<empresa>-net` privada, donde solo conviven los dos contenedores anteriores.

Compartir BD, red o contenedor entre deployments de distintas empresas es **arquitectónicamente imposible**. La aplicación huésped no necesita verificar `company_id` porque su universo de datos es, por construcción, una sola empresa.

Cuando una empresa adquiere licencia para varias apps, cada app obtiene su propio deployment (contenedor + BD propios). Los deployments de la misma empresa no comparten BD ni se comunican directamente; si necesitan intercambiar datos, lo hacen a través del API Gateway del Maestro.

### Premisa tres: La Web Maestro es registry + redirector + provisioner

La Web Maestro cumple cuatro responsabilidades acotadas y nada más:

1. **Registry**: mantiene un catálogo de aplicaciones registradas (`applications`), de empresas tenant (`companies`) y de deployments activos (`deployments`). Las apps se auto-registran via `POST /api/v2/apps/register` desde su CI/CD.
2. **Redirector**: cuando un usuario hace click en una app desde el portal del Maestro, el portal genera un link `<a target="_blank" href="<app_url>">` que abre la URL de la app en una pestaña nueva. La app pide su login propio. La Web Maestro **NO** transfiere identidad ni token al click.
3. **Provisioner**: levanta los contenedores Docker (app + BD) en redes privadas, inyecta las ENV vars necesarias (`DATABASE_URL`, `MAESTRO_API_KEY`, `SUPERADMIN_INITIAL_PASSWORD`, etc.) en runtime, ejecuta migraciones y seeders, y monitorea health checks.
4. **Brand consumer + hook emitter**: consume el endpoint `/maestro/branding` de cada app (autenticando con `X-Maestro-Api-Key`) para mostrar nombre y logos en su portal; emite hooks server-to-server (`on_user_added`, `on_user_removed`, `on_company_license_granted`, `on_company_license_revoked`) firmados con HMAC-SHA256.

La Web Maestro **NO** maneja sesión de usuarios finales. **NO** actúa como reverse proxy con identidad inyectada. **NO** renderiza apps en iframes. **NO** mantiene tabla `users` global de usuarios de las apps.

### Premisa cuatro: Agnosticismo tecnológico de las aplicaciones huésped

La Web Maestro no impone lenguaje, framework, base de datos ni herramienta a las aplicaciones huésped. El único requisito técnico es que la aplicación sea **containerizable mediante Docker** y que cumpla el contrato definido en su `maestro.yaml` v2.

Esto significa que la Web Maestro puede alojar aplicaciones escritas en Node.js, Python, Go, Java, PHP, .NET, Rust, Ruby, Elixir o cualquier otro lenguaje containerizable. La base de datos de cada deployment puede ser PostgreSQL, MySQL, MongoDB, SQLite o ninguna, según declare la app. Si la app no necesita base de datos, simplemente declara `requires.database: none` y el Maestro no provisiona ninguna.

La plantilla **Tailwise Bundle** (HTML, Laravel, React, Vue) es la opción **preferida** del template para apps que tienen frontend, pero **no es obligatoria**. Equipos que necesiten otro stack (Flutter Web, apps sin frontend propio, frameworks específicos del dominio) pueden documentar la excepción en `maestro.yaml` y operar normalmente. Los agentes con responsabilidades de UX/UI presentan Tailwise como recomendación; respetan la decisión final del PO.

Esta premisa protege la libertad de los equipos de desarrollo de elegir las herramientas que mejor conocen o que mejor se adaptan a su problema. La plataforma nunca será un cuello de botella tecnológico.

### Premisa quinta: Contrato de integración obligatorio y validado automáticamente

Cada aplicación huésped debe incluir en la raíz de su repositorio un archivo `maestro.yaml` con `apiVersion: maestro.platform/v2`. Este archivo es el contrato entre la app y la Web Maestro. Define qué recursos de infraestructura necesita la app, cómo verificar que está funcionando (health check), cómo autenticar requests del Maestro (api key del branding endpoint, webhook secret de los hooks), qué ENV vars consume, qué stack frontend usa (Tailwise o excepción) y cuántos recursos de CPU y memoria requiere.

Este contrato no es opcional ni decorativo. Es **validado automáticamente**:

- En el pipeline CI de cada app, mediante `maestro-cli validate` (o equivalente).
- En el momento del registro contra la Web Maestro, mediante el endpoint `POST /api/v2/apps/register`.

Si el contrato es inválido, le faltan campos obligatorios, declara valores fuera de rango o contradice algún no negociable, el pipeline falla y el despliegue se bloquea. **Apps con `apiVersion: maestro.platform/v1` son rechazadas** en `/api/v2/apps/register`.

Especificación completa del contrato en `docs/APP_HUESPED_SPEC.md` y en este conjunto de premisas, archivo `06-CONTRATO-MAESTRO-YAML.md` (a redactarse en el cleanup v4).

### Premisa sexta: Límites de recursos garantizados por deployment

Cada deployment opera con límites estrictos de CPU y memoria definidos en el `maestro.yaml` de la app y aplicados mediante flags de Docker (`--memory`, `--cpus`) al momento del provisioning. Un deployment que intente consumir más memoria de la asignada será detenido por el OOM Killer del kernel; uno que intente consumir más CPU será throttled por el scheduler de Docker.

El propósito es prevenir el efecto **vecino ruidoso** (noisy neighbor): un deployment con alta carga no puede degradar el rendimiento de otros deployments en el mismo servidor. Los tiers permitidos en v4 son `256m`, `512m`, `1g`, `2g`, `4g` para memoria y `0.25` a `4.0` cores para CPU.

El monitoreo detecta deployments que consistentemente alcanzan sus límites y genera alertas para que el operador evalúe si la aplicación necesita un tier superior o si tiene un problema de rendimiento.

### Premisa séptima: Mínimo privilegio en cada capa

Cada componente del sistema opera con los permisos mínimos necesarios para cumplir su función:

- Los contenedores de aplicación huésped y el contenedor de la Web Maestro ejecutan con usuarios **no-root** dentro del contenedor.
- Las credenciales de base de datos son únicas por deployment, generadas aleatoriamente con ≥ 32 caracteres, y solo permiten acceder a la BD de ese deployment. No hay credenciales compartidas entre deployments ni entre apps y la BD del Maestro.
- Los tokens propios de las apps tienen expiración corta (default 1 hora para JWT) y deben renovarse vía refresh token. Los tokens de los admins de la Web Maestro siguen la misma regla.
- Las api keys (`MAESTRO_API_KEY`, `MAESTRO_WEBHOOK_SECRET`) son únicas por deployment, almacenadas cifradas con AES-256 en la BD del Maestro, e inyectadas como ENV vars en runtime; nunca persisten en disco dentro del contenedor.
- Las redes Docker están segmentadas: el contenedor de app y su BD viven en una red privada dedicada; no hay conectividad de red directa entre contenedores de distintos deployments.

Este principio se aplica también a nivel humano: los desarrolladores de una app huésped tienen acceso únicamente al fork de su app y no pueden ver ni modificar el código del Maestro ni de otras apps. Los administradores de la plataforma tienen acceso al Maestro pero las operaciones destructivas (DROP DATABASE, destruir deployment, revocar licencia) requieren confirmación explícita y quedan registradas en el audit log.

### Premisa octava: Cifrado ubicuo y secretos fuera del código

Toda comunicación que sale al exterior usa **TLS 1.2+ (preferiblemente 1.3)** con certificados gestionados por Traefik vía Let's Encrypt. No existe tráfico HTTP plano expuesto fuera del VPS; Traefik redirige automáticamente todo HTTP a HTTPS y agrega header HSTS con duración de un año e includeSubDomains.

La comunicación server-to-server entre la Web Maestro y las apps huésped se firma con HMAC-SHA256: el Maestro envía `X-Maestro-Api-Key` para `/maestro/branding` (comparado timing-safe en la app) y `X-Maestro-Webhook-Signature` para hooks (cuyo cuerpo está firmado con `MAESTRO_WEBHOOK_SECRET`). Las apps verifican estas firmas en tiempo constante (`crypto.timingSafeEqual` o equivalente).

Los **secretos** (api keys, webhook secrets, credenciales de BD, JWT secrets) se almacenan **cifrados con AES-256** en la BD del Maestro y se descifran solo en el momento de la inyección al provisionar el contenedor. **Nunca** persisten en disco dentro del contenedor de la app. **Nunca** aparecen en logs, en respuestas de error, ni en historial de git. Pre-commit hooks y CI deep scans (gitleaks o equivalente) bloquean cualquier commit o push que introduzca un secreto en el código.

### Premisa novena: Observabilidad y recuperabilidad del estado

Cada deployment reporta su estado a través de **health checks periódicos** ejecutados por la Web Maestro contra el endpoint declarado en `health.endpoint` del `maestro.yaml`. La Web Maestro mantiene una máquina de estados completa para cada deployment:

```
provisioning -> starting -> healthy -> degraded -> suspended -> destroyed -> purged (>90 días)
```

Las **acciones correctivas escalonadas** ante health checks fallidos:

- Tras 3 fallos consecutivos: restart automático del contenedor.
- Tras 5 fallos: notificación al administrador.
- Tras 10 fallos: marcado como `suspended` y requiere intervención manual.

Los **logs** de todos los deployments se centralizan en un stack (Loki o equivalente) con búsqueda y filtrado. En v4 los logs incluyen `user_id` y `request_id` pero **NO** incluyen `company_id` (consecuencia del single-tenant físico: el deployment ya identifica la empresa, agregar el campo sería redundante y un artefacto del modelo v3 deprecado).

El **audit log** del Maestro registra toda acción administrativa con precisión de milisegundos: creación de empresas, asignación de usuarios, otorgamiento o revocación de licencias, provisioning o destrucción de deployments, cambios de configuración, accesos administrativos. Es **inmutable**: la tabla `audit_log` tiene triggers de base de datos que rechazan cualquier UPDATE o DELETE.

### Premisa décima: Persistencia de datos garantizada entre versiones

Las bases de datos de los deployments persisten entre versiones del framework agéntico y del contrato `maestro.platform`. Una migración de versión (v3 → v4, v4 → v5, etc.) NO trunca tablas, NO borra datos, NO destruye deployments existentes.

Cualquier cambio que afecte datos existentes requiere **confirmación explícita del PO** (Project Owner = Product Owner). Esto incluye, entre otros:

- Cambios de schema que afecten columnas con datos existentes.
- TRUNCATE de cualquier tabla.
- DROP de tablas con datos.
- DELETE masivos sin filtro estricto.
- Cambios en passwords de usuarios existentes.
- Rotación de api keys o webhook secrets que invalide las actuales sin reemplazo coordinado.

Las migraciones que dropean columnas se hacen **expand-then-contract**: primero se agrega la columna nueva con dual-write durante una versión completa; recién en una versión posterior, y con confirmación del PO, se dropea la vieja. Los seeders son siempre **idempotentes**: re-ejecutarlos no duplica datos ni cambia datos existentes (excepción explícita: el seeder del superadmin, cuando ya existe, no toca password ni roles asignados).

Detalle operativo en `framework-agentico/core/RULES.md` sección `politica_de_persistencia_de_datos`.

---

## Requisitos No Negociables

Los no negociables son cualitativamente diferentes de las premisas. Las premisas definen principios guía cuya implementación específica puede evolucionar. Los no negociables definen **límites duros que jamás pueden violarse**. Una violación de un no negociable bloquea automáticamente el despliegue de la aplicación o, si se detecta en runtime, genera una alerta crítica que requiere acción inmediata.

### No negociable uno: Auth propia obligatoria en cada app huésped

Toda aplicación huésped **DEBE** declarar `auth.mode = "own"` en su `maestro.yaml`. Toda aplicación huésped **DEBE** implementar:

- Un formulario de login servido en `auth.login_path` (default `/login`).
- Un endpoint POST que valida credenciales contra una tabla `users` con `password_hash` (bcrypt cost ≥ 12 o argon2id), emite un token (cookie HttpOnly+Secure+SameSite o JWT corto + refresh) y carga al usuario en el contexto del request.
- Un endpoint de logout que invalida el token.
- Un middleware que valida el token en endpoints protegidos y rechaza con `HTTP 401` cualquier request sin auth válida.

Toda aplicación huésped **NO DEBE** leer headers `X-Auth-*` (deprecados en v4). La Web Maestro v4 **no los emite** y un proxy mal configurado que los inyecte debe ser ignorado por la app. La Web Maestro **no acepta** registros de apps con `apiVersion: maestro.platform/v1` en `/api/v2/apps/register`. Si la validación CLI o el endpoint de registro detectan que la app declara `auth.mode != own` o consume `X-Auth-*`, el despliegue se bloquea.

Verificación continua: el `security-auditor` transversal busca lecturas de `X-Auth-*` en el código de la app en cada PR.

### No negociable dos: Single-tenant físico estricto

Toda aplicación huésped **NO DEBE** tener `company_id` (ni equivalente FK al tenant) en ninguna tabla. Toda query **NO DEBE** filtrar por `company_id`. Toda app **DEBE** asumir que su universo de datos es una sola empresa, implícita por contenedor.

El Maestro **NO DEBE** colocar dos deployments del mismo `application_id` y la misma `company_id` (un solo deployment por par app+empresa). El motor de provisioning **DEBE** rechazar la creación de un segundo deployment para el mismo par.

Verificación continua: el `compliance-analyst` y el `performance-analyst` validan en cada PR que no haya `company_id` en queries ni en logs.

### No negociable tres: Click en app abre URL en `target="_blank"`

El portal de la Web Maestro **NO DEBE** usar iframes para mostrar apps huésped. **NO DEBE** actuar como reverse proxy con inyección de identidad. **NO DEBE** transferir tokens, sesión o credenciales del usuario al click.

El portal **DEBE** generar links HTML estándar `<a target="_blank" href="<app_url>">` cuando el usuario hace click en una app. La app correspondiente abrirá en una pestaña nueva y pedirá su login propio.

El portal **PUEDE** mostrar al usuario un mensaje informativo previo (ej: "Vas a abrir <app>. Te pedirá login propio."). El portal **PUEDE** tracear el click en su audit log con `actor_user_id`, `application_id`, `deployment_id`. Pero **NO DEBE** participar de ninguna forma en la sesión de la app.

### No negociable cuatro: Health check obligatorio

Toda aplicación huésped **DEBE** exponer un endpoint HTTP **sin autenticación** en la ruta declarada en `health.endpoint` (default `/health`). Este endpoint **DEBE**:

- Responder `HTTP 200` con `Content-Type: application/json` y cuerpo que contenga al menos `{"status":"ok"}`.
- Responder en ≤ 5 segundos.
- No ejecutar lógica de negocio pesada, ni operaciones de escritura, ni consultas a servicios externos críticos.
- Verificar conectividad básica a la BD propia (`SELECT 1` en ≤ 200 ms).

Apps que no declaren health check, que no respondan a tiempo, o que respondan con código distinto a 200 no se provisionan. El Maestro ejecuta health checks periódicos contra el endpoint y aplica las acciones correctivas escalonadas descritas en la Premisa novena.

### No negociable cinco: Endpoint `/maestro/branding` obligatorio

Toda aplicación huésped **DEBE** exponer un endpoint en la ruta declarada en `branding.url` (default `/maestro/branding`). Este endpoint **DEBE**:

- Requerir el header `X-Maestro-Api-Key` con valor coincidente a la ENV var `MAESTRO_API_KEY` inyectada por el Maestro.
- Comparar el valor con `crypto.timingSafeEqual` (o equivalente del stack) para evitar timing attacks.
- Responder `HTTP 401` ante ausencia o invalidez del header.
- Responder `HTTP 200` con JSON `{"company_name": "...", "logo_url": "...", "primary_color"?: "...", "favicon_url"?: "..."}` cuando el header es válido. `company_name` y `logo_url` son obligatorios; los otros opcionales.

El Maestro consume este endpoint periódicamente (default cada 6 horas) para cachear el branding de cada deployment y mostrarlo en su portal. Apps sin endpoint de branding o que no autentican correctamente no se provisionan o pasan a `degraded` tras 3 consumos fallidos consecutivos.

### No negociable seis: Hooks server-to-server autenticados con HMAC-SHA256

Toda aplicación huésped que declare hooks en su `maestro.yaml` (`hooks.on_user_added`, etc.) **DEBE** verificar el header `X-Maestro-Webhook-Signature` antes de procesar el cuerpo. La firma sigue el formato `t=<unix_ts>,v1=<hex_hmac>` donde `v1 = HMAC-SHA256(MAESTRO_WEBHOOK_SECRET, "<unix_ts>.<raw_body>")`.

La app **DEBE**:

1. Leer el header.
2. Verificar que `|now - t| ≤ 300` segundos (anti-replay).
3. Recalcular el HMAC y comparar en tiempo constante.
4. Rechazar con `HTTP 401` si la firma no coincide.
5. Procesar el evento de manera **idempotente** usando el `event_id` UUIDv4 incluido en el cuerpo (el Maestro reintenta hasta 3 veces).

Hooks sin firma válida son ignorados.

### No negociable siete: Prohibición de ejecución como root en contenedores

El Dockerfile de toda aplicación huésped y de la Web Maestro **DEBE** incluir una instrucción `USER` que especifique un usuario **no-root** (UID ≠ 0). En multi-stage builds, esta instrucción se verifica en la etapa final.

Las imágenes que ejecutan procesos como root son **rechazadas automáticamente** durante la fase de validación del pipeline CI/CD. La verificación es estática sobre el Dockerfile, antes del build de la imagen.

Adicionalmente, el motor de provisioning del Maestro lanza los contenedores con la flag `--security-opt=no-new-privileges`, asegurando que ni siquiera si el proceso intenta escalar a root, el kernel lo permita.

### No negociable ocho: Secretos nunca en código fuente

Ningún secreto (passwords, api keys, claves privadas, cadenas de conexión, JWT secrets, webhook secrets) puede existir en el código fuente, en el historial de git, en archivos de configuración commiteados, ni en la imagen Docker resultante.

Todos los secretos se proveen exclusivamente vía **ENV vars inyectadas en runtime** por el motor de provisioning del Maestro. Estas ENV vars se almacenan cifradas con AES-256 en la BD del Maestro y se descifran solo al inyectarlas.

La verificación es continua y bloqueante:

- **Pre-commit hook** local con scan de secretos antes de cada commit.
- **CI** con scan profundo (gitleaks) sobre todo el historial de git en cada PR.
- **Image scan** (trivy o equivalente) sobre la imagen Docker construida en CI.

Si cualquiera de los tres scans detecta un secreto, la operación se bloquea sin posibilidad de waiver.

### No negociable nueve: Límites de recursos declarados obligatoriamente

El `maestro.yaml` de toda aplicación huésped **DEBE** incluir el bloque `resources` con los campos `memory` y `cpu`:

- `resources.memory` **DEBE** ser uno de: `256m`, `512m`, `1g`, `2g`, `4g`. No se aceptan otros valores.
- `resources.cpu` **DEBE** ser un decimal entre `0.25` y `4.0`.

Si el contrato no incluye estos campos, la validación CLI falla y la app no se provisiona. **No existe valor por defecto**: la omisión es un error, no aceptación tácita. Esto es intencional: el desarrollador debe tomar una decisión consciente sobre cuántos recursos necesita su aplicación.

### No negociable diez: Base de datos dedicada por deployment

Cada deployment que declare `requires.database != "none"` recibe su propia base de datos con nombre único, usuario dedicado y contraseña aleatoria de ≥ 32 caracteres. Estas credenciales son únicas para ese deployment y no se comparten con ninguna otra entidad.

Compartir una base de datos entre dos deployments (de la misma o de diferentes empresas) es **arquitectónicamente imposible**: el motor de provisioning crea una BD nueva para cada deployment y el contenedor de BD vive en una red Docker privada accesible solo desde el contenedor de aplicación de ese mismo deployment.

Cuando un deployment es destruido, la BD **NO** se elimina inmediatamente: se preserva durante **90 días** como periodo de retención. Durante ese periodo, un administrador puede restaurar el deployment con sus datos intactos. Tras los 90 días la BD es elegible para purgado automático, pero **nunca** sin que el audit log registre la operación y el operador la confirme explícitamente.

### No negociable once: TLS obligatorio sin excepciones

Todo tráfico entre los navegadores de los usuarios y la plataforma usa **HTTPS con TLS 1.2 mínimo** (preferiblemente 1.3). No existe ninguna ruta, endpoint ni servicio accesible vía HTTP plano desde fuera del VPS.

Traefik está configurado para:

- Redirigir todo tráfico HTTP (puerto 80) a HTTPS (puerto 443).
- Obtener y renovar certificados automáticamente vía Let's Encrypt (ACME).
- Enviar `Strict-Transport-Security: max-age=31536000; includeSubDomains` en cada respuesta HTTPS.

Si un certificado falla en renovarse, Traefik usa el anterior hasta su expiración y el sistema de alertas notifica al administrador con 30 días de antelación. Tráfico HTTP plano expuesto al exterior es un incidente de seguridad bloqueante.

### No negociable doce: Audit log inmutable

Toda acción administrativa realizada en la Web Maestro se registra en una tabla `audit_log` que es **inmutable**. La tabla acepta únicamente operaciones INSERT; los UPDATE y DELETE son rechazados a nivel de base de datos mediante triggers SQL (no solo a nivel de aplicación).

Cada registro contiene como mínimo:

- `id` (UUID v4)
- `timestamp` con precisión de milisegundos
- `actor_user_id` (id del admin que realizó la acción)
- `actor_ip`
- `action` (slug del tipo de acción)
- `resource_type`, `resource_id`
- `payload_before`, `payload_after`

Acciones registradas: creación/edición/eliminación de empresas, applications, deployments; otorgamiento o revocación de licencias; provisioning/suspensión/destrucción de deployments; rotación de api keys o webhook secrets; cambios de configuración del Maestro; logins/logouts/cambios de password de admins; ejecuciones de hooks salientes (success/failure).

### No negociable trece: Backup automatizado con retención mínima

Las BDs de todos los deployments y la BD del Maestro se respaldan **diariamente** entre las 02:00 y las 04:00 hora del servidor (configurable). Los respaldos se cifran antes de subirse a almacenamiento en la nube **separado del VPS** (Azure Blob Storage, S3, GCS u otro).

La **retención mínima es de 30 días**. Esto significa que en cualquier momento existen al menos 30 respaldos de cada BD, permitiendo restaurar a cualquier punto de los últimos 30 días. **La retención mínima no puede reducirse**; solo ampliarse.

Adicionalmente, la BD del Maestro se respalda **antes de cada migración de schema**.

### No negociable catorce: Persistencia de datos entre versiones

Las BDs de los deployments persisten entre versiones del framework y del contrato. Las migraciones del framework agéntico (v3 → v4, v4 → v5, etc.) **NO** truncan, borran ni destruyen datos existentes.

Cualquier cambio que afecte datos existentes (DROP TABLE, TRUNCATE, DELETE masivos, alteración de columnas con datos) requiere **confirmación explícita del PO** registrada en el audit log antes de ejecutarse. El framework-migrator (`framework-agentico/migration/migrator-template.md`) **NO toca código de la app ni datos de la BD**: solo genera un reporte de gaps.

Detalle operativo en `framework-agentico/core/RULES.md` sección `politica_de_persistencia_de_datos`.

---

## Relación entre premisas y no negociables

Las premisas y los no negociables están profundamente interrelacionados pero no son lo mismo. Una **premisa** dice "la autenticación de usuarios es responsabilidad de cada app huésped", lo cual es un principio de diseño. El **no negociable** correspondiente dice "toda app huésped DEBE declarar `auth.mode = own` y NO DEBE leer headers `X-Auth-*`", lo cual es un límite duro verificable.

Toda premisa tiene al menos un no negociable que la hace cumplir; pero un no negociable puede servir a múltiples premisas. Por ejemplo, el no negociable de aislamiento físico (single-tenant) sirve tanto a la premisa de aislamiento de datos como a la de mínimo privilegio.

Un agente que lea este documento debe entender:

- Las **premisas** informan **decisiones de diseño**.
- Los **no negociables** informan **decisiones de validación y bloqueo**.

Si una decisión técnica cumple una premisa pero viola un no negociable, la decisión es **inválida**. Si una decisión cumple todos los no negociables pero contradice el espíritu de una premisa, debe escalarse al PO antes de proceder.

---

## Referencias normativas

- `docs/APP_HUESPED_SPEC.md` — contrato `maestro.platform/v2` lado app.
- `framework-agentico/core/PRESET_WEB_MAESTRO.md` — preset que aplica a apps huésped (constraints por fase del framework agéntico).
- `framework-agentico/agents/presets/maestro-platform/PRESET.md` — preset que aplica a la Web Maestro misma.
- `framework-agentico/core/RULES.md` — reglas generales del framework agéntico v4 (glosario, versionado, persistencia, activación de preset).
- `framework-agentico/CHANGELOG.md` — historial de cambios entre versiones.
- `legacy/v3/PremisaWebMaestro/01-PREMISAS-Y-NO-NEGOCIABLES.md` — versión v1 (legacy, deprecado).

---

## Historial de revisiones

| Versión | Fecha | Cambio |
|---|---|---|
| 4.0.0 | 2026-05-07 | Versión inicial v4. Reescribe la constitución del Maestro alineada al modelo registry + redirector + provisioner del contrato `maestro.platform/v2`. Reemplaza al v1 (legacy en `legacy/v3/PremisaWebMaestro/01-PREMISAS-Y-NO-NEGOCIABLES.md`). |
