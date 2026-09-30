# Inventario LLYA v2 — Requisitos (fase 01-discovery)

> **Estado:** borrador armado por análisis del código existente. **La priorización MoSCoW la tiene que validar el
> Product Owner** (01-discovery, exit criterion "Priorización validada").
> **Fuente:** Inventario LLYA v3.4 en producción (Windows/NSSM/SQLite), adaptado al contrato `maestro.platform/v2`.

## 1. Propósito

Registrar y seguir los activos de TI del estudio (notebooks, CPU, monitores, impresoras, servidores, switches, UPS):
a quién están asignados, en qué sede están, su estado, su garantía y su relevamiento técnico automático. Sumar a eso
el seguimiento de los proyectos de IT y sus tareas.

## 2. Alcance de esta versión

| En alcance | Fuera de alcance (v2.0.0) |
|---|---|
| Activos (ABM, ficha, historial de cambios, adjuntos, QR) | Licencias (Claude, Adobe, etc.): dependían del UserManager |
| Relevamiento automático por agentes (PowerShell, Linux, GLPI) | Nómina / Usuarios de RRHH y alta ABM de empleados |
| Garantías (consulta Lenovo, vencimientos a 90 días) | Sincronización con el Excel de stock local |
| Proyectos de IT y tareas | Integración directa con otras apps (se hará vía API Gateway del Maestro) |
| Reportes y tendencias (snapshots semanales) | |
| Usuarios de la app, roles y permisos | |

> El repo se llama `32_registro_activos_licencia_impresoras`, pero Licencias queda **fuera** de esta versión
> porque vive en el UserManager (otra app). **Alcance confirmado por el PO el 2026-09-30.**

## 3. Requisitos funcionales (MoSCoW propuesto)

| ID | Requisito | Prioridad | Criterio de aceptación |
|---|---|---|---|
| RF-01 | Login propio con usuario o email y contraseña | Must | `POST /login` 200 con credenciales válidas, 401 con inválidas (test `test_auth.py`) |
| RF-02 | Roles admin / editor / viewer y superadmin | Must | viewer no puede escribir (403); editor no elimina activos; admin administra usuarios |
| RF-03 | ABM de activos con validación de tipo, estado, serial, marca y modelo | Must | Alta sin marca/modelo/serial → 422; edición registra historial por campo |
| RF-04 | Historial de cambios por activo (usuario, campo, antes, después) | Must | Cada edición o sync deja una fila por campo cambiado |
| RF-05 | Sincronización automática desde agentes con clave (`X-Sync-Key`) | Must | Sin clave o con clave inválida → 401; mismo serial actualiza, no duplica |
| RF-06 | Ingesta de inventario GLPI (JSON o gzip) con resumen de seguridad | Should | EDR, cifrado, batería, acceso remoto visibles en la ficha |
| RF-07 | Adjuntos por activo (pdf, imágenes, office, txt/csv; 10 MB máx.) | Should | Extensión no permitida o > 10 MB → 400 |
| RF-08 | Consulta de garantía Lenovo y listado de vencimientos a 90 días | Should | Solo equipos Lenovo; error del portal → 422 con mensaje |
| RF-09 | Proyectos de IT con responsables, activos vinculados y tareas | Should | Avance calculado por tareas realizadas |
| RF-10 | Notificación por mail al finalizar un proyecto | Could | Sin SMTP configurado no falla; solo no envía |
| RF-11 | Reportes (por sede, tipo, estado) exportables a Excel | Should | Exporta la vista filtrada |
| RF-12 | Tendencias: snapshot semanal de métricas del inventario | Could | Snapshot automático cada `SNAPSHOT_DIAS`; forzable por admin |
| RF-13 | Importar/exportar CSV de activos | Could | Solo con permiso de edición |
| RF-14 | Tickets simples por activo | Won't (esta versión: solo API) | La UI actual no los expone |

## 4. Requisitos no funcionales

| ID | Requisito | Fuente | Verificación |
|---|---|---|---|
| RNF-01 | Contrato `maestro.platform/v2` (health, branding, seeding, auth propia) | SPEC §2 | Tests de contrato + schema v2 |
| RNF-02 | Single-tenant físico: sin `company_id` | SPEC §2.5 | `test_estatico.py` |
| RNF-03 | Passwords bcrypt cost ≥ 12, política ≥ 12 caracteres + blacklist | SPEC §2.4.1 | `test_auth.py` |
| RNF-04 | Access token ≤ 15 min + refresh rotativo en cookie HttpOnly | SPEC §2.4.2, Premisa 7 | `test_auth.py` |
| RNF-05 | Rate limit de login 5/min por IP, 10/h por email, bloqueo tras 5 fallos | BEST_PRACTICES §5.4, 03 | `test_auth.py` |
| RNF-06 | Logs JSON a stdout con `request_id`/`user_id`, sin secretos | CONVENCIONES §10 | `test_logs_json_sin_secretos` |
| RNF-07 | Imagen ≤ 500 MB, no-root, HEALTHCHECK, sin secretos | SPEC §2.2 | Gate 1 (pendiente: Docker) |
| RNF-08 | Sin CRITICAL/HIGH en Trivy | IN-006 | Gate 1 (pendiente: Docker) |
| RNF-09 | Health ≤ 5 s, ≥ 99 % en 100 polls | SPEC §2.3, Gate 2 | `ensayo.sh` (pendiente: VM) |
| RNF-10 | Recursos: 512 MB / 0.5 CPU | `maestro.yaml` | Gate 2 |
| RNF-11 | Filesystem efímero: estado solo en la base | CONVENCIONES §4.2 | ADR-001 |
| RNF-12 | Interfaz en español rioplatense | Convención local | Revisión manual |

## 5. Restricciones

- Sin dependencia del UserManager ni de otras apps (README §4, "aislamiento total").
- Sin IPs, puertos, rutas de Windows ni secretos en el código (README §7).
- Test y Preprod corren sobre HTTP: **no se cargan datos reales** hasta que haya HTTPS (MANUAL §0.1).

## 6. Glosario

| Término | Significado |
|---|---|
| **Activo** | Equipo de TI inventariado, identificado por su número de serie. |
| **Ficha** | Vista de detalle de un activo: identificación, hardware, seguridad, asignación, software, adjuntos, historial. |
| **Sede** | Oficina del estudio (CABA, Rosario, Córdoba, Corrientes, Mendoza, Neuquén, Tigre, Resguarda). |
| **Nomenclatura** | Nombre del equipo según la convención del estudio (prefijo de sede + área + número, ej. `MAUDIT0004`). |
| **Agente** | Script que corre en el equipo y reporta su inventario a `POST /api/sync`. |
| **GLPI** | Agente de inventario GLPI; reporta a `POST /api/sync-glpi` un JSON más completo (antivirus, cifrado, batería). |
| **Sync key** | Clave compartida (`SYNC_API_KEY`) que autentica a los agentes. |
| **Snapshot** | Foto de las métricas del inventario en una fecha, base de Tendencias. |
| **Superadmin** | `admin@llyasoc.com`, creado por el seeder con todos los permisos. |
| **Permiso** | Capacidad atómica (`inventario.ver`, `inventario.editar`, `activos.eliminar`, `garantias.consultar`, `usuarios.administrar`). |
| **Rol** | Conjunto de permisos (`superadmin`, `admin`, `editor`, `viewer`). |
