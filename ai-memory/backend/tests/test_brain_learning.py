from datetime import UTC, datetime, timedelta

import pytest
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from app.models import Account, ContentMemory, ContentPerformance, LifecycleStatus
from app.services import brain_learner
from app.services.brain_learner import VideoSample, resolve_sample_window


@pytest.fixture
async def account_id(client: AsyncClient) -> int:
    response = await client.post(
        "/accounts",
        json={"name": "学习测试号", "platform": "wechat_channels"},
    )
    return response.json()["id"]


async def _seed_learning_video(
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

    performance = ContentPerformance(content_memory_id=video.id, views=views)
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
        await _seed_learning_video(
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


def test_resolve_sample_window():
    assert resolve_sample_window(0) == 0
    assert resolve_sample_window(15) == 15
    assert resolve_sample_window(30) == 30
    assert resolve_sample_window(150) == 60
    assert resolve_sample_window(356) == 100


@pytest.mark.asyncio
async def test_compute_statistics(db_session: AsyncSession, seeded_account: int):
    account = await db_session.get(Account, seeded_account)
    assert account is not None

    samples = await brain_learner.fetch_learning_samples(
        db_session, seeded_account, sample_size=5
    )
    stats = brain_learner.compute_statistics(samples, total_eligible=len(samples))

    assert stats.sample_size == 5
    assert stats.template_ranking[0].name == "口诀"
    assert stats.template_ranking[0].avg_view == 460.0
    assert stats.template_ranking[-1].name == "情绪"
    assert stats.scene_ranking[0].name == "古风"
    assert any(item.name == "20:00" for item in stats.publish_hour_ranking)
    assert stats.hook_ranking[0].name == "60岁以后"
    assert stats.hook_cta_combos[0].hook == "60岁以后"


@pytest.mark.asyncio
async def test_run_learning_for_account(
    db_session: AsyncSession, seeded_account: int
):
    learning = await brain_learner.run_learning_for_account(
        db_session, seeded_account
    )
    await db_session.commit()

    assert learning.sample_size == 5
    assert learning.summary
    assert learning.strength
    assert learning.weakness
    assert learning.stats_snapshot is not None
    assert learning.stats_snapshot["template_ranking"][0]["name"] == "口诀"

    profile = await brain_learner.get_account_profile(db_session, seeded_account)
    assert profile is not None
    assert profile.best_category == "口诀"
    assert profile.best_hook == "60岁以后"
    assert profile.best_knowledge_source == "黄帝内经"
    assert profile.platform == "wechat_channels"


@pytest.mark.asyncio
async def test_locked_fields_preserved_on_profile_refresh(
    db_session: AsyncSession, seeded_account: int
):
    await brain_learner.run_learning_for_account(db_session, seeded_account)
    profile = await brain_learner.get_account_profile(db_session, seeded_account)
    assert profile is not None
    profile.locked_fields = ["best_hook"]
    profile.best_hook = "手动锁定Hook"
    await db_session.flush()

    await brain_learner.run_learning_for_account(db_session, seeded_account)
    await db_session.commit()

    refreshed = await brain_learner.get_account_profile(db_session, seeded_account)
    assert refreshed is not None
    assert refreshed.best_hook == "手动锁定Hook"
    assert refreshed.best_category == "口诀"


@pytest.mark.asyncio
async def test_learning_marks_videos_learned(
    db_session: AsyncSession, seeded_account: int
):
    await brain_learner.run_learning_for_account(db_session, seeded_account)
    await db_session.commit()

    samples = await brain_learner.fetch_learning_samples(
        db_session, seeded_account, sample_size=5
    )
    assert all(
        sample.video.lifecycle_status == LifecycleStatus.LEARNED
        for sample in samples
    )


@pytest.mark.asyncio
async def test_get_latest_learning_api(
    client: AsyncClient,
    db_session: AsyncSession,
    seeded_account: int,
):
    await brain_learner.run_learning_for_account(db_session, seeded_account)
    await db_session.commit()

    response = await client.get(f"/accounts/{seeded_account}/learning/latest")
    assert response.status_code == 200
    data = response.json()
    assert data["account_id"] == seeded_account
    assert data["sample_size"] == 5
    assert data["stats_snapshot"]["avg_view"] == pytest.approx(340.0, rel=0.01)


@pytest.mark.asyncio
async def test_get_profile_api(
    client: AsyncClient,
    db_session: AsyncSession,
    seeded_account: int,
):
    await brain_learner.run_learning_for_account(db_session, seeded_account)
    await db_session.commit()

    response = await client.get(f"/accounts/{seeded_account}/profile")
    assert response.status_code == 200
    data = response.json()
    assert data["best_category"] == "口诀"
    assert data["best_scene"] == "古风"
    assert data["best_publish_time"] == "20:30"


@pytest.mark.asyncio
async def test_learning_latest_not_found(client: AsyncClient, account_id: int):
    response = await client.get(f"/accounts/{account_id}/learning/latest")
    assert response.status_code == 404


@pytest.mark.asyncio
async def test_run_learning_with_mocked_llm(
    db_session: AsyncSession,
    seeded_account: int,
    monkeypatch: pytest.MonkeyPatch,
):
    class MockLlmClient:
        is_configured = True

        async def complete_json(self, *, system: str, user: str) -> dict:
            return {
                "summary": "LLM 总结",
                "strength": "LLM 优势",
                "weakness": "LLM 短板",
                "trend": "LLM 趋势",
                "suggestion": "LLM 建议",
                "optimization": "LLM 优化",
            }

    learning = await brain_learner.run_learning_for_account(
        db_session,
        seeded_account,
        llm_client=MockLlmClient(),  # type: ignore[arg-type]
    )
    assert learning.summary == "LLM 总结"
    assert "策略调整建议" in learning.optimization


@pytest.mark.asyncio
async def test_run_daily_learning_for_all_accounts(
    db_session: AsyncSession,
    seeded_account: int,
):
    result = await brain_learner.run_daily_learning_for_all_accounts(db_session)
    assert result["processed"] == 1
    assert result["skipped"] == 0
    assert result["failed"] == 0


@pytest.mark.asyncio
async def test_trend_detection():
    samples = [
        VideoSample(
            video=ContentMemory(
                publish_time=datetime(2026, 1, 1, tzinfo=UTC),
                title="a",
            ),
            views=100,
        ),
        VideoSample(
            video=ContentMemory(
                publish_time=datetime(2026, 1, 2, tzinfo=UTC),
                title="b",
            ),
            views=120,
        ),
        VideoSample(
            video=ContentMemory(
                publish_time=datetime(2026, 1, 3, tzinfo=UTC),
                title="c",
            ),
            views=400,
        ),
        VideoSample(
            video=ContentMemory(
                publish_time=datetime(2026, 1, 4, tzinfo=UTC),
                title="d",
            ),
            views=450,
        ),
    ]
    stats = brain_learner.compute_statistics(samples, total_eligible=4)
    report = brain_learner._build_rule_based_report(stats, samples)
    assert "上升" in report.trend
