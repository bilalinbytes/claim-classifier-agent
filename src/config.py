"""Configuration and constants for the Kasparro FSE assessment."""
from pathlib import Path

# Repository root and standard directories
ROOT_DIR = Path(__file__).resolve().parent.parent
DATA_DIR = ROOT_DIR / "data"
PROMPTS_DIR = ROOT_DIR / "prompts"
REPORTS_DIR = ROOT_DIR / "reports"
EXCHANGES_DIR = ROOT_DIR / "exchanges"

# Dataset and catalogue versions
DATASET_VERSION = "long-brand-answers-50-v4"
FACT_VERSION = "speaker-catalogue-v4"
EVALUATOR_VERSION = "sentence-spans-and-labels-v4"

# Temporal anchor
QUESTION_DATE = "2026-10-01"

# Standard splits
DEV_SPLIT_NAME = "development"
CHECK_SPLIT_NAME = "check"
DEV_ANSWER_IDS = [f"A{i:02d}" for i in range(1, 41)]
CHECK_ANSWER_IDS = [f"A{i:02d}" for i in range(41, 51)]

# Label enumeration
VALID_LABELS = {"supported", "contradicted", "unknown"}

# Execution constraints
MAX_TURNS = 3
DEFAULT_TIMEOUT_SECONDS = 30.0
