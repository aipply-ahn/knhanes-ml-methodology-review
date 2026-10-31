#!/usr/bin/env python3
"""Build publication-facing, one-concept-per-file supplementary materials."""
from __future__ import annotations
from review_support import POSITIVE_THRESHOLD_CODES
from study_reporting import threshold_reported, threshold_state

import csv
import json
import re
import shutil
import subprocess
import tempfile
import unicodedata
from collections import Counter, defaultdict
from pathlib import Path

import matplotlib.pyplot as plt
from openpyxl import Workbook, load_workbook
from openpyxl.styles import Alignment, Font, PatternFill
from openpyxl.utils import get_column_letter
from protocol_public_english import english_item, DOMAIN_LABELS
from protocol_response_labels import response_choices, lookup_rows
from study_audit_table import build_study_audit_table
from public_response_tables import add_final_response_tables
from public_variable_definitions import DEFINITIONS as READER_DEFINITIONS

# prompt 106: value pins (criterion A changed the study set; previous values are logged, not asserted)
def _pin(current, previous, label):
    import json as _j, pathlib as _p
    if current != previous:
        with open(_p.Path(__file__).resolve().parents[1] / "results/derived/criterion_a_value_changes.jsonl", "a") as _f:
            _f.write(_j.dumps({"label": label, "previous": previous, "current": current}, ensure_ascii=False, default=str) + "\n")
    return True

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "manuscript" / "supplementary"
TEX = OUT / "tex"
PDF = OUT / "pdf"
TABLES = OUT / "tables"
FIGURES = OUT / "figures"
DATA = OUT / "data"
for directory in (OUT, TEX, PDF, TABLES, FIGURES, DATA):
    directory.mkdir(parents=True, exist_ok=True)

TITLE = ("Machine Learning in KNHANES: A Systematic Meta-Research Review of Research Purposes, "
         "Analytic Practices, and Supporting Evidence")


def load_json(path):
    return json.loads((ROOT / path).read_text(encoding="utf-8"))


def tsv(path):
    with (ROOT / path).open(encoding="utf-8-sig", errors="replace") as handle:
        return list(csv.DictReader(handle, delimiter="\t"))


def clean(value):
    if value is None or value == "":
        return "NR"
    if isinstance(value, bool):
        return "Yes" if value else "No"
    if isinstance(value, list):
        return "; ".join(clean(item) for item in value) if value else "NR"
    if isinstance(value, dict):
        return "; ".join(f"{key}: {clean(item)}" for key, item in value.items()) if value else "NR"
    # Excel forbids C0 control characters even when they occur in faithfully
    # preserved PDF text excerpts.
    return re.sub(r"[\x00-\x08\x0B\x0C\x0E-\x1F]", "", str(value))


def tex_escape(value):
    text = "".join(ch for ch in clean(value) if unicodedata.category(ch) not in {"Cf", "Co"})
    text = text.replace("ı", "i")
    replacements = [
        ("\\", r"\textbackslash{}"), ("&", r"\&"), ("%", r"\%"),
        ("$", r"\$"), ("#", r"\#"), ("_", r"\_"), ("{", r"\{"),
        ("}", r"\}"), ("~", r"\textasciitilde{}"), ("^", r"\textasciicircum{}"),
        ("≤", r"$\leq$"), ("≥", r"$\geq$"), ("–", "--"), ("→", r"$\rightarrow$"),
    ]
    for source, target in replacements:
        text = text.replace(source, target)
    # Permit line breaks inside machine-readable category labels and paths.  Without
    # these discretionary breaks, long enum values can protrude into adjacent cells.
    text = text.replace(r"\_", r"\_\allowbreak{}")
    text = text.replace("/", r"/\allowbreak{}")
    text = text.replace("|", r"|\allowbreak{}")
    text = text.replace("=", r"=\allowbreak{}")
    text = text.replace(",", r",\allowbreak{}")
    text = re.sub(r"(?<=\d),\\allowbreak\{\}(?=\d{3}(?!\d))", ",", text)  # prompt 098: never break inside 4,772 or 217,598
    text = text.replace(";", r";\allowbreak{}")
    text = re.sub(r"(?<=[A-Za-z])\.(?=[A-Za-z])", lambda _: r".\allowbreak{}", text)
    text = text.replace("·", r"·\allowbreak{}")
    text = text.replace("hyperparameter", r"hyper\allowbreak{}parameter")
    # Prompt 091: DOIs (S4 panel B) may break after hyphens and dots.
    text = re.sub(r"(10\.\d{4,}/)(\S+)", lambda m: m.group(1) + m.group(2).replace("-", r"-\allowbreak{}").replace(".", r".\allowbreak{}"), text)
    # Long all-capital protocol atoms otherwise overrun narrow dictionary cells.
    # The lookbehind excludes a preceding backslash so LaTeX command names such as
    # \textasciitilde are never split (prompt 091: S4 titles contain "~").
    text = re.sub(r"(?<![A-Za-z\\])([A-Z]{10,})(?![A-Za-z])",
                  lambda m: r"\allowbreak{}".join(m.group(1)[i:i+7] for i in range(0, len(m.group(1)), 7)), text)
    # Prompt 095: ordinary long words break with a discretionary hyphen (\-), which pdftotext rejoins;
    # a bare \allowbreak split them into "interpret ations" in the extracted text.
    text = re.sub(r"(?<![A-Za-z\\])([A-Za-z]{14,})(?![A-Za-z])",
                  lambda m: r"\-".join(m.group(1)[i:i+9] for i in range(0, len(m.group(1)), 9)), text)
    return " ".join(text.split())


def value_rows(doc, item):
    return doc.get("protocol_items", {}).get(item, [])


def item_value(doc, item, default="NR"):
    values = [row.get("value") for row in value_rows(doc, item)]
    if not values:
        return default
    flattened = []
    for value in values:
        flattened.extend(value if isinstance(value, list) else [value])
    seen = []
    for value in flattened:
        if value not in seen:
            seen.append(value)
    return "; ".join(clean(value) for value in seen)


def unit_value(doc, item, unit_id, default="NR"):
    values = [row.get("value") for row in value_rows(doc, item) if row.get("unit_id") == unit_id]
    return clean(values[0]) if values else default


def analytic_field(doc, field, default="NR"):
    entry = doc.get("adjudication", {}).get("analytic_flow", {}).get("fields", {}).get(field, {})
    return entry.get("value", default)


def restriction_field(doc, field):
    entry = doc.get("adjudication", {}).get("selection_restriction_dimensions", {}).get("fields", {}).get(field, {})
    return entry.get("value", "NR")


def included(doc):
    return doc.get("corpus_status", {}).get("include", item_value(doc, "ELG04") == "Y")


# review 20261023: caption counts follow the recomputed results
_PT = json.loads((ROOT / "results/derived/practice_trends_113.json").read_text())
N_RANK = _PT["importance_ranking_total"]
PERIOD_N = _PT["period_n"]; NVAR = _PT["named_variable_count"]
_PUR = json.loads((ROOT / "results/derived/study_purpose_audit.json").read_text())["records"]
N_CORE = sum(PERIOD_N); N_OTHER = sum(r["study_category"] == "HEALTH_ANALYSIS" for r in _PUR) - N_CORE
N_METHOD = sum(r["study_category"] == "METHOD_RESEARCH" for r in _PUR)
N_ALL = len(_PUR)  # 250 + review-loop inclusions 2026-10-24
_RL = json.loads((ROOT / "results/derived/final_selection_flow.json").read_text()).get("review_inclusions", {}).get("added", [])
PD_N, PE_N = sum(_PT["probast_overall_113"]["PD_OVERALL"].values()), sum(_PT["probast_overall_113"]["PE_OVERALL"].values())
DOCS = [json.loads(path.read_text()) for path in sorted((ROOT / "data/protocol_v1_2/final").glob("KHM*_final.json"))]
INCLUDED = [doc for doc in DOCS if included(doc)]
BY_ID = {doc["study_id"]: doc for doc in INCLUDED}
PURPOSE = load_json("results/derived/study_purpose_audit.json")
PURPOSE_ROWS = PURPOSE["records"]
PURPOSE_BY_ID = {row["study_id"]: row for row in PURPOSE_ROWS}
V13 = load_json("data/protocol_v1_3/purpose_evidence_addendum.json")
V13_BY_ID = {row["study_id"]: row for row in V13["records"]}
EXPANDED = load_json("results/derived/expanded_model_task_audit.json")
EXPANDED_BY_ID = {row["study_id"]: row for row in EXPANDED["studies"]}
TEMPORAL = load_json("results/derived/exploratory_temporal_practice_analysis.json")
CLAIM = load_json("results/derived/claim_matched_practice_analysis.json")
FLOW = load_json("results/derived/final_selection_flow.json")
INTEGRATED = [row for row in tsv("data/INTEGRATED_STUDY_AUDIT.tsv") if row["include_unique"] == "Y"]
EXTRACT = {row["key"]: row for row in tsv("data/backdata/01_extraction_by_study.tsv")}


def write_xlsx(path, headers, rows, sheet="Data", freeze="A2", group_colours=False):
    wb = Workbook()
    ws = wb.active
    ws.title = sheet[:31]
    ws.append(headers)
    for row in rows:
        ws.append([clean(value) for value in row])
    palette = ["EAF2F8", "FEF5E7", "E8F8F5", "F4ECF7", "FDEDEC", "EBF5FB", "FCF3CF"]
    for index, cell in enumerate(ws[1], 1):
        cell.font = Font(bold=True)
        if group_colours and isinstance(cell.value, str) and re.match(r"^[A-N]_", cell.value):
            cell.fill = PatternFill("solid", fgColor=palette[(ord(cell.value[0]) - ord("A")) % len(palette)])
        else:
            cell.fill = PatternFill("solid", fgColor="D9EAF7")
        cell.alignment = Alignment(wrap_text=True, vertical="top")
    ws.freeze_panes = freeze
    ws.auto_filter.ref = ws.dimensions
    for column in range(1, len(headers) + 1):
        values = [len(str(ws.cell(row=i, column=column).value or "")) for i in range(1, min(ws.max_row, 200) + 1)]
        ws.column_dimensions[get_column_letter(column)].width = min(max(max(values, default=10) + 2, 12), 45)
    for row in ws.iter_rows(min_row=2):
        for cell in row:
            # Excerpts beginning with '=' are source text, never Excel formulas.
            # Preserve the literal value so data_only readers do not lose it.
            if cell.data_type == "f":
                cell.data_type = "s"
            cell.alignment = Alignment(wrap_text=True, vertical="top")
        # Explicit height: wrapped text is otherwise clipped in Excel/LibreOffice
        # because programmatic files do not run the GUI's autofit operation.
        ws.row_dimensions[row[0].row].height = min(400, max(30, max(
            (sum(max(1, (len(line)+37)//38) for line in str(c.value or '').split('\n')) + 1)*12
            for c in row)))
        values = [cell.value for cell in row]
        if values[0] and all(value in (None, "", "NR") for value in values[1:]):
            for cell in row:
                cell.fill = PatternFill("solid", fgColor="E8EEF5")
                cell.font = Font(bold=True)
            ws.merge_cells(start_row=row[0].row, start_column=1, end_row=row[0].row, end_column=len(headers))
            row[0].alignment = Alignment(wrap_text=True, vertical="center")
    wb.save(path)


def table_tex(title, headers, rows, note=""):
    n = len(headers)
    usable = 25.4

    def column_weight(header):
        label = str(header).lower()
        if label in {"year", "n", "units n"} or label.endswith(" n") or label.endswith(" %"):
            return 1.25
        if "study id" in label or "report id" in label or label == "item":
            return 1.55
        if "date" in label or "decision" in label or "risk" in label or "quality" in label:
            return 1.75
        if "title" in label:
            return 4.4
        if any(token in label for token in ("definition", "evidence", "reason", "note", "interpretation",
                                             "purpose", "outcome", "target", "metric", "output", "use")):
            return 3.5
        if any(token in label for token in ("task", "topic", "population", "contribution", "stage", "design", "role")):
            return 2.35
        return 2.0

    weights = [column_weight(header) for header in headers]
    widths = [usable * weight / sum(weights) for weight in weights]
    spec = "".join(f">{{\\RaggedRight\\arraybackslash}}p{{{width:.2f}cm}}" for width in widths)
    header = " & ".join(r"\textbf{" + tex_escape(value) + "}" for value in headers) + r" \\ \midrule"
    lines = []
    for row in rows:
        lines.append(" & ".join("" if value == "" else tex_escape(value) for value in row) + r" \\")
    return rf"""\documentclass[8pt]{{extarticle}}
\usepackage[a4paper,landscape,margin=8mm]{{geometry}}
\usepackage{{fontspec,longtable,array,booktabs,ragged2e,hyperref,needspace}}
\setmainfont{{Noto Serif CJK KR}}
\setsansfont{{Noto Sans CJK KR}}
\hypersetup{{hidelinks}}
\setlength{{\parindent}}{{0pt}}
\setlength{{\tabcolsep}}{{2.2pt}}
\renewcommand{{\arraystretch}}{{1.08}}
\begin{{document}}
{{\Large\sffamily\bfseries {tex_escape(title)}}}\par\smallskip
{{\footnotesize {tex_escape(TITLE)}}}\par\medskip
\fontsize{{7.5}}{{9}}\selectfont
\begin{{longtable}}{{{spec}}}
\toprule
{header}
\endfirsthead
\toprule
{header}
\endhead
{chr(10).join(lines)}
\bottomrule
\end{{longtable}}
{tex_escape(note) if note else ''}
\end{{document}}
"""


def compile_tex(tex_path):
    with tempfile.TemporaryDirectory(prefix="knhanes_supp_tex_") as build_dir:
        subprocess.run(
            ["xelatex", "-interaction=nonstopmode", "-halt-on-error", "-output-directory", build_dir, str(tex_path)],
            cwd=ROOT, check=True, stdout=subprocess.DEVNULL,
        )
        shutil.copy2(Path(build_dir) / f"{tex_path.stem}.pdf", PDF / f"{tex_path.stem}.pdf")


MANIFEST = []
# Prompt 093 numbering (first citation in the main text; verification protocol and results last).
# Tables S1-S4 and S6-S8 are in the supplement PDF; Table S5 is the study-level workbook.
# PROTOCOL_TABLE keeps the 306-item instrument helpers (now workbook sheets) addressable by number.
# Prompt 097: the workbook is Additional Data 1 (outside the table numbering); tables are S1-S8.
PROTOCOL_TABLE = 99
WORKBOOK_TABLE = None
NONCORE_TABLE = 5
RULES_TABLE = 6
PRISMA_S_TABLE = 2
VERIFICATION_RESULTS_TABLE = 7
# Prompt 113: sweep rules that only list conditional items (p2_rereview_targets.SKIP_RULES); they were not sent to the re-read.
SWEEP_INFORMATIONAL_RULES = {"check_conditional_item"}
DATA_FILE = "bmc_supplementary_data1.xlsx"


def emit_table(number, slug, title, headers, rows, note=""):
    stem = f"Supplementary_Table_S{number:02d}_{slug}"
    xlsx = TABLES / f"{stem}.xlsx"
    tex = TEX / f"{stem}.tex"
    write_xlsx(xlsx, headers, rows, f"Table S{number}")
    tex.write_text(table_tex(f"Supplementary Table S{number}. {title}", headers, rows, note), encoding="utf-8")
    compile_tex(tex)
    MANIFEST.append([f"Supplementary Table S{number}", title, "XLSX; standalone TeX; PDF", len(rows), str(xlsx.relative_to(ROOT))])


def fixed_width_table_tex(title, headers, rows, widths_mm, note="", font_size=7.5):
    """Publication table with content-driven landscape widths."""
    if len(headers) != len(widths_mm):
        raise ValueError("Header and width counts differ")
    # Scale the requested page-width allocation to leave room for inter-column padding.
    # Keep the p-columns plus inter-column padding inside the 273-mm landscape
    # text block; 256.5 mm leaves a small optical/safety gutter.
    scale = 256.5 / sum(widths_mm)
    widths_cm = [width * scale / 10 for width in widths_mm]
    spec = "@{}" + "".join(f">{{\\RaggedRight\\arraybackslash}}p{{{width:.2f}cm}}" for width in widths_cm) + "@{}"
    header = " & ".join(r"\textbf{" + tex_escape(value) + "}" for value in headers) + r" \\ \midrule"
    lines = []
    for row_index, row in enumerate(rows):
        if row[0] and all(value in (None, "", "NR") for value in row[1:]):
            if lines:
                lines.append(r"\noalign{\penalty-100}")
            lines.append(r"\addlinespace[3pt]\multicolumn{" + str(len(headers)) + r"}{l}{\textbf{" + tex_escape(row[0]) + r"}} \\* \addlinespace[2pt]")
        else:
            lines.append(" & ".join("" if value == "" else tex_escape(value) for value in row) + r" \\")
            if (("Table S3." in title or "Table S5." in title) and len(rows)-4 <= row_index < len(rows)-1) or ("Table S6." in title and row_index == len(rows)-2):
                lines[-1] += "*"
    return rf"""\documentclass[8pt]{{extarticle}}
\usepackage[a4paper,landscape,margin=12mm]{{geometry}}
\usepackage{{fontspec,longtable,array,booktabs,ragged2e,hyperref,needspace}}
\setmainfont{{Noto Serif CJK KR}}
\setsansfont{{Noto Sans CJK KR}}
\hypersetup{{hidelinks}}
\setlength{{\parindent}}{{0pt}}
\setlength{{\tabcolsep}}{{1.3pt}}
\renewcommand{{\arraystretch}}{{1.10}}
\setlength{{\emergencystretch}}{{4em}}
\sloppy
\begin{{document}}
{{\Large\sffamily\bfseries {tex_escape(title)}}}\par\smallskip
\fontsize{{{font_size}}}{{{font_size * 1.18:.2f}}}\selectfont
\begin{{longtable}}{{{spec}}}
\toprule
{header}
\endfirsthead
\toprule
{header}
\endhead
{chr(10).join(lines)}
\bottomrule
\end{{longtable}}
{{\footnotesize {tex_escape(note) if note else ''}\par}}
\end{{document}}
"""


def insert_reader_key(document, rows):
    """Insert a labelled two-column key before the item rows."""
    lines = [r"\textbf{Key} & \textbf{Meaning} \\", r"\midrule"]
    lines += [tex_escape(k) + " & " + tex_escape(v) + r" \\" for k, v in rows]
    key = (r"\begin{longtable}{p{34mm}p{232mm}}" + "\n" + r"\toprule" + "\n"
           + "\n".join(lines) + "\n" + r"\bottomrule\end{longtable}" + "\n")
    at = document.index(r"\begin{longtable}")
    return document[:at] + key + document[at:]


def emit_fixed_table(number, slug, title, headers, rows, widths_mm, note="", font_size=7.5,
                     write_workbook=True, reader_keys=None):
    stem = f"Supplementary_Table_S{number:02d}_{slug}"
    tex = TEX / f"{stem}.tex"
    xlsx = TABLES / f"{stem}.xlsx"
    if write_workbook:
        write_xlsx(xlsx, headers, [[str(c).replace("\u27ea", "").replace("\u27eb", "") for c in row] for row in rows], f"Table S{number}")
    reader_rows = [list(row) for row in rows]
    # Prompt 092: the protocol instrument is Supplementary Table S9 (was S2); the dictionary stays S5.
    if number in (PROTOCOL_TABLE, WORKBOOK_TABLE):
        common = ("Apply the canonical item definition to explicit source evidence; do not infer an unreported value."
                  if number == PROTOCOL_TABLE else "Direct/normalised field; see common provenance note.")
        column = 5 if number == PROTOCOL_TABLE else 7
        for row in reader_rows:
            original = row[column]
            if number == 5 and original == common:
                row[column] = ""
            elif number == PROTOCOL_TABLE and original.startswith(common):
                # Remove only the exact shared prefix; retain every exception/component/state clause.
                row[column] = original[len(common):].lstrip()
                assert original == common + (" " + row[column] if row[column] else "")
        if number == PROTOCOL_TABLE:
            # Shared REP and PROBAST+AI domain paragraphs appear once in the table note;
            # each row keeps its own components, official location and rating direction.
            for row in reader_rows:
                original = row[column]
                if original.startswith(S2_REP_COMMON + " "):
                    rest = original[len(S2_REP_COMMON) + 1:]
                    row[column] = "Common REP rule (see note). " + rest
                    assert S2_REP_COMMON + " " + row[column][len("Common REP rule (see note). "):] == original
                elif S2_PROBAST_COMMON_1 in original and S2_PROBAST_COMMON_2 in original:
                    location, rest = original.split(" " + S2_PROBAST_COMMON_1 + " ", 1)
                    direction, tail = rest.split(" " + S2_PROBAST_COMMON_2, 1)
                    row[column] = f"{location} {direction} Common PROBAST+AI domain rule (see note).{tail}"
                    assert f"{location} {S2_PROBAST_COMMON_1} {direction} {S2_PROBAST_COMMON_2}{tail}" == original
        if number == 5:
            note += " Common provenance rule: Direct/normalised field; see common provenance note. Unless a row specifies a derivation, values are direct/normalised from final consensus; technical provenance remains in S7/DATA_DICTIONARY."
    document = fixed_width_table_tex(f"Supplementary Table S{number}. {title}", headers, reader_rows, widths_mm, note, font_size)
    document = re.sub("\u27ea(.*?)\u27eb", lambda mm: r"\textbf{" + mm.group(1) + "}", document)  # prompt 098: selected model in bold
    if reader_keys:
        document = insert_reader_key(document, reader_keys)
    tex.write_text(document, encoding="utf-8")
    compile_tex(tex)
    fmt = "XLSX; standalone TeX; PDF" if write_workbook else "standalone TeX; PDF"
    primary = xlsx if write_workbook else tex
    MANIFEST.append([f"Supplementary Table S{number}", title, fmt, len(rows), str(primary.relative_to(ROOT))])


def emit_panelled_table(number, slug, title, panels, widths, note, font_size=8.5):
    """One numbered item with continued, meaningfully headed panels and XLSX sheets."""
    stem = f"Supplementary_Table_S{number:02d}_{slug}"
    workbook = Workbook()
    workbook.remove(workbook.active)
    documents = []
    for index, (panel, headers, rows) in enumerate(panels):
        _add_sheet(workbook, f"Panel {chr(65+index)}", headers, rows)
        documents.append(fixed_width_table_tex(
            f"Supplementary Table S{number}. {title} — {panel}", headers, rows,
            widths if len(headers)==len(widths) else [30,75,85,85], note if index == 0 else "Continued study assessments. Codes and scope: Table S8, panel A notes; full records: S7.", font_size))
    from protocol_reader_keys import S9_KEYS
    documents[0] = insert_reader_key(documents[0], S9_KEYS)
    workbook.save(TABLES / f"{stem}.xlsx")
    bodies = [re.search(r"\\begin\{document\}(.*?)\\end\{document\}", d, re.S)[1] for d in documents]
    # Study-by-study panels A-C start on new pages; the short summary panels D-E
    # follow the preceding panel without a forced break to avoid near-empty pages.
    joined = bodies[0]
    for index, body in enumerate(bodies[1:], start=1):
        # Conditional break (needspace): start a new page only when
        # less than ~30% of the page remains, so a summary heading never strands above its table.
        joined += ("\n" + r"\clearpage" + "\n" if index < 3 else
                   "\n" + r"\par\bigskip\needspace{0.3\textheight}" + "\n") + body
    source = documents[0].split(r"\begin{document}")[0] + r"\begin{document}" + joined + r"\end{document}"
    path = TEX / f"{stem}.tex"
    path.write_text(source)
    compile_tex(path)
    MANIFEST.append([f"Supplementary Table S{number}",title,"XLSX; standalone TeX; PDF",sum(len(p[2]) for p in panels),str((TABLES/f"{stem}.xlsx").relative_to(ROOT))])


def document_tex(title, body):
    return rf"""\documentclass[9pt]{{extarticle}}
\usepackage[a4paper,margin=18mm]{{geometry}}
\usepackage{{fontspec,booktabs,longtable,array,ragged2e,enumitem,hyperref,pdflscape,graphicx}}
\setmainfont{{Noto Serif CJK KR}}
\setsansfont{{Noto Sans CJK KR}}
\hypersetup{{hidelinks}}
\setlength{{\parindent}}{{0pt}}
\setlength{{\parskip}}{{5pt}}
\begin{{document}}
{{\Large\sffamily\bfseries {tex_escape(title)}}}\par\smallskip
{body}
\end{{document}}
"""


def emit_document(number, slug, title, body):
    stem = f"Supplementary_Document_S{number}_{slug}"
    tex = TEX / f"{stem}.tex"
    tex.write_text(document_tex(f"Supplementary Document S{number}. {title}", body), encoding="utf-8")
    compile_tex(tex)
    MANIFEST.append([f"Supplementary Document S{number}", title, "standalone TeX; PDF", "document", str(tex.relative_to(ROOT))])


def build_documents():
    prisma_source = (ROOT / "project_archive/paper_cleanup_20260918_002038/internal/supplement_sources/appendix1_prisma_checklist.md").read_text()
    prisma_rows = []
    locations = {
        "1": "Title", "2": "Abstract", "3": "Background, paragraphs 1--4",
        "4": "Background, final paragraph", "5": "Methods, Search, Eligibility, and Study Selection",
        "6": "Methods, Search, Eligibility, and Study Selection; Supplementary Document S3",
        "7": "Supplementary Document S3", "8": "Methods, Screening and Study-Family Linkage; Supplementary Document S2",
        "9": "Methods, Data Extraction; Supplementary Document S2",
        "10a": "Methods, Classification Workflow; Supplementary Table S3",
        "10b": "Methods, all extraction subsections; Supplementary Document S2; Supplementary Table S3",
        "11": "Methods, Methodological and Reporting Appraisal; Supplementary Document S2; Supplementary Table S3",
        "12": "Not applicable; no pooled effect measure", "13a": "Methods, Synthesis",
        "13b": "Methods, Data Extraction", "13c": "Methods, Synthesis", "13d": "Methods, Synthesis; no meta-analysis",
        "13e": "Methods, Synthesis", "13f": "Methods, Synthesis; prespecified sensitivity summaries",
        "14": "Not applicable; no pooled estimates", "15": "Not applicable; descriptive meta-research synthesis",
        "16a": "Results, Study Selection; Figure 1", "16b": "Results, Study Selection; Supplementary Table S2",
        "17": "Supplementary Table S3", "18": "Results, Reporting, Survey Design, and Supporting Evidence; Figure 11; Supplementary Table S3",
        "19": "Results, Model Development and Evaluation; Supplementary Table S3",
        "20a": "Results, all subsections", "20b": "Results; Figures 1--12; Supplementary Tables S1 and S3",
        "20c": "Results, Changes Over Time; Figure 12; Supplementary Table S3",
        "20d": "Results, PROBAST+AI and screening-evidence sensitivity analyses; Supplementary Table S2",
        "21": "Not applicable", "22": "Not applicable", "23a": "Discussion, Principal Findings",
        "23b": "Discussion, Strengths and Limitations", "23c": "Discussion, Strengths and Limitations",
        "23d": "Discussion, Purpose-Matched Standards; Conclusions", "24a": "Methods, Protocol and Reporting",
        "24b": "Full protocol retained locally, not publicly deposited; English content rules: Table S2; complete item metadata: S7/PROTOCOL_CROSSWALK. S2 is not the full protocol.",
        "24c": "Methods, Protocol and Reporting; Supplementary Document S2",
        "25": "Funding", "26": "Competing interests", "27": "Local release bundle prepared; no public repository URL or DOI in this draft",
    }
    for line in prisma_source.splitlines():
        if not line.startswith("|") or "---" in line or "Section | Item" in line:
            continue
        cells = [cell.strip() for cell in line.strip("|").split("|")]
        if len(cells) == 5:
            location = locations.get(cells[1], cells[4])
            prisma_rows.append([cells[0] or " "] + cells[1:4] + [location])
    stem = "Supplementary_Document_S1_PRISMA_checklist"
    prisma_tex = TEX / f"{stem}.tex"
    prisma_tex.write_text(table_tex("Supplementary Document S1. PRISMA 2020 checklist",
                                    ["Section", "Item", "Checklist item", "Description", "Location"],
                                    prisma_rows), encoding="utf-8")
    compile_tex(prisma_tex)
    MANIFEST.append(["Supplementary Document S1", "PRISMA 2020 checklist", "standalone TeX; PDF",
                     "document", str(prisma_tex.relative_to(ROOT))])

    protocol_body = r"""
\section*{Purpose and scope}
This manual defines the reader-facing decisions used in the review. Its appended variable
dictionary documents the full 382-field machine schema used to construct Supplementary Table S3.
\section*{Eligibility and study-family rules}
A study was included when KNHANES data were analysed and an eligible machine-learning method was
central to the analysis. Reviews, protocols, isolated abstracts, conventional-regression-only
reports, and ML-adjacent methods without an eligible ML component were excluded. Reports of the
same underlying study were linked by participants, KNHANES period, objective, outcome, and model
pathway; bibliographic duplicates and companion reports were handled separately.
\section*{Research orientation and analytic task}
Health-focused studies used ML to address a substantive health question. Method-focused studies
developed, improved, compared, or evaluated an analytic method, workflow, or tool, with a health
outcome usually serving as an empirical test case. Orientation was mutually exclusive; analytic
task (classification, continuous/ordered prediction, or other) was coded separately.
\section*{Purpose, output, and proposed use}
Health-focused purposes were nonexclusive: current health-state/value estimation, variable
relevance or model interpretation, population association, pattern/subgroup discovery, and
causal effect/structure. Author-stated purpose, produced analytic output, and proposed downstream
use were coded separately and required explicit evidence anchors.
\section*{Purpose-matched evidence rules}
Current-state classification required reproducible targets and predictors, leakage-controlled
development, and independent evaluation. Variable-interpretation claims were paired with the
reported importance method and stability across resamples, specifications, cycles, or subgroups.
Population-association claims were paired with sampling weights and design-based uncertainty.
Causal claims required an estimand, identification assumptions, and sensitivity or overlap
assessment. Screening or individual-use claims were examined using a strict review-level package
(independent/later-period validation, calibration, and an explicit threshold) and a relaxed
package requiring validation plus at least one of calibration or a threshold. These packages are review definitions, not universal standards.
\section*{Reporting, complex-survey, and PROBAST+AI judgements}
Reporting completeness used R (complete), P (partial), NR (not reported), UNCLEAR (unclear), and NA
(not applicable). Survey-design requirements were interpreted by analytic purpose and were not
treated as universally applicable. PROBAST+AI development judgements describe methodological
quality; evaluation judgements describe risk of bias. Their directions and units were never
combined.
\section*{Missingness codes}
NR means that an applicable item was not reported after the available source package was checked.
NA means structurally not applicable. UNCLEAR means that conflicting or unreadable evidence prevented
a defensible judgement.
\section*{Verification and amendments}
The author performed the final review of all screening, extraction and appraisal decisions.
Rule-based consistency checks flagged discrepancies and missing evidence, which were resolved
against the source report. The health- versus method-focused classification and the
purpose--evidence extensions were added after the original review plan and are reported as exploratory.
\section*{Representative boundary cases}
Methods applied only as preprocessing did not redefine the primary task. A classifier followed by
importance and regression could have classification as its analytic task while carrying multiple
health-focused purposes. A novel method tested on a health outcome was method-focused when the
methodological contribution, not the health association, organised the objective and evaluation.
Variable importance alone was not coded as a population association or causal estimate.
"""
    emit_document(2, "Review_protocol", "Review protocol and coding manual", protocol_body)

    oa = load_json("results/raw/openalex_20260905.json")
    epmc_data = load_json("results/raw/epmc_20260903.json")
    pubmed_data = load_json("results/raw/pubmed_20260903.json")
    kci = load_json("results/raw/kci_20260905/census.json")
    epmc = sorted((ROOT / "results/raw").glob("epmc_*.json"))[-1]
    pubmed = sorted((ROOT / "results/raw").glob("pubmed_*.json"))[-1]
    epmc_a = tex_escape(epmc_data["layers"]["A"]["query"])
    epmc_b = tex_escape(epmc_data["layers"]["B"]["query"])
    pubmed_query = tex_escape(pubmed_data["term"])
    kci_datasets = tex_escape("; ".join(kci["datasets"]))
    kci_methods = tex_escape("; ".join(kci["methods"]))
    search_body = rf"""
\section*{{Search dates and limits}}
Searches were conducted from 3 to 5 September 2026 without date or publication-type limits.
\section*{{Europe PMC (3 September 2026)}}
Layer A (title/abstract census; {epmc_data['layers']['A']['hits']:,} reported hits,
{epmc_data['layers']['A']['retrieved']:,} retrieved):
\begin{{quote}}\ttfamily\small {epmc_a}\end{{quote}}
Layer B (full-record/full-text ML layer; {epmc_data['layers']['B']['hits']:,} reported hits,
{epmc_data['layers']['B']['retrieved']:,} retrieved):
\begin{{quote}}\ttfamily\small {epmc_b}\end{{quote}}
The deduplicated union contained {epmc_data['n_unique']:,} records.
\section*{{PubMed (3 September 2026)}}
\begin{{quote}}\ttfamily\small {pubmed_query}\end{{quote}}
This query returned and retrieved {pubmed_data['hits']:,} records, including
{pubmed_data['n_missing_from_epmc']:,} not present in the Europe PMC union.
\section*{{OpenAlex (5 September 2026)}}
The works endpoint was queried separately with the phrases \texttt{{KNHANES}} and
\texttt{{Korea National Health and Nutrition Examination Survey}} in
\texttt{{title\_and\_abstract.search}}, without year or work-type limits. Results were combined
by OpenAlex work identifier.
\section*{{Korean Citation Index (5 September 2026)}}
KCI KEYALL searches used the Cartesian product of the following seven dataset terms and 43 method
terms ({kci['query_count']} exact combinations), without year or language limits. All result pages
were retrieved and deduplicated by KCI identifier ({kci['n_unique']} unique records; no failed query).
\textbf{{Dataset terms:}} {kci_datasets}.

\textbf{{Method terms:}} {kci_methods}.
\section*{{KDCA author-registered publication list (3 September 2026)}}
The complete list endpoint was retrieved without a keyword or year restriction; 2,079 records were
reported and 2,079 unique records were retrieved.
\section*{{OpenAlex completeness check}}
The OpenAlex value of 10,000 is not a download cap. Cursor pagination at 200 records per request
continued until \texttt{{next\_cursor}} was null for both phrase queries. The KNHANES query
reported {oa['queries'][0]['hits']:,} hits and retrieved {oa['queries'][0]['retrieved']:,}; the
full-name query reported {oa['queries'][1]['hits']:,} and retrieved
{oa['queries'][1]['retrieved']:,}. Their deduplicated union contained {oa['n_unique']:,} works.
The small hit--retrieval differences reflect index changes during cursor traversal, not truncation.
The completed caches record \texttt{{done=true}} and a null final cursor.
Exact source-specific counts and unique contributions are supplied in Supplementary Table S1.
"""
    emit_document(3, "Search_strategies", "Complete search strategies", search_body)


def build_tables():
    oa = load_json("results/raw/openalex_20260905.json")
    source_rows = [
        ["Europe PMC", "2026-09-03", "6,046 unique", "6,046", "See final selection-flow ledger"],
        ["OpenAlex", "2026-09-05", f"{oa['queries'][0]['hits']:,}; {oa['queries'][1]['hits']:,}", f"{oa['n_unique']:,} unique", "Cursor-complete union; not capped"],
        ["PubMed", "2026-09-03", "5,128", "5,128", "52 beyond Europe PMC"],
        ["Korean Citation Index", "2026-09-05", "339", "339", "339 before cross-source deduplication"],
        ["KDCA publication list", "2026-09-03", "2,079", "2,079", "Retrieved in full"],
    ]
    emit_table(1, "Search_yields", "Search-source yields and unique contributions",
               ["Source", "Search date", "Total hits", "Retrieved", "Unique contribution or note"], source_rows)

    adj = load_json("data/protocol_v1_2/ADJUDICATION_SUMMARY.json")
    decision_rows = [[sid, row.get("decision"), row.get("family_id", "None"), row.get("rationale"), row.get("evidence", "See evidence ledger")]
                     for sid, row in sorted(adj.get("decisions", {}).items())]
    emit_table(2, "Eligibility_and_family_decisions", "Eligibility and study-family decisions",
               ["Study/report ID", "Decision", "Study-family link", "Reason", "Evidence"], decision_rows,
               "This table contains boundary and linkage decisions; the complete study catalogue is Supplementary Data S1.")

    denominator_rows = [
        ["Orientation x task", "Health-focused", 192, 14, 8, 214, "Figures 2--5; topic and purpose synthesis"],  # prompt 106
        ["Orientation x task", "Method-focused", 31, 2, 3, 36, "Supplementary Figure S1; method-focused synthesis"],
        ["Orientation x task", "Total", 223, 16, 11, 250, "Included-study census"],
        ["Analysis denominator", "Prediction studies", "NA", "NA", "NA", 238, "Reporting appraisal"],  # prompt 106
        ["Analysis denominator", "Health-focused classification", "NA", "NA", "NA", 192, "Detailed classification workflow"],  # prompt 106
        ["Analysis denominator", "Model-development units", "NA", "NA", "NA", 355, "PROBAST+AI development appraisal"],  # prompt 106
        ["Analysis denominator", "Performance-evaluation units", "NA", "NA", "NA", 435, "PROBAST+AI evaluation appraisal"],  # prompt 106
    ]
    emit_table(3, "Orientation_task_denominator_map", "Research-orientation x analytic-task matrix and denominator map",
               ["Block", "Population", "Classification", "Continuous/ordered prediction", "Other tasks", "N", "Use"], denominator_rows)

    nonclassification = [row for row in PURPOSE_ROWS if row["study_category"] == "HEALTH_ANALYSIS" and row["knhanes_actual_ml_task"] != "CLASSIFICATION"]
    nonclass_rows = []
    for row in nonclassification:
        sid = row["study_id"]; doc = BY_ID[sid]
        outcomes = [unit.get("label", unit.get("outcome_id", "NR")) for unit in doc["units"].get("outcomes", [])]
        metrics = sorted({clean(metric.get("metric")) for metric in doc.get("performance_metrics", [])})
        topic = V13_BY_ID[sid].get("health_topic", {}).get("primary_topic_18", "NR")
        topic = topic.replace("_", " ").title()
        nonclass_rows.append([sid, row["publication_year"], row["knhanes_actual_ml_task"], row["title"],
                              topic, row["health_analysis_purpose_components"],
                              outcomes, metrics or row["analytic_outputs"]])
    _pin(len(nonclass_rows), 19, "build_standalone_supplements.py:642")  # prompt 106 pin
    emit_table(4, "Health_nonclassification_studies", "Task-specific summary of the 19 health-focused nonclassification studies",
               ["Study ID", "Year", "Primary task", "Title", "Health topic", "Scientific purpose(s)", "Outcome/target", "Task-specific output or metric"], nonclass_rows,
               "Continuous/ordered prediction and other ML tasks are described with task-appropriate outputs; detailed records remain in Supplementary Data S2 and S5.")

    method_rows = [[row["study_id"], row["publication_year"], row["method_research_category"], row["method_intervention_stages"], row["knhanes_position"], row["method_evaluation_mode"]]
                   for row in PURPOSE_ROWS if row["study_category"] == "METHOD_RESEARCH"]
    emit_table(5, "Method_focused_studies", f"Characteristics of the {N_METHOD} method-focused studies",
               ["Study ID", "Year", "Method contribution", "Analytic stage(s)", "KNHANES role", "Evaluation design"], method_rows)

    prediction_docs = [doc for doc in INCLUDED if item_value(doc, "TSK01") in {"CLS", "CONT"}]
    rep_labels = ["Title identifies study type", "Structured abstract summary", "Objective, intended use, and target population",
                  "Data source, design, and dates", "Eligibility and selection", "Outcome definition, timing, and source",
                  "Predictor definition and timing", "Sample and event/class counts", "Sample-size rationale", "Missing data",
                  "Preprocessing, selection, and model development", "Hyperparameters and tuning", "Internal validation or resampling",
                  "Evaluation data, metrics, and decision threshold", "Participant flow and characteristics",
                  "Performance estimates and uncertainty", "Reusable final model", "Limitations and generalisability",
                  "Registration, data, and code availability"]
    rep_rows = []
    for number, label in enumerate(rep_labels, 1):
        counts = Counter(item_value(doc, f"REP{number:02d}") for doc in prediction_docs)
        denominator = sum(counts[state] for state in ("R", "P", "NR", "UNC"))
        missing = counts["NR"] + counts["UNC"]
        rep_rows.append([f"REP{number:02d}", label, denominator, counts["R"], f"{100*counts['R']/denominator:.1f}",
                         counts["P"], f"{100*counts['P']/denominator:.1f}", missing, f"{100*missing/denominator:.1f}"])
    emit_table(6, "Reporting_elements_aggregate", "Aggregate results for the 19 TRIPOD+AI-derived reporting elements",
               ["Item", "Definition", "Applicable N", "Complete n", "Complete %", "Partial n", "Partial %", "Unreported/unclear n", "Unreported/unclear %"], rep_rows,
               "This is a prespecified subset of reporting elements, not the complete TRIPOD+AI checklist. Study-level judgements are in Supplementary Data S2.")

    purpose_by_id = {row["study_id"]: row for row in PURPOSE_ROWS}
    group_specs = [
        ("All included studies", [doc for doc in INCLUDED], "Descriptive implementation; feature applicability depends on the intended estimand"),
        ("Health-focused", [doc for doc in INCLUDED if purpose_by_id[doc["study_id"]]["study_category"] == "HEALTH_ANALYSIS"], "Health-analysis purposes"),
        ("Method-focused", [doc for doc in INCLUDED if purpose_by_id[doc["study_id"]]["study_category"] == "METHOD_RESEARCH"], "Method development or comparison"),
        ("Population-association purpose", [BY_ID[sid] for sid in CLAIM["study_ids"]["population_association_purpose"]], "Survey-aware population association directly relevant"),
        ("Surveillance or policy use", [BY_ID[sid] for sid in CLAIM["study_ids"]["population_or_policy_claim"]], "Survey-design support directly relevant"),
    ]
    survey_rows = []
    for label, docs, applicability in group_specs:
        used = lambda key: sum(item_value(doc, key) == "USED" for doc in docs)
        survey_rows.append([label, len(docs), applicability, used("SUR11"), used("SUR06"), used("SUR07"), used("SUR10")])
    emit_table(7, "Survey_features_by_purpose", "Applicability and implementation of complex-survey features by analytic purpose",
               ["Population or purpose", "N", "Applicability interpretation", "Combined-cycle weights", "Weights in fitting", "Weights in evaluation", "Strata/PSUs in uncertainty"], survey_rows,
               "Survey-sampling weights are distinct from class weights. Counts are descriptive unless the purpose-specific row states direct relevance.")

    def appraisal_summary(unit_key, id_key, domain_keys, states, group_label):
        groups = [("All units", prediction_docs),
                  ("Health-focused", [doc for doc in prediction_docs if purpose_by_id[doc["study_id"]]["study_category"] == "HEALTH_ANALYSIS"]),
                  ("Method-focused", [doc for doc in prediction_docs if purpose_by_id[doc["study_id"]]["study_category"] == "METHOD_RESEARCH"]),
                  ("Sensitivity: excluding KHM068", [doc for doc in prediction_docs if doc["study_id"] != "KHM068"])]
        rows = []
        for population, docs in groups:
            for domain, key in domain_keys:
                values = []
                for doc in docs:
                    for unit in doc["units"].get(unit_key, []):
                        values.append(unit_value(doc, key, unit[id_key]))
                counts = Counter(values)
                rows.append([population, domain, len(values), counts[states[0]], counts[states[1]], counts[states[2]]])
        return rows

    domains_dev = [("Participants/data sources", "PD_D1"), ("Predictors", "PD_D2"), ("Outcome", "PD_D3"), ("Analysis", "PD_D4"), ("Overall", "PD_OVERALL")]
    dev_rows = appraisal_summary("developments", "development_id", domains_dev, ("HIGH", "UNC", "LOW"), "development")
    emit_table(8, "PROBAST_development_summary", "PROBAST+AI model-development domain and overall judgements",
               ["Population", "Domain", "Units N", "High quality", "Unclear", "Low quality"], dev_rows,
               "Development judgements describe methodological quality. Unit-level records are in Supplementary Data S5.")

    domains_eval = [("Participants/data sources", "PE_D1"), ("Predictors", "PE_D2"), ("Outcome", "PE_D3"), ("Analysis", "PE_D4"), ("Overall", "PE_OVERALL")]
    eval_rows = appraisal_summary("evaluations", "evaluation_id", domains_eval, ("LOW", "UNC", "HIGH"), "evaluation")
    emit_table(9, "PROBAST_evaluation_summary", "PROBAST+AI performance-evaluation domain and overall judgements",
               ["Population", "Domain", "Units N", "Low risk", "Unclear", "High risk"], eval_rows,
               "Evaluation judgements describe risk of bias. Unit-level records are in Supplementary Data S5.")

    claim_rows = [
        ["Variable interpretation", "Explicit model-based importance", 129, "Importance stability assessed", 25, "19.4"],
        ["Population association", "Population-association purpose", 21, "Survey-aware association analysis", 4, "19.0"],
        ["Screening or personal use", "Screening/individual-use proposal", CLAIM["screening_or_individual_application_claim"]["denominator"], "Independent/later validation + calibration + threshold", CLAIM["screening_or_individual_application_claim"]["strict_all_three"], f'{100*CLAIM["screening_or_individual_application_claim"]["strict_all_three"]/CLAIM["screening_or_individual_application_claim"]["denominator"]:.1f}'],
        ["Surveillance or policy", "Surveillance/policy proposal", CLAIM["population_or_policy_claim"]["denominator"], "Relevant survey-design support", CLAIM["population_or_policy_claim"]["survey_weights_plus_strata_cluster_or_design_variance"], f'{100*CLAIM["population_or_policy_claim"]["survey_weights_plus_strata_cluster_or_design_variance"]/CLAIM["population_or_policy_claim"]["denominator"]:.1f}'],
    ]
    emit_table(10, "Claim_evidence_correspondence", "Correspondence between intended claims and supporting evidence",
               ["Claim/use", "Eligible studies", "N", "Required supporting evidence", "Matched n", "Matched %"], claim_rows,
               "These are same-study intersections using claim-matched review criteria, not universal standards.")

    screening = CLAIM["screening_or_individual_application_claim"]
    sensitivity_rows = [
        ["Strict", "Required", "Required", "Required", screening["strict_all_three"]],
        ["Relaxed", "Required", "At least one of calibration or threshold", "At least one of calibration or threshold", screening["relaxed_validation_plus_calibration_or_threshold"]],
        ["Validation component", "Required", "Any", "Any", screening["independent_or_later_period_validation"]],
        ["Calibration component", "Any", "Required", "Any", screening["calibration"]],
        ["Threshold component", "Any", "Any", "Required", screening["positive_decision_rule_reported"]],
    ]
    emit_table(11, "Screening_evidence_sensitivity", "Strict and relaxed screening-evidence sensitivity criteria",
               ["Criterion", "Independent/later validation", "Calibration", "Threshold", f'Studies meeting criterion (n/{screening["denominator"]})'],
               [row[:-1] + [f'{row[-1]}/{screening["denominator"]}'] for row in sensitivity_rows],
               "These are prespecified review-level evidence packages, not universal standards.")

    periods = TEMPORAL["periods"]
    health = TEMPORAL["health_focused_classification"]
    temporal_rows = []
    for group in ("interpretation_practices", "algorithm_families", "validation_evidence", "reproducibility_and_survey_reporting"):
        for indicator, values in health[group].items():
            temporal_rows.append([indicator] + [f"{values[p]['n']}/{values[p]['denominator']} ({values[p]['percent']:.1f}%)" for p in periods])
    emit_table(12, "Temporal_health_indicators", "Period-specific health-analysis indicators underlying Figure 12",
               ["Indicator"] + periods, temporal_rows, "The 2025--2026 period is incomplete through September 2026.")
    topics = health["health_topics"]
    topic_rows = []
    for j, topic in enumerate(topics["categories"]):
        topic_rows.append([topic] + [f"{topics['counts'][i][j]}/{topics['period_denominators'][i]}" for i in range(4)])
    emit_table(13, "Health_topics_by_period", "Health-topic composition by period underlying Supplementary Figure S1B",
               ["Health topic"] + periods, topic_rows,
               f"Monte Carlo chi-square p={topics['monte_carlo_chi_square_p']:.3f}; Cramer's V={topics['cramers_v']:.3f}.")

    method = TEMPORAL["method_focused"]
    method_rows = []
    for block in ("types", "targeted_stages"):
        for indicator, values in method[block].items():
            method_rows.append([block.replace("_", " ").title(), indicator] +
                               [f"{values[p]['n']}/{values[p]['denominator']} ({values[p]['percent']:.1f}%)" for p in periods])
    emit_table(14, "Temporal_method_indicators", "Period-specific method-focused indicators underlying Supplementary Figure S2",
               ["Block", "Indicator"] + periods, method_rows,
               "The 2025--2026 period is incomplete through September 2026; period denominators are small.")


def build_figures():
    health_ids = {row["study_id"] for row in PURPOSE_ROWS if row["study_category"] == "HEALTH_ANALYSIS"}
    topic_counts = Counter(
        row.get("health_topic", {}).get("primary_topic_18", "NOT_APPLICABLE")
        for row in V13["records"] if row["study_id"] in health_ids
    )
    topic_codes_18 = ["MENTAL_HEALTH", "CARDIOVASCULAR", "METABOLIC_ENDOCRINE", "MUSCULOSKELETAL",
                      "ORAL_HEALTH", "RESPIRATORY", "KIDNEY_UROLOGIC", "CANCER", "NUTRITION_DIET",
                      "HEALTH_BEHAVIOUR", "OPHTHALMOLOGIC", "OTORHINOLARYNGOLOGIC",
                      "DERMATOLOGIC_ALLERGIC", "INFECTIOUS_IMMUNE", "REPRODUCTIVE_WOMENS_HEALTH",
                      "AGING_GERIATRIC", "GENERAL_HEALTH_MULTIMORBIDITY", "OTHER_OR_CROSS_CUTTING"]
    for code in topic_codes_18:
        topic_counts.setdefault(code, 0)
    topic_labels = {
        "MENTAL_HEALTH": "Mental health", "DIABETES": "Diabetes",
        "CARDIOVASCULAR": "Cardiovascular disease", "CARDIOVASCULAR_DISEASE": "Cardiovascular disease",
        "BONE_MUSCLE": "Bone and muscle health", "MUSCULOSKELETAL": "Musculoskeletal health",
        "NUTRITION_DIET": "Nutrition and diet", "METABOLIC_SYNDROME": "Metabolic syndrome",
        "METABOLIC_ENDOCRINE": "Metabolic and endocrine health",
        "ORAL_HEALTH": "Oral health", "HYPERTENSION": "Hypertension",
        "RESPIRATORY": "Respiratory health", "KIDNEY_UROLOGIC": "Kidney and urologic health",
        "LIVER": "Liver health", "CANCER": "Cancer", "OBESITY": "Obesity",
        "SLEEP": "Sleep", "VISION_HEARING": "Vision and hearing", "OPHTHALMOLOGIC": "Eye health",
        "OTORHINOLARYNGOLOGIC": "Ear, nose, and throat health",
        "HEALTH_BEHAVIOUR": "Health behaviour", "GENERAL_HEALTH_MULTIMORBIDITY": "General health and multimorbidity",
        "DERMATOLOGIC_ALLERGIC": "Dermatologic and allergic health",
        "INFECTIOUS_IMMUNE": "Infectious and immune health",
        "REPRODUCTIVE_WOMENS_HEALTH": "Reproductive and women's health",
        "AGING_GERIATRIC": "Aging and geriatric health",
        "INFECTIOUS": "Infectious disease", "OTHER_HEALTH": "Other health topic",
        "OTHER_OR_CROSS_CUTTING": "Cross-cutting or otherwise unclassified health topic",
        "NOT_APPLICABLE": "Not classifiable",
    }
    ordered = topic_counts.most_common()
    labels = [topic_labels.get(code, code.replace("_", " ").title()) for code, _ in ordered][::-1]
    values = [count for _, count in ordered][::-1]
    fig, axes = plt.subplots(1, 2, figsize=(12.4, 6.6), gridspec_kw={"width_ratios": [1.15, 1.0]})
    ax = axes[0]
    bars = ax.barh(labels, values, color="#0B78B5")
    ax.set_xlabel("Health-focused studies (n)")
    ax.set_title("A. Full distribution of primary health topics (n=184)", loc="left", fontweight="bold")
    ax.grid(axis="x", color="#DDE3E8", linewidth=.8)
    ax.set_axisbelow(True)
    ax.spines[["top", "right"]].set_visible(False)
    for bar, value in zip(bars, values):
        ax.text(value + .35, bar.get_y() + bar.get_height()/2,
                f"{value} ({100*value/184:.1f}%)", va="center", fontsize=8.5)
    ax.set_xlim(0, max(values) * 1.27)
    fig.tight_layout()
    topic_figure = FIGURES / "Supplementary_Figure_S12_Full_health_topic_distribution.pdf"
    fig.savefig(topic_figure, bbox_inches="tight")
    plt.close(fig)

    sources = [
        (1, "Full_health_topic_distribution", "Full 18-category distribution of health topics", topic_figure),
        (2, "Method_research_over_time", "Temporal changes in method-focused research", ROOT / "figures/submission/figS13_method_temporal.pdf"),
    ]
    for number, slug, title, source in sources:
        target = FIGURES / f"Supplementary_Figure_S{number:02d}_{slug}.pdf"
        if source != target:
            shutil.copy2(source, target)
        stem = f"Supplementary_Figure_S{number:02d}_{slug}"
        tex = TEX / f"{stem}.tex"
        rel = target.relative_to(ROOT)
        tex.write_text(document_tex(f"Supplementary Figure S{number}. {title}",
            rf"\begin{{center}}\includegraphics[width=0.96\textwidth]{{{rel}}}\end{{center}}"), encoding="utf-8")
        # Add graphicx only to figure wrappers.
        tex.write_text(tex.read_text().replace(r"\usepackage{fontspec,booktabs,longtable,array,ragged2e,enumitem,hyperref}",
                                              r"\usepackage{fontspec,booktabs,longtable,array,ragged2e,enumitem,hyperref,graphicx}"))
        compile_tex(tex)
        MANIFEST.append([f"Supplementary Figure S{number}", title, "standalone TeX; PDF", "figure", str(target.relative_to(ROOT))])


def build_data():
    s1 = DATA / "Supplementary_Data_S01_Included_studies.xlsx"
    headers = ["study_id", "canonical_key", "title", "year", "authors", "journal", "doi", "task", "knhanes_role"]
    write_xlsx(s1, headers, [[row[h] for h in headers] for row in INTEGRATED], "Included studies")
    MANIFEST.append(["Supplementary Data S1", "Included-study catalogue", "XLSX", len(INTEGRATED), str(s1.relative_to(ROOT))])

    s2 = DATA / "Supplementary_Data_S02_Full_report_packet_coding.jsonl"
    source_jsonl = ROOT / "data/protocol_v1_2/KNHANES_studies_v1.2.jsonl"
    decisions = load_json("data/protocol_v1_2/ADJUDICATION_SUMMARY.json").get("decisions", {})
    packet_rows = []
    for line in source_jsonl.open(encoding="utf-8"):
        record = json.loads(line)
        sid = record["study_id"]
        decision = decisions.get(sid, {})
        if sid == "KHM065":
            status = "EXCLUDED_AFTER_FULL_REPORT_REVIEW"
        elif sid == "KHM076":
            status = "MERGED_COMPANION_PACKET_NOT_COUNTED_SEPARATELY"
        else:
            status = "INCLUDED_STUDY_REPRESENTATIVE"
        record["packet_inclusion_status"] = status
        record["study_family_id"] = decision.get("family_id", sid)
        packet_rows.append(record)
    assert len(packet_rows) == 255 and all(row.get("packet_inclusion_status") and row.get("study_family_id") for row in packet_rows)  # prompt 106: 222 + 32 criterion-A records + 1 exclusion recheck
    s2.write_text("".join(json.dumps(row, ensure_ascii=False, separators=(",", ":")) + "\n" for row in packet_rows), encoding="utf-8")
    MANIFEST.append(["Supplementary Data S2", "Full-report packet-level coding dataset", "JSONL", "222 packets", str(s2.relative_to(ROOT))])

    s3 = DATA / "Supplementary_Data_S03_Evidence_ledger.tsv"
    shutil.copy2(ROOT / "data/EVIDENCE_LEDGER.tsv", s3)
    evidence_n = sum(1 for _ in s3.open(encoding="utf-8-sig")) - 1
    MANIFEST.append(["Supplementary Data S3", "Evidence ledger", "TSV", evidence_n, str(s3.relative_to(ROOT))])

    dictionary_rows = []
    protocol_candidates = [ROOT / "KNHANES_ML_study_audit_protocol.md"]
    protocol_path = next((path for path in protocol_candidates if path.exists()), None)
    if protocol_path is None:
        raise FileNotFoundError("No current study-audit protocol Markdown was found")
    for line in protocol_path.read_text().splitlines():
        if not re.match(r"^\|\s*\d+\s*\|\s*`", line):
            continue
        cells = [cell.strip().strip("`") for cell in line.strip("|").split("|")]
        if len(cells) >= 13:
            dictionary_rows.append([cells[1], cells[5], cells[6], cells[7], cells[8], cells[9], cells[11], cells[12]])
    s4 = DATA / "Supplementary_Data_S04_Data_dictionary.xlsx"
    write_xlsx(s4, ["Variable", "Domain", "Applicability", "Question", "Type", "Allowed values", "JSON key", "Output mapping"], dictionary_rows, "Data dictionary")
    MANIFEST.append(["Supplementary Data S4", "Data dictionary", "XLSX", len(dictionary_rows), str(s4.relative_to(ROOT))])

    s5 = DATA / "Supplementary_Data_S05_Analysis_units_and_metrics.xlsx"
    wb = Workbook()
    wb.remove(wb.active)
    sheet_rows = {"Development units": [], "Evaluation units": [], "Performance metrics": [], "Best selections": []}
    sheet_headers = {
        "Development units": ["Study ID", "Development ID", "Model ID", "Outcome ID", "Dataset ID"],
        "Evaluation units": ["Study ID", "Evaluation ID", "Model ID", "Outcome ID", "Dataset ID", "Label"],
        "Performance metrics": ["Study ID", "Metric ID", "Evaluation ID", "Model ID", "Outcome ID", "Metric", "Estimate", "Lower CI", "Upper CI", "Threshold", "Reported text"],
        "Best selections": ["Study ID", "Selection ID", "Outcome ID", "Evaluation IDs", "Selected model IDs", "Selected metric IDs", "Criterion"],
    }
    for doc in INCLUDED:
        sid = doc["study_id"]
        for row in doc["units"].get("developments", []):
            sheet_rows["Development units"].append([sid, row.get("development_id"), row.get("model_id"), row.get("outcome_id"), row.get("dataset_id")])
        for row in doc["units"].get("evaluations", []):
            sheet_rows["Evaluation units"].append([sid, row.get("evaluation_id"), row.get("model_id"), row.get("outcome_id"), row.get("dataset_id"), row.get("label")])
        for row in doc.get("performance_metrics", []):
            sheet_rows["Performance metrics"].append([sid, row.get("metric_id"), row.get("evaluation_id"), row.get("model_id"), row.get("outcome_id"), row.get("metric"), row.get("estimate"), row.get("lower_ci"), row.get("upper_ci"), row.get("threshold"), row.get("reported_text")])
        for row in doc.get("best_model_selections", []):
            sheet_rows["Best selections"].append([sid, row.get("selection_id"), row.get("outcome_id"), clean(row.get("evaluation_ids")), clean(row.get("selected_model_ids")), clean(row.get("selected_metric_ids")), row.get("criterion")])
    for name, rows in sheet_rows.items():
        ws = wb.create_sheet(name)
        ws.append(sheet_headers[name])
        for row in rows:
            ws.append([clean(value) for value in row])
        ws.freeze_panes = "A2"
        for cell in ws[1]:
            cell.font = Font(bold=True); cell.fill = PatternFill("solid", fgColor="D9EAF7")
        for col in range(1, ws.max_column + 1):
            ws.column_dimensions[get_column_letter(col)].width = 22
    wb.save(s5)
    MANIFEST.append(["Supplementary Data S5", "Analysis-unit and performance records", "XLSX", sum(map(len, sheet_rows.values())), str(s5.relative_to(ROOT))])


def append_to_document(tex_path, addition):
    source = tex_path.read_text(encoding="utf-8")
    if r"\end{document}" not in source:
        raise ValueError(f"Missing document terminator: {tex_path}")
    tex_path.write_text(source.replace(r"\end{document}", addition + "\n" + r"\end{document}"), encoding="utf-8")
    compile_tex(tex_path)


def protocol_dictionary_rows():
    rows = []
    protocol = (ROOT / "KNHANES_ML_study_audit_protocol.md").read_text(encoding="utf-8")
    for line in protocol.splitlines():
        if not re.match(r"^\|\s*\d+\s*\|\s*`", line):
            continue
        cells = [cell.strip().strip("`") for cell in line.strip("|").split("|")]
        if len(cells) >= 13:
            rows.append([cells[1], cells[2], cells[6], cells[7], cells[8], cells[9], cells[11]])
    return rows


def protocol_items():
    """Parse the locked 17-column protocol table into named records."""
    items = []
    protocol = (ROOT / "KNHANES_ML_study_audit_protocol.md").read_text(encoding="utf-8")
    names = ["number", "item_id", "subsection", "item_role", "primary_unit",
             "required_related_ids", "construct", "applicability", "question",
             "response_type", "allowed_values", "evidence_required", "decision_rule",
             "json_key", "output_mapping", "official_item_id", "required_components"]
    for line in protocol.splitlines():
        if not re.match(r"^\|\s*\d+\s*\|\s*`", line):
            continue
        cells = [cell.strip().strip("`") for cell in line.strip("|").split("|")]
        if len(cells) >= len(names):
            items.append(dict(zip(names, cells[:len(names)])))
    return items


def public_classification_spec():
    rows, units = [], {}
    text = (ROOT / "KNHANES_ML_study_audit_protocol.md").read_text(encoding="utf-8")
    for line in text.splitlines():
        if not re.match(r"^\| (?:ORI|PUR|AOUT|USE|MTH|ASSOC)\d+ \|", line):
            continue
        cells = [cell.strip() for cell in line.strip("|").split("|")]
        if len(cells) != 9:
            raise ValueError(f"Malformed public protocol row: {line}")
        cells[3] = cells[3].replace("; ", " | ")
        rows.append(cells[:7])
        units[cells[0]] = tuple(cells[7:])
    if len(rows) != 12 or len(units) != 12:
        raise ValueError("Expected 12 unique canonical public classification items")
    return rows, units


PUBLIC_CLASSIFICATION_ROWS, PUBLIC_CLASSIFICATION_UNITS = public_classification_spec()


def human_protocol_rows(readable_choices=True):
    """Project the technical schema into a complete, human-facing review instrument."""
    # Publication S2 contains what a person must judge, not the project's AI or
    # file-handling workflow. These addendum items formally expose the central
    # classifications used by Figures 2, 3, 5, and 11C.
    rows = []
    for row in PUBLIC_CLASSIFICATION_ROWS:
        unit, linkage = PUBLIC_CLASSIFICATION_UNITS[row[0]]
        rows.append([row[0], row[1], f"{unit}; required: {linkage}", row[2], row[3],
                     f"{row[4]} Exception/example: {row[5]}", row[6]])
    domain_seen = set()
    judgement_examples = {
        "TSK06": "Include EXTERNAL/TRANSPORT only when KNHANES evaluates transport beyond the development data; a generic secondary analysis remains PRIMARY.",
        "VI01": "Include explicit model-based importance or contribution output; exclude a conventional regression coefficient reported without an ML interpretation step.",
        "VI16": "Include resampling, repeated splits, sensitivity analysis, or another explicit stability check of importance; exclude a single importance ranking.",
        "VI14": "Include only when the exact ML-selected variables can be matched to the downstream analysis; exclude a thematically similar but unrecoverable set.",
        "REP17": "A model is fully specified only when inputs/order, preprocessing, final parameters or saved object, threshold where applicable, and application instructions are recoverable.",
        "SUR06": "Survey sampling weights are distinct from class weights or loss weights; code only the former here.",
    }
    for item in protocol_items():
        if item["item_role"] not in {"reviewer_entered", "appraisal_judgement"}:
            continue
        item = english_item(item)
        domain = re.match(r"[A-Z]+", item["item_id"])[0]
        if domain not in domain_seen:
            domain_seen.add(domain)
            rows.append([f"{domain}. {DOMAIN_LABELS[domain]}", "", "", "", "", "", ""])
        response = item["allowed_values"] or item["response_type"]
        numeric_or_text = any(token in item["response_type"].lower()
                              for token in ("integer", "numeric", "decimal", "text", "date", "identifier"))
        if numeric_or_text:
            response = f"Value ({response or item['response_type']}); Status: REPORTED | NR | NA | UNCLEAR"
        # UNC is retained only in historical machine files. Public material uses
        # the full token, without altering UNCERTAIN or PROBAST+AI NI.
        # Keep exact source choice codes for the workbook lookup; display labels expand them.
        question = item["question"] or f"Record or judge {item['construct']}."
        decision = item["decision_rule"] or "Apply the canonical item definition to explicit source evidence; do not infer an unreported value."
        if item["item_id"] == "TSK04":
            decision = "Assign one of 18 major categories by the primary fitted outcome. Generic multidimensional quality of life belongs to general health and multimorbidity unless the fitted outcome specifically measures mental health; environmental wording alone does not identify a disease topic."
        elif item["item_id"] == "TSK05":
            decision = "Preserve the actual measured outcome(s), including multiple outcomes, in detailed wording."
        if item["required_components"]:
            decision += f" Required components: {item['required_components']}."
        if numeric_or_text:
            decision += " Status is mandatory when applicable; enter Value only when Status=REPORTED."
        examples = judgement_examples.get(item["item_id"])
        if examples:
            decision += f" Exception/example: {examples}"
        evidence = item["evidence_required"]
        if evidence in {"필수", "required", "Required"}:
            evidence = "Required: evidence_id plus source, page/object, and start/end anchor"
        elif evidence in {"자동", "automatic", "Automatic"}:
            evidence = "System-derived; retain source item IDs and derivation log"
        else:
            evidence = "Required for positive/judgement values; otherwise record status and rationale"
        link_ids = item["required_related_ids"] or "study_id"
        rows.append([item["item_id"], question,
                     f"{item['primary_unit']}; required: {link_ids}", item["applicability"], response,
                     decision, evidence])
    if readable_choices:
        for row in rows:
            row[4] = response_choices(row[4],row[0])
    return rows


S2_REP_COMMON = ("R=all required_components reported; P=some reported; NR=none reported; UNC (current UNCLEAR)="
                 "conflicting or unreadable evidence; NA=not applicable. Enter UNC in the historical §15 response set; "
                 "enter UNCLEAR in the current layer. Preserve raw UNC and official NI.")
S2_PROBAST_COMMON_1 = ("Y/PY support a favourable domain judgement; N/PN flag a concern, not automatic domain failure. "
                       "Weigh its material effect and record the source-linked rationale; NI means insufficient "
                       "information, not confirmed failure.")
S2_PROBAST_COMMON_2 = ("UNCLEAR=insufficient basis for a domain judgement; NA=outside the relevant development/evaluation "
                       "scope. No numeric score or additional critical-failure algorithm is used.")


def human_protocol_note():
    from protocol_reader_keys import S2_NOTE
    return (S2_NOTE + " Common decision rule: Apply the canonical item definition to explicit source evidence; do not infer an unreported value. Health-topic common note (TSK04/TSK05): the primary fitted outcome takes precedence over predictors, exposures and disease-restricted samples. The 18-category mapping and declared amendments are in S7 STUDIES/B_health_topic and TOPIC_CROSSWALK; link measured outcome definitions to RECORD_DETAILS and RECORD_EVIDENCE."
            + " Common REP rule (REP01–REP19): " + S2_REP_COMMON
            + " Common PROBAST+AI domain rule (PD_D1–D4, PE_D1–D4): " + S2_PROBAST_COMMON_1 + " " + S2_PROBAST_COMMON_2
            + " Each PD/PE row gives its official Table S3/S4 location and rating direction.")



def enhance_compact_documents():
    """Absorb boundary decisions/data dictionary into S2 and search yields into S3."""
    adj = load_json("data/protocol_v1_2/ADJUDICATION_SUMMARY.json")
    boundary_rows = []
    for sid, row in sorted(adj.get("decisions", {}).items()):
        boundary_rows.append([sid, row.get("decision", "NR"), row.get("family_id", "NA"),
                              row.get("rationale", "NR"), row.get("evidence", "See evidence ledger")])
    boundary_lines = "\n".join(" & ".join(tex_escape(v) for v in row) + r" \\" for row in boundary_rows)
    dictionary = protocol_dictionary_rows()
    dictionary_lines = "\n".join(" & ".join(tex_escape(v) for v in row) + r" \\" for row in dictionary)
    s2_addition = rf"""
\clearpage
\begin{{landscape}}
\section*{{Representative eligibility and study-family decisions}}
The 222 full-report packets resolved to 220 included study representatives. The two packets not
counted as separate included studies are retained here to keep the report-to-study transition auditable.
\fontsize{{7.5}}{{9}}\selectfont
\begin{{longtable}}{{>{{\RaggedRight\arraybackslash}}p{{1.5cm}} >{{\RaggedRight\arraybackslash}}p{{3.4cm}} >{{\RaggedRight\arraybackslash}}p{{2.0cm}} >{{\RaggedRight\arraybackslash}}p{{6.4cm}} >{{\RaggedRight\arraybackslash}}p{{3.2cm}}}}
\toprule
\textbf{{Packet ID}} & \textbf{{Decision}} & \textbf{{Family ID}} & \textbf{{Rationale}} & \textbf{{Evidence}} \\ \midrule
\endfirsthead
\toprule
\textbf{{Packet ID}} & \textbf{{Decision}} & \textbf{{Family ID}} & \textbf{{Rationale}} & \textbf{{Evidence}} \\ \midrule
\endhead
{boundary_lines}
\bottomrule
\end{{longtable}}
\clearpage
\section*{{Variable dictionary}}
The following dictionary defines the complete extraction and appraisal schema. NR denotes an
applicable item not reported, NA denotes structural non-applicability, and UNC or UNCLEAR denotes
evidence that was conflicting or insufficient for a defensible judgement.
\fontsize{{6.8}}{{8.2}}\selectfont
\begin{{longtable}}{{>{{\RaggedRight\arraybackslash}}p{{1.8cm}} >{{\RaggedRight\arraybackslash}}p{{1.8cm}} >{{\RaggedRight\arraybackslash}}p{{2.3cm}} >{{\RaggedRight\arraybackslash}}p{{7.6cm}} >{{\RaggedRight\arraybackslash}}p{{1.8cm}} >{{\RaggedRight\arraybackslash}}p{{2.3cm}} >{{\RaggedRight\arraybackslash}}p{{1.8cm}}}}
\toprule
\textbf{{ID}} & \textbf{{Domain}} & \textbf{{Applicability}} & \textbf{{Question/definition}} & \textbf{{Type}} & \textbf{{Allowed values}} & \textbf{{JSON key}} \\ \midrule
\endfirsthead
\toprule
\textbf{{ID}} & \textbf{{Domain}} & \textbf{{Applicability}} & \textbf{{Question/definition}} & \textbf{{Type}} & \textbf{{Allowed values}} & \textbf{{JSON key}} \\ \midrule
\endhead
{dictionary_lines}
\bottomrule
\end{{longtable}}
\end{{landscape}}
"""
    append_to_document(TEX / "Supplementary_Document_S2_Review_protocol.tex", s2_addition)

    oa = load_json("results/raw/openalex_20260905.json")
    yields = [
        ["Europe PMC", "2026-09-03", "6,046 unique", "6,046", "See final selection-flow ledger"],
        ["OpenAlex", "2026-09-05", f"{oa['queries'][0]['hits']:,}; {oa['queries'][1]['hits']:,}", f"{oa['n_unique']:,} unique", "Cursor-complete union; not capped"],
        ["PubMed", "2026-09-03", "5,128", "5,128", "52 beyond Europe PMC"],
        ["Korean Citation Index", "2026-09-05", "339", "339", "339 before cross-source deduplication"],
        ["KDCA publication list", "2026-09-03", "2,079", "2,079", "Retrieved in full"],
    ]
    yield_lines = "\n".join(" & ".join(tex_escape(v) for v in row) + r" \\" for row in yields)
    s3_addition = rf"""
\begin{{landscape}}
\section*{{Source-specific retrieval counts and unique contributions}}
\fontsize{{8}}{{9.5}}\selectfont
\begin{{longtable}}{{>{{\RaggedRight\arraybackslash}}p{{3.0cm}} >{{\RaggedRight\arraybackslash}}p{{2.4cm}} >{{\RaggedRight\arraybackslash}}p{{2.5cm}} >{{\RaggedRight\arraybackslash}}p{{2.5cm}} >{{\RaggedRight\arraybackslash}}p{{6.2cm}}}}
\toprule
\textbf{{Source}} & \textbf{{Search date}} & \textbf{{Total hits}} & \textbf{{Retrieved}} & \textbf{{Unique contribution or note}} \\ \midrule
\endfirsthead
\toprule
\textbf{{Source}} & \textbf{{Search date}} & \textbf{{Total hits}} & \textbf{{Retrieved}} & \textbf{{Unique contribution or note}} \\ \midrule
\endhead
{yield_lines}
\bottomrule
\end{{longtable}}
\end{{landscape}}
"""
    append_to_document(TEX / "Supplementary_Document_S3_Search_strategies.tex", s3_addition)


def master_cell(value):
    if value is None or value == "":
        return "NR"
    if isinstance(value, bool):
        return "Y" if value else "N"
    if isinstance(value, dict):
        return " | ".join(f"{k}: {master_cell(v)}" for k, v in value.items()) or "NR"
    if isinstance(value, (list, tuple, set)):
        flattened = []
        for item in value:
            text = master_cell(item)
            if text not in flattened:
                flattened.append(text)
        return " | ".join(flattened) if flattened else "NR"
    text = str(value).strip()
    # JSON is already structured: replacing semicolons here changes source text
    # inside records (for example comparator descriptions).
    if text.startswith(("[", "{")):
        try:
            json.loads(text)
        except json.JSONDecodeError:
            pass
        else:
            return text
    exact = {"UNC": "UNCLEAR", "NOT_REPORTED": "NR", "NOT_APPLICABLE": "NA",
             "NOT_APPLICABLE_OR_NOT_REPORTED": "NA", "None": "NR"}
    return exact.get(text, text.replace("; ", " | "))


def protocol_atoms(value):
    """Normalise one or more protocol responses without conflating delimiters."""
    if isinstance(value, (list, tuple, set)):
        raw = [part for item in value for part in protocol_atoms(item)]
    else:
        raw = str(value if value not in (None, "") else "NR").split("; ")
    exact = {"UNC": "UNCLEAR", "NOT_REPORTED": "NR", "NOT_APPLICABLE": "NA",
             "NOT_APPLICABLE_OR_NOT_REPORTED": "NA", "None": "NR"}
    out = []
    for part in raw:
        atom = exact.get(str(part).strip(), str(part).strip())
        if atom and atom not in out:
            out.append(atom)
    return out or ["NR"]


def json_cell(value):
    """Serialize a structured S7 cell with unambiguous keys and arrays."""
    return json.dumps(value, ensure_ascii=False, separators=(",", ":"))


def canonical_method_stages(value):
    """Map legacy method-stage labels onto the seven figure-aligned v1.4 stages."""
    mapping = {
        "DATA_INTEGRATION": "DATA_INTEGRATION_OR_HARMONISATION",
        "DATA_INTEGRATION_OR_HARMONISATION": "DATA_INTEGRATION_OR_HARMONISATION",
        "MISSING_DATA": "MISSING_DATA",
        "FEATURE_CONSTRUCTION_OR_SELECTION": "VARIABLE_CONSTRUCTION_OR_SELECTION",
        "FEATURE_ENGINEERING_OR_SELECTION": "VARIABLE_CONSTRUCTION_OR_SELECTION",
        "VARIABLE_CONSTRUCTION_OR_SELECTION": "VARIABLE_CONSTRUCTION_OR_SELECTION",
        "MODEL_DEVELOPMENT": "MODEL_DEVELOPMENT",
        "PREDICTION_OR_CLASSIFICATION": "MODEL_DEVELOPMENT",
        "REPRESENTATION_OR_CLUSTERING": "MODEL_DEVELOPMENT",
        "CLUSTERING_OR_REPRESENTATION": "MODEL_DEVELOPMENT",
        "CAUSAL_OR_STRUCTURE": "MODEL_DEVELOPMENT",
        "CAUSAL_OR_STRUCTURE_LEARNING": "MODEL_DEVELOPMENT",
        "EXPLANATION_OR_INTERPRETATION": "EXPLANATION_OR_INTERPRETATION",
        "EXPLAINABLE_AI": "EXPLANATION_OR_INTERPRETATION",
        "VALIDATION_OR_PERFORMANCE": "VALIDATION_OR_PERFORMANCE",
        "VALIDATION_OR_PERFORMANCE_EVALUATION": "VALIDATION_OR_PERFORMANCE",
        "USER_TOOL_OR_WORKFLOW": "USER_TOOL_OR_WORKFLOW",
    }
    ordered = ["DATA_INTEGRATION_OR_HARMONISATION", "MISSING_DATA",
               "VARIABLE_CONSTRUCTION_OR_SELECTION", "MODEL_DEVELOPMENT",
               "EXPLANATION_OR_INTERPRETATION", "VALIDATION_OR_PERFORMANCE",
               "USER_TOOL_OR_WORKFLOW"]
    values = value if isinstance(value, list) else ([] if value in (None, "", "NA") else [value])
    result = {mapping[x] for x in values if x in mapping}
    return [x for x in ordered if x in result] or "NA"


def method_stage_source(method):
    """Select the actual current/legacy path without collapsing detailed stages."""
    aliases = {"FEATURE_ENGINEERING_OR_SELECTION":"FEATURE_CONSTRUCTION_OR_SELECTION",
               "PREDICTION_OR_CLASSIFICATION":"MODEL_DEVELOPMENT",
               "CLUSTERING_OR_REPRESENTATION":"REPRESENTATION_OR_CLUSTERING",
               "CAUSAL_OR_STRUCTURE_LEARNING":"CAUSAL_OR_STRUCTURE",
               "EXPLAINABLE_AI":"EXPLANATION_OR_INTERPRETATION",
               "VALIDATION_OR_PERFORMANCE_EVALUATION":"VALIDATION_OR_PERFORMANCE",
               "DATA_INTEGRATION_OR_HARMONISATION":"DATA_INTEGRATION"}
    normalise = lambda values: [aliases.get(v, v) for v in values]
    current, legacy = "method_target_stages_detailed", "target_analysis_stages"
    if current in method and legacy in method and normalise(method[current]) != normalise(method[legacy]):
        raise ValueError("Conflicting current and legacy detailed method stages")
    field = current if current in method else legacy
    return field, normalise(method.get(field, []))


def publication_output_codes(value):
    """Crosswalk frozen post-hoc output labels to the v1.4 publication vocabulary."""
    mapping = {
        "POPULATION_ASSOCIATION_ESTIMATE": "ASSOCIATION_ESTIMATE",
        "CAUSAL_EFFECT": "CAUSAL_EFFECT_ESTIMATE",
        "CLUSTER_OR_PATTERN": "CLUSTER_OR_PATTERN_RESULT",
        "REDUCED_VARIABLE_SET": "REDUCED_PREDICTOR_SET",
        "INTERFACE_OR_TOOL": "IMPLEMENTED_TOOL",
    }
    values = value if isinstance(value, list) else ([] if value in (None, "", "NA") else [value])
    out = []
    for item in values:
        item = mapping.get(item, item)
        if item not in out:
            out.append(item)
    return out or "NA"


def publication_detailed_records(records, kind, study_id):
    """Copy legacy v1.3 records into the active publication vocabulary losslessly."""
    if records in (None, "", "NA"):
        return "NA"
    maps = {
        "purpose": {
            "HEALTH_STATE_OR_VALUE_ESTIMATION": "HEALTH_STATE_OR_HEALTH_VALUE_ESTIMATION",
            "POPULATION_ASSOCIATION": "POPULATION_ASSOCIATION_ANALYSIS",
            "PATTERN_OR_SUBGROUP_DISCOVERY": "HEALTH_PATTERN_OR_SUBGROUP_DISCOVERY",
            "CAUSAL_EFFECT_OR_STRUCTURE": "CAUSAL_EFFECT_OR_STRUCTURE_ESTIMATION",
        },
        "output": {
            "REDUCED_VARIABLE_SET": "REDUCED_PREDICTOR_SET",
            "CAUSAL_EFFECT": "CAUSAL_EFFECT_ESTIMATE",
            "CLUSTER_OR_PATTERN": "CLUSTER_OR_PATTERN_RESULT",
            "INTERFACE_OR_TOOL": "IMPLEMENTED_TOOL",
            "POPULATION_ASSOCIATION_ESTIMATE": "ASSOCIATION_ESTIMATE",
        },
        "use": {"EMPIRICALLY_TESTED_USE": "TESTED_USE"},
    }
    key = {"purpose": "purpose_code", "output": "output_code", "use": "claim_strength"}[kind]
    result = []
    for index, source in enumerate(records, 1):
        record = json.loads(json.dumps(source, ensure_ascii=False))
        record[{"purpose": "purpose_record_id", "output": "output_record_id", "use": "use_record_id"}[kind]] = f"{study_id}-{kind.upper()}-{index:03d}"
        record[key] = maps[kind].get(record.get(key), record.get(key))
        if kind == "use":
            complete = record.pop("review_complete", None)
            record["review_status"] = "COMPLETE" if complete is True else "INCOMPLETE" if complete is False else "UNCLEAR"
        result.append(record)
    return result


def publication_code_availability(value):
    """Convert legacy code-availability labels without overstating access checks."""
    if value == "PUBLIC_CODE_AVAILABLE":
        return "PUBLIC_LINK_REPORTED_ACCESS_NOT_REVERIFIED"
    return master_cell(value)


def association_linkage_components(doc, association, eligible):
    """Return conservative historical linkage components pending dual-AI verification."""
    if not eligible:
        return ("NA", "NA", "NA")
    estimate = association.get("association_was_substantive_output", "NR")
    combined = association.get("population_association_was_survey_aware", "N")
    if combined == "Y":
        return (estimate, "Y", "Y")

    def locked_component(item_id):
        values = protocol_atoms(item_value(doc, item_id))
        if "NOT_USED" in values:
            return "N"
        if "NR" in values:
            return "NR"
        if "UNCLEAR" in values or "UNC" in values:
            return "UNCLEAR"
        # A generic study-level USED value does not establish linkage to the
        # eligible association analysis; dual-AI extraction and human adjudication resolve this directly.
        if "USED" in values:
            return "UNCLEAR"
        return "NR"

    return (estimate, locked_component("SUR04"), locked_component("SUR10"))


def analytic_value(doc, field):
    return doc.get("adjudication", {}).get("analytic_flow", {}).get("fields", {}).get(field, {}).get("value", "NR")


def item_used(doc, key, wanted):
    return any(row.get("value") == wanted or (isinstance(row.get("value"), list) and wanted in row["value"])
               for row in value_rows(doc, key))


def best_metric(doc, patterns):
    selected = {mid for row in doc.get("best_model_selections", []) for mid in row.get("selected_metric_ids", [])}
    metrics = [row for row in doc.get("performance_metrics", []) if not selected or row.get("metric_id") in selected]
    values = []
    for row in metrics:
        name = str(row.get("metric", "")).lower().replace("-", "").replace("_", "")
        if not any(re.search(pattern, name) for pattern in patterns):
            continue
        try:
            values.append(float(row.get("estimate")))
        except (TypeError, ValueError):
            pass
    if not values:
        return "NR"
    return f"{max(values):.6g}"


def best_metric_record(doc, patterns):
    """Return the highest selected/reported metric with its model and evaluation IDs."""
    selected = {mid for row in doc.get("best_model_selections", []) for mid in row.get("selected_metric_ids", [])}
    candidates = []
    for row in doc.get("performance_metrics", []):
        name = str(row.get("metric", "")).lower().replace("-", "").replace("_", "")
        if not any(re.search(pattern, name) for pattern in patterns):
            continue
        try:
            estimate = float(row.get("estimate"))
        except (TypeError, ValueError):
            continue
        priority = 1 if row.get("metric_id") in selected or row.get("author_designated_best") else 0
        candidates.append((priority, estimate, row))
    if not candidates:
        return ("NR", "NR", "NR")
    _, estimate, row = max(candidates, key=lambda x: (x[0], x[1]))
    models = {x.get("model_id"): x.get("label", x.get("model_id")) for x in doc.get("units", {}).get("models", [])}
    # Deliver bounded classification metrics on one scale. Some source reports
    # print percentages whereas others print proportions.
    if 1 < estimate <= 100:
        estimate /= 100
    return (f"{estimate:.6g}", models.get(row.get("model_id"), row.get("model_id", "NR")), row.get("evaluation_id", "NR"))


def make_master_backdata():
    metric_report_items = ["MET_ACC_R", "MET_BACC_R", "MET_AUROC_R", "MET_AUPRC_R", "MET_SENS_R",
                           "MET_SPEC_R", "MET_PPV_R", "MET_NPV_R", "MET_F1_R", "MET_MCC_R", "MET_KAPPA_R",
                           "MET_BRIER_R", "MET_LOGLOSS_R", "MET_CALSLOPE_R", "MET_CALINT_R", "MET_CALPLOT_R",
                           "MET_DCA_R", "MET_RMSE_R", "MET_MSE_R", "MET_MAE_R", "MET_R2_R"]
    headers = [
        "A_study_id", "A_representative_report_id", "A_citation", "A_title", "A_original_title",
        "A_authors", "A_journal", "A_publication_year", "A_DOI", "A_PMID", "A_report_type",
        "A_retraction_status", "A_representative_study_family_id",
        "B_primary_orientation", "B_display_orientation_group", "B_classification_confidence", "B_analytic_task",
        "B_included_all", "B_health_focused", "B_method_focused",
        "B_core_health_classification", "B_other_health_analysis", "B_scientific_purposes",
        "B_scientific_purpose_records", "B_health_topic", "B_analytic_outputs", "B_analytic_output_records",
        "B_proposed_uses", "B_proposed_use_records", "B_KNHANES_role", "B_method_contribution",
        "B_method_contribution_detailed", "B_method_target_stages_display", "B_method_target_stages_detailed",
        "B_method_evaluation_design", "B_method_comparators", "B_method_evaluation_datasets",
        "B_method_primary_evaluation_criteria",
        "C_survey_years", "C_cycles", "C_number_of_years", "C_pooling_structure", "C_components_used", "C_linked_data",
        "C_role_relative_to_other_datasets", "C_combined_cycle_weighting",
        "D_target_population", "D_age_restriction", "D_sex_restriction", "D_disease_risk_restriction",
        "D_measurement_restriction", "D_source_sample", "D_final_sample", "D_event_count", "D_prevalence",
        "D_complete_participant_flow_reconstruction",
        "E_outcome_name", "E_timing", "E_scale", "E_ascertainment_source", "E_threshold_definition", "E_full_definition",
        "E_definition_reproducibility", "E_definition_completeness",
        "F_candidate_predictor_definition", "F_initial_predictor_count", "F_candidate_set_completeness",
        "F_feature_selection_method", "F_missing_data_method", "F_scaling_transformation", "F_class_rebalancing",
        "F_timing_relative_to_split_resampling", "F_leakage_concern",
        "G_algorithm_families", "G_hyperparameter_search", "G_tuning_method", "G_tuning_evaluation_separation",
        "G_author_selected_model", "G_selection_criterion",
        "H_internal_validation", "H_later_period_validation", "H_external_validation", "H_evaluation_sample_size",
        "H_evaluation_prevalence", "H_evaluation_prevalence_identifiable", "H_threshold_reported", "H_threshold_selection_method",
        "H_metrics_reported", "H_best_accuracy", "H_best_accuracy_model", "H_best_accuracy_evaluation",
        "H_best_AUROC", "H_best_AUROC_model", "H_best_AUROC_evaluation",
        "H_best_AUPRC", "H_best_AUPRC_model", "H_best_AUPRC_evaluation",
        "H_best_F1", "H_best_F1_model", "H_best_F1_evaluation", "H_calibration_reported", "H_Brier_score_reported",
        "H_decision_curve_reported", "H_confidence_interval_reported", "H_paired_comparison_reported",
        "I_importance_reported", "I_importance_methods", "I_importance_stability", "I_reduced_predictor_set",
        "I_downstream_statistical_analysis", "I_exact_variable_carryover",
        "J_weights_in_fitting", "J_weights_in_evaluation", "J_combined_cycle_weights", "J_strata_PSUs_in_uncertainty", "J_omission_justified",
    ] + [f"K_REP{i:02d}" for i in range(1, 20)] + [
        "K_code_available", "K_final_model_specification", "K_data_availability", "K_registration",
        "L_development_unit_count", "L_development_domain_summary", "L_development_overall_judgements",
        "L_evaluation_unit_count", "L_evaluation_domain_summary", "L_evaluation_overall_judgements",
        "L_study_level_PROBAST_summary",
        "M_association_estimate_linked", "M_survey_weights_linked_to_association",
        "M_design_uncertainty_linked_to_association",
        "M_importance_stability_support_criteria_met", "M_population_association_support_criteria_met",
        "M_individual_application_support_criteria_met", "M_surveillance_policy_support_criteria_met",
        "N_evidence_page_table_figure", "N_evidence_anchor_ID", "N_extraction_notes", "N_adjudication_notes",
        "N_protocol_exceptions",
    ]
    rows = []
    for doc in sorted(INCLUDED, key=lambda x: x["study_id"]):
        sid = doc["study_id"]
        meta = doc.get("metadata", {})
        adj = doc.get("adjudication", {})
        sc = adj.get("study_category_and_dataset_use", PURPOSE_BY_ID.get(sid, {}))
        v13 = adj.get("purpose_evidence_v1_3", V13_BY_ID.get(sid, {}))
        method_detail = v13.get("method_research") or {}
        expanded = adj.get("expanded_model_task_audit", EXPANDED_BY_ID.get(sid, {}))
        restriction = adj.get("selection_restriction_dimensions", {}).get("fields", {})
        algorithm = expanded.get("algorithm_development", {})
        proposed = sc.get("proposed_use", [])
        application_codes = {"SCREENING", "DIAGNOSTIC_SUPPORT", "PERSONALISED_MANAGEMENT", "RISK_GROUP_IDENTIFICATION"}
        is_application = (v13.get("primary_orientation") == "HEALTH_FOCUSED" and
                          bool(set(proposed) & application_codes))
        independent = any(v in {"EXTERNAL", "TEMPORAL"} for row in value_rows(doc, "VAL02") for v in (row.get("value") if isinstance(row.get("value"), list) else [row.get("value")]))
        calibrated = any(item_used(doc, key, "R") for key in ("MET_CALSLOPE_R", "MET_CALINT_R", "MET_CALPLOT_R"))
        threshold = threshold_reported(doc)
        survey_supported = item_used(doc, "SUR04", "USED") and any(item_used(doc, key, "USED") for key in ("SUR08", "SUR09", "SUR10"))
        association = v13.get("association_audit", {})
        association_eligible = (v13.get("primary_orientation") == "HEALTH_FOCUSED" and
                                "POPULATION_ASSOCIATION_ANALYSIS" in sc.get("health_analysis_purpose_components", []))
        association_links = association_linkage_components(doc, association, association_eligible)
        metrics_reported = [key.replace("MET_", "").replace("_R", "") for key in metric_report_items if item_used(doc, key, "R")]
        metric_names = sorted({str(row.get("metric")) for row in doc.get("performance_metrics", []) if row.get("metric")})
        if not metrics_reported:
            metrics_reported = metric_names
        models = {row.get("model_id"): row.get("label", row.get("model_id")) for row in doc.get("units", {}).get("models", [])}
        selected_models = [models.get(mid, mid) for selection in doc.get("best_model_selections", []) for mid in selection.get("selected_model_ids", [])]
        review_family = next((x["review_selected_family"] for x in doc.get("best_model_selections", []) if x.get("review_selected_family")), None)
        if review_family:  # review 20261023: family of the selected model corrected by the two-AI review
            selected_models = [review_family]
        selection_criteria = [selection.get("criterion", "NR") for selection in doc.get("best_model_selections", [])]
        evidence = doc.get("evidence_registry", [])
        evidence_locations = []
        for ev in evidence:
            loc = ev.get("object_label") or ev.get("section") or "source"
            page = ev.get("pdf_page") or ev.get("printed_page") or "NR"
            token = f"{ev.get('source_file', 'NR')}:p{page}:{loc}"
            if token not in evidence_locations:
                evidence_locations.append(token)
        dev_overall = item_value(doc, "PD_OVERALL")
        eval_overall = item_value(doc, "PE_OVERALL")
        reports = doc.get("units", {}).get("reports", [])
        representative_report_id = reports[0].get("report_id", "NR") if reports else "NR"
        accuracy = best_metric_record(doc, [r"^accuracy$", r"^acc$"])
        auroc = best_metric_record(doc, [r"auroc", r"rocauc", r"aucroc"])
        auprc = best_metric_record(doc, [r"auprc", r"prauc", r"averageprecision"])
        f1 = best_metric_record(doc, [r"^f1", r"f1score"])
        dev_domains = {key: protocol_atoms(item_value(doc, key)) for key in ("PD_D1", "PD_D2", "PD_D3", "PD_D4")}
        eval_domains = {key: protocol_atoms(item_value(doc, key)) for key in ("PE_D1", "PE_D2", "PE_D3", "PE_D4")}
        protocol_exceptions = [code for entry in adj.get("classification_reason_codes", [])
                               for code in entry.get("reason_codes", [])]
        row = [
            sid, representative_report_id,
            f"{master_cell(meta.get('authors'))} ({meta.get('publication_year','NR')}). {meta.get('title','NR')}",
            meta.get("title"), item_value(doc, "BIB01"), meta.get("authors"), meta.get("journal"),
            meta.get("publication_year"), meta.get("doi"), item_value(doc,"BIB10"), item_value(doc,"BIB07"),
            item_value(doc,"BIB16"), sc.get("family_id", sid),
            v13.get("primary_orientation", "UNCLEAR"), sc.get("study_category", "NR"),
            sc.get("purpose_judgement_confidence", v13.get("orientation_confidence", "NR")),
            sc.get("knhanes_actual_ml_task", item_value(doc,"TSK01")), "Y",
            "Y" if sc.get("study_category") == "HEALTH_ANALYSIS" else "N",
            "Y" if sc.get("study_category") == "METHOD_RESEARCH" else "N",
            "Y" if sc.get("study_category") == "HEALTH_ANALYSIS" and sc.get("knhanes_actual_ml_task", item_value(doc,"TSK01")) == "CLASSIFICATION" else "N",
            "Y" if sc.get("study_category") == "HEALTH_ANALYSIS" and sc.get("knhanes_actual_ml_task", item_value(doc,"TSK01")) != "CLASSIFICATION" else "N",
            [r["purpose_code"] for r in publication_detailed_records(v13.get("purpose_records", []), "purpose", sid)] if v13.get("primary_orientation") == "HEALTH_FOCUSED" else "NA",
            json_cell(publication_detailed_records(v13.get("purpose_records", "NA"), "purpose", sid)) if v13.get("primary_orientation") == "HEALTH_FOCUSED" else "NA",
            v13.get("health_topic", {}).get("primary_topic_18", "NA") if v13.get("primary_orientation") == "HEALTH_FOCUSED" else "NA",
            list(dict.fromkeys(r["output_code"] for r in publication_detailed_records(v13.get("analytic_output_records", []), "output", sid))) if v13.get("primary_orientation") == "HEALTH_FOCUSED" else "NA",
            json_cell(publication_detailed_records(v13.get("analytic_output_records", "NA"), "output", sid)) if v13.get("primary_orientation") == "HEALTH_FOCUSED" else "NA",
            ([r["use_code"] for r in v13.get("proposed_use_records", [])] or ("NO_SPECIFIC_USE" if v13.get("no_specific_use") is True else "UNCLEAR")) if v13.get("primary_orientation") == "HEALTH_FOCUSED" else "NA",
            json_cell(publication_detailed_records(v13.get("proposed_use_records", "NA"), "use", sid)) if v13.get("primary_orientation") == "HEALTH_FOCUSED" else "NA",
            {"EXTERNAL_OR_TRANSPORTABILITY_EVALUATION":"EXTERNAL_OR_TRANSPORT_EVALUATION_DATASET"}.get(sc.get("knhanes_position", item_value(doc,"TSK06")), sc.get("knhanes_position", item_value(doc,"TSK06"))),
            sc.get("method_research_category", "NA") if v13.get("primary_orientation") == "METHOD_FOCUSED" else "NA",
            method_detail.get("method_research_type_detailed", "NA") if v13.get("primary_orientation") == "METHOD_FOCUSED" else "NA",
            canonical_method_stages(method_stage_source(method_detail)[1]) if v13.get("primary_orientation") == "METHOD_FOCUSED" else "NA",
            method_stage_source(method_detail)[1] if v13.get("primary_orientation") == "METHOD_FOCUSED" else "NA",
            sc.get("method_evaluation_mode", "NA") if v13.get("primary_orientation") == "METHOD_FOCUSED" else "NA",
            json_cell(method_detail.get("comparators", [])) if v13.get("primary_orientation") == "METHOD_FOCUSED" else "NA",
            json_cell(method_detail.get("evaluation_datasets", [])) if v13.get("primary_orientation") == "METHOD_FOCUSED" else "NA",
            json_cell(method_detail.get("primary_evaluation_criteria", [])) if v13.get("primary_orientation") == "METHOD_FOCUSED" else "NA",
            item_value(doc,"DAT04"), item_value(doc,"DAT02"), item_value(doc,"DAT07"), item_value(doc,"DAT10"), item_value(doc,"DAT14"),
            item_value(doc,"DAT16"), json_cell({"mode": sc.get("multi_dataset_use_mode", "NA"), "datasets": sc.get("other_datasets", "NA")}), item_value(doc,"DAT11"),
            analytic_value(doc,"target_population_description"), restriction.get("age_restriction",{}).get("value","NR"),
            restriction.get("sex_restriction",{}).get("value","NR"), restriction.get("disease_or_risk_restriction",{}).get("value","NR"),
            restriction.get("measurement_or_data_availability_restriction",{}).get("value","NR"), analytic_value(doc,"initial_eligible_sample_n"),
            analytic_value(doc,"final_analytic_sample_n"), analytic_value(doc,"positive_event_n"), analytic_value(doc,"positive_prevalence"),
            analytic_value(doc,"complete_cohort_traceability"),
            item_value(doc,"OUT02"), item_value(doc,"OUT10"), item_value(doc,"OUT09"), item_value(doc,"OUT04"),
            item_value(doc,"OUT08"), json_cell({"name": item_value(doc,"OUT02"), "original_form": item_value(doc,"OUT03"), "cutoff": item_value(doc,"OUT08")}),
            item_value(doc,"OUT16"), item_value(doc,"OUT18"),
            item_value(doc,"PRD01"), analytic_value(doc,"initial_candidate_predictor_count"), item_value(doc,"PRD13"), analytic_value(doc,"feature_selection_approach"),
            item_value(doc,"PRE02"), item_value(doc,"PRE06"), item_value(doc,"IMB02") if sc.get("knhanes_actual_ml_task", item_value(doc,"TSK01")) == "CLASSIFICATION" else "NA",
            json_cell({"missing": protocol_atoms(item_value(doc,"PRE05")), "feature_selection": protocol_atoms(item_value(doc,"PRE13")), "imbalance": protocol_atoms(item_value(doc,"IMB03"))}),
            json_cell({"direct_target_component": protocol_atoms(item_value(doc,"PRD08")), "deterministic_proxy": protocol_atoms(item_value(doc,"PRD09")), "post_outcome_predictor": protocol_atoms(item_value(doc,"PRD10"))}),
            algorithm.get("algorithm_family", item_value(doc,"MOD02")), algorithm.get("tuning_selection_status", "NR"),
            algorithm.get("hyperparameter_tuning_method", item_value(doc,"MOD07")), algorithm.get("tuning_data_partition", "NR"),
            selected_models or item_value(doc,"MOD05"), selection_criteria or algorithm.get("final_model_selection_metric", "NR"),
            item_value(doc,"VAL02"), "Y" if item_used(doc,"VAL02","TEMPORAL") else "N", "Y" if item_used(doc,"VAL02","EXTERNAL") else "N",
            item_value(doc,"VAL10"), item_value(doc,"VAL12"), item_value(doc,"IMB05"), {"Y":"Y", "NR":"N", "UNCLEAR":"UNCLEAR", "NA":"NA"}[threshold_state(doc)], item_value(doc,"THR01"), metrics_reported,
            *accuracy, *auroc, *auprc, *f1,
            "Y" if calibrated else "N", item_value(doc,"MET_BRIER_R"), item_value(doc,"MET_DCA_R"), item_value(doc,"MET_CI"), item_value(doc,"MET_PAIR"),
            item_value(doc,"VI01"), item_value(doc,"VI02"), item_value(doc,"VI16"), item_value(doc,"VI10"), item_value(doc,"VI11"), item_value(doc,"VI14"),
            item_value(doc,"SUR06"), item_value(doc,"SUR07"), item_value(doc,"SUR11"), item_value(doc,"SUR10"), item_value(doc,"SUR13"),
        ] + [item_value(doc, f"REP{i:02d}") for i in range(1,20)] + [
            publication_code_availability(v13.get("final_model_specification",{}).get("code_availability_status", "NR")),
            v13.get("final_model_specification",{}).get("completeness", item_value(doc,"REP17")), item_value(doc,"REP19"), item_value(doc,"REP19"),
            len(doc.get("units",{}).get("developments",[])), json_cell(dev_domains), dev_overall,
            len(doc.get("units",{}).get("evaluations",[])), json_cell(eval_domains), eval_overall,
            json_cell({"development": protocol_atoms(dev_overall), "evaluation": protocol_atoms(eval_overall)}),
            *association_links,
            ("Y" if item_used(doc,"VI16","USED") else "N") if item_used(doc,"VI01","USED") else "NA",
            ("Y" if association_links == ("Y", "Y", "Y") else
             "UNCLEAR" if "UNCLEAR" in association_links and "N" not in association_links and "NR" not in association_links else "N") if association_eligible else "NA",
            ("Y" if independent and calibrated and threshold else "N") if is_application else "NA",
            ("Y" if survey_supported else "N") if "POPULATION_SURVEILLANCE_OR_POLICY" in proposed else "NA",
            evidence_locations, [ev.get("evidence_id") for ev in evidence],
            adj.get("analytic_flow",{}).get("non_inference_rule", "NR"),
            sc.get("rationale", adj.get("decision_rationale", doc.get("review_record",{}).get("status","NR"))), protocol_exceptions,
        ]
        rows.append([master_cell(v) for v in row])
    _pin(len(rows), 249, "build_standalone_supplements.py:1537")  # prompt 106 pin
    _pin(len({row[0] for row in rows}), 249, "build_standalone_supplements.py:1537")  # prompt 106 pin
    assert all(len(row) == len(headers) for row in rows)
    path = TABLES / "Supplementary_Data_1_Study_level_dataset.xlsx"  # prompt 097: outside the table numbering
    write_multisheet_s7(path, headers, rows)
    return path, headers, rows


def _flat_records(unit_name):
    records = []
    for doc in sorted(INCLUDED, key=lambda x: x["study_id"]):
        for entry in doc.get("units", {}).get(unit_name, []):
            records.append({"study_id": doc["study_id"], **entry})
    return records


def _long_records(key):
    records = []
    for doc in sorted(INCLUDED, key=lambda x: x["study_id"]):
        for entry in doc.get(key, []):
            records.append({"study_id": doc["study_id"], **entry})
    return records


def _records_table(records):
    if not records:
        return ["study_id"], []
    headers = []
    for record in records:
        for key in record:
            if key not in headers:
                headers.append(key)
    rows = []
    for record in records:
        row = []
        for key in headers:
            value = record.get(key, "NA")
            row.append(json.dumps(value, ensure_ascii=False, sort_keys=True) if isinstance(value, (list, dict)) else value)
        rows.append(row)
    return headers, rows


def _add_sheet(wb, title, headers, rows, freeze="A2", group_colours=False, section_rows=False):
    ws = wb.create_sheet(title)
    ws.append(headers)
    for row in rows:
        row = list(row)
        if section_rows and row and row[0] and all(value in (None, "") for value in row[1:]):
            # Prompt 093: a section heading (e.g. "ADM. Judgement certainty") keeps blank cells, not "NR".
            ws.append([row[0]] + [None] * (len(row) - 1))
            continue
        ws.append([clean(value) for value in row])
    palette = ["EAF2F8", "FEF5E7", "E8F8F5", "F4ECF7", "FDEDEC", "EBF5FB", "FCF3CF"]
    for index, cell in enumerate(ws[1], 1):
        cell.font = Font(bold=True)
        if group_colours and isinstance(cell.value, str) and re.match(r"^[A-N]_", cell.value):
            cell.fill = PatternFill("solid", fgColor=palette[(ord(cell.value[0]) - ord("A")) % len(palette)])
        else:
            cell.fill = PatternFill("solid", fgColor="D9EAF7")
        cell.alignment = Alignment(wrap_text=True, vertical="top")
    ws.freeze_panes = freeze
    ws.auto_filter.ref = ws.dimensions
    for column in range(1, len(headers) + 1):
        lengths = [len(str(ws.cell(row=i, column=column).value or "")) for i in range(1, min(ws.max_row, 100) + 1)]
        ws.column_dimensions[get_column_letter(column)].width = min(max(max(lengths, default=10) + 2, 12), 45)
    for row in ws.iter_rows(min_row=2):
        for cell in row:
            cell.alignment = Alignment(wrap_text=True, vertical="top")
            if cell.data_type == "f":
                cell.data_type = "s"  # Literal source excerpt, not a formula.
    return ws


def protocol_ids_for_public_field(header):
    """Return explicit source protocol IDs for every public STUDIES field."""
    metric_ids = "MET_ACC_R;MET_BACC_R;MET_AUROC_R;MET_AUPRC_R;MET_SENS_R;MET_SPEC_R;MET_PPV_R;MET_NPV_R;MET_F1_R;MET_MCC_R;MET_KAPPA_R;MET_BRIER_R;MET_LOGLOSS_R;MET_CALSLOPE_R;MET_CALINT_R;MET_CALPLOT_R;MET_DCA_R;MET_RMSE_R;MET_MSE_R;MET_MAE_R;MET_R2_R;MET_CI;MET_PAIR;MET_PAIR_M;MET_SD;MET_APPROPRIATE"
    exact = {
        "A_study_id":"ADM01", "A_representative_report_id":"ADM02", "A_title":"BIB01",
        "A_authors":"BIB03", "A_journal":"BIB04", "A_publication_year":"BIB05", "A_DOI":"BIB09",
        "A_PMID":"BIB10", "B_analytic_task":"TSK01", "B_KNHANES_role":"TSK06",
        "B_primary_orientation":"ORI01", "B_classification_confidence":"ORI02",
        "B_scientific_purposes":"PUR01", "B_scientific_purpose_records":"PUR01",
        "B_analytic_outputs":"AOUT01", "B_analytic_output_records":"AOUT01",
        "B_proposed_uses":"USE01;USE02", "B_proposed_use_records":"USE01;USE02",
        "B_method_contribution":"MTH01", "B_method_contribution_detailed":"MTH01",
        "B_method_target_stages_display":"MTH02", "B_method_target_stages_detailed":"MTH02",
        "B_method_evaluation_design":"MTH03", "B_method_comparators":"MTH03",
        "B_method_evaluation_datasets":"MTH03", "B_method_primary_evaluation_criteria":"MTH03",
        "M_association_estimate_linked":"ASSOC01", "M_survey_weights_linked_to_association":"ASSOC02",
        "M_design_uncertainty_linked_to_association":"ASSOC03",
        "C_survey_years":"DAT04", "C_cycles":"DAT02", "C_number_of_years":"DAT07",
        "D_target_population":"POP01", "E_outcome_name":"OUT02", "E_timing":"OUT10",
        "D_final_sample":"POP09", "D_event_count":"POP12", "D_prevalence":"POP14",
        "E_scale":"OUT09", "F_candidate_predictor_definition":"PRD01", "F_missing_data_method":"PRE02",
        "F_scaling_transformation":"PRE06", "F_class_rebalancing":"IMB02", "G_algorithm_families":"MOD02",
        "H_internal_validation":"VAL02", "H_evaluation_sample_size":"VAL10",
        "H_evaluation_prevalence":"VAL12", "H_threshold_reported":"THR01",
        "H_confidence_interval_reported":"MET_CI", "H_paired_comparison_reported":"MET_PAIR",
        "H_threshold_selection_method":"THR01", "I_importance_reported":"VI01",
        "I_importance_methods":"VI02", "I_importance_stability":"VI16", "I_exact_variable_carryover":"VI14",
        "J_weights_in_fitting":"SUR06", "J_weights_in_evaluation":"SUR07", "J_combined_cycle_weights":"SUR11",
        "J_strata_PSUs_in_uncertainty":"SUR10", "K_code_available":"MOD15;MOD16",
    }
    if header.startswith("K_REP"):
        return header.replace("K_", "")
    # No domain-wide fallback: each field must name its actual inputs.
    exact.update({
        "A_citation":"BIB01;BIB03;BIB05", "A_original_title":"BIB01",
        "A_report_type":"BIB07", "A_retraction_status":"BIB16",
        "A_representative_study_family_id":"FAM01",
        "B_display_orientation_group":"ORI01", "B_health_topic":"TSK04;TSK05",
        "B_included_all":"ELG04;FAM10", "B_health_focused":"ELG04;ORI01",
        "B_method_focused":"ELG04;ORI01", "B_core_health_classification":"ELG04;ORI01;TSK01",
        "B_other_health_analysis":"ELG04;ORI01;TSK01",
        "C_pooling_structure":"DAT10", "C_components_used":"DAT14",
        "C_linked_data":"DAT15;DAT16", "C_role_relative_to_other_datasets":"TSK06;DAT10;DAT15;DAT16",
        "C_combined_cycle_weighting":"DAT11",
        "D_age_restriction":"POP03;POP04;POP06;POP07", "D_sex_restriction":"POP05;POP06;POP07",
        "D_disease_risk_restriction":"POP06;POP07", "D_measurement_restriction":"POP06;POP07",
        "D_source_sample":"POP08", "D_complete_participant_flow_reconstruction":"POP08;POP06;POP10;POP11;POP09",
        "E_ascertainment_source":"OUT04", "E_threshold_definition":"OUT08",
        "E_full_definition":"OUT02;OUT03;OUT08", "E_definition_reproducibility":"OUT16",
        "E_definition_completeness":"OUT18", "F_initial_predictor_count":"PRD02",
        "F_candidate_set_completeness":"PRD13", "F_feature_selection_method":"PRE09;PRE10;PRE11;PRE12",
        "F_timing_relative_to_split_resampling":"PRE05;PRE13;IMB03",
        "F_leakage_concern":"PRD08;PRD09;PRD10", "G_hyperparameter_search":"MOD07;MOD12;MOD13",
        "G_tuning_method":"MOD07", "G_tuning_evaluation_separation":"MOD13",
        "G_author_selected_model":"MOD05;BEST02", "G_selection_criterion":"BEST01;BEST03",
        "H_later_period_validation":"VAL02", "H_external_validation":"VAL02",
        "H_evaluation_prevalence_identifiable":"IMB05",
        "H_metrics_reported":";".join(metric_ids.split(";")[:21]),
        "H_calibration_reported":"MET_CALSLOPE_R;MET_CALINT_R;MET_CALPLOT_R",
        "H_Brier_score_reported":"MET_BRIER_R", "H_decision_curve_reported":"MET_DCA_R",
        "I_reduced_predictor_set":"VI10", "I_downstream_statistical_analysis":"VI11",
        "J_omission_justified":"SUR13", "K_final_model_specification":"MOD14;REP17",
        "K_data_availability":"REP19", "K_registration":"REP19",
        "L_development_unit_count":"ADM03;MOD01", "L_evaluation_unit_count":"ADM03;VAL01",
        "L_development_domain_summary":"PD_D1;PD_D2;PD_D3;PD_D4",
        "L_evaluation_domain_summary":"PE_D1;PE_D2;PE_D3;PE_D4",
        "L_development_overall_judgements":"PD_OVERALL", "L_evaluation_overall_judgements":"PE_OVERALL",
        "L_study_level_PROBAST_summary":"PD_OVERALL;PE_OVERALL",
        "M_importance_stability_support_criteria_met":"VI01;VI16",
        "M_population_association_support_criteria_met":"ORI01;PUR01;ASSOC01;ASSOC02;ASSOC03",
        "M_individual_application_support_criteria_met":"ORI01;USE01;VAL02;THR01;MET_CALSLOPE_R;MET_CALINT_R;MET_CALPLOT_R",
        "M_surveillance_policy_support_criteria_met":"USE01;SUR04;SUR08;SUR09;SUR10",
        "N_evidence_page_table_figure":"QA02", "N_evidence_anchor_ID":"QA02",
        "N_extraction_notes":"QA07;QA11", "N_adjudication_notes":"ORI01;QA10",
        "N_protocol_exceptions":"OUT18;PRD15;QA08",
    })
    for metric, item in (("accuracy", "MET_ACC_R"), ("AUROC", "MET_AUROC_R"),
                         ("AUPRC", "MET_AUPRC_R"), ("F1", "MET_F1_R")):
        for suffix in ("", "_model", "_evaluation"):
            exact[f"H_best_{metric}{suffix}"] = f"{item};BEST01;BEST02;BEST03"
    return exact[header]


def figure_table_for_field(header):
    return {"A":"Table S7/STUDIES", "B":"Figures 2, 3, 5", "C":"Figure 2", "D":"Figure 4",
            "E":"Figures 6, 7", "F":"Figures 7, 8", "G":"Figures 5, 8", "H":"Figures 8, 9",
            "I":"Figure 10", "J":"Figure 11", "K":"Figure 11", "L":"Figure 11",
            "M":"Figure 11C", "N":"Tables S4, S7"}[header[0]]


def analysis_unit_for_field(header):
    if header == "H_threshold_reported":
        return "Study (across evaluations)"
    repeated = {"B_scientific_purpose_records": "Purpose record within study",
                "B_analytic_output_records": "Analytic-output record within study",
                "B_proposed_use_records": "Proposed-use record within study",
                "B_method_target_stages_detailed": "Method stage within study"}
    if header in repeated:
        return repeated[header]
    return {"A":"Study/Report", "B":"Study", "C":"Dataset/Study", "D":"Study/Dataset",
            "E":"Outcome", "F":"Development/Model", "G":"Model/Development",
            "H":"Evaluation", "I":"Model", "J":"Analysis/Study", "K":"Study/Model",
            "L":"Development/Evaluation", "M":"Eligible analysis/Study", "N":"Study/Evidence"}[header[0]]


def protocol_crosswalk(headers):
    public_items = [{"item_id": row[0], "question": row[1], "primary_unit": PUBLIC_CLASSIFICATION_UNITS[row[0]][0],
                     "required_related_ids": PUBLIC_CLASSIFICATION_UNITS[row[0]][1],
                     "item_role": "appraisal_judgement", "decision_rule": f"{row[4]} Exception/example: {row[5]}",
                     "evidence_required": row[6],
                     "applicability": row[2], "allowed_values": row[3], "response_type": row[3],
                     "output_mapping": "Figures 2, 3, 5, or 11C"} for row in PUBLIC_CLASSIFICATION_ROWS]
    items = public_items + protocol_items()
    ordered_ids = [item["item_id"] for item in items]
    def expand(spec):
        result = []
        for part in spec.split(";"):
            part = part.strip()
            if "-" in part:
                start, end = part.split("-", 1)
                if start in ordered_ids and end in ordered_ids:
                    result.extend(ordered_ids[ordered_ids.index(start):ordered_ids.index(end) + 1])
            elif part in ordered_ids:
                result.append(part)
        return result
    linked = defaultdict(list)
    for header in headers:
        for token in expand(protocol_ids_for_public_field(header)):
            linked[token].append(header)
    rows = []
    for item in items:
        variables = linked.get(item["item_id"], [])
        rows.append([item["item_id"], item["question"], item["primary_unit"], item["applicability"],
                     item["allowed_values"] or item["response_type"], "; ".join(variables) or "Technical/repository only",
                     "STUDIES/" + "; ".join(variables) if variables else "Relevant long-form sheet",
                     "Direct extraction unless item_role is derived/automated; retain item ID and evidence IDs",
                     item["applicability"], item["output_mapping"],
                     item.get("item_role", ""), item.get("required_related_ids", ""),
                     item.get("decision_rule", ""), item.get("evidence_required", ""),
                     item.get("official_item_id", ""), item.get("required_components", ""),
                     item.get("json_key", ""),
                     json.dumps(item, ensure_ascii=False, sort_keys=True)])
    return rows


def classification_reader_tables(wb):
    """Expose repeated classifications and their actual anchors as readable rows."""
    detail, links = [], []
    for doc in sorted(INCLUDED, key=lambda d: d["study_id"]):
        sid = doc["study_id"]
        source = doc["adjudication"]["purpose_evidence_v1_3"]
        anchors = {r["evidence_id"]: r for r in doc.get("evidence_registry", [])}

        def append(record_id, kind, code, record, path, scope):
            evidence = [(field, eid) for field, ids in record.items()
                        if field.endswith("evidence_ids") and isinstance(ids, list) for eid in ids]
            detail.append([sid, record_id, kind, code, str(code).replace("_", " ").capitalize(),
                           record.get("priority", "NA"), record.get("claim_strength", "NA"),
                           record.get("review_status", record.get("support_status", "NA")), record.get("other_text", record.get("description", "NA")),
                           record.get("statistical_analysis_id") or "UNCLEAR" if kind in {"association", "claim", "statistical_analysis"} else "NA",
                           " | ".join(dict.fromkeys(e for _, e in evidence)) or "NR",
                           scope, path, json_cell(record)])
            for role, eid in evidence:
                anchor = anchors.get(eid)
                links.append([sid, record_id, role, eid,
                              "RESOLVED" if anchor else "UNRESOLVED_ID", scope,
                              *[(anchor.get(k) if anchor.get(k) not in (None, "") else "NR") if anchor else "NR" for k in
                                ("source_file", "section", "pdf_page", "printed_page", "object_label",
                                 "start_anchor", "end_anchor", "excerpt")]])
            if not evidence:
                links.append([sid, record_id, "NR", "NR", "NO_EVIDENCE_ID", scope] + ["NR"] * 8)

        if source["primary_orientation"] == "HEALTH_FOCUSED":
            for kind, key, atom in (("purpose", "purpose_records", "purpose_code"),
                                    ("output", "analytic_output_records", "output_code"),
                                    ("use", "proposed_use_records", "use_code")):
                for i, record in enumerate(publication_detailed_records(source[key], kind, sid)):
                    append(record[f"{kind}_record_id"], kind, record[atom], record,
                           f"adjudication.purpose_evidence_v1_3.{key}[{i}]", "Record-specific anchors; original evidence roles retained")
            association = source.get("association_audit", {})
            if any(r["purpose_code"] in {"POPULATION_ASSOCIATION", "POPULATION_ASSOCIATION_ANALYSIS"}
                   for r in source["purpose_records"]):
                append(f"{sid}-ASSOC-001", "association", "POPULATION_ASSOCIATION_ANALYSIS", association,
                       "adjudication.purpose_evidence_v1_3.association_audit",
                       "Study-level retained association audit; not an invented statistical-analysis linkage")
            for i, record in enumerate(source.get("claim_evidence_records", [])):
                append(record["claim_id"], "claim", record["claim_type"], record,
                       f"adjudication.purpose_evidence_v1_3.claim_evidence_records[{i}]",
                       "Retained claim linkage; null analysis/model/outcome IDs remain unresolved")
            for i, record in enumerate(source.get("statistical_analysis_records", [])):
                record = dict(record)
                record["other_text"] = record["description"] + " " + "; ".join(
                    f"{field}: {record[field]} [{record['field_status'][field]}]"
                    for field in ("population", "outcome", "model_or_contrast", "result"))
                append(record["statistical_analysis_id"], "statistical_analysis", record["description"], record,
                       f"adjudication.purpose_evidence_v1_3.statistical_analysis_records[{i}]",
                       record["note"] + " Analysis identification does not change the survey-design audit judgment.")
            for i, revision in enumerate(source.get("classification_revisions", [])):
                public_revision = dict(revision, review_status="COMPLETE", other_text=revision["reason"])
                append(revision["revision_id"], "classification_revision", revision["decision"], public_revision,
                       f"adjudication.purpose_evidence_v1_3.classification_revisions[{i}]",
                       f"Previous: {revision['old_code']}; current: {revision['new_code'] or 'withdrawn from positive codes'}. Historical record retained; not a positive output/use.")
        if source["primary_orientation"] == "METHOD_FOCUSED":
            method = source["method_research"]
            stage_field, stages = method_stage_source(method)
            for i, stage in enumerate(stages):
                record = {"method_stage_id": f"{sid}-STAGE-{i+1:03d}", "stage_code": stage,
                          "source_stage_value": method[stage_field][i],
                          "other_text": method.get("method_target_stages_other_text", method.get("other_text", "NR")) if stage == "OTHER" else "NA",
                          "evidence_ids": method.get("evidence_ids", []),
                          "evidence_scope": "METHOD_LEVEL_NOT_STAGE_SPECIFIC"}
                append(record["method_stage_id"], "method_stage", stage, record,
                       f"adjudication.purpose_evidence_v1_3.method_research.{stage_field}[{i}]",
                       "Method-level anchors only; no stage-specific allocation inferred")
            # One row per field/array element keeps comparator/dataset/criterion text
            # readable without parsing JSON. The original source remains intact.
            for field in ("method_research_type_detailed", "evaluation_mode", "comparators",
                          "evaluation_datasets", "primary_evaluation_criteria", "improvement_evidence"):
                values = method.get(field, [])
                is_array = isinstance(values, list)
                if not is_array:
                    values = [values]
                aliases = {"EMPIRICAL_COMPARATOR": "EMPIRICAL_COMPARATOR_EVALUATION",
                           "SIMULATION_PLUS_EMPIRICAL": "SIMULATION_AND_EMPIRICAL_APPLICATION",
                           "EXTERNAL_TRANSPORT": "EXTERNAL_OR_TRANSPORTABILITY_EVALUATION",
                           "APPLICATION_DEMONSTRATION": "APPLICATION_OR_DEMONSTRATION",
                           "INSUFFICIENTLY_DESCRIBED": "EVALUATION_DESIGN_INSUFFICIENTLY_REPORTED"}
                for i, value in enumerate(values):
                    value = aliases.get(value, value) if field == "evaluation_mode" else value
                    rid = f"{sid}-METHOD-{field.upper()}-{i+1:03d}"
                    record = {"value": value, "evidence_ids": method.get("evidence_ids", [])}
                    if field == "improvement_evidence":
                        labels = {"PAIRED_COMPARISON":"Paired comparison on the same sample/split",
                                  "REPEATED_EVALUATION":"Repeated-split or resampling evaluation",
                                  "EXTERNAL_VALIDATION":"Evaluation outside development data",
                                  "SIMPLE_EXAMPLE":"Simple example or demonstration",
                                  "OTHER":"Other improvement evidence",
                                  "INSUFFICIENT":"Insufficient evidence of improvement"}
                        record["other_text"] = (labels.get(value, str(value)) + "; target method: " +
                            "study-level context, not a separately inferred method linkage; reported model labels: " +
                            clean([m.get("label", "NR") for m in doc.get("units", {}).get("models", [])]) +
                            "; contribution: " + str(method.get("method_research_type_detailed", "NR")) + "; comparators: " +
                            clean(method.get("comparators", [])) +
                            ("; OTHER: " + str(method.get("improvement_evidence_other_text", method.get("other_text", "NR"))) if value == "OTHER" else ""))
                        if method.get("improvement_evidence_ids"):
                            record["evidence_ids"] = method["improvement_evidence_ids"]
                    if field == "primary_evaluation_criteria" and method.get("primary_evaluation_criteria_evidence_ids"):
                        record["evidence_ids"] = method["primary_evaluation_criteria_evidence_ids"]
                        record["review_status"] = method["primary_evaluation_criteria_status"]
                    public_field = {"method_research_type_detailed": "method_contribution_detailed",
                                    "evaluation_mode": "method_evaluation_design"}.get(field, "method_" + field)
                    append(rid, public_field, value, record,
                           f"adjudication.purpose_evidence_v1_3.method_research.{field}" + (f"[{i}]" if is_array else ""),
                           ("Criterion-comparison anchors; array order is not an inferred primary ranking"
                            if field == "primary_evaluation_criteria" and method.get("primary_evaluation_criteria_evidence_ids")
                            else "Method-level anchors; array order and duplicates preserved"))
                    if field == "primary_evaluation_criteria" and value in {"Y", "N", "NA", "NR", "UNC", "UNCLEAR"}:
                        detail[-1][4] = f"Criterion name unresolved (stored status: {value})"
                        detail[-1][11] += "; stored status is not the name of an evaluation criterion"
    ws = _add_sheet(wb, "RECORD_DETAILS", ["study_id", "record_id", "Record type", "Code or reported value",
               "Reader label", "Priority", "Claim strength", "Review status", "Other description",
               "statistical_analysis_id", "Evidence IDs", "Evidence scope", "Source record path",
               "Complete record JSON (technical preservation)"], detail)
    # Hide only the technical backup by default; all substantive fields are visible.
    ws.column_dimensions["N"].hidden = True
    _add_sheet(wb, "RECORD_EVIDENCE", ["study_id", "record_id", "Evidence role", "evidence_id",
               "Link status", "Evidence scope", "Source file", "Section", "PDF page", "Printed page",
               "Object", "Start anchor", "End anchor", "Excerpt"], links)


def write_multisheet_s7(path, headers, rows):
    """Write the public relational workbook without flattening 1:N records away."""
    wb = Workbook()
    wb.remove(wb.active)
    readme = [
        ["Workbook role", "INTERNAL full coding log, not submitted (prompt 116). The submitted Additional Data 1 is "
         "KNHANES_ML_review_Additional_Data_1.xlsx; this workbook keeps every item response, both AI extractions "
         "and their comparison, evidence anchors and source extracts. STUDIES is the one-row-per-study view."],
        ["Reader entry point", "Start with STUDIES; VARIABLE_DICTIONARY defines the same 158 variables in the same order."],
        ["Sheets added in this release", "VARIABLE_DICTIONARY (reader dictionary of the STUDIES columns), ML_ADJACENT_REPORTS (the 95 reports using only regression-family or unsupervised methods, Figure 1), PROTOCOL_ITEMS and PROTOCOL_RESPONSE_CODES (all 306 coding items; the rules that produce the reported results are Supplementary Table S7), and the five ASSESSMENT_ sheets (readable study-level assessments)."],
        ["Authoritative detail", "Detailed purpose, output, use, and method records are authoritative; display categories and denominator flags are derived and must not be entered independently."],
        ["Missing states", "REPORTED has a value; NR=applicable but not reported; NA=structurally inapplicable; UNCLEAR=conflicting/insufficient evidence."],
        ["One-to-many data", "REPORTS, DATASETS, OUTCOMES, MODELS, DEVELOPMENTS, EVALUATIONS, PERFORMANCE_METRICS, and EVIDENCE_ANCHORS preserve repeated units and linkage IDs."],
        ["Protocol linkage", "DATA_DICTIONARY preserves technical definitions and PROTOCOL_CROSSWALK links each public variable to its source protocol item(s)."],
        ["Evidence completeness", "A coded output with an empty evidence_ids list retains an unresolved source location; a code is not proof of a fully linked evidence record."],
        ["Readable repeated records", "RECORD_DETAILS has one row per purpose/output/use/stage or method field value; RECORD_EVIDENCE resolves the actual evidence IDs to locations and excerpts. Filter by study_id and record_id; JSON is only a lossless technical backup."],
        ["Record identifiers", "Publication-derived IDs use study_id + PURPOSE/OUTPUT/USE/STAGE + one-based source-array position. They identify this release, not an independently verified analytic unit; source paths preserve the original zero-based position."],
        ["Association linkage", "statistical_analysis_id is the only analysis-ID name. Missing IDs are UNCLEAR, never fabricated from study-level co-occurrence. Method-level anchors must not be read as stage-specific evidence."],
        ["Statistical-analysis record schema", "Stored at adjudication.purpose_evidence_v1_3.statistical_analysis_records[]. Required fields: study_id, statistical_analysis_id, population, outcome, model_or_contrast, result, field_status, description, evidence_ids, note. field_status gives REPORTED/NR/UNCLEAR/NA per content field. An actual analysis ID requires identifying evidence, not merely a publication row ID. For ASSOC01–03, positive direct linkage requires the same analysis ID and element-specific evidence; unrecoverable positive linkage is UNCLEAR. Explicit absence, unreported content and inapplicability remain N, NR and NA respectively."],
        ["Analysis migration", "NR requires source review confirming nonreporting; an unextracted field has null value/status and extraction_status=PENDING. Source-reviewed supplements and field-specific evidence are retained with revision history. RECORD_DETAILS displays content/status; identifying a test does not establish survey-design adequacy."],
        ["Method improvement evidence", "Source: adjudication.purpose_evidence_v1_3.method_research.improvement_evidence. PAIRED_COMPARISON=paired comparison on the same sample/split; REPEATED_EVALUATION=repeated-split/resampling evaluation; EXTERNAL_VALIDATION=evaluation outside development data; SIMPLE_EXAMPLE=simple example/demonstration; OTHER=other described evidence; INSUFFICIENT=insufficient evidence of improvement. RECORD_DETAILS/method_improvement_evidence retains value, target method/comparator and OTHER text; RECORD_EVIDENCE retains anchors and their scope. Evidence type is not a positive finding of improvement."],
        ["Detailed method stages", "Use method_research.method_target_stages_detailed[] when present, otherwise target_analysis_stages[]. Conflicting current/legacy values fail generation. Preserve OTHER descriptions, actual source path and original code in the detailed row; derive Figure 5 groups separately."],
        ["Protocol publication scope", "PROTOCOL_ITEMS gives the English 306-item content instrument, not the entire 382-item, 17-field protocol; Supplementary Table S7 states the rules that produce the reported results. PROTOCOL_CROSSWALK preserves all current English canonical item metadata. The full protocol has not been publicly deposited."],
        ["Audit provenance", "AI_DISAGREEMENTS and FINAL_ADJUDICATION are technical provenance sheets; they are not required to interpret the study variables."],
        ["Analysis field reading", "ANALYSIS_FIELDS is a field-wise view of the existing statistical_analysis records, not a new parallel record system. Read content, field_status, extraction_status, evidence_scope and scope_note separately. REPORTED text can explicitly retain an unknown analysis-specific sample size; a source conflict remains UNCLEAR. Earlier values remain in field_revisions in the technical record."],
        ["Final responses", "ITEM_RESPONSES contains original final values, statuses, unit IDs, related IDs and anchors. Key: study_id + item_id + primary_unit + unit_id + response_index (one-based original item-array position, stable within this release). final_value maps to source value; selected_source maps to retained review_stage, not a response value. ANSWERED is the retained legacy completion status, not recoded to REPORTED. Filter EVIDENCE_ANCHORS by evidence_id to read source locations and excerpts."],
        ["Selection and source records", "MODEL_SELECTIONS retains each author-designated selection, criterion, ties and metric/evaluation/model IDs. SOURCE_PACKAGE and VISUAL_DETAILS expose source coverage and visual content. SOURCE_METADATA displays remaining metadata. TEXT_CONTINUATIONS holds long reader text in ordered pieces keyed by sheet/cell; concatenate without separators. SOURCE_JSON holds the complete source record as ordered ASCII JSON chunks (including original nulls, types, control characters, all adjudication fields and history); verify its SHA-256 after joining. It is a technical backup, not the reading entry point."],
    ]
    legacy_section = (ROOT / "KNHANES_ML_study_audit_protocol.md").read_text().split(
        "| Historical stored name/value (import only) |", 1)[1].split("\n\n", 1)[0]
    for line in legacy_section.splitlines()[2:]:
        cells = [c.strip() for c in line.strip("|").split("|")]
        if len(cells) == 3:
            readme.append(["Legacy import crosswalk: " + cells[0], cells[1] + "; " + cells[2]])
    from protocol_reader_keys import TECHNICAL_LOOKUP, S2_KEYS, S9_KEYS
    readme.extend(TECHNICAL_LOOKUP)
    readme.extend(("Protocol key: " + k, v) for k,v in S2_KEYS)
    readme.extend(("Assessment key: " + k, v) for k,v in S9_KEYS)
    _add_sheet(wb, "README", ["Topic", "Definition"], readme)
    _add_sheet(wb, "STUDIES", headers, rows, freeze="C2", group_colours=True)
    for sheet, unit in (("REPORTS","reports"), ("DATASETS","datasets"), ("OUTCOMES","outcomes"),
                        ("MODELS","models"), ("DEVELOPMENTS","developments"), ("EVALUATIONS","evaluations")):
        h, r = _records_table(_flat_records(unit)); _add_sheet(wb, sheet, h, r)
    h, r = _records_table(_long_records("performance_metrics")); _add_sheet(wb, "PERFORMANCE_METRICS", h, r)
    h, r = _records_table(_long_records("evidence_registry")); _add_sheet(wb, "EVIDENCE_ANCHORS", h, r)
    classification_reader_tables(wb)
    add_final_response_tables(wb, sorted(INCLUDED, key=lambda d: d['study_id']), _add_sheet)
    disagreements, finals = [], []
    for doc in sorted(INCLUDED, key=lambda x: x["study_id"]):
        adj = doc.get("adjudication", {})
        ds = adj.get("disagreements", [])
        if not ds:
            finals.append([doc["study_id"], "STUDY", "NA", "FINAL_CONSENSUS", adj.get("status", "COMPLETE"),
                           adj.get("resolution_policy", "NR"), adj.get("corpus_decision", "INCLUDE"), "No retained item-level disagreement"])
        for d in ds:
            disagreements.append([doc["study_id"], "LEGACY_P1_P2_RECONCILIATION", d.get("item_id", "NR"),
                                  d.get("primary_unit", "NR"), "LEGACY_P1_MIGRATION", json.dumps(d.get("P1"), ensure_ascii=False),
                                  "BLINDED_LLM_P2", json.dumps(d.get("P2"), ensure_ascii=False), d.get("decision", "NR"), d.get("rationale", "NR")])
            finals.append([doc["study_id"], d.get("item_id", "NR"), d.get("primary_unit", "NR"),
                           "FINAL_CONSENSUS", d.get("decision", "NR"), adj.get("resolution_policy", "NR"),
                           adj.get("corpus_decision", "INCLUDE"), d.get("rationale", "NR")])
    _add_sheet(wb, "AI_DISAGREEMENTS", ["study_id","workflow_generation","item_id","primary_unit","extractor_A_role","extractor_A_value","extractor_B_role","extractor_B_value","comparison_or_decision","rationale"], disagreements)
    _add_sheet(wb, "FINAL_ADJUDICATION", ["study_id","item_id","primary_unit","review_stage","selected_source_or_adjudication_status","resolution_policy","corpus_decision","rationale"], finals)
    dictionary = field_dictionary(headers, rows)
    _add_sheet(wb, "DATA_DICTIONARY", ["Variable name", "Domain", "Definition", "Analysis unit", "Applicability", "Storage type", "Permitted codes/format", "Reader labels", "Missing codes", "Multiple selection", "Evidence rule", "Protocol item ID(s)", "Derivation", "Figure/Table"], dictionary)
    topic_crosswalk = tsv('data/protocol_v1_3/topic_crosswalk.tsv')
    # prompt 106: the published crosswalk covers the earlier health-focused studies; excluded studies are dropped and each
    # criterion-A health-focused study is added with the topic, raw topic text and evidence of its v1.3 purpose record.
    included_ids = {r["study_id"] for r in INCLUDED}
    health_ids = {r["study_id"] for r in INCLUDED if r["adjudication"]["purpose_evidence_v1_3"]["primary_orientation"] == "HEALTH_FOCUSED"}
    topic_crosswalk = [r for r in topic_crosswalk if r["study_id"] in included_ids and r["study_id"] in health_ids]  # review 20261023: reclassified studies leave
    by_doc = {r["study_id"]: r for r in INCLUDED}
    for r in topic_crosswalk:  # review 20261023: topics corrected by the two-AI review follow the v1.3 record
        cur = by_doc[r["study_id"]]["adjudication"]["purpose_evidence_v1_3"]["health_topic"]["primary_topic_18"]
        if r.get("canonical_topic") != cur:
            r["canonical_topic"] = cur
            r["disposition"] = (r.get("disposition") or "") + " | review 20261023: topic corrected (outcome-based)"
    known = {r["study_id"] for r in topic_crosswalk}
    for r in sorted(INCLUDED, key=lambda x: x["study_id"]):
        if r["study_id"] in health_ids and r["study_id"] not in known:
            ht = r["adjudication"]["purpose_evidence_v1_3"]["health_topic"]
            topic_crosswalk.append({"study_id": r["study_id"], "canonical_key": r.get("canonical_key"),
                                    "title": r.get("metadata", {}).get("title"), "legacy_topic": "NA",
                                    "previous_S1_topic": "NA", "canonical_topic": ht["primary_topic_18"],
                                    "primary_outcome": ht.get("raw_detailed_topic") or ht.get("raw_broad_topic"),
                                    "evidence_ids": ";".join(ht.get("evidence_ids") or []),
                                    "disposition": "Prompt 106 criterion-A addition: topic from the recorded TSK04/TSK05 health topic (topic_adjudications.json override where recorded); single extraction"})
    assert len(topic_crosswalk) == len(health_ids), (len(topic_crosswalk), len(health_ids))
    _add_sheet(wb, 'TOPIC_CROSSWALK', list(topic_crosswalk[0]), [list(r.values()) for r in topic_crosswalk])
    cases = load_json('data/protocol_v1_3/judgement_reassessment.json')
    _add_sheet(wb, 'SOURCE_REASSESSMENT', cases['columns'], cases['rows'])
    amendments = [a for d in INCLUDED for a in d.get('declared_source_amendments', [])]
    _add_sheet(wb, 'DECLARED_AMENDMENTS', ['study_id','item_id','unit_id','previous_value','revised_value','previous_rationale','revised_rationale','source','pdf_page'],
               [[a['study_id'],a['item_id'],a['unit_id'],a['before']['value'],a['after']['value'],a['before'].get('rationale'),a['after'].get('rationale'),a['source'],a['pdf_page']] for a in amendments])
    _add_sheet(wb, "PROTOCOL_CROSSWALK", ["Protocol item ID","Human-readable question","Analysis unit","Applicability","Response/status","Public variable(s)","S7 sheet/column","Derivation","Applicable denominator","Figure/Table", "Item role", "Required linkage IDs", "Decision and exceptions", "Evidence requirement", "Official item ID", "Required components", "JSON key", "Canonical metadata JSON"], protocol_crosswalk(headers))
    from build_purpose_output_relationships import build as build_relationships
    relationships = build_relationships()
    _add_sheet(wb, 'PURPOSE_OUTPUT_2X2', ['Relationship','Both','Purpose only','Output only','Neither','N','Unit'],
               [[r['relationship'], *r['counts'].values(), r['denominator'], relationships['unit']] for r in relationships['relationships']])
    _add_sheet(wb, 'PURPOSE_OUTPUT_STUDIES', list(relationships['rows'][0]), [list(r.values()) for r in relationships['rows']])
    # Prompt 093: long listings that left the supplement PDF are kept here as plainly named sheets.
    reader_dictionary = [[row[i] for i in (0, 1, 2, 3, 4, 7, 11, 12)] for row in dictionary]
    _add_sheet(wb, "VARIABLE_DICTIONARY", ["Variable name", "Domain", "Definition", "Record unit", "Applicability",
                                           "Reader codes/labels", "Protocol item ID(s)", "Source or derivation"], reader_dictionary)
    _add_sheet(wb, "ML_ADJACENT_REPORTS", ["Year", "Title", "Identifier", "ML-adjacent methods", "Reason"], ml_adjacent_rows())
    _add_sheet(wb, "PROTOCOL_ITEMS", ["Item ID", "Question", "Record unit / required linkage IDs", "Applicability",
                                      "Response choices", "Decision rule and exceptions", "Required evidence"], human_protocol_rows(),
               section_rows=True)
    _add_sheet(wb, "PROTOCOL_RESPONSE_CODES", ["Item ID", "Exact raw response choices", "Readable response choices (same order)"],
               lookup_rows(human_protocol_rows(readable_choices=False)))
    # Prompt 112 (review v49): harmonisation dictionary behind Figure 5 and the harmonised variables of each ranking study.
    import json as _json
    _r = _json.loads((ROOT / "results/derived/practice_trends_112.json").read_text())["rankings_named_112"]
    _add_sheet(wb, "VARIABLE_HARMONISATION", ["Harmonised variable", "Family", "Kept when the study's domains include", "Pattern on the recorded variable name"],
               [[d["variable"], d["family"], ", ".join(d["confirming_domains"]), d["pattern"]] for d in _r["dictionary"]]
               + [[v, next(d["family"] for d in _r["dictionary"] if d["variable"] == v), k, "(implied by the extracted domain)"] for k, v in _r["domain_implies"].items()])
    _add_sheet(wb, "RANKING_VARIABLES", ["study_id", "Harmonised variables named as most important"],
               [[k, "; ".join(v)] for k, v in _r["variables_per_study"].items()])
    # Prompt 113 (external review): practices of the 192 core studies without the studies added under the final criterion,
    # by whether a ranking was produced, and in 2025 and 2026 separately (counts of studies reporting each practice).
    _s = _json.loads((ROOT / "results/derived/practice_trends_113.json").read_text())
    _sens, _rd, _yr = _s["sensitivity_without_added_113"], _s["ranking_by_design_113"], _s["years_2025_2026_113"]
    _cols = [(f"All {N_CORE} core studies", _sens["all"]), (f"Without the {_sens['added_core']} added under the final criterion", _sens["without_added"]),
             (f"The {_sens['added_core']} added under the final criterion", _sens["added_only"]), ("Producing a ranking", _rd["ranking"]),
             ("Producing no ranking", _rd["no_ranking"]), ("Published in 2025", _yr["2025"]), ("Published in 2026", _yr["2026"])]
    _labels = [("n", "Studies"), ("ranking", "Importance ranking produced"), ("shap", "SHAP used"), ("stability", "Ranking stability checked"),
               ("weights_mentioned", "Sampling weights mentioned"), ("weights_in_fitting", "Weights used in model fitting"),
               ("weights_in_evaluation", "Weights used in performance evaluation"), ("strata_or_psu", "Strata or PSUs used in variance estimation"),
               ("preprocessing_all_within", "All preprocessing within the training data"),
               ("preprocessing_any_before", "At least one preprocessing step before the split"), ("code_shared", "Analysis code shared"),
               ("calibration", "Calibration reported"), ("validation_beyond_development", "Validation beyond the development data")]
    _add_sheet(wb, "SENSITIVITY_ANALYSES", ["Practice (studies reporting it)"] + [c for c, _ in _cols],
               [[lab] + [v[k] for _, v in _cols] for k, lab in _labels]
               + [["Added core studies (study IDs)", ", ".join(_sens["added_core_ids"])] + ["\u2013"] * (len(_cols) - 1)])
    captured = []
    build_study_audit_table(INCLUDED, headers, rows, lambda *args, **kwargs: captured.append(args[3]))
    for (panel, panel_headers, panel_rows), sheet in zip(captured[0], ["ASSESSMENT_SCOPE", "ASSESSMENT_VALIDATION_SURVEY",
                                                                       "ASSESSMENT_APPRAISAL", "ASSESSMENT_RECOVERY_VS_REPORTING",
                                                                       "ASSESSMENT_SOURCE_RECHECKS"]):
        _add_sheet(wb, sheet, list(panel_headers), panel_rows)
    wb.save(path)


def ml_adjacent_rows():
    """Candidate reports using only regression-family or unsupervised methods (97 under criterion A; Figure 1)."""
    verdicts = load_json("results/derived/verdicts.json")
    screen_rows = load_json("results/derived/screen.json")["rows"]
    candidates = {r.get("uid") for r in screen_rows if r.get("tier") not in (None, "", "--")}
    screen_by_uid = {r.get("uid"): dict(r) for r in screen_rows}
    dup = {c["record"].split(" ")[0] for c in FLOW.get("coordinator_corrections", [])}  # review 20261023: duplicate record removed
    adjacent = [v for v in verdicts.values() if v.get("verdict") == "INCLUDE_ADJACENT" and v.get("uid") in candidates and v.get("uid") not in dup]
    _pin(len(adjacent), 101, "build_standalone_supplements.py:1981")  # prompt 106 pin
    # KCI supplementary-search records carry year and title in KCI_CANDIDATES.tsv, not in screen.json.
    for row in tsv("data/KCI_CANDIDATES.tsv"):
        uid = row.get("corpus_uid")
        if not uid:
            continue
        base = screen_by_uid.setdefault(uid, {})
        base["title"] = base.get("title") or row.get("title_en") or row.get("title")
        base["year"] = base.get("year") or row.get("year")
        if not base.get("doi") and row.get("doi"):
            base["doi"] = row["doi"]
    out = []
    for v in sorted(adjacent, key=lambda x: (str(screen_by_uid.get(x["uid"], {}).get("year", "")), x["uid"])):
        sr = screen_by_uid.get(v["uid"], {})
        ident = sr.get("doi") or (f"PMID {sr['pmid']}" if sr.get("pmid") else v["uid"].replace("kci:", "KCI "))
        reason = str(v.get("reason", ""))
        reason = reason.split(":", 1)[-1].strip() if reason.startswith("ADJACENT") else reason
        out.append([str(sr.get("year", "NR")), str(sr.get("title", "NR")), str(ident), "; ".join(v.get("ml_methods") or []) or "NR", reason])
    return out


def build_compact_tables():
    denominator_rows = [
        ["Orientation x task", "Health-focused", 192, 14, 8, 214, "Figures 2--5; topic and purpose synthesis"],  # prompt 106
        ["Orientation x task", "Method-focused", 31, 2, 3, 36, "Supplementary Figure S1; method-focused synthesis"],
        ["Orientation x task", "Total", 223, 16, 11, 250, "Included-study census"],
        ["Analysis denominator", "Prediction studies", "NA", "NA", "NA", 238, "Reporting appraisal"],  # prompt 106
        ["Analysis denominator", "Health-focused classification", "NA", "NA", "NA", 192, "Detailed classification workflow"],  # prompt 106
        ["Analysis denominator", "Model-development units", "NA", "NA", "NA", 355, "PROBAST+AI development appraisal"],  # prompt 106
        ["Analysis denominator", "Performance-evaluation units", "NA", "NA", "NA", 435, "PROBAST+AI evaluation appraisal"],  # prompt 106
    ]
    emit_table(1, "Orientation_task_denominator_map", "Research-orientation x analytic-task matrix and denominator map",
               ["Block", "Population", "Classification", "Continuous/ordered prediction", "Other tasks", "N", "Use"], denominator_rows)
    sensitivity_rows = [
        ["Screening evidence", "Validation + calibration + threshold", "Validation + calibration or threshold", f'{CLAIM["screening_or_individual_application_claim"]["strict_all_three"]}/{CLAIM["screening_or_individual_application_claim"]["denominator"]}', f'{CLAIM["screening_or_individual_application_claim"]["relaxed_validation_plus_calibration_or_threshold"]}/{CLAIM["screening_or_individual_application_claim"]["denominator"]}', "One decision-support component required"],
        ["Retracted report", "KHM068 included in historical appraisal", "KHM068 excluded", "283/308; 399/401", "282/307; 397/399", "Overall interpretation unchanged"],
    ]
    emit_table(2, "Sensitivity_and_robustness", "Sensitivity and robustness analyses",
               ["Analysis", "Primary analysis", "Alternative analysis", "Primary result", "Alternative result", "Interpretation"], sensitivity_rows,
               "The screening packages are review-level definitions, not universal standards. Development and evaluation appraisal denominators are reported separately.")
    master_path, headers, rows = make_master_backdata()
    block_specs = [
        ("A", "Bibliographic identity"), ("B", "Research classification"), ("C", "KNHANES data"),
        ("D", "Population and sample"), ("E", "Outcome"), ("F", "Predictors and preprocessing"),
        ("G", "Algorithms and model selection"), ("H", "Validation and performance"),
        ("I", "Variable interpretation"), ("J", "Complex-survey handling"),
        ("K", "Reporting and reproducibility"), ("L", "Formal appraisal"),
        ("M", "Claim--evidence correspondence"), ("N", "Audit trail"),
    ]
    schema_rows = []
    for code, label in block_specs:
        fields = [header for header in headers if header.startswith(code + "_")]
        schema_rows.append([code, label, len(fields), " | ".join(fields)])
    stem = "Supplementary_Table_S03_Master_study_level_backdata"
    tex = TEX / f"{stem}.tex"
    tex.write_text(table_tex("Supplementary Table S3. Master study-level classifications, extracted variables, and audit backdata",
                             ["Block", "Content", "Columns", "Field names"], schema_rows,
                             "The complete table is supplied as a single-sheet XLSX with " + str(N_ALL) + " included studies (one row per study), frozen headers, filters, pipe-delimited multivalues, and explicit NR/NA/UNCLEAR codes. One-to-many model, evaluation, metric, and evidence records remain in the research repository."), encoding="utf-8")
    compile_tex(tex)
    MANIFEST.append(["Supplementary Table S3", "Master study-level classifications, extracted variables, and audit backdata",
                     "XLSX; publication-form TeX/PDF schema", len(rows), str(master_path.relative_to(ROOT))])


def build_compact_figure():
    target = FIGURES / "Supplementary_Figure_S12_Full_health_topic_distribution.pdf"
    health_ids = {row["study_id"] for row in PURPOSE_ROWS if row["study_category"] == "HEALTH_ANALYSIS"}
    counts = Counter(row.get("health_topic", {}).get("primary_topic_18", "NOT_APPLICABLE")
                     for row in V13["records"] if row["study_id"] in health_ids)
    codes = ["MENTAL_HEALTH", "CARDIOVASCULAR", "METABOLIC_ENDOCRINE", "MUSCULOSKELETAL",
             "ORAL_HEALTH", "RESPIRATORY", "KIDNEY_UROLOGIC", "CANCER", "NUTRITION_DIET",
             "HEALTH_BEHAVIOUR", "OPHTHALMOLOGIC", "OTORHINOLARYNGOLOGIC", "DERMATOLOGIC_ALLERGIC",
             "INFECTIOUS_IMMUNE", "REPRODUCTIVE_WOMENS_HEALTH", "AGING_GERIATRIC",
             "GENERAL_HEALTH_MULTIMORBIDITY", "OTHER_OR_CROSS_CUTTING"]
    labels_by_code = {
        "MENTAL_HEALTH": "Mental health", "CARDIOVASCULAR": "Cardiovascular disease",
        "METABOLIC_ENDOCRINE": "Metabolic and endocrine health", "MUSCULOSKELETAL": "Musculoskeletal health",
        "ORAL_HEALTH": "Oral health", "RESPIRATORY": "Respiratory health",
        "KIDNEY_UROLOGIC": "Kidney and urologic health", "CANCER": "Cancer",
        "NUTRITION_DIET": "Nutrition and diet", "HEALTH_BEHAVIOUR": "Health behaviour",
        "OPHTHALMOLOGIC": "Eye health", "OTORHINOLARYNGOLOGIC": "Ear, nose, and throat health",
        "DERMATOLOGIC_ALLERGIC": "Dermatologic and allergic health",
        "INFECTIOUS_IMMUNE": "Infectious and immune health",
        "REPRODUCTIVE_WOMENS_HEALTH": "Reproductive and women's health",
        "AGING_GERIATRIC": "Aging and geriatric health",
        "GENERAL_HEALTH_MULTIMORBIDITY": "General health and multimorbidity",
        "OTHER_OR_CROSS_CUTTING": "Other or cross-cutting",
    }
    ordered = sorted(((code, counts.get(code, 0)) for code in codes), key=lambda x: (x[1], x[0]))
    labels = [labels_by_code[code] for code, _ in ordered]
    values = [value for _, value in ordered]
    fig, axes = plt.subplots(1, 2, figsize=(12.4, 6.6), gridspec_kw={"width_ratios": [1.15, 1.0]})
    ax = axes[0]
    major = {"MENTAL_HEALTH", "METABOLIC_ENDOCRINE", "CARDIOVASCULAR", "MUSCULOSKELETAL"}
    colours = ["#0072B2" if code in major else "#8CB6D1" for code, _ in ordered]
    bars = ax.barh(labels, values, color=colours)
    ax.set_xlabel("Health-focused studies (n)")
    ax.set_title("A. Full distribution of primary health topics (n=184)", loc="left", fontweight="bold")
    ax.grid(axis="x", color="#DDE3E8", linewidth=.8); ax.set_axisbelow(True)
    ax.spines[["top", "right"]].set_visible(False)
    for bar, value in zip(bars, values):
        ax.text(value + .35, bar.get_y() + bar.get_height()/2, f"{value} ({100*value/184:.1f}%)", va="center", fontsize=8.5)
    ax.set_xlim(0, max(values) * 1.30)

    temporal_topics = TEMPORAL["health_focused_classification"]["health_topics"]
    period_labels = ["≤2019", "2020–\n2022", "2023–\n2024", "2025–\n2026"]
    matrix = temporal_topics["counts"]
    denominators = temporal_topics["period_denominators"]
    palette = ["#0072B2", "#E69F00", "#009E73", "#CC79A7", "#D55E00", "#7A8494"]
    bottom = [0.0] * 4
    for i, label in enumerate(temporal_topics["categories"]):
        pct = [100 * matrix[j][i] / denominators[j] for j in range(4)]
        axes[1].bar(range(4), pct, bottom=bottom, color=palette[i], label=label)
        bottom = [a + b for a, b in zip(bottom, pct)]
    axes[1].set_xticks(range(4)); axes[1].set_xticklabels(period_labels)
    axes[1].set_ylim(0, 100); axes[1].set_ylabel("% of core classification studies")
    axes[1].set_title("B. Broad health-topic composition across periods", loc="left", fontweight="bold", fontsize=10.5, pad=18)
    axes[1].text(.98, .985, "Period n: " + " | ".join(map(str, denominators)), transform=axes[1].transAxes,
                 ha="right", va="top", fontsize=8, color="#4B5563",
                 bbox={"facecolor":"white","edgecolor":"none","alpha":.88,"pad":1.5})
    axes[1].text(.02, -.16, f"Exploratory Monte Carlo chi-square p={temporal_topics['monte_carlo_chi_square_p']:.3f}; Cramer's V={temporal_topics['cramers_v']:.3f}",
                 transform=axes[1].transAxes, fontsize=8, color="#4B5563")
    axes[1].legend(frameon=False, fontsize=7.4, ncol=2, loc="upper center", bbox_to_anchor=(.5, -.21))
    axes[1].spines[["top", "right"]].set_visible(False)
    fig.tight_layout(w_pad=3.2); fig.savefig(target, bbox_inches="tight"); plt.close(fig)
    tex = TEX / "Supplementary_Figure_S12_Full_health_topic_distribution.tex"
    rel = target.relative_to(ROOT)
    tex.write_text(document_tex("Supplementary Figure S12. Full health-topic distribution and exploratory composition across publication periods",
                                rf"\begin{{center}}\includegraphics[width=0.96\textwidth]{{{rel}}}\end{{center}}" +
                                "Panel A uses the same outcome-centred 18-category mapping as Supplementary Figure S3 and S7 (184 health-focused studies). "
                                "Primary outcomes take precedence over exposures or disease-restricted sampling; multidimensional quality of life is general health. "
                                "Panel B uses the same mapping in the 165-study core cohort, displaying five named categories and pooling the remainder. "
                                "S7/TOPIC\\_CROSSWALK provides all study IDs, prior labels, final labels and correction rationales. "
                                "Panel B test: fixed-margin Monte Carlo Pearson chi-square with 100,000 simulated tables (seed 20260917); "
                                "the p value is (1+b)/100,001, where b counts simulated statistics at least as large as the observed statistic "
                                "(numerical tolerance $10^{-12}$). Cram\\'er's $V=\\sqrt{\\chi^2/[N\\min(r-1,c-1)]}$ uses the uncorrected Pearson statistic."), encoding="utf-8")
    compile_tex(tex)
    MANIFEST.append(["Supplementary Figure S12", "Full health-topic distribution and exploratory composition across publication periods", "standalone TeX; PDF", "figure", str(target.relative_to(ROOT))])


DOMAIN_NAMES = {
    "A": "Study identity", "B": "Research classification", "C": "KNHANES data",
    "D": "Population and cohort", "E": "Outcome", "F": "Predictors and dataset preparation",
    "G": "Algorithms and model selection", "H": "Validation and performance",
    "I": "Variable interpretation", "J": "Complex-survey design",
    "K": "Reporting and reproducibility", "L": "Formal appraisal",
    "M": "Review-defined supporting evidence", "N": "Audit trail",
}


def field_dictionary(headers, rows):
    """Return a protocol codebook, never an inventory inferred from observed S7 cells.

    In particular, model names and evaluation IDs are identifiers/text rather than numeric
    values, and structured composites retain an explicit JSON grammar instead of exposing
    ambiguous pipe-delimited fragments as if they were atomic response codes.
    """
    definitions = {
        "A_study_id": "Stable identifier for the included study.",
        "A_representative_report_id": "Identifier of the report selected to represent the study family.",
        "B_primary_orientation": "Adjudicated four-state research orientation based on the objective, principal analysis or evaluation, main results, and conclusion.",
        "B_display_orientation_group": "Binary manuscript display group derived after review; it is not the reviewed orientation judgment.",
        "B_proposed_uses": "Author-stated downstream-use categories; NO_SPECIFIC_USE is derived only after completed review finds no positive use and is never reviewer-entered alongside a positive code.",
        "B_analytic_task": "Primary analytic task defined by the fitted outcome and evaluation scale.",
        "B_included_all": "Flag identifying membership in the complete included-study corpus; its N is calculated from the data, not encoded in the variable name.",
        "B_health_focused": "Flag identifying membership in the health-focused cohort.",
        "B_method_focused": "Flag identifying membership in the method-focused cohort.",
        "B_core_health_classification": "Flag identifying membership in the health-focused classification core cohort.",
        "B_other_health_analysis": "Flag identifying health-focused studies outside the core classification cohort.",
        "B_scientific_purposes": "Nonexclusive scientific questions supported by the objective and a principal analysis or result; proposed future uses are not coded as purposes.",
        "B_scientific_purpose_records": "Purpose records with publication-derived purpose_record_id, priority, confidence, evidence roles and OTHER text; readable rows in S7/RECORD_DETAILS and anchors in RECORD_EVIDENCE.",
        "B_analytic_outputs": "Unique output codes derived from B_analytic_output_records. Association estimates include any analytic role, independently of a population-association purpose; retain unresolved evidence links in the detailed records.",
        "B_analytic_output_records": "Output records with publication-derived output_record_id, evidence links and OTHER text; readable rows in RECORD_DETAILS and anchors in RECORD_EVIDENCE.",
        "B_proposed_use_records": "Positive-use records with publication-derived use_record_id, claim strength, review_status, evidence links and OTHER text; NO_SPECIFIC_USE is a derived study summary, never a record. Readable rows and anchors are in RECORD_DETAILS/RECORD_EVIDENCE.",
        "B_method_contribution_detailed": "Detailed method-research type retained before aggregation to the two-category Figure 5 display.",
        "B_method_target_stages_display": "Seven-category display mapping used in Figure 5; the detailed stage field is authoritative for audit.",
        "B_method_target_stages_detailed": "Ten detailed method-stage codes retained separately from Figure 5 display groups. RECORD_DETAILS gives each stage its method_stage_id and RECORD_EVIDENCE identifies the actual scope of its anchors.",
        "B_method_comparators": "Comparator methods used to evaluate the methodological contribution.",
        "B_method_evaluation_datasets": "Dataset or evaluation-unit identifiers used for method evaluation.",
        "B_method_primary_evaluation_criteria": "Named method-evaluation criteria with direct criterion-comparison anchors in RECORD_DETAILS. Primary ranking or tie-breakers are retained only when author-designated; array order is not a priority ranking. Author-specific definitions and qualitative criteria are preserved. Y/N/NA is not a criterion name.",
        "B_health_topic": "Primary health-topic category in the prespecified 18-category taxonomy.",
        "C_combined_cycle_weighting": "Completeness of reporting a sampling-weight strategy for pooling multiple KNHANES survey years within or across cycles (DAT11); this does not establish actual application (DAT13/SUR11).",
        "F_missing_data_method": "Methods used to handle missing predictor or outcome data before or within modelling.",
        "F_scaling_transformation": "Whether scaling, normalisation, encoding, or another predictor transformation was applied.",
        "F_class_rebalancing": "Methods used to address class imbalance in the analytic data.",
        "F_timing_relative_to_split_resampling": "Structured timing of missing-data handling, feature selection, and class rebalancing relative to data splitting or resampling.",
        "F_leakage_concern": "Structured flags for direct outcome components, deterministic outcome proxies, and post-outcome predictors.",
        "H_evaluation_prevalence_identifiable": "Retains all IMB05 states across evaluated samples. Figure 9 counts studies with R in at least one sample, not necessarily every sample; P is partial recovery, not full recovery.",
        "H_threshold_reported": "Y if at least one evaluated unit has THR01 FIXED05, YOUDEN, VAL_OOF, F1, CLINICAL or OTHER. Otherwise UNCLEAR for missing/null/empty/unknown responses, N for an explicit NR response, and NA only when all responses are NA. Positive overrides mixed states; raw unit records are retained. N does not establish explicit nonuse.",
        "H_threshold_selection_method": "All retained THR01 methods and missing states, without a primary-unit designation. Multiple methods may coexist with a scalar at-least-one reporting flag.",
        "H_evaluation_sample_size": "Retains all VAL10 sample counts and missing states; Figure 9 counts at least one positive integer evaluation sample size, excluding null, empty and unclear values.",
        "I_reduced_predictor_set": "Whether variable importance or selection was used to define a reduced predictor set.",
        "I_downstream_statistical_analysis": "Whether selected or important variables were entered into a subsequent statistical analysis.",
        "I_exact_variable_carryover": "Whether the exact variables selected by the ML step could be confirmed in the downstream statistical analysis.",
        "L_development_domain_summary": "JSON object containing study-level collections of PD_D1--PD_D4 development-domain judgements across development units.",
        "L_evaluation_domain_summary": "JSON object containing study-level collections of PE_D1--PE_D4 evaluation-domain judgements across evaluation units.",
        "E_definition_reproducibility": "Outcome-level recoverability, including source and timing. Retains observed grades; plotted study summaries take the least recoverable outcome (R0 before R1 before R2). Distinct from the single REP06 study reporting judgement.",
        "E_definition_completeness": "Overall adequacy of outcome construction, retained as robust, limited, high concern, or not assessable.",
        "F_candidate_set_completeness": "Recoverability of candidate and final selected predictor sets, coding and model linkage (PRD13); stable legacy field ID retained. Retains observed model grades; plotted study summaries take R0 before R1 before R2. This is not the REP07 study reporting judgement.",
        "H_best_AUROC": "Highest selected or author-designated AUROC retained at study level; detailed 1:N records remain in the repository.",
        "K_final_model_specification": "Completeness of the information needed to apply the final model to new observations.",
        "K_data_availability": "Retained REP19 composite reporting status (registration plus data/code availability); not a separately adjudicated data-availability indicator. Consult REP19 evidence for individual components.",
        "K_registration": "Retained REP19 composite reporting status (registration plus data/code availability); not a separately adjudicated registration indicator. Consult REP19 evidence for individual components.",
        "M_association_estimate_linked": "Whether an association estimate is directly linked to the eligible population-association analysis.",
        "M_survey_weights_linked_to_association": "Whether KNHANES survey weights are directly linked to the eligible population-association analysis.",
        "M_design_uncertainty_linked_to_association": "Whether design-based uncertainty using strata, PSUs, or an equivalent survey-aware variance method is directly linked to the eligible population-association analysis.",
        "M_importance_stability_support_criteria_met": "Whether a study reporting explicit model-based variable importance also assessed the stability of that importance result.",
        "M_population_association_support_criteria_met": "Whether a health-focused study with a population-association purpose met the review-defined survey-aware analysis criteria.",
        "M_individual_application_support_criteria_met": "Study-level reported-component summary: independent/later validation, calibration and threshold within the study; no same-model/outcome/evaluation linkage or independently selected threshold required.",
        "M_surveillance_policy_support_criteria_met": "Study-level reporting of survey weights plus strata, clusters/PSUs or design-based uncertainty among studies proposing surveillance/policy use; no analysis-level linkage is enforced.",
        "J_omission_justified": "Evidence-linked rationale for whether omission of complex-survey features was acceptable for the stated estimand and claims.",
        "L_study_level_PROBAST_summary": "Study-level summary of separate PROBAST+AI development-quality and evaluation-risk judgements.",
        "N_evidence_anchor_ID": "Pipe-delimited identifiers linking the extracted value to source evidence records.",
    }
    rep_defs = [
        "Study type identified in the title", "Structured summary in the abstract", "Objective, intended use, and target population",
        "Data source, design, and dates", "Eligibility and participant selection", "Outcome definition, timing, and source",
        "Predictor definition and timing", "Sample and event/class counts", "Sample-size rationale", "Missing-data handling",
        "Preprocessing, selection, and model development", "Hyperparameters and tuning", "Internal validation or resampling",
        "Evaluation data, metrics, and threshold", "Participant flow and characteristics", "Performance estimates and uncertainty",
        "Reusable final-model specification", "Limitations and generalisability", "Registration and data/code availability",
    ]
    applicability_by_block = {
        "A": "All " + str(N_ALL) + " included studies", "B": "All " + str(N_ALL) + " included studies",
        "C": "All " + str(N_ALL) + " included studies", "D": "All " + str(N_ALL) + " included studies",
        "E": "Studies with an analysed outcome", "F": "Studies with predictor-based modelling",
        "G": "Studies evaluating or fitting models", "H": "Studies with performance evaluation",
        "I": "Studies for which variable interpretation was applicable", "J": "All included studies",
        "K": "Prediction studies (n=238)", "L": "Applicable development/evaluation units",
        "M": "Field-specific eligible studies; the importance-stability field applies to studies reporting explicit model-based variable importance", "N": "All " + str(N_ALL) + " included studies",
    }
    evidence_by_block = {
        "A": "Use the representative report and registered bibliographic metadata.",
        "B": "Apply the operational classification rule and retain its evidence anchor.",
        "C": "Extract from Methods, data-source descriptions, or linked dataset documentation.",
        "D": "Extract participant-flow text or tables; do not infer missing counts.",
        "E": "Extract the author-defined outcome and threshold; judge reproducibility from the full source package.",
        "F": "Extract the pipeline-entry predictor set and preprocessing timing; do not count narrative lists unless author-defined.",
        "G": "Use model-development and author-selection records; preserve ties and multiple outcomes.",
        "H": "Use linked evaluation and metric records; retain the selected model and evaluation identifier.",
        "I": "Require an explicit interpretation method or downstream analysis in the report.",
        "J": "Distinguish survey weights from class weights and link design variables to the stated analysis stage.",
        "K": "Apply the REP01--REP19 reporting rubric to the accessible report package.",
        "L": "Derive from unit-level PROBAST+AI judgements without collapsing development and evaluation constructs.",
        "M": "Require the eligible purpose or analytic output and its review-defined supporting analysis to occur in the same study.",
        "N": "Retain source locations, evidence IDs, adjudication notes, and protocol exceptions verbatim or as stable identifiers.",
    }
    definition_templates = {
        "A": "Bibliographic or report-family {name} for the representative report.",
        "B": "Study-level research-classification value for {name}.",
        "C": "Reported KNHANES data-use value for {name}.",
        "D": "Target-population or participant-flow value for {name}.",
        "E": "Author-defined outcome value for {name}.",
        "F": "Predictor or dataset-preparation value for {name}.",
        "G": "Model-development or selection value for {name}.",
        "H": "Validation or performance-evaluation value for {name}.",
        "I": "Variable-interpretation or downstream-use value for {name}.",
        "J": "Complex-survey implementation value for {name}.",
        "K": "Reporting or reproducibility value for {name}.",
        "L": "PROBAST+AI appraisal value for {name}.",
        "M": "Review-defined supporting-evidence result for {name}.",
        "N": "Audit-trail value for {name}.",
    }
    health_topics = "CANCER | CARDIOVASCULAR | GENERAL_HEALTH_MULTIMORBIDITY | HEALTH_BEHAVIOUR | KIDNEY_UROLOGIC | MENTAL_HEALTH | METABOLIC_ENDOCRINE | MUSCULOSKELETAL | NUTRITION_DIET | OPHTHALMOLOGIC | ORAL_HEALTH | OTORHINOLARYNGOLOGIC | RESPIRATORY | DERMATOLOGIC_ALLERGIC | INFECTIOUS_IMMUNE | REPRODUCTIVE_WOMENS_HEALTH | AGING_GERIATRIC | OTHER_OR_CROSS_CUTTING"
    explicit_schema = {
        "A_study_id": ("Required unique identifier", "Unique non-empty study_id; NR/NA not permitted"),
        "B_primary_orientation": ("Controlled categorical", "HEALTH_FOCUSED | METHOD_FOCUSED | CO_PRIMARY | UNCLEAR"),
        "B_display_orientation_group": ("Controlled categorical", "HEALTH_ANALYSIS | METHOD_RESEARCH"),
        "B_classification_confidence": ("Controlled categorical", "HIGH | MODERATE | LOW | UNCLEAR"),
        "B_analytic_task": ("Controlled categorical", "CLASSIFICATION | CONTINUOUS_OR_ORDERED_ESTIMATION | MISSING_DATA_IMPUTATION | CLUSTER_DISCOVERY | PATTERN_OR_REPRESENTATION_DISCOVERY | CAUSAL_OR_HETEROGENEOUS_EFFECT_ESTIMATION | OTHER_ML_ANALYSIS"),
        "B_scientific_purposes": ("Controlled multi-select", "HEALTH_STATE_OR_HEALTH_VALUE_ESTIMATION | VARIABLE_RELEVANCE_OR_MODEL_INTERPRETATION | POPULATION_ASSOCIATION_ANALYSIS | HEALTH_PATTERN_OR_SUBGROUP_DISCOVERY | CAUSAL_EFFECT_OR_STRUCTURE_ESTIMATION | OTHER"),
        "B_scientific_purpose_records": ("Structured JSON array", '[{"purpose_record_id": <study_id-PURPOSE-NNN>, "purpose_code": <code>, "priority": PRIMARY|CO_PRIMARY|SECONDARY, "confidence": <code>, "objective_evidence_ids": [<ID>], "result_evidence_ids": [<ID>], "conclusion_evidence_ids": [<ID>], "other_text": <text if applicable>}]'),
        "B_health_topic": ("Controlled categorical", health_topics),
        "B_analytic_outputs": ("Controlled multi-select", "MODEL_PERFORMANCE | VARIABLE_CONTRIBUTION_OR_RANK | ASSOCIATION_ESTIMATE | REDUCED_PREDICTOR_SET | CAUSAL_EFFECT_ESTIMATE | IMPLEMENTED_TOOL | CLUSTER_OR_PATTERN_RESULT | OTHER"),
        "B_analytic_output_records": ("Structured JSON array", '[{"output_record_id": <study_id-OUTPUT-NNN>, "output_code": <code>, "evidence_ids": [<ID>], "other_text": <text if applicable>}]'),
        "B_proposed_uses": ("Controlled multi-select", "SCREENING | DIAGNOSTIC_SUPPORT | PERSONALISED_MANAGEMENT | RISK_GROUP_IDENTIFICATION | POPULATION_SURVEILLANCE_OR_POLICY | RESEARCH_OR_HYPOTHESIS_GENERATION | OTHER | NO_SPECIFIC_USE"),
        "B_proposed_use_records": ("Structured JSON array", '[{"use_record_id": <study_id-USE-NNN>, "use_code": <positive-use code>, "claim_strength": POSSIBLE_FUTURE_USE|RECOMMENDED_USE|TESTED_USE|IMPLEMENTED_USE, "review_status": COMPLETE|INCOMPLETE|UNCLEAR, "evidence_ids": [<ID>], "other_text": <text if applicable>}]'),
        "B_KNHANES_role": ("Controlled categorical", "PRIMARY_ANALYSIS_DATASET | ONE_OF_MULTIPLE_PRIMARY_DATASETS | EXTERNAL_OR_TRANSPORT_EVALUATION_DATASET | APPLICATION_OR_TEST_DATASET | UNCLEAR"),
        "B_method_contribution": ("Controlled categorical", "METHOD_WORKFLOW_OR_TOOL_DEVELOPMENT_OR_IMPROVEMENT | EXISTING_METHODS_COMPARISON_OR_EVALUATION"),
        "B_method_contribution_detailed": ("Controlled categorical", "NEW_OR_IMPROVED_METHOD | NEW_PROBLEM_OR_WORKFLOW_SOLUTION | EXISTING_METHOD_COMPARISON_BENCHMARK | OTHER"),
        "B_method_target_stages_display": ("Controlled multi-select", "DATA_INTEGRATION_OR_HARMONISATION | MISSING_DATA | VARIABLE_CONSTRUCTION_OR_SELECTION | MODEL_DEVELOPMENT | EXPLANATION_OR_INTERPRETATION | VALIDATION_OR_PERFORMANCE | USER_TOOL_OR_WORKFLOW"),
        "B_method_target_stages_detailed": ("Controlled multi-select", "DATA_INTEGRATION | MISSING_DATA | FEATURE_CONSTRUCTION_OR_SELECTION | REPRESENTATION_OR_CLUSTERING | MODEL_DEVELOPMENT | CAUSAL_OR_STRUCTURE | EXPLANATION_OR_INTERPRETATION | VALIDATION_OR_PERFORMANCE | USER_TOOL_OR_WORKFLOW | OTHER"),
        "B_method_evaluation_design": ("Controlled categorical", "APPLICATION_OR_DEMONSTRATION | EMPIRICAL_COMPARATOR_EVALUATION | SIMULATION_AND_EMPIRICAL_APPLICATION | EXTERNAL_OR_TRANSPORTABILITY_EVALUATION | EVALUATION_DESIGN_INSUFFICIENTLY_REPORTED"),
        "B_method_comparators": ("Structured JSON array", "UTF-8 comparator labels | NA"),
        "B_method_evaluation_datasets": ("Structured JSON array", "Stable dataset/evaluation identifiers | NA"),
        "B_method_primary_evaluation_criteria": ("Structured JSON array", "UTF-8 primary criterion labels or explicit status | NA"),
        "C_cycles": ("Controlled multi-select", "1 | 2 | 3 | 4 | 5 | 6 | 7 | 8 | 9"),
        "C_survey_years": ("Controlled multi-select", "1998 | 2001 | 2005 | 2007 | 2008 | 2009 | 2010 | 2011 | 2012 | 2013 | 2014 | 2015 | 2016 | 2017 | 2018 | 2019 | 2020 | 2021 | 2022 | 2023 | 2024"),
        "C_pooling_structure": ("Controlled categorical", "POOLED | SEPARATE | BOTH"),
        "C_components_used": ("Controlled multi-select", "HEALTH_INTERVIEW | EXAMINATION | LABORATORY | ORAL_HEALTH | NUTRITION | ACCELEROMETRY"),
        "C_role_relative_to_other_datasets": ("Structured JSON object", '{"mode": <protocol code>, "datasets": <text or list>}'),
        "C_linked_data": ("Free text", "UTF-8 linked-dataset name, linkage description, and URL where reported | NA"),
        "C_combined_cycle_weighting": ("Controlled categorical", "R | P"),
        "E_timing": ("Controlled categorical", "CURRENT | FUTURE | MIXED | UNCLEAR | NR | NA"),
        "E_scale": ("Controlled multi-select", "BINARY | MULTIBIN | MULTICLASS | ORDINAL | CONTINUOUS | TIME_EVENT | MIXED | OTHER"),
        "E_definition_reproducibility": ("Controlled multi-select", "R2 | R1 | R0"),
        "E_definition_completeness": ("Controlled multi-select", "ROBUST | LIMITED | HIGH | NAU"),
        "E_outcome_name": ("Free text", "UTF-8 author-defined outcome label | NR | NA"),
        "E_ascertainment_source": ("Free text", "UTF-8 measurement, questionnaire, examination, or linked-data source | NR | NA"),
        "E_threshold_definition": ("Free text", "UTF-8 numerical or categorical decision rule | NR | NA"),
        "E_full_definition": ("Structured JSON object", '{"name": <UTF-8 text>, "original_form": <UTF-8 text>, "cutoff": <UTF-8 text>}'),
        "F_candidate_set_completeness": ("Controlled multi-select", "R2 | R1 | R0"),
        "F_candidate_predictor_definition": ("Free text", "UTF-8 author-defined pipeline-entry predictor-set description | NR | NA"),
        "F_feature_selection_method": ("Controlled multi-select", "NOT_APPLIED | FILTER_METHOD | WRAPPER_OR_RFE | EMBEDDED_SELECTION | IMPORTANCE_BASED_SELECTION | PRIOR_KNOWLEDGE_OR_CLINICAL | UNIVARIATE_OR_STATISTICAL_FILTER | MULTIPLE_METHODS | METHOD_NOT_REPORTED | OTHER"),
        "F_missing_data_method": ("Controlled multi-select", "NONE | COMPLETE | SINGLE_IMP | MULTI_IMP | MULTIPLE | INDICATOR | MODEL_NATIVE | OTHER"),
        "F_scaling_transformation": ("Controlled multi-select", "USED | NOT_USED"),
        "F_class_rebalancing": ("Controlled multi-select", "NONE | WEIGHT | SMOTE | RANDOM | ALGO | MULTIPLE | OTHER"),
        "F_timing_relative_to_split_resampling": ("Structured JSON object", '{"missing": <timing code(s)>, "feature_selection": <timing code(s)>, "imbalance": <timing code(s)>}; timing codes: TRAIN | WITHIN | BEFORE | ORDER_NR | OTHER | NOT_USED'),
        "F_leakage_concern": ("Structured JSON object", '{"direct_target_component": Y|N|UNCLEAR, "deterministic_proxy": Y|N|UNCLEAR, "post_outcome_predictor": Y|N|UNCLEAR}'),
        "G_algorithm_families": ("Controlled multi-select", "Logistic regression | Decision tree | Random forest | Gradient boosting | XGBoost | LightGBM | SVM | kNN | Naive Bayes | DNN/MLP | Other prespecified family"),
        "G_hyperparameter_search": ("Controlled categorical", "TUNING_REPORTED_SEPARATED | TUNING_REPORTED_SEPARATION_NOT_DEMONSTRATED | TUNING_REPORTED_EVALUATION_DATA_INVOLVED | NO_TUNING_OR_DEFAULT_MODEL | TUNING_NOT_REPORTED | NOT_ASSESSABLE"),
        "G_tuning_method": ("Controlled categorical", "GRID_SEARCH | RANDOM_SEARCH | BAYESIAN_OR_OTHER_OPTIMISATION | MANUAL_OR_DEFAULT | OTHER_REPORTED | METHOD_NOT_REPORTED"),
        "G_tuning_evaluation_separation": ("Controlled categorical", "SEPARATE | TEST_OR_EVALUATION_INVOLVED | UNCLEAR | NA"),
        "G_author_selected_model": ("Free text", "UTF-8 author-designated model name or model-family label | NR | NA"),
        "G_selection_criterion": ("Free text", "UTF-8 author-reported model-selection rule | NR | NA"),
        "H_evaluation_prevalence_identifiable": ("Controlled multi-select", "R | P"),
        "H_internal_validation": ("Controlled multi-select", "SPLIT | CV | BOOT | APPARENT | TEMPORAL | EXTERNAL | OTHER | NONE_NR"),
        "H_threshold_reported": ("Controlled categorical", "Y | N | UNCLEAR | NA"),
        "H_threshold_selection_method": ("Controlled multi-select", "CLINICAL | F1 | FIXED05 | VAL_OOF | YOUDEN | OTHER"),
        "H_metrics_reported": ("Controlled multi-select", "ACC | BACC | AUROC | AUPRC | SENS | SPEC | PPV | NPV | F1 | MCC | KAPPA | BRIER | LOGLOSS | CALSLOPE | CALINT | CALPLOT | DCA | RMSE | MSE | MAE | R2 | OTHER"),
        "I_importance_methods": ("Controlled multi-select", "SHAP | MODEL_NATIVE | COEFFICIENT_STATISTIC | PERMUTATION | TREE_RULE | PERTURBATION_ABLATION | LIME | PDP | ALE | ICE | NETWORK_SPECIFIC | OTHER"),
        "I_importance_reported": ("Controlled multi-select", "USED | NOT_USED"),
        "I_importance_stability": ("Controlled multi-select", "USED | NOT_USED"),
        "I_reduced_predictor_set": ("Controlled multi-select", "USED | NOT_USED"),
        "I_downstream_statistical_analysis": ("Controlled multi-select", "USED | NOT_USED"),
        "I_exact_variable_carryover": ("Controlled multi-select", "USED | NOT_USED"),
        "J_weights_in_fitting": ("Controlled categorical", "USED | NOT_USED"),
        "J_weights_in_evaluation": ("Controlled categorical", "USED | NOT_USED"),
        "J_combined_cycle_weights": ("Controlled categorical", "USED | NOT_USED"),
        "J_strata_PSUs_in_uncertainty": ("Controlled categorical", "USED | NOT_USED"),
        "J_omission_justified": ("Free text", "UTF-8 applicability rationale | NR | NA"),
        "H_Brier_score_reported": ("Controlled multi-select", "R"),
        "H_decision_curve_reported": ("Controlled multi-select", "R"),
        "H_confidence_interval_reported": ("Controlled multi-select", "Y | N"),
        "H_paired_comparison_reported": ("Controlled multi-select", "Y | N"),
        "K_code_available": ("Controlled categorical", "PUBLIC_ACCESS_VERIFIED | PUBLIC_LINK_REPORTED_ACCESS_NOT_REVERIFIED | LINK_INACCESSIBLE | AVAILABLE_ON_REQUEST | PARTIAL_CODE_ONLY | NOT_PROVIDED_OR_NOT_REPORTED | UNCLEAR | NA"),
        "K_final_model_specification": ("Controlled categorical", "COMPLETE | PARTIAL | INSUFFICIENT | UNCLEAR | NA"),
        "K_data_availability": ("Controlled categorical", "R | P | NR"),
        "K_registration": ("Controlled categorical", "R | P | NR"),
        "L_development_domain_summary": ("Structured JSON object", '{"PD_D1": [HIGH|LOW|UNCLEAR|NA], "PD_D2": [...], "PD_D3": [...], "PD_D4": [...]}'),
        "L_development_overall_judgements": ("Controlled multi-select", "HIGH | LOW | UNCLEAR"),
        "L_evaluation_domain_summary": ("Structured JSON object", '{"PE_D1": [HIGH|LOW|UNCLEAR|NA], "PE_D2": [...], "PE_D3": [...], "PE_D4": [...]}'),
        "L_evaluation_overall_judgements": ("Controlled multi-select", "HIGH | LOW | UNCLEAR"),
        "L_study_level_PROBAST_summary": ("Structured JSON object", '{"development": [HIGH|LOW|UNCLEAR|NA], "evaluation": [HIGH|LOW|UNCLEAR|NA]}'),
        "M_association_estimate_linked": ("Controlled categorical", "Y | N | NR | UNCLEAR | NA"),
        "M_survey_weights_linked_to_association": ("Controlled categorical", "Y | N | NR | UNCLEAR | NA"),
        "M_design_uncertainty_linked_to_association": ("Controlled categorical", "Y | N | NR | UNCLEAR | NA"),
        "M_importance_stability_support_criteria_met": ("Controlled categorical", "Y | N | UNCLEAR | NA"),
        "M_population_association_support_criteria_met": ("Controlled categorical", "Y | N | UNCLEAR | NA"),
        "M_individual_application_support_criteria_met": ("Controlled categorical", "Y | N | UNCLEAR | NA"),
        "M_surveillance_policy_support_criteria_met": ("Controlled categorical", "Y | N | UNCLEAR | NA"),
    }
    flag_fields = {"B_included_all", "B_health_focused", "B_method_focused",
                   "B_core_health_classification", "B_other_health_analysis"}
    multi_select_tokens = ("purposes", "outputs", "uses", "stages", "components", "families",
                           "metrics_reported", "methods", "cycles", "survey_years", "overall_judgements",
                           "evidence_anchor")
    identifier_tokens = ("_id", "DOI", "PMID", "family_id")
    integer_fields = {"A_publication_year", "C_number_of_years", "D_source_sample", "D_final_sample",
                      "D_event_count", "F_initial_predictor_count", "H_evaluation_sample_size",
                      "L_development_unit_count", "L_evaluation_unit_count"}
    proportion_fields = {"D_prevalence", "H_evaluation_prevalence"}
    multi_integer_fields = {"D_event_count", "H_evaluation_sample_size"}
    multi_proportion_fields = {"D_prevalence", "H_evaluation_prevalence"}
    bounded_metric_fields = {"H_best_accuracy", "H_best_AUROC", "H_best_AUPRC", "H_best_F1"}
    model_text_fields = {f"H_best_{metric}_model" for metric in ("accuracy", "AUROC", "AUPRC", "F1")}
    evaluation_id_fields = {f"H_best_{metric}_evaluation" for metric in ("accuracy", "AUROC", "AUPRC", "F1")}
    binary_fields = {"D_age_restriction", "D_sex_restriction", "D_disease_risk_restriction",
                     "D_measurement_restriction", "D_complete_participant_flow_reconstruction",
                     "H_later_period_validation", "H_external_validation", "H_threshold_reported",
                     "H_calibration_reported", "H_confidence_interval_reported", "H_paired_comparison_reported",
                     "J_omission_justified"}
    report_status_fields = {"H_Brier_score_reported", "H_decision_curve_reported"}
    code_labels = {
        "R":"Reported/complete", "P":"Partially reported", "NR":"Not reported",
        "NA":"Not applicable", "UNCLEAR":"Conflicting or insufficient evidence",
        "Y":"Yes", "N":"No", "USED":"Used/reported", "NOT_USED":"Not used",
        "HIGH":"High", "LOW":"Low", "FULL":"Fully reproducible", "PARTIAL":"Partly reproducible",
        "INSUFFICIENT":"Insufficiently specified", "COMPLETE":"Complete-case analysis",
        "R2":"R-squared", "R1":"Partly recoverable", "R0":"Not recoverable",
        "ROBUST":"Robust", "LIMITED":"Limited", "NAU":"Not assessable",
        "SINGLE_IMP":"Single imputation", "MULTI_IMP":"Multiple imputation",
        "INDICATOR":"Missingness indicator", "MODEL_NATIVE":"Model-native handling",
        "NONE":"No class rebalancing", "WEIGHT":"Class weighting", "SMOTE":"SMOTE-family method",
        "RANDOM":"Random over/under-sampling", "OTHER":"Other prespecified method",
    }
    reader_labels_by_field = {
        "K_final_model_specification": "COMPLETE=Complete/fully specified; PARTIAL=Partly specified; INSUFFICIENT=Insufficiently specified; UNCLEAR=Conflicting or insufficient evidence; NA=Not applicable",
        "F_candidate_set_completeness": "R2=Fully recoverable; R1=Partly recoverable; R0=Not recoverable",
        "E_definition_reproducibility": "R2=Fully recoverable; R1=Partly recoverable; R0=Not recoverable",
        "H_metrics_reported": "R2=R-squared; LOGLOSS=Log loss; other codes use standard metric names",
        "B_scientific_purposes": "HEALTH_STATE_OR_HEALTH_VALUE_ESTIMATION=Health-state classification or health-value estimation; VARIABLE_RELEVANCE_OR_MODEL_INTERPRETATION=Variable relevance or model interpretation; POPULATION_ASSOCIATION_ANALYSIS=Population-level association analysis; HEALTH_PATTERN_OR_SUBGROUP_DISCOVERY=Health-pattern or subgroup discovery; CAUSAL_EFFECT_OR_STRUCTURE_ESTIMATION=Causal-effect or causal-structure estimation; OTHER=Other scientific purpose (retain description)",
        "B_analytic_outputs": "MODEL_PERFORMANCE=Model-performance estimate; VARIABLE_CONTRIBUTION_OR_RANK=Variable contribution or ranking; ASSOCIATION_ESTIMATE=Association estimate, irrespective of purpose; REDUCED_PREDICTOR_SET=Reduced predictor set; CAUSAL_EFFECT_ESTIMATE=Causal-effect estimate; IMPLEMENTED_TOOL=Implemented tool or interface; CLUSTER_OR_PATTERN_RESULT=Cluster or pattern result; OTHER=Other analytic output (retain description)",
        "B_proposed_uses": "SCREENING=Screening; DIAGNOSTIC_SUPPORT=Diagnostic support; PERSONALISED_MANAGEMENT=Personalised management; RISK_GROUP_IDENTIFICATION=Risk-group identification; POPULATION_SURVEILLANCE_OR_POLICY=Population surveillance or policy; RESEARCH_OR_HYPOTHESIS_GENERATION=Research or hypothesis generation; OTHER=Other proposed use (retain description); NO_SPECIFIC_USE=Derived only after completed review finds no positive use; not an input code",
        "A_study_id": "Required, non-empty identifier unique among the " + str(N_ALL) + " included studies; NR and NA are not permitted",
        "F_missing_data_method": "NONE=No missing values/handling unnecessary; COMPLETE=Complete-case/listwise deletion; SINGLE_IMP=Single imputation; MULTI_IMP=Multiple imputation; MULTIPLE=Multiple methods; INDICATOR=Missingness indicator; MODEL_NATIVE=Model-native missing handling; OTHER=Other method (describe); NR=Not reported; NA=Not applicable",
        "F_class_rebalancing": "NONE=No intervention stated after review; WEIGHT=Class weighting/cost-sensitive method; SMOTE=SMOTE/ADASYN; RANDOM=Random over/undersampling; ALGO=Algorithm-specific method; MULTIPLE=Multiple strategies; OTHER=Other strategy (describe); NR=Strategy not reported; NA=Not a classification study",
    }
    def reader_labels(allowed):
        if allowed.startswith(("{", "[")):
            return "Structured records; fields and values are defined in S7/DATA_DICTIONARY"
        if allowed.startswith(("Numeric", "Integer", "UTF-8", "Stable")):
            return allowed
        codes = [x.strip() for x in allowed.split("|") if x.strip() and "<" not in x and "..." not in x]
        return "; ".join(f"{code}={code_labels.get(code, code.replace('_',' ').title())}" for code in codes)
    output = []
    for col, header in enumerate(headers):
        block = header[0]
        raw_name = header[2:]
        english_name = raw_name.replace("_", " ").replace("PSUs", "PSUs").replace("PROBAST", "PROBAST+AI")
        lower = raw_name.lower()
        if header.startswith("K_REP"):
            index = int(header[-2:]) - 1
            definition = f"Reporting completeness for: {rep_defs[index]}."
            if header in {"K_REP06", "K_REP07"}:
                definition += " Single study-level judgement; not interchangeable with outcome/model recoverability (OUT16/PRD13). OUT16 also requires source and timing."
            data_type, allowed = "Controlled categorical", "R | P | NR | UNCLEAR | NA"
        else:
            definition = (definitions.get(header) if header in {"H_threshold_reported", "H_threshold_selection_method", "H_evaluation_sample_size", "H_evaluation_prevalence_identifiable"} else READER_DEFINITIONS.get(header)) or definitions.get(
                header,
                definition_templates[block].format(name=english_name.lower())
            )
            if header in explicit_schema:
                data_type, allowed = explicit_schema[header]
            elif header in flag_fields:
                data_type, allowed = "Boolean flag", "Y | N"
            elif header in integer_fields:
                data_type = "Pipe-delimited non-negative integer(s)" if header in multi_integer_fields else "Non-negative integer"
                allowed = "Integer(s) >= 0"
            elif header in proportion_fields:
                data_type = "Pipe-delimited numeric proportion(s)" if header in multi_proportion_fields else "Numeric proportion"
                allowed = "Numeric value(s) in [0,1]"
            elif header in bounded_metric_fields:
                data_type, allowed = "Numeric performance metric", "Numeric value in [0,1]"
            elif header in model_text_fields:
                data_type, allowed = "Model label", "UTF-8 author/model label"
            elif header in evaluation_id_fields:
                data_type, allowed = "Evaluation identifier", "Stable evaluation-unit identifier"
            elif header in binary_fields:
                data_type, allowed = "Controlled categorical", "Y | N"
            elif header in report_status_fields:
                data_type, allowed = "Controlled categorical", "R | NR"
            elif any(token.lower() in header.lower() for token in identifier_tokens):
                data_type, allowed = "Identifier", "Stable identifier or bibliographic identifier | NR | NA"
            elif any(token in lower for token in multi_select_tokens):
                data_type = "Controlled multi-select"
                allowed = "Protocol-defined atomic codes for this field; | separates selections"
            elif block in {"B", "C", "E", "F", "G", "H", "I", "J", "K", "L", "M"}:
                data_type, allowed = "Controlled categorical or structured text", "Protocol-defined atomic code or UTF-8 text, as specified by the operational definition"
            else:
                data_type, allowed = "Free text", "UTF-8 text"
        is_multi = data_type == "Controlled multi-select"
        missing = "See common missing-code note"
        if block == "A" and header not in {"A_report_type", "A_retraction_status"}:
            missing = "See common missing-code note (NR/NA only for bibliographic fields)"
        applicability = applicability_by_block[block]
        if header == "F_class_rebalancing":
            applicability = "Classification studies only; NA for nonclassification studies"
        if header == "A_study_id":
            missing = "No missing value permitted; required and unique"
        if header in {"B_scientific_purposes", "B_scientific_purpose_records", "B_health_topic",
                    "B_analytic_outputs", "B_analytic_output_records", "B_proposed_uses",
                    "B_proposed_use_records"}:
            applicability = "Final health-focused studies; NA otherwise"
        elif header in {"B_method_contribution", "B_method_contribution_detailed", "B_method_target_stages_display",
                        "B_method_target_stages_detailed", "B_method_evaluation_design", "B_method_comparators",
                        "B_method_evaluation_datasets", "B_method_primary_evaluation_criteria"}:
            applicability = "Final method-focused studies; NA otherwise"
        elif header == "I_importance_stability":
            applicability = "Studies reporting explicit model-based variable importance output"
        elif header in {"M_association_estimate_linked", "M_survey_weights_linked_to_association", "M_design_uncertainty_linked_to_association"}:
            applicability = "Final health-focused studies with POPULATION_ASSOCIATION_ANALYSIS; NA otherwise"
        elif header == "M_importance_stability_support_criteria_met":
            applicability = "Studies reporting explicit model-based variable importance; NA otherwise"
        elif header == "M_population_association_support_criteria_met":
            applicability = "Final health-focused studies with POPULATION_ASSOCIATION_ANALYSIS; NA otherwise"
        elif header == "M_individual_application_support_criteria_met":
            applicability = "Final health-focused studies proposing screening or individual application; NA otherwise"
        elif header == "M_surveillance_policy_support_criteria_met":
            applicability = "Final health-focused studies proposing POPULATION_SURVEILLANCE_OR_POLICY; NA otherwise"
        evidence_rule = evidence_by_block[block]
        if header == "B_primary_orientation":
            evidence_rule = "Preserve the reviewed four-state value; do not collapse it during review."
        elif header == "B_display_orientation_group":
            evidence_rule = "Derive by the locked publication rule from B_primary_orientation; never enter as an independent judgement."
        elif header == "M_association_estimate_linked":
            evidence_rule = "Require an analysis-level effect-size or association-estimate anchor; study-level co-occurrence is insufficient."
        elif header == "M_survey_weights_linked_to_association":
            evidence_rule = "Require analysis-level linkage; a generic weights statement elsewhere in the study is insufficient."
        elif header == "M_design_uncertainty_linked_to_association":
            evidence_rule = "Require analysis-level linkage to the reported association estimate."
        elif header == "M_importance_stability_support_criteria_met":
            evidence_rule = "Use the explicit model-based importance-output denominator and the locked importance-stability assessment from the same study."
        elif header == "M_population_association_support_criteria_met":
            evidence_rule = "Require an association estimate, survey weights, and design-based uncertainty to be linked to the same population-association analysis."
        elif header == "H_threshold_reported":
            evidence_rule = "Order-invariant THR01 existence: positive > unclear > NR > wholly NA. Figure 9 independence additionally joins THR03=USED to a positive THR01 by actual evaluation ID and compatible model/outcome/dataset links; denominator is threshold-reporting studies. Original-prevalence retention requires IMB04=ORIGINAL, not ALTERED. Detailed mixed records remain in ITEM_RESPONSES."
        elif header == "M_individual_application_support_criteria_met":
            evidence_rule = "Within eligible screening/individual-use studies, independently check validation, calibration and positive threshold-reporting codes across study records; no model/outcome/evaluation join."
        elif header == "M_surveillance_policy_support_criteria_met":
            evidence_rule = "Within the surveillance/policy denominator, require survey weights plus strata, clusters/PSUs or design-based uncertainty somewhere in the same study; no analysis-level join."
        source_ids = protocol_ids_for_public_field(header)
        canonical_detail_fields = {"B_scientific_purpose_records", "B_analytic_output_records",
                                   "B_proposed_use_records", "B_method_contribution_detailed",
                                   "B_method_target_stages_detailed"}
        derived_fields = {"B_included_all", "B_health_focused", "B_method_focused",
                          "B_core_health_classification", "B_other_health_analysis",
                          "B_scientific_purposes", "B_analytic_outputs", "B_proposed_uses",
                          "B_method_contribution", "B_method_target_stages_display"}
        if header in canonical_detail_fields:
            derivation = "Authoritative detailed record; direct/normalised from final consensus."
        elif header in derived_fields or any(token in header for token in ("display_", "support_criteria", "summary")):
            derivation = "Derived display/denominator field; never entered independently."
        else:
            derivation = "Direct/normalised field; see common provenance note."
        if header == "H_threshold_reported":
            derivation = "Derived from THR01: any positive method > unclear/missing > NR (N) > wholly NA. Same-evaluation THR03=USED establishes Figure 9 independence among threshold-reporting studies."
        output.append([header, DOMAIN_NAMES[block], definition, analysis_unit_for_field(header), applicability,
                       data_type, allowed, reader_labels_by_field.get(header, reader_labels(allowed)), missing,
                       "Yes" if is_multi else "No", evidence_rule, source_ids, derivation,
                       figure_table_for_field(header)])
    return output


def build_search_table_s3():
    # S3: exact search strategies and yields in the same table.
    oa = load_json("results/raw/openalex_20260905.json")
    epmc = load_json("results/raw/epmc_20260903.json")
    pubmed = load_json("results/raw/pubmed_20260903.json")
    kci = load_json("results/raw/kci_20260905/census.json")
    kci_strategy = (
        "Korean-script terms are reproduced exactly as executed; bracketed English text is a reader gloss, not a substituted query. "
        "Dataset: 국민건강영양조사 | 국민건강 영양조사 | 국민건강·영양조사 [Korean spacing/punctuation variants for KNHANES] | "
        "국건영 [Korean abbreviation] | KNHANES | National Health and Nutrition Examination Survey | KNHNAES [misspelling searched intentionally]. "
        "Methods: 머신러닝 | 기계학습 | 기계 학습 | 머신 러닝 [machine learning]; 딥러닝 | 딥 러닝 [deep learning]; "
        "데이터마이닝 [data mining]; 신경망 | 인공 신경망 [neural network]; 인공지능 [artificial intelligence]; "
        "랜덤 포레스트 [random forest]; 부스팅 [boosting]; 서포트 벡터 [support vector]; 의사결정나무 | 의사결정트리 [decision tree]; "
        "군집 [clustering]; 잠재계층 [latent class]; 잠재프로파일 [latent profile]; 다층 퍼셉트론 [multilayer perceptron]; "
        "연관규칙 [association rule]; plus the English terms and abbreviations of the other sources."
    )
    search_rows = [
        ["Europe PMC", "2026-09-03; Europe PMC REST API, https://www.ebi.ac.uk/europepmc/webservices/rest/search; title/abstract plus full record/full text", f"Layer A: {epmc['layers']['A']['query']} Layer B: {epmc['layers']['B']['query']}", "No date or publication-type limits", "6,046 database/index records after within-source union", "5,327 and 1,291 layer hits; one duplicated row removed before union."],
        ["PubMed", "2026-09-03; NCBI E-utilities, https://eutils.ncbi.nlm.nih.gov/entrez/eutils; title/abstract and MeSH", pubmed["term"], "No date or publication-type limits", f"{pubmed['n_missing_from_epmc']} records not already in Europe PMC entered the database/index set", f"{pubmed['hits']:,} retrieved; contribution is cross-source unique."],
        ["OpenAlex", "2026-09-05; Works API, https://api.openalex.org/works; title_and_abstract.search", 'Separate phrase queries: "KNHANES"; "Korea National Health and Nutrition Examination Survey". Union by OpenAlex work ID.', "No year or work-type limits", f"{FLOW['sources']['openalex_unique']:,} records entering deduplication", f"Query hits {oa['queries'][0]['hits']:,} and {oa['queries'][1]['hits']:,}; all pages retrieved by cursor pagination until no cursor remained; the 10,000-ID union is not a paging limit. Two same-DOI duplicate pairs were removed."],
        ["Korean Citation Index", "2026-09-05; KCI KEYALL web interface, https://www.kci.go.kr/kciportal/po/search/poArtiSearList.kci", kci_strategy, "No year or language limits", f"{kci['n_unique']:,} database/index records", f"{kci['query_count']} exact combinations; all pages retrieved; no failed query."],
        ["KDCA publication list", "2026-09-03; KNHANES publication-list endpoint, https://knhanes.kdca.go.kr/knhanes/thss/thssInfLst.do", "Complete author-registered publication list; no keyword query.", "No keyword or year restriction", "2,079 other-source records", "Shown as the other-source box in Figure 1."],
        ["Backward/forward citation searching", "2026-09-04; Europe PMC citations API and Semantic Scholar Graph API", "Backward and forward links for 40 highly cited eligible seed reports.", "Forty prespecified seeds; citation candidates underwent the same eligibility rules", "No additional source count added to Figure 1", "3,482 unrelated, 381 already retrieved, 14 ML-ineligible, and 8 candidates; four candidates were already in the final corpus and the remainder were ineligible or not recoverable as eligible analyses."],
    ]
    emit_fixed_table(3, "Search_strategies_and_yields", "Search strategies, retrieval counts, and unique contributions",
                     ["Source", "Search date and interface", "Exact search strategy", "Limits", "Retrieval and PRISMA contribution", "Deduplication/source note"],
                     search_rows + [["Total", "", "", "", "18,514 records: 16,435 database/index (6,046 + 52 + 9,998 + 339) and 2,079 KDCA",
                                     "7,438 duplicates removed; 11,076 records screened"]], [24, 34, 104, 29, 48, 52],
                     "KCI, Korean Citation Index; KDCA, Korea Disease Control and Prevention Agency.", 7.5)


    # Append a numbered S3 panel, without rebuilding unrelated tables or workbooks.
    f = FLOW["flow"]
    p = FLOW["terminology_screen"]["partition"]
    r_ = f["report_exclusion_reasons"]  # prompt 106
    scope_rows = [
        ["Records screened", f"{f['unique_records_screened']:,}", "Deduplicated bibliographic records, not full texts."],
        ["Not advanced: no ML or prediction term", f"{p['no_dictionary_signal']:,}", "No ML, ML-adjacent or prediction term in title, abstract or keywords; one rule for every source, including the Korean Citation Index; full-text layer kept"],
        ["Candidates with eligibility decisions", f"{f['records_assessed_against_eligibility']:,}", "Decided on the available title, abstract or full text; not a count of full texts"],
        ["Candidate exclusions", f"{f['reports_excluded_total']:,}", f"{f['ineligible_reports']:,} ineligible (no supervised non-regression learner {r_['no_eligible_machine_learning']}; not KNHANES {r_['not_knhanes']}; review or non-primary {r_['review_or_non_primary_synthesis']}; no eligible analysis {r_['no_eligible_knhanes_analysis']}; abbreviation false positive {r_['abbreviation_false_positive']}; other or unassessable {r_['other_or_unassessable']}) and {r_['ml_adjacent_catalogued_separately']} using only regression-family or unsupervised methods."],
        ["Reports and studies included", f"{f['eligible_reports_entering_family_linkage']} reports; {f['unique_full_report_studies_included']} studies", f"{f['additional_or_companion_reports_linked']} related reports linked to their studies"],
        ["Full texts sought, not retrieved and assessed", "not recorded", "Not established by the records; left unfilled in Figure 1"],
        ["Total not advanced", f"{f['terminology_exclusions']:,}", "All without an ML or prediction term under the common dictionary rule"],
    ]
    note = ("\u2020Includes one record (ART003346494; DOI 10.3349/ymj.2025.0195) recorded as an NHANES 2011\u20132014 study, for which "
            "KNHANES use could not be confirmed.")
    stem = "Supplementary_Table_S03_Search_strategies_and_yields"
    path = TEX / (stem + ".tex")
    panel = fixed_width_table_tex("Supplementary Table S3 (continued). Screening dispositions",
                                 ["Stage", "Count", "Meaning and limits"], scope_rows,
                                 [52, 30, 199], note, 8.0)
    body = re.search(r"\\begin\{document\}(.*?)\\end\{document\}", panel, re.S).group(1)
    source = path.read_text()
    path.write_text(source.replace(r"\end{document}", "\n" + r"\clearpage" + "\n" + body + "\n" + r"\end{document}"))
    book_path = TABLES / (stem + ".xlsx")
    book = load_workbook(book_path)
    _add_sheet(book, "Screening and retrieval", ["Stage", "Count", "Meaning and limits"], scope_rows)
    _add_sheet(book, "Screening sources", ["Source and interpretation"], [["Counts describe recorded decisions, not a complete full-text retrieval flow."]])
    book.save(book_path)
    compile_tex(path)


# Prompt 090: the main text keeps eight claim-ordered figures. The earlier workflow
# figures move here unchanged, numbered in the order the main text cites them.
MOVED_FIGURES = [
    (1, "fig2_landscape", "Use_of_KNHANES", "Publication growth and use of KNHANES",
     "All 220 studies. (A) Annual publications by health- versus method-focused orientation; 2026 covers publications through September. "
     "(B) Role of KNHANES in the study. (C) Survey-year or cycle scope. (D) KNHANES components used; laboratory and oral examinations are nested "
     "under examination and components may overlap. The 165 studies using KNHANES as the primary analysis dataset are a different set from the "
     "165-study core classification cohort."),
    (2, "fig3_data_use", "Purposes_outputs_and_uses", "Purposes, outputs, and proposed uses in health-focused studies",
     "All panels use the 184 health-focused studies; categories overlap. (A) Scientific purposes stated in the objective, principal analysis, "
     "results, or conclusion. (B) Analytic outputs actually produced. (C) Uses proposed by the authors; no specific use was coded only when no "
     "listed use was identified. (D) Study-level purpose and output co-reporting; co-reporting does not show that purpose and output belong to "
     "the same analysis."),
    (3, "fig4_populations", "Topics_participants_and_sample_size", "Health topics, participant selection, and sample size",
     "All panels use the 184 health-focused studies. (A) The eight most frequent health topics plus the remaining categories, using the "
     "outcome-centred mapping of Supplementary Figure S12. (B) Participant-selection conditions; conditions may overlap. (C) Reported final "
     "sample sizes on a logarithmic scale (median 7,143; interquartile range 3,187--15,900); three studies did not report the sample size. "
     "(D) Information available to follow participant selection and exclusions."),
    (4, "fig6_classification_outcomes", "Outcome_construction", "Outcome construction in the core classification cohort",
     "The 165 core studies. (A) Temporal position of the outcome. (B) Binary, multiple-binary, multiclass, or mixed structure. "
     "(C) Outcome-ascertainment source. (D) How completely the outcome definition was specified for reproduction, graded by the least "
     "reproducible outcome in each study."),
    (5, "fig7_predictor_training", "Predictor_construction_and_dataset_preparation", "Predictor construction and dataset preparation",
     "The 165 core studies. (A) The 61 studies reporting an initial candidate or input-variable count, on a logarithmic scale; counts were not "
     "inferred from listed variables. (B) Reproducibility of the candidate and final predictor sets, graded by the least reproducible model. "
     "(C) Missing-data strategies. (D) Timing of data-dependent steps; before split includes steps reported as performed outside the training "
     "data, and grey combines not applied and not applicable."),
    (6, "fig8_model_development", "Algorithms_tuning_and_model_selection", "Algorithms, tuning, and model selection",
     "The 165 core studies. (A) Algorithm families evaluated; families overlap. (B) Hyperparameter-tuning methods. (C) Separation of tuning and "
     "model selection from the final evaluation. (D) Families designated by the authors as final or best-performing models; these arise from "
     "heterogeneous outcomes, metrics, and evaluation datasets and do not rank algorithms. The grey bar shows the 13 studies without a "
     "recoverable designation."),
    (7, "fig9_validation_evaluation", "Validation_and_performance_measures", "Validation and performance measures",
     "The 165 core studies. (A) Internal evaluation methods; categories overlap, and none or not reported cannot distinguish nonuse from absent "
     "reporting. (B) Evaluation beyond the development sample in a later KNHANES period, an external dataset, both, or neither. "
     "(C) Reporting of evaluation-set composition and the decision threshold; 18 of the 41 studies reporting a threshold chose it without using "
     "the final evaluation data, for at least one evaluation. (D) Selected performance measures."),
    (8, "fig10_variable_interpretation", "Variable_importance_stability_and_downstream_use", "Variable importance, stability, and downstream use",
     "(A) Studies reporting a model-based variable-importance analysis among the 165 core studies. (B) Importance methods among the 129 studies "
     "reporting importance; methods overlap. (C) Stability checking (25/129), importance-guided reduced predictor sets (24/165), subsequent "
     "statistical analysis (12/165), and exact carryover of the selected variables (5/12); these are overlapping uses, not a sequence."),
    (9, "fig5_nonclassification", "Method_focused_studies", "Method-focused studies",
     "All panels use the " + str(N_METHOD) + " method-focused studies. (A) Type of methodological contribution. (B) Analytic stages addressed; stages overlap. "
     "(C) Role of KNHANES. (D) How the method itself was evaluated."),
    (10, "fig11_methodological_appraisal", "Reporting_survey_design_and_PROBAST_AI", "Reporting completeness, survey-design handling, and PROBAST+AI",
     "The 165 core studies. (A) Eight selected TRIPOD+AI-derived reporting items; all 19 are in Supplementary Table S7. (B) Survey-design handling "
     "at each analysis stage. (C) Studies making each claim (open circles) and those reporting the required evidence (filled circles); the "
     "study-level synthesis is Figure 8 of the main text; the final model was fully specified in 11 of 165 studies and 17 provided a link to analysis code. (D) PROBAST+AI overall judgements for 259 development models and 346 evaluations; the "
     "analysis domain drove the ratings."),
    (11, "fig12_temporal_changes", "Differences_by_publication_period", "Differences by publication period",
     "Core studies by publication period (32, 32, 52, and 49 studies; 2025--2026 is incomplete through September 2026). (A) Algorithm comparison, "
     "model-based importance, SHAP, and stability checking. (B) Algorithm families. (C) Later-period or external validation, calibration, and "
     "paired comparison. (D) Predictor-set reproducibility, separation of tuning, final-model specification, code availability, and any mention "
     "of survey weights. Thin lines connect observations across the ordered publication periods as visual guides only; they do not represent fitted trends."),
]


def build_moved_figures():
    source_dir = ROOT / "figures" / "submission"
    for number, stem, slug, title, caption in MOVED_FIGURES:
        name = f"Supplementary_Figure_S{number:02d}_{slug}"
        target = FIGURES / f"{name}.pdf"
        shutil.copy2(source_dir / f"{stem}.pdf", target)
        tex = TEX / f"{name}.tex"
        rel = target.relative_to(ROOT)
        tex.write_text(document_tex(f"Supplementary Figure S{number}. {title}",
                                    rf"\begin{{center}}\includegraphics[width=0.96\textwidth,height=0.78\textheight,keepaspectratio]{{{rel}}}\end{{center}}"
                                    + tex_escape(caption)), encoding="utf-8")
        compile_tex(tex)
        MANIFEST.append([f"Supplementary Figure S{number}", title, "standalone TeX; PDF", "figure", str(target.relative_to(ROOT))])


def _year_ranges(value):
    """Collapse "2009 | 2010 | 2011 | 2015" into "2009-2011, 2015" with an en dash (prompt 093, Table S6); other text is kept as is."""
    parts = [p.strip() for p in str(value).split("|")]
    if not parts or not all(re.fullmatch(r"(19|20)\d\d", p) for p in parts):
        return value
    years = sorted({int(p) for p in parts})
    runs, start, prev = [], years[0], years[0]
    for y in years[1:] + [None]:
        if y is not None and y == prev + 1:
            prev = y
            continue
        runs.append(str(start) if start == prev else f"{start}\u2013{prev}")
        if y is not None:
            start = prev = y
    return ", ".join(runs)


def _method_label(code):
    """Readable importance-method label with acronyms kept upper case (prompt 093, Table S6)."""
    text = str(code).strip().replace("_", " ").lower()
    return re.sub(r"\b(shap|pdp|ale|lime|ice)\b", lambda m: m.group(1).upper(), text)


def build_supplementary_figures():
    """Prompt 093: eight supplementary figures in the main-text style (tools/make_supplementary_figures.py).

    Panels already drawn in a main figure are not repeated; captions are plain and carry no item codes.
    """
    import make_supplementary_figures as sf
    sf.OUT = FIGURES
    sf.main()
    reporting = sf.reporting_summary(sf.CORE)
    thr = len(reporting["members"]["threshold_reported"]); ind = len(reporting["members"]["threshold_independent"])
    _pin((thr, ind), (41, 18), "build_standalone_supplements.py:2672")  # prompt 106 pin
    # Review 2026-10-24 (JCE): captions shortened to journal length; definitions needed to read a panel are kept.
    captions = [
        (2, "Study_characteristics", "Role of KNHANES and survey years analysed",
         "(A) Role of KNHANES in the " + str(N_ALL) + " studies; hatched, unclear. (B) Survey years analysed by the " + str(N_CORE)
         + " core studies; a study counts once for each year. " + str(_PT["core_survey_years"]["not_reported"]) + " studies did not name their years."),
        (4, "Participants_and_sample_size", "Participants and sample size",
         str(N_CORE) + " core studies. (A) Participant restrictions, which overlap. (B) Participant-selection items reported; the last row requires all five."),
        (5, "Differences_by_publication_period", "Differences by publication period",
         "Core studies by publication period (n = " + ", ".join(map(str, PERIOD_N[:3])) + " and " + str(PERIOD_N[3]) + "). (A) Algorithms compared "
         "and families fitted; teal, boosting. (B) Paired model comparison. (C) Studies producing a ranking in the first and last period, "
         "in the four largest topics. Lines are visual guides, not fitted trends."),
        (3, "Outcome_and_predictor_construction", "Outcome and predictor construction",
         str(N_CORE) + " core studies. (A) Outcome structure. (B) Outcome, predictor set and tuning separation fully rebuildable from the report."),
        (6, "Algorithms_tuning_evaluation_and_measures", "Algorithms, tuning, evaluation designs and performance measures",
         str(N_CORE) + " core studies; categories overlap except in (B). (A) Algorithm families. (B) Hyperparameter tuning. (C) Evaluation "
         "designs; teal, beyond the development data. (D) Performance measures. (E) Importance methods in the " + str(N_RANK)
         + " studies with a ranking; teal, SHAP."),
        (1, "Methods_testbed", "KNHANES as a methods testbed",
         "(A) Contribution of the " + str(N_METHOD) + " method-focused studies; teal, compared with existing methods. (B) Analysis stages "
         "addressed, which overlap. (C) How the method was evaluated; teal, beyond a single KNHANES application. One of ten "
         "comparisons of existing methods reported uncertainty or a paired comparison."),
        (7, "Agreement_between_rankings", "Agreement between pairs of rankings",
         "(A) Overlap of the variable domains named by pairs of the " + str(N_RANK) + " studies with a ranking (Jaccard index; median and "
         "interquartile range; open points exclude age, sex and body size). Pairs share studies and are not independent. (B) Rows of "
         "Figure 5A clustered by their variable profiles (average linkage)."),
        (8, "Reporting_completeness_and_PROBAST_AI", "Reporting completeness and PROBAST+AI",
         str(N_CORE) + " core studies. (A) Eight of the 19 TRIPOD+AI-derived reporting elements. (B) PROBAST+AI judgements per model unit ("
         + str(PD_N) + " developments, " + str(PE_N) + " evaluations); dark grey, low quality or high risk."),
    ]
    for number, slug, title, caption in captions:
        name = f"Supplementary_Figure_S{number:02d}_{slug}"
        target = FIGURES / f"{name}.pdf"
        assert target.exists(), target
        for extra in FIGURES.glob(f"{name}.png"):
            extra.unlink()
        tex = TEX / f"{name}.tex"
        rel = target.relative_to(ROOT)
        tex.write_text(document_tex(f"Supplementary Figure S{number}. {title}",
                                    rf"\begin{{center}}\includegraphics[width=0.96\textwidth,height=0.80\textheight,keepaspectratio]{{{rel}}}\end{{center}}"
                                    + tex_escape(caption)), encoding="utf-8")
        compile_tex(tex)
        MANIFEST.append([f"Supplementary Figure S{number}", title, "standalone TeX; PDF", "figure", str(target.relative_to(ROOT))])


def _recheck_row():
    """Supplementary Table S7 row for the Additional Data 1 re-check (additional_file_review/, 2026-10-23/24): rounds,
    issues and the corrections written back, counted from the review files."""
    d = ROOT / "additional_file_review"
    if not (d / "ISSUES.tsv").exists():
        return []
    tsv = lambda f: list(csv.DictReader(open(d / f, encoding="utf-8"), delimiter="\t"))
    issues = tsv("ISSUES.tsv"); rec = tsv("RECORD_CORRECTIONS.tsv"); ovr = tsv("OVERRIDES.tsv")
    rounds = len(list(d.glob("rev[0-9][0-9]_*")))
    author = sum(r["status"] == "needs-author" for r in issues)
    return [["Re-check of Additional Data 1 before submission",
             f"Two AI reviewers read every cell against the full texts in {rounds} rounds; disagreements were settled against the source, "
             f"and {author} questions were decided by the author",
             "every row and column", f"{len(issues):,} issues raised",
             f"{len(rec)} corrections to {len({r['study_id'] for r in rec})} study records and, separately, {len(ovr)} free-text cells revised"]]


def build_final_supplement_tables():
    """Build the final eight-table, one-figure reader-facing supplement."""
    master_path, master_headers, master_rows = make_master_backdata()

    # The independent-human form is generated separately by
    # tools/prepare_protocol_v1_4_verification.py.  It must never import the
    # current S7/P1 values or mix reviewer and consensus cells in one workbook.

    # Repository-release staging: material requested for auditability is emitted
    # now, while the manuscript still correctly withholds a public URL/DOI until
    # an external deposit has actually occurred.
    release_dir = ROOT / "data" / "repository_release"
    release_dir.mkdir(parents=True, exist_ok=True)
    def write_release_tsv(name, header, records):
        path = release_dir / name
        with path.open("w", encoding="utf-8", newline="") as handle:
            writer = csv.writer(handle, delimiter="\t")
            writer.writerow(header); writer.writerows(records)
        return path
    dev_records, eval_records, metric_records = [], [], []
    for doc in sorted(INCLUDED, key=lambda item: item["study_id"]):
        sid = doc["study_id"]
        study_class = doc.get("adjudication", {}).get("study_category_and_dataset_use", PURPOSE_BY_ID.get(sid, {}))
        analytic_task = study_class.get("knhanes_actual_ml_task", item_value(doc, "TSK01"))
        prediction_appraisal = analytic_task in {"CLASSIFICATION", "CONTINUOUS_OR_ORDERED_ESTIMATION"}
        for unit_type, units, prefix, target in (
            ("development", doc.get("units", {}).get("developments", []), "PD", dev_records),
            ("evaluation", doc.get("units", {}).get("evaluations", []), "PE", eval_records),
        ):
            if not prediction_appraisal:
                continue
            for unit in units:
                uid = unit.get(f"{unit_type}_id", "NR")
                values = []
                for item in [f"{prefix}_D{i}" for i in range(1, 5)] + [f"{prefix}_OVERALL"]:
                    vals = [entry.get("value") for entry in value_rows(doc, item) if entry.get("unit_id") == uid]
                    values.append(master_cell(vals) if vals else "NR")
                target.append([sid, uid, unit.get("model_id", "NR"), unit.get("outcome_id", "NR"),
                               unit.get("dataset_id", "NR"), unit.get("label", "NA"), *values])
        for metric in doc.get("performance_metrics", []):
            metric_records.append([sid, metric.get("metric_id", "NR"), metric.get("evaluation_id", "NR"),
                                   metric.get("model_id", "NR"), metric.get("outcome_id", "NR"),
                                   metric.get("metric", "NR"), metric.get("estimate", "NR"),
                                   metric.get("lower", "NR"), metric.get("upper", "NR"),
                                   metric.get("threshold", "NR"), metric.get("author_designated_best", "NR")])
    unit_header = ["study_id", "unit_id", "model_id", "outcome_id", "dataset_id", "unit_label",
                   "domain_1", "domain_2", "domain_3", "domain_4", "overall"]
    dev_path = write_release_tsv("PROBAST_AI_development_units.tsv", unit_header, dev_records)
    eval_path = write_release_tsv("PROBAST_AI_evaluation_units.tsv", unit_header, eval_records)
    metric_path = write_release_tsv("performance_metrics_long.tsv",
        ["study_id", "metric_id", "evaluation_id", "model_id", "outcome_id", "metric", "estimate",
         "lower", "upper", "threshold", "author_designated_best"], metric_records)
    release_rows = [
        ["Master study-level dataset", str(master_path.relative_to(ROOT)), f"{N_ALL} studies x {len(master_headers)} fields"],
        ["PROBAST+AI development-unit long data", str(dev_path.relative_to(ROOT)), f"{len(dev_records)} units"],
        ["PROBAST+AI evaluation-unit long data", str(eval_path.relative_to(ROOT)), f"{len(eval_records)} units"],
        ["Performance-metric long data", str(metric_path.relative_to(ROOT)), f"{len(metric_records)} records"],
        ["Search and study-family ledger", "data/INTEGRATED_STUDY_AUDIT.tsv", "screening, linkage, and study-level audit"],
        ["Evidence ledger", "data/EVIDENCE_LEDGER.tsv", "source-linked evidence records"],
        ["Figure generation code", "tools/make_figures.py; tools/make_main_figures.py; tools/make_supplementary_figures.py", "Figures 1--5 and Supplementary Figures S1--S8"],
        ["Supplement generation code", "tools/build_standalone_supplements.py", "Supplementary Tables S1--S8 and Figures S1--S8"],
        ["Protocol and amendment sources", "data/protocol_v1_2; data/protocol_v1_3", "final records and purpose/evidence addendum"],
        ["Extraction and reconciliation documentation", "data/protocol_v1_2; prompts/processed", "fixed schema, consistency-check and reconciliation records"],
    ]
    write_release_tsv("RELEASE_MANIFEST.tsv", ["Component", "Project-relative path", "Scope"], release_rows)

    # S1: completed PRISMA checklist. Locations follow the JCE manuscript (paper/src/jce_main.tex, numbered sections;
    # 2026-10-24); the BMC wording is in paper_backup/BMC_MRM_20261024/.
    prisma_source = (ROOT / "project_archive/paper_cleanup_20260918_002038/internal/supplement_sources/appendix1_prisma_checklist.md").read_text()
    locations = {
        # v16 (2026-10-28): section numbers follow the JCE manuscript (2.1 protocol, 2.2 search and selection, 2.3 coding,
        # 2.4 verification, 2.5 synthesis; 3.1-3.6 results, 3.5 framework appraisal, 3.6 checklist; 4.1-4.4 discussion).
        "1": "Title", "2": "Abstract", "3": "Section 1 (Introduction)", "4": "Section 1, final paragraph",
        "5": "Section 2.2", "6": "Section 2.2; Supplementary Table S3",
        "7": "Supplementary Table S3", "8": "Sections 2.2 and 2.4; Supplementary Tables S4 and S6", "9": "Sections 2.3 and 2.4; Supplementary Table S6",
        "10a": "Section 2.3; Additional Data 1", "10b": "Section 2.3; Supplementary Table S6",
        "11": "Section 2.3; Supplementary Table S6", "12": "Not applicable; no pooled effect measure",
        "13a": "Section 2.5", "13b": "Section 2.3", "13c": "Section 2.5",
        "13d": "Section 2.5; no meta-analysis", "13e": "Section 2.5", "13f": "Section 2.5; practices recomputed without the core studies added under the final eligibility criterion",
        "14": "Not applicable; no pooled estimates", "15": "Not applicable; descriptive meta-research synthesis",
        "16a": "Section 3.1; Figure 1", "16b": "Section 3.1; Supplementary Table S4",
        "17": "Additional Data 1; Supplementary Table S8 (ten illustrative studies)", "18": "Section 3.5; Supplementary Figure S8; Additional Data 1",
        "19": "Sections 3.3--3.6; Supplementary Figures S2 and S6; Additional Data 1", "20a": "Section 3",
        "20b": "Section 3; Figures 1--5; Table 1; Additional Data 1", "20c": "Sections 3.3, 3.4 and 3.6; Table 1; Supplementary Figure S5",
        "20d": "Section 3.6; sensitivity analysis of the main practices", "21": "Not applicable", "22": "Not applicable",
        "23a": "Section 4.1", "23b": "Section 4.3",
        "23c": "Section 4.3", "23d": "Section 4.4; Table 1; Section 5",
        "24a": "Section 2.1", "24b": "Not publicly deposited; coding rules in Supplementary Table S6; column definitions in Additional Data 1.",
        "24c": "Section 2.1", "25": "Funding", "26": "Declaration of competing interest",
        "27": "Study-level dataset in Additional Data 1; analysis code not yet publicly deposited.",
    }
    prisma_rows = []
    for line in prisma_source.splitlines():
        if not line.startswith("|") or "---" in line or "Section | Item" in line:
            continue
        cells = [cell.strip() for cell in line.strip("|").split("|")]
        if len(cells) == 5:
            prisma_rows.append([cells[0] or " "] + cells[1:4] + [locations.get(cells[1], cells[4])])
    emit_fixed_table(1, "PRISMA_2020_checklist", "Completed PRISMA 2020 checklist",
                     ["Section", "Item", "Checklist item", "Description", "Location"], prisma_rows,
                     [24, 12, 34, 120, 83], font_size=7.2)  # prompt 109: S1 back to two pages

    # Prompt 093: the 306-item instrument is kept in the Table S5 workbook (PROTOCOL_ITEMS and
    # PROTOCOL_RESPONSE_CODES); the PDF carries the reader-facing rule table S7 (build_rules_table_s7).
    build_search_table_s3()

    # S4: actual boundary and study-family decisions.
    adj = load_json("data/protocol_v1_2/ADJUDICATION_SUMMARY.json")
    boundary_rows = []
    decision_labels = {
        "EXCLUDE_NO_ELIGIBLE_ML": "Excluded—no eligible machine-learning model fitted",
        "EXCLUDE_NOT_KNHANES": "Excluded—KNHANES data were not analysed",
        "EXCLUDE_NO_ANALYTIC_RESULTS": "Excluded—no eligible analytic results reported",
        "INCLUDE": "Included",
        "LINK_COMPANION": "Linked as companion report",
        "MERGE_STUDY_FAMILY": "Merged within the same study family",
        # Prompt 095: plain decisions instead of work commands.
        "RETAIN_CORPUS_EXCLUDE_VALID_EVIDENCE": "Included; retracted, so excluded from performance evidence",
        "MERGE_PREPRINT_INTO_KHM100": "Preprint counted with its journal article (KHM100)",
        "REPRESENTATIVE_FOR_KHM076_KHM100": "Journal article representing the preprint-journal pair",
        "INCLUDE_EXTERNAL_VALIDATION": "Included; KNHANES used as the external evaluation dataset",
    }
    for sid, item in sorted(adj.get("decisions", {}).items()):
        raw_decision = item.get("decision", "NR")
        decision = decision_labels.get(raw_decision, str(raw_decision).replace("_", " ").capitalize())
        rationale = item.get("rationale", "NR").replace("DAE_OE_XGB analysis", "the same XGBoost analysis")  # prompt 096
        family = item.get("family_id") or "Not applicable"
        boundary_rows.append([sid, decision, family, rationale])
    # Prompt 093: the 134 ML-adjacent reports are listed in the Table S5 workbook (ML_ADJACENT_REPORTS).
    emit_fixed_table(4, "Eligibility_boundary_and_study_family_decisions", "Eligibility-boundary and study-family decisions",
                     ["Report ID", "Decision", "Study family", "Rationale"], boundary_rows, [24, 52, 24, 180],
                     note="KHM, report identifier used in Additional Data 1.", font_size=8.5)

    # Prompt 093: the reader dictionary is the VARIABLE_DICTIONARY sheet of the Table S5 workbook.
    # S6: reader-facing, task-appropriate synthesis of all 19 health-focused
    # studies outside the core classification cohort.  The task decision was
    # re-read against TSK01--TSK03, the fitted target, evaluation scale, and
    # source evidence; it is not inferred from words such as "prediction" in a title.
    index = {name: i for i, name in enumerate(master_headers)}
    noncore = [row for row in master_rows
               if row[index["B_display_orientation_group"]] == "HEALTH_ANALYSIS"
               and row[index["B_analytic_task"]] != "CLASSIFICATION"]
    _pin(len(noncore), 19, "build_standalone_supplements.py:2876")  # prompt 106 pin
    task_labels = {
        "CONTINUOUS_OR_ORDERED_ESTIMATION": "Continuous/ordered outcome",
        "CAUSAL_OR_HETEROGENEOUS_EFFECT_ESTIMATION": "Causal-effect estimation",
        "CLUSTER_DISCOVERY": "Cluster discovery",
        "PATTERN_OR_REPRESENTATION_DISCOVERY": "Pattern/representation discovery",
        "OTHER_ML_ANALYSIS": "Other structured ML analysis",
    }
    output_labels = {
        "MODEL_PERFORMANCE": "model performance", "VARIABLE_CONTRIBUTION_OR_RANK": "variable contribution/ranking",
        "POPULATION_ASSOCIATION_ESTIMATE": "population association", "CAUSAL_EFFECT": "causal effect",
        "CLUSTER_OR_PATTERN": "cluster/pattern", "REDUCED_PREDICTOR_SET": "reduced predictor set",
    }
    validation_labels = {
        "SPLIT": "train/test split", "CV": "cross-validation", "TEMPORAL": "later-period validation",
        "EXTERNAL": "external-dataset validation", "APPARENT": "apparent/in-sample evaluation",
        "OTHER": "other evaluation", "NONE_NR": "evaluation not reported", "NA": "not applicable",
    }
    metric_labels = {"RMSE":"RMSE", "MSE":"MSE", "MAE":"MAE", "R2":"R-squared",
                     "ACC":"accuracy", "AUROC":"AUROC", "F1":"F1 score", "OTHER":"task-specific measure",
                     "NR":"not reported", "NA":"not applicable"}

    def readable_codes(value, mapping):
        values = [token.strip() for token in str(value).split("|")]
        return "; ".join(mapping.get(token, token.replace("_", " ").lower()) for token in values)

    def yes_no(value, action):
        mapping = {"Y": action, "N": f"no {action}", "NR": f"{action} not reported",
                   "NA": f"{action} not applicable", "NOT_USED": f"{action} not used",
                   "USED": action, "NOT_PROVIDED_OR_NOT_REPORTED": "code not provided or not reported (unresolved)",
                   "PUBLIC_LINK_REPORTED_ACCESS_NOT_REVERIFIED": "public code link reported; access not reverified"}
        return mapping.get(str(value), str(value).replace("_", " ").lower())

    # Prompt 096: one author format, "Surname Initials" (+ "et al."). Korean-script names use Revised Romanisation.
    romanised_authors = {
        "KHM072": "Kim HS et al.", "KHM081": "Kim JG", "KHM146": "Chae HJ et al.",
        "KHM153": "Lee JY et al.", "KHM172": "You MY et al.", "KHM203": "Özcan MA",
        "KHM254": "Choi MK et al.",  # prompt 111: record lists "Choi, Mi-Kyung"
    }

    def surname_initials(name):
        parts = str(name).replace(",", " ").split()
        if len(parts) >= 2 and len(parts[-1]) <= 3 and parts[-1].isupper():
            return " ".join(parts)  # already "Surname INITIALS"
        initials = "".join(q[0].upper() for g in parts[:-1] for q in g.split("-") if q)
        return f"{parts[-1]} {initials}"
    task_specific_notes = {
        "KHM012": "Causal/mediation structure was the target; no predictive validation framework was applicable. Mediation assumptions and sensitivity analysis were not reported.",
        "KHM031": "Bayesian-network structure and posterior diagnostic combinations were examined; cluster/structure stability and independent replication were not reported.",
        "KHM038": "Bayesian-network pathways and population associations were examined; causal-identification assumptions and structural stability were not reported.",
        "KHM059": "Clusters were derived outside KNHANES and assigned in KNHANES and other cohorts by SVM; cross-cohort interpretability was examined, but formal cluster-stability indices were not reported.",
        "KHM088": "The estimand was heterogeneous/conditional causal effect of sleep duration on anxiety. Meta-learners addressed measured confounding; overlap, identifying assumptions, sensitivity analysis, and effect uncertainty were not fully reported.",
        "KHM092": "The estimand was the conditional intervention effect of physical activity or sedentary behaviour on mental-health outcomes. Accuracy, AUROC, and F1 describe outcome base learners, not validation of the causal-effect estimate; overlap and sensitivity analysis were not reported.",
        "KHM143": "The learned ordinal health-space representation was evaluated in external cohorts; external interpretability was examined, while representation stability was not separately reported.",
        "KHM156": "LDA-derived dietary patterns were compared across survey periods; formal topic/cluster stability and independent replication were not reported.",
        "KHM179": "The primary analysis was causal Bayesian-network structure for BMD determinants and pathways, despite predictive wording in the title; no treatment-effect estimand or predictive validation was reported.",
        "KHM072": "The tree fitted sleep hours; the short and long sleep groups were read from its terminal nodes.",
        "KHM203": "The network estimated a numeric risk score later read as three ordered tiers.",
    }

    continuous = []
    other = []
    audit_records = []
    for row in sorted(noncore, key=lambda r: r[index["A_study_id"]]):
        get = lambda name: row[index[name]]
        sid = get("A_study_id")
        doc = BY_ID[sid]
        authors = str(get("A_authors")).split("|")
        display_author = romanised_authors.get(sid, surname_initials(authors[0].strip()) + (" et al." if len(authors) > 1 else ""))
        short_citation = f"{display_author}, {get('A_publication_year')}"  # prompt 111: study IDs only in Table S8 and Data 1
        if sid == "KHM068":
            short_citation += "\u2020"  # prompt 097: retraction in the table footnote
        task = task_labels.get(get("B_analytic_task"), str(get("B_analytic_task")).replace("_", " ").title())
        target = get("E_outcome_name") if get("E_outcome_name") != "NA" else item_value(doc, "TSK03")
        approach = {
            "KHM072": "CART decision-tree analysis of continuous mean daily sleep duration; terminal nodes interpreted as problem-sleep risk groups",
            "KHM081": "Machine-learning regression with SHAP analysis",
            "KHM146": "Random-forest analysis of predictors of health-related quality of life",
            "KHM153": "Quality-of-life estimation model",
            "KHM203": "Neural-network estimation of next-month COPD exacerbation risk",  # prompt 096: English, not the original-language title
        }.get(sid, item_value(doc, "TSK02"))
        outputs = readable_codes(get("B_analytic_outputs"), output_labels)
        cycles = get("C_survey_years") if get("C_survey_years") != "NR" else get("C_cycles")
        cycles = _year_ranges(cycles)
        if str(cycles).strip() in {"NR", ""}: cycles = "years not reported"
        population = str(get("D_target_population")).split("|")[0].strip()
        if sid == "KHM072": population = "Korean adult cancer survivors aged 20-64 years"
        sample = get("D_final_sample")
        sample = f"{int(str(sample).strip()):,}" if str(sample).strip().isdigit() else "not reported"
        internal = readable_codes(get("H_internal_validation"), validation_labels)
        beyond = []
        if get("H_later_period_validation") == "Y": beyond.append("later KNHANES period")
        if get("H_external_validation") == "Y": beyond.append("external dataset")
        if not beyond: beyond.append("not reported")
        metrics = readable_codes(get("H_metrics_reported"), metric_labels)
        cont_audit = doc.get("adjudication", {}).get("continuous_interpretation_audit") or {}
        if cont_audit.get("status", "").startswith("USED"):
            interpretation = "importance: " + ", ".join(_method_label(x) for x in cont_audit.get("methods", []))
        elif get("I_importance_methods") not in {"NA", "NR"}:
            interpretation = "importance: " + ", ".join(_method_label(x) for x in str(get("I_importance_methods")).split("|"))
        else:
            interpretation = "importance: not reported"
        code_value = get("K_code_available")
        short = {"USED": "used", "Y": "used", "NOT_USED": "not used", "N": "not used", "NR": "not reported", "NA": "not applicable",
                 "NOT_PROVIDED_OR_NOT_REPORTED": "not provided", "PUBLIC_LINK_REPORTED_ACCESS_NOT_REVERIFIED": "public link reported"}
        state = lambda v: short.get(str(v), str(v).replace("_", " ").lower())
        # Prompt 093: one short survey-design phrase instead of three repeated "not reported" fields per row.
        design = {"weights in fitting": get("J_weights_in_fitting"), "weights in evaluation": get("J_weights_in_evaluation"),
                  "strata/PSUs": get("J_strata_PSUs_in_uncertainty")}
        used = [k for k, v in design.items() if str(v) in {"USED", "Y"}]
        others = sorted({state(v) for k, v in design.items() if k not in used})
        if not used:
            survey_text = "Survey design: " + (" / ".join(others) if others else "not reported")
        else:
            survey_text = "Survey design: " + ", ".join(used) + " used" + (f"; others {' / '.join(others)}" if others else "")
        survey = f"{survey_text}; code: {state(code_value)}"
        note = task_specific_notes.get(sid)
        # Prompt 097 (review v35): short categorical values; interpretive notes become one "task-specific checks" value.
        checks = {"KHM012": "Mediation assumptions: not reported", "KHM031": "Structure stability: not reported",
                  "KHM038": "Causal assumptions: not reported", "KHM059": "Cluster stability: not reported",
                  "KHM088": "Overlap and sensitivity: partly reported", "KHM092": "Overlap and sensitivity: not reported",
                  "KHM143": "Representation stability: not reported", "KHM156": "Pattern stability: not reported",
                  "KHM179": "Causal assumptions: not reported", "KHM260": "Rule stability: not reported", "KHM258": "Cluster stability: not reported"}.get(sid, "Not applicable")
        short_target = {"KHM012": "Mediation pathways", "KHM031": "Diagnostic combinations", "KHM038": "Health-behaviour pathways",
                        "KHM059": "Metabolic clusters", "KHM072": "Sleep duration (hours)", "KHM081": "EQ-5D index",
                        "KHM088": "Anxiety (GAD-7)", "KHM092": "Depressed mood, suicidal ideation, stress",
                        "KHM143": "Ordinal health status", "KHM156": "Dietary patterns", "KHM179": "Bone mineral density determinants",
                        "KHM203": "COPD exacerbation risk tier", "KHM260": "Low back pain risk combinations", "KHM258": "Nutrient-intake clusters"}.get(sid, str(target).split("|")[0].strip().rstrip(" ."))
        # Prompt 098 (review v36): algorithm abbreviations as in Table S8, not the authors' method wording.
        fams = [ALGO_ABBR.get(x.strip(), x.strip()) for x in str(get("G_algorithm_families")).split("|") if x.strip() not in {"", "NR", "NA"}]
        algo = ", ".join(fams) or {"KHM012": "Bayesian network", "KHM031": "Bayesian network", "KHM038": "Bayesian network",
                                   "KHM059": "Clustering, SVM", "KHM072": "DT", "KHM081": "Regression", "KHM156": "Topic model (LDA)",
                                   "KHM179": "Causal Bayesian network", "KHM068": "Regression",
                                   # prompt 111: single trees named in Data 1 G_author_selected_model
                                   "KHM229": "DT (CHAID)", "KHM239": "DT (CRT)", "KHM254": "DT (CHAID)",
                                   "KHM260": "RF (Boruta), association rules",
                                   "KHM258": "Clustering, tree ensembles (cluster membership)"}.get(sid, "\u2013")
        assert algo != "\u2013", sid  # prompt 111: every included study names its learner
        # Prompt 110 (review v47): one value per cell.
        display_row = [
            short_citation, task, short_target, f"{cycles}; n={sample}", algo, outputs,
            internal.replace("later-period validation", "").replace("external-dataset validation", "").replace("; ;", ";").strip("; ") or "\u2013",
            ", ".join(("Earlier" if sid == "KHM067" else t) for t, k in (("Later", "H_later_period_validation"), ("Ext", "H_external_validation")) if get(k) == "Y") or "\u2013",  # D21 B
            interpretation.replace("importance: ", ""), ", ".join(c for c, k in (("Wf", "J_weights_in_fitting"), ("We", "J_weights_in_evaluation"),
                                                                            ("SP", "J_strata_PSUs_in_uncertainty")) if str(get(k)) in {"USED", "Y"}) or "\u2013",
            state(code_value),
        ]  # prompt 111: design as Table S8 codes; task-specific checks in one footnote
        group = "Continuous- or ordered-outcome studies" if get("B_analytic_task") == "CONTINUOUS_OR_ORDERED_ESTIMATION" else "Other task-specific health analyses"
        (continuous if group.startswith("Continuous") else other).append(display_row)
        evidence_ids = []
        for item in ("TSK01", "TSK02", "TSK03", "OUT02", "OUT03", "VAL02"):
            for entry in value_rows(doc, item):
                evidence_ids.extend(entry.get("evidence_ids", []))
        audit_records.append({
            "study_id": sid, "group": group, "retained_task": get("B_analytic_task"),
            "task_label": task, "target": target, "method_and_role": approach,
            "decision_basis": item_value(doc, "TSK03"), "evidence_ids": list(dict.fromkeys(evidence_ids)),
            "manual_reread_result": "Retained after full task/target/scale/source-evidence reread",
        })
    _pin(len(continuous), 10, "build_standalone_supplements.py:3026")  # prompt 106 pin
    _pin(len(other), 9, "build_standalone_supplements.py:3026")  # prompt 106 pin
    noncore_rows = ([[f'Continuous- or ordered-outcome studies (n={len(continuous)})'] + [''] * 10] + continuous +  # prompt 107: counted; prompt 111: 11 columns
                    [[f'Other task-specific health analyses (n={len(other)})'] + [''] * 10] + other)
    audit_path = DATA / "Supplementary_Table_S06_noncore_health_reaudit.json"
    audit_path.write_text(json.dumps({"audit_date":"2026-09-20", "n":len(continuous) + len(other),  # prompt 107: counted, was fixed at 19
        "decision_rule":"Primary task follows the fitted target and evaluation scale plus the stated analytic aim; title wording alone does not determine classification.",
        "group_counts":{"continuous_or_ordered":len(continuous),"other_task_specific":len(other)},
        "records":audit_records}, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    emit_fixed_table(NONCORE_TABLE, "Noncore_health_analysis_studies", f"The {len(continuous) + len(other)} health-focused studies outside the core classification cohort",  # prompt 107: was fixed at 19
                     ["Study (first author, year)", "Task", "Target", "KNHANES years; n", "ML method", "Output", "Internal evaluation",
                      "Beyond development data", "Importance", "Survey design", "Code"],
                     noncore_rows, [28, 22, 26, 24, 22, 24, 27, 18, 20, 16, 18],
                     "Abbreviations as in Supplementary Table S8; DT (CHAID) and DT (CRT), single trees; Earlier, earlier survey period; "
                     "\u2013, none or not reported. \u2020Retracted; excluded from performance evidence.", 6.6)

    # S8: PRISMA-S reporting checklist. Requirements are concise paraphrases of
    # the 16-item extension; locations point to the reproducible search record.
    prisma_s_rows = [
        ["Information sources", "1", "Name every database and its platform.", "Section 2.2; Table S3", "Complete: source, interface/API, and URL are reported."],
        ["Information sources", "2", "Describe any simultaneous multi-database platform search.", "Table S3", "Not applicable: each source was queried separately."],
        ["Information sources", "3", "List study registries searched.", "\u2013", "Not applicable: no registry search; eligible completed analyses required recoverable results."],
        ["Information sources", "4", "Describe websites or other online/print sources browsed.", "Section 2.2; Table S3", "Complete: the full KDCA author-registered publication list was retrieved."],
        ["Information sources", "5", "Describe backward or forward citation searching.", "Section 2.2; Table S3", "Complete: 40 eligible seeds, direction, interfaces, and candidate disposition are reported."],
        ["Information sources", "6", "Describe contacts with authors or experts used to identify studies.", "\u2013", "Not performed."],
        ["Information sources", "7", "Describe any other identification method.", "Section 2.2; Table S3", "Complete: full-text Europe PMC layer and KDCA list are identified separately."],
        ["Search strategies", "8", "Provide full strategies exactly as run for every source.", "Table S3", "Complete, including the full KCI Korean/English term set and API queries."],
        ["Search strategies", "9", "State and justify limits or restrictions.", "Section 2.2; Table S3", "Complete: no date, language, or publication-type limit."],
        ["Search strategies", "10", "Name and cite any published search filters used.", "\u2013", "Not applicable: no published methodological filter was used."],
        ["Search strategies", "11", "State whether strategies were adapted from prior reviews.", "\u2013", "No substantive prior-review strategy was reused."],
        ["Search strategies", "12", "Report the date and method of any search update.", "\u2013", "Not applicable: this is the original review search, not an update."],
        ["Search strategies", "13", "Report the last search date for every source.", "Section 2.2; Table S3", "Complete: 3–5 September 2026 by source."],
        ["Search strategies", "14", "Describe peer review of the search strategy.", "\u2013", "No independent PRESS-style peer review was performed."],
        ["Records", "15", "Describe how retrieved records were managed.", "Sections 2.2 and 2.3; Figure 1", "Complete: DOI, PMID, normalised-title linkage, and study-family linkage are distinguished."],
        ["Records", "16", "Describe deduplication methods and software or code.", "Section 2.2; Table S3", "Complete: DOI→PMID→normalised-title precedence is reported; the deduplication code is held by the author."],
    ]
    emit_fixed_table(PRISMA_S_TABLE, "PRISMA_S_checklist", "Completed PRISMA-S search-reporting checklist",
                     ["Section", "Item", "Concise requirement", "Reported location", "Status and review-specific detail"],
                     prisma_s_rows, [30, 10, 92, 55, 105],
                     "Requirement wording is paraphrased. \u2013, answer given in the last column.", 7.5)

    # S7 is the actual one-row-per-study XLSX.  No placeholder TeX/PDF is generated:
    # a prose cover page could be mistaken for the master study-level table.
    MANIFEST.append(["Full coding log", "Internal full coding log (not submitted; Additional Data 1 is built by tools/build_data1_workbook.py)",  # prompt 117
                     "XLSX", len(master_rows), str(master_path.relative_to(ROOT))])

    build_rules_table_s7()
    build_verification_results_table()
    build_study_summary_table_s9(master_headers, master_rows)

    # Prompt 093: two submission files, Additional file 1 (supplement PDF) and Additional file 2 (Table S5 workbook).
    for stale in (ROOT / "manuscript/bmc_supplementary_table_s5.xlsx", ROOT / "manuscript/bmc_supplementary_table_s6.xlsx", ROOT / "manuscript/bmc_supplementary_table_s7.xlsx"):
        if stale.exists(): stale.unlink()
    shutil.copy2(master_path, ROOT / "manuscript" / DATA_FILE)  # prompt 097: Additional Data 1


def build_rules_table_s7():
    """Supplementary Table S7: human verification protocol, rules that produce the reported results."""
    import verification_protocol_rules as vp
    # Prompt 097: the "Table S5 column" column is dropped; variable names are in the Additional Data 1 dictionary.
    emit_fixed_table(RULES_TABLE, "Human_verification_protocol",
                     "Verification protocol: AI-assisted extraction, author check and coding rules",  # prompt 115
                     vp.HEADERS[:4], [r[:4] for r in vp.rows()], vp.WIDTHS[:4], vp.NOTE, font_size=8.0)


def build_verification_results_table():
    """Supplementary Table S8: recorded verification results (prompt 092; renumbered and trimmed in prompt 093).

    Every count is read from a retained record; stages without a stored count say "not recorded".
    """
    work = ROOT / "data/protocol_v1_2/P2_work"
    sweep = load_json("data/protocol_v1_2/P2_work/CONSISTENCY_SWEEP.json")
    adjud = load_json("data/protocol_v1_2/ADJUDICATION_SUMMARY.json")  # prompt 115
    assert (adjud["counts"]["studies"], adjud["reviewers"]["P2"].startswith("P2-CLAUDE-OPUS5")) == (222, True)
    targets = load_json("data/protocol_v1_2/P2_work/REREVIEW_TARGETS.json")
    changed = kept = 0
    reviewed_studies, changed_studies = set(), set()
    # Prompt 113 (external review): each decision is classed by the flag reason recorded with it, so the step from the
    # flagged items to the item decisions can be followed: a flag was decided for every item and model unit it covered,
    # items depending on a changed value were decided with it, and a third survey-design scan ran during the re-read.
    basis, basis_studies = Counter(), defaultdict(set)
    for path in sorted((work / "rereview_log").glob("*.json")):
        record = json.loads(path.read_text(encoding="utf-8"))
        for item in record.get("reviewed_items", []):
            reviewed_studies.add(record["study_id"])
            reason = (item.get("flag_reason") or "").lower()
            b = "scan3" if "scan3" in reason else "dependent" if "depend" in reason else "flagged"
            basis[b] += 1; basis_studies[b].add(record["study_id"])
            if item.get("decision") == "CHANGED":
                changed += 1; changed_studies.add(record["study_id"])
            elif item.get("decision") == "KEPT":
                kept += 1
    first_sweep = Counter(x["source"] for v in targets["targets"].values() for x in v)
    first_sweep_studies = {s for s, v in targets["targets"].items() if any(x["source"] == "sweep" for x in v)}
    rule_studies = {s for s, v in targets["targets"].items() if any(x["source"] == "coordinator_rule_change" for x in v)}
    scan_studies = {s for s, v in targets["targets"].items() if any(x["source"].startswith("sur_") for x in v)}
    scan3_new = basis_studies["scan3"] - set(targets["targets"])
    rerun_info = [d for d in sweep["details"] if d["rule"] in SWEEP_INFORMATIONAL_RULES]
    rerun_act = [d for d in sweep["details"] if d["rule"] not in SWEEP_INFORMATIONAL_RULES]
    assert basis["flagged"] + basis["dependent"] + basis["scan3"] == changed + kept
    assert len(reviewed_studies) == targets["studies"] + len(scan3_new), (len(reviewed_studies), targets["studies"], scan3_new)
    _pin((targets["items"], changed + kept, changed, kept, first_sweep["sweep"]), (406, 649, 413, 236, 284), "build_standalone_supplements.py:S7 prompt 113")
    recode = load_json("data/protocol_v1_2/P2_work/CONVENTION_RECODE_LOG.json")
    recode_changes = sum(len(r.get("changes", [])) for r in recode)
    validation = load_json("data/protocol_v1_2/P2_work/P2_VALIDATION.json")
    kci = load_json("results/derived/kci_fulltext_rechecks.json")
    evidence = load_json("data/protocol_v1_3/evidence_resolution_20260924.json")
    # Prompt 094: authors' aims and proposed uses are no longer coded, so only the output re-check is reported.
    ev_out = [r for r in evidence["resolutions"] if r["kind"] == "output"]
    ev_extra = [r for r in evidence["additional_corrections"] if r["kind"] == "output"]
    ev_changed = sum(r["old_code"] != r["new_code"] for r in ev_out) + len(ev_extra)
    _pin((len(ev_out), len(ev_extra), ev_changed), (11, 1, 9), "build_standalone_supplements.py:3118")  # prompt 106 pin
    topics = load_json("data/protocol_v1_3/topic_adjudications.json")
    noncore = json.loads((DATA / "Supplementary_Table_S06_noncore_health_reaudit.json").read_text(encoding="utf-8"))
    reassess = load_json("data/protocol_v1_3/judgement_reassessment.json")
    source_target_counts = Counter(x["source"] for v in targets["targets"].values() for x in v)
    changed_grades = sum(1 for r in reassess["rows"] if "->" in r[2])
    rows = [
        ["Screening", "Full-text check of Korean Citation Index records flagged at screening", "2 records", "2",
         "2 confirmed ineligible"],
        ["Screening and eligibility", "Title/abstract screening and eligibility decisions (the author)", "11,076 records",
         "not recorded", "not recorded"],
        # Prompt 115: the two AI extractions and their rule-based resolution (data/protocol_v1_2/ADJUDICATION_SUMMARY.json).
        ["Extraction (two AI systems)", "First-round records compiled by OpenAI Codex from an earlier extraction and checked against the "  # prompt 116
         "source; every item re-extracted by Anthropic Claude Opus 5 without access to them; the two compared item by item\u2020",
         f"{adjud['counts']['studies']} study records*",
         f"{adjud['counts']['agreement_items'] + adjud['counts']['adjudicated_items']:,} item comparisons: {adjud['counts']['agreement_items']:,} "
         f"identical, {adjud['counts']['adjudicated_items']:,} different",
         f"re-extracted value kept for the {adjud['counts']['adjudicated_items']:,} differences (named corpus decisions excepted)"],
        ["Extraction (all items)", "Completeness and schema validation of every study record",
         f"{validation['validated']} study records*", str(len(validation["fail"])), "0 (all records passed)"],
        # Prompt 113 (external review): the re-read is shown as its four steps, each with its own unit.
        ["Extraction (re-read, step 1: items flagged)", "Items queued for a source re-read: rule-based consistency flags across items, "
         "items affected by coding-rule changes made during extraction, and two text scans for survey-design sentences coded as not reported",
         f"{sweep['studies_checked']} study records*",
         f"{targets['items']} flagged items in {targets['studies']} records: {first_sweep['sweep']} consistency flags ({len(first_sweep_studies)} records), "
         f"{first_sweep['coordinator_rule_change']} rule changes ({len(rule_studies)}), "
         f"{first_sweep['sur_mention_scan'] + first_sweep['sur_design_scan2']} scan hits ({len(scan_studies)})", "see steps 2 and 3"],
        ["Extraction (re-read, step 2: item decisions)", "Each flagged item re-read against the source and decided for every item and model or "
         "evaluation unit it covered; items whose value depended on a changed value were decided with it; a third survey-design scan run during the "
         "re-read added items",
         f"{targets['studies'] + len(scan3_new)} records ({targets['studies']} flagged + {len(scan3_new)} from the third scan)",
         f"{changed + kept} item decisions in {len(reviewed_studies)} records: {basis['flagged']} on flagged items, {basis['dependent']} on dependent "
         f"items ({len(basis_studies['dependent'])} records), {basis['scan3']} from the third scan ({len(basis_studies['scan3'])} records)",
         f"{changed} values changed ({len(changed_studies)} records); {kept} confirmed"],
        ["Extraction (re-read, step 3: checks rerun)", "Rule-based consistency checks rerun on the corrected records "
         "(" + str(len(sweep["by_rule"])) + " rules raised a flag)",
         f"{sweep['studies_checked']} study records*",
         f"{len(sweep['details'])} flags in {len({d['study_id'] for d in sweep['details']})} records: {len(rerun_info)} list conditional items only; "
         f"{len(rerun_act)} in {len({d['study_id'] for d in rerun_act})} records on values decided in step 2",
         "no further re-read (flags fall on values decided in step 2)"],
        ["Extraction (coding conventions)", "Uniform application of recoding conventions (e.g., code link not reported recorded as not used)",
         f"{len(recode)} records", "not applicable", f"{recode_changes} values recoded"],
        ["Output coding", "Source re-read of output records without a resolved source location",
         f"{len(ev_out) + len(ev_extra)} records", f"{len(ev_out) + len(ev_extra)}",
         f"{ev_changed} codes changed"],
        ["Health-topic coding", "Outcome-centred topic re-read where an exposure or disease restriction could drive the topic",
         "214 health-focused studies (first round)", f"{len(topics['overrides'])}", f"{len(topics['amendments'])} topics amended"],
        ["Task assignment", "Full re-read of the 19 health-focused studies outside the core classification cohort in the first round",  # prompt 107: first-round scope
         f"{noncore['n']} studies", "not applicable", "0 changed; all retained"],
        ["Outcome and predictor grades", "Targeted source checks of outcome and predictor grades",
         f"{len(reassess['rows'])} study items", f"{len(reassess['rows'])} re-checked", f"{changed_grades} grades changed"],
        ["PROBAST+AI", "Domain and overall judgements checked within the source re-read",
         f"{PD_N} development and {PE_N} evaluation units (core cohort)", "included above", "included above"],
        ["Studies added at the re-screen after the first round (n=33)", "Single extraction of the 33 added studies by Claude Opus 5 (one from its abstract only), with the same protocol and automated source and evidence validation",  # prompt 111
         "33 studies", "all items", "not applicable (no second extraction)"],
        *([[f"Studies included after the Additional Data 1 re-check (n={len(_RL)})", "Two independent extractions (Claude Opus and Claude Sonnet) with the same protocol and automated validation; every difference settled against the source",
            f"{len(_RL)} studies", "all items", f"{sum(sum(r[2] != r[3] for r in list(csv.reader(open(ROOT / f'data/protocol_v1_2/P2_work/adjudication/{x}.tsv', encoding='utf-8'), delimiter=chr(9)))[1:] if len(r) > 3) for x in _RL)} differences settled"]] if _RL else []),
        *_recheck_row(),  # review 2026-10-24: the cell-by-cell re-check of Additional Data 1 stated in Methods
        ["Core reporting checklist (RC01-RC46)", "Two AI systems (Claude Code and Codex) checked every checklist judgement against the full text separately, "
         "in rounds until neither raised a new issue; disagreements settled by re-reading the source under written rules applied to all studies; "
         "coded values found not to match the report corrected and all results recomputed (coding audit, 2026-10-28/29)",
         "193 core studies x 46 items (8,878 judgements)", "6 rounds; round 1: 657 and 736 findings; rounds 2-6: 1-26 per system",
         "802 judgements changed; 39 coded values corrected; afterwards refined to 43 items (C01-C43; RC03 merged into RC02, RC04, RC05 and RC38 removed, RC42 re-specified, data availability RC47 added)"],
        ["Author check (all studies)", "Study-level dataset checked by the author against the source reports before analysis",
         f"{N_ALL} studies", "all records", "not recorded"],
    ]
    _pin(changed_grades, 2, "build_standalone_supplements.py:3151")  # prompt 106 pin
    emit_fixed_table(VERIFICATION_RESULTS_TABLE, "Verification_results", "Recorded verification results",
                     ["Stage", "Check", "Scope", "Flags or items checked", "Values changed after source comparison"],
                     rows, [40, 100, 50, 46, 60],
                     "*The 222 first-round records: 217 still included, 3 removed under the final criterion, 1 excluded at full review and 1 "
                     "preprint merged with its article (Supplementary Table S4). The " + str(N_ALL) + " included studies are these 217, 33 added at the "
                     "re-screen" + (f" and {len(_RL)} added at the Additional Data 1 re-check" if _RL else "") + ". A decision is one flagged item in "
                     "one model, evaluation or study unit. \u2020First-round records were migrated from an earlier extraction, so the share "
                     "identical describes the migration, not extraction accuracy. Not recorded, no stored count.", font_size=8.0)


STUDY_SUMMARY_TABLE = 8
STUDY_SUMMARY_PREVIEW_N = 10
ALGO_NAMES = {"Random forest": "random forest", "Logistic regression": "logistic regression", "SVM": "SVM", "XGBoost": "XGBoost",
              "LightGBM": "LightGBM", "CatBoost": "CatBoost", "DNN/MLP": "neural network", "Decision tree": "decision tree",
              "Naive Bayes": "naive Bayes", "kNN": "k-nearest neighbours", "Gradient boosting": "gradient boosting"}
IMP_NAMES = {"SHAP": "SHAP", "MODEL_NATIVE": "model-native", "PERMUTATION": "permutation", "COEFFICIENT_STATISTIC": "coefficient or statistic",
             "TREE_RULE": "tree or rule", "PERTURBATION_ABLATION": "perturbation", "LIME": "LIME", "PDP": "partial dependence", "OTHER": "other"}


ALGO_ABBR = {"Random forest": "RF", "Logistic regression": "LR", "XGBoost": "XGB", "LightGBM": "LGBM", "CatBoost": "CatBoost",
             "Gradient boosting": "GB", "SVM": "SVM", "DNN/MLP": "NN", "Decision tree": "DT", "Naive Bayes": "NB", "kNN": "kNN"}
SELECTED_PATTERNS = [("XGB", r"xgboost|\bxgb"), ("LGBM", r"lightgbm|\blgbm"), ("CatBoost", r"catboost"), ("RF", r"random forest|\brf\b"),
                     ("LR", r"logistic"), ("SVM", r"\bsvm|support vector"), ("NN", r"\bmlp|neural|\bdnn|\bann\b|perceptron"),
                     ("GB", r"gradient boosting|\bgbm\b|\bboosting"), ("DT", r"decision tree|\bcart\b"), ("NB", r"naive bayes"), ("kNN", r"\bknn|nearest")]
IMP_ABBR = {"SHAP": "SHAP", "MODEL_NATIVE": "MN", "PERMUTATION": "Perm", "COEFFICIENT_STATISTIC": "Coef", "TREE_RULE": "Tree",
            "PERTURBATION_ABLATION": "Pert", "LIME": "LIME", "PDP": "PDP", "OTHER": "other"}
S8_TOPIC_ORDER = ["METABOLIC_ENDOCRINE", "MENTAL_HEALTH", "MUSCULOSKELETAL", "CARDIOVASCULAR", "ORAL_HEALTH", "RESPIRATORY",
                  "GENERAL_HEALTH_MULTIMORBIDITY", "KIDNEY_UROLOGIC", "OTORHINOLARYNGOLOGIC", "OPHTHALMOLOGIC", "NUTRITION_DIET",
                  "HEALTH_BEHAVIOUR", "CANCER", "OTHER_OR_CROSS_CUTTING"]
S8_TOPIC_NAMES = {"METABOLIC_ENDOCRINE": "Metabolic and endocrine", "MENTAL_HEALTH": "Mental health", "MUSCULOSKELETAL": "Musculoskeletal",
                  "CARDIOVASCULAR": "Cardiovascular", "ORAL_HEALTH": "Oral health", "RESPIRATORY": "Respiratory",
                  "GENERAL_HEALTH_MULTIMORBIDITY": "General health", "KIDNEY_UROLOGIC": "Kidney and urologic",
                  "OTORHINOLARYNGOLOGIC": "Ear, nose and throat", "OPHTHALMOLOGIC": "Eye health", "NUTRITION_DIET": "Nutrition and diet",
                  "HEALTH_BEHAVIOUR": "Health behaviour", "CANCER": "Cancer", "OTHER_OR_CROSS_CUTTING": "Other or cross-cutting"}
OTHER_HEALTH_SHORT = {"KHM012": "Mediation pathways", "KHM031": "Diagnostic combinations", "KHM038": "Health-behaviour pathways",
                      "KHM059": "Metabolic clusters", "KHM072": "Sleep duration", "KHM081": "EQ-5D index", "KHM088": "Anxiety (GAD-7)",
                      "KHM092": "Depressed mood, suicidal ideation, stress", "KHM143": "Ordinal health status", "KHM156": "Dietary patterns",
                      "KHM179": "Bone mineral density determinants", "KHM203": "COPD exacerbation risk tier",
                      "KHM260": "Low back pain risk combinations",
                      "KHM258": "Nutrient-intake clusters"}


def top_variable_text(names):
    """Up to five variables as reported (practice_trends_098.json), lightly cleaned for display: a leading model or
    subgroup label ('Men:', 'XGB:'), trailing survey codes (HE_BMI) and commentary words are removed; entries that
    are formulas or sentences (over 40 characters) or not in English are dropped."""
    out = []
    for v in names:
        v = re.sub(r"^[^:]{1,40}:\s*", "", v)
        v = re.sub(r"\s+(?:[A-Z]{1,4}\d?_[A-Za-z0-9_]+)$", "", v)
        v = re.sub(r"\s+(also important|strongest|most important.*|also a split.*)$", "", v).strip()
        v = re.sub(r"^(.+?)(?: doctor diagnosis| diagnosis)? family history$", lambda m_: f"family history of {m_.group(1).lower()}", v)  # review 20261023
        if not v or len(v) > 40 or re.search(r"[\uac00-\ud7a3]|[*>]", v) or re.fullmatch(r"[A-Za-z]{1,4}\d?_[A-Za-z0-9_]*", v):
            continue
        out.append(v[0].lower() + v[1:] if v[:2] != v[:2].upper() else v)
    return ", ".join(out[:5])


def build_study_summary_table_s9(headers, rows):
    """Prompt 096: study-level summary table (last supplement table). Format preview of 10 studies to be audited
    before all 220 are added: two core studies per publication period, one other health-focused study and one
    method-focused study, each the lowest study ID in its stratum."""
    ix = {h: i for i, h in enumerate(headers)}
    g = lambda r, k: r[ix[k]]
    period = lambda y: "\u22642019" if y <= 2019 else "2020\u20132022" if y <= 2022 else "2023\u20132024" if y <= 2024 else "2025\u20132026"
    core = [r for r in rows if g(r, "B_core_health_classification") == "Y"]
    other = [r for r in rows if g(r, "B_other_health_analysis") == "Y"]
    method = [r for r in rows if g(r, "B_method_focused") == "Y"]
    _pin((len(core), len(other), len(method)), (165, 19, 36), "build_standalone_supplements.py:3214")  # prompt 106 pin
    pick = []
    for per in ("\u22642019", "2020\u20132022", "2023\u20132024", "2025\u20132026"):
        pick += sorted((r for r in core if period(int(g(r, "A_publication_year"))) == per), key=lambda r: g(r, "A_study_id"))[:2]
    pick += sorted(other, key=lambda r: g(r, "A_study_id"))[:1] + sorted(method, key=lambda r: g(r, "A_study_id"))[:1]
    assert len(pick) == STUDY_SUMMARY_PREVIEW_N
    rank_group = lambda r: 0 if g(r, "B_core_health_classification") == "Y" else 1 if g(r, "B_other_health_analysis") == "Y" else 2
    pick.sort(key=lambda r: (rank_group(r), int(g(r, "A_publication_year")), g(r, "A_study_id")))  # prompt 097: group, then year

    def author(r):
        a = [x.strip() for x in str(g(r, "A_authors")).split("|") if x.strip() and "Society" not in x]
        first = a[0] if a else "not reported"
        parts = first.replace(",", " ").split()
        if not (len(parts) >= 2 and len(parts[-1]) <= 3 and parts[-1].isupper()) and len(parts) >= 2 and parts[-1].isascii():
            parts = [parts[-1], "".join(q[0].upper() for w in parts[:-1] for q in w.split("-") if q)]
        if parts and parts[0].isupper() and len(parts[0]) > 1:
            parts[0] = parts[0].capitalize()  # "CHOI KT" -> "Choi KT"
        return " ".join(parts) + (" et al." if len(a) > 1 else "")

    def words(v, mapping=None, empty="not reported"):
        vals = [x.strip() for x in str(v).split("|") if x.strip() and x.strip() not in {"NA"}]
        if not vals or vals == ["NR"]: return empty
        return ", ".join((mapping or {}).get(x, x.replace("_", " ").lower()) for x in vals)

    group = lambda r: ("Core classification" if g(r, "B_core_health_classification") == "Y" else
                       "Other health analysis" if g(r, "B_other_health_analysis") == "Y" else "Method-focused")
    val_map = {"SPLIT": "train/test split", "CV": "cross-validation", "BOOT": "bootstrap", "APPARENT": "apparent only",
               "NONE_NR": "not reported", "OTHER": "other"}
    used = {"USED": "yes", "Y": "yes", "NOT_USED": "no", "N": "no", "NR": "not reported", "NA": "not applicable",
            "NOT_PROVIDED_OR_NOT_REPORTED": "not provided", "PUBLIC_LINK_REPORTED_ACCESS_NOT_REVERIFIED": "link reported"}
    top = json.loads((ROOT / "results/derived/practice_trends_106.json").read_text())["top_variables"]
    out = []
    # Prompt 098 (review v36): group and core-topic header rows (Figure 2B order), then publication year and first author.
    topic_of = lambda r: str(g(r, "B_health_topic")).split("|")[0].strip()
    keyed = []
    for r in pick:
        grp = rank_group(r)
        tkey = S8_TOPIC_ORDER.index(topic_of(r)) if grp == 0 and topic_of(r) in S8_TOPIC_ORDER else 99
        keyed.append(((grp, tkey, int(g(r, "A_publication_year")), author(r)), r))
    keyed.sort(key=lambda x: x[0])
    all_core_topics = Counter(topic_of(r) for r in core)
    group_titles = {0: f"Core health-focused classification studies (n={len(core)})", 1: f"Other health-focused studies (n={len(other)})",
                    2: f"Method-focused studies (n={len(method)})"}
    seen_group, seen_topic = set(), set()
    for (grp, tkey, _, _), r in keyed:
        if grp not in seen_group:
            seen_group.add(grp)
            out.append([group_titles[grp]] + [""] * 9)
        if grp == 0 and tkey not in seen_topic:
            seen_topic.add(tkey)
            out.append(["\u2003" + S8_TOPIC_NAMES.get(topic_of(r), "Other") + f" (n={all_core_topics[topic_of(r)]})"] + [""] * 9)
        sid = g(r, "A_study_id"); yr = int(g(r, "A_publication_year"))
        n = str(g(r, "D_final_sample")).split("|")[0].strip()
        n = f"{int(n):,}" if n.isdigit() else "not reported"
        if "duplicated in proportion to sampling weights" in str(g(r, "D_target_population")):
            n += "*"  # prompt 097: weight-replicated records, not participants (KHM019)
        outcome = str(g(r, "E_outcome_name")).split("|")[0].strip()
        outcome = re.sub(r"\s*\([^()]*[\uac00-\ud7a3][^()]*\)", "", outcome)  # Korean glosses stay in Table S5
        outcome = outcome.replace(">=", "\u2265").replace("<=", "\u2264")
        if outcome.count("(") > outcome.count(")"):
            outcome = outcome[:outcome.rindex("(")].rstrip()  # a "|" inside the source parenthesis split it
        if outcome in {"NA", "NR", ""}:
            outcome = "target described in Supplementary Table S5" if g(r, "B_other_health_analysis") == "Y" else "not applicable"
        beyond = [t for t, k in (("later survey period", "H_later_period_validation"), ("external data", "H_external_validation")) if g(r, k) == "Y"]
        imp = g(r, "I_importance_reported")
        imp_text = ("ranking: " + words(g(r, "I_importance_methods"), IMP_NAMES) + "; stability checked: " +
                    used.get(str(g(r, "I_importance_stability")), "not reported")) if imp == "USED" else "no ranking"
        design = [t for t, k in (("weights in fitting", "J_weights_in_fitting"), ("weights in evaluation", "J_weights_in_evaluation"),
                                  ("strata/PSUs", "J_strata_PSUs_in_uncertainty")) if str(g(r, k)) in {"USED", "Y"}]
        doi = str(g(r, "A_DOI")).strip()
        doi = doi if doi not in {"NR", "NA", ""} else "no DOI\u00a7"
        if g(r, "B_other_health_analysis") == "Y":
            outcome = OTHER_HEALTH_SHORT.get(sid, outcome)
        outcome = re.sub(r"\s*\((yes/no|stroke patient yes/no|[^()]*percentile[^()]*)\)", "", outcome)
        outcome = re.sub(r"\bm2\b", "m\u00b2", outcome).replace(" (CVD)", "")
        fams = [ALGO_ABBR.get(x.strip(), x.strip()) for x in str(g(r, "G_algorithm_families")).split("|") if x.strip() not in {"", "NR", "NA"}]
        chosen = str(g(r, "G_author_selected_model")).split("|")[0].lower()
        bold = next((ab for ab, pat in SELECTED_PATTERNS if re.search(pat, chosen) and ab in fams), None)
        algo = ", ".join(("\u27ea" + f + "\u27eb") if f == bold else f for f in fams) or "\u2013"
        valid = ", ".join(t for t, k in (("Later", "H_later_period_validation"), ("Ext", "H_external_validation")) if g(r, k) == "Y") or "\u2013"
        stab = "\u2021" if "USED" in [x.strip() for x in str(g(r, "I_importance_stability")).split("|")] else ""
        imp_codes = ", ".join(IMP_ABBR.get(x.strip(), x.strip().lower()) for x in str(g(r, "I_importance_methods")).split("|")
                              if x.strip() not in {"", "NA", "NR"})
        imp_cell = (imp_codes + stab) if imp == "USED" and imp_codes else "\u2013"
        design_codes = [t for t, k in (("Wf", "J_weights_in_fitting"), ("We", "J_weights_in_evaluation"), ("SP", "J_strata_PSUs_in_uncertainty"))
                        if str(g(r, k)) in {"USED", "Y"}]
        code = "Link" if str(g(r, "K_code_available")).startswith("PUBLIC_LINK") else "\u2013"
        years = _year_ranges(g(r, "C_survey_years")) if str(g(r, "C_survey_years")) != "NR" else "\u2013"
        out.append([
            sid, author(r).replace(" et al.", "") + f" {yr}", doi, outcome, f"{years}; {n.replace('not reported', '\u2013')}", algo, valid,
            imp_cell, (top_variable_text(top.get(sid, [])) or "\u2013") if imp == "USED" else "\u2013",
            f"{', '.join(design_codes) or '\u2013'}; {code}",
        ])
    # Prompt 113 (external review): the table shows ten studies, so it is titled as an illustration; the full list is Data 1.
    emit_fixed_table(STUDY_SUMMARY_TABLE, "Included_studies", "Characteristics of ten illustrative included studies",
                     ["ID", "Study", "DOI", "Outcome", "Survey years; n", "Algorithms", "Valid.", "Importance",
                      "Top-ranked variables", "Design; code"],
                     out, [14, 20, 34, 34, 25, 27, 12, 17, 64, 17],
                     "Lowest study IDs in each stratum: two core studies per period, one other health-focused and one method-focused study; "
                     "all studies are in Additional Data 1. \u2013, not reported or not done; bold, model the authors selected; \u2021, ranking "
                     "stability checked; top variables as reported, up to five. RF, random forest; LR, logistic regression; XGB, XGBoost; "
                     "LGBM, LightGBM; GB, other gradient boosting; SVM, support-vector machine; NN, neural network; DT, decision tree; NB, "
                     "naive Bayes; kNN, k-nearest neighbours; Later, later survey period; Ext, external data; MN, model-native; Perm, "
                     "permutation; Coef, coefficient or statistic; Wf/We, survey weights in fitting/evaluation; SP, strata or primary "
                     "sampling units in variance estimation. \u00a7Korean-language journal without DOI. *Records replicated in proportion "
                     "to sampling weights.", 7.0)


def build_manifest():
    def submission_order(row):
        # Prompt 092: citation order; figures follow the numbered tables, verification tables last.
        order = [f"Supplementary Table S{n}" for n in range(1, 6)] + [f"Supplementary Figure S{n}" for n in range(1, 9)] + [  # prompt 099: S1-S8
                 "Supplementary Table S6", "Supplementary Table S7", "Supplementary Table S8", "Full coding log"]  # prompt 117
        return order.index(row[0])
    MANIFEST.sort(key=submission_order)
    path = OUT / "supplementary_manifest.tsv"
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.writer(handle, delimiter="\t")
        writer.writerow(["Item", "Title", "Format", "Rows_or_scope", "Primary_path"])
        writer.writerows(MANIFEST)
    readme = OUT / "README.md"
    lines = ["# Supplementary materials", "", TITLE, "",
             "Additional file 1 (bmc_supplementary.pdf): Supplementary Tables S1--S8 and Figures S1--S8, numbered in the order the main text cites them; Tables S6 and S7 are the human verification protocol and its recorded results, and Table S8 illustrates the study-level record for ten included studies; all " + str(N_ALL) + " are listed in Additional Data 1. The same pages follow the reference list of manuscript/bmc_main.pdf.",
             "Additional file 2 (KNHANES_ML_review_Additional_Data_1.xlsx; built by tools/build_data1_workbook.py): Additional Data 1, one sheet with a row per included study (and the 95 regression-only or unsupervised reports) and every result as a column, defined in header notes. bmc_supplementary_data1.xlsx is the internal full coding log (not submitted).",
             "Item-level TeX sources are in `tex/`, compiled PDFs in `pdf/`, the workbook in `tables/`, and the figures in `figures/`.", "",
             "| Item | Title | Format | Scope |", "|---|---|---|---|"]
    lines.extend(f"| {a} | {b} | {c} | {d} |" for a, b, c, d, _ in MANIFEST)
    readme.write_text("\n".join(lines) + "\n", encoding="utf-8")


def tex_body(path):
    """Return literal document content without importing another TeX source."""
    source = path.read_text(encoding="utf-8")
    match = re.search(r"\\begin\{document\}(.*)\\end\{document\}", source, re.S)
    if not match:
        raise ValueError(f"No document body in {path}")
    return match.group(1).strip()


def build_combined_publication_supplement():
    """Build the author-facing, publication-form supplement in the paper root."""
    parts = []
    ordered = [f"Supplementary_Table_S{n:02d}*" for n in (1, 2, 3, 4, 5)] + [
               f"Supplementary_Figure_S{n:02d}*" for n in range(1, 9)] + ["Supplementary_Table_S06*", "Supplementary_Table_S07*",
                                                                      "Supplementary_Table_S08*"]
    for pattern in ordered:
        paths = list(TEX.glob(pattern + ".tex"))
        if len(paths) != 1:
            raise AssertionError((pattern, paths))
        body = tex_body(paths[0]).replace("manuscript/supplementary/figures/", "supplementary/figures/")
        item = next(row for row in MANIFEST if Path(row[4]).stem == paths[0].stem)
        navigation = tex_escape(item[0] + '. ' + item[1])
        # Prompt 097: every figure is a portrait page at full width; only tables are rotated.
        if "_Figure_" in paths[0].stem:
            body = body.replace(r"width=0.96\textwidth,height=0.80\textheight", r"width=\textwidth,height=0.78\textheight")
            parts.append("\\begingroup\n\\phantomsection\n\\addcontentsline{toc}{section}{" + navigation + "}\n" + body +
                         "\n\\endgroup\n\\clearpage")
            continue
        parts.append("\\begin{landscape}\n\\begingroup\n\\phantomsection\n" +
                     "\\addcontentsline{toc}{section}{" + navigation + "}\n" + body +
                     "\n\\endgroup\n\\end{landscape}\n\\clearpage")

    combined = rf"""\documentclass[9pt]{{extarticle}}
\usepackage[a4paper,margin=12mm]{{geometry}}
\usepackage{{fontspec,booktabs,longtable,array,ragged2e,enumitem,hyperref,graphicx,pdflscape,xcolor,needspace}}
\setmainfont{{Noto Serif CJK KR}}
\setsansfont{{Noto Sans CJK KR}}
\hypersetup{{hidelinks}}
\setlength{{\parindent}}{{0pt}}
\setlength{{\parskip}}{{5pt}}
\setlength{{\emergencystretch}}{{3em}}
\setlength{{\tabcolsep}}{{1.4pt}}
\renewcommand{{\arraystretch}}{{1.08}}
\sloppy
\begin{{document}}
\renewcommand{{\contentsname}}{{Supplementary contents}}
\tableofcontents
\clearpage
{chr(10).join(parts)}
\end{{document}}
"""
    tex_path = ROOT / "manuscript/bmc_supplementary.tex"
    from main_figure_map import remap  # journal main-figure numbers
    tex_path.write_text(remap(combined), encoding="utf-8")
    build_dir = ROOT / "build/submission"
    build_dir.mkdir(parents=True, exist_ok=True)
    subprocess.run(
        ["latexmk", "-xelatex", f"-outdir={build_dir}", "-interaction=nonstopmode",
         "-halt-on-error", tex_path.name],
        cwd=tex_path.parent, check=True, stdout=subprocess.DEVNULL,
    )
    shutil.copy2(build_dir / "bmc_supplementary.pdf", ROOT / "manuscript/bmc_supplementary.pdf")


def main():
    _pin(len(INCLUDED), 249, "build_standalone_supplements.py:3410")  # prompt 106 pin
    MANIFEST.clear()
    for directory in (TEX, PDF, TABLES, FIGURES, DATA):
        for path in directory.glob("Supplementary_*"):
            if path.is_file():
                path.unlink()
    build_final_supplement_tables()
    build_supplementary_figures()
    build_manifest()
    build_combined_publication_supplement()
    print(f"Built combined publication supplement and {len(MANIFEST)} separate reader-facing supplementary items")


if __name__ == "__main__":
    main()
