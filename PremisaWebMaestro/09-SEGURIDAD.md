# Seguridad: Defensa en Profundidad

## Propósito de este documento

Este documento presenta la estrategia de seguridad completa de Maestro Platform organizada en capas de defensa redundantes. El principio rector es que si una capa de seguridad falla o es comprometida, las capas restantes contienen la amenaza. Un agente de IA que implemente componentes de seguridad, configure infraestructura o revise código debe usar este documento como checklist de seguridad.

---

## Capas de seguridad

La seguridad se implementa en ocho capas que van desde el perímetro externo hasta los datos en reposo.

### Capa perimetral

La capa perimetral es la primera línea de defensa. Traefik, actuando como reverse proxy, es el único componente expuesto a internet. Todo el tráfico pasa por Traefik antes de llegar a cualquier otro componente.

Las medidas de esta capa incluyen la terminación TLS con certificados automáticos de Let's Encrypt, asegurando que toda comunicación externa está cifrada. La redirección forzosa de HTTP a HTTPS elimina la posibilidad de que un usuario accidentalmente envíe datos por una conexión no cifrada. El header HSTS con duración de un año instruye a los navegadores a nunca intentar conectarse por HTTP. El rate limiting por dirección IP previene ataques de fuerza bruta limitando el número de requests por segundo que una IP puede hacer. El rate limiting por tenant previene que una empresa con muchos usuarios sature la plataforma.

Los headers de seguridad que Traefik inyecta en todas las respuestas incluyen X-Content-Type-Options con valor nosniff que previene que el navegador interprete contenido con un tipo MIME diferente al declarado. X-Frame-Options no se usa globalmente porque los iframes son parte de la arquitectura, pero se reemplaza con Content-Security-Policy con la directiva frame-ancestors que restringe qué dominios pueden embeber las páginas como iframes, permitiendo solamente el dominio del portal Maestro. Referrer-Policy con valor strict-origin-when-cross-origin controla qué información de referrer se envía en requests entre orígenes. X-XSS-Protection con valor 1 y mode block habilita el filtro de XSS del navegador.

### Capa de autenticación

La capa de autenticación verifica la identidad de quien hace cada request. El mecanismo central es ForwardAuth en Traefik que delega la validación de tokens al Maestro.

Los tokens JWT están firmados con RSA SHA-256 usando un par de claves asimétricas. La clave privada está almacenada exclusivamente en el Maestro y nunca se expone. La clave pública está disponible para verificación pero no es necesaria para las aplicaciones porque la verificación se hace centralizadamente.

Los tokens tienen expiración de una hora. Los refresh tokens tienen expiración de treinta días. Cuando un usuario cierra sesión, tanto el access token como el refresh token se revocan inmediatamente en Redis y en la base de datos.

Las contraseñas de usuarios se almacenan hasheadas con bcrypt con un costo factor de doce. Nunca se almacenan en texto plano ni se transmiten en texto plano.

La autenticación de Microsoft utiliza el flujo Authorization Code de OAuth2 con PKCE, que es la variante más segura del flujo OAuth2.

### Capa de autorización

La capa de autorización verifica que la identidad autenticada tiene permiso para acceder al recurso solicitado. Opera en cuatro niveles como se describe en el documento de Autenticación y Autorización: validación de plataforma, validación de licencia, validación de acceso a la aplicación, y validación de permisos internos.

El principio rector es denegar por defecto. Si un request no tiene un token válido, se deniega. Si el usuario no tiene una licencia activa para la app, se deniega. Si el usuario no tiene un registro de acceso para esa app en esa empresa, se deniega. Solo cuando todas las verificaciones pasan explícitamente, el request se permite.

### Capa de aislamiento

La capa de aislamiento previene la fuga de datos entre tenants y la interferencia entre instancias.

Las redes Docker separadas por instancia garantizan que un contenedor comprometido no puede alcanzar los contenedores de otras instancias a nivel de red. El contenedor de base de datos de cada instancia solo es accesible desde su propio contenedor de aplicación.

Las bases de datos dedicadas por instancia con credenciales únicas garantizan que incluso si se filtran las credenciales de una instancia, no se puede acceder a los datos de otra instancia.

Los límites de recursos por contenedor previenen que una instancia con alta carga consuma toda la CPU o memoria del servidor, afectando a las demás.

### Capa de contenedor

La capa de contenedor asegura que los contenedores individuales no sean vectores de ataque.

La prohibición de ejecución como root significa que incluso si un atacante logra ejecutar código dentro del contenedor, no tendrá privilegios de root y no podrá escalar a root dentro del contenedor.

La prevención de escalada de privilegios a nivel de Docker impide que un proceso dentro del contenedor cambie a un usuario más privilegiado.

El sistema de archivos de solo lectura, donde sea posible según el stack tecnológico, previene que un atacante escriba archivos maliciosos dentro del contenedor. Los directorios que necesitan escritura, como los de logs o uploads temporales, se montan explícitamente como volúmenes de escritura.

El escaneo de imágenes Docker por vulnerabilidades en el pipeline de CI/CD detecta dependencias con vulnerabilidades conocidas antes de que la imagen llegue a producción.

### Capa de datos

La capa de datos protege la información en reposo y en tránsito.

Los campos sensibles en la base de datos del Maestro, específicamente las credenciales de base de datos y las variables de entorno de las instancias, están cifrados con AES-256 usando la clave de aplicación de Laravel. Estos campos se descifran solo en memoria cuando se necesitan y se descartan inmediatamente después.

Los backups de base de datos se cifran antes de subirse al almacenamiento en la nube. La clave de cifrado de backups es diferente de la clave de la aplicación y se almacena de forma separada.

Las conexiones a las bases de datos dentro de las redes Docker, aunque no están expuestas al exterior, usan autenticación con contraseña. No se permiten conexiones anónimas ni trust-based.

### Capa de auditoría

La capa de auditoría garantiza trazabilidad y detección de intrusiones.

El audit log inmutable registra toda acción administrativa con suficiente detalle para reconstruir qué pasó, quién lo hizo, cuándo y desde dónde. La inmutabilidad se garantiza a nivel de aplicación y de base de datos, previniendo que un atacante que comprometa la aplicación pueda borrar sus huellas.

Los access logs de Traefik registran todos los requests HTTP con timestamp, IP de origen, ruta, código de respuesta y latencia. Estos logs se envían al sistema centralizado de logging para análisis.

Los logs de las aplicaciones se centralizan en el stack de observabilidad, lo que permite correlacionar eventos entre diferentes componentes para detectar patrones de ataque que cruzan fronteras entre servicios.

### Capa de supply chain

La capa de supply chain protege contra ataques a la cadena de suministro de software.

El escaneo de vulnerabilidades de imágenes Docker en el pipeline de CI/CD detecta dependencias con CVEs conocidos antes de que lleguen a producción.

La generación de Software Bill of Materials permite inventariar todas las dependencias de cada aplicación y verificar que no contienen componentes con licencias incompatibles o vulnerabilidades conocidas.

El pinning de dependencias en los archivos de lock del gestor de paquetes, ya sea package-lock.json, requirements.txt, composer.lock u otro, garantiza que las builds sean reproducibles y que no se introduzcan versiones nuevas de dependencias sin revisión.

El uso de imágenes Docker base oficiales y el pinning de sus versiones por digest, no por tag, previene que un cambio en la imagen base introduzca vulnerabilidades o comportamiento malicioso.

---

## Gestión de secretos

Los secretos de la plataforma se clasifican en tres categorías según su alcance.

### Secretos de plataforma

Son secretos que pertenecen a la infraestructura del Maestro. Incluyen la clave de aplicación de Laravel, las credenciales de la base de datos del Maestro, la clave privada para firmar tokens JWT, el client secret de la aplicación de Microsoft Entra ID, las credenciales del registry de Docker, y la clave de cifrado de backups.

Estos secretos se almacenan en variables de entorno del contenedor del Maestro. Se cargan desde un archivo de entorno que está excluido del repositorio de git y que solo es accesible por el administrador del servidor. En una fase posterior de madurez, estos secretos se migrarán a Azure Key Vault.

### Secretos de instancia

Son secretos específicos de cada instancia de aplicación. Incluyen las credenciales de base de datos de la instancia y las variables de entorno sensibles declaradas en el contrato de la app.

Estos secretos se generan automáticamente durante el provisionamiento, se almacenan cifrados en la base de datos del Maestro, y se inyectan como variables de entorno en el contenedor de la app en el momento del despliegue. Nunca se persisten en disco dentro del contenedor.

### Secretos de CI/CD

Son secretos usados por los pipelines de GitHub Actions. Incluyen el token de acceso al registry de Docker y el token de autenticación para el endpoint de registro del Maestro.

Estos secretos se almacenan en GitHub Secrets a nivel de organización y se inyectan automáticamente en los workflows.

---

## Respuesta ante incidentes

Cuando se detecta un incidente de seguridad, el procedimiento de respuesta es el siguiente.

Para una instancia comprometida: el Maestro puede detener inmediatamente una instancia específica a través de la API de administración, cortando todo el tráfico y deteniendo el contenedor. Los logs de la instancia se preservan para análisis forense. La base de datos de la instancia se marca como potencialmente comprometida y se notifica al tenant.

Para una filtración de credenciales: si se detecta que las credenciales de una instancia fueron filtradas, el Maestro puede rotar las credenciales generando unas nuevas, actualizando la base de datos con las nuevas credenciales y reiniciando la instancia con las nuevas variables de entorno. Todo el proceso es automatizable.

Para un compromiso del Maestro: si el propio Maestro es comprometido, lo que constituiría el escenario más severo, el procedimiento incluye aislar el VPS de la red, restaurar desde el último backup verificado, rotar todos los secretos de plataforma incluyendo la clave JWT y la clave de la aplicación, y rotar todas las credenciales de instancia.
