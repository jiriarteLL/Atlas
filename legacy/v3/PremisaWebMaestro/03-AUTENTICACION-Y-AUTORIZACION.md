# Autenticación y Autorización

> ⚠️ **DEPRECADO** — Documento del framework v3 / contrato `maestro.platform/v1`.
> Conservado como referencia historica. NO aplicar en proyectos nuevos.
>
> **Version vigente:** `PremisaWebMaestro/03-AUTENTICACION-Y-AUTORIZACION.md` (constitucion del Maestro v4, redactada en Fase 3 del cleanup v4). Mientras tanto, ver `framework-agentico/agents/presets/maestro-platform/PRESET.md`.
> **Razon de la deprecacion:** ver `framework-agentico/CHANGELOG.md` v4.0.
>
> **Cambio principal v3 -> v4:** el Maestro v4 NO es Identity Provider. NO emite headers `X-Auth-*`. NO usa Traefik ForwardAuth para autenticar apps huesped. Cada app tiene auth propia.

---

## Propósito de este documento

Este documento describe el sistema completo de identidad de Maestro Platform. Cubre los métodos de autenticación, la estructura de los tokens, el mecanismo de ForwardAuth que protege todas las aplicaciones, los niveles de autorización y los flujos detallados paso a paso que un agente de IA necesita comprender para implementar correctamente la capa de seguridad de identidad.

---

## Principio fundamental

El Maestro es el único emisor de identidad en toda la plataforma. Ninguna aplicación alojada autentica usuarios por sí misma. Todas las aplicaciones reciben la identidad del usuario ya resuelta a través de headers HTTP inyectados por Traefik después de validar el token contra el Maestro. Este principio es un no negociable y no admite excepciones.

---

## Métodos de autenticación

La plataforma soporta dos métodos de autenticación que convergen en un mismo formato de token JWT.

### Método uno: Usuario y contraseña

El usuario ingresa su correo electrónico y contraseña en el formulario de login del portal Maestro. Laravel Passport valida las credenciales contra la tabla users. Si las credenciales son correctas, Passport emite un access token JWT y un refresh token. El access token tiene una duración de una hora. El refresh token tiene una duración de treinta días. Ambos se almacenan en el navegador del usuario mediante cookies httpOnly y secure, lo que significa que JavaScript del lado del cliente no puede acceder a ellos y solo se envían sobre conexiones HTTPS.

### Método dos: Microsoft Authentication

El usuario hace click en el botón "Iniciar sesión con Microsoft" en el formulario de login. El portal redirige al usuario a la página de login de Microsoft Entra ID con los parámetros OAuth2 necesarios, incluyendo el client_id de la aplicación registrada en Azure, el redirect_uri que apunta de vuelta al Maestro, y los scopes solicitados que son openid, profile y email. El usuario se autentica en Microsoft. Microsoft redirige de vuelta al Maestro con un authorization code. El backend de Laravel intercambia el authorization code por un access token de Microsoft. El backend usa el access token de Microsoft para obtener el perfil del usuario, incluyendo su email y su Microsoft ID. El backend busca en la tabla users un registro cuyo campo microsoft_id coincida con el Microsoft ID recibido. Si lo encuentra, genera un JWT del Maestro para ese usuario. Si no lo encuentra, busca por email. Si encuentra un usuario con ese email pero sin microsoft_id, vincula la cuenta estableciendo el microsoft_id y genera el JWT. Si no encuentra ningún usuario, el comportamiento depende de la configuración de la empresa: si la empresa tiene auto-provisioning habilitado, crea un nuevo usuario automáticamente; si no, muestra un error indicando que el usuario no está registrado.

En ambos casos, el resultado final es el mismo: un JWT del Maestro con la misma estructura, independientemente de si el usuario se autenticó con contraseña o con Microsoft.

---

## Estructura del token JWT

El token JWT emitido por el Maestro contiene los siguientes claims, que son campos de datos dentro del token.

El claim sub contiene el UUID del usuario. Este es el identificador único e inmutable del usuario en toda la plataforma.

El claim email contiene el correo electrónico del usuario.

El claim name contiene el nombre completo del usuario.

El claim active_company es un objeto que contiene tres campos: id con el UUID de la empresa actualmente seleccionada, slug con el slug de la empresa, y role con el rol del usuario en esa empresa que puede ser owner, admin o member.

El claim companies es un arreglo de UUIDs que lista todas las empresas a las que el usuario tiene acceso con invitación aceptada. Este arreglo permite al frontend mostrar el selector de empresa sin hacer una consulta adicional al API.

El claim iat contiene el timestamp de emisión del token en formato Unix epoch.

El claim exp contiene el timestamp de expiración del token en formato Unix epoch. Por defecto es una hora después de iat.

El claim iss contiene el dominio del Maestro, por ejemplo maestro.tudominio.com, para identificar al emisor.

El token está firmado con el algoritmo RS256 usando la clave privada del Maestro. Cualquier componente que necesite verificar un token puede hacerlo usando la clave pública correspondiente sin necesidad de contactar al Maestro, aunque en la práctica la verificación centralizada a través de ForwardAuth es el mecanismo principal.

---

## Mecanismo de ForwardAuth

ForwardAuth es una funcionalidad de Traefik que permite delegar la decisión de autorización a un servicio externo antes de reenviar el request al destino final. En Maestro Platform, ForwardAuth es el guardián que protege todas las aplicaciones alojadas.

### Cómo funciona paso a paso

Cuando un request llega a Traefik dirigido a cualquier aplicación alojada, por ejemplo a la URL https://inventario-empresax.maestro.com/api/items, Traefik no lo reenvía inmediatamente al contenedor de la aplicación. En su lugar, Traefik extrae el token JWT del request, que puede venir en el header Authorization como Bearer token o en una cookie httpOnly, y envía un request interno al endpoint de validación del Maestro en la ruta /api/auth/validate, incluyendo el token.

El endpoint de validación del Maestro recibe el token, verifica su firma criptográfica, verifica que no ha expirado, extrae los claims del token, verifica que el usuario tiene acceso a la aplicación solicitada dentro de la empresa activa, y si todo es correcto, responde a Traefik con un código HTTP 200 y una serie de headers que contienen la identidad desglosada del usuario.

Traefik recibe la respuesta exitosa del Maestro, toma los headers de identidad de la respuesta y los inyecta en el request original, y finalmente reenvía el request al contenedor de la aplicación con esos headers agregados.

Si la validación falla por cualquier motivo, ya sea token expirado, firma inválida, usuario sin acceso a esa app o empresa, o cualquier otro error, el Maestro responde con un código HTTP 401 y Traefik devuelve ese 401 al navegador del usuario sin reenviar nada al contenedor de la aplicación.

### Headers inyectados

Los headers que Traefik inyecta en el request después de una validación exitosa son los siguientes.

El header X-Auth-User-Id contiene el UUID del usuario autenticado. Este es el mismo valor que el claim sub del JWT.

El header X-Auth-User-Email contiene el correo electrónico del usuario autenticado.

El header X-Auth-User-Name contiene el nombre completo del usuario autenticado.

El header X-Auth-Company-Id contiene el UUID de la empresa activa del usuario. Este es el campo que toda aplicación debe usar para filtrar datos por tenant.

El header X-Auth-Company-Slug contiene el slug de la empresa activa.

El header X-Auth-Roles contiene una cadena separada por comas con los roles del usuario. Incluye tanto el rol en la empresa como los roles específicos en la aplicación, por ejemplo admin,app_editor.

El header X-Auth-Permissions contiene una cadena JSON con los permisos granulares del usuario en la aplicación, si existen.

Estos headers son la única fuente de identidad que las aplicaciones alojadas deben consumir. Las aplicaciones no deben intentar decodificar el JWT directamente ni validarlo por su cuenta. Los headers ya contienen toda la información necesaria y han sido validados por el Maestro.

### Caché de validación

Para evitar que cada request a cada aplicación genere una consulta a la base de datos del Maestro, el endpoint de validación utiliza Redis como caché. Cuando un token se valida exitosamente por primera vez, el resultado se almacena en Redis con una clave derivada del hash del token y una duración de cinco minutos. Los requests subsiguientes con el mismo token durante esos cinco minutos se validan contra la caché sin consultar la base de datos.

Cuando un token se invalida, ya sea por logout del usuario, revocación administrativa o cambio de empresa activa, la entrada correspondiente en Redis se elimina inmediatamente, forzando que la siguiente validación consulte la base de datos y falle.

---

## Flujo de acceso a una aplicación desde el portal

Este flujo describe el camino completo desde que el usuario hace click en una aplicación en el sidebar del portal hasta que ve el contenido de la aplicación renderizado en el iframe.

Paso uno: el usuario, que ya tiene una sesión activa en el portal Maestro, hace click en la aplicación "Inventario" en el sidebar.

Paso dos: el frontend React del portal envía un request POST al endpoint /api/apps/session del Maestro con el identificador de la aplicación y el identificador de la empresa activa. Este request incluye el JWT del usuario en la cookie httpOnly.

Paso tres: el backend del Maestro valida el JWT, verifica que la empresa tiene una licencia activa para esa aplicación, verifica que el usuario tiene acceso a esa aplicación en esa empresa, y si todo es correcto, genera un token de sesión temporal. Este token temporal es un JWT con duración de treinta segundos, firmado con la misma clave que los tokens normales pero con un claim adicional que indica que es un token de transferencia de una sola vez.

Paso cuatro: el Maestro responde al frontend con el token temporal y la URL de la instancia de la aplicación, por ejemplo https://inventario-empresax.maestro.com.

Paso cinco: el frontend del portal carga un iframe con la URL de la instancia como src. Simultáneamente, establece un listener para el evento message del iframe.

Paso seis: cuando el iframe termina de cargar, la aplicación dentro del iframe envía un mensaje postMessage al padre con el evento MAESTRO_READY indicando que está lista para recibir autenticación.

Paso siete: el portal, al recibir MAESTRO_READY, envía un mensaje postMessage al iframe con el evento MAESTRO_AUTH que contiene el token temporal.

Paso ocho: la aplicación dentro del iframe recibe el token temporal, lo envía al Maestro para intercambiarlo por un token de sesión de larga duración específico para esa instancia, y establece su propia sesión interna usando ese token.

Paso nueve: a partir de este momento, todos los requests que la aplicación dentro del iframe haga a su propio backend pasan por Traefik, que ejecuta ForwardAuth contra el Maestro, valida el token de sesión, inyecta los headers X-Auth y reenvía el request al contenedor de la aplicación.

---

## Niveles de autorización

La autorización en Maestro Platform opera en cuatro niveles jerárquicos. Cada nivel debe superarse para que el request llegue a su destino.

### Nivel uno: Validación de plataforma

Este nivel verifica que el token JWT existe, no ha expirado y está firmado por el Maestro. Es responsabilidad de Traefik a través de ForwardAuth. Si falla, el request recibe un 401 y nunca llega a ninguna aplicación. Este nivel no sabe nada sobre aplicaciones ni licencias; solo verifica identidad básica.

### Nivel dos: Validación de licencia

Este nivel verifica que la empresa activa del usuario tiene una licencia con estado active para la aplicación específica que se está intentando acceder. Es responsabilidad del endpoint de validación del Maestro. Si la licencia no existe, está expirada, suspendida o cancelada, el request recibe un 403 con un mensaje que indica que la empresa no tiene licencia para esa aplicación.

### Nivel tres: Validación de acceso a la aplicación

Este nivel verifica que el usuario específico tiene un registro en la tabla application_user para esa aplicación en esa empresa. Es responsabilidad del endpoint de validación del Maestro. Una empresa puede tener licencia para una aplicación pero no todos sus usuarios tienen que tener acceso a ella. Si el usuario no tiene acceso, recibe un 403 con un mensaje que indica que no tiene permisos para esa aplicación.

### Nivel cuatro: Validación de permisos internos

Este nivel verifica los permisos granulares del usuario dentro de la aplicación, como si puede solo leer datos o también escribir, si puede administrar configuraciones o solo usarlas, y otros permisos específicos del dominio de la aplicación. Este nivel es responsabilidad de la aplicación misma, usando los datos que recibe en los headers X-Auth-Roles y X-Auth-Permissions. El SDK provisto por la plataforma incluye helpers para evaluar estos permisos.

---

## Manejo de sesiones y expiración

### Renovación de token

El access token tiene una duración de una hora. Quince minutos antes de que expire, el frontend del portal renueva automáticamente el token enviando el refresh token al endpoint de renovación de Passport. Si la renovación es exitosa, el nuevo access token reemplaza al anterior sin que el usuario note nada. Si la renovación falla porque el refresh token también expiró o fue revocado, el usuario es redirigido al login.

### Logout

Cuando el usuario hace click en "Cerrar sesión", el portal envía un request al endpoint de logout del Maestro que revoca tanto el access token como el refresh token, elimina la entrada de caché en Redis, envía un mensaje postMessage con evento MAESTRO_LOGOUT a todos los iframes abiertos para que las aplicaciones limpien sus sesiones internas, y finalmente redirige al usuario al formulario de login.

### Cambio de empresa activa

Cuando el usuario cambia la empresa activa en el selector del portal, el Maestro genera un nuevo JWT con el claim active_company actualizado a la nueva empresa. Este nuevo token invalida la caché del token anterior en Redis. Todas las aplicaciones abiertas en iframes se recargan con el nuevo contexto de empresa, lo que significa que el sidebar se actualiza para mostrar las aplicaciones de la nueva empresa y cualquier iframe abierto se redirige a la instancia correcta de la nueva empresa si la app está licenciada, o se cierra si la nueva empresa no tiene licencia para esa app.
