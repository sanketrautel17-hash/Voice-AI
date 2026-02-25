# ─────────────────────────────────────────────────────────────────────────────
# start_ngrok.ps1 — Find, configure and start ngrok for Voice AI backend
# ─────────────────────────────────────────────────────────────────────────────

$ErrorActionPreference = "Stop"

# 1. Locate ngrok.exe (WinGet install location)
$ngrokExe = (Get-ChildItem "$env:LOCALAPPDATA\Microsoft\WinGet\Packages\" -Recurse -Filter "ngrok.exe" -ErrorAction SilentlyContinue | Select-Object -First 1).FullName

if (-not $ngrokExe) {
    Write-Host "❌ ngrok.exe not found. Installing via winget..." -ForegroundColor Red
    winget install ngrok.ngrok --accept-package-agreements --accept-source-agreements
    $ngrokExe = (Get-ChildItem "$env:LOCALAPPDATA\Microsoft\WinGet\Packages\" -Recurse -Filter "ngrok.exe" | Select-Object -First 1).FullName
}

Write-Host "✅ Found ngrok at: $ngrokExe" -ForegroundColor Green

# 2. Add to current session PATH
$ngrokDir = Split-Path $ngrokExe
$env:PATH = "$env:PATH;$ngrokDir"

# 3. Add to User PATH permanently
$userPath = [Environment]::GetEnvironmentVariable("PATH", "User")
if ($userPath -notlike "*$ngrokDir*") {
    [Environment]::SetEnvironmentVariable("PATH", "$userPath;$ngrokDir", "User")
    Write-Host "✅ ngrok added to User PATH permanently" -ForegroundColor Green
}

# 4. Check for auth token
$configFile = "$env:USERPROFILE\.config\ngrok\ngrok.yml"
$hasToken = (Test-Path $configFile) -and ((Get-Content $configFile -Raw) -match "authtoken")

if (-not $hasToken) {
    Write-Host ""
    Write-Host "⚠️  ngrok needs an auth token (free account required)" -ForegroundColor Yellow
    Write-Host "   1. Sign up at: https://dashboard.ngrok.com/signup" -ForegroundColor Cyan
    Write-Host "   2. Get token:  https://dashboard.ngrok.com/get-started/your-authtoken" -ForegroundColor Cyan
    Write-Host ""
    $token = Read-Host "Paste your ngrok auth token here"
    & $ngrokExe config add-authtoken $token
    Write-Host "✅ Auth token saved" -ForegroundColor Green
}

# 5. Start ngrok in background
Write-Host ""
Write-Host "🚀 Starting ngrok tunnel on port 8000..." -ForegroundColor Cyan
$ngrokJob = Start-Job -ScriptBlock { param($exe) & $exe http 8000 } -ArgumentList $ngrokExe

# 6. Wait for tunnel to be ready
Write-Host "⏳ Waiting for tunnel..." -ForegroundColor Yellow
$publicUrl = $null
for ($i = 0; $i -lt 15; $i++) {
    Start-Sleep -Seconds 2
    try {
        $tunnels = (Invoke-RestMethod "http://localhost:4040/api/tunnels" -TimeoutSec 3).tunnels
        $httpsTunnel = $tunnels | Where-Object { $_.proto -eq "https" } | Select-Object -First 1
        if ($httpsTunnel) {
            $publicUrl = $httpsTunnel.public_url
            break
        }
    }
    catch { }
}

if ($publicUrl) {
    Write-Host ""
    Write-Host "✅ ngrok tunnel active!" -ForegroundColor Green
    Write-Host "   Public URL: $publicUrl" -ForegroundColor Cyan
    Write-Host ""

    # 7. Auto-update .env
    $envFile = "$PSScriptRoot\backend\.env"
    if (Test-Path $envFile) {
        $content = Get-Content $envFile -Raw
        if ($content -match "PUBLIC_URL=.*") {
            $content = $content -replace "PUBLIC_URL=.*", "PUBLIC_URL=$publicUrl"
        }
        else {
            $content += "`nPUBLIC_URL=$publicUrl"
        }
        Set-Content $envFile $content -NoNewline
        Write-Host "✅ Updated backend\.env with PUBLIC_URL=$publicUrl" -ForegroundColor Green
    }

    Write-Host ""
    Write-Host "═══════════════════════════════════════════════════" -ForegroundColor DarkGray
    Write-Host " ✅ All set! Now restart the backend to apply .env" -ForegroundColor White
    Write-Host "    cd backend && .\venv\Scripts\activate && python main.py" -ForegroundColor DarkGray
    Write-Host "═══════════════════════════════════════════════════" -ForegroundColor DarkGray
    Write-Host ""
    Write-Host "Press Ctrl+C to stop ngrok" -ForegroundColor DarkGray

    # Keep alive
    Wait-Job $ngrokJob
}
else {
    Write-Host "❌ Could not get ngrok public URL. Check ngrok window for errors." -ForegroundColor Red
    Write-Host "   Make sure your auth token is correct at: https://dashboard.ngrok.com" -ForegroundColor Yellow
    Remove-Job $ngrokJob -Force
}
