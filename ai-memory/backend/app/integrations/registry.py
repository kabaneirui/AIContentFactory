"""Resolve the platform adapter for an account."""

from sqlalchemy.ext.asyncio import AsyncSession

from app.config import Settings, get_settings
from app.integrations.base import PlatformAdapter
from app.integrations.bilibili import BilibiliAdapter
from app.integrations.manual import ManualAdapter
from app.integrations.wechat_channels import WechatChannelsAdapter
from app.models.account import Account

WECHAT_CHANNELS_PLATFORM = "wechat_channels"
BILIBILI_PLATFORM = "bilibili"


def get_adapter_for_account(
    account: Account,
    db: AsyncSession,
    *,
    settings: Settings | None = None,
) -> PlatformAdapter:
    """Pick adapter by account platform and global integration settings."""
    cfg = settings or get_settings()

    if (
        account.platform == WECHAT_CHANNELS_PLATFORM
        and cfg.wechat_channels_enabled
        and cfg.wechat_channels_app_id
        and cfg.wechat_channels_app_secret
    ):
        return WechatChannelsAdapter(
            app_id=cfg.wechat_channels_app_id,
            app_secret=cfg.wechat_channels_app_secret,
            access_token=cfg.wechat_channels_access_token,
            timeout_seconds=cfg.wechat_channels_timeout_seconds,
        )

    if account.platform == BILIBILI_PLATFORM and cfg.bilibili_enabled:
        # 公开播放量数据无需凭证；app_key/secret 只用于需要授权的创作者接口。
        return BilibiliAdapter(
            app_key=cfg.bilibili_app_key,
            app_secret=cfg.bilibili_app_secret,
            access_token=cfg.bilibili_access_token,
            timeout_seconds=cfg.bilibili_timeout_seconds,
        )

    return ManualAdapter(db)
