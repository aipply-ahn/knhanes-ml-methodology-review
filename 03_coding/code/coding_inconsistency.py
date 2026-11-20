"""Round 4 of the data coding (2026-11-16, v3): items still open only because one coding flags an internal inconsistency
and the other does not (same status; values otherwise the same item answer). Choosing a side failed there (each system
kept its own flag), so each system is asked a narrower factual question, independently: do the places named in the
flagging note (printed text of the cited IDs given) contradict each other about the same fact, object and condition?
present | none | uncertain (rules of charms_items_v3: notation and rounding are not inconsistencies). Both give the same
verdict -> final = the side whose inconsistency equals it (how = verify_inconsistency_A/B); else author.
Output: inconsistency_calls.jsonl; final_items.jsonl and author_queue.jsonl updated. Usage: coding_inconsistency.py"""
import concurrent.futures as cf, hashlib, json, os, sys, threading
HERE = os.path.dirname(os.path.abspath(__file__)); ROOT = os.path.dirname(os.path.dirname(HERE)); sys.path.insert(0, HERE); os.chdir(ROOT)
import coding_run as RUN, coding_consensus as CS
OUT = os.environ.get("CODING_OUT", "results/oct_search/coding"); CALLS = f"{OUT}/inconsistency_calls.jsonl"; LOCK = threading.Lock()
SCHEMA = {"type": "object", "additionalProperties": False, "required": ["verdict", "reason"], "properties": {
    "verdict": {"type": "string", "enum": ["present", "none", "uncertain"]}, "reason": {"type": "string"}}}
PROMPT = """A reviewer coding a research report noted a possible internal inconsistency for the item below. Check it against the
printed text of the cited IDs. Answer present only if two places of the report give contradictory information about
the same fact, object and condition (e.g. different confidence intervals for the same model and dataset; the same split
called training in one place and test in another). Differences of notation (> vs >=), rounding (0.8948 vs 0.895),
or places that may refer to different objects (another model, another subgroup, another analysis) are not present:
answer none if they clearly are not contradictory, uncertain if the text does not allow telling whether they refer to
the same object. Text that the input marks as another version of the report or as submission-system material (e.g. an
'Original Manuscript' block with an earlier abstract in a preprint server PDF, an earlier preprint version) is not part
of the coded report: a difference between it and the main text is none. reason: one sentence.

ITEM: {item}: {definition}
NOTE OF THE REVIEWER: {note}

PRINTED TEXT OF THE CITED IDS
{evidence}"""


def ask(who, prompt, tag):
    ps = hashlib.sha256(prompt.encode()).hexdigest()
    if os.path.exists(CALLS):
        for l in open(CALLS):
            r = json.loads(l)
            if r["tag"] == tag and r["assessor"] == who and r["prompt_sha256"] == ps and r.get("answer"): return r["answer"]
    res, err, meta = RUN.text_call(who, prompt, SCHEMA, tag)
    with LOCK, open(CALLS, "a") as f: f.write(json.dumps(dict(tag=tag, assessor=who, prompt_sha256=ps, answer=res, error=err, call=meta), ensure_ascii=False) + "\n")
    return res


def one(q):
    A, B = q["A"], q["B"]; flag = A if A.get("inconsistency") != "none" else B
    T = CS.id_text(CS.CR.render(q["record_id"]))
    ids = list(dict.fromkeys(A["evidence_ids"] + B["evidence_ids"]))
    p = PROMPT.format(item=q["item"], definition=RUN.ITEMS["items"][q["item"]], note=flag.get("inconsistency_note") or flag.get("rationale"),
                      evidence="\n".join(f"[{i}] {T.get(i, '(ID not found)')}" for i in ids))
    with cf.ThreadPoolExecutor(2) as ex: a, b = ex.map(lambda w: ask(w, p, f"{q['record_id']}@inconsistency-{q['item']}"), ("claude", "codex"))
    return a, b


def main():
    Q = [json.loads(l) for l in open(f"{OUT}/author_queue.jsonl")]
    todo = [q for q in Q if q["A"]["status"] == q["B"]["status"] and q["A"].get("inconsistency") != q["B"].get("inconsistency")]
    print("inconsistency-only items", len(todo), flush=True)
    with cf.ThreadPoolExecutor(6) as ex: res = list(ex.map(one, todo))
    settled = {}
    for q, (a, b) in zip(todo, res):
        q["inconsistency_check"] = [a, b]
        if a and b and a["verdict"] == b["verdict"]:
            side = next((s for s in ("A", "B") if q[s].get("inconsistency") == a["verdict"]), None)
            if side: settled[(q["record_id"], q["item"])] = (q[side], f"verify_inconsistency_{side}")
    rows = [json.loads(l) for l in open(f"{OUT}/final_items.jsonl")]
    for r in rows:
        k = (r["record_id"], r["item"])
        if r["how"] == "author" and k in settled: r["final"], r["how"] = settled[k]
    with open(f"{OUT}/final_items.jsonl", "w") as f:
        for r in rows: f.write(json.dumps(r, ensure_ascii=False) + "\n")
    left = [q for q in Q if (q["record_id"], q["item"]) not in settled]
    with open(f"{OUT}/author_queue.jsonl", "w") as f:
        for q in left: f.write(json.dumps(q, ensure_ascii=False) + "\n")
    print("settled", len(settled), "left for author", len(left), flush=True)


if __name__ == "__main__":
    main()
