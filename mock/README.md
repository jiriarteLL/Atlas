# mock/ — Estado: LEGACY v3

> Este directorio es **legacy del modelo v3** del framework agentico. **NO se usa en v4.**

---

## Por que esta deprecado

En **framework v3 / contrato `maestro.platform/v1`**, el Maestro era el Identity Provider:

- Traefik ForwardAuth validaba el token contra el Maestro.
- El Maestro inyectaba headers `X-Auth-User-Id`, `X-Auth-User-Email`, `X-Auth-Company-Id`, `X-Auth-Roles`, `X-Auth-Permissions` en cada request.
- La app huesped solo leia esos headers; **no implementaba login**.

Para que el dev pudiera trabajar **sin necesitar al Maestro real corriendo**, este `mock/nginx.conf` simulaba ese flujo: interceptaba el request, agregaba los headers `X-Auth-*` con valores configurables (variables `MOCK_*` del `.env` v3), y reenviaba a la app.

En **framework v4 / contrato `maestro.platform/v2`**, el modelo cambio:

- Cada app huesped tiene su **propio login** (tabla `users`, password con bcrypt/argon2id, tokens propios).
- El Maestro v2 **NO inyecta** headers `X-Auth-*`.
- Cuando un usuario hace click en una app desde el portal del Maestro v2, el portal **abre la URL en `target="_blank"`** y la app pide login con sus credenciales propias.
- Por lo tanto, **NO hay nada que mockear** en dev: simplemente levantas tu app, ejecutas el seeder del superadmin (fase 05-seeding), y te logueas como `admin@llyasoc.com` con `SUPERADMIN_INITIAL_PASSWORD`.

---

## Que hago con `mock/` en mi fork v4?

Tres opciones:

### 1. Borralo (recomendado para apps nuevas v4)

```bash
git rm -rf mock/
```

Y en `docker-compose.yml`, NO declares el servicio `maestro-mock`. Tu stack queda mas simple.

### 2. Mantenelo como referencia historica

Si tu app esta migrando de v3 a v4, podes dejar `mock/` durante la transicion para entender el modelo viejo. Una vez que la migracion termine y los tests pasen, borralo.

### 3. Re-propositalo para mockear `/maestro/branding`

Si tu app expone `/maestro/branding` (obligatorio v4) y queres probarlo localmente sin un Maestro v2 real consumiendolo, podes:

- Reescribir `nginx.conf` para que actue como cliente que envia requests con `X-Maestro-Api-Key` valido contra tu app.
- O usar `curl` directamente:
  ```bash
  curl -H "X-Maestro-Api-Key: $MAESTRO_API_KEY" http://localhost:3100/maestro/branding
  ```

Esta opcion es **opcional** y no esta soportada por el framework. Si la implementas, document tu setup en este README.

---

## Estado actual del archivo

`mock/nginx.conf` (modelo v3): inyecta los siguientes headers a cada request:

- `X-Auth-User-Id: 1`
- `X-Auth-User-Email: dev@empresa-test.com`
- `X-Auth-Company-Id: 1`
- `X-Auth-Roles: admin`
- `X-Auth-Permissions: ["read","write","delete","admin"]`

**Estos headers NO son leidos por apps v4.** Si los recibes en produccion (Maestro v2 NO los emite, pero un proxy mal configurado podria), tu app debe **ignorarlos** y validar con su propio middleware.

---

## Riesgo de seguridad si lo dejas activo en produccion

Si por error queda el servicio `maestro-mock` declarado en un `docker-compose.prod.yml` o si exponen el puerto del mock en produccion:

- El mock inyectaria headers `X-Auth-*` con valores hardcodeados a CUALQUIER request.
- Apps v3 (legacy) que aun lean esos headers quedarian autenticadas como el usuario hardcodeado.
- Apps v4 los ignorarian (correcto), pero igual es ruido innecesario.

**Por eso es preferible borrar `mock/` en apps nuevas v4.** Si lo mantenes, asegurate de que:
- NO se monta en `docker-compose.prod.yml`.
- Su puerto NO se expone en produccion.

---

## Referencias

- `framework-agentico/CHANGELOG.md` — cambios v3 -> v4.
- `framework-agentico/migration/v3-to-v4.md` — proceso de migracion.
- `docs/APP_HUESPED_SPEC_V2.md` — contrato v2 (modelo de auth propio).
- `docs/CONVENCIONES_PLATAFORMA_V2.md` — convenciones v2.
- `README.md` (root del repo) — guia general v4.
