from pathlib import Path
import subprocess
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[1]

class WorkspaceIsolationTests(unittest.TestCase):
    def test_legacy_rules_refresh_without_removing_either_workspace(self):
        with tempfile.TemporaryDirectory() as temporary:
            project = Path(temporary)
            for name in ('.drobotics', '.drobotics-s'):
                (project / name).mkdir()
                (project / name / "user-data").write_text("keep")
            legacy = '# X5 Workspace Rules\n\nIf the user request involves X5 OpenExplorer related topics\n(quantization, compile, deploy, evaluation, training, CLI usage, version issues),\nyou MUST follow the project rules defined in .drobotics/X5.md.\n\nFor X5 OpenExplorer related tasks:\n- Do NOT guess toolchain APIs or CLI parameters based on general LLM knowledge.\n- If uncertain, use .drobotics/scripts/search_local_docs.py to retrieve local documentation before answering.\n'
            (project / "AGENTS.md").write_text(legacy + "\n# User rules\nKeep my settings.\n")
            for args in ([], [], ["--update", "--force"]):
                subprocess.run(["bash", str(ROOT / "setup.sh"), *args, str(project)], check=True, capture_output=True)
                text = (project / "AGENTS.md").read_text()
                self.assertEqual(text.count("you MUST follow the project rules"), 1)
                self.assertIn('.drobotics-x5' + "/" + 'X5.md', text)
                self.assertNotIn('.drobotics' + "/", text)
                self.assertIn("mcp__rdk_docs__search_docs", text)
                self.assertIn("mcp__rdk_docs__get_page", text)
                self.assertIn("If MCP is unavailable", text)
                self.assertNotIn("search_local_docs.py", text)
                self.assertIn("# User rules\nKeep my settings.", text)
                for name in ('.drobotics', '.drobotics-s'):
                    self.assertEqual((project / name / "user-data").read_text(), "keep")
                self.assertTrue((project / '.drobotics-x5' / 'X5.md').is_file())
