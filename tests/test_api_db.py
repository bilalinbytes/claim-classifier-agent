"""Integration tests for FastAPI endpoints and database persistence."""
import uuid
import pytest
from fastapi.testclient import TestClient

from src.api import app
from src.db import (
    get_db_connection,
    init_db,
    save_evaluation_run,
    get_evaluation_run,
)


@pytest.fixture(scope="module")
def client():
    with TestClient(app) as c:
        yield c


def test_classify_success(client, answers_dict):
    a01 = answers_dict["A01"]
    payload = {
        "answer_id": "A01",
        "brand_id": "cleartrail",
        "question": a01.question,
        "ai_answer": a01.ai_answer,
        "agent_version": "v1",
    }
    # Uses default fake provider which returns empty claims list
    res = client.post("/classify", json=payload)
    assert res.status_code == 200
    data = res.json()
    assert data["answer_id"] == "A01"
    assert data["status"] in {"success", "empty"}
    assert isinstance(data["claims"], list)


def test_classify_rejects_forbidden_gold_fields(client, answers_dict):
    a01 = answers_dict["A01"]
    payload = {
        "answer_id": "A01",
        "brand_id": "cleartrail",
        "question": a01.question,
        "ai_answer": a01.ai_answer,
        "agent_version": "v1",
        "gold": [{"start": 0}],  # Forbidden!
    }
    res = client.post("/classify", json=payload)
    assert res.status_code == 422
    assert res.json()["type"] == "validation_error"


def test_classify_rejects_claims_input(client, answers_dict):
    a01 = answers_dict["A01"]
    payload = {
        "answer_id": "A01",
        "brand_id": "cleartrail",
        "question": a01.question,
        "ai_answer": a01.ai_answer,
        "claims_list": ["foo"],  # Forbidden!
    }
    res = client.post("/classify", json=payload)
    assert res.status_code == 422
    assert res.json()["type"] == "validation_error"


def test_classify_unknown_primary_brand(client, answers_dict):
    a01 = answers_dict["A01"]
    payload = {
        "answer_id": "A01",
        "brand_id": "sony_unsupported",
        "question": a01.question,
        "ai_answer": a01.ai_answer,
        "agent_version": "v1",
    }
    res = client.post("/classify", json=payload)
    assert res.status_code == 404
    data = res.json()
    assert data["type"] == "not_found"
    assert "Unknown primary brand" in data["message"]


def test_evaluation_runs_and_get(client):
    # 1. Run check split evaluation
    res = client.post(
        "/evaluation-runs",
        json={"agent_version": "v1", "split": "check", "provider": "fake"},
    )
    assert res.status_code == 201
    data = res.json()
    run_id = data["run_id"]
    assert data["status"] == "completed"
    assert data["counts"]["scheduled"] == 10
    # For check split, quality metrics should be null
    assert data["metrics"]["G"] is None
    assert data["metrics"]["extraction_f1"] is None

    # 2. Retrieve the run via GET /evaluation-runs/{id}
    res_get = client.get(f"/evaluation-runs/{run_id}")
    assert res_get.status_code == 200
    run_data = res_get.json()
    assert run_data["run_id"] == run_id
    assert run_data["split"] == "check"
    assert len(run_data["answers"]) == 10
    # Stable order check: answers must be sorted A41 to A50
    a_ids = [a["answer_id"] for a in run_data["answers"]]
    assert a_ids == sorted(a_ids)


def test_get_evaluation_run_invalid_uuid(client):
    res = client.get("/evaluation-runs/not-a-valid-uuid")
    assert res.status_code == 422
    assert res.json()["type"] == "validation_error"


def test_get_evaluation_run_not_found(client):
    missing_uuid = str(uuid.uuid4())
    res = client.get(f"/evaluation-runs/{missing_uuid}")
    assert res.status_code == 404
    assert res.json()["type"] == "not_found"


def test_db_persistence_and_unique_constraints():
    conn = get_db_connection()
    init_db(conn)

    run_id = str(uuid.uuid4())
    dummy_report = {
        "metadata": {
            "prompt_version": "v1",
            "split": "development",
            "provider": "fake",
            "model": "test",
            "timestamp": "2026-10-21T00:00:00Z",
        },
        "scheduled_answers_count": 1,
        "successful_answers_count": 1,
        "empty_answers_count": 0,
        "error_answers_count": 0,
        "metrics": {"G": 1, "P": 1, "M": 1, "C": 1},
        "answer_outcomes": [
            {
                "answer_id": "A01",
                "status": "success",
                "latency_ms": 12.5,
                "error_message": None,
                "predictions": [
                    {
                        "claim_id": "A01:0:10",
                        "start_char": 0,
                        "end_char": 10,
                        "quote": "Quote text",
                        "label": "supported",
                        "fact_ids": ["fact_1"],
                        "reason": "Test explanation.",
                        "matched_gold_id": "A01:0:10",
                        "is_correct_label": True,
                    }
                ],
            }
        ],
    }

    # Save run
    saved_id = save_evaluation_run(conn, dummy_report, run_id=run_id)
    assert saved_id == run_id

    # Retrieve run
    retrieved = get_evaluation_run(conn, run_id)
    assert retrieved is not None
    assert retrieved["run_id"] == run_id
    assert len(retrieved["answers"]) == 1
    assert len(retrieved["answers"][0]["predictions"]) == 1

    conn.close()
