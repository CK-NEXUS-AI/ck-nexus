"""Non-mutating dependency and host-capability probes."""

from __future__ import annotations

import importlib.util
import shutil

from .models import CapabilityModule, DependencyStatus, ModuleProbe


def probe_module(module: CapabilityModule) -> ModuleProbe:
    packages = tuple(
        DependencyStatus(package=name, available=importlib.util.find_spec(name) is not None)
        for name in module.optional_packages
    )
    binaries = tuple(
        DependencyStatus(binary=name, available=shutil.which(name) is not None)
        for name in module.optional_binaries
    )
    return ModuleProbe(module_id=module.module_id, packages=packages, binaries=binaries)
