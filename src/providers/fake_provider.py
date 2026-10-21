"""Fake provider for deterministic testing of tool calling, error handling, and timeout."""
from __future__ import annotations

import time
from typing import Any, Callable, Optional, Union
from src.providers.base import BaseProvider, LLMMessage, LLMResponse, ToolCall


class FakeProvider(BaseProvider):
    """Configurable mock provider that records calls and returns scripted responses."""

    def __init__(
        self,
        responses: Optional[list[Union[LLMResponse, Exception, Callable[[list[LLMMessage]], LLMResponse]]]] = None,
        artificial_delay: float = 0.0,
    ):
        self.responses = list(responses) if responses else []
        self.call_history: list[dict[str, Any]] = []
        self.artificial_delay = artificial_delay
        self.turn_count = 0

    def chat_completion(
        self,
        messages: list[LLMMessage],
        tools: list[dict[str, Any]],
        timeout_seconds: float,
    ) -> LLMResponse:
        self.turn_count += 1
        record = {
            "turn": self.turn_count,
            "messages": [m.to_dict() for m in messages],
            "tools": tools,
            "timeout_seconds": timeout_seconds,
        }
        self.call_history.append(record)

        if self.artificial_delay > timeout_seconds:
            time.sleep(timeout_seconds + 0.05)
            raise TimeoutError(f"Request timed out after {timeout_seconds}s")
        elif self.artificial_delay > 0:
            time.sleep(self.artificial_delay)

        if not self.responses:
            # Default empty json output
            return LLMResponse(content='{"claims": []}')

        resp = self.responses.pop(0)

        if isinstance(resp, Exception):
            raise resp
        elif callable(resp):
            return resp(messages)
        return resp
