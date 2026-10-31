#!/usr/bin/env python3
"""Validate an immutable review integration and write its audit deliverables."""
from __future__ import annotations

import argparse
from collections import Counter
from datetime import datetime
import hashlib
import json
import re
from pathlib import Path
import statistics

from openpyxl import load_workbook


def digest(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def read(path):
    wb = load_workbook(path, read_only=True)
    it = iter(wb.active.values)
    header = next(it)
    rows = {r[0]: dict(zip(header, r)) for r in it}
    sheets = wb.sheetnames
    wb.close()
    return header, rows, sheets


def snapshot(rows, header):
    core = [r for r in rows.values() if r["Study group"] == "Core classification"]
    included = [r for sid, r in rows.items() if sid.startswith('KHM')]
    methods = [r for r in rows.values() if r['Study group'] == 'Method-focused']
    other = [r for r in rows.values() if r['Study group'] == 'Other health analysis']
    result = {"core_n": len(core), "study_group_counts": dict(Counter(r["Study group"] for r in rows.values())),
              "categorical_counts": {}, "multi_label_counts": {}, "nonclass_display_states": {}, "numeric_summary": {}}
    result['all_included_record_metadata'] = dict(n=len(included),
        publication_year_counts=dict(sorted(Counter(str(r['Year']) for r in included).items())),
        publication_period_counts=dict(sorted(Counter(str(r['Publication period']) for r in included).items())))
    result['method_focused'] = dict(n=len(methods), evaluation_design_counts=dict(Counter(r['Method evaluation design'] for r in methods)))
    result['other_health'] = dict(n=len(other), methods_reported_n=sum(r['Other-health algorithms'] not in (None,'–','Not reported','Not recorded') for r in other),
        note='Source-named analytic methods/comparators are not forced into the core predictive-family taxonomy.')
    for col in header:
        counts = Counter(str(r[col]) for r in core)
        if len(counts) <= 30 and max(map(len, counts), default=0) <= 300:
            result["categorical_counts"][col] = dict(sorted(counts.items()))
    for col in ("Algorithm families fitted", "Family of the selected model", "Harmonised variables (Figure 5)", "Variable domains"):
        counts, states = Counter(), Counter()
        for row in core:
            if isinstance(row[col], str):
                value = row[col]
                if value.startswith('Not assessable') or value in {'–', 'None harmonised', 'Not recorded', 'Not reported', 'Not explicitly designated', 'Several algorithms not compared', 'Not applicable'}:
                    states[value] += 1
                else:
                    counts.update(set(value.split("; ")))
        result["multi_label_counts"][col] = dict(sorted(counts.items()))
        result["nonclass_display_states"][col] = dict(sorted(states.items()))
    for col in ("Final analytic sample", "Initial candidate predictors"):
        values = [r[col] for r in core if type(r[col]) in (int, float) and r[col] > 0]
        result["numeric_summary"][col] = dict(reported_numeric_n=len(values),
            median=statistics.median(values) if values else None, minimum=min(values) if values else None,
            maximum=max(values) if values else None,
            qualified_values=[dict(study_id=r['Study ID'], value=r[col]) for r in core
                              if isinstance(r[col], str) and re.match(r'^\d', r[col])],
            note='Strict positive numeric cells only; qualified source counts are preserved separately and are not silently imputed.')
    ranked = [r for r in core if r['Importance ranking produced'] == 'Yes']
    pairs = Counter()
    eligible = {k: [] for k in ('same_outcome_family', 'different_topic')}
    excluded = Counter()
    def domain_set(row):
        value = row['Variable domains']
        if not isinstance(value, str) or value.startswith('Not assessable') or value in {'–', 'Not reported', 'Not recorded', 'Unclear', 'NR', 'UNC', 'NA'}:
            return None
        return set(value.split('; ')) - {'', 'age', 'sex', 'adiposity body size'}
    for i, left in enumerate(ranked):
        for right in ranked[i + 1:]:
            group = left['Outcome group (Figure S7A)']
            if group != 'other' and group == right['Outcome group (Figure S7A)']:
                kind = 'same_outcome_family'
            elif left['Health topic'] != right['Health topic']:
                kind = 'different_topic'
            else:
                kind = 'same_topic_different_or_unclassified_outcome_family'
            pairs[kind] += 1
            x, y = domain_set(left), domain_set(right)
            if x is None or y is None:
                excluded['unavailable_domains_all_pairs'] += 1
                if kind in eligible:
                    excluded['unavailable_domains_classified_pairs'] += 1
            elif kind in eligible:
                if x | y:
                    eligible[kind].append(len(x & y) / len(x | y))
                else:
                    excluded['empty_domain_union_classified_pairs'] += 1
    result['s7a_pair_counts'] = dict(ranked_studies=len(ranked), **pairs)
    result['s7a_source_available_domain_jaccard'] = dict(
        source_available_studies=sum(domain_set(r) is not None for r in ranked),
        unavailable_study_ids=[r['Study ID'] for r in ranked if domain_set(r) is None],
        excluded_pair_counts=dict(excluded),
        groups={k: dict(pairs=len(v), median=statistics.median(v) if v else None) for k, v in eligible.items()},
        note='Exclude age/sex/adiposity domains. Unavailable source domains are not literal domain labels; no previous-version domain substitution.')
    return result


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("baseline", type=Path)
    parser.add_argument("decisions", type=Path)
    parser.add_argument("workbook", type=Path)
    parser.add_argument("--revision", required=True)
    parser.add_argument("--next-review", required=True)
    parser.add_argument("--next-integration", required=True)
    args = parser.parse_args()
    out = args.workbook.parent
    if (out / "VALIDATION.json").exists():
        raise ValueError("This version already has an audit report; preserve its history")
    d = json.loads(args.decisions.read_text())
    manifest = json.loads(args.workbook.with_suffix(".manifest.json").read_text())
    h, old, old_sheets = read(args.baseline)
    nh, actual_new, new_sheets = read(args.workbook)
    renames = d.get('header_renames', {})
    if tuple(renames.get(col, col) for col in h) != nh or list(old) != list(actual_new) or old_sheets != new_sheets:
        raise ValueError("Unexpected schema, row order or identifier change")
    new = {sid: {col: row[renames.get(col, col)] for col in h} for sid, row in actual_new.items()}
    if digest(args.baseline) != d["baseline_sha256"] or digest(args.workbook) != manifest["output_sha256"]:
        raise ValueError("Version checksum mismatch")
    actual = {(sid, col) for sid in old for col in h if old[sid][col] != new[sid][col]}
    expected = {(x["study_id"], x["column"]) for x in d.get("corrections", [])}
    if actual != expected:
        raise ValueError("Actual cell changes differ from the reviewed decisions")
    for x in d.get("corrections", []):
        if new[x["study_id"]][x["column"]] != x["new_value"]:
            raise ValueError("Integrated value differs from the decision")
    labels = [r["Study"].casefold() for sid, r in new.items() if sid.startswith("KHM")]
    if len(labels) != len(set(labels)):
        raise ValueError("Included first-author/year labels collide")
    statuses = Counter(x["status"] for x in d.get("issues", []))
    report = dict(validated_at=datetime.now().astimezone().isoformat(timespec="seconds"),
        revision=args.revision, rows=len(new), columns=len(h), exact_changed_cells=len(actual),
        matches_decisions=True, included_labels_case_insensitive_unique=True,
        baseline_sha256=digest(args.baseline), integrated_sha256=digest(args.workbook),
        issue_statuses=dict(statuses), verdict="NOT_APPROVED; exact-version independent reviews required")
    report['header_renames'] = renames
    impact = dict(baseline=snapshot(old, h), integrated=snapshot(actual_new, nh),
        changed_columns=dict(Counter(col for _, col in actual)), source_and_manuscript_updated=False,
        header_renames=renames,
        note="Review-only integration; publication figures and source release counts may differ. No new scientific reassessment of all locked source items is claimed.")
    (out / "VALIDATION.json").write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n")
    (out / "IMPACT.json").write_text(json.dumps(impact, ensure_ascii=False, indent=2) + "\n")
    summary = [f"# {args.revision} 통합 기록", "", f"통합: {manifest['integrated_at']}", "",
        f"대상 SHA256: `{report['integrated_sha256']}`", "", "**상태: 검수 중, 승인되지 않음.**", "",
        f"- {len(actual)}개 셀 수정. {len(new)}행·{len(h)}열과 연구 ID/순서를 보존했다.",
        f"- 명시적 열 이름 변경: {renames or '없음'}.",
        f"- 이슈 상태: {dict(statuses)}.",
        "- 변경값·기존 값·근거·통합 판단은 DECISIONS.json 및 XLSX manifest에 보존했다.",
        "- 새 Not assessable/불명확 상태는 원문 확보 또는 판정의 한계를 드러내며 임의의 No를 뜻하지 않는다.",
        "- 집계 영향은 IMPACT.json에 기록했다. 제출본/원고와의 동기화는 이 검수본 통합에 포함되지 않는다.",
        f"- 다음 독립 검수: {args.next_review}. 다음 통합: {args.next_integration}.", ""]
    notes = d.get("integration_notes", "세부 셀별 판단과 이전 검수 이견은 decisions 및 검수자 보고서 참조.")
    if isinstance(notes, list):
        notes = "\n\n".join(str(note) for note in notes)
    summary += ["## 통합 판단", "", notes, ""]
    (out / "INTEGRATION.md").write_text("\n".join(summary))
    ambiguous = [f"# {args.revision} 애매한 값 및 이슈", "", f"SHA256: `{report['integrated_sha256']}`", "",
        "근거에 충실한 원문 불확실성과 해결되지 않은 오류를 구분한다. 전체 파일 승인과 개별 이슈 판정은 다르다.", ""]
    for status in ("unresolved", "accepted_source_uncertainty", "resolved"):
        ambiguous += [f"## {status}", ""]
        for x in d.get("issues", []):
            if x["status"] == status:
                ambiguous += [f"### {x['study_id']} — {renames.get(x['column'], x['column'])}", "",
                    f"현재 값: {new[x['study_id']][x['column']]}", "", x["reason"], "", f"근거: {x['evidence']}", ""]
    limited = [(sid, col, row[col]) for sid, row in new.items() for col in h
               if isinstance(row[col], str) and row[col].startswith("Not assessable")]
    if limited:
        ambiguous += ["## 원문 확보 한계가 표시된 셀", "",
            "아래 상태는 미보고/미실시를 뜻하지 않는다. 이전 값은 셀 메모와 버전별 manifest에 보존된다.", "",
            "| Study | Field | Availability state |", "|---|---|---|"]
        for sid, col, value in limited:
            ambiguous.append(f"| {sid} | {renames.get(col, col)} | {value.replace('|', '/')} |")
        ambiguous.append("")
    (out / "AMBIGUITIES.md").write_text("\n".join(ambiguous))
    changes = [f"# {args.revision} 셀 변경", "", "아래는 축약값이다. 정확한 전문/자료형과 근거는 manifest/DECISIONS.json 참조.", "",
        "| Study | Field | Before | After | Adoption |", "|---|---|---|---|---|"]
    def short(value):
        s = str(value).replace("|", "\\|").replace("\n", " ")
        return s[:117] + "..." if len(s) > 120 else s
    for x in d.get("corrections", []):
        changes.append(f"| {x['study_id']} | {renames.get(x['column'], x['column'])} | {short(x['old_value'])} | {short(x['new_value'])} | {x.get('adoption', 'integrator adjudication')} |")
    (out / "CHANGES.md").write_text("\n".join(changes) + "\n")
    print(json.dumps(report, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
