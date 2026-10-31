"""원고 수치를 자료에 맞춰 자동 동기화한다.

    python tools/sync_numbers.py            # 무엇이 바뀌는지만 보여준다
    python tools/sync_numbers.py --apply    # 실제로 고친다

`tools/verify_numbers.py` 가 이미 (이름, 기대값, 정규식) 목록을 갖고 있다. 그 정규식의 첫 포획
그룹만 기대값으로 바꾼다. 문장은 건드리지 않고 숫자만 갈아 끼우므로, 코퍼스가 바뀔 때마다
손으로 스무 군데를 고치는 일을 없앤다.

포획 그룹이 여러 곳에 걸릴 수 있는 문장은 검증 정규식이 이미 고유하게 잡도록 쓰여 있다.
바꾼 뒤에는 반드시 verify_numbers.py 로 재확인한다.
"""
import os, sys, re
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import verify_numbers as V
from common import PROJ

TARGETS = [("manuscript/submission/main.tex", V.CHECKS, "영문"),
           ("manuscript/submission/main_ko.tex", V.KO_CHECKS, "한글"),
           ("manuscript/submission/main.tex", V.SCOPE_CHECKS, "범위축")]


def main():
    apply = "--apply" in sys.argv
    total = 0
    for rel, checks, label in TARGETS:
        path = os.path.join(PROJ, rel)
        src = open(path).read()
        changed = []
        for name, want, pat in checks:
            m = re.search(pat, src)
            if not m:
                print(f"  ?  {label} {name:<22} 정규식이 원고에서 안 잡힘 — 문장을 확인할 것")
                continue
            got = m.group(1)
            if str(want) == got:
                continue
            a, b = m.start(1), m.end(1)
            src = src[:a] + str(want) + src[b:]
            changed.append((name, got, want))
        for name, got, want in changed:
            print(f"  →  {label} {name:<22} {got} → {want}")
        if changed and apply:
            open(path, "w").write(src)
        total += len(changed)
    print(f"\n  {'적용' if apply else '예상'} {total}건" + ("" if apply else "  (--apply 로 실제 반영)"))


if __name__ == "__main__":
    main()
