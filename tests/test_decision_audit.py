"""Tests for the optional decision-and-motivation audit."""

from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path

import support
from index_manuscript import index_manuscript
from schema_check import validate_instance
from verify_decision_audit import verify_decision_audit


MANUSCRIPT = support.ROOT / "examples" / "decisions" / "the-glass-orchard.md"
KEY = support.ROOT / "evaluations" / "keys" / "the-glass-orchard-known-issues.md"


class DecisionAuditTests(unittest.TestCase):
    """The audit keeps credible choices out of the finding pile."""

    def test_template_matches_the_schema(self) -> None:
        """The empty template is a valid audit shape."""
        schema = json.loads(
            (support.ROOT / "templates" / "decision-audit.schema.json").read_text(encoding="utf-8")
        )
        template = json.loads(
            (support.ROOT / "templates" / "decision-audit.json").read_text(encoding="utf-8")
        )
        self.assertEqual(validate_instance(template, schema), [])

    def test_a_credible_choice_cannot_warrant_a_finding(self) -> None:
        """An irrational but supported choice is not marked as a required finding."""
        with tempfile.TemporaryDirectory() as directory:
            index, paragraph = _one_paragraph(Path(directory))
            decision = _decision(paragraph, "credible", "supported", True)
            checked = verify_decision_audit(index, _audit(index, [decision]))
            self.assertFalse(checked["passed"])
            self.assertTrue(any("must not warrant" in error for error in checked["record_errors"]))
            self.assertEqual(checked["semantic_correctness"], "not_assessed")

    def test_ignored_alternative_must_have_been_perceivable(self) -> None:
        """An alternative known only from later information cannot be called ignored."""
        with tempfile.TemporaryDirectory() as directory:
            index, paragraph = _one_paragraph(Path(directory))
            decision = _decision(paragraph, "under_motivated", "absent", True)
            decision["alternatives"] = [
                {
                    "description": "A door that appears only in a later chapter.",
                    "known_to_character": False,
                    "reasonably_perceivable": False,
                    "disposition": "ignored",
                    "paragraph_ids": [paragraph["id"]],
                }
            ]
            checked = verify_decision_audit(index, _audit(index, [decision]))
            self.assertFalse(checked["passed"])
            self.assertTrue(any("could not perceive" in error for error in checked["record_errors"]))

    def test_conscious_refusal_requires_knowledge(self) -> None:
        """A person cannot consciously refuse an alternative they do not know."""
        with tempfile.TemporaryDirectory() as directory:
            index, paragraph = _one_paragraph(Path(directory))
            decision = _decision(paragraph, "credible", "supported", False)
            decision["alternatives"] = [
                {
                    "description": "The lit road.",
                    "known_to_character": False,
                    "reasonably_perceivable": True,
                    "disposition": "consciously_refused",
                    "paragraph_ids": [paragraph["id"]],
                }
            ]
            checked = verify_decision_audit(index, _audit(index, [decision]))
            self.assertFalse(checked["passed"])
            self.assertTrue(any("does not know" in error for error in checked["record_errors"]))

    def test_a_later_explanation_needs_a_later_paragraph(self) -> None:
        """A motive clarified later must point at a paragraph after the choice."""
        with tempfile.TemporaryDirectory() as directory:
            index, paragraph = _one_paragraph(Path(directory))
            decision = _decision(paragraph, "resolved_later", "clarified_later", False)
            checked = verify_decision_audit(index, _audit(index, [decision]))
            self.assertFalse(checked["passed"])
            self.assertTrue(any("no later paragraph" in error for error in checked["record_errors"]))

    def test_modes_do_not_require_the_audit_outside_developmental_work(self) -> None:
        """Continuity and dialogue reviews are not required to run this audit."""
        skill = (support.ROOT / "SKILL.md").read_text(encoding="utf-8")
        self.assertIn("continuity review and a dialogue-style review do not require it", skill)

    def test_fixture_quotes_land_in_the_named_chapters(self) -> None:
        """The decision fixture keeps its key outside the manuscript folder."""
        self.assertFalse(any(path.name.endswith("known-issues.md") for path in MANUSCRIPT.parent.iterdir()))
        indexed = index_manuscript(MANUSCRIPT)
        self.assertEqual(indexed["counts"]["chapters"], 7)
        self.assertFalse(indexed["segmentation"]["ambiguous"])
        for section in _key_sections(KEY.read_text(encoding="utf-8")):
            for quote in section["quotes"]:
                hits = [item for item in indexed["paragraphs"] if quote in item["text"]]
                self.assertEqual(len(hits), 1, quote)
                ordinal = _chapter_ordinal(indexed, hits[0]["chapter_id"])
                self.assertIn(ordinal, section["chapters"], quote)

    def test_problem_and_non_problem_can_both_be_checked(self) -> None:
        """A real weakness and a credible choice validate without scoring either."""
        indexed = index_manuscript(MANUSCRIPT)
        door = _paragraph(indexed, "She climbed the broken wall instead.")
        ticket = _paragraph(indexed, "She threw the ticket into the river.")
        later = _paragraph(indexed, "I burned it so you could not take it off me on the road.")
        burning = _paragraph(indexed, "That letter is the only account of the orchard")
        problem = _decision(door, "under_motivated", "absent", True)
        problem["id"] = "DA-001"
        problem["alternatives"] = [
            {
                "description": "The side door she has used every summer is open.",
                "known_to_character": True,
                "reasonably_perceivable": True,
                "disposition": "ignored",
                "paragraph_ids": [door["id"]],
            }
        ]
        credible = _decision(ticket, "credible", "supported", False)
        credible["id"] = "DA-002"
        resolved = _decision(burning, "resolved_later", "clarified_later", False)
        resolved["id"] = "DA-003"
        resolved["later_paragraph_ids"] = [later["id"]]
        before = MANUSCRIPT.read_bytes()
        checked = verify_decision_audit(indexed, _audit(indexed, [problem, credible, resolved]))
        self.assertTrue(checked["passed"], checked["record_errors"])
        self.assertEqual(checked["semantic_correctness"], "not_assessed")
        self.assertNotIn("score", checked)
        self.assertEqual(MANUSCRIPT.read_bytes(), before)


def _one_paragraph(root: Path) -> tuple[dict, dict]:
    """Index a one-paragraph manuscript.

    Args:
        root: Directory for the temporary file.

    Returns:
        The index and its only paragraph.
    """
    source = root / "story.txt"
    source.write_text("She arrived before the storm and kept the letter.\n", encoding="utf-8")
    index = index_manuscript(source)
    return index, index["paragraphs"][0]


def _audit(index: dict, decisions: list[dict]) -> dict:
    """Wrap decisions in an audit bound to an index hash.

    Args:
        index: Manuscript index.
        decisions: Decision records.

    Returns:
        An audit document.
    """
    return {
        "format_version": 1,
        "document_type": "decision-audit",
        "manuscript_sha256": index["source"]["sha256"],
        "decisions": decisions,
    }


def _decision(paragraph: dict, assessment: str, motive_support: str, warrants_finding: bool) -> dict:
    """Build one decision from a paragraph.

    Args:
        paragraph: Index paragraph used as evidence.
        assessment: Credibility label.
        motive_support: How far the text supports the motive.
        warrants_finding: Whether a finding is claimed.

    Returns:
        A schema-shaped decision. The quote starts unchecked.
    """
    return {
        "id": "DA-001",
        "character": "Lena",
        "decision": "She acts in the cited paragraph.",
        "objective": "Reach the far bank.",
        "information_available": "She can see the obstacle in front of her.",
        "withheld_from_character": "",
        "explicit_motives": "",
        "implicit_motives": "",
        "motive_support": motive_support,
        "obstacles": "A shut gate." if assessment == "obstacle_unexplained" else "",
        "obstacle_outcome": (
            "removed_without_explanation" if assessment == "obstacle_unexplained" else "not_applicable"
        ),
        "emotional_conflict": "",
        "consequences": "",
        "alternatives": [],
        "paragraph_ids": [paragraph["id"]],
        "later_paragraph_ids": [],
        "evidence": [
            {
                "paragraph_id": paragraph["id"],
                "quote": paragraph["text"] if len(paragraph["text"]) >= 8 else paragraph["text"] + " extra",
                "quote_check": "unchecked",
            }
        ],
        "assessment": assessment,
        "warrants_finding": warrants_finding,
    }


def _paragraph(index: dict, snippet: str) -> dict:
    """Return the only paragraph containing a snippet.

    Args:
        index: Manuscript index.
        snippet: Text that should occur once.

    Returns:
        The matching paragraph.
    """
    hits = [item for item in index["paragraphs"] if snippet in item["text"]]
    if len(hits) != 1:
        raise AssertionError(snippet)
    return hits[0]


def _key_sections(text: str) -> list[dict[str, object]]:
    """Parse the decision-fixture key.

    Args:
        text: Key Markdown.

    Returns:
        Sections with chapter numbers and quotations.
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
        chapter_id: Chapter id.

    Returns:
        The chapter ordinal.
    """
    for chapter in index["chapters"]:
        if chapter["id"] == chapter_id:
            return int(chapter["ordinal"])
    raise AssertionError(chapter_id)


if __name__ == "__main__":
    unittest.main()
