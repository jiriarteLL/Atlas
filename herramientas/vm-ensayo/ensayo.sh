#!/bin/bash
# Ensayo local (MANUAL §5.0) + emulacion de los checks de Gate 1 que corren con Docker (MANUAL §7 Paso 3).
# Corre en la VM de ensayo, desde la raiz del repo:  bash herramientas/vm-ensayo/ensayo.sh
# Usa el MISMO compose que va a Dokploy (docker-compose.test.yml), con secretos generados para el ensayo.
# Al final baja todo con down -v (no deja volumenes). Deja el detalle en ensayo-resultado.txt.
set -uo pipefail
cd "$(dirname "$0")/../.."
OUT=ensayo-resultado.txt
: > "$OUT"
FALLAS=0
log()  { echo "$*" | tee -a "$OUT"; }
ok()   { log "  PASS  $*"; }
mal()  { log "  FAIL  $*"; FALLAS=$((FALLAS + 1)); }
PUERTO="${PUERTO_ENSAYO:-3110}"   # puerto de la VM, no del VPS
IMG=eval/inventario:ensayo

log "== Ensayo Inventario LLYA v2 — $(date -Is) — commit $(git rev-parse --short HEAD)"

# ---------------------------------------------------------------- .env del ensayo (secretos nuevos, en archivo)
ENVF=.env
if [ -e "$ENVF" ]; then echo "Ya existe .env: lo muevo a .env.previo"; mv "$ENVF" .env.previo; fi
hex() { openssl rand -hex "$1"; }
SUPER="Aa1-$(hex 10)"
umask 077
cp .env.example "$ENVF"
set_var() { sed -i "s|^$1=.*|$1=$2|" "$ENVF"; }
set_var APP_PORT "$PUERTO"
set_var DB_PASSWORD "$(hex 24)"
set_var JWT_SECRET "$(hex 32)"
set_var MAESTRO_API_KEY "$(hex 24)"
set_var MAESTRO_WEBHOOK_SECRET "$(hex 24)"
set_var SYNC_API_KEY "$(hex 24)"
set_var SUPERADMIN_INITIAL_PASSWORD "$SUPER"
MK=$(grep '^MAESTRO_API_KEY=' "$ENVF" | cut -d= -f2-)
umask 022

# ---------------------------------------------------------------- 1. los tres compose parsean y sin hardcode
log "== 1. Compose (IN-011)"
for f in docker-compose.yml docker-compose.test.yml docker-compose.preprod.yml; do
  if docker compose -f "$f" --env-file "$ENVF" config >/dev/null 2>>"$OUT"; then ok "$f parsea"; else mal "$f no parsea"; fi
  if grep -nE 'MAESTRO_API_KEY|_SECRET|_PASSWORD|SUPERADMIN' "$f" | grep -v '\${' >>"$OUT"; then mal "$f tiene hardcode"; else ok "$f sin hardcode"; fi
done

# ---------------------------------------------------------------- 2. build y tamaño (IN-004)
log "== 2. Build de imagen (IN-004)"
if docker build -t "$IMG" . >>"$OUT" 2>&1; then
  BYTES=$(docker image inspect "$IMG" --format '{{.Size}}'); MB=$((BYTES / 1024 / 1024))
  if [ "$MB" -gt 500 ]; then mal "imagen ${MB} MB (> 500)"; elif [ "$MB" -gt 350 ]; then log "  WARN  imagen ${MB} MB (> 350)"; else ok "imagen ${MB} MB"; fi
else
  mal "docker build fallo (ver $OUT)"
fi

# ---------------------------------------------------------------- 3. Trivy (IN-006 / CI-003)
log "== 3. Trivy CRITICAL/HIGH"
if docker run --rm -v /var/run/docker.sock:/var/run/docker.sock aquasec/trivy:latest image \
     --severity CRITICAL,HIGH --exit-code 1 --no-progress "$IMG" >>"$OUT" 2>&1; then ok "sin CRITICAL/HIGH"; else mal "Trivy encontro CRITICAL/HIGH (ver $OUT)"; fi

# ---------------------------------------------------------------- 4. Gitleaks, historial completo (SE-001 / CI-004)
log "== 4. Gitleaks"
if docker run --rm -v "$PWD:/repo" zricethezav/gitleaks:latest detect --source=/repo --redact \
     --log-opts=--all --exit-code 1 >>"$OUT" 2>&1; then ok "sin secretos en el historial"; else mal "Gitleaks encontro algo (ver $OUT)"; fi

# ---------------------------------------------------------------- 5. levantar el stack de Test y probar el contrato
log "== 5. Stack docker-compose.test.yml en :$PUERTO"
docker compose -f docker-compose.test.yml up -d --build >>"$OUT" 2>&1 || mal "compose up fallo"
B="http://127.0.0.1:$PUERTO"
for i in $(seq 1 60); do
  [ "$(docker inspect -f '{{.State.Health.Status}}' app-inventario-test 2>/dev/null)" = healthy ] && break; sleep 3
done
EST=$(docker inspect -f '{{.State.Health.Status}}' app-inventario-test 2>/dev/null)
[ "$EST" = healthy ] && ok "app-inventario-test healthy" || mal "app-inventario-test: $EST"
c() { curl -s -o /dev/null -m 5 -w '%{http_code}' "$@"; }
esperar() { local got; got=$("${@:3}"); [ "$got" = "$2" ] && ok "$1 -> $got" || mal "$1 -> $got (esperado $2)"; }
esperar "GET /health"                       200 c "$B/health"
esperar "GET / (frontend)"                  200 c "$B/"
esperar "branding sin key"                  401 c "$B/maestro/branding"
esperar "branding key invalida"             401 c -H 'X-Maestro-Api-Key: x' "$B/maestro/branding"
esperar "branding key valida"               200 c -H "X-Maestro-Api-Key: $MK" "$B/maestro/branding"
esperar "api sin token"                     401 c "$B/api/assets"
TOK=$(curl -s -m 5 -X POST "$B/login" -H 'Content-Type: application/json' \
      -d "{\"email\":\"admin@llyasoc.com\",\"password\":\"$SUPER\"}" | sed -n 's/.*"access_token":"\([^"]*\)".*/\1/p')
[ -n "$TOK" ] && ok "login superadmin (seeder) -> token" || mal "login superadmin sin token"
MALA="Zz9-$(hex 8)"   # bien formada pero no es la de nadie
esperar "login invalido"                    401 c -X POST "$B/login" -H 'Content-Type: application/json' -d "{\"email\":\"admin@llyasoc.com\",\"password\":\"$MALA\"}"
esperar "api con token"                     200 c -H "Authorization: Bearer $TOK" "$B/api/assets"
# cookie de sesion: nombre unico, HttpOnly, SameSite=Strict y SIN Secure en HTTP (MANUAL §6.4)
JAR=$(mktemp)
SC=$(curl -s -m 5 -D - -o /dev/null -c "$JAR" -X POST "$B/login" -H 'Content-Type: application/json' \
      -d "{\"email\":\"admin@llyasoc.com\",\"password\":\"$SUPER\"}" | tr -d '\r' | grep -i '^set-cookie:' | tr 'A-Z' 'a-z')
echo "$SC" | grep -q 'inventario_session=' && echo "$SC" | grep -q 'httponly' && echo "$SC" | grep -q 'samesite=strict' \
  && ok "cookie inventario_session HttpOnly + SameSite=Strict" || mal "cookie de sesion sin los flags esperados"
echo "$SC" | grep -q 'secure' && mal "cookie con Secure sobre HTTP (el login entraria en bucle)" || ok "cookie sin Secure en HTTP"
esperar "refresh con la cookie"             200 c -b "$JAR" -c "$JAR" -X POST -H 'X-Requested-With: fetch' "$B/auth/refresh"
esperar "refresh sin X-Requested-With"      401 c -b "$JAR" -X POST "$B/auth/refresh"
rm -f "$JAR"
esperar "metrics sin key"                   401 c "$B/metrics"
esperar "metrics con key"                   200 c -H "X-Maestro-Api-Key: $MK" "$B/metrics"
curl -s -m 5 -D - -o /dev/null "$B/health" | tr -d '\r' | grep -qi '^content-security-policy:' \
  && ok "cabeceras de seguridad presentes" || mal "falta Content-Security-Policy"
docker exec app-inventario-test sh -c 'touch /app/x 2>/dev/null' && mal "filesystem del contenedor escribible" || ok "filesystem read-only"
[ "$(docker exec app-inventario-test id -u)" != "0" ] && ok "corre como no-root (uid $(docker exec app-inventario-test id -u))" || mal "corre como root"
esperar "logout"                            200 c -X POST -H "Authorization: Bearer $TOK" "$B/auth/logout"
esperar "api tras logout"                   401 c -H "Authorization: Bearer $TOK" "$B/api/assets"
# 100 polls de health (Gate 2 usa >= 99% en <= 5s; aca es orientativo)
OKS=0; for i in $(seq 1 100); do [ "$(c "$B/health")" = 200 ] && OKS=$((OKS + 1)); done
[ "$OKS" -ge 99 ] && ok "health $OKS/100" || mal "health $OKS/100"
# seeder idempotente: reiniciar no rompe ni cambia la password
docker restart app-inventario-test >/dev/null
for i in $(seq 1 40); do [ "$(c "$B/health")" = 200 ] && break; sleep 3; done
T2=$(curl -s -m 5 -X POST "$B/login" -H 'Content-Type: application/json' \
      -d "{\"email\":\"admin@llyasoc.com\",\"password\":\"$SUPER\"}" | sed -n 's/.*"access_token":"\([^"]*\)".*/\1/p')
[ -n "$T2" ] && ok "tras reinicio el seeder no cambio la password" || mal "tras reinicio no entra el superadmin"
# volumenes con el nombre explicito del compose (no uno generado por -p)
docker volume inspect inventario-test_pgdata inventario-test_storage >/dev/null 2>&1 && ok "volumenes con name: explicito" || mal "volumenes con otro nombre"
# ningun secreto en los logs
LOGS=$(docker compose -f docker-compose.test.yml logs --no-color 2>&1)
FUGA=0; for s in "$SUPER" "$MK" "$TOK" "$(grep '^JWT_SECRET=' $ENVF | cut -d= -f2-)" "$(grep '^DB_PASSWORD=' $ENVF | cut -d= -f2-)"; do
  [ -n "$s" ] && echo "$LOGS" | grep -qF "$s" && FUGA=1; done
[ "$FUGA" = 0 ] && ok "logs sin secretos" || mal "hay secretos en los logs"
docker stats --no-stream --format '  info  {{.Name}}: {{.MemUsage}} CPU {{.CPUPerc}}' app-inventario-test db-inventario-test | tee -a "$OUT"

# ---------------------------------------------------------------- 6. tests del backend dentro de un contenedor (sin toolchain en la VM)
log "== 6. Tests (pytest)"
if docker run --rm -v "$PWD/app:/app" -w /app python:3.11-slim sh -c \
     "pip install -q -r backend/requirements-dev.txt && python -m pytest tests -q -p no:cacheprovider" >>"$OUT" 2>&1; then
  ok "pytest"; else mal "pytest fallo (ver $OUT)"; fi

# ---------------------------------------------------------------- teardown
docker compose -f docker-compose.test.yml down -v >>"$OUT" 2>&1
rm -f "$ENVF"; [ -e .env.previo ] && mv .env.previo "$ENVF"
log "== Resultado: $([ "$FALLAS" = 0 ] && echo 'TODO PASS' || echo "$FALLAS FAIL") (detalle en $OUT)"
exit "$FALLAS"
