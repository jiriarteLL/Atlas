# Modelo de Datos y Relaciones

## Propósito de este documento

Este documento define todas las entidades del sistema, sus atributos, las relaciones entre ellas, las reglas de integridad referencial y las restricciones de negocio que gobiernan cómo los datos se crean, modifican y eliminan. Un agente de IA que genere código de migraciones de base de datos, modelos de Eloquent, endpoints de API o lógica de negocio debe usar este documento como fuente de verdad para la estructura de datos.

La base de datos del Maestro utiliza PostgreSQL. Las bases de datos de las instancias de aplicación pueden ser PostgreSQL, MySQL o MongoDB según lo declare cada app en su contrato, pero la base de datos central del Maestro es PostgreSQL sin excepciones.

---

## Entidades principales

### Entidad companies

La entidad companies representa a las organizaciones clientes que utilizan la plataforma. Cada company es un tenant aislado con sus propios usuarios, aplicaciones licenciadas e instancias.

Los atributos de companies son los siguientes. El campo id es un UUID versión 4 generado automáticamente, es la clave primaria y nunca cambia después de la creación. El campo name es una cadena de texto de hasta doscientos cincuenta y cinco caracteres que almacena el nombre comercial de la empresa, es obligatorio y no necesita ser único porque dos empresas legales diferentes podrían tener el mismo nombre comercial. El campo slug es una cadena de texto alfanumérica en minúsculas con guiones, de hasta cien caracteres, que se usa para construir subdominios y URLs, es obligatorio, debe ser único en toda la tabla y no puede modificarse después de la creación porque hacerlo rompería todas las URLs de las instancias de esa empresa. El campo plan es una cadena de texto que indica el plan comercial contratado, los valores válidos son free, starter, professional y enterprise, es obligatorio y su valor por defecto es free. El campo logo_url es una cadena de texto opcional que contiene la URL del logotipo de la empresa, se usa en el portal para personalizar la experiencia del usuario. El campo is_active es un booleano que indica si la empresa está activa, su valor por defecto es verdadero, cuando se pone en falso todas las instancias de esa empresa pasan a estado detenido y sus usuarios pierden acceso. El campo settings es un campo JSON que almacena configuraciones específicas de la empresa como zona horaria preferida, idioma, políticas de contraseña personalizadas y configuraciones de notificaciones. El campo created_at es un timestamp con zona horaria que se establece automáticamente al crear el registro. El campo updated_at es un timestamp con zona horaria que se actualiza automáticamente en cada modificación. El campo deleted_at es un timestamp nullable que implementa soft delete; cuando tiene valor, la empresa se considera eliminada lógicamente pero sus datos persisten.

### Entidad users

La entidad users representa a las personas individuales que utilizan la plataforma. Un usuario puede pertenecer a múltiples empresas y tener roles diferentes en cada una.

Los atributos de users son los siguientes. El campo id es un UUID versión 4, clave primaria. El campo name es una cadena de hasta doscientos cincuenta y cinco caracteres con el nombre completo del usuario, obligatorio. El campo email es una cadena de hasta doscientos cincuenta y cinco caracteres con el correo electrónico, obligatorio y único en toda la tabla; es el identificador principal para login. El campo password es una cadena que almacena el hash bcrypt de la contraseña, es nullable porque un usuario que solo usa Microsoft Auth puede no tener contraseña local. El campo microsoft_id es una cadena nullable que almacena el identificador único del usuario en Microsoft Entra ID, se usa para vincular la cuenta local con la autenticación de Microsoft; es único cuando tiene valor. El campo avatar_url es una cadena nullable con la URL de la foto de perfil. El campo is_active es un booleano con valor por defecto verdadero; cuando es falso, el usuario no puede iniciar sesión en ninguna empresa. El campo email_verified_at es un timestamp nullable que indica cuándo el usuario verificó su correo electrónico. El campo last_login_at es un timestamp nullable que se actualiza cada vez que el usuario inicia sesión exitosamente. El campo last_login_ip es una cadena nullable que almacena la dirección IP del último login exitoso. Los campos created_at, updated_at y deleted_at siguen el mismo patrón que en companies.

### Entidad applications

La entidad applications representa las aplicaciones disponibles en el catálogo de la plataforma. Esta entidad describe la aplicación como producto, no sus instancias desplegadas.

Los atributos de applications son los siguientes. El campo id es un UUID versión 4, clave primaria. El campo name es una cadena de hasta doscientos cincuenta y cinco caracteres con el nombre visible de la aplicación, obligatorio. El campo slug es una cadena alfanumérica en minúsculas con guiones, obligatorio, único y no modificable después de la creación; se usa para construir las URLs de las instancias. El campo description es un texto largo que describe el propósito y funcionalidades de la aplicación. El campo docker_image es una cadena obligatoria que contiene la referencia completa a la imagen Docker en el registry, por ejemplo ghcr.io/org/inventory-app. El campo repo_url es una cadena obligatoria que contiene la URL del repositorio de GitHub de la aplicación. El campo has_frontend es un booleano obligatorio que indica si la aplicación tiene interfaz de usuario propia; si es falso, el portal genera una UI genérica basada en el schema de la API. El campo health_endpoint es una cadena obligatoria que contiene la ruta del endpoint de health check, usualmente /health. El campo config_schema es un campo JSON nullable que define el schema de configuración personalizable por tenant, permitiendo que cada empresa ajuste parámetros de la app según sus necesidades. El campo icon_url es una cadena nullable con la URL del ícono de la aplicación para el sidebar del portal. El campo current_version es una cadena que contiene la versión actual desplegada en formato semver. El campo is_published es un booleano que indica si la aplicación es visible en el catálogo para licenciamiento. Los campos created_at, updated_at y deleted_at siguen el patrón estándar.

### Entidad app_instances

La entidad app_instances representa las instancias vivas de aplicaciones desplegadas para tenants específicos. Cada registro es la materialización de una combinación empresa más aplicación con su propia infraestructura aislada.

Los atributos de app_instances son los siguientes. El campo id es un UUID versión 4, clave primaria. El campo application_id es un UUID que referencia a applications, obligatorio, es clave foránea. El campo company_id es un UUID que referencia a companies, obligatorio, es clave foránea. La combinación de application_id y company_id debe ser única; no puede haber dos instancias de la misma aplicación para la misma empresa. El campo subdomain es una cadena generada automáticamente que resulta de concatenar el slug de la aplicación con el slug de la empresa, por ejemplo inventario-empresax; se usa para construir la URL completa de la instancia. El campo container_id es una cadena nullable que almacena el ID del contenedor Docker mientras está en ejecución. El campo status es una cadena obligatoria con los valores posibles PROVISIONING, STARTING, HEALTHY, RUNNING, DEGRADED, SUSPENDED, STOPPING, STOPPED, DESTROYED y FAILED. El campo port es un entero nullable que almacena el puerto interno asignado al contenedor. El campo db_name es una cadena que almacena el nombre de la base de datos creada para esta instancia. El campo db_credentials es un campo texto cifrado que almacena las credenciales de base de datos en formato JSON con los campos host, port, username, password y database_name. El campo env_vars es un campo texto cifrado que almacena variables de entorno adicionales en formato JSON. El campo deployed_version es una cadena que indica qué versión de la imagen Docker está desplegada actualmente. El campo last_health_check_at es un timestamp nullable con la fecha del último health check exitoso. El campo failed_health_checks es un entero con valor por defecto cero que cuenta los health checks fallidos consecutivos. Los campos created_at, updated_at y deleted_at siguen el patrón estándar.

---

## Tablas de relación

### Tabla company_user

Esta tabla materializa la relación muchos a muchos entre empresas y usuarios. Un usuario puede pertenecer a múltiples empresas y una empresa puede tener múltiples usuarios.

Los atributos de company_user son los siguientes. El campo id es un UUID versión 4, clave primaria. El campo company_id es un UUID que referencia a companies, obligatorio. El campo user_id es un UUID que referencia a users, obligatorio. La combinación de company_id y user_id debe ser única; un usuario no puede tener dos registros en la misma empresa. El campo role es una cadena obligatoria con los valores posibles owner, admin y member. Cada empresa debe tener al menos un owner. Un owner puede hacer todo incluyendo eliminar la empresa. Un admin puede gestionar usuarios y licencias pero no eliminar la empresa. Un member solo puede usar las aplicaciones licenciadas. El campo invited_at es un timestamp que indica cuándo se invitó al usuario a la empresa. El campo accepted_at es un timestamp nullable que indica cuándo el usuario aceptó la invitación; si es nulo, la invitación está pendiente y el usuario no puede acceder a los recursos de esa empresa. Los campos created_at y updated_at siguen el patrón estándar.

### Tabla company_application

Esta tabla materializa la relación muchos a muchos entre empresas y aplicaciones. Representa las licencias: qué aplicaciones tiene contratadas cada empresa.

Los atributos de company_application son los siguientes. El campo id es un UUID versión 4, clave primaria. El campo company_id es un UUID que referencia a companies, obligatorio. El campo application_id es un UUID que referencia a applications, obligatorio. La combinación de company_id y application_id debe ser única. El campo license_status es una cadena obligatoria con los valores posibles active, expired, suspended y cancelled. Solo con status active la empresa puede usar la aplicación. El campo licensed_at es un timestamp que indica cuándo se activó la licencia. El campo expires_at es un timestamp nullable que indica cuándo expira la licencia; nulo significa licencia perpetua o sin fecha de expiración definida. El campo plan_tier es una cadena que indica el tier de recursos asignado a esta licencia, con valores posibles micro, standard, professional y enterprise. El campo custom_config es un campo JSON nullable que almacena configuración específica de esta empresa para esta aplicación, basada en el config_schema definido en la aplicación. Los campos created_at y updated_at siguen el patrón estándar.

### Tabla application_user

Esta tabla materializa la relación muchos a muchos entre aplicaciones y usuarios, pero siempre en el contexto de una empresa. Un usuario no tiene acceso a una aplicación de forma abstracta; tiene acceso a una aplicación dentro de una empresa específica.

Los atributos de application_user son los siguientes. El campo id es un UUID versión 4, clave primaria. El campo application_id es un UUID que referencia a applications, obligatorio. El campo user_id es un UUID que referencia a users, obligatorio. El campo company_id es un UUID que referencia a companies, obligatorio. La combinación de application_id, user_id y company_id debe ser única. El campo role es una cadena que indica el rol del usuario dentro de la aplicación, con valores posibles como app_admin, editor, viewer u otros que la aplicación defina en su config_schema. El campo permissions es un campo JSON nullable que almacena permisos granulares específicos de la aplicación. El campo last_accessed_at es un timestamp nullable que se actualiza cada vez que el usuario accede a esta aplicación. Los campos created_at y updated_at siguen el patrón estándar.

---

## Tablas de soporte

### Tabla audit_logs

Esta tabla almacena el log de auditoría inmutable. No acepta operaciones UPDATE ni DELETE.

Los atributos de audit_logs son los siguientes. El campo id es un UUID versión 4, clave primaria. El campo user_id es un UUID nullable que referencia al usuario que realizó la acción; es nullable porque algunas acciones son del sistema, no de un usuario. El campo action es una cadena obligatoria que describe la acción realizada, como company.created, user.invited, license.activated, instance.provisioned, instance.destroyed, config.changed. El campo entity_type es una cadena que indica el tipo de entidad afectada, como Company, User, Application, AppInstance. El campo entity_id es un UUID que identifica la entidad afectada. El campo data_before es un campo JSON nullable que contiene el estado de la entidad antes del cambio. El campo data_after es un campo JSON nullable que contiene el estado de la entidad después del cambio. El campo ip_address es una cadena que almacena la IP desde donde se realizó la acción. El campo user_agent es una cadena que almacena el user agent del navegador o cliente. El campo created_at es un timestamp que se establece automáticamente y nunca se modifica.

### Tabla oauth_tokens

Esta tabla es gestionada por Laravel Passport y almacena los tokens OAuth2 emitidos. No se documenta su estructura aquí porque es propiedad de Passport, pero es importante saber que existe y que es la fuente de verdad para las sesiones activas.

### Tabla app_versions

Esta tabla registra el historial de versiones de cada aplicación.

Los atributos de app_versions son los siguientes. El campo id es un UUID versión 4. El campo application_id es un UUID que referencia a applications. El campo version es una cadena con la versión en formato semver. El campo docker_image_tag es la referencia completa a la imagen Docker con su tag específico. El campo changelog es un texto que describe los cambios de esta versión. El campo released_at es un timestamp. El campo released_by es un UUID nullable que referencia al usuario que publicó la versión.

---

## Reglas de integridad y negocio

### Regla de cascada de desactivación

Cuando una empresa se desactiva, es decir cuando su campo is_active cambia a falso, todas sus instancias activas deben transicionar al estado STOPPED. Los usuarios de esa empresa pierden la capacidad de acceder a cualquier recurso de esa empresa, pero sus cuentas de usuario siguen existiendo y pueden seguir accediendo a otras empresas a las que pertenezcan. Los datos de las instancias no se eliminan; los volúmenes Docker y las bases de datos persisten para poder reactivar la empresa en el futuro.

### Regla de licencia expirada

Cuando el campo expires_at de un registro en company_application alcanza la fecha actual, el sistema debe cambiar automáticamente el campo license_status a expired. La instancia correspondiente, si existe, debe transicionar al estado SUSPENDED. En estado suspendido, los datos de la instancia persisten durante noventa días. Después de noventa días, la instancia es elegible para purgado, pero el purgado no es automático; requiere acción administrativa explícita.

### Regla de usuario multi-empresa

Cuando un usuario pertenece a múltiples empresas, el portal debe mostrar un selector de empresa activa. Al cambiar de empresa, todo el contexto cambia: las aplicaciones visibles en el sidebar, los permisos del usuario y la empresa incluida en el token JWT. El cambio de empresa activa genera un nuevo token JWT con el company_id actualizado.

### Regla de eliminación lógica

Ninguna entidad se elimina físicamente de la base de datos. Todas las entidades principales usan soft delete a través del campo deleted_at. Cuando deleted_at tiene un valor, la entidad se considera eliminada y debe ser excluida de todas las consultas por defecto. Los modelos de Eloquent deben usar el trait SoftDeletes y todas las consultas deben incluir implícitamente la condición deleted_at IS NULL a menos que explícitamente se solicite incluir registros eliminados.

### Regla de unicidad de instancia

No puede existir más de una instancia activa de la misma aplicación para la misma empresa. La combinación application_id más company_id es única en la tabla app_instances excluyendo registros con status DESTROYED. Si una empresa quiere una nueva instancia de una aplicación que ya tuvo, primero debe destruirse la instancia anterior.

### Regla de pertenencia transitiva para acceso a aplicaciones

Un usuario solo puede tener un registro en application_user si cumple dos condiciones simultáneas: primero, el usuario debe tener un registro activo y aceptado en company_user para la empresa indicada; segundo, la empresa debe tener un registro con license_status active en company_application para la aplicación indicada. Si cualquiera de estas condiciones deja de cumplirse, el acceso del usuario a la aplicación se revoca automáticamente.

### Regla de cifrado de campos sensibles

Los campos db_credentials y env_vars en app_instances deben estar cifrados en reposo utilizando el cifrado simétrico de Laravel con la clave de aplicación. Estos campos nunca deben exponerse en respuestas de API ni en logs. Cuando se necesitan para provisionar una instancia, se descifran en memoria, se inyectan como variables de entorno en el contenedor y se descartan de la memoria.
