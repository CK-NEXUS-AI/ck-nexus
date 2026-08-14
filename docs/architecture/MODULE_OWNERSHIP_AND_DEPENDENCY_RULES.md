# Module Ownership and Dependency Rules

Status: architecture contract.

## Dependency direction

1. `contracts/`, `schemas/`: no runtime/domain dependencies.
2. `config/`: may depend on contracts/schemas only.
3. provider/connector/plugin adapters: depend on contracts/config; never on app UI.
4. persistence/storage adapters: depend on contracts/config and infrastructure clients.
5. governance/trust: depends on contracts/config; exposes decisions/grants, not provider SDKs.
6. services: compose domain behavior using contracts, registries, trust, adapters.
7. AGNES: execution coordination; depends on services/governance/integrations/evidence interfaces.
8. apps: composition roots/UI/API entrypoints; cannot bypass Trust + AGNES for impactful side effects.

## Ownership resolutions

- reasoning planning algorithms -> `intelligence/`; execution plan construction -> `agnes/execution_planner`; service facade -> `services/planning_service` only if needed.
- governance kill switch owns decision/authority; AGNES kill switch enforces it.
- `evidence/` owns append-only evidence artifacts/contracts; `services/evidence` owns APIs/processes; executors emit receipts.
- observability owns technical telemetry; audit owns business/governance actions.
- `apps/api-gateway` is deployable composition; `services/gateway` contains gateway domain/application behavior.
- provider-specific SDK imports are confined to provider/connector adapter packages.

## Forbidden dependencies

- orchestrator -> provider concrete implementation;
- UI -> credential store;
- connector -> another connector's secret/token;
- provider adapter -> AGNES internals;
- contracts/schemas -> runtime package;
- read-only health/status endpoint -> mutation path;
- marketplace package -> implicit permission elevation.

## CI enforcement target

After Q10, add import-boundary tests/static checks for these rules. Violations are architecture failures, not style warnings.
