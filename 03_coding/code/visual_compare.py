"""Comparison of two transcriptions of one page (kept apart from visual_run.py so that the transcription configuration
is not changed by comparison rules).

Objects are matched by normalised label in order of appearance; a label present in only one transcription, or a
different kind of object (table vs figure), is a difference.
- Table (TABLE or TABLE_AS_IMAGE): every Markdown table row is reduced to the sequence of its non-empty cells after
  normalisation (markup removed, whitespace removed, Unicode minus/dashes unified, lower case). The two row sequences
  must be identical: a value moved to another row or column, a changed digit (12 -> 21), a changed sign, unit or
  category label, and a merged cell written once by one transcription and repeated by the other are all differences.
  Every Markdown cell keeps its column position (an empty cell is a cell). Text outside the grid
(footnotes, caption) is compared by its multiset of numbers and, conservatively, by its normalised wording.
- Figure: the multiset of all exact numbers (every printed number, including one- and two-digit integers) must be
  identical. Values read from a plot are written with "~" by the assessor; they are kept apart in each transcription
  (a value is approximate only in the transcription that marks it) and compared separately: a difference in approximate
  readings is a review flag. Both transcriptions are always preserved.
Review flags (status NEEDS_REVIEW, no further round): figure transcriptions that agree on every exact number but are
worded differently (label-value associations, training/testing assignments or diagram connections cannot be verified
by comparison), table notes or captions worded differently, differing approximate readings, and any illegible or
uncertain content reported by either assessor, and a different continuation flag (continued from an earlier page).
compare(a, b) -> (blocking differences: str, review flags: list[str])."""
import collections, difflib, re

NUM = re.compile(r"(?<![\w.~≈])[-−–]?\d+(?:,\d{3}(?!\d))*(?:[.·]\d+)?(?:%|‰)?")
APPROX = re.compile(r"[~≈]\s*([-−–]?\d+(?:,\d{3}(?!\d))*(?:[.·]\d+)?(?:%|‰)?)")
TABLE_KINDS = {"TABLE", "TABLE_AS_IMAGE"}


def norm_num(s):
    return s.replace("−", "-").replace("–", "-").replace("·", ".")


def norm_label(s):
    s = re.sub(r"[\s.:]", "", s or "").lower()
    return s.replace("figure", "fig").replace("supplementary", "s").replace("supplemental", "s")


def norm_text(t):
    """Whole-text normalisation for the conservative prose check (markup, whitespace, dashes, case)."""
    return norm_cell(re.sub(r"\s+", " ", t or ""))


def norm_cell(c):
    c = re.sub(r"<br\s*/?>", " ", c, flags=re.I)
    c = re.sub(r"</?(?:sup|sub|b|i|em|strong|span)[^>]*>", "", c, flags=re.I)
    c = c.replace("**", "").replace("__", "").replace("\\|", "|").replace(" ", " ")
    c = c.replace("−", "-").replace("–", "-").replace("—", "-").replace("·", ".")
    return re.sub(r"\s+", "", c).lower()


def split_table(text):
    """(rows, other_text): rows = list of tuples of non-empty normalised cells, separator rows dropped."""
    rows, other = [], []
    for line in text.splitlines():
        s = line.strip()
        if s.startswith("|") and s.count("|") >= 2:
            inner = s[1:-1] if s.endswith("|") else s[1:]  # only the outer Markdown delimiters are removed
            cells = [norm_cell(c) for c in re.split(r"(?<!\\)\|", inner)]
            if all(re.fullmatch(r":?-{2,}:?", c) or c == "" for c in cells):
                continue
            rows.append(tuple(cells))  # empty cells keep their column position
        else:
            other.append(line)
    return rows, "\n".join(other)


def exact_numbers(text):
    """Multiset of numbers not marked as approximate in this text."""
    approx_spans = [m.span(1) for m in APPROX.finditer(text)]
    out = collections.Counter()
    for m in NUM.finditer(text):
        if any(a <= m.start() < b for a, b in approx_spans): continue
        out[norm_num(m.group(0))] += 1
    return out


def approx_numbers(text):
    return collections.Counter(norm_num(m.group(1)) for m in APPROX.finditer(text))


def fmt(c, n=40):
    items = sorted(c.elements())
    return ", ".join(items[:n]) + (f" ... (+{len(items) - n})" if len(items) > n else "")


def match(a, b):
    """Pairs of objects matched by label in order of appearance; unmatched objects are paired with None."""
    by = collections.defaultdict(list)
    for o in b: by[norm_label(o["label"])].append(o)
    pairs = []
    for o in a:
        k = norm_label(o["label"])
        pairs.append((o, by[k].pop(0) if by[k] else None))
    pairs += [(None, o) for v in by.values() for o in v]
    return pairs


def compare_object(x, y):
    lab = x["label"]
    fam = lambda o: "table" if o["kind"] in TABLE_KINDS else "figure"
    if fam(x) != fam(y):
        return [f"{lab}: kind A {x['kind']} / B {y['kind']}"], []
    diffs, flags = [], []
    if x.get("continued") != y.get("continued"):
        flags.append(f"{lab}: A and B differ on whether it continues from an earlier page (review)")
    for o, w in ((x, "A"), (y, "B")):
        if o["kind"] in TABLE_KINDS and "|" not in o["transcription"]:
            flags.append(f"{lab}: {w} gives this table without a grid (caption/footnote-only part or verbatim code listing; review)")
    if fam(x) == "table":
        ra, oa = split_table(x["transcription"]); rb, ob = split_table(y["transcription"])
        if ra != rb:
            sm = difflib.SequenceMatcher(None, ra, rb, autojunk=False)
            only_a = [r for op, i1, i2, j1, j2 in sm.get_opcodes() if op != "equal" for r in ra[i1:i2]]
            only_b = [r for op, i1, i2, j1, j2 in sm.get_opcodes() if op != "equal" for r in rb[j1:j2]]
            show = lambda rs: " || ".join(" | ".join(r) for r in rs[:6]) + (f" ... (+{len(rs) - 6} rows)" if len(rs) > 6 else "")
            diffs.append(f"{lab}: table rows differ ({len(only_a)} rows only in A, {len(only_b)} only in B). A: {show(only_a)} /// B: {show(only_b)}")
        na, nb = exact_numbers(oa + " " + x["caption"]), exact_numbers(ob + " " + y["caption"])
        if na != nb: diffs.append(f"{lab}: numbers outside the grid (notes, caption) only in A: {fmt(na - nb)}; only in B: {fmt(nb - na)}")
        elif norm_text(oa + x["caption"]) != norm_text(ob + y["caption"]): flags.append(f"{lab}: notes or caption worded differently (review)")
    else:
        ta, tb = x["transcription"] + " " + x["caption"], y["transcription"] + " " + y["caption"]
        na, nb = exact_numbers(ta), exact_numbers(tb)
        if na != nb: diffs.append(f"{lab}: exact numbers only in A: {fmt(na - nb)}; only in B: {fmt(nb - na)}")
        elif norm_text(ta) != norm_text(tb):
            flags.append(f"{lab}: figure transcriptions agree on every exact number but differ in wording (associations of labels, values and connections not verified; review)")
    for o, w in ((x, "A"), (y, "B")):
        if o["uncertain"].strip() or "[illegible]" in o["transcription"]: flags.append(f"{lab}: {w} reports illegible or uncertain content: {o['uncertain'][:150]}")
    pa, pb = approx_numbers(x["transcription"]), approx_numbers(y["transcription"])
    if pa != pb: flags.append(f"{lab}: approximate plot readings differ (A {sum(pa.values())}, B {sum(pb.values())} values)")
    return diffs, flags


def compare(a, b):
    diffs, flags = [], []
    for x, y in match(a, b):
        if x is None: diffs.append(f"object only in B: {y['label']} ({y['kind']})"); continue
        if y is None: diffs.append(f"object only in A: {x['label']} ({x['kind']})"); continue
        d, f = compare_object(x, y); diffs += d; flags += f
    return "\n".join(diffs), flags
