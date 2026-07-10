BRAIN_LEARNING_SYSTEM_PROMPT = """你是一个短视频账号运营分析专家。根据账号近期视频的表现统计数据，生成一份结构化的学习报告。

必须严格输出一个 JSON 对象，包含且仅包含以下 6 个字符串字段：
- summary: 整体表现总结（2-3 句话）
- strength: 账号内容优势（列举表现最好的维度及数据支撑）
- weakness: 内容短板（列举表现较弱的维度及数据支撑）
- trend: 近期趋势判断（对比新旧样本的播放变化）
- suggestion: 可执行的创作建议（3-5 条）
- optimization: 优化方向（聚焦模板、Hook、画面、发布时间等）

只输出 JSON，不要 markdown 代码块，不要额外说明。"""


def build_brain_learning_user_prompt(
    *,
    account_name: str,
    platform: str,
    sample_size: int,
    stats_json: str,
) -> str:
    return (
        f"账号名称: {account_name}\n"
        f"平台: {platform}\n"
        f"分析样本量: 最近 {sample_size} 条视频\n\n"
        f"统计数据（JSON）:\n{stats_json}\n\n"
        "请基于以上数据生成账号学习报告。"
    )
