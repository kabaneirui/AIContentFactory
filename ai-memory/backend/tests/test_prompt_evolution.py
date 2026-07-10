from datetime import UTC, datetime, timedelta

import pytest
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from sqlalchemy import select

from app.models import Account, ContentMemory, ContentPerformance, LifecycleStatus
from app.services import prompt_evolver
from app.services.prompt_evolver import (
    EVOLUTION_SAMPLE_THRESHOLD,
    compute_recommend_score,
)


@pytest.fixture
async def account_id(client: AsyncClient) -> int:
    response = await client.post(
        "/accounts",
        json={"name": "Prompt测试号", "platform": "wechat_channels"},
    )
    return response.json()["id"]


async def _seed_video_with_prompt(
    db: AsyncSession,
    account_id: int,
    *,
    prompt_version: str,
    views: int,
    finish_rate: float = 0.28,
) -> ContentMemory:
    video = ContentMemory(
        account_id=account_id,
        platform="wechat_channels",
        title=f"测试视频-{prompt_version}-{views}",
        prompt=prompt_version,
        lifecycle_status=LifecycleStatus.TAGGED,
        publish_time=datetime(2026, 6, 1, 20, 0, tzinfo=UTC),
    )
    db.add(video)
    await db.flush()
    performance = ContentPerformance(
        content_memory_id=video.id,
        views=views,
        finish_rate=finish_rate,
    )
    db.add(performance)
    await db.flush()
    return video


async def test_account_creation_seeds_v1_prompt(
    client: AsyncClient,
    account_id: int,
):
    response = await client.get(f"/accounts/{account_id}/prompts")
    assert response.status_code == 200
    data = response.json()
    assert len(data["items"]) == 1
    assert data["items"][0]["version"] == "V1"
    assert data["active_version"] == "V1"
    assert data["items"][0]["is_active"] is True


def test_compute_recommend_score():
    assert compute_recommend_score(500, 300) == 5
    assert compute_recommend_score(280, 300) == 3
    assert compute_recommend_score(220, 300) == 2


async def test_refresh_version_stats(
    db_session: AsyncSession,
    account_id: int,
):
    for views in (400, 500, 600):
        await _seed_video_with_prompt(
            db_session, account_id, prompt_version="V1", views=views
        )

    result = await db_session.execute(select(Account).where(Account.id == account_id))
    account = result.scalar_one()
    version = await prompt_evolver.ensure_initial_prompt_version(db_session, account)
    await prompt_evolver.refresh_version_stats(db_session, version)

    assert version.video_count == 3
    assert version.avg_view == 500.0
    assert version.recommend_score >= 1


async def test_manual_create_and_activate_prompt(
    client: AsyncClient,
    account_id: int,
):
    create_resp = await client.post(
        f"/accounts/{account_id}/prompts",
        json={
            "prompt_content": "手动创建的 Prompt V2 内容，要求强化钩子与收藏 CTA。",
            "change_log": "手动测试版本",
            "activate": False,
        },
    )
    assert create_resp.status_code == 201
    v2 = create_resp.json()
    assert v2["version"] == "V2"
    assert v2["is_active"] is False

    activate_resp = await client.post(
        f"/accounts/{account_id}/prompts/{v2['id']}/activate"
    )
    assert activate_resp.status_code == 200
    assert activate_resp.json()["activated_version"] == "V2"
    assert activate_resp.json()["previous_version"] == "V1"

    active_resp = await client.get(f"/accounts/{account_id}/prompts/active")
    assert active_resp.json()["version"] == "V2"


async def test_evolve_prompt_force_without_llm(
    client: AsyncClient,
    db_session: AsyncSession,
    account_id: int,
):
    for index in range(EVOLUTION_SAMPLE_THRESHOLD):
        await _seed_video_with_prompt(
            db_session,
            account_id,
            prompt_version="V1",
            views=100 + index,
        )

    evolve_resp = await client.post(
        f"/accounts/{account_id}/prompts/evolve",
        json={"force": True},
    )
    assert evolve_resp.status_code == 200
    data = evolve_resp.json()
    assert data["evolved"] is True
    assert data["new_version"] is not None
    assert data["new_version"]["version"] == "V2"
    assert data["pending_review"] is True


async def test_compare_prompt_versions(
    client: AsyncClient,
    db_session: AsyncSession,
    account_id: int,
):
    await _seed_video_with_prompt(db_session, account_id, prompt_version="V1", views=200)
    await client.post(
        f"/accounts/{account_id}/prompts",
        json={
            "prompt_content": "对比测试 Prompt，更长内容以满足最小长度校验要求。",
            "change_log": "对比",
            "activate": True,
        },
    )
    await _seed_video_with_prompt(db_session, account_id, prompt_version="V2", views=500)

    compare_resp = await client.get(
        f"/accounts/{account_id}/prompts/compare",
        params={"version_a": "V1", "version_b": "V2"},
    )
    assert compare_resp.status_code == 200
    data = compare_resp.json()
    assert data["view_delta"] > 0


async def test_rollback_prompt_version(
    client: AsyncClient,
    account_id: int,
):
    v2_resp = await client.post(
        f"/accounts/{account_id}/prompts",
        json={
            "prompt_content": "回滚测试 Prompt 内容，包含足够长度以满足校验。",
            "change_log": "回滚测试",
            "activate": True,
        },
    )
    v2_id = v2_resp.json()["id"]

    list_resp = await client.get(f"/accounts/{account_id}/prompts")
    v1_id = next(v["id"] for v in list_resp.json()["items"] if v["version"] == "V1")

    rollback_resp = await client.post(
        f"/accounts/{account_id}/prompts/{v1_id}/rollback"
    )
    assert rollback_resp.status_code == 200
    assert rollback_resp.json()["activated_version"] == "V1"
    assert rollback_resp.json()["previous_version"] == "V2"

    active_resp = await client.get(f"/accounts/{account_id}/prompts/active")
    assert active_resp.json()["id"] == v1_id
