"""Sequential evaluation runner and report generator."""
from __future__ import annotations

import datetime
import json
import subprocess
from pathlib import Path
from typing import Any, Optional

from src.agent import ClaimAgent
from src.config import (
    CHECK_ANSWER_IDS,
    DATA_DIR,
    DATASET_VERSION,
    DEFAULT_TIMEOUT_SECONDS,
    DEV_ANSWER_IDS,
    EVALUATOR_VERSION,
    EXCHANGES_DIR,
    FACT_VERSION,
    MAX_TURNS,
    REPORTS_DIR,
)
from src.data_loader import (
    compute_file_sha256,
    load_answers,
    load_brand_facts,
    load_gold_claims,
)
from src.providers import get_provider
from src.providers.base import BaseProvider
from src.scorer import AnswerOutcome, ScoreReport, score_split


def get_git_revision() -> str:
    """Retrieve current git commit hash if available, otherwise 'unversioned'."""
    try:
        res = subprocess.run(
            ["git", "rev-parse", "HEAD"],
            capture_output=True,
            text=True,
            check=True,
        )
        return res.stdout.strip()
    except Exception:
        return "unversioned"


def generate_markdown_report(report_data: dict[str, Any]) -> str:
    """Format evaluation run report into a clear, readable Markdown document."""
    meta = report_data["metadata"]
    metrics = report_data.get("metrics", {})

    lines = [
        f"# Evaluation Run Report: {meta['prompt_version'].upper()} ({meta['split'].capitalize()})",
        "",
        "## Run Metadata",
        f"- **Timestamp**: {meta['timestamp']}",
        f"- **Split**: `{meta['split']}`",
        f"- **Prompt Version**: `{meta['prompt_version']}`",
        f"- **Provider**: `{meta['provider']}`",
        f"- **Model**: `{meta['model']}`",
        f"- **Git Revision**: `{meta['git_revision']}`",
        f"- **Dataset Version**: `{meta['dataset_version']}`",
        f"- **Evaluator**: `{meta['evaluator']}`",
        f"- **Fact Version**: `{meta['fact_version']}`",
        f"- **Timeout**: {meta['settings']['timeout_seconds']}s",
        f"- **Max Turns**: {meta['settings']['max_turns']}",
        "",
        "## File Integrity Checksums (SHA-256)",
        f"- `answers.csv`: `{meta['csv_hashes']['answers.csv']}`",
        f"- `brand_facts.csv`: `{meta['csv_hashes']['brand_facts.csv']}`",
        f"- `development_gold.csv`: `{meta['csv_hashes']['development_gold.csv']}`",
        "",
        "## Outcome Counts",
        f"- **Scheduled Answers**: {report_data['scheduled_answers_count']}",
        f"- **Successful Answers**: {report_data['successful_answers_count']}",
        f"- **Empty Claims Answers**: {report_data['empty_answers_count']}",
        f"- **Error Answers**: {report_data['error_answers_count']}",
        "",
    ]

    if meta["split"] == "check":
        lines.extend([
            "## Quality Metrics",
            "> [!NOTE]",
            "> Quality metrics (G, M, C, Precision, Recall, F1) are `null` for the check split as per specification.",
            "> Predictions and outcomes have been frozen and saved for evaluation against private ground truth.",
            "",
        ])
    else:
        lines.extend([
            "## Quality Metrics",
            "| Metric | Count / Value |",
            "| :--- | :--- |",
            f"| **Gold Claims (G)** | {metrics.get('G')} |",
            f"| **Accepted Predictions (P)** | {metrics.get('P')} |",
            f"| **Exact Span Matches (M)** | {metrics.get('M')} |",
            f"| **Correctly Labeled Matches (C)** | {metrics.get('C')} |",
            f"| **Extraction Precision (M/P)** | {metrics.get('extraction_precision')} |",
            f"| **Extraction Recall (M/G)** | {metrics.get('extraction_recall')} |",
            f"| **Extraction F1** | {metrics.get('extraction_f1')} |",
            f"| **Joint Precision (C/P)** | {metrics.get('joint_precision')} |",
            f"| **Joint Recall (C/G)** | {metrics.get('joint_recall')} |",
            f"| **Joint F1** | {metrics.get('joint_f1')} |",
            f"| **Coverage (C/G)** | {metrics.get('coverage')} |",
            "",
            "## Detailed Accounting Lists",
            f"- **Missed Gold IDs ({len(report_data.get('missed_gold_ids', []))})**: {', '.join(report_data.get('missed_gold_ids', [])) or 'None'}",
            f"- **Unmatched Prediction IDs ({len(report_data.get('unmatched_prediction_ids', []))})**: {', '.join(report_data.get('unmatched_prediction_ids', [])) or 'None'}",
            f"- **Matched Wrong-Label Count**: {len(report_data.get('matched_wrong_label_ids', []))}",
            "",
        ])

    lines.extend([
        "## Answer Outcomes",
        "| Answer ID | Status | Claims Count | Latency (ms) | Error Message |",
        "| :--- | :--- | :--- | :--- | :--- |",
    ])
    for ans in report_data.get("answer_outcomes", []):
        err = ans.get("error_message") or "-"
        latency = f"{ans.get('latency_ms', 0):.1f}" if ans.get("latency_ms") is not None else "-"
        lines.append(
            f"| `{ans['answer_id']}` | {ans['status']} | {len(ans.get('predictions', []))} | {latency} | {err} |"
        )

    return "\n".join(lines) + "\n"


def run_evaluation(
    prompt_version: str = "v1",
    split: str = "development",
    provider: Optional[BaseProvider] = None,
    provider_name: str = "fake",
    model_name: str = "default",
    timeout_seconds: float = DEFAULT_TIMEOUT_SECONDS,
    max_turns: int = MAX_TURNS,
    answers_path: Optional[Path] = None,
    facts_path: Optional[Path] = None,
    gold_path: Optional[Path] = None,
) -> dict[str, Any]:
    """Execute sequential evaluation run over the selected split and generate reports."""
    # Ensure directories exist
    REPORTS_DIR.mkdir(parents=True, exist_ok=True)
    EXCHANGES_DIR.mkdir(parents=True, exist_ok=True)

    # 1. Load data
    answers = load_answers(answers_path)
    brand_facts = load_brand_facts(facts_path)
    gold_claims = load_gold_claims(gold_path)

    # 2. Determine scheduled answers
    norm_split = split.strip().lower()
    if norm_split == "development":
        scheduled_ids = DEV_ANSWER_IDS
    elif norm_split == "check":
        scheduled_ids = CHECK_ANSWER_IDS
    else:
        raise ValueError(f"Unknown split: {split!r}. Must be 'development' or 'check'")

    # 3. Instantiate agent
    if provider is None:
        provider = get_provider(provider_name, model=model_name)

    agent = ClaimAgent(
        provider=provider,
        brand_facts=brand_facts,
        prompt_version=prompt_version,
        timeout_seconds=timeout_seconds,
        max_turns=max_turns,
    )

    # 4. Sequential execution
    outcomes: dict[str, AnswerOutcome] = {}
    all_exchanges: dict[str, list[dict[str, Any]]] = {}

    for aid in scheduled_ids:
        ans = answers[aid]
        outcome, exchange = agent.process_answer(
            answer_id=ans.answer_id,
            brand_id=ans.brand_id,
            question=ans.question,
            ai_answer=ans.ai_answer,
        )
        outcomes[aid] = outcome
        all_exchanges[aid] = exchange

    # 5. Score split
    score_report = score_split(
        split=norm_split,
        scheduled_answer_ids=scheduled_ids,
        outcomes=outcomes,
        gold_claims=gold_claims,
        answers=answers,
    )

    # 6. Gather metadata
    timestamp = datetime.datetime.now(datetime.timezone.utc).isoformat()
    git_rev = get_git_revision()
    csv_hashes = {
        "answers.csv": compute_file_sha256(answers_path or DATA_DIR / "answers.csv"),
        "brand_facts.csv": compute_file_sha256(facts_path or DATA_DIR / "brand_facts.csv"),
        "development_gold.csv": compute_file_sha256(gold_path or DATA_DIR / "development_gold.csv"),
    }

    report_dict: dict[str, Any] = {
        "metadata": {
            "prompt_version": prompt_version,
            "split": norm_split,
            "provider": provider_name,
            "model": model_name,
            "timestamp": timestamp,
            "git_revision": git_rev,
            "dataset_version": DATASET_VERSION,
            "evaluator": EVALUATOR_VERSION,
            "fact_version": FACT_VERSION,
            "csv_hashes": csv_hashes,
            "settings": {
                "timeout_seconds": timeout_seconds,
                "max_turns": max_turns,
            },
        },
        "scheduled_answers_count": score_report.scheduled_answers_count,
        "successful_answers_count": score_report.successful_answers_count,
        "empty_answers_count": score_report.empty_answers_count,
        "error_answers_count": score_report.error_answers_count,
        "metrics": {
            "G": score_report.G,
            "P": score_report.P,
            "M": score_report.M,
            "C": score_report.C,
            "extraction_precision": score_report.extraction_precision,
            "extraction_recall": score_report.extraction_recall,
            "extraction_f1": score_report.extraction_f1,
            "joint_precision": score_report.joint_precision,
            "joint_recall": score_report.joint_recall,
            "joint_f1": score_report.joint_f1,
            "coverage": score_report.coverage,
        },
        "missed_gold_ids": score_report.missed_gold_ids,
        "unmatched_prediction_ids": score_report.unmatched_prediction_ids,
        "matched_wrong_label_ids": score_report.matched_wrong_label_ids,
        "matched_correct_ids": score_report.matched_correct_ids,
        "answer_outcomes": [
            {
                "answer_id": aid,
                "status": o.status,
                "latency_ms": o.latency_ms,
                "error_message": o.error_message,
                "predictions": o.predictions,
            }
            for aid, o in outcomes.items()
        ],
    }

    # 7. Save reports and sanitized exchanges
    json_path = REPORTS_DIR / f"{prompt_version}_{norm_split}_report.json"
    with open(json_path, "w", encoding="utf-8") as f:
        json.dump(report_dict, f, indent=2)

    md_report = generate_markdown_report(report_dict)
    md_path = REPORTS_DIR / f"{prompt_version}_{norm_split}_report.md"
    with open(md_path, "w", encoding="utf-8") as f:
        f.write(md_report)

    exchanges_path = EXCHANGES_DIR / f"{prompt_version}_{norm_split}_exchanges.json"
    with open(exchanges_path, "w", encoding="utf-8") as f:
        json.dump(all_exchanges, f, indent=2)

    return report_dict
