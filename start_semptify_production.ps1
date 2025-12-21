# =============================================================================
# Semptify 5.0 - Production Server Startup Script
# =============================================================================
# This script starts Semptify with enforced security settings
# =============================================================================

$ErrorActionPreference = "Stop"
$Host.UI.RawUI.WindowTitle = "Semptify 5.0 - Production Server"

# Set working directory
$ScriptDir = Split-Path -Parent $MyInvocation.MyCommand.Path
Set-Location $ScriptDir

# Colors for output
function Write-Header { param($msg) Write-Host "`n========================================" -ForegroundColor Cyan; Write-Host $msg -ForegroundColor Cyan; Write-Host "========================================`n" -ForegroundColor Cyan }
function Write-Success { param($msg) Write-Host "[✓] $msg" -ForegroundColor Green }
function Write-Info { param($msg) Write-Host "[i] $msg" -ForegroundColor Yellow }
function Write-Error { param($msg) Write-Host "[X] $msg" -ForegroundColor Red }

Write-Header "SEMPTIFY 5.0 - PRODUCTION SERVER"

# Check for virtual environment
if (-not (Test-Path ".venv\Scripts\python.exe")) {
    Write-Error "Virtual environment not found. Please run setup first."
    Read-Host "Press Enter to exit"
    exit 1
}

Write-Success "Virtual environment found"

# Check for .env file
if (-not (Test-Path ".env")) {
    Write-Info "Creating production .env file from template..."
    
    # Generate secure random values
    $SecretKey = -join ((48..57) + (65..90) + (97..122) | Get-Random -Count 64 | ForEach-Object {[char]$_})
    $AdminPin = -join ((48..57) + (65..90) + (97..122) | Get-Random -Count 16 | ForEach-Object {[char]$_})
    $InviteCode1 = -join ((48..57) + (65..90) | Get-Random -Count 12 | ForEach-Object {[char]$_})
    $InviteCode2 = -join ((48..57) + (65..90) | Get-Random -Count 12 | ForEach-Object {[char]$_})
    
    # Read template and create production .env
    if (Test-Path ".env.example") {
        $content = Get-Content ".env.example" -Raw
        $content = $content -replace "SECRET_KEY=CHANGE-ME-generate-a-secure-random-key", "SECRET_KEY=$SecretKey"
        $content = $content -replace "ADMIN_PIN=CHANGE-ME", "ADMIN_PIN=$AdminPin"
        $content = $content -replace "INVITE_CODES=CHANGE-CODE-1,CHANGE-CODE-2", "INVITE_CODES=$InviteCode1,$InviteCode2"
        $content | Set-Content ".env"
        Write-Success "Production .env created with secure random values"
        Write-Info "Admin PIN: $AdminPin (save this!)"
    }
}

# Set production environment variables
$env:SECURITY_MODE = "enforced"
$env:PYTHONDONTWRITEBYTECODE = "1"
$env:PYTHONUNBUFFERED = "1"

Write-Success "Security Mode: ENFORCED"

# Ensure database tables exist (including OAuth states table)
Write-Info "Ensuring database tables are up to date..."
& ".venv\Scripts\python.exe" -c @"
import asyncio
from app.core.database import get_engine, Base
from app.models import models  # Import all models

async def create_tables():
    engine = get_engine()
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

asyncio.run(create_tables())
print('Database tables verified.')
"@

Write-Success "Database initialized"
Write-Success "Starting production server..."

Write-Host "`n-----------------------------------------" -ForegroundColor DarkGray
Write-Host "Server URL:   http://localhost:8000" -ForegroundColor White
Write-Host "API Docs:     http://localhost:8000/docs" -ForegroundColor White
Write-Host "Welcome:      http://localhost:8000/static/welcome.html" -ForegroundColor White
Write-Host "-----------------------------------------" -ForegroundColor DarkGray
Write-Host "`nPress Ctrl+C to stop the server`n" -ForegroundColor Yellow

# Start uvicorn with production settings
& ".venv\Scripts\python.exe" -m uvicorn app.main:app `
    --host 0.0.0.0 `
    --port 8000 `
    --workers 4 `
    --limit-concurrency 100 `
    --limit-max-requests 10000 `
    --timeout-keep-alive 30 `
    --access-log `
    --log-level info

# If we get here, server stopped
Write-Host "`nServer stopped." -ForegroundColor Yellow
Read-Host "Press Enter to exit"
