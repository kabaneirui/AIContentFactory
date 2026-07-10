"""Prompt Evolution Engine：版本追踪、指标统计、触发进化与审核激活。"""

from __future__ import annotations

import logging
import re
from statistics import mean

from pydantic import BaseModel, Field, ValidationError
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.models import Account, BrainLearning, ContentMemory, ContentPerformance
from app.models.prompt_version import PromptVersion
from app.prompts.prompt_evolution import (
    PROMPT_EVOLUTION_SYSTEM_PROMPT,
    build_prompt_evolution_user_prompt,
)
from app.services.llm_client import OpenAiCompatibleClient, get_llm_client

logger = logging.getLogger(__name__)

EVOLUTION_SAMPLE_THRESHOLD = 20
DEFAULT_PROMPT_V1 = """你是一个短视频文案生成专家。请根据账号定位与选题生成完整短视频脚本。

输出要求：
1. 标题：带强钩子，适合前 3 秒抓注意力
2. 正文：口语化、节奏快，突出收藏价值或实用获得感
3. 结尾：明确 CTA（收藏 / 关注 / 评论 三选一）
4. 时长：控制在 30–45 秒口播量
5. 风格：结合养生/知识类账号，避免空洞说教"""


class PromptEvolutionError(Exception):
    pass


class EvolutionLlmOutput(BaseModel):
    prompt_content: str = Field(..., min_length=10)
    change_log: str = Field(..., min_length=1)
    evolution_reason: str = Field(..., min_length=1)


def _next_version_label(existing_versions: list[str]) -> str:
    numbers = []
    for label in existing_versions:
        match = re.match(r"^V(\d+)$", label, re.IGNORECASE)
        if match:
            numbers.append(int(match.group(1)))
    next_num = max(numbers, default=0) + 1
    return f"V{next_num}"


def compute_recommend_score(avg_view: float, account_avg_view: float) -> int:
    if account_avg_view <= 0:
        return 3 if avg_view > 0 else 1
    ratio = avg_view / account_avg_view
    if ratio >= 1.3:
        return 5
    if ratio >= 1.1:
        return 4
    if ratio >= 0.9:
        return 3
    if ratio >= 0.7:
        return 2
    return 1


async def _account_avg_view(db: AsyncSession, account_id: int) -> float:
    stmt = (
        select(func.avg(ContentPerformance.views))
        .join(ContentMemory, ContentMemory.id == ContentPerformance.content_memory_id)
        .where(ContentMemory.account_id == account_id)
        .where(ContentPerformance.views > 0)
    )
    result = await db.execute(stmt)
    value = result.scalar_one_or_none()
    return float(value or 0.0)


async def refresh_version_stats(
    db: AsyncSession,
    prompt_version: PromptVersion,
    *,
    account_avg_view: float | None = None,
) -> PromptVersion:
    stmt = (
        select(ContentMemory)
        .options(selectinload(ContentMemory.performance))
        .where(
            ContentMemory.account_id == prompt_version.account_id,
            ContentMemory.prompt == prompt_version.version,
        )
    )
    result = await db.execute(stmt)
    videos = list(result.scalars().all())

    views: list[int] = []
    finish_rates: list[float] = []
    for video in videos:
        if video.performance and video.performance.views > 0:
            views.append(video.performance.views)
            if video.performance.finish_rate is not None:
                finish_rates.append(video.performance.finish_rate)

    prompt_version.video_count = len(videos)
    prompt_version.avg_view = mean(views) if views else 0.0
    prompt_version.avg_finish_rate = mean(finish_rates) if finish_rates else 0.0

    if account_avg_view is None:
        account_avg_view = await _account_avg_view(db, prompt_version.account_id)
    prompt_version.recommend_score = compute_recommend_score(
        prompt_version.avg_view,
        account_avg_view,
    )
    await db.flush()
    await db.refresh(prompt_version)
    return prompt_version


async def refresh_all_version_stats(
    db: AsyncSession,
    account_id: int,
) -> list[PromptVersion]:
    account_avg = await _account_avg_view(db, account_id)
    versions = await list_prompt_versions(db, account_id)
    for version in versions:
        await refresh_version_stats(db, version, account_avg_view=account_avg)
    return versions


async def list_prompt_versions(
    db: AsyncSession,
    account_id: int,
) -> list[PromptVersion]:
    stmt = (
        select(PromptVersion)
        .where(PromptVersion.account_id == account_id)
        .order_by(PromptVersion.id.asc())
    )
    result = await db.execute(stmt)
    return list(result.scalars().all())


async def get_active_prompt_version(
    db: AsyncSession,
    account_id: int,
) -> PromptVersion | None:
    stmt = (
        select(PromptVersion)
        .where(
            PromptVersion.account_id == account_id,
            PromptVersion.is_active.is_(True),
        )
        .order_by(PromptVersion.recommend_score.desc(), PromptVersion.id.desc())
        .limit(1)
    )
    result = await db.execute(stmt)
    return result.scalar_one_or_none()


async def get_prompt_version_by_id(
    db: AsyncSession,
    version_id: int,
) -> PromptVersion | None:
    result = await db.execute(
        select(PromptVersion).where(PromptVersion.id == version_id)
    )
    return result.scalar_one_or_none()


async def get_prompt_version_by_label(
    db: AsyncSession,
    account_id: int,
    version: str,
) -> PromptVersion | None:
    result = await db.execute(
        select(PromptVersion).where(
            PromptVersion.account_id == account_id,
            PromptVersion.version == version,
        )
    )
    return result.scalar_one_or_none()


async def ensure_initial_prompt_version(
    db: AsyncSession,
    account: Account,
) -> PromptVersion:
    existing = await get_prompt_version_by_label(db, account.id, "V1")
    if existing is not None:
        return existing

    prompt = PromptVersion(
        account_id=account.id,
        version="V1",
        prompt_content=DEFAULT_PROMPT_V1,
        change_log="初始版本",
        is_active=True,
        recommend_score=3,
    )
    db.add(prompt)
    await db.flush()
    return prompt


async def create_prompt_version(
    db: AsyncSession,
    account: Account,
    *,
    prompt_content: str,
    change_log: str | None,
    activate: bool,
) -> PromptVersion:
    versions = await list_prompt_versions(db, account.id)
    label = _next_version_label([v.version for v in versions])

    if activate:
        for version in versions:
            version.is_active = False

    prompt = PromptVersion(
        account_id=account.id,
        version=label,
        prompt_content=prompt_content,
        change_log=change_log or f"手动创建 {label}",
        is_active=activate,
    )
    db.add(prompt)
    await db.flush()
    await refresh_version_stats(db, prompt)
    return prompt


async def activate_prompt_version(
    db: AsyncSession,
    account_id: int,
    version_id: int,
) -> tuple[PromptVersion, str | None]:
    target = await get_prompt_version_by_id(db, version_id)
    if target is None or target.account_id != account_id:
        raise PromptEvolutionError(f"Prompt version {version_id} not found")

    previous: str | None = None
    versions = await list_prompt_versions(db, account_id)
    for version in versions:
        if version.is_active:
            previous = version.version
        version.is_active = version.id == target.id

    await db.flush()
    return target, previous


async def _get_latest_learning(
    db: AsyncSession,
    account_id: int,
) -> BrainLearning | None:
    stmt = (
        select(BrainLearning)
        .where(BrainLearning.account_id == account_id)
        .order_by(BrainLearning.learning_date.desc(), BrainLearning.id.desc())
        .limit(1)
    )
    result = await db.execute(stmt)
    return result.scalar_one_or_none()


def _check_evolution_triggers(
    active: PromptVersion,
    account_avg_view: float,
    learning: BrainLearning | None,
    *,
    force: bool,
) -> tuple[bool, str]:
    if force:
        return True, "手动强制进化"

    if (
        active.video_count >= EVOLUTION_SAMPLE_THRESHOLD
        and account_avg_view > 0
        and active.avg_view < account_avg_view
    ):
        return (
            True,
            f"当前版本样本 {active.video_count} 条且平均播放低于账号均值",
        )

    if learning is not None:
        optimization = (learning.optimization or "").strip()
        if optimization and optimization not in ("无", "暂无"):
            return True, "Brain Learning 报告建议调整生成策略"

        suggestion = (learning.suggestion or "").strip()
        if any(
            keyword in suggestion
            for keyword in ("Prompt", "prompt", "生成策略", "文案策略", "钩子")
        ):
            return True, "学习报告建议优化 Prompt / 生成策略"

    return False, "未满足进化触发条件"


async def _generate_evolved_prompt(
    account: Account,
    active: PromptVersion,
    *,
    account_avg_view: float,
    learning: BrainLearning | None,
    trigger_reason: str,
    llm_client: OpenAiCompatibleClient | None = None,
) -> EvolutionLlmOutput:
    client = llm_client or get_llm_client()
    if not client.is_configured:
        return _fallback_evolution(active, trigger_reason)

    user_prompt = build_prompt_evolution_user_prompt(
        account_name=account.name,
        platform=account.platform,
        current_version=active.version,
        current_prompt=active.prompt_content,
        video_count=active.video_count,
        avg_view=active.avg_view,
        avg_finish_rate=active.avg_finish_rate,
        account_avg_view=account_avg_view,
        learning_summary=learning.summary if learning else None,
        learning_weakness=learning.weakness if learning else None,
        learning_suggestion=learning.suggestion if learning else None,
        learning_optimization=learning.optimization if learning else None,
        trigger_reason=trigger_reason,
    )

    try:
        raw = await client.complete_json(
            system=PROMPT_EVOLUTION_SYSTEM_PROMPT,
            user=user_prompt,
        )
        return EvolutionLlmOutput.model_validate(raw)
    except (ValidationError, ValueError, RuntimeError) as exc:
        logger.warning("LLM prompt evolution failed, using fallback: %s", exc)
        return _fallback_evolution(active, trigger_reason)


def _fallback_evolution(
    active: PromptVersion,
    trigger_reason: str,
) -> EvolutionLlmOutput:
    extra_rules = []
    if active.avg_view > 0:
        extra_rules.append(
            f"- 针对当前版本平均播放 {active.avg_view:.0f}，强化前 3 秒钩子与标题数字化"
        )
    extra_rules.append("- 在结尾 CTA 中优先使用「收藏」以提升完播与复看")
    extra_rules.append("- 每条脚本附带 1 个可记忆口诀或数字锚点")

    appended = "\n".join(extra_rules)
    new_content = f"{active.prompt_content.rstrip()}\n\n【进化补充规则】\n{appended}"
    return EvolutionLlmOutput(
        prompt_content=new_content,
        change_log="规则引擎补充：强化钩子、数字化标题与收藏 CTA",
        evolution_reason=trigger_reason,
    )


async def evolve_prompt_for_account(
    db: AsyncSession,
    account: Account,
    *,
    force: bool = False,
    llm_client: OpenAiCompatibleClient | None = None,
) -> tuple[bool, str, PromptVersion | None, bool]:
    """尝试进化 Prompt。返回 (evolved, reason, new_version, pending_review)。"""
    await refresh_all_version_stats(db, account.id)
    active = await get_active_prompt_version(db, account.id)
    if active is None:
        active = await ensure_initial_prompt_version(db, account)

    account_avg = await _account_avg_view(db, account.id)
    learning = await _get_latest_learning(db, account.id)
    should_evolve, reason = _check_evolution_triggers(
        active,
        account_avg,
        learning,
        force=force,
    )
    if not should_evolve:
        return False, reason, None, False

    evolved = await _generate_evolved_prompt(
        account,
        active,
        account_avg_view=account_avg,
        learning=learning,
        trigger_reason=reason,
        llm_client=llm_client,
    )

    versions = await list_prompt_versions(db, account.id)
    label = _next_version_label([v.version for v in versions])
    auto_activate = bool(account.auto_evolve)

    new_version = PromptVersion(
        account_id=account.id,
        version=label,
        prompt_content=evolved.prompt_content,
        change_log=evolved.change_log,
        is_active=auto_activate,
    )
    if auto_activate:
        for version in versions:
            version.is_active = False

    db.add(new_version)
    await db.flush()
    await refresh_version_stats(db, new_version, account_avg_view=account_avg)

    pending_review = not auto_activate
    return True, evolved.evolution_reason, new_version, pending_review


async def run_prompt_evolution_for_account(
    db: AsyncSession,
    account_id: int,
    *,
    force: bool = False,
) -> tuple[bool, str, PromptVersion | None, bool]:
    result = await db.execute(select(Account).where(Account.id == account_id))
    account = result.scalar_one_or_none()
    if account is None:
        raise PromptEvolutionError(f"Account {account_id} not found")
    return await evolve_prompt_for_account(db, account, force=force)


async def run_prompt_evolution_for_all_accounts(db: AsyncSession) -> dict[str, int]:
    result = await db.execute(select(Account.id))
    account_ids = list(result.scalars().all())
    evolved_count = 0
    pending_count = 0
    for account_id in account_ids:
        try:
            evolved, _, _, pending = await run_prompt_evolution_for_account(
                db, account_id
            )
            if evolved:
                evolved_count += 1
                if pending:
                    pending_count += 1
        except Exception:
            logger.exception("Prompt evolution failed for account %s", account_id)
    return {
        "accounts_checked": len(account_ids),
        "evolved": evolved_count,
        "pending_review": pending_count,
    }
