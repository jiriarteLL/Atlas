# CI/CD y Gobernanza de Repositorios

## Propósito de este documento

Este documento describe los pipelines de integración continua y despliegue continuo de Maestro Platform, la estructura organizativa de los repositorios, las protecciones que aíslan el código del Maestro del código de las aplicaciones, y el flujo completo desde un commit hasta el despliegue en producción.

---

## Estructura de repositorios

Los repositorios están organizados bajo una organización de GitHub dedicada a la plataforma. La separación entre repositorios sigue el principio de responsabilidad única: cada repositorio tiene un propósito claro y un equipo responsable.

### Repositorio del Maestro

El repositorio principal del Maestro contiene el código de la aplicación Laravel, el frontend React del portal, la configuración de Traefik, el motor de provisionamiento de instancias y las migraciones de la base de datos central. Este repositorio es accesible únicamente por el equipo de plataforma. Los desarrolladores de aplicaciones no tienen acceso de lectura ni escritura a este repositorio. Esto es una medida de seguridad: el código del Maestro gestiona autenticación, secretos y datos de todos los tenants, y su exposición representaría un riesgo.

El flujo de trabajo en este repositorio sigue un modelo de ramas con protección. La rama main está protegida y requiere al menos dos revisiones aprobadas para hacer merge. Los cambios se desarrollan en ramas feature que se crean desde main y se integran a través de pull requests. Los despliegues a producción se ejecutan automáticamente cuando un merge a main pasa todas las verificaciones.

### Repositorios de SDKs

Existen repositorios separados para cada SDK de lenguaje: uno para Node.js, uno para Python, uno para PHP/Laravel y uno para Go. Estos repositorios son públicos para los desarrolladores de aplicaciones porque necesitan consultar el código fuente del SDK para entender cómo funciona. El equipo de plataforma es responsable del mantenimiento de los SDKs. Los desarrolladores de aplicaciones pueden abrir issues y enviar pull requests pero no tienen merge permissions.

Cada SDK sigue versionado semver independiente. Los cambios breaking se comunican con anticipación y se documenta la guía de migración. Los SDKs se publican en los registros de paquetes correspondientes: npm para Node.js, pip para Python, Composer para PHP y el módulo de Go.

### Repositorio del CLI

El repositorio del CLI maestro-cli contiene la herramienta de validación y scaffolding. Es público para que los desarrolladores puedan instalarlo y usarlo. Se distribuye como un paquete npm que se instala globalmente.

### Repositorio template

El repositorio maestro-app-template es un template repository de GitHub. Cuando un desarrollador crea una nueva aplicación, puede usar este template como punto de partida. El template contiene la estructura de directorios base, archivos de configuración preconfigurados y documentación de referencia. Sin embargo, se recomienda usar el comando maestro-cli new en lugar del template directamente porque el CLI genera un scaffolding más completo y personalizado para el stack elegido.

### Repositorios de aplicaciones

Cada aplicación tiene su propio repositorio bajo la misma organización de GitHub, típicamente en un path como org/apps/nombre-de-la-app. El equipo de desarrollo de cada aplicación tiene acceso completo a su repositorio y no tiene acceso a los repositorios de otras aplicaciones. Esto garantiza que un equipo no puede ver ni modificar el código de otro equipo.

Cada repositorio de aplicación tiene configurados los mismos hooks y protecciones estándar: la rama main está protegida, se requiere al menos una revisión aprobada para merge, el pipeline de CI debe pasar antes de permitir merge, y el scan de secretos se ejecuta como pre-commit hook.

---

## Pipeline de CI/CD de aplicaciones

El pipeline de CI/CD de cada aplicación se define en el archivo .github/workflows/deploy.yml y se ejecuta en GitHub Actions. El pipeline tiene cinco fases que se ejecutan secuencialmente; si una fase falla, las siguientes no se ejecutan.

### Fase uno: Validación

Esta fase se ejecuta en cada push a cualquier rama. Su propósito es verificar que la aplicación cumple con el contrato de la plataforma y que el código está en buen estado.

Las acciones que se ejecutan son las siguientes. Primero, se instala maestro-cli como dependencia de desarrollo. Segundo, se ejecuta maestro-cli validate que verifica el contrato maestro.yaml, el Dockerfile, la declaración de recursos, la ausencia de secretos en el código y la declaración del auth mode. Tercero, se ejecuta el linter del stack correspondiente. Cuarto, se ejecutan los tests unitarios de la aplicación.

Si cualquiera de estas acciones falla, la fase falla y no se permite hacer merge a main. El desarrollador recibe un reporte detallado de qué falló y cómo corregirlo.

### Fase dos: Build

Esta fase se ejecuta solo cuando se hace merge a main. Su propósito es construir la imagen Docker de la aplicación.

Las acciones que se ejecutan son las siguientes. Primero, se construye la imagen Docker usando el Dockerfile del repositorio. La imagen se tagea con el SHA del commit para trazabilidad y con el tag latest para conveniencia. Segundo, se verifica que la imagen se construyó correctamente y que el tamaño es razonable, es decir menor a quinientos megabytes para la mayoría de stacks.

Si la construcción falla, la fase falla y no se publica ninguna imagen.

### Fase tres: Scan de seguridad

Esta fase se ejecuta después de un build exitoso. Su propósito es verificar que la imagen Docker no contiene vulnerabilidades conocidas.

Se ejecuta un escáner de vulnerabilidades de contenedores que analiza todas las capas de la imagen buscando vulnerabilidades catalogadas en bases de datos públicas de CVEs. El escáner clasifica las vulnerabilidades por severidad: crítica, alta, media y baja.

Si se encuentra al menos una vulnerabilidad crítica, la fase falla y la imagen no se publica. Si se encuentran vulnerabilidades altas, se genera un warning pero no se bloquea el despliegue; el equipo de la app recibe una notificación para que planifiquen la corrección. Las vulnerabilidades medias y bajas se reportan informativamente.

### Fase cuatro: Publicación de imagen

Esta fase se ejecuta después de un scan de seguridad exitoso. Su propósito es publicar la imagen Docker en el registry para que el Maestro pueda usarla para despliegues.

La imagen se publica en GitHub Container Registry bajo la organización de la plataforma. Las credenciales de acceso al registry se almacenan como secrets de GitHub Actions y nunca están visibles en el código del workflow.

### Fase cinco: Registro en Maestro

Esta fase se ejecuta después de una publicación exitosa. Su propósito es notificar al Maestro que existe una nueva versión de la aplicación disponible para despliegue.

Se envía un request POST al endpoint /api/apps/register del Maestro con los siguientes datos: el nombre de la aplicación tal como está declarado en maestro.yaml, la nueva versión, la referencia completa de la imagen Docker en el registry, el SHA del commit, y un hash del archivo maestro.yaml para que el Maestro pueda detectar si el contrato cambió.

El Maestro recibe la notificación, actualiza el registro de la aplicación con la nueva versión disponible, y dependiendo de la configuración, puede desplegar automáticamente la nueva versión a todas las instancias activas o marcarla como pendiente de despliegue manual por un administrador.

Si esta fase falla porque el Maestro no está disponible, se reintenta tres veces con intervalos de treinta segundos. Si sigue fallando, la imagen queda publicada en el registry pero no registrada en el Maestro; un administrador deberá registrarla manualmente.

---

## Protección del Maestro

Las aplicaciones nunca modifican el código del Maestro. La interacción entre las aplicaciones y el Maestro es exclusivamente a través de dos interfaces.

La primera interfaz es el API de registro. El pipeline de CI/CD de la aplicación envía la nueva versión de la imagen Docker al endpoint de registro del Maestro. El Maestro decide cuándo y cómo desplegarla. La aplicación no tiene control sobre el despliegue; solo publica su imagen y notifica.

La segunda interfaz es el contrato maestro.yaml. La aplicación define sus necesidades y capacidades en el contrato. El Maestro interpreta el contrato para provisionar la infraestructura adecuada. La aplicación no ejecuta comandos de Docker, no crea redes, no gestiona bases de datos y no configura Traefik. Todo eso es responsabilidad del Maestro.

No existe una tercera interfaz. Las aplicaciones no tienen acceso SSH al VPS, no tienen acceso a la base de datos del Maestro, no tienen acceso a la configuración de Traefik y no tienen acceso a los volúmenes de otras instancias. El principio de mínimo privilegio se aplica estrictamente.

---

## Estrategia de despliegue de nuevas versiones

Cuando el Maestro recibe la notificación de una nueva versión de una aplicación, tiene dos modos de despliegue configurables.

### Modo automático

En modo automático, el Maestro despliega la nueva versión a todas las instancias activas de la aplicación usando una estrategia blue-green. Primero, levanta un nuevo contenedor con la nueva versión en paralelo al contenedor existente. Segundo, ejecuta el health check contra el nuevo contenedor. Tercero, si el health check es exitoso, reconfigura Traefik para que envíe tráfico al nuevo contenedor. Cuarto, espera treinta segundos para que los requests en vuelo al contenedor viejo terminen. Quinto, detiene y elimina el contenedor viejo.

Si el health check del nuevo contenedor falla, el Maestro mantiene el contenedor viejo activo, elimina el nuevo contenedor y genera una alerta indicando que el despliegue falló. No hay interrupción del servicio.

### Modo manual

En modo manual, el Maestro registra la nueva versión como disponible pero no la despliega automáticamente. Un administrador de la plataforma o de la empresa debe aprobar el despliegue desde el panel de administración del Maestro. Esto es útil para aplicaciones críticas que requieren ventanas de mantenimiento programadas.

### Rollback

En cualquier momento, un administrador puede hacer rollback de una instancia a una versión anterior. El Maestro mantiene un historial de versiones desplegadas y puede reconstruir una instancia con cualquier versión anterior que esté disponible en el registry. El rollback sigue el mismo proceso blue-green que el despliegue.
