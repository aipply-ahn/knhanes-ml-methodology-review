"""KDCA 국민건강영양조사 홈페이지 — 저자 수동등록 논문목록 전체 수집.

    python tools/census_kdca.py

화면: https://knhanes.kdca.go.kr/knhanes/thss/thssInfLst.do  (원시자료 → 논문 → 논문목록)
실제 데이터는 Vue 앱이 POST /knhanes/thss/findThssInfList.json 으로 받는다 (10건/페이지).
공통코드(논문유형·연구주제분야)는 /thss/findThssCmmnCodeList.json.

결과: results/raw/kdca_<date>.json
"""
import sys, time, urllib.request
sys.path.insert(0, __import__("os").path.dirname(__file__))
from common import *

BASE = "https://knhanes.kdca.go.kr/knhanes"
H = {"User-Agent": "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/125.0 Safari/537.36",
     "Content-Type": "application/json;charset=UTF-8", "Accept": "application/json",
     "X-Requested-With": "XMLHttpRequest", "Referer": f"{BASE}/thss/thssInfLst.do"}


def post(path, body):
    req = urllib.request.Request(f"{BASE}{path}", data=json.dumps(body).encode(), headers=H)
    for i in range(5):
        try:
            with urllib.request.urlopen(req, timeout=60) as r:
                return json.loads(r.read())
        except Exception:
            if i == 4: raise
            time.sleep(3 * (i + 1))


def main():
    codes = post("/thss/findThssCmmnCodeList.json", {})["data"]
    typ = {c["code"]: c["codeNm"] for c in codes["rschSeCdLst"]}
    fld = {c["code"]: c["codeNm"] for c in codes["thssLstClsfCdLst"]}
    print("  연구주제분야 코드:", fld)
    first = post("/thss/findThssInfList.json", dict(pg=1, st="", sb=1, menuId="", rschTpcFldCd=0))["data"]
    count, pages = first["count"], first["pageCount"]
    print(f"  총 {count} 건 · {pages} 페이지")
    items = list(first["list"])
    for pg in range(2, pages + 1):
        d = post("/thss/findThssInfList.json", dict(pg=pg, st="", sb=1, menuId="", rschTpcFldCd=0))["data"]
        items += d["list"]
        if pg % 20 == 0 or pg == pages:
            print(f"    page {pg}/{pages} · {len(items)}", flush=True)
        time.sleep(0.25)
    seen, recs = set(), []
    for v in items:
        if v["thssNo"] in seen: continue
        seen.add(v["thssNo"])
        f = v.get("rschTpcFld") or ""
        recs.append(dict(
            kdca_no=v["thssNo"], rnum=v.get("rnum"), lang=v.get("thssWrtLgug"),
            title_ko=v.get("kornThssTtl"), title_en=v.get("engThssTtl"),
            title=v.get("engThssTtl") or v.get("kornThssTtl"),
            author_ko=v.get("kornAut"), author_en=v.get("engAut"),
            keywords_ko=v.get("kornKywd"), keywords_en=v.get("engKywd"),
            paper_type=v.get("thssTypNm") or typ.get(v.get("rschSe")), degree=v.get("thssDgr"),
            pub_ym=v.get("pblcnYm"), year=int(v["pblcnYm"][:4]) if (v.get("pblcnYm") or "")[:4].isdigit() else None,
            journal=v.get("srchAcjrnlNm"), field_codes=f,
            fields=[fld.get(c, c) for c in f.split(",") if c] if f else [],
            url=v.get("orgnlLinkUrl"), registered=v.get("wrtDt"), modified=v.get("mdfcnDt")))
    out = dict(source="KDCA KNHANES 논문목록 (저자 등록)", url=f"{BASE}/thss/thssInfLst.do",
               api=f"{BASE}/thss/findThssInfList.json", fetched_on=time.strftime("%Y-%m-%d"),
               count_reported=count, n_unique=len(recs), codes=dict(type=typ, field=fld), records=recs)
    dump(out, os.path.join(RAW, f"kdca_{TODAY}.json"))
    print(f"  고유 {len(recs)} / 보고 {count}")


if __name__ == "__main__":
    main()
