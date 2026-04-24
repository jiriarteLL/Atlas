# Plan de Implementación por Fases

## Propósito de este documento

Este documento establece las fases de construcción de Maestro Platform ordenadas cronológicamente. Cada fase tiene sus dependencias, entregables concretos, criterios de aceptación y una estimación de duración. Un agente de IA que asista en la planificación o ejecución del proyecto debe seguir este orden porque cada fase construye sobre los cimientos de la anterior.

---

## Principios del plan

Las fases son secuenciales pero con solapamiento controlado. La fase dos puede comenzar cuando la fase uno alcanza el ochenta por ciento de completitud. Pero la fase tres no puede comenzar hasta que la fase uno esté completamente terminada y aceptada.

Cada fase produce un entregable funcional. No hay fases puramente de diseño ni fases puramente de investigación. Al final de cada fase, algo funciona que no funcionaba antes.

Los criterios de aceptación son binarios. Se cumplen o no se cumplen. No hay aceptación parcial. Si un criterio no se cumple, la fase no está completa.

---

## Fase uno: Fundación de identidad y modelo de datos

Esta es la fase más importante. Todo lo demás se construye sobre los cimientos que se establecen aquí. Si esta fase se ejecuta mal, todas las fases siguientes heredarán los problemas.

### Alcance

Configurar Laravel Passport como servidor OAuth2 capaz de emitir tokens JWT. Implementar las migraciones de base de datos para todas las entidades del modelo de datos descrito en el documento 02-MODELO-DE-DATOS.md. Implementar los modelos de Eloquent con sus relaciones, scopes y reglas de validación. Implementar los endpoints de API para gestionar empresas, usuarios, aplicaciones y licencias. Implementar la autenticación con usuario y contraseña. Implementar la autenticación con Microsoft. Implementar el endpoint de validación de tokens que ForwardAuth usará en la fase dos.

### Dependencias

Ninguna. Esta es la primera fase.

### Entregables

Un servidor OAuth2 funcional que emite tokens JWT con la estructura definida en el documento de Autenticación y Autorización. Un endpoint POST /api/auth/login que acepta email y contraseña y retorna un JWT. Un flujo OAuth2 funcional con Microsoft Entra ID que retorna un JWT del Maestro. Un endpoint GET /api/auth/validate que recibe un token JWT y responde con headers X-Auth si es válido o con 401 si no lo es. Endpoints CRUD completos para companies, users, applications y las tres tablas pivote. Soft delete implementado en todas las entidades. Campos cifrados para datos sensibles. Audit log registrando todas las operaciones de escritura.

### Criterios de aceptación

Un usuario puede registrarse, iniciar sesión con contraseña y recibir un JWT válido. Un usuario puede iniciar sesión con Microsoft y recibir un JWT válido. El endpoint de validación responde correctamente con headers X-Auth para tokens válidos. El endpoint de validación responde 401 para tokens expirados, inválidos o revocados. Un usuario puede pertenecer a múltiples empresas y cambiar la empresa activa recibiendo un nuevo JWT. Las relaciones many-to-many funcionan correctamente con todas las reglas de integridad. El audit log registra toda operación administrativa con antes y después.

### Duración estimada

Tres a cuatro semanas.

---

## Fase dos: Reverse proxy y autenticación centralizada

Esta fase pone en producción el mecanismo de ForwardAuth que protegerá todas las aplicaciones futuras.

### Alcance

Desplegar Traefik como reverse proxy del stack del Maestro. Configurar terminación TLS con Let's Encrypt. Configurar el middleware ForwardAuth que consulta el endpoint de validación del Maestro. Configurar los headers de seguridad. Configurar rate limiting. Configurar la redirección HTTP a HTTPS.

### Dependencias

La fase uno debe estar completa porque ForwardAuth necesita el endpoint de validación funcional.

### Entregables

Traefik corriendo como contenedor dentro de maestro-network escuchando en puertos 80 y 443. Certificados TLS generados automáticamente para el dominio del Maestro. Redirección automática de HTTP a HTTPS. Middleware ForwardAuth configurado y funcional que valida tokens contra el Maestro e inyecta headers X-Auth. Rate limiting configurado con un límite razonable por defecto de cien requests por minuto por IP. Headers de seguridad inyectados en todas las respuestas.

### Criterios de aceptación

El portal Maestro es accesible exclusivamente por HTTPS. Un request sin token a cualquier ruta protegida recibe 401. Un request con token válido a una ruta protegida pasa al backend con headers X-Auth inyectados. Un request con token expirado recibe 401. La latencia agregada por ForwardAuth es menor a cincuenta milisegundos en percentil noventa y cinco. Los headers de seguridad están presentes en todas las respuestas verificables con herramientas de auditoría web.

### Duración estimada

Dos a tres semanas.

---

## Fase tres: Motor de provisionamiento de instancias

Esta fase implementa la capacidad de crear y destruir instancias de aplicaciones dockerizadas con aislamiento completo.

### Alcance

Implementar el motor de provisionamiento como un servicio Laravel que usa la API de Docker para gestionar contenedores. Implementar la creación de redes Docker aisladas por instancia. Implementar la creación de bases de datos dedicadas con credenciales únicas. Implementar la máquina de estados del ciclo de vida de instancias. Implementar los health checks periódicos. Implementar el auto-restart de instancias con health checks fallidos. Implementar las labels de Traefik para ruteo dinámico.

### Dependencias

La fase uno debe estar completa para el modelo de datos de instancias. La fase dos debe estar completa para que Traefik pueda rutear a los contenedores creados dinámicamente.

### Entregables

Un endpoint POST /api/instances/create que recibe el ID de la aplicación y el ID de la empresa y crea una instancia completa con red aislada, base de datos dedicada y contenedor de la app. Un endpoint POST /api/instances/stop y POST /api/instances/start para detener y reiniciar instancias. Un endpoint DELETE /api/instances/destroy para destruir instancias con periodo de retención de datos. Health checks periódicos ejecutándose como jobs en la cola de Laravel. Auto-restart funcional tras tres health checks fallidos consecutivos. Transiciones de estado correctas en la máquina de estados del ciclo de vida.

### Criterios de aceptación

Se puede crear una instancia de una aplicación de prueba dockerizada y accederla a través de su subdominio con autenticación ForwardAuth. La instancia tiene su propia red Docker, su propia base de datos y sus propios límites de recursos. El contenedor de base de datos solo es accesible desde el contenedor de la app. El health check detecta cuando la aplicación deja de responder y ejecuta restart automático. La instancia pasa por todos los estados del ciclo de vida correctamente. Los datos de una instancia no son accesibles desde otra instancia.

### Duración estimada

Tres a cuatro semanas.

---

## Fase cuatro: Portal web con renderizado de aplicaciones

Esta fase implementa la interfaz de usuario del portal que los usuarios finales usarán para acceder a sus aplicaciones.

### Alcance

Implementar el shell React del portal con barra superior, sidebar y área de contenido principal. Implementar el selector de empresa activa. Implementar el renderizado de aplicaciones en iframes. Implementar el protocolo postMessage para transferencia de autenticación. Implementar la pantalla de carga para cold start. Implementar la pantalla de bienvenida para usuarios sin apps. Implementar el manejo de estados de error.

### Dependencias

La fase uno para la autenticación del portal. La fase tres para que existan instancias que mostrar.

### Entregables

Un portal React funcional accesible en el dominio del Maestro. Sidebar que muestra las aplicaciones licenciadas de la empresa activa del usuario con indicadores de estado. Iframe que carga la aplicación seleccionada con transferencia de token vía postMessage. Selector de empresa activa funcional que cambia el contexto completo. Pantalla de carga cuando una instancia dormida está arrancando con tiempo estimado. Manejo visual de errores para apps caídas, licencias expiradas, tokens expirados y falta de conexión.

### Criterios de aceptación

Un usuario puede iniciar sesión y ver las aplicaciones de su empresa en el sidebar. Al hacer click en una aplicación, se carga dentro del iframe con autenticación transparente. El usuario nunca ve un segundo formulario de login dentro de la aplicación. Al cambiar de empresa, el sidebar se actualiza con las apps de la nueva empresa. Una instancia dormida muestra pantalla de carga y se auto-recarga cuando está lista. Los errores se manejan visualmente sin pantallas en blanco. El portal funciona en desktop, tablet y móvil.

### Duración estimada

Tres a cuatro semanas.

---

## Fase cinco: SDK versión uno y herramientas de desarrollo

Esta fase entrega las herramientas que los desarrolladores necesitan para crear aplicaciones para la plataforma.

### Alcance

Implementar el SDK de Node.js como primer SDK oficial. Definir y publicar el JSON Schema del contrato maestro.yaml. Implementar el CLI maestro-cli con los comandos validate y new. Crear el repositorio template de aplicaciones. Documentar el proceso de desarrollo de una nueva aplicación.

### Dependencias

Las fases uno a cuatro deben estar completas porque el SDK y el CLI interactúan con todos los componentes de la plataforma.

### Entregables

Paquete npm @maestro/sdk-node publicado con middleware de autenticación, filtro de tenant y helpers de permisos. CLI maestro-cli publicado en npm con los comandos validate y new funcionales. JSON Schema del contrato maestro.yaml publicado. Template repository de GitHub configurado. Documentación para desarrolladores que cubre desde cero hasta despliegue.

### Criterios de aceptación

Un desarrollador puede ejecutar maestro-cli new y obtener un proyecto funcional en menos de un minuto. El proyecto generado pasa maestro-cli validate sin errores. El SDK middleware lee correctamente los headers X-Auth y provee el objeto user en el request. El filtro de tenant agrega automáticamente la condición company_id a las consultas. La documentación cubre todos los pasos necesarios para crear, desarrollar y desplegar una aplicación.

### Duración estimada

Dos a tres semanas.

---

## Fase seis: Pipeline de CI/CD estandarizado

Esta fase implementa el pipeline automático que valida, construye y registra las aplicaciones.

### Alcance

Crear el workflow de GitHub Actions estándar para aplicaciones. Configurar la integración con el registry de Docker. Implementar el endpoint de registro de aplicaciones en el Maestro. Implementar el escaneo de imágenes por vulnerabilidades. Configurar las protecciones de rama en los repositorios.

### Dependencias

La fase cinco debe estar completa porque el pipeline usa maestro-cli validate.

### Entregables

Workflow de GitHub Actions funcional que ejecuta validación, build, scan, push y registro. Endpoint POST /api/apps/register funcional en el Maestro. Integración con el escáner de vulnerabilidades. Protecciones de rama configuradas en los repositorios de aplicaciones.

### Criterios de aceptación

Un push a cualquier rama ejecuta la validación y los tests. Un merge a main construye la imagen Docker, la escanea y la publica. La publicación exitosa notifica al Maestro con la nueva versión. Un build que falla la validación o el scan de seguridad bloquea el despliegue.

### Duración estimada

Dos semanas.

---

## Fase siete: Sistema agéntico

Esta fase implementa la capa de inteligencia artificial que asiste a los desarrolladores.

### Alcance

Definir el system prompt del Agente Orquestador con todas las reglas de la plataforma. Implementar la generación automática de CLAUDE.md como parte de maestro-cli new. Crear el primer agente especialista para Node.js con Express. Documentar cómo crear agentes especialistas para otros stacks.

### Dependencias

La fase cinco debe estar completa porque los agentes usan el SDK y el contrato.

### Entregables

System prompt del Agente Orquestador documentado y versionado. Comando maestro-cli new que genera CLAUDE.md automáticamente. CLAUDE.md funcional para Node.js con Express que hereda las reglas de plataforma. Guía para que los equipos creen agentes especialistas para otros stacks.

### Criterios de aceptación

Un desarrollador que use Claude Code con el CLAUDE.md generado recibe asistencia que cumple automáticamente con los no negociables de la plataforma. El agente se niega a generar código que viole el aislamiento de datos o implemente autenticación propia. El agente genera código con logging estructurado, manejo de errores centralizado y filtrado por tenant.

### Duración estimada

Dos a tres semanas.

---

## Fase ocho: Observabilidad

Esta fase implementa el monitoreo y las alertas.

### Alcance

Desplegar Prometheus, cAdvisor, Loki, Promtail y Grafana como contenedores del stack del Maestro. Configurar la recolección de métricas de todos los contenedores. Configurar la recolección de logs de todos los contenedores. Crear los dashboards ejecutivo, por instancia y del Maestro. Configurar las reglas de alertas con sus canales de notificación.

### Dependencias

La fase tres debe estar completa porque se necesitan instancias reales que monitorear.

### Entregables

Stack de observabilidad funcional con todos los componentes desplegados. Dashboards de Grafana configurados. Alertas configuradas con notificaciones a Slack y email. Métricas clave visibles y por debajo de sus umbrales saludables.

### Criterios de aceptación

Se puede ver el uso de CPU y memoria de cada instancia en Grafana en tiempo real. Se pueden buscar y filtrar los logs de cualquier instancia por texto, nivel de severidad y rango de tiempo. Las alertas se disparan correctamente cuando se simula una condición de error. Los dashboards se actualizan en tiempo real con latencia menor a treinta segundos.

### Duración estimada

Dos semanas.

---

## Fase nueve: Optimización y hardening

Esta fase afina el rendimiento y refuerza la seguridad antes de considerar la plataforma como producción-ready.

### Alcance

Implementar el mecanismo de instancias dormidas con cold start gestionado. Configurar la caché de Redis para validación de tokens. Optimizar las imágenes Docker del template. Ajustar los límites de rate limiting basados en datos reales. Ejecutar una auditoría de seguridad completa. Documentar los runbooks operativos.

### Dependencias

Todas las fases anteriores deben estar completas.

### Entregables

Instancias dormidas funcionales con cold start menor a quince segundos. Caché de tokens en Redis con hit rate mayor al noventa por ciento. Template Docker optimizado con imagen final menor a cien megabytes para Node.js. Auditoría de seguridad completada con todos los hallazgos remediados. Runbooks operativos para los escenarios más comunes.

### Criterios de aceptación

Las instancias sin tráfico se duermen automáticamente después del periodo configurado. Las instancias dormidas se despiertan correctamente cuando reciben un request. La latencia de ForwardAuth con caché activa es menor a diez milisegundos. La auditoría de seguridad no encuentra vulnerabilidades críticas ni altas sin remediar. Los runbooks cubren al menos los siguientes escenarios: instancia no responde, VPS sin espacio en disco, certificado TLS no se renueva, base de datos del Maestro no responde, y cómo hacer rollback de una aplicación.

### Duración estimada

Dos semanas.
