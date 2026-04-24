# Sistema Agéntico con Claude

## Propósito de este documento

Este documento define la jerarquía de agentes de inteligencia artificial que asisten en el desarrollo de aplicaciones para Maestro Platform. Describe el agente orquestador, los agentes especialistas por tecnología, el flujo de creación de nuevas aplicaciones asistido por IA, y las reglas que todo agente debe heredar de la plataforma para garantizar que el código generado cumple con los estándares de seguridad, aislamiento y calidad.

---

## Arquitectura del sistema agéntico

El sistema agéntico opera en dos niveles jerárquicos.

### Nivel uno: Agente Orquestador

El Agente Orquestador es el agente de nivel superior que conoce todas las reglas de la plataforma, todos los no negociables, el contrato maestro.yaml completo y las mejores prácticas transversales que aplican a cualquier tecnología. Este agente es responsable de cuatro funciones principales.

La primera función es el scaffolding de proyectos nuevos. Cuando un desarrollador invoca el comando maestro-cli new, el Agente Orquestador genera la estructura completa del repositorio incluyendo todos los archivos de configuración, el código boilerplate con el SDK integrado y el archivo CLAUDE.md del agente especialista. El Orquestador toma decisiones sobre la estructura basándose en el stack tecnológico elegido y las mejores prácticas de la industria para ese stack.

La segunda función es la generación de agentes especialistas. El Orquestador crea el archivo CLAUDE.md que configura el agente especialista para cada nueva aplicación. Este archivo hereda automáticamente los parámetros de plataforma que son inmutables y los combina con las mejores prácticas específicas del stack tecnológico elegido.

La tercera función es la validación de compliance. El Orquestador puede revisar un repositorio existente y verificar que cumple con todas las reglas de la plataforma, incluyendo aspectos que el CLI no puede verificar estáticamente, como patrones de código que podrían violar el aislamiento de datos o prácticas de seguridad deficientes.

La cuarta función es la resolución de conflictos. Cuando un desarrollador intenta implementar algo que contradice las reglas de la plataforma, el Orquestador explica por qué esa implementación es inválida y propone alternativas que cumplen con el contrato.

### Nivel dos: Agentes Especialistas

Los Agentes Especialistas son agentes configurados por el archivo CLAUDE.md que existe en cada repositorio de aplicación. Cada especialista conoce las reglas de la plataforma que heredó del Orquestador más las mejores prácticas específicas de su stack tecnológico. El especialista es el agente con el que los desarrolladores interactúan día a día mientras escriben código.

Un agente especialista para Node.js con Express conoce las reglas de la plataforma más las convenciones de Express, la estructura de proyectos Node.js, las mejores prácticas de Prisma u otro ORM, los patrones de testing con Jest, y las convenciones de logging estructurado. Un agente especialista para Python con Django conoce las mismas reglas de plataforma más las convenciones de Django, la estructura de apps y settings, las mejores prácticas del ORM de Django, y los patrones de testing con pytest.

---

## Archivo CLAUDE.md: Especificación

El archivo CLAUDE.md es un documento markdown que configura un agente Claude para trabajar con una aplicación específica dentro de Maestro Platform. Tiene tres secciones obligatorias y una sección opcional.

### Sección uno: Parámetros heredados de plataforma

Esta sección contiene reglas que el Agente Orquestador inserta automáticamente y que el desarrollador no debe modificar. Son la proyección de los no negociables de la plataforma al contexto de la aplicación individual. El contenido de esta sección es el siguiente.

El agente nunca debe generar código que implemente autenticación propia. No debe crear formularios de login, validar contraseñas, emitir tokens ni gestionar sesiones de usuario. Toda identidad proviene de los headers X-Auth que Traefik inyecta.

El agente siempre debe generar código que lea la identidad del usuario exclusivamente de los headers X-Auth-User-Id, X-Auth-User-Email, X-Auth-Company-Id y X-Auth-Roles. Debe usar el SDK de la plataforma correspondiente al stack tecnológico para abstraer esta lectura.

El agente siempre debe generar código que filtre los datos por company_id. Toda consulta a la base de datos que retorne datos específicos de un tenant debe incluir la condición de filtrado por el company_id recibido en el header. El SDK provee mecanismos automáticos para esto, pero si el desarrollador escribe consultas manuales, el agente debe asegurar que la condición está presente.

El agente debe generar Dockerfiles que incluyan una instrucción USER con un usuario no-root. Si genera un Dockerfile desde cero, debe crear un usuario dedicado para la aplicación con un UID numérico mayor a mil.

El agente debe generar código que exponga un endpoint de health check en la ruta declarada en maestro.yaml. Este endpoint debe responder con código HTTP 200 y un cuerpo JSON que contenga el campo status con valor ok. Adicionalmente, el health check debería verificar la conectividad con la base de datos para reportar un estado significativo.

El agente nunca debe escribir secretos, contraseñas, tokens ni claves en el código fuente. Toda configuración sensible debe leerse de variables de entorno. Si el desarrollador pide hardcodear una credencial, el agente debe negarse y explicar que las credenciales se gestionan a través de variables de entorno inyectadas por el Maestro.

El agente debe generar código que produzca logs en formato JSON estructurado. Cada entrada de log debe incluir como mínimo un timestamp, un nivel de severidad, un mensaje y el company_id del contexto actual. Los logs estructurados son necesarios para la integración con el sistema centralizado de logging de la plataforma.

### Sección dos: Parámetros del stack tecnológico

Esta sección la genera el Orquestador basándose en el campo tech_stack del contrato maestro.yaml. Contiene las mejores prácticas específicas del stack elegido. El desarrollador puede ajustar esta sección según las convenciones de su equipo, siempre y cuando no contradiga los parámetros de plataforma.

Para una aplicación Node.js con Express, esta sección típicamente incluye la versión de Node.js recomendada que es la LTS actual, el framework web que es Express con la versión estable, el ORM recomendado que puede ser Prisma o Knex o TypeORM, la estructura de directorios recomendada con carpetas para controllers, services, middleware, models y utils, el framework de testing recomendado que es Jest con Supertest para tests de integración, el linter recomendado que es ESLint con la configuración estándar más Prettier para formateo, y las convenciones de manejo de errores como middleware centralizado de error handling con clases de error personalizadas.

Para una aplicación Python con Django, esta sección típicamente incluye la versión de Python, el framework que es Django con su versión, la estructura de apps de Django, la estrategia de migraciones, las convenciones de testing con pytest-django, y las prácticas de seguridad específicas de Django como el uso de settings segregados por entorno.

Para una aplicación PHP con Laravel, esta sección típicamente incluye la versión de PHP y Laravel, la estructura de directorios de Laravel, las convenciones de Eloquent con el trait TenantAware del SDK, las prácticas de testing con PHPUnit y Laravel Dusk, y las configuraciones de seguridad de Laravel.

### Sección tres: Patrones obligatorios

Esta sección define patrones de código que son obligatorios para la aplicación. Combina patrones de plataforma con patrones del stack. El desarrollador puede agregar patrones adicionales pero no puede remover los existentes.

Los patrones típicos incluyen la inyección de dependencias para facilitar el testing, el manejo de errores centralizado con un middleware que captura todas las excepciones y las convierte en respuestas HTTP apropiadas, la separación de lógica de negocio en servicios para mantener los controllers delgados, el uso de transacciones de base de datos para operaciones que modifican múltiples tablas, y la implementación del patrón repository si el stack lo soporta para abstraer el acceso a datos.

### Sección cuatro: Contexto adicional (opcional)

Esta sección la escribe el equipo de desarrollo para dar al agente especialista contexto específico del dominio de la aplicación. Por ejemplo, si la aplicación es un sistema de inventario, esta sección explicaría los conceptos del dominio como productos, almacenes, movimientos de stock y órdenes de compra. Si la aplicación interactúa con APIs externas, esta sección documentaría esas integraciones.

---

## Flujo de creación de nueva aplicación

Cuando un desarrollador quiere crear una nueva aplicación para Maestro Platform, el flujo es el siguiente.

Paso uno: el desarrollador ejecuta el comando maestro-cli new con los parámetros de nombre, stack tecnológico y tipo de base de datos. Por ejemplo, maestro-cli new seguido de la opción name con valor expense-tracker, la opción stack con valor node-express y la opción database con valor postgres.

Paso dos: el CLI invoca al Agente Orquestador, ya sea un servicio de IA o un template engine, que genera la estructura completa del repositorio. Esto incluye un archivo maestro.yaml preconfigurado con todos los campos obligatorios ya completados, un Dockerfile optimizado para el stack elegido con multi-stage build y usuario no-root, un archivo docker-compose.dev.yml que levanta una base de datos local y simula los headers de autenticación del Maestro para desarrollo local, un archivo CLAUDE.md con las tres secciones obligatorias ya escritas, un archivo de workflow de GitHub Actions para el pipeline de CI/CD, código boilerplate que incluye el SDK del stack correspondiente ya integrado, un endpoint de health check funcionando, un endpoint de ejemplo que demuestra cómo leer los headers de autenticación y filtrar por company_id, y la configuración del linter y formatter para el stack.

Paso tres: el desarrollador inicializa el repositorio de git, hace el primer commit y lo sube a GitHub bajo la organización de la plataforma.

Paso cuatro: a partir de este punto, el desarrollador trabaja con el agente especialista configurado en CLAUDE.md usando Claude Code u otra herramienta que lea el archivo CLAUDE.md. El especialista le asiste en escribir código que cumple automáticamente con todas las reglas de la plataforma.

Paso cinco: en cada push al repositorio, el pipeline de CI/CD ejecuta maestro-cli validate para verificar compliance, ejecuta los tests de la aplicación, construye la imagen Docker, la escanea por vulnerabilidades y la publica en el registry.

Paso seis: cuando la imagen está publicada, el pipeline notifica al Maestro a través del endpoint de registro de aplicaciones para que la nueva versión esté disponible para despliegue.

---

## Reglas para agentes que lean estos documentos

Si un agente de inteligencia artificial recibe estos documentos de arquitectura para implementar o asistir en el desarrollo de Maestro Platform o de aplicaciones para la plataforma, las siguientes reglas aplican.

El agente debe tratar los no negociables como restricciones absolutas. No puede proponer alternativas que los violen ni encontrar justificaciones para saltárselos. Si un desarrollador pide algo que viola un no negociable, el agente debe negarse explicando cuál no negociable se violaría y proponiendo una alternativa que lo cumpla.

El agente debe priorizar la seguridad sobre la conveniencia. Si existe una forma más fácil de implementar algo pero que compromete el aislamiento de datos, la validación de tokens o el cifrado de comunicaciones, el agente debe elegir la forma más segura aunque sea más compleja.

El agente debe generar código que sea autoexplicativo. Los comentarios deben explicar el porqué, no el qué. El código debe seguir las convenciones del stack tecnológico correspondiente.

El agente debe verificar mentalmente cada pieza de código que genere contra los siguientes criterios: primero, si este código filtra datos por company_id en toda consulta que toque datos de tenant; segundo, si este código lee la identidad exclusivamente de los headers X-Auth y no de otra fuente; tercero, si este código maneja errores apropiadamente sin exponer información interna en las respuestas; cuarto, si este código produce logs estructurados que ayuden a diagnosticar problemas; quinto, si este código no contiene secretos hardcodeados.
