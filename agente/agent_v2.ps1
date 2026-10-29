# Agente de inventario LLYA v2 (enriquecido) — reporta al Inventario V2.
# Recolecta todo lo del agente clasico MAS los campos que antes daba Falcon y son locales:
#   IP publica, MAC, gateway, OU de Active Directory, ultimo reinicio y ultimo login.
# Queda instalado por MSI con su propia tarea; no depende de SYSVOL.
param(
    [string]$Server  = "",
    [string]$SyncKey = "",
    [switch]$Install,     # registra la tarea programada (lo usa el MSI al instalar)
    [switch]$Uninstall    # quita la tarea programada (lo usa el MSI al desinstalar)
)

$TASK   = "LLyA Inventario Agent"
$SELF   = $PSCommandPath
$LOGDIR = Join-Path $env:ProgramData "LLyA"
$LOG    = Join-Path $LOGDIR "agente-v2.log"

# Config (Server / SyncKey) desde agente.ini al lado del script si no vinieron por parametro.
try {
    $ini = Join-Path (Split-Path -Parent $SELF) "agente.ini"
    if (Test-Path $ini) {
        Get-Content $ini | ForEach-Object {
            if ($_ -match '^\s*Server\s*=\s*(.+?)\s*$'  -and -not $Server)  { $Server  = $Matches[1] }
            if ($_ -match '^\s*SyncKey\s*=\s*(.+?)\s*$' -and -not $SyncKey) { $SyncKey = $Matches[1] }
        }
    }
} catch {}
if (-not $Server) { $Server = "https://192.168.100.116:8543" }
function Write-Log($m) {
    try {
        if (-not (Test-Path $LOGDIR)) { New-Item -ItemType Directory -Path $LOGDIR -Force | Out-Null }
        if ((Test-Path $LOG) -and (Get-Item $LOG).Length -gt 1MB) { Move-Item $LOG "$LOG.1" -Force }
        Add-Content -Path $LOG -Value ("{0}  {1}" -f (Get-Date -Format "yyyy-MM-dd HH:mm:ss"), $m)
    } catch {}
}
function Clean($s) { if ($null -eq $s) { return "" } return ($s -replace '[\"\\\/\x00-\x1F]', ' ').Trim() }

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

function Get-Inventario {
    [Net.ServicePointManager]::SecurityProtocol = [Net.SecurityProtocolType]::Tls12
    $serial  = (Get-WmiObject Win32_BIOS).SerialNumber
    $cpu     = (Get-WmiObject Win32_Processor | Select-Object -First 1).Name.Trim()
    $ramGB   = [math]::Round((Get-WmiObject Win32_ComputerSystem).TotalPhysicalMemory/1GB)
    $discoGB = [math]::Round((Get-WmiObject Win32_DiskDrive | Select-Object -First 1).Size/1GB)
    $os      = Get-WmiObject Win32_OperatingSystem
    $cs      = Get-WmiObject Win32_ComputerSystem
    $nombre  = $env:COMPUTERNAME

    # Red: IP local, MAC y gateway del adaptador activo
    $ip = ""; $mac = ""; $gw = ""
    try {
        $nic = Get-WmiObject Win32_NetworkAdapterConfiguration |
               Where-Object { $_.IPEnabled -eq $true -and $_.DefaultIPGateway -ne $null } |
               Select-Object -First 1
        if (-not $nic) { $nic = Get-WmiObject Win32_NetworkAdapterConfiguration | Where-Object { $_.IPEnabled -eq $true } | Select-Object -First 1 }
        if ($nic) {
            $ip  = ($nic.IPAddress        | Where-Object { $_ -match '^\d+\.\d+\.\d+\.\d+$' } | Select-Object -First 1)
            $gw  = ($nic.DefaultIPGateway | Where-Object { $_ -match '^\d+\.\d+\.\d+\.\d+$' } | Select-Object -First 1)
            $mac = $nic.MACAddress
        }
    } catch {}

    # IP publica: el equipo pregunta a un servicio externo (sirve para equipos fuera de la red)
    $ipPublica = ""
    try {
        $wc = New-Object Net.WebClient; $wc.Headers.Add("User-Agent", "LLyA-Agent")
        $ipPublica = ($wc.DownloadString("https://api.ipify.org")).Trim()
        if ($ipPublica -notmatch '^\d+\.\d+\.\d+\.\d+$') { $ipPublica = "" }
    } catch { $ipPublica = "" }

    # OU en Active Directory (distinguishedName de la maquina)
    $ou = ""
    try {
        $ds = New-Object DirectoryServices.DirectorySearcher
        $ds.Filter = "(&(objectCategory=computer)(name=$nombre))"
        $r = $ds.FindOne()
        if ($r) { $ou = ($r.Properties["distinguishedname"][0] -replace '^CN=[^,]+,', '') }
    } catch { $ou = "" }

    # Ultimo reinicio y ultimo login interactivo
    $ultReinicio = ""; $ultLogin = ""
    try { $ultReinicio = ([Management.ManagementDateTimeConverter]::ToDateTime($os.LastBootUpTime)).ToString("yyyy-MM-dd HH:mm") } catch {}
    try {
        $ev = Get-WinEvent -FilterHashtable @{LogName='Security';Id=4624} -MaxEvents 40 -ErrorAction Stop |
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

    # Software instalado
    $software = @()
    try {
        $paths = @("HKLM:\Software\Microsoft\Windows\CurrentVersion\Uninstall\*",
                   "HKLM:\Software\Wow6432Node\Microsoft\Windows\CurrentVersion\Uninstall\*",
                   "HKCU:\Software\Microsoft\Windows\CurrentVersion\Uninstall\*")
        $vistos = @{}
        $paths | ForEach-Object {
            Get-ItemProperty $_ -ErrorAction SilentlyContinue |
            Where-Object { $_.DisplayName } | Select-Object DisplayName, DisplayVersion, InstallDate
        } | Sort-Object DisplayName | ForEach-Object {
            $n = (Clean($_.DisplayName) -replace '\s*#\d+\s*$', '' -replace '\s*\([A-Za-z]:.*$', '').Trim()
            if ($n -and -not $vistos.ContainsKey($n)) { $vistos[$n] = $true
                $software += [ordered]@{ nombre = $n; version = Clean($_.DisplayVersion); fecha = Clean($_.InstallDate) } }
        }
    } catch {}

    # Usuario real
    $usuarioReal = $env:USERNAME
    if ($usuarioReal -match '\$$' -or $usuarioReal -eq "SYSTEM" -or $usuarioReal -eq $env:COMPUTERNAME) {
        if ($cs.UserName) { $usuarioReal = ($cs.UserName -split "\\")[-1] } else { $usuarioReal = "" }
    }

    # Cifrado y TPM (requieren elevacion; como SYSTEM funcionan)
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
        }
    } catch { $cifrado = "Sin acceso" }
    $tpm = "Sin acceso"
    try {
        $t = Get-WmiObject -Namespace "Root\cimv2\Security\MicrosoftTpm" -Class Win32_Tpm -ErrorAction Stop
        if ($t) { $ver = ($t.SpecVersion -split ",")[0].Trim()
            if ($t.IsEnabled_InitialValue -and $t.IsActivated_InitialValue) { $tpm = $ver } else { $tpm = "$ver (inactivo)" } }
        else { $tpm = "No" }
    } catch { $tpm = "Sin acceso" }

    return [ordered]@{
        nombre = "$(Clean($nombre))"; tipo = "Notebook"; marca = "$(Clean($cs.Manufacturer))"; modelo = "$(Clean($cs.Model))"
        serial = "$(Clean($serial))"; cpu = "$(Clean($cpu))"; ram = "$($ramGB)GB"; disco = "$($discoGB)GB"
        so = "$(Clean($os.Caption))"; so_version = "$(Clean($os.Version))"; so_arquitectura = "$(Clean($os.OSArchitecture))"
        ip = "$ip"; red = "$(Clean($cs.Domain))"; grupo = "$(Clean($cs.SystemType))"
        usuario = "$(Clean($usuarioReal))"; usuario_alt = "$(Clean($cs.UserName))"; estado = "Activo"; ubicacion = "$(GetSede($nombre))"
        monitores = "$monitores"; impresoras = "$impresoras"; software = @($software); cifrado = "$cifrado"; tpm = "$tpm"
        ip_publica = "$ipPublica"; mac = "$(Clean($mac))"; gateway = "$gw"; ou_ad = "$(Clean($ou))"
        ultimo_reinicio = "$ultReinicio"; ultimo_login = "$ultLogin"
    }
}

function Send-Inventario($body) {
    $payload = $body | ConvertTo-Json -Depth 4 -Compress
    $bytes = [Text.Encoding]::UTF8.GetBytes($payload)
    # Cert interno (mkcert): aceptar el del servidor del inventario
    [Net.ServicePointManager]::ServerCertificateValidationCallback = { $true }
    try {
        Invoke-RestMethod -Uri "$Server/api/sync" -Method POST -ContentType "application/json; charset=utf-8" -Headers @{"x-sync-key" = $SyncKey} -Body $bytes | Out-Null
    } catch {
        $client = New-Object Net.WebClient
        $client.Headers.Add("Content-Type", "application/json; charset=utf-8")
        $client.Headers.Add("x-sync-key", $SyncKey)
        $client.UploadData("$Server/api/sync", "POST", $bytes) | Out-Null
    }
}

function Register-Tarea {
    $accion = "-ExecutionPolicy Bypass -NonInteractive -WindowStyle Hidden -File `"$SELF`""
    $a   = New-ScheduledTaskAction -Execute "powershell.exe" -Argument $accion
    $tr  = New-ScheduledTaskTrigger -Once -At 08:00 -RepetitionInterval (New-TimeSpan -Hours 2) -RepetitionDuration (New-TimeSpan -Days 1)
    $tl  = New-ScheduledTaskTrigger -AtLogOn; $tl.Delay = "PT2M"
    $p   = New-ScheduledTaskPrincipal -UserId "SYSTEM" -LogonType ServiceAccount -RunLevel Highest
    $s   = New-ScheduledTaskSettingsSet -StartWhenAvailable -AllowStartIfOnBatteries -DontStopIfGoingOnBatteries -ExecutionTimeLimit (New-TimeSpan -Minutes 30) -MultipleInstances IgnoreNew
    Register-ScheduledTask -TaskName $TASK -Description "Inventario LLyA v2 - cada 2 horas y al iniciar sesion" -Action $a -Trigger @($tr, $tl) -Principal $p -Settings $s -Force | Out-Null
    Write-Log "Tarea '$TASK' registrada (SYSTEM, cada 2 h + al iniciar sesion). Servidor: $Server"
}
function Unregister-Tarea {
    Unregister-ScheduledTask -TaskName $TASK -Confirm:$false -ErrorAction SilentlyContinue
    Write-Log "Tarea '$TASK' eliminada"
}

if ($Uninstall) { Unregister-Tarea; return }
if ($Install)   { Register-Tarea }

try {
    $body = Get-Inventario
    Send-Inventario $body
    Write-Log ("OK {0} ({1}) -> {2}  [pub={3} ou={4}]" -f $body.nombre, $body.ubicacion, $Server, $body.ip_publica, $body.ou_ad)
    Write-Host ("OK - Sincronizado: {0} ({1})" -f $body.nombre, $body.ubicacion) -ForegroundColor Green
} catch {
    Write-Log ("ERROR: " + $_.Exception.Message)
    Write-Host ("ERROR: " + $_.Exception.Message) -ForegroundColor Red
    exit 1
}
