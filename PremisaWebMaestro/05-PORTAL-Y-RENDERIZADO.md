# Portal y Renderizado de Aplicaciones

## Propósito de este documento

Este documento describe cómo el portal Maestro renderiza las aplicaciones alojadas, el protocolo de comunicación entre el shell y los iframes, la seguridad del iframe, el manejo de estados de error, los principios de experiencia de usuario y los componentes del portal. Un agente de IA que implemente el frontend del portal o que necesite integrar una aplicación con el shell debe usar este documento como referencia.

---

## Arquitectura del portal

El portal Maestro es una Single Page Application construida con React y Tailwind CSS que actúa como shell de composición. El shell provee la estructura visual permanente que incluye la barra superior, el sidebar de navegación y el área de contenido principal donde se renderizan las aplicaciones dentro de iframes.

La decisión de usar iframes en lugar de micro-frontends con Module Federation o Web Components es deliberada y se basa en el requisito de agnosticismo tecnológico. Las aplicaciones alojadas pueden estar escritas en cualquier tecnología y no es viable ni deseable requerir que todas usen el mismo bundler o framework de frontend. Los iframes proporcionan aislamiento completo de CSS, JavaScript y DOM, lo que significa que una aplicación construida con Vue no puede interferir con otra construida con React ni con el shell del portal.

---

## Estrategias de renderizado

Existen tres estrategias de renderizado dependiendo del tipo de aplicación.

### Aplicación con frontend propio

Cuando la aplicación declara en su contrato maestro.yaml que tiene frontend propio con el campo has_frontend en verdadero, el portal carga la URL de la instancia directamente dentro de un iframe. La aplicación es responsable de renderizar su propia interfaz completa. El portal solo proporciona el shell que la rodea y el protocolo de comunicación para transferir la autenticación.

La aplicación con frontend propio debe implementar un modo embebido que oculte su propia barra de navegación superior y su propio sistema de login si tuviera uno. Esto se activa cuando la aplicación detecta que está corriendo dentro del portal Maestro, lo cual puede determinar verificando si recibe el evento MAESTRO_AUTH a través de postMessage.

### Aplicación solo API sin frontend

Cuando la aplicación declara que no tiene frontend propio con el campo has_frontend en falso, el Maestro genera automáticamente una interfaz de usuario genérica basada en el schema de la API de la aplicación. Esta UI genérica se renderiza dentro del iframe y permite a los usuarios interactuar con los endpoints de la API a través de formularios auto-generados y tablas de resultados. Es similar a una interfaz tipo Swagger UI pero más refinada y orientada al usuario final en lugar de al desarrollador.

Para que esta generación automática funcione, la aplicación debe exponer un endpoint de documentación de su API en formato OpenAPI o JSON Schema que el Maestro consulta durante el provisionamiento.

### Aplicación con frontend embebible

Algunas aplicaciones exponen un modo embebido explícito que adapta su interfaz al contexto del portal. En este modo, la aplicación oculta su propia navegación, usa un fondo transparente para integrarse visualmente con el shell, y utiliza el protocolo postMessage de forma más intensiva para sincronizar navegación y notificaciones con el portal.

---

## Protocolo de comunicación postMessage

La comunicación entre el shell del portal y las aplicaciones dentro de los iframes utiliza el API estándar del navegador postMessage. Este API permite enviar mensajes entre ventanas de diferentes orígenes de forma segura.

Todos los mensajes siguen una estructura estandarizada. Cada mensaje es un objeto JSON con un campo type que identifica el tipo de evento y un campo payload que contiene los datos del evento. Adicionalmente, cada mensaje incluye un campo source que indica quién envía el mensaje, ya sea maestro-shell o el slug de la aplicación.

### Evento MAESTRO_AUTH

Este evento fluye del shell hacia el iframe. Se envía cuando el iframe señala que está listo para recibir autenticación. El payload contiene tres campos: token que es el JWT temporal de treinta segundos para transferencia de autenticación, user que es un objeto con los datos básicos del usuario incluyendo id, name y email, y company que es un objeto con los datos de la empresa activa incluyendo id, slug y name.

La aplicación que recibe este evento debe intercambiar el token temporal por un token de sesión de larga duración enviándolo al endpoint de validación del Maestro. No debe almacenar el token temporal ni reutilizarlo porque es de un solo uso y expira en treinta segundos.

### Evento MAESTRO_READY

Este evento fluye del iframe hacia el shell. La aplicación lo envía cuando ha terminado de cargar y está lista para recibir el evento MAESTRO_AUTH. El payload contiene dos campos: appId que es el slug de la aplicación y version que es la versión actual de la aplicación.

El shell no envía el evento MAESTRO_AUTH hasta que no recibe MAESTRO_READY del iframe. Esto previene race conditions donde el shell envía la autenticación antes de que la aplicación esté lista para recibirla.

### Evento MAESTRO_NAVIGATE

Este evento fluye del iframe hacia el shell. La aplicación lo envía cuando el usuario navega dentro de la aplicación y quiere que la URL del navegador refleje esa navegación. El payload contiene dos campos: path que es la ruta interna de la aplicación como por ejemplo /items/42 y title que es el título de la página actual.

El shell actualiza la URL del navegador y el breadcrumb para reflejar la navegación interna de la app sin recargar la página. Esto permite que el usuario pueda copiar la URL y compartirla, y que al pegarla en otro navegador, el portal cargue directamente en esa vista de la aplicación.

### Evento MAESTRO_NOTIFY

Este evento fluye del iframe hacia el shell. La aplicación lo envía cuando necesita mostrar una notificación al usuario a nivel del portal, fuera del iframe. El payload contiene tres campos: type que puede ser success, warning, error o info, message que es el texto de la notificación, y duration que es opcional y especifica cuántos milisegundos debe mostrarse la notificación antes de desaparecer automáticamente.

### Evento MAESTRO_RESIZE

Este evento fluye del iframe hacia el shell. La aplicación lo envía cuando su contenido cambia de altura y necesita que el iframe se ajuste. El payload contiene un campo height con la altura deseada en píxeles. El shell ajusta la altura del iframe para eliminar scrollbars internos y que la experiencia se sienta como si la aplicación fuera parte del portal.

### Evento MAESTRO_LOGOUT

Este evento fluye del shell hacia todos los iframes. Se envía cuando el usuario cierra sesión en el portal. Las aplicaciones que reciben este evento deben limpiar cualquier sesión interna, estado local o datos cacheados. No necesitan redirigir al login porque el shell se encarga de eso.

---

## Seguridad del iframe

### Atributo sandbox

Cada iframe tiene el atributo sandbox con permisos específicos. Los permisos habilitados son allow-scripts que permite ejecutar JavaScript dentro del iframe, allow-same-origin que permite que el iframe acceda a su propio origen para hacer requests a su backend, y allow-forms que permite enviar formularios. Los permisos no habilitados incluyen allow-top-navigation que prevendría que la aplicación navegue la ventana padre, allow-popups que prevendría que la aplicación abra popups, y allow-modals que prevendría que la aplicación muestre alerts o confirms nativos del navegador.

### Validación de origen en postMessage

Todo handler de mensajes postMessage, tanto en el shell como en las aplicaciones, debe validar que el campo event.origin del mensaje coincide con el dominio esperado. El shell solo acepta mensajes de dominios que coincidan con subdominios registrados de la plataforma. Las aplicaciones solo aceptan mensajes del dominio del portal Maestro. Cualquier mensaje de un origen no reconocido se descarta silenciosamente.

### Content Security Policy

La configuración de Traefik incluye un header Content-Security-Policy que restringe qué orígenes pueden embeber las aplicaciones como iframes. Específicamente, la directiva frame-ancestors solo permite el dominio del portal Maestro, lo que significa que ningún sitio externo puede embeber las aplicaciones de la plataforma en sus propios iframes.

### Token temporal de transferencia

El token que se transfiere vía postMessage en el evento MAESTRO_AUTH tiene tres protecciones. Primera, tiene una duración de solo treinta segundos, lo que minimiza la ventana de vulnerabilidad si es interceptado. Segunda, es de un solo uso: una vez que la aplicación lo intercambia por un token de sesión, el token temporal se invalida y no puede usarse de nuevo. Tercera, está vinculado a una instancia específica; no puede usarse para acceder a otra instancia ni para obtener un token de sesión de otra aplicación.

---

## Componentes del portal

### Barra superior

La barra superior es el componente fijo en la parte superior de la ventana del navegador. Siempre está visible independientemente de qué aplicación esté cargada en el iframe. Contiene en su lado izquierdo el logotipo de Maestro Platform. En el centro muestra un breadcrumb que indica la empresa activa y la aplicación actual, por ejemplo "Empresa X > Inventario > Items". En su lado derecho muestra un ícono de notificaciones con badge que indica notificaciones no leídas, el avatar del usuario con su nombre, y un menú desplegable con opciones para ver perfil, cambiar contraseña y cerrar sesión.

Si el usuario pertenece a múltiples empresas, la barra superior incluye un selector de empresa activa que puede ser un dropdown o un modal dependiendo del número de empresas. Al cambiar de empresa, todo el contexto se actualiza.

### Sidebar de navegación

El sidebar es un panel vertical en el lado izquierdo que muestra las aplicaciones disponibles para la empresa activa. Cada aplicación se muestra con su ícono, su nombre y un indicador de estado: un punto verde si la instancia está corriendo, un punto gris si está dormida, un punto amarillo si está degradada, y un punto rojo si está fallida.

El sidebar incluye en su parte superior un campo de búsqueda rápida que filtra las aplicaciones por nombre. Debajo de la búsqueda, las aplicaciones se organizan en dos secciones: favoritos, que son las aplicaciones que el usuario marcó como favoritas, y todas las aplicaciones en orden alfabético.

En dispositivos móviles, el sidebar se colapsa y se accede a través de un botón hamburguesa en la barra superior.

### Área de contenido principal

El área de contenido principal ocupa todo el espacio restante después de la barra superior y el sidebar. Cuando no hay ninguna aplicación seleccionada, muestra una pantalla de bienvenida con el nombre del usuario, estadísticas de uso reciente y accesos directos a las aplicaciones más usadas.

Cuando hay una aplicación seleccionada, el área de contenido contiene el iframe que renderiza la aplicación. El iframe ocupa todo el ancho y todo el alto disponible, con ajuste dinámico de altura si la aplicación envía el evento MAESTRO_RESIZE.

### Pantalla de carga por cold start

Cuando el usuario selecciona una aplicación cuya instancia está dormida, el área de contenido muestra una pantalla de carga en lugar del iframe. Esta pantalla contiene una animación de carga sutil, el nombre e ícono de la aplicación, un mensaje que dice "Iniciando aplicación" seguido de puntos animados, un tiempo estimado basado en el histórico de cold starts de esa aplicación, y una barra de progreso indeterminada.

Cuando la instancia está lista, es decir cuando pasa su health check, la pantalla de carga se desvanece y el iframe se carga automáticamente.

### Centro de notificaciones

El centro de notificaciones es un panel deslizante que se abre al hacer click en el ícono de notificaciones de la barra superior. Muestra una lista cronológica de notificaciones que incluyen mensajes enviados por las aplicaciones a través del evento MAESTRO_NOTIFY, alertas del sistema como instancias caídas o licencias próximas a expirar, y mensajes administrativos.

Cada notificación se puede marcar como leída individualmente o se pueden marcar todas como leídas con un solo click.

---

## Manejo de estados de error y edge cases

### Aplicación no responde

Cuando el health check de una instancia falla y la instancia está en estado degradado, el portal muestra un banner sobre el iframe con el mensaje "La aplicación está experimentando problemas. Estamos trabajando para resolverlo." con un botón "Reintentar" que recarga el iframe. Si la instancia pasa a estado detenido, el iframe se reemplaza con una pantalla de error que explica que la aplicación no está disponible temporalmente y ofrece un botón para reiniciar la instancia si el usuario tiene permisos de administrador.

### Licencia expirada

Las aplicaciones con licencia expirada aparecen en el sidebar con un badge que dice "Expirada" en color rojo. Al hacer click, en lugar de cargar el iframe, el portal muestra un mensaje explicativo que indica que la licencia de esa aplicación ha expirado y que el administrador de la empresa debe renovarla para continuar usándola. Se incluye un botón "Contactar administrador" que envía un email al owner de la empresa.

### Sin conexión a internet

Si el navegador del usuario pierde la conexión a internet, el portal muestra un banner persistente en la parte superior que dice "Sin conexión a internet. Las acciones se reanudarán cuando la conexión se restablezca." El iframe puede seguir mostrando contenido ya cargado pero no podrá hacer nuevos requests. Cuando la conexión se restablece, el banner desaparece y el portal intenta revalidar el token de sesión.

### Token expirado durante uso

Si el token JWT expira mientras el usuario está usando una aplicación, el mecanismo de refresh automático intenta renovarlo en segundo plano. Si la renovación es exitosa, el usuario no nota nada. Si la renovación falla porque el refresh token también expiró, el portal muestra un modal que dice "Tu sesión ha expirado. Por favor, inicia sesión nuevamente." con un botón que redirige al formulario de login. La URL actual se preserva para que después del login el usuario vuelva exactamente a donde estaba.

### Usuario sin aplicaciones asignadas

Si un usuario inicia sesión pero no tiene ninguna aplicación asignada en su empresa activa, la pantalla de bienvenida muestra un mensaje que dice "No tienes aplicaciones asignadas. Contacta a tu administrador para solicitar acceso." con un ícono ilustrativo que transmite la situación sin ser alarmante.

---

## Principios de diseño de la experiencia de usuario

### Consistencia visual

El portal implementa un sistema de diseño con tokens de diseño compartidos incluyendo colores, tipografía, espaciados y radios de bordes. Las aplicaciones que adopten el design system opcional de la plataforma se verán visualmente integradas con el portal. Las aplicaciones que no lo adopten se ven como contenido embebido diferenciado pero no discordante.

### Zero friction login

El usuario inicia sesión una sola vez y accede a todo. La transición entre aplicaciones es instantánea para aplicaciones que ya están corriendo. El usuario nunca ve un segundo formulario de login dentro de una aplicación.

### Contexto siempre visible

El usuario siempre sabe en qué empresa está trabajando, qué aplicación está viendo y quién es. Esta información está permanentemente visible en la barra superior y nunca es ocultada por el contenido de la aplicación.

### Feedback inmediato

El portal nunca muestra pantallas en blanco sin explicación. Cada estado de carga, error o transición tiene un indicador visual claro que explica qué está pasando y qué debe hacer el usuario si se requiere alguna acción de su parte.

### Responsive obligatorio

El portal funciona en desktop, tablet y móvil. En desktop, el sidebar está expandido permanentemente. En tablet, el sidebar se puede colapsar y expandir. En móvil, el sidebar se oculta completamente y se accede mediante el botón hamburguesa. Los iframes usan CSS responsive para adaptarse al ancho disponible.

### Accesibilidad

El portal cumple con WCAG 2.1 nivel AA como mínimo. Esto significa contraste suficiente entre texto y fondo, navegación completa por teclado, compatibilidad con lectores de pantalla, etiquetas aria en todos los controles interactivos, y focus visible en elementos navegables por teclado.
