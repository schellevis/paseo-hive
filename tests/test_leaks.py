import json
import shutil
import subprocess
import tempfile
import unittest
from pathlib import Path

from helpers import ROOT, hive, run

SEATS = {"session": "20260101-0900-test", "goal": "critique", "mode": "standard", "seats": [
    {"letter": "A", "role": "Skeptic", "provider": "claude", "model": "claude-sonnet-5",
     "label": "Sonnet 5", "agent": "a1", "thinking": "high"},
    {"letter": "B", "role": "Alternative", "provider": "codex", "model": "gpt-5.5",
     "label": "GPT-5.5", "agent": "b1", "thinking": "low"},
]}

EMAIL = "someone" + "@" + "example.org"
LOCAL_PATH = "/" + "home/someone/notes"


class SessionLeaksTest(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.dir = Path(self.tmp.name)
        (self.dir / "seats.json").write_text(json.dumps(SEATS), encoding="utf-8")

    def tearDown(self):
        self.tmp.cleanup()

    def write(self, rel, text):
        path = self.dir / rel
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(text, encoding="utf-8")
        return path

    def leaks(self, *files):
        return run(["leaks", "--session", str(self.dir), *files])

    def test_clean_session(self):
        self.write("checkpoint-1.md", "# Checkpoint\nSeat A holds.\n")
        self.assertEqual(self.leaks(), (0, "ok: no leaks\n"))

    def test_model_label_in_checkpoint(self):
        self.write("checkpoint-1.md", "Seat A (Sonnet 5) holds.\n")
        code, out = self.leaks()
        self.assertEqual(code, 1)
        self.assertIn("checkpoint-1.md:1: Sonnet 5", out)

    def test_role_in_ledger(self):
        self.write("leg-1/ledger-1.md", "The Skeptic says no.\n")
        self.assertIn("leg-1/ledger-1.md:1: Skeptic", self.leaks()[1])

    def test_prose_words_are_not_roles(self):
        self.write("leg-1/round-1/A.md", "A skeptical reading suggests an alternative plan.\n")
        self.assertEqual(self.leaks()[0], 0)

    def test_user_only_files_are_skipped(self):
        self.write("brief.md", "A Skeptic Sonnet 5\n")
        self.write("transcript.md", "B Alternative GPT-5.5\n")
        self.assertEqual(self.leaks()[0], 0)

    def test_explicit_file_is_scanned(self):
        path = self.write("prompts/r2-A.md", "Seat B runs on GPT-5.5.\n")
        code, out = self.leaks(str(path))
        self.assertEqual(code, 1)
        self.assertIn("prompts/r2-A.md:1: gpt-5.5", out)  # reported under the first matching term

    def test_replaced_seat_names_stay_forbidden(self):
        seats = json.loads(json.dumps(SEATS))
        seats["seats"][1]["replaced"] = True
        seats["seats"].append({"letter": "B", "role": "Alternative", "provider": "mistral-vibe",
                               "model": "glm-5-3", "label": "GLM-5.3", "agent": "b2", "thinking": "none"})
        (self.dir / "seats.json").write_text(json.dumps(seats), encoding="utf-8")
        self.write("checkpoint-1.md", "Earlier this seat ran GPT-5.5; now GLM-5.3.\n")
        out = self.leaks()[1]
        self.assertIn("checkpoint-1.md:1: gpt-5.5", out)
        self.assertIn("checkpoint-1.md:1: GLM-5.3", out)

    def test_missing_explicit_file_exits_2(self):
        self.assertEqual(self.leaks(str(self.dir / "prompts/nope.md"))[0], 2)

    def test_non_utf8_seat_file_exits_2(self):
        (self.dir / "checkpoint-1.md").write_bytes(b"caf\xe9\n")
        self.assertEqual(self.leaks()[0], 2)

    def test_malformed_seats_json_exits_2(self):
        (self.dir / "seats.json").write_text("[]", encoding="utf-8")
        self.assertEqual(self.leaks()[0], 2)

    def test_non_string_seat_name_exits_2(self):
        (self.dir / "seats.json").write_text('{"seats": [{"letter": "A", "model": 7}]}', encoding="utf-8")
        code, out = self.leaks()
        self.assertEqual(code, 2)
        self.assertEqual(out, "")

    def test_missing_seats_json_exits_2(self):
        (self.dir / "seats.json").unlink()
        self.assertEqual(self.leaks()[0], 2)


@unittest.skipUnless(shutil.which("git"), "git not installed")
class RepoLeaksTest(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.dir = Path(self.tmp.name)
        subprocess.run(["git", "init", "-q", str(self.dir)], check=True)

    def tearDown(self):
        self.tmp.cleanup()

    def add(self, name, text):
        (self.dir / name).write_text(text, encoding="utf-8")
        subprocess.run(["git", "-C", str(self.dir), "add", name], check=True)

    def test_email_and_local_path_are_flagged(self):
        self.add("notes.md", f"mail {EMAIL}\nsee {LOCAL_PATH}\n")
        code, out = run(["leaks", "--repo", str(self.dir)])
        self.assertEqual(code, 1)
        self.assertIn("notes.md:1: email", out)
        self.assertIn("notes.md:2: local path", out)

    def test_license_and_agents_md_are_skipped(self):
        self.add("LICENSE", f"Copyright {EMAIL}\n")
        self.add("AGENTS.md", f"grep {LOCAL_PATH}\n")
        self.assertEqual(run(["leaks", "--repo", str(self.dir)])[0], 0)

    def test_opsec_extra_terms(self):
        (self.dir / ".opsec-extra").write_text("# my identifiers\nSample Widgets\n", encoding="utf-8")
        self.add("README.md", "Built at sample widgets.\n")
        code, out = run(["leaks", "--repo", str(self.dir)])
        self.assertEqual(code, 1)
        self.assertIn("README.md:1: Sample Widgets", out)

    def test_untracked_files_are_ignored(self):
        (self.dir / "stray.md").write_text(f"{EMAIL}\n", encoding="utf-8")
        self.assertEqual(run(["leaks", "--repo", str(self.dir)])[0], 0)

    def test_not_a_git_checkout_exits_2(self):
        with tempfile.TemporaryDirectory() as plain:
            self.assertEqual(run(["leaks", "--repo", plain])[0], 2)


@unittest.skipUnless(shutil.which("git") and (ROOT / ".git").exists(), "not a git checkout")
class ThisRepositoryTest(unittest.TestCase):
    def test_tracked_files_are_clean(self):
        code, out = run(["leaks", "--repo", str(ROOT)])
        self.assertEqual(code, 0, out)


if __name__ == "__main__":
    unittest.main()
