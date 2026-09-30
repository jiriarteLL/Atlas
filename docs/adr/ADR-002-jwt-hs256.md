# ADR-002 — JWT firmado con HS256

- **Estado:** aceptado (a revisar por el evaluador)
- **Fecha:** 2026-09-30

## Contexto

`docs/APP_HUESPED_BEST_PRACTICES.md` §2.4 (no normativo) recomienda "RS256 o EdDSA. NO HS256". Por otro lado,
`docs/APP_HUESPED_SPEC.md` §2.9 y `CONVENCIONES_PLATAFORMA.md` §6.1 (normativos) definen como variable que inyecta el
Maestro `APP_KEY` o `JWT_SECRET`, "secret para firmar tokens propios": un secreto simétrico, no un par de claves.

## Decisión

Los access tokens se firman con HS256 usando `JWT_SECRET`. Solo la app los emite y los verifica: ningún tercero
necesita validarlos, que es el caso en el que una clave asimétrica tiene sentido.

## Consecuencias

- Se respeta el contrato de variables del Maestro, que tiene más jerarquía que la guía de buenas prácticas.
- Si alguna vez otro servicio tuviera que validar estos tokens, habría que pasar a EdDSA y publicar la clave
  pública. Hoy no aplica.
- El riesgo de HS256 (que se filtre `JWT_SECRET`) se acota así: tokens de 15 min, rotación documentada en el runbook
  y secreto nuevo por ambiente.
