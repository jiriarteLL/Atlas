#!/bin/bash
# AssetManager - Instalador
echo "Instalando AssetManager Agent..."

curl -s -o /usr/local/bin/assetmanager-agent.sh http://192.168.0.88:8000/agent_linux.sh
chmod +x /usr/local/bin/assetmanager-agent.sh

echo "Ejecutando primera sincronizacion..."
/usr/local/bin/assetmanager-agent.sh

echo "Instalacion completada!"