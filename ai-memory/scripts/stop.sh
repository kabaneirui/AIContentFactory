#!/usr/bin/env bash
# 停止 AI Memory 服务（Mac / Linux）
for port in 8000 5173; do
  pid=$(lsof -ti :"$port" 2>/dev/null || true)
  if [[ -n "$pid" ]]; then
    kill $pid 2>/dev/null && echo "已停止端口 $port 的进程 (PID $pid)"
  fi
done
echo "✅ 完成"
