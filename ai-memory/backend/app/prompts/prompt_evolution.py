PROMPT_EVOLUTION_SYSTEM_PROMPT = """你是一个短视频内容生成 Prompt 优化专家。根据账号历史表现、学习报告与当前 Prompt 版本，生成改进后的新版本 Prompt。

输出必须是 JSON 对象，包含：
- prompt_content: string，完整的新 Prompt 正文（可直接用于内容生成）
- change_log: string，相对上一版的具体调整说明（简洁条目式）
- evolution_reason: string，触发进化的主要原因

优化原则：
1. 保留已验证有效的 Hook、栏目与 CTA 模式
2. 针对学习报告中的弱项做定向调整
3. 每次进化聚焦 1-2 个可验证维度，避免大幅重写
4. Prompt 需包含明确的输出格式与时长约束"""


def build_prompt_evolution_user_prompt(
    *,
    account_name: str,
    platform: str,
    current_version: str,
    current_prompt: str,
    video_count: int,
    avg_view: float,
    avg_finish_rate: float,
    account_avg_view: float,
    learning_summary: str | None,
    learning_weakness: str | None,
    learning_suggestion: str | None,
    learning_optimization: str | None,
    trigger_reason: str,
) -> str:
    return f"""账号：{account_name}（{platform}）
当前 Prompt 版本：{current_version}
当前版本样本：{video_count} 条
当前版本平均播放：{avg_view:.0f}
当前版本平均完播率：{avg_finish_rate:.2%}
账号整体平均播放：{account_avg_view:.0f}
进化触发原因：{trigger_reason}

当前 Prompt 全文：
---
{current_prompt}
---

最新学习报告摘要：
- 总结：{learning_summary or "无"}
- 弱项：{learning_weakness or "无"}
- 建议：{learning_suggestion or "无"}
- 优化方向：{learning_optimization or "无"}

请生成改进后的 Prompt V 下一版。"""
