# Validación transversal — 2026-09-30 (intento 1)

Los 5 validadores de `framework-agentico/validation/validators/` corrieron en paralelo, en solo lectura, con los
modelos que indica `TRANSVERSAL_TEMPLATE.md`. Cada hallazgo se verificó contra el código antes de aceptarlo.

## Resultado

| Validador | Modelo | Veredicto reportado | Después de verificar y corregir |
|---|---|---|---|
| security-auditor | sonnet | PASS (1 MEDIUM, 2 LOW) | **PASS**: los 3 corregidos |
| code-reviewer | sonnet | PASS (3 MEDIUM, 1 LOW) | **PASS**: 2 corregidos, 1 pasado a deuda (DT-11), 1 informativo |
| qa-tester | sonnet | FAIL (1 HIGH, 5 MEDIUM, 3 LOW) | **PASS**: tests agregados para el HIGH y los MEDIUM/LOW que aplican (84 → 108 tests) |
| performance-analyst | haiku | FAIL (4 CRITICAL, 2 HIGH) | **PASS**: 3 corregidos; el resto no se sostuvo al verificarlo (ver abajo) |
| compliance-analyst | haiku | FAIL (2 CRITICAL, 1 HIGH) | **PASS**: los 2 CRITICAL eran falsos; el HIGH es una decisión humana (issue #18) |

## Correcciones aplicadas

| Hallazgo | Validador | Corrección |
|---|---|---|
| Los links de proyecto aceptaban `javascript:` o `data:` | security | Validador `http(s)://` en `ProyectoIn` y `urlSegura()` en el frontend |
| HTML sin escapar en los mails | security + code-review | `html.escape` en `mailer.py` |
| El reset de password usaba `prompt()` y mostraba lo que se escribía | security | Modal con `input type=password` y confirmación |
| `ensayo.sh` chequeaba un volumen `_storage` que ya no existe (el ensayo nunca daba PASS) | code-review | Chequeo solo sobre `inventario-test_pgdata` |
| `POST /api/assets/{id}/garantia` sin tests | qa (HIGH) | 5 tests: 200, no Lenovo → 400, portal → 422, serial inválido, sin permiso → 403; y vencimientos con datos |
| Faltaban tests de adjunto > 10 MB, mail de proyecto finalizado, responsables y activos, 403 del snapshot, bcrypt, alta incompleta y TTL | qa | Tests agregados, más los de escape de mails y validación de links |
| N+1 en `_proy_dict` (una consulta por activo) | performance | Una sola consulta con `IN` |
| Sin índice en `snapshots.fecha` | performance | `index=True` en `fecha` y `metrica` |
| Timeout de 25 s en la consulta a Lenovo | performance | 10 s |

## Descartados (con motivo)

| Hallazgo | Motivo |
|---|---|
| compliance: "faltan `docker-compose.test.yml` y `.preprod.yml`" (CRITICAL ×2) | Falso: existen, están trackeados y subidos a `origin/develop` |
| performance: paginar `/api/assets` (CRITICAL) | Son unos 550 activos (menos de 300 KB). El frontend filtra, ordena y pagina de a 50 en el navegador: paginar en el servidor rompería los filtros sin ahorrar memoria que importe frente a 512 MB |
| performance: `vencimientos` sin filtro SQL (CRITICAL) | Falso: ya filtra con `garantia != ""` |
| performance: "el scraping de Lenovo paraliza la app" (CRITICAL) | El endpoint es síncrono y FastAPI lo corre en el threadpool, sin bloquear el event loop. Igual se bajó el timeout a 10 s |
| performance: falta índice en `users.email` (HIGH) | `unique=True` ya crea el índice |
| performance: `/health` hace `SELECT 1` (MEDIUM) | Es lo que pide SPEC §2.3 ("DEBERÍA verificar conectividad a la BD") |
| performance: descarga de adjuntos en memoria (MEDIUM) | Tope de 10 MB por archivo; aceptable con 512 MB |
| code-review: `App.jsx` monolítico (MEDIUM) | Real, pero es un refactor: pasa a deuda técnica DT-11 |
| code-review: aviso de deprecación de `httpx` (LOW) | Informativo; se revisa en la próxima actualización de FastAPI |

## Queda a decisión humana

- **`data_policy.regulated: false` frente a la Ley 25.326** (compliance HIGH, también mencionado por security).
  Issue #18: lo decide el PO o el evaluador.
