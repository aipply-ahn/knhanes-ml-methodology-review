"""Independent checks on a screening run directory (does not import the runner).
Usage: screening_verify.py RUN_DIR   -> checks every finished step so far; final-file checks once decisions.csv exists.
Exit 1 on any failure. Record universe = manifest record_ids (full mode: must equal the frozen input exactly)."""
import collections, csv, hashlib, html, json, os, re, sys, unicodedata
ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
SCR = os.path.join(ROOT, "results/oct_search/screening")
D = sys.argv[1]
S = ("claude", "codex"); CODES = {"X1", "X2", "X3", "X4"}; ORDER = ["X4", "X1", "X2", "X3"]
fail = []
def chk(ok, msg):
    if not ok:
        fail.append(msg)

m = json.load(open(os.path.join(D, "manifest.json")))
cur = {k: f["sha256"] for k, f in m["frozen"].items()}
for a in m.get("amendments", []):
    cur.update(a["sha256"])
for k, f in m["frozen"].items():
    chk(hashlib.sha256(open(os.path.join(ROOT, f["file"]), "rb").read()).hexdigest() == cur[k], f"frozen file changed: {f['file']}")
allin = [json.loads(l) for l in open(os.path.join(SCR, "screening_input.jsonl"))]
ids_all = [r["record_id"] for r in allin]
chk(len(ids_all) == len(set(ids_all)), "duplicate ids in input")
chk(m["record_ids_sha256"] == hashlib.sha256("\n".join(m["record_ids"]).encode()).hexdigest(), "record_ids hash")
if m["mode"] == "full":
    chk(m["record_ids"] == ids_all, "full run does not cover the frozen input exactly")
inp = {r["record_id"]: r for r in allin if r["record_id"] in set(m["record_ids"])}
chk(len(inp) == len(m["record_ids"]), "record_ids not all in input")

rows = [json.loads(l) for l in open(os.path.join(D, "screening_rounds.jsonl"))] if os.path.exists(os.path.join(D, "screening_rounds.jsonl")) else []
cnt = collections.Counter(r["decision_id"] for r in rows)
chk(all(v == 1 for v in cnt.values()), f"duplicate decision_ids {[k for k, v in cnt.items() if v > 1][:5]}")
by = {r["decision_id"]: r for r in rows}

def clean(t):
    t = unicodedata.normalize("NFKC", t or "")
    for a, b in (("“", '"'), ("”", '"'), ("’", "'"), ("‘", "'"), ("–", "-"), ("—", "-")):
        t = t.replace(a, b)
    return " ".join(t.split()).lower()

FORMAT_TAGS = {"h1", "h2", "h3", "h4", "h5", "h6", "i", "b", "em", "strong", "sub", "sup", "title", "p", "br", "span", "div", "bold", "italic", "u", "sc"}
def drop_tags(t):  # amendment 1: remove formatting tags only; keep any other '<' or '>' text
    out, k = [], 0
    while k < len(t):
        e = t.find(">", k) if t[k] == "<" else -1
        if e > 0 and "<" not in t[k + 1:e]:
            inner = t[k + 1:e]; name = inner[1:] if inner.startswith("/") else inner
            name = name.rstrip("/").rstrip().lower()
            if name in FORMAT_TAGS and (inner[:1] == "/" or inner[:1].isalpha()):  # bare tags only, no attributes
                k = e + 1; continue
        out.append(t[k]); k += 1
    return "".join(out)

FIELDS = {"decision_id", "record_id", "stage", "round", "screener", "run_id", "prompt_id", "decision", "code", "evidence", "reason", "response_to_other"}
PROMPT = {"initial": "round1", "consensus": "round_n", "challenge": "challenge", "challenge_consensus": "round_n"}
for r in rows:
    i = r["decision_id"]
    chk(set(r) == FIELDS, f"fields {i}")
    chk(r["record_id"] in inp, f"unknown record {i}")
    chk(r["screener"] in S and r["stage"] in PROMPT and r["round"] in (1, 2, 3), f"stage/round/screener {i}")
    chk(i == f"{r['record_id']}-{r['stage']}-{r['round']}-{r['screener']}", f"decision_id form {i}")
    chk(r["prompt_id"] == PROMPT.get(r["stage"]), f"prompt_id {i}")
    chk(r["decision"] in ("FULL_TEXT", "EXCLUDE_CERTAIN"), f"decision {i}")
    chk((r["decision"] == "FULL_TEXT" and r["code"] is None) or (r["decision"] == "EXCLUDE_CERTAIN" and r["code"] in CODES), f"code {i}")
    chk(isinstance(r["reason"], str) and r["reason"].strip() != "", f"reason {i}")
    recon = r["stage"] in ("consensus", "challenge_consensus")
    chk((isinstance(r["response_to_other"], str) and r["response_to_other"].strip() != "") if recon else r["response_to_other"] is None, f"response_to_other {i}")
    if r["record_id"] in inp:
        detag = lambda t: html.unescape(drop_tags(t or ""))
        nows = lambda t: "".join(clean(detag(t)).split())  # amendment 1: HTML tags and whitespace ignored when matching
        hay = nows(inp[r["record_id"]]["title"] + " " + inp[r["record_id"]]["screening_text"])
        parts = [p.strip(" .,;:\"'") for p in re.split(r"\s*(?:\.\.\.|…)\s*", detag(r["evidence"]))]
        parts = [p for p in parts if p]
        chk(bool(parts) and all(nows(p) in hay for p in parts), f"evidence not found verbatim {i}")
        chk(sum(len(p.split()) for p in parts) <= m["evidence_max_words"], f"evidence longer than {m['evidence_max_words']} words {i}")

# round traceability: rebuild the expected step sequence from the decisions themselves
g = lambda i, st, k, s: by.get(f"{i}-{st}-{k}-{s}")
done = lambda st, k, ids: all(g(i, st, k, s) for i in ids for s in S)
expected = {}  # (stage, round) -> ids
def walk(first, cons, ids):
    expected[(first, 1)] = set(ids)
    if not done(first, 1, ids):
        return None
    fixed = {i: (g(i, first, 1, "claude")["decision"], first, 1) for i in ids if g(i, first, 1, "claude")["decision"] == g(i, first, 1, "codex")["decision"]}
    open_ = [i for i in ids if i not in fixed]
    for k in (1, 2, 3):
        if not open_:
            break
        expected[(cons, k)] = set(open_)
        if not done(cons, k, open_):
            return None
        for i in open_:
            if g(i, cons, k, "claude")["decision"] == g(i, cons, k, "codex")["decision"]:
                fixed[i] = (g(i, cons, k, "claude")["decision"], cons, k)
        open_ = [i for i in open_ if i not in fixed]
    return fixed, open_
r1 = walk("initial", "consensus", list(inp)); r2 = None
if r1:
    ex = [i for i, v in r1[0].items() if v[0] == "EXCLUDE_CERTAIN"]
    r2 = walk("challenge", "challenge_consensus", ex) if ex else ({}, [])
have = collections.defaultdict(set)
for r in rows:
    have[(r["stage"], r["round"])].add(r["record_id"])
for key, ids in have.items():
    chk(key in expected and ids <= expected[key], f"{key}: decisions for records not due in this round ({len(ids - expected.get(key, set()))})")
# reconsideration rounds must have the previous round for both screeners
for r in rows:
    if r["stage"] in ("consensus", "challenge_consensus"):
        pst, prd = (r["stage"], r["round"] - 1) if r["round"] > 1 else ({"consensus": "initial", "challenge_consensus": "challenge"}[r["stage"]], 1)
        chk(all(g(r["record_id"], pst, prd, s) for s in S), f"previous round missing for {r['decision_id']}")
gates = [json.loads(l) for l in open(os.path.join(D, "gates.jsonl"))] if os.path.exists(os.path.join(D, "gates.jsonl")) else []
order = [f"{st}-{k}" for st, k in expected] + ["final"]
for gt in gates:
    chk(gt["step"] in order, f"gate for unknown step {gt['step']}")
for a, b in zip(order, order[1:]):
    st, k = (b.rsplit("-", 1)[0], int(b.rsplit("-", 1)[1])) if b != "final" else (None, None)
    started = b == "final" and os.path.exists(os.path.join(D, "decisions.csv")) or b != "final" and bool(have.get((st, k)))
    chk(not started or any(x["step"] == a for x in gates), f"step {b} started before {a} was approved")

# final files
fp = os.path.join(D, "decisions.csv")
if os.path.exists(fp):
    chk(r1 is not None and r2 is not None, "decisions.csv exists but screening steps are incomplete")
    dec = list(csv.DictReader(open(fp)))
    ids = [r["record_id"] for r in dec]
    chk(len(ids) == len(set(ids)) and set(ids) == set(inp), "decisions.csv must list every record exactly once")
    if r1 and r2:
        (f1, u1), (f2, u2) = r1, r2
        for r in dec:
            i = r["record_id"]
            if i in u2: d, st, k = "AUTHOR", "challenge_consensus", 3  # unresolved challenge overrides the earlier agreement
            elif i in f2: d, st, k = f2[i]
            elif i in f1: d, st, k = f1[i]
            else: d, st, k = "AUTHOR", "consensus", 3
            want = {"FULL_TEXT": "FULL_TEXT", "EXCLUDE_CERTAIN": "EXCLUDE", "AUTHOR": "AUTHOR_PENDING"}[d]
            chk(r["final_decision"] == want and r["fixed_stage"] == st and r["fixed_round"] == str(k), f"final {i}")
            chk(r["basis_decision_ids"] == ";".join(f"{i}-{st}-{k}-{s}" for s in S), f"basis ids {i}")
            chk(r["challenged"] == ("yes" if i in f2 or i in u2 else "no"), f"challenged flag {i}")
            if want == "EXCLUDE":
                chk(r["exclusion_code"] == min({g(i, st, k, s)["code"] for s in S}, key=ORDER.index), f"exclusion code {i}")
            else:
                chk(r["exclusion_code"] == "", f"exclusion code should be empty {i}")
    if r1 and r2:
        chk(sum(r["final_decision"] == "AUTHOR_PENDING" for r in dec) == len(r1[1]) + len(r2[1]), "AUTHOR_PENDING count differs from unresolved records")
        chk(sum(r["final_decision"] == "EXCLUDE" for r in dec) == sum(v[0] == "EXCLUDE_CERTAIN" for v in r2[0].values()), "EXCLUDE count differs from challenge-confirmed exclusions")
    ar = list(csv.DictReader(open(os.path.join(D, "author_review.csv"))))
    aid = [r["record_id"] for r in ar]
    chk(len(aid) == len(set(aid)) and set(aid) == {r["record_id"] for r in dec if r["final_decision"] == "AUTHOR_PENDING"}, "author_review.csv vs AUTHOR_PENDING")

print("mode", m["mode"], "records", len(inp), "decision lines", len(rows), "steps", {f"{k[0]}-{k[1]}": len(v) for k, v in sorted(have.items())},
      "gates", [x["step"] for x in gates])
if os.path.exists(fp):
    print("final", dict(collections.Counter(r["final_decision"] for r in csv.DictReader(open(fp)))))
print("FAIL" if fail else "PASS", *fail[:30], sep="\n")
sys.exit(1 if fail else 0)
