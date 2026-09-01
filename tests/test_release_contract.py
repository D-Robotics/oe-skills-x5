"""Release contract tests for the X5 v1.0.0 source tree."""

from __future__ import annotations

import subprocess
import tempfile
import unittest
import os
from pathlib import Path
import yaml


REPOSITORY_ROOT = Path(__file__).resolve().parents[1]
SETUP_SCRIPT = "setup.sh"
SOURCE_VERSION = "1.0.0"
RELEASE_REF = "v1.0.0"
CREATE_APP_TOKEN_ACTION = (
    "actions/create-github-app-token@"
    "fee1f7d63c2ff003460e3d139729b119787bc349"
)


def read_frontmatter(skill_file: Path) -> dict[str, str]:
    """Read the simple scalar frontmatter required by the Skill contract."""
    lines = skill_file.read_text(encoding="utf-8").splitlines()
    if not lines or lines[0] != "---":
        return {}

    frontmatter: dict[str, str] = {}
    for line in lines[1:]:
        if line == "---":
            return frontmatter
        key, separator, value = line.partition(":")
        if separator:
            frontmatter[key.strip()] = value.strip().strip('"').strip("'")
    return {}


class X5ReleaseContractTests(unittest.TestCase):
    @staticmethod
    def bash_path(path: Path) -> str:
        """Use the WSL mount form when Windows launches the local Bash executable."""
        if os.name != "nt":
            return str(path)
        return f"/mnt/{path.drive[0].lower()}/{path.relative_to(path.anchor).as_posix()}"

    def run_setup(self, *arguments: str, check: bool = True) -> subprocess.CompletedProcess[str]:
        return subprocess.run(
            ["bash", SETUP_SCRIPT, *arguments],
            check=check,
            cwd=REPOSITORY_ROOT,
            capture_output=True,
            text=True,
            encoding="utf-8",
            errors="replace",
        )

    def test_all_skills_have_v1_release_frontmatter(self) -> None:
        """Catch a shipped Skill missing required release metadata."""
        skill_files = sorted((REPOSITORY_ROOT / "x5" / "skills").glob("**/SKILL.md"))
        self.assertTrue(skill_files, "the X5 release must include Skills")

        for skill_file in skill_files:
            with self.subTest(skill=skill_file.parent.name):
                metadata = read_frontmatter(skill_file)
                self.assertEqual(metadata.get("name"), skill_file.parent.name)
                self.assertTrue(metadata.get("description"))
                self.assertEqual(metadata.get("license"), "Apache-2.0")
                self.assertEqual(metadata.get("version"), SOURCE_VERSION)

    def test_source_version_is_v1_release(self) -> None:
        """Catch a setup source that would install a version other than v1.0.0."""
        self.assertEqual((REPOSITORY_ROOT / "x5" / "VERSION").read_text().strip(), SOURCE_VERSION)

    def test_fresh_install_records_release_ref_and_version(self) -> None:
        """Catch a fresh --ref install that fails to preserve its release anchor."""
        with tempfile.TemporaryDirectory() as temporary_directory:
            project = Path(temporary_directory) / "project"
            project.mkdir()

            result = self.run_setup("--ref", RELEASE_REF, self.bash_path(project))

            installed = project / ".drobotics"
            self.assertEqual((installed / "VERSION").read_text().strip(), SOURCE_VERSION)
            self.assertEqual((installed / "INSTALLED_REF").read_text().strip(), RELEASE_REF)
            self.assertNotIn("No such file or directory", result.stderr)

    def test_update_with_same_version_is_a_no_op(self) -> None:
        """Catch an --update path that rebuilds a matching installation."""
        with tempfile.TemporaryDirectory() as temporary_directory:
            project = Path(temporary_directory) / "project"
            project.mkdir()
            self.run_setup(self.bash_path(project))
            sentinel = project / ".drobotics" / "preserve-on-no-op.txt"
            sentinel.write_text("keep", encoding="utf-8")

            result = self.run_setup("--update", self.bash_path(project))

            self.assertIn("Already up to date", result.stdout)
            self.assertEqual(sentinel.read_text(encoding="utf-8"), "keep")

    def test_update_with_different_version_rebuilds_workspace(self) -> None:
        """Catch an --update path that leaves stale content after a version change."""
        with tempfile.TemporaryDirectory() as temporary_directory:
            project = Path(temporary_directory) / "project"
            project.mkdir()
            self.run_setup(self.bash_path(project))
            installed = project / ".drobotics"
            (installed / "VERSION").write_text("0.9.0\n", encoding="utf-8")
            stale_file = installed / "stale-from-prior-release.txt"
            stale_file.write_text("remove", encoding="utf-8")

            result = self.run_setup("--update", self.bash_path(project))

            self.assertIn("Upgrade: 0.9.0 -> 1.0.0", result.stdout)
            self.assertFalse(stale_file.exists())
            self.assertEqual((installed / "VERSION").read_text().strip(), SOURCE_VERSION)

    def test_force_rebuilds_matching_workspace(self) -> None:
        """Catch --force being ignored when the installed version already matches."""
        with tempfile.TemporaryDirectory() as temporary_directory:
            project = Path(temporary_directory) / "project"
            project.mkdir()
            self.run_setup(self.bash_path(project))
            stale_file = project / ".drobotics" / "stale-before-force.txt"
            stale_file.write_text("remove", encoding="utf-8")

            self.run_setup("--update", "--force", self.bash_path(project))

            self.assertFalse(stale_file.exists())

    def test_unknown_option_is_rejected(self) -> None:
        """Catch unsupported setup flags being accepted as a project path or ignored."""
        result = self.run_setup("--unsupported", check=False)

        self.assertEqual(result.returncode, 2)
        self.assertIn("未知参数", result.stderr)

    def test_published_release_notifies_hub_with_verified_payload(self) -> None:
        workflow_path = REPOSITORY_ROOT / ".github" / "workflows" / "notify-hub-release.yml"
        workflow = workflow_path.read_text(encoding="utf-8")
        document = yaml.load(workflow, Loader=yaml.BaseLoader)

        self.assertEqual(document["on"], {"release": {"types": ["published"]}})
        self.assertEqual(document["permissions"], {"contents": "read"})
        self.assertIn("RDK_RELEASE_DISPATCHER_PRIVATE_KEY", workflow)
        self.assertIn("github.event.release.prerelease", workflow)
        self.assertIn(CREATE_APP_TOKEN_ACTION, workflow)
        self.assertIn(
            "repos/D-Robotics/rdk-skills/actions/workflows/component-upgrade.yml/dispatches",
            workflow,
        )
        self.assertIn("^[0-9a-fA-F]{40}$", workflow)

        token_step = next(
            step
            for step in document["jobs"]["notify-hub"]["steps"]
            if step.get("uses") == CREATE_APP_TOKEN_ACTION
        )
        self.assertEqual(
            token_step["with"]["app-id"],
            "${{ vars.RDK_RELEASE_DISPATCHER_APP_ID }}",
        )
        self.assertEqual(
            token_step["with"]["private-key"],
            "${{ secrets.RDK_RELEASE_DISPATCHER_PRIVATE_KEY }}",
        )
        self.assertEqual(token_step["with"]["permission-actions"], "write")
        self.assertNotIn("permission-contents", token_step["with"])

        expected_payload_fields = {
            "schema_version",
            "source_repo",
            "tag",
            "release_url",
            "target_sha",
            "published_at",
        }
        self.assertEqual(
            set(document["jobs"]["notify-hub"]["steps"][-1]["env"]),
            expected_payload_fields,
        )


if __name__ == "__main__":
    unittest.main()
