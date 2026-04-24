# SDK y Contrato de Integración

## Propósito de este documento

Este documento especifica el contrato que toda aplicación debe cumplir para integrarse con Maestro Platform, los SDKs oficiales que la plataforma provee para diferentes lenguajes, las validaciones automáticas del CLI, y la estructura de repositorio esperada. Un agente de IA que genere scaffolding de nuevas aplicaciones, que implemente integraciones con la plataforma o que valide el cumplimiento del contrato debe usar este documento como referencia.

---

## Contrato maestro.yaml

El archivo maestro.yaml es un archivo YAML que debe existir en la raíz del repositorio de toda aplicación que se aloje en Maestro Platform. Este archivo es el contrato entre la aplicación y la plataforma. El motor de provisionamiento del Maestro lee este archivo para saber qué infraestructura crear, el CLI de validación lo verifica en cada push para garantizar cumplimiento, y el sistema agéntico lo usa como fuente de verdad sobre la aplicación.

### Campos obligatorios

El campo name es una cadena que identifica la aplicación de forma única dentro de la plataforma. Debe ser alfanumérico en minúsculas con guiones, sin espacios ni caracteres especiales, y con una longitud máxima de sesenta caracteres. Ejemplos válidos son inventory-manager, billing-app, hr-dashboard. Este nombre se usa como parte del subdominio de las instancias y como identificador en el API del Maestro. Una vez registrado, no puede cambiarse porque hacerlo rompería las URLs existentes.

El campo version es una cadena en formato semver estricto, es decir MAJOR punto MINOR punto PATCH, como por ejemplo 1.0.0 o 2.3.1. No se aceptan prefijos como la letra v ni sufijos como beta o rc.

El campo description es una cadena de texto libre que describe el propósito de la aplicación. No tiene límite de longitud pero se recomienda mantenerla entre cincuenta y doscientos caracteres para que se muestre correctamente en el catálogo del portal.

El campo tech_stack es una cadena que identifica la tecnología principal de la aplicación. Los valores reconocidos por el sistema agéntico son node-express, node-fastify, node-nestjs, python-django, python-flask, python-fastapi, php-laravel, go-gin, go-fiber, java-spring, dotnet-aspnet y rust-actix. Si la tecnología no está en la lista, se puede usar un valor libre pero el sistema agéntico no tendrá un especialista preconfigurado para ese stack.

El bloque requires contiene los requisitos de infraestructura. Dentro de requires, el campo database es obligatorio y sus valores válidos son postgres, mysql, mongo o none. El campo frontend es un booleano obligatorio que indica si la aplicación tiene interfaz de usuario propia. El bloque ports es obligatorio y contiene el campo app que especifica el puerto TCP en el que escucha el backend de la aplicación. Si frontend es verdadero, ports también debe contener el campo frontend con el puerto del servidor de frontend.

El bloque health es obligatorio y contiene el campo endpoint que es la ruta HTTP del health check, típicamente /health. El campo interval especifica cada cuánto tiempo el Maestro ejecuta el health check, expresado como un número seguido de la letra s para segundos, y su valor por defecto es treinta segundos. El campo timeout especifica cuánto tiempo espera el Maestro una respuesta antes de considerar el health check como fallido, y su valor por defecto es cinco segundos. El campo retries especifica cuántos health checks fallidos consecutivos se toleran antes de ejecutar un reinicio automático, y su valor por defecto es tres.

El bloque auth es obligatorio y tiene una estructura fija que no debe modificarse. El campo mode debe tener el valor header porque es el único modo soportado. El bloque headers dentro de auth debe contener cuatro campos con sus valores exactos: user_id con valor X-Auth-User-Id, email con valor X-Auth-User-Email, company_id con valor X-Auth-Company-Id, y roles con valor X-Auth-Roles. Aunque esta sección pueda parecer redundante porque los valores son siempre los mismos, su presencia explícita en el contrato sirve como documentación para los desarrolladores y como verificación de que el desarrollador está consciente del mecanismo de autenticación.

El bloque env contiene dos listas. La lista required enumera las variables de entorno que la aplicación necesita obligatoriamente para funcionar. Como mínimo debe incluir DATABASE_URL que contiene la cadena de conexión a la base de datos, MAESTRO_API_URL que contiene la URL del API del Maestro, y MAESTRO_APP_SECRET que contiene un secreto compartido entre la app y el Maestro para firmar comunicaciones internas. La lista optional enumera variables de entorno que la aplicación puede usar si están disponibles pero que no son necesarias para arrancar, como REDIS_URL o SMTP_HOST.

El bloque resources es obligatorio y contiene el campo memory que especifica el máximo de memoria RAM usando el formato de Docker como 256m para doscientos cincuenta y seis megabytes o 1g para un gigabyte. El campo cpu especifica la fracción de core de CPU como una cadena que contiene un número decimal, por ejemplo 0.25 o 1.0. El campo tier es opcional y especifica el tier de recursos con valores posibles micro, standard, professional o enterprise. Si tier no se especifica, se infiere a partir de los valores de memory y cpu.

### Campos opcionales

El campo icon es una cadena con la ruta relativa al archivo de ícono de la aplicación dentro del repositorio. El ícono se usa en el sidebar del portal. Debe ser un archivo SVG o PNG de al menos sesenta y cuatro por sesenta y cuatro píxeles.

El campo config_schema es un bloque YAML que define los parámetros de configuración que cada empresa puede personalizar para su instancia de la aplicación. Cada parámetro tiene un nombre, un tipo que puede ser string, number, boolean o select, un valor por defecto y una descripción. El portal genera automáticamente un formulario de configuración basado en este schema.

El campo hooks define comandos que el motor de provisionamiento ejecuta en momentos específicos del ciclo de vida. El hook post_provision se ejecuta una vez después de crear la instancia por primera vez y es típicamente usado para ejecutar migraciones de base de datos o sembrar datos iniciales. El hook pre_start se ejecuta cada vez que la instancia arranca, antes de que el proceso principal de la app comience. El hook post_stop se ejecuta después de detener la instancia.

---

## Estructura de repositorio esperada

Todo repositorio de aplicación para Maestro Platform debe seguir la siguiente estructura de archivos.

En la raíz del repositorio debe existir el archivo maestro.yaml que es el contrato de integración descrito en la sección anterior.

En la raíz del repositorio debe existir un archivo Dockerfile que define cómo construir la imagen Docker de la aplicación. Este Dockerfile debe incluir una instrucción USER con un usuario no-root y una instrucción EXPOSE con el puerto declarado en maestro.yaml.

En la raíz del repositorio debe existir un archivo docker-compose.dev.yml que permite al desarrollador ejecutar la aplicación localmente con un mock del Maestro. Este archivo crea una base de datos local y simula los headers de autenticación para que el desarrollador pueda trabajar sin necesidad de conectarse a una instancia real del Maestro.

En la raíz del repositorio debe existir un archivo CLAUDE.md que configura el agente especialista de inteligencia artificial para esta aplicación. La especificación de este archivo se encuentra en el documento 07-SISTEMA-AGENTICO.md.

En la raíz del repositorio debe existir un directorio .github que contiene el subdirectorio workflows con el archivo deploy.yml que define el pipeline de CI/CD para la aplicación.

El código fuente de la aplicación se ubica en un directorio src o en la estructura de directorios que sea convencional para el stack tecnológico utilizado.

Si la aplicación usa una base de datos, las migraciones deben ubicarse en un directorio migrations o en la ubicación convencional del stack, como database/migrations para Laravel o prisma/migrations para Prisma.

---

## SDKs oficiales

La plataforma provee SDKs oficiales para los lenguajes más comunes. Cada SDK abstrae la lectura de headers de autenticación, la validación de permisos, el filtrado automático por tenant y la comunicación con el API del Maestro. Usar el SDK no es obligatorio pero es fuertemente recomendado porque implementa correctamente todos los patrones de seguridad descritos en estos documentos.

### SDK para Node.js

El paquete se llama @maestro/sdk-node y se instala desde npm. Provee un middleware para Express y Fastify que intercepta cada request entrante, lee los headers X-Auth, construye un objeto user con los campos id, email, name, companyId, roles y permissions, y lo adjunta al objeto request para que los handlers lo consuman. Si los headers no están presentes, lo que indicaría que el request no pasó por Traefik, el middleware responde con 401. El SDK también provee un helper de base de datos que automáticamente agrega la condición WHERE company_id igual al company_id del usuario en cada consulta, sirviendo como segunda barrera de aislamiento de datos después del aislamiento a nivel de red.

### SDK para Python

El paquete se llama maestro-sdk y se instala desde pip. Provee middleware para Django, Flask y FastAPI. Para Django, provee un middleware class que se agrega a MIDDLEWARE en settings. Para Flask, provee un decorador require_auth que se aplica a cada ruta. Para FastAPI, provee un dependency que se inyecta en cada endpoint. En todos los casos, el resultado es un objeto user accesible desde el contexto del request con los mismos campos que el SDK de Node.js.

### SDK para PHP y Laravel

El paquete se llama maestro/sdk-laravel y se instala desde Composer. Provee un middleware de Laravel que se registra como middleware global o de grupo de rutas. Provee un Guard personalizado para el sistema de autenticación de Laravel, lo que significa que Auth::user() retorna un objeto con los datos del usuario del Maestro. Provee un Scope de Eloquent llamado ForTenant que se aplica automáticamente a todos los modelos que usen el trait TenantAware, filtrando por company_id en cada consulta.

### SDK para Go

El módulo se llama github.com/maestro/sdk-go y se instala con go get. Provee un middleware para net/http estándar y adaptadores para gin y fiber. El middleware extrae los headers, construye un struct User y lo coloca en el context.Context del request para que los handlers lo consuman mediante una función helper.

---

## Validaciones del CLI

El CLI maestro-cli es una herramienta de línea de comandos que se ejecuta en el pipeline de CI/CD de cada aplicación. Su propósito principal es verificar que la aplicación cumple con el contrato de la plataforma antes de permitir el despliegue.

El comando maestro-cli validate ejecuta las siguientes verificaciones en orden.

Verificación de schema: comprueba que el archivo maestro.yaml existe en la raíz del repositorio y que su contenido cumple con el JSON Schema del contrato. Verifica que todos los campos obligatorios están presentes, que los valores están dentro de los rangos permitidos y que los tipos de datos son correctos. Si esta verificación falla, reporta exactamente qué campos faltan o son inválidos.

Verificación de Dockerfile USER: inspecciona el Dockerfile buscando la instrucción USER. Verifica que el usuario especificado no sea root y que no tenga UID cero. Si el Dockerfile usa multi-stage builds, verifica la instrucción USER en la etapa final.

Verificación de health endpoint: confirma que el campo health.endpoint está presente en maestro.yaml y que no está vacío. No puede verificar que el endpoint realmente funciona en este punto porque la app no está corriendo, pero verifica que está declarado.

Verificación de recursos declarados: confirma que los campos resources.memory y resources.cpu están presentes y que sus valores están dentro de los rangos del tier especificado o inferido.

Verificación de secretos en código: ejecuta un scan de detección de secretos sobre todo el repositorio incluyendo el historial de git. Busca patrones que se parezcan a contraseñas, tokens de API, claves privadas, cadenas de conexión a base de datos y otros datos sensibles. Si encuentra una coincidencia, reporta el archivo y la línea donde se encontró.

Verificación de auth headers: confirma que la sección auth en maestro.yaml tiene mode igual a header y que los cuatro headers estándar están declarados con sus nombres correctos.

Verificación de puerto: confirma que el puerto declarado en requires.ports.app coincide con alguna instrucción EXPOSE en el Dockerfile.

Si cualquiera de estas verificaciones falla, el CLI retorna un código de salida no-cero y el pipeline de CI/CD se detiene, bloqueando el despliegue.

El comando maestro-cli new es un generador de scaffolding que crea la estructura completa de una nueva aplicación. Acepta parámetros para el nombre de la app, el stack tecnológico y el tipo de base de datos, y genera todos los archivos necesarios incluyendo maestro.yaml preconfigurado, Dockerfile con buenas prácticas para el stack elegido, docker-compose.dev.yml para desarrollo local, CLAUDE.md con el agente especialista configurado, workflow de GitHub Actions preconfigurado, y código boilerplate con el SDK integrado incluyendo un endpoint de health check funcional.
