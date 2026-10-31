"""수동 판정용 배치 파일 생성 — T1·T2·T3 레코드를 results/derived/review/batch_<tier>_<nn>.json 으로 나눈다.

    python tools/census_review_batches.py [--size 40] [--tag pass3]

배치 파일명에 tag 가 붙는다. 판정 파일도 같은 tag 로 쓴다 (verdict_<tag>_<tier>_<nn>.json) —
이전 판정 파일을 덮어쓰지 않기 위해서다. verdicts.json 이 누적 원본이다.

각 레코드: uid · tier · terms · year · journal · title · abstract(초록) · keywords · lang · sources
이미 verdicts.json 에 판정이 있는 uid 는 뺀다.
"""
import sys
sys.path.insert(0, __import__("os").path.dirname(__file__))
from common import *


def main():
    size = int(sys.argv[sys.argv.index("--size") + 1]) if "--size" in sys.argv else 40
    tag = sys.argv[sys.argv.index("--tag") + 1] if "--tag" in sys.argv else time.strftime("%Y%m%d")
    C = {r["uid"]: r for r in load(os.path.join(DER, "corpus.json"))["records"]}
    S = load(os.path.join(DER, "screen.json"))
    vp = os.path.join(DER, "verdicts.json")
    V = load(vp) if os.path.exists(vp) else {}
    out = os.path.join(DER, "review")
    os.makedirs(out, exist_ok=True)
    for f in os.listdir(out):
        if f.startswith(f"batch_{tag}_"): os.remove(os.path.join(out, f))
    n = 0
    for tier in ("T1", "T2", "T3"):
        rows = [x for x in S["rows"] if x["tier"] == tier and x["uid"] not in V]
        rows.sort(key=lambda x: (-(x["year"] or 0), x["uid"]))
        for i in range(0, len(rows), size):
            b = []
            for x in rows[i:i + size]:
                r = C[x["uid"]]
                ab = re.sub(r"<[^>]+>", " ", r.get("abstract") or ""); ab = re.sub(r"\s+", " ", ab).strip()
                b.append(dict(uid=x["uid"], tier=tier, terms=x["t1"] + x["t2"] + x["t3"], year=r.get("year"),
                              journal=r.get("journal"), title=r.get("title"), title_ko=r.get("title_ko") or r.get("kdca_title_ko"),
                              abstract=ab[:3500] or None, keywords=(r.get("keywords") or [])[:15],
                              lang=r.get("lang"), sources=r.get("sources"), epmc_layer=r.get("epmc_layer")))
            p = os.path.join(out, f"batch_{tag}_{tier}_{i // size + 1:02d}.json")
            json.dump(b, open(p, "w"), ensure_ascii=False, indent=1); n += 1
        print(f"  {tier}: {len(rows)} 건 → {(len(rows) + size - 1) // size} 배치")
    print(f"  배치 {n} 개 → {os.path.relpath(out, PROJ)}/")


if __name__ == "__main__":
    main()
