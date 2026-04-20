# Maestro Platform — atajos de comandos
# Uso: `just <target>`
# Todo corre en contenedores (DEC-012 — zero local installs).

# --------- Entorno ---------
default:
    @just --list

# Levanta el stack completo en background
up:
    docker compose -f docker-compose.dev.yml up -d

# Detiene el stack
down:
    docker compose -f docker-compose.dev.yml down

# Logs (live)
logs service="":
    docker compose -f docker-compose.dev.yml logs -f {{service}}

# Rebuild de imágenes
build:
    docker compose -f docker-compose.dev.yml build

# --------- Inicialización ---------
# Instala composer deps (backend)
composer-install:
    docker compose -f docker-compose.dev.yml run --rm maestro-api composer install

# Instala npm deps (portal, SDK, CLI)
npm-install:
    docker compose -f docker-compose.dev.yml run --rm maestro-portal npm install

# Genera APP_KEY de Laravel en .env
key-generate:
    docker compose -f docker-compose.dev.yml run --rm maestro-api php artisan key:generate

# Genera MAESTRO_ENCRYPTION_KEY (base64 de 32 bytes)
encryption-key:
    @docker compose -f docker-compose.dev.yml run --rm maestro-api php -r "echo 'MAESTRO_ENCRYPTION_KEY=' . base64_encode(random_bytes(32)) . PHP_EOL;"

# Genera claves OAuth2 Passport en ./secrets/
passport-keys:
    mkdir -p secrets
    docker compose -f docker-compose.dev.yml run --rm maestro-api php artisan passport:keys --force --length=4096
    chmod 600 secrets/oauth-*.key

# Corre todas las migraciones
migrate:
    docker compose -f docker-compose.dev.yml run --rm maestro-api php artisan migrate

# Rollback de la última migración
migrate-rollback:
    docker compose -f docker-compose.dev.yml run --rm maestro-api php artisan migrate:rollback

# Seeder inicial (tenant + admin)
seed:
    docker compose -f docker-compose.dev.yml run --rm maestro-api php artisan db:seed

# Bootstrap demo PO (Acme Demo + po@maestro.local + tester@maestro.local)
bootstrap-demo:
    docker compose -f docker-compose.dev.yml run --rm maestro-api php artisan maestro:bootstrap-demo

# Bootstrap demo con migrate:fresh (CUIDADO: pierde datos)
bootstrap-demo-fresh:
    docker compose -f docker-compose.dev.yml run --rm maestro-api php artisan maestro:bootstrap-demo --fresh

# --------- Desarrollo ---------
# Shell dentro del backend
shell:
    docker compose -f docker-compose.dev.yml run --rm maestro-api bash

# Shell dentro del portal
shell-portal:
    docker compose -f docker-compose.dev.yml run --rm maestro-portal sh

# Artisan arbitrario
artisan +cmd:
    docker compose -f docker-compose.dev.yml run --rm maestro-api php artisan {{cmd}}

# Composer arbitrario
composer +cmd:
    docker compose -f docker-compose.dev.yml run --rm maestro-api composer {{cmd}}

# npm arbitrario (portal)
npm +cmd:
    docker compose -f docker-compose.dev.yml run --rm maestro-portal npm {{cmd}}

# --------- Testing ---------
test:
    docker compose -f docker-compose.dev.yml run --rm maestro-api composer test

test-coverage:
    docker compose -f docker-compose.dev.yml run --rm maestro-api composer test-coverage

lint:
    docker compose -f docker-compose.dev.yml run --rm maestro-api composer lint

lint-fix:
    docker compose -f docker-compose.dev.yml run --rm maestro-api composer lint-fix

analyze:
    docker compose -f docker-compose.dev.yml run --rm maestro-api composer analyze

test-portal:
    docker compose -f docker-compose.dev.yml run --rm maestro-portal npm test

# E2E Playwright smoke (requiere stack arriba + bootstrap-demo ejecutado)
e2e:
    mkdir -p tests/e2e-smoke/screenshots
    docker run --rm \
        --network maestro-network \
        -v "$(pwd)/tests/e2e-smoke:/specs:ro" \
        -v "$(pwd)/tests/e2e-smoke/screenshots:/out" \
        -w /specs \
        -e E2E_EMAIL=po@maestro.local \
        -e E2E_PASS=MaestroPO2026! \
        mcr.microsoft.com/playwright:v1.49.0-jammy \
        sh -c "npm i --no-save playwright@1.49.0 >/dev/null 2>&1 && node /specs/login.spec.mjs"

# --------- Utilidades ---------
# Estado del stack
status:
    docker compose -f docker-compose.dev.yml ps

# Cliente psql contra la BD del Maestro
psql:
    docker compose -f docker-compose.dev.yml exec maestro-db psql -U maestro -d maestro

# Cliente redis-cli
redis-cli:
    docker compose -f docker-compose.dev.yml exec maestro-redis redis-cli -a "${REDIS_PASSWORD:-changeme}"

# Limpiar volumenes (CUIDADO: borra datos locales)
clean:
    docker compose -f docker-compose.dev.yml down -v
    rm -rf backend/vendor portal/node_modules sdk/node/node_modules cli/node/node_modules
