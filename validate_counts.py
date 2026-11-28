"""Recompute the counts reported in the article from the public files of this repository and compare them with the
article (Figure 1 and Supplementary Tables S4 and S5). Run from the repository root: python validate_counts.py
Needs only the Python standard library (openpyxl for the optional Additional Data 1 and 2 checks, which end by running
04_analysis/code/recount_from_additional_data.py: the article's aggregates recounted from Additional Data 1 and 2 and
04_analysis/probast_units.csv)."""
import collections, csv, json, os, sys

ARTICLE = {"identified": 1859, "screened": 921, "assessed": 363, "reports": 287, "studies": 279, "screening_author": 40,
           "fulltext_author": 1, "scr_agreed": 868, "scr_reexamined": 570, "scr_reopened": 25, "eli_agreed": 360, "eli_reexamined": 75, "eli_reopened": 1, "codings": 61326, "step1": 29248, "step2": 21020, "step4": 8876, "step5": 2182, "field_rules": 207,
           "pilot_by_author": 26, "classification": 217, "fallback": 9, "req_codings": 11284, "req_step1": 9849, "req_step2": 946, "req_step4": 365, "req_step5": 124}
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
def stages(R):
    ag = sum(r["rounds"][0]["consensus"]["status"] == "AGREED" for r in R)
    ch = [[x for x in r["rounds"] if x["stage"] == "challenge"] for r in R]
    reop = sum(bool(c) and (c[0]["consensus"]["status"] != "AGREED" or c[0]["consensus"].get("decision") not in ("EXCLUDE_CERTAIN", "EXCLUDE")) for c in ch)
    return ag, sum(bool(c) for c in ch), reop
for nm, R, pre in (("title/abstract", scr, "scr"), ("full text", eli, "eli")):
    ag, rx, ro = stages(R)
    check(f"{nm}: agreed independently", ag, ARTICLE[pre + "_agreed"])
    check(f"{nm}: agreed exclusions re-reviewed", rx, ARTICLE[pre + "_reexamined"])
    check(f"{nm}: re-reviews that reopened the record", ro, ARTICLE[pre + "_reopened"])
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
check("pilot codings decided by the author", sum(c["final"]["route"].startswith("pilot") for c in cod), ARTICLE["pilot_by_author"])
ad = list(csv.DictReader(open("02_selection/author_decisions.csv", encoding="utf-8")))
check("author-adjudicated records with arguments for both positions", sum(bool(r["argument_position_A"] and r["argument_position_B"]) for r in ad), ARTICLE["screening_author"] + ARTICLE["fulltext_author"])
pd = list(csv.DictReader(open("03_coding/author_pilot_decisions.csv", encoding="utf-8")))
check("pilot codings with arguments for both codings", sum(bool(r["argument_position_A"] and r["argument_position_B"]) for r in pd), ARTICLE["pilot_by_author"])
pilot_keys = {(c["record_id"], c["item"]) for c in cod if c["final"]["route"].startswith("pilot")}
check("argued pilot codings are the pilot codings decided by the author", {(r["record_id"], r["item"]) for r in pd} == pilot_keys, True)
check("codings settled by the fallback", sum(c["final"]["route"].startswith("fallback") for c in cod), ARTICLE["fallback"])
req = jl("03_coding/requirement_rounds.jsonl")
check("TRIPOD+AI requirement codings (separate from the item codings)", len(req), ARTICLE["req_codings"])
rs = collections.Counter(c["final"]["settled_at_step"] for c in req)
for k in (1, 2, 4, 5): check(f"requirement codings settled at step {k}", rs[k], ARTICLE[f"req_step{k}"])
rs_rows = list(csv.DictReader(open("03_coding/reporting_status.csv", encoding="utf-8")))
check("reports in the reporting status table", len(rs_rows), ARTICLE["reports"])
check("reporting status table: one row per included report", {r["record_id"] for r in rs_rows} == inc and len({r["record_id"] for r in rs_rows}) == len(rs_rows), True)
link_of = {l["record_id"]: l["study_id"] for l in links}
check("reporting status table: record_id -> study_id as in the report-study links", all(link_of.get(r["record_id"]) == r["study_id"] for r in rs_rows), True)
check("reporting status table: representative reports", {r["record_id"] for r in rs_rows if r["representative_report"] == "yes"} == rep, True)
try:
    from openpyxl import load_workbook
    wb = load_workbook("04_analysis/Additional_Data_1.xlsx", read_only=True)
    allrows = list(wb["Studies"].iter_rows(values_only=True)); hdr, rows = list(allrows[0]), allrows[1:]
    check("studies in Additional Data 1", len(rows), ARTICLE["studies"])
    ci = hdr.index("representative_report")   # column found by name: reader-facing columns come first
    check("Additional Data 1 representative reports match the links", {r[ci] for r in rows} == rep, True)
    sid1 = {r[0] for r in rows}
    check("Additional Data 1 study_ids are the linked studies", sid1 == {l["study_id"] for l in links}, True)
    wb2 = load_workbook("04_analysis/Additional_Data_2.xlsx", read_only=True)
    a2 = list(wb2["Assessment"].iter_rows(values_only=True)); h2, rows2 = list(a2[0]), a2[1:]
    check("classification studies in Additional Data 2", len(rows2), ARTICLE["classification"])
    check("Additional Data 2 studies and reports are in Additional Data 1", all(r[h2.index("study_id")] in sid1 and r[h2.index("record_id")] in rep for r in rows2), True)
    # the article's aggregates recounted from Additional Data 1 and 2 and the unit-level PROBAST+AI judgements (04_analysis/code/recount_from_additional_data.py)
    import subprocess
    rc = subprocess.run([sys.executable, "04_analysis/code/recount_from_additional_data.py"], capture_output=True, text=True)
    out = rc.stdout.strip().splitlines()
    for l in out:
        if l.startswith("FAIL"): print("  " + l)
    print("  " + (out[-1] if out else rc.stderr.strip()[-300:]))
    check("article aggregates recounted from Additional Data 1 and 2 and probast_units.csv", rc.returncode, 0)
except ImportError:
    print("skip Additional Data 1 and 2 checks (openpyxl not installed)")
print("ALL CHECKS PASSED" if ok else "SOME CHECKS FAILED"); sys.exit(0 if ok else 1)
