#!/usr/bin/env python3
"""Build one review-ready Markdown file per included KNHANES-ML study.

Each output combines the extracted main article, every acquired supplement, and a
text-only reconstruction of all inventoried visual objects.  Direct ChatGPT image
reviews are merged with the consensus JSON inventory; no OCR engine is invoked.
"""

from __future__ import annotations

import csv
import hashlib
import json
import re
import shutil
from collections import Counter, defaultdict
from datetime import datetime
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[1]
FINAL_DIR = ROOT / "data/protocol_v1_2/final"
DECISIONS_PATH = ROOT / "data/protocol_v1_2/ADJUDICATION_SUMMARY.json"
MAIN_MD_DIR = ROOT / "references/md"
SUPP_TEXT_DIR = ROOT / "references/supplements_text"
VISION_QUEUE = ROOT / "data/CHATGPT_VISION_REVIEW_QUEUE.tsv"
LATEST_VISION = ROOT / "data/visual_manual_review/latest_after_recrop/LATEST_VISUAL_REVIEW.tsv"
OUTPUT_DIR = ROOT / "references/review_ready_md"


APPROX_RE = re.compile(
    r"(?:\bapprox(?:imate(?:ly)?)?\b|\bestimat(?:e|ed|ion)\b|\broughly\b|"
    r"\babout\b|\bvisually\b|read\s+from|digitized|gridline|axis|[≈~]|약\s*|추정)",
    re.I,
)
IMAGE_MD_RE = re.compile(r"!\[[^\]]*\]\([^\n)]*\)")
# Require a real HTML attribute name after the tag name.  This deliberately does
# not treat source-text markers such as ``<Figure 1>`` as embedded HTML images.
IMAGE_HTML_RE = re.compile(
    r"<\s*(?:img|figure)(?:\s+[A-Za-z_:][^>]*)?\s*/?>(?:.*?<\s*/\s*figure\s*>)?",
    re.I | re.S,
)
FRONT_MATTER_RE = re.compile(r"\A---\s*\n.*?\n---\s*\n", re.S)


def read_tsv(path: Path) -> list[dict[str, str]]:
    if not path.exists():
        return []
    with path.open(encoding="utf-8-sig", newline="") as handle:
        return list(csv.DictReader(handle, delimiter="\t"))


def text(value: Any) -> str:
    if value is None:
        return ""
    if isinstance(value, str):
        return value.strip()
    return json.dumps(value, ensure_ascii=False, sort_keys=True)


def clean_block(value: Any) -> str:
    return re.sub(r"\n{3,}", "\n\n", text(value)).strip()


def strip_front_matter(content: str) -> str:
    return FRONT_MATTER_RE.sub("", content, count=1).strip()


def remove_embedded_images(content: str) -> tuple[str, int]:
    count = 0

    def replacement(_: re.Match[str]) -> str:
        nonlocal count
        count += 1
        return "\n\n> [원본 이미지 생략 — 이 파일의 ‘시각자료 텍스트 재구성’ 절 참조]\n\n"

    content = IMAGE_MD_RE.sub(replacement, content)
    content = IMAGE_HTML_RE.sub(replacement, content)
    return content.strip(), count


def normalize_label(value: str) -> str:
    value = value.lower().replace("supplementary", "s").replace("supplemental", "s")
    value = value.replace("figure", "fig").replace("table", "tab")
    value = re.sub(r"[^a-z0-9]+", "", value)
    return value


def normalize_type(value: str) -> str:
    value = value.upper()
    if "TABLE" in value:
        return "TABLE"
    # The image-review queue calls flowcharts and graphical abstracts "figure";
    # treat every non-table visual as the same matching family.
    return "FIGURE"


def parse_json_list(value: str) -> list[Any]:
    if not value:
        return []
    try:
        parsed = json.loads(value)
        return parsed if isinstance(parsed, list) else [parsed]
    except json.JSONDecodeError:
        return [value]


def merge_direct_reviews() -> dict[str, list[dict[str, str]]]:
    """Merge first-pass and latest direct image reads, with latest fields winning."""
    rows: dict[tuple[str, str], dict[str, str]] = {}
    for row in read_tsv(VISION_QUEUE):
        rows[(row.get("study_key", ""), row.get("object_id", ""))] = dict(row)
    for latest in read_tsv(LATEST_VISION):
        key = (latest.get("study_key", ""), latest.get("object_id", ""))
        row = rows.get(key, {})
        row.update(
            {
                "study_key": latest.get("study_key", ""),
                "object_id": latest.get("object_id", ""),
                "object_type": latest.get("object_type", ""),
                "object_label": latest.get("object_label", ""),
                "source_scope": latest.get("source_scope", ""),
                "source_path": latest.get("source_file", ""),
                "page_or_sheet": latest.get("page_or_sheet", ""),
                "caption": latest.get("caption", ""),
                "chatgpt_vision_status": latest.get("scientific_interpretation_status", ""),
                "chatgpt_review_stage": latest.get("decode_status", ""),
                "chatgpt_visible_text": latest.get("chatgpt_image_transcription", ""),
                "chatgpt_interpretation": latest.get("chatgpt_image_interpretation", ""),
                "chatgpt_uncertainty": latest.get("remaining_uncertainty", ""),
                "manual_review_reason": latest.get("required_followup", ""),
                "ocr_engine_used": latest.get("ocr_engine_used", ""),
            }
        )
        rows[key] = row
    grouped: dict[str, list[dict[str, str]]] = defaultdict(list)
    for (study_key, _), row in rows.items():
        if study_key:
            grouped[study_key].append(row)
    for study_rows in grouped.values():
        study_rows.sort(key=lambda r: (r.get("source_scope", ""), r.get("object_label", ""), r.get("object_id", "")))
    return grouped


def source_manifest_lines(record: dict[str, Any]) -> list[str]:
    package = record.get("source_package", {})
    lines = ["## 원자료 구성", ""]
    main_files = package.get("main_text", {}).get("files", [])
    lines.append("- 본문 원자료:")
    for item in main_files:
        path = item.get("path", "") if isinstance(item, dict) else str(item)
        kind = item.get("type", "file") if isinstance(item, dict) else "file"
        lines.append(f"  - `{path}` ({kind})")
    supplements = package.get("supplement_files", [])
    if supplements:
        lines.append(f"- 서플 원자료: {len(supplements)}개 패키지")
        for supplement in supplements:
            status = supplement.get("availability", "NR")
            lines.append(
                f"  - `{supplement.get('supplement_id', '')}` — {supplement.get('filename', '')} "
                f"[{status}]"
            )
            for path in supplement.get("files", []):
                lines.append(f"    - `{path}`")
    else:
        lines.append("- 서플 원자료: 확인된 별도 서플 없음")
    lines.append("")
    return lines


def caption_for(obj: dict[str, Any]) -> str:
    start = text(obj.get("caption_start_anchor"))
    end = text(obj.get("caption_end_anchor"))
    if start and end and end not in start:
        return f"{start} … {end}"
    return start or end or "캡션 미기재"


def match_review(
    obj: dict[str, Any], candidates: list[dict[str, str]], used_ids: set[str]
) -> dict[str, str] | None:
    label = normalize_label(text(obj.get("object_label")))
    scope = text(obj.get("source_scope")).lower()
    obj_type = normalize_type(text(obj.get("object_type")))
    possible = []
    for row in candidates:
        if row.get("object_id", "") in used_ids:
            continue
        if row.get("source_scope", "").lower() != scope:
            continue
        if normalize_type(row.get("object_type", "")) != obj_type:
            continue
        row_label = normalize_label(row.get("object_label", ""))
        if label and row_label == label:
            possible.append(row)
    if len(possible) == 1:
        return possible[0]
    if possible:
        caption = normalize_label(caption_for(obj))
        return max(possible, key=lambda r: len(set(caption) & set(normalize_label(r.get("caption", "")))))
    return None


def value_line(value: Any) -> str:
    if isinstance(value, dict):
        preferred = ["field", "metric", "model", "outcome", "group", "value", "unit", "basis", "note"]
        keys = [key for key in preferred if key in value]
        keys += [key for key in value if key not in keys]
        return "; ".join(f"{key}={text(value[key])}" for key in keys)
    return text(value)


def split_values(values: list[Any], context: str = "") -> tuple[list[str], list[str]]:
    exact: list[str] = []
    approximate: list[str] = []
    context_approx = bool(APPROX_RE.search(context))
    for value in values:
        rendered = value_line(value)
        if not rendered:
            continue
        if context_approx or APPROX_RE.search(rendered):
            approximate.append(rendered)
        else:
            exact.append(rendered)
    return exact, approximate


def render_visual_object(
    obj: dict[str, Any],
    panels: list[dict[str, Any]],
    review: dict[str, str] | None,
    heading_level: int = 4,
) -> list[str]:
    hashes = "#" * heading_level
    label = text(obj.get("object_label")) or text(obj.get("object_id"))
    page = text(obj.get("printed_page")) or text(obj.get("pdf_page")) or "NR"
    status = text(obj.get("interpretation_status")) or "NR"
    lines = [f"{hashes} {label}", ""]
    lines.append(f"- 검수 객체 ID: `{text(obj.get('object_id'))}`")
    lines.append(
        f"- 위치: {text(obj.get('source_scope'))}; PDF/인쇄 페이지 {page}; "
        f"객체 유형 {text(obj.get('object_type'))}"
    )
    lines.append(f"- 캡션: {caption_for(obj)}")
    lines.append(f"- 판독 상태: {status}")

    transcription = text(obj.get("visible_text"))
    interpretation = text(obj.get("interpretation"))
    uncertainty = text(obj.get("rationale"))
    key_values: list[Any] = []
    if review:
        transcription = text(review.get("chatgpt_visible_text")) or transcription
        interpretation = text(review.get("chatgpt_interpretation")) or interpretation
        uncertainty_parts = [
            uncertainty,
            text(review.get("chatgpt_uncertainty")),
            text(review.get("manual_review_reason")),
        ]
        uncertainty = " | ".join(part for part in uncertainty_parts if part)
        key_values = parse_json_list(review.get("chatgpt_key_values", ""))
        lines.append(
            f"- 이미지 직접 판독: {text(review.get('chatgpt_vision_status')) or '완료'}; "
            f"단계 {text(review.get('chatgpt_review_stage')) or 'recorded'}; OCR 엔진 미사용"
        )

    if transcription:
        lines.extend(["", "**이미지 내 문자·구조 전사**", "", transcription])
    if interpretation:
        lines.extend(["", "**해석 가능한 설명**", "", interpretation])

    object_values = list(obj.get("extracted_values") or [])
    # Consensus extracted values inherit the object's audit rationale (for
    # example, "medians read approximately from the plot").  Direct-review key
    # values are classified one by one so that printed sample sizes/cut-offs stay
    # exact even when other metrics in the same graph are approximate.
    object_exact, object_approximate = split_values(object_values, text(obj.get("rationale")))
    review_exact, review_approximate = split_values(key_values)
    exact = object_exact + review_exact
    approximate = object_approximate + review_approximate
    if exact:
        lines.extend(["", "**문자로 명시된 값·수치(정확 전사)**", ""])
        lines.extend(f"- {item}" for item in dict.fromkeys(exact))
    if approximate:
        lines.extend(["", "**축·눈금·도형 위치에서 읽은 수치(추정값)**", ""])
        lines.extend(f"- 약 {item}" if not APPROX_RE.search(item) else f"- {item}" for item in dict.fromkeys(approximate))
    if not object_values and not key_values:
        lines.extend(["", "- 구조화 수치 목록: 없음(정성 도식이거나 별도 구조화 수치가 기록되지 않음)"])

    if panels:
        lines.extend(["", "**패널별 판독**", ""])
        for panel in panels:
            panel_label = text(panel.get("panel_label")) or text(panel.get("object_id"))
            lines.append(
                f"- ({panel_label}) [{text(panel.get('object_id'))}] "
                f"{text(panel.get('interpretation')) or '해석 미기재'}"
            )
            if panel.get("visible_text"):
                lines.append(f"  - 보이는 문자: {text(panel.get('visible_text'))}")
            p_exact, p_approx = split_values(
                list(panel.get("extracted_values") or []),
                text(panel.get("rationale")),
            )
            for value in p_exact:
                lines.append(f"  - 정확값: {value}")
            for value in p_approx:
                lines.append(f"  - 추정값: {value}")
    if uncertainty:
        lines.extend(["", f"- 남은 한계/불확실성: {uncertainty}"])
    if status.upper() in {"UNREADABLE", "UNCERTAIN"}:
        lines.append("- 검수 표지: 원본 또는 현재 확보 이미지에서 완전 판독 불가 — 사람의 원자료 확인 필요")
    lines.append("")
    return lines


def render_unmatched_review(row: dict[str, str]) -> list[str]:
    label = row.get("object_label") or row.get("object_id")
    lines = [f"#### {label} (직접 이미지 판독 추가 객체)", ""]
    lines.append(
        f"- 위치: {row.get('source_scope', 'NR')}; 페이지/시트 {row.get('page_or_sheet', 'NR')}; "
        f"유형 {row.get('object_type', 'NR')}"
    )
    if row.get("caption"):
        lines.append(f"- 캡션: {row['caption']}")
    if row.get("chatgpt_visible_text"):
        lines.extend(["", "**이미지 내 문자·구조 전사**", "", row["chatgpt_visible_text"]])
    if row.get("chatgpt_interpretation"):
        lines.extend(["", "**해석 가능한 설명**", "", row["chatgpt_interpretation"]])
    values = parse_json_list(row.get("chatgpt_key_values", ""))
    exact, approximate = split_values(values, row.get("chatgpt_uncertainty", ""))
    if exact:
        lines.extend(["", "**문자로 명시된 값·수치(정확 전사)**", ""] + [f"- {v}" for v in exact])
    if approximate:
        lines.extend(["", "**축·눈금·도형 위치에서 읽은 수치(추정값)**", ""] + [f"- {v}" for v in approximate])
    uncertainty = " | ".join(
        value for value in [row.get("chatgpt_uncertainty", ""), row.get("manual_review_reason", "")] if value
    )
    if uncertainty:
        lines.append(f"- 남은 한계/불확실성: {uncertainty}")
    lines.extend(["", "- 주: 최종 JSON 컨테이너와 안전하게 일대일 결합되지 않아 독립 객체로 보존함.", ""])
    return lines


def build_record(
    record: dict[str, Any], reviews: dict[str, list[dict[str, str]]], build_time: str
) -> tuple[str, dict[str, Any]]:
    study_id = record["study_id"]
    study_key = record["canonical_key"]
    metadata = record.get("metadata", {})
    main_path = MAIN_MD_DIR / f"{study_key}.md"
    supplement_path = SUPP_TEXT_DIR / f"{study_key}.md"
    main_content = main_path.read_text(encoding="utf-8")
    main_content, removed_images = remove_embedded_images(strip_front_matter(main_content))
    supplement_content = ""
    if supplement_path.exists():
        supplement_content = strip_front_matter(supplement_path.read_text(encoding="utf-8"))
        supplement_content, supp_removed = remove_embedded_images(supplement_content)
        removed_images += supp_removed

    objects = record.get("visual_objects", [])
    containers = [obj for obj in objects if obj.get("inventory_level") == "CONTAINER"]
    child_map: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for obj in objects:
        if obj.get("parent_object_id"):
            child_map[obj["parent_object_id"]].append(obj)
    for panels in child_map.values():
        panels.sort(key=lambda p: text(p.get("panel_label")))

    direct_rows = reviews.get(study_key, [])
    used_review_ids: set[str] = set()
    visual_lines = ["## 시각자료 텍스트 재구성", ""]
    visual_lines.extend(
        [
            "> 원본 그림 이미지는 이 검수본에 싣지 않았다. 아래 전사는 최종 합의 JSON과 ChatGPT의 직접 이미지 판독 기록을 병합한 것이다. "
            "‘정확값’은 그림·표에 문자로 인쇄된 수치이며, ‘추정값’은 축 눈금·수평선·점/막대 위치에서 읽거나 계산한 값이다. "
            "추정 표지가 없는 축 판독치를 정확값으로 승격하지 않는다.",
            "",
        ]
    )
    for scope in ("MAIN", "SUPPLEMENT"):
        scoped = [obj for obj in containers if obj.get("source_scope") == scope]
        if not scoped:
            continue
        visual_lines.extend([f"### {'본문' if scope == 'MAIN' else '서플'} 그림·표", ""])
        for obj in scoped:
            review = match_review(obj, direct_rows, used_review_ids)
            if review:
                used_review_ids.add(review.get("object_id", ""))
            visual_lines.extend(render_visual_object(obj, child_map.get(obj.get("object_id", ""), []), review))
    unmatched = [row for row in direct_rows if row.get("object_id", "") not in used_review_ids]
    if unmatched:
        visual_lines.extend(["### JSON 컨테이너와 미결합된 직접 이미지 판독 기록", ""])
        for row in unmatched:
            visual_lines.extend(render_unmatched_review(row))

    title = text(metadata.get("title")) or study_key
    authors = "; ".join(metadata.get("authors", []) or []) or "NR"
    front = [
        "---",
        f'study_id: "{study_id}"',
        f'canonical_key: "{study_key}"',
        f'publication_year: "{text(metadata.get("publication_year"))}"',
        f'doi: "{text(metadata.get("doi"))}"',
        'corpus_status: "INCLUDED_REPRESENTATIVE"',
        f'build_timestamp: "{build_time}"',
        'image_policy: "images_replaced_by_text; ChatGPT_direct_vision; OCR_engine_not_used"',
        "---",
        "",
        f"# {title}",
        "",
        f"- 연구 ID: `{study_id}`",
        f"- 정규 키: `{study_key}`",
        f"- 연도: {text(metadata.get('publication_year')) or 'NR'}",
        f"- 저자: {authors}",
        f"- 저널: {text(metadata.get('journal')) or 'NR'}",
        f"- DOI: {text(metadata.get('doi')) or 'NR'}",
        "- 구성: 본문 전체 추출문 + 확보된 모든 서플 추출문 + 전체 시각 객체 텍스트 재구성",
        "- 이미지 판독 정책: OCR 엔진 미사용; 기존 ChatGPT 직접 이미지 판독과 최종 합의 JSON 사용",
        "",
    ]
    output_lines = front + source_manifest_lines(record) + visual_lines
    output_lines.extend(["## 본문 전체 추출문", "", main_content, ""])
    if supplement_content:
        output_lines.extend(["## 서플 전체 추출문", "", supplement_content, ""])
    else:
        output_lines.extend(["## 서플 전체 추출문", "", "확인된 별도 서플 없음.", ""])

    result = "\n".join(output_lines).rstrip() + "\n"
    unresolved = sum(
        1 for obj in containers if text(obj.get("interpretation_status")).upper() in {"UNREADABLE", "UNCERTAIN"}
    )
    stats = {
        "study_id": study_id,
        "canonical_key": study_key,
        "title": title,
        "main_markdown": str(main_path.relative_to(ROOT)),
        "supplement_package_count": len(record.get("source_package", {}).get("supplement_files", [])),
        "supplement_text_included": supplement_path.exists(),
        "visual_objects_total": len(objects),
        "visual_containers": len(containers),
        "visual_panels": len(objects) - len(containers),
        "direct_image_reviews_matched": len(used_review_ids),
        "direct_image_reviews_preserved_unmatched": len(unmatched),
        "unreadable_or_uncertain_containers": unresolved,
        "embedded_images_removed": removed_images,
        "output_bytes": len(result.encode("utf-8")),
        "sha256": hashlib.sha256(result.encode("utf-8")).hexdigest(),
    }
    return result, stats


def included_records() -> list[dict[str, Any]]:
    decisions = json.loads(DECISIONS_PATH.read_text(encoding="utf-8")).get("decisions", {})
    excluded = {study_id for study_id, item in decisions.items() if item.get("include") is False}
    records = []
    for path in sorted(FINAL_DIR.glob("KHM*_final.json")):
        record = json.loads(path.read_text(encoding="utf-8"))
        if record.get("study_id") not in excluded:
            records.append(record)
    return sorted(records, key=lambda item: int(item["study_id"].replace("KHM", "")))


def validate(stats: list[dict[str, Any]], expected_visual_objects: int) -> dict[str, Any]:
    outputs = sorted(OUTPUT_DIR.glob("KHM*__*.md"))
    failures: list[str] = []
    if len(stats) != 220:
        failures.append(f"included record count is {len(stats)}, expected 220")
    if len(outputs) != 220:
        failures.append(f"output Markdown count is {len(outputs)}, expected 220")
    if sum(row["visual_objects_total"] for row in stats) != expected_visual_objects:
        failures.append("visual-object count differs from locked consensus total")
    if any(not row["supplement_text_included"] for row in stats if row["supplement_package_count"]):
        failures.append("at least one acquired supplement package lacks combined text")
    image_syntax_files = []
    for path in outputs:
        body = path.read_text(encoding="utf-8")
        if IMAGE_MD_RE.search(body) or IMAGE_HTML_RE.search(body):
            image_syntax_files.append(path.name)
    if image_syntax_files:
        failures.append(f"embedded image markup remains in {len(image_syntax_files)} files")
    return {
        "status": "PASS" if not failures else "FAIL",
        "included_studies": len(stats),
        "markdown_files": len(outputs),
        "visual_objects": sum(row["visual_objects_total"] for row in stats),
        "visual_containers": sum(row["visual_containers"] for row in stats),
        "visual_panels": sum(row["visual_panels"] for row in stats),
        "supplemented_studies": sum(bool(row["supplement_package_count"]) for row in stats),
        "supplemented_studies_with_text": sum(
            bool(row["supplement_package_count"]) and row["supplement_text_included"] for row in stats
        ),
        "direct_image_reviews_matched": sum(row["direct_image_reviews_matched"] for row in stats),
        "direct_image_reviews_preserved_unmatched": sum(
            row["direct_image_reviews_preserved_unmatched"] for row in stats
        ),
        "unreadable_or_uncertain_containers": sum(row["unreadable_or_uncertain_containers"] for row in stats),
        "ocr_engines_invoked_by_builder": 0,
        "files_with_embedded_image_markup": image_syntax_files,
        "failures": failures,
    }


def main() -> None:
    build_time = datetime.now().astimezone().isoformat(timespec="seconds")
    reviews = merge_direct_reviews()
    records = included_records()
    expected_visual_objects = sum(len(record.get("visual_objects", [])) for record in records)

    if OUTPUT_DIR.exists():
        shutil.rmtree(OUTPUT_DIR)
    OUTPUT_DIR.mkdir(parents=True)

    stats: list[dict[str, Any]] = []
    for record in records:
        rendered, row = build_record(record, reviews, build_time)
        output_path = OUTPUT_DIR / f"{record['study_id']}__{record['canonical_key']}.md"
        output_path.write_text(rendered, encoding="utf-8")
        row["output_file"] = str(output_path.relative_to(ROOT))
        stats.append(row)

    index_path = OUTPUT_DIR / "INDEX.tsv"
    with index_path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=list(stats[0]), delimiter="\t")
        writer.writeheader()
        writer.writerows(stats)

    review_required: list[dict[str, str]] = []
    review_keys: set[tuple[str, str, str]] = set()
    for record in records:
        for obj in record.get("visual_objects", []):
            status = text(obj.get("interpretation_status")).upper()
            if obj.get("inventory_level") != "CONTAINER" or status not in {"UNREADABLE", "UNCERTAIN"}:
                continue
            review_key = (
                record["canonical_key"],
                text(obj.get("source_scope")).lower(),
                normalize_label(text(obj.get("object_label"))),
            )
            review_keys.add(review_key)
            review_required.append(
                {
                    "origin": "CONSENSUS_JSON",
                    "study_id": record["study_id"],
                    "canonical_key": record["canonical_key"],
                    "object_id": text(obj.get("object_id")),
                    "object_label": text(obj.get("object_label")),
                    "source_scope": text(obj.get("source_scope")),
                    "page": text(obj.get("printed_page")) or text(obj.get("pdf_page")),
                    "status": status,
                    "recoverable_interpretation": text(obj.get("interpretation")),
                    "reason": text(obj.get("rationale")),
                    "output_file": f"references/review_ready_md/{record['study_id']}__{record['canonical_key']}.md",
                }
            )
    id_by_key = {record["canonical_key"]: record["study_id"] for record in records}
    for study_key, direct_rows in reviews.items():
        if study_key not in id_by_key:
            continue
        for row in direct_rows:
            direct_status = " ".join(
                [row.get("chatgpt_vision_status", ""), row.get("chatgpt_review_stage", "")]
            ).upper()
            if not any(
                marker in direct_status
                for marker in ("SOURCE_RECOVERY_REQUIRED", "MANUAL_REVIEW_REQUIRED", "UNREADABLE", "UNCERTAIN")
            ):
                continue
            review_key = (
                study_key,
                row.get("source_scope", "").lower(),
                normalize_label(row.get("object_label", "")),
            )
            if review_key in review_keys:
                continue
            review_keys.add(review_key)
            review_required.append(
                {
                    "origin": "DIRECT_IMAGE_REVIEW",
                    "study_id": id_by_key[study_key],
                    "canonical_key": study_key,
                    "object_id": row.get("object_id", ""),
                    "object_label": row.get("object_label", ""),
                    "source_scope": row.get("source_scope", "").upper(),
                    "page": row.get("page_or_sheet", ""),
                    "status": row.get("chatgpt_vision_status", ""),
                    "recoverable_interpretation": row.get("chatgpt_interpretation", ""),
                    "reason": " | ".join(
                        value
                        for value in [row.get("chatgpt_uncertainty", ""), row.get("manual_review_reason", "")]
                        if value
                    ),
                    "output_file": f"references/review_ready_md/{id_by_key[study_key]}__{study_key}.md",
                }
            )
    review_path = OUTPUT_DIR / "REVIEW_REQUIRED.tsv"
    with review_path.open("w", encoding="utf-8", newline="") as handle:
        fields = list(review_required[0]) if review_required else ["study_id"]
        writer = csv.DictWriter(handle, fieldnames=fields, delimiter="\t")
        writer.writeheader()
        writer.writerows(review_required)

    validation = validate(stats, expected_visual_objects)
    validation["review_required_visual_containers"] = len(review_required)
    (OUTPUT_DIR / "VALIDATION.json").write_text(
        json.dumps(validation, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )
    readme = f"""# Review-ready study Markdown corpus

Generated: {build_time}

- Included representative studies: {validation['included_studies']}
- Markdown files: {validation['markdown_files']}
- Full consensus visual objects represented: {validation['visual_objects']} ({validation['visual_containers']} containers; {validation['visual_panels']} panels)
- Studies with acquired supplements: {validation['supplemented_studies']} (combined supplement text present for {validation['supplemented_studies_with_text']})
- Direct ChatGPT image-review records matched to a consensus container: {validation['direct_image_reviews_matched']}
- Direct image-review records preserved separately because safe one-to-one matching was unavailable: {validation['direct_image_reviews_preserved_unmatched']}
- OCR engines invoked by this builder: 0
- Visual containers still requiring human source review: {validation['review_required_visual_containers']} (`REVIEW_REQUIRED.tsv`)
- Validation: **{validation['status']}**

Each `KHMxxx__key.md` contains the main article, every acquired supplement in the combined supplement transcription, and a text replacement for every inventoried figure/table container and panel. Exact printed values and approximate axis/gridline-derived values are labeled separately. `INDEX.tsv` is the per-study audit index and `VALIDATION.json` is the machine-readable completeness check.

Corpus decisions: KHM065 is excluded because no eligible fitted ML model was present; KHM076 is the duplicate preprint merged into representative journal report KHM100. Therefore 222 review packets yield 220 included representative study files.
"""
    (OUTPUT_DIR / "README.md").write_text(readme, encoding="utf-8")
    print(json.dumps(validation, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
