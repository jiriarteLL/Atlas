#!/bin/bash
# Atlas - Instalador del agente Linux (como root)
# Uso: sudo ./instalar_linux.sh <url-de-atlas> <sync-key> [cert-interno 0|1]
#   ej.: sudo ./instalar_linux.sh https://172.20.0.10:8743 xxxxx 1
# Baja el agente desde Atlas, guarda la configuracion (solo root), programa cron (cada 2 h y al arrancar)
# y hace la primera sincronizacion. Es idempotente: se puede volver a correr para actualizar.
set -e
URL="${1:?Uso: instalar_linux.sh <url-de-atlas> <sync-key> [cert-interno 0|1]}"
KEY="${2:?Uso: instalar_linux.sh <url-de-atlas> <sync-key> [cert-interno 0|1]}"
CERT="${3:-0}"
URL="${URL%/}"
[ "$(id -u)" = 0 ] || { echo "Correr como root (sudo)."; exit 1; }
INSEGURO=""; [ "$CERT" = "1" ] && INSEGURO="-k"

echo "Instalando el agente de Atlas desde $URL ..."
curl -fsS $INSEGURO -o /usr/local/bin/atlas-agent.sh.nuevo "$URL/agent_linux.sh"
head -1 /usr/local/bin/atlas-agent.sh.nuevo | grep -q '^#!/bin/bash' || { echo "Descarga invalida"; exit 1; }
mv /usr/local/bin/atlas-agent.sh.nuevo /usr/local/bin/atlas-agent.sh
chmod 755 /usr/local/bin/atlas-agent.sh

( umask 077; printf 'ATLAS_URL="%s"\nATLAS_SYNC_KEY="%s"\nATLAS_CERT_INTERNO=%s\n' "$URL" "$KEY" "$CERT" > /etc/atlas-agent.conf )
chmod 600 /etc/atlas-agent.conf

# Cada 2 horas (minuto al azar para no llegar todos juntos) y 5 minutos despues de arrancar.
MIN=$(( $(od -An -N1 -tu1 /dev/urandom) % 60 ))
cat > /etc/cron.d/atlas-agent <<EOF
# Atlas - inventario LLyA
$MIN */2 * * * root /usr/local/bin/atlas-agent.sh >/dev/null 2>&1
@reboot root sleep 300 && /usr/local/bin/atlas-agent.sh >/dev/null 2>&1
EOF
chmod 644 /etc/cron.d/atlas-agent
# Quita el cron del agente viejo (AssetManager) si estaba
crontab -l 2>/dev/null | grep -v assetmanager-agent | crontab - 2>/dev/null || true

echo "Primera sincronizacion..."
/usr/local/bin/atlas-agent.sh && echo "Instalacion completa. Log: /var/log/atlas-agente.log"
