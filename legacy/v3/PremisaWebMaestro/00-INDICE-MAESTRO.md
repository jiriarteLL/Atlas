# Maestro Platform — Índice Maestro de Arquitectura

> ⚠️ **DEPRECADO** — Documento del framework v3 / contrato `maestro.platform/v1`.
> Conservado como referencia historica. NO aplicar en proyectos nuevos.
>
> **Version vigente:** `PremisaWebMaestro/00-INDICE-MAESTRO.md` (constitucion del Maestro v4, redactada en Fase 3 del cleanup v4). Mientras tanto, ver `framework-agentico/agents/presets/maestro-platform/PRESET.md`.
> **Razon de la deprecacion:** ver `framework-agentico/CHANGELOG.md` v4.0.

---

## Qué es este conjunto de documentos

Este conjunto de archivos markdown constituye la especificación arquitectónica completa de Maestro Platform. Están redactados íntegramente en lenguaje natural para que un agente de inteligencia artificial pueda interpretarlos sin ambigüedad y tomar decisiones de implementación alineadas con la visión, las premisas y los límites aquí definidos.

Cada archivo es autónomo en su dominio pero interdependiente con los demás. Un agente que reciba estos documentos debe leerlos todos antes de generar código, tomar decisiones de diseño o proponer alternativas. Ningún archivo individual contiene la verdad completa; la arquitectura emerge de la lectura conjunta.

## Orden de lectura obligatorio

El agente debe leer los archivos en el siguiente orden porque cada uno construye sobre los conceptos del anterior:

El primer archivo que debe leerse es este mismo índice, el archivo 00-INDICE-MAESTRO.md, porque establece el contexto general, la visión del producto y las reglas de interpretación que aplican a todos los demás documentos.

El segundo archivo es 01-PREMISAS-Y-NO-NEGOCIABLES.md. Este es el documento más importante de todo el conjunto. Contiene los axiomas y los límites duros del sistema. Cualquier decisión técnica que contradiga lo establecido aquí es inválida, sin excepciones. El agente debe internalizar este archivo como su constitución antes de proceder con cualquier otro.

El tercer archivo es 02-MODELO-DE-DATOS.md. Define todas las entidades, sus atributos, las relaciones entre ellas, las reglas de integridad y las restricciones de negocio. Un agente no puede generar código de base de datos, APIs ni lógica de negocio sin haber procesado este archivo.

El cuarto archivo es 03-AUTENTICACION-Y-AUTORIZACION.md. Describe el sistema de identidad centralizado, el flujo completo de autenticación, la estructura de tokens, el mecanismo de ForwardAuth y los niveles de autorización. Este archivo es crítico porque la autenticación es la capa más sensible de toda la plataforma.

El quinto archivo es 04-INFRAESTRUCTURA-DOCKER.md. Detalla la topología de redes Docker, el ciclo de vida de las instancias, los mecanismos de aislamiento, los límites de recursos, las instancias dormidas y la estrategia de escalado progresivo.

El sexto archivo es 05-PORTAL-Y-RENDERIZADO.md. Explica cómo el portal React renderiza las aplicaciones dentro de iframes, el protocolo de comunicación postMessage, la seguridad del iframe, el manejo de estados de error y los principios de experiencia de usuario.

El séptimo archivo es 06-SDK-Y-CONTRATO.md. Especifica el contrato maestro.yaml que toda aplicación debe cumplir, los SDKs por lenguaje, las validaciones del CLI y la estructura de repositorios esperada para cada aplicación.

El octavo archivo es 07-SISTEMA-AGENTICO.md. Define la jerarquía de agentes de inteligencia artificial, el agente orquestador, los agentes especialistas por tecnología, el flujo de creación de nuevas aplicaciones y las reglas que todo agente debe heredar de la plataforma.

El noveno archivo es 08-CICD-Y-GOBERNANZA.md. Describe los pipelines de integración continua, las fases de validación, la estructura de repositorios, las protecciones del código del Maestro y el flujo de despliegue de nuevas versiones.

El décimo archivo es 09-SEGURIDAD.md. Presenta la estrategia de defensa en profundidad con todas las capas de seguridad, las configuraciones de headers, las políticas de secretos, los escaneos de vulnerabilidades y las reglas de auditoría.

El undécimo archivo es 10-OBSERVABILIDAD.md. Cubre el stack de monitoreo, las métricas clave con sus umbrales, el sistema de alertas, los dashboards y la estrategia de logging centralizado.

El duodécimo y último archivo es 11-PLAN-DE-IMPLEMENTACION.md. Establece las fases de construcción ordenadas cronológicamente, con sus dependencias, entregables y criterios de aceptación.

## Visión del producto

Maestro Platform es una plataforma multi-tenant de clase empresarial cuyo propósito es alojar, orquestar y gobernar múltiples aplicaciones dockerizadas bajo un portal web unificado con autenticación centralizada. La plataforma resuelve el problema de fragmentación que enfrentan las organizaciones que operan múltiples herramientas internas: cada herramienta tiene su propio login, su propia gestión de usuarios, su propia infraestructura y su propia deuda técnica de seguridad.

Con Maestro, un usuario inicia sesión una única vez y accede a todas las aplicaciones que su empresa tiene licenciadas. Los desarrolladores publican aplicaciones dockerizadas siguiendo un contrato estándar, y la plataforma se encarga de todo lo demás: provisionamiento de infraestructura, aislamiento de datos, autenticación, monitoreo y gestión del ciclo de vida.

La metáfora más precisa es pensar en Maestro como un sistema operativo para aplicaciones internas. Así como un sistema operativo gestiona procesos, memoria, seguridad y la interfaz de usuario mientras las aplicaciones se enfocan en su propósito específico, Maestro gestiona contenedores, bases de datos, identidad y el portal web mientras cada aplicación alojada se enfoca exclusivamente en su lógica de negocio.

## Contexto técnico existente

La plataforma Maestro ya existe en una versión inicial con las siguientes características que deben preservarse y extenderse:

El backend está desarrollado en Laravel. Este es un hecho inmutable; no se migrará a otro framework. Las extensiones y mejoras deben construirse sobre Laravel.

El frontend está desarrollado con React y Tailwind CSS. Igualmente inmutable. El portal se extiende con estos mismos frameworks.

La aplicación está dockerizada y corre en un VPS en Azure. La infraestructura base es Docker sobre una máquina virtual en la nube de Microsoft Azure.

La autenticación ya soporta usuario y contraseña además de Microsoft Authentication. Estos dos métodos de autenticación deben preservarse y extenderse con capacidades OAuth2 server para emitir tokens a las aplicaciones alojadas.

La estructura de permisos existente ya contempla que muchas empresas tienen muchos usuarios, que muchos usuarios pertenecen a muchas empresas, que muchas empresas tienen muchas aplicaciones, y que muchas aplicaciones tienen muchos usuarios. Estas cuatro relaciones many-to-many son el corazón del modelo de datos y no pueden simplificarse.

## Reglas de interpretación para el agente

Cuando el agente encuentre la palabra "debe" o "obligatorio" en cualquier documento, significa que no hay alternativa. El agente no puede proponer una solución diferente ni omitir ese requisito.

Cuando el agente encuentre la palabra "nunca" o "jamás" o "prohibido", significa que esa acción está completamente vedada. El agente no puede encontrar excepciones ni justificaciones para violar esa restricción.

Cuando el agente encuentre la frase "no negociable", significa que ese requisito tiene la máxima prioridad. Si entra en conflicto con una preferencia del desarrollador, con una limitación de tiempo o con cualquier otra presión, el no negociable prevalece siempre.

Cuando el agente encuentre la palabra "recomendado" o "preferible", significa que es la opción por defecto pero puede modificarse con justificación técnica documentada.

Cuando el agente encuentre la palabra "configurable" o "parametrizable", significa que el valor puede ser ajustado por el administrador de la plataforma sin modificar código.

Cuando el agente necesite tomar una decisión que no está cubierta explícitamente por estos documentos, debe aplicar los siguientes principios en orden de prioridad: primero, seguridad y aislamiento de datos entre tenants; segundo, experiencia de usuario fluida; tercero, simplicidad operativa; cuarto, rendimiento; quinto, elegancia del código.

## Stakeholders del sistema

Las personas y roles que interactúan con la plataforma son cinco grupos distintos con necesidades diferentes.

Las empresas, también llamadas tenants, son las organizaciones clientes que contratan licencias de aplicaciones. Su necesidad principal es tener acceso unificado a sus herramientas con seguridad, control de costos y visibilidad sobre el uso que sus empleados hacen de cada aplicación.

Los usuarios finales son los empleados de las empresas que usan las aplicaciones día a día. Su necesidad principal es una experiencia fluida con un solo login, transiciones rápidas entre aplicaciones y una interfaz consistente que no los obligue a aprender un sistema de navegación diferente para cada herramienta.

Los desarrolladores de aplicaciones son los equipos que crean las aplicaciones que se alojan en la plataforma. Su necesidad principal es un SDK claro, un contrato estándar bien documentado, un pipeline de CI/CD automatizado y un agente de IA que los asista en el cumplimiento de las reglas de la plataforma.

Los administradores de Maestro son el equipo que opera la plataforma. Su necesidad principal es tener observabilidad completa sobre todas las instancias, gobernanza sobre licencias y accesos, y herramientas para escalar la plataforma sin tiempo de inactividad.

La dirección o C-Level son los tomadores de decisiones. Su necesidad principal es ver el retorno de inversión, el cumplimiento de normativas y reportes ejecutivos sobre el uso y la salud de la plataforma.
