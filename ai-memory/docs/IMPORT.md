# 历史视频 CSV 导入说明

## 接口

- **JSON 批量导入**：`POST /accounts/{account_id}/videos/import`
- **CSV 上传**：`POST /accounts/{account_id}/videos/import/csv`（`multipart/form-data`，字段名 `file`）

导入成功后会自动排队 Content DNA 打标（规则引擎或 LLM，取决于 `OPENAI_API_KEY` 配置）。

## 模板文件

参见同目录 [`import-template.csv`](import-template.csv)。

## 必填字段

| 字段 | 说明 |
|------|------|
| `title` | 视频标题（必填） |

## 推荐字段

| 字段 | 说明 |
|------|------|
| `hook` | 前 3 秒钩子文案 |
| `template` | 内容模板（口诀 / 动作 / 情绪等） |
| `knowledge_source` | 知识来源 |
| `scene_style` | 画面风格 |
| `cta` | 结尾行动号召 |
| `duration` | 时长（秒） |
| `category` | 栏目分类 |
| `publish_time` | 发布时间（ISO 8601，含时区） |
| `script` | 完整口播稿 |

## 表现数据字段（可选）

| 字段 | 说明 |
|------|------|
| `views` | 播放量 |
| `finish_rate` | 完播率（0–1） |
| `ctr` | 点击率 |
| `rate_3s` | 3 秒完播率 |
| `likes` / `comments` / `shares` / `collects` | 互动数据 |

## 校验规则

1. CSV 首行为表头，编码 UTF-8（支持 BOM）
2. `title` 不能为空；重复行按行号返回错误
3. `publish_time` 解析失败时该行报错
4. 数值字段不能为负数；比率字段需在 0–1 之间
5. 含 `publish_time` 的记录会进入 `published → syncing` 并创建 T+1h / T+24h / T+7d 同步任务

## 示例（curl）

```bash
curl -X POST "http://localhost:8000/accounts/1/videos/import/csv" \
  -H "accept: application/json" \
  -F "file=@docs/import-template.csv"
```
