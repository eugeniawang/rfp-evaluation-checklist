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
        # A matrix with a valid `stop` is complete without reconciling (that's the point of
        # `stop`) — only a matrix with no stop is required to reconcile.
        for p in sorted(OUT.glob("*.matrix.json")):
            m = load(p)
            if m.get("stop"):
                continue
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
        self.assertEqual(keys, set(check_matrix.ROW_FIELDS))


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
        self.m["rows"][0]["lead"] = "Proposal manager"
        self.assertTrue(any("human column must be empty" in x for x in problems(self.m)))

    def test_filled_status_fails(self):
        self.m["rows"][0]["status"] = "open"
        self.assertTrue(any("status" in x and "human column must be empty" in x for x in problems(self.m)))

    def test_sum_mismatch_without_stop_fails(self):
        self.m["rows"].pop()  # drop Cost Proposal, 35 points
        self.assertTrue(any("points sum to 65" in x for x in problems(self.m)))

    def test_sum_mismatch_with_stop_is_valid(self):
        dropped = self.m["rows"].pop()  # drop Cost Proposal, 35 points
        # dropping the row can't drop its criterion sentence from the source: it has to move
        # to could_not_map so the coverage check still finds it accounted for.
        self.m["could_not_map"].append({
            "text": dropped["criterion"]["text"], "cite": dropped["criterion"]["cite"],
            "why": "sits inside a scored criterion with no points of its own",
        })
        self.m["stop"] = "points do not reconcile to the stated total"
        self.assertEqual(problems(self.m), [])
        _, total = check_matrix.check(self.m, OUT)
        self.assertFalse(check_matrix.reconciles(self.m, total))

    def test_blank_instead_of_not_in_source_fails(self):
        self.m["rows"][2]["answering_section"] = {"text": "", "cite": "p11:18"}
        self.assertTrue(any("empty text" in x for x in problems(self.m)))

    def test_could_not_map_needs_why_and_citation(self):
        self.m["could_not_map"][0]["why"] = ""
        self.assertTrue(any("why: not one of the fixed reasons" in x for x in problems(self.m)))
        self.m["could_not_map"][0]["text"] = "something the RFP never said"
        self.assertTrue(any("could_not_map 1" in x and "not verbatim" in x for x in problems(self.m)))

    def test_no_scoring_table_is_a_valid_stop(self):
        # A real "no scoring table" RFP still has to pass the coverage check, so this can't
        # borrow the full tucker016 source (which is full of gate language elsewhere in the
        # document); it gets its own trigger-free stand-in source instead.
        with tempfile.TemporaryDirectory() as d:
            src_path = pathlib.Path(d) / "no-scoring.source.txt"
            src_path.write_text("p1:1|Request for Qualifications\np1:2|This is a qualifications-based selection.\n")
            m = {"rfp": {"text": "Request for Qualifications", "cite": "p1:1"},
                 "issuer": "not in source", "title": "not in source", "due": "not in source",
                 "source": str(src_path),
                 "stated_total": "not in source", "rows": [], "disqualifiers": [], "could_not_map": [],
                 "reviewed": [], "stop": "no scoring table published"}
            self.assertEqual(check_matrix.check(m, pathlib.Path(d))[0], [])

    # --- the holes two reviewers found in the first version, each now closed ---

    def test_fragment_that_ends_mid_word_fails(self):
        self.m["rows"][0]["criterion"]["text"] = "Staff Exper"  # source: "Staff Experience - 40 points"
        self.assertTrue(any("whole words" in x for x in problems(self.m)))

    def test_points_from_a_neighbouring_line_fail(self):
        # 35 is printed at p11:18 (Cost Proposal); a wide citation must not let row 1 claim it
        self.m["rows"][0]["points"] = {"value": 35, "cite": "p11:14-p11:18"}
        self.assertTrue(any("spans 5 lines; the limit is 2" in x for x in problems(self.m)))

    def test_points_from_the_rfp_number_fail(self):
        self.m["rows"][0]["points"] = {"value": 2026, "cite": "p11:1-p11:14"}
        self.assertTrue(any("row 1 points" in x for x in problems(self.m)))

    @staticmethod
    def _first_part(v):
        """input_needed etc. may now be a single {text,cite} object or a list of them."""
        return v[0] if isinstance(v, list) else v

    def test_citation_across_pages_fails(self):
        self._first_part(self.m["rows"][0]["input_needed"])["cite"] = "p10:20-p11:2"
        self.assertTrue(any("crosses a page" in x for x in problems(self.m)))

    def test_citation_wider_than_twelve_lines_fails(self):
        self._first_part(self.m["rows"][0]["input_needed"])["cite"] = "p10:1-p10:24"
        self.assertTrue(any("spans 24 lines; the limit is 12" in x for x in problems(self.m)))

    def test_unknown_row_key_fails(self):
        self.m["rows"][0]["notes"] = "award expected July 2026"
        self.assertTrue(any("unknown key(s) ['notes']" in x for x in problems(self.m)))

    def test_unknown_top_level_key_fails(self):
        self.m["summary"] = "three criteria, cost is 35%"
        self.assertTrue(any("unknown top-level key" in x for x in problems(self.m)))

    def test_free_text_why_fails(self):
        self.m["could_not_map"][0]["why"] = "probably not important"
        self.assertTrue(any("why: not one of the fixed reasons" in x for x in problems(self.m)))

    def test_free_text_stop_fails(self):
        self.m["rows"].pop()
        self.m["stop"] = "RFP states 100; rows sum to 65; award expected July."
        self.assertTrue(any("stop: not one of the fixed states" in x for x in problems(self.m)))

    def test_missing_could_not_map_fails(self):
        del self.m["could_not_map"]
        self.assertTrue(any("missing top-level key could_not_map" in x for x in problems(self.m)))

    def test_missing_human_column_fails(self):
        # "status" is a human column under both the pre- and post-Ruling-18:25 schema, so this
        # doesn't depend on whether outputs/ has been migrated to lead/reviewer yet.
        del self.m["rows"][0]["status"]
        self.assertTrue(any("row 1: missing field status" in x for x in problems(self.m)))

    def test_stage_on_flat_matrix_fails(self):
        self.m["rows"][0]["stage"] = "Proposal"
        self.assertTrue(any("'stage' is only allowed" in x for x in problems(self.m)))

    def test_rows_out_of_rfp_order_fail(self):
        self.m["rows"].reverse()
        self.assertTrue(any("rows follow the RFP's order" in x for x in problems(self.m)))

    def test_sourced_field_with_extra_key_fails(self):
        self.m["rows"][0]["criterion"]["note"] = "the big one"
        self.assertTrue(any("row 1 criterion: must be" in x for x in problems(self.m)))


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

    def test_extract_drops_the_trailing_form_feed_page(self):
        sys.path.insert(0, str(ROOT / "tools"))
        import extract
        self.assertEqual(len(extract.split_pages("one\n\x0ctwo\n\x0c")), 2)
        self.assertEqual(len(extract.split_pages("one\n\x0ctwo\n")), 2)
        self.assertEqual(extract.number(extract.split_pages("a\nb\n\x0cc\n\x0c")),
                         ["p1:1|a", "p1:2|b", "p2:1|c"])

    def test_extract_refuses_empty(self):
        with tempfile.TemporaryDirectory() as d:
            src = pathlib.Path(d) / "blank.txt"
            src.write_text("\n\n")
            r = subprocess.run([sys.executable, ROOT / "tools/extract.py", src], capture_output=True, text=True)
            self.assertNotEqual(r.returncode, 0)
            self.assertIn("no text found", r.stderr + r.stdout)


# ---------------------------------------------------------------------------------------
# v2 additions. These build their own tiny fixture (a source file + matrix, in a temp
# dir) rather than reusing outputs/, so they don't race with the matrix workers rebuilding
# those files to v2 in parallel, and don't depend on outputs/ already being v2-valid.
# ---------------------------------------------------------------------------------------

MINI_SOURCE_LINES = [
    "Sample RFP No. 2026-001",                                              # p1:1
    "Evaluation Criteria",                                                  # p1:2
    "Staff Qualifications - 50 points",                                     # p1:3
    "Provide resumes of key staff.",                                        # p1:4
    "Proposal Section 3, Key Personnel",                                    # p1:5
    "Total points possible: 50",                                            # p1:6
    "Late submittals will not be considered.",                              # p1:7
    "See Table of Contents item 4.2 for Evaluation Criteria details.",      # p1:8
    "Provide the organizational chart for review.",                        # p1:9
    "Note: A < B applies here.",                                            # p1:10
    "Issued by the City of Sample.",                                        # p1:11
    "Project: Sample Roofing Replacement",                                  # p1:12
    "Proposals are due by 5:00 PM on October 1, 2026.",                     # p1:13
]


def write_mini_source(d: pathlib.Path) -> pathlib.Path:
    p = d / "mini.source.txt"
    p.write_text("\n".join(f"p1:{i}|{t}" for i, t in enumerate(MINI_SOURCE_LINES, start=1)) + "\n")
    return p


def mini_matrix(src_path) -> dict:
    return {
        "rfp": {"text": "Sample RFP No. 2026-001", "cite": "p1:1"},
        "issuer": {"text": "City of Sample.", "cite": "p1:11"},
        "title": {"text": "Sample Roofing Replacement", "cite": "p1:12"},
        "due": {"text": "5:00 PM on October 1, 2026.", "cite": "p1:13"},
        "source": str(src_path),
        "stated_total": {"value": 50, "cite": "p1:6"},
        "rows": [
            {
                "section": {"text": "Evaluation Criteria", "cite": "p1:2"},
                "criterion": {"text": "Staff Qualifications - 50 points", "cite": "p1:3"},
                "points": {"value": 50, "cite": "p1:3"},
                "input_needed": {"text": "Provide resumes of key staff.", "cite": "p1:4"},
                "input_source": "",
                "evaluation_criteria": {"text": "Staff Qualifications - 50 points", "cite": "p1:3"},
                "answering_section": {"text": "Proposal Section 3, Key Personnel", "cite": "p1:5"},
                "lead": "",
                "reviewer": "",
                "status": "",
            }
        ],
        "disqualifiers": [
            {"text": "Late submittals will not be considered.", "cite": "p1:7", "kind": "late submittal"},
        ],
        "could_not_map": [
            {"text": "Note: A < B applies here.", "cite": "p1:10",
             "why": "sits inside a scored criterion with no points of its own"},
        ],
        "reviewed": [
            {"cite": "p1:8", "why": "table of contents or index entry"},
        ],
    }


class V2Additions(unittest.TestCase):
    """The five new refusal cases the spec asks for, plus proof the good baseline passes."""

    @classmethod
    def setUpClass(cls):
        cls.tmp = tempfile.TemporaryDirectory()
        cls.dir = pathlib.Path(cls.tmp.name)
        cls.src_path = write_mini_source(cls.dir)

    @classmethod
    def tearDownClass(cls):
        cls.tmp.cleanup()

    def base(self):
        return mini_matrix(self.src_path)

    def problems(self, m):
        return check_matrix.check(m, self.dir)[0]

    def test_good_baseline_passes(self):
        probs, total = check_matrix.check(self.base(), self.dir)
        self.assertEqual(probs, [])
        self.assertEqual(total, 50)

    def test_disqualifier_bad_kind_fails(self):
        m = self.base()
        m["disqualifiers"][0]["kind"] = "just seemed important"
        self.assertTrue(any("kind: not one of the fixed phrases" in x for x in self.problems(m)))

    def test_unaccounted_coverage_hit_fails(self):
        m = self.base()
        m["reviewed"] = []  # p1:8 ("...Evaluation Criteria details.") is now cited nowhere
        probs = self.problems(m)
        self.assertTrue(any(x.startswith("COVERAGE: p1:8") for x in probs), probs)

    def test_imperative_answering_section_fails(self):
        m = self.base()
        m["rows"][0]["answering_section"] = {
            "text": "Provide the organizational chart for review.", "cite": "p1:9",
        }
        probs = self.problems(m)
        self.assertTrue(any("imperative verb" in x for x in probs), probs)

    def test_filled_status_fails(self):
        m = self.base()
        m["rows"][0]["status"] = "open"
        probs = self.problems(m)
        self.assertTrue(any("status" in x and "must be empty" in x for x in probs), probs)

    def test_claude_does_key_is_rejected(self):
        # Ruling 18:25 removed claude_does from the schema entirely.
        m = self.base()
        m["rows"][0]["claude_does"] = ""
        probs = self.problems(m)
        self.assertTrue(any("claude_does" in x and "unknown key" in x for x in probs), probs)

    def test_multi_part_cell_with_one_bad_part_fails(self):
        m = self.base()
        m["rows"][0]["input_needed"] = [
            {"text": "Provide resumes of key staff.", "cite": "p1:4"},
            {"text": "Something the RFP never said", "cite": "p1:4"},
        ]
        probs = self.problems(m)
        self.assertTrue(any("part 2" in x and "not verbatim" in x for x in probs), probs)

    def test_good_multi_part_cell_passes(self):
        m = self.base()
        m["rows"][0]["input_needed"] = [{"text": "Provide resumes of key staff.", "cite": "p1:4"}]
        self.assertEqual(self.problems(m), [])


class CoverageUnicodeHyphens(unittest.TestCase):
    """Correction 18:17: a Unicode hyphen (U+2011 here) must not defeat `non-?responsive`."""

    def test_unicode_hyphen_gate_line_is_still_a_coverage_hit(self):
        with tempfile.TemporaryDirectory() as d:
            tmp = pathlib.Path(d)
            src = tmp / "src.txt"
            # U+2011 (non-breaking hyphen) in "non‑responsive" — an ASCII-only scan misses it.
            src.write_text(
                "p1:1|Sample RFP\n"
                "p1:2|A proposal found non‑responsive will not be scored.\n"
            )
            m = {
                "rfp": {"text": "Sample RFP", "cite": "p1:1"},
                "issuer": "not in source", "title": "not in source", "due": "not in source",
                "source": str(src),
                "stated_total": "not in source", "rows": [], "disqualifiers": [], "could_not_map": [],
                "reviewed": [], "stop": "no scoring table published",
            }
            probs = check_matrix.check(m, tmp)[0]
            self.assertTrue(any(x.startswith("COVERAGE: p1:2") for x in probs), probs)
            # accounting for it (any bucket) clears the failure
            m["reviewed"] = [{"cite": "p1:2", "why": "not about how proposals are evaluated or rejected"}]
            self.assertEqual(check_matrix.check(m, tmp)[0], [])


class HTMLSmoke(unittest.TestCase):
    """write_matrix.py must actually write the .html, and it must escape source text."""

    def test_html_written_with_every_citation_and_escaped_html(self):
        with tempfile.TemporaryDirectory() as d:
            tmp = pathlib.Path(d)
            src_path = write_mini_source(tmp)
            m = mini_matrix(src_path)
            matrix_path = tmp / "mini.matrix.json"
            matrix_path.write_text(json.dumps(m))
            r = subprocess.run([sys.executable, ROOT / "tools/write_matrix.py", matrix_path],
                               capture_output=True, text=True)
            self.assertEqual(r.returncode, 0, r.stdout + r.stderr)
            html_path = tmp / "mini.matrix.html"
            self.assertTrue(html_path.exists())
            content = html_path.read_text()
            # every citation that actually appears in a rendered part (rfp, stated_total,
            # the row's sourced cells, the disqualifier, the could_not_map entry). The
            # `reviewed` list (p1:8) is bookkeeping for the coverage check, not something
            # Part 1/2/3 renders, so it is not expected to appear here.
            for cite in ("p1:1", "p1:2", "p1:3", "p1:4", "p1:5", "p1:6", "p1:7", "p1:10"):
                self.assertIn(cite, content)
            # the could_not_map entry's text contains a literal "<" from the source; the
            # rendered <li> must carry it escaped, never as a raw, unescaped tag. (The
            # embedded JSON source blob inside <script> legitimately contains the raw "<" —
            # that's JS/JSON string data, not markup, and is only escaped when the sidebar
            # JS writes it into the DOM at click time — so the check is scoped to the <li>.)
            self.assertIn("<li>Note: A &lt; B applies here.", content)
            self.assertNotIn("<li>Note: A < B applies here.", content)


class NotInSourceLiteral(unittest.TestCase):
    """Audit fix: the brief says the output literally says "not in source". Every rendering
    must carry that exact string when the JSON has it; md alone adds a plain-English gloss."""

    def test_literal_string_in_every_rendering(self):
        with tempfile.TemporaryDirectory() as d:
            tmp = pathlib.Path(d)
            src_path = write_mini_source(tmp)
            m = mini_matrix(src_path)
            m["rows"][0]["evaluation_criteria"] = "not in source"
            matrix_path = tmp / "mini.matrix.json"
            matrix_path.write_text(json.dumps(m))
            r = subprocess.run([sys.executable, ROOT / "tools/write_matrix.py", matrix_path],
                               capture_output=True, text=True)
            self.assertEqual(r.returncode, 0, r.stdout + r.stderr)

            md = (tmp / "mini.matrix.md").read_text()
            self.assertIn("not in source (the RFP doesn't say)", md)

            csv_text = (tmp / "mini.matrix.csv").read_text()
            self.assertIn("not in source", csv_text)
            self.assertNotIn("not in source (the RFP doesn't say)", csv_text)

            import openpyxl
            wb = openpyxl.load_workbook(tmp / "mini.matrix.xlsx")
            ws = wb.active
            values = [c.value for row in ws.iter_rows() for c in row]
            self.assertIn("not in source", values)
            self.assertNotIn("not in source (the RFP doesn't say)", values)

            html = (tmp / "mini.matrix.html").read_text()
            self.assertIn("not in source", html)


if __name__ == "__main__":
    unittest.main()
