"""Anthropic provider implementation supporting tool use."""
from __future__ import annotations

import json
import os
from typing import Any, Optional
import requests

from src.providers.base import BaseProvider, LLMMessage, LLMResponse, ToolCall


class AnthropicProvider(BaseProvider):
    def __init__(
        self,
        api_key: Optional[str] = None,
        model: str = "claude-3-5-sonnet-20241022",
    ):
        self.api_key = api_key or os.getenv("ANTHROPIC_API_KEY", "")
        self.model = model

    def chat_completion(
        self,
        messages: list[LLMMessage],
        tools: list[dict[str, Any]],
        timeout_seconds: float,
    ) -> LLMResponse:
        if not self.api_key:
            raise ValueError("ANTHROPIC_API_KEY is not set")

        url = "https://api.anthropic.com/v1/messages"
        headers = {
            "x-api-key": self.api_key,
            "anthropic-version": "2023-06-01",
            "Content-Type": "application/json",
        }

        system_prompt: Optional[str] = None
        anthropic_messages: list[dict[str, Any]] = []

        for m in messages:
            if m.role == "system":
                system_prompt = m.content
            elif m.role == "user":
                anthropic_messages.append({"role": "user", "content": m.content or ""})
            elif m.role == "assistant":
                content_blocks: list[dict[str, Any]] = []
                if m.content:
                    content_blocks.append({"type": "text", "text": m.content})
                for tc in m.tool_calls:
                    content_blocks.append({
                        "type": "tool_use",
                        "id": tc.id,
                        "name": tc.name,
                        "input": tc.arguments,
                    })
                anthropic_messages.append({"role": "assistant", "content": content_blocks})
            elif m.role == "tool":
                anthropic_messages.append({
                    "role": "user",
                    "content": [{
                        "type": "tool_result",
                        "tool_use_id": m.tool_call_id or "unknown",
                        "content": m.content or "",
                    }],
                })

        payload: dict[str, Any] = {
            "model": self.model,
            "messages": anthropic_messages,
            "max_tokens": 4096,
            "temperature": 0.0,
        }

        if system_prompt:
            payload["system"] = system_prompt

        if tools:
            payload["tools"] = [
                {
                    "name": t["name"],
                    "description": t["description"],
                    "input_schema": t.get("parameters", {}),
                }
                for t in tools
            ]

        response = requests.post(
            url,
            headers=headers,
            json=payload,
            timeout=timeout_seconds,
        )

        if response.status_code != 200:
            raise RuntimeError(
                f"Anthropic API error {response.status_code}: {response.text}"
            )

        data = response.json()
        content_blocks = data.get("content", [])

        text_pieces: list[str] = []
        tool_calls: list[ToolCall] = []

        for b in content_blocks:
            if b.get("type") == "text":
                text_pieces.append(b.get("text", ""))
            elif b.get("type") == "tool_use":
                tool_calls.append(
                    ToolCall(
                        id=b["id"],
                        name=b["name"],
                        arguments=b.get("input", {}),
                    )
                )

        combined_text = "".join(text_pieces) if text_pieces else None
        usage = data.get("usage", {})

        return LLMResponse(
            content=combined_text,
            tool_calls=tool_calls,
            prompt_tokens=usage.get("input_tokens"),
            completion_tokens=usage.get("output_tokens"),
            raw_response=data,
        )
