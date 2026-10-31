"""v12: LaTeX for Table 1 from tools/checklist_v12.py (one row per TRIPOD+AI component or checklist item)."""
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent))
import checklist_v12 as CK

NOTE = {"K": ("유지", "Retained"), "R": ("세분화", "Refined"), "RS": ("세분화(특화)", "Refined (KNHANES)"), "N": ("신설", "New"), "NS": ("신설(특화)", "New (KNHANES)")}


class _MS:  # build() only needs the callables, not the data
    first = staticmethod(lambda d, k: None); has = staticmethod(lambda d, k, v: False); flat_values = staticmethod(lambda d, k: [])


def rows():
    return CK.build(_MS)


def table(ko):
    j = 0 if ko else 1
    L, last = [], None
    for it in rows():
        key, cko, cen, oko, oen, note, repro, met, app = it
        if key != last and last is not None:
            L.append("\\addlinespace[1pt]")
            if isinstance(key, str) and isinstance(last, int):
                L.append("\\midrule")
        if isinstance(key, int):
            head = f"{key}. {CK.TRIPOD[key - 1][j]}" if key != last else ""
            comp = cko if ko else cen
        else:
            head = (("{}(해당 없음) " if ko else "{}(None) ") + CK.GROUPS[key][j]) if key != last else ""
            comp = "--" if key != last else ""
        item = (oko if ko else oen) if oko else "\\centering{}''"  # same as the component: ditto mark
        if met is None and note != "K":
            item += "$^{\\S}$"
        L.append(f"{head} & {comp} & {item} & {'$\\bullet$' if repro else ''} & \\mbox{{{NOTE[note][j]}}} \\\\")
        last = key
    head = ("\\textbf{TRIPOD+AI 항목} & \\textbf{TRIPOD+AI 구성요소} & \\textbf{KNHANES 체크리스트 항목} & \\textbf{재현} & \\textbf{비고}" if ko else
            "\\textbf{TRIPOD+AI item} & \\textbf{TRIPOD+AI component} & \\textbf{KNHANES checklist item} & \\textbf{Repro.} & \\textbf{Note}")
    cap = ("TRIPOD+AI 항목·구성요소와 KNHANES 체크리스트 항목의 대조" if ko else "TRIPOD+AI items and components compared with the KNHANES checklist items")
    foot = ("{\\fontsize{6.4}{7.4}\\selectfont TRIPOD+AI 구성요소는 이 검토의 프로토콜에서 각 TRIPOD+AI 유래 요소의 완전 보고 여부를 판정한 필수 구성요소이다. 체크리스트 항목은 한 행에 한 가지 정보만 담도록 구성요소를 나눈 것이며, ''는 구성요소와 같은 항목이다. 재현($\\bullet$): 같은 KNHANES 원자료로 분석 표본, 변수, 모형, 성능 수치를 다시 만들어 내는 데 필요한 항목. 유지: 구성요소를 그대로 씀. 세분화: 구성요소를 나누거나 더 구체화함. 신설: TRIPOD+AI에 대응 구성요소가 없음. (특화): KNHANES의 반복 횡단면 확률표본조사 특성 때문에 필요함. TRIPOD+AI는 보고 지침이며 점수 도구가 아니다. 체크리스트 점수(그림~\\ref{fig:refined})는 적용 가능한 항목 중 보고한 비율로 기술적 지표이다. 일부 항목은 해당 단계를 적용한 연구에만 적용하며(예: 범주화 기준값은 결과변수를 범주화한 연구, 탐색 공간은 튜닝한 연구), 변수중요도와 순위 이후 분석 항목은 순위를 보고한 연구에만 적용한다. 저자가 이 검토의 결과와 기존 보고 지침을 바탕으로 제안한 체크리스트로, TRIPOD+AI와 PROBAST+AI를 대체하지 않고 보완한다. $^{\\S}$ 이 검토에서 코딩하지 않아 점수에 넣지 않음. AUROC, 수신자 조작 특성 곡선 아래 면적; PSU, 일차표본추출단위.\\par}" if ko else
            "{\\fontsize{6.4}{7.4}\\selectfont TRIPOD+AI components are the required components used in this review's protocol to judge whether each TRIPOD+AI-derived element was completely reported. Checklist items split the components so that each row holds one piece of information; '' marks an item identical to the component. Repro. ($\\bullet$): needed to rebuild the analytic sample, variables, model and performance estimates from the same KNHANES data. Retained: the component used as it is. Refined: a component divided or made more specific. New: no corresponding TRIPOD+AI component. (KNHANES): needed because KNHANES is a repeated cross-sectional probability survey. TRIPOD+AI is a reporting guideline, not a scoring tool. The checklist score (Figure~\\ref{fig:refined}) is the percentage of applicable items reported and is descriptive. Some items apply only when the step was applied (for example, the cut-off value when the outcome was categorised, the search space when tuning was done), and the items on variable importance and analyses after the ranking apply only when a ranking was reported. The checklist was proposed by the author from the findings of this review and existing reporting guidance and complements rather than replaces TRIPOD+AI and PROBAST+AI. $^{\\S}$ Not coded in this review and not scored. AUROC, area under the receiver operating characteristic curve; PSU, primary sampling unit.\\par}")
    W = (">{\\RaggedRight\\arraybackslash}p{0.18\\textwidth}>{\\RaggedRight\\arraybackslash}p{0.17\\textwidth}>{\\RaggedRight\\arraybackslash}p{0.355\\textwidth}"
         ">{\\centering\\arraybackslash}p{0.06\\textwidth}>{\\RaggedRight\\arraybackslash}p{0.16\\textwidth}")
    hdr = "\\toprule\n" + head + " \\\\\n\\midrule\n"
    return ("\\begingroup\\renewcommand{\\baselinestretch}{1}\\fontsize{6.6}{7.6}\\selectfont\\setlength{\\tabcolsep}{3pt}\n"
            "\\begin{longtable}{@{}" + W + "@{}}\n\\caption{" + cap + "}\\label{tab:checklist}\\\\\n" + hdr + "\\endfirsthead\n" + hdr + "\\endhead\n\\bottomrule\n\\endlastfoot\n"
            + "\n".join(L).replace("\\midrule\n{}", "\\midrule\n{}") + "\n\\end{longtable}\n" + foot + "\n\\endgroup\n")


if __name__ == "__main__":
    R = rows()
    from collections import Counter
    print(Counter(r[5] for r in R), "repro", sum(r[6] for r in R), "scored", sum(r[7] is not None for r in R),
          "refined TRIPOD items", sorted({r[0] for r in R if r[5] in ("R", "RS")}))
