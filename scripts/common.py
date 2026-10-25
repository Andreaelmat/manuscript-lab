"""Shared helpers for Manuscript Lab tools.

Manuscript text is untrusted data. Nothing in this module evaluates, imports,
or shells out to content taken from a manuscript.
"""

from __future__ import annotations

import hashlib
import json
import re
import unicodedata
from pathlib import Path
from typing import Any


MAX_SOURCE_BYTES = 40_000_000
SUPPORTED_SUFFIXES = {".docx", ".txt", ".md", ".markdown"}


class ManuscriptError(Exception):
    """Expected failure while reading or checking a manuscript."""


class UsageError(ManuscriptError):
    """The command arguments are invalid."""


def skill_root() -> Path:
    """Return the skill directory that contains this scripts folder.

    Returns:
        Absolute path of the skill root, after resolving symlinks.

    Raises:
        None.
    """
    return Path(__file__).resolve().parent.parent


def sha256_bytes(payload: bytes) -> str:
    """Hash bytes with SHA-256.

    Args:
        payload: Raw bytes. They are not decoded or executed.

    Returns:
        Lowercase hexadecimal digest.
    """
    return hashlib.sha256(payload).hexdigest()


def sha256_file(path: Path) -> str:
    """Hash a file without loading it into an interpreter.

    Args:
        path: File to read in binary mode.

    Returns:
        Lowercase hexadecimal digest of the file bytes.

    Raises:
        ManuscriptError: The file cannot be read.
    """
    digest = hashlib.sha256()
    try:
        with path.open("rb") as handle:
            while True:
                chunk = handle.read(1024 * 1024)
                if not chunk:
                    break
                digest.update(chunk)
    except OSError as exc:
        raise ManuscriptError(f"Could not read {path}: {exc}") from exc
    return digest.hexdigest()


def read_bytes(path: Path) -> bytes:
    """Read a source file once and refuse oversized input.

    Args:
        path: Existing file. It is opened read-only.

    Returns:
        The file contents.

    Raises:
        ManuscriptError: The file is missing, unreadable, or larger than the
            supported size.
    """
    if not path.is_file():
        raise ManuscriptError(f"Manuscript file not found: {path}")
    try:
        size = path.stat().st_size
    except OSError as exc:
        raise ManuscriptError(f"Could not stat {path}: {exc}") from exc
    if size > MAX_SOURCE_BYTES:
        raise ManuscriptError(
            f"Refusing to read {path}: {size} bytes exceeds {MAX_SOURCE_BYTES}."
        )
    try:
        return path.read_bytes()
    except OSError as exc:
        raise ManuscriptError(f"Could not read {path}: {exc}") from exc


def word_count(text: str) -> int:
    """Count whitespace-separated tokens.

    This is a navigation count. Punctuation stays attached to tokens, so it is
    not a publisher's word count.

    Args:
        text: Reader-facing paragraph text.

    Returns:
        Number of non-empty tokens.
    """
    return len(re.findall(r"\S+", text))


def paragraph_id(ordinal: int, text: str) -> str:
    """Build a stable paragraph identifier.

    The identifier changes when the paragraph text or its position changes. It
    does not depend on chapter segmentation.

    Args:
        ordinal: One-based position among retained paragraphs.
        text: Exact stored paragraph text.

    Returns:
        Identifier shaped as ``p0001-`` plus eight hex characters.
    """
    digest = sha256_bytes(text.encode("utf-8"))[:8]
    return f"p{ordinal:04d}-{digest}"


def normalize_quote(text: str) -> str:
    """Normalize quotes and whitespace for a secondary citation check.

    Case is preserved. This helper never treats the text as instructions.

    Args:
        text: Quote or paragraph text.

    Returns:
        A single-spaced string with common punctuation variants folded.
    """
    value = unicodedata.normalize("NFKC", text)
    replacements = {
        "\u2018": "'",
        "\u2019": "'",
        "\u201c": '"',
        "\u201d": '"',
        "\u00ab": '"',
        "\u00bb": '"',
        "\u2013": "-",
        "\u2014": "-",
        "\u00a0": " ",
    }
    for source, target in replacements.items():
        value = value.replace(source, target)
    return re.sub(r"\s+", " ", value).strip()


def preview(text: str, limit: int = 80) -> str:
    """Build a single-line preview that cannot break a Markdown table.

    Args:
        text: Paragraph text.
        limit: Maximum preview length.

    Returns:
        Collapsed preview, possibly ending in an ellipsis.
    """
    collapsed = re.sub(r"\s+", " ", text).strip().replace("|", "/")
    if len(collapsed) <= limit:
        return collapsed
    return collapsed[: limit - 1].rstrip() + "…"


def read_json(path: Path) -> Any:
    """Load a JSON file as data.

    Args:
        path: JSON file. Its contents are not executed.

    Returns:
        The parsed JSON value.

    Raises:
        ManuscriptError: The file cannot be read or is not JSON.
    """
    try:
        raw = path.read_text(encoding="utf-8")
    except OSError as exc:
        raise ManuscriptError(f"Could not read {path}: {exc}") from exc
    try:
        return json.loads(raw)
    except json.JSONDecodeError as exc:
        raise ManuscriptError(f"Invalid JSON in {path}: {exc}") from exc


def dump_json(payload: Any) -> str:
    """Serialize JSON for an output artifact.

    Args:
        payload: JSON-compatible value.

    Returns:
        UTF-8 text with a trailing newline. Non-ASCII characters are preserved.
    """
    return json.dumps(payload, ensure_ascii=False, indent=2) + "\n"


def write_text(path: Path, text: str) -> None:
    """Write a generated artifact, creating parent directories.

    Args:
        path: Destination. Callers must already have checked that it is not
            the manuscript.
        text: Artifact contents.

    Raises:
        ManuscriptError: The destination cannot be written.
    """
    try:
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(text, encoding="utf-8", newline="\n")
    except OSError as exc:
        raise ManuscriptError(f"Could not write {path}: {exc}") from exc


def assert_distinct_output(source: Path, output: Path, label: str) -> None:
    """Refuse to overwrite an input with a generated artifact.

    Args:
        source: Input file that must remain unchanged.
        output: Requested destination.
        label: Artifact name used in the error.

    Raises:
        UsageError: The destination resolves to the source.
    """
    if source.resolve() == output.resolve():
        raise UsageError(f"Refusing to write {label} over the source file: {source}")


def decode_text_bytes(payload: bytes) -> tuple[str, str, list[str]]:
    """Decode manuscript bytes without executing them.

    Args:
        payload: Raw text-file bytes.

    Returns:
        Decoded text, encoding name, and human-readable warnings.

    Raises:
        ManuscriptError: The bytes contain NUL and are not a UTF-16 file with
            a byte-order mark, or a UTF-16 file cannot be decoded.
    """
    if payload.startswith((b"\xff\xfe", b"\xfe\xff")):
        try:
            return payload.decode("utf-16"), "utf-16", []
        except UnicodeDecodeError as exc:
            raise ManuscriptError(f"Could not decode UTF-16 text: {exc}") from exc
    if b"\x00" in payload:
        raise ManuscriptError("Refusing to read a binary file as text.")
    if payload.startswith(b"\xef\xbb\xbf"):
        return payload.decode("utf-8-sig"), "utf-8", []
    try:
        return payload.decode("utf-8"), "utf-8", []
    except UnicodeDecodeError:
        warning = "Decoded with windows-1252 because UTF-8 failed."
        return payload.decode("cp1252"), "windows-1252", [warning]


def manuscript_format(path: Path) -> str:
    """Map a suffix to a supported manuscript format.

    Args:
        path: Candidate manuscript path.

    Returns:
        ``docx``, ``txt``, or ``markdown``.

    Raises:
        UsageError: The suffix is not supported.
    """
    suffix = path.suffix.lower()
    if suffix == ".docx":
        return "docx"
    if suffix == ".txt":
        return "txt"
    if suffix in {".md", ".markdown"}:
        return "markdown"
    supported = ", ".join(sorted(SUPPORTED_SUFFIXES))
    raise UsageError(
        f"Unsupported manuscript format '{suffix or path.name}'. "
        f"Supported formats: {supported}."
    )
