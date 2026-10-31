"""논문이 기술한 분석자료를 KNHANES 원시자료에서 복원한다.

    python tools/reproduce.py            # 등록된 레시피 전부
    python tools/reproduce.py <key> ...  # 지정한 것만

각 레시피는 recipes/<key>.py 이며 다음을 노출한다.
  PAPER : 논문이 보고한 값 (waves · 제외 단계별 인원 · 최종 n · 결과변수 유병)
  build(ctx) : 원시자료에서 분석자료를 만들고 (DataFrame, 단계 목록) 을 돌려준다.
               단계는 (설명, 제외수 또는 None, 잔여수) 튜플이다.

산출 results/reproduction/<key>/{dataset.parquet,report.md} 와 요약 results/derived/reproduction.json.
논문 값과 다르면 그대로 기록한다 — 맞추려고 규칙을 바꾸지 않는다.
"""
import os, sys, json, importlib.util, traceback
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import pandas as pd
from knhanes_io import load_year, PROJ

REC = os.path.join(PROJ, "recipes")
OUT = os.path.join(PROJ, "results", "reproduction")


def _load(key):
    spec = importlib.util.spec_from_file_location(key, os.path.join(REC, key + ".py"))
    m = importlib.util.module_from_spec(spec); spec.loader.exec_module(m)
    return m


def pct(a, b):
    return "" if not b else f"{100*(a-b)/b:+.1f}%"


def run(key):
    m = _load(key)
    df, steps = m.build(load_year)
    P = m.PAPER
    d = os.path.join(OUT, key); os.makedirs(d, exist_ok=True)
    df.to_parquet(os.path.join(d, "dataset.parquet"), index=False)

    rep = P.get("reported_cascade", [])
    L = [f"# {key} — 분석자료 복원", "",
         f"- 논문: {P.get('title','')}", f"- 조사연차: {P.get('waves')}",
         f"- 결과변수: {P.get('outcome','')}", "",
         "## 대상자 선정 단계", "",
         "| 단계 | 복원 제외 | 복원 잔여 | 논문 제외 | 논문 잔여 | 잔여 차이 |",
         "|---|---:|---:|---:|---:|---:|"]
    rows = []
    for i, (lab, ex, rem) in enumerate(steps):
        pe = pr = None
        if i < len(rep): pe, pr = rep[i].get("excluded"), rep[i].get("remaining")
        diff = "" if pr is None else f"{rem-pr:+,} ({pct(rem,pr)})"
        rows.append({"step": lab, "excluded": ex, "remaining": rem,
                     "paper_excluded": pe, "paper_remaining": pr,
                     "diff": None if pr is None else rem - pr})
        L.append(f"| {lab} | {'' if ex is None else f'{ex:,}'} | {rem:,} | "
                 f"{'' if pe is None else f'{pe:,}'} | {'' if pr is None else f'{pr:,}'} | {diff} |")
    n_rep, n_got = P.get("n_final"), len(df)
    L += ["", f"**최종 표본 복원 {n_got:,} · 논문 {n_rep:,} · 차이 {n_got-n_rep:+,} ({pct(n_got,n_rep)})**", ""]

    ev = None
    if P.get("outcome_col") and P["outcome_col"] in df.columns:
        y = df[P["outcome_col"]].dropna()
        ev = {"n": int(y.notna().sum()), "events": int(y.sum()), "prev": round(100*y.mean(), 2)}
        pv = P.get("prevalence")
        L += ["## 결과변수", "",
              f"- 복원: 사건 {ev['events']:,} / {ev['n']:,} = {ev['prev']}%",
              (f"- 논문: {pv}" if pv else ""), ""]
    if m.__doc__: L += ["## 복원 시 내린 판단", "", m.__doc__.strip(), ""]
    open(os.path.join(d, "report.md"), "w", encoding="utf-8").write("\n".join(L) + "\n")
    return {"key": key, "n_reconstructed": n_got, "n_paper": n_rep,
            "n_diff": n_got - n_rep, "steps": rows, "outcome": ev,
            "vars": len(df.columns), "waves": P.get("waves"),
            "pooled": P.get("pooled"), "pooled_note": P.get("pooled_note")}


def main():
    keys = sys.argv[1:] or sorted(f[:-3] for f in os.listdir(REC)
                                  if f.endswith(".py") and not f.startswith("_"))
    res = {}
    for k in keys:
        try:
            res[k] = run(k)
            r = res[k]
            mark = "OK " if abs(r["n_diff"]) == 0 else "≈  " if abs(r["n_diff"]) <= 0.02*max(1,r["n_paper"]) else "!! "
            print(f"  {mark}{k:<26} 복원 {r['n_reconstructed']:>7,}  논문 {r['n_paper']:>7,}  "
                  f"차이 {r['n_diff']:>+6,} ({pct(r['n_reconstructed'], r['n_paper'])})")
        except Exception as e:
            print(f"  ×  {k:<26} 실패 — {e}")
            traceback.print_exc(limit=2)
    os.makedirs(os.path.join(PROJ, "results", "derived"), exist_ok=True)
    json.dump(res, open(os.path.join(PROJ, "results", "derived", "reproduction.json"), "w"),
              ensure_ascii=False, indent=1)
    print(f"\n  → results/reproduction/<key>/ · results/derived/reproduction.json")


if __name__ == "__main__":
    main()
