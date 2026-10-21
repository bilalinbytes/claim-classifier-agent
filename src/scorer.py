"""Deterministic evaluation scorer for factual claim extraction and classification."""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Optional

from src.data_loader import Answer, GoldClaim


@dataclass
class AnswerOutcome:
    answer_id: str
    status: str  # "success", "empty", or "error"
    predictions: list[dict[str, Any]] = field(default_factory=list)
    error_message: Optional[str] = None
    latency_ms: Optional[float] = None


@dataclass
class ScoreReport:
    split: str
    scheduled_answers_count: int
    successful_answers_count: int
    empty_answers_count: int
    error_answers_count: int

    # Quality metrics (None for check split or empty split)
    G: Optional[int]
    P: Optional[int]
    M: Optional[int]
    C: Optional[int]

    extraction_precision: Optional[float]
    extraction_recall: Optional[float]
    extraction_f1: Optional[float]

    joint_precision: Optional[float]
    joint_recall: Optional[float]
    joint_f1: Optional[float]
    coverage: Optional[float]

    # Detailed accounting
    missed_gold_ids: list[str] = field(default_factory=list)
    unmatched_prediction_ids: list[str] = field(default_factory=list)
    matched_wrong_label_ids: list[dict[str, Any]] = field(default_factory=list)
    matched_correct_ids: list[str] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        return {
            "split": self.split,
            "scheduled_answers_count": self.scheduled_answers_count,
            "successful_answers_count": self.successful_answers_count,
            "empty_answers_count": self.empty_answers_count,
            "error_answers_count": self.error_answers_count,
            "metrics": {
                "G": self.G,
                "P": self.P,
                "M": self.M,
                "C": self.C,
                "extraction_precision": self.extraction_precision,
                "extraction_recall": self.extraction_recall,
                "extraction_f1": self.extraction_f1,
                "joint_precision": self.joint_precision,
                "joint_recall": self.joint_recall,
                "joint_f1": self.joint_f1,
                "coverage": self.coverage,
            },
            "missed_gold_ids": self.missed_gold_ids,
            "unmatched_prediction_ids": self.unmatched_prediction_ids,
            "matched_wrong_label_ids": self.matched_wrong_label_ids,
            "matched_correct_ids": self.matched_correct_ids,
        }


def safe_div(numerator: float, denominator: float, fallback: float = 0.0) -> float:
    """Deterministic division returning fallback (default 0.0) on zero denominator."""
    if denominator == 0:
        return fallback
    return numerator / denominator


def score_split(
    split: str,
    scheduled_answer_ids: list[str],
    outcomes: dict[str, AnswerOutcome],
    gold_claims: list[GoldClaim],
    answers: dict[str, Answer],
) -> ScoreReport:
    """Score predictions on a scheduled split.

    Strictly enforces:
    - Exactly one outcome per scheduled answer (no missing, no duplicate).
    - Deterministic exact span matching: (answer_id, start_char, end_char).
    - Quote validated first against raw answer.
    - Each gold claim matched at most once.
    - Answer errors add no predictions; their gold claims remain in G as missed.
    - If split == 'check', all quality metrics are null (None).
    """
    # 1. Reject missing or duplicated outcomes
    scheduled_set = set(scheduled_answer_ids)
    outcome_set = set(outcomes.keys())

    missing_answers = scheduled_set - outcome_set
    if missing_answers:
        raise ValueError(
            f"Missing outcomes for scheduled answers: {sorted(missing_answers)}"
        )

    extra_answers = outcome_set - scheduled_set
    if extra_answers:
        raise ValueError(
            f"Extra outcomes not in scheduled answers: {sorted(extra_answers)}"
        )

    if len(scheduled_answer_ids) != len(scheduled_set):
        raise ValueError("Scheduled answer IDs contain duplicates")

    # 2. Accounting for answer outcome statuses
    successful_count = 0
    empty_count = 0
    error_count = 0

    accepted_predictions: list[dict[str, Any]] = []

    for aid in scheduled_answer_ids:
        outcome = outcomes[aid]
        if outcome.status == "error":
            error_count += 1
            # Answer errors add no predictions
            continue
        elif outcome.status == "empty" or len(outcome.predictions) == 0:
            empty_count += 1
        elif outcome.status == "success":
            successful_count += 1
        else:
            raise ValueError(f"Unknown outcome status: {outcome.status!r} for answer {aid}")

        # Validate quotes for accepted predictions
        ans = answers.get(aid)
        if ans is None:
            raise ValueError(f"Answer metadata missing for answer_id {aid}")

        for pred in outcome.predictions:
            start = pred["start_char"]
            end = pred["end_char"]
            quote = pred["quote"]
            expected_quote = ans.ai_answer[start:end]
            if quote != expected_quote:
                raise ValueError(
                    f"Prediction quote mismatch in answer {aid} [{start}:{end}]: {quote!r} != {expected_quote!r}"
                )
            accepted_predictions.append(pred)

    # 3. For the check split, all quality metrics are null (None)
    if split.strip().lower() == "check":
        return ScoreReport(
            split=split,
            scheduled_answers_count=len(scheduled_answer_ids),
            successful_answers_count=successful_count,
            empty_answers_count=empty_count,
            error_answers_count=error_count,
            G=None,
            P=None,
            M=None,
            C=None,
            extraction_precision=None,
            extraction_recall=None,
            extraction_f1=None,
            joint_precision=None,
            joint_recall=None,
            joint_f1=None,
            coverage=None,
            missed_gold_ids=[],
            unmatched_prediction_ids=[],
            matched_wrong_label_ids=[],
            matched_correct_ids=[],
        )

    # 4. Filter gold claims belonging to the scheduled answers
    relevant_gold = [g for g in gold_claims if g.answer_id in scheduled_set]
    G = len(relevant_gold)
    P = len(accepted_predictions)

    # Check for empty split
    if G == 0 and P == 0:
        return ScoreReport(
            split=split,
            scheduled_answers_count=len(scheduled_answer_ids),
            successful_answers_count=successful_count,
            empty_answers_count=empty_count,
            error_answers_count=error_count,
            G=0,
            P=0,
            M=0,
            C=0,
            extraction_precision=None,
            extraction_recall=None,
            extraction_f1=None,
            joint_precision=None,
            joint_recall=None,
            joint_f1=None,
            coverage=None,
            missed_gold_ids=[],
            unmatched_prediction_ids=[],
            matched_wrong_label_ids=[],
            matched_correct_ids=[],
        )

    # 5. Deterministic exact matching on (answer_id, start_char, end_char)
    # Map (answer_id, start, end) -> GoldClaim
    gold_map: dict[tuple[str, int, int], GoldClaim] = {
        (g.answer_id, g.start_char, g.end_char): g for g in relevant_gold
    }

    matched_gold_keys: set[tuple[str, int, int]] = set()
    unmatched_pred_ids: list[str] = []
    matched_wrong_label_records: list[dict[str, Any]] = []
    matched_correct_ids: list[str] = []

    M = 0
    C = 0

    for pred in accepted_predictions:
        key = (pred["answer_id"], pred["start_char"], pred["end_char"])
        cid = pred["claim_id"]
        pred_label = pred["label"]

        if key in gold_map and key not in matched_gold_keys:
            gold = gold_map[key]
            matched_gold_keys.add(key)
            M += 1

            if pred_label == gold.expected_label:
                C += 1
                matched_correct_ids.append(cid)
            else:
                matched_wrong_label_records.append(
                    {
                        "prediction_claim_id": cid,
                        "gold_claim_id": gold.claim_id,
                        "predicted_label": pred_label,
                        "expected_label": gold.expected_label,
                    }
                )
        else:
            unmatched_pred_ids.append(cid)

    # Missed gold claims
    missed_gold_ids = [
        g.claim_id
        for g in relevant_gold
        if (g.answer_id, g.start_char, g.end_char) not in matched_gold_keys
    ]

    # Compute metrics (zero denominator yields 0.0 when gold exists)
    extraction_precision = round(safe_div(M, P, 0.0), 6)
    extraction_recall = round(safe_div(M, G, 0.0), 6)
    extraction_f1 = round(safe_div(2 * M, P + G, 0.0), 6)

    joint_precision = round(safe_div(C, P, 0.0), 6)
    joint_recall = round(safe_div(C, G, 0.0), 6)
    joint_f1 = round(safe_div(2 * C, P + G, 0.0), 6)

    coverage = round(safe_div(C, G, 0.0), 6)

    return ScoreReport(
        split=split,
        scheduled_answers_count=len(scheduled_answer_ids),
        successful_answers_count=successful_count,
        empty_answers_count=empty_count,
        error_answers_count=error_count,
        G=G,
        P=P,
        M=M,
        C=C,
        extraction_precision=extraction_precision,
        extraction_recall=extraction_recall,
        extraction_f1=extraction_f1,
        joint_precision=joint_precision,
        joint_recall=joint_recall,
        joint_f1=joint_f1,
        coverage=coverage,
        missed_gold_ids=missed_gold_ids,
        unmatched_prediction_ids=unmatched_pred_ids,
        matched_wrong_label_ids=matched_wrong_label_records,
        matched_correct_ids=matched_correct_ids,
    )
