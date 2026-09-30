# VM de ensayo (Docker) — Inventario LLYA v2

Para qué sirve: correr el ensayo local del MANUAL §5.0 y los checks de Gate 1 que usan Docker (build y tamaño de
imagen, Trivy, Gitleaks). Se necesita porque el servidor del Inventario de producción es una VM de VMware sin
virtualización anidada y con poca RAM libre, así que no puede correr Docker. Es solo para ensayos: ni datos reales
ni producción.

## 1. Pedido a VMware

| Recurso | Valor |
|---|---|
| Sistema | Ubuntu Server 24.04 LTS (64 bits) |
| vCPU | 2 |
| RAM | 4 GB (build del frontend + Postgres + Trivy) |
| Disco | 40 GB (imágenes Docker y base de Trivy) |
| Red | Misma LAN que el servidor del Inventario, con IP fija |
| Salida a internet | `download.docker.com`, `registry-1.docker.io`, `ghcr.io`, `pypi.org`, `files.pythonhosted.org`, `registry.npmjs.org` y `mirror.gcr.io` (base de vulnerabilidades de Trivy) |
| Acceso | SSH (puerto 22) desde el servidor del Inventario, con un usuario con sudo |
| Opcional | Salida a `10.100.1.124` (Dokploy), para probar puertos y la API desde ahí |

## 2. Instalar Docker (una vez)

```bash
sudo bash instalar-docker.sh <tu-usuario>
# cerrar sesión y volver a entrar
```

## 3. Llevar el repo a la VM

El repo todavía no tiene remote. Desde el servidor del Inventario:

```powershell
cd C:\AssetManagerV2
git bundle create $env:TEMP\inventario-v2.bundle --all
scp $env:TEMP\inventario-v2.bundle <usuario>@<ip-vm>:~/
```

En la VM:

```bash
git clone -b develop ~/inventario-v2.bundle inventario-v2   # la primera vez
# las siguientes: git -C inventario-v2 pull ~/inventario-v2.bundle develop
```

Cuando exista el fork en GitHub, clonar desde ahí.

## 4. Correr el ensayo

```bash
cd inventario-v2
bash herramientas/vm-ensayo/ensayo.sh
```

Genera secretos nuevos solo para el ensayo, levanta `docker-compose.test.yml` (el mismo archivo que va a Dokploy)
en el puerto 3110 **de la VM**, prueba el contrato y al final baja todo con `down -v`. Sale con código 0 si todo
dio PASS. El detalle queda en `ensayo-resultado.txt`, que no se commitea.

Para usar otro puerto: `PUERTO_ENSAYO=3150 bash herramientas/vm-ensayo/ensayo.sh`.

Queda fuera: el login en un navegador real (MANUAL §6.4). Se prueba contra el ambiente Test de Dokploy o dejando el
stack arriba en la VM (`docker compose -f docker-compose.test.yml up -d`) y entrando a `http://<ip-vm>:3110`.
