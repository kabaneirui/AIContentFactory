from datetime import date, timedelta

import pytest
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.trend_topic import TrendTopic
from app.schemas.trend import TrendDirection
from app.services import trend_analyzer, trend_service


@pytest.mark.asyncio
async def test_create_and_list_trends(client: AsyncClient):
    response = await client.post(
        "/trends",
        json={
            "topic": "夏季养心",
            "category": "养生",
            "heat_score": 85.0,
            "season": "夏至",
            "source": "manual",
        },
    )
    assert response.status_code == 201
    body = response.json()
    assert body["topic"] == "夏季养心"
    assert body["heat_score"] == 85.0
    assert body["season"] == "夏至"

    list_response = await client.get("/trends", params={"season": "夏至"})
    assert list_response.status_code == 200
    data = list_response.json()
    assert data["total"] >= 1
    assert any(item["topic"] == "夏季养心" for item in data["items"])


@pytest.mark.asyncio
async def test_import_trends_json(client: AsyncClient):
    response = await client.post(
        "/trends/import",
        json={
            "trends": [
                {
                    "topic": "三伏天祛湿",
                    "category": "养生",
                    "heat_score": 72.0,
                    "season": "大暑",
                },
                {
                    "topic": "秋季润肺",
                    "category": "养生",
                    "heat_score": 68.0,
                    "season": "立秋",
                },
            ]
        },
    )
    assert response.status_code == 200
    result = response.json()
    assert result["imported"] == 2
    assert result["errors"] == []


def test_compute_direction():
    assert trend_analyzer.compute_direction(110, [80, 85, 90]) == TrendDirection.RISING
    assert trend_analyzer.compute_direction(70, [80, 85, 90]) == TrendDirection.FALLING
    assert trend_analyzer.compute_direction(85, [80, 85, 90]) == TrendDirection.STABLE
    assert trend_analyzer.compute_direction(50, []) == TrendDirection.STABLE


@pytest.mark.asyncio
async def test_trend_direction_with_history(db_session: AsyncSession):
    today = date.today()
    older = today - timedelta(days=3)
    db_session.add_all(
        [
            TrendTopic(
                topic="经络疏通",
                category="养生",
                heat_score=60.0,
                source="manual",
                trend_date=older,
            ),
            TrendTopic(
                topic="经络疏通",
                category="养生",
                heat_score=65.0,
                source="manual",
                trend_date=older + timedelta(days=1),
            ),
            TrendTopic(
                topic="经络疏通",
                category="养生",
                heat_score=90.0,
                source="manual",
                trend_date=today,
            ),
        ]
    )
    await db_session.commit()

    items, _total = await trend_service.list_trends(db_session, limit=10)
    record, _direction = items[0]
    direction = await trend_analyzer.resolve_trend_direction(db_session, record)
    assert direction == TrendDirection.RISING


@pytest.mark.asyncio
async def test_get_matching_trends_by_season(db_session: AsyncSession):
    today = date.today()
    db_session.add_all(
        [
            TrendTopic(
                topic="夏至养心",
                category="养生",
                heat_score=80.0,
                source="manual",
                trend_date=today,
                season="夏至",
            ),
            TrendTopic(
                topic="无关热点",
                category="娱乐",
                heat_score=99.0,
                source="manual",
                trend_date=today,
            ),
        ]
    )
    await db_session.commit()

    matched = await trend_analyzer.get_matching_trends(
        db_session,
        season="夏至",
        limit=5,
    )
    assert matched
    assert matched[0][0].topic == "夏至养心"
