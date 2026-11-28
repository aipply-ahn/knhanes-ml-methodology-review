"""Re-reading of crop units (visual_crop.py) with the run1 procedure: same prompts, schema, models, isolation, checks,
stages (initial, reconcile-1..3, challenge, challenge-reconcile-1..3) and manifest mechanism, with these crop-specific
parts, all bound in the run manifest (config components crop_*):
- a note after the report title: the image is a crop of one object (or panel), transcribe only it, with writing
  conventions (powers of ten, superscripts, multi-row headings, merged cells, no figure number in the text, figures in
  three sections 'Printed values' / 'Axes and labels' / 'Approximate readings', tables only grid and printed notes);
- comparison by visual_crop_compare.compare_unit (scheduling, challenge scope and final status use the same function);
- the text-layer check ignores one-digit integers (footnote and superscript markers);
- the inventory binds each unit's crop image, page text and the full unit record (source file, page, reasons, crop
  metadata: label, kind, panel, box, flags, source checksum, locator references); a resumed run refuses changed, added
  (without --amend) or removed units;
- the configuration also binds the build manifest (locate records, units, coverage, crop and source checksums), the
  assembler, driver, status and guard code; before every stage the frozen build is re-verified (visual_crop.verify_build).
A run directory of run1 is refused.
Usage: visual_crop_run.py RUN_DIR STAGE --pages RUN_DIR/units.jsonl [--workers N] [--amend TEXT]"""
import hashlib, inspect, json, os, re, sys
HERE = os.path.dirname(os.path.abspath(__file__)); sys.path.insert(0, HERE)
import visual_run as V
import visual_crop_compare as CC

CROP_NOTE = ("\n\nThe image is a crop of a single object from {source}, page {page}: {label} ({kind}){panel}. Transcribe "
             "this object only, as a list with this one object (use the label {use_label}); the text layer below is that of "
             "the whole page and may contain other text. If the crop does not show this object, return an empty list."
             "\n\nWriting conventions for this transcription (so that two independent transcriptions can be compared): "
             "write powers of ten as x10^-5 (caret and minus sign, no superscript characters); write any other superscript "
             "or subscript text after a caret or underscore in parentheses, e.g. 1.2^(a), Cluster 1^(1)); keep asterisks as printed; "
             "for column headings on several rows give one heading row in which each column's heading levels are joined "
             "with ' / ' from top to bottom; repeat a merged cell's content in every row or column it spans; do not "
             "write the figure or table number or the panel letter inside the transcription other than in the label. "
             "For a figure, write the transcription in three sections, each starting with its heading on its own line: "
             "'Printed values:' every number printed inside the plot area, on bars, points, boxes or nodes, in the legend "
             "or in annotations (e.g. AUC = 0.81, n = 120, p < 0.001), each with what it refers to; "
             "'Axes and labels:' figure type, axis titles, tick labels, legend entries and other printed text; "
             "'Approximate readings:' values read from positions on the plot, each written with a leading ~ (may be empty). "
             "For a table, write only the grid and the notes printed under it; put any comment of your own in uncertain.")
_orig_run_one, _orig_text_check, _orig_config, _orig_inventory = V.run_one, V.text_check, V.config, V.inventory


def crop_title(page, title):
    """Report title followed by the crop note for this unit (the effective title used in every prompt)."""
    c = page["crop"]
    lab = c["label"] + (f" panel {c['panel']}" if c.get("panel") else "")
    return title + CROP_NOTE.format(source=page["source_file"], page=page["page"], label=c["label"], kind=c["kind"],
                                    panel=f", panel {c['panel']}" if c.get("panel") else "", use_label=f'"{lab}"')


def run_one(who, page, title, stage, prev):
    """The run1 call with the crop note; an output whose objects carry another label than the requested unit is not
    accepted (one more attempt, then the call fails and is retried in the next pass)."""
    c = page["crop"]; lab = c["label"] + (f" panel {c['panel']}" if c.get("panel") else "")
    title = crop_title(page, title)
    calls, errs = [], []
    for attempt in range(2):
        res, err = _orig_run_one(who, page, title, stage, prev)
        if err: return res, err
        calls += res["calls"]; errs += res["errors"]
        if CC.identity(res["objects"], c)[0]:
            return dict(res, calls=calls, errors=errs), None
        errs.append(f"identity mismatch: returned {[o['label'] for o in res['objects']]} for {lab}")
    return dict(calls=calls), "; ".join(errs)[-500:]


def text_check(objs, text):
    """As visual_run.text_check, ignoring one-digit integers (footnote and superscript markers)."""
    return [n for n in _orig_text_check(objs, text) if not re.fullmatch(r"-?\d", n)]


def config():
    c, v = _orig_config()
    shs = lambda s: hashlib.sha256(s.encode()).hexdigest()
    sha = lambda p: hashlib.sha256(open(p, "rb").read()).hexdigest()
    c.update(crop_note=shs(CROP_NOTE), crop_run_code=sha(__file__), crop_compare_code=sha(CC.__file__), crop_build_code=sha(os.path.join(HERE, "visual_crop.py")),
             crop_original_run_one=shs(inspect.getsource(_orig_run_one)), crop_original_text_check=shs(inspect.getsource(_orig_text_check)),
             crop_run1_final=sha(os.path.join(V.ROOT, "results/oct_search/visual/run1/visual_final.jsonl")),
             crop_run1_rounds=sha(os.path.join(V.ROOT, "results/oct_search/visual/run1/visual_rounds.jsonl")),
             **{f"crop_code_{n}": sha(os.path.join(HERE, n)) for n in ("visual_crop_assemble.py", "visual_crop_drive.sh", "visual_status.py", "visual_guard.py")},
             crop_build_manifest=sha(os.path.join(OUT, "build_manifest.json")) if OUT and os.path.exists(os.path.join(OUT, "build_manifest.json")) else "none",
             crop_visual_run_file=sha(V.__file__), crop_build_prompt=shs(inspect.getsource(V.build_prompt)),
             crop_lineage_file=sha(os.path.join(HERE, "visual_lineage.py")),
             crop_titles=titles_hash(), crop_lineage_code=shs(inspect.getsource(verify_lineage)) + sha(os.path.join(HERE, 'visual_lineage.py')))
    return c, v


def titles_hash():
    """Report titles used in the prompts (from the candidates ledger) for the records of the run's units."""
    import csv
    f = os.path.join(OUT, "units.jsonl") if OUT else ""
    if not f or not os.path.exists(f): return "none"
    rids = sorted({json.loads(l)["record_id"] for l in open(f)})
    t = {r["record_id"]: r["title"] for r in csv.DictReader(open(os.path.join(V.ROOT, "results/oct_search/candidates_ledger.tsv")), delimiter="\t") if r["record_id"] in rids}
    return hashlib.sha256(json.dumps(t, sort_keys=True, ensure_ascii=False).encode()).hexdigest()


def verify_lineage(out):
    """Transcription lineage (visual_lineage.check) and history: each accepted output backed by its own raw file whose
    full request is this unit, stage and assessor with the frozen model and effort, the transcription schema, the crop
    image and the prompt rebuilt from the records (visual_run.build_prompt with the crop title and the previous stage's
    accepted outputs), optionally followed by the run1 retry note; derived fields recomputed."""
    import csv, collections, visual_lineage
    visual_lineage.verify_history(out, "visual_rounds.jsonl")
    units = {json.loads(l)["page_id"]: json.loads(l) for l in open(os.path.join(out, "units.jsonl"))}
    titles = {r["record_id"]: r["title"] for r in csv.DictReader(open(os.path.join(V.ROOT, "results/oct_search/candidates_ledger.tsv")), delimiter="\t")}
    done = collections.defaultdict(dict)
    if os.path.exists(os.path.join(out, "visual_rounds.jsonl")):
        for l in open(os.path.join(out, "visual_rounds.jsonl")):
            r = json.loads(l)
            if r["objects"] is not None or r["assessor"] not in done[(r["page_id"], r["stage"])]: done[(r["page_id"], r["stage"])][r["assessor"]] = r

    def expect(r):
        u = units.get(r["page_id"]); st = r["stage"]
        if u is None: return None
        if st == "initial": prev = None
        elif st == "challenge":
            ag = V.main_agreed(done, r["page_id"])
            if ag is None: return None
            prev = dict(agreed=ag)
        else:
            pr = done.get((r["page_id"], V.STAGES[V.STAGES.index(st) - 1]), {})
            if len(pr) < 2 or any(x["objects"] is None for x in pr.values()): return None
            prev = dict(claude=pr["claude"]["objects"], codex=pr["codex"]["objects"], diff=V.needs_reconcile(pr))
        return V.build_prompt(r["assessor"], u, crop_title(u, titles[u["record_id"]]), st, prev)

    def derived(r):
        u = units[r["page_id"]]
        tl = text_check(r["objects"], u["text"])
        co = [o["label"] for o in r["objects"] if o["kind"] in ("TABLE", "TABLE_AS_IMAGE") and "|" not in o["transcription"]]
        return "" if tl == r.get("text_layer_missing") and co == r.get("caption_only_tables") else "derived fields differ from recomputation"
    retry = re.escape(V.RETRY).replace(re.escape("{nums}"), r"[^\n]*")
    return visual_lineage.check(out, "visual_rounds.jsonl", lambda r: f"{r['page_id']}@{r['stage']}",
                                lambda r: hashlib.sha256(open(units[r["page_id"]]["png"], "rb").read()).hexdigest() if r["page_id"] in units else None,
                                V.SCREENERS, V.SCHEMA, expect, retry, derived)


def inventory(pages):
    """Page inventory plus the full unit record (every field that enters the prompt, the comparison or the status)."""
    inv = _orig_inventory(pages)
    for p in pages:
        inv[p["page_id"]]["unit"] = hashlib.sha256(json.dumps(p, sort_keys=True, ensure_ascii=False).encode()).hexdigest()
    return inv


OUT = ""
V.run_one, V.text_check, V.config, V.inventory = run_one, text_check, config, inventory
V.compare = lambda a, b: CC.compare_unit(a, b)


def main():
    args = sys.argv[1:]
    out = os.path.normpath(args[0]) if args else ""
    from visual_guard import guard_tree
    guard_tree(out)
    global OUT
    OUT = out
    import visual_crop
    if os.path.exists(os.path.join(out, "build_manifest.json")): visual_crop.verify_build(out)
    elif os.environ.get("VISUAL_CROP_TEST") != "1": sys.exit("build_manifest.json missing; refusing (set VISUAL_CROP_TEST=1 only in isolated tests)")
    if os.path.exists(os.path.join(out, "visual_rounds.jsonl")) and not os.path.exists(os.path.join(out, "manifest.json")):
        sys.exit("transcription history exists without manifest.json; refusing (the manifest is never recreated)")
    verify_lineage(out)
    if "--pages" not in args: sys.exit("--pages RUN_DIR/units.jsonl is required")
    pages_file = args[args.index("--pages") + 1]
    mf = os.path.join(out, "manifest.json")
    if os.path.exists(mf) and "--records" not in args:  # removals are refused
        ids = {json.loads(l)["page_id"] for l in open(pages_file)}
        gone = sorted(set(json.load(open(mf))["pages"]) - ids)
        if gone: sys.exit(f"{len(gone)} units of the manifest are missing from {pages_file} (e.g. {gone[:3]}); refusing")
    import visual_lineage
    from visual_guard import safe_open
    V.ON_APPEND = lambda jl, line: visual_lineage.record_append(out, "visual_rounds.jsonl", line, safe_open)  # per-record checkpoint
    V.main()


if __name__ == "__main__":
    main()
