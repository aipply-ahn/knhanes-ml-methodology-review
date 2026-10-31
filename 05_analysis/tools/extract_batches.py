"""추출 배치 생성 — INCLUDE·INCLUDE_ADJACENT 논문을 md 크기 기준으로 나눈다.

    python tools/extract_batches.py [--per 7] [--tag ext1]

이미 data/extraction/<key>.json 이 있으면 뺀다. 출력 results/derived/review/extract_<tag>_<nn>.json
"""
import sys
sys.path.insert(0, __import__("os").path.dirname(__file__))
from common import *


def main():
    per = int(sys.argv[sys.argv.index("--per") + 1]) if "--per" in sys.argv else 7
    tag = sys.argv[sys.argv.index("--tag") + 1] if "--tag" in sys.argv else "ext1"
    R = load(os.path.join(REF, "refs.json"))
    out = os.path.join(DER, "review"); os.makedirs(out, exist_ok=True)
    done = set(f[:-5] for f in os.listdir(os.path.join(PROJ, "data", "extraction"))) if os.path.isdir(os.path.join(PROJ, "data", "extraction")) else set()
    rows = []
    for r in R:
        if r["verdict"] not in ("INCLUDE", "INCLUDE_ADJACENT") or r["key"] in done:
            continue
        p = os.path.join(REF, "md", f"{r['key']}.md")
        if not os.path.exists(p):
            continue
        full = "full_text: true" in open(p, encoding="utf-8").read(600)
        rows.append(dict(key=r["key"], verdict=r["verdict"], title=r.get("title"), year=r.get("year"),
                         md=os.path.abspath(p), chars=os.path.getsize(p), full_text=full))
    fulls = sorted([x for x in rows if x["full_text"]], key=lambda x: x["chars"])
    abss = [x for x in rows if not x["full_text"]]
    batches, cur, size = [], [], 0
    for x in fulls:                       # 글자수 합 ~450k (≈110k 토큰) 또는 per 건 단위
        if cur and (len(cur) >= per or size + x["chars"] > 450_000):
            batches.append(cur); cur, size = [], 0
        cur.append(x); size += x["chars"]
    if cur: batches.append(cur)
    for i in range(0, len(abss), 20):
        batches.append(abss[i:i + 20])
    for i, b in enumerate(batches, 1):
        json.dump(b, open(os.path.join(out, f"extract_{tag}_{i:02d}.json"), "w"), ensure_ascii=False, indent=1)
    print(f"  전문 {len(fulls)} · 초록만 {len(abss)} → 배치 {len(batches)} (extract_{tag}_NN.json)")
    for i, b in enumerate(batches, 1):
        print(f"   {i:02d}: {len(b)}건 {sum(x['chars'] for x in b)//1000}k자 {'full' if b[0]['full_text'] else 'abs'}")


if __name__ == "__main__":
    main()
