"""Durable, bounded batch authorization for CK-NEXUS automation.

This module records an explicit set of permissions and targets in one grant.
It is a policy primitive, not an identity provider: API callers must still be
authenticated by the application before creating or revoking grants.
"""

from __future__ import annotations

import json
import math
import sqlite3
import time
from contextlib import closing
from dataclasses import dataclass
from pathlib import Path
from typing import Any

_MAX_TTL_SECONDS = 30 * 24 * 60 * 60
_MAX_COST_USD = 10_000.0


@dataclass(frozen=True, slots=True)
class PermissionRequest:
    permission: str
    target: str
    estimated_cost_usd: float = 0.0
    high_impact: bool = False


@dataclass(frozen=True, slots=True)
class AuthorizationDecision:
    allowed: bool
    reason: str
    grant_id: str | None = None


class AuthorizationStore:
    """SQLite-backed batch grants; secrets and bearer tokens are never stored."""

    def __init__(self, database: str | Path) -> None:
        self.database = str(database)
        Path(self.database).parent.mkdir(parents=True, exist_ok=True, mode=0o700)
        with closing(self._connect()) as connection:
            connection.execute("PRAGMA journal_mode=WAL")
            connection.execute(
                """CREATE TABLE IF NOT EXISTS batch_authorization_grants (
                    grant_id TEXT PRIMARY KEY,
                    permissions_json TEXT NOT NULL,
                    targets_json TEXT NOT NULL,
                    approved_by TEXT NOT NULL,
                    created_at REAL NOT NULL,
                    expires_at REAL NOT NULL,
                    max_cost_usd REAL NOT NULL,
                    high_impact_permissions_json TEXT NOT NULL DEFAULT '[]',
                    revoked_at REAL,
                    revoked_by TEXT
                )"""
            )
            connection.execute(
                "CREATE INDEX IF NOT EXISTS idx_batch_grants_active "
                "ON batch_authorization_grants(expires_at, revoked_at)"
            )
        Path(self.database).chmod(0o600)

    def _connect(self) -> sqlite3.Connection:
        connection = sqlite3.connect(self.database, timeout=10, isolation_level=None)
        connection.row_factory = sqlite3.Row
        connection.execute("PRAGMA busy_timeout=10000")
        connection.execute("PRAGMA synchronous=FULL")
        return connection

    @staticmethod
    def _clean_values(values: list[str], label: str) -> list[str]:
        if not isinstance(values, list) or not values:
            raise ValueError(f"{label} must be a non-empty list")
        if any(not isinstance(value, str) or not value.strip() for value in values):
            raise ValueError(f"{label} must contain non-empty strings")
        cleaned = sorted({value.strip() for value in values})
        if "*" in cleaned or any("*" in value for value in cleaned):
            raise ValueError(f"wildcards are not allowed in {label}")
        if len(cleaned) != len(values):
            raise ValueError(f"{label} must not contain duplicates")
        if any(len(value) > 200 for value in cleaned):
            raise ValueError(f"{label} entries must be at most 200 characters")
        return cleaned

    def create_grant(
        self,
        *,
        grant_id: str,
        permissions: list[str],
        targets: list[str],
        approved_by: str,
        ttl_seconds: int,
        max_cost_usd: float = 0.0,
        high_impact_permissions: list[str] | None = None,
    ) -> dict[str, Any]:
        if not isinstance(grant_id, str) or not grant_id.strip() or len(grant_id) > 200:
            raise ValueError("grant_id must be a non-empty string of at most 200 characters")
        if not isinstance(approved_by, str) or not approved_by.strip() or len(approved_by) > 200:
            raise ValueError("approved_by must be a non-empty audit identity")
        if isinstance(ttl_seconds, bool) or not isinstance(ttl_seconds, int):
            raise ValueError("ttl_seconds must be an integer")
        if not 1 <= ttl_seconds <= _MAX_TTL_SECONDS:
            raise ValueError("ttl_seconds must be between 1 second and 30 days")
        if (
            isinstance(max_cost_usd, bool)
            or not isinstance(max_cost_usd, (int, float))
            or not math.isfinite(max_cost_usd)
            or not 0 <= max_cost_usd <= _MAX_COST_USD
        ):
            raise ValueError("max_cost_usd must be finite and between 0 and 10000")
        clean_permissions = self._clean_values(permissions, "permissions")
        clean_targets = self._clean_values(targets, "targets")
        clean_high_impact = (
            self._clean_values(high_impact_permissions, "high_impact_permissions")
            if high_impact_permissions
            else []
        )
        if not set(clean_high_impact).issubset(clean_permissions):
            raise ValueError("high_impact_permissions must be included in permissions")
        now = time.time()
        with closing(self._connect()) as connection:
            try:
                connection.execute(
                    """INSERT INTO batch_authorization_grants
                    (grant_id, permissions_json, targets_json, approved_by, created_at,
                     expires_at, max_cost_usd, high_impact_permissions_json)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?)""",
                    (
                        grant_id.strip(),
                        json.dumps(clean_permissions, separators=(",", ":")),
                        json.dumps(clean_targets, separators=(",", ":")),
                        approved_by.strip(),
                        now,
                        now + ttl_seconds,
                        float(max_cost_usd),
                        json.dumps(clean_high_impact, separators=(",", ":")),
                    ),
                )
            except sqlite3.IntegrityError as exc:
                raise ValueError("grant_id already exists") from exc
        result = self.get_grant(grant_id.strip())
        if result is None:  # pragma: no cover - protects against unexpected DB behavior
            raise RuntimeError("grant was not persisted")
        return result

    def get_grant(self, grant_id: str) -> dict[str, Any] | None:
        with closing(self._connect()) as connection:
            row = connection.execute(
                "SELECT * FROM batch_authorization_grants WHERE grant_id=?", (grant_id,)
            ).fetchone()
        return self._public_row(row) if row is not None else None

    def list_grants(self) -> list[dict[str, Any]]:
        with closing(self._connect()) as connection:
            rows = connection.execute(
                "SELECT * FROM batch_authorization_grants ORDER BY created_at DESC, grant_id"
            ).fetchall()
        return [self._public_row(row) for row in rows]

    def revoke(self, grant_id: str, *, revoked_by: str) -> bool:
        if not isinstance(revoked_by, str) or not revoked_by.strip():
            raise ValueError("revoked_by must be a non-empty audit identity")
        with closing(self._connect()) as connection:
            cursor = connection.execute(
                "UPDATE batch_authorization_grants SET revoked_at=?, revoked_by=? "
                "WHERE grant_id=? AND revoked_at IS NULL",
                (time.time(), revoked_by.strip()[:200], grant_id),
            )
        return cursor.rowcount == 1

    @staticmethod
    def _public_row(row: sqlite3.Row) -> dict[str, Any]:
        return {
            "grant_id": row["grant_id"],
            "permissions": json.loads(row["permissions_json"]),
            "targets": json.loads(row["targets_json"]),
            "approved_by": row["approved_by"],
            "created_at": row["created_at"],
            "expires_at": row["expires_at"],
            "max_cost_usd": row["max_cost_usd"],
            "high_impact_permissions": json.loads(row["high_impact_permissions_json"]),
            "revoked_at": row["revoked_at"],
            "revoked_by": row["revoked_by"],
        }


def evaluate_authorization(
    store: AuthorizationStore,
    request: PermissionRequest,
    *,
    now: float | None = None,
) -> AuthorizationDecision:
    """Fail-closed evaluation; exact permission and target matches only."""
    if not isinstance(request.permission, str) or not request.permission.strip():
        return AuthorizationDecision(False, "invalid_permission")
    if not isinstance(request.target, str) or not request.target.strip():
        return AuthorizationDecision(False, "invalid_target")
    if (
        isinstance(request.estimated_cost_usd, bool)
        or not isinstance(request.estimated_cost_usd, (int, float))
        or not math.isfinite(request.estimated_cost_usd)
        or request.estimated_cost_usd < 0
    ):
        return AuthorizationDecision(False, "invalid_estimated_cost")
    if not isinstance(request.high_impact, bool):
        return AuthorizationDecision(False, "invalid_risk_flag")
    current_time = time.time() if now is None else now
    for grant in store.list_grants():
        if grant["revoked_at"] is not None or grant["expires_at"] <= current_time:
            continue
        if request.permission not in grant["permissions"] or request.target not in grant["targets"]:
            continue
        if request.estimated_cost_usd > grant["max_cost_usd"]:
            continue
        if request.high_impact and request.permission not in grant["high_impact_permissions"]:
            return AuthorizationDecision(False, "high_impact_requires_explicit_approval")
        return AuthorizationDecision(True, "explicit_batch_grant", grant["grant_id"])
    return AuthorizationDecision(False, "no_matching_active_grant")
