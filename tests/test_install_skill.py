"""Tests for installing one skill directory into the three agent layouts."""

from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

import support
from install_skill import InstallError, destination, install_skill
from install_skill import _replace_existing


class InstallTests(unittest.TestCase):
    """The installer publishes the same directory to each client."""

    def test_destinations_for_each_agent(self) -> None:
        """Project and user paths match the documented client layouts."""
        with tempfile.TemporaryDirectory() as directory:
            project = Path(directory)
            expected = {
                "cursor": project / ".cursor" / "skills" / "manuscript-lab",
                "codex": project / ".agents" / "skills" / "manuscript-lab",
                "claude": project / ".claude" / "skills" / "manuscript-lab",
            }
            homes = {
                "cursor": Path.home() / ".cursor" / "skills" / "manuscript-lab",
                "codex": Path.home() / ".agents" / "skills" / "manuscript-lab",
                "claude": Path.home() / ".claude" / "skills" / "manuscript-lab",
            }
            for agent, path in expected.items():
                self.assertEqual(destination(agent, "project", project), path)
                self.assertEqual(destination(agent, "user"), homes[agent])

    def test_dry_run_all_warns_cursor_without_writing(self) -> None:
        """A dry run reports every client and does not create directories."""
        with tempfile.TemporaryDirectory() as directory:
            project = Path(directory)
            completed = support.run_script(
                "install_skill.py",
                ["--agent", "all", "--scope", "project", "--project", str(project), "--dry-run"],
            )
            self.assertEqual(completed.returncode, 0, completed.stderr)
            self.assertIn("more than once", completed.stderr)
            for relative in (".cursor", ".agents", ".claude"):
                self.assertIn(relative, completed.stdout)
                self.assertFalse((project / relative).exists())

    def test_copy_runs_from_another_directory(self) -> None:
        """A copied install extracts a manuscript without the original cwd."""
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            project = root / "novel"
            project.mkdir()
            elsewhere = root / "elsewhere"
            elsewhere.mkdir()
            messages = install_skill(["cursor"], "project", project, copy=True)
            self.assertIn("copied", messages[0])
            installed = project / ".cursor" / "skills" / "manuscript-lab"
            manuscript = project / "story.txt"
            manuscript.write_text("Chapter 1\n\nShe arrived.\n", encoding="utf-8")
            before = manuscript.read_bytes()
            completed = support.run_script(
                "extract_manuscript.py",
                [str(manuscript)],
                cwd=elsewhere,
            )
            copied = support.run_installed(installed, manuscript, elsewhere)
            self.assertEqual(completed.returncode, 0, completed.stderr)
            self.assertEqual(copied.returncode, 0, copied.stderr)
            self.assertIn("She arrived.", copied.stdout)
            self.assertEqual(manuscript.read_bytes(), before)
            self.assertNotEqual(installed.resolve(), support.ROOT.resolve())

    def test_link_follows_the_canonical_skill(self) -> None:
        """A link points at the canonical SKILL.md and survives replacement."""
        with tempfile.TemporaryDirectory() as directory:
            project = Path(directory)
            install_skill(["codex"], "project", project, copy=False)
            linked = project / ".agents" / "skills" / "manuscript-lab" / "SKILL.md"
            self.assertTrue(linked.exists())
            self.assertEqual(linked.resolve(), (support.ROOT / "SKILL.md").resolve())
            install_skill(["codex"], "project", project, copy=False, force=True)
            self.assertTrue((support.ROOT / "SKILL.md").is_file())
            self.assertEqual(linked.resolve(), (support.ROOT / "SKILL.md").resolve())

    def test_refuses_unguarded_replacement_and_self_install(self) -> None:
        """The installer will not delete an unrelated directory or link into itself."""
        with tempfile.TemporaryDirectory() as directory:
            unrelated = Path(directory) / "manuscript-lab"
            unrelated.mkdir()
            with self.assertRaises(InstallError):
                _replace_existing(unrelated, force=True)
            with self.assertRaises(InstallError):
                install_skill(["cursor"], "project", support.ROOT, dry_run=True)
            self.assertTrue(unrelated.is_dir())


if __name__ == "__main__":
    unittest.main()
