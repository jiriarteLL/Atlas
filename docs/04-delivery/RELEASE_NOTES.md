# Release Notes — Maestro Platform v1.0.0-rc.1

**Fecha:** 2026-04-18
**Release Candidate #1** — primera entrega de Maestro Platform para testing en VPS.

---

## Qué es Maestro Platform

Plataforma multi-tenant que aloja aplicaciones dockerizadas con autenticación centralizada. Cada empresa (tenant) puede tener N aplicaciones huésped gestionadas desde un portal único. Todas las apps delegan el login en el Maestro y reciben identidad + contexto vía headers inyectados por Traefik ForwardAuth.

## Qué trae V1 (rc.1)

- **14 épicas** completas: Auth, identidades, audit log inmutable, provisioning de instancias, reverse proxy, portal admin React, SDK + CLI, hooks HMAC, gateway inter-apps, observabilidad, backups, CI/CD
- **39 endpoints REST** registrados (auth, admin CRUD, gateway, v1 platform)
- **151 tests pasando** con 80.2% cobertura
- **CIS Docker Benchmark + OWASP ASVS L2** aplicados

## Cómo desplegar en VPS

### Pre-requisitos en el host

- Docker ≥ 26
- Docker Compose ≥ 2.22
- Dominio DNS apuntando al VPS (wildcard recomendado para apps huésped)
- Puerto 80/443 abiertos

### Paso a paso

1. **Clonar repo en el VPS** (el humano hace esto manualmente — DEC-011):
   ```bash
   git clone https://github.com/LLyAsoc-Digital/web-maestro-para-aplicacones-genericas.git /opt/maestro
   cd /opt/maestro
   git checkout v1.0.0-rc.1
   ```

2. **Preparar `.env.production`:**
   ```bash
   cp .env.production.example .env.production
   # completar: APP_KEY, DB_PASSWORD, REDIS_PASSWORD, MAESTRO_ENCRYPTION_KEY,
   # BACKUP_ENCRYPTION_KEY, MICROSOFT_ENTRA_*, AZURE_STORAGE_*
   # (ver INFRASTRUCTURE.md §5)
   ```

3. **Ajustar dominio en `docker/traefik/traefik.prod.yml`** (contacto ACME + dominio base).

4. **Pull de imágenes desde GHCR:**
   ```bash
   docker login ghcr.io
   IMAGE_TAG=v1.0.0-rc.1 docker compose -f docker-compose.prod.yml --env-file .env.production pull
   ```

5. **Levantar stack:**
   ```bash
   IMAGE_TAG=v1.0.0-rc.1 docker compose -f docker-compose.prod.yml --env-file .env.production up -d
   ```

6. **Migraciones + seeders iniciales:**
   ```bash
   docker exec maestro-api php artisan migrate --force
   docker exec maestro-api php artisan db:seed --class=PassportClientsSeeder
   docker exec maestro-api php artisan db:seed --class=InitialAdminSeeder
   # guardar las credenciales del admin que imprime el seeder
   ```

7. **Stack observabilidad (opcional pero recomendado):**
   ```bash
   docker compose -f docker-compose.obs.yml --env-file .env.production up -d
   ```

8. **Validación manual (humano):**
   - `https://maestro.<dominio>/api/platform/health` → 200 OK
   - Login en portal con admin creado
   - Probar alta de company, user, application
   - Registrar app huésped vía `POST /api/v1/apps/register`
   - Provisionar instancia desde UI
   - Verificar audit-log refleja las acciones
   - Verificar Grafana dashboards

## Rollback

Si un deploy falla:
```bash
IMAGE_TAG=v<anterior> docker compose -f docker-compose.prod.yml --env-file .env.production up -d --force-recreate
docker exec maestro-api php artisan migrate:rollback --step=1  # si aplica
```

## Soporte

El framework V1 no incluye SLA de soporte integrado (DEC-021). Soporte post-release se gestiona por fuera del producto.

## Upgrade path a v1.0.0 final

Tras validación exitosa del rc.1 en VPS durante ≥7 días con los gaps E2E cubiertos manualmente:
1. Tag `v1.0.0` en `main`
2. Pull de `ghcr.io/.../-api:v1.0.0` en VPS
3. `docker compose up -d` con nuevo IMAGE_TAG

## Detalles técnicos

Ver:
- `CHANGELOG.md` — lista completa de features
- `docs/04-delivery/INFRASTRUCTURE.md` — topología + CIS Docker
- `docs/04-delivery/CI_CD.md` — pipeline + versionado
- `docs/04-delivery/INTEGRATION_REPORT.md` — smoke tests ejecutados
- `docs/02-planning/ARCHITECTURE.md` — arquitectura
- `docs/02-planning/ADR_LOG.md` — 14 ADRs que respaldan decisiones
