# Relevamiento SNMP de impresoras (Atlas, paso 2)

`relevar_impresoras.py` consulta por SNMP (solo lectura, MIBs estándar RFC 3805 y HOST-RESOURCES) las impresoras
de red que Atlas ya conoce: modelo, serie, MAC, contador total, estado y consumibles con su porcentaje.
**No escanea la red**: solo consulta las IP que recibe.

`enviar_a_atlas.py` le pide a Atlas la lista de IP, las releva y le manda los resultados. Atlas guarda la lectura
del contador, actualiza los consumibles y, si difieren, corrige serie, modelo y MAC (el dato del equipo manda).

## Instalación (en un servidor que llegue a todas las sedes, hoy LLBASVRAPPS01)

1. Python 3.11 y `pip install "pysnmp>=7.1,<8"` en un venv: `C:\Atlas-relevamiento\.venv`.
2. Copiar `relevar_impresoras.py` y `enviar_a_atlas.py` a `C:\Atlas-relevamiento\`.
3. Crear `C:\Atlas-relevamiento\relevamiento.ini` (solo SYSTEM y Administradores):
   ```ini
   [atlas]
   Server=https://172.20.0.10:8743
   SyncKey=<SYNC_API_KEY de Atlas>
   CertInterno=1
   Community=public
   ```
4. Tarea programada como SYSTEM cada 2 horas: `C:\Atlas-relevamiento\.venv\Scripts\python.exe C:\Atlas-relevamiento\enviar_a_atlas.py`.

Log: `C:\ProgramData\LLyA\atlas-relevamiento-impresoras.log`.

## Prueba manual (sin Atlas)

```
python relevar_impresoras.py --ips 192.168.100.141 192.168.100.26
python relevar_impresoras.py --archivo ips.txt --json resultado.json
```

## Notas

- HP recomienda cambiar la community `public` o pasar a SNMPv3; cuando se haga, se cambia `Community` en el ini
  (SNMPv3 requiere agregar credenciales al lector).
- Nivel de consumible: `-3` = "queda algo" y `-2` = "desconocido" según la RFC; no se muestran como porcentaje.
- Las impresoras personales por USB no tienen SNMP: se vinculan a la PC de la persona por el agente.
