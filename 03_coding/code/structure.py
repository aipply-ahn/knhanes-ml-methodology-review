"""Structured form of the final crop transcriptions (run2_crops), so that the two transcriptions are compared field by
field and not as free text (a difference in layout is then no difference).
- Tables: the Markdown grid is parsed deterministically: caption, header row(s), body rows (cells), notes.
- Figures: the three-section text is converted into a fixed JSON schema (FIG_SCHEMA) by one isolated text-only call
  (claude -p, no tools, no image, the same converter for both transcriptions). The converter copies values exactly;
  a conversion is accepted only if it is lossless for numbers (every number of the text occurs at least as often in the
  JSON, which has no number that the text lacks; shared values may be repeated per panel) and its printed fields (labels, titles, axes, legend, other printed text, printed values) add no word that the
  text does not contain (refers_to, position, plot type and description may be worded by the converter); otherwise it is retried once with the reason, then recorded
  as failed (the unit then falls back to the text comparison).
Outputs: OUT/structured.jsonl (one line per unit and transcription: unit_id, which = claude | codex, data, error,
call metadata; raw CLI outputs in OUT/raw_structure). Usage: structure.py RUN OUT [--workers N] [--only UNIT,...] [--agreed]
--agreed (2026-11-15, object-file migration): units whose two transcriptions gave no item to adjudicate (no hunks, any
status) were never converted; their transcription 1 (the final version) is converted the same way and written to
OUT/structured_agreed.jsonl (never read by the adjudication server)."""
import concurrent.futures as cf, hashlib, json, os, re, subprocess, sys, tempfile, threading, time
HERE = os.path.dirname(os.path.abspath(__file__)); sys.path.insert(0, HERE)
import adjudication_diff as D

STR = {"type": "string"}
LIST = {"type": "array", "items": STR}
PAIR = {"type": "array", "items": {"type": "object", "additionalProperties": False, "required": ["refers_to", "value"],
                                    "properties": {"refers_to": STR, "value": STR}}}
FIG_SCHEMA = {"type": "object", "additionalProperties": False, "required": ["panels"], "properties": {"panels": {"type": "array", "items": {
    "type": "object", "additionalProperties": False,
    "required": ["label", "position", "title", "plot_type", "axes", "legend", "printed_values", "other_printed_text", "description", "approximate_readings"],
    "properties": {"label": STR, "position": STR, "title": STR, "plot_type": STR,
                   "axes": {"type": "array", "items": {"type": "object", "additionalProperties": False, "required": ["axis", "title", "ticks"],
                                                      "properties": {"axis": STR, "title": STR, "ticks": LIST}}},
                   "legend": LIST, "printed_values": PAIR, "other_printed_text": LIST, "description": STR, "approximate_readings": PAIR}}}}}
CONVERT = """Convert the transcription of a figure below into JSON with the given schema. This is a mechanical
restructuring: copy every printed value, label and number exactly as written (same characters, same signs, same
notation); do not add, drop, correct, translate or reinterpret anything.
- panels: one entry per panel in reading order (left to right, top to bottom); a figure without panels has one entry.
  label = the printed panel letter or number ("" if none); position = the panel's position as stated (e.g. "top left",
  "" if not stated); title = the panel's printed title ("" if none). Information given for all panels (e.g. a shared
  axis title) is repeated in every panel.
- plot_type: the kind of plot as stated (e.g. "forest plot", "ROC curve").
- axes: one entry per axis (axis = "x", "y", "y right", ...), with its printed title and its tick labels in order.
- legend: the legend entries in order. printed_values: every value printed inside the plot or in annotations, with
  what it refers to (refers_to) as stated in the transcription. other_printed_text: any other printed text.
- description: the transcriber's own description of what is drawn (not printed text), joined into one string.
- approximate_readings: every value read from positions (written with ~), with what it refers to.

Transcription:
{text}"""
NUM = re.compile(r"\d+(?:[.,]\d+)*")
LOCK = threading.Lock()


def nums(s):
    return sorted(NUM.findall(s))


def words(s):
    return {w.lower() for w in re.findall(r"[^\W\d_]+", s)}


def strings(x):
    if isinstance(x, str): yield x
    elif isinstance(x, dict):
        for v in x.values(): yield from strings(v)
    elif isinstance(x, list):
        for v in x: yield from strings(v)


def lossless(text, data):
    """None if the conversion keeps every number exactly once and adds no word; else the reason."""
    body = "\n".join(strings(data))
    PRINTED = ("label", "title", "axes", "legend", "other_printed_text")  # words are checked in printed fields only
    # the axis name of an axis entry (x, y, angular, radial ...) is the converter's descriptor, not print (2026-11-14)
    pr = lambda p, k: [dict(title=a.get("title"), ticks=a.get("ticks")) for a in p.get("axes") or []] if k == "axes" else p.get(k)
    wbody = "\n".join(strings([[pr(p, k) for k in PRINTED] + [v["value"] for v in p.get("printed_values", [])] for p in data.get("panels", [])]))
    src = re.sub(r"(?m)^(Printed values|Axes and labels|Approximate readings):", "", text)
    import collections
    ca, cb = collections.Counter(nums(src)), collections.Counter(nums(body))
    miss, new = sorted((ca - cb).elements()), sorted(set(cb) - set(ca))  # repetition of shared values across panels is allowed
    if miss or new: return f"numbers differ: missing {miss[:12]}, not in the transcription {new[:12]}"
    extra = words(wbody) - words(text)  # no exemptions in printed fields (Codex ALPHA-02, 2026-11-14); descriptor fields are not checked
    if extra: return f"words not in the transcription: {sorted(extra)[:12]}"
    return None


def parse_table(o):
    """Markdown grid -> header rows, body rows, notes (lines outside the grid)."""
    rows, notes = [], []
    for l in o["transcription"].splitlines():
        s = l.strip()
        if s.startswith("|"):
            cells = [c.strip() for c in s.strip("|").split("|")]
            if all(re.fullmatch(r":?-{2,}:?", c) for c in cells if c) and any(cells): rows.append(None); continue
            rows.append(cells)
        elif s: notes.append(s)
    if None in rows:
        k = rows.index(None); header, body = rows[:k], [r for r in rows[k + 1:] if r is not None]
    else:
        header, body = [], [r for r in rows if r is not None]
    return dict(type="table", label=o["label"], caption=o.get("caption") or "", header=header, rows=body, notes=notes)


def claude_text(prompt, schema, tag, raw_dir):
    """One isolated text-only call (no tools, no settings, no session); raw output kept. Returns (data, error, meta)."""
    d = tempfile.mkdtemp(prefix="struct-"); t0 = time.time()
    cmd = ["claude", "-p", "--safe-mode", "--model", "claude-opus-5-5", "--effort", "medium", "--tools", "", "--setting-sources", "",
           "--strict-mcp-config", "--no-session-persistence", "--output-format", "stream-json", "--verbose", "--json-schema", json.dumps(schema)]
    h = lambda x: hashlib.sha256(x.encode()).hexdigest()
    meta = dict(tag=tag, model="claude-opus-5-5", effort="medium", prompt_sha256=h(prompt), schema_sha256=h(json.dumps(schema, sort_keys=True)))
    try:
        p = subprocess.run(cmd, input=prompt, capture_output=True, text=True, cwd=d, timeout=1800)
        fn = os.path.join(raw_dir, f"{tag.replace('/', '_').replace('#', '_')}-{time.time_ns()}.json")
        with open(fn, "w") as f: json.dump(dict(meta=meta, prompt=prompt, stdout=p.stdout), f)
        meta.update(raw_file=os.path.basename(fn), seconds=round(time.time() - t0, 1), exit=p.returncode)
        ev = [json.loads(l) for l in p.stdout.splitlines() if l.startswith("{")]
        r = [e for e in ev if e.get("type") == "result"]
        if p.returncode or not r or r[-1].get("is_error"): return None, f"claude exit {p.returncode}: {(p.stderr or p.stdout)[-200:]}", meta
        return r[-1].get("structured_output"), None, meta
    except Exception as e:
        return None, repr(e)[:200], meta
    finally:
        import shutil; shutil.rmtree(d, ignore_errors=True)


def convert_figure(o, tag, raw_dir):
    text = o["transcription"]; prompt = CONVERT.format(text=text); calls = []
    for attempt in range(2):
        data, err, meta = claude_text(prompt, FIG_SCHEMA, tag, raw_dir); calls.append(meta)
        if err: return None, err, calls
        why = lossless(text, data)
        if not why: return dict(type="figure", label=o["label"], caption=o.get("caption") or "", **data), None, calls
        prompt = CONVERT.format(text=text) + f"\n\nYour previous conversion was not exact ({why}). Convert again, copying every value exactly once."
    return None, f"not lossless: {why}", calls


def _aff(out):
    """{unit: source tag} for re-transcribed units; their earlier structured records are ignored."""
    f, g = os.path.join(out, "cropbox_affected_units.json"), os.path.join(out, "alpha_affected.json")
    d = {u: "run3_cropfix" for u in (json.load(open(f)) if os.path.exists(f) else [])}
    if os.path.exists(g): d.update({u: "run4_alphafix" for u in json.load(open(g))["units"]})
    return d


def load(out):
    S = {}; A = _aff(out)
    f = os.path.join(out, "structured.jsonl")
    if os.path.exists(f):
        for l in open(f):
            r = json.loads(l)
            if r["unit_id"] in A and r.get("src") != A[r["unit_id"]]: continue  # made from the cut crop's transcription
            if r["data"] is not None or (r["unit_id"], r["which"]) not in S: S[(r["unit_id"], r["which"])] = r
    return S


def main():
    run, out = sys.argv[1], sys.argv[2]
    only = set(sys.argv[sys.argv.index("--only") + 1].split(",")) if "--only" in sys.argv else None
    workers = int(sys.argv[sys.argv.index("--workers") + 1]) if "--workers" in sys.argv else 8
    raw = os.path.join(out, "raw_structure"); os.makedirs(raw, exist_ok=True)
    fin = [json.loads(l) for l in open(os.path.join(run, "unit_final.jsonl"))]
    agreed = "--agreed" in sys.argv; target = "structured_agreed.jsonl" if agreed else "structured.jsonl"
    S = load(out); jobs = []
    if agreed:
        S = {}
        if os.path.exists(os.path.join(out, target)):
            for l in open(os.path.join(out, target)):
                r = json.loads(l)
                if r["data"] is not None: S[(r["unit_id"], r["which"])] = r
    for u in fin:
        if only and u["unit_id"] not in only: continue
        if agreed:
            if u["status"] in ("UNRESOLVED", "NEEDS_REVIEW") and D.hunks(u)[2]: continue
            if (u["unit_id"], "claude") not in S and u.get("claude"): jobs.append((u, "claude"))
            continue
        if u["status"] not in ("UNRESOLVED", "NEEDS_REVIEW"): continue
        if not D.hunks(u)[2]: continue
        for w in ("claude", "codex"):
            if (u["unit_id"], w) in S and S[(u["unit_id"], w)]["data"] is not None: continue
            jobs.append((u, w))
    print(f"structure: {len(jobs)} transcriptions", flush=True)

    def one(j):
        u, w = j; objs, errs, calls = [], [], []
        for k, o in enumerate(u.get(w) or []):
            if o["kind"] in ("TABLE", "TABLE_AS_IMAGE"): objs.append(parse_table(o)); continue
            d, e, c = convert_figure(o, f"{u['unit_id']}-{w}-{k}", raw); calls += c
            if e: errs.append(e)
            else: objs.append(d)
        rec = dict(unit_id=u["unit_id"], which=w, data=None if errs else objs, error="; ".join(errs) or None, calls=calls)
        if u["unit_id"] in _aff(out): rec["src"] = _aff(out)[u["unit_id"]]
        with LOCK, open(os.path.join(out, target), "a") as f: f.write(json.dumps(rec, ensure_ascii=False) + "\n")
        return rec["error"]

    with cf.ThreadPoolExecutor(workers) as ex:
        errs = [e for e in ex.map(one, jobs) if e]
    print(f"done structure: {len(jobs) - len(errs)} ok, {len(errs)} failed", flush=True)


if __name__ == "__main__":
    main()
