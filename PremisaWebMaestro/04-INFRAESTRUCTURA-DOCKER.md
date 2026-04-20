# Infraestructura Docker y Ciclo de Vida de Instancias

## Propósito de este documento

Este documento describe la infraestructura Docker de Maestro Platform: la topología de redes, cómo se crean y destruyen las instancias, los estados del ciclo de vida, los mecanismos de aislamiento, los límites de recursos, las instancias dormidas y la estrategia de escalado progresivo. Un agente de IA que necesite implementar el motor de provisionamiento, configurar Traefik o gestionar contenedores debe usar este documento como referencia.

---

## Topología de redes Docker

Existen dos tipos de redes Docker en la plataforma.

### Red compartida: maestro-network

La red maestro-network es una red Docker bridge creada manualmente durante la instalación inicial de la plataforma. A esta red están conectados permanentemente los siguientes contenedores: Traefik que es el reverse proxy, el contenedor de la aplicación Laravel del Maestro, el contenedor de PostgreSQL del Maestro, el contenedor de Redis del Maestro, y el contenedor del queue worker del Maestro.

Adicionalmente, cada contenedor de aplicación alojada tiene una interfaz de red conectada a maestro-network. Esta conexión es exclusivamente para que Traefik pueda enviarle tráfico. El contenedor de la app no inicia comunicaciones hacia otros componentes de maestro-network por su cuenta.

La red maestro-network es el único punto de contacto entre la infraestructura del Maestro y las aplicaciones alojadas. Todo el tráfico que fluye por esta red está mediado por Traefik con ForwardAuth.

### Redes privadas por instancia

Cada instancia de aplicación tiene su propia red Docker bridge con un nombre que sigue el patrón net seguido de guión bajo, seguido del slug de la empresa, seguido de guión bajo, seguido del slug de la aplicación. Por ejemplo, net_empresax_inventario.

A esta red privada están conectados únicamente dos contenedores: el contenedor de la aplicación y el contenedor de base de datos de esa instancia. Nadie más puede alcanzar estos contenedores a través de esta red. El contenedor de base de datos no tiene ninguna otra conexión de red, lo que significa que es completamente inaccesible desde fuera de su red privada.

El contenedor de la aplicación tiene dos interfaces de red: una conectada a su red privada para comunicarse con su base de datos, y otra conectada a maestro-network para recibir tráfico de Traefik. Esta es la única forma de doble conexión que existe en la plataforma.

---

## Componentes del stack del Maestro

El Maestro se despliega como un conjunto de contenedores Docker gestionados por un archivo docker-compose. Los componentes son los siguientes.

Traefik es el reverse proxy que escucha en los puertos 80 y 443. Es responsable de la terminación TLS con certificados automáticos de Let's Encrypt, el ruteo dinámico basado en labels Docker que permite descubrir nuevas instancias automáticamente sin modificar configuración, la ejecución del middleware ForwardAuth contra el Maestro para validar tokens, el rate limiting por IP y por tenant para prevenir abuso, y la redirección automática de HTTP a HTTPS.

El contenedor Laravel del Maestro ejecuta la aplicación PHP con servidor Nginx y PHP-FPM. Sirve tanto el API REST como los assets estáticos del frontend React compilado. Escucha en un puerto interno que solo es accesible desde maestro-network.

El contenedor PostgreSQL del Maestro ejecuta la base de datos principal de la plataforma. Almacena empresas, usuarios, aplicaciones, licencias, instancias, audit logs y todas las demás entidades del modelo de datos. Solo es accesible desde maestro-network.

El contenedor Redis del Maestro sirve como caché de tokens de autenticación, almacén de sesiones, broker de colas para jobs asíncronos y caché general. Solo es accesible desde maestro-network.

El contenedor queue worker ejecuta Laravel Horizon o un worker de colas que procesa los jobs asíncronos. Estos jobs incluyen el provisionamiento y destrucción de instancias, la ejecución de health checks periódicos, el envío de notificaciones y la ejecución de backups. Este contenedor es idéntico al contenedor Laravel pero ejecuta el comando de queue worker en lugar del servidor web.

---

## Ciclo de vida de una instancia

Cada instancia de aplicación pasa por una serie de estados bien definidos. Las transiciones entre estados están controladas por el motor de orquestación del Maestro y no pueden forzarse manualmente excepto por un administrador con privilegios especiales.

### Estado PROVISIONING

Es el estado inicial cuando se crea una nueva instancia. El motor de orquestación ejecuta las siguientes acciones en orden. Primero, crea la red Docker privada para la instancia. Segundo, genera credenciales de base de datos únicas con al menos treinta y dos caracteres de entropía en la contraseña. Tercero, levanta el contenedor de base de datos dentro de la red privada con las credenciales generadas. Cuarto, espera a que la base de datos esté lista para aceptar conexiones. Quinto, ejecuta las migraciones iniciales de la aplicación si la app las define en su contrato. Sexto, genera las variables de entorno que la app necesita, incluyendo la URL de conexión a la base de datos, la URL del API del Maestro y el secreto de la app. Séptimo, levanta el contenedor de la aplicación con las variables de entorno inyectadas, los límites de recursos aplicados, las labels de Traefik configuradas y las dos interfaces de red conectadas. Si cualquier paso falla, la instancia transiciona al estado FAILED.

### Estado STARTING

La instancia está en este estado mientras el contenedor de la aplicación está arrancando y aún no ha pasado su primer health check exitoso. El motor de orquestación consulta el endpoint de health check cada cinco segundos. Si el health check responde exitosamente, la instancia transiciona a HEALTHY. Si no responde exitosamente después de sesenta segundos que es el timeout de arranque, la instancia transiciona a FAILED.

### Estado HEALTHY

La instancia pasó su primer health check y está lista para recibir tráfico. En este momento, Traefik comienza a rutear requests hacia el contenedor de la aplicación. La instancia transiciona inmediatamente a RUNNING.

### Estado RUNNING

Es el estado normal de operación. La instancia recibe tráfico, ejecuta su lógica de negocio y responde a requests. El motor de orquestación ejecuta health checks periódicos según el intervalo definido en el contrato, por defecto cada treinta segundos. Si el health check falla, el contador de health checks fallidos se incrementa. Si llega a tres, la instancia transiciona a DEGRADED. Si el health check vuelve a responder exitosamente, el contador se resetea a cero.

### Estado DEGRADED

La instancia ha fallado tres o más health checks consecutivos. El motor de orquestación intenta reiniciar el contenedor automáticamente. Si después del reinicio el health check responde exitosamente, la instancia vuelve a RUNNING. Si después de cinco health checks fallidos totales el problema persiste, se envía una notificación al administrador de la plataforma. Si se alcanzan diez health checks fallidos, la instancia transiciona a STOPPING y se marca como que requiere intervención manual.

### Estado SUSPENDED

La instancia ha sido suspendida, ya sea porque la licencia de la empresa expiró o porque un administrador la suspendió manualmente. El contenedor de la aplicación se detiene pero el contenedor de base de datos y los volúmenes persisten. La instancia no recibe tráfico. Puede transicionar de vuelta a STARTING si la licencia se renueva o si un administrador la reactiva. Los datos se preservan durante noventa días después de la suspensión, luego la instancia es elegible para purgado.

### Estado STOPPING

El motor de orquestación está deteniendo el contenedor de la aplicación. Envía una señal SIGTERM al proceso principal del contenedor y espera treinta segundos para un apagado limpio. Si el proceso no se detiene en treinta segundos, envía SIGKILL. La instancia transiciona a STOPPED cuando el contenedor se detiene exitosamente.

### Estado STOPPED

El contenedor de la aplicación está detenido pero todos los datos persisten: la base de datos sigue corriendo o sus volúmenes existen, las variables de entorno están almacenadas en el Maestro y la configuración de red existe. La instancia puede volver a STARTING en cualquier momento, que es exactamente lo que ocurre cuando una instancia dormida se reactiva.

### Estado DESTROYED

Los recursos de la instancia han sido liberados: la red Docker se eliminó y los contenedores se removieron. Sin embargo, los volúmenes de la base de datos se preservan durante el periodo de retención de noventa días. Después de ese periodo, los volúmenes se eliminan y la destrucción es irreversible. Este es un estado terminal; no se puede volver a ningún otro estado.

### Estado FAILED

Algo salió mal durante el provisionamiento o el arranque. El motor de orquestación registra el error detallado en los logs. Un administrador puede intentar el provisionamiento de nuevo, lo cual transiciona la instancia de vuelta a PROVISIONING.

---

## Instancias dormidas

Para optimizar el uso de recursos en el VPS, la plataforma implementa un mecanismo de instancias dormidas. Una instancia dormida es una instancia en estado STOPPED cuyo contenedor de aplicación fue detenido automáticamente porque no recibió tráfico durante un período configurable, que por defecto es treinta minutos.

### Cómo funciona el dormido

El motor de orquestación monitorea la última vez que cada instancia en estado RUNNING recibió un request. Esto se hace a través de los access logs de Traefik. Cuando una instancia no ha recibido ningún request durante el periodo de inactividad configurado, el motor envía un job asíncrono que transiciona la instancia a STOPPING y luego a STOPPED.

### Cómo funciona el despertar

Cuando un usuario intenta acceder a una instancia dormida, Traefik recibe el request pero no tiene un contenedor activo al cual reenviarlo. En este punto, Traefik devuelve un código HTTP 503 que el portal intercepta. El portal muestra una pantalla de carga al usuario con un mensaje indicando que la aplicación se está iniciando y un tiempo estimado. Simultáneamente, el portal envía un request al API del Maestro para despertar la instancia.

El Maestro recibe la solicitud de despertar, cambia el estado de la instancia a STARTING, levanta el contenedor de la aplicación y comienza a ejecutar health checks. Cuando el health check responde exitosamente, la instancia pasa a RUNNING y el portal automáticamente recarga el iframe para mostrar la aplicación.

El tiempo total de despertar, llamado cold start, depende de la complejidad de la aplicación y típicamente oscila entre cinco y quince segundos. Aplicaciones con imágenes Docker optimizadas y arranques rápidos pueden estar listas en menos de cinco segundos.

### Exclusiones del dormido

Algunas instancias pueden configurarse como never_sleep en su registro de company_application, lo que significa que nunca se dormirán automáticamente. Esto es típico para aplicaciones críticas que deben estar siempre disponibles, como sistemas de monitoreo o aplicaciones de comunicación en tiempo real. Esta configuración tiene un costo adicional porque consume recursos permanentemente.

---

## Límites de recursos

Cada instancia opera con límites estrictos de CPU y memoria que se aplican mediante las flags de Docker al crear el contenedor. Estos límites están organizados en tiers.

### Tier micro

El tier micro asigna un cuarto de core de CPU y doscientos cincuenta y seis megabytes de memoria RAM. El almacenamiento máximo para la base de datos es de un gigabyte. Este tier es adecuado para aplicaciones livianas como APIs simples, herramientas internas pequeñas o dashboards que consultan datos de fuentes externas.

### Tier standard

El tier standard asigna medio core de CPU y quinientos doce megabytes de memoria RAM. El almacenamiento máximo para la base de datos es de cinco gigabytes. Este tier es adecuado para la mayoría de aplicaciones típicas con bases de datos moderadas y tráfico normal.

### Tier professional

El tier professional asigna un core de CPU y un gigabyte de memoria RAM. El almacenamiento máximo para la base de datos es de veinte gigabytes. Este tier es adecuado para aplicaciones con alta carga, grandes volúmenes de datos o procesamiento intensivo.

### Tier enterprise

El tier enterprise asigna dos cores de CPU y dos gigabytes de memoria RAM. El almacenamiento máximo para la base de datos es de cincuenta gigabytes. Este tier es adecuado para aplicaciones críticas con requerimientos elevados de rendimiento y capacidad.

---

## Estrategia de escalado progresivo

La plataforma está diseñada para escalar en fases según la demanda crezca.

### Fase uno: un solo VPS

La fase actual. Toda la plataforma corre en un único VPS en Azure con Docker Engine directo. La capacidad es de cinco a veinte instancias simultáneas dependiendo de la RAM del VPS. Las instancias dormidas son el mecanismo principal de optimización. Esta fase es adecuada para los primeros meses de operación.

### Fase dos: múltiples VPS con Docker Swarm

Cuando la demanda supera la capacidad de un solo VPS, se agregan nodos adicionales y se migra a Docker Swarm para orquestar contenedores a través de múltiples máquinas. Traefik soporta Docker Swarm nativamente. La capacidad sube a veinte a cien instancias. Esta fase requiere mínimos cambios en el código del Maestro porque Docker Swarm es compatible con las mismas APIs de Docker.

### Fase tres: Kubernetes en Azure AKS

Cuando la complejidad operativa de Docker Swarm se vuelve un cuello de botella, se migra a Azure Kubernetes Service. Cada aplicación se empaqueta como un Helm chart. Traefik se reemplaza por el Ingress Controller de Kubernetes o se mantiene como Ingress provider. La capacidad sube a cien a quinientas instancias. Esta fase requiere cambios significativos en el motor de provisionamiento pero no en las aplicaciones alojadas ni en el contrato maestro.yaml.

### Fase cuatro: multi-región

Cuando se necesita servir a clientes en diferentes regiones geográficas con baja latencia, se despliegan clusters de Kubernetes en múltiples regiones de Azure con bases de datos geo-replicadas y un CDN global. Esta fase es de largo plazo y requiere un rediseño parcial del motor de orquestación.

Lo importante es que las aplicaciones alojadas no necesitan cambiar en ninguna de estas fases. El contrato maestro.yaml es el mismo. Los headers de autenticación son los mismos. Los SDKs funcionan igual. Toda la complejidad de la migración es responsabilidad del equipo de plataforma, no de los equipos de desarrollo de las aplicaciones.
