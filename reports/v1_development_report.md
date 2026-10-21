# Evaluation Run Report: V1 (Development)

## Run Metadata
- **Timestamp**: 2026-10-21T08:08:59.971652+00:00
- **Split**: `development`
- **Prompt Version**: `v1`
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
- **Successful Answers**: 28
- **Empty Claims Answers**: 0
- **Error Answers**: 12

## Quality Metrics
| Metric | Count / Value |
| :--- | :--- |
| **Gold Claims (G)** | 376 |
| **Accepted Predictions (P)** | 271 |
| **Exact Span Matches (M)** | 270 |
| **Correctly Labeled Matches (C)** | 265 |
| **Extraction Precision (M/P)** | 0.99631 |
| **Extraction Recall (M/G)** | 0.718085 |
| **Extraction F1** | 0.834621 |
| **Joint Precision (C/P)** | 0.97786 |
| **Joint Recall (C/G)** | 0.704787 |
| **Joint F1** | 0.819165 |
| **Coverage (C/G)** | 0.704787 |

## Detailed Accounting Lists
- **Missed Gold IDs (106)**: A02:306:506, A02:507:689, A02:691:875, A02:876:1084, A02:1085:1272, A02:1469:1659, A02:1660:1813, A02:1815:2039, A02:2040:2223, A02:2224:2372, A03:335:505, A03:506:687, A03:689:861, A03:862:1043, A03:1240:1409, A03:1410:1563, A03:1564:1742, A03:1744:1917, A03:1918:2069, A05:371:531, A05:532:697, A05:699:890, A05:891:1095, A05:1292:1467, A05:1468:1651, A05:1652:1828, A05:1830:1980, A12:335:515, A12:516:674, A12:676:871, A12:872:1032, A12:1229:1378, A12:1379:1559, A12:1560:1741, A12:1743:1916, A12:1917:2113, A20:306:485, A20:486:662, A20:664:855, A20:856:1046, A20:1243:1434, A20:1435:1607, A20:1608:1752, A20:1754:1949, A21:335:558, A21:559:722, A21:724:892, A21:893:1087, A21:1284:1478, A21:1479:1676, A21:1677:1848, A21:1850:2028, A23:371:548, A23:549:744, A23:746:907, A23:908:1098, A23:1295:1477, A23:1478:1662, A23:1663:1854, A23:1856:2056, A24:306:498, A24:499:683, A24:685:890, A24:891:1091, A24:1092:1287, A24:1484:1675, A24:1676:1854, A24:1856:2025, A24:2026:2214, A24:2215:2381, A29:306:453, A29:454:615, A29:617:788, A29:789:975, A29:1172:1369, A29:1370:1549, A29:1550:1701, A29:1703:1882, A29:1883:2066, A34:306:479, A34:480:656, A34:658:808, A34:809:958, A34:1155:1315, A34:1316:1496, A34:1497:1683, A34:1685:1854, A35:335:520, A35:521:687, A35:689:883, A35:884:1070, A35:1071:1245, A35:1442:1606, A35:1607:1804, A35:1806:1969, A35:1970:2129, A35:2130:2321, A36:324:496, A36:497:687, A36:689:891, A36:892:1059, A36:1256:1463, A36:1464:1650, A36:1651:1822, A36:1824:1978, A39:494:691
- **Unmatched Prediction IDs (1)**: A39:563:691
- **Matched Wrong-Label Count**: 5

## Answer Outcomes
| Answer ID | Status | Claims Count | Latency (ms) | Error Message |
| :--- | :--- | :--- | :--- | :--- |
| `A01` | success | 9 | 12873.1 | - |
| `A02` | error | 0 | 14250.2 | Quote not found in ai_answer: 'Water damage remains excluded from the standard India manufacturer warranty covering CloudNote Studio after an authorized purchase.' |
| `A03` | error | 0 | 12865.7 | Predicted claims failed validation: Claim #6: reason must be <= 2 sentences, got 3 sentences: 'CloudNote Air weighs 350 grams, not 1100 grams. CloudNote Studio weighs 1100 grams. The weights do not match.' |
| `A04` | success | 11 | 16067.3 | - |
| `A05` | error | 0 | 12194.6 | Predicted claims failed validation: Claim #0: reason must be <= 2 sentences, got 3 sentences: 'The catalogue states 16 hours at 50% volume with EQ off and new battery in laboratory test. 16 hours = 960 minutes, not 1020 minutes. This is contradicted.' |
| `A06` | success | 10 | 16655.3 | - |
| `A07` | success | 8 | 12468.5 | - |
| `A08` | success | 10 | 12525.5 | - |
| `A09` | success | 9 | 14564.1 | - |
| `A10` | success | 10 | 13835.3 | - |
| `A11` | success | 10 | 13499.4 | - |
| `A12` | error | 0 | 15540.0 | Predicted claims failed validation: Duplicate claim_id 'A12:1229:1378' at claim #5; Claims must be in strictly increasing start_char order: #5 starts at 1229 <= previous 1229; Overlapping claim span detected: claim #5 starts at 1229 before previous ends at 1378 |
| `A13` | success | 10 | 14397.6 | - |
| `A14` | success | 9 | 14647.5 | - |
| `A15` | success | 10 | 14742.9 | - |
| `A16` | success | 9 | 13446.6 | - |
| `A17` | success | 11 | 16206.3 | - |
| `A18` | success | 8 | 12368.5 | - |
| `A19` | success | 10 | 14324.2 | - |
| `A20` | error | 0 | 13142.0 | Predicted claims failed validation: Claim #1: reason must be <= 2 sentences, got 3 sentences: 'The 2025 price was INR 1,799, not INR 1,999. The 2026 price is INR 1,999. The claim that the 2025 price was already INR 1,999 is contradicted by the catalogue data.' |
| `A21` | error | 0 | 12538.2 | Predicted claims failed validation: Claim #1: reason must be <= 2 sentences, got 3 sentences: 'The catalogue states ClearTrail Plus battery_50_percent is 20 hours under the specified conditions. Converting 20 hours to minutes: 20 × 60 = 1200 minutes. The claim states 1260 minutes, which does not match the catalogue value of 1200 minutes.' |
| `A22` | success | 10 | 14673.6 | - |
| `A23` | error | 0 | 11357.6 | Predicted claims failed validation: Claim #0: reason must be <= 2 sentences, got 3 sentences: 'CloudNote Studio weighs 1100 grams, not 350 grams. CloudNote Air weighs 350 grams. The weights do not match.' |
| `A24` | error | 0 | 22107.1 | Malformed JSON output from model: Expecting value: line 1 column 1 (char 0) |
| `A25` | success | 9 | 12863.3 | - |
| `A26` | success | 10 | 13529.1 | - |
| `A27` | success | 9 | 13013.9 | - |
| `A28` | success | 10 | 14622.7 | - |
| `A29` | error | 0 | 21005.8 | Malformed JSON output from model: Expecting value: line 1 column 1 (char 0) |
| `A30` | success | 11 | 15266.4 | - |
| `A31` | success | 10 | 13002.6 | - |
| `A32` | success | 9 | 13513.3 | - |
| `A33` | success | 11 | 14915.4 | - |
| `A34` | error | 0 | 19839.2 | Malformed JSON output from model: Expecting value: line 1 column 1 (char 0) |
| `A35` | error | 0 | 15571.4 | Predicted claims failed validation: Duplicate claim_id 'A35:1806:1969' at claim #8; Claims must be in strictly increasing start_char order: #8 starts at 1806 <= previous 1806; Overlapping claim span detected: claim #8 starts at 1806 before previous ends at 1969 |
| `A36` | error | 0 | 19136.4 | Malformed JSON output from model: Expecting value: line 1 column 1 (char 0) |
| `A37` | success | 10 | 14003.0 | - |
| `A38` | success | 9 | 13008.0 | - |
| `A39` | success | 10 | 14256.4 | - |
| `A40` | success | 9 | 14206.1 | - |
