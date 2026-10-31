#!/usr/bin/env python3
"""Prompt 106 coordinator corrections for two criterion-A single-extraction records (found by the S5/S7 code check).

KHM251 DAT14: the extractor coded OTHER with the rationale "components not reported (32 feature variables
  unspecified)".  In the protocol OTHER means another KNHANES component; an unreported component set is NR.
  The final value becomes NR; the P2 answer is kept unchanged as the extraction record.
KHM254 analytic output: the purpose audit's fallback code OTHER_OR_UNCLEAR_OUTPUT is published as OTHER (as for
  every earlier health-focused study without a coded output); the v1.3 record uses the published code.
Idempotent; recomputes protocol_items_sha256 like tools/integrate_criterion_a.py."""
import hashlib
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
FINAL = ROOT / "data/protocol_v1_2/final"


def write(path, d):
    path.write_text(json.dumps(d, ensure_ascii=False, indent=2) + "\n")


def main():
    p = FINAL / "KHM251_final.json"
    d = json.loads(p.read_text())
    row = d["protocol_items"]["DAT14"][0]
    if row["value"] == ["OTHER"]:
        row["value"] = ["NR"]
        row["rationale"] = ("NR: the abstract does not report which KNHANES components supplied the 32 features "
                            "(coordinator correction, prompt 106: P2 coded OTHER for 'not reported').")
        row["review_stage"] = "COORDINATOR"
        d["protocol_items_sha256"] = hashlib.sha256(json.dumps(d["protocol_items"], ensure_ascii=False, sort_keys=True).encode()).hexdigest()
        d.setdefault("adjudication", {}).setdefault("coordinator_corrections", []).append(
            {"item_id": "DAT14", "from": ["OTHER"], "to": ["NR"], "prompt": 106, "reason": "OTHER is a component; an unreported component set is NR"})
        write(p, d)
    q = FINAL / "KHM254_final.json"
    e = json.loads(q.read_text())
    v13 = e["adjudication"]["purpose_evidence_v1_3"]
    changed = False
    for r in v13.get("analytic_output_records", []):
        if r["output_code"] == "OTHER_OR_UNCLEAR_OUTPUT":
            r["output_code"] = "OTHER"; changed = True
    if changed:
        e["adjudication"].setdefault("coordinator_corrections", []).append(
            {"field": "purpose_evidence_v1_3.analytic_output_records", "from": "OTHER_OR_UNCLEAR_OUTPUT", "to": "OTHER", "prompt": 106,
             "reason": "published output code for a study without a coded output"})
        write(q, e)
    print("KHM251 DAT14", json.loads(p.read_text())["protocol_items"]["DAT14"][0]["value"],
          "| KHM254 outputs", [r["output_code"] for r in json.loads(q.read_text())["adjudication"]["purpose_evidence_v1_3"]["analytic_output_records"]])


if __name__ == "__main__":
    main()
