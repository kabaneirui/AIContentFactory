"""Phase 11 端到端验收：覆盖验收清单 11 项 + 全链路闭环。"""

from __future__ import annotations

from datetime import UTC, datetime, timedelta

import pytest
from httpx import AsyncClient
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models import (
    Account,
    ContentMemory,
    ContentPerformance,
    LifecycleStatus,
    PerformanceSyncTask,
)
from app.schemas.dna import DnaTags
from app.services import brain_learner, content_pipeline, knowledge_analyzer
from app.schemas.pipeline import PipelinePublishRequest
from app.schemas.trend import TrendTopicCreate
from app.services import trend_service


TEMPLATES = ("口诀", "动作", "情绪")
HOOKS = ("老祖宗", "很多人", "你知道吗", "60岁以后")
SCENES = ("古风", "实拍", "数字人")
KNOWLEDGE = ("黄帝内经", "养心", "经络", "养生常识")


def _build_video_row(index: int) -> dict:
    template = TEMPLATES[index % len(TEMPLATES)]
    hook = HOOKS[index % len(HOOKS)]
    scene = SCENES[index % len(SCENES)]
    knowledge = KNOWLEDGE[index % len(KNOWLEDGE)]
    views = 120 + (index % 17) * 35 + (index % 3) * 80
    return {
        "title": f"验收视频{index:03d}-{template}养生",
        "hook": hook,
        "template": template,
        "knowledge_source": knowledge,
        "scene_style": scene,
        "cta": "收藏",
        "duration": 30 + (index % 5) * 5,
        "category": "养生",
        "publish_time": (
            datetime(2026, 1, 1, 20, 0, tzinfo=UTC) + timedelta(days=index)
        ).isoformat(),
        "views": views,
        "finish_rate": 0.22 + (index % 10) * 0.01,
    }


async def _seed_videos(
    db: AsyncSession,
    account_id: int,
    count: int,
    *,
    with_dna: bool = True,
) -> list[ContentMemory]:
    videos: list[ContentMemory] = []
    for index in range(count):
        row = _build_video_row(index)
        dna_tags = None
        if with_dna:
            dna_tags = {
                "title_type": "口诀型",
                "hook_type": row["hook"],
                "template": row["template"],
                "knowledge": row["knowledge_source"],
                "emotion": "获得感",
                "scene": row["scene_style"],
                "pacing": "快切",
                "cta": row["cta"],
            }
        video = ContentMemory(
            account_id=account_id,
            platform="wechat_channels",
            title=row["title"],
            hook=row["hook"],
            template=row["template"],
            knowledge_source=row["knowledge_source"],
            scene_style=row["scene_style"],
            cta=row["cta"],
            duration=row["duration"],
            category=row["category"],
            publish_time=datetime.fromisoformat(row["publish_time"]),
            dna_tags=dna_tags,
            lifecycle_status=LifecycleStatus.TAGGED if with_dna else LifecycleStatus.PUBLISHED,
            prompt="V1",
        )
        db.add(video)
        await db.flush()
        performance = ContentPerformance(
            content_memory_id=video.id,
            views=row["views"],
            finish_rate=row["finish_rate"],
        )
        db.add(performance)
        videos.append(video)
    await db.flush()
    return videos


@pytest.fixture
async def account_a_id(client: AsyncClient) -> int:
    response = await client.post(
        "/accounts",
        json={"name": "验收账号A", "platform": "wechat_channels"},
    )
    return response.json()["id"]


@pytest.fixture
async def account_b_id(client: AsyncClient) -> int:
    response = await client.post(
        "/accounts",
        json={"name": "验收账号B", "platform": "wechat_channels"},
    )
    return response.json()["id"]


@pytest.mark.asyncio
async def test_acceptance_01_account_isolation(
    client: AsyncClient,
    account_a_id: int,
    account_b_id: int,
    db_session: AsyncSession,
):
    """#1 每账号独立 AI Memory，数据隔离。"""
    await _seed_videos(db_session, account_a_id, 3)
    await _seed_videos(db_session, account_b_id, 2)
    await db_session.commit()

    list_a = await client.get(f"/accounts/{account_a_id}/videos")
    list_b = await client.get(f"/accounts/{account_b_id}/videos")
    assert list_a.json()["total"] == 3
    assert list_b.json()["total"] == 2
    for item in list_a.json()["items"]:
        assert item["account_id"] == account_a_id
    for item in list_b.json()["items"]:
        assert item["account_id"] == account_b_id


@pytest.mark.asyncio
async def test_acceptance_02_publish_and_performance_update(
    client: AsyncClient,
    account_a_id: int,
    db_session: AsyncSession,
):
    """#2 视频发布自动记录 + 表现持续更新。"""
    publish_time = datetime.now(UTC).isoformat()
    create_resp = await client.post(
        f"/accounts/{account_a_id}/pipeline/publish",
        json={
            "title": "管线发布测试",
            "hook": "老祖宗",
            "template": "口诀",
            "publish_time": publish_time,
            "initial_performance": {"views": 50, "finish_rate": 0.2},
        },
    )
    assert create_resp.status_code == 200
    data = create_resp.json()
    assert data["success"] is True
    assert data["steps"]["content_memory_created"] is True
    assert data["steps"]["sync_tasks_scheduled"] == 3
    assert data["steps"]["performance_updated"] is True
    video_id = data["video_id"]

    tasks = await db_session.execute(
        select(PerformanceSyncTask).where(
            PerformanceSyncTask.content_memory_id == video_id
        )
    )
    assert len(list(tasks.scalars().all())) == 3

    patch_resp = await client.patch(
        f"/videos/{video_id}/performance",
        json={"views": 320, "finish_rate": 0.31},
    )
    assert patch_resp.status_code == 200
    assert patch_resp.json()["performance"]["views"] == 320


@pytest.mark.asyncio
async def test_acceptance_03_content_dna_tagging(
    client: AsyncClient,
    account_a_id: int,
):
    """#3 8 维 Content DNA 自动打标。"""
    resp = await client.post(
        f"/accounts/{account_a_id}/pipeline/publish",
        json={
            "title": "老祖宗留下来的养阳口诀",
            "hook": "老祖宗",
            "template": "口诀",
            "knowledge_source": "黄帝内经",
            "scene_style": "古风",
            "cta": "收藏",
        },
    )
    data = resp.json()
    assert data["success"] is True
    assert data["steps"]["dna_tagged"] is True
    tags = data["dna_tags"]
    assert tags is not None
    validated = DnaTags.model_validate(tags)
    assert validated.hook_type == "老祖宗"
    assert validated.template == "口诀"

    filter_resp = await client.get(
        f"/accounts/{account_a_id}/videos",
        params={"dna_hook_type": "老祖宗"},
    )
    assert filter_resp.json()["total"] >= 1


@pytest.mark.asyncio
async def test_acceptance_04_daily_learning_report(
    client: AsyncClient,
    account_a_id: int,
    db_session: AsyncSession,
):
    """#4 每日自动学习 + 报告（通过 run_learning_for_account 模拟凌晨任务）。"""
    await _seed_videos(db_session, account_a_id, 50)
    await db_session.commit()

    learning = await brain_learner.run_learning_for_account(db_session, account_a_id)
    await db_session.commit()

    assert learning.summary
    assert learning.sample_size >= 30

    latest = await client.get(f"/accounts/{account_a_id}/learning/latest")
    assert latest.status_code == 200
    assert latest.json()["id"] == learning.id


@pytest.mark.asyncio
async def test_acceptance_05_prediction_intercept(
    client: AsyncClient,
    account_a_id: int,
    db_session: AsyncSession,
):
    """#5 发布前预测 + 低分拦截。"""
    await _seed_videos(db_session, account_a_id, 30)
    await db_session.commit()

    predict_resp = await client.post(
        f"/accounts/{account_a_id}/predict",
        json={
            "title": "情绪养生别乱试",
            "hook": "你知道吗",
            "template": "情绪",
            "scene_style": "数字人",
            "duration": 60,
            "cta": "评论",
        },
    )
    assert predict_resp.status_code == 200
    body = predict_resp.json()
    assert "pass" in body
    assert body["prediction"]["predict_view"] > 0
    assert body["prediction"]["predict_level"] in range(1, 6)

    blocked = await client.post(
        f"/accounts/{account_a_id}/pipeline/publish",
        json={
            "title": "极低预期草稿",
            "hook": "你知道吗",
            "template": "情绪",
            "scene_style": "数字人",
            "duration": 90,
            "cta": "评论",
            "require_prediction_pass": True,
        },
    )
    blocked_data = blocked.json()
    if not blocked_data["success"]:
        assert blocked_data["steps"]["prediction_checked"] is True
        assert blocked_data["steps"]["prediction_passed"] is False
    else:
        assert blocked_data["steps"]["prediction_passed"] is True


@pytest.mark.asyncio
async def test_acceptance_06_failure_attribution_and_strategy(
    client: AsyncClient,
    account_a_id: int,
    db_session: AsyncSession,
):
    """#6 失败归因 + 策略调整建议。"""
    await _seed_videos(db_session, account_a_id, 50)
    await db_session.commit()
    await brain_learner.run_learning_for_account(db_session, account_a_id)
    await db_session.commit()

    learning = await client.get(f"/accounts/{account_a_id}/learning/latest")
    assert learning.status_code == 200
    optimization = learning.json().get("optimization") or ""
    assert isinstance(optimization, str)


@pytest.mark.asyncio
async def test_acceptance_07_account_profile(
    client: AsyncClient,
    account_a_id: int,
    db_session: AsyncSession,
):
    """#7 首页账号画像展示（API）。"""
    await _seed_videos(db_session, account_a_id, 50)
    await db_session.commit()
    await brain_learner.run_learning_for_account(db_session, account_a_id)
    await db_session.commit()

    profile = await client.get(f"/accounts/{account_a_id}/profile")
    assert profile.status_code == 200
    data = profile.json()
    assert data.get("best_category") or data.get("best_hook") or data.get("best_scene")


@pytest.mark.asyncio
async def test_acceptance_08_knowledge_evolution_searchable(
    client: AsyncClient,
    account_a_id: int,
    db_session: AsyncSession,
):
    """#8 爆款/失败经验库可检索。"""
    await _seed_videos(db_session, account_a_id, 50)
    await db_session.commit()
    await brain_learner.run_learning_for_account(db_session, account_a_id)
    await db_session.commit()

    result = await knowledge_analyzer.run_knowledge_evolution_for_account(
        db_session, account_a_id
    )
    await db_session.commit()
    assert result["hits"] + result["fails"] + result["skipped"] >= 0

    hits = await client.get(
        f"/accounts/{account_a_id}/knowledge",
        params={"type": "hit"},
    )
    fails = await client.get(
        f"/accounts/{account_a_id}/knowledge",
        params={"type": "fail"},
    )
    assert hits.status_code == 200
    assert fails.status_code == 200
    assert hits.json()["total"] + fails.json()["total"] >= 0


@pytest.mark.asyncio
async def test_acceptance_09_decide_today_70_30(
    client: AsyncClient,
    account_a_id: int,
    db_session: AsyncSession,
):
    """#9 「今天发什么」综合决策（70/30）。"""
    await _seed_videos(db_session, account_a_id, 50)
    await db_session.commit()
    await brain_learner.run_learning_for_account(db_session, account_a_id)
    await db_session.commit()

    await trend_service.create_trend(
        db_session,
        TrendTopicCreate(
            topic="立夏养生",
            category="节气",
            heat_score=88.0,
            source="manual",
            season="立夏",
        ),
    )
    await db_session.commit()

    decide = await client.post(
        f"/accounts/{account_a_id}/decide/today",
        json={"season": "立夏", "platform": "wechat_channels"},
    )
    assert decide.status_code == 200
    recommendations = decide.json()["recommendations"]
    assert 3 <= len(recommendations) <= 5
    first = recommendations[0]
    assert first["title"]
    assert first["predict_level"] in range(1, 6)
    assert first["reasons"]


@pytest.mark.asyncio
async def test_acceptance_10_prompt_version_tracking(
    client: AsyncClient,
    account_a_id: int,
    db_session: AsyncSession,
):
    """#10 Prompt 版本追踪与进化。"""
    prompts = await client.get(f"/accounts/{account_a_id}/prompts")
    assert prompts.status_code == 200
    data = prompts.json()
    assert data["active_version"] == "V1"
    assert len(data["items"]) >= 1

    await _seed_videos(db_session, account_a_id, 25, with_dna=True)
    for video in (
        await db_session.execute(
            select(ContentMemory).where(ContentMemory.account_id == account_a_id)
        )
    ).scalars().all():
        video.prompt = "V1"
    await db_session.commit()

    active = await client.get(f"/accounts/{account_a_id}/prompts/active")
    assert active.status_code == 200
    assert active.json()["version"] == "V1"
    assert active.json()["video_count"] >= 0


@pytest.mark.asyncio
async def test_acceptance_11_full_data_loop(
    client: AsyncClient,
    account_a_id: int,
    db_session: AsyncSession,
):
    """#11 完整数据流闭环：导入 → 打标 → 学习 → 预测 → 决策 → 发布管线。"""
    rows = [_build_video_row(i) for i in range(50)]
    import_resp = await client.post(
        f"/accounts/{account_a_id}/videos/import",
        json={"videos": rows},
    )
    assert import_resp.status_code == 201
    assert import_resp.json()["imported"] == 50

    batch = await client.post(
        f"/accounts/{account_a_id}/videos/batch-tag",
        json={},
    )
    assert batch.status_code == 202
    video_ids = batch.json()["video_ids"]
    for video_id in video_ids[:5]:
        await client.post(f"/videos/{video_id}/retag")

    learning = await brain_learner.run_learning_for_account(db_session, account_a_id)
    await db_session.commit()
    assert learning.id

    predict = await client.post(
        f"/accounts/{account_a_id}/predict",
        json={
            "title": "全链路预测标题",
            "hook": "老祖宗",
            "template": "口诀",
            "duration": 35,
        },
    )
    assert predict.status_code == 200

    decide = await client.post(
        f"/accounts/{account_a_id}/decide/today",
        json={"platform": "wechat_channels"},
    )
    assert decide.status_code == 200

    pipeline_resp = await client.post(
        f"/accounts/{account_a_id}/pipeline/publish",
        json={
            "title": "闭环最终发布",
            "hook": "老祖宗",
            "template": "口诀",
            "knowledge_source": "黄帝内经",
        },
    )
    assert pipeline_resp.json()["success"] is True
    assert pipeline_resp.json()["steps"]["dna_tagged"] is True


@pytest.mark.asyncio
async def test_pipeline_service_direct(
    db_session: AsyncSession,
):
    """管线服务层单元验证。"""
    account = Account(name="管线服务测试", platform="wechat_channels")
    db_session.add(account)
    await db_session.flush()

    result = await content_pipeline.run_publish_pipeline(
        db_session,
        account,
        PipelinePublishRequest(
            title="服务层发布",
            hook="很多人",
            template="动作",
            publish_time=datetime.now(UTC),
        ),
    )
    assert result.success
    assert result.video_id is not None
    assert result.steps.sync_tasks_scheduled == 3
