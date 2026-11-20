"""Round 2 of the data coding: consensus reading of the items on which the two round-1 codings differ (coding_compare.py,
2026-11-16). Free-text codings rarely match literally (unit names, granularity), so agreement is reached by choice,
not by string equality.
Per report and group, Claude and Codex each get (independently, text only, isolated calls) the item definitions, the
general rules, coding A (Claude round 1) and coding B (Codex round 1) of every differing item, and the printed text of
every ID cited by either (from coding_render.py, verbatim). For each item each system chooses:
  A      - A is correct and complete (also when both are correct and equally complete: A by convention);
  B      - B is correct and more complete than A;
  UNION  - both are correct but each has units/values the other lacks: the final answer is A's values plus B's values
           not in A (merged mechanically; status of A; evidence of both);
  NEITHER - both are wrong or the status is wrong in both (one sentence why) -> author.
Same choice by both -> final (how = consensus_A / consensus_B / consensus_UNION). Different choices -> one more round in
which each sees the other's choice and reason; still different -> author queue (QUESTIONS). Items AGREE in round 1
are final as A (values identical after normalisation).
Output: results/oct_search/coding/consensus_calls.jsonl (raw answers), final_items.jsonl (one row per report x item:
final answer, how, round-1/2 record), author_queue.jsonl.
Usage: coding_consensus.py [RID ...] [--workers N]"""
import collections, concurrent.futures as cf, hashlib, json, os, re, sys, threading
HERE = os.path.dirname(os.path.abspath(__file__)); ROOT = os.path.dirname(os.path.dirname(HERE)); sys.path.insert(0, HERE); os.chdir(ROOT)
import coding_render as CR, coding_run as RUN, coding_compare as CMP
OUT = os.environ.get("CODING_OUT", "results/oct_search/coding"); ITEMS = RUN.ITEMS; LOCK = threading.Lock(); CALLS = f"{OUT}/consensus_calls.jsonl"
CHOICES = ["A", "B", "UNION", "NEITHER"]
SCHEMA = {"type": "object", "additionalProperties": False, "required": ["decisions"], "properties": {"decisions": {"type": "array", "items": {
    "type": "object", "additionalProperties": False, "required": ["item", "choice", "reason"],
    "properties": {"item": {"type": "string"}, "choice": {"type": "string", "enum": CHOICES}, "reason": {"type": "string"}}}}}}
PROMPT = """Two reviewers (A and B) independently coded items of a research report for a systematic review of machine-learning
prediction studies that use KNHANES. Their codings of the items below differ. For each item decide which coding is
right, using the item definition, the coding rules and the printed text of the cited IDs (given verbatim below; IDs
in square brackets).

CODING RULES
{rules}

CHOICES (one per item)
- A: A is correct and complete. Also choose A when A and B say the same thing in different words or granularity and
  A is at least as complete.
- B: B is correct and more complete or more accurate than A.
- UNION: both are correct, but each contains units or values the other lacks; the final answer is A plus what only
  B has.
- NEITHER: both are wrong (wrong status, wrong value, or both miss what the cited text clearly states).
Unsupported inference is wrong: a number, procedure or timing not stated in the cited text cannot be correct.
Judge content, not wording: a value copied with more or less surrounding text is the same value. Prefer the coding
that gives printed numbers when the other gives none. reason: one sentence.
{round2}
ITEMS
{items}

PRINTED TEXT OF THE CITED IDS
{evidence}"""


def id_text(rendered):
    t = {}
    for l in rendered.split("\n"):
        m = re.match(r"\s*(?:## )?\[([^\]]+)\]\s?(.*)", l)
        if m and m.group(1) not in t: t[m.group(1)] = m.group(2)
    return t


def show(a):
    d = dict(status=a["status"], values=a["values"], value_kind=a.get("value_kind", "per value"), evidence_ids=a["evidence_ids"], rationale=a["rationale"])
    if "inconsistency" in a: d.update(inconsistency=a["inconsistency"], inconsistency_note=a.get("inconsistency_note", ""))
    return json.dumps(d, ensure_ascii=False)


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


def union(a, b):
    seen = {(CMP.norm(v["unit"]), CMP.norm(v["value"])) for v in a["values"]}
    vals = a["values"] + [v for v in b["values"] if (CMP.norm(v["unit"]), CMP.norm(v["value"])) not in seen]
    return dict(a, values=vals, evidence_ids=list(dict.fromkeys(a["evidence_ids"] + b["evidence_ids"])),
                rationale=a["rationale"] + " | " + b["rationale"])


def one(rid, group, rows):
    rend = CR.render(rid); T = id_text(rend)
    defs = {r["item"]: ITEMS["items"][r["item"]] for r in rows}
    def items_block(extra=None):
        out = []
        for r in rows:
            s = f"- {r['item']}: {defs[r['item']]}\n  A: {show(r['claude'])}\n  B: {show(r['codex'])}"
            if extra and r["item"] in extra: s += "\n  " + extra[r["item"]]
            out.append(s)
        return "\n".join(out)
    ids = list(dict.fromkeys(i for r in rows for w in ("claude", "codex") for i in r[w]["evidence_ids"]))
    ev = "\n".join(f"[{i}] {T[i]}" if i in T else f"[{i}] (ID not found in the report)" for i in ids)
    rules = "\n".join(f"- {x}" for x in ITEMS["general_rules"])
    p1 = PROMPT.format(rules=rules, round2="", items=items_block(), evidence=ev)
    with cf.ThreadPoolExecutor(2) as ex: da, db = ex.map(lambda w: ask(w, p1, f"{rid}@cons1-{group}"), ("claude", "codex"))
    res = {}
    if not (da and db): return {r["item"]: dict(how="author:missing_answer", r1=None, author=True, choice=None) for r in rows}
    ca = {d["item"]: d for d in da["decisions"]}; cb = {d["item"]: d for d in db["decisions"]}
    diff = [r for r in rows if not (ca.get(r["item"]) and cb.get(r["item"]) and ca[r["item"]]["choice"] == cb[r["item"]]["choice"])]
    for r in rows:
        if r not in diff: res[r["item"]] = dict(choice=ca[r["item"]]["choice"], round=1, reasons=[ca[r["item"]]["reason"], cb[r["item"]]["reason"]])
    if diff:
        rows2 = diff
        extra = {r["item"]: f"Earlier choices: reviewer 1 chose {ca.get(r['item'], {}).get('choice')} ({ca.get(r['item'], {}).get('reason')}); "
                             f"reviewer 2 chose {cb.get(r['item'], {}).get('choice')} ({cb.get(r['item'], {}).get('reason')})." for r in rows2}
        rows_b = rows; rows = rows2
        p2 = PROMPT.format(rules=rules, round2="\nThis is a second look: two reviewers chose differently before; their choices and reasons are shown. "
                           "Decide again on the evidence.\n", items=items_block(extra), evidence=ev)
        rows = rows_b
        with cf.ThreadPoolExecutor(2) as ex: xa, xb = ex.map(lambda w: ask(w, p2, f"{rid}@cons2-{group}"), ("claude", "codex"))
        xa = {d["item"]: d for d in (xa or {}).get("decisions", [])}; xb = {d["item"]: d for d in (xb or {}).get("decisions", [])}
        for r in rows2:
            i = r["item"]
            if xa.get(i) and xb.get(i) and xa[i]["choice"] == xb[i]["choice"] and xa[i]["choice"] != "NEITHER":
                res[i] = dict(choice=xa[i]["choice"], round=2, reasons=[xa[i]["reason"], xb[i]["reason"]])
            else:
                res[i] = dict(choice=None, round=2, author=True, choices=[(ca.get(i) or {}).get("choice"), (cb.get(i) or {}).get("choice"),
                              (xa.get(i) or {}).get("choice"), (xb.get(i) or {}).get("choice")],
                              reasons=[(xa.get(i) or {}).get("reason"), (xb.get(i) or {}).get("reason")])
    for i, v in res.items():
        if v.get("choice") == "NEITHER": v["author"] = True
    return res


def main():
    want = [a for a in sys.argv[1:] if a.startswith("OCT")]
    workers = int(sys.argv[sys.argv.index("--workers") + 1]) if "--workers" in sys.argv else 6
    rows = [json.loads(l) for l in open(f"{OUT}/compare_r1.jsonl")]
    rows = [r for r in rows if not want or r["record_id"] in want]
    todo = collections.defaultdict(list)
    for r in rows:
        if r["cls"] in ("STATUS_DIFFER", "STATUS_SAME_VALUES_DIFFER"): todo[(r["record_id"], r["group"])].append(r)
    print("groups to reconcile", len(todo), "items", sum(map(len, todo.values())), flush=True)
    with cf.ThreadPoolExecutor(workers) as ex: out = dict(zip(todo, ex.map(lambda k: one(k[0], k[1], todo[k]), todo)))
    final, queue, cnt = [], [], collections.Counter()
    for r in rows:
        a, b = r["claude"], r["codex"]
        if r["cls"] == "AGREE": fin, how = a, "agree_r1"
        elif r["cls"] == "MISSING": fin, how = (a or b), "one_side_only"
        else:
            d = out[(r["record_id"], r["group"])].get(r["item"]) or dict(author=True, choice=None)
            if d.get("author"):
                fin, how = None, "author"; queue.append(dict(record_id=r["record_id"], group=r["group"], item=r["item"], A=a, B=b, consensus=d))
            else:
                fin = {"A": a, "B": b, "UNION": union(a, b) if a and b else (a or b)}[d["choice"]]; how = f"consensus_r{d['round']}_{d['choice']}"
        cnt[how if not how.startswith("consensus") else how] += 1
        final.append(dict(record_id=r["record_id"], group=r["group"], item=r["item"], final=fin, how=how, r1_class=r["cls"]))
    with open(f"{OUT}/final_items.jsonl", "w") as f:
        for x in final: f.write(json.dumps(x, ensure_ascii=False) + "\n")
    with open(f"{OUT}/author_queue.jsonl", "w") as f:
        for x in queue: f.write(json.dumps(x, ensure_ascii=False) + "\n")
    print("final", len(final), dict(sorted(cnt.items())), "author", len(queue), flush=True)


if __name__ == "__main__":
    main()
