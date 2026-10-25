"""Validate a narrative fact ledger against an index.

The script checks shape, paragraph ids, and quotations. It does not extract
facts from the manuscript and it does not decide whether two claims conflict.
"""

from __future__ import annotations

import argparse
import copy
import sys
from pathlib import Path
from typing import Any

from common import (
    ManuscriptError,
    UsageError,
    assert_distinct_output,
    dump_json,
    read_json,
    skill_root,
    write_text,
)
from quotes import quote_status
from schema_check import validate_instance


FULL_READING_NOTE = (
    "Chapter ids in this ledger do not establish that those chapters were read in full."
)


def verify_ledger(index: dict[str, Any], ledger: dict[str, Any]) -> dict[str, Any]:
    """Validate a ledger and recompute every quotation check.

    Args:
        index: Manuscript index.
        ledger: Narrative fact ledger. Stored ``quote_check`` values are ignored.

    Returns:
        A check document. ``semantic_correctness`` is ``not_assessed`` and
        ``full_reading_established`` is false.

    Raises:
        ManuscriptError: The index or the bundled schema cannot be used.
    """
    paragraphs = _paragraphs(index)
    schema_errors = validate_instance(ledger, _schema())
    record_errors = [] if schema_errors else _record_errors(ledger, index, paragraphs)
    results = [] if schema_errors else _quote_results(ledger, paragraphs)
    failed = [item for item in results if str(item["quote_check"]).startswith("not_found")]
    return {
        "format_version": 1,
        "document_type": "ledger_check",
        "manuscript_sha256": _sha(index),
        "semantic_correctness": "not_assessed",
        "full_reading_established": False,
        "limit": FULL_READING_NOTE,
        "entries_checked": len(ledger.get("entries", [])) if isinstance(ledger.get("entries"), list) else 0,
        "schema_errors": schema_errors,
        "record_errors": record_errors,
        "quote_results": results,
        "counts": _counts(results),
        "passed": not schema_errors and not record_errors and not failed,
    }


def main(argv: list[str] | None = None) -> int:
    """Run the ledger check.

    Args:
        argv: Arguments excluding the program name.

    Returns:
        ``0`` when the ledger passes, ``1`` when it does not, ``2`` on usage errors.
    """
    try:
        return _run(argv)
    except ManuscriptError as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 2


def _run(argv: list[str] | None) -> int:
    """Load inputs and write the check.

    Args:
        argv: Arguments excluding the program name.

    Returns:
        The process exit code.
    """
    parser = _parser()
    args = parser.parse_args(argv)
    index_path = Path(args.index)
    ledger_path = Path(args.ledger)
    index = _object(read_json(index_path), "index")
    ledger = _object(read_json(ledger_path), "ledger")
    document = verify_ledger(index, ledger)
    if args.output:
        output = Path(args.output)
        _protect(output, index_path, ledger_path, index)
        write_text(output, dump_json(document))
    else:
        sys.stdout.write(dump_json(document))
    if args.update_ledger:
        _update(args, ledger, document, index_path, ledger_path, index)
    return 0 if document["passed"] else 1


def _parser() -> argparse.ArgumentParser:
    """Build the command-line parser.

    Returns:
        Parser for the ledger check.
    """
    parser = argparse.ArgumentParser(description="Validate a narrative fact ledger.")
    parser.add_argument("--index", required=True, help="Manuscript index JSON")
    parser.add_argument("--ledger", required=True, help="Narrative ledger JSON")
    parser.add_argument("--output", help="Write the check JSON here instead of stdout")
    parser.add_argument("--update-ledger", help="Write a copy with recomputed quote_check values")
    parser.add_argument(
        "--in-place",
        action="store_true",
        help="Allow --update-ledger to replace the input ledger",
    )
    return parser


def _record_errors(
    ledger: dict[str, Any],
    index: dict[str, Any],
    paragraphs: dict[str, dict[str, Any]],
) -> list[str]:
    """Apply ledger rules that the schema cannot express.

    Args:
        ledger: Schema-valid ledger.
        index: Manuscript index.
        paragraphs: Paragraph lookup.

    Returns:
        Record errors. An empty list does not mean the claims are true.
    """
    errors: list[str] = []
    if ledger.get("manuscript_sha256") != _sha(index):
        errors.append("manuscript_sha256 does not match the index")
    entries = ledger["entries"]
    identifiers = [item["id"] for item in entries]
    if len(identifiers) != len(set(identifiers)):
        errors.append("Ledger entry ids must be unique.")
    known = set(identifiers)
    errors.extend(_reading_errors(ledger.get("reading"), index, paragraphs))
    for entry in entries:
        errors.extend(_entry_errors(entry, known, paragraphs))
    return errors


def _entry_errors(
    entry: dict[str, Any],
    known: set[str],
    paragraphs: dict[str, dict[str, Any]],
) -> list[str]:
    """Check one ledger entry.

    Args:
        entry: Ledger entry.
        known: Entry ids in the same ledger.
        paragraphs: Paragraph lookup.

    Returns:
        Errors for this entry.
    """
    errors: list[str] = []
    identifier = entry["id"]
    errors.extend(_certainty_errors(entry))
    cited = set(entry["paragraph_ids"])
    for evidence in entry["evidence"]:
        if evidence["paragraph_id"] not in cited:
            errors.append(f"{identifier} evidence paragraph is missing from paragraph_ids")
    for paragraph_id in cited:
        if paragraph_id not in paragraphs:
            errors.append(f"{identifier} cites unknown paragraph {paragraph_id}")
    errors.extend(_link_errors(identifier, entry["incompatible_with"], known, "incompatible_with"))
    errors.extend(_link_errors(identifier, entry["revised_by"], known, "revised_by"))
    if entry["revised_by"] and entry["certainty"] != "revised":
        errors.append(f"{identifier} lists a later revision but certainty is not revised")
    return errors


def _certainty_errors(entry: dict[str, Any]) -> list[str]:
    """Reject records that treat an unsettled claim as a certain fact.

    Args:
        entry: Ledger entry.

    Returns:
        Errors when certainty overstates the claim kind or the source.
    """
    identifier = entry["id"]
    if entry["certainty"] != "certain":
        return []
    if entry["claim_kind"] in {"hypothesis", "potentially_false_statement"}:
        return [f"{identifier} cannot be certain while its claim kind is unsettled"]
    if entry["source"] == "inference":
        return [f"{identifier} cannot be certain when the source is inference"]
    return []


def _link_errors(identifier: str, links: list[str], known: set[str], field: str) -> list[str]:
    """Check cross-references between ledger entries.

    Args:
        identifier: Current entry id.
        links: Ids named by the entry.
        known: Ids that exist in the ledger.
        field: Field name used in messages.

    Returns:
        Errors for unknown or self links.
    """
    errors: list[str] = []
    for link in links:
        if link == identifier:
            errors.append(f"{identifier} lists itself in {field}")
        elif link not in known:
            errors.append(f"{identifier} {field} references unknown entry {link}")
    return errors


def _reading_errors(
    reading: Any,
    index: dict[str, Any],
    paragraphs: dict[str, dict[str, Any]],
) -> list[str]:
    """Check optional reading notes against the index.

    Args:
        reading: Reading object, or None when omitted.
        index: Manuscript index.
        paragraphs: Paragraph lookup.

    Returns:
        Errors for ids that are not in the index. Presence is not proof of reading.
    """
    if reading is None:
        return []
    chapters = {item["id"] for item in index.get("chapters", []) if isinstance(item, dict)}
    errors: list[str] = []
    if not chapters and (reading["chapters_opened"] or reading["not_fully_read"]):
        errors.append("Reading note names chapters but the index has no confirmed chapters.")
    for chapter_id in reading["chapters_opened"] + reading["not_fully_read"]:
        if chapters and chapter_id not in chapters:
            errors.append(f"Reading note cites unknown chapter {chapter_id}")
    for paragraph_id in reading["paragraphs_reread"]:
        if paragraph_id not in paragraphs:
            errors.append(f"Reading note cites unknown paragraph {paragraph_id}")
    return errors


def _quote_results(
    ledger: dict[str, Any], paragraphs: dict[str, dict[str, Any]]
) -> list[dict[str, Any]]:
    """Recompute quotation checks for every evidence item.

    Args:
        ledger: Schema-valid ledger.
        paragraphs: Paragraph lookup.

    Returns:
        One result per evidence item. Editorial judgment is not assessed.
    """
    results: list[dict[str, Any]] = []
    for entry in ledger["entries"]:
        for index, evidence in enumerate(entry["evidence"]):
            status, found_in, aligned = quote_status(
                str(evidence["quote"]), str(evidence["paragraph_id"]), paragraphs
            )
            results.append(
                {
                    "entry_id": entry["id"],
                    "evidence_index": index,
                    "paragraph_id": evidence["paragraph_id"],
                    "quote_check": status,
                    "found_in": found_in,
                    "alignment": aligned,
                    "editorial_judgment": "not_assessed",
                }
            )
    return results


def _counts(results: list[dict[str, Any]]) -> dict[str, int]:
    """Count quotation statuses.

    Args:
        results: Quote results.

    Returns:
        Status counts.
    """
    counts = {
        "verified_exact": 0,
        "verified_normalized": 0,
        "not_found": 0,
        "not_found_at_cited_paragraph": 0,
    }
    for item in results:
        status = item["quote_check"]
        if status in counts:
            counts[status] += 1
    return counts


def _update(
    args: argparse.Namespace,
    ledger: dict[str, Any],
    document: dict[str, Any],
    index_path: Path,
    ledger_path: Path,
    index: dict[str, Any],
) -> None:
    """Write quote checks into a ledger copy.

    Args:
        args: Parsed arguments.
        ledger: Original ledger.
        document: Check document.
        index_path: Index path protected from overwrite.
        ledger_path: Ledger path protected unless ``--in-place`` is set.
        index: Index used to protect the manuscript.

    Raises:
        UsageError: The destination is unsafe or the ledger still has schema errors.
    """
    destination = Path(args.update_ledger)
    replacing = destination.resolve() == ledger_path.resolve()
    if replacing and not args.in_place:
        raise UsageError("Refusing to replace the ledger without --in-place.")
    _protect(destination, index_path, ledger_path if not replacing else index_path, index)
    if replacing:
        assert_distinct_output(index_path, destination, "updated ledger")
    if document["schema_errors"]:
        raise UsageError("Refusing to update a ledger that still has schema errors.")
    updated = copy.deepcopy(ledger)
    by_key = {(item["entry_id"], item["evidence_index"]): item for item in document["quote_results"]}
    for entry in updated["entries"]:
        for index, evidence in enumerate(entry["evidence"]):
            result = by_key.get((entry["id"], index))
            if result is not None:
                evidence["quote_check"] = result["quote_check"]
    write_text(destination, dump_json(updated))


def _protect(output: Path, index_path: Path, ledger_path: Path, index: dict[str, Any]) -> None:
    """Refuse to overwrite inputs or the manuscript.

    Args:
        output: Requested destination.
        index_path: Index path.
        ledger_path: Ledger path.
        index: Index document.

    Raises:
        UsageError: The destination collides with a protected file.
    """
    assert_distinct_output(index_path, output, "ledger check")
    assert_distinct_output(ledger_path, output, "ledger check")
    manuscript = index.get("source", {}).get("path") if isinstance(index.get("source"), dict) else None
    if isinstance(manuscript, str) and manuscript:
        assert_distinct_output(Path(manuscript), output, "ledger check")


def _paragraphs(index: dict[str, Any]) -> dict[str, dict[str, Any]]:
    """Index paragraphs by id.

    Args:
        index: Manuscript index.

    Returns:
        Paragraph lookup.

    Raises:
        ManuscriptError: The index has no paragraph list.
    """
    items = index.get("paragraphs")
    if not isinstance(items, list):
        raise ManuscriptError("Index document is missing paragraphs.")
    return {item["id"]: item for item in items if isinstance(item, dict) and isinstance(item.get("id"), str)}


def _sha(index: dict[str, Any]) -> str | None:
    """Return the manuscript hash stored on an index.

    Args:
        index: Manuscript index.

    Returns:
        The hash, or None when the index has no source hash.
    """
    source = index.get("source")
    if isinstance(source, dict) and isinstance(source.get("sha256"), str):
        return source["sha256"]
    return None


def _schema() -> dict[str, Any]:
    """Load the bundled ledger schema.

    Returns:
        Parsed schema object.

    Raises:
        ManuscriptError: The schema is missing or not an object.
    """
    path = skill_root() / "templates" / "narrative-ledger.schema.json"
    payload = read_json(path)
    if not isinstance(payload, dict):
        raise ManuscriptError(f"Ledger schema is invalid: {path}")
    return payload


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


if __name__ == "__main__":
    sys.exit(main())
