$ErrorActionPreference = 'Stop'
$repoPath = Split-Path $PSScriptRoot -Parent
Push-Location $repoPath
try {
    if (!(Test-Path .venv/Scripts/python.exe)) {
        & py -3 -m venv .venv
        if ($LASTEXITCODE -ne 0) { throw 'Python 3.10+ is required.' }
    }
    & ./.venv/Scripts/python.exe -m pip install -r requirements-dev.lock
    if ($LASTEXITCODE -ne 0) { throw 'Python dependencies failed.' }
    & ./.venv/Scripts/python.exe scripts/init-secrets.py
    if ($LASTEXITCODE -ne 0) { throw 'Secret initialization failed.' }
    Push-Location apps/dashboard
    try {
        & npm ci
        if ($LASTEXITCODE -ne 0) { throw 'Frontend dependencies failed.' }
    } finally { Pop-Location }
    Write-Output 'Ready. Start Docker Desktop, then: docker compose up --build -d --wait'
} finally { Pop-Location }

