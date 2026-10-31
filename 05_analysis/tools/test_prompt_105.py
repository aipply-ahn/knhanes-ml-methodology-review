#!/usr/bin/env python3
"""Prompt 105 (review v43): criterion A re-screen is recorded; manuscript and selection records stay unchanged until
the new studies are extracted."""
import json
import unittest
import sys
sys.path.insert(0, str(__import__('pathlib').Path(__file__).resolve().parent))
from revision_artifact_checks import current  # prompt 119
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
R = json.loads((ROOT / "results/derived/criterion_a_rescreen.json").read_text())


class Prompt105(unittest.TestCase):
    def test_rescreen(self):
        p = R["projection"]
        self.assertEqual((p["added"], p["dropped"], p["unresolved"], p["included_after_before_family_linkage"]), (33, 3, 1, 250))
        self.assertEqual(sum(p["added_by_period"].values()), 33)
        self.assertEqual(set(R["drop_from_included"]), {"KHM156", "KHM073", "KHM129"})
        self.assertIn("KHM053", R["kept_after_check"])
        self.assertIn("penalty", R["criterion"]); self.assertIn("Christodoulou", R["criterion"])
        self.assertTrue(all(r["previous_verdict"] == "INCLUDE_ADJACENT" for r in R["new_include"]))

    def test_manuscript_untouched(self):
        rec = ROOT / "prompts/implementation_records/prompt_105/before_sha256.txt"
        import hashlib
        for line in rec.read_text().splitlines():
            h, f = line.split()
            # Prompt 106 extracted the new studies and rewrote the manuscripts and records on purpose; those files must
            # carry a declared prompt-106 amendment from this exact prompt-105 state.
            amend = json.loads((ROOT / "prompts/implementation_records/prompt_106/artifact_amendments.json").read_text())  # Prompt 106
            a107 = json.loads((ROOT / "prompts/implementation_records/prompt_107/artifact_amendments.json").read_text())
            now = hashlib.sha256((ROOT / current(f)).read_bytes()).hexdigest()  # Prompt 106  # prompt 119: moved files
            mid = amend.get(f, {}).get("after_sha256") if amend.get(f, {}).get("before_sha256") == h else h
            a108 = json.loads((ROOT / "prompts/implementation_records/prompt_108/artifact_amendments.json").read_text())
            m107 = a107[f]["after_sha256"] if a107.get(f, {}).get("before_sha256") == mid else mid
            m108 = a108[f]["after_sha256"] if a108.get(f, {}).get("before_sha256") == m107 else m107  # prompt 109
            a109 = json.loads((ROOT / "prompts/implementation_records/prompt_109/artifact_amendments.json").read_text())  # prompt 109
            m109 = a109[f]["after_sha256"] if a109.get(f, {}).get("before_sha256") == m108 else m108  # prompt 110
            a110 = json.loads((ROOT / "prompts/implementation_records/prompt_110/artifact_amendments.json").read_text())  # prompt 110
            m110 = a110[f]["after_sha256"] if a110.get(f, {}).get("before_sha256") == m109 else m109  # prompt 111
            a111 = json.loads((ROOT / "prompts/implementation_records/prompt_111/artifact_amendments.json").read_text())  # prompt 111
            m111 = a111[f]["after_sha256"] if a111.get(f, {}).get("before_sha256") == m110 else m110  # prompt 112
            a112 = json.loads((ROOT / "prompts/implementation_records/prompt_112/artifact_amendments.json").read_text())  # prompt 112
            m112 = a112[f]["after_sha256"] if a112.get(f, {}).get("before_sha256") == m111 else m111  # prompt 113
            a113 = json.loads((ROOT / "prompts/implementation_records/prompt_113/artifact_amendments.json").read_text())  # prompt 113
            m113 = a113[f]["after_sha256"] if a113.get(f, {}).get("before_sha256") == m112 else m112  # prompt 114
            a114 = json.loads((ROOT / "prompts/implementation_records/prompt_114/artifact_amendments.json").read_text())  # prompt 114
            m114 = a114[f]["after_sha256"] if a114.get(f, {}).get("before_sha256") == m113 else m113  # prompt 115
            a115 = json.loads((ROOT / "prompts/implementation_records/prompt_115/artifact_amendments.json").read_text())  # prompt 115
            m115 = a115[f]["after_sha256"] if a115.get(f, {}).get("before_sha256") == m114 else m114  # prompt 116
            a116 = json.loads((ROOT / "prompts/implementation_records/prompt_116/artifact_amendments.json").read_text())  # prompt 116
            m116 = a116[f]["after_sha256"] if a116.get(f, {}).get("before_sha256") == m115 else m115  # prompt 117
            a117 = json.loads((ROOT / "prompts/implementation_records/prompt_117/artifact_amendments.json").read_text())  # prompt 117
            m117 = a117[f]["after_sha256"] if a117.get(f, {}).get("before_sha256") == m116 else m116  # prompt 119
            a119 = json.loads((ROOT / "prompts/implementation_records/prompt_119/artifact_amendments.json").read_text())  # prompt 119
            self.assertTrue(now in (h, mid, m107, m108, m109, m110, m111, m112, m113, m114, m115, m116, m117) or (a119.get(f, {}).get("before_sha256") == m117 and a119[f]["after_sha256"] == now), f)  # Prompt 107  # Prompt 108  # prompt 109  # prompt 110  # prompt 111  # prompt 112


if __name__ == "__main__":
    unittest.main()
