"""Tests for the benchmark fixture and the example findings file.

These tests check that the fixture still contains its planted anchors and that
the example record is internally consistent. They do not grade editorial quality.
"""

from __future__ import annotations

import hashlib
import json
import subprocess
import tempfile
import unittest
from pathlib import Path

import support
from common import read_json
from index_manuscript import index_manuscript
from schema_check import validate_instance


FIXTURE = support.ROOT / "examples" / "benchmark" / "the-lantern-house.md"
KEY = support.ROOT / "examples" / "benchmark" / "known-issues.md"
FINDINGS = support.ROOT / "templates" / "findings.json"


class BenchmarkTests(unittest.TestCase):
    """The fixture, the answer key, and the example findings stay aligned."""

    def test_answer_key_quotes_exist_in_the_fixture(self) -> None:
        """Every answer-key quotation is present in the manuscript text."""
        manuscript = FIXTURE.read_text(encoding="utf-8")
        quotes = [
            line.split("quote:", 1)[1].strip()
            for line in KEY.read_text(encoding="utf-8").splitlines()
            if line.strip().startswith("- quote:")
        ]
        self.assertGreaterEqual(len(quotes), 8)
        for quote in quotes:
            self.assertIn(quote, manuscript)

    def test_planted_anchors_land_in_the_expected_chapters(self) -> None:
        """The indexer keeps the planted facts in separate, explicit chapters."""
        before = hashlib.sha256(FIXTURE.read_bytes()).hexdigest()
        document = index_manuscript(FIXTURE)
        self.assertEqual(hashlib.sha256(FIXTURE.read_bytes()).hexdigest(), before)
        self.assertFalse(document["segmentation"]["ambiguous"])
        self.assertEqual(document["segmentation"]["method"], "explicit-chapter-title")
        self.assertEqual(document["counts"]["chapters"], 4)
        self.assertEqual(self._chapter(document, "Tuesday, 12 March"), "c001")
        self.assertEqual(self._chapter(document, "Wednesday, 12 March"), "c002")
        self.assertEqual(self._chapter(document, "green eyes"), "c001")
        self.assertEqual(self._chapter(document, "blue eyes"), "c003")
        self.assertEqual(self._chapter(document, "Elena set her wet gloves"), "c001")
        self.assertEqual(self._chapter(document, "Marco was in the attic, alive"), "c004")
        self.assertEqual(self._chapter(document, "That Monday was months ago."), "c002")
        self.assertGreaterEqual(FIXTURE.read_text(encoding="utf-8").count("1888"), 4)
        schema = read_json(support.ROOT / "templates" / "manuscript-index.schema.json")
        self.assertEqual(validate_instance(document, schema), [])

    def test_example_findings_verify_against_the_fixture(self) -> None:
        """The checked-in example survives schema and quotation checks."""
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            index_path = root / "index.json"
            support.run_script(
                "index_manuscript.py",
                [str(FIXTURE), "--output", str(index_path)],
                cwd=root,
            )
            report_path = root / "verification.json"
            completed = support.run_script(
                "verify_evidence.py",
                [
                    "--index",
                    str(index_path),
                    "--findings",
                    str(FINDINGS),
                    "--output",
                    str(report_path),
                ],
                cwd=root,
            )
            diagnostic = _verification_diagnostic(completed, index_path, report_path)
            self.assertEqual(completed.returncode, 0, diagnostic)
            report = json.loads(report_path.read_text(encoding="utf-8"))
            self.assertEqual(report["schema_errors"], [], diagnostic)
            self.assertEqual(report["semantic_errors"], [], diagnostic)
            self.assertTrue(
                all(item["quote_check"] == "verified_exact" for item in report["results"]),
                diagnostic,
            )
            self.assertTrue(
                all(item["editorial_judgment"] == "not_assessed" for item in report["results"]),
                diagnostic,
            )
            self.assertNotIn(b"\r", FIXTURE.read_bytes(), diagnostic)
            self.assertEqual(hashlib.sha256(FIXTURE.read_bytes()).hexdigest(), before_hash(), diagnostic)

    def test_report_template_has_the_twelve_sections(self) -> None:
        """The report template keeps the required sections and refuses a score."""
        template = (support.ROOT / "templates" / "editorial-report.md").read_text(encoding="utf-8")
        for heading in (
            "Editorial synthesis",
            "Strengths",
            "Priority problems",
            "Structure",
            "Characters",
            "Pace and tension",
            "Dialogue and style",
            "Narrative continuity",
            "Chapter notes",
            "Contested or rejected observations",
            "Suggested interventions",
            "Limits of the analysis",
            "Sintesi editoriale",
        ):
            self.assertIn(heading, template)
        self.assertIn("numeric score", template.lower())

    def _chapter(self, document: dict, snippet: str) -> str:
        """Return the chapter id of the only paragraph containing a snippet.

        Args:
            document: Index document.
            snippet: Text that should occur in one paragraph.

        Returns:
            The chapter id of that paragraph.
        """
        hits = [item for item in document["paragraphs"] if snippet in item["text"]]
        self.assertEqual(len(hits), 1, snippet)
        return hits[0]["chapter_id"]


def _verification_diagnostic(
    completed: subprocess.CompletedProcess[str],
    index_path: Path,
    report_path: Path,
) -> str:
    """Collect the hashes and the verification report for a failed assertion.

    Args:
        completed: The verifier process.
        index_path: Index written for this run.
        report_path: Verification report path, which may be missing.

    Returns:
        Stdout, stderr, the fixture and index digests, and the report text.
    """
    fixture_bytes = FIXTURE.read_bytes()
    findings = json.loads(FINDINGS.read_text(encoding="utf-8"))
    lines = [
        completed.stdout,
        completed.stderr,
        f"findings manuscript_sha256: {findings.get('manuscript_sha256')}",
        f"fixture sha256: {hashlib.sha256(fixture_bytes).hexdigest()}",
        f"fixture byte_length: {len(fixture_bytes)}",
        f"fixture contains CR: {bytes([13]) in fixture_bytes}",
    ]
    if index_path.is_file():
        source = json.loads(index_path.read_text(encoding="utf-8")).get("source", {})
        lines.append(f"index sha256: {source.get('sha256')}")
        lines.append(f"index byte_length: {source.get('byte_length')}")
    if report_path.is_file():
        lines.append(report_path.read_text(encoding="utf-8"))
    else:
        lines.append("verification.json was not written")
    return "\n".join(line for line in lines if line)


def before_hash() -> str:
    """Hash the fixture.

    Returns:
        SHA-256 of the benchmark manuscript.
    """
    return hashlib.sha256(FIXTURE.read_bytes()).hexdigest()


if __name__ == "__main__":
    unittest.main()
