DNA_TAGGING_SYSTEM_PROMPT = """你是一个短视频内容分析专家。根据视频的标题、脚本、钩子、栏目等信息，输出 Content DNA 8 维结构化标签。

必须严格输出一个 JSON 对象，包含且仅包含以下 8 个字符串字段：
- title_type: 标题类型（如：口诀型、数字型、疑问型、对比型、故事型）
- hook_type: Hook 类型（如：老祖宗、很多人、60岁以后、你知道吗）
- template: 内容模板（如：口诀、动作、情绪、科普）
- knowledge: 知识类型（如：黄帝内经、养阳、养心、经络）
- emotion: 情绪类型（如：获得感、焦虑感、共鸣感、好奇感）
- scene: 画面类型（如：水墨、数字人、实拍、古风）
- pacing: 镜头节奏（快切、慢节奏、混合 之一）
- cta: CTA 类型（如：收藏、关注、评论、转发）

只输出 JSON，不要 markdown 代码块，不要额外说明。"""


def build_dna_tagging_user_prompt(
    *,
    title: str,
    script: str | None,
    hook: str | None,
    template: str | None,
    knowledge_source: str | None,
    scene_style: str | None,
    cta: str | None,
    category: str | None,
    keyword: str | None,
    duration: int | None,
) -> str:
    lines = [
        "请为以下短视频生成 Content DNA 标签：",
        f"标题: {title}",
    ]
    if hook:
        lines.append(f"Hook: {hook}")
    if script:
        lines.append(f"脚本: {script}")
    if template:
        lines.append(f"内容模板（参考）: {template}")
    if knowledge_source:
        lines.append(f"知识来源（参考）: {knowledge_source}")
    if scene_style:
        lines.append(f"画面风格（参考）: {scene_style}")
    if cta:
        lines.append(f"CTA（参考）: {cta}")
    if category:
        lines.append(f"栏目: {category}")
    if keyword:
        lines.append(f"关键词: {keyword}")
    if duration is not None:
        lines.append(f"时长（秒）: {duration}")

    return "\n".join(lines)
