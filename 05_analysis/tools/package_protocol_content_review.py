#!/usr/bin/env python3
"""Bundle the actual protocol/manuscript/supplements and their content audit."""
import hashlib
import argparse
import json
from pathlib import Path
from zipfile import ZIP_DEFLATED, ZipFile

ROOT = Path(__file__).resolve().parents[1]
AUDIT = ROOT / "prompts/implementation_records/protocol_content_audit_20260924"


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--evidence-completion", action="store_true")
    parser.add_argument("--evidence-resolution", action="store_true")
    args = parser.parse_args()
    result = json.loads((AUDIT / "audit.json").read_text())
    assert result["status"] == "PASS", "Run the content audit successfully first"
    for name, expected in result["sha256"].items():
        assert hashlib.sha256((ROOT / name).read_bytes()).hexdigest() == expected, name
    files = [ROOT / "KNHANES_ML_study_audit_protocol.md",
             ROOT / "manuscript/bmc_main.pdf", ROOT / "manuscript/bmc_main_ko.pdf",
             ROOT / "manuscript/bmc_supplementary.pdf"]
    for stem in ("Supplementary_Table_S02_Operational_definitions_coding_rules",
                 "Supplementary_Table_S05_Data_dictionary"):
        files += [ROOT / f"manuscript/supplementary/pdf/{stem}.pdf",
                  ROOT / f"manuscript/supplementary/tables/{stem}.xlsx"]
    files.append(ROOT / "manuscript/supplementary/tables/Supplementary_Table_S07_Master_study_level_dataset.xlsx")
    files += sorted(p for p in AUDIT.iterdir() if p.suffix in {".json", ".tsv", ".md"})
    files += [ROOT / "tools/audit_protocol_publication_content.py"]
    completion = None
    resolution = None
    if args.evidence_resolution:
        notes = ROOT / "prompts/implementation_records/evidence_resolution_20260924"
        resolution = json.loads((notes / "verification.json").read_text())
        assert resolution["status"] == "PASS" and resolution["remaining_in_scope"] == 0
        for name, expected in resolution["sha256"].items():
            assert hashlib.sha256((ROOT / name).read_bytes()).hexdigest() == expected, name
        files += sorted(p for p in notes.iterdir() if p.suffix in {".json", ".tsv", ".md"})
        files += [ROOT / name for name in (
            "data/protocol_v1_3/evidence_resolution_20260924.json",
            "data/protocol_v1_3/evidence_repairs_20260924.json",
            "tools/complete_protocol_evidence.py",
            "tools/validate_evidence_completion.py",
            "tools/validate_evidence_resolution.py",
            "prompts/implementation_records/evidence_completion_20260924/verification.json")]
    if args.evidence_completion:
        notes = ROOT / "prompts/implementation_records/evidence_completion_20260924"
        completion = json.loads((notes / "verification.json").read_text())
        assert completion["validation"] == "PASS"
        assert completion["s7_sha256"] == hashlib.sha256(
            (ROOT / "manuscript/bmc_supplementary_table_s7.xlsx").read_bytes()).hexdigest()
        files += sorted(p for p in notes.iterdir() if p.suffix in {".json", ".tsv", ".md"})
        files += [ROOT / "data/protocol_v1_3/evidence_repairs_20260924.json",
                  ROOT / "tools/complete_protocol_evidence.py",
                  ROOT / "tools/validate_evidence_completion.py"]
    manifest = "sha256\tfile\n" + "".join(
        f"{hashlib.sha256(p.read_bytes()).hexdigest()}\t{p.relative_to(ROOT)}\n" for p in files)
    target = ROOT / ("manuscript/protocol_evidence_completion_20260924.zip" if args.evidence_completion
                     else "manuscript/protocol_content_review_20260924.zip")
    if args.evidence_resolution:
        target = ROOT / "manuscript/protocol_evidence_resolved_20260924.zip"
    with ZipFile(target, "w", ZIP_DEFLATED) as archive:
        for p in files:
            archive.write(p, str(p.relative_to(ROOT)))
        archive.writestr("SHA256SUMS.tsv", manifest)
        if completion:
            archive.writestr("EVIDENCE_COMPLETION_STATUS.json", json.dumps(completion, ensure_ascii=False, indent=2))
        if resolution:
            archive.writestr("EVIDENCE_RESOLUTION_STATUS.json", json.dumps(resolution, ensure_ascii=False, indent=2))
        archive.writestr("README.txt", """프로토콜·본문·서플 실물 대조 묶음

정본 Markdown, 영문/국문 본문, 통합 서플, S2/S5 PDF와 XLSX, S7 실물을 함께 포함합니다.
S2는 질문·기록단위/연결키·적용조건·응답·개별 규칙·근거의 7열 표입니다.
S5는 158개 변수의 8열 사전입니다. S7은 연구별 값과 전체 기술정보를 보존합니다.
S7의 RECORD_DETAILS/RECORD_EVIDENCE에서 반복 기록·원문 위치·발췌를 행 단위로 읽을 수 있습니다.
공개 레코드 ID는 이 판본의 위치 식별자이며 원문 분석단위가 확인됐다는 뜻이 아닙니다.
방법단계의 세부값과 Figure 5용 7개 표시범주는 별도로 보존됩니다.
audit.json 및 item_comparison.tsv는 정본과 실물의 대조 결과입니다.
retained_evidence_gaps.tsv는 원자료에서 근거 ID가 없는 레코드 목록입니다.
source_content_gaps.tsv는 평가기준명·통계분석 연결 등 원문 확인이 필요한 내용 목록입니다.
audit.json의 구조/정보보존 통과와 source_content_status의 원문 확인 상태는 별개입니다.
빈 목록은 해당 점검 항목에 남은 누락이 없다는 뜻이며, 220편 전체를 새로 재추출했다는 뜻은 아닙니다.
완료판의 세부 판정과 이전 기록은 evidence_resolution_20260924 기록 및 S7 classification_revision 행에 보존됩니다.
SHA256SUMS.tsv로 파일 버전을 확인할 수 있습니다.
""")
    with ZipFile(target) as archive:
        assert archive.testzip() is None
    print(target.relative_to(ROOT))


if __name__ == "__main__":
    main()
