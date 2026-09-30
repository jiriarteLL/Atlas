# CI/CD y Gobernanza de Repositorios

> **Versión:** v4 (framework agéntico v4 / contrato `maestro.platform/v2`)
> **Última revisión:** 2026-05-07
> **Estado:** vigente
> **Reemplaza a:** `legacy/v3/PremisaWebMaestro/08-CICD-Y-GOBERNANZA.md` (modelo v1).

---

## Propósito de este documento

Este documento describe los pipelines de integración continua (CI) y despliegue continuo (CD) de la **Web Maestro** v4 y de las **apps huésped**, la estructura organizativa de los repositorios, las protecciones de branch, y el flujo completo desde un commit hasta el deployment en producción.

Audiencia: DevOps, equipos de plataforma, agentes `ci-cd-specialist` y `devops-engineer`.

---

## Estructura de repositorios

### Repositorio del Maestro

Único repo, propiedad del equipo de plataforma:

- `github.com/<org>/maestro-platform` (nombre tentativo).
- Contiene: backend del Maestro, frontend del portal, motor de provisioning, `maestro-cli`, infraestructura (Traefik config, observabilidad).
- Branch principal: `main` con protección estricta.
- Branch de integración: `develop` (opcional).
- Branches de feature: `feature/<descripcion>`.

### Repositorio del template para apps huésped

Este mismo repositorio (`tailwise_laravel_vue_react_template`):

- Contiene framework agéntico v4, presets, premisas, Tailwise Bundle, schemas, documentación.
- Es **template de fork**: cada app huésped lo forkea para su propio repo.
- Branch principal: `master` (o `main`).
- Branches de evolución del framework: `epic/framework-v{n}` (este trabajo se hace en `epic/framework-v4`).

### Repositorios de apps huésped

Cada app es un fork independiente del template:

- `github.com/<owner>/<app_slug>`.
- El owner puede ser una empresa, equipo o individuo.
- Contiene: código de la app, su `maestro.yaml`, su Dockerfile, su `docker-compose.dev.yml`, sus tests.
- **NO** contiene framework agéntico (lo hereda del template via merge upstream).
- **NO** contiene constitución del Maestro (`PremisaWebMaestro/`); la lee del template upstream.
- Branch principal: `main` o `master`.
- Branches de feature: `feature/<descripcion>`.
- Para PR upstream contra `app-<slug>` del repo principal (si la organización lo requiere).

### Convención de gobernanza recomendada

```
REPO PRINCIPAL (org/plataforma-maestro)
│
├── Branch master/main → release oficial
├── Branch app-inventario → versión oficial de la app de inventario
├── Branch app-facturacion → versión oficial de la app de facturación
└── ...

FORKS (org/app-inventario, equipo-A/app-inventario, etc.)
│
├── Branch develop → trabajo en curso
├── Branch feature/* → features
└── PRs hacia principal/app-{nombre} → revisados por el administrador
```

---

## Pipeline CI del Maestro

### Triggers
- Push a `main`.
- Pull request hacia `main` o `develop`.

### Jobs (en orden)

```yaml
# .github/workflows/ci.yml

jobs:
  validate:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
        with: { fetch-depth: 0 }
      - name: Setup runtime
        uses: actions/setup-node@v4   # o php / python según stack
      - run: npm ci                    # o composer install
      - name: Lint
        run: npm run lint
      - name: Format check
        run: npm run format:check
      - name: Unit tests
        run: npm test -- --ci --coverage
      - name: Type check
        run: npm run typecheck
      - name: Schema validation
        run: npx ajv validate -s docs/schemas/maestro.yaml.schema.v2.json -d <test_fixtures>

  security:
    needs: validate
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
        with: { fetch-depth: 0 }
      - name: Gitleaks deep scan
        uses: gitleaks/gitleaks-action@v2
      - name: Dependency scan
        run: npm audit --audit-level=high

  build:
    needs: [validate, security]
    if: github.ref == 'refs/heads/main'
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - uses: docker/setup-buildx-action@v3
      - uses: docker/login-action@v3
        with:
          registry: ghcr.io
          username: ${{ github.actor }}
          password: ${{ secrets.GITHUB_TOKEN }}
      - name: Build & push image
        uses: docker/build-push-action@v6
        with:
          context: .
          push: true
          tags: |
            ghcr.io/${{ github.repository }}:${{ github.sha }}
            ghcr.io/${{ github.repository }}:latest-stable
          cache-from: type=gha
          cache-to: type=gha,mode=max
          provenance: true
          sbom: true
      - name: Vulnerability scan
        uses: aquasecurity/trivy-action@0.24.0
        with:
          image-ref: ghcr.io/${{ github.repository }}:${{ github.sha }}
          severity: CRITICAL,HIGH
          exit-code: '1'
      - name: Sign image with cosign
        uses: sigstore/cosign-installer@v3
      - run: cosign sign --yes ghcr.io/${{ github.repository }}@${{ steps.build.outputs.digest }}

  integration_tests:
    needs: build
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - name: Spin up Maestro stack
        run: docker compose -f docker-compose.test.yml up -d
      - name: Wait for healthy
        run: ./scripts/wait-for-healthy.sh
      - name: Run integration tests
        run: docker compose exec -T maestro-api npm run test:integration
      - name: Tear down
        if: always()
        run: docker compose -f docker-compose.test.yml down -v
```

### Reglas
- `validate` y `security` corren en cada PR (bloqueo si fallan).
- `build` y `integration_tests` solo en push a `main`.
- Si CI falla, el merge se bloquea (branch protection).

---

## Pipeline CI de las apps huésped

Cada app huésped hereda un workflow base del template. Ejemplo:

```yaml
# .github/workflows/deploy.yml

name: deploy

on:
  push:
    branches: [main]
  pull_request:

permissions:
  contents: read
  id-token: write
  packages: write

jobs:
  validate:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
        with: { fetch-depth: 0 }
      - name: Setup runtime
        uses: <stack-specific-action>
      - run: <install dependencies>
      - run: <lint>
      - run: <unit tests>
      - name: Validate maestro.yaml
        run: npx -y @maestro/cli@latest validate
      - name: Gitleaks deep scan
        uses: gitleaks/gitleaks-action@v2

  build:
    needs: validate
    if: github.ref == 'refs/heads/main'
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - uses: docker/setup-buildx-action@v3
      - uses: docker/login-action@v3
        with:
          registry: ghcr.io
          username: ${{ github.actor }}
          password: ${{ secrets.GITHUB_TOKEN }}
      - name: Build & push
        uses: docker/build-push-action@v6
        with:
          context: .
          push: true
          tags: |
            ghcr.io/${{ github.repository }}:${{ github.sha }}
            ghcr.io/${{ github.repository }}:<semver-from-maestro-yaml>
          cache-from: type=gha
          cache-to: type=gha,mode=max
          provenance: true
          sbom: true
      - name: Vulnerability scan
        uses: aquasecurity/trivy-action@0.24.0
        with:
          image-ref: ghcr.io/${{ github.repository }}:${{ github.sha }}
          severity: CRITICAL,HIGH
          exit-code: '1'
      - name: Sign image
        uses: sigstore/cosign-installer@v3
      - run: cosign sign --yes ghcr.io/${{ github.repository }}@${{ steps.build.outputs.digest }}

  register:
    needs: build
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - name: Register on Maestro
        run: |
          curl -fsSL -X POST "$MAESTRO_API_URL/api/v2/apps/register" \
            -H "Authorization: Bearer $MAESTRO_REGISTRATION_TOKEN" \
            -H "Content-Type: application/yaml" \
            -H "X-Image-Ref: ghcr.io/${{ github.repository }}@${{ steps.build.outputs.digest }}" \
            -H "X-Commit-Sha: ${{ github.sha }}" \
            -H "X-Yaml-Hash: $(sha256sum maestro.yaml | cut -d' ' -f1)" \
            --data-binary @maestro.yaml
        env:
          MAESTRO_API_URL: ${{ secrets.MAESTRO_API_URL }}
          MAESTRO_REGISTRATION_TOKEN: ${{ secrets.MAESTRO_REGISTRATION_TOKEN }}
```

### Diferencias con CI del Maestro
- Las apps huésped **NO** ejecutan integration tests con el Maestro real (eso lo haría un job e2e separado en el repo del Maestro).
- Las apps huésped **NO** tienen permiso para mergear en el repo del Maestro.
- Las apps huésped **registran su imagen** vía `POST /api/v2/apps/register` desde su CI; el Maestro decide si crear/actualizar deployments.

---

## Branch protection

### Repo del Maestro (`main`)

- Require pull request reviews antes de merge: 1 aprobación mínima.
- Require status checks: `validate`, `security`, `build` (cuando aplique).
- Require branches up to date.
- Require conversation resolution.
- Restrict pushes que skipean reviews.
- No force-push.
- No deleting.
- Linear history (no merge commits, solo squash o rebase).

### Repo del template

- Mismas reglas que el repo del Maestro.
- `master` o `main` protegidos.
- Branches de evolución del framework (`epic/framework-v{n}`) NO requieren review pero deben pasar CI.

### Repos de apps huésped

- Mínimo recomendado:
  - Require status check: `validate` (debe pasar).
  - No force-push a `main`.
- Branch protection adicional según política de la organización dueña del fork.

---

## Self-registration de apps huésped

El endpoint `POST /api/v2/apps/register` permite a una app registrarse contra el Maestro **automáticamente desde su CI**. Flujo:

```
1. Dev pushea cambios a main del fork de la app.
2. CI corre: lint, tests, build, scan, sign.
3. Si todo OK, CI ejecuta:
   POST $MAESTRO_API_URL/api/v2/apps/register
   con el maestro.yaml y headers de integridad.
4. El Maestro valida:
   - Token de registro (cada owner tiene su token único).
   - JSON Schema v2.
   - apiVersion = maestro.platform/v2.
   - metadata.name único.
   - Hash del YAML.
5. Si valida, el Maestro:
   - Inserta o actualiza la fila en `applications`.
   - Registra audit log.
   - Responde 201 Created (o 200 OK si es update).
6. Si la empresa ya tiene licencia para esta app:
   - Trigger para crear/actualizar el deployment automáticamente (opcional, según política).
   - Si no, el deployment queda pendiente hasta que un admin del Maestro lo provisione.
```

### Tokens de registro

- Cada owner del repo de una app obtiene un `MAESTRO_REGISTRATION_TOKEN` único.
- Se genera desde el portal del Maestro (`/admin/registration-tokens`).
- Se guarda en GitHub Secrets del repo de la app.
- Audit logged en cada uso (request_id, owner, app_slug, success/failure).
- Rotable desde el portal.

### Consideraciones de seguridad

- El token está acotado al `metadata.name` del repo (un token de la app A no puede registrar a la app B).
- Rate limiting: máximo N registros por token por hora.
- Compromiso del token: se revoca y se rota; el Maestro mantiene el último estado registrado válido.

---

## Versionado y releases

### Del Maestro
- SemVer estricto (`MAJOR.MINOR.PATCH`).
- Tags Git en `main` (`v1.0.0`, `v1.1.0`, etc.).
- Releases en GitHub con changelog.
- Imagen Docker: `ghcr.io/<org>/maestro-api:<semver>` y `:<sha>`.

### De las apps huésped
- SemVer estricto en `metadata.version` del `maestro.yaml`.
- Cada PUSH a main que cambie el `metadata.version` registra una nueva versión en la tabla `applications`.
- Versiones anteriores se conservan en `applications_versions` (tabla histórica).

### Del framework agéntico
- SemVer (`MAJOR.MINOR.PATCH`).
- Documentado en `framework-agentico/CHANGELOG.md`.
- Bumps MAYORES (ej: v3 → v4) son **breaking changes** y disparan migración lazy en forks (ver `framework-agentico/migration/`).

### Del contrato `maestro.platform`
- Version actual: `v2`.
- Bumps MAYORES son breaking; el Maestro mantiene compatibilidad ≥ 12 meses con la versión anterior.

---

## Estrategia de deployment

### Maestro
- **Deployment al VPS o cloud lo hace el equipo de plataforma**, no el framework agéntico.
- Scripts/documentación en `docs/deployment.md` (a generar en fase 04-delivery).
- Pasos típicos:
  1. SSH al VPS.
  2. `git pull` del repo del Maestro.
  3. `docker compose pull`.
  4. `docker compose down && docker compose up -d`.
  5. Validar health checks.
  6. Si falla, rollback con tag anterior.

### Apps huésped
- **El Maestro orquesta el deployment** de las apps huésped en sus deployments.
- Cuando una empresa adquiere licencia o actualiza versión:
  - Admin del Maestro ejecuta `POST /api/v2/deployments` (o trigger automático).
  - Motor de provisioning baja la imagen del registry, levanta contenedor + BD, ejecuta migraciones + seeders, espera health.
- Cada app huésped controla su propio CI hasta que la imagen está en el registry; del registry en adelante, el Maestro toma control.

---

## Política de hotfixes

- Hotfix urgente: branch `hotfix/<id>` desde `main`, PR fast-track con 1 reviewer obligatorio, deploy inmediato post-merge.
- Audit log: hotfixes quedan marcados con `is_hotfix=true` en commit message convention.

---

## Auditoría de cambios

Toda modificación al código del Maestro o a apps huésped queda auditada:

- **Git history**: source of truth técnico.
- **CI logs**: storage de outputs en GitHub Actions ≥ 90 días.
- **Audit log del Maestro**: registra acciones administrativas del portal (no commits del código del Maestro mismo).
- **Audit log del registry**: cada llamada a `/api/v2/apps/register` queda audit logged.

---

## Referencias normativas

- `01-PREMISAS-Y-NO-NEGOCIABLES.md` — no-negociables 7 (no-root), 8 (secretos no en código), 11 (TLS), 12 (audit log).
- `04-INFRAESTRUCTURA-DOCKER.md` — imágenes Docker y registries.
- `06-CONTRATO-MAESTRO-YAML.md` — endpoint `/api/v2/apps/register`.
- `09-SEGURIDAD.md` — pre-commit hooks, gitleaks, scan de imágenes.
- `framework-agentico/phases/04-delivery.md` — fase de delivery con CI/CD.
- `framework-agentico/CHANGELOG.md` — historial de versiones del framework.

---

## Historial de revisiones

| Versión | Fecha | Cambio |
|---|---|---|
| 4.0.0 | 2026-05-07 | Versión inicial v4. Documenta CI/CD para Maestro y apps huésped, branch protection, self-registration via `/api/v2/apps/register`, versionado SemVer. Reemplaza al v1 (legacy en `legacy/v3/PremisaWebMaestro/08-CICD-Y-GOBERNANZA.md`). |
