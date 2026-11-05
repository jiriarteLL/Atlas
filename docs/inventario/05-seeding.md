# Atlas — Seeding (fase 05-seeding)

## Qué hace

`app/backend/seed.py` corre en **cada arranque** del contenedor (`docker-entrypoint.sh`), después de esperar a la
base y antes de levantar la app. Es idempotente:

1. Valida `SUPERADMIN_INITIAL_PASSWORD`. Si falta o es débil (menos de 12 caracteres, menos de 3 clases de
   caracteres, en la blacklist o con el texto de ejemplo "cambiar"), **sale con código 1 sin crear nada** y el
   contenedor no arranca.
2. Crea las tablas que falten y el trigger de audit inmutable (`init_db`).
3. Crea o completa los roles (`superadmin`, `admin`, `editor`, `viewer`), los 5 permisos y sus relaciones, sin
   borrar nada.
4. Si `admin@llyasoc.com` no existe, lo crea con rol `superadmin` y `debe_cambiar_password = true`. Si existe y no
   tiene el rol, se lo asigna **sin tocar la password**. Si existe con el rol, no hace nada.

Los logs no muestran la password ni el hash: solo `[seed] superadmin admin@llyasoc.com: creado | ya existia...`.

## Decisiones (02-seeding-plan)

| Decisión | Valor | Quién decide |
|---|---|---|
| Email del superadmin | `admin@llyasoc.com` (canónico) | Framework (no se cambia) |
| Usuarios adicionales (`seeding.additional_users`) | Ninguno (`[]`). Los usuarios se crean desde Configuración. | PO (confirmado 2026-09-30) |
| Cambio de password inicial | Obligatorio en el primer ingreso. Lo exige la UI, no la API, para no romper el smoke del Gate 2. | Implementado |

## Tests (README §10: los 6 obligatorios)

`app/tests/test_seeder.py`:

1. Sin la variable → falla.
2. Password débil → falla (5 casos).
3. Primera corrida → superadmin con todos los permisos.
4. Segunda corrida → no duplica ni cambia la password.
5. Existía sin rol → recibe el rol sin tocar la password.
6. Login con la password de la variable → 200.

A eso se suma que el superadmin sembrado queda marcado para cambiar la password.

## En el pipeline

Como el seeder corre en el entrypoint, cualquier deploy (Dokploy, o el provisioning del Maestro) lo ejecuta después
de las migraciones sin un paso aparte. `herramientas/vm-ensayo/ensayo.sh` verifica que un reinicio no cambie la
password (idempotencia en runtime).
