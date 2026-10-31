#!/usr/bin/env python3
"""Record the manual disposition of supplement keyword-screen candidates."""
import csv
from collections import Counter
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "data/SUPPLEMENT_REEXTRACTION_QUEUE.tsv"
OUT = ROOT / "data/SUPPLEMENT_REEXTRACTION_ADJUDICATION.tsv"
UPDATED = {
    "bhak2024machine", "choi2026development", "dashdondov2026assessing",
    "jang2026psychological", "jo2023development", "kim2026sleep",
    "lee2019deep", "nguyen2024explainable", "you2025related",
    "ahn2025machine", "jang2023machine",
}

rows = list(csv.DictReader(SRC.open(encoding="utf-8"), delimiter="\t"))
out = []
for r in rows:
    if r["key"] in UPDATED:
        decision = "extraction_updated"
        rationale = "Supplement supplied a previously unavailable operational detail; structured extraction and, where applicable, quality coding were updated."
    elif r["priority"] == "high":
        decision = "reviewed_no_change"
        rationale = "The flagged word occurred in a table label, checklist, code default, result, or already captured passage and did not resolve the missing operational detail."
    else:
        decision = "reviewed_no_missing_field_trigger"
        rationale = "Supplement was text-reviewed; no keyword evidence pointed to an extraction field previously coded as missing."
    out.append({
        "key": r["key"], "supplement_files": r["supplement_files"],
        "text_characters": r["text_characters"], "candidate_fields": r["possible_upgrade_fields"],
        "decision": decision, "rationale": rationale,
        "evidence_snippets_json": r["evidence_snippets_json"],
    })

with OUT.open("w", encoding="utf-8", newline="") as f:
    w = csv.DictWriter(f, fieldnames=list(out[0]), delimiter="\t"); w.writeheader(); w.writerows(out)
c = Counter(r["decision"] for r in out)
md = [
    "# 논문 보조자료 재추출 판정", "",
    f"- 보조자료 확보 연구: {len(out)}편",
    f"- 새 정보로 구조화 추출을 갱신: {c['extraction_updated']}편",
    f"- 후보 문구를 원문 대조했으나 판정 변경 없음: {c['reviewed_no_change']}편",
    f"- 기존 미기재 항목과 연결되는 후보 문구 없음: {c['reviewed_no_missing_field_trigger']}편", "",
    "`reviewed_no_change`에는 표 제목·체크리스트·코드의 기본 인수처럼 해당 단어는 있으나 실제 처리 방법을 "
    "설명하지 않은 경우와, 이미 주 논문 추출에 반영된 내용을 보조자료가 반복한 경우가 포함된다.", "",
    "| 연구 | 판정 | 후보 항목 |", "|---|---|---|",
]
for r in out:
    md.append(f"| {r['key']} | {r['decision']} | {r['candidate_fields'] or '없음'} |")
OUT.with_suffix(".md").write_text("\n".join(md)+"\n", encoding="utf-8")
print(dict(c))
