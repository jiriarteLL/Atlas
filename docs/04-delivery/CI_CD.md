# CI_CD.md — Maestro Platform V1

> **Fase:** 04-delivery
> **Versión:** 1.0.0-rc.1

---

## 1. Workflows

### `.github/workflows/ci.yml` — en cada push/PR a `main` y a branches `feature/*`

| Job | Dependencia | Objetivo | Bloquea merge |
|---|---|---|---|
| `secrets-scan` | — | `gitleaks` sobre todo el repo | ✅ |
| `backend-lint` | — | `composer install` + Laravel Pint + PHPStan nivel 8 | ✅ |
| `backend-tests` | postgres:16-alpine + redis:7-alpine services | PHPUnit con xdebug coverage; target ≥80% | ✅ |
| `portal-build` | — | `npm ci` + `npm run build` + typecheck | ✅ |
| `docker-scan` | — | Build Dockerfile `docker/php/Dockerfile` (target prod) + Trivy CRITICAL/HIGH | ✅ |

Cobertura actual (base fase 03 iter 9): **80.2%** (150 passing / 1 skipped / 285 assertions).

### `.github/workflows/release.yml` — en push de tags `v*`

| Job | Objetivo |
|---|---|
| `build-and-push` | Build+push `maestro-api` a GHCR con tags `v1.2.3`, `v1.2`, `sha-<git>`; Trivy scan bloqueante |
| `build-portal` | Build+push `maestro-portal` a GHCR |
| `github-release` | Generar CHANGELOG (conventional commits) + publicar GitHub Release |

## 2. Estrategia de versionado — SemVer

- `v<MAJOR>.<MINOR>.<PATCH>` — p.ej. `v1.0.0-rc.1`, `v1.0.0`, `v1.0.1`
- `MAJOR` = breaking en API/contract/DB
- `MINOR` = features nuevas retrocompatibles
- `PATCH` = fixes
- Prereleases: `-rc.N`, `-beta.N`

V1 inicia en **v1.0.0-rc.1** (esta entrega). La promoción a `v1.0.0` requiere smoke tests en VPS validados por el humano.

## 3. Flujo de release

1. Merge a `main` con squash commit Conventional
2. `git tag vX.Y.Z && git push --tags`
3. GitHub Actions `release.yml` dispara:
   - Build multi-arch imágenes
   - Push a GHCR
   - Trivy scan (si falla → release abortado)
   - Changelog + GitHub Release publicado
4. Humano hace `docker compose -f docker-compose.prod.yml --env-file .env.production pull && up -d`

## 4. Política de rollback

- `docker compose up -d --env-file .env.production` con `IMAGE_TAG=v<prev>` — rollback de imagen
- Rollback de migración: `docker compose exec maestro-api php artisan migrate:rollback --step=N`
- Rollback de datos: `just restore <backup-id>` (restaura pg_dump cifrado de Azure Blob)
- RTO objetivo V1: 30 min (single VPS sin HA)

## 5. Secretos en GitHub Actions

Solo `GITHUB_TOKEN` para GHCR (default). No hay secretos externos expuestos en workflows V1 (sin deploy automatizado al VPS — DEC-011).
