#!/usr/bin/env python3
"""Protect proper nouns and acronyms in BibTeX titles so that sentence-casing styles (elsarticle-num) keep them
(review 2026-10-24: "The korea national health ... (knhanes)", "Tripod+ai", "Uk biobank"). Idempotent.

    python tools/protect_bib_titles.py manuscript/references.bib manuscript/supporting_refs.bib
"""
import re
import sys

PHRASES = ["Korea National Health and Nutrition Examination Survey", "National Health and Nutrition Examination Survey",
           "Demographic and Health Surveys", "UK Biobank", "Achilles"]
WORD = re.compile(r"(?<![{\w])([A-Za-z]*[A-Z][A-Za-z]*[A-Z][\w+\-]*|Korea|Korean|Shapley|Bayesian|Gaussian|Asian|Medicare)(?![\w}])")


def protect(title):
    out, depth, buf = [], 0, ""
    for ch in title:  # only touch text at brace depth 0
        if ch == "{":
            if depth == 0 and buf:
                out.append(fix(buf)); buf = ""
            depth += 1; out.append(ch)
        elif ch == "}":
            depth -= 1; out.append(ch)
        elif depth == 0:
            buf += ch
        else:
            out.append(ch)
    if buf:
        out.append(fix(buf))
    return "".join(out)


def fix(text):
    for p in PHRASES:
        text = re.sub(rf"(?<!{{){re.escape(p)}(?!}})", "{" + p + "}", text, flags=re.I) if p.lower() in text.lower() else text
    parts = re.split(r"(\{[^{}]*\})", text)
    return "".join(x if x.startswith("{") else WORD.sub(r"{\1}", x) for x in parts)


def process(path):
    s = open(path, encoding="utf-8").read()
    out, i, n = [], 0, 0
    for m in re.finditer(r"\btitle\s*=\s*\{", s, flags=re.I):
        j = m.end(); depth = 1; k = j
        while depth:
            depth += {"{": 1, "}": -1}.get(s[k], 0); k += 1
        old = s[j:k - 1]; new = protect(old)
        out.append(s[i:j] + new); i = k - 1; n += old != new
    out.append(s[i:])
    open(path, "w", encoding="utf-8").write("".join(out))
    print(path, "titles changed:", n)


if __name__ == "__main__":
    for p in sys.argv[1:]:
        process(p)
