"""Google Gemini provider implementation supporting function calling."""
from __future__ import annotations

import json
import os
from typing import Any, Optional
import requests

from src.providers.base import BaseProvider, LLMMessage, LLMResponse, ToolCall


class GeminiProvider(BaseProvider):
    def __init__(
        self,
        api_key: Optional[str] = None,
        model: str = "gemini-2.5-flash",
    ):
        self.api_key = api_key or os.getenv("GEMINI_API_KEY", "")
        self.model = model

    def chat_completion(
        self,
        messages: list[LLMMessage],
        tools: list[dict[str, Any]],
        timeout_seconds: float,
    ) -> LLMResponse:
        if not self.api_key:
            raise ValueError("GEMINI_API_KEY is not set")

        url = f"https://generativelanguage.googleapis.com/v1beta/models/{self.model}:generateContent?key={self.api_key}"

        # Convert LLMMessage list to Gemini contents
        contents: list[dict[str, Any]] = []
        system_instruction: Optional[dict[str, Any]] = None

        for m in messages:
            if m.role == "system":
                system_instruction = {"parts": [{"text": m.content or ""}]}
            elif m.role == "user":
                contents.append({"role": "user", "parts": [{"text": m.content or ""}]})
            elif m.role == "assistant":
                parts: list[dict[str, Any]] = []
                if m.content:
                    parts.append({"text": m.content})
                for tc in m.tool_calls:
                    parts.append({
                        "functionCall": {
                            "name": tc.name,
                            "args": tc.arguments,
                        }
                    })
                contents.append({"role": "model", "parts": parts})
            elif m.role == "tool":
                # Function response in Gemini
                try:
                    resp_obj = json.loads(m.content or "{}")
                except Exception:
                    resp_obj = {"result": m.content}
                contents.append({
                    "role": "function",
                    "parts": [{
                        "functionResponse": {
                            "name": m.name or "get_brand_facts",
                            "response": resp_obj,
                        }
                    }]
                })

        payload: dict[str, Any] = {
            "contents": contents,
            "generationConfig": {
                "temperature": 0.0,
            },
        }

        if system_instruction:
            payload["systemInstruction"] = system_instruction

        if tools:
            # Map tools to Gemini functionDeclarations
            declarations = []
            for t in tools:
                declarations.append({
                    "name": t["name"],
                    "description": t["description"],
                    "parameters": t.get("parameters", {}),
                })
            payload["tools"] = [{"functionDeclarations": declarations}]

        response = requests.post(
            url,
            headers={"Content-Type": "application/json"},
            json=payload,
            timeout=timeout_seconds,
        )

        if response.status_code != 200:
            raise RuntimeError(
                f"Gemini API error {response.status_code}: {response.text}"
            )

        data = response.json()
        candidates = data.get("candidates", [])
        if not candidates:
            raise RuntimeError(f"No candidates returned from Gemini: {data}")

        first_candidate = candidates[0]
        content_obj = first_candidate.get("content", {})
        parts = content_obj.get("parts", [])

        text_content_pieces: list[str] = []
        tool_calls: list[ToolCall] = []

        for p in parts:
            if "text" in p:
                text_content_pieces.append(p["text"])
            if "functionCall" in p:
                fc = p["functionCall"]
                tool_calls.append(
                    ToolCall(
                        id=f"call_{fc['name']}",
                        name=fc["name"],
                        arguments=fc.get("args", {}),
                    )
                )

        combined_text = "".join(text_content_pieces) if text_content_pieces else None
        usage_meta = data.get("usageMetadata", {})

        return LLMResponse(
            content=combined_text,
            tool_calls=tool_calls,
            prompt_tokens=usage_meta.get("promptTokenCount"),
            completion_tokens=usage_meta.get("candidatesTokenCount"),
            raw_response=data,
        )
