"""Recompute the counts reported in the article from the public files of this repository and compare them with the
article (Figure 1, Section 2.4 and Supplementary Table S6). Run from the repository root: python validate_counts.py
Needs only the Python standard library (openpyxl for the optional Additional Data 1 check)."""
import collections, csv, json, os, sys

ARTICLE = {"identified": 1859, "screened": 921, "assessed": 363, "reports": 287, "studies": 279, "screening_author": 40,
           "fulltext_author": 1, "codings": 61326, "step1": 29248, "step2": 21020, "step4": 8876, "step5": 2182, "field_rules": 207}
ok = True


def check(name, got, want):
    global ok
    good = got == want; ok &= good
    print(f"{'OK  ' if good else 'FAIL'} {name}: {got} (article {want})")


def jl(p): return [json.loads(l) for l in open(p, encoding="utf-8")]


ss = json.load(open("02_selection/selection_summary.json"))
check("records identified", ss["identified_total"], ARTICLE["identified"])
scr = jl("02_selection/screening_rounds.jsonl"); eli = jl("02_selection/eligibility_rounds.jsonl")
check("records screened", len(scr), ARTICLE["screened"])
to_ft = {r["record_id"] for r in scr if r["final_decision"].endswith("FULL_TEXT")}
check("full texts assessed (sought minus not retrieved)", len(to_ft) - len(ss["not_retrieved_ids"]), ARTICLE["assessed"])
check("full texts assessed (eligibility records)", len(eli), ARTICLE["assessed"])
check("every assessed report was selected at screening", all(r["record_id"] in to_ft for r in eli), True)
inc = {r["record_id"] for r in eli if r["final_decision"] == "INCLUDE"}
check("reports included", len(inc), ARTICLE["reports"])
check("screening decisions by the author (step 5)", sum(r["final_decision"].startswith("AUTHOR:") for r in scr), ARTICLE["screening_author"])
check("full-text decisions by the author (step 5)", sum(r["final_decision"].startswith("AUTHOR:") for r in eli), ARTICLE["fulltext_author"])
links = list(csv.DictReader(open("02_selection/report_study_links.csv")))
check("reports linked to studies are the included reports", {l["record_id"] for l in links} == inc, True)
check("studies", len({l["study_id"] for l in links}), ARTICLE["studies"])
rep = {l["record_id"] for l in links if l["role"] == "representative"}
check("one representative report per study", len(rep), ARTICLE["studies"])

cod = jl("03_coding/coding_rounds.jsonl")
check("item codings", len(cod), ARTICLE["codings"])
st = collections.Counter(c["final"]["settled_at_step"] for c in cod)
for k in (1, 2, 4, 5): check(f"codings settled at step {k}", st[k], ARTICLE[f"step{k}"])
check("CHARMS-based items coded for every included report", {c["record_id"] for c in cod if c["run"] == "charms"} == inc, True)
check("additional items coded for the representative report of every study", {c["record_id"] for c in cod if c["run"] != "charms"} == rep, True)
check("item rules", len(jl("03_coding/field_rules.jsonl")), ARTICLE["field_rules"])
try:
    from openpyxl import load_workbook
    wb = load_workbook("04_analysis/Additional_Data_1.xlsx", read_only=True)
    rows = list(wb["Studies"].iter_rows(values_only=True))[1:]
    check("studies in Additional Data 1", len(rows), ARTICLE["studies"])
    check("Additional Data 1 representative reports match the links", {r[1] for r in rows} == rep, True)
except ImportError:
    print("skip Additional Data 1 check (openpyxl not installed)")
print("ALL CHECKS PASSED" if ok else "SOME CHECKS FAILED"); sys.exit(0 if ok else 1)
