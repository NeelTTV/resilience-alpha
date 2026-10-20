$ErrorActionPreference = 'Stop'
Push-Location (Split-Path $PSScriptRoot -Parent)
try {
    if (!(Test-Path .camera-venv/Scripts/python.exe)) {
        & py -3 -m venv .camera-venv
        if ($LASTEXITCODE -ne 0) { throw 'Camera environment creation failed' }
    }
    & .camera-venv/Scripts/python.exe -m pip install -r services/host_camera/requirements.txt
    if ($LASTEXITCODE -ne 0) { throw 'Camera dependencies installation failed' }
    & ./.venv/Scripts/python.exe scripts/init-secrets.py
    if ($LASTEXITCODE -ne 0) { throw 'Secret initialization failed' }
    & .camera-venv/Scripts/python.exe -m services.host_camera.main @args
    if ($LASTEXITCODE -ne 0) { throw 'Camera agent failed' }
} finally { Pop-Location }
