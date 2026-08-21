#!/usr/bin/env python3
"""Fail-closed runtime availability receipt and artifact-closure validator."""

from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
import re
import stat
from typing import Any


class ReceiptValidationError(RuntimeError):
    """A receipt or its referenced artifact closure is invalid."""


def _resolve_ref(document: dict[str, Any], reference: str) -> dict[str, Any]:
    if not reference.startswith("#/"):
        raise ReceiptValidationError(f"unsupported schema reference: {reference}")
    node: Any = document
    for token in reference[2:].split("/"):
        token = token.replace("~1", "/").replace("~0", "~")
        if not isinstance(node, dict) or token not in node:
            raise ReceiptValidationError(f"unresolved schema reference: {reference}")
        node = node[token]
    if not isinstance(node, dict):
        raise ReceiptValidationError(f"schema reference is not an object: {reference}")
    return node


def _type_matches(expected: str, value: Any) -> bool:
    return {
        "object": isinstance(value, dict),
        "array": isinstance(value, list),
        "string": isinstance(value, str),
        "integer": isinstance(value, int) and not isinstance(value, bool),
        "boolean": isinstance(value, bool),
        "null": value is None,
    }.get(expected, False)


def _validate_schema(document: dict[str, Any], rule: dict[str, Any], value: Any, path: str) -> None:
    if "$ref" in rule:
        _validate_schema(document, _resolve_ref(document, rule["$ref"]), value, path)

    if "oneOf" in rule:
        matches = 0
        for branch in rule["oneOf"]:
            try:
                _validate_schema(document, branch, value, path)
            except ReceiptValidationError:
                continue
            matches += 1
        if matches != 1:
            raise ReceiptValidationError(f"{path}: expected exactly one schema branch, got {matches}")

    if "not" in rule:
        try:
            _validate_schema(document, rule["not"], value, path)
        except ReceiptValidationError:
            pass
        else:
            raise ReceiptValidationError(f"{path}: forbidden schema matched")

    expected_type = rule.get("type")
    if expected_type is not None and not _type_matches(expected_type, value):
        raise ReceiptValidationError(f"{path}: expected {expected_type}, got {type(value).__name__}")
    if "const" in rule and value != rule["const"]:
        raise ReceiptValidationError(f"{path}: expected constant {rule['const']!r}")
    if "enum" in rule and value not in rule["enum"]:
        raise ReceiptValidationError(f"{path}: value is outside enum")
    if isinstance(value, str):
        if len(value) < rule.get("minLength", 0):
            raise ReceiptValidationError(f"{path}: string is too short")
        if "pattern" in rule and re.search(rule["pattern"], value) is None:
            raise ReceiptValidationError(f"{path}: string does not match required pattern")
    if isinstance(value, int) and not isinstance(value, bool) and value < rule.get("minimum", value):
        raise ReceiptValidationError(f"{path}: integer is below minimum")
    if isinstance(value, dict):
        required = rule.get("required", [])
        missing = [name for name in required if name not in value]
        if missing:
            raise ReceiptValidationError(f"{path}: missing required fields: {', '.join(missing)}")
        properties = rule.get("properties", {})
        if rule.get("additionalProperties") is False:
            extras = sorted(set(value) - set(properties))
            if extras:
                raise ReceiptValidationError(f"{path}: unknown fields: {', '.join(extras)}")
        for name, child_rule in properties.items():
            if name in value:
                _validate_schema(document, child_rule, value[name], f"{path}.{name}")


def _artifact_records(receipt: dict[str, Any]) -> list[tuple[str, dict[str, Any]]]:
    records: list[tuple[str, dict[str, Any]]] = []
    for leg in ("codex_availability", "claude_availability", "claude_no_project"):
        artifacts = receipt[leg]["artifacts"]
        records.extend((f"{leg}.artifacts.{name}", record) for name, record in artifacts.items())
    return records


def _validate_artifact_closure(receipt: dict[str, Any], artifact_root: Path) -> None:
    root = artifact_root.resolve()
    referenced: set[Path] = set()
    for label, record in _artifact_records(receipt):
        relative = Path(record["path"])
        if relative.is_absolute() or ".." in relative.parts:
            raise ReceiptValidationError(f"{label}: artifact path escapes closure")
        path = root / relative
        resolved = path.resolve()
        if root not in resolved.parents:
            raise ReceiptValidationError(f"{label}: artifact path escapes closure")
        if path.is_symlink() or not path.exists() or not stat.S_ISREG(path.stat().st_mode):
            raise ReceiptValidationError(f"{label}: artifact is not a regular file")
        if resolved in referenced:
            raise ReceiptValidationError(f"{label}: artifact path is duplicated")
        payload = path.read_bytes()
        if len(payload) != record["bytes"]:
            raise ReceiptValidationError(f"{label}: artifact byte count mismatch")
        if hashlib.sha256(payload).hexdigest() != record["sha256"]:
            raise ReceiptValidationError(f"{label}: artifact digest mismatch")
        referenced.add(resolved)

    excluded = {"receipt.json", "claude-receipt.json"}
    actual = {
        path.resolve()
        for path in root.rglob("*")
        if path.is_file() and path.name not in excluded
    }
    if actual != referenced:
        missing = sorted(str(path.relative_to(root)) for path in referenced - actual)
        extra = sorted(str(path.relative_to(root)) for path in actual - referenced)
        raise ReceiptValidationError(f"artifact closure mismatch: missing={missing} extra={extra}")


def validate_receipt(schema: dict[str, Any], receipt: dict[str, Any], artifact_root: Path) -> None:
    """Validate a receipt structurally and prove its artifact closure."""
    if not isinstance(schema, dict) or not isinstance(receipt, dict):
        raise ReceiptValidationError("schema and receipt must be objects")
    if schema.get("$id") != "https://justinventit.dev/schemas/runtime-skill-receipt-v1.json":
        raise ReceiptValidationError("unsupported receipt schema identity")
    _validate_schema(schema, schema, receipt, "receipt")
    if receipt.get("receipt_kind") != "availability":
        raise ReceiptValidationError("only availability receipts have an artifact closure")
    _validate_artifact_closure(receipt, Path(artifact_root))


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--schema", type=Path, required=True)
    parser.add_argument("--receipt", type=Path, required=True)
    parser.add_argument("--artifact-root", type=Path, required=True)
    args = parser.parse_args()
    try:
        schema = json.loads(args.schema.read_text(encoding="utf-8"))
        receipt = json.loads(args.receipt.read_text(encoding="utf-8"))
        validate_receipt(schema, receipt, args.artifact_root)
        print("runtime availability receipt validation: PASS")
        return 0
    except (OSError, json.JSONDecodeError, ReceiptValidationError) as exc:
        print(f"runtime availability receipt validation error: {exc}")
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
