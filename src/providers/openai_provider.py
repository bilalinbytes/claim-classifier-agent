"""OpenAI provider implementation supporting chat completions and function calling."""
from __future__ import annotations

import json
import os
from typing import Any, Optional
import requests

from src.providers.base import BaseProvider, LLMMessage, LLMResponse, ToolCall


class OpenAIProvider(BaseProvider):
    def __init__(
        self,
        api_key: Optional[str] = None,
        model: str = "gpt-4o",
        base_url: str = "https://api.openai.com/v1",
    ):
        self.api_key = api_key or os.getenv("OPENAI_API_KEY", "")
        self.model = model
        self.base_url = base_url.rstrip("/")

    def chat_completion(
        self,
        messages: list[LLMMessage],
        tools: list[dict[str, Any]],
        timeout_seconds: float,
    ) -> LLMResponse:
        if not self.api_key:
            raise ValueError("OPENAI_API_KEY is not set")

        url = f"{self.base_url}/chat/completions"
        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json",
        }

        # Format messages for OpenAI
        openai_messages: list[dict[str, Any]] = []
        for m in messages:
            msg_dict: dict[str, Any] = {"role": m.role}
            if m.content is not None:
                msg_dict["content"] = m.content
            if m.tool_calls:
                msg_dict["tool_calls"] = [
                    {
                        "id": tc.id,
                        "type": "function",
                        "function": {
                            "name": tc.name,
                            "arguments": json.dumps(tc.arguments),
                        },
                    }
                    for tc in m.tool_calls
                ]
            if m.tool_call_id:
                msg_dict["tool_call_id"] = m.tool_call_id
            if m.name:
                msg_dict["name"] = m.name
            openai_messages.append(msg_dict)

        payload: dict[str, Any] = {
            "model": self.model,
            "messages": openai_messages,
            "temperature": 0.0,
        }

        if tools:
            payload["tools"] = [
                {"type": "function", "function": t} for t in tools
            ]
            payload["tool_choice"] = "auto"

        response = requests.post(
            url,
            headers=headers,
            json=payload,
            timeout=timeout_seconds,
        )

        if response.status_code != 200:
            raise RuntimeError(
                f"OpenAI API error {response.status_code}: {response.text}"
            )

        data = response.json()
        choice = data["choices"][0]["message"]

        content = choice.get("content")
        tool_calls: list[ToolCall] = []

        if "tool_calls" in choice and choice["tool_calls"]:
            for tc in choice["tool_calls"]:
                fn = tc["function"]
                fn_args = json.loads(fn.get("arguments", "{}"))
                tool_calls.append(
                    ToolCall(
                        id=tc["id"],
                        name=fn["name"],
                        arguments=fn_args,
                    )
                )

        usage = data.get("usage", {})
        return LLMResponse(
            content=content,
            tool_calls=tool_calls,
            prompt_tokens=usage.get("prompt_tokens"),
            completion_tokens=usage.get("completion_tokens"),
            raw_response=data,
        )
