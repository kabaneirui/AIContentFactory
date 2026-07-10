KNOWLEDGE_ANALYSIS_SYSTEM_PROMPT = """你是一个短视频运营归因分析专家。对爆款或失败视频做 5 维深度归因。

必须严格输出一个 JSON 对象，包含且仅包含：
- dimension_scores: 对象，键为 title / hook / knowledge / collect_value / engagement，值为 { "score": 1-5, "note": "说明" }
- analysis_text: 一段 2-4 句的综合分析

只输出 JSON，不要 markdown 代码块，不要额外说明。"""


def build_knowledge_analysis_user_prompt(
    *,
    knowledge_type: str,
    title: str,
    views: int,
    avg_view: float,
    dna_tags_json: str,
    profile_json: str,
) -> str:
    label = "爆款" if knowledge_type == "hit" else "失败"
    return (
        f"分析类型: {label}\n"
        f"标题: {title}\n"
        f"播放量: {views}（账号近期均值 {avg_view:.0f}）\n"
        f"DNA 标签: {dna_tags_json}\n"
        f"账号画像: {profile_json}\n\n"
        f"请对该{label}视频进行 5 维归因分析。"
    )
