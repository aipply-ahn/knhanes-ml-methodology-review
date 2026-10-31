# Coding audit (Claude Code + Codex), 2026-10-28/29 — summary

Scope: RC01-RC46 judgements of the 193 core studies (8,878 cells); protocol PROTOCOL.md (three files: claude.jsonl,
codex.jsonl, broadcast.jsonl). Stopped after round 6 (no accepted change, no open dispute).

| Round | Scope (cells) | Claude findings | Codex findings | Applied |
|---|---|---|---|---|
| 1 | 8,878 (all) | 657 | 736 (705 cells) | 361 agreed + 630 adjudicated (RULES_r1) |
| 2 | 983 | 20 | 17 + 8 replies | 31 (RULES_r2) |
| 3 | 451 | 25 | 20 + 3 replies | 35 (RULES_r3) |
| 4 | 393 | 26 | 16 + 6 replies | 34 (RULES_r4: final RC17) |
| 5 | 211 | 5 | 10 + 8 replies | 13 |
| 6 | 11 | 1 | 0 | 0 (stop) |

Final judgements: results/derived/checklist_v18_scores.json (tools/checklist_v18.py; overrides.json, 1,054 cells).
Raw-code corrections (author: "원시 코드도 고쳐"): 34 cells appended to additional_file_review/LOOP_RECORD_CORRECTIONS.tsv
(Final model fully specified 19, Outcome rebuildable 10, Strata/PSUs 5), new record handler for "Outcome rebuildable",
REP17 'No' = partly reported; full rebuild (review_corrections_20261023/rebuild.sh) twice. Snapshot before:
pre_rebuild_snapshot.tar.gz. Changed published numbers: final model fully specified 13 -> 24; outcome rebuildable
97 -> 107; strata/PSUs 30 -> 31 (ranking studies 27 -> 28; sensitivity 9.5% -> 10.1%); mean % of elements completely
reported by period 34.7/36.4/36.1/46.5 -> 35.4/36.8/36.3/46.5.
Kept as definitional differences (raw_code_notes.json; Additional Data 1 'Scoring definitions'): RC09, RC30, RC31,
RC33, RC43 and RC39-RC45 for three tree-only studies. Not changed for lack of a record handler: KHM037 THR02 cutoffs,
KHM184/KHM192 POP08/POP10.
Open source issue: KHM220 ML sample description apparently copied from KHM259.
