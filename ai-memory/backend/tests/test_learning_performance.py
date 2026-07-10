"""Brain Learning 性能验收：单账号 500 条视频学习 < 2 分钟。"""

import time
from datetime import UTC, datetime, timedelta

import pytest
from sqlalchemy.ext.asyncio import AsyncSession

from app.models import Account, ContentMemory, ContentPerformance, LifecycleStatus
from app.services import brain_learner

LEARNING_TIME_LIMIT_SECONDS = 120
VIDEO_COUNT = 500


@pytest.mark.performance
@pytest.mark.asyncio
async def test_learning_performance_500_videos(db_session: AsyncSession):
    account = Account(name="性能测试号", platform="wechat_channels")
    db_session.add(account)
    await db_session.flush()

    base_time = datetime(2025, 1, 1, 20, 0, tzinfo=UTC)
    templates = ("口诀", "动作", "情绪")
    hooks = ("老祖宗", "很多人", "你知道吗")

    for index in range(VIDEO_COUNT):
        video = ContentMemory(
            account_id=account.id,
            platform="wechat_channels",
            title=f"性能视频{index:04d}",
            hook=hooks[index % len(hooks)],
            template=templates[index % len(templates)],
            knowledge_source="黄帝内经",
            scene_style="古风",
            cta="收藏",
            duration=30 + (index % 10),
            publish_time=base_time + timedelta(days=index),
            dna_tags={
                "title_type": "口诀型",
                "hook_type": hooks[index % len(hooks)],
                "template": templates[index % len(templates)],
                "knowledge": "黄帝内经",
                "emotion": "获得感",
                "scene": "古风",
                "pacing": "快切",
                "cta": "收藏",
            },
            lifecycle_status=LifecycleStatus.TAGGED,
            prompt="V1",
        )
        db_session.add(video)
        await db_session.flush()
        db_session.add(
            ContentPerformance(
                content_memory_id=video.id,
                views=150 + (index % 50) * 10,
                finish_rate=0.25,
            )
        )

    await db_session.flush()

    started = time.perf_counter()
    learning = await brain_learner.run_learning_for_account(db_session, account.id)
    elapsed = time.perf_counter() - started

    assert learning.sample_size == 100
    assert elapsed < LEARNING_TIME_LIMIT_SECONDS, (
        f"Learning took {elapsed:.1f}s, limit is {LEARNING_TIME_LIMIT_SECONDS}s"
    )
