#!/usr/bin/env python3
"""Replace the full-page retry for Mun/Lee/Yang 2025 Figure 1 with its embedded figure."""
from __future__ import annotations

import csv
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
OID = "munilyang2025methodology__0002__figure_1"
STUDY = "munilyang2025methodology"
IMAGE = "data/visual_manual_review/latest_after_recrop/decoded_recovered/figure/munilyang2025methodology__0002__figure_1__embedded_original.png"
VISIBLE = (
    "Six-step vertical framework: (1) 연관성 분석 모델—XGBoost 기반 국민건강영양데이터 4개년치(20–23년) 이용 당뇨병 위험 요인 연관성 분석; "
    "(2) 고위험군 식별—Lift chart를 이용한 비교군 고위험군 식별 및 확률 구간 선정; "
    "(3) 반사실적 설명—DiCE 알고리즘을 이용해 고위험군에서 저위험군으로 변환된 가설적 시나리오 생성; "
    "(4) 연관성 기반 도출 프롬프트 작성—원본 고위험군 데이터와 가설적 시나리오 비교; "
    "(5) 온프레미스 LLM 맞춤형 설명—의료 특화 Meerkat-8B를 활용한 자연어 가이드 생성; "
    "(6) 보험산업 적용 전략 수립—위험 평가, 맞춤형 보험상품 개발, 연관성 중심 보험모델 진화 전략 제시."
)
INTERP = (
    "The figure presents an association-oriented six-stage workflow from XGBoost risk-factor analysis and Lift-chart risk stratification "
    "through DiCE counterfactual scenarios and Meerkat-8B explanations to insurance-industry application. "
    "The authors explicitly frame the outputs as statistical associations and hypothetical alternatives, with disclaimers and uncertainty expression."
)
VALUES = [
    "KNHANES years: 2020–2023", "analysis model: XGBoost", "risk stratification: Lift chart",
    "counterfactual method: DiCE", "LLM: Meerkat-8B", "number of stages: 6",
]


def update(row: dict) -> None:
    if row.get("object_id") != OID:
        return
    row.update({
        "image_path": IMAGE, "image_width_px": "920", "image_height_px": "1298",
        "extraction_method": "original embedded PDF image", "extraction_confidence": "verified",
        "vision_required": "N", "chatgpt_vision_status": "completed",
        "chatgpt_review_stage": "embedded_original_chatgpt_reread",
        "chatgpt_visible_text": VISIBLE, "chatgpt_interpretation": INTERP,
        "chatgpt_key_values": json.dumps(VALUES, ensure_ascii=False),
        "chatgpt_uncertainty": "", "manual_review_reason": "",
    })


def tsv(rel: str, remove: bool = False, latest: bool = False) -> None:
    path=ROOT/rel
    with path.open(encoding="utf-8-sig",newline="") as h:
        rd=csv.DictReader(h,delimiter="\t"); fields=rd.fieldnames or []; rows=list(rd)
    out=[]
    for row in rows:
        if remove and row.get("object_id")==OID: continue
        update(row)
        if latest and row.get("object_id")==OID:
            row.update({
                "decode_status":"COMPLETE_AFTER_SOURCE_RECOVERY_CHATGPT_IMAGE_REREAD",
                "crop_recovery_status":"repaired_embedded_original",
                "scientific_interpretation_status":"COMPLETE",
                "chatgpt_image_transcription":VISIBLE,
                "chatgpt_image_interpretation":INTERP,
                "remaining_uncertainty":"", "required_followup":"",
                "latest_review_image":IMAGE, "latest_image_kind":"embedded_original_figure",
            })
        out.append(row)
    with path.open("w",encoding="utf-8-sig",newline="") as h:
        wr=csv.DictWriter(h,fieldnames=fields,delimiter="\t",lineterminator="\n",extrasaction="ignore"); wr.writeheader(); wr.writerows(out)


def main() -> None:
    # Canonical study JSON.
    study_path=ROOT/f"data/study_json/{STUDY}.json"
    study=json.loads(study_path.read_text(encoding="utf-8"))
    for obj in study["visual_objects"]["items"]:
        if obj.get("object_id")==OID:
            obj.update({"image_path":IMAGE,"visible_text":VISIBLE,"interpretation":INTERP,"key_values":VALUES,"vision_status":"completed","vision_review_stage":"embedded_original_chatgpt_reread","uncertainty":"","manual_review_reason":""})
    study_path.write_text(json.dumps(study,ensure_ascii=False,indent=2)+"\n",encoding="utf-8")

    # Vision annotation.
    ann_path=ROOT/f"data/visual_object_audit/vision_annotations/{OID}.json"
    ann=json.loads(ann_path.read_text(encoding="utf-8"))
    ann.update({"status":"completed","visible_text":VISIBLE,"interpretation":INTERP,"key_values":VALUES,"uncertainty":"","manual_review_reason":"","review_stage":"embedded_original_chatgpt_reread"})
    ann_path.write_text(json.dumps(ann,ensure_ascii=False,indent=2)+"\n",encoding="utf-8")

    # Canonical visual ledger.
    jp=ROOT/"data/ALL_REPORT_VISUAL_OBJECTS.jsonl"; rows=[]
    for line in jp.read_text(encoding="utf-8").splitlines():
        if line.strip():
            obj=json.loads(line); update(obj); rows.append(obj)
    jp.write_text("".join(json.dumps(x,ensure_ascii=False)+"\n" for x in rows),encoding="utf-8")
    tsv("data/ALL_REPORT_VISUAL_OBJECTS.tsv")
    tsv("data/CHATGPT_VISION_REVIEW_QUEUE.tsv")
    tsv("data/CHATGPT_VISION_MANUAL_REVIEW_QUEUE.tsv",remove=True)
    tsv("data/visual_manual_review/latest_after_recrop/LATEST_VISUAL_REVIEW.tsv",latest=True)
    tsv("data/visual_manual_review/latest_after_recrop/UNRESOLVED_INDEX.tsv",remove=True)
    tsv("data/visual_manual_review/unresolved_after_recrop/UNRESOLVED_VISUALS.tsv",remove=True)

    # Rebuild decoded index from the current master index.
    latest=ROOT/"data/visual_manual_review/latest_after_recrop/LATEST_VISUAL_REVIEW.tsv"
    with latest.open(encoding="utf-8-sig",newline="") as h:
        rd=csv.DictReader(h,delimiter="\t"); fields=rd.fieldnames or []; rows=[r for r in rd if r.get("scientific_interpretation_status")!="SOURCE_RECOVERY_REQUIRED"]
    decoded=ROOT/"data/visual_manual_review/latest_after_recrop/DECODED_RECOVERED_INDEX.tsv"
    with decoded.open("w",encoding="utf-8-sig",newline="") as h:
        wr=csv.DictWriter(h,fieldnames=fields,delimiter="\t",lineterminator="\n"); wr.writeheader(); wr.writerows(rows)

    # Synchronize the study-level JSONL entry.
    idx=ROOT/"data/STANDARDIZED_STUDY_JSON_INDEX.jsonl"; entries=[]
    for line in idx.read_text(encoding="utf-8").splitlines():
        if line.strip():
            obj=json.loads(line); entries.append(study if obj.get("study_id")==STUDY else obj)
    idx.write_text("".join(json.dumps(x,ensure_ascii=False)+"\n" for x in entries),encoding="utf-8")
    print("resolved",OID)


if __name__=="__main__":
    main()
