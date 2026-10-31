#!/usr/bin/env python3
"""Build Additional files 2--7 in the same order as the manuscript Results."""

from __future__ import annotations

import csv
import json
import math
import re
from collections import Counter
from pathlib import Path

import matplotlib.pyplot as plt
import numpy as np

ROOT = Path(__file__).resolve().parents[1]
DATA = ROOT / "data"
DER = ROOT / "results" / "derived"
APP = ROOT / "manuscript" / "submission" / "appendices"
FIG = "figures/submission"


def load_json(path: Path):
    return json.loads(path.read_text(encoding="utf-8"))


def read_tsv(path: Path):
    with path.open(encoding="utf-8-sig") as handle:
        return list(csv.DictReader(handle, delimiter="\t"))


def clean(value, limit=500):
    value = re.sub(r"\s+", " ", str("" if value is None else value)).strip().replace("|", "/")
    if re.search(r"[\ue000-\uf8ff]", value):
        value = re.sub(r"min[\ue000-\uf8ff′≠\s]+\(1\)", "[source formula not text-decodable] (1)", value)
        value = re.sub(r"[\ue000-\uf8ff]+", "[unresolved source glyph]", value)
    return value if len(value) <= limit else value[: limit - 1].rstrip() + "…"


def table(headers, rows, limit=500):
    lines = ["| " + " | ".join(headers) + " |", "|" + "|".join("---" for _ in headers) + "|"]
    lines += ["| " + " | ".join(clean(x, limit) for x in row) + " |" for row in rows]
    return "\n".join(lines)


def freq(counter, denominator=None):
    denominator = denominator or sum(counter.values())
    return table(["Category", "n", "%"], [
        (key, value, f"{100 * value / denominator:.1f}") for key, value in counter.items()
    ])


def mapping_text(value):
    return "; ".join(f"{k}: {v}" for k, v in value.items())


def display_key(value):
    """Keep the canonical key recognisable while adding one safe line-break point."""
    return re.sub(r"(?<=\d{4})(?=[A-Za-z])", "-", str(value), count=1)


def figure(number, path, caption):
    return f"""\\Needspace{{0.82\\textheight}}

## Figure {number}. {caption}

\\begin{{center}}
\\includegraphics[width=.96\\linewidth,height=.78\\textheight,keepaspectratio]{{{path}}}
\\end{{center}}

**Review status:** Evidence-assisted primary-review output; independent second review and consensus remain pending where judgement-based coding is shown.
"""


def figure_panel(number, path, trim, caption):
    """Expose one or more panels from a vector source without rasterisation."""
    return f"""\\Needspace{{0.82\\textheight}}

## Figure {number}. {caption}

\\begin{{center}}
\\includegraphics[width=.93\\linewidth,height=.74\\textheight,keepaspectratio,clip,trim={{{trim}}}]{{{path}}}
\\end{{center}}

**Review status:** Evidence-assisted primary-review output; independent second review and consensus remain pending where judgement-based coding is shown.
"""


def save_barh(counter, order, title, filename):
    labels = order
    values = [counter.get(x, 0) for x in labels]
    fig, ax = plt.subplots(figsize=(8.6, 4.8))
    y = np.arange(len(labels))
    colors = ['#D55E00' if 'recoverable' in x.lower() else '#0072B2' for x in labels]
    ax.barh(y, values, color=colors)
    ax.set_yticks(y); ax.set_yticklabels(labels, fontsize=9); ax.invert_yaxis()
    ax.set_xlabel('Studies (n)'); ax.set_title(title, loc='left', weight='bold')
    ax.grid(axis='x', color='#E5E7EB', linewidth=.7); ax.set_axisbelow(True)
    for yi, value in zip(y, values): ax.text(value + max(values) * .012, yi, str(value), va='center', fontsize=9)
    ax.spines[['top','right']].set_visible(False)
    fig.tight_layout(); fig.savefig(ROOT / 'figures/submission' / filename, bbox_inches='tight')
    plt.close(fig)


def make_temporal_detail_figures(landscape):
    periods = landscape['period_order']
    short = ['≤2019', '2020–22', '2023–24', '2025–26']
    specs = [
        ('supp_s7_algorithms.pdf', ['Logistic regression','Random forest','XGBoost','SVM','LightGBM','DNN'],
         'model_counts', 'Algorithm use by publication period (%)', 'All studies in period'),
        ('supp_s7_importance.pdf', ['SHAP','Model-native importance','Permutation importance','PDP/ALE/ICE','LIME'],
         'importance_method_counts', 'Variable-importance methods by publication period (%)', 'Classification studies in period')]
    for filename, labels, field, title, denominator_label in specs:
        mat=[]
        for label in labels:
            row=[]
            for period in periods:
                p=landscape['periods'][period]
                den=p['predictive_n'] if field == 'importance_method_counts' else p['n']
                row.append(100*p[field].get(label,0)/den)
            mat.append(row)
        mat=np.asarray(mat)
        fig, ax=plt.subplots(figsize=(8.6,4.8))
        im=ax.imshow(mat, aspect='auto', cmap='Blues', vmin=0, vmax=max(75, float(mat.max())))
        ax.set_xticks(range(4)); ax.set_xticklabels(short); ax.set_yticks(range(len(labels))); ax.set_yticklabels(labels)
        for i in range(mat.shape[0]):
            for j in range(mat.shape[1]):
                ax.text(j,i,f'{mat[i,j]:.0f}',ha='center',va='center',fontsize=9,color='white' if mat[i,j]>45 else '#111827')
        ax.set_title(title,loc='left',weight='bold'); ax.set_xlabel(denominator_label)
        fig.colorbar(im,ax=ax,fraction=.035,pad=.025,label='%')
        fig.tight_layout(); fig.savefig(ROOT/'figures/submission'/filename,bbox_inches='tight'); plt.close(fig)


def body_after_title(path: Path):
    text = path.read_text(encoding="utf-8")
    text = re.sub(r"^# .*?\n+", "", text, count=1)
    return re.sub(r"^# ", "### ", text, flags=re.M)


def build_af2(refs, analysis):
    linked = []
    for r in refs:
        if r.get("verdict") not in {"DUPLICATE", "LINKED_COMPANION"}:
            continue
        parent = r.get("companion_of") or r.get("duplicate_of")
        if not parent:
            match = re.search(r"counted at ([A-Za-z0-9_-]+)", r.get("verdict_reason") or "")
            parent = match.group(1) if match else "Not retained"
        linked.append((r["key"], r.get("year"), r.get("title"), parent,
                       "Author-adjudicated companion" if r["verdict"] == "LINKED_COMPANION" else "Linked duplicate/additional report",
                       r.get("verdict_reason"), r.get("doi")))

    adjacent = [r for r in refs if r.get("verdict") == "INCLUDE_ADJACENT"]
    adjacent_rows = [(i, r.get("year"), r.get("title"), "; ".join(r.get("ml_methods_reported") or []),
                      r.get("verdict_reason"), r.get("doi") or "NR") for i, r in enumerate(adjacent, 1)]
    ref_by_key = {r["key"]: r for r in refs}
    linkage_rows = []
    for key, year, title, parent, kind, basis, doi in linked:
        if key == "amarbayasgalan2021reconstruction":
            evidence = ("Shared Amarbayasgalan/Ryu investigators, KNHANES source, and reconstruction-error "
                        "autoencoder-to-neural-network method lineage; the 2021 diabetes target differs from the "
                        "2019 coronary-heart-disease target. Exact shared cohort/protocol could not be established "
                        "because the 2021 full text was unavailable.")
            decision = ("Author-directed publication-family consolidation; not asserted to be a duplicate outcome "
                        "analysis. Retained as a transparent linkage caveat and not counted separately.")
        else:
            parent_ref = ref_by_key.get(parent, {})
            child_authors = {x.split()[0].lower() for x in (ref_by_key.get(key, {}).get("author_list") or []) if x}
            parent_authors = {x.split()[0].lower() for x in (parent_ref.get("author_list") or []) if x}
            shared = ", ".join(sorted(child_authors & parent_authors)) or "not machine-resolved"
            same_title = clean(title).lower().rstrip(".") == clean(parent_ref.get("title")).lower().rstrip(".")
            evidence = (f"Bibliographic report-family linkage ({basis}); title relation="
                        f"{'exact' if same_title else 'version/related-title'}; shared author tokens={shared}; "
                        f"representative DOI={parent_ref.get('doi') or 'NR'}. The retained report supplies the "
                        "full study-level extraction.")
            decision = "Linked duplicate/additional report; the representative full report was counted once."
        linkage_rows.append((display_key(key), year, title, display_key(parent), kind, evidence, decision, doi or "NR"))
    extraction_items = [
        (1,"Clinical problem/outcome"),(2,"Primary analytic task"),(3,"Role of ML"),(4,"KNHANES cycles/years"),
        (5,"KNHANES data-source role"),(6,"Other datasets"),(7,"Sample eligibility/filtering"),(8,"Final analytic n"),
        (9,"Candidate/input variables"),(10,"Variable-selection procedure"),(11,"Missing-data handling"),
        (12,"Preprocessing and imbalance handling"),(13,"Survey-design handling"),(14,"Models evaluated"),
        (15,"Reported best model"),(16,"Best-model selection criterion/value/context"),(17,"Hyperparameter tuning"),
        (18,"Validation/evaluation design"),(19,"Performance metrics"),(20,"Interpretability/importance method"),
        (21,"Important-variable results and selection rule"),(22,"Downstream statistical analysis/carryover"),
        (23,"Principal findings"),(24,"Limitations"),(25,"Code/data availability")]
    kn_terms = ["KNHANES", "Korea National Health and Nutrition Examination Survey", "Korean National Health and Nutrition Examination Survey"]
    ml_terms = ["machine learning", "deep learning", "artificial intelligence", "neural network", "random forest", "gradient boosting", "XGBoost", "LightGBM", "CatBoost", "support vector machine", "decision tree", "k-nearest neighbor", "naive Bayes", "ensemble learning", "explainable", "SHAP", "multilayer perceptron", "convolutional neural network", "LSTM", "autoencoder", "clustering", "k-means", "LASSO", "elastic net", "prediction model", "risk prediction", "large language model", "AutoML", "TabPFN"]
    epmc_a = "(" + " OR ".join(f'TITLE_ABS:\"{x}\"' for x in kn_terms) + ")"
    epmc_b = "(" + " OR ".join(f'\"{x}\"' for x in kn_terms) + ") AND (" + " OR ".join(f'\"{x}\"' for x in ml_terms) + ")"
    pubmed = 'KNHANES[tiab] OR "Korea National Health and Nutrition Examination Survey"[tiab] OR "Korean National Health and Nutrition Examination Survey"[tiab] OR "Korea National Health and Nutrition Examination Survey"[mh]'
    kci_datasets = "국민건강영양조사 / KNHANES / 국민건강 영양조사 / National Health and Nutrition Examination Survey / 국건영 / 국민건강·영양조사 / KNHNAES"
    kci_methods = "머신러닝 / 기계학습 / 기계 학습 / machine learning / 딥러닝 / deep learning / 데이터마이닝 / data mining / 신경망 / neural network / 인공지능 / artificial intelligence / 랜덤 포레스트 / random forest / XGBoost / 부스팅 / 서포트 벡터 / support vector / 의사결정나무 / 의사결정트리 / decision tree / 군집 / clustering / 잠재계층 / 잠재프로파일 / LASSO / elastic net / AutoML / SHAP / 머신 러닝 / 딥 러닝 / 인공 신경망 / SVM / LightGBM / AdaBoost / CatBoost / k-means / KNN / CHAID / CART / 다층 퍼셉트론 / 연관규칙 / association rule"
    text = f"""# Additional file 2. Supplementary Review Methods and Coding Framework

This file follows the manuscript Methods and contains operational rules rather than completed appraisal results.

## Table S2.1. Review protocol, amendments, and screening flow

The review was reported against PRISMA 2020. The operational protocol, subsequent scope clarifications, and all denominator-affecting decisions are retained as dated amendments; none was used to select studies on the basis of their results.

{table(['Stage','n','Disposition'], [('Records from five sources',18517,'Merged'),('After database-level deduplication',11077,'Terminology screening'),('Reports assessed',1499,'Content adjudication'),('Ineligible',1119,'Excluded'),('ML-adjacent',134,'Catalogued, not included'),('Eligible reports',246,'Entered study-family linkage'),('Additional/companion reports',24,'Linked, not counted separately'),('Unique included studies',222,'Synthesis cohort')])}

## Table S2.2. Complete source-specific search strategies and yields (five sources; 18,517 records)

{table(['Source','Search date','Full operational search','Records entering merged set'], [
('Europe PMC','2026-09-03',f'Layer A: {epmc_a}; Layer B: {epmc_b}','6,046'),
('OpenAlex','2026-09-05','title_and_abstract.search phrase queries: "KNHANES"; "Korea National Health and Nutrition Examination Survey" (the Korean/Korea variant produced the same stemmed set)','10,000'),
('PubMed','2026-09-03',pubmed,'52 unique additional'),
('KDCA publication list','2026-09-03','Complete author-registered publication list; all entries','2,079'),
('Korean Citation Index','2026-09-05',f'KEYALL(dataset) AND KEYALL(method), 7 × 43 = 301 queries. Dataset terms: {kci_datasets}. Method terms: {kci_methods}.','340')], limit=5000)}

## Table S2.3. Eligibility and exclusion criteria

{table(['Decision','Operational criterion'], [
('Include','KNHANES analysed and an eligible ML/AI method actually applied; primary, linked, or external-validation use allowed'),
('ML-adjacent','KNHANES analysed but only an adjacent method was central, without an additional eligible ML component'),
('Exclude','KNHANES only cited; no eligible ML; review/commentary/protocol; isolated abstract without recoverable methods/results; or unrelated dataset'),
('Report linkage','Different reports were linked only after eligibility; database duplicate removal and study-family linkage were distinct operations')])}

## Table S2.4. Boundary rules for ML-adjacent studies and complete report catalogue (n=134 reports)

{table(['Tier','Purpose','Term families','Eligibility implication'], [
('T1','Direct ML retrieval','machine/deep learning, neural networks, tree ensembles, boosting, SVM, kNN, naive Bayes, AutoML, LLM, SHAP','No automatic inclusion; full content adjudicated'),
('T2','ML-adjacent boundary retrieval','clustering, PCA/factor analysis, latent classes/profiles, penalised regression, association rules','Catalogued separately unless another eligible ML component was central'),
('T3','Nonspecific prediction retrieval','prediction model, risk score, classification terminology without a named method','Full text used to identify the fitted method'),
('All','Collision control','Case-sensitive abbreviations and contextual matching','Clinical units and unrelated abbreviations were excluded')])}

{table(['#','Year','Citation/title','Method/boundary category','Exclusion basis','DOI'], adjacent_rows)}

## Table S2.5. Study-family linkage rules and evidence (n=24 additional/companion reports)

The special 2021 reconstruction report is shown with its target discordance and evidence limitation; the decision is a publication-family consolidation directed by the author, not a claim that the two reports analysed an identical outcome.

{table(['Report ID','Year','Report title','Representative report','Linkage type','Cohort/protocol/bibliographic evidence','Why not counted separately','DOI'], linkage_rows)}

Reports were linked only when overlapping participants or data years and a shared model-development/evaluation pathway supported a common underlying study. Similar authors, topics, or outcomes alone were insufficient. The representative-report map is also supplied in Additional file 8, sheets 01_STUDIES and 15_SUPPLEMENT_MANIFEST.

## Table S2.6. Analytic-task taxonomy (n=222 studies)

{table(['Task','n','Operational assignment'], [('Classification',206,'Categorical fitted target and classification was the primary objective'),('Continuous-outcome prediction',5,'Continuous fitted outcome and predictive-error evaluation'),('Other primary tasks',11,'Imputation, clustering, causal/structural, representation, or other nonclassification objective; ancillary classifiers did not alter assignment')])}

## Table S2.7. Analysis-unit and denominator map

{table(['Analysis unit','n','Use'], [('Eligible reports before linkage',246,'Study-family linkage'),('Additional/companion reports',24,'Not counted separately'),('Unique included studies',222,'Corpus-level synthesis'),('Classification-primary studies',206,'Classification-process audit'),('Continuous-outcome studies',5,'Task-specific synthesis'),('Other primary tasks',11,'Task-specific synthesis'),('Multi-year pooled studies',180,'Combined-weight audit'),('Explicit importance studies',126,'Importance-method audit'),('Codable importance-domain studies',81,'Variable-domain frequencies'),('PROBAST+AI development units',203,'Development methodological quality'),('PROBAST+AI evaluation units',243,'Evaluation risk of bias')])}

## Table S2.8. Core extraction dictionary (25 study-level items)

{table(['#','Item'], extraction_items)}

## Table S2.9. Figure, table, container, and panel counting rules

{table(['Unit','Counting rule'], [('Figure/table container','One numbered or uniquely labelled figure or table; the deduplicated audit denominator is 2,095 containers'),('Figure panel','Explicit A, B, C, and similar constituent panels counted separately within the parent container'),('Unpanelled figure','A figure container without explicit constituent panel labels'),('Visual unit','One unpanelled figure or each explicit figure panel; descriptive only'),('Subtable','Explicit A, B, C subdivision of a numbered table; tracked separately when recoverable'),('Denominator safeguard','Panel and subtable counts are never added to the 2,095-container denominator')])}

## Table S2.10. Visual-evidence interpretation and uncertainty rules (2,095 containers; 1,529 image-interpreted)

{table(['Rule','Operational implementation'], [('Inventory','Enumerate every available main-report and supplementary figure and table'),('Native content','Retain machine-readable table cells and captions where recoverable'),('Image content','Interpret rendered figures/image tables directly with the ChatGPT image model; no OCR engine'),('Quantitative acceptance','Require a completed visual reading or corroborating native report text/table'),('Uncertainty','Keep uncertain/unreadable objects flagged; do not interpolate unlabelled bars or curves'),('Provenance','Record source file, page/object label, image path, transcription, interpretation, status, and retry')])}

## Table S2.11. Nonclassification synthesis rules

{table(['Task','Primary synthesis safeguard'], [('Continuous-outcome prediction','Error and fit measures retained separately from classification metrics'),('Imputation','Masking design, reconstruction target, and reconstruction error'),('Clustering','Stability, replication, and assignment validity'),('Causal/structural analysis','Identification assumptions and estimand'),('Representation learning','Representation validity and downstream evaluation')])}

## Table S2.12. Classification-process audit codebook

{table(['Domain','Operational content'], [('Target construction','Outcome timing, source, cutoff basis, class structure, reproducibility, and credibility'),('Data assembly','KNHANES years/cycles, pooling, sample and event counts, predictor dimension, and external linkage'),('Evaluation integrity','Missingness, imbalance timing, original test distribution, threshold selection, and leakage'),('Model development','Algorithms, tuning, validation, performance, uncertainty, and best-model designation')])}

## Table S2.13. Rationale, analytic function, variable-importance, and claim codebook

{table(['Construct','Operational rule'], [('Stated rationale','Purpose stated in Introduction'),('Implemented function','Analysis actually performed'),('Variable importance','Named model-based importance/explanation method and interpreted model'),('Downstream inference','Model-derived ranking explicitly determines later statistical-model variables'),('Exact carryover','Same selected variables enter the inferential model without additions or omissions'),('Claim support','Discussion/Conclusion claim cross-tabulated with prespecified supporting evidence')])}

## Table S2.14. Reporting-completeness rules

{table(['Construct','Operational rule'], [('Reporting completeness','Nineteen prespecified TRIPOD+AI-derived reporting elements; not a full checklist score'),('Missingness','Not reported when applicable but absent; Not applicable when the construct does not apply; Unclear retained separately'),('Review status','Evidence-assisted primary review until independent second review and consensus')])}

## Table S2.15. Complex-survey appraisal rules

{table(['Step','Operational rule'], [('Applicability','Classify target population, estimand, and claim before judging design use'),('Components','Audit weights, strata, clusters, design-based variance, subpopulation handling, and combined-cycle weights'),('Interpretation','Do not infer design handling from use of KNHANES alone; unreported analyses remain Not reported')])}

## Table S2.16. PROBAST+AI operational rules

{table(['Construct','Operational rule'], [('Scope','Prediction-model classification and continuous-outcome studies; other-task studies are not applicable'),('Unit','Separate index-model development and performance-evaluation units'),('Judgement','Retain signalling responses, domains, overall judgement, applicability, evidence, and rationale'),('Review status','Primary evidence review completed; independent second reviewer and consensus remain pending')])}

## Table S2.17. Synthesis and statistical-analysis definitions

{table(['Analysis','Definition'], [('Descriptive synthesis','Frequencies/percentages, medians/IQRs, and narrative synthesis; overlapping indicators identified'),('Performance','Study-specific only; no pooling across nonexchangeable outcomes, prevalences, thresholds, splits, or datasets'),('Nonclassification safeguards','Continuous error/fit metrics; masking/reconstruction for imputation; stability/replication for clustering; identification assumptions for causal work; representation validity where applicable'),('Conditional denominators','Used only where the process applied and stated beside each result'),('Temporal periods','Through 2019; 2020–2022; 2023–2024; 2025–2026, with the last period incomplete'),('Trend models','Publication year entered continuously; odds ratios are descriptive associations, not causal effects')])}
"""
    (APP / "additional_file2_methods.md").write_text(text, encoding="utf-8")


def build_af3(integrated, analysis):
    cats = Counter(r["topic"] for r in integrated)
    years = Counter(r["year"] for r in integrated)
    roles = Counter(r["knhanes_role"] for r in integrated)
    layers = analysis["data_layer"]
    nonclass = [r for r in integrated if r["type"] != "Classification"]
    regression = [r for r in nonclass if r["type"] == "Regression"]
    other = [r for r in nonclass if r["type"] == "Non-predictive"]
    study_headers = ["Study", "Year", "Outcome/objective", "Methods", "Validation/evaluation", "Reported result"]
    def study_rows(rows):
        return [(display_key(r["key"]), r["year"], r["outcome"], r["models"], r["validation_protocol"], r["reported_metrics_full"] or r["findings"]) for r in rows]
    text = f"""# Additional file 3. Evidence Base and Nonclassification Analytic Tasks

This file shadows Results 4.1–4.2.

## Table S3.1. Included studies by publication year (n=222 studies)

{freq(dict(sorted(years.items(), key=lambda x: int(x[0]))), 222)}

## Table S3.2. Complete topic distribution (n=222 studies)

{freq(cats, 222)}

## Table S3.3. KNHANES data role and survey components (n=222 studies)

### Data-source role

{freq(roles, 222)}

### Survey components (overlap permitted)

{table(['Component','Studies'], layers.items())}

{figure('S3.1', FIG + '/fig2_publication.pdf', 'Annual publication volume and cumulative growth of the 222-study evidence base (n=222 studies).')}

## Table S3.4. Detailed characteristics of five continuous-outcome prediction studies

{table(study_headers, study_rows(regression))}

## Table S3.5. Detailed characteristics of eleven other-task studies

{table(study_headers, study_rows(other))}

The three ancillary classifiers reported in nonclassification-primary studies remain described in the integrated study-level audit but do not enter the 206-study classification cohort.
"""
    (APP / "additional_file3_evidence_nonclassification.md").write_text(text, encoding="utf-8")


def build_af4(integrated, prompt3, target, analysis):
    metrics = prompt3["metric_counts"]
    uncertainty = {k: metrics[k] for k in ("Calibration", "Confidence interval", "SD/resampling distribution", "Paired model comparison")}
    selected = [r for r in integrated if r["key"] in {"ahn2025discovering", "choi2023comparisons", "hunag2023predicting"}]
    selected_rows = [(display_key(r["key"]), r["outcome"], r["best_criterion"], r["best_value"], r["evaluation"], r["selection_evidence"], r["figure_candidate_locations"]) for r in selected]
    best_rows = [(display_key(r["key"]), r["outcome"], r["best_model_full"], r["best_criterion"], r["best_value"], r["evaluation"].replace("_", " "), r["selection_evidence"])
                 for r in integrated if r["classifier_process_eligible"] == "Y" and r["best_value"] != "NR"]
    assert len(best_rows) == 66, f"Expected 66 extractable best values, found {len(best_rows)}"
    save_barh(target['counters']['outcome_construction'],
              ['Continuous/score variable discretised','Composite clinical rule','Existing categorical response/diagnosis','Ordinal categories collapsed or retained','Construction not recoverable'],
              'Original outcome construction (n=206)', 'supp_s4_outcome.pdf')
    save_barh(target['counters']['classification_scheme'],
              ['Binary only','Multiple binary endpoints','Multiclass only','Both binary and multiclass','Class count not recoverable'],
              'Classification structure (n=206)', 'supp_s4_structure.pdf')
    text = f"""# Additional file 4. Detailed Classification-Process Audit

This file shadows Results 4.3. The denominator is 206 classification-primary studies unless stated otherwise.

{figure('S4.1', FIG + '/fig3_problem.pdf', 'Detailed outcome timing, outcome construction, and class structure among 206 classification studies. The separate source registry retains 162 current-state, 1 future-outcome, and 43 unclear timing judgements.')}

## Table S4.1. Cut-off and outcome-definition basis (n=206 classification studies)

{freq(target['counters']['cutoff_basis'], 206)}

## Table S4.2. Outcome reproducibility and credibility (n=206 classification studies)

{freq(prompt3['outcome_reproducibility'], 206)}

{freq(prompt3['outcome_credibility'], 206)}

## Table S4.3. Predictor reconstructability and alignment (n=206 classification studies)

{freq(prompt3['predictor_reconstructability'], 206)}

{freq(prompt3['target_predictor_alignment'], 206)}

{figure('S4.2', FIG + '/fig4_data.pdf', 'KNHANES data assembly, including survey-year scope, survey components, analytic sample size, and predictor dimensionality.')}

## Table S4.4. Sample, predictor, and event-information recoverability (n=206 classification studies unless noted)

{table(['Indicator','Reported/Recoverable','Denominator'], [('Analytic sample size',134,206),('Candidate/input-variable count',69,206),('Class distribution',41,206),('Sample-size justification',2,222)])}

## Table S4.5. Multi-year pooling and survey scope (n=222 studies)

{freq(analysis['wave_scope'], 222)}

## Table S4.6. Class-imbalance strategy (n=206 classification studies)

{freq(prompt3['imbalance_strategy'], 206)}

## Table S4.7. Order of imbalance handling (n=206 classification studies)

{freq(prompt3['imbalance_application_order'], 206)}

## Table S4.8. Evaluation/test distribution (n=206 classification studies)

{freq(prompt3['test_distribution'], 206)}

## Table S4.9. Imbalance strategy by reported metric (n=206 classification studies)

{table(['Strategy','Accuracy','AUROC','AUPRC','F1','Calibration'], [(k,v.get('Accuracy',0),v.get('AUROC',0),v.get('AUPRC/average precision',0),v.get('F1',0),v.get('Calibration',0)) for k,v in prompt3['strategy_by_metric'].items()])}

{figure('S4.3', FIG + '/fig6_modeling.pdf', 'Algorithms, tuning, and validation design among 206 classification studies; these descriptive rates are not comparative performance estimates.')}

## Table S4.10. Classification-performance and uncertainty indicators (n=206 classification studies)

{freq(metrics, 206)}

### Calibration and comparative uncertainty

{freq(uncertainty, 206)}

## Table S4.11. Best-model designation criteria (n=206 classification studies)

{freq(prompt3['selection_metric'], 206)}

## Table S4.12. Confidence intervals, resampling distributions, and paired comparisons

{freq(uncertainty, 206)}

## Table S4.13. Visual-object disposition

{table(['Container/interpretation category','n','Denominator'], [('Main-report figures',809,2095),('Main-report tables',817,2095),('Supplementary figures',167,2095),('Supplementary tables',302,2095),('Image interpretation required',1529,2095),('Complete interpretation',1523,1529),('Source artwork unavailable',5,1529),('Publisher raster illegible',1,1529)])}

## Table S4.14. Metric-sensitive evidence and adjudicated discrepancies

{table(['Study','Outcome','Selection criterion','Selected value','Evaluation','Selection evidence','Figure locations'], selected_rows)}

The 976 performance-screened figures are the figure subset of the complete 2,095-container ledger. The 1,529 image-interpreted objects include image tables as well as figures and therefore use a different, explicitly stated denominator. There were 539 metric-sensitive performance candidates across 177 studies. The complete 66-study best-value ledger, including Ahn 2025 F1=0.754 and Huang 2023 Accuracy=0.818, is retained in Additional file 8 rather than duplicated here.
"""
    (APP / "additional_file4_classification.md").write_text(text, encoding="utf-8")


def build_af5(ml, importance, details, prompt1):
    s = importance["summary"]
    rationale = ml["justification"]
    function = ml["analytic_function"]
    discussion = ml["discussion"]
    guided = [(display_key(r["key"]), r["method"], r["selected_n"], r["inferential_n"], r["inference"], r["evidence"]) for r in s["guided_studies"]]
    selection = Counter()
    for r in details:
        for value in (r.get("selection_strategies") or "").split(";"):
            if value.strip(): selection[value.strip()] += 1
    carry_rows=[]
    for r in guided:
        selected_n, inferential_n, inference, evidence = r[2], r[3], r[4], r[5]
        status = "Exact one-to-one carryover" if selected_n == inferential_n else ("Restricted cubic splines applied to selected continuous variables" if "spline" in (inference+evidence).lower() else "Expanded/modified before inference")
        carry_rows.append((r[0], selected_n, inferential_n, status, inference, evidence))
    text = f"""# Additional file 5. Analytic Function and Variable-Importance Audit

This file shadows Results 4.4.

## Table S5.1. Stated ML rationale (n=222 studies; categories overlap)

{freq(rationale, 222)}

## Table S5.2. Actual analytic function (n=222 studies; categories overlap)

{freq(function, 222)}

{figure('S5.1', FIG + '/fig8_interpretation.pdf', 'Stated rationale among 222 studies and classification endpoints, importance methods, and downstream inference paths within the 206-study classification cohort; conditional denominators are shown.')}

## Table S5.3. Importance methods and interpreted-model reporting (n=126 explicit-importance studies)

{freq(s['importance_method_counts'], 126)}

## Table S5.4. Important-variable selection rules (n=126 explicit-importance studies; categories overlap)

{freq(selection, 126)}

{figure_panel('S5.2', FIG + '/fig9_importance_endpoints.pdf', '0 248 393 0', 'Final analytic endpoints of 206 classification studies (source panel A).')}

{figure('S5.3', FIG + '/fig10_important_variables.pdf', 'Frequently prioritised variable domains among 81 studies naming at least one codable variable; these are model-reliance frequencies, not population effects.')}

## Table S5.5. Importance-to-inference pathways (n=7)

{table(['Study','Importance/selection method','Selected n','Inferential n','Downstream analysis','Evidence'], guided)}

## Table S5.6. Carryover, additions, and transformations (n=7 importance-guided inference studies)

{table(['Study','Selected n','Inferential n','Carryover/change','Downstream analysis','Evidence'], carry_rows)}

## Table S5.7. Discussion claim categories (n=222 studies; categories overlap)

{freq(discussion, 222)}

## Table S5.8. Claim–support cross-tabulation (n=222 studies)

{table(['Claim/support combination','n'], prompt1['claim_evidence'].items())}

## Table S5.9. Noncausal and survey-design caveats (n=222 studies unless conditional denominator shown)

{table(['Indicator','n','Denominator'], [('Factor/association insight',150,222),('Factor insight with explicit noncausal caveat',46,150),('Any cross-sectional noncausal caveat',51,222),('Survey-design limitation acknowledged',discussion.get('acknowledges_survey_design_limit',0),222)])}

The full 126-study importance extraction and all retained evidence excerpts are retained in the accompanying TSV/XLSX backdata.
"""
    (APP / "additional_file5_analytic_function.md").write_text(text, encoding="utf-8")


def build_af6(probast, survey_rows, integrated):
    dev, eva = probast["development"], probast["evaluation"]
    adherence = Counter(r.get("methodological_adherence") or r.get("survey_methodological_adherence") or "Not reported" for r in survey_rows)
    contextual = body_after_title(APP / "appendix14_extended_audits.md")
    contextual = contextual[contextual.find("## Contextual methodological benchmark"):contextual.find("## Study-level figure coverage")]
    contextual = contextual.replace("## Contextual methodological benchmark", "### Contextual methodological benchmark (comparison framework; no study denominator)")
    report_rows = [(display_key(r.get("key")), r.get("sample_filtering"), r.get("operational_definition"), r.get("missing_data"), r.get("validation_protocol"), r.get("performance_reporting_depth"), r.get("code_data_availability")) for r in integrated]
    included_ids = {r.get("key") for r in integrated}
    unit_mapping = []
    for path in sorted((DATA / "probast_ai_reassessment/records").glob("*.json")):
        record = load_json(path)
        if record.get("study_id") not in included_ids:
            continue
        dev_n = sum(bool(m.get("development")) for m in record.get("models", []))
        eval_n = sum(len(m.get("evaluations", [])) for m in record.get("models", []))
        unit_mapping.append((display_key(record.get("study_id")), record.get("scope_status"), dev_n, eval_n,
                             "; ".join(e.get("assessment_id", "NR") for m in record.get("models", []) for e in m.get("evaluations", [])) or "NA"))
    survey_compact = [(display_key(r.get("study_id")), f"{(r.get('analytic_role') or '').replace('_',' ')}; {r.get('applicability')}", r.get("methodological_adherence"),
                       f"reported {r.get('weights_reported')}; fitting {r.get('weights_used_in_training')}; evaluation {r.get('weights_used_in_evaluation')}; combined {r.get('integrated_weights_used')}",
                       r.get("evidence_quote")) for r in survey_rows]
    def domain_rows(part):
        return [(d,c.get('low',0),c.get('high',0),c.get('unclear',0)) for d,c in part['domains'].items()]
    tripod = load_json(DER / 'tripod_stats.json')['items']
    item_labels = {
        'title_design':'Design identified in title', 'abstract_structured':'Structured abstract',
        'background_objective':'Background and objective', 'data_source':'Data source and period',
        'participants_eligibility':'Eligibility criteria', 'outcome_definition':'Outcome definition',
        'predictors_description':'Predictor description', 'sample_size_justification':'Sample-size rationale',
        'missing_data':'Missing-data handling', 'model_building':'Model building',
        'model_performance_measures':'Performance measures', 'model_evaluation':'Model evaluation',
        'results_participants':'Participant flow/results', 'results_performance':'Performance results',
        'limitations':'Limitations', 'data_availability':'Data availability',
        'code_availability':'Code availability', 'funding':'Funding', 'model_availability':'Usable final model'}
    report_item_rows = [(item_labels[k], v['yes'], v['applicable'], f"{v['pct']:.1f}", f"{v['ci'][0]:.1f}–{v['ci'][1]:.1f}")
                        for k, v in tripod.items() if k in item_labels]
    text = f"""# Additional file 6. Methodological and Evidentiary Appraisal Results

This file shadows Results 4.5. Reporting completeness, survey appraisal, and PROBAST+AI remain separate constructs.

## Table S6.1. Nineteen reporting-completeness items (n=222 studies; item-specific applicability shown)

{table(['Reporting item','Yes','Applicable','%','95% CI'], report_item_rows)}

## Table S6.2. Study-level reporting results (n=222 studies)

{table(['Study','Cohort flow','Outcome','Missing data','Validation','Uncertainty','Code'], report_rows)}

## Table S6.3. Survey-design component reporting (n=222 studies)

{table(['Component','Studies'], [('Weights reported',47),('Weights used in training',2),('Weights used in evaluation',4),('Strata/clusters reported',94),('Strata/clusters used for uncertainty',20),('Combined weights reported',2),('Combined weights used',1)])}

## Table S6.4. Multiyear pooling and combined-weight handling (n=180 multi-year pooled studies)

Only 2/180 studies pooling multiple survey years described a combined-weight strategy; one documented using the resulting weight in the retained appraisal.

## Table S6.5. Applicability and adherence decisions (n=222 studies)

{table(['Analytic role','Applicability rule'], [('Sample-conditional prediction','Weighted fitting not required unless claims extend to a population'),('Population performance','Design-consistent performance and uncertainty required'),('Population association/importance','Weights, strata, clusters, and design-based uncertainty required'),('Causal/effect estimation','Design and identification assumptions both required')])}

{freq(adherence, 222)}

### Study-level survey rationale (n=222 studies)

{table(['Study','Analytic role and applicability','Adherence','Design handling','Evidence'], survey_compact)}

## Table S6.6. Development-unit ratings (n=203)

Completed development units: {dev['n_units']}.

{table(['Domain','Low','High','Unclear'], domain_rows(dev))}

## Table S6.7. Evaluation-unit ratings (n=243)

Completed evaluation units: {eva['n_units']}.

{table(['Domain','Low','High','Unclear'], domain_rows(eva))}

## Table S6.8. Study-to-assessment-unit mapping (203 development and 243 evaluation units)

Development quality and evaluation risk of bias were assessed as separate model/evaluation units. The complete question bank, response options, rationales, scope registry, and blank second-reviewer/consensus fields accompany the repository under `data/probast_ai_reassessment/`.

{table(['Study','Scope status','Development units','Evaluation units','Evaluation IDs'], unit_mapping)}

## Table S6.9. Domain-level reasons for concern (203 development and 243 evaluation units)

{table(['Assessment/domain','High','Unclear','Low','Principal operational concern'],
[(f'Development: {d}',c.get('high',0),c.get('unclear',0),c.get('low',0),'Participant selection, predictor/outcome availability, effective information, preprocessing, and optimism control') for d,c in dev['domains'].items()] +
[(f'Evaluation: {d}',c.get('high',0),c.get('unclear',0),c.get('low',0),'Evaluation sampling, predictor/outcome compatibility, original prevalence, calibration, and uncertainty') for d,c in eva['domains'].items()])}

{contextual}
"""
    (APP / "additional_file6_appraisal.md").write_text(text, encoding="utf-8")


def build_af7(landscape, quality, prompt1):
    make_temporal_detail_figures(landscape)
    periods = landscape["period_order"]
    topic_rows=[]
    analytic_rows=[]
    for p in periods:
        x=landscape["periods"][p]
        div=x.get("diversity",{})
        topic_rows.append((p,x.get("n"),mapping_text(x.get('topic_counts_display',{})),div.get("observed_topics"),f"{div.get('effective_topics',0):.1f}",f"{100*div.get('normalized_shannon',0):.1f}",f"{div.get('top3_concentration_pct',0):.1f}"))
        analytic_rows.append((p,x.get("n"),mapping_text(x.get("task_counts",{})),mapping_text(x.get("model_counts",{})),mapping_text(x.get("importance_method_counts",{}))))
    qrows=[]
    for p,x in quality["periods"].items():
        qrows.append((p,x['n'],f"{x['general_median']:.1f}",x['external_n'],x['calibration_n'],x['items']['code_availability']['yes'],x['weights_fitting_n']))
    logistic=[]
    for k,v in prompt1["temporal_logistic"].items():
        beta=math.log(v['or_per_year'])
        se=(math.log(v['ci95_high'])-math.log(v['ci95_low']))/(2*1.96)
        p=math.erfc(abs(beta/se)/math.sqrt(2))
        logistic.append((k,v.get('n'),v.get('events'),f"{v.get('or_per_year',0):.2f}",f"{v.get('ci95_low',0):.2f}",f"{v.get('ci95_high',0):.2f}","<.001" if p<.001 else f"{p:.3f}"))
    text=f"""# Additional file 7. Temporal Changes in Analytic Practice and Evidentiary Support

This file shadows Results 4.6. The 2025–2026 period is incomplete because searching ended in September 2026.

{figure('S7.1', FIG + '/fig14_topic_diversification.pdf', 'Topic diversification over time among 222 studies, including composition, observed/effective topic counts, diversity, and concentration.')}

## Table S7.1. Period-specific topic diversity (n=222 studies)

{table(['Period','Studies','Topic frequencies','Observed topics','Effective topics','Normalised Shannon %','Top-three concentration %'],topic_rows)}

{figure('S7.2', FIG + '/fig15_temporal_methods.pdf', 'Temporal change in analytic methods, including task composition, algorithms, pooling scope, and variable-importance methods.')}

## Table S7.2. Period-specific analytic-function denominators (n=222 studies; conditional denominators shown)

{table(['Period','All studies','Task distribution','Algorithms','Importance methods'],analytic_rows)}

## Table S7.3. Period-specific reporting indicators (n=206 classification studies)

{table(['Period','Studies','Median completeness %','External/temporal validation','Calibration','Code available','Weights in fitting'],qrows)}

## Table S7.4. Publication-year logistic models (n=206 classification studies)

{table(['Indicator','n','Events','OR/year','95% CI low','95% CI high','P'],logistic)}

"""
    (APP / "additional_file7_temporal.md").write_text(text, encoding="utf-8")


def main():
    refs=load_json(ROOT/'references/refs.json')
    integrated=read_tsv(DATA/'INTEGRATED_STUDY_AUDIT.tsv')
    analysis=load_json(DER/'analysis.json')
    prompt3=load_json(DER/'prompt3_audit.json')
    target=load_json(DER/'target_definition_audit.json')
    ml=load_json(DER/'ml_rationale.json')
    importance=load_json(DER/'importance_pathway.json')
    details=read_tsv(DATA/'VARIABLE_IMPORTANCE_DETAILS.tsv')
    prompt1=load_json(DER/'prompt1_revision.json')
    probast=load_json(DER/'probast_ai.json')
    survey=read_tsv(DATA/'survey_design_appraisal/study_level_appraisal.tsv')
    landscape=load_json(DER/'temporal_landscape.json')
    quality=load_json(DER/'temporal_quality.json')
    build_af2(refs,analysis)
    build_af3(integrated,analysis)
    build_af4(integrated,prompt3,target,analysis)
    build_af5(ml,importance,details,prompt1)
    build_af6(probast,survey,integrated)
    build_af7(landscape,quality,prompt1)
    print('built Additional files 2--7 shadow structure')


if __name__=='__main__':
    main()
