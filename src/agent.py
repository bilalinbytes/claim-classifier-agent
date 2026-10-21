"""Agent module orchestrating LLM tool calling, quote location, and claim validation."""
from __future__ import annotations

import json
import re
import time
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Optional

from src.config import DEFAULT_TIMEOUT_SECONDS, MAX_TURNS, PROMPTS_DIR
from src.data_loader import BrandFact
from src.providers.base import BaseProvider, LLMMessage, ToolCall
from src.scorer import AnswerOutcome
from src.tools import TOOL_DEFINITIONS, ToolExecutionError, execute_tool_call
from src.validator import validate_claims_list


FORBIDDEN_INPUT_KEYS = {
    "gold",
    "claims",
    "claim_id",
    "start_char",
    "end_char",
    "expected_label",
    "evidence_fact_ids",
    "explanation",
    "difficulty_tags",
    "claims_list",
}


class InputValidationError(Exception):
    """Raised when forbidden gold or claim-list fields are passed to agent."""
    pass


class AgentExecutionError(Exception):
    """Raised when turn limit exhausted, invalid model output, or unrecoverable error occurs."""
    pass


def validate_agent_input(input_data: dict[str, Any]) -> None:
    """Ensure no gold, span, label, or claims data enters the inference path."""
    for key in input_data.keys():
        lower_key = key.lower()
        if lower_key in FORBIDDEN_INPUT_KEYS or "gold" in lower_key or "claim" in lower_key:
            raise InputValidationError(f"Forbidden field in agent request: {key!r}")

    required = ["answer_id", "brand_id", "question", "ai_answer"]
    for req in required:
        if req not in input_data or not isinstance(input_data[req], str):
            raise InputValidationError(f"Missing or invalid required input field: {req!r}")


def locate_quote(ai_answer: str, quote: str, current_search_idx: int = 0) -> tuple[int, int]:
    """Locate the exact character span [start, end) of a quote in ai_answer.

    Model never counts offsets; Python resolves exact Unicode code-point offsets.
    Handles repeated quotes by maintaining sequential scan position.
    """
    clean_quote = quote.strip()
    if not clean_quote:
        raise ValueError("Cannot locate empty quote")

    # First attempt: search starting from current sequential index
    pos = ai_answer.find(clean_quote, current_search_idx)
    if pos != -1:
        return pos, pos + len(clean_quote)

    # Second attempt: search anywhere in ai_answer
    pos = ai_answer.find(clean_quote)
    if pos != -1:
        return pos, pos + len(clean_quote)

    # Third attempt: whitespace-flexible search if exact matching fails due to internal spacing
    pattern = re.escape(clean_quote)
    pattern = re.sub(r'\\\s+', r'\\s+', pattern)
    match = re.search(pattern, ai_answer)
    if match:
        return match.start(), match.end()

    raise ValueError(f"Quote not found in ai_answer: {clean_quote!r}")


def parse_model_claims_json(raw_text: str) -> list[dict[str, Any]]:
    """Parse JSON output from the model, extracting the claims list."""
    cleaned = raw_text.strip()

    # 1. Try direct JSON parse
    try:
        data = json.loads(cleaned)
    except json.JSONDecodeError:
        data = None

    # 2. Try extracting from markdown code block
    if data is None:
        code_match = re.search(r"```(?:json)?\s*(\{.*?\})\s*```", cleaned, re.DOTALL)
        if code_match:
            try:
                data = json.loads(code_match.group(1))
            except json.JSONDecodeError:
                data = None

    # 3. Try finding outermost JSON object
    if data is None:
        outer_match = re.search(r"\{.*\}", cleaned, re.DOTALL)
        if outer_match:
            try:
                data = json.loads(outer_match.group(0))
            except json.JSONDecodeError as exc:
                raise AgentExecutionError(f"Malformed JSON output from model: {exc}")
        else:
            raise AgentExecutionError("Malformed JSON: no JSON object found in model response")

    if not isinstance(data, dict):
        raise AgentExecutionError(f"Model output root must be a JSON object, got {type(data)}")

    claims = data.get("claims")
    if claims is None:
        raise AgentExecutionError("Model output JSON missing 'claims' key")

    if not isinstance(claims, list):
        raise AgentExecutionError(f"'claims' must be a list, got {type(claims)}")

    return claims


class ClaimAgent:
    """Agent that runs model turns, safe tool calls, and validates final claim spans."""

    def __init__(
        self,
        provider: BaseProvider,
        brand_facts: dict[str, BrandFact],
        prompt_version: str = "v1",
        timeout_seconds: float = DEFAULT_TIMEOUT_SECONDS,
        max_turns: int = MAX_TURNS,
    ):
        self.provider = provider
        self.brand_facts = brand_facts
        self.prompt_version = prompt_version
        self.timeout_seconds = timeout_seconds
        self.max_turns = max_turns
        self.catalogue_fact_ids = set(brand_facts.keys())
        self.known_brands = {f.brand_id.lower() for f in brand_facts.values()}

        prompt_file = PROMPTS_DIR / f"{prompt_version}.txt"
        if not prompt_file.exists():
            raise FileNotFoundError(f"Prompt file not found: {prompt_file}")
        self.system_prompt = prompt_file.read_text(encoding="utf-8")

    def process_answer(
        self,
        answer_id: str,
        brand_id: str,
        question: str,
        ai_answer: str,
    ) -> tuple[AnswerOutcome, list[dict[str, Any]]]:
        """Process an answer with up to max_turns.

        Returns (AnswerOutcome, sanitized_exchange_history).
        """
        start_time = time.perf_counter()
        exchange_log: list[dict[str, Any]] = []

        # Validate input purity
        validate_agent_input({
            "answer_id": answer_id,
            "brand_id": brand_id,
            "question": question,
            "ai_answer": ai_answer,
        })

        # Check known primary brand
        if brand_id.strip().lower() not in self.known_brands:
            elapsed_ms = (time.perf_counter() - start_time) * 1000
            outcome = AnswerOutcome(
                answer_id=answer_id,
                status="error",
                predictions=[],
                error_message=f"Unknown primary brand: {brand_id!r}",
                latency_ms=elapsed_ms,
            )
            return outcome, exchange_log

        user_content = (
            f"answer_id: {answer_id}\n"
            f"brand_id: {brand_id}\n"
            f"question: {question}\n\n"
            f"ai_answer:\n{ai_answer}"
        )

        messages = [
            LLMMessage(role="system", content=self.system_prompt),
            LLMMessage(role="user", content=user_content),
        ]

        final_raw_claims: Optional[list[dict[str, Any]]] = None

        try:
            for turn in range(1, self.max_turns + 1):
                # Call provider
                llm_response = self.provider.chat_completion(
                    messages=messages,
                    tools=TOOL_DEFINITIONS,
                    timeout_seconds=self.timeout_seconds,
                )

                # Log sanitized exchange
                exchange_log.append({
                    "turn": turn,
                    "content": llm_response.content,
                    "tool_calls": [
                        {"name": tc.name, "arguments": tc.arguments}
                        for tc in llm_response.tool_calls
                    ],
                })

                # Check if model made tool calls
                if llm_response.tool_calls:
                    # Append assistant message with tool calls
                    assistant_msg = LLMMessage(
                        role="assistant",
                        content=llm_response.content,
                        tool_calls=llm_response.tool_calls,
                    )
                    messages.append(assistant_msg)

                    # Execute all requested tool calls
                    for tc in llm_response.tool_calls:
                        tool_result = execute_tool_call(
                            tool_name=tc.name,
                            arguments=tc.arguments,
                            brand_facts=self.brand_facts,
                            known_brands=self.known_brands,
                        )
                        # Append tool response message
                        messages.append(
                            LLMMessage(
                                role="tool",
                                tool_call_id=tc.id,
                                name=tc.name,
                                content=json.dumps(tool_result),
                            )
                        )
                    # Proceed to next turn
                    continue

                # If no tool calls, model returned its final answer
                if llm_response.content:
                    final_raw_claims = parse_model_claims_json(llm_response.content)
                    break
                else:
                    raise AgentExecutionError("Model returned empty response with no tool calls")

            # Check if turn limit was exhausted without final answer
            if final_raw_claims is None:
                raise AgentExecutionError(
                    f"Turn limit exhausted ({self.max_turns} turns) without final predictions"
                )

            # Python-side quote location and claim formatting
            processed_claims: list[dict[str, Any]] = []
            curr_pos = 0

            for raw_c in final_raw_claims:
                quote = raw_c.get("quote", "").strip()
                if not quote:
                    raise AgentExecutionError("Claim item missing quote")

                start_char, end_char = locate_quote(ai_answer, quote, curr_pos)
                curr_pos = end_char

                claim_id = f"{answer_id}:{start_char}:{end_char}"
                fact_ids = raw_c.get("fact_ids", [])
                if not isinstance(fact_ids, list):
                    fact_ids = []

                processed_claims.append({
                    "answer_id": answer_id,
                    "claim_id": claim_id,
                    "start_char": start_char,
                    "end_char": end_char,
                    "quote": quote,
                    "label": raw_c.get("label"),
                    "fact_ids": fact_ids,
                    "reason": raw_c.get("reason", ""),
                })

            # Sort claims strictly by start_char
            processed_claims.sort(key=lambda c: c["start_char"])

            # Validate the claims list
            validation = validate_claims_list(
                claims=processed_claims,
                answer_id=answer_id,
                ai_answer=ai_answer,
                catalogue_fact_ids=self.catalogue_fact_ids,
            )

            if not validation.is_valid:
                raise AgentExecutionError(
                    f"Predicted claims failed validation: {'; '.join(validation.errors)}"
                )

            elapsed_ms = (time.perf_counter() - start_time) * 1000
            status = "empty" if len(processed_claims) == 0 else "success"

            return (
                AnswerOutcome(
                    answer_id=answer_id,
                    status=status,
                    predictions=processed_claims,
                    error_message=None,
                    latency_ms=elapsed_ms,
                ),
                exchange_log,
            )

        except (ToolExecutionError, AgentExecutionError, TimeoutError, Exception) as exc:
            elapsed_ms = (time.perf_counter() - start_time) * 1000
            outcome = AnswerOutcome(
                answer_id=answer_id,
                status="error",
                predictions=[],
                error_message=str(exc),
                latency_ms=elapsed_ms,
            )
            return outcome, exchange_log
