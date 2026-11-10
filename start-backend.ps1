# Start ShelfMate FastAPI backend on http://127.0.0.1:8000
$ErrorActionPreference = "Stop"
Set-Location $PSScriptRoot\backend

if (-not (Test-Path .\.venv\Scripts\python.exe)) {
  Write-Host "Creating virtualenv..."
  python -m venv .venv
  .\.venv\Scripts\pip.exe install -r requirements.txt
}

if (-not (Test-Path .\.env)) {
  Copy-Item .\.env.example .\.env
}

Write-Host "ShelfMate API -> http://127.0.0.1:8000"
.\.venv\Scripts\python.exe -m uvicorn app.main:app --reload --host 127.0.0.1 --port 8000
