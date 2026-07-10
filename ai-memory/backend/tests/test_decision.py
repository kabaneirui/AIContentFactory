from datetime import UTC, datetime, timedelta

import pytest
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from app.models import ContentMemory, ContentPerformance, LifecycleStatus
from app.schemas.decision import DecideTodayRequest
from app.services import brain_learner, decision_center, trend_service
from app.schemas.trend import TrendTopicCreate


@pytest.fixture
async def account_id(client: AsyncClient) -> int:
    response = await client.post(
        "/accounts",
        json={"name": "决策测试号", "platform": "wechat_channels"},
    )
    return response.json()["id"]


async def _seed_video(
    db: AsyncSession,
    account_id: int,
    *,
    title: str,
    views: int,
    template: str = "口诀",
    hook: str = "老祖宗",
    scene: str = "古风",
    knowledge: str = "黄帝内经",
    cta: str = "收藏",
    duration: int = 32,
    publish_time: datetime | None = None,
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
        publish_time=publish_time or datetime(2026, 6, 1, 20, 0, tzinfo=UTC),
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
    performance = ContentPerformance(
        content_memory_id=video.id,
        views=views,
        finish_rate=0.28,
    )
    db.add(performance)
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
        )
    await db_session.commit()
    return account_id


@pytest.fixture
async def seeded_trends(db_session: AsyncSession):
    await trend_service.create_trend(
        db_session,
        TrendTopicCreate(
            topic="夏季养心",
            category="黄帝内经",
            heat_score=88.0,
            season="夏至",
            source="manual",
        ),
    )
    await trend_service.create_trend(
        db_session,
        TrendTopicCreate(
            topic="三伏祛湿",
            category="养生",
            heat_score=75.0,
            season="大暑",
            source="manual",
        ),
    )
    await db_session.commit()


@pytest.fixture
async def learned_account(
    db_session: AsyncSession,
    seeded_account: int,
) -> int:
    await brain_learner.run_learning_for_account(db_session, seeded_account)
    await db_session.commit()
    return seeded_account


@pytest.mark.asyncio
async def test_decide_today_api(
    client: AsyncClient,
    learned_account: int,
    seeded_trends,
):
    response = await client.post(
        f"/accounts/{learned_account}/decide/today",
        json={"season": "夏至", "count": 3},
    )
    assert response.status_code == 200
    body = response.json()
    assert body["account_id"] == learned_account
    assert body["season"] == "夏至"
    assert len(body["recommendations"]) == 3

    first = body["recommendations"][0]
    assert first["rank"] == 1
    assert first["title"]
    assert 1 <= first["predict_level"] <= 5
    assert first["predict_view"] > 0
    assert first["suggested_publish_time"]
    assert first["reasons"]
    assert 0.0 <= first["account_weight_score"] <= 1.0
    assert 0.0 <= first["trend_weight_score"] <= 1.0
    assert 0.0 <= first["combined_score"] <= 1.0


@pytest.mark.asyncio
async def test_decide_today_ranking(
    db_session: AsyncSession,
    seeded_account: int,
    seeded_trends,
):
    from app.models import Account

    await brain_learner.run_learning_for_account(db_session, seeded_account)
    await db_session.commit()

    account = await db_session.get(Account, seeded_account)
    assert account is not None

    result = await decision_center.decide_today(
        db_session,
        account,
        DecideTodayRequest(season="夏至", count=5),
    )
    assert len(result.recommendations) >= 3
    ranks = [item.rank for item in result.recommendations]
    assert ranks == sorted(ranks)
    scores = [item.combined_score for item in result.recommendations]
    assert scores == sorted(scores, reverse=True)


@pytest.mark.asyncio
async def test_decide_today_includes_trend_reason(
    db_session: AsyncSession,
    seeded_account: int,
    seeded_trends,
):
    from app.models import Account

    await brain_learner.run_learning_for_account(db_session, seeded_account)
    await db_session.commit()

    account = await db_session.get(Account, seeded_account)
    assert account is not None

    result = await decision_center.decide_today(
        db_session,
        account,
        DecideTodayRequest(season="夏至", count=4),
    )
    all_reasons = " ".join(
        reason for item in result.recommendations for reason in item.reasons
    )
    assert "热点" in all_reasons or "夏至" in all_reasons or "账号" in all_reasons
