<#
  Atlas - relevamiento DHCP de telefonos (modulo Telefonia)

  Lee, SOLO LECTURA, las concesiones de los servidores DHCP de Windows (Get-DhcpServerv4Scope +
  Get-DhcpServerv4Lease por Invoke-Command) y se queda con las MAC de los fabricantes de telefonos configurados
  (Grandstream). Le manda a Atlas {mac, ip, hostname, vence}; Atlas pone la IP en el interno que tiene esa MAC
  (de la exportacion de 3CX) y registra los telefonos sin interno. No barre la red ni toca la configuracion DHCP.

  Configuracion en telefonia-dhcp.ini al lado del script (solo SYSTEM y Administradores: tiene la clave):
      [atlas]
      Server=https://atlas.ejemplo:8743
      SyncKey=<SYNC_API_KEY de Atlas>
      CertInterno=1                      (1 solo con certificado interno, p. ej. mkcert)
      Servidores=dhcp1.dominio,dhcp2.dominio
      Ouis=C0-74-AD,EC-74-D7,00-0B-82   (prefijos de MAC de Grandstream)

  Uso:  powershell -ExecutionPolicy Bypass -File relevar_telefonos_dhcp.ps1 [-Probar]
        -Probar muestra lo que encontraria y NO lo manda a Atlas.
  Log:  C:\ProgramData\LLyA\atlas-telefonia-dhcp.log
#>
param([switch]$Probar)

$ErrorActionPreference = "Stop"
$AQUI   = Split-Path -Parent $PSCommandPath
$LOGDIR = Join-Path $env:ProgramData "LLyA"
$LOG    = Join-Path $LOGDIR "atlas-telefonia-dhcp.log"

function Write-Log($m) {
    try {
        if (-not (Test-Path $LOGDIR)) { New-Item -ItemType Directory -Path $LOGDIR -Force | Out-Null }
        if ((Test-Path $LOG) -and (Get-Item $LOG).Length -gt 1MB) { Move-Item $LOG "$LOG.1" -Force }
        Add-Content -Path $LOG -Value ("{0}  {1}" -f (Get-Date -Format "yyyy-MM-dd HH:mm:ss"), $m)
    } catch {}
    Write-Host $m
}

# ---- Configuracion
$cfg = @{ Server = ""; SyncKey = ""; CertInterno = "0"; Servidores = ""; Ouis = "C0-74-AD,EC-74-D7,00-0B-82" }
$ini = Join-Path $AQUI "telefonia-dhcp.ini"
if (Test-Path $ini) {
    Get-Content $ini | ForEach-Object {
        if ($_ -match '^\s*([A-Za-z]+)\s*=\s*(.*?)\s*$' -and $cfg.ContainsKey($Matches[1])) { $cfg[$Matches[1]] = $Matches[2] }
    }
}
$servidores = @($cfg.Servidores -split '[,;\s]+' | Where-Object { $_ })
$ouis = @($cfg.Ouis -split '[,;\s]+' | Where-Object { $_ } | ForEach-Object { ($_ -replace '[^0-9A-Fa-f]', '').ToUpper() })
if (-not $servidores.Count -or -not $ouis.Count) { Write-Log "ERROR: faltan Servidores u Ouis en telefonia-dhcp.ini"; exit 2 }
if (-not $Probar -and (-not $cfg.Server -or -not $cfg.SyncKey)) { Write-Log "ERROR: faltan Server o SyncKey en telefonia-dhcp.ini"; exit 2 }

# ---- Lectura de concesiones (solo lectura)
$concesiones = @{}
foreach ($s in $servidores) {
    try {
        $leidas = Invoke-Command -ComputerName $s -ErrorAction Stop -ArgumentList (, $ouis) -ScriptBlock {
            param($ouis)
            Get-DhcpServerv4Scope -ErrorAction Stop | ForEach-Object {
                Get-DhcpServerv4Lease -ScopeId $_.ScopeId -ErrorAction SilentlyContinue | ForEach-Object {
                    $mac = ($_.ClientId -replace '[^0-9A-Fa-f]', '').ToUpper()
                    if ($mac.Length -eq 12 -and $ouis -contains $mac.Substring(0, 6)) {
                        [pscustomobject]@{ mac = $mac; ip = "$($_.IPAddress)"; hostname = "$($_.HostName)"
                                           vence = $(if ($_.LeaseExpiryTime) { $_.LeaseExpiryTime.ToString("s") } else { "" }) }
                    }
                }
            }
        }
        foreach ($c in @($leidas)) {
            # si la misma MAC aparece en dos servidores (ambito duplicado / conmutacion), queda la que vence despues
            $prev = $concesiones[$c.mac]
            if (-not $prev -or "$($c.vence)" -gt "$($prev.vence)") {
                $concesiones[$c.mac] = @{ mac = $c.mac; ip = $c.ip; hostname = "$($c.hostname)"; vence = "$($c.vence)" }
            }
        }
        Write-Log ("{0}: {1} telefonos" -f $s, @($leidas).Count)
    } catch { Write-Log ("{0}: ERROR {1}" -f $s, $_.Exception.Message) }
}

$lista = @($concesiones.Values)
if ($Probar) {
    $lista | ForEach-Object { [pscustomobject]$_ } | Sort-Object ip | Format-Table mac, ip, hostname, vence -AutoSize
    Write-Host ("{0} telefonos (no se mando nada a Atlas)" -f $lista.Count)
    exit 0
}

# ---- Envio a Atlas
[Net.ServicePointManager]::SecurityProtocol = [Net.SecurityProtocolType]::Tls12
if ($cfg.CertInterno -eq "1") { [Net.ServicePointManager]::ServerCertificateValidationCallback = { $true } }
$cuerpo = ConvertTo-Json -InputObject @{ concesiones = $lista } -Depth 4 -Compress
try {
    $wc = New-Object Net.WebClient
    $wc.Headers["Content-Type"] = "application/json; charset=utf-8"
    $wc.Headers["X-Sync-Key"] = $cfg.SyncKey
    $r = $wc.UploadData(($cfg.Server.TrimEnd("/") + "/api/telefonia/relevamiento-dhcp"), "POST", [Text.Encoding]::UTF8.GetBytes($cuerpo))
    Write-Log ("OK - {0} telefonos enviados: {1}" -f $lista.Count, [Text.Encoding]::UTF8.GetString($r))
} catch {
    Write-Log ("ERROR al enviar a Atlas: " + $_.Exception.Message)
    exit 1
}
