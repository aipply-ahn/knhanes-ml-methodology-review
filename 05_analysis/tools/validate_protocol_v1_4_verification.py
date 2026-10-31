#!/usr/bin/env python3
"""Mechanical safeguards for the v1.4 independent-human workflow."""
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
BASE = ROOT / "data/protocol_v1_4"

def load(p): return json.loads(p.read_text(encoding="utf-8"))
def check(ok, label):
    if not ok: raise AssertionError(label)
    print(f"PASS {label}")

h2 = load(BASE/"H2_blinded/purpose_evidence_H2_blinded.json")
p1 = load(BASE/"P1_locked/purpose_evidence_P1_locked.json")
pilot = load(BASE/"pilot/pilot_H2_blinded_blank.json")
gate = load(BASE/"H2_blinded/phase_b_union_gate_coordinator_only.json")
hrs = h2["records"]
check(len(hrs)==220 and len({r["study_id"] for r in hrs})==220, "H2 contains 220 unique studies")
check(len(p1["records"])==220, "P1 projection contains 220 locked studies")
check(len(pilot["records"])==10 and len({r["study_id"] for r in pilot["records"]})==10, "pilot contains ten unique studies")
check(not (BASE/"HCON/purpose_evidence_HCON.json").exists(), "HCON is not fabricated before review")
check(all(h2[k]==v for k,v in {"core_protocol_version":"1.2","posthoc_protocol_version":"1.3","human_verification_protocol_version":"1.4"}.items()), "three protocol versions explicit")
identity={"study_id","canonical_key","title","publication_year","source_files"}
check(all(all(v is None for k,v in r.items() if k not in identity) for r in hrs), "H2 judgment cells are blank")
forbidden=("manuscript_total","figure_count","display_orientation_group","consensus","P1_value",
           "orientation_components","knhanes_position","purpose_priority","claim_strength",
           "importance_stability_component","independent_validation","calibration_evidence",
           "decision_threshold","surveillance_policy_applicable")
check(not any(any(x.lower() in k.lower() for x in forbidden) for r in hrs for k in r), "H2 contains no P1/aggregate/display fields")
required={"primary_orientation","scientific_purposes","proposed_uses","analytic_outputs",
          "method_contribution","method_target_stages","method_evaluation_design",
          "association_estimate_linked","survey_weights_linked_to_association",
          "design_uncertainty_linked_to_association"}
check(all(required <= set(r) for r in hrs), "H2 contains only the required manuscript-facing judgment modules")
check(len(gate["records"])==220 and all(r["open_health_module"] is None and r["open_method_module"] is None
      and r["open_population_association_module"] is None for r in gate["records"]),
      "hidden P1/H2 union gate is prepared but not opened before Phase A")
check("UNC\"" not in (BASE/"H2_blinded/purpose_evidence_H2_blinded.json").read_text(encoding="utf-8"), "active H2 has no legacy UNC token")
check((BASE/"freeze_manifest.sha256.tsv").exists(), "freeze checksum manifest exists")
print("v1.4 verification mechanics PASS")
