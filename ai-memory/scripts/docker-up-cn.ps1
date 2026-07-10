# Windows：预拉国内镜像后启动 Docker
$ErrorActionPreference = "Stop"
$Root = Split-Path -Parent (Split-Path -Parent $MyInvocation.MyCommand.Path)
Set-Location $Root

$images = @(
    "docker.m.daocloud.io/library/postgres:16-alpine",
    "docker.m.daocloud.io/library/redis:7-alpine"
)

Write-Host "==> 从国内镜像源拉取基础镜像..."
foreach ($img in $images) {
    Write-Host "    pulling $img"
    docker pull $img
    if ($LASTEXITCODE -ne 0) {
        Write-Host "❌ 拉取失败: $img" -ForegroundColor Red
        Write-Host "请查看 docs/DOCKER-MIRROR.md 或使用 start.bat 本地启动"
        exit 1
    }
}

Write-Host "==> 启动服务..."
docker compose -f docker-compose.yml -f docker-compose.cn.yml up --build
