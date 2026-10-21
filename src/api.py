"""FastAPI application providing thin routes for claim classification and evaluation runs."""
from __future__ import annotations

import os
import uuid
from contextlib import asynccontextmanager
from typing import Any, Optional
from fastapi import FastAPI, HTTPException, Request, status
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from pydantic import BaseModel, ConfigDict, Field

from src.agent import (
    ClaimAgent,
    FORBIDDEN_INPUT_KEYS,
    InputValidationError,
    validate_agent_input,
)
from src.config import DEFAULT_TIMEOUT_SECONDS
from src.data_loader import load_brand_facts
from src.db import (
    get_db_connection,
    get_evaluation_run,
    init_db,
    save_evaluation_run,
)
from src.providers import get_provider
from src.runner import run_evaluation


# Preload catalogue
brand_facts_cache = load_brand_facts()
known_brands_cache = {f.brand_id.lower() for f in brand_facts_cache.values()}


@asynccontextmanager
async def lifespan(app: FastAPI):
    # Initialize database schema on startup
    conn = get_db_connection()
    init_db(conn)
    conn.close()
    yield


app = FastAPI(title="Kasparro FSE Evaluation API", version="1.0.0", lifespan=lifespan)


@app.exception_handler(RequestValidationError)
async def validation_exception_handler(request: Request, exc: RequestValidationError):
    return JSONResponse(
        status_code=422,
        content={"type": "validation_error", "message": str(exc)},
    )


class ClassifyRequest(BaseModel):
    model_config = ConfigDict(extra="allow")

    answer_id: str
    brand_id: str
    question: str
    ai_answer: str
    agent_version: str = Field(default="v1", pattern="^(v1|v2)$")


class EvaluationRunRequest(BaseModel):
    agent_version: str = Field(pattern="^(v1|v2)$")
    split: str = Field(pattern="^(development|check)$")
    provider: Optional[str] = None
    model: Optional[str] = None


@app.post("/classify")
async def classify(raw_request: Request):
    """Classify factual claim sentences in an AI answer."""
    try:
        body = await raw_request.json()
    except Exception:
        return JSONResponse(
            status_code=422,
            content={"type": "validation_error", "message": "Invalid JSON body"},
        )

    # 1. Strict forbidden fields check (gold / claims)
    try:
        validate_agent_input(body)
    except InputValidationError as ive:
        return JSONResponse(
            status_code=422,
            content={"type": "validation_error", "message": str(ive)},
        )

    # 2. Validate standard fields
    answer_id = body.get("answer_id")
    brand_id = body.get("brand_id")
    question = body.get("question")
    ai_answer = body.get("ai_answer")
    agent_version = body.get("agent_version", "v1")

    if agent_version not in {"v1", "v2"}:
        return JSONResponse(
            status_code=422,
            content={"type": "validation_error", "message": "agent_version must be v1 or v2"},
        )

    # 3. Unknown primary brand -> 404
    if brand_id.strip().lower() not in known_brands_cache:
        return JSONResponse(
            status_code=status.HTTP_404_NOT_FOUND,
            content={"type": "not_found", "message": f"Unknown primary brand: {brand_id!r}"},
        )

    # 4. Instantiate agent and run
    provider = get_provider()
    agent = ClaimAgent(
        provider=provider,
        brand_facts=brand_facts_cache,
        prompt_version=agent_version,
    )

    outcome, _ = agent.process_answer(
        answer_id=answer_id,
        brand_id=brand_id,
        question=question,
        ai_answer=ai_answer,
    )

    if outcome.status == "error":
        err_msg = outcome.error_message or "Unknown error"
        if "timed out" in err_msg.lower() or "timeout" in err_msg.lower():
            return JSONResponse(
                status_code=status.HTTP_504_GATEWAY_TIMEOUT,
                content={"type": "gateway_timeout", "message": err_msg},
            )
        else:
            return JSONResponse(
                status_code=status.HTTP_502_BAD_GATEWAY,
                content={"type": "bad_gateway", "message": err_msg},
            )

    return {
        "answer_id": answer_id,
        "status": outcome.status,
        "claims": outcome.predictions,
        "latency_ms": outcome.latency_ms,
    }


@app.post("/evaluation-runs", status_code=status.HTTP_201_CREATED)
async def create_evaluation_run(req: EvaluationRunRequest):
    """Run an evaluation benchmark over the fixed split and persist records in PostgreSQL."""
    try:
        report = run_evaluation(
            prompt_version=req.agent_version,
            split=req.split,
            provider_name=req.provider or os.getenv("LLM_PROVIDER", "fake"),
            model_name=req.model or os.getenv("LLM_MODEL", "default"),
        )
    except Exception as exc:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail={"type": "internal_error", "message": str(exc)},
        )

    # Save to database
    conn = get_db_connection()
    run_id = save_evaluation_run(conn, report)
    conn.close()

    return {
        "run_id": run_id,
        "status": "completed",
        "counts": {
            "scheduled": report["scheduled_answers_count"],
            "successful": report["successful_answers_count"],
            "empty": report["empty_answers_count"],
            "error": report["error_answers_count"],
        },
        "metrics": report["metrics"],
    }


@app.get("/evaluation-runs/{run_id}")
async def fetch_evaluation_run(run_id: str):
    """Retrieve joined run metadata, answer outcomes, and claim records in stable order."""
    # Validate UUID format
    try:
        uuid.UUID(run_id)
    except ValueError:
        return JSONResponse(
            status_code=422,
            content={"type": "validation_error", "message": f"Invalid UUID: {run_id!r}"},
        )

    conn = get_db_connection()
    result = get_evaluation_run(conn, run_id)
    conn.close()

    if result is None:
        return JSONResponse(
            status_code=status.HTTP_404_NOT_FOUND,
            content={"type": "not_found", "message": f"Evaluation run {run_id!r} not found"},
        )

    return result
