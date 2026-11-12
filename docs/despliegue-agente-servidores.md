# Despliegue del agente de Atlas en los servidores

Resumen de cómo se instaló y actualizó el agente de Atlas en los servidores Windows (noviembre 2026).

## Cómo se instaló

No fue por GPO: la GPO del inventario está vinculada solo a las unidades de PCs (`OU=LLyASOC`) y los servidores
están en `OU=Servers`. Se instaló **por MSI, en forma remota**, desde **LLBASVRAPPS01**, con la cuenta de
administrador del dominio (`TANGO\jiriarte`):

1. Copia de `AtlasAgent.msi` a `\\SERVIDOR\C$\Windows\Temp\` (recurso administrativo SMB).
2. Ejecución remota por WMI (`Win32_Process.Create`):
   `msiexec /i C:\Windows\Temp\AtlasAgent.msi /qn SERVER="https://172.20.0.10:8743" SYNCKEY=<clave> CERTINTERNO=1 /l*v C:\Windows\Temp\atlas-msi.log`
3. El MSI instala el agente en `C:\Program Files\LLyA\Atlas Agent\` (con `atlas.ini`, ACL solo SYSTEM y
   Administradores) y crea la tarea **"Atlas Inventario"** (SYSTEM, cada 2 horas).

- Clave de sincronización: `C:\Atlas\CREDENCIALES.txt` (VM LLAZSVRAPP01).
- MSI: `C:\Atlas\agente\AtlasAgent.msi`; fuente en `agente\` del repositorio.
- Log del agente en cada servidor: `C:\ProgramData\LLyA\atlas-agente.log`. Log del MSI: `C:\Windows\Temp\atlas-msi.log`.

## Servidores (23)

LLAZSVR02, LLAZSVRAPP01, LLAZSVRTANGO01, LLAZSVRTANGO02, LLBASRVDC01, LLBASVRAPPS04, LLBASVRDC02, LLBASVRTS01,
LLCORSVR16, LLCORSVR17, LLCORSVR18, LLCORSVRDC01, LLROSSVR15, LLROSSVR16, LLROSSVR17, LLROSSVR18, LLROSSVRDC01,
LLSVR24, LLTIGSVR16, LLTIGSVR17, LLTIGSVR18, LLTIGSVRDC01, LLUSSVRAPPS03.

No se instaló en LLSVR17 ni LLCORSVR13 (Windows Server 2008, no soportado).

## Versiones

| Versión | Fecha | Cambio |
|---|---|---|
| 5.1.0 / 5.1.1 | 05-06/11 | Primera instalación; arreglo de tarea en 2012 R2 y tope al leer el log de Seguridad |
| 5.2.0 / 5.2.1 | 06/11 | Salud y seguridad (antivirus, parches, discos); arreglo de tarea en 2012 R2 |
| 5.3.0 | 06/11 | Monitores |
| 5.4.0 | 11/11 | Datos de servidor: roles, volúmenes, reinicio pendiente, servicios detenidos, SQL, IIS, Hyper-V |
| 5.4.1 | 11/11 | Versión liviana (lecturas pesadas 1 vez por día, cada 4 h, prioridad baja). **Compilada, NO instalada** |

Cada actualización se hizo igual: el MSI nuevo reemplaza al anterior (MajorUpgrade).

## Resultado y problemas

- **Reportan a Atlas:** 17 servidores.
- **Sin ruta a Azure (instalados pero no reportan):** LLTIGSVR16/17/18, LLTIGSVRDC01, LLBASVRAPPS04 y, desde el
  10/11, LLUSSVRAPPS03. Es un tema de red.
- **LLSVR24 y LLBASRVDC01 (2012 R2 / DC):** el agente lanzado por el MSI quedaba colgado; se cortó ese proceso y se
  corrió el agente a mano para recrear la tarea. **LLROSSVRDC01** quedó sin tarea.
- **Servidores lentos (11/11):** la carga del agente se sumaba a servidores con poca RAM. Se **deshabilitó la tarea**
  "Atlas Inventario" en LLCORSVR17, LLCORSVR18, LLROSSVR15-18, LLTIGSVR16, LLTIGSVR17, LLBASVRDC02, LLCORSVRDC01 y
  LLTIGSVRDC01 (no se desinstaló).
- **Desde el 11/11 los servidores se traen por CrowdStrike** (conector en Atlas, solo servidores): 41 servidores,
  incluidos Linux y la red 192.168.0.x. CrowdStrike no trae roles, discos ni servicios.

## Cómo revertir

- **Reactivar la tarea:** `schtasks /change /s SERVIDOR /tn "Atlas Inventario" /enable`
- **Desinstalar:** Panel de control → Programas → "Atlas Agent" → Desinstalar (o `msiexec /x` con el código del
  producto). Borra también la tarea. Quedan `C:\ProgramData\LLyA\atlas-agente.log` y `atlas-cache.json`.
- El agente del **inventario productivo** (v4.3) es independiente y no se tocó.
