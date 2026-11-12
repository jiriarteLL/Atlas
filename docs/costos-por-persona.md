# Costo por persona (base del módulo de Usuarios)

`GET /api/costos/personas` (permiso Licencias o Activos, solo lectura) devuelve, por persona, el costo **mensual** de
sus licencias y de sus equipos. Todavía no tiene pantalla: es la base para el módulo de Usuarios, que va a cruzar
personas, inventario y licencias para llegar al costo final de cada usuario.

## Quién es "la persona"

- Clave: **email** o **usuario de Windows**, en minúsculas (`TANGO\Ana` → `ana`).
- El usuario de Windows de un equipo se cruza con el mail de las licencias por la parte antes de la `@`
  (`jiriarte` = `jiriarte@llyasoc.com`). Si no hay licencia con ese mail, la persona queda con el usuario de Windows.

## Licencias

- Costo mensual de una licencia = precio cargado en Atlas (USD y/o ARS); si el precio es anual, se divide por 12.
- **Licencia compartida por dos personas**: es UNA asignación con *segundo usuario*. El costo se reparte por
  `porcentaje_principal` (lo que paga el principal); vacío = **50/50** si hay segundo usuario, **100 %** si no.
- Si alguien figura como segundo usuario de una licencia y además tiene su propia asignación del mismo producto (por
  ejemplo, porque viene en el CSV de Adobe), esa propia se marca *duplicada* y no suma otra licencia.
- Centro de costo: el de la **asignación** si está cargado; si no, el de cada persona (nómina del UserManager o, si
  no hay, el del equipo de esa persona en Atlas).
- Segundo usuario, % y centro de la asignación son **datos de Atlas**: ninguna importación los pisa (el CSV de Adobe
  solo trae al principal; el UserManager solo los completa si están vacíos).

## Equipos (notebooks, PC y cualquier activo)

- Costo mensual = **costo de compra / vida útil en meses** (la del equipo o, si está vacía, la de su tipo:
  `VIDA_UTIL_MESES`, por defecto Notebook 48, CPU 60, Monitor 72, Impresora 60, Servidor 60).
- Se reparte igual que las licencias: usuario del equipo y *segundo usuario* (`asset_admin.usuario_secundario`) según
  `porcentaje_principal` (vacío = 50/50 con segundo usuario).
- Sin costo, sin moneda o sin vida útil → **"sin dato"**: el equipo figura en `equipos_detalle` con `sin_dato: true`
  y suma en `equipos_sin_costo`, pero no en el total.
- El segundo usuario y el centro de costo del equipo los carga una persona en la ficha (*Uso y centro de costo*); el
  agente, GLPI, CrowdStrike y las actas nunca los tocan.

## Monedas y centro de costo

- USD y ARS van **separados** (no se convierte).
- Centro de costo: texto libre, normalizado (espacios simples y MAYÚSCULAS). Las sugerencias del campo salen de los
  valores ya usados en Atlas (`GET /api/costos/centros`); no hay tabla maestra todavía.

## Respuesta

```json
[{"persona": "ana@llyasoc.com", "nombre": "Ana", "centro_costo": "CABA 1-AUD EA",
  "licencias": {"USD": 30}, "equipos": {"USD": 50}, "total": {"USD": 80}, "equipos_sin_costo": 0,
  "licencias_detalle": [{"producto": "Claude Team Standard", "proveedor": "Anthropic", "fraccion": 1, "mensual": {"USD": 30}}],
  "equipos_detalle": [{"id": "A1B2C3", "nombre": "NB-0001", "tipo": "Notebook", "fraccion": 0.5, "mensual": {"USD": 50}, "sin_dato": false}]}]
```

## Antes (licencia_compartida)

Hasta la migración 0013 las licencias compartidas (pares de Adobe del UserManager) estaban en la tabla
`licencia_compartida`. La 0013 las pasó a la asignación del principal (o a una asignación nueva `par-<id>`) con la
imputación como centro de costo. El % de imputación viejo no se trasladó (queda 50/50, se ajusta a mano). La tabla
queda sin uso, solo como registro.
