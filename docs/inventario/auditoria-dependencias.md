# Auditoría de dependencias — 2026-09-30

Lectura previa al Gate 1, sin Docker. **No reemplaza a Trivy**, que además escanea el sistema operativo de la
imagen: ese escaneo queda pendiente de la VM de ensayo (issue #2).

## Backend — `pip-audit -r app/backend/requirements.txt`

| Paquete | Hallazgo | Resolución |
|---|---|---|
| `ecdsa` 0.19.2 (dependencia de `python-jose`) | CVE-2024-23342 / PYSEC-2026-1325, ataque de tiempo (Minerva) en firmas ECDSA P-256. **Sin versión corregida**: los mantenedores no lo van a arreglar. | La app firma con HS256 y nunca usa ECDSA. Aun así, Trivy lo reporta como HIGH y bloquea el Gate 1. **Se reemplazó `python-jose` por PyJWT 2.15.1**, que no depende de `ecdsa` (ni de `rsa`/`pyasn1`). |

**Resultado después del cambio:** `No known vulnerabilities found`.

## Frontend — `npm audit`

| Paquete | Severidad | Resolución |
|---|---|---|
| `brace-expansion` (vía `exceljs → archiver → glob/readdir-glob` y vía eslint) | Alta (DoS) | `npm audit fix`, sin cambios incompatibles. Además solo se usa en tiempo de build: la imagen final no lleva `node_modules`. |
| `uuid` < 11.1.1 (vía `exceljs@4.4.0`) | Moderada (GHSA-w5hq-g745-h8pq) | **No aplica.** El bug está en v3/v5/v6 cuando se les pasa un buffer, y exceljs usa solo `uuid.v4()`. El arreglo que propone npm (bajar a `exceljs@3.4.0`) rompe compatibilidad. Tampoco se fuerza otra versión con `overrides`: el navegador carga el bundle ya compilado de exceljs, que trae su propia copia, así que forzar la versión solo silenciaría el aviso. Se revisa si sale exceljs 4.x con uuid ≥ 11.1.1. |

**Resultado después del fix:** 2 moderadas, ambas del caso `uuid` descripto arriba. Ninguna alta ni crítica.
