# 视频历史数据导入模板

用于 `POST /accounts/{id}/videos/import`（JSON）或 `POST /accounts/{id}/videos/import/csv`（CSV 上传）。

## 必填字段

| 字段 | 说明 |
|------|------|
| title | 视频标题 |

## 内容字段（可选）

| 字段 | 说明 | 示例 |
|------|------|------|
| platform_video_id | 平台视频 ID，重复导入时跳过 | wx_12345 |
| platform | 平台，默认取账号平台 | wechat_channels |
| script | 完整脚本 | 老祖宗留下来的养阳口诀…… |
| hook | 开头钩子 | 老祖宗 |
| template | 内容模板 | 口诀 |
| knowledge_source | 知识来源 | 黄帝内经 |
| prompt | Prompt 版本号 | v1.2 |
| scene_style | 画面风格 | 水墨 |
| duration | 时长（秒） | 45 |
| cta | 行动号召 | 收藏 |
| publish_time | 发布时间（ISO 8601） | 2026-01-15T20:00:00+08:00 |
| season | 节气 | 立春 |
| festival | 节日 | 春节 |
| weather | 天气 | 晴 |
| keyword | 关键词 | 养阳 |
| category | 栏目 | 养生口诀 |

## 表现数据字段（可选）

| 字段 | 说明 |
|------|------|
| views | 播放量 |
| ctr | 点击率（0–1） |
| rate_3s | 3 秒留存率（0–1） |
| finish_rate | 完播率（0–1） |
| average_watch | 平均观看时长（秒） |
| likes | 点赞 |
| comments | 评论 |
| shares | 分享 |
| collects | 收藏 |
| forwards | 转发 |
| fans_increase | 涨粉 |
| reach_level | 流量层级 |
| recommend_rate | 推荐率（0–1） |
| engagement_rate | 互动率（0–1） |

## CSV 示例

```csv
title,hook,template,knowledge_source,publish_time,views,finish_rate
老祖宗留下来的养阳口诀,老祖宗,口诀,黄帝内经,2026-01-15T20:00:00+08:00,420,0.35
很多人不知道的养心方法,很多人,动作,养心,2026-01-16T17:00:00+08:00,280,0.22
```

## JSON 示例

```json
{
  "videos": [
    {
      "title": "老祖宗留下来的养阳口诀",
      "hook": "老祖宗",
      "template": "口诀",
      "knowledge_source": "黄帝内经",
      "publish_time": "2026-01-15T20:00:00+08:00",
      "views": 420,
      "finish_rate": 0.35
    }
  ]
}
```

## 生命周期说明

- 有 `publish_time` 的记录导入后状态为 `published`，并自动创建 T+1h / T+24h / T+7d 表现同步任务，随后进入 `syncing`
- 无 `publish_time` 的记录状态为 `created`
