"""search inputs for the ORIGINAL manuscript figures (author: "keep the figures of the original manuscript ... and change only the numbers").
Builds, from the coding (v3.1.3 + legacy1 + legacy2 items, 279 representative reports), files in the same shapes as
the earlier inputs of tools/make_main_figures.py:
  results/oct_search/legacy_fig/results/derived/practice_trends_112.json   (keys the figures read)
  results/oct_search/legacy_fig/results/derived/reporting_trends_v9.json   (29 rows of an appendix table of an earlier draft, recomputed per study)
  results/oct_search/legacy_fig/results/derived/checklist_v22_scores.json  (43 items + TRIPOD+AI levels, core studies)
  results/oct_search/legacy_fig/records.json                               (protocol-shaped per-study records for the live figure code)
Value sources: legacy final (settled) > consensus final > Claude round-1 value (only while settlement is pending; counted and printed).
Usage: legacy_figdata.py"""
import collections, csv, json, os, re, statistics, sys
HERE = os.path.dirname(os.path.abspath(__file__)); ROOT = os.path.dirname(os.path.dirname(HERE)); os.chdir(ROOT)
OUTD = "results/oct_search/legacy_fig"; DER = f"{OUTD}/results/derived"
PERIODS = ["≤2019", "2020–2022", "2023–2024", "2025–2026"]
SRC = collections.Counter()


def per(y):
    return 0 if y <= 2019 else 1 if y <= 2022 else 2 if y <= 2024 else 3


def load_final(folder, reps):
    """item -> record -> final dict."""
    out = collections.defaultdict(dict)
    cmp_ = f"{folder}/compare_r1.jsonl"
    if os.path.exists(cmp_):
        for l in open(cmp_):
            r = json.loads(l)
            if r["record_id"] in reps: out[r["item"]][r["record_id"]] = ("r1_claude", r["claude"] if r["cls"] != "AGREE" else r["claude"])
            if r["cls"] == "AGREE": out[r["item"]][r["record_id"]] = ("agree", r["claude"])
    for name, tag in (("final_items.jsonl", "consensus"), ("final_settled.jsonl", "settled")):
        p = f"{folder}/{name}"
        if os.path.exists(p):
            for l in open(p):
                r = json.loads(l)
                if r["record_id"] in reps and r.get("final") is not None: out[r["item"]][r["record_id"]] = (tag, r["final"])
    return out


def main():
    os.makedirs(DER, exist_ok=True)
    reps = open("results/oct_search/coding_legacy/reps.txt").read().split()
    meta = {r["record_id"]: r for r in csv.DictReader(open("results/oct_search/public/included_reports.csv"))}
    links = list(csv.DictReader(open("results/oct_search/public/report_study_links.csv")))
    sid = {l["record_id"]: l["study_id"] for l in links}
    F = {}
    for folder in ("results/oct_search/coding_legacy", "results/oct_search/coding_legacy2"):
        F.update(load_final(folder, set(reps)))
    # author decisions applied after settlement (results/oct_search/coding_legacy/author_decisions_*.json)
    import glob as _g
    for _f in sorted(_g.glob("results/oct_search/coding_legacy/author_decisions_*.json")):
        for _d in json.load(open(_f)):
            if _d["record_id"] in reps: F.setdefault(_d["item"], {})[_d["record_id"]] = ("author_decision", _d["final"])
    main_rows = collections.defaultdict(dict)
    for l in open("results/oct_search/coding/final_items_clean.jsonl"):
        r = json.loads(l)
        if r["record_id"] in reps and r.get("final"): main_rows[r["item"]][r["record_id"]] = r["final"]
    D = {r["record_id"]: r for r in csv.DictReader(open("results/oct_search/coding/analysis/study_derived.csv"))}

    def units(item, rid):
        """[(unit, value)] for a legacy item; status not_applicable -> [('', 'NA')]; not_reported -> NR."""
        src, x = F.get(item, {}).get(rid, (None, None))
        SRC[src] += 1
        if not x: return []
        st = x.get("status")
        vals = [(v.get("unit", ""), str(v.get("value", "")).strip()) for v in (x.get("values") or []) if str(v.get("value", "")).strip()]
        if vals: return vals
        return [("", {"not_applicable": "NA", "not_reported": "NR", "unclear": "UNC"}.get(st, "NR"))]

    def codes(item, rid):
        return [c.split(":")[0].strip() for _, v in units(item, rid) for c in re.split(r"\s*;\s*", v) if c.strip()]  # 'METHOD_RESEARCH: compare_existing' -> code

    def first(item, rid, default="NR"):
        c = codes(item, rid)
        return c[0] if c else default

    def text_value(item, rid):
        return "; ".join(v for _, v in units(item, rid))

    # ---------- protocol-shaped records ----------
    PERF = collections.defaultdict(list)
    for p in ("results/oct_search/coding/pilot_final/perf_rows_final.jsonl", "results/oct_search/coding/perf_rows_final.jsonl"):
        for l in open(p):
            r = json.loads(l); PERF[r["record_id"]].append(r)
    MET = [("AUROC", r"auroc|auc|roc|c[- ]?statistic|c[- ]?index|area under"), ("AUPRC", r"auprc|pr[- ]?auc|precision[- ]recall curve|average precision"),
           ("BRIER", r"brier"), ("BACC", r"balanced accuracy"), ("ACC", r"accura"), ("SENS", r"sensitiv|recall|true positive rate|\btpr\b"),
           ("SPEC", r"specific|true negative rate|\btnr\b"), ("PPV", r"precision|\bppv\b|positive predictive"), ("NPV", r"\bnpv\b|negative predictive"),
           ("F1", r"\bf1|f-score|f score|f-measure"), ("MCC", r"\bmcc\b|matthews"), ("KAPPA", r"kappa"), ("DCA", r"net benefit|decision curve")]

    def metric_codes(rid):
        out = set()
        for p in PERF.get(rid, []):
            t = str(p.get("metric", "")).lower()
            for c, pat in MET:
                if re.search(pat, t):
                    out.add(c)
                    if c not in ("BACC",): break
        return [{"metric": c} for c in sorted(out)]

    def age(rid):
        t = text_value("legacy.age_range", rid)
        lo = re.search(r"min:\s*([\d.]+)", t); hi = re.search(r"max:\s*([\d.]+)", t)
        return (lo.group(1) if lo else "NR"), (hi.group(1) if hi else "NR")

    CYC = {1998: 1, 2001: 2, 2005: 3, **{y: 4 for y in (2007, 2008, 2009)}, **{y: 5 for y in (2010, 2011, 2012)}, **{y: 6 for y in (2013, 2014, 2015)},
           **{y: 7 for y in (2016, 2017, 2018)}, **{y: 8 for y in (2019, 2020, 2021)}, **{y: 9 for y in (2022, 2023, 2024)}, **{y: 10 for y in (2025, 2026, 2027)}}

    def year_scope(rid):
        """Survey years analysed, by fixed rule from the coded KNHANES survey years (data_source.survey_cycles) and the
        published KNHANES cycle boundaries (IV 2007-2009, V 2010-2012, ... IX 2022-2024): one year -> ONE_YEAR, several
        years in one cycle -> MULTI_SAME, years in more than one cycle -> MULTI_CROSS; None when no year is printed
        (author: settle by rule; cycle membership is public, not something a report has to state)."""
        #
        x = main_rows.get("data_source.survey_cycles", {}).get(rid) or {}
        ys = set()
        for v in x.get("values") or []:
            if re.match(r"\s*NHANES", str(v.get("unit", ""))): continue  # US NHANES datasets
            t = str(v.get("value", ""))
            #
            # years analysed: when the value also states a year outside the parentheses, that year is used (review v14 fix)
            spn = r""
            sp = [(int(m_.group(2)), int(m_.group(3)) if len(m_.group(3)) == 4 else int(m_.group(2)[:2] + m_.group(3))) for m_ in re.finditer(spn, t)]
            t_ = re.sub(spn, r"\1", t); rest = [int(y) for y in re.findall(r"(?<!\d)((?:19|20)\d\d)(?!\d)", t_)]
            if sp and rest and all(any(a0 <= y <= b0 for a0, b0 in sp) for y in rest): t = t_
            for a_, b_ in re.findall(r"(?<!\d)((?:19|20)\d\d)\s*(?:[-–—~∼～]|to|through|and)\s*((?:19|20)?\d\d)(?!\d)", t):
                a1, b1 = int(a_), int(b_) if len(b_) == 4 else int(a_[:2] + b_)
                if 1998 <= a1 <= b1 <= 2027 and " and " not in t[t.find(a_):t.find(a_) + 12]: ys.update(range(a1, b1 + 1))
            ys.update(int(y) for y in re.findall(r"(?<!\d)((?:19|20)\d\d)(?!\d)", t) if 1998 <= int(y) <= 2027)
        ys = {y for y in ys if y in CYC}
        if not ys: return None
        if len(ys) == 1: return "ONE_YEAR"
        return "MULTI_SAME" if len({CYC[y] for y in ys}) == 1 else "MULTI_CROSS"

    SEX = {"BOTH": "None (both sexes)", "WOMEN_ONLY": "female only", "MEN_ONLY": "male only", "NR": "NR"}
    CODE_USED = {"PUBLIC_ACCESS_VERIFIED", "PUBLIC_LINK_REPORTED_ACCESS_NOT_REVERIFIED"}
    # One definition of shared analysis code for an appendix table of an earlier draft, the figures and checklist item C36 (author review:
    # the three codings differed for 8 studies): the report gives a public location (repository link or supplementary
    # file) holding code of the analysis; code on request, promised after publication, or code of a web tool only does not
    # count. Base: checklist C36 (both coders, settled); the 8 studies where MOD15, C36 and the study classification
    # differed were settled by this rule from the coded code-availability statement (model_development.model_code_availability).
    CODE_RULE = {"OCT0055": True, "OCT0842": True, "OCT0687": True, "OCT0954": True,      # public repository link or supplementary file
                 "OCT0729": False, "OCT0172": False, "OCT0723": False, "OCT0384": False}  # promised later / no location / web-tool code / no code
    def code_public(rid):
        return CODE_RULE[rid] if rid in CODE_RULE else first("legacy.checklist.C36", rid, "") == "met"
    recs = {}
    for rid in reps:
        y = int(meta[rid]["year"])
        pi = {}
        def put(k, vals): pi[k] = [{"value": v} for v in vals]
        lo, hi = age(rid); put("POP03", [lo]); put("POP04", [hi])
        put("POP05", [SEX.get(first("legacy.POP05", rid), "NR")])
        for k in ("OUT11", "OUT12", "MET_CI", "MET_PAIR", "VI17"): put(k, [first(f"legacy.{k}", rid)])
        for k in ("VI01", "VI10", "VI11", "VI16", "SUR04", "SUR06", "SUR07", "SUR10", "SUR11", "PRE05", "PRE11", "PRE13", "PRE14", "IMB03", "OUT16", "PRD13"):
            put(k, [first(f"legacy.{k}", rid)])
        put("VI02", codes("legacy.VI02", rid) or ["NA"]); put("VI07", codes("legacy.VI07", rid) or ["NA"])
        put("VI06", [text_value("legacy.VI06", rid) or "NA"])
        put("VAL02", codes("legacy.VAL02", rid) or ["NONE_NR"])
        # Ranking stability as defined in the manuscript (Methods): rankings compared across resamples, KNHANES survey cycles or
        # subgroups. The legacy item also let comparisons across models, importance methods or other sensitivity analyses count;
        # those are recoded NOT_USED by this fixed rule (author: settle by rule; keep the manuscript's definitions).
        st_txt = text_value("legacy.stability_method", rid).lower()
        cats = [c for c, pat in (("RESAMPLE", r"resampl|under-?sampl|over-?sampl|bootstrap|fold|cross-valid|split|partition|iteration"),
                                 ("CYCLE", r"cycle|survey year|yearly|period|200\d|201\d|202\d"),
                                 ("SUBGROUP", r"subgroup|\bsex\b|gender|\bages?\b|age group|\bmen\b|\bwomen\b|phenotype|cluster|\bbmi\b|stratif"))
                if re.search(pat, st_txt)]
        put("STAB_CAT", cats or ["NA"])
        if first("legacy.VI16", rid) == "USED" and not cats: pi["VI16"] = [{"value": "NOT_USED"}]
        put("MOD15", ["USED" if code_public(rid) else (first("legacy.MOD15", rid) if first("legacy.MOD15", rid) not in CODE_USED else "NOT_USED")])
        put("TSK01", [first("legacy.task", rid)]); put("DAT08", [year_scope(rid) or first("legacy.year_scope", rid, "UNC")])
        # Applicability by fixed rule (review v9): combined-year survey weights cannot apply to one KNHANES year
        if pi["DAT08"][0]["value"] == "ONE_YEAR": pi["SUR11"] = [{"value": "NA"}]
        put("DAT14", codes("legacy.survey_components", rid))
        put("OUT10", [{"current_state_same_survey": "CURRENT", "future_event": "FUTURE", "timing_unclear": "UNC"}.get(first("legacy.outcome_timing", rid), "UNC")])
        cal = D.get(rid, {}).get("calibration_beyond_brier") in ("True", "1", "yes", "Y")
        put("MET_CALPLOT_R", ["R" if cal else "NR"])
        for i in range(1, 20): put(f"REP{i:02d}", [first(f"legacy.REP{i:02d}", rid)])
        for k in [k for k in F if k.startswith(("legacy.PD_", "legacy.PE_"))]:
            put(k.split(".", 1)[1], [c for c in codes(k, rid)] or ["NA"])
            pi["U:" + k.split(".", 1)[1]] = [{"unit": u, "value": v.split(":")[0].strip()} for u, v in units(k, rid)]  # unit-level, for the text
        od = main_rows.get("outcome.definition", {}).get(rid) or {}
        put("OUT02", [((od.get("values") or [{}])[0].get("unit") or "") + " " + ((od.get("values") or [{}])[0].get("value") or "")])
        recs[rid] = {"study_id": rid, "study": sid.get(rid), "metadata": {"publication_year": y}, "protocol_items": pi, "performance_metrics": metric_codes(rid)}
    cat = {r: first("legacy.study_category", r, "HEALTH_ANALYSIS") for r in reps}
    task = {r: recs[r]["protocol_items"]["TSK01"][0]["value"] for r in reps}
    HEALTH = [r for r in reps if cat[r] == "HEALTH_ANALYSIS"]; METHOD = [r for r in reps if cat[r] == "METHOD_RESEARCH"]
    CORE = [r for r in HEALTH if task[r] == "CLS"]
    P = lambda rs: [[r for r in rs if per(recs[r]["metadata"]["publication_year"]) == k] for k in range(4)]
    PC = P(CORE); period_n = [len(x) for x in PC]
    has = lambda r, k, acc: any(x["value"] in acc for x in recs[r]["protocol_items"].get(k, []))
    fv = lambda r, k: recs[r]["protocol_items"].get(k, [{}])[0].get("value")
    byp = lambda f: [sum(bool(f(r)) for r in g) for g in PC]
    o = {"periods": PERIODS, "period_n": period_n, "source": "search, legacy_figdata.py"}
    # earlier-draft Figure 2
    mkind = {r: first("legacy.study_category", r) for r in METHOD}
    def method_kind(r):
        t = " ".join(v for _, v in units("legacy.study_category", r)).lower() + " " + (F["legacy.study_category"].get(r, (0, {}))[1] or {}).get("rationale", "").lower()
        return "compare_existing" if "compare_existing" in t else "develop_or_improve"
    def health_kind(r):
        t = task[r]
        if t == "CLS": return "classification"
        txt = " ".join(v for _, v in units("legacy.task", r)).lower()
        return "continuous_or_ordered" if t == "CONT" or "continuous" in txt or "ordered" in txt else "other"
    o["task_composition"] = {"health": dict(collections.Counter(health_kind(r) for r in HEALTH)), "method": dict(collections.Counter(method_kind(r) for r in METHOD))}
    for k in ("classification", "continuous_or_ordered", "other"): o["task_composition"]["health"].setdefault(k, 0)
    for k in ("develop_or_improve", "compare_existing"): o["task_composition"]["method"].setdefault(k, 0)
    grp = lambda r: "core" if r in CORE else "other_health" if r in HEALTH else "method"
    topic = {r: first("legacy.topic", r, "OTHER_OR_CROSS_CUTTING") for r in reps}
    o["literature_map"] = [{"id": r, "year": recs[r]["metadata"]["publication_year"], "group": grp(r), "topic": topic[r], "ranking": has(r, "VI01", {"USED"})} for r in reps]
    tim = collections.Counter(fv(r, "OUT10") for r in CORE)
    src = collections.Counter(first("legacy.outcome_source", r, "other_or_not_reported") for r in CORE)
    o["classified_outcome"] = {"n": len(CORE), "current_state_same_survey": tim["CURRENT"], "timing_unclear": tim["UNC"], "future_event": tim["FUTURE"], "source": dict(src)}
    o["outcome_timing_192"] = {k: o["classified_outcome"][k] for k in ("current_state_same_survey", "timing_unclear", "future_event")}
    rank = [r for r in CORE if has(r, "VI01", {"USED"})]
    o["importance_ranking_total"] = len(rank)
    # earlier-draft Figure 3
    o["core_topics"] = dict(collections.Counter(topic[r] for r in CORE).most_common())
    o["core_year_scope"] = {k: sum(fv(r, "DAT08") == k for r in CORE) for k in ("ONE_YEAR", "MULTI_SAME", "MULTI_CROSS", "UNC")}
    o["core_year_scope"]["UNC"] += len(CORE) - sum(o["core_year_scope"].values())
    ost = collections.Counter(first("legacy.outcome_structure", r, "BINARY") for r in CORE)
    o["outcome_structure"] = {k: ost.get(k, 0) for k in ("BINARY", "MULTIBIN", "MULTICLASS", "MIXED")}
    o["outcome_structure"]["UNC"] = len(CORE) - sum(o["outcome_structure"].values())  # structure coded unclear (author review: shown apart, not pooled with mixed)
    o["survey_components_165"] = {k: sum(has(r, "DAT14", {k}) for r in CORE) for k in ("HEALTH_INTERVIEW", "EXAMINATION", "LABORATORY", "ORAL_HEALTH", "NUTRITION")}
    def num(x):
        m_ = re.search(r"\d[\d,]*\.?\d*", str(x or "").replace(",", ""))
        return float(m_.group(0)) if m_ else None
    ns = [num(D.get(r, {}).get("n_analysed_max")) for r in CORE]; nsv = sorted(int(x) for x in ns if x)
    q = lambda v: statistics.quantiles(v, n=4, method="inclusive") if len(v) > 1 else [None] * 3
    qs = q(nsv); o["core_sample"] = {"values": nsv, "reported": len(nsv), "median": statistics.median(nsv), "q1": qs[0], "q3": qs[2]}
    cp = sorted(x for x in (num(first("legacy.candidate_predictors", r, "")) for r in CORE) if x)
    qc = q(cp); o["candidate_predictors"] = {"reported": len(cp), "median": statistics.median(cp), "q1": qc[0], "q3": qc[2]}; o["candidate_predictor_values"] = cp
    mh = collections.Counter(first("legacy.missing_handling", r, "not_reported") for r in CORE)
    keys = ("complete_case", "single_imputation", "multiple_imputation", "model_native", "other_or_several", "not_reported")
    o["missing_handling_165"] = {k: mh.get(k, 0) for k in keys}; o["missing_handling_165"]["other_or_several"] += len(CORE) - sum(o["missing_handling_165"].values())
    alg = {r: set(c.split("(")[0].strip().lower().replace(" ", "_") for c in codes("legacy.algorithms_fitted", r)) for r in CORE}
    fams = ("boosting", "random_forest", "logistic_regression", "decision_tree", "svm", "neural_network")
    o["algorithms_fitted_192"] = {k: sum(k in alg[r] for r in CORE) for k in fams}
    o["algorithms_fitted_192"]["other"] = sum(bool(alg[r] - set(fams)) for r in CORE); o["algorithms_fitted_192"]["n"] = len(CORE)
    selmap = {"boosting": "Boosting", "random forest": "Random forest", "logistic regression": "Logistic regression", "decision tree": "Decision tree",
              "svm": "SVM", "neural network": "Neural network", "single_algorithm": "single_algorithm", "not designated": "Not designated"}
    sm = collections.Counter(selmap.get(first("legacy.selected_model", r, "Other").lower(), "Other") for r in CORE)
    o["selected_model_family_192"] = {"n": len(CORE), **{k: sm.get(k, 0) for k in ("Not designated", "Boosting", "Neural network", "Logistic regression", "Random forest", "Decision tree", "SVM", "Other", "single_algorithm")}}
    PR = {"importance_ranking": lambda r: has(r, "VI01", {"USED"}), "shap": lambda r: has(r, "VI02", {"SHAP"}),
          "boosting": lambda r: "boosting" in alg[r], "validation_beyond_development": lambda r: has(r, "VAL02", {"EXTERNAL", "TEMPORAL"}),
          "calibration": lambda r: has(r, "MET_CALPLOT_R", {"R"}), "code_link": lambda r: has(r, "MOD15", {"USED"}),
          "survey_weight_mention": lambda r: has(r, "SUR04", {"USED"})}
    o["practices"] = {k: byp(f) for k, f in PR.items()}
    o["ranking_n"] = o["practices"]["importance_ranking"]
    o["stability_among_ranking"] = byp(lambda r: r in rank and has(r, "VI16", {"USED"}))
    o["shap_among_ranking"] = byp(lambda r: r in rank and has(r, "VI02", {"SHAP"}))
    dom = collections.Counter(c for r in rank for c in set(codes("legacy.VI07", r)))
    o["ranking_domains_all"] = {"n": len(rank), **dict(dom.most_common())}
    # reporting_trends rows (an appendix table of an earlier draft and earlier-draft Figures 9B, 10), recomputed per study
    pre_before = lambda r: fv(r, "PRE05") == "NOT_USED" or fv(r, "PRE14") == "NOT_USED" or fv(r, "PRE13") == "BEFORE" or fv(r, "IMB03") == "BEFORE"
    pre_all_within = lambda r: not pre_before(r) and all(fv(r, k) in ("USED", "NA") for k in ("PRE05", "PRE14")) and fv(r, "PRE13") in ("WITHIN", "TRAIN", "NA") and fv(r, "IMB03") in ("WITHIN", "TRAIN", "NA")
    rows = {
        "Several survey years combined": lambda r: fv(r, "DAT08") in ("MULTI_SAME", "MULTI_CROSS"),
        "Combined-year weights used": lambda r: has(r, "SUR11", {"USED"}),
        "Age range reported": lambda r: fv(r, "POP03") != "NR" or fv(r, "POP04") != "NR",
        "Sex of the sample reported": lambda r: fv(r, "POP05") != "NR",
        "Outcome rebuildable from the report": lambda r: has(r, "OUT16", {"R2"}),
        "Basis of the outcome cut-off reported": lambda r: fv(r, "OUT11") == "Y" and fv(r, "OUT12") not in ("NR", "UNEXPLAINED", "NA"),
        "Number of candidate predictors reported": lambda r: num(first("legacy.candidate_predictors", r, "")) is not None,
        "Predictor set rebuildable from the report": lambda r: has(r, "PRD13", {"R2"}),
        "Missing-value handling reported": lambda r: first("legacy.missing_handling", r, "not_reported") != "not_reported",
        "Several algorithms compared": lambda r: first("legacy.selected_model", r, "") != "single_algorithm",
        "Final model fully specified": lambda r: first("legacy.final_model_specified", r) == "R",
        "Analysis code shared": PR["code_link"],
        "Tuning kept apart from the final evaluation": lambda r: first("legacy.tuning_kept_apart", r) in ("USED", "NA"),
        "All preprocessing within the training data": pre_all_within,
        "At least one preprocessing step before the split": pre_before,
        "Sampling weights mentioned": PR["survey_weight_mention"],
        "Weights used in model fitting": lambda r: has(r, "SUR06", {"USED"}),
        "Weights used in performance evaluation": lambda r: has(r, "SUR07", {"USED"}),
        "Strata or PSUs used in variance estimation": lambda r: has(r, "SUR10", {"USED"}),
        "Validation beyond the development data": PR["validation_beyond_development"],
        "AUROC reported": lambda r: any(m_["metric"] == "AUROC" for m_ in recs[r]["performance_metrics"]),
        "Confidence interval for performance": lambda r: has(r, "MET_CI", {"Y"}),
        "Decision-threshold selection reported": lambda r: D.get(r, {}).get("threshold_reported") in ("True", "1", "yes", "Y"),
        "Calibration reported": PR["calibration"],
        "Importance ranking produced": PR["importance_ranking"],
        "SHAP used": PR["shap"],
        "Ranking stability checked": lambda r: r in rank and has(r, "VI16", {"USED"}),
        "Ranking used for a reduced predictor set": lambda r: r in rank and has(r, "VI10", {"USED"}),
        "Ranking guided a later statistical analysis": lambda r: r in rank and has(r, "VI11", {"USED"})}
    rt = {"period_n": period_n, "source": "search: recomputed per study by tools/oct_search/legacy_figdata.py", "rows": {k: byp(f) for k, f in rows.items()}}
    def unit_vals(r, k): return [x["value"] for x in recs[r]["protocol_items"].get(k, []) if x["value"] != "NA"]
    rt["units"] = {"development": [sum(len(unit_vals(r, "PD_OVERALL")) for r in g) for g in PC], "evaluation": [sum(len(unit_vals(r, "PE_OVERALL")) for r in g) for g in PC]}
    def upct(k, val): return [round(100 * sum(v == val for r in g for v in unit_vals(r, k)) / max(1, sum(len(unit_vals(r, k)) for r in g)), 1) for g in PC]
    tri = lambda g, acc: round(statistics.mean(100 * sum(fv(r, f"REP{i:02d}") in acc for i in range(1, 20)) / 19 for r in g), 1) if g else 0
    rt["pct"] = {"TRIPOD+AI elements completely reported (mean % of 19)": [tri(g, ("R",)) for g in PC],
                 "TRIPOD+AI elements completely or partly reported (mean % of 19)": [tri(g, ("R", "P")) for g in PC],
                 "PROBAST+AI developments low quality (% of units)": upct("PD_OVERALL", "LOW"), "PROBAST+AI evaluations high risk (% of units)": upct("PE_OVERALL", "HIGH"),
                 "PROBAST+AI participants domain high risk (% of evaluations)": upct("PE_D1", "HIGH")}
    o["table1_by_period"] = {"period_n": period_n, "n": len(CORE), **{k: v for k, v in rt["rows"].items()}}
    # checklist (core studies): items meta from the earlier file, studies recomputed
    ck = json.load(open("results/derived/checklist_v22_scores.json"))
    # author: name the weight precisely (survey sampling weights, not model or class weights)
    OVR = {"RC06": dict(crit_en="States whether survey weights were used and which survey weight, or why not", crit_ko=""),
           "RC07": dict(item_en="Combined-year survey weights", item_ko="", crit_en="When survey years were combined, reports how survey weights were adjusted for the combination (not applicable when the years were analysed separately or survey weights were stated not to be used)", crit_ko=""),
           "RC24": dict(item_en="Survey weights in model fitting", item_ko="", crit_en="States whether survey weights were used in model fitting and how, or why not", crit_ko=""),
           "RC32": dict(item_en="Survey weights in performance evaluation", item_ko="", crit_en="States whether performance measures were weighted by survey weights and how, or why not", crit_ko=""),
           "RC42": dict(item_en="Survey weights in importance aggregation", item_ko="", crit_ko="")}
    for x in ck["items"]: x.update(OVR.get(x["id"], {}))
    LEV = {"R": "Reported", "P": "Partly reported", "NR": "Not reported"}
    studies = {}; NAWHY = {"C04": collections.Counter(), "C05": collections.Counter()}
    for r in CORE:
        it = {}
        for x in ck["items"]:
            u = F.get(f"legacy.checklist.{x['pub_id']}", {}).get(r)
            if not u: continue
            st = (u[1] or {}).get("status"); v = first(f"legacy.checklist.{x['pub_id']}", r, "")
            if x["pub_id"] in ("C04", "C05"):  # applicability composition, reported in the earlier-draft Figure 5 caption
                why = ("coded_NA" if (st == "not_applicable" or v.upper() == "NA") else "one_year" if fv(r, "DAT08") == "ONE_YEAR"
                       else "weights_NA_or_not_used" if x["pub_id"] == "C04" and fv(r, "SUR11") in ("NA", "NOT_USED") else "applies")
                NAWHY[x["pub_id"]][f"{why}|{fv(r, 'DAT08')}|SUR11={fv(r, 'SUR11')}"] += 1
            if st == "not_applicable" or v.upper() == "NA": continue
            # same fixed rule (review v9): C04 applies to combined years with survey weights used or not reported;
            # C05 to combined or unclear years (one KNHANES year: nothing to harmonise)
            if x["pub_id"] in ("C04", "C05") and fv(r, "DAT08") == "ONE_YEAR": continue
            if x["pub_id"] == "C04" and fv(r, "SUR11") in ("NA", "NOT_USED"): continue
            it[str(x["idx"])] = code_public(r) if x["pub_id"] == "C36" else v == "met"
        studies[r] = {"items": it, "tripod": {str(i): LEV.get(fv(r, f"REP{i:02d}"), "Not reported") for i in range(1, 20)}}
    ck_out = {k: v for k, v in ck.items() if k not in ("studies", "removed")}; ck_out["studies"] = studies; ck_out["na_composition"] = {k_: dict(sorted(v_.items())) for k_, v_ in NAWHY.items()}
    ck_out["source"] = "search: items meta of checklist_v22; per-study values from legacy.checklist.C01-C43 and legacy.REP01-19"
    json.dump(o, open(f"{DER}/practice_trends_112.json", "w"), indent=1, ensure_ascii=False)
    json.dump(rt, open(f"{DER}/reporting_trends_v9.json", "w"), indent=1, ensure_ascii=False)
    json.dump(ck_out, open(f"{DER}/checklist_v22_scores.json", "w"), indent=1, ensure_ascii=False)
    json.dump({"ALL": reps, "HEALTH": HEALTH, "METHOD": METHOD, "CORE": CORE, "records": recs}, open(f"{OUTD}/records.json", "w"), ensure_ascii=False)
    print("studies", len(reps), "health", len(HEALTH), "method", len(METHOD), "core", len(CORE), "period_n", period_n, "ranking", len(rank))
    print("value sources", dict(SRC))


if __name__ == "__main__":
    main()
