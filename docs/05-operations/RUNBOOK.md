# RUNBOOK.md — Maestro Platform V1

> **Fase:** 05-operations
> **Versión:** v1.0.0-rc.1
> **Fecha:** 2026-04-18
> **Audiencia:** operador humano (1 persona V1) + Claude Code asistente
> **Alcance V1 (DEC-017):** 1 empresa × 7 apps huésped, VPS único operado manualmente (DEC-011).

Este runbook cubre el ciclo operativo diario y los procedimientos de respuesta a las alertas definidas en `MONITORING.md §3.1`. No reemplaza al `INCIDENT_PLAYBOOK.md` — complementa §3.4 (Resolución).

---

## 1. Puesta en marcha (cold start)

### 1.1 Prerrequisitos del host VPS

- Debian 12 / Ubuntu 22.04 actualizado
- Docker Engine ≥ 25 + Compose plugin
- Usuario `maestro` en grupo `docker` (no root para operación diaria)
- Volumen `/var/lib/docker` en disco con ≥ 50 GB libres
- DNS apuntando a `<dominio>` y `*.<dominio>` hacia IP del VPS
- Puertos 80 y 443 abiertos en firewall

### 1.2 Secuencia de arranque

```bash
cd /opt/maestro
git pull origin main                   # si aplica (DEC-011 = deploy manual)
cp .env.production.example .env.production  # solo primera vez
# editar .env.production con secretos reales

# 1) Stack principal
docker compose -f docker-compose.prod.yml --env-file .env.production up -d

# 2) Stack de observabilidad
docker compose -f docker-compose.obs.yml --env-file .env.production up -d

# 3) Verificar
docker compose -f docker-compose.prod.yml ps
curl -sf https://<dominio>/api/platform/health | jq .
```

### 1.3 Parada ordenada

```bash
# Drenar workers primero (terminan jobs en curso)
docker compose -f docker-compose.prod.yml exec maestro-worker \
  php artisan queue:restart

# Parar servicios (orden: worker → scheduler → api → traefik → db/redis)
docker compose -f docker-compose.prod.yml stop \
  maestro-worker maestro-scheduler maestro-api maestro-traefik
docker compose -f docker-compose.prod.yml stop maestro-postgres maestro-redis

# Obs stack
docker compose -f docker-compose.obs.yml stop
```

### 1.4 Parada de emergencia

```bash
docker compose -f docker-compose.prod.yml down        # mantiene volúmenes
# NUNCA: docker compose down -v (destruye volúmenes = pierde DB)
```

---

## 2. Verificación diaria (smoke check)

Check rápido (≤ 2 min) que el operador corre una vez al día:

```bash
# 1) Todos los containers up
docker compose -f docker-compose.prod.yml ps \
  | awk 'NR>1 && $4 !~ /Up/ { print "NOT UP:", $0; exit 1 }'

# 2) Health del API
curl -sf https://<dominio>/api/platform/health | jq -e '.status=="ok"'

# 3) Disco < 70%
df -h / | awk 'NR==2 && int($5)>70 { print "DISK WARN:", $5; exit 1 }'

# 4) Colas sin backlog
docker compose -f docker-compose.prod.yml exec -T maestro-api \
  php artisan queue:monitor redis:default,redis:hooks,redis:provisioning

# 5) Grafana accesible
curl -sfk https://grafana.<dominio>/api/health | jq -e '.database=="ok"'
```

Si falla cualquiera → abrir `INCIDENT_PLAYBOOK.md` y triaje.

---

## 3. Backups y restauración

### 3.1 Alcance (DEC-019)

- Retención: **30 días** para backups operativos.
- Post-destrucción de instancia huésped: **90 días** de retención de su volumen de DB antes de purga final.
- No excede los mínimos (política de retención agresiva).

### 3.2 Backup diario programado

Cron del host (fuera de Docker):

```bash
# /etc/cron.d/maestro-backup
15 2 * * * maestro /opt/maestro/scripts/backup-daily.sh >> /var/log/maestro-backup.log 2>&1
```

Contenido `backup-daily.sh`:

```bash
#!/usr/bin/env bash
set -euo pipefail
DATE=$(date -u +%Y%m%d-%H%M)
DEST=/var/backups/maestro/$DATE
mkdir -p "$DEST"

# DB del Maestro
docker compose -f /opt/maestro/docker-compose.prod.yml exec -T maestro-postgres \
  pg_dump -U "$POSTGRES_USER" -Fc "$POSTGRES_DB" > "$DEST/maestro.dump"

# DBs de apps huésped (1 por instancia activa)
docker compose -f /opt/maestro/docker-compose.prod.yml exec -T maestro-api \
  php artisan maestro:instances:backup --dest="$DEST/instances"

# Volumen obs (Grafana dashboards provisionados + Loki últimos 7d)
docker run --rm -v obs-grafana-data:/src:ro -v "$DEST":/dst alpine \
  tar czf /dst/grafana.tgz -C /src .

# Permisos restrictivos: solo el operador lee los dumps
chown -R maestro:maestro /var/backups/maestro/
find /var/backups/maestro/ -type f -exec chmod 0600 {} +
find /var/backups/maestro/ -type d -exec chmod 0700 {} +

# Rotación (>30d se borra)
find /var/backups/maestro -maxdepth 1 -type d -mtime +30 -exec rm -rf {} +
```

### 3.3 Restauración del Maestro DB

```bash
# 1) Poner el API en mantenimiento
docker compose -f docker-compose.prod.yml exec maestro-api \
  php artisan down --secret="<token>"

# 2) Parar workers
docker compose -f docker-compose.prod.yml stop maestro-worker maestro-scheduler

# 3) Restaurar
docker compose -f docker-compose.prod.yml exec -T maestro-postgres \
  pg_restore -U "$POSTGRES_USER" -d "$POSTGRES_DB" --clean --if-exists \
  < /var/backups/maestro/<DATE>/maestro.dump

# 4) Reanudar
docker compose -f docker-compose.prod.yml start maestro-worker maestro-scheduler
docker compose -f docker-compose.prod.yml exec maestro-api php artisan up
```

### 3.4 Restauración de una instancia huésped

```bash
# Identificar instancia
docker compose exec maestro-api php artisan tinker --execute="
  \App\Modules\Provisioning\Models\AppInstance::where('slug','<slug>')->first();
"

# Restaurar volumen (dentro de los 90d post-destrucción)
docker run --rm -v <volumen_huesped>:/dst -v /var/backups/maestro/<DATE>/instances:/src:ro \
  alpine sh -c "tar xzf /src/<slug>.tgz -C /dst"

# Reconstruir container de la app
docker compose exec maestro-api php artisan maestro:instances:restart --slug=<slug>
```

### 3.5 Verificación mensual (DRY-RUN de restore)

El primer sábado de cada mes, el operador ejecuta una restauración de prueba a un entorno stage (`stage.<dominio>`) y verifica login + query simple. Registra en `docs/05-operations/INCIDENTS/` si falla.

---

## 4. Operaciones comunes

### 4.1 Deploy de nueva versión

```bash
# 1) Pull de imagen nueva (GHCR)
docker pull ghcr.io/<org>/maestro-api:vX.Y.Z
docker pull ghcr.io/<org>/maestro-portal:vX.Y.Z

# 2) Actualizar IMAGE_TAG
sed -i "s/^IMAGE_TAG=.*/IMAGE_TAG=vX.Y.Z/" .env.production

# 3) Migraciones (si aplica)
docker compose -f docker-compose.prod.yml run --rm maestro-api \
  php artisan migrate --force

# 4) Rolling update del API (3 réplicas)
docker compose -f docker-compose.prod.yml up -d --no-deps --scale maestro-api=3 maestro-api

# 5) Verificar health x3 polls
for i in 1 2 3; do curl -sf https://<dominio>/api/platform/health || exit 1; sleep 5; done
```

### 4.2 Rollback rápido

```bash
# 1) Volver a IMAGE_TAG anterior
sed -i "s/^IMAGE_TAG=.*/IMAGE_TAG=v<anterior>/" .env.production

# 2) Si la migración reciente rompe: revertirla ANTES de bajar código
docker compose exec maestro-api php artisan migrate:rollback --step=1 --force

# 3) Redeployar
docker compose -f docker-compose.prod.yml up -d --no-deps maestro-api maestro-worker maestro-scheduler
```

> **Nota:** `just rollback vX.Y.Z` (1-click) es **deuda V1.1** (TD-012). En V1 se ejecuta manual.

### 4.3 Rotación de secretos

- **`MAESTRO_ENCRYPTION_KEY`:** re-cifra `webhook_secret_encrypted` de todas las apps. Ver RUNBOOK §6.8.
- **`GRAFANA_ADMIN_PASSWORD`:** editar `.env.production` → `docker compose up -d --force-recreate obs-grafana`.
- **Passport keys:** `php artisan passport:keys --force` + reiniciar API. Invalida todos los tokens.
- **DB passwords de instancias huésped:** por diseño son aleatorias y se rotan al re-provisionar la instancia.

### 4.4 Escalado manual (V1)

V1 corre con **3 réplicas de `maestro-api`** (justificado por performance-analyst en Fase 04 para 50 concurrentes). Cambios manuales:

```bash
# Escalar API
docker compose -f docker-compose.prod.yml up -d --scale maestro-api=4 maestro-api

# Escalar workers (si backlog sostenido)
docker compose -f docker-compose.prod.yml up -d --scale maestro-worker=2 maestro-worker
```

> **Regla (DEC-017):** con 1 empresa × 7 apps V1, escalar más allá de 3 API / 2 workers es síntoma de bug, no de demanda. Investigar antes de escalar.

### 4.5 Ventanas de mantenimiento (DEC-020)

V1 **no exige zero-downtime**. Política:

- Ventanas programadas fuera de horario laboral (21:00-07:00 UTC-3).
- Anuncio al tenant por email ≥ 24h antes.
- Modo mantenimiento Laravel: `php artisan down --render="maintenance"`.

---

## 5. Troubleshooting general

| Síntoma | Primera sonda | Siguiente paso |
|---|---|---|
| API responde 502 | `docker compose logs --tail=100 maestro-traefik` | RUNBOOK §6.1 |
| API responde 500 intermitente | `docker compose logs --tail=200 maestro-api \| grep ERROR` | Revisar Loki por `request_id` del user |
| Provisioning cuelga | `docker compose exec maestro-api php artisan queue:monitor redis:provisioning` | Si backlog → revisar `obs-cadvisor` para un container huésped trabado |
| Login falla masivamente | `php artisan passport:purge` solo si se rotó key | Verificar `AUTH_ENDPOINT_URL` y clock skew |
| Webhook delivery cae | `php artisan tinker --execute="\App\Models\Hook::failed()->count();"` | Revisar runbook de colas §6.4 |
| Grafana down | `docker compose -f docker-compose.obs.yml logs obs-grafana` | Re-crear container; volumen `obs-grafana-data` preserva dashboards |

---

## 6. Runbooks específicos por alerta

Referencias desde `MONITORING.md §3.1`.

### 6.1 `MaestroContainerDown` (SEV1)

**Disparo:** container no visto por cAdvisor en >2 min.

1. `docker compose -f docker-compose.prod.yml ps` — ¿qué container falta?
2. `docker compose logs --tail=200 <servicio>` — busca error fatal, OOM, panic.
3. **Si OOM-killed:** ver §6.2.
4. **Si crash por config:** revertir último deploy (§4.2).
5. **Si DB corrupta:** restaurar (§3.3) + postmortem SEV1.
6. Reiniciar: `docker compose -f docker-compose.prod.yml up -d <servicio>`.
7. Verificar health x3 polls antes de cerrar.

### 6.2 `MaestroContainerMemoryHigh` (SEV2)

**Disparo:** container memoria > 80% límite x 10 min.

1. `docker stats --no-stream <container>` — confirmar lectura.
2. Identificar causa:
   - **API:** revisar queries N+1 en Loki (`duration > 1s`), revisar cache hit ratio.
   - **Worker:** job específico grande (revisar `failed_jobs`).
   - **Redis:** ¿memoria de Redis cerca de `maxmemory`? → aplicar política `allkeys-lru`.
3. Si transitorio (picos de provisioning): aceptar.
4. Si sostenido: escalar horizontalmente (§4.4) y abrir ticket a `tech-debt-manager` (TD-###).
5. **Nunca** subir el límite sin análisis: enmascara el root cause.

### 6.3 `MaestroContainerCPUHigh` / `HostLoadHigh` (SEV3)

**Disparo:** CPU > 90% x 15 min, o load5 > 1.5×cores x 15 min.

1. `docker stats --no-stream` + `top -b -n1 | head -20` en host.
2. Identificar top consumidor:
   - **Proceso del Maestro:** buscar regex costosos, JSON decode en loop, llamadas síncronas externas.
   - **Worker:** job repeticionado (failed → retry → failed).
3. Mitigación: pausar worker problemático, matar query PG bloqueante.
4. Si la causa es un tenant específico (DEC-017 = 1 tenant V1, pero prep para V2+): revisar rate limiting.
5. Documentar en postmortem si impacto >30 min.

### 6.4 `MaestroContainerRestarting` (SEV2)

**Disparo:** container reiniciado en últimos 15 min.

1. `docker compose ps` — ¿restart loop o reinicio puntual?
2. `docker inspect <container> --format '{{.RestartCount}} {{.State.ExitCode}}'`.
3. **Exit 137:** OOM-killed → §6.2.
4. **Exit 143:** SIGTERM (deploy/parada intencional) → ignorar si fue manual.
5. **Exit otro + loop:** ver logs. Si no arranca: rollback (§4.2).
6. Si causa config inválida: revertir `.env.production` desde git.
7. Abrir postmortem si SEV ≥2.

### 6.5 `HostDiskAlmostFull` / `HostDiskGrowthFast`

**SEV1** si ≥ 85% x 5 min; **SEV3** predictivo si llena en <24h.

1. `df -h` + `du -sh /var/lib/docker/* 2>/dev/null | sort -h | tail`.
2. Top consumidores típicos:
   - `overlay2/`: limpiar con `docker system prune -af --volumes=false` (cuidado con volúmenes).
   - `volumes/obs-prometheus-data`: Prometheus retiene 30d → si sube anómalo, revisar cardinalidad de labels.
   - `volumes/obs-loki-data`: Loki 30d → idem, revisar labels runaway.
   - Backups: `ls -la /var/backups/maestro/`.
3. Purga inmediata: borrar backups > 30d (ya hace `backup-daily.sh`).
4. Si crítico: `docker image prune -a --filter "until=168h"`.
5. **Nunca:** `rm -rf /var/lib/docker/containers/*` con containers corriendo.

### 6.6 `HostMemoryHigh` (SEV2)

**Disparo:** memoria host > 90% x 10 min.

1. `free -m` + `top -b -n1 -o %MEM | head -15`.
2. Si causa fuera de Docker: investigar procesos del host (raro en VPS dedicado).
3. Si causa es Docker: revisar §6.2 por container.
4. Acción de emergencia: parar `obs-cadvisor` (es el más prescindible); nunca parar `maestro-postgres`.
5. Si swap > 50% usado → rebootear VPS en ventana de mantenimiento.

### 6.7 `PrometheusTargetDown` (SEV2)

**Disparo:** scrape target `up=0` x 5 min.

1. `docker compose -f docker-compose.obs.yml logs obs-prometheus | tail -50`.
2. Verificar red: `docker exec obs-prometheus wget -qO- <target>:<puerto>/metrics | head`.
3. Target típicos:
   - `maestro-api:8080/metrics` → probable 404 hasta TD-015 (deuda V1.1, endpoint no implementado). Alerta `MaestroAPIMetricsMissing` lo cubre como SEV3 informativa.
   - `maestro-traefik:8082/metrics` → verificar `metrics.prometheus` en `traefik.yml` (TD-010).
   - `obs-cadvisor:8080` / `obs-node-exporter:9100` → reiniciar el exporter.
4. Si es target legítimo caído (e.g. cadvisor): `docker compose -f docker-compose.obs.yml restart obs-cadvisor`.

### 6.8 Rotación de `MAESTRO_ENCRYPTION_KEY`

1. Anunciar ventana de mantenimiento (DEC-020).
2. Backup DB (§3.2 manual one-shot).
3. Ejecutar comando de re-cifrado:
   ```bash
   docker compose exec maestro-api php artisan maestro:rotate-encryption-key \
     --old="<actual>" --new="<nueva>"
   ```
4. Actualizar `.env.production` con nueva key.
5. `docker compose up -d --force-recreate maestro-api maestro-worker maestro-scheduler`.
6. Forzar re-login: `php artisan passport:purge` (invalida refresh tokens).
7. Verificar con un login de prueba y dispatch de un hook de test.

---

## 7. Contactos y escalamientos

| Dominio | A quién | Cuándo |
|---|---|---|
| Plataforma Azure (VPS) | soporte del proveedor | Caída infra no-Docker |
| Dominio / DNS | registrador del dominio | Pérdida de resolución DNS |
| Certificados | Let's Encrypt logs via Traefik | Falla renovación ACME |
| Compliance (GDPR) | legal interno | Brecha confirmada o subpoena |
| Escalamiento técnico | Claude Code (prompt en INCIDENT_PLAYBOOK §5) | Bloqueo del operador humano |

---

## 8. Referencias cruzadas

- `docs/05-operations/MONITORING.md` — stack de observabilidad, métricas, alertas, dashboards
- `docs/05-operations/INCIDENT_PLAYBOOK.md` — niveles severidad, flujo respuesta, postmortems
- `docs/05-operations/TECH_DEBT.md` — deuda técnica inventariada (TD-###)
- `docs/05-operations/templates/POSTMORTEM_TEMPLATE.md` — template blameless
- `docs/04-delivery/INFRASTRUCTURE.md` — topología y secretos
- `docs/04-delivery/RELEASE_NOTES.md` — procedimiento de release
- `CLAUDE.md` — contexto global del framework
