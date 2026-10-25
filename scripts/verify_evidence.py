"""Check finding quotations against an indexed manuscript.

A successful quote check only means the quoted characters occur in the cited
paragraph. It says nothing about whether the editorial interpretation is right.
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
from finding_record import record_errors, resolve_editorial_status
from quotes import quote_status
from schema_check import validate_instance


QUOTE_NOTE = "A quote check does not confirm or reject the editorial interpretation."


def verify_evidence(index: dict[str, Any], findings: dict[str, Any]) -> dict[str, Any]:
    """Validate findings and compare every quote with the index.

    Args:
        index: Index document from ``index_manuscript.py``.
        findings: Findings document. ``quote_check`` values in it are ignored
            and computed again.

    Returns:
        Verification report. ``editorial_judgment`` is always ``not_assessed``.

    Raises:
        ManuscriptError: The index or the findings schema cannot be loaded.
    """
    schema_errors = validate_instance(findings, _findings_schema())
    semantic_errors = [] if schema_errors else semantic_findings_errors(findings)
    if _index_usable(index) and not schema_errors:
        hash_error = _hash_error(index, findings)
        if hash_error:
            semantic_errors.append(hash_error)
    results = _results(index, findings) if _index_usable(index) and not schema_errors else []
    if not _index_usable(index):
        schema_errors.append("Index document is missing paragraph text.")
    return _report(index, findings, results, schema_errors, semantic_errors)


def semantic_findings_errors(findings: dict[str, Any]) -> list[str]:
    """Apply editorial-record rules that JSON Schema cannot express.

    Args:
        findings: A document that already matches the findings schema.

    Returns:
        Semantic errors. Quote truth is not decided here.
    """
    errors: list[str] = []
    errors.extend(_review_errors(findings["independent_review"]))
    version = findings.get("format_version")
    version_number = version if isinstance(version, int) else 1
    for finding in findings["findings"]:
        errors.extend(record_errors(finding, version_number))
    errors.extend(_finding_errors(findings["findings"]))
    return errors


def main(argv: list[str] | None = None) -> int:
    """Run the verification command.

    Args:
        argv: Arguments excluding the program name.

    Returns:
        ``0`` when the schema, semantic rules, and quotes pass; ``1`` when a
        finding fails those checks; ``2`` on usage or read errors.
    """
    try:
        return _run(argv)
    except ManuscriptError as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 2


def _run(argv: list[str] | None) -> int:
    """Load inputs, write the report, and set the exit code.

    Args:
        argv: Arguments excluding the program name.

    Returns:
        The verification exit code.
    """
    parser = _parser()
    args = parser.parse_args(argv)
    index_path = Path(args.index)
    findings_path = Path(args.findings)
    index = _load_document(index_path, "index")
    findings = _load_document(findings_path, "findings")
    report = verify_evidence(index, findings)
    rendered = dump_json(report)
    if args.output:
        output = Path(args.output)
        _refuse_protected(output, index_path, findings_path, index)
        write_text(output, rendered)
    else:
        sys.stdout.write(rendered)
    if args.update_findings:
        _update_findings(args, findings, report, index_path, findings_path, index)
    return _exit_code(report)


def _parser() -> argparse.ArgumentParser:
    """Build the command-line parser.

    Returns:
        Parser for the verification command.
    """
    parser = argparse.ArgumentParser(
        description="Verify finding quotations against an indexed manuscript."
    )
    parser.add_argument("--index", required=True, help="Index JSON from index_manuscript.py")
    parser.add_argument("--findings", required=True, help="Findings JSON to check")
    parser.add_argument("--output", help="Write the verification report to this path")
    parser.add_argument(
        "--update-findings",
        help="Write a separate findings file with recomputed quote_check values",
    )
    parser.add_argument(
        "--in-place",
        action="store_true",
        help="Allow --update-findings to replace the input findings file",
    )
    return parser


def _load_document(path: Path, label: str) -> dict[str, Any]:
    """Load a JSON object.

    Args:
        path: JSON file.
        label: Name used in errors.

    Returns:
        The parsed object.

    Raises:
        ManuscriptError: The file is not a JSON object.
    """
    payload = read_json(path)
    if not isinstance(payload, dict):
        raise ManuscriptError(f"{label} JSON must be an object: {path}")
    return payload


def _findings_schema() -> dict[str, Any]:
    """Load the bundled findings schema.

    Returns:
        Parsed schema object.

    Raises:
        ManuscriptError: The schema file is missing or invalid.
    """
    path = skill_root() / "templates" / "findings.schema.json"
    payload = read_json(path)
    if not isinstance(payload, dict):
        raise ManuscriptError(f"Findings schema is invalid: {path}")
    return payload


def _index_usable(index: dict[str, Any]) -> bool:
    """Return whether the index has paragraph text that can be searched.

    Args:
        index: Candidate index document.

    Returns:
        True when paragraphs are a list of objects containing id and text.
    """
    paragraphs = index.get("paragraphs")
    source = index.get("source")
    if not isinstance(paragraphs, list) or not isinstance(source, dict):
        return False
    return all(
        isinstance(item, dict) and isinstance(item.get("id"), str) and isinstance(item.get("text"), str)
        for item in paragraphs
    )


def _hash_error(index: dict[str, Any], findings: dict[str, Any]) -> str | None:
    """Return an error when findings point at a different manuscript hash.

    Args:
        index: Usable index document.
        findings: Schema-valid findings document.

    Returns:
        An error string, or None when the hashes match.
    """
    if findings.get("manuscript_sha256") != index["source"].get("sha256"):
        return "manuscript_sha256 does not match the index source"
    return None


def _results(index: dict[str, Any], findings: dict[str, Any]) -> list[dict[str, Any]]:
    """Check every evidence quote.

    Args:
        index: Usable index document.
        findings: Schema-valid findings document.

    Returns:
        One result per evidence item. Input ``quote_check`` values are ignored.
    """
    paragraphs = _paragraph_map(index["paragraphs"])
    results: list[dict[str, Any]] = []
    for finding in findings["findings"]:
        for evidence_index, evidence in enumerate(finding["evidence"]):
            results.append(_one_result(finding["id"], evidence_index, evidence, paragraphs))
    return results


def _paragraph_map(paragraphs: list[dict[str, Any]]) -> dict[str, dict[str, Any]]:
    """Index paragraphs by identifier.

    Args:
        paragraphs: Index paragraphs.

    Returns:
        Mapping from paragraph id to paragraph. Later duplicates replace
        earlier ones; the index builder does not emit duplicates.
    """
    return {item["id"]: item for item in paragraphs}


def _one_result(
    finding_id: str,
    evidence_index: int,
    evidence: dict[str, Any],
    paragraphs: dict[str, dict[str, Any]],
) -> dict[str, Any]:
    """Compare one quote with the cited paragraph and the rest of the index.

    Args:
        finding_id: Finding identifier.
        evidence_index: Position of the quote inside the finding.
        evidence: Evidence object. Its stored ``quote_check`` is ignored.
        paragraphs: Paragraph lookup.

    Returns:
        A verification result whose editorial judgment is not assessed.
    """
    quote = str(evidence["quote"])
    cited = str(evidence["paragraph_id"])
    status, found_in, aligned = quote_status(quote, cited, paragraphs)
    return {
        "finding_id": finding_id,
        "evidence_index": evidence_index,
        "paragraph_id": cited,
        "quote_check": status,
        "found_in": found_in,
        "alignment": aligned,
        "editorial_judgment": "not_assessed",
        "note": QUOTE_NOTE,
    }


def _review_errors(review: dict[str, Any]) -> list[str]:
    """Check the independent-review record.

    Args:
        review: ``independent_review`` object.

    Returns:
        Errors when a same-model pass is labeled independent.
    """
    errors: list[str] = []
    performed = review["performed"]
    same_model = review["same_as_primary_model"]
    if performed and same_model is True:
        errors.append("A same-model pass cannot be recorded as an independent review.")
    elif performed and same_model is not False:
        errors.append(
            "independent_review.same_as_primary_model must be false when performed is true."
        )
    if performed and not str(review["reviewer_model"]).strip():
        errors.append("independent_review.reviewer_model is required when a review was performed.")
    if not review["requested"] and performed:
        errors.append("independent_review.performed requires requested to be true.")
    return errors


def _finding_errors(findings: list[dict[str, Any]]) -> list[str]:
    """Check identifiers, evidence links, and completed verification fields.

    Args:
        findings: Finding objects.

    Returns:
        Semantic errors.
    """
    errors: list[str] = []
    identifiers = [item["id"] for item in findings]
    if len(identifiers) != len(set(identifiers)):
        errors.append("Finding ids must be unique.")
    for finding in findings:
        errors.extend(_one_finding_errors(finding))
    return errors


def _one_finding_errors(finding: dict[str, Any]) -> list[str]:
    """Check one finding's evidence links and completed review fields.

    Args:
        finding: Finding object.

    Returns:
        Semantic errors for this finding.
    """
    errors: list[str] = []
    cited = set(finding["paragraph_ids"])
    for evidence in finding["evidence"]:
        if evidence["paragraph_id"] not in cited:
            errors.append(
                f"{finding['id']} cites {evidence['paragraph_id']} in evidence "
                "but omits it from paragraph_ids."
            )
    status = resolve_editorial_status(finding)
    if status == "unreviewed" or status is None:
        return errors
    if not finding["counterarguments"]:
        errors.append(f"{finding['id']} needs a counterargument once editorial status is set.")
    if not str(finding["uncertainty"]).strip():
        errors.append(f"{finding['id']} needs a residual uncertainty note once editorial status is set.")
    return errors


def _report(
    index: dict[str, Any],
    findings: dict[str, Any],
    results: list[dict[str, Any]],
    schema_errors: list[str],
    semantic_errors: list[str],
) -> dict[str, Any]:
    """Assemble the verification report.

    Args:
        index: Index document, possibly unusable.
        findings: Findings document.
        results: Quote results. Empty when validation failed first.
        schema_errors: Schema errors.
        semantic_errors: Semantic errors.

    Returns:
        Report document.
    """
    counts = {
        "verified_exact": 0,
        "verified_normalized": 0,
        "not_found": 0,
        "not_found_at_cited_paragraph": 0,
    }
    for result in results:
        counts[result["quote_check"]] += 1
    source = index.get("source") if isinstance(index.get("source"), dict) else {}
    return {
        "format_version": 1,
        "document_type": "verification",
        "manuscript_sha256": source.get("sha256"),
        "findings_checked": len(findings.get("findings", [])) if isinstance(findings.get("findings"), list) else 0,
        "evidence_checked": len(results),
        "counts": counts,
        "schema_errors": schema_errors,
        "semantic_errors": semantic_errors,
        "results": results,
    }


def _refuse_protected(
    output: Path,
    index_path: Path,
    findings_path: Path,
    index: dict[str, Any],
) -> None:
    """Refuse to overwrite the index, findings input, or manuscript.

    Args:
        output: Requested report path.
        index_path: Index input path.
        findings_path: Findings input path.
        index: Index document, used to find the manuscript path.

    Raises:
        UsageError: The output collides with a protected file.
    """
    assert_distinct_output(index_path, output, "verification report")
    assert_distinct_output(findings_path, output, "verification report")
    manuscript = index.get("source", {}).get("path") if isinstance(index.get("source"), dict) else None
    if isinstance(manuscript, str) and manuscript:
        assert_distinct_output(Path(manuscript), output, "verification report")


def _update_findings(
    args: argparse.Namespace,
    findings: dict[str, Any],
    report: dict[str, Any],
    index_path: Path,
    findings_path: Path,
    index: dict[str, Any],
) -> None:
    """Write a findings copy with script-computed quote checks.

    Args:
        args: Parsed arguments.
        findings: Original findings object.
        report: Verification report.
        index_path: Index path protected from overwrite.
        findings_path: Findings path protected unless ``--in-place`` is set.
        index: Index document used to protect the manuscript path.

    Raises:
        UsageError: The destination replaces an input without permission, or
            the findings cannot be updated because validation failed.
    """
    destination = Path(args.update_findings)
    replacing_input = destination.resolve() == findings_path.resolve()
    if replacing_input and not args.in_place:
        raise UsageError("Refusing to replace findings JSON without --in-place.")
    assert_distinct_output(index_path, destination, "updated findings")
    manuscript = index.get("source", {}).get("path") if isinstance(index.get("source"), dict) else None
    if isinstance(manuscript, str) and manuscript:
        assert_distinct_output(Path(manuscript), destination, "updated findings")
    if not replacing_input:
        assert_distinct_output(findings_path, destination, "updated findings")
    if report["schema_errors"]:
        raise UsageError("Refusing to update findings while schema errors remain.")
    updated = _apply_quote_checks(findings, report["results"])
    write_text(destination, dump_json(updated))


def _apply_quote_checks(findings: dict[str, Any], results: list[dict[str, Any]]) -> dict[str, Any]:
    """Copy findings and replace quote checks with script results.

    Args:
        findings: Original findings object.
        results: Quote results aligned with evidence order.

    Returns:
        A new findings object. The input is not mutated.
    """
    updated = json_copy(findings)
    by_key = {(item["finding_id"], item["evidence_index"]): item for item in results}
    for finding in updated["findings"]:
        for index, evidence in enumerate(finding["evidence"]):
            result = by_key.get((finding["id"], index))
            if result is not None:
                evidence["quote_check"] = result["quote_check"]
    return updated


def json_copy(payload: dict[str, Any]) -> dict[str, Any]:
    """Deep-copy a JSON object.

    Args:
        payload: JSON object made of dicts, lists, and scalars.

    Returns:
        A detached copy. The input object is not mutated.
    """
    return copy.deepcopy(payload)


def _exit_code(report: dict[str, Any]) -> int:
    """Choose the process exit code for a report.

    Args:
        report: Verification report.

    Returns:
        ``1`` when any check failed, otherwise ``0``.
    """
    failed_quote = any(item["quote_check"].startswith("not_found") for item in report["results"])
    if report["schema_errors"] or report["semantic_errors"] or failed_quote:
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
