"""Public Additional Data files, version 2 (author: each file holds ONE kind of data plus one description sheet;
reviewers must be able to read them; GitHub holds the codebook, rules and round logs).

  Additional Data 1  study-level dataset, one row per included study (279)              sheets README, Studies
                     reader columns first (final values behind the manuscript figures and numbers, including age range, candidate
                     predictors, missing-value handling, final model, tuning, preprocessing timing and AUROC with the
                     classification-study definitions), then the coded columns; recount_from_additional_data.py recomputes the
                     article's aggregates from Data 1-2 alone
  Additional Data 2  reporting assessment of the 217 classification studies, one row per study
                     (19 TRIPOD+AI-derived elements, 52 requirements, 43 proposed items in Table 1 order)   sheets README, Assessment
  Report-level reporting status, one row per eligible report (287): an intermediate coding record, not a journal attachment
                     (author); written to results/oct_search/public/reporting_status.csv and published by
                     github_package.py as 03_coding/reporting_status.csv of the public repository
  PROBAST+AI unit file  not written: the PROBAST+AI domain judgements are not recorded unit by unit (see check_probast_units)

Every value comes from the internal final data; nothing is typed by hand. Each reader column is checked against the
number macros of the manuscript (manuscript/legacy_numbers.tex; requirement macros of rewrite/round18/final/jce_main_v18.tex)
or against the figure data (rewrite/round3/03_manuscript_draft/figs/figure_data.json); the script stops on any mismatch.

Sources
  results/oct_search/legacy_fig/records.json                         study groups, protocol-shaped final codes (VI01, VI02, ...)
  results/oct_search/legacy_fig/results/derived/practice_trends_112.json   topics, ranking variables (Figures 2C, 5)
  results/oct_search/legacy_fig/results/derived/checklist_v22_scores.json  43 proposed items and 19 elements per study
  results/oct_search/coding_legacy{,2}/  (via legacy_figdata.load_final)   algorithms fitted / preferred (Figure 3D)
  results/oct_search/coding/final_items_clean.jsonl                  KNHANES survey years (rule of legacy_figdata.year_scope)
  results/oct_search/coding_legacy4/final_items.jsonl                52 TRIPOD+AI requirements x 217 studies
  tools/oct_search/item_definitions.json                             criteria and not-applicable conditions of the 19 elements,
                                                                     52 requirements and 43 items (README of Data 2; checked by ID and name)
  manuscript/KNHANES_ML_review_Additional_Data_1_oct.xlsx            coded columns (Studies), reporting status (Status),
                                                                     derivation rules (Derivation); written by build_excel.py
Output: manuscript/KNHANES_ML_review_Additional_Data_{1,2}.xlsx and results/oct_search/public/reporting_status.csv
(previous three-file version kept in manuscript/additional_data_before_v3/, the one before in manuscript/additional_data_before_v2/)
Usage: ~/knhanes_build_env/bin/python3 tools/oct_search/build_additional_data_v2.py"""
import ast, collections, glob, html, json, os, re, statistics, sys
from openpyxl import Workbook, load_workbook
from openpyxl.styles import Alignment, Font, PatternFill
from openpyxl.utils import get_column_letter

HERE = os.path.dirname(os.path.abspath(__file__)); ROOT = os.path.dirname(os.path.dirname(HERE)); os.chdir(ROOT)
sys.path.insert(0, HERE); sys.path.insert(0, os.path.join(ROOT, "tools"))
sys.path.insert(0, os.path.join(ROOT, "rewrite/round4/03_manuscript_draft"))
L = "results/oct_search/legacy_fig"; DER = f"{L}/results/derived"
REC = json.load(open(f"{L}/records.json")); recs = REC["records"]; CORE, ALL = REC["CORE"], REC["ALL"]
O = json.load(open(f"{DER}/practice_trends_112.json")); CK = json.load(open(f"{DER}/checklist_v22_scores.json"))
FD = json.load(open("rewrite/round3/03_manuscript_draft/figs/figure_data.json"))
MAC = dict(re.findall(r"\\newcommand\{\\k(\w+)\}\{([^}]*)\}", open("manuscript/legacy_numbers.tex").read()))
MAC.update(re.findall(r"\\newcommand\{\\k(Req\w+)\}\{([^}]*)\}", open("rewrite/round18/final/jce_main_v18.tex").read()))
OCT_XLSX = "manuscript/KNHANES_ML_review_Additional_Data_1_oct.xlsx"
REPO = "https://github.com/aipply-ahn/knhanes-ml-methodology-review"
CHECKS = []


def chk(name, got, want):
    """Stop unless got == want (want: a macro name 'k...' or a value)."""
    exp = MAC[want[1:]] if isinstance(want, str) and want.startswith("k") and want[1:] in MAC else want
    if isinstance(exp, str): exp = exp.replace(",", "")
    assert str(got) == str(exp), (name, got, want, exp)
    CHECKS.append(f"{name} = {got} ({want if isinstance(want, str) else 'figure data'})")


fv = lambda r, k: (recs[r]["protocol_items"].get(k) or [{}])[0].get("value")
has = lambda r, k, acc: any(x["value"] in acc for x in recs[r]["protocol_items"].get(k, []))
vals = lambda r, k: [x["value"] for x in recs[r]["protocol_items"].get(k, [])]
CORE_S = set(CORE)


def figure_labels(name):
    """A label dictionary of the figure script (TOPIC, DOMAIN), read as a literal so the labels match the figures."""
    src = open("rewrite/round3/03_manuscript_draft/figs/make_figures.py").read()
    for node in ast.parse(src).body:
        if isinstance(node, ast.Assign) and any(getattr(t, "id", None) == name for t in node.targets):
            return ast.literal_eval(node.value)
    raise KeyError(name)


TOPIC_LAB = figure_labels("TOPIC"); DOMAIN_LAB = figure_labels("DOMAIN")
YES, NO = "yes", "no"


# =========================================================================================== reader columns (Data 1)
def reader_columns():
    col = collections.defaultdict(dict)       # column -> rid -> value
    lm = {q["id"]: q for q in O["literature_map"]}
    assert set(lm) == set(ALL) and len(ALL) == 279
    # ---- study group (Figure 2B)
    G = {"core": "health-state classification", "other_health": "other health analysis", "method": "ML method study"}
    for r in ALL: col["study_group"][r] = G[lm[r]["group"]]
    c = collections.Counter(col["study_group"].values())
    chk("study_group classification", c[G["core"]], "kCore"); chk("study_group other health", c[G["other_health"]], "kOtherHealth")
    chk("study_group method", c[G["method"]], "kMethod")
    assert {r for r in ALL if lm[r]["group"] == "core"} == CORE_S
    # ---- publication period (all studies; manuscript periods)
    per = lambda y: 0 if y <= 2019 else 1 if y <= 2022 else 2 if y <= 2024 else 3
    for r in ALL: col["publication_period"][r] = O["periods"][per(recs[r]["metadata"]["publication_year"])]
    pc = collections.Counter(col["publication_period"][r] for r in CORE)
    for k, p in enumerate(O["periods"]): chk(f"period {p} (classification)", pc[p], "kPerN" + "ABCD"[k])
    # ---- primary health topic (Figure 2C; classification studies)
    for r in CORE: col["primary_health_topic"][r] = TOPIC_LAB[lm[r]["topic"]]
    tc = collections.Counter(lm[r]["topic"] for r in CORE)
    assert dict(tc) == FD["fig2C"]["topics"] and len(tc) == 17
    for code, m in (("METABOLIC_ENDOCRINE", "kTopMetabolic"), ("MENTAL_HEALTH", "kTopMental"), ("CARDIOVASCULAR", "kTopCardio"), ("MUSCULOSKELETAL", "kTopMusculo")):
        chk(f"topic {code}", tc[code], m)
    CHECKS.append("primary_health_topic: all 17 topic counts equal figure_data fig2C")
    # ---- outcome timing (Figure 2D)
    T = {"CURRENT": "same survey", "FUTURE": "later event", "UNC": "unclear"}
    for r in CORE: col["outcome_timing"][r] = T[fv(r, "OUT10")]
    c = collections.Counter(col["outcome_timing"][r] for r in CORE)
    chk("timing same survey", c["same survey"], "kSameSurvey"); chk("timing later", c["later event"], "kFuture"); chk("timing unclear", c["unclear"], "kTimingUnclear")
    # ---- survey years (Figure 3A): scope category + years by the rule of legacy_figdata.year_scope
    S = {"ONE_YEAR": "one survey year", "MULTI_SAME": "several years within one KNHANES cycle", "MULTI_CROSS": "several years across KNHANES cycles", "UNC": "unclear"}
    years = survey_years()
    for r in CORE:
        sc = fv(r, "DAT08"); ys = years.get(r)
        if ys: assert scope_of(ys) == sc, (r, ys, sc)          # the years printed are exactly those behind the category
        col["survey_years"][r] = S[sc] + (f": {span(ys)}" if ys else "")
    c = collections.Counter(fv(r, "DAT08") for r in CORE)
    chk("years one", c["ONE_YEAR"], "kYOne"); chk("years same cycle", c["MULTI_SAME"], "kYSame"); chk("years across cycles", c["MULTI_CROSS"], "kYCross"); chk("years unclear", c["UNC"], "kYUnc")
    # ---- algorithms fitted and preferred (Figure 3D)
    alg, pref = algorithms()
    FAM = [("logistic_regression", "logistic regression"), ("boosting", "boosting"), ("random_forest", "random forest"), ("decision_tree", "decision tree"),
           ("neural_network", "neural network"), ("svm", "SVM")]
    for r in CORE:
        fams = [lab for k, lab in FAM if k in alg[r]] + (["other"] if alg[r] - {k for k, _ in FAM} else [])
        col["algorithm_families_fitted"][r] = "; ".join(fams)
    af = O["algorithms_fitted_192"]
    for k, lab in FAM + [("other", "other")]:
        n = sum(lab in col["algorithm_families_fitted"][r].split("; ") for r in CORE)
        chk(f"fitted {k}", n, {"logistic_regression": "kAlgLR", "boosting": "kAlgBoost", "random_forest": "kAlgRF"}.get(k, af[k]))
    PREF = {"Not designated": "not designated", "single_algorithm": "single algorithm fitted (no comparison)", "Other": "other"}
    for r in CORE: col["preferred_algorithm_family"][r] = PREF.get(pref[r], dict(FAM).get(pref[r].lower().replace(" ", "_"), pref[r]))
    pc = collections.Counter(pref[r] for r in CORE); sm = O["selected_model_family_192"]
    for k in sm:
        if k != "n": chk(f"preferred {k}", pc[k], {"Boosting": "kSelBoost", "single_algorithm": "kSingleAlg"}.get(k, sm[k]))
    # ---- evaluation design (Figure 3E): VAL02 codes
    V = [("SPLIT", "train-test split"), ("CV", "cross-validation"), ("BOOT", "bootstrap"), ("EXTERNAL", "external validation"),
         ("TEMPORAL", "temporal validation"), ("APPARENT", "apparent performance only"), ("OTHER", "other"), ("NONE_NR", "none or not reported")]
    assert {v for r in CORE for v in vals(r, "VAL02")} <= dict(V).keys()
    for r in CORE: col["evaluation_design"][r] = "; ".join(lab for k, lab in V if has(r, "VAL02", {k}))
    chk("evaluation split", sum(has(r, "VAL02", {"SPLIT"}) for r in CORE), "kSplit"); chk("evaluation CV", sum(has(r, "VAL02", {"CV"}) for r in CORE), "kCV")
    chk("evaluation beyond development data", sum(has(r, "VAL02", {"EXTERNAL", "TEMPORAL"}) for r in CORE), "kBeyond")
    # ---- survey weights in model fitting (Figure 3A, Table 2)
    W = {"USED": YES, "NOT_USED": "no (stated not used)", "NR": "not reported", "UNC": "unclear", "NA": "not applicable"}
    for r in CORE: col["survey_weights_in_fitting"][r] = W[fv(r, "SUR06")]
    chk("survey weights in fitting", sum(col["survey_weights_in_fitting"][r] == YES for r in CORE), "kWFit")
    # ---- variable-importance rankings (Figures 4, 5)
    rank = [r for r in CORE if has(r, "VI01", {"USED"})]; rk = set(rank)
    for r in CORE: col["ranking_study"][r] = YES if r in rk else NO
    chk("ranking studies", len(rank), "kRanking")
    M = [("SHAP", "SHAP"), ("MODEL_NATIVE", "model-native importance"), ("TREE_RULE", "tree or rule structure"), ("PERMUTATION", "permutation importance"),
         ("COEFFICIENT_STATISTIC", "coefficient or test statistic"), ("LIME", "LIME"), ("PDP", "partial dependence"), ("ALE", "accumulated local effects"),
         ("ICE", "individual conditional expectation"), ("NETWORK_SPECIFIC", "network-specific method"), ("PERTURBATION_ABLATION", "perturbation or ablation"), ("OTHER", "other")]
    for r in rank:
        v = set(vals(r, "VI02")) - {"NA", "NR", "UNC"}; assert v <= dict(M).keys(), (r, v)
        col["importance_methods"][r] = "; ".join(lab for k, lab in M if k in v) or "not reported"
    for lab, n in FD["fig4B"]["methods"].items():
        codes = {"Model-native": {"MODEL_NATIVE"}, "Tree or rule": {"TREE_RULE"}, "Coefficient or test statistic": {"COEFFICIENT_STATISTIC"},
                 "Other": {"PDP", "ALE", "ICE", "NETWORK_SPECIFIC", "PERTURBATION_ABLATION", "OTHER"}}.get(lab, {lab.upper()})
        chk(f"importance method {lab}", sum(bool(set(vals(r, "VI02")) & codes) for r in rank), "kShap" if lab == "SHAP" else n)
    for r in rank:
        d = [k for k in DOMAIN_LAB if k in set(vals(r, "VI07"))]
        col["important_variable_domains"][r] = "; ".join(DOMAIN_LAB[k] for k in d) or "none classifiable"
    dc = collections.Counter(k for r in rank for k in set(vals(r, "VI07")))
    for k, n in FD["fig5A"]["domains"].items():
        chk(f"domain {k}", dc[k], {"AGE": "kDomAge", "ADIPOSITY_BODY_SIZE": "kDomBody", "SOCIOECONOMIC": "kDomSes"}.get(k, n))
    vps = O["rankings_named_112"]["variables_per_study"]; assert set(vps) == rk
    for r in rank: col["important_variables_harmonised"][r] = "; ".join(vps[r]) or "none harmonised"
    vc = collections.Counter(v for r in rank for v in vps[r])
    assert dict(vc) == {k: n for k, n in O["rankings_named_112"]["all"]["counts"].items() if n}
    CHECKS.append("important_variables_harmonised: counts of all harmonised variables equal Figure 5B 'all ranking studies' row")
    for r in CORE:
        col["ranking_stability_checked"][r] = (YES if has(r, "VI16", {"USED"}) else NO) if r in rk else "not applicable (no ranking)"
    stab = [r for r in rank if has(r, "VI16", {"USED"})]
    chk("ranking stability checked", len(stab), "kRankStab"); chk("ranking stability checked (Figure 4D)", len(stab), "kStab")
    SC = [("SUBGROUP", "subgroups"), ("RESAMPLE", "resamples"), ("CYCLE", "survey cycles")]
    for r in stab: col["stability_compared_across"][r] = "; ".join(lab for k, lab in SC if has(r, "STAB_CAT", {k}))
    for k, m in (("SUBGROUP", "kStabSubgroup"), ("RESAMPLE", "kStabResample"), ("CYCLE", "kStabCycle")):
        chk(f"stability across {k}", sum(has(r, "STAB_CAT", {k}) for r in stab), m)
    # ---- outcome group (Figure 5B rows): ranking studies in a topic that Figure 5B splits by outcome
    og = {}
    for row in O["rankings_named_112"]["rows"]:
        if row["level"] == "outcome":
            for i in row["ids"]:
                assert i not in og; og[i] = row["group"] if row["group"] != "other" else f"other {TOPIC_LAB[row['topic']].lower()} outcome"
    # verification round 2: topics that Figure 5B does not split by outcome are one row each, and the
    # remaining topics are pooled, so every ranking study carries the Figure 5B row it is counted in
    for row in O["rankings_named_112"]["rows"]:
        if row.get("leaf"):
            lab = "other topics" if row["topic"] == "OTHER_TOPICS" else f"all {TOPIC_LAB[row['topic']].lower()} outcomes"
            for i in row["ids"]:
                assert i not in og; og[i] = lab
    assert set(og) == rk
    for r, g in og.items(): col["outcome_group"][r] = g
    rows5 = {(x["topic"], x["group"]): x["n"] for x in O["rankings_named_112"]["rows"] if x["level"] == "outcome"}
    gc = collections.Counter(og.values())
    for (t, g), n in rows5.items(): assert gc[g if g != "other" else f"other {TOPIC_LAB[t].lower()} outcome"] == n
    chk("outcome group diabetes", gc["diabetes"], "kDiabN"); chk("outcome group suicide", gc["suicide"], "kSuicN")
    CHECKS.append(f"outcome_group: {len(og)} ranking studies, group sizes equal the Figure 5B rows")
    return col


def analysis_columns(col):
    """Reader columns for the remaining classification-study quantities of the manuscript and of the period rows behind
    Figure 3 (round 20 regeneration check: age range, candidate predictors, missing-value handling, final model, tuning,
    preprocessing timing and AUROC had no column with the classification-study definition), plus the outcome form and the
    subgroups of the non-classification studies (Figure 2B). Each value is the final internal value behind the macro; the
    per-period counts are asserted against the rows of reporting_trends_v9.json (period counts of the Results and Figure 3F)."""
    RT = json.load(open(f"{DER}/reporting_trends_v9.json")); RTR = RT["rows"]
    per = lambda r: (lambda y: 0 if y <= 2019 else 1 if y <= 2022 else 2 if y <= 2024 else 3)(recs[r]["metadata"]["publication_year"])
    def byp(rows, f, name):   # one period row, recomputed from the column, per period
        got = [sum(bool(f(r)) for r in CORE if per(r) == k) for k in range(4)]
        assert got == RTR[rows], (name, got, RTR[rows]); CHECKS.append(f"{name}: per-period counts {got} equal the period row '{rows}' of reporting_trends_v9.json")
    # ---- study subgroups of the non-classification studies (Figure 2B; rules of legacy_figdata.health_kind / method_kind)
    HEALTH, METHOD = REC["HEALTH"], REC["METHOD"]
    F = legacy_final()
    for r in HEALTH:
        if r in CORE_S: continue
        t = fv(r, "TSK01"); txt = " ".join(v for _, v in lunits("legacy.task", r)).lower()
        col["study_subgroup"][r] = "continuous or ordered outcome" if t == "CONT" or "continuous" in txt or "ordered" in txt else "other analysis"
    for r in METHOD:
        t = " ".join(v for _, v in lunits("legacy.study_category", r)).lower() + " " + (F["legacy.study_category"].get(r, (0, {}))[1] or {}).get("rationale", "").lower()
        col["study_subgroup"][r] = "compares existing methods" if "compare_existing" in t else "develops or improves a method"
    c = collections.Counter(col["study_subgroup"].values())
    chk("other health: continuous or ordered", c["continuous or ordered outcome"], "kOtherCont"); chk("other health: other", c["other analysis"], "kOtherOther")
    chk("method: develop or improve", c["develops or improves a method"], "kMethDev"); chk("method: compare existing", c["compares existing methods"], "kMethCmp")
    # ---- outcome form (Figure 3B)
    OF = {"BINARY": "binary", "MULTIBIN": "several binary outcomes", "MULTICLASS": "multiclass", "MIXED": "mixed"}
    for r in CORE: col["outcome_form"][r] = OF.get(lfirst("legacy.outcome_structure", r, "BINARY"), "unclear")
    c = collections.Counter(col["outcome_form"][r] for r in CORE)
    chk("outcome form binary", c["binary"], "kOutBinary"); chk("outcome form several binary", c["several binary outcomes"], "kOutMultibin")
    FD3 = FD["fig3B"]["form"]
    assert (c["multiclass"], c["mixed"], c["unclear"]) == (FD3["Multiclass"], FD3["Mixed"], FD3["Unclear"]), c
    # ---- age range (POP03 / POP04 of records.json; Figure 3B bands, 'Age range reported')
    def age_cell(v):
        v = str(v or "NR")
        if v == "NR": return "not reported"
        assert re.fullmatch(r"\d+(\.\d+)?", v), v
        x = float(v); return int(x) if x == int(x) else x
    for r in CORE:
        col["age_min_years"][r] = age_cell(fv(r, "POP03")); col["age_max_years"][r] = age_cell(fv(r, "POP04"))
    byp("Age range reported", lambda r: col["age_min_years"][r] != "not reported" or col["age_max_years"][r] != "not reported", "age range reported")
    chk("age range reported", sum(col["age_min_years"][r] != "not reported" or col["age_max_years"][r] != "not reported" for r in CORE), sum(RTR["Age range reported"]))
    band = collections.Counter()
    for r in CORE:   # the age bands of Figure 3 (legacy_numbers.py)
        m = re.search(r"\d+", str(col["age_min_years"][r])); lo = int(m.group(0)) if m else None
        m2 = re.search(r"\d+", str(col["age_max_years"][r])); hi = int(m2.group(0)) if m2 else None
        band["nr" if lo is None and hi is None else "u19" if hi is not None and hi < 19 else "all" if lo is not None and lo < 18 else "nr" if lo is None
             else "a60" if lo >= 60 else "a30" if lo >= 30 else "a19"] += 1
    for k, m in (("a19", "kAgeNineteen"), ("a30", "kAgeThirty"), ("a60", "kAgeSixty"), ("nr", "kAgeNR"), ("u19", "kAgeUnder"), ("all", "kAgeAll")): chk(f"age band {k}", band[k], m)
    # ---- number of candidate predictors (legacy.candidate_predictors, first number)
    for r in CORE:
        x = num(lfirst("legacy.candidate_predictors", r, ""))
        col["candidate_predictors_n"][r] = "not reported" if x is None else int(x) if x == int(x) else x
    cp = [col["candidate_predictors_n"][r] for r in CORE if col["candidate_predictors_n"][r] != "not reported"]
    byp("Number of candidate predictors reported", lambda r: col["candidate_predictors_n"][r] != "not reported", "candidate predictors reported")
    chk("candidate predictors reported", len(cp), "kCandReported"); chk("candidate predictors median", f"{statistics.median(cp):g}", "kCandMedian")
    chk("candidate predictors not reported", len(CORE) - len(cp), "kCandNR")
    # ---- missing-value handling (legacy.missing_handling)
    MH = {"complete_case": "complete-case analysis", "single_imputation": "single imputation", "multiple_imputation": "multiple imputation",
          "model_native": "handled within the algorithm", "not_reported": "not reported"}
    for r in CORE: col["missing_value_handling"][r] = MH.get(lfirst("legacy.missing_handling", r, "not_reported"), "other or several methods")
    c = collections.Counter(col["missing_value_handling"][r] for r in CORE)
    byp("Missing-value handling reported", lambda r: col["missing_value_handling"][r] != "not reported", "missing-value handling reported")
    chk("missing: complete case", c["complete-case analysis"], "kMissCC"); chk("missing: not reported", c["not reported"], "kMissNR")
    fm = FD["fig3C_missing"]
    assert [c[x] for x in ("single imputation", "multiple imputation", "handled within the algorithm", "other or several methods")] == \
        [fm["Single imputation"], fm["Multiple imputation"], fm["Handled within the algorithm"], fm["Other or several methods"]], c
    # ---- final model fully specified (legacy.final_model_specified)
    FM = {"R": YES, "P": "partly", "NR": "not reported"}
    for r in CORE: col["final_model_fully_specified"][r] = FM[lfirst("legacy.final_model_specified", r)]
    byp("Final model fully specified", lambda r: col["final_model_fully_specified"][r] == YES, "final model fully specified")
    # ---- tuning kept apart from the final evaluation (legacy.tuning_kept_apart; NA = no tuning counts as kept apart)
    TK = {"USED": YES, "NOT_USED": "no (evaluation data used for tuning or selection)", "NR": "not reported", "NA": "not applicable (no tuning)"}
    for r in CORE: col["tuning_kept_apart"][r] = TK[lfirst("legacy.tuning_kept_apart", r)]
    kept = lambda r: col["tuning_kept_apart"][r] in (YES, TK["NA"])
    byp("Tuning kept apart from the final evaluation", kept, "tuning kept apart")
    chk("tuning kept apart", sum(kept(r) for r in CORE), FD["fig6A"]["Tuning, model selection or threshold kept apart from the final evaluation"])
    # ---- preprocessing timing (PRE05, PRE13, PRE14, IMB03; legacy_figdata pre_before / pre_all_within; legacy_numbers PreNone)
    pre_before = lambda r: fv(r, "PRE05") == "NOT_USED" or fv(r, "PRE14") == "NOT_USED" or fv(r, "PRE13") == "BEFORE" or fv(r, "IMB03") == "BEFORE"
    within = lambda r: not pre_before(r) and all(fv(r, k) in ("USED", "NA") for k in ("PRE05", "PRE14")) and fv(r, "PRE13") in ("WITHIN", "TRAIN", "NA") and fv(r, "IMB03") in ("WITHIN", "TRAIN", "NA")
    nostep = lambda r: all(fv(r, k) in ("NA", None) for k in ("PRE05", "PRE13", "PRE14", "IMB03"))
    PT = ("all steps within the training data", "at least one step before the split", "no preprocessing step", "timing unclear")
    for r in CORE:
        k = 0 if within(r) else 1 if pre_before(r) else 2 if nostep(r) else 3
        assert not (within(r) and nostep(r)) or k == 0
        col["preprocessing_timing"][r] = PT[k]
    c = collections.Counter(col["preprocessing_timing"][r] for r in CORE)
    byp("All preprocessing within the training data", lambda r: col["preprocessing_timing"][r] == PT[0], "preprocessing all within training data")
    byp("At least one preprocessing step before the split", lambda r: col["preprocessing_timing"][r] == PT[1], "preprocessing step before split")
    chk("preprocessing within", c[PT[0]], "kPreWithin"); chk("preprocessing before", c[PT[1]], "kPreBefore")
    chk("preprocessing none", c[PT[2]], "kPreNone"); chk("preprocessing unclear", c[PT[3]], "kPreUnclear")
    # ---- AUROC reported (performance rows of the coding, metric classified as AUROC)
    for r in CORE: col["auroc_reported"][r] = YES if any(m_["metric"] == "AUROC" for m_ in recs[r]["performance_metrics"]) else NO
    byp("AUROC reported", lambda r: col["auroc_reported"][r] == YES, "AUROC reported")
    chk("AUROC reported", sum(col["auroc_reported"][r] == YES for r in CORE), "kAuroc")
    return col


def survey_years():
    """KNHANES survey years per study: the year-reading rule of legacy_figdata.year_scope (copied verbatim below), applied to
    the coded survey years (data_source.survey_cycles); {} when no year is printed."""
    main_rows = collections.defaultdict(dict)
    for l in open("results/oct_search/coding/final_items_clean.jsonl"):
        r = json.loads(l)
        if r["item"] == "data_source.survey_cycles" and r.get("final"): main_rows[r["record_id"]] = r["final"]
    out = {}
    for rid in CORE:
        x = main_rows.get(rid) or {}; ys = set()
        for v in x.get("values") or []:
            if re.match(r"\s*NHANES", str(v.get("unit", ""))): continue
            t = str(v.get("value", ""))
            spn = r""
            sp = [(int(m_.group(2)), int(m_.group(3)) if len(m_.group(3)) == 4 else int(m_.group(2)[:2] + m_.group(3))) for m_ in re.finditer(spn, t)]
            t_ = re.sub(spn, r"\1", t); rest = [int(y) for y in re.findall(r"(?<!\d)((?:19|20)\d\d)(?!\d)", t_)]
            if sp and rest and all(any(a0 <= y <= b0 for a0, b0 in sp) for y in rest): t = t_
            for a_, b_ in re.findall(r"(?<!\d)((?:19|20)\d\d)\s*(?:[-–—~∼～]|to|through|and)\s*((?:19|20)?\d\d)(?!\d)", t):
                a1, b1 = int(a_), int(b_) if len(b_) == 4 else int(a_[:2] + b_)
                if 1998 <= a1 <= b1 <= 2027 and " and " not in t[t.find(a_):t.find(a_) + 12]: ys.update(range(a1, b1 + 1))
            ys.update(int(y) for y in re.findall(r"(?<!\d)((?:19|20)\d\d)(?!\d)", t) if 1998 <= int(y) <= 2027)
        ys = {y for y in ys if y in CYC}
        if ys: out[rid] = ys
    return out


CYC = {1998: 1, 2001: 2, 2005: 3, **{y: 4 for y in (2007, 2008, 2009)}, **{y: 5 for y in (2010, 2011, 2012)}, **{y: 6 for y in (2013, 2014, 2015)},
       **{y: 7 for y in (2016, 2017, 2018)}, **{y: 8 for y in (2019, 2020, 2021)}, **{y: 9 for y in (2022, 2023, 2024)}, **{y: 10 for y in (2025, 2026, 2027)}}
scope_of = lambda ys: "ONE_YEAR" if len(ys) == 1 else "MULTI_SAME" if len({CYC[y] for y in ys}) == 1 else "MULTI_CROSS"


def span(ys):
    ys = sorted(ys); runs = [[ys[0], ys[0]]]
    for y in ys[1:]:
        if y == runs[-1][1] + 1: runs[-1][1] = y
        else: runs.append([y, y])
    return ", ".join(str(a) if a == b else f"{a}–{b}" for a, b in runs)


_LEG = {}


def legacy_final():
    """Final values of the additional (legacy) items, read as legacy_figdata.py reads them (same files, same order:
    coding_legacy, coding_legacy2, then the author decisions)."""
    if not _LEG:
        import legacy_figdata as lf
        reps = set(open("results/oct_search/coding_legacy/reps.txt").read().split())
        F = {}
        for folder in ("results/oct_search/coding_legacy", "results/oct_search/coding_legacy2"): F.update(lf.load_final(folder, reps))
        for f in sorted(glob.glob("results/oct_search/coding_legacy/author_decisions_*.json")):
            for d in json.load(open(f)):
                if d["record_id"] in reps: F.setdefault(d["item"], {})[d["record_id"]] = ("author_decision", d["final"])
        _LEG["F"] = F
    return _LEG["F"]


def lunits(item, rid):
    """[(unit, value)] of a legacy item (legacy_figdata.units)."""
    x = legacy_final().get(item, {}).get(rid, (None, None))[1]
    if not x: return []
    v = [(u.get("unit", ""), str(u.get("value", "")).strip()) for u in (x.get("values") or []) if str(u.get("value", "")).strip()]
    return v or [("", {"not_applicable": "NA", "not_reported": "NR", "unclear": "UNC"}.get(x.get("status"), "NR"))]


def codes(item, rid):
    """Response codes of a legacy item (legacy_figdata.codes)."""
    return [c.split(":")[0].strip() for _, t in lunits(item, rid) for c in re.split(r"\s*;\s*", t) if c.strip()]


def lfirst(item, rid, default="NR"):
    c = codes(item, rid)
    return c[0] if c else default


def num(x):
    """First number in a value (legacy_figdata.num)."""
    m_ = re.search(r"\d[\d,]*\.?\d*", str(x or "").replace(",", ""))
    return float(m_.group(0)) if m_ else None


def algorithms():
    """Families fitted and the author-preferred family as in Figure 3D (rules of legacy_figdata.py, same final values)."""
    selmap = {"boosting": "Boosting", "random forest": "Random forest", "logistic regression": "Logistic regression", "decision tree": "Decision tree",
              "svm": "SVM", "neural network": "Neural network", "single_algorithm": "single_algorithm", "not designated": "Not designated"}
    alg = {r: set(c.split("(")[0].strip().lower().replace(" ", "_") for c in codes("legacy.algorithms_fitted", r)) for r in CORE}
    pref = {r: selmap.get((codes("legacy.selected_model", r) or ["Other"])[0].lower(), "Other") for r in CORE}
    # the same final values as records.json (consistency of the two read paths)
    for r in CORE: assert fv(r, "TSK01") == (codes("legacy.task", r) or ["NR"])[0], r
    return alg, pref


# =========================================================================================== Data 2 (reporting assessment)
def assessment():
    import item_ids as II
    items = CK["items"]; S = CK["studies"]; assert set(S) == CORE_S
    byc = {x["pub_id"]: x for x in items}
    EL = {e["element"]: e["name"] for e in FD["fig6"]["elements"]}
    LEV = {"Reported": "complete", "Partly reported": "partial", "Not reported": "not reported"}
    REQ = collections.defaultdict(dict)
    for l in open("results/oct_search/coding_legacy4/final_items.jsonl"):
        x = json.loads(l); f = x["final"]; k = x["item"].rsplit(".", 1)[1]
        v = f["values"][0]["value"] if f["values"] else f["status"]
        REQ[k][x["record_id"]] = {"met": "met", "not_met": "not met", "not_applicable": "not applicable", "unclear": "unclear", "not_reported": "unclear"}[v]
    reqs = [f"{e}{II.L[i]}" for e in range(1, 20) for i in range(len(II.COMP[e]))]
    assert sorted(REQ) == sorted(reqs) and len(reqs) == int(MAC["ReqN"]) and all(set(REQ[k]) == CORE_S for k in reqs)
    cols = []                                                     # (header, kind, key, label)
    for e in range(1, 22):
        if e <= 19: cols.append((f"element {e}", "element", e, EL[e]))
        for kind, key, disp, *_ in II.ROWS[e]:
            if kind == "base": cols.append((key, "requirement", key, II.COMP[e][II.L.index(key[-1])][0]))
            else: cols.append((II.DISP[key], "item", key, byc[key]["item_en"]))
    assert sum(c[1] == "element" for c in cols) == 19 and sum(c[1] == "requirement" for c in cols) == 52 and sum(c[1] == "item" for c in cols) == 43
    rows = {}
    for r in CORE:
        it = S[r]["items"]; v = {}
        for h, kind, key, _ in cols:
            if kind == "element": v[h] = LEV[S[r]["tripod"][str(key)]]
            elif kind == "requirement": v[h] = REQ[key][r]
            else:
                i = str(byc[key]["idx"]); v[h] = "not applicable" if i not in it else ("met" if it[i] else "not met")
        ne = sum(v[f"element {e}"] == "complete" for e in range(1, 20))
        app = [x for x in it.values()]
        v["elements_complete_n"] = ne; v["proposed_items_met_pct"] = round(100 * sum(app) / len(app), 1)
        rows[r] = v
    # ---- checks against the manuscript
    for e in FD["fig6"]["elements"]:
        c = collections.Counter(rows[r][f"element {e['element']}"] for r in CORE)
        assert (c["complete"], c["partial"], c["not reported"]) == (e["complete"], e["partial"], e["not_reported"]), e
    CHECKS.append("19 elements: complete/partial/not reported counts equal figure_data fig6")
    for i, m in ((8, "kRepCounts"), (6, "kRepOutcomeDef"), (17, "kRepFinalModel"), (9, "kRepSampleSize"), (19, "kRepRegistration"), (4, "kElemFourComplete"), (11, "kElemElevenComplete")):
        chk(f"element {i} complete", sum(rows[r][f"element {i}"] == "complete" for r in CORE), m)
    chk("element 19 partial", sum(rows[r]["element 19"] == "partial" for r in CORE), "kElemNineteenPartly")
    ne = [rows[r]["elements_complete_n"] for r in CORE]
    chk("elements complete median", f"{statistics.median(ne):g}", "kTripodMedian"); chk("elements complete min", min(ne), "kTripodMin"); chk("elements complete max", max(ne), "kTripodMax")
    T = json.load(open("results/oct_search/coding_legacy4/tripod_requirement_counts.json"))
    for k in reqs:
        c = collections.Counter(rows[r][k] for r in CORE)
        assert c["met"] == T[k].get("met", 0) and len(CORE) - c["not applicable"] == T[k]["applicable"], (k, c, T[k])
    CHECKS.append("52 requirements: met and applicable counts equal coding_legacy4/tripod_requirement_counts.json")
    chk("requirements", len(reqs), "kReqN"); chk("requirement codings", len(reqs) * len(CORE), "kReqCodings")
    chk("requirement 19a met", sum(rows[r]["19a"] == "met" for r in CORE), "kReqRegistration"); chk("requirement 9a met", sum(rows[r]["9a"] == "met" for r in CORE), "kReqSampleSize")
    # requirement vs its refinement (Results): among studies where the refinement applies, requirement met and refinement met
    pairs = {(a, b): (n, m1, m2) for a, b, n, m1, m2 in json.load(open("results/oct_search/coding_legacy4/req_vs_refined.json"))}
    for (k, c), (n, m1, m2) in pairs.items():
        ap = [r for r in CORE if rows[r][c] != "not applicable"]
        got = (len(ap), sum(rows[r][k] == "met" for r in ap), sum(rows[r][k] == "met" and rows[r][c] == "met" for r in ap))
        assert got == (n, m1, m2), (k, c, got, (n, m1, m2))
    CHECKS.append(f"{len(pairs)} requirement/refinement pairs equal coding_legacy4/req_vs_refined.json")
    for k, c, m in (("4b", "4b′", "kReqDesign"), ("11a", "11a′", "kReqPrep"), ("6a", "6a′", "kReqOutcome"), ("14b", "14b″", "kReqMetrics")):
        n, m1, m2 = pairs[(k, c)]; chk(f"requirement {k} met (refinement applicable)", m1, m + "Met"); chk(f"refinement {c} met", m2, m + "Refined")
    P = sorted(100 * sum(rows[r][k] == "met" for r in CORE) / (len(CORE) - sum(rows[r][k] == "not applicable" for r in CORE)) for k in reqs)
    chk("requirements median % met", f"{statistics.median(P):.1f}", "kReqMedianPct"); chk("requirements met by <50%", sum(p < 50 for p in P), "kReqBelowHalf")
    dig = "Zero One Two Three Four Five Six Seven Eight Nine".split()
    for code, x in byc.items():
        h = II.DISP[code]; n = sum(rows[r][h] == "met" for r in CORE); d = sum(rows[r][h] != "not applicable" for r in CORE)
        mn = "kCk" + re.sub(r"\d", lambda m_: dig[int(m_.group(0))], code)
        chk(f"item {h} ({code}) met", n, mn + "n"); chk(f"item {h} ({code}) applicable", d, mn + "d")
    sc = [rows[r]["proposed_items_met_pct"] for r in CORE]
    sc_exact = [100 * sum(S[r]["items"].values()) / len(S[r]["items"]) for r in CORE]
    chk("proposed items % met median", f"{statistics.median(sc_exact):.1f}", "kCkMedian"); chk("min", f"{min(sc_exact):.1f}", "kCkMin"); chk("max", f"{max(sc_exact):.1f}", "kCkMax")
    return cols, rows


# =========================================================================================== PROBAST+AI unit totals
def check_probast_units():
    """Check the PROBAST+AI unit totals against the article and count how many units carry a judgement for all four domains
    under the same unit label. The unit-level judgements themselves are written by export_probast_units.py."""
    out = {}
    for pre, mac in (("PD", "kDevUnits"), ("PE", "kEvalUnits")):
        n = linked = 0
        for r in CORE:
            pi = recs[r]["protocol_items"]
            ov = [x["unit"] for x in pi.get(f"U:{pre}_OVERALL", []) if x["value"] != "NA"]; n += len(ov)
            dm = [{x["unit"] for x in pi.get(f"U:{pre}_D{i}", [])} for i in range(1, 5)]
            linked += sum(all(u in d for d in dm) for u in ov)
        chk(f"PROBAST+AI {pre} units", n, mac); out[pre] = (n, linked)
    return out


# =========================================================================================== workbook helpers
def clean(s):
    if s is None: return None
    s = html.unescape(str(s)).replace("\u00a0", " ").replace("\u2009", " ")
    return re.sub(r"\s+", " ", s).strip()


HEAD = Font(bold=True); WRAP = Alignment(wrap_text=True, vertical="top"); TOP = Alignment(vertical="top")
FILL_R = PatternFill("solid", fgColor="DDEBF7"); FILL_C = PatternFill("solid", fgColor="EDEDED")


def write_sheet(ws, header, rows, fills=None, freeze="B2", maxw=45):
    ws.append(header)
    for c, h in enumerate(header, start=1):
        cell = ws.cell(row=1, column=c); cell.font = HEAD; cell.alignment = WRAP
        if fills: cell.fill = fills[c - 1]
    for row in rows: ws.append(row)
    for c, h in enumerate(header, start=1):
        w = max([len(str(h))] + [len(str(r[c - 1])) for r in rows[:400] if r[c - 1] is not None])
        ws.column_dimensions[get_column_letter(c)].width = max(8, min(w + 2, maxw))
    ws.freeze_panes = freeze; ws.auto_filter.ref = ws.dimensions


def write_readme(ws, blocks, widths=(30, 60, 45, 70)):
    """blocks: list of ('title'|'para'|'table', content)."""
    r = 1
    for kind, content in blocks:
        if kind == "title":
            ws.cell(row=r, column=1, value=content).font = Font(bold=True, size=13); r += 2
        elif kind == "head":
            ws.cell(row=r, column=1, value=content).font = HEAD; r += 1
        elif kind == "para":
            c = ws.cell(row=r, column=1, value=content); c.alignment = WRAP
            ws.merge_cells(start_row=r, start_column=1, end_row=r, end_column=4)
            ws.row_dimensions[r].height = 15 * max(1, len(content) // 150 + 1); r += 2
        elif kind == "table":
            for i, row in enumerate(content):
                for j, v in enumerate(row, start=1):
                    c = ws.cell(row=r, column=j, value=v); c.alignment = WRAP
                    if i == 0: c.font = HEAD
                r += 1
            r += 1
    for j, w in enumerate(widths, start=1): ws.column_dimensions[get_column_letter(j)].width = w


# =========================================================================================== Data 1
READER = [  # column, definition, allowed values, how derived
    ("study_id", "Study identifier (one study may have several reports; see all_reports)", "S_OCT####", "Assigned at selection"),
    ("title_display", "Title of the representative report, for display (HTML entities and non-breaking spaces normalised)", "text", "Bibliographic record"),
    ("journal_display", "Journal or venue, for display (HTML entities normalised)", "text", "Bibliographic record"),
    ("publication_period", "Publication period used in the manuscript", "≤2019; 2020–2022; 2023–2024; 2025–2026", "Publication year of the representative report"),
    ("study_group", "Study group of Figure 2B", "health-state classification; other health analysis; ML method study",
     "Final study category (health analysis vs ML method research) and, for health analyses, the final task (classification vs other)"),
    ("study_subgroup", "Subgroup of the studies that are not health-state classification studies (Figure 2B)",
     "other health analyses: continuous or ordered outcome; other analysis. ML method studies: develops or improves a method; compares existing methods",
     "Final coded task (other health analyses) and final study category with its kind (ML method studies); blank for classification studies"),
    ("primary_health_topic", "Primary health topic of Figure 2C (17 topics)", "one of the 17 topic labels of Figure 2C", "Final topic classification; classification studies only"),
    ("outcome_timing", "Timing of the outcome relative to predictor measurement (Figure 2D)", "same survey; later event; unclear", "Final outcome-timing code; classification studies only"),
    ("outcome_form", "Form of the modelled outcome (Figure 3B)", "binary; several binary outcomes; multiclass; mixed; unclear",
     "Final coded outcome structure; classification studies only"),
    ("survey_years", "KNHANES survey years analysed (Figure 3A), with the years read from the coded survey years where printed",
     "one survey year; several years within one KNHANES cycle; several years across KNHANES cycles; unclear (+ ': years')",
     "Fixed rule: years named in the coded survey years, assigned to the published KNHANES cycles; classification studies only"),
    ("age_min_years", "Minimum age of the analysed participants, in years, as reported", "number; not reported",
     "Final coded age range. 'age range reported' in the manuscript = age_min_years or age_max_years reported. Age bands of Figure 3B: "
     "both not reported -> not reported; maximum below 19 -> includes <19 years; minimum below 18 -> all ages; minimum not reported -> not reported; "
     "otherwise minimum ≥60, ≥30 or ≥19 (19-29) years (whole years, decimals truncated); classification studies only"),
    ("age_max_years", "Maximum age of the analysed participants, in years, as reported", "number; not reported", "Final coded age range (see age_min_years); classification studies only"),
    ("candidate_predictors_n", "Number of candidate predictors considered before any selection, as reported or countable from a listed set",
     "number; not reported", "Final coded number (first number of the coded value; 'not reported' also when no number could be given); "
     "'number of candidate predictors reported' in the manuscript = a number given; classification studies only"),
    ("missing_value_handling", "Handling of missing values (Figure 3C)",
     "complete-case analysis; single imputation; multiple imputation; handled within the algorithm; other or several methods; not reported",
     "Final coded missing-data handling; 'missing-value handling reported' in the manuscript = any value except 'not reported'; classification studies only"),
    ("algorithm_families_fitted", "Algorithm families fitted (Figure 3D)", "logistic regression; boosting; random forest; decision tree; neural network; SVM; other (multi-value)",
     "Final coded algorithms grouped into the families of Figure 3D; classification studies only"),
    ("preferred_algorithm_family", "Family of the model the authors designated as final or preferred (Figure 3D)",
     "one family; other; not designated; single algorithm fitted (no comparison)", "Final coded selected model; classification studies only"),
    ("final_model_fully_specified", "The final model is fully specified so that it could be applied (equation with coefficients, tree, score, shared model file, or full hyperparameters with code)",
     "yes; partly; not reported", "Final coded item; 'final model fully specified' in the manuscript = yes; classification studies only"),
    ("tuning_kept_apart", "Hyperparameter tuning and model selection were kept apart from the data of the final performance evaluation",
     "yes; no (evaluation data used for tuning or selection); not reported; not applicable (no tuning)",
     "Final coded item; 'tuning kept apart from the final evaluation' in the manuscript = yes or not applicable; classification studies only"),
    ("preprocessing_timing", "Timing of the preprocessing steps (imputation, scaling, feature selection, class rebalancing) relative to the train-test split (Figure 3E)",
     "all steps within the training data; at least one step before the split; no preprocessing step; timing unclear",
     "Fixed rule on the coded columns fig_PRE05 (imputation within training data), fig_PRE13 (scaling), fig_PRE14 (feature selection within training data) "
     "and fig_IMB03 (rebalancing): before the split if imputation or feature selection was not confined to the training data, or scaling or rebalancing "
     "came before the split; within the training data if every step that was done was confined to it; no step if none applies; otherwise unclear. "
     "Scaling before the split = fig_PRE13 BEFORE; feature selection before the split = fig_PRE14 NOT_USED; classification studies only"),
    ("evaluation_design", "Evaluation designs used (Figure 3E)", "train-test split; cross-validation; bootstrap; external validation; temporal validation; apparent performance only; other; none or not reported (multi-value)",
     "Final coded validation types; 'validation beyond the development data' in the manuscript = external or temporal; classification studies only"),
    ("auroc_reported", "The study reported the area under the ROC curve (or c-statistic) for a model", "yes; no",
     "Fixed rule on the coded performance measures (metric name containing AUROC, AUC, ROC, c-statistic, c-index or 'area under'); classification studies only"),
    ("survey_weights_in_fitting", "Survey weights used in model fitting", "yes; no (stated not used); not reported; unclear", "Final coded use of survey weights in fitting; classification studies only"),
    ("ranking_study", "The study reported a variable-importance ranking (Figures 4–5)", "yes; no", "Final coded ranking item; classification studies only"),
    ("importance_methods", "Methods used to produce the ranking (Figure 4C)", "SHAP; model-native importance; tree or rule structure; permutation importance; coefficient or test statistic; LIME; other methods (multi-value)",
     "Final coded importance methods; ranking studies only"),
    ("important_variable_domains", "Domains of the variables reported as important (Figure 5A)", "the 15 domains of Figure 5A or 'Other' (multi-value); none classifiable",
     "Final coded domains; ranking studies only"),
    ("important_variables_harmonised", "Harmonised names of the variables reported as important (Figure 5B–C)", "harmonised variable labels (multi-value); none harmonised",
     "Named variables mapped to harmonised labels by the fixed dictionary of Figure 5 (public repository, 04_analysis/code/practice_trends.py), confirmed by the coded domains; ranking studies only"),
    ("outcome_group", "Figure 5B row of the ranking study", "e.g. diabetes; depression; suicide; other <topic> outcome; all <topic> outcomes; other topics",
     "Keyword rule on the coded outcome name (Figure 5B). An outcome group sits under the topic it belongs to, which can differ from primary_health_topic (e.g. an obesity outcome is shown under metabolic and endocrine); topics not split by outcome form one row ('all <topic> outcomes') and the remaining topics are pooled ('other topics'); ranking studies only"),
    ("ranking_stability_checked", "The ranking study reported checking ranking stability across resamples, survey cycles or subgroups (Figure 4D)",
     "yes; no; not applicable (no ranking)", "Final coded stability item, restricted by the manuscript's definition; classification studies only"),
    ("stability_compared_across", "What the stability check compared", "subgroups; resamples; survey cycles (multi-value)", "Fixed rule on the coded stability method; studies with a check only"),
]


# Coded columns of the earlier derivation (rules on the CHARMS-based coding) that describe the same concept as a reader column
# or a fig_* column under a different source item or rule, so that the two disagree for some studies (e.g. weights_fitting
# 14 vs survey_weights_in_fitting 10, auc_reported 156 vs auroc_reported 157, scope_all_stated_within_training 0 vs
# preprocessing_timing 'all steps within the training data' 1). The analysis values of the article are the reader and fig_*
# columns; these duplicates are not used by the article or by recount_from_additional_data.py and are left out of Data 1.
LEGACY_DROP = {
    "timing": "outcome_timing",
    **{k: "evaluation_design" for k in ("val_external", "val_temporal", "val_geographic", "val_split", "val_cv", "val_bootstrap",
                                         "val_apparent", "val_none", "val_best")},
    "auc_reported": "auroc_reported",
    "calibration": "fig_MET_CALPLOT_R",
    "weights_fitting": "survey_weights_in_fitting", "weights_evaluation": "fig_SUR07",
    "design_any": "fig_SUR04", "design_descriptive_only": "fig_SUR04, fig_SUR06, fig_SUR07",
    **{k: "preprocessing_timing" for k in ("scope_whole_before_split", "scope_test_outcomes_used", "scope_all_stated_within_training",
                                           "scope_any_not_stated")},
    "missing_imputation": "missing_value_handling",
    **{k: "algorithm_families_fitted" for k in ("fam_tree_ensemble", "fam_svm", "fam_neural_network", "fam_single_tree", "fam_knn",
                                                "fam_naive_bayes", "fam_regression_family", "fam_llm", "fam_automl")},
    "pres_shap": "importance_methods",
}
_same = lambda r: tuple(r)
DERIV_KEEP = {   # rows of the derivation table: kept, rewritten for the remaining columns, or dropped (None)
    "fam_*": None, "timing": None, "val_*": None, "auc_reported": None,
    "calibration": lambda r: ("calibration_beyond_brier", r[1], "status reported and a value naming calibration, Hosmer-Lemeshow, reliability or O:E (Brier-only excluded)"),
    "weights_fitting / weights_evaluation": None, "design_any / design_descriptive_only": None, "scope_*": None,
    "imb_*": _same, "missing_imputation": None,
    "pres_shap / pres_tool": lambda r: ("pres_tool", r[1], "nomogram, score, calculator, web/app or equation named"),
    "overlap": _same, "n_analysed_max": _same,
}


def data1(col):
    src = load_workbook(OCT_XLSX, read_only=True)
    st = [list(r) for r in src["Studies"].iter_rows(values_only=True)]
    deriv = [list(r) for r in src["Derivation"].iter_rows(values_only=True)]
    h0 = st[0]; assert len(h0) == 170 and len(st) == 280 and h0[0] == "study_id"
    assert set(LEGACY_DROP) <= set(h0), set(LEGACY_DROP) - set(h0)
    keep = [i for i, k in enumerate(h0) if k not in LEGACY_DROP]
    st = [[row[i] for i in keep] for row in st]; h = st[0]
    deriv = [deriv[0]] + [DERIV_KEEP[r[0]](r) for r in deriv[1:] if DERIV_KEEP[r[0]] is not None]
    ix = {k: i for i, k in enumerate(h)}
    rid_of = {row[0]: row[ix["representative_report"]] for row in st[1:]}
    assert set(rid_of.values()) == set(ALL) and all(recs[rid_of[s]]["study"] == s for s in rid_of)
    names = [c[0] for c in READER]; assert set(col) <= set(names), set(col) - set(names)
    out = []
    for row in st[1:]:
        s, r = row[0], rid_of[row[0]]
        rd = {"study_id": s, "title_display": clean(row[ix["title"]]), "journal_display": clean(row[ix["journal_or_venue"]])}
        rd.update({k: col[k].get(r, "") for k in col})
        out.append([rd.get(k, "") for k in names] + row[1:])
    header = names + h[1:]
    assert len(set(header)) == len(header)
    wb = Workbook(); ws = wb.active; ws.title = "README"
    fills = [FILL_R] * len(names) + [FILL_C] * (len(h) - 1)
    write_sheet(wb.create_sheet("Studies"), header, out, fills=fills, freeze="B2")
    cnt = lambda k, v: sum(col[k].get(r) == v for r in ALL)
    write_readme(ws, [
        ("title", "Additional Data 1. Study-level dataset of the 279 included studies"),
        ("para", "Purpose. One row per included study (its representative report), so that a reader can see which health problem each study "
                 "addressed and how it built, evaluated and explained its models, and can recount the figures and tables of the manuscript. "
                 "The values are the final values of the coding: two AI systems coded each report independently, disagreements were "
                 "reconciled through cross-review and item-level rules, and the author confirmed the rules and settled the remaining cases. "
                 "The round-by-round records, prompts and rules are in the public repository. Only bibliographic details (title, journal, "
                 "year, identifiers, first author) and categorical codes are given; no abstracts, full texts, quotations or page locations."),
        ("head", "Sheet 'Studies'"),
        ("para", f"Blue columns (1–{len(names)}): reader columns, the final values behind the manuscript figures, in plain words. "
                 f"Grey columns ({len(names) + 1}–{len(header)}): the coded dataset ({len(h)} columns; study_id is shown once): bibliographic details, "
                 "study-level variables derived from the coded items (rules below), and the coded categories used in the figures and tables (fig_*), "
                 "including the PROBAST+AI judgements (fig_PD_*, model development; fig_PE_*, performance evaluation; several units of a study "
                 "are separated by ';'). Multi-value cells use '; '. The analysis columns are filled for the 217 health-state classification studies, "
                 "which form the denominator of the manuscript's analyses; they are blank for the 18 other health analyses and the 44 ML method studies."),
        ("head", "Reader columns"),
        ("table", [("column", "definition", "allowed values", "how derived")] + READER),
        ("head", "Counts in the reader columns (they equal the numbers in the manuscript)"),
        ("para", f"study_group: {cnt('study_group', 'health-state classification')} / {cnt('study_group', 'other health analysis')} / {cnt('study_group', 'ML method study')}. "
                 f"outcome_timing: same survey {cnt('outcome_timing', 'same survey')}, later event {cnt('outcome_timing', 'later event')}, unclear {cnt('outcome_timing', 'unclear')}. "
                 f"ranking_study yes {cnt('ranking_study', YES)}; ranking_stability_checked yes {cnt('ranking_stability_checked', YES)}; "
                 f"survey_weights_in_fitting yes {cnt('survey_weights_in_fitting', YES)}. "
                 f"Among the classification studies: age range reported (age_min_years or age_max_years) {sum(col['age_min_years'].get(r) != 'not reported' or col['age_max_years'].get(r) != 'not reported' for r in CORE)}; "
                 f"candidate_predictors_n given {sum(col['candidate_predictors_n'].get(r) != 'not reported' for r in CORE)}; "
                 f"missing_value_handling reported {sum(col['missing_value_handling'].get(r) != 'not reported' for r in CORE)}; "
                 f"final_model_fully_specified yes {cnt('final_model_fully_specified', YES)}; "
                 f"tuning_kept_apart yes or not applicable {sum(col['tuning_kept_apart'].get(r, '').startswith(('yes', 'not applicable')) for r in CORE)}; "
                 f"preprocessing_timing: all steps within the training data {cnt('preprocessing_timing', 'all steps within the training data')}, "
                 f"at least one step before the split {cnt('preprocessing_timing', 'at least one step before the split')}, "
                 f"timing unclear {cnt('preprocessing_timing', 'timing unclear')}; auroc_reported yes {cnt('auroc_reported', YES)}."),
        ("head", "Companion files"),
        ("para", "Additional Data 2: reporting assessment of the 217 health-state classification studies (TRIPOD+AI-derived elements, "
                 f"individual requirements and proposed items), linked by study_id. The report-level reporting status of the 287 eligible reports, "
                 f"an intermediate coding record, is in the public repository ({REPO}, 03_coding/reporting_status.csv)."),
        ("head", "Coded columns"),
        ("para", f"The coding items behind the coded columns are defined in the codebook of the public repository ({REPO}, folder 03_coding/items). "
                 "The study-level variables of the coded block were derived from the coded items by the following fixed rules."),
        ("table", [tuple(deriv[0])] + [tuple(r) for r in deriv[1:]]),
        ("head", "Which columns hold the analysis values"),
        ("para", "The values analysed in the manuscript are the reader columns and the fig_* columns. An earlier derivation on the same coding "
                 "also produced study-level variables that describe the same concepts under other source items or rules, and that therefore "
                 "differ for some studies; to avoid two values for one concept, they are not included here: "
                 + "; ".join(f"{', '.join(k for k in LEGACY_DROP if LEGACY_DROP[k] == v)} (analysis value: {v})" for v in dict.fromkeys(LEGACY_DROP.values()))
                 + ". The remaining coded variables (e.g. n_analysed_max, threshold_reported, calibration_beyond_brier, imb_*) have no "
                   "differently defined counterpart."),
    ])
    return wb, header, out


# =========================================================================================== report-level status (repository only)
STATUS_CSV = "results/oct_search/public/reporting_status.csv"


def status_table(study_rep):
    src = load_workbook(OCT_XLSX, read_only=True)
    st = [list(r) for r in src["Status"].iter_rows(values_only=True)]
    h = st[0]; assert h[:2] == ["record_id", "study_id"] and len(h) == 220 and len(st) == 288
    reps = set(study_rep.values())
    add = [i for i, k in enumerate(h) if k.startswith("legacy.")]; charms = [i for i in range(2, len(h)) if i not in add]
    assert len(add) == 155 and len(charms) == 63
    out = []
    for row in st[1:]:
        rep = row[0] in reps
        assert row[1] in study_rep, row[1]
        if not rep: assert all(row[i] in (None, "") for i in add), row[0]          # additional items: representative reports only
        else: assert all(row[i] not in (None, "") for i in add + charms), row[0]
        out.append([row[0], row[1], YES if rep else NO] + row[2:])
    header = ["record_id", "study_id", "representative_report"] + h[2:]
    import csv
    with open(STATUS_CSV, "w", newline="", encoding="utf-8") as f:
        w = csv.writer(f); w.writerow(header); w.writerows([["" if v is None else v for v in r] for r in out])
    allv = collections.Counter(str(row[i]).split(";")[0].strip() for row in st[1:] for i in charms + add if row[i] not in (None, ""))
    print("status values:", dict(allv), "inconsistency:", sum("inconsistency" in str(row[i]) for row in st[1:] for i in charms + add))
    return header, out


# =========================================================================================== Data 2 (reporting assessment)
DEFS = "tools/oct_search/item_definitions.json"   # definitions of the 19 elements, 52 requirements and 43 proposed items (from the
                                                 # former supplement tables, extracted by rewrite/round20/extract_supp_tables.py)


def definitions(cols):
    """Definition rows of the README, one per assessment column, in column order; IDs and names are checked against the
    assessment columns (item_ids / checklist scores) so that a definition cannot sit under the wrong column."""
    import item_ids as II
    D = json.load(open(DEFS))
    el = {e["element"]: e for e in D["elements"]}; rq = {r["id"]: r for r in D["requirements"]}; it = {r["id"]: r for r in D["items"]}
    byc = {x["pub_id"]: x for x in CK["items"]}
    fd = {int(k.split(".")[0]): v for k, v in D["further_detail"].items()}
    na = lambda v: "never (applies to all 217 studies)" if v in ("–", "") else v
    out = []
    for h, kind, key, label in cols:
        if kind == "element":
            e = el[key]; assert e["name"] == label, (key, e["name"], label)
            out.append((h, "TRIPOD+AI-derived element", e["name"],
                        f"{e['question']} Complete: all of the element's requirements reported ({e['requirements']}); partly: some; not reported: none.",
                        "never (judged in all 217 studies)", "proposed items: " + ("none" if e['proposed_items'] in ('–', '') else e['proposed_items']), fd.get(key, "")))
        elif kind == "requirement":
            r = rq[key]; assert r["name"] == label, (key, r["name"], label)
            out.append((h, "TRIPOD+AI requirement", r["name"], r["criterion"], na(r["not_applicable_when"]),
                        "refined by: " + ("none (retained unchanged)" if r["refined_by"] in ("–", "") else r["refined_by"]), ""))
        else:
            r = it[h]; assert r["name"] == label, (h, r["name"], label)
            out.append((h, "proposed item", r["name"], r["criterion"], na(r["not_applicable_when"]), f"stage: {r['stage']}; type: {r['type']}", ""))
    assert len(out) == 19 + 52 + 43 and [o[0] for o in out] == [c[0] for c in cols]
    n_ref = sum(r["type"].startswith("Refined") for r in it.values()); n_add = sum(r["type"].startswith("Added") for r in it.values())
    n_new = sum(r["type"].startswith("New") for r in it.values()); n_kept = sum(r["refined_by"] in ("–", "") for r in rq.values())
    n_knh = sum("(KNHANES)" in r["type"] for r in it.values())
    assert (n_ref, n_add, n_new, n_knh) == (24, 12, 7, 13), (n_ref, n_add, n_new, n_knh)
    chk("requirements retained unchanged", n_kept, "kReqKept")
    crit_diff = [h for h, kind, key, _ in cols if kind == "item" and it[h]["criterion"] != clean(byc[key]["crit_en"])]
    CHECKS.append(f"definitions: 19 elements, 52 requirements, 43 items matched to their columns by ID and name; "
                  f"{43 - len(crit_diff)} item criteria identical to the scoring file, {len(crit_diff)} worded as printed in the article ({', '.join(crit_diff)})")
    return out, (n_kept, len(rq) - n_kept, n_ref, n_add, n_new, n_knh)


def denominators(rows, study_of, ad1):
    """Counts that use different definitions or denominators (practice coding in Additional Data 1 vs judgements here)."""
    C = CORE; a = lambda r, k: str(ad1[r].get(k) or "")
    rank = {r for r in C if a(r, "ranking_study") == YES}
    app20a = {r for r in C if rows[r]["20a⁺"] != "not applicable"}
    assert rank <= app20a
    chk("ranking studies", len(rank), "kRanking"); chk("20a+ applicable", len(app20a), "kCkCThreeSevend")
    stab = {r for r in C if a(r, "ranking_stability_checked") == YES}; m20e = {r for r in C if rows[r]["20e⁺"] == "met"}
    assert m20e <= stab
    chk("stability check (practice)", len(stab), "kRankStab"); chk("20e+ met", len(m20e), "kCkCFourOnen")
    wfit = {r for r in C if a(r, "survey_weights_in_fitting") == YES}; m11f = {r for r in C if rows[r]["11f⁺"] == "met"}
    chk("survey weights in fitting (practice)", len(wfit), "kWFit"); chk("11f+ met", len(m11f), "kCkCTwoTwon")
    chk("11f+ met by users", len(m11f & wfit), "kCkWFitUsedMet"); chk("11f+ met, why not", len(m11f - wfit), "kCkWFitWhyNot")
    chk("users not meeting 11f+", len(wfit - m11f), "kCkWFitUsedNotMet")
    comb_app = {r for r in C if a(r, "fig_SUR11") not in ("NA", "")}; comb = {r for r in comb_app if a(r, "fig_SUR11") == "USED"}
    multi = {r for r in C if a(r, "fig_DAT08") in ("MULTI_SAME", "MULTI_CROSS")}; ydunc = {r for r in C if a(r, "fig_DAT08") == "UNC"}
    one_y = {r for r in C if a(r, "fig_DAT08") == "ONE_YEAR"}; sep = {r for r in multi if a(r, "fig_SUR11") == "NA"}
    assert comb_app == (multi - sep) | ydunc and one_y | sep == {r for r in C if a(r, "fig_SUR11") == "NA"}, "fig_SUR11 applicability"
    chk("combined-year weights applicable", len(comb_app), want=len(multi) - len(sep) + len(ydunc))
    app4e = {r for r in C if rows[r]["4e⁺"] != "not applicable"}; m4e = {r for r in C if rows[r]["4e⁺"] == "met"}
    out_r = {r for r in C if a(r, "fig_OUT16") == "R2"}; prd_r = {r for r in C if a(r, "fig_PRD13") == "R2"}
    m6a = {r for r in C if rows[r]["6a′"] == "met"}; m7a = {r for r in C if rows[r]["7a′"] == "met"}
    chk("outcome rebuildable (practice)", len(out_r), "kOutRebuild"); chk("predictor set rebuildable (practice)", len(prd_r), "kPrdRebuild")
    chk("6a' met", len(m6a), "kCkCZeroEightn"); chk("7a' met", len(m7a), "kCkCOneOnen")
    chk("4e+ met", len(m4e), "kCkCZeroFourn"); chk("4e+ applicable", len(app4e), "kCkCZeroFourd")
    CHECKS.append(f"combined-year survey weights (practice, Additional Data 1 fig_SUR11): {len(comb)}/{len(comb_app)}")
    return [
        f"52 requirements and 43 proposed items. The 52 individual requirements are this review's division of the TRIPOD+AI items; "
        f"the 43 proposed items are a separate set with their own criteria and applicability (Table 1), so counts from the two sets are not interchangeable.",
        f"Importance items. Ranking studies (ranking_study = yes in Additional Data 1) are the {len(rank)} studies with a model-based ranking. "
        f"The importance items apply to every study presenting an importance result the item could describe, so 20a⁺ applies to {len(app20a)} studies: "
        f"the {len(rank)} ranking studies and {len(app20a - rank)} that ordered predictors by regression coefficients, filter statistics or a tree split hierarchy.",
        f"Ranking stability. {len(stab)} ranking studies reported a stability check (practice coding, Additional Data 1); {len(m20e)} of them described both its "
        f"method and its result and met item 20e⁺.",
        f"Survey weights in model fitting. {len(wfit)} studies reported using survey weights in model fitting (practice coding); item 11f⁺ was met by "
        f"{len(m11f)} studies: {len(m11f & wfit)} that described how the weights were used and {len(m11f - wfit)} that explained why they were not used. "
        f"{len(wfit - m11f)} of the {len(wfit)} users did not describe the use well enough to meet the item.",
        f"Combined-year survey weights. Use of combined-year survey weights (practice coding, Additional Data 1 column fig_SUR11) applied to "
        f"{len(comb_app)} studies: the {len(multi)} studies analysing several survey years, except {len(sep)} that analysed the years separately "
        f"without pooling them ({', '.join(sorted(a(r, 'study_id') or r for r in sep))}), plus the {len(ydunc)} studies whose survey years were unclear "
        f"(coded unclear, because pooling could not be ruled out); it does not apply to the {len(one_y)} single-year studies. "
        f"Combined-year weights were found in {len(comb)} studies; item 4e⁺ judges whether the adjustment was reported and also "
        f"excludes studies stating that survey weights were not used, so it applies to {len(app4e)} studies and was met by {len(m4e)}.",
        f"Rebuilding outcomes and predictors. The practice coding (Additional Data 1 columns fig_OUT16 and fig_PRD13, value R2) found the outcome "
        f"rebuildable in {len(out_r)} studies and the predictor set in {len(prd_r)}; the stricter criteria of items 6a′ and 7a′ were met by {len(m6a)} and "
        f"{len(m7a)} studies. A practice records what a study did and an item whether the study reported the decision, so neither count is a subset of the other.",
    ]


def data2(cols, rows, study_of, d1_bib, ad1):
    header = ["study_id", "record_id", "first_author", "year", "elements_complete_n", "proposed_items_met_pct"] + [c[0] for c in cols]
    order = sorted(CORE, key=lambda r: study_of[r])
    out = [[study_of[r], r, d1_bib[r][0], d1_bib[r][1], rows[r]["elements_complete_n"], rows[r]["proposed_items_met_pct"]] + [rows[r][c[0]] for c in cols] for r in order]
    KF = {"element": PatternFill("solid", fgColor="DDEBF7"), "requirement": PatternFill("solid", fgColor="E2EFDA"), "item": PatternFill("solid", fgColor="FCE4D6")}
    wb = Workbook(); ws = wb.active; ws.title = "README"
    write_sheet(wb.create_sheet("Assessment"), header, out, fills=[FILL_C] * 6 + [KF[c[1]] for c in cols], freeze="C2", maxw=14)
    for c in range(7, len(header) + 1): wb["Assessment"].column_dimensions[get_column_letter(c)].width = 11
    defs, (n_kept, n_refd, n_ref, n_add, n_new, n_knh) = definitions(cols)
    dens = denominators(rows, study_of, ad1)
    def_rows = [("column", "kind", "name", "judgement criterion", "not applicable when", "refinement, stage and type", "further detail to report (not judged)")] + defs
    write_readme(ws, [
        ("title", "Additional Data 2. Reporting assessment of the 217 health-state classification studies"),
        ("para", "Purpose. One row per classification study, giving the final judgement for each of the 19 broad TRIPOD+AI-derived elements, the "
                 "52 individual TRIPOD+AI requirements and the 43 proposed items of Table 1. Recounting the columns reproduces Figure 6 and the "
                 "reporting numbers of the manuscript. The judgements were made by two AI systems independently and reconciled (with author "
                 "confirmation of the rules) as described in the Methods; no text from the reports is given."),
        ("head", "Columns"),
        ("para", "study_id, record_id, first_author, year: identifiers (link to Additional Data 1). elements_complete_n: number of the 19 elements "
                 "judged complete. proposed_items_met_pct: percentage of the applicable proposed items met (the per-study score of the manuscript; "
                 "rounded to one decimal). Then one column per element, requirement and proposed item in the row order of Table 1: for each element, "
                 "the element ('element 4'), its requirements (4a, 4b, ...) each followed by its KNHANES refinement (prime: 4a′; a second refinement 14b″), "
                 "then the requirements added by this review (plus: 4e⁺); elements 20–21 hold the new items 20a⁺–21a⁺. Blue = elements, green = "
                 "requirements, orange = proposed items."),
        ("head", "Values"),
        ("table", [("columns", "values", "meaning", ""),
                   ("element N", "complete; partial; not reported", "all, some or none of the element's requirements reported", ""),
                   ("requirements (e.g. 4a)", "met; not met; not applicable; unclear",
                    "not applicable = the requirement does not apply to the study; unclear (12 of 11,284 cells) = could not be judged, counted as applicable and not met", ""),
                   ("proposed items (e.g. 4a′, 4e⁺)", "met; not met; not applicable", "not applicable follows the item's applicability rule (e.g. combined-year survey weights do not apply to a single survey year)", "")]),
        ("head", "How the judgements were made"),
        ("para", "Each element, requirement and item was judged in the representative report of each study. Elements and requirements were coded "
                 "independently: element judgements were kept as coded, not re-derived from the requirement judgements, so the two levels can differ. "
                 "A requirement or item was not applicable only when its object did not exist in the study; not having performed a step did not make it "
                 "not applicable. Reporting, not practice, was judged: a clear statement that something was not done meets a criterion that asks whether "
                 "it was done, and 'not met' means that the report was insufficient for the criterion, not that it gave no information. Element and "
                 "requirement labels (1a, 2a, ...) are this review's, not the official TRIPOD+AI item numbers."),
        ("para", f"Proposed items. Of the 52 requirements, {n_kept} were retained unchanged and {n_refd} were refined into {n_ref} items (prime; one "
                 f"requirement, 14b, into two); {n_add} items were added within existing elements and {n_new} form the new elements 20 (variable importance) "
                 f"and 21 (analyses after the ranking) (plus). (KNHANES) marks the {n_knh} items needed because KNHANES is a repeated cross-sectional "
                 "probability survey. Stage: data, rebuilding the analysis dataset; model, reproducing the model and performance estimates; importance, "
                 "reproducing the importance results; reporting, needed to interpret or appraise the results. proposed_items_met_pct = 100 × items met / "
                 "items applicable; it describes the completeness of the information needed for reproduction, not verified reproducibility or a "
                 "validated quality score. The checklist was proposed by the author and has not been externally validated."),
        ("head", "Counts with different definitions or denominators"),
    ] + [("para", d) for d in dens] + [
        ("head", "Definitions of the assessment columns"),
        ("para", "One row per column of the sheet 'Assessment', in column order: the judgement criterion and the condition under which the column was "
                 "judged not applicable. Criteria are paraphrased from the coding definitions; the item-level exceptions settled during reconciliation are "
                 f"in the codebook of the public repository ({REPO}, 03_coding)."),
        ("table", def_rows),
        ("head", "Companion files"),
        ("para", "Additional Data 1: study-level dataset of the 279 included studies (bibliographic details and coded values), linked by study_id. "
                 f"The report-level reporting status of the 287 eligible reports, an intermediate coding record, is in the public repository "
                 f"({REPO}, 03_coding/reporting_status.csv)."),
    ], widths=(14, 22, 30, 70, 40, 30, 60))
    return wb, header, out


# =========================================================================================== verification of the written files
def verify(paths, study_rep):
    LONG_OK = {"title", "title_display", "journal_display", "journal_or_venue"}
    code_like = re.compile(r"^[A-Za-z0-9_ ;:.,()+/′″⁺–≤-]*$")
    res = {}
    for p, sheet in paths:
        wb = load_workbook(p, read_only=True)
        assert len(wb.sheetnames) == 2 and wb.sheetnames[0] == "README", wb.sheetnames
        data = [list(r) for r in wb[sheet].iter_rows(values_only=True)]
        h = data[0]; body = data[1:]
        ids = [r[0] for r in body]; assert len(ids) == len(set(ids))
        for r in body:
            for k, v in zip(h, r):
                if isinstance(v, str) and len(v) > 300 and k not in LONG_OK and not code_like.match(v):
                    raise AssertionError(f"long free text in {p}:{k}: {v[:80]}")
        res[p] = (sheet, len(body), len(h), ids, h, body)
    return res


def strip_file_dates(p):
    """Public files carry no generation timestamp: the created/modified dates of the document properties are removed."""
    import re as _re, zipfile as _zf, shutil as _sh
    tmp = p + ".tmp"
    with _zf.ZipFile(p) as zi, _zf.ZipFile(tmp, "w", _zf.ZIP_DEFLATED) as zo:
        for it in zi.infolist():
            b = zi.read(it.filename)
            if it.filename == "docProps/core.xml":
                b = _re.sub(rb"<dcterms:(created|modified)[^>]*>[^<]*</dcterms:\1>", b"", b)
            zi2 = _zf.ZipInfo(it.filename, date_time=(1980, 1, 1, 0, 0, 0)); zi2.compress_type = _zf.ZIP_DEFLATED
            zo.writestr(zi2, b)
    _sh.move(tmp, p)


def main():
    col = analysis_columns(reader_columns())
    cols, rows = assessment()
    pu = check_probast_units()
    wb1, h1, d1 = data1(col)
    study_rep = {r[0]: r[h1.index("representative_report")] for r in d1}
    hs, b2 = status_table(study_rep)
    study_of = {v: k for k, v in study_rep.items()}
    bib = {r[h1.index("representative_report")]: (r[h1.index("first_author")], r[h1.index("year")]) for r in d1}
    ad1 = {r[h1.index("representative_report")]: dict(zip(h1, r)) for r in d1}
    wb2, h2, d2 = data2(cols, rows, study_of, bib, ad1)
    paths = []
    for k, wb, sheet in ((1, wb1, "Studies"), (2, wb2, "Assessment")):
        p = f"manuscript/KNHANES_ML_review_Additional_Data_{k}.xlsx"; wb.save(p); strip_file_dates(p); paths.append((p, sheet))
    for k in (3, 4): assert not os.path.exists(f"manuscript/KNHANES_ML_review_Additional_Data_{k}.xlsx"), k
    V = verify(paths, study_rep)
    s1, n1, c1, ids1, *_ = V[paths[0][0]]; s2, n2, c2, ids2, *_ = V[paths[1][0]]
    assert n1 == 279 and n2 == 217 and len(b2) == 287
    rid2 = [r[0] for r in b2]; assert len(set(rid2)) == 287
    sid2 = [r[1] for r in b2]; assert set(sid2) == set(ids1) and len(sid2) - len(set(sid2)) == 8
    assert sum(r[2] == YES for r in b2) == 279 and set(ids2) <= set(ids1)
    for p, (sheet, n, c, *_r) in V.items(): print(f"wrote {p}: sheets README + {sheet}, {n} rows x {c} columns")
    print(f"wrote {STATUS_CSV}: {len(b2)} rows x {len(hs)} columns; {len(set(sid2))} studies, {len(sid2) - len(set(sid2))} additional reports; all study_ids in Data 1")
    for pre, (n, linked) in pu.items():
        print(f"PROBAST+AI {pre}: {n} units with an overall judgement; {linked} carry all four domain judgements under the same unit label "
              f"(the unit-level judgements are exported separately by export_probast_units.py to probast_units.csv)")
    print(f"{len(CHECKS)} checks passed"); open(os.path.join(ROOT, "results/oct_search/additional_data_v2_checks.txt"), "w").write("\n".join(CHECKS) + "\n")


if __name__ == "__main__":
    main()
