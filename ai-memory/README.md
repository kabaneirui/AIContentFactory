# AI Memory

个人账号内容大脑 — 为每个视频号/短视频账号建立独立 AI Memory，实现「发布 → 记录 → 打标 → 学习 → 预测 → 决策 → 进化」完整闭环。

## 功能概览

| 模块 | 能力 |
|------|------|
| Content Memory | 视频全生命周期记录与表现同步 |
| Content DNA | 8 维 AI 自动标签 |
| Brain Learning | 每日统计学习 + 账号报告 |
| Account Profile | 最佳栏目/画面/时长/发布时间画像 |
| Prediction Engine | 发布前播放预测与低分拦截 |
| Knowledge Evolution | 爆款/失败经验库 |
| Decision Center | 「今天发什么」70% 账号经验 + 30% 热点 |
| Prompt Evolution | Prompt 版本追踪与半自动进化 |

## 快速开始（脱离 Cursor，Win / Mac 通用）

> 完整独立运行指南：**[docs/STANDALONE.md](docs/STANDALONE.md)**

### 方式一：Docker（推荐）

```bash
cd ai-memory
cp .env.example .env          # 编辑填入 DeepSeek API Key
docker compose up --build
```

- 前端：http://localhost:3000
- API：http://localhost:8000/docs

### 方式二：本地脚本

| 平台 | 首次安装 | 每次启动 |
|------|----------|----------|
| **Mac** | `./setup.sh` | `./start.sh` 或双击 `启动 AI Memory.command` |
| **Windows** | 双击 `setup.bat` | 双击 `start.bat` |

- 前端：http://localhost:5173
- API：http://localhost:8000/docs

详细部署见 [docs/DEPLOYMENT.md](docs/DEPLOYMENT.md)。  
**使用指南**（含 DeepSeek 配置）：[docs/USAGE.md](docs/USAGE.md)

## 目录结构

```
ai-memory/
├── backend/          # FastAPI + SQLAlchemy + Celery
├── frontend/         # React + Vite
├── docs/             # 部署、导入模板
└── docker-compose.yml
```

## 核心 API

| 端点 | 说明 |
|------|------|
| `POST /accounts` | 创建账号（自动初始化 Prompt V1） |
| `POST /accounts/{id}/pipeline/publish` | **内容生成管线发布钩子** |
| `POST /accounts/{id}/videos/import` | 批量导入历史视频 |
| `POST /accounts/{id}/predict` | 发布前预测 |
| `POST /accounts/{id}/decide/today` | 今日创作建议 |
| `GET /accounts/{id}/profile` | 账号画像 |
| `GET /accounts/{id}/learning/latest` | 最新学习报告 |

历史视频 CSV 导入字段说明：[docs/IMPORT.md](docs/IMPORT.md)

## 验收清单

Phase 11 端到端验收由 `backend/tests/test_e2e_acceptance.py` 覆盖全部 11 项：

1. 每账号独立 AI Memory，数据隔离
2. 视频发布自动记录 + 表现持续更新
3. 8 维 Content DNA 自动打标
4. 每日自动学习 + 报告
5. 发布前预测 + 低分拦截
6. 失败归因 + 策略调整建议
7. 账号画像 API
8. 爆款/失败经验库可检索
9. 「今天发什么」综合决策（70/30）
10. Prompt 版本追踪与进化
11. 完整数据流闭环

运行验收：

```bash
cd backend && source .venv/bin/activate
pytest tests/test_e2e_acceptance.py -v
pytest tests/test_learning_performance.py -m performance -v
```

## 技术栈

- **后端**：FastAPI、SQLAlchemy 2.0、Alembic、Celery、PostgreSQL、Redis
- **前端**：React、Vite、TypeScript
- **AI**：OpenAI 兼容 API（可配置；未配置时规则引擎兜底）

## 相关文档

- **独立运行（Win/Mac）**：[docs/STANDALONE.md](docs/STANDALONE.md)
- 产品设计：[AI-Memory-开发文档.md](../AI-Memory-开发文档.md)
- 部署：[docs/DEPLOYMENT.md](docs/DEPLOYMENT.md)
- 使用教程：[docs/USAGE.md](docs/USAGE.md)
- 数据导入：[docs/IMPORT.md](docs/IMPORT.md)
