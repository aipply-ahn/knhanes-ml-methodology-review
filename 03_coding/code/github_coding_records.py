"""Public round-by-round record of the data coding, one JSON line per report x item, in the order of the five steps of
the settlement (author 2026-11-20: record selection and coding as one linear process - cross-review rounds, author's
directions, cross-checks under those directions, decision - and publish the intermediate results as one file per stage).
Nothing is re-decided here: every entry is read from the recorded calls and the recorded settlement route (how).

Published per coding: report id, run, item, item group; for each step what each system returned in categories
(status, choice, verdict, rule side), the route that settled it and the final status. Not published: coded values,
evidence identifiers, reasons and notes of the systems (they may contain text copied from the reports), prompt
hashes. Field-rule records (one line per field): proposed rules, choices in each round, status, source of the rule
for fields without agreement, final rule; the systems' causes, checks and counter-examples are not published (they cite
the reports).

Output: <OUT>/coding_rounds.jsonl, <OUT>/field_rules.jsonl, <OUT>/coding_steps_summary.json
Usage: github_coding_records.py OUT_DIR"""
import ast, collections, hashlib, json, os, sys
ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
S = os.path.join(ROOT, "results/oct_search")
OUT = sys.argv[1]; os.makedirs(OUT, exist_ok=True)
RUNS = [("coding", "charms"), ("coding_legacy", "additional_1"), ("coding_legacy2", "additional_2"), ("coding_legacy3", "additional_3")]
PILOT_DIRS = ["coding/v31_pilot", "coding/v3_pilot", "coding/v2_pilot"]


def jl(p):
    if not os.path.exists(p): return []
    out = []
    with open(p) as f:
        for l in f:
            l = l.strip()
            if l:
                try: out.append(json.loads(l))
                except Exception: pass
    return out


def calls(dirs, name):
    """(tag, assessor) -> last recorded answer; earlier directories are overridden by later ones."""
    m = {}
    for d in dirs:
        for r in jl(os.path.join(S, d, name)):
            if r.get("answer"): m[(r["tag"], r["assessor"])] = r["answer"]
    return m


def item_answers(ans):
    if not ans: return {}
    ds = ans.get("decisions") if isinstance(ans, dict) else None
    return {d.get("item"): d for d in ds} if ds is not None else {}


def swap(rid, item): return int(hashlib.sha256((rid + item).encode()).hexdigest(), 16) % 2 == 1


def step_of(how, fstat):
    if how == "agree_r1": return 1
    if how.startswith("consensus"): return 2
    if how.startswith(("rule_not_material", "verify_inconsistency", "triage_", "rule_blind")): return 4
    if how.startswith("field_rule"): return 4 if str(fstat).startswith("agreed") else 5
    return 5  # rule_fix*, decision_* (pilot decisions accepted by the author)


ROUTE = {"agree_r1": "agreed in round 1", "consensus_r1": "same choice in round 2", "consensus_r2": "same choice in round 3",
         "rule_not_material": "fixed rule: difference judged not material by both", "verify_inconsistency": "fixed rule: inconsistency flag verified by both",
         "triage_form": "fixed rule: difference of form by both", "triage_rule": "fixed rule: rule-reading difference, same side by both",
         "rule_blind": "fixed rule: blind rule check, same coding by both", "field_rule": "field rule applied",
         "rule_fix_side": "fallback: coding accepted under the rule", "rule_fix_unclear": "fallback: unclear", "rule_fix": "field rule applied after one more revision",
         "decision": "pilot: review decision accepted by the author"}


def route(how):
    for k in sorted(ROUTE, key=len, reverse=True):
        if how.startswith(k): return ROUTE[k]
    return how


def lit(x):
    if isinstance(x, (list, dict)): return x
    try: return ast.literal_eval(x)
    except Exception: return x


summary = collections.OrderedDict()
with open(os.path.join(OUT, "coding_rounds.jsonl"), "w") as fo, open(os.path.join(OUT, "field_rules.jsonl"), "w") as ff:
    for d, run in RUNS:
        D = os.path.join(S, d)
        fin = jl(f"{D}/final_items.jsonl"); r1 = {(x["record_id"], x["item"]): x for x in jl(f"{D}/compare_r1.jsonl")}
        pilot = set()
        if d == "coding":
            pf = jl(f"{D}/pilot_final/final_items.jsonl"); pilot = {x["record_id"] for x in pf}; fin = pf + fin
            r1.update({(x["record_id"], x["item"]): x for x in jl(f"{D}/pilot_final/compare_r1.jsonl")})
        dirs = ([*PILOT_DIRS] if d == "coding" else []) + [d]
        C = {n: calls(dirs, f"{n}_calls.jsonl") for n in ("consensus", "material", "inconsistency", "triage", "rule_blind")}
        fr = json.load(open(f"{D}/field_rules_decided.json")) if os.path.exists(f"{D}/field_rules_decided.json") else {}
        app = {}
        for n in ("field_rules_applied", "field_decide_applied", "rule_fix_applied"):
            for x in jl(f"{D}/{n}.jsonl"): app.setdefault((x["record_id"], x["item"]), []).append((n, x))
        dec = {(x["record_id"], x["item"]): x for x in jl(f"{D}/decisions_applied.jsonl")} if d == "coding" else {}
        if d == "coding": dec.update({(x["record_id"], x["item"]): x for x in jl(f"{D}/pilot_final/decisions_applied.jsonl")})
        cnt = collections.Counter(); mism = collections.Counter()
        for x in fin:
            rid, it, grp, how = x["record_id"], x["item"], x["group"], x.get("how") or ""
            fstat = (fr.get(it) or {}).get("status")
            rec = dict(record_id=rid, run=run, pilot=rid in pilot, item=it, group=grp)
            steps = []
            a = r1.get((rid, it), {})
            s1 = dict(step=1, name="independent coding", claude=dict(status=(a.get("claude") or {}).get("status"), inconsistency=(a.get("claude") or {}).get("inconsistency")),
                      codex=dict(status=(a.get("codex") or {}).get("status"), inconsistency=(a.get("codex") or {}).get("inconsistency")), comparison=a.get("cls") or x.get("r1_class"))
            steps.append(s1)
            if how != "agree_r1":
                for k in (1, 2):
                    ch = {w: (item_answers(C["consensus"].get((f"{rid}@cons{k}-{grp}", w))).get(it) or {}).get("choice") for w in ("claude", "codex")}
                    if any(ch.values()): steps.append(dict(step=2, name=f"cross-review round {k + 1}", claude=dict(choice=ch["claude"]), codex=dict(choice=ch["codex"]),
                                                          result="same choice" if ch["claude"] == ch["codex"] and ch["claude"] not in (None, "NEITHER") else "different"))
            s4 = []
            m = {w: (item_answers(C["material"].get((f"{rid}@material-{grp}", w))).get(it) or {}).get("verdict") for w in ("claude", "codex")}
            if any(m.values()): s4.append(dict(check="materiality", claude=dict(verdict=m["claude"]), codex=dict(verdict=m["codex"])))
            v = {w: (C["inconsistency"].get((f"{rid}@inconsistency-{it}", w)) or {}).get("verdict") for w in ("claude", "codex")}
            if any(v.values()): s4.append(dict(check="inconsistency flag", claude=dict(verdict=v["claude"]), codex=dict(verdict=v["codex"])))
            t = {w: item_answers(C["triage"].get((f"{rid}@triage-{grp}", w))).get(it) or {} for w in ("claude", "codex")}
            if any(t.values()): s4.append(dict(check="form, rule or substance", **{w: dict(kind=t[w].get("kind"), rule_side=t[w].get("rule_side")) for w in t}))
            b = {w: (item_answers(C["rule_blind"].get((f"{rid}@ruleblind-{grp}", w))).get(it) or {}).get("follows_rules") for w in ("claude", "codex")}
            if any(b.values()):
                mp = {"X": "B" if swap(rid, it) else "A", "Y": "A" if swap(rid, it) else "B"}
                s4.append(dict(check="blind rule check", **{w: dict(follows_rules=mp.get(b[w], b[w])) for w in b}))
            for n, y in app.get((rid, it), []):
                if n == "field_rules_applied": s4.append(dict(check="field rule (agreed by both systems)" if str(y.get("why")) != "no_agreement" else "field rule (no agreement; to step 5)", outcome=y.get("outcome")))
            if s4: steps.append(dict(step=4, name="cross-checks under the author's directions", checks=s4))
            s5 = []
            for n, y in app.get((rid, it), []):
                if n == "field_decide_applied": s5.append(dict(action="field rule applied", field_rule_status=y.get("field_status"), outcome=y.get("outcome")))
                if n == "rule_fix_applied": s5.append(dict(action="fallback", outcome=y.get("how")))
            if (rid, it) in dec: s5.append(dict(action="pilot decision accepted by the author", decision=dec[(rid, it)].get("decision"), outcome=dec[(rid, it)].get("outcome")))
            if s5: steps.append(dict(step=5, name="decision", actions=s5))
            st = step_of(how, fstat)
            f = x.get("final") or {}
            rec.update(steps=steps, final=dict(status=f.get("status"), inconsistency=f.get("inconsistency"), settled_at_step=st, route=route(how), how=how))
            fo.write(json.dumps(rec, ensure_ascii=False) + "\n")
            cnt[st] += 1; cnt["n"] += 1
            # consistency of the recorded calls with the recorded route
            if how.startswith("consensus_r1") and not any(s.get("name") == "cross-review round 2" and s.get("result") == "same choice" for s in steps): mism["consensus_r1"] += 1
            if how.startswith("consensus_r2") and not any(s.get("name") == "cross-review round 3" and s.get("result") == "same choice" for s in steps): mism["consensus_r2"] += 1
        summary[run] = dict(codings=cnt["n"], reports=len({x["record_id"] for x in fin}), settled_by_step={k: cnt[k] for k in (1, 2, 4, 5)}, route_call_mismatch=dict(mism))
        fs = collections.Counter()
        for it, v in fr.items():
            r1r = lit(v.get("r1")) or []; r2r = lit(v.get("r2")) or []; r3r = lit(v.get("r3")) or []
            order = (v.get("r2_order") or "claude,codex").split(",")
            dd = lit(v.get("decision")) or {}
            src = {"agreed_r2": "agreed by both systems in round 2", "agreed_r3": "agreed by both systems in round 3",
                   "decided_review": "no agreement; rule from review comments accepted by the author",
                   "decided_suggestion": "no agreement; suggested rule adopted under the author's direction"}.get(v.get("status"), v.get("status"))
            rec = dict(run=run, field=it, open_cases=int(v.get("cases") or 0),
                       round1=[dict(system=w, proposed_rule=(r1r[i] or {}).get("rule")) for i, w in enumerate(("claude", "codex")) if i < len(r1r)],
                       round2=[dict(system=w, choice=(r2r[i] or {}).get("choice"), revised_rule=(r2r[i] or {}).get("rule") if (r2r[i] or {}).get("choice") == "REVISED" else None) for i, w in enumerate(order) if i < len(r2r)],
                       round3=[dict(system=w, P_accepted=(r3r[i] or {}).get("P_ok"), Q_accepted=(r3r[i] or {}).get("Q_ok"), choice=(r3r[i] or {}).get("choice")) for i, w in enumerate(order) if i < len(r3r)],
                       round3_candidates=lit(v.get("r3_rules")) or None, status=v.get("status"), rule_source=src, final_rule=v.get("rule") or (dd.get("rule") if isinstance(dd, dict) else None))
            ff.write(json.dumps(rec, ensure_ascii=False) + "\n"); fs[v.get("status")] += 1
        summary[run]["field_rules"] = dict(fs)
json.dump(summary, open(os.path.join(OUT, "coding_steps_summary.json"), "w"), indent=1)
print(json.dumps(summary, indent=1))
