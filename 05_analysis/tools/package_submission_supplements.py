#!/usr/bin/env python3
"""Package Additional file 8 as machine-readable submission artifacts."""
from pathlib import Path
from shutil import copy2

ROOT = Path(__file__).resolve().parents[1]
DATA = ROOT / "data"
OUT = ROOT / "manuscript/submission/additional_files"
OUT.mkdir(parents=True, exist_ok=True)

FILES = {
    DATA / "INTEGRATED_STUDY_AUDIT.xlsx": OUT / "Additional_file_8a_integrated_study_dataset.xlsx",
    DATA / "INTEGRATED_STUDY_AUDIT.jsonl": OUT / "Additional_file_8b_integrated_study_dataset.jsonl",
    DATA / "EVIDENCE_LEDGER.tsv": OUT / "Additional_file_8c_evidence_ledger.tsv",
    DATA / "STUDY_JSON_DATA_DICTIONARY.md": OUT / "Additional_file_8d_data_dictionary.md",
}
for source, destination in FILES.items():
    if not source.exists():
        raise SystemExit(f"missing required supplement: {source}")
    copy2(source, destination)
print(f"PASS: packaged {len(FILES)} files in {OUT}")
