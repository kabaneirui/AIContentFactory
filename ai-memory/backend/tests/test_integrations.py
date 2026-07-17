"""Phase 3: platform adapter and performance sync tests."""

from datetime import UTC, datetime, timedelta
from unittest.mock import AsyncMock, MagicMock

import pytest
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from app.integrations.base import AdapterNotConfiguredError, PerformanceSnapshot
from app.integrations.bilibili import BilibiliAdapter
from app.integrations.manual import ManualAdapter
from app.integrations.registry import get_adapter_for_account
from app.integrations.wechat_channels import WechatChannelsAdapter
from app.models import (
    Account,
    ContentMemory,
    ContentPerformance,
    LifecycleStatus,
    PerformanceSyncTask,
    SyncCheckpoint,
    SyncLogStatus,
    SyncTaskStatus,
)
from app.services.performance_apply_service import (
    apply_performance_snapshot,
    sync_video_by_id,
    sync_video_performance,
)
from app.services.performance_sync_service import list_due_sync_tasks, process_due_sync_tasks


@pytest.fixture
async def account_id(client: AsyncClient) -> int:
    response = await client.post(
        "/accounts", json={"name": "适配器测试", "platform": "wechat_channels"}
    )
    assert response.status_code == 201
    return response.json()["id"]


@pytest.mark.asyncio
async def test_manual_adapter_returns_none_without_performance(db_session: AsyncSession):
    account = Account(name="Manual", platform="manual")
    db_session.add(account)
    await db_session.flush()

    video = ContentMemory(
        account_id=account.id,
        platform="manual",
        title="无表现数据",
        platform_video_id="vid-001",
    )
    db_session.add(video)
    await db_session.flush()

    adapter = ManualAdapter(db_session)
    snapshot = await adapter.fetch_performance(
        account_id=account.id,
        video_id=video.id,
        platform_video_id=video.platform_video_id,
    )
    assert snapshot is None


@pytest.mark.asyncio
async def test_manual_adapter_reads_stored_performance(db_session: AsyncSession):
    account = Account(name="Manual", platform="manual")
    db_session.add(account)
    await db_session.flush()

    video = ContentMemory(
        account_id=account.id,
        platform="manual",
        title="有表现数据",
        platform_video_id="vid-002",
    )
    db_session.add(video)
    await db_session.flush()

    perf = ContentPerformance(content_memory_id=video.id, views=999, likes=10)
    db_session.add(perf)
    await db_session.flush()

    adapter = ManualAdapter(db_session)
    snapshot = await adapter.fetch_performance(
        account_id=account.id,
        video_id=video.id,
        platform_video_id=video.platform_video_id,
    )
    assert snapshot is not None
    assert snapshot.views == 999
    assert snapshot.likes == 10


@pytest.mark.asyncio
async def test_registry_defaults_to_manual_adapter(db_session: AsyncSession):
    account = Account(name="WC", platform="wechat_channels")
    db_session.add(account)
    await db_session.flush()

    adapter = get_adapter_for_account(account, db_session)
    assert adapter.adapter_name == "manual"


@pytest.mark.asyncio
async def test_wechat_adapter_requires_credentials():
    adapter = WechatChannelsAdapter(app_id=None, app_secret=None)
    with pytest.raises(AdapterNotConfiguredError):
        adapter._ensure_configured()


@pytest.mark.asyncio
async def test_bilibili_adapter_requires_credentials():
    adapter = BilibiliAdapter(app_key=None, app_secret=None)
    with pytest.raises(AdapterNotConfiguredError):
        adapter._ensure_configured()


@pytest.mark.asyncio
async def test_registry_bilibili_adapter_when_enabled(db_session: AsyncSession):
    from app.config import Settings

    account = Account(name="B站号", platform="bilibili")
    db_session.add(account)
    await db_session.flush()

    settings = Settings(bilibili_enabled=True)
    adapter = get_adapter_for_account(account, db_session, settings=settings)
    assert adapter.adapter_name == "bilibili"


@pytest.mark.asyncio
async def test_registry_bilibili_falls_back_to_manual_when_disabled(
    db_session: AsyncSession,
):
    from app.config import Settings

    account = Account(name="B站号停用", platform="bilibili")
    db_session.add(account)
    await db_session.flush()

    settings = Settings(bilibili_enabled=False)
    adapter = get_adapter_for_account(account, db_session, settings=settings)
    assert adapter.adapter_name == "manual"


@pytest.mark.asyncio
async def test_bilibili_fetch_performance_without_bvid_returns_none():
    adapter = BilibiliAdapter(app_key=None, app_secret=None)
    result = await adapter.fetch_performance(
        account_id=1, video_id=1, platform_video_id=None
    )
    assert result is None


@pytest.mark.asyncio
async def test_bilibili_list_videos_requires_credentials():
    adapter = BilibiliAdapter(app_key=None, app_secret=None)
    with pytest.raises(AdapterNotConfiguredError):
        await adapter.list_videos(account_id=1)


@pytest.mark.asyncio
async def test_create_bilibili_account(client: AsyncClient):
    response = await client.post(
        "/accounts",
        json={"name": "B站知识号", "platform": "bilibili"},
    )
    assert response.status_code == 201
    assert response.json()["platform"] == "bilibili"


@pytest.mark.asyncio
async def test_sync_video_no_data_creates_log(db_session: AsyncSession):
    account = Account(name="Sync", platform="manual")
    db_session.add(account)
    await db_session.flush()

    video = ContentMemory(
        account_id=account.id,
        platform="manual",
        title="待同步",
        publish_time=datetime.now(UTC),
        lifecycle_status=LifecycleStatus.SYNCING,
    )
    db_session.add(video)
    await db_session.flush()

    sync_log = await sync_video_performance(db_session, video, account)
    assert sync_log.status == SyncLogStatus.NO_DATA
    assert sync_log.adapter == "manual"
    assert video.performance is None


@pytest.mark.asyncio
async def test_sync_video_applies_manual_performance(db_session: AsyncSession):
    account = Account(name="Sync", platform="manual")
    db_session.add(account)
    await db_session.flush()

    video = ContentMemory(
        account_id=account.id,
        platform="manual",
        title="已录入",
        publish_time=datetime.now(UTC),
        lifecycle_status=LifecycleStatus.SYNCING,
    )
    db_session.add(video)
    await db_session.flush()

    db_session.add(
        ContentPerformance(content_memory_id=video.id, views=500, finish_rate=0.4)
    )
    await db_session.flush()

    sync_log = await sync_video_performance(db_session, video, account)
    assert sync_log.status == SyncLogStatus.SUCCESS
    assert video.performance is not None
    assert video.performance.views == 500
    assert video.performance.synced_at is not None


@pytest.mark.asyncio
async def test_apply_performance_snapshot_creates_record(db_session: AsyncSession):
    account = Account(name="Apply", platform="manual")
    db_session.add(account)
    await db_session.flush()

    video = ContentMemory(
        account_id=account.id,
        platform="manual",
        title="新建表现",
    )
    db_session.add(video)
    await db_session.flush()

    snapshot = PerformanceSnapshot(views=120, likes=3, finish_rate=0.25)
    perf = await apply_performance_snapshot(db_session, video, snapshot)
    assert perf.views == 120
    assert perf.likes == 3
    assert perf.finish_rate == 0.25


@pytest.mark.asyncio
async def test_process_due_sync_tasks_with_adapter(db_session: AsyncSession):
    account = Account(name="Worker", platform="manual")
    db_session.add(account)
    await db_session.flush()

    video = ContentMemory(
        account_id=account.id,
        platform="manual",
        title="定时同步",
        publish_time=datetime.now(UTC) - timedelta(hours=2),
        lifecycle_status=LifecycleStatus.SYNCING,
    )
    db_session.add(video)
    await db_session.flush()

    db_session.add(
        ContentPerformance(content_memory_id=video.id, views=300)
    )
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
    assert result["failed"] == 0
    assert task.status == SyncTaskStatus.COMPLETED
    assert task.completed_at is not None


@pytest.mark.asyncio
async def test_process_due_sync_tasks_no_data(db_session: AsyncSession):
    account = Account(name="Worker", platform="manual")
    db_session.add(account)
    await db_session.flush()

    video = ContentMemory(
        account_id=account.id,
        platform="manual",
        title="无数据同步",
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

    result = await process_due_sync_tasks(db_session)
    assert result["processed"] == 1
    assert result["no_data"] == 1
    assert task.status == SyncTaskStatus.COMPLETED


@pytest.mark.asyncio
async def test_sync_video_with_mock_adapter(db_session: AsyncSession):
    account = Account(name="Mock", platform="manual")
    db_session.add(account)
    await db_session.flush()

    video = ContentMemory(
        account_id=account.id,
        platform="manual",
        title="Mock 同步",
        platform_video_id="ext-1",
    )
    db_session.add(video)
    await db_session.flush()

    mock_adapter = MagicMock()
    mock_adapter.adapter_name = "mock_platform"
    mock_adapter.fetch_performance = AsyncMock(
        return_value=PerformanceSnapshot(views=777, likes=22)
    )

    sync_log = await sync_video_performance(
        db_session, video, account, adapter=mock_adapter
    )
    assert sync_log.status == SyncLogStatus.SUCCESS
    assert sync_log.adapter == "mock_platform"
    assert video.performance.views == 777


@pytest.mark.asyncio
async def test_trigger_sync_api(client: AsyncClient, account_id: int):
    create_resp = await client.post(
        f"/accounts/{account_id}/videos",
        json={
            "title": "API 同步测试",
            "publish_time": datetime.now(UTC).isoformat(),
            "platform_video_id": "api-vid-1",
        },
    )
    video_id = create_resp.json()["id"]

    sync_resp = await client.post(f"/videos/{video_id}/sync")
    assert sync_resp.status_code == 200
    data = sync_resp.json()
    assert data["video_id"] == video_id
    assert data["performance_updated"] is False
    assert data["sync_log"]["status"] == "no_data"
    assert data["sync_log"]["adapter"] == "manual"


@pytest.mark.asyncio
async def test_trigger_sync_api_after_performance_update(
    client: AsyncClient, account_id: int
):
    create_resp = await client.post(
        f"/accounts/{account_id}/videos",
        json={"title": "PATCH 后同步", "platform_video_id": "api-vid-2"},
    )
    video_id = create_resp.json()["id"]

    await client.patch(
        f"/videos/{video_id}/performance",
        json={"views": 888, "likes": 5},
    )

    sync_resp = await client.post(f"/videos/{video_id}/sync")
    assert sync_resp.status_code == 200
    data = sync_resp.json()
    assert data["performance_updated"] is True
    assert data["sync_log"]["status"] == "success"

    detail = await client.get(f"/videos/{video_id}")
    assert detail.json()["performance"]["views"] == 888


@pytest.mark.asyncio
async def test_list_sync_logs_api(client: AsyncClient, account_id: int):
    create_resp = await client.post(
        f"/accounts/{account_id}/videos",
        json={"title": "日志测试"},
    )
    video_id = create_resp.json()["id"]

    await client.post(f"/videos/{video_id}/sync")
    await client.post(f"/videos/{video_id}/sync")

    logs_resp = await client.get(f"/videos/{video_id}/sync-logs")
    assert logs_resp.status_code == 200
    logs = logs_resp.json()
    assert logs["total"] == 2
    assert all(item["adapter"] == "manual" for item in logs["items"])


@pytest.mark.asyncio
async def test_sync_video_by_id(db_session: AsyncSession):
    account = Account(name="ById", platform="manual")
    db_session.add(account)
    await db_session.flush()

    video = ContentMemory(
        account_id=account.id,
        platform="manual",
        title="by id",
    )
    db_session.add(video)
    await db_session.flush()

    db_session.add(ContentPerformance(content_memory_id=video.id, views=42))
    await db_session.flush()

    sync_log = await sync_video_by_id(db_session, video.id, account_id=account.id)
    assert sync_log.status == SyncLogStatus.SUCCESS
