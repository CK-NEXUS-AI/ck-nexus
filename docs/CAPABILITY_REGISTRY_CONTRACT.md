# Capability Registry Contract

This directory is the canonical registry boundary for CK-NEXUS capabilities.

Rules:
- one stable capability id per capability;
- versions are explicit;
- status is evidence-derived;
- permissions are separate from roles;
- provenance is mandatory for promoted implementations;
- blocked/quarantined capabilities cannot be selected for production execution;
- registry data must not contain secrets.

The JSON Schema at schemas/capability.schema.json defines the minimum contract.
