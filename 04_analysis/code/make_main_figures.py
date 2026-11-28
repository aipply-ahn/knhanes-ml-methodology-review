#!/usr/bin/env python3
"""earlier-draft Figures 2-5 (prompts 094-100): how ML is used in KNHANES and how its practice has changed.

Prompt 100 (review v38, straight storyline): one step per figure, no reversal panels.
  earlier-draft Figure 2  How ML was used, step by step: A studies per year by purpose, B purpose and task, C health topic,
            D outcome (source and form), E predictors and data, F algorithm families, G evaluation steps
  earlier-draft Figure 3  Variable importance as the main product: A rankings and SHAP by period, B domains of the most important
            variables (all + four topics with at least ten ranking studies), C diabetes and prediabetes variables
  earlier-draft Figure 4  Practices that became more common: code sharing and ranking stability (every period); validation and
            calibration (2026; 2025 and 2026 as separate points) as small multiples
  earlier-draft Figure 5  Next steps: A how ranking stability was checked, B survey design by workflow step, C preprocessing timing
  Supplementary helpers: figure_agreement (S7, with oral-health and respiratory columns), figure_topic_slopes and
  figure_flat_practices (S3E-F), figure_testbed (S6).

Prompt 099 (review v37 storyline): earlier-draft Figure 2 is the bridge "the familiar ML workflow and what it classified"
(A studies per year, B topics, C algorithm families by period, D familiar evaluation work, E what was classified);
earlier-draft Figure 3 A rankings and SHAP by period, B rankings within each major topic, C importance methods; earlier-draft Figure 4 A-B
(pairwise agreement moved to a supplementary figure of an earlier draft via figure_agreement); earlier-draft Figure 5 one slope chart (A more
common including ranking stability, B no consistent change); earlier-draft Figure 6 A how stability was checked (survey cycles 0),
B survey design by workflow step, C preprocessing timing with an all-steps summary row. No amber in main figures.

  earlier-draft Figure 2  The KNHANES ML literature (prompt 097, review v35): A every study by year and sample size, B health
            topic by period (184), C analytic task (220)
  earlier-draft Figure 3  From classification to explanation (A ranking and SHAP by period, 165; B importance methods, 129;
            C later use of rankings, 129)
  earlier-draft Figure 4  What the rankings pointed to (prompt 097): A domains named important by topic, B the metabolic and
            endocrine studies one by one, C agreement of domain sets between pairs of studies
  earlier-draft Figure 5  Maturing practice (2x3 small multiples; earlier-draft Figure 4)
  earlier-draft Figure 6  Next steps (A stability, B survey design by stage, C preprocessing timing)
  The earlier-draft Figure 5 (methods testbed) is drawn by figure_testbed for a supplementary figure of an earlier draft.

Author decision: no author-aim or proposed-use coding and no claim/requirement framing.
All counts come from results/derived/practice_trends_096.json (tools/practice_trends.py), computed from the
adjudicated study records exported in a supplementary table of an earlier draft; nothing is typed in.

Colour meaning, shared by every figure (no red):
  NAVY   health-focused studies / the main series
  TEAL   practices that became more common (maturing practice)
  greys  "before the split" (dark grey), not applicable, reference, method-focused studies (no amber since prompt 099)
  greys  not applicable, reference, method-focused studies
"""
from __future__ import annotations

import json
import os
from collections import Counter
from pathlib import Path

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
from matplotlib.lines import Line2D
from matplotlib.patches import Patch

from main_figure_map import remap

from make_claim_figures import FS_LABEL, FS_TICK, FS_TITLE, FS_VALUE, FIG_W, NAVY, SLATE, TEAL, AMBER, LGREY, DGREY, PALE_NAVY, OUT, style, title, grid, T

# prompt 106: value pins (criterion A changed the study set; previous values are logged, not asserted)
def _pin(current, previous, label):
    import json as _j, pathlib as _p
    if current != previous:
        with open(_p.Path(__file__).resolve().parents[1] / "results/derived/criterion_a_value_changes.jsonl", "a") as _f:
            _f.write(_j.dumps({"label": label, "previous": previous, "current": current}, ensure_ascii=False, default=str) + "\n")
    return True

ROOT = Path(__file__).resolve().parents[1]
LIGHT_TEAL = "#8CCFD0"
TICKS = {"en": ["≤2019", "2020–22", "2023–24", "2025–26"], "ko": ["≤2019", "2020–22", "2023–24", "2025–26"]}
SHORT_TICKS = ["≤19", "20–22", "23–24", "25–26"]
BEFORE = "#6B7280"  # prompt 099: "before the split" in dark grey (review v37: no warning colour)
SHADES = ["#1F3A5F", "#3E5C82", "#6D86A6", "#9FB2C8", "#C9D4E1"]  # navy shades for composition bars


def data():
    return json.loads((ROOT / "results/derived/practice_trends_112.json").read_text())  # prompt 112: superset of _110


def NS():
    """prompt 106: study-set counts from the derived values (criterion A changed them)."""
    o = data()
    tc = o["task_composition"]
    h, mth = sum(tc["health"].values()), sum(tc["method"].values())
    return {"core": o["classified_outcome"]["n"], "health": h, "method": mth, "all": h + mth, "rank": o["importance_ranking_total"]}


def save(fig, stem, ko, out=None, tight=False):
    name = stem + ("_ko" if ko else "")
    for ext in ("pdf", "png"):
        fig.savefig(os.path.join(out or OUT, f"{name}.{ext}"), dpi=450, facecolor="white",
                    **({"bbox_inches": "tight", "pad_inches": .02} if tight else {}))  # prompt 108: full-width earlier-draft Figure 3
    plt.close(fig)


def pct(n, d):
    return 100.0 * n / d if d else 0.0


def hbars(ax, labels, values, colors, denom, xmax, fmt_pct=True, fs=None):
    y = np.arange(len(labels))
    ax.barh(y, values, color=colors, height=.64)
    ax.set_yticks(y); ax.set_yticklabels(labels, linespacing=1.0); ax.invert_yaxis()
    for i, v in enumerate(values):
        ax.text(v + xmax * .015, i, f"{v} ({pct(v, denom):.0f}%)" if fmt_pct else str(v), va="center", fontsize=fs or FS_VALUE)
    ax.set_xlim(0, xmax); grid(ax)


DOMAIN_NAMES = {"AGE": ("Age", ""), "ADIPOSITY_BODY_SIZE": ("Body size", ""), "SOCIOECONOMIC": ("Socio-\neconomic", ""),
                "MENTAL_SUBJECTIVE_HEALTH": ("Mental,\nsubjective", ""), "SEX": ("Sex", ""),
                "PHYSICAL_ACTIVITY_FUNCTION": ("Physical\nactivity", ""), "LIPIDS": ("Lipids", ""),
                "ALCOHOL": ("Alcohol", ""), "GLYCAEMIA_DIABETES": ("Glucose", ""), "SMOKING": ("Smoking", ""),
                "WORK_CLINICAL_HISTORY": ("Work,\nclinical\nhistory", ""), "BLOOD_PRESSURE": ("Blood\npressure", ""),
                "DIET": ("Diet", ""), "KIDNEY_URINE": ("Kidney,\nurine", ""), "PAIN_MUSCULOSKELETAL": ("Pain,\nmuscle", "")}


# --------------------------------------------------------------------------- earlier-draft Figure 2
TOPIC_NAMES = {"METABOLIC_ENDOCRINE": ("Metabolic and endocrine", ""), "MENTAL_HEALTH": ("Mental health", ""),
               "MUSCULOSKELETAL": ("Musculoskeletal", ""), "CARDIOVASCULAR": ("Cardiovascular", ""),
               "ORAL_HEALTH": ("Oral health", ""), "RESPIRATORY": ("Respiratory", ""),
               "GENERAL_HEALTH_MULTIMORBIDITY": ("General health", ""),
               "KIDNEY_UROLOGIC": ("Kidney and urologic", ""), "OTORHINOLARYNGOLOGIC": ("Ear, nose and throat", "")}  # prompt 106
PALE_SLATE = "#B8C0CA"


def grouped_hbars(ax, groups, denom, xmax, fs=None):
    """Horizontal bars in labelled groups; a group heading takes one row without a bar."""
    labels, y, i = [], [], 0
    for gname, rows, col in groups:
        labels.append(gname); y.append(i); i += 1
        for lab, v in rows:
            ax.barh(i, v, color=col, height=.64)
            ax.text(v + xmax * .015, i, f"{v} ({pct(v, denom):.0f}%)", va="center", fontsize=fs or FS_VALUE)
            labels.append(lab); y.append(i); i += 1
    ax.set_yticks(y); ax.set_yticklabels(labels, linespacing=1.0); ax.set_ylim(i - .4, -.6)
    heads = {0} | {sum(len(g[1]) + 1 for g in groups[:k]) for k in range(1, len(groups))}
    for k, t in enumerate(ax.get_yticklabels()):
        if y[k] in heads:
            t.set_weight("bold"); t.set_color(DGREY)
    ax.tick_params(axis="y", length=0); ax.set_xlim(0, xmax); grid(ax)


# --------------------------------------------------------------------------- earlier-draft Figures 2 and 3 (prompt 107)
# Review v44 (fixed denominators): earlier-draft Figure 2 describes the literature and its data (A, B on all 250 studies in three
# colours; C, D on the 192 core studies); earlier-draft Figure 3 describes how the analyses were done, every panel on the 192 core
# studies, with not-reported (hatched) and not-applicable (very light grey) bars so that each panel adds to 192.
LBLUE = "#8DB6E0"      # the 22 health-focused studies with other tasks
NA_GREY = "#E9ECF0"    # not applicable / step not applied
NR_EDGE = "#9CA3AF"    # hatch colour of not-reported bars


def nr_bar(ax, y, v, height, horizontal=True, left=0):
    """Not reported: white bar with grey hatching."""
    kw = dict(color="white", edgecolor=NR_EDGE, hatch="/////", linewidth=.6)
    if horizontal:
        ax.barh(y, v, left=left, height=height, **kw)
    else:
        ax.bar(y, v, bottom=left, width=height, **kw)


def figure2(lang="en"):
    """Prompt 108 (review v45): the literature (250 studies). A studies per publication year and B task, in the three
    group colours (navy 192 core, light blue 22 other health tasks, grey 36 method-focused). The 192-study panels (topic,
    survey years) moved to earlier-draft Figure 3, so each figure keeps one denominator."""
    style(lang); ko = lang == "ko"; o = data()
    FT, FS = FS_TITLE - 1.4, FS_VALUE - 1.2  # prompt 108: legible at text width
    fig = plt.figure(figsize=(FIG_W, 3.9))
    # Prompt 108 (author request): two equal half-width cells; A keeps its y-axis label inside its cell.
    axA = fig.add_axes([.075, .15, .405, .66])
    axB = fig.add_axes([.515, .15, .465, .66])

    def ttl(ax, text, dx=0.0, dy=.03):
        pos = ax.get_position()
        fig.text(.01 if ax is axA else .515, pos.y1 + dy, text, ha="left", va="bottom", fontsize=FT, weight="bold", linespacing=1.0)

    grp = [("core", NAVY, T(ko, f"Health analysis (classification) (n={NS()['core']})", f" () (n={NS()['core']})")),
           ("other_health", LBLUE, T(ko, f"Health analysis (other ML) (n={NS()['health'] - NS()['core']})", f" ( ML) (n={NS()['health'] - NS()['core']})")),
           ("method", SLATE, T(ko, f"Method-focused (n={NS()['method']})", f"  (n={NS()['method']})"))]
    pts = o["literature_map"]
    assert {q["group"] for q in pts} == {g for g, _, _ in grp} and len(pts) == NS()["all"]
    years = list(range(min(q["year"] for q in pts), 2027))
    bottom = np.zeros(len(years))
    for g, col, lab in grp:
        v = np.array([sum(q["year"] == y and q["group"] == g for q in pts) for y in years])
        axA.bar(years[:-1], v[:-1], bottom=bottom[:-1], color=col, width=.72, label=lab)
        axA.bar(years[-1], v[-1], bottom=bottom[-1], color=col, width=.72, hatch="////", edgecolor="white", linewidth=0)
        bottom += v
    for y, t in zip(years, bottom):
        axA.text(y, t + .8, f"{int(t)}", ha="center", va="bottom", fontsize=FS - 2.6, color=DGREY)  # prompt 108: every year, small enough to stay apart
    axA.text(2026.55, 1.2, T(ko, "to\nOct", ""), ha="left", va="bottom", fontsize=FS - .6, color=DGREY, linespacing=.95)
    axA.set_xlim(min(years) - .8, 2027.2); axA.set_ylim(0, 50); axA.set_yticks([0, 20, 40])  # prompt 108: axis starts at the first study (no shared survey-year axis now)
    axA.set_xticks([2010, 2015, 2020, 2025]); axA.tick_params(labelsize=FS)
    axA.set_ylabel(T(ko, "Studies", ""), fontsize=FS, labelpad=2); grid(axA, "y")
    [axA.spines[k].set_visible(False) for k in ("top", "right")]
    axA.legend(frameon=False, loc="upper left", fontsize=FS - 1.4, handlelength=1.0, labelspacing=.3, borderaxespad=.2)
    ttl(axA, T(ko, f"A. Studies per publication year (N={NS()['all']})", f"A.    (N={NS()['all']})"))

    # B. Task of the 250 studies: three groups with subtotals, one bar per task.
    tc = o["task_composition"]; hh, mm_ = tc["health"], tc["method"]
    groups = [(T(ko, f"Health analysis (classification) ({hh['classification']})", f" () ({hh['classification']})"), NAVY,
               [(T(ko, "Classify a health state", ""), hh["classification"])]),
              (T(ko, f"Health analysis (other ML) ({hh['continuous_or_ordered'] + hh['other']})", f" ( ML) ({hh['continuous_or_ordered'] + hh['other']})"), LBLUE,
               [(T(ko, "Continuous or ordered value", ""), hh["continuous_or_ordered"]), (T(ko, "Other analyses", ""), hh["other"])]),
              (T(ko, f"Method-focused ({sum(mm_.values())})", f"  ({sum(mm_.values())})"), SLATE,
               [(T(ko, "Develop or improve a method", ""), mm_["develop_or_improve"]),
                (T(ko, "Compare existing methods", ""), mm_["compare_existing"])])]
    assert sum(n for _, _, rows in groups for _, n in rows) == NS()["all"]
    yb = 0.0
    for gname, col, rows in groups:
        axB.text(0, yb - .15, gname, ha="left", va="bottom", fontsize=FS, weight="bold", color=NAVY if col == LBLUE else col)
        yb += 1.0
        for lab, n in rows:
            axB.text(0, yb - .30, lab, ha="left", va="bottom", fontsize=FS, color="#111827")
            axB.barh(yb, n, color=col, height=.42)
            axB.text(n + 4, yb, f"{n}", va="center", fontsize=FS)
            yb += 1.35
        yb += .30
    # Author: box the classification group and name it "core studies" so readers do not miss the term.
    axB.add_patch(matplotlib.patches.Rectangle((-3, -.72), 216, 2.02, fill=False, edgecolor=TEAL, lw=1.6, clip_on=False, zorder=4))
    axB.text(210, .70, T(ko, "Core studies", ""), ha="right", va="bottom", fontsize=FS + .4, weight="bold", color=TEAL)
    axB.set_ylim(yb - .5, -.75); axB.set_yticks([]); axB.set_xlim(0, max(215, 1.1 * NS()["core"])); axB.set_xticks([0, 50, 100, 150, 200])
    axB.tick_params(axis="x", labelsize=FS); axB.set_xlabel(T(ko, "Studies", ""), fontsize=FS, labelpad=1)
    [axB.spines[k].set_visible(False) for k in ("left", "top", "right")]; grid(axB)
    ttl(axB, T(ko, f"B. Task (N={NS()['all']})", f"B.  (N={NS()['all']})"))
    save(fig, "fig2_literature_map", ko, tight=True)


def figure_analysis(lang="en"):
    """Prompt 110 (review v47): how the 192 core studies were analysed, ten panels in workflow order.
    Topic and data: A health topic | B how survey years were combined | C outcome source | D predictor data.
    Sample and preparation: E analytic sample | F candidate predictors | G missing values.
    Analysis: H algorithms fitted (count order) | I model selected (H's order) | J evaluation steps.
    The survey-years histogram is a supplementary figure of an earlier draft (prompt 110). Bar panels sit on a white 192-long frame; not reported is
    hatched and not applicable very light grey."""
    style(lang); ko = lang == "ko"; o = data(); N = NS()["core"]
    FT, FS = FS_TITLE - 2.5, FS_VALUE - 2.5  # prompt 111: about 8 pt titles and 7 pt labels at print size
    # Prompt 111 (review v48): one row pitch and one bar thickness in every bar panel (earlier-draft Figure 6B style); panels with
    # fewer rows are shorter. Bands: Topic and data (A-D quarters), Sample and preparation (E-G thirds), Analysis
    # (H-J thirds). Laid out in inches.
    PITCH, GRP, TTL, XL, HH = .21, .30, .38, .42, 1.15  # prompt 112: C has three timing rows; review: .17 -> .19 (denser panels C, I)
    bands = (12 * PITCH, 9 * PITCH, 15 * PITCH)  # C: age and sex; E: outcome form and construction; M: three groups  # author: data and sample | variables and processing | analysis
    H_in = .04 + sum(GRP + TTL + bh + XL for bh in bands)
    fig = plt.figure(figsize=(FIG_W, H_in))
    tops, t = [], .04
    for bh in bands:
        t += GRP + TTL; tops.append(t); t += bh + XL
    GUT, YL = .06, .055  # prompt 112: wider gutter; v8: .045 -> .06 (labels of the next panel)

    def cell(k, top, ncol, h, ylab=False, widths=None):
        w = widths[k] if widths else 1.0 / ncol
        c0 = .005 + (sum(widths[:k]) if widths else k * w)
        x0 = c0 + (YL if ylab else 0)
        ax = fig.add_axes([x0, 1 - (top + h) / H_in, c0 + w - GUT - x0, h / H_in])
        ax._cellx = c0; ax._cellr = c0 + w - GUT  # titles start at the cell edge; labels are fitted inside the cell
        ax._hin = h; ax._col = (ncol, k, ncol == 4)  # review: aligned rows and columns (see align_columns)
        return ax
    nrows = {"A": 8, "B": 4, "C": 9, "D": 4, "G": 6, "H": 7, "I": 8, "J": 5}  # prompt 112: C has three timing rows
    # Review (author: align rows and columns): every panel of a band has the same axes height and top, so
    # titles and x axes line up across the row; bars keep one thickness and spread over the height.
    # Author: three bands in ML order. 1 dataset and sample: A dataset composition, B outcome timing and
    # source, C age group, D sample size. 2 variables and processing: E topic, F data-driven variable selection,
    # G predictor data, H candidate predictors, I missing values. 3 analysis: J fitted, K selected, L evaluation
    # designs, M performance measures (L and M as in a supplementary figure of an earlier draft).
    # Author: row 1 A dataset, B topic, C sample selection (age, sex), D sample size; row 2 E outcome coding,
    # F predictor data, G variable selection, H candidate predictors, I missing values.
    axB, axA, axAge, axF_ = cell(0, tops[0], 4, bands[0]), cell(1, tops[0], 4, bands[0]), cell(2, tops[0], 4, bands[0]), cell(3, tops[0], 4, bands[0], ylab=True)
    # Author: the variable-selection panel was dropped; four panels per band.
    axD_, axE_, axG_, axH_ = (cell(0, tops[1], 4, bands[1]), cell(1, tops[1], 4, bands[1]), cell(2, tops[1], 4, bands[1], ylab=True),
                              cell(3, tops[1], 4, bands[1]))
    axI_, axJ_, axK_, axM = (cell(k, tops[2], 4, bands[2]) for k in range(4))
    for top, lab in zip(tops, (T(ko, "Dataset and problem design", ""), T(ko, "Health variables and data processing", ""),
                               T(ko, "Analysis (modelling and performance)", ""))):
        fig.text(.01, 1 - (top - TTL - (.07 if ko else .04)) / H_in, lab, fontsize=FT + .6, weight="bold", color=DGREY, va="bottom")  # KO glyphs are taller
    # internal names keep the old panel roles; the printed letters follow the new order
    axD, axE, axF, axG, axH, axI, axJ, axK = axD_, axE_, axF_, axG_, axH_, axI_, axJ_, axK_

    def ttl(ax, text):
        pos = ax.get_position()
        small = getattr(ax, "_col", (0,))[0] == 5  # five-panel band: slightly smaller titles
        fig.text(getattr(ax, "_cellx", pos.x0), pos.y1 + .06 / H_in, text, ha="left", va="bottom", fontsize=FT - (.8 if small else 0), weight="bold", linespacing=1.0)

    renderer = fig.canvas.get_renderer()

    def fbars(ax, rows, colors=None):
        """rows: (label, value, kind) with kind navy | teal | nr | na; white 192 frame behind every bar; names on the
        left axis, value right after the bar (prompt 111)."""
        xmax = max(228, 1.18 * N)
        bh = min(.6, .6 * PITCH * len(rows) / ax._hin)  # one physical bar thickness in every panel
        for i, (lab, v, kind) in enumerate(rows):
            if kind == "head":  # group heading row (no bar)
                continue
            ax.barh(i, N, color="white", edgecolor="#D1D5DB", linewidth=.5, height=bh, zorder=1)
            if kind == "nr":
                nr_bar(ax, i, v, bh)
            else:
                ax.barh(i, v, color={"navy": NAVY, "teal": TEAL, "na": NA_GREY}[kind], height=bh, zorder=2,
                        edgecolor="#C4CAD3" if kind == "na" else None, linewidth=.5 if kind == "na" else 0)
            ax.text(max(v, 0) + 4, i, f"{v}", va="center", fontsize=FS, color="#111827", zorder=3)
        ax.set_yticks(range(len(rows))); ax.set_yticklabels([r[0] for r in rows], fontsize=FS)
        for t, r in zip(ax.get_yticklabels(), rows):
            if r[2] == "head":
                t.set_fontweight("bold"); t.set_color(DGREY)
        ax.tick_params(axis="y", length=0, pad=2)
        ax.set_ylim(len(rows) - .5, -.5); ax.set_xlim(0, xmax)
        ax.set_xticks([0, N // 2, N]); ax.tick_params(axis="x", labelsize=FS)
        ax.set_xlabel(T(ko, "Core studies", ""), fontsize=FS, labelpad=1)
        [ax.spines[k].set_visible(False) for k in ("left", "top", "right")]; grid(ax)
        lw = max(t.get_window_extent(renderer).width for t in ax.get_yticklabels()) / fig.bbox.width
        ax._need = lw + .012  # left space for the row names; align_columns sets one start per column

    # Study-level codes for C, E and G.
    import claim_evidence_analysis as _ce, make_streamlined_figures as _ms
    CORE_ = _ce.CORE; assert len(CORE_) == N

    def _num(x):
        try:
            return float(x)
        except (TypeError, ValueError):
            return None

    def _age(d):
        lo, hi = _num(_ms.first(d, "POP03")), _num(_ms.first(d, "POP04"))
        if lo is None and hi is None:
            return "nr"
        if hi is not None and hi < 19:
            return "child"
        if lo is not None and lo < 18:
            return "all"
        if lo is None:
            return "nr"
        return "older" if lo >= 60 else "middle" if lo >= 30 else "adult"
    # A. Health topic of the 192 core studies.
    ct = o["core_topics"]
    shown = [k for k in ct if k in TOPIC_NAMES and k != "KIDNEY_UROLOGIC"][:7]
    short = {"METABOLIC_ENDOCRINE": ("Metabolic", ""), "OTORHINOLARYNGOLOGIC": ("ENT", ""),
             "MUSCULOSKELETAL": ("Musculoskeletal", "")}
    rowsA = [(T(ko, *short.get(k, TOPIC_NAMES[k])), ct[k], "navy") for k in shown]
    rowsA.append((T(ko, "Other topics", ""), sum(v for k, v in ct.items() if k not in shown), "navy"))
    assert sum(r[1] for r in rowsA) == N
    fbars(axA, rowsA)
    ttl(axA, T(ko, f"B. Health topic\n(N={N})", f"B. \n(N={N})"))
    # B. How each core study combined survey years (sums to 192; unclear hatched).
    sc = o["core_year_scope"]
    tm = o["outcome_timing_192"]
    rowsB = [(T(ko, "Survey years", ""), 0, "head"),  # author: survey years above outcome timing
             (T(ko, "One year", ""), sc["ONE_YEAR"], "navy"),  # author: labels name years and cycles
             (T(ko, "Several years,\none cycle", ""), sc["MULTI_SAME"], "navy"),
             (T(ko, "Several years,\nseveral cycles", ""), sc["MULTI_CROSS"], "navy"), (T(ko, "Unclear", ""), sc["UNC"], "nr"),
             (T(ko, "Outcome timing", ""), 0, "head"),
             (T(ko, "Same survey", ""), tm["current_state_same_survey"], "navy"),
             (T(ko, "Unclear", ""), tm["timing_unclear"], "nr"), (T(ko, "Future event", ""), tm["future_event"], "navy")]
    assert sum(r[1] for r in rowsB[1:5]) == N and sum(r[1] for r in rowsB[6:]) == N
    fbars(axB, rowsB)
    ttl(axB, T(ko, f"A. Dataset and\ntiming (N={N})", f"A.  \n  (N={N})"))

    # E. Outcome coding: modelled form (as Table 1 counts) and how the categories were made (protocol OUT11).
    os_ = o["outcome_structure"]
    oc = Counter(_ms.first(d, "OUT11") for d in CORE_)
    rowsE = [(T(ko, "Outcome form", ""), 0, "head"), (T(ko, "Binary", ""), os_["BINARY"], "navy"),
             (T(ko, "Several binary", ""), os_["MULTIBIN"], "navy"), (T(ko, "Multiclass", ""), os_["MULTICLASS"], "navy"),
             (T(ko, "Mixed", ""), os_["MIXED"], "navy")] + ([(T(ko, "Unclear", ""), os_["UNC"], "nr")] if os_.get("UNC") else []) + [
             (T(ko, "Categories from", ""), 0, "head"), (T(ko, "Categorical source", ""), oc["N"], "navy"),
             (T(ko, "Cut-off on a score", ""), oc["Y"], "navy"), (T(ko, "Unclear", ""), oc["UNC"], "nr")]
    h2 = next(i for i, r in enumerate(rowsE) if i and r[2] == "head")
    assert sum(r[1] for r in rowsE[1:h2]) == N and sum(r[1] for r in rowsE[h2 + 1:]) == N
    fbars(axD, rowsE)
    ttl(axD, T(ko, f"E. Outcome coding\n(N={N})", f"E.  \n(N={N})"))
    # E. Predictor data (overlap).
    cc = o["survey_components_165"]
    fbars(axE, [(T(ko, "Interview", ""), cc["HEALTH_INTERVIEW"], "navy"), (T(ko, "Examination", ""), cc["EXAMINATION"], "navy"),  # prompt 111
                (T(ko, "Laboratory", ""), cc["LABORATORY"], "navy"), (T(ko, "Nutrition", ""), cc["NUTRITION"], "navy")])
    ttl(axE, T(ko, f"F. Predictor sources\n(N={N}; overlap)", f"F.  \n(N={N}, )"))

    # F and G. Histograms on a log axis; studies not reporting the value are stated in the median box.
    def hist_panel(ax, vals, reported, edges, ticks, ticklabels, text_fmt):
        h = ax.hist(vals, bins=edges, color=NAVY, edgecolor="white")[0]
        ax.set_ylim(0, max(h) * 1.9)
        ax.set_yticks([t for t in ax.get_yticks() if 0 <= t <= max(h) * 1.25])
        ax.set_xscale("log"); ax.set_xticks(ticks); ax.set_xticklabels(ticklabels); ax.tick_params(labelsize=FS); ax.minorticks_off()
        ax.set_ylabel(T(ko, "Core studies", ""), fontsize=FS, labelpad=1)
        [ax.spines[k].set_visible(False) for k in ("top", "right")]
        text_fmt = text_fmt + T(ko, f"\nnot reported {N - reported}", f"\n {N - reported}")
        ax.text(.97, .97, text_fmt, bbox=dict(facecolor="white", edgecolor="none", pad=1.5), zorder=5, transform=ax.transAxes,
                ha="right", va="top", fontsize=FS - .6, linespacing=1.0)
        ax._need = ax.get_position().x0 - ax.get_tightbbox(renderer).x0 / fig.bbox.width + .004  # tick labels and y label

    cs = o["core_sample"]
    hist_panel(axF, cs["values"], cs["reported"], np.logspace(np.log10(min(cs["values"])), np.log10(max(cs["values"])), 13),
               [1000, 10000, 100000], ["1k", "10k", "100k"],
               T(ko, f"median {cs['median']:,.0f}\n(IQR {cs['q1']:,.0f}–\n{cs['q3']:,.0f})", f" {cs['median']:,.0f}\n(\n{cs['q1']:,.0f}–{cs['q3']:,.0f})"))
    axF.axvline(cs["median"], color=DGREY, lw=1.3, ls="--")
    ttl(axF, T(ko, f"D. Final analytic sample\n(N={N}; log scale)", f"D.   \n(N={N},  )"))
    cp, cv = o["candidate_predictors"], o["candidate_predictor_values"]
    hist_panel(axG, cv, cp["reported"], np.logspace(np.log10(min(cv)), np.log10(max(cv)), 12), [10, 100, 1000], ["10", "100", "1k"],
               T(ko, f"median {cp['median']:g}", f" {cp['median']:g}"))
    axG.axvline(cp["median"], color=DGREY, lw=1.3, ls="--")
    for tx in axG.texts:  # author: keep the note clear of panel H's row labels (left-aligned, top left)
        tx.set_position((.03, .97)); tx.set_ha("left")
    axG.set_ylabel("")  # narrow column: the y axis is read as in D
    axG._need = axG.get_position().x0 - axG.get_tightbbox(renderer).x0 / fig.bbox.width + .004
    ttl(axG, T(ko, "G. Candidate\npredictors (log)", ""))

    # H. Missing values.
    mh = o["missing_handling_165"]
    rowsH = [(T(ko, "Complete case", ""), mh["complete_case"], "navy"), (T(ko, "Single imputation", ""), mh["single_imputation"], "navy"),
             (T(ko, "Multiple imputation", ""), mh["multiple_imputation"], "navy"), (T(ko, "Model-native", ""), mh["model_native"], "navy"),
             (T(ko, "Other or several", ""), mh["other_or_several"], "navy"), (T(ko, "Not reported", ""), mh["not_reported"], "nr")]
    assert sum(r[1] for r in rowsH) == N
    fbars(axH, rowsH)
    ttl(axH, T(ko, f"H. Missing values\n(N={N})", f"H.  \n(N={N})"))
    # I and J share one family order (by the number of studies fitting each family; Other last), so what was fitted
    # reads across to what the authors selected.
    # author: boosting and neural network are families, the other rows single algorithms, so name the coded
    # algorithms (fitted: XGBoost, LightGBM, gradient boosting; DNN/MLP)
    names = {"boosting": ("Boosting", T(ko, "Tree boosting\n(XGBoost, LightGBM etc.)", "")), "random_forest": ("Random forest", T(ko, "Random forest", "")),
             "logistic_regression": ("Logistic regression", T(ko, "Logistic regression", "")),
             "decision_tree": ("Decision tree", T(ko, "Decision tree", "")), "svm": ("SVM", "SVM"),
             "neural_network": ("Neural network", T(ko, "Neural network\n(MLP, DNN etc.)", ""))}
    af = o["algorithms_fitted_192"]; bp = o["practices"]["boosting"]; den = o["period_n"]
    order = sorted(names, key=lambda k: -af[k]) + ["other"]
    names["other"] = ("Other", T(ko, "Other", ""))
    fbars(axI, [(names[k][1], af[k], "navy") for k in order])  # prompt 108: no family singled out (author request)
    ttl(axI, T(ko, f"I. Algorithms fitted\n(N={N}; overlap)", f"I.  \n(N={N}, )"))
    sm = o["selected_model_family_192"]
    short_ = {"boosting": T(ko, "Tree boosting", ""), "neural_network": T(ko, "Neural network", ""), "logistic_regression": T(ko, "Logistic\nregression", "")}  # two lines: clear of panel I values  # K: full names in J
    rowsJ = [(short_.get(k, names[k][1]), sm[names[k][0]], "navy") for k in order] + [(T(ko, "Not designated", ""), sm.get("Not designated", 0), "nr")] * bool(sm.get("Not designated")) \
        + [(T(ko, "Not compared", ""), sm["single_algorithm"], "na")]  # author decision D17: no model designated
    assert sum(r[1] for r in rowsJ) == N
    fbars(axJ, rowsJ)
    ttl(axJ, T(ko, f"J. Model selected by\nthe authors (N={N})", f"J.   \n(N={N})"))
    ag = Counter(_age(d) for d in CORE_)
    def _sex(x):
        x = str(x).lower()
        if x in ("nr", "", "none_nr"):
            return "nr"
        if x.startswith(("female", "women")):
            return "f"
        if x.startswith(("male", "men")):
            return "m"
        return "both"
    sx = Counter(_sex(_ms.first(d, "POP05")) for d in CORE_)
    fbars(axAge, [(T(ko, "Age", ""), 0, "head"), (T(ko, "Under 19 only", ""), ag["child"], "navy"), (T(ko, "All ages", ""), ag["all"], "navy"),
                  (T(ko, "Minimum 18-29", ""), ag["adult"], "navy"), (T(ko, "Minimum 30-59", ""), ag["middle"], "navy"),
                  (T(ko, "Minimum 60+", ""), ag["older"], "navy"), (T(ko, "Not reported", ""), ag["nr"], "nr"),
                  (T(ko, "Sex", ""), 0, "head"), (T(ko, "Both sexes", ""), sx["both"], "navy"), (T(ko, "Women only", ""), sx["f"], "navy"),
                  (T(ko, "Men only", ""), sx["m"], "navy"), (T(ko, "Not reported", ""), sx["nr"], "nr")])
    assert sum(sx.values()) == N
    ttl(axAge, T(ko, f"C. Sample selection\n(N={N})", f"C.  \n(N={N})"))
    # L and M. Evaluation designs and performance measures (as a supplementary figure of an earlier draft).
    cs_ = _ms.classification_summary(CORE_); vc = cs_["validation"]
    fbars(axK, [(T(ko, "Train-test split", ""), vc["SPLIT"], "navy"), (T(ko, "Cross-validation", ""), vc["CV"], "navy"),
                (T(ko, "Bootstrap", ""), vc["BOOT"], "navy"), (T(ko, "Apparent only", ""), vc["APPARENT"], "navy"),
                (T(ko, "Later survey period", ""), vc["TEMPORAL"], "teal"), (T(ko, "External dataset", ""), vc["EXTERNAL"], "teal"),
                (T(ko, "Unclear", ""), vc["NONE_NR"], "nr")])
    both = sum(_ms.has(d, "VAL02", {"TEMPORAL"}) and _ms.has(d, "VAL02", {"EXTERNAL"}) for d in CORE_)
    beyond = vc["TEMPORAL"] + vc["EXTERNAL"] - both
    ttl(axK, T(ko, f"K. Evaluation designs\n(N={N}; overlap)", f"K.  \n(N={N}, )"))  # {beyond} beyond development data: in the text
    q, mr = cs_["metrics"], cs_["metric_reporting"]
    calib = sum(any(_ms.has(d, k, {"R"}) for k in ("MET_CALSLOPE_R", "MET_CALINT_R", "MET_CALPLOT_R")) for d in CORE_)
    # Author: grouped as discrimination and classification | uncertainty | calibration and clinical use.
    disc = sorted([("AUROC", q["AUROC"]), (T(ko, "Accuracy", ""), q["ACC"]), (T(ko, "Sensitivity (recall)", ""), q["SENS"]),
                   (T(ko, "PPV (precision)", ""), q["PPV"]), (T(ko, "Specificity", ""), q["SPEC"]),
                   (T(ko, "F1 score", ""), q["F1"]), ("AUPRC", q["AUPRC"])], key=lambda t: -t[1])
    fbars(axM, [(T(ko, "Discrimination", ""), 0, "head")] + [(l, v, "navy") for l, v in disc]
          + [(T(ko, "Uncertainty", ""), 0, "head"), (T(ko, "Confidence interval", ""), mr["MET_CI"], "navy"),
             (T(ko, "Test of model difference", ""), mr["MET_PAIR"], "navy")]
          + [(T(ko, "Calibration, utility", ""), 0, "head"), (T(ko, "Calibration", ""), calib, "navy"),
             (T(ko, "Brier score", ""), q["BRIER"], "navy"), (T(ko, "Decision curve", ""), q["DCA"], "navy")])
    ttl(axM, T(ko, f"L. Performance measures\nreported (N={N}; overlap)", f"L.   \n(N={N}, )"))
    # One plot start per column: the four columns of the first band, and the three columns shared by the second and
    # third bands (E above H, F above I, G above J); every panel in a column starts its bars or axis at the same x.
    groups = {}
    for ax in (axA, axB, axD, axE, axF, axG, axH, axI, axJ, axK, axAge, axM):
        groups.setdefault(ax._col, []).append(ax)
    for axs in groups.values():
        x0 = min(max(a._cellx + a._need for a in axs), min(a._cellr for a in axs) - (.10 if axs[0]._col[0] == 5 else .14))  # five-panel band: narrower plots
        for a in axs:
            pos = a.get_position(); a.set_position([x0, pos.y0, a._cellr - x0, pos.height])
    save(fig, "fig3_analysis_workflow", ko, tight=True)


# --------------------------------------------------------------------------- earlier-draft Figure 3
DOMAIN_TOPICS = ("METABOLIC_ENDOCRINE", "MENTAL_HEALTH", "MUSCULOSKELETAL", "CARDIOVASCULAR")
SHORT_TOPIC = {"ALL": ("All", ""), "METABOLIC_ENDOCRINE": ("Metabolic", ""), "MENTAL_HEALTH": ("Mental", ""),
               "MUSCULOSKELETAL": ("Musculo-\nskeletal", ""), "CARDIOVASCULAR": ("Cardio-\nvascular", ""),
               "ORAL_HEALTH": ("Oral", ""), "RESPIRATORY": ("Respiratory", ""),
               "KIDNEY_UROLOGIC": ("Kidney", ""), "OTORHINOLARYNGOLOGIC": ("ENT", ""),
               "OTHER_OR_CROSS_CUTTING": ("Other", "")}  # prompt 106


def domain_heatmap(ax, o, ko, topics, doms, outline=()):
    cmap = matplotlib.colors.LinearSegmentedColormap.from_list("nv", ["#FFFFFF", NAVY])
    cols = [("ALL", o["ranking_domains_all"])] + [(t, o["ranking_domains_by_topic"][t]) for t in topics]
    mat = np.array([[c[k] for _, c in cols] for k in doms]); ns = np.array([c["n"] for _, c in cols])
    share = mat / ns[None, :]
    ax.imshow(share, cmap=cmap, vmin=0, vmax=1, aspect="auto")
    for i in range(mat.shape[0]):
        for j in range(mat.shape[1]):
            ax.text(j, i, f"{100 * share[i, j]:.0f}", ha="center", va="center", fontsize=FS_VALUE - 2.6,
                    color="white" if share[i, j] > .5 else "#111827")
    tot = {"ALL": sum(o["core_topics"].values()), **o["core_topics"]}  # prompt 107: n of the 192-based topic size
    ax.set_xticks(range(len(cols))); ax.set_xticklabels([T(ko, *SHORT_TOPIC[t]) + f"\n{n} of {tot[t]}" for (t, _), n in zip(cols, ns)],
                                                       fontsize=FS_TICK - 2.4, linespacing=.95)
    ax.xaxis.tick_top()
    ax.set_yticks(range(len(doms))); ax.set_yticklabels([T(ko, *DOMAIN_NAMES[k]).replace("-\n", "").replace("\n", " ") for k in doms],
                                                       fontsize=FS_TICK - 2.2)
    ax.tick_params(length=0); [sp.set_visible(False) for sp in ax.spines.values()]
    ax.axvline(.5, color="white", lw=6)  # the "All" column stands apart
    for dom, tp in outline:
        i, j = doms.index(dom), 1 + list(topics).index(tp)
        ax.add_patch(matplotlib.patches.Rectangle((j - .5, i - .5), 1, 1, fill=False, edgecolor=TEAL, lw=2.2, zorder=4))
    return share


def figure3(lang="en"):
    """Prompt 100 (review v38): variable importance as the main product. A rankings and SHAP by period (165); B domains of
    the most important variables, all and the four topics with at least ten ranking studies (129); C variables named by
    the 12 diabetes and prediabetes studies. Topic slopes, importance methods and pairwise agreement are supplementary."""
    style(lang); ko = lang == "ko"; o = data()
    fig = plt.figure(figsize=(FIG_W, 2.9))  # prompt 112: one panel; the variables named are earlier-draft Figure 5
    axA = fig.add_axes([.11, .21, .87, .58])
    den = o["period_n"]; imp = o["practices"]["importance_ranking"]; shap = o["practices"]["shap"]
    x = np.arange(4)
    axA.bar(x, [pct(a, b) for a, b in zip(imp, den)], width=.62, color=NAVY, label=T(ko, f"Produced an importance ranking ({sum(imp)} of {NS()['core']})", f"    ({NS()['core']}  {sum(imp)})"))  # prompt 110
    axA.bar(x, [pct(a, b) for a, b in zip(shap, den)], width=.36, color=TEAL, label=T(ko, f"Used SHAP ({sum(shap)} of {NS()['core']})", f"SHAP  ({NS()['core']}  {sum(shap)})"))  # prompt 110
    for i in range(4):
        axA.text(i, pct(imp[i], den[i]) + 2.5, f"{imp[i]}/{den[i]}", ha="center", fontsize=FS_VALUE, color=NAVY)
        v = pct(shap[i], den[i])
        axA.text(i, v + 2.5 if v < 60 else v - 9, f"{shap[i]}/{den[i]}", ha="center", fontsize=FS_VALUE - 1,
                 color="white", weight="bold")  # prompt 111: white on navy or teal (teal on navy was hard to read)
    axA.set_xticks(x); axA.set_xticklabels([f"{t}\n(n={n})" for t, n in zip(SHORT_TICKS, den)], linespacing=1.0); axA.set_ylim(0, 112)  # prompt 101: same ticks as Figs 2F and 4
    axA.set_yticks([0, 25, 50, 75, 100]); axA.set_yticklabels(["0", "25", "50", "75", "100%"])
    axA.set_ylabel(T(ko, "% of core studies", "")); grid(axA, "y")
    axA.legend(frameon=False, loc="lower left", bbox_to_anchor=(0.0, 1.0), ncol=2, fontsize=FS_VALUE - .4, handlelength=1.0, borderaxespad=.1)  # prompt 110
    title(fig, axA, T(ko, f"Importance ranking and SHAP by publication period (N={NS()['core']})", f"    SHAP (N={NS()['core']})"), dy=.11)  # prompt 112: one panel, no letter
    save(fig, "fig4_variable_importance", ko, tight=True)  # prompt 107: earlier-draft Figure 3 -> 4; prompt 110: text width


# --------------------------------------------------------------------------- earlier-draft Figure 5 (prompt 112)
VAR_NAMES = {"Age": ("Age", ""), "Education, income or occupation": ("Educ., income, job", ""), "Sex": ("Sex", ""),
             "Marital status or household": ("Marital, household", ""), "Region or residence": ("Region", ""),
             "BMI": ("BMI", "BMI"), "Waist circumference or WHtR": ("Waist, WHtR", ""), "Height or weight": ("Height, weight", ""),
             "Body composition or grip": ("Body composition, grip", ""), "Smoking": ("Smoking", ""), "Alcohol": ("Alcohol", ""),
             "Physical activity": ("Physical activity", ""), "Diet or nutrients": ("Diet, nutrients", ""), "Sleep": ("Sleep", ""),
             "Self-rated health or quality of life": ("Self-rated health", ""), "Stress": ("Stress", ""),
             "Depression or mood": ("Depression, mood", ""), "Activity limitation or pain": ("Limitation, pain", ""),
             "Cholesterol or triglycerides": ("Cholesterol, TG", ""),
             "Hypertension or blood pressure": ("Blood pressure", ""), "Other diagnosed conditions": ("Other diagnoses", ""),
             "HbA1c or fasting glucose": ("HbA1c, glucose", ""), "Diabetes diagnosis": ("Diabetes", ""),
             "Blood count": ("Blood count", ""), "Liver enzymes": ("Liver enzymes", ""),
             "Kidney function or uric acid": ("Kidney function, uric acid", ""), "Family history of diabetes": ("Family history of diabetes", ""),
             "Urine markers": ("Urine markers", "")}
FAMILY_NAMES = {"Person": ("Person", ""), "Body": ("Body", ""), "Behaviour": ("Behaviour", ""),
                "Mind and pain": ("Mind and pain", ""), "Clinical and laboratory": ("Clinical and laboratory", "")}
OUTCOME_NAMES = {"diabetes": ("Diabetes or prediabetes", ""), "metabolic syndrome": ("Metabolic syndrome", ""),
                 "obesity": ("Obesity", ""), "depression": ("Depression", ""), "suicide": ("Suicidality", ""),
                 "quality of life": ("Quality of life", ""), "cardiovascular": ("Cardiovascular disease", ""),
                 "hypertension": ("Hypertension", ""), "bone": ("Bone", ""), "muscle": ("Muscle", ""),
                 "other": ("Other outcomes", "")}
FIG5_TOPIC = {"METABOLIC_ENDOCRINE": ("Metabolic", ""), "MENTAL_HEALTH": ("Mental health", ""),
              "CARDIOVASCULAR": ("Cardiovascular", ""), "MUSCULOSKELETAL": ("Musculoskeletal", ""), "ORAL_HEALTH": ("Oral health", ""),
              "RESPIRATORY": ("Respiratory", ""), "OTORHINOLARYNGOLOGIC": ("Ear, nose, throat", ""),
              "OPHTHALMOLOGIC": ("Eye health", ""), "KIDNEY_UROLOGIC": ("Kidney and urologic", ""), "HEALTH_BEHAVIOUR": ("Health behaviour", ""),
              "GENERAL_HEALTH_MULTIMORBIDITY": ("General health", ""), "NUTRITION_DIET": ("Nutrition and diet", ""), "CANCER": ("Cancer", ""), "OTHER_TOPICS": ("Other topics", "")}
FIG5_OUTLINE = ()  # author: unexplained teal boxes removed; all five former cells are >= 50%, so their values still show


def fig5_columns(r):
    """Columns of earlier-draft Figure 5: harmonised variables named by at least ten studies in family order, plus one pooled
    'Other' column for each family that has rarer variables."""
    cols = []
    for f in r["families"]:
        cols += [(l, (l,)) for l in r["columns"] if r["family"][l] == f]
        rare = tuple(l for l in r["family"] if r["family"][l] == f and l not in r["columns"])
        if rare:
            cols.append(("OTHER:" + f, rare))
    return cols



def figure_trends(lang="en"):
    """Author (prompt for v8): earlier-draft Figure 5, reporting of selected checklist items by publication period, from
    results/derived/reporting_trends_v8.json (the counts of the detailed appendix table). Three panels: model
    development and evaluation, variable importance, survey design. Points joined by lines; descriptive only."""
    style(lang); ko = lang == "ko"
    t = json.load(open(os.path.join(ROOT, "results/derived/reporting_trends_v8.json")))
    R, n = t["rows"], np.array(t["period_n"], float)
    per = ["≤2019", "2020–22", "2023–24", "2025–26"]
    COLS = [NAVY, TEAL, "#C2410C", "#7B8794"]
    panels = [(T(ko, "A. Development and evaluation", ""),
               [("All preprocessing within the training data", ("Training-only preprocessing", "")),
                ("Validation beyond the development data", ("Temporal/external validation", "")),
                ("Confidence interval for performance", ("Confidence interval", "")),
                ("Calibration reported", ("Calibration", ""))]),
              (T(ko, "B. Variable importance", ""),
               [("Importance ranking produced", ("Importance ranking", "")), ("SHAP used", ("SHAP", "SHAP")),
                ("Ranking stability checked", ("Ranking stability check", ""))]),
              (T(ko, "C. Survey design", ""),
               [("Sampling weights mentioned", ("Survey weights mentioned", "")),
                ("Strata or PSUs used in variance estimation", ("Strata or PSUs", "")),
                ("Weights used in model fitting", ("Survey weights in model fitting", "")),
                ("Weights used in performance evaluation", ("Survey weights in evaluation", ""))])]
    per = ["≤2019", "2020–\n2022", "2023–\n2024", "2025–\n2026"]
    fig = plt.figure(figsize=(FIG_W, 3.4))
    W = .215
    for k, (title, rows) in enumerate(panels):
        x0 = (.075, .445, .765)[k]
        ax = fig.add_axes([x0, .45, W, .42])
        for c, (key, (en, kr)) in enumerate(rows):
            y = 100 * np.array(R[key]) / n
            ax.plot(range(4), y, color=COLS[c], lw=1.8, marker="o", ms=3.6, zorder=3,
                    label=f"{T(ko, en, kr)} ({y[0]:.0f}→{y[-1]:.0f})")
        ax.set_xlim(-.25, 3.25); ax.set_ylim(0, 100); ax.set_yticks([0, 25, 50, 75, 100])
        ax.set_xticks(range(4)); ax.set_xticklabels(per, fontsize=FS_TICK - 2.2, linespacing=.95)
        ax.tick_params(axis="y", labelsize=FS_TICK - 1.8)
        if k == 0:
            ax.set_ylabel(T(ko, "Core studies reporting (%)", ""), fontsize=FS_TICK - 1.6)
        [ax.spines[s_].set_visible(False) for s_ in ("top", "right")]; grid(ax, "y")
        ax.legend(frameon=False, loc="upper left", bbox_to_anchor=(-.05, -.24), fontsize=FS_TICK - 2.2, handlelength=1.4,
                  labelspacing=.25, borderaxespad=0)
        fig.text(x0 - .05, .975, title, fontsize=FS_TITLE - 2.0, weight="bold", va="top")
    save(fig, "fig8_reporting_trends", ko, tight=True)



def _trend_figure(panels, ko, name, ylabel):
    """Shared layout of the v9 trend figures: three panels of percentages by publication period, points joined by
    lines, legends below with the first and last values. panels: (title, [(label_en, label_ko, [4 values]), ...])."""
    COLS = [NAVY, TEAL, "#C2410C", "#7B8794", "#A16207"]
    per = ["≤2019", "2020–\n2022", "2023–\n2024", "2025–\n2026"]
    fig = plt.figure(figsize=(FIG_W, 3.55))
    W = .205
    for k, (title, rows) in enumerate(panels):
        x0 = (.075, .43, .785)[k]
        ax = fig.add_axes([x0, .47, W, .40])
        for c, (en, kr, y) in enumerate(rows):
            ax.plot(range(4), y, color=COLS[c], lw=1.8, marker="o", ms=3.6, zorder=3, label=f"{T(ko, en, kr)} ({y[0]:.0f}→{y[-1]:.0f})")
        ax.set_xlim(-.25, 3.25); ax.set_ylim(0, 100); ax.set_yticks([0, 25, 50, 75, 100])
        ax.set_xticks(range(4)); ax.set_xticklabels(per, fontsize=FS_TICK - 2.2, linespacing=.95)
        ax.tick_params(axis="y", labelsize=FS_TICK - 1.8)
        if k == 0:
            ax.set_ylabel(ylabel, fontsize=FS_TICK - 1.6)
        [ax.spines[s_].set_visible(False) for s_ in ("top", "right")]; grid(ax, "y")
        ax.legend(frameon=False, loc="upper left", bbox_to_anchor=(-.05, -.26), fontsize=FS_TICK - (2.3 if ko else 2.7), handlelength=1.4,
                  labelspacing=.25, borderaxespad=0)
        fig.text(x0 - .05, .975, title, fontsize=FS_TITLE - 2.0, weight="bold", va="top")
    save(fig, name, ko, tight=True)


def _trend_data():
    t = json.load(open(os.path.join(ROOT, "results/derived/reporting_trends_v9.json")))
    n = np.array(t["period_n"], float)
    return (lambda key: list(100 * np.array(t["rows"][key]) / n)), t["pct"]



TRIPOD_ELEMENTS = [("Title", ""), ("Abstract", ""), ("Objective and intended use", ""),
                   ("Data source and design", ""), ("Eligibility and selection", ""),
                   ("Outcome definition, timing", ""), ("Predictor definition, timing", ""),
                   ("Sample and event counts", ""), ("Sample-size rationale", ""),
                   ("Missing-data methods", ""), ("Preprocessing and development", ""),
                   ("Hyperparameters, tuning", ""), ("Internal validation", ""),
                   ("Measures, thresholds", ""), ("Participant flow", ""),
                   ("Performance and uncertainty", ""), ("Final model reusable", ""),
                   ("Limitations", ""), ("Registration, data, code", "")]


def _period_of_core():
    import claim_evidence_analysis as _ce
    yr = {q["id"]: q["year"] for q in data()["literature_map"]}
    per = lambda y: 0 if y <= 2019 else 1 if y <= 2022 else 2 if y <= 2024 else 3
    return [(d, per(yr[d["study_id"]])) for d in _ce.CORE]


def _small_multiples(sections, ko, name, legend=None, ncol=5):
    """Author: one small panel per item (percent by publication period, 0-100). sections:
    (title, [(label, [series: (values, colour, style)]), ...]). legend: [(label, colour, style)] drawn once at the top."""
    import textwrap
    per = ["≤19", "20–\n22", "23–\n24", "25–\n26"]
    PW, PH, GX, GY, ST = FIG_W / ncol, .82, .0, .52, .30  # inches: panel cell width/height, gaps, section title
    rows = sum((len(items) + ncol - 1) // ncol for _, items in sections)
    H = .15 + (.22 if legend else 0) + len(sections) * ST + rows * (PH + GY) + .1
    fig = plt.figure(figsize=(FIG_W, H))
    fy = lambda yin: 1 - yin / H
    y = .1
    if legend:
        for k, (lab, col, ls) in enumerate(legend):
            fig.add_artist(Line2D([.02 + k * .3, .06 + k * .3], [fy(y + .07)] * 2, color=col, ls=ls, lw=1.6))
            fig.text(.065 + k * .3, fy(y + .07), lab, fontsize=FS_TICK - 2.0, va="center")
        y += .22
    for title, items in sections:
        fig.text(.01, fy(y + .02), title, fontsize=FS_TITLE - 2.2, weight="bold", va="top")
        y += ST
        for i, (lab, series) in enumerate(items):
            r, c = divmod(i, ncol)
            top = y + r * (PH + GY)
            ax = fig.add_axes([(c * PW + .30) / FIG_W, fy(top + .12 + PH - .02), (PW - .42) / FIG_W, (PH - .14) / H])
            for vals, col, ls in series:
                ax.plot(range(4), vals, color=col, ls=ls, lw=1.5, marker="o", ms=2.6, zorder=3)
            ax.set_ylim(0, 100); ax.set_xlim(-.3, 3.3); ax.set_yticks([0, 50, 100])
            ax.set_xticks(range(4)); ax.set_xticklabels(per, fontsize=FS_TICK - 3.6, linespacing=.85)
            ax.tick_params(axis="y", labelsize=FS_TICK - 3.2, length=2, pad=1); ax.tick_params(axis="x", length=2, pad=1)
            [ax.spines[s_].set_visible(False) for s_ in ("top", "right")]; grid(ax, "y")
            fig.text((c * PW + .30) / FIG_W, fy(top + .1), "\n".join(textwrap.wrap(lab, 22 if not ko else 13)), fontsize=FS_TICK - 2.6, va="bottom", ha="left", linespacing=.95)
        y += ((len(items) + ncol - 1) // ncol) * (PH + GY)
    save(fig, name, ko, tight=True)


def figure_existing_frameworks(lang="en"):
    """v9 Figure 5 (author: one panel per item): TRIPOD+AI elements, selected TRIPOD+AI-related practices and
    PROBAST+AI domains by publication period."""
    import make_streamlined_figures as _ms
    style(lang); ko = lang == "ko"
    SP = _period_of_core(); n = np.array([sum(p == k for _, p in SP) for k in range(4)], float)
    def pct(f):
        return list(100 * np.array([sum(bool(f(d)) for d, p in SP if p == k) for k in range(4)]) / n)
    tri = []
    for i, (en, kr) in enumerate(TRIPOD_ELEMENTS, 1):
        key = f"REP{i:02d}"
        tri.append((T(ko, en, kr), [(pct(lambda d: _ms.first(d, key) in ("R", "P")), "#9DC9C4", "--"),
                                     (pct(lambda d: _ms.first(d, key) == "R"), NAVY, "-")]))
    R, _ = _trend_data()
    items = [(T(ko, "Confidence interval", ""), "Confidence interval for performance"),
             (T(ko, "Temporal/external validation", ""), "Validation beyond the development data"),
             (T(ko, "Calibration", ""), "Calibration reported"), (T(ko, "Code shared or linked", ""), "Analysis code shared"),
             (T(ko, "Final model specified", ""), "Final model fully specified")]
    sel = [(lab, [(R(k), TEAL, "-")]) for lab, k in items]
    def unit_pct(field, val):
        out = []
        for k in range(4):
            v = [x for d, p in SP if p == k for x in _ms.flat_values(d, field) if x != "NA"]
            out.append(100 * sum(x == val for x in v) / len(v))
        return out
    prob = [(T(ko, "Development: low quality", ""), [(unit_pct("PD_OVERALL", "LOW"), "#C2410C", "-")])]
    for i, (en, kr) in enumerate([("participants", ""), ("predictors", ""), ("outcome", ""), ("analysis", "")], 1):
        prob.append((T(ko, f"Evaluation: {en}", f": {kr}"), [(unit_pct(f"PE_D{i}", "HIGH"), "#C2410C", "-")]))
    prob.append((T(ko, "Evaluation: overall", ""), [(unit_pct("PE_OVERALL", "HIGH"), "#C2410C", "-")]))
    _small_multiples([(T(ko, "A. TRIPOD+AI reporting elements (% of studies)", ""), tri),
                      (T(ko, "B. Selected practices related to TRIPOD+AI (% of studies)", ""), sel),
                      (T(ko, "C. PROBAST+AI: low quality or high risk (% of model units)", ""), prob)],
                     ko, "fig9_existing_frameworks",
                     legend=[(T(ko, "A: reported completely", ""), NAVY, "-"), (T(ko, "A: completely or partly", ""), "#9DC9C4", "--")])


def figure_checklist_trends(lang="en"):
    """v9 Figure 6 (author: one panel per item): KNHANES-specific checklist items by publication period."""
    style(lang); ko = lang == "ko"; R, _ = _trend_data()
    def sec(rows, col):
        return [(T(ko, en, kr), [(R(key), col, "-")]) for en, kr, key in rows]
    _small_multiples([(T(ko, "A. Survey design (% of studies)", ""), sec([
                          ("Survey weights mentioned", "", "Sampling weights mentioned"),
                          ("Survey weights in model fitting", "", "Weights used in model fitting"),
                          ("Survey weights in evaluation", "", "Weights used in performance evaluation"),
                          ("Strata or PSUs", "", "Strata or PSUs used in variance estimation"),
                          ("Combined-year survey weights", "", "Combined-year weights used")], NAVY)),
                      (T(ko, "B. Data and preprocessing (% of studies)", ""), sec([
                          ("Training-only preprocessing", "", "All preprocessing within the training data"),
                          ("Step before the split", "", "At least one preprocessing step before the split"),
                          ("Cut-off basis stated", "", "Basis of the outcome cut-off reported"),
                          ("Predictor set rebuildable", "", "Predictor set rebuildable from the report"),
                          ("Outcome rebuildable", "", "Outcome rebuildable from the report")], TEAL)),
                      (T(ko, "C. Variable importance (% of studies)", ""), sec([
                          ("Importance ranking", "", "Importance ranking produced"), ("SHAP", "SHAP", "SHAP used"),
                          ("Ranking stability check", "", "Ranking stability checked"),
                          ("Ranking for reduced set", "", "Ranking used for a reduced predictor set"),
                          ("Ranking for later analysis", "", "Ranking guided a later statistical analysis")], "#C2410C"))],
                     ko, "fig10_checklist_trends")



def figure_refined_scores(lang="en"):
    """v11 Figure 5 (author, layout 2): one row per refined TRIPOD+AI item. Middle column: distribution of the
    TRIPOD+AI judgement (3 levels); right column: distribution of the refined score (% of applicable KNHANES
    sub-items reported, 10-point bins), bars stacked by the TRIPOD+AI judgement. Last row: overall distributions."""
    style(lang); ko = lang == "ko"
    t = json.load(open(os.path.join(ROOT, "results/derived/refined_scores_v11.json")))
    S = t["studies"]
    names = {"data": ("4. Data source and design", ""), "outcome": ("6. Outcome", ""),
             "predictors": ("7. Predictors", ""), "missing": ("10. Missing data", ""),
             "development": ("11. Preprocessing,\ndevelopment", ""),
             "tuning_validation": ("12. Tuning and validation", ""), "performance": ("16. Performance", "")}
    levels = [("Not reported", T(ko, "Not reported", ""), "#C9CED6"), ("Partly reported", T(ko, "Partly", ""), "#8FC3BD"),
              ("Reported", T(ko, "Complete", ""), NAVY)]
    doms = t["domains"]; nrow = len(doms) + 1
    RH, TOP, BOT = .8, .55, .5
    H = TOP + nrow * RH + BOT
    fig = plt.figure(figsize=(FIG_W, H))
    fy = lambda yin: 1 - yin / H
    X1, W1, X2, W2 = 2.05, 1.55, 3.95, 3.25  # inches
    fs = FS_TICK - 2.4
    fig.text(X1 / FIG_W, fy(.18), T(ko, "TRIPOD+AI judgement", ""), fontsize=FS_TITLE - 2.6, weight="bold", va="bottom")
    fig.text(X2 / FIG_W, fy(.18), T(ko, "KNHANES checklist: refined score (% of sub-items)", ""),
             fontsize=FS_TITLE - 2.6, weight="bold", va="bottom")
    for k, (lev, lab, col) in enumerate(levels):  # legend for the stacking
        fig.add_artist(matplotlib.patches.Rectangle(((X2 + 1.15 * k) / FIG_W, fy(.38)), .12 / FIG_W, .09 / H, color=col, transform=fig.transFigure))
        fig.text((X2 + 1.15 * k + .16) / FIG_W, fy(.335), lab, fontsize=fs, va="center")
    bins = np.arange(0, 101, 10)
    for r, dom in enumerate(doms):
        y0 = TOP + r * RH
        key = dom["key"]
        fig.text(.05 / FIG_W, fy(y0 + RH * .45), T(ko, *names[key]) + T(ko, f"\n({len(dom['subitems'])} sub-items)", f"\n(  {len(dom['subitems'])})"),
                 fontsize=fs + .4, va="center", linespacing=1.0)
        a1 = fig.add_axes([X1 / FIG_W, fy(y0 + RH - .12), W1 / FIG_W, (RH - .22) / H])
        a2 = fig.add_axes([X2 / FIG_W, fy(y0 + RH - .12), W2 / FIG_W, (RH - .22) / H])
        cnt = [sum(S[i][key]["tripod"] == lev for i in S) for lev, _, _ in levels]
        a1.bar(range(3), cnt, color=[c for _, _, c in levels], width=.7)
        for x, c in enumerate(cnt):
            a1.text(x, c + 4, str(c), ha="center", fontsize=fs - .4)
        a1.set_xticks(range(3)); a1.set_xticklabels([l for _, l, _ in levels] if r == len(doms) - 1 else [], fontsize=fs - .2)
        a1.set_ylim(0, 215); a1.set_yticks([0, 100, 200]); a1.tick_params(axis="y", labelsize=fs - .4, length=2, pad=1)
        bottom = np.zeros(len(bins) - 1)
        for lev, _, col in levels:
            v = [min(S[i][key]["score"], 99.999) for i in S if S[i][key]["tripod"] == lev]
            h = np.histogram(v, bins=bins)[0]
            a2.bar(bins[:-1] + 5, h, bottom=bottom, width=8.6, color=col)
            bottom += h
        lv = len({S[i][key]['score'] for i in S})
        a2.text(99, 190, T(ko, f'{lv} distinct scores vs 3 judgements', f' {lv} (TRIPOD+AI  3)'), ha='right', va='top', fontsize=fs - .2, color=DGREY)
        a2.set_xlim(0, 100); a2.set_xticks(bins); a2.set_xticklabels([f"{b}" for b in bins] if r == len(doms) - 1 else [], fontsize=fs - .4)
        a2.set_ylim(0, 215); a2.set_yticks([0, 100, 200]); a2.tick_params(axis="y", labelsize=fs - .4, length=2, pad=1)
        for a in (a1, a2):
            [a.spines[s_].set_visible(False) for s_ in ("top", "right")]; grid(a, "y")
    # last row: overall
    y0 = TOP + len(doms) * RH + .12
    fig.add_artist(Line2D([.02, .98], [fy(y0 - .05)] * 2, color=DGREY, lw=.6))
    fig.text(.05 / FIG_W, fy(y0 + RH * .45), T(ko, "Overall", ""), fontsize=fs + .6, weight="bold", va="center")
    a1 = fig.add_axes([X1 / FIG_W, fy(y0 + RH - .12), W1 / FIG_W, (RH - .22) / H])
    a2 = fig.add_axes([X2 / FIG_W, fy(y0 + RH - .12), W2 / FIG_W, (RH - .22) / H])
    tri = [S[i]["tripod_complete_19"] for i in S]
    a1.hist(tri, bins=np.arange(-.5, 20, 1), color=NAVY, rwidth=.85)
    a1.set_xlim(-.5, 19.5); a1.set_xticks([0, 5, 10, 15, 19]); a1.tick_params(labelsize=fs - .4, length=2, pad=1)
    a1.set_xlabel(T(ko, "Elements complete (of 19)", ""), fontsize=fs, labelpad=1)
    ref = [100 * sum(len(S[i][d["key"]]["met"]) for d in doms) / sum(S[i][d["key"]]["applicable"] for d in doms) for i in S]
    a2.hist(ref, bins=np.arange(0, 101, 2.5), color=TEAL, rwidth=.85)
    a2.set_xlim(0, 100); a2.set_xticks(bins); a2.tick_params(labelsize=fs - .4, length=2, pad=1)
    a2.set_xlabel(T(ko, "Sub-items reported (% of all applicable)", ""), fontsize=fs, labelpad=1)
    for a in (a1, a2):
        [a.spines[s_].set_visible(False) for s_ in ("top", "right")]; grid(a, "y")
    fig.text(X1 / FIG_W - .045, fy(y0 + RH * .5), T(ko, "Studies", ""), rotation=90, fontsize=fs, va="center")
    save(fig, "fig11_refined_scores", ko, tight=True)



def figure_checklist_v12(lang="en"):
    """v12 Figure 5 (author): rows = TRIPOD+AI items with at least two scored checklist items, then the new
    survey-design and variable-importance groups. Middle: TRIPOD+AI judgement (3 levels); right: checklist score (% of
    applicable scored items reported), stacked by the TRIPOD+AI judgement. Last row: overall TRIPOD+AI elements complete
    (of 19) and per-study checklist scores for all items and for items needed for reproduction."""
    import checklist_v12 as CK
    style(lang); ko = lang == "ko"
    t = json.load(open(os.path.join(ROOT, "results/derived/checklist_v12_scores.json")))
    items, S = t["items"], t["studies"]
    groups = []
    for key in list(range(1, 20)) + ["survey", "importance"]:
        idx = [str(i["idx"]) for i in items if i["tripod"] == key and i["scored"]]
        if len(idx) >= 2:
            groups.append((key, idx))
    levels = [("Not reported", T(ko, "Not reported", ""), "#C9CED6"), ("Partly reported", T(ko, "Partly", ""), "#8FC3BD"),
              ("Reported", T(ko, "Complete", ""), NAVY)]
    RH, TOP, BOT = .62, .55, .55
    nrow = len(groups) + 1
    H = TOP + nrow * RH + BOT + .1
    fig = plt.figure(figsize=(FIG_W, H))
    fy = lambda yin: 1 - yin / H
    X1, W1, X2, W2 = 2.05, 1.55, 3.95, 3.25
    fs = FS_TICK - 2.4
    fig.text(X1 / FIG_W, fy(.18), T(ko, "TRIPOD+AI judgement", ""), fontsize=FS_TITLE - 2.6, weight="bold", va="bottom")
    fig.text(X2 / FIG_W, fy(.18), T(ko, "KNHANES checklist score (% of applicable items)", ""), fontsize=FS_TITLE - 2.6, weight="bold", va="bottom")
    for k, (lev, lab, col) in enumerate(levels):
        fig.add_artist(matplotlib.patches.Rectangle(((X2 + 1.15 * k) / FIG_W, fy(.38)), .12 / FIG_W, .09 / H, color=col, transform=fig.transFigure))
        fig.text((X2 + 1.15 * k + .16) / FIG_W, fy(.335), lab, fontsize=fs, va="center")
    bins = np.arange(0, 101, 10)
    def score(sid, idx):
        v = [S[sid]["items"][i] for i in idx if i in S[sid]["items"]]
        return 100 * sum(v) / len(v) if v else None
    for r, (key, idx) in enumerate(groups):
        y0 = TOP + r * RH
        if isinstance(key, int):
            lab = f"{key}. " + T(ko, CK.TRIPOD[key - 1][1], CK.TRIPOD[key - 1][0])
        else:
            lab = T(ko, "(New) ", "") + T(ko, CK.GROUPS[key][1], CK.GROUPS[key][0])
        fig.text(.05 / FIG_W, fy(y0 + RH * .45), "\n".join(__import__("textwrap").wrap(lab, 24 if not ko else 14)) + T(ko, f"\n({len(idx)} items)", f"\n( {len(idx)})"),
                 fontsize=fs + .2, va="center", linespacing=1.0)
        a1 = fig.add_axes([X1 / FIG_W, fy(y0 + RH - .1), W1 / FIG_W, (RH - .2) / H])
        a2 = fig.add_axes([X2 / FIG_W, fy(y0 + RH - .1), W2 / FIG_W, (RH - .2) / H])
        if isinstance(key, int):
            cnt = [sum(S[s]["tripod"][str(key)] == lev for s in S) for lev, _, _ in levels]
            a1.bar(range(3), cnt, color=[c for _, _, c in levels], width=.7)
            for x, c in enumerate(cnt):
                a1.text(x, c + 5, str(c), ha="center", fontsize=fs - .5)
        else:
            a1.text(1, 100, T(ko, "No TRIPOD+AI item", ""), ha="center", va="center", fontsize=fs, color=DGREY)
        a1.set_xlim(-.6, 2.6); a1.set_ylim(0, 215); a1.set_yticks([0, 100, 200]); a1.tick_params(axis="y", labelsize=fs - .5, length=2, pad=1)
        a1.set_xticks(range(3)); a1.set_xticklabels([l for _, l, _ in levels] if r == len(groups) - 1 else [], fontsize=fs - .3)
        bottom = np.zeros(len(bins) - 1); vals = []
        for lev, _, col in levels:
            v = [min(score(s, idx), 99.999) for s in S if score(s, idx) is not None and (not isinstance(key, int) or S[s]["tripod"][str(key)] == lev)]
            if not isinstance(key, int) and lev != "Reported":
                continue
            vals += v
            h = np.histogram(v, bins=bins)[0]
            a2.bar(bins[:-1] + 5, h, bottom=bottom, width=8.6, color=col if isinstance(key, int) else TEAL)
            bottom += h
        nd = len({round(x, 3) for x in vals})
        a2.text(99, 205, T(ko, f"{nd} distinct scores", f" {nd}"), ha="right", va="top", fontsize=fs - .3, color=DGREY)
        a2.set_xlim(0, 100); a2.set_xticks(bins); a2.set_xticklabels([str(b) for b in bins] if r == len(groups) - 1 else [], fontsize=fs - .5)
        a2.set_ylim(0, 215); a2.set_yticks([0, 100, 200]); a2.tick_params(axis="y", labelsize=fs - .5, length=2, pad=1)
        for a in (a1, a2):
            [a.spines[s_].set_visible(False) for s_ in ("top", "right")]; grid(a, "y")
    y0 = TOP + len(groups) * RH + .2
    fig.add_artist(Line2D([.02, .98], [fy(y0 - .08)] * 2, color=DGREY, lw=.6))
    fig.text(.05 / FIG_W, fy(y0 + RH * .45), T(ko, "Overall", ""), fontsize=fs + .6, weight="bold", va="center")
    a1 = fig.add_axes([X1 / FIG_W, fy(y0 + RH - .1), W1 / FIG_W, (RH - .2) / H])
    a2 = fig.add_axes([X2 / FIG_W, fy(y0 + RH - .1), W2 / FIG_W, (RH - .2) / H])
    a1.hist([sum(S[s]["tripod"][str(i)] == "Reported" for i in range(1, 20)) for s in S], bins=np.arange(-.5, 20, 1), color=NAVY, rwidth=.85)
    a1.set_xlim(-.5, 19.5); a1.set_xticks([0, 5, 10, 15, 19]); a1.tick_params(labelsize=fs - .5, length=2, pad=1)
    a1.set_xlabel(T(ko, "TRIPOD+AI elements complete (of 19)", ""), fontsize=fs, labelpad=1)
    allidx = [str(i["idx"]) for i in items if i["scored"]]; repidx = [str(i["idx"]) for i in items if i["scored"] and i["repro"]]
    a2.hist([score(s, allidx) for s in S], bins=np.arange(0, 101, 2.5), color="#8FC3BD", rwidth=.85, label=T(ko, "All checklist items", ""))
    a2.hist([score(s, repidx) for s in S], bins=np.arange(0, 101, 2.5), histtype="step", color=NAVY, lw=1.5, label=T(ko, "Items needed for reproduction", ""))
    a2.set_xlim(0, 100); a2.set_xticks(bins); a2.tick_params(labelsize=fs - .5, length=2, pad=1)
    a2.set_xlabel(T(ko, "Items reported (% of applicable)", ""), fontsize=fs, labelpad=1)
    a2.legend(frameon=False, fontsize=fs - .6, loc="lower left", bbox_to_anchor=(0, 1.0), ncol=2, handlelength=1.2, borderaxespad=.1)
    for a in (a1, a2):
        [a.spines[s_].set_visible(False) for s_ in ("top", "right")]; grid(a, "y")
    save(fig, "fig12_checklist_scores", ko, tight=True)



def figure_checklist_v13(lang="en"):
    """v13 Figure 5 (survey-design items now refined under their elements)
    v12 doc: (author): rows = TRIPOD+AI items with at least two scored checklist items, then the new
    survey-design and variable-importance groups. Middle: TRIPOD+AI judgement (3 levels); right: checklist score (% of
    applicable scored items reported), stacked by the TRIPOD+AI judgement. Last row: overall TRIPOD+AI elements complete
    (of 19) and per-study checklist scores for all items and for items needed for reproduction."""
    import checklist_v13 as CK
    style(lang); ko = lang == "ko"
    t = json.load(open(os.path.join(ROOT, "results/derived/checklist_v13_scores.json")))
    items, S = t["items"], t["studies"]
    groups = []
    for key in list(range(1, 20)) + ["importance"]:
        idx = [str(i["idx"]) for i in items if i["tripod"] == key and i["scored"]]
        if len(idx) >= 2:
            groups.append((key, idx))
    levels = [("Not reported", T(ko, "Not reported", ""), "#C9CED6"), ("Partly reported", T(ko, "Partly", ""), "#8FC3BD"),
              ("Reported", T(ko, "Complete", ""), NAVY)]
    RH, TOP, BOT = .62, .55, .55
    nrow = len(groups) + 1
    H = TOP + nrow * RH + BOT + .1
    fig = plt.figure(figsize=(FIG_W, H))
    fy = lambda yin: 1 - yin / H
    X1, W1, X2, W2 = 2.05, 1.55, 3.95, 3.25
    fs = FS_TICK - 2.4
    fig.text(X1 / FIG_W, fy(.18), T(ko, "TRIPOD+AI judgement", ""), fontsize=FS_TITLE - 2.6, weight="bold", va="bottom")
    fig.text(X2 / FIG_W, fy(.18), T(ko, "KNHANES checklist score (% of applicable items)", ""), fontsize=FS_TITLE - 2.6, weight="bold", va="bottom")
    for k, (lev, lab, col) in enumerate(levels):
        fig.add_artist(matplotlib.patches.Rectangle(((X2 + 1.15 * k) / FIG_W, fy(.38)), .12 / FIG_W, .09 / H, color=col, transform=fig.transFigure))
        fig.text((X2 + 1.15 * k + .16) / FIG_W, fy(.335), lab, fontsize=fs, va="center")
    bins = np.arange(0, 101, 10)
    def score(sid, idx):
        v = [S[sid]["items"][i] for i in idx if i in S[sid]["items"]]
        return 100 * sum(v) / len(v) if v else None
    for r, (key, idx) in enumerate(groups):
        y0 = TOP + r * RH
        if isinstance(key, int):
            lab = f"{key}. " + T(ko, CK.TRIPOD[key - 1][1], CK.TRIPOD[key - 1][0])
        else:
            lab = T(ko, "(New) ", "") + T(ko, CK.GROUPS[key][1], CK.GROUPS[key][0])
        fig.text(.05 / FIG_W, fy(y0 + RH * .45), "\n".join(__import__("textwrap").wrap(lab, 24 if not ko else 14)) + T(ko, f"\n({len(idx)} items)", f"\n( {len(idx)})"),
                 fontsize=fs + .2, va="center", linespacing=1.0)
        a1 = fig.add_axes([X1 / FIG_W, fy(y0 + RH - .1), W1 / FIG_W, (RH - .2) / H])
        a2 = fig.add_axes([X2 / FIG_W, fy(y0 + RH - .1), W2 / FIG_W, (RH - .2) / H])
        if isinstance(key, int):
            cnt = [sum(S[s]["tripod"][str(key)] == lev for s in S) for lev, _, _ in levels]
            a1.bar(range(3), cnt, color=[c for _, _, c in levels], width=.7)
            for x, c in enumerate(cnt):
                a1.text(x, c + 5, str(c), ha="center", fontsize=fs - .5)
        else:
            a1.text(1, 100, T(ko, "No TRIPOD+AI item", ""), ha="center", va="center", fontsize=fs, color=DGREY)
        a1.set_xlim(-.6, 2.6); a1.set_ylim(0, 215); a1.set_yticks([0, 100, 200]); a1.tick_params(axis="y", labelsize=fs - .5, length=2, pad=1)
        a1.set_xticks(range(3)); a1.set_xticklabels([l for _, l, _ in levels] if r == len(groups) - 1 else [], fontsize=fs - .3)
        bottom = np.zeros(len(bins) - 1); vals = []
        for lev, _, col in levels:
            v = [min(score(s, idx), 99.999) for s in S if score(s, idx) is not None and (not isinstance(key, int) or S[s]["tripod"][str(key)] == lev)]
            if not isinstance(key, int) and lev != "Reported":
                continue
            vals += v
            h = np.histogram(v, bins=bins)[0]
            a2.bar(bins[:-1] + 5, h, bottom=bottom, width=8.6, color=col if isinstance(key, int) else TEAL)
            bottom += h
        nd = len({round(x, 3) for x in vals})
        a2.text(99, 205, T(ko, f"{nd} distinct scores", f" {nd}"), ha="right", va="top", fontsize=fs - .3, color=DGREY)
        a2.set_xlim(0, 100); a2.set_xticks(bins); a2.set_xticklabels([str(b) for b in bins] if r == len(groups) - 1 else [], fontsize=fs - .5)
        a2.set_ylim(0, 215); a2.set_yticks([0, 100, 200]); a2.tick_params(axis="y", labelsize=fs - .5, length=2, pad=1)
        for a in (a1, a2):
            [a.spines[s_].set_visible(False) for s_ in ("top", "right")]; grid(a, "y")
    y0 = TOP + len(groups) * RH + .2
    fig.add_artist(Line2D([.02, .98], [fy(y0 - .08)] * 2, color=DGREY, lw=.6))
    fig.text(.05 / FIG_W, fy(y0 + RH * .45), T(ko, "Overall", ""), fontsize=fs + .6, weight="bold", va="center")
    a1 = fig.add_axes([X1 / FIG_W, fy(y0 + RH - .1), W1 / FIG_W, (RH - .2) / H])
    a2 = fig.add_axes([X2 / FIG_W, fy(y0 + RH - .1), W2 / FIG_W, (RH - .2) / H])
    a1.hist([sum(S[s]["tripod"][str(i)] == "Reported" for i in range(1, 20)) for s in S], bins=np.arange(-.5, 20, 1), color=NAVY, rwidth=.85)
    a1.set_xlim(-.5, 19.5); a1.set_xticks([0, 5, 10, 15, 19]); a1.tick_params(labelsize=fs - .5, length=2, pad=1)
    a1.set_xlabel(T(ko, "TRIPOD+AI elements complete (of 19)", ""), fontsize=fs, labelpad=1)
    allidx = [str(i["idx"]) for i in items if i["scored"]]; repidx = [str(i["idx"]) for i in items if i["scored"] and i["repro"]]
    a2.hist([score(s, allidx) for s in S], bins=np.arange(0, 101, 2.5), color="#8FC3BD", rwidth=.85, label=T(ko, "All checklist items", ""))
    a2.hist([score(s, repidx) for s in S], bins=np.arange(0, 101, 2.5), histtype="step", color=NAVY, lw=1.5, label=T(ko, "Items needed for reproduction", ""))
    a2.set_xlim(0, 100); a2.set_xticks(bins); a2.tick_params(labelsize=fs - .5, length=2, pad=1)
    a2.set_xlabel(T(ko, "Items reported (% of applicable)", ""), fontsize=fs, labelpad=1)
    a2.legend(frameon=False, fontsize=fs - .6, loc="lower left", bbox_to_anchor=(0, 1.0), ncol=2, handlelength=1.2, borderaxespad=.1)
    for a in (a1, a2):
        [a.spines[s_].set_visible(False) for s_ in ("top", "right")]; grid(a, "y")
    save(fig, "fig13_checklist_scores", ko, tight=True)



def figure_checklist_v14(lang="en"):
    """v13 Figure 5 (survey-design items now refined under their elements)
    v12 doc: (author): rows = TRIPOD+AI items with at least two scored checklist items, then the new
    survey-design and variable-importance groups. Middle: TRIPOD+AI judgement (3 levels); right: checklist score (% of
    applicable scored items reported), stacked by the TRIPOD+AI judgement. Last row: overall TRIPOD+AI elements complete
    (of 19) and per-study checklist scores for all items and for items needed for reproduction."""
    import checklist_v14 as CK
    style(lang); ko = lang == "ko"
    t = json.load(open(os.path.join(ROOT, "results/derived/checklist_v14_scores.json")))
    items, S = t["items"], t["studies"]
    groups = []
    for key in list(range(1, 20)) + ["importance"]:
        idx = [str(i["idx"]) for i in items if i["tripod"] == key and i["scored"]]
        if len(idx) >= 2:
            groups.append((key, idx))
    levels = [("Not reported", T(ko, "Not reported", ""), "#C9CED6"), ("Partly reported", T(ko, "Partly", ""), "#8FC3BD"),
              ("Reported", T(ko, "Complete", ""), NAVY)]
    RH, TOP, BOT = .62, .55, .55
    nrow = len(groups) + 1
    H = TOP + nrow * RH + BOT + .1
    fig = plt.figure(figsize=(FIG_W, H))
    fy = lambda yin: 1 - yin / H
    X1, W1, X2, W2 = 2.05, 1.55, 3.95, 3.25
    fs = FS_TICK - 2.4
    fig.text(X1 / FIG_W, fy(.18), T(ko, "TRIPOD+AI judgement", ""), fontsize=FS_TITLE - 2.6, weight="bold", va="bottom")
    fig.text(X2 / FIG_W, fy(.18), T(ko, "Core checklist score (% of applicable items met)", ""), fontsize=FS_TITLE - 2.6, weight="bold", va="bottom")
    for k, (lev, lab, col) in enumerate(levels):
        fig.add_artist(matplotlib.patches.Rectangle(((X2 + 1.15 * k) / FIG_W, fy(.38)), .12 / FIG_W, .09 / H, color=col, transform=fig.transFigure))
        fig.text((X2 + 1.15 * k + .16) / FIG_W, fy(.335), lab, fontsize=fs, va="center")
    bins = np.arange(0, 101, 10)
    def score(sid, idx):
        v = [S[sid]["items"][i] for i in idx if i in S[sid]["items"]]
        return 100 * sum(v) / len(v) if v else None
    for r, (key, idx) in enumerate(groups):
        y0 = TOP + r * RH
        if isinstance(key, int):
            lab = f"{key}. " + T(ko, CK.TRIPOD[key - 1][1], CK.TRIPOD[key - 1][0]) if False else f"{key}. " + T(ko, __import__("checklist_v12").TRIPOD[key - 1][1], __import__("checklist_v12").TRIPOD[key - 1][0])
        else:
            lab = T(ko, "(New) ", "") + T(ko, CK.GROUPS[key][1], CK.GROUPS[key][0])
        fig.text(.05 / FIG_W, fy(y0 + RH * .45), "\n".join(__import__("textwrap").wrap(lab, 24 if not ko else 14)) + T(ko, f"\n({len(idx)} items)", f"\n( {len(idx)})"),
                 fontsize=fs + .2, va="center", linespacing=1.0)
        a1 = fig.add_axes([X1 / FIG_W, fy(y0 + RH - .1), W1 / FIG_W, (RH - .2) / H])
        a2 = fig.add_axes([X2 / FIG_W, fy(y0 + RH - .1), W2 / FIG_W, (RH - .2) / H])
        if isinstance(key, int):
            cnt = [sum(S[s]["tripod"][str(key)] == lev for s in S) for lev, _, _ in levels]
            a1.bar(range(3), cnt, color=[c for _, _, c in levels], width=.7)
            for x, c in enumerate(cnt):
                a1.text(x, c + 5, str(c), ha="center", fontsize=fs - .5)
        else:
            a1.text(1, 100, T(ko, "No TRIPOD+AI item", ""), ha="center", va="center", fontsize=fs, color=DGREY)
        a1.set_xlim(-.6, 2.6); a1.set_ylim(0, 215); a1.set_yticks([0, 100, 200]); a1.tick_params(axis="y", labelsize=fs - .5, length=2, pad=1)
        a1.set_xticks(range(3)); a1.set_xticklabels([l for _, l, _ in levels] if r == len(groups) - 1 else [], fontsize=fs - .3)
        bottom = np.zeros(len(bins) - 1); vals = []
        for lev, _, col in levels:
            v = [min(score(s, idx), 99.999) for s in S if score(s, idx) is not None and (not isinstance(key, int) or S[s]["tripod"][str(key)] == lev)]
            if not isinstance(key, int) and lev != "Reported":
                continue
            vals += v
            h = np.histogram(v, bins=bins)[0]
            a2.bar(bins[:-1] + 5, h, bottom=bottom, width=8.6, color=col if isinstance(key, int) else TEAL)
            bottom += h
        nd = len({round(x, 3) for x in vals})
        a2.text(99, 205, T(ko, f"{nd} distinct scores", f" {nd}"), ha="right", va="top", fontsize=fs - .3, color=DGREY)
        a2.set_xlim(0, 100); a2.set_xticks(bins); a2.set_xticklabels([str(b) for b in bins] if r == len(groups) - 1 else [], fontsize=fs - .5)
        a2.set_ylim(0, 215); a2.set_yticks([0, 100, 200]); a2.tick_params(axis="y", labelsize=fs - .5, length=2, pad=1)
        for a in (a1, a2):
            [a.spines[s_].set_visible(False) for s_ in ("top", "right")]; grid(a, "y")
    y0 = TOP + len(groups) * RH + .2
    fig.add_artist(Line2D([.02, .98], [fy(y0 - .08)] * 2, color=DGREY, lw=.6))
    fig.text(.05 / FIG_W, fy(y0 + RH * .45), T(ko, "Overall", ""), fontsize=fs + .6, weight="bold", va="center")
    a1 = fig.add_axes([X1 / FIG_W, fy(y0 + RH - .1), W1 / FIG_W, (RH - .2) / H])
    a2 = fig.add_axes([X2 / FIG_W, fy(y0 + RH - .1), W2 / FIG_W, (RH - .2) / H])
    a1.hist([sum(S[s]["tripod"][str(i)] == "Reported" for i in range(1, 20)) for s in S], bins=np.arange(-.5, 20, 1), color=NAVY, rwidth=.85)
    a1.set_xlim(-.5, 19.5); a1.set_xticks([0, 5, 10, 15, 19]); a1.tick_params(labelsize=fs - .5, length=2, pad=1)
    a1.set_xlabel(T(ko, "TRIPOD+AI elements complete (of 19)", ""), fontsize=fs, labelpad=1)
    allidx = [str(i["idx"]) for i in items if i["scored"]]; repidx = [str(i["idx"]) for i in items if i["scored"] and i["repro"]]
    a2.hist([score(s, allidx) for s in S], bins=np.arange(0, 101, 2.5), color="#8FC3BD", rwidth=.85, label=T(ko, "All checklist items", ""))
    a2.hist([score(s, repidx) for s in S], bins=np.arange(0, 101, 2.5), histtype="step", color=NAVY, lw=1.5, label=T(ko, "Items needed for reproduction", ""))
    a2.set_xlim(0, 100); a2.set_xticks(bins); a2.tick_params(labelsize=fs - .5, length=2, pad=1)
    a2.set_xlabel(T(ko, "Items reported (% of applicable)", ""), fontsize=fs, labelpad=1)
    a2.legend(frameon=False, fontsize=fs - .6, loc="lower left", bbox_to_anchor=(0, 1.0), ncol=2, handlelength=1.2, borderaxespad=.1)
    for a in (a1, a2):
        [a.spines[s_].set_visible(False) for s_ in ("top", "right")]; grid(a, "y")
    save(fig, "fig14_checklist_scores", ko, tight=True)



def figure_checklist_items_v14(lang="en"):
    """v14 Figure 5, layout 2 (author): per TRIPOD+AI-derived element, (1) the 3-level TRIPOD+AI judgement,
    (2) each core checklist item as its own box (percentage of applicable studies meeting it, item numbers as in Table 1),
    (3) the distribution of the number of items met per study (0..k). Last row: overall."""
    import checklist_v14 as CK, checklist_v14_table as TB
    from checklist_v12 import TRIPOD
    style(lang); ko = lang == "ko"
    t = json.load(open(os.path.join(ROOT, "results/derived/checklist_v14_scores.json")))
    items, S = t["items"], t["studies"]
    num = {(r[0], r[2]): n for n, r in enumerate(TB.ordered(), 1)}
    groups = []
    for key in list(range(1, 20)) + ["importance"]:
        idx = [i for i in items if i["tripod"] == key and i["scored"]]
        if len(idx) >= 2:
            groups.append((key, sorted(idx, key=lambda i: num[(key, i["item_en"])])))
    levels = [("Not reported", T(ko, "No", ""), "#C9CED6"), ("Partly reported", T(ko, "Part", ""), "#8FC3BD"), ("Reported", T(ko, "Full", ""), NAVY)]
    RH, TOP = .7, .62
    H = TOP + (len(groups) + 1) * RH + .75
    fig = plt.figure(figsize=(FIG_W, H))
    fy = lambda yin: 1 - yin / H
    XA, WA, XB, WB, XC, WC = 1.62, 1.05, 3.0, 2.2, 5.6, 1.5
    fs = FS_TICK - 2.4
    for x, txt in ((XA, T(ko, "TRIPOD+AI\n(3 levels)", "")),
                   (XB, T(ko, "Core items: % meeting each\n(numbers as in Table 1)", "")),
                   (XC, T(ko, "Items met\nper study (0 to k)", ""))):
        fig.text(x / FIG_W, fy(.12), txt, fontsize=FS_TITLE - 2.8, weight="bold", va="top", linespacing=1.05)
    def deco(a):
        [a.spines[s_].set_visible(False) for s_ in ("top", "right")]; grid(a, "y"); a.tick_params(labelsize=fs - .6, length=2, pad=1)
    for r, (key, its) in enumerate(groups):
        y0 = TOP + r * RH
        lab = (f"{key}. " + T(ko, TRIPOD[key - 1][1], TRIPOD[key - 1][0])) if isinstance(key, int) else T(ko, "(New) Variable importance", "")
        fig.text(.05 / FIG_W, fy(y0 + RH * .45), "\n".join(__import__("textwrap").wrap(lab, 20 if not ko else 11)), fontsize=fs + .1, va="center", linespacing=1.0)
        aA = fig.add_axes([XA / FIG_W, fy(y0 + RH - .14), WA / FIG_W, (RH - .26) / H])
        aB = fig.add_axes([XB / FIG_W, fy(y0 + RH - .14), WB / FIG_W, (RH - .26) / H])
        aC = fig.add_axes([XC / FIG_W, fy(y0 + RH - .14), WC / FIG_W, (RH - .26) / H])
        if isinstance(key, int):
            cnt = [100 * sum(S[s]["tripod"][str(key)] == lev for s in S) / len(S) for lev, _, _ in levels]
            aA.bar(range(3), cnt, color=[c for _, _, c in levels], width=.7)
            aA.set_xticks(range(3)); aA.set_xticklabels([l for _, l, _ in levels], fontsize=fs - .6)
        else:
            aA.text(1, 50, T(ko, "No element", ""), ha="center", va="center", fontsize=fs - .3, color=DGREY); aA.set_xticks([])
        aA.set_xlim(-.6, 2.6); aA.set_ylim(0, 100); aA.set_yticks([0, 50, 100]); deco(aA)
        pct = []
        for it in its:
            v = [S[s]["items"][str(it["idx"])] for s in S if str(it["idx"]) in S[s]["items"]]
            pct.append(100 * sum(v) / len(v))
        aB.bar(range(len(its)), pct, color=TEAL, width=.62, edgecolor="#0F5F59", linewidth=.6)
        for x, v in enumerate(pct):
            aB.add_patch(matplotlib.patches.Rectangle((x - .31, 0), .62, 100, fill=False, edgecolor="#9CA3AF", lw=.6))
        aB.set_xticks(range(len(its))); aB.set_xticklabels([str(num[(key, it["item_en"])]) for it in its], fontsize=fs - .5)
        aB.set_xlim(-.6, max(len(its), 5) - .4); aB.set_ylim(0, 100); aB.set_yticks([0, 50, 100]); deco(aB)
        k = len(its)
        met = [sum(S[s]["items"].get(str(it["idx"]), False) for it in its) for s in S if any(str(it["idx"]) in S[s]["items"] for it in its)]
        h = np.bincount(met, minlength=k + 1)
        aC.bar(range(k + 1), 100 * h / len(met), color=NAVY, width=.7)
        aC.set_xticks(range(k + 1)); aC.set_xlim(-.6, max(k, 5) + .6); aC.set_ylim(0, 100); aC.set_yticks([0, 50, 100]); deco(aC)
    y0 = TOP + len(groups) * RH + .18
    fig.add_artist(Line2D([.02, .98], [fy(y0 - .08)] * 2, color=DGREY, lw=.6))
    fig.text(.05 / FIG_W, fy(y0 + RH * .45), T(ko, "Overall", ""), fontsize=fs + .6, weight="bold", va="center")
    aA = fig.add_axes([XA / FIG_W, fy(y0 + RH - .14), (XB + WB - XA) / FIG_W, (RH - .26) / H])
    aC = fig.add_axes([XC / FIG_W, fy(y0 + RH - .14), WC / FIG_W, (RH - .26) / H])
    aA.hist([sum(S[s]["tripod"][str(i)] == "Reported" for i in range(1, 20)) for s in S], bins=np.arange(-.5, 20, 1), color="#8FC3BD", rwidth=.85)
    aA.set_xlim(-.5, 19.5); aA.set_xticks([0, 5, 10, 15, 19]); deco(aA)
    aA.set_xlabel(T(ko, "TRIPOD+AI elements reported completely (of 19)", ""), fontsize=fs, labelpad=1)
    sc = [i for i in items if i["scored"]]
    tot = [sum(S[s]["items"].get(str(i["idx"]), False) for i in sc) for s in S]
    aC.hist(tot, bins=np.arange(-.5, len(sc) + 1, 1), color=NAVY, rwidth=.85)
    aC.set_xlim(-.5, len(sc) + .5); aC.set_xticks([0, 10, 20, 30]); deco(aC)
    aC.set_xlabel(T(ko, f"Core items met (of {len(sc)})", f"   ({len(sc)} )"), fontsize=fs, labelpad=1)
    save(fig, "fig15_checklist_items", ko, tight=True)



def figure_checklist_items_v14b(lang="en"):
    """v14 Figure 5, layout 3 (author): per TRIPOD+AI-derived element with at least one scored core item:
    left, the 3-level TRIPOD+AI judgement (blue-green); right, every core item as a box filled to the percentage of
    studies meeting it (orange; numbers as in Table 1). Items met by fewer than 10% of applicable studies are boxed in
    red and numbered with circled numbers, listed in a legend below. Last row: overall distributions."""
    import checklist_v14 as CK, checklist_v14_table as TB
    from checklist_v12 import TRIPOD
    style(lang); ko = lang == "ko"
    t = json.load(open(os.path.join(ROOT, "results/derived/checklist_v14_scores.json")))
    items, S = t["items"], t["studies"]
    order = TB.ordered()
    num = {(r[0], r[2]): n for n, r in enumerate(order, 1)}
    name = {(r[0], r[2]): (r[1] if ko else r[2]) for r in order}
    groups = []
    for key in list(range(1, 20)) + ["importance"]:
        idx = [i for i in items if i["tripod"] == key and i["scored"]]
        if idx:
            groups.append((key, sorted(idx, key=lambda i: num[(key, i["item_en"])])))
    levels = [("Not reported", T(ko, "No", ""), "#C9CED6"), ("Partly reported", T(ko, "Part", ""), "#7FB8C9"), ("Reported", T(ko, "Full", ""), "#1F4E79")]
    ORANGE, OEDGE, RED = "#F28E2B", "#B85C00", "#D62728"
    circ = "①②③④⑤⑥⑦⑧⑨⑩"
    pct = {}
    for key, its in groups:
        for it in its:
            v = [S[s]["items"][str(it["idx"])] for s in S if str(it["idx"]) in S[s]["items"]]
            pct[it["idx"]] = (100 * sum(v) / len(v), len(v))
    low = sorted([it for _, its in groups for it in its if pct[it["idx"]][0] < 10], key=lambda i: num[(i["tripod"], i["item_en"])])
    lowmark = {it["idx"]: circ[k] for k, it in enumerate(low)}
    RH, TOP = .5, .62
    LEG = .2 + .17 * len(low)
    H = TOP + (len(groups) + 1) * RH + .55 + LEG
    fig = plt.figure(figsize=(FIG_W, H))
    fy = lambda yin: 1 - yin / H
    XA, WA, XB, WB = 1.95, 1.05, 3.5, 3.7
    fs = FS_TICK - 2.4
    fig.text(XA / FIG_W, fy(.12), T(ko, "TRIPOD+AI\n(3 levels, %)", ""), fontsize=FS_TITLE - 2.8, weight="bold", va="top", color="#1F4E79", linespacing=1.05)
    fig.text(XB / FIG_W, fy(.12), T(ko, "KNHANES core checklist: % meeting each item\n(numbers as in Table 1; red, below 10%)", ""),
             fontsize=FS_TITLE - 2.8, weight="bold", va="top", color=OEDGE, linespacing=1.05)
    def deco(a):
        [a.spines[s_].set_visible(False) for s_ in ("top", "right")]; grid(a, "y"); a.tick_params(labelsize=fs - .7, length=2, pad=1)
    maxk = max(len(its) for _, its in groups)
    for r, (key, its) in enumerate(groups):
        y0 = TOP + r * RH
        lab = (f"{key}. " + T(ko, TRIPOD[key - 1][1], TRIPOD[key - 1][0])) if isinstance(key, int) else T(ko, "(New) Variable importance", "")
        fig.text(.05 / FIG_W, fy(y0 + RH * .42), "\n".join(__import__("textwrap").wrap(lab, 22 if not ko else 14)), fontsize=fs, va="center", linespacing=1.0)
        aA = fig.add_axes([XA / FIG_W, fy(y0 + RH - .13), WA / FIG_W, (RH - .24) / H])
        aB = fig.add_axes([XB / FIG_W, fy(y0 + RH - .13), WB / FIG_W, (RH - .24) / H])
        if isinstance(key, int):
            cnt = [100 * sum(S[s]["tripod"][str(key)] == lev for s in S) / len(S) for lev, _, _ in levels]
            aA.bar(range(3), cnt, color=[c for _, _, c in levels], width=.7)
            aA.set_xticks(range(3)); aA.set_xticklabels([l for _, l, _ in levels], fontsize=fs - 1.2)
        else:
            aA.text(1, 50, T(ko, "No element", ""), ha="center", va="center", fontsize=fs - .4, color=DGREY); aA.set_xticks([])
        aA.set_xlim(-.6, 2.6); aA.set_ylim(0, 100); aA.set_yticks([0, 50, 100]); deco(aA)
        for x, it in enumerate(its):
            v, n = pct[it["idx"]]
            isl = it["idx"] in lowmark
            aB.add_patch(matplotlib.patches.Rectangle((x - .32, 0), .64, 100, fill=False, edgecolor=RED if isl else "#C4C9D0", lw=1.6 if isl else .6, zorder=4 if isl else 2))
            aB.bar(x, v, color=ORANGE, width=.64, edgecolor=OEDGE, linewidth=.5, zorder=3)
            aB.text(x, -14, str(num[(key, it["item_en"])]), ha="center", va="top", fontsize=fs - .6)
            if isl:
                aB.text(x + .36, 92, lowmark[it["idx"]], ha="left", va="top", fontsize=fs + 1.2, color=RED, weight="bold")
        aB.set_xticks([]); aB.set_xlim(-.6, maxk - .4); aB.set_ylim(0, 100); aB.set_yticks([0, 50, 100]); deco(aB)
    y0 = TOP + len(groups) * RH + .22
    fig.add_artist(Line2D([.02, .98], [fy(y0 - .1)] * 2, color=DGREY, lw=.6))
    fig.text(.05 / FIG_W, fy(y0 + RH * .45), T(ko, "Overall\n(studies)", ""), fontsize=fs + .4, weight="bold", va="center", linespacing=1.0)
    aA = fig.add_axes([XA / FIG_W, fy(y0 + RH - .1), WA / FIG_W, (RH - .2) / H])
    aB = fig.add_axes([XB / FIG_W, fy(y0 + RH - .1), WB / FIG_W, (RH - .2) / H])
    aA.hist([sum(S[s]["tripod"][str(i)] == "Reported" for i in range(1, 20)) for s in S], bins=np.arange(-.5, 20, 1), color="#1F4E79", rwidth=.85)
    aA.set_xlim(-.5, 19.5); aA.set_xticks([0, 5, 10, 15, 19]); deco(aA)
    aA.set_xlabel(T(ko, "Elements reported completely (of 19)", ""), fontsize=fs - .2, labelpad=1)
    sc = [i for i in items if i["scored"]]
    tot = [sum(S[s]["items"].get(str(i["idx"]), False) for i in sc) for s in S]
    aB.hist(tot, bins=np.arange(-.5, len(sc) + 1, 1), color=ORANGE, edgecolor=OEDGE, linewidth=.4, rwidth=.85)
    aB.set_xlim(-.5, len(sc) + .5); aB.set_xticks([0, 5, 10, 15, 20, 25, 30]); deco(aB)
    aB.set_xlabel(T(ko, f"Core items met (of {len(sc)})", f"   ({len(sc)} )"), fontsize=fs - .2, labelpad=1)
    yl = y0 + RH + .45
    fig.text(.05 / FIG_W, fy(yl), T(ko, "Items met by fewer than 10% of studies (the least reported information):", ""), fontsize=fs + .2, weight="bold", color=RED, va="top")
    for k, it in enumerate(low):
        v, n = pct[it["idx"]]
        key = it["tripod"]
        fig.text(.2 / FIG_W, fy(yl + .2 + .17 * k), f"{circ[k]}  {num[(key, it['item_en'])]}. {name[(key, it['item_en'])]} — {v:.1f}% ({round(v * n / 100)}/{n})",
                 fontsize=fs + .1, va="top")
    save(fig, "fig16_checklist_items", ko, tight=True)




def figure_checklist_v15(lang="en"):
    """v15 Figure 5 (author): drawn at the printed size (text width 5.4 in, about 0.8 of the text height) so
    the type is legible. Per TRIPOD+AI-derived element: left, the 3-level TRIPOD+AI judgement; middle, every core item
    as a box filled to the percentage of studies meeting it (IDs as in Table 1); items met by fewer than 10% are boxed
    in red with a circled number, and named with their percentage at the right of the same row. Last row: overall."""
    import checklist_v15 as CK, checklist_v15_table as TB
    from checklist_v12 import TRIPOD
    import textwrap
    style(lang); ko = lang == "ko"
    t = json.load(open(os.path.join(ROOT, "results/derived/checklist_v15_scores.json")))
    items, S = t["items"], t["studies"]
    order = TB.ordered()
    num = {(r[1], r[3]): r[0] for r in order}
    name = {(r[1], r[3]): (r[2] if ko else r[3]) for r in order}
    groups = []
    for key in list(range(1, 20)) + ["importance", "after"]:
        idx = [i for i in items if i["tripod"] == key and i["scored"]]
        if idx:
            groups.append((key, sorted(idx, key=lambda i: num[(key, i["item_en"])])))
    levels = [("Not reported", T(ko, "Not", ""), "#C9CED6"), ("Partly reported", T(ko, "Partly", ""), "#7FB8C9"), ("Reported", T(ko, "Completely", ""), "#1F4E79")]
    ORANGE, OEDGE, RED = "#F28E2B", "#B85C00", "#D62728"
    circ = "①②③④⑤⑥⑦⑧⑨⑩"
    pct = {}
    for key, its in groups:
        for it in its:
            v = [S[s]["items"][str(it["idx"])] for s in S if str(it["idx"]) in S[s]["items"]]
            pct[it["idx"]] = (100 * sum(v) / len(v), len(v))
    low = [it for _, its in groups for it in its if pct[it["idx"]][0] < 10]  # plotting order
    lowmark = {it["idx"]: circ[k] for k, it in enumerate(low)}
    W = 5.4
    fs, fa = 6.6, 6.2                               # type size at print (pt)
    LH = fa * 1.25 / 72                             # annotation line height (in)
    AW = 30 if not ko else 24                       # annotation wrap (characters)
    ann = {it["idx"]: textwrap.wrap(f"{lowmark[it['idx']]} {num[(it['tripod'], it['item_en'])]} {name[(it['tripod'], it['item_en'])]} "
                                    f"{pct[it['idx']][0]:.1f}% ({round(pct[it['idx']][0] * pct[it['idx']][1] / 100)}/{pct[it['idx']][1]})", AW, subsequent_indent="   ")
           for it in low}
    nlow = [sum(len(ann[it["idx"]]) for it in its if it["idx"] in lowmark) for _, its in groups]
    rh = [max(.28, n * LH + .08) for n in nlow]
    TOP = .5
    ys = [TOP + sum(rh[:r]) for r in range(len(groups))]
    H = TOP + sum(rh) + .2 + .55
    fig = plt.figure(figsize=(W, H))
    fy = lambda yin: 1 - yin / H
    XA, WA, XB, WB, XC = 1.32, .58, 2.18, 1.5, 3.78
    fig.text(XA / W, fy(.04), T(ko, "TRIPOD+AI\n(% of studies)", ""), fontsize=fs, weight="bold", va="top", color="#1F4E79", linespacing=1.05)
    fig.text(XB / W, fy(.04), T(ko, "Core checklist: % meeting\neach item (ID, Table 1)", ""), fontsize=fs, weight="bold", va="top", color=OEDGE, linespacing=1.05)
    fig.text(XC / W, fy(.04), T(ko, "Met by <10% of studies\n(red boxes)", ""), fontsize=fs, weight="bold", va="top", color=RED, linespacing=1.05)
    # legend for the three TRIPOD+AI levels (instead of tick labels on every row)
    for k, (_, lab, c) in enumerate(levels):
        x = XA + k * .3 - .05
        fig.patches.append(matplotlib.patches.Rectangle((x / W, fy(.4)), .07 / W, .07 / H, color=c, transform=fig.transFigure, figure=fig))
        fig.text((x + .09) / W, fy(.4) + .035 / H, lab, fontsize=fs - 1.6, va="center")
    def deco(a):
        [a.spines[s_].set_visible(False) for s_ in ("top", "right")]
        a.tick_params(labelsize=fs - 1.6, length=1.5, pad=1, width=.5); [a.spines[s_].set_linewidth(.5) for s_ in ("left", "bottom")]
    maxk = max(len(its) for _, its in groups)
    for r, (key, its) in enumerate(groups):
        y0, h = ys[r], rh[r]
        lab = (f"{key}. " + T(ko, TRIPOD[key - 1][1], TRIPOD[key - 1][0])) if isinstance(key, int) else T(ko, "(New) " + CK.GROUPS[key][1], "" + CK.GROUPS[key][0])
        fig.text(0, fy(y0 + h / 2), "\n".join(textwrap.wrap(lab, 22 if not ko else 13)), fontsize=fs, va="center", linespacing=1.0)
        bh = .17
        yb = y0 + (h - bh) / 2 - .02
        aA = fig.add_axes([XA / W, fy(yb + bh), WA / W, bh / H])
        aB = fig.add_axes([XB / W, fy(yb + bh), WB / W, bh / H])
        if isinstance(key, int):
            cnt = [100 * sum(S[s]["tripod"][str(key)] == lev for s in S) / len(S) for lev, _, _ in levels]
            aA.bar(range(3), cnt, color=[c for _, _, c in levels], width=.75)
        else:
            aA.text(1, 50, T(ko, "no element", ""), ha="center", va="center", fontsize=fs - 1.2, color=DGREY)
        aA.set_xticks([]); aA.set_xlim(-.6, 2.6); aA.set_ylim(0, 100); aA.set_yticks([0, 100]); deco(aA)
        lines = []
        for x, it in enumerate(its):
            v, n = pct[it["idx"]]
            isl = it["idx"] in lowmark
            aB.add_patch(matplotlib.patches.Rectangle((x - .34, 0), .68, 100, fill=False, edgecolor=RED if isl else "#C4C9D0", lw=1.1 if isl else .5, zorder=4 if isl else 2))
            aB.bar(x, v, color=ORANGE, width=.68, edgecolor=OEDGE, linewidth=.4, zorder=3)
            aB.text(x, -16, str(num[(key, it["item_en"])]).replace("RC", ""), ha="center", va="top", fontsize=fs - 1.4)
            if isl:
                aB.text(x + .38, 100, lowmark[it["idx"]], ha="left", va="top", fontsize=fs - .2, color=RED, weight="bold")
                lines += ann[it["idx"]]
        aB.set_xticks([]); aB.set_xlim(-.5, maxk - .5); aB.set_ylim(0, 100); aB.set_yticks([0, 100]); deco(aB)
        for k, ln in enumerate(lines):
            fig.text(XC / W, fy(y0 + h / 2 + (k - (len(lines) - 1) / 2) * LH), ln, fontsize=fa, va="center", color="#7A1010")
    y0 = TOP + sum(rh) + .12
    fig.add_artist(Line2D([0, 1], [fy(y0 - .05)] * 2, color=DGREY, lw=.6))
    fig.text(0, fy(y0 + .2), T(ko, "Overall (studies)", ""), fontsize=fs, weight="bold", va="center")
    aA = fig.add_axes([XA / W, fy(y0 + .3), WA / W, .22 / H])
    aB = fig.add_axes([XB / W, fy(y0 + .3), WB / W, .22 / H])
    aA.hist([sum(S[s]["tripod"][str(i)] == "Reported" for i in range(1, 20)) for s in S], bins=np.arange(-.5, 20, 1), color="#1F4E79", rwidth=.85)
    aA.set_xlim(-.5, 19.5); aA.set_xticks([0, 10, 19]); deco(aA)
    aA.set_xlabel(T(ko, "Elements complete (of 19)", ""), fontsize=fs - 1.2, labelpad=1)
    sc = [i for i in items if i["scored"]]
    tot = [sum(S[s]["items"].get(str(i["idx"]), False) for i in sc) for s in S]
    aB.hist(tot, bins=np.arange(-.5, len(sc) + 1, 1), color=ORANGE, edgecolor=OEDGE, linewidth=.3, rwidth=.85)
    aB.set_xlim(-.5, len(sc) + .5); aB.set_xticks([0, 15, 30, 45]); deco(aB)
    aB.set_xlabel(T(ko, f"Core items met (of {len(sc)})", f"   ({len(sc)} )"), fontsize=fs - 1.2, labelpad=1)
    save(fig, "fig18_checklist_v15", ko, tight=True)



def figure_checklist_v16_detail(lang="en"):
    """an appendix figure of an earlier draft (= v15 Figure 5 with the v16 items) (author): drawn at the printed size (text width 5.4 in, about 0.8 of the text height) so
    the type is legible. Per TRIPOD+AI-derived element: left, the 3-level TRIPOD+AI judgement; middle, every core item
    as a box filled to the percentage of studies meeting it (IDs as in Table 1); items met by fewer than 10% are boxed
    in red with a circled number, and named with their percentage at the right of the same row. Last row: overall."""
    import checklist_v16 as CK, checklist_v16_table as TB
    from checklist_v12 import TRIPOD
    import textwrap
    style(lang); ko = lang == "ko"
    t = json.load(open(os.path.join(ROOT, "results/derived/checklist_v16_scores.json")))
    items, S = t["items"], t["studies"]
    order = TB.ordered()
    num = {(r[1], r[3]): r[0] for r in order}
    name = {(r[1], r[3]): (r[2] if ko else r[3]) for r in order}
    groups = []
    for key in list(range(1, 20)) + ["importance", "after"]:
        idx = [i for i in items if i["tripod"] == key and i["scored"]]
        if idx:
            groups.append((key, sorted(idx, key=lambda i: num[(key, i["item_en"])])))
    levels = [("Not reported", T(ko, "Not", ""), "#C9CED6"), ("Partly reported", T(ko, "Partly", ""), "#7FB8C9"), ("Reported", T(ko, "Completely", ""), "#1F4E79")]
    ORANGE, OEDGE, RED = "#F28E2B", "#B85C00", "#D62728"
    circ = "①②③④⑤⑥⑦⑧⑨⑩"
    pct = {}
    for key, its in groups:
        for it in its:
            v = [S[s]["items"][str(it["idx"])] for s in S if str(it["idx"]) in S[s]["items"]]
            pct[it["idx"]] = (100 * sum(v) / len(v), len(v))
    low = [it for _, its in groups for it in its if pct[it["idx"]][0] < 10]  # plotting order
    lowmark = {it["idx"]: circ[k] for k, it in enumerate(low)}
    W = 5.4
    fs, fa = 6.6, 6.2                               # type size at print (pt)
    LH = fa * 1.25 / 72                             # annotation line height (in)
    AW = 30 if not ko else 24                       # annotation wrap (characters)
    ann = {it["idx"]: textwrap.wrap(f"{lowmark[it['idx']]} {num[(it['tripod'], it['item_en'])]} {name[(it['tripod'], it['item_en'])]} "
                                    f"{pct[it['idx']][0]:.1f}% ({round(pct[it['idx']][0] * pct[it['idx']][1] / 100)}/{pct[it['idx']][1]})", AW, subsequent_indent="   ")
           for it in low}
    nlow = [sum(len(ann[it["idx"]]) for it in its if it["idx"] in lowmark) for _, its in groups]
    rh = [max(.28, n * LH + .08) for n in nlow]
    TOP = .5
    ys = [TOP + sum(rh[:r]) for r in range(len(groups))]
    H = TOP + sum(rh) + .2 + .55
    fig = plt.figure(figsize=(W, H))
    fy = lambda yin: 1 - yin / H
    XA, WA, XB, WB, XC = 1.32, .58, 2.18, 1.5, 3.78
    fig.text(XA / W, fy(.04), T(ko, "TRIPOD+AI\n(% of studies)", ""), fontsize=fs, weight="bold", va="top", color="#1F4E79", linespacing=1.05)
    fig.text(XB / W, fy(.04), T(ko, "Core checklist: % meeting\neach item (ID, Table 1)", ""), fontsize=fs, weight="bold", va="top", color=OEDGE, linespacing=1.05)
    fig.text(XC / W, fy(.04), T(ko, "Met by <10% of studies\n(red boxes)", ""), fontsize=fs, weight="bold", va="top", color=RED, linespacing=1.05)
    # legend for the three TRIPOD+AI levels (instead of tick labels on every row)
    for k, (_, lab, c) in enumerate(levels):
        x = XA + k * .3 - .05
        fig.patches.append(matplotlib.patches.Rectangle((x / W, fy(.4)), .07 / W, .07 / H, color=c, transform=fig.transFigure, figure=fig))
        fig.text((x + .09) / W, fy(.4) + .035 / H, lab, fontsize=fs - 1.6, va="center")
    def deco(a):
        [a.spines[s_].set_visible(False) for s_ in ("top", "right")]
        a.tick_params(labelsize=fs - 1.6, length=1.5, pad=1, width=.5); [a.spines[s_].set_linewidth(.5) for s_ in ("left", "bottom")]
    maxk = max(len(its) for _, its in groups)
    for r, (key, its) in enumerate(groups):
        y0, h = ys[r], rh[r]
        lab = (f"{key}. " + T(ko, TRIPOD[key - 1][1], TRIPOD[key - 1][0])) if isinstance(key, int) else T(ko, "(New) " + CK.GROUPS[key][1], "" + CK.GROUPS[key][0])
        fig.text(0, fy(y0 + h / 2), "\n".join(textwrap.wrap(lab, 22 if not ko else 13)), fontsize=fs, va="center", linespacing=1.0)
        bh = .17
        yb = y0 + (h - bh) / 2 - .02
        aA = fig.add_axes([XA / W, fy(yb + bh), WA / W, bh / H])
        aB = fig.add_axes([XB / W, fy(yb + bh), WB / W, bh / H])
        if isinstance(key, int):
            cnt = [100 * sum(S[s]["tripod"][str(key)] == lev for s in S) / len(S) for lev, _, _ in levels]
            aA.bar(range(3), cnt, color=[c for _, _, c in levels], width=.75)
        else:
            aA.text(1, 50, T(ko, "no element", ""), ha="center", va="center", fontsize=fs - 1.2, color=DGREY)
        aA.set_xticks([]); aA.set_xlim(-.6, 2.6); aA.set_ylim(0, 100); aA.set_yticks([0, 100]); deco(aA)
        lines = []
        for x, it in enumerate(its):
            v, n = pct[it["idx"]]
            isl = it["idx"] in lowmark
            aB.add_patch(matplotlib.patches.Rectangle((x - .34, 0), .68, 100, fill=False, edgecolor=RED if isl else "#C4C9D0", lw=1.1 if isl else .5, zorder=4 if isl else 2))
            aB.bar(x, v, color=ORANGE, width=.68, edgecolor=OEDGE, linewidth=.4, zorder=3)
            aB.text(x, -16, str(num[(key, it["item_en"])]).replace("RC", ""), ha="center", va="top", fontsize=fs - 1.4)
            if isl:
                aB.text(x + .38, 100, lowmark[it["idx"]], ha="left", va="top", fontsize=fs - .2, color=RED, weight="bold")
                lines += ann[it["idx"]]
        aB.set_xticks([]); aB.set_xlim(-.5, maxk - .5); aB.set_ylim(0, 100); aB.set_yticks([0, 100]); deco(aB)
        for k, ln in enumerate(lines):
            fig.text(XC / W, fy(y0 + h / 2 + (k - (len(lines) - 1) / 2) * LH), ln, fontsize=fa, va="center", color="#7A1010")
    y0 = TOP + sum(rh) + .12
    fig.add_artist(Line2D([0, 1], [fy(y0 - .05)] * 2, color=DGREY, lw=.6))
    fig.text(0, fy(y0 + .2), T(ko, "Overall (studies)", ""), fontsize=fs, weight="bold", va="center")
    aA = fig.add_axes([XA / W, fy(y0 + .3), WA / W, .22 / H])
    aB = fig.add_axes([XB / W, fy(y0 + .3), WB / W, .22 / H])
    aA.hist([sum(S[s]["tripod"][str(i)] == "Reported" for i in range(1, 20)) for s in S], bins=np.arange(-.5, 20, 1), color="#1F4E79", rwidth=.85)
    aA.set_xlim(-.5, 19.5); aA.set_xticks([0, 10, 19]); deco(aA)
    aA.set_xlabel(T(ko, "Elements complete (of 19)", ""), fontsize=fs - 1.2, labelpad=1)
    sc = [i for i in items if i["scored"]]
    tot = [sum(S[s]["items"].get(str(i["idx"]), False) for i in sc) for s in S]
    aB.hist(tot, bins=np.arange(-.5, len(sc) + 1, 1), color=ORANGE, edgecolor=OEDGE, linewidth=.3, rwidth=.85)
    aB.set_xlim(-.5, len(sc) + .5); aB.set_xticks([0, 15, 30, 45]); deco(aB)
    aB.set_xlabel(T(ko, f"Core items met (of {len(sc)})", f"   ({len(sc)} )"), fontsize=fs - 1.2, labelpad=1)
    save(fig, "fig20_checklist_v16_detail", ko, tight=True)

def figure_checklist_v16(lang="en"):
    """v16 Figure 5 (prompt 134): what the item-level checklist adds. (A) Among studies judged completely reported on a
    TRIPOD+AI-derived element, the per-study percentage of that element's core items met; (B) per-study percentage met by
    reproduction stage and for KNHANES-specific items; (C) the least reported core items. Drawn at print size."""
    import checklist_v16 as CK
    from checklist_v12 import TRIPOD
    style(lang); ko = lang == "ko"
    t = json.load(open(os.path.join(ROOT, "results/derived/checklist_v16_scores.json")))
    items, S = t["items"], t["studies"]
    I = {str(i["idx"]): i for i in items}
    ORANGE, OEDGE, RED, BLUE = "#F28E2B", "#B85C00", "#D62728", "#1F4E79"
    fs = 7.0
    rng = np.random.default_rng(7)

    def score(st, f):
        v = [b for k, b in st["items"].items() if f(I[k])]
        return 100 * sum(v) / len(v) if v else None

    # A: elements with >= 3 core items (fewer give only 0/50/100%) and >= 20 studies completely reported
    A = []
    for el in range(1, 20):
        its = [i for i in items if i["tripod"] == el]
        if len(its) < 3:
            continue
        v = [score(st, lambda i, el=el: i["tripod"] == el) for st in S.values() if st["tripod"][str(el)] == "Reported"]
        v = [x for x in v if x is not None]
        if len(v) >= 20:
            A.append((el, len(its), v))
    B = [(T(ko, "Data", ""), lambda i: i["stage"] == "D"), (T(ko, "Model", ""), lambda i: i["stage"] == "M"),
         (T(ko, "Importance", ""), lambda i: i["stage"] == "I"), (T(ko, "Reporting", ""), lambda i: i["stage"] == "R"),
         (T(ko, "KNHANES-specific", ""), lambda i: i["note"] in ("RS", "NS")), (T(ko, "All items", ""), lambda i: True)]
    Bv = []
    for lab, f in B:
        v = [score(st, f) for st in S.values()]
        v = [x for x in v if x is not None]
        n_it = sum(f(i) for i in items)
        Bv.append((lab, n_it, v))
    pct = []
    for i in items:
        v = [S[s]["items"][str(i["idx"])] for s in S if str(i["idx"]) in S[s]["items"]]
        pct.append((100 * sum(v) / len(v), sum(v), len(v), i))
    C = sorted(pct, key=lambda x: x[0])[:12]

    W = 5.4
    hA, hB, hC = .26 * len(A) + .55, .26 * len(Bv) + .55, .2 * len(C) + .55
    H = hA + hB + hC + .25
    fig = plt.figure(figsize=(W, H))
    L, R_ = 2.05, .25
    def ax_at(y, h):
        return fig.add_axes([L / W, 1 - (y + h - .38) / H, (W - L - R_) / W, (h - .55) / H])
    def strip(ax, rows, col):
        for k, (lab, n_it, v, extra) in enumerate(rows):
            y = len(rows) - 1 - k
            ax.boxplot([v], positions=[y], vert=False, widths=.55, showfliers=False, whis=(0, 100),
                       medianprops=dict(color="black", lw=1.1), boxprops=dict(lw=.6, color=DGREY), whiskerprops=dict(lw=.6, color=DGREY), capprops=dict(lw=.6, color=DGREY))
            ax.scatter(v, y + rng.uniform(-.2, .2, len(v)), s=3, color=col, alpha=.45, lw=0, zorder=3)
            ax.text(-3, y, lab, ha="right", va="center", fontsize=fs - .4, transform=ax.transData, clip_on=False)
            ax.text(103, y, extra, ha="left", va="center", fontsize=fs - 1.2, color=DGREY, clip_on=False)
        ax.set_yticks([]); ax.set_xlim(0, 100); ax.set_ylim(-.6, len(rows) - .4)
        ax.set_xticks([0, 25, 50, 75, 100]); ax.tick_params(labelsize=fs - 1, length=2, pad=1)
        [ax.spines[s_].set_visible(False) for s_ in ("top", "right", "left")]; grid(ax, "x")
    def head(y, letter, en, kr):
        fig.text(0, 1 - y / H, f"{letter}  " + T(ko, en, kr), fontsize=fs + .6, weight="bold", va="top")
    y = 0
    head(y, "A", "Studies judged 'completely reported' on an element: % of its core items met",
         "")
    ax = ax_at(y, hA)
    strip(ax, [("\n".join(__import__("textwrap").wrap(f"{el}. " + T(ko, TRIPOD[el - 1][1], TRIPOD[el - 1][0]), 30 if not ko else 18)), n, v,
                f"n={len(v)}\n{n} " + T(ko, "items", "")) for el, n, v in A], BLUE)
    ax.set_xlabel(T(ko, "% of the element's core items met", ""), fontsize=fs - .8, labelpad=1)
    y += hA
    head(y, "B", "All 193 studies: % of applicable core items met, by reproduction stage",
         "")
    ax = ax_at(y, hB)
    strip(ax, [(lab, n, v, f"{n} " + T(ko, "items", "") + f"\n{T(ko, 'median', '')} {np.median(v):.0f}%") for lab, n, v in Bv], ORANGE)
    ax.set_xlabel(T(ko, "% of applicable core items met per study", ""), fontsize=fs - .8, labelpad=1)
    y += hB
    head(y, "C", "The least reported core items (% of studies to which the item applies)",
         "")
    ax = ax_at(y, hC)
    for k, (p, m, n, i) in enumerate(C):
        yy = len(C) - 1 - k
        ax.barh(yy, p, height=.65, color=RED if p < 10 else ORANGE, edgecolor="none")
        ax.text(max(p, 10) + .8, yy, f"{p:.1f}% ({m}/{n})", va="center", fontsize=fs - 1.2)
        ax.text(-1.5, yy, f"{i['id']} " + (i["item_ko"] if ko else i["item_en"]), ha="right", va="center", fontsize=fs - .6)
    ax.axvline(10, color=RED, lw=.6, ls="--", zorder=1)
    ax.set_yticks([]); ax.set_xlim(0, 40); ax.set_ylim(-.6, len(C) - .4); ax.set_xticks([0, 10, 20, 30, 40])
    ax.tick_params(labelsize=fs - 1, length=2, pad=1); [ax.spines[s_].set_visible(False) for s_ in ("top", "right", "left")]; grid(ax, "x")
    ax.set_xlabel(T(ko, "% of studies meeting the item (red, below 10%)", ""), fontsize=fs - .8, labelpad=1)
    save(fig, "fig19_checklist_v16", ko, tight=True)


def figure_checklist_v17_detail(lang="en"):
    """an appendix figure of an earlier draft (= v15 Figure 5 with the v16 items) (author): drawn at the printed size (text width 5.4 in, about 0.8 of the text height) so
    the type is legible. Per TRIPOD+AI-derived element: left, the 3-level TRIPOD+AI judgement; middle, every core item
    as a box filled to the percentage of studies meeting it (IDs as in Table 1); items met by fewer than 10% are boxed
    in red with a circled number, and named with their percentage at the right of the same row. Last row: overall."""
    import checklist_v17 as CK, checklist_v17_table as TB
    from checklist_v12 import TRIPOD
    import textwrap
    style(lang); ko = lang == "ko"
    t = json.load(open(os.path.join(ROOT, "results/derived/checklist_v17_scores.json")))
    items, S = t["items"], t["studies"]
    order = TB.ordered()
    num = {(r[1], r[3]): r[0] for r in order}
    name = {(r[1], r[3]): (r[2] if ko else r[3]) for r in order}
    groups = []
    for key in list(range(1, 20)) + ["importance", "after"]:
        idx = [i for i in items if i["tripod"] == key and i["scored"]]
        if idx:
            groups.append((key, sorted(idx, key=lambda i: num[(key, i["item_en"])])))
    levels = [("Not reported", T(ko, "Not", ""), "#C9CED6"), ("Partly reported", T(ko, "Partly", ""), "#7FB8C9"), ("Reported", T(ko, "Completely", ""), "#1F4E79")]
    ORANGE, OEDGE, RED = "#F28E2B", "#B85C00", "#D62728"
    circ = "①②③④⑤⑥⑦⑧⑨⑩"
    pct = {}
    for key, its in groups:
        for it in its:
            v = [S[s]["items"][str(it["idx"])] for s in S if str(it["idx"]) in S[s]["items"]]
            pct[it["idx"]] = (100 * sum(v) / len(v), len(v))
    low = [it for _, its in groups for it in its if pct[it["idx"]][0] < 10]  # plotting order
    lowmark = {it["idx"]: circ[k] for k, it in enumerate(low)}
    W = 5.4
    fs, fa = 6.6, 6.2                               # type size at print (pt)
    LH = fa * 1.25 / 72                             # annotation line height (in)
    AW = 30 if not ko else 24                       # annotation wrap (characters)
    ann = {it["idx"]: textwrap.wrap(f"{lowmark[it['idx']]} {num[(it['tripod'], it['item_en'])]} {name[(it['tripod'], it['item_en'])]} "
                                    f"{pct[it['idx']][0]:.1f}% ({round(pct[it['idx']][0] * pct[it['idx']][1] / 100)}/{pct[it['idx']][1]})", AW, subsequent_indent="   ")
           for it in low}
    nlow = [sum(len(ann[it["idx"]]) for it in its if it["idx"] in lowmark) for _, its in groups]
    rh = [max(.28, n * LH + .08) for n in nlow]
    TOP = .5
    ys = [TOP + sum(rh[:r]) for r in range(len(groups))]
    H = TOP + sum(rh) + .2 + .55
    fig = plt.figure(figsize=(W, H))
    fy = lambda yin: 1 - yin / H
    XA, WA, XB, WB, XC = 1.32, .58, 2.18, 1.5, 3.78
    fig.text(XA / W, fy(.04), T(ko, "TRIPOD+AI\n(% of studies)", ""), fontsize=fs, weight="bold", va="top", color="#1F4E79", linespacing=1.05)
    fig.text(XB / W, fy(.04), T(ko, "Core checklist: % meeting\neach item (ID, Table 1)", ""), fontsize=fs, weight="bold", va="top", color=OEDGE, linespacing=1.05)
    fig.text(XC / W, fy(.04), T(ko, "Met by <10% of studies\n(red boxes)", ""), fontsize=fs, weight="bold", va="top", color=RED, linespacing=1.05)
    # legend for the three TRIPOD+AI levels (instead of tick labels on every row)
    for k, (_, lab, c) in enumerate(levels):
        x = XA + k * .3 - .05
        fig.patches.append(matplotlib.patches.Rectangle((x / W, fy(.4)), .07 / W, .07 / H, color=c, transform=fig.transFigure, figure=fig))
        fig.text((x + .09) / W, fy(.4) + .035 / H, lab, fontsize=fs - 1.6, va="center")
    def deco(a):
        [a.spines[s_].set_visible(False) for s_ in ("top", "right")]
        a.tick_params(labelsize=fs - 1.6, length=1.5, pad=1, width=.5); [a.spines[s_].set_linewidth(.5) for s_ in ("left", "bottom")]
    maxk = max(len(its) for _, its in groups)
    for r, (key, its) in enumerate(groups):
        y0, h = ys[r], rh[r]
        lab = (f"{key}. " + T(ko, TRIPOD[key - 1][1], TRIPOD[key - 1][0])) if isinstance(key, int) else T(ko, "(New) " + CK.GROUPS[key][1], "" + CK.GROUPS[key][0])
        fig.text(0, fy(y0 + h / 2), "\n".join(textwrap.wrap(lab, 22 if not ko else 13)), fontsize=fs, va="center", linespacing=1.0)
        bh = .17
        yb = y0 + (h - bh) / 2 - .02
        aA = fig.add_axes([XA / W, fy(yb + bh), WA / W, bh / H])
        aB = fig.add_axes([XB / W, fy(yb + bh), WB / W, bh / H])
        if isinstance(key, int):
            cnt = [100 * sum(S[s]["tripod"][str(key)] == lev for s in S) / len(S) for lev, _, _ in levels]
            aA.bar(range(3), cnt, color=[c for _, _, c in levels], width=.75)
        else:
            aA.text(1, 50, T(ko, "no element", ""), ha="center", va="center", fontsize=fs - 1.2, color=DGREY)
        aA.set_xticks([]); aA.set_xlim(-.6, 2.6); aA.set_ylim(0, 100); aA.set_yticks([0, 100]); deco(aA)
        lines = []
        for x, it in enumerate(its):
            v, n = pct[it["idx"]]
            isl = it["idx"] in lowmark
            aB.add_patch(matplotlib.patches.Rectangle((x - .34, 0), .68, 100, fill=False, edgecolor=RED if isl else "#C4C9D0", lw=1.1 if isl else .5, zorder=4 if isl else 2))
            aB.bar(x, v, color=ORANGE, width=.68, edgecolor=OEDGE, linewidth=.4, zorder=3)
            aB.text(x, -16, str(num[(key, it["item_en"])]).replace("RC", ""), ha="center", va="top", fontsize=fs - 1.4)
            if isl:
                aB.text(x + .38, 100, lowmark[it["idx"]], ha="left", va="top", fontsize=fs - .2, color=RED, weight="bold")
                lines += ann[it["idx"]]
        aB.set_xticks([]); aB.set_xlim(-.5, maxk - .5); aB.set_ylim(0, 100); aB.set_yticks([0, 100]); deco(aB)
        for k, ln in enumerate(lines):
            fig.text(XC / W, fy(y0 + h / 2 + (k - (len(lines) - 1) / 2) * LH), ln, fontsize=fa, va="center", color="#7A1010")
    y0 = TOP + sum(rh) + .12
    fig.add_artist(Line2D([0, 1], [fy(y0 - .05)] * 2, color=DGREY, lw=.6))
    fig.text(0, fy(y0 + .2), T(ko, "Overall (studies)", ""), fontsize=fs, weight="bold", va="center")
    aA = fig.add_axes([XA / W, fy(y0 + .3), WA / W, .22 / H])
    aB = fig.add_axes([XB / W, fy(y0 + .3), WB / W, .22 / H])
    aA.hist([sum(S[s]["tripod"][str(i)] == "Reported" for i in range(1, 20)) for s in S], bins=np.arange(-.5, 20, 1), color="#1F4E79", rwidth=.85)
    aA.set_xlim(-.5, 19.5); aA.set_xticks([0, 10, 19]); deco(aA)
    aA.set_xlabel(T(ko, "Elements complete (of 19)", ""), fontsize=fs - 1.2, labelpad=1)
    sc = [i for i in items if i["scored"]]
    tot = [sum(S[s]["items"].get(str(i["idx"]), False) for i in sc) for s in S]
    aB.hist(tot, bins=np.arange(-.5, len(sc) + 1, 1), color=ORANGE, edgecolor=OEDGE, linewidth=.3, rwidth=.85)
    aB.set_xlim(-.5, len(sc) + .5); aB.set_xticks([0, 15, 30, 45]); deco(aB)
    aB.set_xlabel(T(ko, f"Core items met (of {len(sc)})", f"   ({len(sc)} )"), fontsize=fs - 1.2, labelpad=1)
    save(fig, "fig22_checklist_v17_detail", ko, tight=True)


def figure_checklist_v17(lang="en"):
    """v17 Figure 5 (prompt 135; KNHANES-specific and all-item rows marked as cross-cutting). Was v16 Figure 5 (prompt 134): what the item-level checklist adds. (A) Among studies judged completely reported on a
    TRIPOD+AI-derived element, the per-study percentage of that element's core items met; (B) per-study percentage met by
    reproduction stage and for KNHANES-specific items; (C) the least reported core items. Drawn at print size."""
    import checklist_v17 as CK
    from checklist_v12 import TRIPOD
    style(lang); ko = lang == "ko"
    t = json.load(open(os.path.join(ROOT, "results/derived/checklist_v17_scores.json")))
    items, S = t["items"], t["studies"]
    I = {str(i["idx"]): i for i in items}
    ORANGE, OEDGE, RED, BLUE = "#F28E2B", "#B85C00", "#D62728", "#1F4E79"
    fs = 7.0
    rng = np.random.default_rng(7)

    def score(st, f):
        v = [b for k, b in st["items"].items() if f(I[k])]
        return 100 * sum(v) / len(v) if v else None

    # A: elements with >= 3 core items (fewer give only 0/50/100%) and >= 20 studies completely reported
    A = []
    for el in range(1, 20):
        its = [i for i in items if i["tripod"] == el]
        if len(its) < 3:
            continue
        v = [score(st, lambda i, el=el: i["tripod"] == el) for st in S.values() if st["tripod"][str(el)] == "Reported"]
        v = [x for x in v if x is not None]
        if len(v) >= 20:
            A.append((el, len(its), v))
    B = [(T(ko, "Data", ""), lambda i: i["stage"] == "D"), (T(ko, "Model", ""), lambda i: i["stage"] == "M"),
         (T(ko, "Importance", ""), lambda i: i["stage"] == "I"), (T(ko, "Reporting", ""), lambda i: i["stage"] == "R"),
         (T(ko, "KNHANES-specific\n(cross-cutting)", ""), lambda i: i["note"] in ("RS", "NS")), (T(ko, "All items", ""), lambda i: True)]
    Bv = []
    for lab, f in B:
        v = [score(st, f) for st in S.values()]
        v = [x for x in v if x is not None]
        n_it = sum(f(i) for i in items)
        Bv.append((lab, n_it, v))
    pct = []
    for i in items:
        v = [S[s]["items"][str(i["idx"])] for s in S if str(i["idx"]) in S[s]["items"]]
        pct.append((100 * sum(v) / len(v), sum(v), len(v), i))
    C = sorted(pct, key=lambda x: x[0])[:12]

    W = 5.4
    hA, hB, hC = .26 * len(A) + .55, .26 * len(Bv) + .55, .2 * len(C) + .55
    H = hA + hB + hC + .25
    fig = plt.figure(figsize=(W, H))
    L, R_ = 2.05, .25
    def ax_at(y, h):
        return fig.add_axes([L / W, 1 - (y + h - .38) / H, (W - L - R_) / W, (h - .55) / H])
    def strip(ax, rows, col):
        for k, (lab, n_it, v, extra) in enumerate(rows):
            y = len(rows) - 1 - k
            ax.boxplot([v], positions=[y], vert=False, widths=.55, showfliers=False, whis=(0, 100),
                       medianprops=dict(color="black", lw=1.1), boxprops=dict(lw=.6, color=DGREY), whiskerprops=dict(lw=.6, color=DGREY), capprops=dict(lw=.6, color=DGREY))
            ax.scatter(v, y + rng.uniform(-.2, .2, len(v)), s=3, color=col, alpha=.45, lw=0, zorder=3)
            ax.text(-3, y, lab, ha="right", va="center", fontsize=fs - .4, transform=ax.transData, clip_on=False)
            ax.text(103, y, extra, ha="left", va="center", fontsize=fs - 1.2, color=DGREY, clip_on=False)
        ax.set_yticks([]); ax.set_xlim(0, 100); ax.set_ylim(-.6, len(rows) - .4)
        ax.set_xticks([0, 25, 50, 75, 100]); ax.tick_params(labelsize=fs - 1, length=2, pad=1)
        [ax.spines[s_].set_visible(False) for s_ in ("top", "right", "left")]; grid(ax, "x")
    def head(y, letter, en, kr):
        fig.text(0, 1 - y / H, f"{letter}  " + T(ko, en, kr), fontsize=fs + .6, weight="bold", va="top")
    y = 0
    head(y, "A", "Studies judged 'completely reported' on an element: % of its core items met",
         "")
    ax = ax_at(y, hA)
    strip(ax, [("\n".join(__import__("textwrap").wrap(f"{el}. " + T(ko, TRIPOD[el - 1][1], TRIPOD[el - 1][0]), 30 if not ko else 18)), n, v,
                f"n={len(v)}\n{n} " + T(ko, "items", "")) for el, n, v in A], BLUE)
    ax.set_xlabel(T(ko, "% of the element's core items met", ""), fontsize=fs - .8, labelpad=1)
    y += hA
    head(y, "B", "All 193 studies: % of applicable core items met, by reproduction stage",
         "")
    ax = ax_at(y, hB)
    strip(ax, [(lab, n, v, f"{n} " + T(ko, "items", "") + f"\n{T(ko, 'median', '')} {np.median(v):.0f}%") for lab, n, v in Bv], ORANGE)
    ax.axhline(1.5, color=DGREY, lw=.6, ls=":")  # rows below cut across the stages
    ax.set_xlabel(T(ko, "% of applicable core items met per study", ""), fontsize=fs - .8, labelpad=1)
    y += hB
    head(y, "C", "The least reported core items (% of studies to which the item applies)",
         "")
    ax = ax_at(y, hC)
    for k, (p, m, n, i) in enumerate(C):
        yy = len(C) - 1 - k
        ax.barh(yy, p, height=.65, color=RED if p < 10 else ORANGE, edgecolor="none")
        ax.text(max(p, 10) + .8, yy, f"{p:.1f}% ({m}/{n})", va="center", fontsize=fs - 1.2)
        ax.text(-1.5, yy, f"{i['id']} " + (i["item_ko"] if ko else i["item_en"]), ha="right", va="center", fontsize=fs - .6)
    ax.axvline(10, color=RED, lw=.6, ls="--", zorder=1)
    ax.set_yticks([]); ax.set_xlim(0, 40); ax.set_ylim(-.6, len(C) - .4); ax.set_xticks([0, 10, 20, 30, 40])
    ax.tick_params(labelsize=fs - 1, length=2, pad=1); [ax.spines[s_].set_visible(False) for s_ in ("top", "right", "left")]; grid(ax, "x")
    ax.set_xlabel(T(ko, "% of studies meeting the item (red, below 10%)", ""), fontsize=fs - .8, labelpad=1)
    save(fig, "fig21_checklist_v17", ko, tight=True)


def figure_checklist_v18_detail(lang="en"):
    """an appendix figure of an earlier draft (= v15 Figure 5 with the v16 items) (author): drawn at the printed size (text width 5.4 in, about 0.8 of the text height) so
    the type is legible. Per TRIPOD+AI-derived element: left, the 3-level TRIPOD+AI judgement; middle, every core item
    as a box filled to the percentage of studies meeting it (IDs as in Table 1); items met by fewer than 10% are boxed
    in red with a circled number, and named with their percentage at the right of the same row. Last row: overall."""
    import checklist_v18 as CK, checklist_v18_table as TB
    from checklist_v12 import TRIPOD
    import textwrap
    style(lang); ko = lang == "ko"
    t = json.load(open(os.path.join(ROOT, "results/derived/checklist_v18_scores.json")))
    items, S = t["items"], t["studies"]
    order = TB.ordered()
    num = {(r[1], r[3]): r[0] for r in order}
    name = {(r[1], r[3]): (r[2] if ko else r[3]) for r in order}
    groups = []
    for key in list(range(1, 20)) + ["importance", "after"]:
        idx = [i for i in items if i["tripod"] == key and i["scored"]]
        if idx:
            groups.append((key, sorted(idx, key=lambda i: num[(key, i["item_en"])])))
    levels = [("Not reported", T(ko, "Not", ""), "#C9CED6"), ("Partly reported", T(ko, "Partly", ""), "#7FB8C9"), ("Reported", T(ko, "Completely", ""), "#1F4E79")]
    ORANGE, OEDGE, RED = "#F28E2B", "#B85C00", "#D62728"
    circ = "①②③④⑤⑥⑦⑧⑨⑩"
    pct = {}
    for key, its in groups:
        for it in its:
            v = [S[s]["items"][str(it["idx"])] for s in S if str(it["idx"]) in S[s]["items"]]
            pct[it["idx"]] = (100 * sum(v) / len(v), len(v))
    low = [it for _, its in groups for it in its if pct[it["idx"]][0] < 10]  # plotting order
    lowmark = {it["idx"]: circ[k] for k, it in enumerate(low)}
    W = 5.4
    fs, fa = 6.6, 6.2                               # type size at print (pt)
    LH = fa * 1.25 / 72                             # annotation line height (in)
    AW = 30 if not ko else 24                       # annotation wrap (characters)
    from checklist_desc import DESC  # author: say what each item checks
    ann = {it["idx"]: textwrap.wrap(f"{lowmark[it['idx']]} {num[(it['tripod'], it['item_en'])]} {name[(it['tripod'], it['item_en'])]}: "
                                    f"{DESC[num[(it['tripod'], it['item_en'])]][0 if ko else 1]} "
                                    f"{pct[it['idx']][0]:.1f}% ({round(pct[it['idx']][0] * pct[it['idx']][1] / 100)}/{pct[it['idx']][1]})", AW, subsequent_indent="   ")
           for it in low}
    nlow = [sum(len(ann[it["idx"]]) for it in its if it["idx"] in lowmark) for _, its in groups]
    rh = [max(.28, n * LH + .08) for n in nlow]
    TOP = .78
    ys = [TOP + sum(rh[:r]) for r in range(len(groups))]
    H = TOP + sum(rh) + .2 + .55
    fig = plt.figure(figsize=(W, H))
    fy = lambda yin: 1 - yin / H
    # author: two halves side by side, each with its own "<10%" column, so that TRIPOD+AI finds no element
    # reported by fewer than 10% of studies while the checklist finds eight items
    XA, WA, XT, XS, XB, WB, XC = 1.20, .38, 1.66, 2.22, 2.46, 1.30, 3.84
    BLUE = "#1F4E79"
    n_tlow = sum(1 for key, _ in groups if isinstance(key, int) and
                 100 * sum(S[s]["tripod"][str(key)] in ("Reported", "Partly reported") for s in S) / len(S) < 10)
    fig.text(XA / W, fy(.02), T(ko, "TRIPOD+AI", ""), fontsize=fs + .5, weight="bold", va="top", color=BLUE)
    fig.text(XB / W, fy(.02), T(ko, "Core checklist (Table 1)", ""), fontsize=fs + .5, weight="bold", va="top", color=OEDGE)
    fig.text(XA / W, fy(.2), T(ko, "% studies", ""), fontsize=fs - .6, va="top", color=BLUE)
    fig.text(XT / W, fy(.2), T(ko, f"Elements\nreported\n<10%: {n_tlow}", f" \n10% \n: {n_tlow}"), fontsize=fs - .6, va="top", color=RED, weight="bold", linespacing=1.0)
    fig.text(XB / W, fy(.2), T(ko, "% meeting each item (ID)", ""), fontsize=fs - .6, va="top", color=OEDGE)
    fig.text(XC / W, fy(.2), T(ko, f"Items met by <10% of studies: {len(low)}\n(red boxes)", f"  10%  : {len(low)}\n( )"), fontsize=fs - .6, va="top", color=RED, weight="bold", linespacing=1.0)
    # legend for the three TRIPOD+AI levels (instead of tick labels on every row)
    NAVYD, SKY = BLUE, "#7FB8C9"  # one stacked column per element: complete (navy), partly (dark sky blue), not reported (white)
    # author: each legend sits under the header of its own half
    def key(x, y, fc, ec, lab, lw=.6):
        fig.patches.append(matplotlib.patches.Rectangle((x / W, fy(y + .07)), .07 / W, .07 / H, facecolor=fc, edgecolor=ec, lw=lw,
                                                        transform=fig.transFigure, figure=fig))
        fig.text((x + .1) / W, fy(y + .035), lab, fontsize=fs - 1.4, va="center")
    for k, (lab, fc) in enumerate([(T(ko, "Full", ""), NAVYD), (T(ko, "Partial", ""), SKY), (T(ko, "None", ""), "white")]):
        key(XA, .36 + k * .12, fc, NAVYD, lab)
    for k, (lab, fc, ec, lw) in enumerate([(T(ko, "Met", ""), ORANGE, OEDGE, .6), (T(ko, "Not met", ""), "white", "#C4C9D0", .6),
                                           (T(ko, "Met by <10%", ""), "white", RED, 1.1)]):
        key(XB, .36 + k * .12, fc, ec, lab, lw)
    fig.add_artist(Line2D([XS / W] * 2, [fy(.02), fy(TOP + sum(rh) + .05)], color=DGREY, lw=.7))
    def deco(a):
        [a.spines[s_].set_visible(False) for s_ in ("top", "right")]
        a.tick_params(labelsize=fs - 1.6, length=1.5, pad=1, width=.5); [a.spines[s_].set_linewidth(.5) for s_ in ("left", "bottom")]
    maxk = max(len(its) for _, its in groups)
    for r, (key, its) in enumerate(groups):
        y0, h = ys[r], rh[r]
        lab = (f"{key}. " + T(ko, TRIPOD[key - 1][1], TRIPOD[key - 1][0])) if isinstance(key, int) else T(ko, "(New) " + CK.GROUPS[key][1], "" + CK.GROUPS[key][0])
        fig.text(0, fy(y0 + h / 2), "\n".join(textwrap.wrap(lab, 22 if not ko else 13)), fontsize=fs if ko else fs - .7, va="center", linespacing=1.0)
        bh = .17
        yb = y0 + (h - bh) / 2 - .02
        aA = fig.add_axes([XA / W, fy(yb + bh), WA / W, bh / H])
        aB = fig.add_axes([XB / W, fy(yb + bh), WB / W, bh / H])
        if isinstance(key, int):
            cnt = {lev: 100 * sum(S[s]["tripod"][str(key)] == lev for s in S) / len(S) for lev, _, _ in levels}
            c_, p_ = cnt["Reported"], cnt["Partly reported"]
            aA.bar(1, 100, width=1.6, facecolor="white", edgecolor=NAVYD, lw=.7, zorder=2)
            aA.bar(1, c_, width=1.6, facecolor=NAVYD, edgecolor=NAVYD, lw=.7, zorder=3)
            aA.bar(1, p_, bottom=c_, width=1.6, facecolor=SKY, edgecolor=NAVYD, lw=.7, zorder=3)
            fig.text((XT + .05) / W, fy(yb + bh / 2), "–", fontsize=fs, va="center", color=DGREY)
        else:
            aA.text(1, 50, T(ko, "no\nelement", ""), ha="center", va="center", fontsize=fs - 2, color=DGREY, linespacing=1.0)
        aA.set_xticks([]); aA.set_xlim(-.6, 2.6); aA.set_ylim(0, 100); aA.set_yticks([0, 100]); deco(aA)
        lines = []
        for x, it in enumerate(its):
            v, n = pct[it["idx"]]
            isl = it["idx"] in lowmark
            aB.add_patch(matplotlib.patches.Rectangle((x - .34, 0), .68, 100, fill=False, edgecolor=RED if isl else "#C4C9D0", lw=1.1 if isl else .5, zorder=4 if isl else 2))
            aB.bar(x, v, color=ORANGE, width=.68, edgecolor=OEDGE, linewidth=.4, zorder=3)
            aB.text(x, -16, str(num[(key, it["item_en"])]).replace("RC", ""), ha="center", va="top", fontsize=fs - 1.4)
            if isl:
                aB.text(x + .38, 100, lowmark[it["idx"]], ha="left", va="top", fontsize=fs - .2, color=RED, weight="bold")
                lines += ann[it["idx"]]
        aB.set_xticks([]); aB.set_xlim(-.5, maxk - .5); aB.set_ylim(0, 100); aB.set_yticks([0, 100]); deco(aB)
        for k, ln in enumerate(lines):
            fig.text(XC / W, fy(y0 + h / 2 + (k - (len(lines) - 1) / 2) * LH), ln, fontsize=fa, va="center", color="#7A1010")
    y0 = TOP + sum(rh) + .12
    fig.add_artist(Line2D([0, 1], [fy(y0 - .05)] * 2, color=DGREY, lw=.6))
    fig.text(0, fy(y0 + .2), T(ko, "Overall (studies)", ""), fontsize=fs, weight="bold", va="center")
    aA = fig.add_axes([XA / W, fy(y0 + .3), (XS - .12 - XA) / W, .22 / H])
    aB = fig.add_axes([XB / W, fy(y0 + .3), WB / W, .22 / H])
    aA.hist([sum(S[s]["tripod"][str(i)] == "Reported" for i in range(1, 20)) for s in S], bins=np.arange(-.5, 20, 1), color=BLUE, rwidth=.85)
    aA.set_xlim(-.5, 19.5); aA.set_xticks([0, 10, 19]); deco(aA)
    aA.set_xlabel(T(ko, "Elements complete (of 19)", ""), fontsize=fs - 1.2, labelpad=1)
    sc = [i for i in items if i["scored"]]
    tot = [sum(S[s]["items"].get(str(i["idx"]), False) for i in sc) for s in S]
    aB.hist(tot, bins=np.arange(-.5, len(sc) + 1, 1), color=ORANGE, edgecolor=OEDGE, linewidth=.3, rwidth=.85)
    aB.set_xlim(-.5, len(sc) + .5); aB.set_xticks([0, 15, 30, 45]); deco(aB)
    aB.set_xlabel(T(ko, f"Core items met (of {len(sc)})", f"   ({len(sc)} )"), fontsize=fs - 1.2, labelpad=1)
    save(fig, "fig24_checklist_v18_detail", ko, tight=True)



def figure_checklist_v20_detail(lang="en"):
    """an appendix figure of an earlier draft (= v15 Figure 5 with the v16 items) (author): drawn at the printed size (text width 5.4 in, about 0.8 of the text height) so
    the type is legible. Per TRIPOD+AI-derived element: left, the 3-level TRIPOD+AI judgement; middle, every core item
    as a box filled to the percentage of studies meeting it (IDs as in Table 1); items met by fewer than 10% are boxed
    in red with a circled number, and named with their percentage at the right of the same row. Last row: overall."""
    import checklist_v20 as CK, checklist_v20_table as TB
    from checklist_v12 import TRIPOD
    import textwrap
    style(lang); ko = lang == "ko"
    t = json.load(open(os.path.join(ROOT, "results/derived/checklist_v20_scores.json")))
    items, S = t["items"], t["studies"]
    order = TB.ordered()
    num = {(r[1], r[3]): r[0] for r in order}
    name = {(r[1], r[3]): (r[2] if ko else r[3]) for r in order}
    groups = []
    for key in list(range(1, 20)) + ["importance", "after"]:
        idx = [i for i in items if i["tripod"] == key and i["scored"]]
        if idx:
            groups.append((key, sorted(idx, key=lambda i: num[(key, i["item_en"])])))
    levels = [("Not reported", T(ko, "Not", ""), "#C9CED6"), ("Partly reported", T(ko, "Partly", ""), "#7FB8C9"), ("Reported", T(ko, "Completely", ""), "#1F4E79")]
    ORANGE, OEDGE, RED = "#F28E2B", "#B85C00", "#D62728"
    circ = "①②③④⑤⑥⑦⑧⑨⑩"
    pct = {}
    for key, its in groups:
        for it in its:
            v = [S[s]["items"][str(it["idx"])] for s in S if str(it["idx"]) in S[s]["items"]]
            pct[it["idx"]] = (100 * sum(v) / len(v), len(v))
    low = [it for _, its in groups for it in its if pct[it["idx"]][0] < 10]  # plotting order
    lowmark = {it["idx"]: circ[k] for k, it in enumerate(low)}
    W = 5.4
    fs, fa = 6.6, 6.2                               # type size at print (pt)
    LH = fa * 1.25 / 72                             # annotation line height (in)
    AW = 30 if not ko else 24                       # annotation wrap (characters)
    from checklist_desc import DESC  # author: say what each item checks
    ann = {it["idx"]: textwrap.wrap(f"{lowmark[it['idx']]} {num[(it['tripod'], it['item_en'])]} {name[(it['tripod'], it['item_en'])]}: "
                                    f"{DESC[num[(it['tripod'], it['item_en'])]][0 if ko else 1]} "
                                    f"{pct[it['idx']][0]:.1f}% ({round(pct[it['idx']][0] * pct[it['idx']][1] / 100)}/{pct[it['idx']][1]})", AW, subsequent_indent="   ")
           for it in low}
    nlow = [sum(len(ann[it["idx"]]) for it in its if it["idx"] in lowmark) for _, its in groups]
    rh = [max(.28, n * LH + .08) for n in nlow]
    TOP = .78
    ys = [TOP + sum(rh[:r]) for r in range(len(groups))]
    H = TOP + sum(rh) + .2 + .55
    fig = plt.figure(figsize=(W, H))
    fy = lambda yin: 1 - yin / H
    # author: two halves side by side, each with its own "<10%" column, so that TRIPOD+AI finds no element
    # reported by fewer than 10% of studies while the checklist finds eight items
    XA, WA, XT, XS, XB, WB, XC = 1.20, .38, 1.66, 2.22, 2.46, 1.30, 3.84
    BLUE = "#1F4E79"
    n_tlow = sum(1 for key, _ in groups if isinstance(key, int) and
                 100 * sum(S[s]["tripod"][str(key)] in ("Reported", "Partly reported") for s in S) / len(S) < 10)
    fig.text(XA / W, fy(.02), T(ko, "TRIPOD+AI", ""), fontsize=fs + .5, weight="bold", va="top", color=BLUE)
    fig.text(XB / W, fy(.02), T(ko, "Core checklist (Table 1)", ""), fontsize=fs + .5, weight="bold", va="top", color=OEDGE)
    fig.text(XA / W, fy(.2), T(ko, "% studies", ""), fontsize=fs - .6, va="top", color=BLUE)
    fig.text(XT / W, fy(.2), T(ko, f"Elements\nreported\n<10%: {n_tlow}", f" \n10% \n: {n_tlow}"), fontsize=fs - .6, va="top", color=RED, weight="bold", linespacing=1.0)
    fig.text(XB / W, fy(.2), T(ko, "% meeting each item (ID)", ""), fontsize=fs - .6, va="top", color=OEDGE)
    fig.text(XC / W, fy(.2), T(ko, f"Items met by <10% of studies: {len(low)}\n(red boxes)", f"  10%  : {len(low)}\n( )"), fontsize=fs - .6, va="top", color=RED, weight="bold", linespacing=1.0)
    # legend for the three TRIPOD+AI levels (instead of tick labels on every row)
    NAVYD, SKY = BLUE, "#7FB8C9"  # one stacked column per element: complete (navy), partly (dark sky blue), not reported (white)
    # author: each legend sits under the header of its own half
    def key(x, y, fc, ec, lab, lw=.6):
        fig.patches.append(matplotlib.patches.Rectangle((x / W, fy(y + .07)), .07 / W, .07 / H, facecolor=fc, edgecolor=ec, lw=lw,
                                                        transform=fig.transFigure, figure=fig))
        fig.text((x + .1) / W, fy(y + .035), lab, fontsize=fs - 1.4, va="center")
    for k, (lab, fc) in enumerate([(T(ko, "Full", ""), NAVYD), (T(ko, "Partial", ""), SKY), (T(ko, "None", ""), "white")]):
        key(XA, .36 + k * .12, fc, NAVYD, lab)
    for k, (lab, fc, ec, lw) in enumerate([(T(ko, "Met", ""), ORANGE, OEDGE, .6), (T(ko, "Not met", ""), "white", "#C4C9D0", .6),
                                           (T(ko, "Met by <10%", ""), "white", RED, 1.1)]):
        key(XB, .36 + k * .12, fc, ec, lab, lw)
    fig.add_artist(Line2D([XS / W] * 2, [fy(.02), fy(TOP + sum(rh) + .05)], color=DGREY, lw=.7))
    def deco(a):
        [a.spines[s_].set_visible(False) for s_ in ("top", "right")]
        a.tick_params(labelsize=fs - 1.6, length=1.5, pad=1, width=.5); [a.spines[s_].set_linewidth(.5) for s_ in ("left", "bottom")]
    maxk = max(len(its) for _, its in groups)
    for r, (key, its) in enumerate(groups):
        y0, h = ys[r], rh[r]
        lab = (f"{key}. " + T(ko, TRIPOD[key - 1][1], TRIPOD[key - 1][0])) if isinstance(key, int) else T(ko, "(New) " + CK.GROUPS[key][1], "" + CK.GROUPS[key][0])
        fig.text(0, fy(y0 + h / 2), "\n".join(textwrap.wrap(lab, 22 if not ko else 13)), fontsize=fs if ko else fs - .7, va="center", linespacing=1.0)
        bh = .17
        yb = y0 + (h - bh) / 2 - .02
        aA = fig.add_axes([XA / W, fy(yb + bh), WA / W, bh / H])
        aB = fig.add_axes([XB / W, fy(yb + bh), WB / W, bh / H])
        if isinstance(key, int):
            cnt = {lev: 100 * sum(S[s]["tripod"][str(key)] == lev for s in S) / len(S) for lev, _, _ in levels}
            c_, p_ = cnt["Reported"], cnt["Partly reported"]
            aA.bar(1, 100, width=1.6, facecolor="white", edgecolor=NAVYD, lw=.7, zorder=2)
            aA.bar(1, c_, width=1.6, facecolor=NAVYD, edgecolor=NAVYD, lw=.7, zorder=3)
            aA.bar(1, p_, bottom=c_, width=1.6, facecolor=SKY, edgecolor=NAVYD, lw=.7, zorder=3)
            fig.text((XT + .05) / W, fy(yb + bh / 2), "–", fontsize=fs, va="center", color=DGREY)
        else:
            aA.text(1, 50, T(ko, "no\nelement", ""), ha="center", va="center", fontsize=fs - 2, color=DGREY, linespacing=1.0)
        aA.set_xticks([]); aA.set_xlim(-.6, 2.6); aA.set_ylim(0, 100); aA.set_yticks([0, 100]); deco(aA)
        lines = []
        for x, it in enumerate(its):
            v, n = pct[it["idx"]]
            isl = it["idx"] in lowmark
            aB.add_patch(matplotlib.patches.Rectangle((x - .34, 0), .68, 100, fill=False, edgecolor=RED if isl else "#C4C9D0", lw=1.1 if isl else .5, zorder=4 if isl else 2))
            aB.bar(x, v, color=ORANGE, width=.68, edgecolor=OEDGE, linewidth=.4, zorder=3)
            aB.text(x, -16, str(num[(key, it["item_en"])]).replace("RC", ""), ha="center", va="top", fontsize=fs - 1.4)
            if isl:
                aB.text(x + .38, 100, lowmark[it["idx"]], ha="left", va="top", fontsize=fs - .2, color=RED, weight="bold")
                lines += ann[it["idx"]]
        aB.set_xticks([]); aB.set_xlim(-.5, maxk - .5); aB.set_ylim(0, 100); aB.set_yticks([0, 100]); deco(aB)
        for k, ln in enumerate(lines):
            fig.text(XC / W, fy(y0 + h / 2 + (k - (len(lines) - 1) / 2) * LH), ln, fontsize=fa, va="center", color="#7A1010")
    y0 = TOP + sum(rh) + .12
    fig.add_artist(Line2D([0, 1], [fy(y0 - .05)] * 2, color=DGREY, lw=.6))
    fig.text(0, fy(y0 + .2), T(ko, "Overall (studies)", ""), fontsize=fs, weight="bold", va="center")
    aA = fig.add_axes([XA / W, fy(y0 + .3), (XS - .12 - XA) / W, .22 / H])
    aB = fig.add_axes([XB / W, fy(y0 + .3), WB / W, .22 / H])
    aA.hist([sum(S[s]["tripod"][str(i)] == "Reported" for i in range(1, 20)) for s in S], bins=np.arange(-.5, 20, 1), color=BLUE, rwidth=.85)
    aA.set_xlim(-.5, 19.5); aA.set_xticks([0, 10, 19]); deco(aA)
    aA.set_xlabel(T(ko, "Elements complete (of 19)", ""), fontsize=fs - 1.2, labelpad=1)
    sc = [i for i in items if i["scored"]]
    tot = [sum(S[s]["items"].get(str(i["idx"]), False) for i in sc) for s in S]
    aB.hist(tot, bins=np.arange(-.5, len(sc) + 1, 1), color=ORANGE, edgecolor=OEDGE, linewidth=.3, rwidth=.85)
    aB.set_xlim(-.5, len(sc) + .5); aB.set_xticks([0, 15, 30, 45]); deco(aB)
    aB.set_xlabel(T(ko, f"Core items met (of {len(sc)})", f"   ({len(sc)} )"), fontsize=fs - 1.2, labelpad=1)
    save(fig, "fig26_checklist_v20", ko, tight=True)


def figure_checklist_v21_detail(lang="en"):
    """an appendix figure of an earlier draft (= v15 Figure 5 with the v16 items) (author): drawn at the printed size (text width 5.4 in, about 0.8 of the text height) so
    the type is legible. Per TRIPOD+AI-derived element: left, the 3-level TRIPOD+AI judgement; middle, every core item
    as a box filled to the percentage of studies meeting it (IDs as in Table 1); items met by fewer than 10% are boxed
    in red with a circled number, and named with their percentage at the right of the same row. Last row: overall."""
    import checklist_v21 as CK, checklist_v21_table as TB
    from checklist_v12 import TRIPOD
    import textwrap
    style(lang); ko = lang == "ko"
    t = json.load(open(os.path.join(ROOT, "results/derived/checklist_v21_scores.json")))
    items, S = t["items"], t["studies"]
    order = TB.ordered()
    num = {(r[1], r[3]): r[0] for r in order}
    pub = {r[0]: f"C{k + 1:02d}" for k, r in enumerate(order)}  # v21: publication IDs as in Table 1
    name = {(r[1], r[3]): (r[2] if ko else r[3]) for r in order}
    groups = []
    for key in list(range(1, 20)) + ["importance", "after"]:
        idx = [i for i in items if i["tripod"] == key and i["scored"]]
        if idx:
            groups.append((key, sorted(idx, key=lambda i: num[(key, i["item_en"])])))
    levels = [("Not reported", T(ko, "Not", ""), "#C9CED6"), ("Partly reported", T(ko, "Partly", ""), "#7FB8C9"), ("Reported", T(ko, "Completely", ""), "#1F4E79")]
    ORANGE, OEDGE, RED = "#F28E2B", "#B85C00", "#D62728"
    circ = "①②③④⑤⑥⑦⑧⑨⑩"
    pct = {}
    for key, its in groups:
        for it in its:
            v = [S[s]["items"][str(it["idx"])] for s in S if str(it["idx"]) in S[s]["items"]]
            pct[it["idx"]] = (100 * sum(v) / len(v), len(v))
    low = [it for _, its in groups for it in its if pct[it["idx"]][0] < 10]  # plotting order
    lowmark = {it["idx"]: circ[k] for k, it in enumerate(low)}
    W = 5.4
    fs, fa = 6.6, 6.2                               # type size at print (pt)
    LH = fa * 1.25 / 72                             # annotation line height (in)
    AW = 30 if not ko else 24                       # annotation wrap (characters)
    from checklist_desc import DESC  # author: say what each item checks
    ann = {it["idx"]: textwrap.wrap(f"{lowmark[it['idx']]} {pub[num[(it['tripod'], it['item_en'])]]} {name[(it['tripod'], it['item_en'])]}: "
                                    f"{DESC[num[(it['tripod'], it['item_en'])]][0 if ko else 1]} "
                                    f"{pct[it['idx']][0]:.1f}% ({round(pct[it['idx']][0] * pct[it['idx']][1] / 100)}/{pct[it['idx']][1]})", AW, subsequent_indent="   ")
           for it in low}
    nlow = [sum(len(ann[it["idx"]]) for it in its if it["idx"] in lowmark) for _, its in groups]
    rh = [max(.28, n * LH + .08) for n in nlow]
    TOP = .78
    ys = [TOP + sum(rh[:r]) for r in range(len(groups))]
    H = TOP + sum(rh) + .2 + .55
    fig = plt.figure(figsize=(W, H))
    fy = lambda yin: 1 - yin / H
    # author: two halves side by side, each with its own "<10%" column, so that TRIPOD+AI finds no element
    # reported by fewer than 10% of studies while the checklist finds eight items
    XA, WA, XT, XS, XB, WB, XC = 1.20, .38, 1.66, 2.22, 2.46, 1.30, 3.84
    BLUE = "#1F4E79"
    n_tlow = sum(1 for key, _ in groups if isinstance(key, int) and
                 100 * sum(S[s]["tripod"][str(key)] in ("Reported", "Partly reported") for s in S) / len(S) < 10)
    n_tel = sum(isinstance(key, int) for key, _ in groups)
    fig.text(XA / W, fy(.02), T(ko, "TRIPOD+AI", ""), fontsize=fs + .5, weight="bold", va="top", color=BLUE)
    fig.text(XB / W, fy(.02), T(ko, "Core checklist (Table 1)", ""), fontsize=fs + .5, weight="bold", va="top", color=OEDGE)
    fig.text(XA / W, fy(.2), T(ko, "% studies", ""), fontsize=fs - .6, va="top", color=BLUE)
    fig.text(XT / W, fy(.2), T(ko, f"Elements\nreported\n<10%: {n_tlow}\n(of {n_tel}\nshown)", f" \n10% \n: {n_tlow}\n(\n{n_tel} )"), fontsize=fs - .6, va="top", color=RED, weight="bold", linespacing=1.0)
    fig.text(XB / W, fy(.2), T(ko, "% meeting each item (ID)", ""), fontsize=fs - .6, va="top", color=OEDGE)
    fig.text(XC / W, fy(.2), T(ko, f"Items met by <10% of studies: {len(low)}\n(red boxes)", f"  10%  : {len(low)}\n( )"), fontsize=fs - .6, va="top", color=RED, weight="bold", linespacing=1.0)
    # legend for the three TRIPOD+AI levels (instead of tick labels on every row)
    NAVYD, SKY = BLUE, "#7FB8C9"  # one stacked column per element: complete (navy), partly (dark sky blue), not reported (white)
    # author: each legend sits under the header of its own half
    def key(x, y, fc, ec, lab, lw=.6):
        fig.patches.append(matplotlib.patches.Rectangle((x / W, fy(y + .07)), .07 / W, .07 / H, facecolor=fc, edgecolor=ec, lw=lw,
                                                        transform=fig.transFigure, figure=fig))
        fig.text((x + .1) / W, fy(y + .035), lab, fontsize=fs - 1.4, va="center")
    for k, (lab, fc) in enumerate([(T(ko, "Full", ""), NAVYD), (T(ko, "Partial", ""), SKY), (T(ko, "None", ""), "white")]):
        key(XA, .36 + k * .12, fc, NAVYD, lab)
    for k, (lab, fc, ec, lw) in enumerate([(T(ko, "Met", ""), ORANGE, OEDGE, .6), (T(ko, "Not met", ""), "white", "#C4C9D0", .6),
                                           (T(ko, "Met by <10%", ""), "white", RED, 1.1)]):
        key(XB, .36 + k * .12, fc, ec, lab, lw)
    fig.add_artist(Line2D([XS / W] * 2, [fy(.02), fy(TOP + sum(rh) + .05)], color=DGREY, lw=.7))
    def deco(a):
        [a.spines[s_].set_visible(False) for s_ in ("top", "right")]
        a.tick_params(labelsize=fs - 1.6, length=1.5, pad=1, width=.5); [a.spines[s_].set_linewidth(.5) for s_ in ("left", "bottom")]
    maxk = max(len(its) for _, its in groups)
    for r, (key, its) in enumerate(groups):
        y0, h = ys[r], rh[r]
        lab = (f"{key}. " + T(ko, TRIPOD[key - 1][1], TRIPOD[key - 1][0])) if isinstance(key, int) else T(ko, "(New) " + CK.GROUPS[key][1], "" + CK.GROUPS[key][0])
        fig.text(0, fy(y0 + h / 2), "\n".join(textwrap.wrap(lab, 22 if not ko else 13)), fontsize=fs if ko else fs - .7, va="center", linespacing=1.0)
        bh = .17
        yb = y0 + (h - bh) / 2 - .02
        aA = fig.add_axes([XA / W, fy(yb + bh), WA / W, bh / H])
        aB = fig.add_axes([XB / W, fy(yb + bh), WB / W, bh / H])
        if isinstance(key, int):
            cnt = {lev: 100 * sum(S[s]["tripod"][str(key)] == lev for s in S) / len(S) for lev, _, _ in levels}
            c_, p_ = cnt["Reported"], cnt["Partly reported"]
            aA.bar(1, 100, width=1.6, facecolor="white", edgecolor=NAVYD, lw=.7, zorder=2)
            aA.bar(1, c_, width=1.6, facecolor=NAVYD, edgecolor=NAVYD, lw=.7, zorder=3)
            aA.bar(1, p_, bottom=c_, width=1.6, facecolor=SKY, edgecolor=NAVYD, lw=.7, zorder=3)
            fig.text((XT + .05) / W, fy(yb + bh / 2), "–", fontsize=fs, va="center", color=DGREY)
        else:
            aA.text(1, 50, T(ko, "no\nelement", ""), ha="center", va="center", fontsize=fs - 2, color=DGREY, linespacing=1.0)
        aA.set_xticks([]); aA.set_xlim(-.6, 2.6); aA.set_ylim(0, 100); aA.set_yticks([0, 100]); deco(aA)
        lines = []
        for x, it in enumerate(its):
            v, n = pct[it["idx"]]
            isl = it["idx"] in lowmark
            aB.add_patch(matplotlib.patches.Rectangle((x - .34, 0), .68, 100, fill=False, edgecolor=RED if isl else "#C4C9D0", lw=1.1 if isl else .5, zorder=4 if isl else 2))
            aB.bar(x, v, color=ORANGE, width=.68, edgecolor=OEDGE, linewidth=.4, zorder=3)
            aB.text(x, -16, pub[num[(key, it["item_en"])]].replace("C", ""), ha="center", va="top", fontsize=fs - 1.4)
            if isl:
                aB.text(x + .38, 100, lowmark[it["idx"]], ha="left", va="top", fontsize=fs - .2, color=RED, weight="bold")
                lines += ann[it["idx"]]
        aB.set_xticks([]); aB.set_xlim(-.5, maxk - .5); aB.set_ylim(0, 100); aB.set_yticks([0, 100]); deco(aB)
        for k, ln in enumerate(lines):
            fig.text(XC / W, fy(y0 + h / 2 + (k - (len(lines) - 1) / 2) * LH), ln, fontsize=fa, va="center", color="#7A1010")
    y0 = TOP + sum(rh) + .12
    fig.add_artist(Line2D([0, 1], [fy(y0 - .05)] * 2, color=DGREY, lw=.6))
    fig.text(0, fy(y0 + .2), T(ko, "Overall (studies)", ""), fontsize=fs, weight="bold", va="center")
    aA = fig.add_axes([XA / W, fy(y0 + .3), (XS - .12 - XA) / W, .22 / H])
    aB = fig.add_axes([XB / W, fy(y0 + .3), WB / W, .22 / H])
    aA.hist([sum(S[s]["tripod"][str(i)] == "Reported" for i in range(1, 20)) for s in S], bins=np.arange(-.5, 20, 1), color=BLUE, rwidth=.85)
    aA.set_xlim(-.5, 19.5); aA.set_xticks([0, 10, 19]); deco(aA)
    aA.set_xlabel(T(ko, "Elements complete (of 19)", ""), fontsize=fs - 1.2, labelpad=1)
    sc = [i for i in items if i["scored"]]
    tot = [sum(S[s]["items"].get(str(i["idx"]), False) for i in sc) for s in S]
    aB.hist(tot, bins=np.arange(-.5, len(sc) + 1, 1), color=ORANGE, edgecolor=OEDGE, linewidth=.3, rwidth=.85)
    aB.set_xlim(-.5, len(sc) + .5); aB.set_xticks([0, 15, 30, len(sc)]); deco(aB)
    aB.set_xlabel(T(ko, f"Core items met (of {len(sc)})", f"   ({len(sc)} )"), fontsize=fs - 1.2, labelpad=1)
    save(fig, "fig27_checklist_v21", ko, tight=True)


def figure_checklist_v22_detail(lang="en"):
    """an appendix figure of an earlier draft (= v15 Figure 5 with the v16 items) (author): drawn at the printed size (text width 5.4 in, about 0.8 of the text height) so
    the type is legible. Per TRIPOD+AI-derived element: left, the 3-level TRIPOD+AI judgement; middle, every core item
    as a box filled to the percentage of studies meeting it (IDs as in Table 1); items met by fewer than 10% are boxed
    in red with a circled number, and named with their percentage at the right of the same row. Last row: overall."""
    import checklist_v22 as CK, checklist_v22_table as TB
    from checklist_v12 import TRIPOD
    import textwrap
    style(lang); ko = lang == "ko"
    t = json.load(open(os.path.join(ROOT, "results/derived/checklist_v22_scores.json")))
    items, S = t["items"], t["studies"]
    order = TB.ordered()
    num = {(r[1], r[3]): r[0] for r in order}
    pub = {r[0]: f"C{k + 1:02d}" for k, r in enumerate(order)}  # v21: publication IDs as in Table 1
    name = {(r[1], r[3]): (r[2] if ko else r[3]) for r in order}
    groups = []
    for key in list(range(1, 20)) + ["importance", "after"]:
        idx = [i for i in items if i["tripod"] == key and i["scored"]]
        if idx:
            groups.append((key, sorted(idx, key=lambda i: pub[num[(key, i["item_en"])]])))
    levels = [("Not reported", T(ko, "Not", ""), "#C9CED6"), ("Partly reported", T(ko, "Partly", ""), "#7FB8C9"), ("Reported", T(ko, "Completely", ""), "#1F4E79")]
    ORANGE, OEDGE, RED = "#F28E2B", "#B85C00", "#D62728"
    circ = "①②③④⑤⑥⑦⑧⑨⑩"
    pct = {}
    for key, its in groups:
        for it in its:
            v = [S[s]["items"][str(it["idx"])] for s in S if str(it["idx"]) in S[s]["items"]]
            pct[it["idx"]] = (100 * sum(v) / len(v), len(v))
    low = [it for _, its in groups for it in its if pct[it["idx"]][0] < 10]  # plotting order
    lowmark = {it["idx"]: circ[k] for k, it in enumerate(low)}
    W = 5.4
    fs, fa = 6.6, 6.2                               # type size at print (pt)
    LH = fa * 1.25 / 72                             # annotation line height (in)
    AW = 30 if not ko else 24                       # annotation wrap (characters)
    from checklist_desc import DESC  # author: say what each item checks
    ann = {it["idx"]: textwrap.wrap(f"{lowmark[it['idx']]} {pub[num[(it['tripod'], it['item_en'])]]} {name[(it['tripod'], it['item_en'])]}: "
                                    f"{DESC[num[(it['tripod'], it['item_en'])]][0 if ko else 1]} "
                                    f"{pct[it['idx']][0]:.1f}% ({round(pct[it['idx']][0] * pct[it['idx']][1] / 100)}/{pct[it['idx']][1]})", AW, subsequent_indent="   ")
           for it in low}
    nlow = [sum(len(ann[it["idx"]]) for it in its if it["idx"] in lowmark) for _, its in groups]
    rh = [max(.28, n * LH + .08) for n in nlow]
    TOP = .78
    ys = [TOP + sum(rh[:r]) for r in range(len(groups))]
    H = TOP + sum(rh) + .2 + .55
    fig = plt.figure(figsize=(W, H))
    fy = lambda yin: 1 - yin / H
    # author: two halves side by side, each with its own "<10%" column, so that TRIPOD+AI finds no element
    # reported by fewer than 10% of studies while the checklist finds eight items
    XA, WA, XT, XS, XB, WB, XC = 1.20, .38, 1.66, 2.22, 2.46, 1.30, 3.84
    BLUE = "#1F4E79"
    n_tlow = sum(1 for key, _ in groups if isinstance(key, int) and
                 100 * sum(S[s]["tripod"][str(key)] in ("Reported", "Partly reported") for s in S) / len(S) < 10)
    n_tel = sum(isinstance(key, int) for key, _ in groups)
    fig.text(XA / W, fy(.02), T(ko, "TRIPOD+AI", ""), fontsize=fs + .5, weight="bold", va="top", color=BLUE)
    fig.text(XB / W, fy(.02), T(ko, "Core checklist (Table 1)", ""), fontsize=fs + .5, weight="bold", va="top", color=OEDGE)
    fig.text(XA / W, fy(.2), T(ko, "% studies", ""), fontsize=fs - .6, va="top", color=BLUE)
    fig.text(XT / W, fy(.2), T(ko, f"Elements\nreported\n<10%: {n_tlow}\n(of {n_tel}\nshown)", f" \n10% \n: {n_tlow}\n(\n{n_tel} )"), fontsize=fs - .6, va="top", color=RED, weight="bold", linespacing=1.0)
    fig.text(XB / W, fy(.2), T(ko, "% meeting each item (ID)", ""), fontsize=fs - .6, va="top", color=OEDGE)
    fig.text(XC / W, fy(.2), T(ko, f"Items met by <10% of studies: {len(low)}\n(red boxes)", f"  10%  : {len(low)}\n( )"), fontsize=fs - .6, va="top", color=RED, weight="bold", linespacing=1.0)
    # legend for the three TRIPOD+AI levels (instead of tick labels on every row)
    NAVYD, SKY = BLUE, "#7FB8C9"  # one stacked column per element: complete (navy), partly (dark sky blue), not reported (white)
    # author: each legend sits under the header of its own half
    def key(x, y, fc, ec, lab, lw=.6):
        fig.patches.append(matplotlib.patches.Rectangle((x / W, fy(y + .07)), .07 / W, .07 / H, facecolor=fc, edgecolor=ec, lw=lw,
                                                        transform=fig.transFigure, figure=fig))
        fig.text((x + .1) / W, fy(y + .035), lab, fontsize=fs - 1.4, va="center")
    for k, (lab, fc) in enumerate([(T(ko, "Full", ""), NAVYD), (T(ko, "Partial", ""), SKY), (T(ko, "None", ""), "white")]):
        key(XA, .36 + k * .12, fc, NAVYD, lab)
    for k, (lab, fc, ec, lw) in enumerate([(T(ko, "Met", ""), ORANGE, OEDGE, .6), (T(ko, "Not met", ""), "white", "#C4C9D0", .6),
                                           (T(ko, "Met by <10%", ""), "white", RED, 1.1)]):
        key(XB, .36 + k * .12, fc, ec, lab, lw)
    fig.add_artist(Line2D([XS / W] * 2, [fy(.02), fy(TOP + sum(rh) + .05)], color=DGREY, lw=.7))
    def deco(a):
        [a.spines[s_].set_visible(False) for s_ in ("top", "right")]
        a.tick_params(labelsize=fs - 1.6, length=1.5, pad=1, width=.5); [a.spines[s_].set_linewidth(.5) for s_ in ("left", "bottom")]
    maxk = max(len(its) for _, its in groups)
    for r, (key, its) in enumerate(groups):
        y0, h = ys[r], rh[r]
        lab = (f"{key}. " + T(ko, TRIPOD[key - 1][1], TRIPOD[key - 1][0])) if isinstance(key, int) else T(ko, "(New) " + CK.GROUPS[key][1], "" + CK.GROUPS[key][0])
        fig.text(0, fy(y0 + h / 2), "\n".join(textwrap.wrap(lab, 22 if not ko else 13)), fontsize=fs if ko else fs - .7, va="center", linespacing=1.0)
        bh = .17
        yb = y0 + (h - bh) / 2 - .02
        aA = fig.add_axes([XA / W, fy(yb + bh), WA / W, bh / H])
        aB = fig.add_axes([XB / W, fy(yb + bh), WB / W, bh / H])
        if isinstance(key, int):
            cnt = {lev: 100 * sum(S[s]["tripod"][str(key)] == lev for s in S) / len(S) for lev, _, _ in levels}
            c_, p_ = cnt["Reported"], cnt["Partly reported"]
            aA.bar(1, 100, width=1.6, facecolor="white", edgecolor=NAVYD, lw=.7, zorder=2)
            aA.bar(1, c_, width=1.6, facecolor=NAVYD, edgecolor=NAVYD, lw=.7, zorder=3)
            aA.bar(1, p_, bottom=c_, width=1.6, facecolor=SKY, edgecolor=NAVYD, lw=.7, zorder=3)
            fig.text((XT + .05) / W, fy(yb + bh / 2), "–", fontsize=fs, va="center", color=DGREY)
        else:
            aA.text(1, 50, T(ko, "no\nelement", ""), ha="center", va="center", fontsize=fs - 2, color=DGREY, linespacing=1.0)
        aA.set_xticks([]); aA.set_xlim(-.6, 2.6); aA.set_ylim(0, 100); aA.set_yticks([0, 100]); deco(aA)
        lines = []
        for x, it in enumerate(its):
            v, n = pct[it["idx"]]
            isl = it["idx"] in lowmark
            aB.add_patch(matplotlib.patches.Rectangle((x - .34, 0), .68, 100, fill=False, edgecolor=RED if isl else "#C4C9D0", lw=1.1 if isl else .5, zorder=4 if isl else 2))
            aB.bar(x, v, color=ORANGE, width=.68, edgecolor=OEDGE, linewidth=.4, zorder=3)
            aB.text(x, -16, pub[num[(key, it["item_en"])]].replace("C", ""), ha="center", va="top", fontsize=fs - 1.4)
            if isl:
                aB.text(x + .38, 100, lowmark[it["idx"]], ha="left", va="top", fontsize=fs - .2, color=RED, weight="bold")
                lines += ann[it["idx"]]
        aB.set_xticks([]); aB.set_xlim(-.5, maxk - .5); aB.set_ylim(0, 100); aB.set_yticks([0, 100]); deco(aB)
        for k, ln in enumerate(lines):
            fig.text(XC / W, fy(y0 + h / 2 + (k - (len(lines) - 1) / 2) * LH), ln, fontsize=fa, va="center", color="#7A1010")
    y0 = TOP + sum(rh) + .12
    fig.add_artist(Line2D([0, 1], [fy(y0 - .05)] * 2, color=DGREY, lw=.6))
    fig.text(0, fy(y0 + .2), T(ko, "Overall (studies)", ""), fontsize=fs, weight="bold", va="center")
    aA = fig.add_axes([XA / W, fy(y0 + .3), (XS - .12 - XA) / W, .22 / H])
    aB = fig.add_axes([XB / W, fy(y0 + .3), WB / W, .22 / H])
    aA.hist([sum(S[s]["tripod"][str(i)] == "Reported" for i in range(1, 20)) for s in S], bins=np.arange(-.5, 20, 1), color=BLUE, rwidth=.85)
    aA.set_xlim(-.5, 19.5); aA.set_xticks([0, 10, 19]); deco(aA)
    aA.set_xlabel(T(ko, "Elements complete (of 19)", ""), fontsize=fs - 1.2, labelpad=1)
    sc = [i for i in items if i["scored"]]
    tot = [sum(S[s]["items"].get(str(i["idx"]), False) for i in sc) for s in S]
    aB.hist(tot, bins=np.arange(-.5, len(sc) + 1, 1), color=ORANGE, edgecolor=OEDGE, linewidth=.3, rwidth=.85)
    aB.set_xlim(-.5, len(sc) + .5); aB.set_xticks([0, 15, 30, len(sc)]); deco(aB)
    aB.set_xlabel(T(ko, f"Core items met (of {len(sc)})", f"   ({len(sc)} )"), fontsize=fs - 1.2, labelpad=1)
    save(fig, "fig28_checklist_v22", ko, tight=True)

def figure_checklist_v18(lang="en"):
    """v17 Figure 5 (prompt 135; KNHANES-specific and all-item rows marked as cross-cutting). Was v16 Figure 5 (prompt 134): what the item-level checklist adds. (A) Among studies judged completely reported on a
    TRIPOD+AI-derived element, the per-study percentage of that element's core items met; (B) per-study percentage met by
    reproduction stage and for KNHANES-specific items; (C) the least reported core items. Drawn at print size."""
    import checklist_v18 as CK
    from checklist_v12 import TRIPOD
    style(lang); ko = lang == "ko"
    t = json.load(open(os.path.join(ROOT, "results/derived/checklist_v18_scores.json")))
    items, S = t["items"], t["studies"]
    I = {str(i["idx"]): i for i in items}
    ORANGE, OEDGE, RED, BLUE = "#F28E2B", "#B85C00", "#D62728", "#1F4E79"
    fs = 7.0
    rng = np.random.default_rng(7)

    def score(st, f):
        v = [b for k, b in st["items"].items() if f(I[k])]
        return 100 * sum(v) / len(v) if v else None

    # A: elements with >= 3 core items (fewer give only 0/50/100%) and >= 20 studies completely reported
    A = []
    for el in range(1, 20):
        its = [i for i in items if i["tripod"] == el]
        if len(its) < 3:
            continue
        v = [score(st, lambda i, el=el: i["tripod"] == el) for st in S.values() if st["tripod"][str(el)] == "Reported"]
        v = [x for x in v if x is not None]
        if len(v) >= 20:
            A.append((el, len(its), v))
    B = [(T(ko, "Data", ""), lambda i: i["stage"] == "D"), (T(ko, "Model", ""), lambda i: i["stage"] == "M"),
         (T(ko, "Importance", ""), lambda i: i["stage"] == "I"), (T(ko, "Reporting", ""), lambda i: i["stage"] == "R"),
         (T(ko, "KNHANES-specific\n(cross-cutting)", ""), lambda i: i["note"] in ("RS", "NS")), (T(ko, "All items", ""), lambda i: True)]
    Bv = []
    for lab, f in B:
        v = [score(st, f) for st in S.values()]
        v = [x for x in v if x is not None]
        n_it = sum(f(i) for i in items)
        Bv.append((lab, n_it, v))
    pct = []
    for i in items:
        v = [S[s]["items"][str(i["idx"])] for s in S if str(i["idx"]) in S[s]["items"]]
        pct.append((100 * sum(v) / len(v), sum(v), len(v), i))
    C = sorted(pct, key=lambda x: x[0])[:12]

    W = 5.4
    hA, hB, hC = .26 * len(A) + .55, .26 * len(Bv) + .55, .2 * len(C) + .55
    H = hA + hB + hC + .25
    fig = plt.figure(figsize=(W, H))
    L, R_ = 2.05, .25
    def ax_at(y, h):
        return fig.add_axes([L / W, 1 - (y + h - .38) / H, (W - L - R_) / W, (h - .55) / H])
    def strip(ax, rows, col):
        for k, (lab, n_it, v, extra) in enumerate(rows):
            y = len(rows) - 1 - k
            ax.boxplot([v], positions=[y], vert=False, widths=.55, showfliers=False, whis=(0, 100),
                       medianprops=dict(color="black", lw=1.1), boxprops=dict(lw=.6, color=DGREY), whiskerprops=dict(lw=.6, color=DGREY), capprops=dict(lw=.6, color=DGREY))
            ax.scatter(v, y + rng.uniform(-.2, .2, len(v)), s=3, color=col, alpha=.45, lw=0, zorder=3)
            ax.text(-3, y, lab, ha="right", va="center", fontsize=fs - .4, transform=ax.transData, clip_on=False)
            ax.text(103, y, extra, ha="left", va="center", fontsize=fs - 1.2, color=DGREY, clip_on=False)
        ax.set_yticks([]); ax.set_xlim(0, 100); ax.set_ylim(-.6, len(rows) - .4)
        ax.set_xticks([0, 25, 50, 75, 100]); ax.tick_params(labelsize=fs - 1, length=2, pad=1)
        [ax.spines[s_].set_visible(False) for s_ in ("top", "right", "left")]; grid(ax, "x")
    def head(y, letter, en, kr):
        fig.text(0, 1 - y / H, f"{letter}  " + T(ko, en, kr), fontsize=fs + .6, weight="bold", va="top")
    y = 0
    head(y, "A", "Studies judged 'completely reported' on an element: % of its core items met",
         "")
    ax = ax_at(y, hA)
    strip(ax, [("\n".join(__import__("textwrap").wrap(f"{el}. " + T(ko, TRIPOD[el - 1][1], TRIPOD[el - 1][0]), 30 if not ko else 18)), n, v,
                f"n={len(v)}\n{n} " + T(ko, "items", "")) for el, n, v in A], BLUE)
    ax.set_xlabel(T(ko, "% of the element's core items met", ""), fontsize=fs - .8, labelpad=1)
    y += hA
    head(y, "B", "All 193 studies: % of applicable core items met, by reproduction stage",
         "")
    ax = ax_at(y, hB)
    strip(ax, [(lab, n, v, f"{n} " + T(ko, "items", "") + f"\n{T(ko, 'median', '')} {np.median(v):.0f}%") for lab, n, v in Bv], ORANGE)
    ax.axhline(1.5, color=DGREY, lw=.6, ls=":")  # rows below cut across the stages
    ax.set_xlabel(T(ko, "% of applicable core items met per study", ""), fontsize=fs - .8, labelpad=1)
    y += hB
    head(y, "C", "The least reported core items (% of studies to which the item applies)",
         "")
    ax = ax_at(y, hC)
    for k, (p, m, n, i) in enumerate(C):
        yy = len(C) - 1 - k
        ax.barh(yy, p, height=.65, color=RED if p < 10 else ORANGE, edgecolor="none")
        ax.text(max(p, 10) + .8, yy, f"{p:.1f}% ({m}/{n})", va="center", fontsize=fs - 1.2)
        ax.text(-1.5, yy, f"{i['id']} " + (i["item_ko"] if ko else i["item_en"]), ha="right", va="center", fontsize=fs - .6)
    ax.axvline(10, color=RED, lw=.6, ls="--", zorder=1)
    ax.set_yticks([]); ax.set_xlim(0, 40); ax.set_ylim(-.6, len(C) - .4); ax.set_xticks([0, 10, 20, 30, 40])
    ax.tick_params(labelsize=fs - 1, length=2, pad=1); [ax.spines[s_].set_visible(False) for s_ in ("top", "right", "left")]; grid(ax, "x")
    ax.set_xlabel(T(ko, "% of studies meeting the item (red, below 10%)", ""), fontsize=fs - .8, labelpad=1)
    save(fig, "fig23_checklist_v18", ko, tight=True)


def figure_checklist_v19(lang="en"):
    """v19 Figure 5 (author: the box plots were not intuitive). A: among studies judged 'completely
    reported' on a TRIPOD+AI-derived element, the % meeting each core item of that element (grey background = what the
    TRIPOD+AI judgement implies, 100%). B: the least reported core items in all 193 studies. Drawn at print size."""
    import checklist_v18 as CK
    from checklist_v12 import TRIPOD
    import textwrap
    from checklist_desc import DESC
    desc = lambda i: DESC[i["id"]][0 if ko else 1]
    style(lang); ko = lang == "ko"
    t = json.load(open(os.path.join(ROOT, "results/derived/checklist_v18_scores.json")))
    items, S = t["items"], t["studies"]
    ORANGE, RED, GREY = "#F28E2B", "#D62728", "#E6E9EE"
    fs = 6.8
    name = lambda i: (i["item_ko"] if ko else i["item_en"])
    def group(el):
        sub = [st for st in S.values() if st["tripod"][str(el)] == "Reported"]
        rows = []
        for i in items:
            if i["tripod"] != el:
                continue
            v = [st["items"][str(i["idx"])] for st in sub if str(i["idx"]) in st["items"]]
            if v:
                rows.append((i, sum(v), len(v)))
        return len(sub), sorted(rows, key=lambda x: x[0]["id"])
    cols = [[4, 6, 10], [11, 12, 14]]
    LH = .155
    W = 5.4
    def col_h(c):
        return sum(.34 + LH * len(group(el)[1]) for el in c)
    hA = max(col_h(c) for c in cols) + .62
    pct = []
    for i in items:
        v = [s["items"][str(i["idx"])] for s in S.values() if str(i["idx"]) in s["items"]]
        pct.append((100 * sum(v) / len(v), sum(v), len(v), i))
    C = sorted(pct, key=lambda x: x[0])[:10]
    hB = .28 * len(C) + .5
    H = hA + hB + .1
    fig = plt.figure(figsize=(W, H))
    fy = lambda y: 1 - y / H
    fig.text(0, fy(.02), T(ko, "A  Studies judged 'completely reported' by TRIPOD+AI: % meeting each core item (definitions in Table 1)",
                           ""), fontsize=fs + .7, weight="bold", va="top")
    fig.text(0, fy(.19), T(ko, "Grey bar = 100% implied by the 'completely reported' judgement; coloured bar = studies that actually reported the item (red, below 10%)",
                           ""), fontsize=fs - 1.0, color=DGREY, va="top")
    CW = W / 2
    LBL, BW = 1.32, .78   # label width, bar width (in)
    for ci, c in enumerate(cols):
        x0 = ci * CW
        y = .42
        for el in c:
            n, rows = group(el)
            head = f"{el}. " + T(ko, TRIPOD[el - 1][1], TRIPOD[el - 1][0])
            fig.text(x0 / W, fy(y), head + T(ko, f" (n={n})", f" ({n})"), fontsize=fs, weight="bold", va="top")
            y += .17
            for i, m, nn in rows:
                p = 100 * m / nn
                yc = y + LH / 2
                fig.text((x0 + LBL) / W, fy(yc), f"{i['id']} " + textwrap.shorten(name(i), 24 if not ko else 14, placeholder="…"),
                         fontsize=fs - .9, ha="right", va="center")
                ax = fig.add_axes([(x0 + LBL + .05) / W, fy(yc + LH * .38), BW / W, LH * .76 / H])
                ax.barh(0, 100, color=GREY, height=1); ax.barh(0, p, color=RED if p < 10 else ORANGE, height=1)
                ax.set_xlim(0, 100); ax.axis("off")
                fig.text((x0 + LBL + .05 + BW + .04) / W, fy(yc), f"{p:.0f}% ({m}/{nn})", fontsize=fs - 1.1, va="center")
                y += LH
            y += .17
    y0 = hA
    fig.text(0, fy(y0), T(ko, "B  The least reported core items in all 193 studies (% of studies to which the item applies)",
                          ""), fontsize=fs + .7, weight="bold", va="top")
    ax = fig.add_axes([2.45 / W, fy(y0 + hB - .32), (W - 2.45 - .55) / W, (hB - .55) / H])
    for k, (p, m, n, i) in enumerate(C):
        yy = len(C) - 1 - k
        ax.barh(yy, 100, height=.68, color=GREY, edgecolor="none")
        ax.barh(yy, p, height=.68, color=RED if p < 10 else ORANGE, edgecolor="none")
        ax.text(-1.5, yy + .17, f"{i['id']} " + name(i), ha="right", va="center", fontsize=fs - .5)
        ax.text(-1.5, yy - .22, desc(i), ha="right", va="center", fontsize=fs - 1.6, color=DGREY)
        ax.text(max(p, 0) + 1.5, yy, f"{p:.1f}% ({m}/{n})", va="center", fontsize=fs - 1)
    ax.set_xlim(0, 100); ax.set_ylim(-.6, len(C) - .4); ax.set_yticks([]); ax.set_xticks([0, 25, 50, 75, 100])
    ax.tick_params(labelsize=fs - 1, length=2, pad=1); [ax.spines[s_].set_visible(False) for s_ in ("top", "right", "left")]
    ax.set_xlabel(T(ko, "% of studies meeting the item", ""), fontsize=fs - .8, labelpad=1)
    save(fig, "fig25_checklist_v19", ko, tight=True)

def figure_checklist_all_v14(lang="en"):
    """v14 Figure 5, layout 4 (author): every item of the detailed checklist (an appendix table of an earlier draft, numbered as
    there) as a box per TRIPOD+AI-derived element: orange fill = % of applicable studies meeting the item; grey hatched =
    not coded in this review; red box and circled number = met by fewer than 10%. Left: 3-level TRIPOD+AI judgement."""
    import checklist_v13 as C13
    from checklist_v12 import TRIPOD
    style(lang); ko = lang == "ko"
    t = json.load(open(os.path.join(ROOT, "results/derived/checklist_v13_scores.json")))
    S = t["studies"]
    class _M:
        first = staticmethod(lambda d, k: None); has = staticmethod(lambda d, k, v: False); flat_values = staticmethod(lambda d, k: [])
    rows = C13.build(_M)
    keys = []
    for r in rows:
        if r[0] not in keys:
            keys.append(r[0])
    pct = {}
    for k, r in enumerate(rows):
        if r[7] is not None:
            v = [S[s]["items"][str(k)] for s in S if str(k) in S[s]["items"]]
            pct[k] = (100 * sum(v) / len(v), len(v), sum(v))
    circ = "①②③④⑤⑥⑦⑧⑨⑩⑪⑫⑬⑭⑮⑯⑰⑱⑲⑳"
    low = [k for k in range(len(rows)) if k in pct and pct[k][0] < 10]
    mark = {k: circ[n] for n, k in enumerate(low)}
    levels = [("Not reported", T(ko, "No", ""), "#C9CED6"), ("Partly reported", T(ko, "Part", ""), "#7FB8C9"), ("Reported", T(ko, "Full", ""), "#1F4E79")]
    ORANGE, OEDGE, RED = "#F28E2B", "#B85C00", "#D62728"
    RH, TOP = .46, .62
    LEG = .25 + .16 * len(low)
    H = TOP + len(keys) * RH + LEG + .1
    fig = plt.figure(figsize=(FIG_W, H))
    fy = lambda yin: 1 - yin / H
    XA, WA, XB, WB = 1.95, .95, 3.2, 4.05
    fs = FS_TICK - 2.6
    maxk = max(sum(1 for r in rows if r[0] == key) for key in keys)
    fig.text(XA / FIG_W, fy(.12), T(ko, "TRIPOD+AI\n(3 levels, %)", ""), fontsize=FS_TITLE - 2.8, weight="bold", va="top", color="#1F4E79", linespacing=1.05)
    fig.text(XB / FIG_W, fy(.12), T(ko, "All checklist items (numbers as in Appendix Table A2): % meeting each\nhatched, not coded; red, below 10%", ""),
             fontsize=FS_TITLE - 2.8, weight="bold", va="top", color=OEDGE, linespacing=1.05)
    def deco(a):
        [a.spines[s_].set_visible(False) for s_ in ("top", "right")]; a.tick_params(labelsize=fs - .5, length=2, pad=1)
    for rr, key in enumerate(keys):
        y0 = TOP + rr * RH
        if isinstance(key, int):
            lab = f"{key}. " + T(ko, TRIPOD[key - 1][1], TRIPOD[key - 1][0])
        else:
            lab = T(ko, "(New) ", "") + T(ko, *{"importance": ("", "Variable importance"), "after": ("", "Analyses after the ranking")}[key][::-1])
        fig.text(.05 / FIG_W, fy(y0 + RH * .42), "\n".join(__import__("textwrap").wrap(lab, 24 if not ko else 13)), fontsize=fs + .1, va="center", linespacing=1.0)
        aA = fig.add_axes([XA / FIG_W, fy(y0 + RH - .13), WA / FIG_W, (RH - .22) / H])
        aB = fig.add_axes([XB / FIG_W, fy(y0 + RH - .13), WB / FIG_W, (RH - .22) / H])
        if isinstance(key, int):
            cnt = [100 * sum(S[s]["tripod"][str(key)] == lev for s in S) / len(S) for lev, _, _ in levels]
            aA.bar(range(3), cnt, color=[c for _, _, c in levels], width=.7)
            aA.set_xticks(range(3)); aA.set_xticklabels([l for _, l, _ in levels], fontsize=fs - 1)
        else:
            aA.text(1, 50, T(ko, "No element", ""), ha="center", va="center", fontsize=fs - .4, color=DGREY); aA.set_xticks([])
        aA.set_xlim(-.6, 2.6); aA.set_ylim(0, 100); aA.set_yticks([0, 100]); deco(aA)
        idx = [k for k, r in enumerate(rows) if r[0] == key]
        for x, k in enumerate(idx):
            if k in pct:
                isl = k in mark
                aB.add_patch(matplotlib.patches.Rectangle((x - .36, 0), .72, 100, fill=False, edgecolor=RED if isl else "#C4C9D0", lw=1.4 if isl else .5, zorder=4 if isl else 2))
                aB.bar(x, pct[k][0], color=ORANGE, width=.72, edgecolor=OEDGE, linewidth=.4, zorder=3)
                if isl:
                    aB.text(x, 104, mark[k], ha="center", va="bottom", fontsize=fs + .6, color=RED, weight="bold")
            else:
                aB.add_patch(matplotlib.patches.Rectangle((x - .36, 0), .72, 100, facecolor="#F3F4F6", edgecolor="#C4C9D0", hatch="////", lw=.5, zorder=2))
            aB.text(x, -12, str(k + 1), ha="center", va="top", fontsize=fs - 1.2)
        aB.set_xticks([]); aB.set_xlim(-.6, maxk - .4); aB.set_ylim(0, 100); aB.set_yticks([0, 100]); deco(aB)
    yl = TOP + len(keys) * RH + .2
    fig.text(.05 / FIG_W, fy(yl), T(ko, "Items met by fewer than 10% of studies (the least reported information):", ""), fontsize=fs + .3, weight="bold", color=RED, va="top")
    for n, k in enumerate(low):
        v, den, met = pct[k]
        r = rows[k]
        nm = (r[3] if ko else r[4]) or (r[1] if ko else r[2])
        fig.text(.2 / FIG_W + ((n % 2) * .5 if ko else 0), fy(yl + .2 + .16 * ((n // 2) if ko else n)), f"{circ[n]} {k + 1}. {nm.replace('$^{\\dagger}$', '')} — {v:.1f}% ({met}/{den})", fontsize=fs - .2, va="top")
    save(fig, "fig17_checklist_all", ko, tight=True)


def top_band(fig, fx, fy, ko, o, FT, FL):
    """Author: earlier-draft Figure 4 top band. A studies per year (all ML studies, core studies with an importance ranking,
    SHAP); B importance methods of the ranking studies; C analyses after the ranking."""
    import claim_evidence_analysis as _ce, make_streamlined_figures as _ms
    R = [d for d in _ce.CORE if _ms.has(d, "VI01", {"USED"})]
    shap_ids = {d["study_id"] for d in R if _ms.has(d, "VI02", {"SHAP"})}
    rank_ids = {d["study_id"] for d in R}
    pts = o["literature_map"]
    years = list(range(min(q["year"] for q in pts), 2027))
    def per_year(sel):
        return [sum(q["year"] == y and sel(q) for q in pts) for y in years]
    allv, rkv, shv = per_year(lambda q: True), per_year(lambda q: q["id"] in rank_ids), per_year(lambda q: q["id"] in shap_ids)
    assert sum(rkv) == len(R) and sum(shv) == len(shap_ids)
    top, h = .42, 1.25
    axA = fig.add_axes([fx(.42), fy(top + h), fx(2.05), h / fig.get_figheight()])
    for v, col, lab in ((allv, "#C9D3E0", T(ko, f"All ML studies ({sum(allv)})", f" ML  ({sum(allv)})")),
                        (rkv, "#5B7FA6", T(ko, f"Importance ranking ({sum(rkv)})", f"  ({sum(rkv)})")),
                        (shv, NAVY, T(ko, f"SHAP ({sum(shv)})", f"SHAP ({sum(shv)})"))):
        axA.bar(years, v, color=col, width=.75, label=lab)
    axA.set_xticks([2010, 2015, 2020, 2025]); axA.tick_params(labelsize=FL); axA.set_ylim(0, 50); axA.set_yticks([0, 20, 40])
    axA.set_ylabel(T(ko, "Studies", ""), fontsize=FL, labelpad=1); grid(axA, "y")
    [axA.spines[k].set_visible(False) for k in ("top", "right")]
    axA.legend(frameon=False, loc="upper left", fontsize=FL - .6, handlelength=1.0, labelspacing=.25, borderaxespad=.1)
    axA.set_ylim(0, max(50, allv[-1] + 26))  # room for the legend above the tall recent bars
    axA.text(2026.4, allv[-1] + .8, T(ko, "to Oct", ""), ha="right", va="bottom", fontsize=FL - 1.6, color=DGREY)  # above the last bar, horizontal (a rotated label ran into the legend)
    fig.text(fx(.06), fy(.04), T(ko, "A. Studies per year", ""), fontsize=FT, weight="bold", va="top")
    # B. Importance methods (overlap) among the ranking studies.
    named = [("SHAP", "SHAP", "SHAP"), ("MODEL_NATIVE", "Model-native", ""), ("TREE_RULE", "Tree or rule", ""),
             ("PERMUTATION", "Permutation", ""), ("COEFFICIENT_STATISTIC", "Coefficient", ""), ("LIME", "LIME", "LIME")]
    rows = [(T(ko, en, kr), sum(_ms.has(d, "VI02", {k}) for d in R)) for k, en, kr in named]
    rows.append((T(ko, "Other", ""), sum(bool(set(_ms.flat_values(d, "VI02")) & {"PDP", "ALE", "ICE", "NETWORK_SPECIFIC", "PERTURBATION_ABLATION", "OTHER"}) for d in R)))
    def hbars(ax, rows, n):
        for i, (lab, v) in enumerate(rows):
            ax.barh(i, n, color="white", edgecolor="#D1D5DB", linewidth=.5, height=.6, zorder=1)
            ax.barh(i, v, color=NAVY, height=.6, zorder=2)
            ax.text(v + 2, i, f"{v}", va="center", fontsize=FL)
        ax.set_yticks(range(len(rows))); ax.set_yticklabels([r[0] for r in rows], fontsize=FL); ax.tick_params(axis="y", length=0, pad=2)
        ax.set_ylim(len(rows) - .5, -.5); ax.set_xlim(0, n * 1.18); ax.set_xticks([0, n // 2, n]); ax.tick_params(axis="x", labelsize=FL)
        [ax.spines[k].set_visible(False) for k in ("left", "top", "right")]; grid(ax)
        ax.set_xlabel(T(ko, "Ranking studies", ""), fontsize=FL, labelpad=1)
    axB = fig.add_axes([fx(3.55), fy(top + h), fx(1.25), h / fig.get_figheight()])
    hbars(axB, rows, len(R))
    fig.text(fx(2.62), fy(.04), T(ko, f"B. Importance methods\n(N={len(R)}; overlap)", f"B.  \n(N={len(R)}, )"), fontsize=FT, weight="bold", va="top")
    # C. Analyses after the ranking (overlap); none = none of these.
    keys = [("VI16", "Stability check", ""), ("VI10", "Reduced model", ""),
            ("VI11", "Statistical model", ""), ("VI17", "Explanation fidelity", "")]
    rows = [(T(ko, en, kr), sum(_ms.has(d, k, {"USED"}) for d in R)) for k, en, kr in keys]
    rows.append((T(ko, "None of these", ""), sum(not any(_ms.has(d, k, {"USED"}) for k, _, _ in keys) for d in R)))
    axC = fig.add_axes([fx(6.05), fy(top + h), fx(1.25), h / fig.get_figheight()])
    hbars(axC, rows, len(R))
    fig.text(fx(5.05), fy(.04), T(ko, f"C. Analyses after the ranking\n(N={len(R)}; overlap)", f"C.   \n(N={len(R)}, )"), fontsize=FT, weight="bold", va="top")


def figure_named(lang="en"):
    """Prompt 112 (review v49): what the rankings named (N=154). A hierarchical heatmap (rows: all, then the earlier-draft Figure 3A
    topics, split into outcome groups where a topic has two or more with at least five ranking studies; a defined tree on
    the left); B the diabetes or prediabetes row of A, study by study, on the same columns. Laid out in inches."""
    style(lang); ko = lang == "ko"; o = data(); r = o["rankings_named_112"]
    vps = r["variables_per_study"]
    cols = fig5_columns(r); nc = len(cols)
    fam_of = [r["family"][c[1][0]] for c in cols]
    FT, FL, FN = FS_TITLE - 1.6, FS_TICK - 1.2, FS_VALUE - 3.0
    rows = [{"level": "all", "topic": "ALL", "group": "all", "ids": sorted(vps), "n": r["all"]["n"]}] + r["rows"]
    dia = next(x_ for x_ in r["rows"] if x_["group"] == "diabetes")
    studies = sorted(o["diabetes_variable_panel_112"]["studies"], key=lambda st: (st["n_named"], st["year"], st["id"]))
    assert len(studies) == dia["n"]

    def rowlab(row):
        if row["level"] == "all":
            return T(ko, f"All ranking studies ({row['n']})", f"   ({row['n']})"), "bold", 0
        if row["level"] == "topic":
            return T(ko, *FIG5_TOPIC[row["topic"]]) + f" ({row['n']})", "bold", 1
        return T(ko, *OUTCOME_NAMES[row["group"]]) + f" ({row['n']})", "normal", 2
    collab = [T(ko, "Other", "") if k.startswith("OTHER:") else T(ko, *VAR_NAMES[k]) for k, _ in cols]
    # measure text in inches on a scratch figure
    scratch = plt.figure(figsize=(FIG_W, 4)); rend = scratch.canvas.get_renderer()

    def ext(text, size, weight="normal", rot=0):
        t = scratch.text(0, 0, text, fontsize=size, weight=weight, rotation=rot)
        bb = t.get_window_extent(rend); t.remove()
        return bb.width / scratch.dpi, bb.height / scratch.dpi
    INDENT = (0, .10, .22)  # tree depth -> label x (in)
    lab_w = max(INDENT[d] + ext(l, FL, w)[0] for l, w, d in map(rowlab, rows))
    lab_w = max(lab_w, max(ext(f"{st['label']} ({st['n_named']})", FL)[0] for st in studies))
    col_h = max(ext(c, FL, rot=90)[1] for c in collab)
    plt.close(scratch)
    LEFT_IN, RIGHT_IN, GAPF = .06 + lab_w + .08, .05, .35  # GAPF: gap between families (in units of a cell)
    xs, x, prev = [], 0.0, None
    for f in fam_of:
        if prev is not None and f != prev:
            x += GAPF
        xs.append(x); x += 1; prev = f
    XMAX = x
    cw = (FIG_W - LEFT_IN - RIGHT_IN) / XMAX  # cell width (in)
    PITCH = .14  # prompt 112; the top band makes the figure taller, so it prints slightly smaller
    ys, y = [], 0.0
    for k, row in enumerate(rows):
        ys.append(y); y += 1 + (.6 if k == 0 else 0)
    TITLE, KEY, FAM = .30, .0, .36
    fam_lines = {}
    for f in r["families"]:
        span = sum(1 for g in fam_of if g == f) * cw
        name = T(ko, *FAMILY_NAMES[f])
        fam_lines[f] = name if ext(name, FL, "bold")[0] < span - .04 else name.replace(" and ", " and\n").replace("·", "·\n", 1)
    FAM = .26 + (.16 if any("\n" in v for v in fam_lines.values()) else 0)
    Y0 = 2.2  # author: top band (A trends, B importance methods, C analyses after the ranking)
    topA = Y0 + .04 + TITLE + FAM + col_h + .06
    hA = (ys[-1] + 1) * PITCH; hB = len(studies) * PITCH
    topB = topA + hA + .30
    H = topB + .40 + hB + .08
    fig = plt.figure(figsize=(FIG_W, H))
    fx = lambda xin: xin / FIG_W; fy = lambda yin: 1 - yin / H
    axA = fig.add_axes([fx(LEFT_IN), fy(topA + hA), fx(cw * XMAX), hA / H])
    axB = fig.add_axes([fx(LEFT_IN), fy(topB + .40 + hB), fx(cw * XMAX), hB / H])
    cmap = matplotlib.colors.LinearSegmentedColormap.from_list("nv", ["#FFFFFF", NAVY])
    top_band(fig, fx, fy, ko, o, FT, FL)

    def share(ids, labs):
        return sum(bool(set(vps[i]) & set(labs)) for i in ids)
    for k, row in enumerate(rows):
        for j, (key, labs) in enumerate(cols):
            n = share(row["ids"], labs); p = n / row["n"]
            axA.add_patch(matplotlib.patches.Rectangle((xs[j], ys[k]), 1, 1, facecolor=cmap(p), edgecolor="white", linewidth=.6))
            outlined = (row["group"], key) in FIG5_OUTLINE
            if p >= .5 or outlined:
                axA.text(xs[j] + .5, ys[k] + .53, f"{100 * p:.0f}", ha="center", va="center", fontsize=FN - (.7 if p >= .995 else 0),
                         color="white" if p > .55 else "#111827")
            if outlined:
                axA.add_patch(matplotlib.patches.Rectangle((xs[j] + .04, ys[k] + .05), .92, .9, fill=False, edgecolor=TEAL, lw=1.5, zorder=4))
    axA.set_xlim(0, XMAX); axA.set_ylim(ys[-1] + 1, 0); axA.axis("off")
    for j, lab in enumerate(collab):
        fig.text(fx(LEFT_IN + (xs[j] + .5) * cw), fy(topA - .05), lab, rotation=90, ha="center", va="bottom", fontsize=FL)
    for f in r["families"]:
        js = [j for j in range(nc) if fam_of[j] == f]
        x0, x1 = LEFT_IN + xs[js[0]] * cw, LEFT_IN + (xs[js[-1]] + 1) * cw
        yb = topA - .05 - col_h - .09
        fig.add_artist(Line2D([fx(x0 + .02), fx(x1 - .02)], [fy(yb), fy(yb)], color=DGREY, lw=.8))
        fig.text(fx((x0 + x1) / 2), fy(yb - .035), fam_lines[f], ha="center", va="bottom", fontsize=FL, weight="bold", linespacing=.95)
    # row labels and the defined tree: root (All) -> topics -> outcome groups
    yc = lambda yy: fy(topA + (yy + .5) * PITCH)
    X0 = .06
    line = lambda xa, ya, xb, yb: fig.add_artist(Line2D([fx(xa), fx(xb)], [ya, yb], color=DGREY, lw=.7))
    tops = [k for k, row in enumerate(rows) if row["level"] == "topic"]
    line(X0 + .02, yc(ys[0]) - .5 * PITCH / H, X0 + .02, yc(ys[tops[-1]]))
    for k in tops:
        line(X0 + .02, yc(ys[k]), X0 + INDENT[1] - .02, yc(ys[k]))
        kids = []
        for q in range(k + 1, len(rows)):
            if rows[q]["level"] != "outcome":
                break
            kids.append(q)
        if kids:
            line(X0 + INDENT[1] + .02, yc(ys[k]) - .45 * PITCH / H, X0 + INDENT[1] + .02, yc(ys[kids[-1]]))
            for q in kids:
                line(X0 + INDENT[1] + .02, yc(ys[q]), X0 + INDENT[2] - .02, yc(ys[q]))
    GREEN = "#2E9E5B"  # author: the diabetes row of A is the example shown in B
    for k, row in enumerate(rows):
        lab, wt, d = rowlab(row)
        dia_row = row["group"] == "diabetes"
        fig.text(fx(X0 + INDENT[d]), yc(ys[k]), lab, ha="left", va="center", fontsize=FL, weight=wt,
                 color=GREEN if dia_row else None)
        if dia_row:
            axA.add_patch(matplotlib.patches.Rectangle((0, ys[k]), XMAX, 1, fill=False, edgecolor=GREEN, lw=1.6, zorder=5))
            dia_y = ys[k] + 1  # bottom edge of the diabetes row of D, linked to the E box below (author)
    # Axis guides (author): rows are what the studies analysed, columns the variables they named; a
    # triangle points along each axis.
    def guide(yin, marker, text):
        fig.add_artist(Line2D([fx(X0 + .05)], [fy(yin)], marker=marker, markersize=6.5, color=TEAL, linestyle="none"))
        fig.text(fx(X0 + .13), fy(yin), text, ha="left", va="center", fontsize=FL, weight="bold", color=TEAL, linespacing=1.0)
    guide(topA - .05 - .62 * col_h, ">", T(ko, "Columns: variables named\nas most important", ""))
    guide(topA - .05 - .18 * col_h, "v", T(ko, "Rows: study topic\nand outcome", ""))
    # colour key, top right of the title line
    axK = fig.add_axes([fx(FIG_W - 1.15), fy(Y0 + .04 + .12), fx(1.05), .07 / H])  # right end of the panel A title line
    axK.imshow(np.linspace(0, 1, 101)[None, :], cmap=cmap, aspect="auto", extent=(0, 100, 0, 1))
    axK.set_yticks([]); axK.set_xticks([0, 50, 100]); axK.set_xticklabels(["0", "50", "100%"], fontsize=FL - .8)
    axK.tick_params(length=2, pad=1); [sp.set_linewidth(.4) for sp in axK.spines.values()]
    fig.text(fx(FIG_W - 1.22), fy(Y0 + .04 + .085), T(ko, "Studies in the row", ""), fontsize=FL - .8, ha="right", va="center", color=DGREY)
    fig.text(fx(.06), fy(Y0 + .04), T(ko, f"D. Most important variables by outcome (N={r['all']['n']}; %)",
                                 f"D.      (N={r['all']['n']}, %)"), fontsize=FT, weight="bold", va="top")
    # B. the diabetes or prediabetes studies on the same columns
    for k, st in enumerate(studies):
        for j, (key, labs) in enumerate(cols):
            if set(st["variables"]) & set(labs):
                axB.scatter(xs[j] + .5, k + .5, s=24, color=GREEN, zorder=3, edgecolor="white", linewidth=.4)
    for j in range(nc):
        axB.plot([xs[j] + .5] * 2, [0, len(studies)], color="#E5E7EB", lw=.5, zorder=1)
    for k in range(len(studies)):
        axB.plot([xs[0], XMAX], [k + .5] * 2, color="#F1F3F6", lw=.5, zorder=1)
    axB.set_xlim(0, XMAX); axB.set_ylim(len(studies), 0); axB.axis("off")
    for k, st in enumerate(studies):
        fig.text(fx(X0), fy(topB + .40 + (k + .5) * PITCH), f"{st['label']} ({st['n_named']})", ha="left", va="center", fontsize=FL)
    fig.text(fx(.06), fy(topB), T(ko, f"E. Important variables for one disease: diabetes or prediabetes (N={dia['n']} of the {r['all']['n']})",
                                  f"E.  (·)   (N={r['all']['n']}  {dia['n']})"), fontsize=FT, weight="bold", va="top")
    # E is the subset of the diabetes row of D (author): a green box around E, joined to that row of D.
    bx0, bx1, by0, by1 = .03, FIG_W - .03, topB - .10, topB + .40 + hB + .05
    fig.add_artist(matplotlib.patches.Rectangle((fx(bx0), fy(by1)), fx(bx1) - fx(bx0), fy(by0) - fy(by1), transform=fig.transFigure,
                                                fill=False, edgecolor=GREEN, lw=1.6, zorder=6))
    # author: one short bracket (a reversed C) outside the heatmap, from the right end of the diabetes row of D
    # to the right side of the E box, so the link does not run over the table
    xr, yr = fig.transFigure.inverted().transform(axA.transData.transform((XMAX, dia_y - .5)))
    xg, yb_ = fx(bx1 + .09), fy(by0 + .22)
    fig.add_artist(Line2D([xr, xg, xg, fx(bx1)], [yr, yr, yb_, yb_], transform=fig.transFigure, color=GREEN, lw=1.2,
                          linestyle=(0, (4, 2.5)), zorder=6, solid_joinstyle="miter"))
    fig.add_artist(Line2D([fx(X0 + .05)], [fy(topB + .30)], marker="v", markersize=6.5, color=TEAL, linestyle="none"))
    fig.text(fx(X0 + .13), fy(topB + .30), T(ko, "Rows: studies (first author and year; variables named); columns as in D",
                                             ""),
             fontsize=FL, weight="bold", color=TEAL, va="center")
    save(fig, "fig5_rankings_named", ko, tight=True)


# --------------------------------------------------------------------------- supplementary helpers (S3, S7)
def figure_agreement(lang="en", out=None):
    """a supplementary figure of an earlier draft: A overlap of the named domains between pairs of ranking studies; B the domain columns
    of the oral-health and respiratory studies (fewer than ten ranking studies each; moved from earlier-draft Figure 3B)."""
    style(lang); ko = lang == "ko"; o = data()
    fig = plt.figure(figsize=(FIG_W, 9.6))  # prompt 112: B is the data-only tree
    axC = fig.add_axes([.30, .77, .62, .16])
    axH = fig.add_axes([.42, .03, .56, .50])  # prompt 112: data-only tree heatmap
    g = o["domain_agreement_098"]
    kinds = [("same_outcome", T(ko, "Same outcome", "")), ("same_topic_other_outcome", T(ko, "Same topic,\nother outcome", "")),
             ("different_topic", T(ko, "Different topics", ""))]
    for i, (k, lab) in enumerate(kinds):
        for gi, (grp, face, off) in enumerate((("all_domains", NAVY, -.14), ("without_age_sex_body_size", "white", .14))):
            v = g[grp][k]
            axC.plot([v["q1"], v["q3"]], [i + off, i + off], color=NAVY if gi == 0 else SLATE, lw=2.2, alpha=.5, solid_capstyle="butt")
            axC.scatter([v["median"]], [i + off], s=46, facecolor=face, edgecolor=NAVY if gi == 0 else SLATE, linewidth=1.2, zorder=3)
            axC.text(v["q3"] + .015, i + off, f"{v['median']:.2f}", va="center", fontsize=FS_VALUE - 2.2)
    axC.set_yticks(range(3)); axC.set_yticklabels([f"{lab} ({g['all_domains'][k]['pairs']:,})" for k, lab in kinds], fontsize=FS_TICK - 2.4, linespacing=1.0)
    axC.set_ylim(2.5, -.5); axC.set_xlim(0, .7); axC.set_xticks([0, .2, .4, .6])
    axC.set_xlabel(T(ko, "Overlap of named domains between two studies (Jaccard index; pairs)", ""), fontsize=FS_TICK - 1.4)
    grid(axC)
    axC.legend(handles=[Line2D([], [], marker="o", ls="", color=NAVY, ms=6, label=T(ko, "All domains", "")),
                        Line2D([], [], marker="o", ls="", markerfacecolor="white", markeredgecolor=SLATE, ms=6,
                               label=T(ko, "Without age, sex and body size", ""))],
               frameon=False, loc="lower right", bbox_to_anchor=(1.0, 1.0), ncol=2, fontsize=FS_VALUE - 2.2, handletextpad=.2)
    title(fig, axC, T(ko, f"A. Overlap of named variable domains between pairs of studies (N={NS()['rank']})", f"A.        ({NS()['rank']})"), dy=.05)
    # B (prompt 112): rows of earlier-draft Figure 5A clustered by their variable profiles alone (no topic tree).
    from scipy.cluster.hierarchy import dendrogram
    r = o["rankings_named_112"]; vps = r["variables_per_study"]; cols = fig5_columns(r)
    tree = r["data_tree"]; leaf = [r["rows"][k] for k in tree["rows"]]
    dn = dendrogram(np.array(tree["linkage"]), orientation="left", no_plot=True)
    order = dn["leaves"]
    assert order == tree["order"] or sorted(order) == sorted(tree["order"])
    axT = fig.add_axes([.01, .03, .085, .50])
    dendrogram(np.array(tree["linkage"]), orientation="left", ax=axT, link_color_func=lambda k: DGREY, no_labels=True)
    axT.axis("off"); axT.set_ylim(10 * len(order), 0)  # leaves at 5, 15, ... pinned to the heatmap rows
    cmap = matplotlib.colors.LinearSegmentedColormap.from_list("nv", ["#FFFFFF", NAVY])
    nL = len(order)
    for rr, li in enumerate(order):
        row = leaf[li]
        for j_, (key, labs) in enumerate(cols):
            p = sum(bool(set(vps[i_]) & set(labs)) for i_ in row["ids"]) / row["n"]
            axH.add_patch(matplotlib.patches.Rectangle((j_, rr), 1, 1, facecolor=cmap(p), edgecolor="white", linewidth=.5))
    axH.set_xlim(0, len(cols)); axH.set_ylim(nL, 0)
    axH.set_xticks([j_ + .5 for j_ in range(len(cols))])
    axH.set_xticklabels([T(ko, "Other", "") if k.startswith("OTHER:") else T(ko, *VAR_NAMES[k]) for k, _ in cols], rotation=90, fontsize=FS_TICK - 3.6)
    axH.xaxis.tick_top()
    def lab(row):
        if row["level"] == "topic":
            return T(ko, *FIG5_TOPIC[row["topic"]])
        return T(ko, *FIG5_TOPIC[row["topic"]]) + ": " + T(ko, *OUTCOME_NAMES[row["group"]]).lower().replace("other outcomes", "other") if not ko else \
            T(ko, *FIG5_TOPIC[row["topic"]]) + ": " + T(ko, *OUTCOME_NAMES[row["group"]])
    axH.set_yticks([rr + .5 for rr in range(nL)]); axH.set_yticklabels([f"{lab(leaf[li])} ({leaf[li]['n']})" for li in order], fontsize=FS_TICK - 3.2)
    axH.tick_params(length=0); [sp.set_visible(False) for sp in axH.spines.values()]
    fig_named = remap("Figure 5D").split()[1]  # main-figure number in the journal version (JCE: 4D; the heatmap is panel D)
    title(fig, axH, T(ko, f"B. Rows of Figure {fig_named} clustered by their variable profiles alone (N={NS()['rank']}; %)",
                      f"B.     {fig_named}  (N={NS()['rank']}, %)"), x=.012, dy=.135)
    save(fig, "figS_ranking_agreement", ko, out)


def figure_topic_slopes(ax, o, ko=False):
    """a supplementary figure of an earlier draft (earlier-draft Figure 3B): ranking share in the first and last period within the four
    largest topics."""
    rt = o["ranking_by_topic_period"]
    right = []
    for k in DOMAIN_TOPICS:
        a = pct(rt[k]["ranking"][0], rt[k]["n"][0]); b = pct(rt[k]["ranking"][-1], rt[k]["n"][-1])
        _pin(b > a, True, f"make_main_figures.py:455 rose {k}")  # prompt 106 pin
        ax.plot([0, 1], [a, b], color=NAVY, lw=1.6, zorder=2)
        ax.scatter([0, 1], [a, b], s=30, color=NAVY, zorder=3, edgecolor="white", linewidth=.5)
        # Prompt 103 (review v41): one label per line, at its right end, naming the topic and both counts.
        right.append([b, f"{T(ko, *TOPIC_NAMES[k]).split(' and ')[0]} {rt[k]['ranking'][0]}/{rt[k]['n'][0]} → {rt[k]['ranking'][-1]}/{rt[k]['n'][-1]}", a])
    right.sort(key=lambda r: -r[0])
    for i in range(1, len(right)):  # prompt 100: three topics end at 100%, so stack the end labels
        right[i][0] = min(right[i][0], right[i - 1][0] - 8)
    for yv, lab, _ in right:
        ax.text(1.08, yv, lab, ha="left", va="center", fontsize=FS_VALUE - 2.6, clip_on=False)
    ax.set_xticks([0, 1]); ax.set_xticklabels([SHORT_TICKS[0], SHORT_TICKS[-1]]); ax.set_xlim(-.15, 1.2)  # prompt 102: short period format
    ax.set_ylim(0, 108); ax.set_yticks([0, 50, 100]); ax.set_yticklabels(["0", "50", "100%"]); grid(ax, "y")
    [ax.spines[k].set_visible(False) for k in ("top", "right")]


# --------------------------------------------------------------------------- earlier-draft Figure 4
def figure4(lang="en"):
    """Prompt 109 (review v46): practices that make results reusable, three equal panels on one y axis (N=192):
    A analysis code shared, B calibration reported, C validation beyond the development data. Ranking stability is in
    earlier-draft Figure 6A; the 2025 and 2026 values are in the caption and the Table 1 footnote."""
    style(lang); ko = lang == "ko"; o = data()
    den = o["period_n"]; p = o["practices"]
    Nc = NS()["core"]
    cells = [(T(ko, f"A. Analysis code shared\n(N={Nc})", f"A.   \n(N={Nc})"), p["code_link"]),
             (T(ko, f"B. Calibration reported\n(N={Nc})", f"B.  \n(N={Nc})"), p["calibration"]),
             (T(ko, f"C. Validation beyond the\ndevelopment data (N={Nc})", f"C.   \n(N={Nc})"), p["validation_beyond_development"])]
    fig = plt.figure(figsize=(FIG_W, 3.2))
    x = np.arange(4)
    for k, (ttl, num) in enumerate(cells):
        c0 = .005 + k / 3  # three equal cells; the y-axis labels stay inside each cell
        ax = fig.add_axes([c0 + .065, .2, 1 / 3 - .09, .58])
        v = [pct(a_, b_) for a_, b_ in zip(num, den)]
        ax.plot(x, v, color=TEAL, lw=1.4, zorder=2)
        ax.scatter(x, v, s=30, color=TEAL, zorder=3, edgecolor="white", linewidth=.5)  # prompt 112: one dot size
        for i_ in range(4):  # prompt 111: n/N at every period point; prompt 112: below the point when a neighbour is higher
            nb = [v[q] for q in (i_ - 1, i_ + 1) if 0 <= q < 4]
            below = max(nb) > v[i_] + 2 and v[i_] > 9
            ax.text(i_ + (.0 if not below else 0), v[i_] + (-3.2 if below else 3.2), f"{num[i_]}/{den[i_]}", ha="center", va="top" if below else "bottom",
                    fontsize=FS_TICK - 2.6, color="#111827", bbox=dict(boxstyle="square,pad=.05", fc="white", ec="none"), zorder=4)
        ax.set_xticks(x); ax.set_xticklabels([f"{t}\n(n={n})" for t, n in zip(SHORT_TICKS, den)], fontsize=FS_TICK - 2.9, linespacing=1.0)
        ax.set_xlim(-.45, 3.45); ax.set_ylim(0, 45); ax.set_yticks([0, 20, 40]); ax.set_yticklabels(["0", "20", "40%"], fontsize=FS_TICK - 2.9)  # prompt 112: one tick size
        [ax.spines[q].set_visible(False) for q in ("top", "right")]; grid(ax, "y")
        fig.text(c0, .8 + .03, ttl, ha="left", va="bottom", fontsize=FS_TITLE - 1.6, weight="bold", linespacing=1.0)
    save(fig, "fig6_maturing_practice", ko, tight=True)  # prompt 109: three panels; prompt 112: earlier-draft Figure 5 -> 6


def figure_flat_practices(ax, o):
    """a supplementary figure of an earlier draft (earlier-draft Figure 5B): reporting practices with no consistent change."""
    den = o["period_n"]; lc = o["little_changed"]; x = np.arange(4)
    rows = [("Tuning kept apart", lc["tuning_kept_apart"]), ("Predictor set rebuildable", lc["predictor_set_rebuildable"]),
            ("Final model fully specified", lc["final_model_fully_specified"])]
    for (lab, num), col in zip(rows, (NAVY, SLATE, "#9CA3AF")):
        v = [pct(a, b) for a, b in zip(num, den)]
        ax.plot(x, v, color=col, lw=1.4, marker="o", ms=4, label=f"{lab} ({num[0]}/{den[0]} \u2192 {num[-1]}/{den[-1]})")
    ax.set_xticks(x); ax.set_xticklabels(SHORT_TICKS); ax.set_xlim(-.25, 3.25); ax.set_ylim(0, 100)
    ax.set_yticks([0, 50, 100]); ax.set_yticklabels(["0", "50", "100%"]); grid(ax, "y")


# --------------------------------------------------------------------------- earlier-draft Figure 5
def figure5(lang="en"):
    """Prompt 100 (review v38): next steps (earlier-draft Figure 6). A how ranking stability was checked (survey cycles 0);
    B survey design by workflow step; C preprocessing timing among the studies applying each step with a summary row."""
    style(lang); ko = lang == "ko"; o = data()
    # Prompt 108 (author request): one grid laid out in inches. Every axis shares the left edge (label column), the
    # width and, for A0, B and C, the 0-192 scale; bar rows share one pitch; each panel is title -> legend -> plot with
    # the same gaps; n/a notes sit in one right margin.
    PITCH, TT, LG, GAP = .22, .32, .22, .62  # one row pitch for every bar panel; GAP clears the x label above; fits the text width
    # Prompt 109 (review v46): stability appears once, as A (by period, the former 5B line) and B (approach of the 25), side
    # by side in two equal halves; C survey design and D preprocessing keep the shared full-width grid.
    t = .02
    tA = t; t += TT + .30; topA = t; t += 6 * PITCH; t += .80
    tB = t; t += TT + LG; topB = t; t += 5 * PITCH + GAP
    tC = t; t += TT + 1.75 * LG; topC = t; t += 5 * PITCH + .45
    H6 = t
    fig = plt.figure(figsize=(FIG_W, H6))
    X0, W6 = .30, .56
    hA = 6 * PITCH / H6
    axA0 = fig.add_axes([.075, 1 - topA / H6 - hA, .38, hA])  # A: stability by period
    axA = fig.add_axes([X0 + .36, 1 - topA / H6 - hA, X0 + W6 - (X0 + .36), hA])  # B: approach of the 25
    axB = fig.add_axes([X0, 1 - (topB + 5 * PITCH) / H6, W6, 5 * PITCH / H6])
    axC = fig.add_axes([X0, 1 - (topC + 5 * PITCH) / H6, W6, 5 * PITCH / H6])

    def ftitle(top, text, x=.012):
        fig.text(x, 1 - top / H6, text, ha="left", va="top", fontsize=FS_TITLE, weight="bold", linespacing=1.0)

    def flegend(top, handles, ncol):
        fig.legend(handles=handles, loc="upper left", bbox_to_anchor=(.012, 1 - (top + TT - .04) / H6), frameon=False, ncol=ncol,
                   fontsize=FS_VALUE - 1.6, handlelength=1.0, columnspacing=1.2, borderaxespad=0, borderpad=0)
    sm = o["stability_methods"]
    mrow = [(T(ko, "Subgroups", ""), sm["SUBGROUP_CONSISTENCY"], TEAL), (T(ko, "Resampling", ""), sm["RESAMPLING_STABILITY"], TEAL),
            (T(ko, "External data", ""), sm["EXTERNAL_DATA_REPLICATION"], TEAL), (T(ko, "Intervals", ""), sm["UNCERTAINTY_INTERVAL"], TEAL),
            (T(ko, "Sensitivity analyses", ""), sm.get("SENSITIVITY_ANALYSIS", 0), TEAL),  # D20 A
            (T(ko, "Across survey cycles", ""), o["stability_by_survey_cycle"], TEAL)]
    # Prompt 107 (review v44): the 14 checks without a described approach are drawn (hatched), so all 25 are visible.
    nd = sm["n"] - sm["method_identified"]
    s192 = o["stability_192"]; Nc = NS()["core"]
    assert s192["checked"] == sm["n"] and sum(s192.values()) == Nc
    den = o["period_n"]; stab = o["stability_among_ranking"]
    assert sum(stab) == sm["n"]
    x = np.arange(4); v = [pct(a_, b_) for a_, b_ in zip(stab, den)]
    axA0.plot(x, v, color=TEAL, lw=1.4, zorder=2)
    axA0.scatter(x, v, s=30, color=TEAL, zorder=3, edgecolor="white", linewidth=.5)  # prompt 112: one dot size
    for i_ in range(4):  # prompt 111: n/N at every period point; same axis as earlier-draft Figure 6
        axA0.text(i_, v[i_] + 3.2, f"{stab[i_]}/{den[i_]}", ha="center", va="bottom", fontsize=FS_TICK, color="#111827",
                  bbox=dict(boxstyle="square,pad=.05", fc="white", ec="none"), zorder=4)
    axA0.set_xticks(x); axA0.set_xticklabels([f"{t_}\n(n={n})" for t_, n in zip(SHORT_TICKS, den)], fontsize=FS_TICK, linespacing=1.0)
    axA0.set_xlim(-.45, 3.45); axA0.set_ylim(0, 45); axA0.set_yticks([0, 20, 40]); axA0.set_yticklabels(["0", "20", "40%"], fontsize=FS_TICK)
    [axA0.spines[k].set_visible(False) for k in ("top", "right")]; grid(axA0, "y")
    hbars(axA, [r[0] for r in mrow], [r[1] for r in mrow], [r[2] for r in mrow], sm["n"], sm["n"], fmt_pct=False)
    yA = len(mrow)
    nr_bar(axA, yA, nd, .64)
    axA.text(nd + sm["n"] * .015, yA, str(nd), va="center", fontsize=FS_VALUE)
    axA.set_yticks(list(range(len(mrow) + 1))); axA.set_yticklabels([r[0] for r in mrow] + [T(ko, "Approach not described", "")], linespacing=1.0)
    axA.set_ylim(len(mrow) + .5, -.5)
    two = sum(r[1] for r in mrow) + nd - sm["n"]  # review : studies using two approaches, from the counts
    axA.set_xticks([0, 5, 10, 15, 20, 25]); axA.set_xlabel(T(ko, f"Studies ({two} used two)" if two else "Studies", f" ({two}  )" if two else ""))  # prompt 109: fits the half-width cell
    ftitle(tA, T(ko, f"A. Ranking stability checked, by period and approach (N={Nc})", f"A.   : ,  (N={Nc})"))  # prompt 109
    fig.text(.012, 1 - (tA + TT) / H6, T(ko, "Share of the core studies, by period", ""), ha="left", va="top", fontsize=FS_VALUE - 1.2, color=DGREY)
    fig.text(.50, 1 - (tA + TT) / H6, T(ko, f"Approach, among the {sm['n']} that checked", f" {sm['n']} "), ha="left", va="top", fontsize=FS_VALUE - 1.2, color=DGREY)
    st = o["survey_design_192"]  # prompt 107: used / not used / not applicable, every row adds to 192
    srow = [(T(ko, "Weights mentioned", ""), st["any_weight_mention"]),
            (T(ko, "Survey weights in fitting", ""), st["weights_in_fitting"]),
            (T(ko, "Survey weights in evaluation", ""), st["weights_in_evaluation"]),
            (T(ko, "Strata or PSUs in variance", ""), st["strata_or_psu_in_variance"]),
            (T(ko, "Combined-year survey weights", ""), st["combined_cycle_weights"])]
    yy = np.arange(len(srow))
    for i, (_, r) in enumerate(srow):
        assert sum(r.values()) == NS()["core"]
        axB.barh(i, r["used"], color=TEAL, height=.62)
        axB.barh(i, r["not_used"], left=r["used"], color="white", edgecolor="#9CA3AF", linewidth=.8, height=.62)
        if r["not_applicable"]:
            axB.barh(i, r["not_applicable"], left=r["used"] + r["not_used"], color=NA_GREY, edgecolor="#C4CAD3", linewidth=.5, height=.62)
            axB.text(NS()["core"] + 3, i, T(ko, f"n/a {r['not_applicable']}", f" {r['not_applicable']}"), va="center", fontsize=FS_VALUE - 1.6, color=DGREY, clip_on=False)
        axB.text(r["used"] + 2, i, str(r["used"]), va="center", ha="left", fontsize=FS_VALUE - .6, color="#111827")
    axB.set_yticks(yy); axB.set_yticklabels([r[0] for r in srow], linespacing=1.0); axB.invert_yaxis()
    axB.set_xlim(0, NS()["core"]); axB.set_xticks([0, 50, 100, 150, NS()["core"]]); axB.set_xlabel(T(ko, "Core studies", "")); grid(axB)
    flegend(tB, [Patch(color=TEAL, label=T(ko, "Yes", "")), Patch(facecolor="white", edgecolor="#9CA3AF", label=T(ko, "No", "")),  # prompt 110: row 1 is "mentioned"
                 Patch(facecolor=NA_GREY, edgecolor="#C4CAD3", label=T(ko, "Not applicable", ""))], 3)
    ftitle(tB, T(ko, f"B. Survey design at each workflow step (N={NS()['core']})", f"B.     (N={NS()['core']})"))
    # Prompt 107: counts over all 192 core studies; within (teal), before the split (navy), timing unclear (hatched),
    # step not applied (very light grey). The top row classifies each study over all applied steps.
    pp = o["preprocessing_192"]; N = NS()["core"]
    rows = [(T(ko, "All applied steps", ""), pp["all_applied_steps"])]
    for lab_en, lab_ko, k in (("Missing-value handling", "", "missing_value_handling"), ("Scaling or other", "", "scaling_or_other_preprocessing"),
                              ("Feature selection", "", "feature_selection"), ("Class rebalancing", "", "class_rebalancing")):
        rows.append((T(ko, lab_en, lab_ko), dict(pp[k])))
    # review  (Codex rule 4): feature-selection "not applied" splits into not reported (selection not described)
    fs = rows[3][1]; fs["NR"] = o.get("feature_selection_not_reported", 0); fs["NA"] -= fs["NR"]
    for i, (_, cnt) in enumerate(rows):
        assert sum(cnt.values()) == N
        left = 0
        for stt in ("WITHIN", "BEFORE", "UNCLEAR", "NR", "NA"):
            n = cnt.get(stt, 0)
            if n:
                if stt == "NR":
                    axC.barh(i, n, left=left, color=NA_GREY, hatch="....", edgecolor="#9CA3AF", height=.62, linewidth=.6)
                elif stt == "UNCLEAR":
                    nr_bar(axC, i, n, .62, left=left)
                else:
                    axC.barh(i, n, left=left, color={"WITHIN": TEAL, "BEFORE": "white", "NA": NA_GREY}[stt], height=.62,  # prompt 109: before = open
                             edgecolor={"WITHIN": "white", "BEFORE": "#9CA3AF", "NA": "#C4CAD3"}[stt], linewidth=.8 if stt == "BEFORE" else .6)
                if 0 < n < 9 and stt == "WITHIN":  # prompt 111: count above a teal segment too short for it
                    axC.text(left + n + 1.2, i, f"{n}", ha="left", va="center", fontsize=FS_VALUE - 1.6, color="#111827")
                if n >= 9:
                    axC.text(left + n / 2, i, f"{n}", ha="center", va="center", fontsize=FS_VALUE - 1.0,
                             color="white" if stt == "WITHIN" else "#111827", weight="bold" if i == 0 else "normal",
                             bbox=dict(boxstyle="square,pad=.08", fc="white", ec="none") if stt == "UNCLEAR" else None)
            left += n
    axC.axhline(.5, color="#9CA3AF", lw=.8, ls=(0, (3, 2)))
    axC.set_yticks(range(len(rows))); axC.set_yticklabels([r[0] for r in rows], linespacing=1.0); axC.invert_yaxis()
    axC.get_yticklabels()[0].set_weight("bold")
    axC.set_xlim(0, N); axC.set_xticks([0, 50, 100, 150, N])
    axC.set_xlabel(T(ko, "Core studies", ""))
    flegend(tC, [Patch(color=TEAL, label=T(ko, "Within the training data", "")),
                 Patch(facecolor="white", edgecolor="#9CA3AF", label=T(ko, "Before the split (at least one step)", "")),
                 Patch(facecolor="white", edgecolor=NR_EDGE, hatch="/////", label=T(ko, "Timing unclear", "")),
                 Patch(facecolor=NA_GREY, edgecolor="#9CA3AF", hatch="....", label=T(ko, "Selection not reported", "")),
                 Patch(facecolor=NA_GREY, edgecolor="#C4CAD3", label=T(ko, "Step not applied", ""))], 2)
    ftitle(tC, T(ko, f"C. When data-dependent preprocessing was done (N={N})", f"C.     (N={N})"))
    save(fig, "fig7_next_steps", ko, tight=True)  # prompt 107: earlier-draft Figure 5 -> 6; prompt 108: one grid, text width; prompt 112: 6 -> 7


# --------------------------------------------------------------------------- methods testbed (a supplementary figure of an earlier draft)
def figure_testbed(lang="en", out=None):
    """Former earlier-draft Figure 5; a supplementary figure of an earlier draft from prompt 097."""
    style(lang); ko = lang == "ko"
    import make_streamlined_figures as m
    from collections import Counter
    method = [r for r in m.PURPOSE_RECORDS if r["study_category"] == "METHOD_RESEARCH"]
    _pin(len(method), 36, "make_main_figures.py:586")  # prompt 106 pin
    fig = plt.figure(figsize=(FIG_W, 8.2))
    a = fig.add_axes([.46, .83, .44, .10])
    b = fig.add_axes([.46, .47, .44, .26])
    c = fig.add_axes([.46, .06, .44, .30])
    kc = Counter(r["method_research_category"] for r in method)
    dev = kc["METHOD_WORKFLOW_OR_TOOL_DEVELOPMENT_OR_IMPROVEMENT"]; cmp_ = kc["EXISTING_METHODS_COMPARISON_OR_EVALUATION"]
    # Same definition as claim_evidence_analysis (method_claims.development.comparator_evaluation).
    comparator = sum(r["method_evaluation_mode"] == "EMPIRICAL_COMPARATOR_EVALUATION"
                     for r in method if r["method_research_category"] == "METHOD_WORKFLOW_OR_TOOL_DEVELOPMENT_OR_IMPROVEMENT")
    _pin((dev, cmp_, comparator), (26, 10, 21), "make_main_figures.py:596")  # prompt 106 pin
    a.barh([0, 1], [dev, cmp_], color=[NAVY, PALE_NAVY], height=.62)
    a.barh([0], [comparator], color=TEAL, height=.30)
    a.set_yticks([0, 1]); a.set_yticklabels([T(ko, "Develop or improve\na method", ""), T(ko, "Compare existing\nmethods", "")], linespacing=1.0)
    a.invert_yaxis()
    a.text(dev + .8, 0, str(dev), va="center", fontsize=FS_VALUE - .4)
    a.text(comparator / 2, 0, T(ko, f"{comparator} compared", f" {comparator}"), ha="center", va="center", fontsize=FS_VALUE - 1.4, color="white")
    a.text(cmp_ + .8, 1, str(cmp_), va="center", fontsize=FS_VALUE - .4)
    a.set_xlim(0, 40); a.set_xticks([0, 10, 20, 30]); grid(a)
    title(fig, a, T(ko, f"A. Contribution (N={len(method)})", f"A.   (N={len(method)})"))
    sc = Counter(x for r in method for x in r["method_intervention_stages"])
    model_dev = sum(any(x in r["method_intervention_stages"] for x in ("PREDICTION_OR_CLASSIFICATION", "CLUSTERING_OR_REPRESENTATION", "CAUSAL_OR_STRUCTURE_LEARNING")) for r in method)
    srows = [(T(ko, "Model development", ""), model_dev), (T(ko, "Validation or performance\nevaluation", ""), sc["VALIDATION_OR_PERFORMANCE_EVALUATION"]),
             (T(ko, "Variable construction\nor selection", ""), sc["FEATURE_ENGINEERING_OR_SELECTION"]), (T(ko, "Explanation", ""), sc["EXPLAINABLE_AI"]),
             (T(ko, "User tool or workflow", ""), sc["USER_TOOL_OR_WORKFLOW"]), (T(ko, "Missing data", ""), sc["MISSING_DATA"]),
             (T(ko, "Data integration", ""), sc["DATA_INTEGRATION_OR_HARMONISATION"])]
    hbars(b, [r[0] for r in srows], [r[1] for r in srows], NAVY, len(method), 46)
    b.set_xticks([0, 10, 20, 30]); b.set_xlabel(T(ko, "Method-focused studies (stages overlap)", ""))
    title(fig, b, T(ko, f"B. Analysis stages addressed (N={len(method)})", f"B.    (N={len(method)})"))

    def ev(r):
        if r["method_evaluation_mode"] == "SIMULATION_AND_EMPIRICAL_APPLICATION": return "SIM"
        if r["method_evaluation_mode"] == "EXTERNAL_OR_TRANSPORTABILITY_EVALUATION" or r["knhanes_position"] == "EXTERNAL_OR_TRANSPORTABILITY_EVALUATION": return "IND"
        if r["knhanes_position"] == "ONE_OF_MULTIPLE_PRIMARY_DATASETS": return "MULTI"
        if r["method_evaluation_mode"] == "EVALUATION_DESIGN_INSUFFICIENTLY_REPORTED": return "NR"
        if r["method_evaluation_mode"] == "EMPIRICAL_COMPARATOR_EVALUATION": return "CMP"
        return "APP"
    ec = Counter(ev(r) for r in method)
    erows = [(T(ko, "Simulation plus\nKNHANES application", ""), ec["SIM"], TEAL),
             (T(ko, "Independent population", ""), ec["IND"], TEAL),
             (T(ko, "KNHANES one of several\nprimary datasets", ""), ec["MULTI"], TEAL),
             (T(ko, "KNHANES application,\ncompared with other methods", ""), ec["CMP"], NAVY),
             (T(ko, "KNHANES application\nor demonstration only", ""), ec["APP"], PALE_NAVY),
             (T(ko, "Design not reported", ""), ec["NR"], LGREY)]
    _pin(sum(r[1] for r in erows), 36, "make_main_figures.py:630")  # prompt 106 pin
    _pin(ec["SIM"] + ec["IND"] + ec["MULTI"], 5, "make_main_figures.py:630")  # prompt 106 pin
    hbars(c, [r[0] for r in erows], [r[1] for r in erows], [r[2] for r in erows], len(method), 46)
    c.set_xticks([0, 10, 20, 30]); c.set_xlabel(T(ko, "Method-focused studies", ""))
    title(fig, c, T(ko, f"C. How the method was evaluated (N={len(method)})", f"C.    (N={len(method)})"))
    save(fig, "fig5_methods_testbed", ko, out)


# Prompt 110 (review v47): source font offsets so the median figure text prints at about 7 pt in every main figure
# (prompts/implementation_records/internal review note/font_sizes.py measures the built PDF).
FONT_DELTA = {"figure2": .3, "figure_analysis": 1.3, "figure3": -.2, "figure_named": 0, "figure4": 1.0, "figure5": -1.4}  # prompt 112: earlier-draft Figure 4 one panel


def _sized(fn):
    def run(lang="en"):
        import make_claim_figures as mcf
        g = globals(); keys = ("FS_TITLE", "FS_LABEL", "FS_TICK", "FS_VALUE")
        saved = {k: g[k] for k in keys}; d = FONT_DELTA.get(fn.__name__, 0)
        for k in keys:
            g[k] = saved[k] + d; setattr(mcf, k, saved[k] + d)
        try:
            return fn(lang)
        finally:
            for k in keys:
                g[k] = saved[k]; setattr(mcf, k, saved[k])
    run.__name__ = fn.__name__
    return run


FIGURES = tuple(_sized(f) for f in (figure2, figure_analysis, figure3, figure_named, figure4, figure5))  # prompt 107: six main figures; prompt 110: sized; prompt 112: seven


def main():
    for lang in ("en", "ko"):
        for fn in FIGURES:
            fn(lang)
        figure_checklist_v22_detail(lang)  # v22: earlier-draft Figure 5 (43 items, IDs C01-C43)
    print("built", len(FIGURES) * 2, "figure files")


if __name__ == "__main__":
    main()
