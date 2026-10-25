"""Regression checks for the failures in the first benchmark.

These tests read the original review artifacts and do not rewrite them.
"""

from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path

import support
from check_report import check_report
from index_manuscript import index_manuscript
from score_findings import score_findings


ORIGINAL = support.ROOT / "examples" / "benchmark" / "manuscript-lab-output" / "the-lantern-house"
MANUSCRIPT = support.ROOT / "examples" / "long-distance" / "the-mile-road.md"
KEY = support.ROOT / "evaluations" / "keys" / "the-mile-road-known-issues.md"


class FirstBenchmarkRegressionTests(unittest.TestCase):
    """The first review's structural failures stay visible to the new checks."""

    def test_rejected_factual_finding_is_not_a_positive_prediction(self) -> None:
        """Confirmed factual findings are the only positive predictions."""
        before = (ORIGINAL / "findings.json").read_bytes()
        findings = json.loads(before)
        score = score_findings(findings)
        self.assertEqual((ORIGINAL / "findings.json").read_bytes(), before)
        self.assertEqual(score["positive_prediction_ids"], ["F-001", "F-002"])
        self.assertEqual(score["excluded"]["rejected"], ["F-005"])
        self.assertEqual(score["excluded"]["interpretive"], ["F-003"])
        self.assertEqual(score["excluded"]["strength"], ["F-004"])
        self.assertEqual(score["semantic_correctness"], "not_assessed")

    def test_original_report_still_has_an_unverified_direct_quotation(self) -> None:
        """A paraphrase in quotation marks fails, and a real block quote is checked."""
        report = (ORIGINAL / "editorial-report.md").read_text(encoding="utf-8")
        index = json.loads((ORIGINAL / "index.json").read_text(encoding="utf-8"))
        findings = json.loads((ORIGINAL / "findings.json").read_text(encoding="utf-8"))
        checked = check_report(report, index, findings)
        monday = next(item for item in checked["quotations"] if item["quote"].startswith("That Monday"))
        self.assertEqual(monday["quote_check"], "verified_exact")
        self.assertEqual(monday["paragraph_id"], "p0014-276e81c7")
        failed = [item["quote"] for item in checked["quotations"] if item["quote_check"].startswith("not_found")]
        self.assertIn("prima di mattina", failed)
        clipped = [item for item in checked["quotations"] if "I never drowned" in item["quote"]]
        self.assertEqual(clipped[0]["alignment"], "inside_quotation")
        self.assertEqual(checked["semantic_correctness"], "not_assessed")
        self.assertTrue(all("giorno dopo" not in error for error in checked["errors"]))

    def test_report_check_does_not_overwrite_the_original_review(self) -> None:
        """The checker writes only to the path it is given."""
        with tempfile.TemporaryDirectory() as directory:
            destination = Path(directory) / "report-check.json"
            completed = support.run_script(
                "check_report.py",
                [
                    "--report",
                    str(ORIGINAL / "editorial-report.md"),
                    "--index",
                    str(ORIGINAL / "index.json"),
                    "--findings",
                    str(ORIGINAL / "findings.json"),
                    "--output",
                    str(destination),
                ],
            )
            self.assertEqual(completed.returncode, 1, completed.stderr)
            self.assertTrue(destination.is_file())
            names = {path.name for path in ORIGINAL.iterdir()}
            self.assertNotIn("report-check.json", names)
            self.assertNotIn("score.json", names)


class RecordSeparationTests(unittest.TestCase):
    """Nature, quote checks, and editorial status stay distinct."""

    def test_version_two_rejects_disagreeing_legacy_fields(self) -> None:
        """A factual nature cannot hide behind an interpretive legacy label."""
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            source = root / "story.txt"
            source.write_text("She arrived before the storm.\n", encoding="utf-8")
            index = index_manuscript(source)
            index_path = root / "index.json"
            index_path.write_text(json.dumps(index), encoding="utf-8")
            findings = {
                "format_version": 2,
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
                        "description": "Sample description for the record.",
                        "chapters": [],
                        "paragraph_ids": [index["paragraphs"][0]["id"]],
                        "evidence": [
                            {
                                "paragraph_id": index["paragraphs"][0]["id"],
                                "quote": "She arrived before the storm.",
                                "quote_check": "unchecked",
                            }
                        ],
                        "explanation": "The sample explanation is long enough.",
                        "narrative_impact": "The sample impact is local.",
                        "priority": "low",
                        "nature": "factual",
                        "editorial_status": "unreviewed",
                        "judgment_type": "interpretive",
                        "suggested_intervention": "Leave the wording to the author.",
                        "counterarguments": [],
                        "uncertainty": "",
                    }
                ],
            }
            findings_path = root / "findings.json"
            findings_path.write_text(json.dumps(findings), encoding="utf-8")
            completed = support.run_script(
                "verify_evidence.py",
                ["--index", str(index_path), "--findings", str(findings_path)],
            )
            self.assertEqual(completed.returncode, 1)
            self.assertIn("disagree", completed.stdout)


class LongDistanceFixtureTests(unittest.TestCase):
    """The second benchmark keeps its key away from the manuscript folder."""

    def test_answer_key_is_not_beside_the_manuscript(self) -> None:
        """A review of the folder does not have the key as a sibling file."""
        folder = MANUSCRIPT.parent
        self.assertTrue(MANUSCRIPT.is_file())
        self.assertTrue(KEY.is_file())
        self.assertFalse(any(path.name.endswith("known-issues.md") for path in folder.iterdir()))
        self.assertIn("contaminated", (folder / "README.md").read_text(encoding="utf-8"))

    def test_planted_quotes_sit_in_the_named_chapters(self) -> None:
        """Each key quotation occurs once, in one of the chapters the key names."""
        indexed = index_manuscript(MANUSCRIPT)
        self.assertFalse(indexed["segmentation"]["ambiguous"])
        self.assertEqual(indexed["counts"]["chapters"], 18)
        for section in _key_sections(KEY.read_text(encoding="utf-8")):
            for quote in section["quotes"]:
                hits = [item for item in indexed["paragraphs"] if quote in item["text"]]
                self.assertEqual(len(hits), 1, quote)
                ordinal = _chapter_ordinal(indexed, hits[0]["chapter_id"])
                self.assertIn(ordinal, section["chapters"], quote)


def _key_sections(text: str) -> list[dict[str, object]]:
    """Parse the long-distance answer key.

    Args:
        text: Key Markdown.

    Returns:
        Sections that declare a kind, chapter numbers, and quotations.
    """
    sections: list[dict[str, object]] = []
    current: dict[str, object] | None = None
    for line in text.splitlines():
        if line.startswith("### "):
            current = {"quotes": [], "chapters": []}
            sections.append(current)
            continue
        if current is None:
            continue
        if line.startswith("- chapters:"):
            current["chapters"] = [int(part.strip()) for part in line.split(":", 1)[1].split(",")]
        elif line.startswith("- quote:"):
            quotes = current["quotes"]
            if isinstance(quotes, list):
                quotes.append(line.split(":", 1)[1].strip())
    return [section for section in sections if section["quotes"] and section["chapters"]]


def _chapter_ordinal(index: dict, chapter_id: str) -> int:
    """Return the one-based chapter number for an id.

    Args:
        index: Manuscript index.
        chapter_id: Chapter id such as ``c017``.

    Returns:
        The chapter's ordinal. Front matter is zero.
    """
    for chapter in index["chapters"]:
        if chapter["id"] == chapter_id:
            return int(chapter["ordinal"])
    raise AssertionError(chapter_id)


if __name__ == "__main__":
    unittest.main()
