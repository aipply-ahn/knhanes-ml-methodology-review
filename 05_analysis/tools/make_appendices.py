"""JMIR Multimedia Appendix 1-7 생성.  python tools/make_appendices.py"""
import sys, os, json, glob, re
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from common import PROJ, REF, DER, load
OUT = os.path.join(PROJ, "manuscript", "submission", "appendices")
os.makedirs(OUT, exist_ok=True)
R = {r["key"]: r for r in load(os.path.join(REF, "refs.json"))}
E = {d["key"]: d for d in (load(f) for f in glob.glob(os.path.join(PROJ, "data/extraction/*.json")))}
S = load(os.path.join(DER, "screen.json"))
I_DOM = load(os.path.join(DER, "important_variable_domains.json"))
def w(f, txt): open(os.path.join(OUT, f), "w", encoding="utf-8").write(txt); print("  " + f)

PRISMA = [
 ("TITLE","1","Title","Identify the report as a systematic review.","Title"),
 ("ABSTRACT","2","Abstract","See the PRISMA 2020 for Abstracts checklist.","Abstract"),
 ("INTRODUCTION","3","Rationale","Describe the rationale for the review.","Introduction, paras 1-4"),
 ("","4","Objectives","Provide an explicit statement of the objectives.","Introduction, final para"),
 ("METHODS","5","Eligibility criteria","Specify inclusion and exclusion criteria and grouping.","Methods, Eligibility Criteria"),
 ("","6","Information sources","Specify all sources searched and the date each was last searched.","Methods, Search Strategy; Appendix 4"),
 ("","7","Search strategy","Present the full search strategies for all sources.","Appendix 4"),
 ("","8","Selection process","Specify the methods used to decide whether a study met the criteria.","Methods, Screening; Appendix 2"),
 ("","9","Data collection process","Specify the methods used to collect data from reports.","Methods, Data Extraction; Appendix 3"),
 ("","10a","Data items (outcomes)","List and define all outcomes for which data were sought.","Methods, Data Extraction; Appendix 3"),
 ("","10b","Data items (other)","List and define all other variables for which data were sought.","Appendix 3"),
 ("","11","Study risk of bias assessment","Specify the methods used to assess risk of bias.","Methods, Risk of Bias; Appendix 7"),
 ("","12","Effect measures","Specify for each outcome the effect measure used.","Not applicable; no effect measures synthesised"),
 ("","13a","Synthesis (eligibility)","Describe processes to decide which studies were eligible for each synthesis.","Methods, Synthesis"),
 ("","13b","Synthesis (preparation)","Describe any methods required to prepare the data.","Methods, Data Extraction"),
 ("","13c","Synthesis (tabulation)","Describe any methods used to tabulate or visually display results.","Methods, Synthesis"),
 ("","13d","Synthesis (statistical)","Describe any methods used to synthesise results.","Methods, Synthesis; meta-analysis not performed"),
 ("","13e","Synthesis (heterogeneity)","Describe any methods used to explore heterogeneity.","Methods, Synthesis"),
 ("","13f","Synthesis (sensitivity)","Describe any sensitivity analyses.","Not applicable; reports not retrieved were excluded before detailed synthesis"),
 ("","14","Reporting bias assessment","Describe methods to assess risk of bias due to missing results.","Not applicable; no pooled estimates"),
 ("","15","Certainty assessment","Describe methods to assess certainty in the body of evidence.","Not applicable; descriptive synthesis"),
 ("RESULTS","16a","Study selection (flow)","Describe the results of the search and selection process.","Results, Study Selection; Figure 1"),
 ("","16b","Study selection (exclusions)","Cite studies that met many but not all criteria and explain why excluded.","Results, Study Selection; Appendix 5"),
 ("","17","Study characteristics","Cite each included study and present its characteristics.","Appendix 6"),
 ("","18","Risk of bias in studies","Present assessments of risk of bias for each included study.","Appendix 7"),
 ("","19","Results of individual studies","Present for all outcomes, for each study, summary statistics.","Appendix 6"),
 ("","20a","Results of syntheses (a)","Summarise characteristics and risk of bias among contributing studies.","Results, all subsections"),
 ("","20b","Results of syntheses (b)","Present results of all statistical syntheses.","Results; Table 1; Figures 2-4"),
 ("","20c","Results of syntheses (c)","Present investigations of possible causes of heterogeneity.","Results, Change Over Time"),
 ("","20d","Results of syntheses (d)","Present results of sensitivity analyses.","Results, Study Selection"),
 ("","21","Reporting biases","Present assessments of risk of bias due to missing results.","Not applicable"),
 ("","22","Certainty of evidence","Present assessments of certainty in the body of evidence.","Not applicable"),
 ("DISCUSSION","23a","Interpretation","Provide a general interpretation of the results.","Discussion, Principal Results"),
 ("","23b","Limitations of evidence","Discuss limitations of the evidence included.","Discussion, Limitations"),
 ("","23c","Limitations of process","Discuss limitations of the review processes used.","Discussion, Limitations"),
 ("","23d","Implications","Discuss implications for practice, policy, and future research.","Discussion, Conclusions"),
 ("OTHER","24a","Registration","Provide registration information.","Not registered; stated in Limitations"),
 ("","24b","Protocol","Indicate where the review protocol can be accessed.","Appendices 2 and 3"),
 ("","24c","Amendments","Describe any amendments to registration information.","Not applicable"),
 ("","25","Support","Describe sources of financial or non-financial support.","Funding Statement"),
 ("","26","Competing interests","Declare any competing interests.","Conflicts of Interest"),
 ("","27","Availability of data, code","Report which materials are publicly available and where.","Data Availability"),
]
L = ["# Multimedia Appendix 1. PRISMA 2020 Checklist\n",
     "Machine Learning Applied to the Korea National Health and Nutrition Examination Survey: "
     "Systematic Review of Study Design, Methods, and Reporting\n",
     "| Section | Item | Checklist item | Description | Location where item is reported |",
     "|---|---|---|---|---|"]
L += [f"| {a} | {b} | {c} | {d} | {e} |" for a, b, c, d, e in PRISMA]
w("appendix1_prisma_checklist.md", "\n".join(L) + "\n")

src = open(os.path.join(PROJ, "tools/census_screen.py"), encoding="utf-8").read()
dic = src[src.index("T1 = {"):src.index("NEG = ")]
adj_for_screening = sorted([r for r in R.values() if r["verdict"] == "INCLUDE_ADJACENT"],
                           key=lambda r: (-(r.get("year") or 0), r["key"]))
adj_lines = ["", "## Part D. ML-adjacent report catalogue (n=134)", "",
             "These reports were assessed in full as boundary records but excluded because the adjacent method was the primary/final analytic engine without another eligible ML component. The list is report-level and separate from bibliographic duplicates and linked reports within included study families.", "",
             "| # | Year | Citation/title | Method or boundary category | Exclusion basis | DOI |",
             "|---:|---:|---|---|---|---|"]
for i, r in enumerate(adj_for_screening, 1):
    d = E.get(r["key"], {})
    method = "; ".join(str(x) for x in (d.get("models") or [])) or d.get("task") or r.get("bench_category") or "ML-adjacent"
    adj_lines.append(f"| {i} | {r.get('year') or ''} | {(r.get('title') or r['key']).replace('|','/')} | {str(method).replace('|','/')} | Primary/final adjacent analysis; no additional eligible ML component central to the objective | {r.get('doi') or ''} |")
linked = R["amarbayasgalan2021reconstruction"]
adj_lines += ["", "## Part E. Study-family linkage (24 additional/companion reports)", "",
              "The 246 eligible reports comprised 222 unique full-report studies and 24 additional or companion reports linked within represented publication families. The table below records the newly adjudicated 24th linkage; the preceding 23 report-family links remain in the screening provenance. No eligible report remains unretrieved.", "",
              "| Report ID | Year | Title | Representative report | Linkage type | Audit caveat | DOI |", "|---|---:|---|---|---|---|---|",
              f"| {linked['key']} | {linked.get('year') or ''} | {(linked.get('title') or '').replace('|','/')} | {linked.get('companion_of')} | Author-adjudicated methodological/publication-family companion | Diabetes and coronary-heart-disease targets differ; identical outcome analysis is not asserted | {linked.get('doi') or ''} |"]
w("appendix2_screening_manual.md",
  "# Multimedia Appendix 2. Screening Manual and Terminology Dictionary\n\n"
  "## Part A. Adjudication manual\n\n"
  + open(os.path.join(PROJ, "tools/REVIEW_GUIDE.md"), encoding="utf-8").read()
  + "\n\n## Part B. Machine-readable terminology dictionary\n\n"
  "Regular expressions applied to title, abstract, keywords, and MeSH terms. Abbreviations are "
  "matched case-sensitively using `(?-i:...)` to avoid collisions with clinical units (mL, dL) "
  "and unrelated terms (AI for adequate intake, RF for radiofrequency).\n\n```python\n" + dic
  + "```\n\n## Part C. Screening yield\n\n| Tier | Records |\n|---|---:|\n"
  + "\n".join(f"| {k} | {v} |" for k, v in sorted(S["tiers"].items())) + "\n"
  + "\n".join(adj_lines) + "\n")

w("appendix3_extraction_manual.md", "# Multimedia Appendix 3. Data Extraction Manual\n\n"
  "## Analysis-unit and denominator map\n\n"
  "| Analysis unit | n | Use in this review |\n|---|---:|---|\n"
  "| Included full-report studies | 222 | Overall evidence base, content coding, and reporting analysis |\n"
  "| Classification-primary studies | 206 | Core classification workflow and variable-centred audit |\n"
  "| Continuous-outcome studies | 5 | Continuous prediction synthesis |\n"
  "| Other primary tasks | 11 | Imputation, clustering, causal, structural, and representation analyses |\n"
  "| Eligible reports entering study-family linkage | 246 | Report-level eligibility set before family linkage |\n"
  "| Additional/companion reports | 24 | Linked within represented publication families and not counted separately |\n"
  "| Reports not retrieved | 0 | No eligible report remained unretrieved after retrieval and linkage |\n"
  "| Development units | 203 | PROBAST+AI development-quality assessment |\n"
  "| Evaluation units | 243 | PROBAST+AI performance-evaluation risk-of-bias assessment |\n"
  "| Multi-year pooled studies | 180 | Combined-weight audit |\n"
  "| Explicit variable-importance studies | 126 | Importance-method and selection audit within classification studies |\n"
  f"| Codable variable-importance studies | {I_DOM['n_with_codable_variable_domains']} | Important-variable domain analysis |\n\n"
  "These denominators are not interchangeable. A study can contribute more than one model or evaluation unit.\n\n"
  + open(os.path.join(PROJ, "tools/EXTRACT_GUIDE.md"), encoding="utf-8").read())

cen = open(os.path.join(PROJ, "planning/CENSUS.md"), encoding="utf-8").read()
blk = cen[cen.index("<!-- AUTOGEN:census -->"):cen.index("<!-- /AUTOGEN:census -->")]
w("appendix4_search_strategy.md", "# Multimedia Appendix 4. Search Strategies and Record Counts\n\n"
  "Searches were run between September 3 and 5, 2026 with no date restriction.\n\n" + blk + "\n")

adj = sorted([r for r in R.values() if r["verdict"] == "INCLUDE_ADJACENT"], key=lambda r: (-(r.get("year") or 0), r["key"]))
L = [f"# Multimedia Appendix 5. Reports Using ML-Adjacent Methods Only (n={len(adj)})\n",
     "Inclusion was determined by analytic role, not by the name of a method. These reports used a classical "
     "clustering, latent-class/profile, principal-component/factor, penalised-regression, or association-rule "
     "method as the primary/final analytic engine without an additional eligible ML component. They are "
     "catalogued separately from the 222 full-report studies in the detailed synthesis.\n",
     "## Included clustering exceptions\n",
     "| Study | Clustering role | Additional eligible ML component | Why included |",
     "|---|---|---|---|",
     "| cho2019identification | Primary phenotype discovery | SVM assignment plus independent-population replication and cluster-specific prediction evaluation | Eligible supervised learning and evaluation were central to the analytic objective, not incidental preprocessing. |",
     "| choi2022dietary | K-means preprocessing of food names | fastText representation and LDA topic modelling | The primary pipeline transformed unstructured dietary text with representation learning and probabilistic topic modelling; classical clustering alone did not determine eligibility. |\n",
     "## ML-adjacent catalogue\n",
     "The method-role column makes explicit why superficially similar clustering terminology did not imply eligibility. "
     "The adjacent-method summary contains 28 conventional k-means/hierarchical-clustering reports and 16 separate "
     "latent-class/profile reports; these categories are mutually exclusive in this summary.\n",
     "| # | Year | Journal | Title | Method | Method role / boundary reason | DOI |", "|---:|---:|---|---|---|---|---|"]
for i, r in enumerate(adj, 1):
    d = E.get(r["key"], {})
    m = "; ".join(str(x) for x in (d.get("models") or []))[:58] or (d.get("task") or "")
    role = "Primary/final adjacent analysis; no additional eligible ML component central to the objective"
    L.append(f"| {i} | {r.get('year')} | {(r.get('journal') or '')[:36]} | {(r.get('title') or '')[:86]} | {m} | {role} | {r.get('doi') or ''} |")
w("appendix5_ml_adjacent.md", "\n".join(L) + "\n")

def g(d, k, n=70):
    v = d.get(k)
    if v is None: return ""
    if isinstance(v, list): v = "; ".join(str(x) for x in v)
    return re.sub(r"\s+", " ", str(v)).replace("|", "/")[:n]
inc = sorted([r for r in R.values() if r["verdict"] == "INCLUDE" and E.get(r["key"], {}).get("source") == "full_text"], key=lambda r: (-(r.get("year") or 0), r["key"]))
hdr = ["#","Year","Journal","Outcome domain","Task","Survey cycles","n","Data layers","Missing data",
       "Survey weights","Models compared","Best model","Validation","Performance","Interpretability","Source"]
L = [f"# Multimedia Appendix 6. Characteristics of Included Studies (n={len(inc)})\n",
     "All records were extracted from full reports. Empty cells indicate the item was not reported.\n",
     "| " + " | ".join(hdr) + " |", "|" + "---|" * len(hdr)]
for i, r in enumerate(inc, 1):
    d = E.get(r["key"], {})
    L.append("| " + " | ".join([str(i), str(r.get("year") or ""), (r.get("journal") or "")[:26],
        r.get("category") or "", g(d,"task",18), g(d,"knhanes_waves",30), g(d,"n_final",10),
        g(d,"variables",40), g(d,"missing_handling",34), g(d,"survey_weights",30), g(d,"models",58),
        g(d,"best_model",26), g(d,"validation",40), g(d,"metrics",44), g(d,"interpretability",26),
        "full text" if d.get("source") == "full_text" else "abstract"]) + " |")
w("appendix6_study_characteristics.md", "\n".join(L) + "\n")
print("  → manuscript/submission/appendices/")
