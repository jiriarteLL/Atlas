# ADR-003 — La v2 no depende del UserManager

- **Estado:** aceptado por el PO (2026-09-29, "V2 solo con lo propio"; alcance sin Licencias reconfirmado el 2026-09-30)
- **Fecha:** 2026-09-29

## Contexto

En producción, el Inventario consume la API del UserManager (otra app, con su propio backend y su propia base) para
Licencias, Nómina/Usuarios, alta ABM de empleados y parte del Dashboard y los Reportes, y un script lee directamente
la base del UserManager. El README exige que cada app sea autónoma ("Se levanta sin depender del Maestro ni de otros
forks") y que la comunicación entre apps pase por el API Gateway del Maestro.

## Decisión

La v2 incluye solo lo que es propio del Inventario: activos, agentes, garantías, proyectos, reportes, tendencias y
usuarios de la app. Quedan afuera Licencias, Nómina/Usuarios, alta ABM, alertas de nómina, la tarjeta "Empleado
asignado" y los reportes de empleados.

## Consecuencias

- La app se despliega sola, con su base.
- Se pierde, por ahora, la funcionalidad de Licencias, aunque el nombre del repo la menciona. Cuando el API Gateway
  del Maestro exista, se puede volver a integrar con el UserManager, o llevar Licencias a esta app como módulo
  propio (deuda DT-09).
