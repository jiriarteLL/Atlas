# Changelog — Inventario LLYA

## [2.0.0] — 2026-09-29

Primera version como app huesped del contrato `maestro.platform/v2`, en paralelo al Inventario de
produccion (v3.4, servicio NSSM en Windows con SQLite).

### Agregado
- Contenedor Docker (imagen unica: FastAPI sirve el frontend compilado) y tres compose:
  `docker-compose.yml` (dev local), `docker-compose.test.yml` y `docker-compose.preprod.yml`.
- PostgreSQL como base (contenedor propio por ambiente).
- `GET /health` y `GET /maestro/branding` (autenticado con `X-Maestro-Api-Key`).
- Tablas `roles`, `permissions`, `role_permissions` y `user_roles`; permisos por codigo.
- Seeder idempotente del superadmin `admin@llyasoc.com` (falla si la password falta o es debil).
- `POST /auth/logout` que revoca el token; cambio de password y desactivacion invalidan sesiones.
- Politica de passwords (>= 12 caracteres, complejidad, blacklist). Login por usuario o email.
- Snapshot de tendencias automatico dentro de la app y `POST /api/tendencias/snapshot`.
- 62 tests de backend (contrato, auth, seeder, negocio y chequeos estaticos).

### Cambiado
- Toda la configuracion por variables de entorno; sin IPs, puertos, rutas de Windows ni secretos en el codigo.
- Todos los endpoints de `/api` exigen login (antes varios GET eran publicos).
- Rate limit del login: 5 intentos por minuto por IP (antes 10).
- Claves de sincronizacion comparadas en tiempo constante (`hmac.compare_digest`).
- Adjuntos guardados en `/app/storage` con rutas relativas.
- Frontend con rutas relativas (mismo origen) y controles segun permisos.
- Agentes: servidor y clave por parametro; ahora mandan `X-Sync-Key`.

### Quitado (dependian del UserManager o de Windows)
- Secciones Licencias y Usuarios/Nomina, alta ABM, alertas de nomina y reportes de empleados.
- Sincronizacion con el Excel de stock local y scripts sobre SQLite.
