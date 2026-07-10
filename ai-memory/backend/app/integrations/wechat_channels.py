"""WeChat Channels (视频号) adapter skeleton.

Official APIs require 视频号助手开放平台 credentials and specific open capabilities
(留资、直播数据、达人罗盘等). Ordinary play/finish metrics are not freely available.
See: https://developers.weixin.qq.com/doc/oplatform/developers/product/channel/channel_management.html
"""

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

WECHAT_CHANNELS_API_BASE = "https://api.weixin.qq.com"


class WechatChannelsAdapter(PlatformAdapter):
    """Skeleton adapter for 视频号助手开放平台 (requires user-provided AppID/secret)."""

    def __init__(
        self,
        *,
        app_id: str | None,
        app_secret: str | None,
        access_token: str | None = None,
        timeout_seconds: float = 30.0,
    ) -> None:
        self._app_id = app_id
        self._app_secret = app_secret
        self._access_token = access_token
        self._timeout = timeout_seconds

    @property
    def adapter_name(self) -> str:
        return "wechat_channels"

    def _ensure_configured(self) -> None:
        if not self._app_id or not self._app_secret:
            raise AdapterNotConfiguredError(
                "WeChat Channels adapter requires WECHAT_CHANNELS_APP_ID and "
                "WECHAT_CHANNELS_APP_SECRET. Official APIs also need the account "
                "to enable the corresponding open capabilities."
            )

    async def _resolve_access_token(self) -> str:
        if self._access_token:
            return self._access_token

        self._ensure_configured()
        url = f"{WECHAT_CHANNELS_API_BASE}/cgi-bin/token"
        params = {
            "grant_type": "client_credential",
            "appid": self._app_id,
            "secret": self._app_secret,
        }
        async with httpx.AsyncClient(timeout=self._timeout) as client:
            response = await client.get(url, params=params)
            response.raise_for_status()
            payload = response.json()

        if "access_token" not in payload:
            err = payload.get("errmsg", "unknown error")
            raise AdapterNotConfiguredError(
                f"WeChat token request failed: {err}. "
                "Verify AppID/secret and open-platform permissions."
            )
        return str(payload["access_token"])

    async def fetch_performance(
        self,
        *,
        account_id: int,
        video_id: int,
        platform_video_id: str | None,
    ) -> PerformanceSnapshot | None:
        """Fetch video metrics from 视频号助手 API (stub — endpoint varies by capability)."""
        self._ensure_configured()
        if not platform_video_id:
            logger.warning(
                "WechatChannelsAdapter: video %s has no platform_video_id", video_id
            )
            return None

        token = await self._resolve_access_token()
        # Placeholder: real endpoint depends on which open capability is enabled.
        # e.g. channel video stats API when available on the account.
        url = f"{WECHAT_CHANNELS_API_BASE}/channels/ec/finder/get_finder_video_stats"
        params = {"access_token": token}
        body = {"export_id": platform_video_id}

        async with httpx.AsyncClient(timeout=self._timeout) as client:
            response = await client.post(url, params=params, json=body)
            if response.status_code == 404:
                logger.info(
                    "WechatChannelsAdapter: stats endpoint not available (404); "
                    "fall back to manual import for account %s",
                    account_id,
                )
                return None
            response.raise_for_status()
            payload = response.json()

        if payload.get("errcode", 0) != 0:
            errmsg = payload.get("errmsg", "unknown")
            logger.warning(
                "WechatChannelsAdapter API error for video %s: %s", video_id, errmsg
            )
            return None

        stats = payload.get("stats") or payload.get("data") or {}
        return PerformanceSnapshot(
            views=int(stats.get("read_count") or stats.get("views") or 0),
            likes=int(stats.get("like_count") or stats.get("likes") or 0),
            comments=int(stats.get("comment_count") or stats.get("comments") or 0),
            shares=int(stats.get("forward_count") or stats.get("shares") or 0),
            finish_rate=_optional_float(stats.get("finish_rate")),
            average_watch=_optional_float(stats.get("avg_play_time_sec")),
        )

    async def list_videos(
        self,
        *,
        account_id: int,
        since: datetime | None = None,
        limit: int = 100,
    ) -> list[PlatformVideoItem]:
        """List recent videos from the channel (stub — requires finder list API access)."""
        self._ensure_configured()
        token = await self._resolve_access_token()
        url = f"{WECHAT_CHANNELS_API_BASE}/channels/ec/finder/list_videos"
        params = {"access_token": token}
        body: dict[str, object] = {"page_size": min(limit, 50)}
        if since is not None:
            body["start_time"] = int(since.timestamp())

        async with httpx.AsyncClient(timeout=self._timeout) as client:
            response = await client.post(url, params=params, json=body)
            if response.status_code in {404, 501}:
                logger.info(
                    "WechatChannelsAdapter: list_videos not available for account %s",
                    account_id,
                )
                return []
            response.raise_for_status()
            payload = response.json()

        if payload.get("errcode", 0) != 0:
            logger.warning(
                "WechatChannelsAdapter list_videos error: %s",
                payload.get("errmsg", "unknown"),
            )
            return []

        items: list[PlatformVideoItem] = []
        for row in payload.get("video_list") or payload.get("list") or []:
            export_id = row.get("export_id") or row.get("video_id")
            if not export_id:
                continue
            items.append(
                PlatformVideoItem(
                    platform_video_id=str(export_id),
                    title=str(row.get("title") or row.get("desc") or ""),
                    publish_time=_optional_datetime(row.get("create_time")),
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
