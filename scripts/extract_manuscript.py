"""Extract paragraph text from DOCX, TXT, and Markdown manuscripts.

The manuscript is opened read-only. Its contents are stored as data and are
never evaluated or passed to a shell.
"""

from __future__ import annotations

import argparse
import io
import re
import sys
import zipfile
import xml.etree.ElementTree as ET
from pathlib import Path
from typing import Any

from common import (
    ManuscriptError,
    UsageError,
    assert_distinct_output,
    decode_text_bytes,
    dump_json,
    manuscript_format,
    read_bytes,
    sha256_bytes,
    word_count,
    write_text,
)


W = "{http://schemas.openxmlformats.org/wordprocessingml/2006/main}"
MAX_XML_BYTES = 40_000_000
ATX_HEADING = re.compile(r"^(#{1,6})\s+(.+?)\s*#*$")
SETEXT_HEADING = re.compile(r"^(.+)\n(=+|-+)\s*$")
THEMATIC_BREAK = re.compile(r"^(?:-{3,}|\*{3,}|_{3,})$")


def extract_manuscript(path: Path) -> dict[str, Any]:
    """Extract paragraphs from one manuscript file.

    Args:
        path: DOCX, TXT, or Markdown file. The file is not modified.

    Returns:
        An extract document with source metadata, warnings, and paragraphs.

    Raises:
        ManuscriptError: The file cannot be read or parsed.
        UsageError: The format is unsupported.
    """
    source_path = path.resolve()
    payload = read_bytes(source_path)
    kind = manuscript_format(source_path)
    if kind == "docx":
        paragraphs, encoding, warnings = extract_docx(payload)
    else:
        text, encoding, warnings = decode_text_bytes(payload)
        paragraphs = extract_plain_text(text)
    return {
        "format_version": 1,
        "document_type": "extract",
        "source": _source(source_path, kind, payload, encoding),
        "warnings": warnings,
        "paragraphs": _number_paragraphs(paragraphs),
    }


def extract_plain_text(text: str) -> list[dict[str, Any]]:
    """Split plain text or Markdown into paragraphs.

    Args:
        text: Decoded manuscript text. It is not interpreted as code.

    Returns:
        Paragraph records without ordinals. Empty blocks are omitted.
    """
    normalized = text.replace("\r\n", "\n").replace("\r", "\n")
    paragraphs: list[dict[str, Any]] = []
    for block in re.split(r"\n\s*\n", normalized):
        record = _plain_block(block.strip())
        if record is not None:
            paragraphs.append(record)
    return paragraphs


def extract_docx(payload: bytes) -> tuple[list[dict[str, Any]], str, list[str]]:
    """Extract paragraphs from a DOCX package.

    Args:
        payload: Raw DOCX bytes.

    Returns:
        Paragraph records, the XML encoding label, and warnings.

    Raises:
        ManuscriptError: The package is not a readable DOCX or its XML is
            unsafe to parse.
    """
    try:
        archive = zipfile.ZipFile(io.BytesIO(payload))
    except zipfile.BadZipFile as exc:
        raise ManuscriptError("File is not a readable DOCX package.") from exc
    with archive:
        document_xml = _docx_document_xml(archive)
    root = _parse_xml(document_xml)
    body = root.find(f"{W}body")
    if body is None:
        raise ManuscriptError("DOCX is missing a document body.")
    retained = []
    for element in _iter_body_paragraphs(body):
        record = _docx_paragraph(element)
        if record is not None:
            retained.append(record)
    return retained, "utf-8", []


def main(argv: list[str] | None = None) -> int:
    """Run the extract command.

    Args:
        argv: Arguments excluding the program name. Defaults to ``sys.argv``.

    Returns:
        Process exit code. ``0`` on success, ``2`` on expected failure.
    """
    try:
        return _run(argv)
    except ManuscriptError as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 2


def _run(argv: list[str] | None) -> int:
    """Parse arguments and write the extract document.

    Args:
        argv: Arguments excluding the program name.

    Returns:
        ``0`` after the artifact is written or printed.
    """
    parser = _parser()
    args = parser.parse_args(argv)
    source = Path(args.manuscript)
    document = extract_manuscript(source)
    rendered = dump_json(document)
    if args.output:
        output = Path(args.output)
        assert_distinct_output(source, output, "extract")
        write_text(output, rendered)
    else:
        sys.stdout.write(rendered)
    return 0


def _parser() -> argparse.ArgumentParser:
    """Build the command-line parser.

    Returns:
        Parser for the extract command.
    """
    parser = argparse.ArgumentParser(
        description="Extract manuscript paragraphs without modifying the source."
    )
    parser.add_argument("manuscript", help="Path to a .docx, .txt, .md, or .markdown file")
    parser.add_argument("--output", help="Write extract JSON here instead of stdout")
    return parser


def _source(path: Path, kind: str, payload: bytes, encoding: str) -> dict[str, Any]:
    """Build source metadata for an extract document.

    Args:
        path: Resolved manuscript path.
        kind: ``docx``, ``txt``, or ``markdown``.
        payload: Bytes that were hashed.
        encoding: Encoding used to decode text, or ``utf-8`` for DOCX XML.

    Returns:
        Source object stored in the extract document.
    """
    return {
        "path": str(path),
        "name": path.name,
        "format": kind,
        "sha256": sha256_bytes(payload),
        "byte_length": len(payload),
        "encoding": encoding,
    }


def _number_paragraphs(paragraphs: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """Assign one-based ordinals after empty paragraphs are removed.

    Args:
        paragraphs: Unnumbered paragraph records.

    Returns:
        The same records with an ``ordinal`` field.
    """
    numbered: list[dict[str, Any]] = []
    for ordinal, paragraph in enumerate(paragraphs, start=1):
        record = dict(paragraph)
        record["ordinal"] = ordinal
        numbered.append(record)
    return numbered


def _plain_block(block: str) -> dict[str, Any] | None:
    """Convert one blank-line-delimited block into a paragraph.

    Args:
        block: Stripped block. It may be a heading, a break, or prose.

    Returns:
        A paragraph record, or None when the block should be omitted.
    """
    if not block or THEMATIC_BREAK.fullmatch(block):
        return None
    if "\n" not in block:
        heading = ATX_HEADING.fullmatch(block)
        if heading:
            return _heading(heading.group(2).strip(), len(heading.group(1)), block)
    setext = SETEXT_HEADING.fullmatch(block)
    if setext and len(setext.group(2)) >= 3:
        level = 1 if setext.group(2).startswith("=") else 2
        return _heading(setext.group(1).strip(), level, block)
    return _prose(block, block)


def _heading(text: str, level: int, raw: str) -> dict[str, Any] | None:
    """Build a Markdown heading paragraph.

    Args:
        text: Heading text without marker characters.
        level: Heading level from 1 to 6.
        raw: Original block, including markers.

    Returns:
        A heading record, or None when the visible text is empty.
    """
    if not text:
        return None
    record = _prose(text, raw)
    record["kind"] = "heading"
    record["heading_level"] = level
    record["heading_source"] = "markdown"
    return record


def _prose(text: str, raw: str) -> dict[str, Any]:
    """Build a prose paragraph record.

    Args:
        text: Reader-facing text.
        raw: Original block.

    Returns:
        A prose record. Word counts are navigation counts.
    """
    return {
        "text": text,
        "raw": raw,
        "kind": "prose",
        "heading_level": None,
        "heading_source": None,
        "word_count": word_count(text),
    }


def _docx_document_xml(archive: zipfile.ZipFile) -> bytes:
    """Read ``word/document.xml`` with a size guard.

    Args:
        archive: Open DOCX zip.

    Returns:
        The document XML bytes.

    Raises:
        ManuscriptError: The part is missing or too large.
    """
    try:
        info = archive.getinfo("word/document.xml")
    except KeyError as exc:
        raise ManuscriptError("DOCX is missing word/document.xml.") from exc
    if info.file_size > MAX_XML_BYTES:
        raise ManuscriptError("DOCX document.xml is larger than 40 MB; refusing to expand it.")
    return archive.read(info)


def _parse_xml(payload: bytes) -> ET.Element:
    """Parse DOCX XML after rejecting entity declarations.

    Args:
        payload: XML bytes from the package.

    Returns:
        The document root.

    Raises:
        ManuscriptError: The XML declares entities or cannot be parsed.
    """
    folded = payload.upper()
    if b"<!DOCTYPE" in folded or b"<!ENTITY" in folded:
        raise ManuscriptError("Refusing to parse DOCX XML that declares a DOCTYPE or entity.")
    try:
        return ET.fromstring(payload)
    except ET.ParseError as exc:
        raise ManuscriptError(f"DOCX XML could not be parsed: {exc}") from exc


def _docx_paragraph(element: ET.Element) -> dict[str, Any] | None:
    """Convert one DOCX paragraph element into a record.

    Args:
        element: A ``w:p`` element.

    Returns:
        A paragraph record, or None when no visible text remains.
    """
    text = _docx_visible_text(element).strip()
    if not text:
        return None
    style = _docx_style(element)
    level = _heading_level(style)
    record = _prose(text, text)
    if level is not None:
        record["kind"] = "heading"
        record["heading_level"] = level
        record["heading_source"] = "docx"
    return record


def _iter_body_paragraphs(body: ET.Element) -> list[ET.Element]:
    """List body paragraphs that are not inside a deletion.

    Args:
        body: The ``w:body`` element.

    Returns:
        Paragraph elements in document order, including paragraphs in tables.
    """
    found: list[ET.Element] = []
    _walk_paragraphs(body, found, deleted=False)
    return found


def _walk_paragraphs(element: ET.Element, found: list[ET.Element], deleted: bool) -> None:
    """Collect paragraphs while tracking Word deletion regions.

    Args:
        element: Current XML element.
        found: Collector for paragraph elements.
        deleted: True when an ancestor is ``w:del``.
    """
    if element.tag == f"{W}del":
        deleted = True
    if element.tag == f"{W}p":
        if not deleted:
            found.append(element)
        return
    for child in list(element):
        _walk_paragraphs(child, found, deleted)


def _docx_visible_text(element: ET.Element) -> str:
    """Collect visible runs, skipping deleted text.

    Args:
        element: Paragraph element.

    Returns:
        Text with tabs and line breaks preserved.
    """
    parts: list[str] = []
    _collect_visible(element, parts, deleted=False)
    return "".join(parts)


def _collect_visible(element: ET.Element, parts: list[str], deleted: bool) -> None:
    """Append visible text from a paragraph subtree.

    Args:
        element: Current XML element.
        parts: Collector for text fragments.
        deleted: True when an ancestor is ``w:del``.
    """
    if element.tag == f"{W}del":
        deleted = True
    if not deleted:
        if element.tag == f"{W}t" and element.text:
            parts.append(element.text)
        elif element.tag == f"{W}tab":
            parts.append("\t")
        elif element.tag in {f"{W}br", f"{W}cr"}:
            parts.append("\n")
    for child in list(element):
        _collect_visible(child, parts, deleted)


def _docx_style(element: ET.Element) -> str | None:
    """Read the paragraph style identifier.

    Args:
        element: Paragraph element.

    Returns:
        The style value, or None when the paragraph has no style.
    """
    style = element.find(f"{W}pPr/{W}pStyle")
    if style is None:
        return None
    return style.get(f"{W}val") or style.get("val")


def _heading_level(style: str | None) -> int | None:
    """Map a Word paragraph style to a heading level.

    Args:
        style: Raw style identifier such as ``Heading1`` or ``Titolo 1``.

    Returns:
        A level from 1 to 6, or None for body styles.
    """
    if not style:
        return None
    compact = re.sub(r"[\s_-]+", "", style).casefold()
    match = re.fullmatch(r"(?:heading|titolo)([1-6])", compact)
    if not match:
        return None
    return int(match.group(1))


if __name__ == "__main__":
    sys.exit(main())
