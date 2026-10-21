# Evaluation Run Report: V2 (Development)

## Run Metadata
- **Timestamp**: 2026-10-21T08:21:07.969512+00:00
- **Split**: `development`
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
- **Scheduled Answers**: 40
- **Successful Answers**: 35
- **Empty Claims Answers**: 0
- **Error Answers**: 5

## Quality Metrics
| Metric | Count / Value |
| :--- | :--- |
| **Gold Claims (G)** | 376 |
| **Accepted Predictions (P)** | 329 |
| **Exact Span Matches (M)** | 326 |
| **Correctly Labeled Matches (C)** | 313 |
| **Extraction Precision (M/P)** | 0.990881 |
| **Extraction Recall (M/G)** | 0.867021 |
| **Extraction F1** | 0.924823 |
| **Joint Precision (C/P)** | 0.951368 |
| **Joint Recall (C/G)** | 0.832447 |
| **Joint F1** | 0.887943 |
| **Coverage (C/G)** | 0.832447 |

## Detailed Accounting Lists
- **Missed Gold IDs (50)**: A02:306:506, A02:507:689, A02:691:875, A02:876:1084, A02:1085:1272, A02:1469:1659, A02:1660:1813, A02:1815:2039, A02:2040:2223, A02:2224:2372, A12:335:515, A12:516:674, A12:676:871, A12:872:1032, A12:1229:1378, A12:1379:1559, A12:1560:1741, A12:1743:1916, A12:1917:2113, A16:455:618, A23:371:548, A24:306:498, A24:499:683, A24:685:890, A24:891:1091, A24:1092:1287, A24:1484:1675, A24:1676:1854, A24:1856:2025, A24:2026:2214, A24:2215:2381, A35:1442:1606, A36:324:496, A36:497:687, A36:689:891, A36:892:1059, A36:1256:1463, A36:1464:1650, A36:1651:1822, A36:1824:1978, A39:306:493, A39:494:691, A39:693:869, A39:870:1062, A39:1063:1245, A39:1442:1614, A39:1615:1792, A39:1794:1971, A39:1972:2172, A39:2173:2360
- **Unmatched Prediction IDs (3)**: A16:513:618, A23:447:548, A35:1500:1606
- **Matched Wrong-Label Count**: 13

## Answer Outcomes
| Answer ID | Status | Claims Count | Latency (ms) | Error Message |
| :--- | :--- | :--- | :--- | :--- |
| `A01` | success | 9 | 12705.8 | - |
| `A02` | error | 0 | 14414.5 | Quote not found in ai_answer: 'Water damage remains excluded from the standard India manufacturer warranty covering CloudNote Studio after an authorized purchase.' |
| `A03` | success | 9 | 13157.1 | - |
| `A04` | success | 11 | 16004.3 | - |
| `A05` | success | 8 | 11220.1 | - |
| `A06` | success | 10 | 14838.9 | - |
| `A07` | success | 8 | 12506.1 | - |
| `A08` | success | 10 | 12658.0 | - |
| `A09` | success | 9 | 13308.2 | - |
| `A10` | success | 10 | 13447.3 | - |
| `A11` | success | 10 | 13091.2 | - |
| `A12` | error | 0 | 21186.0 | Predicted claims failed validation: Claim #4: reason must be <= 2 sentences, got 3 sentences: 'The 2026 catalogue prices are Go at INR 1999 and Max at INR 3499, making the difference INR 1500; however, this is the correct difference, so the claim is actually supported. Let me recalculate: 3499 - 1999 = 1500. The claim is correct.' |
| `A13` | success | 10 | 14565.8 | - |
| `A14` | success | 9 | 13179.8 | - |
| `A15` | success | 10 | 14074.1 | - |
| `A16` | success | 9 | 12832.4 | - |
| `A17` | success | 11 | 15974.0 | - |
| `A18` | success | 8 | 12017.2 | - |
| `A19` | success | 10 | 12994.2 | - |
| `A20` | success | 8 | 11737.0 | - |
| `A21` | success | 8 | 12211.5 | - |
| `A22` | success | 10 | 14614.9 | - |
| `A23` | success | 8 | 11116.2 | - |
| `A24` | error | 0 | 20994.4 | Predicted claims failed validation: Claim #7: reason must be <= 2 sentences, got 3 sentences: 'The price increased from INR 1199 to INR 1499, a difference of INR 300, but the claim states the price was raised by INR 300 when it actually increased by INR 300 (1499 - 1199 = 300). Wait, recalculating: 1499 - 1199 = 300. The claim is correct.' |
| `A25` | success | 9 | 12913.5 | - |
| `A26` | success | 10 | 13635.0 | - |
| `A27` | success | 9 | 12784.0 | - |
| `A28` | success | 10 | 14252.9 | - |
| `A29` | success | 9 | 21078.1 | - |
| `A30` | success | 11 | 14638.7 | - |
| `A31` | success | 10 | 13097.5 | - |
| `A32` | success | 9 | 13301.9 | - |
| `A33` | success | 11 | 14390.6 | - |
| `A34` | success | 8 | 19531.1 | - |
| `A35` | success | 10 | 13724.4 | - |
| `A36` | error | 0 | 19237.5 | Predicted claims failed validation: Claim #6: reason must be <= 2 sentences, got 3 sentences: "The 2025 price was INR 999 and the 2026 price is INR 1299, a difference of INR 300; however, the claim states the price was 'raised by INR 300' when it was actually raised by INR 300 (1299 - 999 = 300), so this is actually supported. Let me recalculate: 1299 - 999 = 300. The claim is correct." |
| `A37` | success | 10 | 13798.7 | - |
| `A38` | success | 9 | 12771.0 | - |
| `A39` | error | 0 | 13399.9 | Quote not found in ai_answer: 'Water damage remains excluded from the standard India manufacturer warranty covering CloudNote Air after an authorized purchase.' |
| `A40` | success | 9 | 13889.4 | - |
