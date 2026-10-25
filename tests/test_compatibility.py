"""Package checks for Cursor, Codex, and Claude Code.

These tests do not launch the three products. They check the shared package
against the discovery rules those products publish. A passing result does not
mean a live session produced the same editorial judgment.
"""

from __future__ import annotations

import ast
import sys
import tempfile
import unittest
from pathlib import Path

import support
from install_skill import destination
from skill_manifest import SPEC_KEYS, parse_frontmatter, validate_skill_directory


TRIGGER_PHRASES = (
    "professional editor",
    "full editorial review",
    "inconsistencies",
    "dialogue",
    "repetition",
    "critically verify",
    "editorial report",
)
LOCAL_MODULES = {
    "common",
    "extract_manuscript",
    "index_manuscript",
    "verify_evidence",
    "install_skill",
    "skill_manifest",
    "schema_check",
    "quotes",
    "finding_record",
    "score_findings",
    "check_report",
    "verify_ledger",
    "verify_decision_audit",
}


class CompatibilityTests(unittest.TestCase):
    """One package satisfies the published constraints of each client."""

    @classmethod
    def setUpClass(cls) -> None:
        """Load the manifest once for the client-specific assertions."""
        cls.text = (support.ROOT / "SKILL.md").read_text(encoding="utf-8")
        cls.metadata, cls.body = parse_frontmatter(cls.text)

    def test_cursor_package(self) -> None:
        """Cursor can discover the skill by name, description, and directory."""
        self.assertEqual(self.metadata["name"], support.ROOT.name)
        self.assertEqual(self.metadata["name"], "manuscript-lab")
        for phrase in TRIGGER_PHRASES:
            self.assertIn(phrase, self.metadata["description"])
        self.assertNotIn("disable-model-invocation", self.metadata)
        self.assertNotIn("paths", self.metadata)
        with tempfile.TemporaryDirectory() as directory:
            project = Path(directory)
            path = destination("cursor", "project", project)
        self.assertEqual(path.parts[-3:], (".cursor", "skills", "manuscript-lab"))

    def test_codex_package(self) -> None:
        """Codex can discover the skill under its agents skills directory."""
        self.assertTrue(self.metadata["name"])
        self.assertTrue(self.metadata["description"])
        self.assertTrue((support.ROOT / "scripts" / "extract_manuscript.py").is_file())
        self.assertTrue((support.ROOT / "references" / "editorial-methodology.md").is_file())
        with tempfile.TemporaryDirectory() as directory:
            path = destination("codex", "project", Path(directory))
        self.assertEqual(path.parts[-3:], (".agents", "skills", "manuscript-lab"))

    def test_claude_code_package(self) -> None:
        """Claude Code can load the manifest without client-only fields."""
        self.assertTrue(set(self.metadata) <= SPEC_KEYS)
        self.assertNotIn("$ARGUMENTS", self.text)
        self.assertNotIn("${CLAUDE_", self.text)
        self.assertIsNone(__import__("re").search(r"\$\d", self.text))
        with tempfile.TemporaryDirectory() as directory:
            path = destination("claude", "project", Path(directory))
        self.assertEqual(path.parts[-3:], (".claude", "skills", "manuscript-lab"))
        self.assertLessEqual(len(self.text.splitlines()), 500)
        self.assertLessEqual(len(self.metadata["description"]), 1024)
        self.assertEqual(validate_skill_directory(support.ROOT), [])

    def test_scripts_use_the_standard_library_only(self) -> None:
        """The skill does not import an agent SDK or another third-party package."""
        for path in (support.ROOT / "scripts").glob("*.py"):
            tree = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
            for node in ast.walk(tree):
                modules = _imported_modules(node)
                for module in modules:
                    root_name = module.split(".", 1)[0]
                    if root_name in LOCAL_MODULES:
                        continue
                    self.assertIn(
                        root_name,
                        sys.stdlib_module_names,
                        f"{path.name} imports {module}",
                    )

    def test_documentation_names_every_client_and_system(self) -> None:
        """Install instructions cover the three clients and the three systems."""
        readme = (support.ROOT / "README.md").read_text(encoding="utf-8")
        for phrase in (
            "Windows",
            "macOS",
            "Linux",
            ".cursor/skills/manuscript-lab",
            ".agents/skills/manuscript-lab",
            ".claude/skills/manuscript-lab",
            "does not prove",
        ):
            self.assertIn(phrase, readme)
        skill_files = list(support.ROOT.rglob("SKILL.md"))
        self.assertEqual(skill_files, [support.ROOT / "SKILL.md"])


def _imported_modules(node: ast.AST) -> list[str]:
    """Return module names imported by one AST node.

    Args:
        node: Any syntax node. Import nodes contribute module names.

    Returns:
        Imported module names. An empty list for every other node.
    """
    if isinstance(node, ast.Import):
        return [alias.name for alias in node.names]
    if isinstance(node, ast.ImportFrom) and node.module and node.level == 0:
        return [node.module]
    return []


if __name__ == "__main__":
    unittest.main()
