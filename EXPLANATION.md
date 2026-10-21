# Kasparro Assessment: Candidate Explanation & Analysis

## 1. Targeted Change (v1 -> v2)
- **Problem Diagnosed in v1**:
  Inspection of `reports/v1_development_report.md` revealed 12 answer-level errors. 5 of those 12 errors (`A03`, `A05`, `A20`, `A21`, `A23`) were caused strictly by the model outputting 3 short sentences in the `reason` field (e.g. converting hours to minutes across three distinct sentences), which violated the strict `reason <= 2 sentences` validation rule and led to complete rejection of all valid claims for those answers.
- **Hypothesis**:
  Explicitly instructing the model to output exactly ONE concise sentence per reason will eliminate the 3-sentence overflow errors, preserve answer validity, and recover significant recall.
- **Exact Change Made in `prompts/v2.txt`**:
  Under `### OUTPUT FORMAT`, updated the explanation requirement:
  ```diff
  - - "reason": A concise explanation of at most two sentences.
  + - "reason": Exactly ONE concise sentence explaining the determination (never write more than one or two sentences).
  ```
  All other elements (catalogue data, evaluator, provider, model `claude-haiku-4-5-20251001`, timeout, and execution settings) remained completely identical.

---

## 2. Measured Effect on Development Set (A01 - A40)

| Metric | Baseline (v1) | Candidate (v2) | Delta |
| :--- | :--- | :--- | :--- |
| **Gold Claims (G)** | 376 | 376 | 0 |
| **Accepted Predictions (P)** | 271 | 329 | +58 |
| **Exact Span Matches (M)** | 270 | 326 | +56 |
| **Correctly Labeled Matches (C)** | 265 | 313 | +48 |
| **Extraction Precision (M/P)** | 0.9963 (99.6%) | 0.9909 (99.1%) | -0.0054 |
| **Extraction Recall (M/G)** | 0.7181 (71.8%) | 0.8670 (86.7%) | +0.1489 (+14.9%) |
| **Extraction F1** | 0.8346 | 0.9248 | +0.0902 (+9.0%) |
| **Joint Precision (C/P)** | 0.9779 (97.8%) | 0.9514 (95.1%) | -0.0265 |
| **Joint Recall (C/G)** | 0.7048 (70.5%) | 0.8324 (83.2%) | +0.1276 (+12.8%) |
| **Joint F1** *(Primary Metric)* | **0.8192** | **0.8879** | **+0.0687 (+6.9%)** |
| **Coverage (C/G)** | 0.7048 | 0.8324 | +0.1276 |
| **Answer Errors Count** | 12 | 5 | -7 (58% error reduction) |

---

## 3. Regressions and Trade-Off Analysis
- **Observed Regressions**:
  Precision saw a negligible drop of ~2.6% (from 97.79% to 95.14%) as 58 additional claims were extracted across newly recovered answers.
- **Analysis**:
  The targeted change successfully recovered all 5 answers previously rejected due to reason length violations (`A03`, `A05`, `A20`, `A21`, `A23`). Because the model maintained high factual alignment, the newly accepted claims drove Joint F1 up significantly from 0.8192 to 0.8879.

---

## 4. Final Check Runs (A41 - A50)
- **v1 Check Artifacts**: `reports/v1_check_report.json`, `reports/v1_check_report.md`
- **v2 Check Artifacts**: `reports/v2_check_report.json`, `reports/v2_check_report.md`
- *Note: As per specification, all quality metrics for the check split remain `null` in the reports; predictions and outcomes are frozen for evaluation by the reviewer using private ground truth.*

---

## 5. Development Effort, Limitations & Unfinished Work
- **Time Spent**: ~2.5 hours total across design, implementation, testing, and benchmark execution.
- **System Limitations**:
  - Processing is sequential (as requested) rather than concurrent.
  - LLM quote matching requires strict verbatim reproduction from source answers.
- **Unfinished Work / Future Improvements**:
  - Implement automatic exponential backoff for provider rate limit spikes.
  - Implement automated database migration tooling (e.g., Alembic).

---

## 6. Disclosure of AI Assistance & Self-Verification
- **AI Tool Used**: Antigravity IDE (Google DeepMind Advanced Agentic Coding Assistant).
- **Assistance Scope**:
  - Codebase structure and schema setup.
  - Fast authoring of Pytest suites for deterministic arithmetic and security verification.
  - Route handlers for FastAPI.
- **Candidate Self-Verification**:
  - Manually audited code-point offset calculations `ai_answer[start:end]` and quote matching.
  - Verified SHA-256 integrity of the three input CSVs.
  - Reviewed the arithmetic benchmark test ($G=10, P=10, M=8, C=7 \implies \text{extraction}=0.80, \text{joint}=0.70$).
  - Inspected error logs and designed the targeted v2 prompt rule change.
