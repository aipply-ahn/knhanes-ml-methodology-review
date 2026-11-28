"""Transcription of the tables and figures of the included reports by two AI systems, page by page.
Stages, each one pass over the pages that need it, resumable (results appended to OUT/visual_rounds.jsonl):
  initial      Claude and Codex transcribe every selected page independently (page image + text layer).
  reconcile-1  pages whose two transcriptions differ (visual_compare.compare), or where a table still contains numbers
  reconcile-2  absent from the page text layer: each system receives its own and the other's transcription with the
               list of differences and returns a corrected transcription from the image.
Checks on every output: schema; for a TABLE set in text on a page with a text layer, every number must occur in that
layer (otherwise the call is repeated once with the numbers not found; numbers still absent are recorded and flagged).
Freezing: OUT/manifest.json binds the page inventory (page ids, PNG and text-layer hashes), the transcription
configuration (prompts, schema, models, isolation settings, CLI versions, the code that builds and checks calls) and
amendments; a run refuses to continue when any of these differ from the manifest unless --amend "reason" records an
amendment. Each call keeps its raw CLI output (OUT/raw/, gzip) and metadata (duration, event types, model check).
Usage: visual_run.py OUT_DIR STAGE [--records RID,...] [--workers N] [--pages PAGES_JSONL] [--amend TEXT]"""
import argparse, base64, collections, concurrent.futures as cf, datetime, gzip, hashlib, inspect, json, os, re, shutil, subprocess, sys, tempfile, threading, time
ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
os.chdir(ROOT)
sys.path.insert(0, os.path.join(ROOT, "tools/oct_search"))
from visual_compare import compare  # noqa: E402
WORK = "<work_dir_outside_project>/visual_calls"; os.makedirs(WORK, exist_ok=True)
SCREENERS = {"claude": dict(model="claude-opus-5-5", effort="high"), "codex": dict(model="gpt-6.1-sol", effort="high")}
CODEX_DISABLE = ["apps", "plugins", "hooks", "browser_use", "browser_use_external", "in_app_browser", "computer_use", "skill_search", "memories",
                 "shell_tool", "unified_exec"]  # as in the selection runs, plus no shell (an attached image otherwise invites commands)
MAIN = ["initial", "reconcile-1", "reconcile-2", "reconcile-3"]
CHALLENGE = ["challenge", "challenge-reconcile-1", "challenge-reconcile-2", "challenge-reconcile-3"]
STAGES = MAIN + CHALLENGE
RISK = {"caption", "embedded_image", "ocr_page", "supplement"}
KINDS = ["TABLE", "TABLE_AS_IMAGE", "FIGURE"]

SCHEMA = {"type": "object", "additionalProperties": False, "required": ["objects"], "properties": {"objects": {"type": "array", "items": {
    "type": "object", "additionalProperties": False, "required": ["label", "kind", "continued", "caption", "transcription", "uncertain"],
    "properties": {"label": {"type": "string"}, "kind": {"type": "string", "enum": KINDS}, "continued": {"type": "boolean"},
                   "caption": {"type": "string"}, "transcription": {"type": "string"}, "uncertain": {"type": "string"}}}}}}

RULES = """You transcribe the tables and figures on one page of a research report, so that a reviewer can later extract data
without seeing the page. You receive the page image and the text layer extracted from the PDF (it may be missing,
garbled or produced by OCR). The image is authoritative; use the text layer for exact characters where it agrees.

1. Report every table and every figure that appears on this page, including a part of a table or figure that starts on an
   earlier page or continues onto a later one (continued = true if it continues from an earlier page). Do not transcribe
   running body text, references, page headers or footers.
2. label: the label as printed (e.g. "Table 2", "Figure 3", "Fig. 1", "Supplementary Table S1", " 2", " 1");
   "unlabelled" if none is printed. For an image taken from a Word file, the label and caption are those printed in the
   text next to [THIS IMAGE].
3. kind: TABLE = a table set in text; TABLE_AS_IMAGE = a table embedded as a picture; FIGURE = chart, plot, diagram,
   flowchart, decision tree, photograph or other graphic (a figure that consists of a table is TABLE_AS_IMAGE).
4. caption: the caption or title as printed (empty if none).
5. transcription, in Markdown:
   - Table: every row and every column as a Markdown table, each cell exactly as printed (numbers, signs, symbols,
     footnote marks, units); a merged cell is repeated in each row or column it spans; footnotes and abbreviations
     printed under the table follow the table.
   - Figure: first a line stating the figure type (e.g. "ROC curves", "SHAP summary plot", "bar chart", "flow chart",
     "decision tree"); then all printed text (titles, panel labels, axis titles and tick labels, legend entries,
     annotations) and every printed number with what it refers to. Values that are not printed but read from the
     position of a mark on a plot are written with a leading "~" (e.g. ~0.82) and are given only where they can be
     read with reasonable confidence. A flow chart or tree: every box or node with its text and numbers, and which box
     leads to which. A panel-by-panel layout where panels are labelled (A, B, ...).
6. Do not infer, compute or complete values that are not on the page. Write [illegible] for anything that cannot be
   read and say what in uncertain (empty if nothing).
7. A page without any table or figure returns an empty list."""

PROMPT_1 = RULES + "\n\nReport: {title}\nSource: {source}, page {page}\n\nText layer of this page:\n<<<\n{text}\n>>>\n"
PROMPT_R = RULES + """

Report: {title}
Source: {source}, page {page}

Two independent transcriptions of this page differ. Yours is A, the other assessor's is B. Look at the image again and
return your corrected transcription of the whole page (same format). Keep what the image supports and correct what it
does not; do not copy B where the image does not support it.

Differences found by comparison:
{diff}

Transcription A (yours):
{a}

Transcription B (other assessor):
{b}

Text layer of this page:
<<<
{text}
>>>
"""
PROMPT_C = RULES + """

Report: {title}
Source: {source}, page {page}

Below is a transcription of this page on which two independent assessors agreed. Agreement does not guarantee it is
correct: both may have misread the same value or missed the same table or figure. Check it against the image: every
object on the page (is any table or figure missing?), every cell and number, signs, units, labels, row and column
positions. Return the complete transcription of the page in the same format, corrected wherever the image shows an
error; if you find no error, return it unchanged.

Agreed transcription:
{agreed}

Text layer of this page:
<<<
{text}
>>>
"""
RETRY = "\n\nYour previous answer listed numbers in a TABLE set in text that do not occur in the text layer: {nums}. Check them against the image and the text layer."

NUM = re.compile(r"(?<![\w.~≈])[-−–]?\d+(?:,\d{3}(?!\d))*(?:[.·]\d+)?(?:%|‰)?")
norm_num = lambda s: s.replace("−", "-").replace("–", "-").replace("·", ".")
def text_check(objs, text):
    """Numbers of TABLE objects (set in text) missing from a usable text layer."""
    layer = {norm_num(m.group(0)) for m in NUM.finditer(text or "")}
    if len(layer) < 5: return []
    miss = []
    for o in objs:
        if o["kind"] == "TABLE":
            miss += [n for n in (norm_num(m.group(0)) for m in NUM.finditer(o["transcription"])) if n not in layer and n.lstrip("-") not in layer]
    return sorted(set(miss))


def caption_only(o, text):
    """A table part without a grid is accepted only as a caption- or footnote-only part (e.g. the caption printed on one
    page and the body on another): short, and every number in it visible in its caption or the page text layer."""
    if "|" in o["transcription"] or "```" in o["transcription"] or len(o["transcription"]) > 800: return False  # code blocks: code_listing only
    seen = {norm_num(m.group(0)) for m in NUM.finditer((text or "") + " " + o["caption"])}
    return all(norm_num(m.group(0)) in seen for m in NUM.finditer(o["transcription"]))


def code_listing(o, text):
    """A table printed as a single cell of program code (e.g. HTML generated by a model) may be given as a fenced code
    block instead of a grid, only if the code is found verbatim (ignoring whitespace) in the page text layer."""
    m = re.fullmatch(r"(.{0,300}?)```[\w-]*\n(.*?)\n```(.{0,300})", o["transcription"], re.S)
    if not m or "|" in m.group(1) + m.group(3): return False  # at most a short description around one code block
    squash = lambda t: re.sub(r"\s+", "", t or "")
    code = squash(m.group(2))
    return len(code) >= 20 and code in squash(text)


def valid(res, text=""):
    if not isinstance(res, dict) or not isinstance(res.get("objects"), list): return "no objects list"
    for o in res["objects"]:
        if set(o) != set(SCHEMA["properties"]["objects"]["items"]["required"]) or o["kind"] not in KINDS: return "bad object"
        if o["kind"] in ("TABLE", "TABLE_AS_IMAGE") and "|" not in o["transcription"] and not caption_only(o, text) and not code_listing(o, text):
            return "table without Markdown grid"
    return ""


def codex_home(d):
    """A fresh CODEX_HOME for one call containing only a copy of auth.json (no state shared between concurrent calls)."""
    h = os.path.join(d, "codex_home"); os.makedirs(h)
    shutil.copy2(os.path.expanduser("~/.codex/auth.json"), os.path.join(h, "auth.json"))
    return h


RAW = None  # OUT/raw directory, set in main
ON_APPEND = None  # optional callback after each record is appended (under the writer lock)


def keep_raw(tag, who, stdout, meta):
    """Keep the raw CLI output; the file name and its checksum are recorded in the call metadata (lineage)."""
    if RAW:
        fn = os.path.join(RAW, f"{tag.replace('/', '_').replace('@', '_')}-{who}-{time.time_ns()}-{os.getpid()}-{threading.get_ident()}.json.gz")
        with gzip.open(fn, "wt") as f:
            json.dump(dict(meta={k: v for k, v in meta.items() if k not in ("raw_file", "raw_sha256")}, stdout=stdout), f)
        meta.update(raw_file=os.path.basename(fn), raw_sha256=hashlib.sha256(open(fn, "rb").read()).hexdigest())
    if isinstance(meta.get("request"), dict):  # the full prompt stays in the raw file only; the record keeps its checksum
        meta["request"] = {k: v for k, v in meta["request"].items() if k != "prompt"}


def _call(who, prompt, png, tag, meta_out, schema=None):
    """One isolated call. Returns (result, error, meta)."""
    cfg = SCREENERS[who]; d = tempfile.mkdtemp(prefix=f"{tag.replace('/', '_')}-{who}-", dir=WORK); t0 = time.time(); meta = meta_out
    schema = SCHEMA if schema is None else schema  # per-call schema (no shared global is changed)
    h = lambda x: hashlib.sha256(x.encode()).hexdigest()
    meta["request"] = dict(tag=tag, assessor=who, model=cfg["model"], effort=cfg["effort"], prompt=prompt, prompt_sha256=h(prompt),
                           schema_sha256=h(json.dumps(schema, sort_keys=True)), png_sha256=sha_file(png))  # request identity, kept in the raw file
    try:
        if who == "claude":
            msg = {"type": "user", "message": {"role": "user", "content": [
                {"type": "image", "source": {"type": "base64", "media_type": "image/png", "data": base64.b64encode(open(png, "rb").read()).decode()}},
                {"type": "text", "text": prompt}]}}
            cmd = ["claude", "-p", "--safe-mode", "--model", cfg["model"], "--effort", cfg["effort"], "--tools", "", "--setting-sources", "",
                   "--strict-mcp-config", "--no-session-persistence", "--input-format", "stream-json", "--output-format", "stream-json",
                   "--verbose", "--json-schema", json.dumps(schema)]
            p = subprocess.run(cmd, input=json.dumps(msg) + "\n", capture_output=True, text=True, cwd=d, timeout=3600)
            ev = [json.loads(l) for l in p.stdout.splitlines() if l.startswith("{")]
            r = [e for e in ev if e.get("type") == "result"]
            meta.update(seconds=round(time.time() - t0, 1), exit=p.returncode, event_types=sorted({e.get("type") for e in ev}),
                        models=list((r[-1].get("modelUsage") or {}).keys()) if r else [])
            keep_raw(tag, who, p.stdout, meta)
            if p.returncode or not r: return None, f"claude exit {p.returncode}: {(p.stderr or p.stdout)[-300:]}"
            r = r[-1]
            if r.get("is_error") or r.get("subtype") != "success": return None, f"claude error: {str(r.get('result'))[:300]}"
            if cfg["model"] not in (r.get("modelUsage") or {}): return None, f"claude: unexpected models {list((r.get('modelUsage') or {}))}"
            return r.get("structured_output"), None
        img = os.path.join(d, "page.png"); shutil.copy2(png, img)
        sf = os.path.join(d, "schema.json"); json.dump(schema, open(sf, "w")); of = os.path.join(d, "out.json")
        cmd = ["codex", "exec", "--ignore-user-config", "--ignore-rules", "--skip-git-repo-check", "--ephemeral", "-s", "read-only", "-C", d,
               "-m", cfg["model"], "-c", f'model_reasoning_effort="{cfg["effort"]}"', "--output-schema", sf, "-o", of, "--json", "-i", img]
        for f in CODEX_DISABLE: cmd += ["--disable", f]
        cmd += ["-c", "project_doc_max_bytes=0", "-c", "memories.use_memories=false", "-c", "memories.generate_memories=false", "-c", 'web_search="disabled"']
        h = codex_home(d)
        p = subprocess.run(cmd + ["-"], input=prompt, capture_output=True, text=True, cwd=d, timeout=3600, env=dict(os.environ, CODEX_HOME=h))
        meta.update(seconds=round(time.time() - t0, 1), exit=p.returncode)
        if p.returncode: return None, f"codex exit {p.returncode}: {(p.stderr or p.stdout)[-300:]}"
        ev = []
        for l in p.stdout.splitlines():
            try: ev.append(json.loads(l))
            except Exception: pass
        types = [e.get("type") for e in ev]
        meta.update(event_types=sorted(set(types)), item_types=sorted({e.get("item", {}).get("type") for e in ev if str(e.get("type", "")).startswith("item.")} - {None}))
        keep_raw(tag, who, p.stdout, meta)
        if "turn.completed" not in types or "turn.failed" in types: return None, f"codex: turn not completed ({types[-3:]})"
        tools = sorted({e["item"].get("type") for e in ev if str(e.get("type", "")).startswith("item.") and e.get("item", {}).get("type") not in ("agent_message", "reasoning")})
        if tools: return None, f"codex: tool events {tools}"
        return json.load(open(of)), None
    except Exception as e:
        return None, f"{who}: {e!r}"[:300]
    finally:
        shutil.rmtree(d, ignore_errors=True)


def call(who, prompt, png, tag):
    meta = dict(png_sha256=sha_file(png))
    res, err = _call(who, prompt, png, tag, meta)
    return res, err, meta


def sha_file(p):
    return hashlib.sha256(open(p, "rb").read()).hexdigest()


def build_prompt(who, page, title, stage, prev):
    """The prompt of one transcription call (before any retry note)."""
    if stage == "initial":
        prompt = PROMPT_1.format(title=title, source=page["source_file"], page=page["page"], text=page["text"][:12000])
    elif stage == "challenge":
        prompt = PROMPT_C.format(title=title, source=page["source_file"], page=page["page"],
                                 agreed=json.dumps(prev["agreed"], ensure_ascii=False, indent=1), text=page["text"][:12000])
    else:
        mine, other = prev[who], prev["codex" if who == "claude" else "claude"]
        prompt = PROMPT_R.format(title=title, source=page["source_file"], page=page["page"], diff=prev["diff"],
                                 a=json.dumps(mine, ensure_ascii=False, indent=1), b=json.dumps(other, ensure_ascii=False, indent=1), text=page["text"][:12000])
    return prompt


def run_one(who, page, title, stage, prev):
    """One validated transcription (up to 3 attempts; a text-layer miss gets one corrective retry)."""
    prompt = build_prompt(who, page, title, stage, prev)
    note, errs, metas = "", [], []
    for attempt in range(3):
        res, err, meta = call(who, prompt + note, page["png"], f"{page['page_id']}@{stage}"); metas.append(dict(meta, error=err))
        if err: errs.append(err); continue
        v = valid(res, page["text"])
        if v: errs.append(v); continue
        miss = text_check(res["objects"], page["text"])
        if miss and not note:
            note = RETRY.format(nums=", ".join(miss[:60])); errs.append(f"text-layer miss {len(miss)}"); continue
        part = [o["label"] for o in res["objects"] if o["kind"] in ("TABLE", "TABLE_AS_IMAGE") and "|" not in o["transcription"]]
        return dict(objects=res["objects"], text_layer_missing=miss, attempts=attempt + 1, errors=errs, calls=metas,
                    caption_only_tables=part), None
    return dict(calls=metas), "; ".join(errs)[-500:]


def config():
    """Everything that determines a transcription call, hashed component by component."""
    cli = lambda c: subprocess.run(c, capture_output=True, text=True).stdout.strip()
    parts = dict(rules=RULES, prompt_initial=PROMPT_1, prompt_reconcile=PROMPT_R, retry=RETRY, schema=json.dumps(SCHEMA, sort_keys=True),
                 screeners=json.dumps(SCREENERS, sort_keys=True), codex_disable=json.dumps(CODEX_DISABLE),
                 prompt_challenge=PROMPT_C,
                 stage_policy=json.dumps(dict(main=MAIN, challenge=CHALLENGE, risk=sorted(RISK))),
                 compare_code=open(os.path.join(ROOT, "tools/oct_search/visual_compare.py")).read(),
                 scheduler_code=inspect.getsource(main_agreed) + inspect.getsource(needs_reconcile) + inspect.getsource(main),
                 status_code=open(os.path.join(ROOT, "tools/oct_search/visual_status.py")).read(),
                 call_code=inspect.getsource(_call) + inspect.getsource(codex_home), check_code=inspect.getsource(valid) + inspect.getsource(caption_only) + inspect.getsource(code_listing) + inspect.getsource(text_check) + inspect.getsource(run_one),
                 claude_cli=cli(["claude", "--version"]), codex_cli=cli(["codex", "--version"]))
    return {k: hashlib.sha256(v.encode()).hexdigest() for k, v in parts.items()}, {k: parts[k] for k in ("claude_cli", "codex_cli")}


def inventory(pages):
    return {p["page_id"]: dict(png=sha_file(p["png"]), text=hashlib.sha256(p["text"].encode()).hexdigest()) for p in pages}


def check_manifest(out, pages, amend):
    """Create the manifest on the first run; afterwards refuse changed inputs or configuration unless amended.
    Pages may be added by an amendment; a page already in the manifest must keep its PNG and text hashes."""
    mf = os.path.join(out, "manifest.json"); cfg, versions = config(); inv = inventory(pages)
    now = datetime.datetime.now().astimezone().isoformat(timespec="seconds")
    if not os.path.exists(mf):
        json.dump(dict(created=now, config=cfg, versions=versions, pages=inv, amendments=[]), open(mf, "w"), indent=1)
        return
    m = json.load(open(mf))
    changed_cfg = sorted(k for k in cfg if m["config"].get(k) != cfg[k])
    changed_pages = sorted(k for k in inv if k in m["pages"] and m["pages"][k] != inv[k])
    new_pages = sorted(k for k in inv if k not in m["pages"])
    if changed_pages:
        sys.exit(f"page image or text changed for {len(changed_pages)} pages already transcribed (e.g. {changed_pages[:3]}); refusing")
    if changed_cfg or new_pages:
        if not amend:
            sys.exit(f"configuration changed {changed_cfg} / {len(new_pages)} new pages; rerun with --amend 'reason'")
        m["amendments"].append(dict(ts=now, reason=amend, config_changed={k: [m["config"].get(k), cfg[k]] for k in changed_cfg},
                                    pages_added=len(new_pages)))
        m["config"] = cfg; m["versions"] = versions; m["pages"].update({k: inv[k] for k in new_pages})
        json.dump(m, open(mf + ".tmp", "w"), indent=1); os.replace(mf + ".tmp", mf)


def main_agreed(done, pid):
    """Objects agreed in the main rounds (Claude's version at the first stage needing no further round), else None."""
    for s in MAIN:
        pr = done.get((pid, s), {})
        if len(pr) < 2 or not all(x.get("objects") is not None for x in pr.values()): return None
        if not needs_reconcile(pr): return pr["claude"]["objects"]
    return None


def needs_reconcile(pr):
    """Differences that send a page to the next round: comparison differences and table numbers absent from the text layer."""
    diff, _ = compare(pr["claude"]["objects"], pr["codex"]["objects"])
    tl = [f"{'A' if w == 'claude' else 'B'}: table numbers not found in the page text layer: {', '.join(pr[w]['text_layer_missing'][:40])}"
          for w in ("claude", "codex") if pr[w].get("text_layer_missing")]
    return "\n".join(x for x in [diff] + tl if x)


def main():
    global RAW
    ap = argparse.ArgumentParser(); ap.add_argument("out"); ap.add_argument("stage", choices=STAGES)
    ap.add_argument("--records", default=""); ap.add_argument("--workers", type=int, default=4)
    ap.add_argument("--pages", default="results/oct_search/visual/pages.jsonl"); ap.add_argument("--amend", default=""); a = ap.parse_args()
    os.makedirs(a.out, exist_ok=True); jl = os.path.join(a.out, "visual_rounds.jsonl")
    RAW = os.path.join(a.out, "raw"); os.makedirs(RAW, exist_ok=True)
    import csv
    titles = {r["record_id"]: r["title"] for r in csv.DictReader(open("results/oct_search/candidates_ledger.tsv"), delimiter="\t")}
    want = set(filter(None, a.records.split(",")))
    pages = [p for p in map(json.loads, open(a.pages)) if p["selected"] and (not want or p["record_id"] in want)]
    check_manifest(a.out, pages, a.amend)
    done = collections.defaultdict(dict)
    if os.path.exists(jl):
        for l in open(jl):
            r = json.loads(l)
            if r["objects"] is not None or r["assessor"] not in done[(r["page_id"], r["stage"])]:
                done[(r["page_id"], r["stage"])][r["assessor"]] = r
    todo = []
    for p in pages:
        if a.stage == "initial":
            prev = None
        elif a.stage == "challenge":
            ag = main_agreed(done, p["page_id"])
            if ag is None or not (ag or RISK & set(p.get("reasons", []))): continue  # agreed pages with an object or a risk flag
            prev = dict(agreed=ag)
        else:
            k = STAGES.index(a.stage); pst = STAGES[k - 1]; pr = done.get((p["page_id"], pst), {})
            if len(pr) < 2 or not all(x.get("objects") is not None for x in pr.values()):
                continue
            diff = needs_reconcile(pr)
            if not diff: continue
            prev = dict(claude=pr["claude"]["objects"], codex=pr["codex"]["objects"], diff=diff)
        for who in ("claude", "codex"):
            if who not in done.get((p["page_id"], a.stage), {}) or done[(p["page_id"], a.stage)][who].get("objects") is None:
                todo.append((who, p, prev))
    if a.stage == "challenge":  # the challenge scope is derived after reconcile-3 and recorded (same on every pass)
        scope = []
        for p in pages:
            ag = main_agreed(done, p["page_id"])
            if ag is None: continue
            stage = next(s for s in MAIN if not needs_reconcile(done[(p["page_id"], s)]))
            risk = sorted(RISK & set(p.get("reasons", [])))
            scope.append(dict(page_id=p["page_id"], main_stage=stage, objects=len(ag), risk_flags=risk,
                              challenged=bool(ag or risk), reason="table or figure agreed" if ag else ("risk flag" if risk else "agreed empty, no risk flag: skipped")))
        sf = os.path.join(a.out, "challenge_scope.jsonl"); txt = "".join(json.dumps(x) + "\n" for x in scope)
        if os.path.exists(sf) and open(sf).read() != txt: sys.exit("challenge scope differs from the recorded scope; refusing")
        open(sf, "w").write(txt)
        print(f"challenge scope: {sum(x['challenged'] for x in scope)} challenged, {sum(not x['challenged'] for x in scope)} skipped", flush=True)
    print(f"{a.stage}: {len(todo)} calls", flush=True)
    lock = threading.Lock()

    def work(t):
        who, p, prev = t
        res, err = run_one(who, p, titles[p["record_id"]], a.stage, prev)
        ok = err is None
        rec = dict(page_id=p["page_id"], record_id=p["record_id"], stage=a.stage, assessor=who, model=SCREENERS[who]["model"],
                   ts=datetime.datetime.now().astimezone().isoformat(timespec="seconds"), objects=res["objects"] if ok else None,
                   text_layer_missing=res["text_layer_missing"] if ok else None, attempts=res["attempts"] if ok else 3,
                   errors=res["errors"] if ok else [err], calls=res["calls"], diff_given=(prev or {}).get("diff"),
                   caption_only_tables=res.get("caption_only_tables") if ok else None)
        with lock:
            line = json.dumps(rec, ensure_ascii=False) + "\n"
            open(jl, "a").write(line)
            if ON_APPEND: ON_APPEND(jl, line)  # e.g. a per-record history checkpoint (crop runs)
        return who, p["page_id"], ok
    n = 0
    with cf.ThreadPoolExecutor(a.workers * 2) as ex:
        for who, pid, ok in ex.map(work, todo):
            n += 1
            if n % 20 == 0 or not ok: print(n, who, pid, "ok" if ok else "FAILED", flush=True)
    print("done", a.stage, flush=True)


if __name__ == "__main__":
    main()
