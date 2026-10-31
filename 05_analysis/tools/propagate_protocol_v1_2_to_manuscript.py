#!/usr/bin/env python3
"""Derive manuscript constants from adjudicated protocol-v1.2 final records."""
import json
from collections import Counter
from datetime import date
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "data/protocol_v1_2/final"
OUT = ROOT / "results/derived/protocol_v1_2_manuscript_numbers.json"
TEX = ROOT / "manuscript/protocol_v1_2_numbers.tex"  # prompt 106: the file the manuscripts \input

all_records = [json.loads(p.read_text()) for p in sorted(SRC.glob("KHM*_final.json"))]
if len(all_records) != 259 or any(  # prompt 106: 222 + 32 criterion A + 1 exclusion recheck; +3 review-loop inclusions 2026-10-24
    r.get("adjudication", {}).get("status") != "COMPLETE" for r in all_records):
    raise SystemExit("adjudicated final census is incomplete")

def included(r):
    return r.get("corpus_status", {}).get("include", r["protocol_items"]["ELG04"][0]["value"] == "Y")

records = [r for r in all_records if included(r)]
tasks = Counter(r["protocol_items"]["TSK01"][0]["value"] for r in records)
orientation = {
    r["study_id"]: r.get("adjudication", {}).get("study_category_and_dataset_use", {}).get("study_category")
    for r in records
}
health_n = sum(v == "HEALTH_ANALYSIS" for v in orientation.values())
method_n = sum(v == "METHOD_RESEARCH" for v in orientation.values())
health_class_n = sum(
    orientation.get(r["study_id"]) == "HEALTH_ANALYSIS"
    and r["protocol_items"]["TSK01"][0]["value"] == "CLS" for r in records
)
if (health_n, method_n, health_class_n) != (215, 39, 193):  # review 2026-10-24 (corrected groups + 3 inclusions); prompt 106: (214, 36, 192)
    raise SystemExit(f"study-orientation denominators are stale: {(health_n, method_n, health_class_n)}")
prediction = [r for r in records if r["protocol_items"]["TSK01"][0]["value"] in ("CLS", "CONT")]
visuals = [v for r in records for v in r["visual_objects"]]
containers = [v for v in visuals if v.get("inventory_level") == "CONTAINER"]
fig_types = {"FIGURE", "FLOW", "GRAPH_ABS"}
vscope = Counter((v.get("source_scope"), "figure" if v.get("object_type") in fig_types else
                  "table" if v.get("object_type") == "TABLE" else "other") for v in containers)
vstatus = Counter(v.get("interpretation_status") for v in visuals)
supp = [s for r in records for s in r["source_package"]["supplement_files"]]
numbers = {
 "reports_screened_final": len(all_records), "studies": len(records), "health": health_n,
 "method": method_n, "classification": tasks["CLS"], "all_classification": tasks["CLS"],
 "health_classification": health_class_n,
 "continuous": tasks["CONT"], "other": tasks["OTHER"], "prediction": tasks["CLS"] + tasks["CONT"],
 "protocol_items": len(records[0]["protocol_items"]),
 "development_units": sum(len(r["units"]["developments"]) for r in prediction),
 "evaluation_units": sum(len(r["units"]["evaluations"]) for r in prediction),
 "visual_objects": len(visuals), "visual_containers": len(containers),
 "visual_panels": sum(v.get("inventory_level") == "PANEL" for v in visuals),
 "main_figures": vscope[("MAIN", "figure")], "main_tables": vscope[("MAIN", "table")],
 "supplement_figures": vscope[("SUPPLEMENT", "figure")], "supplement_tables": vscope[("SUPPLEMENT", "table")],
 "figure_objects": sum(v.get("object_type") in fig_types or v.get("object_type") == "FIG_PANEL" for v in visuals),
 "image_interpreted": sum(v.get("vision_required") is True for v in visuals),
 "image_complete": vstatus["COMPLETE"], "image_source_unavailable": vstatus["UNREADABLE"],
 "image_manual_resolution": vstatus["UNCERTAIN"],
 "metric_sensitive_figures": sum(v.get("metric_sensitive") == "Y" for v in visuals),
 "supplement_files": len(supp), "supplement_studies": sum(bool(r["source_package"]["supplement_files"]) for r in records),
 "performance_metric_records": sum(len(r["performance_metrics"]) for r in records),
 "best_model_selections": sum(len(r["best_model_selections"]) for r in records),
 "evidence_records": sum(len(r["evidence_registry"]) for r in records),
 "retracted_corpus_history": sum(r.get("corpus_status", {}).get("exclude_from_valid_evidence") is True for r in records),
 "external_validation_only": sum(r["protocol_items"]["TSK06"][0]["value"] == "EXTVAL" for r in records),
}
payload = {"schema": "protocol_v1_2_manuscript_numbers", "date": date.today().isoformat(), "status": "PASS",
           "source": "data/protocol_v1_2/final/*.json", "inclusion_rule": "ELG04=Y after family linkage and coordinator decisions",
           "numbers": numbers, "legacy_crosscheck": "not equality-constrained after independent P2 adjudication"}
OUT.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n")
macros = {"ScreenedReportN":"reports_screened_final", "StudyN":"studies", "HealthN":"health", "MethodN":"method",
 "ClassN":"classification", "AllClassN":"all_classification", "HealthClassN":"health_classification",
 "ContinuousN":"continuous", "OtherN":"other", "PredictionN":"prediction", "ProtocolItemN":"protocol_items",
 "DevelopmentN":"development_units", "EvaluationN":"evaluation_units", "VisualN":"visual_objects",
 "VisualContainerN":"visual_containers", "VisualPanelN":"visual_panels", "MainFigureN":"main_figures",
 "MainTableN":"main_tables", "SuppFigureN":"supplement_figures", "SuppTableN":"supplement_tables",
 "FigureObjectN":"figure_objects", "ImageInterpretedN":"image_interpreted", "ImageCompleteN":"image_complete",
 "ImageUnavailableN":"image_source_unavailable", "ImageManualN":"image_manual_resolution",
 "MetricFigureN":"metric_sensitive_figures", "SupplementFileN":"supplement_files", "SupplementStudyN":"supplement_studies",
 "EvidenceRecordN":"evidence_records", "PerformanceRecordN":"performance_metric_records", "BestSelectionN":"best_model_selections",
 "RetractedN":"retracted_corpus_history", "ExternalOnlyN":"external_validation_only"}
lines = ["% Generated by tools/propagate_protocol_v1_2_to_manuscript.py; do not edit manually."]
for macro, key in macros.items(): lines.append(f"\\newcommand{{\\{macro}}}{{{numbers[key]:,}}}")
TEX.write_text("\n".join(lines) + "\n")
print(json.dumps(payload, ensure_ascii=False, indent=2))
