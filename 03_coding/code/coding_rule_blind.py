"""Round 6 of the data coding (2026-11-17, v3.1): blind rule check. In round 5 (coding_triage.py) 18 of 20 items that both
systems called RULE had each system siding with its own coding. Here every open item that at least one system called
RULE is shown again with the two codings anonymised as X and Y, their order swapped for half of the items (by a hash
of report and item, so the systems cannot tell which is their own), and only the rule question is asked: which coding
follows the coding rules and the item definition (X | Y | both_defensible), naming the rule. Both name the same coding
-> that coding (how = rule_blind_A/B); otherwise author. Output: rule_blind_calls.jsonl; final_items.jsonl and
author_queue.jsonl updated. Usage: coding_rule_blind.py [--workers N]"""
import concurrent.futures as cf, hashlib, json, os, sys, threading, collections
HERE = os.path.dirname(os.path.abspath(__file__)); ROOT = os.path.dirname(os.path.dirname(HERE)); sys.path.insert(0, HERE); os.chdir(ROOT)
import coding_run as RUN, coding_consensus as CS
OUT = os.environ.get("CODING_OUT", "results/oct_search/coding"); CALLS = f"{OUT}/rule_blind_calls.jsonl"; LOCK = threading.Lock(); ITEMS = RUN.ITEMS
SCHEMA = {"type": "object", "additionalProperties": False, "required": ["decisions"], "properties": {"decisions": {"type": "array", "items": {
    "type": "object", "additionalProperties": False, "required": ["item", "follows_rules", "rule", "reason"],
    "properties": {"item": {"type": "string"}, "follows_rules": {"type": "string", "enum": ["X", "Y", "both_defensible"]},
                   "rule": {"type": "string"}, "reason": {"type": "string"}}}}}}
PROMPT = """Two codings (X and Y) of items of a research report for a systematic review of machine-learning prediction studies
that use KNHANES differ in how the coding rules apply. For each item decide which coding follows the coding rules and
the item definition as written (X or Y); both_defensible only if the rules as written allow both. Apply the rules
literally; do not prefer either coding for its style. rule: the rule or item sentence that decides it. reason: one
sentence.

CODING RULES
{rules}

ITEMS
{items}

PRINTED TEXT OF THE CITED IDS
{evidence}"""


def swap(q): return int(hashlib.sha256((q["record_id"] + q["item"]).encode()).hexdigest(), 16) % 2 == 1


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


def neutral(a):  # drop wording that could identify the system (rationale kept: it carries the reading)
    return CS.show(a)


def one(key, qs):
    rid, group = key; T = CS.id_text(CS.CR.render(rid)); out = []
    for q in qs:
        x, y = (q["B"], q["A"]) if swap(q) else (q["A"], q["B"])
        out.append(f"- {q['item']}: {ITEMS['items'][q['item']]}\n  X: {neutral(x)}\n  Y: {neutral(y)}")
    ids = list(dict.fromkeys(i for q in qs for s in ("A", "B") for i in q[s]["evidence_ids"]))
    ev = "\n".join(f"[{i}] {T.get(i, '(ID not found in the report)')}" for i in ids)
    p = PROMPT.format(rules="\n".join(f"- {r}" for r in ITEMS["general_rules"]), items="\n".join(out), evidence=ev)
    with cf.ThreadPoolExecutor(2) as ex: a, b = ex.map(lambda w: ask(w, p, f"{rid}@ruleblind-{group}"), ("claude", "codex"))
    va = {d["item"]: d for d in (a or {}).get("decisions", [])}; vb = {d["item"]: d for d in (b or {}).get("decisions", [])}
    return {q["item"]: (va.get(q["item"]), vb.get(q["item"])) for q in qs}


def main():
    workers = int(sys.argv[sys.argv.index("--workers") + 1]) if "--workers" in sys.argv else 6
    Q = [json.loads(l) for l in open(f"{OUT}/author_queue.jsonl")]
    sel = [q for q in Q if any((t or {}).get("kind") == "RULE" for t in q.get("triage") or [])]
    groups = {}
    for q in sel: groups.setdefault((q["record_id"], q["group"]), []).append(q)
    print("rule items", len(sel), "groups", len(groups), flush=True)
    with cf.ThreadPoolExecutor(workers) as ex: res = dict(zip(groups, ex.map(lambda k: one(k, groups[k]), groups)))
    settled, left, sides = {}, [], collections.Counter()
    for q in Q:
        if q not in sel: left.append(q); continue
        a, b = res[(q["record_id"], q["group"])][q["item"]]
        m = {"X": "B" if swap(q) else "A", "Y": "A" if swap(q) else "B"}
        ca, cb = (m.get((a or {}).get("follows_rules")), m.get((b or {}).get("follows_rules")))
        q["rule_blind"] = [dict(a or {}, side=ca), dict(b or {}, side=cb)]; sides[(ca, cb)] += 1
        if ca and ca == cb: settled[(q["record_id"], q["item"])] = (q[ca], f"rule_blind_{ca}")
        else: left.append(q)
    rows = [json.loads(l) for l in open(f"{OUT}/final_items.jsonl")]
    for r in rows:
        k = (r["record_id"], r["item"])
        if r["how"] == "author" and k in settled: r["final"], r["how"] = settled[k]
    with open(f"{OUT}/final_items.jsonl", "w") as f:
        for r in rows: f.write(json.dumps(r, ensure_ascii=False) + "\n")
    with open(f"{OUT}/author_queue.jsonl", "w") as f:
        for q in left: f.write(json.dumps(q, ensure_ascii=False) + "\n")
    print("choices (claude side, codex side)", dict(sides), "settled", len(settled), "left for author", len(left), flush=True)


if __name__ == "__main__":
    main()
