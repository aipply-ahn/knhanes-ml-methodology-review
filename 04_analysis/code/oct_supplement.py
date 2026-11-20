"""Supplementary material 1 of the ORIGINAL manuscript, rebuilt with the October-search data (author 2026-11-19: keep the
text, figures and tables, swap the numbers). Same sections and layout as manuscript/bmc_supplementary.tex (September):
Numbered in the order of first citation in the article (author 2026-11-21): Tables S1 (PRISMA 2020) and S2 (PRISMA-S);
S3 search strategies; S4 eligibility-boundary and study-family decisions (cited in 2.2); S5 verification protocol and coding
rules (2.3); S6 linear record of selection and coding (2.4); S7 health-focused studies outside the core cohort; S8 ten
illustrative studies; then Figures S1-S8 (legacy_supplement.py; S3 participants, S4 outcome and predictors).
No text copied from the reports is printed: study rows give coded categories, counts and bibliographic details only.
Output: manuscript/supplementary/oct/KNHANES_ML_review_Supplementary.tex (+ .pdf with xelatex)
Usage: oct_supplement.py"""
import collections, csv, json, os, re, shutil, subprocess, sys
HERE = os.path.dirname(os.path.abspath(__file__)); ROOT = os.path.dirname(os.path.dirname(HERE)); os.chdir(ROOT)
sys.path.insert(0, HERE)
import query as Q
OUT = "manuscript/supplementary/oct"; os.makedirs(f"{OUT}/figures", exist_ok=True)
SEPT = open("manuscript/bmc_supplementary.tex").read()
L = "results/oct_search/legacy_fig"


def macros(f):
    return {m.group(1): m.group(2) for m in re.finditer(r"\\newcommand\{\\(\w+)\}\{([^}]*)\}", open(f).read())}


K = {**macros("manuscript/oct_numbers.tex"), **macros("manuscript/legacy_numbers.tex")}
k = lambda n: K[n]
esc = lambda t: (str(t).replace("\\", "/").replace("&", "\\&").replace("%", "\\%").replace("_", "\\_").replace("#", "\\#")
                 .replace("$", "\\$").replace("{", "(").replace("}", ")").replace("~", "-").replace("^", ""))
brk = lambda t: esc(t).replace("/", "/¦").replace(";", ";¦").replace(",", ",¦")


def section(name, kind, body, landscape=True):
    head = f"\\phantomsection\n\\addcontentsline{{toc}}{{section}}{{{kind} {name}}}\n{{\\Large\\sffamily\\bfseries {kind} {name}}}\\par\\smallskip\n"
    s = "\\begingroup\n" + head + body + "\\endgroup\n"
    return ("\\begin{landscape}\n" + s + "\\end{landscape}\n" if landscape else s) + "\\clearpage\n"


def longtable(widths, header, rows, size="7.5", note=""):
    spec = "".join(f">{{\\RaggedRight\\arraybackslash}}p{{{w}cm}}" for w in widths)
    h = " & ".join(f"\\textbf{{{x}}}" for x in header) + " \\\\ \\midrule\n"
    body = "".join((r if isinstance(r, str) else " & ".join(r) + " \\\\\n") for r in rows)
    lead = float(size) * 1.18
    return (f"\\fontsize{{{size}}}{{{lead:.2f}}}\\selectfont\n\\begin{{longtable}}{{@{{}}{spec}@{{}}}}\n\\toprule\n{h}\\endfirsthead\n\\toprule\n{h}\\endhead\n"
            + body + "\\bottomrule\n\\end{longtable}\n" + f"{{\\footnotesize {note}\\par}}\n")


def grp(t, n):
    return f"\\addlinespace[3pt]\\multicolumn{{{n}}}{{l}}{{\\textbf{{{t}}}}} \\\\* \\addlinespace[2pt]\n"


def old_table(title):
    """rows of a September table (S1, S2) as lists of cells."""
    i = SEPT.index(title); j = SEPT.index("\\endhead", i) + len("\\endhead"); e = SEPT.index("\\bottomrule", j)
    return [r.strip() for r in SEPT[j:e].split("\\\\\n") if r.strip()]


def main():
    recs = json.load(open(f"{L}/records.json")); R = recs["records"]
    o = json.load(open(f"{L}/results/derived/practice_trends_112.json"))
    sel = json.load(open("results/oct_search/public/selection_summary.json"))
    meta = {r["record_id"]: r for r in csv.DictReader(open("results/oct_search/public/included_reports.csv"))}
    links = list(csv.DictReader(open("results/oct_search/public/report_study_links.csv")))
    cls = {r["record_id"]: r for r in csv.DictReader(open("results/oct_search/coding/analysis/study_classified.csv"))}
    der = {r["record_id"]: r for r in csv.DictReader(open("results/oct_search/coding/analysis/study_derived.csv"))}
    sys.argv = [sys.argv[0]]
    import legacy_figures as LF
    ids = [r for r in R if r not in recs["CORE"]] + sorted(recs["CORE"])
    lab = LF.first_author_labels(ids)  # 'Surname Year' (Crossref / OpenAlex / KCI bibliographic metadata, cached)
    F = collections.defaultdict(dict)
    for folder in ("coding_legacy", "coding_legacy3"):
        p = f"results/oct_search/{folder}/final_items.jsonl"
        for l in (open(p) if os.path.exists(p) else []):
            x = json.loads(l)
            if x.get("final"): F[x["item"]][x["record_id"]] = x["final"]
    M = collections.defaultdict(dict)
    for l in open("results/oct_search/coding/final_items_clean.jsonl"):
        x = json.loads(l)
        if x.get("final"): M[x["item"]][x["record_id"]] = x["final"]
    codes = lambda item, r: [c.split(":")[0].split("(")[0].strip() for v in ((F[item].get(r) or {}).get("values") or []) for c in re.split(r"\s*;\s*", re.sub(r"\([^)]*\)", "", str(v.get("value", "")))) if c.strip()]
    pv = lambda r, key: [x["value"] for x in R[r]["protocol_items"].get(key, [])]
    nS = lambda x: f"{int(x):,}"

    def years(r):
        ys = set()
        for v in (M["data_source.survey_cycles"].get(r) or {}).get("values") or []:
            if re.match(r"\s*NHANES", str(v.get("unit", ""))): continue
            t = str(v.get("value", ""))
            for a_, b_ in re.findall(r"((?:19|20)\d\d)\s*(?:[-–—~∼]|to|through)\s*((?:19|20)?\d\d)\b", t):
                a1, b1 = int(a_), int(b_) if len(b_) == 4 else int(a_[:2] + b_)
                if a1 <= b1: ys.update(range(a1, b1 + 1))
            ys.update(int(y) for y in re.findall(r"\b((?:19|20)\d\d)\b", t))
        ys = sorted(y for y in ys if 1998 <= y <= 2027)
        if not ys: return "years not reported"
        runs, s = [], ys[0]
        for a, b in zip(ys, ys[1:] + [None]):
            if b != a + 1: runs.append(f"{s}--{a}" if a > s else f"{a}"); s = b
        return ", ".join(runs)

    def n_an(r):
        m_ = re.search(r"\d[\d,]*", str(der.get(r, {}).get("n_analysed_max") or "").replace(",", ""))
        return f"n={int(float(m_.group(0))):,}" if m_ else "n not reported"
    ALG = {"boosting": "Boost", "random_forest": "RF", "logistic_regression": "LR", "decision_tree": "DT", "svm": "SVM", "neural_network": "NN", "other": "other"}
    alg = lambda r: ", ".join(dict.fromkeys(ALG.get(c, c) for c in codes("legacy.algorithms_fitted", r))) or "--"
    VAL = {"SPLIT": "split", "CV": "CV", "BOOT": "bootstrap", "APPARENT": "apparent", "TEMPORAL": "Temporal", "EXTERNAL": "Ext", "NONE_NR": "not reported"}
    internal = lambda r: ", ".join(VAL[v] for v in pv(r, "VAL02") if v in ("SPLIT", "CV", "BOOT", "APPARENT", "NONE_NR")) or "--"
    beyond = lambda r: ", ".join(VAL[v] for v in pv(r, "VAL02") if v in ("TEMPORAL", "EXTERNAL")) or "--"
    IMP = {"SHAP": "SHAP", "MODEL_NATIVE": "MN", "PERMUTATION": "Perm", "TREE_RULE": "tree rule", "COEFFICIENT_STATISTIC": "coef", "LIME": "LIME",
           "PDP": "PDP", "PERTURBATION_ABLATION": "ablation", "OTHER": "other"}
    imp = lambda r: (", ".join(IMP.get(v, v.lower().replace("_", " ")) for v in pv(r, "VI02") if v not in ("NA", "NR")) or "--") if "USED" in pv(r, "VI01") else "--"
    design = lambda r: ", ".join(t for kk, t in (("SUR06", "Wf"), ("SUR07", "We"), ("SUR10", "SP")) if "USED" in pv(r, kk)) or "--"
    CODE = {"public_repository": "Link", "in_supplement": "Suppl.", "on_request": "Request", "none_stated": "--"}
    code = lambda r: "Public" if "USED" in pv(r, "MOD15") else ("Request" if cls.get(r, {}).get("code") == "on_request" else "--")  # one definition, as in Table A1
    TOP = {t: t.replace("_", " ").capitalize() for t in ("METABOLIC_ENDOCRINE", "MENTAL_HEALTH", "CARDIOVASCULAR", "MUSCULOSKELETAL")}
    topic = {q["id"]: q["topic"].replace("_", " ").lower() for q in o["literature_map"]}
    parts = []

    # ---------------- S1 PRISMA 2020
    rows = old_table("Supplementary Table S1. Completed PRISMA 2020 checklist}\\par")
    fix = {"Describe any sensitivity analyses.": "Not performed", "Present results of sensitivity analyses.": "Not performed",
           "Report which materials are publicly available and where.": "Study-level dataset (Additional Data 1);¦ public repository (Data availability) with the queries,¦ criteria,¦ protocols,¦ prompts,¦ the record of every selection and coding round,¦ the field rules and the analysis code;¦ coded values held by the author."}
    loc = {"13a": "Sections 2.3 and 2.5;¦ Section 3.2", "13f": "Not performed", "20d": "Not performed",
           "16b": "Section 3.1;¦ Supplementary Table S4;¦ public selection records (decision and reasons for every report)",
           "19": "Additional Data 1 (study-level coded variables);¦ Supplementary Tables S7 and S8",
           "20b": "Section 3;¦ Figures 1--5;¦ Appendix Table A1;¦ Additional Data 1", "20c": "Sections 3.3,¦ 3.4 and 3.6;¦ Appendix Table A1;¦ Supplementary Figure S5",
           "27": fix["Report which materials are publicly available and where."],
           "24b": "Not registered;¦ selection and coding protocols and prompts in the public repository (Data availability);¦ coding rules in Supplementary Table S5;¦ the five steps of selection and coding in Supplementary Table S6",
           "10b": "Section 2.3;¦ Supplementary Table S5", "11": "Section 2.3;¦ Supplementary Table S5",
           "8": "Sections 2.2 and 2.4;¦ Supplementary Tables S4 and S6;¦ public repository (prompts and round records)", "9": "Sections 2.3 and 2.4;¦ Supplementary Tables S5 and S6;¦ public repository (prompts and round records)"}
    s1 = []
    for r in rows:
        c = r.split(" & "); it = next((i for i, x in enumerate(c) if re.fullmatch(r"\d+[a-f]?", x.strip(" &"))), None)
        if it is not None and c[it].strip(" &") in loc: c[-1] = loc[c[it].strip(" &")]
        s1.append(" & ".join(c) + " \\\\\n")
    parts.append(section("S1. Completed PRISMA 2020 checklist", "Supplementary Table", longtable([2.25, 1.13, 3.19, 11.27, 7.8], ["Section", "Item", "Checklist item", "Description", "Location"], s1, "7.2")))

    # ---------------- S2 PRISMA-S
    rows = old_table("Supplementary Table S2. Completed PRISMA-S search-reporting checklist}\\par")
    rep = {"5": "Not performed: the search relied on the databases and the KDCA publication list.",
           "4": "Complete: the full KDCA author-registered publication list was retrieved and the same terms applied to titles and keywords.",
           "7": "Complete: the KDCA publication list is identified separately (Figure 1).",
           "8": "Complete: the queries exactly as run, including the Korean and English KCI term set.",
           "13": "Complete: 2 November 2026 for every source.",
           "15": "Complete: DOI,¦ PMID and normalised-title linkage (Section 2.2) and study-family linkage (Supplementary Table S4) are distinguished.", "16": "Complete: DOI$\\rightarrow$PMID$\\rightarrow$normalised-title precedence;¦ the deduplication code is public with the selection records."}
    s2 = []
    for r in rows:
        c = r.split(" & ")
        if c[1].strip() in rep: c[4] = rep[c[1].strip()]
        if c[1].strip() == "15": c[3] = "Section 2.2;¦ Supplementary Table S4;¦ Figure 1"
        s2.append(" & ".join(c) + " \\\\\n")
    parts.append(section("S2. Completed PRISMA-S search-reporting checklist", "Supplementary Table", longtable([2.64, .88, 8.08, 4.83, 9.22], ["Section", "Item", "Concise requirement", "Reported location", "Status and review-specific detail"], s2,
                                                                                                         note="Requirement wording is paraphrased. --,¦ answer given in the last column.")))

    # ---------------- S3 search strategies
    idn = sel["identified"]
    kci_terms = "; ".join(Q.SURVEY_KO) + " (survey names) by " + "; ".join([t.rstrip("*") for t in Q.ML] + Q.ML_KO) + " (terms)"
    s3 = [[ "Europe PMC", "2026-11-02;¦ Europe PMC REST API (webservices/rest/search)", brk(Q.europepmc()), "None", f"{idn['europepmc']:,} records", "Survey names in any field;¦ terms in title,¦ abstract or keywords"],
           ["PubMed", "2026-11-02;¦ NCBI E-utilities (esearch,¦ efetch)", brk(Q.pubmed()), "None", f"{idn['pubmed']:,} records", "Title/¦abstract and author keywords"],
           ["OpenAlex", "2026-11-02;¦ Works API (filter title\\_abstract\\_keywords.search.exact)", brk(Q.openalex_filter()), "None", f"{idn['openalex']:,} records", "Exact matching (no stemming);¦ wildcards expanded to singular and plural"],
           ["Korean Citation Index", "2026-11-02;¦ KCI KEYALL web search", "KEYALL: survey name AND term,¦ for every pair: " + brk(kci_terms) + ". The same query was then applied to the KCI title,¦ abstract and keywords,¦ because the KCI search expands terms.", "None", f"{idn['kci']:,} records", "Korean script as executed"],
           ["KDCA publication list", "2026-11-02;¦ KNHANES publication list (knhanes.kdca.go.kr)", "Complete author-registered publication list;¦ the English and Korean terms above applied to titles and keywords.", "None", f"{idn['kdca']:,} records", "Other source (Figure 1)"],
           ["Total", "", "", "", f"{sel['identified_total']:,} records", f"{sel['duplicates_removed']:,} duplicates removed;¦ {sum(sel['removed_before_screening'].values())} removed before screening (theses,¦ reviews,¦ editorials,¦ errata,¦ protocols,¦ conference abstracts,¦ a withdrawn record);¦ {sel['records_screened']:,} records screened"]]
    parts.append(section("S3. Search strategies,¦ retrieval counts,¦ and unique contributions", "Supplementary Table",
                         longtable([2.1, 3.0, 11.0, 1.4, 2.4, 5.6], ["Source", "Search date and interface", "Exact search strategy", "Limits", "Retrieval", "Note"], s3, "6.6",
                                   "KCI,¦ Korean Citation Index;¦ KDCA,¦ Korea Disease Control and Prevention Agency. Queries are printed by tools/¦oct\\_search/¦query.py,¦ published with the selection records.")))

    # ---------------- S4 boundary and family decisions
    fam = collections.defaultdict(list)
    for l_ in links: fam[l_["study_id"]].append(l_)
    s4 = [grp("Reports of the same study (counted once)", 4)]
    for st, ls in sorted(fam.items()):
        if len(ls) < 2: continue
        rep_ = next(x["record_id"] for x in ls if x["role"] == "representative")
        for x in sorted(ls, key=lambda x: x["role"] != "representative"):
            s4.append([x["record_id"], "Representative report" if x["role"] == "representative" else f"Counted with {rep_}", brk(st),
                       brk(x.get("link_basis") or ("journal article of the study" if x["role"] == "representative" else "same study (same authors,¦ data and analysis)"))])
    s4.append(grp("Reports excluded at full text, by reason", 4))
    for code_, (n_, t) in {"F3": (k("oExclLearner"), "No supervised learner outside the regression family fitted to a health-related outcome"),
                           "F2": (k("oExclData"), "KNHANES data not analysed at participant level for the ML analysis"),
                           "F1": (k("oExclType"), "Not a research report with recoverable ML results"),
                           "RETRACTED": (k("oExclRetracted"), "Retracted report")}.items():
        s4.append([code_, f"Excluded ({n_} report{'' if str(n_) == '1' else 's'})", "Not applicable", t])
    s4.append(grp("Report not retrieved", 4))
    for r in sel["not_retrieved_ids"]: s4.append([r, "Not retrieved", "Not applicable", "Full text not obtainable through the library or the authors' public copies"])
    pos = {r: (codes("legacy.knhanes_position", r) or [""])[0].upper() for r in R}
    ext = sorted(r for r, p in pos.items() if p.startswith("EXTERNAL"))
    if ext:
        s4.append(grp("Included with KNHANES as the external evaluation dataset", 4))
        for r in ext: s4.append([r, "Included", "Not applicable", "Eligibility covers KNHANES use in model development or evaluation;¦ KNHANES is the external evaluation dataset."])
    crit = [["E1 Data", "Participant-level KNHANES data (any cycle) used to develop,¦ validate or evaluate a model,¦ including linked or merged data and KNHANES used only for external validation",
             "KNHANES cited or compared only;¦ published aggregate statistics only;¦ other surveys only (e.g.,¦ US NHANES)", "X1;¦ F2"],
            ["E2 Analysis", "A supervised model fitted to classify or estimate a designated outcome from predictors,¦ with at least one learner outside the regression family:¦ decision,¦ classification or regression trees (CART,¦ CHAID,¦ C4.5),¦ random forest,¦ boosting and other ensembles,¦ support vector machines,¦ k-nearest neighbours,¦ naive Bayes,¦ Bayesian networks,¦ neural networks or deep learning,¦ AutoML,¦ large language models. Causal ML counts only when such a learner is fitted to the outcome;¦ a large language model only when it is the model that classifies or estimates the outcome. Unsupervised steps followed by an eligible supervised learner qualify",
             "Regression-family methods only (linear,¦ logistic,¦ Cox,¦ Poisson,¦ GLM,¦ LASSO,¦ ridge,¦ elastic net,¦ GAM),¦ whether or not the authors call them machine learning;¦ unsupervised methods only (clustering,¦ latent class or profile,¦ association rules,¦ PCA or factor analysis);¦ propensity scores or effect estimates from regression models alone", "X2;¦ F3"],
            ["E3 Purpose", "A health-related outcome (disease or health state,¦ risk factor or biomarker,¦ health behaviour,¦ nutrition,¦ mental health,¦ quality of life,¦ health-care use),¦ or development or comparison of ML methods using KNHANES", "Neither", "X3;¦ F4"],
            ["E4 Report type", "An original research report:¦ journal article (including a research letter reporting an original analysis),¦ full conference paper,¦ chapter reporting an original analysis,¦ preprint", "Thesis;¦ conference abstract only;¦ review,¦ introductory or textbook chapter;¦ commentary,¦ editorial or letter on another publication;¦ protocol;¦ erratum", "X4;¦ F1"],
            ["E5 Language and date", "Any language;¦ published up to the search date (2 November 2026)", "--", "--"],
            ["Decision rules", "Screening:¦ FULL\\_TEXT unless exclusion is certain from the title and abstract (when in doubt,¦ full text). Full text:¦ INCLUDE,¦ or EXCLUDE only when the full text shows a criterion is not met;¦ reports without an obtainable full text are not assessed. Retracted reports are excluded (author's direction)",
             "Reports of the same study are counted once;¦ the journal article,¦ or without one the later version,¦ represents the study (part B)", "Order when several apply:¦ X4,¦ X1,¦ X2,¦ X3;¦ F1--F4"]]
    s4body = ("{\\bfseries A. Eligibility criteria,¦ fixed before screening and applied unchanged at full text}\\par\\smallskip\n"
              + longtable([3.0, 10.4, 9.6, 3.4], ["Criterion", "Eligible", "Not eligible", "Exclusion code (screening;¦ full text)"], crit, "8.0",
                          "The prompts of screening and full-text assessment insert these criteria verbatim (Supplementary Note S1).")
              + "\\bigskip{\\bfseries B. Boundary decisions and reports of the same study}\\par\\smallskip\n")
    parts.append(section("S4. Eligibility criteria,¦ boundary decisions and study families", "Supplementary Table", s4body +
                         longtable([2.2, 4.8, 2.4, 16.2], ["Report ID", "Decision", "Study", "Basis"], s4, "8.0",
                                   "OCT,¦ report identifier used in Additional Data 1 and the public selection records,¦ where every round's decisions and reasons are given for each record. The exclusion codes are those of the eligibility criteria.")))

    # ---------------- S5 other health-focused studies
    cat = {r: codes("legacy.study_category", r) for r in R}
    other = [r for r in recs["HEALTH"] if r not in recs["CORE"]]
    task = {r: (codes("legacy.task", r) or ["OTHER"])[0] for r in other}
    s5 = []
    for title, sel_ in (("Continuous- or ordered-outcome studies", lambda t: "CONT" in t.upper() or "ORDER" in t.upper()), ("Other task-specific health analyses", lambda t: not ("CONT" in t.upper() or "ORDER" in t.upper()))):
        rs = sorted((r for r in other if sel_(task[r])), key=lambda r: (-int(meta[r]["year"]), r))
        s5.append(grp(f"{title} (n=¦{len(rs)})", 10))
        for r in rs:
            s5.append([brk(lab[r]), brk({"cont": "continuous or ordered outcome", "other": "other ML analysis"}.get(task[r].lower(), task[r].replace("_", " ").lower())), brk(topic.get(r, "")), brk(years(r)) + ";¦ " + n_an(r), brk(alg(r)), brk(internal(r)), brk(beyond(r)), brk(imp(r)), brk(design(r)), brk(code(r))])
    parts.append(section(f"S7. The {len(other)} health-focused studies outside the core classific\\-ation cohort", "Supplementary Table",
                         longtable([3.0, 2.8, 3.0, 3.6, 3.2, 2.6, 1.8, 2.4, 1.7, 1.5], ["Study (first author, year)", "Task", "Health topic", "KNHANES years; n", "ML method", "Internal evaluation", "Beyond development data", "Importance", "Survey design", "Code"], s5, "6.8",
                                   "Abbreviations as in Supplementary Table S8;¦ --,¦ none or not reported. Categories are the coded values;¦ outcome definitions are in the reports.")))

    # ---------------- Figures S1-S8 (legacy_supplement.py)
    for f in os.listdir(f"{L}/supp"): shutil.copy(f"{L}/supp/{f}", f"{OUT}/figures/{f}")
    core = [R[r] for r in recs["CORE"]]
    units = lambda key: sum(len([u for u in d["protocol_items"].get("U:" + key, []) if u["value"] != "NA"]) for d in core)
    pc = collections.Counter(pos[r] for r in R)
    ynr = sum(years(r) == "years not reported" for r in recs["CORE"])
    caps = [("S1. KNHANES as a methods testbed", "Supplementary_Figure_S01_Methods_testbed",
             f"(A) Contribution of the {k('kMethod')} method-focused studies;¦ teal,¦ compared with existing methods. (B) Analysis stages addressed,¦ which overlap. (C) How the method was evaluated;¦ teal,¦ beyond a single KNHANES application."),
            ("S2. Role of KNHANES and survey years analysed", "Supplementary_Figure_S02_Study_characteristics",
             f"(A) Role of KNHANES in the {k('kAll')} studies;¦ hatched,¦ unclear. (B) Survey years analysed by the {k('kCore')} core studies;¦ a study counts once for each year. {ynr} studies named no single survey year (some named only the survey cycle)."),
            ("S3. Participants and sample size", "Supplementary_Figure_S04_Participants_and_sample_size",
             f"{k('kCore')} core studies. (A) Participant restrictions,¦ which overlap. (B) Participant-selection items reported;¦ the last row requires all five."),
            ("S4. Outcome and predictor construction", "Supplementary_Figure_S03_Outcome_and_predictor_construction",
             f"{k('kCore')} core studies. (A) Outcome structure. (B) Outcome and predictor set rebuildable from the report,¦ and model choice,¦ tuning and threshold made without the final evaluation data (all three in the last row)."),
            ("S5. Differences by publication period", "Supplementary_Figure_S05_Differences_by_publication_period",
             f"Core studies by publication period (n =¦ {k('kPerNA')},¦ {k('kPerNB')},¦ {k('kPerNC')} and {k('kPerND')}). (A) Algorithms compared and families fitted;¦ teal,¦ boosting. (B) Paired model comparison. (C) Studies producing a ranking in the first and last period,¦ in the four largest topics. Lines are visual guides,¦ not fitted trends."),
            ("S6. Algorithms,¦ tuning,¦ evaluation designs and performance measures", "Supplementary_Figure_S06_Algorithms_tuning_evaluation_and_measures",
             f"{k('kCore')} core studies;¦ categories overlap except in (B). (A) Algorithm families. (B) Hyperpara\\-meter tuning. (C) Evaluation designs;¦ teal,¦ beyond the development data. (D) Performance measures. (E) Importance methods in the {k('kRanking')} studies with a ranking;¦ teal,¦ SHAP."),
            ("S7. Agreement between pairs of rankings", "Supplementary_Figure_S07_Agreement_between_rankings",
             f"(A) Overlap of the variable domains named by pairs of the {k('kRanking')} studies with a ranking (Jaccard index;¦ median and interquartile range;¦ open points exclude age,¦ sex and body size). Pairs share studies and are not independent. (B) Rows of Figure 4D clustered by their variable profiles (average linkage)."),
            ("S8. Reporting completeness and PROBAST+AI", "Supplementary_Figure_S08_Reporting_completeness_and_PROBAST_AI",
             f"{k('kCore')} core studies. (A) Eight of the 19 TRIPOD+AI-derived reporting elements. (B) PROBAST+AI judgements per model unit ({units('PD_OVERALL')} developments,¦ {units('PE_OVERALL')} evaluations);¦ dark grey,¦ low quality or high risk. Each bar is 100\\% of the units judged for that row: the overall rows include every development or evaluation unit with an overall judgement;¦ a domain row includes the evaluation units with both an overall and a domain judgement,¦ so units without a judgement for that domain (not applicable or not assessed) are left out and the domain totals can be smaller than the overall total.")]
    for t, f, c in caps:
        parts.append(section(t, "Supplementary Figure", f"\\begin{{center}}\\includegraphics[width=\\textwidth,height=0.78\\textheight,keepaspectratio]{{figures/{f}.pdf}}\\end{{center}}{c}\n", landscape=False))

    # ---------------- S6 verification protocol
    nH = int(k("kAll")) - int(k("kMethod"))
    s6 = [grp("A. Procedure and response states", 4),
          ["Assessors", "Who made and checked each decision?", "All stages", "Two AI systems,¦ Anthropic Claude (claude-opus-5-5) and OpenAI Codex (gpt-6.1-sol),¦ each call isolated without tools or memory;¦ every decision cites the text it relied on. The author set the rules and decided the cases the rules left open."],
          ["Screening", "How were titles and abstracts screened?", f"{k('oScreened')} records", f"Both systems independently (step 1);¦ disagreements through up to three consensus rounds in which each saw the other's decision and reason (step 2);¦ as directed by the author,¦ agreed exclusions re-examined once by both,¦ with up to three further rounds when discordant (steps 3 and 4);¦ records still in disagreement decided by the author ({k('oScreenedAuthor')},¦ step 5)."],
          ["Eligibility", "How were full texts assessed?", f"{k('oAssessed')} reports", f"As for screening,¦ against the written eligibility criteria;¦ author decision for {k('oEligAuthor')} report."],
          ["Source text", "What did the coders read?", f"{k('oReports')} reports", "Each report and its supplements converted into a text in which every paragraph,¦ table cell and figure element carries an identifier;¦ tables and figures transcribed element by element by both systems and compared."],
          ["Evidence", "What supports a coded value?", "All items", "The identifiers of the supporting text;¦ values are never inferred from information the report does not give."],
          ["Response states", "How are missing values recorded?", "All items", "Reported: stated in the report. Not reported: the item applies but the report does not state it. Not applicable: the item has no object in the study. Unclear: the report touches it but the value cannot be fixed. A stated conflict within a report is recorded as an inconsistency."],
          ["Units", "At what level is an item coded?", "All items", "Study items once;¦ outcome,¦ model,¦ development and evaluation items for each unit named in the report."],
          ["Settling codings", "How were differences between the two systems settled?", f"{k('kVCoded')} item codings", f"Five steps (Supplementary Table S6). 1:¦ agreed codings final ({k('kVAgree')}). 2:¦ each system chose the correct coding of the two,¦ then saw the other's choice ({k('kVConsensus')}). 3:¦ the author directed that the rest be settled by rules,¦ not case by case. 4:¦ cross-checks under these directions ({k('kVStepFour')}:¦ {k('kVRule')} by fixed rules for immaterial,¦ form,¦ one-sided inconsistency and rule-reading differences,¦ the rest by common rules agreed by both systems for {k('kVFieldAgreedItems')} items). 5:¦ rules for the {k('kVFieldDecidedItems')} items without agreement taken from review comments accepted by the author or from the suggested rule,¦ as directed,¦ with a fallback ({k('kVStepFive')},¦ of which {k('kVFallback')} by the fallback and {k('kVDecision')} pilot codings by review comments accepted by the author)."],
          "\\noalign{\\penalty-100}\n", grp("B. Coding rules that produce the reported results", 4)]
    B = [("Orientation", "Is the study health-focused or method-focused?", f"All {k('kAll')} studies", "Judged from the objective,¦ principal analysis,¦ main results and conclusion together,¦ not from the algorithm or title. Health-focused: answers a health question. Method-focused: develops,¦ improves or compares an analytic method."),
         ("Analytic task", "What is the primary analytic task?", f"All {k('kAll')} studies", f"Set by the fitted outcome scale and evaluation:¦ classific\\-ation,¦ continuous or ordered estimation,¦ or another task. Health-focused classific\\-ation studies form the core cohort ({k('kCore')})."),
         ("Health topic", "What is the primary health topic?", f"{nH} health-focused", "One of 18 categories,¦ assigned by the primary fitted outcome rather than by predictors,¦ exposures or a disease-restricted sample."),
         ("KNHANES role", "How was KNHANES used?", f"All {k('kAll')} studies", "Sole primary dataset,¦ one of several primary datasets,¦ external evaluation dataset,¦ application or test dataset,¦ or unclear."),
         ("Method contribution and evaluation", "What did a method-focused study contribute,¦ and how was it evaluated?", f"{k('kMethod')} method-focused", "Develop or improve a method,¦ or compare existing methods;¦ analysis stages addressed;¦ evaluation by simulation with an empirical application,¦ in an independent population,¦ against a comparator on KNHANES,¦ or by a single application."),
         ("Participant selection", "Could a reader follow participant selection?", f"{k('kCore')} core", "Five items: source population size,¦ eligibility criteria,¦ numbers excluded,¦ reasons for exclusion,¦ final analytic sample;¦ every step requires all five."),
         ("Outcome and predictor set", "Can the outcome and the predictor set be rebuilt from the report?", f"{k('kCore')} core", "Full: every element needed to rebuild it is stated (target,¦ source,¦ timing and cut-off rules;¦ candidate and final inputs with definitions). Partial: identifiable but a necessary detail missing. Insufficient: a label or count only."),
         ("Tuning and evaluation", "Was tuning kept apart from the final evaluation?", f"{k('kCore')} core", "Kept apart: tuning,¦ model selection and the decision threshold chosen without the final evaluation data,¦ or there was no tuning;¦ otherwise not shown or evaluation data involved."),
         ("Data-dependent steps", "When were data-dependent steps done?", f"{k('kCore')} core", "Missing-value handling,¦ scaling,¦ feature selection and class rebalancing: within the training data,¦ before the split,¦ timing unclear,¦ or not applied."),
         ("Evaluation design", "How was the model evaluated?", f"{k('kCore')} core", "Apparent,¦ single split,¦ cross-validation,¦ bootstrap,¦ later survey period,¦ external dataset (nonexclusive). Validation beyond the development data means a later survey period or an external dataset."),
         ("Calibration and threshold", "Were calibration and a decision threshold reported?", f"{k('kCore')} core", "Calibration: a slope,¦ intercept,¦ plot or other agreement measure beyond the Brier score. Threshold: a stated threshold or selection method."),
         ("Variable importance", "Was a model-based importance ranking produced,¦ and how?", f"{k('kCore')} core", "An explicit model-based importance or explanation output (SHAP,¦ model-native,¦ permutation,¦ coefficient,¦ tree or rule,¦ perturbation,¦ LIME,¦ partial dependence,¦ other);¦ coefficients alone,¦ a tree diagram or the split variables alone do not qualify;¦ the variables named as most important recorded as reported and assigned to domains."),
         ("Ranking stability and use", "Was the ranking checked or used further?", "Studies producing a ranking", "Stability: importance or the selected variables compared across resamples,¦ survey cycles or subgroups. Use: a reduced predictor set,¦ a subsequent statistical analysis."),
         ("Survey design", "Were survey weights and design used?", "All studies", "Survey weights mentioned;¦ used in model fitting;¦ used in performance evaluation;¦ combined across pooled years;¦ strata or primary sampling units in variance estimation. Class or loss weights do not qualify."),
         ("Final model and code", "Was the final model fully specified,¦ and was code provided?", f"{k('kCore')} core", "Full specification: inputs,¦ preprocessing,¦ final parameters or a saved model and the threshold where used. Code: public repository,¦ supplement,¦ on request,¦ or none stated."),
         ("Reporting elements and PROBAST+AI", "How completely were the 19 TRIPOD+AI-derived elements reported,¦ and what were the PROBAST+AI judgements?", f"{k('kCore')} core", "Each element complete,¦ partial or not reported. PROBAST+AI signalling questions and domain judgements for each model-development unit (quality) and each performance-evaluation unit (risk of bias)."),
         ("Core reporting checklist", "Did the report meet each of the 43 core items (C01--C43,¦ Table 1)?", f"{k('kCore')} core", "Met,¦ not met or not applicable against the item criterion,¦ coded by both systems for the representative report of each core study. Items judge reporting,¦ not practice.")]
    s6 += [list(b) for b in B]
    parts.append(section("S5. Selection and coding procedure and coding rules", "Supplementary Table",
                         longtable([3.3, 5.1, 3.5, 13.7], ["Item", "Question", "Applies to", "Decision rule"], s6, "8.0",
                                   "The coding items (CHARMS-based,¦ v3.1.3,¦ with the additional items for the figures),¦ the general rules and the settled field rules are in Additional Data 1 (sheets Items and Field\\_rules).")))

    # ---------------- S7 recorded verification results
    def rounds(f):
        c = collections.Counter()
        for l in open(f"results/oct_search/public/{f}_rounds_public.jsonl"):
            x = json.loads(l); Rr = x["rounds"]; c["n"] += 1; c["agree1"] += Rr[0]["consensus"]["status"] == "AGREED"
            c["cons"] += any(r_["stage"] == "consensus" for r_ in Rr); c["chal"] += any(r_["stage"] == "challenge" for r_ in Rr)
            c["chal_changed"] += any(r_["stage"] == "challenge_consensus" for r_ in Rr); c["open"] += Rr[-1]["consensus"]["status"] != "AGREED"
        return c
    sc, ec = rounds("screening"), rounds("eligibility")
    def how(files):
        c = collections.Counter()
        for f in files:
            for l in (open(f) if os.path.exists(f) else []):
                h = json.loads(l).get("how") or ""
                c["agree" if h.startswith("agree") else "consensus" if h.startswith("consensus") else "field" if h.startswith(("field_rule", "rule_fix")) else
                  "decision" if h.startswith("decision") else "rule"] += 1
        return c
    hm = how(["results/oct_search/coding/final_items_clean.jsonl"])
    hl = how([f"results/oct_search/{d}/final_items.jsonl" for d in ("coding_legacy", "coding_legacy2", "coding_legacy3")])
    fmt = lambda c: f"{sum(c.values()):,} codings: {c['agree']:,} agreed,¦ {c['consensus']:,} by consensus,¦ {c['rule']:,} by fixed rules,¦ {c['field']:,} by field rules" + (f",¦ {c['decision']} pilot decisions" if c["decision"] else "")
    # linear record: the five steps for selection and coding (counts from the public selection records and the
    # recorded settlement routes; field rules agreed by both systems are step 4, rules for fields without agreement step 5)
    def sel_steps(f):
        c = collections.Counter()
        for l in open(f"results/oct_search/public/{f}_rounds_public.jsonl"):
            x = json.loads(l); Rr = x["rounds"]; fd = str(x["final_decision"]); c["n"] += 1
            c["s1"] += Rr[0]["consensus"]["status"] == "AGREED"
            cons = [r_ for r_ in Rr if r_["stage"] == "consensus"]
            c["s2_in"] += bool(cons); c["s2_ok"] += bool(cons) and cons[-1]["consensus"]["status"] == "AGREED"
            ch = [r_ for r_ in Rr if r_["stage"] == "challenge"]; cc = [r_ for r_ in Rr if r_["stage"] == "challenge_consensus"]
            c["s4_in"] += bool(ch); c["s4_kept"] += bool(ch) and ch[0]["consensus"]["status"] == "AGREED" and "EXCL" in str(ch[0]["consensus"].get("decision"))
            c["s4_open"] += bool(ch) and not (ch[0]["consensus"]["status"] == "AGREED" and "EXCL" in str(ch[0]["consensus"].get("decision")))
            c["s4_back"] += bool(ch) and not fd.startswith("AUTHOR") and fd not in ("EXCLUDE",)
            c["s5"] += fd.startswith("AUTHOR:")
        return c
    sc, ec = sel_steps("screening"), sel_steps("eligibility")
    fst = {}
    for d in ("coding", "coding_legacy", "coding_legacy2", "coding_legacy3"):
        p_ = f"results/oct_search/{d}/field_rules_decided.json"
        if os.path.exists(p_): fst.update({i_: v_["status"] for i_, v_ in json.load(open(p_)).items()})
    def cod_steps(files):
        c = collections.Counter(); ag, dc = set(), set()
        for f in files:
            for l in (open(f) if os.path.exists(f) else []):
                r_ = json.loads(l); h = r_.get("how") or ""; c["n"] += 1; a_ = str(fst.get(r_["item"])).startswith("agreed")
                if h == "agree_r1": c["s1"] += 1
                elif h.startswith("consensus"): c["s2"] += 1
                elif h.startswith(("rule_not_material", "verify_inconsistency", "triage", "rule_blind")): c["s4"] += 1; c["s4_fixed"] += 1
                elif h.startswith("field_rule") and a_: c["s4"] += 1; ag.add(r_["item"])
                else:
                    c["s5"] += 1; c["s5_fallback"] += h in ("rule_fix_side", "rule_fix_unclear"); c["s5_pilot"] += h.startswith("decision")
                    if h.startswith(("field_rule", "rule_fix")) and not a_: dc.add(r_["item"])
        c["items_agreed"], c["items_decided"] = len(ag), len(dc); return c
    cm = cod_steps(["results/oct_search/coding/final_items_clean.jsonl"])
    cl = cod_steps([f"results/oct_search/{d}/final_items.jsonl" for d in ("coding_legacy", "coding_legacy2", "coding_legacy3")])
    sel_dir = "Every exclusion agreed by both systems re-examined once by both;¦ publication-type rules and deduplication exceptions added as protocol amendments;¦ retracted reports excluded"
    cod_dir = "Remaining differences settled by rules,¦ not case by case:¦ immaterial differences,¦ differences of form,¦ an inconsistency flagged by one system only and differences in reading a rule by fixed rules;¦ the rest by one common rule per item,¦ cross-checked in up to three rounds"
    def c4(c): return f"{c['s4']:,} settled:¦ {c['s4_fixed']:,} by the fixed rules,¦ {c['s4'] - c['s4_fixed']:,} by rules agreed for {c['items_agreed']} items"
    def c5(c): return (f"{c['s5']:,} settled by the rules set for {c['items_decided']} items without an agreed rule (review comments accepted by the author or the suggested rule,¦ as directed) and by the fallback"
                       + (f",¦ {c['s5_fallback']} of them by the fallback" if c["s5_fallback"] else "") + (f";¦ {c['s5_pilot']} pilot codings by review comments accepted by the author" if c["s5_pilot"] else ""))
    s7 = [["Scope", f"{sc['n']:,} records", f"{ec['n']:,} reports", f"{cm['n']:,} codings ({k('oItemsPerReport')} items,¦ {k('oReports')} reports)", f"{cl['n']:,} codings (additional items,¦ {k('kAll')} representative reports)"],
          ["1. Independent assessment", f"{sc['s1']:,} agreed", f"{ec['s1']:,} agreed", f"{cm['s1']:,} agreed", f"{cl['s1']:,} agreed"],
          ["2. Cross-review rounds", f"{sc['s2_in']} discordant;¦ up to three rounds;¦ {sc['s2_ok']} agreed", f"{ec['s2_in']} discordant;¦ up to three rounds;¦ {ec['s2_ok']} agreed",
           f"Two rounds (choice,¦ then choice after seeing the other's);¦ {cm['s2']:,} settled", f"As for the CHARMS-based items;¦ {cl['s2']:,} settled"],
          ["3. Author's directions (rules,¦ no case decisions)", sel_dir, sel_dir, cod_dir, cod_dir],
          ["4. Cross-checks under the directions", f"{sc['s4_in']} agreed exclusions re-examined;¦ {sc['s4_kept']} kept,¦ {sc['s4_open']} reopened (up to three rounds)",
           f"{ec['s4_in']} agreed exclusions re-examined;¦ {ec['s4_kept']} kept,¦ {ec['s4_open']} reopened (up to three rounds)", c4(cm), c4(cl)],
          ["5. Decision", f"{sc['s5']} decided by the author", f"{ec['s5']} decided by the author;¦ 1 retracted report excluded under the author's direction (step 3)", c5(cm), c5(cl)],
          ["Prompts (Supplementary Note S1)", "Step 1:¦ screening\\_round1;¦ steps 2 and 4:¦ screening\\_round\\_n;¦ step 4:¦ screening\\_challenge",
           "Step 1:¦ eligibility\\_round1;¦ steps 2 and 4:¦ eligibility\\_round\\_n;¦ step 4:¦ eligibility\\_challenge",
           "Step 1:¦ step1\\_independent\\_coding,¦ step1\\_performance\\_rows;¦ step 2:¦ step2\\_cross\\_review;¦ step 4:¦ step4\\_* (materiality,¦ inconsistency,¦ form or rule,¦ blind rule check,¦ field rule rounds 1--3 and application);¦ step 5:¦ step5\\_*", "As for the CHARMS-based items"],
          ["Public record", "02\\_¦selection/¦screening\\_¦rounds.jsonl", "02\\_¦selection/¦eligibility\\_¦rounds.jsonl", "03\\_¦coding/¦coding\\_¦rounds.jsonl (run charms);¦ field\\_¦rules.jsonl", "03\\_¦coding/¦coding\\_¦rounds.jsonl (runs additional\\_¦1--3);¦ field\\_¦rules.jsonl"]]
    tot = cm["n"] + cl["n"]; pc_ = lambda x: f"{100 * x / tot:.1f}"
    s1_, s2_, s4_, s5_ = cm["s1"] + cl["s1"], cm["s2"] + cl["s2"], cm["s4"] + cl["s4"], cm["s5"] + cl["s5"]
    summ = [["Independent agreement (step 1)", f"{s1_:,}", pc_(s1_), "Both systems gave the same coding"],
            ["Cross-review (step 2)", f"{s2_:,}", pc_(s2_), "Same choice of coding in the second or third round"],
            ["Rule-based cross-checks (step 4)", f"{s4_:,}", pc_(s4_), f"Fixed rules ({cm['s4_fixed'] + cl['s4_fixed']:,}) or a common item rule agreed by both systems ({s4_ - cm['s4_fixed'] - cl['s4_fixed']:,})"],
            ["Final resolution (step 5)", f"{s5_:,}", pc_(s5_), f"Rules for items without an agreed rule,¦ set under the author's direction;¦ fallback ({cm['s5_fallback'] + cl['s5_fallback']});¦ pilot codings decided by the author on accepted review comments ({cm['s5_pilot'] + cl['s5_pilot']})"],
            ["Total", f"{tot:,}", "100.0", "Step 3 gives directions and settles no coding by itself"]]
    s6sum = ("\\bigskip{\\bfseries Resolution of all item codings}\\par\\smallskip\n"
             + longtable([5.6, 2.2, 1.6, 16.6], ["Pathway", "Codings", "\\%", "What settled the coding"], summ, "8.0", ""))
    parts.append(section("S6. Linear record of selection and coding", "Supplementary Table",
                         longtable([3.6, 4.6, 4.6, 6.6, 6.6], ["Step", "Screening", "Full-text eligibility", "Coding:¦ CHARMS-based items", "Coding:¦ additional items"], s7, "8.0",
                                   f"Counts from the public round records. A coding is one item for one report;¦ units within a report (models,¦ evaluations) are part of the coding. Of {k('kVCoded')} codings,¦ {k('kVAgreePct')}\\% agreed at once and {k('kVOpen')} were left open. Prompts for every step are in Supplementary Note S1 and in the repository folders 02\\_selection/prompts and 03\\_coding/prompts;¦ the repository README describes each file.") + s6sum))

    # ---------------- S8 ten illustrative studies
    P = lambda y: 0 if y <= 2019 else 1 if y <= 2022 else 2 if y <= 2024 else 3
    pick = [r for p_ in range(4) for r in sorted(x for x in recs["CORE"] if P(int(meta[x]["year"])) == p_)[:2]]
    pick += sorted(other)[:1] + sorted(recs["METHOD"])[:1]
    vps = o["rankings_named_112"]["variables_per_study"]
    s8 = []
    for title, rs in (("Core health-focused classific\\-ation studies, two per period (n=¦" + k("kCore") + ")", pick[:8]),
                      (f"Other health-focused studies (n=¦{len(other)})", pick[8:9]), (f"Method-focused studies (n=¦{k('kMethod')})", pick[9:])):
        s8.append(grp(title, 10))
        for r in rs:
            v = vps.get(r) or []
            s8.append([r, brk(lab[r]), brk(meta[r]["doi"] or "no DOI"), brk(topic.get(r, "") or (codes("legacy.study_category", r) or [""])[0].split(":")[-1].strip().replace("_", " ")),
                       brk(years(r)) + ";¦ " + n_an(r).replace("n=", ""), brk(alg(r)), brk(beyond(r)), brk(imp(r)), brk(", ".join(v[:5]) + (" ..." if len(v) > 5 else "") if v else "--"), brk(design(r)) + ";¦ " + brk(code(r))])
    parts.append(section("S8. Character\\-istics of ten illustrative included studies", "Supplementary Table",
                         longtable([1.5, 2.2, 3.4, 3.0, 2.7, 2.6, 1.3, 1.9, 5.6, 1.8], ["ID", "Study", "DOI", "Health topic", "Survey years; n", "Algorithms", "Valid.", "Importance", "Variables named as most important (domains)", "Design; code"], s8, "7.0",
                                   "Lowest study IDs in each stratum: two core studies per period,¦ one other health-focused and one method-focused study;¦ all studies are in Additional Data 1. --,¦ not reported or not done;¦ variables as domains,¦ up to five. RF,¦ random forest;¦ LR,¦ logistic regression;¦ Boost,¦ gradient boosting (XGBoost,¦ LightGBM and others);¦ DT,¦ decision tree;¦ SVM,¦ support-vector machine;¦ NN,¦ neural network;¦ split,¦ single train--test split;¦ CV,¦ cross-validation;¦ Ext,¦ external dataset;¦ Temporal,¦ later survey period;¦ MN,¦ model-native importance;¦ Perm,¦ permutation importance;¦ coef,¦ coefficient or statistic;¦ Wf and We,¦ survey weights in fitting and in evaluation;¦ SP,¦ strata or PSUs;¦ Public,¦ analysis code in a public repository or supplementary file;¦ Request,¦ code on request.")))

    pre = SEPT[:SEPT.index("\\begin{landscape}")]
    # ---------------- Note S1: prompt templates of every step (verbatim, from the public repository copy)
    G = "results/oct_search/github_repo"
    PRM = [("Study selection", [
               ("02_selection/prompts/screening_round1.md", "Step 1. Title and abstract screening, each system independently"),
               ("02_selection/prompts/screening_round_n.md", "Steps 2 and 4. Consensus round:¦ each system sees its previous decision and the other's decision,¦ evidence and reason"),
               ("02_selection/prompts/screening_challenge.md", "Step 4. Re-examination of an exclusion agreed by both systems (author's direction at step 3)"),
               ("02_selection/prompts/eligibility_round1.md", "Step 1. Full-text eligibility,¦ each system independently"),
               ("02_selection/prompts/eligibility_round_n.md", "Steps 2 and 4. Full-text consensus round"),
               ("02_selection/prompts/eligibility_challenge.md", "Step 4. Full-text re-examination of an agreed exclusion")]),
           ("Source text for coding (before step 1)", [
               ("03_coding/prompts/source_text_conversion.txt", "Conversion of a report into a text in which every paragraph,¦ table cell and figure element carries an identifier"),
               ("03_coding/prompts/table_figure_transcription_rules.txt", "Rules for transcribing tables and figures element by element"),
               ("03_coding/prompts/table_figure_transcription.txt", "Transcription of one table or figure,¦ each system independently"),
               ("03_coding/prompts/table_figure_transcription_compare.txt", "Comparison of the two transcriptions")]),
           ("Data coding", [
               ("03_coding/prompts/step1_independent_coding.txt", "Step 1. Independent coding of the items of one item group"),
               ("03_coding/prompts/step1_performance_rows.txt", "Step 1. Performance rows (model,¦ outcome,¦ dataset,¦ metric,¦ value)"),
               ("03_coding/prompts/step2_cross_review.txt", "Step 2. Choice between the two codings (A,¦ B,¦ UNION,¦ NEITHER);¦ in the next round each system also sees the other's choice"),
               ("03_coding/prompts/step4_materiality.txt", "Step 4. Is the difference material?"),
               ("03_coding/prompts/step4_inconsistency_check.txt", "Step 4. Does the report contradict itself where one coding flags an inconsistency?"),
               ("03_coding/prompts/step4_form_rule_substance.txt", "Step 4. Is the difference one of form,¦ of reading a rule,¦ or of substance?"),
               ("03_coding/prompts/step4_blind_rule_check.txt", "Step 4. Which anonymised coding follows the rules?"),
               ("03_coding/prompts/step4_field_rule_round1.txt", "Step 4. Common rule for an item,¦ round 1:¦ causes of disagreement and one minimal rule"),
               ("03_coding/prompts/step4_field_rule_round2.txt", "Step 4. Common rule,¦ round 2:¦ choose between the two proposed rules or revise"),
               ("03_coding/prompts/step4_field_rule_round3.txt", "Step 4. Common rule,¦ round 3:¦ test both rules on other open cases"),
               ("03_coding/prompts/step4_field_rule_application.txt", "Step 4. Judging each coding under the agreed rule"),
               ("03_coding/prompts/step5_field_rule_writing.txt", "Step 5. Writing the rule for an item without agreement from the decision"),
               ("03_coding/prompts/step5_field_rule_check.txt", "Step 5. Checking the written rule"),
               ("03_coding/prompts/step5_coding_under_rule.txt", "Step 5. Writing the coding under the rule"),
               ("03_coding/prompts/step5_coding_under_rule_check.txt", "Step 5. Checking the coding written under the rule")]),
           ("After coding", [
               ("03_coding/prompts/after_shorten_long_values.txt", "Short form of long coded values for Additional Data 1"),
               ("03_coding/prompts/after_shorten_long_values_check.txt", "Check of the short form against the full value"),
               ("03_coding/prompts/analysis_study_classification.txt", "Study-level categories not settled by keyword rules (code availability,¦ online tool,¦ outcome domain,¦ purpose)")])]
    def _prompt_text(f):
        s = open(f"{G}/{f}").read()
        if f.endswith(".txt"):
            s = s.split("\n", 1)[1].strip()
            s = re.sub(r'^[rfbRFB]*"""', "", s); s = re.sub(r'"""\s*$', "", s)
        return s.strip("\n")
    nb = ["Prompt templates of every step,¦ verbatim. Both systems received the same prompt in isolated calls without tools or earlier conversation (Anthropic Claude claude-opus-5-5,¦ OpenAI Codex gpt-6.1-sol). Words in braces are filled for each call:¦ the eligibility criteria (Supplementary Table S4),¦ the item definitions and general coding rules,¦ the records or the report text with its identifiers,¦ and,¦ in later rounds,¦ the earlier answers. Item definitions,¦ coding rules and these files are in the public repository (Data availability).\\par\\medskip\n"]
    for g_, lst in PRM:
        nb.append(f"{{\\large\\sffamily\\bfseries {g_}}}\\par\\smallskip\n")
        for f, d in lst:
            nb.append(f"\\needspace{{6\\baselineskip}}{{\\bfseries {d}}}\\par{{\\footnotesize\\texttt{{{f.replace('_', '\\_')}}}}}\\par\n"
                      "\\begin{Verbatim}[breaklines,breakanywhere,fontsize=\\scriptsize,frame=single,framesep=2pt]\n" + _prompt_text(f) + "\n\\end{Verbatim}\n\\medskip\n")
    parts.append(section("S1. Prompts of every step", "Supplementary Note", "".join(nb), landscape=False))

    def _key(p_):  # tables S1-S8 first, then figures S1-S8, each in number order (= order of first citation in the article)
        m_ = re.search(r"Supplementary (Table|Note|Figure) S(\d+)\.", p_)
        return ({"Table": 0, "Note": 1, "Figure": 2}[m_.group(1)], int(m_.group(2)))
    parts.sort(key=_key)
    pre = pre.replace("\\begin{document}", "\\usepackage{fvextra}\n\\setmonofont{DejaVu Sans Mono}[Scale=0.92]\n\\begin{document}", 1)
    tex = (pre + "".join(parts) + "\\end{document}\n").replace("¦", "\\allowbreak{}")
    open(f"{OUT}/KNHANES_ML_review_Supplementary.tex", "w").write(tex)
    env = dict(os.environ, PATH=os.path.expanduser("~/knhanes_build_env/bin") + ":" + os.environ["PATH"])
    for _ in range(2):
        p = subprocess.run(["xelatex", "-interaction=nonstopmode", "-halt-on-error", "KNHANES_ML_review_Supplementary.tex"], cwd=OUT, capture_output=True, text=True, env=env)
    print("xelatex", p.returncode, p.stdout[-600:] if p.returncode else "ok", f"{OUT}/KNHANES_ML_review_Supplementary.pdf")


if __name__ == "__main__":
    main()
