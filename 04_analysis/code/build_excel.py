"""Excel files of the October-search data coding (2026-11-19; author: 'convert to Excel').
Private working file (all coded values, including printed phrases copied from the reports; not for publication):
  results/oct_search/coding/KNHANES_ML_coding_private.xlsx
    README, Studies, Reports, Coding (one row per value: status, inconsistency, unit, value, kind, full value before
    shortening, evidence IDs, settling route), Status (report x item), Performance (performance rows), Items (definitions
    and general rules of v3.1.3), Field_rules, Derivation (rules of the study-level variables).
Public file (Additional Data 1; no text copied from the reports: no values, quotations, evidence or page locations):
  manuscript/KNHANES_ML_review_Additional_Data_1.xlsx
    README, Studies (bibliographic details and study-level variables), Status (report x item reporting status and
    inconsistency flag), Items, Field_rules, Derivation.
Usage: build_excel.py"""
import collections, csv, json, os, re, sys
HERE = os.path.dirname(os.path.abspath(__file__)); ROOT = os.path.dirname(os.path.dirname(HERE)); os.chdir(ROOT)
from openpyxl import Workbook
from openpyxl.styles import Font, Alignment
from openpyxl.utils import get_column_letter
from openpyxl.cell.cell import ILLEGAL_CHARACTERS_RE
C = "results/oct_search/coding"; A = f"{C}/analysis"
ITEMS = json.load(open("tools/oct_search/coding/charms_items_v3.1.3.json"))
ROUTE = [("agree_r1", "agreed in round 1"), ("consensus", "consensus reading"), ("rule_not_material", "difference not material, settled by rule"),
         ("verify_inconsistency", "inconsistency check"), ("triage_form", "form difference, settled by rule"), ("triage_rule", "rule difference, settled by rule"),
         ("rule_blind", "rule difference, blinded rule reading"), ("decision", "pilot review decision"), ("field_rule", "field rule"), ("rule_fix_side", "fallback rule: coding one system accepted"), ("rule_fix_unclear", "fallback rule: coded unclear"), ("rule_fix", "field rule, checker's problem fixed")]


def route(h):
    return next((t for k, t in ROUTE if h.startswith(k)), h)


def sheet(wb, name, header, rows, widths=None, note=None):
    ws = wb.create_sheet(name)
    r0 = 1
    if note: ws.cell(1, 1, note).font = Font(italic=True); r0 = 3
    for j, h in enumerate(header, 1): c = ws.cell(r0, j, h); c.font = Font(bold=True)
    for i, row in enumerate(rows, r0 + 1):
        for j, v in enumerate(row, 1): ws.cell(i, j, ILLEGAL_CHARACTERS_RE.sub("", v) if isinstance(v, str) else v)  # control characters from PDF text dropped
    ws.freeze_panes = ws.cell(r0 + 1, 2)
    for j, h in enumerate(header, 1): ws.column_dimensions[get_column_letter(j)].width = (widths or {}).get(h, min(40, max(10, len(str(h)) + 2)))
    return ws


PREPRINT = re.compile(r"^10\.(21203|1101|2196/preprints|32388|20944|48550|2139|31219|36227|22541)")
SERVER = {"10.21203": "Research Square", "10.1101": "medRxiv or bioRxiv", "10.2196/preprints": "JMIR Preprints", "10.20944": "Preprints.org",
          "10.48550": "arXiv", "10.2139": "SSRN", "10.31219": "OSF Preprints", "10.36227": "TechRxiv", "10.22541": "Authorea", "10.32388": "Qeios"}
TYPE_OVERRIDE = {"OCT1302": "conference paper", "OCT1440": "conference paper"}  # ITBAM and ICCC proceedings papers without a DOI
AUTHOR_OVERRIDE = {"OCT1302": "Park", "OCT1436": "Kim", "OCT1440": "Ishag", "OCT0742": "Malaysha"}  # not in the search metadata: first author as printed in the report
VENUE_OVERRIDE = {"OCT1251": "International Journal of Applied Science and Engineering"}  # from the DOI prefix; not in the search metadata


def venues(meta):
    """journal or venue, publication type and first author of each included report, from the search metadata only
    (Crossref container for DOIs; otherwise the source record's journal field, matched by DOI, KCI id, PMID or title;
    preprint servers by DOI prefix)."""
    cm = json.load(open("results/oct_search/crossref_meta_screened.json"))
    R = json.load(open("results/oct_search/records.json"))
    by = {}
    for x in R:
        for m in x["members"]:
            for k in ("doi", "kci_id", "pmid"):
                v = str(m.get(k) or "").lower()
                if v and v != "none": by.setdefault((k, v), []).append(m)
            by.setdefault(("title", str(m.get("title") or "").lower().strip(" .")), []).append(m)
    fa = json.load(open("results/oct_search/legacy_fig/first_authors.json"))
    out = {}
    for r, x in meta.items():
        c = cm.get(r) or {}; doi = (x["doi"] or "").lower()
        ms = [m for k in ("doi", "kci_id", "pmid") for m in by.get((k, str(x[k]).lower()), [])] or by.get(("title", x["title"].lower().strip(" .")), [])
        js = [m["journal"] for m in ms if m.get("journal") and m["journal"] != "None"]
        en = [j for j in js if not re.search("[\uac00-\ud7a3]", j)]
        pre = next((v for k, v in SERVER.items() if doi.startswith(k)), None) if PREPRINT.match(doi) else None
        venue = VENUE_OVERRIDE.get(r) or c.get("container") or pre or (en or js or [""])[0]
        ct = c.get("type")
        typ = TYPE_OVERRIDE.get(r) or ("preprint" if pre or ct == "posted-content" else {"journal-article": "journal article", "proceedings-article": "conference paper",
               "book-chapter": "book chapter"}.get(ct) or ("journal article" if any(m.get("source") == "KCI" or "article" in str(m.get("ptype")) or "\ud559\uc220\uc9c0" in str(m.get("ptype")) for m in ms) else "other"))
        out[r] = dict(venue=venue, type=typ, first_author=fa.get(r) or AUTHOR_OVERRIDE.get(r, ""))
    return out


def main():
    rows = [json.loads(l) for l in open(f"{C}/final_items_clean.jsonl")]
    links = list(csv.DictReader(open("results/oct_search/public/report_study_links.csv")))
    sid = {l["record_id"]: l["study_id"] for l in links}
    meta = {r["record_id"]: r for r in csv.DictReader(open("results/oct_search/public/included_reports.csv"))}
    D = {r["record_id"]: r for r in csv.DictReader(open(f"{A}/study_derived.csv"))}
    for r in csv.DictReader(open(f"{A}/study_classified.csv")): D[r["record_id"]].update(r)
    items = [i for g in ITEMS["groups"].values() for i in g]
    grp = {i: g for g, its in ITEMS["groups"].items() for i in its}
    fr = json.load(open(f"{C}/field_rules_decided.json"))
    der = list(csv.reader(open(f"{A}/derive_rules.tsv"), delimiter="\t"))
    st = collections.defaultdict(dict)
    for r in rows: st[r["record_id"]][r["item"]] = r["final"]
    LEG = [("v3.1.3-legacy1", "results/oct_search/coding_legacy"), ("v3.1.3-legacy2", "results/oct_search/coding_legacy2"), ("v3.1.3-legacy3", "results/oct_search/coding_legacy3")]
    litems, lgroups, ldef, lfr = [], {}, {}, {}
    for ver, folder in LEG:  # additional items of the figures and checklist (representative report of each study)
        I = json.load(open(f"tools/oct_search/coding/charms_items_{ver}.json"))
        for g, its in I["groups"].items():
            for i in its: litems.append(i); lgroups[i] = g; ldef[i] = I["items"][i]
        if os.path.exists(f"{folder}/final_items.jsonl"):
            for l in open(f"{folder}/final_items.jsonl"):
                r = json.loads(l)
                if r["record_id"] in st: st[r["record_id"]][r["item"]] = r["final"]
        if os.path.exists(f"{folder}/field_rules_decided.json"): lfr.update(json.load(open(f"{folder}/field_rules_decided.json")))
    REC = json.load(open("results/oct_search/legacy_fig/records.json"))["records"]
    TEXT = {"OUT02", "VI06", "POP03", "POP04"}  # printed text or numbers copied from the reports: private file only
    pkeys = sorted({k for x in REC.values() for k in x["protocol_items"] if not k.startswith("U:") and k not in TEXT})
    for r in D: D[r].update({f"fig_{k}": ";".join(v["value"] for v in REC.get(r, {}).get("protocol_items", {}).get(k, [])) for k in pkeys})
    reports = sorted(st)
    svars = [k for k in next(iter(D.values())) if k not in ("record_id", "study_id", "year")]  # publication year is given once (author review 2026-11-20)
    ven = venues(meta)
    studies = [[D[r]["study_id"], r, ";".join(sorted(l["record_id"] for l in links if l["study_id"] == D[r]["study_id"])), meta[r]["year"], ven[r]["first_author"], meta[r]["title"],
                ven[r]["venue"], ven[r]["type"], meta[r]["doi"], meta[r]["pmid"], meta[r]["kci_id"]]
               + [D[r][k] for k in svars] for r in sorted(D)]
    shead = ["study_id", "representative_report", "all_reports", "year", "first_author", "title", "journal_or_venue", "publication_type", "doi", "pmid", "kci_id"] + svars
    rep = [[r, sid[r], next(l["role"] for l in links if l["record_id"] == r), meta[r]["year"], meta[r]["title"], meta[r]["doi"]] for r in reports]
    items = items + litems; grp.update(lgroups)
    status = [[r, sid[r]] + [((st[r].get(i) or {}).get("status", "") + ("; inconsistency" if (st[r].get(i) or {}).get("inconsistency") == "present" else "")) for i in items] for r in reports]
    itemrows = [[g, i, ITEMS["items"][i]] for g, its in ITEMS["groups"].items() for i in its] + [[lgroups[i], i, ldef[i]] for i in litems] + [["general rule", f"rule {k}", t] for k, t in enumerate(ITEMS["general_rules"], 1)]
    frrows = [[f, v["cases"], {"agreed_r2": "agreed by both systems (round 2)", "agreed_r3": "agreed by both systems (round 3)", "decided_review": "no agreement; rule from review comments accepted by the author",
                               "decided_suggestion": "no agreement; suggested rule adopted under the author's direction"}.get(v["status"], v["status"]), v.get("rule") or ""] for f, v in sorted({**fr, **lfr}.items())]
    readme_pub = [
        ["KNHANES machine-learning review: Additional Data 1 (coding of 287 included reports of 279 studies)"],
        ["Studies: one row per study (representative report); study-level variables derived mechanically from the coded items (rules in Derivation) or classified by two AI systems (code, tool, domain, purpose; *_how = how settled); fig_* = coded categories used in the figures and tables (additional items, legacy.*; codes as in Items)."],
        ["Status: reporting status of each coded item for each report: reported | not_reported | unclear | not_applicable; '; inconsistency' = the report prints conflicting values for the same object."],
        ["Items: the coding items (CHARMS-based, version v3.1.3) and the general coding rules, as given to both coding systems. Items named legacy.* are the additional items coded for the representative report of each study to rebuild the figures and tables of the manuscript (variable importance, survey design, TRIPOD+AI-derived elements, PROBAST+AI, the 43 checklist items as legacy.checklist.C01-C43); they are used in the analyses, not a superseded coding."],
        ["Field_rules: rules settled for the items on which the two coding systems disagreed (see Methods)."],
        ["Coded values are not included because they contain text copied from the reports; they are held by the author."]]
    wb = Workbook(); ws = wb.active; ws.title = "README"
    for i, (t,) in enumerate(readme_pub, 1): ws.cell(i, 1, t)
    ws.column_dimensions["A"].width = 160
    sheet(wb, "Studies", shead, studies, {"title": 60})
    sheet(wb, "Status", ["record_id", "study_id"] + items, status)
    sheet(wb, "Items", ["group", "item", "definition"], itemrows, {"definition": 140, "item": 42})
    sheet(wb, "Field_rules", ["item", "cases", "how the rule was settled", "rule"], frrows, {"rule": 140, "item": 42})
    sheet(wb, "Derivation", der[0], der[1:], {"rule": 140, "item": 42, "variable": 30})
    for w in wb.worksheets[1:]:
        for col in w.iter_cols():
            for c in col: c.alignment = Alignment(wrap_text=False, vertical="top")
    wb.save("manuscript/KNHANES_ML_review_Additional_Data_1_oct.xlsx")
    # private
    coding = []
    for f_ in [f"{folder}/final_items.jsonl" for _, folder in LEG]:
        rows += [json.loads(l) for l in (open(f_) if os.path.exists(f_) else [])]
    for r in rows:
        x = r["final"] or {}
        base = [r["record_id"], sid[r["record_id"]], grp[r["item"]], r["item"], x.get("status", ""), x.get("inconsistency", ""), x.get("inconsistency_note", ""), route(r["how"]), ";".join(x.get("evidence_ids", []))]
        vs = x.get("values") or [{}]
        for v in vs: coding.append(base + [v.get("unit", ""), v.get("value", ""), v.get("kind", ""), v.get("value_full", ""), "yes" if v.get("short_failed") else ""])
    perf = [json.loads(l) for l in open(f"{C}/pilot_final/perf_rows_final.jsonl")] + [json.loads(l) for l in open(f"{C}/perf_rows_final.jsonl")]
    ph = ["record_id", "model", "outcome", "analysis", "dataset_role", "dataset_or_split", "subgroup", "metric", "value", "ci", "threshold", "evidence_id", "source"]
    wb = Workbook(); ws = wb.active; ws.title = "README"
    for i, t in enumerate(["PRIVATE working file: contains text copied from the reports (values, notes). Do not publish.",
                           "Coding: one row per coded value; value = short form (value_full = before shortening; short_failed = short form not accepted, full value kept)."] + [x[0] for x in readme_pub[1:5]], 1):
        ws.cell(i, 1, t)
    ws.column_dimensions["A"].width = 160
    sheet(wb, "Studies", shead, studies, {"title": 60})
    sheet(wb, "Reports", ["record_id", "study_id", "role", "year", "title", "doi"], rep, {"title": 60})
    sheet(wb, "Coding", ["record_id", "study_id", "group", "item", "status", "inconsistency", "inconsistency_note", "settled_by", "evidence_ids", "unit", "value", "kind", "value_full", "short_failed"],
          coding, {"value": 80, "value_full": 60, "unit": 30, "item": 36, "inconsistency_note": 40})
    sheet(wb, "Status", ["record_id", "study_id"] + items, status)
    sheet(wb, "Performance", ph, [[p.get(k, "") for k in ph] for p in perf], {"model": 24, "metric": 24, "dataset_or_split": 30})
    sheet(wb, "Items", ["group", "item", "definition"], itemrows, {"definition": 140, "item": 42})
    sheet(wb, "Field_rules", ["item", "cases", "how the rule was settled", "rule"], frrows, {"rule": 140, "item": 42})
    sheet(wb, "Derivation", der[0], der[1:], {"rule": 140, "item": 42, "variable": 30})
    wb.save(f"{C}/KNHANES_ML_coding_private.xlsx")
    print("studies", len(studies), "reports", len(rep), "coding rows", len(coding), "performance rows", len(perf))


if __name__ == "__main__":
    main()
