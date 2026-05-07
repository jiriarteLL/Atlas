# Premisas Fundamentales y Requisitos No Negociables

> ⚠️ **DEPRECADO** — Documento del framework v3 / contrato `maestro.platform/v1`.
> Conservado como referencia historica. NO aplicar en proyectos nuevos.
>
> **Version vigente:** `PremisaWebMaestro/01-PREMISAS-Y-NO-NEGOCIABLES.md` (constitucion del Maestro v4, redactada en Fase 3 del cleanup v4). Mientras tanto, ver `framework-agentico/agents/presets/maestro-platform/PRESET.md`.
> **Razon de la deprecacion:** ver `framework-agentico/CHANGELOG.md` v4.0.
>
> **Cambio principal v3 -> v4:** la Premisa Uno (auth centralizada por el Maestro con headers `X-Auth-*`) fue **invertida**. En v4 cada app huesped implementa su propio login. Ver CHANGELOG.

---

## Propósito de este documento

Este documento es la constitución de Maestro Platform. Todo lo que aquí se establece tiene fuerza vinculante sobre cualquier decisión técnica, de diseño o de implementación. Un agente de IA que reciba este documento debe internalizarlo como su marco de referencia primario antes de generar cualquier código, arquitectura o recomendación.

Las premisas son los axiomas: principios verdaderos sobre los cuales se construyen todas las decisiones. Los no negociables son los límites duros: restricciones absolutas que jamás pueden violarse bajo ninguna circunstancia, presión de negocio, limitación de tiempo o excepción técnica.

---

## Premisas Fundamentales

### Premisa uno: La autenticación es responsabilidad exclusiva del Maestro

Ninguna aplicación alojada en la plataforma implementa, gestiona ni muestra su propio sistema de login. El Maestro es el único Identity Provider de todo el ecosistema. Utiliza Laravel Passport como servidor OAuth2 y emite tokens JWT que contienen la identidad del usuario, su empresa activa y sus roles. Las aplicaciones alojadas reciben estos datos exclusivamente a través de headers HTTP que el reverse proxy Traefik inyecta después de validar el token contra el Maestro.

Lo que esto significa en la práctica es que una aplicación que intente mostrar un formulario de login, que intente validar credenciales por su cuenta, que intente emitir sus propios tokens o que intente gestionar sesiones de usuario de forma independiente será rechazada en el proceso de validación del contrato y no podrá desplegarse en la plataforma.

La implicación técnica directa es que toda aplicación debe leer la identidad del usuario exclusivamente de los headers HTTP que llegan en cada request. Estos headers son cuatro: X-Auth-User-Id que contiene el identificador único del usuario, X-Auth-User-Email que contiene el correo electrónico, X-Auth-Company-Id que contiene el identificador de la empresa activa del usuario, y X-Auth-Roles que contiene una lista separada por comas de los roles del usuario dentro de esa aplicación y esa empresa. El SDK provisto por la plataforma abstrae la lectura de estos headers, pero incluso sin el SDK, la app puede leerlos directamente del request HTTP.

### Premisa dos: Aislamiento completo de datos entre tenants

Cada instancia de aplicación, que es la combinación única de una empresa más una aplicación, posee su propia base de datos con credenciales únicas generadas automáticamente durante el provisionamiento. Las redes Docker están segmentadas de tal forma que el contenedor de base de datos de una instancia solo es accesible desde el contenedor de aplicación de esa misma instancia. No existe conectividad de red entre bases de datos de diferentes instancias ni entre contenedores de aplicación de diferentes tenants.

Adicionalmente, el SDK valida el campo company_id en cada operación de base de datos a nivel de middleware, creando una barrera de defensa que es independiente del código que escriba el desarrollador de la aplicación. Esto significa que incluso si un desarrollador olvida filtrar por empresa en una consulta, el middleware del SDK intercepta la operación y agrega automáticamente la condición de filtrado. Esta doble protección, aislamiento a nivel de red más filtrado a nivel de aplicación, garantiza que un bug en el código de la app no pueda exponer datos de un tenant a otro.

### Premisa tres: Agnosticismo tecnológico

La plataforma no impone ningún lenguaje de programación, framework, base de datos ni herramienta específica a las aplicaciones alojadas. El único requisito es que la aplicación sea containerizable mediante Docker y que cumpla el contrato definido en el archivo maestro.yaml. Esto significa que la plataforma puede alojar aplicaciones escritas en Node.js, Python, Go, Java, PHP, dotNET, Rust, Ruby o cualquier otro lenguaje que pueda ejecutarse dentro de un contenedor Docker.

La base de datos de cada instancia puede ser PostgreSQL, MySQL o MongoDB, según lo declare la aplicación en su contrato. Si una aplicación no necesita base de datos, también puede declarar que no requiere una y la plataforma simplemente no provisionará ninguna.

Lo que esta premisa protege es la libertad de los equipos de desarrollo de elegir las herramientas que mejor conocen o que mejor se adaptan a su problema específico. La plataforma nunca será un cuello de botella tecnológico que obligue a todos a usar el mismo stack.

### Premisa cuatro: Contrato de integración obligatorio y validado automáticamente

Cada aplicación que se aloja en la plataforma debe incluir en la raíz de su repositorio un archivo llamado maestro.yaml. Este archivo es el contrato entre la aplicación y la plataforma. Define qué recursos de infraestructura necesita la app, cómo verificar que está funcionando correctamente, qué variables de entorno espera recibir, cómo consume la autenticación y cuántos recursos de CPU y memoria requiere.

Este contrato no es opcional ni decorativo. Es validado automáticamente en cada push al repositorio mediante el CLI de la plataforma llamado maestro-cli. Si el contrato es inválido, si le faltan campos obligatorios, si declara valores fuera de rango o si contradice algún no negociable, el pipeline de integración continua falla y el despliegue se bloquea. No existe mecanismo para saltarse esta validación.

La especificación completa del contrato maestro.yaml se encuentra en el documento 06-SDK-Y-CONTRATO.md.

### Premisa cinco: Límites de recursos garantizados por instancia

Cada contenedor de aplicación opera con límites estrictos de CPU y memoria que se definen en el contrato maestro.yaml y se aplican mediante las flags de Docker al momento del despliegue. Esto significa que un contenedor que intente consumir más memoria de la asignada será detenido por el kernel de Linux a través del mecanismo OOM Killer, y un contenedor que intente consumir más CPU de la asignada será throttled por el scheduler de Docker.

El propósito de esta premisa es prevenir el efecto conocido como vecino ruidoso o noisy neighbor, donde una instancia con alta carga degrada el rendimiento de todas las demás instancias que comparten el mismo servidor. Con límites estrictos, cada instancia tiene un techo de consumo que no puede superar, independientemente de lo que haga la aplicación dentro del contenedor.

El monitoreo detecta instancias que consistentemente alcanzan sus límites y genera alertas para que el administrador evalúe si la aplicación necesita un tier de recursos superior o si tiene un problema de rendimiento que debe corregirse.

### Premisa seis: Principio de mínimo privilegio en cada capa

Cada componente del sistema opera con los permisos mínimos necesarios para cumplir su función y nada más. Los contenedores de aplicación ejecutan con usuarios no-root dentro del contenedor. Las credenciales de base de datos son únicas por instancia y tienen permisos limitados exclusivamente a su propia base de datos; un set de credenciales no puede acceder a la base de datos de otra instancia ni a la base de datos del Maestro. Los tokens JWT tienen expiración corta, por defecto una hora, y deben renovarse mediante refresh tokens. Las aplicaciones no tienen acceso a la red del Maestro más allá de lo necesario para recibir tráfico a través de Traefik.

Este principio se aplica también a nivel humano: los desarrolladores de una aplicación tienen acceso únicamente al repositorio de su aplicación y no pueden ver ni modificar el código del Maestro ni de otras aplicaciones. Los administradores de la plataforma tienen acceso al Maestro pero las operaciones destructivas requieren confirmación adicional y quedan registradas en el audit log.

### Premisa siete: Cifrado ubicuo de comunicaciones

Toda comunicación que sale del VPS hacia internet utiliza TLS versión 1.3 con certificados generados automáticamente por Let's Encrypt y gestionados por Traefik. No existe tráfico HTTP plano expuesto al exterior; todo request que llegue por puerto 80 es redirigido automáticamente al puerto 443 con HTTPS.

La comunicación interna entre el Maestro y las instancias de aplicación utiliza tokens firmados con HMAC-SHA256. Aunque esta comunicación ocurre dentro de la red Docker y no está expuesta al exterior, la firma garantiza que un contenedor comprometido no pueda fabricar requests falsos hacia el Maestro.

Los secretos, que incluyen credenciales de base de datos, tokens de API y claves de cifrado, se almacenan cifrados en la base de datos del Maestro usando cifrado simétrico AES-256. Se inyectan como variables de entorno en el contenedor de la aplicación únicamente en el momento del despliegue. Nunca se persisten en disco dentro del contenedor ni se exponen en logs.

### Premisa ocho: Observabilidad y recuperabilidad del estado

Cada instancia de aplicación reporta su estado a través de health checks periódicos que el motor de orquestación del Maestro ejecuta contra el endpoint de salud declarado en el contrato maestro.yaml. El Maestro mantiene un registro completo de estados para cada instancia, cubriendo todo su ciclo de vida desde el provisionamiento hasta la destrucción.

Cuando una instancia falla un health check, el sistema ejecuta acciones correctivas automáticas escalonadas: después de tres health checks fallidos consecutivos, reinicia el contenedor automáticamente; después de cinco, notifica al administrador de la plataforma; después de diez, suspende la instancia y la marca como que requiere intervención manual.

Los logs de todas las instancias se centralizan en un sistema de logging que permite buscar, filtrar y correlacionar eventos a través de todas las aplicaciones y todos los tenants. Esto es esencial para diagnosticar problemas que cruzan fronteras entre componentes.

---

## Requisitos No Negociables

Los no negociables son cualitativamente diferentes de las premisas. Mientras que las premisas definen principios guía cuya implementación específica puede evolucionar, los no negociables definen límites duros que jamás pueden violarse. Una violación de un no negociable bloquea automáticamente el despliegue de la aplicación o, si se detecta en runtime, genera una alerta crítica que requiere acción inmediata.

### No negociable uno: Zero Trust en autenticación

Ningún request HTTP llega a ninguna aplicación alojada sin haber sido autenticado previamente por el Maestro. Esto se implementa a través del middleware ForwardAuth de Traefik, que intercepta cada request antes de reenviarlo al contenedor de la aplicación, envía el token al endpoint de validación del Maestro, y solo si el Maestro responde confirmando que el token es válido, Traefik reenvía el request original con los headers de identidad inyectados.

No existen endpoints públicos en las aplicaciones alojadas. Si una aplicación necesita exponer un endpoint sin autenticación, como por ejemplo un webhook que recibe datos de un servicio externo, debe hacerlo a través de un mecanismo específico del Maestro que valida la fuente del webhook mediante firma HMAC en lugar de token JWT. Pero en ningún caso un request llega a la aplicación sin pasar por alguna forma de validación.

La verificación de este no negociable es continua en runtime. Traefik está configurado de forma que no existe ruta que bypass el middleware ForwardAuth. Si alguien modifica la configuración de Traefik para remover el middleware de una ruta, el sistema de monitoreo detecta la discrepancia y genera una alerta crítica.

### No negociable dos: Aislamiento de red por instancia

Cada instancia de aplicación vive en su propia red Docker dedicada. El contenedor de la aplicación y su contenedor de base de datos están conectados a esta red privada y solo pueden comunicarse entre sí. El contenedor de la aplicación tiene adicionalmente una conexión a la red compartida del Maestro, pero exclusivamente para recibir tráfico reenviado por Traefik. El contenedor de base de datos no tiene conexión a ninguna red compartida y es completamente inaccesible desde fuera de su red privada.

No existe mecanismo para que una aplicación se comunique directamente con otra aplicación a nivel de red. Si dos aplicaciones del mismo tenant necesitan intercambiar datos, deben hacerlo a través del API Gateway del Maestro, que actúa como intermediario, verifica permisos y registra la comunicación.

La verificación de este no negociable ocurre en el momento del provisionamiento. El motor de orquestación crea la red Docker aislada como primer paso antes de levantar cualquier contenedor. Si la creación de la red falla, todo el provisionamiento se detiene y la instancia queda en estado de fallo.

### No negociable tres: Health check obligatorio

Toda aplicación alojada en la plataforma debe exponer un endpoint HTTP en la ruta que declare en su contrato maestro.yaml, usualmente la ruta /health, que responda con código de estado HTTP 200 y un cuerpo JSON que contenga al menos el campo status con valor ok. Este endpoint debe responder en menos de cinco segundos. Si no responde o responde con un código de estado diferente a 200, se considera un health check fallido.

El CLI de validación verifica que el contrato maestro.yaml declare un endpoint de health check. Si no lo declara, la validación falla y la aplicación no puede desplegarse. Adicionalmente, durante el provisionamiento, el motor de orquestación espera a que el health check responda exitosamente antes de marcar la instancia como saludable y comenzar a enviarle tráfico.

Una aplicación que no tenga health check no puede existir en la plataforma. No hay excepciones ni waivers para este requisito.

### No negociable cuatro: Prohibición de ejecución como root en contenedores

El Dockerfile de toda aplicación debe incluir una instrucción USER que especifique un usuario no-root. Las imágenes Docker que ejecutan sus procesos como el usuario root son rechazadas automáticamente durante la fase de validación del pipeline de CI/CD.

El CLI de validación inspecciona el Dockerfile buscando la instrucción USER. Si no la encuentra, o si encuentra que el usuario especificado es root o tiene UID 0, la validación falla. Esto se hace estáticamente sobre el Dockerfile, no en runtime, para detectar el problema antes de que la imagen se construya.

Adicionalmente, el motor de orquestación configura el contenedor con la flag de Docker que previene la escalada de privilegios, asegurando que incluso si el proceso dentro del contenedor intenta cambiar a root, el kernel de Linux lo impide.

### No negociable cinco: Secretos nunca en código fuente

Ningún secreto, que incluye contraseñas, tokens de API, claves de cifrado, cadenas de conexión a base de datos, claves privadas y cualquier otro dato sensible, puede existir en el código fuente de una aplicación, en su historial de git, en sus archivos de configuración commiteados ni en su imagen Docker.

Todos los secretos se proveen exclusivamente a través de variables de entorno que el motor de orquestación del Maestro inyecta en el contenedor en el momento del despliegue. Estas variables de entorno se almacenan cifradas en la base de datos del Maestro y se descifran solo en el momento de la inyección.

La verificación de este no negociable utiliza dos herramientas complementarias. Primero, un hook de pre-commit que ejecuta un scan de secretos antes de permitir cada commit local. Segundo, el pipeline de CI/CD ejecuta un scan profundo con una herramienta de detección de secretos que analiza todo el historial de git, no solo el commit actual, buscando patrones que se parezcan a credenciales. Si cualquiera de los dos scans detecta un posible secreto, la operación se bloquea.

### No negociable seis: Límites de recursos declarados obligatoriamente

El contrato maestro.yaml de toda aplicación debe incluir la sección de recursos con al menos dos campos: memory que especifica el máximo de memoria RAM en formato como 256m o 1g, y cpu que especifica la fracción de core de CPU como 0.5 o 1.0.

Si el contrato no incluye estos campos, la validación del CLI falla y la aplicación no puede desplegarse. No existe un valor por defecto; la omisión es un error, no una aceptación tácita de algún límite predeterminado. Esto es intencional: el desarrollador debe tomar una decisión consciente sobre cuántos recursos necesita su aplicación.

Los valores declarados deben estar dentro de los rangos permitidos por el tier seleccionado. Los tiers y sus rangos se definen en el documento 04-INFRAESTRUCTURA-DOCKER.md.

### No negociable siete: Base de datos dedicada por instancia

Cada instancia de aplicación que declare que necesita una base de datos recibe su propia base de datos dedicada con un nombre único, un usuario dedicado y una contraseña generada aleatoriamente con al menos 32 caracteres de entropía. Estas credenciales son únicas para esa instancia y no se comparten con ninguna otra instancia ni con el Maestro.

Compartir una base de datos entre dos instancias de diferentes tenants es arquitectónicamente imposible. El motor de provisionamiento crea una base de datos nueva para cada instancia y el contenedor de base de datos vive en una red Docker privada accesible únicamente desde el contenedor de aplicación de esa misma instancia.

Cuando una instancia es destruida, la base de datos no se elimina inmediatamente. Se preserva durante noventa días como periodo de retención, después del cual es elegible para purgado automático. Durante este periodo, un administrador puede restaurar la instancia con sus datos intactos.

### No negociable ocho: TLS obligatorio sin excepciones

Todo tráfico entre los navegadores de los usuarios y la plataforma utiliza HTTPS con TLS versión 1.2 como mínimo, prefiriendo TLS 1.3 cuando el cliente lo soporte. No existe ninguna ruta, endpoint ni servicio accesible mediante HTTP plano desde fuera del VPS.

Traefik está configurado para redirigir automáticamente todo tráfico HTTP al equivalente HTTPS. Los certificados son generados y renovados automáticamente por Traefik utilizando el proveedor ACME de Let's Encrypt. Los headers HSTS se envían con una duración de un año y la directiva includeSubDomains para indicar a los navegadores que nunca intenten conectarse por HTTP.

Si un certificado falla en renovarse, Traefik continúa usando el certificado anterior hasta que expire. El sistema de alertas notifica al administrador treinta días antes de la expiración para que intervenga manualmente si la renovación automática sigue fallando.

### No negociable nueve: Audit log inmutable

Toda acción administrativa realizada en la plataforma se registra en un log de auditoría que es inmutable. Esto incluye la creación de empresas, la asignación de usuarios, el otorgamiento o revocación de licencias, el provisionamiento o destrucción de instancias, los cambios de configuración del Maestro, los accesos administrativos y cualquier operación que modifique el estado del sistema.

Cada registro del audit log contiene como mínimo la fecha y hora con precisión de milisegundos, el identificador del usuario que realizó la acción, la dirección IP desde donde se realizó, el tipo de acción, los datos antes del cambio y los datos después del cambio.

Los registros del audit log no pueden modificarse ni eliminarse. La tabla de auditoría no acepta operaciones UPDATE ni DELETE; solo INSERT. Esto se implementa tanto a nivel de aplicación como a nivel de base de datos mediante restricciones y triggers que rechazan cualquier intento de modificación.

### No negociable diez: Backup automatizado con retención mínima

Las bases de datos de todas las instancias activas se respaldan diariamente de forma automática. El respaldo se ejecuta durante la ventana de menor actividad, configurable pero por defecto entre las dos y las cuatro de la madrugada hora del servidor.

Los respaldos se almacenan en un servicio de almacenamiento en la nube separado del VPS, específicamente Azure Blob Storage, para que la pérdida total del VPS no implique la pérdida de los respaldos. Los respaldos se cifran antes de subirse al almacenamiento en la nube.

La retención mínima es de treinta días. Esto significa que en cualquier momento existen al menos treinta respaldos de cada base de datos, permitiendo restaurar a cualquier punto de los últimos treinta días. Esta retención mínima no puede reducirse; solo puede ampliarse.

La base de datos del Maestro se respalda con la misma frecuencia y retención, pero adicionalmente se realiza un respaldo antes de cada operación de migración de esquema.

---

## Relación entre premisas y no negociables

Las premisas y los no negociables están profundamente interrelacionados pero no son lo mismo. Una premisa dice "la autenticación es responsabilidad exclusiva del Maestro", lo cual es un principio de diseño. El no negociable correspondiente dice "ningún request llega a una app sin token válido verificado por Traefik", lo cual es un límite duro verificable.

Toda premisa tiene al menos un no negociable que la hace cumplir, pero un no negociable puede servir a múltiples premisas. Por ejemplo, el no negociable de aislamiento de red sirve tanto a la premisa de aislamiento de datos como a la premisa de mínimo privilegio.

El agente que lea este documento debe entender que las premisas informan decisiones de diseño, mientras que los no negociables informan decisiones de validación y bloqueo. Si una decisión técnica cumple una premisa pero viola un no negociable, la decisión es inválida.
