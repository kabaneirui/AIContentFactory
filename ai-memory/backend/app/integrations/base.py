"""Platform data adapter interface for performance sync (Phase 3)."""

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from datetime import datetime


@dataclass(frozen=True, slots=True)
class PerformanceSnapshot:
    """Normalized performance metrics from any platform adapter."""

    views: int = 0
    ctr: float | None = None
    rate_3s: float | None = None
    finish_rate: float | None = None
    average_watch: float | None = None
    likes: int = 0
    comments: int = 0
    shares: int = 0
    collects: int = 0
    forwards: int = 0
    fans_increase: int = 0
    reach_level: str | None = None
    recommend_rate: float | None = None
    engagement_rate: float | None = None


@dataclass(frozen=True, slots=True)
class PlatformVideoItem:
    """Summary of a video discovered on a platform."""

    platform_video_id: str
    title: str
    publish_time: datetime | None = None
    performance: PerformanceSnapshot | None = None
    extra: dict[str, str] = field(default_factory=dict)


class AdapterError(Exception):
    """Base error for platform adapter failures."""


class AdapterNotConfiguredError(AdapterError):
    """Raised when required credentials or settings are missing."""


class PlatformAdapter(ABC):
    """Abstract adapter for fetching video performance from a platform."""

    @property
    @abstractmethod
    def adapter_name(self) -> str:
        """Short identifier stored in sync logs."""

    @abstractmethod
    async def fetch_performance(
        self,
        *,
        account_id: int,
        video_id: int,
        platform_video_id: str | None,
    ) -> PerformanceSnapshot | None:
        """Fetch latest performance for one video.

        Return ``None`` when the platform has no data yet (manual mode).
        """

    @abstractmethod
    async def list_videos(
        self,
        *,
        account_id: int,
        since: datetime | None = None,
        limit: int = 100,
    ) -> list[PlatformVideoItem]:
        """List videos available on the platform for the account."""
