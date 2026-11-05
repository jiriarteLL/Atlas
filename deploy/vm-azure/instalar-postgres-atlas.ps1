# instalar-postgres-atlas.ps1 - PostgreSQL 16 PROPIO de Atlas en la VM (separado del PostgreSQL 17 de nddPrint).
# Ejecutar en la VM como administrador. Idempotente.
#   - Binarios en C:\Atlas\pgsql, datos en C:\Atlas\pgdata.
#   - Puerto 5433, escucha SOLO en 127.0.0.1 (no se abre en el firewall).
#   - Servicio "Atlas-PostgreSQL" (automatico, NT AUTHORITY\NetworkService).
#   - Contrasena del superusuario generada al azar en C:\Atlas\pg-superusuario.txt (solo SYSTEM + Administradores).
param(
    [string]$Version = "16.15-1",
    [int]$Puerto = 5433
)
$ErrorActionPreference = "Stop"
$RAIZ  = "C:\Atlas"
$PGDIR = "$RAIZ\pgsql"
$DATA  = "$RAIZ\pgdata"
$SVC   = "Atlas-PostgreSQL"
$PWF   = "$RAIZ\pg-superusuario.txt"
function Paso($m) { Write-Host "==> $m"; Add-Content "$RAIZ\logs\instalacion.log" ("{0}  {1}" -f (Get-Date -Format s), $m) }
New-Item -ItemType Directory -Force "$RAIZ\logs" | Out-Null

# 1. Binarios
if (-not (Test-Path "$PGDIR\bin\pg_ctl.exe")) {
    $zip = "$env:TEMP\pgsql-$Version.zip"
    if (-not (Test-Path $zip)) {
        [Net.ServicePointManager]::SecurityProtocol = [Net.SecurityProtocolType]::Tls12
        $ProgressPreference = "SilentlyContinue"
        Invoke-WebRequest "https://get.enterprisedb.com/postgresql/postgresql-$Version-windows-x64-binaries.zip" -OutFile $zip -UseBasicParsing
    }
    $tmp = "$env:TEMP\pgsql-extraer"
    Remove-Item $tmp -Recurse -Force -ErrorAction SilentlyContinue
    Expand-Archive $zip $tmp -Force
    Move-Item "$tmp\pgsql" $PGDIR
    Remove-Item $tmp -Recurse -Force -ErrorAction SilentlyContinue
    # Move-Item conserva el ACL del TEMP del usuario: se vuelve al heredado para que el servicio pueda ejecutarlo.
    & icacls.exe $PGDIR /reset /T /Q | Out-Null
    Paso "PostgreSQL $Version descomprimido en $PGDIR"
} else { Paso "Binarios ya presentes" }
& "$PGDIR\bin\postgres.exe" --version

# 2. Cluster
if (-not (Test-Path "$DATA\PG_VERSION")) {
    if (-not (Test-Path $PWF)) {
        $b = New-Object byte[] 24; [Security.Cryptography.RandomNumberGenerator]::Create().GetBytes($b)
        (-join ($b | ForEach-Object { '{0:x2}' -f $_ })) | Set-Content $PWF -Encoding ascii -NoNewline
        & icacls.exe $PWF /inheritance:r /grant:r "*S-1-5-18:F" "*S-1-5-32-544:F" | Out-Null
    }
    New-Item -ItemType Directory -Force $DATA | Out-Null
    # initdb corre con un token sin privilegios de administrador: no puede leer $PWF (solo Administradores).
    # Se le pasa una copia temporal en el TEMP del usuario, que se borra enseguida.
    $pwTmp = Join-Path $env:TEMP ("pgpw_" + [guid]::NewGuid().ToString("N"))
    Copy-Item $PWF $pwTmp
    try {
        & "$PGDIR\bin\initdb.exe" -D $DATA -U postgres --pwfile=$pwTmp --auth=scram-sha-256 --encoding=UTF8 --no-locale | Out-Null
        if ($LASTEXITCODE -ne 0) { throw "initdb fallo" }
    } finally { Remove-Item $pwTmp -Force -ErrorAction SilentlyContinue }
    $conf = "$DATA\postgresql.conf"
    Add-Content $conf "`n# --- Atlas ---`nport = $Puerto`nlisten_addresses = '127.0.0.1'`nmax_connections = 50`nshared_buffers = 256MB`nlog_timezone = 'America/Argentina/Buenos_Aires'`ntimezone = 'UTC'"
    Paso "Cluster creado en $DATA (puerto $Puerto, solo 127.0.0.1)"
} else { Paso "Cluster ya existente en $DATA" }

# 3. Permisos y servicio
& icacls.exe $DATA /grant "*S-1-5-20:(OI)(CI)F" /T /Q | Out-Null   # NETWORK SERVICE
if (-not (Get-Service $SVC -ErrorAction SilentlyContinue)) {
    & "$PGDIR\bin\pg_ctl.exe" register -N $SVC -D $DATA -S auto -U "NT AUTHORITY\NetworkService" -w | Out-Null
    Paso "Servicio $SVC registrado"
}
Start-Service $SVC
(Get-Service $SVC).WaitForStatus("Running", "00:00:30")
$env:PGPASSWORD = Get-Content $PWF
try {
    $v = & "$PGDIR\bin\psql.exe" -h 127.0.0.1 -p $Puerto -U postgres -tAc "SELECT version()"
    if ($LASTEXITCODE -ne 0) { throw "No responde en 127.0.0.1:$Puerto" }
    Paso "OK: $v"
} finally { Remove-Item Env:\PGPASSWORD -ErrorAction SilentlyContinue }
