from __future__ import annotations

from copy import deepcopy

import pytest

from creator_app.data_intelligence import (
    ODCS_VERSION,
    OPENLINEAGE_LIBRARY_VERSION,
    OPENLINEAGE_SCHEMA_VERSION,
    DataContractError,
    OpenLineageProjectionError,
    contract_dataset_names,
    odcs_contract_digest,
    to_openlineage_run_event,
    validate_odcs_contract,
    validate_openlineage_projection,
)


def _contract() -> dict:
    return {
        "apiVersion": "v3.1.0",
        "kind": "DataContract",
        "id": "urn:ck-nexus:data:orders",
        "name": "orders",
        "version": "1.0.0",
        "status": "active",
        "team": {
            "name": "data-platform",
            "members": [
                {"username": "owner@example.invalid", "role": "Owner"},
            ],
        },
        "schema": [
            {
                "name": "order_header",
                "properties": [
                    {
                        "name": "order_id",
                        "logicalType": "string",
                        "required": True,
                    },
                    {
                        "name": "amount",
                        "logicalType": "number",
                        "quality": [{"type": "library", "metric": "nullValues"}],
                    },
                ],
            },
            {
                "name": "order_item",
                "properties": [
                    {"name": "order_id", "logicalType": "string"},
                    {"name": "sku", "logicalType": "string"},
                ],
            },
        ],
        "slaProperties": [{"property": "freshness", "value": 15, "unit": "minute"}],
    }


def test_odcs_contract_validates_and_has_deterministic_digest() -> None:
    contract = _contract()
    validate_odcs_contract(contract)
    assert ODCS_VERSION == "v3.1.0"
    digest = odcs_contract_digest(contract)
    reordered = deepcopy(contract)
    reordered["team"] = {
        "members": contract["team"]["members"],
        "name": "data-platform",
    }
    assert odcs_contract_digest(reordered) == digest
    assert contract_dataset_names(contract) == (
        "orders.order_header",
        "orders.order_item",
    )


def test_stale_odcs_version_fails_closed() -> None:
    contract = _contract()
    contract["apiVersion"] = "v3.0.2"
    with pytest.raises(DataContractError, match="apiVersion mismatch"):
        validate_odcs_contract(contract)


def test_contract_requires_owner_and_schema() -> None:
    contract = _contract()
    contract["team"]["members"][0]["role"] = "Reader"
    with pytest.raises(DataContractError, match="declare an Owner"):
        validate_odcs_contract(contract)

    contract = _contract()
    contract["schema"] = []
    with pytest.raises(DataContractError, match="at least one object"):
        validate_odcs_contract(contract)


def test_contract_rejects_duplicate_properties() -> None:
    contract = _contract()
    contract["schema"][0]["properties"].append(
        {"name": "order_id", "logicalType": "string"}
    )
    with pytest.raises(DataContractError, match="duplicate property"):
        validate_odcs_contract(contract)


def test_openlineage_projection_preserves_contract_binding() -> None:
    contract = _contract()
    event = to_openlineage_run_event(
        contract,
        run_id="78c33d18-170c-44d3-a227-b3194f134f73",
        event_time="2026-08-27T05:00:00Z",
        event_type="START",
        job_namespace="urn:ck-nexus:jobs",
        job_name="build-orders",
        dataset_namespace="urn:ck-nexus:datasets",
        input_names=("orders.order_header",),
        output_names=("orders.order_item",),
    )
    assert OPENLINEAGE_LIBRARY_VERSION == "1.52.0"
    assert OPENLINEAGE_SCHEMA_VERSION == "2-0-2"
    assert event["eventType"] == "START"
    assert event["run"]["facets"]["ck_contract_binding"]["contractDigest"] == (
        odcs_contract_digest(contract)
    )
    validate_openlineage_projection(contract, event)


def test_openlineage_rejects_undeclared_dataset() -> None:
    with pytest.raises(OpenLineageProjectionError, match="not declared"):
        to_openlineage_run_event(
            _contract(),
            run_id="78c33d18-170c-44d3-a227-b3194f134f73",
            event_time="2026-08-27T05:00:00Z",
            event_type="START",
            job_namespace="urn:ck-nexus:jobs",
            job_name="build-orders",
            dataset_namespace="urn:ck-nexus:datasets",
            input_names=("orders.unknown",),
        )


def test_openlineage_rejects_invalid_run_id_and_naive_time() -> None:
    common = {
        "contract": _contract(),
        "event_type": "START",
        "job_namespace": "urn:ck-nexus:jobs",
        "job_name": "build-orders",
        "dataset_namespace": "urn:ck-nexus:datasets",
    }
    with pytest.raises(OpenLineageProjectionError, match="run_id must be a UUID"):
        to_openlineage_run_event(
            **common,
            run_id="not-a-uuid",
            event_time="2026-08-27T05:00:00Z",
        )
    with pytest.raises(OpenLineageProjectionError, match="timezone-aware"):
        to_openlineage_run_event(
            **common,
            run_id="78c33d18-170c-44d3-a227-b3194f134f73",
            event_time="2026-08-27T05:00:00",
        )


def test_lineage_projection_cannot_change_contract_or_authority_flags() -> None:
    contract = _contract()
    event = to_openlineage_run_event(
        contract,
        run_id="78c33d18-170c-44d3-a227-b3194f134f73",
        event_time="2026-08-27T05:00:00Z",
        event_type="COMPLETE",
        job_namespace="urn:ck-nexus:jobs",
        job_name="build-orders",
        dataset_namespace="urn:ck-nexus:datasets",
        output_names=("orders.order_header",),
    )

    forged = deepcopy(event)
    forged["run"]["facets"]["ck_contract_binding"]["contractDigest"] = "0" * 64
    with pytest.raises(OpenLineageProjectionError, match="contract digest mismatch"):
        validate_openlineage_projection(contract, forged)

    forged = deepcopy(event)
    forged["run"]["facets"]["ck_contract_binding"]["truthUpgradeAllowed"] = True
    with pytest.raises(OpenLineageProjectionError, match="cannot upgrade truth"):
        validate_openlineage_projection(contract, forged)

    forged = deepcopy(event)
    forged["outputs"][0]["facets"]["ck_data_contract"][
        "productionMutationAllowed"
    ] = True
    with pytest.raises(OpenLineageProjectionError, match="production mutation"):
        validate_openlineage_projection(contract, forged)
