#!/usr/bin/env python3
"""Attach transparent reason codes to classification audit grades without changing judgements."""
from __future__ import annotations

import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
FINAL = ROOT / "data/protocol_v1_2/final"
PUBLISHED_CODES = {k: v["classification_reason_codes"] for k, v in json.loads((ROOT / "data/protocol_v1_3/published_classification_reason_codes.json").read_text())["records"].items()}  # prompt 106


def rows(d, key):
    return d.get("protocol_items", {}).get(key, [])


def by_unit(d, key):
    return {x.get("unit_id"): x.get("value") for x in rows(d, key)}


def included(d):
    elg = rows(d, "ELG04")
    return d.get("corpus_status", {}).get("include", bool(elg and elg[0].get("value") == "Y"))


def codes_for_outcome(rep, cred):
    codes = []
    if rep == "R0": codes.append("outcome_rule_not_reconstructable")
    if rep == "R1": codes.append("outcome_rule_partly_reconstructable")
    if cred == "C0": codes.append("outcome_circularity_or_misalignment")
    if cred == "C1": codes.append("outcome_basis_limited")
    if cred in {"CU", "UNC", None}: codes.append("insufficient_evidence")
    return codes or ["no_specific_outcome_problem_identified"]


def codes_for_predictor(rep, align, direct, proxy, post, available):
    codes = []
    if rep == "R0": codes.append("predictor_set_not_reconstructable")
    if rep == "R1": codes.append("predictor_set_partly_reconstructable")
    if direct == "Y": codes.append("target_component_used_as_predictor")
    if proxy == "Y": codes.append("near_direct_target_proxy_used")
    if post == "Y": codes.append("post_outcome_predictor")
    if available == "N": codes.append("predictor_unavailable_at_intended_use")
    if align == "C0": codes.append("target_predictor_misalignment")
    if align in {"CU", "UNC", None} or any(x in {"UNC", None} for x in (direct, proxy, post)):
        codes.append("insufficient_evidence")
    return list(dict.fromkeys(codes)) or ["no_specific_target_predictor_problem_identified"]


def main():
    changed = classification = 0
    for path in sorted(FINAL.glob("KHM*_final.json")):
        d = json.loads(path.read_text())
        task = rows(d, "TSK01")
        if not task or task[0].get("value") != "CLS" or not included(d):
            if d.get("adjudication", {}).pop("classification_reason_codes", None) is not None:
                path.write_text(json.dumps(d,ensure_ascii=False,indent=2)+"\n")
            continue
        classification += 1
        if d["study_id"] in PUBLISHED_CODES:  # prompt 106: published codes of the 220-study release are kept verbatim
            d["adjudication"]["classification_reason_codes"] = PUBLISHED_CODES[d["study_id"]]
            path.write_text(json.dumps(d,ensure_ascii=False,indent=2)+"\n")
            changed += 1
            continue
        out_rep, out_cred = by_unit(d,"OUT16"), by_unit(d,"OUT17")
        prd_rep, prd_align = by_unit(d,"PRD13"), by_unit(d,"PRD14")
        direct, proxy, post, available = (by_unit(d,k) for k in ("PRD08","PRD09","PRD10","PRD07"))
        entries = []
        for x in rows(d,"OUT18"):
            unit=x.get("unit_id")
            entries.append({"scope":"outcome","unit_id":unit,"overall_value":x.get("value"),
                            "reason_codes":codes_for_outcome(out_rep.get(unit),out_cred.get(unit)),
                            "rationale":x.get("rationale")})
        for x in rows(d,"PRD15"):
            unit=x.get("unit_id")
            entries.append({"scope":"predictor","unit_id":unit,"overall_value":x.get("value"),
                            "reason_codes":codes_for_predictor(prd_rep.get(unit),prd_align.get(unit),direct.get(unit),proxy.get(unit),post.get(unit),available.get(unit)),
                            "rationale":x.get("rationale")})
        threshold_nr = any(x.get("value") == "NR" for x in rows(d,"THR01"))
        if threshold_nr:
            entries.append({"scope":"classification_cutoff","unit_id":None,"overall_value":"NR",
                            "reason_codes":["cutoff_basis_not_reported"],
                            "rationale":"Classification cutoff selection was not reported."})
        d.setdefault("adjudication",{})["classification_reason_codes"] = entries
        path.write_text(json.dumps(d,ensure_ascii=False,indent=2)+"\n")
        changed += 1
    merged = [json.loads(p.read_text()) for p in sorted(FINAL.glob("KHM*_final.json"))]
    jsonl = ROOT / "data/protocol_v1_2/KNHANES_studies_v1.2.jsonl"
    jsonl.write_text("".join(json.dumps(d,ensure_ascii=False)+"\n" for d in merged))
    print(json.dumps({"status":"PASS","classification_records":classification,"updated":changed,
                      "merged_jsonl_records":len(merged)},indent=2))
    if classification != changed:  # prompt 106: count follows the included classification studies (222 under criterion A)
        raise SystemExit(1)


if __name__ == "__main__":
    main()
