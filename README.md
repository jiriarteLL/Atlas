# Plataforma Maestro v2 — Guía de Desarrollo de Aplicaciones Huésped (Framework Agéntico v4)

> Este repositorio es el punto de partida para desarrollar aplicaciones compatibles con la plataforma **Web Maestro v2**. Cada aplicación se desarrolla en un **fork independiente** de este repo. Cada deployment de una app sirve a **una sola empresa** (single-tenant físico). Todas las apps comparten el sistema de diseño **Tailwise** para una experiencia visual unificada.
>
> **Contrato de integración:** `maestro.platform/v2`
> **Framework agéntico:** v4
> **Última actualización:** 2026-09-22

> 📘 **¿Vas a subir una app a Test o Preproducción?** Este README cubre **cómo se desarrolla** una app huésped. El **cómo se sube** está en **[`MANUAL_METODOLOGICO.md`](MANUAL_METODOLOGICO.md)**: flujo operativo del panel de Dokploy (`http://10.100.1.124:3000/`), convención de nombres y tags, puertos del VPS compartido, despliegue por API, evaluación contra el Maestro y reparto de responsabilidades entre desarrollador y evaluador humano.

---

## ¿Qué cambió respecto a v3?

| Area | v3 (legacy) | v4 (vigente) |
|---|---|---|
| Tenancy | Multi-tenant lógico con `company_id` por fila | **Single-tenant físico**: un contenedor = una empresa |
| Auth | Headers `X-Auth-*` inyectados por Traefik | **Login propio de la app** (tablas users + roles + permissions + tokens propios) |
| Tabla `users` | **Prohibida** | **Obligatoria** |
| Maestro → App (usuario) | Reverse proxy + iframe | Abre URL en `target="_blank"` |
| Maestro → App (server) | `X-Maestro-Webhook-Secret` para hooks | `X-Maestro-Webhook-Secret` + `X-Maestro-Api-Key` (para `/maestro/branding`) |
| Fases del framework | 7 (00 → 06) | 8 (00 → 07; **nueva 05-seeding**) |
| Superadmin | N/A | `admin@llyasoc.com` creado por seeder idempotente |

Detalle completo en `framework-agentico/CHANGELOG.md` y `framework-agentico/migration/v3-to-v4.md`.

---

## Índice

1. [Modelo de Trabajo](#1-modelo-de-trabajo)
2. [Estructura del Fork](#2-estructura-del-fork)
3. [Tailwise Bundle: Sistema de Diseño Unificado](#3-tailwise-bundle-sistema-de-diseño-unificado)
4. [Docker: Arquitectura por App](#4-docker-arquitectura-por-app)
5. [Convención de Puertos](#5-convención-de-puertos)
6. [Redes Docker y Aislamiento](#6-redes-docker-y-aislamiento)
7. [Seguridad](#7-seguridad)
8. [Autenticación: Login Propio de la App](#8-autenticación-login-propio-de-la-app)
9. [Endpoint /maestro/branding](#9-endpoint-maestrobranding)
10. [Seeding del Superadmin](#10-seeding-del-superadmin)
11. [docker-compose.yml: Template Base](#11-docker-composeyml-template-base)
12. [Dockerfile: Requisitos Obligatorios](#12-dockerfile-requisitos-obligatorios)
13. [maestro.yaml: Contrato de Integración v2](#13-maestroyaml-contrato-de-integración-v2)
14. [Variables de Entorno (.env)](#14-variables-de-entorno-env)
15. [Flujo de Desarrollo](#15-flujo-de-desarrollo)
16. [Despliegue: Del Fork a Producción](#16-despliegue-del-fork-a-producción)
17. [Checklist Pre-PR](#17-checklist-pre-pr)
18. [Troubleshooting](#18-troubleshooting)
19. [Documentos de Referencia](#19-documentos-de-referencia)

> **Fuera de este README:** el despliegue a Test y Preproducción vive en **[`MANUAL_METODOLOGICO.md`](MANUAL_METODOLOGICO.md)**.

---

## 1. Modelo de Trabajo

```
REPO PRINCIPAL (tu-org/plataforma-maestro)
│
├── Fork A: app-inventario     ← Equipo de inventario
├── Fork B: app-facturacion    ← Equipo de facturación
├── Fork C: app-rrhh           ← Equipo de RRHH
└── Fork D: app-crm            ← Equipo de CRM

Cada fork es autónomo:
- Tiene su propio docker-compose.yml
- Tiene su propia base de datos
- Tiene su propio sistema de login (users + roles + permissions)
- Se levanta sin depender del Maestro ni de otros forks
- En producción, cada deployment sirve a UNA empresa
```

### Reglas de gobernanza

- Cada fork trabaja sobre una rama `develop` propia.
- Para proponer cambios al repo principal, se crea un PR desde `fork/develop` hacia `principal/app-{nombre}`.
- El repo principal tiene una rama por cada app: `app-inventario`, `app-facturacion`, etc.
- Solo el administrador de la organización puede aprobar y mergear PRs al repo principal.
- Nunca se hace PR directo a `main` del repo principal.

---

## 2. Estructura del Fork

```
mi-fork/
├── CLAUDE.md                           [EXISTENTE]  Instrucciones para Claude Code
├── README.md                           [EXISTENTE]  Este documento
├── maestro.yaml                        [CREAR]      Contrato de integración v2
├── Dockerfile                          [CREAR]      Build de la app
├── docker-compose.yml                  [CREAR]      Stack completo local
├── .dockerignore                       [CREAR]      Exclusiones del build
├── .env.example                        [EXISTENTE]  Variables de entorno de referencia
├── .env                                [CREAR]      Copia de .env.example con tus valores (gitignored)
│
├── app/                                [CREAR]      Código fuente de la app
│   ├── src/
│   │   ├── auth/                       [CREAR]      Login propio: middleware + endpoints + servicios
│   │   ├── routes/                     [CREAR]      Endpoints de negocio + /health + /maestro/branding
│   │   ├── services/                   [CREAR]      Lógica de negocio
│   │   ├── seeders/
│   │   │   └── superadmin.*            [CREAR]      Seeder idempotente del superadmin (fase 05)
│   │   └── health.*                    [CREAR]      Health check endpoint (sin auth)
│   ├── migrations/                     [CREAR]      Migraciones de BD (incluye users, roles, permissions)
│   ├── resources/                      [CREAR]      Assets del frontend
│   │   ├── css/                        [COPIAR]     Desde Tailwise Bundle
│   │   ├── js/                         [COPIAR]     Desde Tailwise Bundle
│   │   └── images/                     [COPIAR]     Desde Tailwise Bundle
│   └── tests/
│       └── integration/
│           ├── auth.test.*             [CREAR]      Tests de login propio (obligatorio)
│           ├── branding.test.*         [CREAR]      Tests del endpoint /maestro/branding
│           └── seeder.test.*           [CREAR]      Tests de idempotencia del seeder
│
│
├── framework-agentico/                 [EXISTENTE]  Framework de fases de desarrollo (v4)
├── Tailwise Bundle/                    [EXISTENTE]  Sistema de diseño (leer, copiar, no modificar)
│   ├── HTML Version - v1.0.1/         Componentes HTML + Tailwind
│   ├── Laravel Version - v1.0.3/      Componentes Blade + Tailwind
│   ├── React Version - v1.0.9/        Componentes React + TypeScript + Tailwind
│   └── Tailwise Vue - v1.0.1/         Componentes Vue 3 + TypeScript + Tailwind
│
└── .github/
    └── workflows/
        └── ci.yml                      [CREAR]      Pipeline de validación
```

---

## 3. Tailwise Bundle: Sistema de Diseño Unificado

### Por qué es preferido

Todas las aplicaciones de la plataforma Maestro usan el mismo lenguaje visual para una experiencia coherente. Tailwise es el sistema de diseño compartido.

**Regla: usar Tailwise es el camino preferido. Solo se permite omitirlo cuando hay un impedimento técnico documentado** (por ejemplo: la app usa Flutter Web, o es una app sin frontend propio).

### Versiones disponibles

| Tu stack de frontend | Versión de Tailwise a usar | Ruta en el repo |
|---|---|---|
| HTML/JS vanilla | HTML Version v1.0.1 | `Tailwise Bundle/HTML Version - v1.0.1/Source/` |
| Laravel Blade | Laravel Version v1.0.3 | `Tailwise Bundle/Laravel Version - v1.0.3/Source/` |
| React / Next.js | React Version v1.0.9 | `Tailwise Bundle/React Version - v1.0.9/Source/` |
| Vue 3 / Nuxt | Tailwise Vue v1.0.1 | `Tailwise Bundle/Tailwise Vue - v1.0.1/Source/` |

### Cómo integrar Tailwise

**Paso 1: Identificar tu stack y copiar los assets base**

```bash
# Ejemplo para React
cp -r "Tailwise Bundle/React Version - v1.0.9/Source/src/assets/css" app/resources/css/
cp -r "Tailwise Bundle/React Version - v1.0.9/Source/src/assets/images" app/resources/images/
cp "Tailwise Bundle/React Version - v1.0.9/Source/tailwind.config.js" app/
cp "Tailwise Bundle/React Version - v1.0.9/Source/postcss.config.cjs" app/

# Ejemplo para Laravel
cp -r "Tailwise Bundle/Laravel Version - v1.0.3/Source/resources/css" app/resources/css/
cp -r "Tailwise Bundle/Laravel Version - v1.0.3/Source/resources/images" app/resources/images/
cp "Tailwise Bundle/Laravel Version - v1.0.3/Source/tailwind.config.js" app/
cp "Tailwise Bundle/Laravel Version - v1.0.3/Source/postcss.config.js" app/
```

**Paso 2: Copiar componentes base que necesites**

No copies todo. Copia solo los que tu app usa (botones, forms, tablas, modales, etc.).

**Paso 3: Páginas de referencia útiles para apps v4**

Tailwise incluye páginas completas que podés usar como plantillas:

| Funcionalidad de tu app | Página de referencia en Tailwise |
|---|---|
| **Login propio** (obligatorio v4) | `dagger-login`, `echo-login`, etc. (los `*-login.html` y equivalentes en cada stack) |
| Dashboard / resumen | `dashboard-overview-1` a `dashboard-overview-8` |
| Listado de items | `product-list`, `seller-list`, `transaction-list`, `users` |
| **Gestión de usuarios** (v4) | `users`, `add-user`, `profile-overview` |
| **Gestión de roles/permisos** (v4) | adaptar `settings` con tabs |
| Configuración | `settings` (tabs internos) |
| Recuperación de password | adaptar `dagger-register` o flujo custom |

**Paso 4: Elegir un theme**

Themes: `dagger`, `echo`, `exort`, `havoc`, `hook`, `hurricane`, `ravage`, `raze`, `razor`, `shuriken`, `viper`. Mantenelo consistente en toda tu app.

```bash
cp "Tailwise Bundle/React Version - v1.0.9/Source/src/assets/css/themes/echo.css" app/resources/css/themes/
cp -r "Tailwise Bundle/React Version - v1.0.9/Source/src/themes/Echo" app/src/themes/Echo/
```

### Cuándo se permite NO usar Tailwise

Documentar en `maestro.yaml` el motivo:

```yaml
ui:
  tailwise: false
  reason: "App sin frontend propio, solo API REST"
```

Si `ui.tailwise` no está declarado o es `true`, se asume que la app usa Tailwise.

### Premisa para agentes UX/UI

La plataforma Web Maestro es **stack-agnóstica**: cualquier stack containerizable con Docker es válido para una aplicación huésped. Tailwise es la opción **preferida** del template pero NO obligatoria.

Los agentes con responsabilidades UX/UI (`ux-designer`, `frontend-developer`, `fullstack-developer`, `mobile-developer`) deben:

- Presentar Tailwise como recomendación inicial cuando hay frontend.
- Respetar la decisión del PO si elige otro stack (ej: Flutter Web, Svelte, framework propietario).
- Documentar la decisión en `maestro.yaml` (`ui.tailwise: false`, `ui.reason`).
- NO sesgar la propuesta hacia Tailwise si el PO no lo pide explícitamente.

Esta premisa está formalizada en `framework-agentico/core/RULES.md` sección `plantilla_base`.

---

## 4. Docker: Arquitectura por App

Cada app es un stack Docker autocontenido con mínimo 2 servicios (app + db) y máximo 4 (app + db + redis + opcionales):

```
┌─────────────────────────────────────────────────┐
│         FORK: app-inventario                     │
│         Red: app-inventario-net                  │
│                                                   │
│  ┌──────────────┐  ┌──────────────────────────┐  │
│  │  app          │  │  db                       │  │
│  │  :3100        │  │  PostgreSQL/MySQL/Mongo   │  │
│  │  (login propio│──│  :5432 (interno)          │  │
│  │   + branding) │  │                           │  │
│  └──────┬───────┘  └──────────────────────────┘  │
│         │                                         │
│         │           ┌──────────────────────────┐  │
│         └───────────│  redis (opcional)         │  │
│                     │  :6379 (interno)          │  │
│                     └──────────────────────────┘  │
└─────────────────────────────────────────────────┘
```

### Principios

1. **Aislamiento total**: cada app vive en su propia red Docker. Los contenedores de una app no ven los de otra.
2. **Sin puertos compartidos**: cada app usa un rango de puertos único (ver §5).
3. **Base de datos propia**: cada app tiene su propio contenedor de BD con volumen persistente.
4. **Sin estado compartido**: las apps no comparten Redis, BD, ni volúmenes entre sí.
5. **Sin mock de auth en v4**: la app maneja su propio login (a diferencia de v3).

---

## 5. Convención de Puertos

> ⚠️ **Esta sección es sólo para `localhost`** — la máquina del desarrollador. Los puertos del **VPS compartido** (`10.100.1.124`), donde conviven Test y Preproducción, se asignan con **otra** regla: ver [`MANUAL_METODOLOGICO.md` §2](MANUAL_METODOLOGICO.md).
>
> **Los números se parecen y no significan lo mismo.** `3100-3199` acá es el bloque local de la app con `APP_ID=1`; en el VPS es el rango de **Test** para cualquier app. Nunca deduzcas el puerto del VPS a partir de tu `APP_ID`, ni al revés: en el VPS el puerto se asigna secuencialmente y **se verifica libre antes de reservarlo**.

Para evitar colisiones cuando un dev levanta múltiples apps simultáneamente, cada app reserva un bloque de 100 puertos basado en su `APP_ID`.

### Fórmula

```
Puerto app    = 3000 + (APP_ID × 100)
Puerto DB     = 3000 + (APP_ID × 100) + 1    (solo en modo debug)
```

| APP_ID | App | Puerto App | Puerto DB (debug) | Rango reservado |
|--------|-----|-----------|-------------------|-----------------|
| 1 | inventario | 3100 | 3101 | 3100-3199 |
| 2 | facturacion | 3200 | 3201 | 3200-3299 |
| 3 | rrhh | 3300 | 3301 | 3300-3399 |
| 4 | crm | 3400 | 3401 | 3400-3499 |
| 5 | proyectos | 3500 | 3501 | 3500-3599 |
| 6 | logistica | 3600 | 3601 | 3600-3699 |
| 7 | calidad | 3700 | 3701 | 3700-3799 |
| 8 | produccion | 3800 | 3801 | 3800-3899 |
| 9 | reportes | 3900 | 3901 | 3900-3999 |
| 10+ | (solicitar) | ... | ... | ... |

> **Nota v4:** los puertos `9100-9999` que en v3 reservaba `maestro-mock` ya **NO se usan** para auth. Quedan libres salvo que un equipo los re-proponga para mockear el `branding endpoint` del Maestro v2 (ver §9).

### Reglas

- El `APP_ID` se asigna al crear el fork (coordinar con el administrador).
- Se declara en `maestro.yaml` y en `.env`.
- Nunca uses puertos por debajo de 3000 ni por encima de 9999.
- Si tu app necesita puertos adicionales (WebSocket, worker, etc.), usá `base+2`, `base+3`, etc., dentro de tu bloque.
- **Este bloque no te reserva nada en el VPS.** Al desplegar a Test o Preproducción, el puerto sale del rango del ambiente y se verifica libre con el chequeo de [`MANUAL_METODOLOGICO.md` §2.3](MANUAL_METODOLOGICO.md).

---

## 6. Redes Docker y Aislamiento

```yaml
networks:
  app-net:
    driver: bridge
    name: app-${APP_NAME}-net
```

Esto garantiza:

- **Aislamiento**: `app-inventario` no puede hacer ping a `app-facturacion`.
- **Nombres DNS internos**: dentro de la red, los servicios se referencian por nombre (`db`, `redis`).
- **Sin conflictos**: dos apps pueden tener un servicio llamado `db` sin colisionar (viven en redes distintas).

En producción, el Maestro v2 crea una red aislada por cada deployment (empresa + app) con el nombre `app_{slug}_{empresa}`.

---

## 7. Seguridad

### En desarrollo (tu fork)

| Regla | Implementación |
|---|---|
| No hay secretos en el repo | Usar `.env` (gitignored) + `.env.example` como referencia |
| No hay credenciales hardcodeadas | Todo viene de variables de entorno |
| DB no expuesta por default | El puerto de DB solo se expone si `DB_EXPOSE_PORT=true` |
| Usuario no-root en Docker | El Dockerfile debe usar `USER appuser` |
| Filesystem read-only | El contenedor solo escribe en `/app/storage` (volumen montado) |
| Password storage | bcrypt (cost ≥ 12) o argon2id en la tabla `users` |
| Tokens propios | Cookies `HttpOnly + Secure + SameSite` o JWT con expiración corta + refresh |
| Audit log | Tabla `audit_log` inmutable (solo INSERT) con eventos de auth |

### Prohibiciones absolutas v4

```
✗ Nunca incluir .env en el repo (solo .env.example)
✗ Nunca montar /var/run/docker.sock en la app huésped
✗ Nunca usar --privileged ni --network=host
✗ Nunca hardcodear IPs, puertos, passwords ni api keys
✗ Nunca exponer la DB al host sin DB_EXPOSE_PORT=true explícito
✗ Nunca leer headers X-Auth-* (deprecados; el Maestro v2 NO los inyecta)
✗ Nunca filtrar queries por company_id (single-tenant físico)
✗ Nunca almacenar passwords en texto plano (siempre bcrypt/argon2id)
✗ Nunca loguear: passwords, hashes, JWTs, MAESTRO_API_KEY, MAESTRO_WEBHOOK_SECRET, SUPERADMIN_INITIAL_PASSWORD, cookies de sesión
✗ Nunca modificar archivos dentro de Tailwise Bundle/ (copiar a app/)
✗ Nunca modificar framework-agentico/
```

### Obligaciones nuevas v4

```
✓ Tabla users con password_hash (bcrypt cost ≥ 12 o argon2id)
✓ Tablas roles y permissions (estructura sugerida; ver framework-agentico/core/PRESET_WEB_MAESTRO.md §02-Planning)
✓ Login propio en auth.login_path (default /login)
✓ Logout que invalida el token
✓ Endpoint /maestro/branding autenticado con X-Maestro-Api-Key
✓ Seeder idempotente del superadmin admin@llyasoc.com (fase 05)
✓ Audit log de eventos de auth (login OK/FAIL, logout, password change, role change)
✓ Rate limiting en /login (ej: 5 intentos por minuto por IP)
✓ Validación de SUPERADMIN_INITIAL_PASSWORD (≥ 12 chars, complejidad, no en blacklist)
```

---

## 8. Autenticación: Login Propio de la App

> **Cambio importante respecto a v3:** en v4, la app **implementa su propio login**. NO recibe headers `X-Auth-*` del Maestro. NO depende de Traefik ForwardAuth.

### Flujo de auth en v4

```
1. Usuario navega al portal del Maestro v2.
2. Click en la app → Maestro abre la URL de la app en target="_blank".
3. La app muestra su propio formulario de login (auth.login_path).
4. Usuario ingresa email + password.
5. La app valida contra su tabla users (bcrypt/argon2id).
6. Si OK: emite token (cookie HttpOnly o JWT) y redirige al dashboard.
7. Cada request posterior usa ese token; la app valida con su middleware.
```

### Tabla `users` mínima (sugerida, no obligatoria)

```sql
CREATE TABLE users (
  id UUID PRIMARY KEY,
  email VARCHAR(255) UNIQUE NOT NULL,
  password_hash VARCHAR(255) NOT NULL,
  name VARCHAR(255),
  is_active BOOLEAN DEFAULT TRUE,
  last_login_at TIMESTAMP,
  created_at TIMESTAMP DEFAULT NOW(),
  updated_at TIMESTAMP DEFAULT NOW()
);
CREATE INDEX idx_users_email ON users(email);
```

Más detalle (incluyendo `roles`, `permissions` y pivots) en `docs/APP_HUESPED_SPEC.md` §3.

### Middleware de auth (obligatorio)

Toda app debe tener un middleware que:

1. Lee el token del request (cookie o header `Authorization: Bearer ...`).
2. Valida el token contra su BD o lo verifica criptográficamente (JWT).
3. Carga el usuario y sus roles/permisos en el contexto del request.
4. Rechaza con `HTTP 401` si el token es inválido o expirado.
5. **Excepciones públicas** (NO requieren auth): `/health`, `/login`, `/maestro/branding` (que tiene su propio middleware de api key).

### Stack-agnóstico — recomendaciones por lenguaje

| Stack | Library recomendada |
|---|---|
| Node.js / Express | `passport.js` + `bcrypt` + `express-session` (cookies) o `jsonwebtoken` (JWT) |
| Python / Django | `django.contrib.auth` (incluye bcrypt + sesiones) |
| Python / FastAPI | `passlib[bcrypt]` + `python-jose` (JWT) o `fastapi-users` |
| PHP / Laravel | `Laravel Sanctum` (SPA con cookies) o `Laravel Passport` (OAuth2) |
| Go / Gin / Fiber | `golang.org/x/crypto/bcrypt` + `github.com/golang-jwt/jwt/v5` |
| .NET / ASP.NET | `Microsoft.AspNetCore.Identity` |
| Ruby / Rails | `Devise` |

Lo único obligatorio: que cumpla las reglas v4 de §7 y §8.

### Si el dev necesita "ver" cómo se vería el login antes de implementarlo

Tailwise tiene componentes de login listos para adaptar (ver §3, página de referencia "Login propio"). Copialos a `app/` y conectalos a tu backend.

---

## 9. Endpoint /maestro/branding

> **Nuevo en v4.** Reemplaza al rol del Maestro v3 que mantenía la tabla canónica de empresas.

Cada app huésped expone un endpoint que el Maestro v2 consume para obtener el nombre y los logos de la empresa que opera ese deployment. El Maestro lo usa en su portal para mostrar branding.

### Contrato

```
GET /maestro/branding
Headers:
  X-Maestro-Api-Key: <secret compartido>

200 OK
Content-Type: application/json
{
  "company_name": "Acme S.A.",
  "logo_url": "https://app.example.com/storage/logo.png",
  "primary_color": "#1F2937",   // opcional
  "favicon_url": "https://app.example.com/storage/favicon.ico"  // opcional
}

401 Unauthorized   (si X-Maestro-Api-Key falta o es inválida)
```

### ENV var asociada

```
MAESTRO_API_KEY=<secret compartido entre Maestro v2 y la app>
```

El Maestro v2 conoce esta key y la envía en cada request. La app la valida con timing-safe-compare. Rotación recomendada: cada 90 días.

### Cómo implementarlo (ejemplo Express + Node)

```js
import express from 'express';
import { timingSafeEqual } from 'node:crypto';

const router = express.Router();

router.get('/maestro/branding', (req, res) => {
  const apiKey = req.header('X-Maestro-Api-Key') ?? '';
  const expected = process.env.MAESTRO_API_KEY ?? '';
  const a = Buffer.from(apiKey);
  const b = Buffer.from(expected);
  if (a.length !== b.length || !timingSafeEqual(a, b)) {
    return res.status(401).json({ error: 'invalid_api_key' });
  }
  res.json({
    company_name: process.env.COMPANY_NAME ?? 'Demo Co.',
    logo_url: `${req.protocol}://${req.get('host')}/storage/logo.png`,
  });
});
```

---

## 10. Seeding del Superadmin

> **Nuevo en v4 (fase 05-seeding del framework agéntico).**

Cada deployment de app huésped debe arrancar con un usuario superadmin operativo. El framework v4 obliga:

- Email canónico: `admin@llyasoc.com`
- Rol: `superadmin` con TODOS los permisos definidos por la app
- Password: leída desde ENV var `SUPERADMIN_INITIAL_PASSWORD`
- Idempotente: re-correr el seeder NO duplica usuarios ni cambia passwords existentes

### Ejemplo de seeder (Node.js)

```js
// app/src/seeders/superadmin.js
import bcrypt from 'bcrypt';
import { db } from '../db.js';

const SUPERADMIN_EMAIL = 'admin@llyasoc.com';
const PASSWORD_MIN_LENGTH = 12;

export async function seedSuperadmin() {
  const password = process.env.SUPERADMIN_INITIAL_PASSWORD;
  if (!password || password.length < PASSWORD_MIN_LENGTH) {
    console.error('[seed] SUPERADMIN_INITIAL_PASSWORD missing or too weak (>=12 chars)');
    process.exit(1);
  }
  // Validar contra blacklist mínima
  if (['admin', 'password', '123456789012'].includes(password.toLowerCase())) {
    console.error('[seed] password is in common-passwords blacklist');
    process.exit(1);
  }

  // Crear/verificar rol superadmin
  const role = await db.upsertRole('superadmin', { description: 'Acceso total' });
  await db.assignAllPermissionsToRole(role.id);

  // Crear/verificar usuario
  const user = await db.findUserByEmail(SUPERADMIN_EMAIL);
  if (!user) {
    const password_hash = await bcrypt.hash(password, 12);
    await db.createUser({ email: SUPERADMIN_EMAIL, password_hash, name: 'Super Admin', is_active: true });
    console.log(`[seed] superadmin ${SUPERADMIN_EMAIL} created`);
  } else {
    console.log(`[seed] superadmin ${SUPERADMIN_EMAIL} already exists, leaving password untouched`);
  }
  // Asegurar que tenga el rol
  await db.assignRoleIfMissing(user?.id ?? (await db.findUserByEmail(SUPERADMIN_EMAIL)).id, role.id);
}

if (import.meta.url === `file://${process.argv[1]}`) {
  seedSuperadmin().then(() => process.exit(0)).catch(e => { console.error(e); process.exit(1); });
}
```

### Hook en el pipeline de deploy

El seeder debe ejecutarse **post-migrations** en cada deploy. Ejemplo de paso en `.github/workflows/deploy.yml`:

```yaml
- name: Seed superadmin (idempotent)
  run: docker compose exec app npm run seed:superadmin
  env:
    SUPERADMIN_INITIAL_PASSWORD: ${{ secrets.SUPERADMIN_INITIAL_PASSWORD }}
```

### Tests obligatorios

1. Sin `SUPERADMIN_INITIAL_PASSWORD` → seeder falla con exit != 0.
2. Password débil (< 12 chars o blacklisted) → seeder falla.
3. Primera ejecución → crea `admin@llyasoc.com` con rol `superadmin` y todos los permisos.
4. Segunda ejecución → no duplica, no cambia password.
5. Si existe sin rol → asigna rol superadmin sin tocar password.
6. Login con la password de la ENV → 200.

Detalle completo en `framework-agentico/phases/05-seeding.md`.

---

## 11. docker-compose.yml: Template Base

Este es el `docker-compose.yml` de la **raíz**, para desarrollo local. Es obligatorio por contrato (`IN-011`) y es el que evalúa el Gate 1 — **no se elimina ni se reemplaza**.

Para desplegar a Dokploy hacen falta además `docker-compose.test.yml` y `docker-compose.preprod.yml`, autocontenidos y con `name:` explícito de proyecto y de volúmenes: ver [`MANUAL_METODOLOGICO.md` §1.5](MANUAL_METODOLOGICO.md).

```yaml
# docker-compose.yml
# App: {APP_NAME} | APP_ID: {APP_ID}
# Ver tabla de puertos en README §5

services:
  # ── Tu aplicación ──
  app:
    build:
      context: ./app
      dockerfile: Dockerfile
    container_name: app-${APP_NAME}
    restart: unless-stopped
    env_file: .env
    environment:
      - DATABASE_URL=${DB_DRIVER}://${DB_USER}:${DB_PASSWORD}@db:${DB_PORT_INTERNAL}/${DB_NAME}
      - APP_ENV=${APP_ENV}
      - JWT_SECRET=${JWT_SECRET}
      - MAESTRO_API_KEY=${MAESTRO_API_KEY}
      - MAESTRO_WEBHOOK_SECRET=${MAESTRO_WEBHOOK_SECRET}
      - SUPERADMIN_INITIAL_PASSWORD=${SUPERADMIN_INITIAL_PASSWORD}
      - COMPANY_NAME=${COMPANY_NAME}
    ports:
      - "${APP_PORT}:${APP_INTERNAL_PORT}"
    volumes:
      - ./app/src:/app/src
      - app-storage:/app/storage
    networks:
      - app-net
    depends_on:
      db:
        condition: service_healthy
    healthcheck:
      test: ["CMD", "curl", "-f", "http://localhost:${APP_INTERNAL_PORT}/health"]
      interval: 30s
      timeout: 5s
      start_period: 60s
      retries: 3

  # ── Base de datos ──
  db:
    image: ${DB_IMAGE}
    container_name: db-${APP_NAME}
    restart: unless-stopped
    environment:
      - POSTGRES_DB=${DB_NAME}
      - POSTGRES_USER=${DB_USER}
      - POSTGRES_PASSWORD=${DB_PASSWORD}
    volumes:
      - db-data:/var/lib/postgresql/data
    networks:
      - app-net
    ports:
      - "${DB_DEBUG_PORT}:${DB_PORT_INTERNAL}"
    healthcheck:
      test: ["CMD-SHELL", "pg_isready -U ${DB_USER}"]
      interval: 10s
      timeout: 5s
      retries: 5

  # ── Redis (opcional) ──
  # redis:
  #   image: redis:7-alpine
  #   container_name: redis-${APP_NAME}
  #   restart: unless-stopped
  #   command: redis-server --requirepass ${REDIS_PASSWORD}
  #   networks: [app-net]

volumes:
  db-data:
    name: ${APP_NAME}-db-data
  app-storage:
    name: ${APP_NAME}-storage

networks:
  app-net:
    driver: bridge
    name: app-${APP_NAME}-net
```

> **Cambio v4:** ya no hay servicio `maestro-mock`. La app maneja su propio login. El usuario en dev se loguea directamente con el superadmin creado por el seeder.

---

## 12. Dockerfile: Requisitos Obligatorios

Todo Dockerfile debe cumplir estos 7 requisitos:

```dockerfile
# ── Stage 1: Build ──
FROM <base-image> AS builder
WORKDIR /app
COPY . .
RUN <install-deps> && <build>

# ── Stage 2: Runtime ──
FROM <slim-base-image>
WORKDIR /app

# 1. OBLIGATORIO: Usuario no-root
RUN addgroup --system appgroup && \
    adduser --system --ingroup appgroup appuser

# 2. OBLIGATORIO: Copiar solo lo necesario
COPY --from=builder /app/dist ./dist
COPY --from=builder /app/node_modules ./node_modules

# 3. OBLIGATORIO: Volumen persistente
RUN mkdir -p /app/storage && chown appuser:appgroup /app/storage
VOLUME /app/storage

# 4. OBLIGATORIO: Puerto interno fijo
EXPOSE 3000

# 5. OBLIGATORIO: Ejecutar como no-root
USER appuser

# 6. OBLIGATORIO: Health check
HEALTHCHECK --interval=30s --timeout=5s --start-period=60s --retries=3 \
    CMD curl -f http://localhost:3000/health || exit 1

# 7. OBLIGATORIO: Comando de inicio
CMD ["node", "dist/server.js"]
```

### .dockerignore recomendado

```
.git
.gitignore
node_modules
vendor
.env
.env.*
!.env.example
*.log
*.md
!README.md
Tailwise Bundle/
framework-agentico/
legacy/
.claude/
docker-compose*.yml
.DS_Store
__pycache__
.pytest_cache
coverage
dist
```

---

## 13. maestro.yaml: Contrato de Integración v2

Cada fork debe tener un `maestro.yaml` en la raíz:

```yaml
apiVersion: maestro.platform/v2
kind: Application
metadata:
  name: inventario
  version: 1.0.0
  description: "Sistema de inventario"
requires:
  database: postgres
  ports:
    app: 3000
health:
  endpoint: /health
  timeout_seconds: 5
auth:
  mode: own                    # v2: la app implementa su propio login
  login_path: /login
  logout_path: /logout         # opcional
branding:
  url: /maestro/branding       # endpoint autenticado con X-Maestro-Api-Key
seeding:
  superadmin_email: admin@llyasoc.com
  additional_users: []         # opcional, decisión del PO en fase 02-planning
hooks:                         # opcional
  on_user_added: /hooks/user-added
  on_company_license_revoked: /hooks/license-revoked
resources:
  memory: 512m
  cpu: 0.5
ui:
  tailwise: true
  theme: echo
env:
  - SMTP_HOST
  - REDIS_URL
  - FEATURE_FLAGS_API_KEY
```

Validar con: `maestro-cli validate` (cuando el CLI v2 esté disponible) o contra el schema en `docs/schemas/maestro.yaml.schema.v2.json`.

Spec completa: `docs/APP_HUESPED_SPEC.md`.

---

## 14. Variables de Entorno (.env)

Al crear tu fork, copiá `.env.example` a `.env` y ajustá los valores:

```bash
cp .env.example .env
```

El archivo `.env.example` está documentado con todos los valores posibles. Variables organizadas por bloques:

- **APP**: identificación, puertos, entorno
- **DB**: motor, credenciales, debug port
- **AUTH (v4)**: `JWT_SECRET`, `BCRYPT_COST` para hash de passwords
- **MAESTRO (v4)**: `MAESTRO_API_KEY`, `MAESTRO_WEBHOOK_SECRET`, `MAESTRO_BASE_URL`
- **SEEDING (v4)**: `SUPERADMIN_INITIAL_PASSWORD`
- **REDIS**: configuración opcional
- **TAILWISE**: theme y versión
- **STORAGE / LOGGING / SMTP**: opcionales según necesidad de la app

Ver `.env.example` para la referencia completa.

---

## 15. Flujo de Desarrollo

```
1. FORK
   └─ Hacer fork del repo principal a tu cuenta/org

2. SETUP
   └─ cp .env.example .env
   └─ Editar .env: APP_ID, APP_NAME, DB engine, secretos
   └─ Generar SUPERADMIN_INITIAL_PASSWORD seguro (>= 12 chars)
   └─ Crear: maestro.yaml, Dockerfile, docker-compose.yml, app/
   └─ Copiar assets de Tailwise según tu stack

3. DESARROLLAR
   └─ git checkout -b develop
   └─ docker compose up -d
   └─ Implementar tabla users, roles, permissions (migraciones)
   └─ Implementar login propio (formulario + endpoint + middleware)
   └─ Implementar /maestro/branding con X-Maestro-Api-Key
   └─ Implementar seeder del superadmin
   └─ Acceder a la app: http://localhost:{APP_PORT} (ej: 3100)
   └─ Loguearse como admin@llyasoc.com con SUPERADMIN_INITIAL_PASSWORD

4. TESTEAR
   └─ Tests de login (200/401)
   └─ Tests de health (200 sin auth)
   └─ Tests de /maestro/branding (sin/con api key inválida → 401, con válida → 200)
   └─ Tests de seeder idempotente
   └─ Tests de aislamiento (single-tenant: no debe haber company_id en queries)

5. PROPONER CAMBIOS
   └─ Push a fork/develop
   └─ Crear PR: fork/develop → principal/app-{nombre}
   └─ CI corre: lint + tests + maestro-cli validate (v2 schema) + trivy scan
   └─ Esperar review del administrador

6. MERGE + CI/CD
   └─ Administrador revisa y mergea
   └─ CI/CD construye imagen Docker
   └─ Maestro v2 (cuando esté disponible) registra y despliega un deployment por empresa
```

---

## 16. Despliegue: Del Fork a Producción

```
TU FORK (desarrollo)              REPO PRINCIPAL                PRODUCCIÓN

fork/develop ──PR──► principal/app-{nombre} ──CI/CD──► ghcr.io/org/app-{nombre}:sha
                            │                                     │
                     Admin aprueba                          Maestro v2 registra
                                                            y provisiona
                                                                │
                                                         ┌──────┴──────────┐
                                                         │ Deployment       │
                                                         │ empresa-A       │
                                                         │ + DB propia     │
                                                         │ + ENV vars      │
                                                         │   inyectados    │
                                                         │   (incluye      │
                                                         │   SUPERADMIN_*) │
                                                         │ + seeder corre  │
                                                         │   post-migrate  │
                                                         └─────────────────┘
                                                                │
                                                  Maestro consume /maestro/branding
                                                  (con X-Maestro-Api-Key) para mostrar
                                                  nombre y logos en su portal.
```

**En producción (Maestro v2):**
- El Maestro v2 descarga la imagen, crea red aislada, provisiona BD, inyecta ENV vars.
- El pipeline ejecuta migraciones + seeder.
- La app queda accesible en `https://<app_slug>-<empresa_slug>.<MAESTRO_BASE_DOMAIN>`.
- Cuando un usuario hace click desde el portal del Maestro, se abre la URL en `target="_blank"`.
- El usuario hace login en la app con sus credenciales propias.

### Ambientes previos: Test y Preproducción (Dokploy)

Antes de producción hay **dos ambientes** sobre el VPS interno `llubuntu2` (`10.100.1.124`), que se operan desde el panel de Dokploy (`http://10.100.1.124:3000/`). El procedimiento completo está en **[`MANUAL_METODOLOGICO.md`](MANUAL_METODOLOGICO.md)**; el resumen:

| Ambiente | Tag | Qué es | Quién lo despliega |
|---|---|---|---|
| **Test** | `Test` | App **sin evaluar**, para probar el desarrollo end-to-end en un entorno real. | **El desarrollador**, por su cuenta. |
| **Preproducción** | `Preprod` | App **ya evaluada** contra el Maestro y aprobada por el evaluador humano. Se registra en el catálogo. | **El evaluador humano**, nunca el desarrollador. |

Lo que tenés que saber antes de abrir el manual:

- **El código llega por Provider `Git`** (`sourceType: git` + `customGitUrl`), y el despliegue se hace **por API**, no a mano por el panel.
- **Un `docker-compose` por ambiente**, versionado en el repo y autocontenido: `docker-compose.yml` (desarrollo local, el obligatorio de §11), `docker-compose.test.yml` y `docker-compose.preprod.yml`. Dokploy recibe un solo `composePath`, así que no hay overlays.
- **Los puertos del VPS no son los de §5** — ver la advertencia de esa sección.
- **Un Gate 1 en PASS habilita la revisión, no la promoción.** El desarrollador auto-evalúa su propio PR hasta PASS y ahí se detiene: no corre el Gate 2, no mergea y no despliega a `Preprod`.
- El ambiente corre sobre **HTTP sin certificado**: no se suben datos reales.

> **Estado transitorio (mientras Maestro v2 no exista):** las apps v4 funcionan **standalone**. Levantás el fork local con `docker compose up`, te logueás directo, y operás. El endpoint `/maestro/branding` queda preparado para cuando el Maestro v2 esté disponible.

---

## 17. Checklist Pre-PR

```
ESTRUCTURA
[ ] maestro.yaml v2 (apiVersion: maestro.platform/v2)
[ ] Dockerfile cumple los 7 requisitos
[ ] docker-compose.yml levanta con `docker compose up -d`
[ ] docker-compose.test.yml y docker-compose.preprod.yml presentes y autocontenidos
    (MANUAL_METODOLOGICO.md §1.5)
[ ] Los tres compose parsean con `docker compose -f <archivo> config`
[ ] Ninguno de los tres tiene secretos hardcodeados (grep anti-hardcode, IN-011)
[ ] .dockerignore excluye Tailwise Bundle/, framework-agentico/, .env, legacy/
[ ] .env.example actualizado con todas las variables usadas

PUERTOS Y REDES
[ ] Puertos locales según APP_ID (ver §5)
[ ] Puerto del VPS tomado del rango del ambiente y verificado libre
    (MANUAL_METODOLOGICO.md §2 — NO se deduce del APP_ID)
[ ] Red Docker: app-{nombre}-net
[ ] Volúmenes: {nombre}-db-data, {nombre}-storage
[ ] DB no expone puerto sin DB_EXPOSE_PORT=true

AUTENTICACIÓN (v4)
[ ] Tabla users con password_hash (bcrypt cost ≥ 12 o argon2id)
[ ] Tabla roles + permissions con pivots
[ ] Middleware de auth lee tokens propios (NO X-Auth-*)
[ ] /login emite token; /logout lo invalida
[ ] Tests de auth pasan (200 con creds válidas, 401 sin/inválidas)
[ ] Sin company_id en queries (single-tenant físico)

ENDPOINT /maestro/branding (v4)
[ ] Path declarado en maestro.yaml branding.url
[ ] Sin X-Maestro-Api-Key → 401
[ ] Con X-Maestro-Api-Key inválida → 401
[ ] Con válida → 200 + JSON { company_name, logo_url, ... }
[ ] Comparación de api key con timing-safe

SEEDING (v4)
[ ] Seeder idempotente del superadmin admin@llyasoc.com
[ ] SUPERADMIN_INITIAL_PASSWORD obligatoria; falla si missing/débil
[ ] Re-ejecutar el seeder no duplica ni cambia passwords existentes
[ ] Hook en pipeline de deploy

HEALTH
[ ] GET /health retorna 200 con {"status":"ok"}
[ ] /health NO requiere autenticación
[ ] HEALTHCHECK en Dockerfile

UI
[ ] Tailwise integrado (o excepción documentada en maestro.yaml)
[ ] Un solo theme en toda la app

SEGURIDAD
[ ] No hay .env en el repo
[ ] No hay credenciales/api keys hardcodeadas
[ ] Logs no exponen passwords, hashes, tokens, MAESTRO_API_KEY, MAESTRO_WEBHOOK_SECRET, SUPERADMIN_INITIAL_PASSWORD
[ ] Cookies con HttpOnly + Secure + SameSite (si usás cookies)
[ ] La bandera Secure es apagable por env var para ambientes sin TLS
    (el VPS de Test/Preprod corre HTTP; con Secure el navegador descarta la
    cookie y el login entra en bucle silencioso — MANUAL_METODOLOGICO.md §6.4)
[ ] Nombre de la cookie de sesión único en toda la plataforma: <slug>_session
    (NO maestro_session: las cookies se indexan por host, no por puerto, y
    pisaría la sesión del portal del Maestro)
[ ] Audit log de auth implementado (recomendado)
[ ] Rate limiting en /login

INTEGRIDAD DEL REPO
[ ] No se modificó framework-agentico/
[ ] No se modificaron archivos dentro de Tailwise Bundle/
[ ] CLAUDE.md herredita reglas del template
[ ] Versión en maestro.yaml incrementada
```

---

## 18. Troubleshooting

### "Puerto en uso" al levantar docker compose

```bash
lsof -i :3100            # Ver qué usa el puerto
docker ps -a             # Ver todos los contenedores
docker compose down      # Apagar el otro stack primero
```

### "El seeder falla por SUPERADMIN_INITIAL_PASSWORD"

Causas comunes:
- Variable no seteada en `.env`.
- Password muy corta (< 12 chars).
- Password en blacklist (`admin`, `password`, `12345`).

Solución: generar una password fuerte y agregarla al `.env`. Ejemplo:
```bash
openssl rand -base64 24
```

### "Mi app no recibe el request de /maestro/branding"

En desarrollo standalone, no hay Maestro v2 consumiendo el endpoint todavía. Podés probarlo manualmente:
```bash
curl -H "X-Maestro-Api-Key: $MAESTRO_API_KEY" http://localhost:3100/maestro/branding
```

### "¿Cómo conecto mi app con otra app?"

En desarrollo local, no conectás. Cada app es autónoma.
En producción (cuando el Maestro v2 esté disponible), usarás el API Gateway del Maestro v2:
```
GET https://maestro.tudominio.com/api/v2/gateway/{otra-app}/endpoint
```
Nunca conectás directamente entre contenedores.

### "Antes había un mock/ con auth simulada. ¿Sigue siendo válido?"

NO. El directorio `mock/` era **legacy v3** y simulaba la inyección de headers `X-Auth-*` cuando el Maestro v1 actuaba como Identity Provider. En v4, la app maneja su propio login y no necesita ese mock. **El directorio fue eliminado del template** durante el cleanup del 2026-05-07; sigue accesible via git history si alguien lo necesita como referencia historica.

### "Quiero levantar 2 apps al mismo tiempo"

Cada app tiene puertos distintos:
```bash
# Terminal 1: inventario (APP_ID=1) → http://localhost:3100
cd fork-inventario && docker compose up -d

# Terminal 2: facturación (APP_ID=2) → http://localhost:3200
cd fork-facturacion && docker compose up -d
```

### "¿Cómo uso un componente de Tailwise?"

1. Identificá tu stack (React, Vue, Laravel, HTML)
2. Buscá el componente en `Tailwise Bundle/{tu-version}/Source/`
3. Copialo a tu `app/src/components/` o `app/resources/views/components/`
4. Adaptalo a tu lógica
5. Nunca edites el original en `Tailwise Bundle/`

### "Mi stack no es compatible con Tailwise"

Documentá en `maestro.yaml` con `ui.tailwise: false` y `ui.reason`.

---

## 19. Documentos de Referencia

| Documento | Rol |
|---|---|
| `MANUAL_METODOLOGICO.md` | **Despliegue a Test y Preproducción vía Dokploy**: flujo operativo, convención de nombres/tags, puertos del VPS, despliegue por API, verificación, evaluación contra el Maestro y reparto de responsabilidades desarrollador ↔ evaluador humano |
| `framework-agentico/CHANGELOG.md` | Historial completo v3 → v4 |
| `framework-agentico/migration/v3-to-v4.md` | Proceso de migración para apps existentes v3 |
| `framework-agentico/core/RULES.md` | Reglas generales del framework v4 (glosario de sinónimos, política de versionado, política de persistencia de datos, activación de preset, etc.) |
| `framework-agentico/core/PRESET_WEB_MAESTRO.md` | Constraints del preset `web-maestro` (apps huésped, default) |
| `framework-agentico/agents/presets/maestro-platform/PRESET.md` | Constraints del preset `maestro-platform` (Web Maestro / Web Anfitriona) |
| `framework-agentico/phases/05-seeding.md` | Detalle de la fase 05-seeding |
| `docs/APP_HUESPED_SPEC.md` | Especificación normativa del contrato `maestro.platform/v2` (este README es la guía rápida; aquí va el detalle técnico) |
| `docs/APP_HUESPED_BEST_PRACTICES.md` | Recomendaciones (12-factor, supply chain, observabilidad, testing) |
| `docs/CONVENCIONES_PLATAFORMA.md` | Naming, redes, puertos, env vars |
| `docs/schemas/maestro.yaml.schema.v2.json` | JSON Schema v2 para validar tu `maestro.yaml` |
| `legacy/README.md` | Índice de versiones anteriores (en `legacy/v{n}/`) |
| `CHANGELOG.md` | Cambios del repo (este template) |

### Documentos legacy (referencia histórica)

| Documento | Estado |
|---|---|
| `legacy/v3/docs/APP_HUESPED_SPEC.md` | DEPRECADO (contrato v1) — vigente: `docs/APP_HUESPED_SPEC.md` |
| `legacy/v3/docs/APP_HUESPED_BEST_PRACTICES.md` | DEPRECADO (acompañaba v1) — vigente: `docs/APP_HUESPED_BEST_PRACTICES.md` |
| `legacy/v3/docs/CONVENCIONES_PLATAFORMA.md` | DEPRECADO (convenciones v1) — vigente: `docs/CONVENCIONES_PLATAFORMA.md` |
| `legacy/v3/framework-agentico/agents/presets/maestro-platform/` | DEPRECADO (preset v1 del Maestro) — vigente: `framework-agentico/agents/presets/maestro-platform/` |
| `legacy/v3/PremisaWebMaestro/` | DEPRECADO (constitución v1 del Maestro) — será reescrita en `PremisaWebMaestro/` v4 (Fase 3 del cleanup) |
| `legacy/v3/arquitectura_actual.md` | DEPRECADO (snapshot histórico del 2026-04-14, sin reemplazo) |
| `mock/` | ELIMINADO en cleanup v4. Recuperable via git history (commit anterior a 2026-05-07). |
| `cli/` | ELIMINADO en cleanup v4 (el repo es stack-agnóstico). Recuperable via git history. |

Para apps v4 nuevas, ignorá los legacy. Para apps v3 que migran a v4, ver `framework-agentico/migration/v3-to-v4.md`.
