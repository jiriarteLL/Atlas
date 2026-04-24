# Especificaciones de UX — Maestro Platform V1

> **Fase:** 02-Planning
> **Agente:** ux-designer
> **Fecha:** 2026-04-16
> **Proyecto:** PRJ-MAESTRO-V1
> **Base visual:** Tailwise React Template v1.0.9 (`Tailwise Bundle/React Version - v1.0.9/`)
> **Idioma único V1:** Español argentino (DEC-014)
> **Accesibilidad V1:** baseline sin WCAG AA formal (DEC-015)

---

## 1. Flujos de Usuario

### 1.1 Flow — Login con usuario y contraseña

```
[ / ] usuario no autenticado
   │
   ▼
[ /login ] pantalla login
   ├─ Email + Password → submit
   │    ├─ credenciales OK → guardar tokens (httpOnly cookies) → redirect a /
   │    ├─ credenciales FAIL → mostrar error inline "Email o contraseña incorrectos"
   │    ├─ usuario disabled → "Cuenta desactivada. Contactá al admin."
   │    └─ rate limit → "Demasiados intentos. Esperá 1 minuto."
   │
   └─ Botón "Continuar con Microsoft" → ver Flow 1.2
```

### 1.2 Flow — Login con Microsoft Entra ID

```
[ /login ] → click "Continuar con Microsoft"
   │
   ▼
Redirect a microsoft.entra / OAuth2 consent
   │
   ▼
Usuario autoriza → Microsoft redirect a /api/auth/microsoft/callback?code=...&state=...
   │
   ▼
Backend valida, crea o vincula user, emite JWT, setea cookies httpOnly
   │
   ▼
Redirect a / (portal)
   │
   └─ Si falla (state inválido / code expirado / consent denegado):
        → /auth/error?reason=... → pantalla "No pudimos autenticarte con Microsoft. [Volver a login]"
```

### 1.3 Flow — Portal home (usuario autenticado)

```
[ / ] usuario autenticado
   │
   ├─ Sidebar:
   │    ├─ Avatar + nombre usuario
   │    ├─ Selector de empresa activa (solo si tiene >1 empresa)
   │    ├─ Lista de apps licenciadas de la empresa activa
   │    │    └─ click app → carga iframe en área principal (ver Flow 1.4)
   │    ├─ Si usuario es platform_admin → sección "Administración" con submenu
   │    │    (empresas, usuarios, aplicaciones, licencias, instancias, audit log)
   │    └─ Logout
   │
   ├─ Área principal:
   │    ├─ Estado inicial: welcome screen
   │    │     "Hola {nombre}, tenés {N} aplicaciones en {empresa}"
   │    │     "Seleccioná una desde la izquierda para comenzar."
   │    └─ App seleccionada: iframe con app huésped
   │
   └─ Header superior:
        ├─ Logo Maestro / nombre empresa activa
        ├─ Indicador de estado de la app cargada (healthy/starting/degraded)
        └─ Menú usuario (perfil, logout)
```

### 1.4 Flow — Cargar una app huésped en iframe

```
Click app en sidebar
   │
   ▼
Portal determina URL: https://<app-slug>-<company-slug>.<MAESTRO_BASE_DOMAIN>
   │
   ▼
Portal consulta /api/admin/instances?app=<id>&company=<id> para estado
   │
   ├─ Status: healthy → inicia carga del iframe
   │    └─ Portal envía postMessage({type:'maestro:auth', token:<jwt_corto_iframe>}) al iframe al cargar
   │
   ├─ Status: suspended / destroyed → mostrar "Esta aplicación está detenida. Contactá al admin."
   │
   └─ Status: starting o si no existe instancia → mostrar pantalla cold start:
        "🔄 La aplicación está iniciando"
        "Tiempo estimado: <15s"
        ├─ Progress bar indeterminada
        ├─ Polling cada 2s a /api/admin/instances/{id} hasta que healthy
        └─ Al healthy → carga iframe.

Si tras 30s sigue sin healthy → mostrar error "No pudimos iniciar la aplicación. [Reintentar] [Contactar soporte]"
```

### 1.5 Flow — Cambio de empresa activa

```
Selector empresa en sidebar → elige otra empresa
   │
   ▼
Portal llama POST /api/auth/switch-company { company_id }
   │
   ▼
Backend valida membresía y emite nuevo JWT con X-Auth-Company-Id actualizado
   │
   ▼
Portal recarga el sidebar con las apps de la nueva empresa
   │
   ▼
Si estaba viendo una app del contexto anterior → descargar iframe, volver a welcome
```

### 1.6 Flow — Admin: gestionar empresas (CRUD)

```
[ /admin/empresas ] (solo platform_admin)
   │
   ├─ Tabla paginada: nombre | slug | subdomain | status | usuarios | apps | acciones
   ├─ Buscador por nombre/slug
   ├─ Filtro por status
   ├─ Botón "Nueva empresa" → modal con form
   │    └─ validación inline; submit POST /api/admin/companies → toast éxito
   └─ Click fila → detalle con tabs: Info / Usuarios / Apps licenciadas / Instancias / Audit
```

### 1.7 Flow — Admin: gestionar instancias

```
[ /admin/instancias ]
   │
   ├─ Tabla: empresa | app | estado (badge color) | versión | última health OK | acciones
   ├─ Filtros: por empresa, por app, por estado
   ├─ Botón "Provisionar" → modal (selector de app + empresa + override resources opcional)
   ├─ Acciones por fila:
   │    ├─ Detener (stop)
   │    ├─ Reiniciar (restart)
   │    ├─ Eliminar (destroy) con confirmación "Esta acción marca la instancia como destruida. Los datos se retienen 90 días."
   │    └─ Ver detalle → drawer con historial de health, lifecycle events, logs (snippet últimos 100)
   └─ Estado vacío: "No hay instancias provisionadas. [Provisionar la primera]"
```

### 1.8 Flow — Admin: audit log viewer

```
[ /admin/audit ]
   │
   ├─ Filtros: usuario (dropdown), empresa, acción, tipo de recurso, rango de fechas
   ├─ Tabla: timestamp | actor | acción | recurso | resultado (data_before vs after) | ip
   ├─ Click fila → expandir JSON diff before/after en monospace
   └─ Export CSV (SHOULD HAVE, RF-202)
```

### 1.9 Flow — Estado de error catastrófico

Cualquier flujo puede derivar en:
- **Token expirado** → redirect /login con toast "Tu sesión expiró, volvé a ingresar."
- **Sin conexión** → banner superior "Sin conexión con el servidor. Reintentando..."
- **Servidor 500** → pantalla de error con request_id y botón "Reintentar" / "Volver".

---

## 2. Sistema de Diseño

Hereda **100% del template Tailwise React** (`Tailwise Bundle/React Version - v1.0.9/`). No se crea custom CSS nuevo; se parametriza el tema por Tailwind config.

### 2.1 Tokens de color (desde Tailwise, confirmar en Fase 03)

| Token | Uso |
|---|---|
| `primary` (indigo/violeta del template) | botones primarios, links activos |
| `secondary` (gris) | botones secundarios |
| `success` (verde) | status healthy, toasts de éxito |
| `warning` (amarillo) | status degraded, advertencias |
| `danger` (rojo) | status destroyed/failed, errores |
| `neutral` | fondos, bordes |

### 2.2 Tipografía

- Sans-serif del template (probablemente Inter o similar).
- Jerarquía: H1 32px, H2 24px, H3 20px, body 14-16px, caption 12px.

### 2.3 Espaciado y grid

- Sistema 4px base.
- Breakpoints: sm 640 / md 768 / lg 1024 / xl 1280 / 2xl 1536 (Tailwind defaults).
- Portal principal: layout de 2 columnas desktop (sidebar 280px + contenido fluid); tablet drawer colapsable; mobile menu hamburger.

### 2.4 Componentes base (del template)

Reutilizar:
- `Button` (variants: primary, secondary, danger, ghost)
- `Input`, `Select`, `Checkbox`, `Radio`
- `Table` (con paginación cursor-based; se adapta)
- `Modal`, `Drawer`, `Dialog de confirmación`
- `Toast` (notifications)
- `Badge` (status indicators)
- `Avatar`
- `Dropdown Menu`
- `Tabs`
- `Skeleton loaders`
- `EmptyState`

Nuevos componentes custom (se definen en Fase 03):
- `AppIframe`: wrapper del iframe con manejo de postMessage, loading, error states.
- `CompanySwitcher`: dropdown avanzado con búsqueda si el user tiene >5 empresas.
- `ColdStartScreen`: animación + polling.
- `StatusBadge`: estado de instancia con color semántico.
- `HealthSparkline`: mini gráfico de health history últimos 24h.
- `AuditDiffViewer`: JSON diff before/after.

---

## 3. Wireframes — Pantallas clave (descripción textual)

### 3.1 `/login`

```
┌─────────────────────────────────────────────────┐
│                                                 │
│               [ Logo Maestro ]                  │
│                                                 │
│            Bienvenido a Maestro                 │
│                                                 │
│     ┌─────────────────────────────────────┐     │
│     │  Email                              │     │
│     │  [_______________________________]  │     │
│     │                                     │     │
│     │  Contraseña                         │     │
│     │  [_______________________________]  │     │
│     │                                     │     │
│     │  [  Iniciar sesión  ]               │     │
│     │                                     │     │
│     │  ────────  o  ────────              │     │
│     │                                     │     │
│     │  [  🅼 Continuar con Microsoft  ]   │     │
│     └─────────────────────────────────────┘     │
│                                                 │
│                                                 │
└─────────────────────────────────────────────────┘
```

### 3.2 Portal home (usuario con apps)

```
┌─────────────────────────────────────────────────────────────────────────┐
│ [Maestro]   LLyAsoc ▾              [Estado: OK]           👤 Alan ▾     │ ← header
├──────────┬──────────────────────────────────────────────────────────────┤
│ 👤 Alan   │                                                             │
│ LLyAsoc▾ │                                                              │
│──────────│                                                              │
│ 📱 Apps   │                                                             │
│  • App 1 │                 ┌───────────────────────────┐                │
│  • App 2 │                 │                           │                │
│  • App 3 │                 │  Bienvenido, Alan         │                │
│  • App 4 │                 │                           │                │
│──────────│                 │  Tenés 7 aplicaciones     │                │
│ ⚙️  Admin │                 │  disponibles en LLyAsoc.  │                │
│  • Emp.  │                 │                           │                │
│  • Users │                 │  Seleccioná una del menú  │                │
│  • Apps  │                 │  para comenzar.           │                │
│  • Licns │                 │                           │                │
│  • Insts │                 └───────────────────────────┘                │
│  • Audit │                                                              │
│──────────│                                                              │
│ ⬇ Logout │                                                              │
└──────────┴──────────────────────────────────────────────────────────────┘
```

### 3.3 Portal con app en iframe

```
┌─────────────────────────────────────────────────────────────────────────┐
│ [Maestro]   LLyAsoc ▾              [App1: OK]           👤 Alan ▾       │
├──────────┬──────────────────────────────────────────────────────────────┤
│ 👤 Alan   │  [App1]                                            🗘 ↗      │
│...sidebar│  ┌──────────────────────────────────────────────────────┐   │
│          │  │                                                      │   │
│          │  │          (iframe con la app huésped)                 │   │
│          │  │                                                      │   │
│          │  │                                                      │   │
│          │  │                                                      │   │
│          │  └──────────────────────────────────────────────────────┘   │
└──────────┴──────────────────────────────────────────────────────────────┘
```

### 3.4 Cold start screen

```
                    ┌──────────────────────────────────┐
                    │                                  │
                    │         🔄                        │
                    │                                  │
                    │   Iniciando App 3...             │
                    │                                  │
                    │   Tiempo estimado: 12s           │
                    │                                  │
                    │   [▰▰▰▰▰▱▱▱▱▱]                  │
                    │                                  │
                    └──────────────────────────────────┘
```

### 3.5 Admin — Instancias (tabla)

```
┌──────────────────────────────────────────────────────────────────────────────┐
│ Instancias                                              [+ Provisionar]      │
│                                                                              │
│ 🔍 [________________]  Empresa: [LLyAsoc ▾]  Estado: [Todas ▾]              │
│                                                                              │
│ ┌────────┬──────────┬────────┬───────────┬────────────┬──────────────────┐  │
│ │ Emp.   │ App      │ Estado │ Versión   │ Última OK  │ Acciones         │  │
│ ├────────┼──────────┼────────┼───────────┼────────────┼──────────────────┤  │
│ │LLyAsoc │ contab.  │[🟢 OK] │ 1.2.3     │ hace 5s    │ ⏸ 🔄 🗑 📋         │  │
│ │LLyAsoc │ rrhh     │[🟡 dgd]│ 0.9.1     │ hace 45s   │ ⏸ 🔄 🗑 📋         │  │
│ │LLyAsoc │ legales  │[🔴 off]│ 2.0.0     │ hace 1h    │ ▶ 🔄 🗑 📋         │  │
│ └────────┴──────────┴────────┴───────────┴────────────┴──────────────────┘  │
│                                                                              │
│                                                   ← Anterior  1  Siguiente → │
└──────────────────────────────────────────────────────────────────────────────┘
```

---

## 4. Accesibilidad

**WON'T HAVE V1 (DEC-015)** — no hay cumplimiento formal WCAG AA.

Baseline aplicado por defecto (del template Tailwise + buenas prácticas):
- HTML semántico (`<button>`, `<nav>`, `<main>`, headings jerárquicos).
- `alt` en imágenes.
- Contraste razonable de texto sobre fondo (heredado del template).
- Focus visible en interactivos (default Tailwind `focus:ring`).
- `<label>` ligado a inputs.

**NO se implementa V1**:
- Skip links, navegación por teclado exhaustiva en tablas, aria-live regions, screen reader testing, pruebas con axe-core, contraste verificado tool.

Documentado como deuda técnica para V2 si mercado objetivo lo exige.

---

## 5. Responsive

Breakpoints (Tailwind default):
- `sm` (640px): menú hamburger, sidebar como drawer.
- `md` (768px): sidebar fija colapsable.
- `lg` (1024px): sidebar siempre visible, layout 2 columnas.
- `xl` (1280px+): más padding y ancho máximo para tablas.

Iframes de apps huésped:
- Responsive por defecto: `width: 100%; height: 100%;` en el área main.
- La app huésped debe ser responsive por su cuenta (responsabilidad del dev de la app; parte del contrato informal).

Mobile support:
- Portal funciona en 375px (iPhone SE).
- Admin panels no están optimizados para mobile (SHOULD HAVE, no crítico); se puede usar tablet/desktop para tareas admin.

---

## 6. Estados por pantalla

Cada pantalla debe manejar explícitamente:

| Estado | UX |
|---|---|
| **Loading** | Skeleton del layout esperado (no spinners para pantallas con datos conocidos; sí spinners en acciones tipo "provisionar") |
| **Empty** | Mensaje + CTA (ej: "No hay empresas cargadas. [Crear la primera]") |
| **Error** | Mensaje claro + botón de retry + opción de ver request_id para soporte |
| **Success** | Toast top-right "✓ Empresa creada" con auto-dismiss 4s |
| **Partial** | Cargas parciales cuando es relevante (ej: tabla con paginación) |

---

## 7. Protocolo `postMessage` portal ↔ iframe

El portal transfiere autenticación al iframe de la app huésped:

### 7.1 Del portal al iframe

```js
iframe.contentWindow.postMessage({
  type: 'maestro:auth',
  version: 1,
  token: '<jwt de corta duración, scope de la app>',
  context: { user_id, company_id, app_id, base_domain }
}, APP_ORIGIN);
```

Se envía al evento `iframe.onload` y ante refresh de token.

### 7.2 Del iframe al portal

```js
window.parent.postMessage({
  type: 'maestro:ready' | 'maestro:navigate' | 'maestro:token-refresh-request',
  version: 1,
  payload: { ... }
}, MAESTRO_ORIGIN);
```

- `maestro:ready` → app lista, portal oculta cold start.
- `maestro:navigate` → app informa navegación interna (opcional, para deep links).
- `maestro:token-refresh-request` → app pide token renovado (si su contexto detecta 401).

### 7.3 Validación

Ambos lados verifican `event.origin` estrictamente. Se documenta para devs de apps huésped en `docs/CONVENCIONES_PLATAFORMA.md`.

---

## 8. Internacionalización

**Solo español (DEC-014).** Strings hardcoded en componentes (formato `'Iniciar sesión'` no `t('login')`).

Convención: strings del UI viven cerca del componente o en archivos `<Componente>.strings.ts` con constantes exportadas. Esto facilita una migración futura a i18next sin re-auditar todo el código.

---

## 9. Coherencia con otros artefactos

| Pantalla | RF | Endpoint | Entidad |
|---|---|---|---|
| /login | RF-001 | POST /api/auth/login | users |
| /login btn Microsoft | RF-002 | GET /api/auth/microsoft/redirect | users + oauth_* |
| Portal sidebar | RF-050, RF-055 | GET /api/portal/my-apps | application_user + instances |
| Portal iframe | RF-051, RF-053, RF-054 | instances.status | instances |
| Company switcher | RF-052 | POST /api/auth/switch-company | company_user |
| Admin empresas | RF-010 | /api/admin/companies/* | companies |
| Admin usuarios | RF-011 | /api/admin/users/* | users + company_user |
| Admin apps | RF-012 | /api/admin/applications/* | applications |
| Admin licencias | RF-014 | /api/admin/applications/{}/licenses | application_company |
| Admin instancias | RF-030–RF-034 | /api/admin/instances/* | instances + history |
| Audit viewer | RF-021 | /api/admin/audit-log | audit_log |
| Error/loading/empty states | (transversal) | (varios) | (varios) |
