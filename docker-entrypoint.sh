#!/bin/sh
# Espera la base, corre migracion + seeder y recien ahi levanta la app.
# Si el seeder falla (password del superadmin ausente o debil) el contenedor NO arranca.
set -e
cd /app/backend

i=0
until python -c "import database; database.engine.connect().close()" 2>/dev/null; do
    i=$((i + 1))
    if [ "$i" -ge 30 ]; then
        echo "[entrypoint] la base no respondio en 60s" >&2
        exit 1
    fi
    sleep 2
done

python seed.py
exec "$@"
