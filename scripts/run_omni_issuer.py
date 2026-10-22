#!/usr/bin/env python3
"""Launch the OMNI issuer as a separate loopback-only authority process."""

from __future__ import annotations

import importlib
import json
import os
import stat
from pathlib import Path

from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey

from creator_app.agnes.execution.omni import EvidenceLevel
from creator_app.council_authority.identity import IdentityVerifier
from creator_app.council_authority.omni_issuer import (
    Ed25519OmniIssuer,
    OmniCapabilityRule,
    SQLiteOmniIssuerStore,
)
from creator_app.council_authority.omni_transport import OmniIssuerHTTPServer


def required(name: str) -> str:
    value = os.environ.get(name, "").strip()
    if not value:
        raise RuntimeError(f"required environment variable missing: {name}")
    return value


def load_callback(spec: str):
    module_name, sep, attribute = spec.partition(":")
    if not sep or not module_name or not attribute:
        raise RuntimeError("provider callback must use module:function syntax")
    callback = getattr(importlib.import_module(module_name), attribute)
    if not callable(callback):
        raise RuntimeError("configured provider callback is not callable")
    return callback


def main() -> None:
    key_path = Path(required("CKNEXUS_OMNI_PRIVATE_KEY_FILE"))
    if key_path.is_symlink():
        raise RuntimeError("OMNI private key path must not be a symlink")
    key_stat = key_path.stat()
    if not stat.S_ISREG(key_stat.st_mode) or stat.S_IMODE(key_stat.st_mode) & 0o077:
        raise RuntimeError("OMNI private key must be a regular file with mode 0600 or stricter")
    private_key = serialization.load_pem_private_key(key_path.read_bytes(), password=None)
    if not isinstance(private_key, Ed25519PrivateKey):
        raise RuntimeError("OMNI issuer key must be Ed25519")

    policy_path = Path(required("CKNEXUS_OMNI_RULES_FILE"))
    policy = json.loads(policy_path.read_text())
    if (
        not isinstance(policy, dict)
        or set(policy) != {"rules"}
        or not isinstance(policy["rules"], list)
    ):
        raise RuntimeError("policy file must be an object containing only a rules list")
    rules = []
    for item in policy["rules"]:
        expected = {
            "skill_id",
            "capability_id",
            "tool_id",
            "target_id",
            "environments",
            "risk",
            "evidence_required",
        }
        if not isinstance(item, dict) or set(item) != expected:
            raise RuntimeError("each policy rule must have the exact documented schema")
        if not isinstance(item["environments"], list) or not all(
            isinstance(x, str) for x in item["environments"]
        ):
            raise RuntimeError("rule environments must be a list of strings")
        if not isinstance(item["evidence_required"], bool) or item["evidence_required"] is not True:
            raise RuntimeError("OMNI evidence requirement must be true")
        rules.append(
            OmniCapabilityRule(
                skill_id=item["skill_id"],
                capability_id=item["capability_id"],
                tool_id=item["tool_id"],
                target_id=item["target_id"],
                environments=tuple(item["environments"]),
                risk=EvidenceLevel(item["risk"]),
                evidence_required=True,
            )
        )
    if not rules:
        raise RuntimeError("at least one explicit OMNI capability rule is required")

    evidence_verifier = load_callback(required("CKNEXUS_OMNI_EVIDENCE_VERIFIER"))
    approval_spec = os.environ.get("CKNEXUS_OMNI_APPROVAL_VERIFIER", "").strip()
    approval_verifier = load_callback(approval_spec) if approval_spec else None
    identity_secret = bytes.fromhex(required("CKNEXUS_OMNI_IDENTITY_SECRET_HEX"))
    identity_verifier = IdentityVerifier(
        identity_secret, issuer=os.environ.get("CKNEXUS_OMNI_TOKEN_ISSUER", "ck-nexus")
    )
    issuer = Ed25519OmniIssuer(
        private_key=private_key,
        store=SQLiteOmniIssuerStore(required("CKNEXUS_OMNI_DATABASE")),
        issuer_id=required("CKNEXUS_OMNI_ISSUER_ID"),
        agent_id=required("CKNEXUS_OMNI_AGENT_ID"),
        model_id=required("CKNEXUS_OMNI_MODEL_ID"),
        policy_id=required("CKNEXUS_OMNI_POLICY_ID"),
        rules=rules,
        runtime_id=required("CKNEXUS_OMNI_RUNTIME_ID"),
        verifier_id=required("CKNEXUS_OMNI_VERIFIER_ID"),
        lease_ttl_seconds=int(os.environ.get("CKNEXUS_OMNI_LEASE_TTL_SECONDS", "60")),
        evidence_verifier=evidence_verifier,
        approval_verifier=approval_verifier,
    )
    host = os.environ.get("CKNEXUS_OMNI_BIND_HOST", "127.0.0.1")
    port = int(os.environ.get("CKNEXUS_OMNI_PORT", "8766"))
    server = OmniIssuerHTTPServer(
        (host, port),
        issuer,
        identity_verifier,
        allowed_service_id=required("CKNEXUS_OMNI_ALLOWED_SERVICE_ID"),
    )
    try:
        server.serve_forever(poll_interval=0.25)
    finally:
        server.server_close()


if __name__ == "__main__":
    main()
