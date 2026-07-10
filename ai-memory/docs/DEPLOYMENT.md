# 部署说明

## 环境要求

- Docker 20.10+
- Docker Compose v2
- （可选）OpenAI 兼容 API Key，用于 DNA 打标、学习报告、预测理由等 LLM 能力

## 快速启动

```bash
cd ai-memory
docker compose up --build
```

服务地址：

| 服务 | 地址 |
|------|------|
| 后端 API | http://localhost:8000 |
| OpenAPI 文档 | http://localhost:8000/docs |
| 健康检查 | http://localhost:8000/health |
| 前端 | http://localhost:3000 |
| PostgreSQL | localhost:5432（用户/库：`aimemory`） |
| Redis | localhost:6379 |

启动时后端会自动执行 `alembic upgrade head`。

## 环境变量

在 `docker-compose.yml` 的 `backend.environment` 中配置，或创建 `backend/.env`：

| 变量 | 默认值 | 说明 |
|------|--------|------|
| `DATABASE_URL` | `postgresql+asyncpg://aimemory:aimemory@postgres:5432/aimemory` | 数据库连接 |
| `REDIS_URL` | `redis://redis:6379/0` | Celery broker |
| `OPENAI_API_KEY` | （空） | LLM API Key；未配置时使用规则引擎 |
| `OPENAI_BASE_URL` | `https://api.openai.com/v1` | 兼容 API 地址 |
| `OPENAI_MODEL` | `gpt-4o-mini` | 模型名称 |
| `DNA_TAG_USE_CELERY` | `false` | 是否通过 Celery 异步打标 |
| `LOG_LEVEL` | `INFO` | 日志级别 |

## Celery 定时任务（生产环境）

`docker-compose.yml` 默认仅启动 API。生产环境建议额外启动 worker 与 beat：

```bash
# Worker
docker compose exec backend celery -A app.workers.celery_app worker -l info

# Beat（定时任务）
docker compose exec backend celery -A app.workers.celery_app beat -l info
```

已注册的 Beat 任务：

| 任务 | 调度 | 说明 |
|------|------|------|
| `process_due_performance_syncs` | 每 15 分钟 | T+1h/24h/7d 表现同步 |
| `run_daily_brain_learning` | 每天 02:00（上海时区） | 全账号 Brain Learning |
| `run_prompt_evolution` | 每天 02:30 | Prompt 进化检查 |

## 本地开发（无 Docker）

```bash
cd backend
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt

# 需本地 PostgreSQL + Redis，或修改 DATABASE_URL 为 sqlite（仅测试）
export DATABASE_URL=postgresql+asyncpg://aimemory:aimemory@localhost:5432/aimemory
alembic upgrade head
uvicorn app.main:app --reload --port 8000
```

前端：

```bash
cd frontend
npm install
npm run dev
```

## 内容生成管线集成

外部内容系统发布时调用：

```
POST /accounts/{account_id}/pipeline/publish
```

该接口会依次：写入 Video Memory → 调度表现同步 → Content DNA 打标 → 绑定活跃 Prompt 版本。

可选参数 `require_prediction_pass=true` 在发布前执行预测拦截。

## 验收测试

```bash
cd backend
source .venv/bin/activate
pytest tests/test_e2e_acceptance.py -v          # 11 项验收清单
pytest tests/test_learning_performance.py -m performance -v  # 500 条性能
pytest tests/ -q                                 # 全量回归
```

## 数据备份

PostgreSQL 数据卷：`postgres_data`。备份示例：

```bash
docker compose exec postgres pg_dump -U aimemory aimemory > backup.sql
```
