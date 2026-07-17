# AI Memory 使用指南

本文档说明如何从零开始使用 AI Memory，完成「导入历史 → 学习画像 → 今日决策 → 预测拦截 → 发布记录」的完整工作流。

---

## 一、启动系统

> **脱离 Cursor 独立运行？** 见 [STANDALONE.md](STANDALONE.md)（Windows / Mac 完整指南）

### 方式 A：Docker（推荐，Win / Mac 相同）

```bash
cd ai-memory

# 1. 复制并编辑环境变量（见下文 DeepSeek 配置）
cp .env.example .env          # Windows: copy .env.example .env

# 2. 启动全部服务（需先安装 Docker Desktop）
docker compose up --build
```

启动后访问：

| 地址 | 说明 |
|------|------|
| http://localhost:3000 | 前端界面 |
| http://localhost:8000/docs | API 交互文档（Swagger） |
| http://localhost:8000/health | 健康检查 |

### 方式 B：本地脚本（无需 Docker）

| 平台 | 首次安装 | 每次启动 |
|------|----------|----------|
| Mac | `./setup.sh` | `./start.sh` |
| Windows | 双击 `setup.bat` | 双击 `start.bat` |

访问 http://localhost:5173（本地开发端口）

### 方式 C：手动启动（开发者）

```bash
# 后端
cd backend
python3 -m venv .venv && source .venv/bin/activate   # Windows: .venv\Scripts\activate
pip install -r requirements.txt
cp ../.env.example .env   # 编辑后生效
alembic upgrade head
uvicorn app.main:app --reload --port 8000

# 前端（新终端）
cd frontend
npm install
npm run dev   # http://localhost:5173
```

---

## 二、配置 AI 模型（支持 DeepSeek）

系统使用 **OpenAI 兼容 API**，可接入 DeepSeek、OpenAI、通义、Moonshot 等任何兼容 `/chat/completions` 的服务。

### DeepSeek 配置（推荐）

在 `ai-memory/.env` 中写入：

```env
OPENAI_API_KEY=sk-你的DeepSeek密钥
OPENAI_BASE_URL=https://api.deepseek.com/v1
OPENAI_MODEL=deepseek-chat
DNA_TAGGING_ENABLED=true
```

| 变量 | DeepSeek 推荐值 | 说明 |
|------|----------------|------|
| `OPENAI_API_KEY` | 从 [DeepSeek 开放平台](https://platform.deepseek.com/) 获取 | API 密钥 |
| `OPENAI_BASE_URL` | `https://api.deepseek.com/v1` | 兼容端点 |
| `OPENAI_MODEL` | `deepseek-chat` | 通用对话，适合 DNA 打标、学习报告、预测理由 |
| `OPENAI_MODEL` | `deepseek-reasoner` | 推理更强，响应更慢，可按需切换 |

**Docker 用户**：编辑 `.env` 后，在 `docker-compose.yml` 的 `backend` 服务下添加：

```yaml
env_file:
  - .env
```

然后重启：`docker compose up -d --build backend`

### 不配置 API Key 时

系统仍可运行，但以下能力会降级为**规则引擎**：

- Content DNA 打标（根据标题/模板关键词推断）
- Brain Learning 报告（统计 + 规则文案）
- 预测理由生成

统计、画像、决策排序等**不依赖 LLM** 的功能正常工作。

---

## 三、典型工作流

```
┌─────────────┐    ┌─────────────┐    ┌─────────────┐    ┌─────────────┐
│ 1. 创建账号  │ → │ 2. 导入历史  │ → │ 3. 触发学习  │ → │ 4. 查看画像  │
└─────────────┘    └─────────────┘    └─────────────┘    └─────────────┘
                                              │
       ┌──────────────────────────────────────┘
       ▼
┌─────────────┐    ┌─────────────┐    ┌─────────────┐
│ 5. 今日决策  │ → │ 6. 预测拦截  │ → │ 7. 发布记录  │
└─────────────┘    └─────────────┘    └─────────────┘
```

### 步骤 1：创建账号

**前端（推荐）**：

1. 打开 http://localhost:3000（或本地开发 http://localhost:5173）
2. 左侧「当前账号」区域点击 **+ 创建**
3. 填写账号名称、选择平台（视频号 / 抖音 / 快手 / B站）
4. 保存后在下拉框中选择该账号

编辑/删除：同一区域点击 **编辑** 或 **删除**（可设置预测拦截阈值、Prompt 自动进化开关）。

**API（备选）**：

```bash
curl -X POST http://localhost:8000/accounts \
  -H "Content-Type: application/json" \
  -d '{"name": "养生口诀号", "platform": "wechat_channels"}'
```

返回 `id` 即账号 ID，系统会自动创建 Prompt V1。

---

### 步骤 2：导入历史视频

首次使用建议导入 **30 条以上**历史视频（越多越好，系统会自动选择 30/60/100 条样本窗口学习）。

#### 方式 A：前端导入页

1. 打开 http://localhost:3000/import
2. 选择当前账号
3. 上传 CSV 或粘贴 JSON

#### 方式 B：CSV 文件

模板见 [`import-template.csv`](import-template.csv)，字段说明见 [`IMPORT.md`](IMPORT.md)。

```bash
curl -X POST "http://localhost:8000/accounts/1/videos/import/csv" \
  -F "file=@docs/import-template.csv"
```

#### 方式 C：JSON 批量

```bash
curl -X POST http://localhost:8000/accounts/1/videos/import \
  -H "Content-Type: application/json" \
  -d '{
    "videos": [
      {
        "title": "老祖宗养阳口诀",
        "hook": "老祖宗",
        "template": "口诀",
        "knowledge_source": "黄帝内经",
        "scene_style": "古风",
        "cta": "收藏",
        "duration": 32,
        "publish_time": "2026-01-10T20:00:00+08:00",
        "views": 420,
        "finish_rate": 0.28
      }
    ]
  }'
```

导入后系统会**自动排队 DNA 打标**（有 DeepSeek Key 时用 AI，否则规则打标）。

手动补打标：

```bash
# 单条重打
curl -X POST http://localhost:8000/videos/1/retag

# 批量打标
curl -X POST http://localhost:8000/accounts/1/videos/batch-tag \
  -H "Content-Type: application/json" \
  -d '{}'
```

---

### 步骤 3：触发 Brain Learning

学习报告默认由 **Celery 每天凌晨 02:00** 自动生成。首次导入后需手动触发一次。

#### 手动触发（Docker）

```bash
docker compose exec backend python -c "
import asyncio
from app.database import async_session_factory
from app.services.brain_learner import run_learning_for_account

async def main():
    async with async_session_factory() as session:
        learning = await run_learning_for_account(session, 1)  # 1 = 账号 ID
        await session.commit()
        print(f'学习完成: sample_size={learning.sample_size}')

asyncio.run(main())
"
```

#### 启动定时任务（生产环境）

```bash
# Worker
docker compose exec -d backend celery -A app.workers.celery_app worker -l info

# Beat（含每日 02:00 学习、02:30 Prompt 进化、每 15 分钟表现同步）
docker compose exec -d backend celery -A app.workers.celery_app beat -l info
```

---

### 步骤 4：查看账号画像

**前端**：首页 http://localhost:3000/

展示最佳栏目、画面、时长、发布时间、Hook、CTA 等。

点击 **编辑锁定字段** 可勾选不希望被每日学习自动覆盖的画像项（如最佳发布时间、最佳 Hook 等）。

**API**：

```bash
curl http://localhost:8000/accounts/1/profile
curl http://localhost:8000/accounts/1/learning/latest
```

---

### 步骤 5：「今天发什么」— 决策中心

**前端**：http://localhost:3000/decision

1. 填写当前节气/节日（可选，用于 30% 热点权重）
2. 点击「今天发什么」
3. 查看 3–5 条排名推荐，含预测星级、预计播放、理由

**API**：

```bash
curl -X POST http://localhost:8000/accounts/1/decide/today \
  -H "Content-Type: application/json" \
  -d '{"season": "夏至", "festival": "", "count": 5}'
```

决策逻辑：**70% 账号历史经验** + **30% 全网热点**（可在「热点管理」页录入）。

**录入热点（前端）**：

1. 侧边栏进入 **热点管理**
2. 点击 **+ 新建热点**，填写话题、分类、热度、节气/节日
3. 支持 CSV 批量导入

**API（备选）**：

```bash
curl -X POST http://localhost:8000/trends \
  -H "Content-Type: application/json" \
  -d '{"topic": "夏季养心", "category": "养生", "heat_score": 85, "season": "夏至"}'
```

---

### 步骤 6：发布前预测拦截

写完文案后，先预测再决定是否发布。

**前端**：http://localhost:3000/predict

**API**：

```bash
curl -X POST http://localhost:8000/accounts/1/predict \
  -H "Content-Type: application/json" \
  -d '{
    "title": "老祖宗留下来的养阳口诀",
    "hook": "老祖宗",
    "template": "口诀",
    "duration": 35
  }'
```

返回示例：

```json
{
  "pass": true,
  "prediction": {
    "predict_view": 380,
    "predict_level": 4,
    "confidence": 0.72,
    "reason": ["模板「口诀」为账号最佳类型", "..."],
    "passed": true
  }
}
```

`pass: false` 表示低于账号阈值（默认为近 30 条播放 P25），建议修改文案后重试。

---

### 步骤 7：发布并记录

**前端（推荐）**：

1. 进入 **视频记忆** → 点击 **+ 发布视频**
2. 填写标题、Hook、模板等，可选填发布时间
3. 发布后进入视频详情页，点击 **编辑表现数据** 更新播放量/完播率

**API（管线钩子，备选）**：

```bash
curl -X POST http://localhost:8000/accounts/1/pipeline/publish \
  -H "Content-Type: application/json" \
  -d '{
    "title": "立夏养阳三件事",
    "hook": "老祖宗",
    "template": "口诀",
    "knowledge_source": "黄帝内经",
    "scene_style": "古风",
    "cta": "收藏",
    "duration": 32,
    "initial_performance": {"views": 0, "finish_rate": 0},
    "require_prediction_pass": false
  }'
```

该接口自动完成：

1. 写入 Video Memory
2. 创建 T+1h / T+24h / T+7d 表现同步任务
3. Content DNA 打标
4. 绑定当前活跃 Prompt 版本

若希望发布前强制预测通过，设 `"require_prediction_pass": true`。

发布后更新播放数据：在 **视频详情页 → 编辑表现数据** 录入即可（无需调 API）。

---

## 四、前端页面速查

| 页面 | 路径 | 功能 |
|------|------|------|
| 账号画像 | `/` | 最佳栏目/画面/时长/Hook；**编辑锁定字段** |
| 决策中心 | `/decision` | 今天发什么 |
| 视频记忆 | `/videos` | 列表、**发布视频**（`/videos/new`）、详情 |
| 热点管理 | `/trends` | 热点 **新建/编辑/删除**、CSV 导入 |
| 学习报告 | `/learning` | Brain Learning 报告与策略建议 |
| 预测拦截 | `/predict` | 发布前效果预测 |
| Prompt 管理 | `/prompts` | **创建版本**、进化、激活 |
| 数据导入 | `/import` | CSV / JSON 批量导入 |

侧边栏 **+ 创建 / 编辑 / 删除** 管理账号；每个账号数据完全隔离。

---

## 五、Prompt 进化

**前端**：http://localhost:3000/prompts

- **+ 创建版本**：手动录入 Prompt 全文与变更说明
- 查看各版本的视频数、平均播放、推荐分
- **检查进化 / 强制进化**：自动生成新版本
- **激活此版本**：切换活跃 Prompt

默认 **半自动模式**（`auto_evolve=false`）：系统生成新版本后需人工确认激活。

---

## 六、常见问题

### Q：配置了 DeepSeek 但打标仍是规则结果？

1. 确认 `.env` 已被 backend 加载（Docker 需加 `env_file`）
2. 确认 `OPENAI_API_KEY` 非空
3. 对已有视频执行 `POST /videos/{id}/retag` 重新打标
4. 查看 backend 日志是否有 API 报错

### Q：首页显示「暂无画像」？

需要先：导入视频 → DNA 打标完成 → 触发 Brain Learning（见步骤 3）。

### Q：决策中心返回空或报错？

至少需要若干条带 DNA 标签且有播放数据的视频，并已完成至少一次 Learning。

### Q：视频号 / B站数据怎么同步？

当前版本默认是**手动导入 + 后台录入**。发布后在「视频记忆」详情页更新播放数据，或调用 `PATCH /videos/{id}/performance`。

平台适配器已预留：

| 平台 | `.env` 开关 | 说明 |
|------|-------------|------|
| 视频号 | `WECHAT_CHANNELS_ENABLED` | 需 AppID/Secret |
| B站 | `BILIBILI_ENABLED` | 需 AppKey/Secret + AccessToken |

未开启时统一走手动模式。抖音 / 快手目前仅作账号标签，自动同步尚未接入。

### Q：多个账号怎么管理？

每个账号独立 AI Memory，互不可见。侧边栏切换账号即可。

---

## 七、每日自动运转（上线后）

配置 Celery Worker + Beat 后，系统每天自动：

| 时间 | 任务 |
|------|------|
| 每 15 分钟 | 检查 T+1h/24h/7d 表现同步 |
| 02:00 | 全账号 Brain Learning + 画像刷新 + 经验库 + 策略优化 |
| 02:30 | Prompt 进化检查 |

你只需：按决策中心选题 → 创作 → 预测 → 发布 → 隔天查看学习报告。

---

## 相关文档

- [部署说明](DEPLOYMENT.md)
- [数据导入](IMPORT.md)
- [产品设计](../AI-Memory-开发文档.md)
