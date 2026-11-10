# Conectores de servidores (Atlas, fase D)

Atlas trae datos de servidores y VM desde tres fuentes externas, además del agente. Cada conector queda **apagado**
hasta que se configura y siempre usa un usuario de **solo lectura**. Las claves nunca se guardan en Atlas: van en un
archivo aparte (una sola línea) con permisos solo para SYSTEM y Administradores.

Se ve el estado de cada conector en **Activos → Servidores y VM → Conectores** (qué falta configurar, última corrida,
errores). Corre solo cada `CONECTORES_CADA_HORAS` (6 por defecto) o con el botón **Actualizar ahora**.

## Dónde van las claves (en la VM de Atlas)

```powershell
New-Item -ItemType Directory -Force C:\Atlas\secretos | Out-Null
Set-Content C:\Atlas\secretos\vcenter.txt 'LA-CLAVE' -Encoding UTF8          # una por conector
icacls C:\Atlas\secretos /inheritance:r /grant:r "*S-1-5-18:(OI)(CI)F" "*S-1-5-32-544:(OI)(CI)F"
```

Las variables van en `C:\Atlas\.env` y se aplican reiniciando los servicios `Atlas-HTTP` y `Atlas-HTTPS`.

## 1. VMware vCenter (VMs, hosts ESXi)

**Qué pedir:** un usuario de vCenter (por ejemplo `atlas-lectura@vsphere.local`) con el rol **Read-only** asignado
en la **raíz** del inventario, con propagación a los hijos.

```ini
VCENTER_URL=https://<ip o nombre del vCenter>
VCENTER_USUARIO=atlas-lectura@vsphere.local
VCENTER_CLAVE_ARCHIVO=C:\Atlas\secretos\vcenter.txt
VCENTER_VERIFICAR_CERT=0      # 1 si el vCenter tiene un certificado que la VM reconoce
```

Usa la API REST de vSphere 7 (`/api/session`, `/api/vcenter/vm`, `/api/vcenter/host`, `/api/vcenter/cluster`).
Cada VM se cruza con el activo del agente por la serie (`VMware-42 1d …` = bios_uuid de la VM). Las VM sin agente
(Linux, appliances) se dan de alta como activo tipo **VM**; si después se instala el agente se unifican solas. Los
hosts ESXi se dan de alta como **Servidor**. Lo que trae vCenter nunca pisa lo que informa el agente.

**Ojo:** vCenter está en la red 192.168.0.x, que hoy no llega a Azure. Hasta que Networking abra esa ruta (o se
corra el conector desde otro servidor), el conector va a mostrar "Sin conexión".

## 2. Microsoft Azure (VMs de las suscripciones)

**Opción A (recomendada): identidad administrada de la VM de Atlas.** Sin claves.
1. En el portal de Azure: VM **LLAZSVRAPP01 → Identidad → Asignada por el sistema → Activado**.
2. En la suscripción (o el grupo de recursos): **Control de acceso (IAM) → Agregar asignación de rol → Lector →
   Identidad administrada → LLAZSVRAPP01**.

```ini
AZURE_USAR_IDENTIDAD=1
AZURE_SUSCRIPCIONES=<id de suscripción>[,<otra>]
```

**Opción B: service principal.** Registrar una aplicación en Entra ID, crearle un secreto y darle el rol **Lector**
en la suscripción.

```ini
AZURE_TENANT_ID=<tenant>
AZURE_CLIENT_ID=<id de la aplicación>
AZURE_CLIENT_SECRET_ARCHIVO=C:\Atlas\secretos\azure.txt
AZURE_SUSCRIPCIONES=<id de suscripción>
```

Trae nombre, grupo de recursos, región, tamaño (vmSize), sistema, estado, discos e IP privada. Se cruza por nombre
de equipo con los servidores del dominio (LLAZSVR02, LLAZSVRAPP01, LLAZSVRTANGO01/02…) y completa la ficha.

## 3. Redfish: iDRAC (Dell) e iLO (HPE)

**Qué pedir:** en cada controladora, un usuario local con privilegio **solo lectura** (iDRAC: rol *Read Only*;
iLO: sin permisos de configuración, solo *Login*). Conviene el mismo usuario y clave en todas.

```ini
REDFISH_HOSTS=<ip iDRAC 1>,<ip iLO 1>,<ip iLO 2>
REDFISH_USUARIO=atlas-lectura
REDFISH_CLAVE_ARCHIVO=C:\Atlas\secretos\redfish.txt
REDFISH_VERIFICAR_CERT=0      # las controladoras traen certificado autofirmado
```

(`IDRAC_HOSTS`, `IDRAC_USUARIO`, `IDRAC_CLAVE_ARCHIVO` siguen funcionando como alias.)

Usa las rutas estándar de Redfish (`/redfish/v1/Systems`, `Managers`, `Chassis/…/Power`, `Thermal`, `Storage`):
fabricante, modelo, serie / service tag, salud general, encendido, BIOS, firmware de la controladora, fuentes, discos
y temperatura. Si la iDRAC de Dell expone la garantía en su sección OEM, también la muestra. Se cruza con el activo
del agente por la serie (Dell: service tag).

Controladoras vistas hasta ahora: iDRAC de LLROSSVR03 (Rosario) y dos iLO de HPE en la red 192.168.100.x. Las de la
red 192.168.0.x tienen el mismo problema de ruta hacia Azure que vCenter.

## Apagar un conector

Borrar (o dejar vacía) su variable principal (`VCENTER_URL`, `AZURE_SUSCRIPCIONES`, `REDFISH_HOSTS`) y reiniciar
los servicios. Los datos que ya trajo quedan en las fichas.
