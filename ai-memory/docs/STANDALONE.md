# 独立运行指南（Windows / Mac，无需 Cursor）

本系统可完全脱离 Cursor IDE，在任意 Windows 或 Mac 电脑上独立运行。

---

## 你需要准备什么

| 依赖 | 版本 | 用途 |
|------|------|------|
| **方案 A：Docker Desktop** | 最新版 | **推荐**，一键启动全部服务 |
| **方案 B：Python** | 3.11+ | 后端 API |
| **方案 B：Node.js** | 18+ | 前端界面 |
| **方案 B：PostgreSQL** | 16 | 数据库 |
| **方案 B：Redis** | 7 | 任务队列（可选，定时任务用） |

> 整个 `ai-memory` 文件夹可以复制到 U 盘、网盘或另一台电脑使用。

---

## 方案 A：Docker（推荐，Win / Mac 通用）

**优点**：不用单独装数据库，Windows 和 Mac 操作完全一样。

### 1. 安装 Docker Desktop

- Mac：https://docs.docker.com/desktop/setup/install/mac-install/
- Windows：https://docs.docker.com/desktop/setup/install/windows-install/
  - Windows 需开启 WSL2（安装程序会提示）

### 2. 首次配置

```bash
cd ai-memory
cp .env.example .env    # Windows: copy .env.example .env
```

编辑 `.env`，填入 DeepSeek 密钥：

```env
OPENAI_API_KEY=sk-你的密钥
OPENAI_BASE_URL=https://api.deepseek.com/v1
OPENAI_MODEL=deepseek-chat
```

### 3. 启动

```bash
docker compose up --build
```

**国内拉镜像失败？** 见 [DOCKER-MIRROR.md](DOCKER-MIRROR.md)，或：

```bash
# 使用国内镜像源
docker compose -f docker-compose.yml -f docker-compose.cn.yml up --build
```

Windows 可双击 **`docker-up-cn.bat`**。

首次启动约 3–5 分钟（下载镜像 + 构建）。

### 4. 访问

| 地址 | 说明 |
|------|------|
| http://localhost:3000 | 前端界面 |
| http://localhost:8000/docs | API 文档 |

### 5. 停止

```bash
docker compose down
```

### 6. 后台运行

```bash
docker compose up -d --build
```

---

## 方案 B：本地运行（不用 Docker）

### Mac

**首次安装（只需一次）：**

```bash
cd ai-memory
chmod +x setup.sh start.sh scripts/*.sh
./setup.sh
```

或双击 `setup.sh`（需在终端中运行）。

**每次启动：**

```bash
./start.sh
```

或双击 **`启动 AI Memory.command`**（Mac 右键 → 打开，首次需允许）。

访问：http://localhost:5173

**停止：**

```bash
./scripts/stop.sh
```

**数据库（Mac 首次）：**

```bash
brew install postgresql@16 redis
brew services start postgresql@16
brew services start redis

# 创建数据库用户
export PATH="/opt/homebrew/opt/postgresql@16/bin:$PATH"
psql postgres -c "CREATE USER aimemory WITH PASSWORD 'aimemory' CREATEDB;" 2>/dev/null || true
psql postgres -c "CREATE DATABASE aimemory OWNER aimemory;" 2>/dev/null || true
```

---

### Windows

**首次安装（只需一次）：**

双击 **`setup.bat`**

或在 PowerShell 中：

```powershell
cd ai-memory
.\scripts\setup.ps1
```

**每次启动：**

双击 **`start.bat`**

访问：http://localhost:5173

**停止：**

双击运行 `scripts\stop.ps1`，或在 PowerShell：

```powershell
.\scripts\stop.ps1
```

**数据库（Windows 首次，不用 Docker 时）：**

1. 安装 [PostgreSQL 16](https://www.postgresql.org/download/windows/)
2. 安装时记住 postgres 用户密码
3. 用 pgAdmin 或 psql 执行：

```sql
CREATE USER aimemory WITH PASSWORD 'aimemory' CREATEDB;
CREATE DATABASE aimemory OWNER aimemory;
```

4. 确认 `.env` 中：

```env
DATABASE_URL=postgresql+asyncpg://aimemory:aimemory@localhost:5432/aimemory
```

5. （可选）安装 [Redis for Windows](https://github.com/microsoftarchive/redis/releases) 或使用 Docker 只跑 Redis。

---

## 配置 DeepSeek

编辑 `ai-memory/.env`：

```env
OPENAI_API_KEY=sk-你的DeepSeek密钥
OPENAI_BASE_URL=https://api.deepseek.com/v1
OPENAI_MODEL=deepseek-chat
DNA_TAGGING_ENABLED=true
```

密钥获取：https://platform.deepseek.com/

不配置也能用，AI 功能会降级为规则引擎。

---

## 复制到其他电脑

1. 复制整个 `ai-memory` 文件夹
2. **不要复制** `node_modules/`、`backend/.venv/`、`frontend/dist/`（体积大，到新电脑重新 setup）
3. **可以复制** `.env`（含你的 API Key）
4. 到新电脑后：
   - Docker 方案：直接 `docker compose up --build`
   - 本地方案：重新运行 `setup.bat` 或 `./setup.sh`

---

## 日常使用流程

1. 启动系统（`start.bat` / `./start.sh` / `docker compose up`）
2. 打开浏览器 → 数据导入 → 上传历史视频 CSV
3. 触发学习（首次）：

**Docker：**

```bash
docker compose exec backend python -c "
import asyncio
from app.database import async_session_factory
from app.services.brain_learner import run_learning_for_account
async def main():
    async with async_session_factory() as s:
        await run_learning_for_account(s, 1)
        await s.commit()
asyncio.run(main())
"
```

**本地 Mac/Linux：**

```bash
cd backend && source ../.env && .venv/bin/python -c "
import asyncio
from app.database import async_session_factory
from app.services.brain_learner import run_learning_for_account
async def main():
    async with async_session_factory() as s:
        await run_learning_for_account(s, 1)
        await s.commit()
asyncio.run(main())
"
```

**本地 Windows（PowerShell）：**

```powershell
cd backend
.\.venv\Scripts\python.exe -c @"
import asyncio
from app.database import async_session_factory
from app.services.brain_learner import run_learning_for_account
async def main():
    async with async_session_factory() as s:
        await run_learning_for_account(s, 1)
        await s.commit()
asyncio.run(main())
"@
```

4. 查看账号画像 → 决策中心 → 预测拦截 → 日常使用

详细功能说明见 [USAGE.md](USAGE.md)。

---

## 常见问题

### Mac 提示「无法打开，因为来自身份不明的开发者」

右键 `启动 AI Memory.command` → **打开** → 确认打开。

### Windows 提示「无法加载，因为在此系统上禁止运行脚本」

以管理员打开 PowerShell，执行：

```powershell
Set-ExecutionPolicy -Scope CurrentUser RemoteSigned
```

或直接双击 `start.bat`（已绕过策略）。

### 端口被占用

修改端口：
- 后端：启动时加 `--port 8001`
- 前端：在 `frontend/vite.config.ts` 中改 `server.port`

### 换电脑后数据库为空

数据存在 PostgreSQL 中。换电脑需：
- Docker：数据在 `postgres_data` 卷，需备份 `docker compose exec postgres pg_dump ...`
- 本地：备份 PostgreSQL 数据库

---

## 文件速查

| 文件 | 平台 | 作用 |
|------|------|------|
| `setup.bat` / `setup.sh` | Win / Mac | 首次安装 |
| `start.bat` / `start.sh` | Win / Mac | 启动服务 |
| `启动 AI Memory.command` | Mac | 双击启动 |
| `docker compose up` | Win / Mac | Docker 启动 |
| `docker-up-cn.bat` | Windows | Docker 启动（国内镜像） |
| `.env` | 通用 | API 密钥与数据库配置 |
| `docs/DOCKER-MIRROR.md` | 通用 | Docker 镜像拉取失败 |
| `docs/USAGE.md` | 通用 | 功能使用教程 |
