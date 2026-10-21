"""Unit tests for the validator module."""
import pytest
from src.validator import (
    count_sentences,
    validate_single_claim,
    validate_claims_list,
)

def test_count_sentences():
    assert count_sentences("") == 0
    assert count_sentences("   ") == 0
    assert count_sentences("Single sentence.") == 1
    assert count_sentences("Sentence one. Sentence two.") == 2
    assert count_sentences("Sentence one! Sentence two? Sentence three.") == 3
    assert count_sentences("Unpunctuated sentence") == 1

def test_validate_valid_claim(answers_dict, catalogue_fact_ids):
    a01 = answers_dict["A01"]
    # Slice valid first sentence:
    # "For the current India catalogue, ClearTrail Mini is listed at INR 1,200 less than ClearTrail Plus, comparing the two tax-inclusive prices before shipping."
    start = 306
    end = 460
    quote = a01.ai_answer[start:end]

    claim = {
        "claim_id": f"A01:{start}:{end}",
        "start_char": start,
        "end_char": end,
        "quote": quote,
        "label": "supported",
        "fact_ids": ["cleartrail.mini.price_2026", "cleartrail.plus.price_2026"],
        "reason": "The two 2026 list prices are 1299 and 2499; the difference is correct.",
    }

    errors = validate_single_claim(claim, "A01", a01.ai_answer, catalogue_fact_ids)
    assert errors == []

def test_validate_offset_bounds(answers_dict, catalogue_fact_ids):
    a01 = answers_dict["A01"]
    # start < 0
    c1 = {
        "claim_id": "A01:-1:10",
        "start_char": -1,
        "end_char": 10,
        "quote": "text",
        "label": "unknown",
        "fact_ids": [],
        "reason": "test.",
    }
    errs1 = validate_single_claim(c1, "A01", a01.ai_answer, catalogue_fact_ids)
    assert any("start_char must be non-negative" in e for e in errs1)

    # end <= start
    c2 = {
        "claim_id": "A01:10:10",
        "start_char": 10,
        "end_char": 10,
        "quote": "",
        "label": "unknown",
        "fact_ids": [],
        "reason": "test.",
    }
    errs2 = validate_single_claim(c2, "A01", a01.ai_answer, catalogue_fact_ids)
    assert any("end_char (10) must be strictly greater than start_char (10)" in e for e in errs2)

    # end > len(ai_answer)
    over_len = len(a01.ai_answer) + 50
    c3 = {
        "claim_id": f"A01:0:{over_len}",
        "start_char": 0,
        "end_char": over_len,
        "quote": "text",
        "label": "unknown",
        "fact_ids": [],
        "reason": "test.",
    }
    errs3 = validate_single_claim(c3, "A01", a01.ai_answer, catalogue_fact_ids)
    assert any("exceeds ai_answer length" in e for e in errs3)

def test_validate_quote_mismatch_and_whitespace(answers_dict, catalogue_fact_ids):
    a01 = answers_dict["A01"]
    start = 306
    end = 460
    correct_quote = a01.ai_answer[start:end]

    # Quote does not match exact slice
    c_mismatch = {
        "claim_id": f"A01:{start}:{end}",
        "start_char": start,
        "end_char": end,
        "quote": "Completely wrong text",
        "label": "supported",
        "fact_ids": [],
        "reason": "test.",
    }
    errs = validate_single_claim(c_mismatch, "A01", a01.ai_answer, catalogue_fact_ids)
    assert any("Quote mismatch" in e for e in errs)

    # Quote with leading whitespace
    c_ws = {
        "claim_id": f"A01:{start}:{end}",
        "start_char": start,
        "end_char": end,
        "quote": " " + correct_quote,
        "label": "supported",
        "fact_ids": [],
        "reason": "test.",
    }
    errs_ws = validate_single_claim(c_ws, "A01", a01.ai_answer, catalogue_fact_ids)
    assert any("leading or trailing whitespace" in e for e in errs_ws)

def test_validate_claim_id_format(answers_dict, catalogue_fact_ids):
    a01 = answers_dict["A01"]
    start = 306
    end = 460
    c = {
        "claim_id": "wrong_claim_id",
        "start_char": start,
        "end_char": end,
        "quote": a01.ai_answer[start:end],
        "label": "supported",
        "fact_ids": [],
        "reason": "test.",
    }
    errs = validate_single_claim(c, "A01", a01.ai_answer, catalogue_fact_ids)
    assert any("claim_id must be 'A01:306:460'" in e for e in errs)

def test_validate_label(answers_dict, catalogue_fact_ids):
    a01 = answers_dict["A01"]
    start = 306
    end = 460
    c = {
        "claim_id": f"A01:{start}:{end}",
        "start_char": start,
        "end_char": end,
        "quote": a01.ai_answer[start:end],
        "label": "partially_true",  # invalid
        "fact_ids": [],
        "reason": "test.",
    }
    errs = validate_single_claim(c, "A01", a01.ai_answer, catalogue_fact_ids)
    assert any("Invalid label 'partially_true'" in e for e in errs)

def test_validate_fact_ids_catalogue(answers_dict, catalogue_fact_ids):
    a01 = answers_dict["A01"]
    start = 306
    end = 460
    c = {
        "claim_id": f"A01:{start}:{end}",
        "start_char": start,
        "end_char": end,
        "quote": a01.ai_answer[start:end],
        "label": "supported",
        "fact_ids": ["cleartrail.invented_fact_999"],  # non-existent
        "reason": "test.",
    }
    errs = validate_single_claim(c, "A01", a01.ai_answer, catalogue_fact_ids)
    assert any("does not exist in catalogue" in e for e in errs)

def test_validate_reason_sentence_count(answers_dict, catalogue_fact_ids):
    a01 = answers_dict["A01"]
    start = 306
    end = 460
    c_long_reason = {
        "claim_id": f"A01:{start}:{end}",
        "start_char": start,
        "end_char": end,
        "quote": a01.ai_answer[start:end],
        "label": "supported",
        "fact_ids": [],
        "reason": "Sentence one. Sentence two. Sentence three exceeds the limit.",
    }
    errs = validate_single_claim(c_long_reason, "A01", a01.ai_answer, catalogue_fact_ids)
    assert any("reason must be <= 2 sentences" in e for e in errs)

def test_validate_claims_list_overlaps_and_order(answers_dict, catalogue_fact_ids):
    a01 = answers_dict["A01"]
    q1 = a01.ai_answer[306:460]
    q2 = a01.ai_answer[461:647]

    valid_list = [
        {
            "claim_id": "A01:306:460",
            "start_char": 306,
            "end_char": 460,
            "quote": q1,
            "label": "supported",
            "fact_ids": [],
            "reason": "Reason 1.",
        },
        {
            "claim_id": "A01:461:647",
            "start_char": 461,
            "end_char": 647,
            "quote": q2,
            "label": "contradicted",
            "fact_ids": [],
            "reason": "Reason 2.",
        },
    ]
    res_valid = validate_claims_list(valid_list, "A01", a01.ai_answer, catalogue_fact_ids)
    assert res_valid.is_valid is True

    # Test empty list is valid
    res_empty = validate_claims_list([], "A01", a01.ai_answer, catalogue_fact_ids)
    assert res_empty.is_valid is True

    # Test overlapping spans
    overlapping_list = [
        {
            "claim_id": "A01:306:460",
            "start_char": 306,
            "end_char": 460,
            "quote": q1,
            "label": "supported",
            "fact_ids": [],
            "reason": "Reason 1.",
        },
        {
            "claim_id": f"A01:400:647",
            "start_char": 400,
            "end_char": 647,
            "quote": a01.ai_answer[400:647],
            "label": "contradicted",
            "fact_ids": [],
            "reason": "Reason 2.",
        },
    ]
    res_overlap = validate_claims_list(overlapping_list, "A01", a01.ai_answer, catalogue_fact_ids)
    assert res_overlap.is_valid is False
    assert any("Overlapping claim span" in e for e in res_overlap.errors)

    # Test reverse start order
    reverse_order_list = [valid_list[1], valid_list[0]]
    res_order = validate_claims_list(reverse_order_list, "A01", a01.ai_answer, catalogue_fact_ids)
    assert res_order.is_valid is False
    assert any("strictly increasing start_char order" in e for e in res_order.errors)
