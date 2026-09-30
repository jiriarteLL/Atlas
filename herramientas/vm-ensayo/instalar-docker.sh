#!/bin/bash
# Instala Docker Engine + plugin compose en Ubuntu 24.04 (repo oficial de Docker).
# Uso: sudo bash instalar-docker.sh <usuario-que-va-a-usar-docker>
set -euo pipefail
USUARIO="${1:?Uso: sudo bash instalar-docker.sh <usuario>}"

apt-get update
apt-get install -y ca-certificates curl git openssl
install -m 0755 -d /etc/apt/keyrings
curl -fsSL https://download.docker.com/linux/ubuntu/gpg -o /etc/apt/keyrings/docker.asc
chmod a+r /etc/apt/keyrings/docker.asc
. /etc/os-release
echo "deb [arch=$(dpkg --print-architecture) signed-by=/etc/apt/keyrings/docker.asc] https://download.docker.com/linux/ubuntu ${VERSION_CODENAME} stable" \
  > /etc/apt/sources.list.d/docker.list
apt-get update
apt-get install -y docker-ce docker-ce-cli containerd.io docker-buildx-plugin docker-compose-plugin
usermod -aG docker "$USUARIO"
systemctl enable --now docker

docker version --format 'Docker {{.Server.Version}}'
docker compose version
echo "Listo. $USUARIO tiene que cerrar sesion y volver a entrar para usar docker sin sudo."
