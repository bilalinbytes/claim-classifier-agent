"""Validator module for predicted claims and spans."""
from __future__ import annotations

import re
from dataclasses import dataclass
from typing import Any, Iterable

from src.config import VALID_LABELS


@dataclass
class ValidationResult:
    is_valid: bool
    errors: list[str]


def count_sentences(text: str) -> int:
    """Count sentences by standard terminal punctuation (. ! ?)."""
    stripped = text.strip()
    if not stripped:
        return 0
    # Split on sentence boundaries: punctuation followed by whitespace or end of string
    parts = [p.strip() for p in re.split(r'(?<=[.!?])\s+', stripped) if p.strip()]
    return len(parts)


def validate_single_claim(
    claim: dict[str, Any],
    answer_id: str,
    ai_answer: str,
    catalogue_fact_ids: set[str],
) -> list[str]:
    """Validate a single claim dictionary against rules."""
    errors: list[str] = []

    # Required fields check
    required_keys = {"claim_id", "start_char", "end_char", "quote", "label", "fact_ids", "reason"}
    missing_keys = required_keys - set(claim.keys())
    if missing_keys:
        return [f"Claim missing required fields: {sorted(missing_keys)}"]

    start = claim.get("start_char")
    end = claim.get("end_char")
    quote = claim.get("quote")
    cid = claim.get("claim_id")
    label = claim.get("label")
    fact_ids = claim.get("fact_ids")
    reason = claim.get("reason", "")

    # Integer offset validation
    if not isinstance(start, int) or not isinstance(end, int):
        errors.append(f"Offsets must be integers: start_char={start!r}, end_char={end!r}")
        return errors

    if start < 0:
        errors.append(f"start_char must be non-negative: {start}")
    if end <= start:
        errors.append(f"end_char ({end}) must be strictly greater than start_char ({start})")
    if end > len(ai_answer):
        errors.append(f"end_char ({end}) exceeds ai_answer length ({len(ai_answer)})")

    # Quote validation
    if not isinstance(quote, str):
        errors.append(f"quote must be a string, got {type(quote)}")
    else:
        # Check no leading/trailing whitespace
        if quote != quote.strip():
            errors.append(f"quote has leading or trailing whitespace: {quote!r}")
        if len(quote) == 0:
            errors.append("quote cannot be empty")

        # Code-point span equality check
        if 0 <= start < end <= len(ai_answer):
            expected_slice = ai_answer[start:end]
            if quote != expected_slice:
                errors.append(
                    f"Quote mismatch at [{start}:{end}]. Expected {expected_slice!r}, got {quote!r}"
                )

    # Claim ID format check: answer_id:start_char:end_char
    expected_cid = f"{answer_id}:{start}:{end}"
    if cid != expected_cid:
        errors.append(f"claim_id must be {expected_cid!r}, got {cid!r}")

    # Label validation
    if label not in VALID_LABELS:
        errors.append(f"Invalid label {label!r}. Must be one of {sorted(VALID_LABELS)}")

    # Fact IDs validation
    if not isinstance(fact_ids, list):
        errors.append(f"fact_ids must be a list, got {type(fact_ids)}")
    else:
        for fid in fact_ids:
            if not isinstance(fid, str):
                errors.append(f"fact_id must be a string, got {type(fid)}")
            elif fid not in catalogue_fact_ids:
                errors.append(f"fact_id {fid!r} does not exist in catalogue")

    # Reason validation: <= 2 sentences
    if not isinstance(reason, str):
        errors.append(f"reason must be a string, got {type(reason)}")
    else:
        sent_count = count_sentences(reason)
        if sent_count > 2:
            errors.append(f"reason must be <= 2 sentences, got {sent_count} sentences: {reason!r}")

    return errors


def validate_claims_list(
    claims: list[dict[str, Any]],
    answer_id: str,
    ai_answer: str,
    catalogue_fact_ids: set[str],
) -> ValidationResult:
    """Validate full claims list for an answer, including uniqueness, ordering, and overlap."""
    all_errors: list[str] = []

    if not isinstance(claims, list):
        return ValidationResult(is_valid=False, errors=["Claims must be a list"])

    # If empty list, structurally valid
    if len(claims) == 0:
        return ValidationResult(is_valid=True, errors=[])

    seen_ids: set[str] = set()
    prev_start = -1
    prev_end = -1

    for idx, claim in enumerate(claims):
        claim_errors = validate_single_claim(claim, answer_id, ai_answer, catalogue_fact_ids)
        if claim_errors:
            all_errors.extend([f"Claim #{idx}: {e}" for e in claim_errors])
            continue

        cid = claim["claim_id"]
        start = claim["start_char"]
        end = claim["end_char"]

        # Unique ID check
        if cid in seen_ids:
            all_errors.append(f"Duplicate claim_id {cid!r} at claim #{idx}")
        seen_ids.add(cid)

        # Increasing start order check
        if idx > 0 and start <= prev_start:
            all_errors.append(
                f"Claims must be in strictly increasing start_char order: #{idx} starts at {start} <= previous {prev_start}"
            )

        # Non-overlapping check
        if idx > 0 and start < prev_end:
            all_errors.append(
                f"Overlapping claim span detected: claim #{idx} starts at {start} before previous ends at {prev_end}"
            )

        prev_start = start
        prev_end = end

    return ValidationResult(is_valid=(len(all_errors) == 0), errors=all_errors)
