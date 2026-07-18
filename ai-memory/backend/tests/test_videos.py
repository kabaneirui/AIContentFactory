from datetime import UTC, datetime, timedelta

import pytest
from httpx import AsyncClient
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models import (
    ContentMemory,
    LifecycleStatus,
    PerformanceSyncTask,
    SyncCheckpoint,
    SyncTaskStatus,
)
from app.services import lifecycle as lifecycle_service
from app.services.performance_sync_service import list_due_sync_tasks, process_due_sync_tasks


@pytest.fixture
async def account_id(client: AsyncClient) -> int:
    response = await client.post(
        "/accounts",
        json={"name": "养生口诀号", "platform": "wechat_channels"},
    )
    return response.json()["id"]


@pytest.mark.asyncio
async def test_create_video_without_publish_time(client: AsyncClient, account_id: int):
    response = await client.post(
        f"/accounts/{account_id}/videos",
        json={
            "title": "草稿视频",
            "hook": "很多人",
            "template": "口诀",
        },
    )
    assert response.status_code == 201
    data = response.json()
    assert data["title"] == "草稿视频"
    assert data["lifecycle_status"] == "created"
    assert data["platform"] == "wechat_channels"
    assert data["performance"] is None


@pytest.mark.asyncio
async def test_create_video_with_publish_time_schedules_sync(
    client: AsyncClient, account_id: int, db_session: AsyncSession
):
    publish_time = "2026-01-15T20:00:00+08:00"
    response = await client.post(
        f"/accounts/{account_id}/videos",
        json={
            "title": "已发布视频",
            "publish_time": publish_time,
            "template": "口诀",
        },
    )
    assert response.status_code == 201
    data = response.json()
    assert data["lifecycle_status"] == "syncing"
    video_id = data["id"]

    result = await db_session.execute(
        select(PerformanceSyncTask).where(
            PerformanceSyncTask.content_memory_id == video_id
        )
    )
    tasks = list(result.scalars().all())
    assert len(tasks) == 3
    checkpoints = {task.checkpoint for task in tasks}
    assert checkpoints == {SyncCheckpoint.H1, SyncCheckpoint.H24, SyncCheckpoint.D7}
    assert all(task.status == SyncTaskStatus.PENDING for task in tasks)


@pytest.mark.asyncio
async def test_list_videos_with_filters(client: AsyncClient, account_id: int):
    await client.post(
        f"/accounts/{account_id}/videos",
        json={"title": "口诀视频A", "template": "口诀", "category": "养生"},
    )
    await client.post(
        f"/accounts/{account_id}/videos",
        json={
            "title": "情绪视频B",
            "template": "情绪",
            "category": "养生",
            "publish_time": "2026-01-15T20:00:00+08:00",
        },
    )

    response = await client.get(
        f"/accounts/{account_id}/videos",
        params={"template": "口诀", "page_size": 10},
    )
    assert response.status_code == 200
    data = response.json()
    assert data["total"] == 1
    assert data["items"][0]["title"] == "口诀视频A"


@pytest.mark.asyncio
async def test_get_video_detail(client: AsyncClient, account_id: int):
    create_resp = await client.post(
        f"/accounts/{account_id}/videos",
        json={"title": "详情测试", "hook": "老祖宗"},
    )
    video_id = create_resp.json()["id"]

    response = await client.get(f"/videos/{video_id}")
    assert response.status_code == 200
    assert response.json()["id"] == video_id
    assert response.json()["hook"] == "老祖宗"


@pytest.mark.asyncio
async def test_update_video_performance(client: AsyncClient, account_id: int):
    create_resp = await client.post(
        f"/accounts/{account_id}/videos",
        json={
            "title": "表现更新测试",
            "publish_time": "2026-01-15T20:00:00+08:00",
        },
    )
    video_id = create_resp.json()["id"]

    response = await client.patch(
        f"/videos/{video_id}/performance",
        json={"views": 420, "finish_rate": 0.35, "likes": 12},
    )
    assert response.status_code == 200
    data = response.json()
    assert data["lifecycle_status"] == "syncing"
    assert data["performance"]["views"] == 420
    assert data["performance"]["finish_rate"] == 0.35
    assert data["performance"]["likes"] == 12
    assert data["performance"]["synced_at"] is not None


@pytest.mark.asyncio
async def test_update_video_metadata_sets_platform_video_id(
    client: AsyncClient, account_id: int
):
    create_resp = await client.post(
        f"/accounts/{account_id}/videos",
        json={"title": "补填BV号测试"},
    )
    video_id = create_resp.json()["id"]
    assert create_resp.json()["platform_video_id"] is None

    response = await client.patch(
        f"/videos/{video_id}",
        json={"platform_video_id": "BV1xx4y1x7xx"},
    )
    assert response.status_code == 200
    assert response.json()["platform_video_id"] == "BV1xx4y1x7xx"

    detail = await client.get(f"/videos/{video_id}")
    assert detail.json()["platform_video_id"] == "BV1xx4y1x7xx"


@pytest.mark.asyncio
async def test_delete_video(client: AsyncClient, account_id: int):
    create_resp = await client.post(
        f"/accounts/{account_id}/videos",
        json={"title": "待删除视频"},
    )
    video_id = create_resp.json()["id"]

    delete_resp = await client.delete(f"/videos/{video_id}")
    assert delete_resp.status_code == 204

    detail = await client.get(f"/videos/{video_id}")
    assert detail.status_code == 404

    listed = await client.get(f"/accounts/{account_id}/videos")
    assert all(item["id"] != video_id for item in listed.json()["items"])


@pytest.mark.asyncio
async def test_list_videos_sort_by_views(client: AsyncClient, account_id: int):
    low = await client.post(
        f"/accounts/{account_id}/videos",
        json={"title": "低播放"},
    )
    high = await client.post(
        f"/accounts/{account_id}/videos",
        json={"title": "高播放"},
    )
    low_id = low.json()["id"]
    high_id = high.json()["id"]

    await client.patch(f"/videos/{low_id}/performance", json={"views": 10})
    await client.patch(f"/videos/{high_id}/performance", json={"views": 999})

    desc = await client.get(
        f"/accounts/{account_id}/videos",
        params={"sort_by": "views", "sort_order": "desc"},
    )
    assert desc.status_code == 200
    titles = [item["title"] for item in desc.json()["items"]]
    assert titles.index("高播放") < titles.index("低播放")

    asc = await client.get(
        f"/accounts/{account_id}/videos",
        params={"sort_by": "views", "sort_order": "asc"},
    )
    titles_asc = [item["title"] for item in asc.json()["items"]]
    assert titles_asc.index("低播放") < titles_asc.index("高播放")


@pytest.mark.asyncio
async def test_import_videos_json(client: AsyncClient, account_id: int):
    response = await client.post(
        f"/accounts/{account_id}/videos/import",
        json={
            "videos": [
                {
                    "title": "导入视频1",
                    "template": "口诀",
                    "publish_time": "2026-01-10T20:00:00+08:00",
                    "views": 300,
                },
                {
                    "title": "导入视频2",
                    "hook": "60岁以后",
                    "template": "动作",
                },
            ]
        },
    )
    assert response.status_code == 201
    data = response.json()
    assert data["imported"] == 2
    assert data["skipped"] == 0

    list_resp = await client.get(f"/accounts/{account_id}/videos")
    assert list_resp.json()["total"] == 2


@pytest.mark.asyncio
async def test_import_videos_csv(client: AsyncClient, account_id: int):
    csv_content = (
        "title,hook,template,publish_time,views\n"
        "CSV导入视频,老祖宗,口诀,2026-01-12T20:00:00+08:00,500\n"
    )
    response = await client.post(
        f"/accounts/{account_id}/videos/import/csv",
        files={"file": ("videos.csv", csv_content, "text/csv")},
    )
    assert response.status_code == 201
    data = response.json()
    assert data["imported"] == 1

    list_resp = await client.get(f"/accounts/{account_id}/videos")
    titles = {item["title"] for item in list_resp.json()["items"]}
    assert "CSV导入视频" in titles


@pytest.mark.asyncio
async def test_import_skips_duplicate_platform_video_id(
    client: AsyncClient, account_id: int
):
    payload = {
        "videos": [
            {
                "title": "第一条",
                "platform_video_id": "wx_dup_1",
                "publish_time": "2026-01-10T20:00:00+08:00",
            },
            {
                "title": "重复条",
                "platform_video_id": "wx_dup_1",
                "publish_time": "2026-01-11T20:00:00+08:00",
            },
        ]
    }
    response = await client.post(
        f"/accounts/{account_id}/videos/import",
        json=payload,
    )
    assert response.status_code == 201
    data = response.json()
    assert data["imported"] == 1
    assert data["skipped"] == 1
    assert len(data["errors"]) == 1


@pytest.mark.asyncio
async def test_lifecycle_transitions():
    assert lifecycle_service.can_transition(
        LifecycleStatus.CREATED, LifecycleStatus.PUBLISHED
    )
    assert lifecycle_service.can_transition(
        LifecycleStatus.PUBLISHED, LifecycleStatus.SYNCING
    )
    assert not lifecycle_service.can_transition(
        LifecycleStatus.CREATED, LifecycleStatus.LEARNED
    )

    with pytest.raises(lifecycle_service.InvalidLifecycleTransition):
        lifecycle_service.transition(LifecycleStatus.CREATED, LifecycleStatus.LEARNED)


@pytest.mark.asyncio
async def test_process_due_sync_tasks(db_session: AsyncSession):
    from app.models import Account

    account = Account(name="Sync测试", platform="wechat_channels")
    db_session.add(account)
    await db_session.flush()

    video = ContentMemory(
        account_id=account.id,
        platform="wechat_channels",
        title="同步任务测试",
        publish_time=datetime.now(UTC) - timedelta(hours=2),
        lifecycle_status=LifecycleStatus.SYNCING,
    )
    db_session.add(video)
    await db_session.flush()

    task = PerformanceSyncTask(
        content_memory_id=video.id,
        checkpoint=SyncCheckpoint.H1,
        due_at=datetime.now(UTC) - timedelta(minutes=5),
        status=SyncTaskStatus.PENDING,
    )
    db_session.add(task)
    await db_session.flush()

    due_tasks = await list_due_sync_tasks(db_session)
    assert len(due_tasks) == 1

    result = await process_due_sync_tasks(db_session)
    assert result["processed"] == 1
    assert result["no_data"] == 1
    assert task.status == SyncTaskStatus.COMPLETED
    assert task.completed_at is not None
