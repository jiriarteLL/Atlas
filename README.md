# Maestro Platform V1

> Plataforma multi-tenant de clase empresarial que aloja, orquesta y gobierna múltiples aplicaciones dockerizadas bajo un portal web unificado con autenticación centralizada.

**Proyecto:** PRJ-MAESTRO-V1 · **Preset:** maestro-platform (dual invertido de web-maestro) · **Stack:** Laravel 13 + Passport + React + Traefik + Docker

---

## Estructura del repositorio

```
MaestroConFrameworkAgentico/
├── backend/                 # Laravel 13 Maestro API (monolito modular)
│   ├── app/Modules/         # Auth, Identity, Catalog, Provisioning, Gateway, Hooks, AuditLog, Platform
│   ├── database/migrations/ # schema del Maestro
│   └── composer.json
├── portal/                  # React 18 + Tailwind (base Tailwise v1.0.9)
├── sdk/node/                # @maestro/sdk-node (middleware auth + filtro tenant)
├── cli/node/                # maestro-cli (validate + new)
├── docker/                  # Dockerfiles y configs (php, portal, traefik)
├── docker-compose.dev.yml   # stack completo local (DEC-012 — zero local installs)
├── docs/                    # artefactos del framework agéntico
│   ├── 01-discovery/        # RESEARCH_FINDINGS, REQUIREMENTS, GLOSSARY
│   ├── 02-planning/         # ARCHITECTURE, ADR_LOG, DATA_MODEL, API_CONTRACTS, UX_SPECS, THREAT_MODEL
│   └── CONVENCIONES_PLATAFORMA.md   # DEL-001: naming/puertos/redes/volúmenes
├── framework-agentico/      # agentes, checkpoints y governance del framework
└── PremisaWebMaestro/       # constitución del proyecto (no modificar)
```

---

## Quick start (dev)

### Prerequisitos del host
- Docker 24+ y Docker Compose v2
- git
- IDE (recomendado VSCode con Dev Containers)
- **Nada más.** Sin PHP, Composer, Node o psql en el host (DEC-012).

### Primer arranque

```bash
# 1. Clonar y preparar .env
cp .env.example .env

# 2. Generar keys
just key-generate          # APP_KEY de Laravel
just encryption-key        # MAESTRO_ENCRYPTION_KEY, copiar al .env
just passport-keys         # claves OAuth2 RSA-4096 en ./secrets/

# 3. Instalar dependencias dentro de contenedores
just composer-install
just npm-install

# 4. Levantar el stack
just up

# 5. Correr migraciones
just migrate

# 6. Seeder inicial (crea tenant LLyAsoc + admin platform)
just seed
```

El portal queda en `https://maestro.local/` y la API en `https://maestro.maestro.local/api/`. Para evitar warnings de TLS self-signed en dev, agregá estas entradas a `/etc/hosts`:

```
127.0.0.1 maestro.local maestro.maestro.local
```

---

## Comandos útiles (justfile)

| Comando | Acción |
|---|---|
| `just up` / `just down` | Levantar / detener stack |
| `just logs <servicio>` | Logs en vivo |
| `just artisan <cmd>` | Comando artisan arbitrario |
| `just composer <cmd>` | Composer arbitrario |
| `just npm <cmd>` | npm del portal |
| `just test` / `just test-coverage` | Tests backend |
| `just lint` / `just lint-fix` | Pint (code style) |
| `just analyze` | PHPStan / larastan |
| `just psql` | Abrir psql en la BD del Maestro |
| `just shell` | Bash dentro del contenedor backend |
| `just clean` | Borrar volúmenes y node_modules/vendor |

`just --list` muestra el catálogo completo.

---

## Documentación

| Tema | Archivo |
|---|---|
| Premisa vinculante (10 no-negociables) | `PremisaWebMaestro/01-PREMISAS-Y-NO-NEGOCIABLES.md` |
| Arquitectura completa | `docs/02-planning/ARCHITECTURE.md` |
| Decisiones (14 ADRs) | `docs/02-planning/ADR_LOG.md` |
| Modelo de datos | `docs/02-planning/DATA_MODEL.md` |
| Contratos de API | `docs/02-planning/API_CONTRACTS.md` |
| UX specs | `docs/02-planning/UX_SPECS.md` |
| Threat model (STRIDE + ASVS L2 + CIS + GDPR) | `docs/02-planning/THREAT_MODEL.md` |
| Convenciones para coexistencia con apps huésped | `docs/CONVENCIONES_PLATAFORMA.md` |
| Checkpoint global del proyecto | `framework-agentico/agents/CHECKPOINT_GLOBAL.md` |

---

## Estado actual

Framework agéntico activo. Fases completadas: **00-setup**, **01-discovery**, **02-planning**. En curso: **03-development** (kickoff).

- 125 requisitos validados (62 RF MUST + 4 SHOULD + 4 COULD + 13 WON'T + 42 RNF).
- 14 ADRs con trade-offs documentados.
- Stack definitivo: Laravel 13.x + Passport 13.x + PostgreSQL 16 + Redis 7 + React 18 + Tailwise + Traefik v3 + docker-socket-proxy + SDK Node 20.
- Escala V1: 1 tenant × 7 apps × 50 usuarios concurrentes.

---

## Licencia y governance

Proyecto propietario de **LLyAsoc Digital**. Contribuciones siguen el flujo trunk-based (master protegida, PR + review, conventional commits). Ver `docs/02-planning/ARCHITECTURE.md §6`.
