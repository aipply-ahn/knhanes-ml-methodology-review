#!/usr/bin/env python3
"""Claim-ordered main figures (prompt 093): Figures 2-5, English and Korean.

Prompt 093 reduces the main text from eight to five figures (review v31, section 4.2):
  Figure 2  How ML was used and what studies claimed (A use of ML, B purpose vs output, C proposed uses)
  Figure 3  Evidence for the classification claim (A definitions and tuning, B data-dependent steps)
  Figure 4  Evidence for further claims (A SHAP vs stability, B survey design, C individual use, D methods)
  Figure 5  Claims and required evidence, study by study (A heatmap, B claim-by-claim summary)
Panels moved out of the main text (publications per year, analyses performed, participant selection,
importance methods, survey design by stage) are drawn by make_supplementary_figures.py.
All counts come from the adjudicated study records via claim_evidence_analysis (the same records
exported in Supplementary Table S5); nothing is typed in.

Colour rules shared by every figure:
  evidence met / complete / done      TEAL
  partial / unclear                   AMBER
  problem (before split, evaluation data involved, insufficient)  VERMILION
  not reported                        DARK GREY
  not applicable / no claim           LIGHT GREY
  studies making a claim (open ring)  NAVY outline
  neutral distributions               NAVY
  health-focused vs method-focused    NAVY vs SLATE
"""
from __future__ import annotations

import os
from collections import Counter

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
from matplotlib.lines import Line2D
from matplotlib.patches import Patch

import claim_evidence_analysis as ce
import make_streamlined_figures as m

OUT = m.OUT
TEAL, AMBER, VERM = "#0F8B8D", "#E0A526", "#D1495B"
DGREY, LGREY, NAVY, SLATE = "#4B5563", "#D9DEE5", "#1F3A5F", "#7B8794"
LIGHT_TEAL, PALE_NAVY = "#8CCFD0", "#A9B8CC"
FS_TITLE, FS_LABEL, FS_TICK, FS_VALUE = 12.4, 11.4, 11.0, 10.8
FIG_W = 7.4


def style(lang):
    plt.rcParams.update({
        "font.family": "NanumSquare" if lang == "ko" else "DejaVu Sans",
        "font.size": FS_TICK, "axes.labelsize": FS_LABEL, "xtick.labelsize": FS_TICK,
        "ytick.labelsize": FS_TICK, "legend.fontsize": FS_VALUE,
        "axes.spines.top": False, "axes.spines.right": False, "axes.linewidth": .7,
        "pdf.fonttype": 42, "ps.fonttype": 42, "savefig.dpi": 450, "axes.unicode_minus": False,
    })


def title(fig, ax, text, x=0.012, dy=0.012):
    pos = ax.get_position()
    fig.text(x, pos.y1 + dy, text, ha="left", va="bottom", fontsize=FS_TITLE, weight="bold")


def grid(ax, axis="x"):
    ax.grid(axis=axis, color="#E5E7EB", linewidth=.6); ax.set_axisbelow(True)


def save(fig, stem, ko):
    name = stem + ("_ko" if ko else "")
    for ext in ("pdf", "png"):
        fig.savefig(os.path.join(OUT, f"{name}.{ext}"), dpi=450, facecolor="white")
    plt.close(fig)


def pct(n, d):
    return 100.0 * n / d if d else 0.0


def T(ko, en, kr):
    return kr if ko else en


SYN = None


def syn():
    global SYN
    if SYN is None:
        SYN = ce.build()
    return SYN


def stacked_rows(ax, rows, colors, show_min=7.0):
    """rows: list of (label, [counts]); counts sum to the row denominator."""
    y = np.arange(len(rows))
    for i, (_, counts) in enumerate(rows):
        total = sum(counts); left = 0.0
        for n, col in zip(counts, colors):
            w = pct(n, total)
            if n:
                ax.barh(i, w, left=left, color=col, height=.64, edgecolor="white", linewidth=.6)
                if w >= show_min:
                    dark = col in (TEAL, VERM, DGREY, NAVY)
                    ax.text(left + w / 2, i, f"{w:.0f}%", ha="center", va="center", fontsize=FS_VALUE,
                            color="white" if dark else "#111827")
            left += w
    ax.set_yticks(y); ax.set_yticklabels([r[0] for r in rows], linespacing=1.0); ax.invert_yaxis()
    ax.set_xlim(0, 100); ax.set_xticks([0, 25, 50, 75, 100]); ax.set_xticklabels(["0", "25", "50", "75", "100%"])


def dumbbell(ax, rows, xmax, ko, context_rows=(), label_pad=.045):
    y = np.arange(len(rows))
    for i, (_, claim, ev) in enumerate(rows):
        ax.plot([ev, claim], [i, i], color=LGREY, lw=3.2, zorder=1, solid_capstyle="round")
        ax.scatter(claim, i, s=78, facecolor="white", edgecolor=NAVY, linewidth=1.9, zorder=3)
        ax.scatter(ev, i, s=78, color="#9CA3AF" if i in context_rows else TEAL, zorder=4)
        ax.text(claim + xmax * label_pad, i, f"{ev}/{claim} ({pct(ev, claim):.0f}%)", va="center", fontsize=FS_VALUE)
    ax.set_yticks(y); ax.set_yticklabels([r[0] for r in rows], linespacing=1.0); ax.invert_yaxis()
    ax.set_xlim(0, xmax); grid(ax)
    return [Line2D([], [], marker="o", ls="", mfc="white", mec=NAVY, mew=1.9, ms=8.5, label=T(ko, "Studies making the claim", "주장한 연구")),
            Line2D([], [], marker="o", ls="", color=TEAL, ms=8.5, label=T(ko, "Required evidence reported", "필요한 근거를 보고한 연구"))]


# --------------------------------------------------------------------------- Figure 2
def figure2(lang="en"):
    """How ML was used (220) and what health-focused studies claimed (184)."""
    style(lang); ko = lang == "ko"; s = syn()
    fig = plt.figure(figsize=(FIG_W, 10.2))
    axA = fig.add_axes([.44, .735, .46, .215])
    axB = fig.add_axes([.44, .445, .40, .17])
    axC = fig.add_axes([.44, .055, .40, .28])
    # A. how ML was used (mutually exclusive, 220)
    u = s["use_composition"]
    rows = [(T(ko, "Classify a current\nhealth state", "현재 건강상태 분류"), u["classify_current_state"], NAVY),
            (T(ko, "Classify, outcome\ntiming unclear", "분류, 결과 시점 불명확"), u["classification_timing_unclear"], NAVY),
            (T(ko, "Estimate a continuous\nor ordered value", "연속·순서형 값 추정"), u["estimate_continuous_or_ordered"], NAVY),
            (T(ko, "Other health analyses", "기타 건강 분석"), u["other_health_analyses"], NAVY),
            (T(ko, "Develop or improve\na method", "방법 개발·개선"), u["develop_or_improve_method"], SLATE),
            (T(ko, "Compare existing\nmethods", "기존 방법 비교"), u["compare_existing_methods"], SLATE)]
    assert sum(r[1] for r in rows) == 220
    y = np.arange(len(rows))
    axA.barh(y, [r[1] for r in rows], color=[r[2] for r in rows], height=.66)
    axA.set_yticks(y); axA.set_yticklabels([r[0] for r in rows], linespacing=1.0); axA.invert_yaxis()
    for i, r in enumerate(rows):
        axA.text(r[1] + 3, i, str(r[1]), va="center", fontsize=FS_VALUE)
    axA.axhline(3.5, color="#9CA3AF", lw=.8, ls=(0, (3, 2)))
    axA.text(185, 1.5, T(ko, "Health-\nfocused\n184", "건강\n중심\n184"), color=NAVY, fontsize=FS_VALUE, va="center", ha="right")
    axA.text(185, 4.5, T(ko, "Method-\nfocused\n36", "방법\n중심\n36"), color=SLATE, fontsize=FS_VALUE, va="center", ha="right")
    axA.set_xlim(0, 188); axA.set_xticks([0, 50, 100, 150]); axA.set_xlabel(T(ko, "Studies", "연구 수")); grid(axA)
    title(fig, axA, T(ko, "A. What ML was used for (N=220)", "A. ML의 사용 목적 (N=220)"))
    # B. stated purpose (open ring) vs produced output (filled square), 184 health-focused studies
    health = [r for r in m.PURPOSE_RECORDS if r["study_category"] == "HEALTH_ANALYSIS"]
    assoc_out = lambda r: m.PURPOSE_V13_BY_ID[r["study_id"]]["association_audit"]["any_association_estimate_reported"] == "Y"
    pairs = [(T(ko, "Health-state estimation\nvs performance estimate", "건강상태 추정 목적\n대 성능 추정치"), "HEALTH_STATE_OR_HEALTH_VALUE_ESTIMATION", lambda r: "MODEL_PERFORMANCE" in r["analytic_outputs"]),
             (T(ko, "Variable interpretation\nvs importance ranking", "변수 해석 목적\n대 중요도 순위"), "VARIABLE_RELEVANCE_OR_MODEL_INTERPRETATION", lambda r: "VARIABLE_CONTRIBUTION_OR_RANK" in r["analytic_outputs"]),
             (T(ko, "Population association\nvs association estimate", "모집단 연관 목적\n대 연관 추정치"), "POPULATION_ASSOCIATION_ANALYSIS", assoc_out)]
    stats = []
    for label, purpose, out in pairs:
        p = [r for r in health if purpose in r["health_analysis_purpose_components"]]
        o = [r for r in health if out(r)]
        stats.append((label, len(p), len(o), sum(out(r) for r in p)))
    assert [x[1:] for x in stats] == [(173, 175, 172), (84, 138, 80), (21, 56, 20)]
    for i, (_, p, o, _both) in enumerate(stats):
        axB.plot([p, o], [i, i], color=LGREY, lw=3.2, zorder=1, solid_capstyle="round")
        axB.scatter(p, i, s=78, facecolor="white", edgecolor=NAVY, linewidth=1.9, zorder=3)
        axB.scatter(o, i, s=78, marker="s", color=NAVY, zorder=3)
        axB.text(p - 7, i, str(p), ha="right", va="center", fontsize=FS_VALUE)
        axB.text(o + 6, i, str(o), ha="left", va="center", fontsize=FS_VALUE, weight="bold")
    axB.set_yticks(range(3)); axB.set_yticklabels([x[0] for x in stats], linespacing=1.0); axB.set_ylim(2.6, -.6)
    axB.set_xlim(0, 200); axB.set_xticks([0, 50, 100, 150, 200]); axB.set_xlabel(T(ko, "Health-focused studies", "건강 중심 연구 수")); grid(axB)
    axB.legend(handles=[Line2D([], [], marker="o", ls="", mfc="white", mec=NAVY, mew=1.8, ms=8, label=T(ko, "Stated as a purpose", "목적으로 명시")),
                        Line2D([], [], marker="s", ls="", color=NAVY, ms=8, label=T(ko, "Produced as an output", "산출물로 제시"))],
               frameon=False, loc="lower left", bbox_to_anchor=(-.02, 1.0), ncol=2, fontsize=FS_VALUE - .4, handlelength=1.0)
    title(fig, axB, T(ko, "B. Stated purposes and produced outputs (N=184)", "B. 명시된 목적과 실제 산출물 (N=184)"), dy=.045)
    # C. uses proposed by the authors
    uses = s["health_proposed_use"]
    rows = [(T(ko, "Research or hypothesis\ngeneration", "연구·가설 생성"), uses["RESEARCH_OR_HYPOTHESIS_GENERATION"], PALE_NAVY, None),
            (T(ko, "Surveillance or policy", "감시·정책"), uses["POPULATION_SURVEILLANCE_OR_POLICY"], NAVY, T(ko, "core cohort 37", "핵심 코호트 37")),
            (T(ko, "Individual use\n(any of the four below)", "개인 활용\n(아래 넷 중 하나 이상)"), uses["individual_use_any"], NAVY, T(ko, "core cohort 48", "핵심 코호트 48")),
            (T(ko, "   Screening", "   선별"), uses["SCREENING"], PALE_NAVY, None),
            (T(ko, "   Diagnostic support", "   진단 보조"), uses["DIAGNOSTIC_SUPPORT"], PALE_NAVY, None),
            (T(ko, "   Risk-group identification", "   위험군 식별"), uses["RISK_GROUP_IDENTIFICATION"], PALE_NAVY, None),
            (T(ko, "   Personalised management", "   개인 맞춤 관리"), uses["PERSONALISED_MANAGEMENT"], PALE_NAVY, None),
            (T(ko, "Other prevention support", "기타 예방 지원"), uses["OTHER"], PALE_NAVY, None)]
    y = np.arange(len(rows))
    axC.barh(y, [r[1] for r in rows], color=[r[2] for r in rows], height=.66)
    axC.set_yticks(y); axC.set_yticklabels([r[0] for r in rows], linespacing=1.0); axC.invert_yaxis()
    for i, (lab, v, col, note) in enumerate(rows):
        axC.text(v + 2.5, i, f"{v}" + (f"  ({note})" if note else ""), va="center", fontsize=FS_VALUE,
                 weight="bold" if note else "normal")
    axC.set_xlim(0, 135); axC.set_xticks([0, 25, 50, 75, 100]); axC.set_xlabel(T(ko, "Health-focused studies (may overlap)", "건강 중심 연구 수(중복 가능)")); grid(axC)
    title(fig, axC, T(ko, "C. Uses proposed by the authors (N=184)", "C. 저자가 제안한 활용 (N=184)"))
    save(fig, "fig2_use_and_claims", ko)


# --------------------------------------------------------------------------- Figure 3
def figure3(lang="en"):
    """Evidence for the classification claim (165 core studies)."""
    style(lang); ko = lang == "ko"; s = syn()
    fig = plt.figure(figsize=(FIG_W, 7.2))
    axA = fig.add_axes([.40, .655, .56, .28])
    axB = fig.add_axes([.40, .125, .56, .33])
    cc = s["classification_components"]
    out_c = Counter(m.reduce_recoverability(d, "OUT16") for d in ce.CORE)
    prd_c = Counter(m.reduce_recoverability(d, "PRD13") for d in ce.CORE)
    tun = Counter(ce.tuning_status(d) for d in ce.CORE)
    rows = [(T(ko, "Outcome definition", "결과 정의"), [out_c["FULL"], out_c["PART"], out_c["NO"], 0, 0]),
            (T(ko, "Predictor set", "설명변수 집합"), [prd_c["FULL"], prd_c["PART"], prd_c["NO"], 0, 0]),
            (T(ko, "Tuning kept apart\nfrom final evaluation", "튜닝과 최종 평가 분리"),
             [tun["TUNING_REPORTED_SEPARATED"] + tun["NO_TUNING_OR_DEFAULT_MODEL"], tun["TUNING_REPORTED_SEPARATION_NOT_DEMONSTRATED"],
              tun["TUNING_REPORTED_EVALUATION_DATA_INVOLVED"], tun["TUNING_NOT_REPORTED"], 0]),
            (T(ko, "All three", "세 요소 모두"), [cc["all_three"], 0, 165 - cc["all_three"], 0, 0])]
    for _, r in rows: assert sum(r) == 165
    assert cc["all_three"] == 12
    stacked_rows(axA, rows, [TEAL, AMBER, VERM, DGREY, LGREY])
    axA.get_yticklabels()[-1].set_weight("bold")
    fig.legend(handles=[Patch(color=TEAL, label=T(ko, "Complete or kept apart", "완전·분리")), Patch(color=AMBER, label=T(ko, "Partial or not shown", "부분·확인 불가")),
                        Patch(color=VERM, label=T(ko, "Insufficient, tuned on evaluation\ndata, or not all three", "불충분·평가자료로 튜닝·\n셋 중 하나 이상 없음")), Patch(color=DGREY, label=T(ko, "Not reported", "미보고"))],
               frameon=False, ncol=3, loc="upper left", bbox_to_anchor=(.02, .605), fontsize=FS_VALUE - .6, handlelength=1.0, columnspacing=.9)
    title(fig, axA, T(ko, "A. Reproducible definitions and clean evaluation (N=165)", "A. 재현 가능한 정의와 분리된 평가 (N=165)"))

    def status(d, key, within, before, unclear):
        v = set(m.flat_values(d, key))
        if v & set(before): return "BEFORE"
        if v & set(within): return "WITHIN"
        if v & set(unclear): return "UNCLEAR"
        return "NA"
    specs = [(T(ko, "Missing-value handling", "결측값 처리"), "PRE05", ("USED",), ("NOT_USED",), ("NR", "UNC")),
             (T(ko, "Scaling or other\npreprocessing", "척도화·기타 전처리"), "PRE14", ("USED",), ("NOT_USED",), ("NR", "UNC")),
             (T(ko, "Feature selection", "변수 선택"), "PRE13", ("WITHIN", "TRAIN"), ("BEFORE",), ("ORDER_NR", "OTHER")),
             (T(ko, "Class rebalancing", "클래스 재균형"), "IMB03", ("WITHIN", "TRAIN"), ("BEFORE",), ("ORDER_NR", "OTHER"))]
    status_rows = []
    any_before = set()
    for lab, key, wi, be, un in specs:
        c = Counter()
        for d in ce.CORE:
            st = status(d, key, wi, be, un); c[st] += 1
            if st == "BEFORE": any_before.add(d["study_id"])
        status_rows.append((lab, [c["WITHIN"], c["UNCLEAR"], c["BEFORE"], c["NA"]]))
    assert [r[1] for r in status_rows] == [[6, 42, 31, 86], [20, 65, 78, 2], [22, 21, 37, 85], [40, 5, 17, 103]]
    assert len(any_before) == 83
    status_rows.append((T(ko, "At least one step\nbefore the split", "분할 전 수행 단계\n하나 이상"), [0, 0, len(any_before), 165 - len(any_before)]))
    stacked_rows(axB, status_rows, [TEAL, AMBER, VERM, LGREY])
    axB.get_yticklabels()[-1].set_weight("bold")
    axB.axhline(3.5, color="#9CA3AF", lw=.8, ls=(0, (3, 2)))
    fig.legend(handles=[Patch(color=TEAL, label=T(ko, "Within training data", "훈련자료 안에서")), Patch(color=AMBER, label=T(ko, "Timing unclear", "시점 불명확")),
                        Patch(color=VERM, label=T(ko, "Before the split", "분할 전")), Patch(color=LGREY, label=T(ko, "Not applied or not applicable", "미적용·해당 없음"))],
               frameon=False, ncol=4, loc="lower left", bbox_to_anchor=(.02, .0), fontsize=FS_VALUE - .6, handlelength=1.0, columnspacing=.8)
    title(fig, axB, T(ko, "B. When data-dependent steps were done (N=165)", "B. 자료 의존 처리를 수행한 시점 (N=165)"))
    save(fig, "fig3_classification_evidence", ko)


# --------------------------------------------------------------------------- Figure 4
def figure4(lang="en"):
    """Evidence for further claims: variables, population, individual use, methods."""
    style(lang); ko = lang == "ko"; s = syn()
    fig = plt.figure(figsize=(FIG_W, 12.4))
    axA = fig.add_axes([.14, .795, .60, .16])
    axB = fig.add_axes([.44, .54, .44, .15])
    axC = fig.add_axes([.44, .295, .44, .15])
    axD = fig.add_axes([.52, .06, .30, .125])
    # A. SHAP versus stability checks, by publication period (studies producing a ranking)
    per = s["period_importance"]; periods = list(per)
    ticks = ["≤2019", "2020–22", "2023–24", "2025–26"]
    shap = [pct(per[p]["shap"], per[p]["importance"]) for p in periods]
    stab = [pct(per[p]["stability_among_importance"], per[p]["importance"]) for p in periods]
    x = np.arange(4)
    axA.plot(x, shap, color=NAVY, lw=1.3, alpha=.8, zorder=2); axA.scatter(x, shap, s=70, color=NAVY, zorder=3)
    axA.plot(x, stab, color=TEAL, lw=1.3, alpha=.8, zorder=2); axA.scatter(x, stab, s=70, marker="D", color=TEAL, zorder=3)
    for i, p in enumerate(periods):
        shap_up = shap[i] >= stab[i]
        axA.text(i, shap[i] + (6 if shap_up else -13), f"{per[p]['shap']}/{per[p]['importance']}", ha="center", fontsize=FS_VALUE, color=NAVY)
        axA.text(i, stab[i] + (-13 if shap_up else 6), f"{per[p]['stability_among_importance']}/{per[p]['importance']}", ha="center", fontsize=FS_VALUE, color=TEAL)
    axA.text(3.2, shap[-1], T(ko, "SHAP used", "SHAP 사용"), va="center", fontsize=FS_VALUE, color=NAVY, weight="bold")
    axA.text(3.2, stab[-1], T(ko, "Stability\nchecked", "안정성\n점검"), va="center", fontsize=FS_VALUE, color=TEAL, weight="bold", linespacing=1.0)
    axA.set_xticks(x); axA.set_xticklabels(ticks); axA.set_xlim(-.4, 3.15); axA.set_ylim(-14, 100)
    axA.set_yticks([0, 50, 100]); axA.set_yticklabels(["0", "50", "100%"])
    axA.set_ylabel(T(ko, "% of studies\nproducing a ranking", "순위 산출 연구 중 %"), linespacing=1.0); grid(axA, "y")
    title(fig, axA, T(ko, "A. Variables: SHAP spread faster than stability checks (N=129)", "A. 변수: SHAP 확산과 안정성 점검 (N=129)"))
    # B. survey design by claim group; each requirement row shows only the group it applies to
    g = s["survey_by_claim_group"]
    groups = [("population_association", T(ko, "Association purpose", "모집단 연관 목적"), NAVY),
              ("surveillance_or_policy", T(ko, "Surveillance or policy", "감시·정책 활용"), "#4F7CAC"),
              ("neither", T(ko, "Neither", "둘 다 아님"), LGREY)]
    metrics = [("association_criterion_met", T(ko, "Weights + design-based\nvariance, same analysis\n(association requirement)", "같은 분석의 가중치 +\n설계 기반 분산\n(연관 주장 기준)")),
               ("policy_criterion_met", T(ko, "Weights + a design\nfeature (surveillance\nor policy requirement)", "가중치 + 설계 요소\n(감시·정책 주장 기준)")),
               ("any_weight_mention", T(ko, "Any mention of\nsurvey weights", "조사가중치 언급"))]
    applies = {"association_criterion_met": {"population_association"}, "policy_criterion_met": {"surveillance_or_policy"},
               "any_weight_mention": {"population_association", "surveillance_or_policy", "neither"}}
    h = .26
    for j, (gk, glab, col) in enumerate(groups):
        n = g[gk]["n"]
        for i, (mk, _) in enumerate(metrics):
            if gk not in applies[mk]:
                continue
            yi = i if len(applies[mk]) == 1 else i + (j - 1) * h
            v = pct(g[gk][mk], n)
            axB.barh(yi, v, height=h * .92 * (1.6 if len(applies[mk]) == 1 else 1), color=col)
            axB.text(v + 1.2, yi, f"{g[gk][mk]}/{n}", va="center", fontsize=FS_VALUE - .6)
    assert (g["population_association"]["association_criterion_met"], g["surveillance_or_policy"]["policy_criterion_met"]) == (4, 8)
    axB.set_yticks(np.arange(len(metrics))); axB.set_yticklabels([lab for _, lab in metrics], linespacing=1.0); axB.invert_yaxis()
    for lab in axB.get_yticklabels()[:2]: lab.set_weight("bold")
    axB.axhline(1.5, color="#9CA3AF", lw=.8, ls=(0, (3, 2)))
    axB.set_xlim(0, 45); axB.set_xticks([0, 10, 20, 30, 40]); axB.set_xticklabels(["0", "10", "20", "30", "40%"]); grid(axB)
    axB.legend(handles=[Patch(color=col, label=f"{glab} (n={g[gk]['n']})") for gk, glab, col in groups],
               frameon=False, loc="lower left", bbox_to_anchor=(-.72, 1.0), ncol=3, fontsize=FS_VALUE - .8, handlelength=1.0, columnspacing=.7)
    title(fig, axB, T(ko, "B. Population: survey design by claim (N=165; groups overlap)", "B. 모집단: 주장별 조사설계 반영 (N=165; 집단 중복)"), dy=.04)
    # C. individual use versus other core studies
    iv = s["individual_vs_other"]
    imetrics = [("validated_beyond_development", T(ko, "Validation beyond the\ndevelopment data", "개발자료 밖 검증")),
                ("calibration", T(ko, "Calibration", "보정")), ("threshold_reported", T(ko, "Decision threshold", "결정 임계값")),
                ("all_three", T(ko, "All three (requirement)", "셋 모두 (기준)"))]
    h = .36
    for j, (gk, glab, col) in enumerate([("individual_use", T(ko, "Proposed individual use", "개인 활용 제안"), NAVY), ("other", T(ko, "Other core studies", "그 외 핵심 코호트"), PALE_NAVY)]):
        n = iv[gk]["n"]
        yy = np.arange(len(imetrics)) + (j - .5) * h
        axC.barh(yy, [pct(iv[gk][k], n) for k, _ in imetrics], height=h * .92, color=col, label=f"{glab} (n={n})")
        for yi, (k, _) in zip(yy, imetrics):
            axC.text(pct(iv[gk][k], n) + 1, yi, f"{iv[gk][k]}/{n}", va="center", fontsize=FS_VALUE - .6)
    assert iv["individual_use"]["all_three"] == 5 and iv["individual_use"]["n"] == 48
    axC.set_yticks(np.arange(len(imetrics))); axC.set_yticklabels([lab for _, lab in imetrics], linespacing=1.0); axC.invert_yaxis()
    axC.get_yticklabels()[-1].set_weight("bold")
    axC.set_xlim(0, 60); axC.set_xticks([0, 20, 40, 60]); axC.set_xticklabels(["0", "20", "40", "60%"]); grid(axC)
    axC.legend(frameon=False, loc="lower left", bbox_to_anchor=(-.72, 1.0), ncol=2, fontsize=FS_VALUE - .8, handlelength=1.0, columnspacing=.8)
    title(fig, axC, T(ko, "C. Individual use: validation, calibration, threshold (N=165)", "C. 개인 활용: 검증·보정·임계값 (N=165)"), dy=.04)
    # D. method claims; the two review requirements first, context rows in grey
    mc = s["method_claims"]
    rows = [(T(ko, "Develop a method: tested\nbeyond one KNHANES application", "방법 개발: KNHANES 한 번\n적용을 넘어선 평가"), mc["development"]["n"], mc["development"]["beyond_single_knhanes_application"]),
            (T(ko, "Compare methods: uncertainty\nor paired comparison", "방법 비교:\n불확실성·쌍 비교"), mc["comparison"]["n"], mc["comparison"]["uncertainty_or_paired_comparison"]),
            (T(ko, "Develop a method:\ncompared with other methods", "방법 개발:\n다른 방법과 비교"), mc["development"]["n"], mc["development"]["comparator_evaluation"]),
            (T(ko, "Compare methods: tested\nbeyond one KNHANES application", "방법 비교: KNHANES 한 번\n적용을 넘어선 평가"), mc["comparison"]["n"], mc["comparison"]["beyond_single_knhanes_application"])]
    handles = dumbbell(axD, rows, 40, ko, context_rows={2, 3}, label_pad=.05)
    for lab in axD.get_yticklabels()[:2]: lab.set_weight("bold")
    axD.axhline(1.5, color="#9CA3AF", lw=.8, ls=(0, (3, 2)))
    axD.set_xticks([0, 10, 20, 30]); axD.set_xlabel(T(ko, "Method-focused studies", "방법 중심 연구 수"))
    handles.append(Line2D([], [], marker="o", ls="", color="#9CA3AF", ms=8.5, label=T(ko, "Other evidence (not a requirement)", "기타 근거(기준 아님)")))
    axD.legend(handles=handles, frameon=False, loc="lower left", bbox_to_anchor=(-1.62, 1.0), ncol=2, fontsize=FS_VALUE - .8, columnspacing=.8, handletextpad=.3)
    title(fig, axD, T(ko, "D. Methods: evaluation of the method (N=36)", "D. 방법: 방법의 평가 (N=36)"), dy=.04)
    save(fig, "fig4_further_claims", ko)


# --------------------------------------------------------------------------- Figure 5
def figure5(lang="en"):
    """Study-level synthesis (unchanged content of former Figure 8; prompt 091 layout)."""
    style(lang); ko = lang == "ko"; s = syn()
    fig = plt.figure(figsize=(FIG_W, 9.2))
    axA = fig.add_axes([.33, .64, .56, .26])
    axB = fig.add_axes([.37, .07, .41, .40])
    rows = s["studies"]
    keys = ["classification", "interpretation", "association", "policy", "individual"]
    row_labels = [T(ko, "Classification: outcome,\npredictors, tuning apart", "분류: 결과·설명변수\n정의, 튜닝 분리"),
                  T(ko, "Variable interpretation:\nranking stability", "변수 해석:\n순위 안정성"),
                  T(ko, "Population association:\nweights + design variance", "모집단 연관:\n가중치 + 설계 분산"),
                  T(ko, "Surveillance or policy:\nweights + design feature", "감시·정책:\n가중치 + 설계 요소"),
                  T(ko, "Individual use: validation,\ncalibration, threshold", "개인 활용: 검증·\n보정·임계값"),
                  T(ko, "All own claims supported", "자기 주장 근거 모두")]

    def all_met(r):
        return all(v for v in r["evidence_met"].values() if v is not None)
    nclaims = lambda r: sum(r["claims"].values())
    nmet = lambda r: sum(bool(v) for v in r["evidence_met"].values() if v is not None)
    bins = [("4–5", lambda n: n >= 4), ("3", lambda n: n == 3), ("2", lambda n: n == 2), ("1", lambda n: n == 1)]
    order, bounds = [], []
    for lab, test in bins:
        g = sorted([r for r in rows if test(nclaims(r))], key=lambda r: (-nmet(r), -nclaims(r), r["study_id"]))
        bounds.append((lab, len(order), len(order) + len(g))); order += g
    assert len(order) == 165 and [b[2] - b[1] for b in bounds] == [12, 41, 67, 45]
    M = [[(1 if r["evidence_met"][k] else 0) if r["claims"][k] else -1 for r in order] for k in keys]
    M.append([1 if all_met(r) else 0 for r in order])
    cmap = {1: TEAL, 0: VERM, -1: "#EEF1F4"}
    img = np.array([[matplotlib.colors.to_rgb(cmap[v]) for v in row] for row in M])
    axA.imshow(img, aspect="auto", interpolation="nearest")
    axA.set_yticks(range(len(row_labels))); axA.set_yticklabels(row_labels, linespacing=.95, fontsize=FS_TICK - .8)
    axA.get_yticklabels()[-1].set_weight("bold")
    axA.axhline(4.5, color="white", lw=3.0)
    for lab, a, b in bounds:
        if a:
            axA.axvline(a - .5, color=NAVY, lw=1.1)
        axA.text((a + b - 1) / 2, -.62, f"{lab}\n{b - a}", ha="center", va="bottom", fontsize=FS_VALUE - .4,
                 color=NAVY, linespacing=1.0, clip_on=False)
    axA.text(-3, -.62, T(ko, "Claims per study\nStudies (n)", "연구당 주장 수\n연구 수"), ha="right", va="bottom",
             fontsize=FS_VALUE - .4, color=NAVY, linespacing=1.0, clip_on=False)
    beyond = s["beyond_classification"]
    x120 = (bounds[0][1] + bounds[2][2] - 1) / 2
    axA.text(x120, 5, T(ko, f"{beyond['all_claims_supported']} of {beyond['studies']} with a further claim",
                        f"추가 주장 {beyond['studies']}편 중 {beyond['all_claims_supported']}편"),
             ha="center", va="center", fontsize=FS_VALUE - .8, color="white", weight="bold")
    axA.set_xticks([]); axA.set_xlabel(T(ko, "165 core studies grouped by number of claims", "핵심 연구 165편, 주장 수별 묶음"), fontsize=FS_VALUE - 1.0)
    for sp in axA.spines.values(): sp.set_visible(False)
    counts = [sum(v == 1 for v in row) for row in M]; dens = [sum(v != -1 for v in row) for row in M]
    assert list(zip(counts, dens)) == [(12, 165), (15, 82), (4, 19), (8, 37), (5, 48), (3, 165)]
    for i, (n, dn) in enumerate(zip(counts, dens)):
        axA.text(1.01, 1 - (i + .5) / len(M), f"{n}/{dn}", transform=axA.transAxes, va="center", ha="left",
                 fontsize=FS_VALUE, weight="bold" if i == len(M) - 1 else "normal")
    fig.legend(handles=[Patch(color=TEAL, label=T(ko, "Requirement met", "기준 충족")), Patch(color=VERM, label=T(ko, "Requirement not met", "기준 미충족")),
                        Patch(color="#EEF1F4", label=T(ko, "Claim not made", "해당 주장 없음"))],
               frameon=False, ncol=3, loc="upper left", bbox_to_anchor=(.10, .605), fontsize=FS_VALUE - .6, handlelength=1.0)
    title(fig, axA, T(ko, "A. Evidence each study reported for its own claims (N=165)", "A. 연구별로 자기 주장에 필요한 근거를 보고했는가 (N=165)"), dy=.055)
    cl = {c["claim"]: c for c in s["claims"]}
    ip = s["importance_produced_row"]; rel = s["individual_relaxed_row"]; mc = s["method_claims"]
    drows = [(T(ko, "Classify a current health state:\nall three components", "현재 건강상태 분류:\n세 요소 모두"), 165, cl["classification"]["studies_with_required_evidence"]),
             (T(ko, "Variable interpretation stated:\nstability checked", "변수 해석 목적 명시:\n안정성 점검"), cl["interpretation"]["studies_making_claim"], cl["interpretation"]["studies_with_required_evidence"]),
             (T(ko, "Population association:\nweights + design-based variance", "모집단 연관:\n가중치 + 설계 기반 분산"), cl["association"]["studies_making_claim"], cl["association"]["studies_with_required_evidence"]),
             (T(ko, "Surveillance or policy:\nweights + a design feature", "감시·정책:\n가중치 + 설계 요소"), cl["policy"]["studies_making_claim"], cl["policy"]["studies_with_required_evidence"]),
             (T(ko, "Individual use: validation +\ncalibration + threshold", "개인 활용: 검증 +\n보정 + 임계값"), cl["individual"]["studies_making_claim"], cl["individual"]["studies_with_required_evidence"]),
             (T(ko, "Method development: tested\nbeyond one KNHANES application", "방법 개발: KNHANES 한 번\n적용을 넘어선 평가"), mc["development"]["n"], mc["development"]["beyond_single_knhanes_application"]),
             (T(ko, "Method comparison: uncertainty\nor paired comparison", "방법 비교:\n불확실성·쌍 비교"), mc["comparison"]["n"], mc["comparison"]["uncertainty_or_paired_comparison"]),
             (T(ko, "Importance produced (output,\nnot a claim): stability checked", "중요도 산출(산출물, 주장 아님):\n안정성 점검"), ip["studies_producing_importance"], ip["stability_checked"]),
             (T(ko, "Individual use, relaxed: validation\n+ calibration or threshold", "개인 활용, 완화 기준:\n검증 + 보정 또는 임계값"), rel["studies_making_claim"], rel["studies_with_required_evidence"])]
    handles = dumbbell(axB, drows, 200, ko, context_rows={7, 8})
    for lab in axB.get_yticklabels(): lab.set_fontsize(FS_TICK - .8)
    axB.axhline(6.5, color="#9CA3AF", lw=.8, ls=(0, (3, 2)))
    axB.text(198, 6.28, T(ko, "below: output and relaxed checks", "아래: 산출물·완화 기준 점검"), ha="right", va="center", fontsize=FS_VALUE - 1.2, color=DGREY)
    axB.set_xticks([0, 50, 100, 150]); axB.set_xlabel(T(ko, "Studies (core cohort; method rows: method-focused)", "연구 수(핵심 코호트; 방법 행은 방법 중심)"))
    axB.legend(handles=handles, frameon=False, loc="lower left", bbox_to_anchor=(-.8, 1.0), ncol=2, fontsize=FS_VALUE - .6)
    title(fig, axB, T(ko, "B. Claims and the evidence they require", "B. 주장과 그 주장에 필요한 근거"), dy=.04)
    save(fig, "fig5_claim_evidence", ko)


FIGURES = (figure2, figure3, figure4, figure5)


def main():
    for lang in ("en", "ko"):
        for fn in FIGURES:
            fn(lang)
    print("built", len(FIGURES) * 2, "figure files")


if __name__ == "__main__":
    main()
