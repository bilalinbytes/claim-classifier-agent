"""Unit tests for the data loader module."""
import pytest
from src.data_loader import (
    load_answers,
    load_brand_facts,
    load_gold_claims,
    compute_file_sha256,
    parse_typed_value,
    get_facts_for_brand,
)
from src.config import DATA_DIR, DEV_ANSWER_IDS, CHECK_ANSWER_IDS

def test_parse_typed_value_boolean():
    # Strict boolean tests: "false" is not True!
    assert parse_typed_value("false", "boolean") is False
    assert parse_typed_value("False", "boolean") is False
    assert parse_typed_value("true", "boolean") is True
    assert parse_typed_value("True", "boolean") is True

    with pytest.raises(ValueError):
        parse_typed_value("not_a_bool", "boolean")

def test_parse_typed_value_number():
    assert parse_typed_value("1299", "number") == 1299
    assert isinstance(parse_typed_value("1299", "number"), int)
    assert parse_typed_value("12.5", "number") == 12.5
    assert isinstance(parse_typed_value("12.5", "number"), float)

def test_parse_typed_value_string():
    assert parse_typed_value("ClearTrail Mini", "string") == "ClearTrail Mini"

def test_load_answers(answers_dict):
    assert len(answers_dict) == 50
    # Development split A01 to A40
    for aid in DEV_ANSWER_IDS:
        assert aid in answers_dict
        assert answers_dict[aid].split == "development"
    # Check split A41 to A50
    for aid in CHECK_ANSWER_IDS:
        assert aid in answers_dict
        assert answers_dict[aid].split == "check"

    # Verify answers are never modified or whitespace-stripped
    a01 = answers_dict["A01"]
    assert "ClearTrail Mini" in a01.ai_answer
    assert "\n" in a01.ai_answer

def test_load_brand_facts(brand_facts_dict):
    assert len(brand_facts_dict) == 132

    # Check boolean fact parsing
    bool_facts = [f for f in brand_facts_dict.values() if f.value_type == "boolean"]
    assert len(bool_facts) > 0
    for bf in bool_facts:
        assert isinstance(bf.typed_value, bool)
        if bf.raw_value.lower() == "false":
            assert bf.typed_value is False
        elif bf.raw_value.lower() == "true":
            assert bf.typed_value is True

    # Check blank unit/condition becomes N/A
    facts_with_na = [f for f in brand_facts_dict.values() if f.unit == "N/A" or f.condition == "N/A"]
    assert len(facts_with_na) > 0

    # Check get_facts_for_brand
    ct_facts = get_facts_for_brand(brand_facts_dict, "cleartrail")
    assert len(ct_facts) > 0
    assert all(f.brand_id == "cleartrail" for f in ct_facts)

def test_load_gold_claims(gold_claims_list, answers_dict):
    assert len(gold_claims_list) == 376
    for gold in gold_claims_list:
        assert gold.answer_id in DEV_ANSWER_IDS
        # Verify 0-based code-point offset quote matches exact slice
        ai_ans = answers_dict[gold.answer_id].ai_answer
        actual_quote = ai_ans[gold.start_char:gold.end_char]
        assert gold.quote == actual_quote
        assert gold.expected_label in {"supported", "contradicted", "unknown"}

def test_csv_sha256_integrity():
    answers_sha = compute_file_sha256(DATA_DIR / "answers.csv")
    facts_sha = compute_file_sha256(DATA_DIR / "brand_facts.csv")
    gold_sha = compute_file_sha256(DATA_DIR / "development_gold.csv")

    assert answers_sha == "fa28e813ea54b4e5ea985585f22f084d826241e1182accbc27ace17066125724"
    assert facts_sha == "2190d40fad2dd167ef2437956c43d595aaf2554ea673a4789b9343cb7e2936f2"
    assert gold_sha == "afe84cc78f304afb6a4aaa505dd7504af80fcbf8bc507806aa5ff0aab6bf4850"
