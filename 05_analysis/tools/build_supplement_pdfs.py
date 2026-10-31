"""Build the eight active reader-facing Additional files."""
import csv, glob, json, subprocess, unicodedata
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
APP = ROOT / "manuscript/appendices"
SRC = (ROOT / "project_archive/paper_cleanup_20260918_002038/internal/"
       "supplement_sources")
OUT = APP / "pdf"


def esc(value):
    s = "".join(ch if unicodedata.category(ch) != "Cc" else " " for ch in str(value or ""))
    for a, b in [("\\", r"\textbackslash{}"), ("&", r"\&"), ("%", r"\%"),
                 ("$", r"\$"), ("#", r"\#"), ("_", r"\_"), ("{", r"\{"),
                 ("}", r"\}"), ("~", r"\textasciitilde{}"), ("^", r"\textasciicircum{}")]:
        s = s.replace(a, b)
    return " ".join(s.split())


def cap(value, n=500):
    s = join(value)
    return s if len(s) <= n else s[:n].rstrip() + " […]"


def join(value):
    if isinstance(value, list):
        return "; ".join(map(str, value))
    return str(value or "")


def latex_document(title, blocks, every):
    head = rf'''\documentclass[8pt]{{extarticle}}
\usepackage[a4paper,landscape,margin=8mm]{{geometry}}
\usepackage{{fontspec,xetexko,tabularx,array,xcolor,hyperref,graphicx}}
\setmainfont{{Noto Serif CJK KR}}\setsansfont{{Noto Sans CJK KR}}
\setmonofont{{Noto Sans Mono CJK KR}}
\hypersetup{{hidelinks}}\pagestyle{{plain}}\setlength{{\parindent}}{{0pt}}
\setlength{{\tabcolsep}}{{3pt}}\renewcommand{{\arraystretch}}{{1.05}}
\newcolumntype{{L}}{{>{{\raggedright\arraybackslash}}X}}
\begin{{document}}
{{\Large\sffamily\bfseries {esc(title)}}}\par\medskip
'''
    body = []
    for i, block in enumerate(blocks):
        if i and i % every == 0:
            body.append(r"\newpage")
        body.append(block)
    return head + "\n".join(body) + "\n\\end{document}\n"


def build_tex(name, title, blocks, every):
    tex = OUT / f"{name}.tex"
    tex.write_text(latex_document(title, blocks, every))
    subprocess.run(["xelatex", "-interaction=nonstopmode", "-halt-on-error", tex.name],
                   cwd=OUT, check=True, stdout=subprocess.DEVNULL)


def build_appendix6():
    refs = {r["key"]: r for r in json.load(open(ROOT / "references/refs.json"))}
    ext = {d["key"]: d for p in glob.glob(str(ROOT / "data/extraction/*.json"))
           for d in [json.load(open(p))]}
    rows = sorted((r for r in refs.values() if r.get("verdict") == "INCLUDE" and
                   ext.get(r["key"], {}).get("source") == "full_text"),
                  key=lambda r: (-(r.get("year") or 0), r["key"]))
    blocks = []
    for i, r in enumerate(rows, 1):
        d = ext.get(r["key"], {})
        line1 = f"{i}. {r['key']} ({r.get('year')}); {r.get('journal') or 'Journal NR'}"
        pairs = [
            ("Topic / task", f"{r.get('category') or 'NR'} / {d.get('task') or 'NR'}"),
            ("Survey cycles / n / source", f"{join(d.get('knhanes_waves')) or 'NR'} / {d.get('n_final') or 'NR'} / {d.get('source') or 'NR'}"),
            ("Data layers", cap(d.get("variables")) or "NR"), ("Missing data", cap(d.get("missing_handling"), 350) or "NR"),
            ("Survey design", cap(d.get("survey_weights"), 350) or "NR"), ("Models", cap(d.get("models"), 350) or "NR"),
            ("Best model", cap(d.get("best_model"), 350) or "NR"), ("Validation", cap(d.get("validation"), 400) or "NR"),
            ("Performance", cap(d.get("metrics")) or "NR"), ("Interpretability", cap(d.get("interpretability"), 400) or "NR"),
        ]
        cells = " ".join(rf"\textbf{{{esc(k)}}} & {esc(v)} \\" for k, v in pairs)
        blocks.append(rf'''\begin{{minipage}}{{\linewidth}}\noindent\colorbox{{gray!12}}{{\parbox{{0.975\linewidth}}{{\textbf{{{esc(line1)}}}}}}}\par\vspace{{1mm}}
\begin{{tabularx}}{{\linewidth}}{{>{{\bfseries}}p{{3.5cm}}L}}{cells}\end{{tabularx}}\par\vspace{{1.5mm}}\hrule\vspace{{2mm}}\end{{minipage}}''')
    build_tex("appendix6", f"Multimedia Appendix 6. Characteristics of Included Studies (n={len(rows)})", blocks, 2)


def build_appendix10():
    with open(ROOT / "data/TARGET_DEFINITION_AUDIT.tsv", encoding="utf-8-sig") as f:
        rows = list(csv.DictReader(f, delimiter="\t"))
    blocks = []
    for i, r in enumerate(rows, 1):
        line1 = f"{i}. {r['key']} ({r['year']}); {r['topic']}"
        pairs = [
            ("Outcome", r["outcome"]), ("Operational definition", cap(r["outcome_definition"], 800) or "NR"),
            ("Construction", r["outcome_construction"]), ("Cutoff reporting / basis", f"{r['cutoff_reported']} / {r['cutoff_basis']}"),
            ("Classification", f"{r['classification_scheme']}; classes={r['n_classes'] or 'NR'}"),
            ("Evidence excerpt", cap(r["source_text"], 800) or "NR"),
        ]
        cells = " ".join(rf"\textbf{{{esc(k)}}} & {esc(v)} \\" for k, v in pairs)
        blocks.append(rf'''\begin{{minipage}}{{\linewidth}}\noindent\colorbox{{gray!12}}{{\parbox{{0.975\linewidth}}{{\textbf{{{esc(line1)}}}}}}}\par\vspace{{1mm}}
\begin{{tabularx}}{{\linewidth}}{{>{{\bfseries}}p{{4.0cm}}L}}{cells}\end{{tabularx}}\par\vspace{{1.5mm}}\hrule\vspace{{2mm}}\end{{minipage}}''')
    build_tex("appendix10", f"Multimedia Appendix 10. Classification Outcomes, Discretisation, and Class Structure (n={len(rows)})", blocks, 3)


def build_appendix11():
    with open(ROOT / "data/INTEGRATED_STUDY_AUDIT.tsv", encoding="utf-8-sig") as f:
        canonical_ids = {r["key"] for r in csv.DictReader(f, delimiter="\t")}
    with open(ROOT / "data/ARTICLE_SUPPLEMENT_AUDIT.tsv", encoding="utf-8-sig") as f:
        studies = [r for r in csv.DictReader(f, delimiter="\t") if r["key"] in canonical_ids]
    with open(ROOT / "references/supplements/manifest.tsv", encoding="utf-8-sig") as f:
        files = [r for r in csv.DictReader(f, delimiter="\t") if r["key"] in canonical_ids]
    blocks = [
        rf'''\begin{{minipage}}{{\linewidth}}\textbf{{Study-level retrieval audit}}. We searched PMC/Europe PMC,
publisher pages, and links embedded in main PDFs. ``Not identified'' means not found in reachable sources,
not proven absence. Public files were archived locally and re-reviewed with the main report.\end{{minipage}}'''
    ]
    for i, r in enumerate(studies, 1):
        line = f"{i}. {r['key']} ({r['year']}): {r['supplement_status']}"
        detail = f"Files={r['files_archived']}; checked={r['source_types_checked'] or 'No reachable source recorded'}; {r['note']}"
        blocks.append(rf'''\begin{{minipage}}{{\linewidth}}\noindent\colorbox{{gray!12}}{{\parbox{{0.975\linewidth}}{{\textbf{{{esc(line)}}}}}}}\par
{esc(detail)}\par\vspace{{1mm}}\end{{minipage}}''')
    blocks.append(r"\newpage\textbf{File manifest: URL, local file, size, and SHA-256}\par\medskip")
    for i, r in enumerate(files, 1):
        line = f"{i}. {r['key']}: {r['filename']} ({r['bytes']} bytes)"
        detail = f"Source={r['source']}; URL={r['final_url'] or r['source_url']}; Local={r['local_path']}; SHA-256={r['sha256']}"
        blocks.append(rf'''\begin{{minipage}}{{\linewidth}}\noindent\textbf{{{esc(line)}}}\par
\scriptsize {esc(detail)}\par\vspace{{1mm}}\end{{minipage}}''')
    build_tex("appendix11", "Multimedia Appendix 11. Article Supplement Retrieval and Re-review Audit", blocks, 5)


def build_markdown_appendices():
    sources = {
        1: SRC / "appendix1_prisma_checklist.md",
        # The reader must be able to create one complete study JSON from AF2
        # alone.  Use the full 382-item protocol, including response options,
        # skip rules, evidence requirements, units, and derived-view rules;
        # the former three-table synopsis is retained only in the archive.
        2: ROOT / "KNHANES_ML_study_audit_protocol.md",
        3: SRC / "appendix4_search_strategy.md",
        4: SRC / "archive_pre_embedded_20260914/additional_file3_evidence_nonclassification.md",
        5: SRC / "archive_pre_embedded_20260914/additional_file5_analytic_function.md",
        6: SRC / "archive_pre_embedded_20260914/additional_file4_classification.md",
        7: SRC / "archive_pre_embedded_20260914/additional_file6_appraisal.md",
        8: SRC / "appendix8_integrated_study_audit.md",
    }
    for n, src in sources.items():
        cmd = ["pandoc", str(src), "-o", str(OUT / f"appendix{n}.pdf"), "--pdf-engine=xelatex",
               "--lua-filter", str(ROOT / "tools/appendix_table_widths.lua"),
               "--resource-path", str(ROOT),
               "-V", "documentclass=extarticle", "-V", "geometry:landscape", "-V", f"geometry:margin={'5mm' if n == 1 else '8mm'}",
               "-V", "papersize=a4",
               "-V", "fontsize=8pt", "-V", "mainfont=DejaVu Serif", "-V", "sansfont=DejaVu Sans",
               "-V", "monofont=DejaVu Sans Mono", "-V", "CJKmainfont=Noto Serif CJK KR",
               "-V", "CJKsansfont=Noto Sans CJK KR", "-V", r"header-includes:\usepackage{graphicx}",
               "-V", r"header-includes:\usepackage{needspace}",
               "--metadata", f"pagetitle=Multimedia Appendix {n}"]
        if n == 1:
            cmd[cmd.index("--metadata"):cmd.index("--metadata")] = ["-V", r"header-includes:\AtBeginDocument{\fontsize{7}{8}\selectfont}"]
        subprocess.run(cmd, check=True, stdout=subprocess.DEVNULL)


def main():
    OUT.mkdir(parents=True, exist_ok=True)
    subprocess.run(["python", str(ROOT / "tools/add_classification_reason_codes.py")], check=True)
    subprocess.run(["python", str(ROOT / "tools/build_expanded_model_task_audit.py")], check=True)
    subprocess.run(["python", str(ROOT / "tools/build_protocol_v1_2_integrated_audit.py")], check=True)
    subprocess.run(["python", str(ROOT / "tools/build_embedded_summary_tables.py")], check=True)
    # Additional files 4--7 are active reader-facing outputs even though their
    # source snapshots live under the historical directory name. Refresh those
    # sources before PDF conversion so protocol labels cannot drift from figures.
    subprocess.run(["python", str(ROOT / "tools/build_final_consensus_supplements.py")], check=True)
    build_markdown_appendices()
    for n in range(1, 9):
        path = OUT / f"appendix{n}.pdf"
        if not path.exists():
            raise RuntimeError(f"Missing {path}")
        print(path.relative_to(ROOT))


if __name__ == "__main__":
    main()
