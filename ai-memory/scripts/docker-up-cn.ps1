# Windows：预拉国内镜像后启动 Docker
$ErrorActionPreference = "Stop"
$Root = Split-Path -Parent (Split-Path -Parent $MyInvocation.MyCommand.Path)
Set-Location $Root

$Mirror = "docker.m.daocloud.io/library"
$images = @(
    "$Mirror/postgres:16-alpine",
    "$Mirror/redis:7-alpine",
    "$Mirror/python:3.12-slim",
    "$Mirror/node:22-alpine",
    "$Mirror/nginx:alpine"
)

Write-Host "==> 从国内镜像源拉取基础镜像..."
foreach ($img in $images) {
    Write-Host "    pulling $img"
    docker pull $img
    if ($LASTEXITCODE -ne 0) {
        Write-Host ""
        Write-Host "❌ 拉取失败: $img" -ForegroundColor Red
        Write-Host ""
        Write-Host "可选方案：" -ForegroundColor Yellow
        Write-Host "  1. Docker Desktop → Settings → Docker Engine 配置 registry-mirrors"
        Write-Host "  2. 换手机热点后重试"
        Write-Host "  3. 不用 Docker，运行 setup.bat + start.bat"
        Write-Host "  详见 docs/DOCKER-MIRROR.md"
        exit 1
    }
}

Write-Host ""
Write-Host "==> 启动服务（使用 docker-compose.cn.yml）..."
docker compose -f docker-compose.yml -f docker-compose.cn.yml up --build
