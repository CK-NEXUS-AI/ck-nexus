"""AGNES capability fabric facade.

This facade is read-first. It inventories built-in module contracts and probes
optional external engines without installing packages, executing shell commands,
or changing host configuration.
"""

from __future__ import annotations

from dataclasses import dataclass

from .catalog import ModuleCatalog
from .models import ActivationMode, ModuleProbe, ResourceSnapshot, RuntimeDecision
from .probe import probe_module
from .quality import select_runtime_decision
from .resource import snapshot


@dataclass(frozen=True)
class FabricStatus:
    module_count: int
    write_capable_count: int
    default_disabled_count: int
    resource: ResourceSnapshot
    runtime: RuntimeDecision


class AGNESCapabilityFabric:
    def __init__(self, catalog: ModuleCatalog | None = None) -> None:
        self.catalog = catalog or ModuleCatalog()

    def probe(self, module_id: str) -> ModuleProbe:
        return probe_module(self.catalog.get(module_id))

    def status(self, *, sovereign: bool = False) -> FabricStatus:
        resource = snapshot()
        runtime = select_runtime_decision(resource, sovereign=sovereign)
        modules = self.catalog.all()
        return FabricStatus(
            module_count=len(modules),
            write_capable_count=sum(module.write_capable for module in modules),
            default_disabled_count=sum(
                module.default_mode is ActivationMode.DISABLED for module in modules
            ),
            resource=resource,
            runtime=runtime,
        )

    def external_dependency_plan(self) -> dict[str, tuple[str, ...]]:
        packages: set[str] = set()
        binaries: set[str] = set()
        for module in self.catalog.all():
            packages.update(module.optional_packages)
            binaries.update(module.optional_binaries)
        return {
            "python_packages": tuple(sorted(packages)),
            "host_binaries": tuple(sorted(binaries)),
        }
