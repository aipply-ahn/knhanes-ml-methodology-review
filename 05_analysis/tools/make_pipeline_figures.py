"""Create manuscript figures in literature-review and ML-workflow order."""
import os, sys, json, glob, csv, re
from collections import Counter

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import numpy as np
import matplotlib.pyplot as plt
from matplotlib.patches import FancyBboxPatch, FancyArrowPatch
from analyze_extraction import (missing, imbalance, validation, metric_depth, weights,
                                canon_model, posthoc, importance_kind, layers, wave_scope)
from canonical_data import included_extractions

PROJ = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
OUT = os.path.join(PROJ, "figures", "submission")
A = json.load(open(os.path.join(PROJ, "results/derived/analysis.json")))
R = {r["key"]: r for r in json.load(open(os.path.join(PROJ, "references/refs.json")))}
E = included_extractions()
INC = E
PRED = [d for d in INC if d.get("task") in ("classification", "regression")]
CLS = [d for d in INC if d.get("task") == "classification"]
CLS_AUDIT = [d for d in INC if d.get("task") == "classification"]
N_INC, N_PRED, N_CLS = len(INC), len(PRED), len(CLS_AUDIT)
# Okabe-Ito-derived, colour-vision-deficiency-safe palette.  Blue denotes a
# documented/desired practice, vermillion a deficit, and grey unknown/absent.
BLUE, RED, GREY = "#0072B2", "#D55E00", "#6B7280"
GREEN, ORANGE, PURPLE, SKY = "#009E73", "#E69F00", "#CC79A7", "#56B4E9"
PALETTE = [BLUE, SKY, PURPLE, GREEN, ORANGE, RED, "#8C6D5A", "#B8B8B8"]


def save(fig, name):
    for ext in ("pdf", "png"):
        fig.savefig(os.path.join(OUT, f"{name}.{ext}"), bbox_inches="tight", dpi=450,
                    facecolor="white")
    plt.close(fig)


def style(lang):
    plt.rcParams.update({"font.family": "NanumSquare" if lang == "ko" else "DejaVu Sans",
                         "font.size": 10, "axes.titlesize": 10.5,
                         "axes.labelsize": 9.5, "xtick.labelsize": 8.5,
                         "ytick.labelsize": 8.5, "legend.fontsize": 8,
                         "axes.spines.top": False, "axes.spines.right": False,
                         "axes.linewidth": .7, "lines.linewidth": 1.7,
                         "pdf.fonttype": 42, "ps.fonttype": 42,
                         "savefig.dpi": 450})


def barh(ax, labels, vals, title, colors=None, xlabel=None, xmax=None):
    colors = colors or [BLUE] * len(vals)
    y = np.arange(len(labels))
    ax.barh(y, vals, color=colors, height=.66)
    ax.set_yticks(y); ax.set_yticklabels(labels, fontsize=8.1); ax.invert_yaxis()
    m = max(vals) if vals else 1
    for i, v in enumerate(vals): ax.text(v + m*.018, i, str(v), va="center", fontsize=8)
    ax.set_xlim(0, xmax or m*1.20); ax.set_title(title, loc="left", fontsize=10.2, weight="bold")
    ax.grid(axis="x", color="#E5E7EB", linewidth=.6, zorder=0)
    ax.set_axisbelow(True)
    # Use the axis itself for the numeric meaning; repeating "(n)" on every
    # count axis adds clutter and is not needed when denominators sit in titles.
    if xlabel == "Studies (n)":
        xlabel = "Studies"
    if xlabel: ax.set_xlabel(xlabel)


def donut(ax, labels, vals, title, center):
    total = sum(vals)
    ax.pie(vals, startangle=90, counterclock=False, colors=PALETTE[:len(vals)],
           wedgeprops={"width": .38, "edgecolor": "white"})
    ax.text(0, .04, center, ha="center", va="center", fontsize=9.5, weight="bold")
    ax.legend([f"{x} — {v} ({100*v/total:.1f}%)" for x,v in zip(labels,vals)],
              loc="upper center", bbox_to_anchor=(.5,-.02), frameon=False,
              fontsize=6.4, handlelength=1, labelspacing=.3)
    ax.set_title(title, loc="left", fontsize=9, weight="bold")


def fig2_publication(lang="en"):
    style(lang); ko = lang == "ko"
    M=json.load(open(os.path.join(PROJ,"results/derived/master_manuscript_results.json")))
    years=sorted((int(k),v) for k,v in M['years'].items()); xs=[x for x,_ in years]; ns=[v for _,v in years]
    fig,ax=plt.subplots(2,2,figsize=(10.5,7.0)); ax=ax.ravel()
    ax[0].bar(xs,ns,color=BLUE,width=.75); ax[0].set_xticks(range(2009,2027,2)); ax[0].set_ylabel('연구 수' if ko else 'Studies (n)'); ax[0].set_title('A. 연도별 출판량' if ko else 'A. Annual publication volume',loc='left',weight='bold')
    ax[0].annotate('9월까지' if ko else 'Through September',xy=(2026,dict(years)[2026]),xytext=(2021,37),fontsize=7,color=GREY,arrowprops={'arrowstyle':'->','color':GREY})
    ax[1].plot(xs,np.cumsum(ns),color=ORANGE,marker='o',ms=3); ax[1].set_xticks(range(2009,2027,2)); ax[1].set_ylabel('누적 연구 수' if ko else 'Cumulative studies'); ax[1].set_title('B. 누적 근거' if ko else 'B. Cumulative evidence',loc='left',weight='bold')
    t=M['tasks_by_year']; bottoms=np.zeros(len(xs))
    task_labels={'CLS':'분류','CONT':'연속형 결과','OTHER':'기타'} if ko else {'CLS':'Classification','CONT':'Continuous outcome','OTHER':'Other'}
    for key,label,col in [('CLS',task_labels['CLS'],BLUE),('CONT',task_labels['CONT'],ORANGE),('OTHER',task_labels['OTHER'],GREY)]:
        vals=np.array([t[str(y)].get(key,0) for y in xs]); ax[2].bar(xs,vals,bottom=bottoms,color=col,label=label); bottoms+=vals
    ax[2].set_xticks(range(2009,2027,2)); ax[2].set_ylabel('연구 수' if ko else 'Studies (n)'); ax[2].set_title('C. 연도별 주 분석 과제' if ko else 'C. Primary analytic task by year',loc='left',weight='bold'); ax[2].legend(frameon=False,fontsize=7)
    topic_labels={'mental_health':'Mental health','diabetes':'Diabetes','cvd':'Cardiovascular disease','osteoporosis_sarcopenia':'Bone/muscle','nutrition_diet':'Nutrition/diet','other':'Other topics','metabolic_syndrome':'Metabolic syndrome','oral_health':'Oral health'}
    topic_labels_ko={'mental_health':'정신건강','diabetes':'당뇨','cvd':'심혈관질환','osteoporosis_sarcopenia':'골·근육','nutrition_diet':'영양·식이','other':'기타 주제','metabolic_syndrome':'대사증후군','oral_health':'구강건강'}
    top=sorted(M['topics'].items(),key=lambda z:-z[1])[:8]; labs=topic_labels_ko if ko else topic_labels
    barh(ax[3],[labs.get(k,k) for k,v in top],[v for k,v in top],'D. 주요 건강주제' if ko else 'D. Leading health topics',[BLUE]*8,'연구 수' if ko else 'Studies (n)')
    fig.tight_layout(h_pad=2.2,w_pad=2.4); save(fig,"fig2_publication_ko" if ko else "fig2_publication")


def fig3_problem(lang="en"):
    style(lang); ko=lang=="ko"
    fig,ax=plt.subplots(1,3,figsize=(13.2,4.0)); ax=ax.ravel()
    final=json.load(open(os.path.join(PROJ,"results/derived/protocol_v1_2_consensus_results.json")))
    ncls=final["denominators"]["classification"]; c=final["classification"]
    timing=Counter(c["outcome_timing"])
    timing_rows=[("Diagnostic/current state","진단·현재상태","diagnostic_current"),
                 ("Prognostic/future outcome","예후·미래결과","prognostic_future"),
                 ("Unclear","불명확","UNC")]
    timing['diagnostic_current']=timing['CURRENT']; timing['prognostic_future']=timing['FUTURE']
    barh(ax[0],[b if ko else a for a,b,k in timing_rows],[timing[k] for a,b,k in timing_rows],
         f"A. 결과 시간관계\n(합의; n={ncls})" if ko else f"A. Outcome timing\n(adjudicated; n={ncls})",
         [BLUE,ORANGE,GREY],"연구 수" if ko else "Studies (n)")
    outcome=Counter(c["outcome_adequacy"]); predictor=Counter(c["predictor_adequacy"])
    oo=[("Robust","강건"),("Limited","제한적"),("High concern","높은 우려"),("Not assessable","판단 불가")]
    omap={'Robust':'ROBUST','Limited':'LIMITED','High concern':'HIGH','Not assessable':'NAU'}
    barh(ax[1],[b if ko else a for a,b in oo],[outcome.get(omap[a],0) for a,b in oo],
         f"B. 목적변수 구성 적절성\n(합의; n={ncls})" if ko else f"B. Outcome-construction adequacy\n(adjudicated; n={ncls})",
         [GREEN,ORANGE,RED,GREY],"연구 수" if ko else "Studies (n)")
    po=[("Robust","강건"),("Limited","제한적"),("High concern","높은 우려"),("Not assessable","판단 불가")]
    pmap={'Robust':'ROBUST','Limited':'LIMITED','High concern':'HIGH','Not assessable':'NAU'}
    barh(ax[2],[b if ko else a for a,b in po],[predictor.get(pmap[a],0) for a,b in po],
         f"C. 설명변수 구성·정합성\n(합의; n={ncls})" if ko else f"C. Predictor construction and alignment\n(adjudicated; n={ncls})",
         [GREEN,ORANGE,RED,GREY],"연구 수" if ko else "Studies (n)")
    fig.text(.5,.012,("블라인드 LLM P2 및 사전 규칙 기반 조정 완료" if ko else
                      "Blinded LLM P2 and prespecified rule-based reconciliation complete"),ha="center",fontsize=7,color=GREY)
    fig.tight_layout(rect=(0,.07,1,1),w_pad=2.5)
    save(fig,"fig3_problem_ko" if ko else "fig3_problem")


def fig3b_target_definition(lang="en"):
    """Describe how classification outcomes were constructed and converted to classes."""
    style(lang); ko=lang=="ko"
    T=json.load(open(os.path.join(PROJ,"results/derived/target_definition_audit.json")))
    C=T["counters"]
    fig,ax=plt.subplots(2,2,figsize=(10,7)); ax=ax.ravel()

    co=[("Continuous/score variable discretised","연속값·점수 이산화"),
        ("Composite clinical rule","복합 임상 규칙"),
        ("Existing categorical response/diagnosis","기존 범주·진단"),
        ("Ordinal categories collapsed or retained","순서범주 축소·유지"),
        ("Construction not recoverable","구성 확인 불가")]
    co_vals=[C["outcome_construction"].get(a,0) for a,b in co]
    barh(ax[0],[b if ko else a for a,b in co],co_vals,
         f"A. 목적변수 구성 (n={N_CLS})" if ko else f"A. Outcome construction (n={N_CLS})",
         [BLUE,SKY,SKY,SKY,RED],"연구 수" if ko else "Studies (n)")

    so=[("Binary only","이진 분류"),("Multiple binary endpoints","여러 이진 결과"),
        ("Multiclass only","다중분류"),("Both binary and multiclass","이진+다중분류"),
        ("Class count not recoverable","클래스 수 확인 불가")]
    so_vals=[C["classification_scheme"].get(a,0) for a,b in so]
    barh(ax[1],[b if ko else a for a,b in so],so_vals,
         f"B. 분류 구조 (n={N_CLS})" if ko else f"B. Classification structure (n={N_CLS})",
         [BLUE,SKY,SKY,SKY,RED],"연구 수" if ko else "Studies (n)")

    bo=[("Clinical guideline/diagnostic standard","임상 지침·진단기준"),
        ("Validated scale or instrument convention","검증 척도·도구 관례"),
        ("Reference population or prior literature","참조집단·선행문헌"),
        ("Data-driven distribution or optimisation","자료분포·최적화"),
        ("Numeric rule reported; rationale not stated","수치만 보고·근거 미기재"),
        ("Basis not recoverable","근거 확인 불가")]
    barh(ax[2],[b if ko else a for a,b in bo],[T["threshold_basis"].get(a,0) for a,b in bo],
         f"C. 이산화·범주화 기준의 근거 (n={T['n_threshold_relevant']})" if ko else f"C. Basis for discretisation/categorisation (n={T['n_threshold_relevant']})",
         [BLUE,GREEN,PURPLE,ORANGE,RED,GREY],"연구 수" if ko else "Studies (n)",50)

    reported=C["cutoff_reported"].get("Reported",0)
    notrec=C["cutoff_reported"].get("Not recoverable",0)-C["outcome_construction"].get("Construction not recoverable",0)
    vals=[reported,max(notrec,0),C["definition_status"].get("Not recoverable",0)]
    labs=(["수치·규칙 보고\n(범주화 연구)","범주화했으나\n기준 확인 불가","목적변수 구성\n확인 불가"] if ko else
          ["Rule reported\n(categorised outcomes)","Categorised but rule\nnot recoverable","Outcome construction\nnot recoverable"])
    ax[3].bar(range(3),vals,color=[BLUE,RED,GREY]); ax[3].set_xticks(range(3)); ax[3].set_xticklabels(labs,fontsize=7)
    ax[3].set_ylabel("연구 수" if ko else "Studies (n)")
    ax[3].set_title("D. 목적변수 정의의 재현 가능성" if ko else "D. Recoverability of outcome definition",loc="left",weight="bold",fontsize=9)
    for i,v in enumerate(vals): ax[3].text(i,v+2,str(v),ha="center",fontsize=8)
    ax[3].set_ylim(0,max(vals)*1.18)
    fig.tight_layout(h_pad=2,w_pad=2); save(fig,"fig3b_target_definition_ko" if ko else "fig3b_target_definition")


def fig4_data(lang="en"):
    style(lang); ko=lang=="ko"; fig,ax=plt.subplots(2,2,figsize=(9,6)); ax=ax.ravel()
    so=[("Single year","단년도","단년"),("Multiple, same cycle","다년도·같은 기수","복수년 · 같은 기수"),("Multiple, across cycles","다년도·기수 넘음","복수년 · 기수 넘음"),("Years unclear","연도 불명","연도 불명")]
    barh(ax[0],[x[1] if ko else x[0] for x in so],[A["wave_scope"].get(x[2],0) for x in so],"A. 조사연도 범위" if ko else "A. Survey-year scope",[BLUE,BLUE,PURPLE,GREY],"연구 수" if ko else "Studies (n)")
    lay=[("Examination","검진","검진(검사·계측)"),("Questionnaire","설문","설문(건강행태·사회경제)"),("Dietary","영양","영양(식이)"),("Oral health","구강","구강"),("Linked data","연계자료","연계자료")]
    barh(ax[1],[x[1] if ko else x[0] for x in lay],[A["data_layer"].get(x[2],0) for x in lay],"B. 사용한 조사영역" if ko else "B. Survey components used",[BLUE,BLUE,GREEN,ORANGE,RED],"연구 수(중복 허용)" if ko else "Studies (multiple permitted)")
    samples=[d["n_final"] for d in CLS_AUDIT if isinstance(d.get("n_final"),int) and d["n_final"]>0]
    bins=np.logspace(np.log10(100),np.log10(300000),12); ax[2].hist(samples,bins=bins,color=BLUE,edgecolor="white"); ax[2].set_xscale("log"); ax[2].set_title(f"C. 분석 표본 수 (보고 {len(samples)}/{N_CLS}편)" if ko else f"C. Analytic sample size (reported {len(samples)}/{N_CLS})",loc="left",weight="bold",fontsize=9); ax[2].set_xlabel("대상자 수 (로그 축)" if ko else "Participants (log scale)"); ax[2].set_ylabel("연구 수" if ko else "Studies (n)"); ax[2].axvline(np.median(samples),ls="--",color=RED)
    rows={}
    with open(os.path.join(PROJ,"data/input_counts.tsv"),encoding="utf-8-sig") as f:
        for r in csv.DictReader(f,delimiter="\t"):
            if r.get("n_variables"): rows[r["key"]]=int(r["n_variables"])
    vals=[rows[d["key"]] for d in CLS_AUDIT if d["key"] in rows]
    ax[3].hist(vals,bins=[1,5,10,20,50,100,250,500,1000,2500],color=GREEN,edgecolor="white"); ax[3].set_xscale("log"); ax[3].set_title(f"D. 후보·입력 변수 수 (보고 {len(vals)}/{N_CLS}편)" if ko else f"D. Candidate/input variables (reported {len(vals)}/{N_CLS})",loc="left",weight="bold",fontsize=9); ax[3].set_xlabel("변수 수 (로그 축)" if ko else "Variables (log scale)"); ax[3].set_ylabel("연구 수" if ko else "Studies (n)"); ax[3].axvline(np.median(vals),ls="--",color=RED)
    fig.tight_layout(h_pad=2); save(fig,"fig4_data_ko" if ko else "fig4_data")


def fig5_preprocessing(lang="en"):
    style(lang); ko=lang=="ko"; fig,ax=plt.subplots(2,2,figsize=(9,5.8)); ax=ax.ravel()
    final=json.load(open(os.path.join(PROJ,"results/derived/protocol_v1_2_consensus_results.json")))
    c=final["classification"]; ncls=final["denominators"]["classification"]
    mc=c["missing_primary"]
    mo=[("Complete case","완전사례","COMPLETE"),("Single imputation","단일대체","SINGLE_IMP"),("Multiple imputation","다중대체","MULTI_IMP"),("Multiple strategies","복수전략","MULTIPLE"),("Model-native/indicator","모형내장·지시자","MODEL_NATIVE_INDICATOR"),("Other","기타","OTHER"),("Not reported","미보고","NR")]
    mvals=[mc.get(k,0) if k!="MODEL_NATIVE_INDICATOR" else mc.get("MODEL_NATIVE",0)+mc.get("INDICATOR",0) for _,_,k in mo]
    barh(ax[0],[b if ko else a for a,b,_ in mo],mvals,f"A. 결측자료 처리 (합의; n={ncls})" if ko else f"A. Missing-data handling (adjudicated; n={ncls})",[BLUE,SKY,GREEN,PURPLE,PURPLE,GREY,RED],"연구 수" if ko else "Studies (n)")
    ic=c["imbalance_primary"]
    io=[("No active intervention","적극적 개입 없음","NONE"),("SMOTE/ADASYN","SMOTE/ADASYN","SMOTE"),("Random over/undersampling","무작위 과·소표집","RANDOM"),("Weighting/cost-sensitive","가중·비용민감","WEIGHT"),("Multiple strategies","복수전략","MULTIPLE"),("Other","기타","OTHER"),("Not reported","미보고","NR")]
    barh(ax[1],[b if ko else a for a,b,_ in io],[ic.get(k,0) for _,_,k in io],f"B. 클래스 불균형 (합의; n={ncls})" if ko else f"B. Class imbalance (adjudicated; n={ncls})",[SKY,BLUE,GREEN,PURPLE,ORANGE,GREY,RED],"연구 수" if ko else "Studies (n)")
    cr=c["class_recoverability"]
    ro=[("Recoverable","복원 가능","R"),("Partly recoverable","부분 복원","P"),("Not recoverable","복원 불가","NR"),("Unclear","불명확","UNC")]
    barh(ax[2],[b if ko else a for a,b,_ in ro],[cr.get(k,0) for _,_,k in ro],f"C. 클래스 분포 복원 가능성 (합의; n={ncls})" if ko else f"C. Class-distribution recoverability (adjudicated; n={ncls})",[GREEN,SKY,RED,GREY],"연구 수" if ko else "Studies (n)")
    th=c["threshold_primary"]
    to=[("Not reported","미보고","NR"),("Not applicable","해당 없음","NA"),("Youden index","Youden 지수","YOUDEN"),("Fixed 0.5","0.5 고정","FIXED05"),("Clinical rule","임상 기준","CLINICAL"),("Validation/OOF","검증·OOF","VAL_OOF"),("F1 optimised","F1 최적화","F1"),("Other","기타","OTHER")]
    barh(ax[3],[b if ko else a for a,b,_ in to],[th.get(k,0) for _,_,k in to],f"D. 의사결정 역치 선택 (합의; n={ncls})" if ko else f"D. Decision-threshold selection (adjudicated; n={ncls})",[RED,GREY,BLUE,SKY,GREEN,GREEN,ORANGE,PURPLE],"연구 수" if ko else "Studies (n)")
    fig.tight_layout(h_pad=2,w_pad=2); save(fig,"fig5_preprocessing_ko" if ko else "fig5_preprocessing")


def predictive_model_counts():
    comp,best,nm=Counter(),Counter(),Counter()
    # Classifier families are summarised only within the prespecified core
    # classification cohort; continuous and other tasks are synthesised separately.
    for d in CLS_AUDIT:
        ms=set(filter(None,(canon_model(m) for m in d.get("models",[])))); nm[len(ms)]+=1
        for m in ms: comp[m]+=1
        b=canon_model(d.get("best_model"));
        if b: best[b]+=1
    return comp,best,nm


def fig6_modeling(lang="en"):
    style(lang); ko=lang=="ko"; fig,ax=plt.subplots(1,2,figsize=(9,4),gridspec_kw={"width_ratios":[1.4,1]})
    comp,best,nm=predictive_model_counts(); models=[m for m,_ in comp.most_common(12)]; y=np.arange(len(models))
    ax[0].barh(y+.18,[comp[m] for m in models],height=.35,color="#b9cde0",label="평가됨" if ko else "Evaluated"); ax[0].barh(y-.18,[best[m] for m in models],height=.35,color=BLUE,label="최고로 보고됨" if ko else "Reported as best"); ax[0].set_yticks(y); ax[0].set_yticklabels(models,fontsize=7); ax[0].invert_yaxis(); ax[0].set_xlabel("연구 수" if ko else "Studies (n)"); ax[0].set_title("A. 평가된 알고리즘과 최고로 보고된 알고리즘" if ko else "A. Algorithms evaluated and reported as best",loc="left",weight="bold",fontsize=9); ax[0].legend(frameon=False,fontsize=7)
    # Selection rates contextualise unequal opportunities to be named best.  They
    # are descriptive only because studies used heterogeneous metrics, ties, and splits.
    for i,m in enumerate(models):
        if best[m]: ax[0].text(comp[m]+2,i-.18,f"{100*best[m]/comp[m]:.0f}%",va="center",fontsize=6.5,color=BLUE)
    ks=sorted(nm); ax[1].bar([str(k) for k in ks],[nm[k] for k in ks],color=[RED if k<=1 else BLUE for k in ks]); ax[1].set_xlabel("연구당 모형 계열 수" if ko else "Model families per study"); ax[1].set_ylabel("연구 수" if ko else "Studies (n)"); ax[1].set_title("B. 모형 비교의 폭" if ko else "B. Breadth of model comparison",loc="left",weight="bold",fontsize=9)
    fig.tight_layout(w_pad=2); save(fig,"fig6_modeling_ko" if ko else "fig6_modeling")


def fig7_evaluation(lang="en"):
    style(lang); ko=lang=="ko"; fig,ax=plt.subplots(2,2,figsize=(9,6)); ax=ax.ravel()
    final=json.load(open(os.path.join(PROJ,"results/derived/protocol_v1_2_consensus_results.json")))
    c=final["classification"]; ncls=final["denominators"]["classification"]
    def pctbar(a, labels, vals, title, colors):
        y=np.arange(len(labels)); a.barh(y,vals,color=colors,height=.66); a.set_yticks(y); a.set_yticklabels(labels,fontsize=7.2); a.invert_yaxis()
        m=max(vals) if vals else 1
        for i,v in enumerate(vals): a.text(v+m*.018,i,f"{v} ({100*v/ncls:.1f}%)",va="center",fontsize=6.7)
        a.set_xlim(0,m*1.34); a.set_xlabel("연구 수" if ko else "Studies (n)"); a.grid(axis="x",color="#E5E7EB",linewidth=.6); a.set_axisbelow(True); a.set_title(title,loc="left",weight="bold",fontsize=9)
    vc=c["validation"]
    vo=[("Single split","단일 분할","SPLIT"),("Cross-validation","교차검증","CV"),("Apparent","외관 평가","APPARENT"),("Temporal","시간 검증","TEMPORAL"),("External","외부 검증","EXTERNAL"),("None/not reported","없음·미보고","NONE_NR")]
    barh(ax[0],[b if ko else a for a,b,_ in vo],[vc[k] for _,_,k in vo],f"A. 검증 방식 (합의; n={ncls})" if ko else f"A. Validation approach (adjudicated; n={ncls})",[ORANGE,BLUE,GREY,GREEN,GREEN,RED],"연구 수(중복 허용)" if ko else "Studies (multiple permitted)")
    q=c["metrics"]
    metrics=[("AUROC","AUROC","AUROC"),("Accuracy","정확도","ACC"),("Sensitivity/recall","민감도/재현율","SENS"),("Precision/PPV","정밀도/PPV","PPV"),("F1","F1","F1"),("Specificity/TNR","특이도/TNR","SPEC"),("AUPRC","AUPRC","AUPRC"),("Calibration plot","보정도","CALPLOT"),("Decision curve/net benefit","결정곡선/순편익","DCA"),("Brier score","Brier 점수","BRIER")]
    pctbar(ax[1],[b if ko else a for a,b,_ in metrics],[q[k] for _,_,k in metrics],"B. 분류 성능지표" if ko else "B. Classification performance metrics",[BLUE]*7+[GREEN,ORANGE,SKY])
    master=json.load(open(os.path.join(PROJ,"results/derived/master_manuscript_results.json")))
    crit=master['best_criterion']; co=[('AUROC','AUROC'),('Multiple metrics/author judgement','복수지표·저자판정'),('Other author criterion','기타 저자기준'),('Accuracy','정확도'),('F1','F1'),('Criterion not recoverable','기준 복원 불가')]
    pctbar(ax[2],[b if ko else a for a,b in co],[crit.get(a,0) for a,b in co],"C. 최고모형 지정 기준" if ko else "C. Best-model designation criterion",[BLUE,SKY,GREY,ORANGE,GREEN,RED])
    mr=c["metric_reporting"]
    uncertainty=[("Calibration plot","보정도",q["CALPLOT"]),("Confidence interval","신뢰구간",mr["MET_CI"]),("SD/resampling distribution","반복표집 분포",mr["MET_SD"]),("Paired model comparison","짝지은 모형 비교",mr["MET_PAIR"])]
    pctbar(ax[3],[b if ko else a for a,b,_ in uncertainty],
           [v for _,_,v in uncertainty],
           "D. 보정과 비교 불확실성" if ko else "D. Calibration and comparative uncertainty",
           [GREEN,SKY,ORANGE,RED])
    fig.tight_layout(h_pad=2,w_pad=2); save(fig,"fig7_evaluation_ko" if ko else "fig7_evaluation")


def fig8_interpretation(lang="en"):
    style(lang); ko=lang=="ko"
    D=json.load(open(os.path.join(PROJ,"results/derived/ml_rationale.json")))
    I=json.load(open(os.path.join(PROJ,"results/derived/importance_pathway.json")))["summary"]
    fig,ax=plt.subplots(2,2,figsize=(11.6,7.5)); ax=ax.ravel()

    keys=["performance_beyond_conventional_methods","clinical_screening_or_personalization",
          "complexity_nonlinearity_high_dimension","factor_discovery_or_interpretability",
          "methodological_or_data_problem","dynamic_or_deployed_prediction"]
    labs=["성능 우월 기대","선별·맞춤화","복잡성·비선형성","요인 탐색·해석","방법·자료 문제","동적·배치 맥락"] if ko else ["Expected performance gain","Screening/personalisation","Complexity/nonlinearity","Factor discovery","Method/data problem","Dynamic/deployment"]
    vals=[D["justification"][k] for k in keys]
    barh(ax[0],labs,vals,f"A. 서론의 머신러닝 정당화 (원문 n={D['n_full_text_coded']})" if ko else f"A. Rationale for ML (full text n={D['n_full_text_coded']})",[BLUE]*len(vals),"연구 수(중복 허용)" if ko else "Studies (multiple permitted)",125)

    # A stage-wise denominator display is more auditable than equal-width flow
    # arrows, which visually exaggerated the seven studies reaching inference.
    no_imp=I['n_predictive']-I['n_explicit_importance_method']
    rows=[
      (("모형 비교" if ko else "Model comparison"),
       [(I['n_algorithm_comparison'],BLUE,"비교" if ko else "Compared"),
        (I['n_predictive']-I['n_algorithm_comparison'],"#D1D5DB","비교 없음" if ko else "No comparison")]),
      (("변수 중요도" if ko else "Variable importance"),
       [(I['n_explicit_importance_method'],BLUE,"명시적 방법" if ko else "Explicit method"),
        (no_imp,"#D1D5DB","없음" if ko else "None")]),
      (("중요도 이후" if ko else "After importance"),
       [(I['n_explicit_importance_method']-I['n_importance_guided_inference'],SKY,"최종 산출물" if ko else "Final output"),
        (I['n_importance_guided_inference'],ORANGE,"후속 추론" if ko else "Inference")]),
    ]
    ax[1].set_xlim(0,I['n_predictive']); ax[1].set_ylim(-.65,2.65)
    for yi,(rowlab,segs) in enumerate(rows):
        left=0
        for value,color,label in segs:
            ax[1].barh(2-yi,value,left=left,height=.58,color=color,edgecolor="white",linewidth=1)
            if value >= 18:
                ax[1].text(left+value/2,2-yi,f"{label}\n{value}",ha="center",va="center",
                           fontsize=7.4,color="white" if color in (BLUE,ORANGE) else "#374151",weight="bold")
            else:
                ax[1].annotate(f"{label} {value}",xy=(left+value/2,2-yi),xytext=(left+value/2,2-yi-.43),
                               ha="center",va="top",fontsize=7,color=ORANGE,
                               arrowprops={"arrowstyle":"-","color":ORANGE,"lw":.7})
            left+=value
    ax[1].set_yticks([2,1,0]); ax[1].set_yticklabels([x[0] for x in rows],fontsize=8)
    ax[1].set_xlabel("연구 수" if ko else "Studies (n)")
    ax[1].spines[['top','right','left']].set_visible(False); ax[1].tick_params(axis='y',length=0)
    ax[1].grid(axis='x',color='#E5E7EB',linewidth=.6); ax[1].set_axisbelow(True)
    ax[1].set_title(
        (f"B. 예측모형 분석이 멈춘 단계\n(후속 추론 {I['n_importance_guided_inference']}편 중 동일 변수 이월 {I['n_exact_carryover']}편)" if ko else
         f"B. Where predictive analyses stopped\n(exact carryover in {I['n_exact_carryover']}/{I['n_importance_guided_inference']} inference studies)"),
        loc="left",weight="bold",fontsize=10.2)

    order=["SHAP","Model-native importance","Permutation importance","PDP/ALE/ICE","LIME","Perturbation/ablation importance","Coefficient/statistic ranking","Tree/rule structure","Network/model-specific importance"]
    mlabs=["SHAP","모형 내장 변수 중요도","순열 변수 중요도","PDP/ALE/ICE","LIME","섭동·제거 변수 중요도","모형 계수·통계량 순위","트리·규칙 구조","네트워크 고유 변수 중요도"] if ko else order
    mvals=[I["importance_method_counts"].get(k,0) for k in order]
    barh(ax[2],mlabs,mvals,f"C. 변수 중요도·설명 방법\n(명시적 방법 n={I['n_explicit_importance_method']})" if ko else f"C. Variable-importance/explanation methods\n(explicit method n={I['n_explicit_importance_method']})",[BLUE,BLUE,GREEN,PURPLE,ORANGE,GREEN,GREY,GREY,GREY],"연구 수(중복 허용)" if ko else "Studies (multiple permitted)",80)

    # Build the panel directly from the audited guided-study records so a later
    # source correction cannot silently leave a stale hard-coded row or denominator.
    guided=I["guided_studies"]
    labels={"ahn2025discovering":"Ahn 2025","bhak2024machine":"Bhak 2024",
            "byeon2022exploring":"Byeon 2022","nam2021discovery":"Nam 2021",
            "kim2026predicting":"Kim 2026","wu2026development":"Wu 2026",
            "zhang2026online":"Zhang 2026"}
    studies=[labels[g["key"]] for g in guided]
    selected=[max(map(int,re.findall(r"\d+",g["selected_n"]))) for g in guided]
    inferred=[np.nan if g["inferential_n"].startswith("NR") else
              max(map(int,re.findall(r"\d+",g["inferential_n"]))) for g in guided]
    y=np.arange(len(studies)); ax[3].barh(y,selected,color="#b9cde0",height=.62,label="변수 중요도 단계 선택" if ko else "Selected by variable importance")
    ax[3].scatter(inferred,y,color=RED,s=28,zorder=3,label="후속 추론 투입" if ko else "Entered inferential analysis")
    ax[3].set_yticks(y); ax[3].set_yticklabels(studies,fontsize=7); ax[3].invert_yaxis(); ax[3].set_xlim(0,21)
    ax[3].set_xlabel("변수 수" if ko else "Variables (n)"); ax[3].set_title(f"D. 변수 중요도 기반 후속 추론\n(n={len(guided)})" if ko else f"D. Variable-importance-guided inference\n(n={len(guided)})",loc="left",weight="bold",fontsize=9)
    ax[3].legend(frameon=False,fontsize=6.3,loc="upper center",bbox_to_anchor=(.5,-.17),ncol=2)
    ypos={g["key"]:i for i,g in enumerate(guided)}
    ax[3].text(11.3,ypos["bhak2024machine"],"추론 변수 수 미확정" if ko else "inference set expanded",va="center",fontsize=6.3,color=GREY)
    ax[3].text(18.3,ypos["nam2021discovery"],"추론 변수 수 미확정" if ko else "inference set expanded",va="center",fontsize=6.3,color=GREY)
    ax[3].text(10.3,ypos["kim2026predicting"],"성인 7 / 노인 10" if ko else "7 adults / 10 older",va="center",fontsize=6.3)
    fig.tight_layout(h_pad=2.5,w_pad=3.2); save(fig,"fig8_interpretation_ko" if ko else "fig8_interpretation")


def fig5_analytic_function(lang="en"):
    """Central synthesis: rationale, actual function, ranking pathway, and claims."""
    style(lang); ko=lang=="ko"
    final=json.load(open(os.path.join(PROJ,"results/derived/protocol_v1_2_consensus_results.json")))
    D=final["content"]; I=final["classification"]["importance"]
    n=final["denominators"]["studies"]; ncls=final["denominators"]["classification"]
    fig,ax=plt.subplots(2,2,figsize=(11.8,7.7)); ax=ax.ravel()

    rkeys=["RAT_PERF","RAT_SCREEN","RAT_COMPLEX","RAT_FACTOR","RAT_METHOD","RAT_DEPLOY"]
    rlabs=(['성능 우월 기대','선별·맞춤화','복잡성·비선형성','요인 탐색·해석','방법·자료 문제','동적·배치 맥락'] if ko else
           ['Expected performance gain','Screening/personalisation','Complexity/nonlinearity',
            'Factor discovery/interpretation','Method/data problem','Dynamic/deployment'])
    barh(ax[0],rlabs,[D[k] for k in rkeys],
         f"A. 서론에서 제시한 ML 근거 (합의; n={n})" if ko else
         f"A. Stated rationale for ML (adjudicated; n={n})",
         [BLUE]*6,"연구 수(중복 허용)" if ko else "Studies (multiple permitted)",130)

    fkeys=['FUN_PRED','FUN_COMPARE','FUN_INTERP','FUN_PROCESS','FUN_TRANSPORT','FUN_TOOL']
    flabs=(['예측·분류','알고리즘 비교','변수·요인 해석','자료처리·증강','외부검증·이식','구현된 도구'] if ko else
           ['Prediction/classification','Algorithm comparison','Feature/factor interpretation',
            'Data processing/augmentation','External validation/transport','Implemented tool'])
    barh(ax[1],flabs,[D[k] for k in fkeys],
         f"B. 실제 분석 기능 (합의; n={n})" if ko else
         f"B. Actual analytic function (adjudicated; n={n})",
         [BLUE,SKY,GREEN,PURPLE,ORANGE,RED],"연구 수(중복 허용)" if ko else "Studies (multiple permitted)",225)

    stage_labels=(['분류연구','명시적 변수중요도','모형 기반 부분집합','후속 통계추론','동일 변수 정확 이월'] if ko else
                  ['Classification studies','Explicit variable importance','Model-guided subset',
                   'Downstream inference','Exact variable carryover'])
    stage_values=[ncls,I['VI01'],I['VI10'],I['VI11'],I['VI14']]
    barh(ax[2],stage_labels,stage_values,
         "C. 변수 중심 분석 경로" if ko else "C. Variable-centred analytic pathway",
         [BLUE,SKY,GREEN,ORANGE,RED],"연구 수" if ko else "Studies (n)",225)
    ax[2].text(.01,-.22,("각 단계는 더 엄격한 조작적 기준을 적용함" if ko else
                         "Each successive row applies a stricter operational criterion"),
               transform=ax[2].transAxes,fontsize=7,color=GREY)

    claim_labels=(['선별·맞춤화 주장','외부검증·보정 언급','실제 구현·배치 언급','복합표본 한계 언급',
                   '요인·연관성 주장','비인과성 주의'] if ko else
                  ['Screening/personalisation claim','External validation/calibration discussed','Implementation/deployment discussed',
                   'Complex-survey limitation discussed','Factor/association claim','Noncausal caveat'])
    claim_values=[D['CLM_SCREEN'],D['CLM_EXTVAL'],D['CLM_IMPLEMENT'],D['CLM_SURVEY'],D['CLM_FACTOR'],D['CLM_NONCAUSAL']]
    barh(ax[3],claim_labels,claim_values,
         "D. 독립적으로 코딩한 논의 주장" if ko else "D. Independently coded Discussion claims",
         [BLUE,GREEN,GREEN,GREEN,BLUE,ORANGE],"연구 수" if ko else "Studies (n)",165)
    ax[3].axhline(3.5,color='#D1D5DB',lw=.8)
    fig.text(.5,.008,("주장·기능 범주는 중복 허용; 동반 근거는 인과적 정당성을 판정하지 않음" if ko else
                      "Rationale, function, and claim categories may overlap; rows in panel D are not nested subsets"),
             ha='center',fontsize=7,color=GREY)
    fig.tight_layout(rect=(0,.035,1,1),h_pad=2.8,w_pad=3.3)
    save(fig,'fig5_analytic_function_ko' if ko else 'fig5_analytic_function')


def fig9_importance_endpoints(lang="en"):
    """Show where importance analyses ended, how this changed, and how variables were chosen."""
    style(lang); ko=lang=="ko"
    pathway=json.load(open(os.path.join(PROJ,"results/derived/importance_pathway.json")))["studies"]
    years={k:int(v["year"]) for k,v in R.items() if str(v.get("year","")).isdigit()}
    def period(y):
        return "≤2019" if y<=2019 else "2020–2022" if y<=2022 else "2023–2024" if y<=2024 else "2025–2026"
    periods=["≤2019","2020–2022","2023–2024","2025–2026"]
    by={p:Counter() for p in periods}
    for row in pathway:
        p=period(years[row["key"]]); by[p]["n"]+=1
        if not row["explicit_importance_method"]: by[p]["none"]+=1
        elif row["importance_guided_inference"]: by[p]["inference"]+=1
        else: by[p]["importance_final"]+=1

    with open(os.path.join(PROJ,"data/VARIABLE_IMPORTANCE_DETAILS.tsv"),encoding="utf-8-sig") as f:
        detail=list(csv.DictReader(f,delimiter="\t"))
    status=Counter(r["importance_selection_status"] for r in detail)
    strategy=Counter()
    for r in detail:
        strategy.update(r["selection_strategies"].split("; "))

    fig,ax=plt.subplots(2,2,figsize=(10,7)); ax=ax.ravel()
    endpoint=[sum(by[p]['none'] for p in periods),sum(by[p]['importance_final'] for p in periods),sum(by[p]['inference'] for p in periods)]
    endpoint_labs=(['변수 중요도\n없음','변수 중요도\n보고로 종료','후속\n통계추론'] if ko
                   else ['No variable\nimportance','Importance as\nfinal output','Forwarded to\ninference'])
    ax[0].bar(range(3),endpoint,color=[GREY,BLUE,GREEN])
    ax[0].set_xticks(range(3)); ax[0].set_xticklabels(endpoint_labs,fontsize=7)
    ax[0].set_ylabel('연구 수' if ko else 'Studies (n)')
    ax[0].set_title(f'A. 분류 분석의 최종 종착점 (n={N_CLS})' if ko else f'A. Final endpoint of classification analyses (n={N_CLS})',loc='left',weight='bold',fontsize=9)
    for i,v in enumerate(endpoint): ax[0].text(i,v+2,str(v),ha='center',fontsize=8)
    ax[0].set_ylim(0,125)

    bottom=np.zeros(len(periods))
    series=[('none',GREY,'변수 중요도 없음' if ko else 'No variable importance'),
            ('importance_final',BLUE,'변수 중요도 보고로 종료' if ko else 'Variable importance as final output'),
            ('inference',GREEN,'후속 통계추론' if ko else 'Forwarded to inference')]
    for key,color,label in series:
        vals=np.array([100*by[p][key]/by[p]['n'] for p in periods])
        ax[1].bar(periods,vals,bottom=bottom,color=color,label=label)
        bottom+=vals
    ax[1].set_xticks(range(len(periods)))
    ax[1].set_xticklabels(['≤2019','2020–\n2022','2023–\n2024','2025–\n2026'],fontsize=7)
    ax[1].set_ylim(0,100); ax[1].set_ylabel('%')
    ax[1].set_title('B. 모형 비교에서 중요변수 도출로의 이동' if ko else 'B. Shift from model comparison to variable importance',loc='left',weight='bold',fontsize=9)
    ax[1].legend(frameon=True,facecolor='white',framealpha=.9,edgecolor='none',fontsize=6.0,loc='center right')
    for i,p in enumerate(periods): ax[1].text(i,98,f"n={by[p]['n']}",ha='center',va='top',fontsize=6.4,color='white',weight='bold')

    status_order=['Importance/model-guided selection','Importance reported for ranking; subset determined otherwise or not reduced','Unreported']
    status_labs=(['모형 기반 부분집합 선택','순위만/다른 경로/축소 없음','선정 규칙 미보고'] if ko
                 else ['Model-guided subset','Ranking/other route/no reduction','Selection rule unreported'])
    vals=[status[x] for x in status_order]
    barh(ax[2],status_labs,vals,f'C. “중요변수”의 조작적 의미 (n={len(detail)})' if ko else f'C. Operational meaning of “important” (n={len(detail)})',[GREEN,BLUE,GREY],'연구 수' if ko else 'Studies (n)',60)

    strategy_order=['Expert/domain judgment','Penalized/statistical filter','Recursive/wrapper or performance-guided subset','No reduction/all prespecified inputs','Importance threshold, shadow, or cross-model consensus','Availability/missingness filter','Fixed top-k from model ranking','Expert/manual combined with model-guided selection']
    strategy_labs=(['전문가·도메인 판단','통계검정·벌점 필터','RFE·wrapper·성능 기준','축소 없이 전체 사용','임계값·Boruta·모형 합의','가용성·결측 필터','고정 Top-k','전문가+모형 기반'] if ko else
                   ['Expert/domain judgement','Statistical/penalised filter','RFE/wrapper/performance','No reduction','Threshold/Boruta/consensus','Availability/missingness','Fixed top-k','Expert + model-guided'])
    vals=[strategy[x] for x in strategy_order]
    barh(ax[3],strategy_labs,vals,'D. 중요변수 선정에 사용한 규칙' if ko else 'D. Rules used to designate important variables',[BLUE]*len(vals),'연구 수(중복 허용)' if ko else 'Studies (multiple permitted)',40)
    fig.tight_layout(h_pad=2,w_pad=2); save(fig,'fig9_importance_endpoints_ko' if ko else 'fig9_importance_endpoints')


def fig10_important_variables(lang="en"):
    """Show which broad variable domains recur in reported importance results."""
    style(lang); ko=lang=="ko"
    D=json.load(open(os.path.join(PROJ,"results/derived/important_variable_domains.json")))
    fig,ax=plt.subplots(2,2,figsize=(10,7)); ax=ax.ravel()
    coded=D['n_with_codable_variable_domains']; missing=D['n']-coded
    ax[0].bar(range(2),[coded,missing],color=[BLUE,GREY])
    ax[0].set_xticks(range(2)); ax[0].set_xticklabels(['변수명 코딩 가능','방법명만/변수명 불충분'] if ko else ['Variable domains\ncodable','Method only/insufficient\nvariable detail'],fontsize=7)
    ax[0].set_ylabel('연구 수' if ko else 'Studies (n)'); ax[0].set_ylim(0,90)
    ax[0].set_title(f"A. 중요변수 결과의 상세도 (n={D['n']})" if ko else f"A. Detail in importance results (n={D['n']})",loc='left',weight='bold',fontsize=9)
    for i,v in enumerate([coded,missing]): ax[0].text(i,v+2,str(v),ha='center',fontsize=8)

    overall=Counter(D['overall']); order=[k for k,v in overall.most_common(12)]
    ko_domains={'Age':'연령','Adiposity/body size':'비만·체격','Sex':'성별','Blood pressure/hypertension':'혈압·고혈압',
      'Glycaemia/diabetes/insulin':'혈당·당뇨·인슐린','Lipids':'지질','Kidney/urine':'신장·소변',
      'Mental/subjective health':'정신·주관적 건강','Socioeconomic/context':'사회경제·환경','Diet/nutrients':'식이·영양',
      'Physical activity/function':'신체활동·기능','Smoking':'흡연','Alcohol':'음주','Pain/musculoskeletal':'통증·근골격',
      'Work/clinical history':'근로·임상병력'}
    barh(ax[1],[ko_domains.get(x,x) if ko else x for x in order],[overall[x] for x in order],
         'B. 변수 중요도 결과에 반복된 변수군' if ko else 'B. Variable domains recurring in importance results',
         [BLUE]*len(order),'연구 수(중복 허용)' if ko else 'Studies (multiple permitted)',70)

    topics=['Mental health','Diabetes','Cardiovascular/HTN','Bone/muscle','Metabolic syndrome','Obesity/body composition','Oral health','Kidney disease']
    domains=['Age','Adiposity/body size','Mental/subjective health','Socioeconomic/context','Sex','Lipids','Glycaemia/diabetes/insulin','Blood pressure/hypertension','Smoking','Alcohol','Kidney/urine','Pain/musculoskeletal']
    mat=np.array([[100*D['by_topic'].get(t,{}).get(d,0)/D['topic_codable_n'].get(t,1) for d in domains] for t in topics])
    im=ax[2].imshow(mat,aspect='auto',cmap='Blues',vmin=0,vmax=100)
    topic_ko={'Mental health':'정신건강','Diabetes':'당뇨','Cardiovascular/HTN':'심혈관·고혈압','Bone/muscle':'골·근육',
              'Metabolic syndrome':'대사증후군','Obesity/body composition':'비만·체성분','Oral health':'구강','Kidney disease':'신장'}
    ax[2].set_yticks(range(len(topics))); ax[2].set_yticklabels([f"{topic_ko.get(t,t) if ko else t} (n={D['topic_codable_n'].get(t,0)})" for t in topics],fontsize=6.5)
    ax[2].set_xticks(range(len(domains))); ax[2].set_xticklabels([ko_domains.get(d,d) if ko else d for d in domains],rotation=55,ha='right',fontsize=5.7)
    for i in range(mat.shape[0]):
      for j in range(mat.shape[1]):
       if mat[i,j]>=25: ax[2].text(j,i,f"{mat[i,j]:.0f}",ha='center',va='center',fontsize=5.5,color='white' if mat[i,j]>55 else 'black')
    ax[2].set_title('C. 주제별 변수군 보고 비율 (%)' if ko else 'C. Variable-domain prevalence by topic (%)',loc='left',weight='bold',fontsize=9)
    fig.colorbar(im,ax=ax[2],fraction=.025,pad=.02,label='%')

    ax[3].axis('off'); ax[3].set_title('D. 주제별 가장 반복된 변수군' if ko else 'D. Most recurrent domains within topic',loc='left',weight='bold',fontsize=9)
    y=.93
    for t in topics:
      n=D['topic_codable_n'].get(t,0); top=Counter(D['by_topic'].get(t,{})).most_common(3)
      name=topic_ko.get(t,t) if ko else t
      vals=', '.join(f"{ko_domains.get(d,d) if ko else d} {v}/{n}" for d,v in top)
      ax[3].text(.01,y,f"{name}: {vals}",transform=ax[3].transAxes,fontsize=7.2,va='top'); y-=.115
    ax[3].text(.01,.01,'한 연구가 여러 변수군에 포함될 수 있음' if ko else 'A study may contribute to multiple domains.',transform=ax[3].transAxes,fontsize=6.5,color=GREY)
    fig.tight_layout(h_pad=2.4,w_pad=2); save(fig,'fig10_important_variables_ko' if ko else 'fig10_important_variables')


def fig9_quality(lang="en"):
    style(lang); ko=lang=="ko"; B=json.load(open(os.path.join(PROJ,"results/derived/probast.json"))); fig,ax=plt.subplots(1,2,figsize=(9,4.8),gridspec_kw={"width_ratios":[1,1.35]})
    dom=[("Participants","대상자","D1"),("Predictors","예측변수","D2"),("Outcome","결과","D3"),("Analysis","분석","D4")]; low=[B["domain"][x[2]].get("low",0) for x in dom]+[B["overall"].get("low",0)]; unc=[B["domain"][x[2]].get("unclear",0) for x in dom]+[B["overall"].get("unclear",0)]; high=[B["domain"][x[2]].get("high",0) for x in dom]+[B["overall"].get("high",0)]; labs=[x[1] if ko else x[0] for x in dom]+["전반" if ko else "Overall"]; y=np.arange(5); ax[0].barh(y,low,color="#8bbf9f",label="낮음" if ko else "Low"); ax[0].barh(y,unc,left=low,color="#d9d9d9",label="불명확" if ko else "Unclear"); ax[0].barh(y,high,left=np.array(low)+np.array(unc),color=RED,label="높음" if ko else "High"); ax[0].set_yticks(y); ax[0].set_yticklabels(labs); ax[0].invert_yaxis(); ax[0].set_xlim(0,224); ax[0].set_title("A. PROBAST 비뚤림 위험" if ko else "A. PROBAST risk of bias",loc="left",weight="bold",fontsize=9); ax[0].legend(frameon=False,fontsize=7,ncol=3,loc="lower center",bbox_to_anchor=(.5,-.16))
    items=[("title_design","Design in title","제목: 연구설계"),("abstract_structured","Structured abstract","초록: 구조화"),("background_objective","Background/objective","서론: 배경·목적"),("data_source","Data source/period","방법: 자료원·기간"),("participants_eligibility","Eligibility criteria","방법: 적격기준"),("outcome_definition","Outcome definition","방법: 결과변수"),("predictors_description","Predictor description","방법: 예측변수"),("sample_size_justification","Sample-size rationale","방법: 표본크기"),("missing_data","Missing data","방법: 결측처리"),("model_building","Model building","방법: 모형구축"),("model_evaluation","Model evaluation","방법: 모형평가"),("results_participants","Participant flow","결과: 대상자"),("model_performance_measures","Performance measures","결과: 성능지표"),("results_performance","Performance results","결과: 성능결과"),("limitations","Limitations","고찰: 한계"),("funding","Funding","기타: 연구비"),("data_availability","Data availability","기타: 자료공개"),("model_availability","Usable final model","기타: 최종모형"),("code_availability","Code availability","기타: 코드")]
    vals=[B["tripod_adherence"][k]["pct"] or 0 for k,_,_ in items]; labs=[x[2] if ko else x[1] for x in items]; y=np.arange(len(items)); ax[1].barh(y,vals,color=[RED if x<25 else ORANGE if x<60 else BLUE for x in vals]); ax[1].set_yticks(y); ax[1].set_yticklabels(labs,fontsize=6.6); ax[1].invert_yaxis(); ax[1].set_xlim(0,105); ax[1].set_xlabel("보고한 연구 (%)" if ko else "Studies reporting item (%)"); ax[1].set_title("B. 원고 흐름에 따른 TRIPOD+AI" if ko else "B. TRIPOD+AI in manuscript order",loc="left",weight="bold",fontsize=9)
    fig.tight_layout(w_pad=2); save(fig,"fig9_quality_ko" if ko else "fig9_quality")


def fig10_quality_trends(lang="en"):
    style(lang); ko=lang=="ko"; T=json.load(open(os.path.join(PROJ,"results/derived/tripod_stats.json"))); refs={d["key"] for d in INC}; prob=[]
    for p in glob.glob(os.path.join(PROJ,"data/probast/*.json")):
        d=json.load(open(p));
        if d.get("key") in refs: prob.append(d)
    gen=[x["gen_pct"] for x in T["per_study"] if x.get("gen_pct") is not None]
    ext=[x["ext_pct"] for x in T["per_study"] if x.get("ext_pct") is not None]
    hd=[sum((((d.get("probast") or {}).get(k) or {}).get("judgment") == "high")
            for k in ("D1","D2","D3","D4")) for d in prob]
    fig,ax=plt.subplots(2,2,figsize=(9,5.8)); ax=ax.ravel(); ax[0].hist(gen,bins=np.arange(-2.5,108,10),color=BLUE,edgecolor="white"); ax[0].axvline(np.median(gen),color=RED,ls="--"); ax[0].set_title("A. 연구별 일반 보고 준수율" if ko else "A. Per-study general reporting adherence",loc="left",weight="bold",fontsize=9); ax[0].set_xlabel("준수율 (%)" if ko else "Adherence (%)"); ax[0].set_ylabel("연구 수" if ko else "Studies (n)")
    ax[1].hist(ext,bins=np.arange(-8.34,108.4,16.67),color="#c15c5c",edgecolor="white"); ax[1].set_title("B. 연구별 조사설계 준수율" if ko else "B. Per-study survey-design adherence",loc="left",weight="bold",fontsize=9); ax[1].set_xlabel("준수율 (%)" if ko else "Adherence (%)"); ax[1].set_ylabel("연구 수" if ko else "Studies (n)")
    c=Counter(hd); xs=range(5); ax[2].bar(xs,[c[x] for x in xs],color=RED); ax[2].set_xticks(list(xs)); ax[2].set_xlabel("고위험 PROBAST 영역 수" if ko else "High-risk PROBAST domains"); ax[2].set_ylabel("연구 수" if ko else "Studies (n)"); ax[2].set_title("C. 연구별 고위험 영역" if ko else "C. High-risk domains per study",loc="left",weight="bold",fontsize=9)
    Q=json.load(open(os.path.join(PROJ,"results/derived/temporal_quality.json")))["periods"]
    labs=["≤2019","2020–22","2023–24","2025–26"]; qp=["≤2019","2020–2022","2023–2024","2025–2026"]
    pathway=json.load(open(os.path.join(PROJ,"results/derived/importance_pathway.json")))["studies"]
    def pp(y): return "≤2019" if y<=2019 else "2020–2022" if y<=2022 else "2023–2024" if y<=2024 else "2025–2026"
    pn=Counter(); pi=Counter()
    for r in pathway:
        p=pp(int(R[r["key"]]["year"])); pn[p]+=1; pi[p]+=bool(r["explicit_importance_method"])
    series=[("명시적 변수 중요도" if ko else "Explicit variable importance",[100*pi[p]/pn[p] for p in qp],BLUE,"o"),
            ("코드 공개" if ko else "Code available",[Q[p]["items"]["code_availability"]["pct"] for p in qp],GREEN,"s"),
            ("외부검증" if ko else "External validation",[Q[p]["external_pct"] for p in qp],ORANGE,"^"),
            ("학습 가중치" if ko else "Weights in fitting",[Q[p]["weights_fitting_pct"] for p in qp],RED,"D")]
    for name,vals,col,mark in series: ax[3].plot(labs,vals,label=name,color=col,marker=mark,lw=1.5)
    ax[3].set_ylim(-3,100); ax[3].set_ylabel("시기별 연구 비율 (%)" if ko else "Studies in period (%)"); ax[3].set_title("D. 방법론 관행의 시간 변화" if ko else "D. Methodological practice over time",loc="left",weight="bold",fontsize=9); ax[3].legend(frameon=False,fontsize=6.5)
    fig.tight_layout(h_pad=2,w_pad=2); save(fig,"fig10_quality_trends_ko" if ko else "fig10_quality_trends")


def fig14_topic_diversification(lang="en"):
    """Topic breadth increased, but relative diversity did not improve monotonically."""
    style(lang); ko=lang=="ko"
    T=json.load(open(os.path.join(PROJ,"results/derived/temporal_landscape.json")))['periods']
    periods=['≤2019','2020–2022','2023–2024','2025–2026']; short=['≤2019','2020–22','2023–24','2025–26']
    groups=['Mental health','Diabetes','Cardiovascular/HTN','Bone/muscle','Nutrition/diet','Metabolic syndrome','Oral health','Other topics']
    glabs=['정신건강','당뇨병','심혈관·고혈압','골·근육','영양·식이','대사증후군','구강건강','기타 주제'] if ko else groups
    fig,ax=plt.subplots(2,2,figsize=(10,7)); ax=ax.ravel(); x=np.arange(4)
    topic_mat=np.array([[100*T[p]['topic_counts_display'].get(g,0)/T[p]['n']
                         for p in periods] for g in groups])
    im0=ax[0].imshow(topic_mat,aspect='auto',cmap='Blues',vmin=0,vmax=max(35,topic_mat.max()))
    ax[0].set_xticks(x); ax[0].set_xticklabels(short)
    ax[0].set_yticks(range(len(groups))); ax[0].set_yticklabels(glabs,fontsize=7.4)
    for i in range(topic_mat.shape[0]):
        for j in range(topic_mat.shape[1]):
            v=topic_mat[i,j]
            ax[0].text(j,i,f'{v:.0f}',ha='center',va='center',fontsize=7,
                       color='white' if v>.58*topic_mat.max() else '#111827')
    ax[0].set_title('A. 시기별 연구 주제 구성 (%)' if ko else 'A. Topic composition by period (%)',loc='left',weight='bold',fontsize=10.2)
    fig.colorbar(im0,ax=ax[0],fraction=.035,pad=.025,label='%')

    observed=[T[p]['diversity']['observed_topics'] for p in periods]
    effective=[T[p]['diversity']['effective_topics'] for p in periods]
    ax[1].plot(x,observed,marker='o',color=BLUE,label='관찰 주제 수' if ko else 'Observed topics')
    ax[1].plot(x,effective,marker='s',color=GREEN,label='유효 주제 수, exp(H)' if ko else 'Effective topics, exp(H)')
    for i,(a,b) in enumerate(zip(observed,effective)):
        ax[1].text(i,a+.35,str(a),ha='center',fontsize=7,color=BLUE); ax[1].text(i,b-.7,f'{b:.1f}',ha='center',fontsize=7,color=GREEN)
    ax[1].set_xticks(x); ax[1].set_xticklabels(short); ax[1].set_ylim(0,17); ax[1].legend(frameon=False,fontsize=7)
    ax[1].set_title('B. 주제 범위는 넓어졌지만 지속 확대되지는 않음' if ko else 'B. Topic breadth widened but did not expand continuously',loc='left',weight='bold',fontsize=9)

    norm=[100*T[p]['diversity']['normalized_shannon'] for p in periods]
    top3=[T[p]['diversity']['top3_concentration_pct'] for p in periods]
    ax[2].plot(x,norm,marker='o',color=PURPLE,label='정규화 Shannon 다양성' if ko else 'Normalized Shannon diversity')
    ax[2].plot(x,top3,marker='s',color=ORANGE,label='상위 3개 주제 집중도' if ko else 'Top-three concentration')
    for i,v in enumerate(norm): ax[2].text(i,v+1.2,f'{v:.1f}',ha='center',fontsize=7,color=PURPLE)
    for i,v in enumerate(top3): ax[2].text(i,v-3.2,f'{v:.1f}',ha='center',fontsize=7,color=ORANGE)
    ax[2].set_xticks(x); ax[2].set_xticklabels(short); ax[2].set_ylim(35,100); ax[2].set_ylabel('%'); ax[2].legend(frameon=False,fontsize=7)
    ax[2].set_title('C. 상대적 다양성과 주제 집중도' if ko else 'C. Relative diversity and topic concentration',loc='left',weight='bold',fontsize=9)

    linegroups=['Mental health','Diabetes','Cardiovascular/HTN','Bone/muscle','Nutrition/diet']
    for j,g in enumerate(linegroups):
        vals=[T[p]['topic_counts_display'].get(g,0) for p in periods]
        ax[3].plot(x,vals,marker='o',lw=1.5,color=PALETTE[j],label=glabs[groups.index(g)])
    ax[3].set_xticks(x); ax[3].set_xticklabels(short); ax[3].set_ylabel('연구 수' if ko else 'Studies (n)'); ax[3].legend(frameon=False,fontsize=6.5,ncol=2)
    ax[3].set_title('D. 주요 주제의 절대 출판량' if ko else 'D. Absolute volume in leading topics',loc='left',weight='bold',fontsize=9)
    fig.tight_layout(h_pad=2.4,w_pad=3.4); save(fig,'fig14_topic_diversification_ko' if ko else 'fig14_topic_diversification')


def fig15_temporal_methods(lang="en"):
    """Temporal change in tasks, algorithms, year pooling, and variable-importance methods."""
    style(lang); ko=lang=="ko"
    T=json.load(open(os.path.join(PROJ,"results/derived/temporal_landscape.json")))['periods']
    periods=['≤2019','2020–2022','2023–2024','2025–2026']; short=['≤2019','2020–22','2023–24','2025–26']; x=np.arange(4)
    fig,ax=plt.subplots(2,2,figsize=(10,7)); ax=ax.ravel()
    taskgroups=[('classification','분류' if ko else 'Classification'),('regression','연속형 예측' if ko else 'Continuous prediction'),('other','비예측·구조적' if ko else 'Non-predictive/structural')]
    bottom=np.zeros(4)
    for j,(g,label) in enumerate(taskgroups):
        vals=[]
        for p in periods:
            c=T[p]['task_counts']; n=T[p]['n']; v=c.get(g,0) if g!='other' else n-c.get('classification',0)-c.get('regression',0); vals.append(100*v/n)
        ax[0].bar(x,vals,bottom=bottom,color=[BLUE,ORANGE,GREY][j],label=label); bottom+=vals
    ax[0].set_xticks(x); ax[0].set_xticklabels(short); ax[0].set_ylim(0,100); ax[0].set_ylabel('%'); ax[0].legend(frameon=False,fontsize=7)
    ax[0].set_title('A. 분석 과제: 분류 중심 구조 지속' if ko else 'A. Analytic tasks: persistent classification dominance',loc='left',weight='bold',fontsize=9)

    models=['Logistic regression','Random forest','XGBoost','SVM','LightGBM','DNN']
    mlabs=['로지스틱 회귀','랜덤포레스트','XGBoost','SVM','LightGBM','심층신경망'] if ko else models
    model_mat=np.array([[100*T[p]['model_counts'].get(m,0)/T[p]['n'] for p in periods] for m in models])
    im1=ax[1].imshow(model_mat,aspect='auto',cmap='Blues',vmin=0,vmax=75)
    ax[1].set_xticks(x); ax[1].set_xticklabels(short); ax[1].set_yticks(range(len(models))); ax[1].set_yticklabels(mlabs,fontsize=7.5)
    for i in range(model_mat.shape[0]):
      for j in range(model_mat.shape[1]):
       v=model_mat[i,j]; ax[1].text(j,i,f'{v:.0f}',ha='center',va='center',fontsize=7,color='white' if v>42 else '#111827')
    ax[1].set_title('B. 알고리즘 채택: 부스팅의 급증 (%)' if ko else 'B. Algorithm uptake: rapid growth of boosting (%)',loc='left',weight='bold',fontsize=10.2)
    fig.colorbar(im1,ax=ax[1],fraction=.035,pad=.025,label='%')

    scopes=[('단년','단년도' if ko else 'Single year'),('복수년 · 같은 기수','복수년·같은 기수' if ko else 'Multiple years, same cycle'),('복수년 · 기수 넘음','복수년·기수 초과' if ko else 'Across cycles'),('불명확','불명확' if ko else 'Unclear')]
    bottom=np.zeros(4)
    for j,(g,label) in enumerate(scopes):
        vals=[100*T[p]['wave_scope_counts'].get(g,0)/T[p]['n'] for p in periods]
        ax[2].bar(x,vals,bottom=bottom,color=[BLUE,GREEN,ORANGE,GREY][j],label=label); bottom+=vals
    ax[2].set_xticks(x); ax[2].set_xticklabels(short); ax[2].set_ylim(0,100); ax[2].set_ylabel('%'); ax[2].legend(frameon=False,fontsize=6.5)
    ax[2].set_title('C. KNHANES 조사연도 결합 범위' if ko else 'C. Scope of KNHANES year pooling',loc='left',weight='bold',fontsize=9)

    methods=['SHAP','Model-native importance','Permutation importance','PDP/ALE/ICE','LIME']
    labels=['SHAP','모형 내장 변수 중요도','순열 변수 중요도','PDP·ALE·ICE','LIME'] if ko else methods
    imp_mat=np.array([[100*T[p]['importance_method_counts'].get(m,0)/T[p]['predictive_n'] for p in periods] for m in methods])
    im3=ax[3].imshow(imp_mat,aspect='auto',cmap='PuBu',vmin=0,vmax=75)
    ax[3].set_xticks(x); ax[3].set_xticklabels(short); ax[3].set_yticks(range(len(methods))); ax[3].set_yticklabels(labels,fontsize=7.4)
    for i in range(imp_mat.shape[0]):
      for j in range(imp_mat.shape[1]):
       v=imp_mat[i,j]; ax[3].text(j,i,f'{v:.0f}',ha='center',va='center',fontsize=7,color='white' if v>42 else '#111827')
    ax[3].set_title('D. 변수 중요도 방법: SHAP의 정착 (%)' if ko else 'D. Variable-importance methods: SHAP becomes dominant (%)',loc='left',weight='bold',fontsize=10.2)
    fig.colorbar(im3,ax=ax[3],fraction=.035,pad=.025,label='%')
    fig.tight_layout(h_pad=2.4,w_pad=2.2); save(fig,'fig15_temporal_methods_ko' if ko else 'fig15_temporal_methods')


def fig16_temporal_quality(lang="en"):
    """Separate growth, analytic-role change, reporting, and persistent quality deficits."""
    style(lang); ko=lang=="ko"
    T=json.load(open(os.path.join(PROJ,"results/derived/temporal_quality.json")))['periods']
    periods=['≤2019','2020–2022','2023–2024','2025–2026']; n=[T[p]['n'] for p in periods]
    fig,ax=plt.subplots(2,2,figsize=(10,7)); ax=ax.ravel()
    ax[0].bar(periods,n,color=BLUE)
    for i,v in enumerate(n): ax[0].text(i,v+1,str(v),ha='center',fontsize=8)
    ax[0].set_ylim(0,75); ax[0].set_ylabel('연구 수' if ko else 'Studies (n)')
    ax[0].set_title('A. 절대 출판량 증가' if ko else 'A. Growth in publication volume',loc='left',weight='bold',fontsize=9)

    med=np.array([T[p]['general_median'] for p in periods]); q1=np.array([T[p]['general_q1'] for p in periods]); q3=np.array([T[p]['general_q3'] for p in periods])
    fm=np.array([T[p]['fulltext_median'] for p in periods]); fq1=np.array([T[p]['fulltext_q1'] for p in periods]); fq3=np.array([T[p]['fulltext_q3'] for p in periods])
    x=np.arange(4); ax[1].errorbar(x-.06,med,yerr=[med-q1,q3-med],marker='o',capsize=3,color=BLUE,label='전체 연구' if ko else 'All studies')
    ax[1].errorbar(x+.06,fm,yerr=[fm-fq1,fq3-fm],marker='s',capsize=3,color=GREEN,label='원문 확보' if ko else 'Full reports')
    ax[1].set_xticks(x); ax[1].set_xticklabels(periods); ax[1].set_ylim(0,100); ax[1].set_ylabel('%')
    ax[1].set_title('B. 일반 TRIPOD+AI: 완만한 개선 후 정체' if ko else 'B. General TRIPOD+AI: modest improvement and plateau',loc='left',weight='bold',fontsize=9)
    ax[1].legend(frameon=False,fontsize=7); ax[1].text(.02,.04,'중앙값과 사분위범위' if ko else 'Median and IQR',transform=ax[1].transAxes,fontsize=6.5,color=GREY)

    hd=np.zeros((4,4))
    for i,p in enumerate(periods):
      for k,v in T[p]['high_domain_distribution'].items(): hd[i,int(k)-1]=100*v/T[p]['n']
    bottom=np.zeros(4); cols=['#d8eadf','#c9dded',ORANGE,RED]
    for j in range(4):
      ax[2].bar(periods,hd[:,j],bottom=bottom,color=cols[j],label=(f'{j+1}개' if ko else str(j+1)))
      bottom+=hd[:,j]
    ax[2].set_ylim(0,100); ax[2].set_ylabel('%'); ax[2].legend(frameon=False,ncol=4,fontsize=6.5,loc='lower center')
    ax[2].set_title('C. PROBAST 고위험 영역 수: 개선 없음' if ko else 'C. Number of high-risk PROBAST domains: no improvement',loc='left',weight='bold',fontsize=9)
    ax[2].text(.02,.92,'모든 시기 중앙값 3개' if ko else 'Median 3 in every period',transform=ax[2].transAxes,fontsize=7,weight='bold')

    metrics=[('limitations','한계 논의' if ko else 'Limitations discussed'),('missing_data','결측처리 보고' if ko else 'Missing data reported'),('model_evaluation','모형평가 설명' if ko else 'Model evaluation described'),
             ('external','외부검증' if ko else 'External validation'),('calibration','보정 평가' if ko else 'Calibration assessed'),('code_availability','코드 공개' if ko else 'Code available'),('sample_size_justification','표본크기 근거' if ko else 'Sample-size rationale'),('weights','학습 가중치' if ko else 'Weights in fitting')]
    mat=[]
    for key,label in metrics:
      vals=[]
      for p in periods:
       vals.append(T[p]['external_pct'] if key=='external' else T[p]['calibration_pct'] if key=='calibration' else T[p]['weights_fitting_pct'] if key=='weights' else T[p]['items'][key]['pct'])
      mat.append(vals)
    mat=np.array(mat); im=ax[3].imshow(mat,aspect='auto',cmap='YlGnBu',vmin=0,vmax=100)
    ax[3].set_yticks(range(len(metrics))); ax[3].set_yticklabels([x[1] for x in metrics],fontsize=6.5); ax[3].set_xticks(range(4)); ax[3].set_xticklabels(periods,fontsize=7)
    for i in range(mat.shape[0]):
      for j in range(4): ax[3].text(j,i,f'{mat[i,j]:.0f}',ha='center',va='center',fontsize=5.8,color='white' if mat[i,j]>55 else 'black')
    ax[3].set_title('D. 선택적 개선과 지속되는 결함 (%)' if ko else 'D. Selective improvement and persistent deficits (%)',loc='left',weight='bold',fontsize=9)
    fig.colorbar(im,ax=ax[3],fraction=.03,pad=.02,label='%')
    fig.tight_layout(h_pad=2.4,w_pad=2); save(fig,'fig16_temporal_quality_ko' if ko else 'fig16_temporal_quality')


def fig16_evidence_support(lang="en"):
    """Core prompt-1 figure: analytic outputs versus evidentiary support by era."""
    style(lang); ko=lang=="ko"
    periods=['≤2019','2020–2022','2023–2024','2025–2026']
    def pp(y): return '≤2019' if y<=2019 else '2020–2022' if y<=2022 else '2023–2024' if y<=2024 else '2025–2026'
    rows=[('Explicit variable importance','명시적 변수중요도'),('Importance stability assessed','중요도 안정성 평가'),('External/temporal validation','외부·시간적 검증'),('Calibration plot','보정도'),('Paired model comparison','짝지은 모형비교'),('Open science fully met','오픈사이언스 완전충족'),('Survey weights reported','표본가중치 보고'),('Sample-size rationale','표본크기 근거')]
    num=np.zeros((len(rows),4)); den=np.zeros((len(rows),4))
    finals=[]
    for path in glob.glob(os.path.join(PROJ,'data/protocol_v1_2/final/KHM*_final.json')):
        d=json.load(open(path)); one=lambda k:d['protocol_items'][k][0]['value']
        if d.get('corpus_status',{}).get('include',one('ELG04')=='Y') and one('TSK01')=='CLS': finals.append(d)
    for d in finals:
        one=lambda k:d['protocol_items'][k][0]['value']
        anyv=lambda k,v:any(x['value']==v or isinstance(x['value'],list) and v in x['value'] for x in d['protocol_items'][k])
        j=periods.index(pp(int(d['metadata']['publication_year'])))
        vals=[anyv('VI01','USED'),anyv('VI16','USED'),anyv('VAL02','EXTERNAL') or anyv('VAL02','TEMPORAL'),
              any(m.get('metric') in ('CALSLOPE','CALINT','CALPLOT') for m in d['performance_metrics']),
              anyv('MET_PAIR','Y'),one('REP19')=='R',one('SUR04')=='USED',one('REP09') in ('R','P')]
        for i,v in enumerate(vals):
            den[i,j]+=1; num[i,j]+=bool(v)
    mat=np.divide(100*num,den,out=np.zeros_like(num),where=den>0)
    fig,ax=plt.subplots(figsize=(7.6,4.7)); im=ax.imshow(mat,aspect='auto',cmap='YlGnBu',vmin=0,vmax=100)
    ax.set_xticks(range(4)); ax.set_xticklabels(periods,fontsize=8)
    ax.set_yticks(range(len(rows))); ax.set_yticklabels([b if ko else a for a,b in rows],fontsize=8)
    for i in range(mat.shape[0]):
        for j in range(4): ax.text(j,i,f'{mat[i,j]:.0f}%\n({int(num[i,j])}/{int(den[i,j])})',ha='center',va='center',fontsize=6.2,color='white' if mat[i,j]>55 else '#111827')
    ax.set_title('분석 산출물과 근거 지원의 시기별 변화 (%)' if ko else 'Temporal change in analytic output versus evidentiary support (%)',loc='left',weight='bold')
    fig.colorbar(im,ax=ax,fraction=.035,pad=.025,
                 label='적용 가능한 연구 중 백분율' if ko else '% of applicable studies')
    era=[int(x) for x in den[0]]
    ax.set_xlabel((f'모든 행의 분모: 시기별 분류연구 {era[0]} / {era[1]} / {era[2]} / {era[3]}편' if ko else
                   f'Denominator for every row: classification studies by era, n={era[0]} / {era[1]} / {era[2]} / {era[3]}'),fontsize=7)
    fig.tight_layout(); save(fig,'fig16_evidence_support_ko' if ko else 'fig16_evidence_support')


def fig17_probast_ai(lang="en"):
    """Adjudicated protocol-v1.2 PROBAST+AI and reporting/survey results."""
    style(lang); ko=lang=="ko"
    c=json.load(open(os.path.join(PROJ,"results/derived/protocol_v1_2_consensus_results.json")))
    a=c['probast_ai']; nstudy=c['denominators']['studies']; npred=c['denominators']['prediction']
    fig,ax=plt.subplots(2,2,figsize=(9.4,6.5)); ax=ax.ravel()
    domains=['D1','D2','D3','D4']
    dlabs=(['참여자·자료원','예측변수','결과','분석'] if ko else
           ['Participants/data','Predictors','Outcome','Analysis'])
    # Corpus-wide reporting and survey-design results lead; instrument-specific
    # model/evaluation units follow so readers encounter denominators in a natural order.
    report_keys=['REP03','REP10','REP09','REP19','REP17']
    report_labels=(['연구목적','결측자료','표본크기 근거','오픈사이언스 완전충족','사용가능 최종모형'] if ko else
                   ['Objectives','Missing data','Sample-size rationale','Open science fully met','Usable final model'])
    barh(ax[0],report_labels,[c['reporting'][k].get('R',0) for k in report_keys],
         f'A. 핵심 완전보고 (예측연구 n={npred})' if ko else f'A. Complete reporting (prediction studies; n={npred})',
         [BLUE,BLUE,RED,ORANGE,ORANGE],'연구 수' if ko else 'Studies (n)',npred)

    slabels=(['모집단 해석에 필요','사용목적에 따라 조건부','부분 충족','불충분','불명확','비해당'] if ko else
             ['Required for population claims','Conditional on intended use','Partial','Inadequate','Unclear','Not applicable'])
    svals=[c['survey']['SUR12'].get('REQUIRED',0),c['survey']['SUR12'].get('CONDITIONAL',0),
           c['survey']['SUR14'].get('PARTIAL',0),c['survey']['SUR14'].get('INADEQ',0),
           c['survey']['SUR14'].get('UNC',0),c['survey']['SUR14'].get('NA',0)]
    barh(ax[1],slabels,svals,f'B. 복합표본 적용성과 충족도 (n={nstudy})' if ko else
         f'B. Complex-survey applicability and adherence (n={nstudy})',
         [BLUE,SKY,GREEN,RED,GREY,ORANGE],'연구 수' if ko else 'Studies (n)',nstudy)
    ax[1].axhline(1.5,color='#D1D5DB',lw=.8)

    for panel,phase,title in [(2,'development','C. 개발 방법론적 품질'),
                              (3,'evaluation','D. 성능평가 비뚤림 위험')]:
        n=a[phase]['n_units']; bottom=np.zeros(4)
        if phase=='development':
            levels=['HIGH','UNC','LOW']; cols=[GREEN,'#b8bec7',RED]
            llabs=['높은 품질','불명확','낮은 품질'] if ko else ['High quality','Unclear','Low quality']
        else:
            levels=['LOW','UNC','HIGH']; cols=[GREEN,'#b8bec7',RED]
            llabs=['낮은 위험','불명확','높은 위험'] if ko else ['Low risk','Unclear','High risk']
        for level,col,label in zip(levels,cols,llabs):
            vals=np.array([100*a[phase]['domains'][d].get(level,0)/n for d in domains])
            ax[panel].barh(range(4),vals,left=bottom,color=col,label=label)
            for i,v in enumerate(vals):
                if v>=8: ax[panel].text(bottom[i]+v/2,i,f'{v:.0f}',ha='center',va='center',fontsize=7)
            bottom+=vals
        ax[panel].set_yticks(range(4)); ax[panel].set_yticklabels(dlabs,fontsize=7.5)
        ax[panel].invert_yaxis(); ax[panel].set_xlim(0,100); ax[panel].set_xlabel('%')
        etitle=('Development methodological quality' if phase=='development' else 'Performance-evaluation risk of bias')
        ax[panel].set_title((title if ko else f'{title[0:2]} {etitle}')+f' (n={n})',loc='left',weight='bold',fontsize=9)
        ax[panel].legend(frameon=False,ncol=3,fontsize=7,loc='lower center',bbox_to_anchor=(.5,-.36))
    fig.text(.5,.012,('블라인드 LLM P2 및 사전 규칙 기반 조정 완료' if ko else
                      'Blinded LLM P2 and prespecified rule-based reconciliation complete'),
             ha='center',fontsize=7,color=GREY)
    fig.tight_layout(rect=(0,.04,1,1),h_pad=2.6,w_pad=2.2)
    save(fig,'fig17_probast_ai_ko' if ko else 'fig17_probast_ai')


def make_all():
    os.makedirs(OUT,exist_ok=True)
    for lang in ("en","ko"):
        fig2_publication(lang); fig3_problem(lang); fig3b_target_definition(lang); fig4_data(lang); fig5_preprocessing(lang)
        fig6_modeling(lang); fig7_evaluation(lang); fig8_interpretation(lang); fig5_analytic_function(lang); fig9_importance_endpoints(lang); fig10_important_variables(lang)
        fig14_topic_diversification(lang); fig15_temporal_methods(lang); fig16_evidence_support(lang); fig17_probast_ai(lang)


if __name__ == "__main__":
    make_all()
