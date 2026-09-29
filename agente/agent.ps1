# AssetManager Agent v3.4 - Compatible Windows Server 2008 R2+
$server = "http://192.168.100.116:8000"

try {
    # Forzar TLS 1.2 para versiones antiguas
    [Net.ServicePointManager]::SecurityProtocol = [Net.SecurityProtocolType]::Tls12

    function Clean($s) { 
        if ($null -eq $s) { return "" } 
        return ($s -replace '[\"\\\/\x00-\x1F]', ' ').Trim() 
    }

    function GetSede($nombre) {
        $n = $nombre.ToUpper()
        if ($n -match '^RSG')                                             { return "Resguarda" }
        if ($n -match '^(CBA|CBAIMPTO|CBAAUDIT|CBAADMIN|CBALEGALES|CBAMULETO)') { return "Cordoba" }
        if ($n -match '^NQN')                                             { return "Neuquen" }
        if ($n -match '^(RIMPTO|RADMIN|RAUDIT)')                          { return "Rosario" }
        if ($n -match '^(CIMPTO|CAUDIT|CADMIN)')                          { return "Corrientes" }
        if ($n -match '^(TIMPTO|TAUDIT|TADMIN)')                          { return "Tigre" }
        if ($n -match '^(MIMPTO|MADMIN|MAUDIT)')                          { return "Mendoza" }
        if ($n -match '^(ADMIN|CONSULT|AUDIT|AUDITFIN|PYMES|SISTEMAS)')   { return "CABA" }
        return "CABA"
    }

    # Datos basicos - compatibles con PS 2.0+
    $serial  = (Get-WmiObject Win32_BIOS).SerialNumber
    $cpu     = (Get-WmiObject Win32_Processor | Select-Object -First 1).Name.Trim()
    $ramGB   = [math]::Round((Get-WmiObject Win32_ComputerSystem).TotalPhysicalMemory/1GB)
    $discoGB = [math]::Round((Get-WmiObject Win32_DiskDrive | Select-Object -First 1).Size/1GB)
    $os      = Get-WmiObject Win32_OperatingSystem
    $cs      = Get-WmiObject Win32_ComputerSystem
    $nombre  = $env:COMPUTERNAME

    # IP - compatible con PS 2.0 (sin Get-NetIPAddress)
    $ip = ""
    try {
        $ip = (Get-WmiObject Win32_NetworkAdapterConfiguration | 
               Where-Object { $_.IPEnabled -eq $true -and $_.IPAddress -ne $null } | 
               Select-Object -First 1).IPAddress | 
               Where-Object { $_ -match "^\d+\.\d+\.\d+\.\d+$" } | 
               Select-Object -First 1
    } catch { $ip = "" }

    # Impresoras - compatible con PS 2.0
    $impresoras = ""
    try {
        $impresoras = (Get-WmiObject Win32_Printer -ErrorAction SilentlyContinue | 
                      Select-Object -ExpandProperty Name | 
                      ForEach-Object { Clean($_) }) -join "|"
    } catch { $impresoras = "" }

    # Monitores - compatible con PS 2.0
    $monitores = ""
    try {
        $monitores = (Get-WmiObject WmiMonitorID -Namespace root\wmi -ErrorAction SilentlyContinue | 
                     ForEach-Object {
                         $man = ($_.ManufacturerName | Where-Object {$_ -ne 0} | ForEach-Object {[char]$_}) -join ""
                         $mod = ($_.UserFriendlyName | Where-Object {$_ -ne 0} | ForEach-Object {[char]$_}) -join ""
                         Clean("$man $mod")
                     }) -join "|"
    } catch { $monitores = "" }

    # Software - compatible con PS 2.0
    $software = ""
    try {
        $paths = @(
            "HKLM:\Software\Microsoft\Windows\CurrentVersion\Uninstall\*",
            "HKLM:\Software\Wow6432Node\Microsoft\Windows\CurrentVersion\Uninstall\*",
            "HKCU:\Software\Microsoft\Windows\CurrentVersion\Uninstall\*"
        )
        $software = ($paths | ForEach-Object {
            Get-ItemProperty $_ -ErrorAction SilentlyContinue |
            Where-Object { $_.DisplayName -ne $null -and $_.DisplayName -ne "" } |
            Select-Object DisplayName, DisplayVersion, InstallDate
        } | Sort-Object DisplayName -Unique |
        ForEach-Object { "$(Clean($_.DisplayName))|||$(Clean($_.DisplayVersion))|||$(Clean($_.InstallDate))" }) -join "~~~"
    } catch { $software = "" }

    $ubicacion = GetSede($nombre)

    $body = [ordered]@{
        nombre          = "$(Clean($nombre))"
        tipo            = "Notebook"
        marca           = "$(Clean($cs.Manufacturer))"
        modelo          = "$(Clean($cs.Model))"
        serial          = "$(Clean($serial))"
        cpu             = "$(Clean($cpu))"
        ram             = "$($ramGB)GB"
        disco           = "$($discoGB)GB"
        so              = "$(Clean($os.Caption))"
        so_version      = "$(Clean($os.Version))"
        so_arquitectura = "$(Clean($os.OSArchitecture))"
        ip              = "$ip"
        red             = "$(Clean($cs.Domain))"
        grupo           = "$(Clean($cs.SystemType))"
        usuario         = "$(Clean($env:USERNAME))"
        usuario_alt     = "$(Clean($cs.UserName))"
        estado          = "Activo"
        ubicacion       = "$ubicacion"
        comentarios     = ""
        garantia        = ""
        monitores       = "$monitores"
        impresoras      = "$impresoras"
        software        = "$software"
    }

    $payload = $body | ConvertTo-Json -Depth 2 -Compress

    # HTTP Request - compatible con PS 2.0 (sin Invoke-RestMethod en algunos casos)
    try {
        # Intentar con Invoke-RestMethod (PS 3.0+)
        Invoke-RestMethod -Uri "$server/api/sync" -Method POST -ContentType "application/json; charset=utf-8" -Body ([System.Text.Encoding]::UTF8.GetBytes($payload))
    } catch {
        # Fallback con WebClient para PS 2.0
        $client = New-Object System.Net.WebClient
        $client.Headers.Add("Content-Type", "application/json; charset=utf-8")
        $client.UploadData("$server/api/sync", "POST", [System.Text.Encoding]::UTF8.GetBytes($payload)) | Out-Null
    }

    Write-Host "OK - Sincronizado: $nombre ($ubicacion)" -ForegroundColor Green

} catch {
    Write-Host "ERROR: $_" -ForegroundColor Red
}