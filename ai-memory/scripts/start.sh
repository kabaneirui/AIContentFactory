#!/usr/bin/env bash
# 启动 AI Memory（Mac / Linux，无需 Docker）
set -euo pipefail

ROOT="$(cd "$(dirname "$0")/.." && pwd)"
cd "$ROOT"

# 补充常见 PostgreSQL 路径
for p in \
  /opt/homebrew/opt/postgresql@16/bin \
  /usr/local/opt/postgresql@16/bin \
  /opt/homebrew/bin \
  /usr/local/bin; do
  [[ -d "$p" ]] && PATH="$p:$PATH"
done
export PATH

if [[ ! -f .env ]]; then
  echo "❌ 未找到 .env，请先运行: ./scripts/setup.sh"
  exit 1
fi

if [[ ! -d backend/.venv ]]; then
  echo "❌ 未安装依赖，请先运行: ./scripts/setup.sh"
  exit 1
fi

# 尝试启动数据库服务（Homebrew）
if command -v brew >/dev/null 2>&1; then
  brew services start postgresql@16 2>/dev/null || true
  brew services start redis 2>/dev/null || true
  sleep 1
fi

# 加载 .env
set -a
# shellcheck source=/dev/null
source "$ROOT/.env"
set +a

# 检查数据库连接
if ! backend/.venv/bin/python -c "
import asyncio, sys
from sqlalchemy.ext.asyncio import create_async_engine
from sqlalchemy import text
async def check():
    e = create_async_engine('$DATABASE_URL', pool_pre_ping=True)
    async with e.connect() as c:
        await c.execute(text('SELECT 1'))
    await e.dispose()
asyncio.run(check())
" 2>/dev/null; then
  echo "❌ 无法连接数据库。请选择："
  echo "   1) 安装 Docker Desktop 后运行: docker compose up --build"
  echo "   2) Mac 安装数据库: brew install postgresql@16 redis"
  echo "   3) 确认 .env 中 DATABASE_URL 正确"
  exit 1
fi

echo "==> 数据库迁移..."
cd "$ROOT/backend"
.venv/bin/alembic upgrade head

cleanup() {
  echo ""
  echo "正在停止服务..."
  kill "$BACKEND_PID" "$FRONTEND_PID" 2>/dev/null || true
  wait "$BACKEND_PID" "$FRONTEND_PID" 2>/dev/null || true
  echo "已停止。"
}
trap cleanup EXIT INT TERM

echo "==> 启动后端 http://localhost:8000"
.venv/bin/uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload &
BACKEND_PID=$!

echo "==> 启动前端 http://localhost:5173"
cd "$ROOT/frontend"
npm run dev -- --host 0.0.0.0 &
FRONTEND_PID=$!

sleep 2
echo ""
echo "=========================================="
echo "  ✅ AI Memory 已启动"
echo "=========================================="
echo "  前端:  http://localhost:5173"
echo "  API:   http://localhost:8000/docs"
echo "  按 Ctrl+C 停止"
echo "=========================================="
echo ""

# Mac 自动打开浏览器
if [[ "$(uname)" == "Darwin" ]] && command -v open >/dev/null; then
  open "http://localhost:5173" 2>/dev/null || true
fi

wait
