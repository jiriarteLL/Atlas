# Portal y Renderizado de Apps

> **Versión:** v4 (framework agéntico v4 / contrato `maestro.platform/v2`)
> **Última revisión:** 2026-05-07
> **Estado:** vigente
> **Reemplaza a:** `legacy/v3/PremisaWebMaestro/05-PORTAL-Y-RENDERIZADO.md` (modelo v1 con shell + iframes + postMessage).

---

## Propósito de este documento

Este documento describe el portal de la **Web Maestro** v4: cómo renderiza el catálogo de apps disponibles para los admins, cómo gestiona el cambio de contexto entre empresas, cómo el click en una app abre la URL del deployment correspondiente en una pestaña nueva, y por qué se eliminaron iframes y postMessage del modelo v1. Un agente que implemente el frontend del portal o que necesite integrar visualmente el Maestro debe usar este documento como referencia.

---

## Cambio fundamental respecto a v1

En v1 el portal era un shell React que:

- Renderizaba las apps huésped en **iframes**.
- Transferia el token JWT del usuario al iframe vía **postMessage**.
- Inyectaba **headers `X-Auth-*`** en el reverse proxy.
- Manejaba la sesión del usuario centralmente.

En v4 el portal:

- **NO usa iframes**.
- **NO transfiere identidad** al click.
- **Abre la URL del deployment en `target="_blank"`** (pestaña nueva).
- Cada app huésped pide su login propio en la pestaña abierta.

El portal del Maestro v4 es exclusivamente la **interfaz administrativa** del Maestro: gestiona empresas, applications, deployments, api_keys, webhook_secrets, audit log. No es la interfaz para los usuarios finales de las apps huésped.

---

## Audiencia del portal

Solo **admins de la Web Maestro** se loguean al portal. Los usuarios finales de las apps huésped:

- Reciben directamente la URL pública de su deployment (ej: `https://inventario-acme.miplataforma.com`).
- Hacen login en esa URL con sus credenciales propias (gestionadas por la app).
- Nunca pasan por el portal del Maestro.

Si la empresa quiere ofrecer a sus usuarios un "selector de apps", lo hace **dentro de cada app** (cada app puede mostrar un menú con links a las otras apps de la empresa, si la empresa lo configura). El portal del Maestro **NO** es el portal de los usuarios finales.

---

## Stack del portal

El portal del Maestro es **stack-agnóstico** dentro de los límites generales del framework:

- **Frontend recomendado**: React + TypeScript + Tailwise (consistencia visual con el resto del ecosistema).
- **Frontend alternativo**: Vue 3, HTML+Tailwind directo, o cualquier framework que el equipo prefiera, siempre que se containerice y respete las convenciones (`docs/CONVENCIONES_PLATAFORMA.md`).
- La premisa 4 (Agnosticismo tecnológico) aplica también al Maestro mismo.

Los agentes con responsabilidades de UX/UI (`ux-designer`, `frontend-developer`) deben **presentar Tailwise como recomendación** y **respetar la decisión final del PO** (ver `framework-agentico/core/RULES.md` sección `plantilla_base`).

---

## Funcionalidades del portal

### Login

- Formulario en `/login` (path declarado en el `maestro.yaml` del propio Maestro).
- POST `/api/v2/auth/login` con email + password.
- Cookie `maestro_session` `HttpOnly + Secure + SameSite=Lax` o JWT en cookie/header (según implementación).
- Audit log: `login.success` o `login.failure`.
- Bloqueo tras 5 fallos consecutivos durante 15 min.
- Detalle en `03-AUTENTICACION-Y-AUTORIZACION.md`.

### Dashboard ejecutivo

Vista inicial post-login con resumen:
- Total de empresas (`companies` activas).
- Total de applications registradas.
- Total de deployments por estado (healthy / degraded / suspended).
- Hooks success rate de las últimas 24h.
- Branding fetch success rate de las últimas 24h.
- Backup status.

Solo lectura. Filtros por rango de tiempo.

### Gestión de empresas (`/companies`)

- Lista paginada con filtros (`status`, búsqueda por `slug` o `name`).
- Acciones por empresa (según permisos del admin):
  - Ver detalle (deployments asociados, audit log filtrado).
  - Crear nueva (`companies.create`).
  - Editar (`companies.update`).
  - Suspender/activar (`companies.suspend`).
  - Soft-delete (`companies.delete`).
- Cada acción genera audit log.

### Gestión de applications (`/applications`)

- Lista paginada de apps registradas.
- Vista detalle: maestro.yaml registrado, hash, versiones históricas, deployments asociados.
- Auto-registro: las apps llegan via `POST /api/v2/apps/register` desde su CI; los admins pueden ver pero no editar las metadata (la app es la fuente de verdad).
- Acción `applications.deprecate` para marcar una app como deprecada (no se permiten nuevos deployments, los existentes siguen).

### Gestión de deployments (`/deployments`)

- Lista paginada de deployments con filtros (`status`, empresa, application).
- Vista detalle: estado actual, URL pública, métricas recientes, health check history, branding cache, hooks log de las últimas 24h.
- Acciones (según permisos):
  - Crear (`deployments.create`): selecciona application + company; el motor de provisioning hace el resto.
  - Suspender (`deployments.suspend`).
  - Destruir (`deployments.destroy`): soft-destroy (BD preservada 90 días). Pide confirmación.
  - Purgar (`deployments.purge`): solo si `destroyed_at + 90 days <= NOW()`. Pide doble confirmación + `superadmin` requerido.
  - Restaurar (`deployments.restore`): si está `destroyed` y dentro de 90 días, levanta de nuevo el contenedor + BD desde backup.
  - Rotar `MAESTRO_API_KEY` (`api_keys.rotate`).
  - Rotar `MAESTRO_WEBHOOK_SECRET` (`webhook_secrets.rotate`).
  - Forzar refresh de branding (`branding.refresh`).
- **Click en la URL pública del deployment**: genera link `<a target="_blank" href="<app_url>">` que abre la app en pestaña nueva. **NO transfiere token**.

### Branding viewer

- Vista que muestra cómo se ve el deployment desde el portal: `company_name`, `logo_url`, `primary_color`, `favicon_url`.
- Estado del fetch: ok / unauthorized / timeout / server_error.
- Acción "Refresh now" (audit log).

### Audit log viewer

- Vista con filtros por `actor_user_id`, `action`, `resource_type`, `resource_id`, rango de fechas.
- Solo lectura (audit log es inmutable).
- Permite exportar a CSV/JSON para auditorías externas.
- Permiso requerido: `audit_log.read`.

### Hooks log viewer

- Vista con filtros por deployment, event_type, status (success / failed / retry / abandoned), rango de fechas.
- Permite reintentar manualmente un hook fallido (`hooks.retry`, audit log).

### Gestión de admins

- Lista de admins (`admin_users`).
- Crear admin con rol asignado (`admins.create`, requiere permisos del admin actor).
- Cambiar password propia (cualquier admin puede cambiar su propia password).
- Cambiar password de otro (`admins.password_reset`, requiere `superadmin`).
- Asignar/revocar roles (`admins.roles.grant` / `admins.roles.revoke`).
- Desactivar / reactivar (`admins.deactivate` / `admins.activate`).
- Ver historial de logins (audit log filtrado).

### Settings del Maestro

- Vista de configuraciones globales:
  - Frecuencia de health checks (default 30s).
  - Frecuencia de fetch de branding (default 6h).
  - Política de retención de backups (default 30 días, ampliable).
  - Política de purge de deployments (default 90 días post-destroy).
- Cambios audit logged.

---

## Click en una app: flujo detallado

> Esta sección detalla el flujo del No-negociable tres.

```
1. Admin del Maestro está en la vista detalle de un deployment.
2. Ve el campo "URL pública": https://inventario-acme.miplataforma.com
3. Hace click en el botón "Abrir app" (que es un <a target="_blank" href="<app_url>">).
4. El navegador abre la URL en una pestaña nueva.
5. La app huésped responde su página de login (auth.login_path, default /login).
6. El admin (o el usuario final, según contexto) ingresa email + password.
7. La app valida contra su tabla `users` propia.
8. La app emite su propio token (cookie HttpOnly o JWT propio).
9. La pestaña nueva opera completamente independiente del Maestro.
```

**Lo que el Maestro NO hace en este flujo**:
- NO inyecta token al click.
- NO modifica headers HTTP del request.
- NO intercepta requests subsiguientes.
- NO sabe si el usuario logró loguearse (la app no le reporta eso al Maestro).

**Lo que el Maestro SÍ hace**:
- Audit log: `deployment.opened` con `actor_user_id` (admin), `resource_id` (deployment), `actor_ip`, `user_agent`.
- (Opcional) Rate limiting: si un admin abre el mismo deployment muchas veces en poco tiempo, podría flagear como sospechoso.

### Mensaje informativo previo (recomendado)

Antes de abrir el link, el portal **PUEDE** mostrar un mensaje:

> "Vas a abrir la app **<nombre>** de la empresa **<empresa>**. La app te pedirá login propio. ¿Continuar?"

Esto reduce la confusión en admins acostumbrados al modelo v1 (donde el portal manejaba la sesión).

---

## Por qué NO iframes en v4

Razones técnicas que llevaron al cambio:

1. **Aislamiento de seguridad**: el modelo v1 con iframes + postMessage requería gestionar dos contextos de origen (portal + app) y mensajes entre ellos. Esto introducía complejidad y vectores de XSS.
2. **Independencia operativa**: con iframes, si el portal fallaba, todas las apps quedaban inaccesibles. Con `target="_blank"`, las apps siguen funcionando aunque el portal esté caído.
3. **Performance**: iframes anidados degradan UX en navegadores modernos.
4. **Compliance**: GDPR y otras regulaciones se simplifican cuando los datos personales de los usuarios finales **nunca pasan por el portal del Maestro**.
5. **Single-tenant físico**: cada deployment ya es un dominio separado (`<app>-<empresa>.<base>`). Tiene sentido tratarlo como una aplicación independiente, no como un componente del portal.

### Trade-off aceptado

Pérdida: el usuario final (no admin) pierde la experiencia de "un solo portal con todas las apps".

Mitigación: cada empresa puede construir su propio "selector de apps" dentro de una de sus apps (por ejemplo, la primera que loguean). El Maestro provee la lista de apps licenciadas vía endpoint `GET /api/v2/portal/my-apps` (autenticado con la api key del deployment), pero la decisión de cómo mostrarla queda en cada app.

---

## Cold start del deployment

Cuando un admin destruyó (`destroyed`) un deployment y luego lo restaura:
- El motor de provisioning levanta el contenedor desde la imagen registrada.
- Restaura la BD desde backup (si aplica).
- Espera health check.
- Tiempo total objetivo: ≤ 60 segundos (medible vía métrica).

Mientras el deployment está `provisioning` o `starting`, el portal muestra un estado visible ("Levantando..."). El click al botón "Abrir app" durante este estado abre una página intermedia del Maestro (`/portal/loading?deployment=<id>`) que polea el estado y redirige a la app cuando alcanza `healthy`.

Cold start no aplica a deployments `healthy` (siempre están corriendo en v4; no hay deployments dormidos en v4 — los deployments destruidos se restauran explícitamente, no automáticamente).

---

## Manejo de estados de error

El portal muestra estados visibles cuando un deployment NO está disponible:

| Estado | UX |
|---|---|
| `provisioning` / `starting` | Spinner + tiempo estimado + botón "Cancelar" |
| `degraded` | Banner amarillo: "App con problemas, último health check fallido. Reintentando" |
| `suspended` | Banner rojo: "App suspendida. Contactar admin" + razón |
| `destroyed` (dentro de 90 días) | "App destruida el <fecha>. Restaurable hasta <fecha + 90 días>" + botón "Restaurar" |
| `purged` | "App purgada. Datos no recuperables." |
| Branding `unauthorized` | Marcar deployment con icono de alerta; admin debe verificar `MAESTRO_API_KEY` |

Cada error logueado en audit log si genera acción del admin.

---

## Accesibilidad y responsive

- WCAG 2.1 nivel AA mínimo.
- Tema claro y oscuro.
- Responsive: desktop (1280+), tablet (768+), mobile (320+).
- Navegación por teclado completa.
- Labels en formularios.
- Contraste suficiente.

---

## I18n

- Idioma default: español argentino (alineado con el equipo de operaciones del Maestro).
- Soporte adicional: inglés (recomendado para futuros operadores externos).
- Implementación con `i18next` o equivalente del stack.

---

## Referencias normativas

- `01-PREMISAS-Y-NO-NEGOCIABLES.md` — premisas 1, 3, 4; no-negociable 3 (target="_blank").
- `02-MODELO-DE-DATOS.md` — tablas que el portal lee/escribe.
- `03-AUTENTICACION-Y-AUTORIZACION.md` — login + RBAC del portal.
- `04-INFRAESTRUCTURA-DOCKER.md` — provisioning (lo que el portal dispara via `POST /api/v2/deployments`).
- `09-SEGURIDAD.md` — CSP, HttpOnly cookies, CSRF protection.
- `framework-agentico/core/RULES.md` sección `plantilla_base` — Tailwise preferido pero no obligatorio.

---

## Historial de revisiones

| Versión | Fecha | Cambio |
|---|---|---|
| 4.0.0 | 2026-05-07 | Versión inicial v4. Rediseña el portal como interfaz puramente administrativa. Elimina iframes, postMessage, transferencia de tokens. Click en app → `<a target="_blank">`. Reemplaza al v1 (legacy en `legacy/v3/PremisaWebMaestro/05-PORTAL-Y-RENDERIZADO.md`). |
