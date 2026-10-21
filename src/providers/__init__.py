"""Provider factory and exports."""
from __future__ import annotations

import os
from typing import Optional
from src.providers.base import BaseProvider, LLMMessage, LLMResponse, ToolCall
from src.providers.fake_provider import FakeProvider
from src.providers.openai_provider import OpenAIProvider
from src.providers.gemini_provider import GeminiProvider
from src.providers.anthropic_provider import AnthropicProvider


def get_provider(
    provider_name: Optional[str] = None,
    model: Optional[str] = None,
    api_key: Optional[str] = None,
) -> BaseProvider:
    """Factory to instantiate the appropriate provider."""
    name = (provider_name or os.getenv("LLM_PROVIDER", "fake")).strip().lower()

    if name == "gemini":
        m = model or os.getenv("LLM_MODEL", "gemini-2.5-flash")
        return GeminiProvider(api_key=api_key, model=m)
    elif name == "openai":
        m = model or os.getenv("LLM_MODEL", "gpt-4o")
        return OpenAIProvider(api_key=api_key, model=m)
    elif name == "anthropic":
        m = model or os.getenv("LLM_MODEL", "claude-3-5-sonnet-20241022")
        return AnthropicProvider(api_key=api_key, model=m)
    elif name == "fake":
        return FakeProvider()
    else:
        raise ValueError(f"Unknown provider name: {provider_name!r}")
