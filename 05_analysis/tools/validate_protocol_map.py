"""프로토콜 판정 규칙의 정확도 검증 — 전문을 사람이 직접 읽어 만든 정답과 대조.

    python tools/validate_protocol_map.py

정답(TRUTH)은 2026-09-05 에 전문을 직접 읽고 만든 8편이다. 규칙을 고칠 때마다 이 검증을
돌려 일치율을 확인한다. 일치율이 낮으면 그 지표는 정규식으로 발표할 수 없다.
"""
import sys, os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import protocol_map as pm

NAMES = ["단계별인원", "절단값", "결측코드", "누출통제", "초매개변수", "검증구분", "신뢰구간"]
TRUTH = {
 "chung2014screening":  [True, True, True, True, True, True, False],
 "kim2013osteoporosis": [False, True, False, False, True, True, False],
 "oh2015artificial":    [True, True, False, False, True, True, True],
 "lee2019predictive":   [False, True, True, False, False, True, False],
 "shim2020application": [False, True, False, False, True, True, False],
 "park2021application": [True, True, True, False, True, True, False],
 "kim2023usefulness":   [True, True, False, False, False, True, True],
 "kim2024predictiona":  [False, False, True, True, True, True, False],
}


def main():
    per = {n: [0, 0, 0] for n in NAMES}   # 일치·과대·누락
    print(f"  {'논문':<24}" + "".join(f"{n:>9}" for n in NAMES))
    for k, truth in TRUTH.items():
        t = pm.FT.get(k)
        if not t:
            print(f"  {k:<24} 전문 없음"); continue
        line = f"  {k:<24}"
        for i, (_, fn) in enumerate(pm.METRICS):
            got, exp = bool(fn(t, k)), truth[i]
            tag = "OK" if got == exp else ("과대" if got else "누락")
            per[NAMES[i]][0 if got == exp else (1 if got else 2)] += 1
            line += f"{tag:>9}"
        print(line)
    n = len(TRUTH)
    print(f"\n  {'지표':<14}{'일치':>6}{'과대':>6}{'누락':>6}{'일치율':>8}")
    tot = 0
    for name in NAMES:
        ok, fp, fn_ = per[name]; tot += ok
        print(f"  {name:<14}{ok:>6}{fp:>6}{fn_:>6}{100*ok/n:>7.0f}%")
    print(f"\n  전체 일치 {tot}/{n*len(NAMES)} = {100*tot/(n*len(NAMES)):.0f}%")
    return tot / (n * len(NAMES))


if __name__ == "__main__":
    main()
