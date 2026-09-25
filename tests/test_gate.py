import json
import tempfile
import unittest
from pathlib import Path

from helpers import CRITIQUE_FOLLOWUP, CRITIQUE_R1, run

SEATS = {"session": "20260101-0900-test", "goal": "critique", "mode": "standard", "seats": [
    {"letter": "A", "role": "Skeptic", "provider": "claude", "model": "claude-sonnet-5",
     "label": "Sonnet 5", "agent": "a1", "thinking": "high"},
    {"letter": "B", "role": "Alternative", "provider": "codex", "model": "gpt-5.5",
     "label": "GPT-5.5", "agent": "b1", "thinking": "low"},
]}


class GateTest(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.session = Path(self.tmp.name)
        (self.session / "seats.json").write_text(json.dumps(SEATS), encoding="utf-8")

    def tearDown(self):
        self.tmp.cleanup()

    def seat(self, rnd, letter, text, fmt=None, code=0):
        log = self.session / f"log-{rnd}-{letter}.txt"
        log.write_text(text, encoding="utf-8")
        fmt = fmt or ("critique-r1" if rnd == 1 else "critique-followup")
        got, out = run(["ingest", "--session", str(self.session), "--seat", letter, "--leg", "1",
                        "--round", str(rnd), "--format", fmt, "--log", str(log)])
        self.assertEqual(got, code, out)
        return self.session / "leg-1" / f"round-{rnd}" / f"{letter}.md"

    def moderator(self, rnd, text):
        path = self.session / f"leg-1/ledger-{rnd}.md"
        path.write_text(path.read_text(encoding="utf-8") + text, encoding="utf-8")

    def ledger(self, rnd, fmt):
        return run(["ledger", "--session", str(self.session), "--leg", "1",
                    "--round", str(rnd), "--format", fmt])

    def gate(self, rnd, *extra):
        return run(["gate", "--session", str(self.session), "--leg", "1",
                    "--round", str(rnd), *extra])

    def round_one(self):
        self.seat(1, "A", CRITIQUE_R1)
        self.seat(1, "B", CRITIQUE_R1)
        self.assertEqual(self.ledger(1, "critique-r1")[0], 0)

    def test_complete_round_passes(self):
        self.round_one()
        code, out = self.gate(1)
        self.assertEqual(code, 0, out)
        self.assertIn("ok: leg 1 round 1 is complete", out)

    def test_missing_seat_answer(self):
        self.seat(1, "A", CRITIQUE_R1)
        self.ledger(1, "critique-r1")
        code, out = self.gate(1)
        self.assertEqual(code, 1)
        self.assertIn("missing: seat B has no ingested answer", out)

    def test_skip_must_be_recorded(self):
        self.seat(1, "A", CRITIQUE_R1)
        self.ledger(1, "critique-r1")
        code, out = self.gate(1, "--skip", "B")
        self.assertEqual(code, 1)
        self.assertIn("skip: seat B is not recorded", out)
        self.moderator(1, "Skipped: B (no activity for 10 minutes)\n")
        self.assertEqual(self.gate(1, "--skip", "B")[0], 0)

    def test_skip_of_a_seat_that_answered(self):
        self.round_one()
        self.moderator(1, "Skipped: B (stalled)\n")
        code, out = self.gate(1, "--skip", "B")
        self.assertEqual(code, 1)
        self.assertIn("skip: seat B is passed to --skip but has an answer", out)

    def test_replaced_seat_is_not_required(self):
        seats = json.loads(json.dumps(SEATS))
        seats["seats"][1]["replaced"] = True
        (self.session / "seats.json").write_text(json.dumps(seats), encoding="utf-8")
        self.seat(1, "A", CRITIQUE_R1)
        self.ledger(1, "critique-r1")
        self.assertEqual(self.gate(1)[0], 0)

    def test_hand_written_ledger(self):
        self.seat(1, "A", CRITIQUE_R1)
        self.seat(1, "B", CRITIQUE_R1)
        (self.session / "leg-1/ledger-1.md").write_text("# Ledger\nA: holds.\n", encoding="utf-8")
        code, out = self.gate(1)
        self.assertEqual(code, 1)
        self.assertIn("hand-written: leg-1/ledger-1.md", out)

    def test_hand_written_seat_file(self):
        self.round_one()
        path = self.session / "leg-1/round-1/C.md"
        seats = json.loads(json.dumps(SEATS))
        seats["seats"].append({"letter": "C", "role": "Advocate", "provider": "mistral-vibe",
                               "model": "glm-5-3", "label": "GLM-5.3", "agent": "c1"})
        (self.session / "seats.json").write_text(json.dumps(seats), encoding="utf-8")
        path.write_text(CRITIQUE_R1, encoding="utf-8")
        code, out = self.gate(1)
        self.assertEqual(code, 1)
        self.assertIn("hand-written: leg-1/round-1/C.md was not saved by hive.py ingest", out)

    def test_edited_seat_file(self):
        self.round_one()
        path = self.session / "leg-1/round-1/A.md"
        path.write_text("RANKING: summary by the moderator\n", encoding="utf-8")
        code, out = self.gate(1)
        self.assertEqual(code, 1)
        self.assertIn("edited: leg-1/round-1/A.md changed after hive.py ingest", out)

    def test_edited_items_part(self):
        self.round_one()
        path = self.session / "leg-1/ledger-1.md"
        path.write_text(path.read_text(encoding="utf-8").replace("A-C1", "A-C1 (moderator note)", 1),
                        encoding="utf-8")
        code, out = self.gate(1)
        self.assertEqual(code, 1)
        self.assertIn("edited: the Items part of leg-1/ledger-1.md", out)

    def test_moderator_part_may_change(self):
        self.round_one()
        self.moderator(1, "K1 Whether any contract promises same-hour invoices.\n")
        self.assertEqual(self.gate(1)[0], 0)

    def test_missing_ledger(self):
        self.seat(1, "A", CRITIQUE_R1)
        self.seat(1, "B", CRITIQUE_R1)
        code, out = self.gate(1)
        self.assertEqual(code, 1)
        self.assertIn("missing: leg-1/ledger-1.md", out)

    def test_answer_ingested_after_the_ledger(self):
        self.round_one()
        log = self.session / "log-again.txt"
        log.write_text(CRITIQUE_R1.replace("nightly", "weekly"), encoding="utf-8")
        run(["ingest", "--session", str(self.session), "--seat", "A", "--leg", "1", "--round", "1",
             "--format", "critique-r1", "--log", str(log), "--force"])
        code, out = self.gate(1)
        self.assertEqual(code, 1)
        self.assertIn("stale: the seat answers changed after leg-1/ledger-1.md", out)
        self.assertEqual(self.ledger(1, "critique-r1")[0], 0)
        self.assertEqual(self.gate(1)[0], 0)

    def test_followup_needs_change_log(self):
        self.round_one()
        self.seat(2, "A", CRITIQUE_FOLLOWUP)
        self.seat(2, "B", CRITIQUE_FOLLOWUP.replace("B-C", "A-C"))
        self.assertEqual(self.ledger(2, "critique-followup")[0], 0)
        code, out = self.gate(2)
        self.assertEqual(code, 1)
        self.assertIn("missing: no 'Round 2' entry in leg-1/changes.md", out)
        changes = self.session / "leg-1/changes.md"
        changes.write_text("Round 1: no changes\n", encoding="utf-8")
        self.assertEqual(self.gate(2)[0], 1)
        changes.write_text("Round 2: A changed.\n", encoding="utf-8")
        self.assertEqual(self.gate(2)[0], 0)

    def test_dangling_reference_blocks(self):
        self.round_one()
        self.seat(2, "A", CRITIQUE_FOLLOWUP)
        self.seat(2, "B", CRITIQUE_FOLLOWUP.replace("B-C2", "A-C9").replace("B-C1", "A-C1"), code=1)
        self.ledger(2, "critique-followup")
        (self.session / "leg-1/changes.md").write_text("Round 2: no changes\n", encoding="utf-8")
        code, out = self.gate(2)
        self.assertEqual(code, 1)
        self.assertIn("dangling: leg-1 round 2: B cites A-C9", out)

    def test_leak_blocks(self):
        self.round_one()
        path = self.session / "leg-1/ledger-1.md"
        path.write_text(path.read_text(encoding="utf-8") + "Seat B (GPT-5.5) holds.\n",
                        encoding="utf-8")
        code, out = self.gate(1)
        self.assertEqual(code, 1)
        self.assertIn("leak: leg-1/ledger-1.md", out)

    def test_missing_seats_json_exits_2(self):
        (self.session / "seats.json").unlink()
        self.assertEqual(self.gate(1)[0], 2)

    def test_bad_round_exits_2(self):
        self.assertEqual(self.gate("two")[0], 2)


if __name__ == "__main__":
    unittest.main()
