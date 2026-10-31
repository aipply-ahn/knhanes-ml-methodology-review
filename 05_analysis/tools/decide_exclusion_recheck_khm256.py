#!/usr/bin/env python3
"""Prompt 106: coordinator decision on the second exclusion-recheck candidate (KHM256, zhang2026relationship).

The blinded P2 extraction passed, but the full text does not support KNHANES as the data source: covariates are
NHANES definitions (household income relative to the poverty line <=1.3 / 1.3-3.5 / >3.5 taken from
'demographic variable files'; Healthy Eating Index-2015), and GAD-7 data are claimed for 2001, 2005 and 2007-2023,
whereas KNHANES introduced GAD-7 only in 2021.  Same rule as KCI ART003346494 (KNHANES use not confirmed): the
record stays EXCLUDE (no eligible KNHANES analysis).  The P2 packet is kept as an audit record, not integrated.
Idempotent."""
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
UID, SID = "10.5114/aoms/221898", "KHM256"
WHY = ("KNHANES use not confirmed on full-text check: NHANES covariate definitions (poverty-income ratio from demographic "
       "files; HEI-2015) and GAD-7 claimed for 2001-2023 although KNHANES introduced GAD-7 in 2021; XGBoost/SHAP otherwise "
       "met criterion A (blinded P2 record kept as audit, not integrated)")


def main():
    p = ROOT / "results/derived/criterion_a_rescreen.json"
    R = json.loads(p.read_text())
    x = R["exclusion_recheck"]
    if any(a["study_id"] == SID for a in x["added"]):
        x["added"] = [a for a in x["added"] if a["study_id"] != SID]
        x["kept_excluded"][UID] = WHY
        x["extracted_then_excluded"] = {SID: {"uid": UID, "reason": WHY, "p2_packet": f"data/protocol_v1_2/P2_blinded/{SID}_P2.json"}}
        p.write_text(json.dumps(R, ensure_ascii=False, indent=2) + "\n")
    t = ROOT / "data/protocol_v1_2/criterion_a_additions.tsv"
    lines = [l for l in t.read_text().splitlines() if not l.startswith(SID + "\t")]
    t.write_text("\n".join(lines) + "\n")
    v = ROOT / "results/derived/verdicts.json"
    V = json.loads(v.read_text())
    assert V[UID]["verdict"] == "EXCLUDE"
    if "coordinator_recheck" not in V[UID]:
        V[UID]["coordinator_recheck"] = {"date": "2026-09-30", "previous_reason": V[UID]["reason"]}
        V[UID]["reason"] = "NO_ML_OR_DATASET: " + WHY
        v.write_text(json.dumps(V, ensure_ascii=False, indent=2) + "\n")
    print("added:", [a["study_id"] for a in x["added"]], "| tsv rows:", len(lines) - 1)


if __name__ == "__main__":
    main()
