"""Unit tests for the claim extraction agent and fake provider scenarios."""
import json
import pytest
from src.agent import (
    ClaimAgent,
    InputValidationError,
    validate_agent_input,
    locate_quote,
)
from src.providers.base import LLMResponse, ToolCall
from src.providers.fake_provider import FakeProvider


def test_validate_agent_input_rejects_gold():
    forbidden_payloads = [
        {"answer_id": "A01", "brand_id": "cleartrail", "question": "Q", "ai_answer": "Ans", "gold": []},
        {"answer_id": "A01", "brand_id": "cleartrail", "question": "Q", "ai_answer": "Ans", "claims": []},
        {"answer_id": "A01", "brand_id": "cleartrail", "question": "Q", "ai_answer": "Ans", "start_char": 0},
        {"answer_id": "A01", "brand_id": "cleartrail", "question": "Q", "ai_answer": "Ans", "expected_label": "supported"},
    ]
    for p in forbidden_payloads:
        with pytest.raises(InputValidationError):
            validate_agent_input(p)


def test_locate_quote():
    text = "Sentence one. Sentence two. Sentence three."
    s, e = locate_quote(text, "Sentence two.")
    assert s == 14
    assert e == 27
    assert text[s:e] == "Sentence two."


def test_agent_successful_tool_call_and_prediction(answers_dict, brand_facts_dict):
    """Test 2-turn agent: Turn 1 requests get_brand_facts, Turn 2 returns claims."""
    a01 = answers_dict["A01"]
    quote = "For the current India catalogue, ClearTrail Mini is listed at INR 1,200 less than ClearTrail Plus, comparing the two tax-inclusive prices before shipping."

    resp1 = LLMResponse(
        content=None,
        tool_calls=[
            ToolCall(
                id="call_1",
                name="get_brand_facts",
                arguments={"brand_id": "cleartrail"},
            )
        ],
    )

    model_json = json.dumps({
        "claims": [
            {
                "quote": quote,
                "label": "supported",
                "fact_ids": ["cleartrail.mini.price_2026", "cleartrail.plus.price_2026"],
                "reason": "The two 2026 list prices are 1299 and 2499; difference is 1200.",
            }
        ]
    })
    resp2 = LLMResponse(content=model_json)

    fake_provider = FakeProvider(responses=[resp1, resp2])
    agent = ClaimAgent(
        provider=fake_provider,
        brand_facts=brand_facts_dict,
        prompt_version="v1",
    )

    outcome, exchange = agent.process_answer(
        answer_id="A01",
        brand_id="cleartrail",
        question=a01.question,
        ai_answer=a01.ai_answer,
    )

    assert outcome.status == "success"
    assert outcome.error_message is None
    assert len(outcome.predictions) == 1
    pred = outcome.predictions[0]
    assert pred["quote"] == quote
    assert pred["label"] == "supported"
    assert pred["start_char"] == 306
    assert pred["end_char"] == 460
    assert pred["claim_id"] == "A01:306:460"
    assert len(exchange) == 2


def test_agent_unknown_tool_fails_with_answer_error(answers_dict, brand_facts_dict):
    """Illegal tool call should produce a preserved answer-level error with 0 predictions."""
    a01 = answers_dict["A01"]

    resp1 = LLMResponse(
        content=None,
        tool_calls=[
            ToolCall(
                id="call_bad",
                name="malicious_tool",
                arguments={"arg": "value"},
            )
        ],
    )

    fake_provider = FakeProvider(responses=[resp1])
    agent = ClaimAgent(
        provider=fake_provider,
        brand_facts=brand_facts_dict,
        prompt_version="v1",
    )

    outcome, exchange = agent.process_answer(
        answer_id="A01",
        brand_id="cleartrail",
        question=a01.question,
        ai_answer=a01.ai_answer,
    )

    assert outcome.status == "error"
    assert outcome.predictions == []
    assert "Illegal tool" in outcome.error_message


def test_agent_unknown_brand_tool_fails(answers_dict, brand_facts_dict):
    """Unknown requested brand should produce a preserved answer-level error."""
    a01 = answers_dict["A01"]

    resp1 = LLMResponse(
        content=None,
        tool_calls=[
            ToolCall(
                id="call_brand",
                name="get_brand_facts",
                arguments={"brand_id": "nonexistent_brand"},
            )
        ],
    )

    fake_provider = FakeProvider(responses=[resp1])
    agent = ClaimAgent(
        provider=fake_provider,
        brand_facts=brand_facts_dict,
        prompt_version="v1",
    )

    outcome, exchange = agent.process_answer(
        answer_id="A01",
        brand_id="cleartrail",
        question=a01.question,
        ai_answer=a01.ai_answer,
    )

    assert outcome.status == "error"
    assert outcome.predictions == []
    assert "Unknown requested brand" in outcome.error_message


def test_agent_malformed_json_fails(answers_dict, brand_facts_dict):
    """Malformed model JSON output should produce a preserved answer-level error."""
    a01 = answers_dict["A01"]

    resp1 = LLMResponse(content="This is plain text, not valid JSON")
    fake_provider = FakeProvider(responses=[resp1])
    agent = ClaimAgent(
        provider=fake_provider,
        brand_facts=brand_facts_dict,
        prompt_version="v1",
    )

    outcome, exchange = agent.process_answer(
        answer_id="A01",
        brand_id="cleartrail",
        question=a01.question,
        ai_answer=a01.ai_answer,
    )

    assert outcome.status == "error"
    assert outcome.predictions == []
    assert "Malformed JSON" in outcome.error_message


def test_agent_unsupported_label_fails(answers_dict, brand_facts_dict):
    """Unsupported label returned by model produces preserved answer-level error."""
    a01 = answers_dict["A01"]
    quote = "For the current India catalogue, ClearTrail Mini is listed at INR 1,200 less than ClearTrail Plus, comparing the two tax-inclusive prices before shipping."

    model_json = json.dumps({
        "claims": [
            {
                "quote": quote,
                "label": "mostly_supported",  # invalid label
                "fact_ids": [],
                "reason": "Test explanation.",
            }
        ]
    })
    fake_provider = FakeProvider(responses=[LLMResponse(content=model_json)])
    agent = ClaimAgent(
        provider=fake_provider,
        brand_facts=brand_facts_dict,
        prompt_version="v1",
    )

    outcome, exchange = agent.process_answer(
        answer_id="A01",
        brand_id="cleartrail",
        question=a01.question,
        ai_answer=a01.ai_answer,
    )

    assert outcome.status == "error"
    assert outcome.predictions == []
    assert "Invalid label" in outcome.error_message


def test_agent_invented_fact_id_fails(answers_dict, brand_facts_dict):
    """Invented fact ID returned by model produces preserved answer-level error."""
    a01 = answers_dict["A01"]
    quote = "For the current India catalogue, ClearTrail Mini is listed at INR 1,200 less than ClearTrail Plus, comparing the two tax-inclusive prices before shipping."

    model_json = json.dumps({
        "claims": [
            {
                "quote": quote,
                "label": "supported",
                "fact_ids": ["invented.fact.id.999"],  # not in catalogue
                "reason": "Test explanation.",
            }
        ]
    })
    fake_provider = FakeProvider(responses=[LLMResponse(content=model_json)])
    agent = ClaimAgent(
        provider=fake_provider,
        brand_facts=brand_facts_dict,
        prompt_version="v1",
    )

    outcome, exchange = agent.process_answer(
        answer_id="A01",
        brand_id="cleartrail",
        question=a01.question,
        ai_answer=a01.ai_answer,
    )

    assert outcome.status == "error"
    assert outcome.predictions == []
    assert "does not exist in catalogue" in outcome.error_message


def test_agent_turn_exhaustion(answers_dict, brand_facts_dict):
    """Model requesting tools for all 3 turns without returning answer exhausts limit."""
    a01 = answers_dict["A01"]

    tool_call_resp = LLMResponse(
        content=None,
        tool_calls=[
            ToolCall(
                id="call_1",
                name="get_brand_facts",
                arguments={"brand_id": "cleartrail"},
            )
        ],
    )

    fake_provider = FakeProvider(responses=[tool_call_resp, tool_call_resp, tool_call_resp])
    agent = ClaimAgent(
        provider=fake_provider,
        brand_facts=brand_facts_dict,
        prompt_version="v1",
        max_turns=3,
    )

    outcome, exchange = agent.process_answer(
        answer_id="A01",
        brand_id="cleartrail",
        question=a01.question,
        ai_answer=a01.ai_answer,
    )

    assert outcome.status == "error"
    assert outcome.predictions == []
    assert "Turn limit exhausted" in outcome.error_message


def test_agent_timeout(answers_dict, brand_facts_dict):
    """Provider timeout produces preserved answer-level error."""
    a01 = answers_dict["A01"]

    fake_provider = FakeProvider(artificial_delay=0.1)
    agent = ClaimAgent(
        provider=fake_provider,
        brand_facts=brand_facts_dict,
        prompt_version="v1",
        timeout_seconds=0.01,
    )

    outcome, exchange = agent.process_answer(
        answer_id="A01",
        brand_id="cleartrail",
        question=a01.question,
        ai_answer=a01.ai_answer,
    )

    assert outcome.status == "error"
    assert outcome.predictions == []
    assert "timed out" in outcome.error_message.lower()


def test_gold_never_leaked_to_provider(answers_dict, brand_facts_dict, gold_claims_list):
    """Strict verification: Gold data must NEVER appear in any message or tool payload."""
    a01 = answers_dict["A01"]
    a01_gold = [g for g in gold_claims_list if g.answer_id == "A01"]
    gold_cids = [g.claim_id for g in a01_gold]

    fake_provider = FakeProvider(responses=[LLMResponse(content='{"claims": []}')])
    agent = ClaimAgent(
        provider=fake_provider,
        brand_facts=brand_facts_dict,
        prompt_version="v1",
    )

    outcome, exchange = agent.process_answer(
        answer_id="A01",
        brand_id="cleartrail",
        question=a01.question,
        ai_answer=a01.ai_answer,
    )

    for call in fake_provider.call_history:
        call_str = json.dumps(call)
        for cid in gold_cids:
            assert cid not in call_str, f"Gold claim_id {cid} leaked to provider!"
        assert "expected_label" not in call_str
        assert "difficulty_tags" not in call_str
