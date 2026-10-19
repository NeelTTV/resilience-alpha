$ErrorActionPreference = 'Stop'
Push-Location (Split-Path $PSScriptRoot -Parent)
try {
    & ./.venv/Scripts/python.exe -m ruff check .
    if ($LASTEXITCODE -ne 0) { throw 'Lint failed.' }
    & ./.venv/Scripts/python.exe -m pytest -q
    if ($LASTEXITCODE -ne 0) { throw 'Backend tests failed.' }
    Push-Location apps/dashboard
    try {
        & npm run build
        if ($LASTEXITCODE -ne 0) { throw 'Dashboard build failed.' }
    } finally { Pop-Location }
    & docker compose --profile observability --profile ai config --quiet
    if ($LASTEXITCODE -ne 0) { throw 'Compose validation failed.' }
} finally { Pop-Location }

