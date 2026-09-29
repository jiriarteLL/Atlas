#!/bin/bash
# AssetManager - Instalador del agente Linux
# Uso: sudo ./instalar_linux.sh <url-del-inventario> <sync-key>
set -e
URL="${1:?Uso: instalar_linux.sh <url-del-inventario> <sync-key>}"
KEY="${2:?Uso: instalar_linux.sh <url-del-inventario> <sync-key>}"
URL="${URL%/}"
echo "Instalando AssetManager Agent desde $URL ..."

curl -fsS -o /usr/local/bin/assetmanager-agent.sh "$URL/agent_linux.sh"
chmod +x /usr/local/bin/assetmanager-agent.sh

# La clave queda solo legible por root, fuera del script.
umask 077
printf 'INVENTARIO_URL="%s"\nINVENTARIO_SYNC_KEY="%s"\n' "$URL" "$KEY" > /etc/assetmanager-agent.conf

echo "Ejecutando primera sincronizacion..."
/usr/local/bin/assetmanager-agent.sh

echo "Instalacion completada!"
