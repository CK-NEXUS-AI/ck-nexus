"""Verifier profile requirements separated by change class."""

from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass

from .registry import VerifierProfile


@dataclass(frozen=True, slots=True)
class ProfilePolicy:
    profile: VerifierProfile
    checks: tuple[str, ...]
    network: str = "deny"
    credentials: str = "deny"
    host_execution: bool = False

    @property
    def digest(self) -> str:
        payload = {
            "profile": self.profile.value,
            "checks": self.checks,
            "network": self.network,
            "credentials": self.credentials,
            "host_execution": self.host_execution,
        }
        encoded = json.dumps(payload, sort_keys=True, separators=(",", ":")).encode()
        return hashlib.sha256(encoded).hexdigest()


PROFILE_POLICIES: dict[VerifierProfile, ProfilePolicy] = {
    VerifierProfile.PYTHON_QUALITY: ProfilePolicy(
        VerifierProfile.PYTHON_QUALITY,
        ("compileall", "ruff", "pytest_portable"),
    ),
    VerifierProfile.PYTHON_SECURITY: ProfilePolicy(
        VerifierProfile.PYTHON_SECURITY,
        ("bandit", "secret_scan", "pytest_security"),
    ),
    VerifierProfile.API_CONTRACT: ProfilePolicy(
        VerifierProfile.API_CONTRACT,
        ("openapi_schema", "contract_tests", "authz_negative_tests"),
    ),
    VerifierProfile.FRONTEND_QUALITY: ProfilePolicy(
        VerifierProfile.FRONTEND_QUALITY,
        ("static_build", "lint", "accessibility_smoke"),
    ),
    VerifierProfile.CONNECTOR_SECURITY: ProfilePolicy(
        VerifierProfile.CONNECTOR_SECURITY,
        ("scope_check", "credential_boundary", "prompt_injection_tests"),
    ),
    VerifierProfile.DATABASE_MIGRATION: ProfilePolicy(
        VerifierProfile.DATABASE_MIGRATION,
        ("migration_parse", "upgrade_dry_run", "rollback_contract"),
    ),
    VerifierProfile.DEPENDENCY_CHANGE: ProfilePolicy(
        VerifierProfile.DEPENDENCY_CHANGE,
        ("lock_check", "dependency_audit", "license_check", "sbom_diff"),
    ),
    VerifierProfile.CONTAINER_IMAGE: ProfilePolicy(
        VerifierProfile.CONTAINER_IMAGE,
        ("non_root", "image_scan", "sbom", "entrypoint_check"),
    ),
    VerifierProfile.INFRASTRUCTURE: ProfilePolicy(
        VerifierProfile.INFRASTRUCTURE,
        ("syntax", "policy", "least_privilege", "rollback_contract"),
    ),
}


def policy_for(profile: VerifierProfile) -> ProfilePolicy:
    return PROFILE_POLICIES[profile]
