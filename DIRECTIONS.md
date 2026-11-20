# Step 3: the author's directions

The author gave directions as rules for the remaining cases, never as a decision on an individual record or coding
(except the step-5 adjudication of selection records and the pilot coding decisions listed below). Dates are 2026.

## Study selection

| Date | Direction | Implemented in |
|---|---|---|
| before 2 Nov | Every exclusion on which both systems agree is re-examined once by both; discordant re-examinations go through up to three consensus rounds; records still in disagreement are adjudicated by the author | `02_selection/protocol/SCREENING_PROTOCOL.md` (stage `challenge`), `prompts/*_challenge.md` |
| 4-5 Nov | Records that are not research reports by their metadata type (code, data or supplement deposits, conference abstracts, including abstracts published as journal-article records) are removed before screening (protocol amendments 3-5) | `SCREENING_PROTOCOL.md` |
| 5 Nov | Second database records of an included article are merged in deduplication as documented exceptions (amendments 6-7) | `SCREENING_PROTOCOL.md`, `01_search/dedup_rule_merges.tsv` |
| 5 Nov | Retracted publications are excluded | `ELIGIBILITY_PROTOCOL.md` |

## Data coding

| Date | Direction | Step-4 check or step-5 rule | Implemented in |
|---|---|---|---|
| 16 Nov | A difference that does not change what a reader takes from the review table is settled by a structural rule (the side with more printed numbers, then more value entries, then A) when both systems judge it not material | materiality | `code/coding_material.py` |
| 16 Nov | An inconsistency flagged by one coding only is settled by a factual check of the cited places by both systems | inconsistency flag | `code/coding_inconsistency.py` |
| 17 Nov | Differences of form and differences in how a rule applies are settled by rule; only substantive differences go further. Rule-reading differences are checked again blind (the two codings anonymised) | form, rule or substance; blind rule check | `code/coding_triage.py`, `code/coding_rule_blind.py` |
| 18 Nov | The rest is not settled one case at a time: for each item in dispute, both systems find the recurring causes and agree on one minimal common rule in at most three cross-checked rounds (round 3 tests both candidates on other cases), which is applied to every open case of the item | field rule | `code/coding_field_rules.py` |
| 19 Nov | For an item without an agreed rule, the rule is taken from review comments accepted by the author or, otherwise, the suggested rule is adopted after checking that it does not contradict the item definition; it is written in short form by one system and checked by the other, and applied to every open case | step 5 | `code/coding_field_decide.py` |
| 19-20 Nov | What remains is settled by rule, without a judgement on the case: the coding is written under the rule once more; if still not accepted, the coding a checker accepted under the rule is kept; otherwise the item is coded unclear | step 5 (fallback) | `code/coding_rule_fix.py` |
| 17 Nov (pilot) | In the ten pilot reports, open codings were settled by review comments that the author accepted | step 5 (pilot) | `code/coding_apply_decisions.py` |
