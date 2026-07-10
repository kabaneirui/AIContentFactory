#!/usr/bin/env bash
# 首次安装（Mac / Linux）
set -euo pipefail

ROOT="$(cd "$(dirname "$0")/.." && pwd)"
cd "$ROOT"

echo "=========================================="
echo "  AI Memory 首次安装 (Mac / Linux)"
echo "=========================================="

# --- 检查依赖 ---
missing=()
command -v python3 >/dev/null || missing+=("Python 3.11+  → https://www.python.org/downloads/")
command -v node    >/dev/null || missing+=("Node.js 18+  → https://nodejs.org/")
command -v npm     >/dev/null || missing+=("npm（随 Node.js 安装）")

if [[ ${#missing[@]} -gt 0 ]]; then
  echo "❌ 缺少以下依赖，请先安装："
  printf '   %s\n' "${missing[@]}"
  exit 1
fi

PY_VER=$(python3 -c 'import sys; print(f"{sys.version_info.major}.{sys.version_info.minor}")')
echo "✓ Python $PY_VER"
echo "✓ Node $(node --version)"

# --- 环境变量 ---
if [[ ! -f .env ]]; then
  cp .env.example .env
  echo "✓ 已创建 .env（请编辑填入 DeepSeek API Key）"
else
  echo "✓ .env 已存在"
fi

# --- Python 虚拟环境 ---
echo "==> 安装 Python 依赖..."
cd backend
python3 -m venv .venv
.venv/bin/pip install -q --upgrade pip
.venv/bin/pip install -q -r requirements.txt
cd ..

# --- 前端依赖 ---
echo "==> 安装前端依赖..."
cd frontend
npm install --silent
cd ..

# --- 数据库（可选：Homebrew）---
if ! command -v psql >/dev/null 2>&1; then
  echo ""
  echo "⚠️  未检测到 PostgreSQL。"
  echo "   推荐方案：安装 Docker Desktop，然后运行 docker compose up --build"
  echo "   本地方案：Mac 执行 brew install postgresql@16 redis"
  echo ""
else
  echo "✓ PostgreSQL 已安装"
  if command -v brew >/dev/null 2>&1; then
    brew services start postgresql@16 2>/dev/null || true
    brew services start redis 2>/dev/null || true
  fi
fi

echo ""
echo "=========================================="
echo "  ✅ 安装完成"
echo "=========================================="
echo ""
echo "下一步："
echo "  1. 编辑 .env，填入 OPENAI_API_KEY（DeepSeek 密钥）"
echo "  2. 启动系统："
echo "       ./start.sh          （Mac / Linux 本地）"
echo "       docker compose up   （需 Docker Desktop）"
echo ""
