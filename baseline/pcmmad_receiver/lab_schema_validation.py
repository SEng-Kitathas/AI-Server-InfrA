"""Compact schema validation and runtime route authority checks for lab tool exposure."""

from __future__ import annotations

from collections.abc import Callable, MutableMapping
from dataclasses import dataclass
import re
from typing import Any

JsonObject = MutableMapping[str, Any]
RaiseSchemaError = Callable[[str, str, int], None]


@dataclass(frozen=True)
class SchemaValidationRequest:
    schema: JsonObject
    value: Any
    path: str
    raise_error: RaiseSchemaError


def _schema_type(schema: JsonObject) -> str | list[str] | None:
    expected_type = schema.get("type")
    if expected_type is None and ("properties" in schema or "required" in schema):
        return "object"
    if isinstance(expected_type, list):
        return [str(item) for item in expected_type]
    return str(expected_type) if expected_type is not None else None


def _value_matches_type(value: Any, expected_type: str) -> bool:
    if expected_type == "null":
        return value is None
    if expected_type == "object":
        return isinstance(value, dict)
    if expected_type == "array":
        return isinstance(value, list)
    if expected_type == "string":
        return isinstance(value, str)
    if expected_type == "integer":
        return isinstance(value, int) and not isinstance(value, bool)
    if expected_type == "number":
        return isinstance(value, (int, float)) and not isinstance(value, bool)
    if expected_type == "boolean":
        return isinstance(value, bool)
    return False


def _validate_object(request: SchemaValidationRequest) -> None:
    if not isinstance(request.value, dict):
        request.raise_error("BAD_REQUEST", f"{request.path} must be an object", 400)
    properties = request.schema.get("properties") or {}
    required = request.schema.get("required") or []
    for key in required:
        if key not in request.value:
            request.raise_error("BAD_REQUEST", f"{request.path}.{key} is required", 400)
    additional = request.schema.get("additionalProperties", True)
    unknown = sorted(key for key in request.value if key not in properties)
    if additional is False and unknown:
        request.raise_error(
            "BAD_REQUEST", f"{request.path} contains unknown fields: {', '.join(unknown)}", 400
        )
    if isinstance(additional, dict):
        for key in unknown:
            validate_schema_value(
                additional,
                request.value[key],
                f"{request.path}.{key}",
                raise_error=request.raise_error,
            )
    for key, child_schema in properties.items():
        if key in request.value:
            validate_schema_value(
                child_schema,
                request.value[key],
                f"{request.path}.{key}",
                raise_error=request.raise_error,
            )


def _validate_array(request: SchemaValidationRequest) -> None:
    if not isinstance(request.value, list):
        request.raise_error("BAD_REQUEST", f"{request.path} must be an array", 400)
    min_items = request.schema.get("minItems")
    max_items = request.schema.get("maxItems")
    if min_items is not None and len(request.value) < int(min_items):
        request.raise_error(
            "BAD_REQUEST", f"{request.path} must contain at least {min_items} items", 400
        )
    if max_items is not None and len(request.value) > int(max_items):
        request.raise_error(
            "BAD_REQUEST", f"{request.path} must contain at most {max_items} items", 400
        )
    item_schema = request.schema.get("items")
    if isinstance(item_schema, dict):
        for index, item in enumerate(request.value):
            validate_schema_value(
                item_schema, item, f"{request.path}[{index}]", raise_error=request.raise_error
            )


def _validate_string(request: SchemaValidationRequest) -> None:
    if not isinstance(request.value, str):
        request.raise_error("BAD_REQUEST", f"{request.path} must be a string", 400)
    if "enum" in request.schema and request.value not in request.schema["enum"]:
        request.raise_error(
            "BAD_REQUEST",
            f"{request.path} must be one of: {', '.join(map(str, request.schema['enum']))}",
            400,
        )
    min_length = request.schema.get("minLength")
    max_length = request.schema.get("maxLength")
    if min_length is not None and len(request.value) < int(min_length):
        request.raise_error(
            "BAD_REQUEST", f"{request.path} must be at least {min_length} characters", 400
        )
    if max_length is not None and len(request.value) > int(max_length):
        request.raise_error(
            "BAD_REQUEST", f"{request.path} must be at most {max_length} characters", 400
        )
    pattern = request.schema.get("pattern")
    if pattern is not None:
        try:
            matched = re.fullmatch(str(pattern), request.value) is not None
        except re.error as exc:
            request.raise_error("SCHEMA_INVALID", f"{request.path} schema pattern is invalid: {exc}", 500)
            return
        if not matched:
            request.raise_error("BAD_REQUEST", f"{request.path} does not match required pattern", 400)


def _validate_integer(request: SchemaValidationRequest) -> None:
    if isinstance(request.value, bool) or not isinstance(request.value, int):
        request.raise_error("BAD_REQUEST", f"{request.path} must be an integer", 400)
    _validate_numeric_bounds(request)


def _validate_number(request: SchemaValidationRequest) -> None:
    if isinstance(request.value, bool) or not isinstance(request.value, (int, float)):
        request.raise_error("BAD_REQUEST", f"{request.path} must be numeric", 400)
    _validate_numeric_bounds(request)


def _validate_numeric_bounds(request: SchemaValidationRequest) -> None:
    minimum = request.schema.get("minimum")
    maximum = request.schema.get("maximum")
    if minimum is not None and request.value < minimum:
        request.raise_error("BAD_REQUEST", f"{request.path} must be >= {minimum}", 400)
    if maximum is not None and request.value > maximum:
        request.raise_error("BAD_REQUEST", f"{request.path} must be <= {maximum}", 400)


def _validate_boolean(request: SchemaValidationRequest) -> None:
    if not isinstance(request.value, bool):
        request.raise_error("BAD_REQUEST", f"{request.path} must be a boolean", 400)


def validate_schema_value(
    schema: JsonObject,
    value: Any,
    path: str,
    *,
    raise_error: RaiseSchemaError,
) -> None:
    request = SchemaValidationRequest(
        schema=schema, value=value, path=path, raise_error=raise_error
    )
    if schema.get("nullable") and value is None:
        return
    validators: dict[str, Callable[[SchemaValidationRequest], None]] = {
        "object": _validate_object,
        "array": _validate_array,
        "string": _validate_string,
        "integer": _validate_integer,
        "number": _validate_number,
        "boolean": _validate_boolean,
    }
    expected_type = _schema_type(schema)
    if isinstance(expected_type, list):
        matched = next((item for item in expected_type if _value_matches_type(value, item)), None)
        if matched is None:
            raise_error(
                "BAD_REQUEST",
                f"{path} must match one of the declared types: {', '.join(expected_type)}",
                400,
            )
            return
        if matched == "null":
            return
        matched_schema = dict(schema)
        matched_schema["type"] = matched
        validate_schema_value(matched_schema, value, path, raise_error=raise_error)
        return
    if expected_type == "null":
        if value is not None:
            raise_error("BAD_REQUEST", f"{path} must be null", 400)
        return
    if expected_type in validators:
        validators[expected_type](request)
        return
    if "enum" in schema and value not in schema["enum"]:
        raise_error(
            "BAD_REQUEST", f"{path} must be one of: {', '.join(map(str, schema['enum']))}", 400
        )


def validate_payload_schema(
    tool_name: str,
    schema: JsonObject | None,
    payload: JsonObject,
    *,
    raise_error: RaiseSchemaError,
) -> None:
    if not schema:
        return

    def prefixed(code: str, message: str, status: int) -> None:
        raise_error(code, f"{tool_name}: {message}", status)

    validate_schema_value(schema, payload, "payload", raise_error=prefixed)
