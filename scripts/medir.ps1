# Ejecuta la prueba de estrés (k6 en contenedor) y, en paralelo, muestrea cada ~3 s
# las estadísticas de los contenedores (docker stats) y las conexiones activas en
# PostgreSQL (pg_stat_activity). Solo usa la CLI de Docker.
#
# Uso (desde la raíz del proyecto, con el entorno ya levantado):
#   powershell -ExecutionPolicy Bypass -File scripts\medir.ps1 [-Etiqueta corrida1]
param(
  [string]$Etiqueta = "corrida",
  [string]$Escalones = "100,300,600,900,1200,1500,2000",
  [string]$Duracion = "3m",
  [string]$Calentar = "1m",
  [int]$Reposo = 60
)
$ErrorActionPreference = "Stop"
Set-Location (Split-Path $PSScriptRoot -Parent)
$dir = "resultados\$Etiqueta"
New-Item -ItemType Directory -Force $dir | Out-Null

$env:ESCALONES = $Escalones; $env:DURACION = $Duracion; $env:CALENTAR_DUR = $Calentar
$stats = "$dir\docker-stats.csv"
"ts,contenedor,cpu_pct,mem_mib,conexiones_bd" | Out-File -Encoding utf8 $stats

function A-MiB([string]$s) {
  $v = [double]($s -replace '[^\d\.]', '')
  if ($s -match 'GiB') { return $v * 1024 } elseif ($s -match 'KiB') { return $v / 1024 } else { return $v }
}

function Muestrear {
  $ts = [DateTimeOffset]::UtcNow.ToUnixTimeSeconds()
  $con = (docker compose exec -T db psql -U crud -d crud -tAc "SELECT count(*) FROM pg_stat_activity WHERE datname='crud' AND pid <> pg_backend_pid()" 2>$null)
  $con = ($con | Select-Object -First 1).Trim()
  $lineas = docker stats --no-stream --format "{{.Name}};{{.CPUPerc}};{{.MemUsage}}"
  foreach ($l in $lineas) {
    $p = $l.Split(';')
    if ($p[0] -notmatch 'lab04') { continue }
    $cpu = ($p[1] -replace '%', '')
    $mem = A-MiB (($p[2] -split '/')[0].Trim())
    "$ts,$($p[0]),$cpu,$([math]::Round($mem,1)),$con" | Out-File -Append -Encoding utf8 $stats
  }
}

# Línea base: entorno en reposo (app + BD + APM corriendo, sin carga).
$inicioReposo = [DateTimeOffset]::UtcNow.ToUnixTimeSeconds()
Write-Host "Midiendo línea base en reposo durante $Reposo s..."
while ([DateTimeOffset]::UtcNow.ToUnixTimeSeconds() - $inicioReposo -lt $Reposo) { Muestrear; Start-Sleep -Seconds 2 }

$inicio = [DateTimeOffset]::UtcNow.ToUnixTimeSeconds()
@{ etiqueta = $Etiqueta; inicio = $inicio; inicio_reposo = $inicioReposo; escalones = $Escalones
   duracion = $Duracion; calentamiento = $Calentar } |
  ConvertTo-Json | Out-File -Encoding utf8 "$dir\ejecucion.json"

Write-Host "Iniciando k6 ($Escalones usuarios, $Duracion por escalón)..."
$k6 = Start-Process docker -ArgumentList "compose --profile carga run --rm k6" -NoNewWindow -PassThru `
  -RedirectStandardOutput "$dir\k6-salida.txt" -RedirectStandardError "$dir\k6-errores.txt"

while (-not $k6.HasExited) { Muestrear; Start-Sleep -Seconds 2 }
if (Test-Path "resultados\k6-resumen.json") { Move-Item -Force "resultados\k6-resumen.json" "$dir\k6-resumen.json" }
Write-Host "Prueba terminada. Datos en $dir"

