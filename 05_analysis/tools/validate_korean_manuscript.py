#!/usr/bin/env python3
"""Validate that the current Korean reader copy matches the canonical BMC manuscript."""
from __future__ import annotations

import json
import re
import subprocess
from datetime import datetime
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SUB = ROOT / "manuscript"
SRC = SUB / "bmc_main_ko.tex"
OUT = ROOT / "results" / "derived" / "korean_manuscript_validation.json"


def pdf_text(path: Path) -> str:
    return subprocess.run(
        ["pdftotext", str(path), "-"], check=True, capture_output=True, text=True
    ).stdout


def page_count(path: Path) -> int:
    info = subprocess.run(
        ["pdfinfo", str(path)], check=True, capture_output=True, text=True
    ).stdout
    return int(re.search(r"^Pages:\s+(\d+)$", info, re.MULTILINE).group(1))


def main() -> None:
    source = SRC.read_text()
    figures = re.findall(r"\\includegraphics(?:\[[^]]*\])?\{([^}]+)\}", source)
    tables = re.findall(r"\\input\{(generated_tables_ko/[^}]+)\}", source)
    supplements = re.findall(r"\\includepdf[^\n]*\{([^}]+)\}", source)

    expected_macros = {
        "ScreenedReportN": "255", "StudyN": "250", "HealthN": "214", "MethodN": "36",  # prompt 106: criterion A
        "ClassN": "222", "AllClassN": "222", "HealthClassN": "192",  # prompt 106
        "ContinuousN": "16", "OtherN": "12", "PredictionN": "238",  # prompt 106
        "DevelopmentN": "355", "EvaluationN": "435",  # prompt 106
    }
    macro_text = (SUB / "protocol_v1_2_numbers.tex").read_text()
    macro_values = dict(re.findall(r"\\newcommand\{\\(\w+)\}\{([^}]+)\}", macro_text))

    # Prompt 092: manuscript/bmc_main_ko.pdf carries the English supplement; check the manuscript-only build.
    full_pdf = ROOT / "build" / "submission" / "bmc_main_ko.pdf"
    body_text = pdf_text(full_pdf)
    stale_patterns = ["224편", "198편", "209편", "206편", "11,076", "1,498"]
    stale_hits = [x for x in stale_patterns if x in body_text]
    generic_english = [
        "Catalogued outside the eligible ML corpus", "196 classification + 12 continuous + 12 other",
        "220 studies", "172 files across 80 studies", "Models and validation",
        "% of applicable studies", "Accounting", "Primary=198", "other=17",
    ]
    generic_english_hits = [x for x in generic_english if x in body_text]

    log_findings = {}
    for name in ("bmc_main_ko.log",):
        text = (ROOT / "build" / "submission" / name).read_text(errors="replace")
        log_findings[name] = {
            "fatal_or_error": bool(re.search(r"^!|Fatal error|Emergency stop", text, re.MULTILINE)),
            "undefined_reference_or_citation": bool(re.search(r"undefined references|undefined citations", text, re.I)),
            "overfull_boxes": len(re.findall(r"Overfull \\[hv]box", text)),
        }

    checks = {
        "canonical_macro_values": all(macro_values.get(k) == v for k, v in expected_macros.items()),
        # Prompt 093: five claim-ordered main figures (review v31 section 4.2).
        # Prompt 094 (review v32): six main figures.
        "twelve_figures_present": len(figures) == 7 and all((SUB / f).exists() for f in figures),  # Prompt 107: six main figures; Prompt 112: seven
        "one_conceptual_main_table": len(tables) == 0 and source.count(r"\begin{table}") == 1
        and not re.search(r"\\input\{table_[^}]+\}", source),
        "standalone_supplements": not supplements
        # Prompt 093: 7 PDF tables (S5 is the workbook) + 8 figures; S1-S8 XLSX.
        and len(list((SUB / "supplementary" / "pdf").glob("*.pdf"))) == 16  # Prompt 099: 8 tables + 8 figures
        and not list((SUB / "supplementary" / "pdf").glob("Supplementary_Data_1*.pdf"))  # Prompt 097: the workbook has no PDF
        and len(list((SUB / "supplementary" / "tables").glob("*.xlsx"))) == 9  # Prompt 097: S1-S8 + Additional Data 1
        and len(list((SUB / "supplementary" / "data").iterdir())) == 1
        and (SUB / "bmc_supplementary.tex").exists()
        and (SUB / "bmc_supplementary.pdf").exists()
        and not re.search(r"\\(?:input|include)\{", (SUB / "bmc_supplementary.tex").read_text()),
        "no_stale_denominators_in_body_pdf": not stale_hits,
        "no_known_generic_english_residue": not generic_english_hits,
        "latex_logs_clean": all(
            not v["fatal_or_error"] and not v["undefined_reference_or_citation"]
            for v in log_findings.values()
        ),
    }
    result = {
        "generated_at": datetime.now().astimezone().isoformat(timespec="seconds"),
        "source": str(SRC.relative_to(ROOT)),
        "status": "PASS" if all(checks.values()) else "FAIL",
        "checks": checks,
        "counts": {
            "figures": len(figures), "tables": len(tables), "supplements": len(supplements),
            "full_pages": page_count(full_pdf),
        },
        "canonical_macros": {k: macro_values.get(k) for k in expected_macros},
        "stale_hits": stale_hits,
        "generic_english_hits": generic_english_hits,
        "log_findings": log_findings,
        "notes": [
            "논문명, 고유 모델명, 약어 및 참고문헌의 원문 영문 표기는 허용한다.",
            "보충표 9개와 보충그림 1개를 제공하며 S7은 전체 220×158 자료를 담은 XLSX 전용 제출물이다.",
            "추가자료 10개 개별 제출물과 self-contained 통합 보충 TeX/PDF를 함께 관리한다.",
        ],
    }
    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(json.dumps(result, ensure_ascii=False, indent=2) + "\n")
    print(f"{result['status']}: {OUT.relative_to(ROOT)}")
    if result["status"] != "PASS":
        raise SystemExit(1)


if __name__ == "__main__":
    main()
# prompt 115: repinned to the sentences revised for review v51 (update_historical_tests.py)
