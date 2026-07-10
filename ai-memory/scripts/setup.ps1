# 首次安装（Windows）
$ErrorActionPreference = "Stop"
$Root = Split-Path -Parent (Split-Path -Parent $MyInvocation.MyCommand.Path)
Set-Location $Root

Write-Host "==========================================" -ForegroundColor Cyan
Write-Host "  AI Memory 首次安装 (Windows)" -ForegroundColor Cyan
Write-Host "==========================================" -ForegroundColor Cyan

function Test-Command($name) {
    return [bool](Get-Command $name -ErrorAction SilentlyContinue)
}

$missing = @()
if (-not (Test-Command python)) { $missing += "Python 3.11+  → https://www.python.org/downloads/ （勾选 Add to PATH）" }
if (-not (Test-Command node))    { $missing += "Node.js 18+  → https://nodejs.org/" }

if ($missing.Count -gt 0) {
    Write-Host "❌ 缺少以下依赖，请先安装：" -ForegroundColor Red
    $missing | ForEach-Object { Write-Host "   $_" }
    exit 1
}

Write-Host "✓ Python $(python --version)"
Write-Host "✓ Node $(node --version)"

# 环境变量
if (-not (Test-Path ".env")) {
    Copy-Item ".env.example" ".env"
    Write-Host "✓ 已创建 .env（请编辑填入 DeepSeek API Key）"
} else {
    Write-Host "✓ .env 已存在"
}

# Python 虚拟环境
Write-Host "==> 安装 Python 依赖..."
Set-Location "$Root\backend"
python -m venv .venv
& ".\.venv\Scripts\pip.exe" install -q --upgrade pip
& ".\.venv\Scripts\pip.exe" install -q -r requirements.txt
Set-Location $Root

# 前端依赖
Write-Host "==> 安装前端依赖..."
Set-Location "$Root\frontend"
npm install --silent
Set-Location $Root

# 数据库提示
if (-not (Test-Command psql)) {
    Write-Host ""
    Write-Host "⚠️  未检测到 PostgreSQL。" -ForegroundColor Yellow
    Write-Host "   推荐方案：安装 Docker Desktop，然后运行 docker compose up --build"
    Write-Host "   本地方案：安装 PostgreSQL 16 + Redis，并创建数据库 aimemory"
    Write-Host "   下载：https://www.postgresql.org/download/windows/"
    Write-Host ""
}

Write-Host ""
Write-Host "==========================================" -ForegroundColor Green
Write-Host "  ✅ 安装完成" -ForegroundColor Green
Write-Host "==========================================" -ForegroundColor Green
Write-Host ""
Write-Host "下一步："
Write-Host "  1. 编辑 .env，填入 OPENAI_API_KEY（DeepSeek 密钥）"
Write-Host "  2. 启动系统："
Write-Host "       双击 start.bat          （Windows 本地）"
Write-Host "       docker compose up       （需 Docker Desktop）"
Write-Host ""
