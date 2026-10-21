"""Pytest fixtures for testing data loading, validation, and scoring."""
import pytest
from src.data_loader import load_answers, load_brand_facts, load_gold_claims
from src.config import DATA_DIR

@pytest.fixture(scope="session")
def answers_dict():
    return load_answers(DATA_DIR / "answers.csv")

@pytest.fixture(scope="session")
def brand_facts_dict():
    return load_brand_facts(DATA_DIR / "brand_facts.csv")

@pytest.fixture(scope="session")
def gold_claims_list():
    return load_gold_claims(DATA_DIR / "development_gold.csv")

@pytest.fixture(scope="session")
def catalogue_fact_ids(brand_facts_dict):
    return set(brand_facts_dict.keys())
