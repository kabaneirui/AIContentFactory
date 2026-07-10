"""Platform data adapters (Phase 3)."""

from app.integrations.base import (
    AdapterError,
    AdapterNotConfiguredError,
    PerformanceSnapshot,
    PlatformAdapter,
    PlatformVideoItem,
)
from app.integrations.manual import ManualAdapter
from app.integrations.registry import get_adapter_for_account
from app.integrations.wechat_channels import WechatChannelsAdapter

__all__ = [
    "AdapterError",
    "AdapterNotConfiguredError",
    "ManualAdapter",
    "PerformanceSnapshot",
    "PlatformAdapter",
    "PlatformVideoItem",
    "WechatChannelsAdapter",
    "get_adapter_for_account",
]
