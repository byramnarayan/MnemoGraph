from __future__ import annotations

from app.services.llm.groq_client import GroqClient


class LLMProviderFactory:
    """Factory for instantiating LLM clients."""

    @staticmethod
    def get_client() -> GroqClient:
        return GroqClient()

