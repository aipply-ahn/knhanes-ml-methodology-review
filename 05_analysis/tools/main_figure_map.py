"""Main-figure numbers of the journal version in use, applied to text that cites main figures (supplement, Additional
Data 1 notes). JCE version (2026-10-24): the BMC Figures 4 and 6 repeated Table 1 and were dropped; Figure 5 became
Figure 4 and Figure 7 became Figure 5. Set MAP = {} to restore the BMC numbering."""
import re

MAP = {"4": None, "5": "4", "6": None, "7": "5"}  # None: cite Table 1


def remap(text):
    def sub(m):
        new = MAP.get(m.group(2), m.group(2))
        return "Table 1" if new is None else f"Figure{m.group(1)}{new}{m.group(3)}"
    out = re.sub(r"(?<!Supplementary )(?<!Supplementary~)\bFigure( |~)([1-7])([A-J]?)\b", sub, text)
    return re.sub(r"Table 1 and Table 1", "Table 1", out)


def internal_header(name):
    """Header of a built workbook -> internal column name (review tools key overrides by the BMC-numbered names)."""
    return {"Outcome group (Figure 4)": "Outcome group (Figure 5)",
            "Harmonised variables (Figure 4)": "Harmonised variables (Figure 5)"}.get(name, name) if MAP else name
