#!/bin/bash
# AssetManager Agent v1.0 - Linux
# Configuracion: /etc/assetmanager-agent.conf (la escribe instalar_linux.sh) o variables de entorno.
[ -r /etc/assetmanager-agent.conf ] && . /etc/assetmanager-agent.conf
SERVER="${INVENTARIO_URL:?Falta INVENTARIO_URL}"
SYNC_KEY="${INVENTARIO_SYNC_KEY:?Falta INVENTARIO_SYNC_KEY}"
SERVER="${SERVER%/}"

NOMBRE=$(hostname -s)
SERIAL=$(sudo dmidecode -s system-serial-number 2>/dev/null | tr -d '[:space:]' || echo "sin-serial")
CPU=$(grep -m1 "model name" /proc/cpuinfo 2>/dev/null | cut -d: -f2 | xargs || echo "")
RAM=$(free -g 2>/dev/null | awk '/Mem:/{print $2"GB"}' || echo "")
DISCO=$(df -BG / 2>/dev/null | awk 'NR==2{gsub("G","",$2); print $2"GB"}' || echo "")
IP=$(hostname -I 2>/dev/null | awk '{print $1}' || echo "")
SO=$(. /etc/os-release 2>/dev/null && echo "$NAME $VERSION" || uname -s)
SO_VERSION=$(uname -r)
ARCH=$(uname -m)
USUARIO=$(whoami)
DOMINIO=$(realm list 2>/dev/null | grep "domain-name" | awk '{print $2}' || echo "")
MARCA=$(sudo dmidecode -s system-manufacturer 2>/dev/null | xargs || echo "")
MODELO=$(sudo dmidecode -s system-product-name 2>/dev/null | xargs || echo "")

detect_sede() {
    N=$(echo "$1" | tr '[:lower:]' '[:upper:]')
    case "$N" in
        RSG*)                        echo "Resguarda" ;;
        CBA*|CBAIMPTO*|CBAAUDIT*)    echo "Cordoba" ;;
        NQN*)                        echo "Neuquen" ;;
        RIMPTO*|RADMIN*|RAUDIT*)     echo "Rosario" ;;
        CIMPTO*|CAUDIT*|CADMIN*)     echo "Corrientes" ;;
        TIMPTO*|TAUDIT*|TADMIN*)     echo "Tigre" ;;
        MIMPTO*|MADMIN*|MAUDIT*)     echo "Mendoza" ;;
        *)                           echo "CABA" ;;
    esac
}

UBICACION=$(detect_sede "$NOMBRE")

SOFTWARE=$(dpkg -l 2>/dev/null | awk 'NR>5 && $2!="" && $3!=""{print $2"|||"$3"|||"}' | tr '\n' '~' | sed 's/~$//' \
        || rpm -qa --queryformat '%{NAME}|||%{VERSION}|||\n' 2>/dev/null | tr '\n' '~' | sed 's/~$//' \
        || echo "")

# Escapar caracteres especiales
SOFTWARE=$(echo "$SOFTWARE" | sed 's/"/\\"/g' | tr -d '\n\r')
CPU=$(echo "$CPU" | sed 's/"/\\"/g')
SO=$(echo "$SO" | sed 's/"/\\"/g')
MARCA=$(echo "$MARCA" | sed 's/"/\\"/g')
MODELO=$(echo "$MODELO" | sed 's/"/\\"/g')

PAYLOAD="{\"nombre\":\"$NOMBRE\",\"tipo\":\"Servidor\",\"marca\":\"$MARCA\",\"modelo\":\"$MODELO\",\"serial\":\"$SERIAL\",\"cpu\":\"$CPU\",\"ram\":\"$RAM\",\"disco\":\"$DISCO\",\"so\":\"$SO\",\"so_version\":\"$SO_VERSION\",\"so_arquitectura\":\"$ARCH\",\"ip\":\"$IP\",\"red\":\"$DOMINIO\",\"grupo\":\"\",\"usuario\":\"$USUARIO\",\"usuario_alt\":\"\",\"estado\":\"Activo\",\"ubicacion\":\"$UBICACION\",\"comentarios\":\"\",\"garantia\":\"\",\"monitores\":\"\",\"impresoras\":\"\",\"software\":\"$SOFTWARE\"}"

RESPONSE=$(curl -s -o /dev/null -w "%{http_code}" -X POST "$SERVER/api/sync" \
  -H "Content-Type: application/json; charset=utf-8" \
  -H "X-Sync-Key: $SYNC_KEY" \
  -d "$PAYLOAD")

if [ "$RESPONSE" = "200" ]; then
    echo "OK - Sincronizado: $NOMBRE ($UBICACION)"
else
    echo "ERROR - Codigo HTTP: $RESPONSE"
fi

# Programar cron si no existe
if ! crontab -l 2>/dev/null | grep -q "assetmanager"; then
    (crontab -l 2>/dev/null; echo "0 10 * * * /usr/local/bin/assetmanager-agent.sh") | crontab -
    echo "Cron programado - se ejecutara diariamente a las 10am"
fi