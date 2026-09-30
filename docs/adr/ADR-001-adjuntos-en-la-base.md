# ADR-001 — Adjuntos en la base, sin volumen de storage

- **Estado:** aceptado
- **Fecha:** 2026-09-30

## Contexto

El Inventario de producción guarda los adjuntos de cada activo (facturas, fotos, remitos; máximo 10 MB cada uno)
en una carpeta del disco. Los documentos del template no coinciden sobre cómo resolver eso en el contenedor:

- `README.md` §12 y §17 piden un volumen `/app/storage` y un volumen `{nombre}-storage`.
- `docs/CONVENCIONES_PLATAFORMA.md` §4.2, que es **normativo**, dice: *"Apps huésped no pueden solicitar
  volúmenes custom al Maestro v2"* y *"Filesystem del contenedor de app es efímero — todo estado persistente va a
  la BD o a blob storage externo"*.

Según la precedencia de `AGENTS.md` §7 y de `APP_HUESPED_SPEC.md` §0, CONVENCIONES tiene más jerarquía que el
README (este último entra como convención local del fork).

## Decisión

El contenido de los adjuntos se guarda en la tabla `adjuntos`, columna `contenido` (`bytea` en PostgreSQL). La
columna es *deferred* para que al listar no se carguen los binarios. La imagen no declara `VOLUME`, los compose no
montan storage y el contenedor corre con `read_only: true`, con `/tmp` como tmpfs.

## Consecuencias

- La app no depende de un volumen que el Maestro no va a provisionar, y el backup de la base incluye los adjuntos.
- La base crece con los adjuntos. Con el límite de 10 MB por archivo y el volumen actual de uso, se considera
  aceptable. Si creciera mucho, la alternativa que admite CONVENCIONES es un blob storage externo.
- Esto se aparta del README §12/§17 (volumen `storage`), y queda documentado acá para la evaluación.
