# AssetManager Network Scanner v2.1
$server = "http://192.168.0.88:8000"

function Clean($s) { if ($null -eq $s) { return "" } return ($s -replace '[\"\\\/\x00-\x1F]', ' ').Trim() }

function GetSedePorNombre($nombre) {
    $n = $nombre.ToUpper()
    if ($n -match '^RSG')                                            { return "Resguarda" }
    if ($n -match '^CBA')                                            { return "Cordoba" }
    if ($n -match '^NQN')                                            { return "Neuquen" }
    if ($n -match '^(RIMPTO|RADMIN|RAUDIT)')                         { return "Rosario" }
    if ($n -match '^(CIMPTO|CAUDIT|CADMIN)')                         { return "Corrientes" }
    if ($n -match '^(TIMPTO|TAUDIT|TADMIN)')                         { return "Tigre" }
    if ($n -match '^(MIMPTO|MADMIN|MAUDIT)')                         { return "Mendoza" }
    if ($n -match '^(ADMIN|CONSULT|AUDIT|AUDITFIN|PYMES|SISTEMAS)')  { return "CABA" }
    return $null
}

function GetSedePorRed($red) {
    switch -Wildcard ($red) {
        "192.168.100.*" { return "CABA" }
        "192.168.252.*" { return "CABA" }
        "172.16.11.*"   { return "Rosario" }
        "172.16.8.*"    { return "Rosario" }
        "192.168.24.*"  { return "Cordoba" }
        "192.168.10.*"  { return "Corrientes" }
        "192.168.90.*"  { return "Mendoza" }
        "172.16.32.*"   { return "Neuquen" }
        "192.168.9.*"   { return "Tigre" }
        "192.168.8.*"   { return "Resguarda" }
        default         { return "CABA" }
    }
}

function GetUsuario($ip) {
    try {
        $result = quser /server:$ip 2>$null
        if ($result) {
            $lineas = $result | Select-Object -Skip 1
            foreach ($linea in $lineas) {
                if ($linea -match "^\s*>?\s*(\S+)") {
                    return $matches[1]
                }
            }
        }
    } catch {}
    return ""
}

$redes = @(
    @{ sede="CABA";       red="192.168.100" },
    @{ sede="CABA";       red="192.168.252" },
    @{ sede="Rosario";    red="172.16.11"   },
    @{ sede="Rosario";    red="172.16.8"    },
    @{ sede="Cordoba";    red="192.168.24"  },
    @{ sede="Corrientes"; red="192.168.10"  },
    @{ sede="Mendoza";    red="192.168.90"  },
    @{ sede="Neuquen";    red="172.16.32"   },
    @{ sede="Tigre";      red="192.168.9"   },
    @{ sede="Resguarda";  red="192.168.8"   }
)

$totalEncontrados = 0
$totalRegistrados = 0

foreach ($r in $redes) {
    Write-Host ""
    Write-Host "=== Escaneando $($r.sede) ($($r.red).0/24) ===" -ForegroundColor Cyan

    1..254 | ForEach-Object {
        $ip = "$($r.red).$_"
        if (Test-Connection -ComputerName $ip -Count 1 -Quiet -ErrorAction SilentlyContinue) {
            $totalEncontrados++

            # Resolver hostname via DNS
            $nombre = ""
            try {
                $dns = [System.Net.Dns]::GetHostEntry($ip)
                $nombre = $dns.HostName.Split(".")[0].ToUpper()
            } catch {
                $nombre = "DESCONOCIDO-$($ip -replace '\.', '-')"
            }

            # Determinar sede - primero por nombre, si no por red
            $sedePorNombre = GetSedePorNombre($nombre)
            $sedePorRed    = GetSedePorRed("$ip")
            $ubicacion     = if ($sedePorNombre) { $sedePorNombre } else { $sedePorRed }

            # Intentar obtener usuario logueado
            $usuario = GetUsuario($ip)

            Write-Host "  Encontrado: $ip - $nombre ($ubicacion) - Usuario: $(if($usuario){$usuario}else{'desconocido'})" -ForegroundColor Yellow

            try {
                $body = [ordered]@{
                    nombre          = "$nombre"
                    tipo            = "Notebook"
                    marca           = ""
                    modelo          = ""
                    serial          = "SCAN-$($ip -replace '\.', '-')"
                    cpu             = ""
                    ram             = ""
                    disco           = ""
                    so              = ""
                    so_version      = ""
                    so_arquitectura = ""
                    ip              = "$ip"
                    red             = ""
                    grupo           = ""
                    usuario         = "$usuario"
                    usuario_alt     = ""
                    estado          = "Activo"
                    ubicacion       = "$ubicacion"
                    comentarios     = "Descubierto por escaneo de red - pendiente sincronizacion con agente"
                    garantia        = ""
                    monitores       = ""
                    impresoras      = ""
                    software        = ""
                }

                $payload = $body | ConvertTo-Json -Depth 2 -Compress
                Invoke-RestMethod -Uri "$server/api/sync" -Method POST -ContentType "application/json; charset=utf-8" -Body ([System.Text.Encoding]::UTF8.GetBytes($payload))
                Write-Host "    OK - Registrado: $nombre ($ubicacion)" -ForegroundColor Green
                $totalRegistrados++
            } catch {
                Write-Host "    Error al registrar: $_" -ForegroundColor Red
            }
        }
    }
}

Write-Host ""
Write-Host "==============================" -ForegroundColor Cyan
Write-Host "Escaneo completado!" -ForegroundColor Cyan
Write-Host "Equipos encontrados: $totalEncontrados" -ForegroundColor White
Write-Host "Equipos registrados: $totalRegistrados" -ForegroundColor Green
Write-Host "==============================" -ForegroundColor Cyan