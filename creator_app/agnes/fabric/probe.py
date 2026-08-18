"""Non-mutating dependency and host-capability probes."""

import shutil
from importlib import metadata

from .models import CapabilityModule, DependencyStatus, ModuleProbe


def _package_available(distribution_name: str) -> bool:
    try:
        metadata.distribution(distribution_name)
    except (metadata.PackageNotFoundError, ValueError):
        return False
    return True


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
