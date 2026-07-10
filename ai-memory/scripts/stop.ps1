# 停止 AI Memory 服务（Windows）
Get-Process -Name "uvicorn" -ErrorAction SilentlyContinue | Stop-Process -Force
Get-Process -Name "node" -ErrorAction SilentlyContinue | Where-Object {
    $_.Path -like "*ai-memory*"
} | Stop-Process -Force -ErrorAction SilentlyContinue

# 通过端口停止
foreach ($port in @(8000, 5173)) {
    $conn = Get-NetTCPConnection -LocalPort $port -ErrorAction SilentlyContinue |
        Select-Object -First 1
    if ($conn) {
        Stop-Process -Id $conn.OwningProcess -Force -ErrorAction SilentlyContinue
    }
}

Write-Host "✅ 已尝试停止 AI Memory 服务（端口 8000 / 5173）"
