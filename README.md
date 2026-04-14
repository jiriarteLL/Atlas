# Plataforma Maestro — Guía de Desarrollo de Aplicaciones

> Este repositorio es el punto de partida para desarrollar aplicaciones compatibles con la plataforma Web Maestro. Cada aplicación se desarrolla en un **fork independiente** de este repo, con su propio Docker Compose, base de datos y ciclo de vida aislado. Todas las apps comparten el sistema de diseño **Tailwise** para mantener una experiencia visual unificada.

---

## Índice

1. [Modelo de Trabajo](#1-modelo-de-trabajo)
2. [Estructura del Fork](#2-estructura-del-fork)
3. [Tailwise Bundle: Sistema de Diseño Unificado](#3-tailwise-bundle-sistema-de-diseño-unificado)
4. [Docker: Arquitectura por App](#4-docker-arquitectura-por-app)
5. [Convención de Puertos](#5-convención-de-puertos)
6. [Redes Docker y Aislamiento](#6-redes-docker-y-aislamiento)
7. [Seguridad](#7-seguridad)
8. [Autenticación: Integración con el Maestro](#8-autenticación-integración-con-el-maestro)
9. [Maestro Mock: Desarrollo Sin Dependencias](#9-maestro-mock-desarrollo-sin-dependencias)
10. [docker-compose.yml: Template Base](#10-docker-composeyml-template-base)
11. [Dockerfile: Requisitos Obligatorios](#11-dockerfile-requisitos-obligatorios)
12. [maestro.yaml: Contrato de Integración](#12-maestroyaml-contrato-de-integración)
13. [Variables de Entorno (.env)](#13-variables-de-entorno-env)
14. [Flujo de Desarrollo](#14-flujo-de-desarrollo)
15. [Despliegue: Del Fork a Producción](#15-despliegue-del-fork-a-producción)
16. [Checklist Pre-PR](#16-checklist-pre-pr)
17. [Troubleshooting](#17-troubleshooting)

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
- Se levanta sin depender del Maestro ni de otros forks
- El equipo tiene gobierno total del fork
- Los cambios se proponen vía PR al repo principal
- Solo el administrador aprueba merges al repo principal
```

### Reglas de gobernanza

- Cada fork trabaja sobre una rama `develop` propia.
- Para proponer cambios al repo principal, se crea un PR desde `fork/develop` hacia `principal/app-{nombre}`.
- El repo principal tiene una rama por cada app: `app-inventario`, `app-facturacion`, etc.
- Solo el administrador de la organización puede aprobar y mergear PRs al repo principal.
- Nunca se hace PR directo a `main` del repo principal.

---

## 2. Estructura del Fork

Al hacer fork, el desarrollador trabaja dentro de esta estructura. Los archivos `[CREAR]` son nuevos; los `[EXISTENTE]` ya vienen del repo principal.

```
mi-fork/
├── CLAUDE.md                           [EXISTENTE]  Instrucciones agente AI
├── README.md                           [EXISTENTE]  Este documento
├── maestro.yaml                        [CREAR]      Contrato de integración
├── Dockerfile                          [CREAR]      Build de la app
├── docker-compose.yml                  [CREAR]      Stack completo local
├── .dockerignore                       [CREAR]      Exclusiones del build
├── .env.example                        [EXISTENTE]  Variables de entorno de referencia
├── .env                                [CREAR]      Copia de .env.example con tus valores (gitignored)
│
├── app/                                [CREAR]      Código fuente de la app
│   ├── src/
│   │   ├── middleware/
│   │   │   └── maestroAuth.*           [CREAR]      Middleware de auth (obligatorio)
│   │   ├── routes/                     [CREAR]      Endpoints de la app
│   │   ├── services/                   [CREAR]      Lógica de negocio
│   │   └── health.*                    [CREAR]      Health check endpoint
│   ├── migrations/                     [CREAR]      Migraciones de BD
│   ├── resources/                      [CREAR]      Assets del frontend
│   │   ├── css/                        [COPIAR]     Desde Tailwise Bundle
│   │   ├── js/                         [COPIAR]     Desde Tailwise Bundle
│   │   └── images/                     [COPIAR]     Desde Tailwise Bundle
│   └── tests/
│       └── integration/
│           └── auth.test.*             [CREAR]      Tests de auth (obligatorio)
│
├── mock/
│   └── nginx.conf                      [EXISTENTE]  Config del mock de auth
│
├── framework-agentico/                 [EXISTENTE]  Framework de fases de desarrollo
├── Tailwise Bundle/                    [EXISTENTE]  Sistema de diseño (leer, copiar, no modificar)
│   ├── HTML Version - v1.0.1/         Componentes HTML + Tailwind puros
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

### Por qué es obligatorio

Todas las aplicaciones de la plataforma Maestro se muestran dentro del mismo portal (vía iframe). Si cada app tiene un diseño visual diferente, la experiencia del usuario se rompe. Tailwise es el sistema de diseño compartido que garantiza coherencia visual.

**Regla: usar Tailwise es el camino preferido. Solo se permite omitirlo cuando hay un impedimento técnico documentado** (por ejemplo: la app usa un framework UI incompatible como Flutter Web, o es una app sin frontend propio).

### Versiones disponibles

| Tu stack de frontend | Versión de Tailwise a usar | Ruta en el repo |
|---|---|---|
| HTML/JS vanilla | HTML Version v1.0.1 | `Tailwise Bundle/HTML Version - v1.0.1/Source/` |
| Laravel Blade | Laravel Version v1.0.3 | `Tailwise Bundle/Laravel Version - v1.0.3/Source/` |
| React / Next.js | React Version v1.0.9 | `Tailwise Bundle/React Version - v1.0.9/Source/` |
| Vue 3 / Nuxt | Tailwise Vue v1.0.1 | `Tailwise Bundle/Tailwise Vue - v1.0.1/Source/` |

### Cómo integrar Tailwise en tu app

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

**Paso 2: Copiar los componentes base que necesites**

No copies todo. Copia solo los componentes que tu app usa:

```bash
# React: copiar componentes base (botones, forms, tablas, etc.)
cp -r "Tailwise Bundle/React Version - v1.0.9/Source/src/components/Base" app/src/components/Base/

# Laravel: copiar componentes Blade
cp -r "Tailwise Bundle/Laravel Version - v1.0.3/Source/resources/views/components/base" app/resources/views/components/base/
```

**Paso 3: Usar las páginas de referencia como punto de partida**

Tailwise incluye páginas completas que podés usar como plantillas. Elegí la más cercana a tu funcionalidad y adaptala:

| Funcionalidad de tu app | Página de referencia en Tailwise |
|---|---|
| Dashboard / resumen | `dashboard-overview-1` a `dashboard-overview-8` |
| Listado de items | `product-list`, `seller-list`, `transaction-list`, `users` |
| Grilla de items | `product-grid`, `file-manager-grid` |
| Formulario de creación | `add-product`, `add-user`, `regular-form` |
| Detalle de un item | `seller-detail`, `transaction-detail` |
| Configuración | `settings` (con tabs internos) |
| Perfil de usuario | `profile-overview` |
| Login/Registro | `login`, `register` (solo como referencia visual, NO como funcionalidad) |
| Chat / mensajería | `chat`, `inbox` |
| Calendario | `calendar` |
| Facturación | `billing`, `invoice` |
| File manager | `file-manager-list`, `file-manager-grid` |
| Punto de venta | `point-of-sale` |
| Tablas con filtros | `tabulator` |
| Charts y reportes | `chart` |

**Paso 4: Elegir un theme**

Tailwise incluye 11 themes. Elegí uno y mantenerlo consistente en toda tu app:

Themes disponibles: `dagger`, `echo`, `exort`, `havoc`, `hook`, `hurricane`, `ravage`, `raze`, `razor`, `shuriken`, `viper`.

```bash
# React: copiar el theme elegido
cp "Tailwise Bundle/React Version - v1.0.9/Source/src/assets/css/themes/echo.css" app/resources/css/themes/
cp -r "Tailwise Bundle/React Version - v1.0.9/Source/src/themes/Echo" app/src/themes/Echo/
```

Se recomienda que todas las apps de la plataforma usen el mismo theme para máxima consistencia. Consultar con el administrador cuál es el theme oficial.

### Qué copiar y qué no

```
COPIAR a tu app/                          NO COPIAR
─────────────────                         ──────────
src/assets/css/                           Páginas de demo completas (son referencia)
src/assets/css/themes/{tu-theme}.css      Todos los themes (elegir uno)
src/assets/css/components/                Imágenes de demo (users, products, etc.)
src/assets/css/vendors/                   Fakers / datos de prueba
src/assets/css/fonts/
src/components/Base/                      
tailwind.config.js
postcss.config.*
```

### Cuándo se permite NO usar Tailwise

Documentar en `maestro.yaml` el motivo si tu app no usa Tailwise:

```yaml
# maestro.yaml
ui:
  tailwise: false
  reason: "App sin frontend propio, solo API REST"
  # o: "Frontend en Flutter Web, incompatible con Tailwind CSS"
  # o: "App embebida usa componentes nativos de {framework} por requisito del cliente"
```

Si `ui.tailwise` no está declarado o es `true`, se asume que la app usa Tailwise.

---

## 4. Docker: Arquitectura por App

Cada app es un stack Docker autocontenido con mínimo 2 servicios (app + db) y máximo 4 (app + db + redis + maestro-mock):

```
┌─────────────────────────────────────────────────┐
│         FORK: app-inventario                     │
│         Red: app-inventario-net                  │
│                                                   │
│  ┌──────────────┐  ┌──────────────────────────┐  │
│  │  app          │  │  db                       │  │
│  │  :3100        │  │  PostgreSQL/MySQL/Mongo   │  │
│  │  (tu código)  │  │  :5432 (interno)          │  │
│  │               │──│                           │  │
│  └──────┬───────┘  └──────────────────────────┘  │
│         │                                         │
│  ┌──────┴───────┐  ┌──────────────────────────┐  │
│  │  maestro-mock │  │  redis (opcional)         │  │
│  │  :9100        │  │  :6379 (interno)          │  │
│  │  (simula auth)│  │                           │  │
│  └──────────────┘  └──────────────────────────┘  │
└─────────────────────────────────────────────────┘
```

### Principios

1. **Aislamiento total**: Cada app vive en su propia red Docker. Los contenedores de una app no pueden ver los de otra.
2. **Sin puertos compartidos**: Cada app usa un rango de puertos único (ver sección 5).
3. **Base de datos propia**: Cada app tiene su propio contenedor de BD con volumen persistente.
4. **Sin estado compartido**: Las apps no comparten Redis, BD, ni volúmenes entre sí.

---

## 5. Convención de Puertos

Para evitar colisiones cuando un desarrollador levanta múltiples apps simultáneamente en la misma máquina, cada app reserva un bloque de 100 puertos basado en su `APP_ID`.

### Fórmula

```
Puerto app    = 3000 + (APP_ID × 100)
Puerto mock   = 9000 + (APP_ID × 100)
Puerto DB     = 3000 + (APP_ID × 100) + 1    (solo en modo debug)
```

| APP_ID | App | Puerto App | Puerto Mock | Puerto DB (debug) | Rango reservado |
|--------|-----|-----------|------------|-------------------|-----------------|
| 1 | inventario | 3100 | 9100 | 3101 | 3100-3199 |
| 2 | facturacion | 3200 | 9200 | 3201 | 3200-3299 |
| 3 | rrhh | 3300 | 9300 | 3301 | 3300-3399 |
| 4 | crm | 3400 | 9400 | 3401 | 3400-3499 |
| 5 | proyectos | 3500 | 9500 | 3501 | 3500-3599 |
| 6 | logistica | 3600 | 9600 | 3601 | 3600-3699 |
| 7 | calidad | 3700 | 9700 | 3701 | 3700-3799 |
| 8 | produccion | 3800 | 9800 | 3801 | 3800-3899 |
| 9 | reportes | 3900 | 9900 | 3901 | 3900-3999 |
| 10+ | (solicitar) | ... | ... | ... | ... |

### Reglas

- El `APP_ID` se asigna al crear el fork (coordinar con el administrador).
- El `APP_ID` se declara en `maestro.yaml` y en `.env`.
- Nunca uses puertos por debajo de 3000 ni por encima de 9999.
- Si tu app necesita puertos adicionales (WebSocket, worker, etc.), usá los siguientes dentro de tu bloque: `base+2`, `base+3`, etc.
- El contenedor siempre escucha internamente en su puerto natural (3000, 8000, 8080 según stack). El mapping al host es lo que cambia por app.

---

## 6. Redes Docker y Aislamiento

Cada app crea su propia red Docker:

```yaml
networks:
  app-net:
    driver: bridge
    name: app-${APP_NAME}-net
```

Esto garantiza:

- **Aislamiento**: `app-inventario` no puede hacer ping a `app-facturacion`.
- **Nombres DNS internos**: Dentro de la red, los servicios se referencian por nombre (`db`, `redis`, `maestro-mock`), no por IP ni por puerto externo.
- **Sin conflictos**: Dos apps pueden tener un servicio llamado `db` sin colisionar, porque viven en redes distintas.

En producción, el Maestro crea una red aislada por cada instancia (empresa + app) con el nombre `app_{company}_{app}`.

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

### Prohibiciones absolutas

```
✗ Nunca incluir .env en el repo (solo .env.example)
✗ Nunca montar /var/run/docker.sock
✗ Nunca usar --privileged ni --network=host
✗ Nunca hardcodear IPs, puertos o credenciales
✗ Nunca exponer la DB al host sin DB_EXPOSE_PORT=true explícito
✗ Nunca crear tablas de usuarios, sesiones o autenticación
✗ Nunca implementar login propio
✗ Nunca modificar archivos dentro de Tailwise Bundle/ (copiar a app/)
✗ Nunca modificar framework-agentico/
```

---

## 8. Autenticación: Integración con el Maestro

Tu app **nunca implementa login**. En producción, Traefik intercepta cada request, verifica con el Maestro, e inyecta headers de identidad. Tu app solo lee esos headers.

### Headers que tu app recibe

| Header | Tipo | Ejemplo |
|---|---|---|
| `X-Auth-User-Id` | String | `"42"` |
| `X-Auth-User-Email` | String | `"juan@empresa.com"` |
| `X-Auth-Company-Id` | String | `"7"` |
| `X-Auth-Roles` | String | `"admin"` |
| `X-Auth-Permissions` | JSON String | `'["read","write"]'` |

### Middleware obligatorio

Toda app debe tener un middleware que:

1. Lee estos headers en cada request entrante
2. Rechaza con `401` si faltan `X-Auth-User-Id` o `X-Auth-Company-Id`
3. Pone el usuario en el contexto del request para que los controllers lo usen

El endpoint `/health` es la única excepción: NO debe requerir autenticación.

Ver `ARQUITECTURA_APLICACIONES_GENERICAS.md` sección 4.4 para implementaciones en 8 lenguajes distintos (Node.js, Python, PHP, Go, Java, .NET, Ruby, Rust).

---

## 9. Maestro Mock: Desarrollo Sin Dependencias

Para desarrollar sin necesitar el Maestro real corriendo, cada app incluye un servicio `maestro-mock` en su docker-compose. Es un nginx que intercepta los requests, agrega los headers de autenticación, y los reenvia a tu app.

### Cómo funciona

```
Tu navegador → localhost:{MOCK_PORT}
                    ↓
            maestro-mock (nginx)
            intercepta, agrega headers:
              X-Auth-User-Id: 1
              X-Auth-User-Email: dev@test.com
              X-Auth-Company-Id: 1
              X-Auth-Roles: admin
                    ↓
            Tu app recibe request con identidad
```

En desarrollo, accedés a tu app a través del mock (`localhost:9100`), no directamente (`localhost:3100`). El acceso directo es útil solo para debug del health check o endpoints que no requieren auth.

La configuración del mock está en `mock/nginx.conf` (ya incluido en el repo). Los valores de los headers se controlan con las variables `MOCK_*` del `.env`.

---

## 10. docker-compose.yml: Template Base

Copiar este template y ajustar según tu stack:

```yaml
# docker-compose.yml
# App: {APP_NAME} | APP_ID: {APP_ID}
# Ver tabla de puertos en README sección 5

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
      - MAESTRO_API_URL=http://maestro-mock:80
      - MAESTRO_INSTANCE_ID=local-dev-${APP_NAME}
      - APP_COMPANY_SLUG=dev-company
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
      # PostgreSQL
      - POSTGRES_DB=${DB_NAME}
      - POSTGRES_USER=${DB_USER}
      - POSTGRES_PASSWORD=${DB_PASSWORD}
      # MySQL (descomentar si usás MySQL, comentar las de arriba)
      # - MYSQL_DATABASE=${DB_NAME}
      # - MYSQL_USER=${DB_USER}
      # - MYSQL_PASSWORD=${DB_PASSWORD}
      # - MYSQL_ROOT_PASSWORD=${DB_PASSWORD}
      # MongoDB (descomentar si usás Mongo, comentar las de arriba)
      # - MONGO_INITDB_DATABASE=${DB_NAME}
      # - MONGO_INITDB_ROOT_USERNAME=${DB_USER}
      # - MONGO_INITDB_ROOT_PASSWORD=${DB_PASSWORD}
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

  # ── Mock del Maestro (simula autenticación) ──
  maestro-mock:
    image: nginx:alpine
    container_name: mock-${APP_NAME}
    restart: unless-stopped
    volumes:
      - ./mock/nginx.conf:/etc/nginx/conf.d/default.conf:ro
    ports:
      - "${MOCK_PORT}:80"
    networks:
      - app-net
    depends_on:
      - app

  # ── Redis (descomentar si tu app lo necesita) ──
  # redis:
  #   image: redis:7-alpine
  #   container_name: redis-${APP_NAME}
  #   restart: unless-stopped
  #   command: redis-server --requirepass ${REDIS_PASSWORD}
  #   networks:
  #     - app-net
  #   healthcheck:
  #     test: ["CMD", "redis-cli", "-a", "${REDIS_PASSWORD}", "ping"]
  #     interval: 10s
  #     timeout: 5s
  #     retries: 5

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

---

## 11. Dockerfile: Requisitos Obligatorios

Todo Dockerfile debe cumplir estos 7 requisitos para ser compatible con el Maestro:

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

# 2. OBLIGATORIO: Copiar solo lo necesario del build
COPY --from=builder /app/dist ./dist
COPY --from=builder /app/node_modules ./node_modules

# 3. OBLIGATORIO: Directorio para archivos persistentes
RUN mkdir -p /app/storage && chown appuser:appgroup /app/storage
VOLUME /app/storage

# 4. OBLIGATORIO: Puerto interno fijo (el mapping externo lo hace docker-compose)
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
.claude/
docker-compose*.yml
mock/
.DS_Store
__pycache__
.pytest_cache
```

---

## 12. maestro.yaml: Contrato de Integración

Cada fork debe tener un `maestro.yaml` en la raíz:

```yaml
name: "inventario"
version: "0.1.0"
description: "Sistema de inventario"
category: "inventario"
app_id: 1

tech_stack: "node-express"

requires:
  database: "postgres"
  frontend: true
  ports:
    app: 3000

health:
  endpoint: "/health"
  interval: "30s"
  timeout: "5s"

auth:
  mode: "header"
  headers:
    user_id: "X-Auth-User-Id"
    email: "X-Auth-User-Email"
    company_id: "X-Auth-Company-Id"
    roles: "X-Auth-Roles"
    permissions: "X-Auth-Permissions"

ui:
  tailwise: true
  theme: "echo"
  version_used: "React Version - v1.0.9"
  # Si tailwise: false, documentar el motivo:
  # reason: "App sin frontend, solo API REST"

env:
  required:
    - DATABASE_URL
    - MAESTRO_API_URL
    - MAESTRO_INSTANCE_ID
    - APP_COMPANY_SLUG

resources:
  memory: "512m"
  cpu: "0.5"

lifecycle:
  migrate: "npm run migrate"
  start: "npm start"
```

---

## 13. Variables de Entorno (.env)

Al crear tu fork, copiá `.env.example` a `.env` y ajustá los valores:

```bash
cp .env.example .env
```

El archivo `.env.example` está documentado con todos los valores posibles y sus defaults. Nunca modifiques `.env.example` sin actualizar también este README.

Las variables están organizadas en bloques:

- **APP**: Identificación y puertos de la app
- **DB**: Motor, credenciales y configuración de base de datos
- **MOCK**: Datos del usuario simulado para desarrollo
- **REDIS**: Configuración opcional de Redis
- **TAILWISE**: Theme y versión del sistema de diseño

Ver el archivo `.env.example` para la referencia completa.

---

## 14. Flujo de Desarrollo

```
1. FORK
   └─ Hacer fork del repo principal a tu cuenta/org

2. SETUP
   └─ cp .env.example .env
   └─ Editar .env: asignar APP_ID, APP_NAME, elegir DB engine
   └─ Crear: maestro.yaml, Dockerfile, docker-compose.yml, app/
   └─ Copiar assets de Tailwise según tu stack

3. DESARROLLAR
   └─ git checkout -b develop
   └─ docker compose up -d
   └─ Con auth mock: http://localhost:{MOCK_PORT}  (ej: 9100)
   └─ Sin auth (debug): http://localhost:{APP_PORT}  (ej: 3100)
   └─ Usar los comandos agénticos de .claude/ para guiar el desarrollo

4. TESTEAR
   └─ docker compose exec app <test-command>
   └─ Health check responde 200 en /health
   └─ Auth middleware rechaza 401 sin headers
   └─ Auth middleware acepta con headers del mock

5. PROPONER CAMBIOS
   └─ Push a fork/develop
   └─ Crear PR: fork/develop → principal/app-{nombre}
   └─ Esperar review del administrador

6. MERGE + CI/CD
   └─ Administrador revisa y mergea
   └─ CI/CD construye imagen Docker
   └─ Maestro registra y despliega
```

---

## 15. Despliegue: Del Fork a Producción

```
TU FORK (desarrollo)              REPO PRINCIPAL                PRODUCCIÓN

fork/develop ──PR──► principal/app-{nombre} ──CI/CD──► ghcr.io/org/app-{nombre}:sha
                            │                                     │
                     Admin aprueba                          Maestro registra
                                                            y despliega
                                                                │
                                                         ┌──────┴──────┐
                                                         │ Instancia   │
                                                         │ empresa-A   │
                                                         │ + DB propia │
                                                         └─────────────┘
```

En producción, tu `docker-compose.yml` **no se usa**. El Maestro se encarga de todo: descarga la imagen, crea red aislada, provisiona BD, levanta el contenedor con las variables correctas, registra la ruta en Traefik con ForwardAuth.

---

## 16. Checklist Pre-PR

```
ESTRUCTURA
[ ] maestro.yaml existe con app_id asignado
[ ] Dockerfile cumple los 7 requisitos obligatorios
[ ] docker-compose.yml levanta la app completa con docker compose up -d
[ ] .dockerignore excluye Tailwise Bundle/, framework-agentico/, .env
[ ] .env.example actualizado con todas las variables usadas

PUERTOS Y REDES
[ ] Puertos corresponden al APP_ID asignado (ver tabla sección 5)
[ ] Red Docker tiene nombre único: app-{nombre}-net
[ ] Volúmenes tienen nombre único: {nombre}-db-data, {nombre}-storage
[ ] DB no expone puerto al host sin DB_EXPOSE_PORT=true

AUTENTICACIÓN
[ ] Middleware de auth lee X-Auth-* headers
[ ] Middleware rechaza 401 sin headers
[ ] Tests de auth pasan

HEALTH
[ ] GET /health retorna 200 con {"status":"ok"}
[ ] GET /health NO requiere autenticación
[ ] HEALTHCHECK en Dockerfile funciona

UI
[ ] Tailwise integrado según sección 3 (o excepción documentada en maestro.yaml)
[ ] Se usa un solo theme de Tailwise en toda la app
[ ] Los componentes de Tailwise se copiaron a app/, no se editaron los originales

SEGURIDAD
[ ] No hay .env en el repo
[ ] No hay credenciales hardcodeadas
[ ] No hay tablas de users/sessions/auth en migraciones
[ ] Dockerfile usa USER no-root

INTEGRIDAD DEL REPO
[ ] No se modificó framework-agentico/
[ ] No se modificaron archivos dentro de Tailwise Bundle/
[ ] CLAUDE.md tiene la sección inmutable intacta
[ ] Versión en maestro.yaml incrementada
```

---

## 17. Troubleshooting

### "Puerto en uso" al levantar docker compose

Otro fork o servicio está usando el mismo puerto:
```bash
lsof -i :3100            # Ver qué usa el puerto
docker ps -a             # Ver todos los contenedores
docker compose down      # Apagar el otro stack primero
```
Cada fork tiene un `APP_ID` único. Verificá que tu `.env` tenga los puertos correctos según la tabla de la sección 5.

### "Mi app no recibe los headers de auth"

1. Verificá que estás accediendo vía el mock (`localhost:9100`), no directo (`localhost:3100`).
2. Verificá que tu middleware lee los headers con guiones: `X-Auth-User-Id`, no underscores.
3. En PHP/Django, los headers se transforman: `X-Auth-User-Id` se convierte en `HTTP_X_AUTH_USER_ID`.
4. Verificá que `mock/nginx.conf` tiene `proxy_pass http://app:{APP_INTERNAL_PORT}` con el puerto correcto.

### "Quiero levantar 2 apps al mismo tiempo"

Cada app tiene puertos distintos, así que no hay conflicto:
```bash
# Terminal 1: inventario (APP_ID=1)
cd fork-inventario && docker compose up -d
# App: 3100, Mock: 9100

# Terminal 2: facturación (APP_ID=2)
cd fork-facturacion && docker compose up -d
# App: 3200, Mock: 9200
```

### "¿Cómo conecto mi app con otra app del Maestro?"

En desarrollo local, no conectás. Cada app es autónoma.
En producción, usás el API Gateway del Maestro:
```
GET https://maestro.tudominio.com/api/gateway/{otra-app}/endpoint
```
Nunca conectás directamente entre contenedores.

### "¿Cómo uso un componente de Tailwise?"

1. Identificá tu stack (React, Vue, Laravel, HTML)
2. Buscá el componente en `Tailwise Bundle/{tu-version}/Source/`
3. Copialo a tu `app/src/components/` o `app/resources/views/components/`
4. Adaptalo a tu lógica de negocio
5. Nunca edites el original en `Tailwise Bundle/`

### "Mi stack no es compatible con Tailwise"

Documentá el motivo en `maestro.yaml` con `ui.tailwise: false` y `ui.reason`. Tu app será aceptada pero deberá mantener una apariencia profesional y consistente con el resto de la plataforma en la medida de lo posible.
