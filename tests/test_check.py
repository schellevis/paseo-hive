import json
import tempfile
import unittest
from pathlib import Path

from helpers import (BRAINSTORM_R1, CRITIQUE_FOLLOWUP, CRITIQUE_R1, DEBUG_FOLLOWUP,
                     DEBUG_FOLLOWUP_B, DEBUG_FOLLOWUP_MAX, DEBUG_R1, DEBUG_R1_MAX,
                     DEBUG_R1_RESULT, SELECT, SOLVE_FOLLOWUP, SOLVE_R1, hive, run)

F = hive.load_formats()


def check(text, fmt="critique-r1", **kw):
    return hive.check_answer(text, fmt, F, **kw)


def pad(text, total):
    """Append filler words to the first line until the answer has `total` words."""
    missing = total - len(text.split())
    return text.replace("\n", " " + " ".join(["word"] * missing) + "\n", 1)


class CheckTest(unittest.TestCase):
    def test_valid_answer_is_ok(self):
        res = check(CRITIQUE_R1)
        self.assertEqual(res["status"], "ok")
        self.assertRegex(res["line"], r"^ok \d+/250$")

    def test_overrun_within_tolerance_is_note(self):
        res = check(pad(CRITIQUE_R1, 280))
        self.assertEqual(res["status"], "note")
        self.assertTrue(res["line"].startswith("note 280/250 (+12%)"), res["line"])

    def test_overrun_beyond_tolerance_is_trim(self):
        self.assertEqual(check(pad(CRITIQUE_R1, 454))["line"], "trim 454/250 (+82%)")

    def test_deep_mode_uses_400(self):
        self.assertEqual(check(pad(CRITIQUE_R1, 380), mode="deep")["status"], "ok")

    def test_missing_field_is_invalid(self):
        res = check(CRITIQUE_R1.replace("CRUX: Whether any contract promises same-hour invoices.\n", ""))
        self.assertEqual(res["status"], "invalid")
        self.assertIn("missing CRUX", res["line"])

    def test_fields_out_of_order(self):
        lines = CRITIQUE_R1.splitlines()
        swapped = "\n".join([lines[-2], *lines[:-2], lines[-1]]) + "\n"
        self.assertIn("fields out of order", check(swapped)["line"])

    def test_bad_tag_is_invalid(self):
        res = check(CRITIQUE_R1.replace("[likely]", "[maybe]"))
        self.assertIn("C1: [maybe] not in certain|likely|guess", res["line"])

    def test_too_few_claims(self):
        text = CRITIQUE_R1.replace("C3 [guess] Most customers read the export the next morning.\n", "")
        self.assertIn("CLAIMS: 2 items, expected 3-5", check(text)["line"])

    def test_numbering_gap(self):
        self.assertIn("numbered [1, 2, 4]", check(CRITIQUE_R1.replace("C3 [guess]", "C4 [guess]"))["line"])

    def test_too_many_sentences_is_a_note(self):
        text = CRITIQUE_R1.replace("idempotent keys.", "idempotent keys. It runs at night. Nobody waits.")
        res = check(text)
        self.assertEqual(res["status"], "note")
        self.assertIn("note: C1 has 4 sentences", res["line"])

    def test_bold_field_names_are_accepted(self):
        bold = CRITIQUE_R1.replace("POSITION:", "**POSITION:**").replace("CRUX:", "**CRUX:**")
        self.assertEqual(check(bold)["status"], "ok")

    def test_choice_value_must_be_allowed(self):
        res = check(CRITIQUE_FOLLOWUP.replace("POSITION: changed", "POSITION: maybe"), "critique-followup")
        self.assertIn("POSITION: expected changed | unchanged", res["line"])

    def test_unknown_reference_is_invalid(self):
        res = check(CRITIQUE_FOLLOWUP, "critique-followup", known={"B-C1"})
        self.assertEqual(res["unknown"], ["B-C2"])
        self.assertIn("unknown id B-C2", res["line"])

    def test_known_references_pass(self):
        res = check(CRITIQUE_FOLLOWUP, "critique-followup", known={"B-C1", "B-C2"})
        self.assertEqual(res["status"], "ok")

    def test_blind_seat(self):
        blind = CRITIQUE_R1.replace("POSITION: A nightly", "POSITION: If this is about a nightly")
        self.assertEqual(check(blind)["status"], "blind?")
        self.assertEqual(check(CRITIQUE_R1 + "Note: I cannot see the attached files.\n")["status"], "blind?")

    def test_if_this_later_in_answer_is_not_blind(self):
        text = CRITIQUE_R1.replace("CRUX: Whether", "CRUX: If this holds, whether")
        self.assertEqual(check(text)["status"], "ok")

    def test_select_merges_repeated_shortlist_lines(self):
        res = check(SELECT, "select")
        self.assertEqual(res["status"], "ok")
        self.assertTrue(res["line"].endswith("/120"))

    def test_brainstorm_tags(self):
        self.assertEqual(check(BRAINSTORM_R1, "brainstorm-r1")["status"], "ok")
        bad = BRAINSTORM_R1.replace("[effort: mid] Repair", "[effort: medium] Repair")
        self.assertIn("I2: [effort: medium] not in low|mid|high", check(bad, "brainstorm-r1")["line"])

    def test_solve_r1_is_ok(self):
        res = check(SOLVE_R1, "solve-r1")
        self.assertEqual(res["status"], "ok", res["line"])

    def test_solve_r1_step_bounds(self):
        two = SOLVE_R1.replace("S3 Send exceptions to the shared desk with a written reason.\n", "")
        res = check(two, "solve-r1")
        self.assertEqual(res["status"], "invalid")
        self.assertIn("STEPS: 2 items, expected 3-6", res["line"])
        gap = SOLVE_R1.replace("S3 Send", "S4 Send")
        res = check(gap, "solve-r1")
        self.assertEqual(res["status"], "invalid")
        self.assertIn("numbered [1, 2, 4]", res["line"])

    def test_solve_replaces_tag(self):
        self.assertEqual(check(SOLVE_FOLLOWUP, "solve-followup")["status"], "ok")
        two = SOLVE_FOLLOWUP.replace("[replaces: A-S2]", "[replaces: A-S2, A-S3]")
        res = check(two, "solve-followup")
        self.assertEqual(res["status"], "invalid")
        self.assertIn("S1:", res["line"])
        empty = SOLVE_FOLLOWUP.replace("[replaces: new]", "[replaces: ]")
        res = check(empty, "solve-followup")
        self.assertEqual(res["status"], "invalid")
        self.assertIn("S2:", res["line"])

    def test_debug_r1_is_ok(self):
        for text in (DEBUG_R1, DEBUG_R1_RESULT):
            res = check(text, "debug-r1")
            self.assertEqual(res["status"], "ok", res["line"])

    def test_debug_hypothesis_bounds_and_tags(self):
        bad = DEBUG_R1.replace("[likely]", "[probable]")
        res = check(bad, "debug-r1")
        self.assertEqual(res["status"], "invalid")
        self.assertIn("H2: [probable] not in likely|possible|unlikely", res["line"])
        one = DEBUG_R1.replace("H2 [likely] Daylight saving makes the 19:00 start feel rushed after work. "
                               "It explains why members still like rehearsals.\n", "")
        res = check(one.replace("LEADING: H2", "LEADING: H1"), "debug-r1")
        self.assertEqual(res["status"], "invalid")
        self.assertIn("HYPOTHESES: 1 items, expected 2-3", res["line"])
        four = DEBUG_R1_MAX.replace("LEADING:", "H4 [possible] The oven door is opened too often. "
                                    "Each opening drops the chamber temperature.\nLEADING:")
        res = check(four, "debug-r1")
        self.assertEqual(res["status"], "invalid")
        self.assertIn("HYPOTHESES: 4 items, expected 2-3", res["line"])

    def test_debug_needs_a_test(self):
        none = DEBUG_R1.replace(
            "T1 Compare sign-ins for the two weeks around the clock change. "
            "A step at that week supports H2 over H1.\n", "")
        res = check(none, "debug-r1")
        self.assertEqual(res["status"], "invalid")
        self.assertIn("TESTS: 0 items, expected 1-2", res["line"])

    def test_debug_leading_must_name_an_item_of_the_answer(self):
        res = check(DEBUG_R1.replace("LEADING: H2,", "LEADING: H3,"), "debug-r1")
        self.assertEqual(res["status"], "invalid")
        self.assertIn("LEADING: H3 is not an item in this answer", res["line"])

    def test_debug_result_must_name_a_test_of_the_answer(self):
        res = check(DEBUG_R1_RESULT.replace("RESULT: T1:", "RESULT: T3:"), "debug-r1")
        self.assertEqual(res["status"], "invalid")
        self.assertIn("RESULT: T3 is not an item in this answer", res["line"])

    def test_debug_followup_is_ok_without_known_new_ids(self):
        known = {"A-H1", "A-H2", "B-H1", "B-H2", "A-T1", "B-T1", "B-RESULT", "A-LEADING", "B-LEADING"}
        res = check(DEBUG_FOLLOWUP, "debug-followup", known=known)
        self.assertEqual(res["status"], "ok", res["line"])
        self.assertEqual(res["unknown"], [])
        self.assertIn("B-RESULT", res["refs"])
        res = check(DEBUG_FOLLOWUP_B, "debug-followup", known=known)
        self.assertEqual(res["status"], "ok", res["line"])
        self.assertIn("B-RESULT", res["refs"])

    def test_debug_followup_unknown_prefixed_id_is_invalid(self):
        known = {"A-H1", "A-H2", "B-H1", "B-H2", "A-T1", "B-T1", "B-RESULT"}
        res = check(DEBUG_FOLLOWUP.replace("A-H1: B-RESULT", "A-H9: B-RESULT"),
                    "debug-followup", known=known)
        self.assertEqual(res["status"], "invalid")
        self.assertIn("unknown id A-H9", res["line"])

    def test_debug_max_answers_are_neither_trim_nor_invalid(self):
        for text, fmt_id in ((DEBUG_R1_MAX, "debug-r1"), (DEBUG_FOLLOWUP_MAX, "debug-followup")):
            res = check(text, fmt_id, mode="standard")
            self.assertIn(res["status"], ("ok", "note"), res["line"])
            self.assertFalse(any("sentences" in p["message"] for p in res["problems"]), res["line"])

    def test_debug_reference_boundaries(self):
        res = check(DEBUG_FOLLOWUP.replace(
            "H1 [likely] The handout and the clock change fall in the same week, and members blame "
            "the new pieces. It explains both signals.", "none"), "debug-followup")
        self.assertEqual(res["status"], "invalid")
        self.assertIn("LEADING: H1 is not an item in this answer", res["line"])
        known = {"A-H1", "A-H2", "B-H1", "B-H2", "A-T1", "B-T1", "B-RESULT"}
        res = check(DEBUG_FOLLOWUP_B.replace("unchanged — B-H1", "unchanged — A-H1"),
                    "debug-followup", known=known)
        self.assertEqual(res["status"], "ok", res["line"])
        res = check(DEBUG_FOLLOWUP_B.replace("unchanged — B-H1", "unchanged — A-H9"),
                    "debug-followup", known=known)
        self.assertEqual(res["status"], "invalid")
        self.assertIn("unknown id A-H9", res["line"])
        res = check(DEBUG_FOLLOWUP_B.replace("RESULT: A-T1:", "RESULT: T3:"), "debug-followup")
        self.assertEqual(res["status"], "invalid")
        self.assertIn("RESULT: T3 is not an item in this answer", res["line"])

    def test_fairness(self):
        self.assertEqual(check("fair\n", "fairness")["status"], "ok")
        self.assertEqual(check("unfair: it drops my second claim\n", "fairness")["status"], "ok")
        self.assertEqual(check("mostly fair\n", "fairness")["status"], "invalid")


class CheckCliTest(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.dir = Path(self.tmp.name)

    def tearDown(self):
        self.tmp.cleanup()

    def write(self, text):
        path = self.dir / "A.md"
        path.write_text(text, encoding="utf-8")
        return str(path)

    def test_ok_exits_0(self):
        code, out = run(["check", self.write(CRITIQUE_R1), "--format", "critique-r1"])
        self.assertEqual(code, 0)
        self.assertTrue(out.startswith("ok "))

    def test_trim_exits_1(self):
        code, _ = run(["check", self.write(pad(CRITIQUE_R1, 400)), "--format", "critique-r1"])
        self.assertEqual(code, 1)

    def test_json_output(self):
        _, out = run(["check", self.write(CRITIQUE_R1), "--format", "critique-r1", "--json"])
        self.assertEqual(json.loads(out)["status"], "ok")

    def test_session_enables_reference_check(self):
        leg = self.dir / "leg-1"
        leg.mkdir()
        (leg / "items.json").write_text(json.dumps([{"id": "B-C1"}]), encoding="utf-8")
        code, out = run(["check", self.write(CRITIQUE_FOLLOWUP), "--format", "critique-followup",
                         "--session", str(self.dir)])
        self.assertEqual(code, 1)
        self.assertIn("unknown id B-C2", out)

    def test_missing_file_exits_2(self):
        self.assertEqual(run(["check", str(self.dir / "nope.md"), "--format", "critique-r1"])[0], 2)

    def test_unknown_format_exits_2(self):
        self.assertEqual(run(["check", self.write(CRITIQUE_R1), "--format", "nope"])[0], 2)


if __name__ == "__main__":
    unittest.main()
