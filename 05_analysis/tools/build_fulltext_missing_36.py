#!/usr/bin/env python3
"""Build a clickable hand-search packet for all still-missing included reports.

The list is rebuilt from the current inclusion verdicts rather than from the
original 36-report verification cohort. Any included record with no validated
PDF in ``references/pdf`` is listed.
"""

from __future__ import annotations

import csv
import json
import subprocess
from collections import Counter
from pathlib import Path
from urllib.parse import quote

ROOT = Path(__file__).resolve().parents[1]
REFS = ROOT / "references" / "refs.json"
BASE_PREFIX = ROOT / "data" / "FULL_TEXT_MISSING"


def esc(value: object) -> str:
    s = str(value or "")
    for old, new in [("\\", r"\textbackslash{}"), ("&", r"\&"), ("%", r"\%"),
                     ("$", r"\$"), ("#", r"\#"), ("_", r"\_"), ("{", r"\{"),
                     ("}", r"\}"), ("~", r"\textasciitilde{}"), ("^", r"\textasciicircum{}")]:
        s = s.replace(old, new)
    return " ".join(s.split())


def platform(doi: str, journal: str) -> tuple[str, str]:
    d = (doi or "").lower()
    rules = [
        ("10.1109/", "IEEE Xplore", "institutional access likely"),
        ("10.1007/", "SpringerLink", "institutional access likely"),
        ("10.1016/", "ScienceDirect", "institutional access likely"),
        ("10.1080/", "Taylor & Francis", "institutional access likely"),
        ("10.1145/", "ACM Digital Library", "institutional access likely"),
        ("10.3390/", "MDPI", "open access"),
        ("10.2196/", "JMIR/preprint", "open access or preprint"),
        ("10.2139/", "SSRN", "open preprint"),
        ("10.6703/", "Society journal", "publisher or library search"),
    ]
    for prefix, name, access in rules:
        if d.startswith(prefix):
            return name, access
    if not doi:
        return ("KCI or journal website" if any(x in (journal or "").lower() for x in ("한국", "korean"))
                else "Journal/conference website", "manual title search")
    return "DOI landing page", "access varies"


def href(url: str, label: str) -> str:
    return rf"\href{{\detokenize{{{url}}}}}{{{esc(label)}}}" if url else ""


def main() -> None:
    refs = {r["key"]: r for r in json.loads(REFS.read_text(encoding="utf-8"))}
    keys = [
        key for key, ref in refs.items()
        if ref.get("verdict") == "INCLUDE"
        and not (
            ref.get("pdf_file")
            and (ROOT / "references" / "pdf" / ref["pdf_file"]).is_file()
        )
    ]

    rows = []
    for key in keys:
        r = refs[key]
        doi = r.get("doi") or ""
        plat, access = platform(doi, r.get("journal") or "")
        doi_url = f"https://doi.org/{doi}" if doi else ""
        pubmed = f"https://pubmed.ncbi.nlm.nih.gov/{r['pmid']}/" if r.get("pmid") else ""
        openalex = r.get("oa_id") or ""
        title_search = "https://scholar.google.com/scholar?q=" + quote(r.get("title") or "")
        rows.append({
            "key": key, "year": r.get("year") or "", "title": r.get("title") or "",
            "authors": r.get("authors") or "", "journal": r.get("journal") or "",
            "doi": doi, "platform": plat, "access_hint": access,
            "doi_url": doi_url, "publisher_url": r.get("landing") or doi_url,
            "pubmed_url": pubmed, "openalex_url": openalex,
            "title_search_url": title_search, "save_as": f"{key}.pdf",
            "source": ", ".join(r.get("sources") or []),
        })
    rows.sort(key=lambda r: (r["platform"], -(int(r["year"]) if r["year"] else 0), r["key"]))
    base = Path(f"{BASE_PREFIX}_{len(rows)}")

    fields = ["key", "year", "title", "authors", "journal", "doi", "platform",
              "access_hint", "doi_url", "publisher_url", "pubmed_url", "openalex_url",
              "title_search_url", "save_as", "source"]
    with base.with_suffix(".tsv").open("w", encoding="utf-8-sig", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=fields, delimiter="\t")
        writer.writeheader()
        writer.writerows(rows)

    counts = Counter(r["platform"] for r in rows)
    md = [
        f"# 전문 미확보 포함논문 {len(rows)}편—수동 확보 확인 목록", "",
        f"현재 포함 연구 중 전문이 미확보된 {len(rows)}편이다. 링크에서 PDF를 확보하면 파일명을 `인용키.pdf`로 바꾸어 프로젝트 루트에 놓는다.", "",
        "| 플랫폼 | 건수 |", "|---|---:|",
    ]
    md.extend(f"| {name} | {n} |" for name, n in counts.most_common())
    md += ["", "| # | 인용키 | 연도 | 논문 | 링크 | 저장 파일명 |", "|---:|---|---:|---|---|---|"]
    for i, r in enumerate(rows, 1):
        links = []
        for label, col in (("DOI", "doi_url"), ("Publisher", "publisher_url"),
                           ("PubMed", "pubmed_url"), ("OpenAlex", "openalex_url"),
                           ("Title search", "title_search_url")):
            if r[col] and r[col] not in [x[1] for x in links]:
                links.append((label, r[col]))
        link_text = " · ".join(f"[{label}]({url})" for label, url in links)
        md.append(f"| {i} | `{r['key']}` | {r['year']} | {r['title'].replace('|', '/')} | {link_text} | `{r['save_as']}` |")
    base.with_suffix(".md").write_text("\n".join(md) + "\n", encoding="utf-8")

    blocks = []
    for i, r in enumerate(rows, 1):
        links = [href(r["doi_url"], "DOI") if r["doi_url"] else "",
                 href(r["publisher_url"], "Publisher") if r["publisher_url"] and r["publisher_url"] != r["doi_url"] else "",
                 href(r["pubmed_url"], "PubMed") if r["pubmed_url"] else "",
                 href(r["openalex_url"], "OpenAlex") if r["openalex_url"] else "",
                 href(r["title_search_url"], "Title search")]
        links = r" \quad ".join(x for x in links if x)
        blocks.append(rf"""
\noindent\colorbox{{gray!12}}{{\parbox{{0.975\linewidth}}{{\textbf{{{i}. {esc(r['key'])} ({esc(r['year'])})}} \hfill {esc(r['platform'])}}}}}\\[1mm]
\textbf{{{esc(r['title'])}}}\\
{esc(r['authors'])}\\
\textit{{{esc(r['journal'])}}} \quad DOI: {esc(r['doi'] or 'none')}\\
Access: {esc(r['access_hint'])} \quad Source: {esc(r['source'])}\\
{links}\\
\textbf{{Save as:}} \texttt{{{esc(r['save_as'])}}}
\par\vspace{{2mm}}
""")
    tex = rf"""\documentclass[9pt]{{extarticle}}
\usepackage[a4paper,margin=14mm]{{geometry}}
\usepackage{{fontspec,xetexko,xcolor,hyperref,xurl}}
\setmainfont{{Noto Serif CJK KR}}
\setsansfont{{Noto Sans CJK KR}}
\setmonofont{{Noto Sans Mono CJK KR}}
\hypersetup{{colorlinks=true,urlcolor=blue}}
\setlength{{\parindent}}{{0pt}}
\begin{{document}}
{{\Large\sffamily\bfseries 전문 미확보 포함논문 {len(rows)}편—수동 확보 확인 목록}}\\[2mm]
링크를 클릭해 원문 PDF를 확인하십시오. 확보한 파일은 표시된 인용키 파일명으로 바꾸어 프로젝트 루트에 놓으면 됩니다.\\[3mm]
{"".join(blocks)}
\end{{document}}
"""
    base.with_suffix(".tex").write_text(tex, encoding="utf-8")
    subprocess.run(["xelatex", "-interaction=nonstopmode", "-halt-on-error",
                    "-output-directory", str(base.parent), str(base.with_suffix('.tex'))],
                   cwd=ROOT, check=True, stdout=subprocess.DEVNULL)
    print(f"built {base.with_suffix('.pdf').relative_to(ROOT)} ({len(rows)} reports)")


if __name__ == "__main__":
    main()
