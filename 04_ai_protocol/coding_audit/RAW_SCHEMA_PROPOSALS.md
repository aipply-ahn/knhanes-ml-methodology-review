# Raw-code schema proposals (원시 코드 틀 변경 의견)

Opinions that the raw coding frame itself should change, kept apart from cell-level findings; nothing is applied
without the author's decision. Nature: STRUCT = change to the raw structure (new item/value set/handler),
ERRFIX = correction of an actual coding error, DEFN = change to the definition of a reported result.
Decision rule (author, 2026-10-29): adopt a change only when the current codes cannot separate two study states that
matter for the paper's conclusions; storing more detail is not a reason. New entries go to raw_schema_proposals.jsonl
(fields: ts, from, nature, items, problem, proposal, affects, examples).

| ID | Nature | Item(s) | Problem | Decision (2026-10-29) | Status |
|---|---|---|---|---|---|
| S01 | DEFN | VI16 | Subgroup comparisons of separately built models counted as stability checks | Keep VI16; what counts as a stability check is a criterion question (RC43 vs S6 definition), documented as a definitional difference | closed (no change) |
| S02 | STRUCT | POP10, POP11 | Total excluded only, not per step | Hold; RC09 already judges per-step reporting | on hold |
| S03 | ERRFIX | POP08, POP10 | KHM184, KHM192 flow-chart values not coded | Cells corrected (37,753; 30,341 / 30,610) with a minimal handler | applied |
| S04 | STRUCT | THR01/THR02 | Cutoff not linked to the final model | Hold; RC31 judges reporting of the final model's cutoff | on hold |
| S05 | STRUCT | MET_CI | SDs over resamples not captured | Keep; RC33 rule accepts SDs | closed (no change) |
| S06 | STRUCT | MET_AUROC_R | Data partition of AUROC not recorded | Hold; RC30 judges whether the partition is stated | on hold |
| S07 | STRUCT | MET_CAL* | Calibration error has no slot | Not adopted | closed (rejected) |
| S08 | DEFN/ERRFIX | VI01 | Tree split variables counted as a ranking | Full texts of KHM224, KHM241, KHM252 checked: tree structure only; VI01 corrected to No (150 -> 147 rankings) | applied |
| S09 | STRUCT | PRE04 | Per-variable vs pooled missingness not coded | Keep; RC17 judges it | closed (no change) |
| S10 | ERRFIX | REP17 handler | Not fully specified mapped to Not reported | Partly reported | applied |
| S11 | STRUCT | OUT16 handler | No handler for outcome rebuildable | Handler added | applied |
| S12 | STRUCT | POP12, POP14 | How class counts were reported | Hold; RC13 judges it | on hold |
| S13 | STRUCT | source issues | Suspected errors in the source reports | Internal audit record only (SOURCE_ISSUES.md), not a study-level analysis variable | applied (internal) |
| S14 | ERRFIX | FUN_TRANSPORT, VAL08 | 5 studies with separate evaluation data coded ABSENT (KHM013, KHM020, KHM058, KHM137, KHM195) | Pending author decision | open |
