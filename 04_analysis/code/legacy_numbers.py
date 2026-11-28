"""Numbers of the ORIGINAL manuscript text recomputed with the search data (author: same text, figures
and tables; new numbers). Reads the files written by legacy_figdata.py / legacy_figures.py (results/oct_search/legacy_fig)
and writes
  manuscript/legacy_numbers.tex   LaTeX macros \\k... used in paper/src/jce_main(_ko).tex
  results/oct_search/legacy_fig/legacy_numbers.json  (the same numbers, for checking)
and, with --table, rewrites the numeric cells of a supplementary table of an earlier draft (manuscript/supp_S9_detailed_counts.tex; formerly an appendix table of an earlier draft)
(row order = reporting_trends_v9 rows; labels and layout untouched).
Usage: legacy_numbers.py [--table]"""
import collections, json, os, re, statistics, sys
HERE = os.path.dirname(os.path.abspath(__file__)); ROOT = os.path.dirname(os.path.dirname(HERE)); os.chdir(ROOT)
L = "results/oct_search/legacy_fig"; DER = f"{L}/results/derived"
REC = json.load(open(f"{L}/records.json")); recs = REC["records"]
O = json.load(open(f"{DER}/practice_trends_112.json")); RT = json.load(open(f"{DER}/reporting_trends_v9.json"))
CK = json.load(open(f"{DER}/checklist_v22_scores.json"))
ALL, HEALTH, METHOD, CORE = REC["ALL"], REC["HEALTH"], REC["METHOD"], REC["CORE"]
N = collections.OrderedDict()
W = {0: "None", 1: "One", 2: "Two", 3: "Three", 4: "Four", 5: "Five", 6: "Six", 7: "Seven", 8: "Eight", 9: "Nine", 10: "Ten", 11: "Eleven", 12: "Twelve"}


DIG = "Zero One Two Three Four Five Six Seven Eight Nine".split()


def macro(k):
    """LaTeX macro names take letters only: digits spelled out (C05 -> CZeroFive)."""
    return re.sub(r"\d", lambda m: DIG[int(m.group(0))], re.sub(r"[^A-Za-z0-9]", "", k))


def put(k, v):
    N[k] = v


def pct(a, b, d=1):
    return f"{100 * a / b:.{d}f}" if b else "0.0"


def fv(r, k):
    return (recs[r]["protocol_items"].get(k) or [{}])[0].get("value")


def has(r, k, acc):
    return any(x["value"] in acc for x in recs[r]["protocol_items"].get(k, []))


def year(r):
    return recs[r]["metadata"]["publication_year"]


def per(y):
    return 0 if y <= 2019 else 1 if y <= 2022 else 2 if y <= 2024 else 3


def crossref_meta(ids):
    """Journal and author names (family, given) from Crossref by DOI; public bibliographic metadata, cached."""
    import csv, time, urllib.request
    cp = f"{L}/crossref_meta.json"; cache = json.load(open(cp)) if os.path.exists(cp) else {}
    meta = {r["record_id"]: r for r in csv.DictReader(open("results/oct_search/public/included_reports.csv"))}
    for i in ids:
        if cache.get(i, {}).get("journal"): continue
        cache[i] = {"journal": "", "authors": []}
        if meta[i]["doi"]:
            try:
                req = urllib.request.Request("https://api.crossref.org/works/" + meta[i]["doi"], headers={"User-Agent": "review-figure-builder/1.0"})
                m = json.load(urllib.request.urlopen(req, timeout=30))["message"]
                cache[i] = {"journal": (m.get("container-title") or [""])[0], "authors": [f"{a.get('family', '')}, {a.get('given', '')}" for a in m.get("author", [])]}
            except Exception:
                pass
            time.sleep(.2)
        if not cache[i]["journal"] and meta[i].get("kci_id"):  # KCI article page metadata
            try:
                req = urllib.request.Request("https://www.kci.go.kr/kciportal/ci/sereArticleSearch/ciSereArtiView.kci?sereArticleSearchBean.artiId=" + meta[i]["kci_id"], headers={"User-Agent": "review-figure-builder/1.0"})
                h = urllib.request.urlopen(req, timeout=30).read().decode("utf-8", "ignore")
                j = re.search(r'citation_journal_title" content="([^"]+)"', h)
                cache[i] = {"journal": j.group(1) if j else "", "authors": re.findall(r'citation_author" content="([^"]+)"', h)}
            except Exception:
                pass
    json.dump(cache, open(cp, "w"), ensure_ascii=False, indent=0)
    return cache


def main():
    pn = O["period_n"]; nC = len(CORE); P = [[r for r in CORE if per(year(r)) == k] for k in range(4)]
    rank = [r for r in CORE if has(r, "VI01", {"USED"})]; nR = len(rank)
    # ---- groups
    put("All", len(ALL)); put("Core", nC); put("OtherHealth", len(HEALTH) - nC); put("Method", len(METHOD))
    put("CorePct", pct(nC, len(ALL)))
    tc = O["task_composition"]; put("OtherCont", tc["health"].get("continuous_or_ordered", 0)); put("OtherOther", tc["health"].get("other", 0))
    put("MethDev", tc["method"]["develop_or_improve"]); put("MethCmp", tc["method"]["compare_existing"])
    for k in range(4): put("PerN" + "ABCD"[k], pn[k])
    y26 = sum(year(r) == 2026 for r in CORE); y25 = sum(year(r) == 2025 for r in CORE); put("CoreYtwentysix", y26); put("CoreYtwentyfive", y25)
    yc = collections.Counter(year(r) for r in ALL)
    put("AnnualMaxTo2019", max(v for y, v in yc.items() if y <= 2019)); put("Annual2024", yc[2024]); put("Annual2025", yc[2025]); put("Annual2026", yc[2026])
    put("YearMin", min(yc)); put("YearMax", max(yc))
    # ---- dataset and problem design (earlier-draft Figure 3)
    co = O["classified_outcome"]; put("SameSurvey", co["current_state_same_survey"]); put("TimingUnclear", co["timing_unclear"]); put("Future", co["future_event"])
    ys = O["core_year_scope"]; put("YOne", ys["ONE_YEAR"]); put("YSame", ys["MULTI_SAME"]); put("YCross", ys["MULTI_CROSS"]); put("YUnc", ys["UNC"])
    put("Pooled", ys["MULTI_SAME"] + ys["MULTI_CROSS"])
    t = O["core_topics"]; put("TopMetabolic", t.get("METABOLIC_ENDOCRINE", 0)); put("TopMental", t.get("MENTAL_HEALTH", 0))
    put("TopCardio", t.get("CARDIOVASCULAR", 0)); put("TopMusculo", t.get("MUSCULOSKELETAL", 0))
    agemin = collections.Counter()  # same categories as earlier-draft Figure 3C (make_main_figures._age): upper age < 19 -> under 19 only;
    for r in CORE:                   # minimum < 18 -> all ages; otherwise by minimum age 18-29 / 30-59 / 60+
        m = re.search(r"\d+", str(fv(r, "POP03") or "")); lo = int(m.group(0)) if m else None
        m2 = re.search(r"\d+", str(fv(r, "POP04") or "")); hi = int(m2.group(0)) if m2 else None
        agemin["nr" if lo is None and hi is None else "u19" if hi is not None and hi < 19 else "all" if lo is not None and lo < 18 else "nr" if lo is None
               else "a60" if lo >= 60 else "a30" if lo >= 30 else "a19"] += 1
    put("AgeNineteen", agemin["a19"]); put("AgeThirty", agemin["a30"]); put("AgeSixty", agemin["a60"]); put("AgeNR", agemin["nr"]); put("AgeUnder", agemin["u19"]); put("AgeAll", agemin["all"])
    sx = collections.Counter(fv(r, "POP05") for r in CORE)
    put("SexBoth", sx.get("None (both sexes)", 0)); put("SexWomen", sx.get("female only", 0)); put("SexMen", sx.get("male only", 0)); put("SexNR", sx.get("NR", 0))
    cs = O["core_sample"]; put("SampleMedian", f"{round(cs['median']):,}"); put("SampleQone", f"{round(cs['q1']):,}"); put("SampleQthree", f"{round(cs['q3']):,}")
    put("SampleReported", cs["reported"]); put("SampleNR", nC - cs["reported"])
    # ---- health variables
    os_ = O["outcome_structure"]; put("OutBinary", os_["BINARY"]); put("OutMultibin", os_["MULTIBIN"])
    cut = sum(fv(r, "OUT11") == "Y" for r in CORE); put("OutCut", cut); put("OutCutNA", nC - cut)
    src = co["source"]; put("SrcQuest", src.get("questionnaire_or_scale", 0)); put("SrcPhys", src.get("physical_measurement", 0))
    put("SrcLab", src.get("laboratory_value", 0)); put("SrcDiag", src.get("diagnosis_or_history", 0))
    sc = O["survey_components_165"]; put("CompInterview", sc["HEALTH_INTERVIEW"]); put("CompExam", sc["EXAMINATION"]); put("CompLab", sc["LABORATORY"]); put("CompNutr", sc["NUTRITION"])
    cp = O["candidate_predictors"]; put("CandReported", cp["reported"]); put("CandMedian", f"{cp['median']:g}"); put("CandNR", nC - cp["reported"])
    mh = O["missing_handling_165"]; put("MissCC", mh["complete_case"]); put("MissNR", mh["not_reported"])
    # ---- analysis
    af = O["algorithms_fitted_192"]; put("AlgBoost", af["boosting"]); put("AlgLR", af["logistic_regression"]); put("AlgRF", af["random_forest"])
    pr = O["practices"]; put("BoostA", pr["boosting"][0]); put("BoostD", pr["boosting"][3])
    sm = O["selected_model_family_192"]; put("SelBoost", sm["Boosting"]); put("SingleAlg", sm["single_algorithm"])
    val = collections.Counter(v for r in CORE for v in {x["value"] for x in recs[r]["protocol_items"].get("VAL02", [])})
    rows = RT["rows"]; tot = lambda k: sum(rows[k])
    put("Temporal", sum(has(r, "VAL02", {"TEMPORAL"}) for r in CORE))
    put("Split", sum(has(r, "VAL02", {"SPLIT", "TRAIN_TEST", "HOLDOUT"}) for r in CORE)); put("CV", sum(has(r, "VAL02", {"CV", "CROSS_VALIDATION"}) for r in CORE))
    put("Beyond", tot("Validation beyond the development data")); put("Auroc", tot("AUROC reported")); put("CI", tot("Confidence interval for performance"))
    put("Calib", tot("Calibration reported"))
    # ---- variable importance
    put("Ranking", nR); put("RankA", pr["importance_ranking"][0]); put("RankD", pr["importance_ranking"][3])
    put("RankAPct", pct(pr["importance_ranking"][0], pn[0])); put("RankDPct", pct(pr["importance_ranking"][3], pn[3]))
    r26 = [r for r in rank if year(r) == 2026]; put("RankTwentysix", len(r26))
    shap = [r for r in CORE if has(r, "VI02", {"SHAP"})]; put("Shap", len(shap)); put("ShapD", pr["shap"][3]); put("ShapA", pr["shap"][0])
    put("ShapTwentysix", sum(year(r) == 2026 for r in shap))
    put("Stab", tot("Ranking stability checked")); put("Reduced", tot("Ranking used for a reduced predictor set")); put("Later", tot("Ranking guided a later statistical analysis"))
    none = sum(not any(has(r, k, {"USED"}) for k in ("VI16", "VI10", "VI11", "VI17")) for r in rank); put("RankNone", none)
    put("Fidelity", sum(has(r, "VI17", {"USED"}) for r in rank))
    dom = O["ranking_domains_all"]; put("DomAge", dom.get("AGE", 0)); put("DomSes", dom.get("SOCIOECONOMIC", 0)); put("DomBody", dom.get("ADIPOSITY_BODY_SIZE", 0))
    nv = O.get("named_variable_count_all_models", {"strings": 0, "strings_mapped": 0})  # written by legacy_figures.py (build_112)
    put("NamedStrings", f"{nv['strings']:,}"); put("NamedMapped", f"{nv['strings_mapped']:,}")
    dp = O.get("diabetes_variable_panel_112", {}); put("DiabetesN", len(dp.get("studies", [])) if isinstance(dp, dict) else 0)
    # ---- frameworks and checklist
    put("CodeA", rows["Analysis code shared"][0]); put("CodeD", rows["Analysis code shared"][3])
    c26 = [r for r in CORE if year(r) == 2026]
    put("CalTwentysix", sum(has(r, "MET_CALPLOT_R", {"R"}) for r in c26)); put("BeyondTwentysix", sum(has(r, "VAL02", {"EXTERNAL", "TEMPORAL"}) for r in c26))
    # journals and authors of the 2026 studies reporting validation beyond the development data (Discussion; Crossref, cached)
    v26 = [r for r in c26 if has(r, "VAL02", {"EXTERNAL", "TEMPORAL"})]
    cm = crossref_meta(v26)
    js = collections.Counter(cm[r]["journal"] for r in v26 if cm[r]["journal"]); au = collections.Counter(a_ for r in v26 for a_ in set(cm[r]["authors"]))
    put("ValTwentysixJournals", len(js)); put("ValTwentysixMaxPerAuthor", max(au.values()) if au else 0); put("ValTwentysixNoJournal", sum(not cm[r]["journal"] for r in v26))
    put("CalD", rows["Calibration reported"][3]); put("BeyondD", rows["Validation beyond the development data"][3])
    rep = lambda r, i: fv(r, f"REP{i:02d}")
    ncomp = [sum(rep(r, i) == "R" for i in range(1, 20)) for r in CORE]
    put("TripodAllComplete", sum(n == 19 for n in ncomp)); put("TripodMedian", f"{statistics.median(ncomp):g}"); put("TripodMin", min(ncomp)); put("TripodMax", max(ncomp))
    for i, nm in ((8, "Counts"), (6, "OutcomeDef"), (17, "FinalModel"), (9, "SampleSize"), (19, "Registration")):
        k = sum(rep(r, i) == "R" for r in CORE); put("Rep" + nm, k); put("Rep" + nm + "Pct", pct(k, nC))
    def units(k):
        return [x["value"] for r in CORE for x in recs[r]["protocol_items"].get(k, []) if x["value"] != "NA"]
    pd_, pe = units("PD_OVERALL"), units("PE_OVERALL"); put("DevUnits", len(pd_)); put("EvalUnits", len(pe))
    put("DevLow", sum(v == "LOW" for v in pd_)); put("EvalHigh", sum(v == "HIGH" for v in pe))
    def unit_map(r, k):
        return {x["unit"]: x["value"] for x in recs[r]["protocol_items"].get("U:" + k, []) if x["value"] != "NA"}
    for k, nm in (("PE_D4", "Analysis"), ("PE_D1", "Participants"), ("PE_D3", "Outcome"), ("PE_D2", "Predictors")):
        # domain judged high among the evaluation units with an overall judgement (unit labels matched; unlabelled single units paired)
        n_ = 0
        for r in CORE:
            ov, dm = unit_map(r, "PE_OVERALL"), unit_map(r, k)
            if len(ov) == 1 and len(dm) == 1: n_ += next(iter(dm.values())) == "HIGH"
            else: n_ += sum(dm.get(u) == "HIGH" for u in ov)
        put("EvalHigh" + nm, n_)
    tp = RT["pct"]["TRIPOD+AI elements completely reported (mean % of 19)"]
    for k in range(4): put("TripodMean" + "ABCD"[k], f"{tp[k]:.1f}")
    for nm, row in (("CI", "Confidence interval for performance"), ("Beyond", "Validation beyond the development data"), ("Calib", "Calibration reported")):
        put(nm + "PctA", pct(rows[row][0], pn[0])); put(nm + "PctD", pct(rows[row][3], pn[3]))
    eh = RT["pct"]["PROBAST+AI evaluations high risk (% of units)"]; put("EvalHighMinPct", f"{int(min(eh))}")  # floor: "at least" must hold
    # checklist
    items = CK["items"]; S = CK["studies"]; idx = {x["pub_id"]: str(x["idx"]) for x in items}
    def met(c):
        v = [S[r]["items"][idx[c]] for r in CORE if idx[c] in S.get(r, {}).get("items", {})]
        return sum(v), len(v)
    sc_ = []
    for r in CORE:
        v = list(S.get(r, {}).get("items", {}).values())
        if v: sc_.append(100 * sum(v) / len(v))
    put("CkMedian", f"{statistics.median(sc_):.1f}"); put("CkMin", f"{min(sc_):.1f}"); put("CkMax", f"{max(sc_):.1f}")
    stage = collections.defaultdict(list)
    for r in CORE:
        it = S.get(r, {}).get("items", {})
        for st in ("D", "M", "I"):
            v = [it[str(x["idx"])] for x in items if x.get("stage") == st and str(x["idx"]) in it]
            if v: stage[st].append(100 * sum(v) / len(v))
        v = [it[str(x["idx"])] for x in items if "S" in x.get("note", "") and str(x["idx"]) in it]  # note *S = KNHANES-specific
        if v: stage["K"].append(100 * sum(v) / len(v))
    for st, nm in (("D", "Data"), ("M", "Model"), ("I", "Importance"), ("K", "Knhanes")):
        put("CkStage" + nm, f"{statistics.median(stage[st]):.1f}" if stage[st] else "--")
    low = sorted(((100 * a / b, c, a, b) for c in idx for a, b in [met(c)] if b and 100 * a / b < 10), key=lambda z: z[0])
    put("CkLowN", len(low)); put("CkLowNWord", W.get(len(low), str(len(low))))
    for c in idx:
        a, b = met(c); put("Ck" + c.replace("C", "C"), f"{pct(a, b)}"); put("Ck" + c + "n", a); put("Ck" + c + "d", b)
    # TRIPOD element 4 vs checklist (Results paragraph)
    e4 = [r for r in CORE if rep(r, 4) == "R"]; put("ElemFourComplete", len(e4))
    e11 = [r for r in CORE if rep(r, 11) == "R"]; put("ElemElevenComplete", len(e11))
    e19p = [r for r in CORE if rep(r, 19) == "P"]; put("ElemNineteenPartly", len(e19p))
    def met_in(c, grp):
        v = [S[r]["items"][idx[c]] for r in grp if idx[c] in S.get(r, {}).get("items", {})]
        return sum(v), len(v)
    for c in ("C02", "C03", "C05"):
        a, b = met_in(c, e4); put("ElemFour" + c, pct(a, b, 0))
        put("ElemFour" + c + "n", a); put("ElemFour" + c + "d", b)
    a, b = met_in("C22", e11); put("ElemElevenCtwentytwo", pct(a, b, 0))
    put("ElemElevenCtwentytwon", a); put("ElemElevenCtwentytwod", b)
    put("ElemFourElevenSame", "yes" if set(e4) == set(e11) else f"no ({len(set(e4) & set(e11))} shared)")
    rest4 = [r for r in CORE if r not in e4]; rest11 = [r for r in CORE if r not in e11]; rest19 = [r for r in CORE if r not in e19p]
    for c in ("C03", "C05"):
        a_, b_ = met_in(c, rest4); put("OutFour" + c + "n", a_); put("OutFour" + c + "d", b_)
    a_, b_ = met_in("C22", rest11); put("OutElevenCtwentytwon", a_); put("OutElevenCtwentytwod", b_)
    for c, nm in (("C35", "Data"), ("C36", "Code")):
        a_, b_ = met_in(c, rest19); put("OutNineteen" + nm + "n", a_); put("OutNineteen" + nm + "d", b_)
    put("ElemNineteenData", met_in("C35", e19p)[0]); put("ElemNineteenCode", met_in("C36", e19p)[0])
    e4items = [x for x in items if x["tripod"] == 4]
    e4s = [100 * sum(S[r]["items"][str(x["idx"])] for x in e4items if str(x["idx"]) in S[r]["items"]) / n_
           for r in e4 for n_ in [sum(str(x["idx"]) in S.get(r, {}).get("items", {}) for x in e4items)] if n_]
    put("ElemFourMedian", f"{statistics.median(e4s):.1f}"); put("ElemFourMin", f"{min(e4s):.0f}"); put("ElemFourMax", f"{max(e4s):.0f}")
    a35, b35 = met("C35"); a36, b36 = met("C36"); put("DataAvail", a35); put("DataAvailPct", pct(a35, nC)); put("CodePublic", a36); put("CodePublicPct", pct(a36, nC))
    put("CkWFitMet", met("C22")[0]); put("CkWFitWhyNot", met("C22")[0] - sum(has(r, "SUR06", {"USED"}) and S.get(r, {}).get("items", {}).get(idx["C22"]) for r in CORE))
    put("CkWFitUsedMet", sum(bool(has(r, "SUR06", {"USED"}) and S.get(r, {}).get("items", {}).get(idx["C22"])) for r in CORE))
    put("CkWFitUsedNotMet", sum(has(r, "SUR06", {"USED"}) for r in CORE) - N["CkWFitUsedMet"])
    rk = lambda c: (sum(S[r]["items"][idx[c]] for r in rank if idx[c] in S.get(r, {}).get("items", {})), sum(idx[c] in S.get(r, {}).get("items", {}) for r in rank))
    put("RankSettings", rk("C38")[0]); put("RankStabReported", rk("C41")[0]); put("RankStabReportedPct", pct(rk("C41")[0], nR))
    put("RankScopeNotStated", rk("C42")[1] - rk("C42")[0])
    for nm, row in (("Stab", "Ranking stability checked"), ("Within", "All preprocessing within the training data"), ("WFit", "Weights used in model fitting")):
        put(nm + "PctD", pct(rows[row][3], pn[3]))
    # items met by fewer than 10% of studies, in increasing order (Results sentence, en / ko)
    PH = {"C36": ("public analysis code", ""), "C40": ("survey weights in aggregating participant-level importance", ""),
          "C27": ("information to reproduce the split", ""), "C30": ("survey weights in performance evaluation", ""),
          "C22": ("survey weights in model fitting", ""), "C15": ("missingness by variable or common pattern", ""),
          "C04": ("combined-year survey weights", ""), "C05": ("harmonising variables across years", ""),
          "C03": ("choice of survey weights", ""), "C33": ("strata and PSUs", ""), "C38": ("importance settings", ""),
          "C41": ("ranking stability", ""), "C19": ("class rebalancing", ""), "C17": ("special response codes", "")}
    def phrase(c, ko):
        a_, b_ = met(c); p_ = pct(a_, b_); nm = PH.get(c, (next(x["item_en"] for x in items if x["pub_id"] == c).lower(), next(x["item_ko"] for x in items if x["pub_id"] == c)))[ko]
        if c == "C40": return f"{nm}({p_}\\%,   {b_} )" if ko else f"{nm} ({p_}\\% of the {b_} studies to which it applied)"
  # percentages of applicable studies, as in the earlier text (only C40 states its denominator)
        return f"{nm}({p_}\\%)" if ko else f"{nm} ({p_}\\%)"
    lows = [c for _, c, _, _ in low]
    en = [phrase(c, 0) for c in lows]; kr = [phrase(c, 1) for c in lows]
    put("CkLowListEn", (", ".join(en[:-1]) + " and " + en[-1]) if len(en) > 1 else "".join(en))
    put("CkLowListKo", ", ".join(kr))
    # ---- survey design and preprocessing
    put("WMention", tot("Sampling weights mentioned")); put("WFit", tot("Weights used in model fitting")); put("WEval", tot("Weights used in performance evaluation"))
    put("Strata", tot("Strata or PSUs used in variance estimation")); put("StrataPct", pct(tot("Strata or PSUs used in variance estimation"), nC))
    put("PreWithin", tot("All preprocessing within the training data")); put("PreBefore", tot("At least one preprocessing step before the split"))
    put("PreScaleBefore", sum(fv(r, "PRE13") == "BEFORE" for r in CORE)); put("PreSelBefore", sum(fv(r, "PRE14") == "NOT_USED" for r in CORE))
    nostep = sum(all(fv(r, k) in ("NA", None) for k in ("PRE05", "PRE13", "PRE14", "IMB03")) for r in CORE); put("PreNone", nostep)
    put("PreUnclear", nC - tot("All preprocessing within the training data") - tot("At least one preprocessing step before the split") - nostep)
    # stability methods (studies describing how), three practices among the ranking studies
    stab = [r for r in rank if has(r, "VI16", {"USED"})]
    smc = collections.Counter(x["value"] for r in stab for x in recs[r]["protocol_items"].get("STAB_CAT", []))
    for k in ("RESAMPLE", "CYCLE", "SUBGROUP"): put("Stab" + k.title(), smc.get(k, 0))
    put("StabCycleWord", W.get(smc.get("CYCLE", 0), str(smc.get("CYCLE", 0))))
    pre_before = lambda r: fv(r, "PRE05") == "NOT_USED" or fv(r, "PRE14") == "NOT_USED" or fv(r, "PRE13") == "BEFORE" or fv(r, "IMB03") == "BEFORE"
    within = lambda r: not pre_before(r) and all(fv(r, k) in ("USED", "NA") for k in ("PRE05", "PRE14")) and fv(r, "PRE13") in ("WITHIN", "TRAIN", "NA") and fv(r, "IMB03") in ("WITHIN", "TRAIN", "NA")
    trio = [(has(r, "VI16", {"USED"}), has(r, "SUR06", {"USED"}), within(r)) for r in rank]
    put("RankAllThree", sum(all(t) for t in trio)); put("RankNoneThree", sum(not any(t) for t in trio))
    put("RankStab", sum(t[0] for t in trio)); put("RankWithin", sum(t[2] for t in trio))
    put("RankWFit", sum(has(r, "SUR06", {"USED"}) for r in rank)); put("RankWEval", sum(has(r, "SUR07", {"USED"}) for r in rank))
    put("RankStrata", sum(has(r, "SUR10", {"USED"}) for r in rank)); put("NoRank", nC - nR)
    # an appendix table of an earlier draft footnotes
    put("NAFit", sum(fv(r, "SUR06") == "NA" for r in CORE)); put("NAEval", sum(fv(r, "SUR07") == "NA" for r in CORE))
    na11 = [r for r in CORE if fv(r, "SUR11") == "NA"]
    put("NACombOneYear", sum(fv(r, "DAT08") == "ONE_YEAR" for r in na11)); put("NACombSeparate", sum(fv(r, "DAT08") != "ONE_YEAR" for r in na11))
    # C04 / C05 applicability composition (earlier-draft Figure 5 caption; review v14): from legacy_figdata na_composition
    nc = CK.get("na_composition", {}); cnt = lambda it, f: sum(v for k_, v in nc.get(it, {}).items() if not k_.startswith("applies") and f(k_))
    put("CFourNAOne", cnt("C04", lambda k_: "|ONE_YEAR|" in k_)); put("CFourNASep", cnt("C04", lambda k_: "|ONE_YEAR|" not in k_ and k_.endswith("SUR11=NA")))
    put("CFourNANoW", cnt("C04", lambda k_: "|ONE_YEAR|" not in k_ and k_.endswith("NOT_USED"))); put("CFiveNA", cnt("C05", lambda k_: True))
    put("CFiveNAOne", cnt("C05", lambda k_: "|ONE_YEAR|" in k_))
    for k in range(4):
        put("DevUnits" + "ABCD"[k], RT["units"]["development"][k]); put("EvalUnits" + "ABCD"[k], RT["units"]["evaluation"][k])
    put("NotRankNA", nC - nR)
    # topic mix by period (Monte Carlo chi-square, as in the earlier version: six topic groups, permutations of the topic labels)
    import numpy as np
    lm = {q["id"]: q["topic"] for q in O["literature_map"]}
    grp6 = {"MENTAL_HEALTH": 0, "METABOLIC_ENDOCRINE": 1, "CARDIOVASCULAR": 2, "MUSCULOSKELETAL": 3, "ORAL_HEALTH": 4}
    tlab = np.array([grp6.get(lm[r], 5) for r in CORE]); plab = np.array([per(year(r)) for r in CORE])
    def chi(t):
        tab = np.zeros((4, 6)); np.add.at(tab, (plab, t), 1)
        e = tab.sum(1, keepdims=True) * tab.sum(0, keepdims=True) / tab.sum()
        return (((tab - e) ** 2) / np.where(e > 0, e, 1)).sum()
    rng = np.random.default_rng(20261120); x0 = chi(tlab); B = 20000
    pv = (1 + sum(chi(rng.permutation(tlab)) >= x0 - 1e-12 for _ in range(B))) / (B + 1)
    put("TopicMixP", f"{pv:.2f}")
    rise = []
    for t in ("METABOLIC_ENDOCRINE", "MENTAL_HEALTH", "MUSCULOSKELETAL", "CARDIOVASCULAR"):
        g = [[r for r in P[k] if lm[r] == t] for k in (0, 3)]
        sh = [sum(has(r, "VI01", {"USED"}) for r in x) / len(x) if x else 0 for x in g]; rise.append(sh[1] > sh[0])
    put("RankRiseAllFourTopics", "yes" if all(rise) else "no")
    # Jaccard agreement (build_098 via legacy_figures.py) and named variables by outcome (earlier-draft Figure 4)
    da = O.get("domain_agreement_098", {}).get("without_age_sex_body_size", {})
    put("JacSame", f"{da.get('same_outcome', {}).get('median', 0):.2f}"); put("JacDiff", f"{da.get('different_topic', {}).get('median', 0):.2f}")
    rn = O.get("rankings_named_112", {}).get("rows", [])
    row = lambda g: next((x for x in rn if x["level"] != "topic" and x["group"] == g), {"n": 0, "counts": {}})
    su, di = row("suicide"), row("diabetes")
    put("SuicN", su["n"]); put("SuicDep", su["counts"].get("Depression or mood", 0))
    put("DiabN", di["n"]); put("DiabAge", di["counts"].get("Age", 0)); put("DiabWaist", di["counts"].get("Waist circumference or WHtR", 0))
    # how the item codings were settled (Methods, Verification): main coding + the two additional codings
    how = collections.Counter(); fields = set()
    for f in ("results/oct_search/coding/final_items_clean.jsonl", "results/oct_search/coding_legacy/final_items.jsonl", "results/oct_search/coding_legacy2/final_items.jsonl",
              "results/oct_search/coding_legacy3/final_items.jsonl"):
        for l in (open(f) if os.path.exists(f) else []):
            r = json.loads(l); h = r.get("how") or ""
            k = ("agree" if h.startswith("agree") else "consensus" if h.startswith("consensus") else
                 "field" if h.startswith(("field_rule", "rule_fix")) else "decision" if h.startswith("decision") else
                 "rule" if h.startswith(("rule_not_material", "verify_inconsistency", "triage", "rule_blind")) else "open")
            how[k] += 1; how["fallback"] += h in ("rule_fix_side", "rule_fix_unclear")
            if k == "field": fields.add(r["item"])
    ntot = sum(v for k_, v in how.items() if k_ != "fallback"); put("VCoded", f"{ntot:,}"); put("VAgree", f"{how['agree']:,}"); put("VAgreePct", pct(how["agree"], ntot))
    put("VConsensus", f"{how['consensus']:,}"); put("VRule", f"{how['rule']:,}"); put("VField", f"{how['field']:,}"); put("VFieldItems", len(fields))
    # studies represented by a preprint (no journal version; eligibility E4 admits preprints): DOI prefixes of preprint servers
    import csv as _csv
    _ln = {l["record_id"]: l["role"] for l in _csv.DictReader(open("results/oct_search/public/report_study_links.csv"))}
    _pre = re.compile(r"^10\.(21203|1101|2196/preprints|32388|20944|48550|2139|31219|36227|22541)")
    put("PreprintStudies", sum(_ln[r["record_id"]] == "representative" and bool(_pre.match(r["doi"] or "")) for r in _csv.DictReader(open("results/oct_search/public/included_reports.csv"))))
    put("VDecision", how["decision"]); put("VOpen", how["open"]); put("VFallback", how["fallback"])
    # linear record (step 4: cross-checks under the author's directions; step 5: decision): field rules agreed by both
    # systems belong to step 4, rules for fields without agreement (set under the author's direction) to step 5
    fst = {}
    for d in ("coding", "coding_legacy", "coding_legacy2", "coding_legacy3"):
        p = f"results/oct_search/{d}/field_rules_decided.json"
        if os.path.exists(p): fst.update({k_: v["status"] for k_, v in json.load(open(p)).items()})
    st4 = st5 = 0
    for f in ("results/oct_search/coding/final_items_clean.jsonl", "results/oct_search/coding_legacy/final_items.jsonl", "results/oct_search/coding_legacy2/final_items.jsonl",
              "results/oct_search/coding_legacy3/final_items.jsonl"):
        for l in (open(f) if os.path.exists(f) else []):
            r = json.loads(l); h = r.get("how") or ""
            if h.startswith(("rule_not_material", "verify_inconsistency", "triage", "rule_blind")) or (h.startswith("field_rule") and str(fst.get(r["item"])).startswith("agreed")): st4 += 1
            elif h.startswith(("field_rule", "rule_fix", "decision")): st5 += 1
    put("VStepFour", f"{st4:,}"); put("VStepFive", f"{st5:,}")
    # outcome and predictor set rebuildable from the report (OUT16 / PRD13 = R2), as in a supplementary figure of an earlier draft and an appendix table of an earlier draft
    _core = [recs[r] for r in REC["CORE"]]
    _o = sum(any(x["value"] == "R2" for x in d["protocol_items"].get("OUT16", [])) for d in _core)
    _p = sum(any(x["value"] == "R2" for x in d["protocol_items"].get("PRD13", [])) for d in _core)
    put("OutRebuild", _o); put("OutRebuildPct", pct(_o, len(_core))); put("PrdRebuild", _p); put("PrdRebuildPct", pct(_p, len(_core)))
    put("VFieldAgreedItems", sum(str(fst.get(i)).startswith("agreed") for i in fields)); put("VFieldDecidedItems", sum(not str(fst.get(i)).startswith("agreed") for i in fields))
    json.dump(N, open(f"{L}/legacy_numbers.json", "w"), indent=1, ensure_ascii=False)
    with open("manuscript/legacy_numbers.tex", "w") as f:
        f.write("% generated by tools/oct_search/legacy_numbers.py from results/oct_search/legacy_fig; do not edit\n")
        for k, v in N.items():
            f.write(f"\\newcommand{{\\k{macro(k)}}}{{{v}}}\n")
    print(len(N), "numbers")


def patch_table():
    """Numeric cells of an appendix table of an earlier draft in both manuscripts: header n and the 29 rows, in reporting_trends_v9 order."""
    pn = RT["period_n"]; n = sum(pn); rows = list(RT["rows"].values())
    cell = lambda a, b: f"{a} ({100 * a / b:.1f})"
    for p in ("manuscript/supp_S9_detailed_counts.tex",):  # a supplementary table of an earlier draft (formerly an appendix table of an earlier draft, author)
        s = open(p).read()
        i = s.index("\\begin{tabularx}"); j = s.index("\\end{tabularx}", i); t = s[i:j]
        t = re.sub(r"\(n=\d+\)", lambda m, it=iter(pn): f"(n={next(it)})", t, count=4)
        t = re.sub(r"\(N=\d+\)", f"(N={n})", t, count=1)
        it = iter(rows); out = []
        for line in t.split("\n"):
            cells = re.findall(r"\d+ \(\d+\.\d\)", line)
            if len(cells) == 5:
                v = next(it); new = [cell(v[k], pn[k]) for k in range(4)] + [cell(sum(v), n)]
                parts = re.split(r"\d+ \(\d+\.\d\)", line)
                line = "".join(x + (new[k] if k < 5 else "") for k, x in enumerate(parts))
            out.append(line)
        assert next(it, None) is None, p
        s = s[:i] + "\n".join(out) + s[j:]
        open(p, "w").write(s); print("table A1 patched", p)


if __name__ == "__main__":
    main()
    if "--table" in sys.argv: patch_table()
