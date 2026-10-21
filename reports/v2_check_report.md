# Evaluation Run Report: V2 (Check)

## Run Metadata
- **Timestamp**: 2026-10-21T08:26:20.912266+00:00
- **Split**: `check`
- **Prompt Version**: `v2`
- **Provider**: `anthropic`
- **Model**: `claude-haiku-4-5-20251001`
- **Git Revision**: `unversioned`
- **Dataset Version**: `long-brand-answers-50-v4`
- **Evaluator**: `sentence-spans-and-labels-v4`
- **Fact Version**: `speaker-catalogue-v4`
- **Timeout**: 30.0s
- **Max Turns**: 3

## File Integrity Checksums (SHA-256)
- `answers.csv`: `fa28e813ea54b4e5ea985585f22f084d826241e1182accbc27ace17066125724`
- `brand_facts.csv`: `2190d40fad2dd167ef2437956c43d595aaf2554ea673a4789b9343cb7e2936f2`
- `development_gold.csv`: `afe84cc78f304afb6a4aaa505dd7504af80fcbf8bc507806aa5ff0aab6bf4850`

## Outcome Counts
- **Scheduled Answers**: 10
- **Successful Answers**: 8
- **Empty Claims Answers**: 0
- **Error Answers**: 2

## Quality Metrics
> [!NOTE]
> Quality metrics (G, M, C, Precision, Recall, F1) are `null` for the check split as per specification.
> Predictions and outcomes have been frozen and saved for evaluation against private ground truth.

## Answer Outcomes
| Answer ID | Status | Claims Count | Latency (ms) | Error Message |
| :--- | :--- | :--- | :--- | :--- |
| `A41` | success | 9 | 13687.6 | - |
| `A42` | error | 0 | 14979.2 | Quote not found in ai_answer: 'Water damage remains excluded from the standard India manufacturer warranty covering ClearTrail Plus after an authorized purchase.' |
| `A43` | success | 9 | 13040.4 | - |
| `A44` | success | 10 | 13253.0 | - |
| `A45` | success | 9 | 12883.4 | - |
| `A46` | success | 11 | 15170.6 | - |
| `A47` | success | 8 | 17732.6 | - |
| `A48` | error | 0 | 13504.6 | Quote not found in ai_answer: 'Water damage remains excluded from the standard India manufacturer warranty covering StoneWave Go after an authorized purchase.' |
| `A49` | success | 8 | 11242.3 | - |
| `A50` | success | 10 | 13824.9 | - |
