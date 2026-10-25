"""Resolve the separate fields of a finding record.

Nature, evidence checks, and editorial status answer different questions.
This module does not decide whether a literary claim is true.
"""

from __future__ import annotations

from typing import Any


NATURES = {"factual", "interpretive", "strength"}
EDITORIAL_STATUSES = {"unreviewed", "confirmed", "downgraded", "rejected"}
POSITIVE_RULE = (
    "A positive prediction is a finding whose nature is factual and whose "
    "editorial status is confirmed. Rejected, downgraded, unreviewed, "
    "interpretive, and strength findings are not positive predictions."
)


def resolve_nature(finding: dict[str, Any]) -> str | None:
    """Return the finding's nature from the current or the legacy fields.

    Args:
        finding: One findings-document item.

    Returns:
        ``factual``, ``interpretive``, ``strength``, or None when the record
        does not say.
    """
    if "nature" in finding:
        return finding["nature"] if isinstance(finding["nature"], str) else None
    if finding.get("category") == "strength":
        return "strength"
    judgment = finding.get("judgment_type")
    return judgment if isinstance(judgment, str) else None


def resolve_editorial_status(finding: dict[str, Any]) -> str | None:
    """Return the editorial judgment, not the quote check.

    Args:
        finding: One findings-document item.

    Returns:
        ``unreviewed``, ``confirmed``, ``downgraded``, ``rejected``, or None.
    """
    if "editorial_status" in finding:
        status = finding["editorial_status"]
        return status if isinstance(status, str) else None
    legacy = finding.get("verification_status")
    return legacy if isinstance(legacy, str) else None


def prediction_bucket(finding: dict[str, Any]) -> str:
    """Classify a finding for scoring.

    Args:
        finding: One findings-document item.

    Returns:
        ``positive`` only for a confirmed factual finding. Every other record
        returns an exclusion bucket.
    """
    status = resolve_editorial_status(finding)
    if status == "rejected":
        return "rejected"
    if status == "downgraded":
        return "downgraded"
    if status != "confirmed":
        return "unreviewed"
    nature = resolve_nature(finding)
    if nature == "factual":
        return "positive"
    if nature == "strength":
        return "strength"
    return "interpretive"


def record_errors(finding: dict[str, Any], format_version: int) -> list[str]:
    """Check that nature and editorial status are present and not contradictory.

    Args:
        finding: One findings-document item.
        format_version: Document version. Version 2 requires the explicit fields.

    Returns:
        Errors about the record's shape. An empty list does not mean the
        literary claim is correct.
    """
    identifier = str(finding.get("id", "finding"))
    errors: list[str] = []
    has_nature = "nature" in finding
    has_editorial = "editorial_status" in finding
    has_judgment = "judgment_type" in finding
    has_legacy_status = "verification_status" in finding
    if format_version >= 2 and not (has_nature and has_editorial):
        errors.append(f"{identifier} requires nature and editorial_status")
    if format_version < 2 and not ((has_nature and has_editorial) or (has_judgment and has_legacy_status)):
        errors.append(
            f"{identifier} requires nature and editorial_status, "
            "or the legacy judgment_type and verification_status pair"
        )
    errors.extend(_agreement_errors(finding, identifier, has_nature, has_judgment, has_editorial, has_legacy_status))
    return errors


def _agreement_errors(
    finding: dict[str, Any],
    identifier: str,
    has_nature: bool,
    has_judgment: bool,
    has_editorial: bool,
    has_legacy_status: bool,
) -> list[str]:
    """Return errors when explicit and legacy fields disagree.

    Args:
        finding: Finding object.
        identifier: Finding id used in messages.
        has_nature: Whether ``nature`` is present.
        has_judgment: Whether ``judgment_type`` is present.
        has_editorial: Whether ``editorial_status`` is present.
        has_legacy_status: Whether ``verification_status`` is present.

    Returns:
        Agreement errors.
    """
    errors: list[str] = []
    if has_nature and has_judgment and not _nature_agrees(finding["nature"], finding["judgment_type"]):
        errors.append(f"{identifier} has nature and judgment_type that disagree")
    if has_editorial and has_legacy_status and finding["editorial_status"] != finding["verification_status"]:
        errors.append(f"{identifier} has editorial_status and verification_status that disagree")
    nature = resolve_nature(finding)
    status = resolve_editorial_status(finding)
    if nature is not None and nature not in NATURES:
        errors.append(f"{identifier} has an unknown nature")
    if status is not None and status not in EDITORIAL_STATUSES:
        errors.append(f"{identifier} has an unknown editorial status")
    return errors


def _nature_agrees(nature: Any, judgment: Any) -> bool:
    """Return whether a legacy judgment type fits a nature.

    Args:
        nature: Explicit nature.
        judgment: Legacy judgment type.

    Returns:
        True when a strength is paired with an interpretive legacy value, or
        when the two factual/interpretive labels match.
    """
    if nature == "strength":
        return judgment == "interpretive"
    return nature == judgment
