"""PRISMA counts and the list of included reports, derived from the frozen search flow and the two run directories.
Outputs: results/oct_search/public/selection_summary.json, included_reports.csv. Usage: selection_summary.py"""
import collections, csv, json, os
ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
P = lambda *a: os.path.join(ROOT, *a)
fl = json.load(open(P("results/oct_search/flow.json")))
L = {r["record_id"]: r for r in csv.DictReader(open(P("results/oct_search/candidates_ledger.tsv")), delimiter="\t")}
ta = list(csv.DictReader(open(P("results/oct_search/screening/run/decisions.csv"))))
ft = list(csv.DictReader(open(P("results/oct_search/eligibility/run_batch1/decisions.csv"))))
final = lambda r, inc: (r["author_decision"] or "").upper() if r["final_decision"] == "AUTHOR_PENDING" else r["final_decision"]
ta_c = collections.Counter("FULL_TEXT" if final(r, 0) == "FULL_TEXT" else r["final_decision"] for r in ta)
ta_ex = [r for r in ta if r["final_decision"] == "EXCLUDE"]
targets = [r["record_id"] for r in ta if r["final_decision"] == "FULL_TEXT" or r["author_decision"] == "FULL_TEXT"]
not_retr = [i for i in targets if L[i]["fulltext_status"] == "NOT_RETRIEVED"]
ft_final = {r["record_id"]: (final(r, 1), r["exclusion_code"] or r.get("author_code", "")) for r in ft}
# author exclusions after the run (e.g. retracted publications), kept outside the run files
for r in csv.DictReader(open(P("results/oct_search/eligibility/author_post_run_exclusions.csv"))):
    assert r["record_id"] in ft_final; ft_final[r["record_id"]] = (r["decision"], r["reason_code"])
inc = sorted(i for i, (d, c) in ft_final.items() if d == "INCLUDE")
exc = collections.Counter(c for d, c in ft_final.values() if d == "EXCLUDE")
withdrawn = sum(1 for r in L.values() if r.get("screening_status", "").startswith("REMOVED_BEFORE_SCREENING: withdrawn"))
S = dict(identified=fl["identified"], identified_total=fl["identified_total"], duplicates_removed=fl["identified_total"] - fl["after_deduplication"],
         removed_before_screening=dict(thesis=fl["excluded_thesis"], review_editorial_erratum_protocol=fl["excluded_other_type"],
                                       conference_abstract_or_deposit=fl["excluded_not_research_report"], withdrawn=withdrawn),
         records_screened=len(ta), records_excluded=len(ta_ex),
         records_excluded_by_code=dict(collections.Counter(r["exclusion_code"] for r in ta_ex)),
         reports_sought=len(targets), reports_not_retrieved=len(not_retr), not_retrieved_ids=not_retr,
         reports_assessed=len(ft), reports_excluded=sum(exc.values()), reports_excluded_by_code=dict(exc), reports_included=len(inc))
json.dump(S, open(P("results/oct_search/public/selection_summary.json"), "w"), indent=1)
with open(P("results/oct_search/public/included_reports.csv"), "w", newline="") as f:
    w = csv.writer(f); w.writerow(["record_id", "title", "doi", "pmid", "kci_id", "year"])
    for i in inc:
        r = L[i]; w.writerow([i, r["title"], r["doi"], r["pmid"], r["kci_id"], r["year"]])
print(json.dumps(S, indent=1))
