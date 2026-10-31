"""v14: Table 1 (core checklist with criteria) from tools/checklist_v14.py."""
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent))
import checklist_v14 as CK
from checklist_v12 import TRIPOD


class _MS:
    first = staticmethod(lambda d, k: None); has = staticmethod(lambda d, k, v: False); flat_values = staticmethod(lambda d, k: [])


def ordered():
    R = CK.build(_MS)
    key = lambda r: (r[0] if isinstance(r[0], int) else 100 + list(CK.GROUPS).index(r[0]))
    return sorted(R, key=key)


def table(ko):
    j = 0 if ko else 1
    L, last = [], None
    for n, it in enumerate(ordered(), 1):
        el, iko, ien, cko, cen, st, ty, met, app = it
        if last is not None and el != last:
            L.append("\\addlinespace[1.5pt]")
            if isinstance(el, str) and isinstance(last, int):
                L.append("\\midrule")
        if el != last:
            head = f"{el}. {TRIPOD[el - 1][j]}" if isinstance(el, int) else (("{}(해당 없음) " if ko else "{}(None) ") + CK.GROUPS[el][j])
        else:
            head = ""
        name = (iko if ko else ien) + ("$^{\\S}$" if met is None else "")
        L.append(f"{head} & {n}. {name} & {cko if ko else cen} & {CK.STAGE[st][j]} & \\mbox{{{CK.TYPE[ty][j]}}} \\\\")
        last = el
    head = ("\\textbf{TRIPOD+AI 유래 평가 요소} & \\textbf{핵심 평가항목} & \\textbf{충족(1) 판정 기준} & \\textbf{재현 단계} & \\textbf{유형}" if ko else
            "\\textbf{TRIPOD+AI-derived element} & \\textbf{Core item} & \\textbf{Criterion for meeting the item (1)} & \\textbf{Stage} & \\textbf{Type}")
    cap = ("KNHANES 기반 머신러닝 분류 연구의 재현성을 위한 TRIPOD+AI 기반 핵심 보고 체크리스트" if ko else
           "TRIPOD+AI-aligned core reporting checklist for reproducible machine learning classification studies using KNHANES")
    foot = ("{\\fontsize{6.4}{7.4}\\selectfont 왼쪽 열은 공식 TRIPOD+AI 항목이 아니라 이 검토에서 TRIPOD+AI 항목을 재구성한 19개 평가 요소이다. 각 핵심 평가항목은 하나의 보고 요구사항이며, 같은 목적(예: 결과변수를 다시 만드는 것)에 함께 필요한 정보는 한 항목으로 묶고 서로 다른 분석 행위(예: 중요도 계산과 순위 안정성 점검)는 나누었다. 각 항목은 충족(1), 미충족(0), 해당 없음(NA)으로 판정하며 부분 보고 범주를 두지 않는다. 미충족은 정보가 전혀 없다는 뜻이 아니라 요구사항을 충족하기에 불충분하다는 뜻이다. 항목은 관행이 아니라 보고를 판정한다(예: 가중치는 적용 여부와 방법 또는 쓰지 않은 근거를 보고했는지). 재현 단계: 자료(같은 원자료로 분석자료 재구성), 모형(모형과 성능 수치 재현), 중요도(변수중요도 결과 재현), 보고·해석(재현이 아니라 결과의 해석과 평가에 필요함). 유형: 구체화(TRIPOD+AI 유래 요소를 구체화함), 신설(대응 요소가 없음), (특화)(KNHANES의 반복 횡단면 확률표본조사 특성 때문에 필요함). 이 검토의 판정은 코딩된 구성요소만으로 했으므로, 판정 기준의 일부(예: 원자료 파일, 연도 간 변수 조화, 특수 응답 코드, 파이프라인 순서)는 판정에 반영되지 않았다. 점수(그림~\\ref{fig:refined})는 적용 가능한 항목 중 충족한 비율로, 재현에 필요한 정보의 보고 완전성을 나타내는 기술적 지표이며 실제 재현 가능성이나 검증된 질 점수가 아니다. 항목별 상세 보고 명세는 부록 표~\\ref{tab:spec}에 있다. 저자가 이 검토의 결과와 기존 보고 지침을 바탕으로 제안한 체크리스트로, TRIPOD+AI와 PROBAST+AI를 대체하지 않고 보완한다. $^{\\S}$ 이 검토에서 코딩하지 않아 점수에 넣지 않음. PSU, 일차표본추출단위.\\par}" if ko else
            "{\\fontsize{6.4}{7.4}\\selectfont The left column lists the 19 elements into which this review reorganised TRIPOD+AI, not official TRIPOD+AI items. Each core item is one reporting requirement: information needed together for one purpose (such as rebuilding the outcome) is bundled, and distinct analytic acts (such as computing importance and checking ranking stability) are separate. Each item is judged met (1), not met (0) or not applicable (NA), with no partly reported category; not met means insufficient to meet the requirement, not that no information was given. Items judge reporting, not practice (for example, for weights, whether and how they were applied or why not). Stage: Data (rebuilding the analysis dataset from the same raw data), Model (reproducing the model and performance estimates), Importance (reproducing the variable-importance results), Reporting (needed to interpret or appraise the results rather than to reproduce them). Type: Specified (specifies a TRIPOD+AI-derived element), New (no corresponding element), (KNHANES) (needed because KNHANES is a repeated cross-sectional probability survey). Judgements in this review used only the coded components, so parts of some criteria (such as raw data files, harmonisation across years, special response codes and pipeline order) were not judged. The score (Figure~\\ref{fig:refined}) is the percentage of applicable items met; it is a descriptive measure of the completeness of the information needed for reproduction, not verified reproducibility or a validated quality score. The detailed specification of each item is in Appendix Table~\\ref{tab:spec}. The checklist was proposed by the author from the findings of this review and existing reporting guidance and complements rather than replaces TRIPOD+AI and PROBAST+AI. $^{\\S}$ Not coded in this review and not scored. PSU, primary sampling unit.\\par}")
    W = (">{\\RaggedRight\\arraybackslash}p{0.16\\textwidth}>{\\RaggedRight\\arraybackslash}p{0.2\\textwidth}>{\\RaggedRight\\arraybackslash}p{0.395\\textwidth}"
         ">{\\RaggedRight\\arraybackslash}p{0.085\\textwidth}>{\\RaggedRight\\arraybackslash}p{0.12\\textwidth}")
    hdr = "\\toprule\n" + head + " \\\\\n\\midrule\n"
    return ("\\begingroup\\renewcommand{\\baselinestretch}{1}\\fontsize{6.6}{7.6}\\selectfont\\setlength{\\tabcolsep}{3pt}\n"
            "\\begin{longtable}{@{}" + W + "@{}}\n\\caption{" + cap + "}\\label{tab:checklist}\\\\\n" + hdr + "\\endfirsthead\n" + hdr + "\\endhead\n\\bottomrule\n\\endlastfoot\n"
            + "\n".join(L) + "\n\\end{longtable}\n" + foot + "\n\\endgroup\n")


if __name__ == "__main__":
    from collections import Counter
    R = ordered()
    print(len(R), Counter(r[5] for r in R), Counter(r[6] for r in R), "scored", sum(r[7] is not None for r in R))
