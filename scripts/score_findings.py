"""Score findings without judging literary quality.

Only a confirmed factual finding is a positive prediction. Rejected findings
are excluded even when their nature is factual.
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path
from typing import Any

from common import ManuscriptError, assert_distinct_output, dump_json, read_json, write_text
from finding_record import POSITIVE_RULE, prediction_bucket


def score_findings(findings: dict[str, Any]) -> dict[str, Any]:
    """Classify findings into positive predictions and exclusions.

    Args:
        findings: Findings document, version 1 or 2.

    Returns:
        A score document. ``semantic_correctness`` is always ``not_assessed``.
    """
    items = findings.get("findings")
    if not isinstance(items, list):
        raise ManuscriptError("Findings document is missing a findings list.")
    buckets: dict[str, list[str]] = {
        "positive": [],
        "rejected": [],
        "downgraded": [],
        "unreviewed": [],
        "interpretive": [],
        "strength": [],
    }
    for finding in items:
        if not isinstance(finding, dict) or not isinstance(finding.get("id"), str):
            raise ManuscriptError("A finding is missing an id.")
        buckets[prediction_bucket(finding)].append(finding["id"])
    positive = buckets.pop("positive")
    return {
        "format_version": 1,
        "document_type": "score",
        "rule": POSITIVE_RULE,
        "positive_prediction_ids": positive,
        "excluded": buckets,
        "counts": {"positive_predictions": len(positive)},
        "semantic_correctness": "not_assessed",
        "note": "This count is not a score of the novel and does not prove the report's prose.",
    }


def main(argv: list[str] | None = None) -> int:
    """Run the scoring command.

    Args:
        argv: Arguments excluding the program name.

    Returns:
        ``0`` when a score document is written, ``2`` on usage errors.
    """
    try:
        return _run(argv)
    except ManuscriptError as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 2


def _run(argv: list[str] | None) -> int:
    """Load findings and write the score document.

    Args:
        argv: Arguments excluding the program name.

    Returns:
        ``0`` after a successful write or print.
    """
    parser = _parser()
    args = parser.parse_args(argv)
    source = Path(args.findings)
    findings = read_json(source)
    if not isinstance(findings, dict):
        raise ManuscriptError("Findings JSON must be an object.")
    document = score_findings(findings)
    rendered = dump_json(document)
    if args.output:
        output = Path(args.output)
        assert_distinct_output(source, output, "score")
        write_text(output, rendered)
    else:
        sys.stdout.write(rendered)
    return 0


def _parser() -> argparse.ArgumentParser:
    """Build the command-line parser.

    Returns:
        Parser for the scoring command.
    """
    parser = argparse.ArgumentParser(
        description="List confirmed factual findings as the only positive predictions."
    )
    parser.add_argument("--findings", required=True, help="Findings JSON")
    parser.add_argument("--output", help="Write the score JSON here instead of stdout")
    return parser


if __name__ == "__main__":
    sys.exit(main())
