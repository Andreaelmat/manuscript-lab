"""Compare quotations with indexed manuscript paragraphs.

A match means the quoted characters occur. It does not judge the editorial
claim that uses them.
"""

from __future__ import annotations

from typing import Any

from common import normalize_quote


def quote_status(
    quote: str, cited: str, paragraphs: dict[str, dict[str, Any]]
) -> tuple[str, list[str], str]:
    """Classify a quote against the cited paragraph.

    Args:
        quote: Claimed excerpt.
        cited: Paragraph id the citation names. Empty when the report did not
            name one.
        paragraphs: Paragraph lookup keyed by id.

    Returns:
        Status, matching paragraph ids capped at ten, and an alignment label.
        Alignment is ``boundary``, ``inside_quotation``, ``mid_token``, or
        ``not_applicable``.
    """
    found_in = search_quotes(quote, paragraphs)[:10]
    paragraph = paragraphs.get(cited) if cited else None
    if cited and paragraph is None:
        status = "not_found_at_cited_paragraph" if found_in else "not_found"
        return status, found_in, "not_applicable"
    if paragraph is not None and contains_quote(quote, paragraph, exact=True):
        return "verified_exact", [cited], alignment(quote, paragraph)
    if paragraph is not None and contains_quote(quote, paragraph, exact=False):
        return "verified_normalized", [cited], alignment(quote, paragraph)
    if not cited and found_in:
        host = paragraphs[found_in[0]]
        exact = contains_quote(quote, host, exact=True)
        status = "verified_exact" if exact else "verified_normalized"
        return status, found_in, alignment(quote, host)
    if found_in:
        return "not_found_at_cited_paragraph", found_in, "not_applicable"
    return "not_found", [], "not_applicable"


def search_quotes(quote: str, paragraphs: dict[str, dict[str, Any]]) -> list[str]:
    """Find paragraphs that contain a quote exactly or after normalization.

    Args:
        quote: Claimed excerpt.
        paragraphs: Paragraph lookup.

    Returns:
        Matching paragraph ids in index order.
    """
    matches: list[str] = []
    for identifier, paragraph in paragraphs.items():
        if contains_quote(quote, paragraph, exact=True) or contains_quote(quote, paragraph, exact=False):
            matches.append(identifier)
    return matches


def contains_quote(quote: str, paragraph: dict[str, Any], exact: bool) -> bool:
    """Return whether a paragraph contains a quote.

    Args:
        quote: Claimed excerpt.
        paragraph: Index paragraph with ``text`` and optional ``raw``.
        exact: True for a literal substring, False for normalized comparison.

    Returns:
        True when the quote occurs in ``text`` or ``raw``.
    """
    if not quote.strip():
        return False
    if exact:
        return any(quote in haystack for haystack in haystacks(paragraph))
    needle = normalize_quote(quote)
    if not needle:
        return False
    return any(needle in normalize_quote(haystack) for haystack in haystacks(paragraph))


def alignment(quote: str, paragraph: dict[str, Any]) -> str:
    """Describe where a literal match sits inside the paragraph.

    Args:
        quote: Excerpt already known to match, exactly or after normalization.
        paragraph: Host paragraph.

    Returns:
        ``mid_token`` when the match starts inside a word, ``inside_quotation``
        when it starts just after a quotation mark, otherwise ``boundary``.
    """
    for haystack in haystacks(paragraph):
        start = haystack.find(quote)
        if start < 0:
            folded = normalize_quote(haystack)
            start = folded.find(normalize_quote(quote))
            haystack = folded
        if start < 0:
            continue
        if start == 0:
            return "boundary"
        previous = haystack[start - 1]
        if previous.isalnum():
            return "mid_token"
        if previous in {'"', "'", "“", "”", "«", "»"}:
            return "inside_quotation"
        return "boundary"
    return "not_applicable"


def haystacks(paragraph: dict[str, Any]) -> list[str]:
    """Return the text surfaces a quote may match.

    Args:
        paragraph: Index paragraph.

    Returns:
        Reader-facing text, plus raw source text when it differs.
    """
    surfaces = [str(paragraph.get("text", ""))]
    raw = paragraph.get("raw")
    if isinstance(raw, str) and raw not in surfaces:
        surfaces.append(raw)
    return surfaces
