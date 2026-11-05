# Atlas — Threat model (fase 02-planning)

Modelo STRIDE simplificado sobre los flujos de `02-arquitectura.md`. Donde dice "Pendiente", el control depende de
la infraestructura o de una decisión humana.

## Activos a proteger

Credenciales y sesiones de los usuarios; el inventario (qué equipo tiene cada persona, su IP, su software y su
estado de seguridad: una lista muy útil para un atacante); los adjuntos (facturas, remitos); las claves compartidas
`MAESTRO_API_KEY`, `SYNC_API_KEY` y `JWT_SECRET`.

## Amenazas y controles

| # | Amenaza (STRIDE) | Vector | Control | Estado |
|---|---|---|---|---|
| T1 | Suplantación de usuario (S) | Fuerza bruta o *credential stuffing* en `/login` | bcrypt ≥ 12; 5/min por IP; 10/h por email; bloqueo de 15 min tras 5 fallos; blacklist de 1.200 passwords comunes; mensaje único | Hecho |
| T2 | Robo de sesión (S) | XSS que lea el token | Access en memoria (no en localStorage) y de 15 min; refresh en cookie HttpOnly; CSP `script-src 'self'`; React escapa por defecto | Hecho |
| T3 | Reuso de un refresh robado (S) | Cookie filtrada | Rotación en cada uso; si se reusa uno rotado, se revocan todas las sesiones y queda en el audit (`REFRESH_REUSE`) | Hecho |
| T4 | CSRF (T) | Sitio ajeno que dispara `/auth/refresh` | `SameSite=Strict`, `Path=/auth` y header `X-Requested-With` obligatorio | Hecho |
| T5 | Agente falso que inyecta datos (T/S) | `POST /api/sync` | `X-Sync-Key` comparada en tiempo constante; sanitizado de caracteres de control; límite de 8 MB | Hecho. La clave es una sola para todos los agentes: ver deuda técnica DT-03 |
| T6 | Escalada de privilegios (E) | Un viewer o editor llama endpoints de admin | Permisos verificados en el backend en cada endpoint; tests por rol | Hecho |
| T7 | Enumeración de usuarios (I) | Diferencias de respuesta o de tiempo en el login | Mismo mensaje; se verifica contra un hash señuelo cuando el usuario no existe | Hecho |
| T8 | Path traversal (I/T) | Adjuntos, archivos estáticos | Adjuntos en la base; id de activo validado por regex; estáticos resueltos con `realpath` dentro de su carpeta | Hecho |
| T9 | Subida de archivos maliciosos (T) | Adjuntos | Whitelist de extensiones, 10 MB, descarga como `attachment` con `nosniff` | Hecho. Sin antivirus: DT-04 |
| T10 | Fuga de secretos en logs (I) | Logs de requests o errores | Logs JSON sin query string ni headers; tapado de tokens y passwords; test automático | Hecho |
| T11 | Manipulación del audit (R) | UPDATE/DELETE sobre `audit_log` | Trigger en la base que lo rechaza | Hecho |
| T12 | Secretos en el repo o la imagen (I) | Commits, capas de Docker | Gitleaks (0 hallazgos en commits de la app); `.dockerignore`; secretos solo por ENV | Hecho. Hay 31 hallazgos heredados del template (decisión del evaluador) |
| T13 | Tráfico en claro (I) | Test/Preprod en HTTP | Aviso de "sin datos reales"; `COOKIES_SEGURAS=false` solo en esos ambientes | **Pendiente: HTTPS** |
| T14 | Vulnerabilidades de dependencias (E) | Imagen y paquetes | Versiones fijadas, digests de imágenes, Trivy en CI | **Pendiente: primer escaneo con Docker** |
| T15 | Denegación de servicio (D) | Payloads grandes, login | Límites de tamaño (8 MB sync, 10 MB adjuntos); rate limit; límites de CPU y memoria en compose | Parcial: el rate limit es en memoria, por proceso (DT-02) |
| T16 | Clickjacking (T) | iframe ajeno | `X-Frame-Options: DENY`, `frame-ancestors 'none'` | Hecho |
| T17 | XSS por URI guardada (T) | `javascript:` o `data:` en los links de un proyecto | El backend acepta solo `http(s)://` y el frontend solo usa como `href` URLs `http(s)` (`urlSegura`) | Hecho (validación transversal) |
| T18 | HTML inyectado en mails (T) | Nombre de proyecto o tarea con HTML | Los valores de usuario se escapan con `html.escape` antes de armar el mail | Hecho (validación transversal) |
