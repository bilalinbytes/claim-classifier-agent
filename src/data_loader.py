"""Data loading and parsing module with strict type handling and UTF-8 decoding."""
from __future__ import annotations

import csv
import hashlib
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Union

from src.config import DATA_DIR


@dataclass(frozen=True)
class Answer:
    answer_id: str
    split: str
    brand_id: str
    question: str
    ai_answer: str


@dataclass(frozen=True)
class BrandFact:
    fact_id: str
    brand_id: str
    model_id: str
    field: str
    raw_value: str
    typed_value: Union[int, float, bool, str]
    value_type: str
    unit: str
    condition: str
    valid_from: str
    valid_to: str

    def to_dict(self) -> dict[str, Any]:
        return {
            "fact_id": self.fact_id,
            "brand_id": self.brand_id,
            "model_id": self.model_id,
            "field": self.field,
            "value": self.raw_value,
            "typed_value": self.typed_value,
            "value_type": self.value_type,
            "unit": self.unit,
            "condition": self.condition,
            "valid_from": self.valid_from,
            "valid_to": self.valid_to,
        }


@dataclass(frozen=True)
class GoldClaim:
    answer_id: str
    claim_id: str
    start_char: int
    end_char: int
    quote: str
    expected_label: str
    evidence_fact_ids: list[str] = field(default_factory=list)
    explanation: str = ""
    difficulty_tags: str = ""


def parse_typed_value(raw_val: str, value_type: str) -> Union[int, float, bool, str]:
    """Parse raw string value into python typed representation according to value_type."""
    vt = value_type.strip().lower()
    if vt == "boolean":
        lowered = raw_val.strip().lower()
        if lowered == "true":
            return True
        elif lowered == "false":
            return False
        else:
            raise ValueError(f"Invalid boolean value: {raw_val!r}")
    elif vt == "number":
        cleaned = raw_val.strip()
        try:
            return int(cleaned)
        except ValueError:
            return float(cleaned)
    elif vt == "string":
        return raw_val
    else:
        raise ValueError(f"Unknown value_type: {value_type!r}")


def compute_file_sha256(path: Union[str, Path]) -> str:
    """Compute SHA-256 hash of a file."""
    hasher = hashlib.sha256()
    with open(path, "rb") as f:
        while chunk := f.read(65536):
            hasher.update(chunk)
    return hasher.hexdigest()


def load_answers(path: Union[str, Path] | None = None) -> dict[str, Answer]:
    """Load answers CSV file without altering whitespace or linebreaks."""
    filepath = Path(path) if path else DATA_DIR / "answers.csv"
    answers: dict[str, Answer] = {}
    with open(filepath, "r", encoding="utf-8", newline="") as f:
        reader = csv.DictReader(f)
        for row in reader:
            aid = row["answer_id"].strip()
            answers[aid] = Answer(
                answer_id=aid,
                split=row["split"].strip(),
                brand_id=row["brand_id"].strip(),
                question=row["question"],
                ai_answer=row["ai_answer"],
            )
    return answers


def load_brand_facts(path: Union[str, Path] | None = None) -> dict[str, BrandFact]:
    """Load brand_facts CSV file, parsing types and normalizing blank unit/condition to N/A."""
    filepath = Path(path) if path else DATA_DIR / "brand_facts.csv"
    facts: dict[str, BrandFact] = {}
    with open(filepath, "r", encoding="utf-8", newline="") as f:
        reader = csv.DictReader(f)
        for row in reader:
            fid = row["fact_id"].strip()
            raw_val = row["value"]
            vtype = row["value_type"].strip()
            typed_val = parse_typed_value(raw_val, vtype)

            raw_unit = row.get("unit", "")
            unit = raw_unit.strip() if raw_unit and raw_unit.strip() != "" else "N/A"

            raw_cond = row.get("condition", "")
            cond = raw_cond.strip() if raw_cond and raw_cond.strip() != "" else "N/A"

            facts[fid] = BrandFact(
                fact_id=fid,
                brand_id=row["brand_id"].strip(),
                model_id=row["model_id"].strip(),
                field=row["field"].strip(),
                raw_value=raw_val,
                typed_value=typed_val,
                value_type=vtype,
                unit=unit,
                condition=cond,
                valid_from=row["valid_from"].strip(),
                valid_to=row["valid_to"].strip(),
            )
    return facts


def load_gold_claims(path: Union[str, Path] | None = None) -> list[GoldClaim]:
    """Load development gold claims CSV."""
    filepath = Path(path) if path else DATA_DIR / "development_gold.csv"
    claims: list[GoldClaim] = []
    with open(filepath, "r", encoding="utf-8", newline="") as f:
        reader = csv.DictReader(f)
        for row in reader:
            evidence_raw = row.get("evidence_fact_ids", "")
            if evidence_raw and evidence_raw.strip():
                evidence_list = [f.strip() for f in evidence_raw.split("|") if f.strip()]
            else:
                evidence_list = []

            claims.append(
                GoldClaim(
                    answer_id=row["answer_id"].strip(),
                    claim_id=row["claim_id"].strip(),
                    start_char=int(row["start_char"]),
                    end_char=int(row["end_char"]),
                    quote=row["quote"],
                    expected_label=row["expected_label"].strip(),
                    evidence_fact_ids=evidence_list,
                    explanation=row.get("explanation", ""),
                    difficulty_tags=row.get("difficulty_tags", ""),
                )
            )
    return claims


def get_facts_for_brand(facts: dict[str, BrandFact], brand_id: str) -> list[BrandFact]:
    """Return all facts matching the given brand_id."""
    target = brand_id.strip().lower()
    return [fact for fact in facts.values() if fact.brand_id.lower() == target]
