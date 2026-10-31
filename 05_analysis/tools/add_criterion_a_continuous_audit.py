#!/usr/bin/env python3
"""Prompt 106: continuous-outcome interpretation audit for the four criterion-A continuous studies.
Same rule as results/derived/continuous_interpretation_audit.json (independent full-text audit; VI01 is
classification-only).  All four fit regression trees and interpret the split variables and their order as the main
influencing factors, which is model-based interpretation by tree rules.  Evidence is the extracted evidence record.
Idempotent."""
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
P = ROOT / "results/derived/continuous_interpretation_audit.json"
ADD = {
    "KHM229": "CHAID trees for fruit and vegetable intake frequency; the split variables (residence, sex, income) are reported as the factors influencing intake.",
    "KHM232": "CART regression tree for body-fat percentage; the four split predictors and their levels are reported as the estimating factors.",
    "KHM239": "CRT regression trees for EQ-5D in urban and rural residents; the split variables are interpreted as the factors defining the lowest-quality-of-life groups.",
    "KHM254": "CHAID regression trees for systolic and diastolic blood pressure; the first split (age) and later splits are interpreted as the associated factors.",
}


def source(sid):
    d = json.loads((ROOT / f"data/protocol_v1_2/final/{sid}_final.json").read_text())
    ev = [e for e in d["evidence_registry"] if any(w in (e.get("excerpt") or "").lower() for w in ("split", "node", "decision tree", "levels and 4 predictors"))]
    e = ev[0]
    return d["canonical_key"], f"{e['source_file']}:page {e.get('pdf_page')}"


def main():
    d = json.loads(P.read_text())
    have = {s["study_id"] for s in d["studies"]}
    for sid, why in ADD.items():
        if sid in have:
            continue
        key, src = source(sid)
        d["studies"].append({"study_id": sid, "canonical_key": key, "status": "USED", "methods": ["TREE_RULE"],
                             "evidence": why, "source": src, "added": "prompt 106 criterion-A single review"})
    n = len(d["studies"])
    d["denominator"] = n
    used = [s for s in d["studies"] if s["status"].startswith("USED")]
    d["summary"]["explicit_model_based_importance_or_interpretation"] = len(used)
    d["summary"]["no_explicit_method_located"] = n - len(used)
    d["summary"]["tree_rule"] = sum("TREE_RULE" in s["methods"] for s in d["studies"])
    P.write_text(json.dumps(d, ensure_ascii=False, indent=2) + "\n")
    print(n, d["summary"])


if __name__ == "__main__":
    main()
