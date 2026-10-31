# Coding audit protocol: Claude Code + Codex, round-based (2026-10-28)

Goal: every RC01-RC46 judgement of the 193 core studies (8,878 cells) matches its criterion in the RC Codebook, and
the raw protocol codes the mapped items rely on are correct. Repeat rounds until neither reviewer raises a new issue.

## Three communication files (this folder), all append-only JSON Lines (one object per line, never edit old lines)
| File | Written by | Content |
|---|---|---|
| claude.jsonl | Claude Code only | Claude's findings and Claude's integration decisions |
| codex.jsonl | Codex only | Codex's findings and Codex's replies to rejected findings |
| broadcast.jsonl | both (append one line at a time) | events: round start with scope, review done, integration done, stop |

Every line has "ts" (ISO time), "round" and "from" ("claude" or "codex").

### Line types
- Finding (claude.jsonl or codex.jsonl):
  {"kind": "finding", "round": 1, "from": "codex", "study_id": "KHM001", "item": "RC24", "current": 0, "proposed": 1,
   "type": "value | mapping | criterion-ambiguity | raw-code", "evidence": "verbatim quote <= 40 words",
   "location": "page/section/table", "reason": "why the criterion is or is not met"}
- Integration decision (claude.jsonl only): {"kind": "decision", "round": 1, "finding_from": "codex", "study_id": ...,
  "item": ..., "decision": "accept | reject | modify", "value": 1, "reason": "..."}
- Reply (codex.jsonl or claude.jsonl): {"kind": "reply", "round": 2, "study_id": ..., "item": ..., "agree": true|false, "reason": "..."}
- Broadcast events (broadcast.jsonl):
  {"event": "round_start", "round": N, "from": "claude", "scope": "all" | [["KHM001","RC24"], ...], "scores_version": "..."}
  {"event": "review_done", "round": N, "from": "codex" | "claude", "findings": <count>}
  {"event": "integration_done", "round": N, "from": "claude", "accepted": n, "rejected": n, "rule_changes": [...]}
  {"event": "stop", "round": N, "from": "claude", "reason": "no accepted change and no open dispute"}

## Roles
- Claude Code: reviewer A and the only integrator; the only one that edits code, override files, workbook, figures, manuscript.
- Codex: reviewer B; writes only codex.jsonl and its own lines in broadcast.jsonl.

## Sources of truth (read only)
- Criteria: sheet "RC Codebook" of manuscript/KNHANES_ML_review_Additional_Data_1.xlsx.
- Judgements: results/derived/checklist_v17_scores.json (items[].id; studies[sid].items[idx]; evidence) — the file named
  in the latest round_start "scores_version".
- Full texts: references/md/<canonical_key>.md (PDFs in references/pdf/); study list in
  prompts/implementation_records/v15_recode/batch_*_input.json.

## Round flow
1. Claude writes round_start in broadcast.jsonl (round 1 scope: all 193 studies x 46 items; later rounds: the cells
   changed at the last integration, disputed cells and cells affected by a rule change).
2. Both review independently. Do not read the other reviewer's findings of the current round before writing
   your review_done. Record only errors or ambiguities, with quote and location; a correct judgement is not recorded.
3. After both review_done lines exist, Claude integrates: same proposal from both -> apply; one-sided or different ->
   re-read the source and decide with a reason; criterion-ambiguity -> one rule for all 193 studies (criteria are never
   changed to fit numbers). Claude regenerates scores, workbook and figures and writes integration_done.
4. In the next round each reviewer may reply to decisions on its own findings (kind "reply").
5. Stop when a round has no accepted change and no open dispute. Manuscript numbers are updated once at the end.

## Raw-code schema proposals (author, 2026-10-29)
Whenever coding or auditing suggests that the raw coding frame itself should change (an item, its value set, a derived
column or a record handler), record it separately, never as a cell finding: append one line to
raw_schema_proposals.jsonl, e.g.
{"ts": "...", "from": "codex", "items": "VI16", "problem": "...", "proposal": "...", "affects": "...", "examples": ["KHM033"]}
Claude Code keeps RAW_SCHEMA_PROPOSALS.md (numbered S01...) in sync and reports open proposals to the author; nothing is
applied without the author's decision.


## Framework-change proposals during raw coding (user instruction, 2026-10-29)

While coding or correcting raw records, both Claude and Codex must separately record suggestions that would require
changing the coding framework. Use `framework_change_proposals.jsonl` in this folder, not the study-value correction
log. This auxiliary register adds append permission for both reviewers to the role restrictions above; ownership of
production files and integration remains unchanged.

- A wrong value under an adequate existing definition is a coding correction, not a framework proposal.
- A missing implementation handler is an implementation issue. A legitimate difference between raw-code and checklist
  definitions is a mapping explanation; neither automatically justifies changing the framework.
- Record a framework proposal when definitions, allowed values, units, dependencies or available fields cannot adequately
  represent source information, or repeatedly conflate distinct concepts. Include an alternative using existing or derived
  fields before proposing a new locked item.
- Record the suggestion when discovered; continue coding under the current framework. If the current framework cannot
  express a source fact, use its existing NR/UNC/NA definitions as appropriate, explain the limitation, and link the proposal.
  Do not silently invent a value or interpret missing reporting as explicit nonuse.
- A proposal entry is advisory, not an applied schema change. Do not change item IDs, definitions, allowed values,
  historical records or manuscript numbers merely because a proposal was recorded.

The register is append-only JSON Lines. Use one complete JSON object per line and a file lock for concurrent appends.
Never edit old entries. Proposal IDs must include the author and a timestamp to avoid collisions. A later review,
correction or decision is a new entry referencing the same `proposal_id`.

Required proposal fields:
- `ts`, `kind` = `framework_proposal`, `proposal_id`, `from`, `status` = `proposed`;
- `category`: `definition`, `allowed_values`, `item_addition`, `item_split`, `unit`, `dependency`, `provenance`, or `derived_mapping`;
- `items`: affected existing item IDs; `current_framework`: current definition/structure and its source location;
- `problem`: what cannot be represented or what is conflated, with concrete examples;
- `examples`: study IDs and source/evidence locations (quote the source when the issue concerns its wording);
- `proposed_change`, `alternative_without_schema_change`, `reason`;
- `impact`: effects on existing values, backward compatibility, affected studies, recoding needs and derived outputs.
  Mark unknown scope explicitly instead of inventing a count.

The integrator records a review or decision as a new `framework_decision` entry with `ts`, `from`, `proposal_id`,
`status` (`accepted`, `rejected`, or `deferred`) and `reason`. Accepted proposals still need a documented framework
version, affected-record scope and migration/recalculation plan before implementation. Open advisory proposals do not
by themselves reopen a completed checklist audit; an actual unresolved coding error follows the audit protocol.
