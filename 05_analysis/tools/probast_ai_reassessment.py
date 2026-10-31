#!/usr/bin/env python3
"""Initialize, validate, and aggregate the PROBAST+AI reassessment.

This module deliberately does not translate the legacy PROBAST ratings.  The 2025
tool changes the assessment unit, constructs, and judgement target; an automatic
crosswalk would create unsupported results.

Usage
-----
python tools/probast_ai_reassessment.py init
python tools/probast_ai_reassessment.py validate
python tools/probast_ai_reassessment.py aggregate
"""

from __future__ import annotations

import csv
import glob
import json
import os
import sys
from collections import Counter
from datetime import date

from common import DER, PROJ, REF, dump, load


OUT = os.path.join(PROJ, "data", "probast_ai_reassessment")
RECORDS = os.path.join(OUT, "records")
PREDICTIVE_TASKS = {"classification", "regression"}
ANSWERS = {"Y", "PY", "PN", "N", "NI", "NA"}
JUDGEMENTS = {"low", "high", "unclear"}

# Operational summaries keyed to Table 2 of Moons et al (BMJ 2025;388:e082505).
# These are phase-specific because the development and evaluation tools are distinct.
QUESTIONS = {
    "development": {
        "D1.1": "appropriate data source",
        "D1.2": "appropriate study design",
        "D1.3": "representative inclusion and exclusion",
        "D2.1": "predictors defined and assessed consistently",
        "D2.2": "predictor preprocessing applied consistently",
        "D2.3": "predictor assessment independent of outcome knowledge",
        "D2.4": "predictors available at intended use",
        "D3.1": "outcome defined and assessed appropriately",
        "D3.2": "outcome defined and assessed consistently",
        "D3.3": "outcome assessment independent of predictors",
        "D3.4": "appropriate predictor-to-outcome interval",
        "D4.1": "reasonable effective sample size",
        "D4.2": "appropriate handling of continuous and categorical predictors",
        "D4.3": "appropriate handling of missing or censored data",
        "D4.4": "recalibration after class-imbalance correction when needed",
        "D4.5": "methods address model overfitting",
    },
    "evaluation": {
        "D1.1": "appropriate data source",
        "D1.2": "appropriate study design",
        "D1.3": "representative inclusion and exclusion",
        "D2.1": "predictors defined and assessed consistently",
        "D2.2": "predictor preprocessing applied consistently",
        "D2.3": "predictor assessment independent of outcome knowledge",
        "D2.4": "predictors available at intended use",
        "D3.1": "outcome defined and assessed appropriately",
        "D3.2": "outcome defined and assessed consistently",
        "D3.3": "outcome assessment independent of predictors",
        "D3.4": "appropriate predictor-to-outcome interval",
        "D4.1": "evaluation not limited to apparent performance",
        "D4.2": "reasonable effective evaluation sample size",
        "D4.3": "appropriate handling of missing or censored data",
        "D4.4": "evaluation retains the natural outcome distribution",
        "D4.5": "data leakage avoided in split-sample evaluation",
        "D4.6": "all development steps repeated within resampling",
        "D4.7": "performance measures appropriate to intended use",
    },
}


def included_records():
    refs = {r["key"]: r for r in load(os.path.join(REF, "refs.json"))}
    ext = [load(p) for p in glob.glob(os.path.join(PROJ, "data", "extraction", "*.json"))]
    return refs, [e for e in ext if refs.get(e["key"], {}).get("verdict") == "INCLUDE"]


def phase_template(phase):
    return {
        "status": "pending",
        "questions": {q: "" for q in QUESTIONS[phase]},
        "domains": {d: "" for d in ("D1", "D2", "D3", "D4")},
        "overall_judgement": "",
        "applicability": {d: "" for d in ("D1", "D2", "D3", "overall")},
        "evidence": {},
        "judgement_rationale": "",
        "reviewer": "",
        "assessment_date": "",
    }


def init():
    os.makedirs(RECORDS, exist_ok=True)
    refs, records = included_records()
    rows = []
    for e in sorted(records, key=lambda x: x["key"]):
        key = e["key"]
        task = e.get("task") or "unclear"
        eligible = task in PREDICTIVE_TASKS
        source = e.get("source") or "unknown"
        role = e.get("knhanes_role") or "unclear"
        if not eligible:
            phase_plan = "not_applicable"
            status = "excluded_nonpredictive"
        elif role == "external_validation":
            phase_plan = "evaluation_only_candidate--confirm_from_report"
            status = "pending_scope_confirmation"
        else:
            phase_plan = "development_plus_evaluation--confirm_model_units"
            status = "ready_for_reassessment" if source == "full_text" else "limited_report_reassessment"
        rows.append({
            "study_id": key,
            "year": refs[key].get("year") or "",
            "task": task,
            "source": source,
            "knhanes_role": role,
            "probast_ai_eligible": "Y" if eligible else "N",
            "phase_plan": phase_plan,
            "task_timing": "pending_manual_classification" if eligible else "not_applicable",
            "assessment_status": status,
            "scope_note": "",
        })
        if eligible:
            path = os.path.join(RECORDS, key + ".json")
            if not os.path.exists(path):
                dump({
                    "schema_version": "probast_ai_2025_v1",
                    "study_id": key,
                    "source": source,
                    "task": task,
                    "task_timing": "",
                    "intended_use": "",
                    "target_population": "",
                    "outcome": "",
                    "scope_status": "pending",
                    "scope_rationale": "",
                    "models": [],
                    "assessment_blueprints": {
                        "development": phase_template("development"),
                        "evaluation": phase_template("evaluation"),
                    },
                    "legacy_probast_used_as_evidence_locator_only": os.path.exists(
                        os.path.join(PROJ, "data", "probast", key + ".json")
                    ),
                }, path)
            else:
                rec = load(path)
                # Availability can change when a report is acquired after the
                # reassessment registry was initialized.  Keep the registry and
                # uncompleted model record aligned with the current extraction.
                rec["source"] = source
                rec["task"] = task
                # Keep entered model assessments intact; refresh only unused blueprints.
                if rec.get("scope_status") == "pending" and not rec.get("models"):
                    rec["assessment_blueprints"] = {
                        "development": phase_template("development"),
                        "evaluation": phase_template("evaluation"),
                    }
                    with open(path, "w", encoding="utf-8") as f:
                        json.dump(rec, f, ensure_ascii=False, indent=1)
    with open(os.path.join(OUT, "scope_registry.tsv"), "w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=list(rows[0]), delimiter="\t")
        w.writeheader(); w.writerows(rows)
    with open(os.path.join(OUT, "question_bank.tsv"), "w", newline="", encoding="utf-8") as f:
        w = csv.writer(f, delimiter="\t")
        w.writerow(["phase", "question_id", "domain", "operational_summary", "source"])
        for phase, questions in QUESTIONS.items():
            for q, summary in questions.items():
                w.writerow([phase, q, q.split(".")[0], summary,
                            "Moons et al, BMJ 2025;388:e082505, Table 2"])
    print(f"  scope registry: {len(rows)} studies; {sum(r['probast_ai_eligible']=='Y' for r in rows)} eligible")


def validate_assessment(a, phase, where):
    errors = []
    questions = a.get("questions", {})
    expected = set(QUESTIONS[phase])
    if set(questions) != expected:
        errors.append(f"{where}: question IDs differ from the {phase} instrument")
    if a.get("status") == "complete":
        bad = {q: v for q, v in questions.items() if v not in ANSWERS}
        if bad:
            errors.append(f"{where}: invalid or blank answers {bad}")
        bad_domains = {d: a.get("domains", {}).get(d) for d in ("D1", "D2", "D3", "D4")
                       if a.get("domains", {}).get(d) not in JUDGEMENTS}
        if bad_domains:
            errors.append(f"{where}: invalid or blank domain judgements {bad_domains}")
        if a.get("overall_judgement") not in JUDGEMENTS:
            errors.append(f"{where}: invalid or blank overall judgement")
        bad_app = {d: a.get("applicability", {}).get(d) for d in ("D1", "D2", "D3", "overall")
                   if a.get("applicability", {}).get(d) not in JUDGEMENTS}
        if bad_app:
            errors.append(f"{where}: invalid or blank applicability judgements {bad_app}")
        if not a.get("judgement_rationale"):
            errors.append(f"{where}: judgement_rationale is required")
        if not a.get("reviewer") or not a.get("assessment_date"):
            errors.append(f"{where}: reviewer and assessment_date are required")
    return errors


def iter_units(record):
    for model in record.get("models", []):
        if model.get("development"):
            yield "development", model["development"], f"{record['study_id']}/{model.get('model_id','?')}/development"
        for ev in model.get("evaluations", []):
            yield "evaluation", ev, f"{record['study_id']}/{model.get('model_id','?')}/{ev.get('assessment_id','?')}"


def validate():
    errors = []
    complete = 0
    for path in sorted(glob.glob(os.path.join(RECORDS, "*.json"))):
        rec = load(path)
        if rec.get("scope_status") == "complete" and not rec.get("models"):
            errors.append(f"{rec.get('study_id', path)}: completed scope has no model units")
        for phase, unit, where in iter_units(rec):
            errors.extend(validate_assessment(unit, phase, where))
            complete += unit.get("status") == "complete"
    if errors:
        print("\n".join("ERROR " + e for e in errors))
        raise SystemExit(1)
    print(f"  validation passed; {complete} completed assessment units")


def aggregate():
    validate()
    with open(os.path.join(OUT, "scope_registry.tsv"), encoding="utf-8") as f:
        scope_rows = list(csv.DictReader(f, delimiter="\t"))
    synthesis_ids = {r["study_id"] for r in scope_rows if r["source"] == "full_text"}
    units = {"development": [], "evaluation": []}
    for path in sorted(glob.glob(os.path.join(RECORDS, "*.json"))):
        rec = load(path)
        if rec.get("study_id") not in synthesis_ids:
            continue
        for phase, unit, where in iter_units(rec):
            if unit.get("status") == "complete":
                units[phase].append((rec, unit, where))
    result = {
        "instrument": "PROBAST+AI (BMJ 2025;388:e082505)",
        "generated": date.today().isoformat(),
        "unit_of_analysis": "model development or model evaluation assessment",
        "development": summarize(units["development"]),
        "evaluation": summarize(units["evaluation"]),
        "legacy_probast_not_combined": True,
        "survey_design_appraisal_not_combined": True,
    }
    dump(result, os.path.join(DER, "probast_ai.json"))
    write_appendix(result)


def summarize(rows):
    out = {"n_units": len(rows), "overall": {}, "domains": {}, "questions": {}}
    out["overall"] = dict(Counter(a["overall_judgement"] for _, a, _ in rows))
    for d in ("D1", "D2", "D3", "D4"):
        out["domains"][d] = dict(Counter(a["domains"][d] for _, a, _ in rows))
    for q in sorted({q for _, a, _ in rows for q in a["questions"]}):
        out["questions"][q] = dict(Counter(a["questions"][q] for _, a, _ in rows))
    return out


def write_appendix(result):
    p = os.path.join(PROJ, "manuscript", "submission", "appendices", "appendix7_probast_ai.md")
    with open(os.path.join(OUT, "scope_registry.tsv"), encoding="utf-8") as f:
        scope = list(csv.DictReader(f, delimiter="\t"))
    scope = [r for r in scope if r["source"] == "full_text"]
    eligible = [r for r in scope if r["probast_ai_eligible"] == "Y"]
    source_counts = Counter(r["source"] for r in eligible)
    all_source_counts = Counter(r["source"] for r in scope)
    missing_reports = [load(p) for p in glob.glob(os.path.join(PROJ, "data", "extraction", "*.json"))
                       if load(p).get("source") != "full_text"
                       and load(p).get("key") in {r["key"] for r in load(os.path.join(REF, "refs.json"))
                                                  if r.get("verdict") == "INCLUDE"}]
    missing_sentence = ("No abstract-only or unretrieved report remained outside detailed synthesis after study-family linkage."
                        if not missing_reports else
                        ("One abstract-only report was excluded from detailed evidence synthesis before appraisal."
                         if len(missing_reports) == 1 else
                         f"{len(missing_reports)} abstract-only reports were excluded from detailed evidence synthesis before appraisal."))
    lines = [
        "# Additional file 7A. PROBAST+AI assessment",
        "",
        "PROBAST+AI was restricted to prediction-model studies. Development methodological quality and evaluation risk of bias were assessed as separate model-level units. KNHANES complex-survey items were not incorporated into these judgements. The reported results are an evidence-assisted primary review and require independent second review and consensus before submission.",
        "",
        "## Scope and assessment units",
        "",
        f"Of {len(scope)} included full-report studies, {len(eligible)} classification or regression studies were eligible for PROBAST+AI; {len(scope)-len(eligible)} nonprediction studies were excluded from the instrument and retained for task-specific narrative appraisal. {missing_sentence}",
        "",
        "Each report is first classified as diagnostic/current-state or prognostic/future-outcome modelling. Intended use, target population, outcome timing, model units, and evaluation datasets are then identified. A development study that reports apparent or internal performance contributes both a development-quality unit and at least one evaluation-risk-of-bias unit. A study evaluating an existing model contributes an evaluation unit only.",
        "",
        "Responses are Y, PY, PN, N, NI, or NA. Consistent with the official guidance, an N response did not automatically determine the domain judgement. This primary review used prespecified critical-failure rules plus retained study-specific evidence; other N, PN, or NI responses yielded an unclear judgement. Overall concern was high if any domain was high and otherwise unclear if any domain was unclear. These operational judgements require independent human verification and consensus. Applicability is judged separately for the first three domains. Concurrent measurement is not by itself an adverse judgement for a diagnostic/current-state model.",
        "",
    ]
    for phase, title in (("development", "Model development: methodological quality"),
                         ("evaluation", "Model evaluation: risk of bias")):
        x = result[phase]
        lines += [f"## {title}", "", f"Completed assessment units: {x['n_units']}.", ""]
        if not x["n_units"]:
            lines += ["Reassessment is pending; no legacy PROBAST judgement was carried forward.", ""]
            continue
        lines += ["| Domain | Low | High | Unclear |", "|---|---:|---:|---:|"]
        for d in ("D1", "D2", "D3", "D4"):
            c = x["domains"][d]
            lines.append(f"| {d} | {c.get('low',0)} | {c.get('high',0)} | {c.get('unclear',0)} |")
        lines.append("")
    lines += [
        "## Signalling-question structure",
        "",
        "The following concise labels are operational summaries. Assessment uses the official PROBAST+AI wording and accompanying guidance (Moons et al, BMJ 2025;388:e082505).",
        "",
        "| Part | ID | Operational summary |",
        "|---|---|---|",
    ]
    for phase, questions in QUESTIONS.items():
        for q, summary in questions.items():
            lines.append(f"| {phase} | {q} | {summary} |")
    survey_summary_path = os.path.join(PROJ, "results", "derived", "survey_design_appraisal.json")
    survey_summary = json.load(open(survey_summary_path, encoding="utf-8")) if os.path.exists(survey_summary_path) else None
    lines += [
        "",
        "# Additional file 7B. KNHANES complex-survey appraisal",
        "",
        "This appraisal is not part of PROBAST+AI and never changes a PROBAST+AI domain or overall judgement. It separately records: (1) whether a design feature is applicable to the stated estimand or intended interpretation; (2) whether the target population, estimand, weights, strata, clusters, pooled-cycle weights, and variance method are reported; and (3) whether applicable features are implemented or their omission is justified.",
        "",
        "Analytic roles are classified as sample-conditional prediction, population performance, population prevalence or association, population-level variable importance, causal/effect estimation, or mixed/unclear. Weighting in model fitting and weighting in performance evaluation are distinct items. Unweighted fitting is not automatically nonadherent for a clearly delimited sample-conditional prediction target.",
        "",
    ]
    if survey_summary:
        lines += [
            f"The evidence-assisted primary appraisal was completed for all {survey_summary['n_studies']} studies; independent duplicate review and consensus remain pending.",
            "", "| Applicability | Studies |", "|---|---:|",
        ]
        for label, count in survey_summary["applicability"].items():
            lines.append(f"| {label} | {count} |")
        lines += ["", "| Methodological adherence | Studies |", "|---|---:|"]
        for label, count in survey_summary["methodological_adherence"].items():
            lines.append(f"| {label} | {count} |")
        lines += ["", "| Design item | Studies reporting/using item |", "|---|---:|"]
        for label, count in survey_summary["design_reporting"].items():
            lines.append(f"| {label.replace('_',' ')} | {count} |")
        lines += ["", "The complete study-level appraisal, evidence excerpt, rationale, reviewer, and date are retained in `data/survey_design_appraisal/study_level_appraisal.tsv` and joined to the canonical JSON and Additional file 8.", ""]
    else:
        lines += ["Study-level appraisal results have not been generated.", ""]
    lines += [
        "# Additional file 7C. Reporting completeness",
        "",
        f"Reporting completeness uses a prespecified subset of 19 TRIPOD+AI-derived elements rather than the full checklist. The primary denominator is the {all_source_counts.get('full_text', 0)} full reports. Information unavailable because only an abstract was retrieved is not assessable, not not reported. Reporting completeness is not combined with PROBAST+AI or complex-survey methodological adherence and is not compared with them using a paired significance test.",
        "",
        "The complete scope registry, question bank, data dictionary, model-level records, and validation script accompany this appendix in the repository.",
        "",
    ]
    os.makedirs(os.path.dirname(p), exist_ok=True)
    with open(p, "w", encoding="utf-8") as f:
        f.write("\n".join(lines) + "\n")
    print("  saved " + os.path.relpath(p, PROJ))


if __name__ == "__main__":
    command = sys.argv[1] if len(sys.argv) > 1 else "validate"
    {"init": init, "validate": validate, "aggregate": aggregate}.get(command, lambda: sys.exit(
        "usage: probast_ai_reassessment.py [init|validate|aggregate]"))()
