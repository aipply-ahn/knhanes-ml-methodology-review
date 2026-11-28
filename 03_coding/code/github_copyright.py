"""Copyright screen for the public repository (author: public evidence must not contain abstracts, full
texts, quotations, page locations or hashes of the included reports).

The report texts held internally (full texts read at eligibility, the abstracts read at screening, the converted
report texts, the table and figure transcriptions and supplement texts) are reduced to word 8-grams. A public free-text
value is screened in three ways:
  1. word 8-gram overlap with any report text -> the overlapping span is replaced by '[excerpt withheld]';
  2. a quoted span (straight or curly quotes) of four or more words printed word for word in a report text (in fewer
     than three reports for spans of four to seven words; more frequent short phrases are common terminology) ->
     replaced by '[excerpt withheld]' (shorter quoted terms are category labels or single terms and are kept);
Proper names of data sources (survey names), DOIs, the KNHANES cycle years and two phrases of the TRIPOD statement
that reports reprint in their checklists (GUIDELINE) are masked before matching. Spans for
which a neutral researcher wording was written are replaced by that wording instead (internal mapping, see NEUTRAL).
  3. page, paragraph or line locators (p. N, page N, paragraph N, line N, [PN] with numbers) -> replaced by '[location withheld]'.
The decision, step and rule identifiers around the text are never changed and no new judgement is added.

Only counts are logged (per file and field), never the text. The 8-gram index is cached internally
(results/oct_search/internal/report_8gram_index.pkl; hashed n-grams only) and is never published.

Library use: from github_copyright import Screen; sc = Screen; new = sc.clean(text, file=..., field=...)
Command line: github_copyright.py scan REPO_DIR  -> final scan of every text file of the package (exit 1 on a hit)."""
import collections, glob, hashlib, json, os, pickle, re, sys, unicodedata

ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
S = f"{ROOT}/results/oct_search"
CACHE = f"{S}/internal/report_8gram_index.pkl"
N = 8
TOK = re.compile(r"")
WITHHELD = "[excerpt withheld]"
LOCATION = "[location withheld]"
LOC = re.compile(r"\b(?:pp?\.\s?\d+(?:\s?[-–]\s?\d+)?|pages?\s\d+(?:\s?[-–]\s?\d+)?|paragraphs?\s\d+|para\.?\s\d+|lines?\s\d+(?:\s?[-–]\s?\d+)?)\b"
                 r"|\[(?:P|p)\d+(?:[.:#]\w+)?\]|¶\s?\d+", re.I)
SURVEY = re.compile(r"\b(?:the\s+)?(?:(?:third|fourth|fifth|sixth|seventh|eighth|ninth)\s+)?Korean?\s+National\s+Health\s+and\s+Nutrition(?:al)?\s+Examination\s+Surveys?"
                    r"(?:\s*\(KNHANES(?:\s+[IVX]+(?:[-\u2013, ]+[IVX0-9]+)*)?\))?|(?:the\s+)?(?:US\s+)?National\s+Health\s+and\s+Nutrition\s+Examination\s+Surveys?(?:\s*\(NHANES\))?", re.I)
PROPER = re.compile(r"\b(?:[A-Z\u00c0-\u00de][\w\u00e0-\u00ff'-]*\s+(?:(?:and|of|in|on)\s+)?){1,7}Surveys?(?:\s*\([A-Z0-9-]+\))?")
DOI = re.compile(r"\b(?:doi:?\s*)?10\.\d{4,9}/[^\s,;)\]\"']+", re.I)
CYCLES = re.compile(r"\b[IVX]{1,4}\s?=\s?\d{4}(?:\s?[-\u2013]\s?\d{2,4})?(?:,\s?[IVX]{1,4}\s?=\s?\d{4}(?:\s?[-\u2013]\s?\d{2,4})?)*")
# wording of the TRIPOD statement (items 9 and 13a) used in the requirement definitions; it matches a report only
# because that report reprints the TRIPOD checklist
GUIDELINE = re.compile("|".join(re.escape(x) for x in ("the number of participants with and without the outcome",
                                                        "how missing data were handled (e.g. complete-case analysis")), re.I)
QUOTE = re.compile(r"“([^”]{3,400})”|‘([^’]{3,400})’|\"([^\"\n]{3,400})\"|(?<![A-Za-z0-9])'([^'\n]{3,400})'(?![A-Za-z0-9])")


def norm(s):
    s = unicodedata.normalize("NFKC", s)
    s = re.sub(r"(\w)-\s*\n\s*(\w)", r"\1\2", s)  # words split at a line end in PDF text
    return s.lower()


def h(gram): return int.from_bytes(hashlib.blake2b(" ".join(gram).encode(), digest_size=8).digest(), "little")


def strings(x):
    if isinstance(x, str): yield x
    elif isinstance(x, dict):
        for v in x.values(): yield from strings(v)
    elif isinstance(x, list):
        for v in x: yield from strings(v)


RID = re.compile(r"OCT\d{4}")


def sources():
    """(record_id, text) for every internal report text."""
    for l in open(f"{S}/eligibility/eligibility_input.jsonl"):
        x = json.loads(l); yield x["record_id"], "\n".join(x.get("pages") or [])
    for l in open(f"{S}/screening/screening_input.jsonl"):
        x = json.loads(l); yield x["record_id"], x.get("screening_text") or ""
    p = f"{S}/abstracts_author_provided.json"
    if os.path.exists(p):
        for k, v in json.load(open(p)).items(): yield k, v if isinstance(v, str) else " ".join(strings(v))
    p = f"{S}/abstracts_web.tsv"
    if os.path.exists(p):
        for l in open(p, errors="ignore").read().split("\n")[1:]:
            c = l.split("\t")
            if len(c) > 1 and c[1]: yield c[0], c[1]
    for p in glob.glob(f"{S}/body/body/OCT*.json"):
        yield os.path.basename(p)[:7], "\n".join(strings(json.load(open(p))))
    for p in glob.glob(f"{S}/body/streams/OCT*.txt"):
        yield os.path.basename(p)[:7], open(p, errors="ignore").read()
    for run in ("run2_merged", "run4_alphafix", "run5_supp_new"):
        p = f"{S}/visual/{run}/unit_final.jsonl"
        if os.path.exists(p):
            for l in open(p):
                x = json.loads(l); m = RID.search(x.get("unit_id", ""))
                if m:  # printed content only (labels, captions, transcriptions), not the systems' comments
                    yield m.group(), "\n".join(str(o.get(k) or "") for w in ("claude", "codex") for o in (x.get(w) or []) if isinstance(o, dict)
                                                for k in ("label", "caption", "transcription"))
    for p in glob.glob(f"{S}/visual/*/report_md/OCT*.md"):
        yield os.path.basename(p)[:7], open(p, errors="ignore").read()


def build_index():
    per = collections.defaultdict(set)
    for rid, t in sources():
        w = TOK.findall(norm(t))
        per[rid].update(h(tuple(w[i:i + N])) for i in range(len(w) - N + 1))
    df = collections.Counter()
    for g in per.values(): df.update(g)
    return dict(df), len(per)


GENERIC_DF = 3  # a quoted phrase of 4-7 words printed in this many reports or more is common terminology, not an excerpt
BIB_KEYS = {"title", "journal", "venue", "doi", "pmid", "kci_id", "authors", "first_author", "year"}
BIB_FILES = {"02_selection/screening_records.jsonl", "02_selection/included_reports.csv", "02_selection/report_study_links.csv",
             "01_search/dedup_rule_merges.tsv"}  # bibliographic identification of the records (titles, journals, identifiers)
NEUTRAL = f"{S}/internal/copyright_neutral_summaries.json"  # internal: {copied span: neutral researcher wording}; never published


class Screen:
    def __init__(self, rebuild=False):
        if not rebuild and os.path.exists(CACHE): self.df, self.nrec = pickle.load(open(CACHE, "rb"))
        else:
            self.df, self.nrec = build_index(); os.makedirs(os.path.dirname(CACHE), exist_ok=True)
            pickle.dump((self.df, self.nrec), open(CACHE, "wb"))
        self.short = None
        self.neutral = json.load(open(NEUTRAL)) if os.path.exists(NEUTRAL) else {}
        self.log = collections.Counter()

    def _toks(self, s):
        for pat in (SURVEY, PROPER, DOI, CYCLES, GUIDELINE):  # proper names of data sources, identifiers and survey cycle years are not excerpts
            s = pat.sub(lambda m: "zzmaskzz".ljust(len(m.group())), s)
        return [(m.group(), m.start(), m.end()) for m in TOK.finditer(s.lower())]

    def overlaps(self, s):
        """Character spans of s covered by a word 8-gram found in a report text."""
        t = self._toks(s); cov = [False] * len(t)
        for i in range(len(t) - N + 1):
            if h(tuple(x[0] for x in t[i:i + N])) in self.df:
                for j in range(i, i + N): cov[j] = True
        spans = []; i = 0
        while i < len(t):
            if cov[i]:
                j = i
                while j + 1 < len(t) and cov[j + 1]: j += 1
                spans.append((t[i][1], t[j][2])); i = j + 1
            else: i += 1
        return spans

    def _short_df(self):
        if self.short is None:
            p = CACHE.replace(".pkl", "_short.pkl")
            if os.path.exists(p): self.short = pickle.load(open(p, "rb"))
            else:
                per = collections.defaultdict(set)
                for rid, t in sources():
                    ws = TOK.findall(norm(t))
                    for n in range(4, N): per[rid].update(h(tuple(ws[i:i + n])) for i in range(len(ws) - n + 1))
                c = collections.Counter()
                for g in per.values(): c.update(g)
                self.short = {k: min(v, 255) for k, v in c.items()}; pickle.dump(self.short, open(p, "wb"))
        return self.short

    def quoted_excerpt(self, body):
        """A quoted phrase of four or more words printed word for word in fewer than GENERIC_DF reports."""
        w = [x[0] for x in self._toks(body)]
        if len(w) < 4 or WITHHELD in body: return False
        if len(w) >= N: return any(h(tuple(w[i:i + N])) in self.df for i in range(len(w) - N + 1))
        return 0 < self._short_df().get(h(tuple(w)), 0) < GENERIC_DF

    def quotes(self, s):
        for m in QUOTE.finditer(s):
            body = next(g for g in m.groups() if g is not None)
            if self.quoted_excerpt(body): yield m

    def clean(self, s, file="", field=""):
        if not isinstance(s, str) or not s: return s
        out = s
        for a, b in sorted(self.neutral.items(), key=lambda kv: -len(kv[0])):
            if a in out: self.log[(file, field, "span summarised")] += out.count(a); out = out.replace(a, b)
        for a, b in sorted(self.overlaps(out), reverse=True):
            out = out[:a] + WITHHELD + out[b:]; self.log[(file, field, "8-gram span withheld")] += 1
        for m in sorted(self.quotes(out), key=lambda m: m.start(), reverse=True):
            out = out[:m.start()] + m.group()[0] + WITHHELD + m.group()[-1] + out[m.end():]; self.log[(file, field, "quoted excerpt withheld")] += 1
        out, k = LOC.subn(LOCATION, out)
        if k: self.log[(file, field, "location withheld")] += k
        return re.sub(r"(?:\[excerpt withheld\][\s.,;:]*){2,}", WITHHELD + " ", out)

    def write_log(self, path, title):
        with open(path, "w") as f:
            f.write(f"# {title}\n# counts only; no text of the reports is recorded here\nfile\tfield\taction\tcount\n")
            for (a, b, c), n in sorted(self.log.items()): f.write(f"{a}\t{b}\t{c}\t{n}\n")


def clean_tree(x, sc, file, field=""):
    """Clean every string of a JSON value; identifier, category and bibliographic fields are left alone."""
    KEEP = {"record_id", "decision", "code", "status", "stage", "choice", "system", "run", "field", "item", "group", "how",
            "route", "final_decision", "exclusion_code", "kind", "rule_side", "verdict", "outcome"} | BIB_KEYS
    if isinstance(x, dict): return {k: (v if k in KEEP else clean_tree(v, sc, file, k)) for k, v in x.items()}
    if isinstance(x, list): return [clean_tree(v, sc, file, field) for v in x]
    if isinstance(x, str): return sc.clean(x, file, field)
    return x


def _texts(p, rel):
    """(field, text) units of a file: string values of JSON files (bibliographic keys skipped), else the whole text."""
    t = open(p, errors="ignore").read()
    def walk(x, k=""):
        if isinstance(x, dict):
            for kk, v in x.items():
                if kk not in BIB_KEYS: yield from walk(v, kk)
        elif isinstance(x, list):
            for v in x: yield from walk(v, k)
        elif isinstance(x, str): yield k, x
    if p.endswith(".jsonl"):
        for l in t.splitlines():
            if l.strip(): yield from walk(json.loads(l))
    elif p.endswith(".json"): yield from walk(json.loads(t))
    else: yield "", t


def scan(repo, sc=None):
    """Final scan of every text file of the package: 8-gram overlaps, quoted report excerpts and locators remaining."""
    sc = sc or Screen(); hits = collections.Counter(); n_units = 0
    for dp, _, fs in os.walk(repo):
        if "/.git" in dp: continue
        for f in fs:
            p = os.path.join(dp, f); rel = os.path.relpath(p, repo)
            if f.endswith((".pdf", ".png", ".xlsx", ".pkl")) or rel in BIB_FILES: continue
            for k, t in _texts(p, rel):
                n_units += 1
                hits[(rel, "8-gram span")] += len(sc.overlaps(t))
                if not f.endswith(".py"):  # string literals of code are labels, not quotations
                    hits[(rel, "quoted excerpt")] += sum(1 for _ in sc.quotes(t)); hits[(rel, "location")] += len(LOC.findall(t))
    return {k: v for k, v in hits.items() if v}, n_units


if __name__ == "__main__":
    if len(sys.argv) > 2 and sys.argv[1] == "scan":
        r, n = scan(sys.argv[2])
        for k, v in sorted(r.items()): print("HIT", k, v)
        print(f"text units scanned: {n}; remaining hits: {sum(r.values())}"); sys.exit(1 if r else 0)
    if len(sys.argv) > 1 and sys.argv[1] == "build":
        sc = Screen(rebuild=True); print("records", sc.nrec, "8-grams", len(sc.df), "short n-grams", len(sc._short_df()))
