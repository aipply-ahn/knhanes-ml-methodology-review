"""Last settling step for cases still open after coding_field_decide.py (author 2026-11-19/20: 'settle the rest yourself').
1) rule_fix: Codex writes the coding under the field rule once more, shown the last checker's problem; Claude checks
   (coding_apply_decisions.apply_one, which allows one more revision).
2) Still not accepted -> by rule, no judgement of mine: the side a checker accepted under the rule (and no checker
   accepted the other side) -> that coding (how rule_fix_side); otherwise status 'unclear' with no value (general rule:
   where the printed text does not settle it, unclear; how rule_fix_unclear).
Output: rule_fix_applied.jsonl; final_items.jsonl updated, author_queue.jsonl emptied (inputs kept as *_before_rule_fix.jsonl).
Usage: CODING_OUT=... CODING_ITEMS=... coding_rule_fix.py [--workers N]"""
import collections, concurrent.futures as cf, json, os, shutil, sys
HERE = os.path.dirname(os.path.abspath(__file__)); ROOT = os.path.dirname(os.path.dirname(HERE)); sys.path.insert(0, HERE); os.chdir(ROOT)
import coding_field_rules as FRM, coding_apply_decisions as AP
C = os.environ.get("CODING_OUT", "results/oct_search/coding")
AP.CALLS = f"{C}/rule_fix_calls.jsonl"


def fix(q):
    fa = q.get("field_apply") or {}
    prob = (fa.get("why") or "").replace("written coding not accepted: ", "")
    if q.get("field_rule"):
        d = dict(record_id=q["record_id"], item=q["item"], instruction="Code this item under the rule for the item: " + q["field_rule"]
                 + (" A checker rejected the last coding written under this rule: " + prob + " Avoid that problem." if prob else "")
                 + " Where the printed text does not settle a point, code it as the rules say (unclear or not_reported), without guessing.")
        fin, p = AP.apply_one(d, q["A"], q["B"], q["group"])
        if fin: return fin, "rule_fix", ""
        prob = p or prob
    x, y, x_is_A = FRM.xy(q); ans = [a for a in fa.get("answers") or [] if a]
    okx, oky = any(a.get("X_ok") for a in ans), any(a.get("Y_ok") for a in ans)
    if okx != oky: return (x if okx else y), "rule_fix_side", prob
    base = q["A"] or q["B"]
    return dict(item=q["item"], status="unclear", values=[], evidence_ids=base.get("evidence_ids", []), inconsistency="absent",
                rationale="Settled by rule: the two codings and the written codings were not accepted under the field rule."), "rule_fix_unclear", prob


def main():
    workers = int(sys.argv[sys.argv.index("--workers") + 1]) if "--workers" in sys.argv else 8
    for f in ("final_items", "author_queue"):
        if not os.path.exists(f"{C}/{f}_before_rule_fix.jsonl"): shutil.copy(f"{C}/{f}.jsonl", f"{C}/{f}_before_rule_fix.jsonl")
    Q = [json.loads(l) for l in open(f"{C}/author_queue_before_rule_fix.jsonl")]
    rows = [json.loads(l) for l in open(f"{C}/final_items.jsonl")]; R = {(r["record_id"], r["item"]): r for r in rows}
    with cf.ThreadPoolExecutor(workers) as ex: res = list(ex.map(fix, Q))
    log = []
    for q, (fin, how, prob) in zip(Q, res):
        r = R[(q["record_id"], q["item"])]; r["final"], r["how"] = fin, how
        log.append(dict(record_id=q["record_id"], item=q["item"], how=how, problem=prob, status_final=fin.get("status")))
    with open(f"{C}/final_items.jsonl", "w") as f:
        for r in rows: f.write(json.dumps(r, ensure_ascii=False) + "\n")
    open(f"{C}/author_queue.jsonl", "w").close()
    with open(f"{C}/rule_fix_applied.jsonl", "w") as f:
        for x in log: f.write(json.dumps(x, ensure_ascii=False) + "\n")
    print("rule_fix", dict(collections.Counter(x["how"] for x in log)), "open", sum(1 for r in rows if r.get("final") is None), flush=True)


if __name__ == "__main__":
    main()
