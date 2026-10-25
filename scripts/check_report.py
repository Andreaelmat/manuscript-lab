"""Check a finished editorial report against the index and the findings.

The check is mechanical. It can show that a direct quotation does not occur,
that a finding id is unknown, or that a confirmed finding is missing from the
report. It cannot show that the report's reasoning is right.
"""

from __future__ import annotations

import argparse
import re
import sys
from pathlib import Path
from typing import Any

from common import ManuscriptError, UsageError, assert_distinct_output, dump_json, read_json, write_text
from finding_record import resolve_editorial_status
from quotes import quote_status


PARAGRAPH_ID = re.compile(r"`(p[0-9]{4,}-[0-9a-f]{8})`")
FINDING_ID = re.compile(r"\b(F-[0-9]{3,})\b")
SHA256 = re.compile(r"\b([0-9a-f]{64})\b")
INLINE_QUOTE = re.compile(r"«([^»]{8,})»|“([^”]{8,})”|\"([^\"]{8,})\"")
LIMIT_NOTE = (
    "Matching quotations and identifiers does not establish the semantic "
    "correctness of the report."
)


def check_report(
    report_text: str, index: dict[str, Any], findings: dict[str, Any]
) -> dict[str, Any]:
    """Compare report quotations and identifiers with the structured record.

    Args:
        report_text: Editorial report Markdown.
        index: Manuscript index.
        findings: Findings document.

    Returns:
        A check document with errors, warnings, and ``semantic_correctness``
        set to ``not_assessed``.
    """
    paragraphs = _paragraphs(index)
    quotations = _quotations(report_text, paragraphs)
    errors, warnings = _quote_issues(quotations)
    errors.extend(_identifier_errors(report_text, findings))
    warnings.extend(_coverage_warnings(report_text, findings))
    hash_errors, hash_warnings = _hash_findings(report_text, index)
    errors.extend(hash_errors)
    warnings.extend(hash_warnings)
    return {
        "format_version": 1,
        "document_type": "report_check",
        "semantic_correctness": "not_assessed",
        "limit": LIMIT_NOTE,
        "quotations": quotations,
        "errors": errors,
        "warnings": warnings,
        "counts": _counts(quotations),
    }


def main(argv: list[str] | None = None) -> int:
    """Run the report check.

    Args:
        argv: Arguments excluding the program name.

    Returns:
        ``0`` when no mechanical errors were found, ``1`` when quotations or
        identifiers fail, ``2`` on usage errors.
    """
    try:
        return _run(argv)
    except ManuscriptError as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 2


def _run(argv: list[str] | None) -> int:
    """Load the three inputs and write the check document.

    Args:
        argv: Arguments excluding the program name.

    Returns:
        The check exit code.
    """
    parser = _parser()
    args = parser.parse_args(argv)
    report_path = Path(args.report)
    index_path = Path(args.index)
    findings_path = Path(args.findings)
    index = _object(read_json(index_path), "index")
    findings = _object(read_json(findings_path), "findings")
    try:
        report_text = report_path.read_text(encoding="utf-8")
    except OSError as exc:
        raise ManuscriptError(f"Could not read {report_path}: {exc}") from exc
    document = check_report(report_text, index, findings)
    rendered = dump_json(document)
    if args.output:
        output = Path(args.output)
        _protect(output, report_path, index_path, findings_path, index)
        write_text(output, rendered)
    else:
        sys.stdout.write(rendered)
    return 1 if document["errors"] else 0


def _parser() -> argparse.ArgumentParser:
    """Build the command-line parser.

    Returns:
        Parser for the report check.
    """
    parser = argparse.ArgumentParser(description="Check report quotations and finding identifiers.")
    parser.add_argument("--report", required=True, help="Editorial report Markdown")
    parser.add_argument("--index", required=True, help="Manuscript index JSON")
    parser.add_argument("--findings", required=True, help="Findings JSON")
    parser.add_argument("--output", help="Write the check JSON here instead of stdout")
    return parser


def _quotations(report_text: str, paragraphs: dict[str, dict[str, Any]]) -> list[dict[str, Any]]:
    """Extract and verify direct quotations from the report.

    Args:
        report_text: Report Markdown.
        paragraphs: Index paragraphs.

    Returns:
        One record per block quote and per inline quotation span.
    """
    records = [_block_record(item, paragraphs) for item in _block_quotes(report_text)]
    records.extend(_inline_record(item, paragraphs) for item in _inline_quotes(report_text))
    return records


def _block_quotes(report_text: str) -> list[dict[str, Any]]:
    """Collect Markdown block quotes and any paragraph id attached to them.

    Args:
        report_text: Report Markdown.

    Returns:
        Quote texts, line numbers, and optional paragraph ids.
    """
    lines = report_text.splitlines()
    found: list[dict[str, Any]] = []
    index = 0
    while index < len(lines):
        if not _is_quote_line(lines[index]):
            index += 1
            continue
        start = index + 1
        parts: list[str] = []
        paragraph_id = ""
        while index < len(lines) and _is_quote_line(lines[index]):
            content = lines[index].lstrip()[1:].strip()
            marker = PARAGRAPH_ID.search(content)
            if marker and _citation_line(content):
                paragraph_id = marker.group(1)
            elif content:
                parts.append(content)
            index += 1
        quote = " ".join(parts).strip()
        if quote:
            found.append({"quote": quote, "line": start, "paragraph_id": paragraph_id, "kind": "blockquote"})
    return found


def _inline_quotes(report_text: str) -> list[dict[str, Any]]:
    """Collect guillemet and double-quoted spans outside block quotes.

    Args:
        report_text: Report Markdown.

    Returns:
        Inline quote texts and line numbers.
    """
    found: list[dict[str, Any]] = []
    for line_number, line in enumerate(report_text.splitlines(), start=1):
        if _is_quote_line(line):
            continue
        for match in INLINE_QUOTE.finditer(line):
            quote = next(group for group in match.groups() if group)
            found.append({"quote": quote, "line": line_number, "paragraph_id": "", "kind": "inline"})
    return found


def _block_record(item: dict[str, Any], paragraphs: dict[str, dict[str, Any]]) -> dict[str, Any]:
    """Verify one block quote.

    Args:
        item: Extracted block quote.
        paragraphs: Index paragraphs.

    Returns:
        Quotation record.
    """
    status, found_in, aligned = quote_status(item["quote"], item["paragraph_id"], paragraphs)
    return _record(item, status, found_in, aligned)


def _inline_record(item: dict[str, Any], paragraphs: dict[str, dict[str, Any]]) -> dict[str, Any]:
    """Verify one inline quotation against the whole index.

    Args:
        item: Extracted inline quote.
        paragraphs: Index paragraphs.

    Returns:
        Quotation record. Inline spans have no cited paragraph id.
    """
    status, found_in, aligned = quote_status(item["quote"], "", paragraphs)
    return _record(item, status, found_in, aligned)


def _record(item: dict[str, Any], status: str, found_in: list[str], aligned: str) -> dict[str, Any]:
    """Assemble one quotation result.

    Args:
        item: Extracted quote.
        status: Quote status from the shared checker.
        found_in: Paragraph ids that contain the quote.
        aligned: Alignment label.

    Returns:
        Result object stored in the check document.
    """
    return {
        "kind": item["kind"],
        "line": item["line"],
        "paragraph_id": item["paragraph_id"] or None,
        "quote": item["quote"],
        "quote_check": status,
        "found_in": found_in,
        "alignment": aligned,
        "editorial_judgment": "not_assessed",
    }


def _quote_issues(quotations: list[dict[str, Any]]) -> tuple[list[str], list[str]]:
    """Separate failed quotations from alignment warnings.

    Args:
        quotations: Checked quotations.

    Returns:
        Error strings and warning strings.
    """
    errors: list[str] = []
    warnings: list[str] = []
    for item in quotations:
        if str(item["quote_check"]).startswith("not_found"):
            errors.append(
                f"Line {item['line']}: unverified {item['kind']} quotation: {item['quote']}"
            )
        elif item["alignment"] in {"mid_token", "inside_quotation"}:
            warnings.append(
                f"Line {item['line']}: quotation matches {item['alignment']} in the manuscript."
            )
    return errors, warnings


def _identifier_errors(report_text: str, findings: dict[str, Any]) -> list[str]:
    """Flag finding ids that the report names and the findings file lacks.

    Args:
        report_text: Report Markdown.
        findings: Findings document.

    Returns:
        Error strings.
    """
    known = _finding_ids(findings)
    errors: list[str] = []
    for identifier in dict.fromkeys(FINDING_ID.findall(report_text)):
        if identifier not in known:
            errors.append(f"Report names unknown finding {identifier}")
    return errors


def _coverage_warnings(report_text: str, findings: dict[str, Any]) -> list[str]:
    """Warn when a judged finding id does not appear in the report.

    Args:
        report_text: Report Markdown.
        findings: Findings document.

    Returns:
        Warning strings. Absence is a structural gap, not a semantic verdict.
    """
    present = set(FINDING_ID.findall(report_text))
    warnings: list[str] = []
    for finding in _finding_list(findings):
        status = resolve_editorial_status(finding)
        identifier = finding.get("id")
        if status in {"confirmed", "downgraded", "rejected"} and identifier not in present:
            warnings.append(f"{identifier} has editorial status {status} and is absent from the report")
    return warnings


def _hash_findings(report_text: str, index: dict[str, Any]) -> tuple[list[str], list[str]]:
    """Compare SHA-256 strings in the report with the manuscript hash.

    Args:
        report_text: Report Markdown.
        index: Manuscript index.

    Returns:
        Errors for a hash that does not match, and a warning when the report
        names no hash at all. Matching characters do not prove the prose.
    """
    expected = index.get("source", {}).get("sha256") if isinstance(index.get("source"), dict) else None
    if not isinstance(expected, str):
        return ["Index is missing a manuscript SHA-256."], []
    found = SHA256.findall(report_text)
    if not found:
        return [], ["Report does not include the manuscript SHA-256."]
    errors = [f"Report hash {digest} does not match the index" for digest in found if digest != expected]
    return errors, []


def _counts(quotations: list[dict[str, Any]]) -> dict[str, int]:
    """Count quotation statuses.

    Args:
        quotations: Checked quotations.

    Returns:
        Status counts.
    """
    counts = {
        "verified_exact": 0,
        "verified_normalized": 0,
        "not_found": 0,
        "not_found_at_cited_paragraph": 0,
    }
    for item in quotations:
        status = item["quote_check"]
        if status in counts:
            counts[status] += 1
    return counts


def _paragraphs(index: dict[str, Any]) -> dict[str, dict[str, Any]]:
    """Index paragraphs by id.

    Args:
        index: Manuscript index.

    Returns:
        Paragraph lookup.

    Raises:
        ManuscriptError: The index has no usable paragraphs.
    """
    items = index.get("paragraphs")
    if not isinstance(items, list):
        raise ManuscriptError("Index document is missing paragraphs.")
    return {
        item["id"]: item
        for item in items
        if isinstance(item, dict) and isinstance(item.get("id"), str)
    }


def _finding_list(findings: dict[str, Any]) -> list[dict[str, Any]]:
    """Return finding objects.

    Args:
        findings: Findings document.

    Returns:
        The findings list, or an empty list when the document has none.
    """
    items = findings.get("findings")
    if not isinstance(items, list):
        return []
    return [item for item in items if isinstance(item, dict)]


def _finding_ids(findings: dict[str, Any]) -> set[str]:
    """Return finding identifiers.

    Args:
        findings: Findings document.

    Returns:
        Identifiers present on finding objects.
    """
    return {item["id"] for item in _finding_list(findings) if isinstance(item.get("id"), str)}


def _is_quote_line(line: str) -> bool:
    """Return whether a Markdown line opens a block quote.

    Args:
        line: One report line.

    Returns:
        True when the stripped line starts with ``>``.
    """
    return line.lstrip().startswith(">")


def _citation_line(content: str) -> bool:
    """Return whether a block-quote line names a paragraph id.

    Args:
        content: Text after the ``>`` marker.

    Returns:
        True when the line contains a paragraph id. The chapter title beside
        it is a locator, not part of the manuscript quotation.
    """
    return PARAGRAPH_ID.search(content) is not None


def _object(payload: Any, label: str) -> dict[str, Any]:
    """Require a JSON object.

    Args:
        payload: Parsed JSON.
        label: Name used in the error.

    Returns:
        The object.

    Raises:
        ManuscriptError: The payload is not an object.
    """
    if not isinstance(payload, dict):
        raise ManuscriptError(f"{label} JSON must be an object.")
    return payload


def _protect(
    output: Path,
    report_path: Path,
    index_path: Path,
    findings_path: Path,
    index: dict[str, Any],
) -> None:
    """Refuse to overwrite the report inputs or the manuscript.

    Args:
        output: Requested destination.
        report_path: Report input.
        index_path: Index input.
        findings_path: Findings input.
        index: Index used to find the manuscript path.

    Raises:
        UsageError: The destination is one of the inputs.
    """
    for source, label in (
        (report_path, "report check"),
        (index_path, "report check"),
        (findings_path, "report check"),
    ):
        assert_distinct_output(source, output, label)
    manuscript = index.get("source", {}).get("path") if isinstance(index.get("source"), dict) else None
    if isinstance(manuscript, str) and manuscript:
        assert_distinct_output(Path(manuscript), output, "report check")


if __name__ == "__main__":
    sys.exit(main())
