# Atlas - Agente de inventario LLyA v5.0
# Une el agente de produccion v4.3 (GLPI Agent + respaldo clasico, tarea SYSTEM) con el agente enriquecido de
# la v2 (IP publica, MAC, gateway, OU de AD, ultimo reinicio y login). Reporta a Atlas (/api/sync y /api/sync-glpi).
#
# Funciona igual que hoy en produccion:
#   - Desde la GPO de inicio (SYSVOL): corre, y si tiene permisos registra la tarea programada apuntando a si mismo.
#   - Instalado por MSI (equipos fuera del dominio): igual, con la configuracion en atlas.ini al lado del script.
#   - A mano: muestra el resultado en pantalla y lo deja en C:\ProgramData\LLyA\atlas-agente.log.
#
# Configuracion (en orden de prioridad): parametros > atlas.ini al lado del script > valores de abajo.
#   [atlas]
#   Server=https://atlas.llyasoc.com
#   SyncKey=<SYNC_API_KEY de Atlas>
#   Glpi=piloto            (piloto | todos | no)
#   Piloto=TEST,SISTEMAS*
#   GlpiMsi=\\192.168.100.18\varios\glpi\GLPI-Agent-1.20-x64.msi
#   CertInterno=0          (1 solo para servidores con certificado interno, p. ej. mkcert)
param(
    [string]$Server  = "",
    [string]$SyncKey = "",
    [switch]$Install,      # registra la tarea (lo usa el MSI)
    [switch]$Uninstall,    # quita la tarea (lo usa el MSI)
    [switch]$Probar,       # junta el inventario y lo muestra, sin enviar nada
    [switch]$ForzarLegacy  # no usa GLPI Agent aunque el equipo este en el piloto
)

$VERSION = "5.0"
$TASK    = "Atlas Inventario"
$SELF    = $PSCommandPath
$LOGDIR  = Join-Path $env:ProgramData "LLyA"
$LOG     = Join-Path $LOGDIR "atlas-agente.log"

# ---- Configuracion
$cfg = @{ Server = ""; SyncKey = ""; Glpi = "piloto"; Piloto = "TEST,SISTEMAS*"
          GlpiMsi = "\\192.168.100.18\varios\glpi\GLPI-Agent-1.20-x64.msi"; CertInterno = "0" }
try {
    $ini = Join-Path (Split-Path -Parent $SELF) "atlas.ini"
    if (Test-Path $ini) {
        Get-Content $ini | ForEach-Object {
            if ($_ -match '^\s*([A-Za-z]+)\s*=\s*(.*?)\s*$' -and $cfg.ContainsKey($Matches[1])) { $cfg[$Matches[1]] = $Matches[2] }
        }
    }
} catch {}
if ($Server)  { $cfg.Server  = $Server }
if ($SyncKey) { $cfg.SyncKey = $SyncKey }
$Server  = $cfg.Server.TrimEnd("/")
$SyncKey = $cfg.SyncKey
$GLPI_DIR = "C:\Program Files\GLPI-Agent"

function Write-Log($m) {
    try {
        if (-not (Test-Path $LOGDIR)) { New-Item -ItemType Directory -Path $LOGDIR -Force | Out-Null }
        if ((Test-Path $LOG) -and (Get-Item $LOG).Length -gt 1MB) { Move-Item $LOG "$LOG.1" -Force }
        Add-Content -Path $LOG -Value ("{0}  {1}" -f (Get-Date -Format "yyyy-MM-dd HH:mm:ss"), $m)
    } catch {}
}
function Say($m, $color = "Gray") { Write-Host $m -ForegroundColor $color; Write-Log $m }
function Clean($s) { if ($null -eq $s) { return "" } return ($s -replace '[\"\\\/\x00-\x1F]', ' ').Trim() }

function Set-Red {
    [Net.ServicePointManager]::SecurityProtocol = [Net.SecurityProtocolType]::Tls12
    if ($cfg.CertInterno -eq "1") { [Net.ServicePointManager]::ServerCertificateValidationCallback = { $true } }
}

function GetSede($nombre) {
    $n = $nombre.ToUpper()
    if ($n -match '^(RESG|RSG)')                                     { return "Resguarda" }
    if ($n -match '^CBA')                                            { return "Cordoba" }
    if ($n -match '^NQN')                                            { return "Neuquen" }
    if ($n -match '^(RIMPTO|RADMIN|RAUDIT|RAUDI|RLEGALES)')          { return "Rosario" }
    if ($n -match '^(CIMPTO|CAUDIT|CADMIN|CLEGALES|CPYMES|CMULETO)') { return "Corrientes" }
    if ($n -match '^(TIMPTO|TAUDIT|TADMIN|TSISTEMAS|PRECYTRANS)')    { return "Tigre" }
    if ($n -match '^(MIMPTO|MADMIN|MAUDIT|MLEGALES|MPYMES|MNMULETO)'){ return "Mendoza" }
    return "CABA"
}

# Tipo de equipo con el mismo criterio que usa Atlas para GLPI: virtual o Windows Server -> Servidor,
# chasis portatil -> Notebook, el resto -> CPU. (Antes el agente mandaba siempre "Notebook" y pisaba el tipo.)
function Get-Tipo($cs, $os) {
    try {
        $modelo = "$($cs.Manufacturer) $($cs.Model)"
        if ($modelo -match 'VMware|VirtualBox|Virtual Machine|KVM|QEMU|Xen|Hyper-V' -or $os.Caption -match 'Server') { return "Servidor" }
        $ch = @((Get-WmiObject Win32_SystemEnclosure -ErrorAction Stop).ChassisTypes)
        if ($ch | Where-Object { $_ -in 8,9,10,11,12,14,18,21,30,31,32 }) { return "Notebook" }
        if ($ch | Where-Object { $_ -in 3,4,5,6,7,13,15,16,23,24,35,36 }) { return "CPU" }
    } catch {}
    if ($cs.PCSystemType -eq 2) { return "Notebook" }
    return "CPU"
}

function Get-Inventario {
    $serial  = (Get-WmiObject Win32_BIOS).SerialNumber
    $cpu     = (Get-WmiObject Win32_Processor | Select-Object -First 1).Name.Trim()
    $os      = Get-WmiObject Win32_OperatingSystem
    $cs      = Get-WmiObject Win32_ComputerSystem
    $ramGB   = [math]::Round($cs.TotalPhysicalMemory/1GB)
    $discoGB = [math]::Round((Get-WmiObject Win32_DiskDrive | Select-Object -First 1).Size/1GB)
    $nombre  = $env:COMPUTERNAME

    # Red: IP local, MAC y gateway del adaptador con salida
    $ip = ""; $mac = ""; $gw = ""
    try {
        $nic = Get-WmiObject Win32_NetworkAdapterConfiguration |
               Where-Object { $_.IPEnabled -eq $true -and $_.DefaultIPGateway -ne $null } | Select-Object -First 1
        if (-not $nic) { $nic = Get-WmiObject Win32_NetworkAdapterConfiguration | Where-Object { $_.IPEnabled -eq $true } | Select-Object -First 1 }
        if ($nic) {
            $ip  = ($nic.IPAddress        | Where-Object { $_ -match '^\d+\.\d+\.\d+\.\d+$' } | Select-Object -First 1)
            $gw  = ($nic.DefaultIPGateway | Where-Object { $_ -match '^\d+\.\d+\.\d+\.\d+$' } | Select-Object -First 1)
            $mac = $nic.MACAddress
        }
    } catch {}

    # IP publica (sirve para ubicar equipos fuera de la oficina)
    $ipPublica = ""
    try {
        $wc = New-Object Net.WebClient; $wc.Headers.Add("User-Agent", "LLyA-Atlas-Agent")
        $ipPublica = ($wc.DownloadString("https://api.ipify.org")).Trim()
        if ($ipPublica -notmatch '^\d+\.\d+\.\d+\.\d+$') { $ipPublica = "" }
    } catch {}

    # OU en Active Directory (vacio si el equipo esta fuera del dominio)
    $ou = ""
    if ($cs.PartOfDomain) {
        try {
            $ds = New-Object DirectoryServices.DirectorySearcher
            $ds.Filter = "(&(objectCategory=computer)(name=$nombre))"
            $r = $ds.FindOne()
            if ($r) { $ou = ($r.Properties["distinguishedname"][0] -replace '^CN=[^,]+,', '') }
        } catch {}
    }

    # Ultimo reinicio y ultimo inicio de sesion interactivo (el log de seguridad requiere elevacion)
    $ultReinicio = ""; $ultLogin = ""
    try { $ultReinicio = ([Management.ManagementDateTimeConverter]::ToDateTime($os.LastBootUpTime)).ToString("yyyy-MM-dd HH:mm") } catch {}
    try {
        $ev = Get-WinEvent -FilterHashtable @{LogName='Security';Id=4624} -MaxEvents 60 -ErrorAction Stop |
              Where-Object { $_.Properties[8].Value -in 2,10,11 } | Select-Object -First 1
        if ($ev) { $ultLogin = $ev.TimeCreated.ToString("yyyy-MM-dd HH:mm") }
    } catch {}

    # Impresoras y monitores
    $impresoras = ""; $monitores = ""
    try { $impresoras = (Get-WmiObject Win32_Printer -ErrorAction SilentlyContinue | Select-Object -ExpandProperty Name | ForEach-Object { Clean($_) }) -join "|" } catch {}
    try {
        $monitores = (Get-WmiObject WmiMonitorID -Namespace root\wmi -ErrorAction SilentlyContinue | ForEach-Object {
            $man = ($_.ManufacturerName | Where-Object {$_ -ne 0} | ForEach-Object {[char]$_}) -join ""
            $mod = ($_.UserFriendlyName | Where-Object {$_ -ne 0} | ForEach-Object {[char]$_}) -join ""
            Clean("$man $mod") }) -join "|"
    } catch {}

    # Software instalado (lista estructurada, sin duplicados)
    $software = @()
    try {
        $paths = @("HKLM:\Software\Microsoft\Windows\CurrentVersion\Uninstall\*",
                   "HKLM:\Software\Wow6432Node\Microsoft\Windows\CurrentVersion\Uninstall\*",
                   "HKCU:\Software\Microsoft\Windows\CurrentVersion\Uninstall\*")
        $vistos = @{}
        $paths | ForEach-Object {
            Get-ItemProperty $_ -ErrorAction SilentlyContinue | Where-Object { $_.DisplayName } |
            Select-Object DisplayName, DisplayVersion, InstallDate
        } | Sort-Object DisplayName | ForEach-Object {
            $n = (Clean($_.DisplayName) -replace '\s*#\d+\s*$', '' -replace '\s*\([A-Za-z]:.*$', '').Trim()
            if ($n -and -not $vistos.ContainsKey($n)) { $vistos[$n] = $true
                $software += [ordered]@{ nombre = $n; version = Clean($_.DisplayVersion); fecha = Clean($_.InstallDate) } }
        }
    } catch {}

    # Usuario real aunque corra como SYSTEM
    $usuarioReal = $env:USERNAME
    if ($usuarioReal -match '\$$' -or $usuarioReal -eq "SYSTEM" -or $usuarioReal -eq $env:COMPUTERNAME) {
        if ($cs.UserName) { $usuarioReal = ($cs.UserName -split "\\")[-1] } else { $usuarioReal = "" }
    }

    # Cifrado (BitLocker) y TPM: requieren elevacion. "Sin acceso" no pisa el dato que ya tiene Atlas.
    $cifrado = "Sin acceso"
    try {
        $vol = Get-WmiObject -Namespace "Root\cimv2\Security\MicrosoftVolumeEncryption" -Class Win32_EncryptableVolume -Filter "DriveLetter='C:'" -ErrorAction Stop
        if ($vol) {
            $prot = $vol.ProtectionStatus; $conv = ($vol.GetConversionStatus()).ConversionStatus
            if ($conv -eq 1 -and $prot -eq 1) { $cifrado = "Cifrado" }
            elseif ($conv -eq 1)              { $cifrado = "Cifrado (proteccion off)" }
            elseif ($conv -eq 2)              { $cifrado = "Cifrando" }
            elseif ($conv -eq 0)              { $cifrado = "Sin cifrar" }
            else                              { $cifrado = "Estado $conv/$prot" }
        } else { $cifrado = "Sin volumen" }
    } catch {}
    $tpm = "Sin acceso"
    try {
        $t = Get-WmiObject -Namespace "Root\cimv2\Security\MicrosoftTpm" -Class Win32_Tpm -ErrorAction Stop
        if ($t) { $ver = ($t.SpecVersion -split ",")[0].Trim()
            if ($t.IsEnabled_InitialValue -and $t.IsActivated_InitialValue) { $tpm = $ver } else { $tpm = "$ver (inactivo)" } }
        else { $tpm = "No" }
    } catch {}

    return [ordered]@{
        nombre = "$(Clean($nombre))"; tipo = "$(Get-Tipo $cs $os)"; marca = "$(Clean($cs.Manufacturer))"; modelo = "$(Clean($cs.Model))"
        serial = "$(Clean($serial))"; cpu = "$(Clean($cpu))"; ram = "$($ramGB)GB"; disco = "$($discoGB)GB"
        so = "$(Clean($os.Caption))"; so_version = "$(Clean($os.Version))"; so_arquitectura = "$(Clean($os.OSArchitecture))"
        ip = "$ip"; red = "$(Clean($cs.Domain))"; grupo = "$(Clean($cs.SystemType))"
        usuario = "$(Clean($usuarioReal))"; usuario_alt = "$(Clean($cs.UserName))"; estado = "Activo"; ubicacion = "$(GetSede($nombre))"
        comentarios = ""; garantia = ""
        monitores = "$monitores"; impresoras = "$impresoras"; software = @($software); cifrado = "$cifrado"; tpm = "$tpm"
        ip_publica = "$ipPublica"; mac = "$(Clean($mac))"; gateway = "$gw"; ou_ad = "$(Clean($ou))"
        ultimo_reinicio = "$ultReinicio"; ultimo_login = "$ultLogin"
    }
}

# POST con hasta 3 intentos (cubre cortes breves de red o un reinicio del servidor). Devuelve el texto de la respuesta.
function Send-Post($ruta, [byte[]]$bytes, $extra = @{}) {
    $ultimo = $null
    for ($i = 1; $i -le 3; $i++) {
        try {
            $wc = New-Object Net.WebClient
            $wc.Headers.Add("x-sync-key", $SyncKey)
            $wc.Headers.Add("User-Agent", "LLyA-Atlas-Agent/$VERSION")
            foreach ($k in $extra.Keys) { $wc.Headers.Add($k, $extra[$k]) }
            return [Text.Encoding]::UTF8.GetString($wc.UploadData("$Server$ruta", "POST", $bytes))
        } catch {
            $ultimo = $_.Exception
            $resp = $_.Exception.InnerException.Response
            if ($resp -and [int]$resp.StatusCode -in 401,413,422) { break }   # errores que no se arreglan reintentando
            if ($i -lt 3) { Start-Sleep -Seconds (10 * $i) }
        }
    }
    throw $ultimo
}

function Test-Piloto {
    if ($cfg.Glpi -eq "todos") { return $true }
    if ($cfg.Glpi -ne "piloto") { return $false }
    foreach ($p in ($cfg.Piloto -split ",")) { if ($p.Trim() -and $env:COMPUTERNAME -like $p.Trim()) { return $true } }
    return $false
}

# Inventario GLPI (mas detalle: discos, antivirus, bateria, Office, BIOS, actualizaciones). Igual que el v4.3.
function Invoke-Glpi {
    $bat = Join-Path $GLPI_DIR "glpi-inventory.bat"
    if (-not (Test-Path $bat)) {
        if (-not (Test-Path $cfg.GlpiMsi)) { Write-Log "GLPI: MSI no accesible: $($cfg.GlpiMsi)"; return $false }
        Write-Log "GLPI: instalando desde $($cfg.GlpiMsi)"
        $p = Start-Process msiexec.exe -ArgumentList "/i `"$($cfg.GlpiMsi)`" /quiet /norestart EXECMODE=3" -Wait -PassThru
        if (-not (Test-Path $bat)) { Write-Log "GLPI: instalacion fallida, codigo $($p.ExitCode)"; return $false }
    }
    $tmp = Join-Path $env:TEMP ("glpi_" + [guid]::NewGuid().ToString("N") + ".json")
    $linea = '/c ""' + $bat + '" --json --no-category=environment,process > "' + $tmp + '" 2>nul"'
    Start-Process cmd.exe -ArgumentList $linea -Wait -WindowStyle Hidden
    if (-not (Test-Path $tmp) -or (Get-Item $tmp).Length -lt 1000) {
        Write-Log "GLPI: inventario vacio o incompleto"
        Remove-Item $tmp -Force -ErrorAction SilentlyContinue
        return $false
    }
    $bytes = [IO.File]::ReadAllBytes($tmp)
    Remove-Item $tmp -Force -ErrorAction SilentlyContinue
    $ms = New-Object IO.MemoryStream
    $gz = New-Object IO.Compression.GZipStream($ms, [IO.Compression.CompressionMode]::Compress)
    $gz.Write($bytes, 0, $bytes.Length); $gz.Close()
    $resp = Send-Post "/api/sync-glpi" $ms.ToArray() @{ "Content-Type" = "application/json"; "Content-Encoding" = "gzip" }
    Write-Log ("GLPI OK ({0} KB): {1}" -f [math]::Round($bytes.Length/1KB), $resp)
    return $true
}

# Tarea programada como SYSTEM: cada 2 horas de 8 a 22 y al iniciar sesion. Apunta a este mismo script
# (SYSVOL si vino por GPO, Program Files si vino por MSI). Solo se re-registra si cambio algo.
function Set-Tarea {
    try {
        $id = [Security.Principal.WindowsIdentity]::GetCurrent()
        $esSystem = $id.Name -eq "NT AUTHORITY\SYSTEM"
        $esAdmin  = ([Security.Principal.WindowsPrincipal]$id).IsInRole([Security.Principal.WindowsBuiltInRole]::Administrator)
        if (-not ($esSystem -or $esAdmin)) { return }
        $desc = "Atlas - inventario LLyA cada 2 horas y al iniciar sesion (v$VERSION) - $SELF"
        $t = Get-ScheduledTask -TaskName $TASK -ErrorAction SilentlyContinue
        if ($t -and $t.Principal.UserId -eq "SYSTEM" -and $t.Description -eq $desc) { return }
        $a   = New-ScheduledTaskAction -Execute "powershell.exe" -Argument "-ExecutionPolicy Bypass -NonInteractive -WindowStyle Hidden -File `"$SELF`""
        $tr  = New-ScheduledTaskTrigger -Daily -At 08:00 -RandomDelay (New-TimeSpan -Minutes 15)
        $rep = New-ScheduledTaskTrigger -Once -At 08:00 -RepetitionInterval (New-TimeSpan -Hours 2) -RepetitionDuration (New-TimeSpan -Hours 14)
        $tr.Repetition = $rep.Repetition
        $tl  = New-ScheduledTaskTrigger -AtLogOn; $tl.Delay = "PT2M"
        $p   = New-ScheduledTaskPrincipal -UserId "SYSTEM" -LogonType ServiceAccount -RunLevel Highest
        $s   = New-ScheduledTaskSettingsSet -StartWhenAvailable -AllowStartIfOnBatteries -DontStopIfGoingOnBatteries -ExecutionTimeLimit (New-TimeSpan -Minutes 30) -MultipleInstances IgnoreNew
        Register-ScheduledTask -TaskName $TASK -Description $desc -Action $a -Trigger @($tr, $tl) -Principal $p -Settings $s -Force | Out-Null
        Write-Log "Tarea '$TASK' registrada como SYSTEM -> $SELF"
    } catch { Write-Log ("No se pudo registrar la tarea: " + $_.Exception.Message) }
}

function Restrict-Ini {
    # La clave vive en atlas.ini: solo SYSTEM (S-1-5-18) y Administradores (S-1-5-32-544), sin herencia.
    try {
        $ini = Join-Path (Split-Path -Parent $SELF) "atlas.ini"
        if ((Test-Path $ini) -and $SELF -notlike "\\*") {
            & icacls.exe "$ini" /inheritance:r /grant:r "*S-1-5-18:F" "*S-1-5-32-544:F" | Out-Null
            Write-Log "ACL de atlas.ini restringido a SYSTEM + Administradores"
        }
    } catch { Write-Log ("No se pudo restringir el ACL: " + $_.Exception.Message) }
}

# ---- Principal
if ($Uninstall) { Unregister-ScheduledTask -TaskName $TASK -Confirm:$false -ErrorAction SilentlyContinue; Write-Log "Tarea '$TASK' eliminada"; return }
if ($Install)   { Restrict-Ini }

Set-Red
if ($Probar) {
    $body = Get-Inventario
    $body.software = "($(@($body.software).Count) programas)"
    $body.GetEnumerator() | ForEach-Object { "{0,-16} {1}" -f $_.Key, $_.Value }
    return
}
if (-not $Server -or -not $SyncKey) {
    Say "ERROR: falta Server o SyncKey (atlas.ini al lado del script o parametros -Server / -SyncKey)." Red
    exit 2
}
Set-Tarea

$codigo = 0
try {
    $body  = Get-Inventario
    $bytes = [Text.Encoding]::UTF8.GetBytes(($body | ConvertTo-Json -Depth 4 -Compress))
    Send-Post "/api/sync" $bytes @{ "Content-Type" = "application/json; charset=utf-8" } | Out-Null
    Say ("OK - Sincronizado en Atlas: {0} ({1}, {2}) -> {3}" -f $body.nombre, $body.tipo, $body.ubicacion, $Server) Green
} catch {
    Say ("ERROR al enviar a {0}: {1}" -f $Server, $_.Exception.Message) Red
    $codigo = 1
}

# GLPI va despues del clasico: si corre, su detalle (y su tipo) prevalece.
if ($codigo -eq 0 -and -not $ForzarLegacy -and (Test-Piloto)) {
    try { if (Invoke-Glpi) { Say "OK - Detalle GLPI enviado" Green } } catch { Write-Log ("GLPI error: " + $_.Exception.Message) }
}
exit $codigo
