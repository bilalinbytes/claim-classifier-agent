"""CLI entry point for running evaluation benchmarks."""
import argparse
import os
import sys
from dotenv import load_dotenv

from src.runner import run_evaluation


def main():
    load_dotenv()

    parser = argparse.ArgumentParser(
        description="Run Kasparro factual claim extraction and evaluation harness."
    )
    parser.add_argument(
        "--version",
        required=True,
        choices=["v1", "v2"],
        help="Agent/prompt version to evaluate (v1 or v2).",
    )
    parser.add_argument(
        "--split",
        required=True,
        choices=["development", "check"],
        help="Data split to evaluate (development [A01-A40] or check [A41-A50]).",
    )
    parser.add_argument(
        "--provider",
        default=None,
        choices=["gemini", "openai", "anthropic", "fake"],
        help="LLM provider name (defaults to LLM_PROVIDER from env or 'fake').",
    )
    parser.add_argument(
        "--model",
        default=None,
        help="Model name (defaults to LLM_MODEL from env or provider default).",
    )
    parser.add_argument(
        "--timeout",
        type=float,
        default=30.0,
        help="Per-request timeout in seconds (default: 30.0).",
    )

    args = parser.parse_args()

    print(f"=== Starting Kasparro Evaluation Run: {args.version} ({args.split}) ===")
    report = run_evaluation(
        prompt_version=args.version,
        split=args.split,
        provider_name=args.provider or os.getenv("LLM_PROVIDER", "fake"),
        model_name=args.model or os.getenv("LLM_MODEL", "default"),
        timeout_seconds=args.timeout or float(os.getenv("TIMEOUT_SECONDS", "30.0")),
    )

    print("\n=== Run Complete ===")
    print(f"Scheduled answers: {report['scheduled_answers_count']}")
    print(f"Successful: {report['successful_answers_count']}")
    print(f"Empty: {report['empty_answers_count']}")
    print(f"Errors: {report['error_answers_count']}")

    if args.split == "development":
        m = report["metrics"]
        print("\n=== Metrics ===")
        print(f"G: {m['G']}, P: {m['P']}, M: {m['M']}, C: {m['C']}")
        print(f"Extraction Precision: {m['extraction_precision']}, Recall: {m['extraction_recall']}, F1: {m['extraction_f1']}")
        print(f"Joint Precision: {m['joint_precision']}, Recall: {m['joint_recall']}, F1: {m['joint_f1']}")
        print(f"Coverage: {m['coverage']}")
    else:
        print("\nCheck split: Quality metrics are null (frozen for reviewer evaluation).")

    print(f"\nSaved reports to reports/{args.version}_{args.split}_report.json and .md")
    print(f"Saved sanitized exchanges to exchanges/{args.version}_{args.split}_exchanges.json")


if __name__ == "__main__":
    main()
