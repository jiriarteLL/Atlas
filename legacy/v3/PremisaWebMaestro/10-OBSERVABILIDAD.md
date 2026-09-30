# Observabilidad y Monitoreo

> ⚠️ **DEPRECADO** — Documento del framework v3 / contrato `maestro.platform/v1`.
> Conservado como referencia historica. NO aplicar en proyectos nuevos.
>
> **Version vigente:** `PremisaWebMaestro/10-OBSERVABILIDAD.md` (constitucion del Maestro v4, redactada en Fase 3 del cleanup v4). Mientras tanto, ver `framework-agentico/agents/presets/maestro-platform/PRESET.md` seccion `observabilidad`.
> **Razon de la deprecacion:** ver `framework-agentico/CHANGELOG.md` v4.0.
>
> **Cambio principal v3 -> v4:** stack se mantiene (Prometheus, Loki, Grafana). Cambian las metricas relevantes: en v4 ya no aplica `company_id` en logs (single-tenant fisico) y se agregan metricas de provisioning de deployments y consumo de `/maestro/branding`.

---

## Propósito de este documento

Este documento describe el stack de observabilidad de Maestro Platform, las métricas clave con sus umbrales, el sistema de alertas, los dashboards y la estrategia de logging centralizado. Sin observabilidad, la plataforma es ingobernable: no se puede operar lo que no se puede ver.

---

## Stack de observabilidad

La observabilidad se implementa con herramientas open source que se despliegan como contenedores adicionales dentro del stack del Maestro.

### Prometheus y cAdvisor para métricas

Prometheus es el sistema de recolección y almacenamiento de métricas. Funciona mediante un modelo pull donde Prometheus consulta periódicamente los endpoints de métricas de los componentes monitoreados.

cAdvisor se ejecuta como un contenedor con acceso al socket de Docker y recolecta métricas de todos los contenedores en ejecución. Las métricas que recolecta incluyen uso de CPU por contenedor expresado como porcentaje del límite asignado, uso de memoria RAM por contenedor en bytes, tráfico de red entrante y saliente por contenedor, uso de disco por contenedor, y el número de procesos activos dentro de cada contenedor.

Prometheus almacena estas métricas con una retención de quince días. Para datos históricos de más largo plazo, se exportan a almacenamiento externo.

### Loki y Promtail para logs

Loki es el sistema de almacenamiento y consulta de logs. A diferencia de sistemas como Elasticsearch, Loki indexa los logs por etiquetas y no por contenido, lo que lo hace más eficiente en recursos.

Promtail es el agente que recolecta logs de los contenedores Docker y los envía a Loki. Se configura para recolectar los logs de todos los contenedores etiquetando cada entrada con el nombre del contenedor, la aplicación, la empresa y la instancia.

Los logs de Traefik proporcionan visibilidad sobre todos los requests HTTP: IP de origen, ruta solicitada, código de respuesta, tiempo de respuesta, y headers relevantes. Los logs del Maestro proporcionan visibilidad sobre operaciones administrativas, provisionamiento de instancias, validaciones de tokens, y errores internos. Los logs de las aplicaciones proporcionan visibilidad sobre la lógica de negocio de cada app, errores de aplicación, y eventos relevantes del dominio.

### Grafana para dashboards y alertas

Grafana es la interfaz de visualización que consume datos de Prometheus y Loki para presentar dashboards y ejecutar reglas de alertas.

Grafana está configurada con autenticación propia pero accesible solo desde la red interna o a través de una VPN. Los administradores de la plataforma son los únicos usuarios de Grafana. Los tenants no tienen acceso directo a Grafana; sus métricas y logs se les presentan a través del panel de administración del Maestro si es aplicable.

---

## Métricas clave y umbrales

Las siguientes métricas son las más importantes para la operación de la plataforma. Cada una tiene un umbral saludable y una acción recomendada cuando se supera.

### Tiempo de respuesta de ForwardAuth en percentil noventa y cinco

Esta métrica mide cuánto tarda el endpoint de validación de tokens del Maestro en responder a Traefik. Es crítica porque afecta la latencia de todos los requests a todas las aplicaciones. El umbral saludable es menos de cincuenta milisegundos. Si se supera consistentemente, indica que la base de datos del Maestro o Redis están bajo carga excesiva. La acción es investigar queries lentos en la base de datos del Maestro, verificar que la caché de Redis está funcionando correctamente, y evaluar si la conexión pooling de PostgreSQL necesita ajuste.

### Tiempo de cold start de instancias dormidas

Esta métrica mide cuánto tiempo pasa desde que se solicita despertar una instancia dormida hasta que pasa su primer health check exitoso. Es importante para la experiencia del usuario que espera que la aplicación se cargue. El umbral saludable es menos de quince segundos. Si se supera, indica que la imagen Docker de la aplicación es demasiado grande, que la aplicación tiene un arranque lento, o que el VPS está bajo carga. La acción es optimizar la imagen Docker con multi-stage builds, investigar el proceso de arranque de la aplicación, y evaluar si el VPS tiene suficientes recursos.

### Health checks fallidos por hora por instancia

Esta métrica mide la estabilidad de cada instancia. El umbral saludable es menos de cinco fallos por hora por instancia. Si se supera, indica que la aplicación tiene problemas intermitentes de estabilidad. El sistema automáticamente reinicia instancias con tres fallos consecutivos y alerta al administrador con cinco fallos. La acción es revisar los logs de la instancia para identificar la causa raíz, evaluar si la aplicación necesita más recursos, y contactar al equipo de desarrollo de la app.

### Uso de RAM del VPS

Esta métrica mide el consumo total de memoria del servidor. El umbral saludable es menos del ochenta por ciento de la RAM total. Si se supera, el servidor empieza a usar swap lo que degrada el rendimiento de todo el sistema. La acción es activar el dormido de instancias más agresivamente, reduciendo el timeout de inactividad, evaluar si alguna instancia está consumiendo más memoria de la esperada, y planificar la migración a un VPS más grande o la transición a múltiples nodos.

### Errores HTTP 5xx por hora por aplicación

Esta métrica mide los errores internos de servidor de cada aplicación. El umbral saludable es menos de diez errores por hora. Si se supera, indica un problema en la aplicación que está causando fallos. La acción es notificar al equipo de desarrollo de la app, revisar los logs de la instancia para identificar la causa, y evaluar si es necesario hacer rollback a una versión anterior.

### Tiempo de login en percentil noventa y cinco

Esta métrica mide la latencia del proceso de inicio de sesión, desde que el usuario envía sus credenciales hasta que recibe el token JWT. El umbral saludable es menos de dos segundos. Si se supera, indica problemas en el rendimiento de Laravel Passport o en la base de datos del Maestro. La acción es optimizar las queries de autenticación, verificar el rendimiento de bcrypt con el costo factor actual, y evaluar el caching de sesiones.

### Espacio en disco del VPS

Esta métrica mide el uso del sistema de archivos del VPS incluyendo las imágenes Docker, los volúmenes de las bases de datos de las instancias, y los logs. El umbral saludable es menos del setenta por ciento de ocupación. Si se supera, la acción es purgar imágenes Docker no utilizadas, limpiar logs antiguos, y evaluar si las instancias destruidas que están en período de retención pueden purgarse anticipadamente.

---

## Sistema de alertas

Las alertas se configuran en Grafana y se envían a través de canales de notificación configurables. Los canales recomendados son un canal de Slack dedicado para alertas operativas y email al equipo de plataforma.

Las alertas se clasifican en tres niveles de severidad.

Las alertas críticas requieren acción inmediata. Incluyen el VPS con más del noventa por ciento de RAM usada, más de tres instancias en estado FAILED simultáneamente, Traefik no responde o no puede validar tokens, la base de datos del Maestro no responde, y los certificados TLS expiran en menos de siete días.

Las alertas de advertencia requieren atención dentro de las próximas horas. Incluyen una instancia con más de cinco health checks fallidos en la última hora, el VPS con más del ochenta por ciento de RAM usada, más de cincuenta errores 5xx en la última hora agregados entre todas las apps, y un backup diario que falló.

Las alertas informativas se revisan en la siguiente revisión programada. Incluyen una nueva versión de aplicación registrada, una instancia desplegada o destruida, un tier de recursos cercano al límite en alguna instancia, y una licencia que expira en menos de treinta días.

---

## Dashboards

### Dashboard ejecutivo global

Este dashboard muestra una vista de alto nivel de toda la plataforma. Incluye el número total de instancias activas, dormidas y detenidas, el uso agregado de recursos del VPS como porcentaje de CPU y RAM, el número de requests por minuto agregado, la tasa de errores global, y el uptime de la plataforma en los últimos treinta días.

### Dashboard por instancia

Este dashboard muestra las métricas detalladas de una instancia específica. Incluye el uso de CPU y memoria del contenedor de la app, el uso de disco de la base de datos, la tasa de requests por minuto, la distribución de códigos de respuesta HTTP, el tiempo de respuesta en percentiles cincuenta, noventa y noventa y cinco, y el historial de health checks con fallos marcados.

### Dashboard del Maestro

Este dashboard muestra las métricas internas del propio Maestro. Incluye el tiempo de respuesta de ForwardAuth, el hit rate de la caché de Redis para tokens, el número de tokens activos, el throughput de la cola de jobs, y el espacio usado por la base de datos central.

---

## Retención de datos de observabilidad

Las métricas de Prometheus se retienen durante quince días con resolución completa. Después de quince días, se compactan a resolución de una hora y se retienen durante noventa días.

Los logs en Loki se retienen durante treinta días. Después de treinta días se eliminan automáticamente. Los logs de auditoría, que son diferentes de los logs operativos, se retienen indefinidamente en la tabla audit_logs de la base de datos del Maestro.

Los datos de alertas y sus resoluciones se retienen durante noventa días para análisis de patrones.
