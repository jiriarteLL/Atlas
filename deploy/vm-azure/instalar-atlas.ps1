# instalar-atlas.ps1 - Deja Atlas funcionando en la VM de Azure (LLAZSVRAPP01), al costado de Kairos y LEX.
# Ejecutar EN LA VM, en PowerShell como administrador:
#     powershell -ExecutionPolicy Bypass -File C:\Atlas\deploy\instalar-atlas.ps1
# Pide la contrasena del usuario "postgres" (no se guarda). Es idempotente: se puede volver a correr.
#
# Que hace (y que NO toca):
#   - Crea el usuario y la base "atlas" en el PostgreSQL 17 existente. No toca otras bases ni pg_hba.conf.
#   - Genera C:\Atlas\.env con secretos nuevos (si ya existe, lo conserva).
#   - Registra los servicios Atlas-HTTP (8700) y Atlas-HTTPS (8743) con el NSSM que ya esta en C:\nssm.
#   - Abre 8700/8743 en el firewall de Windows (perfiles Dominio y Privado).
#   - Programa un backup diario de la base (pg_dump, 02:30, guarda 14 dias en C:\Atlas\backups).
#   - Deja las credenciales iniciales en C:\Atlas\CREDENCIALES.txt (solo Administradores).
param([string]$AppUrl = "https://172.20.0.10:8743")

$ErrorActionPreference = "Stop"
$RAIZ  = "C:\Atlas"
$PY    = "$RAIZ\.venv\Scripts\python.exe"
$NSSM  = "C:\nssm\nssm-2.24\win64\nssm.exe"
$PGBIN = "C:\Program Files\PostgreSQL\17\bin"
$LOG   = "$RAIZ\logs\instalacion.log"
function Paso($m) { Write-Host "==> $m" -ForegroundColor Cyan; Add-Content $LOG ("{0}  {1}" -f (Get-Date -Format s), $m) }
function Token {
    $b = New-Object byte[] 32
    [Security.Cryptography.RandomNumberGenerator]::Create().GetBytes($b)
    -join ($b | ForEach-Object { '{0:x2}' -f $_ })
}

$admin = ([Security.Principal.WindowsPrincipal][Security.Principal.WindowsIdentity]::GetCurrent()).IsInRole([Security.Principal.WindowsBuiltInRole]::Administrator)
if (-not $admin) { throw "Ejecutar PowerShell como administrador." }
foreach ($f in $PY, $NSSM, "$PGBIN\psql.exe", "$RAIZ\app\backend\main.py", "$RAIZ\certs\atlas.pem") {
    if (-not (Test-Path $f)) { throw "Falta $f" }
}
New-Item -ItemType Directory -Force "$RAIZ\logs", "$RAIZ\backups" | Out-Null
foreach ($p in 8700, 8743) {
    $uso = Get-NetTCPConnection -State Listen -LocalPort $p -ErrorAction SilentlyContinue
    if ($uso -and -not (Get-Service "Atlas-*" -ErrorAction SilentlyContinue)) { throw "El puerto $p ya esta en uso por otro programa." }
}

# ---- 1. Secretos y .env (se conservan si ya existen)
$envFile = "$RAIZ\.env"
if (Test-Path $envFile) {
    Paso ".env existente: se conserva"
    $dbPass = ((Get-Content $envFile | Where-Object { $_ -match '^DATABASE_URL=' }) -replace '^.*://atlas:([^@]+)@.*$', '$1')
} else {
    $dbPass = Token
    $admPass = "Pz7#" + (Token).Substring(0, 16) + "Q!"   # sin palabras de la lista negra ("atlas", "llyasoc"...)
    $syncKey = Token
    @(
        "APP_ENV=production"
        "APP_NAME=atlas"
        "DATABASE_URL=postgres://atlas:$dbPass@127.0.0.1:5432/atlas"
        "JWT_SECRET=$(Token)"
        "SUPERADMIN_INITIAL_PASSWORD=$admPass"
        "SYNC_API_KEY=$syncKey"
        "MAESTRO_API_KEY=$(Token)"
        "FRONTEND_DIST=$RAIZ\dist"
        "AGENTE_DIR=$RAIZ\agente"
        "APP_URL=$AppUrl"
        "COOKIES_SEGURAS=true"
        "SNAPSHOT_DIAS=7"
        "LOG_FORMAT=json"
        "LOG_LEVEL=info"
        "FORWARDED_ALLOW_IPS=127.0.0.1"
    ) | Set-Content $envFile -Encoding ascii
    @(
        "ATLAS - credenciales iniciales ($(Get-Date -Format 'yyyy-MM-dd HH:mm'))"
        ""
        "Web:          $AppUrl   (y http://172.20.0.10:8700)"
        "Superadmin:   admin@llyasoc.com"
        "Contrasena:   $admPass   (la pide cambiar en el primer ingreso)"
        ""
        "Agentes (X-Sync-Key / SYNCKEY del MSI):"
        "  $syncKey"
        ""
        "Base: PostgreSQL 17 local, base 'atlas', usuario 'atlas' (contrasena en C:\Atlas\.env)"
    ) | Set-Content "$RAIZ\CREDENCIALES.txt" -Encoding utf8
    foreach ($f in $envFile, "$RAIZ\CREDENCIALES.txt") {
        & icacls.exe $f /inheritance:r /grant:r "*S-1-5-18:F" "*S-1-5-32-544:F" | Out-Null
    }
    Paso ".env y CREDENCIALES.txt generados (solo SYSTEM + Administradores)"
}

# ---- 2. Usuario y base en PostgreSQL
$pg = Read-Host "Contrasena del usuario 'postgres' de PostgreSQL 17" -AsSecureString
$env:PGPASSWORD = [Runtime.InteropServices.Marshal]::PtrToStringAuto([Runtime.InteropServices.Marshal]::SecureStringToBSTR($pg))
try {
    $psql = "$PGBIN\psql.exe"
    $existe = & $psql -h 127.0.0.1 -U postgres -tAc "SELECT 1 FROM pg_roles WHERE rolname='atlas'"
    if ($LASTEXITCODE -ne 0) { throw "No se pudo entrar a PostgreSQL con el usuario postgres (contrasena?)." }
    if ($existe -ne "1") {
        & $psql -h 127.0.0.1 -U postgres -v ON_ERROR_STOP=1 -c "CREATE ROLE atlas LOGIN PASSWORD '$dbPass'" | Out-Null
        Paso "Usuario 'atlas' creado"
    } else {
        & $psql -h 127.0.0.1 -U postgres -v ON_ERROR_STOP=1 -c "ALTER ROLE atlas PASSWORD '$dbPass'" | Out-Null
        Paso "Usuario 'atlas' ya existia: contrasena alineada con .env"
    }
    $hayBase = & $psql -h 127.0.0.1 -U postgres -tAc "SELECT 1 FROM pg_database WHERE datname='atlas'"
    if ($hayBase -ne "1") {
        & $psql -h 127.0.0.1 -U postgres -v ON_ERROR_STOP=1 -c "CREATE DATABASE atlas OWNER atlas ENCODING 'UTF8' TEMPLATE template0" | Out-Null
        Paso "Base 'atlas' creada"
    } else { Paso "Base 'atlas' ya existia" }
} finally { Remove-Item Env:\PGPASSWORD -ErrorAction SilentlyContinue }

# ---- 3. Servicios NSSM
foreach ($s in @(@{N = "Atlas-HTTP"; M = "http"; D = "Atlas (HTTP 8700)"}, @{N = "Atlas-HTTPS"; M = "https"; D = "Atlas (HTTPS 8743)"})) {
    if (-not (Get-Service $s.N -ErrorAction SilentlyContinue)) {
        & $NSSM install $s.N $PY "$RAIZ\deploy\run_atlas.py" $s.M | Out-Null
    } else {
        & $NSSM set $s.N Application $PY | Out-Null
        & $NSSM set $s.N AppParameters "`"$RAIZ\deploy\run_atlas.py`" $($s.M)" | Out-Null
    }
    & $NSSM set $s.N DisplayName $s.D | Out-Null
    & $NSSM set $s.N Description "Atlas - inventario LLyA" | Out-Null
    & $NSSM set $s.N AppDirectory "$RAIZ\app\backend" | Out-Null
    & $NSSM set $s.N AppStdout "$RAIZ\logs\$($s.N).log" | Out-Null
    & $NSSM set $s.N AppStderr "$RAIZ\logs\$($s.N).log" | Out-Null
    & $NSSM set $s.N AppRotateFiles 1 | Out-Null
    & $NSSM set $s.N AppRotateBytes 10485760 | Out-Null
    & $NSSM set $s.N Start SERVICE_AUTO_START | Out-Null
    & $NSSM set $s.N DependOnService postgresql-x64-17 | Out-Null
    Paso "Servicio $($s.N) configurado"
}
Restart-Service Atlas-HTTP
Start-Sleep 20
Restart-Service Atlas-HTTPS
Paso "Servicios iniciados"

# ---- 4. Firewall
if (-not (Get-NetFirewallRule -DisplayName "Atlas 8700/8743" -ErrorAction SilentlyContinue)) {
    New-NetFirewallRule -DisplayName "Atlas 8700/8743" -Direction Inbound -Protocol TCP -LocalPort 8700, 8743 -Action Allow -Profile Domain, Private | Out-Null
    Paso "Firewall: 8700 y 8743 abiertos (Dominio y Privado)"
}

# ---- 5. Backup diario
$bk = "$RAIZ\deploy\backup-atlas.ps1"
@"
`$ErrorActionPreference = 'Stop'
`$url = (Get-Content '$envFile' | Where-Object { `$_ -match '^DATABASE_URL=' }) -replace '^DATABASE_URL=postgres://', 'postgresql://'
`$archivo = '$RAIZ\backups\atlas_' + (Get-Date -Format 'yyyy-MM-dd_HHmm') + '.dump'
& '$PGBIN\pg_dump.exe' --format=custom --file=`$archivo `$url
Get-ChildItem '$RAIZ\backups' -Filter 'atlas_*.dump' | Where-Object LastWriteTime -lt (Get-Date).AddDays(-14) | Remove-Item -Force
Add-Content '$RAIZ\logs\backup.log' ((Get-Date -Format s) + '  OK ' + `$archivo)
"@ | Set-Content $bk -Encoding utf8
$a = New-ScheduledTaskAction -Execute "powershell.exe" -Argument "-ExecutionPolicy Bypass -NonInteractive -File `"$bk`""
$t = New-ScheduledTaskTrigger -Daily -At 02:30
$p = New-ScheduledTaskPrincipal -UserId "SYSTEM" -LogonType ServiceAccount -RunLevel Highest
Register-ScheduledTask -TaskName "Atlas Backup" -Action $a -Trigger $t -Principal $p -Force | Out-Null
Paso "Backup diario programado (02:30, 14 dias)"

# ---- 6. Verificacion
$ok = $false
for ($i = 0; $i -lt 12 -and -not $ok; $i++) {
    try { $ok = (Invoke-WebRequest "http://127.0.0.1:8700/health" -UseBasicParsing -TimeoutSec 5).StatusCode -eq 200 } catch { Start-Sleep 5 }
}
if ($ok) {
    Paso "LISTO: Atlas responde. Credenciales en $RAIZ\CREDENCIALES.txt"
    Write-Host "`nAtlas: $AppUrl   |   http://172.20.0.10:8700" -ForegroundColor Green
} else {
    Paso "Atlas no respondio en /health. Revisar $RAIZ\logs\Atlas-HTTP.log"
    exit 1
}
