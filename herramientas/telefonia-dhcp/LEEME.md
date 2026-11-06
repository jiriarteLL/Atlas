# Relevamiento DHCP de teléfonos (Atlas, módulo Telefonía)

La central es 3CX **Pro** (sin API), así que Telefonía se alimenta de dos fuentes:

1. **Internos**: la exportación de usuarios de la consola de 3CX (*Usuarios → seleccionar todos → Exportar*), que
   se sube en Atlas con **Telefonía → Importar exportación de 3CX**. Atlas lee solo interno, nombre, mail, DID,
   departamento, MAC, modelo y si está deshabilitado. **Nunca** guarda PIN de casilla de voz, claves de
   click-to-call ni configuración de agentes IA (el resto de las columnas no se lee). Después de importar,
   borrá el CSV: trae esos datos sensibles.
2. **IP de cada teléfono**: `relevar_telefonos_dhcp.ps1` lee (solo lectura) las concesiones de los servidores DHCP
   de Windows, se queda con las MAC de Grandstream y se las manda a Atlas, que pone la IP en el interno con esa
   MAC y calcula la sede por la red. Los teléfonos con concesión pero sin interno en 3CX aparecen en
   *Teléfonos sin interno*. No barre la red: solo consulta el DHCP.

## Instalación (en un servidor que llegue a los DHCP y a Atlas, hoy LLBASVRAPPS01)

1. Copiar `relevar_telefonos_dhcp.ps1` a `C:\Atlas-relevamiento\telefonia\`. La cuenta que lo corre necesita
   leer los DHCP (grupo *DHCP Users* o administrador) y WinRM hacia ellos.
2. Crear `C:\Atlas-relevamiento\telefonia\telefonia-dhcp.ini` y dejarlo **solo para SYSTEM y Administradores**:
   ```ini
   [atlas]
   Server=https://172.20.0.10:8743
   SyncKey=<SYNC_API_KEY de Atlas>
   CertInterno=1
   Servidores=llbasvrdc02.llasesores.corp,llbasrvdc01.llasesores.corp,llcorsvrdc01.llasesores.corp
   Ouis=C0-74-AD,EC-74-D7,00-0B-82
   ```
   ```
   icacls telefonia-dhcp.ini /inheritance:r /grant:r "*S-1-5-18:F" "*S-1-5-32-544:F"
   ```
3. Probar sin mandar nada: `powershell -ExecutionPolicy Bypass -File relevar_telefonos_dhcp.ps1 -Probar`.
4. Tarea programada cada 2 horas (**la registra el administrador**, no se crea sola):
   `powershell -ExecutionPolicy Bypass -NonInteractive -File C:\Atlas-relevamiento\telefonia\relevar_telefonos_dhcp.ps1`

Log: `C:\ProgramData\LLyA\atlas-telefonia-dhcp.log`.

## Notas

- Las sedes cuyo DHCP lo da el router (no Windows) no aparecen en estas concesiones: esos teléfonos quedan sin IP
  hasta que se cargue a mano en la ficha (la IP manual no la pisa el relevamiento).
- Tipo **IP / WiFi**: 3CX exporta el mismo modelo para ambos; se marca a mano en la ficha y la importación no lo
  vuelve a cambiar.
