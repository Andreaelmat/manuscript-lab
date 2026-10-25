"""Read and validate the open Agent Skills manifest in SKILL.md.

The parser accepts the frontmatter this skill writes. It is not a general
YAML implementation.
"""

from __future__ import annotations

import re
from pathlib import Path
from typing import Any

from common import skill_root


SPEC_KEYS = {
    "name",
    "description",
    "license",
    "compatibility",
    "metadata",
    "allowed-tools",
}
RESOURCE_ROOTS = {"scripts", "references", "templates", "examples"}
RESOURCE_SUFFIXES = {".py", ".md", ".json"}
NAME_RE = re.compile(r"^[a-z0-9]+(?:-[a-z0-9]+)*$")
LINK_RE = re.compile(r"\[[^\]]*\]\(([^)\s]+)\)")
CODE_RE = re.compile(r"`([^`]+)`")


def skill_directory() -> Path:
    """Return the canonical skill directory.

    Returns:
        Absolute skill root.
    """
    return skill_root()


def load_skill_text(directory: Path | None = None) -> str:
    """Read SKILL.md as text.

    Args:
        directory: Skill root. Defaults to this installation's skill root.

    Returns:
        The full SKILL.md text.

    Raises:
        ValueError: SKILL.md is missing.
    """
    path = (directory or skill_directory()) / "SKILL.md"
    if not path.is_file():
        raise ValueError(f"Missing required file: {path}")
    return path.read_text(encoding="utf-8")


def parse_frontmatter(text: str) -> tuple[dict[str, Any], str]:
    """Split SKILL.md into frontmatter data and body.

    Args:
        text: Full SKILL.md contents. Frontmatter must begin at byte zero.

    Returns:
        A mapping of manifest fields and the Markdown body.

    Raises:
        ValueError: The frontmatter is missing, unclosed, or not the subset
            this parser accepts.
    """
    if not text.startswith("---\n"):
        raise ValueError("SKILL.md must start with YAML frontmatter")
    closing = text.find("\n---\n", 4)
    if closing == -1:
        raise ValueError("SKILL.md frontmatter is not closed")
    raw = text[4:closing]
    body = text[closing + 5 :]
    return _parse_simple_yaml(raw), body


def validate_skill_directory(directory: Path | None = None) -> list[str]:
    """Validate this skill against the open Agent Skills constraints.

    Args:
        directory: Skill root to validate. Defaults to the directory that
            contains these scripts.

    Returns:
        Error strings. An empty list means the package passed these checks.
    """
    root = directory or skill_directory()
    errors: list[str] = []
    try:
        text = load_skill_text(root)
        metadata, body = parse_frontmatter(text)
    except ValueError as exc:
        return [str(exc)]
    errors.extend(_metadata_errors(metadata, root))
    errors.extend(_body_errors(text, body, root))
    return errors


def _parse_simple_yaml(raw: str) -> dict[str, Any]:
    """Parse one-level mappings and a single nested metadata map.

    Args:
        raw: YAML text between the frontmatter markers.

    Returns:
        Parsed mapping.

    Raises:
        ValueError: A line is not a supported key/value pair.
    """
    data: dict[str, Any] = {}
    current_map: str | None = None
    for line_number, line in enumerate(raw.splitlines(), start=2):
        if not line.strip():
            continue
        if line.startswith("  "):
            if current_map is None:
                raise ValueError(f"Nested YAML is only supported under metadata (line {line_number})")
            key, value = _split_kv(line.strip(), line_number)
            data[current_map][key] = _unquote(value)
            continue
        current_map = None
        key, value = _split_kv(line, line_number)
        if value == "":
            data[key] = {}
            current_map = key
            continue
        data[key] = _unquote(value)
    return data


def _split_kv(line: str, line_number: int) -> tuple[str, str]:
    """Split one manifest line on its first colon.

    Args:
        line: A single YAML line.
        line_number: Line number in SKILL.md, used in errors.

    Returns:
        Key and raw value.

    Raises:
        ValueError: The line has no colon.
    """
    if ":" not in line:
        raise ValueError(f"Invalid frontmatter line {line_number}")
    key, value = line.split(":", 1)
    return key.strip(), value.strip()


def _unquote(value: str) -> str:
    """Remove one matching pair of quotes from a scalar.

    Args:
        value: Raw YAML scalar.

    Returns:
        The scalar without wrapping quotes.
    """
    if len(value) >= 2 and value[0] == value[-1] and value[0] in {'"', "'"}:
        return value[1:-1]
    return value


def _metadata_errors(metadata: dict[str, Any], root: Path) -> list[str]:
    """Check required Agent Skills fields and portable optional fields.

    Args:
        metadata: Parsed frontmatter.
        root: Skill directory whose name must match ``name``.

    Returns:
        Validation errors.
    """
    errors: list[str] = []
    unknown = sorted(set(metadata) - SPEC_KEYS)
    if unknown:
        errors.append("Frontmatter has keys outside the Agent Skills spec: " + ", ".join(unknown))
    name = metadata.get("name")
    if not isinstance(name, str) or not 1 <= len(name) <= 64 or NAME_RE.fullmatch(name) is None:
        errors.append("name must be 1-64 lowercase letters, numbers, or single hyphens")
    elif root.name != name:
        errors.append(f"name {name!r} must match the parent directory {root.name!r}")
    description = metadata.get("description")
    if not isinstance(description, str) or not description.strip():
        errors.append("description is required")
    elif len(description) > 1024:
        errors.append("description must be at most 1024 characters")
    compatibility = metadata.get("compatibility")
    if compatibility is not None and (
        not isinstance(compatibility, str) or not 1 <= len(compatibility) <= 500
    ):
        errors.append("compatibility must be a string of 1-500 characters")
    extra = metadata.get("metadata")
    if extra is not None:
        if not isinstance(extra, dict) or not extra:
            errors.append("metadata must be a non-empty string map")
        elif any(not isinstance(key, str) or not isinstance(value, str) for key, value in extra.items()):
            errors.append("metadata values must be strings")
    return errors


def _body_errors(text: str, body: str, root: Path) -> list[str]:
    """Check instruction length and relative resource references.

    Args:
        text: Full SKILL.md text.
        body: Markdown after the frontmatter.
        root: Skill directory used to resolve relative paths.

    Returns:
        Validation errors.
    """
    errors: list[str] = []
    if len(text.splitlines()) > 500:
        errors.append("SKILL.md must stay under 500 lines")
    for token in _resource_tokens(body):
        if not (root / token).is_file():
            errors.append(f"Referenced file does not exist: {token}")
    return errors


def _resource_tokens(body: str) -> list[str]:
    """Collect relative resource paths cited from the skill body.

    Args:
        body: SKILL.md Markdown body.

    Returns:
        Unique POSIX paths in citation order.
    """
    found: list[str] = []
    for match in list(LINK_RE.finditer(body)) + list(CODE_RE.finditer(body)):
        token = _resource_token(match.group(1))
        if token and token not in found:
            found.append(token)
    return found


def _resource_token(token: str) -> str | None:
    """Return a token when it is a bundled relative resource path.

    Args:
        token: Link target or inline code span.

    Returns:
        The normalized relative path, or None when the token is not a
        bundled file reference.
    """
    if "://" in token or token.startswith("#") or token.startswith(("<", "/")):
        return None
    if " " in token or "\\" in token:
        return None
    path = Path(token)
    if ".." in path.parts or not path.parts:
        return None
    if path.parts[0] not in RESOURCE_ROOTS or path.suffix.lower() not in RESOURCE_SUFFIXES:
        return None
    return path.as_posix()
