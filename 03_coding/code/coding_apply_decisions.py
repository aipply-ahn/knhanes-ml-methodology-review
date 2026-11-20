"""Apply decisions on the open data-coding items (2026-11-17). Sources, in order of precedence: the author's own decisions
from the app (author_decisions.jsonl: A | B | neither, latest per item) over the decisions adopted from the external
review (review_internal review note.json, forwarded by the author with 'apply it').
  A / B        -> final = that coding (how = decision_A/B; author_A/B for the author's own);
  APPLY        -> the decision says how to combine or correct the two codings (merge, 'closer to B', corrections):
                  Codex writes the final coding (item schema of the frozen rules, text only) from coding A, coding B,
                  the instruction, the coding rules and the printed text of the cited IDs; Claude checks it
                  independently (ok | problem). ok -> final (how = decision_apply); problem -> one revision by Codex with the problem shown, checked
                  again; still a problem -> stays open for the author.
  APPLY_FINAL  -> the same, correcting an item that was already final (e.g. an inconsistency flag the review rejected).
Raw calls: apply_calls.jsonl. final_items.jsonl and author_queue.jsonl updated; decisions_applied.jsonl lists each
decision with its outcome. Usage: coding_apply_decisions.py [--workers N]"""
import concurrent.futures as cf, hashlib, json, os, sys, threading
HERE = os.path.dirname(os.path.abspath(__file__)); ROOT = os.path.dirname(os.path.dirname(HERE)); sys.path.insert(0, HERE); os.chdir(ROOT)
import coding_run as RUN, coding_consensus as CS
C = os.environ.get("CODING_OUT", "results/oct_search/coding"); CALLS = f"{C}/apply_calls.jsonl"; LOCK = threading.Lock(); ITEMS = RUN.ITEMS
CHECK = {"type": "object", "additionalProperties": False, "required": ["verdict", "problem"], "properties": {
    "verdict": {"type": "string", "enum": ["ok", "problem"]}, "problem": {"type": "string"}}}
WRITE = """You finalise one coded item of a research report for a systematic review of machine-learning prediction studies that
use KNHANES. Two reviewers coded it (A and B); a decision says how the final coding should be made from them. Write the
final coding of this item following the decision, the coding rules and the printed text of the cited IDs: keep what the
decision keeps, correct what it corrects, add nothing the cited text does not state. Cite only IDs listed below.

CODING RULES
{rules}

ITEM
{item}: {definition}

CODING A
{a}

CODING B
{b}

DECISION
{instruction}

PRINTED TEXT OF THE CITED IDS
{evidence}"""
VERIFY = """Check a finalised coded item of a research report (systematic review of machine-learning prediction studies using
KNHANES). The final coding was written from codings A and B following the decision below. Answer ok if the final coding
follows the decision and the coding rules and states nothing that the printed text of the cited IDs does not support;
otherwise problem, naming it in one sentence (problem '' when ok).

CODING RULES
{rules}

ITEM
{item}: {definition}

CODING A
{a}

CODING B
{b}

DECISION
{instruction}

FINAL CODING
{final}

PRINTED TEXT OF THE CITED IDS
{evidence}"""


def ask(who, prompt, sch, tag):
    ps = hashlib.sha256(prompt.encode()).hexdigest()
    if os.path.exists(CALLS):
        for l in open(CALLS):
            r = json.loads(l)
            if r["tag"] == tag and r["assessor"] == who and r["prompt_sha256"] == ps and r.get("answer"): return r["answer"]
    res, err, meta = RUN.text_call(who, prompt, sch, tag)
    with LOCK, open(CALLS, "a") as f: f.write(json.dumps(dict(tag=tag, assessor=who, prompt_sha256=ps, answer=res, error=err, call=meta), ensure_ascii=False) + "\n")
    return res


def apply_one(d, a, b, group):
    T = CS.id_text(CS.CR.render(d["record_id"]))
    ids = list(dict.fromkeys(i for x in (a, b) if x for i in x["evidence_ids"]))
    ev = "\n".join(f"[{i}] {T.get(i, '(ID not found in the report)')}" for i in ids)
    kw = dict(rules="\n".join(f"- {r}" for r in ITEMS["general_rules"]), item=d["item"], definition=ITEMS["items"][d["item"]],
              a=CS.show(a) if a else "(none)", b=CS.show(b) if b else "(none)", instruction=d["instruction"], evidence=ev)
    sch = RUN.schema(group)["properties"]["items"]["items"]
    tag = f"{d['record_id']}@apply-{d['item']}"
    fin = ask("codex", WRITE.format(**kw), sch, tag)
    if not fin: return None, "write failed"
    bad = [i for i in fin["evidence_ids"] if i not in T]
    if bad: fin["evidence_ids"] = [i for i in fin["evidence_ids"] if i in T]; fin["invalid_evidence_ids"] = bad
    chk = ask("claude", VERIFY.format(final=CS.show(fin), **kw), CHECK, tag + "-check")
    if not chk: return None, "check failed"
    if chk["verdict"] == "ok": return fin, ""
    # one revision: the writer sees its draft and the checker's problem, the checker checks the revision
    kw2 = dict(kw, instruction=kw["instruction"] + "\nA checker found a problem in an earlier draft (" + CS.show(fin) + "): " + chk["problem"] + " Fix it.")
    fin = ask("codex", WRITE.format(**kw2), sch, tag + "-rev")
    if not fin: return None, "revision failed: " + chk["problem"]
    fin["evidence_ids"] = [i for i in fin["evidence_ids"] if i in T]
    chk2 = ask("claude", VERIFY.format(final=CS.show(fin), **kw), CHECK, tag + "-check2")
    if not chk2: return None, "check failed"
    return (fin, "") if chk2["verdict"] == "ok" else (None, chk2["problem"])


def main():
    workers = int(sys.argv[sys.argv.index("--workers") + 1]) if "--workers" in sys.argv else 6
    Q = {(q["record_id"], q["item"]): q for q in map(json.loads, open(f"{C}/author_queue.jsonl"))}
    rows = [json.loads(l) for l in open(f"{C}/final_items.jsonl")]; R = {(r["record_id"], r["item"]): r for r in rows}
    dec = {(d["record_id"], d["item"]): d for d in json.load(open(f"{C}/review_internal review note.json"))}
    if os.path.exists(f"{C}/author_decisions.jsonl"):
        for l in open(f"{C}/author_decisions.jsonl"):
            x = json.loads(l); k = (x["record_id"], x["item"])
            dec[k] = dict(record_id=k[0], item=k[1], decision={"A": "A", "B": "B"}.get(x["decision"], "NEITHER"), instruction=x.get("memo", ""), source="author")
    jobs, log = [], []
    for k, d in dec.items():
        q, r = Q.get(k), R[k]
        if d["decision"] in ("A", "B") and q:
            r["final"], r["how"] = q[d["decision"]], ("author_" if d["source"] == "author" else "decision_") + d["decision"]; log.append(dict(d, outcome=r["how"]))
        elif d["decision"] in ("APPLY", "SET") and q: jobs.append((d, q["A"], q["B"], r))
        elif d["decision"] == "APPLY_FINAL" and r["final"]: jobs.append((d, r["final"], None, r))
        else: log.append(dict(d, outcome="open"))
    print("direct", len(log), "apply", len(jobs), flush=True)
    with cf.ThreadPoolExecutor(workers) as ex: res = list(ex.map(lambda j: apply_one(j[0], j[1], j[2], j[3]["group"]), jobs))
    for (d, a, b, r), (fin, prob) in zip(jobs, res):
        if fin: r["final"], r["how"] = fin, "decision_apply"; log.append(dict(d, outcome="applied"))
        else: log.append(dict(d, outcome="open", problem=prob))
    left = [q for k, q in Q.items() if R[k]["how"] == "author" or not R[k]["final"]]
    for r in rows:
        if not r["final"]: r["how"] = "author"
    with open(f"{C}/final_items.jsonl", "w") as f:
        for r in rows: f.write(json.dumps(r, ensure_ascii=False) + "\n")
    with open(f"{C}/author_queue.jsonl", "w") as f:
        for q in left: f.write(json.dumps(q, ensure_ascii=False) + "\n")
    with open(f"{C}/decisions_applied.jsonl", "w") as f:
        for x in log: f.write(json.dumps(x, ensure_ascii=False) + "\n")
    import collections
    print("outcomes", dict(collections.Counter(x["outcome"] for x in log)), "left for author", len(left), flush=True)
    for x in log:
        if x["outcome"] == "open": print("  open:", x["record_id"], x["item"], x.get("problem", "")[:200])


if __name__ == "__main__":
    main()
