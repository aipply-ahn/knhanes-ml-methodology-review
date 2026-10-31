"""리뷰 본문 그림 생성 — results/derived/analysis.json 에서만 수치를 읽는다.

    python tools/make_figures.py

출력 figures/submission/fig{1,2,3,4}.{pdf,png}. 라벨은 영문(JMIR 투고용).
"""
import sys, os, json, glob
from collections import Counter
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
from matplotlib.patches import FancyBboxPatch, FancyArrowPatch

PROJ = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
OUT = os.path.join(PROJ, "figures", "submission")
A = json.load(open(os.path.join(PROJ, "results/derived/analysis.json")))
plt.rcParams.update({"font.family": "DejaVu Sans", "font.size": 9, "axes.spines.top": False,
                     "axes.spines.right": False, "savefig.bbox": "tight", "savefig.dpi": 300})
GREY, BLUE, RED = "#4d4d4d", "#3b6ea5", "#b03a2e"
ORANGE, DARK_BLUE, LIGHT_BLUE = "#D97706", "#164E7A", "#DCEEFF"


def save(fig, name):
    for ext in ("pdf", "png"):
        fig.savefig(os.path.join(OUT, f"{name}.{ext}"))
    plt.close(fig)
    print(f"  {name}")


def fig1_prisma(lang="en"):
    """Recorded selection flow; full-text coverage is described in the caption."""
    ko = lang == "ko"
    sf = json.load(open(os.path.join(PROJ, "results/derived/final_selection_flow.json")))
    src, flow = sf["sources"], sf["flow"]
    part = sf["terminology_screen"]["partition"]
    assert all(sf["full_text_retrieval"][k] is None for k in
               ("reports_sought", "reports_not_retrieved", "reports_assessed"))
    # Noto CJK collections need Type 3 embedding here: inherited Type 42 can
    # retain searchable text while rendering mostly blank after XeLaTeX inclusion.
    with plt.rc_context({"font.family": "Noto Sans CJK KR" if ko else "DejaVu Sans",
                         "pdf.fonttype": 3 if ko else 42}):
        fig = plt.figure(figsize=(7.2, 7.0))
        ax = fig.add_axes([.015, .015, .97, .97])
        ax.axis("off"); ax.set_xlim(0, 16); ax.set_ylim(0, 19)
        def choose(en, kr):
            return kr if ko else en
        def box(x, y, w, h, title, detail="", accent=False, fs=11.3, tfs=11.6):
            ax.add_patch(FancyBboxPatch((x,y),w,h,boxstyle="round,pad=.04,rounding_size=.10",
                                       fc="#E8F1FC" if accent else "#F6F8FA",ec="#52728A",lw=1.1,zorder=2))
            # A separated bold heading, divider and left-aligned rows encode hierarchy.
            extra = .36*title.count("\n") if detail else 0  # two-line headings push the divider down
            ty = y+h-.43-extra/2 if detail else y+h/2
            ax.text(x+w/2,ty,title,ha="center",va="center",fontsize=tfs,
                    weight="bold",color="#164E7A",linespacing=1.25,zorder=3)
            if detail:
                ax.plot([x+.24,x+w-.24],[y+h-.84-extra]*2,color="#B8C9D8",lw=.8,zorder=3)
                ax.text(x+.27,y+h-1.02-extra,detail,ha="left",va="top",fontsize=fs,
                        color="#17212B",linespacing=1.36,zorder=3)
        def arrow(x1,y1,x2,y2):
            ax.add_patch(FancyArrowPatch((x1,y1),(x2,y2),arrowstyle="-|>",
                         mutation_scale=10,lw=1.15,color="#526673",zorder=1))
        db = src["total_before_cross_source_deduplication"] - src["kdca_publication_list"]
        box(.15,15.35,7.65,3.45,choose(f"Database/index records (n={db:,})",f"데이터베이스·색인 레코드 (n={db:,})"),
            f"Europe PMC  {src['europe_pmc_unique']:,}\nOpenAlex  {src['openalex_unique']:,}\n" + choose(f"Korean Citation Index  {src['korean_citation_index']:,}\n", f"한국학술지인용색인  {src['korean_citation_index']:,}\n") + choose(f"PubMed  {src['pubmed_unique_beyond_europe_pmc']:,}",f"PubMed  {src['pubmed_unique_beyond_europe_pmc']:,}"),accent=True)  # prompt 110: caption explains
        # Author decision (2026-09-28): citation searching added no records, so it is reported in Methods and Table S3 only,
        # not as a box line in the flow diagram.
        box(8.45,15.35,7.35,3.45,choose(f"Other sources (n={src['kdca_publication_list']:,})",f"기타 자료원 (n={src['kdca_publication_list']:,})"),choose("Korea Disease Control and\nPrevention Agency list","질병관리청 출판목록"))
        ax.plot([12.1,12.1,4],[15.3,14.9,14.9],color="#526673",lw=1.0)
        arrow(4,15.3,4,14.45)
        # Prompt 091: plain wording for the merge and screening boxes (review v29).
        box(.15,13.25,7.65,1.2,choose(f"Records combined (n={src['total_before_cross_source_deduplication']:,})",f"합친 레코드 (n={src['total_before_cross_source_deduplication']:,})"))
        arrow(7.85,13.85,8.4,13.85)
        box(8.45,13.25,7.35,1.2,choose(f"Duplicates removed (n={flow['duplicates_removed']:,})",f"중복 제거 (n={flow['duplicates_removed']:,})"))
        arrow(4,13.2,4,12.35)
        box(.15,11.05,7.65,1.3,choose(f"Records screened (n={flow['unique_records_screened']:,})",f"레코드 선별 (n={flow['unique_records_screened']:,})"))
        arrow(7.85,11.7,8.4,11.7)
        box(8.45,8.72,7.35,3.63,choose(f"Excluded at title and\nabstract screening (n={flow['terminology_exclusions']:,})",f"제목·초록 선별에서\n제외 (n={flow['terminology_exclusions']:,})"),choose(
            f"No ML or prediction term  {part['no_dictionary_signal']:,}",
            f"ML·예측 용어 없음  {part['no_dictionary_signal']:,}"),fs=10.6)  # prompt 106: unified screening rule; prompt 110: rule in caption
        arrow(4,11,4,8.5)
        # Author 2026-10-24: the "full texts sought/not retrieved/assessed: not recorded" line is dropped.
        box(.15,6.9,7.65,1.6,choose(f"Reports assessed for eligibility (n={flow['records_assessed_against_eligibility']:,})",f"선정 기준 평가 보고 (n={flow['records_assessed_against_eligibility']:,})"),tfs=choose(9.9,11.6),
            )
        arrow(7.85,7.7,8.4,7.7)
        r = flow["report_exclusion_reasons"]
        inel = flow['ineligible_reports']
        assert inel + r['ml_adjacent_catalogued_separately'] == flow['reports_excluded_total']
        adj = r['ml_adjacent_catalogued_separately']  # prompt 106: criterion A -> one exclusion reason, not a separate group
        # Ineligible reasons (subtotal) and the separately catalogued ML-adjacent reports are shown as two groups.
        box(8.45,2.3,7.35,6.1,choose(f"Reports excluded (n={flow['reports_excluded_total']:,})",f"제외된 보고 (n={flow['reports_excluded_total']:,})"),choose(
            f"No supervised non-regression\n learner  {r['no_eligible_machine_learning']}\nUnsupervised or regression-\n family methods only  {adj}\nNot KNHANES  {r['not_knhanes']}\nReview/non-primary  {r['review_or_non_primary_synthesis']}\nNo eligible analysis  {r['no_eligible_knhanes_analysis']}\nAbbreviation not ML  {r['abbreviation_false_positive']}\nOther/unassessable  {r['other_or_unassessable']}",
            f"회귀 계열 밖 지도학습\n 없음  {r['no_eligible_machine_learning']}\n비지도·회귀 계열\n 방법만 사용  {adj}\nKNHANES 아님  {r['not_knhanes']}\n리뷰·비원저  {r['review_or_non_primary_synthesis']}\n해당 분석 없음  {r['no_eligible_knhanes_analysis']}\nML이 아닌 약어  {r['abbreviation_false_positive']}\n기타·판정불가  {r['other_or_unassessable']}"),fs=10.6)
        arrow(4,6.85,4,5.25)
        box(.15,3.95,7.65,1.3,choose(f"Reports of included studies (n={flow['eligible_reports_entering_family_linkage']:,})",f"포함된 연구의 보고 (n={flow['eligible_reports_entering_family_linkage']:,})"))
        arrow(4,3.9,4,1.9)
        nl = flow['additional_or_companion_reports_linked']  # prompt 106: from the flow record
        ax.text(4,2.9,choose(f"{nl} related reports grouped", f"관련 보고 {nl}건을 연구별로 통합"),ha="center",va="center",fontsize=11.3,
                bbox=dict(fc="white",ec="none",pad=2))
        box(.15,.35,7.65,1.55,choose(f"Studies included (n={flow['unique_full_report_studies_included']:,})",f"포함된 연구 (n={flow['unique_full_report_studies_included']:,})"),accent=True)
        # Prompt 107 (review v44): the three study groups in the colours used by every later figure.
        tc = json.load(open(os.path.join(PROJ, "results/derived/practice_trends_107.json")))["task_composition"]
        g3 = [(tc["health"]["classification"], choose("Health analysis\n(classification)", "건강 분석\n(분류)"), "#1F3A5F", "white"),
              (tc["health"]["continuous_or_ordered"] + tc["health"]["other"], choose("Health analysis\n(other ML)", "건강 분석\n(기타 ML)"), "#8DB6E0", "#111827"),
              (sum(tc["method"].values()), choose("Method-\nfocused", "방법\n중심"), "#7B8794", "#111827")]  # prompt 107: dark text keeps the KO glyph check
        assert sum(g[0] for g in g3) == flow['unique_full_report_studies_included']
        ax.plot([7.85, 8.4], [1.12, 1.12], color="#526673", lw=1.0)
        for i, (n, lab, fc, tcol) in enumerate(g3):
            x0 = 8.45 + i * 2.48
            ax.add_patch(FancyBboxPatch((x0, .35), 2.30, 1.55, boxstyle="round,pad=.04,rounding_size=.10", fc=fc, ec=fc, lw=1.0, zorder=2))
            ax.text(x0 + 1.15, 1.12, f"{lab}\n{n}", ha="center", va="center", fontsize=8.0, weight="bold", color=tcol, linespacing=1.1, zorder=3)  # prompt 107: renamed labels fit the box
        save(fig, "fig1_prisma_ko" if ko else "fig1_prisma")


def fig2_trend():
    """연도별 출판 + 관행 추이"""
    fig, (a1, a2) = plt.subplots(1, 2, figsize=(7.4, 3.0), gridspec_kw={"width_ratios": [1.15, 1]})
    yr = {int(k): v for k, v in A["year"].items() if k}
    a1.bar(list(yr), list(yr.values()), color=BLUE, width=0.72)
    a1.set_xlabel("Publication year"); a1.set_ylabel("Studies (n)")
    a1.set_title("A. Publication trend", loc="left", fontsize=9, weight="bold")
    a1.set_xticks(range(2013, 2027, 2))
    a1.annotate("2026 partial\n(September census)", xy=(2026, yr.get(2026, 0)), xytext=(2021.4, 21),
                fontsize=7, color=GREY, arrowprops=dict(arrowstyle="->", lw=0.7, color=GREY))
    P = A["period_trend"]; order = ["–2019", "2020–2022", "2023–2024", "2025–2026"]
    lab = ["≤2019", "2020-22", "2023-24", "2025-26"]
    n = [P[o]["n"] for o in order]
    series = [("Interpretability", [P[o].get("해석기법 사용", 0) for o in order], BLUE, "o"),
              ("Code shared", [P[o].get("코드 공개", 0) for o in order], "#7aa6c2", "s"),
              ("External validation", [P[o].get("외부검증", 0) for o in order], GREY, "^"),
              ("Survey weights in model fitting", [P[o].get("학습에 반영", 0) for o in order], RED, "D")]
    for name, v, c, m in series:
        a2.plot(lab, [100 * x / t for x, t in zip(v, n)], marker=m, color=c, lw=1.4, ms=4.5, label=name)
    a2.set_ylabel("% of studies in period"); a2.set_ylim(-3, 100)
    a2.set_title("B. Practice over time", loc="left", fontsize=9, weight="bold")
    a2.legend(fontsize=6.6, frameon=False, loc="upper left")
    save(fig, "fig2_trend")


def fig3_cycles():
    """조사 연차별 사용 + 자료층"""
    fig, (a1, a2) = plt.subplots(1, 2, figsize=(7.4, 2.9), gridspec_kw={"width_ratios": [1.5, 1]})
    wy = {int(k): v for k, v in A["wave_year_usage"].items()}
    ys = sorted(wy)
    a1.bar(ys, [wy[y] for y in ys], color=[RED if y >= 2021 else BLUE for y in ys], width=0.75)
    a1.set_xlabel("KNHANES survey year"); a1.set_ylabel("Studies using that year (n)")
    a1.set_title("A. Survey years used", loc="left", fontsize=9, weight="bold")
    a1.set_xticks(range(1998, 2026, 4))
    peak = max(wy, key=wy.get)
    a1.annotate(f"peak {peak} (n={wy[peak]})", xy=(peak, wy[peak]), xytext=(1999, 82), fontsize=7, color=GREY,
                arrowprops=dict(arrowstyle="->", lw=0.7, color=GREY))
    a1.annotate("2021 onward\nrarely used", xy=(2023, wy.get(2023, 0)), xytext=(2016.5, 30), fontsize=7, color=RED,
                arrowprops=dict(arrowstyle="->", lw=0.7, color=RED))
    L = {"Examination": "검진(검사·계측)", "Questionnaire": "설문(건강행태·사회경제)",
         "Dietary": "영양(식이)", "Oral health": "구강", "Record linkage": "연계자료"}
    names = list(L); vals = [A["data_layer"].get(L[k], 0) for k in names]
    a2.barh(names[::-1], vals[::-1], color=[RED if v <= 10 else BLUE for v in vals[::-1]], height=0.62)
    for i, v in enumerate(vals[::-1]): a2.text(v + 2, i, str(v), va="center", fontsize=7.5)
    a2.set_xlabel("Studies (n)"); a2.set_xlim(0, max(vals) * 1.18)
    a2.set_title("B. Survey components used", loc="left", fontsize=9, weight="bold")
    save(fig, "fig3_cycles")


def fig3_overview(lang="en"):
    """Core corpus profile: three donut charts and two log-scale histograms."""
    ko = lang == "ko"
    fig = plt.figure(figsize=(10.2, 7.3))
    gs = fig.add_gridspec(2, 6, height_ratios=[1.0, 1.05], hspace=0.92, wspace=0.82)
    pies = [fig.add_subplot(gs[0, 0:2]), fig.add_subplot(gs[0, 2:4]),
            fig.add_subplot(gs[0, 4:6])]
    h1, h2 = fig.add_subplot(gs[1, 0:3]), fig.add_subplot(gs[1, 3:6])
    palette = ["#3b6ea5", "#6f9fc4", "#7b6fa6", "#4f9d8a", "#d08b49",
               "#c15c5c", "#9c7a5b", "#b8b8b8"]

    def donut(ax, labels, values, title):
        total = sum(values)
        ax.pie(values, startangle=90, counterclock=False, colors=palette[:len(values)],
               wedgeprops={"width": .38, "edgecolor": "white", "linewidth": 1.0})
        ax.text(0, 0.05, f"n={total}", ha="center", va="center", fontsize=10, weight="bold")
        ax.text(0, -0.16, "studies" if not ko else "편", ha="center", va="center", fontsize=7, color=GREY)
        legend = [f"{lab} — {v} ({100*v/total:.1f}%)" for lab,v in zip(labels,values)]
        ax.legend(legend, loc="upper center", bbox_to_anchor=(0.5, -0.02), frameon=False,
                  fontsize=6.3, handlelength=1.0, labelspacing=.3)
        ax.set_title(title, loc="left", fontsize=9.2, weight="bold", pad=4)

    task_order = ["classification", "regression", "other", "feature_selection", "imputation", "clustering"]
    task_en = {"classification":"Classification", "regression":"Regression", "other":"Other",
               "feature_selection":"Feature selection", "imputation":"Imputation", "clustering":"Clustering"}
    task_ko = {"classification":"분류", "regression":"회귀", "other":"기타",
               "feature_selection":"변수선택", "imputation":"결측대체", "clustering":"군집"}
    donut(pies[0], [(task_ko if ko else task_en)[k] for k in task_order],
          [A["task"].get(k,0) for k in task_order], "A. 분석 과제" if ko else "A. Analytic task")

    domains = [("Mental health","정신건강",A["category"].get("mental_health",0)),
               ("Diabetes","당뇨병",A["category"].get("diabetes",0)),
               ("Cardiovascular/HTN","심혈관·고혈압",A["category"].get("cvd",0)+A["category"].get("hypertension",0)),
               ("Osteoporosis/sarcopenia","골다공증·근감소증",A["category"].get("osteoporosis_sarcopenia",0)),
               ("Nutrition/diet","영양·식이",A["category"].get("nutrition_diet",0)),
               ("Metabolic syndrome","대사증후군",A["category"].get("metabolic_syndrome",0)),
               ("Oral health","구강건강",A["category"].get("oral_health",0))]
    known=sum(x[2] for x in domains); domains.append(("Other targets","기타 타깃",A["n_include"]-known))
    donut(pies[1], [x[1] if ko else x[0] for x in domains], [x[2] for x in domains],
          "B. 타깃 결과 영역" if ko else "B. Target outcome domain")

    scopes=[("Single year","단년도","단년"), ("Multiple, same cycle","다년도·같은 기수","복수년 · 같은 기수"),
            ("Multiple, across cycles","다년도·다른 기수 포함","복수년 · 기수 넘음"), ("Years unclear","연도 불명","연도 불명")]
    donut(pies[2], [x[1] if ko else x[0] for x in scopes], [A["wave_scope"].get(x[2],0) for x in scopes],
          "C. 조사연도 범위" if ko else "C. Survey-year scope")

    refs = {r["key"] for r in json.load(open(os.path.join(PROJ,"references","refs.json"))) if r.get("verdict")=="INCLUDE"}
    samples=[]
    for p in glob.glob(os.path.join(PROJ,"data","extraction","*.json")):
        d=json.load(open(p)); n=d.get("n_final")
        if d.get("key") in refs and isinstance(n,(int,float)) and n>0: samples.append(n)
    sample_bins=np.logspace(np.log10(100),np.log10(300000),12)
    h1.hist(samples,bins=sample_bins,color=BLUE,edgecolor="white",linewidth=.7)
    h1.set_xscale("log"); h1.set_xticks([100,1000,10000,100000]); h1.set_xticklabels(["100","1k","10k","100k"])
    h1.set_ylabel("연구 수" if ko else "Studies (n)"); h1.set_xlabel("분석 대상자 수 (로그 축)" if ko else "Participants analysed (log scale)")
    h1.set_title(f"D. 분석 표본 수\n(보고 {len(samples)}/{A['n_include']}편)" if ko else f"D. Analytic sample size\n(reported {len(samples)}/{A['n_include']})",loc="left",fontsize=8.8,weight="bold")
    h1.axvline(np.median(samples),color=RED,lw=1.3,ls="--"); h1.text(np.median(samples)*1.08,h1.get_ylim()[1]*.87,f"median {int(round(np.median(samples))):,}",fontsize=7,color=RED)

    iv=json.load(open(os.path.join(PROJ,"results","derived","input_counts.json")))
    var_bins=np.array([1,5,10,20,50,100,250,500,1000,2500],dtype=float)
    h2.hist(iv["values"],bins=var_bins,color="#4f9d8a",edgecolor="white",linewidth=.7)
    h2.set_xscale("log"); h2.set_xticks([1,5,10,20,50,100,500,1000]); h2.set_xticklabels(["1","5","10","20","50","100","500","1k"])
    h2.set_ylabel("연구 수" if ko else "Studies (n)"); h2.set_xlabel("후보·입력 변수 수 (로그 축)" if ko else "Candidate/input variables (log scale)")
    h2.set_title(f"E. 머신러닝 투입 변수 수\n(보고 {iv['n_reported']}/{A['n_include']}편)" if ko else f"E. Variables supplied to ML pipeline\n(reported {iv['n_reported']}/{A['n_include']})",loc="left",fontsize=8.8,weight="bold")
    h2.axvline(iv["median"],color=RED,lw=1.3,ls="--"); h2.text(iv["median"]*1.08,h2.get_ylim()[1]*.87,f"median {iv['median']:g}",fontsize=7,color=RED)
    save(fig,"fig3_overview_ko" if ko else "fig3_overview")


def fig3c_scope():
    """조사연도 범위(단년/같은 기수/기수 넘음) × 통합 가중치 기술"""
    fig, (a1, a2) = plt.subplots(1, 2, figsize=(7.4, 2.7), gridspec_kw={"width_ratios": [1, 1.15]})
    EN = {"단년": "Single year", "복수년 · 같은 기수": "Multiple years,\nwithin one cycle",
          "복수년 · 기수 넘음": "Multiple years,\nacross cycles", "연도 불명": "Years unclear"}
    sc = A["wave_scope"]
    ks = [k for k in ["단년", "복수년 · 같은 기수", "복수년 · 기수 넘음", "연도 불명"] if k in sc]
    vals = [sc[k] for k in ks]
    cols = [BLUE, BLUE, RED, GREY][:len(ks)]
    a1.barh([EN[k] for k in ks][::-1], vals[::-1], color=cols[::-1], height=0.6)
    for i, v in enumerate(vals[::-1]): a1.text(v + 1.5, i, str(v), va="center", fontsize=7.5)
    a1.set_xlabel("Studies (n)"); a1.set_xlim(0, max(vals) * 1.25)
    a1.set_title("A. Span of survey years used", loc="left", fontsize=9, weight="bold")
    a1.tick_params(axis="y", labelsize=7.5)

    # 통합 가중치 기술(S3) — 연차를 실제로 합친 연구만 분모
    x = A["wave_scope_x_s3"]
    ks2 = [k for k in ["복수년 · 같은 기수", "복수년 · 기수 넘음"] if k in x]
    seg = [("Described (Y)", "Y", BLUE), ("Not described (N)", "N", RED),
           ("No information (NI)", "NI", GREY), ("Not applicable (NA)", "NA", "#d9d9d9")]
    left = [0] * len(ks2)
    for lab, code, c in seg:
        v = [x[k].get(code, 0) for k in ks2]
        a2.barh([EN[k] for k in ks2][::-1], v[::-1], left=left[::-1], color=c, height=0.55, label=lab)
        left = [l + n for l, n in zip(left, v)]
    for i, k in enumerate(ks2[::-1]):
        y_ = x[k].get("Y", 0)
        a2.text(sum(x[k].values()) + 1.5, i, f"Y={y_}", va="center", fontsize=7.5,
                color=BLUE if y_ else RED, weight="bold")
    a2.set_xlabel("Studies (n)"); a2.set_xlim(0, max(sum(x[k].values()) for k in ks2) * 1.55)
    a2.set_title("B. Integrated weight construction described", loc="left", fontsize=9, weight="bold")
    a2.tick_params(axis="y", labelsize=7.5)
    a2.legend(fontsize=6.4, loc="upper right", frameon=False, ncol=1, handlelength=1.1,
              borderaxespad=0.2, labelspacing=0.35)
    save(fig, "fig3c_scope")


def fig4_models():
    """알고리즘 사용 대 최고 성능 채택"""
    fig, ax = plt.subplots(figsize=(7.0, 3.2))
    comp, best = A["models_compared"], A["best_model"]
    ms = [m for m, _ in sorted(comp.items(), key=lambda x: -x[1])[:12]]
    y = range(len(ms))
    ax.barh([i + 0.19 for i in y], [comp[m] for m in ms], height=0.36, color="#b9cde0", label="Included as comparator")
    ax.barh([i - 0.19 for i in y], [best.get(m, 0) for m in ms], height=0.36, color=BLUE, label="Best-performing model")
    ax.set_yticks(list(y)); ax.set_yticklabels(ms, fontsize=8); ax.invert_yaxis()
    ax.set_xlabel("Studies (n)"); ax.legend(fontsize=7.5, frameon=False, loc="lower right")
    ax.set_title("Algorithms compared and selected as best performing", loc="left", fontsize=9, weight="bold")
    for i, m in enumerate(ms):
        if comp[m] >= 20:
            ax.text(comp[m] + 1.5, i + 0.19, f"{best.get(m,0)}/{comp[m]}", va="center", fontsize=6.8, color=GREY)
    save(fig, "fig4_models")


def fig6_pipeline():
    """분석 파이프라인 6축 — 사용자 요청 표 항목"""
    fig, axes = plt.subplots(2, 3, figsize=(10.4, 5.6))
    def hbar(ax, d, title, order=None, red=None, total=None):
        items = order or list(d)
        vals = [d.get(k, 0) for k in items]
        cols = [RED if (red and k in red) else BLUE for k in items]
        ax.barh(range(len(items)), vals, color=cols, height=0.66)
        ax.set_yticks(range(len(items)))
        ax.set_yticklabels(items, fontsize=7.0)
        ax.invert_yaxis()
        n = total or sum(vals)
        for i, v in enumerate(vals):
            ax.text(v + max(vals) * 0.02, i, f"{v}", va="center", fontsize=7)
        ax.set_xlim(0, max(vals) * 1.22)
        ax.set_title(title, loc="left", fontsize=8.6, weight="bold")
        ax.set_xlabel("Studies (n)", fontsize=7.5)
        ax.tick_params(axis="x", labelsize=7)

    W = {"Not mentioned": "언급 없음", "Descriptive only": "일부(기술통계·회귀만)",
         "Explicitly not used": "미적용 명시", "Used in model fitting": "학습에 반영"}
    hbar(axes[0][0], {k: A["weights"].get(v, 0) for k, v in W.items()},
         "A. Survey weight handling", list(W), red=["Not mentioned"])
    M = {"Complete case": "완전제거", "Not reported": "미기재", "Simple imputation": "단순 대체",
         "Multiple imputation": "다중대체", "KNN imputation": "KNN 대체", "Other": "기타"}
    hbar(axes[0][1], {k: A["missing"].get(v, 0) for k, v in M.items()},
         "B. Missing data handling", list(M), red=["Complete case", "Not reported"])
    T = {"Classification": "classification", "Other": "other", "Regression": "regression",
         "Clustering": "clustering", "Feature selection": "feature_selection", "Imputation": "imputation"}
    hbar(axes[0][2], {k: A["task"].get(v, 0) for k, v in T.items()},
         "C. Task type", [k for k in T if A["task"].get(T[k], 0) > 0])
    D = {"Discrimination + calibration": "판별력 + 보정", "Discrimination + CI": "판별력 + 신뢰구간",
         "Discrimination + class\nmetrics": "판별력 + 분류지표", "Discrimination only": "판별력만(AUC)",
         "Accuracy-centred": "정확도 중심", "Other": "기타", "No performance reported": "성능 미보고"}
    hbar(axes[1][0], {k: A["metric_depth"].get(v, 0) for k, v in D.items()},
         "D. Depth of performance reporting", list(D),
         red=["Accuracy-centred", "No performance reported", "Discrimination only"])
    I = {"SHAP": "SHAP", "Built-in importance": "모델 내장 중요도(FI)",
         "Permutation importance": "순열 중요도(PI)", "Regression coefficients": "회귀계수·오즈비",
         "LIME": "LIME", "Partial dependence": "부분의존·스플라인", "Other": "기타", "None": "없음"}
    hbar(axes[1][1], {k: A["importance_kind"].get(v, 0) for k, v in I.items()},
         "E. Variable importance method", list(I), red=["None"])
    C = {"Multiple models,\nstatistically supported": "복수 모형 + 통계적 뒷받침",
         "Multiple models,\nnumbers only": "복수 모형, 수치 나열만",
         "Single model,\nno comparison": "단일 모형(비교 없음)"}
    hbar(axes[1][2], {k: A["model_comparison"].get(v, 0) for k, v in C.items()},
         "F. How models were compared", list(C),
         red=["Multiple models,\nnumbers only", "Single model,\nno comparison"])
    fig.tight_layout()
    save(fig, "fig6_pipeline")


def fig7_posthoc():
    """모형·사후분석 — 사용자 요청"""
    fig, (a1, a2) = plt.subplots(1, 2, figsize=(8.4, 3.2), gridspec_kw={"width_ratios": [1.15, 1]})
    P = {"Regression alongside ML": "회귀 병행 분석", "Bootstrap CI": "부트스트랩 신뢰구간",
         "Subgroup analysis": "하위군 분석", "Calibration assessment": "보정 평가",
         "Decision curve analysis": "결정곡선분석(DCA)", "DeLong test": "DeLong 검정",
         "Sensitivity analysis": "민감도 분석"}
    ks = list(P); vs = [A["posthoc"].get(P[k], 0) for k in ks]
    a1.barh(range(len(ks)), vs, color=BLUE, height=0.62)
    a1.set_yticks(range(len(ks))); a1.set_yticklabels(ks, fontsize=7.5); a1.invert_yaxis()
    for i, v in enumerate(vs): a1.text(v + 0.4, i, str(v), va="center", fontsize=7.2)
    a1.set_xlim(0, max(vs) * 1.25); a1.set_xlabel("Studies (n)")
    a1.set_title(f"A. Post hoc statistical analyses\n"
                 f"(any: {A['n_any_posthoc']}/{A['n_include']}; none: {A['n_no_posthoc']})",
                 loc="left", fontsize=8.6, weight="bold")
    npm = A["n_models_per_paper"]
    ks2 = sorted(int(k) for k in npm)
    a2.bar([str(k) for k in ks2], [npm[str(k)] if str(k) in npm else npm[k] for k in ks2],
           color=[RED if k <= 1 else BLUE for k in ks2], width=0.72)
    a2.set_xlabel("Model families compared per study"); a2.set_ylabel("Studies (n)")
    a2.set_title("B. Breadth of model comparison", loc="left", fontsize=8.6, weight="bold")
    a2.tick_params(axis="x", labelsize=7)
    fig.tight_layout()
    save(fig, "fig7_posthoc")


def fig5_probast():
    """PROBAST 영역·신호질문 + TRIPOD 준수율"""
    B = json.load(open(os.path.join(PROJ, "results/derived/probast.json")))
    fig, (a1, a2) = plt.subplots(1, 2, figsize=(7.4, 3.4), gridspec_kw={"width_ratios": [1, 1.15]})
    doms = [("Participants", "D1"), ("Predictors", "D2"), ("Outcome", "D3"), ("Analysis", "D4")]
    lows = [B["domain"][d]["low"] if "low" in B["domain"][d] else 0 for _, d in doms]
    uncs = [B["domain"][d].get("unclear", 0) for _, d in doms]
    highs = [B["domain"][d].get("high", 0) for _, d in doms]
    names = [n for n, _ in doms] + ["Overall"]
    lows.append(B["overall"].get("low", 0)); uncs.append(B["overall"].get("unclear", 0)); highs.append(B["overall"].get("high", 0))
    y = range(len(names))
    a1.barh(y, lows, color="#8bbf9f", label="Low", height=0.62)
    a1.barh(y, uncs, left=lows, color="#d9d9d9", label="Unclear", height=0.62)
    a1.barh(y, highs, left=[l + u for l, u in zip(lows, uncs)], color=RED, label="High", height=0.62)
    a1.set_yticks(list(y)); a1.set_yticklabels(names, fontsize=8); a1.invert_yaxis()
    a1.set_xlabel("Studies (n)"); a1.set_xlim(0, A["n_include"])
    a1.legend(fontsize=7, frameon=False, ncol=3, loc="lower center", bbox_to_anchor=(0.5, -0.30))
    a1.set_title("A. PROBAST risk of bias", loc="left", fontsize=9, weight="bold")
    items = [("Sample size justification", "sample_size_justification"), ("Code availability", "code_availability"),
             ("Model availability", "model_availability"), ("Missing data", "missing_data"),
             ("Data availability", "data_availability"), ("Structured abstract", "abstract_structured"),
             ("Eligibility criteria", "participants_eligibility"), ("Design in title", "title_design"),
             ("Predictor description", "predictors_description"), ("Funding statement", "funding"),
             ("Model evaluation", "model_evaluation"), ("Performance results", "results_performance"),
             ("Performance measures", "model_performance_measures"), ("Data source", "data_source"),
             ("Background/objective", "background_objective")]
    pct = [B["tripod_adherence"][k]["pct"] or 0 for _, k in items]
    a2.barh(range(len(items)), pct, color=[RED if p < 60 else BLUE for p in pct], height=0.66)
    a2.set_yticks(range(len(items))); a2.set_yticklabels([n for n, _ in items], fontsize=7.2)
    a2.set_xlabel("Studies reporting the item (%)"); a2.set_xlim(0, 105)
    for i, v in enumerate(pct): a2.text(v + 1.5, i, f"{v:.0f}", va="center", fontsize=6.8)
    a2.set_title("B. TRIPOD+AI item adherence", loc="left", fontsize=9, weight="bold")
    save(fig, "fig5_probast")


def fig9_quality_distributions(lang="en"):
    """Study-level quality and model-comparison distributions."""
    ko = lang == "ko"
    T = json.load(open(os.path.join(PROJ, "results", "derived", "tripod_stats.json")))
    refs = {r["key"] for r in json.load(open(os.path.join(PROJ,"references","refs.json"))) if r.get("verdict")=="INCLUDE"}
    prob=[]
    for p in glob.glob(os.path.join(PROJ,"data","probast","*.json")):
        d=json.load(open(p))
        if d.get("key") in refs: prob.append(d)
    general=[r["gen_pct"] for r in T["per_study"] if r.get("gen_pct") is not None]
    extension=[r["ext_pct"] for r in T["per_study"] if r.get("ext_pct") is not None]
    high_domains=[]
    for d in prob:
        high_domains.append(sum((((d.get("probast") or {}).get(k) or {}).get("judgment") == "high") for k in ("D1","D2","D3","D4")))

    fig,ax=plt.subplots(2,2,figsize=(8.8,5.8)); ax=ax.ravel()
    bins=np.arange(-2.5,107.6,10)
    ax[0].hist(general,bins=bins,color=BLUE,edgecolor="white")
    ax[0].axvline(np.median(general),color=RED,ls="--",lw=1.3)
    ax[0].text(np.median(general)+2,ax[0].get_ylim()[1]*.86,f"median {np.median(general):.1f}%",color=RED,fontsize=7)
    ax[0].set(xlim=(-3,103),xlabel="일반항목 준수율 (%)" if ko else "General-item adherence (%)",ylabel="연구 수" if ko else "Studies (n)")
    ax[0].set_title("A. 연구별 TRIPOD+AI 준수율" if ko else "A. Per-study TRIPOD+AI adherence",loc="left",fontsize=9,weight="bold")

    ax[1].hist(extension,bins=np.arange(-8.34,108.4,16.67),color="#c15c5c",edgecolor="white")
    ax[1].axvline(np.median(extension),color=GREY,ls="--",lw=1.3)
    ax[1].set(xlim=(-4,104),xlabel="조사설계 항목 준수율 (%)" if ko else "Survey-design adherence (%)",ylabel="연구 수" if ko else "Studies (n)")
    ax[1].set_title("B. 연구별 조사설계 확장항목 준수율" if ko else "B. Per-study survey-design adherence",loc="left",fontsize=9,weight="bold")
    ax[1].text(3,ax[1].get_ylim()[1]*.86,f"median {np.median(extension):.1f}%",color=GREY,fontsize=7)

    hd=Counter(high_domains); xs=list(range(5)); vals=[hd.get(x,0) for x in xs]
    ax[2].bar(xs,vals,color=["#8bbf9f" if x==0 else RED for x in xs],width=.72)
    for x,v in zip(xs,vals): ax[2].text(x,v+2,str(v),ha="center",fontsize=7)
    ax[2].set(xticks=xs,xlabel="고위험 PROBAST 영역 수" if ko else "High-risk PROBAST domains",ylabel="연구 수" if ko else "Studies (n)")
    ax[2].set_title("C. 연구별 비뚤림 위험 분포" if ko else "C. Per-study risk-of-bias distribution",loc="left",fontsize=9,weight="bold")

    comp=A["model_comparison"]
    keys=["단일 모형(비교 없음)","복수 모형, 수치 나열만","복수 모형 + 통계적 뒷받침"]
    labs=(["단일 모형","점 추정치만 비교","통계적 뒷받침"] if ko else ["Single model","Point estimates only","Statistically supported"])
    vals=[comp.get(k,0) for k in keys]
    ax[3].bar(range(3),vals,color=[GREY,"#d08b49",BLUE],width=.68)
    for x,v in enumerate(vals): ax[3].text(x,v+2,f"{v}\n({100*v/A['n_include']:.1f}%)",ha="center",fontsize=7)
    ax[3].set_xticks(range(3)); ax[3].set_xticklabels(labs,fontsize=7.3)
    ax[3].set_ylabel("연구 수" if ko else "Studies (n)")
    ax[3].set_title("D. 모형 비교 근거의 분포" if ko else "D. Distribution of model-comparison support",loc="left",fontsize=9,weight="bold")
    fig.tight_layout(h_pad=2.0,w_pad=2.0)
    save(fig,"fig9_quality_distributions_ko" if ko else "fig9_quality_distributions")


if __name__ == "__main__":
    os.makedirs(OUT, exist_ok=True)
    fig1_prisma(); fig2_trend(); fig3_overview()
    plt.rcParams["font.family"] = "NanumSquare"; fig3_overview("ko")
    plt.rcParams["font.family"] = "DejaVu Sans"
    fig3_cycles(); fig3c_scope(); fig4_models(); fig5_probast(); fig6_pipeline(); fig7_posthoc(); fig9_quality_distributions()
    plt.rcParams["font.family"] = "NanumSquare"; fig9_quality_distributions("ko")
    plt.rcParams["font.family"] = "DejaVu Sans"
    from make_pipeline_figures import make_all as make_pipeline_figures
    make_pipeline_figures()
    print(f"  → {os.path.relpath(OUT, PROJ)}/")
