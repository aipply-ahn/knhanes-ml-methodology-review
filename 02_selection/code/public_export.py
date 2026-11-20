"""Public record of a screening or eligibility run: one JSON line per record with every round in order.
Each round holds Claude's and Codex's decision, code and reason, then the consensus: AGREED with the decision, or
DISAGREED (the next round follows). In a reconsideration round each assessor's reply to the other's previous view is
given as response_to_codex / response_to_claude, as written by that assessor in that round.
Not published: abstracts, full texts, PDFs, verbatim quotations from the reports, text hashes and page numbers (page
references in the assessors' reasons are replaced by "[page]").
Usage: public_export.py RUN_DIR OUT_JSONL"""
import csv, json, os, re, sys
D, OUT = sys.argv[1], sys.argv[2]
rows = [json.loads(l) for l in open(os.path.join(D, [f for f in os.listdir(D) if f.endswith("_rounds.jsonl")][0]))]
dec = {r["record_id"]: r for r in csv.DictReader(open(os.path.join(D, "decisions.csv")))}
post = os.path.join(os.path.dirname(D.rstrip("/")), "author_post_run_exclusions.csv")  # author decisions after the run
post = {r["record_id"]: r for r in csv.DictReader(open(post))} if os.path.exists(post) else {}
ORDER = [("initial", 1), ("consensus", 1), ("consensus", 2), ("consensus", 3), ("challenge", 1),
         ("challenge_consensus", 1), ("challenge_consensus", 2), ("challenge_consensus", 3)]
OTHER = {"claude": "codex", "codex": "claude"}
PAGE = re.compile(r"\b(?:pages?|pp?\.)\s*\d+(?:\s*(?:-|–|,|and|to)\s*\d+)*", re.I)
mask = lambda t: PAGE.sub("[page]", t) if t else t
by = {}
for r in rows:
    by.setdefault(r["record_id"], {}).setdefault((r["stage"], r["round"]), {})[r["screener"]] = r
with open(OUT, "w") as f:
    for rid in sorted(dec):
        out = []
        for st, k in ORDER:
            pair = by.get(rid, {}).get((st, k))
            if not pair:
                continue
            step = dict(stage=st, round=k)
            for s in ("claude", "codex"):
                x = pair[s]; e = dict(decision=x["decision"], code=x["code"], reason=mask(x["reason"]))
                if x.get("response_to_other"):
                    e[f"response_to_{OTHER[s]}"] = mask(x["response_to_other"])
                step[s] = e
            same = pair["claude"]["decision"] == pair["codex"]["decision"]
            step["consensus"] = dict(status="AGREED", decision=pair["claude"]["decision"]) if same else dict(status="DISAGREED")
            out.append(step)
        d = dec[rid]
        final = d["final_decision"] if d["final_decision"] != "AUTHOR_PENDING" else f"AUTHOR: {d['author_decision'] or 'pending'}"
        code = d["exclusion_code"] or (d.get("author_code") if d["final_decision"] == "AUTHOR_PENDING" else "") or None
        if rid in post:
            final, code = f"AUTHOR (after the run): {post[rid]['decision']}", post[rid]["reason_code"]
        f.write(json.dumps(dict(record_id=rid, rounds=out, final_decision=final, exclusion_code=code), ensure_ascii=False) + "\n")
print("records", len(dec), "->", OUT)
