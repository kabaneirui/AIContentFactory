"""Bilibili (B站) adapter.

`fetch_performance` uses B站的公开稿件详情接口
(``/x/web-interface/view``)，该接口无需任何登录凭证即可拿到
播放/点赞/评论/转发/收藏等公开数据，只需要视频的 BV 号
（写入 ``platform_video_id`` 字段）。

`list_videos`（批量拉取账号稿件列表）依赖创作者中心的授权接口，
仍需要 哔哩哔哩开放平台 的 app key / secret / access token，
见 https://openhome.bilibili.com/doc 。未配置时会直接报错，
调用方应回退到手动导入。
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

# B站公开接口会拒绝没有 User-Agent 的请求。
_PUBLIC_HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
        "(KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36"
    ),
    "Referer": "https://www.bilibili.com",
}


class BilibiliAdapter(PlatformAdapter):
    """B站适配器：公开播放数据 + （可选）创作者中心稿件列表。"""

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
                "该功能需要 BILIBILI_APP_KEY / BILIBILI_APP_SECRET（哔哩哔哩开放平台凭证），"
                "播放量等公开数据同步无需此配置。"
            )

    async def fetch_performance(
        self,
        *,
        account_id: int,
        video_id: int,
        platform_video_id: str | None,
    ) -> PerformanceSnapshot | None:
        """通过公开接口拉取稿件的播放/点赞/评论/分享/收藏数据（无需凭证）。"""
        if not platform_video_id:
            logger.info(
                "BilibiliAdapter: video %s has no platform_video_id (BV号)，跳过同步",
                video_id,
            )
            return None

        bvid = platform_video_id.strip()
        params: dict[str, str] = (
            {"bvid": bvid} if bvid.upper().startswith("BV") else {"aid": bvid}
        )

        async with httpx.AsyncClient(timeout=self._timeout) as client:
            response = await client.get(
                f"{BILIBILI_OPEN_API_BASE}/x/web-interface/view",
                params=params,
                headers=_PUBLIC_HEADERS,
            )
            if response.status_code == 404:
                logger.info(
                    "BilibiliAdapter: video %s (bv=%s) not found on Bilibili",
                    video_id,
                    bvid,
                )
                return None
            response.raise_for_status()
            payload = response.json()

        if payload.get("code", 0) != 0:
            logger.warning(
                "BilibiliAdapter API error for video %s (bv=%s): %s",
                video_id,
                bvid,
                payload.get("message") or payload.get("msg") or "unknown",
            )
            return None

        data = payload.get("data") or {}
        stat = data.get("stat") or {}
        return PerformanceSnapshot(
            views=int(stat.get("view") or 0),
            likes=int(stat.get("like") or 0),
            comments=int(stat.get("reply") or 0),
            shares=int(stat.get("share") or 0),
            collects=int(stat.get("favorite") or 0),
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

    async def list_videos(
        self,
        *,
        account_id: int,
        since: datetime | None = None,
        limit: int = 100,
    ) -> list[PlatformVideoItem]:
        """List recent uploads (requires creator archive list API access)."""
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


def _optional_datetime(value: object) -> datetime | None:
    if value is None:
        return None
    try:
        ts = int(value)
        return datetime.fromtimestamp(ts)
    except (TypeError, ValueError, OSError):
        return None
