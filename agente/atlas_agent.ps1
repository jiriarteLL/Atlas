# Atlas - Agente de inventario LLyA v5.1
# Une el agente de produccion v4.3 (GLPI Agent + respaldo clasico, tarea SYSTEM) con el agente enriquecido de
# la v2 (IP publica, MAC, gateway, OU de AD, ultimo reinicio y login). Reporta a Atlas (/api/sync y /api/sync-glpi).
#
# Funciona igual que hoy en produccion:
#   - Desde la GPO de inicio (SYSVOL): se copia a C:\Program Files\LLyA\Atlas Agent y registra la tarea programada
#     sobre esa copia; despues se actualiza solo desde la GPO (ver Sync-CopiaLocal).
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

$VERSION = "5.2.0"
$TASK    = "Atlas Inventario"
$SELF    = $PSCommandPath
$LOCALDIR = Join-Path $env:ProgramFiles "LLyA\Atlas Agent"
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
    # Servidores: LLCOR..., LLROS..., LLTIG... (el resto, incluidos LLBA y LLAZ, queda en CABA)
    if ($n -match '^LLCOR')                                          { return "Corrientes" }
    if ($n -match '^LLROS')                                          { return "Rosario" }
    if ($n -match '^LLTIG')                                          { return "Tigre" }
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

# Modelo con el nombre comercial. Lenovo informa en Model el machine type ("21M80017AR") y el nombre que conoce
# la gente en Win32_ComputerSystemProduct.Version ("ThinkPad E14 Gen 6"); HP y Dell ya lo traen en Model.
function Get-Modelo($cs) {
    $modelo = Clean($cs.Model)
    try {
        $ver = Clean((Get-WmiObject Win32_ComputerSystemProduct -ErrorAction Stop).Version)
        $generico = '^(none|default string|system version|to be filled.*|not applicable|n/?a|0+|[\d.\s]+)$'
        if ($ver.Length -ge 3 -and $ver -match '[A-Za-z]' -and $ver -notmatch $generico -and $ver -ne $modelo) { return $ver }
    } catch {}
    return $modelo
}

# Salud y seguridad (fase A): version exacta de Windows, antivirus/EDR, parches, discos y bateria.
# Cada bloque es independiente: si uno falla (permisos, clase WMI inexistente) el resto se manda igual.
function Get-Salud($os) {
    $s = [ordered]@{ so = $null; antivirus = @(); parches = $null; discos = @(); bateria = $null }

    # Windows: edicion, version comercial (23H2...), build y UBR (revision de parches del build)
    try {
        $cv = Get-ItemProperty 'HKLM:\SOFTWARE\Microsoft\Windows NT\CurrentVersion' -ErrorAction Stop
        $ed = if ($os.Caption -match '(Enterprise|Education|Pro|Home|Datacenter|Standard)') { $Matches[1] } else { "" }
        $s.so = [ordered]@{ edicion = $ed; display_version = "$(if ($cv.DisplayVersion) { $cv.DisplayVersion } else { $cv.ReleaseId })"
                            build = [int]$cv.CurrentBuildNumber; ubr = [int]$cv.UBR }
    } catch {}

    # Antivirus/EDR. En estaciones de trabajo: Centro de seguridad (productState: 2.o byte = activo, 3.o = definiciones al dia).
    # En servidores (no tienen SecurityCenter2): Defender por Get-MpComputerStatus + servicio de CrowdStrike.
    try {
        if ((Get-WmiObject Win32_OperatingSystem).ProductType -eq 1) {
            $s.antivirus = @(Get-CimInstance -Namespace root/SecurityCenter2 -ClassName AntiVirusProduct -ErrorAction Stop | ForEach-Object {
                $h = '{0:X6}' -f [int]$_.productState
                [ordered]@{ nombre = Clean($_.displayName); activo = ($h.Substring(2, 2) -in '10', '11'); actualizado = ($h.Substring(4, 2) -eq '00') }
            })
        } else {
            $av = @()
            try {
                $mp = Get-MpComputerStatus -ErrorAction Stop
                $av += [ordered]@{ nombre = "Microsoft Defender"; activo = [bool]$mp.AntivirusEnabled; actualizado = ($mp.AntivirusSignatureAge -le 7) }
            } catch {}
            $cs = Get-Service CSFalconService -ErrorAction SilentlyContinue
            if ($cs) { $av += [ordered]@{ nombre = "CrowdStrike Falcon"; activo = ($cs.Status -eq 'Running'); actualizado = $true } }
            $s.antivirus = $av
        }
    } catch {}

    # Parches: ultimo instalado y cuantos en los ultimos 90 dias (Win32_QuickFixEngineering)
    try {
        $fechas = @(Get-HotFix -ErrorAction Stop | Where-Object { $_.InstalledOn } | ForEach-Object { [datetime]$_.InstalledOn })
        if ($fechas.Count) {
            $ult = ($fechas | Measure-Object -Maximum).Maximum
            $s.parches = [ordered]@{ ultimo = $ult.ToString('yyyy-MM-dd'); cantidad_90d = @($fechas | Where-Object { $_ -ge (Get-Date).AddDays(-90) }).Count }
        }
    } catch {}

    # Discos: salud y, si el controlador lo informa, desgaste / temperatura / errores de lectura
    try {
        $s.discos = @(Get-PhysicalDisk -ErrorAction Stop | Where-Object { $_.BusType -notin 'USB', 'SD', 'MMC' } | ForEach-Object {
            $r = $null; try { $r = $_ | Get-StorageReliabilityCounter -ErrorAction Stop } catch {}
            [ordered]@{
                nombre = Clean($_.FriendlyName); tipo = "$($_.MediaType)"; salud = "$($_.HealthStatus)"
                desgaste = $(if ($r -and $null -ne $r.Wear) { [int]$r.Wear } else { $null })
                temperatura = $(if ($r -and $r.Temperature) { [int]$r.Temperature } else { $null })
                errores_lectura = $(if ($r -and $null -ne $r.ReadErrorsUncorrected) { [int]$r.ReadErrorsUncorrected } else { $null })
                tamano_gb = [int][math]::Round($_.Size / 1GB)
            }
        })
    } catch {}

    # Bateria: capacidad de carga completa / de diseno. Equipos de escritorio y servidores: null.
    # BatteryStaticData da "Generic failure" en muchas notebooks modernas -> respaldo: powercfg /batteryreport /xml.
    try {
        if (Get-CimInstance Win32_Battery -ErrorAction Stop) {
            $dis = $null; $full = $null; $cic = $null
            try { $dis = [int](Get-CimInstance -Namespace root\wmi -ClassName BatteryStaticData -ErrorAction Stop | Select-Object -First 1).DesignedCapacity } catch {}
            try { $full = [int](Get-CimInstance -Namespace root\wmi -ClassName BatteryFullChargedCapacity -ErrorAction Stop | Select-Object -First 1).FullChargedCapacity } catch {}
            try { $cic = [int](Get-CimInstance -Namespace root\wmi -ClassName BatteryCycleCount -ErrorAction Stop | Select-Object -First 1).CycleCount } catch {}
            if (-not $dis -or -not $full) {
                $xml = Join-Path $env:TEMP "atlas-bateria.xml"
                & powercfg.exe /batteryreport /xml /output $xml | Out-Null
                if (Test-Path $xml) {
                    $b = ([xml](Get-Content $xml -Raw)).BatteryReport.Batteries.Battery | Select-Object -First 1
                    [IO.File]::Delete($xml)
                    if ($b) { if (-not $dis) { $dis = [int]$b.DesignCapacity }; if (-not $full) { $full = [int]$b.FullChargeCapacity }
                              if (-not $cic -and $b.CycleCount) { $cic = [int]$b.CycleCount } }
                }
            }
            if ($dis -gt 0 -and $full -gt 0) {
                $s.bateria = [ordered]@{ salud = [int][math]::Min(100, [math]::Round($full * 100 / $dis))
                                         ciclos = $(if ($cic) { $cic } else { $null }); diseno_mwh = $dis; actual_mwh = $full }
            }
        }
    } catch {}
    return $s
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
        # Filtro en el propio log (no entre los ultimos N eventos): en un equipo con mucho acceso de red los 4624
        # recientes son casi todos tipo 3. 2 = consola, 10 = escritorio remoto, 11 = credenciales en cache.
        # Se descartan las cuentas internas de Windows que tambien inician sesion tipo 2 (DWM-n, UMFD-n).
        # Solo los ultimos 30 dias y con tope de 15 s: en un controlador de dominio el log de Seguridad pesa gigas
        # y recorrerlo trababa el agente por mas de 20 minutos. Si no termina, el dato queda vacio.
        $job = Start-Job -ScriptBlock {
            $xp = "*[System[EventID=4624 and TimeCreated[timediff(@SystemTime) <= 2592000000]] and " +
                  "EventData[Data[@Name='LogonType']='2' or Data[@Name='LogonType']='10' or Data[@Name='LogonType']='11']]"
            $ev = Get-WinEvent -LogName Security -FilterXPath $xp -MaxEvents 30 -ErrorAction Stop |
                  Where-Object { $_.Properties[5].Value -notmatch '^(DWM|UMFD)-\d+$' } | Select-Object -First 1
            if ($ev) { $ev.TimeCreated.ToString("yyyy-MM-dd HH:mm") }
        }
        if (Wait-Job $job -Timeout 15) { $ultLogin = "$(Receive-Job $job -ErrorAction SilentlyContinue)".Trim() }
        else { Write-Log "Ultimo login: el log de Seguridad tardo mas de 15 s, se omite" }
        Remove-Job $job -Force -ErrorAction SilentlyContinue
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
        nombre = "$(Clean($nombre))"; tipo = "$(Get-Tipo $cs $os)"; marca = "$(Clean($cs.Manufacturer))"; modelo = "$(Get-Modelo $cs)"
        serial = "$(Clean($serial))"; cpu = "$(Clean($cpu))"; ram = "$($ramGB)GB"; disco = "$($discoGB)GB"
        so = "$(Clean($os.Caption))"; so_version = "$(Clean($os.Version))"; so_arquitectura = "$(Clean($os.OSArchitecture))"
        ip = "$ip"; red = "$(Clean($cs.Domain))"; grupo = "$(Clean($cs.SystemType))"
        usuario = "$(Clean($usuarioReal))"; usuario_alt = "$(Clean($cs.UserName))"; estado = "Activo"; ubicacion = "$(GetSede($nombre))"
        comentarios = ""; garantia = ""
        monitores = "$monitores"; impresoras = "$impresoras"; software = @($software); cifrado = "$cifrado"; tpm = "$tpm"
        ip_publica = "$ipPublica"; mac = "$(Clean($mac))"; gateway = "$gw"; ou_ad = "$(Clean($ou))"
        ultimo_reinicio = "$ultReinicio"; ultimo_login = "$ultLogin"
        salud = (Get-Salud $os)
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

function Test-Elevado {
    $id = [Security.Principal.WindowsIdentity]::GetCurrent()
    return ($id.Name -eq "NT AUTHORITY\SYSTEM") -or
           ([Security.Principal.WindowsPrincipal]$id).IsInRole([Security.Principal.WindowsBuiltInRole]::Administrator)
}

function Test-InstaladoPorMsi {
    $claves = "HKLM:\Software\Microsoft\Windows\CurrentVersion\Uninstall\*", "HKLM:\Software\Wow6432Node\Microsoft\Windows\CurrentVersion\Uninstall\*"
    return [bool](Get-ItemProperty $claves -ErrorAction SilentlyContinue | Where-Object { $_.DisplayName -eq "Atlas Agent" })
}

function Copiar-Si-Cambio($desde, $hacia) {
    if (-not (Test-Path $desde)) { return $false }
    if ((Test-Path $hacia) -and (Get-FileHash $desde).Hash -eq (Get-FileHash $hacia).Hash) { return $false }
    Copy-Item $desde $hacia -Force
    return $true
}

# Copia local: el agente no depende de que el controlador de dominio que le toque al equipo tenga la GPO al dia
# (si la replicacion de SYSVOL falla, sigue funcionando con la ultima version que recibio).
#   - Corriendo desde SYSVOL: se copia con su atlas.ini a Program Files y anota de donde vino (origen.txt).
#   - Corriendo desde la copia local: si el origen esta accesible y tiene otra version, se actualiza (rige desde la
#     proxima corrida). Si el origen no esta o esta atrasado, no pasa nada.
#   - Instalado por MSI: no se toca (el MSI maneja su propia copia).
# Devuelve la ruta que tiene que usar la tarea programada.
function Sync-CopiaLocal {
    try {
        if (-not (Test-Elevado) -or (Test-InstaladoPorMsi)) { return $SELF }
        if ($SELF -like "\\*") {
            $origenDir = Split-Path -Parent $SELF
            New-Item -ItemType Directory -Force $LOCALDIR | Out-Null
            $nuevo = Copiar-Si-Cambio $SELF (Join-Path $LOCALDIR "atlas_agent.ps1")
            $nuevo = (Copiar-Si-Cambio (Join-Path $origenDir "atlas.ini") (Join-Path $LOCALDIR "atlas.ini")) -or $nuevo
            Set-Content (Join-Path $LOCALDIR "origen.txt") $origenDir -Encoding ascii
            Restrict-Ini (Join-Path $LOCALDIR "atlas.ini")
            if ($nuevo) { Write-Log "Copia local instalada/actualizada en $LOCALDIR desde $origenDir" }
            return (Join-Path $LOCALDIR "atlas_agent.ps1")
        }
        $origenTxt = Join-Path (Split-Path -Parent $SELF) "origen.txt"
        if (Test-Path $origenTxt) {
            $origenDir = (Get-Content $origenTxt -TotalCount 1).Trim()
            if ($origenDir -and (Test-Path (Join-Path $origenDir "atlas_agent.ps1"))) {
                $nuevo = Copiar-Si-Cambio (Join-Path $origenDir "atlas_agent.ps1") $SELF
                $nuevo = (Copiar-Si-Cambio (Join-Path $origenDir "atlas.ini") (Join-Path (Split-Path -Parent $SELF) "atlas.ini")) -or $nuevo
                if ($nuevo) {
                    Restrict-Ini (Join-Path (Split-Path -Parent $SELF) "atlas.ini")
                    Write-Log "Copia local actualizada desde $origenDir (rige desde la proxima corrida)"
                }
            }
        }
    } catch { Write-Log ("Copia local: " + $_.Exception.Message) }
    return $SELF
}

# Tarea programada como SYSTEM: cada 2 horas de 8 a 22 y al iniciar sesion. Apunta a la copia local (o al MSI).
# Solo se re-registra si cambio algo.
function Set-Tarea($ruta) {
    try {
        if (-not (Test-Elevado)) { return }
        $desc = "Atlas - inventario LLyA cada 2 horas y al iniciar sesion (v$VERSION) - $ruta"
        $t = Get-ScheduledTask -TaskName $TASK -ErrorAction SilentlyContinue
        if ($t -and $t.Principal.UserId -eq "SYSTEM" -and $t.Description -eq $desc) { return }
        $a   = New-ScheduledTaskAction -Execute "powershell.exe" -Argument "-ExecutionPolicy Bypass -NonInteractive -WindowStyle Hidden -File `"$ruta`""
        $tr  = New-ScheduledTaskTrigger -Daily -At 08:00 -RandomDelay (New-TimeSpan -Minutes 15)
        $rep = New-ScheduledTaskTrigger -Once -At 08:00 -RepetitionInterval (New-TimeSpan -Hours 2) -RepetitionDuration (New-TimeSpan -Hours 14)
        if ($tr.PSObject.Properties["Repetition"]) { $tr.Repetition = $rep.Repetition }
        else {
            # Windows Server 2012 R2 / 8.1: el disparador diario no trae Repetition. Se usa uno unico que se repite
            # cada 2 horas durante 10 anios (el equivalente que acepta esa version; corre tambien de noche).
            $tr = New-ScheduledTaskTrigger -Once -At 08:00 -RandomDelay (New-TimeSpan -Minutes 15) -RepetitionInterval (New-TimeSpan -Hours 2) -RepetitionDuration (New-TimeSpan -Days 3650)
        }
        $tl  = New-ScheduledTaskTrigger -AtLogOn; $tl.Delay = "PT2M"
        $p   = New-ScheduledTaskPrincipal -UserId "SYSTEM" -LogonType ServiceAccount -RunLevel Highest
        $s   = New-ScheduledTaskSettingsSet -StartWhenAvailable -AllowStartIfOnBatteries -DontStopIfGoingOnBatteries -ExecutionTimeLimit (New-TimeSpan -Minutes 30) -MultipleInstances IgnoreNew
        Register-ScheduledTask -TaskName $TASK -Description $desc -Action $a -Trigger @($tr, $tl) -Principal $p -Settings $s -Force | Out-Null
        Write-Log "Tarea '$TASK' registrada como SYSTEM -> $ruta"
    } catch { Write-Log ("No se pudo registrar la tarea: " + $_.Exception.Message) }
}

function Restrict-Ini($ini = (Join-Path (Split-Path -Parent $SELF) "atlas.ini")) {
    # La clave vive en atlas.ini: solo SYSTEM (S-1-5-18) y Administradores (S-1-5-32-544), sin herencia.
    try {
        if ((Test-Path $ini) -and $ini -notlike "\\*") {
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
    $salud = $body.salud; $body.Remove('salud')
    $body.GetEnumerator() | ForEach-Object { "{0,-16} {1}" -f $_.Key, $_.Value }
    "salud:"; $salud | ConvertTo-Json -Depth 5
    return
}
if (-not $Server -or -not $SyncKey) {
    Say "ERROR: falta Server o SyncKey (atlas.ini al lado del script o parametros -Server / -SyncKey)." Red
    exit 2
}
Set-Tarea (Sync-CopiaLocal)

$codigo = 0
try {
    $body  = Get-Inventario
    $bytes = [Text.Encoding]::UTF8.GetBytes(($body | ConvertTo-Json -Depth 6 -Compress))
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
