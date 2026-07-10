PREDICTION_SYSTEM_PROMPT = """你是一个短视频内容表现预测专家。根据账号历史画像与学习报告，为待发布文案生成预测理由。

必须严格输出一个 JSON 对象，包含且仅包含：
- reason: 字符串数组，3-5 条预测理由（每条以 ✓ 或 ✗ 开头，说明匹配优势或风险）

只输出 JSON，不要 markdown 代码块，不要额外说明。"""


def build_prediction_user_prompt(
    *,
    title: str,
    dna_tags_json: str,
    profile_json: str,
    learning_summary: str | None,
    predict_view: int,
    predict_level: int,
    avg_view: float,
) -> str:
    learning_block = learning_summary or "暂无近期学习报告"
    return (
        f"待发布标题: {title}\n"
        f"预估 DNA 标签: {dna_tags_json}\n"
        f"账号画像: {profile_json}\n"
        f"近期学习摘要: {learning_block}\n\n"
        f"规则引擎预测播放: {predict_view}\n"
        f"账号近期均值: {avg_view:.0f}\n"
        f"预测等级: {predict_level} 星\n\n"
        "请生成结构化预测理由列表。"
    )
