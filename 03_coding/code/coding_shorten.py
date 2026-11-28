"""Tidy the final coded values before the Excel file (author: 'tidy the long values and convert to Excel').
1. model_development.step_data_scope values written as JSON text ({"step": "scope", ...}) are split mechanically into
   one value per step (unit gets ' | <step>' appended; value = the scope label); kind kept.
2. Values longer than LIMIT characters: Codex writes a short form (at most ~200 characters) that keeps every number,
   named method, variable, dataset and qualifier needed for the item and adds nothing; Claude checks each short form
   against the full value (ok | problem); one revision; still a problem -> the full value is kept (flag short_failed).
   The full text stays in value_full. Nothing else changes.
Input: final_items.jsonl of the full run and pilot_final/final_items.jsonl; output: final_items_clean.jsonl (both
together, 287 reports) and shorten_calls.jsonl (raw). Usage: coding_shorten.py [--workers N]"""
import collections, concurrent.futures as cf, copy, hashlib, json, os, sys, threading
HERE = os.path.dirname(os.path.abspath(__file__)); ROOT = os.path.dirname(os.path.dirname(HERE)); sys.path.insert(0, HERE); os.chdir(ROOT)
import coding_run as RUN
C = "results/oct_search/coding"; CALLS = f"{C}/shorten_calls.jsonl"; LOCK = threading.Lock(); LIMIT = 300
S = {"type": "string"}
SHORT = {"type": "object", "additionalProperties": False, "required": ["short"], "properties": {"short": {"type": "array", "items": S}}}
CHECK = {"type": "object", "additionalProperties": False, "required": ["checks"], "properties": {"checks": {"type": "array", "items": {
    "type": "object", "additionalProperties": False, "required": ["n", "ok", "problem"], "properties": {"n": {"type": "integer"}, "ok": {"type": "boolean"}, "problem": S}}}}}
W = """Shorten coded values of one item of a systematic-review dataset (machine-learning studies using KNHANES). For each
numbered value write a short form of at most about 200 characters, in the same language as the value, that keeps every
number, named method, model, variable, dataset, split and qualifier (e.g. 'not stated', 'training data only') that
answers the item, drops repetition, quotations of procedure and explanations, and adds nothing. Use ';' between parts.
Return the short forms in the same order (one per numbered value).

ITEM
{item}: {definition}

VALUES
{values}{extra}"""
V = """Check short forms of coded values (systematic-review dataset of machine-learning studies using KNHANES). For each
numbered pair: ok if the short form keeps every number, named method, model, variable, dataset, split and qualifier of
the full value that answers the item and adds or changes nothing; otherwise not ok with the problem in one sentence
('' when ok).

ITEM
{item}: {definition}

PAIRS
{pairs}"""


def ask(who, prompt, sch, tag):
    ps = hashlib.sha256(prompt.encode()).hexdigest()
    with LOCK:
        if os.path.exists(CALLS):
            for l in open(CALLS):
                r = json.loads(l)
                if r["tag"] == tag and r["assessor"] == who and r["prompt_sha256"] == ps and r.get("answer"): return r["answer"]
    res, err, meta = RUN.text_call(who, prompt, sch, tag)
    with LOCK: open(CALLS, "a").write(json.dumps(dict(tag=tag, assessor=who, prompt_sha256=ps, answer=res, error=err, call=meta), ensure_ascii=False) + "\n")
    return res


def split_steps(x):
    out = []
    for v in x["values"]:
        t = v["value"].strip()
        if x.get("item") == "model_development.step_data_scope" and t.startswith("{"):
            try: d = json.loads(t)
            except Exception: d = None
            if isinstance(d, dict) and d:
                out += [dict(v, unit=(v["unit"] + " | " if v["unit"] else "") + k, value=str(s)) for k, s in d.items()]; continue
        out.append(v)
    return out


def shorten(rid, item, vals):
    """vals: list of (index, full text). Returns {index: short} for the short forms Claude accepted."""
    d = RUN.ITEMS["items"][item]; tag = f"{rid}@short-{item}"
    vs = "\n".join(f"{k + 1}. {t}" for k, (_, t) in enumerate(vals))
    s = ask("codex", W.format(item=item, definition=d, values=vs, extra=""), SHORT, tag)
    if not s or len(s["short"]) != len(vals): return {}
    def check(ks, shorts, t):
        pairs = "\n".join(f"{n + 1}. FULL: {vals[k][1]}\n   SHORT: {shorts[k]}" for n, k in enumerate(ks))
        c = ask("claude", V.format(item=item, definition=d, pairs=pairs), CHECK, t)
        if not c: return None
        bad = {z["n"] - 1: z["problem"] for z in c["checks"] if not z["ok"]}
        return {ks[n]: p for n, p in bad.items() if 0 <= n < len(ks)}
    ks = list(range(len(vals))); bad = check(ks, s["short"], tag + "-check")
    if bad is None: return {}
    acc = {vals[k][0]: s["short"][k] for k in ks if k not in bad}
    if not bad: return acc
    extra = "\n\nAn earlier attempt had problems; fix them: " + " / ".join(f"value {k + 1}: {p}" for k, p in bad.items())
    s2 = ask("codex", W.format(item=item, definition=d, values=vs, extra=extra), SHORT, tag + "-rev")
    if not s2 or len(s2["short"]) != len(vals): return acc
    kb = sorted(bad); bad2 = check(kb, s2["short"], tag + "-check2")
    if bad2 is None: return acc
    acc.update({vals[k][0]: s2["short"][k] for k in kb if k not in bad2})
    return acc


def main():
    workers = int(sys.argv[sys.argv.index("--workers") + 1]) if "--workers" in sys.argv else 10
    rows = [json.loads(l) for l in open(f"{C}/pilot_final/final_items.jsonl")] + [json.loads(l) for l in open(f"{C}/final_items.jsonl")]
    rows = [copy.deepcopy(r) for r in rows]
    jobs = []
    for r in rows:
        x = r["final"]
        if not x: continue
        x["values"] = split_steps(dict(x, item=r["item"]))
        long = [(i, v["value"]) for i, v in enumerate(x["values"]) if len(v["value"]) > LIMIT]
        if long: jobs.append((r, long))
    print("items with long values", len(jobs), "values", sum(len(l) for _, l in jobs), flush=True)
    with cf.ThreadPoolExecutor(workers) as ex: res = list(ex.map(lambda j: shorten(j[0]["record_id"], j[0]["item"], j[1]), jobs))
    cnt = collections.Counter()
    for (r, long), acc in zip(jobs, res):
        for i, t in long:
            v = r["final"]["values"][i]; v["value_full"] = t
            if i in acc: v["value"] = acc[i]; cnt["shortened"] += 1
            else: v["short_failed"] = True; cnt["kept_full"] += 1
    with open(f"{C}/final_items_clean.jsonl", "w") as f:
        for r in rows: f.write(json.dumps(r, ensure_ascii=False) + "\n")
    print("rows", len(rows), dict(cnt), flush=True)


if __name__ == "__main__":
    main()
