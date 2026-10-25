"""Build a navigable manuscript index from an extract or a source file.

Chapter boundaries are detected only from explicit titles or repeated DOCX
Heading 1 styles. Ambiguous heading lines stay candidates.
"""

from __future__ import annotations

import argparse
import re
import sys
from pathlib import Path
from typing import Any

from common import (
    ManuscriptError,
    UsageError,
    assert_distinct_output,
    dump_json,
    paragraph_id,
    preview,
    read_json,
    sha256_file,
    word_count,
    write_text,
)
from extract_manuscript import extract_manuscript


EXPLICIT_CHAPTER = re.compile(
    r"^(?:chapter|capitolo|cap[ií]tulo|chapitre|kapitel)\s+"
    r"(?:[0-9]+|[ivxlcdm]+)"
    r"(?:\s*[:.\-—–]\s*[^.]{0,80})?$",
    re.IGNORECASE,
)
MAX_TITLE_LENGTH = 120


def index_manuscript(source: Path) -> dict[str, Any]:
    """Index a manuscript path or an extract JSON file.

    Args:
        source: Manuscript file or extract document produced by
            ``extract_manuscript.py``.

    Returns:
        An index document with stable paragraph identifiers.

    Raises:
        ManuscriptError: The input cannot be read, or the manuscript changed
            after extraction.
        UsageError: The file format is unsupported.
    """
    extract, read_now = _load_extract(source)
    if read_now:
        return build_index(extract, True)
    available = _recheck_extract_source(extract["source"])
    return build_index(extract, available)


def build_index(extract: dict[str, Any], source_available: bool) -> dict[str, Any]:
    """Segment an extract document into a navigable index.

    Args:
        extract: Document produced by ``extract_manuscript``.
        source_available: Whether the original file was re-hashed successfully.

    Returns:
        Index document. Paragraph identifiers do not depend on chapter labels.

    Raises:
        ManuscriptError: The extract document is missing required fields.
    """
    paragraphs = _require_paragraphs(extract)
    method, ambiguous, boundaries = _select_boundaries(paragraphs)
    boundary_ordinals = {item["ordinal"] for item in boundaries}
    candidates = _candidates(paragraphs, boundary_ordinals)
    indexed = [_index_paragraph(item, boundary_ordinals) for item in paragraphs]
    chapters = _chapters(indexed, [item["ordinal"] for item in boundaries])
    _assign_chapters(indexed, chapters)
    notes = _notes(ambiguous, candidates, indexed)
    return {
        "format_version": 1,
        "document_type": "index",
        "source": _index_source(extract["source"], source_available),
        "segmentation": {
            "ambiguous": ambiguous,
            "method": method,
            "notes": notes,
            "candidates": candidates,
        },
        "counts": _counts(indexed, chapters),
        "chapters": chapters,
        "paragraphs": indexed,
    }


def render_outline(index: dict[str, Any]) -> str:
    """Render a Markdown outline that points back at paragraph identifiers.

    Args:
        index: Index document from ``build_index``.

    Returns:
        Markdown outline. It is a navigation aid, not a new manuscript.
    """
    source = index["source"]
    segmentation = index["segmentation"]
    counts = index["counts"]
    lines = [
        "# Manuscript index",
        "",
        f"- Source: `{source['name']}`",
        f"- SHA-256: `{source['sha256']}`",
        f"- Words: {counts['words']}",
        f"- Paragraphs: {counts['paragraphs']}",
        f"- Chapters: {counts['chapters']}",
        f"- Segmentation: `{segmentation['method']}`",
        f"- Ambiguous: `{str(segmentation['ambiguous']).lower()}`",
        "",
    ]
    for note in segmentation["notes"]:
        lines.append(f"- Note: {note}")
    if segmentation["notes"]:
        lines.append("")
    if index["chapters"]:
        lines.extend(_chapter_outline(index))
    else:
        lines.extend(_sequence_outline(index["paragraphs"]))
    return "\n".join(lines).rstrip() + "\n"


def main(argv: list[str] | None = None) -> int:
    """Run the index command.

    Args:
        argv: Arguments excluding the program name.

    Returns:
        ``0`` on success, ``2`` on expected failure.
    """
    try:
        return _run(argv)
    except ManuscriptError as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 2


def is_explicit_chapter_title(text: str) -> bool:
    """Return whether a paragraph is an explicit chapter title.

    Args:
        text: Reader-facing paragraph text.

    Returns:
        True when the whole paragraph matches a chapter heading and is short
        enough not to be a sentence that merely mentions a chapter.
    """
    stripped = text.strip()
    if not stripped or len(stripped) > MAX_TITLE_LENGTH:
        return False
    return EXPLICIT_CHAPTER.fullmatch(stripped) is not None


def _run(argv: list[str] | None) -> int:
    """Parse arguments and write index artifacts.

    Args:
        argv: Arguments excluding the program name.

    Returns:
        ``0`` after writing or printing the index.
    """
    parser = _parser()
    args = parser.parse_args(argv)
    source = Path(args.source)
    document = index_manuscript(source)
    rendered = dump_json(document)
    if args.output:
        output = Path(args.output)
        assert_distinct_output(source, output, "index")
        write_text(output, rendered)
    else:
        sys.stdout.write(rendered)
    if args.outline:
        outline = Path(args.outline)
        assert_distinct_output(source, outline, "outline")
        write_text(outline, render_outline(document))
    return 0


def _parser() -> argparse.ArgumentParser:
    """Build the command-line parser.

    Returns:
        Parser for the index command.
    """
    parser = argparse.ArgumentParser(
        description="Index manuscript paragraphs and detect chapter boundaries."
    )
    parser.add_argument("source", help="Manuscript file or extract JSON")
    parser.add_argument("--output", help="Write index JSON here instead of stdout")
    parser.add_argument("--outline", help="Write a Markdown outline to this path")
    return parser


def _load_extract(source: Path) -> tuple[dict[str, Any], bool]:
    """Load an extract document or create one from a manuscript.

    Args:
        source: Manuscript or extract JSON path.

    Returns:
        The extract document and whether the original manuscript file was read
        during this call.

    Raises:
        ManuscriptError: The JSON is not an extract document.
    """
    if source.suffix.lower() == ".json":
        payload = read_json(source)
        if not _is_extract(payload):
            raise ManuscriptError(f"{source} is not a manuscript extract document.")
        return payload, False
    return extract_manuscript(source), True


def _is_extract(payload: Any) -> bool:
    """Return whether a JSON value is an extract document.

    Args:
        payload: Parsed JSON value.

    Returns:
        True when the value has the extract document type and a paragraph list.
    """
    return (
        isinstance(payload, dict)
        and payload.get("document_type") == "extract"
        and isinstance(payload.get("paragraphs"), list)
        and isinstance(payload.get("source"), dict)
    )


def _recheck_extract_source(source: dict[str, Any]) -> bool:
    """Re-hash a manuscript referenced by a saved extract.

    Args:
        source: Extract source object.

    Returns:
        True when the original file is present and its hash still matches.

    Raises:
        ManuscriptError: The file exists but its hash changed.
    """
    path = Path(str(source.get("path", "")))
    if not path.is_file():
        return False
    current = sha256_file(path)
    if current != source.get("sha256"):
        raise ManuscriptError(
            "Source file changed after extraction. Run extract_manuscript.py again. "
            "The manuscript was not modified by this tool."
        )
    return True


def _require_paragraphs(extract: dict[str, Any]) -> list[dict[str, Any]]:
    """Return extract paragraphs or raise when the document is unusable.

    Args:
        extract: Extract document.

    Returns:
        Paragraph dictionaries.

    Raises:
        ManuscriptError: Required fields are missing or have the wrong type.
    """
    source = extract.get("source")
    paragraphs = extract.get("paragraphs")
    if not isinstance(source, dict) or not isinstance(paragraphs, list):
        raise ManuscriptError("Extract document is missing source or paragraphs.")
    for paragraph in paragraphs:
        if not isinstance(paragraph, dict) or not isinstance(paragraph.get("text"), str):
            raise ManuscriptError("Extract paragraph is missing text.")
    return paragraphs


def _select_boundaries(paragraphs: list[dict[str, Any]]) -> tuple[str, bool, list[dict[str, Any]]]:
    """Choose chapter boundaries without inventing them.

    Args:
        paragraphs: Extract paragraphs in order.

    Returns:
        Method name, ambiguity flag, and the paragraphs used as boundaries.
    """
    explicit = [item for item in paragraphs if is_explicit_chapter_title(str(item["text"]))]
    if explicit:
        return "explicit-chapter-title", False, explicit
    docx_headings = [
        item
        for item in paragraphs
        if item.get("heading_source") == "docx" and item.get("heading_level") == 1
    ]
    if len(docx_headings) >= 2:
        return "docx-heading-1", False, docx_headings
    return "unsegmented", True, []


def _candidates(
    paragraphs: list[dict[str, Any]], boundary_ordinals: set[int]
) -> list[dict[str, Any]]:
    """List heading-like paragraphs that were not used as chapters.

    Args:
        paragraphs: Extract paragraphs.
        boundary_ordinals: Ordinals already used as chapter boundaries.

    Returns:
        Candidate objects in document order.
    """
    candidates: list[dict[str, Any]] = []
    for item in paragraphs:
        if item["ordinal"] in boundary_ordinals:
            continue
        reason = _heading_reason(item)
        if reason is None:
            continue
        candidates.append(
            {"ordinal": item["ordinal"], "text": item["text"], "reason": reason}
        )
    return candidates


def _heading_reason(paragraph: dict[str, Any]) -> str | None:
    """Classify a paragraph that looks like a heading.

    Args:
        paragraph: Extract paragraph.

    Returns:
        A candidate reason, or None when the paragraph is ordinary prose.
    """
    if is_explicit_chapter_title(str(paragraph["text"])):
        return "explicit-chapter-title"
    if paragraph.get("heading_source") == "docx" and paragraph.get("heading_level"):
        return "docx-heading"
    if paragraph.get("heading_source") == "markdown" and paragraph.get("heading_level"):
        return "markdown-heading"
    return None


def _index_paragraph(paragraph: dict[str, Any], boundary_ordinals: set[int]) -> dict[str, Any]:
    """Copy one extract paragraph into an index paragraph.

    Args:
        paragraph: Extract paragraph.
        boundary_ordinals: Ordinals used as chapter boundaries.

    Returns:
        Index paragraph. ``chapter_id`` is filled later.
    """
    text = str(paragraph["text"])
    ordinal = int(paragraph["ordinal"])
    kind = paragraph.get("kind") if paragraph.get("kind") in {"prose", "heading"} else "prose"
    return {
        "id": paragraph_id(ordinal, text),
        "ordinal": ordinal,
        "chapter_id": None,
        "kind": kind,
        "structural_role": _structural_role(paragraph, boundary_ordinals),
        "heading_level": paragraph.get("heading_level"),
        "heading_source": paragraph.get("heading_source"),
        "text": text,
        "raw": str(paragraph.get("raw", text)),
        "word_count": int(paragraph.get("word_count") or word_count(text)),
        "preview": preview(text),
    }


def _structural_role(paragraph: dict[str, Any], boundary_ordinals: set[int]) -> str:
    """Label a paragraph's structural role.

    Args:
        paragraph: Extract paragraph.
        boundary_ordinals: Ordinals used as chapter boundaries.

    Returns:
        ``chapter-heading``, ``subheading``, or ``body``.
    """
    if paragraph["ordinal"] in boundary_ordinals:
        return "chapter-heading"
    if paragraph.get("kind") == "heading":
        return "subheading"
    return "body"


def _chapters(paragraphs: list[dict[str, Any]], starts: list[int]) -> list[dict[str, Any]]:
    """Group indexed paragraphs into front matter and chapters.

    Args:
        paragraphs: Index paragraphs in order.
        starts: Boundary ordinals in document order.

    Returns:
        Chapter objects. The list is empty when no boundary was confirmed.
    """
    if not paragraphs or not starts:
        return []
    chapters: list[dict[str, Any]] = []
    front = [item for item in paragraphs if item["ordinal"] < starts[0]]
    if front:
        chapters.append(_chapter("c000", 0, "Front matter", "front-matter", front))
    last_ordinal = paragraphs[-1]["ordinal"]
    for position, start in enumerate(starts):
        next_start = starts[position + 1] if position + 1 < len(starts) else None
        end = last_ordinal if next_start is None else next_start - 1
        members = [item for item in paragraphs if start <= item["ordinal"] <= end]
        number = position + 1
        title = members[0]["text"] if members else f"Chapter {number}"
        chapters.append(_chapter(f"c{number:03d}", number, title, "chapter", members))
    return chapters


def _chapter(
    identifier: str,
    ordinal: int,
    title: str,
    role: str,
    members: list[dict[str, Any]],
) -> dict[str, Any]:
    """Build one chapter object.

    Args:
        identifier: Stable chapter id such as ``c001``.
        ordinal: Zero for front matter, otherwise one-based chapter order.
        title: Heading text or ``Front matter``.
        role: ``chapter`` or ``front-matter``.
        members: Paragraphs that belong to this span.

    Returns:
        Chapter object without mutating the paragraphs.
    """
    return {
        "id": identifier,
        "ordinal": ordinal,
        "title": title,
        "role": role,
        "paragraph_ids": [item["id"] for item in members],
        "word_count": sum(item["word_count"] for item in members),
    }


def _assign_chapters(paragraphs: list[dict[str, Any]], chapters: list[dict[str, Any]]) -> None:
    """Set ``chapter_id`` on paragraphs from chapter membership.

    Args:
        paragraphs: Index paragraphs mutated in place.
        chapters: Chapter objects whose paragraph ids cover the ranges.
    """
    lookup = {
        paragraph_id_: chapter["id"]
        for chapter in chapters
        for paragraph_id_ in chapter["paragraph_ids"]
    }
    for paragraph in paragraphs:
        paragraph["chapter_id"] = lookup.get(paragraph["id"])


def _notes(
    ambiguous: bool, candidates: list[dict[str, Any]], paragraphs: list[dict[str, Any]]
) -> list[str]:
    """Explain the segmentation decision.

    Args:
        ambiguous: Whether confirmed chapter boundaries were not found.
        candidates: Unused heading-like paragraphs.
        paragraphs: Indexed paragraphs.

    Returns:
        Notes safe to show to the agent and the user.
    """
    notes: list[str] = []
    if not paragraphs:
        notes.append("No paragraphs found.")
    if ambiguous and candidates:
        notes.append(
            "No reliable chapter boundaries were found. Heading-like lines are "
            "listed as candidates and were not turned into chapters."
        )
    elif ambiguous:
        notes.append(
            "No chapter boundaries were found. The manuscript is indexed as one "
            "undifferentiated sequence."
        )
    elif candidates:
        notes.append("Some heading-like paragraphs were not used as chapter boundaries.")
    return notes


def _counts(paragraphs: list[dict[str, Any]], chapters: list[dict[str, Any]]) -> dict[str, int]:
    """Summarize the index.

    Args:
        paragraphs: Indexed paragraphs.
        chapters: Chapter objects, including optional front matter.

    Returns:
        Word, paragraph, and confirmed-chapter counts.
    """
    return {
        "words": sum(item["word_count"] for item in paragraphs),
        "paragraphs": len(paragraphs),
        "chapters": sum(1 for chapter in chapters if chapter["role"] == "chapter"),
    }


def _index_source(source: dict[str, Any], available: bool) -> dict[str, Any]:
    """Copy extract source metadata into the index.

    Args:
        source: Extract source object.
        available: Whether the original file was read during this indexing call.

    Returns:
        Source object for the index.

    Raises:
        ManuscriptError: The source object is incomplete.
    """
    required = ("path", "name", "format", "sha256", "byte_length", "encoding")
    if any(key not in source for key in required):
        raise ManuscriptError("Extract source metadata is incomplete.")
    if not isinstance(source["sha256"], str):
        raise ManuscriptError("Extract source hash is invalid.")
    return {
        "path": source["path"],
        "name": source["name"],
        "format": source["format"],
        "sha256": source["sha256"],
        "byte_length": source["byte_length"],
        "encoding": source["encoding"],
        "available": available,
    }


def _chapter_outline(index: dict[str, Any]) -> list[str]:
    """Render one outline section per chapter.

    Args:
        index: Index document.

    Returns:
        Markdown lines.
    """
    by_id = {item["id"]: item for item in index["paragraphs"]}
    lines: list[str] = []
    for chapter in index["chapters"]:
        lines.append(f"## {chapter['title']} (`{chapter['id']}`)")
        lines.append("")
        lines.append(f"Words: {chapter['word_count']}")
        lines.append("")
        lines.extend(_paragraph_table(chapter["paragraph_ids"], by_id))
        lines.append("")
    return lines


def _sequence_outline(paragraphs: list[dict[str, Any]]) -> list[str]:
    """Render an outline for an unsegmented manuscript.

    Args:
        paragraphs: Indexed paragraphs.

    Returns:
        Markdown lines.
    """
    lines = ["## Unsegmented", ""]
    identifiers = [item["id"] for item in paragraphs]
    by_id = {item["id"]: item for item in paragraphs}
    lines.extend(_paragraph_table(identifiers, by_id))
    lines.append("")
    return lines


def _paragraph_table(identifiers: list[str], by_id: dict[str, dict[str, Any]]) -> list[str]:
    """Render a paragraph table.

    Args:
        identifiers: Paragraph ids in display order.
        by_id: Paragraph lookup.

    Returns:
        Markdown table lines.
    """
    lines = ["| ID | Words | Preview |", "| --- | ---: | --- |"]
    for identifier in identifiers:
        item = by_id[identifier]
        lines.append(f"| `{item['id']}` | {item['word_count']} | {item['preview']} |")
    return lines


if __name__ == "__main__":
    sys.exit(main())
