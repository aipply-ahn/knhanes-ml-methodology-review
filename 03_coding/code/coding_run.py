"""Two-system data coding of included reports (data coding protocol r0, 2026-11-16; author: code into JSON item by item
with IDs and reasons, consensus coding, Excel later mechanically).
Per report and item group (A data/participants/sample/missing, B outcome/predictors, C development/validation,
D performance, E use/reporting; tools/oct_search/coding/charms_items_v1.json) Claude and Codex each code the items
independently from the same input (coding_render.py: the report with every citable ID), text only, isolated calls
(no tools, no project files, fresh Codex home), raw output kept, answers reused only for identical prompt + schema.
Answer per item: {item, status, values [{unit, value} (+ kind per value from v3.1)], value_kind (to v3), evidence_ids, rationale}; group D also
performance_rows [{model, outcome, dataset_role, dataset_or_split, subgroup, metric, value, ci, threshold, evidence_id}].
Output: results/oct_search/coding/calls.jsonl (one record per call), raw/ (CLI output).
Usage: coding_run.py RID [RID ...] [--workers N] [--groups A,B,...]"""
import concurrent.futures as cf, hashlib, json, os, shutil, subprocess, sys, tempfile, threading, time
HERE = os.path.dirname(os.path.abspath(__file__)); ROOT = os.path.dirname(os.path.dirname(HERE)); sys.path.insert(0, HERE); os.chdir(ROOT)
import visual_run as V
import coding_render as CR
OUT = os.environ.get("CODING_OUT", "results/oct_search/coding"); ITEMS = json.load(open("tools/oct_search/coding/charms_items_" + os.environ.get("CODING_ITEMS", "v3.1.3") + ".json")); LOCK = threading.Lock()
STATUS = ["reported", "not_reported", "unclear", "not_applicable"] if ITEMS["version"] >= "v3" else ["reported", "not_reported", "unclear", "not_applicable", "conflicting"]
V3 = ITEMS["version"] >= "v3"
V31 = ITEMS["version"] >= "v3.1"  # v3.1: value kind per value entry (internal review note review)
V312 = ITEMS["version"] >= "v3.1.2"  # v3.1.2: performance rows carry analysis main | sensitivity | comparator | other (internal review note)
KIND = ["printed", "approx", "derived", "judged", "none"]
S = {"type": "string"}


def schema(group):
    item = {"type": "object", "additionalProperties": False, "required": ["item", "status", "values", "value_kind", "evidence_ids", "rationale"], "properties": {
        "item": {"type": "string", "enum": ITEMS["groups"][group]}, "status": {"type": "string", "enum": STATUS},
        "values": {"type": "array", "items": {"type": "object", "additionalProperties": False, "required": ["unit", "value"], "properties": {"unit": S, "value": S}}},
        "value_kind": {"type": "string", "enum": KIND}, "evidence_ids": {"type": "array", "items": S}, "rationale": S}}
    if V31:
        item["required"].remove("value_kind"); del item["properties"]["value_kind"]
        v = item["properties"]["values"]["items"]; v["required"].append("kind"); v["properties"]["kind"] = {"type": "string", "enum": KIND[:4]}
    if V3:  # v3: internal inconsistency recorded apart from the reporting status
        item["required"] += ["inconsistency", "inconsistency_note"]
        item["properties"].update(inconsistency={"type": "string", "enum": ["none", "present", "uncertain"]}, inconsistency_note=S)
    row = {"type": "object", "additionalProperties": False, "required": ["model", "outcome", "dataset_role", "dataset_or_split", "subgroup", "metric", "value", "ci", "threshold", "evidence_id"],
           "properties": {"model": S, "outcome": S, "dataset_role": {"type": "string", "enum": ["apparent", "internal", "external", "unclear"]}, "dataset_or_split": S,
                          "subgroup": S, "metric": S, "value": S, "ci": S, "threshold": S, "evidence_id": S}}
    if V312:
        row["required"].insert(2, "analysis"); row["properties"]["analysis"] = {"type": "string", "enum": ["main", "sensitivity", "comparator", "other"]}
    return {"type": "object", "additionalProperties": False, "required": ["items", "performance_rows"], "properties": {
        "items": {"type": "array", "items": item}, "performance_rows": {"type": "array", "items": row}}}


PROMPT = """You are one of two independent reviewers coding a research report for a systematic review of machine-learning
prediction studies that use the Korea National Health and Nutrition Examination Survey (KNHANES). Below the
instructions is the whole report: body paragraphs, tables (cell by cell) and figures (element by element), and
supplementary text, each piece with its ID in square brackets. Code the items of this group.

GENERAL RULES
{rules}

ITEMS (code every item exactly once, in this order)
{items}
{perf}
Answer in the given JSON form. values: [] when status is not_applicable, and when not_reported unless the item allows
a derived value; otherwise one entry per unit of the item (unit "" when the value applies to the whole study).{kind} Cite IDs
exactly as they appear (without brackets). rationale: one sentence.

REPORT
{report}"""
PERF = """
PERFORMANCE ROWS: list every reported performance value as one row (model, outcome,{analysis} dataset_role apparent | internal |
external | unclear, dataset_or_split as named, subgroup or "", metric as printed, value exactly as printed, ci as printed
or "", threshold or "", evidence_id = the cell or paragraph or figure element). Leave the list empty if none.
For items other than performance.estimate do not repeat the rows; for performance.estimate give status and evidence and
leave values empty (the rows carry the values).
"""


def text_call(who, prompt, sch, tag):
    """One isolated text-only call (as visual_run._call, without an image)."""
    cfg = V.SCREENERS[who]; d = tempfile.mkdtemp(prefix="coding-"); t0 = time.time()
    h = lambda x: hashlib.sha256(x.encode()).hexdigest()
    meta = dict(request=dict(tag=tag, assessor=who, model=cfg["model"], effort=cfg["effort"], prompt_sha256=h(prompt), schema_sha256=h(json.dumps(sch, sort_keys=True))))
    try:
        if who == "claude":
            cmd = ["claude", "-p", "--safe-mode", "--model", cfg["model"], "--effort", cfg["effort"], "--tools", "", "--setting-sources", "",
                   "--strict-mcp-config", "--no-session-persistence", "--output-format", "stream-json", "--verbose", "--json-schema", json.dumps(sch)]
            p = subprocess.run(cmd, input=prompt, capture_output=True, text=True, cwd=d, timeout=3600)
            ev = [json.loads(l) for l in p.stdout.splitlines() if l.startswith("{")]
            r = [e for e in ev if e.get("type") == "result"]
            meta.update(seconds=round(time.time() - t0, 1), exit=p.returncode); V.keep_raw(tag, who, p.stdout, meta)
            if p.returncode or not r: return None, f"claude exit {p.returncode}: {(p.stderr or p.stdout)[-300:]}", meta
            r = r[-1]
            if r.get("is_error") or r.get("subtype") != "success": return None, f"claude error: {str(r.get('result'))[:300]}", meta
            if cfg["model"] not in (r.get("modelUsage") or {}): return None, "claude: unexpected model", meta
            return r.get("structured_output"), None, meta
        sf = os.path.join(d, "schema.json"); json.dump(sch, open(sf, "w")); of = os.path.join(d, "out.json")
        cmd = ["codex", "exec", "--ignore-user-config", "--ignore-rules", "--skip-git-repo-check", "--ephemeral", "-s", "read-only", "-C", d,
               "-m", cfg["model"], "-c", f'model_reasoning_effort="{cfg["effort"]}"', "--output-schema", sf, "-o", of, "--json"]
        for f in V.CODEX_DISABLE: cmd += ["--disable", f]
        cmd += ["-c", "project_doc_max_bytes=0", "-c", "memories.use_memories=false", "-c", "memories.generate_memories=false", "-c", 'web_search="disabled"']
        p = subprocess.run(cmd + ["-"], input=prompt, capture_output=True, text=True, cwd=d, timeout=3600, env=dict(os.environ, CODEX_HOME=V.codex_home(d)))
        meta.update(seconds=round(time.time() - t0, 1), exit=p.returncode); V.keep_raw(tag, who, p.stdout, meta)
        if p.returncode: return None, f"codex exit {p.returncode}: {(p.stderr or p.stdout)[-300:]}", meta
        types = []
        for l in p.stdout.splitlines():
            try: types.append(json.loads(l).get("type"))
            except Exception: pass
        if "turn.completed" not in types or "turn.failed" in types: return None, "codex: turn not completed", meta
        return json.load(open(of)), None, meta
    except Exception as e:
        return None, f"{who}: {e!r}"[:300], meta
    finally:
        shutil.rmtree(d, ignore_errors=True)


def prompt_for(rid, group, report):
    items = "\n".join(f"- {i}: {ITEMS['items'][i]}" for i in ITEMS["groups"][group])
    return PROMPT.format(rules="\n".join(f"- {r}" for r in ITEMS["general_rules"]), items=items, perf=(PERF.replace("{analysis}", " analysis main | sensitivity | comparator | other," if V312 else "")) if group == "D_performance" else "", report=report,
                         kind=" kind per value: printed | derived | judged | approx." if V31 else "")


def main():
    rids = [a for a in sys.argv[1:] if a.startswith("OCT")]
    workers = int(sys.argv[sys.argv.index("--workers") + 1]) if "--workers" in sys.argv else 6
    groups = sys.argv[sys.argv.index("--groups") + 1].split(",") if "--groups" in sys.argv else list(ITEMS["groups"])
    groups = [g for g in ITEMS["groups"] if any(g.startswith(x) for x in groups)]
    os.makedirs(OUT, exist_ok=True); V.RAW = os.path.join(OUT, "raw"); os.makedirs(V.RAW, exist_ok=True)
    f = os.path.join(OUT, "calls.jsonl"); done = set()
    if os.path.exists(f):
        for l in open(f):
            r = json.loads(l)
            if r.get("answer"): done.add((r["record_id"], r["group"], r["assessor"], r["prompt_sha256"]))
    jobs = []
    for rid in rids:
        rep = CR.render(rid)
        for g in groups:
            p = prompt_for(rid, g, rep); ps = hashlib.sha256(p.encode()).hexdigest()
            for w in ("claude", "codex"):
                if (rid, g, w, ps) not in done: jobs.append((rid, g, w, p, ps))
    print("coding calls", len(jobs), flush=True)
    if "--count-only" in sys.argv: return

    def one(j):
        rid, g, w, p, ps = j; sch = schema(g)
        res, err, meta = text_call(w, p, sch, f"{rid}@coding-{g}")
        ok = res is not None and isinstance(res.get("items"), list)
        rec = dict(record_id=rid, group=g, assessor=w, prompt_sha256=ps, items_version=ITEMS["version"], answer=res if ok else None, error=None if ok else (err or "invalid"), call=meta)
        with LOCK, open(f, "a") as fo: fo.write(json.dumps(rec, ensure_ascii=False) + "\n")
        return ok
    with cf.ThreadPoolExecutor(workers) as ex: res = list(ex.map(one, jobs))
    print("done", sum(res), "ok,", len(res) - sum(res), "failed", flush=True)


if __name__ == "__main__":
    main()
