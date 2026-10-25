"""Validate an optional decision-and-motivation audit.

The script checks shape, paragraph ids, and quotations. It does not decide
whether a character chose well, and it does not assign a score.
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


OPEN_ASSESSMENTS = {"under_motivated", "obstacle_unexplained"}
CLOSED_ASSESSMENTS = {"credible", "resolved_later"}


def verify_decision_audit(
    index: dict[str, Any],
    audit: dict[str, Any],
    ledger: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """Validate a decision audit and recompute quotation checks.

    Args:
        index: Manuscript index.
        audit: Decision audit. Stored ``quote_check`` values are ignored.
        ledger: Optional narrative fact ledger. When present, ``ledger_entry_ids``
            must name entries in it.

    Returns:
        A check document. ``semantic_correctness`` is ``not_assessed``.
        A passing check is not a judgment that the decision is credible.

    Raises:
        ManuscriptError: The index or the bundled schema cannot be used.
    """
    paragraphs = _paragraphs(index)
    schema_errors = validate_instance(audit, _schema())
    record_errors = [] if schema_errors else _record_errors(audit, index, paragraphs, ledger)
    results = [] if schema_errors else _quote_results(audit, paragraphs)
    failed = [item for item in results if str(item["quote_check"]).startswith("not_found")]
    return {
        "format_version": 1,
        "document_type": "decision_check",
        "manuscript_sha256": _sha(index),
        "semantic_correctness": "not_assessed",
        "decisions_checked": len(audit.get("decisions", [])) if isinstance(audit.get("decisions"), list) else 0,
        "schema_errors": schema_errors,
        "record_errors": record_errors,
        "quote_results": results,
        "counts": _counts(results),
        "passed": not schema_errors and not record_errors and not failed,
        "note": "This check does not score the decision and does not prove the motive.",
    }


def main(argv: list[str] | None = None) -> int:
    """Run the decision-audit check.

    Args:
        argv: Arguments excluding the program name.

    Returns:
        ``0`` when the audit passes, ``1`` when it does not, ``2`` on usage errors.
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
    audit_path = Path(args.audit)
    index = _object(read_json(index_path), "index")
    audit = _object(read_json(audit_path), "audit")
    ledger = _load_ledger(args.ledger)
    document = verify_decision_audit(index, audit, ledger)
    if args.output:
        output = Path(args.output)
        _protect(output, index_path, audit_path, index)
        write_text(output, dump_json(document))
    else:
        sys.stdout.write(dump_json(document))
    if args.update_audit:
        _update(args, audit, document, index_path, audit_path, index)
    return 0 if document["passed"] else 1


def _parser() -> argparse.ArgumentParser:
    """Build the command-line parser.

    Returns:
        Parser for the decision-audit check.
    """
    parser = argparse.ArgumentParser(description="Validate an optional decision audit.")
    parser.add_argument("--index", required=True, help="Manuscript index JSON")
    parser.add_argument("--audit", required=True, help="Decision audit JSON")
    parser.add_argument("--ledger", help="Optional narrative ledger used to check entry ids")
    parser.add_argument("--output", help="Write the check JSON here instead of stdout")
    parser.add_argument("--update-audit", help="Write a copy with recomputed quote_check values")
    parser.add_argument(
        "--in-place",
        action="store_true",
        help="Allow --update-audit to replace the input audit",
    )
    return parser


def _record_errors(
    audit: dict[str, Any],
    index: dict[str, Any],
    paragraphs: dict[str, dict[str, Any]],
    ledger: dict[str, Any] | None,
) -> list[str]:
    """Apply decision-audit rules the schema cannot express.

    Args:
        audit: Schema-valid audit.
        index: Manuscript index.
        paragraphs: Paragraph lookup.
        ledger: Optional ledger.

    Returns:
        Record errors. An empty list does not mean the choices are credible.
    """
    errors: list[str] = []
    if audit.get("manuscript_sha256") != _sha(index):
        errors.append("manuscript_sha256 does not match the index")
    decisions = audit["decisions"]
    identifiers = [item["id"] for item in decisions]
    if len(identifiers) != len(set(identifiers)):
        errors.append("Decision ids must be unique.")
    ledger_ids = _ledger_ids(ledger)
    for decision in decisions:
        errors.extend(_decision_errors(decision, paragraphs, ledger_ids, ledger is not None))
    return errors


def _decision_errors(
    decision: dict[str, Any],
    paragraphs: dict[str, dict[str, Any]],
    ledger_ids: set[str] | None,
    ledger_supplied: bool,
) -> list[str]:
    """Check one decision record.

    Args:
        decision: Decision object.
        paragraphs: Paragraph lookup.
        ledger_ids: Ids from the optional ledger.
        ledger_supplied: Whether a ledger file was provided.

    Returns:
        Errors for this decision.
    """
    errors: list[str] = []
    identifier = decision["id"]
    errors.extend(_assessment_errors(decision))
    errors.extend(_alternative_errors(decision, paragraphs))
    errors.extend(_paragraph_errors(decision, paragraphs))
    if ledger_supplied:
        errors.extend(_ledger_errors(identifier, decision.get("ledger_entry_ids", []), ledger_ids or set()))
    return errors


def _assessment_errors(decision: dict[str, Any]) -> list[str]:
    """Keep non-problems from being marked as findings.

    Args:
        decision: Decision object.

    Returns:
        Errors when the assessment and the finding flag disagree, or when a
        later explanation has no later paragraph.
    """
    identifier = decision["id"]
    assessment = decision["assessment"]
    errors: list[str] = []
    if assessment in CLOSED_ASSESSMENTS and decision["warrants_finding"]:
        errors.append(f"{identifier} is {assessment} and must not warrant a finding")
    if assessment == "resolved_later" and not decision["later_paragraph_ids"]:
        errors.append(f"{identifier} is resolved later but names no later paragraph")
    if assessment == "resolved_later" and decision["motive_support"] != "clarified_later":
        errors.append(f"{identifier} is resolved later but motive_support is not clarified_later")
    if assessment == "under_motivated" and decision["motive_support"] not in {"thin", "absent"}:
        errors.append(f"{identifier} is under-motivated but motive_support is not thin or absent")
    if assessment == "obstacle_unexplained" and decision["obstacle_outcome"] != "removed_without_explanation":
        errors.append(f"{identifier} marks an unexplained obstacle without that outcome")
    if assessment == "obstacle_unexplained" and not str(decision["obstacles"]).strip():
        errors.append(f"{identifier} marks an unexplained obstacle but describes none")
    return errors


def _alternative_errors(decision: dict[str, Any], paragraphs: dict[str, dict[str, Any]]) -> list[str]:
    """Check that an ignored or refused alternative was available to the person.

    Args:
        decision: Decision object.
        paragraphs: Paragraph lookup.

    Returns:
        Errors for alternatives the character could not have considered.
    """
    identifier = decision["id"]
    errors: list[str] = []
    for alternative in decision["alternatives"]:
        disposition = alternative["disposition"]
        if disposition == "consciously_refused" and not alternative["known_to_character"]:
            errors.append(f"{identifier} marks a refusal of an alternative the character does not know")
        perceivable = alternative["known_to_character"] or alternative["reasonably_perceivable"]
        if disposition == "ignored" and not perceivable:
            errors.append(f"{identifier} marks an ignored alternative the character could not perceive")
        if disposition in {"consciously_refused", "ignored"} and not alternative["paragraph_ids"]:
            errors.append(f"{identifier} gives no paragraph for a {disposition} alternative")
        for paragraph_id in alternative["paragraph_ids"]:
            if paragraph_id not in paragraphs:
                errors.append(f"{identifier} alternative cites unknown paragraph {paragraph_id}")
    return errors


def _paragraph_errors(decision: dict[str, Any], paragraphs: dict[str, dict[str, Any]]) -> list[str]:
    """Check decision paragraphs and that later paragraphs are actually later.

    Args:
        decision: Decision object.
        paragraphs: Paragraph lookup.

    Returns:
        Errors for unknown ids, evidence links, and paragraph order.
    """
    identifier = decision["id"]
    errors: list[str] = []
    cited = set(decision["paragraph_ids"])
    for paragraph_id in cited:
        if paragraph_id not in paragraphs:
            errors.append(f"{identifier} cites unknown paragraph {paragraph_id}")
    for evidence in decision["evidence"]:
        if evidence["paragraph_id"] not in cited:
            errors.append(f"{identifier} evidence paragraph is missing from paragraph_ids")
    anchor = _max_ordinal(cited, paragraphs)
    for paragraph_id in decision["later_paragraph_ids"]:
        if paragraph_id not in paragraphs:
            errors.append(f"{identifier} cites unknown later paragraph {paragraph_id}")
            continue
        if anchor is not None and int(paragraphs[paragraph_id]["ordinal"]) <= anchor:
            errors.append(f"{identifier} lists {paragraph_id} as later, but it is not after the decision")
    return errors


def _ledger_errors(identifier: str, links: list[str], known: set[str]) -> list[str]:
    """Check optional links into a narrative fact ledger.

    Args:
        identifier: Decision id.
        links: Ledger entry ids named by the decision.
        known: Entry ids present in the supplied ledger.

    Returns:
        Errors for unknown ledger ids.
    """
    return [
        f"{identifier} ledger_entry_ids references unknown entry {link}"
        for link in links
        if link not in known
    ]


def _quote_results(
    audit: dict[str, Any], paragraphs: dict[str, dict[str, Any]]
) -> list[dict[str, Any]]:
    """Recompute quotation checks.

    Args:
        audit: Schema-valid audit.
        paragraphs: Paragraph lookup.

    Returns:
        One result per evidence item. Editorial judgment is not assessed.
    """
    results: list[dict[str, Any]] = []
    for decision in audit["decisions"]:
        for index, evidence in enumerate(decision["evidence"]):
            status, found_in, aligned = quote_status(
                str(evidence["quote"]), str(evidence["paragraph_id"]), paragraphs
            )
            results.append(
                {
                    "decision_id": decision["id"],
                    "evidence_index": index,
                    "paragraph_id": evidence["paragraph_id"],
                    "quote_check": status,
                    "found_in": found_in,
                    "alignment": aligned,
                    "editorial_judgment": "not_assessed",
                }
            )
    return results


def _max_ordinal(identifiers: set[str], paragraphs: dict[str, dict[str, Any]]) -> int | None:
    """Return the latest ordinal among known paragraphs.

    Args:
        identifiers: Paragraph ids.
        paragraphs: Paragraph lookup.

    Returns:
        The maximum ordinal, or None when none of the ids are known.
    """
    ordinals = [
        int(paragraphs[identifier]["ordinal"])
        for identifier in identifiers
        if identifier in paragraphs
    ]
    if not ordinals:
        return None
    return max(ordinals)


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


def _load_ledger(path: str | None) -> dict[str, Any] | None:
    """Load an optional ledger.

    Args:
        path: Ledger path, or None.

    Returns:
        The ledger object, or None when no path was given.

    Raises:
        ManuscriptError: The file is not a JSON object.
    """
    if not path:
        return None
    return _object(read_json(Path(path)), "ledger")


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


def _ledger_ids(ledger: dict[str, Any] | None) -> set[str] | None:
    """Collect entry ids from a ledger.

    Args:
        ledger: Ledger object, or None.

    Returns:
        The ids, or None when no ledger was supplied.
    """
    if ledger is None:
        return None
    entries = ledger.get("entries")
    if not isinstance(entries, list):
        return set()
    return {item["id"] for item in entries if isinstance(item, dict) and isinstance(item.get("id"), str)}


def _update(
    args: argparse.Namespace,
    audit: dict[str, Any],
    document: dict[str, Any],
    index_path: Path,
    audit_path: Path,
    index: dict[str, Any],
) -> None:
    """Write recomputed quote checks into an audit copy.

    Args:
        args: Parsed arguments.
        audit: Original audit.
        document: Check document.
        index_path: Index path.
        audit_path: Audit path.
        index: Index used to protect the manuscript.

    Raises:
        UsageError: The destination is unsafe or schema errors remain.
    """
    destination = Path(args.update_audit)
    replacing = destination.resolve() == audit_path.resolve()
    if replacing and not args.in_place:
        raise UsageError("Refusing to replace the decision audit without --in-place.")
    assert_distinct_output(index_path, destination, "updated decision audit")
    if not replacing:
        assert_distinct_output(audit_path, destination, "updated decision audit")
    manuscript = index.get("source", {}).get("path") if isinstance(index.get("source"), dict) else None
    if isinstance(manuscript, str) and manuscript:
        assert_distinct_output(Path(manuscript), destination, "updated decision audit")
    if document["schema_errors"]:
        raise UsageError("Refusing to update a decision audit that still has schema errors.")
    updated = copy.deepcopy(audit)
    by_key = {(item["decision_id"], item["evidence_index"]): item for item in document["quote_results"]}
    for decision in updated["decisions"]:
        for index, evidence in enumerate(decision["evidence"]):
            result = by_key.get((decision["id"], index))
            if result is not None:
                evidence["quote_check"] = result["quote_check"]
    write_text(destination, dump_json(updated))


def _protect(output: Path, index_path: Path, audit_path: Path, index: dict[str, Any]) -> None:
    """Refuse to overwrite inputs or the manuscript.

    Args:
        output: Requested destination.
        index_path: Index path.
        audit_path: Audit path.
        index: Index document.

    Raises:
        UsageError: The destination collides with a protected file.
    """
    assert_distinct_output(index_path, output, "decision check")
    assert_distinct_output(audit_path, output, "decision check")
    manuscript = index.get("source", {}).get("path") if isinstance(index.get("source"), dict) else None
    if isinstance(manuscript, str) and manuscript:
        assert_distinct_output(Path(manuscript), output, "decision check")


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


def _schema() -> dict[str, Any]:
    """Load the bundled decision-audit schema.

    Returns:
        Parsed schema object.

    Raises:
        ManuscriptError: The schema is missing or not an object.
    """
    path = skill_root() / "templates" / "decision-audit.schema.json"
    payload = read_json(path)
    if not isinstance(payload, dict):
        raise ManuscriptError(f"Decision audit schema is invalid: {path}")
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
