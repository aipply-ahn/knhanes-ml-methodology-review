"""Number macros for the TRIPOD+AI requirement re-coding (results/oct_search/coding_legacy4; 52 requirements x 217 core studies).
Injected into the v3 and v4 drafts by assemble.py."""
import json, os, statistics
ROOT = os.path.abspath(os.path.join(os.path.dirname(os.path.abspath(__file__)), "../../.."))
L4 = os.path.join(ROOT, "results/oct_search/coding_legacy4")
def macros():
    R = json.load(open(f"{L4}/tripod_requirement_counts.json"))
    P = {k: 100 * v.get("met", 0) / v["applicable"] for k, v in R.items()}
    pairs = {r[0] + "|" + r[1]: r for r in json.load(open(f"{L4}/req_vs_refined.json"))}
    fin = [json.loads(l) for l in open(f"{L4}/final_items.jsonl")]
    agree = sum(r["how"] == "agree_r1" for r in fin)
    def pr(k, c):   # requirement met, and of those the refined item met
        r = pairs[f"{k}|{c}"]; return r[3], r[4], f"{100 * r[4] / r[3]:.1f}"
    m = {"kReqN": len(R), "kReqCodings": f"{len(fin):,}", "kReqAgreeFirst": f"{agree:,}", "kReqAgreeFirstPct": f"{100 * agree / len(fin):.1f}",
         "kReqBelowHalf": sum(p < 50 for p in P.values()), "kReqMedianPct": f"{statistics.median(P.values()):.1f}",
         "kReqRegistration": R["19a"]["met"], "kReqRegistrationPct": f"{P['19a']:.1f}",
         "kReqSampleSize": R["9a"]["met"], "kReqSampleSizePct": f"{P['9a']:.1f}"}
    for name, k, c in (("Design", "4b", "4b′"), ("Prep", "11a", "11a′"), ("Outcome", "6a", "6a′"), ("Metrics", "14b", "14b″")):
        a, b, p = pr(k, c); m[f"kReq{name}Met"] = a; m[f"kReq{name}Refined"] = b; m[f"kReq{name}RefinedPct"] = p
    m["kReqKept"] = 29
    return "\n".join(rf"\newcommand{{\{k}}}{{{v}}}" for k, v in m.items())
if __name__ == "__main__": print(macros())
