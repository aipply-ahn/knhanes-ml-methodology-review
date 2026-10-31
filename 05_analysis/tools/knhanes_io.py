"""KNHANES 원시자료 적재 — 논문 재현용.

    from knhanes_io import load_year, available_years

`data/KNHANES/HN{yy}_ALL(SAS).zip` 을 필요할 때 풀어 `data/KNHANES/extracted/` 에 두고,
최초 1회 parquet 으로 캐시해 이후 적재를 빠르게 한다. 원본 zip 은 건드리지 않는다.
"""
import os, re, glob, zipfile
import pandas as pd

PROJ = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
RAW = os.path.join(PROJ, "data", "KNHANES")
EXT = os.path.join(RAW, "extracted")
CACHE = os.path.join(RAW, "cache")


def _yy(year):
    """2010 → '10', 1998 → '98'."""
    return f"{year % 100:02d}"


def available_years():
    """ALL 주자료를 가진 조사연도."""
    ys = set()
    for p in glob.glob(os.path.join(RAW, "*.zip")) + glob.glob(os.path.join(RAW, "*.sas7bdat")):
        m = re.search(r"hn(\d{2})[_\-]?all", os.path.basename(p), re.I)
        if m:
            n = int(m.group(1))
            ys.add(1900 + n if n >= 90 else 2000 + n)
    return sorted(ys)


def _find_sas(year):
    yy = _yy(year)
    for p in (os.path.join(EXT, f"hn{yy}_all.sas7bdat"), os.path.join(RAW, f"hn{yy}_all.sas7bdat")):
        if os.path.exists(p): return p
    for z in glob.glob(os.path.join(RAW, "*.zip")):
        if re.search(rf"hn{yy}[_\-]?all", os.path.basename(z), re.I):
            os.makedirs(EXT, exist_ok=True)
            with zipfile.ZipFile(z) as f:
                for n in f.namelist():
                    if n.lower().endswith(".sas7bdat"):
                        f.extract(n, EXT)
                        src = os.path.join(EXT, n)
                        dst = os.path.join(EXT, os.path.basename(n).lower())
                        if src != dst: os.replace(src, dst)
                        return dst
    return None


def _harmonize(df, year):
    """연도마다 다른 표기를 맞춘다 — 식별자는 1998·2001·2007–2015 가 id, 나머지가 ID 다."""
    df.columns = [c.strip() for c in df.columns]
    if "ID" not in df.columns and "id" in df.columns:
        df = df.rename(columns={"id": "ID"})
    if "year" not in df.columns:
        df["year"] = year
    return df


def load_module(year, name):
    """DXA·EYE·ENT·OE 같은 부가 모듈. 주자료와 같은 방식으로 표준화한다."""
    yy = _yy(year)
    for p in (os.path.join(RAW, f"hn{yy}_{name}.sas7bdat"), os.path.join(EXT, f"hn{yy}_{name}.sas7bdat")):
        if os.path.exists(p):
            return _harmonize(pd.read_sas(p, encoding="latin-1"), year)
    for z in glob.glob(os.path.join(RAW, "*.zip")):
        if re.search(rf"hn{yy}[_\-]?{name}", os.path.basename(z), re.I):
            os.makedirs(EXT, exist_ok=True)
            with zipfile.ZipFile(z) as f:
                for n in f.namelist():
                    if n.lower().endswith(".sas7bdat"):
                        f.extract(n, EXT)
                        return _harmonize(pd.read_sas(os.path.join(EXT, n), encoding="latin-1"), year)
    raise FileNotFoundError(f"{year}년 {name} 모듈을 찾지 못했다")


def load_year(year, columns=None):
    """한 조사연도의 주자료를 DataFrame 으로. columns 를 주면 그 열만 돌려준다."""
    os.makedirs(CACHE, exist_ok=True)
    pq = os.path.join(CACHE, f"hn{_yy(year)}_all.parquet")
    if not os.path.exists(pq):
        src = _find_sas(year)
        if src is None: raise FileNotFoundError(f"{year}년 ALL 주자료를 찾지 못했다")
        df = pd.read_sas(src, encoding="latin-1")
        df = _harmonize(df, year)
        df.to_parquet(pq, index=False)
    df = pd.read_parquet(pq, columns=columns) if columns else pd.read_parquet(pq)
    return df


def find_vars(year, pattern):
    """변수명을 정규식으로 찾는다 — 코드북 없이 탐색할 때."""
    df = load_year(year)
    return [c for c in df.columns if re.search(pattern, c, re.I)]
