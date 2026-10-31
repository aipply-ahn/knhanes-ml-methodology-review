#!/usr/bin/env python3
"""Freeze existing audit inputs and prepare a strictly blinded v1.4 H2 package."""
from __future__ import annotations

import hashlib
import json
from datetime import datetime, timezone
from pathlib import Path

from openpyxl import Workbook
from openpyxl.worksheet.datavalidation import DataValidation

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "data/protocol_v1_4"
P1_DIR = ROOT / "data/protocol_v1_2/P1"
V13 = ROOT / "data/protocol_v1_3/purpose_evidence_addendum.json"

VERSIONS = {
    "core_protocol_version": "1.2",
    "posthoc_protocol_version": "1.3",
    "human_verification_protocol_version": "1.4",
}

ORIENTATION = "HEALTH_FOCUSED,METHOD_FOCUSED,CO_PRIMARY,UNCLEAR"
YN = "Y,N,NR,NA,UNCLEAR"

FIELDS = [
    "study_id", "canonical_key", "title", "publication_year", "source_files",
    "source_package_complete", "missing_source_components",
    "primary_orientation", "orientation_confidence", "orientation_objective_evidence",
    "orientation_main_evaluation_or_result_evidence", "orientation_conclusion_evidence", "orientation_notes",
    "scientific_purposes", "scientific_purpose_evidence",
    "proposed_uses", "proposed_use_evidence",
    "analytic_outputs", "analytic_output_evidence",
    "method_contribution", "method_target_stages", "method_evaluation_design", "method_evidence",
    "association_estimate_linked", "survey_weights_linked_to_association",
    "design_uncertainty_linked_to_association", "association_support_evidence",
    "reviewer_id", "review_date", "review_complete", "overall_confidence", "reviewer_notes",
]


def sha256(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        for block in iter(lambda: f.read(1024 * 1024), b""):
            h.update(block)
    return h.hexdigest()


def load_json(path: Path):
    return json.loads(path.read_text(encoding="utf-8"))


def source_files_for(study_id: str) -> list[str]:
    p = P1_DIR / f"{study_id}_P1.json"
    if not p.exists():
        return []
    d = load_json(p)
    files = []
    for ev in d.get("evidence_registry", []):
        value = ev.get("source_file")
        if value and value not in files:
            files.append(value)
    return files


def blank_record(r: dict) -> dict:
    out = {k: None for k in FIELDS}
    out.update({
        "study_id": r["study_id"],
        "canonical_key": r["canonical_key"],
        "title": r["title"],
        "publication_year": r["publication_year"],
        "source_files": source_files_for(r["study_id"]),
    })
    return out


def choose_pilot(records: list[dict]) -> tuple[list[str], list[dict]]:
    """Stratify using hidden P1 features; expose only IDs in the reviewer packet."""
    chosen, audit = [], []
    def take(label, predicate):
        for r in records:
            if r["study_id"] not in chosen and predicate(r):
                chosen.append(r["study_id"]); audit.append({"study_id": r["study_id"], "hidden_selection_stratum": label}); return
        raise RuntimeError(f"No pilot candidate for {label}")
    take("health_multilabel_purpose", lambda r: r["primary_orientation"] == "HEALTH_FOCUSED" and len(r.get("purpose_records", [])) >= 2)
    take("health_no_proposed_use", lambda r: r["primary_orientation"] == "HEALTH_FOCUSED" and r.get("no_specific_use") is True)
    take("health_individual_application", lambda r: r["primary_orientation"] == "HEALTH_FOCUSED" and r.get("individual_application") is True)
    take("health_population_association", lambda r: any(x.get("purpose_code") == "POPULATION_ASSOCIATION" for x in r.get("purpose_records", [])))
    take("health_surveillance_policy", lambda r: any(x.get("use_code") == "POPULATION_SURVEILLANCE_OR_POLICY" for x in r.get("proposed_use_records", [])))
    take("health_causal_or_structure", lambda r: any(x.get("purpose_code") == "CAUSAL_EFFECT_OR_STRUCTURE" for x in r.get("purpose_records", [])))
    take("method_development", lambda r: r["primary_orientation"] == "METHOD_FOCUSED" and (r.get("method_research") or {}).get("method_research_type_figure4") == "METHOD_WORKFLOW_OR_TOOL_DEVELOPMENT_OR_IMPROVEMENT")
    take("method_comparison", lambda r: r["primary_orientation"] == "METHOD_FOCUSED" and (r.get("method_research") or {}).get("method_research_type_figure4") == "EXISTING_METHODS_COMPARISON_OR_EVALUATION")
    take("method_multistage", lambda r: r["primary_orientation"] == "METHOD_FOCUSED" and len((r.get("method_research") or {}).get("target_analysis_stages", [])) >= 3)
    take("orientation_boundary_candidate", lambda r: r["primary_orientation"] == "METHOD_FOCUSED" and (r.get("method_research") or {}).get("evaluation_mode") == "INSUFFICIENTLY_DESCRIBED")
    return chosen, audit


def make_workbook(records: list[dict], path: Path, title: str) -> None:
    wb = Workbook(); ws = wb.active; ws.title = "H2 blinded form"
    ws.append(FIELDS)
    for r in records:
        ws.append([json.dumps(r[k], ensure_ascii=False) if isinstance(r[k], list) else r[k] for k in FIELDS])
    ws.freeze_panes = "F2"; ws.auto_filter.ref = ws.dimensions
    widths = {"A": 14, "B": 28, "C": 62, "D": 12, "E": 52}
    for col, width in widths.items(): ws.column_dimensions[col].width = width
    for col in range(6, len(FIELDS)+1): ws.column_dimensions[ws.cell(1,col).column_letter].width = 24
    validations = {
        "source_package_complete": "Y,N",
        "primary_orientation": ORIENTATION,
        "orientation_confidence": "HIGH,MODERATE,LOW",
        "method_contribution": "METHOD_WORKFLOW_OR_TOOL_DEVELOPMENT_OR_IMPROVEMENT,EXISTING_METHODS_COMPARISON_OR_EVALUATION,UNCLEAR",
        "method_evaluation_design": "SIMULATION_AND_EMPIRICAL_APPLICATION,EMPIRICAL_COMPARATOR_EVALUATION,EXTERNAL_OR_TRANSPORTABILITY_EVALUATION,APPLICATION_OR_DEMONSTRATION,EVALUATION_DESIGN_INSUFFICIENTLY_REPORTED",
        "association_estimate_linked": YN,
        "survey_weights_linked_to_association": YN,
        "design_uncertainty_linked_to_association": YN,
        "review_complete": "Y,N",
        "overall_confidence": "HIGH,MODERATE,LOW",
    }
    for name, formula in validations.items():
        col = FIELDS.index(name)+1
        dv = DataValidation(type="list", formula1=f'"{formula}"', allow_blank=True)
        ws.add_data_validation(dv); dv.add(f"{ws.cell(1,col).column_letter}2:{ws.cell(1,col).column_letter}{len(records)+1}")
    meta = wb.create_sheet("README")
    meta.append([title]); meta.append([json.dumps(VERSIONS, ensure_ascii=False)])
    meta.append(["BLINDED: no P1 values, consensus values, manuscript totals, or figure labels are included."])
    meta.append(["Multi-select cells use JSON arrays. Evidence cells use JSON arrays of evidence objects defined in protocol v1.4."])
    meta.append(["Phase A orientation is locked first. Phase B modules are opened by a coordinator-side hidden P1/H2 union gate; the reviewer is not shown P1 values or gate reasons."])
    wb.save(path)


def main() -> None:
    for d in (OUT/"P1_locked", OUT/"H2_blinded", OUT/"HCON", OUT/"pilot"):
        d.mkdir(parents=True, exist_ok=True)
    source = load_json(V13); records = sorted(source["records"], key=lambda x: x["study_id"])
    assert len(records) == 220 and len({r["study_id"] for r in records}) == 220

    locked = {**VERSIONS, "schema": "purpose_evidence_P1_locked_v1.4_projection", "records": records}
    (OUT/"P1_locked/purpose_evidence_P1_locked.json").write_text(json.dumps(locked, ensure_ascii=False, indent=2)+"\n", encoding="utf-8")

    blank = [blank_record(r) for r in records]
    h2 = {**VERSIONS, "schema": "purpose_evidence_H2_blinded_v1.4", "review_status": "NOT_STARTED", "records": blank}
    (OUT/"H2_blinded/purpose_evidence_H2_blinded.json").write_text(json.dumps(h2, ensure_ascii=False, indent=2)+"\n", encoding="utf-8")
    make_workbook(blank, OUT/"H2_blinded/KNHANES_ML_H2_blinded_form_v1.4.xlsx", "Full 220-study blinded H2 form")

    gate_plan = []
    for r in records:
        p1_orientation = r.get("primary_orientation")
        p1_purposes = {x.get("purpose_code") for x in r.get("purpose_records", [])}
        gate_plan.append({
            "study_id": r["study_id"],
            "phase_a_status": "NOT_STARTED",
            "p1_health_candidate": p1_orientation in {"HEALTH_FOCUSED", "CO_PRIMARY"},
            "p1_method_candidate": p1_orientation in {"METHOD_FOCUSED", "CO_PRIMARY"},
            "p1_population_association_candidate": "POPULATION_ASSOCIATION" in p1_purposes,
            "h2_orientation": None,
            "h2_population_association_candidate": None,
            "open_health_module": None,
            "open_method_module": None,
            "open_population_association_module": None,
        })
    (OUT/"H2_blinded/phase_b_union_gate_coordinator_only.json").write_text(
        json.dumps({**VERSIONS, "schema": "phase_b_hidden_union_gate_v1.4", "records": gate_plan}, ensure_ascii=False, indent=2)+"\n",
        encoding="utf-8",
    )

    pilot_ids, pilot_audit = choose_pilot(records)
    pilot = [r for r in blank if r["study_id"] in pilot_ids]
    (OUT/"pilot/pilot_selection_audit_coordinator_only.json").write_text(json.dumps({**VERSIONS, "pilot_n": 10, "records": pilot_audit}, ensure_ascii=False, indent=2)+"\n", encoding="utf-8")
    (OUT/"pilot/pilot_H2_blinded_blank.json").write_text(json.dumps({**VERSIONS, "schema": "pilot_H2_blinded_v1.4", "review_status": "NOT_STARTED", "records": pilot}, ensure_ascii=False, indent=2)+"\n", encoding="utf-8")
    make_workbook(pilot, OUT/"pilot/KNHANES_ML_pilot_10_H2_blinded_v1.4.xlsx", "Ten-study blinded pilot form")
    (OUT/"HCON/README.md").write_text("# HCON\n\nIntentionally empty until genuine H2 review and adjudication are complete. Never populate from P1 alone.\n", encoding="utf-8")

    freeze_files = [
        ROOT/"KNHANES_ML_study_audit_protocol.md",
        V13,
        ROOT/"manuscript/bmc_main.tex",
        ROOT/"manuscript/bmc_main_ko.tex",
        ROOT/"manuscript/bmc_supplementary.tex",
        ROOT/"manuscript/bmc_supplementary_table_s5.xlsx",
        ROOT/"manuscript/bmc_supplementary_table_s7.xlsx",
    ] + sorted(P1_DIR.glob("*.json"))
    lines = ["sha256\tbytes\tpath"] + [f"{sha256(p)}\t{p.stat().st_size}\t{p.relative_to(ROOT)}" for p in freeze_files if p.exists()]
    (OUT/"freeze_manifest.sha256.tsv").write_text("\n".join(lines)+"\n", encoding="utf-8")
    metadata = {**VERSIONS, "created_utc": datetime.now(timezone.utc).isoformat(), "file_count": len(lines)-1, "p1_archive_role": "LOCKED_READ_ONLY_INPUT", "h2_status": "NOT_STARTED", "hcon_status": "NOT_CREATED"}
    (OUT/"freeze_manifest_metadata.json").write_text(json.dumps(metadata, ensure_ascii=False, indent=2)+"\n", encoding="utf-8")
    print(f"Prepared v1.4: 220 blank H2 records; pilot IDs={','.join(pilot_ids)}; frozen files={len(lines)-1}")

if __name__ == "__main__":
    main()
