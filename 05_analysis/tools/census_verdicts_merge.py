"""검토자(사람·에이전트)가 쓴 results/derived/review/verdict_*.json 을 verdicts.json 에 합친다.

    python tools/census_verdicts_merge.py

입력 한 항목: {"uid":…, "verdict":"INCLUDE|INCLUDE_ADJACENT|EXCLUDE|UNCERTAIN", "reason":…, "category":…,
              "ml_methods":[…], "task":…, "knhanes_role":…, "outcome":…}
같은 uid 가 여러 파일에 있으면 나중 파일이 이긴다 (파일명 정렬순).
"""
import glob, sys
from collections import Counter
sys.path.insert(0, __import__("os").path.dirname(__file__))
from common import *


def main():
    vp = os.path.join(DER, "verdicts.json")
    V = load(vp) if os.path.exists(vp) else {}
    files = sorted(glob.glob(os.path.join(DER, "review", "verdict_*.json")))
    n = 0
    for f in files:
        try:
            items = load(f)
        except Exception as e:
            print(f"  !! {os.path.basename(f)} 파싱 실패 {e}"); continue
        for it in items:
            if not it.get("uid") or it.get("verdict") not in ("INCLUDE", "INCLUDE_ADJACENT", "EXCLUDE", "UNCERTAIN"):
                continue
            it["reviewed_on"] = it.get("reviewed_on") or time.strftime("%Y-%m-%d")
            it["source_file"] = os.path.basename(f)
            V[it["uid"]] = it; n += 1
    dump(V, vp)
    c = Counter(v["verdict"] for v in V.values())
    print(f"  파일 {len(files)} · 항목 {n} · 누적 {len(V)} → {dict(c)}")


if __name__ == "__main__":
    main()
