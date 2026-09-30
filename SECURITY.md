# Seguridad — Inventario LLYA v2

## Reportar una vulnerabilidad

No abras un issue público. Avisale al equipo de TI del estudio por el canal interno de soporte, con la descripción,
los pasos para reproducirla y el impacto que estimás.

## Qué hace la app

- Login propio: bcrypt (cost ≥ 12); política de passwords de 12 caracteres o más, con complejidad y blacklist;
  bloqueo de 15 min tras 5 fallos; 5 intentos/min por IP y 10/h por email.
- Sesión: access token JWT de 15 min en memoria; refresh rotativo en cookie `HttpOnly` + `SameSite=Strict`; detección
  de reuso de refresh; revocación en logout, cambio de password o desactivación.
- Autorización por permisos, verificada en el backend en cada endpoint.
- Audit log inmutable (trigger en la base) con usuario, IP, user-agent y `request_id`.
- Logs JSON sin secretos; cabeceras de seguridad (CSP, nosniff, frame DENY, HSTS bajo HTTPS).
- Secretos solo por variables de entorno; Gitleaks sobre el historial; imagen no-root, filesystem read-only y bases
  fijadas por digest.

El detalle está en [`docs/inventario/02-threat-model.md`](docs/inventario/02-threat-model.md).

## Ambientes sin TLS

Test y Preprod en Dokploy corren sobre HTTP. **No cargues datos reales** en esos ambientes (MANUAL §0.1).
