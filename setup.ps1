# setup.ps1 — one-time setup for audio_transcribe.
# Run from the project folder:  powershell -ExecutionPolicy Bypass -File setup.ps1

Write-Host "=== audio_transcribe setup ===" -ForegroundColor Cyan

# 1. Check Python
$py = Get-Command python -ErrorAction SilentlyContinue
if (-not $py) {
    Write-Host "Python not found. Install Python 3.13 from https://python.org and re-run." -ForegroundColor Red
    exit 1
}
Write-Host "Found $(python --version)"

# 2. Create the virtual environment
if (-not (Test-Path "venv")) {
    Write-Host "Creating virtual environment (venv)..."
    python -m venv venv
} else {
    Write-Host "venv already exists, skipping."
}

# 3. Install dependencies
Write-Host "Installing dependencies (this can take a few minutes)..."
& .\venv\Scripts\python.exe -m pip install --upgrade pip
& .\venv\Scripts\python.exe -m pip install -r requirements.txt

# 4. Create .env from the template
if (-not (Test-Path ".env")) {
    Copy-Item ".env.example" ".env"
    Write-Host "Created .env — open it and add your ANTHROPIC_API_KEY (only needed for summaries)." -ForegroundColor Yellow
} else {
    Write-Host ".env already exists, leaving it as-is."
}

Write-Host ""
Write-Host "Setup complete!" -ForegroundColor Green
Write-Host "Start the app by double-clicking run.bat, or run:" -ForegroundColor Green
Write-Host "    .\venv\Scripts\python.exe run.py"
