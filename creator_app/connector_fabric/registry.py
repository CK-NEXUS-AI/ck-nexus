from __future__ import annotations

import json
import os
from dataclasses import replace
from pathlib import Path
from threading import RLock

from creator_app.connector_fabric.models import (
    ConnectorConfig,
    ConnectorRecord,
    ConnectorState,
    DiscoverySnapshot,
    RiskClass,
)


class ConnectorRegistry:
    """Persistent metadata registry. Raw tokens are intentionally never stored here."""

    def __init__(self, path: str | Path) -> None:
        self.path = Path(path)
        self._lock = RLock()
        self._records: dict[str, ConnectorRecord] = {}
        self._snapshots: dict[str, DiscoverySnapshot] = {}
        self._load_configs()

    def register(self, config: ConnectorConfig) -> ConnectorRecord:
        with self._lock:
            if config.connector_id in self._records:
                raise ValueError("connector_id already exists")
            record = ConnectorRecord(config=config)
            self._records[config.connector_id] = record
            self._persist()
            return record

    def get(self, connector_id: str) -> ConnectorRecord:
        try:
            return self._records[connector_id]
        except KeyError:
            raise KeyError("connector not registered") from None

    def list(self) -> tuple[ConnectorRecord, ...]:
        return tuple(self._records[key] for key in sorted(self._records))

    def snapshot(self, connector_id: str) -> DiscoverySnapshot:
        try:
            return self._snapshots[connector_id]
        except KeyError:
            raise KeyError("connector has no discovery snapshot") from None

    def set_snapshot(self, snapshot: DiscoverySnapshot) -> ConnectorRecord:
        with self._lock:
            record = self.get(snapshot.connector_id)
            counts = {risk: 0 for risk in RiskClass}
            for tool in snapshot.tools:
                counts[tool.risk] += 1
            updated = replace(
                record,
                state=ConnectorState.SCHEMA_VERIFIED,
                schema_hash=snapshot.schema_hash,
                tool_count=len(snapshot.tools),
                read_only_count=counts[RiskClass.READ_ONLY],
                write_count=counts[RiskClass.WRITE] + counts[RiskClass.UNKNOWN],
                destructive_count=counts[RiskClass.DESTRUCTIVE],
                blocked_reason=None,
            )
            self._records[snapshot.connector_id] = updated
            self._snapshots[snapshot.connector_id] = snapshot
            self._persist()
            return updated

    def set_state(
        self,
        connector_id: str,
        state: ConnectorState,
        *,
        blocked_reason: str | None = None,
    ) -> ConnectorRecord:
        with self._lock:
            updated = replace(self.get(connector_id), state=state, blocked_reason=blocked_reason)
            self._records[connector_id] = updated
            self._persist()
            return updated

    def _load_configs(self) -> None:
        if not self.path.exists():
            return
        try:
            payload = json.loads(self.path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError):
            raise RuntimeError("Connector registry is corrupt.") from None
        items = payload.get("connectors", []) if isinstance(payload, dict) else []
        if not isinstance(items, list):
            raise RuntimeError("Connector registry is corrupt.")
        from creator_app.connector_fabric.models import ConnectorProtocol
        for item in items:
            if not isinstance(item, dict):
                continue
            try:
                config = ConnectorConfig(
                    connector_id=str(item["connectorId"]),
                    url=str(item["url"]),
                    protocol=ConnectorProtocol(str(item["protocol"])),
                    credential_ref=item.get("credentialRef"),
                    trust_source=str(item.get("trustSource", "manual")),
                    allow_private_network=bool(item.get("allowPrivateNetwork", False)),
                    allowed_tools=tuple(item.get("allowedTools", [])),
                )
            except (KeyError, TypeError, ValueError):
                raise RuntimeError("Connector registry contains an invalid record.") from None
            # A persisted connector is intentionally reloaded as REGISTERED because the
            # verified schema snapshot is runtime evidence and must be rediscovered.
            self._records[config.connector_id] = ConnectorRecord(config=config)

    def _persist(self) -> None:
        self.path.parent.mkdir(parents=True, exist_ok=True)
        payload = {"connectors": [record.as_dict() for record in self.list()]}
        temp = self.path.with_suffix(self.path.suffix + ".tmp")
        temp.write_text(json.dumps(payload, indent=2, sort_keys=True), encoding="utf-8")
        os.replace(temp, self.path)
