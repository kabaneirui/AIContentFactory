import json
import logging
import re
from typing import Protocol

import httpx

from app.config import Settings, get_settings

logger = logging.getLogger(__name__)


class LlmClient(Protocol):
    async def complete_json(self, *, system: str, user: str) -> dict: ...


class OpenAiCompatibleClient:
    """OpenAI 兼容 Chat Completions 客户端。"""

    def __init__(self, settings: Settings) -> None:
        self._api_key = settings.openai_api_key
        self._base_url = settings.openai_base_url.rstrip("/")
        self._model = settings.openai_model
        self._timeout = settings.openai_timeout_seconds

    @property
    def is_configured(self) -> bool:
        return bool(self._api_key)

    async def complete_json(self, *, system: str, user: str) -> dict:
        if not self.is_configured:
            raise RuntimeError("OpenAI API key is not configured")

        headers = {
            "Authorization": f"Bearer {self._api_key}",
            "Content-Type": "application/json",
        }
        payload = {
            "model": self._model,
            "messages": [
                {"role": "system", "content": system},
                {"role": "user", "content": user},
            ],
            "temperature": 0.2,
            "response_format": {"type": "json_object"},
        }

        async with httpx.AsyncClient(timeout=self._timeout) as client:
            response = await client.post(
                f"{self._base_url}/chat/completions",
                headers=headers,
                json=payload,
            )
            response.raise_for_status()
            data = response.json()

        content = data["choices"][0]["message"]["content"]
        return _parse_json_content(content)


def _parse_json_content(content: str) -> dict:
    text = content.strip()
    fence_match = re.search(r"```(?:json)?\s*([\s\S]*?)\s*```", text)
    if fence_match:
        text = fence_match.group(1).strip()
    parsed = json.loads(text)
    if not isinstance(parsed, dict):
        raise ValueError("LLM response must be a JSON object")
    return parsed


_llm_client: OpenAiCompatibleClient | None = None


def get_llm_client() -> OpenAiCompatibleClient:
    return OpenAiCompatibleClient(get_settings())


def reset_llm_client() -> None:
    """测试用：保留兼容接口（客户端已改为每次读取最新配置）。"""
    global _llm_client
    _llm_client = None
