"""Render Additional file 13 as detailed classification-process and analytic-function figures.

Exact reusable values remain in the three PROMPT3 TSV ledgers and are also joined into
INTEGRATED_STUDY_AUDIT.tsv/xlsx.  This module only changes the reader-facing presentation.
"""
from __future__ import annotations

import json
from pathlib import Path

import matplotlib.pyplot as plt
import numpy as np

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "figures/submission"
APP = ROOT / "manuscript/submission/appendices/appendix13_prompt3_figures.md"

BLUE, SKY, GREEN, ORANGE, RED, GREY = "#315B7D", "#64A9CF", "#3D8B6D", "#D88932", "#B84A4A", "#7A8591"


def style() -> None:
    plt.rcParams.update({
        "font.family": "DejaVu Sans", "font.size": 8.5, "axes.titlesize": 10,
        "axes.labelsize": 8.5, "axes.spines.top": False, "axes.spines.right": False,
        "figure.facecolor": "white", "axes.facecolor": "white",
    })


def save(fig: plt.Figure, name: str) -> None:
    OUT.mkdir(parents=True, exist_ok=True)
    fig.savefig(OUT / f"{name}.pdf", bbox_inches="tight")
    fig.savefig(OUT / f"{name}.png", dpi=300, bbox_inches="tight")
    plt.close(fig)


def barh(ax, labels, values, denominator, title, color=BLUE) -> None:
    y = np.arange(len(labels))
    colors = color if isinstance(color, list) else [color] * len(labels)
    ax.barh(y, values, color=colors, height=.66)
    ax.set_yticks(y, labels)
    ax.invert_yaxis()
    maximum = max(values) if values else 1
    ax.set_xlim(0, max(maximum * 1.30, 1))
    for i, value in enumerate(values):
        ax.text(value + maximum * .018, i, f"{value} ({100 * value / denominator:.1f}%)", va="center", fontsize=7.3)
    ax.set_title(title, loc="left", fontweight="bold")
    ax.set_xlabel(f"Analyses/studies (denominator={denominator})")
    ax.grid(axis="x", color="#E1E6EA", linewidth=.6)
    ax.set_axisbelow(True)


def figure_1(data: dict) -> None:
    n = data["n_classification"]
    q = data["metric_counts"]
    style()
    fig, axes = plt.subplots(4, 2, figsize=(14, 12.8))
    axes = axes.ravel()
    barh(axes[0], ["Accuracy", "Balanced accuracy", "F1", "MCC"],
         [q[x] for x in ("Accuracy", "Balanced accuracy", "F1", "MCC")], n,
         "A. Overall and threshold-dependent metrics", [BLUE, SKY, GREEN, ORANGE])
    barh(axes[1], ["AUROC", "AUPRC / average precision"],
         [q["AUROC"], q["AUPRC/average precision"]], n,
         "B. Discrimination", [BLUE, ORANGE])
    barh(axes[2], ["Sensitivity / recall", "Specificity / TNR", "Precision / PPV", "NPV"],
         [q[x] for x in ("Sensitivity/recall", "Specificity/TNR", "Precision/PPV", "NPV")], n,
         "C. Class-specific metrics", [BLUE, SKY, GREEN, ORANGE])
    barh(axes[3], ["Brier score", "Log loss", "Calibration", "Decision curve / net benefit"],
         [q[x] for x in ("Brier score", "Log loss", "Calibration", "Decision curve/net benefit")], n,
         "D. Probabilistic performance and clinical utility", [SKY, GREY, GREEN, ORANGE])
    barh(axes[4], ["Confidence interval", "SD / resampling distribution", "Paired model comparison"],
         [q[x] for x in ("Confidence interval", "SD/resampling distribution", "Paired model comparison")], n,
         "E. Uncertainty and comparative inference", [BLUE, SKY, ORANGE])
    s = data["selection_metric"]
    single = sum(s.get(x, 0) for x in ("AUROC", "Accuracy", "F1", "AUPRC", "Balanced accuracy", "Clinical utility"))
    labels = ["Explicit single primary metric", "Explicit multiple-metric judgement",
              "Best model claimed; criterion not reported", "Selection rule not recoverable"]
    vals = [single, s.get("Multiple metrics", 0), s.get("Author-selected; criterion not reported", 0), s.get("Not recoverable", 0)]
    barh(axes[5], labels, vals, n, "F. Criterion used to designate the best model", [GREEN, BLUE, ORANGE, RED])
    axes[5].text(.01, -.22, f"Single-metric detail: AUROC {s.get('AUROC',0)}; accuracy {s.get('Accuracy',0)}; F1 {s.get('F1',0)}; AUPRC {s.get('AUPRC',0)}.",
                 transform=axes[5].transAxes, fontsize=7.3)
    threshold = data["threshold_method"]
    threshold_keys = ["Not reported", "Youden index", "Validation/OOF selected", "F1 optimised", "Fixed 0.5", "Other/unclear reported method"]
    threshold_labels = ["Not reported", "Youden index", "Validation / out-of-fold", "F1 optimised", "Fixed at 0.5", "Other incompletely specified rule"]
    barh(axes[6], threshold_labels, [threshold[x] for x in threshold_keys], n,
         "G. Decision-threshold selection", [GREY, BLUE, GREEN, ORANGE, SKY, RED])
    axes[7].axis("off")
    fig.suptitle("Figure S13. Performance evaluation and model-selection reporting", fontsize=14, fontweight="bold", y=.995)
    fig.text(.5, .004, f"Unit: {n} primary classification studies. Metric indicators overlap; model-selection categories are mutually exclusive.", ha="center", fontsize=8)
    fig.tight_layout(rect=(0, .018, 1, .98), h_pad=2.7, w_pad=3.2)
    save(fig, "figS13_performance_selection")


def figure_2(data: dict) -> None:
    n = data["n_classification"]
    strategy = data["imbalance_strategy"]
    active_names = ["SMOTE/ADASYN", "Random over/undersampling", "Multiple methods", "Class weighting/cost-sensitive"]
    active_n = sum(strategy[x] for x in active_names)
    assert active_n == 72
    style()
    fig = plt.figure(figsize=(13, 11.2))
    grid = fig.add_gridspec(3, 2, height_ratios=[1, 1, 1.45], hspace=.45, wspace=.38)
    ax = [fig.add_subplot(grid[0, 0]), fig.add_subplot(grid[0, 1]), fig.add_subplot(grid[1, 0]), fig.add_subplot(grid[1, 1]), fig.add_subplot(grid[2, :])]
    labels = ["No strategy reported", "Explicitly no handling", "SMOTE / ADASYN",
              "Random over- or undersampling", "Two or more methods", "Class weighting / cost-sensitive"]
    values = [strategy["Not reported"], strategy["No handling stated"], strategy["SMOTE/ADASYN"],
              strategy["Random over/undersampling"], strategy["Multiple methods"], strategy["Class weighting/cost-sensitive"]]
    barh(ax[0], labels, values, n, "A. Class-imbalance strategy", [GREY, SKY, BLUE, GREEN, ORANGE, RED])
    timing = data["imbalance_application_order"]
    tl = ["Order not reported", "Training data only", "Within each resampling training partition", "Before split (leakage concern)"]
    barh(ax[1], tl, [timing[x] for x in tl], active_n, "B. Timing among active interventions", [GREY, BLUE, GREEN, RED])
    test = data["test_distribution"]
    dl = ["Not reported", "Original prevalence retained", "Balanced / altered test distribution"]
    dv = [test["Not reported"], test["Original prevalence retained"], test["Balanced/altered test distribution"]]
    barh(ax[2], dl, dv, active_n, "C. Evaluation distribution among active interventions", [GREY, GREEN, RED])
    recover = data["class_distribution_recoverability"]
    barh(ax[3], ["Partly recoverable", "Not recoverable"], [recover["Partial"], recover["No"]], n,
         "D. Class-distribution recoverability", [GREEN, RED])

    metric_names = ["Accuracy", "AUROC", "AUPRC", "F1", "Calibration"]
    rows = ["Not reported", "SMOTE/ADASYN", "Random over/undersampling", "Multiple methods", "Class weighting/cost-sensitive", "No handling stated"]
    matrix = np.array([[100 * data["strategy_by_metric"][r][m if m != "AUPRC" else "AUPRC/average precision"] / strategy[r] for m in metric_names] for r in rows])
    image = ax[4].imshow(matrix, cmap="Blues", vmin=0, vmax=100, aspect="auto")
    ax[4].set_xticks(range(len(metric_names)), metric_names)
    ax[4].set_yticks(range(len(rows)), [f"{r} (n={strategy[r]})" for r in rows])
    for i, r in enumerate(rows):
        for j, m in enumerate(metric_names):
            raw = data["strategy_by_metric"][r][m if m != "AUPRC" else "AUPRC/average precision"]
            ax[4].text(j, i, f"{raw}\n({matrix[i,j]:.1f}%)", ha="center", va="center", fontsize=7,
                       color="white" if matrix[i, j] >= 55 else "#17212B")
    ax[4].set_title("E. Reported metric within each imbalance-strategy row", loc="left", fontweight="bold")
    fig.colorbar(image, ax=ax[4], fraction=.018, pad=.015, label="Row percentage (%)")
    fig.suptitle("Figure S14. Class-imbalance handling and evaluation integrity", fontsize=14, fontweight="bold", y=.995)
    fig.text(.5, .012, "Timing and evaluation-distribution panels use the 72 studies reporting an active intervention. Small rows (class weighting n=7; explicitly no handling n=2) are descriptive only.", ha="center", fontsize=8)
    fig.subplots_adjust(top=.95, bottom=.06)
    save(fig, "figS14_imbalance_integrity")


def stacked(ax, labels, series, title, denominator) -> None:
    colors = [GREEN, SKY, ORANGE, RED]
    left = np.zeros(len(labels))
    for idx, (name, values) in enumerate(series):
        values = np.array(values)
        ax.barh(np.arange(len(labels)), values, left=left, label=name, color=colors[idx], height=.56)
        for y, (start, value) in enumerate(zip(left, values)):
            if value >= 7:
                ax.text(start + value / 2, y, f"{int(value)}\n({100*value/denominator:.1f}%)", ha="center", va="center", fontsize=6.8,
                        color="white" if idx in (0, 3) else "#17212B")
        left += values
    ax.set_xlim(0, denominator)
    ax.set_yticks(np.arange(len(labels)), labels)
    ax.invert_yaxis(); ax.grid(axis="x", color="#E1E6EA", linewidth=.6); ax.set_axisbelow(True)
    ax.set_title(title, loc="left", fontweight="bold"); ax.set_xlabel(f"Classification studies (n={denominator})")


def figure_3(data: dict) -> None:
    n = data["n_classification"]
    style()
    fig, axes = plt.subplots(1, 2, figsize=(14, 7.7))
    stacked(axes[0], ["Definition reproducibility", "Definition credibility", "Overall construction adequacy"], [
        ("Favourable / robust", [data["outcome_reproducibility"]["R2"], data["outcome_credibility"]["C2"], data["outcome_overall"]["Robust"]]),
        ("Limited", [data["outcome_reproducibility"]["R1"], data["outcome_credibility"]["C1"], data["outcome_overall"]["Limited"]]),
        ("Unclear / not assessable", [0, data["outcome_credibility"]["CU"], data["outcome_overall"]["Not assessable"]]),
        ("Not reproducible", [data["outcome_reproducibility"]["R0"], 0, 0]),
    ], "A. Outcome construction", n)
    stacked(axes[1], ["Predictor-set reconstructability", "Target–predictor alignment", "Overall adequacy"], [
        ("Favourable / robust", [data["predictor_reconstructability"]["R2"], data["target_predictor_alignment"]["C2"], 0]),
        ("Limited", [data["predictor_reconstructability"]["R1"], data["target_predictor_alignment"]["C1"], data["predictor_overall"]["Limited"]]),
        ("Unclear / not assessable", [0, data["target_predictor_alignment"]["CU"], data["predictor_overall"]["Not assessable"]]),
        ("High concern / not reconstructable", [data["predictor_reconstructability"]["R0"], data["target_predictor_alignment"]["C0"], data["predictor_overall"]["High concern"]]),
    ], "B. Predictor construction and alignment", n)
    for axis in axes:
        axis.legend(loc="upper center", bbox_to_anchor=(.5, -.18), fontsize=7, frameon=False, ncol=2)
    fig.suptitle("Figure S15. Outcome and predictor construction audit", fontsize=14, fontweight="bold", y=.98)
    fig.text(.5, .06,
             "Codebook: R2=fully reproducible/reconstructable; R1=partly reproducible/reconstructable; R0=not reproducible/reconstructable; "
             "C2=credible/aligned; C1=limited; C0=high concern; CU=unclear/not assessable.", ha="center", fontsize=8, wrap=True)
    fig.subplots_adjust(top=.84, bottom=.27, wspace=.38)
    save(fig, "figS15_outcome_predictor")


def markdown() -> None:
    text = r"""# Additional file 13. Detailed classification-process and analytic-function audits

**Preliminary—internal quality-control output.** Evidence-assisted primary coding has not yet completed independent second review and consensus adjudication. Exact study-level values remain available in `INTEGRATED_STUDY_AUDIT.tsv` and `.xlsx`; the figures below are the reader-facing synthesis and do not replace the reusable ledgers.

The unit is the full-report primary classification cohort (n=206). Three studies assigned to other primary analytic tasks additionally trained ancillary classifiers; those components remain in Additional file 15 but are not added to this cohort. Metric indicators may overlap. Model-selection categories are mutually exclusive.

## Figure S13. Performance evaluation and model-selection reporting

\begin{center}
\includegraphics[width=.97\linewidth,height=.78\textheight,keepaspectratio]{figures/submission/figS13_performance_selection.pdf}
\end{center}

AUROC and accuracy dominated, whereas imbalance-sensitive metrics, calibration, clinical utility, and uncertainty-aware comparisons were uncommon.

**Review status:** Evidence-assisted primary-review judgements; independent second review and consensus pending.

\newpage

## Figure S14. Class-imbalance handling and evaluation integrity

\begin{center}
\includegraphics[width=.97\linewidth,height=.78\textheight,keepaspectratio]{figures/submission/figS14_imbalance_integrity.pdf}
\end{center}

Timing and evaluation-distribution percentages are conditional on the 72 studies reporting an active intervention.

**Review status:** Evidence-assisted primary-review judgements; independent second review and consensus pending.

\newpage

## Figure S15. Outcome and predictor construction audit

\begin{center}
\includegraphics[width=.97\linewidth,height=.78\textheight,keepaspectratio]{figures/submission/figS15_outcome_predictor.pdf}
\end{center}

Outcome-definition reproducibility and credibility, and predictor-set reconstructability and target alignment. Full code meanings are printed below the panels.

**Review status:** Evidence-assisted primary-review judgements; independent second review and consensus pending.

\newpage

## Figure S16. Classification-outcome construction and class structure

\begin{center}
\includegraphics[width=.97\linewidth,height=.78\textheight,keepaspectratio]{figures/submission/fig3b_target_definition.pdf}
\end{center}

This figure expands outcome-definition source, class count, and recoverability beyond the main-text summary.

**Review status:** Evidence-assisted primary-review judgements; independent second review and consensus pending.

\newpage

## Figure S17. Variable-importance endpoints and selection rules

\begin{center}
\includegraphics[width=.97\linewidth,height=.78\textheight,keepaspectratio]{figures/submission/fig9_importance_endpoints.pdf}
\end{center}

The panels detail where variable-importance analyses stopped, temporal change in those endpoints, and the reported rules used to select variables.

**Review status:** Evidence-assisted primary-review judgements; independent second review and consensus pending.

\newpage

## Figure S18. Reported important-variable domains

\begin{center}
\includegraphics[width=.97\linewidth,height=.78\textheight,keepaspectratio]{figures/submission/fig10_important_variables.pdf}
\end{center}

Domain frequencies describe variables reported as important within each study's candidate set and outcome definition; they are not population effect estimates.

**Review status:** Evidence-assisted primary-review judgements; independent second review and consensus pending.
"""
    APP.write_text(text, encoding="utf-8")


def main() -> None:
    data = json.load(open(ROOT / "results/derived/prompt3_audit.json", encoding="utf-8"))
    assert data["n_classification"] == 206
    figure_1(data); figure_2(data); figure_3(data); markdown()
    print(APP.relative_to(ROOT))


if __name__ == "__main__":
    main()
