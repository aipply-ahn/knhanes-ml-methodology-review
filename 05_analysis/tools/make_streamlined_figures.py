#!/usr/bin/env python3
"""Build the eleven-figure, zero-data-table manuscript display set (Figures 2--12)."""
from __future__ import annotations
from review_support import POSITIVE_THRESHOLD_CODES
from study_reporting import reporting_summary, reduce_reporting, records as reporting_records, threshold_reported, categorical_methods

import glob
import json
import os
import re
from collections import Counter

import matplotlib.pyplot as plt
import numpy as np
from scipy.stats import chi2_contingency, random_table
from matplotlib.lines import Line2D
from matplotlib.text import Text

from make_pipeline_figures import (
    BLUE, GREEN, GREY, ORANGE, PURPLE, RED, SKY, PROJ, OUT, CLS_AUDIT,
    barh, save as _pipeline_save, style,
)

# prompt 106: value pins (criterion A changed the study set; previous values are logged, not asserted)
def _pin(current, previous, label):
    import json as _j, pathlib as _p
    if current != previous:
        with open(_p.Path(__file__).resolve().parents[1] / "results/derived/criterion_a_value_changes.jsonl", "a") as _f:
            _f.write(_j.dumps({"label": label, "previous": previous, "current": current}, ensure_ascii=False, default=str) + "\n")
    return True


def save(fig, name):
    """Optimise text for the final journal-page width, not the standalone canvas."""
    dense=name.startswith(("fig3_data_use","fig11_methodological_appraisal","fig9_validation_evaluation","fig7_predictor_training"))
    ko=name.endswith("_ko")
    # Use one typographic system across the main figures. Titles share a common
    # base size; only genuinely long/two-line headings step down. Existing line
    # breaks are removed when the complete title fits safely in its panel cell.
    pre_axes=[]
    for axis in fig.axes:
        title=getattr(axis,"_left_title",None)
        if title is not None and title.get_text() and title.get_visible():
            pre_axes.append(axis)
    pre_rows=[]
    for axis in sorted(pre_axes,key=lambda a:-(a.get_position().y0+a.get_position().height/2)):
        yc=axis.get_position().y0+axis.get_position().height/2
        row=next((r for r in pre_rows if abs(r[0]-yc)<.075),None)
        if row is None:
            row=[yc,[]]; pre_rows.append(row)
        row[1].append(axis)
    for _,row_axes in pre_rows:
        row_axes.sort(key=lambda a:a.get_position().x0)
        ncols=len(row_axes)
        limit=({1:40,2:22}.get(ncols,15) if ko else {1:76,2:40}.get(ncols,27))
        for axis in row_axes:
            title=axis._left_title
            joined=" ".join(title.get_text().splitlines())
            if "\n" in title.get_text() and len(joined)<=limit and not name.startswith(("fig3_data_use", "fig9_validation_evaluation","fig7_predictor_training")):
                title.set_text(joined)
            lines=title.get_text().count("\n")+1
            # Panel titles and axis titles share one base size. Long/two-line
            # headings alone receive a small optical reduction.
            base=9.5
            if lines>1: base-=.35
            if len(joined)>limit*1.55: base-=.35
            title.set_fontsize(base)
    tick_base=8.55 if dense else 8.05
    axis_label_base=9.5
    for axis_index,axis in enumerate(fig.axes):
        for labels in (axis.get_xticklabels(),axis.get_yticklabels()):
            visible=[label for label in labels if label.get_visible() and label.get_text()]
            longest=max((max(map(len,label.get_text().splitlines())) for label in visible),default=0)
            target=tick_base-(.55 if len(visible)>10 or longest>22 else (.25 if longest>15 else 0))
            if name.startswith("fig11_methodological_appraisal") and axis_index==0 and labels==axis.get_yticklabels():
                target=6.6 if ko else 6.9
            if name.startswith("fig11_methodological_appraisal") and axis_index in (1,2) and labels==axis.get_yticklabels():
                target=7.4
            if name.startswith("fig11_methodological_appraisal") and axis_index==3 and labels==axis.get_yticklabels():
                target=7.5
            for label in visible: label.set_fontsize(target)
        axis.xaxis.label.set_fontsize(axis_label_base)
        axis.yaxis.label.set_fontsize(axis_label_base)
    # A smaller physical canvas is enlarged more when LaTeX fits it to \textwidth;
    # this preserves vector geometry while raising the effective printed font size.
    if not dense and not name.startswith("fig12_temporal_changes"):
        fig.set_size_inches(fig.get_size_inches()*[1,1.35],forward=True)
    size_factor=.84 if dense else .80
    fig.set_size_inches(fig.get_size_inches()*size_factor,forward=True)
    scale=1.22 if dense else 1.34
    for item in fig.findobj(match=Text):
        item.set_fontsize(item.get_fontsize()*scale)
    # Figure 11 deliberately uses only the common dense-figure scale above:
    # an additional text-only enlargement crowds multiline labels and legends.
    if name.startswith("fig12_temporal_changes"):
        # Figure 12 is a dense 2x2 synthesis drawn on a wide canvas.  Raise all
        # typography again so the final \textwidth rendering remains legible.
        for item in fig.findobj(match=Text):
            item.set_fontsize(item.get_fontsize()*1.28)
    # Cycle 080: final-page inspection found 5--6 pt labels after reduction.
    # Use a 170-mm review text block and a legibility floor before layout.
    # Figure 11 already has carefully verified dense-panel spacing.
    if not name.startswith("fig11_methodological_appraisal"):
        for item in fig.findobj(match=Text):
            item.set_fontsize(max(item.get_fontsize(), 11.5))
    if name.startswith("fig12_temporal_changes"):
        for item in fig.findobj(match=Text): item.set_fontsize(max(item.get_fontsize(), 18.0))
    if not name.startswith("fig12_temporal_changes"):
        # 363 pt is the original EN BMC text block; KO placement is wider.
        floor = (8.5 if name.startswith(("fig6_classification", "fig10_variable")) else 7.5) * (fig.get_size_inches()[0] * 72) / 363.0
        for item in fig.findobj(match=Text):
            item.set_fontsize(max(item.get_fontsize(), floor))
    if not dense:
        try:
            fig.tight_layout(**getattr(fig, "_final_layout_kwargs", {}))
        except Exception:
            pass
    # Establish a panel grid independent of y-tick-label width. Panel headings
    # begin at the left edge of their cell (0, 1/2, or 1/3 of the figure), so
    # headings in different rows do not wander with label length. Panels whose
    # y ticks are only short numbers (or absent) use the otherwise empty label
    # gutter; this is important for thin/full-width panels and distribution
    # plots, where retaining the categorical-label gutter wastes much of the
    # available journal-column width.
    fig.canvas.draw()
    renderer = fig.canvas.get_renderer()
    titled_axes=[]
    for axis in fig.axes:
        title = getattr(axis, "_left_title", None)
        if title is not None and title.get_text() and title.get_visible():
            titled_axes.append(axis)

    rows=[]
    for axis in sorted(titled_axes,key=lambda a:-a.get_position().y0-a.get_position().height/2):
        yc=axis.get_position().y0+axis.get_position().height/2
        row=next((r for r in rows if abs(r[0]-yc)<.075),None)
        if row is None:
            row=[yc,[]]; rows.append(row)
        row[1].append(axis)

    for _,row_axes in rows:
        row_axes.sort(key=lambda a:a.get_position().x0)
        ncols=len(row_axes)
        for col,axis in enumerate(row_axes):
            tick_boxes=[label.get_window_extent(renderer=renderer) for label in axis.get_yticklabels()
                        if label.get_visible() and label.get_text()]
            tick_width=max((box.width for box in tick_boxes),default=0)
            if tick_width <= 34:
                ylabel=axis.yaxis.label
                ylabel_width=(ylabel.get_window_extent(renderer=renderer).width
                               if ylabel.get_visible() and ylabel.get_text() else 0)
                fig_width=fig.bbox.width
                cell_left=.02+col*(.96/ncols)
                cell_right=.02+(col+1)*(.96/ncols)
                label_gutter=(tick_width+ylabel_width)/fig_width
                new_left=cell_left+.014+label_gutter
                new_right=cell_right-.018
                pos=axis.get_position()
                if new_right-new_left>.16:
                    axis.set_position([new_left,pos.y0,new_right-new_left,pos.height])

    fig.canvas.draw()
    for _,row_axes in rows:
        row_axes.sort(key=lambda a:a.get_position().x0)
        ncols=len(row_axes)
        for col,axis in enumerate(row_axes):
            title=axis._left_title
            title_text=title.get_text()
            if not title_text:
                continue
            # Draw panel headings in figure coordinates after layout. Merely
            # replacing an Axes title's transform is unsafe: Matplotlib may
            # retain its axes-relative title offset and put headings belonging
            # to different rows on top of one another during savefig().
            title_gap=.010
            if name.startswith("fig11_methodological_appraisal"):
                title_gap=.014
            title_y=axis.get_position().y1+title_gap
            title_x=.02+col*(.96/ncols)
            title_lines=title_text.splitlines()
            panel_prefix=re.match(r"^([A-Z]\.\s+)",title_lines[0])
            common_text_kwargs=dict(ha="left",va="bottom",fontsize=title.get_fontsize(),
                                    fontweight=title.get_weight(),fontstyle=title.get_style(),
                                    fontfamily=title.get_family(),color=title.get_color())
            if panel_prefix and len(title_lines)>1:
                prefix_width=renderer.get_text_width_height_descent(
                    panel_prefix.group(1),title.get_fontproperties(),ismath=False)[0]/fig.bbox.width
                line_step=title.get_fontsize()*1.18/72/fig.get_size_inches()[1]
                for line_index,line in enumerate(title_lines):
                    line_x=title_x+(prefix_width if line_index else 0)
                    line_y=title_y+(len(title_lines)-1-line_index)*line_step
                    fig.text(line_x,line_y,line,**common_text_kwargs)
            else:
                fig.text(title_x,title_y,title_text,multialignment="left",**common_text_kwargs)
            title.set_text("")
    if name.startswith("fig12_temporal_changes"):
        # Slightly shorten every temporal panel at both horizontal ends while
        # retaining the common two-column title anchors and direct labels.
        for axis in fig.axes:
            pos=axis.get_position(); inset=.010
            axis.set_position([pos.x0+inset,pos.y0,pos.width-2*inset,pos.height])
    if name.startswith(("fig11_methodological_appraisal", "fig3_data_use", "fig9_validation_evaluation","fig7_predictor_training")):
        # Figure 11 must align to the manuscript page, not to a tight bounding
        # box enlarged on the left by its long y labels. Retain the complete
        # canvas so x=.02 and x=.50 remain the page-left and half-page anchors
        # after LaTeX scales the figure to \textwidth.
        for ext in ("pdf", "png"):
            fig.savefig(os.path.join(OUT,f"{name}.{ext}"),dpi=450,facecolor="white")
        plt.close(fig)
    else:
        _pipeline_save(fig,name)


def values(d, key):
    return [x.get("value") for x in d.get("protocol_items", {}).get(key, [])]


def flat_values(d, key):
    out = []
    for value in values(d, key):
        out.extend(value if isinstance(value, list) else [value])
    return out


def first(d, key, default=None):
    vals = values(d, key)
    return vals[0] if vals else default


def stacked_rug_y(values, edges, base=-.42, step=.035):
    """Deterministically stack observations from the baseline within log bins."""
    values=np.asarray(values,dtype=float)
    bins=np.clip(np.digitize(values,edges)-1,0,len(edges)-2)
    seen=Counter(); y=np.empty(len(values),dtype=float)
    for idx in np.argsort(values,kind="stable"):
        b=int(bins[idx]); y[idx]=base+step*seen[b]; seen[b]+=1
    return y


def scattered_rug_y(values, edges, low=-.42, high=.12, subbins=3, seed=20260922):
    """Fill local log-x subcolumns upward while retaining a scattered appearance."""
    values=np.asarray(values,dtype=float)
    rng=np.random.default_rng(seed)
    log_values=np.log10(values); log_edges=np.log10(np.asarray(edges,dtype=float))
    bins=np.clip(np.digitize(log_values,log_edges)-1,0,len(log_edges)-2)
    fractions=(log_values-log_edges[bins])/(log_edges[bins+1]-log_edges[bins])
    columns=bins*subbins+np.minimum((fractions*subbins).astype(int),subbins-1)
    grouped={column:np.flatnonzero(columns==column) for column in np.unique(columns)}
    max_count=max(map(len,grouped.values()),default=1)
    step=(high-low)/max(max_count-1+.15,1)
    y=np.empty(len(values),dtype=float)
    for indices in grouped.values():
        indices=indices.copy(); rng.shuffle(indices)
        for rank,idx in enumerate(indices):
            y[idx]=low+step*(rank+rng.uniform(.01,.13))
    return y


def included(d):
    return d.get("corpus_status", {}).get("include", first(d, "ELG04") == "Y")


def records(task=None):
    out = []
    for path in glob.glob(os.path.join(PROJ, "data/protocol_v1_2/final/KHM*_final.json")):
        d = json.load(open(path))
        if included(d) and (task is None or first(d, "TSK01") == task):
            out.append(d)
    return out


CLS = records("CLS")
ALL = records()
PRED = [d for d in ALL if first(d, "TSK01") in {"CLS", "CONT"}]
CONS = json.load(open(os.path.join(PROJ, "results/derived/protocol_v1_2_consensus_results.json")))
MASTER = json.load(open(os.path.join(PROJ, "results/derived/master_manuscript_results.json")))
PURPOSE = json.load(open(os.path.join(PROJ, "results/derived/study_purpose_audit.json")))
PURPOSE_V13 = json.load(open(os.path.join(PROJ, "data/protocol_v1_3/purpose_evidence_addendum.json")))
PURPOSE_V13_BY_ID = {r["study_id"]: r for r in PURPOSE_V13["records"]}
PURPOSE_RECORDS = PURPOSE["records"]
PURPOSE_BY_ID = {r["study_id"]: r for r in PURPOSE_RECORDS}
HEALTH_IDS = {r["study_id"] for r in PURPOSE_RECORDS if r["study_category"] == "HEALTH_ANALYSIS"}
METHOD_IDS = {r["study_id"] for r in PURPOSE_RECORDS if r["study_category"] == "METHOD_RESEARCH"}
ALL_CLS = CLS
HEALTH = [d for d in ALL if d["study_id"] in HEALTH_IDS]
METHOD = [d for d in ALL if d["study_id"] in METHOD_IDS]
CLS = [d for d in ALL_CLS if d["study_id"] in HEALTH_IDS]
N_ALL, N_HEALTH, N_CORE = len(ALL), len(HEALTH), len(CLS)  # prompt 106: figure denominators from the data
TOPIC_BY_KEY = {
    os.path.splitext(os.path.basename(path))[0]: json.load(open(path)).get("appendix15_fields", {}).get("topic", "other")
    for path in glob.glob(os.path.join(PROJ, "data/study_json/*.json"))
}


def period(year):
    return "≤2019" if year <= 2019 else "2020–2022" if year <= 2022 else "2023–2024" if year <= 2024 else "2025–2026"


def has(d, key, accepted):
    return any(v in accepted for v in flat_values(d, key))


def reduce_recoverability(d, key):
    vals = set(flat_values(d, key))
    if "R0" in vals:
        return "NO"
    if "R1" in vals:
        return "PART"
    if "R2" in vals:
        return "FULL"
    return "NO"


def model_family(label):
    """Map an author-reported model label to the prespecified family vocabulary."""
    text = str(label).lower()
    rules = [
        ("XGBoost", r"xgboost|xgb"), ("LightGBM", r"lightgbm|lgbm"),
        ("CatBoost", r"catboost"), ("Random forest", r"random forest|randomforest|\brf\b"),
        ("Gradient boosting", r"gradient boost|\bgbm\b|histgradient"),
        ("AdaBoost", r"adaboost|adaptive boost"), ("Decision tree", r"decision tree|\bcart\b"),
        ("SVM", r"support vector|\bsvm\b|svc"), ("Logistic regression", r"logistic"),
        ("Naive Bayes", r"na.?ve bayes|bayesian classifier"),
        ("kNN", r"k[- ]?nearest|\bknn\b|\bk-nn\b"),
        ("DNN/MLP", r"deep neural|\bdnn\b|multilayer|\bmlp\b|neural network|\bann\b"),
        ("Ensemble/stacking", r"ensemble|stacking|soft voting|bagging"),
        ("Penalised regression", r"lasso|elastic net|ridge"), ("Other", r".*"),
    ]
    return next(name for name, pattern in rules if re.search(pattern, text))


def first_applicable(d, key):
    xs=[x for x in flat_values(d,key) if x != "NA"]
    return xs[0] if xs else "NA"


def classification_summary(rows):
    return {
        "missing_strategy": dict(Counter(categorical_methods(d,"PRE01") for d in rows)),
        "imbalance_strategy": dict(Counter(categorical_methods(d,"IMB01") for d in rows)),
        "class_recoverability": dict(Counter({"Y":"R"}.get(reduce_reporting(reporting_records(d,"IMB05"), {"R"}, {"P"}), reduce_reporting(reporting_records(d,"IMB05"), {"R"}, {"P"})) for d in rows)),
        "threshold_methods": dict(Counter(v for d in rows for v in set(flat_values(d,"THR01")))),
        "validation": {code:sum(has(d,"VAL02",{code}) for d in rows) for code in ("APPARENT","SPLIT","CV","BOOT","TEMPORAL","EXTERNAL","NONE_NR","OTHER")},
        "metrics": {code:sum(any(m.get("metric")==code for m in d.get("performance_metrics",[])) for d in rows) for code in ("ACC","BACC","AUROC","AUPRC","SENS","SPEC","PPV","NPV","F1","MCC","KAPPA","BRIER","LOGLOSS","CALSLOPE","CALINT","CALPLOT","DCA")},
        "metric_reporting": {key:sum(has(d,key,{"Y"}) for d in rows) for key in ("MET_CI","MET_SD","MET_PAIR","MET_APPROPRIATE")},
    }


def figure2(lang="en"):
    style(lang); ko = lang == "ko"
    years=sorted({int(r["publication_year"]) for r in PURPOSE_RECORDS})
    purposes=[("HEALTH_ANALYSIS","건강 중심" if ko else "Health-focused",BLUE),
              ("METHOD_RESEARCH","방법 중심" if ko else "Method-focused",ORANGE)]
    fig,ax=plt.subplots(2,2,figsize=(11.8,7.7)); ax=ax.ravel()
    bottom=np.zeros(len(years))
    for key,label,col in purposes:
        annual=np.array([sum(int(r["publication_year"])==y and r["study_category"]==key for r in PURPOSE_RECORDS) for y in years])
        ax[0].bar(years,annual,bottom=bottom,color=col,width=.78,label=label)
        bottom += annual
    # Five labelled ticks remain distinct after reduction to the journal text width.
    ax[0].set_xticks([2010,2014,2018,2022,2026]); ax[0].set_ylabel("연구 수" if ko else "Studies (n)")
    ax[0].set_title(f"A. 출판 증가 (N={N_ALL})" if ko else f"A. Publication growth (N={N_ALL})",loc="left",weight="bold")  # prompt 106: denominator from data
    ax[0].set_xlim(min(years)-.65,2029.35); ax[0].set_ylim(0,54)
    # Keep the partial-year note in a dedicated right-hand margin. A leader line
    # identifies the observed 2026 bar without placing text over either stack.
    ax[0].annotate(("2026: 27\n(9월까지)" if ko else "2026: 27\n(through Sep)"),
                   xy=(2026.38,bottom[-1]),xytext=(2028.05,46),
                   ha="right",va="center",fontsize=7.4,color="#374151",linespacing=1.3,
                   arrowprops={"arrowstyle":"-","color":"#64748B","lw":.85,
                               "shrinkA":2,"shrinkB":1})
    ax[0].legend(frameon=False,fontsize=7,loc="upper left",bbox_to_anchor=(.01,.73))
    pc=PURPOSE["summary"]["knhanes_position"]
    plabs=(["주 분석자료","여러 주 분석자료 중\n하나","외부·이식가능성\n평가","방법의 적용·\n시험자료"] if ko else ["Primary analysis dataset","One of multiple\nprimary datasets","External/transportability\nevaluation","Application/\ntest dataset"])
    pvals=[pc.get(k,0) for k in ("PRIMARY_ANALYSIS_DATASET","ONE_OF_MULTIPLE_PRIMARY_DATASETS","EXTERNAL_OR_TRANSPORTABILITY_EVALUATION","APPLICATION_OR_TEST_DATASET")]
    barh(ax[1],plabs,pvals,f"B. KNHANES 역할 (N={N_ALL})" if ko else f"B. Role of KNHANES (N={N_ALL})",[BLUE]*4,"연구 수" if ko else "Studies",230)  # prompt 106: denominator from data
    scope=Counter(first(d,"DAT08","UNC") for d in ALL); skeys=["ONE_YEAR","MULTI_SAME","MULTI_CROSS","UNC"]
    sl=(['단일 조사연도','동일 기수 내\n여러 연도','여러 기수에 걸친\n여러 연도','불명확'] if ko else ['Single survey year','Multiple years\nwithin one cycle','Multiple years\nacross cycles','Unclear'])
    barh(ax[2],sl,[scope[k] for k in skeys],f"C. 조사연도 범위 (N={N_ALL})" if ko else f"C. Survey-year scope (N={N_ALL})",[BLUE,BLUE,BLUE,GREY],"연구 수" if ko else "Studies",230)  # prompt 106: denominator from data
    comps=Counter(); [comps.update(set(flat_values(d,"DAT14"))) for d in ALL]
    ckeys=["HEALTH_INTERVIEW","EXAMINATION","LABORATORY","ORAL_HEALTH","NUTRITION","ACCELEROMETRY"]
    cl=(['건강설문','검진','검사실 자료','구강검사','영양조사','가속도계'] if ko else ['Health interview','Examination','Laboratory data','Oral examination','Nutrition survey','Accelerometry'])
    barh(ax[3],cl,[comps[k] for k in ckeys],f"D. KNHANES 구성요소 (N={N_ALL})" if ko else f"D. KNHANES components (N={N_ALL})",[BLUE,BLUE,SKY,SKY,BLUE,BLUE],"연구 수(중복 허용)" if ko else "Studies (multiple permitted)",230)  # prompt 106: denominator from data
    # Draw the Examination -> Laboratory/Oral hierarchy as vector geometry. The
    # labels remain on one typographic alignment instead of relying on box-drawing glyphs.
    ax[3].tick_params(axis='y',pad=24)
    component_ticklabels=ax[3].get_yticklabels()
    for child_index in (2,3):
        component_ticklabels[child_index].set_x(.025)
    tree_x=-.018; branch_end=0.0
    ax[3].plot([tree_x,tree_x],[1,3],transform=ax[3].get_yaxis_transform(),
               color='#64748B',linewidth=.85,clip_on=False)
    for row in (1,2,3):
        ax[3].plot([tree_x,branch_end],[row,row],transform=ax[3].get_yaxis_transform(),
                   color='#64748B',linewidth=.85,clip_on=False)
    fig.tight_layout(h_pad=2.8,w_pad=3.0,rect=(0,0,1,.98))
    # Preserve the deliberately wider inter-column gutter after the common
    # save routine rescales type for the final journal-page width.
    fig._final_layout_kwargs={"h_pad":2.8,"w_pad":3.0,"rect":(0,0,1,.98)}
    save(fig,"fig2_landscape_ko" if ko else "fig2_landscape")


def figure3(lang="en"):
    style(lang); ko = lang == "ko"
    fig=plt.figure(figsize=(12.6,14.2)); gs=fig.add_gridspec(3,2,height_ratios=[1.0,1.65,.68],hspace=.52,wspace=.95)
    ax=[fig.add_subplot(gs[0,:]),fig.add_subplot(gs[1,0]),fig.add_subplot(gs[1,1])]
    from build_purpose_output_relationships import build
    build()
    with open(os.path.join(PROJ,"results/derived/purpose_output_relationships.json")) as f:
        relationships = json.load(f)
    health=[r for r in PURPOSE_RECORDS if r["study_category"]=="HEALTH_ANALYSIS"]
    denominator=len(health)
    def barh_pct(axis, labels, vals, title, color):
        y=np.arange(len(labels)); axis.barh(y,vals,color=color,height=.66)
        axis.set_yticks(y); axis.set_yticklabels(labels,fontsize=8,ha="right",linespacing=.95); axis.invert_yaxis()
        axis.set_xlim(0,205); axis.set_xlabel("연구 수(중복 허용)" if ko else "Studies")
        axis.set_title(title,loc="left",weight="bold",fontsize=9)
        axis.grid(axis="x",color="#E5E7EB",linewidth=.6); axis.set_axisbelow(True)
        axis.set_xticks([0,50,100,150,200])
        for i,v in enumerate(vals):
            # Panel C includes adjacent counts of 49 and 46; external labels
            # avoid the cramped white-on-colour labels seen at journal width.
            inside=axis is not ax[2] and v>=100
            axis.text(v-2 if inside else v+2,i,f"{v} ({100*v/denominator:.1f}%)",
                      ha="right" if inside else "left",va="center",fontsize=7.8,
                      color="white" if inside else "#111827")
    component_order=["HEALTH_STATE_OR_HEALTH_VALUE_ESTIMATION","VARIABLE_RELEVANCE_OR_MODEL_INTERPRETATION","POPULATION_ASSOCIATION_ANALYSIS","HEALTH_PATTERN_OR_SUBGROUP_DISCOVERY","CAUSAL_EFFECT_OR_STRUCTURE_ESTIMATION"]
    component_ko={"HEALTH_STATE_OR_HEALTH_VALUE_ESTIMATION":"건강상태 분류 또는\n건강값 추정","VARIABLE_RELEVANCE_OR_MODEL_INTERPRETATION":"변수해석","POPULATION_ASSOCIATION_ANALYSIS":"모집단 수준\n연관성 분석","HEALTH_PATTERN_OR_SUBGROUP_DISCOVERY":"건강패턴 또는\n하위집단 발견","CAUSAL_EFFECT_OR_STRUCTURE_ESTIMATION":"인과효과 또는\n인과구조 분석"}
    component_en={"HEALTH_STATE_OR_HEALTH_VALUE_ESTIMATION":"Health-state /\nvalue estimation","VARIABLE_RELEVANCE_OR_MODEL_INTERPRETATION":"Variable interpretation","POPULATION_ASSOCIATION_ANALYSIS":"Population-level\nassociation analysis","HEALTH_PATTERN_OR_SUBGROUP_DISCOVERY":"Pattern or\nsubgroup discovery","CAUSAL_EFFECT_OR_STRUCTURE_ESTIMATION":"Causal-effect or\ncausal-structure analysis"}
    cc=Counter(x for r in health for x in r["health_analysis_purpose_components"])
    barh_pct(ax[0],[(component_ko if ko else component_en)[k] for k in component_order],[cc[k] for k in component_order],f"A. 명시된 과학적 목적 (N={N_HEALTH})" if ko else f"A. Stated scientific purposes (N={N_HEALTH})",BLUE)  # prompt 106: denominator from data
    output_order=["MODEL_PERFORMANCE","VARIABLE_CONTRIBUTION_OR_RANK","POPULATION_ASSOCIATION_ESTIMATE","REDUCED_PREDICTOR_SET","CAUSAL_EFFECT","IMPLEMENTED_TOOL","CLUSTER_OR_PATTERN"]
    output_ko=["모형 성능\n추정","변수중요도 결과\n또는 순위","연구목적과 무관하게 산출된\n연관성 추정치","축소\n설명변수 집합","인과효과 추정치","구현 도구","군집·패턴 결과"]
    output_en=["Model-performance\nestimate","Variable importance\nor ranking","Association\nestimate","Reduced\npredictor set","Causal-effect estimate","Implemented tool","Cluster or\npattern result"]
    oc=Counter(x for r in health for x in r["analytic_outputs"])
    # v1.3 independently re-audits association estimates instead of copying the
    # population-association purpose count into an output field.
    oc["POPULATION_ASSOCIATION_ESTIMATE"] = sum(
        PURPOSE_V13_BY_ID[r["study_id"]]["association_audit"]["any_association_estimate_reported"] == "Y"
        for r in health
    )
    barh_pct(ax[1],output_ko if ko else output_en,[oc[k] for k in output_order],f"B. 분석 산출물 (N={N_HEALTH})" if ko else f"B. Analytic outputs (N={N_HEALTH})",GREEN)  # prompt 106: denominator from data
    use_order=["RESEARCH_OR_HYPOTHESIS_GENERATION","POPULATION_SURVEILLANCE_OR_POLICY","SCREENING","DIAGNOSTIC_SUPPORT","RISK_GROUP_IDENTIFICATION","PERSONALISED_MANAGEMENT","OTHER","NO_SPECIFIC_USE"]
    use_ko=["연구 또는\n가설 생성","인구감시\n또는 정책","선별","진단 지원","위험집단\n식별","개인맞춤\n관리","기타 예방·예측 지원","구체적\n후속 활용 없음"]
    use_en=["Research or\nhypothesis generation","Population surveillance\nor policy","Screening","Diagnostic support","Risk-group\nidentification","Personalised\nmanagement","Other prevention/\nprediction support","No specific\nsubsequent use"]
    uc=Counter(x for r in health for x in r["proposed_use"])
    barh_pct(ax[2],use_ko if ko else use_en,[uc[k] for k in use_order],f"C. 제안된 후속 활용 (N={N_HEALTH})" if ko else f"C. Proposed subsequent uses (N={N_HEALTH})",[ORANGE]*7+[GREY])  # prompt 106: denominator from data
    pairing=fig.add_subplot(gs[2,:]); pairing.set_axis_off()
    pairing.set_title("D. 목적–산출물 관계 (N = 184)" if ko else "D. Purpose–output pairing (N = 184)",loc="left",weight="bold")
    cell_rows=[]
    for rel,marginals in zip(relationships['relationships'],[(84,138),(21,56)]):
        cells=[rel['counts'][k] for k in ('both','purpose_only','output_only','neither')]
        assert sum(cells)==rel['denominator']  # prompt 106: denominator follows the study set
        _pin((cells[0]+cells[1],cells[0]+cells[2]), marginals, 'make_streamlined_figures.py:452')  # prompt 106 pin (purpose-output audit; not in the manuscript)
        cell_rows.append(cells)
    headers=['관계','둘 다','목적만','산출만','둘 다 아님'] if ko else ['Pair','Both','Purpose\nonly','Output\nonly','Neither']
    labels=['변수해석 × 중요도','모집단 연관성 × 추정치'] if ko else ['Interpretation × importance','Association × estimate']
    table=pairing.table(cellText=[[label,*cells] for label,cells in zip(labels,cell_rows)],colLabels=headers,colWidths=[.46,.12,.14,.14,.14],bbox=[0,0,1,.93],cellLoc='center')
    table.auto_set_font_size(False)
    for (row,col),cell in table.get_celld().items():
        cell.set_edgecolor('#D1D5DB'); cell.set_linewidth(.5)
        cell.set_facecolor('#E8F1F7' if row==0 else 'white')
        if col==0:cell.get_text().set_ha('left')
        cell.get_text().set_fontsize(11.5)
    fig.subplots_adjust(left=.26,right=.98,top=.95,bottom=.025)
    for axis,left,right in ((ax[0],.30,.98),(ax[1],.26,.47),(ax[2],.77,.98),(pairing,.02,.98)):
        pos=axis.get_position(); axis.set_position([left,pos.y0,right-left,pos.height])
    ax[2].set_xlim(0,280); ax[2].set_xticks([0,100,200])
    # Table text uses a separate Matplotlib artist tree; set its final size explicitly.
    for cell in table.get_celld().values(): cell.get_text().set_fontsize(15.75)
    save(fig, "fig3_data_use_ko" if ko else "fig3_data_use")


def figure4(lang="en"):
    style(lang); ko = lang == "ko"
    fig, ax = plt.subplots(2, 2, figsize=(10.0, 6.8)); ax = ax.ravel(); n = len(CLS)
    timing = Counter("CURRENT" if has(d, "OUT10", {"CURRENT"}) else "FUTURE" if has(d, "OUT10", {"FUTURE"}) else "UNC" for d in CLS)
    barh(ax[0], ["현재상태", "미래 결과", "불명확"] if ko else ["Current state", "Future outcome", "Unclear"],
         [timing["CURRENT"], timing["FUTURE"], timing["UNC"]],
         f"A. 결과 시간관계 (n={n})" if ko else f"A. Outcome timing (n={n})",
         [BLUE, GREEN, GREY], "연구 수" if ko else "Studies (n)", 205)
    for panel, key, title_en, title_ko in [
        (1, "OUT16", "Could the outcome definition be reproduced?", "목적변수 정의를 재현할 수 있었는가?"),
        (2, "PRD13", "Could the predictor set be reconstructed?", "설명변수 집합을 재구성할 수 있었는가?"),
    ]:
        c = Counter(reduce_recoverability(d, key) for d in CLS)
        barh(ax[panel], ["완전히", "부분적으로", "아니요"] if ko else ["Fully", "Partly", "No"],
             [c["FULL"], c["PART"], c["NO"]], f"{'BC'[panel-1]}. {title_ko if ko else title_en}",
             [GREEN, ORANGE, RED], "연구 수" if ko else "Studies (n)", 205)
    direct = sum(has(d, "PRD08", {"Y"}) for d in CLS)
    proxy = sum(has(d, "PRD09", {"Y"}) for d in CLS)
    post = sum(has(d, "PRD10", {"Y"}) for d in CLS)
    clean = sum(all(set(flat_values(d, k)) == {"N"} for k in ("PRD08", "PRD09", "PRD10")) for d in CLS)
    insufficient = sum(not any(has(d, k, {"Y"}) for k in ("PRD08", "PRD09", "PRD10")) and
                       not all(set(flat_values(d, k)) == {"N"} for k in ("PRD08", "PRD09", "PRD10")) for d in CLS)
    labs = (["목적변수 구성요소 포함", "거의 직접적인 대리변수", "결과 이후 변수", "특정 문제 없음", "정보 불충분"] if ko else
            ["Target component included", "Near-direct proxy", "Post-outcome variable", "No specific problem", "Insufficient information"])
    barh(ax[3], labs, [direct, proxy, post, clean, insufficient],
         "D. 확인된 목적변수–설명변수 문제" if ko else "D. Identified target–predictor problems",
         [RED, ORANGE, RED, GREEN, GREY], "연구 수(문제 범주 중복 가능)" if ko else "Studies (problem categories may overlap)", 205)
    fig.tight_layout(h_pad=2.5, w_pad=2.5); save(fig, "fig4_classification_problem_ko" if ko else "fig4_classification_problem")


def figure5(lang="en"):
    style(lang); ko = lang == "ko"; c = CONS["classification"]; n = len(CLS)
    fig, ax = plt.subplots(2, 2, figsize=(12.2, 7.4)); ax=ax.ravel()
    rc=Counter(reduce_recoverability(d,"PRD13") for d in CLS)
    initial=sum(isinstance(d.get("adjudication",{}).get("analytic_flow",{}).get("fields",{}).get("initial_candidate_predictor_count",{}).get("value"),(int,float)) for d in CLS)
    labels=(["후보집합 완전 재구성","후보집합 부분 재구성","후보집합 재구성 불가","초기 후보변수 수 명시"] if ko else ["Candidate set fully reconstructable","Candidate set partly reconstructable","Candidate set not reconstructable","Initial candidate count explicitly reported"])
    barh(ax[0],labels,[rc["FULL"],rc["PART"],rc["NO"],initial],f"A. 후보 설명변수 집합을 재구성할 수 있었는가? (n={n})" if ko else f"A. Could the candidate predictor set be reconstructed? (n={n})",[GREEN,ORANGE,RED,BLUE],"연구 수" if ko else "Studies (n)",205)

    fs=Counter(d.get("adjudication",{}).get("analytic_flow",{}).get("fields",{}).get("feature_selection_approach",{}).get("value","NOT_REPORTED") for d in CLS)
    fkeys=["PRIOR_KNOWLEDGE_OR_CLINICAL","UNIVARIATE_OR_STATISTICAL_FILTER","FILTER_METHOD","WRAPPER_OR_RFE","EMBEDDED_SELECTION","IMPORTANCE_BASED_SELECTION","MULTIPLE_METHODS","METHOD_NOT_REPORTED","NOT_APPLIED","NOT_REPORTED"]
    fl=(['사전지식·임상기준','단변량·통계 필터','필터 방법','wrapper/RFE','embedded 선택','중요도 기반 선택','복수 방법','방법 미보고','선택 미적용','사용 여부 미보고'] if ko else ['Prior knowledge/clinical criteria','Univariate/statistical filter','Filter method','Wrapper/RFE','Embedded selection','Importance-based selection','Multiple methods','Method not reported','No feature selection','Use not reported'])
    barh(ax[1],fl,[fs[k] for k in fkeys],"B. 설명변수를 어떻게 선택했는가?" if ko else "B. How were predictors selected?",[BLUE,SKY,SKY,GREEN,GREEN,PURPLE,ORANGE,GREY,GREY,RED],"연구 수" if ko else "Studies (n)",205)
    def step_status(d,key,within,before,unclear,na):
        v=set(flat_values(d,key))
        if v & set(before): return "BEFORE"
        if v & set(within): return "WITHIN"
        if v & set(unclear): return "UNCLEAR"
        return "NA"
    specs=[("Feature selection","변수선택","PRE13",("WITHIN","TRAIN"),("BEFORE",),("ORDER_NR","OTHER"),("NA",)),
           ("All data-dependent preprocessing","자료의존적 전처리 전체","PRE14",("USED",),("NOT_USED",),("NR","UNC"),("NA",))]
    cols=["WITHIN","BEFORE","UNCLEAR","NA"]; mat=[]
    for en,kr,key,wi,be,un,na in specs:
        cc=Counter(step_status(d,key,wi,be,un,na) for d in CLS); mat.append([cc[x] for x in cols])
    mat=np.array(mat); im=ax[2].imshow(mat,aspect="auto",cmap="YlGnBu",vmin=0,vmax=196)
    ax[2].set_yticks(range(len(specs))); ax[2].set_yticklabels([x[1] if ko else x[0] for x in specs],fontsize=8)
    ax[2].set_xticks(range(4)); ax[2].set_xticklabels(["훈련 안","분할 전","불명확","비해당"] if ko else ["Within training","Before split","Unclear","NA"],fontsize=7.5)
    for i in range(len(specs)):
        for j in range(4): ax[2].text(j,i,str(mat[i,j]),ha="center",va="center",fontsize=8,color="white" if mat[i,j]>95 else "#111827")
    ax[2].set_title("C. 자료의존적 처리를 훈련자료 안에 제한했는가?" if ko else "C. Was data-dependent processing confined to training data?",loc="left",weight="bold",fontsize=10)
    mc=c["missing_strategy"]; ic=c["imbalance_strategy"]
    active=sum(ic.get(k,0) for k in ("SMOTE","RANDOM","WEIGHT","ALGO","MULTIPLE","OTHER"))
    outcome_frequency=sum(d.get("adjudication",{}).get("analytic_flow",{}).get("fields",{}).get("outcome_cases_or_prevalence_reported",{}).get("value") is True for d in CLS)
    dl=(['결측—완전사례','결측—대치·모형처리','결측—미보고','불균형—적극적 처리','불균형—처리 없음','불균형—미보고'] if ko else ['Missing—complete case','Missing—imputation/model handling','Missing—not reported','Imbalance—active handling','Imbalance—no active handling','Imbalance—not reported'])
    dv=[mc.get("COMPLETE",0),sum(mc.get(k,0) for k in ("SINGLE_IMP","MULTI_IMP","MULTIPLE","MODEL_NATIVE","INDICATOR","OTHER")),mc.get("NR",0),active,ic.get("NONE",0),ic.get("NR",0)]
    barh(ax[3],dl,dv,"D. 결측값과 클래스 불균형을 어떻게 처리했는가?" if ko else "D. How were missing values and class imbalance handled?",[ORANGE,BLUE,SKY,RED,GREEN,GREY,RED],"연구 수" if ko else "Studies (n)",205)
    ax[3].title.set_fontsize(10)
    fig.tight_layout(h_pad=2.8,w_pad=4.2); save(fig, "fig7_predictor_training_ko" if ko else "fig7_predictor_training")


def figure6(lang="en"):
    style(lang); ko = lang == "ko"; c = classification_summary(CLS); n = len(CLS)
    fig, ax = plt.subplots(2, 2, figsize=(10.3, 7.0)); ax = ax.ravel()
    vc = c["validation"]
    labs = (["단일 훈련–평가 분할", "교차검증", "겉보기 평가", "시간적 검증", "외부검증", "없음/미보고"] if ko else
            ["Single train–test split", "Cross-validation", "Apparent evaluation", "Temporal validation", "External validation", "None/not reported"])
    barh(ax[0], labs, [vc[k] for k in ("SPLIT","CV","APPARENT","TEMPORAL","EXTERNAL","NONE_NR")],
         f"A. 어디에서 성능을 평가했는가? (n={n})" if ko else f"A. Where was performance evaluated? (n={n})", [ORANGE,BLUE,GREY,GREEN,GREEN,RED], "연구 수(중복 허용)" if ko else "Studies (multiple permitted)", 150)
    cr = c["class_recoverability"]
    barh(ax[1], ["예", "부분적으로", "아니요"] if ko else ["Yes", "Partly", "No"],
         [cr.get("R",0), cr.get("P",0), cr.get("NR",0)+cr.get("UNC",0)],
         "B. 평가자료의 유병률을 확인할 수 있었는가?" if ko else "B. Was evaluation-set prevalence reported?",
         [GREEN,ORANGE,RED], "연구 수" if ko else "Studies (n)", 150)
    th = c["threshold_methods"]
    tlabs = (["미보고", "0.5 고정", "검증자료로 선정", "Youden 지수", "F1 최적화", "임상/비용 기준", "이진 임계값 비해당", "기타 규칙"] if ko else
             ["Not reported", "Fixed at 0.5", "Selected using validation data", "Youden index", "F1-optimised", "Clinical/cost-based rule", "No binary cutoff used", "Other reported rule"])
    tvals = [th[k] for k in ("NR","FIXED05","VAL_OOF","YOUDEN","F1","CLINICAL","NA","OTHER")]
    barh(ax[2], tlabs, tvals, "C. 양성 판정 임계값을 어떻게 정했는가?" if ko else "C. How was the positive-class cutoff chosen?",
         [RED,SKY,GREEN,BLUE,ORANGE,GREEN,GREY,PURPLE], "연구 수" if ko else "Studies (n)", 145)
    q=c["metrics"]; mr=c["metric_reporting"]
    glabs = (["판별: AUROC","클래스: AUPRC","클래스: 민감도","클래스: 특이도","클래스: PPV","클래스: F1","확률: 보정","확률: Brier","효용: 결정곡선","불확실성: 신뢰구간","비교: 짝지은 비교"] if ko else
             ["Discrimination: AUROC","Class: AUPRC","Class: sensitivity","Class: specificity","Class: PPV","Class: F1","Probability: calibration","Probability: Brier score","Utility: decision curve","Uncertainty: confidence interval","Comparison: paired comparison"])
    gvals=[q[k] for k in ("AUROC","AUPRC","SENS","SPEC","PPV","F1")]
    gvals += [sum(any(has(d,k,{"R"}) for k in ("MET_CALSLOPE_R","MET_CALINT_R","MET_CALPLOT_R")) for d in CLS),q["BRIER"],q["DCA"],mr["MET_CI"],mr["MET_PAIR"]]
    barh(ax[3], glabs, gvals, "D. 성능의 어떤 측면을 보고했는가?" if ko else "D. Which aspects of performance were reported?",
         [BLUE]+[SKY]*5+[GREEN]*2+[ORANGE,PURPLE,PURPLE], "연구 수(중복 허용)" if ko else "Studies (multiple permitted)", 205)
    fig.tight_layout(h_pad=2.5,w_pad=2.4); save(fig, "fig9_validation_evaluation_ko" if ko else "fig9_validation_evaluation")


def figure7(lang="en"):
    style(lang); ko = lang == "ko"; D = CONS["content"]; I = CONS["classification"]["importance"]
    fig, ax = plt.subplots(2, 2, figsize=(10.6, 7.2)); ax = ax.ravel()
    labels = (["근거: 성능 향상", "근거: 선별/맞춤화", "근거: 요인 해석", "기능: 예측/분류", "기능: 알고리즘 비교", "기능: 변수/요인 해석"] if ko else
              ["Rationale: performance", "Rationale: screening/personalisation", "Rationale: factor interpretation", "Function: prediction/classification", "Function: algorithm comparison", "Function: feature interpretation"])
    vals = [D[k] for k in ("RAT_PERF","RAT_SCREEN","RAT_FACTOR","FUN_PRED","FUN_COMPARE","FUN_INTERP")]
    barh(ax[0], labels, vals, "A. 명시된 근거와 실제 분석 기능" if ko else "A. Stated rationale versus actual analytic function",
         [SKY,SKY,SKY,BLUE,BLUE,BLUE], "연구 수(중복 허용)" if ko else "Studies (multiple permitted)", 225)
    periods = ["≤2019","2020–2022","2023–2024","2025–2026"]
    den, num = Counter(), Counter()
    for d in CLS:
        p = period(int(d["metadata"]["publication_year"])); den[p] += 1; num[p] += has(d,"VI01",{"USED"})
    pct = [100*num[p]/den[p] for p in periods]
    ax[1].bar(range(4), pct, color=BLUE); ax[1].set_xticks(range(4)); ax[1].set_xticklabels(["≤2019","2020–22","2023–24","2025–26"])
    ax[1].set_ylim(0,100); ax[1].set_ylabel("%")
    ax[1].set_title("B. 명시적 변수중요도 사용의 증가" if ko else "B. Adoption of explicit variable importance", loc="left", weight="bold")
    for i,p in enumerate(periods): ax[1].text(i,pct[i]+2,f"{num[p]}/{den[p]}",ha="center",fontsize=8)
    pathway = [196,I["VI01"],I["VI10"],I["VI11"],I["VI14"]]
    plabs = (["분류", "명시적 중요도", "모형 기반 부분집합", "후속 통계추론", "정확한 변수 이월"] if ko else
             ["Classification", "Explicit importance", "Model-guided subset", "Downstream inference", "Exact variable carryover"])
    barh(ax[2], plabs, pathway, "C. 변수 중심 분석 경로" if ko else "C. Variable-centred analytic pathway",
         [BLUE,SKY,GREEN,ORANGE,RED], "연구 수" if ko else "Studies (n)", 205)
    domains = Counter()
    for d in CLS:
        domains.update(set(v for v in flat_values(d,"VI07") if v not in {"NA","NR","UNC"}))
    top = domains.most_common(8)
    names = {"AGE":"Age","ADIPOSITY_BODY_SIZE":"Adiposity/body size","SOCIOECONOMIC":"Socioeconomic context","OTHER":"Other",
             "SEX":"Sex","MENTAL_SUBJECTIVE_HEALTH":"Mental/subjective health","LIPIDS":"Lipids","PHYSICAL_ACTIVITY_FUNCTION":"Physical activity/function"}
    trans = {"AGE":"연령","ADIPOSITY_BODY_SIZE":"비만·체격","SOCIOECONOMIC":"사회경제·환경","OTHER":"기타",
             "SEX":"성별","MENTAL_SUBJECTIVE_HEALTH":"정신·주관적 건강","LIPIDS":"지질","PHYSICAL_ACTIVITY_FUNCTION":"신체활동·기능"}
    barh(ax[3], [trans.get(k,k) if ko else names.get(k,k) for k,_ in top], [v for _,v in top],
         "D. 자주 순위화된 변수 영역" if ko else "D. Most frequently ranked variable domains",
         [BLUE]*8, "연구 수(중복 허용)" if ko else "Studies (multiple permitted)", 115)
    fig.tight_layout(h_pad=2.5,w_pad=2.5); save(fig, "fig7_variable_centred_ko" if ko else "fig7_variable_centred")


def figure8(lang="en"):
    style(lang); ko = lang == "ko"; c = CONS; npred=c["denominators"]["prediction"]; nstudy=c["denominators"]["studies"]
    fig, ax = plt.subplots(1, 3, figsize=(13.0, 4.6))
    rkeys = ["REP09","REP10","REP17","REP19"]
    rlabs = (["표본크기 근거", "결측자료 절차", "재사용 가능한 최종모형", "공개 코드/모형"] if ko else
             ["Sample-size rationale", "Missing-data procedure", "Reusable final model", "Open code/model"])
    rvals = [npred-c["reporting"][k].get("R",0) for k in rkeys[:3]]
    rvals.append(npred-sum(has(d,"MOD14",{"USED"}) or has(d,"MOD15",{"USED"}) for d in PRED))
    barh(ax[0], rlabs, rvals, f"A. 선택 보고 결함 (n={npred})" if ko else f"A. Selected reporting gaps (n={npred})",
         [RED,ORANGE,RED,ORANGE], "미충족 연구 수" if ko else "Studies with the gap (n)", npred+8)
    slabels = (["가중치 언급", "모형 적합에 가중치 사용", "성능평가에 가중치 사용", "층화변수 보고", "집락/PSU 보고", "설계기반 분산 추정"] if ko else
               ["Weights mentioned", "Weights used in fitting", "Weights used in evaluation", "Strata reported", "Clusters/PSUs reported", "Design-based variance estimation"])
    svals = [c["survey"][k].get("USED",0) for k in ("SUR04","SUR06","SUR07","SUR08","SUR09","SUR10")]
    barh(ax[1], slabels, svals, f"B. 복합표본 처리 (n={nstudy})" if ko else f"B. Survey-design handling (n={nstudy})",
         [SKY,RED,RED,BLUE,BLUE,GREEN], "연구 수" if ko else "Studies (n)", 225)
    a=c["probast_ai"]; phases=[("development", "개발 방법론 품질" if ko else "Development quality"), ("evaluation", "성능평가 비뚤림 위험" if ko else "Evaluation risk of bias")]
    for y,(phase,label) in enumerate(phases):
        overall=a[phase]["overall"]; n=a[phase]["n_units"]
        if phase=="development": order=[("HIGH",GREEN,"높은 품질/낮은 위험" if ko else "High quality/low risk"),("UNC",GREY,"불명확" if ko else "Unclear"),("LOW",RED,"낮은 품질/높은 위험" if ko else "Low quality/high risk")]
        else: order=[("LOW",GREEN,"낮은 위험" if ko else "Low risk"),("UNC",GREY,"불명확" if ko else "Unclear"),("HIGH",RED,"높은 위험" if ko else "High risk")]
        left=0
        for key,col,ll in order:
            v=overall.get(key,0); ax[2].barh(y,100*v/n,left=left,color=col,label=ll if y==0 else None)
            if 100*v/n >= 8: ax[2].text(left+50*v/n,y,f"{v}/{n}",ha="center",va="center",fontsize=7,color="white" if v/n>.45 else "black")
            left += 100*v/n
    ax[2].set_yticks([0,1]); ax[2].set_yticklabels([f"{phases[0][1]}\n(n={a['development']['n_units']})",f"{phases[1][1]}\n(n={a['evaluation']['n_units']})"]); ax[2].invert_yaxis(); ax[2].set_xlim(0,100); ax[2].set_xlabel("%")
    ax[2].set_title("C. PROBAST+AI 종합판정" if ko else "C. Overall PROBAST+AI judgements",loc="left",weight="bold")
    ax[2].legend(frameon=False,fontsize=7,loc="upper center",bbox_to_anchor=(.5,-.18),ncol=3)
    fig.tight_layout(w_pad=2.7); save(fig, "fig8_method_support_ko" if ko else "fig8_method_support")


def figure9(lang="en"):
    style(lang); ko = lang == "ko"; periods=["≤2019","2020–2022","2023–2024","2025–2026"]
    rows = [
        ("Explicit variable importance","명시적 변수중요도",lambda d:has(d,"VI01",{"USED"})),
        ("SHAP","SHAP",lambda d:has(d,"VI02",{"SHAP"})),
        ("Importance stability assessed","중요도 안정성 평가",lambda d:has(d,"VI16",{"USED"})),
        ("External/temporal validation","외부·시간적 검증",lambda d:any(has(d,"VAL02",{x}) for x in ("EXTERNAL","TEMPORAL"))),
        ("Calibration","보정",lambda d:any(has(d,k,{"R"}) for k in ("MET_BRIER_R","MET_CALSLOPE_R","MET_CALINT_R","MET_CALPLOT_R"))),
        ("Paired model comparison","짝지은 모형 비교",lambda d:has(d,"MET_PAIR",{"Y","USED"})),
        ("Sample-size rationale","표본크기 근거",lambda d:has(d,"REP09",{"R","P"})),
        ("Survey weights reported","표본가중치 보고",lambda d:has(d,"SUR04",{"USED"})),
        ("Reusable code/model","재사용 가능한 코드/모형",lambda d:has(d,"MOD14",{"USED"}) or has(d,"MOD15",{"USED"})),
    ]
    num=np.zeros((len(rows),4)); den=np.zeros_like(num)
    for d in CLS:
        j=periods.index(period(int(d["metadata"]["publication_year"])))
        for i,(_,_,fn) in enumerate(rows): den[i,j]+=1; num[i,j]+=fn(d)
    mat=np.divide(100*num,den,out=np.zeros_like(num),where=den>0)
    fig,ax=plt.subplots(figsize=(8.0,5.2)); im=ax.imshow(mat,aspect="auto",cmap="YlGnBu",vmin=0,vmax=100)
    ax.set_xticks(range(4)); ax.set_xticklabels(periods)
    ax.set_yticks(range(len(rows))); ax.set_yticklabels([b if ko else a for a,b,_ in rows],fontsize=8)
    for i in range(len(rows)):
        for j in range(4): ax.text(j,i,f"{mat[i,j]:.0f}%\n({int(num[i,j])}/{int(den[i,j])})",ha="center",va="center",fontsize=6.4,color="white" if mat[i,j]>55 else "#111827")
    ax.axhline(2.5,color="white",lw=2)
    ax.text(3.55,1,"분석 활용" if ko else "Analytic use",rotation=90,va="center",fontsize=8,color=BLUE)
    ax.text(3.55,5.5,"근거 지원" if ko else "Evidentiary support",rotation=90,va="center",fontsize=8,color=RED)
    ax.set_title("분석 활용과 근거 지원의 시기별 변화" if ko else "Temporal change in analytic use and evidentiary support",loc="left",weight="bold")
    fig.colorbar(im,ax=ax,fraction=.035,pad=.08,label="분류 연구 중 백분율" if ko else "% of classification studies")
    fig.tight_layout(); save(fig,"fig9_temporal_support_ko" if ko else "fig9_temporal_support")


def figure4_nonclassification(lang="en"):
    style(lang); ko=lang=="ko"; method=[r for r in PURPOSE_RECORDS if r["study_category"]=="METHOD_RESEARCH"]
    fig,ax=plt.subplots(2,2,figsize=(11.8,9.6)); ax=ax.ravel()
    kinds=["METHOD_WORKFLOW_OR_TOOL_DEVELOPMENT_OR_IMPROVEMENT","EXISTING_METHODS_COMPARISON_OR_EVALUATION"]
    kc=Counter(r["method_research_category"] for r in method)
    barh(ax[0],["방법·절차·도구 개발\n또는 개선","기존 방법 비교\n또는 평가"] if ko else ["Method/workflow/tool\ndevelopment\nor improvement","Existing-method\ncomparison\nor evaluation"],[kc[k] for k in kinds],"A. 방법론적 기여 유형 (N=36)" if ko else "A. Methodological contribution (N=36)",[ORANGE]*2,"연구 수" if ko else "Studies",40)
    # Collapse the detailed intervention codes into distinct workflow levels.
    # Detailed, potentially overlapping codes remain in the study-level audit.
    stages=["DATA_INTEGRATION_OR_HARMONISATION","MISSING_DATA","FEATURE_ENGINEERING_OR_SELECTION","MODEL_DEVELOPMENT","EXPLAINABLE_AI","VALIDATION_OR_PERFORMANCE_EVALUATION","USER_TOOL_OR_WORKFLOW"]
    sc=Counter(x for r in method for x in r["method_intervention_stages"])
    stage_vals=[sc["DATA_INTEGRATION_OR_HARMONISATION"],sc["MISSING_DATA"],sc["FEATURE_ENGINEERING_OR_SELECTION"],
                sum(any(x in r["method_intervention_stages"] for x in ("PREDICTION_OR_CLASSIFICATION","CLUSTERING_OR_REPRESENTATION","CAUSAL_OR_STRUCTURE_LEARNING")) for r in method),
                sc["EXPLAINABLE_AI"],sc["VALIDATION_OR_PERFORMANCE_EVALUATION"],sc["USER_TOOL_OR_WORKFLOW"]]
    # Korean stage labels are short enough for single lines. Avoid wrapping here:
    # seven two-line labels in a half-page panel visually merge adjacent rows.
    sl_ko=["자료통합·조화","결측자료","변수 구성·선택","모델 개발","설명·해석","검증·성능평가","사용자 도구·절차"]
    sl_en=["Data integration/\nharmonisation","Missing data","Variable construction/\nselection","Model development","Explanation/\ninterpretation","Validation/\nperformance evaluation","User tool/\nworkflow"]
    barh(ax[1],sl_ko if ko else sl_en,stage_vals,"B. 대상 워크플로 단계 (N=36)" if ko else "B. Workflow stages targeted (N=36)",[ORANGE]*len(stages),"연구 수(중복 허용)" if ko else "Studies (multiple permitted)",40)
    for label in ax[1].get_yticklabels():
        label.set_linespacing(.78)
    roles=["APPLICATION_OR_TEST_DATASET","ONE_OF_MULTIPLE_PRIMARY_DATASETS","EXTERNAL_OR_TRANSPORTABILITY_EVALUATION"]
    rc=Counter(r["knhanes_position"] for r in method)
    rl_ko=["적용·시험자료","여러 주 자료 중\n하나","외부·이식가능성\n평가"]
    rl_en=["Application/test dataset","One of multiple\nprimary datasets","External/transportability\nevaluation"]
    barh(ax[2],rl_ko if ko else rl_en,[rc[k] for k in roles],"C. KNHANES의 역할 (N=36)" if ko else "C. Role of KNHANES (N=36)",[ORANGE]*len(roles),"연구 수" if ko else "Studies",40)
    modes=["SIMULATION_AND_EMPIRICAL_APPLICATION","EMPIRICAL_COMPARATOR_EVALUATION","EXTERNAL_OR_TRANSPORTABILITY_EVALUATION","APPLICATION_OR_DEMONSTRATION","OTHER_EVALUATION_DESIGN","EVALUATION_DESIGN_INSUFFICIENTLY_REPORTED"]
    mc=Counter(r["method_evaluation_mode"] for r in method)
    ml_ko=["시뮬레이션+\n경험자료","경험자료 비교평가","독립 자료/\n모집단 평가","적용·시연","기타 평가설계","평가설계\n보고 불충분"]
    ml_en=["Simulation plus\nempirical application","Empirical comparator evaluation","Independent-dataset/\npopulation evaluation","Application/demonstration","Other evaluation design","Evaluation design\ninsufficiently reported"]
    mode_rows=[(label,mc[k]) for label,k in zip(ml_ko if ko else ml_en,modes) if mc[k]>0]
    mode_colors=[GREY if "불충분" in label or "insufficiently" in label else ORANGE for label,_ in mode_rows]
    barh(ax[3],[x[0] for x in mode_rows],[x[1] for x in mode_rows],"D. 방법 평가 설계 (N=36)" if ko else "D. Method-evaluation design (N=36)",mode_colors,"연구 수" if ko else "Studies",40)
    fig.tight_layout(h_pad=2.7,w_pad=3.0); save(fig,"fig5_nonclassification_ko" if ko else "fig5_nonclassification")
    return
    fig,ax=plt.subplots(1,2,figsize=(11.8,4.9))
    outcome=Counter()
    for d in cont:
        s=" ".join(map(str,flat_values(d,"OUT02"))).lower()
        if any(x in s for x in ("eq-5d","hint-8","quality of life","stress","phq")): outcome["QoL/mental"]+=1
        elif any(x in s for x in ("ldl","creatin")): outcome["Biochemical"]+=1
        elif any(x in s for x in ("grip","sleep")): outcome["Physical/sleep"]+=1
        else: outcome["Other continuous/ordinal"]+=1
    labs_ko={"QoL/mental":"삶의 질·정신건강","Biochemical":"생화학 지표","Physical/sleep":"신체기능·수면","Other continuous/ordinal":"기타 연속·서열 출력"}
    keys=["QoL/mental","Biochemical","Physical/sleep","Other continuous/ordinal"]
    barh(ax[0],[labs_ko[k] if ko else k for k in keys],[outcome[k] for k in keys],"A. 연속형·순서형 결과 예측 (n=12)" if ko else "A. Continuous- or ordered-outcome prediction (n=12)",[BLUE,SKY,GREEN,GREY],"연구 수" if ko else "Studies (n)",13)
    audit=json.load(open(os.path.join(PROJ,"results/derived/expanded_model_task_audit.json")))
    aa=[x for x in audit["studies"] if "task_appropriate_criteria_reported" in x]
    subtype=Counter(v for d in other for v in flat_values(d,"TSK11"))
    vals=[subtype["IMPUTATION"],subtype["CLUSTERING"],len(other)-subtype["IMPUTATION"]-subtype["CLUSTERING"]]
    barh(ax[1],["결측대체","군집","구조·인과·표현" ] if ko else ["Imputation","Clustering","Structural, causal, or representation"],vals,"B. 기타 분석과제 (n=12)" if ko else "B. Other analytic tasks (n=12)",[BLUE,ORANGE,PURPLE],"연구 수" if ko else "Studies (n)",13)
    defs=[("IMPUTATION","masking_design","대체: masking 설계 (n=3)" if ko else "Imputation: masking design (n=3)"),
          ("IMPUTATION","reconstruction_error","대체: 재구성 오차 (n=3)" if ko else "Imputation: reconstruction error (n=3)"),
          ("IMPUTATION","comparison_baseline","대체: 비교기준 (n=3)" if ko else "Imputation: comparator (n=3)"),
          ("CLUSTERING","stability_assessment","군집: 안정성 (n=2)" if ko else "Clustering: stability (n=2)"),
          ("CLUSTERING","external_replication","군집: 외부 재현 (n=2)" if ko else "Clustering: external replication (n=2)"),
          ("CAUSAL","identification_assumptions","인과: 식별가정 (n=5)" if ko else "Causal: identification assumptions (n=5)"),
          ("CAUSAL","sensitivity_or_overlap","인과: 민감도·overlap (n=5)" if ko else "Causal: sensitivity/overlap (n=5)"),
          ("REPRESENTATION","downstream_or_external_validation","표현: 후속·외부검증 (n=1)" if ko else "Representation: downstream/external validation (n=1)")]
    def match(x,group): return x["task_group"]=="CONT" if group=="CONT" else x.get("other_task_subtype")==group
    dvals=[sum(bool(x["task_appropriate_criteria_reported"].get(key)) for x in aa if match(x,group)) for group,key,label in defs]
    brief=(f"과제별 점검: 대체 masking/복원오차/비교기준 {dvals[0]}/{dvals[1]}/{dvals[2]} (n=3); 군집 안정성/외부재현 {dvals[3]}/{dvals[4]} (n=2); 인과 식별가정/민감도·overlap {dvals[5]}/{dvals[6]} (n=5)" if ko else f"Task-specific checks: imputation masking/error/comparator {dvals[0]}/{dvals[1]}/{dvals[2]} (n=3); clustering stability/external replication {dvals[3]}/{dvals[4]} (n=2); causal assumptions/sensitivity-overlap {dvals[5]}/{dvals[6]} (n=5)")
    # Task-specific checks and the independently audited continuous-study
    # interpretation fields remain in Additional file 5; tiny callouts made the
    # main figure difficult to read and previously treated classification-only
    # VI01=NA as absence of importance analysis.
    fig.tight_layout(w_pad=3.0); save(fig,"fig5_nonclassification_ko" if ko else "fig5_nonclassification")


def figure5_classification(lang="en"):
    style(lang); ko=lang=="ko"; n=len(HEALTH); fig,ax=plt.subplots(2,2,figsize=(11.2,7.3)); ax=ax.ravel()
    labels_en={"MENTAL_HEALTH":"Mental health","METABOLIC_ENDOCRINE":"Metabolic/endocrine","CARDIOVASCULAR":"Cardiovascular disease","MUSCULOSKELETAL":"Musculoskeletal health","ORAL_HEALTH":"Oral health","RESPIRATORY":"Respiratory health","GENERAL_HEALTH_MULTIMORBIDITY":"General health and multimorbidity","KIDNEY_UROLOGIC":"Kidney/urologic health","OTORHINOLARYNGOLOGIC":"Ear, nose and throat"}
    labels_ko={"MENTAL_HEALTH":"정신건강","METABOLIC_ENDOCRINE":"대사·내분비","CARDIOVASCULAR":"심혈관질환","MUSCULOSKELETAL":"근골격계 건강","ORAL_HEALTH":"구강건강","RESPIRATORY":"호흡기 건강","GENERAL_HEALTH_MULTIMORBIDITY":"전반적 건강·다중질환","KIDNEY_UROLOGIC":"신장·비뇨기 건강","OTORHINOLARYNGOLOGIC":"이비인후 건강"}
    # Same amended study-level taxonomy as S1A, S1B and S7; no legacy topic fallback.
    topic_counts=Counter(PURPOSE_V13_BY_ID[d["study_id"]]["health_topic"]["primary_topic_18"] for d in HEALTH)
    topics=sorted(topic_counts.items(),key=lambda x:(-x[1],x[0]))[:8]
    shown_keys={key for key,_ in topics}
    remaining=sum(value for key,value in topic_counts.items() if key not in shown_keys)
    topics.append(("remaining",remaining))
    assert sum(value for _,value in topics)==n
    tl=labels_ko if ko else labels_en
    topic_colors=[GREY if k=="remaining" else BLUE for k,_ in topics]
    topic_labels=[("나머지 주제 범주" if ko else "Remaining topic categories") if k=="remaining" else tl.get(k,k.replace('_',' ').title()) for k,_ in topics]
    barh(ax[0],topic_labels,[v for _,v in topics],f"A. {'건강분석의 주요 건강주제' if ko else 'Leading health topics'} (N={n})",topic_colors,"연구 수" if ko else "Studies (n)",55)
    ax[0].axhline(len(topics)-1.5,color='#9CA3AF',linewidth=.8)
    restrictions=lambda d:d.get("adjudication",{}).get("selection_restriction_dimensions",{}).get("fields",{})
    restriction_order=("age_restriction","sex_restriction","disease_or_risk_restriction","measurement_or_data_availability_restriction")
    rvals=[sum(restrictions(d).get(k,{}).get("value") is True for d in HEALTH) for k in restriction_order]
    rl=(['연령 제한','성별 제한','질환·위험집단 제한','측정·자료가용성\n제한'] if ko else ['Age restriction','Sex restriction','Disease/risk restriction','Measurement/data-availability\nrestriction'])
    barh(ax[1],rl,rvals,f"B. 대상자 선정 조건 (N={N_HEALTH})" if ko else f"B. Participant-selection conditions (N={N_HEALTH})",[BLUE]*4,"연구 수(중복 허용)" if ko else "Studies (multiple permitted)",195)  # prompt 106: denominator from data
    flow=lambda d:d.get("adjudication",{}).get("analytic_flow",{}).get("fields",{})
    sample=[]; events=[]
    for d in HEALTH:
        for dest,key in ((sample,"final_analytic_sample_n"),(events,"positive_event_n")):
            raw=flow(d).get(key,{}).get("value",[]); raw=raw if isinstance(raw,list) else [raw]
            v=next((float(x) for x in raw if isinstance(x,(int,float))),None)
            if v is not None: dest.append(v)
    q1,med,q3=np.percentile(sample,[25,50,75])
    # A low-profile histogram provides distributional context; the smaller rug-like
    # points sit in the lower half so neither layer obscures the other.
    hist_edges=np.logspace(np.log10(min(sample)),np.log10(max(sample)),17)
    hist_counts,_=np.histogram(sample,bins=hist_edges)
    hist_height=.62*hist_counts/max(hist_counts)
    ax[2].bar(hist_edges[:-1],hist_height,width=np.diff(hist_edges),bottom=-.46,
              align='edge',color='#CBD5E1',alpha=.62,edgecolor='white',linewidth=.35,zorder=0)
    scattered=scattered_rug_y(sample,hist_edges,low=-.43,high=.13,subbins=3,seed=20260917)
    ax[2].scatter(sample,scattered,s=15,color=BLUE,alpha=.70,edgecolors='white',linewidth=.20,zorder=3)
    ax[2].axvspan(q1,q3,color=SKY,alpha=.24,zorder=.5); ax[2].axvline(med,ymax=.76,color=RED,linewidth=1.6,zorder=4)
    ax[2].set_xscale('log'); ax[2].set_xticks([1000,10000,100000]); ax[2].set_xticklabels(['1,000','10,000','100,000']); ax[2].set_yticks([]); ax[2].set_ylim(-.48,.52)
    ax[2].grid(axis='x',color='#E5E7EB',linewidth=.6); ax[2].set_axisbelow(True)
    ax[2].set_xlabel("최종 분석대상자 수(로그 척도)" if ko else "Final analytic sample size (log scale)")
    ax[2].set_title((f"C. 최종 표본크기\n분포 (N={N_HEALTH})" if ko else f"C. Final sample-size\ndistribution (N={N_HEALTH})"),loc='left',weight='bold',fontsize=9.4)  # prompt 106: denominator from data
    summary=(f"중앙값 {med:,.0f}\nIQR {q1:,.0f}–{q3:,.0f}" if ko else f"Median {med:,.0f}\nIQR {q1:,.0f}–{q3:,.0f}")
    ax[2].text(.01,.93,summary,transform=ax[2].transAxes,fontsize=8.2,va='top',color="#111827")
    ax[2].text(.99,.93,("미보고 = 3" if ko else "Not reported = 3"),transform=ax[2].transAxes,
               ha='right',va='top',fontsize=7.8,color=GREY,
               bbox={'facecolor':'white','edgecolor':'#9CA3AF','linewidth':.6,'pad':2.0})
    fkeys=["source_population_size_reported","eligibility_criteria_reported","exclusion_numbers_reported","exclusion_reasons_reported","final_analytic_sample_reported","complete_cohort_traceability"]
    fv=[sum(flow(d).get(k,{}).get("value") is True for d in HEALTH) for k in fkeys]
    fl=(['원천 표본 수','적격 기준','제외 인원','제외 사유','최종 분석표본','모든 선정 단계 보고'] if ko else ['Source-population size','Eligibility criteria','Exclusion counts','Exclusion reasons','Final analytic sample','All selection steps reported'])
    barh(ax[3],fl,fv,f"D. 대상자 흐름\n보고 (N={N_HEALTH})" if ko else f"D. Participant-flow\nreporting (N={N_HEALTH})",[SKY]*5+[BLUE],"건강 중심 연구 수" if ko else "Health-focused studies",195)  # prompt 106: denominator from data
    ax[3].axhline(4.5,color='#64748B',linewidth=.9)
    ax[3].patches[-1].set_edgecolor('#004E73'); ax[3].patches[-1].set_linewidth(1.1)
    fig.tight_layout(h_pad=2.7,w_pad=3.0); save(fig,"fig4_populations_ko" if ko else "fig4_populations")
    return
    scheme=Counter()
    for d in CLS:
        rs=rows=d.get("protocol_items",{}).get("OUT09",[]); scales={x.get("value") for x in rs}; units={x.get("unit_id") for x in rs if x.get("value")=="BINARY"}
        if len(scales)>1: scheme["MIXED"]+=1
        elif "MULTICLASS" in scales: scheme["MULTICLASS"]+=1
        elif "MULTIBIN" in scales or len(units)>1: scheme["MULTIBIN"]+=1
        else: scheme["BINARY"]+=1
    barh(ax[0],["이진","복수의 개별 이진 결과","다중분류","혼합"] if ko else ["Binary","Multiple separate binary outcomes","Multiclass","Mixed"],[scheme[k] for k in ("BINARY","MULTIBIN","MULTICLASS","MIXED")],"A. 어떤 분류 구조를 사용했는가?" if ko else "A. What classification structure was used?",[BLUE,SKY,ORANGE,PURPLE],"연구 수" if ko else "Studies (n)",205)
    sc=Counter(c for d in CLS for c in (lambda v: v if isinstance(v,list) else [v])(d.get("adjudication",{}).get("analytic_flow",{}).get("fields",{}).get("outcome_ascertainment_source_category",{}).get("value","NOT_REPORTED")))
    sk=["VALIDATED_QUESTIONNAIRE_OR_SCALE","CLINICAL_OR_PHYSICAL_MEASUREMENT","LABORATORY_THRESHOLD"]
    sl=(['설문·검증척도','임상·신체측정','검사실 수치','진단·질병력','기타 보고 출처','미보고'] if ko else ['Questionnaire/validated scale','Clinical/physical measurement','Laboratory values','Diagnosis/disease history','Other reported source','Not reported'])
    sv=[sc[k] for k in sk]+[sc["SELF_REPORTED_DIAGNOSIS"]+sc["PHYSICIAN_DIAGNOSIS"],sc["DATA_DERIVED_CLASS"]+sc["OTHER_REPORTED_SOURCE"]+sc["COMPOSITE_DEFINITION"],sc["NOT_REPORTED"]]
    barh(ax[1],sl,sv,"B. 목적변수는 어떤 측정에서 파생되었는가?" if ko else "B. From which measurements were outcomes derived?",[GREEN,BLUE,SKY,ORANGE,PURPLE,GREY],"연구 수; 원문 표현의 규칙기반 분류" if ko else "Studies; rule-classified from reported source",205)
    oc=Counter(reduce_recoverability(d,"OUT16") for d in CLS)
    dl=(["충분히 기술됨","부분적으로 기술됨","재구성 불가"] if ko else ["Sufficiently described","Partly described","Not reconstructable"])
    barh(ax[2],dl,[oc[k] for k in ("FULL","PART","NO")],"C. 목적변수 정의를 재구성할 수 있었는가?" if ko else "C. Could the outcome definition be reconstructed?",[GREEN,ORANGE,RED],"분류 연구 수" if ko else "Classification studies (n)",205)

    rc=Counter(reduce_recoverability(d,"PRD13") for d in CLS)
    initial=sum(isinstance(d.get("adjudication",{}).get("analytic_flow",{}).get("fields",{}).get("initial_candidate_predictor_count",{}).get("value"),(int,float)) for d in CLS)
    rl=(['처음 검토한 설명변수 전체 확인','일부만 확인','전체 확인 불가','초기 후보변수 수 보고'] if ko else ['All initially considered predictors identifiable','Predictors partly identifiable','Full set not identifiable','Initial candidate count reported'])
    barh(ax[3],rl,[rc['FULL'],rc['PART'],rc['NO'],initial],"D. 처음 검토한 설명변수를 확인할 수 있었는가?" if ko else "D. Could the initially considered predictors be identified?",[GREEN,ORANGE,RED,BLUE],"분류 연구 수" if ko else "Classification studies (n)",205)
    fig.tight_layout(h_pad=2.5,w_pad=2.5); save(fig,"fig6_classification_outcomes_ko" if ko else "fig6_classification_outcomes")


def figure7_model_development(lang="en"):
    style(lang); ko=lang=="ko"; audit=json.load(open(os.path.join(PROJ,"results/derived/expanded_model_task_audit.json"))); fig,ax=plt.subplots(2,2,figsize=(11.2,7.5)); ax=ax.ravel()
    alg=MASTER["algorithms"][:10]
    barh(ax[0],[x[0] for x in alg],[x[1] for x in alg],"A. 평가한 알고리즘 계열" if ko else "A. Algorithm families evaluated",[BLUE]*len(alg),"연구 수(중복 허용)" if ko else "Studies (multiple permitted)",120)
    cls_a=[x for x in audit["studies"] if x["task_group"]=="CLS"]
    ds=MASTER["data_scale"]
    role_labs=(['전체 사건 수','적어도 한 적합모형의 입력차원','사건 수와 입력차원 동시 확인'] if ko else ['Overall event count reported','Input dimension for ≥1 fitted model','Event count and input dimension both reported'])
    role_vals=[ds["event_count_recoverable"],ds["input_count_recoverable"],ds["event_and_input_recoverable"]]
    barh(ax[1],role_labs,role_vals,"B. 사건 수와 모형 입력 수가 모두 있었는가?" if ko else "B. Were outcome-event and model-input counts both available?",[BLUE,ORANGE],"연구 수" if ko else "Studies (n)",205)
    ts=Counter(x["algorithm_development"]["tuning_selection_status"] for x in cls_a)
    keys=["TUNING_REPORTED_SEPARATED","TUNING_REPORTED_SEPARATION_NOT_DEMONSTRATED","TUNING_REPORTED_EVALUATION_DATA_INVOLVED","TUNING_NOT_REPORTED","NO_TUNING_OR_DEFAULT_MODEL"]
    labs=(['튜닝 보고+평가와 분리','튜닝 보고, 분리 입증 안 됨','튜닝에 평가자료 관여','튜닝 미보고','튜닝 없음·기본모형'] if ko else ['Tuning reported + separated','Tuning reported; separation not demonstrated','Tuning reported; evaluation data involved','Tuning not reported','No tuning/default model'])
    barh(ax[2],labs,[ts[k] for k in keys],"C. 모형 튜닝을 최종평가와 분리했는가?" if ko else "C. Was model tuning separated from final evaluation?",[GREEN,ORANGE,RED,GREY,SKY],"분류 연구 수" if ko else "Classification studies (n)",205)
    def criterion_bucket(selection, metric_index):
        text=str(selection.get("criterion") or "").lower()
        metrics={metric_index.get(i) for i in selection.get("selected_metric_ids",[]) if metric_index.get(i)}
        if text.startswith("nr") or "not recoverable" in text: return "Not recoverable"
        if any(x in text for x in ("no selection","single pre-specified","single prespecified","single algorithm","single model","only model","chosen a priori","author-designated focus","pre-specified as","prespecified as")):
            return "Author judgement/no clear metric"
        if len(metrics)>1: return "Multiple metrics"
        if len(metrics)==1:
            return {"ACC":"Accuracy","AUROC":"AUROC","AUPRC":"AUPRC","F1":"F1"}.get(next(iter(metrics)),"Other criterion")
        return "Author judgement/no clear metric"
    sels=[]; crit=Counter()
    for d in CLS:
        metric_index={m.get("metric_id"):m.get("metric") for m in d.get("performance_metrics",[])}
        for b in d.get("best_model_selections",[]):
            if b.get("author_designated"):
                sels.append(b); crit[criterion_bucket(b,metric_index)]+=1
    fam=MASTER["algorithms"][:5]; flabs=[("최종계열—" if ko else "Final family—")+x[0] for x in fam]; fvals=[x[2] for x in fam]
    ck=["AUROC","Multiple metrics","Other criterion","Accuracy","Author judgement/no clear metric","F1","Not recoverable","AUPRC"]
    trans={"Multiple metrics":"복수 지표","Other criterion":"기타 기준","Accuracy":"정확도","Author judgement/no clear metric":"저자 판단/명확한 지표 없음","Not recoverable":"복원 불가"}
    clabs=[("선택기준—" if ko else "Criterion—")+(trans.get(k,k) if ko else k) for k in ck]
    barh(ax[3],flabs+clabs,fvals+[crit[k] for k in ck],(f"D. 어떤 모형이 어떤 기준으로 선택되었는가? (레코드 n={len(sels)})" if ko else f"D. Which models were selected—and by what criterion? (records n={len(sels)})"),[BLUE]*len(fam)+[ORANGE]*len(ck),"선택 레코드 수; 비교 우월성이 아님" if ko else "Selection records; not comparative superiority",110)
    fig.tight_layout(h_pad=2.5,w_pad=2.6); save(fig,"fig8_model_selection_ko" if ko else "fig8_model_selection")


def figure9_variable(lang="en"):
    style(lang); ko=lang=="ko"; fig=plt.figure(figsize=(11.0,8.8)); gs=fig.add_gridspec(2,2,height_ratios=[.30,1.0],hspace=.62,wspace=1.05,width_ratios=[1.08,1.0])
    ax=[fig.add_subplot(gs[0,:]),fig.add_subplot(gs[1,0]),fig.add_subplot(gs[1,1])]
    reported=sum(has(d,"VI01",{"USED"}) for d in CLS); unreported=len(CLS)-reported
    left=0
    for value,color,label in [(reported,GREEN,"명시적 변수중요도 보고" if ko else "Explicit importance reported"),(unreported,GREY,"명시적 모형 기반\n중요도 미보고" if ko else "Not reported")]:
        width=100*value/len(CLS); ax[0].barh(0,width,left=left,color=color,height=.55)
        ax[0].text(left+width/2,0,f"{label}\n{value}/{N_CORE} ({width:.1f}%)",ha='center',va='center',fontsize=6.6 if value==unreported else 7.7,color='white',linespacing=1.1)  # prompt 106: denominator from data
        left+=width
    ax[0].set_xlim(0,100); ax[0].set_yticks([]); ax[0].set_xlabel('%')
    ax[0].set_title(f"A. 모형 기반 변수중요도 사용 (N={N_CORE})" if ko else f"A. Use of model-based variable importance (N={N_CORE})",loc='left',weight='bold',fontsize=9.2)  # prompt 106: denominator from data
    named=[("SHAP","SHAP"),("MODEL_NATIVE","모형 고유 중요도" if ko else "Model-native"),("COEFFICIENT_STATISTIC","계수·통계량" if ko else "Coefficient/statistic"),("PERMUTATION","순열 중요도" if ko else "Permutation"),("TREE_RULE","트리·규칙" if ko else "Tree/rule"),("PERTURBATION_ABLATION","교란·제거" if ko else "Perturbation/ablation"),("LIME","LIME"),("PDP","PDP")]
    residual={"ALE","ICE","NETWORK_SPECIFIC","OTHER"}
    ml=[x[1] for x in named]+(["ALE·ICE·네트워크/\n기타"] if ko else ["ALE/ICE/network/\nother"])
    ml=[x.replace("Coefficient/statistic","Coefficient/\nstatistic-based").replace("Perturbation/ablation","Perturbation/\nablation") for x in ml]
    mv=[sum(has(d,"VI02",{x[0]}) for d in CLS) for x in named]+[sum(bool(set(flat_values(d,"VI02")) & residual) for d in CLS)]
    _pin(reported, 129, "make_streamlined_figures.py:861")  # prompt 106 pin
    barh(ax[1],ml,mv,f"B. 변수중요도 방법 (적용 가능 N={reported})" if ko else f"B. Variable-importance methods\n(eligible N={reported})",[GREEN]*8+[GREY],"중요도 보고 연구 수(중복 허용)" if ko else "Studies",65)  # prompt 106: denominator from data

    pathway=[sum(has(d,k,{"USED"}) for d in CLS) for k in ("VI16","VI10","VI11","VI14")]
    labels=(['중요도 안정성\n평가','중요도 기반\n축소 변수집합','후속\n통계분석','정확한 변수\n이월'] if ko else ['Importance-stability\nassessment','Importance-guided\nreduced subset','Subsequent\nstatistical analysis','Exact variable\ncarryover'])
    pathway_den=[reported,len(CLS),len(CLS),pathway[2]]
    _pin(pathway, [25,24,12,5], "make_streamlined_figures.py:867")  # prompt 106 pin
    _pin(pathway_den, [129,165,165,12], "make_streamlined_figures.py:867")  # prompt 106 pin
    pct=[100*x/d for x,d in zip(pathway,pathway_den)]; y=np.arange(len(labels))
    ax[2].barh(y,pathway,color=["#008C95",BLUE,PURPLE,'#6D28D9'],height=.62); ax[2].set_yticks(y); ax[2].set_yticklabels(labels,fontsize=8,ha='right',linespacing=.95); ax[2].invert_yaxis(); ax[2].set_xlim(0,30); ax[2].set_xlabel('연구 수' if ko else 'Studies')
    ax[2].set_title("C. 안정성과 후속 활용—항목별 적용 분모" if ko else "C. Stability and downstream use\n(field-specific denominators)",loc='left',weight='bold',fontsize=9.2); ax[2].grid(axis='x',color='#E5E7EB',linewidth=.6); ax[2].set_axisbelow(True)
    for i,(n,d,p) in enumerate(zip(pathway,pathway_den,pct)): ax[2].text(n+.5,i,f"{n}/{d} ({p:.1f}%)",va='center',fontsize=7)
    save(fig,"fig10_variable_interpretation_ko" if ko else "fig10_variable_interpretation")


def figure10_support(lang="en"):
    style(lang); ko=lang=="ko"; c=CONS; npred=c["denominators"]["prediction"]; nstudy=c["denominators"]["studies"]; fig,ax=plt.subplots(2,2,figsize=(11,7.2)); ax=ax.ravel()
    rkeys=["REP09","REP17"]; rv=[c["reporting"][k].get("R",0)+c["reporting"][k].get("P",0) for k in rkeys]; rv.append(sum(has(d,"MOD14",{"USED"}) for d in PRED)); rl=(["표본크기 근거(완전·부분)","재사용 최종모형(완전·부분)","분석 코드 공개"] if ko else ["Sample-size rationale (full/partial)","Reusable final model (full/partial)","Analysis code available"])
    barh(ax[0],rl,rv,f"A. 보고된 분석을 재현하거나 재사용할 수 있었는가? (n={npred})" if ko else f"A. Could the reported analysis be reproduced or reused? (n={npred})",[GREEN]*3,"근거가 있는 연구 수" if ko else "Studies with support (n)",npred+8)
    sl=(["통합기수 가중치 전략","모형 적합에 가중치","성능평가에 가중치","불확실성에 층·PSU"] if ko else ["Combined-cycle weight strategy","Weights in model fitting","Weights in performance evaluation","Strata/PSUs in uncertainty"])
    sv=[c["survey"]["SUR11"].get("USED",0),c["survey"]["SUR06"].get("USED",0),c["survey"]["SUR07"].get("USED",0),c["survey"]["SUR10"].get("USED",0)]
    barh(ax[1],sl,sv,f"B. KNHANES 조사설계를 분석에 반영했는가? (n={nstudy})" if ko else f"B. Was the KNHANES survey design reflected in the analysis? (n={nstudy})",[GREEN]*4,"연구 수" if ko else "Studies (n)",225)
    a=c["probast_ai"]; vals=[a["development"]["overall"].get("HIGH",0),a["evaluation"]["overall"].get("LOW",0)]; labs=([f"높은 개발 품질\n(n={a['development']['n_units']})",f"낮은 평가 비뚤림 위험\n(n={a['evaluation']['n_units']})"] if ko else [f"High development quality\n(n={a['development']['n_units']})",f"Low evaluation risk of bias\n(n={a['evaluation']['n_units']})"])
    barh(ax[2],labs,vals,"C. 개발과 평가가 PROBAST+AI 기준을\n얼마나 충족했는가?" if ko else "C. How often did development and evaluation\nmeet PROBAST+AI standards?",[GREEN,GREEN],"평가단위 수" if ko else "Assessment units (n)",20)
    cs=MASTER["claim_support"]; cl=[("더 나은 예측+짝지은 비교" if ko else "Better prediction + paired comparison",28,179),("선별+검증·보정·역치" if ko else "Screening + validation/calibration/cutoff",6,167),("요인+후속추론·가중치" if ko else "Factors + inference/survey weights",7,185),("구현+인터페이스·전향배치" if ko else "Implementation + interface/deployment",9,21)]
    yy=np.arange(4); ax[3].barh(yy,[x[1] for x in cl],color=GREEN,height=.66); ax[3].set_yticks(yy); ax[3].set_yticklabels([x[0] for x in cl],fontsize=8.1); ax[3].invert_yaxis(); ax[3].set_xlim(0,34); ax[3].grid(axis="x",color="#E5E7EB",linewidth=.6); ax[3].set_axisbelow(True); ax[3].set_xlabel("뒷받침 연구 수" if ko else "Supported studies (n)"); ax[3].set_title("D. 연구 주장은 대응 근거를\n함께 제시했는가?" if ko else "D. Were study claims accompanied by\ncorresponding evidence?",loc="left",weight="bold")
    for i,(_,v,den) in enumerate(cl): ax[3].text(v+.6,i,f"{v}/{den}",va="center",fontsize=8)
    fig.tight_layout(h_pad=2.5,w_pad=2.7); save(fig,"fig10_method_support_ko" if ko else "fig10_method_support")


def figure11_temporal(lang="en"):
    style(lang); ko=lang=="ko"; periods=["≤2019","2020–2022","2023–2024","2025–2026"]
    def txt(d,k): return " ".join(map(str,flat_values(d,k))).lower()
    groups=[
      [("Tree-based boosting","트리 기반 부스팅",lambda d:any(x in txt(d,"MOD02") for x in ("xgboost","lightgbm","catboost","gradient boosting","adaboost","boosting"))),
       ("Explicit variable importance","명시적 변수중요도",lambda d:has(d,"VI01",{"USED"})),
       ("SHAP","SHAP",lambda d:has(d,"VI02",{"SHAP"}))],
      [("External/later-period validation","외부·이후 시기 검증",lambda d:any(has(d,"VAL02",{x}) for x in ("EXTERNAL","TEMPORAL"))),
       ("Calibration","보정",lambda d:any(has(d,k,{"R"}) for k in ("MET_CALSLOPE_R","MET_CALINT_R","MET_CALPLOT_R")))],
      [("Analysis code available","분석 코드 공개",lambda d:has(d,"MOD14",{"USED"})),
       ("Survey weights used","표본가중치 반영",lambda d:has(d,"SUR06",{"USED"}) or has(d,"SUR07",{"USED"}))]]
    rows=[item for group in groups for item in group]
    num=np.zeros((len(rows),4)); den=np.zeros_like(num)
    for d in CLS:
        j=periods.index(period(int(d["metadata"]["publication_year"])))
        for i,(_,_,fn) in enumerate(rows): den[i,j]+=1; num[i,j]+=fn(d)
    mat=np.divide(100*num,den,out=np.zeros_like(num),where=den>0)
    fig,axes=plt.subplots(1,3,figsize=(12.2,4.2),sharey=True)
    panel_titles=(['A. ML 도입','B. 검증','C. 재현성과 조사설계'] if ko else
                  ['A. ML adoption','B. Validation','C. Reproducibility and survey design'])
    colors=[BLUE,ORANGE,GREEN]
    offset=0
    for g,(ax,title) in enumerate(zip(axes,panel_titles)):
        group=groups[g]
        for i,(en,kr,_) in enumerate(group):
            idx=offset+i; y=mat[idx]
            ax.plot(range(4),y,marker='o',linewidth=2.2,markersize=5.5,
                    color=colors[i],label=kr if ko else en)
            label_offset = 7 if i % 2 == 0 else -12
            for j,val in enumerate(y):
                ax.annotate(f"{int(num[idx,j])}/{int(den[idx,j])}",(j,val),
                            xytext=(0,label_offset),textcoords='offset points',ha='center',fontsize=6.5)
        offset += len(group)
        ax.set_title(title,loc='left',weight='bold'); ax.set_xticks(range(4)); ax.set_xticklabels(periods,fontsize=7.5)
        ax.set_ylim(-4,104); ax.grid(axis='y',color='#E5E7EB',linewidth=.7); ax.set_axisbelow(True)
        ax.legend(frameon=False,fontsize=7,loc='upper left')
    axes[0].set_ylabel('분류 연구 중 백분율' if ko else '% of classification studies')
    fig.suptitle('시간에 따른 ML 도입, 검증과 재현성의 변화' if ko else
                 'Changes in ML Adoption, Validation, and Reproducibility Over Time',
                 x=.06,ha='left',weight='bold',fontsize=12)
    fig.tight_layout(rect=(0,0,1,.94),w_pad=2.0)
    save(fig,"fig11_temporal_support_ko" if ko else "fig11_temporal_support")


def figure7_dataset_preparation(lang="en"):
    style(lang); ko=lang=="ko"; c=classification_summary(CLS)
    fig,ax=plt.subplots(2,2,figsize=(11.6,9.2)); ax=ax.ravel()
    flow=lambda d:d.get("adjudication",{}).get("analytic_flow",{}).get("fields",{})
    rc=Counter(reduce_recoverability(d,"PRD13") for d in CLS)
    completeness=[rc["FULL"],rc["PART"],rc["NO"]]
    completeness_labels=(['완전 명세','부분 명세','불충분 명세'] if ko else ['Fully specified','Partly specified','Insufficiently specified'])

    initial_rows=[]
    for d in CLS:
        field=flow(d).get("initial_candidate_predictor_count",{})
        value=field.get("value")
        if field.get("value_status")=="REPORTED" and isinstance(value,(int,float)) and not isinstance(value,bool) and value>0:
            initial_rows.append({"study_id":d["study_id"],"candidate_input_n":int(value) if float(value).is_integer() else float(value)})
    initial_vals=np.array([r["candidate_input_n"] for r in initial_rows],dtype=float)
    q1,median,q3=np.percentile(initial_vals,[25,50,75]); lo,hi=initial_vals.min(),initial_vals.max()
    hist_edges=np.logspace(np.log10(initial_vals.min()),np.log10(initial_vals.max()),14)
    hist_counts,_=np.histogram(initial_vals,bins=hist_edges)
    hist_height=.58*hist_counts/max(hist_counts)
    ax[0].bar(hist_edges[:-1],hist_height,width=np.diff(hist_edges),bottom=-.42,align='edge',
              color='#CBD5E1',alpha=.62,edgecolor='white',linewidth=.35,zorder=0)
    scattered=scattered_rug_y(initial_vals,hist_edges,low=-.41,high=.13,subbins=2,seed=20260918)
    ax[0].scatter(initial_vals,scattered,s=24,color=BLUE,alpha=.70,edgecolor='white',linewidth=.30,zorder=3)
    ax[0].axvspan(q1,q3,color=SKY,alpha=.18,zorder=1); ax[0].axvline(median,ymax=.76,color=RED,linewidth=1.4,zorder=2)
    ax[0].set_xscale('log'); ax[0].set_xticks([10,100,1000]); ax[0].set_xticklabels(['10','100','1,000']); ax[0].set_ylim(-.44,.52); ax[0].set_yticks([]); ax[0].grid(axis='x',color='#E5E7EB',linewidth=.6); ax[0].set_axisbelow(True)
    ax[0].set_xlabel("최초 후보변수 수(로그 척도)" if ko else "Initial predictors (log scale)")
    ax[0].set_title((f"A. 보고된 최초 설명변수 수 (N={N_CORE})" if ko else f"A. Reported initial\npredictor counts (N={N_CORE})"),loc='left',weight='bold',fontsize=9.2)  # prompt 106: denominator from data
    ax[0].text(.01,.93,(f"중앙값 {median:.0f}; IQR {q1:.0f}–{q3:.0f}" if ko else f"Median {median:.0f}; IQR {q1:.0f}–{q3:.0f}"),
               transform=ax[0].transAxes,fontsize=7.7,va='top',color="#374151")
    ax[0].text(.99,.78,("미보고 = 104" if ko else "Not reported = 104"),transform=ax[0].transAxes,
               ha='right',va='top',fontsize=7.6,color=GREY,
               bbox={'facecolor':'white','edgecolor':'#9CA3AF','linewidth':.6,'pad':2.0})

    # Separate rows make all three completeness states directly comparable and
    # avoid encoding a very small category as an unreadable sliver.
    by=np.arange(3)
    ax[1].barh(by,completeness,color=[GREEN,ORANGE,RED],height=.56)
    ax[1].set_yticks(by); ax[1].set_yticklabels(completeness_labels,fontsize=8)
    ax[1].invert_yaxis(); ax[1].set_xlim(0,205); ax[1].set_xlabel("연구 수" if ko else "Studies")
    ax[1].set_xticks([0,50,100,150]); ax[1].grid(axis='x',color='#E5E7EB',linewidth=.6); ax[1].set_axisbelow(True)
    for i,value in enumerate(completeness):
        ax[1].text(value+2,i,f"{value}",va='center',fontsize=8,color='#111827')
    ax[1].set_title(f"B. 후보·최종 변수집합 복원가능성 (N={N_CORE})" if ko else f"B. Candidate/final predictor-set\nrecoverability (N={N_CORE})",loc='left',weight='bold',fontsize=9.5)  # prompt 106: denominator from data
    if not ko:
        export={"schema":"initial_candidate_input_count_study_level_v1","population":"165 health-focused classification studies","source":"adjudication.analytic_flow.fields.initial_candidate_predictor_count; curated from data/input_counts.tsv","inclusion_rule":"Retain only an explicitly labelled overall candidate/input count at the author-identified pipeline-entry stage; do not infer counts by enumerating variable lists.","aggregation":"One audited value per study; differing outcome/subgroup/model-stage values are not averaged.","reporting_studies":len(initial_rows),"summary":{"median":float(median),"q1":float(q1),"q3":float(q3),"minimum":float(lo),"maximum":float(hi)},"records":initial_rows}
        with open(os.path.join(PROJ,"results/derived/initial_candidate_input_count_audit.json"),"w") as f: json.dump(export,f,indent=2,ensure_ascii=False)

    mc=c["missing_strategy"]
    labs=(['완전사례분석','단일대체','다중대체','모형 기반 처리','기타·복수방법','미보고'] if ko else ['Complete-case analysis','Single imputation','Multiple imputation','Model-native handling','Other/multiple methods','Not reported'])
    vals=[mc.get("COMPLETE",0),mc.get("SINGLE_IMP",0),mc.get("MULTI_IMP",0),mc.get("MODEL_NATIVE",0),sum(mc.get(k,0) for k in ("MULTIPLE","INDICATOR","OTHER")),mc.get("NR",0)]
    barh(ax[2],labs,vals,f"C. 결측자료 처리방법 (N={N_CORE})" if ko else f"C. Missing-data strategies (N={N_CORE})",[BLUE,"#56B4E9","#2B8CBE","#74A9CF","#A6BDDB",GREY],"연구 수" if ko else "Studies",120)  # prompt 106: denominator from data
    ax[2].set_xticks([0,50,100])

    def status(d,key,within,before,unclear):
        v=set(flat_values(d,key))
        if v & set(before): return "BEFORE"
        if v & set(within): return "WITHIN"
        if v & set(unclear): return "UNCLEAR"
        return "NA"
    # PRE05/PRE14 ask whether the step was kept inside the training/resampling structure;
    # NOT_USED means it was not (done outside training), so it belongs with "before split".
    specs=[("Missing-value handling","결측값 처리","PRE05",("USED",),("NOT_USED",),("NR","UNC")),
           ("Scaling/other\npreprocessing","척도화·변환 등\n기타 전처리","PRE14",("USED",),("NOT_USED",),("NR","UNC")),
           ("Feature selection","변수선택","PRE13",("WITHIN","TRAIN"),("BEFORE",),("ORDER_NR","OTHER")),
           ("Class rebalancing","클래스 재균형","IMB03",("WITHIN","TRAIN"),("BEFORE",),("ORDER_NR","OTHER"))]
    cols=["WITHIN","UNCLEAR","BEFORE","NA"]
    mat=np.array([[Counter(status(d,key,wi,be,un) for d in CLS)[x] for x in cols] for _,_,key,wi,be,un in specs])
    assert np.all(mat.sum(axis=1)==len(CLS))
    pct=100*mat/len(CLS); left=np.zeros(len(specs))
    status_labels=["훈련자료 내","시점 불명확","훈련자료 외·분할 전","미적용·비해당"] if ko else ["Within training","Timing unclear","Before split","Not applied / NA"]
    for j,(label,color) in enumerate(zip(status_labels,[GREEN,ORANGE,RED,GREY])):
        ax[3].barh(np.arange(len(specs)),pct[:,j],left=left,color=color,height=.66,label=label)
        for i,(n,p) in enumerate(zip(mat[:,j],pct[:,j])):
            # Every non-empty segment is labelled; narrow segments get a short leader to a label below their own bar.
            if p>=8: ax[3].text(left[i]+p/2,i,f"{n}",ha="center",va="center",fontsize=7,linespacing=1.1,color="white" if color in (GREEN,RED,GREY) else "#111827")
            elif n>0:
                x=left[i]+p/2; right_edge=x>90
                ax[3].annotate(f"{n}",xy=(x,i+.26),xytext=(x-4 if right_edge else x+4,i+.47),ha="right" if right_edge else "left",va="center",fontsize=6.6,color="#111827",
                                     arrowprops={"arrowstyle":"-","color":"#374151","lw":.6})
        left+=pct[:,j]
    ax[3].set_yticks(range(len(specs))); ax[3].set_yticklabels([x[1] if ko else x[0] for x in specs],fontsize=7.1)
    ax[3].invert_yaxis(); ax[3].set_ylim(3.75,-.5); ax[3].set_xlim(0,100); ax[3].set_xlabel('%')
    ax[3].set_xlim(0,100)
    fig.legend(*ax[3].get_legend_handles_labels(),frameon=False,fontsize=7.5,ncol=2,loc='lower center',bbox_to_anchor=(.5,.015))
    ax[3].set_title(f"D. 자료의존적 절차의 시점 (N={N_CORE})" if ko else f"D. Data-dependent timing\n(N={N_CORE})",loc="left",weight="bold",fontsize=9.5)  # prompt 106: denominator from data
    fig.subplots_adjust(top=.90,bottom=.20,hspace=.65)
    # Panel C starts farther right so its longest category label is not clipped at the canvas edge.
    for axis,left,right in ((ax[0],.07,.46),(ax[1],.74,.98),(ax[2],.27,.48),(ax[3],.75,.98)):
        pos=axis.get_position();axis.set_position([left,pos.y0,right-left,pos.height])
    save(fig,"fig7_predictor_training_ko" if ko else "fig7_predictor_training")


def figure6_health_classification(lang="en"):
    """Outcome construction in health-focused classification studies."""
    style(lang); ko=lang=="ko"
    fig=plt.figure(figsize=(12.2,8.0))
    outer=fig.add_gridspec(2,1,height_ratios=[.82,4.8],hspace=.82)
    lower=outer[1].subgridspec(1,3,width_ratios=[1.0,1.35,1.05],wspace=1.45)
    ax=[fig.add_subplot(outer[0]),fig.add_subplot(lower[0]),fig.add_subplot(lower[1]),fig.add_subplot(lower[2])]
    timing=Counter(first_applicable(d,"OUT10") for d in CLS)
    current_pct=100*timing['CURRENT']/len(CLS); unclear_pct=100*timing['UNC']/len(CLS)
    ax[0].barh(0,current_pct,color=BLUE,height=.50)
    ax[0].barh(0,unclear_pct,left=current_pct,color=GREY,height=.50)
    current_label = "현재 건강상태" if ko else "current health state"
    ax[0].text(current_pct/2,0,f"{timing['CURRENT']}/{len(CLS)} {current_label}",ha='center',va='center',color='white',fontsize=8.2,weight='bold')
    # Keep the two exceptional timing counts in the unused right side of the
    # panel header, clear of the dominant bar, percentage axis, and lower row.
    ax[0].text(.995,-.85,(f"시점 불명확 1/{N_CORE}" if ko else f"Timing unclear 1/{N_CORE}"),transform=ax[0].transAxes,ha='right',va='bottom',fontsize=7.3,color=GREY)  # prompt 106: denominator from data
    ax[0].set_xlim(0,100); ax[0].set_yticks([]); ax[0].set_xlabel(''); ax[0].set_title(f"A. {'결과 시점' if ko else 'Outcome timing'} (N={len(CLS)})",loc='left',weight='bold',fontsize=9.5)
    scheme=Counter()
    for d in CLS:
        scales=set(flat_values(d,"OUT09")); units={x.get("unit_id") for x in d.get("protocol_items",{}).get("OUT09",[]) if x.get("value")=="BINARY"}
        if len(scales)>1: scheme["MIXED"]+=1
        elif "MULTICLASS" in scales: scheme["MULTICLASS"]+=1
        elif "MULTIBIN" in scales or len(units)>1: scheme["MULTIBIN"]+=1
        else: scheme["BINARY"]+=1
    barh(ax[1],["이진","복수의 개별\n이진 결과","다중분류","혼합"] if ko else ["Binary","Multiple separate\nbinary outcomes","Multiclass","Mixed"],[scheme[k] for k in ("BINARY","MULTIBIN","MULTICLASS","MIXED")],f"B. 분류\n구조 (N={N_CORE})" if ko else f"B. Classification\nstructure (N={N_CORE})",[BLUE]*4,"연구 수" if ko else "Studies",145)  # prompt 106: denominator from data
    source=Counter(c for d in CLS for c in (lambda v: v if isinstance(v,list) else [v])(d.get("adjudication",{}).get("analytic_flow",{}).get("fields",{}).get("outcome_ascertainment_source_category",{}).get("value","NOT_REPORTED")))
    sl=["설문/\n검증척도","임상/\n신체측정","검사실 수치","진단/\n질병력","기타","미보고"] if ko else ["Questionnaire/\nscale","Clinical/physical\nmeasurement","Laboratory values","Diagnosis/\ndisease history","Other","Not reported"]
    sv=[source["VALIDATED_QUESTIONNAIRE_OR_SCALE"],source["CLINICAL_OR_PHYSICAL_MEASUREMENT"],source["LABORATORY_THRESHOLD"],source["SELF_REPORTED_DIAGNOSIS"]+source["PHYSICIAN_DIAGNOSIS"],source["DATA_DERIVED_CLASS"]+source["OTHER_REPORTED_SOURCE"]+source["COMPOSITE_DEFINITION"],source["NOT_REPORTED"]]
    barh(ax[2],sl,sv,f"C. 목적변수\n확인 (N={N_CORE})" if ko else f"C. Outcome\nascertainment (N={N_CORE})",[BLUE]*5+[GREY],"연구 수" if ko else "Studies",75)  # prompt 106: denominator from data
    # Put the long binary count inside its bar, clear of the next panel's labels.
    binary_label=ax[1].texts[0]
    binary_label.set_position((scheme['BINARY']-8,0))
    binary_label.set_ha('right');binary_label.set_color('white')
    outcome=Counter(reduce_recoverability(d,"OUT16") for d in CLS)
    labs=["완전 명세","부분 명세","불충분 명세"] if ko else ["Fully specified","Partly specified","Insufficiently specified"]
    vals=[outcome[k] for k in ("FULL","PART","NO")]
    barh(ax[3],labs,vals,f"D. 목적변수 정의 복원성\n(N={N_CORE})" if ko else f"D. Outcome-definition\nrecoverability (N={N_CORE})",[GREEN,ORANGE,RED],"연구 수" if ko else "Studies",90)  # prompt 106: denominator from data
    save(fig,"fig6_classification_outcomes_ko" if ko else "fig6_classification_outcomes")


def figure8_model_development(lang="en"):
    style(lang); ko=lang=="ko"; fig,ax=plt.subplots(2,2,figsize=(11.8,7.7)); ax=ax.ravel()
    audit=json.load(open(os.path.join(PROJ,"results/derived/expanded_model_task_audit.json")))
    cls_a=[x for x in audit["studies"] if x["task_group"]=="CLS" and x["study_id"] in HEALTH_IDS]
    ac=Counter(f for x in cls_a for f in set(x["algorithm_development"]["algorithm_family"]))
    fixed_order=["Random forest","Logistic regression","XGBoost","SVM","DNN/MLP","LightGBM","Decision tree","Naive Bayes"]
    evaluated_other=sum(bool(set(x["algorithm_development"]["algorithm_family"])-set(fixed_order)) for x in cls_a)
    display_order=fixed_order+["Other families"]
    avals=[ac[k] for k in fixed_order]+[evaluated_other]
    labels_ko={"Random forest":"랜덤포레스트","Logistic regression":"로지스틱 회귀","DNN/MLP":"DNN/MLP","Other families":"기타 계열","Naive Bayes":"나이브 베이즈","Decision tree":"의사결정나무"}
    barh(ax[0],[labels_ko.get(k,k) if ko else k for k in display_order],avals,f"A. 평가한 알고리즘 계열 (N={N_CORE})" if ko else f"A. Algorithm families evaluated (N={N_CORE})",[BLUE]*8+[GREY],"연구 수(중복 허용)" if ko else "Studies (multiple permitted)",120)  # prompt 106: denominator from data

    tm=Counter(x["algorithm_development"]["hyperparameter_tuning_method"] for x in cls_a)
    search=sum(tm[k] for k in ("RANDOM_SEARCH","BAYESIAN_OR_OTHER_OPTIMISATION","GRID_SEARCH","OTHER_REPORTED"))
    no_tuning=sum(x["algorithm_development"]["tuning_selection_status"]=="NO_TUNING_OR_DEFAULT_MODEL" for x in cls_a)
    manual=sum(x["algorithm_development"]["hyperparameter_tuning_method"]=="MANUAL_OR_DEFAULT" and x["algorithm_development"]["tuning_selection_status"]!="NO_TUNING_OR_DEFAULT_MODEL" for x in cls_a)
    missing=len(cls_a)-search-no_tuning-manual
    labs=(['체계적 탐색\n또는 최적화','수동 튜닝','기본값 또는\n튜닝 없음','정보 불충분'] if ko else ['Systematic search\nor optimisation','Manual tuning','Default or\nno tuning','Insufficient reporting'])
    barh(ax[1],labs,[search,manual,no_tuning,missing],f"B. 하이퍼파라미터 튜닝 방법 (N={N_CORE})" if ko else f"B. Hyperparameter-tuning methods (N={N_CORE})",[GREEN,BLUE,'#CBD5E1',GREY],"연구 수" if ko else "Studies",110)  # prompt 106: denominator from data

    ts=Counter(x["algorithm_development"]["tuning_selection_status"] for x in cls_a)
    keys=["TUNING_REPORTED_SEPARATED","NO_TUNING_OR_DEFAULT_MODEL","TUNING_REPORTED_SEPARATION_NOT_DEMONSTRATED","TUNING_REPORTED_EVALUATION_DATA_INVOLVED","TUNING_NOT_REPORTED"]
    labs=(['명확히 분리','튜닝 없음/\n기본값','분리 근거\n부족','평가자료\n관여','정보 불충분'] if ko else ['Clearly separated','No tuning/\ndefault','Separation not\ndemonstrated','Evaluation data\ninvolved','Insufficient reporting'])
    barh(ax[2],labs,[ts[k] for k in keys],f"C. 튜닝과 최종 평가의\n분리 (N={N_CORE})" if ko else f"C. Separation of tuning\nfrom final evaluation (N={N_CORE})",[GREEN,'#CBD5E1',ORANGE,RED,GREY],"연구 수" if ko else "Studies",65)  # prompt 106: denominator from data

    selected=Counter(); selected_studies=0; single_model=0; selected_other=0
    for d in CLS:
        selections=[x for x in d.get("best_model_selections",[]) if x.get("author_designated")]
        if not selections: continue
        selected_studies += 1
        model_index={x["model_id"]:x.get("label","") for x in d.get("units",{}).get("models",[])}
        families={model_family(model_index[mid]) for x in selections for mid in x.get("selected_model_ids",[]) if mid in model_index}
        selected.update(families)
        selected_other += bool(families-set(fixed_order))
        single_model += len(model_index)==1
    selected_order=["XGBoost","DNN/MLP","Random forest","Logistic regression","SVM","LightGBM","Decision tree","Naive Bayes"]
    selected_display=selected_order+["Other families","No designation recoverable"]
    no_designation=len(CLS)-selected_studies
    dvals=[selected[k] for k in selected_order]+[selected_other,no_designation]
    dcolors=[PURPLE]*8+[GREY,"#CBD5E1"]
    display_labels=[labels_ko.get(k,k) if ko else k for k in selected_display]
    if ko: display_labels[-1]="저자 지정 복원 불가"
    barh(ax[3],display_labels,dvals,f"D. 저자 지정 최종모형 (N={N_CORE})" if ko else f"D. Author-designated final models (N={N_CORE})",dcolors,"연구 수(계열 중복 허용)" if ko else "Studies (families may overlap)",48)  # prompt 106: denominator from data
    ax[3].axhline(len(display_labels)-1.5,color='#9CA3AF',linewidth=.8)
    if not ko:
        export={"schema":"author_designated_model_family_study_level_v1","population":"165 health-focused classification studies","aggregation":"Each family counted at most once per study; multiple families permitted for ties or multiple outcomes/subgroups.","studies_with_author_designated_selection":selected_studies,"single_model_studies":single_model,"designation_not_recoverable":len(CLS)-selected_studies,"family_counts":dict(selected)}
        with open(os.path.join(PROJ,"results/derived/author_designated_model_family_audit.json"),"w") as f: json.dump(export,f,indent=2,ensure_ascii=False)
    fig.tight_layout(h_pad=2.8,w_pad=3.0); save(fig,"fig8_model_development_ko" if ko else "fig8_model_development")


def figure9_evaluation(lang="en"):
    style(lang); ko=lang=="ko"; c=classification_summary(CLS); fig,ax=plt.subplots(2,2,figsize=(12.2,10.8)); ax=ax.ravel()
    vc=c["validation"]
    labs=(['단일 학습–평가 분할','교차검증','Bootstrap','겉보기 평가','평가 상태 불명확\n(없음/미보고 미분리)'] if ko else ['Single train–test\nsplit','Cross-validation','Bootstrap','Apparent evaluation','Evaluation status\nunclear'])
    vals=[vc["SPLIT"],vc["CV"],vc["BOOT"],vc["APPARENT"],vc["NONE_NR"]]
    barh(ax[0],labs,vals,f"A. 내부 평가방법 (N={len(CLS)})" if ko else f"A. Internal evaluation\nmethods (N={len(CLS)})",[BLUE]*4+[GREY],"연구 수(중복 허용)" if ko else "Studies",max(155,1.15*max(vals)))  # prompt 106: N and axis limits from data

    both=sum(has(d,"VAL02",{"TEMPORAL"}) and has(d,"VAL02",{"EXTERNAL"}) for d in CLS)
    temporal_only=vc["TEMPORAL"]-both; external_only=vc["EXTERNAL"]-both
    neither=len(CLS)-temporal_only-external_only-both
    segments=[neither,temporal_only,external_only,both]
    labels=(['없음','이후 시기만','외부자료만','둘 다'] if ko else ['Neither','Later period only','External dataset\nonly','Both'])
    barh(ax[1],labels,segments,f"B. 개발자료 밖 평가 (N={len(CLS)})" if ko else f"B. Beyond development\ndata (N={len(CLS)})",[GREY,GREEN,BLUE,PURPLE],"연구 수" if ko else "Studies",max(160,1.15*max(segments)))  # prompt 106: N and axis limits from data
    beyond=both+external_only+temporal_only
    ax[1].text(.98,-.28,(f"개발자료 밖 평가: {beyond}/{len(CLS)}" if ko else f"Beyond development: {beyond}/{len(CLS)}"),transform=ax[1].transAxes,ha='right',va='top',fontsize=8.2,weight='bold',color='#374151',bbox={'facecolor':'white','edgecolor':'none','alpha':.88,'pad':1.5})  # prompt 106: N and axis limits from data

    report=reporting_summary(CLS)
    counts={k:len(v) for k,v in report['members'].items()}
    original=counts['original_prevalence']; cutoff=counts['threshold_reported']
    evaluation_n=counts['sample_size']; independent=counts['threshold_independent']
    applicable=len(report['denominators']['threshold_independent'])
    if not ko:
        with open(os.path.join(PROJ,'results/derived/study_reporting_summary.json'),'w') as handle:
            json.dump(report,handle,indent=2)
    clabs=(['표본 수\n보고','클래스 분포\n확인 가능','원래 유병률\n유지 보고','판정기준\n상태','독립적 선택\n(판정기준 보고 연구)'] if ko else ['Sample size\nreported','Class distribution\nidentifiable','Original prevalence\nretained','Decision-rule\nstatus','Independent selection\n(rule-reporting studies)'])
    numer=[evaluation_n,counts["class_distribution"],original]; denom=[len(CLS)]*3
    pct=[100*n/d for n,d in zip(numer,denom)]; y=np.array([0,1,2,3.7,5.0])
    ax[2].barh(y[:3],pct,color=[BLUE]*3,height=.62)
    for yi,n,d,p in zip(y[:3],numer,denom,pct): ax[2].text(p+1,yi,f"{n}/{d}",va='center',fontsize=7.5)
    decision_parts=[report["decision_states"].get(k,0) for k in ("Y","NR","UNCLEAR","NA")]
    left=0
    part_labels=(['보고','미보고','불명확','비해당'] if ko else ['Reported','Not reported','Unclear','Not applicable'])
    for value,label,color in zip(decision_parts,part_labels,[ORANGE,GREY,PURPLE,'#CBD5E1']):
        if not value: continue
        width=100*value/len(CLS)
        ax[2].barh(y[3],width,left=left,color=color,height=.62)
        ax[2].text(left+width/2,y[3],str(value),ha='center',va='center',fontsize=7.5,color='#374151' if color=='#CBD5E1' else 'white')
        left+=width
    independent_pct=100*independent/applicable
    ax[2].barh(y[4],independent_pct,color=GREEN,height=.62)
    ax[2].text(independent_pct+1,y[4],f"{independent}/{applicable}",va='center',fontsize=7.5)
    ax[2].set_yticks(y); ax[2].set_yticklabels(clabs,fontsize=8,ha='right',linespacing=.95); ax[2].invert_yaxis(); ax[2].set_xlim(0,125); ax[2].set_xticks([0,50,100]); ax[2].set_xlabel('%')
    ax[2].set_title(f"C. 하나 이상 평가단위의\n보고 상태 (N={len(CLS)})" if ko else f"C. Reporting in at least one\nevaluated unit (N={len(CLS)})",loc='left',weight='bold',fontsize=9.2); ax[2].grid(axis='x',color='#E5E7EB',linewidth=.6); ax[2].set_axisbelow(True)
    ax[2].axhline(2.8,color='#9CA3AF',linewidth=.8)

    q=c["metrics"]; mr=c["metric_reporting"]
    calibration=sum(any(has(d,k,{"R"}) for k in ("MET_CALSLOPE_R","MET_CALINT_R","MET_CALPLOT_R")) for d in CLS)
    labs=['AUROC','AUPRC','Calibration','Brier score','Decision-curve\nanalysis','Confidence\ninterval','Paired model\ncomparison']
    vals=[q["AUROC"],q["AUPRC"],calibration,q["BRIER"],q["DCA"],mr["MET_CI"],mr["MET_PAIR"]]
    colors=[BLUE,BLUE,GREEN,GREEN,ORANGE,PURPLE,PURPLE]
    ypos=np.array([0,1,2.65,3.65,5.0,6.8,8.5])
    ax[3].barh(ypos,vals,color=colors,height=.68)
    ax[3].set_yticks(ypos); ax[3].set_yticklabels(labs,fontsize=8); ax[3].invert_yaxis(); ax[3].set_xlim(0,max(170,1.15*max(vals)))  # prompt 106: N and axis limits from data
    ax[3].set_xlabel("연구 수(중복 허용)" if ko else "Studies")
    ax[3].set_title(f"D. 보고된\n성능지표 (N={len(CLS)})" if ko else f"D. Performance measures\nreported (N={len(CLS)})",loc='left',weight='bold',fontsize=9.4)  # prompt 106: N and axis limits from data
    for yi,v in zip(ypos,vals): ax[3].text(v+1.5,yi,str(v),va='center',fontsize=7.5)
    for cut in (1.75,5.5): ax[3].axhline(cut,color='#D1D5DB',lw=.7)
    group_names=(['판별·클래스 민감 지표','보정·임상적 유용성','불확실성·비교'] if ko else ['Discrimination/class-sensitive','Calibration/clinical utility','Uncertainty/comparison'])

    fig.subplots_adjust(top=.90,bottom=.08,hspace=.68)
    for axis,left,right in ((ax[0],.25,.48),(ax[1],.77,.98),(ax[2],.27,.48),(ax[3],.77,.98)):
        pos=axis.get_position(); axis.set_position([left,pos.y0,right-left,pos.height])
    for axis in ax: axis.set_xticks([0,50,100] if axis is ax[2] else [0,50,100,150])
    save(fig,"fig9_validation_evaluation_ko" if ko else "fig9_validation_evaluation")


def _figure10_reproducibility_full_audit(lang="en"):
    style(lang); ko=lang=="ko"; c=CONS
    # Designed at approximately final journal width so nominal point sizes remain legible.
    # A wider canvas preserves the vertical room required by the two-line reporting
    # labels while keeping the full-width manuscript rendering within one text page.
    fig=plt.figure(figsize=(8.2,10.15)); outer=fig.add_gridspec(3,1,height_ratios=[6.7,1.5,1.5],hspace=.76)
    row2=outer[1].subgridspec(1,2,width_ratios=[.35,.65],wspace=1.12)
    row3=outer[2].subgridspec(1,2,wspace=1.08)
    ax_a=fig.add_subplot(outer[0]); ax_b=fig.add_subplot(row2[0]); ax_d=fig.add_subplot(row2[1]); ax_c1=fig.add_subplot(row3[0]); ax_c2=fig.add_subplot(row3[1])
    rep_labels_en=["Title: study type","Abstract summary","Objective, use, population","Data source, design, and dates","Eligibility and selection","Outcome definition, timing,\nand source","Predictor definition and timing","Sample and event/class counts","Sample-size rationale","Missing data","Preprocessing, selection,\nand model development","Hyperparameters and tuning","Internal validation/resampling","Evaluation data, metrics,\nand threshold","Participant flow/characteristics","Performance estimates and uncertainty","Reusable final model","Limitations and generalisability","Registration, data, and code"]
    rep_labels_ko=["제목의 연구유형 식별","초록 요약","목적·활용·대상 모집단","자료원·설계·기간","적격기준·선정과정","결과 정의·시점·\n자료원","설명변수 정의·측정시점","분석표본·사건/클래스 수","표본크기 근거","결측자료","전처리·선택·\n모델개발","하이퍼파라미터·튜닝","내부검증·재표집","평가자료·지표·\n판정기준","참가자 흐름·특성","성능 추정값·불확실성","재사용 가능한 최종모형","제한점·일반화 가능성","등록·자료·코드 공개"]
    rep=[]; rep_den=[]
    for i in range(1,20):
        counts=Counter(v for d in PRED for v in flat_values(d,f"REP{i:02d}"))
        rep.append([counts.get("R",0),counts.get("P",0),counts.get("NR",0)+counts.get("UNC",0)])
        rep_den.append(sum(v for key,v in counts.items() if key!="NA"))
    rep=np.array(rep); rep_den=np.array(rep_den); assert np.all(rep.sum(axis=1)==rep_den)
    rpct=100*rep/rep.sum(axis=1)[:,None]; left=np.zeros(19)
    active_labels=rep_labels_ko if ko else rep_labels_en
    row_heights=np.array([1.80 if "\n" in label else 1.0 for label in active_labels])
    ypos=np.cumsum(np.r_[0,(row_heights[:-1]+row_heights[1:])/2])
    ypos[3:]+=.55; ypos[10:]+=.55; ypos[13:]+=.55
    partial_color="#E6A700"; unreported_color="#7A8494"
    for j,(name,color) in enumerate(zip((["완전","부분","명세 불충분·미보고·불명확"] if ko else ["Complete","Partial","Insufficient / NR / unclear"]),[GREEN,partial_color,unreported_color])):
        ax_a.barh(ypos,rpct[:,j],left=left,color=color,height=.72,label=name)
        for i,(n,p) in enumerate(zip(rep[:,j],rpct[:,j])):
            if p>=8: ax_a.text(left[i]+p/2,ypos[i],f"{p:.0f}%",ha='center',va='center',fontsize=7.5,color='#111827' if color==partial_color else 'white')
        left+=rpct[:,j]
    ax_a.set_yticks(ypos); ax_a.set_yticklabels(active_labels,fontsize=9.0,ha='right',linespacing=.82); ax_a.invert_yaxis(); ax_a.set_xlim(0,100); ax_a.set_xlabel('Applicable prediction studies (%)' if not ko else '적용 가능한 예측연구(%)',labelpad=3,fontsize=8.5)
    for cut in (ypos[2]+.83,ypos[9]+.83,ypos[12]+.83): ax_a.axhline(cut,color='#CBD5E1',lw=.8)
    ax_a.set_title("A. 19개 사전지정 TRIPOD+AI 유래 보고항목" if ko else "A. 19 prespecified TRIPOD+AI-derived reporting elements",loc='left',weight='bold',fontsize=10.5)
    ax_a.legend(frameon=False,fontsize=7.8,ncol=3,loc='upper center',bbox_to_anchor=(.5,-.095))

    labs=(['통합기수\n가중치 전략','모델 적합에\n조사가중치','성능평가에\n조사가중치','불확실성에\n층·PSU 반영'] if ko else ['Combined-cycle\nweights','Survey weights\nin model fitting','Survey weights in\nperformance evaluation','Strata/PSUs in\nuncertainty estimation'])
    vals=[c["survey"][k].get("USED",0) for k in ("SUR11","SUR06","SUR07","SUR10")]
    barh(ax_b,labs,vals,"B. KNHANES 조사설계\n요소 사용" if ko else "B. Use of KNHANES\nsurvey-design features",[GREEN]*4,"전체 연구 수(n=220)" if ko else "All studies (n=220)",22)
    for label,value in zip(ax_b.texts,vals): label.set_text(f"{value}/220")
    for label in ax_b.get_yticklabels(): label.set_fontsize(7.5); label.set_linespacing(.82)
    ax_b.set_xticks(np.arange(0,21,5))

    domain_keys=["PD_D1","PD_D2","PD_D3","PD_D4","PD_OVERALL"]
    eval_keys=["PE_D1","PE_D2","PE_D3","PE_D4","PE_OVERALL"]
    domain_labels=(['참가자·자료원','설명변수','결과변수','분석','전체'] if ko else ['Participants/data sources','Predictors','Outcome','Analysis','Overall'])
    def appraisal_block(axis,keys,states,title,legend_labels):
        mat=np.array([[Counter(v for d in PRED for v in flat_values(d,key)).get(state,0) for state in states] for key in keys])
        den=mat.sum(axis=1); pct=100*mat/den[:,None]; left=np.zeros(len(keys))
        for j,(label,color) in enumerate(zip(legend_labels,[GREEN,"#B3A25A",RED])):
            axis.barh(np.arange(len(keys)),pct[:,j],left=left,color=color,height=.66,label=label)
            for i,(n,p) in enumerate(zip(mat[:,j],pct[:,j])):
                if p>=8: axis.text(left[i]+p/2,i,f"{p:.0f}%",ha='center',va='center',fontsize=7.5,color='white' if color!="#B3A25A" else '#111827')
            left+=pct[:,j]
        axis.set_yticks(range(5)); axis.set_yticklabels(domain_labels,fontsize=8); axis.invert_yaxis(); axis.set_xlim(0,100); axis.set_xlabel('%'); axis.set_title(title,loc='left',weight='bold',fontsize=9)
        return mat,den
    appraisal_legend=['양호','불명확','불리'] if ko else ['Favourable','Unclear','Unfavourable']
    pd_mat,pd_den=appraisal_block(ax_c1,domain_keys,["HIGH","UNC","LOW"],"D1. 모델개발 품질\n(308단위)" if ko else "D1. Model-development quality\n(308 units)",appraisal_legend)
    pe_mat,pe_den=appraisal_block(ax_c2,eval_keys,["LOW","UNC","HIGH"],"D2. 평가 비뚤림 위험\n(401단위)" if ko else "D2. Evaluation risk of bias\n(401 units)",appraisal_legend)
    claim_labels=(['변수 해석\n안정성 평가','모집단 연관성\n조사설계 반영','선별·개인 활용\n검증+보정+판정기준','감시·정책\n조사설계 근거'] if ko else
                  ['Variable interpretation\nStability assessed','Population association\nSurvey-aware analysis','Screening or personal use\nValidation + calibration + threshold','Surveillance or policy\nSurvey-design support'])
    claim_totals=[129,21,49,49]; matched=[25,4,5,8]
    y=np.arange(4)
    for i,(total,good) in enumerate(zip(claim_totals,matched)):
        present=100*good/total; absent=100-present
        ax_d.barh(i,present,color=GREEN,height=.62,label='대응 근거 있음' if ko and i==0 else ('Support present' if i==0 else None))
        ax_d.barh(i,absent,left=present,color='#D1D5DB',height=.62,label='대응 근거 없음' if ko and i==0 else ('Support absent' if i==0 else None))
        ax_d.text(present+1.4,i,f"{good}/{total} ({present:.1f}%)",ha='left',va='center',fontsize=7.7,color='#065F46',weight='bold')
    ax_d.set_yticks(y); ax_d.set_yticklabels(claim_labels,fontsize=7.8,ha='right',linespacing=.95); ax_d.invert_yaxis(); ax_d.set_xlim(0,100)
    for label in ax_d.get_yticklabels(): label.set_linespacing(.82)
    ax_d.set_title('C. 의도한 주장에\n부합하는 근거' if ko else 'C. Evidence matched to\nthe intended claim',loc='left',weight='bold',fontsize=9)
    ax_d.legend(frameon=False,fontsize=7.5,loc='upper center',bbox_to_anchor=(.5,-.20),ncol=2)
    handles,labels=ax_c1.get_legend_handles_labels()
    fig.legend(handles,labels,frameon=False,fontsize=7.5,ncol=3,loc='lower center',bbox_to_anchor=(.5,.002))
    if not ko:
        export={"schema":"figure11_reporting_and_probast_domain_audit_v1","reporting":{"population":"prediction studies","items":[{"item_id":f"REP{i+1:02d}","label":rep_labels_en[i],"complete":int(rep[i,0]),"partial":int(rep[i,1]),"not_reported_or_unclear":int(rep[i,2]),"applicable_denominator":int(rep_den[i])} for i in range(19)]},"probast_ai":{"development":{"unit_n":int(pd_den[0]),"state_order":["HIGH_QUALITY","UNCLEAR","LOW_QUALITY"],"rows":{label:{"high_quality":int(row[0]),"unclear":int(row[1]),"low_quality":int(row[2])} for label,row in zip(domain_labels,pd_mat)}},"evaluation":{"unit_n":int(pe_den[0]),"state_order":["LOW_RISK","UNCLEAR","HIGH_RISK"],"rows":{label:{"low_risk":int(row[0]),"unclear":int(row[1]),"high_risk":int(row[2])} for label,row in zip(domain_labels,pe_mat)}}}}
        with open(os.path.join(PROJ,"results/derived/figure11_reporting_probast_domain_audit.json"),"w") as f: json.dump(export,f,indent=2,ensure_ascii=False)
    save(fig,"fig11_methodological_appraisal_ko" if ko else "fig11_methodological_appraisal")


def figure10_reproducibility(lang="en"):
    """Core-cohort reporting, survey-design, claim-evidence, and appraisal summary."""
    style(lang); ko=lang=="ko"; core_n=len(CLS)
    # Keep the total page height publication-safe while reallocating vertical
    # space from panel A (whose labels are now smaller) to panels B--D.
    fig=plt.figure(figsize=(9.2,11.65))
    outer=fig.add_gridspec(3,1,height_ratios=[6.8,3.4,2.8],hspace=.40)
    middle=outer[1].subgridspec(1,2,width_ratios=[1,1],wspace=.82)
    ax_a=fig.add_subplot(outer[0]); ax_b=fig.add_subplot(middle[0]); ax_c=fig.add_subplot(middle[1]); ax_d=fig.add_subplot(outer[2])

    all_labels_en=["Title: study type","Abstract summary","Objective, use, population","Data source, design, and dates","Eligibility and selection","Outcome definition, timing, and source","Predictor definition and timing","Sample and event/class counts","Sample-size rationale","Missing-data handling","Preprocessing, selection, and model development","Hyperparameters and tuning","Internal validation/resampling","Evaluation data, metrics, and threshold","Participant flow/characteristics","Performance estimates and uncertainty","Reusable final-model specification","Limitations and generalisability","Registration, data, and code"]
    rep=[]
    for i in range(1,20):
        counts=Counter(v for d in CLS for v in flat_values(d,f"REP{i:02d}"))
        row=[counts.get("R",0),counts.get("P",0),counts.get("NR",0)+counts.get("UNC",0)]
        assert sum(row)==core_n
        rep.append(row)
    rep=np.array(rep); selected_idx=[5,6,7,9,11,12,16,18]
    labels_en=["Outcome definition,\ntiming, and source (REP06)","Predictor definition\nand timing (REP07)","Sample and event/\nclass counts","Missing-data\nhandling","Hyperparameters\nand tuning","Internal validation/\nresampling","Final-model\nspecification","Registration and\ndata/code availability\n(REP19)"]
    labels_ko=["결과 정의·시점·자료원\n(REP06)","설명변수 정의·시점\n(REP07)","표본·사건/클래스 수","결측자료 처리","하이퍼파라미터·튜닝","내부검증·재표집","최종모형 명세","등록·자료/코드 공개\n(REP19)"]
    selected=rep[selected_idx]; pct=100*selected/core_n; left=np.zeros(len(selected)); y=np.arange(len(selected))
    states=["완전","부분","명세 불충분·미보고·불명확"] if ko else ["Complete","Partial","Insufficient / NR / unclear"]
    for j,(label,color) in enumerate(zip(states,[GREEN,"#E6AB02",GREY])):
        ax_a.barh(y,pct[:,j],left=left,color=color,height=.66,label=label)
        for i,p in enumerate(pct[:,j]):
            if p>=9: ax_a.text(left[i]+p/2,i,f"{selected[i,j]} ({p:.0f}%)",ha='center',va='center',fontsize=7.5,color='white' if color in (GREEN,GREY) else '#111827')
        left+=pct[:,j]
    # Reader-facing labels omit internal item codes; the codes remain in S2/S7.
    labels_en[0]="Outcome definition,\ntiming and source"
    labels_en[1]="Predictor definition\nand timing"
    labels_en[-1]="Registration; data/code\navailability"
    labels_ko=[x.split("\n(REP")[0] for x in labels_ko]
    ax_a.set_yticks(y); ax_a.set_yticklabels(labels_ko if ko else labels_en,fontsize=6.9,linespacing=.85,va='center'); ax_a.set_ylim(7.35,-.35); ax_a.set_xlim(0,100); ax_a.set_xlabel('')
    ax_a.set_title(("A. 선택된 TRIPOD+AI 유래 보고 지표" if ko else "A. Selected TRIPOD+AI-derived reporting indicators")+f" (N={core_n} studies)",loc='left',weight='bold',fontsize=9.5)
    ax_a.legend(frameon=False,ncol=3,loc='upper center',bbox_to_anchor=(.5,-.065),fontsize=7.2)

    survey_labels=(['통합기수\n가중치 전략','모델 적합\n조사가중치','성능평가\n조사가중치','불확실성\n층·PSU'] if ko else ['Combined-cycle\nweights','Weights in\nfitting','Weights in\nevaluation','Strata/PSUs in\nvariance'])
    survey_keys=("SUR11","SUR06","SUR07","SUR10")
    survey_states=("USED","NOT_USED","NR","NA","UNC")
    survey_matrix=np.array([[Counter(flat_values(d,key)[0] if flat_values(d,key) else "NR" for d in CLS).get(state,0) for state in survey_states] for key in survey_keys])
    assert np.all(survey_matrix.sum(axis=1)==core_n)
    survey_vals=survey_matrix[:,0].tolist(); survey_pct=100*survey_matrix/core_n
    # Small "used" counts are stated in the row label rather than squeezed into narrow segments.
    survey_labels=[f"{lab} ({'사용' if ko else 'used'} {n})" for lab,n in zip(survey_labels,survey_vals)]
    sy=np.arange(len(survey_vals)); left=np.zeros(len(survey_vals))
    state_labels=(['사용','미사용','미보고','비해당','불명확'] if ko else ['Used','Not used','Not reported','Not applicable','Unclear'])
    state_colors=[GREEN,SKY,GREY,'#CBD5E1',ORANGE]
    for j,(label,color) in enumerate(zip(state_labels,state_colors)):
        ax_b.barh(sy,survey_pct[:,j],left=left,color=color,height=.62,label=label)
        for i,(count,width) in enumerate(zip(survey_matrix[:,j],survey_pct[:,j])):
            # Tiny adjacent status segments (for example 7 and 4 studies) are
            # distinguishable by colour but too narrow for collision-free labels.
            if width>=12.0:
                ax_b.text(left[i]+width/2,i,str(count),ha='center',va='center',fontsize=7.0,
                          color='white' if color in (GREEN,GREY) else '#374151')
        left+=survey_pct[:,j]
    ax_b.set_yticks(sy); ax_b.set_yticklabels(survey_labels,fontsize=7.4,linespacing=1.15); ax_b.set_ylim(3.5,-.5); ax_b.set_xlim(0,100)
    ax_b.set_xticks([0,25,50,75,100]); ax_b.set_xlabel('핵심 코호트 중 %' if ko else '% of core cohort',labelpad=3)
    ax_b.grid(axis='x',color='#E5E7EB',linewidth=.6); ax_b.set_axisbelow(True)
    ax_b.set_title(("B. 복합표본 처리" if ko else "B. Survey design")+f" (N={core_n} studies)",loc='left',weight='bold',fontsize=9.5)
    ax_b.set_xlabel('')
    ax_b.legend(frameon=False,fontsize=6.8,ncol=3,loc='upper center',bbox_to_anchor=(.5,-.12),handlelength=1.0,columnspacing=.7)

    def survey_supported(d):
        return has(d,"SUR04",{"USED"}) and any(has(d,k,{"USED"}) for k in ("SUR08","SUR09","SUR10"))
    def calibrated(d): return any(has(d,k,{"R"}) for k in ("MET_CALSLOPE_R","MET_CALINT_R","MET_CALPLOT_R"))
    def independently_validated(d): return has(d,"VAL02",{"EXTERNAL","TEMPORAL"})
    importance=[d for d in CLS if has(d,"VI01",{"USED"})]
    association=[d for d in CLS if "POPULATION_ASSOCIATION_ANALYSIS" in PURPOSE_BY_ID[d["study_id"]]["health_analysis_purpose_components"]]
    application_codes={"SCREENING","DIAGNOSTIC_SUPPORT","PERSONALISED_MANAGEMENT","RISK_GROUP_IDENTIFICATION"}
    application=[d for d in CLS if set(PURPOSE_BY_ID[d["study_id"]]["proposed_use"]) & application_codes]
    policy=[d for d in CLS if "POPULATION_SURVEILLANCE_OR_POLICY" in PURPOSE_BY_ID[d["study_id"]]["proposed_use"]]
    claim_rows=[importance,association,application,policy]
    totals=[len(x) for x in claim_rows]
    matched=[sum(has(d,"VI16",{"USED"}) for d in importance),
             sum(PURPOSE_V13_BY_ID[d["study_id"]]["association_audit"]["population_association_was_survey_aware"]=="Y" for d in association),
             sum(independently_validated(d) and calibrated(d) and threshold_reported(d) for d in application),
             sum(survey_supported(d) for d in policy)]
    claim_labels=(['변수중요도\n안정성 보고','연관성: 동일 분석\n조사설계 반영','개인 활용: 연구 내 공존\n3요소·동일 분석 미확인','감시·정책\n조사설계 보고'] if ko else ['Importance\nstability','Association: linked\nsurvey-aware','Individual use:\n3 co-reported checks','Policy: survey\ndesign reported'])
    cy=np.arange(4)
    for i,(total,good) in enumerate(zip(totals,matched)):
        ax_c.hlines(i,good,total,color='#94A3B8',linewidth=1.6,zorder=1)
        ax_c.scatter(total,i,s=48,facecolor='white',edgecolor=BLUE,linewidth=1.6,zorder=3)
        ax_c.scatter(good,i,s=48,color=GREEN,zorder=4)
        # Put every ratio above its connector with the same vertical offset.
        # No label sits on a line or against either endpoint marker.
        # Keep short connectors' labels clear of the y axis line.
        ax_c.text(max((good+total)/2,20),i-.30,f"{good}/{total}",ha='center',va='bottom',fontsize=7.8,color='#065F46',weight='bold')
    ax_c.set_yticks(cy); ax_c.set_yticklabels(claim_labels,fontsize=7.4,linespacing=1.15); ax_c.set_xlim(0,175); ax_c.set_xlabel("연구 수" if ko else "Studies")  # prompt 106: 154 eligible rankings exceed the old 150 limit
    ax_c.grid(axis='x',color='#E5E7EB',linewidth=.6); ax_c.set_axisbelow(True)
    ax_c.set_title(("C. 보고된 검토 요소" if ko else "C. Reported checks")+f" (N={core_n} studies)",loc='left',weight='bold',fontsize=9.5)
    # Identical limits AND rectangles align all four row centres with panel B.
    ax_c.set_ylim(3.5,-.5)
    legend_handles=[
        Line2D([0],[0],marker='o',linestyle='none',markerfacecolor='white',markeredgecolor=BLUE,
               markeredgewidth=1.4,markersize=6,label='해당 연구' if ko else 'eligible'),
        Line2D([0],[0],marker='o',linestyle='none',markerfacecolor=GREEN,markeredgecolor=GREEN,
               markersize=6,label='요소 보고' if ko else 'criterion reported'),
    ]
    ax_c.legend(handles=legend_handles,loc='upper center',bbox_to_anchor=(.5,-.30),ncol=2,
                frameon=False,fontsize=7.0,handlelength=.8,handletextpad=.45,columnspacing=.8)

    dev=Counter(v for d in CLS for v in flat_values(d,"PD_OVERALL") if v!="NA")
    eva=Counter(v for d in CLS for v in flat_values(d,"PE_OVERALL") if v!="NA")
    overall=np.array([[dev.get("HIGH",0),dev.get("UNC",0),dev.get("LOW",0)],[eva.get("LOW",0),eva.get("UNC",0),eva.get("HIGH",0)]])
    unit_den=overall.sum(axis=1); opct=100*overall/unit_den[:,None]; left=np.zeros(2); oy=np.arange(2)
    row_states=([['높은 품질','불명확','낮은 품질'],['낮은 위험','불명확','높은 위험']] if ko else
                [['High quality','Unclear','Low quality'],['Low risk','Unclear','High risk']])
    for j,color in enumerate([GREEN,"#B3A25A",RED]):
        ax_d.barh(oy,opct[:,j],left=left,color=color,height=.86)
        for i,p in enumerate(opct[:,j]):
            label=f"{row_states[i][j]}\n{overall[i,j]}/{unit_den[i]} ({p:.0f}%)"
            if p>=12:
                ax_d.text(left[i]+p/2,i,label,ha='center',va='center',fontsize=7.5,
                          color='white' if color in (GREEN,RED) else '#111827',linespacing=.95)
        left+=opct[:,j]
    # Small segments use separated callouts so the actual direction-specific labels
    # remain legible and cannot be mistaken for a generic favourable/unfavourable scale.
    # prompt 106: callout counts and anchor points from the data (were fixed at 14, 9 and 2 for the 165-study release)
    dh, du, el, eu = int(overall[0,0]), int(overall[0,1]), int(overall[1,0]), int(overall[1,1])
    xh, xu = opct[0,0]/2, opct[0,0]+opct[0,1]/2
    xl, xeu = opct[1,0]/2, opct[1,0]+opct[1,1]/2
    callouts = ([('높은 품질',dh,xh,15,-.53,GREEN),('불명확',du,xu,45,-.53,'#8A7A35'),
                 ('낮은 위험',el,xl,18,1.53,GREEN)] if ko else
                [('High quality',dh,xh,15,-.53,GREEN),('Unclear',du,xu,65,-.53,'#8A7A35'),
                 ('Low risk',el,xl,18,1.53,GREEN)])
    if eu:
        callouts.append(('불명확' if ko else 'Unclear',eu,xeu,50,1.53,'#8A7A35'))
    for label,n,xpoint,xtext,ytext,color in callouts:
        row = 0 if ytext < 0 else 1
        pct_value = 100*n/unit_den[row]
        ax_d.annotate(f"{label} {n} ({pct_value:.1f}%)",xy=(xpoint,row),xytext=(xtext,ytext),
                      fontsize=7.5,color=color,ha='center',va='bottom' if row == 0 else 'top',
                      arrowprops={'arrowstyle':'-','color':color,'lw':.7})
    dlabels=([f'개발 모형 (n={unit_den[0]})\n방법론적 품질',f'평가 (n={unit_den[1]})\n비뚤림 위험'] if ko else [f'Development models (n={unit_den[0]})\nMethodological quality',f'Evaluations (n={unit_den[1]})\nRisk of bias'])
    ax_d.set_yticks(oy); ax_d.set_yticklabels(dlabels,fontsize=7.5,linespacing=1.15); ax_d.set_ylim(1.95,-.68); ax_d.set_xlim(0,100); ax_d.set_xlabel('%')
    ax_d.set_title(("D. 모델 수준 PROBAST+AI 평가" if ko else "D. PROBAST+AI model-level appraisal") +
                   f" (N={core_n} studies)",loc='left',weight='bold',fontsize=9.5)

    # Figure 11 is exported on the complete canvas so that panel headings use
    # manuscript-page anchors. Reserve each cell's leading area for its y labels
    # and place only the plotting rectangle farther right; this prevents the
    # fixed canvas from clipping long reporting and appraisal labels.
    # English REP06 is the widest label; the extra four percentage points keep
    # its second line inside the exported canvas at journal-scale rendering.
    # Leave a true top-page gutter for the publication-layer panel heading;
    # its font bounding box must remain inside the exported vector canvas.
    fig.subplots_adjust(top=.950,bottom=.065)
    panel_a_left = .29 if not ko else .25
    # B's row labels carry the "used n" count; its plot starts at .235 (was .18) so the labels stay on the canvas.
    for axis,left,right in ((ax_a,panel_a_left,.98),(ax_b,.235 if not ko else .20,.44),(ax_c,.70,.98),(ax_d,.36,.98)):
        pos=axis.get_position()
        # Reserve room for B's two-line legend above the D heading.
        axis.set_position([left,pos.y0,right-left,pos.height-(.025 if axis is ax_d else 0)])

    if not ko:
        domain_labels=['Participants/data sources','Predictors','Outcome','Analysis','Overall']
        domain_keys=["PD_D1","PD_D2","PD_D3","PD_D4","PD_OVERALL"]; eval_keys=["PE_D1","PE_D2","PE_D3","PE_D4","PE_OVERALL"]
        pd_mat=np.array([[Counter(v for d in CLS for v in flat_values(d,key)).get(state,0) for state in ("HIGH","UNC","LOW")] for key in domain_keys])
        pe_mat=np.array([[Counter(v for d in CLS for v in flat_values(d,key)).get(state,0) for state in ("LOW","UNC","HIGH")] for key in eval_keys])
        export={"schema":"figure11_core_cohort_reporting_and_probast_audit_v4","core_study_n":core_n,"main_figure_reporting_items":[f"REP{i+1:02d}" for i in selected_idx],"reporting":{"population":"health-focused classification studies","items":[{"item_id":f"REP{i+1:02d}","label":all_labels_en[i],"complete":int(rep[i,0]),"partial":int(rep[i,1]),"not_reported_or_unclear":int(rep[i,2]),"denominator":core_n} for i in range(19)]},"survey_design":dict(zip(survey_keys,survey_vals)),"survey_design_status":{key:dict(zip(survey_states,map(int,row))) for key,row in zip(survey_keys,survey_matrix)},"claim_evidence":{"claim_present":totals,"matched_evidence":matched},"probast_ai":{"development":{"unit_n":int(unit_den[0]),"rows":{label:{"high_quality":int(row[0]),"unclear":int(row[1]),"low_quality":int(row[2])} for label,row in zip(domain_labels,pd_mat)}},"evaluation":{"unit_n":int(unit_den[1]),"rows":{label:{"low_risk":int(row[0]),"unclear":int(row[1]),"high_risk":int(row[2])} for label,row in zip(domain_labels,pe_mat)}}}}
        with open(os.path.join(PROJ,"results/derived/figure11_reporting_probast_domain_audit.json"),"w") as f: json.dump(export,f,indent=2,ensure_ascii=False)
    save(fig,"fig11_methodological_appraisal_ko" if ko else "fig11_methodological_appraisal")


def figure11_practices(lang="en"):
    style(lang); ko=lang=="ko"; periods=["≤2019","2020–2022","2023–2024","2025–2026"]
    period_ticks=["≤2019","2020–22","2023–24","2025–26"]
    colors=[BLUE,ORANGE,GREEN,PURPLE,RED,SKY]
    expanded=json.load(open(os.path.join(PROJ,"results/derived/expanded_model_task_audit.json")))
    exp_by_id={x["study_id"]:x for x in expanded["studies"]}
    method_records=[r for r in PURPOSE_RECORDS if r["study_category"]=="METHOD_RESEARCH"]
    hgroups=[[d for d in CLS if period(int(d["metadata"]["publication_year"]))==p] for p in periods]
    topic_groups=[[d for d in CLS if period(int(d["metadata"]["publication_year"]))==p] for p in periods]
    mgroups=[[r for r in method_records if period(int(r["publication_year"]))==p] for p in periods]
    hden=[len(x) for x in hgroups]; topic_den=[len(x) for x in topic_groups]; mden=[len(x) for x in mgroups]
    fig,axes=plt.subplots(2,2,figsize=(15.2,14.2)); axes=axes.ravel()
    sfig,saxes=plt.subplots(1,2,figsize=(12.4,4.8))

    def period_dot_panel(ax,specs,title,palette=None,direct_labels=True,label_offsets=None,ylim=(0,100)):
        result={}
        palette=palette or colors
        markers=['o','s','^','D','P','X']
        endpoints=[]
        point_labels={j:[] for j in range(4)}
        for i,(en,kr,fn) in enumerate(specs):
            ns=[sum(fn(d) for d in rows) for rows in hgroups]; pct=[100*n/d for n,d in zip(ns,hden)]
            # Preserve the author's requested visual guide across ordered periods.
            # The caption states that these lines are descriptive connectors, not
            # fitted trends; do not remove them in later presentation revisions.
            ax.plot(range(4),pct,color=palette[i],linewidth=1.15,alpha=.72,zorder=2)
            ax.scatter(range(4),pct,marker=markers[i],s=48,color=palette[i],
                       edgecolor='white',linewidth=.55,zorder=3,label=kr if ko else en)
            for j,value in enumerate(pct):
                if direct_labels and j == 3: continue
                point_labels[j].append((value,palette[i]))
            if direct_labels:
                offset=(label_offsets or [0]*len(specs))[i]
                direct_en={
                    "Tuning/evaluation separated":"Tuning/evaluation\nseparated",
                    "Survey weights reported":"Survey weights\nreported",
                    "Candidate predictors specified":"Candidate/final sets\nrecoverable",
                    "Analysis code available":"Analysis code\navailable",
                    "Final model fully specified":"Final model fully\nspecified",
                }
                direct_ko={
                    "Tuning/evaluation separated":"튜닝·평가\n분리",
                    "Survey weights reported":"조사가중치\n보고",
                    "Candidate predictors specified":"후보·최종 집합\n복원 가능",
                    "Analysis code available":"분석 코드\n공개",
                    "Final model fully specified":"최종모형 완전\n명세",
                }
                display=(direct_ko if ko else direct_en).get(en,kr if ko else en)
                import textwrap
                display="\n".join(textwrap.wrap(display.replace("\n", " "), 16 if not ko else 10, break_long_words=False, break_on_hyphens=False))
                endpoints.append((pct[-1],display,palette[i]))
            result[en]={p:{"n":n,"denominator":d,"percent":round(q,1)} for p,n,d,q in zip(periods,ns,hden,pct)}
        # Separate numeric labels for close observations without moving the data.
        for j,points in []:  # intermediate values remain in the temporal source audit / S7
            ordered=sorted(points)
            gap=(ylim[1]-ylim[0])*.055
            last=ylim[0]+gap*.35
            slots=[]
            for value,color in ordered:
                slot=max(value,last);slots.append(slot);last=slot+gap
            if slots and slots[-1]>ylim[1]-gap*.3:
                shift=slots[-1]-(ylim[1]-gap*.3);slots=[x-shift for x in slots]
            for (value,color),slot in zip(ordered,slots):
                ax.annotate(f"{value:.0f}",(j,value),xytext=(j+.12,slot),
                            textcoords='data',ha='left',va='center',fontsize=7.5,color=color,
                            arrowprops={'arrowstyle':'-','color':color,'lw':.5},
                            bbox={'facecolor':'white','edgecolor':'none','alpha':.8,'pad':.25})
        # Allocate a distinct endpoint-label slot for every series; leaders retain
        # the true endpoint. Final-point percentages live in this column only.
        if direct_labels:
            ordered=sorted(endpoints)
            lo,hi=ylim
            slots=np.linspace(lo+.13*(hi-lo),hi-.12*(hi-lo),len(ordered))
            for (value,display,color),slot in zip(ordered,slots):
                ax.plot([3.05,3.38],[value,slot],color=color,lw=.8,alpha=.8)
                ax.text(3.43,slot,f"{display} ({value:.0f}%)",fontsize=9.0,
                        va='center',color=color,linespacing=1.4)
        ax.set_title(title,loc='left',weight='bold',fontsize=9.5,pad=12); ax.set_xticks(range(4)); ax.set_xticklabels(period_ticks,fontsize=8,rotation=90,ha="center")
        ax.set_ylim(ylim[0],ylim[1]); ax.set_xlim(-.12,5.35 if direct_labels else 3.18); ax.axvspan(2.5,3.5,color='#E5E7EB',alpha=.55,zorder=0)
        ax.grid(axis='y',color='#E5E7EB',linewidth=.6); ax.set_axisbelow(True)
        return result

    panel_a=[("Algorithm comparison","알고리즘 비교",lambda d:has(d,"FUN_COMPARE",{"PRESENT"})),
             ("Model-based importance","모형 기반 중요도",lambda d:has(d,"VI01",{"USED"})),
             ("SHAP","SHAP",lambda d:has(d,"VI02",{"SHAP"})),
             ("Stability assessed","안정성 평가",lambda d:has(d,"VI16",{"USED"}))]
    # Panel A shows importance outputs, not the stated variable-interpretation purpose (Methods distinction).
    ares=period_dot_panel(axes[0],panel_a,"A. 중요도와 안정성" if ko else "A. Importance and stability",[BLUE,"#009E73","#007C6C","#CC79A7"],label_offsets=[0,0,0,0],ylim=(-3,103))
    axes[0].set_ylabel('건강분석 분류연구 중 %' if ko else '% of core studies')

    topic_codes=["MENTAL_HEALTH","METABOLIC_ENDOCRINE","CARDIOVASCULAR","MUSCULOSKELETAL","ORAL_HEALTH","OTHER"]
    topic_en=["Mental health","Metabolic/endocrine","Cardiovascular disease","Musculoskeletal health","Oral health","Other topics"]
    topic_ko=["정신건강","대사·내분비","심혈관질환","근골격계 건강","구강건강","기타 주제"]
    topic_mat=np.zeros((4,6),dtype=int)
    for j,rows in enumerate(topic_groups):
        for d in rows:
            t=PURPOSE_V13_BY_ID[d["study_id"]]["health_topic"]["primary_topic_18"]
            idx=topic_codes.index(t) if t in topic_codes[:-1] else 5; topic_mat[j,idx]+=1
    chi,p_asym,df,expected=chi2_contingency(topic_mat,correction=False)
    rng=np.random.default_rng(20260917); sims=random_table.rvs(topic_mat.sum(1),topic_mat.sum(0),size=100000,random_state=rng)
    sim_chi=((sims-expected)**2/expected).sum(axis=(1,2)); p_mc=float((1+np.sum(sim_chi>=chi-1e-12))/100001)
    cramer_v=float(np.sqrt(chi/(topic_mat.sum()*min(topic_mat.shape[0]-1,topic_mat.shape[1]-1))))

    def family(d,names): return bool(set(exp_by_id[d["study_id"]]["algorithm_development"]["algorithm_family"]) & set(names))
    panel_c=[("Tree-based boosting","트리 기반 부스팅",lambda d:family(d,{"XGBoost","LightGBM","Gradient boosting"})),
             ("Random forest","랜덤포레스트",lambda d:family(d,{"Random forest"})),
             ("Logistic regression","로지스틱 회귀",lambda d:family(d,{"Logistic regression"})),
             ("SVM","SVM",lambda d:family(d,{"SVM"})),
             ("Neural networks","신경망",lambda d:family(d,{"DNN/MLP"}))]
    cres=period_dot_panel(axes[1],panel_c,"B. 알고리즘군 사용" if ko else "B. Algorithm-family use",[BLUE,'#587987','#596273','#806F91','#806750'],ylim=(-3,103))
    neural_counts=[cres["Neural networks"][p]["n"] for p in periods]
    _pin(neural_counts, [13,14,18,9], "make_streamlined_figures.py:1529")  # prompt 106 pin
    _pin(sum(neural_counts), 54, "make_streamlined_figures.py:1529")  # prompt 106 pin
    axes[1].set_ylabel('%')

    def independently_validated(d): return has(d,"VAL02",{"EXTERNAL","TEMPORAL"})
    def calibrated(d): return any(has(d,k,{"R"}) for k in ("MET_CALSLOPE_R","MET_CALINT_R","MET_CALPLOT_R"))
    panel_validation=[("Later/external validation","후기·외부 검증",independently_validated),
                      ("Calibration reported","보정 보고",calibrated),
                      ("Paired model comparison","짝지은 모델 비교",lambda d:has(d,"MET_PAIR",{"Y","USED"}))]
    vres=period_dot_panel(axes[2],panel_validation,"C. 검증 근거" if ko else "C. Validation evidence",[GREEN,"#B07A00",PURPLE],direct_labels=True,label_offsets=[1,0,-1],ylim=(-2,48))
    axes[2].set_ylabel('%')

    panel_d=[("Candidate predictors specified","후보 설명변수 명세",lambda d:reduce_recoverability(d,"PRD13")=="FULL"),
             ("Tuning/evaluation separated","튜닝·평가 분리",lambda d:exp_by_id[d["study_id"]]["algorithm_development"]["tuning_selection_status"]=="TUNING_REPORTED_SEPARATED"),
             ("Final model fully specified","최종모형 완전 명세",lambda d:has(d,"REP17",{"R"})),
             ("Analysis code available","분석 코드 공개",lambda d:has(d,"MOD15",{"USED"})),
             ("Survey weights reported","조사가중치 보고",lambda d:has(d,"SUR04",{"USED"}))]
    dres=period_dot_panel(axes[3],panel_d,"D. 재현성과 조사설계 보고" if ko else "D. Reproducibility and survey-design reporting",[BLUE,"#E69F00","#009E73","#CC79A7","#D55E00"],direct_labels=True,label_offsets=[4,0,-5,-1,0],ylim=(-2,58))
    axes[3].set_ylabel('%')

    method_types=[("Method/workflow/tool development or improvement","방법·절차·도구 개발·개선","METHOD_WORKFLOW_OR_TOOL_DEVELOPMENT_OR_IMPROVEMENT"),
                  ("Existing-method comparison/evaluation","기존 방법 비교·평가","EXISTING_METHODS_COMPARISON_OR_EVALUATION")]
    mbottom=np.zeros(4); eres={}
    for i,(en,kr,code) in enumerate(method_types):
        ns=np.array([sum(r["method_research_category"]==code for r in rows) for rows in mgroups]); pct=100*ns/np.array(mden)
        saxes[0].bar(range(4),pct,bottom=mbottom,color=colors[i],label=kr if ko else en); mbottom+=pct
        eres[en]={p:{"n":int(n),"denominator":d,"percent":round(float(q),1)} for p,n,d,q in zip(periods,ns,mden,pct)}
    saxes[0].set_title("A. 방법연구 유형" if ko else "A. Method-research type",loc='left',weight='bold',fontsize=9.2); saxes[0].set_xticks(range(4)); saxes[0].set_xticklabels(periods,fontsize=7); saxes[0].set_ylim(0,112); saxes[0].set_ylabel('%')
    saxes[0].legend(frameon=False,fontsize=7,loc='upper center',bbox_to_anchor=(.5,-.14)); saxes[0].axvspan(2.5,3.5,color='#E5E7EB',alpha=.45,zorder=0)
    for j,n in enumerate(mden): saxes[0].text(j,103,f"n={n}",ha='center',fontsize=7,color=GREY)

    stage_specs=[("Model development","모델 개발",lambda s:bool(set(s)&{"PREDICTION_OR_CLASSIFICATION","CLUSTERING_OR_REPRESENTATION","CAUSAL_OR_STRUCTURE_LEARNING"})),
                 ("Validation/performance evaluation","검증·성능평가",lambda s:"VALIDATION_OR_PERFORMANCE_EVALUATION" in s),
                 ("Variable construction/selection","변수 구성·선택",lambda s:"FEATURE_ENGINEERING_OR_SELECTION" in s),
                 ("Explainable AI","설명가능 AI",lambda s:"EXPLAINABLE_AI" in s),
                 ("Missing data/data integration","결측자료·자료통합",lambda s:bool(set(s)&{"MISSING_DATA","DATA_INTEGRATION_OR_HARMONISATION"})),
                 ("User tool/workflow","사용자 도구·절차",lambda s:"USER_TOOL_OR_WORKFLOW" in s)]
    smat=np.array([[sum(fn(r["method_intervention_stages"]) for r in rows) for rows in mgroups] for _,_,fn in stage_specs])
    spct=100*smat/np.array(mden); im=saxes[1].imshow(spct,aspect='auto',cmap='Blues',vmin=0,vmax=100)
    saxes[1].set_yticks(range(6)); saxes[1].set_yticklabels([x[1] if ko else x[0] for x in stage_specs],fontsize=7); saxes[1].set_xticks(range(4)); saxes[1].set_xticklabels(periods,fontsize=7)
    saxes[1].set_title("B. 방법연구가 다룬 분석단계" if ko else "B. Analytic stages targeted by method research",loc='left',weight='bold',fontsize=9.2)
    for i in range(6):
        for j in range(4): saxes[1].text(j,i,f"{smat[i,j]}/{mden[j]}\n({spct[i,j]:.1f}%)",ha='center',va='center',fontsize=7,color='white' if spct[i,j]>55 else '#111827')

    export={"schema":"exploratory_temporal_orientation_analysis_v2","analysis_status":"POST_HOC_DESCRIPTIVE; not a monotonic trend model","periods":periods,
            "health_focused_classification":{"period_denominators":hden,"interpretation_practices":ares,"health_topics":{"population":"health-focused classification studies","period_denominators":topic_den,"categories":topic_en,"counts":topic_mat.tolist(),"monte_carlo_chi_square_p":round(p_mc,6),"cramers_v":round(cramer_v,6)},"algorithm_families":cres,"validation_evidence":vres,"reproducibility_and_survey_reporting":dres},
            "method_focused":{"period_denominators":mden,"types":eres,"targeted_stages":{en:{p:{"n":int(smat[i,j]),"denominator":mden[j],"percent":round(float(spct[i,j]),1)} for j,p in enumerate(periods)} for i,(en,_,_) in enumerate(stage_specs)}},
            "limits":"The 2025-2026 period is incomplete through September 2026; method-period denominators are small."}
    # Keep the two columns close enough to spend the available width on larger
    # panel typography rather than on an oversized central gutter.
    fig._final_layout_kwargs={"h_pad":2.8,"w_pad":3.0,"pad":.8}
    fig.tight_layout(**fig._final_layout_kwargs)
    fig.text(.52,1.035,f"N={N_CORE}; period n={', '.join(map(str, hden))}",ha="center",va="bottom",fontsize=10)  # prompt 106: denominator from data
    save(fig,"fig12_temporal_changes_ko" if ko else "fig12_temporal_changes")
    # Method-focused period counts are retained in the derived JSON only; their small
    # denominators do not justify a separately numbered reader-facing figure.
    plt.close(sfig)
    if not ko:
        with open(os.path.join(PROJ,"results/derived/exploratory_temporal_practice_analysis.json"),"w") as f: json.dump(export,f,indent=2,ensure_ascii=False)


def main():
    _pin(len(CLS), 165, "make_streamlined_figures.py:1590")  # prompt 106 pin
    _pin(len(HEALTH), 184, "make_streamlined_figures.py:1590")  # prompt 106 pin
    _pin(len(METHOD), 36, "make_streamlined_figures.py:1590")  # prompt 106 pin
    _pin(len(ALL), 220, "make_streamlined_figures.py:1590")  # prompt 106 pin
    for lang in ("en","ko"):
        figure2(lang); figure3(lang); figure4_nonclassification(lang); figure5_classification(lang); figure6_health_classification(lang); figure7_dataset_preparation(lang)
        figure8_model_development(lang); figure9_evaluation(lang); figure9_variable(lang); figure10_reproducibility(lang); figure11_practices(lang)


if __name__ == "__main__":
    main()
