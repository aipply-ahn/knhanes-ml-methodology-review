"""Two-AI title/abstract screening (results/oct_search/screening/PROCESS.md), run one gated step at a time.

  screening_run.py init --out DIR [--pilot-ids FILE]   freeze the run (manifest.json) before any model call
  screening_run.py next --out DIR                      run the next step; refuses until the previous step is approved
  screening_run.py approve STEP --out DIR --by WHO --ref REF   record verification of a finished step (gates.jsonl)
  screening_run.py status --out DIR

Steps: initial-1 -> consensus-1..3 (while disagreements remain) -> challenge-1 (agreed exclusions) ->
challenge_consensus-1..3 -> final (decisions.csv, author_review.csv).
Screeners: Claude (claude -p) and Codex (codex exec), each called in a fresh empty directory outside the project with
customisations disabled (Claude --safe-mode, no tools, no setting sources; Codex with an isolated CODEX_HOME holding only
the login, user config and rules ignored, tool-capable features disabled, any tool use rejected), no session
persistence, JSON-schema output. A record's decision is written only when it passes every output check; otherwise the
record is requested again, and a step that cannot be completed stops with an execution error (nothing is written for
that record). Diagnostics of failed requests stay in the private work directory, not in the run directory."""
import argparse, collections, concurrent.futures as cf, csv, datetime, hashlib, html, json, os, re, shutil, subprocess, sys, tempfile, threading, time, unicodedata
ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
SCR = os.path.join(ROOT, "results/oct_search/screening")
WORK = "<work_dir_outside_project>"  # outside the project: no AGENTS.md, CLAUDE.md or project files
SCREENERS = {"claude": dict(model="claude-opus-5-5", effort="high"), "codex": dict(model="gpt-6.1-sol", effort="high")}
CODEX_DISABLE = ["apps", "plugins", "hooks", "browser_use", "browser_use_external", "in_app_browser", "computer_use", "skill_search", "memories"]
ISOLATION = dict(
    claude='claude -p --safe-mode --tools "" --setting-sources "" --strict-mcp-config --no-session-persistence --json-schema; cwd = fresh empty directory',
    codex="codex exec with CODEX_HOME = isolated directory containing only auth.json; --ignore-user-config --ignore-rules --ephemeral "
          "-s read-only --skip-git-repo-check; disabled features: " + ",".join(CODEX_DISABLE) + "; project_doc_max_bytes=0; memories "
          "off; web search disabled; --output-schema; cwd = fresh empty "
          "directory; outputs with any tool event are rejected")
BATCH, WORKERS, MAX_ATTEMPTS, EVIDENCE_WORDS = 20, 4, 4, 40
CODES = ("X1", "X2", "X3", "X4")
CODE_ORDER = ("X4", "X1", "X2", "X3")  # reported reason when the screeners agree to exclude with different codes
PROMPT_OF = {"initial": "round1", "consensus": "round_n", "challenge": "challenge", "challenge_consensus": "round_n"}
FIRST_OF = {"consensus": "initial", "challenge_consensus": "challenge"}
lock = threading.Lock()


def now():
    return datetime.datetime.now().astimezone().isoformat(timespec="seconds")


def sha(b):
    return hashlib.sha256(b if isinstance(b, bytes) else b.encode()).hexdigest()


def fsha(p):
    return sha(open(p, "rb").read())


def atomic_json(obj, path):
    tmp = path + ".tmp"; json.dump(obj, open(tmp, "w"), indent=1, ensure_ascii=False); os.replace(tmp, path)


def schema(reconsider):
    item = {"record_id": {"type": "string"}, "decision": {"type": "string", "enum": ["FULL_TEXT", "EXCLUDE_CERTAIN"]},
            "code": {"type": ["string", "null"], "enum": list(CODES) + [None]}, "evidence": {"type": "string"}, "reason": {"type": "string"}}
    if reconsider:
        item["response_to_other"] = {"type": "string"}
    return {"type": "object", "additionalProperties": False, "required": ["decisions"],
            "properties": {"decisions": {"type": "array", "items": {"type": "object", "additionalProperties": False,
                                                                     "required": list(item), "properties": item}}}}


# ---- output checks (the verifier re-implements these independently) ----
def norm(t):
    t = unicodedata.normalize("NFKC", t or "")
    for a, b in (("“", '"'), ("”", '"'), ("’", "'"), ("‘", "'"), ("–", "-"), ("—", "-")):
        t = t.replace(a, b)
    return re.sub(r"\s+", " ", t).strip().lower()


def evidence_parts(ev):
    return [p.strip(" .,;:\"'") for p in re.split(r"\s*(?:\.\.\.|…)\s*", ev or "") if p.strip(" .,;:\"'")]


HTML_TAGS = "h1|h2|h3|h4|h5|h6|i|b|em|strong|sub|sup|title|p|br|span|div|bold|italic|u|sc"
TAG = re.compile(r"</?(?:%s)\s*/?>" % HTML_TAGS, re.I)  # bare tags only (no tag in the input has attributes)


def display_text(t):
    """Text as displayed: markup tags of the listed formatting elements removed, then entities decoded; other '<' and
    '>' (e.g. 'p < 0.05', '<median') are kept."""
    return html.unescape(TAG.sub("", t or ""))


def squash(t):
    # matching ignores HTML markup and all whitespace: screening texts keep source markup (e.g. <i>n</i>&nbsp;=) and
    # PDF-extracted Korean abstracts contain spaces inside words; quotations need not reproduce either (amendment 1)
    return re.sub(r"\s+", "", norm(display_text(t)))


def evidence_found(ev, rec):
    hay = squash(rec["title"] + " " + rec["screening_text"]); parts = evidence_parts(display_text(ev))
    return bool(parts) and all(squash(p) in hay for p in parts)


def evidence_words(ev):
    return sum(len(p.split()) for p in evidence_parts(ev))


def problems(d, rec, reconsider):
    p = []
    if d.get("decision") not in ("FULL_TEXT", "EXCLUDE_CERTAIN"): p.append("decision")
    if d.get("decision") == "FULL_TEXT" and d.get("code") is not None: p.append("code with FULL_TEXT")
    if d.get("decision") == "EXCLUDE_CERTAIN" and d.get("code") not in CODES: p.append("code missing")
    if not isinstance(d.get("evidence"), str) or not d["evidence"].strip(): p.append("evidence empty")
    elif not evidence_found(d["evidence"], rec): p.append("evidence not verbatim")
    elif evidence_words(d["evidence"]) > EVIDENCE_WORDS: p.append("evidence too long")
    if not isinstance(d.get("reason"), str) or not d["reason"].strip(): p.append("reason empty")
    if reconsider and (not isinstance(d.get("response_to_other"), str) or not d["response_to_other"].strip()): p.append("response_to_other empty")
    if not reconsider and "response_to_other" in d: p.append("unexpected response_to_other")
    return p


# ---- screener calls ----
def codex_home():
    h = os.path.join(WORK, "codex_home")
    if not os.path.exists(os.path.join(h, "auth.json")):
        os.makedirs(h, exist_ok=True); shutil.copy2(os.path.expanduser("~/.codex/auth.json"), os.path.join(h, "auth.json"))
    extra = set(os.listdir(h)) - {"auth.json"}
    for x in extra:  # anything Codex wrote last time (logs, caches) is removed so each call starts from the same state
        p = os.path.join(h, x); shutil.rmtree(p) if os.path.isdir(p) else os.remove(p)
    return h


def call(screener, prompt, reconsider, tag):
    """One call in a fresh directory. Returns (parsed object, None) or (None, execution error)."""
    cfg = SCREENERS[screener]
    d = tempfile.mkdtemp(prefix=f"{tag}-", dir=os.path.join(WORK, "calls"))
    sch = schema(reconsider)
    if screener == "claude":
        cmd = ["claude", "-p", "--safe-mode", "--model", cfg["model"], "--effort", cfg["effort"], "--tools", "", "--setting-sources", "",
               "--strict-mcp-config", "--no-session-persistence", "--output-format", "json", "--json-schema", json.dumps(sch)]
        try:
            p = subprocess.run(cmd, input=prompt, capture_output=True, text=True, cwd=d, timeout=3600)
        except Exception as e:
            return None, f"claude: {e!r}"[:300]
        if p.returncode != 0:
            return None, f"claude exit {p.returncode}: {(p.stderr or p.stdout)[-300:]}"
        try:
            out = json.loads(p.stdout)
        except Exception:
            return None, "claude: stdout not JSON"
        if out.get("is_error") or out.get("subtype") not in (None, "success"):
            return None, f"claude error: {str(out.get('result'))[:300]}"
        models = list((out.get("modelUsage") or {}).keys())
        if cfg["model"] not in models:
            return None, f"claude: unexpected models {models}"
        res = out.get("structured_output")
        if res is None:
            try:
                res = json.loads(out.get("result") or "")
            except Exception:
                return None, "claude: no structured output"
        return res, None
    sf = os.path.join(d, "schema.json"); json.dump(sch, open(sf, "w")); of = os.path.join(d, "out.json")
    cmd = ["codex", "exec", "--ignore-user-config", "--ignore-rules", "--skip-git-repo-check", "--ephemeral", "-s", "read-only", "-C", d,
           "-m", cfg["model"], "-c", f'model_reasoning_effort="{cfg["effort"]}"', "--output-schema", sf, "-o", of, "--json"]
    for f in CODEX_DISABLE:
        cmd += ["--disable", f]
    cmd += ["-c", "project_doc_max_bytes=0", "-c", "memories.use_memories=false", "-c", "memories.generate_memories=false", "-c", 'web_search="disabled"']
    env = dict(os.environ, CODEX_HOME=codex_home_path)
    try:
        p = subprocess.run(cmd + ["-"], input=prompt, capture_output=True, text=True, cwd=d, timeout=3600, env=env)
    except Exception as e:
        return None, f"codex: {e!r}"[:300]
    if p.returncode != 0:
        return None, f"codex exit {p.returncode}: {(p.stderr or p.stdout)[-300:]}"
    ev = []
    for l in p.stdout.splitlines():
        try:
            ev.append(json.loads(l))
        except Exception:
            pass
    types = [e.get("type") for e in ev]
    if "turn.completed" not in types or "turn.failed" in types or "error" in types:
        return None, f"codex: turn not completed ({types[-3:]})"
    tools = sorted({e["item"].get("type") for e in ev if str(e.get("type", "")).startswith("item.") and e.get("item", {}).get("type") not in ("agent_message", "reasoning")})
    if tools:
        return None, f"codex: tool events {tools}"
    try:
        return json.load(open(of)), None
    except Exception:
        return None, "codex: no output file"


codex_home_path = None


# ---- run ----
class Run:
    def __init__(self, out):
        self.out = out
        self.mf = os.path.join(out, "manifest.json"); self.jl = os.path.join(out, "screening_rounds.jsonl"); self.gf = os.path.join(out, "gates.jsonl")
        if not os.path.exists(self.mf):
            if os.path.exists(self.jl):
                sys.exit("decisions exist without a manifest; refusing to continue")
            return
        self.m = json.load(open(self.mf))
        self.check_frozen()
        allin = [json.loads(l) for l in open(os.path.join(SCR, "screening_input.jsonl"))]
        self.inp = {r["record_id"]: r for r in allin if r["record_id"] in set(self.m["record_ids"])}
        self.elig = open(os.path.join(SCR, "ELIGIBILITY.md")).read()
        self.prompts = {k: open(os.path.join(SCR, "prompts", k + ".md")).read() for k in ("round1", "round_n", "challenge")}
        self.rows = [json.loads(l) for l in open(self.jl)] if os.path.exists(self.jl) else []
        ids = collections.Counter(r["decision_id"] for r in self.rows)
        assert all(v == 1 for v in ids.values()), "duplicate decision_id in screening_rounds.jsonl"
        for r in self.rows:
            assert r["record_id"] in self.inp and r["screener"] in SCREENERS and r["decision_id"] == f"{r['record_id']}-{r['stage']}-{r['round']}-{r['screener']}", r["decision_id"]
        self.by = {r["decision_id"]: r for r in self.rows}
        self.gates = [json.loads(l) for l in open(self.gf)] if os.path.exists(self.gf) else []

    @staticmethod
    def frozen_files():
        f = {"input": "results/oct_search/screening/screening_input.jsonl", "criteria": "results/oct_search/screening/ELIGIBILITY.md",
             "process": "results/oct_search/screening/PROCESS.md", "runner": "tools/oct_search/screening_run.py",
             "verifier": "tools/oct_search/screening_verify.py"}
        f.update({f"prompt_{k}": f"results/oct_search/screening/prompts/{k}.md" for k in ("round1", "round_n", "challenge")})
        return f

    def check_frozen(self):
        cur = {k: v["sha256"] for k, v in self.m["frozen"].items()}
        for a in self.m.get("amendments", []):  # documented, verified changes during the run
            cur.update(a["sha256"])
        for k, p in self.frozen_files().items():
            if fsha(os.path.join(ROOT, p)) != cur[k]:
                sys.exit(f"frozen file changed: {p}")
        for s, cfg in SCREENERS.items():
            if {k: self.m["screeners"][s][k] for k in ("model", "effort")} != cfg:
                sys.exit(f"screener settings changed: {s}")
            if subprocess.run([s, "--version"], capture_output=True, text=True).stdout.strip() != self.m["screeners"][s]["cli"]:
                sys.exit(f"CLI version changed: {s}")

    # steps are derived from the decisions already made
    def get(self, i, st, k, s):
        return self.by.get(f"{i}-{st}-{k}-{s}")

    def complete(self, st, k, ids):
        return all(self.get(i, st, k, s) for i in ids for s in SCREENERS)

    def agree(self, i, st, k):
        return self.get(i, st, k, "claude")["decision"] == self.get(i, st, k, "codex")["decision"]

    def plan(self):
        """Ordered steps known so far: list of (step_name, stage, round, ids); stops at the first incomplete step."""
        steps = []
        def stage(first, cons, ids):
            steps.append((f"{first}-1", first, 1, ids))
            if not self.complete(first, 1, ids):
                return None
            fixed = {i: (self.get(i, first, 1, "claude")["decision"], first, 1) for i in ids if self.agree(i, first, 1)}
            open_ = [i for i in ids if i not in fixed]
            for k in (1, 2, 3):
                if not open_:
                    break
                steps.append((f"{cons}-{k}", cons, k, open_))
                if not self.complete(cons, k, open_):
                    return None
                fixed.update({i: (self.get(i, cons, k, "claude")["decision"], cons, k) for i in open_ if self.agree(i, cons, k)})
                open_ = [i for i in open_ if i not in fixed]
            return fixed, open_
        r1 = stage("initial", "consensus", list(self.inp))
        if r1 is None:
            return steps, None
        excl = [i for i, v in r1[0].items() if v[0] == "EXCLUDE_CERTAIN"]
        r2 = stage("challenge", "challenge_consensus", excl) if excl else ({}, [])
        if r2 is None:
            return steps, None
        steps.append(("final", None, None, []))
        return steps, (r1, r2)

    def approved(self, step):
        return any(g["step"] == step for g in self.gates)

    def next(self):
        steps, res = self.plan()
        for name, st, k, ids in steps:
            done = name == "final" and os.path.exists(os.path.join(self.out, "decisions.csv")) or name != "final" and self.complete(st, k, ids)
            if done and self.approved(name):
                continue
            if done:
                sys.exit(f"step {name} finished; waiting for approval")
            prev = steps[steps.index((name, st, k, ids)) - 1][0] if steps.index((name, st, k, ids)) else None
            if prev and not self.approved(prev):
                sys.exit(f"previous step {prev} not approved")
            if name == "final":
                return self.finish(*res)
            return self.screen(name, st, k, ids)
        print("all steps finished and approved")

    def screen(self, name, stage, rnd, ids):
        global codex_home_path
        codex_home_path = codex_home()
        prompt_id = PROMPT_OF[stage]; reconsider = prompt_id == "round_n"
        run = next((x for x in self.m["runs"] if x["step"] == name), None)
        if run is None:
            run = dict(step=name, stage=stage, round=rnd, prompt_id=prompt_id, records=len(ids), started=now(), calls={}, rerequests={})
            self.m["runs"].append(run); atomic_json(self.m, self.mf)
        jobs = []
        for s in SCREENERS:
            todo = [i for i in ids if not self.get(i, stage, rnd, s)]
            jobs += [(s, todo[b:b + BATCH]) for b in range(0, len(todo), BATCH)]
        print(now(), name, "records", len(ids), "batches", len(jobs), flush=True)
        fails = []
        with cf.ThreadPoolExecutor(WORKERS * len(SCREENERS)) as ex:
            for f in ex.map(lambda j: self.batch(name, stage, rnd, prompt_id, reconsider, *j, run=run), jobs):
                fails += f
        run["last_attempt_finished"] = now()
        if not fails:
            run["finished"] = now()
        atomic_json(self.m, self.mf)
        if fails:
            sys.exit(f"step {name}: {len(fails)} decisions could not be obtained after {MAX_ATTEMPTS} requests; rerun 'next' to request them again")
        print(now(), name, "finished; awaiting verification", flush=True)

    def payload(self, rid, stage, rnd, screener, reconsider):
        r = self.inp[rid]; x = dict(record_id=rid, title=r["title"], text_source=r["text_source"], screening_text=r["screening_text"])
        if reconsider:
            pst, prd = (stage, rnd - 1) if rnd > 1 else (FIRST_OF[stage], 1)
            other = next(o for o in SCREENERS if o != screener)
            pick = lambda d: {k: d[k] for k in ("decision", "code", "evidence", "reason")}
            x["your_previous"] = pick(self.get(rid, pst, prd, screener)); x["other_previous"] = pick(self.get(rid, pst, prd, other))
        return x

    def batch(self, name, stage, rnd, prompt_id, reconsider, screener, ids, run):
        pending = list(ids)
        for attempt in range(1, MAX_ATTEMPTS + 1):
            if not pending:
                break
            recs = "\n".join(json.dumps(self.payload(i, stage, rnd, screener, reconsider), ensure_ascii=False) for i in pending)
            prompt = self.prompts[prompt_id].replace("{ELIGIBILITY}", self.elig).replace("{RECORDS}", recs)
            res, err = call(screener, prompt, reconsider, f"{name}-{screener}")
            with lock:
                run["calls"][screener] = run["calls"].get(screener, 0) + 1
                if attempt > 1:
                    run["rerequests"][screener] = run["rerequests"].get(screener, 0) + len(pending)
            if err:
                self.diag(name, screener, pending, attempt, err); time.sleep(20 * attempt); continue
            items = res.get("decisions") if isinstance(res, dict) else None
            if not isinstance(items, list):
                self.diag(name, screener, pending, attempt, "no decisions list"); continue
            cnt = collections.Counter(d.get("record_id") for d in items if isinstance(d, dict))
            bad = {}
            for i in pending:
                if cnt[i] != 1:
                    bad[i] = [f"returned {cnt[i]} times"]; continue
                d = next(d for d in items if isinstance(d, dict) and d.get("record_id") == i)
                p = problems(d, self.inp[i], reconsider)
                if p:
                    bad[i] = p
                else:
                    self.write(name, stage, rnd, screener, prompt_id, d)
            extra = [k for k in cnt if k not in pending]
            if bad or extra:
                self.diag(name, screener, list(bad), attempt, dict(problems=bad, unexpected_ids=extra))
            pending = list(bad)
        return [(screener, i) for i in pending]

    def diag(self, name, screener, ids, attempt, err):
        with lock, open(os.path.join(WORK, "diagnostics.jsonl"), "a") as f:
            f.write(json.dumps(dict(ts=now(), out=self.out, step=name, screener=screener, attempt=attempt, records=ids, error=err), ensure_ascii=False) + "\n")

    def write(self, name, stage, rnd, screener, prompt_id, d):
        row = dict(decision_id=f"{d['record_id']}-{stage}-{rnd}-{screener}", record_id=d["record_id"], stage=stage, round=rnd,
                   screener=screener, run_id=f"{self.m['run_label']}:{name}:{screener}", prompt_id=prompt_id, decision=d["decision"],
                   code=d["code"], evidence=d["evidence"], reason=d["reason"], response_to_other=d.get("response_to_other"))
        with lock:
            if row["decision_id"] in self.by:
                return
            with open(self.jl, "a") as f:
                f.write(json.dumps(row, ensure_ascii=False) + "\n"); f.flush(); os.fsync(f.fileno())
            self.rows.append(row); self.by[row["decision_id"]] = row

    def finish(self, r1, r2):
        (f1, u1), (f2, u2) = r1, r2
        rows = []
        for i in self.inp:
            if i in f2:
                dec, st, k = f2[i]
            elif i in u2:  # agreed exclusion reopened by the challenge and still unresolved (amendment 2)
                dec, st, k = "AUTHOR", "challenge_consensus", 3
            elif i in f1:
                dec, st, k = f1[i]
            else:
                dec, st, k = "AUTHOR", "consensus", 3
            codes = sorted({self.get(i, st, k, s)["code"] for s in SCREENERS}, key=CODE_ORDER.index) if dec == "EXCLUDE_CERTAIN" else []
            rows.append(dict(record_id=i, final_decision={"FULL_TEXT": "FULL_TEXT", "EXCLUDE_CERTAIN": "EXCLUDE", "AUTHOR": "AUTHOR_PENDING"}[dec],
                             exclusion_code=codes[0] if codes else "", fixed_stage=st, fixed_round=k,
                             basis_decision_ids=";".join(f"{i}-{st}-{k}-{s}" for s in SCREENERS),
                             challenged="yes" if i in f2 or i in u2 else "no", author_decision="", author_code=""))
        # author_review.csv is written first and decisions.csv last, each via a temporary file, so decisions.csv exists only
        # when both files are complete
        ar = os.path.join(self.out, "author_review.csv")
        with open(ar + ".tmp", "w", newline="") as f:
            w = csv.writer(f); w.writerow(["record_id", "title", "text_source", "unresolved_stage", "decision_ids", "author_decision", "author_code", "author_note"])
            for r in rows:
                if r["final_decision"] == "AUTHOR_PENDING":
                    i = r["record_id"]
                    w.writerow([i, self.inp[i]["title"], self.inp[i]["text_source"], r["fixed_stage"],
                                ";".join(x["decision_id"] for x in self.rows if x["record_id"] == i), "", "", ""])
        os.replace(ar + ".tmp", ar)
        dp = os.path.join(self.out, "decisions.csv")
        with open(dp + ".tmp", "w", newline="") as f:
            w = csv.DictWriter(f, fieldnames=list(rows[0])); w.writeheader(); w.writerows(rows)
        os.replace(dp + ".tmp", dp)
        c = collections.Counter(r["final_decision"] for r in rows)
        self.m["result"] = dict(c); self.m["finished"] = now(); atomic_json(self.m, self.mf)
        print(now(), "final", dict(c), "; awaiting verification", flush=True)


def init(out, pilot_ids):
    if os.path.exists(os.path.join(out, "manifest.json")) or os.path.exists(os.path.join(out, "screening_rounds.jsonl")):
        sys.exit("run directory already initialised")
    os.makedirs(out, exist_ok=True); os.makedirs(os.path.join(WORK, "calls"), exist_ok=True)
    allin = [json.loads(l) for l in open(os.path.join(SCR, "screening_input.jsonl"))]
    ids = [r["record_id"] for r in allin]
    assert len(ids) == len(set(ids)), "duplicate record ids in input"
    for r in allin:
        assert r["screening_text"].strip() and sha(r["screening_text"]) == r["text_sha256"], r["record_id"]
    if pilot_ids:
        want = [l.strip() for l in open(pilot_ids) if l.strip()]
        assert set(want) <= set(ids); ids = [i for i in ids if i in set(want)]
    m = dict(run_label=os.path.basename(os.path.normpath(out)), mode="pilot" if pilot_ids else "full", created=now(),
             record_ids=ids, record_ids_sha256=sha("\n".join(ids)), input_records=len(allin),
             frozen={k: dict(file=p, sha256=fsha(os.path.join(ROOT, p))) for k, p in Run.frozen_files().items()},
             screeners={s: dict(cfg, cli=subprocess.run([s, "--version"], capture_output=True, text=True).stdout.strip()) for s, cfg in SCREENERS.items()},
             isolation=ISOLATION, batch_size=BATCH, max_requests_per_record=MAX_ATTEMPTS, evidence_max_words=EVIDENCE_WORDS,
             code_order_for_reporting=list(CODE_ORDER), runs=[])
    atomic_json(m, os.path.join(out, "manifest.json"))
    print("initialised", out, m["mode"], len(ids), "records")


def main():
    ap = argparse.ArgumentParser(); ap.add_argument("cmd", choices=["init", "next", "approve", "status"]); ap.add_argument("step", nargs="?")
    ap.add_argument("--out", required=True); ap.add_argument("--pilot-ids"); ap.add_argument("--by"); ap.add_argument("--ref")
    a = ap.parse_args()
    if a.cmd == "init":
        return init(a.out, a.pilot_ids)
    R = Run(a.out)
    if not hasattr(R, "m"):
        sys.exit("not initialised")
    if a.cmd == "next":
        return R.next()
    steps, _ = R.plan()
    if a.cmd == "approve":
        names = [s[0] for s in steps]
        assert a.step in names and a.by and a.ref, "approve STEP --by WHO --ref REF"
        st = steps[names.index(a.step)]
        assert (a.step == "final" and os.path.exists(os.path.join(a.out, "decisions.csv"))) or (a.step != "final" and R.complete(st[1], st[2], st[3])), "step not finished"
        with open(R.gf, "a") as f:
            f.write(json.dumps(dict(ts=now(), step=a.step, approved_by=a.by, ref=a.ref)) + "\n")
        return print("approved", a.step)
    for name, st, k, ids in steps:
        done = name == "final" and os.path.exists(os.path.join(a.out, "decisions.csv")) or name != "final" and R.complete(st, k, ids)
        print(name, len(ids), "done" if done else "pending", "approved" if R.approved(name) else "")


if __name__ == "__main__":
    main()
