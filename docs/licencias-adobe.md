# Licencias en Atlas

Atlas → **Licencias**: productos contratados, quién los tiene, cupos, costos (por producto, persona, centro de costo y
mes) y renovaciones.

## Qué se carga solo

Solo el **catálogo** de productos contratados (lo hace `seed.py` al arrancar Atlas-HTTP; idempotente por
proveedor + producto: no duplica ni pisa lo que ya exista). **Sin costos, sin personas, sin asignaciones.**

| Proveedor | Producto | Plan | Cupo |
|---|---|---|---|
| Anthropic | Claude Team Standard | Team | (vacío) |
| Anthropic | Claude Team Premium | Team | (vacío) |
| Anthropic | Claude Max 20x | Max 20x | (vacío) |
| Adobe | Creative Cloud Pro | Teams | 4 |
| Adobe | Illustrator | Teams | 4 |
| Adobe | Photoshop | Teams | 1 |
| Adobe | Premiere Pro | Teams | 4 |
| Adobe | Acrobat Premium para equipos | Teams | 66 |

## Costos

En la tabla de productos se editan directo: **precio por licencia en USD y/o ARS**, **periodicidad** (mensual o
anual), **cupo** y **renovación**. Ninguna importación los pisa.

- Costo mensual de una licencia = precio (mensual) o precio / 12 (anual).
- Costo del producto = licencias contratadas (cupo) × costo mensual. Sin cupo cargado: licencias en uso.
  Los planes Team cobran un precio fijo por asiento: costo = asientos × precio.
- Sin asignar = (contratadas − en uso) × costo mensual de una licencia.
- Por persona = suma de sus productos (una licencia compartida cuenta la mitad para cada uno).
- Por centro de costo: asignación individual → centro de costo de la persona; licencia compartida → su centro de
  imputación (o su %), si no mitad a cada centro de las dos personas; cuenta de equipo → su unidad; lo libre →
  "sin asignar".
- Las monedas no se convierten: los totales se muestran por moneda.
- **Costos por mes**: el costo real de cada mes (lo que dice la factura) se carga a mano (origen "manual"); cuando
  haya API con costos, el conector los cargará con origen "api" (sin pisar lo manual).

## Personas y asignaciones

- **Planes Team sin API**: Adobe Teams no tiene User Management API y Claude Team no tiene Admin / Analytics API
  (son de Enterprise). Las asignaciones van por carga manual (ficha del producto → Asignar) o con
  **Importar miembros**:
  - **CSV de miembros** (Claude, Adobe u otro): columnas por nombre, en inglés o castellano: `email` (obligatoria),
    nombre, producto / seat tier, proveedor. Si el archivo no dice el producto, se elige en la ventana.
    "Premium" / "Standard" en la columna seat tier se asignan a "Claude Team Premium" / "Claude Team Standard".
  - **Exportación de usuarios de la Admin Console de Adobe** (adminconsole.adobe.com → Usuarios → "…" → Exportar
    lista de usuarios a CSV): formatos Enterprise (`Product Configurations`) y Teams (`Products`).
  - **UserManager** (JSON): ver abajo.
- Lo que deja de venir en una importación queda **liberado** con su fecha (no se borra).
- Alertas: licencias de personas **de baja** en la nómina o con cuenta deshabilitada (AD / Adobe), licencias sin
  asignar, renovaciones en 60 días (`LICENCIAS_RENOVACION_DIAS`), más en uso que contratadas, productos sin precio.

## UserManager (preparado, no importado)

- `herramientas/licencias/exportar_usermanager.py --base C:\UserManager\usermanager.db --salida um.json`
  abre la base **solo en lectura** y genera un JSON (licencias, asignaciones, empleados, pares de Adobe, cuentas de
  equipo de Claude). El JSON lleva datos de la nómina: tratarlo como confidencial y borrarlo después.
- Importación: Licencias → Importar miembros → "Exportación del UserManager (JSON)", o en la VM
  `importar_usermanager.py um.json [--probar]` (con `--probar` no guarda nada). Idempotente (upsert por los ids del
  UserManager), no pisa costos ni cupos cargados en Atlas.

## Conectores por API (para cuando el plan los tenga)

- **Adobe User Management API** (solo Enterprise): credencial OAuth Server-to-Server en developer.adobe.com
  (Crear proyecto → Agregar API → User Management API → OAuth Server-to-Server). Variables en `C:\Atlas\.env`:
  `ADOBE_CLIENT_ID`, `ADOBE_ORG_ID` (@AdobeOrg), `ADOBE_SECRET_ARCHIVO=C:\Atlas\secretos\adobe-secret.txt`
  (ACL: SYSTEM, Administradores y `TANGO\servicio-inventario` lectura). Opcional `LICENCIAS_CADA_HORAS` (24).
  Solo lee; nunca asigna ni saca licencias.
- **Anthropic** (Admin / Analytics API, solo Enterprise): preparado el modelo (costos por mes con origen "api",
  workspace) y `ANTHROPIC_ADMIN_KEY_ARCHIVO`; la llamada todavía no está implementada (faltan los endpoints
  confirmados). No corre nunca hasta implementarlo.
