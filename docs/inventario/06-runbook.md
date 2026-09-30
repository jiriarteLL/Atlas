# Inventario LLYA v2 — Runbook operativo (fase 06-operations)

> Aplica a Test y Preprod en Dokploy. Producción la opera el Maestro v2 con su propio runbook.

## Arranque y salud

| Qué | Cómo | Esperado |
|---|---|---|
| ¿Está viva? | `curl -s http://<host>:<puerto>/health` | `{"status":"ok"}` en menos de 3 s |
| ¿Contenedores OK? | Dokploy → `docker.getContainersByAppNameMatch` (MANUAL §6.1) | `app-inventario-*` y `db-inventario-*` en `running (healthy)` |
| ¿Arrancó el seeder? | Logs de la app | `[seed] superadmin admin@llyasoc.com: ...` antes de `app.start` |
| ¿Métricas? | `curl -H "X-Maestro-Api-Key: …" …/metrics` | Texto Prometheus |

## Problemas frecuentes

| Síntoma | Causa probable | Qué hacer |
|---|---|---|
| El contenedor se reinicia en loop y el log muestra `[seed] ERROR` | `SUPERADMIN_INITIAL_PASSWORD` falta o es débil | Cargar una password válida en las variables del ambiente y redesplegar |
| `Falta la variable de entorno obligatoria …` | Faltan `DATABASE_URL` o `JWT_SECRET` | Revisar `createEnvFile: true` y las variables (MANUAL §5.3) |
| `[entrypoint] la base no respondio en 60s` | La DB no levantó o `DB_PASSWORD` no coincide con el volumen | Ver los logs de `db-inventario-*`. Si se regeneraron los secretos, Postgres conserva la password vieja: hay que borrar el volumen (MANUAL §5.0, trampa 3) |
| El login vuelve siempre a la pantalla de login | Cookie `Secure` sobre HTTP | `COOKIES_SEGURAS=false` en ambientes HTTP (MANUAL §6.4) |
| 401 al renovar la sesión cada ~15 min | Hora del servidor desfasada, o `sesiones_desde` posterior (cambio de password) | Revisar NTP; volver a iniciar sesión |
| Un usuario no puede entrar aunque la password es correcta | Cuenta bloqueada 15 min por 5 fallos | Esperar, o que un admin le resetee la password. El evento `ACCOUNT_LOCKED` queda en el audit. |
| Los agentes dan 401 | `SYNC_API_KEY` distinta entre el agente y el ambiente | Reinstalar el agente con la clave del ambiente |
| El `logo_url` del branding apunta a `:8000` | Proxy sin `APP_URL` ni `FORWARDED_ALLOW_IPS` | Definir `APP_URL` con la URL pública |

## Tareas

- **Rotar `MAESTRO_API_KEY`** (cada 90 días): cambiar la variable y redesplegar. El Maestro tiene que usar la nueva.
- **Rotar `JWT_SECRET`:** cambiarla y redesplegar. Todos los access tokens vigentes dejan de valer, los usuarios
  renuevan con el refresh y no pierden la sesión.
- **Cortar todas las sesiones de un usuario:** desactivarlo, o resetearle la password desde Configuración.
- **Forzar un snapshot de Tendencias:** `POST /api/tendencias/snapshot` como admin.
- **Backup:** volumen `inventario*_pgdata` con `pg_dump`. Incluye los adjuntos (ADR-001).

## Cambios de esquema (Alembic)

Las migraciones están en `app/backend/migrations/versions/` y se aplican solas en cada arranque (`seed.py` →
`init_db()` → `alembic upgrade head`). Para cambiar un modelo:

1. Modificar el modelo en `database.py` o `auth.py`.
2. Generar la migración contra una base temporal **ya migrada** (si está vacía, Alembic genera todo el esquema de nuevo):
   ```
   cd app/backend
   export DATABASE_URL=sqlite:///tmp.db JWT_SECRET=x
   alembic upgrade head
   alembic revision --autogenerate --rev-id 0002 -m "descripcion"
   rm tmp.db
   ```
3. **Revisarla a mano** (renombres, datos, triggers: Alembic no los detecta).
4. `pytest app/tests`: `test_el_esquema_migrado_coincide_con_los_modelos` falla si el modelo y las migraciones no
   coinciden.

Para volver atrás: `alembic downgrade -1`, hecho a mano y con backup previo de la base.

## Logs

JSON por stdout. Cada request deja un evento `http.request` con `request_id`, `user_id`, `method`, `path`,
`status` y `duration_ms` (el `/health` en 200 no se loguea). Para seguir un problema, buscar el `request_id`, que el
cliente recibe en la cabecera `X-Request-Id` y queda también en el `audit_log`.
