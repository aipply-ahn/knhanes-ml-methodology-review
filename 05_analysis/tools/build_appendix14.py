"""Build Additional file 14: figure evidence and protocol heterogeneity audits."""
from __future__ import annotations

import csv
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "manuscript/submission/appendices/appendix14_extended_audits.md"


def cell(value: object) -> str:
    return " ".join(str(value or "").replace("|", "/").split())


CASES = [
    ("Diabetes/prediabetes", "choi2014screening", "FPG 100–125 mg/dL; diagnosed/undiagnosed diabetes excluded", "Adults ≥20; 2010 development/internal, 2011 temporal", "21.4% in 2010 analytic cohort", "Temporal", "AUROC", "Internal ANN 0.768; temporal SVM 0.731"),
    ("Diabetes/prediabetes", "ryu2020deep", "Undiagnosed diabetes; diagnosed diabetes excluded", "Adults ≥20; 2013–2015 development, 2016 temporal", "NR in retained extraction", "Temporal", "AUROC", "DLM 0.8011"),
    ("Diabetes/prediabetes", "choi2023comparisons", "FPG ≥126 mg/dL or HbA1c ≥6.5% without diagnosis/treatment", "Age 19–79; 2014–2018 development, 2019–2020 temporal", "4.3% development; 5.1% temporal", "Temporal", "AUROC", "LightGBM 0.819 (95% CI 0.805–0.833)"),
    ("Depression", "nam2021discovery", "Current physician-diagnosed depression; sensitivity analysis PHQ-9 ≥10", "Age 19–64; 2012–2016 pooled", "NR in retained extraction", "Internal hold-out", "AUROC", "0.86 diagnosis definition; 0.82 PHQ-9"),
    ("Depression", "kim2024machine", "PHQ-9 ≥10", "Adult current nonsmokers; 2014/2016/2018 pooled", "5.4%", "Internal hold-out", "AUROC", "SVM 0.900; LGBM accuracy 0.954 but sensitivity 0.339"),
    ("Depression", "lee2026development", "PHQ-9 ≥10 and ≥5 modelled separately", "Age ≥65; 2020+2022 development, 2024 temporal", "≥10: 4.3% development, 2.8% temporal", "Temporal", "AUROC/AUPRC", "CatBoost 0.853/0.267 for PHQ-9 ≥10"),
    ("Osteoporosis", "kim2013osteoporosis", "Any-site DXA T-score ≤−2.5", "Postmenopausal women; 2010", "34.8%", "Internal hold-out", "AUROC", "SVM 0.827"),
    ("Osteoporosis", "kwon2022osteoporosis", "DXA T-score <−2.5 vs ≥−1; osteopenia excluded", "Postmenopausal women 40–69; 2008–2011 pooled", "57.4% after spectrum restriction", "Internal hold-out/repeated CV", "AUROC", "AdaBoost 0.921"),
    ("Osteoporosis", "zhang2026online", "Normal vs any DXA abnormality; separate 3-class task", "Adults; 2009–2011 development, 2008 temporal", "35.4% any abnormality", "Temporal", "AUROC", "GradientBoost 0.845 internal; 0.876 temporal"),
]


def grade(row: dict) -> tuple[str, str]:
    txt = (row.get("caption", "") + " " + row.get("detected_metrics", "")).lower()
    nums = bool(row.get("numeric_labels_detected"))
    if any(x in txt for x in ("architecture", "flow", "importance", "loss", "formula", "t-sne", "path diagram")) and not any(x in txt for x in ("roc", "auc", "accuracy", "precision", "recall", "f1", "calibration")):
        return "D", "Context/diagnostic figure; not standalone predictive performance"
    if nums and any(x in txt for x in ("external", "test set", "validation")):
        return "A", "Exact printed value with an identifiable evaluation context"
    if nums:
        return "B", "Exact printed value; evaluation context must be read with the report"
    return "C", "Curve, bar, or rank without machine-recoverable printed values; no interpolation"


def main() -> None:
    with open(ROOT / "data/INTEGRATED_STUDY_AUDIT.tsv", encoding="utf-8-sig") as f:
        canonical_ids = {r["key"] for r in csv.DictReader(f, delimiter="\t")}
    studies = list(csv.DictReader(open(ROOT / "data/FIGURE_PERFORMANCE_AUDIT.tsv", encoding="utf-8-sig"), delimiter="\t"))
    figures = list(csv.DictReader(open(ROOT / "data/FIGURE_PERFORMANCE_CANDIDATES.tsv", encoding="utf-8-sig"), delimiter="\t"))
    studies = [r for r in studies if r["key"] in canonical_ids]
    figures = [r for r in figures if r["manuscript"] in canonical_ids]
    graded = []
    for r in figures:
        g, meaning = grade(r)
        graded.append((g, r, meaning))
    graded.sort(key=lambda x: (x[0], x[1]["manuscript"], x[1]["page"], x[1]["figure"]))

    lines = [
        "# Additional file 14. Extended task, figure-evidence, and protocol-heterogeneity audits",
        "",
        "## Figure-evidence grading rule",
        "",
        "The grade orders the *extractability and evaluation context of the figure evidence*, not the methodological quality of the study or its model. Grade A is an exact printed value with an identifiable external, temporal, validation, or test context; B is an exact printed value whose evaluation context must be interpreted with the report; C is a curve, bar, or rank without recoverable printed values, for which values were not interpolated; D is a training diagnostic, importance, architecture, formula, or other context figure and is not treated as standalone predictive performance. Candidate detection uses native document text and ChatGPT visual transcription/interpretation only; no OCR engine is used. Manuscript values were reconciled against the figure, report context, and accompanying text or table.",
        "",
        f"Coverage: {len(studies)} included studies; {sum(int(r['catalogued_figures_screened']) for r in studies)} numbered figures screened; {len(figures)} metric-keyword candidates in {len({r['manuscript'] for r in figures})} studies.",
        "",
        "## Same-disease protocol–performance case analysis",
        "",
        "These purposively selected cases illustrate nonexchangeability and are not a meta-analysis. Highest values are reported values in the stated evaluation setting, not pooled estimates or a cross-study league table.",
        "",
        "| Task family | Study | Outcome definition | Population and survey years | Positive prevalence | Evaluation | Metric | Reported value |",
        "|---|---|---|---|---:|---|---|---|",
    ]
    for row in CASES:
        lines.append("| " + " | ".join(cell(x) for x in row) + " |")

    lines += [
        "", "## Contextual methodological benchmark", "",
        "Values are descriptive because eligibility criteria, units, and appraisal instruments differ.", "",
        "| Indicator | KNHANES review | Comparator | Interpretation |",
        "|---|---|---|---|",
        "| Sample-size justification | 2/222 full reports (0.9%) | 17.8% in a general-ML review; 1/89 (1.1%) in oncology external validation | Clear weakness that also occurs elsewhere |",
        "| Formal calibration assessment | 24/206 classification studies (11.7%) | 12.5% in general ML; 57/89 (64%) in oncology external validation | Below both comparators, especially validation-focused work |",
        "| Transport/external-validation analytic function | 38/222 (17.1%) | No independent validation among 486 cardiovascular models; 31% of a 2023 oncology snapshot had any external validation | Broader content code than the 35/206 classification studies with eligible external/temporal validation |",
        "| Code reported available | 24/222 full reports (10.8%) | 4/89 (4.5%) in oncology external validation | Low in absolute terms |",
        "| Usable final model | 28/222 (12.6%) | 5.2% complete-model reporting in general ML | Better than the older benchmark, but rarely reusable |",
    ]

    lines += ["", "## Study-level figure coverage", "", "| Study | Task | Figures screened | Candidate figures | Candidate locations | Audit disposition |", "|---|---|---:|---:|---|---|"]
    for r in studies:
        lines.append(f"| {cell(r['key'])} | {cell(r['task'])} | {r['catalogued_figures_screened']} | {r['performance_figure_candidates']} | {cell(r['candidate_locations'])} | {cell(r['audit_status'])} |")

    lines += ["", "## Figure-level candidate ledger, ordered A to D", "", "| Grade | Study | Figure/page | Detected evidence | Printed values recovered by ChatGPT/native extraction | Adjudication meaning |", "|---|---|---|---|---|---|"]
    for g, r, meaning in graded:
        lines.append(f"| {g} | {cell(r['manuscript'])} | Fig {cell(r['figure'])}, p{cell(r['page'])} | {cell(r['detected_metrics'])} | {cell(r['numeric_labels_detected']) or 'None'} | {cell(meaning)} |")

    OUT.write_text("\n".join(lines) + "\n", encoding="utf-8")
    print(OUT.relative_to(ROOT))


if __name__ == "__main__":
    main()
