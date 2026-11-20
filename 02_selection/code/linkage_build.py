"""Report-study linkage of the included reports (author decisions) -> results/oct_search/linkage/report_study_links.csv,
and the study count in results/oct_search/public/selection_summary.json. Run after selection_summary.py.
Usage: linkage_build.py"""
import csv, json, os
ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
os.chdir(ROOT)
# linked report -> (representative report, basis); decided by the author on 2026-11-05
LINKS = {
    "OCT0278": ("OCT0785", "same authors and title; earlier of two preprint versions (medRxiv 2025; later version Qeios 2026)"),
    "OCT0664": ("OCT0190", "Research Square preprint of the journal article (Crossref is-preprint-of)"),
    "OCT0736": ("OCT0728", "JMIR preprint of the journal article (same manuscript number and authors)"),
    "OCT0276": ("OCT0771", "medRxiv preprint of the journal article: same KNHANES 2015-2019 sample (11,929 women aged >= 35), predictors, network and results"),
    "OCT0652": ("OCT0170", "Research Square preprint of the journal article: same authors, KNHANES sample and results"),
    "OCT0682": ("OCT0429", "SSRN preprint of the journal article: same authors and KNHANES sample (198,964 participants, 3,529 with asthma)"),
    "OCT0734": ("OCT0735", "earlier of two JMIR preprint versions of the same study: same authors and KNHANES sample (13,946 participants); later version represents"),
    "OCT0285": ("OCT0342", "conference paper (EMBC 2014) of the same study as the journal article: same KNHANES 2010 development and 2011 validation samples and SVM results; the journal article adds an ANN"),
}
inc = [r["record_id"] for r in csv.DictReader(open("results/oct_search/public/included_reports.csv"))]
assert all(k in inc and v[0] in inc for k, v in LINKS.items()), "linked or representative report not included"
rows = [dict(study_id="S_" + (LINKS[i][0] if i in LINKS else i), record_id=i, role="linked_report" if i in LINKS else "representative",
             link_basis=LINKS[i][1] if i in LINKS else "", decided_by="author (2026-11-05)" if i in LINKS else "") for i in inc]
os.makedirs("results/oct_search/linkage", exist_ok=True)
for out in ("results/oct_search/linkage/report_study_links.csv", "results/oct_search/public/report_study_links.csv"):
    with open(out, "w", newline="") as f:
        w = csv.DictWriter(f, fieldnames=list(rows[0])); w.writeheader(); w.writerows(rows)
s = json.load(open("results/oct_search/public/selection_summary.json"))
s["studies_included"] = len({r["study_id"] for r in rows}); s["reports_linked_to_another_report_of_the_same_study"] = len(LINKS)
json.dump(s, open("results/oct_search/public/selection_summary.json", "w"), indent=1)
print("reports", len(rows), "studies", s["studies_included"])
