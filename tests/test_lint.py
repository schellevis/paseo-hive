import shutil
import tempfile
import unittest
from pathlib import Path

from helpers import ROOT, hive, run


class LintTest(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.root = Path(self.tmp.name)
        shutil.copytree(ROOT / "paseo-hive", self.root / "paseo-hive",
                        ignore=shutil.ignore_patterns("__pycache__"))
        shutil.copy2(ROOT / "AGENTS.md", self.root / "AGENTS.md")

    def tearDown(self):
        self.tmp.cleanup()

    def edit(self, rel, old, new):
        path = self.root / rel
        text = path.read_text(encoding="utf-8")
        self.assertIn(old, text)
        path.write_text(text.replace(old, new, 1), encoding="utf-8")

    def test_repository_passes(self):
        self.assertEqual(hive.lint(ROOT), [])

    def test_long_skill_md(self):
        path = self.root / "paseo-hive/SKILL.md"
        path.write_text(path.read_text(encoding="utf-8") + "x\n" * 200, encoding="utf-8")
        self.assertTrue(any(f.startswith("SKILL.md has") for f in hive.lint(self.root)))

    def test_missing_link(self):
        self.edit("paseo-hive/SKILL.md", "](references/panel.md)", "](references/nope.md)")
        self.assertIn("SKILL.md links to missing references/nope.md", hive.lint(self.root))

    def test_status_count(self):
        self.edit("paseo-hive/references/prompts.md", "\nSTATUS: continue | nothing new", "\nSTATE: continue")
        self.assertIn("prompts.md has 3 STATUS lines (want 4)", hive.lint(self.root))

    def test_heading_count(self):
        self.edit("paseo-hive/references/goals.md", "### Minimum engagement", "### Min engagement")
        self.assertIn("goals.md has 3 '### Minimum engagement' headings (want 4)", hive.lint(self.root))

    def test_verbatim_sentence(self):
        self.edit("paseo-hive/SKILL.md", "Stop when another round cannot settle anything.", "Stop when done.")
        self.assertTrue(any("verbatim" in f for f in hive.lint(self.root)))

    def test_field_list_in_agents_md(self):
        self.edit("AGENTS.md", "`CRUX`", "`CRUXES`")
        fails = hive.lint(self.root)
        self.assertIn("field CRUXES missing from prompts.md", fails)
        self.assertIn("field CRUXES missing from formats.json", fails)

    def test_format_drift(self):
        self.edit("paseo-hive/references/prompts.md", "WEAKEST ASSUMPTION:", "WEAK SPOT:")
        self.assertTrue(any(f.startswith("critique-r1:") for f in hive.lint(self.root)))

    def test_cli_exit_codes(self):
        self.assertEqual(run(["lint", str(self.root)])[0], 0)
        self.edit("paseo-hive/SKILL.md", "](references/panel.md)", "](references/nope.md)")
        self.assertEqual(run(["lint", str(self.root)])[0], 1)


if __name__ == "__main__":
    unittest.main()
