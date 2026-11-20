"""Round 3 of the data coding (2026-11-16): materiality of the differences still open after the consensus rounds
(coding_consensus.py author_queue.jsonl). Pilot v2: 99 of 131 open items were each system choosing its own coding in
both rounds over wording or granularity. Each system (independently, text only) is asked per item only whether the
difference is MATERIAL - a reader of the review table would take a different fact from A than from B (different
status, a different number, a different category, something present in one and wrong in the other) - or
NOT_MATERIAL (wording, quoting length, level of detail, unit labels, extra correct detail on one side).
Both NOT_MATERIAL -> settled by rule (structure, not content): the side with more printed numbers in its values,
then more value entries, then A ("number present on one side only -> that side"; author rule for low-importance
items); how = rule_not_material_A/B. Otherwise -> author. Output: material_calls.jsonl, final_items.jsonl updated in
place (rows with how == "author" that are settled), author_queue.jsonl rewritten with what is left.
Usage: coding_material.py [--workers N]"""
import concurrent.futures as cf, hashlib, json, os, re, sys, threading
HERE = os.path.dirname(os.path.abspath(__file__)); ROOT = os.path.dirname(os.path.dirname(HERE)); sys.path.insert(0, HERE); os.chdir(ROOT)
import coding_run as RUN, coding_consensus as CS
OUT = os.environ.get("CODING_OUT", "results/oct_search/coding"); CALLS = f"{OUT}/material_calls.jsonl"; LOCK = threading.Lock(); ITEMS = RUN.ITEMS
SCHEMA = {"type": "object", "additionalProperties": False, "required": ["decisions"], "properties": {"decisions": {"type": "array", "items": {
    "type": "object", "additionalProperties": False, "required": ["item", "verdict", "reason"],
    "properties": {"item": {"type": "string"}, "verdict": {"type": "string", "enum": ["MATERIAL", "NOT_MATERIAL"]}, "reason": {"type": "string"}}}}}}
PROMPT = """Two reviewers (A and B) coded items of a research report for a systematic review of machine-learning prediction studies
that use KNHANES. For the items below they still differ. Do not choose a side. Decide only whether the difference is
MATERIAL: a reader of the review's data table would take a different fact from A than from B - a different status
(e.g. reported vs not_reported vs not_applicable), a different number, a different category or label, or something
stated in one that is wrong or absent from the report. NOT_MATERIAL: the same facts in different wording, longer or
shorter quotation, more or less detail or splitting into units, or one side adds correct extra detail the other
leaves out without contradicting it. Use the printed text of the cited IDs. reason: one sentence naming the
difference.

ITEMS
{items}

PRINTED TEXT OF THE CITED IDS
{evidence}"""


def nums(a): return len(re.findall(r"\d+(?:\.\d+)?", " ".join(v["value"] for v in (a or {}).get("values") or [])))


def ask(who, prompt, tag):
    ps = hashlib.sha256(prompt.encode()).hexdigest()
    if os.path.exists(CALLS):
        for l in open(CALLS):
            r = json.loads(l)
            if r["tag"] == tag and r["assessor"] == who and r["prompt_sha256"] == ps and r.get("answer"): return r["answer"]
    res, err, meta = RUN.text_call(who, prompt, SCHEMA, tag)
    ok = res is not None and isinstance(res.get("decisions"), list)
    with LOCK, open(CALLS, "a") as f: f.write(json.dumps(dict(tag=tag, assessor=who, prompt_sha256=ps, answer=res if ok else None, error=None if ok else err, call=meta), ensure_ascii=False) + "\n")
    return res if ok else None


def one(key, qs):
    rid, group = key; T = CS.id_text(CS.CR.render(rid))
    items = "\n".join(f"- {q['item']}: {ITEMS['items'][q['item']]}\n  A: {CS.show(q['A'])}\n  B: {CS.show(q['B'])}" for q in qs)
    ids = list(dict.fromkeys(i for q in qs for s in ("A", "B") for i in q[s]["evidence_ids"]))
    ev = "\n".join(f"[{i}] {T.get(i, '(ID not found in the report)')}" for i in ids)
    p = PROMPT.format(items=items, evidence=ev)
    with cf.ThreadPoolExecutor(2) as ex: a, b = ex.map(lambda w: ask(w, p, f"{rid}@material-{group}"), ("claude", "codex"))
    va = {d["item"]: d for d in (a or {}).get("decisions", [])}; vb = {d["item"]: d for d in (b or {}).get("decisions", [])}
    return {q["item"]: (va.get(q["item"]), vb.get(q["item"])) for q in qs}


def main():
    workers = int(sys.argv[sys.argv.index("--workers") + 1]) if "--workers" in sys.argv else 6
    Q = [json.loads(l) for l in open(f"{OUT}/author_queue.jsonl")]
    Q = [q for q in Q if q.get("A") and q.get("B")]
    groups = {}
    for q in Q: groups.setdefault((q["record_id"], q["group"]), []).append(q)
    print("open items", len(Q), "groups", len(groups), flush=True)
    with cf.ThreadPoolExecutor(workers) as ex: res = dict(zip(groups, ex.map(lambda k: one(k, groups[k]), groups)))
    settled, left = {}, []
    for q in Q:
        a, b = res[(q["record_id"], q["group"])][q["item"]]
        q["material"] = [a, b]
        if a and b and a["verdict"] == b["verdict"] == "NOT_MATERIAL":
            side = "A" if (nums(q["A"]), len(q["A"]["values"])) >= (nums(q["B"]), len(q["B"]["values"])) else "B"
            settled[(q["record_id"], q["item"])] = (q[side], f"rule_not_material_{side}")
        else: left.append(q)
    rows = [json.loads(l) for l in open(f"{OUT}/final_items.jsonl")]
    for r in rows:
        k = (r["record_id"], r["item"])
        if r["how"] == "author" and k in settled: r["final"], r["how"] = settled[k]
    with open(f"{OUT}/final_items.jsonl", "w") as f:
        for r in rows: f.write(json.dumps(r, ensure_ascii=False) + "\n")
    with open(f"{OUT}/author_queue.jsonl", "w") as f:
        for q in left: f.write(json.dumps(q, ensure_ascii=False) + "\n")
    print("settled not material", len(settled), "left for author", len(left), flush=True)


if __name__ == "__main__":
    main()
