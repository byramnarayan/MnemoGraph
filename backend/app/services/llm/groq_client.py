from __future__ import annotations

import itertools
import json
import logging
from typing import Any
import httpx

from app.core.config import settings

logger = logging.getLogger(__name__)


class GroqClient:
    """
    OpenAI-compatible Groq Chat Completions client with thread-safe Round-Robin Key Rotation
    and automatic failover across all configured GROQ API keys.
    """

    _key_cycle: itertools.cycle | None = None
    _total_keys: int = 0
    _keys_list: list[str] = []

    def __init__(
        self,
        api_keys: list[str] | None = None,
        model: str | None = None,
        base_url: str | None = None,
        timeout: float = 30.0,
    ):
        raw_keys = api_keys or []
        if not raw_keys:
            for k in [settings.groq_api_key_1, settings.groq_api_key_2, settings.groq_api_key_3]:
                if k:
                    val = k.get_secret_value() if hasattr(k, "get_secret_value") else str(k)
                    if val.strip() and val.strip() not in raw_keys:
                        raw_keys.append(val.strip())

        self.api_keys = raw_keys
        self.model = model or settings.groq_model
        self.base_url = (base_url or settings.groq_api_base).rstrip("/")
        self.timeout = timeout

        if not GroqClient._keys_list and self.api_keys:
            GroqClient._keys_list = list(self.api_keys)
            GroqClient._total_keys = len(self.api_keys)
            GroqClient._key_cycle = itertools.cycle(range(GroqClient._total_keys))

    @classmethod
    def get_next_key_index(cls) -> int:
        """Returns the next key index in round-robin sequence."""
        if cls._key_cycle is not None:
            return next(cls._key_cycle)
        return 0

    async def chat_completion(
        self,
        messages: list[dict[str, str]],
        temperature: float = 0.1,
        max_tokens: int = 4096,
        response_format: dict[str, str] | None = None,
    ) -> str:
        """
        Calls Groq chat completion API with round-robin key rotation across every call,
        plus automated failover if the active key hits rate limits (HTTP 429) or errors.
        """
        if not self.api_keys:
            raise ValueError("No Groq API keys configured. Set GROQ_API_KEY_1, GROQ_API_KEY_2, GROQ_API_KEY_3 in .env")

        total = len(self.api_keys)
        start_idx = self.get_next_key_index() % total
        last_error = None

        payload: dict[str, Any] = {
            "model": self.model,
            "messages": messages,
            "temperature": temperature,
            "max_tokens": max_tokens,
        }
        if response_format:
            payload["response_format"] = response_format

        # Attempt up to total keys starting from the round-robin selected key
        async with httpx.AsyncClient(timeout=self.timeout) as client:
            for attempt in range(total):
                curr_idx = (start_idx + attempt) % total
                key = self.api_keys[curr_idx]
                masked_key = f"{key[:6]}...{key[-4:]}"

                headers = {
                    "Authorization": f"Bearer {key}",
                    "Content-Type": "application/json",
                }
                url = f"{self.base_url}/chat/completions"

                try:
                    logger.info(
                        f"Invoking Groq LLM (attempt {attempt + 1}/{total}, key #{curr_idx + 1} [{masked_key}], model={self.model})..."
                    )
                    res = await client.post(url, json=payload, headers=headers)

                    if res.status_code == 200:
                        data = res.json()
                        choices = data.get("choices", [])
                        if choices:
                            content = choices[0].get("message", {}).get("content", "")
                            logger.info(
                                f"Groq LLM response received successfully from key #{curr_idx + 1}."
                            )
                            return content
                        return ""

                    # If rate limited (429) or quota exhausted or 5xx, log and rotate to next key immediately
                    logger.warning(
                        f"Groq API key #{curr_idx + 1} [{masked_key}] failed with status {res.status_code}: {res.text}. Rotating to next key..."
                    )
                    last_error = RuntimeError(f"HTTP {res.status_code}: {res.text}")

                except Exception as e:
                    logger.error(f"Network error invoking Groq with key #{curr_idx + 1} [{masked_key}]: {e}. Rotating to next key...")
                    last_error = e

        raise RuntimeError(f"All {total} Groq API keys exhausted or failed. Last error: {last_error}")
