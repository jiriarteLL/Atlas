#!/bin/bash
# Atlas - Agente de inventario LLyA para Linux v5.1
# Manda el inventario del equipo a Atlas (POST /api/sync) con los mismos campos que el agente de Windows.
# Corre como root (lee /sys/class/dmi y los logs). Lo instala instalar_linux.sh: cron cada 2 horas y al arrancar.
#
# Configuracion: /etc/atlas-agent.conf (solo root)
#   ATLAS_URL="https://172.20.0.10:8743"
#   ATLAS_SYNC_KEY="<SYNC_API_KEY de Atlas>"
#   ATLAS_CERT_INTERNO=1      # 1 = aceptar el certificado interno (mkcert) del servidor
#
# Uso: atlas-agent.sh            sincroniza
#      atlas-agent.sh --probar   muestra el JSON sin enviarlo
VERSION="5.1"
LOG=/var/log/atlas-agente.log
[ -r /etc/atlas-agent.conf ] && . /etc/atlas-agent.conf
PROBAR=0; [ "$1" = "--probar" ] && PROBAR=1

log() { echo "$(date '+%Y-%m-%d %H:%M:%S')  $*" | tee -a "$LOG" 2>/dev/null; }
leer() { [ -r "$1" ] && tr -d '\0' < "$1" | sed 's/[[:space:]]*$//' ; }

# Texto -> string JSON (comillas, barras y caracteres de control)
json() {
    printf '%s' "$1" | awk 'BEGIN{ORS=""} {
        gsub(/\\/,"\\\\"); gsub(/"/,"\\\""); gsub(/\t/," "); gsub(/\r/,"");
        gsub(/[\001-\037]/,"");
        if (NR>1) printf " "; printf "%s", $0 }' | sed 's/^/"/; s/$/"/'
}

sede() {
    case "$(echo "$1" | tr '[:lower:]' '[:upper:]')" in
        LLCOR*|CIMPTO*|CAUDIT*|CADMIN*|CLEGALES*|CPYMES*|CMULETO*) echo "Corrientes" ;;
        LLROS*|RIMPTO*|RADMIN*|RAUDIT*|RAUDI*|RLEGALES*)           echo "Rosario" ;;
        LLTIG*|TIMPTO*|TAUDIT*|TADMIN*|TSISTEMAS*|PRECYTRANS*)     echo "Tigre" ;;
        RESG*|RSG*)                                                echo "Resguarda" ;;
        CBA*)                                                      echo "Cordoba" ;;
        NQN*)                                                      echo "Neuquen" ;;
        MIMPTO*|MADMIN*|MAUDIT*|MLEGALES*|MPYMES*|MNMULETO*)       echo "Mendoza" ;;
        *)                                                         echo "CABA" ;;
    esac
}

# ---- Identidad y hardware
NOMBRE=$(hostname -s 2>/dev/null || hostname)
D=/sys/class/dmi/id
MARCA=$(leer $D/sys_vendor)
MODELO=$(leer $D/product_name)
VERSION_PROD=$(leer $D/product_version)          # Lenovo pone ahi el nombre comercial ("ThinkPad E14 Gen 6")
case "$VERSION_PROD" in ""|None|"Not Specified"|"System Version"|"To be filled"*|[0-9.]*) ;; *) [ "$VERSION_PROD" != "$MODELO" ] && MODELO="$VERSION_PROD" ;; esac
SERIAL=$(leer $D/product_serial)
case "$SERIAL" in ""|"Not Specified"|"Default string"|"To be filled"*|0|00000000) SERIAL=$(leer /etc/machine-id) ;; esac
CPU=$(grep -m1 "model name" /proc/cpuinfo 2>/dev/null | cut -d: -f2- | xargs)
RAM="$(awk '/MemTotal/{printf "%d", $2/1048576 + 0.5}' /proc/meminfo)GB"
DISCO=$(lsblk -dbno SIZE,TYPE 2>/dev/null | awk '$2=="disk"{printf "%s%dGB", (n++?" + ":""), $1/1e9}')

VIRT=$(systemd-detect-virt 2>/dev/null || echo none)
CHASIS=$(leer $D/chassis_type)
case "$CHASIS" in 8|9|10|11|12|14|18|21|30|31|32) TIPO="Notebook" ;; *) TIPO="Servidor" ;; esac
[ "$VIRT" != "none" ] && TIPO="Servidor"

# ---- Sistema
SO=$( . /etc/os-release 2>/dev/null; echo "${PRETTY_NAME:-$(uname -s)}" )
SO_VERSION=$(uname -r)
ARCH=$(uname -m)

# ---- Red
GW=$(ip route show default 2>/dev/null | awk '/default/{print $3; exit}')
DEV=$(ip route show default 2>/dev/null | awk '/default/{print $5; exit}')
IP=$(ip -4 -o addr show dev "$DEV" 2>/dev/null | awk '{split($4,a,"/"); print a[1]; exit}')
[ -z "$IP" ] && IP=$(hostname -I 2>/dev/null | awk '{print $1}')
MAC=$(leer /sys/class/net/$DEV/address | tr '[:lower:]' '[:upper:]')
IP_PUBLICA=$(curl -s --max-time 8 https://api.ipify.org 2>/dev/null | grep -E '^[0-9]+(\.[0-9]+){3}$')
RED=$(realm list 2>/dev/null | awk '/domain-name/{print $2; exit}')
[ -z "$RED" ] && RED=$(dnsdomainname 2>/dev/null)

# ---- Actividad
ULT_REINICIO=$(uptime -s 2>/dev/null | cut -c1-16)
ULT_LINEA=$(last -w -F 2>/dev/null | grep -vE '^(reboot|wtmp|$)' | head -1)
USUARIO=$(echo "$ULT_LINEA" | awk '{print $1}')
ULT_LOGIN=$(echo "$ULT_LINEA" | awk '{print $5" "$6" "$8" "$7}' | xargs -I{} date -d "{}" '+%Y-%m-%d %H:%M' 2>/dev/null)

# ---- Paquetes instalados -> lista JSON [{"nombre","version"}]
if command -v dpkg-query >/dev/null 2>&1; then
    PAQ=$(dpkg-query -W -f='${binary:Package}\t${Version}\n' 2>/dev/null)
elif command -v rpm >/dev/null 2>&1; then
    PAQ=$(rpm -qa --queryformat '%{NAME}\t%{VERSION}-%{RELEASE}\n' 2>/dev/null)
fi
SOFTWARE=$(printf '%s\n' "$PAQ" | sort -u | awk -F'\t' 'BEGIN{ORS=""; print "["} $1!=""{
    gsub(/\\/,"\\\\",$1); gsub(/"/,"\\\"",$1); gsub(/\\/,"\\\\",$2); gsub(/"/,"\\\"",$2);
    printf "%s{\"nombre\":\"%s\",\"version\":\"%s\",\"fecha\":\"\"}", (n++?",":""), $1, $2 } END{print "]"}')

PAYLOAD="{\"nombre\":$(json "$NOMBRE"),\"tipo\":$(json "$TIPO"),\"marca\":$(json "$MARCA"),\"modelo\":$(json "$MODELO"),\
\"serial\":$(json "$SERIAL"),\"cpu\":$(json "$CPU"),\"ram\":$(json "$RAM"),\"disco\":$(json "$DISCO"),\
\"so\":$(json "$SO"),\"so_version\":$(json "$SO_VERSION"),\"so_arquitectura\":$(json "$ARCH"),\
\"ip\":$(json "$IP"),\"red\":$(json "$RED"),\"grupo\":$(json "Linux $VIRT"),\"usuario\":$(json "$USUARIO"),\"usuario_alt\":\"\",\
\"estado\":\"Activo\",\"ubicacion\":$(json "$(sede "$NOMBRE")"),\"comentarios\":\"\",\"garantia\":\"\",\
\"monitores\":\"\",\"impresoras\":\"\",\"software\":$SOFTWARE,\"cifrado\":\"\",\"tpm\":\"\",\
\"ip_publica\":$(json "$IP_PUBLICA"),\"mac\":$(json "$MAC"),\"gateway\":$(json "$GW"),\"ou_ad\":\"\",\
\"ultimo_reinicio\":$(json "$ULT_REINICIO"),\"ultimo_login\":$(json "$ULT_LOGIN")}"

if [ "$PROBAR" = 1 ]; then
    printf '%s\n' "$PAYLOAD" | sed 's/"software":\[[^]]*\]/"software":[...]/'
    echo "(paquetes: $(printf '%s\n' "$PAQ" | grep -c .))"
    exit 0
fi

[ -z "$ATLAS_URL" ] || [ -z "$ATLAS_SYNC_KEY" ] && { log "ERROR: falta ATLAS_URL o ATLAS_SYNC_KEY en /etc/atlas-agent.conf"; exit 2; }
INSEGURO=""; [ "$ATLAS_CERT_INTERNO" = "1" ] && INSEGURO="-k"
for i in 1 2 3; do
    CODIGO=$(printf '%s' "$PAYLOAD" | curl -s $INSEGURO -o /dev/null -w "%{http_code}" --max-time 30 -X POST "${ATLAS_URL%/}/api/sync" \
        -H "Content-Type: application/json; charset=utf-8" -H "X-Sync-Key: $ATLAS_SYNC_KEY" \
        -H "User-Agent: LLyA-Atlas-Agent-Linux/$VERSION" --data-binary @-)
    case "$CODIGO" in
        200) log "OK - Sincronizado en Atlas: $NOMBRE ($TIPO, $(sede "$NOMBRE")) -> $ATLAS_URL"; exit 0 ;;
        401|413|422) break ;;
    esac
    [ $i -lt 3 ] && sleep $((10 * i))
done
log "ERROR al enviar a $ATLAS_URL: HTTP $CODIGO"
exit 1
