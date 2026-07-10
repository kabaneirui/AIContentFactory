import pytest
from httpx import AsyncClient


@pytest.mark.asyncio
async def test_health_check(client: AsyncClient):
    response = await client.get("/health")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "ok"
    assert data["database"] == "ok"
    assert data["service"] == "AI Memory"


@pytest.mark.asyncio
async def test_create_account(client: AsyncClient):
    response = await client.post(
        "/accounts",
        json={"name": "养生口诀号", "platform": "wechat_channels"},
    )
    assert response.status_code == 201
    data = response.json()
    assert data["name"] == "养生口诀号"
    assert data["platform"] == "wechat_channels"
    assert "id" in data
    assert "created_at" in data


@pytest.mark.asyncio
async def test_list_accounts(client: AsyncClient):
    await client.post(
        "/accounts",
        json={"name": "账号A", "platform": "douyin"},
    )
    await client.post(
        "/accounts",
        json={"name": "账号B", "platform": "xiaohongshu"},
    )

    response = await client.get("/accounts")
    assert response.status_code == 200
    accounts = response.json()
    assert len(accounts) == 2
    names = {a["name"] for a in accounts}
    assert names == {"账号A", "账号B"}


@pytest.mark.asyncio
async def test_get_account(client: AsyncClient):
    create_resp = await client.post(
        "/accounts",
        json={"name": "测试账号", "platform": "wechat_channels"},
    )
    account_id = create_resp.json()["id"]

    response = await client.get(f"/accounts/{account_id}")
    assert response.status_code == 200
    assert response.json()["id"] == account_id


@pytest.mark.asyncio
async def test_get_account_not_found(client: AsyncClient):
    response = await client.get("/accounts/9999")
    assert response.status_code == 404


@pytest.mark.asyncio
async def test_update_account(client: AsyncClient):
    create_resp = await client.post(
        "/accounts",
        json={"name": "旧名称", "platform": "douyin"},
    )
    account_id = create_resp.json()["id"]

    response = await client.patch(
        f"/accounts/{account_id}",
        json={"name": "新名称"},
    )
    assert response.status_code == 200
    assert response.json()["name"] == "新名称"
    assert response.json()["platform"] == "douyin"


@pytest.mark.asyncio
async def test_delete_account(client: AsyncClient):
    create_resp = await client.post(
        "/accounts",
        json={"name": "待删除", "platform": "douyin"},
    )
    account_id = create_resp.json()["id"]

    response = await client.delete(f"/accounts/{account_id}")
    assert response.status_code == 204

    get_resp = await client.get(f"/accounts/{account_id}")
    assert get_resp.status_code == 404
