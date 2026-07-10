# 启动 AI Memory（Windows，无需 Docker）
$ErrorActionPreference = "Stop"
$Root = Split-Path -Parent (Split-Path -Parent $MyInvocation.MyCommand.Path)
Set-Location $Root

if (-not (Test-Path ".env")) {
    Write-Host "❌ 未找到 .env，请先运行: .\scripts\setup.ps1" -ForegroundColor Red
    Read-Host "按 Enter 退出"
    exit 1
}

if (-not (Test-Path "backend\.venv\Scripts\python.exe")) {
    Write-Host "❌ 未安装依赖，请先运行: .\scripts\setup.ps1" -ForegroundColor Red
    Read-Host "按 Enter 退出"
    exit 1
}

# 加载 .env 到进程环境
Get-Content ".env" | ForEach-Object {
    $line = $_.Trim()
    if ($line -eq "" -or $line.StartsWith("#")) { return }
    $idx = $line.IndexOf("=")
    if ($idx -lt 1) { return }
    $key = $line.Substring(0, $idx).Trim()
    $val = $line.Substring($idx + 1).Trim().Trim('"')
    [Environment]::SetEnvironmentVariable($key, $val, "Process")
}

$Python = "$Root\backend\.venv\Scripts\python.exe"
$Alembic = "$Root\backend\.venv\Scripts\alembic.exe"
$Uvicorn = "$Root\backend\.venv\Scripts\uvicorn.exe"

# 检查数据库
Write-Host "==> 检查数据库连接..."
$dbCheck = & $Python -c @"
import asyncio, os, sys
from sqlalchemy.ext.asyncio import create_async_engine
from sqlalchemy import text
async def check():
    url = os.environ.get('DATABASE_URL', '')
    e = create_async_engine(url, pool_pre_ping=True)
    async with e.connect() as c:
        await c.execute(text('SELECT 1'))
    await e.dispose()
asyncio.run(check())
"@ 2>&1

if ($LASTEXITCODE -ne 0) {
    Write-Host "❌ 无法连接数据库。请选择：" -ForegroundColor Red
    Write-Host "   1) 安装 Docker Desktop 后运行: docker compose up --build"
    Write-Host "   2) 安装 PostgreSQL 16 + Redis（见 docs/STANDALONE.md）"
    Write-Host "   3) 确认 .env 中 DATABASE_URL 正确"
    Read-Host "按 Enter 退出"
    exit 1
}

Write-Host "==> 数据库迁移..."
Set-Location "$Root\backend"
& $Alembic upgrade head

Write-Host "==> 启动后端 http://localhost:8000"
$backendJob = Start-Process -FilePath $Uvicorn -ArgumentList "app.main:app","--host","0.0.0.0","--port","8000","--reload" -WorkingDirectory "$Root\backend" -PassThru -WindowStyle Minimized

Write-Host "==> 启动前端 http://localhost:5173"
Set-Location "$Root\frontend"
$frontendJob = Start-Process -FilePath "npm" -ArgumentList "run","dev","--","--host","0.0.0.0" -WorkingDirectory "$Root\frontend" -PassThru -WindowStyle Minimized

Start-Sleep -Seconds 3
Start-Process "http://localhost:5173" | Out-Null

Write-Host ""
Write-Host "==========================================" -ForegroundColor Green
Write-Host "  ✅ AI Memory 已启动" -ForegroundColor Green
Write-Host "==========================================" -ForegroundColor Green
Write-Host "  前端:  http://localhost:5173"
Write-Host "  API:   http://localhost:8000/docs"
Write-Host ""
Write-Host "  关闭此窗口不会停止服务。"
Write-Host "  停止方式：任务管理器结束 python.exe 和 node.exe"
Write-Host "  或运行: .\scripts\stop.ps1"
Write-Host "=========================================="
Write-Host ""
Read-Host "按 Enter 退出此窗口（服务继续运行）"
