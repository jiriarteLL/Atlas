# Inventario LLYA v2 (app huesped Maestro)

Version del Inventario LLYA adaptada al contrato `maestro.platform/v2` para desplegar en Dokploy.
Proyecto paralelo: el Inventario de produccion sigue en C:\AssetManager y no se toca desde aca.

**Antes de nada leer `AGENTS.md`** (normativo, manda sobre este archivo), `README.md` y `docs/deployment/MANUAL.md`.

## Arquitectura
- Backend: FastAPI en app/backend/. Configuracion SOLO por variables de entorno (config.py). Base PostgreSQL via DATABASE_URL.
- Frontend: React + Vite en app/frontend/. Llama a la API con rutas relativas (mismo origen), nunca IPs ni puertos.
- Una sola imagen: el Dockerfile compila el frontend y lo sirve el backend desde /app/frontend_dist.
- Sin storage en disco: el filesystem del contenedor es efimero (CONVENCIONES §4.2). Adjuntos y todo estado van a la base (ADR-001).
- Autonoma: NO depende del UserManager. Licencias, Nomina y ABM quedaron fuera de esta version.

## Reglas
- Nada de IPs, puertos, rutas C:/ ni secretos en el codigo o en los compose.
- Todo endpoint requiere login salvo /health, /auth/login y /maestro/branding.
- Tests: `python -m pytest app/tests` (usan SQLite en memoria, no necesitan Docker).
- Trabajar en la rama develop, commit por etapa.
- El agente NO corre Gate 2, NO mergea, NO despliega a Preprod (AGENTS.md §3).
- Interfaz en espanol rioplatense.
