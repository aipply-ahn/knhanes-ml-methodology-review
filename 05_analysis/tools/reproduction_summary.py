"""복원 결과 종합 — results/derived/reproduction.json → data/REPRODUCTION.md"""
import os, sys, json
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from common import PROJ, DER, load
sys.path.insert(0, os.path.join(PROJ, "tools"))
from analyze_extraction import wave_scope

R = load(os.path.join(DER, "reproduction.json"))
E = {}
for k in R:
    p = os.path.join(PROJ, "data", "extraction", k + ".json")
    if os.path.exists(p): E[k] = load(p)

rows = []
for k, r in R.items():
    sc = wave_scope((E.get(k) or {}).get("knhanes_waves")) or "?"
    rows.append({**r, "scope": sc, "n_waves": len(r.get("waves") or []),
                 "pooled": bool(r.get("pooled"))})
rows.sort(key=lambda x: abs(x["n_diff"] / max(1, x["n_paper"])))

L = ["# 논문 분석자료의 원시자료 복원", "",
     "각 논문이 기술한 대상자 선정과 결과변수 정의를 KNHANES 원시자료에 그대로 적용해 분석자료를",
     "다시 만들고, 논문이 보고한 표본 수와 대조한 결과다. **수치를 맞추려고 규칙을 바꾸지 않았다.**",
     "복원 시 내린 판단은 각 레시피(`recipes/<key>.py`)의 문서화 문자열에 남겼다.", "",
     "| 논문 | 조사연차 | 범위 | 연차 통합 | 복원 n | 논문 n | 차이 | 상대오차 |",
     "|---|---|---|---|---:|---:|---:|---:|"]
for r in rows:
    w = r.get("waves") or []
    ws = f"{w[0]}" if len(w) == 1 else f"{w[0]}–{w[-1]} ({len(w)}개)"
    rel = 100 * r["n_diff"] / max(1, r["n_paper"])
    L.append(f"| {r['key']} | {ws} | {r['scope']} | {'통합' if r['pooled'] else '분리'} "
             f"| {r['n_reconstructed']:,} | {r['n_paper']:,} "
             f"| {r['n_diff']:+,} | {rel:+.1f}% |")

single = [r for r in rows if not r["pooled"]]
multi = [r for r in rows if r["pooled"]]
def mad(g): return sum(abs(100*x["n_diff"]/max(1,x["n_paper"])) for x in g)/len(g) if g else 0
L += ["", f"연차를 합치지 않은 {len(single)}편의 평균 절대 상대오차 **{mad(single):.1f}%**, "
      f"연차를 통합한 {len(multi)}편은 **{mad(multi):.1f}%**.", "",
      "연차 수 자체보다 **하나의 분석자료로 합쳤는지**가 갈랐다. chung2014screening 은 두 연차를 쓰지만",
      "2010년으로 개발하고 2011년을 외부검증에 써 합치지 않았고, 복원 오차가 0.4%에 그친다.", "",
      "## 단계별 대조", ""]
for r in rows:
    L += [f"### {r['key']}", "",
          "| 단계 | 복원 잔여 | 논문 잔여 | 차이 |", "|---|---:|---:|---:|"]
    for s in r["steps"]:
        pr = s.get("paper_remaining")
        d = s.get("diff")
        L.append(f"| {s['step']} | {s['remaining']:,} | "
                 + ("" if pr is None else f"{pr:,}") + " | "
                 + ("" if d is None else f"{d:+,}") + " |")
    o = r.get("outcome")
    if o: L.append(f"\n결과변수: 사건 {o['events']:,} / {o['n']:,} = {o['prev']}%\n")
    L.append("")
open(os.path.join(PROJ, "data", "REPRODUCTION.md"), "w", encoding="utf-8").write("\n".join(L) + "\n")
print(f"  data/REPRODUCTION.md — {len(rows)}편")
print(f"  단일 연차 평균 절대오차 {mad(single):.1f}% · 복수 연차 {mad(multi):.1f}%")
