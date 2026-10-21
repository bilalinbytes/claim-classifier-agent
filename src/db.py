"""Database layer supporting PostgreSQL (via DATABASE_URL) and SQLite fallback for local testing."""
from __future__ import annotations

import json
import os
import sqlite3
import uuid
from typing import Any, Optional, Union
import psycopg2
from psycopg2.extras import RealDictCursor


def get_db_connection(database_url: Optional[str] = None):
    """Return a database connection based on DATABASE_URL or in-memory SQLite."""
    db_url = database_url or os.getenv("DATABASE_URL", "")

    if db_url.startswith("postgres://") or db_url.startswith("postgresql://"):
        return psycopg2.connect(db_url)
    elif db_url.startswith("sqlite:///"):
        sqlite_path = db_url.replace("sqlite:///", "")
        conn = sqlite3.connect(sqlite_path)
        conn.row_factory = sqlite3.Row
        conn.execute("PRAGMA foreign_keys = ON;")
        return conn
    else:
        # Default local SQLite file or in-memory
        conn = sqlite3.connect("kasparro.db")
        conn.row_factory = sqlite3.Row
        conn.execute("PRAGMA foreign_keys = ON;")
        return conn


def is_postgres(conn: Any) -> bool:
    return isinstance(conn, psycopg2.extensions.connection)


def init_db(conn: Any) -> None:
    """Initialize database tables with foreign keys and unique constraints."""
    cur = conn.cursor()

    if is_postgres(conn):
        cur.execute("""
            CREATE TABLE IF NOT EXISTS runs (
                run_id UUID PRIMARY KEY,
                created_at TIMESTAMP WITH TIME ZONE NOT NULL,
                agent_version TEXT NOT NULL,
                split TEXT NOT NULL,
                status TEXT NOT NULL,
                scheduled_count INT NOT NULL,
                successful_count INT NOT NULL,
                empty_count INT NOT NULL,
                error_count INT NOT NULL,
                metrics JSONB,
                config JSONB,
                missed_gold_ids JSONB,
                unmatched_prediction_ids JSONB,
                matched_wrong_label_ids JSONB
            );

            CREATE TABLE IF NOT EXISTS answer_results (
                id SERIAL PRIMARY KEY,
                run_id UUID NOT NULL REFERENCES runs(run_id) ON DELETE CASCADE,
                answer_id TEXT NOT NULL,
                status TEXT NOT NULL,
                error_message TEXT,
                latency_ms DOUBLE PRECISION,
                trace_ref TEXT,
                CONSTRAINT uq_run_answer UNIQUE (run_id, answer_id)
            );

            CREATE TABLE IF NOT EXISTS claim_results (
                id SERIAL PRIMARY KEY,
                run_id UUID NOT NULL REFERENCES runs(run_id) ON DELETE CASCADE,
                answer_id TEXT NOT NULL,
                claim_id TEXT NOT NULL,
                start_char INT NOT NULL,
                end_char INT NOT NULL,
                quote TEXT NOT NULL,
                label TEXT NOT NULL,
                fact_ids JSONB NOT NULL,
                reason TEXT NOT NULL,
                matched_gold_id TEXT,
                is_correct_label BOOLEAN,
                CONSTRAINT uq_run_answer_span UNIQUE (run_id, answer_id, start_char, end_char)
            );
        """)
    else:
        # SQLite dialect
        cur.execute("""
            CREATE TABLE IF NOT EXISTS runs (
                run_id TEXT PRIMARY KEY,
                created_at TEXT NOT NULL,
                agent_version TEXT NOT NULL,
                split TEXT NOT NULL,
                status TEXT NOT NULL,
                scheduled_count INTEGER NOT NULL,
                successful_count INTEGER NOT NULL,
                empty_count INTEGER NOT NULL,
                error_count INTEGER NOT NULL,
                metrics TEXT,
                config TEXT,
                missed_gold_ids TEXT,
                unmatched_prediction_ids TEXT,
                matched_wrong_label_ids TEXT
            );
        """)
        cur.execute("""
            CREATE TABLE IF NOT EXISTS answer_results (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                run_id TEXT NOT NULL REFERENCES runs(run_id) ON DELETE CASCADE,
                answer_id TEXT NOT NULL,
                status TEXT NOT NULL,
                error_message TEXT,
                latency_ms REAL,
                trace_ref TEXT,
                UNIQUE (run_id, answer_id)
            );
        """)
        cur.execute("""
            CREATE TABLE IF NOT EXISTS claim_results (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                run_id TEXT NOT NULL REFERENCES runs(run_id) ON DELETE CASCADE,
                answer_id TEXT NOT NULL,
                claim_id TEXT NOT NULL,
                start_char INTEGER NOT NULL,
                end_char INTEGER NOT NULL,
                quote TEXT NOT NULL,
                label TEXT NOT NULL,
                fact_ids TEXT NOT NULL,
                reason TEXT NOT NULL,
                matched_gold_id TEXT,
                is_correct_label INTEGER,
                UNIQUE (run_id, answer_id, start_char, end_char)
            );
        """)

    conn.commit()
    cur.close()


def save_evaluation_run(conn: Any, report_dict: dict[str, Any], run_id: Optional[str] = None) -> str:
    """Persist an evaluation run and its answer/claim outcomes using parameterized SQL."""
    actual_run_id = run_id or str(uuid.uuid4())
    meta = report_dict["metadata"]
    metrics = report_dict.get("metrics")

    # Serialize JSON payloads
    metrics_json = json.dumps(metrics) if metrics is not None else None
    config_json = json.dumps(meta)
    missed_json = json.dumps(report_dict.get("missed_gold_ids", []))
    unmatched_json = json.dumps(report_dict.get("unmatched_prediction_ids", []))
    wrong_label_json = json.dumps(report_dict.get("matched_wrong_label_ids", []))

    cur = conn.cursor()
    ph = "%s" if is_postgres(conn) else "?"

    # 1. Insert run row
    insert_run_sql = f"""
        INSERT INTO runs (
            run_id, created_at, agent_version, split, status,
            scheduled_count, successful_count, empty_count, error_count,
            metrics, config, missed_gold_ids, unmatched_prediction_ids, matched_wrong_label_ids
        ) VALUES ({', '.join([ph] * 14)});
    """
    cur.execute(
        insert_run_sql,
        (
            actual_run_id,
            meta.get("timestamp"),
            meta.get("prompt_version"),
            meta.get("split"),
            "completed",  # fully processed runs with answer errors are still 'completed'
            report_dict.get("scheduled_answers_count", 0),
            report_dict.get("successful_answers_count", 0),
            report_dict.get("empty_answers_count", 0),
            report_dict.get("error_answers_count", 0),
            metrics_json,
            config_json,
            missed_json,
            unmatched_json,
            wrong_label_json,
        ),
    )

    # 2. Insert answer rows and claim rows
    insert_ans_sql = f"""
        INSERT INTO answer_results (
            run_id, answer_id, status, error_message, latency_ms, trace_ref
        ) VALUES ({', '.join([ph] * 6)});
    """

    insert_claim_sql = f"""
        INSERT INTO claim_results (
            run_id, answer_id, claim_id, start_char, end_char,
            quote, label, fact_ids, reason, matched_gold_id, is_correct_label
        ) VALUES ({', '.join([ph] * 11)});
    """

    for ans in report_dict.get("answer_outcomes", []):
        cur.execute(
            insert_ans_sql,
            (
                actual_run_id,
                ans["answer_id"],
                ans["status"],
                ans.get("error_message"),
                ans.get("latency_ms"),
                ans.get("trace_ref"),
            ),
        )

        for pred in ans.get("predictions", []):
            fact_ids_val = json.dumps(pred.get("fact_ids", []))
            cur.execute(
                insert_claim_sql,
                (
                    actual_run_id,
                    ans["answer_id"],
                    pred["claim_id"],
                    pred["start_char"],
                    pred["end_char"],
                    pred["quote"],
                    pred["label"],
                    fact_ids_val,
                    pred.get("reason", ""),
                    pred.get("matched_gold_id"),
                    pred.get("is_correct_label"),
                ),
            )

    conn.commit()
    cur.close()
    return actual_run_id


def get_evaluation_run(conn: Any, run_id: str) -> Optional[dict[str, Any]]:
    """Retrieve joined run metadata, answer outcomes, and predicted claims in stable order."""
    cur = conn.cursor()
    ph = "%s" if is_postgres(conn) else "?"

    # 1. Fetch run
    cur.execute(f"SELECT * FROM runs WHERE run_id = {ph};", (run_id,))
    run_row = cur.fetchone()
    if not run_row:
        cur.close()
        return None

    # Handle row dict mapping
    if is_postgres(conn):
        colnames = [desc[0] for desc in cur.description]
        run_dict = dict(zip(colnames, run_row))
    else:
        run_dict = dict(run_row)

    # 2. Fetch answers in stable answer_id order
    cur.execute(
        f"SELECT * FROM answer_results WHERE run_id = {ph} ORDER BY answer_id ASC;",
        (run_id,),
    )
    ans_rows = cur.fetchall()
    ans_list = []
    for a in ans_rows:
        if is_postgres(conn):
            d = dict(zip([desc[0] for desc in cur.description], a))
        else:
            d = dict(a)
        ans_list.append(d)

    # 3. Fetch claims in stable (answer_id, start_char) order
    cur.execute(
        f"SELECT * FROM claim_results WHERE run_id = {ph} ORDER BY answer_id ASC, start_char ASC;",
        (run_id,),
    )
    claim_rows = cur.fetchall()
    claims_by_ans: dict[str, list[dict[str, Any]]] = {}
    for c in claim_rows:
        if is_postgres(conn):
            cd = dict(zip([desc[0] for desc in cur.description], c))
        else:
            cd = dict(c)
        if isinstance(cd.get("fact_ids"), str):
            try:
                cd["fact_ids"] = json.loads(cd["fact_ids"])
            except Exception:
                pass
        aid = cd["answer_id"]
        claims_by_ans.setdefault(aid, []).append(cd)

    cur.close()

    # Join claims into answers
    for ans in ans_list:
        ans["predictions"] = claims_by_ans.get(ans["answer_id"], [])

    # Decode JSON fields in run_dict if strings
    for k in ["metrics", "config", "missed_gold_ids", "unmatched_prediction_ids", "matched_wrong_label_ids"]:
        if isinstance(run_dict.get(k), str):
            try:
                run_dict[k] = json.loads(run_dict[k])
            except Exception:
                pass

    run_dict["answers"] = ans_list
    return run_dict
