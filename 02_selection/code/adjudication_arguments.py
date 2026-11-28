"""Arguments for each position of the author-adjudicated cases (author: after the AI three-step review, an AI
reads the earlier records, blinded to which system held which view, and writes the reasons supporting A and supporting
B; the author checks the reasons and decides. The arguments are added before the author's decision in the record; the
decisions themselves do not change).

Cases (67): the 40 title/abstract records and the 1 full-text report decided by the author and
the 26 pilot codings decided from review comments the author accepted. The retracted-publication
exclusion and the item rules are rule-based, not case decisions, and are not covered.

Per case:
  1. a blinded record: the two positions as Position A and Position B (which system becomes A is drawn per case with a
     fixed seed; system names are never shown), each position's decisions and reasons through the rounds (coding: each
     position's coding, and the comments of the later review steps with the A/B labels carried over), the criteria
     (eligibility criteria, or the item definition and the general coding rules) and the source text the systems saw
     (abstract, full text, or the printed text of the cited IDs);
  2. writer (Claude): the strongest argument for A and for B (1-3 sentences each) and the question that separates them;
     no verdict, no mention of a decision, no quotation of the source, no locators or evidence IDs;
  3. checker (Codex): faithful, balanced, no copied text -> ok | problem; on problem one revision and a second check;
  4. copyright screen (github_copyright.Screen: 8-gram overlap with the report texts, quoted excerpts, locators) and a
     check for identities, IDs and locators; a hit is rewritten by the writer (at most two times).
Every call is cached by tag, assessor and prompt checksum (internal/adjudication_arguments_calls.jsonl).
Output: results/oct_search/internal/adjudication_arguments.jsonl (with the system behind each position) and
results/oct_search/public/adjudication_arguments_public.jsonl (without identities, free text screened).
Usage: adjudication_arguments.py [--workers N] [--only CASE_ID ...]"""
import concurrent.futures as cf, csv, hashlib, json, os, random, re, sys, threading
os.environ.setdefault("CODING_ITEMS", "v3.1.2")  # the pilot codings were made and decided under the v3.1.2 coding rules
HERE = os.path.dirname(os.path.abspath(__file__)); ROOT = os.path.dirname(os.path.dirname(HERE)); sys.path.insert(0, HERE); os.chdir(ROOT)
import coding_run as RUN, coding_consensus as CS, visual_run as V
import github_copyright as GC
S = "results/oct_search"; INT = f"{S}/internal"; os.makedirs(INT, exist_ok=True)
CALLS = f"{INT}/adjudication_arguments_calls.jsonl"; V.RAW = f"{INT}/adjudication_arguments_raw"; os.makedirs(V.RAW, exist_ok=True)
OUT_INT = f"{INT}/adjudication_arguments.jsonl"; OUT_PUB = f"{S}/public/adjudication_arguments_public.jsonl"
WRITTEN = "YYYY-MM-DD"; SEED = "<withheld: seed of the blinded position labels>"; LOCK = threading.Lock(); ITEMS = RUN.ITEMS
WRITER, CHECKER = "claude", "codex"
SC = GC.Screen()

ARG = {"type": "object", "additionalProperties": False, "required": ["argument_A", "argument_B", "key_question"],
       "properties": {"argument_A": {"type": "string"}, "argument_B": {"type": "string"}, "key_question": {"type": "string"}}}
CHECK = {"type": "object", "additionalProperties": False, "required": ["verdict", "problem"], "properties": {
    "verdict": {"type": "string", "enum": ["ok", "problem"]}, "problem": {"type": "string"}}}

WRITE = """You prepare material for the person who adjudicates a case on which two independent reviewers did not agree, in a
systematic review of machine-learning studies that use data of the Korea National Health and Nutrition Examination
Survey (KNHANES). Below is a blinded record of the case: the {task}, the two positions (Position A and Position B) with
what each held through the review rounds and why, and the source text both reviewers saw.

Write, in English:
- argument_A: the strongest argument supporting Position A, in 1-3 sentences (at most about 90 words);
- argument_B: the strongest argument supporting Position B, in 1-3 sentences (at most about 90 words);
- key_question: one sentence naming the question whose answer separates the two positions.

Rules:
- Ground every statement only in the record and the criteria or rules below; add no outside facts.
- Argue each position as its best advocate would, stating the reasoning (which fact of the source text and which
  criterion or rule lead to the position), not only the conclusion. Make the two arguments comparably strong and long.
- Each argument naturally argues for its own position's answer (e.g. FULL_TEXT or EXCLUDE_CERTAIN X2, or a coding);
  that is expected. But do not say or imply which position is right, better or more cautious overall; do not mention
  how the case was or will be decided or by whom; do not refer to the reviewers as people or systems (say "Position A",
  "Position B").
- Paraphrase. Do not copy sentences or phrases of the source text (technical terms of a few words are fine) and do not
  use quotation marks around source wording.
- Give no locators: no page, paragraph or line numbers and no evidence IDs (such as P0012, T03-R01-C02, F01-TX8,
  SUPTXT1.P20); refer to places in general terms (the abstract, the methods, a table, a figure, the supplement).
{revision}
{criteria_head}
{criteria}

CASE
{case}

POSITION A
{pos_a}

POSITION B
{pos_b}
{comments}
SOURCE TEXT SEEN BY BOTH REVIEWERS
{source}"""

VERIFY = """Check arguments written for the person who adjudicates a case on which two independent reviewers did not agree,
in a systematic review of machine-learning studies that use KNHANES data. The writer was given the blinded record below
and asked for the strongest argument for Position A, the strongest for Position B (1-3 sentences each) and the
question that separates them.

Answer ok only if all of the following hold, otherwise problem and name the problem in one or two sentences (problem
'' when ok):
- each argument is faithful to its position and to the record and criteria (no fact absent from the record, no
  misstatement of what a position held or why);
- the arguments are balanced: each is a genuine best case for its position, neither is a straw man, and nothing says
  or signals which position is right overall or mentions how the case was or will be decided (each argument arguing
  for its own position's answer, e.g. FULL_TEXT, an exclusion code or a coding, is expected and is not a problem);
- the key question really separates the two positions;
- no sentence or longer phrase is copied from the report's source text (technical terms of a few words are fine;
  wording taken from the criteria or coding rules is not a problem), and there are no page, paragraph or line
  locators, no evidence IDs and no reviewer identities.
An argument may rest on a reading of the criteria or rules that its position itself put forward in the record; that is
faithful representation, not a problem, unless the argument misstates what the criteria or rules say. Minor matters of
style or length are not problems.

{criteria_head}
{criteria}

CASE
{case}

POSITION A
{pos_a}

POSITION B
{pos_b}
{comments}
SOURCE TEXT SEEN BY BOTH REVIEWERS
{source}

ARGUMENTS TO CHECK
argument_A: {argument_A}
argument_B: {argument_B}
key_question: {key_question}"""


def ask(who, prompt, sch, tag):
    ps = hashlib.sha256(prompt.encode()).hexdigest()
    if os.path.exists(CALLS):
        for l in open(CALLS):
            r = json.loads(l)
            if r["tag"] == tag and r["assessor"] == who and r["prompt_sha256"] == ps and r.get("answer"): return r["answer"]
    res, err, meta = RUN.text_call(who, prompt, sch, tag)
    with LOCK, open(CALLS, "a") as f: f.write(json.dumps(dict(tag=tag, assessor=who, prompt_sha256=ps, answer=res, error=err, call=meta), ensure_ascii=False) + "\n")
    return res


def a_system(case_id):
    """The system shown as Position A (fixed seed, drawn per case)."""
    return random.Random(f"{SEED}:{case_id}").choice(["claude", "codex"])


def relabel(text, swapped):
    """A/B labels of the codings (A = Claude's coding, B = Codex's) carried over to the blinded positions."""
    if not swapped or not text: return text
    return re.sub(r"(?<![A-Za-z0-9])([AB])(?![A-Za-z0-9])", lambda m: "B" if m.group(1) == "A" else "A", text)


def strip_html(s): return re.sub(r"\s+", " ", re.sub(r"<[^>]+>", " ", s or "")).strip()


STAGE_ORDER = {"initial": 0, "consensus": 1, "challenge": 2, "challenge_consensus": 3}
STAGE_NAME = {"initial": "independent review", "consensus": "mutual review round", "challenge": "re-review of the agreed exclusion",
              "challenge_consensus": "mutual review round after the re-review"}


def dec_label(d, c): return f"{d} ({c})" if c else d


def trajectory(rounds):
    """Compact public summary of one position's decisions through the rounds."""
    parts = []
    for r in rounds:
        lab = STAGE_NAME[r["stage"]] + (f" {r['round']}" if r["stage"] in ("consensus", "challenge_consensus") else "")
        parts.append(f"{lab}: {dec_label(r['decision'], r['code'])}")
    finals = {dec_label(r["decision"], r["code"]) for r in rounds}
    head = next(iter(finals)) + " in every round" if len(finals) == 1 else f"{dec_label(rounds[-1]['decision'], rounds[-1]['code'])} in the last round"
    return head, "; ".join(parts)


def show_rounds(rounds, ev_key):
    out = []
    for r in rounds:
        lab = STAGE_NAME[r["stage"]] + (f" {r['round']}" if r["stage"] in ("consensus", "challenge_consensus") else "")
        s = f"- {lab}: decision {dec_label(r['decision'], r['code'])}. Reason: {r['reason']}"
        if r.get(ev_key): s += f" Evidence cited: {r[ev_key]}"
        if r.get("response_to_other"): s += f" Reply to the other position: {r['response_to_other']}"
        out.append(s)
    return "\n".join(out)


def selection_cases():
    cases = []
    crit_s = open(f"{S}/screening/ELIGIBILITY.md").read(); crit_e = open(f"{S}/eligibility/CRITERIA.md").read()
    for stage, d, crit in (("screening", f"{S}/screening/run", crit_s), ("eligibility", f"{S}/eligibility/run_batch1", crit_e)):
        top = {r["record_id"]: r for r in csv.DictReader(open(f"{d}/author_review.csv"))}
        det = list(csv.DictReader(open(f"{d}/author_review_detail.csv")))
        ft = {}
        if stage == "eligibility":
            for l in open(f"{S}/eligibility/eligibility_input.jsonl"):
                x = json.loads(l)
                if x["record_id"] in top: ft[x["record_id"]] = "\n\n".join(x.get("pages") or [])
        for rid, t in top.items():
            cid = f"{stage}:{rid}"; asys = a_system(cid); bsys = "codex" if asys == "claude" else "claude"
            rows = sorted((r for r in det if r["record_id"] == rid), key=lambda r: (STAGE_ORDER[r["stage"]], int(r["round"])))
            who = "screener" if stage == "screening" else "assessor"
            R = {w: [r for r in rows if r[who] == w] for w in ("claude", "codex")}
            if stage == "screening":
                src = strip_html(rows[0]["screening_text"]) or "(no abstract or lead text: the title only)"
                source = f"Title: {t['title']}\nText screened ({rows[0]['text_source'] or 'title only'}): {src}"
            else: source = f"Title: {t['title']}\nFull text:\n{ft[rid]}"
            tr = {w: trajectory(R[w]) for w in R}
            cases.append(dict(case_id=cid, stage=stage, record_id=rid, item="", title=t["title"], A=asys, B=bsys, criteria=crit,
                              criteria_head="ELIGIBILITY CRITERIA (" + ("title/abstract screening" if stage == "screening" else "full-text eligibility") + ")",
                              task="eligibility criteria of the " + ("title/abstract" if stage == "screening" else "full-text") + " stage",
                              case=f"Stage: {'title/abstract screening' if stage == 'screening' else 'full-text eligibility'}. Record {rid}. The question is whether the record goes on "
                                   + ("to full-text assessment (FULL_TEXT) or is excluded at title/abstract (EXCLUDE_CERTAIN with a code)." if stage == "screening" else "to be included (INCLUDE) or excluded (EXCLUDE with a reason code)."),
                              pos={"A": show_rounds(R[asys], "evidence"), "B": show_rounds(R[bsys], "evidence")}, comments="", source=source,
                              position_decision={"A": tr[asys][0], "B": tr[bsys][0]}, position_rounds={"A": tr[asys][1], "B": tr[bsys][1]},
                              author=dict(decision=dec_label(t["author_decision"], t["author_code"]), date="YYYY-MM-DD" if stage == "screening" else "YYYY-MM-DD", note=t["author_note"])))
    return cases


HOW = {"decision_A": "{X}", "decision_B": "{X}", "decision_A_corrected": "{X}, corrected as the decision states", "decision_B_checked": "{X} (checked)",
       "decision_apply": "a coding written from both codings as the decision states"}


def coding_cases():
    C = f"{S}/coding/pilot_final"
    Q = {(q["record_id"], q["item"]): q for q in map(json.loads, open(f"{C}/author_queue_before_decisions.jsonl"))}
    R1 = {(x["record_id"], x["item"]): x for x in map(json.loads, open(f"{C}/compare_r1.jsonl"))}
    FIN = {(x["record_id"], x["item"]): x for x in map(json.loads, open(f"{C}/final_items.jsonl"))}
    titles = {}
    for l in open(f"{S}/public/screening_records.jsonl"):
        x = json.loads(l); titles[x["record_id"]] = x.get("title", "")
    cases = []
    for d in json.load(open(f"{S}/coding/review_internal review note.json")):
        k = (d["record_id"], d["item"]); cid = f"coding:{d['record_id']}:{d['item']}"
        asys = a_system(cid); bsys = "codex" if asys == "claude" else "claude"; sw = asys == "codex"
        q = Q.get(k)
        cod = {"claude": q["A"], "codex": q["B"]} if q else {"claude": R1[k]["claude"], "codex": R1[k]["codex"]}
        comments = []
        if q:
            comments += list((q.get("consensus") or {}).get("reasons") or [])
            for key in ("material", "inconsistency_check", "triage"): comments += [m.get("reason") for m in (q.get(key) or []) if m and m.get("reason")]
        comments = [relabel(c, sw) for c in comments if c]
        random.Random(f"{SEED}:{cid}:comments").shuffle(comments)
        T = CS.id_text(CS.CR.render(d["record_id"]))
        ids = list(dict.fromkeys(i for w in ("claude", "codex") for i in cod[w]["evidence_ids"]))
        source = f"Title: {titles.get(d['record_id'], T.get('TITLE', ''))}\nPrinted text of the IDs cited by either coding:\n" + "\n".join(f"[{i}] {T.get(i, '(ID not found in the report)')}" for i in ids)
        summ = lambda a: f"status {a['status']}; inconsistency {a.get('inconsistency', 'n/a')}; {len(a['values'])} value entr{'y' if len(a['values']) == 1 else 'ies'}"
        f = FIN[k]; how = f.get("how", "")
        X = {"A": "Position A's coding", "B": "Position B's coding"}
        sysdec = {"A": "claude", "B": "codex"}.get(d["decision"])
        if how in HOW and "{X}" in HOW[how]:
            letter = "A" if (how[9] == "A") != sw else "B"; base = HOW[how].replace("{X}", X[letter])
        elif d["decision"] == "SET": base = "neither coding; a new coding set as the decision states"
        elif d["decision"] == "APPLY_FINAL": base = "the coding already settled, corrected as the decision states"
        else: base = HOW.get(how, how)
        instr = relabel(d["instruction"], sw)
        cases.append(dict(case_id=cid, stage="coding (pilot)", record_id=d["record_id"], item=d["item"], title=titles.get(d["record_id"], ""), A=asys, B=bsys,
                          criteria="GENERAL CODING RULES\n" + "\n".join(f"- {r}" for r in ITEMS["general_rules"]) + f"\n\nITEM\n{d['item']}: {ITEMS['items'][d['item']]}",
                          criteria_head=f"CODING RULES (codebook {ITEMS['version']})", task="item definition and the general coding rules",
                          case=f"Data coding of report {d['record_id']}, item {d['item']}. Two codings of this item differ; the question is which coding (or which parts of each) the final coding should follow.",
                          pos={"A": CS.show(cod[asys]), "B": CS.show(cod[bsys])},
                          comments=("\nCOMMENTS FROM THE LATER REVIEW STEPS (both reviewers, unattributed, in random order; 'A' and 'B' refer to the positions above)\n"
                                    + "\n".join(f"- {c}" for c in comments) + "\n") if comments else "",
                          source=source, position_decision={"A": summ(cod[asys]), "B": summ(cod[bsys])}, position_rounds={"A": "", "B": ""},
                          author=dict(decision=base + (f": {instr}" if instr else ""), decision_code=d["decision"], decision_relabelled=({"A": "A", "B": "B"}[d["decision"]] if not sw else {"A": "B", "B": "A"}[d["decision"]]) if sysdec else d["decision"],
                                      date="YYYY-MM-DD", note="decided from review comments accepted by the author ('apply it')", final_how=how)))
    return cases


ID_RE = re.compile(r"\b(?:P\d{3,4}|T\d{2}-\S+|F\d{2}-\S+|SUP\w*[.-]\S+|SUPTXT\d+\S*)\b")
BAD = re.compile(r"\b(claude|codex|anthropic|openai|gpt|author|adjudicat\w*|decision was)\b", re.I)


def screen(arg):
    """Copyright and blinding hits of the generated text: list of (field, kind, span)."""
    hits = []
    for k in ("argument_A", "argument_B", "key_question"):
        t = arg.get(k) or ""
        for a, b in SC.overlaps(t): hits.append((k, "8-gram overlap with a report text", t[a:b]))
        for m in SC.quotes(t): hits.append((k, "quoted report excerpt", m.group()))
        for m in GC.LOC.finditer(t): hits.append((k, "locator", m.group()))
        for m in ID_RE.finditer(t): hits.append((k, "evidence ID", m.group()))
        for m in BAD.finditer(t): hits.append((k, "identity or decision word", m.group()))
    return hits


SHORT = 5  # coordinator: no run of 5+ consecutive words identical to the source text the systems saw


def _grams(toks, n): return {tuple(toks[i:i + n]) for i in range(len(toks) - n + 1)}


STOP = {"and", "or", "of", "the", "in", "with", "a", "an", "for", "to", "on", "by"}


def name_like(w, c):
    """A word of a technical term or name: capitalised or acronym, with a digit, a function word, or a word of the criteria."""
    if "_wc" not in c: c["_wc"] = {x[0] for x in SC._toks(c["criteria"])}
    return w[:1].isupper() or any(ch.isdigit() for ch in w) or w.lower() in STOP or w.lower() in c["_wc"] or w.startswith("zzmask")


def short_hits(arg, c):
    """Runs of SHORT or more consecutive words of an argument that repeat the case's source text. Survey names, DOIs and
    cycle years are masked (as in the copyright screen); runs whose every 5-gram also occurs in the criteria or coding
    rules (wording of the criteria, technical terms, variable names defined there) are not counted."""
    if "_g" not in c:
        c["_g"] = _grams([t[0] for t in SC._toks(c["source"])], SHORT); c["_gc"] = _grams([t[0] for t in SC._toks(c["criteria"])], SHORT)
    out = []
    for k in ("argument_A", "argument_B", "key_question"):
        t = arg.get(k) or ""; tk = SC._toks(t); cov = [False] * len(tk)
        for i in range(len(tk) - SHORT + 1):
            g = tuple(x[0] for x in tk[i:i + SHORT])
            if g in c["_g"] and g not in c["_gc"] and not all(w.isdigit() for w in g):
                for j in range(i, i + SHORT): cov[j] = True
        i = 0
        while i < len(tk):
            if cov[i]:
                j = i
                while j + 1 < len(tk) and cov[j + 1]: j += 1
                if not all(name_like(t[x[1]:x[2]], c) for x in tk[i:j + 1]):  # runs made only of names and criteria terms are kept
                    out.append((k, f"{j - i + 1}-word run repeated from the source text", t[tk[i][1]:tk[j][2]]))
                i = j + 1
            else: i += 1
    return out


MAX_REV = 3  # coordinator: up to three writer -> checker revision rounds, as in the other steps of the review
MAX_COPY = 3


def process(c):
    kw = dict(task=c["task"], criteria_head=c["criteria_head"], criteria=c["criteria"], case=c["case"], pos_a=c["pos"]["A"], pos_b=c["pos"]["B"],
              comments=c["comments"], source=c["source"])
    tag = f"{c['case_id']}@argue"; log = dict(revised=False, revision_rounds=0, copyright_rewrites=0, short_span_fixes=0, short_spans_found=0, checks=[])
    arg = ask(WRITER, WRITE.format(revision="", **kw), ARG, tag)
    if not arg: return None, dict(log, error="write failed")
    chk = ask(CHECKER, VERIFY.format(**kw, **arg), CHECK, tag + "-check")
    if not chk: return None, dict(log, error="check failed")
    log["checks"].append(chk)
    RT = {1: ("-rev", "-check2"), 2: ("-rev2", "-rev2-check"), 3: ("-rev3", "-rev3-check")}
    for _ in range(MAX_REV + MAX_COPY + 2):
        hits = screen(arg); sh = short_hits(arg, c)
        if (hits or sh) and log["copyright_rewrites"] < MAX_COPY:  # copied wording first: rewrite, then check again
            n = log["copyright_rewrites"] + 1; log["short_spans_found"] += len(sh)
            rev = ("\nAn earlier draft repeated wording of the source text or contained a locator, an ID or a word that is not allowed. Earlier draft: "
                   + json.dumps(arg, ensure_ascii=False) + "\nSpans to rephrase in your own words or remove: " + "; ".join(f"{h[1]}: '{h[2]}'" for h in hits + sh)
                   + "\nWrite the same arguments again, keeping their content, without these spans.\n")
            new = ask(WRITER, WRITE.format(revision=rev, **kw), ARG, f"{tag}-copy{n}" + ("" if n == 1 and not sh else "-s"))
            if not new: return None, dict(log, error="copyright rewrite failed")
            arg = new; log["copyright_rewrites"] = n; log["short_span_fixes"] += bool(sh)
            chk = ask(CHECKER, VERIFY.format(**kw, **arg), CHECK, f"{tag}-copy{n}-check" + ("" if n == 1 and not sh else "-s"))
            if chk: log["checks"].append(chk)
            continue
        if log["checks"][-1]["verdict"] == "problem" and log["revision_rounds"] < MAX_REV:
            k = log["revision_rounds"] + 1
            rev = ("\nAn earlier draft was checked and found to have a problem. Earlier draft: " + json.dumps(arg, ensure_ascii=False)
                   + "\nProblem found: " + log["checks"][-1]["problem"] + "\nWrite a corrected version.\n")
            new = ask(WRITER, WRITE.format(revision=rev, **kw), ARG, tag + RT[k][0])
            if not new: return None, dict(log, error="revision failed")
            arg = new; log["revised"] = True; log["revision_rounds"] = k
            chk = ask(CHECKER, VERIFY.format(**kw, **arg), CHECK, tag + RT[k][1])
            if not chk: return None, dict(log, error="check failed")
            log["checks"].append(chk); continue
        break
    log["screen_hits"] = len(screen(arg)); log["short_hits_left"] = len(short_hits(arg, c))
    log["final_verdict"] = log["checks"][-1]["verdict"]; log["remaining_issue"] = log["checks"][-1]["problem"] if log["final_verdict"] == "problem" else ""
    return arg, log


KO = {"": "geomjeungyong", "": "pyeonggayong", "": "hullyeonyong"}  # Korean split labels of a Korean-language report


def romanise(rec):
    """Public text is English: Korean split labels quoted by the arguments are romanised, with a gloss at first use."""
    out = {}
    for k, v in rec.items():
        if isinstance(v, str):
            seen = set()
            for ko, ro in KO.items():
                if ko in v:
                    v = v.replace(ko, ro + " (a Korean data-split label)", 1).replace(ko, ro); seen.add(ko)
        out[k] = v
    return out


PUBLIC_DROP = ("author_decision_date", "arguments_written", "author_confirmation")   # kept in the internal file only


def main():
    workers = int(sys.argv[sys.argv.index("--workers") + 1]) if "--workers" in sys.argv else 6
    only = set(sys.argv[sys.argv.index("--only") + 1:]) if "--only" in sys.argv else None
    cases = selection_cases() + coding_cases()
    print("cases", len(cases), {s: sum(c["stage"] == s for c in cases) for s in ("screening", "eligibility", "coding (pilot)")}, flush=True)
    todo = [c for c in cases if not only or c["case_id"] in only]
    with cf.ThreadPoolExecutor(workers) as ex: res = list(ex.map(process, todo))
    fi, fp = open(OUT_INT, "w"), open(OUT_PUB, "w")
    for c, (arg, log) in zip(todo, res):
        rec = dict(case_id=c["case_id"], stage=c["stage"], record_id=c["record_id"], item=c["item"], title=c["title"],
                   position_A_decision=c["position_decision"]["A"], position_B_decision=c["position_decision"]["B"],
                   position_A_rounds=c["position_rounds"]["A"], position_B_rounds=c["position_rounds"]["B"],
                   argument_position_A=(arg or {}).get("argument_A"), argument_position_B=(arg or {}).get("argument_B"), key_question=(arg or {}).get("key_question"),
                   author_decision=c["author"]["decision"], author_decision_date=c["author"]["date"], arguments_written=WRITTEN,
                   writer="one system", checker="the other system", checker_verdicts=[x["verdict"] for x in log["checks"]], revised=log["revised"],
                   revision_rounds=log["revision_rounds"], final_verdict=log.get("final_verdict"), remaining_issue=log.get("remaining_issue", ""),
                   copyright_rewrites=log["copyright_rewrites"], short_span_fixes=log["short_span_fixes"], author_confirmation="pending")
        fi.write(json.dumps(dict(rec, position_A_system=c["A"], position_B_system=c["B"], writer=WRITER, checker=CHECKER, author_note=c["author"]["note"],
                                 author_decision_code=c["author"].get("decision_code"), final_how=c["author"].get("final_how"),
                                 checker_problems=[x["problem"] for x in log["checks"] if x["verdict"] == "problem"], error=log.get("error"),
                                 screen_hits=log.get("screen_hits"), short_hits_left=log.get("short_hits_left"), short_spans_found=log.get("short_spans_found")), ensure_ascii=False) + "\n")
        pub = {k: v for k, v in rec.items() if k not in PUBLIC_DROP}   # no process dates in the public export
        fp.write(json.dumps(GC.clean_tree(romanise(pub), SC, "adjudication_arguments_public.jsonl"), ensure_ascii=False) + "\n")
    fi.close(); fp.close()
    import collections
    print("verdict sequences", dict(collections.Counter("/".join(r[1]["checks"] and [x["verdict"] for x in r[1]["checks"]] or ["none"]) for r in res)))
    print("final verdicts", dict(collections.Counter(r[1].get("final_verdict") for r in res)), "revision rounds", dict(collections.Counter(r[1]["revision_rounds"] for r in res)),
          "short-span rewrites", sum(r[1]["short_span_fixes"] > 0 for r in res), "short spans found", sum(r[1]["short_spans_found"] for r in res), "short left", sum(r[1].get("short_hits_left") or 0 for r in res))
    print("revised", sum(r[1]["revised"] for r in res), "copyright rewrites", sum(r[1]["copyright_rewrites"] > 0 for r in res),
          "remaining screen hits", sum(r[1].get("screen_hits") or 0 for r in res), "errors", [c["case_id"] for c, r in zip(todo, res) if r[1].get("error")])


if __name__ == "__main__":
    main()
