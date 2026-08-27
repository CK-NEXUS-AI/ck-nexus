from __future__ import annotations

from datetime import datetime
from typing import Any
from uuid import UUID

from .contracts import contract_dataset_names, odcs_contract_digest, validate_odcs_contract

OPENLINEAGE_LIBRARY_VERSION = "1.52.0"
OPENLINEAGE_SCHEMA_VERSION = "2-0-2"
OPENLINEAGE_RUN_EVENT_SCHEMA = (
    "https://openlineage.io/spec/2-0-2/OpenLineage.json#/$defs/RunEvent"
)
PRODUCER = "urn:ck-nexus:openlineage-adapter:v1"
CONTRACT_FACET_SCHEMA = "urn:ck-nexus:schema:openlineage:ck-data-contract-facet:v1"
_ALLOWED_EVENT_TYPES = {"START", "RUNNING", "COMPLETE", "ABORT", "FAIL", "OTHER"}


class OpenLineageProjectionError(ValueError):
    """Raised when a lineage projection loses CK-NEXUS data-contract bindings."""


def _require_text(value: Any, field_name: str) -> str:
    if not isinstance(value, str) or not value.strip():
        raise OpenLineageProjectionError(f"{field_name} must be a non-empty string")
    return value.strip()


def _validate_event_time(value: str) -> str:
    text = _require_text(value, "event_time")
    normalized = text[:-1] + "+00:00" if text.endswith("Z") else text
    try:
        parsed = datetime.fromisoformat(normalized)
    except ValueError as exc:
        raise OpenLineageProjectionError("event_time must be ISO-8601") from exc
    if parsed.tzinfo is None:
        raise OpenLineageProjectionError("event_time must be timezone-aware")
    return text


def _validate_run_id(value: str) -> str:
    text = _require_text(value, "run_id")
    try:
        UUID(text)
    except ValueError as exc:
        raise OpenLineageProjectionError("run_id must be a UUID") from exc
    return text


def _dataset(
    *,
    namespace: str,
    name: str,
    contract_id: str,
    contract_version: str,
    contract_digest: str,
) -> dict[str, Any]:
    return {
        "namespace": namespace,
        "name": name,
        "facets": {
            "ck_data_contract": {
                "_producer": PRODUCER,
                "_schemaURL": CONTRACT_FACET_SCHEMA,
                "contractId": contract_id,
                "contractVersion": contract_version,
                "contractDigest": contract_digest,
                "truthUpgradeAllowed": False,
                "productionMutationAllowed": False,
            }
        },
    }


def to_openlineage_run_event(
    contract: dict[str, Any],
    *,
    run_id: str,
    event_time: str,
    event_type: str,
    job_namespace: str,
    job_name: str,
    dataset_namespace: str,
    input_names: tuple[str, ...] = (),
    output_names: tuple[str, ...] = (),
) -> dict[str, Any]:
    """Project governed CK data identities into an OpenLineage RunEvent."""

    validate_odcs_contract(contract)
    run_id = _validate_run_id(run_id)
    event_time = _validate_event_time(event_time)
    event_type = _require_text(event_type, "event_type").upper()
    if event_type not in _ALLOWED_EVENT_TYPES:
        raise OpenLineageProjectionError("unsupported OpenLineage event type")

    job_namespace = _require_text(job_namespace, "job_namespace")
    job_name = _require_text(job_name, "job_name")
    dataset_namespace = _require_text(dataset_namespace, "dataset_namespace")
    contract_id = _require_text(contract["id"], "contract.id")
    contract_version = _require_text(contract["version"], "contract.version")
    contract_digest = odcs_contract_digest(contract)
    allowed_names = set(contract_dataset_names(contract))

    selected_names = set(input_names) | set(output_names)
    unknown = sorted(selected_names - allowed_names)
    if unknown:
        raise OpenLineageProjectionError(
            f"datasets are not declared by the data contract: {','.join(unknown)}"
        )

    dataset_kwargs = {
        "namespace": dataset_namespace,
        "contract_id": contract_id,
        "contract_version": contract_version,
        "contract_digest": contract_digest,
    }
    return {
        "eventTime": event_time,
        "producer": PRODUCER,
        "schemaURL": OPENLINEAGE_RUN_EVENT_SCHEMA,
        "eventType": event_type,
        "run": {
            "runId": run_id,
            "facets": {
                "ck_contract_binding": {
                    "_producer": PRODUCER,
                    "_schemaURL": CONTRACT_FACET_SCHEMA,
                    "contractDigest": contract_digest,
                    "truthUpgradeAllowed": False,
                    "productionMutationAllowed": False,
                }
            },
        },
        "job": {
            "namespace": job_namespace,
            "name": job_name,
        },
        "inputs": [
            _dataset(name=name, **dataset_kwargs)
            for name in sorted(set(input_names))
        ],
        "outputs": [
            _dataset(name=name, **dataset_kwargs)
            for name in sorted(set(output_names))
        ],
    }


def validate_openlineage_projection(
    contract: dict[str, Any],
    event: dict[str, Any],
) -> None:
    """Fail closed if a projected lineage event loses contract authority."""

    contract_digest = odcs_contract_digest(contract)
    if event.get("producer") != PRODUCER:
        raise OpenLineageProjectionError("producer mismatch")
    if event.get("schemaURL") != OPENLINEAGE_RUN_EVENT_SCHEMA:
        raise OpenLineageProjectionError("OpenLineage schema mismatch")
    if event.get("eventType") not in _ALLOWED_EVENT_TYPES:
        raise OpenLineageProjectionError("invalid event type")

    run = event.get("run")
    job = event.get("job")
    if not isinstance(run, dict) or not isinstance(job, dict):
        raise OpenLineageProjectionError("run and job are required")
    _validate_run_id(run.get("runId", ""))
    _validate_event_time(event.get("eventTime", ""))
    _require_text(job.get("namespace"), "job.namespace")
    _require_text(job.get("name"), "job.name")

    run_facets = run.get("facets")
    if not isinstance(run_facets, dict):
        raise OpenLineageProjectionError("run facets are required")
    binding = run_facets.get("ck_contract_binding")
    if not isinstance(binding, dict):
        raise OpenLineageProjectionError("contract binding facet missing")
    if binding.get("contractDigest") != contract_digest:
        raise OpenLineageProjectionError("contract digest mismatch")
    if binding.get("truthUpgradeAllowed") is not False:
        raise OpenLineageProjectionError("lineage cannot upgrade truth")
    if binding.get("productionMutationAllowed") is not False:
        raise OpenLineageProjectionError("lineage cannot enable production mutation")

    allowed_names = set(contract_dataset_names(contract))
    for direction in ("inputs", "outputs"):
        datasets = event.get(direction)
        if not isinstance(datasets, list):
            raise OpenLineageProjectionError(f"{direction} must be a list")
        for dataset in datasets:
            if not isinstance(dataset, dict) or dataset.get("name") not in allowed_names:
                raise OpenLineageProjectionError("undeclared dataset in lineage event")
            facets = dataset.get("facets")
            facet = facets.get("ck_data_contract") if isinstance(facets, dict) else None
            if not isinstance(facet, dict) or facet.get("contractDigest") != contract_digest:
                raise OpenLineageProjectionError("dataset contract binding mismatch")
            if facet.get("truthUpgradeAllowed") is not False:
                raise OpenLineageProjectionError("dataset lineage cannot upgrade truth")
            if facet.get("productionMutationAllowed") is not False:
                raise OpenLineageProjectionError(
                    "dataset lineage cannot enable production mutation"
                )
