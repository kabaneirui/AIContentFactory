from datetime import UTC, datetime, timedelta

from collections import Counter

import pytest
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from app.models import ContentMemory, ContentPerformance, KnowledgeType, LifecycleStatus
from app.services import brain_learner, knowledge_analyzer, strategy_optimizer
from app.services.strategy_optimizer import attribute_failure, build_strategy_optimization


@pytest.fixture
async def account_id(client: AsyncClient) -> int:
    response = await client.post(
        "/accounts",
        json={"name": "经验库测试号", "platform": "wechat_channels"},
    )
    return response.json()["id"]


async def _seed_video(
    db: AsyncSession,
    account_id: int,
    *,
    title: str,
    views: int,
    template: str,
    hook: str,
    scene: str,
    knowledge: str,
    cta: str,
    duration: int,
    publish_time: datetime,
    rate_3s: float | None = None,
) -> ContentMemory:
    video = ContentMemory(
        account_id=account_id,
        platform="wechat_channels",
        title=title,
        hook=hook,
        template=template,
        knowledge_source=knowledge,
        scene_style=scene,
        cta=cta,
        duration=duration,
        publish_time=publish_time,
        dna_tags={
            "title_type": "口诀型",
            "hook_type": hook,
            "template": template,
            "knowledge": knowledge,
            "emotion": "获得感",
            "scene": scene,
            "pacing": "快切",
            "cta": cta,
        },
        lifecycle_status=LifecycleStatus.TAGGED,
    )
    db.add(video)
    await db.flush()
    db.add(
        ContentPerformance(
            content_memory_id=video.id,
            views=views,
            rate_3s=rate_3s,
            finish_rate=0.25,
        )
    )
    await db.flush()
    return video


@pytest.fixture
async def seeded_account(
    db_session: AsyncSession,
    account_id: int,
) -> int:
    base_time = datetime(2026, 6, 1, 20, 0, tzinfo=UTC)
    samples = [
        ("老祖宗养阳口诀", 420, "口诀", "老祖宗", "古风", "黄帝内经", "收藏", 32),
        ("很多人不知道的养心法", 280, "动作", "很多人", "实拍", "养心", "关注", 45),
        ("情绪养生别乱试", 110, "情绪", "你知道吗", "数字人", "养生常识", "评论", 60),
        ("60岁以后要这样睡", 500, "口诀", "60岁以后", "古风", "黄帝内经", "收藏", 30),
        ("经络疏通小动作", 390, "动作", "很多人", "实拍", "经络", "收藏", 35),
    ]
    for index, row in enumerate(samples):
        title, views, template, hook, scene, knowledge, cta, duration = row
        await _seed_video(
            db_session,
            account_id,
            title=title,
            views=views,
            template=template,
            hook=hook,
            scene=scene,
            knowledge=knowledge,
            cta=cta,
            duration=duration,
            publish_time=base_time + timedelta(days=index),
            rate_3s=0.25 if views < 200 else 0.45,
        )
    await db_session.commit()
    return account_id


@pytest.mark.asyncio
async def test_run_knowledge_evolution(
    db_session: AsyncSession,
    seeded_account: int,
):
    await brain_learner.run_learning_for_account(db_session, seeded_account)
    await db_session.commit()

    hits, hit_total = await knowledge_analyzer.list_knowledge(
        db_session,
        seeded_account,
        knowledge_type=KnowledgeType.HIT,
    )
    fails, fail_total = await knowledge_analyzer.list_knowledge(
        db_session,
        seeded_account,
        knowledge_type=KnowledgeType.FAIL,
    )
    assert hit_total >= 1
    assert fail_total >= 1
    assert hits[0].dimension_scores["title"]["score"] >= 1
    assert hits[0].analysis_text

    result = await knowledge_analyzer.run_knowledge_evolution_for_account(
        db_session,
        seeded_account,
    )
    assert result["hits"] == 0
    assert result["fails"] == 0


@pytest.mark.asyncio
async def test_knowledge_api(
    client: AsyncClient,
    db_session: AsyncSession,
    seeded_account: int,
):
    await brain_learner.run_learning_for_account(db_session, seeded_account)
    await db_session.commit()

    hit_response = await client.get(
        f"/accounts/{seeded_account}/knowledge",
        params={"type": "hit"},
    )
    assert hit_response.status_code == 200
    hit_data = hit_response.json()
    assert hit_data["total"] >= 1
    assert hit_data["items"][0]["knowledge_type"] == "hit"

    fail_response = await client.get(
        f"/accounts/{seeded_account}/knowledge",
        params={"type": "fail"},
    )
    assert fail_response.status_code == 200
    assert fail_response.json()["total"] >= 1


@pytest.mark.asyncio
async def test_strategy_optimizer_updates_learning(
    db_session: AsyncSession,
    seeded_account: int,
):
    learning = await brain_learner.run_learning_for_account(db_session, seeded_account)
    await db_session.commit()

    strategy = await strategy_optimizer.run_strategy_optimizer_for_account(
        db_session,
        seeded_account,
    )
    assert strategy is not None
    assert strategy.summary
    await db_session.refresh(learning)
    assert "策略调整建议" in learning.optimization or strategy.failure_reasons


def test_attribute_failure_detects_weak_opening():
    video = ContentMemory(
        title="测试",
        template="情绪",
        hook="你知道吗",
        scene_style="数字人",
        duration=60,
        publish_time=datetime(2026, 6, 1, 20, 0, tzinfo=UTC),
        dna_tags={"scene": "数字人", "hook_type": "你知道吗", "template": "情绪"},
    )
    video.performance = ContentPerformance(
        content_memory_id=1,
        views=100,
        rate_3s=0.2,
    )
    reasons = attribute_failure(video, None, recent_fail_scenes=["数字人", "数字人"])
    assert "weak_opening" in reasons
    assert "scene_repetition" in reasons
    assert "low_knowledge_value" in reasons


def test_build_strategy_optimization():
    strategy = build_strategy_optimization(
        Counter({"weak_hook": 2, "low_knowledge_value": 1}),
        None,
        None,
    )
    assert "Hook 太平" in strategy.failure_reasons
    assert strategy.increase
    assert strategy.decrease
