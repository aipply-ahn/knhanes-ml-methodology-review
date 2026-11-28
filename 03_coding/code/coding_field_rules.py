"""Field-level rule settlement of the open data-coding items (internal review note, author: do not settle the open items
one by one - pick the fields in dispute (Occam's razor: fewest causes, fewest rules), find what goes wrong in each field,
agree on a common rule in at most three cross-checked rounds per field, apply the rule to every open case, send only
the rest to the author).
Per field (item) with open cases (author_queue.jsonl):
  R1  Claude and Codex each (independently, text only, isolated calls) read the item definition, the coding rules and
      up to 10 open cases (the two codings shown as X / Y, order fixed by a hash, so neither system sees which is its
      own; printed text of the cited IDs) and give the recurring causes of the disagreement, whether the existing rules
      already decide each, and ONE minimal rule for the field (the exact reading of the existing rule when no new rule
      is needed).
  R2  Each sees both R1 rules (P / Q, hash order) with the same cases, checks them and chooses P, Q or REVISED (with
      the revised text). Same choice P or Q by both -> agreed, stop.
  R3  Each sees both R2 rules (P / Q) and up to 6 other open cases of the field (counter-example test) and chooses P,
      Q, EITHER (same effect) or NONE (with the counter-example). P/Q agreed (EITHER goes with the other's choice;
      EITHER + EITHER -> P) -> agreed; otherwise the field goes to the author as a rule question with both rules.
      (Choosing between two texts drew each system to its own text in tests, so R3 judges each rule on its own:)
      R3 checks each rule separately on the test cases (ok, or not ok with a counterexample); a rule accepted by both
      systems is agreed (both accepted: the shorter); none -> rule question for the author with both rules.
Application (agreed fields): per open case both systems independently judge codings X / Y (hash order) each on its own
under the agreed rule, with the full printed text of the cited IDs (ok, or not ok with the problem; insufficient = the
cited text does not let one judge, no side is chosen then). A coding accepted by both while the other is not -> final
(how field_rule_A / field_rule_B); both accepted by both -> the one with more values (A on a tie); neither accepted by
anyone -> Codex writes the coding under the rule, Claude checks it, one revision (coding_apply_decisions.apply_one) ->
how field_rule_write.
Anything else stays for the author. Earlier codings and all round records are kept.
Output: field_rules_calls.jsonl (raw), field_rules.json (per field: cases, causes, rounds, rule, status),
field_rules_applied.jsonl (per case), final_items.jsonl / author_queue.jsonl updated (inputs copied to *_before_field_rules).
Usage: coding_field_rules.py [--workers N] [--fields a,b]"""
import collections, concurrent.futures as cf, hashlib, json, os, shutil, sys, threading
HERE = os.path.dirname(os.path.abspath(__file__)); ROOT = os.path.dirname(os.path.dirname(HERE)); sys.path.insert(0, HERE); os.chdir(ROOT)
import coding_run as RUN, coding_consensus as CS, coding_apply_decisions as AP
C = os.environ.get("CODING_OUT", "results/oct_search/coding"); CALLS = f"{C}/field_rules_calls.jsonl"; LOCK = threading.Lock(); ITEMS = RUN.ITEMS
AP.CALLS, AP.LOCK = CALLS, LOCK  # NEITHER-path writes go to the same raw file under the same lock
S = {"type": "string"}; B = {"type": "boolean"}
def obj(props, req=None): return {"type": "object", "additionalProperties": False, "required": req or list(props), "properties": props}
SCH1 = obj(dict(causes={"type": "array", "items": obj(dict(cause=S, cases={"type": "array", "items": {"type": "integer"}}, existing_rules_decide=B))},
                new_rule_needed=B, rule=S))
SCH2 = obj(dict(check_P=S, check_Q=S, choice={"type": "string", "enum": ["P", "Q", "REVISED"]}, rule=S))
SCH3 = obj(dict(P_ok=B, P_counterexample=S, Q_ok=B, Q_counterexample=S))
SCHA = obj(dict(insufficient=B, X_ok=B, X_problem=S, Y_ok=B, Y_problem=S))
HEAD = """You help settle the coding rules of a systematic review of machine-learning prediction studies that use the Korea
National Health and Nutrition Examination Survey (KNHANES). Two independent coders (shown as X and Y, in no particular
order) coded the item below in many reports and disagree on the cases shown. The aim is the simplest rule that makes the
coding of this item consistent and accurate across all reports (Occam's razor: the fewest causes and the fewest, shortest
rules that explain the disagreements). Do not assume either coder is right. Where the existing rules already decide a
case, no new rule is needed: then the rule to state is the exact reading of the existing rule. A rule must not let a coder
infer what the printed text does not state. Write every rule in general terms for all reports: no case numbers, no report-
specific names.

CODING RULES (general)
{rules}

ITEM
{item}: {definition}
"""
R1 = HEAD + """
TASK: list the recurring causes of the disagreement (each cause with the case numbers it explains and whether the
existing rules already decide it), then give ONE rule for this item that settles them: a few sentences to be added to
the item definition (or, if the existing rules suffice, the exact reading of the existing rules for these cases).

CASES
{cases}"""
R2 = HEAD + """
Two rules were proposed for this item (P and Q, in no particular order):
P: {p}
Q: {q}

TASK: check each against the cases and the existing rules (check_P, check_Q: one or two sentences: what it gets right,
what it gets wrong or leaves open). Then choose P or Q if it is right and sufficient as written; otherwise REVISED and
write the revised rule (the simplest wording that is right). rule: the text of the rule you choose (copied when P/Q).
When P and Q differ only on a convention on which both are defensible, the simpler one wins: fewer distinctions, closer
to the wording of the item definition and the general rules, less judgement asked of the coder.

CASES
{cases}"""
R3 = HEAD + """
Two final candidate rules for this item (P and Q, in no particular order):
P: {p}
Q: {q}

TASK: test each rule on its own on the cases below (other cases of the same item, not used to write the rules).
P_ok: true if coding these cases by P gives correct, consistent codings that the printed text supports; false only with
a counterexample (P_counterexample: the case number and what P gets wrong; '' when P_ok). The same for Q. Judge each
rule on its own: both can be acceptable, or neither.

CASES
{cases}"""
APP = HEAD + """
AGREED RULE FOR THIS ITEM
{rule}

TASK: apply the agreed rule and the coding rules to this report and judge each coding on its own. X_ok: true if
coding X follows them and states nothing the printed text of the cited IDs does not support and misses nothing it
clearly states; false only with the problem named (X_problem; '' when X_ok). The same for Y. Both can be acceptable, or
neither. insufficient: true only if the printed text does not let you judge under the rule (do not guess then).

CODING X
{x}

CODING Y
{y}

PRINTED TEXT OF THE CITED IDS
{evidence}"""
_cache = None


def ask(who, prompt, sch, tag):
    global _cache
    ps = hashlib.sha256(prompt.encode()).hexdigest()
    with LOCK:
        if _cache is None:
            _cache = {}
            if os.path.exists(CALLS):
                for l in open(CALLS):
                    r = json.loads(l)
                    if r.get("answer"): _cache[(r["tag"], r["assessor"], r["prompt_sha256"])] = r["answer"]
        if (tag, who, ps) in _cache: return _cache[(tag, who, ps)]
    res, err, meta = RUN.text_call(who, prompt, sch, tag)
    with LOCK:
        open(CALLS, "a").write(json.dumps(dict(tag=tag, assessor=who, prompt_sha256=ps, answer=res, error=err, call=meta), ensure_ascii=False) + "\n")
        if res: _cache[(tag, who, ps)] = res
    return res


def both(prompt, sch, tag):
    with cf.ThreadPoolExecutor(2) as ex: return list(ex.map(lambda w: ask(w, prompt, sch, tag), ("claude", "codex")))


def h(s): return int(hashlib.sha256(s.encode()).hexdigest(), 16)


_T = {}
def texts(rid):
    with LOCK:
        if rid not in _T: _T[rid] = CS.id_text(CS.CR.render(rid))
        return _T[rid]


def xy(q):
    """Coding X / Y of a case (hash order); returns (x, y, x_is_A)."""
    sw = h(q["record_id"] + q["item"]) % 2
    return (q["B"], q["A"], False) if sw else (q["A"], q["B"], True)


def case_block(qs, cut=800):
    out = []
    for k, q in enumerate(qs, 1):
        x, y, _ = xy(q); T = texts(q["record_id"])
        ids = list(dict.fromkeys(x["evidence_ids"] + y["evidence_ids"]))
        ev = "\n".join(f"  [{i}] {T.get(i, '(ID not found)')[:cut]}" for i in ids)
        out.append(f"CASE {k} ({q['record_id']})\n X: {CS.show(x)}\n Y: {CS.show(y)}\n printed text:\n{ev}")
    return "\n\n".join(out)


def pq(field, a, b, rnd):
    return (b, a, True) if h(field + rnd) % 2 else (a, b, False)


def settle(field, qs):
    qs = sorted(qs, key=lambda q: h(q["record_id"] + field))
    s1, s3 = qs[:10], (qs[10:16] or qs[:6])
    kw = dict(rules="\n".join(f"- {r}" for r in ITEMS["general_rules"]), item=field, definition=ITEMS["items"][field])
    rec = dict(field=field, cases=len(qs), sample=[q["record_id"] for q in s1], test=[q["record_id"] for q in s3])
    r1 = both(R1.format(cases=case_block(s1), **kw), SCH1, f"field@{field}-r1")
    if not all(r1): return dict(rec, status="failed_r1")
    rec["r1"] = r1
    p, q, swapped = pq(field, r1[0]["rule"], r1[1]["rule"], "r2")
    r2 = both(R2.format(p=p, q=q, cases=case_block(s1), **kw), SCH2, f"field@{field}-r2")
    if not all(r2): return dict(rec, status="failed_r2")
    rec["r2"] = r2; rec["r2_order"] = "codex,claude" if swapped else "claude,codex"
    ch = [x["choice"] for x in r2]
    if ch[0] == ch[1] and ch[0] in ("P", "Q"):
        return dict(rec, status="agreed_r2", rule={"P": p, "Q": q}[ch[0]])
    p, q, swapped = pq(field, r2[0]["rule"], r2[1]["rule"], "r3")
    r3 = both(R3.format(p=p, q=q, cases=case_block(s3), **kw), SCH3, f"field@{field}-r3")
    if not all(r3): return dict(rec, status="failed_r3")
    rec["r3"] = r3; rec["r3_rules"] = dict(P=p, Q=q)
    ok = [k for k in ("P", "Q") if all(x[k + "_ok"] for x in r3)]  # a rule accepted by both systems
    if ok:
        rule = min((rec["r3_rules"][k] for k in ok), key=len)  # both accepted by both: the simpler (shorter) one
        return dict(rec, status="agreed_r3", rule=rule)
    return dict(rec, status="no_agreement")


def apply_case(q, rule):
    x, y, x_is_A = xy(q); T = texts(q["record_id"])
    ids = list(dict.fromkeys(x["evidence_ids"] + y["evidence_ids"]))
    kw = dict(rules="\n".join(f"- {r}" for r in ITEMS["general_rules"]), item=q["item"], definition=ITEMS["items"][q["item"]])
    pr = APP.format(rule=rule, x=CS.show(x), y=CS.show(y), evidence="\n".join(f"[{i}] {T.get(i, '(ID not found)')}" for i in ids), **kw)
    a = both(pr, SCHA, f"{q['record_id']}@fieldapply-{q['item']}")
    if not all(a): return dict(outcome="open", why="call failed", answers=a)
    if any(z["insufficient"] for z in a): return dict(outcome="open", why="insufficient text under the rule", answers=a)
    okx, oky = all(z["X_ok"] for z in a), all(z["Y_ok"] for z in a)
    A_ok, B_ok = (okx, oky) if x_is_A else (oky, okx)
    if A_ok or B_ok:
        if A_ok and B_ok:  # both accepted by both: the more complete one (more values), A by convention on a tie
            ab = "B" if len(q["B"]["values"]) > len(q["A"]["values"]) else "A"
        else: ab = "A" if A_ok else "B"
        return dict(outcome="field_rule_" + ab, final=q[ab], answers=a)
    if not any(z["X_ok"] or z["Y_ok"] for z in a):
        d = dict(record_id=q["record_id"], item=q["item"], instruction="Code this item under the agreed rule for the item: " + rule
                 + " Both checkers found both codings wrong: " + " / ".join(z["X_problem"] + " | " + z["Y_problem"] for z in a))
        fin, prob = AP.apply_one(dict(d), q["A"], q["B"], q["group"])
        if fin: return dict(outcome="field_rule_write", final=fin, answers=a)
        return dict(outcome="open", why="write not accepted: " + prob, answers=a)
    return dict(outcome="open", why="split: each system accepts a different coding", answers=a)


def main():
    workers = int(sys.argv[sys.argv.index("--workers") + 1]) if "--workers" in sys.argv else 8
    only = sys.argv[sys.argv.index("--fields") + 1].split(",") if "--fields" in sys.argv else None
    for f in ("final_items", "author_queue"):
        if not os.path.exists(f"{C}/{f}_before_field_rules.jsonl"): shutil.copy(f"{C}/{f}.jsonl", f"{C}/{f}_before_field_rules.jsonl")
    Q = [json.loads(l) for l in open(f"{C}/author_queue_before_field_rules.jsonl")]
    rows = [json.loads(l) for l in open(f"{C}/final_items_before_field_rules.jsonl")]; R = {(r["record_id"], r["item"]): r for r in rows}
    by = collections.defaultdict(list)
    for q in Q:
        if not only or q["item"] in only: by[q["item"]].append(q)
    print("fields", len(by), "cases", sum(map(len, by.values())), flush=True)
    with cf.ThreadPoolExecutor(workers) as ex: FR = dict(zip(by, ex.map(lambda f: settle(f, by[f]), by)))
    print("rules", dict(collections.Counter(v["status"] for v in FR.values())), flush=True)
    jobs = [(q, FR[f]["rule"]) for f, qs in by.items() if FR[f].get("rule") for q in qs]
    with cf.ThreadPoolExecutor(workers) as ex: res = list(ex.map(lambda j: apply_case(*j), jobs))
    out = {(q["record_id"], q["item"]): r for (q, _), r in zip(jobs, res)}
    left, log = [], []
    for q in Q:
        k = (q["record_id"], q["item"]); r = out.get(k)
        if r and r["outcome"] != "open":
            R[k]["final"], R[k]["how"] = r["final"], r["outcome"]
        else:
            q = dict(q, field_rule=FR.get(q["item"], {}).get("rule"), field_rule_status=FR.get(q["item"], {}).get("status"), field_apply=r); left.append(q)
        if q["item"] in by: log.append(dict(record_id=k[0], item=k[1], **{x: y for x, y in (r or dict(outcome="open", why=FR[q["item"]]["status"])).items() if x != "final"}))
    with open(f"{C}/final_items.jsonl", "w") as f:
        for r in rows: f.write(json.dumps(r, ensure_ascii=False) + "\n")
    with open(f"{C}/author_queue.jsonl", "w") as f:
        for q in left: f.write(json.dumps(q, ensure_ascii=False) + "\n")
    with open(f"{C}/field_rules_applied.jsonl", "w") as f:
        for x in log: f.write(json.dumps(x, ensure_ascii=False) + "\n")
    json.dump(FR, open(f"{C}/field_rules.json", "w"), ensure_ascii=False, indent=1)
    print("outcomes", dict(collections.Counter(x["outcome"] for x in log)), "left for author", len(left), flush=True)
    print("field\tcases\tcauses(c/x)\tstatus\tresolved\tleft")
    for f, v in sorted(FR.items(), key=lambda z: -z[1]["cases"]):
        n = sum(1 for x in log if x["item"] == f and x["outcome"] != "open")
        cz = "/".join(str(len(a["causes"])) for a in v.get("r1", [])) or "-"
        print(f"{f}\t{v['cases']}\t{cz}\t{v['status']}\t{n}\t{v['cases'] - n}", flush=True)


if __name__ == "__main__":
    main()
