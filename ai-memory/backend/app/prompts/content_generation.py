CONTENT_GENERATION_SYSTEM_PROMPT = """你是一个短视频口播文案专家。根据选题方向、账号画像与 Prompt 规范，生成可直接录制的完整口播稿。

必须严格输出一个 JSON 对象，包含且仅包含：
- script: 完整口播稿（口语化、有节奏，适合短视频录制）
- title: 最终标题（可在选题标题基础上优化钩子）

要求：
1. 前 3 秒必须有强钩子（使用提供的 hook 或等价开场）
2. 正文突出实用获得感或收藏价值，避免空洞说教
3. 结尾有明确 CTA（收藏 / 关注 / 评论）
4. 口播时长控制在请求的 duration 秒左右（约 {duration} 秒）
5. 只输出 JSON，不要 markdown 代码块，不要额外说明。"""


def build_content_generation_user_prompt(
    *,
    title: str,
    hook: str,
    template: str,
    knowledge_source: str,
    scene_style: str,
    duration: int,
    cta: str,
    season: str | None,
    festival: str | None,
    matched_trend: str | None,
    reasons: list[str],
    prompt_content: str,
    profile_summary: str,
) -> str:
    season_block = season or "未指定"
    festival_block = festival or "未指定"
    trend_block = matched_trend or "无"
    reasons_block = "\n".join(f"- {r}" for r in reasons[:5]) if reasons else "无"
    return (
        f"选题标题: {title}\n"
        f"Hook: {hook}\n"
        f"内容模板: {template}\n"
        f"知识来源: {knowledge_source}\n"
        f"画面风格: {scene_style}\n"
        f"目标时长: {duration} 秒\n"
        f"CTA: {cta}\n"
        f"节气: {season_block}\n"
        f"节日: {festival_block}\n"
        f"关联热点: {trend_block}\n\n"
        f"决策推荐理由:\n{reasons_block}\n\n"
        f"账号画像摘要:\n{profile_summary}\n\n"
        f"当前 Prompt 规范:\n{prompt_content}\n\n"
        "请生成完整口播稿。"
    )
