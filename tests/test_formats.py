import tempfile
import unittest
from pathlib import Path

from helpers import ROOT, hive, run

FORMAT_IDS = [
    "brainstorm-followup", "brainstorm-r1", "critique-followup", "critique-r1",
    "decide-followup", "decide-r1", "explore-followup", "explore-r1",
    "fairness", "select", "solve-followup", "solve-r1",
]


class FormatsTest(unittest.TestCase):
    def setUp(self):
        self.formats = hive.load_formats()
        self.prompts = (ROOT / "paseo-hive/references/prompts.md").read_text(encoding="utf-8")

    def test_all_format_ids_present(self):
        self.assertEqual(sorted(self.formats["formats"]), FORMAT_IDS)

    def test_prompts_and_formats_agree(self):
        self.assertEqual(hive.format_drift(self.prompts, self.formats), [])

    def test_drift_is_detected(self):
        changed = self.prompts.replace("WEAKEST ASSUMPTION:", "WEAK SPOT:", 1)
        fails = hive.format_drift(changed, self.formats)
        self.assertTrue(any(f.startswith("critique-r1:") for f in fails), fails)

    def test_solve_field_drift_is_detected(self):
        changed = self.prompts.replace("DIAGNOSIS:", "CAUSE:", 1)
        fails = hive.format_drift(changed, self.formats)
        self.assertTrue(any(f.startswith("solve-r1:") for f in fails), fails)

    def test_select_block_is_parsed(self):
        self.assertEqual(hive.prompt_formats(self.prompts)["select"],
                         ["SHORTLIST", "WILDCARD KEEP", "DROP"])

    def test_followup_block_is_parsed(self):
        self.assertEqual(hive.prompt_formats(self.prompts)["brainstorm-followup"],
                         ["BUILDS", "NEW", "STATUS", "QUESTION FOR THE USER"])

    def test_bad_json_is_usage_error(self):
        with tempfile.TemporaryDirectory() as d:
            path = Path(d) / "formats.json"
            path.write_text("{", encoding="utf-8")
            with self.assertRaises(hive.HiveError):
                hive.load_formats(path)

    def test_malformed_structure_is_usage_error(self):
        with tempfile.TemporaryDirectory() as d:
            path = Path(d) / "formats.json"
            path.write_text('{"formats": {"x": {"fields": "POSITION"}}, "word_limits": {}}', encoding="utf-8")
            with self.assertRaises(hive.HiveError):
                hive.load_formats(path)

    def test_nested_malformed_formats_are_usage_errors(self):
        cases = [
            '{"formats": {"x": []}, "word_limits": {}}',
            '{"formats": {"x": {"limit": "mode", "fields": [{"name": "CLAIMS", "kind": "items"}]}}, '
            '"word_limits": {"standard": 250}}',
            '{"formats": {"x": {"limit": "mode", "fields": [{"name": "STATUS", "kind": "choice"}]}}, '
            '"word_limits": {"standard": 250}}',
            '{"formats": {}, "word_limits": {"standard": "250"}}',
            '{"formats": {}, "word_limits": {}, "tolerance": "a lot"}',
        ]
        with tempfile.TemporaryDirectory() as d:
            path = Path(d) / "formats.json"
            for text in cases:
                path.write_text(text, encoding="utf-8")
                with self.assertRaises(hive.HiveError, msg=text):
                    hive.load_formats(path)

    def test_non_utf8_file_is_usage_error(self):
        with tempfile.TemporaryDirectory() as d:
            path = Path(d) / "formats.json"
            path.write_bytes(b"\xff\xfe{")
            with self.assertRaises(hive.HiveError):
                hive.load_formats(path)

    def test_unknown_format_is_usage_error(self):
        with self.assertRaises(hive.HiveError):
            hive.get_format(self.formats, "nope")


class MainTest(unittest.TestCase):
    def test_no_command_is_usage_error(self):
        self.assertEqual(run([])[0], 2)

    def test_help_exits_0(self):
        self.assertEqual(run(["--help"])[0], 0)


if __name__ == "__main__":
    unittest.main()
