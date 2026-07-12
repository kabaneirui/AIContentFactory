import pytest
from httpx import AsyncClient


@pytest.fixture
async def account_id(client: AsyncClient) -> int:
    response = await client.post(
        "/accounts",
        json={"name": "工作流测试号", "platform": "wechat_channels"},
    )
    return response.json()["id"]


@pytest.mark.asyncio
async def test_generate_script_rule_fallback(client: AsyncClient, account_id: int):
    response = await client.post(
        f"/accounts/{account_id}/workflow/generate-script",
        json={
            "title": "夏季养心三件事",
            "hook": "老祖宗",
            "template": "口诀",
            "knowledge_source": "黄帝内经",
            "scene_style": "古风",
            "duration": 35,
            "cta": "收藏",
            "reasons": ["口诀类历史表现最好"],
        },
    )
    assert response.status_code == 200
    data = response.json()
    assert data["generated_by"] in {"llm", "rule"}
    assert data["title"]
    assert len(data["script"]) >= 20
    assert data["hook"] == "老祖宗"
