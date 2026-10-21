# Kasparro FSE Intern Pathway Assessment

An AI agent system that reads long product answers about speaker hardware, extracts factual claim sentences, and classifies each claim as `supported`, `contradicted`, or `unknown` using a catalogue-backed tool execution framework with deterministic evaluation and PostgreSQL persistence.

---

## 1. Environment & Installation

### Requirements
- Python 3.11+ (verified on Python 3.15.0)
- PostgreSQL (or local SQLite fallback)

### Installation
```bash
# Clone the repository and navigate to root
cd assesment

# Install pinned dependencies
pip install -r requirements.txt
```

### Environment Configuration
Copy `.env.example` to `.env` and fill in your chosen LLM provider credentials:
```bash
cp .env.example .env
```
Supported providers: `gemini`, `openai`, `anthropic`, and `fake` (for offline testing).

---

## 2. CLI Evaluation Benchmark

Run sequential evaluation benchmarks across splits:
```bash
# Baseline v1 on Development Split (A01 - A40)
python -m src.run --version v1 --split development --provider gemini --model gemini-2.5-flash

# Baseline v1 on Final Check Split (A41 - A50)
python -m src.run --version v1 --split check --provider gemini --model gemini-2.5-flash

# Candidate v2 on Development Split (A01 - A40)
python -m src.run --version v2 --split development --provider gemini --model gemini-2.5-flash

# Candidate v2 on Final Check Split (A41 - A50)
python -m src.run --version v2 --split check --provider gemini --model gemini-2.5-flash
```

Outputs are automatically saved:
- JSON Report: `reports/{version}_{split}_report.json`
- Markdown Report: `reports/{version}_{split}_report.md`
- Sanitized Interaction Traces: `exchanges/{version}_{split}_exchanges.json`

---

## 3. FastAPI Service & PostgreSQL Setup

### Setup PostgreSQL Database
Set your `DATABASE_URL` in `.env`:
```env
DATABASE_URL=postgresql://postgres:password@localhost:5432/kasparro
```
*(If omitted, the service falls back to `sqlite:///kasparro.db` automatically).*

### Launch the Server
```bash
python -m uvicorn src.api:app --host 0.0.0.0 --port 8000
```

### Endpoints
- **`POST /classify`**: Real-time single answer classification.
  - Returns 200 with extracted claims.
  - Returns 422 if forbidden gold or claims fields are passed.
  - Returns 404 for unknown primary brand.
  - Returns 502 for provider failures / malformed output.
  - Returns 504 for timeouts.
- **`POST /evaluation-runs`**: Run split benchmark (`development` or `check`) and persist results to DB.
- **`GET /evaluation-runs/{id}`**: Joined retrieval of run metadata, answer outcomes, and predicted claims in stable order.

---

## 4. Test Suite Execution

Run all unit, integration, and security tests:
```bash
pytest -v
```

### Verified Test Status (Actually Executed)
The following 49 tests were executed and passed in the local environment:
- **Data Layer & Types (`tests/test_data_loader.py`)**: 7 tests passed (strict boolean `"false"` vs `"true"`, numbers, UTF-8 preservation, SHA-256 verification).
- **Validation Rules (`tests/test_validator.py`)**: 11 tests passed (code-point offsets, exact quote equality, whitespace trimming, unique IDs, overlap prevention, order sorting, reason sentence counts $\le 2$).
- **Scorer Determinism (`tests/test_scorer.py`)**: 10 tests passed (arithmetic check $G=10, P=10, M=8, C=7$, perfect output, missed claims, extra advice claims, wrong labels, answer errors, empty predictions, duplicate rejection, null check metrics).
- **Tool Security (`tests/test_tools.py`)**: 4 tests passed (catalogue retrieval, unknown brand rejection, illegal tool name rejection, malformed argument handling).
- **Agent & Provider Security (`tests/test_agent.py`)**: 11 tests passed (multi-turn execution, quote location, unknown brand, malformed JSON, unsupported label, invented fact IDs, turn exhaustion, timeout, gold payload leakage prevention).
- **FastAPI & DB Persistence (`tests/test_api_db.py`)**: 6 tests passed (status codes 200, 404, 422, joined run retrieval, unique DB constraints).
