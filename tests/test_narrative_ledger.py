"""Tests for the narrative fact ledger.

The ledger is a retrieval aid. These tests check shape and quotations, not
whether a literary claim is true.
"""

from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path

import support
from index_manuscript import index_manuscript
from schema_check import validate_instance
from verify_ledger import verify_ledger


class NarrativeLedgerTests(unittest.TestCase):
    """A ledger stays tied to paragraphs and does not promote guesses to facts."""

    def test_template_matches_the_schema(self) -> None:
        """The empty template is a valid ledger shape."""
        schema = json.loads(
            (support.ROOT / "templates" / "narrative-ledger.schema.json").read_text(encoding="utf-8")
        )
        template = json.loads(
            (support.ROOT / "templates" / "narrative-ledger.json").read_text(encoding="utf-8")
        )
        self.assertEqual(validate_instance(template, schema), [])

    def test_verified_quote_and_later_revision(self) -> None:
        """A revised claim passes, and the manuscript stays unchanged."""
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            source = root / "story.md"
            source.write_text(
                "# Chapter 1. Arrival\n\n"
                "The rain reached the coast on Tuesday, 12 March.\n\n"
                "# Chapter 2. The Letter\n\n"
                "On Wednesday, 12 March, the rain had not stopped.\n",
                encoding="utf-8",
            )
            before = source.read_bytes()
            index = index_manuscript(source)
            tuesday = next(item for item in index["paragraphs"] if "Tuesday" in item["text"])
            wednesday = next(item for item in index["paragraphs"] if "Wednesday" in item["text"])
            ledger = _ledger(
                index,
                [
                    _entry(
                        "NF-001",
                        "The narration dates the rain to Tuesday, 12 March.",
                        "narrator",
                        "narrated_fact",
                        "revised",
                        tuesday,
                        ["NF-002"],
                        [],
                    ),
                    _entry(
                        "NF-002",
                        "A later chapter dates the same rain to Wednesday, 12 March.",
                        "narrator",
                        "narrated_fact",
                        "certain",
                        wednesday,
                        [],
                        [],
                    ),
                ],
            )
            checked = verify_ledger(index, ledger)
            self.assertTrue(checked["passed"], checked)
            self.assertFalse(checked["full_reading_established"])
            self.assertEqual(checked["semantic_correctness"], "not_assessed")
            self.assertEqual(checked["counts"]["verified_exact"], 2)
            self.assertEqual(source.read_bytes(), before)

    def test_hypothesis_cannot_be_recorded_as_certain(self) -> None:
        """An inference or a hypothesis is not a certain fact."""
        with tempfile.TemporaryDirectory() as directory:
            index, paragraph = _one_paragraph(Path(directory))
            ledger = _ledger(
                index,
                [
                    _entry(
                        "NF-001",
                        "She may have wanted the room.",
                        "inference",
                        "hypothesis",
                        "certain",
                        paragraph,
                        [],
                        [],
                    )
                ],
            )
            checked = verify_ledger(index, ledger)
            self.assertFalse(checked["passed"])
            self.assertTrue(checked["record_errors"])

    def test_false_quote_and_unknown_link_fail(self) -> None:
        """A missing quotation and a dangling revision id are both errors."""
        with tempfile.TemporaryDirectory() as directory:
            index, paragraph = _one_paragraph(Path(directory))
            entry = _entry(
                "NF-001",
                "A sentence that is not in the paragraph.",
                "narrator",
                "narrated_fact",
                "certain",
                paragraph,
                [],
                ["NF-009"],
            )
            entry["evidence"][0]["quote"] = "her violet eyes were bright"
            ledger = _ledger(index, [entry])
            checked = verify_ledger(index, ledger)
            self.assertFalse(checked["passed"])
            self.assertEqual(checked["quote_results"][0]["quote_check"], "not_found")
            self.assertTrue(any("NF-009" in error for error in checked["record_errors"]))

    def test_command_writes_a_separate_check(self) -> None:
        """The command does not replace the manuscript or the ledger input."""
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            index, paragraph = _one_paragraph(root)
            index_path = root / "index.json"
            ledger_path = root / "ledger.json"
            index_path.write_text(json.dumps(index), encoding="utf-8")
            ledger = _ledger(
                index,
                [
                    _entry(
                        "NF-001",
                        "She arrived before the storm.",
                        "narrator",
                        "narrated_fact",
                        "certain",
                        paragraph,
                        [],
                        [],
                    )
                ],
            )
            ledger_path.write_text(json.dumps(ledger), encoding="utf-8")
            before = ledger_path.read_bytes()
            completed = support.run_script(
                "verify_ledger.py",
                [
                    "--index",
                    str(index_path),
                    "--ledger",
                    str(ledger_path),
                    "--output",
                    str(root / "ledger-check.json"),
                    "--update-ledger",
                    str(root / "ledger.checked.json"),
                ],
            )
            self.assertEqual(completed.returncode, 0, completed.stderr)
            self.assertEqual(ledger_path.read_bytes(), before)
            updated = json.loads((root / "ledger.checked.json").read_text(encoding="utf-8"))
            self.assertEqual(updated["entries"][0]["evidence"][0]["quote_check"], "verified_exact")


def _one_paragraph(root: Path) -> tuple[dict, dict]:
    """Index a one-paragraph manuscript.

    Args:
        root: Directory for the temporary file.

    Returns:
        The index and its only body paragraph.
    """
    source = root / "story.txt"
    source.write_text("She arrived before the storm.\n", encoding="utf-8")
    index = index_manuscript(source)
    return index, index["paragraphs"][0]


def _ledger(index: dict, entries: list[dict]) -> dict:
    """Wrap entries in a ledger bound to an index hash.

    Args:
        index: Manuscript index.
        entries: Ledger entries.

    Returns:
        A ledger document.
    """
    return {
        "format_version": 1,
        "document_type": "narrative-ledger",
        "manuscript_sha256": index["source"]["sha256"],
        "reading": {
            "chapters_opened": [],
            "paragraphs_reread": [entries[0]["paragraph_ids"][0]] if entries else [],
            "not_fully_read": [],
            "note": "These ids were opened. That is not a full reading.",
        },
        "entries": entries,
    }


def _entry(
    identifier: str,
    statement: str,
    source: str,
    claim_kind: str,
    certainty: str,
    paragraph: dict,
    revised_by: list[str],
    incompatible_with: list[str],
) -> dict:
    """Build one ledger entry from a paragraph.

    Args:
        identifier: Entry id.
        statement: Reviewer wording of the claim.
        source: How the text presents the claim.
        claim_kind: Fact, statement, knowledge, hypothesis, or withholding.
        certainty: How settled the claim is.
        paragraph: Index paragraph.
        revised_by: Later entry ids.
        incompatible_with: Conflicting entry ids.

    Returns:
        A schema-shaped entry. The quote starts unchecked.
    """
    return {
        "id": identifier,
        "statement": statement,
        "subjects": ["Mara"],
        "event_time": "",
        "narration_time": "",
        "place": "",
        "source": source,
        "paragraph_ids": [paragraph["id"]],
        "evidence": [
            {
                "paragraph_id": paragraph["id"],
                "quote": paragraph["text"],
                "quote_check": "unchecked",
            }
        ],
        "certainty": certainty,
        "claim_kind": claim_kind,
        "incompatible_with": incompatible_with,
        "revised_by": revised_by,
    }


if __name__ == "__main__":
    unittest.main()
