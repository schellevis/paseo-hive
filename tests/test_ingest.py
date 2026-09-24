import subprocess
import tempfile
import unittest
from pathlib import Path
from unittest import mock

from helpers import CRITIQUE_FOLLOWUP, FIXTURES, hive, run

F = hive.load_formats()
LOGS = FIXTURES / "logs"


def fmt(fid):
    return hive.get_format(F, fid)


def log(name):
    return (LOGS / name).read_text(encoding="utf-8")


class ExtractTest(unittest.TestCase):
    def test_thought_after_answer_is_cut(self):
        ans = hive.extract_answer(log("brainstorm-followup-thought.txt"), fmt("brainstorm-followup"))
        self.assertTrue(ans.startswith("BUILDS:\nN1 [builds on: B-I1]"), ans)
        self.assertTrue(ans.rstrip().endswith("QUESTION FOR THE USER: none"), ans)
        self.assertNotIn("draft", ans)
        self.assertEqual(hive.check_answer(ans, "brainstorm-followup", F)["status"], "ok")

    def test_bold_answer_after_echoed_template(self):
        ans = hive.extract_answer(log("critique-r1-bold.txt"), fmt("critique-r1"))
        self.assertTrue(ans.startswith("**POSITION:** Streaming will not cut tickets"), ans)
        self.assertNotIn("<", ans)
        self.assertEqual(hive.check_answer(ans, "critique-r1", F)["status"], "ok")

    def test_repeated_first_field_is_kept_whole(self):
        ans = hive.extract_answer(log("select-repeated.txt"), fmt("select"))
        self.assertEqual(ans.count("SHORTLIST:"), 3)
        self.assertIn("DROP: none", ans)
        self.assertEqual(hive.check_answer(ans, "select", F)["status"], "ok")

    def test_incomplete_answer_is_not_swapped_for_inlined_one(self):
        text = ("[User] Round 2. Seat B wrote:\n" + CRITIQUE_FOLLOWUP +
                "Answer in exactly this format:\nATTACKS:\n<claim id>: <why it is wrong>\n"
                "POSITION: changed | unchanged — <one sentence>\n"
                "ATTACKS:\nA-C3: Real attack.\nCONCESSIONS:\nnone\n"
                "POSITION: unchanged — Still batch.\nBECAUSE: A-C3 did not hold.\n"
                "STATUS: continue\nQUESTION FOR THE USER: none\n")
        ans = hive.extract_answer(text, fmt("critique-followup"))
        self.assertTrue(ans.startswith("ATTACKS:\nA-C3: Real attack."), ans)
        self.assertIn("missing CRUX", hive.check_answer(ans, "critique-followup", F)["line"])

    def test_no_answer_returns_none(self):
        self.assertIsNone(hive.extract_answer("[User] hello\nThinking aloud.\n", fmt("critique-r1")))


class IngestCliTest(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.dir = Path(self.tmp.name)

    def tearDown(self):
        self.tmp.cleanup()

    def ingest(self, *extra, source=("--log", str(LOGS / "brainstorm-followup-thought.txt"))):
        return run(["ingest", "--session", str(self.dir), "--seat", "C", "--leg", "1",
                    "--round", "2", "--format", "brainstorm-followup", *source, *extra])

    def test_writes_seat_file(self):
        code, out = self.ingest()
        self.assertEqual(code, 0, out)
        self.assertTrue(out.startswith("ok "))
        text = (self.dir / "leg-1/round-2/C.md").read_text(encoding="utf-8")
        self.assertTrue(text.startswith("BUILDS:"))

    def test_refuses_to_overwrite_without_force(self):
        self.ingest()
        self.assertEqual(self.ingest()[0], 2)

    def test_force_keeps_previous_version(self):
        self.ingest()
        code, _ = self.ingest("--force")
        self.assertEqual(code, 0)
        self.assertTrue((self.dir / "leg-1/round-2/C.v1.md").exists())

    def test_answer_not_found_writes_nothing(self):
        empty = self.dir / "empty.txt"
        empty.write_text("[User] hi\n", encoding="utf-8")
        code, out = self.ingest(source=("--log", str(empty)))
        self.assertEqual(code, 1)
        self.assertIn("answer not found", out)
        self.assertFalse((self.dir / "leg-1/round-2/C.md").exists())

    def test_select_round_path(self):
        code, _ = run(["ingest", "--session", str(self.dir), "--seat", "B", "--leg", "1",
                       "--round", "select", "--format", "select",
                       "--log", str(LOGS / "select-repeated.txt")])
        self.assertEqual(code, 0)
        self.assertTrue((self.dir / "leg-1/select/B.md").exists())

    def test_write_failure_exits_2(self):
        blocker = self.dir / "leg-1"
        blocker.write_text("not a directory", encoding="utf-8")
        self.assertEqual(self.ingest()[0], 2)

    def test_bad_seat_letter_exits_2(self):
        code, _ = run(["ingest", "--session", str(self.dir), "--seat", "seat1", "--leg", "1",
                       "--round", "2", "--format", "brainstorm-followup",
                       "--log", str(LOGS / "brainstorm-followup-thought.txt")])
        self.assertEqual(code, 2)

    def test_fairness_is_not_ingested(self):
        code, _ = run(["ingest", "--session", str(self.dir), "--seat", "A", "--leg", "1",
                       "--round", "1", "--format", "fairness",
                       "--log", str(LOGS / "select-repeated.txt")])
        self.assertEqual(code, 2)

    def test_agent_without_paseo_cli_exits_2(self):
        with mock.patch("hive.shutil.which", return_value=None):
            code, _ = self.ingest(source=("--agent", "abc123"))
        self.assertEqual(code, 2)

    def test_agent_uses_paseo_logs(self):
        done = subprocess.CompletedProcess([], 0, stdout=log("brainstorm-followup-thought.txt"), stderr="")
        with mock.patch("hive.shutil.which", return_value="paseo"), \
             mock.patch("hive.subprocess.run", return_value=done) as call:
            code, _ = self.ingest(source=("--agent", "abc123"))
        self.assertEqual(code, 0)
        self.assertEqual(call.call_args[0][0], ["paseo", "logs", "abc123", "--filter", "text"])


if __name__ == "__main__":
    unittest.main()
