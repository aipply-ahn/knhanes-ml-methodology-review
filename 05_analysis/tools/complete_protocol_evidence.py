#!/usr/bin/env python3
"""Apply reviewed, explicit evidence repairs, preserving prior values and IDs."""
import copy
import json
import re
from collections import Counter
from pathlib import Path
from protocol_record_schema import normalise_analysis_records

ROOT = Path(__file__).resolve().parents[1]
DECISIONS = ROOT / "data/protocol_v1_3/evidence_repairs_20260924.json"
NOTES = ROOT / "prompts/implementation_records/evidence_completion_20260924"
RESOLUTIONS = ROOT / "data/protocol_v1_3/evidence_resolution_20260924.json"
RESOLUTION_NOTES = ROOT / "prompts/implementation_records/evidence_resolution_20260924"


def apply_repairs(doc, record, decisions):
    sid = doc["study_id"]
    closure = json.loads(RESOLUTIONS.read_text()) if RESOLUTIONS.exists() else {}
    registry = {e["evidence_id"]: e for e in doc["evidence_registry"]}
    for spec in decisions.get("source_spans", {}).get(sid, []) + closure.get("source_spans", {}).get(sid, []):
        eid = spec["evidence_id"]
        if eid in registry:
            continue
        source = (ROOT / spec["source_file"]).read_text()
        if "lines" in spec:
            lo, hi = spec["lines"]
            excerpt = "\n".join(source.splitlines()[lo-1:hi])
            before = "\n".join(source.splitlines()[:lo-1])
        else:
            start = source.index(spec["start"])
            end = source.index(spec["end"], start) + len(spec["end"])
            excerpt, before = source[start:end], source[:start]
        assert spec["contains"] in excerpt
        pages = re.findall(r"<!-- page (\d+) -->", before)
        anchor = {"evidence_id": eid, "source_file": spec["source_file"],
                  "source_type": spec.get("source_type", "MAIN_TEXT"),
                  "section": spec["section"], "object_label": spec.get("object_label"),
                  "pdf_page": int(pages[-1]) if pages else None,
                  "printed_page": None, "start_anchor": excerpt[:120],
                  "end_anchor": excerpt[-120:], "excerpt": excerpt,
                  "interpretation_status": "NATIVE", "source_lines": spec.get("lines")}
        doc["evidence_registry"].append(anchor)
        registry[eid] = anchor
    for field, atom, mapping in (
        ("analytic_output_records", "output_code", {"ASSOCIATION_ESTIMATE": decisions.get("association_output_anchors", {}).get(sid, [])}),
        ("proposed_use_records", "use_code", decisions.get("use_anchors", {}).get(sid, {})),
    ):
        for entry in record[field]:
            nums = mapping.get(entry[atom], [])
            if not nums:
                continue
            ids = [f"{sid}-EV{n:03d}" for n in nums]
            assert all(e in registry for e in ids)
            entry.setdefault("previous_evidence_ids", copy.deepcopy(entry.get("evidence_ids", [])))
            entry["evidence_ids"] = list(dict.fromkeys(entry.get("evidence_ids", []) + ids))
            entry["support_status"] = "EVIDENCE_LINKED"
            entry["evidence_repair_note"] = (
                "Linked to the reported result/table or author-stated proposed use. "
                "This linkage does not establish causal interpretation, implementation, or survey-design adequacy."
            )
    change = decisions["method_criteria"].get(sid)
    if change:
        assert all(e in registry for e in change["evidence_ids"])
        method = record["method_research"]
        method.setdefault("previous_primary_evaluation_criteria", copy.deepcopy(method["primary_evaluation_criteria"]))
        method["primary_evaluation_criteria"] = change["criteria"]
        method["primary_evaluation_criteria_evidence_ids"] = change["evidence_ids"]
        method["primary_evaluation_criteria_status"] = change.get("status", "CRITERIA_IDENTIFIED_PRIMARY_RANK_NOT_INFERRED")
        method["evidence_ids"] = list(dict.fromkeys(method["evidence_ids"] + change["evidence_ids"]))
    for change in decisions["record_evidence"]:
        if change["study_id"] != sid:
            continue
        key = change["field"]
        entry = record[key][change["index"]]
        assert entry[change["code_field"]] == change["code"]
        for anchor in change.get("new_anchors", []):
            if anchor["evidence_id"] not in registry:
                doc["evidence_registry"].append(anchor)
                registry[anchor["evidence_id"]] = anchor
        assert all(e in registry for e in change["evidence_ids"])
        entry.setdefault("previous_evidence_ids", copy.deepcopy(entry.get("evidence_ids", [])))
        entry["evidence_ids"] = list(dict.fromkeys(entry.get("evidence_ids", []) + change["evidence_ids"]))
        entry["support_status"] = "EVIDENCE_LINKED"
        entry["evidence_repair_note"] = change["note"]
    caution = decisions.get("record_cautions", {}).get(sid)
    if caution:
        for entry in record["analytic_output_records"]:
            if entry["output_code"] == "ASSOCIATION_ESTIMATE":
                entry["review_status"] = "CLASSIFICATION_REQUIRES_REVIEW"
                entry["other_text"] = caution
                entry["support_status"] = "UNCONFIRMED"
                if sid == "KHM140":
                    entry["candidate_anchors"] = ["KHM140-EV025", "KHM140-EV038"]
                    entry["evidence_ids"] = entry.get("previous_evidence_ids", [])
                    entry["evidence_repair_note"] = caution
    analysis = decisions["statistical_analyses"].get(sid)
    if analysis:
        analysis = copy.deepcopy(analysis)
        previous = next((a for a in doc.get('adjudication', {}).get('purpose_evidence_v1_3', {}).get('statistical_analysis_records', [])
                         if a.get('statistical_analysis_id') == analysis['statistical_analysis_id']), {})
        for key in ('field_revisions', 'migration_previous_schema_note', 'migration_previous_values'):
            if key in previous:
                analysis[key] = copy.deepcopy(previous[key])
        assert all(e in registry for e in analysis["evidence_ids"])
        record["statistical_analysis_records"] = [analysis]
        record["association_audit"]["statistical_analysis_id"] = analysis["statistical_analysis_id"]
        record["association_audit"]["analysis_linkage_note"] = analysis["note"]
        record["association_audit"]["evidence_ids"] = list(dict.fromkeys(
            record["association_audit"].get("evidence_ids", []) + analysis["evidence_ids"]))
    return normalise_analysis_records(apply_resolutions(doc, record, closure))


def apply_resolutions(doc, record, closure):
    """Resolve reviewed classifications; retain every superseded record verbatim."""
    sid = doc["study_id"]
    actions = [x for x in closure.get("resolutions", []) + closure.get("additional_corrections", []) if x["study_id"] == sid]
    prior = doc.get("adjudication", {}).get("purpose_evidence_v1_3", {})
    if actions:
        record.setdefault("classification_revisions", copy.deepcopy(prior.get("classification_revisions", [])))
    anchors = {e["evidence_id"] for e in doc["evidence_registry"]}
    for action in actions:
        kind = action["kind"]
        field, atom = ("analytic_output_records", "output_code") if kind == "output" else ("proposed_use_records", "use_code")
        rid = f"{sid}-REV-{kind.upper()}-{action['old_code']}"
        existing = next((x for x in record["classification_revisions"] if x["revision_id"] == rid), None)
        entry = next((x for x in record[field] if x[atom] == action["old_code"]), None)
        if existing is None:
            assert entry is not None, (sid, action["old_code"])
            existing = {"revision_id": rid, "field": field, "previous_record": copy.deepcopy(entry),
                        "previous_index": record[field].index(entry), "old_code": action["old_code"],
                        "new_code": action["new_code"], "reason": action["reason"],
                        "evidence_ids": action["evidence_ids"],
                        "decision": "RETAINED_WITH_EVIDENCE" if action["new_code"] == action["old_code"] else
                                    "WITHDRAWN" if action["new_code"] is None else "RECLASSIFIED"}
            record["classification_revisions"].append(existing)
        assert all(e in anchors for e in action["evidence_ids"])
        if entry is not None:
            record[field].remove(entry)
        if action["new_code"] is not None:
            replacement = next((x for x in record[field] if x[atom] == action["new_code"]), None)
            if replacement is None:
                replacement = copy.deepcopy(existing["previous_record"])
                replacement[atom] = action["new_code"]
                record[field].insert(min(existing["previous_index"], len(record[field])), replacement)
            replacement["evidence_ids"] = action["evidence_ids"]
            replacement["support_status"] = "EVIDENCE_LINKED"
            replacement["review_status"] = "COMPLETE"
            replacement["evidence_repair_note"] = action["reason"]
            replacement["other_text"] = action.get("other_text", action["reason"])
            if kind == "use":
                replacement["review_complete"] = True
                replacement["claim_strength"] = action.get("claim_strength", "POSSIBLE_FUTURE_USE")
        if kind == "output" and action["old_code"] == "ASSOCIATION_ESTIMATE":
            audit = record["association_audit"]
            if action["new_code"] != "ASSOCIATION_ESTIMATE":
                audit["any_association_estimate_reported"] = "N"
                audit["association_was_substantive_output"] = "N"
                audit["population_association_was_survey_aware"] = "N"
                audit["linkage_status"] = "REJECTED_FALSE_POSITIVE"
                audit["evidence_ids"] = action["evidence_ids"]
            else:
                audit["evidence_ids"] = action["evidence_ids"]
                audit["linkage_status"] = "DIRECTLY_LINKED"
            audit["resolution_note"] = action["reason"]
    use_actions = [x for x in actions if x["kind"] == "use"]
    if use_actions:
        record["no_specific_use"] = not record["proposed_use_records"]
        record["use_review_complete"] = True
        record["use_review_evidence_ids"] = list(dict.fromkeys(e for a in use_actions for e in a["evidence_ids"]))
        # Remove/rebuild stale use claims, without inventing model-level support.
        use_types = {"INDIVIDUAL_APPLICATION", "POPULATION_SURVEILLANCE_OR_POLICY"}
        old_claims = [c for c in record["claim_evidence_records"] if c["claim_type"] in use_types]
        record.setdefault("previous_use_claim_records", copy.deepcopy(prior.get("previous_use_claim_records", old_claims)))
        record["claim_evidence_records"] = [c for c in record["claim_evidence_records"] if c["claim_type"] not in use_types]
        for claim_type, codes in (("INDIVIDUAL_APPLICATION", {"SCREENING", "DIAGNOSTIC_SUPPORT", "RISK_GROUP_IDENTIFICATION", "PERSONALISED_MANAGEMENT"}),
                                  ("POPULATION_SURVEILLANCE_OR_POLICY", {"POPULATION_SURVEILLANCE_OR_POLICY"})):
            uses = [u for u in record["proposed_use_records"] if u["use_code"] in codes]
            if not uses:
                continue
            record["claim_evidence_records"].append({
                "claim_id": f"{sid}-C-USE-{claim_type}", "claim_type": claim_type,
                "claim_strength": "AUTHOR_STATED", "model_id": None, "outcome_id": None,
                "evaluation_id": None, "statistical_analysis_id": None,
                "support_elements": [], "support_status": "STUDY_LEVEL_ONLY",
                "evidence_ids": list(dict.fromkeys(e for u in uses for e in u["evidence_ids"])),
                "note": "Author-stated use only; predictive performance is not a tested-use evaluation."})
    analysis = closure.get("statistical_analysis", {})
    if analysis.get("study_id") == sid:
        record["statistical_analysis_records"] = [analysis]
        record["association_audit"]["statistical_analysis_id"] = analysis["statistical_analysis_id"]
        record["association_audit"]["analysis_linkage_note"] = analysis["note"]
        record["association_audit"]["evidence_ids"] = analysis["evidence_ids"]
    return record


def project_public_classification(category, record):
    """Project authoritative revised records into legacy figure/claim consumers."""
    if record.get("classification_revisions"):
        category["proposed_use"] = [u["use_code"] for u in record["proposed_use_records"]] or ["NO_SPECIFIC_USE"]
        aliases = {"ASSOCIATION_ESTIMATE": "POPULATION_ASSOCIATION_ESTIMATE", "REDUCED_VARIABLE_SET": "REDUCED_PREDICTOR_SET",
                   "INTERFACE_OR_TOOL": "IMPLEMENTED_TOOL"}
        category["analytic_outputs"] = list(dict.fromkeys(aliases.get(r["output_code"], r["output_code"]) for r in record["analytic_output_records"]))
    return category


def main():
    decisions = json.loads(DECISIONS.read_text())
    path = ROOT / "data/protocol_v1_3/purpose_evidence_addendum.json"
    addendum = json.loads(path.read_text())
    changes = []
    NOTES.mkdir(parents=True, exist_ok=True)
    RESOLUTION_NOTES.mkdir(parents=True, exist_ok=True)
    purpose_path = ROOT / "results/derived/study_purpose_audit.json"
    purposes = json.loads(purpose_path.read_text())
    categories = {r["study_id"]: r for r in purposes["records"]}
    for i, record in enumerate(addendum["records"]):
        sid = record["study_id"]
        target = ROOT / f"data/protocol_v1_2/final/{sid}_final.json"
        doc = json.loads(target.read_text())
        original = copy.deepcopy(doc["adjudication"]["purpose_evidence_v1_3"])
        assert original == record, f"Existing canonical/addendum disagreement: {sid}"
        revised = apply_repairs(doc, copy.deepcopy(record), decisions)
        if revised == original:
            continue
        resolution_backup = RESOLUTION_NOTES / f"{sid}_before.json"
        if not resolution_backup.exists():
            resolution_backup.write_text(json.dumps(doc, ensure_ascii=False, indent=2) + "\n")
        backup = NOTES / f"{sid}_before.json"
        if not backup.exists():
            backup.write_text(json.dumps(original, ensure_ascii=False, indent=2) + "\n")
        doc["adjudication"]["purpose_evidence_v1_3"] = revised
        category = project_public_classification(doc["adjudication"]["study_category_and_dataset_use"], revised)
        categories[sid].update(category)
        target.write_text(json.dumps(doc, ensure_ascii=False, indent=2) + "\n")
        addendum["records"][i] = revised
        changes.append(sid)
    for key, records in (("association_audit", addendum["records"]),
                         ("health_focused_association_audit", [r for r in addendum["records"] if r["primary_orientation"] == "HEALTH_FOCUSED"])):
        addendum["summary"][key] = {k: dict(Counter(r["association_audit"][k] for r in records)) for k in
            ("any_association_estimate_reported", "association_was_substantive_output", "population_association_was_survey_aware")}
    for key in ("proposed_use", "analytic_outputs"):
        purposes["summary"][key] = dict(Counter(v for r in purposes["records"] if r["study_category"] == "HEALTH_ANALYSIS" for v in r[key]))
    path.write_text(json.dumps(addendum, ensure_ascii=False, indent=2) + "\n")
    purpose_path.write_text(json.dumps(purposes, ensure_ascii=False, indent=2) + "\n")
    print(json.dumps({"updated_studies": changes, "count": len(changes)}, ensure_ascii=False))


if __name__ == "__main__":
    main()
