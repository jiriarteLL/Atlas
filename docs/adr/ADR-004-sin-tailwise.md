# ADR-004 — Se mantiene el sistema de diseño propio (sin Tailwise)

- **Estado:** aceptado (a revisar por el evaluador)
- **Fecha:** 2026-09-30

## Contexto

README §3: Tailwise es el camino preferido, y "solo se permite omitirlo cuando hay un impedimento técnico
documentado", declarándolo en `maestro.yaml` con `ui.tailwise: false` y `ui.reason`. La app ya existe y tiene su
propio sistema de diseño (`styles.css`, con modos y colores por variables CSS), que usan los usuarios del estudio.

## Decisión

Se mantiene el sistema propio y se declara `ui.tailwise: false` con su motivo.

## Consecuencias

- La app no queda visualmente alineada con el resto de las apps de la plataforma.
- Pasar a Tailwise React v1.0.9 implica rehacer todas las pantallas: es trabajo aparte, que el PO puede decidir en
  una versión futura. Mientras tanto, los componentes nuevos no deberían sumar estilos por fuera de las variables
  de `styles.css`.
