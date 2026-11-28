"""Rule decisions for the fields without an agreed rule, and re-application to all open cases (internal review note, external review forwarded by the author with 'apply it').
Rules: for each field without agreement (field_rules.json status no_agreement) the decision is the review's (file
review_internal review note.json) or else the suggested answer of the rule question (field_questions_ko.json,
'adopt the suggested answers by default, checking that they do not contradict the coding definitions'). Codex writes the field rule in Occam form - a core rule of one or
two sentences plus at most two short exceptions, general terms, no exception made for a single report - from the
decision, rules P and Q, the item definition and the general rules; Claude checks it (follows the decision, does not
contradict the item definition or the general rules, short); one revision; still a problem -> rule question for the author.
Application: every open case (author_queue.jsonl) of a field with a rule (agreed or decided) is judged as in
coding_field_rules.apply_case (each coding on its own under the rule; same calls reused). Cases left split or
'insufficient' are no longer sent to the author on that ground: the review found that many were the rule not carried
through. Codex writes the coding under the rule (the judgements of both systems shown; unclear / not_reported where the
printed text does not settle it), Claude checks it, one revision (coding_apply_decisions.apply_one). Only codings
not accepted after the revision stay for the author.
Output: field_decide_calls.jsonl (raw), field_rules_decided.json, field_decide_applied.jsonl, final_items.jsonl /
author_queue.jsonl updated (inputs kept as *_before_field_decide.jsonl). Usage: coding_field_decide.py [--workers N]"""
import collections, concurrent.futures as cf, json, os, shutil, sys
HERE = os.path.dirname(os.path.abspath(__file__)); ROOT = os.path.dirname(os.path.dirname(HERE)); sys.path.insert(0, HERE); os.chdir(ROOT)
import coding_run as RUN, coding_field_rules as FRM, coding_apply_decisions as AP
C = os.environ.get("CODING_OUT", "results/oct_search/coding"); ITEMS = RUN.ITEMS
FRM.CALLS = AP.CALLS = f"{C}/field_decide_calls.jsonl"
FRM._cache = {}  # answers of the field-rule stage are reused (same tag, assessor and prompt), new calls go to the new file
for _f in (f"{C}/field_rules_calls.jsonl", FRM.CALLS):
    if os.path.exists(_f):
        for _l in open(_f):
            _r = json.loads(_l)
            if _r.get("answer"): FRM._cache[(_r["tag"], _r["assessor"], _r["prompt_sha256"])] = _r["answer"]
S = {"type": "string"}
RULE = FRM.obj(dict(rule=S)); CHECK = AP.CHECK
WRITE = """You write the coding rule for one item of a systematic review of machine-learning prediction studies that use KNHANES.
Two reviewers proposed different rules (P, Q); a decision says which way to settle it. Write the rule in Occam form: a
core rule of one or two sentences, then at most two short exceptions only if the decision requires them. General terms
for all reports: no case numbers, no report-specific names, no exception made to settle a single report. It must not
contradict the item definition or the general rules.

GENERAL RULES
{rules}

ITEM
{item}: {definition}

RULE P
{p}

RULE Q
{q}

DECISION
{decision}
{extra}"""
VERIFY = """Check a coding rule written for one item of a systematic review of machine-learning prediction studies that use KNHANES.
Answer ok if the rule follows the decision, does not contradict the item definition or the general rules, is written in
general terms and is short (a core rule of one or two sentences, at most two short exceptions); otherwise problem, naming
it in one sentence (problem '' when ok).

GENERAL RULES
{rules}

ITEM
{item}: {definition}

RULE P
{p}

RULE Q
{q}

DECISION
{decision}

RULE WRITTEN
{rule}"""


def decide(f, v, dec, sug):
    rr = v.get("r3_rules") or {}
    kw = dict(rules="\n".join(f"- {r}" for r in ITEMS["general_rules"]), item=f, definition=ITEMS["items"][f], p=rr.get("P", ""), q=rr.get("Q", ""))
    if f in dec: d, src = dec[f], "review"
    else: d, src = "Adopt the suggested answer below (written in Korean), as the simplest rule consistent with the item definition and the general rules.\n" + sug.get(f, ""), "suggestion"
    r = FRM.ask("codex", WRITE.format(decision=d, extra="", **kw), RULE, f"field@{f}-decide")
    if not r: return dict(status="decide_failed", source=src, decision=d)
    c = FRM.ask("claude", VERIFY.format(decision=d, rule=r["rule"], **kw), CHECK, f"field@{f}-decide-check")
    if c and c["verdict"] == "problem":
        r2 = FRM.ask("codex", WRITE.format(decision=d, extra=f"\nA checker found a problem in an earlier draft ({r['rule']}): {c['problem']} Fix it.", **kw), RULE, f"field@{f}-decide-rev")
        if not r2: return dict(status="decide_failed", source=src, decision=d, draft=r["rule"], problem=c["problem"])
        c2 = FRM.ask("claude", VERIFY.format(decision=d, rule=r2["rule"], **kw), CHECK, f"field@{f}-decide-check2")
        if not c2 or c2["verdict"] != "ok": return dict(status="decide_open", source=src, decision=d, draft=r2["rule"], problem=(c2 or {}).get("problem", "check failed"))
        r = r2
    elif not c: return dict(status="decide_failed", source=src, decision=d)
    return dict(status="decided_" + src, source=src, decision=d, rule=r["rule"])


def apply(q, rule):
    r = FRM.apply_case(q, rule)
    if r["outcome"] != "open" or not r.get("answers") or not all(r["answers"]) or r.get("why", "").startswith("write not accepted"): return r
    x, y, x_is_A = FRM.xy(q); lx, ly = ("A", "B") if x_is_A else ("B", "A")
    js = " / ".join(f"{lx} {'ok' if z['X_ok'] else 'problem: ' + z['X_problem']}; {ly} {'ok' if z['Y_ok'] else 'problem: ' + z['Y_problem']}"
                    + ("; printed text may not settle it" if z["insufficient"] else "") for z in r["answers"])
    d = dict(record_id=q["record_id"], item=q["item"], instruction="Code this item under the rule for the item: " + rule
             + " Two checkers judged the codings: " + js + ". Where the printed text does not settle a point, code it as the rules say"
             " (unclear or not_reported), without guessing. Keep a stated conflict between parts of the report (e.g. text and code) as an inconsistency.")
    fin, prob = AP.apply_one(d, q["A"], q["B"], q["group"])
    return dict(outcome="field_rule_write2", final=fin, answers=r["answers"], first=r.get("why")) if fin else dict(outcome="open", why="written coding not accepted: " + prob, answers=r["answers"], first=r.get("why"))


def main():
    workers = int(sys.argv[sys.argv.index("--workers") + 1]) if "--workers" in sys.argv else 8
    for f in ("final_items", "author_queue"):
        if not os.path.exists(f"{C}/{f}_before_field_decide.jsonl"): shutil.copy(f"{C}/{f}.jsonl", f"{C}/{f}_before_field_decide.jsonl")
    FR = json.load(open(f"{C}/field_rules.json"))
    dec = {d["field"]: d["instruction"] for d in json.load(open(f"{C}/review_internal review note.json"))}
    sug = {f: b["suggestion"] for f, b in json.load(open(f"{C}/field_questions_ko.json")).items()}
    noag = [f for f, v in FR.items() if not v.get("rule")]
    with cf.ThreadPoolExecutor(workers) as ex: D = dict(zip(noag, ex.map(lambda f: decide(f, FR[f], dec, sug), noag)))
    for f, d in D.items(): FR[f].update(decision=d, rule=d.get("rule"), status=d["status"])
    json.dump(FR, open(f"{C}/field_rules_decided.json", "w"), ensure_ascii=False, indent=1)
    print("rules", dict(collections.Counter(d["status"] for d in D.values())), flush=True)
    Q = [json.loads(l) for l in open(f"{C}/author_queue_before_field_decide.jsonl")]
    rows = [json.loads(l) for l in open(f"{C}/final_items_before_field_decide.jsonl")]; R = {(r["record_id"], r["item"]): r for r in rows}
    jobs = [q for q in Q if FR.get(q["item"], {}).get("rule")]
    with cf.ThreadPoolExecutor(workers) as ex: res = list(ex.map(lambda q: apply(q, FR[q["item"]]["rule"]), jobs))
    out = {(q["record_id"], q["item"]): r for q, r in zip(jobs, res)}
    left, log = [], []
    for q in Q:
        k = (q["record_id"], q["item"]); r = out.get(k)
        if r and r["outcome"] != "open": R[k]["final"], R[k]["how"] = r["final"], r["outcome"]
        else: left.append(dict(q, field_rule=FR.get(q["item"], {}).get("rule"), field_rule_status=FR.get(q["item"], {}).get("status"), field_apply=r))
        fin = R[k]["final"] if r and r["outcome"] != "open" else None
        log.append(dict(record_id=k[0], item=k[1], field_status=FR.get(q["item"], {}).get("status"), outcome=(r or {}).get("outcome", "open"), why=(r or {}).get("why"),
                        first=(r or {}).get("first"), status_A=q["A"]["status"], status_B=q["B"]["status"], status_final=(fin or {}).get("status"),
                        inconsistency_final=(fin or {}).get("inconsistency")))
    with open(f"{C}/final_items.jsonl", "w") as f:
        for r in rows: f.write(json.dumps(r, ensure_ascii=False) + "\n")
    with open(f"{C}/author_queue.jsonl", "w") as f:
        for q in left: f.write(json.dumps(q, ensure_ascii=False) + "\n")
    with open(f"{C}/field_decide_applied.jsonl", "w") as f:
        for x in log: f.write(json.dumps(x, ensure_ascii=False) + "\n")
    print("outcomes", dict(collections.Counter(x["outcome"] for x in log)), "left for author", len(left), flush=True)
    by = collections.defaultdict(collections.Counter)
    for x in log: by[x["item"]][x["outcome"]] += 1
    for f, c in sorted(by.items(), key=lambda z: -sum(z[1].values())): print(f"{f}\t{FR[f]['status']}\t{dict(c)}", flush=True)


if __name__ == "__main__":
    main()
