"""Round 5 of the data coding (v3.1; internal review note: settle formal and rule-level differences by rule, send
only substantive ones to the author). Each item still open after rounds 2-4 is classified by Claude and Codex,
independently (text only), with the coding rules, both codings and the printed text of the cited IDs:
  FORM        - the same facts in another form (unit split or grouped, wording, quotation length, extra correct detail);
  RULE        - the difference is how a coding rule or the item definition applies, and the rule text decides it:
                rule_side = the coding that follows the rule (A or B), naming the rule;
  SUBSTANTIVE - the codings take a different fact from the report (what was done, which data, which number), and the
                rules do not decide it: the author reads the report.
Settlement: both FORM -> side with more printed numbers, then more value entries, then A (as coding_material.py);
both RULE with the same rule_side -> that side; otherwise author (triage labels kept for the author file).
how = triage_form_A/B, triage_rule_A/B. Output: triage_calls.jsonl; final_items.jsonl and author_queue.jsonl updated.
Usage: coding_triage.py [--workers N]"""
import concurrent.futures as cf, hashlib, json, os, sys, threading
HERE = os.path.dirname(os.path.abspath(__file__)); ROOT = os.path.dirname(os.path.dirname(HERE)); sys.path.insert(0, HERE); os.chdir(ROOT)
import coding_run as RUN, coding_consensus as CS, coding_material as MAT
OUT = os.environ.get("CODING_OUT", "results/oct_search/coding"); CALLS = f"{OUT}/triage_calls.jsonl"; LOCK = threading.Lock(); ITEMS = RUN.ITEMS
SCHEMA = {"type": "object", "additionalProperties": False, "required": ["decisions"], "properties": {"decisions": {"type": "array", "items": {
    "type": "object", "additionalProperties": False, "required": ["item", "kind", "rule_side", "reason"],
    "properties": {"item": {"type": "string"}, "kind": {"type": "string", "enum": ["FORM", "RULE", "SUBSTANTIVE"]},
                   "rule_side": {"type": "string", "enum": ["A", "B", "none"]}, "reason": {"type": "string"}}}}}}
PROMPT = """Two reviewers (A and B) coded items of a research report for a systematic review of machine-learning prediction studies
that use KNHANES. For the items below they still differ after discussion. Do not re-argue; classify the difference.
- FORM: both give the same facts in a different form: units split differently or grouped ('all models' vs one entry
  per model), wording, quotation length, or one adds correct detail the other leaves out without contradicting it.
  rule_side none.
- RULE: the difference is how a coding rule or the item definition applies (status choice such as not_applicable vs
  not_reported, whether a partial detail makes the item reported, unit form, version scope, unsupported inference),
  and the rule text below decides it. rule_side = the coding that follows the rule (A or B). Name the rule in reason.
- SUBSTANTIVE: the two codings take a different fact from the report (what was done, on which data, which number,
  whether two places contradict) and the rules do not decide it; only reading the report can. rule_side none.
reason: one sentence.

CODING RULES
{rules}

ITEMS
{items}

PRINTED TEXT OF THE CITED IDS
{evidence}"""


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
    p = PROMPT.format(rules="\n".join(f"- {x}" for x in ITEMS["general_rules"]), items=items, evidence=ev)
    with cf.ThreadPoolExecutor(2) as ex: a, b = ex.map(lambda w: ask(w, p, f"{rid}@triage-{group}"), ("claude", "codex"))
    va = {d["item"]: d for d in (a or {}).get("decisions", [])}; vb = {d["item"]: d for d in (b or {}).get("decisions", [])}
    return {q["item"]: (va.get(q["item"]), vb.get(q["item"])) for q in qs}


def main():
    workers = int(sys.argv[sys.argv.index("--workers") + 1]) if "--workers" in sys.argv else 6
    Q = [json.loads(l) for l in open(f"{OUT}/author_queue.jsonl")]
    groups = {}
    for q in Q:
        if q.get("A") and q.get("B"): groups.setdefault((q["record_id"], q["group"]), []).append(q)
    print("open items", len(Q), "groups", len(groups), flush=True)
    with cf.ThreadPoolExecutor(workers) as ex: res = dict(zip(groups, ex.map(lambda k: one(k, groups[k]), groups)))
    settled, left = {}, []
    for q in Q:
        a, b = res.get((q["record_id"], q["group"]), {}).get(q["item"], (None, None)); q["triage"] = [a, b]
        if a and b and a["kind"] == b["kind"] == "FORM":
            side = "A" if (MAT.nums(q["A"]), len(q["A"]["values"])) >= (MAT.nums(q["B"]), len(q["B"]["values"])) else "B"
            settled[(q["record_id"], q["item"])] = (q[side], f"triage_form_{side}")
        elif a and b and a["kind"] == b["kind"] == "RULE" and a["rule_side"] == b["rule_side"] in ("A", "B"):
            settled[(q["record_id"], q["item"])] = (q[a["rule_side"]], f"triage_rule_{a['rule_side']}")
        else: left.append(q)
    rows = [json.loads(l) for l in open(f"{OUT}/final_items.jsonl")]
    for r in rows:
        k = (r["record_id"], r["item"])
        if r["how"] == "author" and k in settled: r["final"], r["how"] = settled[k]
    with open(f"{OUT}/final_items.jsonl", "w") as f:
        for r in rows: f.write(json.dumps(r, ensure_ascii=False) + "\n")
    with open(f"{OUT}/author_queue.jsonl", "w") as f:
        for q in left: f.write(json.dumps(q, ensure_ascii=False) + "\n")
    import collections
    print("settled", len(settled), collections.Counter(v[1] for v in settled.values()), "left for author", len(left),
          collections.Counter(tuple(sorted(((x or {}).get("kind") or "-") for x in q["triage"])) for q in left), flush=True)


if __name__ == "__main__":
    main()
