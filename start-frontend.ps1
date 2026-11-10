# Start ShelfMate Vite frontend on http://localhost:5173
$ErrorActionPreference = "Stop"
Set-Location $PSScriptRoot\frontend

if (-not (Test-Path .\node_modules)) {
  npm install
}

npm run dev
