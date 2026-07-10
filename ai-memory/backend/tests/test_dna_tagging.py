import pytest
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from app.models import ContentMemory, LifecycleStatus
from app.schemas.dna import DnaTags
from app.services import dna_tagger
from app.services.llm_client import OpenAiCompatibleClient, reset_llm_client


@pytest.fixture
async def account_id(client: AsyncClient) -> int:
    response = await client.post(
        "/accounts",
        json={"name": "DNA测试号", "platform": "wechat_channels"},
    )
    return response.json()["id"]


@pytest.mark.asyncio
async def test_retag_video_rule_based(
    client: AsyncClient, account_id: int, db_session: AsyncSession
):
    create_resp = await client.post(
        f"/accounts/{account_id}/videos",
        json={
            "title": "老祖宗留下来的养阳口诀",
            "hook": "老祖宗",
            "template": "口诀",
            "knowledge_source": "黄帝内经",
            "cta": "收藏",
            "scene_style": "古风",
        },
    )
    video_id = create_resp.json()["id"]

    response = await client.post(f"/videos/{video_id}/retag")
    assert response.status_code == 200
    data = response.json()
    assert data["video_id"] == video_id
    assert data["lifecycle_status"] == "tagged"

    tags = data["dna_tags"]
    assert tags["hook_type"] == "老祖宗"
    assert tags["template"] == "口诀"
    assert tags["knowledge"] == "黄帝内经"
    assert tags["cta"] == "收藏"
    assert tags["scene"] == "古风"
    assert tags["title_type"] == "口诀型"

    DnaTags.model_validate(tags)


@pytest.mark.asyncio
async def test_retag_video_with_mocked_llm(
    client: AsyncClient, account_id: int, monkeypatch: pytest.MonkeyPatch
):
    create_resp = await client.post(
        f"/accounts/{account_id}/videos",
        json={"title": "LLM打标测试", "hook": "你知道吗"},
    )
    video_id = create_resp.json()["id"]

    class MockLlmClient:
        is_configured = True

        async def complete_json(self, *, system: str, user: str) -> dict:
            return {
                "title_type": "疑问型",
                "hook_type": "你知道吗",
                "template": "科普",
                "knowledge": "经络",
                "emotion": "好奇感",
                "scene": "数字人",
                "pacing": "快切",
                "cta": "关注",
            }

    reset_llm_client()
    monkeypatch.setattr(
        dna_tagger,
        "get_llm_client",
        lambda: MockLlmClient(),
    )

    response = await client.post(f"/videos/{video_id}/retag")
    assert response.status_code == 200
    tags = response.json()["dna_tags"]
    assert tags["hook_type"] == "你知道吗"
    assert tags["template"] == "科普"
    assert tags["emotion"] == "好奇感"


@pytest.mark.asyncio
async def test_batch_tag_videos(
    client: AsyncClient, account_id: int, db_session: AsyncSession
):
    ids: list[int] = []
    for title in ("批量打标1", "批量打标2"):
        resp = await client.post(
            f"/accounts/{account_id}/videos",
            json={"title": title, "template": "口诀"},
        )
        ids.append(resp.json()["id"])

    batch_resp = await client.post(
        f"/accounts/{account_id}/videos/batch-tag",
        json={"video_ids": ids},
    )
    assert batch_resp.status_code == 202
    data = batch_resp.json()
    assert data["queued"] == 2
    assert set(data["video_ids"]) == set(ids)

    for video_id in ids:
        retag_resp = await client.post(f"/videos/{video_id}/retag")
        assert retag_resp.json()["lifecycle_status"] == "tagged"


@pytest.mark.asyncio
async def test_batch_tag_only_untagged_by_default(
    client: AsyncClient, account_id: int, db_session: AsyncSession
):
    tagged_resp = await client.post(
        f"/accounts/{account_id}/videos",
        json={"title": "已打标", "hook": "老祖宗"},
    )
    tagged_id = tagged_resp.json()["id"]
    await client.post(f"/videos/{tagged_id}/retag")

    untagged = ContentMemory(
        account_id=account_id,
        platform="wechat_channels",
        title="未打标",
        lifecycle_status=LifecycleStatus.CREATED,
    )
    db_session.add(untagged)
    await db_session.flush()
    untagged_id = untagged.id

    batch_resp = await client.post(
        f"/accounts/{account_id}/videos/batch-tag",
        json={},
    )
    assert batch_resp.status_code == 202
    assert batch_resp.json()["queued"] == 1
    assert batch_resp.json()["video_ids"] == [untagged_id]


@pytest.mark.asyncio
async def test_list_videos_filter_by_dna_tags(
    client: AsyncClient, account_id: int, db_session: AsyncSession
):
    video_a = (
        await client.post(
            f"/accounts/{account_id}/videos",
            json={"title": "口诀A", "hook": "老祖宗", "template": "口诀"},
        )
    ).json()["id"]
    video_b = (
        await client.post(
            f"/accounts/{account_id}/videos",
            json={"title": "情绪B", "hook": "很多人", "template": "情绪"},
        )
    ).json()["id"]

    await client.post(f"/videos/{video_a}/retag")
    await client.post(f"/videos/{video_b}/retag")

    response = await client.get(
        f"/accounts/{account_id}/videos",
        params={"dna_hook_type": "老祖宗"},
    )
    assert response.status_code == 200
    data = response.json()
    assert data["total"] == 1
    assert data["items"][0]["id"] == video_a
    assert data["items"][0]["dna_tags"]["hook_type"] == "老祖宗"


@pytest.mark.asyncio
async def test_create_video_background_tagging(
    client: AsyncClient, account_id: int, db_session: AsyncSession
):
    from app.services.dna_trigger import run_video_tagging

    create_resp = await client.post(
        f"/accounts/{account_id}/videos",
        json={
            "title": "发布后自动打标",
            "hook": "60岁以后",
            "publish_time": "2026-01-15T20:00:00+08:00",
        },
    )
    video_id = create_resp.json()["id"]

    await run_video_tagging(video_id)

    video = await db_session.get(ContentMemory, video_id)
    assert video is not None
    assert video.dna_tags is not None
    assert video.dna_tags["hook_type"] == "60岁以后"
    assert video.lifecycle_status == LifecycleStatus.TAGGED


@pytest.mark.asyncio
async def test_import_returns_video_ids(client: AsyncClient, account_id: int):
    response = await client.post(
        f"/accounts/{account_id}/videos/import",
        json={
            "videos": [
                {"title": "导入打标1", "template": "口诀"},
                {"title": "导入打标2", "hook": "很多人"},
            ]
        },
    )
    assert response.status_code == 201
    data = response.json()
    assert data["imported"] == 2
    assert len(data["video_ids"]) == 2


@pytest.mark.asyncio
async def test_dna_tags_schema_rejects_invalid_llm_output():
    video = ContentMemory(
        account_id=1,
        platform="wechat_channels",
        title="测试",
        lifecycle_status=LifecycleStatus.CREATED,
    )

    class BadLlmClient:
        is_configured = True

        async def complete_json(self, *, system: str, user: str) -> dict:
            return {"hook_type": "老祖宗"}

    with pytest.raises(dna_tagger.DnaTaggingError):
        await dna_tagger.generate_dna_tags(video, llm_client=BadLlmClient())
