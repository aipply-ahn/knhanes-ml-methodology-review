#!/usr/bin/env python3
"""Prompt 106: one screening rule for every source (author decision 2026-09-28, 'complete unification').

Before: Korean Citation Index (KCI) records were screened by manual title/abstract status, other sources by the
T1/T2/T3 dictionary.  Now every record is screened by the dictionary replay (prisma source_audit.json):

* 20 KCI records with a dictionary hit that the manual KCI status had not advanced now enter eligibility
  assessment; their recorded manual finding becomes the eligibility reason (not KNHANES 3, no eligible ML 17).
* 4 records advanced by KCI manual review without any dictionary hit (all catalogued ML-adjacent) now stop at
  title/abstract screening.
* Exception, recorded: KHM229 (10.5720/kjcn.2014.19.5.468) also lacks a dictionary hit because the indexed abstract
  is truncated after 'Methods:'; it is an included criterion-A study (CHAID classification tree) and stays advanced.

Idempotent: runs once (a 'unified_screening' block marks completion)."""
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
FLOW = ROOT / "results/derived/final_selection_flow.json"
AUDIT = ROOT / "prompts/implementation_records/prisma_publication_hierarchy/source_replay/source_audit.json"
KEEP_ADVANCED = {"10.5720/kjcn.2014.19.5.468": "KHM229: included criterion-A study; indexed abstract truncated after 'Methods:'"}
NOT_KNHANES = {"kci:ART003311380": "US NHANES only (abstract)", "kci:ART003346494": "NHANES 2011-2014 (US); KNHANES use not shown",
               "kci:ART002908025": "Food-exchange-table classification; KNHANES raw data not analysed (full text checked)"}


def main():
    F = json.loads(FLOW.read_text())
    if "unified_screening" in F:
        print("already unified"); return
    A = json.loads(AUDIT.read_text())
    up = sorted(m["uid"] for m in A["screen_replay_mismatches"] if m["stored"] == "--" and m["replayed"] != "--")
    down_all = sorted(m["uid"] for m in A["screen_replay_mismatches"] if m["stored"] != "--" and m["replayed"] == "--")
    down = [u for u in down_all if u not in KEEP_ADVANCED]
    assert len(up) == 20 and len(down) == 4 and set(NOT_KNHANES) <= set(up), (len(up), len(down))
    V = json.loads((ROOT / "results/derived/verdicts.json").read_text())
    assert all(V[u]["verdict"] == "INCLUDE_ADJACENT" for u in down)
    assert all(u not in V for u in up)
    f, p = F["flow"], F["terminology_screen"]["partition"]
    before = {"terminology_exclusions": f["terminology_exclusions"], "no_dictionary_signal": p["no_dictionary_signal"],
              "kci_not_advanced": p["kci_not_advanced"], "records_assessed_against_eligibility": f["records_assessed_against_eligibility"],
              "ineligible_reports": f["ineligible_reports"], "ml_adjacent_reports_catalogued": f["ml_adjacent_reports_catalogued"],
              "reports_excluded_total": f["reports_excluded_total"]}
    r = f["report_exclusion_reasons"]
    kci_no_hit = p["kci_not_advanced"] - len(up)
    p["no_dictionary_signal"] += kci_no_hit + len(down)
    p["kci_not_advanced"] = 0
    f["terminology_exclusions"] = p["no_dictionary_signal"]
    f["records_assessed_against_eligibility"] += len(up) - len(down)
    r["not_knhanes"] += len(NOT_KNHANES)
    r["no_eligible_machine_learning"] += len(up) - len(NOT_KNHANES)
    r["ml_adjacent_catalogued_separately"] -= len(down)
    f["ml_adjacent_reports_catalogued"] = r["ml_adjacent_catalogued_separately"]
    f["ineligible_reports"] = sum(v for k, v in r.items() if k != "ml_adjacent_catalogued_separately")
    f["reports_excluded_total"] = f["ineligible_reports"] + f["ml_adjacent_reports_catalogued"]
    assert f["unique_records_screened"] - f["terminology_exclusions"] == f["records_assessed_against_eligibility"]
    assert f["reports_excluded_total"] + f["eligible_reports_entering_family_linkage"] == f["records_assessed_against_eligibility"]
    F["unified_screening"] = {"date": "2026-09-30", "rule": "T1/T2/T3 dictionary replay for every source, KCI included",
                              "before": before, "kci_records_now_assessed": up, "not_knhanes": NOT_KNHANES,
                              "kci_advanced_records_now_screened_out": down, "kept_advanced_exception": KEEP_ADVANCED,
                              "kci_no_hit_records_moved_to_no_term": kci_no_hit,
                              "provenance": "tools/unify_screening_rule.py; source_replay/source_audit.json; references/kci_refs.json"}
    FLOW.write_text(json.dumps(F, ensure_ascii=False, indent=2) + "\n")
    print(json.dumps({k: f[k] for k in ("terminology_exclusions", "records_assessed_against_eligibility", "ineligible_reports",
                                         "ml_adjacent_reports_catalogued", "reports_excluded_total", "eligible_reports_entering_family_linkage",
                                         "unique_full_report_studies_included")}), r)


if __name__ == "__main__":
    main()
