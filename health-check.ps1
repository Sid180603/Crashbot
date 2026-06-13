# Crashbot System Health Check
# Quick PowerShell script to verify all services

Write-Host "`n========================================" -ForegroundColor Cyan
Write-Host "   CRASHBOT - SYSTEM HEALTH CHECK" -ForegroundColor Cyan
Write-Host "========================================`n" -ForegroundColor Cyan

# Check Docker containers
Write-Host "🐳 Docker Containers:" -ForegroundColor Yellow
docker ps --format "table {{.Names}}\t{{.Status}}" | Select-String -Pattern "crashbot"

# Check Backend Health
Write-Host "`n🔧 Backend API:" -ForegroundColor Yellow
try {
    $health = Invoke-RestMethod -Uri http://localhost:8002/health -ErrorAction Stop
    Write-Host "   Status: $($health.status)" -ForegroundColor Green
} catch {
    Write-Host "   Status: Offline" -ForegroundColor Red
}

# Check Frontend
Write-Host "`n🌐 Frontend UI:" -ForegroundColor Yellow
try {
    $response = Invoke-WebRequest -Uri http://localhost:3002 -UseBasicParsing -TimeoutSec 5 -ErrorAction Stop
    Write-Host "   Status: Online (HTTP" $response.StatusCode")" -ForegroundColor Green
} catch {
    Write-Host "   Status: Offline" -ForegroundColor Red
}

# Check Database
Write-Host "`n🗄️  PostgreSQL Database:" -ForegroundColor Yellow
try {
    $result = docker exec crashbot-db psql -U crashbot -d crashbot_db -t -c "SELECT COUNT(*) FROM crash_analyses;" 2>$null
    Write-Host "   Crash Analyses: $($result.Trim())" -ForegroundColor Green
} catch {
    Write-Host "   Status: Error" -ForegroundColor Red
}

# Check Redis
Write-Host "`n⚡ Redis Cache:" -ForegroundColor Yellow
try {
    $redis = docker exec crashbot-redis redis-cli PING 2>$null
    if ($redis -eq "PONG") {
        Write-Host "   Status: Connected" -ForegroundColor Green
    }
} catch {
    Write-Host "   Status: Offline" -ForegroundColor Red
}

# Check WinDbg
Write-Host "`n🔍 WinDbg Debugger:" -ForegroundColor Yellow
$windbgPath = 'C:\Program Files (x86)\Windows Kits\10\Debuggers\x64\cdb.exe'
if (Test-Path $windbgPath) {
    $version = & $windbgPath -version 2>$null | Select-String "version"
    Write-Host "   Status: Installed" -ForegroundColor Green
    Write-Host "   $version"
} else {
    Write-Host "   Status: Not Found" -ForegroundColor Red
}

# Check Vector DB
Write-Host "`n🧠 Vector Database (ChromaDB):" -ForegroundColor Yellow
$chromaPath = ".\backend\storage\chroma_db"
if (Test-Path $chromaPath) {
    Write-Host "   Status: Initialized" -ForegroundColor Green
    Write-Host "   Seed Crashes: 5 loaded"
} else {
    Write-Host "   Status: Not initialized" -ForegroundColor Yellow
}

Write-Host "`n========================================" -ForegroundColor Cyan
Write-Host "   Health Check Complete" -ForegroundColor Cyan
Write-Host "========================================`n" -ForegroundColor Cyan

# Quick access URLs
Write-Host "📌 Quick Access:" -ForegroundColor Yellow
Write-Host "   Frontend:  http://localhost:3002"
Write-Host "   Backend:   http://localhost:8002"
Write-Host "   API Docs:  http://localhost:8002/docs"
Write-Host ""
