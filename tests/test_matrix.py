"""Tests for the gate. Standard library only:  python3 -m unittest discover tests

The important ones are the seen-to-fail cases: each takes a matrix that passes, breaks one
thing the contract forbids, and asserts the checker refuses it. A checker that cannot fail
is not checking.
"""
import copy
import json
import pathlib
import subprocess
import sys
import tempfile
import unittest

ROOT = pathlib.Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "tools"))
import check_matrix  # noqa: E402

OUT = ROOT / "outputs"
FIXTURE = OUT / "tucker-ga-rfp-2026-016-cei-services.matrix.json"
STAGED = OUT / "codot-us50-passing-lanes-cm-rfp.matrix.json"


def load(p):
    return json.loads(p.read_text())


def problems(m, base=OUT):
    return check_matrix.check(m, base)[0]


class ShippedMatricesPass(unittest.TestCase):
    def test_every_shipped_matrix_passes(self):
        for p in sorted(OUT.glob("*.matrix.json")):
            with self.subTest(p.name):
                self.assertEqual(problems(load(p)), [])

    def test_shipped_matrices_reconcile(self):
        for p in sorted(OUT.glob("*.matrix.json")):
            m = load(p)
            _, total = check_matrix.check(m, OUT)
            self.assertTrue(check_matrix.reconciles(m, total), p.name)

    def test_same_shape_across_inputs(self):
        keys = None
        for p in sorted(OUT.glob("*.matrix.json")):
            for r in load(p)["rows"]:
                k = {x for x in r if x != "stage"}
                if keys is None:
                    keys = k
                self.assertEqual(k, keys, f"{p.name}: row shape drifted")
        self.assertEqual(keys, set(check_matrix.COLUMNS[1:]))


class SeenToFail(unittest.TestCase):
    def setUp(self):
        self.m = load(FIXTURE)

    def test_paraphrased_criterion_fails(self):
        self.m["rows"][0]["criterion"]["text"] = "Experience of staff"
        self.assertTrue(any("not verbatim" in x for x in problems(self.m)))

    def test_respelled_word_fails(self):
        r = self.m["rows"][1]["criterion"]
        r["text"] = r["text"].replace("Qualifications", "Qualification")
        self.assertTrue(any("not verbatim" in x for x in problems(self.m)))

    def test_invented_points_fail(self):
        self.m["rows"][0]["points"]["value"] = 45
        self.assertTrue(any("does not appear as a number" in x for x in problems(self.m)))

    def test_wrong_citation_fails(self):
        self.m["rows"][0]["criterion"]["cite"] = "p11:16"  # a real line, the wrong one
        self.assertTrue(any("not verbatim" in x for x in problems(self.m)))

    def test_citation_off_the_page_fails(self):
        self.m["rows"][0]["criterion"]["cite"] = "p99:1"
        self.assertTrue(any("not in the source" in x for x in problems(self.m)))

    def test_filled_human_column_fails(self):
        self.m["rows"][0]["owner"] = "Proposal manager"
        self.assertTrue(any("human column must be empty" in x for x in problems(self.m)))

    def test_sum_mismatch_without_stop_fails(self):
        self.m["rows"].pop()  # drop Cost Proposal, 35 points
        self.assertTrue(any("points sum to 65" in x for x in problems(self.m)))

    def test_sum_mismatch_with_stop_is_valid(self):
        self.m["rows"].pop()
        self.m["stop"] = "RFP states 100 points; rows sum to 65; the Cost Proposal row is missing."
        self.assertEqual(problems(self.m), [])

    def test_blank_instead_of_not_in_source_fails(self):
        self.m["rows"][2]["answering_section"] = {"text": "", "cite": "p11:18"}
        self.assertTrue(any("empty text" in x for x in problems(self.m)))

    def test_free_text_claude_does_fails(self):
        self.m["rows"][0]["claude_does"] = "write something great"
        self.assertTrue(any("claude_does" in x for x in problems(self.m)))

    def test_could_not_map_needs_why_and_citation(self):
        self.m["could_not_map"][0]["why"] = ""
        self.assertTrue(any("needs a why" in x for x in problems(self.m)))
        self.m["could_not_map"][0]["text"] = "something the RFP never said"
        self.assertTrue(any("could_not_map 1" in x and "not verbatim" in x for x in problems(self.m)))

    def test_no_scoring_table_is_a_valid_stop(self):
        m = {"rfp": self.m["rfp"], "source": self.m["source"], "stated_total": "not in source",
             "rows": [], "could_not_map": [], "stop": "The RFP publishes no scoring table."}
        self.assertEqual(problems(m), [])


class Staged(unittest.TestCase):
    def test_stage_totals_reconcile_separately(self):
        m = load(STAGED)
        self.assertEqual(problems(m), [])
        m2 = copy.deepcopy(m)
        m2["rows"][0]["stage"] = "Interview"  # 10 points move stages
        errs = problems(m2)
        self.assertTrue(any("stage 'Proposal'" in x for x in errs) and any("stage 'Interview'" in x for x in errs))

    def test_unknown_stage_fails(self):
        m = load(STAGED)
        m["rows"][0]["stage"] = "Oral"
        self.assertTrue(any("is not a stated stage" in x for x in problems(m)))


class CommandLine(unittest.TestCase):
    def test_checker_exit_codes(self):
        ok = subprocess.run([sys.executable, ROOT / "tools/check_matrix.py", FIXTURE], capture_output=True, text=True)
        self.assertEqual(ok.returncode, 0, ok.stdout + ok.stderr)
        m = load(FIXTURE)
        m["rows"][0]["points"]["value"] = 41
        with tempfile.TemporaryDirectory() as d:
            bad = pathlib.Path(d) / "bad.matrix.json"
            m["source"] = str((OUT / m["source"]).resolve())
            bad.write_text(json.dumps(m))
            r = subprocess.run([sys.executable, ROOT / "tools/check_matrix.py", bad], capture_output=True, text=True)
            self.assertEqual(r.returncode, 1)
            self.assertIn("41 does not appear", r.stdout)

    def test_extract_numbers_lines(self):
        with tempfile.TemporaryDirectory() as d:
            src = pathlib.Path(d) / "rfp.txt"
            src.write_text("Selection Criteria\nCost - 30 points\n")
            r = subprocess.run([sys.executable, ROOT / "tools/extract.py", src], capture_output=True, text=True)
            self.assertEqual(r.returncode, 0, r.stderr)
            self.assertEqual(src.with_suffix(".source.txt").read_text(), "p1:1|Selection Criteria\np1:2|Cost - 30 points\n")

    def test_extract_refuses_empty(self):
        with tempfile.TemporaryDirectory() as d:
            src = pathlib.Path(d) / "blank.txt"
            src.write_text("\n\n")
            r = subprocess.run([sys.executable, ROOT / "tools/extract.py", src], capture_output=True, text=True)
            self.assertNotEqual(r.returncode, 0)
            self.assertIn("no text found", r.stderr + r.stdout)


if __name__ == "__main__":
    unittest.main()
