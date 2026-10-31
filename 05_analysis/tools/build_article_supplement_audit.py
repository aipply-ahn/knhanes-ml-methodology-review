#!/usr/bin/env python3
"""Build a study-level audit of supplementary-material retrieval for 224 reports."""

from __future__ import annotations

import csv
import json
from collections import Counter
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
REFS = ROOT / "references" / "refs.json"
MANIFEST = ROOT / "references" / "supplements" / "manifest.tsv"
STATUS = ROOT / "references" / "supplements" / "study_status.tsv"
VERIFY = ROOT / "data" / "MAIN_REPORT_SUPPLEMENT_VERIFICATION.tsv"
OUT = ROOT / "data" / "ARTICLE_SUPPLEMENT_AUDIT.tsv"

# Confirmed on the official article interface, but binary transfer remains blocked.
# Remove a study from this mapping once a manually retrieved file is entered in
# manifest.tsv; the manifest then takes precedence and marks it as acquired.
DISCLOSED_UNRETRIEVED = {
    "park2024predicting": (
        "The preprint refers to online Supplementary Tables S1 and S2, but its "
        "Supplementary Files page contains no file or asset URL; no separate file "
        "was recoverable from the retrieved report."
    ),
}


def main() -> None:
    refs = [r for r in json.loads(REFS.read_text(encoding="utf-8")) if r.get("verdict") == "INCLUDE"]
    manifest = list(csv.DictReader(MANIFEST.open(encoding="utf-8"), delimiter="\t"))
    checks = list(csv.DictReader(STATUS.open(encoding="utf-8"), delimiter="\t"))
    verification = (list(csv.DictReader(VERIFY.open(encoding="utf-8"), delimiter="\t"))
                    if VERIFY.exists() else [])
    by_verification = {row["key"]: row for row in verification}
    by_file, by_check = {}, {}
    for row in manifest:
        by_file.setdefault(row["key"], []).append(row)
    for row in checks:
        by_check.setdefault(row["key"], []).append(row)

    rows = []
    for ref in sorted(refs, key=lambda r: (r.get("year") or 0, r["key"])):
        key = ref["key"]
        extraction_path = ROOT / "data" / "extraction" / f"{key}.json"
        extraction = json.loads(extraction_path.read_text(encoding="utf-8")) if extraction_path.exists() else {}
        report_source = extraction.get("source", "")
        files = by_file.get(key, [])
        examined = [x.get("source_checked", "") for x in by_check.get(key, [])]
        verified = by_verification.get(key)
        if verified and verified.get("main_text_checked") == "Y":
            examined.extend(["main report disclosure text", "main PDF URI annotations"])
        if files:
            status = "acquired_and_text_reviewed"
            note = "Publicly accessible supplement files archived; searchable text generated where format permitted."
        elif key in DISCLOSED_UNRETRIEVED:
            status = "disclosed_but_transfer_blocked"
            note = DISCLOSED_UNRETRIEVED[key]
        else:
            status = "not_identified_in_reachable_sources"
            note = "No study-specific supplement was identified in the sources that could be inspected; this is not proof that none exists."
        rows.append({
            "key": key,
            "year": ref.get("year", ""),
            "title": ref.get("title", ""),
            "doi": ref.get("doi", ""),
            "pmcid": ref.get("pmcid", ""),
            # A generated markdown record may contain only an abstract.  It is therefore
            # not evidence that an assessable full report was obtained.
            "full_text_available": "yes" if report_source == "full_text" else "no",
            "report_source": report_source,
            "supplement_status": status,
            "files_archived": len(files),
            "local_paths": ";".join(x["local_path"] for x in files),
            "source_types_checked": ";".join(sorted(set(examined))),
            "manifest_sources": ";".join(sorted(set(x["source"] for x in files))),
            "review_text": f"references/supplements_text/{key}.md" if files else "",
            "note": note,
        })

    with OUT.open("w", encoding="utf-8", newline="") as f:
        w = csv.DictWriter(f, fieldnames=list(rows[0]), delimiter="\t")
        w.writeheader(); w.writerows(rows)

    c = Counter(r["supplement_status"] for r in rows)
    full_text_count = sum(r["full_text_available"] == "yes" for r in rows)
    file_count = sum(int(r["files_archived"]) for r in rows)
    verified_full = sum(r.get("main_text_checked") == "Y" for r in verification)
    verified_abstract = sum(r.get("adjudication") == "not_assessable_abstract_only" for r in verification)
    embedded_false_positive = sum(r.get("adjudication") == "embedded_or_false_positive_no_separate_file" for r in verification)
    md = [
        "# 포함 연구의 논문 보조자료 수집·검토 감사", "",
        "- 감사일: 2026-09-06",
        f"- 포함 보고: {len(rows)}편",
        f"- 평가 가능한 전문 확보: {full_text_count}편; 초록만 확보: {len(rows)-full_text_count}편",
        f"- 보조자료 확보·텍스트 재검토: {c['acquired_and_text_reviewed']}편, 원본 {file_count}개",
        f"- 출판사에서 보조자료를 명시했으나 전송 차단: {c['disclosed_but_transfer_blocked']}편",
        f"- 접근 가능한 출처에서 연구별 보조자료를 확인하지 못함: {c['not_identified_in_reachable_sources']}편", "",
        "## 판정 원칙", "",
        "각 DOI에 대해 Europe PMC/PMC, 출판사 랜딩 페이지와 주 논문 PDF의 링크를 확인했다. "
        "확보 파일은 `references/supplements/<study-key>/`에 원형으로 보존하고 URL·접근일·SHA-256을 manifest에 기록했다. "
        "PDF, DOCX, DOC, XLS/XLSX 및 ZIP의 텍스트는 `references/supplements_text/`에 변환해 주 논문 추출과 대조했다. "
        "그림·동영상 파일은 원본을 보존하고 매체 파일로 목록화했다.", "",
        "`not_identified_in_reachable_sources`는 확인 가능한 경로에서 발견하지 못했다는 뜻이다. "
        "출판사 접근 차단이나 페이지 구조 때문에 존재하지 않는다고 단정하지 않는다. 자동 전송이 차단됐던 "
        "SAGE 1편과 JAMIA 1편의 파일은 2026-09-06에 브라우저로 내려받아 수동 등록했다.", "",
        f"보조자료를 확인하지 못한 {c['not_identified_in_reachable_sources']}편 중 전문이 있는 {verified_full}편은 본문 전체의 명시적 보조자료 교차참조와 "
        f"PDF URI 주석을 추가로 검사했다. 별도 파일을 가리키는 미해결 후보는 없었고, {embedded_false_positive}편의 신호는 본문에 "
        f"포함된 Appendix 또는 체크리스트·참고문헌 문구로 판정했다. 초록만 확보된 {verified_abstract}편은 이 검증이 불가능했다.", "",
        "## 원고 반영", "",
        f"확보된 {c['acquired_and_text_reviewed']}편 모두의 추출 JSON에 보조자료 검토 여부와 파일 수를 기록했다. 보조자료로 명확히 확인된 "
        "표본 수, 결측 대체, 조사 가중치, 검증, 변수선택, 초매개변수 및 코드 공개 항목을 갱신했다. "
        "이 재검토에서 확인된 근거는 연구별 추출표에 반영하며, PROBAST+AI 판정은 별도 모형 단위 재평가에서 수행한다.", "",
        "연구별 상태, 저장 경로와 검사 출처는 [`ARTICLE_SUPPLEMENT_AUDIT.tsv`](ARTICLE_SUPPLEMENT_AUDIT.tsv), "
        "파일별 URL·체크섬은 [`../references/supplements/manifest.tsv`](../references/supplements/manifest.tsv), "
        "본문 재검증은 [`MAIN_REPORT_SUPPLEMENT_VERIFICATION.tsv`](MAIN_REPORT_SUPPLEMENT_VERIFICATION.tsv), "
        "재추출 대조표는 [`SUPPLEMENT_REEXTRACTION_QUEUE.tsv`](SUPPLEMENT_REEXTRACTION_QUEUE.tsv)에 있다.", "",
    ]
    OUT.with_suffix(".md").write_text("\n".join(md), encoding="utf-8")
    print(dict(c), "files", file_count)


if __name__ == "__main__":
    main()
