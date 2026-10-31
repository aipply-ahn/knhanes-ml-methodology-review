#!/usr/bin/env python3
"""Extract searchable text from archived article supplements and flag re-review items."""

from __future__ import annotations

import csv
import hashlib
import json
import re
import shutil
import subprocess
import tempfile
import zipfile
from collections import Counter
from pathlib import Path
from xml.etree import ElementTree as ET

ROOT = Path(__file__).resolve().parents[1]
SUPP = ROOT / "references" / "supplements"
OUT = ROOT / "references" / "supplements_text"
EXT = ROOT / "data" / "extraction"
QUEUE = ROOT / "data" / "SUPPLEMENT_REEXTRACTION_QUEUE.tsv"

IGNORE = {"manifest.tsv", "study_status.tsv"}
OOXML_TEXT_TAGS = {"t", "instrText", "delText"}

CATEGORIES = {
    "cohort_sample": r"inclusion|exclusion|eligible|eligibility|participant|sample|cohort|flow\s*chart|screen(?:ed|ing)|제외|포함|대상자|표본",
    "outcome_definition": r"outcome|endpoint|target|case\s+definition|diagnos|cut.?off|threshold|define[ds]?\s+as|결과변수|목적변수|진단|기준|정의",
    "predictor_definition": r"predictor|feature|variable|covariate|input|candidate|설명변수|예측변수|후보변수|변수",
    "missing_preprocessing": r"missing|imput|complete.case|standardi[sz]|normali[sz]|scal(?:e|ing)|one.hot|encoding|preprocess|결측|대치|표준화|정규화|전처리",
    "hyperparameters": r"hyper.?parameter|grid\s*search|random\s*search|bayesian|learning.rate|max.depth|n.estimator|tuning|초매개|하이퍼파라미터|튜닝",
    "validation_split": r"cross.?validation|bootstrap|train(?:ing)?.{0,12}(?:test|valid)|hold.?out|fold|split|external\s+valid|내부검증|외부검증|교차검증|훈련.{0,8}(?:시험|검증)|분할",
    "survey_design": r"survey\s*(?:weight|design)|sampling\s*weight|strat(?:a|ification)|cluster|complex\s*sample|weighted\s+(?:auc|analysis)|가중치|층화|집락|복합표본",
    "variable_importance": r"feature\s*importance|variable\s*importance|SHAP|Shapley|permutation\s*importance|Boruta|recursive\s*feature|RFE\b|LIME\b|PDP\b|partial\s*dependence|중요도|중요변수",
    "downstream_inference": r"odds\s*ratio|hazard\s*ratio|confidence\s*interval|logistic\s+regression|linear\s+regression|Cox\s+regression|spline|p.?value|추론|회귀분석|오즈비|신뢰구간",
    "code_or_model": r"github|source\s*code|code\s+(?:is|was|available)|repository|trained\s+model|model\s+file|코드\s*공개|저장소",
}

FIELD_MAP = {
    "cohort_sample": ["sample_filtering", "n_final"],
    "outcome_definition": ["problem"],
    "predictor_definition": ["variables", "variable_selection"],
    "missing_preprocessing": ["missing_handling", "preprocessing"],
    "hyperparameters": ["hyperparameter_tuning"],
    "validation_split": ["validation"],
    "survey_design": ["survey_weights"],
    "variable_importance": ["interpretability", "variable_selection"],
    "downstream_inference": ["findings", "interpretability"],
    "code_or_model": ["code_data_availability"],
}


def norm(s: str) -> str:
    return re.sub(r"\s+", " ", s).strip()


def extract_docx(path: Path) -> str:
    chunks = []
    with zipfile.ZipFile(path) as z:
        names = [n for n in z.namelist() if n.startswith("word/") and n.endswith(".xml")]
        names.sort(key=lambda n: (n != "word/document.xml", n))
        for name in names:
            try:
                root = ET.fromstring(z.read(name))
            except ET.ParseError:
                continue
            vals = []
            for e in root.iter():
                if e.tag.rsplit("}", 1)[-1] in OOXML_TEXT_TAGS and e.text:
                    vals.append(e.text)
                elif e.tag.rsplit("}", 1)[-1] in {"p", "tr"}:
                    vals.append("\n")
            chunks.append(f"\n[{name}]\n" + norm(" ".join(vals)))
    return "\n".join(chunks)


def extract_xlsx(path: Path) -> str:
    import openpyxl
    wb = openpyxl.load_workbook(path, read_only=True, data_only=True)
    out = []
    for ws in wb.worksheets:
        out.append(f"\n[SHEET: {ws.title}]")
        for row in ws.iter_rows(values_only=True):
            vals = [str(x) if x is not None else "" for x in row]
            if any(vals):
                out.append("\t".join(vals))
    return "\n".join(out)


def via_libreoffice(path: Path, target: str, tmp: Path) -> Path | None:
    subprocess.run(
        ["libreoffice", "--headless", "--convert-to", target, "--outdir", str(tmp), str(path)],
        stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, timeout=90, check=False,
    )
    candidates = list(tmp.glob(path.stem + ".*"))
    return max(candidates, key=lambda p: p.stat().st_mtime) if candidates else None


def extract_pdf(path: Path, tmp: Path) -> str:
    out = tmp / (path.stem + ".txt")
    subprocess.run(["pdftotext", "-layout", str(path), str(out)], timeout=120, check=False,
                   stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    return out.read_text(encoding="utf-8", errors="ignore") if out.exists() else ""


def extract_one(path: Path, tmp: Path, depth: int = 0) -> tuple[str, str]:
    ext = path.suffix.lower()
    try:
        if ext == ".pdf":
            return extract_pdf(path, tmp), "text_extracted"
        if ext == ".docx":
            return extract_docx(path), "text_extracted"
        if ext == ".xlsx":
            return extract_xlsx(path), "text_extracted"
        if ext == ".xls":
            converted = via_libreoffice(path, "xlsx", tmp)
            return (extract_xlsx(converted), "text_extracted") if converted else ("", "conversion_failed")
        if ext == ".doc":
            converted = via_libreoffice(path, "docx", tmp)
            return (extract_docx(converted), "text_extracted") if converted else ("", "conversion_failed")
        if ext == ".zip" and depth < 3:
            dest = tmp / ("unzipped_" + hashlib.sha1(str(path).encode()).hexdigest()[:10])
            dest.mkdir(exist_ok=True)
            with zipfile.ZipFile(path) as z:
                for item in z.infolist():
                    q = (dest / item.filename).resolve()
                    if not str(q).startswith(str(dest.resolve())):
                        continue
                    z.extract(item, dest)
            parts = []
            statuses = []
            for child in sorted(p for p in dest.rglob("*") if p.is_file()):
                txt, status = extract_one(child, tmp, depth + 1)
                statuses.append(status)
                parts.append(f"\n--- ARCHIVE MEMBER: {child.relative_to(dest)} ---\n{txt}")
            return "\n".join(parts), "archive_extracted" if parts else "empty_archive"
        if ext in {".txt", ".csv", ".tsv", ".md", ".xml"}:
            return path.read_text(encoding="utf-8", errors="ignore"), "text_extracted"
        if ext in {".png", ".jpg", ".jpeg", ".tif", ".tiff", ".gif", ".mp4"}:
            return "", "nontext_media_catalogued"
        return "", "unsupported_format"
    except Exception as exc:
        return "", f"error:{type(exc).__name__}"


def is_missing(value) -> bool:
    if value is None or value == "":
        return True
    if isinstance(value, str):
        return bool(re.search(r"미기재|확인\s*불가|not reported|unreported|unknown|^NR$", value, re.I))
    return False


def main() -> None:
    OUT.mkdir(parents=True, exist_ok=True)
    file_rows = []
    queue_rows = []
    for study_dir in sorted(p for p in SUPP.iterdir() if p.is_dir()):
        key = study_dir.name
        study_out = OUT / key
        if study_out.exists():
            shutil.rmtree(study_out)
        study_out.mkdir(parents=True)
        combined = []
        with tempfile.TemporaryDirectory(prefix=f"supp_{key}_") as td:
            tmp = Path(td)
            for path in sorted(p for p in study_dir.iterdir() if p.is_file() and p.name not in IGNORE):
                text, status = extract_one(path, tmp)
                text = text.replace("\x00", "")
                out_path = study_out / (re.sub(r"[^A-Za-z0-9._-]+", "_", path.name) + ".txt")
                out_path.write_text(text, encoding="utf-8")
                combined.append(f"\n## {path.name}\n\nExtraction status: {status}\n\n{text}")
                file_rows.append({
                    "key": key, "file": str(path.relative_to(ROOT)), "format": path.suffix.lower(),
                    "bytes": path.stat().st_size, "text_characters": len(text), "extraction_status": status,
                    "text_file": str(out_path.relative_to(ROOT)),
                })
        all_text = "\n".join(combined)
        (OUT / f"{key}.md").write_text(f"# {key}: article supplements\n" + all_text, encoding="utf-8")
        ext_path = EXT / f"{key}.json"
        rec = json.loads(ext_path.read_text(encoding="utf-8")) if ext_path.exists() else {}
        flags, possible = {}, []
        snippets = {}
        for cat, pat in CATEGORIES.items():
            matches = list(re.finditer(pat, all_text, re.I))
            flags[cat] = len(matches)
            if matches:
                m = matches[0]
                snippets[cat] = norm(all_text[max(0, m.start()-120):m.end()+220])
                if any(is_missing(rec.get(f)) for f in FIELD_MAP[cat]):
                    possible.extend(f for f in FIELD_MAP[cat] if is_missing(rec.get(f)))
        queue_rows.append({
            "key": key,
            "supplement_files": len(list(study_dir.iterdir())),
            "text_characters": len(all_text),
            **{f"hits_{k}": v for k, v in flags.items()},
            "possible_upgrade_fields": ";".join(sorted(set(possible))),
            "priority": "high" if possible else "reviewed_no_missing_field_trigger",
            "evidence_snippets_json": json.dumps(snippets, ensure_ascii=False),
        })

    fields = list(file_rows[0]) if file_rows else []
    with (OUT / "file_index.tsv").open("w", encoding="utf-8", newline="") as f:
        w = csv.DictWriter(f, fieldnames=fields, delimiter="\t"); w.writeheader(); w.writerows(file_rows)
    qfields = list(queue_rows[0]) if queue_rows else []
    with QUEUE.open("w", encoding="utf-8", newline="") as f:
        w = csv.DictWriter(f, fieldnames=qfields, delimiter="\t"); w.writeheader(); w.writerows(queue_rows)

    status_counts = Counter(r["extraction_status"] for r in file_rows)
    high = [r for r in queue_rows if r["priority"] == "high"]
    md = [
        "# 논문 보조자료 재추출 대기열", "",
        f"- 보조자료 확보 연구: {len(queue_rows)}편",
        f"- 파일: {len(file_rows)}개",
        f"- 검색 가능한 텍스트: {sum(r['text_characters'] > 0 for r in file_rows)}개 파일",
        f"- 기존 미기재 항목을 보완할 가능성이 있는 연구: {len(high)}편", "",
        "파일 처리 상태: " + ", ".join(f"{k} {v}" for k, v in sorted(status_counts.items())), "",
        "## 우선 원문 대조 대상", "",
        "| 연구 | 잠재 보완 항목 | 서플 텍스트 문자 수 |", "|---|---|---:|",
    ]
    for r in high:
        md.append(f"| {r['key']} | {r['possible_upgrade_fields']} | {r['text_characters']:,} |")
    (ROOT / "data" / "SUPPLEMENT_REEXTRACTION_QUEUE.md").write_text("\n".join(md) + "\n", encoding="utf-8")
    print(f"processed studies={len(queue_rows)} files={len(file_rows)} high_priority={len(high)}")
    print(dict(status_counts))


if __name__ == "__main__":
    main()
