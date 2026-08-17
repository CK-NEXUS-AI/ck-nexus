"""Non-mutating dependency and host-capability probes."""

from __future__ import annotations

import importlib.util
import shutil

from .models import CapabilityModule, DependencyStatus, ModuleProbe


_IMPORT_NAMES = {
    "nats-py": "nats",
    "qdrant-client": "qdrant_client",
    "opentelemetry-api": "opentelemetry",
    "opentelemetry-sdk": "opentelemetry.sdk",
}


def _package_available(distribution_name: str) -> bool:
    import_name = _IMPORT_NAMES.get(distribution_name, distribution_name.replace("-", "_"))
    try:
        return importlib.util.find_spec(import_name) is not None
    except (ImportError, ModuleNotFoundError, ValueError):
        return False


def probe_module(module: CapabilityModule) -> ModuleProbe:
    packages = tuple(
        DependencyStatus(package=name, available=_package_available(name))
        for name in module.optional_packages
    )
    binaries = tuple(
        DependencyStatus(binary=name, available=shutil.which(name) is not None)
        for name in module.optional_binaries
    )
    return ModuleProbe(module_id=module.module_id, packages=packages, binaries=binaries)
