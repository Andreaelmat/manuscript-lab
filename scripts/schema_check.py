"""Validate JSON instances against the subset of JSON Schema this skill uses.

The validator covers the keywords stored in ``templates``. It does not fetch
remote schemas and it does not execute schema contents.
"""

from __future__ import annotations

import re
from typing import Any


def validate_instance(
    instance: Any,
    schema: dict[str, Any],
    path: str = "$",
    root: dict[str, Any] | None = None,
) -> list[str]:
    """Validate one JSON value against a schema object.

    Local references such as ``#/$defs/finding`` are followed. Remote
    references are rejected. When a value is null and null is an allowed
    type, other keywords are not applied, so a string pattern does not
    reject null.

    Args:
        instance: Parsed JSON value.
        schema: JSON Schema object using the supported subset.
        path: JSONPath-like location used in error messages.
        root: Root schema used to resolve references. Defaults to ``schema``.

    Returns:
        A list of human-readable errors. An empty list means the instance
        matches the schema.
    """
    if not isinstance(schema, dict):
        return [f"{path} has an invalid schema"]
    root_schema = schema if root is None else root
    if "$ref" in schema:
        return _validate_ref(instance, schema["$ref"], path, root_schema)
    errors: list[str] = []
    if "const" in schema and instance != schema["const"]:
        errors.append(f"{path} must be {schema['const']!r}")
        return errors
    if not _type_ok(instance, schema, path, errors):
        return errors
    if instance is None:
        return errors
    if "enum" in schema and instance not in schema["enum"]:
        errors.append(f"{path} must be one of {schema['enum']!r}")
    if isinstance(instance, str):
        errors.extend(_string_errors(instance, schema, path))
    if isinstance(instance, list):
        errors.extend(_array_errors(instance, schema, path, root_schema))
    if isinstance(instance, dict):
        errors.extend(_object_errors(instance, schema, path, root_schema))
    return errors


def _type_ok(instance: Any, schema: dict[str, Any], path: str, errors: list[str]) -> bool:
    """Return whether ``instance`` matches the schema type.

    Args:
        instance: Value under test.
        schema: Schema that may declare ``type``.
        path: Location used in errors.
        errors: Collector mutated when the type does not match.

    Returns:
        True when later keyword checks should run.
    """
    expected = schema.get("type")
    if expected is None:
        return True
    names = set(expected if isinstance(expected, list) else [expected])
    if instance is None:
        if "null" in names:
            return False
        errors.append(f"{path} must not be null")
        return False
    if any(_matches(instance, name) for name in names):
        return True
    errors.append(f"{path} must be of type {expected!r}")
    return False


def _matches(instance: Any, expected: str) -> bool:
    """Return whether one JSON Schema type name matches a Python value.

    Args:
        instance: Non-null value.
        expected: Schema type name.

    Returns:
        True when the Python value is acceptable for that type.
    """
    if expected == "object":
        return isinstance(instance, dict)
    if expected == "array":
        return isinstance(instance, list)
    if expected == "string":
        return isinstance(instance, str)
    if expected == "boolean":
        return isinstance(instance, bool)
    if expected == "integer":
        return isinstance(instance, int) and not isinstance(instance, bool)
    if expected == "number":
        return isinstance(instance, (int, float)) and not isinstance(instance, bool)
    if expected == "null":
        return instance is None
    return False


def _string_errors(instance: str, schema: dict[str, Any], path: str) -> list[str]:
    """Check string keywords.

    Args:
        instance: String value.
        schema: Schema containing optional ``minLength`` and ``pattern``.
        path: Location used in errors.

    Returns:
        Errors for this string.
    """
    errors: list[str] = []
    minimum = schema.get("minLength")
    if isinstance(minimum, int) and len(instance) < minimum:
        errors.append(f"{path} must be at least {minimum} characters")
    maximum = schema.get("maxLength")
    if isinstance(maximum, int) and len(instance) > maximum:
        errors.append(f"{path} must be at most {maximum} characters")
    pattern = schema.get("pattern")
    if isinstance(pattern, str) and re.fullmatch(pattern, instance) is None:
        errors.append(f"{path} must match /{pattern}/")
    return errors


def _validate_ref(instance: Any, ref: Any, path: str, root: dict[str, Any]) -> list[str]:
    """Follow one local JSON Schema reference.

    Args:
        instance: Value under test.
        ref: Reference string such as ``#/$defs/finding``.
        path: Location used in errors.
        root: Root schema.

    Returns:
        Errors from the referenced schema, or an error when the reference
        cannot be resolved.
    """
    if not isinstance(ref, str) or not ref.startswith("#/"):
        return [f"{path} uses an unsupported schema reference"]
    target: Any = root
    for part in ref[2:].split("/"):
        if not isinstance(target, dict) or part not in target:
            return [f"{path} schema reference {ref} was not found"]
        target = target[part]
    if not isinstance(target, dict):
        return [f"{path} schema reference {ref} is not an object"]
    return validate_instance(instance, target, path, root)


def _array_errors(
    instance: list[Any], schema: dict[str, Any], path: str, root: dict[str, Any]
) -> list[str]:
    """Check array keywords.

    Args:
        instance: Array value.
        schema: Schema containing optional ``minItems`` and ``items``.
        path: Location used in errors.
        root: Root schema used to resolve references inside items.

    Returns:
        Errors for this array and its items.
    """
    errors: list[str] = []
    minimum = schema.get("minItems")
    if isinstance(minimum, int) and len(instance) < minimum:
        errors.append(f"{path} must contain at least {minimum} items")
    item_schema = schema.get("items")
    if isinstance(item_schema, dict):
        for index, item in enumerate(instance):
            errors.extend(validate_instance(item, item_schema, f"{path}[{index}]", root))
    return errors


def _object_errors(
    instance: dict[str, Any], schema: dict[str, Any], path: str, root: dict[str, Any]
) -> list[str]:
    """Check object keywords.

    Args:
        instance: Object value.
        schema: Schema containing ``properties``, ``required``, and
            ``additionalProperties``.
        path: Location used in errors.
        root: Root schema used to resolve references inside properties.

    Returns:
        Errors for this object and its properties.
    """
    errors: list[str] = []
    properties = schema.get("properties", {})
    if not isinstance(properties, dict):
        properties = {}
    required = schema.get("required", [])
    if isinstance(required, list):
        for key in required:
            if key not in instance:
                errors.append(f"{path}.{key} is required")
    if schema.get("additionalProperties") is False:
        for key in instance:
            if key not in properties:
                errors.append(f"{path}.{key} is not allowed")
    for key, subschema in properties.items():
        if key in instance and isinstance(subschema, dict):
            errors.extend(validate_instance(instance[key], subschema, f"{path}.{key}", root))
    return errors
