"""Assemble the public reproducibility repository aipply-ahn/knhanes-ml-methodology-review (layout from the
AIPPLY-AHN repository guide, 2026-10-31) into a target folder; rerun to refresh it.
    python tools/build_public_repo.py <target_dir>
Copyright-protected article PDFs and extracted full texts, abstracts of retrieved records, caches and credentials
are never copied; the contact e-mail used for API polite pools is replaced by an environment variable."""
import csv, json, os, re, shutil, sys
from pathlib import Path
ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "tools"))
T = Path(sys.argv[1]).resolve()
J = lambda p: json.load(open(ROOT / p))


def w_csv(rel, rows, fields=None):
    p = T / rel; p.parent.mkdir(parents=True, exist_ok=True)
    fields = fields or (list(rows[0]) if rows else ["empty"])
    with open(p, "w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=fields, extrasaction="ignore"); w.writeheader(); w.writerows(rows)


def w_txt(rel, text):
    p = T / rel; p.parent.mkdir(parents=True, exist_ok=True); p.write_text(text, encoding="utf-8")


def cp(src, rel, sanitize=False):
    p = T / rel; p.parent.mkdir(parents=True, exist_ok=True)
    if sanitize:
        s = (ROOT / src).read_text(encoding="utf-8", errors="ignore")
        s = s.replace('MAILTO = os.environ.get("CONTACT_EMAIL", "your-email@example.org")', 'MAILTO = os.environ.get("CONTACT_EMAIL", "your-email@example.org")')
        s = s.replace("your-email@example.org", "your-email@example.org")
        p.write_text(s, encoding="utf-8")
    else:
        shutil.copy2(ROOT / src, p)


def data1():
    from openpyxl import load_workbook
    wb = load_workbook(ROOT / "manuscript/KNHANES_ML_review_Additional_Data_1.xlsx", read_only=True)
    out = {}
    for name in wb.sheetnames:
        rows = list(wb[name].iter_rows(values_only=True))
        out[name] = [dict(zip(rows[0], r)) for r in rows[1:]]
    return out


def main():
    D1 = data1(); AD = D1["Additional Data 1"]
    # ---------------- data/
    inc_groups = ("Core classification", "Method-focused", "Other health analysis")
    w_csv("data/studies.csv", [dict(study_id=d["Study ID"], study=d["Study"], title=d["Title"], journal=d["Journal"], year=d["Year"],
                                    doi_or_pmid=d["DOI or PMID"], report_type=d["Report type"], study_group=d["Study group"],
                                    included=d["Study group"] in inc_groups) for d in AD])
    # ---------------- 01_search
    corpus = J("results/rerun_20261031/baseline/corpus.json")["records"]
    w_csv("01_search/retrieved_records.csv", [dict(record_id=r["uid"], source=";".join(r.get("sources") or []), retrieval_run="baseline_2026-09-03_05",
                                                   doi=r.get("doi"), pmid=r.get("pmid"), title=r.get("title"), year=r.get("year"),
                                                   journal=r.get("journal")) for r in corpus])
    kci = J("results/raw/kci_20260905/census.json")["records"]
    kci = kci if isinstance(kci, list) else list(kci.values())
    w_csv("01_search/kci_records.csv", [dict(record_id="kci:" + r["kci_id"], retrieval_run="baseline_2026-09-05", title=r.get("title"),
                                             journal=r.get("journal"), pub_ym=r.get("pub_ym"),
                                             matched_queries=";".join(f"{m['dataset']} AND {m['method']}" for m in r.get("search_matches", [])))
                                        for r in kci])
    F = J("results/rerun_20261031/baseline/final_selection_flow.json")
    runs = [dict(run="baseline", source=k, records=v, date="2026-09-03 to 2026-09-05", note="") for k, v in F["sources"].items()]
    runs.append(dict(run="update_2026-10-31", source="all", records="", date="2026-10-31",
                     note="re-run of the same queries in progress; results will be added with a comparison to the baseline"))
    w_csv("01_search/search_updates.csv", runs)
    w_txt("01_search/queries_by_source.md", QUERIES)
    for s in ("census_epmc", "census_pubmed", "census_openalex", "census_kdca", "census_kdca_match", "census_kci", "common"):
        cp(f"tools/{s}.py", f"01_search/scripts/{s}.py", sanitize=True)
    cp("tools/census_merge.py", "01_search/deduplication.py", sanitize=True)
    cp("tools/census_screen.py", "01_search/keyword_filter.py", sanitize=True)
    # ---------------- 02_screening
    w_txt("02_screening/eligibility_criteria.md", ELIG)
    scr = J("results/rerun_20261031/baseline/screen.json")["rows"]
    w_csv("02_screening/screening_decisions.csv", [dict(record_id=r["uid"], stage="title-abstract dictionary screen", tier=r.get("tier"),
                                                        decision="advance" if r.get("tier") not in (None, "--") else "exclude (no ML or prediction term)",
                                                        method="deterministic dictionary (01_search/keyword_filter.py)", verification_status="rule-based")
                                                   for r in scr])
    refs = J("results/rerun_20261031/baseline/refs.json")
    w_csv("02_screening/report_decisions.csv", [dict(report_key=r["key"], record_id=r["uid"], doi=r.get("doi"), title=r.get("title"), year=r.get("year"),
                                                     decision=r.get("verdict"), reason=r.get("verdict_reason")) for r in refs])
    w_csv("02_screening/excluded_reports.csv", [dict(report_key=r["key"], record_id=r["uid"], doi=r.get("doi"), title=r.get("title"),
                                                     reason=r.get("verdict_reason")) for r in refs if r.get("verdict") == "EXCLUDE"])
    w_csv("02_screening/report_study_links.csv", [dict(study_id=d["Study ID"], representative_report=d["Study"], doi_or_pmid=d["DOI or PMID"],
                                                       report_type=d["Report type"], study_group=d["Study group"]) for d in AD if d["Study group"] in inc_groups]
          + [dict(study_id="", representative_report=r["key"], doi_or_pmid=r.get("doi") or r.get("pmid"), report_type=r.get("verdict"),
                  study_group="companion or duplicate report: " + (r.get("verdict_reason") or "")) for r in refs if r.get("verdict") in ("DUPLICATE", "LINKED_COMPANION")])
    fl = F["flow"]
    w_csv("02_screening/prisma_flow.csv", [dict(step=k, n=v) for k, v in fl.items() if not isinstance(v, dict)]
          + [dict(step="exclusion_reason:" + k, n=v) for k, v in fl["report_exclusion_reasons"].items()]
          + [dict(step="included_core_classification", n=193), dict(step="included_other_health_analysis", n=22), dict(step="included_method_focused", n=39)])
    # ---------------- 03_coding
    shutil.copy2(ROOT / "manuscript/KNHANES_ML_review_Additional_Data_1.xlsx", (T / "03_coding").mkdir(parents=True, exist_ok=True) or T / "03_coding/study_level_data.xlsx")
    cp("KNHANES_ML_study_audit_protocol.md", "03_coding/raw_coding_protocol.md")
    cb = D1["RC Codebook"]
    md = ["# Codebook", "", "Raw study-level codes: see raw_coding_protocol.md (item ID, question, allowed values and decision rules).",
          "Core reporting checklist: see 06_reporting_checklist/core_checklist.csv and scoring_rules.md.", "",
          "## Columns of study_level_data.xlsx", "", "Sheet 'Additional Data 1': one row per study (included or not included).",
          "Sheet 'RC Codebook': criterion, not-met and not-applicable conditions, stage, type, source of every checklist item.",
          "Sheet 'Scoring definitions': study and stage scores and their interpretation."]
    w_txt("03_coding/codebook.md", "\n".join(md) + "\n")
    w_csv("03_coding/source_evidence.csv", [dict(study_id=d["Study ID"], evidence_locations=d.get("Evidence locations"),
                                                 checklist_evidence=d.get("Core checklist evidence (full-text items)")) for d in AD])
    ov = J("prompts/implementation_records/coding_audit/overrides.json")
    w_csv("03_coding/verification_log.csv", [dict(study_id=s, item=i, value=v.get("value"), decision=v.get("decision"), reason=v.get("reason"),
                                                  process="Claude Code / Codex coding audit, rounds 1-6 (2026-10-28/29)")
                                             for s, it in sorted(ov.items()) for i, v in sorted(it.items())])
    for f in ("rc47_data_availability.tsv",):
        cp(f"prompts/implementation_records/coding_audit/{f}", f"03_coding/new_items/{f}")
    for f in ("t20b_t16.tsv", "t20b_t16_summary.md", "rc48_descriptive_design.tsv", "rc48_summary.md"):
        cp(f"prompts/implementation_records/coding_audit/new_items_20261031/{f}", f"03_coding/new_items/{f}")
    # ---------------- 04_ai_protocol
    w_csv("04_ai_protocol/model_manifest.csv", MANIFEST)
    A = "prompts/implementation_records/coding_audit"
    for f in ("PROTOCOL.md", "RULES_r1.md", "RULES_r2.md", "RULES_r3.md", "RULES_r4.md", "RULES_r5.md", "RAW_SCHEMA_PROPOSALS.md", "SOURCE_ISSUES.md"):
        cp(f"{A}/{f}", f"04_ai_protocol/coding_audit/{f}")
    cp(f"{A}/SUMMARY.md", "04_ai_protocol/audit_summary.md")
    for f in ("broadcast.jsonl", "claude.jsonl", "codex.jsonl"):
        cp(f"{A}/{f}", f"04_ai_protocol/coding_audit/logs/{f}")
    cp("prompts/implementation_records/v15_recode/CODING_GUIDE.md", "04_ai_protocol/prompts/checklist_recoding_guide.md")
    for g in ("EXTRACT_GUIDE.md", "REVIEW_GUIDE.md", "PROBAST_GUIDE.md"):
        cp(f"tools/{g}", f"04_ai_protocol/prompts/{g}")
    w_txt("04_ai_protocol/decision_rules.md", "# Decision rules\n\nThe written rules applied by both AI reviewers and the author in the coding audit are in\ncoding_audit/RULES_r1.md to RULES_r5.md (in force from the round named in each file). Changes to the raw coding frame\nare proposed and decided separately (coding_audit/RAW_SCHEMA_PROPOSALS.md); a proposal is applied only on the\nauthor's decision.\n")
    # ---------------- 05_analysis
    for p in sorted((ROOT / "tools").glob("*.py")):
        cp(f"tools/{p.name}", f"05_analysis/tools/{p.name}", sanitize=True)
    w_txt("05_analysis/README.md", ANALYSIS)
    w_txt("05_analysis/reproduce_all.py", REPRO)
    # ---------------- 06_reporting_checklist
    w_csv("06_reporting_checklist/core_checklist.csv", cb)
    w_csv("06_reporting_checklist/rc_to_public_id.csv", [dict(public_id=r["ID (Table 1)"], internal_code=r["Internal code"], item=r["Core item"]) for r in cb])
    w_txt("06_reporting_checklist/scoring_rules.md", "# Scoring rules\n\n" + "\n".join(f"- **{r['Term']}**: {r['Definition']}" for r in D1["Scoring definitions"]) + "\n")
    import importlib.util
    spec = importlib.util.spec_from_file_location("mp", ROOT / "prompts/implementation_records/tripod_mapping/build_mapping.py")
    src = (ROOT / "prompts/implementation_records/tripod_mapping/build_mapping.py").read_text()
    ns = {"__file__": str(ROOT / "prompts/implementation_records/tripod_mapping/build_mapping.py")}
    exec(src.split("wb = Workbook()")[0].replace("from openpyxl import Workbook", "").replace("from openpyxl.styles import Alignment, Font, PatternFill", ""), ns)
    w_csv("06_reporting_checklist/tripod_ai_official_mapping.csv",
          [dict(tripod_ai_item=r[0], official_text=r[1], requirement=r[2], knhanes_example=ns["EXAMPLE"][r[0]], layer=ns["layer"](r[0]),
                coding_plan=ns["plan"](r[0]), current_items=r[3], relation=r[4], scope=r[5], existing_codes=r[6], decision_needed=r[7]) for r in ns["R"]])
    w_txt("06_reporting_checklist/README.md", "Official TRIPOD+AI sub-items (52), the 19 elements this review reorganised for its own judgements, and the\nKNHANES-specific checklist are different layers. tripod_ai_official_mapping.csv maps every official sub-item to the\nchecklist; the mapping is a working document under the author's review (status in the coding_plan column).\n")
    # ---------------- 07_survey_design
    from checklist_v12 import _ctx
    ms, CORE, rows = _ctx()
    f = lambda d, k: ms.first(d, k)
    w_txt("07_survey_design/survey_coding_rules.md", SURVEY)
    cp("prompts/implementation_records/coding_audit/new_items_20261031/rc48_descriptive_design.tsv", "07_survey_design/descriptive_statistics.tsv")
    w_csv("07_survey_design/model_weighting.csv", [dict(study_id=d["study_id"], SUR06_weights_in_model_fitting=f(d, "SUR06")) for d in CORE])
    w_csv("07_survey_design/evaluation_weighting.csv", [dict(study_id=d["study_id"], SUR07_weights_in_performance_evaluation=f(d, "SUR07"),
                                                             SUR10_strata_psu_in_variance=f(d, "SUR10")) for d in CORE])
    t = J("results/derived/checklist_v22_scores.json"); k42 = next(str(i["idx"]) for i in t["items"] if i["id"] == "RC42")
    w_csv("07_survey_design/importance_weighting.csv", [dict(study_id=s, C40_weights_in_importance_aggregation=("NA" if k42 not in st["items"] else int(st["items"][k42])))
                                                        for s, st in sorted(t["studies"].items())])
    # ---------------- root
    w_txt("README.md", README)
    w_txt("CITATION.cff", CITATION)
    w_txt("LICENSE", MIT)
    w_txt("environment.yml", ENV)
    w_txt(".gitignore", "__pycache__/\n*.pyc\n*.pdf\nreferences/md/\nresults/raw/\n.env\n")
    print("built", T)


QUERIES = """# Search queries by source

Baseline searches: 3-5 September 2026, no date or language limits. Exact code: scripts/ (census_*.py).
An update re-running the same queries was started on 31 October 2026 (see search_updates.csv).

| Source | Query | Script |
|---|---|---|
| Europe PMC | Layer A: TITLE_ABS contains KNHANES, "Korea National Health and Nutrition Examination Survey" or "Korean National Health and Nutrition Examination Survey" (all records). Layer B: full text contains a KNHANES term AND an ML term (list in census_epmc.py) | scripts/census_epmc.py |
| PubMed | KNHANES[tiab] OR "Korea National Health and Nutrition Examination Survey"[tiab] OR "Korean National Health and Nutrition Examination Survey"[tiab] OR "Korea National Health and Nutrition Examination Survey"[mh]; records not in Europe PMC added | scripts/census_pubmed.py |
| OpenAlex | title_and_abstract.search: "KNHANES"; "Korea National Health and Nutrition Examination Survey" | scripts/census_openalex.py |
| Korean Citation Index | KEYALL: 7 survey names x 43 ML terms (301 queries; lists in census_kci.py) | scripts/census_kci.py |
| KDCA KNHANES publication list | complete author-registered publication list (not a keyword search) | scripts/census_kdca.py, census_kdca_match.py |

Deduplication: DOI, then PubMed ID, then normalised title (deduplication.py). Title/abstract screening: deterministic
dictionary of ML and prediction terms (keyword_filter.py; tiers T1 ML/AI method, T2 ML-adjacent, T3 prediction model
without ML term; records with no term are excluded at this stage).
"""

ELIG = """# Eligibility criteria

Included: reports that fitted at least one supervised learner outside the regression family to a designated
health-related outcome using data from any KNHANES survey cycle (e.g., decision trees, boosting, support vector
machines, neural networks, large language models). Logistic and linear regression, including penalised regression,
count as regression-family methods (Christodoulou et al., 2019).

Excluded: reports that cited KNHANES only for comparison; used only regression-family or unsupervised methods; or gave
insufficient information to establish the ML analysis and its results (reviews, commentaries, protocols, stand-alone
abstracts).

Study grouping: multiple reports of the same study (preprint and journal article, conference paper and journal
article, Korean- and English-language articles, article and its code or data deposit) form one study with one
representative report. Included studies are grouped as core classification (193), other health analysis (22) and
method-focused (39).

Screening stages: records passing the deterministic dictionary screen were judged against these criteria from the
available title, abstract or full text; the number judged from full text is not separately recorded for the
baseline search.
"""

MANIFEST = [
    dict(provider="Anthropic", model="Claude (Claude Code; reviewer id P2-CLAUDE-OPUS5 in the coding records)", version="as recorded per record",
         interface="Claude Code CLI", run_date="2026-09 to 2026-10", task="study-level extraction (protocol v1.2), checklist judgements, coding-audit reviewer A and integrator",
         prompt_file="prompts/, coding_audit/PROTOCOL.md", io_location="03_coding/, 04_ai_protocol/coding_audit/logs/claude.jsonl"),
    dict(provider="OpenAI", model="Codex", version="not recorded", interface="Codex CLI", run_date="2026-10",
         task="coding-audit reviewer B, coordinator rule adjudication", prompt_file="coding_audit/PROTOCOL.md, RULES_r*.md",
         io_location="04_ai_protocol/coding_audit/logs/codex.jsonl"),
    dict(provider="Author", model="-", version="-", interface="-", run_date="2026-09 to 2026-10",
         task="eligibility decisions, verification of the study-level dataset, final decisions on rules", prompt_file="-", io_location="-")]

ANALYSIS = """# Analysis code

tools/ holds the project scripts as used for the manuscript (copied without change except that the API contact
e-mail is read from the CONTACT_EMAIL environment variable). Main entry points:

- figures: make_main_figures.py (Figures 1-5 and appendix figures)
- core checklist: checklist_v22.py (scores), checklist_v22_table.py (Table 1), add_checklist_columns_v22.py (Additional Data 1)
- Additional Data 1 workbook: build_data1_workbook.py
- supplements: build_standalone_supplements.py

These scripts currently expect the project layout (protocol JSON records under data/protocol_v1_2/final, which hold
per-study evidence quotes and are not published here). reproduce_all.py documents the order of the steps. A standalone
pipeline that regenerates all tables and figures from the public coded data (03_coding/study_level_data.xlsx) is in
preparation and will be released with the submission tag.
"""

REPRO = '''"""Order of the steps that regenerate the review outputs inside the project layout (see README.md)."""
import subprocess, sys
STEPS = ["tools/checklist_v22.py", "tools/build_data1_workbook.py", "tools/make_main_figures.py", "tools/build_standalone_supplements.py"]
if __name__ == "__main__":
    for s in STEPS:
        print("running", s, flush=True)
        subprocess.run([sys.executable, s], check=True)
'''

SURVEY = """# Survey-design coding rules

KNHANES is a stratified, clustered probability sample with sampling weights. Each analysis stage is coded
separately; "used", "explicitly not used", "not reported" and "unclear" are kept apart, and use is not equated with
methodological validity.

| Stage | Raw code | Question |
|---|---|---|
| Weights mentioned | SUR04 | Were KNHANES sampling weights mentioned? |
| Descriptive statistics and population estimates | SUR05; RC48 | Were descriptive statistics weighted? RC48 (reporting item): whether descriptive statistics and population estimates were weighted, with the method, or identified as unweighted sample summaries; POPEST records whether population-level estimates were presented |
| Model fitting | SUR06; C22 | Were weights used in model fitting (and is it reported how, or why not)? |
| Performance evaluation | SUR07; C30 | Were performance measures weighted? |
| Uncertainty | SUR10; C33 | Were strata and PSUs used for variance estimation? |
| Combined years | SUR11; C04 | Were weights adjusted when pooling survey years? |
| Importance aggregation | C40 | When participant-level importance (SHAP, LIME) was aggregated, were weights used? |

Full definitions: 03_coding/raw_coding_protocol.md (SUR01-SUR15) and 06_reporting_checklist/core_checklist.csv.
"""

README = """# knhanes-ml-methodology-review

This repository provides search records, eligibility decisions, study-level coding, TRIPOD+AI mapping,
survey-design reporting assessments, AI-assisted verification documentation, and scripts for reproducing the
systematic methodological review results.

Review: *From Classification to Explanation: A Systematic Methodological Review of Supervised Machine Learning in a
National Health Survey* (Hongryul Ahn, The University of Suwon; manuscript under submission).

## Layout
| Folder | Content |
|---|---|
| 01_search | queries by source, retrieved records (bibliographic fields only), search runs, deduplication and keyword-filter code |
| 02_screening | eligibility criteria, dictionary screening decisions, report-level decisions and exclusions, report-study links, PRISMA counts |
| 03_coding | study-level coded data (Additional Data 1), raw coding protocol, evidence locations, verification log, newly coded items |
| 04_ai_protocol | AI model manifest, prompts and coding guides, written decision rules, audit logs and summary |
| 05_analysis | analysis scripts and the order of steps |
| 06_reporting_checklist | official TRIPOD+AI sub-item mapping, core checklist, public-to-internal ID map, scoring rules |
| 07_survey_design | survey-design coding rules and stage-specific codes (descriptive statistics, model fitting, evaluation, importance) |
| data | one row per study with identifiers and study group |

## Units
Record (search hit) -> report (publication) -> study (one or more reports; study_id KHMnnn) -> coded values with
evidence locations -> author verification -> tables and figures.

Deterministic steps (searches, DOI/PMID/title deduplication, dictionary screen, aggregation) are separated from
AI-assisted judgements (extraction, checklist coding, audit) and author decisions; 04_ai_protocol states what each AI
system did. No step that was not performed is reported as performed.

## Not included
Copyright-protected article PDFs and their extracted full texts, abstracts of retrieved records, and API credentials.

## Status
A search update re-running the baseline queries started on 31 October 2026; its records and a comparison with the
baseline will be added. Some checklist items (06_reporting_checklist, 03_coding/new_items) are under cross-review.

## Licence
Code: MIT (LICENSE). Coded data and documentation: CC BY 4.0.
"""

CITATION = """cff-version: 1.2.0
message: "If you use these materials, please cite the review."
title: "knhanes-ml-methodology-review: reproducibility materials for a systematic methodological review of supervised machine learning in KNHANES"
authors:
  - family-names: Ahn
    given-names: Hongryul
    affiliation: "Division of AI and Data Science, DS&ML Center, The University of Suwon"
    orcid: "https://orcid.org/0000-0002-5941-9784"
repository-code: "https://github.com/aipply-ahn/knhanes-ml-methodology-review"
license: MIT
date-released: 2026-10-31
"""

MIT = """MIT License

Copyright (c) 2026 Hongryul Ahn

Permission is hereby granted, free of charge, to any person obtaining a copy of this software and associated
documentation files (the "Software"), to deal in the Software without restriction, including without limitation the
rights to use, copy, modify, merge, publish, distribute, sublicense, and/or sell copies of the Software, and to permit
persons to whom the Software is furnished to do so, subject to the following conditions:

The above copyright notice and this permission notice shall be included in all copies or substantial portions of the
Software.

THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR IMPLIED, INCLUDING BUT NOT LIMITED TO THE
WARRANTIES OF MERCHANTABILITY, FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE AUTHORS OR
COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR
OTHERWISE, ARISING FROM, OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE SOFTWARE.
"""

ENV = """name: knhanes-ml-review
channels:
  - conda-forge
dependencies:
  - python=3.11
  - numpy
  - pandas
  - matplotlib
  - openpyxl
  - requests
  - beautifulsoup4
"""

if __name__ == "__main__":
    main()
