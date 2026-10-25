"""Tests for chapter detection and stable paragraph ids."""

from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path

import support
from index_manuscript import index_manuscript, is_explicit_chapter_title


class IndexTests(unittest.TestCase):
    """Indexing detects only boundaries the text actually marks."""

    def test_explicit_title_rules(self) -> None:
        """Chapter titles match, and sentences that mention a chapter do not."""
        self.assertTrue(is_explicit_chapter_title("Chapter 1. The Attic Bargain"))
        self.assertTrue(is_explicit_chapter_title("Capitolo 2 — La lettera"))
        self.assertFalse(is_explicit_chapter_title("Chapter 1 was the one she skipped."))
        self.assertFalse(is_explicit_chapter_title("She skipped chapter 2 of the book."))

    def test_plain_text_chapters_and_front_matter(self) -> None:
        """An explicit title splits the book, and a false title stays prose."""
        text = (
            "Chapter 1 was the one she skipped.\n\n"
            "She arrived.\n\n"
            "Chapter 2\n\n"
            "She left.\n"
        )
        document = self._index("story.txt", text)
        self.assertFalse(document["segmentation"]["ambiguous"])
        self.assertEqual(document["segmentation"]["method"], "explicit-chapter-title")
        self.assertEqual(document["counts"]["chapters"], 1)
        self.assertEqual(document["chapters"][0]["id"], "c000")
        self.assertEqual(document["chapters"][0]["role"], "front-matter")
        self.assertEqual(document["chapters"][1]["title"], "Chapter 2")
        self.assertEqual(document["paragraphs"][0]["chapter_id"], "c000")
        self.assertEqual(document["paragraphs"][0]["structural_role"], "body")

    def test_capitolo_and_setext_headings(self) -> None:
        """Italian chapter labels and setext headings are explicit boundaries."""
        italian = self._index("story.md", "Capitolo 1. La soffitta\n\nElena arrivò.\n")
        self.assertEqual(italian["counts"]["chapters"], 1)
        self.assertFalse(italian["segmentation"]["ambiguous"])
        setext = self._index(
            "story.txt",
            "Chapter 1\n=========\n\nShe arrived.\n\nChapter 2\n=========\n\nShe left.\n",
        )
        self.assertEqual(setext["counts"]["chapters"], 2)
        self.assertEqual(setext["paragraphs"][0]["kind"], "heading")

    def test_markdown_headings_without_chapter_words_are_not_invented(self) -> None:
        """Heading lines that are not chapter titles stay candidates."""
        document = index_manuscript(support.ROOT / "examples" / "ambiguous-coast.md")
        self.assertTrue(document["segmentation"]["ambiguous"])
        self.assertEqual(document["chapters"], [])
        self.assertEqual(document["counts"]["chapters"], 0)
        self.assertEqual(
            [item["text"] for item in document["segmentation"]["candidates"]],
            ["Notes from the coast", "Later"],
        )
        self.assertIsNone(document["paragraphs"][0]["chapter_id"])

    def test_docx_heading_1_requires_two_non_explicit_titles(self) -> None:
        """One Heading 1 is a candidate. Two Heading 1 styles are chapters."""
        with tempfile.TemporaryDirectory() as directory:
            single = Path(directory) / "single.docx"
            support.write_docx(single, support.paragraph_xml("Prologue", "Heading1"))
            single_index = index_manuscript(single)
            self.assertTrue(single_index["segmentation"]["ambiguous"])
            self.assertEqual(single_index["chapters"], [])
            paired = Path(directory) / "paired.docx"
            support.write_docx(
                paired,
                support.paragraph_xml("The Coast", "Heading1")
                + support.paragraph_xml("She arrived.")
                + support.paragraph_xml("The City", "Titolo1"),
            )
            paired_index = index_manuscript(paired)
            self.assertFalse(paired_index["segmentation"]["ambiguous"])
            self.assertEqual(paired_index["segmentation"]["method"], "docx-heading-1")
            self.assertEqual(
                [chapter["title"] for chapter in paired_index["chapters"]],
                ["The Coast", "The City"],
            )

    def test_ids_are_stable_and_independent_of_cwd(self) -> None:
        """The same file indexes identically, including from another directory."""
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "story.md"
            path.write_text("# Chapter 1\n\nShe arrived.\n\n# Chapter 2\n\nShe left.\n", encoding="utf-8")
            output = Path(directory) / "index.json"
            other = Path(directory) / "elsewhere"
            other.mkdir()
            first = support.run_script(
                "index_manuscript.py",
                [str(path), "--output", str(output), "--outline", str(Path(directory) / "index.md")],
                cwd=other,
            )
            self.assertEqual(first.returncode, 0, first.stderr)
            second = index_manuscript(path)
            saved = json.loads(output.read_text(encoding="utf-8"))
            self.assertEqual(saved, second)
            self.assertIn(saved["paragraphs"][0]["id"], (Path(directory) / "index.md").read_text(encoding="utf-8"))
            changed = Path(directory) / "changed.md"
            changed.write_text("# Chapter 1\n\nShe departed.\n", encoding="utf-8")
            changed_index = index_manuscript(changed)
            self.assertNotEqual(saved["paragraphs"][1]["id"], changed_index["paragraphs"][1]["id"])

    def test_extract_hash_is_checked_again(self) -> None:
        """A saved extract is rejected when the manuscript bytes change."""
        with tempfile.TemporaryDirectory() as directory:
            source = Path(directory) / "story.txt"
            source.write_text("Chapter 1\n\nShe arrived.\n", encoding="utf-8")
            extract = Path(directory) / "extract.json"
            completed = support.run_script(
                "extract_manuscript.py",
                [str(source), "--output", str(extract)],
            )
            self.assertEqual(completed.returncode, 0, completed.stderr)
            source.write_text("Chapter 1\n\nShe left.\n", encoding="utf-8")
            stale = support.run_script("index_manuscript.py", [str(extract)])
            self.assertEqual(stale.returncode, 2)
            self.assertIn("changed", stale.stderr)
            source.unlink()
            payload = json.loads(extract.read_text(encoding="utf-8"))
            payload["source"]["sha256"] = "a" * 64
            extract.write_text(json.dumps(payload), encoding="utf-8")
            missing = index_manuscript(extract)
            self.assertFalse(missing["source"]["available"])

    def _index(self, name: str, text: str) -> dict:
        """Index a temporary manuscript.

        Args:
            name: File name, including the suffix.
            text: Manuscript text.

        Returns:
            The index document.
        """
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / name
            path.write_text(text, encoding="utf-8")
            return index_manuscript(path)


if __name__ == "__main__":
    unittest.main()
