from __future__ import annotations

import hashlib
import json
from typing import Any

ODCS_VERSION = "v3.1.0"
ODCS_KIND = "DataContract"


class DataContractError(ValueError):
    """Raised when an ODCS contract violates the CK-NEXUS admission boundary."""


def _require_text(value: Any, field_name: str) -> str:
    if not isinstance(value, str) or not value.strip():
        raise DataContractError(f"{field_name} must be a non-empty string")
    return value.strip()


def _canonical_json(value: Any) -> str:
    return json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False)


def validate_odcs_contract(document: dict[str, Any]) -> None:
    """Validate the minimum governed ODCS surface accepted by CK-NEXUS.

    This intentionally validates a conservative subset. Full ODCS schema
    validation can be added behind this boundary later without weakening CK
    ownership, evidence, or production-mutation rules.
    """

    if not isinstance(document, dict):
        raise DataContractError("data contract must be an object")
    if document.get("apiVersion") != ODCS_VERSION:
        raise DataContractError("ODCS apiVersion mismatch")
    if document.get("kind") != ODCS_KIND:
        raise DataContractError("ODCS kind mismatch")

    for field_name in ("id", "name", "version", "status"):
        _require_text(document.get(field_name), field_name)

    team = document.get("team")
    if not isinstance(team, dict):
        raise DataContractError("team must be an object")
    _require_text(team.get("name"), "team.name")
    members = team.get("members")
    if not isinstance(members, list) or not members:
        raise DataContractError("team.members must contain at least one owner")
    if not any(
        isinstance(member, dict)
        and _require_text(member.get("role"), "team.members.role").casefold() == "owner"
        for member in members
    ):
        raise DataContractError("data contract must declare an Owner")

    schemas = document.get("schema")
    if not isinstance(schemas, list) or not schemas:
        raise DataContractError("schema must contain at least one object")

    seen_objects: set[str] = set()
    for index, schema_object in enumerate(schemas):
        if not isinstance(schema_object, dict):
            raise DataContractError(f"schema[{index}] must be an object")
        object_name = _require_text(schema_object.get("name"), f"schema[{index}].name")
        if object_name in seen_objects:
            raise DataContractError(f"duplicate schema object: {object_name}")
        seen_objects.add(object_name)

        properties = schema_object.get("properties")
        if not isinstance(properties, list) or not properties:
            raise DataContractError(f"schema[{index}].properties must not be empty")
        seen_properties: set[str] = set()
        for property_index, prop in enumerate(properties):
            if not isinstance(prop, dict):
                raise DataContractError(
                    f"schema[{index}].properties[{property_index}] must be an object"
                )
            property_name = _require_text(
                prop.get("name"),
                f"schema[{index}].properties[{property_index}].name",
            )
            _require_text(
                prop.get("logicalType"),
                f"schema[{index}].properties[{property_index}].logicalType",
            )
            if property_name in seen_properties:
                raise DataContractError(
                    f"duplicate property {object_name}.{property_name}"
                )
            seen_properties.add(property_name)

            quality = prop.get("quality")
            if quality is not None and not isinstance(quality, list):
                raise DataContractError(
                    f"quality must be a list for {object_name}.{property_name}"
                )

    sla = document.get("slaProperties")
    if sla is not None and not isinstance(sla, list):
        raise DataContractError("slaProperties must be a list when provided")


def odcs_contract_digest(document: dict[str, Any]) -> str:
    validate_odcs_contract(document)
    return hashlib.sha256(_canonical_json(document).encode()).hexdigest()


def contract_dataset_names(document: dict[str, Any]) -> tuple[str, ...]:
    validate_odcs_contract(document)
    contract_name = _require_text(document["name"], "name")
    return tuple(
        f"{contract_name}.{_require_text(schema_object['name'], 'schema.name')}"
        for schema_object in document["schema"]
    )
