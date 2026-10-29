# MSI del agente de inventario LLyA v2

Empaqueta `agent_v2.ps1` como instalador MSI: lo copia a `C:\Program Files\LLyA\Inventario Agent\`,
escribe `agente.ini` con el servidor y la clave, y registra una tarea programada (SYSTEM, cada 2 h +
al iniciar sesión). Desinstala limpio (borra la tarea y la carpeta).

## Compilar
Requiere los binarios de WiX 3.14 en `C:\Tools\wix314`.
```
copy ..\agent_v2.ps1 .\agent_v2.ps1
C:\Tools\wix314\candle.exe -arch x64 InventarioAgent.wxs
C:\Tools\wix314\light.exe -sval InventarioAgent.wixobj -o InventarioAgent.msi
```

## Instalar (en cada equipo)
```
msiexec /i InventarioAgent.msi /qn SERVER="https://192.168.100.116:8543" SYNCKEY="<clave de /api/sync>"
```
- `SERVER`: URL del Inventario V2 (por defecto `https://192.168.100.116:8543`).
- `SYNCKEY`: la clave `SYNC_API_KEY` del servidor (header `X-Sync-Key`).

## Desinstalar
`msiexec /x {ProductCode}` o desde Agregar/quitar programas.

## Notas
- La clave queda en `agente.ini` dentro de Program Files. Conviene restringir su ACL (SYSTEM +
  Administradores) en una próxima versión; es una clave de bajo impacto (solo permite enviar inventario).
- La tarea corre el script sin pasarle la clave: la lee del `.ini` en tiempo de ejecución.
- Probado end-to-end el 29/10/2026 en LLBASVRAPPS01: install, tarea automática, reporte a la V2 y
  desinstalación limpia, todo OK.
