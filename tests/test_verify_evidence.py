"""Tests for quotation checks and findings validation."""

from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path

import support
from index_manuscript import index_manuscript


class VerifyEvidenceTests(unittest.TestCase):
    """The verifier checks quotations and refuses to grade the interpretation."""

    def test_exact_normalized_and_missing_quotes(self) -> None:
        """Exact text passes, flexible punctuation is labeled, and inventions fail."""
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            index = self._index(root, 'She said "hello there friend" today and left.\n')
            exact = self._findings(index, "She said \"hello there friend\" today", "unchecked")
            exact_report = self._verify(root, index, exact)
            self.assertEqual(exact_report.returncode, 0, exact_report.stderr)
            exact_body = json.loads(exact_report.stdout)
            self.assertEqual(exact_body["results"][0]["quote_check"], "verified_exact")
            self.assertEqual(exact_body["results"][0]["editorial_judgment"], "not_assessed")
            curly = self._findings(index, "She said \u201chello there friend\u201d today", "unchecked")
            curly_body = json.loads(self._verify(root, index, curly).stdout)
            self.assertEqual(curly_body["results"][0]["quote_check"], "verified_normalized")
            fake = self._findings(index, "She said a sentence that is not there.", "verified_exact")
            fake_run = self._verify(root, index, fake)
            self.assertEqual(fake_run.returncode, 1)
            self.assertEqual(json.loads(fake_run.stdout)["results"][0]["quote_check"], "not_found")

    def test_quote_in_another_paragraph_is_not_verified(self) -> None:
        """A real sentence cited from the wrong paragraph stays unverified."""
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            index = self._index(root, "She arrived in the rain.\n\nHe left before dawn.\n")
            findings = self._findings(index, "He left before dawn.", "unchecked")
            findings["findings"][0]["evidence"][0]["paragraph_id"] = index["paragraphs"][0]["id"]
            findings["findings"][0]["paragraph_ids"] = [index["paragraphs"][0]["id"]]
            completed = self._verify(root, index, findings)
            self.assertEqual(completed.returncode, 1)
            result = json.loads(completed.stdout)["results"][0]
            self.assertEqual(result["quote_check"], "not_found_at_cited_paragraph")
            self.assertIn(index["paragraphs"][1]["id"], result["found_in"])

    def test_schema_and_independence_rules(self) -> None:
        """Invalid records and same-model independent reviews fail closed."""
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            index = self._index(root, "She arrived before the storm.\n")
            broken = self._findings(index, "She arrived before the storm.", "unchecked")
            del broken["findings"][0]["title"]
            broken_run = self._verify(root, index, broken)
            self.assertEqual(broken_run.returncode, 1)
            self.assertTrue(json.loads(broken_run.stdout)["schema_errors"])
            same_model = self._findings(index, "She arrived before the storm.", "unchecked")
            same_model["independent_review"]["requested"] = True
            same_model["independent_review"]["performed"] = True
            same_model["independent_review"]["same_as_primary_model"] = True
            same_model["independent_review"]["reviewer_model"] = "same-model"
            same_run = self._verify(root, index, same_model)
            self.assertEqual(same_run.returncode, 1)
            self.assertTrue(json.loads(same_run.stdout)["semantic_errors"])
            mismatched = self._findings(index, "She arrived before the storm.", "unchecked")
            mismatched["manuscript_sha256"] = "b" * 64
            mismatch_run = self._verify(root, index, mismatched)
            self.assertEqual(mismatch_run.returncode, 1)
            self.assertIn("manuscript_sha256", json.loads(mismatch_run.stdout)["semantic_errors"][0])

    def test_completed_status_needs_a_counterargument(self) -> None:
        """A rejected finding without a counterargument is incomplete."""
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            index = self._index(root, "She arrived before the storm.\n")
            findings = self._findings(index, "She arrived before the storm.", "unchecked")
            findings["findings"][0]["verification_status"] = "rejected"
            completed = self._verify(root, index, findings)
            self.assertEqual(completed.returncode, 1)
            self.assertIn("counterargument", json.loads(completed.stdout)["semantic_errors"][0])

    def test_empty_findings_are_valid(self) -> None:
        """A review with nothing to file is a successful verification."""
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            index = self._index(root, "She arrived before the storm.\n")
            findings = self._findings(index, "She arrived before the storm.", "unchecked")
            findings["findings"] = []
            completed = self._verify(root, index, findings)
            self.assertEqual(completed.returncode, 0, completed.stderr)
            self.assertEqual(json.loads(completed.stdout)["evidence_checked"], 0)

    def test_update_does_not_touch_the_manuscript(self) -> None:
        """Updating findings writes a copy and can replace them only in place."""
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            elsewhere = root / "elsewhere"
            elsewhere.mkdir()
            source = root / "story.txt"
            source.write_text("She arrived before the storm.\n", encoding="utf-8")
            before = source.read_bytes()
            index = index_manuscript(source)
            index_path = root / "index.json"
            index_path.write_text(json.dumps(index), encoding="utf-8")
            findings = self._findings(index, "She arrived before the storm.", "unchecked")
            findings_path = root / "findings.json"
            findings_path.write_text(json.dumps(findings), encoding="utf-8")
            updated = root / "findings.checked.json"
            completed = support.run_script(
                "verify_evidence.py",
                [
                    "--index",
                    str(index_path),
                    "--findings",
                    str(findings_path),
                    "--output",
                    str(root / "verification.json"),
                    "--update-findings",
                    str(updated),
                ],
                cwd=elsewhere,
            )
            self.assertEqual(completed.returncode, 0, completed.stderr)
            self.assertEqual(source.read_bytes(), before)
            stored = json.loads(findings_path.read_text(encoding="utf-8"))
            self.assertEqual(stored["findings"][0]["evidence"][0]["quote_check"], "unchecked")
            checked = json.loads(updated.read_text(encoding="utf-8"))
            self.assertEqual(checked["findings"][0]["evidence"][0]["quote_check"], "verified_exact")
            refused = support.run_script(
                "verify_evidence.py",
                [
                    "--index",
                    str(index_path),
                    "--findings",
                    str(findings_path),
                    "--update-findings",
                    str(findings_path),
                ],
                cwd=elsewhere,
            )
            self.assertEqual(refused.returncode, 2)
            self.assertIn("in-place", refused.stderr)
            stored_again = json.loads(findings_path.read_text(encoding="utf-8"))
            self.assertEqual(stored_again["findings"][0]["evidence"][0]["quote_check"], "unchecked")

    def _index(self, root: Path, text: str) -> dict:
        """Write a temporary manuscript and index it.

        Args:
            root: Directory that will contain the manuscript.
            text: Manuscript text.

        Returns:
            The index document.
        """
        path = root / "story.txt"
        path.write_text(text, encoding="utf-8")
        return index_manuscript(path)

    def _findings(self, index: dict, quote: str, quote_check: str) -> dict:
        """Build one valid findings document around a quotation.

        Args:
            index: Index that supplies the hash and the first paragraph id.
            quote: Evidence quotation.
            quote_check: Stored quote status. The verifier recomputes it.

        Returns:
            A findings object.
        """
        paragraph_id = index["paragraphs"][0]["id"]
        return {
            "format_version": 1,
            "manuscript_sha256": index["source"]["sha256"],
            "mode": "continuity",
            "depth": "standard",
            "report_language": "en",
            "scope_chapters": [],
            "independent_review": {
                "requested": False,
                "performed": False,
                "reviewer_model": "",
                "same_as_primary_model": None,
                "note": "Not requested.",
            },
            "findings": [
                {
                    "id": "F-001",
                    "category": "continuity",
                    "title": "Sample",
                    "description": "Sample description for the verifier.",
                    "chapters": [],
                    "paragraph_ids": [paragraph_id],
                    "evidence": [
                        {
                            "paragraph_id": paragraph_id,
                            "quote": quote,
                            "quote_check": quote_check,
                        }
                    ],
                    "explanation": "The sample explanation is long enough.",
                    "narrative_impact": "The sample impact is local.",
                    "priority": "low",
                    "judgment_type": "factual",
                    "suggested_intervention": "Leave the wording to the author.",
                    "counterarguments": [],
                    "verification_status": "unreviewed",
                    "uncertainty": "",
                }
            ],
        }

    def _verify(self, root: Path, index: dict, findings: dict):
        """Run the verifier on temporary JSON files.

        Args:
            root: Output directory.
            index: Index document.
            findings: Findings document.

        Returns:
            The completed verifier process.
        """
        index_path = root / "index.json"
        findings_path = root / "findings.json"
        index_path.write_text(json.dumps(index), encoding="utf-8")
        findings_path.write_text(json.dumps(findings), encoding="utf-8")
        return support.run_script(
            "verify_evidence.py",
            ["--index", str(index_path), "--findings", str(findings_path)],
            cwd=root,
        )


if __name__ == "__main__":
    unittest.main()
