$ErrorActionPreference = "Stop"

$ProjectRoot = Split-Path -Parent $MyInvocation.MyCommand.Path
Set-Location $ProjectRoot

$VenvPython = Join-Path $ProjectRoot "venv\Scripts\python.exe"

& $VenvPython -m pip install --upgrade pip
& $VenvPython -m pip install -r requirements.txt

if (-not (Test-Path ".env")) {
    Copy-Item ".env.example" ".env"
    Write-Host "Created .env from .env.example."
    Write-Host "Fill PostgreSQL settings in .env and run run.ps1 again."
    exit 1
}

$RequiredKeys = @("SECRET_KEY", "DB_NAME", "DB_USER", "DB_PASSWORD", "DB_HOST", "DB_PORT")
$EnvLines = Get-Content ".env" -Encoding UTF8
$Missing = @()

foreach ($Key in $RequiredKeys) {
    $Line = $EnvLines | Where-Object { $_ -match "^\s*$Key\s*=" } | Select-Object -First 1
    if (-not $Line) {
        $Missing += $Key
        continue
    }
    $Value = ($Line -split "=", 2)[1].Trim()
    if ([string]::IsNullOrWhiteSpace($Value)) {
        $Missing += $Key
    }
}

if ($Missing.Count -gt 0) {
    Write-Host "Fill these .env values: $($Missing -join ', ')"
    exit 1
}

& $VenvPython manage.py migrate
& $VenvPython manage.py runserver
