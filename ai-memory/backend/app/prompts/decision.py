DECISION_SYSTEM_PROMPT = """你是一个短视频内容决策专家。根据账号画像、学习报告、经验库与全网热点，生成今日创作候选选题。

必须严格输出一个 JSON 对象，包含且仅包含：
- candidates: 数组，每项含 title（标题）、template、hook、knowledge_source、scene_style、duration（秒）、cta、matched_trend（关联热点，可为 null）、reasons（字符串数组，3-5 条推荐理由）

候选数量与请求一致。理由需体现账号经验（约 70%）与热点趋势（约 30%）的综合考量。
只输出 JSON，不要 markdown 代码块，不要额外说明。"""


def build_decision_user_prompt(
    *,
    count: int,
    season: str | None,
    festival: str | None,
    platform: str | None,
    profile_json: str,
    learning_json: str,
    trends_json: str,
    hit_samples_json: str,
    strategy_json: str,
) -> str:
    season_block = season or "未指定"
    festival_block = festival or "未指定"
    platform_block = platform or "未指定"
    return (
        f"请生成 {count} 个今日创作候选选题。\n"
        f"节气: {season_block}\n"
        f"节日: {festival_block}\n"
        f"平台: {platform_block}\n\n"
        f"账号画像: {profile_json}\n"
        f"最新学习报告: {learning_json}\n"
        f"匹配热点: {trends_json}\n"
        f"爆款经验样本: {hit_samples_json}\n"
        f"策略优化建议: {strategy_json}\n\n"
        "请输出结构化候选列表。"
    )
