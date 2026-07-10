from datetime import UTC, datetime, timedelta

import pytest
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from app.models import Account, ContentMemory, ContentPerformance, LifecycleStatus
from app.services import brain_learner, knowledge_analyzer, predictor, strategy_optimizer
from app.services.knowledge_analyzer import classify_video
from app.services.predictor import compute_error_rate


@pytest.fixture
async def account_id(client: AsyncClient) -> int:
    response = await client.post(
        "/accounts",
        json={"name": "预测测试号", "platform": "wechat_channels"},
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
    rate_3s: float | None = None,
    finish_rate: float | None = 0.28,
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
        rate_3s=rate_3s,
        finish_rate=finish_rate,
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


def test_classify_video():
    assert classify_video(500, p25=200, p75=400) is not None
    assert classify_video(500, p25=200, p75=400).value == "hit"
    assert classify_video(100, p25=200, p75=400).value == "fail"
    assert classify_video(300, p25=200, p75=400) is None


def test_compute_error_rate():
    assert compute_error_rate(400, 420) == pytest.approx(0.05)
    assert compute_error_rate(0, 100) == 1.0


@pytest.mark.asyncio
async def test_predict_high_score_content(
    db_session: AsyncSession,
    seeded_account: int,
):
    from app.schemas.prediction import PredictRequest

    await brain_learner.run_learning_for_account(db_session, seeded_account)
    await db_session.commit()

    account = await db_session.get(Account, seeded_account)
    assert account is not None

    result, _dna = await predictor.predict_content(
        db_session,
        account,
        PredictRequest(
            title="老祖宗留下来的养阳口诀",
            template="口诀",
            hook="老祖宗",
            knowledge_source="黄帝内经",
            scene_style="古风",
            cta="收藏",
            duration=32,
        ),
    )
    assert result.predict_view >= result.threshold
    assert result.passed is True
    assert 1 <= result.predict_level <= 5
    assert result.reason


@pytest.mark.asyncio
async def test_predict_low_score_content(
    db_session: AsyncSession,
    seeded_account: int,
):
    await brain_learner.run_learning_for_account(db_session, seeded_account)
    await db_session.commit()

    account = await db_session.get(Account, seeded_account)
    assert account is not None

    from app.schemas.prediction import PredictRequest

    result, _dna = await predictor.predict_content(
        db_session,
        account,
        PredictRequest(
            title="情绪养生别乱试",
            template="情绪",
            hook="你知道吗",
            knowledge_source="养生常识",
            scene_style="数字人",
            cta="评论",
            duration=60,
        ),
    )
    assert result.predict_level <= 3
    assert result.reason


@pytest.mark.asyncio
async def test_predict_api(
    client: AsyncClient,
    db_session: AsyncSession,
    seeded_account: int,
):
    await brain_learner.run_learning_for_account(db_session, seeded_account)
    await db_session.commit()

    response = await client.post(
        f"/accounts/{seeded_account}/predict",
        json={
            "title": "60岁以后要这样睡",
            "template": "口诀",
            "hook": "60岁以后",
            "knowledge_source": "黄帝内经",
            "scene_style": "古风",
            "cta": "收藏",
            "duration": 30,
        },
    )
    assert response.status_code == 200
    data = response.json()
    assert "pass" in data
    assert data["prediction_id"] > 0
    assert data["prediction"]["predict_view"] > 0
    assert isinstance(data["prediction"]["reason"], list)


@pytest.mark.asyncio
async def test_calibrate_prediction_api(
    client: AsyncClient,
    db_session: AsyncSession,
    seeded_account: int,
):
    await brain_learner.run_learning_for_account(db_session, seeded_account)
    await db_session.commit()

    predict_response = await client.post(
        f"/accounts/{seeded_account}/predict",
        json={
            "title": "经络疏通小动作",
            "template": "动作",
            "hook": "很多人",
            "knowledge_source": "经络",
            "scene_style": "实拍",
            "cta": "收藏",
            "duration": 35,
        },
    )
    prediction_id = predict_response.json()["prediction_id"]
    predicted_view = predict_response.json()["prediction"]["predict_view"]

    video = await _seed_video(
        db_session,
        seeded_account,
        title="发布后校准",
        views=410,
        finish_rate=0.31,
    )
    await db_session.commit()

    response = await client.patch(
        f"/predictions/{prediction_id}",
        json={
            "video_id": video.id,
            "actual_view": 410,
            "actual_finish_rate": 0.31,
        },
    )
    assert response.status_code == 200
    data = response.json()
    assert data["actual_view"] == 410
    assert data["video_id"] == video.id
    assert data["error_rate"] == pytest.approx(
        abs(410 - predicted_view) / predicted_view,
        rel=0.01,
    )


@pytest.mark.asyncio
async def test_custom_predict_threshold(
    client: AsyncClient,
    db_session: AsyncSession,
    seeded_account: int,
):
    await brain_learner.run_learning_for_account(db_session, seeded_account)
    await db_session.commit()

    await client.patch(
        f"/accounts/{seeded_account}",
        json={"predict_threshold": 1000},
    )

    response = await client.post(
        f"/accounts/{seeded_account}/predict",
        json={
            "title": "老祖宗留下来的养阳口诀",
            "template": "口诀",
            "hook": "老祖宗",
            "knowledge_source": "黄帝内经",
            "scene_style": "古风",
            "cta": "收藏",
            "duration": 32,
        },
    )
    data = response.json()
    assert data["pass"] is False
    assert data["prediction"]["threshold"] == 1000
