"""Bilibili (B站) adapter skeleton.

Creator data APIs require 哔哩哔哩开放平台 credentials (app key / secret)
and authorized scopes for video analytics. Ordinary BV links do not expose
full creator metrics without the open platform.

See: https://openhome.bilibili.com/doc
"""

from __future__ import annotations

import logging
from datetime import datetime

import httpx

from app.integrations.base import (
    AdapterNotConfiguredError,
    PerformanceSnapshot,
    PlatformAdapter,
    PlatformVideoItem,
)

logger = logging.getLogger(__name__)

BILIBILI_API_BASE = "https://member.bilibili.com"
BILIBILI_OPEN_API_BASE = "https://api.bilibili.com"


class BilibiliAdapter(PlatformAdapter):
    """Skeleton adapter for B站开放平台 / 创作中心数据接口."""

    def __init__(
        self,
        *,
        app_key: str | None,
        app_secret: str | None,
        access_token: str | None = None,
        timeout_seconds: float = 30.0,
    ) -> None:
        self._app_key = app_key
        self._app_secret = app_secret
        self._access_token = access_token
        self._timeout = timeout_seconds

    @property
    def adapter_name(self) -> str:
        return "bilibili"

    def _ensure_configured(self) -> None:
        if not self._app_key or not self._app_secret:
            raise AdapterNotConfiguredError(
                "Bilibili adapter requires BILIBILI_APP_KEY and "
                "BILIBILI_APP_SECRET. Official creator APIs also need the "
                "account to authorize the corresponding open-platform scopes."
            )

    async def _resolve_access_token(self) -> str:
        if self._access_token:
            return self._access_token

        self._ensure_configured()
        # Placeholder: real OAuth token exchange depends on open-platform app type.
        raise AdapterNotConfiguredError(
            "Bilibili adapter needs BILIBILI_ACCESS_TOKEN (or a completed OAuth flow). "
            "Set BILIBILI_ACCESS_TOKEN after authorizing the creator account."
        )

    async def fetch_performance(
        self,
        *,
        account_id: int,
        video_id: int,
        platform_video_id: str | None,
    ) -> PerformanceSnapshot | None:
        """Fetch B站稿件数据（骨架：需开放平台权限后对接真实接口）。"""
        self._ensure_configured()
        if not platform_video_id:
            logger.warning(
                "BilibiliAdapter: video %s has no platform_video_id (bvid/aid)", video_id
            )
            return None

        token = await self._resolve_access_token()
        # Placeholder endpoint — replace with the authorized analytics API.
        url = f"{BILIBILI_OPEN_API_BASE}/x/web-interface/view"
        params = {"bvid": platform_video_id} if platform_video_id.startswith("BV") else {
            "aid": platform_video_id
        }
        headers = {"Authorization": f"Bearer {token}"}

        async with httpx.AsyncClient(timeout=self._timeout) as client:
            response = await client.get(url, params=params, headers=headers)
            if response.status_code in {401, 403, 404}:
                logger.info(
                    "BilibiliAdapter: stats unavailable (%s) for account %s; "
                    "fall back to manual import",
                    response.status_code,
                    account_id,
                )
                return None
            response.raise_for_status()
            payload = response.json()

        if payload.get("code", 0) != 0:
            logger.warning(
                "BilibiliAdapter API error for video %s: %s",
                video_id,
                payload.get("message") or payload.get("msg") or "unknown",
            )
            return None

        data = payload.get("data") or {}
        stat = data.get("stat") or data.get("stats") or {}
        return PerformanceSnapshot(
            views=int(stat.get("view") or stat.get("views") or 0),
            likes=int(stat.get("like") or stat.get("likes") or 0),
            comments=int(stat.get("reply") or stat.get("comments") or 0),
            shares=int(stat.get("share") or stat.get("shares") or 0),
            collects=int(stat.get("favorite") or stat.get("collects") or 0),
            finish_rate=_optional_float(stat.get("finish_rate")),
            average_watch=_optional_float(stat.get("avg_play_time")),
        )

    async def list_videos(
        self,
        *,
        account_id: int,
        since: datetime | None = None,
        limit: int = 100,
    ) -> list[PlatformVideoItem]:
        """List recent uploads (stub — requires creator archive list API access)."""
        self._ensure_configured()
        token = await self._resolve_access_token()
        url = f"{BILIBILI_API_BASE}/x/web/archives"
        headers = {"Authorization": f"Bearer {token}"}
        params: dict[str, object] = {"pn": 1, "ps": min(limit, 50)}
        if since is not None:
            params["start_time"] = int(since.timestamp())

        async with httpx.AsyncClient(timeout=self._timeout) as client:
            response = await client.get(url, params=params, headers=headers)
            if response.status_code in {401, 403, 404, 501}:
                logger.info(
                    "BilibiliAdapter: list_videos not available for account %s",
                    account_id,
                )
                return []
            response.raise_for_status()
            payload = response.json()

        if payload.get("code", 0) != 0:
            logger.warning(
                "BilibiliAdapter list_videos error: %s",
                payload.get("message") or payload.get("msg") or "unknown",
            )
            return []

        items: list[PlatformVideoItem] = []
        archives = (
            (payload.get("data") or {}).get("arc_audits")
            or (payload.get("data") or {}).get("archives")
            or (payload.get("data") or {}).get("list")
            or []
        )
        for row in archives:
            archive = row.get("Archive") or row.get("archive") or row
            bvid = archive.get("bvid") or archive.get("BV") or archive.get("aid")
            if not bvid:
                continue
            items.append(
                PlatformVideoItem(
                    platform_video_id=str(bvid),
                    title=str(archive.get("title") or ""),
                    publish_time=_optional_datetime(
                        archive.get("ptime") or archive.get("pubdate")
                    ),
                )
            )
        return items[:limit]


def _optional_float(value: object) -> float | None:
    if value is None:
        return None
    try:
        return float(value)
    except (TypeError, ValueError):
        return None


def _optional_datetime(value: object) -> datetime | None:
    if value is None:
        return None
    try:
        ts = int(value)
        return datetime.fromtimestamp(ts)
    except (TypeError, ValueError, OSError):
        return None
