"""Unit tests for the scorer module."""
import pytest
from src.data_loader import Answer, GoldClaim
from src.scorer import AnswerOutcome, score_split, safe_div


def test_safe_div():
    assert safe_div(10, 2) == 5.0
    assert safe_div(0, 5) == 0.0
    assert safe_div(5, 0) == 0.0
    assert safe_div(0, 0) == 0.0


def test_arithmetic_g10_p10_m8_c7():
    """Specific spec test:

    G=10, P=10, M=8, C=7 -> extraction P=0.80, R=0.80, F1=0.80; joint P=0.70, R=0.70, F1=0.70.
    """
    # Create 1 synthetic answer with 10 sentences
    text = "Sentence one. Sentence two. Sentence three. Sentence four. Sentence five. Sentence six. Sentence seven. Sentence eight. Sentence nine. Sentence ten. Extra eleven. Extra twelve."
    # Find offsets for 12 sentences
    sentences = [
        "Sentence one.",
        "Sentence two.",
        "Sentence three.",
        "Sentence four.",
        "Sentence five.",
        "Sentence six.",
        "Sentence seven.",
        "Sentence eight.",
        "Sentence nine.",
        "Sentence ten.",
        "Extra eleven.",
        "Extra twelve.",
    ]
    spans = []
    curr = 0
    for s in sentences:
        start = text.index(s, curr)
        end = start + len(s)
        spans.append((start, end, s))
        curr = end

    answers = {
        "A01": Answer(
            answer_id="A01",
            split="development",
            brand_id="test_brand",
            question="Question?",
            ai_answer=text,
        )
    }

    # 10 gold claims: first 10 sentences, all expected_label="supported"
    gold_claims = [
        GoldClaim(
            answer_id="A01",
            claim_id=f"A01:{spans[i][0]}:{spans[i][1]}",
            start_char=spans[i][0],
            end_char=spans[i][1],
            quote=spans[i][2],
            expected_label="supported",
        )
        for i in range(10)
    ]

    # 10 predictions:
    # 7 match span & label (supported) -> sentences 0..6
    # 1 matches span but wrong label (contradicted) -> sentence 7
    # 2 unmatched predictions -> sentences 10, 11 (Extra eleven, Extra twelve)
    predictions = []
    for i in range(7):
        predictions.append(
            {
                "answer_id": "A01",
                "claim_id": f"A01:{spans[i][0]}:{spans[i][1]}",
                "start_char": spans[i][0],
                "end_char": spans[i][1],
                "quote": spans[i][2],
                "label": "supported",
            }
        )
    # sentence 7 wrong label
    predictions.append(
        {
            "answer_id": "A01",
            "claim_id": f"A01:{spans[7][0]}:{spans[7][1]}",
            "start_char": spans[7][0],
            "end_char": spans[7][1],
            "quote": spans[7][2],
            "label": "contradicted",  # wrong label
        }
    )
    # sentences 10 and 11: extra predictions
    for i in [10, 11]:
        predictions.append(
            {
                "answer_id": "A01",
                "claim_id": f"A01:{spans[i][0]}:{spans[i][1]}",
                "start_char": spans[i][0],
                "end_char": spans[i][1],
                "quote": spans[i][2],
                "label": "supported",
            }
        )

    outcomes = {
        "A01": AnswerOutcome(
            answer_id="A01",
            status="success",
            predictions=predictions,
        )
    }

    report = score_split(
        split="development",
        scheduled_answer_ids=["A01"],
        outcomes=outcomes,
        gold_claims=gold_claims,
        answers=answers,
    )

    assert report.G == 10
    assert report.P == 10
    assert report.M == 8
    assert report.C == 7

    assert report.extraction_precision == 0.80
    assert report.extraction_recall == 0.80
    assert report.extraction_f1 == 0.80

    assert report.joint_precision == 0.70
    assert report.joint_recall == 0.70
    assert report.joint_f1 == 0.70

    assert report.coverage == 0.70
    assert len(report.missed_gold_ids) == 2  # sentences 8, 9
    assert len(report.unmatched_prediction_ids) == 2  # sentences 10, 11
    assert len(report.matched_wrong_label_ids) == 1  # sentence 7


def test_perfect_output(answers_dict, gold_claims_list):
    """Test perfect prediction where predictions match all gold claims exactly."""
    a01_gold = [g for g in gold_claims_list if g.answer_id == "A01"]
    predictions = [
        {
            "answer_id": g.answer_id,
            "claim_id": g.claim_id,
            "start_char": g.start_char,
            "end_char": g.end_char,
            "quote": g.quote,
            "label": g.expected_label,
            "fact_ids": g.evidence_fact_ids,
            "reason": "Perfect match.",
        }
        for g in a01_gold
    ]

    outcomes = {
        "A01": AnswerOutcome(
            answer_id="A01",
            status="success",
            predictions=predictions,
        )
    }

    report = score_split(
        split="development",
        scheduled_answer_ids=["A01"],
        outcomes=outcomes,
        gold_claims=gold_claims_list,
        answers=answers_dict,
    )

    G = len(a01_gold)
    assert report.G == G
    assert report.P == G
    assert report.M == G
    assert report.C == G
    assert report.extraction_precision == 1.0
    assert report.extraction_recall == 1.0
    assert report.extraction_f1 == 1.0
    assert report.joint_precision == 1.0
    assert report.joint_recall == 1.0
    assert report.joint_f1 == 1.0
    assert report.coverage == 1.0
    assert report.missed_gold_ids == []
    assert report.unmatched_prediction_ids == []
    assert report.matched_wrong_label_ids == []


def test_missed_claims(answers_dict, gold_claims_list):
    """Test where half the claims are missed."""
    a01_gold = [g for g in gold_claims_list if g.answer_id == "A01"]
    assert len(a01_gold) >= 2
    half = len(a01_gold) // 2

    predictions = [
        {
            "answer_id": g.answer_id,
            "claim_id": g.claim_id,
            "start_char": g.start_char,
            "end_char": g.end_char,
            "quote": g.quote,
            "label": g.expected_label,
            "fact_ids": g.evidence_fact_ids,
            "reason": "Matched.",
        }
        for g in a01_gold[:half]
    ]

    outcomes = {
        "A01": AnswerOutcome(
            answer_id="A01",
            status="success",
            predictions=predictions,
        )
    }

    report = score_split(
        split="development",
        scheduled_answer_ids=["A01"],
        outcomes=outcomes,
        gold_claims=gold_claims_list,
        answers=answers_dict,
    )

    assert report.G == len(a01_gold)
    assert report.P == half
    assert report.M == half
    assert report.C == half
    assert report.extraction_recall < 1.0
    assert report.extraction_precision == 1.0
    assert len(report.missed_gold_ids) == len(a01_gold) - half


def test_extra_advice_claim(answers_dict, gold_claims_list):
    """Test where an extra advice sentence is erroneously extracted."""
    a01 = answers_dict["A01"]
    a01_gold = [g for g in gold_claims_list if g.answer_id == "A01"]

    # All gold claims
    predictions = [
        {
            "answer_id": g.answer_id,
            "claim_id": g.claim_id,
            "start_char": g.start_char,
            "end_char": g.end_char,
            "quote": g.quote,
            "label": g.expected_label,
            "fact_ids": g.evidence_fact_ids,
            "reason": "Gold.",
        }
        for g in a01_gold
    ]

    # Erroneously extract the first advice sentence:
    # "Start with the exact model name before deciding what belongs in a weekend bag."
    advice_quote = "Start with the exact model name before deciding what belongs in a weekend bag."
    adv_start = a01.ai_answer.index(advice_quote)
    adv_end = adv_start + len(advice_quote)
    predictions.append(
        {
            "answer_id": "A01",
            "claim_id": f"A01:{adv_start}:{adv_end}",
            "start_char": adv_start,
            "end_char": adv_end,
            "quote": advice_quote,
            "label": "supported",
            "fact_ids": [],
            "reason": "Mistaken advice claim.",
        }
    )

    outcomes = {
        "A01": AnswerOutcome(
            answer_id="A01",
            status="success",
            predictions=predictions,
        )
    }

    report = score_split(
        split="development",
        scheduled_answer_ids=["A01"],
        outcomes=outcomes,
        gold_claims=gold_claims_list,
        answers=answers_dict,
    )

    assert report.G == len(a01_gold)
    assert report.P == len(a01_gold) + 1
    assert report.M == len(a01_gold)
    assert report.C == len(a01_gold)
    assert report.extraction_precision < 1.0
    assert report.extraction_recall == 1.0
    assert report.unmatched_prediction_ids == [f"A01:{adv_start}:{adv_end}"]


def test_wrong_labels(answers_dict, gold_claims_list):
    """Test where spans match but labels are inverted."""
    a01_gold = [g for g in gold_claims_list if g.answer_id == "A01"]
    predictions = [
        {
            "answer_id": g.answer_id,
            "claim_id": g.claim_id,
            "start_char": g.start_char,
            "end_char": g.end_char,
            "quote": g.quote,
            "label": "unknown" if g.expected_label != "unknown" else "supported",
            "fact_ids": [],
            "reason": "Wrong label.",
        }
        for g in a01_gold
    ]

    outcomes = {
        "A01": AnswerOutcome(
            answer_id="A01",
            status="success",
            predictions=predictions,
        )
    }

    report = score_split(
        split="development",
        scheduled_answer_ids=["A01"],
        outcomes=outcomes,
        gold_claims=gold_claims_list,
        answers=answers_dict,
    )

    assert report.M == len(a01_gold)
    assert report.C == 0
    assert report.extraction_f1 == 1.0
    assert report.joint_f1 == 0.0
    assert len(report.matched_wrong_label_ids) == len(a01_gold)


def test_provider_error_answer(answers_dict, gold_claims_list):
    """Test that answer errors add no predictions and their gold remains in G."""
    a01_gold = [g for g in gold_claims_list if g.answer_id == "A01"]

    outcomes = {
        "A01": AnswerOutcome(
            answer_id="A01",
            status="error",
            predictions=[
                {
                    "answer_id": "A01",
                    "claim_id": "A01:0:10",
                    "start_char": 0,
                    "end_char": 10,
                    "quote": "text",
                    "label": "supported",
                }
            ],
            error_message="Provider timeout after 30s",
        )
    }

    report = score_split(
        split="development",
        scheduled_answer_ids=["A01"],
        outcomes=outcomes,
        gold_claims=gold_claims_list,
        answers=answers_dict,
    )

    assert report.error_answers_count == 1
    assert report.P == 0  # No accepted predictions
    assert report.G == len(a01_gold)  # All gold remains in G
    assert report.M == 0
    assert report.C == 0
    assert report.extraction_f1 == 0.0
    assert len(report.missed_gold_ids) == len(a01_gold)


def test_valid_empty_predictions(answers_dict, gold_claims_list):
    """Test valid empty predictions returns 0.0 metrics when gold claims exist."""
    a01_gold = [g for g in gold_claims_list if g.answer_id == "A01"]

    outcomes = {
        "A01": AnswerOutcome(
            answer_id="A01",
            status="empty",
            predictions=[],
        )
    }

    report = score_split(
        split="development",
        scheduled_answer_ids=["A01"],
        outcomes=outcomes,
        gold_claims=gold_claims_list,
        answers=answers_dict,
    )

    assert report.empty_answers_count == 1
    assert report.P == 0
    assert report.G == len(a01_gold)
    assert report.M == 0
    assert report.C == 0
    assert report.extraction_precision == 0.0
    assert report.extraction_recall == 0.0
    assert report.extraction_f1 == 0.0
    assert report.joint_f1 == 0.0


def test_missing_or_duplicate_scheduled_answers(answers_dict, gold_claims_list):
    """Test rejection of missing or duplicated answer outcomes."""
    # Missing answer A02
    outcomes = {
        "A01": AnswerOutcome(answer_id="A01", status="empty", predictions=[]),
    }
    with pytest.raises(ValueError, match="Missing outcomes"):
        score_split(
            split="development",
            scheduled_answer_ids=["A01", "A02"],
            outcomes=outcomes,
            gold_claims=gold_claims_list,
            answers=answers_dict,
        )

    # Extra/unsolicited outcome
    outcomes_extra = {
        "A01": AnswerOutcome(answer_id="A01", status="empty", predictions=[]),
        "A99": AnswerOutcome(answer_id="A99", status="empty", predictions=[]),
    }
    with pytest.raises(ValueError, match="Extra outcomes"):
        score_split(
            split="development",
            scheduled_answer_ids=["A01"],
            outcomes=outcomes_extra,
            gold_claims=gold_claims_list,
            answers=answers_dict,
        )


def test_check_split_quality_metrics_null(answers_dict, gold_claims_list):
    """Test that check split has null quality metrics."""
    outcomes = {
        "A41": AnswerOutcome(answer_id="A41", status="empty", predictions=[]),
    }
    report = score_split(
        split="check",
        scheduled_answer_ids=["A41"],
        outcomes=outcomes,
        gold_claims=gold_claims_list,
        answers=answers_dict,
    )
    assert report.G is None
    assert report.P is None
    assert report.M is None
    assert report.C is None
    assert report.extraction_f1 is None
    assert report.joint_f1 is None
    assert report.coverage is None
