"""Round-1 comparison of the two systems' data coding (coding_run.py output; data coding protocol r0).
Per report and item: status equal? values equal after mechanical normalisation (case, spaces, dashes, quotes,
trailing punctuation; units matched by normalised name, order ignored)? evidence IDs overlapping? Performance rows
matched by normalised (value, evidence_id), then by value alone.
Classes per item: AGREE (same status and same values, or both without values), STATUS_SAME_VALUES_DIFFER,
STATUS_DIFFER, MISSING (an answer lacks the item). Output: results/oct_search/coding/compare_r1.jsonl (one row per
report x item, both answers kept) and a summary printed. Mechanical only; nothing is decided here.
Usage: coding_compare.py [RID ...]"""
import collections, json, os, re, sys
HERE = os.path.dirname(os.path.abspath(__file__)); ROOT = os.path.dirname(os.path.dirname(HERE)); os.chdir(ROOT)
OUT = os.environ.get("CODING_OUT", "results/oct_search/coding"); ITEMS = json.load(open("tools/oct_search/coding/charms_items_" + os.environ.get("CODING_ITEMS", "v3.1.3") + ".json"))


def norm(s):
    s = (s or "").lower().replace("–", "-").replace("—", "-").replace("−", "-").replace("’", "'").replace("“", '"').replace("”", '"')
    s = re.sub(r"\s+", " ", s).strip()
    return re.sub(r"[\s.;,:]+$", "", s)


def vals(a):
    return sorted((norm(v["unit"]), norm(v["value"])) for v in a.get("values") or []) + [("~inconsistency", a.get("inconsistency") or "")]


def check_ids(best):
    """Evidence IDs must exist in the coding input (pilot review: cited IDs such as T04-H01-C02 were not
    found). IDs not in the input are removed from the answer and listed in invalid_evidence_ids."""
    import coding_render as CR, coding_consensus as CS
    cache = {}
    for (rid, g, w), A in best.items():
        if rid not in cache: cache[rid] = set(CS.id_text(CR.render(rid)))
        T = cache[rid]
        for x in A["items"]:
            bad = [i for i in x["evidence_ids"] if i not in T]
            if bad: x["evidence_ids"] = [i for i in x["evidence_ids"] if i in T]; x["invalid_evidence_ids"] = bad
        for r in A.get("performance_rows") or []:
            if r["evidence_id"] and r["evidence_id"] not in T: r["invalid_evidence_id"] = r["evidence_id"]


def latest():
    """Latest successful answer per (rid, group, assessor)."""
    best = {}
    for l in open(f"{OUT}/calls.jsonl"):
        r = json.loads(l)
        if r.get("answer") and r.get("items_version") == ITEMS["version"]: best[(r["record_id"], r["group"], r["assessor"])] = r["answer"]
    return best


def main():
    best = latest(); sys.path.insert(0, HERE); check_ids(best); want = [a for a in sys.argv[1:] if a.startswith("OCT")]
    rids = sorted({k[0] for k in best if not want or k[0] in want})
    rows, cnt, by_item, perf = [], collections.Counter(), collections.defaultdict(collections.Counter), collections.Counter()
    for rid in rids:
        for g, items in ITEMS["groups"].items():
            A, B = best.get((rid, g, "claude")), best.get((rid, g, "codex"))
            if not (A and B): cnt["group_missing"] += 1; continue
            ia = {x["item"]: x for x in A["items"]}; ib = {x["item"]: x for x in B["items"]}
            for it in items:
                a, b = ia.get(it), ib.get(it)
                if not (a and b): c = "MISSING"
                elif a["status"] != b["status"]: c = "STATUS_DIFFER"
                elif a["status"] in ("reported", "unclear") and not (a["evidence_ids"] and b["evidence_ids"]): c = "STATUS_SAME_VALUES_DIFFER"  # no valid evidence on a side
                elif vals(a) == vals(b): c = "AGREE"
                else: c = "STATUS_SAME_VALUES_DIFFER"
                ev = len(set(a["evidence_ids"]) & set(b["evidence_ids"])) if a and b else 0
                rows.append(dict(record_id=rid, group=g, item=it, cls=c, evidence_overlap=ev, claude=a, codex=b)); cnt[c] += 1; by_item[it][c] += 1
            if g == "D_performance":
                key = lambda r: (norm(r["value"]), r["evidence_id"].strip())
                ka = collections.Counter(map(key, A["performance_rows"])); kb = collections.Counter(map(key, B["performance_rows"]))
                both = sum((ka & kb).values()); perf["claude_rows"] += sum(ka.values()); perf["codex_rows"] += sum(kb.values()); perf["matched_value_and_id"] += both
                va = collections.Counter(k[0] for k in (ka - kb).elements()); vb = collections.Counter(k[0] for k in (kb - ka).elements())
                perf["matched_value_only"] += sum((va & vb).values())
    with open(f"{OUT}/compare_r1.jsonl", "w") as f:
        for r in rows: f.write(json.dumps(r, ensure_ascii=False) + "\n")
    n = sum(v for k, v in cnt.items() if k != "group_missing")
    print("reports", len(rids), "item rows", n, dict(cnt))
    print("performance rows", dict(perf))
    print("lowest agreement items:")
    for it, c in sorted(by_item.items(), key=lambda x: x[1]["AGREE"] / max(1, sum(x[1].values())))[:15]:
        print(f"  {it}: {dict(c)}")


if __name__ == "__main__":
    main()
