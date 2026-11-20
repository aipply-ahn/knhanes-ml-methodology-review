"""PRISMA 2020 flow diagram from results/oct_search/public/selection_summary.json.
Output: results/oct_search/public/prisma_flow.pdf and .png; with 'ko', the Korean version prisma_flow_ko.pdf/.png
(manuscript Figure 1: copied to figures/submission/fig1_prisma(_ko)). Usage: prisma_figure.py [ko]"""
import json, os, sys
KO = "ko" in sys.argv[1:]
T = lambda en, ko: ko if KO else en
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.patches import FancyBboxPatch
ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
S = json.load(open(os.path.join(ROOT, "results/oct_search/public/selection_summary.json")))
idf, rb = S["identified"], S["removed_before_screening"]
ta, ft = S["records_excluded_by_code"], S["reports_excluded_by_code"]
f = lambda n: f"{n:,}"

fig, ax = plt.subplots(figsize=(10, 12.2)); ax.set_xlim(0, 100); ax.set_ylim(0, 122); ax.axis("off")
plt.rcParams["font.family"] = "NanumGothic" if KO else "DejaVu Sans"


TR = [("Records identified (search on 2 November 2026)", ""), ("Korean Citation Index", ""),
      ("KDCA KNHANES publication list", ""), ("Total", ""), ("Records removed before screening", ""), ("Duplicate records", ""), ("Ineligible report type or withdrawn", ""),
      ("theses", ""), ("reviews, editorials, errata, protocols", ""),
      ("conference abstracts, code or data\n    deposits", ""), ("withdrawn from repository", ""),
      ("Records screened (titles and abstracts)", ""), ("Records excluded", ""),
      ("KNHANES data not analysed", ""), ("No eligible supervised learner", ""),
      ("Neither health outcome nor ML method", ""), ("Reports sought for retrieval", ""),
      ("Reports not retrieved", ""), ("Reports assessed for eligibility\n(full text)", ""),
      ("Reports excluded", ""), ("Retracted publication", ""), ("Reports included", ""),
      ("Reports linked to another report of\nthe same study", ""),
      ("(preprint and journal version, or\n  conference paper and journal article)", ""),
      ("Studies included", "")]


def box(x, y, w, h, text, fc="white", size=8.6, bold=False):
    for a, b in (TR if KO else []): text = text.replace(a, b)
    ax.add_patch(FancyBboxPatch((x, y), w, h, boxstyle="square,pad=0", fc=fc, ec="black", lw=0.9))
    ax.text(x + 1.2, y + h - 1.2, text, va="top", ha="left", fontsize=size, fontweight="bold" if bold else "normal", linespacing=1.35)


def arrow(x1, y1, x2, y2):
    ax.annotate("", xy=(x2, y2), xytext=(x1, y1), arrowprops=dict(arrowstyle="-|>", lw=0.9, color="black"))


def band(y, h, label):
    ax.add_patch(FancyBboxPatch((0, y), 4.5, h, boxstyle="round,pad=0.2", fc="#cfe2f3", ec="#9fc5e8", lw=0.8))
    ax.text(2.25, y + h / 2, label, rotation=90, va="center", ha="center", fontsize=9.5, fontweight="bold")


L, R, W = 7, 56, 42
# identification
band(88, 33, T("Identification", ""))
box(L, 99, W, 21, "Records identified (search on 2 November 2026)\n"
    f"  Europe PMC (n = {f(idf['europepmc'])})\n  PubMed (n = {f(idf['pubmed'])})\n  OpenAlex (n = {f(idf['openalex'])})\n"
    f"  Korean Citation Index (n = {f(idf['kci'])})\n  KDCA KNHANES publication list (n = {f(idf['kdca'])})\n"
    f"Total (n = {f(S['identified_total'])})")
box(R, 92, W, 28, "Records removed before screening\n"
    f"  Duplicate records (n = {f(S['duplicates_removed'])})\n"
    f"  Ineligible report type or withdrawn (n = {f(sum(rb.values()))})\n"
    f"    theses (n = {rb['thesis']})\n    reviews, editorials, errata, protocols (n = {rb['review_editorial_erratum_protocol']})\n"
    f"    conference abstracts, code or data\n    deposits (n = {rb['conference_abstract_or_deposit']})\n"
    f"    withdrawn from repository (n = {rb['withdrawn']})")
arrow(L + W, 109, R, 109)
# screening
band(30, 55, T("Screening", ""))
box(L, 74, W, 9, f"Records screened (titles and abstracts)\n(n = {f(S['records_screened'])})")
box(R, 70, W, 15, f"Records excluded (n = {f(S['records_excluded'])})\n"
    f"  KNHANES data not analysed (n = {ta.get('X1', 0)})\n  No eligible supervised learner (n = {ta.get('X2', 0)})\n"
    f"  Neither health outcome nor ML method\n  (n = {ta.get('X3', 0)})\n  Ineligible report type (n = {ta.get('X4', 0)})")
arrow(L + W / 2, 99, L + W / 2, 83); arrow(L + W, 78.5, R, 78.5)
box(L, 55, W, 9, f"Reports sought for retrieval\n(n = {f(S['reports_sought'])})")
box(R, 56, W, 7, f"Reports not retrieved\n(n = {S['reports_not_retrieved']})")
arrow(L + W / 2, 74, L + W / 2, 64); arrow(L + W, 59.5, R, 59.5)
box(L, 33, W, 9, f"Reports assessed for eligibility\n(full text) (n = {f(S['reports_assessed'])})")
box(R, 26, W, 20, f"Reports excluded (n = {S['reports_excluded']})\n"
    f"  Ineligible report type (n = {ft.get('F1', 0)})\n  KNHANES data not analysed (n = {ft.get('F2', 0)})\n"
    f"  No eligible supervised learner (n = {ft.get('F3', 0)})\n  Neither health outcome nor ML method\n  (n = {ft.get('F4', 0)})\n  Retracted publication (n = {ft.get('RETRACTED', 0)})")
arrow(L + W / 2, 55, L + W / 2, 42); arrow(L + W, 37.5, R, 37.5)
# included
band(1, 26, T("Included", ""))
box(L, 14, W, 9, f"Reports included\n(n = {S['reports_included']})", bold=True)
box(R, 13, W, 11, f"Reports linked to another report of\nthe same study (n = {S['reports_linked_to_another_report_of_the_same_study']})\n"
    "  (preprint and journal version, or\n  conference paper and journal article)")
arrow(L + W / 2, 33, L + W / 2, 23); arrow(L + W, 18.5, R, 18.5)
box(L, 2, W, 8, f"Studies included\n(n = {S['studies_included']})", bold=True)
arrow(L + W / 2, 14, L + W / 2, 10)
out = os.path.join(ROOT, "results/oct_search/public/prisma_flow" + ("_ko" if KO else ""))
fig.savefig(out + ".pdf", bbox_inches="tight"); fig.savefig(out + ".png", dpi=200, bbox_inches="tight")
print(out)
