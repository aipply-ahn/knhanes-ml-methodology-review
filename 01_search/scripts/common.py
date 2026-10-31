"""공통 — 경로·HTTP·키 생성. 모든 census 도구가 import 한다."""
import json, os, re, time, unicodedata, urllib.parse, urllib.request

PROJ = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
RAW = os.path.join(PROJ, "results", "raw")
DER = os.path.join(PROJ, "results", "derived")
REF = os.path.join(PROJ, "references")
MAILTO = os.environ.get("CONTACT_EMAIL", "your-email@example.org")
UA = f"knhanes-ml-review/1.0 (mailto:{MAILTO})"
TODAY = time.strftime("%Y%m%d")

# KNHANES 명칭 변형 — 검색식은 이 목록에서 만든다
KNHANES_TERMS = [
    "KNHANES",
    "Korea National Health and Nutrition Examination Survey",
    "Korean National Health and Nutrition Examination Survey",
]


def get(url, tries=5, raw=False, timeout=90, headers=None):
    h = {"User-Agent": UA}
    if headers:
        h.update(headers)
    req = urllib.request.Request(url, headers=h)
    for i in range(tries):
        try:
            with urllib.request.urlopen(req, timeout=timeout) as r:
                b = r.read()
                return b if raw else json.loads(b)
        except Exception as e:
            code = getattr(e, "code", None)
            if i == tries - 1:
                raise
            time.sleep(min(90, 5 * 2 ** i) if code == 429 else 3 * (i + 1))


def q(s):
    return urllib.parse.quote(s, safe="")


def norm_doi(d):
    if not d:
        return None
    d = d.strip().lower()
    d = re.sub(r"^https?://(dx\.)?doi\.org/", "", d)
    return d or None


def norm_title(t):
    t = unicodedata.normalize("NFKD", t or "").lower()
    t = re.sub(r"<[^>]+>", " ", t)
    t = re.sub(r"[^a-z0-9 ]+", " ", t)
    return re.sub(r"\s+", " ", t).strip()


STOP = {"a", "an", "the", "of", "in", "on", "for", "and", "or", "to", "with", "using",
        "from", "by", "among", "based", "via", "is", "are", "its", "at", "as", "vs",
        "korean", "korea", "national", "health", "nutrition", "examination", "survey",
        "knhanes", "study", "data", "analysis", "adults", "population"}


def bibkey(author, year, title):
    """firstauthor + year + 첫 의미단어. medimage 규칙과 같다."""
    first = (author or "anon").split(" and ")[0].strip()
    if "," in first:                      # "Kim, Sujin"
        last = first.split(",")[0].strip()
    else:
        toks = first.split()
        # "Kim S" / "Kim SJ" (EPMC fullName) → 첫 토큰 · "Sujin Kim" (OpenAlex) → 마지막 토큰
        last = toks[0] if len(toks) >= 2 and re.fullmatch(r"[A-Z]{1,3}", toks[-1]) else (toks[-1] if toks else "anon")
    last = re.sub(r"[^a-z]", "", unicodedata.normalize("NFKD", last).encode("ascii", "ignore").decode().lower()) or "anon"
    w = next((x for x in norm_title(title).split() if x not in STOP and len(x) > 2), "manuscript")
    return f"{last}{year or 'nd'}{w}"


def dump(obj, path):
    os.makedirs(os.path.dirname(path), exist_ok=True)
    json.dump(obj, open(path, "w"), ensure_ascii=False, indent=1)
    print(f"  saved {os.path.relpath(path, PROJ)}")


def load(path):
    return json.load(open(path))
